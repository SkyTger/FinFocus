# Шаг 5: Edit Callback

## Briefing

- **Цель:** Реализовать Pattern-Matching callback для клика по операции в tooltip
- **Ключевые файлы:**
  - `app/components/calendar.py` — добавить callback open_edit_from_tooltip()
- **Доп. информация:** ADR-003 guard clauses обязательны

## Sub-tasks

1. **Добавить импорт ALL** если не импортирован:
   ```python
   from dash.dependencies import ALL
   ```

2. **Реализовать callback open_edit_from_tooltip()**:
   ```python
   @callback(
       [
           Output("edit-modal", "is_open", allow_duplicate=True),
           Output("edit-transaction-id", "data", allow_duplicate=True),
           Output("recurring-edit-context", "data", allow_duplicate=True),
           Output("recurring-edit-scope-modal", "is_open", allow_duplicate=True),
       ],
       Input({"type": "tooltip-txn", "date": ALL, "id": ALL, "is_virtual": ALL, "template_id": ALL}, "n_clicks"),
       prevent_initial_call=True,
   )
   def open_edit_from_tooltip(n_clicks_list: list[int | None]):
       """Открывает модал редактирования при клике на операцию в tooltip."""
       ...
   ```

3. **Добавить ADR-003 guard clauses** (4 guards):
   - Guard #1: triggered_id exists
   - Guard #2: correct type (dict with type="tooltip-txn")
   - Guard #3: real click (ctx.triggered[0].get("value") is not None)
   - Guard #4: n_clicks > 0

4. **Логика обработки**:
   - Если is_virtual=True → открыть recurring-edit-scope-modal
   - Иначе → открыть edit-modal с edit-transaction-id

5. **Добавить logger.debug** для отладки:
   - При открытии scope modal
   - При открытии edit modal

## Workflow

1. Выполни Sub-tasks
2. Проверка: `python -m py_compile app/components/calendar.py`
3. Запустить приложение, проверить:
   - Клик на обычную операцию → открывается edit-modal
   - Клик на виртуальную recurring → открывается scope-modal
   - Клик на день (не на операцию) → открывается create-modal (как раньше)
4. Обнови `log.md`
5. Обнови `context.md` — Current Step: 6
6. Коммит: `git add . && git commit -m "feat(calendar): add tooltip click callback [protocol-0015/05]"`
7. Push
8. Отчёт
