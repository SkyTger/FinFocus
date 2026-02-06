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
