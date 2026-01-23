# Шаг 4: Bulk Callbacks

## Briefing

- **Цель:** Реализовать callbacks для bulk selection и bulk assign
- **Ключевые файлы:**
  - `app/components/transactions.py` — callbacks
- **Доп. информация:**
  - Critique v2: `prevent_initial_call=True` в toggle_bulk_panel!
  - Critique v2: Рассмотреть сброс "Select All" checkbox при filter change
  - `clear_selection_on_filter_change` критичен для WYSIWYG

## Sub-tasks

- [ ] 4.1. Добавить callback `update_selection_state`
  - Input: `{"type": "tx-checkbox", "index": ALL}.value`, `select-all-checkbox.value`
  - State: `{"type": "tx-checkbox", "index": ALL}.id`
  - Обработка Select All и individual checkboxes
  - Return list[int] в selected-transactions Store
- [ ] 4.2. Добавить callback `clear_selection_on_filter_change`
  - Input: `filter-no-category.value`
  - **КРИТИЧНО для WYSIWYG**: Return [] при любом изменении
  - **Critique v2**: Добавить Output для сброса select-all-checkbox.value
- [ ] 4.3. Добавить callback `toggle_bulk_panel`
  - Input: `selected-transactions.data`
  - **Critique v2**: `prevent_initial_call=True`!
  - Показывать/скрывать panel по len(selected)
  - Форматировать counter через _pluralize_operations
- [ ] 4.4. Добавить callback `bulk_assign_category`
  - Input: `bulk-apply-btn.n_clicks`
  - State: `bulk-category-dropdown.value`, `selected-transactions.data`, `filter-no-category.value`
  - try/except ValidationError → transaction-error-alert
  - Emit trigger, clear selection, return table

## Workflow

1. Выполни Sub-tasks
2. Проверка: `python -m py_compile app/components/transactions.py`
3. Обнови log.md, context.md
4. Коммит: `git add . && git commit -m "feat(transactions): add bulk selection callbacks [protocol-0011/04]"`
5. Push, отчёт
