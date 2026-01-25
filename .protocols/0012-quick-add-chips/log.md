# Work Log: 0012-quick-add-chips — Quick-Add Chips

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0012#ctx-N -->

Restore context: protocol-0012#ctx-1

---

## Step Log

<!--
Формат записи:
### Step XX — [название] (commit: abc1234)
- Что сделано
- Неочевидные решения и почему
- Проблемы и как решены
-->

### Step 01 — Schema и константы (commit: pending)
- Создан `app/schema/quick_add.py` с TypedDict QuickAddChipData
- Обновлен `app/schema/__init__.py` — экспорт QuickAddChipData
- Добавлена константа DEFAULT_QUICK_ADD_CHIP_NAMES (5 expense + 2 income)
- Добавлена функция `_get_quick_add_chips()` — lookup по имени с warning
- Lookup по имени защищает от ID mismatch между dev/prod окружениями
