# Шаг 1: Helper методы

## Briefing

- **Цель:** Добавить 4 helper метода в BudgetReservationService
- **Ключевые файлы:**
  - `app/services/budget_reservation_service.py`
- **Доп. информация:** См. solution-v3.md секции интерфейсов

## Sub-tasks

1. Добавить `_find_any_reserve_template(user_id: int) -> Transaction | None`
   - Находит любой recurring шаблон резерва (включая остановленный)
   - Фильтр: `description LIKE '%Резервирование%'` или по типу SAVINGS_RESERVE
   - Сортировка по created_at DESC для получения последнего

2. Добавить `_get_template_day(template: Transaction) -> int`
   - Извлекает день месяца из шаблона
   - Для EOM anchor (recurring_anchor_eom=True) возвращает 31
   - Возвращает recurring_day_of_month

3. Добавить `_get_reserve_date_for_month(user_id: int, reference_date: date) -> date | None`
   - Возвращает дату резерва для указанного месяца
   - Учитывает короткие месяцы: min(day_of_month, last_day_of_month)
   - Возвращает None если режим != fixed_date

4. Добавить `_delete_exception_for_date(template_id: int, target_date: date) -> bool`
   - Удаляет exception для конкретной даты
   - Используется когда нет взносов (резерв = полный бюджет)
   - Возвращает True если удалён, False если не существовал

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/services/budget_reservation_service.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 2, Next Action: Шаг 2
5. Проверь что не изменились файлы в main
6. Коммит: `git add . && git commit -m "feat(budget): add helper methods for template reuse [protocol-0018/01]"`
7. Push
8. Отчёт по формату
