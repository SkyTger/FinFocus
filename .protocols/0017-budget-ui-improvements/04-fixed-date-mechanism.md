# Шаг 4: Fixed Date Mechanism

## Briefing

- **Цель:** Реализовать механику корректировки резерва при досрочных взносах в режиме fixed_date
- **Ключевые файлы:**
  - `app/services/budget_reservation_service.py`
  - `app/services/recurring_service.py` (использование существующего API)
- **Доп. информация:**
  - Взнос ДО даты резерва → создать Exception с уменьшенной суммой
  - Взнос ПОСЛЕ даты резерва → только SAVINGS_CONTRIBUTION
  - Если сумма >= бюджета → Exception с amount=0 и "(внесено досрочно)"

## Sub-tasks

1. Добавить новый метод в BudgetReservationService:
   ```python
   def adjust_reserve_for_contribution(
       self,
       user_id: int,
       contribution_date: date,
       contribution_amount: Decimal
   ) -> None:
       """Корректирует сумму резерва при досрочном взносе (режим fixed_date).

       Создаёт/обновляет Exception для recurring шаблона резервирования.
       Вызывается из GoalService.add_contribution() если:
       - Режим = fixed_date
       - contribution_date < reservation_day текущего месяца

       Args:
           user_id: ID пользователя
           contribution_date: Дата взноса
           contribution_amount: Сумма взноса (для логирования)
       """
   ```

2. Реализовать логику метода:
   ```python
   # 1. Получить настройки
   settings = self.get_settings(user_id)

   # 2. Guard: только для fixed_date режима
   if settings["mode"] != "fixed_date":
       return

   # 3. Определить дату резерва текущего месяца
   reserve_day = settings["day_of_month"]
   if reserve_day is None:
       return

   # Дата резерва в текущем месяце
   reserve_date = date(contribution_date.year, contribution_date.month,
                       min(reserve_day, monthrange(contribution_date.year, contribution_date.month)[1]))

   # 4. Guard: взнос после резерва — не корректируем
   if contribution_date >= reserve_date:
       return

   # 5. Получить шаблон резерва
   template = self._get_reserve_template(user_id)
   if not template:
       return

   # 6. Посчитать сумму взносов до даты резерва в текущем месяце
   month_start = date(contribution_date.year, contribution_date.month, 1)
   contributions_sum = self.session.query(func.sum(GoalContribution.amount)).join(
       Goal, Goal.id == GoalContribution.goal_id
   ).filter(
       Goal.user_id == user_id,
       GoalContribution.contribution_date >= month_start,
       GoalContribution.contribution_date < reserve_date
   ).scalar() or Decimal("0")

   # 7. Рассчитать новую сумму
   budget = settings["monthly_budget"]
   new_amount = max(budget - contributions_sum, Decimal("0"))

   # 8. Определить description
   if new_amount == 0:
       description = f"{RESERVE_DESCRIPTION} (внесено досрочно)"
   else:
       description = RESERVE_DESCRIPTION

   # 9. Создать/обновить Exception
   from app.services import RecurringService
   recurring_service = RecurringService(self.session)
   recurring_service.create_exception(
       template_id=template.id,
       instance_date=reserve_date,
       amount=new_amount,
       description=description
   )
   ```

3. Добавить импорты если отсутствуют:
   ```python
   from calendar import monthrange
   from sqlalchemy import func
   from app.models.database import Goal, GoalContribution
   ```

4. Базовая проверка: `python -m py_compile app/services/budget_reservation_service.py`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 5, Next Action: Шаг 5
5. Коммит: `git add . && git commit -m "feat(services): add adjust_reserve_for_contribution [protocol-0017/04]"`
6. Push
7. Отчёт
