"""Словарь строк интерфейса: русский, казахский, английский."""

STRINGS: dict[str, dict[str, str]] = {
    # Навигация
    "nav.home": {"ru": "Главная", "kk": "Басты бет", "en": "Home"},
    "nav.services": {"ru": "Сервисы", "kk": "Сервистер", "en": "Services"},
    "nav.courses": {"ru": "Обучение", "kk": "Оқыту", "en": "Learning"},
    "nav.news": {"ru": "Новости", "kk": "Жаңалықтар", "en": "News"},
    "nav.faq": {"ru": "Вопросы", "kk": "Сұрақтар", "en": "FAQ"},
    "nav.help": {"ru": "Поддержка", "kk": "Қолдау", "en": "Support"},
    "nav.about": {"ru": "О платформе", "kk": "Платформа туралы", "en": "About"},
    "nav.account": {"ru": "Кабинет", "kk": "Кабинет", "en": "Account"},
    "nav.admin": {"ru": "Админка", "kk": "Әкімші", "en": "Admin"},

    # Действия
    "action.open": {"ru": "Открыть", "kk": "Ашу", "en": "Open"},
    "action.open_service": {"ru": "Перейти в сервис", "kk": "Сервиске өту", "en": "Go to service"},
    "action.details": {"ru": "Подробнее", "kk": "Толығырақ", "en": "Details"},
    "action.start_course": {"ru": "Пройти обучение", "kk": "Оқудан өту", "en": "Start course"},
    "action.continue": {"ru": "Продолжить", "kk": "Жалғастыру", "en": "Continue"},
    "action.all_services": {"ru": "Все сервисы", "kk": "Барлық сервистер", "en": "All services"},
    "action.search": {"ru": "Поиск", "kk": "Іздеу", "en": "Search"},
    "action.login": {"ru": "Войти", "kk": "Кіру", "en": "Sign in"},
    "action.logout": {"ru": "Выйти", "kk": "Шығу", "en": "Sign out"},
    "action.register": {"ru": "Регистрация", "kk": "Тіркелу", "en": "Sign up"},
    "action.send": {"ru": "Отправить", "kk": "Жіберу", "en": "Send"},
    "action.save": {"ru": "Сохранить", "kk": "Сақтау", "en": "Save"},
    "action.back": {"ru": "Назад", "kk": "Артқа", "en": "Back"},
    "action.next": {"ru": "Далее", "kk": "Әрі қарай", "en": "Next"},

    # Сервисы
    "svc.course_badge": {"ru": "Есть мини-курс", "kk": "Шағын курс бар", "en": "Mini-course"},
    "svc.audience": {"ru": "Для кого", "kk": "Кімге арналған", "en": "Audience"},
    "svc.benefits": {"ru": "Что это вам даёт", "kk": "Бұл сізге не береді", "en": "What you get"},
    "svc.how_to": {"ru": "Как пользоваться", "kk": "Қалай пайдалану керек", "en": "How to use"},
    "svc.screenshots": {"ru": "Как это выглядит", "kk": "Бұл қалай көрінеді", "en": "Screenshots"},
    "svc.faq": {"ru": "Частые вопросы", "kk": "Жиі қойылатын сұрақтар", "en": "FAQ"},
    "svc.support": {"ru": "Нужна помощь", "kk": "Көмек керек", "en": "Need help"},
    "svc.related": {"ru": "Похожие сервисы", "kk": "Ұқсас сервистер", "en": "Related services"},
    "svc.empty": {"ru": "Сервисы не найдены", "kk": "Сервистер табылмады", "en": "No services found"},

    # Обучение
    "learn.progress": {"ru": "Прогресс", "kk": "Прогресс", "en": "Progress"},
    "learn.lessons": {"ru": "Уроки", "kk": "Сабақтар", "en": "Lessons"},
    "learn.minutes": {"ru": "мин", "kk": "мин", "en": "min"},
    "learn.level": {"ru": "Уровень", "kk": "Деңгей", "en": "Level"},
    "learn.outcomes": {"ru": "Чему вы научитесь", "kk": "Не үйренесіз", "en": "What you'll learn"},
    "learn.mark_done": {"ru": "Отметить пройденным", "kk": "Өтті деп белгілеу", "en": "Mark complete"},
    "learn.done": {"ru": "Пройдено", "kk": "Өтілді", "en": "Completed"},
    "learn.quiz": {"ru": "Итоговый тест", "kk": "Қорытынды тест", "en": "Final quiz"},
    "learn.tip": {"ru": "Совет", "kk": "Кеңес", "en": "Tip"},
    "learn.certificate": {"ru": "Сертификат", "kk": "Сертификат", "en": "Certificate"},

    # Кабинет
    "acc.favorites": {"ru": "Избранное", "kk": "Таңдаулылар", "en": "Favorites"},
    "acc.my_courses": {"ru": "Моё обучение", "kk": "Менің оқуым", "en": "My learning"},
    "acc.certificates": {"ru": "Сертификаты", "kk": "Сертификаттар", "en": "Certificates"},
    "acc.profile": {"ru": "Профиль", "kk": "Профиль", "en": "Profile"},

    # Общее
    "common.empty": {"ru": "Пока пусто", "kk": "Әзірге бос", "en": "Nothing here yet"},
    "common.loading": {"ru": "Загрузка…", "kk": "Жүктелуде…", "en": "Loading…"},
    "common.of": {"ru": "из", "kk": "ішінен", "en": "of"},
    "common.min_read": {"ru": "мин чтения", "kk": "мин оқу", "en": "min read"},
}


def t(key: str, lang: str = "ru") -> str:
    entry = STRINGS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("ru") or key
