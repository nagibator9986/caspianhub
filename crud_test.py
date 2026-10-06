"""Функциональная проверка админки: создание, изменение и удаление записей."""
from __future__ import annotations

import sys

from app import create_app
from app.extensions import db
from app.models import (Category, Course, Faq, Feedback, Lesson, MenuItem,
                        News, Question, Quiz, Service, Setting, Testimonial,
                        User)

app = create_app()
app.config["WTF_CSRF_ENABLED"] = False

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((name, bool(condition), detail))
    print(f"  {'✓' if condition else '✗'} {name}{('  — ' + detail) if detail and not condition else ''}")


def purge_test_data() -> None:
    """Удаляет записи от прошлых прогонов, чтобы проверки считали корректно."""
    with app.app_context():
        for model, field, needles in [
            (Service, Service.name_ru, ("Тестовый сервис", "Изменённый сервис")),
            (Course, Course.title_ru, ("Тестовый курс",)),
            (Category, Category.name_ru, ("Тестовая категория",)),
            (News, News.title_ru, ("Тестовая новость",)),
            (Faq, Faq.question_ru, ("Тестовый вопрос платформы?",)),
            (Testimonial, Testimonial.author, ("Тестовый Автор",)),
            (MenuItem, MenuItem.title_ru, ("Тестовый пункт",)),
            (Feedback, Feedback.email, ("guest@test.kz", "bot@test.kz")),
        ]:
            for needle in needles:
                for row in model.query.filter(field == needle).all():
                    db.session.delete(row)
        for row in Service.query.filter(Service.slug.like("testovyy-servis%")).all():
            db.session.delete(row)
        db.session.commit()


def main() -> int:
    purge_test_data()
    with app.test_client() as c:
        c.post("/auth/login", data={"email": "admin@ccu.edu.kz", "password": "admin123"},
               follow_redirects=True)

        # ─── Сервис ───
        print("\n── Сервисы ──")
        r = c.post("/admin/services/new", data={
            "name_ru": "Тестовый сервис", "name_kk": "Сынақ", "name_en": "Test service",
            "tagline_ru": "Короткое описание", "description_ru": "## Заголовок\n\nТекст описания.",
            "benefits_ru": "Первый плюс\nВторой плюс", "audience_ru": "Студенты",
            "slug": "", "url": "https://example.kz", "url_label_ru": "Открыть",
            "icon": "star", "color": "#123456", "accent": "#654321",
            "status": "beta", "access_level": "students", "is_published": "on",
            "position": "99", "tags": "тест, проверка", "seo_title": "SEO заголовок",
        }, follow_redirects=True)
        with app.app_context():
            svc = Service.query.filter_by(name_ru="Тестовый сервис").first()
            check("создание сервиса", svc is not None, f"HTTP {r.status_code}")
            if svc:
                check("slug сгенерирован из названия", svc.slug == "testovyy-servis", svc.slug)
                check("цвет сохранён", svc.color == "#123456", svc.color)
                check("статус сохранён", svc.status == "beta", svc.status)
                check("теги привязаны", len(svc.tags) == 2, str([t.name_ru for t in svc.tags]))
                check("казахское название сохранено", svc.name_kk == "Сынақ", svc.name_kk)
                svc_id = svc.id

        # изменение
        c.post(f"/admin/services/{svc_id}", data={
            "name_ru": "Изменённый сервис", "tagline_ru": "Новое описание",
            "slug": "testovyy-servis", "url": "https://example.kz", "icon": "star",
            "color": "#ABCDEF", "accent": "#654321", "status": "active",
            "access_level": "all", "position": "99", "tags": "один",
        }, follow_redirects=True)
        with app.app_context():
            svc = db.session.get(Service, svc_id)
            check("изменение сервиса", svc.name_ru == "Изменённый сервис", svc.name_ru)
            check("снятие с публикации без чекбокса", svc.is_published is False, str(svc.is_published))
            check("теги перезаписаны", len(svc.tags) == 1, str(len(svc.tags)))

        # FAQ сервиса
        c.post(f"/admin/services/{svc_id}/faq", data={
            "question_ru": "Тестовый вопрос?", "answer_ru": "Тестовый ответ.",
        }, follow_redirects=True)
        with app.app_context():
            svc = db.session.get(Service, svc_id)
            check("добавление FAQ сервиса", len(svc.faqs) == 1)

        # ─── Категория ───
        print("\n── Категории ──")
        c.post("/admin/categories", data={
            "name_ru": "Тестовая категория", "description_ru": "Описание",
            "slug": "", "icon": "flask-conical", "color": "#00AA00",
            "position": "9", "is_active": "on",
        }, follow_redirects=True)
        with app.app_context():
            cat = Category.query.filter_by(name_ru="Тестовая категория").first()
            check("создание категории", cat is not None)
            check("slug категории", cat and cat.slug == "testovaya-kategoriya", cat.slug if cat else "")
            cat_id = cat.id if cat else None

        # ─── Курс, модуль, урок ───
        print("\n── Курсы ──")
        c.post("/admin/courses/new", data={
            "title_ru": "Тестовый курс", "summary_ru": "Кратко о курсе",
            "outcomes_ru": "Научитесь раз\nНаучитесь два", "slug": "",
            "service_id": str(svc_id), "level": "intermediate",
            "duration_min": "25", "pass_score": "80", "is_published": "on",
            "certificate_enabled": "on",
        }, follow_redirects=True)
        with app.app_context():
            course = Course.query.filter_by(title_ru="Тестовый курс").first()
            check("создание курса", course is not None)
            check("уровень курса", course and course.level == "intermediate")
            check("проходной балл", course and course.pass_score == 80, str(course.pass_score if course else ""))
            check("пункты результата разбиты", course and len(course.outcome_list()) == 2)
            course_id = course.id if course else None

        c.post(f"/admin/courses/{course_id}/modules", data={
            "title_ru": "Тестовый модуль", "description_ru": "Описание модуля",
        }, follow_redirects=True)
        with app.app_context():
            course = db.session.get(Course, course_id)
            check("добавление модуля", len(course.modules) == 1)
            module_id = course.modules[0].id if course.modules else None

        c.post(f"/admin/modules/{module_id}/lessons/new", data={
            "title_ru": "Тестовый урок", "content_ru": "## Шаги\n\n1. Первый\n2. Второй",
            "tip_ru": "Полезный совет", "media_type": "none", "media_url": "",
            "duration_min": "7", "position": "1",
        }, follow_redirects=True)
        with app.app_context():
            course = db.session.get(Course, course_id)
            check("добавление урока", course.lesson_count == 1, str(course.lesson_count))
            lesson = course.lessons[0] if course.lessons else None
            check("длительность урока", lesson and lesson.duration_min == 7)
            check("совет сохранён", lesson and lesson.tip_ru == "Полезный совет")

        # ─── Тест ───
        print("\n── Тесты ──")
        c.post(f"/admin/courses/{course_id}/quiz", data={
            "title_ru": "Тест курса", "description_ru": "Проверка",
            "pass_score": "75", "time_limit_min": "10",
        }, follow_redirects=True)
        with app.app_context():
            quiz = Quiz.query.filter_by(course_id=course_id).first()
            check("создание теста", quiz is not None)
            check("проходной балл теста", quiz and quiz.pass_score == 75)
            quiz_id = quiz.id if quiz else None

        c.post(f"/admin/quiz/{quiz_id}/questions", data={
            "text_ru": "Сколько будет 2+2?", "explanation_ru": "Простая арифметика.",
            "option1": "3", "option2": "4", "option3": "5", "option4": "22", "correct": "2",
        }, follow_redirects=True)
        with app.app_context():
            quiz = db.session.get(Quiz, quiz_id)
            check("добавление вопроса", len(quiz.questions) == 1)
            q = quiz.questions[0] if quiz.questions else None
            check("четыре варианта", q and len(q.options) == 4, str(len(q.options) if q else 0))
            check("верный вариант отмечен", q and q.correct_option and q.correct_option.text_ru == "4",
                  q.correct_option.text_ru if q and q.correct_option else "нет")

        # ─── Новость ───
        print("\n── Новости ──")
        c.post("/admin/news/new", data={
            "title_ru": "Тестовая новость", "excerpt_ru": "Краткое описание",
            "body_ru": "Текст новости.", "slug": "", "kind": "announcement",
            "is_published": "on", "is_pinned": "on",
        }, follow_redirects=True)
        with app.app_context():
            n = News.query.filter_by(title_ru="Тестовая новость").first()
            check("создание новости", n is not None)
            check("тип новости", n and n.kind == "announcement")
            check("закрепление", n and n.is_pinned is True)
            news_id = n.id if n else None

        # ─── FAQ, отзыв, меню ───
        print("\n── FAQ, отзывы, меню ──")
        c.post("/admin/faq", data={"question_ru": "Тестовый вопрос платформы?",
                                    "answer_ru": "Ответ.", "category": "Тест",
                                    "is_active": "on"}, follow_redirects=True)
        with app.app_context():
            check("создание FAQ", Faq.query.filter_by(question_ru="Тестовый вопрос платформы?").first() is not None)
            faq_id = Faq.query.filter_by(question_ru="Тестовый вопрос платформы?").first().id

        c.post("/admin/testimonials", data={"author": "Тестовый Автор", "role_ru": "Студент",
                                             "text_ru": "Отличная платформа.", "rating": "4",
                                             "is_active": "on"}, follow_redirects=True)
        with app.app_context():
            tm = Testimonial.query.filter_by(author="Тестовый Автор").first()
            check("создание отзыва", tm is not None)
            check("рейтинг отзыва", tm and tm.rating == 4)
            tm_id = tm.id if tm else None

        c.post("/admin/menu", data={"location": "header", "title_ru": "Тестовый пункт",
                                     "url": "/test", "icon": "star", "is_active": "on",
                                     "position": "9"}, follow_redirects=True)
        with app.app_context():
            mi = MenuItem.query.filter_by(title_ru="Тестовый пункт").first()
            check("создание пункта меню", mi is not None)
            menu_id = mi.id if mi else None

        # ─── Настройки ───
        print("\n── Настройки ──")
        with app.app_context():
            rows = {s.key: s.value for s in Setting.query.all()}
        payload = dict(rows)
        payload["site_name"] = "Изменённое имя"
        payload["brand_color"] = "#112233"
        payload["enable_registration"] = "on"
        payload["active_group"] = "brand"
        c.post("/admin/settings", data=payload, follow_redirects=True)
        with app.app_context():
            check("настройка: название сайта",
                  Setting.query.filter_by(key="site_name").first().value == "Изменённое имя")
            check("настройка: цвет бренда",
                  Setting.query.filter_by(key="brand_color").first().value == "#112233")
        # вернуть как было
        payload["site_name"] = rows.get("site_name", "Caspian College Hub")
        payload["brand_color"] = rows.get("brand_color", "#EB5A40")
        c.post("/admin/settings", data=payload, follow_redirects=True)
        with app.app_context():
            check("настройки восстановлены",
                  Setting.query.filter_by(key="brand_color").first().value == "#EB5A40")

        # ─── Сортировка ───
        print("\n── Сортировка перетаскиванием ──")
        with app.app_context():
            ids = [s.id for s in Service.query.order_by(Service.position).limit(3).all()]
        r = c.post("/admin/reorder/service", json={"order": list(reversed(ids))})
        check("переупорядочивание сервисов", r.status_code == 200 and r.get_json().get("ok"))
        with app.app_context():
            first = db.session.get(Service, list(reversed(ids))[0])
            check("позиция обновилась", first.position == 1, str(first.position))

        # ─── Удаление ───
        print("\n── Удаление ──")
        for url, model, ident, label in [
            (f"/admin/news/{news_id}/delete", News, news_id, "новости"),
            (f"/admin/faq/{faq_id}/delete", Faq, faq_id, "FAQ"),
            (f"/admin/testimonials/{tm_id}/delete", Testimonial, tm_id, "отзыва"),
            (f"/admin/menu/{menu_id}/delete", MenuItem, menu_id, "пункта меню"),
            (f"/admin/courses/{course_id}/delete", Course, course_id, "курса"),
            (f"/admin/categories/{cat_id}/delete", Category, cat_id, "категории"),
            (f"/admin/services/{svc_id}/delete", Service, svc_id, "сервиса"),
        ]:
            c.post(url, follow_redirects=True)
            with app.app_context():
                check(f"удаление {label}", db.session.get(model, ident) is None)

        with app.app_context():
            check("каскад: уроки курса удалены", Lesson.query.filter_by(module_id=module_id).count() == 0)
            check("каскад: вопросы теста удалены", Question.query.filter_by(quiz_id=quiz_id).count() == 0)

    # ─── Обращения (отдельные клиенты, без вложенности) ───
    print("\n── Обращения ──")
    with app.test_client() as guest:
        guest.post("/support", data={"name": "Гость", "email": "guest@test.kz",
                                      "topic": "Вопрос", "message": "Это тестовое обращение из формы."},
                   follow_redirects=True)
        guest.post("/support", data={"name": "Бот", "email": "bot@test.kz", "topic": "Вопрос",
                                      "message": "Спам-сообщение подлиннее десяти символов.",
                                      "website": "http://spam"}, follow_redirects=True)
    with app.app_context():
        fb = Feedback.query.filter_by(email="guest@test.kz").first()
        check("обращение создано", fb is not None)
        check("honeypot отсекает ботов", Feedback.query.filter_by(email="bot@test.kz").first() is None)
        fb_id = fb.id if fb else None

    if fb_id:
        with app.test_client() as c2:
            c2.post("/auth/login", data={"email": "admin@ccu.edu.kz", "password": "admin123"},
                    follow_redirects=True)
            c2.post(f"/admin/feedback/{fb_id}", data={"status": "done", "admin_note": "Обработано"},
                    follow_redirects=True)
            with app.app_context():
                check("статус обращения изменён", db.session.get(Feedback, fb_id).status == "done")
            c2.post(f"/admin/feedback/{fb_id}/delete", follow_redirects=True)
            with app.app_context():
                check("удаление обращения", db.session.get(Feedback, fb_id) is None)

    # ─── Права доступа ───
    print("\n── Права доступа ──")
    with app.test_client() as student:
        student.post("/auth/login", data={"email": "student@ccu.edu.kz", "password": "student123"},
                     follow_redirects=True)
        check("студента не пускает в админку", student.get("/admin/").status_code == 403)
    with app.test_client() as guest:
        r = guest.get("/admin/", follow_redirects=False)
        check("гостя перенаправляет на вход", r.status_code == 302 and "/auth/login" in r.headers.get("Location", ""))
        check("гостя не пускает в кабинет", guest.get("/account/", follow_redirects=False).status_code == 302)

    failed = [name for name, ok, _ in results if not ok]
    print("\n" + "=" * 70)
    if failed:
        print(f"ПРОВАЛЕНО {len(failed)} из {len(results)}:")
        for name in failed:
            print("  •", name)
        return 1
    print(f"ВСЕ {len(results)} ПРОВЕРОК ПРОЙДЕНЫ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
