"""Сквозная проверка всех маршрутов платформы."""
import sys
import traceback

from app import create_app
from app.extensions import db
from app.models import Certificate, Course, Lesson, News, Quiz, Service, User

app = create_app()
app.config["WTF_CSRF_ENABLED"] = False


def login(client, email, password):
    return client.post("/auth/login", data={"email": email, "password": password},
                       follow_redirects=True)


def main() -> int:
    with app.app_context():
        svc = Service.query.filter_by(is_published=True).first()
        course = Course.query.filter_by(is_published=True).first()
        lesson = Lesson.query.first()
        news = News.query.first()
        cat = svc.category.slug if svc and svc.category else "study"
        user = User.query.filter_by(role="student").first()

        public_routes = [
            "/", "/services", "/courses", "/news", "/faq", "/about", "/support",
            "/search?q=журнал", "/search?q=", f"/services/{svc.slug}",
            f"/category/{cat}", f"/news/{news.slug}", f"/learn/{course.slug}",
            f"/learn/{course.slug}/lesson/{lesson.id}",
            "/api/search?q=практика", "/api/stats", "/robots.txt", "/sitemap.xml",
            "/auth/login", "/auth/register", "/?lang=kk", "/?lang=en", "/?lang=ru",
        ]

        account_routes = ["/account/", "/account/favorites", "/account/learning",
                          "/account/certificates", "/account/profile",
                          f"/learn/{course.slug}/quiz"]

        admin_routes = [
            "/admin/", "/admin/services", "/admin/services/new",
            f"/admin/services/{svc.id}", "/admin/categories", "/admin/courses",
            "/admin/courses/new", f"/admin/courses/{course.id}",
            f"/admin/courses/{course.id}/quiz", f"/admin/lessons/{lesson.id}",
            "/admin/news", "/admin/news/new", f"/admin/news/{news.id}",
            "/admin/faq", "/admin/testimonials", "/admin/menu", "/admin/home",
            "/admin/settings", "/admin/users", f"/admin/users/{user.id}",
            "/admin/feedback", "/admin/media", "/admin/analytics", "/admin/log",
        ]

    failures = []

    def check(client, routes, label):
        print(f"\n─── {label} ───")
        for route in routes:
            try:
                resp = client.get(route, follow_redirects=False)
                code = resp.status_code
                ok = code in (200, 302)
                size = len(resp.data)
                # У JSON- и текстовых ответов маленький размер — это норма
                is_html = resp.mimetype == "text/html"
                if not ok or (code == 200 and is_html and size < 900):
                    failures.append((route, code, size, ""))
                    print(f"  ✗ {code} {size:>8}b  {route}")
                else:
                    print(f"  ✓ {code} {size:>8}b  {route}")
            except Exception as exc:
                detail = traceback.format_exc().strip().splitlines()[-1]
                failures.append((route, "EXC", 0, detail))
                print(f"  ✗ EXC          {route}\n      {detail}")

    with app.test_client() as client:
        check(client, public_routes, "Публичные страницы (гость)")

    with app.test_client() as client:
        resp = login(client, "student@ccu.edu.kz", "student123")
        print(f"\nВход студента: {resp.status_code}")
        check(client, account_routes, "Личный кабинет (студент)")
        check(client, ["/", f"/services/{svc.slug}", f"/learn/{course.slug}"],
              "Публичные страницы (авторизован)")

    with app.test_client() as client:
        login(client, "admin@ccu.edu.kz", "admin123")
        check(client, admin_routes, "Панель управления (администратор)")

    print("\n" + "=" * 70)
    if failures:
        print(f"ПРОБЛЕМ: {len(failures)}")
        for route, code, size, detail in failures:
            print(f"  {code:>5} {route}")
            if detail:
                print(f"        {detail}")
        return 1
    print("ВСЕ МАРШРУТЫ РАБОТАЮТ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
