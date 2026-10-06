# Дизайн-язык Caspian College Hub — обязательная справка для шаблонов

Эталоны, на которые нужно равняться (прочитай их перед работой):
- `app/templates/public/index.html` — публичные страницы
- `app/templates/public/service_detail.html` — страница-карточка + контент
- `app/templates/learn/lesson.html` — страница с сайдбаром
- `app/templates/layouts/admin_base.html` — каркас админки
- `app/static/css/app.css` — все классы и токены

## Палитра (взята с ccu.edu.kz и логотипа колледжа)
Коралловый `#EB5A40`, акцент `#F9A03F`, графит `#6D6D6B`, белый.
**Никогда не пиши цвета напрямую** — используй токены: `var(--brand)`, `var(--brand-2)`,
`var(--brand-50)`, `var(--ink)`, `var(--ink-2)`, `var(--ink-3)`, `var(--ink-4)`,
`var(--surface)`, `var(--surface-2)`, `var(--bg)`, `var(--bg-soft)`, `var(--line)`, `var(--line-strong)`.
Тёмная тема работает автоматически через эти токены — поэтому Tailwind-классы вроде
`bg-white`, `text-gray-500`, `border-gray-200` **запрещены**. Вместо них:
`style="background:var(--surface)"`, `class="ink-muted"`, `style="border-color:var(--line)"`.

## Готовые классы (все в app.css)
- Оболочка: `.container-hub`
- Карточки: `.card`, `.card-hover`, `.svc-card` (+ `style="--glow:<цвет>"`), `.glass`, `.svc-icon`
- Кнопки: `.btn` + `.btn-primary` / `.btn-ghost` / `.btn-soft` / `.btn-dark`, размеры `.btn-sm` / `.btn-lg` / `.btn-block`, `.magnetic`
- Бейджи: `.badge` + `.badge-brand` / `-emerald` / `-amber` / `-sky` / `-rose` / `-slate`, `.pulse-dot`
- Чипы-фильтры: `.chip`, активный — `.is-active`
- Формы: `.field`, `.label`, `.help`, `.switch` (`<label class="switch"><input type="checkbox"><span></span></label>`)
- Текст: `.font-display`, `.text-gradient`, `.ink-muted`, `.prose-hub` (для Markdown)
- Прогресс: `.progress` > `.progress__bar`
- Аккордеон: обёртка `data-acc="single"`, элемент `.acc` > `.acc__btn` (+ `.acc__icon`) > `.acc__panel`
- Появление: `.reveal` / `.reveal-scale` (+ `data-reveal-delay="120"`), `.animate-fade-up`, `.stagger`, `.float`
- Фон: `.aurora` (`<div class="aurora"><span></span><span></span><span></span></div>`), `.grain`, `.grid-bg`
- Таблицы админки: `.tbl`
- Таймлайн: `.timeline`, `.timeline__dot`
- Сертификат: `.certificate`

## Иконки
Только Lucide: `<i data-lucide="имя" class="w-4 h-4"></i>`. Никаких эмодзи в интерфейсе,
никаких SVG-вставок вручную, никаких других иконочных наборов.

## Мультиязычность
Для моделей с примесью Translatable выводи **только** через `obj.tr('поле')`,
например `service.tr('name')`, `course.tr('title')`, `item.tr('answer')`.
Прямое `service.name_ru` в публичных шаблонах — ошибка.
Строки интерфейса — через `{{ t('ключ') }}` (ключи см. `app/i18n.py`).
Настройки сайта — через `{{ setting('ключ', 'значение по умолчанию') }}`.

## Фильтры Jinja
`| markdown` (безопасный HTML), `| excerpt(160)`, `| date_ru`, `| dt`,
`| plural('урок','урока','уроков')`, `| tojson_safe`.

## Правила разметки
1. Каждая страница наследует `layouts/base.html` (публичная) или `layouts/admin_base.html` (админка).
2. Блоки: `{% block title %}`, `{% block description %}`, `{% block content %}`, `{% block scripts %}`;
   в админке дополнительно `{% block heading %}`, `{% block subheading %}`, `{% block actions %}`.
3. Публичная страница начинается с секции-шапки: хлебные крошки → бейдж → h1 → подзаголовок → действия.
4. У каждого списка обязано быть пустое состояние: иконка в круге, заголовок, пояснение, кнопка действия.
5. Каждая форма содержит `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
6. Формы с файлами — `enctype="multipart/form-data"`.
7. Удаление — отдельная `<form method="post">` с `data-confirm="Точное сообщение?"`.
8. Адаптивность: сначала мобильная вёрстка, затем `sm:` / `lg:` / `xl:`. Таблицы — в `overflow-x-auto`.
9. Доступность: `aria-label` у кнопок-иконок, `alt` у картинок, `<label>` у полей.
10. Никаких `<style>`-блоков со своими цветами. Точечный inline-`style` с токенами — можно.

## Тон интерфейсных текстов
Русский, дружелюбный, на «вы», без канцелярита. «Пока пусто» вместо «Данные отсутствуют».
«Сохранить» вместо «Применить изменения». Пояснения — короткие и по делу.
