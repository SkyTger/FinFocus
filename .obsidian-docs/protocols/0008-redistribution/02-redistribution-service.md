# Шаг 2: RedistributionService

## Briefing
- **Цель:** Создать RedistributionService с "Temporary Status Pattern" для расчета preview перераспределения, включая timing logs для NFR-2 и аудит-логирование для NFR-4.
- **Ключевые файлы:**
  - `app/services/redistribution_service.py` (создать)
  - `app/services/__init__.py` (модифицировать — экспорт)
- **Additional info:**
  - "Temporary Status Pattern": временное изменение goal.status в памяти (без DB commit) для расчета OLD allocation
  - Timing logs через time.perf_counter() с WARNING при превышении 50ms (NFR-2)
  - Метод log_redistribution_event() для аудита (NFR-4)
  - DI pattern: AllocationService передается через конструктор для тестируемости

## Sub-tasks

1. **Создать `app/services/redistribution_service.py`:**
   - Импорты: time, datetime, Decimal, loguru, GoalStatus, AllocationService, GoalService, TypedDicts
   - Константа `NFR2_WARNING_THRESHOLD_MS = 50.0`

2. **Реализовать класс RedistributionService:**
   ```python
   class RedistributionService:
       def __init__(self, goal_service: GoalService, allocation_service: AllocationService | None = None):
           """DI pattern для тестируемости."""
           self.goal_service = goal_service
           self.allocation_service = allocation_service or AllocationService()
   ```

3. **Реализовать `calculate_redistribution_preview()`:**
   - Принимает: completed_goal, all_goals, monthly_budget, savings_mode
   - Возвращает: RedistributionPreview
   - **CRITICAL**: Реализовать "Temporary Status Pattern":
     1. Сохранить original_status = goal.status
     2. Временно установить goal.status = ACTIVE
     3. Вычислить old_allocation
     4. Восстановить goal.status = original_status
     5. Вычислить new_allocation
     6. **finally блок** для гарантированного восстановления статуса
   - Timing logs: start_time → elapsed_ms → WARNING если > 50ms
   - Подсчет remaining_goals (ACTIVE, excluding completed)

4. **Реализовать `get_freed_budget_from_allocation()`:**
   - Принимает: completed_goal_id, old_allocation
   - Возвращает: tuple[Decimal, bool] — (freed_budget, was_skipped)
   - Найти goal в old_allocation.results
   - Если skipped_reason is not None → return (0, True)
   - Иначе → return (allocated_amount, False)
   - Логировать если goal не найден (error)

5. **Реализовать `log_redistribution_event()`:**
   - Принимает: user_id, completed_goal, freed_budget, remaining_goals_count, action, new_allocation
   - Создает RedistributionEvent
   - Логирует через loguru.info()
   - Возвращает event для возможного использования

6. **Обновить `app/services/__init__.py`:**
   - Добавить экспорт RedistributionService

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи.

2. **Базовая проверка:**
   ```bash
   python -m py_compile app/services/redistribution_service.py
   ```

3. **Фиксация:**
   - **Добавь запись в `log.md`**: Опиши реализованный сервис, особенно "Temporary Status Pattern".
   - **Обнови `context.md`**: Current Step = 3, Next Action для тестов сервиса.
   - Проверь ветку main.

4. **Сделай коммит:**
   ```bash
   git add . && git commit -m "feat(services): add RedistributionService with Temporary Status Pattern [protocol-0008/02]"
   ```
   Сделай пуш.

5. **Отчет пользователю.**
