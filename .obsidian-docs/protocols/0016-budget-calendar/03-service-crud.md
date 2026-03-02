# Шаг 3: BudgetReservationService CRUD

## Briefing

- **Цель:** Добавить методы для работы с транзакциями SAVINGS_CONTRIBUTION
- **Ключевые файлы:**
  - `app/services/budget_reservation_service.py` — CRUD методы
- **Доп. информация:** Синхронизация Transaction ↔ GoalContribution при edit/delete

## Sub-tasks

1. **create_contribution_transaction()**:
   ```python
   def create_contribution_transaction(
       self,
       user_id: int,
       goal_name: str,
       amount: Decimal,
       contribution_date: date,
   ) -> Transaction | None:
   ```
   - Возвращает None если mode="fixed_date"
   - Создаёт Transaction(type=SAVINGS_CONTRIBUTION)
   - description="Взнос: {goal_name}"
   - category_id=NULL (не расход с категорией)

2. **update_contribution_transaction()**:
   ```python
   def update_contribution_transaction(
       self,
       transaction_id: int,
       new_amount: Decimal,
   ) -> None:
   ```
   - Обновляет Transaction.amount
   - Находит связанный GoalContribution по transaction_id
   - Обновляет GoalContribution.amount
   - Пересчитывает Goal.current_amount (delta)
   - Проверяет GoalStatus (COMPLETED ↔ ACTIVE)

3. **delete_contribution_transaction()**:
   ```python
   def delete_contribution_transaction(self, transaction_id: int) -> None:
   ```
   - Каскадное удаление: Transaction → GoalContribution
   - Уменьшает Goal.current_amount
   - Откатывает GoalStatus если был COMPLETED

4. **sync_template_amount()**:
   ```python
   def sync_template_amount(self, user_id: int) -> None:
   ```
   - Синхронизирует сумму recurring шаблона с monthly_savings_budget
   - Вызывается при изменении бюджета

5. **Unit тесты**:
   - create_contribution_transaction — режим from_balance
   - create_contribution_transaction — режим fixed_date → None
   - update_contribution_transaction — sync с GoalContribution
   - delete_contribution_transaction — cascade delete
   - sync_template_amount — обновление суммы шаблона

## Workflow

1. Выполни Sub-tasks
2. Проверка: `python -m py_compile app/services/budget_reservation_service.py`
3. Тесты: `pytest tests/test_budget_reservation_service.py -v`
4. Обнови `log.md`
5. Обнови `context.md` — Current Step: 4
6. Коммит: `git add . && git commit -m "feat(services): add BudgetReservationService CRUD [protocol-0016/03]"`
7. Push
