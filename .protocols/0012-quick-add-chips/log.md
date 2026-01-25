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

### Step 01 — Schema и константы (commit: ffb88d3)
- Создан `app/schema/quick_add.py` с TypedDict QuickAddChipData
- Обновлен `app/schema/__init__.py` — экспорт QuickAddChipData
- Добавлена константа DEFAULT_QUICK_ADD_CHIP_NAMES (5 expense + 2 income)
- Добавлена функция `_get_quick_add_chips()` — lookup по имени с warning
- Lookup по имени защищает от ID mismatch между dev/prod окружениями

### Step 02 — UI секция Quick-add (commit: 76be290)
- Создана `_build_quick_add_chip()` — Pattern-Matching ID, вертикальный layout
- Создана `_build_quick_add_section()` — группировка expense/income + кнопки "Ещё"
- Интегрировано в `create_transactions_layout()` между header и фильтрами
- Pattern-Matching IDs: `{"type": "qa-chip", ...}`, `{"type": "qa-more-btn", ...}`

### Step 03 — Модал "Ещё..." (commit: 2fdcaec)
- Создана `_build_category_more_modal()` — dbc.Modal с Tabs (expense/income)
- Создан callback `load_more_modal_categories()` — динамическая загрузка при открытии
- Pattern-Matching ID для кнопок: `{"type": "qa-more-category", ...}`
- Модал добавлен в layout после bulk panel

### Step 04 — Preselection механизм (commit: b500451)
- Добавлены Store: `preselected-category`, `preselected-type`
- Создан callback `set_preselection_on_modal_open()` — применяет preselection при открытии
- Модифицирован `create_transaction` — reset preselection после создания
- 2 новых Output в create_transaction callback

### Step 05 — Callbacks Quick-add (commit: 69f7837)
- `open_create_from_quick_add()` — клик на chip → открытие модала с preselection
- `open_more_modal()` — клик на "Ещё..." → открытие модала с активной вкладкой
- `select_from_more_modal()` — выбор из модала → закрытие + открытие create
- ADR-003 guard clauses во всех 3 callbacks

### Step 06 — CSS стили (commit: pending)
- Добавлены стили `.qa-*` в transactions.css (~100 строк)
- Chips: vertical layout, hover transform, ellipsis для длинных названий
- Responsive: horizontal scroll на 768px, уменьшенные размеры на 576px
