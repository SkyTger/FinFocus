# Шаг 3: Модал "Ещё..."

## Briefing

- **Цель:** Создать единый модал со всеми категориями и динамической загрузкой
- **Ключевые файлы:**
  - `app/components/transactions.py`
- **Доп. информация:** Динамическая загрузка при открытии (future-proof для Protocol B)

## Sub-tasks

1. Создать `_build_category_more_modal() -> dbc.Modal`:
   - ID: `quick-add-more-modal`
   - dbc.Tabs с двумя вкладками: "Расход" (tab_id="expense"), "Доход" (tab_id="income")
   - Пустые контейнеры: `quick-add-more-expense-grid`, `quick-add-more-income-grid`
   - `backdrop=True` — автоматическое закрытие при клике вне модала
   - `centered=True`, `size="lg"`

2. Создать callback `load_more_modal_categories()`:
   ```python
   @callback(
       [
           Output("quick-add-more-expense-grid", "children"),
           Output("quick-add-more-income-grid", "children"),
       ],
       Input("quick-add-more-modal", "is_open"),
       prevent_initial_call=True,
   )
   ```
   - Guard: `if not is_open: raise PreventUpdate`
   - Загрузка категорий из CategoryService
   - Рендер кнопок с Pattern-Matching ID: `{"type": "qa-more-category", "category_id": N, "tx_type": str}`
   - Fallback "Нет категорий" для пустых списков

3. Добавить модал в layout (в конец `create_transactions_layout()`)

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/transactions.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 4, Next Action: Шаг 4
5. Коммит: `git add . && git commit -m "feat(quick-add): add category more modal with dynamic loading [protocol-0012/03]"`
6. Push
7. Отчёт
