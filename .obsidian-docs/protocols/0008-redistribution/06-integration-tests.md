# Шаг 6: Integration тесты

## Briefing
- **Цель:** Создать E2E тесты для проверки полного flow перераспределения: от добавления взноса до подтверждения/отклонения.
- **Ключевые файлы:**
  - `tests/test_redistribution_integration.py` (создать)
- **Additional info:**
  - Тесты проверяют взаимодействие между GoalService, AllocationService, RedistributionService
  - Проверка корректности данных после confirm/decline
  - Проверка edge cases: no remaining goals, skipped goal, repeated contribution

## Sub-tasks

1. **Создать `tests/test_redistribution_integration.py`:**
   - Импорты: pytest, Decimal, date, сервисы, модели

2. **Fixtures для integration тестов:**
   ```python
   @pytest.fixture
   def setup_goals_for_redistribution(db_session, test_user):
       """Создать набор целей для тестирования перераспределения."""
       goal_service = GoalService(db_session)

       # Goal 1: почти достигнута (current=9500, target=10000)
       goal1 = goal_service.create_goal(
           user_id=test_user.id,
           name="Отпуск",
           target_amount=Decimal("10000"),
           target_date=date(2026, 6, 1),
       )
       goal_service.add_contribution(goal1.id, Decimal("9500"), date.today())

       # Goal 2: ACTIVE, частично накоплена
       goal2 = goal_service.create_goal(...)

       # Goal 3: ACTIVE, пустая
       goal3 = goal_service.create_goal(...)

       db_session.commit()
       return goal1, goal2, goal3
   ```

3. **Тест: Goal completion triggers preview calculation:**
   - `test_goal_completion_triggers_redistribution_preview`
   - Добавить взнос 500 к goal1 (достигает цели)
   - Проверить: goal1.is_completed = True
   - Вызвать calculate_redistribution_preview()
   - Проверить: freed_budget > 0, has_remaining_goals = True

4. **Тест: Repeated contribution to completed goal:**
   - `test_repeated_contribution_no_redistribution`
   - Goal уже COMPLETED
   - Добавить еще один взнос
   - Проверить: just_completed = False (was_completed_before = True)

5. **Тест: Confirm updates allocation:**
   - `test_confirm_redistribution_updates_allocation`
   - Достигнуть goal1
   - Получить old_allocation (до confirm)
   - "Confirm" redistribution
   - Получить new_allocation (после confirm)
   - Проверить: goal2 и goal3 получили больше allocation

6. **Тест: Decline keeps allocation unchanged:**
   - `test_decline_redistribution_keeps_allocation`
   - Достигнуть goal1
   - Получить allocation
   - "Decline" redistribution
   - Проверить: allocation не изменился (goal1 просто excluded)

7. **Тест: No remaining goals scenario:**
   - `test_no_remaining_goals_scenario`
   - Создать только одну цель
   - Достигнуть её
   - Проверить: has_remaining_goals = False, new_allocation = None

8. **Тест: Skipped goal in old allocation:**
   - `test_skipped_goal_freed_budget_zero`
   - Goal с низким приоритетом, который был skipped в allocation
   - Достигнуть его
   - Проверить: freed_budget = 0, was_skipped_in_old_allocation = True

## Workflow (Порядок работы)

1. **Выполнение:** Создай файл тестов с всеми test cases.

2. **Базовая проверка:**
   ```bash
   python -m py_compile tests/test_redistribution_integration.py
   # Запустить тесты:
   pytest tests/test_redistribution_integration.py -v --tb=short
   ```

3. **Фиксация:**
   - **Добавь запись в `log.md`**: Список E2E тестов и покрытые сценарии.
   - **Обнови `context.md`**: Current Step = 7, Next Action для финализации.
   - Проверь ветку main.

4. **Сделай коммит:**
   ```bash
   git add . && git commit -m "test(redistribution): add E2E integration tests [protocol-0008/06]"
   ```
   Сделай пуш.

5. **Отчет пользователю.**
