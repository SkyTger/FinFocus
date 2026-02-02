# Шаг 7: Callbacks интеграция

## Briefing

- **Цель:** Интегрировать recalculate в save_budget и update_contribution
- **Ключевые файлы:**
  - `app/components/goals.py` (save_budget callback)
  - `app/services/budget_reservation_service.py` (update_contribution_transaction)
- **Доп. информация:** Порядок вызовов в save_budget важен!

## Sub-tasks

1. **Модифицировать save_budget callback** (goals.py):

   ```python
   def save_budget(n_clicks, budget_value, ...):
       # ... существующий код ...

       # Порядок вызовов ВАЖЕН:
       # 1. update_savings_budget() — обновить User.monthly_savings_budget
       goal_service.update_savings_budget(user_id, Decimal(budget_value))

       # 2. set_mode() — использует НОВОЕ значение бюджета
       reservation_service.set_mode(user_id, mode, day_of_month)

       # 3. recalculate_current_month_exception() — пересчитывает с НОВЫМ бюджетом
       reservation_service.recalculate_current_month_exception(user_id)

       db_session.commit()
       # ...
   ```

   Добавить комментарий про порядок вызовов.

2. **Модифицировать update_contribution_transaction** (budget_reservation_service.py):

   ```python
   def update_contribution_transaction(self, transaction_id: int, new_amount: Decimal) -> bool:
       # ... существующий код обновления ...

       # НОВОЕ: После обновления — пересчитать exception
       if contribution and contribution.goal:
           user_id = contribution.goal.user_id
           self.recalculate_current_month_exception(
               user_id=user_id,
               reference_date=contribution.contribution_date,
           )

       return True
   ```

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка обоих файлов
3. Обнови log.md, context.md
4. Коммит: `git add . && git commit -m "feat(budget): integrate recalculate in callbacks [protocol-0018/07]"`
5. Push
