# Шаг 4: Sidebar + Transactions

## Briefing

- **Цель:** Sidebar в card-контейнере с active highlight, Transactions query params handling
- **Ключевые файлы:**
  - `app/components/sidebar.py` — dbc.Card обертка, id="sidebar-nav", callback
  - `app/components/transactions.py` — +apply_url_date_filter callback
  - `app/assets/sidebar.css` — НОВЫЙ файл
- **Доп. информация:** Solution v3 Steps 8-9. Sidebar: dbc.Nav получает id, static active убирается, callback rebuilds children. Transactions: parse_qs + date.fromisoformat() с try/except.

## Sub-tasks

1. **sidebar.py** — card-контейнер:
   - Обернуть sidebar content в `dbc.Card(className="sidebar-card h-100")`
   - Убрать static `active=True` из nav_items
   - Добавить `id="sidebar-nav"` на `dbc.Nav`

2. **sidebar.py** — callback highlight_active_sidebar():
   - Input: url.pathname
   - Output: sidebar-nav.children
   - Rebuilds 5 NavLink с active=True для matching pathname
   - className "sidebar-nav-item-active" для активного элемента

3. **sidebar.css** — НОВЫЙ файл:
   - `.sidebar-card` — белый фон, border, без shadow
   - `.sidebar-nav-item-active` — border-left 4px solid var(--color-primary)

4. **transactions.py** — apply_url_date_filter():
   - Input: url.search, State: url.pathname
   - Guard: pathname != "/transactions" → PreventUpdate
   - Parse ?start=YYYY-MM-DD&end=YYYY-MM-DD
   - Validate dates с try/except (invalid → None)
   - Output: filter-date-range.start_date, filter-date-range.end_date

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/sidebar.py app/components/transactions.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 5, Next Action: Шаг 5
5. Коммит: `git add . && git commit -m "feat(sidebar): card container with active highlight + transactions query params [protocol-0023/04]"`
6. Push
7. Отчёт
