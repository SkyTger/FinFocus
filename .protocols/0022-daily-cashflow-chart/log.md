# Work Log: 0022-daily-cashflow-chart — Daily & Yearly Cashflow Chart

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0022#ctx-N -->

Restore context: protocol-0022#ctx-1

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
