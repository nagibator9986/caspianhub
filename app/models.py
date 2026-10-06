"""Модели данных Caspian College Hub.

Мультиязычность реализована суффиксами полей (_ru/_kk/_en) + хелпер ``tr()``,
что позволяет редактировать каждый язык прямо в админке без внешних .po-файлов.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from flask import g, has_request_context
from flask_login import UserMixin
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

LANGS = ("ru", "kk", "en")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def current_lang() -> str:
    if has_request_context():
        return getattr(g, "lang", "ru") or "ru"
    return "ru"


class Translatable:
    """Примесь: ``obj.tr('title')`` вернёт поле на текущем языке с откатом на русский."""

    def tr(self, field: str, lang: str | None = None) -> str:
        lang = lang or current_lang()
        value = getattr(self, f"{field}_{lang}", None)
        if value:
            return value
        for fallback in ("ru", "en", "kk"):
            value = getattr(self, f"{field}_{fallback}", None)
            if value:
                return value
        return ""


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


# ─────────────────────────────── Пользователи ───────────────────────────────

class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    full_name = db.Column(db.String(160), nullable=False, default="")
    role = db.Column(db.String(20), nullable=False, default="student")  # admin | editor | student
    group_name = db.Column(db.String(60), default="")      # учебная группа, напр. «ПО-21»
    specialty = db.Column(db.String(120), default="")
    avatar = db.Column(db.String(255), default="")
    bio = db.Column(db.Text, default="")
    locale = db.Column(db.String(5), default="ru")
    theme = db.Column(db.String(10), default="light")

    is_active_flag = db.Column(db.Boolean, default=True, nullable=False)
    last_seen = db.Column(db.DateTime(timezone=True), default=utcnow)

    progress = db.relationship("LessonProgress", back_populates="user", cascade="all, delete-orphan")
    attempts = db.relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    certificates = db.relationship("Certificate", back_populates="user", cascade="all, delete-orphan")
    favorites = db.relationship("Favorite", back_populates="user", cascade="all, delete-orphan")

    # ── пароль
    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    # ── роли
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_staff(self) -> bool:
        return self.role in ("admin", "editor")

    @property
    def is_active(self) -> bool:  # используется Flask-Login
        return bool(self.is_active_flag)

    @property
    def initials(self) -> str:
        parts = [p for p in (self.full_name or self.email).replace("@", " ").split() if p]
        return "".join(p[0].upper() for p in parts[:2]) or "?"

    def has_favorite(self, service_id: int) -> bool:
        return any(f.service_id == service_id for f in self.favorites)

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


# ─────────────────────────────── Настройки сайта ───────────────────────────────

class Setting(db.Model):
    """Ключ-значение для полной редактируемости сайта из админки."""

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, default="")
    value_type = db.Column(db.String(20), default="text")   # text | textarea | color | image | bool | int | json | url
    group = db.Column(db.String(40), default="general")     # general | brand | hero | contacts | social | seo | footer
    label = db.Column(db.String(160), default="")
    hint = db.Column(db.String(255), default="")
    position = db.Column(db.Integer, default=0)

    @property
    def parsed(self):
        if self.value_type == "bool":
            return str(self.value).lower() in ("1", "true", "on", "yes")
        if self.value_type == "int":
            try:
                return int(self.value or 0)
            except (TypeError, ValueError):
                return 0
        if self.value_type == "json":
            try:
                return json.loads(self.value or "{}")
            except json.JSONDecodeError:
                return {}
        return self.value or ""

    def __repr__(self) -> str:
        return f"<Setting {self.key}>"


class MenuItem(db.Model, Translatable):
    """Конструктор навигации: шапка и подвал редактируются из админки."""

    __tablename__ = "menu_items"

    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(20), default="header")   # header | footer | quick
    title_ru = db.Column(db.String(120), default="")
    title_kk = db.Column(db.String(120), default="")
    title_en = db.Column(db.String(120), default="")
    url = db.Column(db.String(400), default="/")
    icon = db.Column(db.String(60), default="")
    is_external = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    position = db.Column(db.Integer, default=0)
    parent_id = db.Column(db.Integer, db.ForeignKey("menu_items.id", ondelete="CASCADE"))

    children = db.relationship("MenuItem", backref=db.backref("parent", remote_side=[id]),
                               cascade="all, delete-orphan", order_by="MenuItem.position")


class HomeSection(db.Model, Translatable):
    """Блоки главной страницы — включаются/выключаются и переставляются в админке."""

    __tablename__ = "home_sections"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)  # hero, stats, categories, services...
    title_ru = db.Column(db.String(200), default="")
    title_kk = db.Column(db.String(200), default="")
    title_en = db.Column(db.String(200), default="")
    subtitle_ru = db.Column(db.Text, default="")
    subtitle_kk = db.Column(db.Text, default="")
    subtitle_en = db.Column(db.Text, default="")
    is_active = db.Column(db.Boolean, default=True)
    position = db.Column(db.Integer, default=0)
    config = db.Column(db.Text, default="{}")

    @property
    def cfg(self) -> dict:
        try:
            return json.loads(self.config or "{}")
        except json.JSONDecodeError:
            return {}


# ─────────────────────────────── Сервисы ───────────────────────────────

service_tags = db.Table(
    "service_tags",
    db.Column("service_id", db.Integer, db.ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Category(db.Model, Translatable, TimestampMixin):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name_ru = db.Column(db.String(120), nullable=False)
    name_kk = db.Column(db.String(120), default="")
    name_en = db.Column(db.String(120), default="")
    description_ru = db.Column(db.Text, default="")
    description_kk = db.Column(db.Text, default="")
    description_en = db.Column(db.Text, default="")
    icon = db.Column(db.String(60), default="layout-grid")   # имя иконки Lucide
    color = db.Column(db.String(20), default="#EB5A40")
    position = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    services = db.relationship("Service", back_populates="category", order_by="Service.position")

    @property
    def active_services(self):
        return [s for s in self.services if s.is_published]


class Tag(db.Model, Translatable):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name_ru = db.Column(db.String(80), nullable=False)
    name_kk = db.Column(db.String(80), default="")
    name_en = db.Column(db.String(80), default="")


class Service(db.Model, Translatable, TimestampMixin):
    """Карточка внешнего сервиса экосистемы колледжа."""

    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"))

    name_ru = db.Column(db.String(160), nullable=False)
    name_kk = db.Column(db.String(160), default="")
    name_en = db.Column(db.String(160), default="")

    tagline_ru = db.Column(db.String(300), default="")      # короткий подзаголовок на карточке
    tagline_kk = db.Column(db.String(300), default="")
    tagline_en = db.Column(db.String(300), default="")

    description_ru = db.Column(db.Text, default="")         # Markdown, полное описание
    description_kk = db.Column(db.Text, default="")
    description_en = db.Column(db.Text, default="")

    # «Зачем это нужно» — список пунктов, по одному на строку
    benefits_ru = db.Column(db.Text, default="")
    benefits_kk = db.Column(db.Text, default="")
    benefits_en = db.Column(db.Text, default="")

    audience_ru = db.Column(db.String(300), default="")     # для кого: студенты / преподаватели / все
    audience_kk = db.Column(db.String(300), default="")
    audience_en = db.Column(db.String(300), default="")

    url = db.Column(db.String(400), default="")             # ссылка на внешний сервис
    url_label_ru = db.Column(db.String(120), default="Перейти в сервис")
    url_label_kk = db.Column(db.String(120), default="")
    url_label_en = db.Column(db.String(120), default="")
    mobile_ios_url = db.Column(db.String(400), default="")
    mobile_android_url = db.Column(db.String(400), default="")
    support_contact = db.Column(db.String(300), default="")

    icon = db.Column(db.String(60), default="app-window")    # иконка Lucide
    logo = db.Column(db.String(255), default="")             # загруженный логотип
    cover = db.Column(db.String(255), default="")            # обложка страницы
    color = db.Column(db.String(20), default="#EB5A40")
    accent = db.Column(db.String(20), default="#F9A03F")

    status = db.Column(db.String(20), default="active")      # active | beta | soon | maintenance
    access_level = db.Column(db.String(30), default="all")   # all | students | teachers | staff

    is_published = db.Column(db.Boolean, default=True, index=True)
    is_featured = db.Column(db.Boolean, default=False, index=True)
    position = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)

    seo_title = db.Column(db.String(200), default="")
    seo_description = db.Column(db.String(400), default="")

    category = db.relationship("Category", back_populates="services")
    tags = db.relationship("Tag", secondary=service_tags, backref="services")
    screenshots = db.relationship("ServiceScreenshot", back_populates="service",
                                  cascade="all, delete-orphan", order_by="ServiceScreenshot.position")
    faqs = db.relationship("ServiceFaq", back_populates="service",
                           cascade="all, delete-orphan", order_by="ServiceFaq.position")
    course = db.relationship("Course", back_populates="service", uselist=False, cascade="all, delete-orphan")
    favorites = db.relationship("Favorite", back_populates="service", cascade="all, delete-orphan")

    STATUS_LABELS = {
        "active": ("Работает", "emerald"),
        "beta": ("Бета", "amber"),
        "soon": ("Скоро", "sky"),
        "maintenance": ("Техработы", "rose"),
    }

    @property
    def status_label(self) -> str:
        return self.STATUS_LABELS.get(self.status, ("—", "slate"))[0]

    @property
    def status_color(self) -> str:
        return self.STATUS_LABELS.get(self.status, ("—", "slate"))[1]

    def benefit_list(self, lang: str | None = None) -> list[str]:
        raw = self.tr("benefits", lang)
        return [line.strip(" •-–—\t") for line in raw.splitlines() if line.strip()]

    @property
    def has_course(self) -> bool:
        return bool(self.course and self.course.is_published and self.course.lesson_count)

    @property
    def favorite_count(self) -> int:
        return len(self.favorites)

    def __repr__(self) -> str:
        return f"<Service {self.slug}>"


class ServiceScreenshot(db.Model, Translatable):
    __tablename__ = "service_screenshots"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    caption_ru = db.Column(db.String(300), default="")
    caption_kk = db.Column(db.String(300), default="")
    caption_en = db.Column(db.String(300), default="")
    position = db.Column(db.Integer, default=0)

    service = db.relationship("Service", back_populates="screenshots")


class ServiceFaq(db.Model, Translatable):
    __tablename__ = "service_faqs"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    question_ru = db.Column(db.String(400), nullable=False)
    question_kk = db.Column(db.String(400), default="")
    question_en = db.Column(db.String(400), default="")
    answer_ru = db.Column(db.Text, default="")
    answer_kk = db.Column(db.Text, default="")
    answer_en = db.Column(db.Text, default="")
    position = db.Column(db.Integer, default=0)

    service = db.relationship("Service", back_populates="faqs")


# ─────────────────────────────── Обучение ───────────────────────────────

class Course(db.Model, Translatable, TimestampMixin):
    """Мини-курс «как пользоваться сервисом», живёт на странице сервиса."""

    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id", ondelete="CASCADE"), unique=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)

    title_ru = db.Column(db.String(200), nullable=False)
    title_kk = db.Column(db.String(200), default="")
    title_en = db.Column(db.String(200), default="")
    summary_ru = db.Column(db.Text, default="")
    summary_kk = db.Column(db.Text, default="")
    summary_en = db.Column(db.Text, default="")
    outcomes_ru = db.Column(db.Text, default="")    # чему научится — по пункту на строку
    outcomes_kk = db.Column(db.Text, default="")
    outcomes_en = db.Column(db.Text, default="")

    level = db.Column(db.String(20), default="beginner")   # beginner | intermediate | advanced
    duration_min = db.Column(db.Integer, default=15)
    cover = db.Column(db.String(255), default="")
    is_published = db.Column(db.Boolean, default=True)
    certificate_enabled = db.Column(db.Boolean, default=True)
    pass_score = db.Column(db.Integer, default=70)

    service = db.relationship("Service", back_populates="course")
    modules = db.relationship("Module", back_populates="course",
                              cascade="all, delete-orphan", order_by="Module.position")

    LEVEL_LABELS = {"beginner": "Начальный", "intermediate": "Средний", "advanced": "Продвинутый"}

    @property
    def level_label(self) -> str:
        return self.LEVEL_LABELS.get(self.level, "Начальный")

    def outcome_list(self, lang: str | None = None) -> list[str]:
        return [ln.strip(" •-–—\t") for ln in self.tr("outcomes", lang).splitlines() if ln.strip()]

    @property
    def lessons(self):
        return [lesson for module in self.modules for lesson in module.lessons]

    @property
    def lesson_count(self) -> int:
        return len(self.lessons)

    @property
    def quiz(self):
        return Quiz.query.filter_by(course_id=self.id).first()

    def progress_for(self, user) -> int:
        """Процент завершения курса для пользователя (0–100)."""
        if not user or not getattr(user, "is_authenticated", False):
            return 0
        total = self.lesson_count
        if not total:
            return 0
        ids = {lesson.id for lesson in self.lessons}
        done = LessonProgress.query.filter(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id.in_(ids),
            LessonProgress.completed.is_(True),
        ).count()
        return int(round(done * 100 / total))

    def is_completed_by(self, user) -> bool:
        return self.progress_for(user) >= 100


class Module(db.Model, Translatable):
    __tablename__ = "modules"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title_ru = db.Column(db.String(200), nullable=False)
    title_kk = db.Column(db.String(200), default="")
    title_en = db.Column(db.String(200), default="")
    description_ru = db.Column(db.Text, default="")
    description_kk = db.Column(db.Text, default="")
    description_en = db.Column(db.Text, default="")
    position = db.Column(db.Integer, default=0)

    course = db.relationship("Course", back_populates="modules")
    lessons = db.relationship("Lesson", back_populates="module",
                              cascade="all, delete-orphan", order_by="Lesson.position")


class Lesson(db.Model, Translatable, TimestampMixin):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    slug = db.Column(db.String(140), nullable=False, index=True)

    title_ru = db.Column(db.String(200), nullable=False)
    title_kk = db.Column(db.String(200), default="")
    title_en = db.Column(db.String(200), default="")
    content_ru = db.Column(db.Text, default="")    # Markdown
    content_kk = db.Column(db.Text, default="")
    content_en = db.Column(db.Text, default="")
    tip_ru = db.Column(db.Text, default="")        # блок «совет»
    tip_kk = db.Column(db.Text, default="")
    tip_en = db.Column(db.Text, default="")

    media_type = db.Column(db.String(20), default="none")  # none | image | video | embed
    media_url = db.Column(db.String(500), default="")
    duration_min = db.Column(db.Integer, default=3)
    position = db.Column(db.Integer, default=0)

    module = db.relationship("Module", back_populates="lessons")
    progress = db.relationship("LessonProgress", back_populates="lesson", cascade="all, delete-orphan")

    @property
    def course(self):
        return self.module.course if self.module else None

    def is_done_by(self, user) -> bool:
        if not user or not getattr(user, "is_authenticated", False):
            return False
        row = LessonProgress.query.filter_by(user_id=user.id, lesson_id=self.id).first()
        return bool(row and row.completed)


class LessonProgress(db.Model):
    __tablename__ = "lesson_progress"
    __table_args__ = (db.UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime(timezone=True))

    user = db.relationship("User", back_populates="progress")
    lesson = db.relationship("Lesson", back_populates="progress")


# ─────────────────────────────── Тесты ───────────────────────────────

class Quiz(db.Model, Translatable):
    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title_ru = db.Column(db.String(200), default="Итоговый тест")
    title_kk = db.Column(db.String(200), default="")
    title_en = db.Column(db.String(200), default="")
    description_ru = db.Column(db.Text, default="")
    description_kk = db.Column(db.Text, default="")
    description_en = db.Column(db.Text, default="")
    pass_score = db.Column(db.Integer, default=70)
    time_limit_min = db.Column(db.Integer, default=0)   # 0 — без ограничения

    course = db.relationship("Course", backref=db.backref("quizzes", cascade="all, delete-orphan"))
    questions = db.relationship("Question", back_populates="quiz",
                                cascade="all, delete-orphan", order_by="Question.position")

    def best_attempt(self, user):
        if not user or not getattr(user, "is_authenticated", False):
            return None
        return (QuizAttempt.query.filter_by(quiz_id=self.id, user_id=user.id)
                .order_by(QuizAttempt.score.desc()).first())


class Question(db.Model, Translatable):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    text_ru = db.Column(db.Text, nullable=False)
    text_kk = db.Column(db.Text, default="")
    text_en = db.Column(db.Text, default="")
    explanation_ru = db.Column(db.Text, default="")
    explanation_kk = db.Column(db.Text, default="")
    explanation_en = db.Column(db.Text, default="")
    position = db.Column(db.Integer, default=0)

    quiz = db.relationship("Quiz", back_populates="questions")
    options = db.relationship("Option", back_populates="question",
                              cascade="all, delete-orphan", order_by="Option.position")

    @property
    def correct_option(self):
        return next((o for o in self.options if o.is_correct), None)


class Option(db.Model, Translatable):
    __tablename__ = "options"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    text_ru = db.Column(db.String(500), nullable=False)
    text_kk = db.Column(db.String(500), default="")
    text_en = db.Column(db.String(500), default="")
    is_correct = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, default=0)

    question = db.relationship("Question", back_populates="options")


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score = db.Column(db.Integer, default=0)          # процент
    correct_count = db.Column(db.Integer, default=0)
    total_count = db.Column(db.Integer, default=0)
    passed = db.Column(db.Boolean, default=False)
    answers_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    quiz = db.relationship("Quiz", backref=db.backref("attempts", cascade="all, delete-orphan"))
    user = db.relationship("User", back_populates="attempts")


class Certificate(db.Model):
    __tablename__ = "certificates"
    __table_args__ = (db.UniqueConstraint("user_id", "course_id", name="uq_user_course_cert"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    code = db.Column(db.String(24), unique=True, nullable=False, index=True)
    score = db.Column(db.Integer, default=0)
    issued_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    user = db.relationship("User", back_populates="certificates")
    course = db.relationship("Course", backref=db.backref("certificates", cascade="all, delete-orphan"))

    @staticmethod
    def new_code() -> str:
        return "CCU-" + secrets.token_hex(5).upper()


# ─────────────────────────────── Контент и обратная связь ───────────────────────────────

class News(db.Model, Translatable, TimestampMixin):
    __tablename__ = "news"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    title_ru = db.Column(db.String(240), nullable=False)
    title_kk = db.Column(db.String(240), default="")
    title_en = db.Column(db.String(240), default="")
    excerpt_ru = db.Column(db.Text, default="")
    excerpt_kk = db.Column(db.Text, default="")
    excerpt_en = db.Column(db.Text, default="")
    body_ru = db.Column(db.Text, default="")
    body_kk = db.Column(db.Text, default="")
    body_en = db.Column(db.Text, default="")
    cover = db.Column(db.String(255), default="")
    kind = db.Column(db.String(20), default="news")     # news | update | announcement
    is_published = db.Column(db.Boolean, default=True, index=True)
    is_pinned = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime(timezone=True), default=utcnow, index=True)
    views = db.Column(db.Integer, default=0)

    KIND_LABELS = {"news": "Новость", "update": "Обновление", "announcement": "Объявление"}

    @property
    def kind_label(self) -> str:
        return self.KIND_LABELS.get(self.kind, "Новость")


class Faq(db.Model, Translatable):
    __tablename__ = "faqs"

    id = db.Column(db.Integer, primary_key=True)
    question_ru = db.Column(db.String(400), nullable=False)
    question_kk = db.Column(db.String(400), default="")
    question_en = db.Column(db.String(400), default="")
    answer_ru = db.Column(db.Text, default="")
    answer_kk = db.Column(db.Text, default="")
    answer_en = db.Column(db.Text, default="")
    category = db.Column(db.String(60), default="Общее")
    position = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), default="")
    email = db.Column(db.String(160), default="")
    topic = db.Column(db.String(60), default="Вопрос")
    service_id = db.Column(db.Integer, db.ForeignKey("services.id", ondelete="SET NULL"))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="new")    # new | in_progress | done
    admin_note = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, index=True)

    service = db.relationship("Service")

    STATUS_LABELS = {"new": "Новая", "in_progress": "В работе", "done": "Закрыта"}

    @property
    def status_label(self) -> str:
        return self.STATUS_LABELS.get(self.status, "Новая")


class Testimonial(db.Model, Translatable):
    __tablename__ = "testimonials"

    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(160), nullable=False)
    role_ru = db.Column(db.String(160), default="")
    role_kk = db.Column(db.String(160), default="")
    role_en = db.Column(db.String(160), default="")
    text_ru = db.Column(db.Text, default="")
    text_kk = db.Column(db.Text, default="")
    text_en = db.Column(db.Text, default="")
    avatar = db.Column(db.String(255), default="")
    rating = db.Column(db.Integer, default=5)
    is_active = db.Column(db.Boolean, default=True)
    position = db.Column(db.Integer, default=0)


class Favorite(db.Model):
    __tablename__ = "favorites"
    __table_args__ = (db.UniqueConstraint("user_id", "service_id", name="uq_user_service_fav"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    user = db.relationship("User", back_populates="favorites")
    service = db.relationship("Service", back_populates="favorites")


class ServiceEvent(db.Model):
    """Сырая аналитика: просмотры и переходы по сервисам."""

    __tablename__ = "service_events"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    kind = db.Column(db.String(20), default="view")   # view | click
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, index=True)

    service = db.relationship("Service")


class MediaFile(db.Model):
    __tablename__ = "media_files"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(400), nullable=False)
    original_name = db.Column(db.String(255), default="")
    mime = db.Column(db.String(80), default="")
    size = db.Column(db.Integer, default=0)
    folder = db.Column(db.String(40), default="media")
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    @property
    def size_human(self) -> str:
        n = float(self.size or 0)
        for unit in ("Б", "КБ", "МБ", "ГБ"):
            if n < 1024:
                return f"{n:.0f} {unit}" if unit == "Б" else f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} ТБ"

    @property
    def is_image(self) -> bool:
        return (self.mime or "").startswith("image/")


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    action = db.Column(db.String(40), default="")       # create | update | delete | login
    entity = db.Column(db.String(60), default="")
    entity_id = db.Column(db.Integer)
    summary = db.Column(db.String(400), default="")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, index=True)

    user = db.relationship("User")
