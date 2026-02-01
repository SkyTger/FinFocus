# Шаг 3: DOM Restructure

## Briefing

- **Цель:** Реструктурировать build_day_cell() для sibling structure (tooltip рядом с кликабельной областью, не внутри)
- **Ключевые файлы:**
  - `app/components/calendar.py` — функция build_day_cell()
- **Доп. информация:** DOM restructure решает конфликт click handlers (tooltip click не bubbles к calendar-day)

## Sub-tasks

1. **Добавить константу** в начало файла:
   ```python
   MAX_VISIBLE_TRANSACTIONS = 5
   ```

2. **Модифицировать build_day_cell()** для создания sibling structure:

   **Было:**
   ```python
   return html.Div(
       [day_number, icons, balance],
       id={"type": "calendar-day", ...},
       className=...,
   )
   ```

   **Стало:**
   ```python
   # Кликабельная область (для create-modal)
   clickable_content = html.Div(
       [day_number, icons, balance],
       id={"type": "calendar-day", "date": day_date.isoformat()},
       n_clicks=0,
       className="calendar-day-content",
   )

   # Tooltip как sibling (пока None, будет в шаге 4)
   tooltip = None  # TODO: _build_day_tooltip() в шаге 4

   # Wrapper без n_clicks
   return html.Div(
       [clickable_content, tooltip] if tooltip else [clickable_content],
       className=" ".join(css_classes),
   )
   ```

3. **Убедиться что n_clicks и id перенесены** на clickable_content, не на wrapper

4. **Проверить что CSS классы** остаются на wrapper (calendar-day, today, has-transactions, etc.)

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка: `python -m py_compile app/components/calendar.py`
3. Запустить приложение, убедиться что календарь работает
4. Обнови `log.md`
5. Обнови `context.md` — Current Step: 4
6. Коммит: `git add . && git commit -m "refactor(calendar): DOM restructure for tooltip sibling [protocol-0015/03]"`
7. Push
8. Отчёт
