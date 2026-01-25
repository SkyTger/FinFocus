# Шаг 5: Callbacks Quick-add

## Briefing

- **Цель:** Создать callbacks для открытия модала создания из Quick-add chips
- **Ключевые файлы:**
  - `app/components/transactions.py`
- **Доп. информация:** ADR-003 guard clauses обязательны для Pattern-Matching callbacks

## Sub-tasks

1. Создать `open_create_from_quick_add()`:
   ```python
   @callback(
       [
           Output("create-modal", "is_open"),
           Output("modal-source", "data"),
           Output("preselected-category", "data"),
           Output("preselected-type", "data"),
       ],
       Input({"type": "qa-chip", "category_id": ALL, "tx_type": ALL}, "n_clicks"),
       prevent_initial_call=True,
   )
   ```
   - Guard #1: `if not ctx.triggered_id: raise PreventUpdate`
   - Guard #2: `if not isinstance(ctx.triggered_id, dict): raise PreventUpdate`
   - Guard #3: `if ctx.triggered_id.get("type") != "qa-chip": raise PreventUpdate`
   - Guard #4: `if not ctx.triggered or ctx.triggered[0].get("value") is None: raise PreventUpdate`
   - Return: `(True, "quick-add", category_id, tx_type.upper())`

2. Создать `open_more_modal()`:
   ```python
   @callback(
       [
           Output("quick-add-more-modal", "is_open"),
           Output("quick-add-more-tabs", "active_tab"),
       ],
       Input({"type": "qa-more-btn", "tx_type": ALL}, "n_clicks"),
       prevent_initial_call=True,
   )
   ```
   - Guard clauses аналогичны
   - Return: `(True, tx_type)` — открывает модал с активной вкладкой

3. Создать `select_from_more_modal()`:
   ```python
   @callback(
       [
           Output("create-modal", "is_open", allow_duplicate=True),
           Output("modal-source", "data", allow_duplicate=True),
           Output("preselected-category", "data", allow_duplicate=True),
           Output("preselected-type", "data", allow_duplicate=True),
           Output("quick-add-more-modal", "is_open", allow_duplicate=True),
       ],
       Input({"type": "qa-more-category", "category_id": ALL, "tx_type": ALL}, "n_clicks"),
       prevent_initial_call=True,
   )
   ```
   - Guard clauses
   - Return: `(True, "quick-add", category_id, tx_type.upper(), False)` — закрывает "Ещё...", открывает create

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/transactions.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 6, Next Action: Шаг 6
5. Коммит: `git add . && git commit -m "feat(quick-add): add callbacks for chip clicks [protocol-0012/05]"`
6. Push
7. Отчёт
