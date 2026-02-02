# Шаг 6: GoalService

## Briefing

- **Цель:** Добавить delete_contribution() с lazy import
- **Ключевые файлы:**
  - `app/services/goal_service.py`
- **Доп. информация:** Lazy import для избежания circular dependency (паттерн уже в проекте)

## Sub-tasks

1. Добавить метод `delete_contribution(contribution_id: int) -> bool`:

   ```python
   def delete_contribution(self, contribution_id: int) -> bool:
       """Удаляет взнос и пересчитывает exception.

       Алгоритм:
       1. Находит GoalContribution по ID
       2. Если есть transaction_id — удаляет через BudgetReservationService
       3. Иначе — удаляет напрямую
       4. Обновляет Goal.current_amount
       5. Вызывает recalculate_current_month_exception()

       Args:
           contribution_id: ID взноса GoalContribution.

       Returns:
           bool: True если взнос удалён, False если не найден.
       """
       contribution = self.session.get(GoalContribution, contribution_id)
       if not contribution:
           return False

       goal = contribution.goal
       user_id = goal.user_id
       amount = contribution.amount
       contribution_date = contribution.contribution_date

       # Lazy import для избежания circular dependency
       # (паттерн уже используется в add_contribution, строки 154, 486)
       from app.services.budget_reservation_service import BudgetReservationService

       budget_service = BudgetReservationService(self.session)

       # Удаляем транзакцию если есть
       if contribution.transaction_id:
           budget_service.delete_contribution_transaction(contribution.transaction_id)
       else:
           self.session.delete(contribution)

       # Обновляем current_amount
       goal.current_amount -= amount
       if goal.current_amount < Decimal("0"):
           goal.current_amount = Decimal("0")

       # Пересчитываем exception для месяца взноса
       budget_service.recalculate_current_month_exception(
           user_id=user_id,
           reference_date=contribution_date,
       )

       self.session.flush()
       logger.info(
           f"Deleted contribution {contribution_id} for goal {goal.id}, "
           f"amount={amount}, recalculated exception"
       )
       return True
   ```

2. Добавить import Decimal если нет
3. Добавить import logger если нет

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка: `python -m py_compile app/services/goal_service.py`
3. Обнови log.md, context.md
4. Коммит: `git add . && git commit -m "feat(goals): add delete_contribution with lazy import [protocol-0018/06]"`
5. Push
