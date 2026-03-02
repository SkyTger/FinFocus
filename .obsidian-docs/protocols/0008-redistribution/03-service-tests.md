# Шаг 3: Unit тесты RedistributionService

## Briefing
- **Цель:** Покрыть RedistributionService unit тестами для всех сценариев: базовый расчет, edge cases, timing, exception safety.
- **Ключевые файлы:**
  - `tests/test_redistribution_service.py` (создать)
  - `tests/conftest.py` (прочитать — использовать существующие фикстуры)
- **Additional info:**
  - Использовать pytest fixtures для session, user, goals
  - Mock AllocationService где нужно для изоляции тестов
  - Проверить "Temporary Status Pattern" — статус восстанавливается даже при exception

## Sub-tasks

1. **Создать `tests/test_redistribution_service.py`:**
   - Импорты: pytest, Decimal, date, unittest.mock, сервисы, модели, TypedDicts

2. **Fixtures для тестов:**
   ```python
   @pytest.fixture
   def redistribution_service(db_session):
       goal_service = GoalService(db_session)
       allocation_service = AllocationService()
       return RedistributionService(goal_service, allocation_service)

   @pytest.fixture
   def sample_goals(db_session, test_user):
       """Создать 3 цели с разными приоритетами."""
       # Goal 1: priority=1, target=10000, current=10000 (COMPLETED)
       # Goal 2: priority=2, target=20000, current=5000 (ACTIVE)
       # Goal 3: priority=3, target=15000, current=0 (ACTIVE)
       pass
   ```

3. **Тесты calculate_redistribution_preview():**
   - `test_preview_basic_calculation` — базовый сценарий с 3 целями
   - `test_preview_no_remaining_goals` — все цели completed
   - `test_preview_single_remaining_goal` — одна оставшаяся цель
   - `test_preview_freed_budget_calculation` — проверка суммы freed_budget
   - `test_preview_includes_timing` — calculation_time_ms > 0

4. **Тесты Temporary Status Pattern:**
   - `test_temporary_status_restored_on_success` — статус COMPLETED после успешного расчета
   - `test_temporary_status_restored_on_exception` — статус восстанавливается при exception в AllocationService
   - `test_preview_with_active_goal_warning` — WARNING если goal уже ACTIVE

5. **Тесты get_freed_budget_from_allocation():**
   - `test_freed_budget_normal_goal` — обычный goal в allocation
   - `test_freed_budget_skipped_goal` — goal был skipped → freed_budget=0
   - `test_freed_budget_goal_not_found` — goal не найден → freed_budget=0, error log

6. **Тесты log_redistribution_event():**
   - `test_log_event_confirmed` — action="confirmed" с new_allocation
   - `test_log_event_declined` — action="declined" без new_allocation
   - `test_log_event_structure` — проверка всех полей RedistributionEvent

7. **Тесты timing (NFR-2):**
   - `test_timing_under_threshold` — DEBUG log при < 50ms
   - `test_timing_over_threshold` — WARNING log при > 50ms (с mock time.perf_counter)

## Workflow (Порядок работы)

1. **Выполнение:** Создай файл тестов с всеми test cases.

2. **Базовая проверка:**
   ```bash
   python -m py_compile tests/test_redistribution_service.py
   # Можно запустить тесты для проверки:
   pytest tests/test_redistribution_service.py -v --tb=short
   ```

3. **Фиксация:**
   - **Добавь запись в `log.md`**: Список тестов и что они покрывают.
   - **Обнови `context.md`**: Current Step = 4, Next Action для UI.
   - Проверь ветку main.

4. **Сделай коммит:**
   ```bash
   git add . && git commit -m "test(redistribution): add unit tests for RedistributionService [protocol-0008/03]"
   ```
   Сделай пуш.

5. **Отчет пользователю.**
