# Шаг 2: Reconciliation глобализация

## Briefing

- **Цель:** Глобализировать reconciliation modal — доступен и с Dashboard, и с Calendar. Удалить дублирующий calendar-refresh-trigger.
- **Ключевые файлы:**
  - `app/components/calendar.py` — удалить calendar-refresh-trigger Store, удалить refresh_calendar_after_reconciliation callback, рефакторинг apply_reconciliation Output, удалить create_reconciliation_modal() из layout
  - `app/main.py` — +import create_reconciliation_modal, +вызов в app.layout
  - `app/components/dashboard.py` — замена dcc.Link на dbc.Button для recon (KPI + banner), новый callback open_recon_from_dashboard с 2 Inputs
- **Доп. информация:** Solution v3 Steps 4-5. calendar-refresh-trigger заменяется на global-transaction-trigger. refresh_calendar_after_reconciliation удаляется (дублирует refresh_calendar_after_transaction). suppress_callback_exceptions=True обрабатывает missing open-reconciliation-btn Input на Dashboard.

## Sub-tasks

1. **calendar.py** — удалить calendar-refresh-trigger:
   - Удалить `dcc.Store(id="calendar-refresh-trigger", data=None)` из create_calendar_layout()
   - Удалить вызов `create_reconciliation_modal()` из create_calendar_layout()
   - Удалить callback `refresh_calendar_after_reconciliation()` целиком
   - Рефакторинг `apply_reconciliation()`: Output `calendar-refresh-trigger` → `global-transaction-trigger` (allow_duplicate=True). Return data: `{"source": "reconciliation", "action": "create", "timestamp": ...}`

2. **main.py** — глобальный reconciliation modal:
   - Добавить `from app.components.calendar import create_reconciliation_modal`
   - Добавить `create_reconciliation_modal()` в app.layout после `create_wishlist_modal()`

3. **dashboard.py** — кнопки "Сверка":
   - В `build_overview_cards()`: заменить `dcc.Link(href="/calendar?open_recon=1")` на `dbc.Button(id="open-recon-from-dashboard-btn")`
   - В `_build_balance_banner()`: заменить `dcc.Link(dbc.Button(...), href="/calendar?open_recon=1")` на `dbc.Button("Сверить баланс", id="open-recon-from-dashboard-banner-btn")`
   - Новый callback `open_recon_from_dashboard()` с 2 Inputs (KPI btn + banner btn) → Output open-recon-trigger

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/calendar.py app/main.py app/components/dashboard.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 3, Next Action: Шаг 3
5. Коммит: `git add . && git commit -m "refactor(reconciliation): globalize modal and replace calendar-refresh-trigger [protocol-0023/02]"`
6. Push
7. Отчёт
