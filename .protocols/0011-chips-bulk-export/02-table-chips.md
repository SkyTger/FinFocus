# Шаг 2: Table + Chips

## Briefing

- **Цель:** Добавить checkboxes в таблицу и chips cell для некатегоризированных транзакций
- **Ключевые файлы:**
  - `app/components/transactions.py` — расширение _build_transactions_table
- **Доп. информация:**
  - Critique v2: Guard для TRANSFER/ADJUSTMENT — chips не показывать!
  - Pattern-Matching IDs: `{"type": "tx-checkbox", "index": tx_id}`, `{"type": "chip-btn", ...}`, `{"type": "chip-dropdown", ...}`

## Sub-tasks

- [ ] 2.1. Добавить helper `_build_chips_cell(tx, frequent_categories, all_categories) -> html.Div`
  - **ВАЖНО**: Guard для TRANSFER/ADJUSTMENT — return html.Span("-")
  - Определить category_type из tx.transaction_type.name.lower()
  - Chips из frequent_categories[category_type][:5]
  - dbc.Button для каждого chip с ID `{"type": "chip-btn", "tx_id": ..., "cat_id": ...}`
  - Inline dcc.Dropdown для overflow с ID `{"type": "chip-dropdown", "tx_id": ...}`
- [ ] 2.2. Расширить `_build_transactions_table(transactions, frequent_categories, all_categories)`
  - Добавить параметры frequent_categories, all_categories
  - Добавить колонку checkbox в header: "Select All" checkbox (id="select-all-checkbox")
  - Добавить checkbox в каждую строку: ID `{"type": "tx-checkbox", "index": tx.id}`
  - Для транзакций без category_id: вызвать `_build_chips_cell()`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/transactions.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step = 3
5. Коммит: `git add . && git commit -m "feat(transactions): add checkboxes and chips cell [protocol-0011/02]"`
6. Push
7. Отчёт
