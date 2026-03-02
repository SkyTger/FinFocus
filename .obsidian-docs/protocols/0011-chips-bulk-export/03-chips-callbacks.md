# Шаг 3: Chips Callbacks

## Briefing

- **Цель:** Реализовать callbacks для chips и загрузки категорий
- **Ключевые файлы:**
  - `app/components/transactions.py` — callbacks
- **Доп. информация:**
  - **КРИТИЧНО**: 3-уровневые guard clauses по ADR-003!
  - Guard #1: `if not triggered_id or not isinstance(triggered_id, dict)`
  - Guard #2: `if triggered_id.get("type") != "chip-btn"`
  - Guard #3: `if not ctx.triggered or ctx.triggered[0].get("value") is None`

## Sub-tasks

- [ ] 3.1. Добавить callback `load_frequent_categories`
  - Input: `url.pathname`
  - State: `frequent-categories.data`
  - Загружать только при pathname="/transactions" и пустом кеше
  - CategoryService.get_frequent_for_type() для expense и income
- [ ] 3.2. Обновить callback `load_transactions`
  - Добавить Input для `frequent-categories.data`
  - Загрузить all_categories из CategoryService.get_for_dropdown()
  - Передать в `_build_transactions_table()`
- [ ] 3.3. Добавить callback `chip_assign_category`
  - **3-уровневые guard clauses!**
  - Input: `{"type": "chip-btn", "tx_id": ALL, "cat_id": ALL}.n_clicks`
  - TransactionService.update_transaction(category_id=...)
  - Emit global-transaction-trigger + return updated table
- [ ] 3.4. Добавить callback `chip_dropdown_assign_category`
  - **3-уровневые guard clauses!**
  - Input: `{"type": "chip-dropdown", "tx_id": ALL}.value`
  - Аналогичная логика

## Workflow

1. Выполни Sub-tasks последовательно
2. Проверка: `python -m py_compile app/components/transactions.py`
3. Обнови log.md, context.md
4. Коммит: `git add . && git commit -m "feat(transactions): add chips callbacks with guard clauses [protocol-0011/03]"`
5. Push, отчёт
