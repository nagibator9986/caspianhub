"""Проверка вёрстки в реальном браузере: переполнение, тёмная тема, ошибки консоли.

Запуск: сначала `PORT=5055 python run.py`, затем `python layout_check.py`
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5055"
WIDTHS = (390, 768, 1024, 1440, 1920)

PUBLIC = ["/", "/services", "/courses", "/news", "/faq", "/about", "/support",
          "/search?q=журнал", "/services/smartnation", "/category/study",
          "/learn/smartnation", "/learn/smartnation/lesson/1",
          "/auth/login", "/auth/register", "/nosuchpage"]

STUDENT = ["/account/", "/account/favorites", "/account/learning",
           "/account/certificates", "/account/profile", "/learn/smartnation/quiz"]

ADMIN = ["/admin/", "/admin/services", "/admin/services/1", "/admin/services/new",
         "/admin/categories", "/admin/courses", "/admin/courses/1",
         "/admin/courses/1/quiz", "/admin/lessons/1", "/admin/news",
         "/admin/news/new", "/admin/faq", "/admin/testimonials", "/admin/menu",
         "/admin/home", "/admin/settings", "/admin/users", "/admin/users/3",
         "/admin/feedback", "/admin/media", "/admin/analytics", "/admin/log"]

PROBE = """() => {
  const doc = document.documentElement;
  const overflow = document.body.scrollWidth - doc.clientWidth;
  const clipped = [];

  // Элемент внутри горизонтального скроллера выходить за экран может — это норма
  const inScroller = (el) => {
    let p = el.parentElement;
    while (p && p !== document.body) {
      const ox = getComputedStyle(p).overflowX;
      if (ox === 'auto' || ox === 'scroll') return true;
      p = p.parentElement;
    }
    return false;
  };
  // Подписи для скринридеров намеренно схлопнуты в 1px
  const isScreenReaderOnly = (el) => {
    let p = el;
    while (p && p !== document.body) {
      if ((p.className || '').toString().includes('sr-only')) return true;
      p = p.parentElement;
    }
    return false;
  };

  document.querySelectorAll('a,button,h1,h2,h3,span,p,td,th,label,input,select').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || !el.offsetParent) return;
    if (isScreenReaderOnly(el)) return;
    if (el.closest('.marquee, .aurora, .swiper')) return;

    const cls = (el.className || '').toString();
    // scrollWidth раздувают и декоративные псевдоэлементы (свечение карточек),
    // поэтому обрезку засчитываем, только если реально вылезает дочерний элемент
    const childOverflows = [...el.children].some(kid => {
      const kr = kid.getBoundingClientRect();
      const er = el.getBoundingClientRect();
      return kr.width > 0 && (kr.right > er.right + 2 || kr.left < er.left - 2);
    });
    if (cs.overflow === 'hidden' && el.scrollWidth > el.clientWidth + 2 && childOverflows &&
        !cls.includes('truncate') && !cls.includes('line-clamp') && !inScroller(el)) {
      clipped.push(((el.textContent || '').trim().slice(0, 30) || el.tagName) +
                   ' [' + el.clientWidth + '<' + el.scrollWidth + ']');
    }
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > doc.clientWidth + 2 && cs.position !== 'fixed' && !inScroller(el)) {
      clipped.push('ЗА ЭКРАНОМ: ' + ((el.textContent || '').trim().slice(0, 30) || el.tagName));
    }
  });

  const rawIcons = document.querySelectorAll('i[data-lucide]').length;
  return { overflow, clipped: [...new Set(clipped)].slice(0, 5), rawIcons };
}"""


def login(page, email, password):
    page.goto(f"{BASE}/auth/login", wait_until="domcontentloaded")
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"], form button:not([type="button"])')
    page.wait_for_load_state("domcontentloaded")


def scan(page, routes, label, problems, widths=WIDTHS):
    print(f"\n{'═' * 78}\n {label}\n{'═' * 78}")
    for route in routes:
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)[:120]))
        row = []
        for width in widths:
            page.set_viewport_size({"width": width, "height": 900})
            try:
                page.goto(BASE + route, wait_until="domcontentloaded", timeout=40000)
                page.wait_for_timeout(500)
                data = page.evaluate(PROBE)
            except Exception as exc:
                problems.append(f"{route} @{width}: {type(exc).__name__}")
                row.append(f"{width}:ОШИБКА")
                continue

            issues = []
            if data["overflow"] > 2:
                issues.append(f"гор.прокрутка +{data['overflow']}px")
            if data["clipped"]:
                issues.append("обрезано: " + "; ".join(data["clipped"][:2]))
            if data["rawIcons"]:
                issues.append(f"{data['rawIcons']} иконок не отрисовано")
            if issues:
                problems.append(f"{route} @{width}px — " + " | ".join(issues))
                row.append(f"{width}:✗")
            else:
                row.append(f"{width}:✓")
        if errors:
            problems.append(f"{route} — JS-ошибка: {errors[0]}")
        print(f"  {' '.join(row):<46} {route}")


def main() -> int:
    problems: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")

        ctx = browser.new_context()
        page = ctx.new_page()
        scan(page, PUBLIC, "ПУБЛИЧНЫЕ СТРАНИЦЫ", problems)
        ctx.close()

        ctx = browser.new_context()
        page = ctx.new_page()
        login(page, "student@ccu.edu.kz", "student123")
        scan(page, STUDENT, "ЛИЧНЫЙ КАБИНЕТ", problems)
        ctx.close()

        ctx = browser.new_context()
        page = ctx.new_page()
        login(page, "admin@ccu.edu.kz", "admin123")
        scan(page, ADMIN, "ПАНЕЛЬ УПРАВЛЕНИЯ", problems, widths=(768, 1440, 1920))
        ctx.close()

        # Тёмная тема на ключевых страницах
        ctx = browser.new_context(color_scheme="dark")
        page = ctx.new_page()
        scan(page, ["/", "/services", "/services/smartnation", "/learn/smartnation/lesson/1"],
             "ТЁМНАЯ ТЕМА", problems, widths=(390, 1440))
        ctx.close()

        browser.close()

    print("\n" + "═" * 78)
    if problems:
        print(f" НАЙДЕНО ПРОБЛЕМ: {len(problems)}\n" + "═" * 78)
        for item in problems:
            print("  •", item)
        return 1
    print(" ВЁРСТКА ЧИСТАЯ НА ВСЕХ ШИРИНАХ\n" + "═" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
