# Шаг 5: get_budget_progress

## Briefing

- **Цель:** Унифицировать расчёт used_budget для обоих режимов
- **Ключевые файлы:**
  - `app/services/budget_reservation_service.py`
- **Доп. информация:** mode_text = "Внесено" для обоих режимов

## Sub-tasks

1. Модифицировать get_budget_progress():

   ```python
   def get_budget_progress(
       self,
       user_id: int,
       reference_date: date | None = None,
   ) -> BudgetProgress:
       """Рассчитывает прогресс использования бюджета.

       Изменение: единообразно для обоих режимов считает взносы,
       а не резервы. mode_text = "Внесено" для обоих режимов.
       """
       if reference_date is None:
           reference_date = date.today()

       settings = self.get_settings(user_id)
       total_budget = settings["monthly_budget"]

       # Единообразный расчёт: взносы за месяц
       used_budget = self._get_contributions_sum_for_month(user_id, reference_date)

       available_budget = total_budget - used_budget
       if available_budget < Decimal("0"):
           available_budget = Decimal("0")

       progress_percent = float(used_budget / total_budget * 100) if total_budget > 0 else 0.0

       # Статус
       if progress_percent >= 100:
           status = "completed"
       elif progress_percent >= 80:
           status = "almost"
       else:
           status = "in_progress"

       return BudgetProgress(
           total_budget=total_budget,
           used_budget=used_budget,
           available_budget=available_budget,
           progress_percent=progress_percent,
           status=status,
           mode=settings["mode"],
           mode_text="Внесено",  # Единообразно для обоих режимов
       )
   ```

2. Убедиться что _get_contributions_sum_for_month() существует или добавить

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка
3. Обнови log.md, context.md
4. Коммит: `git add . && git commit -m "feat(budget): unify get_budget_progress calculation [protocol-0018/05]"`
5. Push
