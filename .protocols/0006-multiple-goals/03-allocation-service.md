# Шаг 3: AllocationService

## Briefing
- **Цель:** Создать новый сервис для распределения бюджета накоплений между целями по приоритетам с использованием жадного алгоритма.
- **Ключевые файлы:**
  - `app/services/allocation_service.py` (создать)
  - `app/services/__init__.py` (обновить экспорты)
  - `tests/test_allocation_service.py` (создать)
- **Additional info:**
  - Жадный алгоритм: приоритет 1 получает первым min(needed, remaining)
  - Только ACTIVE цели с monthly_contribution > 0 получают allocation
  - PAUSED/COMPLETED цели получают skipped_reason
  - Использовать TypedDicts из app/types/goals.py

## Sub-tasks

1. **Создать `app/services/allocation_service.py`**:
   ```python
   """Сервис распределения бюджета накоплений между целями."""

   from decimal import Decimal
   from app.models.database import Goal, GoalStatus
   from app.schema.goals import AllocationResult, AllocationSummary


   class AllocationService:
       """Сервис распределения бюджета накоплений между целями.

       Использует жадный алгоритм: цели обрабатываются в порядке priority (1, 2, 3...),
       каждая получает минимум из (needed, remaining_budget).
       """

       def calculate_allocation(
           self,
           goals: list[Goal],
           monthly_budget: Decimal,
       ) -> AllocationSummary:
           """Распределяет бюджет между целями по приоритету."""
   ```

2. **Реализовать жадный алгоритм** в `calculate_allocation()`:
   - Сортировка по priority ASC
   - Для каждой цели:
     - Если COMPLETED → skipped_reason="completed", allocated=0
     - Если PAUSED → skipped_reason="paused", allocated=0
     - Если monthly_contribution <= 0 → skipped_reason="zero_contribution", allocated=0
     - Иначе: allocated = min(needed, remaining_budget)
   - Подсчет total_allocated, total_needed, total_shortfall
   - Формирование AllocationSummary

3. **Обновить `app/services/__init__.py`**:
   - Добавить импорт и экспорт AllocationService
   - Добавить экспорт типов из app/types/goals

4. **Написать тесты** в `tests/test_allocation_service.py` (7 тестов):

   ```python
   def test_empty_goals_list():
       """Пустой список целей → пустой results, все totals = 0."""

   def test_single_goal_fully_funded():
       """Одна цель, бюджет покрывает → is_fully_funded=True, shortfall=0."""

   def test_single_goal_partially_funded():
       """Одна цель, бюджет НЕ покрывает → is_fully_funded=False, shortfall > 0."""

   def test_multiple_goals_full_coverage():
       """Несколько целей, бюджет покрывает все → all_goals_funded=True."""

   def test_multiple_goals_partial_coverage():
       """3 цели с приоритетами 1,2,3, бюджет покрывает только 1.5 цели.
       Цель 1: fully funded
       Цель 2: partially funded
       Цель 3: not funded (allocated=0)
       """

   def test_zero_budget():
       """Нулевой бюджет → budget_not_set=True, все allocated=0."""

   def test_mixed_statuses():
       """Цели с разными статусами (ACTIVE, PAUSED, COMPLETED).
       ACTIVE получают allocation, остальные — skipped_reason.
       """
   ```

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-4.

2. **Верификация:**
   ```bash
   black app/services/allocation_service.py tests/test_allocation_service.py
   flake8 app/services/allocation_service.py tests/test_allocation_service.py
   pytest tests/test_allocation_service.py -v
   pytest tests/ -v
   ```

3. **Фиксация:**
   - Добавь запись в `log.md`
   - Обнови `context.md`: `Current Step` = 4
   - Проверь ветку main

4. **Коммит:**
   ```bash
   git add .
   git commit -m "feat(services): add AllocationService with greedy algorithm [protocol-0006/03]"
   git push
   ```

5. **Отчет пользователю.**
