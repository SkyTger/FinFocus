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
