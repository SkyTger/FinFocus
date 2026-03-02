# Work Log: 0022-daily-cashflow-chart — Daily & Yearly Cashflow Chart

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0022#ctx-N -->

Restore context: protocol-0022#ctx-1
Restore context: protocol-0022#ctx-2

---

## Step Log

<!--
Формат записи:
### Step XX — [название] (commit: abc1234)
- Что сделано
- Неочевидные решения и почему
- Проблемы и как решены
-->

### Step 01 — Schema + CalendarService (commit: TBD)
- Создан `app/schema/dashboard.py` (~100 строк): 8 типов/констант (BalanceStatus, BALANCE_RISK/ATTENTION_THRESHOLD, DailyCashflow, DailyBalancePoint, MonthlyCashflowData, MonthlyCashflow, YearlyCashflowData)
- Добавлен `CalendarService.get_recurring_income_expense_by_day()` — public обёртка над `_get_recurring_instances_for_period()`, возвращает `dict[date, tuple[Decimal, Decimal]]` (income, expense)
- Обновлены экспорты в `app/schema/__init__.py` и `app/services/__init__.py`
- Решение: defaultdict с lambda для tuple(Decimal, Decimal) — чтобы дни без recurring не попадали в результат (consistent API)
- Guard comment для ADJUSTMENT recurring (практически невозможен)

### Step 02 — DashboardService (commit: TBD)
- Добавлен `_classify_balance_status()` module-level helper (ok/attention/risk по порогам)
- Добавлен `_get_daily_income_expense()` — SQL CASE для INCOME/EXPENSE/SAVINGS/ADJUSTMENT, GROUP BY date
- Добавлен `get_daily_cashflow()` — merge regular + recurring, running balance, min marker → MonthlyCashflowData
- Добавлен `_get_monthly_income_expense()` — переиспользует _get_daily_income_expense() (рекомендация critique)
- Добавлен `get_yearly_cashflow()` — оптимизация: один calculate_daily_balances(Jan 1, Dec 31) вместо 12x
- ADJUSTMENT: amount > 0 → income, amount < 0 → expense(abs) — сознательное решение, documented в docstring
- Используется protected `_get_recurring_totals_for_period` для Year mode recurring (допустимо — тот же сервисный слой)

### Step 03 — Unit Tests (commit: TBD)
- 12 тестов TestGetDailyCashflow: basic, no_txn, risk/attention/ok statuses, min_middle, cumulative, adjustment +/-, transfer, savings_reserve, savings_contribution
- 4 теста TestGetYearlyCashflow: 12_months, income_expense, end_balance, min_year
- Все 35 тестов файла прошли (19 старых + 16 новых)

### Step 04 — Charts + Integration (commit: TBD)
- STATUS_COLORS dict для цветовой индикации баланса (ok/attention/risk)
- _build_daily_cashflow_chart(): grouped bars (income/expense) + balance line (yaxis2) + diamond min marker + today dashed line
- _build_yearly_cashflow_chart(): аналогичная структура, X=месяцы, current month rect highlight
- _load_dashboard_components(): единая точка загрузки, устраняет дублирование между load_dashboard_data и refresh_dashboard_after_crud
- update_period_state расширен: Store хранит {period, year, month}
- open_create_from_chart callback: клик на bar → create-modal с preselected-date (только month mode)
- transaction_modals.py: source="chart" → set preselected date
- Dual Y-axis: yaxis для bars, yaxis2 для balance line
- hovermode="x unified" с customdata + format_rub() для tooltip
- Единый Graph ID "daily-cashflow-chart" для обоих режимов
- 508 тестов пройдено (1 pre-existing failure в allocation precision)

### Step 05 — Finalization (commit: TBD)
- Black: 3 файла переформатированы (dashboard_service.py, test_dashboard_service.py, +1)
- Flake8: 2 ошибки исправлены (F841 unused cashflow_data, F401 unused defaultdict import)
- Удалён неиспользуемый вызов get_cashflow_data() из _load_dashboard_components
- Pytest: 508 passed (1 deselected pre-existing)
- Context.md → Status: Completed
