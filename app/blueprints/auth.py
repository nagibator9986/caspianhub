"""Регистрация, вход, выход."""
from __future__ import annotations

import re

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models import User
from ..utils import log_action, safe_next

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Неверная почта или пароль.", "danger")
            return render_template("auth/login.html", email=email), 401
        if not user.is_active:
            flash("Учётная запись заблокирована. Обратитесь в поддержку.", "danger")
            return render_template("auth/login.html", email=email), 403

        login_user(user, remember=remember)
        session["lang"] = user.locale or "ru"
        log_action("login", "user", user.id, f"Вход: {user.email}")
        db.session.commit()

        flash(f"С возвращением, {user.full_name or 'студент'}!", "success")
        target = safe_next(request.args.get("next") or request.form.get("next"))
        if target == "/" and user.is_staff:
            target = url_for("admin.dashboard")
        return redirect(target)

    return render_template("auth/login.html", email="")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = {"full_name": "", "email": "", "group_name": "", "specialty": ""}

    if request.method == "POST":
        form = {k: (request.form.get(k) or "").strip() for k in form}
        email = form["email"].lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        errors = []
        if len(form["full_name"]) < 3:
            errors.append("Укажите имя и фамилию.")
        if not EMAIL_RE.match(email):
            errors.append("Проверьте адрес электронной почты.")
        if len(password) < 6:
            errors.append("Пароль должен быть не короче 6 символов.")
        if password != password2:
            errors.append("Пароли не совпадают.")
        if User.query.filter_by(email=email).first():
            errors.append("Пользователь с такой почтой уже зарегистрирован.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html", form=form), 400

        user = User(email=email, full_name=form["full_name"],
                    group_name=form["group_name"], specialty=form["specialty"],
                    role="student")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user, remember=True)
        flash("Добро пожаловать в Caspian College Hub!", "success")
        return redirect(url_for("account.dashboard"))

    return render_template("auth/register.html", form=form)


@bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("public.index"))
