"""Конфигурация Caspian College Hub."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'caspianhub.db'}")
    # Railway/Heroku отдают postgres:// — SQLAlchemy 2 понимает только postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "ccu-hub-dev-secret-change-me-in-production")

    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Загрузка файлов
    UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 МБ
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg", "pdf", "docx", "xlsx", "pptx"}
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}

    # Сессии
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 14
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 30

    # Локализация
    LANGUAGES = {"ru": "Русский", "kk": "Қазақша", "en": "English"}
    DEFAULT_LANGUAGE = "ru"

    # Пагинация
    ITEMS_PER_PAGE = 12
    ADMIN_ITEMS_PER_PAGE = 20

    WTF_CSRF_TIME_LIMIT = None


class DevelopmentConfig(Config):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


configs = {"development": DevelopmentConfig, "production": ProductionConfig, "default": DevelopmentConfig}
