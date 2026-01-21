# Шаг 2: GoalService — приоритеты и бюджет

## Briefing
- **Цель:** Расширить GoalService для поддержки множественных целей: снять ограничение D009, добавить методы управления приоритетами и бюджетом накоплений.
- **Ключевые файлы:**
  - `app/services/goal_service.py` (изменить)
  - `tests/test_goal_service_priority.py` (создать)
- **Additional info:**
  - Ограничение D009 находится в методе `create_goal()` — проверка `active_goals_count >= 1`
  - Алгоритм shift-down для update_priority из solution-v3.md
  - Методы бюджета добавляются в GoalService (не UserService) чтобы избежать circular dependency

## Sub-tasks

1. **Удалить ограничение D009** из `create_goal()`:
   - Найти и удалить проверку `if active_goals_count >= 1: raise ValidationError`
   - Обновить docstring метода

2. **Добавить метод `get_next_priority()`**:
   ```python
   def get_next_priority(self, session: Session, user_id: int) -> int:
       """Возвращает следующий приоритет для новой цели.

       Returns:
           int: max(priority среди ACTIVE целей) + 1, или 1 если нет активных
       """
   ```

3. **Обновить `create_goal()`** для использования auto-priority:
   - Вызывать `get_next_priority()` если priority не указан
   - Добавить опциональный параметр `priority: int | None = None`

4. **Добавить метод `update_priority()`** с shift-down алгоритмом:
   ```python
   def update_priority(
       self, session: Session, goal_id: int, new_priority: int
   ) -> Goal:
       """Изменяет приоритет цели с автоматическим сдвигом конфликтующих."""
   ```
   Алгоритм:
   - Если new < old: сдвинуть цели с priority >= new AND < old на +1
   - Если new > old: сдвинуть цели с priority > old AND <= new на -1
   - Установить new_priority для цели

5. **Добавить convenience методы**:
   ```python
   def move_priority_up(self, session: Session, goal_id: int) -> Goal:
       """Перемещает цель на один приоритет вверх (уменьшает priority)."""

   def move_priority_down(self, session: Session, goal_id: int) -> Goal:
       """Перемещает цель на один приоритет вниз (увеличивает priority)."""
   ```

6. **Добавить методы бюджета**:
   ```python
   def get_savings_budget(self, session: Session, user_id: int) -> Decimal:
       """Получает месячный бюджет накоплений пользователя."""

   def update_savings_budget(
       self, session: Session, user_id: int, budget: Decimal
   ) -> None:
       """Обновляет бюджет накоплений пользователя."""
   ```

7. **Обновить `get_all_by_user()`**: всегда сортировать по priority ASC.

8. **Написать тесты** в `tests/test_goal_service_priority.py` (6 тестов):
   - `test_get_next_priority_empty` — возвращает 1 если нет целей
   - `test_get_next_priority_with_goals` — возвращает max+1
   - `test_create_goal_auto_priority` — auto-priority работает
   - `test_update_priority_shift_up` — сдвиг при повышении приоритета
   - `test_update_priority_shift_down` — сдвиг при понижении приоритета
   - `test_move_priority_up_down` — convenience методы работают

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-8.

2. **Верификация:**
   ```bash
   black app/services/goal_service.py tests/test_goal_service_priority.py
   flake8 app/services/goal_service.py tests/test_goal_service_priority.py
   pytest tests/test_goal_service_priority.py -v
   pytest tests/test_goal_service.py -v  # Существующие тесты
   pytest tests/ -v  # Все тесты
   ```

3. **Фиксация:**
   - Добавь запись в `log.md`
   - Обнови `context.md`: `Current Step` = 3
   - Проверь ветку main

4. **Коммит:**
   ```bash
   git add .
   git commit -m "feat(services): extend GoalService with priorities and budget [protocol-0006/02]"
   git push
   ```

5. **Отчет пользователю.**
