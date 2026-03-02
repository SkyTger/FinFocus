# Шаг 8: Unit тесты

## Briefing

- **Цель:** Добавить unit тесты для новых методов
- **Ключевые файлы:**
  - `tests/test_budget_reservation_service.py`
- **Доп. информация:** Тестовые классы из solution-v3

## Sub-tasks

1. **TestFindAnyReserveTemplate** — тесты для _find_any_reserve_template:
   - test_find_active_template
   - test_find_stopped_template
   - test_find_returns_latest_when_multiple
   - test_find_returns_none_when_no_templates

2. **TestGetTemplateDay** — тесты для _get_template_day:
   - test_normal_day
   - test_anchor_eom_returns_31
   - test_day_31_without_eom

3. **TestCleanupOrphanExceptions** — тесты для _cleanup_orphan_exceptions:
   - test_deletes_all_exceptions
   - test_logs_count_when_deleted
   - test_returns_zero_when_none

4. **TestRecalculateCurrentMonthException** — тесты для recalculate:
   - test_skips_for_from_balance_mode
   - test_skips_for_past_reserve_date
   - test_creates_exception_when_contributions_exist
   - test_deletes_exception_when_no_contributions
   - test_uses_reference_date_parameter

5. **TestUpdateContributionRecalc** — тесты для update_contribution_transaction:
   - test_recalculates_after_amount_change

## Workflow

1. Выполни Sub-tasks
2. Запусти тесты: `pytest tests/test_budget_reservation_service.py -v`
3. Обнови log.md, context.md
4. Коммит: `git add . && git commit -m "test(budget): add unit tests for new methods [protocol-0018/08]"`
5. Push
