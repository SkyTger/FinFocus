# Шаг 4: CalendarService Integration

## Briefing

- **Цель:** Добавить SAVINGS_RESERVE и SAVINGS_CONTRIBUTION в расчёты баланса календаря
- **Ключевые файлы:**
  - `app/services/calendar_service.py` — 4 метода для обновления
- **Доп. информация:** Оба типа уменьшают баланс (как EXPENSE)

## Sub-tasks

1. **_calculate_balance_before_date()** — добавить в SQL filter:
   ```python
   Transaction.transaction_type.in_([
       TransactionType.INCOME,
       TransactionType.EXPENSE,
       TransactionType.ADJUSTMENT,
       TransactionType.SAVINGS_RESERVE,      # NEW
       TransactionType.SAVINGS_CONTRIBUTION, # NEW
   ])
   ```

2. **_get_daily_changes()** — обновить case expression:
   ```python
   case(
       (TransactionType.INCOME, Transaction.amount),
       (TransactionType.ADJUSTMENT, Transaction.amount),
       (TransactionType.EXPENSE, -Transaction.amount),
       (TransactionType.SAVINGS_RESERVE, -Transaction.amount),      # NEW
       (TransactionType.SAVINGS_CONTRIBUTION, -Transaction.amount), # NEW
       else_=Decimal("0"),
   )
   ```

3. **_get_recurring_instances_for_period()** — добавить обработку:
   ```python
   if inst["transaction_type"] == "income":
       # ...existing
   elif inst["transaction_type"] in ("expense", "savings_reserve"):
       # уменьшить баланс
   ```

4. **_get_recurring_daily_changes()** — аналогично п.3

5. **TransactionInfo** — убедиться что новые типы отображаются:
   - SAVINGS_RESERVE: иконка 💼
   - SAVINGS_CONTRIBUTION: иконка 🎯

6. **Unit тесты** `tests/test_calendar_service.py`:
   - calculate_daily_balances с SAVINGS_RESERVE
   - calculate_daily_balances с SAVINGS_CONTRIBUTION
   - Recurring SAVINGS_RESERVE генерация

## Workflow

1. Выполни Sub-tasks
2. Проверка: `python -m py_compile app/services/calendar_service.py`
3. Тесты: `pytest tests/test_calendar_service.py -v`
4. Обнови `log.md`
5. Обнови `context.md` — Current Step: 5
6. Коммит: `git add . && git commit -m "feat(calendar): integrate SAVINGS_RESERVE/CONTRIBUTION [protocol-0016/04]"`
7. Push
