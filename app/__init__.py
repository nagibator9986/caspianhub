"""Фабрика приложения Caspian College Hub."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from flask import Flask, g, render_template, request, session

from .extensions import csrf, db, login_manager, migrate


def create_app(config_name: str = "default") -> Flask:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import configs

    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(configs.get(config_name, configs["default"]))

    if not app.debug:
        # За прокси Railway: корректные https-ссылки и IP клиента
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    _register_blueprints(app)
    _register_hooks(app)
    _register_jinja(app)
    _register_errors(app)
    _register_cli(app)

    return app


def _register_blueprints(app: Flask) -> None:
    from .blueprints.public import bp as public_bp
    from .blueprints.auth import bp as auth_bp
    from .blueprints.learn import bp as learn_bp
    from .blueprints.account import bp as account_bp
    from .blueprints.admin import bp as admin_bp
    from .blueprints.api import bp as api_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(learn_bp, url_prefix="/learn")
    app.register_blueprint(account_bp, url_prefix="/account")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")


def _register_hooks(app: Flask) -> None:
    from flask_login import current_user

    from .models import User, utcnow

    @app.before_request
    def set_language():
        lang = request.args.get("lang")
        if lang in app.config["LANGUAGES"]:
            session["lang"] = lang
            session.permanent = True
        g.lang = session.get("lang") or app.config["DEFAULT_LANGUAGE"]

    @app.before_request
    def touch_user():
        if current_user.is_authenticated:
            now = utcnow()
            last = current_user.last_seen
            if last is not None and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if last is None or (now - last).total_seconds() > 300:
                current_user.last_seen = now
                db.session.commit()

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    @app.teardown_appcontext
    def remove_session(exc=None):
        if exc:
            db.session.rollback()
        db.session.remove()


def _register_jinja(app: Flask) -> None:
    from flask_wtf.csrf import generate_csrf

    from .i18n import t as translate
    from .models import Category, MenuItem, Service
    from .utils import (date_ru, human_date, plural_ru, render_markdown, setting,
                        setting_bool, setting_int, strip_markdown)

    app.jinja_env.filters["markdown"] = render_markdown
    app.jinja_env.filters["excerpt"] = strip_markdown
    app.jinja_env.filters["date_ru"] = date_ru
    app.jinja_env.filters["dt"] = human_date
    app.jinja_env.filters["plural"] = plural_ru
    app.jinja_env.filters["tojson_safe"] = lambda v: json.dumps(v, ensure_ascii=False)
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    @app.context_processor
    def inject_globals():
        lang = getattr(g, "lang", "ru")

        def _t(key: str) -> str:
            return translate(key, lang)

        def nav_items(location: str = "header"):
            try:
                return (MenuItem.query
                        .filter_by(location=location, is_active=True, parent_id=None)
                        .order_by(MenuItem.position).all())
            except Exception:
                return []

        def all_categories():
            try:
                return Category.query.filter_by(is_active=True).order_by(Category.position).all()
            except Exception:
                return []

        return {
            "t": _t,
            "lang": lang,
            "LANGUAGES": app.config["LANGUAGES"],
            "setting": setting,
            "setting_bool": setting_bool,
            "setting_int": setting_int,
            "nav_items": nav_items,
            "all_categories": all_categories,
            "csrf_token": generate_csrf,
            "now": datetime.now(timezone.utc),
            "Service": Service,
        }


def _register_errors(app: Flask) -> None:
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/error.html", code=403,
                               title="Доступ закрыт",
                               message="У вашей учётной записи нет прав на этот раздел."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/error.html", code=404,
                               title="Страница не найдена",
                               message="Возможно, ссылка устарела или сервис переехал."), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/error.html", code=413,
                               title="Файл слишком большой",
                               message="Максимальный размер загружаемого файла — 16 МБ."), 413

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/error.html", code=500,
                               title="Что-то пошло не так",
                               message="Мы уже знаем о проблеме. Попробуйте обновить страницу."), 500


def _register_cli(app: Flask) -> None:
    import click

    @app.cli.command("init-db")
    def init_db():
        """Создать таблицы и наполнить базу демо-данными."""
        from seed import run_seed

        db.create_all()
        run_seed()
        click.echo("База данных готова.")

    @app.cli.command("reset-db")
    def reset_db():
        """Полностью пересоздать базу."""
        from seed import run_seed

        db.drop_all()
        db.create_all()
        run_seed()
        click.echo("База пересоздана.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--name", default="Администратор")
    def create_admin(email, password, name):
        """Создать администратора."""
        from .models import User

        if User.query.filter_by(email=email).first():
            click.echo("Пользователь с такой почтой уже существует.")
            return
        user = User(email=email, full_name=name, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Администратор {email} создан.")
