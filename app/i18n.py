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

    # Сообщество
    "hub.title": {"ru": "Для студентов", "kk": "Студенттерге", "en": "For students"},
    "hub.lead": {"ru": "Соцсети, бонусы, связь с администрацией, материалы и ваш контент в одном месте.", "kk": "Әлеуметтік желілер, бонустар, әкімшілікпен байланыс, материалдар және сіздің контентіңіз бір жерде.", "en": "Social media, perks, contacting the administration, materials and your content in one place."},
    "social.title": {"ru": "Соцсети и клубы", "kk": "Әлеуметтік желілер мен клубтар", "en": "Social media and clubs"},
    "social.lead": {"ru": "Официальные аккаунты колледжа и студенческих организаций.", "kk": "Колледж бен студенттік ұйымдардың ресми аккаунттары.", "en": "Official accounts of the college and student organisations."},
    "bonus.title": {"ru": "Студенческие бонусы", "kk": "Студенттік бонустар", "en": "Student perks"},
    "bonus.lead": {"ru": "Предложения для студентов от партнёров колледжа.", "kk": "Колледж серіктестерінің студенттерге арналған ұсыныстары.", "en": "Offers for students from college partners."},
    "bonus.go": {"ru": "Перейти к партнёру", "kk": "Серіктеске өту", "en": "Go to partner"},
    "bonus.promo": {"ru": "Промокод", "kk": "Промокод", "en": "Promo code"},
    "bonus.copy": {"ru": "Скопировать", "kk": "Көшіру", "en": "Copy"},
    "bonus.copied": {"ru": "Скопировано", "kk": "Көшірілді", "en": "Copied"},
    "contact.title": {"ru": "Связь с администрацией", "kk": "Әкімшілікпен байланыс", "en": "Contact the administration"},
    "contact.lead": {"ru": "Выберите подразделение, к которому относится ваш вопрос, предложение или обращение.", "kk": "Сұрағыңыз, ұсынысыңыз немесе өтінішіңіз қатысты бөлімшені таңдаңыз.", "en": "Choose the office your question, suggestion or request relates to."},
    "contact.name": {"ru": "ФИО", "kk": "Аты-жөні", "en": "Full name"},
    "contact.group": {"ru": "Группа", "kk": "Топ", "en": "Group"},
    "contact.reach": {"ru": "Телефон или почта для ответа", "kk": "Жауап үшін телефон немесе пошта", "en": "Phone or email for a reply"},
    "contact.kind": {"ru": "Тип обращения", "kk": "Өтініш түрі", "en": "Type"},
    "contact.message": {"ru": "Сообщение", "kk": "Хабарлама", "en": "Message"},
    "library.title": {"ru": "Библиотека материалов", "kk": "Материалдар кітапханасы", "en": "Materials library"},
    "library.lead": {"ru": "Официальные логотипы и фирменные материалы для учебных проектов, роликов, презентаций и публикаций.", "kk": "Оқу жобаларына, бейнелерге, презентациялар мен жарияланымдарға арналған ресми логотиптер мен фирмалық материалдар.", "en": "Official logos and brand assets for student projects, videos, presentations and posts."},
    "library.download": {"ru": "Скачать", "kk": "Жүктеу", "en": "Download"},
    "content.title": {"ru": "Студенческий контент", "kk": "Студенттік контент", "en": "Student content"},
    "content.lead": {"ru": "Отправьте фото и видео с мероприятий, идеи для роликов и предложения по развитию соцсетей.", "kk": "Іс-шаралардан фото мен бейне, ролик идеяларын және әлеуметтік желілерді дамыту бойынша ұсыныстарды жіберіңіз.", "en": "Send photos and videos from events, ideas for reels and suggestions for our social media."},
    "kb.answer": {"ru": "Подходящие ответы", "kk": "Сәйкес жауаптар", "en": "Matching answers"},
    "kb.steps": {"ru": "Как сделать", "kk": "Қалай жасау керек", "en": "How to do it"},

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
