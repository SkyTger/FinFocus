# Work Log: 0023-dashboard-layout — Dashboard Layout Redesign (Batch 5.3)

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0023#ctx-N -->

---

## Step Log

<!--
Формат записи:
### Step XX — [название] (commit: abc1234)
- Что сделано
- Неочевидные решения и почему
- Проблемы и как решены
-->

### Step 01 — Formatters + DashboardService (commit: pending)
- Добавлен `format_date_human()` + `MONTH_NAMES_RU_GENITIVE` в formatters.py
- Добавлено `is_recurring_instance: bool` в RecentTransaction TypedDict
- Рефакторинг `get_recent_transactions()`: добавлен `reference_date` параметр, фильтр first_of_month..reference_date, новый recurring фильтр (исключает только шаблоны, включает instances)
- Добавлен `get_upcoming_transactions()`: reference_date..end_of_month, ASC sort, аналогичные фильтры
- Добавлен `_map_transactions()` helper для устранения дублирования маппинга
- Обновлены существующие тесты: передан `reference_date` в 3 старых теста
- 12 новых тестов: 3 formatter + 3 recent refactor + 6 upcoming
- Все 57 тестов (13+44) прошли
Restore context: protocol-0023#ctx-1

### Step 02 — Reconciliation globalization (commit: pending)
- calendar.py: удален dcc.Store("calendar-refresh-trigger"), удален create_reconciliation_modal() из layout
- calendar.py: удален callback refresh_calendar_after_reconciliation() (дублировал refresh_calendar_after_transaction)
- calendar.py: apply_reconciliation() Output "calendar-refresh-trigger" → "global-transaction-trigger" (allow_duplicate=True), return data расширен source/action
- main.py: добавлен import create_reconciliation_modal, вызов в app.layout после create_wishlist_modal()
- dashboard.py: KPI recon_button — dcc.Link(href=...) → dbc.Button(id="open-recon-from-dashboard-btn")
- dashboard.py: Banner — dcc.Link(dbc.Button(...)) → dbc.Button(id="open-recon-from-dashboard-banner-btn")
- dashboard.py: новый callback open_recon_from_dashboard() — 2 Inputs → Output open-recon-trigger (timestamp)
- dashboard.py: type hint dcc.Link → dbc.Button в _build_kpi_card()
- Все 3 файла: py_compile OK

### Step 03 — Dashboard UI rebuild (commit: pending)
- Новая функция _build_empty_state(): icon, message, button_id
- Новая функция _build_transactions_split_table(): format_date_human, recurring icon 🔁, без "Completed" бейджей, ссылка "Все операции"
- Новая функция _build_cushion_card_readonly(): CushionService.get_settings(), readonly прогресс-бар, link→/goals
- create_dashboard_layout() перестроен: split 8/4, split tables 50/50, cushion + stats в правой колонке
- _load_dashboard_components() расширен: +get_upcoming_transactions(), +cushion card, 6 outputs
- load_dashboard_data и refresh_dashboard_after_crud: 6 Outputs
- Новый callback open_create_from_empty(): 2 Inputs (empty-recent-add-btn, empty-upcoming-add-btn) → create-modal
- Import CushionService + format_date_human
- py_compile OK
