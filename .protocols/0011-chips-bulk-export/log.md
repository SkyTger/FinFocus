# Work Log: 0011-chips-bulk-export — Chips + Bulk + Export UI

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

- Restore context: protocol-0011#ctx-1 (2026-01-23)

<!-- Записи вида: Restore context: protocol-0011#ctx-N -->

---

## Step Log

### Step 0 — Setup (commit: 045b8fb)
- Создан worktree и ветка 0011-chips-bulk-export
- Артефакты протокола созданы из шаблонов
- Plan включает замечания из critique-v2

### Step 1 — Layout + Helpers (commit: 1b2e3f5)
- Добавлен import dcc для Store/Download компонентов
- dcc.Store: selected-transactions, frequent-categories
- dcc.Download: export-download для CSV экспорта
- Кнопка "Экспорт CSV" в header рядом с "Добавить операцию"
- Helper _pluralize_operations() — склонение "операция/операции/операций"
- Helper _build_bulk_panel() — sticky panel с dropdown и кнопкой
- Bulk panel добавлен в layout (hidden по умолчанию)

### Step 2 — Table + Chips (commit: ef16193)
- Helper _build_chips_cell() добавлен (~70 строк):
  - Guard для TRANSFER/ADJUSTMENT — возвращает "—"
  - Chips из frequent_categories[:5] с Pattern-Matching IDs
  - Overflow dropdown для полного списка категорий
- _build_transactions_table() расширен:
  - Параметры frequent_categories, all_categories (с defaults)
  - Колонка checkbox в header (select-all-checkbox)
  - Checkbox в каждой строке {"type": "tx-checkbox", "index": tx.id}
  - colSpan обновлен 6→7 для пустой таблицы

### Step 3 — Chips Callbacks (commit: 1931a48)
- load_frequent_categories callback добавлен:
  - Кеширование при pathname=/transactions и пустом кеше
  - CategoryService.get_frequent_for_type() для expense/income
- load_transactions обновлен:
  - Добавлен Input frequent-categories.data
  - Загрузка all_categories и передача в _build_transactions_table()
- chip_assign_category callback (~55 строк):
  - 3-уровневые guard clauses по ADR-003
  - TransactionService.update_transaction()
  - Emit trigger + return updated table
- chip_dropdown_assign_category callback (~55 строк):
  - Аналогичная структура с guard clauses

### Step 4 — Bulk Callbacks (commit: b89c954)
- Добавлен import no_update, ValidationError
- update_selection_state callback:
  - Обработка Select All и individual checkboxes
  - Return list[int] в selected-transactions Store
- clear_selection_on_filter_change callback:
  - Сброс selection И select-all-checkbox при filter change
  - Критично для WYSIWYG (critique v2)
- toggle_bulk_panel callback:
  - prevent_initial_call=True (critique v2)
  - Показ/скрытие panel + counter через _pluralize_operations
- bulk_assign_category callback:
  - Валидация inputs (selection, category)
  - try/except ValidationError → error alert
  - Emit trigger, clear selection, return table

### Step 5 — Export + Tests (commit: pending)
- export_transactions callback добавлен:
  - Filename: finfocus_transactions_{YYYY-MM-DD}.csv
  - Учитывает filter-no-category
- tests/test_transactions_callbacks.py создан:
  - 13 тестов для _pluralize_operations helper
  - Все склонения проверены (1,2,5,11,21,100,101,111)
- Black + Flake8: 0 ошибок
- Pytest: 13 passed

<!--
Формат записи:
### Step XX — [название] (commit: abc1234)
- Что сделано
- Неочевидные решения и почему
- Проблемы и как решены
-->
