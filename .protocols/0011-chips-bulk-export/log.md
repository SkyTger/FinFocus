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

### Step 3 — Chips Callbacks (commit: pending)
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

<!--
Формат записи:
### Step XX — [название] (commit: abc1234)
- Что сделано
- Неочевидные решения и почему
- Проблемы и как решены
-->
