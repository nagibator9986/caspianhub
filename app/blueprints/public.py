"""Публичная часть: главная, каталог сервисов, страница сервиса, новости, FAQ, поддержка."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from flask import (Blueprint, abort, current_app, flash, g, redirect, render_template,
                   request, send_from_directory, url_for)
from flask_login import current_user
from sqlalchemy import or_

from ..extensions import db
from ..models import (AppealDepartment, Category, ContentSubmission, Course, Faq, Feedback,
                      HomeSection, LibraryAsset, News, PartnerOffer, Service, ServiceEvent,
                      SocialLink, SubmissionFile, Testimonial)
from ..utils import delete_upload, setting, setting_bool, store_student_file

bp = Blueprint("public", __name__)


def _published_services():
    return Service.query.filter_by(is_published=True)


@bp.route("/")
def index():
    services = (_published_services()
                .order_by(Service.position, Service.id).all())
    featured = [s for s in services if s.is_featured][:6] or services[:6]

    categories = (Category.query.filter_by(is_active=True)
                  .order_by(Category.position).all())

    courses = (Course.query.join(Service)
               .filter(Course.is_published.is_(True), Service.is_published.is_(True))
               .order_by(Service.position).limit(6).all())

    news = (News.query.filter_by(is_published=True)
            .order_by(News.is_pinned.desc(), News.published_at.desc()).limit(3).all())

    testimonials = (Testimonial.query.filter_by(is_active=True)
                    .order_by(Testimonial.position).all())

    faqs = (Faq.query.filter_by(is_active=True)
            .order_by(Faq.position).limit(6).all())

    sections = {s.key: s for s in HomeSection.query.filter_by(is_active=True)
                .order_by(HomeSection.position).all()}

    stats = {
        "services": len(services),
        "categories": len(categories),
        "courses": Course.query.filter_by(is_published=True).count(),
        "lessons": sum(c.lesson_count for c in Course.query.filter_by(is_published=True).all()),
    }

    return render_template("public/index.html",
                           services=services, featured=featured, categories=categories,
                           courses=courses, news=news, testimonials=testimonials,
                           faqs=faqs, sections=sections, stats=stats)


@bp.route("/services")
def services():
    q = (request.args.get("q") or "").strip()
    cat_slug = request.args.get("cat") or "all"

    query = _published_services()
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Service.name_ru.ilike(like), Service.name_kk.ilike(like), Service.name_en.ilike(like),
            Service.tagline_ru.ilike(like), Service.description_ru.ilike(like),
        ))
    items = query.order_by(Service.position, Service.id).all()

    categories = (Category.query.filter_by(is_active=True)
                  .order_by(Category.position).all())

    return render_template("public/services.html",
                           services=items, categories=categories,
                           q=q, active_cat=cat_slug)


@bp.route("/services/<slug>")
def service_detail(slug: str):
    service = Service.query.filter_by(slug=slug).first_or_404()
    if not service.is_published and not (current_user.is_authenticated and current_user.is_staff):
        abort(404)

    service.views = (service.views or 0) + 1
    db.session.add(ServiceEvent(
        service_id=service.id, kind="view",
        user_id=current_user.id if current_user.is_authenticated else None,
    ))
    db.session.commit()

    related = (_published_services()
               .filter(Service.category_id == service.category_id, Service.id != service.id)
               .order_by(Service.position).limit(3).all())
    if len(related) < 3:
        extra = (_published_services()
                 .filter(Service.id != service.id,
                         Service.id.notin_([r.id for r in related] or [0]))
                 .order_by(Service.is_featured.desc(), Service.position)
                 .limit(3 - len(related)).all())
        related += extra

    course = service.course if service.course and service.course.is_published else None
    progress = course.progress_for(current_user) if course else 0

    return render_template("public/service_detail.html",
                           service=service, related=related, course=course, progress=progress)


@bp.route("/category/<slug>")
def category(slug: str):
    cat = Category.query.filter_by(slug=slug, is_active=True).first_or_404()
    items = (_published_services().filter(Service.category_id == cat.id)
             .order_by(Service.position).all())
    categories = Category.query.filter_by(is_active=True).order_by(Category.position).all()
    return render_template("public/category.html",
                           category=cat, services=items, categories=categories)


@bp.route("/courses")
def courses():
    items = (Course.query.join(Service)
             .filter(Course.is_published.is_(True), Service.is_published.is_(True))
             .order_by(Service.position).all())
    return render_template("public/courses.html", courses=items)


@bp.route("/news")
def news():
    page = request.args.get("page", 1, type=int)
    kind = request.args.get("kind")
    query = News.query.filter_by(is_published=True)
    if kind in ("news", "update", "announcement"):
        query = query.filter_by(kind=kind)
    pagination = (query.order_by(News.is_pinned.desc(), News.published_at.desc())
                  .paginate(page=page, per_page=9, error_out=False))
    return render_template("public/news.html", pagination=pagination, kind=kind)


@bp.route("/news/<slug>")
def news_detail(slug: str):
    item = News.query.filter_by(slug=slug).first_or_404()
    if not item.is_published and not (current_user.is_authenticated and current_user.is_staff):
        abort(404)
    item.views = (item.views or 0) + 1
    db.session.commit()
    more = (News.query.filter(News.is_published.is_(True), News.id != item.id)
            .order_by(News.published_at.desc()).limit(3).all())
    return render_template("public/news_detail.html", item=item, more=more)


@bp.route("/faq")
def faq():
    items = Faq.query.filter_by(is_active=True).order_by(Faq.position).all()
    groups: dict[str, list] = {}
    for item in items:
        groups.setdefault(item.category or "Общее", []).append(item)
    return render_template("public/faq.html", groups=groups, total=len(items))


@bp.route("/about")
def about():
    stats = {
        "services": Service.query.filter_by(is_published=True).count(),
        "courses": Course.query.filter_by(is_published=True).count(),
        "lessons": sum(c.lesson_count for c in Course.query.filter_by(is_published=True).all()),
        "categories": Category.query.filter_by(is_active=True).count(),
    }
    return render_template("public/about.html", stats=stats)


@bp.route("/support", methods=["GET", "POST"])
def support():
    services_list = (Service.query.filter_by(is_published=True)
                     .order_by(Service.name_ru).all())

    if request.method == "POST":
        message = (request.form.get("message") or "").strip()
        if len(message) < 10:
            flash("Опишите вопрос подробнее — минимум 10 символов.", "danger")
            return redirect(url_for("public.support"))
        if request.form.get("website"):          # honeypot против ботов
            return redirect(url_for("public.support"))

        service_id = request.form.get("service_id", type=int)
        db.session.add(Feedback(
            name=(request.form.get("name") or "").strip()[:160],
            email=(request.form.get("email") or "").strip()[:160],
            topic=(request.form.get("topic") or "Вопрос")[:60],
            service_id=service_id or None,
            message=message[:4000],
        ))
        db.session.commit()
        flash("Спасибо! Мы получили обращение и ответим в ближайшее время.", "success")
        return redirect(url_for("public.support"))

    return render_template("public/support.html", services=services_list)


# ─────────────────── Сообщество ───────────────────

APPEAL_KINDS = ("Вопрос", "Предложение", "Обращение")
SUBMIT_WINDOW, SUBMIT_LIMIT = 600, 5
_recent_submits: dict[str, deque] = defaultdict(deque)


def _too_many_submits() -> bool:
    """Защита публичных форм: не больше пяти отправок за десять минут с одного адреса в процессе."""
    now = time.time()
    if len(_recent_submits) > 5000:
        _recent_submits.clear()
    bucket = _recent_submits[request.remote_addr or "-"]
    while bucket and now - bucket[0] > SUBMIT_WINDOW:
        bucket.popleft()
    if len(bucket) >= SUBMIT_LIMIT:
        return True
    bucket.append(now)
    return False


def _clean(name: str, limit: int) -> str:
    return (request.form.get(name) or "").strip()[:limit]


@bp.route("/social")
def social():
    items = SocialLink.query.filter_by(is_active=True).order_by(SocialLink.position).all()
    groups = [(key, label, [i for i in items if i.group == key]) for key, label in SocialLink.GROUPS.items()]
    return render_template("public/social.html", groups=groups)


@bp.route("/bonuses")
def bonuses():
    items = PartnerOffer.query.filter_by(is_active=True).order_by(PartnerOffer.position).all()
    return render_template("public/bonuses.html", items=items)


@bp.route("/contact")
def contact():
    items = AppealDepartment.query.filter_by(is_active=True).order_by(AppealDepartment.position).all()
    return render_template("public/contact.html", items=items)


@bp.route("/contact/<slug>", methods=["GET", "POST"])
def contact_form(slug: str):
    department = AppealDepartment.query.filter_by(slug=slug, is_active=True).first_or_404()
    form = {"name": "", "group": "", "reach": "", "kind": APPEAL_KINDS[0], "message": ""}
    if current_user.is_authenticated:
        form.update(name=current_user.full_name or "", group=current_user.group_name or "",
                    reach=current_user.email or "")

    if request.method == "POST":
        form = {"name": _clean("name", 120), "group": _clean("group", 30), "reach": _clean("reach", 160),
                "kind": _clean("kind", 30), "message": _clean("message", 4000)}
        if request.form.get("website"):          # honeypot против ботов
            return redirect(url_for("public.contact"))
        if not form["name"] or not form["reach"]:
            flash("Укажите ФИО и контакт, чтобы вам могли ответить.", "danger")
        elif len(form["message"]) < 10:
            flash("Опишите вопрос подробнее — минимум 10 символов.", "danger")
        elif _too_many_submits():
            flash("Слишком много отправок подряд. Попробуйте через несколько минут.", "danger")
        else:
            kind = form["kind"] if form["kind"] in APPEAL_KINDS else APPEAL_KINDS[0]
            db.session.add(Feedback(
                name=f"{form['name']} ({form['group']})" if form["group"] else form["name"],
                email=form["reach"], topic=department.name_ru[:60],
                message=f"{kind}: {form['message']}",
            ))
            db.session.commit()
            flash(f"Спасибо! Обращение передано: {department.tr('name')}.", "success")
            return redirect(url_for("public.contact"))
    return render_template("public/contact_form.html", department=department, form=form, kinds=APPEAL_KINDS)


@bp.route("/library")
def library():
    items = (LibraryAsset.query.filter_by(is_active=True)
             .order_by(LibraryAsset.position, LibraryAsset.id).all())
    groups: dict[str, list] = {}
    for item in items:
        groups.setdefault(item.category or "Материалы", []).append(item)
    return render_template("public/library.html", groups=groups, total=len(items))


@bp.route("/library/<int:asset_id>/download")
def library_download(asset_id: int):
    item = LibraryAsset.query.filter_by(id=asset_id, is_active=True).first_or_404()
    return send_from_directory(current_app.static_folder, item.path, as_attachment=True,
                               download_name=item.download_name or item.path.rsplit("/", 1)[-1])


@bp.route("/student-content", methods=["GET", "POST"])
def student_content():
    kinds = ContentSubmission.KINDS
    form = {"kind": "photo", "description": "", "event_name": "", "link_url": "",
            "author_name": "", "author_group": "", "author_contact": ""}
    if current_user.is_authenticated:
        form.update(author_name=current_user.full_name or "", author_group=current_user.group_name or "",
                    author_contact=current_user.email or "")

    if request.method == "POST":
        form = {"kind": _clean("kind", 20), "description": _clean("description", 4000),
                "event_name": _clean("event_name", 200), "link_url": _clean("link_url", 500),
                "author_name": _clean("author_name", 160), "author_group": _clean("author_group", 60),
                "author_contact": _clean("author_contact", 160)}
        if request.form.get("website"):          # honeypot против ботов
            return redirect(url_for("public.student_content"))
        uploads = [f for f in request.files.getlist("files") if f and f.filename]
        link_ok = not form["link_url"] or form["link_url"].lower().startswith(("http://", "https://"))
        error = None
        if form["kind"] not in kinds:
            error = "Выберите, что вы отправляете."
        elif len(form["description"]) < 10:
            error = "Опишите материал подробнее — минимум 10 символов."
        elif not form["author_name"] or not form["author_contact"]:
            error = "Укажите имя и контакт, чтобы отдел маркетинга мог с вами связаться."
        elif not link_ok:
            error = "Ссылка должна начинаться с http:// или https://."
        elif not request.form.get("consent"):
            error = "Подтвердите согласие на публикацию материалов."
        elif len(uploads) > current_app.config["STUDENT_MAX_FILES"]:
            error = f"Можно прикрепить не больше {current_app.config['STUDENT_MAX_FILES']} файлов."
        elif _too_many_submits():
            error = "Слишком много отправок подряд. Попробуйте через несколько минут."

        if not error:
            stored = []
            for upload in uploads:
                saved = store_student_file(upload)
                if not saved:
                    for path, _, _ in stored:
                        delete_upload(path)
                    error = f"Файл «{upload.filename}» не подходит: нужны фото JPG, PNG, WEBP, HEIC или видео MP4, MOV."
                    break
                stored.append((saved[0], saved[1], upload.filename[:255]))

        if error:
            flash(error, "danger")
        else:
            item = ContentSubmission(consent=True, **form)
            item.files = [SubmissionFile(path=path, size=size, original_name=name) for path, size, name in stored]
            db.session.add(item)
            db.session.commit()
            flash("Спасибо! Материал отправлен в отдел маркетинга. Если он подойдёт, с вами свяжутся.", "success")
            return redirect(url_for("public.student_content"))

    return render_template("public/student_content.html", form=form, kinds=kinds)


@bp.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    services_found, news_found, faqs_found = [], [], []
    if len(q) >= 2:
        like = f"%{q}%"
        services_found = (_published_services().filter(or_(
            Service.name_ru.ilike(like), Service.name_en.ilike(like), Service.name_kk.ilike(like),
            Service.tagline_ru.ilike(like), Service.description_ru.ilike(like),
            Service.benefits_ru.ilike(like),
        )).order_by(Service.position).all())
        news_found = (News.query.filter(News.is_published.is_(True), or_(
            News.title_ru.ilike(like), News.excerpt_ru.ilike(like), News.body_ru.ilike(like),
        )).order_by(News.published_at.desc()).limit(8).all())
        faqs_found = (Faq.query.filter(Faq.is_active.is_(True), or_(
            Faq.question_ru.ilike(like), Faq.answer_ru.ilike(like),
        )).limit(8).all())
    total = len(services_found) + len(news_found) + len(faqs_found)
    return render_template("public/search.html", q=q, services=services_found,
                           news=news_found, faqs=faqs_found, total=total)


@bp.route("/robots.txt")
def robots():
    from flask import Response
    body = "User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /account\n"
    body += f"Sitemap: {url_for('public.sitemap', _external=True)}\n"
    return Response(body, mimetype="text/plain")


@bp.route("/sitemap.xml")
def sitemap():
    from flask import Response

    urls = [url_for("public.index", _external=True),
            url_for("public.services", _external=True),
            url_for("public.courses", _external=True),
            url_for("public.news", _external=True),
            url_for("public.faq", _external=True),
            url_for("public.about", _external=True),
            url_for("public.social", _external=True),
            url_for("public.bonuses", _external=True),
            url_for("public.contact", _external=True),
            url_for("public.library", _external=True),
            url_for("public.student_content", _external=True)]
    urls += [url_for("public.service_detail", slug=s.slug, _external=True)
             for s in _published_services().all()]
    urls += [url_for("public.news_detail", slug=n.slug, _external=True)
             for n in News.query.filter_by(is_published=True).all()]

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f"<url><loc>{u}</loc></url>" for u in urls]
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")
