/* ══════════════════════════════════════════════════════════════════════════
   Caspian College Hub — клиентская логика и хореография анимаций
   ══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => Array.from(root.querySelectorAll(s));

  /* ── Тема ──────────────────────────────────────────────────────────── */
  const Theme = {
    key: 'ccu-hub-theme',
    get() {
      try { return localStorage.getItem(this.key); } catch (e) { return null; }
    },
    apply(mode) {
      document.documentElement.classList.toggle('dark', mode === 'dark');
      try { localStorage.setItem(this.key, mode); } catch (e) { /* приватный режим */ }
      $$('[data-theme-icon]').forEach((el) => {
        el.setAttribute('data-lucide', mode === 'dark' ? 'sun' : 'moon');
      });
      if (window.lucide) window.lucide.createIcons();
      document.dispatchEvent(new CustomEvent('themechange', { detail: { mode } }));
    },
    toggle() {
      this.apply(document.documentElement.classList.contains('dark') ? 'light' : 'dark');
    },
    init() {
      const saved = this.get();
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      this.apply(saved || (prefersDark ? 'dark' : 'light'));
      $$('[data-theme-toggle]').forEach((b) => b.addEventListener('click', () => this.toggle()));
    },
  };

  /* ── Уведомления ───────────────────────────────────────────────────── */
  let notyf = null;
  function toast(message, type = 'success') {
    if (!window.Notyf) return;
    if (!notyf) {
      notyf = new window.Notyf({
        duration: 3600,
        position: { x: 'right', y: 'top' },
        ripple: true,
        types: [
          { type: 'success', background: 'linear-gradient(135deg,#EB5A40,#F9A03F)', icon: false },
          { type: 'error', background: '#E11D48', icon: false },
          { type: 'info', background: '#0EA5E9', icon: false },
        ],
      });
    }
    notyf.open({ type, message });
  }
  window.hubToast = toast;

  /* ── Плавная прокрутка (Lenis) ─────────────────────────────────────── */
  function initSmoothScroll() {
    if (reduced || !window.Lenis || window.innerWidth < 1024) return;
    const lenis = new window.Lenis({ duration: 1.05, smoothWheel: true, wheelMultiplier: 0.9 });
    function raf(time) { lenis.raf(time); requestAnimationFrame(raf); }
    requestAnimationFrame(raf);
    window.__lenis = lenis;
    if (window.ScrollTrigger) {
      lenis.on('scroll', window.ScrollTrigger.update);
    }
    $$('a[href^="#"]').forEach((a) => {
      a.addEventListener('click', (e) => {
        const id = a.getAttribute('href');
        if (id.length > 1 && $(id)) { e.preventDefault(); lenis.scrollTo(id, { offset: -100 }); }
      });
    });
  }

  /* ── Появление элементов при скролле ───────────────────────────────── */
  function initReveal() {
    const items = $$('.reveal, .reveal-scale');
    if (!items.length) return;
    if (reduced || !('IntersectionObserver' in window)) {
      items.forEach((el) => el.classList.add('is-in'));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const delay = parseInt(entry.target.dataset.revealDelay || '0', 10);
        setTimeout(() => entry.target.classList.add('is-in'), delay);
        io.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });
    items.forEach((el) => io.observe(el));
  }

  /* ── Индикатор прокрутки страницы ──────────────────────────────────── */
  function initScrollProgress() {
    const bar = $('#scroll-progress');
    if (!bar) return;
    const update = () => {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.width = h > 0 ? (window.scrollY / h) * 100 + '%' : '0%';
    };
    window.addEventListener('scroll', update, { passive: true });
    update();
  }

  /* ── Липкая шапка ──────────────────────────────────────────────────── */
  function initStickyNav() {
    const nav = $('.nav-root');
    if (!nav) return;
    const update = () => nav.classList.toggle('is-stuck', window.scrollY > 12);
    window.addEventListener('scroll', update, { passive: true });
    update();
  }

  /* ── Счётчики ──────────────────────────────────────────────────────── */
  function initCounters() {
    const els = $$('[data-count]');
    if (!els.length) return;
    const run = (el) => {
      const target = parseFloat(el.dataset.count) || 0;
      if (reduced || !window.countUp) { el.textContent = target.toLocaleString('ru-RU'); return; }
      const c = new window.countUp.CountUp(el, target, {
        duration: 2.1, separator: ' ', decimalPlaces: (target % 1 ? 1 : 0),
      });
      if (!c.error) c.start(); else el.textContent = target;
    };
    if (!('IntersectionObserver' in window)) { els.forEach(run); return; }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { run(e.target); io.unobserve(e.target); } });
    }, { threshold: 0.5 });
    els.forEach((el) => io.observe(el));
  }

  /* ── Подсветка курсора на карточках сервисов ───────────────────────── */
  function initCardGlow() {
    if (reduced) return;
    $$('.svc-card').forEach((card) => {
      card.addEventListener('pointermove', (e) => {
        const r = card.getBoundingClientRect();
        card.style.setProperty('--mx', ((e.clientX - r.left) / r.width) * 100 + '%');
        card.style.setProperty('--my', ((e.clientY - r.top) / r.height) * 100 + '%');
      });
    });
  }

  /* ── Магнитные кнопки ──────────────────────────────────────────────── */
  function initMagnetic() {
    if (reduced || window.matchMedia('(hover: none)').matches) return;
    $$('.magnetic').forEach((el) => {
      const strength = parseFloat(el.dataset.magnetic || '0.28');
      el.addEventListener('pointermove', (e) => {
        const r = el.getBoundingClientRect();
        const x = (e.clientX - r.left - r.width / 2) * strength;
        const y = (e.clientY - r.top - r.height / 2) * strength;
        el.style.transform = `translate(${x}px, ${y}px)`;
      });
      el.addEventListener('pointerleave', () => { el.style.transform = ''; });
    });
  }

  /* ── Параллакс героя (GSAP) ────────────────────────────────────────── */
  function initParallax() {
    if (reduced || !window.gsap || !window.ScrollTrigger) return;
    window.gsap.registerPlugin(window.ScrollTrigger);
    $$('[data-parallax]').forEach((el) => {
      const speed = parseFloat(el.dataset.parallax) || 0.25;
      window.gsap.to(el, {
        yPercent: speed * 100,
        ease: 'none',
        scrollTrigger: { trigger: el.closest('section') || el, start: 'top bottom', end: 'bottom top', scrub: 1 },
      });
    });
  }

  /* ── Аккордеоны ────────────────────────────────────────────────────── */
  function initAccordion() {
    $$('[data-acc]').forEach((group) => {
      const single = group.dataset.acc === 'single';
      $$('.acc', group).forEach((item) => {
        const btn = $('.acc__btn', item);
        const panel = $('.acc__panel', item);
        if (!btn || !panel) return;
        panel.style.overflow = 'hidden';
        panel.style.height = item.classList.contains('is-open') ? 'auto' : '0px';
        btn.setAttribute('aria-expanded', item.classList.contains('is-open') ? 'true' : 'false');
        btn.addEventListener('click', () => {
          const willOpen = !item.classList.contains('is-open');
          if (single && willOpen) {
            $$('.acc.is-open', group).forEach((other) => {
              other.classList.remove('is-open');
              const p = $('.acc__panel', other);
              const b = $('.acc__btn', other);
              if (b) b.setAttribute('aria-expanded', 'false');
              if (p) { p.style.height = p.scrollHeight + 'px'; requestAnimationFrame(() => { p.style.transition = 'height .4s cubic-bezier(.22,1,.36,1)'; p.style.height = '0px'; }); }
            });
          }
          item.classList.toggle('is-open', willOpen);
          btn.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
          panel.style.transition = 'height .4s cubic-bezier(.22,1,.36,1)';
          if (willOpen) {
            panel.style.height = panel.scrollHeight + 'px';
            panel.addEventListener('transitionend', function once() {
              panel.style.height = 'auto'; panel.removeEventListener('transitionend', once);
            });
          } else {
            panel.style.height = panel.scrollHeight + 'px';
            requestAnimationFrame(() => { panel.style.height = '0px'; });
          }
        });
      });
    });
  }

  /* ── Живой поиск по сервисам ───────────────────────────────────────── */
  function initSearch() {
    const input = $('[data-search-input]');
    const box = $('[data-search-results]');
    if (!input || !box) return;
    let timer = null;
    let lastQuery = '';

    const render = (items, query) => {
      if (!items.length) {
        box.innerHTML = `<div class="px-5 py-8 text-center">
            <p class="text-sm ink-muted">По запросу «${escapeHtml(query)}» ничего не найдено</p>
            <p class="text-xs mt-1" style="color:var(--ink-4)">Попробуйте «журнал», «практика» или «справка»</p>
          </div>`;
      } else {
        box.innerHTML = items.map((it) => `
          <a href="${it.url}" class="flex items-start gap-3 px-4 py-3 rounded-xl hover:bg-[var(--brand-50)] transition-colors group">
            <span class="grid place-items-center w-9 h-9 rounded-xl flex-none"
                  style="background:${it.color}1a;color:${it.color}">
              <i data-lucide="${it.icon || 'app-window'}" class="w-[18px] h-[18px]"></i>
            </span>
            <span class="min-w-0">
              <span class="block text-sm font-semibold truncate group-hover:text-[var(--brand)] transition-colors">${escapeHtml(it.name)}</span>
              <span class="block text-xs ink-muted truncate">${escapeHtml(it.tagline || it.category || '')}</span>
            </span>
            ${it.has_course ? '<span class="badge badge-brand ml-auto flex-none text-[10px]">курс</span>' : ''}
          </a>`).join('');
      }
      box.classList.remove('hidden');
      if (window.lucide) window.lucide.createIcons();
    };

    const search = async (q) => {
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`, { headers: { 'X-Requested-With': 'fetch' } });
        if (!res.ok) throw new Error('search failed');
        const data = await res.json();
        if (q === lastQuery) render(data.results || [], q);
      } catch (e) {
        box.innerHTML = '<div class="px-5 py-6 text-center text-sm ink-muted">Поиск временно недоступен</div>';
        box.classList.remove('hidden');
      }
    };

    input.addEventListener('input', () => {
      const q = input.value.trim();
      lastQuery = q;
      clearTimeout(timer);
      if (q.length < 2) { box.classList.add('hidden'); box.innerHTML = ''; return; }
      timer = setTimeout(() => search(q), 220);
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { input.blur(); box.classList.add('hidden'); }
    });
    document.addEventListener('click', (e) => {
      if (!box.contains(e.target) && e.target !== input) box.classList.add('hidden');
    });
    // Ctrl/⌘+K
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault(); input.focus(); input.select();
      }
    });
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  /* ── Фильтрация каталога без перезагрузки ──────────────────────────── */
  function initCatalogFilter() {
    const grid = $('[data-catalog]');
    if (!grid) return;
    const cards = $$('[data-card]', grid);
    const empty = $('[data-catalog-empty]');
    const countEl = $('[data-catalog-count]');
    const qInput = $('[data-filter-q]');

    const state = { cat: 'all', q: '', sort: 'default' };

    const apply = () => {
      let shown = 0;
      cards.forEach((card) => {
        const okCat = state.cat === 'all' || card.dataset.category === state.cat;
        const hay = (card.dataset.search || '').toLowerCase();
        const okQ = !state.q || hay.includes(state.q);
        const visible = okCat && okQ;
        card.classList.toggle('hidden', !visible);
        if (visible) { shown++; card.style.animation = 'fade-up .5s var(--ease) both'; card.style.animationDelay = (shown * 0.03) + 's'; }
      });
      if (empty) empty.classList.toggle('hidden', shown > 0);
      if (countEl) countEl.textContent = shown;
    };

    $$('[data-filter-cat]').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.cat = btn.dataset.filterCat;
        $$('[data-filter-cat]').forEach((b) => b.classList.toggle('is-active', b === btn));
        apply();
        const url = new URL(window.location);
        if (state.cat === 'all') url.searchParams.delete('cat'); else url.searchParams.set('cat', state.cat);
        window.history.replaceState({}, '', url);
      });
    });

    if (qInput) {
      let t = null;
      qInput.addEventListener('input', () => {
        clearTimeout(t);
        t = setTimeout(() => { state.q = qInput.value.trim().toLowerCase(); apply(); }, 150);
      });
    }

    const sortSel = $('[data-filter-sort]');
    if (sortSel) {
      sortSel.addEventListener('change', () => {
        const mode = sortSel.value;
        const sorted = cards.slice().sort((a, b) => {
          if (mode === 'name') return (a.dataset.name || '').localeCompare(b.dataset.name || '', 'ru');
          if (mode === 'popular') return (+b.dataset.views || 0) - (+a.dataset.views || 0);
          if (mode === 'course') return (+b.dataset.course || 0) - (+a.dataset.course || 0);
          return (+a.dataset.position || 0) - (+b.dataset.position || 0);
        });
        sorted.forEach((c) => grid.appendChild(c));
        apply();
      });
    }

    const initial = new URL(window.location).searchParams.get('cat');
    if (initial) {
      const btn = $(`[data-filter-cat="${CSS.escape(initial)}"]`);
      if (btn) btn.click();
    }
  }

  /* ── Избранное ─────────────────────────────────────────────────────── */
  function initFavorites() {
    $$('[data-fav]').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault(); e.stopPropagation();
        const id = btn.dataset.fav;
        try {
          const res = await fetch(`/api/favorite/${id}`, {
            method: 'POST',
            headers: { 'X-CSRFToken': window.CSRF_TOKEN || '', 'Content-Type': 'application/json' },
          });
          if (res.status === 401) { toast('Войдите, чтобы сохранять избранное', 'info'); return; }
          const data = await res.json();
          btn.classList.toggle('is-fav', data.favorited);
          const icon = $('svg, i', btn);
          if (icon) icon.style.fill = data.favorited ? 'currentColor' : 'none';
          btn.style.color = data.favorited ? 'var(--brand)' : '';
          toast(data.favorited ? 'Добавлено в избранное' : 'Удалено из избранного', data.favorited ? 'success' : 'info');
        } catch (err) { toast('Не удалось сохранить', 'error'); }
      });
    });
  }

  /* ── Отметка урока пройденным ──────────────────────────────────────── */
  function initLessonComplete() {
    const btn = $('[data-lesson-complete]');
    if (!btn) return;
    btn.addEventListener('click', async () => {
      const id = btn.dataset.lessonComplete;
      btn.disabled = true;
      try {
        const res = await fetch(`/learn/lesson/${id}/complete`, {
          method: 'POST',
          headers: { 'X-CSRFToken': window.CSRF_TOKEN || '' },
        });
        if (res.status === 401) { window.location.href = btn.dataset.loginUrl || '/auth/login'; return; }
        const data = await res.json();
        const bar = $('[data-course-progress]');
        if (bar) { bar.style.width = data.progress + '%'; }
        $$('[data-progress-value]').forEach((el) => { el.textContent = data.progress + '%'; });
        if (data.completed_course) {
          burstConfetti();
          toast('Курс пройден! Сертификат ждёт вас 🎉');
          setTimeout(() => { if (data.next_url) window.location.href = data.next_url; }, 1500);
        } else {
          toast('Урок отмечен как пройденный');
          if (data.next_url) setTimeout(() => { window.location.href = data.next_url; }, 700);
        }
      } catch (err) { toast('Не удалось сохранить прогресс', 'error'); btn.disabled = false; }
    });
  }

  function burstConfetti() {
    if (reduced || !window.confetti) return;
    const colors = ['#EB5A40', '#F9A03F', '#FFC9BC', '#FFFFFF'];
    window.confetti({ particleCount: 90, spread: 72, origin: { y: 0.65 }, colors });
    setTimeout(() => window.confetti({ particleCount: 60, angle: 60, spread: 60, origin: { x: 0, y: 0.7 }, colors }), 180);
    setTimeout(() => window.confetti({ particleCount: 60, angle: 120, spread: 60, origin: { x: 1, y: 0.7 }, colors }), 300);
  }
  window.hubConfetti = burstConfetti;

  /* ── Учёт переходов на внешние сервисы ─────────────────────────────── */
  function initClickTracking() {
    $$('[data-track-service]').forEach((el) => {
      el.addEventListener('click', () => {
        const id = el.dataset.trackService;
        const url = `/api/track/${id}`;
        if (navigator.sendBeacon) navigator.sendBeacon(url);
        else fetch(url, { method: 'POST', keepalive: true, headers: { 'X-CSRFToken': window.CSRF_TOKEN || '' } });
      });
    });
  }

  /* ── Лайтбокс для скриншотов ───────────────────────────────────────── */
  function initLightbox() {
    if (!window.GLightbox || !$('.glightbox')) return;
    window.GLightbox({ selector: '.glightbox', touchNavigation: true, loop: true, openEffect: 'zoom' });
  }

  /* ── Слайдеры ──────────────────────────────────────────────────────── */
  function initSwipers() {
    if (!window.Swiper) return;
    $$('[data-swiper]').forEach((el) => {
      const perView = parseFloat(el.dataset.perView || '3');
      new window.Swiper(el, {
        slidesPerView: 1.08,
        spaceBetween: 20,
        grabCursor: true,
        autoplay: el.dataset.autoplay ? { delay: +el.dataset.autoplay, disableOnInteraction: true } : false,
        pagination: { el: el.querySelector('.swiper-pagination'), clickable: true },
        navigation: {
          nextEl: el.parentElement.querySelector('[data-swiper-next]'),
          prevEl: el.parentElement.querySelector('[data-swiper-prev]'),
        },
        breakpoints: {
          640: { slidesPerView: Math.min(2, perView), spaceBetween: 22 },
          1024: { slidesPerView: perView, spaceBetween: 26 },
        },
      });
    });
  }

  /* ── 3D-наклон карточек ────────────────────────────────────────────── */
  function initTilt() {
    if (reduced || !window.VanillaTilt || window.matchMedia('(hover: none)').matches) return;
    const els = $$('[data-tilt]');
    if (els.length) window.VanillaTilt.init(els, { max: 5, speed: 500, glare: true, 'max-glare': 0.12, scale: 1.01 });
  }

  /* ── Кольцевой прогресс ────────────────────────────────────────────── */
  function initRings() {
    $$('[data-ring]').forEach((svg) => {
      const circle = $('.ring__value', svg);
      if (!circle) return;
      const r = circle.r.baseVal.value;
      const c = 2 * Math.PI * r;
      const pct = Math.max(0, Math.min(100, parseFloat(svg.dataset.ring) || 0));
      circle.style.strokeDasharray = `${c} ${c}`;
      circle.style.strokeDashoffset = c;
      requestAnimationFrame(() => {
        setTimeout(() => { circle.style.strokeDashoffset = c - (pct / 100) * c; }, 250);
      });
    });
  }

  /* ── Копирование в буфер ───────────────────────────────────────────── */
  function initCopy() {
    $$('[data-copy]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(btn.dataset.copy);
          toast('Скопировано');
        } catch (e) { toast('Не удалось скопировать', 'error'); }
      });
    });
  }

  /* ── Мобильное меню ────────────────────────────────────────────────── */
  function initMobileMenu() {
    const btn = $('[data-menu-toggle]');
    const panel = $('[data-menu-panel]');
    if (!btn || !panel) return;
    const close = () => {
      panel.classList.add('hidden');
      btn.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    };
    btn.addEventListener('click', () => {
      const open = panel.classList.contains('hidden');
      panel.classList.toggle('hidden', !open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.style.overflow = open ? 'hidden' : '';
    });
    $$('a', panel).forEach((a) => a.addEventListener('click', close));
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
  }

  /* ── Подтверждение удаления ────────────────────────────────────────── */
  function initConfirm() {
    document.addEventListener('submit', (e) => {
      const form = e.target;
      const msg = form.dataset.confirm;
      if (msg && !window.confirm(msg)) e.preventDefault();
    });
    $$('[data-confirm-link]').forEach((a) => {
      a.addEventListener('click', (e) => { if (!window.confirm(a.dataset.confirmLink)) e.preventDefault(); });
    });
  }

  /* ── Флеш-сообщения из Flask → toast ───────────────────────────────── */
  function initFlashes() {
    const node = $('#flash-data');
    if (!node) return;
    try {
      JSON.parse(node.textContent || '[]').forEach(([cat, msg], i) => {
        const type = cat === 'danger' || cat === 'error' ? 'error' : cat === 'info' ? 'info' : 'success';
        setTimeout(() => toast(msg, type), 180 * (i + 1));
      });
    } catch (e) { /* пусто */ }
  }

  /* ── Инициализация ─────────────────────────────────────────────────── */
  function boot() {
    Theme.init();
    if (window.lucide) window.lucide.createIcons();
    if (window.AOS) window.AOS.init({ duration: 800, easing: 'ease-out-cubic', once: true, offset: 70, disable: reduced });

    initSmoothScroll(); initReveal(); initScrollProgress(); initStickyNav();
    initCounters(); initCardGlow(); initMagnetic(); initParallax();
    initAccordion(); initSearch(); initCatalogFilter(); initFavorites();
    initLessonComplete(); initClickTracking(); initLightbox(); initSwipers();
    initTilt(); initRings(); initCopy(); initMobileMenu(); initConfirm(); initFlashes();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
