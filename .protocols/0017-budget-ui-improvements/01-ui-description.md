# Шаг 1: UI Description

## Briefing

- **Цель:** Изменить текст recurring шаблона резерва с "Резерв на цели" на "Резервирование бюджета"
- **Ключевые файлы:**
  - `app/services/budget_reservation_service.py`
- **Доп. информация:** Константа RESERVE_DESCRIPTION используется при создании шаблона

## Sub-tasks

1. Изменить константу RESERVE_DESCRIPTION:
   ```python
   # Было:
   RESERVE_DESCRIPTION: str = "Резерв на цели"

   # Станет:
   RESERVE_DESCRIPTION: str = "Резервирование бюджета"
   ```

2. Проверить что "(авто)" суффикс добавляется в calendar.py (не менять)

3. Базовая проверка: `python -m py_compile app/services/budget_reservation_service.py`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/services/budget_reservation_service.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 2, Next Action: Шаг 2
5. Проверь main на случайные файлы
6. Коммит: `git add . && git commit -m "fix(services): change reserve description [protocol-0017/01]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
