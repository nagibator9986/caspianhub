"""Наполнение базы: настройки, меню, категории, сервисы, курсы, тесты, новости, FAQ, отзывы.

Контент читается из каталога ``content/`` (JSON-файлы), поэтому его можно
править и перезаливать без изменения кода.
"""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from app.extensions import db
from app.models import (Category, Course, Faq, HomeSection, Lesson, MenuItem,
                        Module, News, Option, Question, Quiz, Service,
                        ServiceFaq, Setting, Tag, Testimonial, User, utcnow)
from app.utils import clear_settings_cache, slugify

CONTENT_DIR = Path(__file__).resolve().parent / "content"


# ─────────────────────────── Настройки ───────────────────────────

SETTINGS: list[tuple] = [
    # (ключ, значение, тип, группа, подпись, подсказка, порядок)
    ("brand_color", "#EB5A40", "color", "brand", "Основной цвет бренда", "Коралловый цвет логотипа колледжа", 1),
    ("brand_color_2", "#F9A03F", "color", "brand", "Дополнительный цвет", "Используется в градиентах и акцентах", 2),
    ("site_logo", "", "image", "brand", "Логотип", "Пусто — используется логотип колледжа из комплекта", 3),
    ("site_name", "Caspian College Hub", "text", "brand", "Название платформы", "Показывается в шапке, подвале и вкладке браузера", 4),
    ("site_tagline", "Единое окно сервисов колледжа", "text", "brand", "Подпись под названием", "Короткая, до 45 знаков", 5),

    ("hero_badge", "Экосистема цифровых сервисов колледжа", "text", "hero", "Бейдж над заголовком", "", 1),
    ("hero_title", "Все сервисы колледжа — в одном окне", "text", "hero", "Заголовок первого экрана", "До 60 знаков", 2),
    ("hero_highlight", "в одном окне", "text", "hero", "Подсвечиваемая часть заголовка", "Эта часть будет выделена цветом; должна встречаться в заголовке", 3),
    ("hero_subtitle", "Электронный журнал, библиотека, практика, справки и госуслуги. Каждый сервис — с понятным описанием и коротким курсом «как этим пользоваться».", "textarea", "hero", "Подзаголовок", "", 4),
    ("hero_cta_primary", "Открыть каталог сервисов", "text", "hero", "Текст главной кнопки", "", 5),
    ("hero_cta_secondary", "Начать обучение", "text", "hero", "Текст второй кнопки", "", 6),
    ("search_placeholder_hero", "Что вам нужно? Например: журнал, справка, практика", "text", "hero", "Подсказка в поиске на главной", "", 7),
    ("search_placeholder", "Найти сервис…", "text", "hero", "Подсказка в поиске в шапке", "", 8),

    ("site_description", "Единое окно цифровых сервисов Колледжа Каспийского университета: электронный журнал, библиотека, практика, справки и обучение работе с каждым сервисом.", "textarea", "seo", "Описание сайта", "Показывается в поисковой выдаче и при отправке ссылки", 1),
    ("seo_keywords", "колледж каспийского университета, ccu, сервисы колледжа, электронный журнал, smartnation", "textarea", "seo", "Ключевые слова", "Через запятую", 2),

    ("contact_address", "г. Алматы, проспект Сейфуллина, 521", "text", "contacts", "Адрес", "", 1),
    ("contact_phone", "+7 (727) 279-3777", "text", "contacts", "Телефон", "", 2),
    ("contact_phone_mobile", "+7 706 430 84 61", "text", "contacts", "Мобильный / WhatsApp", "", 3),
    ("contact_email", "info@ccu.edu.kz", "text", "contacts", "Электронная почта", "", 4),
    ("contact_hours", "Пн–Пт, 09:00–18:00", "text", "contacts", "Часы работы", "", 5),

    ("social_instagram", "https://www.instagram.com/college.caspian/", "url", "social", "Instagram", "", 1),
    ("social_facebook", "https://www.facebook.com/CollegeCaspian", "url", "social", "Facebook", "", 2),
    ("social_whatsapp", "https://wa.me/77064308461", "url", "social", "WhatsApp", "", 3),
    ("social_site", "https://ccu.edu.kz", "url", "social", "Сайт колледжа", "", 4),

    ("footer_about", "Все цифровые сервисы Колледжа Каспийского университета в одном месте — с понятным описанием и коротким обучением по каждому.", "textarea", "footer", "Текст в подвале", "", 1),
    ("footer_legal", "Колледж Каспийского университета", "text", "footer", "Правообладатель", "Показывается рядом со знаком ©", 2),

    ("enable_registration", "true", "bool", "features", "Разрешить регистрацию", "Если выключить, новые пользователи не смогут создать аккаунт", 1),
    ("enable_certificates", "true", "bool", "features", "Выдавать сертификаты", "За успешно пройденные тесты", 2),
    ("enable_testimonials", "true", "bool", "features", "Показывать отзывы на главной", "", 3),
    ("enable_news", "true", "bool", "features", "Показывать новости", "", 4),

    ("items_per_page", "12", "int", "general", "Элементов на странице", "Для списков новостей и каталога", 1),
    ("support_note", "Обращения рассматриваются в рабочие часы колледжа.", "textarea", "general", "Заметка на странице поддержки", "", 2),
]

HOME_SECTIONS = [
    ("hero", "Все сервисы колледжа — в одном окне", "Экосистема цифровых сервисов колледжа", 1),
    ("stats", "Платформа в цифрах", "", 2),
    ("categories", "С чего начать", "Сервисы сгруппированы по задачам — выберите ту, которая ближе к вашему вопросу.", 3),
    ("services", "Сервисы, которыми пользуются чаще всего", "Каждая карточка — это не просто ссылка: внутри описание, ответы на частые вопросы и короткое обучение.", 4),
    ("how", "Четыре шага — и вы разобрались", "Платформа не заменяет сервисы колледжа — она объясняет, где что лежит и как этим пользоваться.", 5),
    ("courses", "Мини-курсы по сервисам", "10–20 минут — и вы уверенно пользуетесь сервисом. В конце тест и сертификат.", 6),
    ("testimonials", "Что говорят студенты и преподаватели", "", 7),
    ("news", "Новости и обновления", "", 8),
    ("faq", "Коротко о главном", "Не нашли ответ? Напишите нам — отвечаем в рабочие часы.", 9),
    ("cta", "Хватит искать нужную ссылку в чате группы", "Создайте аккаунт — сохраняйте избранные сервисы, проходите мини-курсы и получайте сертификаты.", 10),
]

HEADER_MENU = [
    ("Сервисы", "Сервистер", "Services", "/services", "layout-grid", 1),
    ("Обучение", "Оқыту", "Learning", "/courses", "graduation-cap", 2),
    ("Новости", "Жаңалықтар", "News", "/news", "newspaper", 3),
    ("Вопросы", "Сұрақтар", "FAQ", "/faq", "circle-help", 4),
    ("О платформе", "Платформа туралы", "About", "/about", "info", 5),
]

FOOTER_MENU = [
    ("Поддержка", "Қолдау", "Support", "/support", "life-buoy", 1),
    ("Сайт колледжа", "Колледж сайты", "College website", "https://ccu.edu.kz", "globe", 2),
]

USERS = [
    ("admin@ccu.edu.kz", "admin123", "Администратор платформы", "admin", "", ""),
    ("editor@ccu.edu.kz", "editor123", "Айгерим Нурланова", "editor", "", "Методист"),
    ("student@ccu.edu.kz", "student123", "Алишер Сагындык", "student", "ПО-21", "Программное обеспечение"),
    ("aruzhan@ccu.edu.kz", "student123", "Аружан Бекова", "student", "МК-22", "Маркетинг"),
]


def _load(name: str):
    path = CONTENT_DIR / name
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _ml(data: dict, prefix: str) -> dict:
    """Собирает мультиязычные поля из JSON, недостающие языки — пустая строка."""
    return {f"{prefix}_{lang}": (data.get(f"{prefix}_{lang}") or "") for lang in ("ru", "kk", "en")}


# ─────────────────────────── Разделы наполнения ───────────────────────────

def seed_settings() -> None:
    for key, value, vtype, group, label, hint, position in SETTINGS:
        if not Setting.query.filter_by(key=key).first():
            db.session.add(Setting(key=key, value=value, value_type=vtype, group=group,
                                   label=label, hint=hint, position=position))
    db.session.commit()
    clear_settings_cache()


def seed_home_sections() -> None:
    for key, title, subtitle, position in HOME_SECTIONS:
        if not HomeSection.query.filter_by(key=key).first():
            db.session.add(HomeSection(key=key, title_ru=title, subtitle_ru=subtitle,
                                       position=position, is_active=True))
    db.session.commit()


def seed_menu() -> None:
    if MenuItem.query.count():
        return
    for location, rows in (("header", HEADER_MENU), ("footer", FOOTER_MENU)):
        for title_ru, title_kk, title_en, url, icon, position in rows:
            db.session.add(MenuItem(
                location=location, title_ru=title_ru, title_kk=title_kk, title_en=title_en,
                url=url, icon=icon, position=position, is_active=True,
                is_external=url.startswith("http"),
            ))
    db.session.commit()


def seed_users() -> None:
    for email, password, name, role, group, specialty in USERS:
        if User.query.filter_by(email=email).first():
            continue
        user = User(email=email, full_name=name, role=role,
                    group_name=group, specialty=specialty)
        user.set_password(password)
        db.session.add(user)
    db.session.commit()


def seed_categories() -> dict[str, Category]:
    data = _load("_categories.json") or {}
    result: dict[str, Category] = {}
    for position, (slug, payload) in enumerate(data.items(), start=1):
        cat = Category.query.filter_by(slug=slug).first()
        if not cat:
            cat = Category(slug=slug)
            db.session.add(cat)
        cat.name_ru = payload.get("name_ru", slug)
        cat.name_kk = payload.get("name_kk", "")
        cat.name_en = payload.get("name_en", "")
        cat.description_ru = payload.get("description_ru", "")
        cat.icon = payload.get("icon", "layout-grid")
        cat.color = payload.get("color", "#EB5A40")
        cat.position = position
        cat.is_active = True
        result[slug] = cat
    db.session.commit()
    return result


def _get_tag(name: str) -> Tag:
    slug = slugify(name)
    tag = Tag.query.filter_by(slug=slug).first()
    if not tag:
        tag = Tag(slug=slug, name_ru=name)
        db.session.add(tag)
    return tag


def seed_services(categories: dict[str, Category]) -> None:
    files = sorted(p for p in CONTENT_DIR.glob("*.json") if not p.name.startswith("_"))

    # Порядок сервисов на витрине: сначала самые нужные студенту
    priority = ["smartnation", "raspisanie", "spravki", "praktika", "biblioteka", "beam",
                "vmk", "egov", "obshezhitie", "priem-direktora", "antiplagiat",
                "sajt-kolledzha", "whatsapp-podderzhka", "enbek", "socseti",
                "ai-pomoshnik", "cifrovaya-gramotnost", "caspian-university"]
    featured = {"smartnation", "raspisanie", "spravki", "praktika", "biblioteka", "beam"}

    def sort_key(path: Path) -> tuple:
        stem = path.stem
        return (priority.index(stem) if stem in priority else 999, stem)

    for position, path in enumerate(sorted(files, key=sort_key), start=1):
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)

        slug = data.get("slug") or path.stem
        service = Service.query.filter_by(slug=slug).first()
        if not service:
            service = Service(slug=slug)
            db.session.add(service)

        for prefix in ("name", "tagline", "description", "benefits", "audience", "url_label"):
            for field, value in _ml(data, prefix).items():
                setattr(service, field, value)
        if not service.url_label_ru:
            service.url_label_ru = "Перейти в сервис"

        service.category = categories.get(data.get("category", ""))
        service.url = data.get("url", "")
        service.mobile_ios_url = data.get("mobile_ios_url", "")
        service.mobile_android_url = data.get("mobile_android_url", "")
        service.support_contact = data.get("support_contact", "")
        service.icon = data.get("icon", "app-window")
        service.color = data.get("color", "#EB5A40")
        service.accent = data.get("accent", "#F9A03F")
        service.status = data.get("status", "active")
        service.access_level = data.get("access_level", "all")
        service.is_published = True
        service.is_featured = slug in featured
        service.position = position
        service.seo_title = data.get("seo_title", "")
        service.seo_description = data.get("seo_description") or (data.get("tagline_ru") or "")[:400]

        service.tags = [_get_tag(name) for name in (data.get("tags") or [])[:12]]

        # FAQ сервиса
        if not service.faqs:
            for i, faq in enumerate(data.get("faqs") or [], start=1):
                db.session.add(ServiceFaq(
                    service=service, position=i,
                    question_ru=faq.get("q", ""), answer_ru=faq.get("a", ""),
                ))

        db.session.flush()
        _seed_course(service, data.get("course") or {})

    db.session.commit()


def _seed_course(service: Service, payload: dict) -> None:
    if not payload:
        return

    course = Course.query.filter_by(service_id=service.id).first()
    if not course:
        course = Course(service_id=service.id, slug=service.slug)
        db.session.add(course)

    for prefix in ("title", "summary", "outcomes"):
        for field, value in _ml(payload, prefix).items():
            setattr(course, field, value)

    course.level = payload.get("level", "beginner")
    course.duration_min = int(payload.get("duration_min") or 15)
    course.pass_score = int((payload.get("quiz") or {}).get("pass_score") or 70)
    course.is_published = True
    course.certificate_enabled = True
    db.session.flush()

    if course.modules:          # уже наполнен — не дублируем
        return

    for m_index, module_data in enumerate(payload.get("modules") or [], start=1):
        module = Module(course_id=course.id, position=m_index)
        for prefix in ("title", "description"):
            for field, value in _ml(module_data, prefix).items():
                setattr(module, field, value)
        db.session.add(module)
        db.session.flush()

        for l_index, lesson_data in enumerate(module_data.get("lessons") or [], start=1):
            lesson = Lesson(module_id=module.id, position=l_index)
            for prefix in ("title", "content", "tip"):
                for field, value in _ml(lesson_data, prefix).items():
                    setattr(lesson, field, value)
            lesson.slug = f"{course.slug}-{m_index}-{l_index}"
            lesson.duration_min = int(lesson_data.get("duration_min") or 3)
            db.session.add(lesson)

    quiz_data = payload.get("quiz") or {}
    questions = quiz_data.get("questions") or []
    if questions:
        quiz = Quiz(course_id=course.id, pass_score=int(quiz_data.get("pass_score") or 70))
        for prefix in ("title", "description"):
            for field, value in _ml(quiz_data, prefix).items():
                setattr(quiz, field, value)
        if not quiz.title_ru:
            quiz.title_ru = "Проверьте себя"
        db.session.add(quiz)
        db.session.flush()

        for q_index, q_data in enumerate(questions, start=1):
            question = Question(quiz_id=quiz.id, position=q_index)
            for prefix in ("text", "explanation"):
                for field, value in _ml(q_data, prefix).items():
                    setattr(question, field, value)
            db.session.add(question)
            db.session.flush()
            for o_index, o_data in enumerate(q_data.get("options") or [], start=1):
                db.session.add(Option(
                    question_id=question.id, position=o_index,
                    text_ru=o_data.get("text_ru", ""),
                    is_correct=bool(o_data.get("is_correct")),
                ))


def seed_news() -> None:
    if News.query.count():
        return
    items = _load("_news.json") or []
    now = utcnow()
    for item in items:
        slug = item.get("slug") or slugify(item.get("title_ru", "novost"))
        db.session.add(News(
            slug=slug,
            **_ml(item, "title"), **_ml(item, "excerpt"), **_ml(item, "body"),
            kind=item.get("kind", "news"),
            is_published=True,
            is_pinned=bool(item.get("is_pinned")),
            published_at=now - timedelta(days=int(item.get("days_ago") or 1)),
        ))
    db.session.commit()


def seed_faq() -> None:
    if Faq.query.count():
        return
    for position, item in enumerate(_load("_faq.json") or [], start=1):
        db.session.add(Faq(
            **_ml(item, "question"), **_ml(item, "answer"),
            category=item.get("category", "Общее"),
            position=position, is_active=True,
        ))
    db.session.commit()


def seed_testimonials() -> None:
    if Testimonial.query.count():
        return
    for position, item in enumerate(_load("_testimonials.json") or [], start=1):
        db.session.add(Testimonial(
            author=item.get("author", ""),
            **_ml(item, "role"), **_ml(item, "text"),
            rating=int(item.get("rating") or 5),
            position=position, is_active=True,
        ))
    db.session.commit()


def apply_site_copy() -> None:
    """Если агент подготовил _site_copy.json — переносим тексты в настройки и блоки."""
    copy = _load("_site_copy.json")
    if not copy:
        return

    hero = copy.get("hero") or {}
    mapping = {
        "hero_badge": hero.get("badge_ru"),
        "hero_title": hero.get("title_ru"),
        "hero_highlight": hero.get("highlight_ru"),
        "hero_subtitle": hero.get("subtitle_ru"),
        "hero_cta_primary": hero.get("cta_primary_ru"),
        "hero_cta_secondary": hero.get("cta_secondary_ru"),
        "search_placeholder_hero": hero.get("search_placeholder_ru"),
    }
    for key, value in mapping.items():
        if value:
            row = Setting.query.filter_by(key=key).first()
            if row:
                row.value = value

    footer = copy.get("footer") or {}
    if footer.get("about_ru"):
        row = Setting.query.filter_by(key="footer_about").first()
        if row:
            row.value = footer["about_ru"]

    for key, payload in (copy.get("sections") or {}).items():
        section = HomeSection.query.filter_by(key=key).first()
        if section and isinstance(payload, dict):
            if payload.get("title_ru"):
                section.title_ru = payload["title_ru"]
            if payload.get("subtitle_ru"):
                section.subtitle_ru = payload["subtitle_ru"]

    hero_section = HomeSection.query.filter_by(key="hero").first()
    if hero_section:
        if hero.get("title_ru"):
            hero_section.title_ru = hero["title_ru"]
        if hero.get("badge_ru"):
            hero_section.subtitle_ru = hero["badge_ru"]
        for lang in ("kk", "en"):
            if hero.get(f"title_{lang}"):
                setattr(hero_section, f"title_{lang}", hero[f"title_{lang}"])

    db.session.commit()
    clear_settings_cache()


# ─────────────────────────── Точка входа ───────────────────────────

def run_seed() -> None:
    seed_settings()
    seed_home_sections()
    seed_menu()
    seed_users()
    categories = seed_categories()
    seed_services(categories)
    seed_news()
    seed_faq()
    seed_testimonials()
    apply_site_copy()

    print(f"  категорий:  {Category.query.count()}")
    print(f"  сервисов:   {Service.query.count()}")
    print(f"  курсов:     {Course.query.count()}")
    print(f"  уроков:     {Lesson.query.count()}")
    print(f"  вопросов:   {Question.query.count()}")
    print(f"  новостей:   {News.query.count()}")
    print(f"  FAQ:        {Faq.query.count()}")
    print(f"  отзывов:    {Testimonial.query.count()}")
    print(f"  настроек:   {Setting.query.count()}")
    print(f"  учёток:     {User.query.count()}")


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        db.create_all()
        run_seed()
