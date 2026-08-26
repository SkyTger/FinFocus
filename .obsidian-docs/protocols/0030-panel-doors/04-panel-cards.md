# Шаг 4: Карточки-двери

## Briefing

- **Цель:** `app/components/panel_cards.py` — чистые build-функции пяти карточек + секции CSS по эскизу v3.
- **Ключевые файлы:**
  - `app/components/panel_cards.py` — НОВЫЙ (~600 строк)
  - `app/assets/panel.css` — секции дверей и wishlist-полосы
  - читать: `.visual/finfocus-panel-dashboard/v3.html` — эскиз (карточка «Календарь» там **три** окошка, в реализации **два**)
- **Доп. информация:** solution-v4.md, секции «Двери-переходы» и RTM #59-#74 (визуальные требования эскиза с классами и цветами).

## Sub-tasks

- [ ] `_door_shell(...)` — каркас двери: заголовок в `dcc.Link`, если `href` задан. **Ни одного серверного Input** — переход делает сам `dcc.Link` (так класс регрессий C-6 не создаётся вообще)
- [ ] `build_calendar_card` — **два окошка** (сегодня, завтра), каждое `dcc.Link` на `/calendar?focus_date=<ISO>`; маркер просадки при `status == OK`, класс `pnl-flagline-strong` при `dip_free <= 0` (прямое сравнение, не константа-порог)
- [ ] `build_goals_card` — топ-цель `dcc.Link` на `/goals?goal=<id>`, сводка, строка подушки; `margin-top:auto` у подушки (заметка vision-критика эскиза)
- [ ] `build_operations_card` — две группы по `OPERATIONS_PER_GROUP`, ссылки на `/transactions?start=&end=`
- [ ] `build_analytics_card` — цифра месяца, топ-категория, мини-структура **на CSS-полоске, без Plotly**; **подпись объявленного расхождения** «расходы августа · без регулярных и взносов в цели» (`.pnl-note`)
- [ ] `build_wishlist_card` — двухуровневая дверь: тело `id="panel-wishlist-door"` (уровень 1, через Store), каждая хотелка `dcc.Link` на `/calendar?wishlist_item=<id>` (уровень 2)
- [ ] `build_cards_row(data)` — пять карточек **безусловно** (конституция FR-2); докстринг: единственный источник правды отрисовки — `<slot>["status"]`
- [ ] CSS: `.pnl-slots` (grid 4 двери) + `.pnl-wish` полосой; `.pnl-door*`, `.pnl-day`, `.pnl-day-today`, `.pnl-flagline`, `.pnl-flagline-strong`, `.pnl-bar`, `.pnl-bar-thin`, `.pnl-grp`, `.pnl-big-sum`, `.pnl-note`, `.pnl-mini-slot`, `.pnl-wish*`; цвета гнёзд из существующих `--pnl-free`/`--pnl-reserve`; адаптив 1180px/680px; `prefers-reduced-motion`
- [ ] **Проверить вёрстку двух окошек**: эскиз рисовал три, вертикальный ритм карточки не должен поехать

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/panel_cards.py`
3. Обнови `log.md`, `context.md`
4. Проверь `main` на случайные файлы
5. Коммит: `git add . && git commit -m "feat(ui): карточки-двери щитка [protocol-0030/04]"`
6. Push
7. Отчёт
