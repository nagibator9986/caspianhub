/* Панель управления: редактор Markdown, drag&drop сортировка, вкладки, слаги. */
(function () {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  /* ── Markdown-редакторы ─────────────────────────────────────────── */
  function initEditors() {
    if (!window.EasyMDE) return;
    $$('[data-editor]').forEach((el) => {
      if (el.dataset.editorReady) return;
      el.dataset.editorReady = '1';
      new window.EasyMDE({
        element: el,
        spellChecker: false,
        autoDownloadFontAwesome: false,
        status: ['lines', 'words'],
        minHeight: el.dataset.editorHeight || '220px',
        placeholder: el.getAttribute('placeholder') || 'Текст в формате Markdown…',
        toolbar: ['bold', 'italic', 'heading', '|', 'quote', 'unordered-list', 'ordered-list',
                  '|', 'link', 'image', 'table', 'code', '|', 'preview', 'side-by-side', 'guide'],
      });
    });
  }

  /* ── Вкладки (в т.ч. языковые) ──────────────────────────────────── */
  function initTabs() {
    $$('[data-tabs]').forEach((group) => {
      const buttons = $$('[data-tab]', group);
      const panels = $$('[data-panel]', group);
      const activate = (key) => {
        buttons.forEach((b) => b.classList.toggle('is-active', b.dataset.tab === key));
        panels.forEach((p) => p.classList.toggle('hidden', p.dataset.panel !== key));
        if (group.dataset.tabs !== 'lang') {
          try { localStorage.setItem('tab:' + (group.dataset.tabsKey || location.pathname), key); } catch (e) {}
        }
      };
      buttons.forEach((b) => b.addEventListener('click', (e) => { e.preventDefault(); activate(b.dataset.tab); }));
      let initial = buttons[0] && buttons[0].dataset.tab;
      if (location.hash.length > 1) {
        const fromHash = buttons.find((b) => b.dataset.tab === location.hash.slice(1));
        if (fromHash) initial = fromHash.dataset.tab;
      } else if (group.dataset.tabs !== 'lang') {
        try {
          const saved = localStorage.getItem('tab:' + (group.dataset.tabsKey || location.pathname));
          if (saved && buttons.some((b) => b.dataset.tab === saved)) initial = saved;
        } catch (e) {}
      }
      if (initial) activate(initial);
    });
  }

  /* ── Сортировка перетаскиванием ─────────────────────────────────── */
  function initSortable() {
    if (!window.Sortable) return;
    $$('[data-sortable]').forEach((list) => {
      const entity = list.dataset.sortable;
      new window.Sortable(list, {
        handle: '.drag-handle',
        animation: 180,
        ghostClass: 'sortable-ghost',
        chosenClass: 'sortable-chosen',
        onEnd: async () => {
          const order = $$('[data-id]', list).map((el) => el.dataset.id);
          try {
            const res = await fetch(`/admin/reorder/${entity}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN || '' },
              body: JSON.stringify({ order }),
            });
            if (!res.ok) throw new Error();
            if (window.hubToast) window.hubToast('Порядок сохранён');
          } catch (e) {
            if (window.hubToast) window.hubToast('Не удалось сохранить порядок', 'error');
          }
        },
      });
    });
  }

  /* ── Автогенерация slug из названия ─────────────────────────────── */
  const TRANSLIT = { а:'a',б:'b',в:'v',г:'g',д:'d',е:'e',ё:'e',ж:'zh',з:'z',и:'i',й:'y',к:'k',л:'l',
    м:'m',н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',у:'u',ф:'f',х:'h',ц:'ts',ч:'ch',ш:'sh',щ:'sch',ъ:'',
    ы:'y',ь:'',э:'e',ю:'yu',я:'ya',ә:'a',ғ:'g',қ:'q',ң:'ng',ө:'o',ұ:'u',ү:'u',һ:'h',і:'i' };

  function slugify(value) {
    return value.toLowerCase().split('').map((c) => (TRANSLIT[c] !== undefined ? TRANSLIT[c] : c))
      .join('').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 90);
  }

  function initSlug() {
    $$('[data-slug-source]').forEach((source) => {
      const target = $(source.dataset.slugSource);
      if (!target) return;
      let touched = target.value.trim().length > 0;
      target.addEventListener('input', () => { touched = true; });
      source.addEventListener('input', () => { if (!touched) target.value = slugify(source.value); });
    });
    $$('[data-slugify]').forEach((input) => {
      input.addEventListener('blur', () => { if (input.value) input.value = slugify(input.value); });
    });
  }

  /* ── Предпросмотр загружаемой картинки ──────────────────────────── */
  function initImagePreview() {
    $$('[data-preview-for]').forEach((input) => {
      const box = $(input.dataset.previewFor);
      if (!box) return;
      input.addEventListener('change', () => {
        const file = input.files && input.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
          box.innerHTML = `<img src="${e.target.result}" alt="" class="w-full h-full object-contain">`;
        };
        reader.readAsDataURL(file);
      });
    });
  }

  /* ── Синхронизация цвета (color + text) ─────────────────────────── */
  function initColorSync() {
    $$('[data-color-sync]').forEach((picker) => {
      const text = $(picker.dataset.colorSync);
      if (!text) return;
      picker.addEventListener('input', () => { text.value = picker.value.toUpperCase(); });
      text.addEventListener('input', () => {
        if (/^#[0-9a-fA-F]{6}$/.test(text.value)) picker.value = text.value;
      });
    });
  }

  /* ── Счётчик символов ───────────────────────────────────────────── */
  function initCounters() {
    $$('[data-maxlen]').forEach((field) => {
      const max = parseInt(field.dataset.maxlen, 10);
      const out = document.createElement('span');
      out.className = 'help block text-right';
      field.insertAdjacentElement('afterend', out);
      const update = () => {
        const n = field.value.length;
        out.textContent = `${n} / ${max}`;
        out.style.color = n > max ? '#E11D48' : 'var(--ink-4)';
      };
      field.addEventListener('input', update);
      update();
    });
  }

  /* ── Графики дашборда ───────────────────────────────────────────── */
  function initCharts() {
    if (!window.Chart) return;
    const css = getComputedStyle(document.documentElement);
    const brand = css.getPropertyValue('--brand').trim() || '#EB5A40';
    const brand2 = css.getPropertyValue('--brand-2').trim() || '#F9A03F';
    const ink4 = css.getPropertyValue('--ink-4').trim() || '#A8A29E';
    const line = css.getPropertyValue('--line').trim() || 'rgba(0,0,0,.08)';

    window.Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
    window.Chart.defaults.color = ink4;

    const area = $('#chart-activity');
    if (area && area.dataset.chart) {
      const data = JSON.parse(area.dataset.chart);
      const ctx = area.getContext('2d');
      const grad = ctx.createLinearGradient(0, 0, 0, 260);
      grad.addColorStop(0, brand + '55');
      grad.addColorStop(1, brand + '00');
      new window.Chart(ctx, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [
            { label: 'Просмотры', data: data.views, borderColor: brand, backgroundColor: grad,
              fill: true, tension: 0.38, borderWidth: 2.5, pointRadius: 0, pointHoverRadius: 5 },
            { label: 'Переходы', data: data.clicks, borderColor: brand2, backgroundColor: 'transparent',
              tension: 0.38, borderWidth: 2, borderDash: [5, 4], pointRadius: 0, pointHoverRadius: 5 },
          ],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: { legend: { position: 'top', align: 'end', labels: { usePointStyle: true, boxWidth: 7, padding: 16 } } },
          scales: {
            x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } },
            y: { beginAtZero: true, grid: { color: line }, border: { display: false }, ticks: { precision: 0 } },
          },
        },
      });
    }

    const donut = $('#chart-categories');
    if (donut && donut.dataset.chart) {
      const data = JSON.parse(donut.dataset.chart);
      new window.Chart(donut, {
        type: 'doughnut',
        data: {
          labels: data.labels,
          datasets: [{
            data: data.values,
            backgroundColor: ['#EB5A40', '#F59E0B', '#0EA5E9', '#10B981', '#8B5CF6', '#EC4899', '#64748B'],
            borderWidth: 0, hoverOffset: 10,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: '64%',
          plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 7, padding: 14 } } },
        },
      });
    }
  }

  function boot() {
    if (window.lucide) window.lucide.createIcons();
    initEditors(); initTabs(); initSortable(); initSlug();
    initImagePreview(); initColorSync(); initCounters(); initCharts();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
