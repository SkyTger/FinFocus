# Шаг 5: Unit тесты

## Briefing

- **Цель:** Написать 22+ unit тестов для update_contribution(), delete_contribution() и calendar guard
- **Ключевые файлы:**
  - `tests/test_goal_service.py` — тесты для GoalService (или новый файл tests/test_contribution_edit.py)
  - Существующие фикстуры: `session`, `user`, `goal` (см. conftest.py)
- **Доп. информация:** См. `.design/solution-v4.md` секция "Обновленный тест-план (22 теста)"

## Sub-tasks

1. **Тесты update_contribution() — 17 тестов:**

   **Amount:**
   - `test_update_contribution_amount_increase` — увеличение суммы, goal.current_amount увеличивается
   - `test_update_contribution_amount_decrease` — уменьшение суммы, goal.current_amount уменьшается
   - `test_update_contribution_amount_zero_error` — amount=0 → error
   - `test_update_contribution_amount_negative_error` — amount<0 → error

   **Date:**
   - `test_update_contribution_date_within_month` — смена даты в рамках месяца
   - `test_update_contribution_date_across_months_recalculates_exception` — смена между месяцами → recalculate для обоих
   - `test_update_contribution_date_past_month_error` — Guard #2a: дата в прошлом месяце → error
   - `test_update_contribution_date_none_no_recalculate` — date=None → НЕ пересчитывать Exception
   - `test_update_contribution_date_far_future_error` — Guard #2b: дата через 2+ месяца → error
   - `test_update_contribution_date_next_month_ok` — дата в следующем месяце → ok

   **Description:**
   - `test_update_contribution_description_sync_transaction` — описание синхронизируется с Transaction
   - `test_update_contribution_description_empty_string_clears` — "" → очистить (default "Взнос: {name}")
   - `test_update_contribution_description_none_no_change` — None → не изменять

   **Status:**
   - `test_update_contribution_status_completed_to_active` — уменьшение → COMPLETED→ACTIVE
   - `test_update_contribution_status_active_to_completed` — увеличение до target → ACTIVE→COMPLETED
   - `test_update_contribution_exact_boundary_active` — точно на границе completed/active

   **Error:**
   - `test_update_contribution_not_found` — несуществующий ID → error

2. **Тесты delete_contribution() — 5 тестов:**
   - `test_delete_contribution_with_transaction_id_reverts_status` — удаление с transaction_id → COMPLETED→ACTIVE
   - `test_delete_contribution_without_transaction_id_reverts_status` — удаление без transaction_id → COMPLETED→ACTIVE
   - `test_delete_contribution_returns_contribution_info` — проверить ВСЕ 4 поля ContributionInfo
   - `test_delete_contribution_recalculates_exception` — вызывается recalculate
   - `test_delete_contribution_with_transaction_no_double_decrement` — Вариант A: current_amount -= amount ровно 1 раз

3. **Тест Calendar guard — 1 тест:**
   - `test_calendar_tooltip_blocks_savings_contribution` — клик на SAVINGS_CONTRIBUTION → PreventUpdate

## Workflow

1. Выполни Sub-tasks
2. Запусти все тесты: `pytest tests/ -v`
3. Убедись что все 22+ новых тестов проходят и старые не сломаны
4. Обнови `log.md`
5. Обнови `context.md` — Current Step: 6, Next Action: Шаг 6
6. Коммит: `git add . && git commit -m "test(goals): add 22 tests for contribution edit/delete [protocol-0019/05]"`
7. Push
8. Отчёт
