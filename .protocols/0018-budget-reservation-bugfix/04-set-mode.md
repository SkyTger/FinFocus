# Шаг 4: set_mode модификация

## Briefing

- **Цель:** Модифицировать set_mode() для переиспользования шаблона
- **Ключевые файлы:**
  - `app/services/budget_reservation_service.py`
- **Доп. информация:** Ключевое изменение — если день совпадает, реактивируем а не создаём новый

## Sub-tasks

1. Изменить логику set_mode() для режима fixed_date:

   ```python
   def set_mode(self, user_id: int, mode: ReservationMode, day_of_month: int | None = None):
       # ... существующая валидация ...

       if mode == "fixed_date":
           if day_of_month is None:
               raise ValueError("day_of_month required for fixed_date mode")

           # НОВОЕ: поиск существующего шаблона
           existing_template = self._find_any_reserve_template(user_id)

           if existing_template:
               existing_day = self._get_template_day(existing_template)

               if existing_day == day_of_month:
                   # Тот же день — реактивируем (exceptions сохраняются!)
                   if existing_template.recurring_end_date is not None:
                       existing_template.recurring_end_date = None
                       self.session.flush()
                       logger.info(f"Reactivated template {existing_template.id} for user {user_id}")
                   # Иначе шаблон уже активен
               else:
                   # Другой день — останавливаем старый, чистим exceptions, создаём новый
                   self._stop_reserve_template(user_id)
                   self._cleanup_orphan_exceptions(existing_template.id)
                   self._create_reserve_template(user_id, day_of_month)
           else:
               # Нет шаблона — создаём новый
               self._create_reserve_template(user_id, day_of_month)

       elif mode == "from_balance":
           # Останавливаем шаблон если есть (exceptions НЕ чистим — пригодятся при возврате)
           self._stop_reserve_template(user_id)

       # Обновляем настройки пользователя
       user = self._get_user(user_id)
       user.reservation_mode = mode
       if mode == "fixed_date":
           user.reservation_day = day_of_month
       self.session.flush()

       return self.get_settings(user_id)
   ```

2. Добавить комментарии про сохранение exceptions

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка
3. Обнови log.md, context.md
4. Коммит: `git add . && git commit -m "feat(budget): modify set_mode for template reuse [protocol-0018/04]"`
5. Push
