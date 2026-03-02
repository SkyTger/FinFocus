# Шаг 2: recalculate метод

## Briefing

- **Цель:** Реализовать recalculate_current_month_exception()
- **Ключевые файлы:**
  - `app/services/budget_reservation_service.py`
- **Доп. информация:** Параметр называется `reference_date` (не `month`) для консистентности

## Sub-tasks

1. Добавить метод `recalculate_current_month_exception(user_id: int, reference_date: date | None = None) -> bool`

2. Реализовать логику:
   ```python
   def recalculate_current_month_exception(...):
       if reference_date is None:
           reference_date = date.today()

       settings = self.get_settings(user_id)

       # Guard: только fixed_date режим
       if settings["mode"] != "fixed_date":
           return False

       reserve_date = self._get_reserve_date_for_month(user_id, reference_date)
       if reserve_date is None:
           return False

       # Guard: не пересчитываем прошедшие даты (ВАЖНО: < а не <=)
       # Если reserve_date == today, recurring экземпляр ещё не материализован
       if reserve_date < date.today():
           logger.debug(f"Reserve date {reserve_date} already passed, skipping recalc")
           return False

       template = self._get_reserve_template(user_id)
       if not template:
           logger.warning(f"No active template for user {user_id}, skipping recalc")
           return False

       # Считаем взносы ДО даты резерва (< reserve_date, не <=)
       contributions_sum = self._get_contributions_sum_for_month(
           user_id, reserve_date, before_date=reserve_date
       )

       budget = settings["monthly_budget"]
       new_reserve = budget - contributions_sum

       if new_reserve == budget:
           # Нет взносов — удаляем exception
           return self._delete_exception_for_date(template.id, reserve_date)
       else:
           # Создаём/обновляем exception
           self.recurring_service.create_exception(
               template_id=template.id,
               exception_date=reserve_date,
               new_amount=new_reserve,
           )
           return True
   ```

3. Добавить docstring с описанием параметра reference_date

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка: `python -m py_compile app/services/budget_reservation_service.py`
3. Обнови log.md, context.md
4. Коммит: `git add . && git commit -m "feat(budget): add recalculate_current_month_exception [protocol-0018/02]"`
5. Push
