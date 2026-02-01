# Work Log: 0015-calendar-tooltip — Tooltip для дней календаря

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0015#ctx-N -->

- Restore context: protocol-0015#ctx-1 (2026/02/01)

---

## Step Log

### Step 00 — Setup (commit: b3b209a)
- Создана ветка 0015-calendar-tooltip
- Создан worktree в ../worktrees/0015-calendar-tooltip
- Созданы артефакты протокола (plan.md, context.md, log.md, step files)
- Источник: solution-v3.md из .design/

### Step 01 — Extend TransactionInfo (commit: 77db700)
- Добавлены поля `is_skipped: bool` и `category_icon: str | None` в TransactionInfo
- Добавлены поля `is_skipped: bool` и `category_icon: str | None` в VirtualTransaction
- Обновлено заполнение TransactionInfo в get_all_transactions_for_period():
  - regular transactions: is_skipped=False, category_icon из category_rel
  - VirtualTransaction: is_skipped из instance, category_icon из instance
  - exceptions: is_skipped из instance.is_skipped, category_icon из category_rel
- Обновлено создание VirtualTransaction в generate_instances(): is_skipped=False, category_icon из template
- 80 тестов calendar/recurring проходят

### Step 02 — CSS Styles (commit: a50a7f3)
- Добавлены CSS переменные: --tooltip-hide-delay
- Добавлены стили .calendar-day-content (wrapper для tooltip)
- Glassmorphism tooltip: backdrop-filter, rgba background, transitions
- Hover trigger с delay для visibility
- Edge detection для правых 2 колонок (nth-child)
- Fallback для браузеров без backdrop-filter
- Стили контента: .tooltip-balance, .tooltip-txn-row, .tooltip-txn-row.skipped
- CSS checkbox hack для expand/collapse (.tooltip-expand-checkbox)
- Mobile media query (display: none на 768px)

### Step 03 — DOM Restructure (commit: c28f455)
- Добавлена константа MAX_VISIBLE_TRANSACTIONS = 5
- Реструктурирован build_day_cell():
  - clickable_content (id, n_clicks, className=calendar-day-content)
  - wrapper без n_clicks (className=css_classes)
  - tooltip = None placeholder для шага 4
- CSS классы остаются на wrapper (calendar-day, today, etc.)
- 38 тестов calendar проходят

### Step 04 — Tooltip Builders (commit: 68998f6)
- Добавлен импорт ICON_TO_EMOJI из formatters
- Реализованы функции:
  - _build_tooltip_balance() — header с балансом, positive/negative классы
  - _build_tooltip_transaction_row() — строка транзакции с emoji, описанием, суммой
  - _build_day_tooltip() — полный tooltip с expand/collapse через CSS checkbox
- Pattern-Matching ID для tooltip-txn (для будущего edit callback)
- dcc.Checklist для expand checkbox (CSS hack)
- ARIA атрибуты: role="tooltip", aria-label
- Интеграция в build_day_cell() — вызов _build_day_tooltip()
- 38 тестов calendar проходят

### Step 05 — Edit Callback (commit: 2318c57)
- Реализован callback open_edit_from_tooltip()
- Pattern-Matching Input для tooltip-txn (date, id, is_virtual, template_id)
- 4 ADR-003 guard clauses:
  - Guard #1: triggered_id exists
  - Guard #2: correct type (dict with type="tooltip-txn")
  - Guard #3: real click (value is not None)
  - Guard #4: n_clicks > 0
- Логика:
  - is_virtual=True → открыть scope modal с recurring_context
  - Иначе → открыть edit modal с transaction id
- logger.debug для отладки
- 38 тестов calendar проходят

### Step 06 — Unit Tests (commit: 90e595c)
- Создан tests/test_calendar_tooltip.py (20 тестов)
- Тесты TransactionInfo: category_icon, is_skipped
- Тесты _build_tooltip_balance: positive/negative/zero
- Тесты _build_tooltip_transaction_row: income/expense/skipped/recurring/category
- Тесты _build_day_tooltip: empty/few/many/aria/balance_header/hidden_container
- Fix: Dash Pattern-Matching ID не поддерживает None — заменен на -1 placeholder
- Обновлен callback open_edit_from_tooltip() для проверки -1
- 343 теста проходят (было 300)
