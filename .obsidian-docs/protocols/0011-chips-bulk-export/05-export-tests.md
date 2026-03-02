# Шаг 5: Export + Tests

## Briefing

- **Цель:** Добавить export callback и unit тесты
- **Ключевые файлы:**
  - `app/components/transactions.py` — export callback
  - `tests/test_transactions_callbacks.py` — новые тесты
- **Доп. информация:**
  - Filename format: `finfocus_transactions_{YYYY-MM-DD}.csv`
  - UTF-8 BOM для Excel (уже в TransactionService.export_to_csv)

## Sub-tasks

- [ ] 5.1. Добавить callback `export_transactions`
  - Input: `export-btn.n_clicks`
  - State: `filter-no-category.value`
  - TransactionService.export_to_csv(uncategorized_only=filter_value)
  - Return dcc.send_bytes(csv_bytes, filename)
- [ ] 5.2. Создать `tests/test_transactions_callbacks.py`
  - Тесты для guard clauses в chip callbacks
  - Тесты для bulk selection logic
  - Тесты для _pluralize_operations helper
- [ ] 5.3. Запустить black + flake8
- [ ] 5.4. Запустить pytest

## Workflow

1. Выполни Sub-tasks
2. Проверка качества: `black . && flake8 . && pytest`
3. Обнови log.md, context.md
4. Коммит: `git add . && git commit -m "feat(transactions): add export callback and tests [protocol-0011/05]"`
5. Push, отчёт
