# Шаг 5: GoalService Integration

## Briefing

- **Цель:** Расширить add_contribution для создания транзакций и валидации
- **Ключевые файлы:**
  - `app/services/goal_service.py` — add_contribution, update_savings_budget
- **Доп. информация:** Интеграция с BudgetReservationService

## Sub-tasks

1. **add_contribution()** — расширить:
   ```python
   def add_contribution(
       self,
       goal_id: int,
       amount: Decimal,
       contribution_date: date | None = None,
       description: str | None = None,
   ) -> Goal:
       # Валидация amount > 0
       if amount <= 0:
           raise ValidationError("Сумма взноса должна быть больше 0")

       # Guard: нельзя вносить в COMPLETED
       if goal.status == GoalStatus.COMPLETED:
           raise ValidationError(f"Невозможно внести взнос в завершенную цель")

       # Создать транзакцию через BudgetReservationService
       budget_service = BudgetReservationService(self.session)
       transaction = budget_service.create_contribution_transaction(
           user_id=goal.user_id,
           goal_name=goal.name,
           amount=amount,
           contribution_date=contribution_date or date.today(),
       )

       # Создать GoalContribution с transaction_id
       contribution = GoalContribution(
           goal_id=goal_id,
           amount=amount,
           contribution_date=contribution_date or date.today(),
           description=description,
           transaction_id=transaction.id if transaction else None,
       )
   ```

2. **update_savings_budget()** — вызвать sync_template_amount:
   ```python
   def update_savings_budget(self, user_id: int, budget: Decimal) -> None:
       # ... existing logic ...

       # Синхронизировать recurring шаблон если режим fixed_date
       budget_service = BudgetReservationService(self.session)
       budget_service.sync_template_amount(user_id)
   ```

3. **Warning logging** при budget=0:
   ```python
   if user.monthly_savings_budget == 0:
       logger.warning(f"Взнос {amount} в цель {goal_id} без настроенного бюджета")
   ```

4. **Unit тесты** `tests/test_goal_service.py`:
   - add_contribution создаёт транзакцию в режиме from_balance
   - add_contribution не создаёт транзакцию в режиме fixed_date
   - add_contribution в COMPLETED цель → ValidationError
   - update_savings_budget синхронизирует шаблон

## Workflow

1. Выполни Sub-tasks
2. Проверка: `python -m py_compile app/services/goal_service.py`
3. Тесты: `pytest tests/test_goal_service.py -v`
4. Обнови `log.md`
5. Обнови `context.md` — Current Step: 6
6. Коммит: `git add . && git commit -m "feat(goals): integrate contribution transactions [protocol-0016/05]"`
7. Push
