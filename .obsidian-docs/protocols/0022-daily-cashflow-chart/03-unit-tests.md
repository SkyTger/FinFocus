# Шаг 3: Unit Tests

## Briefing

- **Цель:** 16 unit тестов для get_daily_cashflow() и get_yearly_cashflow()
- **Ключевые файлы:**
  - `tests/test_dashboard_service.py` — MOD (+250 строк)
- **Доп. информация:** Использовать существующие fixtures из conftest.py (db_session, test_user с starting_balance=10000). Паттерн тестирования: создать Transaction через session, вызвать service method, проверить результат.

## Sub-tasks

1. **`TestGetDailyCashflow` class (12 тестов):**
   - `test_basic_income_expense` — 2 операции (income + expense), проверка daily list, balance
   - `test_no_transactions` — пустой месяц, balance == starting_balance для всех дней
   - `test_negative_balance_risk_status` — баланс < 0, min_balance_point.status == "risk"
   - `test_attention_balance_status` — 0 <= balance < 5000, status == "attention"
   - `test_ok_balance_status` — balance >= 5000, status == "ok"
   - `test_min_balance_in_middle` — минимум в середине месяца (не в конце)
   - `test_running_balance_cumulative` — проверка кумулятивности (day2 balance = day1 balance + day2 change)
   - `test_adjustment_positive_as_income` — ADJUSTMENT amount > 0 → income bar
   - `test_adjustment_negative_as_expense` — ADJUSTMENT amount < 0 → expense bar (abs)
   - `test_transfer_not_counted` — TRANSFER не в income и не в expense
   - `test_savings_reserve_as_expense` — SAVINGS_RESERVE → expense
   - `test_savings_contribution_as_expense` — SAVINGS_CONTRIBUTION → expense

2. **`TestGetYearlyCashflow` class (4 теста):**
   - `test_returns_12_months` — len(monthly) == 12, все month номера 1-12
   - `test_monthly_income_expense` — корректная агрегация income/expense за месяц
   - `test_end_balance_correct` — end_balance совпадает с CalendarService balance
   - `test_min_balance_year` — минимум года определяется правильно

3. **Запустить тесты:**
   ```bash
   pytest tests/test_dashboard_service.py -v
   ```
   Все должны пройти.

## Workflow

1. Выполни Sub-tasks последовательно
2. Проверка: `pytest tests/test_dashboard_service.py -v`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 4, Next Action: Шаг 4
5. Коммит: `git add . && git commit -m "test(dashboard): add 16 unit tests for daily/yearly cashflow [protocol-0022/03]"`
6. Push
