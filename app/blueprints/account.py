"""Личный кабинет студента: прогресс, избранное, сертификаты, профиль."""
from __future__ import annotations

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Certificate, Course, LessonProgress, QuizAttempt, Service
from ..utils import delete_upload, save_upload

bp = Blueprint("account", __name__)


@bp.route("/")
@login_required
def dashboard():
    favorites = [f.service for f in current_user.favorites if f.service and f.service.is_published]

    started_ids = {p.lesson.course.id for p in current_user.progress
                   if p.lesson and p.lesson.course}
    courses = [c for c in Course.query.filter(Course.id.in_(started_ids or [0])).all()
               if c.is_published]
    in_progress = [(c, c.progress_for(current_user)) for c in courses]
    in_progress.sort(key=lambda x: x[1], reverse=True)

    certificates = (Certificate.query.filter_by(user_id=current_user.id)
                    .order_by(Certificate.issued_at.desc()).all())

    done_lessons = LessonProgress.query.filter_by(
        user_id=current_user.id, completed=True).count()
    attempts = (QuizAttempt.query.filter_by(user_id=current_user.id)
                .order_by(QuizAttempt.created_at.desc()).limit(5).all())

    recommended = (Service.query.filter(
        Service.is_published.is_(True),
        Service.id.notin_([s.id for s in favorites] or [0]),
    ).order_by(Service.is_featured.desc(), Service.views.desc()).limit(3).all())

    return render_template("account/dashboard.html",
                           favorites=favorites, in_progress=in_progress,
                           certificates=certificates, done_lessons=done_lessons,
                           attempts=attempts, recommended=recommended)


@bp.route("/favorites")
@login_required
def favorites():
    items = [f.service for f in
             sorted(current_user.favorites, key=lambda f: f.created_at, reverse=True)
             if f.service and f.service.is_published]
    return render_template("account/favorites.html", services=items)


@bp.route("/learning")
@login_required
def learning():
    all_courses = (Course.query.filter_by(is_published=True).all())
    rows = []
    for course in all_courses:
        pct = course.progress_for(current_user)
        if pct > 0:
            rows.append((course, pct))
    rows.sort(key=lambda x: x[1], reverse=True)
    available = [c for c in all_courses if c.progress_for(current_user) == 0]
    return render_template("account/learning.html", rows=rows, available=available)


@bp.route("/certificates")
@login_required
def certificates():
    items = (Certificate.query.filter_by(user_id=current_user.id)
             .order_by(Certificate.issued_at.desc()).all())
    return render_template("account/certificates.html", certificates=items)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        action = request.form.get("action", "profile")

        if action == "password":
            current = request.form.get("current_password") or ""
            new = request.form.get("new_password") or ""
            repeat = request.form.get("new_password2") or ""
            if not current_user.check_password(current):
                flash("Текущий пароль указан неверно.", "danger")
            elif len(new) < 6:
                flash("Новый пароль должен быть не короче 6 символов.", "danger")
            elif new != repeat:
                flash("Новые пароли не совпадают.", "danger")
            else:
                current_user.set_password(new)
                db.session.commit()
                flash("Пароль обновлён.", "success")
            return redirect(url_for("account.profile"))

        current_user.full_name = (request.form.get("full_name") or "").strip()[:160]
        current_user.group_name = (request.form.get("group_name") or "").strip()[:60]
        current_user.specialty = (request.form.get("specialty") or "").strip()[:120]
        current_user.bio = (request.form.get("bio") or "").strip()[:1000]
        locale = request.form.get("locale")
        if locale in ("ru", "kk", "en"):
            current_user.locale = locale
            session["lang"] = locale

        avatar = request.files.get("avatar")
        if avatar and avatar.filename:
            saved = save_upload(avatar, folder="media", images_only=True)
            if saved:
                delete_upload(current_user.avatar)
                current_user.avatar = saved

        db.session.commit()
        flash("Профиль сохранён.", "success")
        return redirect(url_for("account.profile"))

    return render_template("account/profile.html")
