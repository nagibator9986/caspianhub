"""Панель управления: полное редактирование всего содержимого платформы."""
from __future__ import annotations

import json
from collections import Counter
from datetime import timedelta

from flask import (Blueprint, abort, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import (AuditLog, Category, Certificate, Course, Faq, Feedback,
                      HomeSection, Lesson, LessonProgress, MediaFile, MenuItem,
                      Module, News,
                      Option, Question, Quiz, Service, ServiceEvent,
                      ServiceFaq, ServiceScreenshot, Setting, Tag,
                      Testimonial, User, utcnow)
from ..utils import (clear_settings_cache, delete_upload, form_bool, form_int,
                     log_action, multilang_fields, save_upload, set_setting,
                     slugify, staff_required, unique_slug)

bp = Blueprint("admin", __name__)


@bp.before_request
@staff_required
def guard():
    """Весь раздел доступен только сотрудникам."""
    return None


def _commit(message: str = "Сохранено.", category: str = "success"):
    db.session.commit()
    clear_settings_cache()
    flash(message, category)


def _apply_ml(obj, prefix: str) -> None:
    """Записывает мультиязычные поля из формы в объект."""
    for key, value in multilang_fields(prefix).items():
        if hasattr(obj, key):
            setattr(obj, key, value)


# ═══════════════════════════════ Дашборд ═══════════════════════════════

@bp.route("/")
def dashboard():
    now = utcnow()
    since = now - timedelta(days=30)

    counts = {
        "services": Service.query.count(),
        "published": Service.query.filter_by(is_published=True).count(),
        "courses": Course.query.count(),
        "lessons": Lesson.query.count(),
        "users": User.query.count(),
        "students": User.query.filter_by(role="student").count(),
        "news": News.query.count(),
        "certificates": Certificate.query.count(),
        "feedback_new": Feedback.query.filter_by(status="new").count(),
    }

    top_services = (Service.query.order_by(Service.clicks.desc(), Service.views.desc())
                    .limit(8).all())

    # График активности за 30 дней
    events = (db.session.query(
        func.date(ServiceEvent.created_at).label("day"),
        ServiceEvent.kind,
        func.count(ServiceEvent.id),
    ).filter(ServiceEvent.created_at >= since)
        .group_by("day", ServiceEvent.kind).all())

    chart: dict[str, dict[str, int]] = {}
    for day, kind, count in events:
        chart.setdefault(str(day), {"view": 0, "click": 0})[kind] = count
    days = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]
    chart_data = {
        "labels": [d[8:10] + "." + d[5:7] for d in days],
        "views": [chart.get(d, {}).get("view", 0) for d in days],
        "clicks": [chart.get(d, {}).get("click", 0) for d in days],
    }

    cat_rows = (db.session.query(Category.name_ru, func.count(Service.id))
                .outerjoin(Service, Service.category_id == Category.id)
                .group_by(Category.id).order_by(Category.position).all())
    cat_data = {"labels": [r[0] for r in cat_rows], "values": [r[1] for r in cat_rows]}

    recent_feedback = (Feedback.query.order_by(Feedback.created_at.desc()).limit(5).all())
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_log = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()

    return render_template("admin/dashboard.html", counts=counts, top_services=top_services,
                           chart_data=chart_data, cat_data=cat_data,
                           recent_feedback=recent_feedback, recent_users=recent_users,
                           recent_log=recent_log)


# ═══════════════════════════════ Сервисы ═══════════════════════════════

@bp.route("/services")
def services():
    q = (request.args.get("q") or "").strip()
    cat = request.args.get("cat", type=int)
    query = Service.query
    if q:
        query = query.filter(Service.name_ru.ilike(f"%{q}%"))
    if cat:
        query = query.filter_by(category_id=cat)
    items = query.order_by(Service.position, Service.id).all()
    categories = Category.query.order_by(Category.position).all()
    return render_template("admin/services.html", services=items,
                           categories=categories, q=q, cat=cat)


@bp.route("/services/new", methods=["GET", "POST"])
@bp.route("/services/<int:service_id>", methods=["GET", "POST"])
def service_edit(service_id: int | None = None):
    service = db.session.get(Service, service_id) if service_id else None
    if service_id and not service:
        abort(404)

    if request.method == "POST":
        is_new = service is None
        if is_new:
            service = Service()
            db.session.add(service)

        for prefix in ("name", "tagline", "description", "benefits", "audience", "url_label"):
            _apply_ml(service, prefix)

        slug_input = (request.form.get("slug") or "").strip()
        if is_new or (slug_input and slug_input != service.slug):
            service.slug = unique_slug(Service, slug_input or service.name_ru,
                                        exclude_id=service.id)

        service.category_id = request.form.get("category_id", type=int) or None
        service.url = (request.form.get("url") or "").strip()
        service.mobile_ios_url = (request.form.get("mobile_ios_url") or "").strip()
        service.mobile_android_url = (request.form.get("mobile_android_url") or "").strip()
        service.support_contact = (request.form.get("support_contact") or "").strip()
        service.icon = (request.form.get("icon") or "app-window").strip()
        service.color = (request.form.get("color") or "#EB5A40").strip()
        service.accent = (request.form.get("accent") or "#F9A03F").strip()
        service.status = request.form.get("status") or "active"
        service.access_level = request.form.get("access_level") or "all"
        service.is_published = form_bool("is_published")
        service.is_featured = form_bool("is_featured")
        service.position = form_int("position")
        service.seo_title = (request.form.get("seo_title") or "").strip()
        service.seo_description = (request.form.get("seo_description") or "").strip()

        for field, folder in (("logo", "services"), ("cover", "services")):
            uploaded = request.files.get(field)
            if uploaded and uploaded.filename:
                saved = save_upload(uploaded, folder=folder, images_only=True)
                if saved:
                    delete_upload(getattr(service, field))
                    setattr(service, field, saved)
            if form_bool(f"remove_{field}"):
                delete_upload(getattr(service, field))
                setattr(service, field, "")

        # Теги — строка через запятую
        raw_tags = [t.strip() for t in (request.form.get("tags") or "").split(",") if t.strip()]
        service.tags = []
        for name in raw_tags[:12]:
            slug = slugify(name)
            tag = Tag.query.filter_by(slug=slug).first()
            if not tag:
                tag = Tag(slug=slug, name_ru=name)
                db.session.add(tag)
            service.tags.append(tag)

        log_action("create" if is_new else "update", "service", service.id, service.name_ru)
        _commit("Сервис создан." if is_new else "Сервис обновлён.")
        return redirect(url_for("admin.service_edit", service_id=service.id))

    categories = Category.query.order_by(Category.position).all()
    return render_template("admin/service_form.html", service=service, categories=categories)


@bp.route("/services/<int:service_id>/delete", methods=["POST"])
def service_delete(service_id: int):
    service = db.session.get(Service, service_id) or abort(404)
    name = service.name_ru
    delete_upload(service.logo)
    delete_upload(service.cover)
    db.session.delete(service)
    log_action("delete", "service", service_id, name)
    _commit(f"Сервис «{name}» удалён.")
    return redirect(url_for("admin.services"))


@bp.route("/services/<int:service_id>/screenshots", methods=["POST"])
def service_screenshots(service_id: int):
    service = db.session.get(Service, service_id) or abort(404)
    for file in request.files.getlist("screenshots"):
        if file and file.filename:
            saved = save_upload(file, folder="services", images_only=True)
            if saved:
                db.session.add(ServiceScreenshot(
                    service_id=service.id, image=saved,
                    position=len(service.screenshots) + 1,
                ))
    _commit("Скриншоты добавлены.")
    return redirect(url_for("admin.service_edit", service_id=service.id) + "#screenshots")


@bp.route("/screenshots/<int:shot_id>/delete", methods=["POST"])
def screenshot_delete(shot_id: int):
    shot = db.session.get(ServiceScreenshot, shot_id) or abort(404)
    service_id = shot.service_id
    delete_upload(shot.image)
    db.session.delete(shot)
    _commit("Скриншот удалён.")
    return redirect(url_for("admin.service_edit", service_id=service_id) + "#screenshots")


@bp.route("/services/<int:service_id>/faq", methods=["POST"])
def service_faq_add(service_id: int):
    service = db.session.get(Service, service_id) or abort(404)
    item = ServiceFaq(service_id=service.id, position=len(service.faqs) + 1)
    _apply_ml(item, "question")
    _apply_ml(item, "answer")
    if not item.question_ru:
        flash("Введите вопрос.", "danger")
    else:
        db.session.add(item)
        _commit("Вопрос добавлен.")
    return redirect(url_for("admin.service_edit", service_id=service.id) + "#faq")


@bp.route("/service-faq/<int:faq_id>/delete", methods=["POST"])
def service_faq_delete(faq_id: int):
    item = db.session.get(ServiceFaq, faq_id) or abort(404)
    service_id = item.service_id
    db.session.delete(item)
    _commit("Вопрос удалён.")
    return redirect(url_for("admin.service_edit", service_id=service_id) + "#faq")


# ═══════════════════════════════ Категории ═══════════════════════════════

@bp.route("/categories", methods=["GET", "POST"])
def categories():
    if request.method == "POST":
        cat_id = request.form.get("id", type=int)
        cat = db.session.get(Category, cat_id) if cat_id else Category()
        if not cat_id:
            db.session.add(cat)
        _apply_ml(cat, "name")
        _apply_ml(cat, "description")
        slug_input = (request.form.get("slug") or "").strip()
        if not cat_id or (slug_input and slug_input != cat.slug):
            cat.slug = unique_slug(Category, slug_input or cat.name_ru, exclude_id=cat.id)
        cat.icon = (request.form.get("icon") or "layout-grid").strip()
        cat.color = (request.form.get("color") or "#EB5A40").strip()
        cat.position = form_int("position")
        cat.is_active = form_bool("is_active")
        _commit("Категория сохранена.")
        return redirect(url_for("admin.categories"))

    items = Category.query.order_by(Category.position).all()
    return render_template("admin/categories.html", categories=items)


@bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
def category_delete(cat_id: int):
    cat = db.session.get(Category, cat_id) or abort(404)
    if cat.services:
        flash("Сначала перенесите сервисы в другую категорию.", "danger")
    else:
        db.session.delete(cat)
        _commit("Категория удалена.")
    return redirect(url_for("admin.categories"))


# ═══════════════════════════════ Курсы ═══════════════════════════════

@bp.route("/courses")
def courses():
    items = Course.query.join(Service, isouter=True).order_by(Service.position).all()
    orphan_services = (Service.query.filter(~Service.id.in_(
        db.session.query(Course.service_id).filter(Course.service_id.isnot(None))
    )).order_by(Service.position).all())
    return render_template("admin/courses.html", courses=items, orphans=orphan_services)


@bp.route("/courses/new", methods=["GET", "POST"])
@bp.route("/courses/<int:course_id>", methods=["GET", "POST"])
def course_edit(course_id: int | None = None):
    course = db.session.get(Course, course_id) if course_id else None
    if course_id and not course:
        abort(404)

    if request.method == "POST":
        is_new = course is None
        if is_new:
            course = Course()
            db.session.add(course)

        for prefix in ("title", "summary", "outcomes"):
            _apply_ml(course, prefix)

        course.service_id = request.form.get("service_id", type=int) or None
        slug_input = (request.form.get("slug") or "").strip()
        if is_new or (slug_input and slug_input != course.slug):
            course.slug = unique_slug(Course, slug_input or course.title_ru, exclude_id=course.id)
        course.level = request.form.get("level") or "beginner"
        course.duration_min = form_int("duration_min", 15)
        course.pass_score = form_int("pass_score", 70)
        course.is_published = form_bool("is_published")
        course.certificate_enabled = form_bool("certificate_enabled")

        cover = request.files.get("cover")
        if cover and cover.filename:
            saved = save_upload(cover, folder="services", images_only=True)
            if saved:
                delete_upload(course.cover)
                course.cover = saved

        log_action("create" if is_new else "update", "course", course.id, course.title_ru)
        _commit("Курс создан." if is_new else "Курс обновлён.")
        return redirect(url_for("admin.course_edit", course_id=course.id))

    services_list = Service.query.order_by(Service.position).all()
    return render_template("admin/course_form.html", course=course, services=services_list)


@bp.route("/courses/<int:course_id>/delete", methods=["POST"])
def course_delete(course_id: int):
    course = db.session.get(Course, course_id) or abort(404)
    title = course.title_ru
    db.session.delete(course)
    log_action("delete", "course", course_id, title)
    _commit(f"Курс «{title}» удалён.")
    return redirect(url_for("admin.courses"))


@bp.route("/courses/<int:course_id>/modules", methods=["POST"])
def module_add(course_id: int):
    course = db.session.get(Course, course_id) or abort(404)
    module = Module(course_id=course.id, position=len(course.modules) + 1)
    _apply_ml(module, "title")
    _apply_ml(module, "description")
    if not module.title_ru:
        flash("Введите название модуля.", "danger")
    else:
        db.session.add(module)
        _commit("Модуль добавлен.")
    return redirect(url_for("admin.course_edit", course_id=course.id) + "#modules")


@bp.route("/modules/<int:module_id>/update", methods=["POST"])
def module_update(module_id: int):
    module = db.session.get(Module, module_id) or abort(404)
    _apply_ml(module, "title")
    _apply_ml(module, "description")
    module.position = form_int("position", module.position)
    _commit("Модуль обновлён.")
    return redirect(url_for("admin.course_edit", course_id=module.course_id) + "#modules")


@bp.route("/modules/<int:module_id>/delete", methods=["POST"])
def module_delete(module_id: int):
    module = db.session.get(Module, module_id) or abort(404)
    course_id = module.course_id
    db.session.delete(module)
    _commit("Модуль удалён.")
    return redirect(url_for("admin.course_edit", course_id=course_id) + "#modules")


@bp.route("/modules/<int:module_id>/lessons/new", methods=["GET", "POST"])
@bp.route("/lessons/<int:lesson_id>", methods=["GET", "POST"])
def lesson_edit(module_id: int | None = None, lesson_id: int | None = None):
    lesson = db.session.get(Lesson, lesson_id) if lesson_id else None
    if lesson_id and not lesson:
        abort(404)
    module = lesson.module if lesson else (db.session.get(Module, module_id) or abort(404))

    if request.method == "POST":
        is_new = lesson is None
        if is_new:
            lesson = Lesson(module_id=module.id, position=len(module.lessons) + 1)
            db.session.add(lesson)

        for prefix in ("title", "content", "tip"):
            _apply_ml(lesson, prefix)
        lesson.slug = unique_slug(Lesson, lesson.title_ru, exclude_id=lesson.id)
        lesson.media_type = request.form.get("media_type") or "none"
        lesson.media_url = (request.form.get("media_url") or "").strip()
        lesson.duration_min = form_int("duration_min", 3)
        lesson.position = form_int("position", lesson.position or 1)

        media = request.files.get("media_file")
        if media and media.filename:
            saved = save_upload(media, folder="media", images_only=True)
            if saved:
                lesson.media_url = "/static/" + saved
                lesson.media_type = "image"

        _commit("Урок создан." if is_new else "Урок обновлён.")
        return redirect(url_for("admin.lesson_edit", lesson_id=lesson.id))

    return render_template("admin/lesson_form.html", lesson=lesson, module=module)


@bp.route("/lessons/<int:lesson_id>/delete", methods=["POST"])
def lesson_delete(lesson_id: int):
    lesson = db.session.get(Lesson, lesson_id) or abort(404)
    course_id = lesson.module.course_id
    db.session.delete(lesson)
    _commit("Урок удалён.")
    return redirect(url_for("admin.course_edit", course_id=course_id) + "#modules")


# ═══════════════════════════════ Тесты ═══════════════════════════════

@bp.route("/courses/<int:course_id>/quiz", methods=["GET", "POST"])
def quiz_edit(course_id: int):
    course = db.session.get(Course, course_id) or abort(404)
    quiz = course.quiz

    if request.method == "POST":
        if not quiz:
            quiz = Quiz(course_id=course.id)
            db.session.add(quiz)
        _apply_ml(quiz, "title")
        _apply_ml(quiz, "description")
        quiz.pass_score = form_int("pass_score", 70)
        quiz.time_limit_min = form_int("time_limit_min", 0)
        _commit("Тест сохранён.")
        return redirect(url_for("admin.quiz_edit", course_id=course.id))

    return render_template("admin/quiz_form.html", course=course, quiz=quiz)


@bp.route("/quiz/<int:quiz_id>/questions", methods=["POST"])
def question_add(quiz_id: int):
    quiz = db.session.get(Quiz, quiz_id) or abort(404)
    question = Question(quiz_id=quiz.id, position=len(quiz.questions) + 1)
    _apply_ml(question, "text")
    _apply_ml(question, "explanation")
    if not question.text_ru:
        flash("Введите текст вопроса.", "danger")
        return redirect(url_for("admin.quiz_edit", course_id=quiz.course_id))

    db.session.add(question)
    db.session.flush()

    correct = request.form.get("correct", type=int) or 1
    for i in range(1, 5):
        text = (request.form.get(f"option{i}") or "").strip()
        if text:
            db.session.add(Option(question_id=question.id, text_ru=text,
                                   is_correct=(i == correct), position=i))
    _commit("Вопрос добавлен.")
    return redirect(url_for("admin.quiz_edit", course_id=quiz.course_id))


@bp.route("/questions/<int:question_id>/delete", methods=["POST"])
def question_delete(question_id: int):
    question = db.session.get(Question, question_id) or abort(404)
    course_id = question.quiz.course_id
    db.session.delete(question)
    _commit("Вопрос удалён.")
    return redirect(url_for("admin.quiz_edit", course_id=course_id))


@bp.route("/questions/<int:question_id>/update", methods=["POST"])
def question_update(question_id: int):
    question = db.session.get(Question, question_id) or abort(404)
    _apply_ml(question, "text")
    _apply_ml(question, "explanation")
    correct = request.form.get("correct", type=int)
    for option in question.options:
        new_text = (request.form.get(f"option_{option.id}") or "").strip()
        if new_text:
            option.text_ru = new_text
        option.is_correct = (option.id == correct)
    _commit("Вопрос обновлён.")
    return redirect(url_for("admin.quiz_edit", course_id=question.quiz.course_id))


# ═══════════════════════════════ Новости ═══════════════════════════════

@bp.route("/news")
def news():
    items = News.query.order_by(News.published_at.desc()).all()
    return render_template("admin/news.html", items=items)


@bp.route("/news/new", methods=["GET", "POST"])
@bp.route("/news/<int:news_id>", methods=["GET", "POST"])
def news_edit(news_id: int | None = None):
    item = db.session.get(News, news_id) if news_id else None
    if news_id and not item:
        abort(404)

    if request.method == "POST":
        is_new = item is None
        if is_new:
            item = News()
            db.session.add(item)

        for prefix in ("title", "excerpt", "body"):
            _apply_ml(item, prefix)
        slug_input = (request.form.get("slug") or "").strip()
        if is_new or (slug_input and slug_input != item.slug):
            item.slug = unique_slug(News, slug_input or item.title_ru, exclude_id=item.id)
        item.kind = request.form.get("kind") or "news"
        item.is_published = form_bool("is_published")
        item.is_pinned = form_bool("is_pinned")

        published = request.form.get("published_at")
        if published:
            from datetime import datetime, timezone as tz
            try:
                item.published_at = datetime.fromisoformat(published).replace(tzinfo=tz.utc)
            except ValueError:
                pass

        cover = request.files.get("cover")
        if cover and cover.filename:
            saved = save_upload(cover, folder="news", images_only=True)
            if saved:
                delete_upload(item.cover)
                item.cover = saved
        if form_bool("remove_cover"):
            delete_upload(item.cover)
            item.cover = ""

        log_action("create" if is_new else "update", "news", item.id, item.title_ru)
        _commit("Новость создана." if is_new else "Новость обновлена.")
        return redirect(url_for("admin.news_edit", news_id=item.id))

    return render_template("admin/news_form.html", item=item)


@bp.route("/news/<int:news_id>/delete", methods=["POST"])
def news_delete(news_id: int):
    item = db.session.get(News, news_id) or abort(404)
    delete_upload(item.cover)
    db.session.delete(item)
    _commit("Новость удалена.")
    return redirect(url_for("admin.news"))


# ═══════════════════════════════ FAQ ═══════════════════════════════

@bp.route("/faq", methods=["GET", "POST"])
def faq():
    if request.method == "POST":
        faq_id = request.form.get("id", type=int)
        item = db.session.get(Faq, faq_id) if faq_id else Faq()
        if not faq_id:
            item.position = Faq.query.count() + 1
            db.session.add(item)
        _apply_ml(item, "question")
        _apply_ml(item, "answer")
        item.category = (request.form.get("category") or "Общее").strip()
        item.is_active = form_bool("is_active")
        if request.form.get("position"):
            item.position = form_int("position", item.position)
        _commit("Вопрос сохранён.")
        return redirect(url_for("admin.faq"))

    items = Faq.query.order_by(Faq.position).all()
    return render_template("admin/faq.html", items=items)


@bp.route("/faq/<int:faq_id>/delete", methods=["POST"])
def faq_delete(faq_id: int):
    item = db.session.get(Faq, faq_id) or abort(404)
    db.session.delete(item)
    _commit("Вопрос удалён.")
    return redirect(url_for("admin.faq"))


# ═══════════════════════════════ Отзывы ═══════════════════════════════

@bp.route("/testimonials", methods=["GET", "POST"])
def testimonials():
    if request.method == "POST":
        item_id = request.form.get("id", type=int)
        item = db.session.get(Testimonial, item_id) if item_id else Testimonial()
        if not item_id:
            item.position = Testimonial.query.count() + 1
            db.session.add(item)
        item.author = (request.form.get("author") or "").strip()[:160]
        _apply_ml(item, "role")
        _apply_ml(item, "text")
        item.rating = max(1, min(5, form_int("rating", 5)))
        item.is_active = form_bool("is_active")
        avatar = request.files.get("avatar")
        if avatar and avatar.filename:
            saved = save_upload(avatar, folder="media", images_only=True)
            if saved:
                delete_upload(item.avatar)
                item.avatar = saved
        _commit("Отзыв сохранён.")
        return redirect(url_for("admin.testimonials"))

    items = Testimonial.query.order_by(Testimonial.position).all()
    return render_template("admin/testimonials.html", items=items)


@bp.route("/testimonials/<int:item_id>/delete", methods=["POST"])
def testimonial_delete(item_id: int):
    item = db.session.get(Testimonial, item_id) or abort(404)
    delete_upload(item.avatar)
    db.session.delete(item)
    _commit("Отзыв удалён.")
    return redirect(url_for("admin.testimonials"))


# ═══════════════════════════════ Меню и главная ═══════════════════════════════

@bp.route("/menu", methods=["GET", "POST"])
def menu():
    if request.method == "POST":
        item_id = request.form.get("id", type=int)
        item = db.session.get(MenuItem, item_id) if item_id else MenuItem()
        if not item_id:
            db.session.add(item)
        _apply_ml(item, "title")
        item.location = request.form.get("location") or "header"
        item.url = (request.form.get("url") or "/").strip()
        item.icon = (request.form.get("icon") or "").strip()
        item.is_external = form_bool("is_external")
        item.is_active = form_bool("is_active")
        item.position = form_int("position")
        _commit("Пункт меню сохранён.")
        return redirect(url_for("admin.menu"))

    groups = {loc: MenuItem.query.filter_by(location=loc).order_by(MenuItem.position).all()
              for loc in ("header", "footer", "quick")}
    return render_template("admin/menu.html", groups=groups)


@bp.route("/menu/<int:item_id>/delete", methods=["POST"])
def menu_delete(item_id: int):
    item = db.session.get(MenuItem, item_id) or abort(404)
    db.session.delete(item)
    _commit("Пункт меню удалён.")
    return redirect(url_for("admin.menu"))


@bp.route("/home", methods=["GET", "POST"])
def home_sections():
    if request.method == "POST":
        for section in HomeSection.query.all():
            prefix = f"s{section.id}_"
            for field in ("title", "subtitle"):
                for lang in ("ru", "kk", "en"):
                    value = request.form.get(f"{prefix}{field}_{lang}")
                    if value is not None:
                        setattr(section, f"{field}_{lang}", value.strip())
            section.is_active = request.form.get(f"{prefix}is_active") in ("on", "1")
            try:
                section.position = int(request.form.get(f"{prefix}position") or section.position)
            except ValueError:
                pass
        _commit("Блоки главной страницы обновлены.")
        return redirect(url_for("admin.home_sections"))

    sections = HomeSection.query.order_by(HomeSection.position).all()
    return render_template("admin/home_sections.html", sections=sections)


# ═══════════════════════════════ Настройки ═══════════════════════════════

@bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        for row in Setting.query.all():
            if row.value_type == "bool":
                row.value = "true" if request.form.get(row.key) in ("on", "1", "true") else "false"
            elif row.value_type == "image":
                uploaded = request.files.get(row.key)
                if uploaded and uploaded.filename:
                    saved = save_upload(uploaded, folder="media", images_only=True)
                    if saved:
                        row.value = "/static/" + saved
                elif request.form.get(f"{row.key}__text") is not None:
                    row.value = request.form.get(f"{row.key}__text").strip()
            else:
                value = request.form.get(row.key)
                if value is not None:
                    row.value = value.strip()
        log_action("update", "settings", None, "Настройки сайта")
        _commit("Настройки сохранены.")
        return redirect(url_for("admin.settings") + "#" + (request.form.get("active_group") or "brand"))

    rows = Setting.query.order_by(Setting.group, Setting.position).all()
    groups: dict[str, list] = {}
    for row in rows:
        groups.setdefault(row.group, []).append(row)
    order = ["brand", "hero", "general", "contacts", "social", "footer", "seo", "features"]
    ordered = {k: groups[k] for k in order if k in groups}
    ordered.update({k: v for k, v in groups.items() if k not in ordered})
    return render_template("admin/settings.html", groups=ordered)


# ═══════════════════════════════ Пользователи ═══════════════════════════════

@bp.route("/users")
def users():
    q = (request.args.get("q") or "").strip()
    role = request.args.get("role")
    query = User.query
    if q:
        query = query.filter(db.or_(User.full_name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    if role in ("admin", "editor", "student"):
        query = query.filter_by(role=role)
    items = query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=items, q=q, role=role)


@bp.route("/users/<int:user_id>", methods=["GET", "POST"])
def user_edit(user_id: int):
    user = db.session.get(User, user_id) or abort(404)

    if request.method == "POST":
        if not current_user.is_admin:
            abort(403)
        user.full_name = (request.form.get("full_name") or "").strip()[:160]
        user.group_name = (request.form.get("group_name") or "").strip()[:60]
        user.specialty = (request.form.get("specialty") or "").strip()[:120]
        new_role = request.form.get("role")
        if new_role in ("admin", "editor", "student"):
            if user.id == current_user.id and new_role != "admin":
                flash("Нельзя снять с себя права администратора.", "danger")
            else:
                user.role = new_role
        user.is_active_flag = form_bool("is_active_flag")
        new_password = request.form.get("new_password") or ""
        if new_password:
            if len(new_password) < 6:
                flash("Пароль должен быть не короче 6 символов.", "danger")
            else:
                user.set_password(new_password)
                flash("Пароль пользователя изменён.", "info")
        log_action("update", "user", user.id, user.email)
        _commit("Пользователь обновлён.")
        return redirect(url_for("admin.user_edit", user_id=user.id))

    certificates = Certificate.query.filter_by(user_id=user.id).all()
    done = sum(1 for p in user.progress if p.completed)
    return render_template("admin/user_form.html", user=user,
                           certificates=certificates, done_lessons=done)


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
def user_delete(user_id: int):
    if not current_user.is_admin:
        abort(403)
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash("Нельзя удалить собственную учётную запись.", "danger")
        return redirect(url_for("admin.users"))
    email = user.email
    db.session.delete(user)
    log_action("delete", "user", user_id, email)
    _commit(f"Пользователь {email} удалён.")
    return redirect(url_for("admin.users"))


# ═══════════════════════════════ Обращения ═══════════════════════════════

@bp.route("/feedback")
def feedback():
    status = request.args.get("status")
    query = Feedback.query
    if status in ("new", "in_progress", "done"):
        query = query.filter_by(status=status)
    items = query.order_by(Feedback.created_at.desc()).all()
    counts = Counter(f.status for f in Feedback.query.all())
    return render_template("admin/feedback.html", items=items, status=status, counts=counts)


@bp.route("/feedback/<int:item_id>", methods=["POST"])
def feedback_update(item_id: int):
    item = db.session.get(Feedback, item_id) or abort(404)
    new_status = request.form.get("status")
    if new_status in ("new", "in_progress", "done"):
        item.status = new_status
    item.admin_note = (request.form.get("admin_note") or "").strip()[:2000]
    _commit("Обращение обновлено.")
    return redirect(url_for("admin.feedback"))


@bp.route("/feedback/<int:item_id>/delete", methods=["POST"])
def feedback_delete(item_id: int):
    item = db.session.get(Feedback, item_id) or abort(404)
    db.session.delete(item)
    _commit("Обращение удалено.")
    return redirect(url_for("admin.feedback"))


# ═══════════════════════════════ Медиа ═══════════════════════════════

@bp.route("/media", methods=["GET", "POST"])
def media():
    if request.method == "POST":
        saved_count = 0
        for file in request.files.getlist("files"):
            if file and file.filename and save_upload(file, folder="media"):
                saved_count += 1
        _commit(f"Загружено файлов: {saved_count}." if saved_count else "Ничего не загружено.",
                "success" if saved_count else "danger")
        return redirect(url_for("admin.media"))

    items = MediaFile.query.order_by(MediaFile.created_at.desc()).all()
    total = sum(m.size or 0 for m in items)
    return render_template("admin/media.html", items=items, total=total)


@bp.route("/media/<int:item_id>/delete", methods=["POST"])
def media_delete(item_id: int):
    item = db.session.get(MediaFile, item_id) or abort(404)
    delete_upload(item.path)
    db.session.delete(item)
    _commit("Файл удалён.")
    return redirect(url_for("admin.media"))


# ═══════════════════════════════ Аналитика и журнал ═══════════════════════════════

@bp.route("/analytics")
def analytics():
    services_list = Service.query.order_by(Service.clicks.desc()).all()
    courses_list = Course.query.filter_by(is_published=True).all()
    course_stats = []
    for course in courses_list:
        lesson_ids = [lesson.id for lesson in course.lessons] or [0]
        learners = (db.session.query(func.count(func.distinct(LessonProgress.user_id)))
                    .filter(LessonProgress.lesson_id.in_(lesson_ids),
                            LessonProgress.completed.is_(True)).scalar() or 0)
        course_stats.append({
            "course": course,
            "learners": learners,
            "certificates": Certificate.query.filter_by(course_id=course.id).count(),
            "lessons": course.lesson_count,
        })
    course_stats.sort(key=lambda r: r["learners"], reverse=True)
    top_users = (db.session.query(User, func.count(Certificate.id).label("n"))
                 .outerjoin(Certificate, Certificate.user_id == User.id)
                 .group_by(User.id).order_by(func.count(Certificate.id).desc())
                 .limit(10).all())
    return render_template("admin/analytics.html", services=services_list,
                           course_stats=course_stats, top_users=top_users)


@bp.route("/log")
def audit_log():
    items = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template("admin/log.html", items=items)


# ═══════════════════════════════ Сортировка (drag&drop) ═══════════════════════════════

MODELS_FOR_REORDER = {
    "service": Service, "category": Category, "menu": MenuItem,
    "module": Module, "lesson": Lesson, "faq": Faq,
    "testimonial": Testimonial, "screenshot": ServiceScreenshot,
    "service_faq": ServiceFaq, "question": Question, "home_section": HomeSection,
}


@bp.route("/reorder/<entity>", methods=["POST"])
def reorder(entity: str):
    model = MODELS_FOR_REORDER.get(entity)
    if not model:
        return jsonify({"error": "unknown_entity"}), 400
    order = (request.get_json(silent=True) or {}).get("order") or []
    for index, raw_id in enumerate(order, start=1):
        obj = db.session.get(model, int(raw_id))
        if obj is not None:
            obj.position = index
    db.session.commit()
    clear_settings_cache()
    return jsonify({"ok": True, "count": len(order)})
