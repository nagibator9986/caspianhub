"""Вспомогательные функции: настройки, Markdown, загрузка файлов, доступ."""
from __future__ import annotations

import os
import re
import unicodedata
import uuid
from functools import wraps
from pathlib import Path

import bleach
import markdown as md
from flask import abort, current_app, flash, g, redirect, request, url_for
from flask_login import current_user
from markupsafe import Markup
from werkzeug.utils import secure_filename

from .extensions import db
from .models import AuditLog, MediaFile, Setting

# ─────────────────────────── Настройки сайта ───────────────────────────

_SETTINGS_CACHE: dict[str, str] = {}


def load_settings() -> dict[str, str]:
    """Читает все настройки в кэш процесса (сбрасывается при сохранении в админке)."""
    global _SETTINGS_CACHE
    if not _SETTINGS_CACHE:
        try:
            _SETTINGS_CACHE = {s.key: s.value for s in Setting.query.all()}
        except Exception:  # таблицы ещё нет (первый запуск / миграция)
            return {}
    return _SETTINGS_CACHE


def clear_settings_cache() -> None:
    global _SETTINGS_CACHE
    _SETTINGS_CACHE = {}


def setting(key: str, default: str = "") -> str:
    return load_settings().get(key) or default


def setting_bool(key: str, default: bool = False) -> bool:
    raw = load_settings().get(key)
    if raw is None or raw == "":
        return default
    return str(raw).lower() in ("1", "true", "on", "yes")


def setting_int(key: str, default: int = 0) -> int:
    try:
        return int(load_settings().get(key) or default)
    except (TypeError, ValueError):
        return default


def set_setting(key: str, value, value_type: str = "text", group: str = "general",
                label: str = "", hint: str = "", position: int = 0) -> Setting:
    row = Setting.query.filter_by(key=key).first()
    if not row:
        row = Setting(key=key, value_type=value_type, group=group, label=label or key,
                      hint=hint, position=position)
        db.session.add(row)
    row.value = "" if value is None else str(value)
    clear_settings_cache()
    return row


# ─────────────────────────── Markdown ───────────────────────────

ALLOWED_TAGS = [
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u", "s", "del", "mark", "small", "sub", "sup",
    "ul", "ol", "li", "blockquote", "code", "pre", "kbd",
    "a", "img", "figure", "figcaption",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td",
    "span", "div", "details", "summary",
]
ALLOWED_ATTRS = {
    "*": ["class", "id"],   # style не разрешаем: bleach без css_sanitizer его всё равно вырежет
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height", "loading"],
    "td": ["colspan", "rowspan", "align"],
    "th": ["colspan", "rowspan", "align", "scope"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto", "tel", "data"]


def render_markdown(text: str | None) -> Markup:
    """Markdown → безопасный HTML. Внешние ссылки получают target=_blank."""
    if not text:
        return Markup("")
    html = md.markdown(
        text,
        extensions=["extra", "sane_lists", "nl2br", "admonition", "toc"],
        output_format="html5",
    )
    clean = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS,
                         protocols=ALLOWED_PROTOCOLS, strip=True)
    clean = re.sub(r'<a href="(https?://)', r'<a target="_blank" rel="noopener noreferrer" href="\1', clean)
    return Markup(clean)


def strip_markdown(text: str | None, limit: int = 160) -> str:
    """Короткая текстовая выжимка для превью и SEO-описаний."""
    if not text:
        return ""
    plain = re.sub(r"[#*_`>\[\]()!-]", " ", text)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain[:limit].rstrip() + ("…" if len(plain) > limit else "")


# ─────────────────────────── Slug ───────────────────────────

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya", "ә": "a", "ғ": "g", "қ": "q", "ң": "ng", "ө": "o", "ұ": "u", "ү": "u",
    "һ": "h", "і": "i",
}


def slugify(text: str, max_length: int = 90) -> str:
    text = (text or "").lower().strip()
    text = "".join(_TRANSLIT.get(ch, ch) for ch in text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return (text[:max_length].rstrip("-")) or "item"


def unique_slug(model, text: str, field: str = "slug", exclude_id: int | None = None) -> str:
    """Подбирает свободный slug.

    Запросы выполняются в ``no_autoflush``: объект, для которого подбирается slug,
    обычно уже добавлен в сессию, и автоматический flush попытался бы записать его
    с пустым slug (поле NOT NULL) ещё до присвоения значения.
    """
    base = slugify(text)
    candidate, i = base, 2
    with db.session.no_autoflush:
        while True:
            query = model.query.filter(getattr(model, field) == candidate)
            if exclude_id:
                query = query.filter(model.id != exclude_id)
            if not query.first():
                return candidate
            candidate = f"{base}-{i}"
            i += 1


# ─────────────────────────── Загрузка файлов ───────────────────────────

def allowed_file(filename: str, images_only: bool = False) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    allowed = (current_app.config["ALLOWED_IMAGE_EXTENSIONS"] if images_only
               else current_app.config["ALLOWED_EXTENSIONS"])
    return ext in allowed


def save_upload(file_storage, folder: str = "media", images_only: bool = False,
                record: bool = True) -> str | None:
    """Сохраняет файл и возвращает путь относительно /static/ (или None)."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename, images_only):
        flash("Недопустимый формат файла.", "danger")
        return None

    original = file_storage.filename
    ext = original.rsplit(".", 1)[1].lower()
    name = f"{uuid.uuid4().hex[:16]}.{ext}"
    target_dir: Path = current_app.config["UPLOAD_FOLDER"] / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    full_path = target_dir / name
    file_storage.save(full_path)

    # Сжимаем большие растровые изображения
    if ext in {"jpg", "jpeg", "png", "webp"}:
        try:
            from PIL import Image

            with Image.open(full_path) as img:
                if img.width > 1920:
                    ratio = 1920 / img.width
                    img = img.resize((1920, int(img.height * ratio)), Image.LANCZOS)
                    img.save(full_path, optimize=True, quality=86)
        except Exception:
            pass  # не критично: оставляем оригинал

    rel = f"uploads/{folder}/{name}"
    if record:
        db.session.add(MediaFile(
            filename=name, path=rel, original_name=secure_filename(original),
            mime=file_storage.mimetype or "", size=full_path.stat().st_size, folder=folder,
            uploaded_by=current_user.id if getattr(current_user, "is_authenticated", False) else None,
        ))
    return rel


def delete_upload(rel_path: str | None) -> None:
    if not rel_path or not rel_path.startswith("uploads/"):
        return
    try:
        path = current_app.config["UPLOAD_FOLDER"].parent / rel_path
        if path.exists() and path.is_file():
            os.remove(path)
    except OSError:
        pass


# ─────────────────────────── Доступ ───────────────────────────

def staff_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Войдите в панель управления.", "info")
            return redirect(url_for("auth.login", next=request.path))
        if not current_user.is_staff:
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def log_action(action: str, entity: str, entity_id: int | None = None, summary: str = "") -> None:
    db.session.add(AuditLog(
        user_id=current_user.id if getattr(current_user, "is_authenticated", False) else None,
        action=action, entity=entity, entity_id=entity_id, summary=summary[:400],
    ))


# ─────────────────────────── Разное ───────────────────────────

def form_bool(name: str) -> bool:
    return request.form.get(name) in ("on", "1", "true", "yes")


def form_int(name: str, default: int = 0) -> int:
    try:
        return int(request.form.get(name) or default)
    except (TypeError, ValueError):
        return default


def multilang_fields(prefix: str, source=None) -> dict[str, str]:
    """Собирает {'title_ru': ..., 'title_kk': ..., 'title_en': ...} из формы."""
    source = source if source is not None else request.form
    return {f"{prefix}_{lang}": (source.get(f"{prefix}_{lang}") or "").strip()
            for lang in ("ru", "kk", "en")}


def safe_next(target: str | None, fallback: str = "/") -> str:
    """Защита от open redirect."""
    if not target:
        return fallback
    if target.startswith("/") and not target.startswith("//"):
        return target
    return fallback


def human_date(value, fmt: str = "%d.%m.%Y") -> str:
    return value.strftime(fmt) if value else ""


MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня",
             "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def date_ru(value) -> str:
    if not value:
        return ""
    return f"{value.day} {MONTHS_RU[value.month - 1]} {value.year}"


def plural_ru(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return few
    return many
