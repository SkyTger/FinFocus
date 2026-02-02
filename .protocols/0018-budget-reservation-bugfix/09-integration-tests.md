# Шаг 9: Integration тесты

## Briefing

- **Цель:** Добавить E2E тесты calendar + reservation
- **Ключевые файлы:**
  - `tests/test_budget_calendar_integration.py` (новый файл)
- **Доп. информация:** Код тестов из solution-v3.md

## Sub-tasks

1. **Создать `tests/test_budget_calendar_integration.py`**

2. **TestContributionAffectsCalendar** — 2 теста:
   - test_contribution_before_reserve_reduces_reserve_in_calendar
   - test_contribution_after_mode_switch_updates_reserve

3. **TestDeleteContributionRecalculatesReserve** — 1 тест:
   - test_delete_contribution_restores_reserve

4. **Особенности:**
   - Использовать `pytest.skip()` для дат >= reserve_day
   - Проверять через CalendarService.get_all_transactions_for_period()
   - Искать резерв по description "Резервирование"

## Workflow

1. Скопируй код тестов из solution-v3.md
2. Запусти: `pytest tests/test_budget_calendar_integration.py -v`
3. Обнови log.md, context.md
4. Коммит: `git add . && git commit -m "test(budget): add integration tests calendar + reservation [protocol-0018/09]"`
5. Push
