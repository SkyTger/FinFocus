# Шаг 4: Preselection механизм

## Briefing

- **Цель:** Добавить dcc.Store для preselection и callback установки значений в dropdown
- **Ключевые файлы:**
  - `app/components/transaction_modals.py`
- **Доп. информация:** Триггер `create-modal.is_open` гарантирует порядок (ПОСЛЕ открытия модала)

## Sub-tasks

1. Добавить в `create_transaction_modals()` два Store:
   ```python
   dcc.Store(id="preselected-category", data=None),
   dcc.Store(id="preselected-type", data=None),
   ```

2. Создать callback `set_preselection_on_modal_open()`:
   ```python
   @callback(
       [
           Output("create-category-dropdown", "value", allow_duplicate=True),
           Output("create-type-select", "value", allow_duplicate=True),
       ],
       Input("create-modal", "is_open"),
       [
           State("preselected-category", "data"),
           State("preselected-type", "data"),
       ],
       prevent_initial_call=True,
   )
   ```
   - Guard: `if not is_open: return no_update, no_update`
   - Apply preselection if available, else `no_update`

3. Модифицировать `create_transaction` callback:
   - Добавить Outputs: `preselected-category.data`, `preselected-type.data`
   - Reset to `None` после успешного создания
   - При ошибке: `no_update, no_update`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/transaction_modals.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 5, Next Action: Шаг 5
5. Коммит: `git add . && git commit -m "feat(quick-add): add preselection stores and callback [protocol-0012/04]"`
6. Push
7. Отчёт
