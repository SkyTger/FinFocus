# Шаг 6: Unit Tests

## Briefing

- **Цель:** Написать unit тесты для tooltip функций
- **Ключевые файлы:**
  - `tests/test_calendar_tooltip.py` — новый файл
- **Доп. информация:** ~15 тестов для покрытия основных сценариев

## Sub-tasks

1. **Создать файл tests/test_calendar_tooltip.py**

2. **Тесты для TransactionInfo**:
   - `test_transaction_info_has_category_icon`
   - `test_transaction_info_has_is_skipped`

3. **Тесты для _build_tooltip_balance()**:
   - `test_build_tooltip_balance_positive`
   - `test_build_tooltip_balance_negative`
   - `test_build_tooltip_balance_zero`

4. **Тесты для _build_tooltip_transaction_row()**:
   - `test_build_tooltip_row_income`
   - `test_build_tooltip_row_expense`
   - `test_build_tooltip_row_skipped`
   - `test_build_tooltip_row_recurring_icon`
   - `test_build_tooltip_row_no_category`

5. **Тесты для _build_day_tooltip()**:
   - `test_build_day_tooltip_empty_transactions`
   - `test_build_day_tooltip_few_transactions`
   - `test_build_day_tooltip_many_transactions_has_expand`
   - `test_build_day_tooltip_aria_attributes`

6. **Запустить тесты**:
   ```bash
   pytest tests/test_calendar_tooltip.py -v
   ```

## Workflow

1. Выполни Sub-tasks
2. Убедись что все тесты проходят
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 7
5. Коммит: `git add . && git commit -m "test(calendar): add tooltip unit tests [protocol-0015/06]"`
6. Push
7. Отчёт
