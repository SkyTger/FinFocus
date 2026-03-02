# modules/ui-components.md

## Суть
Dash компоненты для UI: Dashboard, Sidebar, Transactions с Bootstrap styling

## Ключевые файлы
- `app/components/dashboard.py` - главная страница с метриками и графиками
- `app/components/sidebar.py` - навигация
- `app/components/transactions.py` - управление операциями (CRUD)

## Dashboard Component

**Layout**:
- 4 metric cards (Balance, Income, Expense, Goals)
- Cashflow bar chart (Plotly)
- Expense structure donut chart (Plotly)
- AI Assistant card (placeholder)

**Callbacks**: Пока статические данные, интеграция с БД в Фазе 4

**Ключевые элементы**:
```python
dbc.Card([
    dbc.CardBody([
        html.H4("Balance", className="text-muted"),
        html.H2("₽125,000", className="text-success")
    ])
])
```

## Sidebar Component (Протокол 0023 — рефакторинг)

**Файл**: `app/components/sidebar.py` (~130 строк после протокола 0023)

**Layout**:
- dbc.Card контейнер (className="sidebar-card h-100") **(NEW)**
- Логотип + заголовок
- Навигационные ссылки (Dashboard, Calendar, Goals, Transactions)
- User info block (username, logout button)

**Styling** (sidebar.css — NEW файл):
- `.sidebar-card` — белый фон, border, padding, no shadow
- `.sidebar-nav-item-active` — border-left 4px green для активного пункта

**Callback** (NEW):
- `highlight_active_sidebar()` — динамический active highlight
  - Input: url.pathname
  - Output: sidebar-nav.children
  - Logic: перерисовывает NavLinks с active=True для текущего pathname

**Константы**:
```python
MAIN_NAV_ITEMS = [
    {"label": "Dashboard", "href": "/dashboard", "icon": "bi-house"},
    {"label": "Calendar", "href": "/calendar", "icon": "bi-calendar3"},
    {"label": "Goals", "href": "/goals", "icon": "bi-bullseye"},
    {"label": "Transactions", "href": "/transactions", "icon": "bi-list-ul"}
]

ADDITIONAL_NAV_ITEMS = [
    {"label": "Analytics", "href": "/analytics", "icon": "bi-bar-chart"}
]
```

**Helper функция**:
- `_build_nav_links(pathname)` — генерирует NavLinks с active=True для текущего pathname

**Навигация**:
```python
dbc.NavLink(
    "Dashboard",
    href="/dashboard",
    active=(pathname == "/dashboard"),  # Dynamic
    className="sidebar-nav-item-active" if pathname == "/dashboard" else ""
)
```

## Transactions Component (КРИТИЧНО, Протокол 0023 — расширен)

**Layout**:
- Header с кнопками "Добавить операцию" и "Экспорт CSV"
- Date Range Filter (dcc.DatePickerRange) — фильтр по диапазону дат
- Transactions table с:
  - Multi-select checkboxes (select-all в header)
  - Quick chips для категоризации некатегоризированных операций
  - Edit/Delete кнопки для каждой операции
- Bulk Actions Panel (sticky bottom):
  - Счетчик выбранных операций с склонением
  - Dropdown категорий для массового назначения
  - Кнопка "Применить категорию"
- Модалы:
  - Create modal с формой создания
  - Edit modal с формой редактирования
- dcc.Store:
  - selected-transactions - список ID выбранных операций
  - frequent-categories - кеш частых категорий
- dcc.Download для CSV экспорта

**Callbacks** (Pattern-Matching):
- `toggle_create_modal()` - открытие/закрытие модала создания
- `create_transaction()` - создание операции через TransactionService
- `open_edit_modal()` - открытие модала редактирования (pattern-matching)
- `update_transaction()` - обновление операции
- `delete_transaction()` - удаление операции (pattern-matching)
- `refresh_transactions_table()` - обновление таблицы после изменений

**Категоризация Callbacks** (Протокол 0011):
- `load_frequent_categories()` - кеширование частых категорий через CategoryService.get_frequent_for_type()
- `chip_assign_category()` - быстрое назначение через chip (Pattern-Matching с guard clauses)
- `chip_dropdown_assign_category()` - назначение через overflow dropdown

**Bulk Actions Callbacks** (Протокол 0011):
- `update_selection_state()` - обработка Select All и individual checkboxes
- `clear_selection_on_filter_change()` - сброс selection при смене фильтра (WYSIWYG)
- `toggle_bulk_panel()` - показ/скрытие panel с prevent_initial_call=True
- `bulk_assign_category()` - массовое назначение категории (max 100, ValidationError handling)

**Export Callback** (Протокол 0011):
- `export_transactions()` - CSV экспорт с UTF-8 BOM, учет filter-no-category

**URL Query Params Callback** (Протокол 0023 — NEW):
- `apply_url_date_filter()` - парсинг ?start=&end= query params в date filter
  - Input: url.search
  - Output: filter-date-range.dates (start, end tuple)
  - Logic: parse_qs() + date.fromisoformat() с try/except для невалидных дат
  - Применение: прямые ссылки с предзаполненным фильтром

**Pattern-Matching Callbacks** (КРИТИЧНО):
```python
# Edit buttons
Input({"type": "edit-btn", "index": ALL}, "n_clicks")

# КРИТИЧНО: проверка автовызова
if ctx.triggered[0].get('value') is None:
    raise PreventUpdate

# Используем triggered_id напрямую
transaction_id = ctx.triggered_id["index"]
```

**Quick Chips UI** (Протокол 0011):
```python
# Pattern-Matching ID для chip кнопок
{"type": "category-chip", "tx_id": transaction_id, "cat_id": category_id}

# Helper функция
def _build_chips_cell(tx, frequent_categories, all_categories):
    # Guard: TRANSFER/ADJUSTMENT → "—"
    if tx.type in [TransactionType.TRANSFER, TransactionType.ADJUSTMENT]:
        return "—"

    # Chips из frequent_categories[:5]
    chips = [dbc.Badge(cat.name, ...) for cat in frequent_categories[:5]]

    # Overflow dropdown с полным списком
    overflow = dcc.Dropdown(options=all_categories, ...)
```

**Ключевые особенности**:
- Chips показываются ТОЛЬКО для транзакций без категории
- TRANSFER и ADJUSTMENT типы не могут иметь категорию (guard clause)
- Chips загружаются из CategoryService.get_frequent_for_type() (кеш в Store)
- Max 5 chips + overflow dropdown "..." с полным списком
- 3-уровневые guard clauses в callbacks (ADR-003)

**Bulk Actions Panel** (Протокол 0011):
```python
# Helper для склонения
def _pluralize_operations(count: int) -> str:
    """Склонение слова 'операция' по падежам."""
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} операция"
    elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
        return f"{count} операции"
    else:
        return f"{count} операций"

# Bulk panel visibility
def toggle_bulk_panel(selection):
    if not selection or len(selection) == 0:
        return {"display": "none"}, ""

    counter = _pluralize_operations(len(selection))
    return {"display": "block"}, f"Выбрано {counter}"
```

**Ключевые особенности**:
- Multi-select с checkboxes в таблице (select-all в header)
- Sticky bottom panel появляется только при выборе
- Max 100 транзакций (лимит в TransactionService.bulk_update_category)
- Сброс selection при смене фильтров (WYSIWYG behavior)
- ValidationError handling с alert notification

**CSV Export** (Протокол 0011):
```python
# Filename pattern
filename = f"finfocus_transactions_{datetime.now().strftime('%Y-%m-%d')}.csv"

# UTF-8 BOM для Excel совместимости
content = TransactionService.export_to_csv(session, user_id, include_uncategorized)
```

**Ключевые особенности**:
- Учитывает filter-no-category
- UTF-8 BOM для корректного отображения кириллицы в Excel
- Timestamp в имени файла

**Form Validation**:
- amount > 0 (frontend: type="number", min=0)
- transaction_type required (frontend: dropdown)
- transaction_date required (frontend: DatePickerSingle)
- Backend validation через TransactionService

## Важное

**Dash Bootstrap Components**:
- `dbc.Modal` - модальные окна
- `dbc.Table` - таблицы с striped/hover
- `dbc.Card` - карточки для метрик
- `dbc.Button` - кнопки с цветами (primary/danger/success)

**Plotly Charts**:
```python
fig = go.Figure(data=[
    go.Bar(x=dates, y=amounts, name="Income", marker_color="green")
])
fig.update_layout(template="plotly_white", showlegend=True)
```

**Component IDs** (kebab-case):
- `transaction-table` - таблица операций
- `create-modal` - модал создания
- `edit-modal` - модал редактирования
- `export-download` - dcc.Download для CSV экспорта
- `selected-transactions` - dcc.Store для списка ID выбранных операций
- `frequent-categories` - dcc.Store для кеша частых категорий
- `select-all-checkbox` - checkbox в header таблицы
- `bulk-actions-panel` - sticky panel для bulk операций
- `bulk-category-dropdown` - dropdown категорий для bulk назначения
- `{"type": "edit-btn", "index": transaction_id}` - pattern-matching ID
- `{"type": "tx-checkbox", "index": transaction_id}` - checkbox для multi-select
- `{"type": "category-chip", "tx_id": tx_id, "cat_id": cat_id}` - chip кнопка категории
- `{"type": "chip-dropdown", "index": transaction_id}` - overflow dropdown категорий

## Transaction Modals Component (Глобальные модалы CRUD)

**Файл**: `app/components/transaction_modals.py` (~800 строк)

**Layout**:
- create-modal — форма создания транзакции с recurring секцией
- edit-modal — форма редактирования транзакции
- recurring-scope-modal — выбор scope при редактировании recurring операций

**dcc.Stores**:
- modal-source — источник открытия модала (calendar/transactions/dashboard)
- global-transaction-trigger — эмиттер обновления страниц после CRUD
- edit-transaction-id — ID редактируемой транзакции
- recurring-edit-context — контекст для recurring operations

**Submit Callbacks** (3):
1. **create_transaction** — создание новой операции
   - TransactionService.create_transaction()
   - RecurringService.create_recurring() для recurring операций
   - emit global-transaction-trigger для refresh страниц

2. **update_transaction** — обновление существующей операции
   - TransactionService.update_transaction()
   - Обработка recurring edit через RecurringService

3. **skip_recurring_instance** — пропуск экземпляра recurring операции
   - RecurringService.skip_instance()
   - emit global-transaction-trigger

**Recurring Edit Scope Callback** (КРИТИЧНО):
- **process_recurring_edit_scope()** — обработка выбора scope редактирования (2026/02/02)
  - Inputs: scope-ok-button.n_clicks, scope-radio.value, recurring-edit-context.data
  - Outputs: edit-modal, transaction fields, category dropdown
  - Logic:
    - scope="all" → редактирование шаблона (template_id)
    - scope="instance" + transaction_id → редактирование существующего exception
    - scope="instance" + VIRTUAL op (transaction_id=None) → **AUTO-CREATE EXCEPTION** (commit cae3575)
  - **Критичный bugfix (cae3575)**:
    - RecurringService.create_exception() для виртуальных операций перед редактированием
    - Предотвращает "fully NULL primary key identity" ошибку
    - Error handling с transaction_error_alert
  - **Context обновление**: updated_context для кнопки "Пропустить"

**Category Dropdown Callbacks**:
- load_create_category_options / update_edit_category_options — dynamic dropdown с ICON_TO_EMOJI
- Guard clause: allow_duplicate=True для update_edit

**Close Callbacks**:
- close_create_modal / close_edit_modal — глобальные close для Cancel buttons

**Ключевые паттерны**:
- **Refresh Trigger Pattern** — global-transaction-trigger emit/listen
- **modal-source Store** — источник открытия для Selective Refresh
- **Auto-create exception** — виртуальные recurring ops → exception перед edit (cae3575)
- **Error handling** — try/catch в callbacks с transaction-error-alert UI

**Важно**:
- Модалы глобальные — доступны с любой страницы
- RecurringService.create_exception() — idempotent (возвращает существующий exception)
- Flush/commit contract: сервис flush(), callback commit()

## Критичные проблемы и решения

**ADR-003**: Pattern-Matching Callbacks auto-trigger issue
- **Проблема**: Callbacks срабатывают автоматически при обновлении DOM
- **Решение**: Проверка `ctx.triggered[0].get('value') is None` для фильтрации автовызовов
- **Статус**: Исправлено в Батче 4 (2025-12-22)

**BUG-001**: Auto-deletion после создания операции
- **Проблема**: Delete callback срабатывал автоматически после create
- **Решение**: Проверка `ctx.triggered[0].get('value') is None`
- **Статус**: Исправлено

**BUG-002**: Edit virtual recurring operations error (2026/02/02)
- **Проблема**: Клик по виртуальной recurring операции в tooltip → выбор "только этот экземпляр" → SQLAlchemy ошибка "fully NULL primary key identity"
- **Root Cause**: callback пытался загрузить transaction_id=None для виртуальных операций
- **Решение**: process_recurring_edit_scope() создаёт exception через RecurringService.create_exception() перед редактированием
- **Статус**: Исправлено (commit cae3575)

**Упрощение логики**:
- Использование `ctx.triggered_id["index"]` напрямую вместо поиска в списках
- Удаление избыточной проверки `n_clicks is None` (не нужна с `prevent_initial_call=True`)

## Calendar Component (Фаза 3 + Протокол 0015, 0023 — ЗАВЕРШЕНА)

**Файлы**:
- `app/components/calendar.py` — UI + callbacks (~820 строк после протокола 0023)
- `app/assets/calendar.css` — стили (~390 строк после протокола 0015)

**Layout**:
- Header с навигацией (prev/today/next кнопки)
- Stats cards (Доходы/Расходы/Баланс за месяц)
- Calendar grid — сетка дней с балансами
- Hover tooltips на каждой ячейке дня (Протокол 0015)
- Интеграция с create-modal из transactions.py
- **NEW (Протокол 0023)**: Reconciliation modal перенесён в main.py (глобализация)

**Основные функции**:
- `create_calendar_layout()` — главный layout страницы
- `build_calendar_header()` — навигация по месяцам
- `build_stats_cards()` — карточки статистики (dbc.Row)
- `build_calendar_grid()` — сетка дней
- `build_day_cell()` — ячейка одного дня (sibling structure для tooltip)

**Tooltip Builder Functions** (Протокол 0015):
- `_build_day_tooltip(day_date, balance, transactions)` — полный tooltip с expand/collapse
  - Glassmorphism стиль с backdrop-filter
  - CSS checkbox hack для expand (max 5 visible, кнопка "Показать ещё")
  - Pattern-Matching IDs для клика по операциям
  - ARIA атрибуты: role="tooltip", aria-label
- `_build_tooltip_balance(balance)` — header с балансом (positive/negative классы)
- `_build_tooltip_transaction_row(tx)` — строка операции с emoji, описанием, суммой
  - category_icon из TransactionInfo → ICON_TO_EMOJI mapping
  - Strikethrough для is_skipped=True
  - Цветовая индикация: зеленый (income), красный (expense)

**Callbacks**:
- `load_and_navigate_calendar()` — загрузка данных и навигация ±12 месяцев
- `open_create_modal_from_calendar()` — открытие модала при клике на день
- `refresh_calendar_after_transaction()` — обновление после CRUD операций **(Протокол 0023: удален calendar-refresh-trigger, использует global-transaction-trigger)**
- `open_edit_from_tooltip()` — Pattern-Matching callback для клика по операции в tooltip (Протокол 0015)
  - Inputs: {"type": "tooltip-txn", "date": ALL, "id": ALL, "is_virtual": ALL, "template_id": ALL}
  - Outputs: recurring-scope-modal is_open, recurring-edit-context data, edit-modal is_open, edit-transaction-id data
  - 4 ADR-003 guard clauses: triggered_id exists, type="tooltip-txn", n_clicks not None, n_clicks > 0
  - Logic: is_virtual=True → scope modal, else → edit modal
  - Placeholder -1 для template_id вместо None (Dash PM ID limitation)
- `apply_reconciliation()` — применение сверки баланса **(Протокол 0023: Output global-transaction-trigger вместо calendar-refresh-trigger)**
  - allow_duplicate=True для множественных Outputs на trigger
  - return data: {"timestamp": ..., "source": "calendar", "action": "reconciliation"}
- `toggle_reconciliation_modal()` — открытие/закрытие модала сверки (query param ?open_recon=1)

**Утилиты**:
- `serialize_balances()` / `deserialize_balances()` — Decimal ↔ JSON для dcc.Store
- `format_balance()` — форматирование суммы с разделителями
- `format_month_header()` — локализованный заголовок (MONTH_NAMES_RU)

**Pattern-Matching IDs**:
```python
# Ячейка дня
{"type": "calendar-day", "date": "2026-01-19"}

# Tooltip операция (Протокол 0015)
{"type": "tooltip-txn", "date": "2026-01-19", "id": 123, "is_virtual": False, "template_id": -1}
# ВАЖНО: template_id=-1 placeholder вместо None (Dash limitation)

# КРИТИЧНО: проверка автовызова (ADR-003)
if ctx.triggered[0].get('value') is None:
    raise PreventUpdate
```

**Стили** (calendar.css):
- `.calendar-grid` — flexbox контейнер
- `.calendar-day` — ячейка дня
- `.calendar-day-balance.positive` — зеленый баланс
- `.calendar-day-balance.negative` — красный баланс
- `.calendar-day-balance.warning` — желтый (< 5000₽)
- `.calendar-day.today` — подсветка сегодня
- `.calendar-day.weekend` — выходные дни

**Tooltip Styles** (Протокол 0015, ~200 строк):
- `.calendar-day-content` — wrapper для tooltip sibling structure
- `.day-tooltip` — glassmorphism стиль с backdrop-filter blur
  - Transitions: opacity 0.3s, visibility с delay 0.5s
  - Edge detection: `:nth-child(6n), :nth-child(7n)` → tooltip слева
  - Mobile: `display: none` на 768px (нет hover на мобильных)
- `.tooltip-balance.positive` / `.tooltip-balance.negative` — цветовая индикация баланса
- `.tooltip-txn-row` — строка операции (hover highlight)
- `.tooltip-txn-row.skipped` — strikethrough для пропущенных
- `.tooltip-expand-checkbox` — CSS checkbox hack для expand/collapse
- `.tooltip-hidden-container` — скрытые операции (display: none до expand)

**Константы**:
- `WARNING_BALANCE_THRESHOLD = Decimal("5000")` — порог предупреждения
- `MAX_MONTHS_OFFSET = 12` — ограничение навигации
- `MAX_VISIBLE_TRANSACTIONS = 5` — лимит видимых операций в tooltip (Протокол 0015)

**Критичные детали Tooltip** (Протокол 0015):
- **CSS-only approach** — zero server calls, instant response
- **Sibling structure** — clickable_content (n_clicks) + tooltip как siblings в wrapper (CSS классы на wrapper)
- **Checkbox hack** — dcc.Checklist для expand без JavaScript callbacks
- **Edge detection** — tooltip справа для колонок 1-5, слева для колонок 6-7
- **Mobile disabled** — tooltip скрыт на < 768px (нет hover)
- **Placeholder -1** — template_id=-1 вместо None для Dash Pattern-Matching (None не поддерживается)

## Dashboard Component (Фаза 4 + Epic-05-UI Протокол 0021-0023 — ЗАВЕРШЕНА)

**Файлы**:
- `app/components/dashboard.py` — UI + callbacks (~1100 строк после протокола 0023)
- `app/assets/dashboard.css` — стили

**Layout** (обновлено в протоколе 0021-0023):
- **Row 1**: 4 KPI cards (Total Balance, Income, Expense, Goals) с новым дизайном:
  - Белый фон вместо градиентов
  - Border и border-radius
  - Типографика: .kpi-number, .kpi-title, .kpi-subtitle
  - Русские label: "Обзор", "Доходы", "Расходы", "Накопления"
  - **Кнопка "Сверка" на Total Balance** — открывает reconciliation modal (Протокол 0023)
- **Row 2 (8/4 split)** **(Протокол 0023)**:
  - **Левая колонна (8 cols)**:
    - **Daily/Yearly cashflow chart (Plotly)** — дневной график для Month mode, месячный для Year mode (Протокол 0022):
      - Grouped bars (доходы/расходы) + линия running balance
      - Diamond маркер минимального баланса
      - Today вертикальная линия (только Month mode)
      - Current month highlight rect (только Year mode)
      - Dual Y-axis (bars слева, balance справа)
      - hovermode="x unified" с customdata + format_rub()
      - Клик по bar → create-modal с preselected date (только Month mode)
    - **Split Transactions Tables (50/50)** **(Протокол 0023)**:
      - Недавние операции (до today) — последние 5, DESC sort
      - Предстоящие операции (от today) — ближайшие 5, ASC sort
      - format_date_human() для дат ("5 февраля")
      - Иконка 🔁 для recurring instances
      - Empty states с CTA кнопками "Добавить"
      - Ссылка "Все операции" → /transactions
  - **Правая колонна (4 cols)** **(Протокол 0023)**:
    - **Wishlist Widget** — 5 фокусных хотелок (переиспользован из Протокола 0020)
    - **Safety Cushion Card (readonly)** — прогресс подушки, link→/goals
- Period switcher (month/year) через RadioItems
- AI Assistant и Exchange cards — **скрыты** (TODO Epic-08)

**Callbacks** (протокол 0022-0023):
- `load_dashboard_data()` — загрузка данных из DashboardService при открытии страницы
  - **Рефакторинг (0022)**: использует _load_dashboard_components() helper
  - **Расширен (0023)**: +2 Outputs (recent table, upcoming table)
- `refresh_dashboard_after_crud()` — обновление после CRUD операций
  - **Рефакторинг (0022)**: использует _load_dashboard_components() helper (устраняет дублирование)
  - **Расширен (0023)**: +2 Outputs (recent table, upcoming table)
- `update_period_state()` — обновление dcc.Store при смене периода
  - **NEW (0022)**: Store теперь хранит {period, year, month} вместо просто period
- `open_create_from_chart()` — Pattern-Matching callback для клика по bar (Протокол 0022)
  - Inputs: {"type": "cashflow-bar", "date": ALL}.n_clicks, period-store, preselection Stores
  - Outputs: create-modal is_open, preselected-date, 4x preselection resets
  - **Только Month mode**: Year mode не поддерживает клик (guard clause)
  - ADR-003 guard clauses #1-4 (triggered_id, type, n_clicks, period)
- `open_create_from_empty()` — открытие create-modal из empty states **(Протокол 0023)**
  - Inputs: empty-recent-add-btn, empty-upcoming-add-btn
  - Output: create-modal is_open
  - ADR-003 guard clauses
- `open_recon_from_dashboard()` — открытие reconciliation modal **(Протокол 0023)**
  - Inputs: open-recon-from-dashboard-btn (KPI button), open-recon-from-dashboard-banner-btn (banner button)
  - Output: open-recon-trigger (timestamp)
  - ADR-003 guard clauses

**State Management**:
- `dcc.Store(id="dashboard-period-store")` — хранит {period, year, month}
- Preselection Stores (интеграция с transaction_modals.py):
  - preselected-date, preselected-amount, preselected-description, preselected-risk-warning

**Build Functions** (протокол 0021-0023):
- `_build_kpi_card()` — новая функция для KPI-карточек (вместо create_metric_card)
- `_build_daily_cashflow_chart()` — дневной график для Month mode (Протокол 0022)
  - Grouped bars (go.Bar) для income/expense (yaxis)
  - Balance line (go.Scatter) с yaxis2 (dual Y-axis)
  - Diamond marker для минимального баланса (go.Scatter)
  - Today вертикальная линия (go.Scatter vline)
  - Hover customdata: (date_iso, income_str, expense_str, balance_str, status)
  - Pattern-Matching IDs для bar clickable: {"type": "cashflow-bar", "date": date_iso}
- `_build_yearly_cashflow_chart()` — годовой график для Year mode (Протокол 0022)
  - Аналогичная структура, X=месяцы вместо дней
  - Current month highlight rect (go.Scatter fill)
  - Bars НЕ clickable (guard в callback)
- `_load_dashboard_components()` — helper для устранения дублирования (Протокол 0022-0023)
  - Единая точка загрузки: KPI, chart, recent/upcoming transactions
  - **Расширен (0023)**: +get_upcoming_transactions(), +cushion card, +6 outputs
  - Используется в load_dashboard_data И refresh_dashboard_after_crud
- `_build_transactions_split_table()` — таблица для Recent/Upcoming **(Протокол 0023)**
  - format_date_human() для дат ("5 февраля")
  - Иконка 🔁 для recurring instances
  - Без "Completed" бейджей (не нужны на Dashboard)
  - Ссылка "Все операции" → /transactions
- `_build_empty_state()` — пустое состояние с CTA **(Протокол 0023)**
  - icon: bi-inbox или bi-calendar-plus
  - message: текст подсказки
  - button_id: для callback open_create_from_empty
- `_build_cushion_card_readonly()` — readonly карточка подушки **(Протокол 0023)**
  - CushionService.get_settings() для данных
  - Прогресс-бар с 4 статусами (not_configured/danger/warning/info/success)
  - Link → /goals (без edit функциональности)

**Форматирование** (протокол 0021):
- 12 inline замен на format_rub():
  - KPI values (Total Balance, Income, Expense, Goals)
  - Cashflow текст под графиком
  - Transaction amounts в таблице
- Python hardcoded colors: #28a745 → #27ae60, #17a2b8 → #e74c3c
- .table-amount.positive / .negative классы для цветовой индикации

**Plotly Chart Patterns** (Протокол 0022):
```python
# STATUS_COLORS для индикации
STATUS_COLORS = {
    "ok": "#2ecc71",       # Зеленый (≥ 15000₽)
    "attention": "#f39c12", # Оранжевый (5000-15000₽)
    "risk": "#e74c3c"      # Красный (< 5000₽)
}

# Dual Y-axis
fig.update_layout(
    yaxis=dict(title="Доходы/Расходы (₽)", side="left"),
    yaxis2=dict(title="Баланс (₽)", side="right", overlaying="y")
)

# hovermode unified
fig.update_layout(hovermode="x unified")

# Hover template с customdata
hovertemplate=(
    "<b>%{customdata[0]}</b><br>"
    "Доходы: %{customdata[1]}<br>"
    "Расходы: %{customdata[2]}<br>"
    "Баланс: %{customdata[3]}<extra></extra>"
)

# Pattern-Matching ID для клика
customdata=[...], ids={"type": "cashflow-bar", "date": date.isoformat()}
```

**Интеграция**:
- DashboardService для данных (get_daily_cashflow, get_yearly_cashflow)
- CalendarService для балансов
- GoalService для savings (агрегация по всем ACTIVE целям)
- format_rub() для форматирования всех денежных сумм
- transaction_modals.py — preselection Store Pattern

**Критичные изменения** (протокол 0021-0023):
- Новый формат денег: $X,XXX.XX → X XXX ₽ (глобально)
- CSS-переменные: --color-primary (#2ecc71), --color-secondary (#e74c3c)
- AI Assistant/Exchange скрыты, НЕ удалены (будущий Epic-08)
- **_load_dashboard_components() helper** — устраняет дублирование между load и refresh callbacks
- **Единый Graph ID "daily-cashflow-chart"** — переиспользуется для Month и Year режимов
- **Preselection Store Pattern** — для передачи даты в create-modal из chart click
- **Reconciliation globalization (0023)** — modal доступен с Dashboard (не только Calendar)
- **Split tables 50/50 (0023)** — recent (до today) + upcoming (от today)
- **Empty states (0023)** — CTA кнопки для создания операций
- **Layout 8/4 (0023)** — левая колонна (chart + tables), правая колонна (wishlist + cushion)

## Onboarding Wizard Component (Протокол 0014 — ЗАВЕРШЕН)

**Файлы**:
- `app/components/onboarding_wizard.py` — Wizard UI + callbacks (~200 строк)
- `app/assets/onboarding.css` — стили (~80 строк)

**Layout**:
- Blocking modal (dbc.Modal):
  - backdrop="static" — нельзя закрыть кликом вне модала
  - keyboard=False — нельзя закрыть ESC
  - is_open управляется из check_onboarding_and_validate callback
- Header с зеленым градиентом
- Body:
  - Welcome text с объяснением важности starting_balance
  - InputGroup с полем ввода + ruble sign (₽)
  - Warning div для negative balance (display: none по умолчанию)
- Footer:
  - "Пропустить" button (secondary) — для опытных пользователей
  - "Продолжить" button (success, disabled по умолчанию) — активируется при valid input

**Callbacks** (2):
1. **check_onboarding_and_validate** (triggered on URL change + input change)
   - Inputs: url.pathname, starting-balance-input.value
   - Outputs: modal is_open, continue-button disabled, continue-button n_clicks, warning visibility
   - Logic:
     - Check first_launch через OnboardingService.get_status()
     - Show modal если first_launch=True
     - Validate input: empty → disabled, negative → warning + disabled, positive → enabled
     - DB failure strategy: fail-closed (hide wizard on error)

2. **handle_onboarding_action** (triggered on button clicks)
   - Inputs: continue-btn.n_clicks, skip-btn.n_clicks, starting-balance-input.value
   - Outputs: modal is_open, dashboard-refresh-trigger
   - Logic:
     - ADR-003 guard clauses для n_clicks (prevent auto-triggers)
     - Continue → OnboardingService.complete_with_balance()
     - Skip → OnboardingService.skip()
     - Emit dashboard-refresh-trigger для обновления UI
     - Close modal

**Dashboard Toast Integration** (Протокол 0014):
- Toast UI в dashboard.py:
  - _build_balance_toast() — warning toast с CTA кнопкой
  - Показывается если starting_balance=0 AND first_launch=False (пользователь пропустил)
  - Dismissable через close button (состояние в session Store)
  - CTA кнопка "Настроить" → redirect на /calendar?open_recon=1
- 2 callbacks:
  - toggle_balance_toast — показ/скрытие на основе OnboardingStatus
  - persist_toast_dismissal — сохранение dismissal state в Store

**Calendar Query Param Handler** (Протокол 0014):
- Extended toggle_reconciliation_modal в calendar.py:
  - Added Input("url", "search") и State("url", "pathname")
  - Logic: если ?open_recon=1 → auto-open reconciliation modal
  - Query cleanup strategy: full (return "" для url.search Output)
  - All return statements updated с 6th element для url.search Output

**State Management**:
- `dcc.Store(id="balance-toast-dismissed")` — session state для toast dismissal (в main.py)

**Ключевые паттерны**:
- **Fail-closed DB strategy**: wizard скрывается при ошибке БД, не блокирует приложение (critical для UX)
- **Query param full cleanup**: url.search = "" после обработки (не оставляем артефактов в URL)
- **Flush/commit contract**: OnboardingService.flush(), callback context manager commit()
- **ADR-003 guard clauses**: n_clicks проверки в handle_onboarding_action

**Стили** (onboarding.css):
- `.onboarding-modal .modal-header` — green gradient (linear-gradient #1a7431 → #228b3b)
- `.onboarding-modal .modal-body` — padding, line-height
- `.balance-toast` — warning colors (#856404 bg, #fff3cd text)
- Responsive: max-width 90% на mobile

**Критичные детали**:
- Modal НЕЛЬЗЯ закрыть без действия (backdrop=static, keyboard=False, no X button)
- Negative balance → warning div показывается, button disabled
- Toast dismissal в session Store (не в БД) — reset при новой сессии
- Query param ?open_recon=1 обрабатывается ОДИН РАЗ (full cleanup после)

**Unit тесты**: 8 тестов OnboardingService покрывают бизнес-логику

---

## Goals Component (Фаза 5 — ЗАВЕРШЕНА, Протокол 0006 — РЕФАКТОРИНГ)

**Файлы**:
- `app/components/goals.py` — UI + callbacks (~1500 строк после протокола 0006)
- `app/assets/goals.css` — стили (~270 строк после протокола 0006)

**Layout** (после протокола 0006):
- Empty state для новых пользователей
- Summary section:
  - Общий прогресс по всем целям
  - Статус распределения бюджета (Budget Alert если не настроен)
  - Кнопка "Настроить бюджет"
- Список карточек целей (вместо одной карточки):
  - Priority badge (#1, #2, #3...)
  - Кнопки ↑↓ для изменения приоритета
  - Прогресс-бар
  - Allocation badge (Полностью/Частично/Не профинансирована/Пропущена)
- Модалы:
  - Создание цели
  - Редактирование цели
  - Добавление взноса
  - Настройка бюджета накоплений
  - Выбор режима накоплений (free/medium/strict) — Протокол 0007
- dcc.ConfirmDialog для удаления

**Callbacks** (10+ callbacks):
- CRUD операции (create, edit, delete, add_contribution)
- Смена статуса (pause, resume)
- Управление приоритетами (move_up, move_down) — Pattern-Matching
- Настройка бюджета (update_budget)
- Смена режима накоплений (update_savings_mode) — Протокол 0007
- `_recalculate_and_render()` — helper для пересчета allocation и рендера

**State Management**:
- `dcc.Store(id="goals-store")` — ID активной цели (для модалов)
- `dcc.Store(id="goals-budget-store")` — текущий бюджет
- `dcc.Store(id="goals-allocation-store")` — результаты AllocationService
- `dcc.Store(id="goals-savings-mode-store")` — режим накоплений (free/medium/strict)

**Интеграция**:
- GoalService для CRUD
- AllocationService для распределения бюджета
- Утилиты форматирования (app/utils/formatters.py)

**Ключевые уроки**:
- Simple IDs > Pattern-Matching для Goals UI (простота callbacks)
- dcc.Store для синхронизации состояния между callbacks
- allow_duplicate=True для множественных Outputs на один компонент
- Helper функции (_recalculate_and_render) для DRY

---

Детали: `architecture.md` (Presentation Layer), `code-style.md` (Dash Callbacks Pattern), `schema.md` (TypedDicts)
