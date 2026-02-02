# Шаг 3: cleanup + logging

## Briefing

- **Цель:** Реализовать _cleanup_orphan_exceptions с логированием
- **Ключевые файлы:**
  - `app/services/budget_reservation_service.py`
- **Доп. информация:** logger.info() при удалении, logger.debug() если нечего удалять

## Sub-tasks

1. Добавить метод `_cleanup_orphan_exceptions(template_id: int) -> int`

2. Реализовать логику:
   ```python
   def _cleanup_orphan_exceptions(self, template_id: int) -> int:
       """Удаляет exceptions для остановленного шаблона.

       Вызывается при изменении дня месяца для очистки
       невалидных exceptions от старого шаблона.
       Удаляет ВСЕ exceptions для шаблона с recurring_end_date < today.

       Args:
           template_id: ID остановленного шаблона.

       Returns:
           int: Количество удалённых exceptions.
       """
       today = date.today()

       # Находим и удаляем все exceptions для шаблона
       exceptions_to_delete = (
           self.session.query(Transaction)
           .filter(
               Transaction.recurring_parent_id == template_id,
               Transaction.original_date.isnot(None),  # Это exception
           )
           .all()
       )

       count = len(exceptions_to_delete)
       for exc in exceptions_to_delete:
           self.session.delete(exc)

       if count > 0:
           self.session.flush()
           logger.info(
               f"Cleaned up {count} orphan exception(s) for template {template_id}"
           )
       else:
           logger.debug(
               f"No orphan exceptions to clean up for template {template_id}"
           )

       return count
   ```

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка: `python -m py_compile app/services/budget_reservation_service.py`
3. Обнови log.md, context.md
4. Коммит: `git add . && git commit -m "feat(budget): add _cleanup_orphan_exceptions with logging [protocol-0018/03]"`
5. Push
