# Шаг 1: Formatters + DashboardService

## Briefing

- **Цель:** Добавить format_date_human(), get_upcoming_transactions(), рефакторинг get_recent_transactions(), unit тесты
- **Ключевые файлы:**
  - `app/utils/formatters.py` — +MONTH_NAMES_RU_GENITIVE, +format_date_human()
  - `app/services/dashboard_service.py` — +get_upcoming_transactions(), refactor get_recent_transactions(), +is_recurring_instance
  - `tests/test_formatters.py` — +3 теста format_date_human
  - `tests/test_dashboard_service.py` — +9 тестов
- **Доп. информация:** Solution v3 Steps 1-3. Intentional semantic change в get_recent_transactions() (month range вместо global). SQL фильтр: NOT (is_recurring=True AND recurring_parent_id IS NULL).

## Sub-tasks

1. **format_date_human()** в formatters.py:
   - Добавить `MONTH_NAMES_RU_GENITIVE` dict (12 месяцев, генитив)
   - Добавить `format_date_human(date_obj: date) -> str` — формат "5 февраля"
   - Экспорт в `__init__.py` если нужно

2. **RecentTransaction TypedDict** расширение:
   - Добавить `is_recurring_instance: bool` в dashboard_service.py

3. **get_recent_transactions()** рефакторинг:
   - Добавить `reference_date: date | None = None` параметр
   - first_of_month..reference_date фильтр
   - Новый recurring фильтр: `~((Transaction.is_recurring == True) & (Transaction.recurring_parent_id == None))`
   - Маппинг: `is_recurring_instance=t.recurring_parent_id is not None`
   - Docstring: INTENTIONAL SEMANTIC CHANGE

4. **get_upcoming_transactions()** новый метод:
   - reference_date..end_of_month, ASC sort
   - Те же recurring фильтры
   - limit=5 default

5. **Unit тесты** (3 formatter + 9 service):
   - format_date_human: day1 "1 января", day15 "15 июня", day31 "31 декабря"
   - upcoming: basic, empty, limit, sorting_asc, excludes_templates, includes_recurring_instances
   - recent: month_range, sorting_desc, includes_recurring_instances

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/utils/formatters.py app/services/dashboard_service.py`
3. Запусти тесты: `pytest tests/test_formatters.py tests/test_dashboard_service.py -v`
4. Обнови `log.md` — что сделано, неочевидные решения
5. Обнови `context.md` — Current Step: 2, Next Action: Шаг 2
6. Коммит: `git add . && git commit -m "feat(dashboard): add format_date_human and upcoming transactions [protocol-0023/01]"`
7. Push
8. Отчёт по формату из report-format.md.tpl
