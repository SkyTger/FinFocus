# Шаг 2: DashboardService Methods

## Briefing

- **Цель:** Добавить `get_daily_cashflow()`, `get_yearly_cashflow()` и private helpers в DashboardService.
- **Ключевые файлы:**
  - `app/services/dashboard_service.py` — MOD (+220 строк)
- **Доп. информация:** Использует CalendarService.calculate_daily_balances() для balance и CalendarService.get_recurring_income_expense_by_day() для recurring. Рекомендация critique-v2: оптимизировать Year mode (batch вместо x12 get_balance_on_date).

## Sub-tasks

1. **Добавить `_classify_balance_status()` module-level helper:**
   - Принимает Decimal balance, возвращает BalanceStatus
   - Пороги из `app/schema/dashboard` констант

2. **Добавить `_get_daily_income_expense()` private method:**
   - SQL CASE expression: INCOME→income, EXPENSE/SAVINGS_RESERVE/SAVINGS_CONTRIBUTION→expense, ADJUSTMENT(>0)→income/(< 0)→expense(abs), TRANSFER→ignore
   - Фильтр: is_recurring==False, recurring_parent_id==None
   - GROUP BY transaction_date
   - Docstring с обоснованием ADJUSTMENT как income/expense (conscious decision)

3. **Добавить `get_daily_cashflow()` public method:**
   - CalendarService.calculate_daily_balances() для running balance
   - _get_daily_income_expense() для обычных транзакций
   - CalendarService.get_recurring_income_expense_by_day() для recurring
   - Merge + min + classify → MonthlyCashflowData
   - min_balance_point всегда non-None (daily_list гарантированно непуст)

4. **Добавить `_get_monthly_income_expense()` private method:**
   - Рекомендация critique-v2: переиспользовать `_get_daily_income_expense()` вместо дублирования SQL CASE
   - Вызвать _get_daily_income_expense() и просуммировать результат
   - Возвращает tuple[Decimal, Decimal]

5. **Добавить `get_yearly_cashflow()` public method:**
   - 12 месяцев: _get_monthly_income_expense + recurring + end_balance
   - Рекомендация critique-v2: использовать calculate_daily_balances(Jan 1, Dec 31) вместо 12x get_balance_on_date()
   - min по end_balance → DailyBalancePoint
   - → YearlyCashflowData

6. **Импорты:**
   - Из `app/schema.dashboard`: все TypedDicts + константы
   - `from calendar import monthrange`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/services/dashboard_service.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 3, Next Action: Шаг 3
5. Коммит: `git add . && git commit -m "feat(dashboard): add get_daily_cashflow and get_yearly_cashflow [protocol-0022/02]"`
6. Push
