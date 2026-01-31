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

## Sidebar Component

**Layout**:
- Логотип + заголовок
- Навигационные ссылки (Dashboard, Calendar, Goals, Transactions)
- User info block (username, logout button)

**Styling**:
- `bg-light` для фона
- Bootstrap icons для пунктов меню
- `fixed` позиционирование

**Навигация**:
```python
dbc.NavLink("Dashboard", href="/dashboard", active="exact")
dbc.NavLink("Calendar", href="/calendar", active="exact")
dbc.NavLink("Goals", href="/goals", active="exact")
dbc.NavLink("Transactions", href="/transactions", active="exact")
```

## Transactions Component (КРИТИЧНО)

**Layout**:
- Header с кнопками "Добавить операцию" и "Экспорт CSV"
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

## Критичные проблемы и решения

**ADR-003**: Pattern-Matching Callbacks auto-trigger issue
- **Проблема**: Callbacks срабатывают автоматически при обновлении DOM
- **Решение**: Проверка `ctx.triggered[0].get('value') is None` для фильтрации автовызовов
- **Статус**: Исправлено в Батче 4 (2025-12-22)

**BUG-001**: Auto-deletion после создания операции
- **Проблема**: Delete callback срабатывал автоматически после create
- **Решение**: Проверка `ctx.triggered[0].get('value') is None`
- **Статус**: Исправлено

**Упрощение логики**:
- Использование `ctx.triggered_id["index"]` напрямую вместо поиска в списках
- Удаление избыточной проверки `n_clicks is None` (не нужна с `prevent_initial_call=True`)

## Calendar Component (Фаза 3 — ЗАВЕРШЕНА)

**Файлы**:
- `app/components/calendar.py` — UI + callbacks (~700 строк)
- `app/assets/calendar.css` — стили (~190 строк)

**Layout**:
- Header с навигацией (prev/today/next кнопки)
- Stats cards (Доходы/Расходы/Баланс за месяц)
- Calendar grid — сетка дней с балансами
- Интеграция с create-modal из transactions.py

**Основные функции**:
- `create_calendar_layout()` — главный layout страницы
- `build_calendar_header()` — навигация по месяцам
- `build_stats_cards()` — карточки статистики (dbc.Row)
- `build_calendar_grid()` — сетка дней
- `build_day_cell()` — ячейка одного дня (Pattern-Matching ID)

**Callbacks**:
- `load_and_navigate_calendar()` — загрузка данных и навигация ±12 месяцев
- `open_create_modal_from_calendar()` — открытие модала при клике на день
- `refresh_calendar_after_transaction()` — обновление после CRUD операций

**Утилиты**:
- `serialize_balances()` / `deserialize_balances()` — Decimal ↔ JSON для dcc.Store
- `format_balance()` — форматирование суммы с разделителями
- `format_month_header()` — локализованный заголовок (MONTH_NAMES_RU)

**Pattern-Matching IDs**:
```python
# Ячейка дня
{"type": "calendar-day", "date": "2026-01-19"}

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

**Константы**:
- `WARNING_BALANCE_THRESHOLD = Decimal("5000")` — порог предупреждения
- `MAX_MONTHS_OFFSET = 12` — ограничение навигации

## Dashboard Component (Фаза 4 — ЗАВЕРШЕНА)

**Файлы**:
- `app/components/dashboard.py` — UI + callbacks (~685 строк)
- `app/assets/dashboard.css` — стили

**Layout**:
- 4 metric cards (Balance, Income, Expense, Goals) с реальными данными
- Cashflow bar chart (Plotly) — последние 12 месяцев или 5 лет
- Recent transactions table — последние 5 транзакций
- Period switcher (month/year) через RadioItems

**Callbacks**:
- `load_dashboard_data()` — загрузка данных из DashboardService при открытии страницы
- `update_period_state()` — обновление dcc.Store при смене периода
- Использует guard clauses (ADR-003) для безопасности

**State Management**:
- `dcc.Store(id="dashboard-period-store")` — хранит текущий период (month/year)

**Build Functions**:
- `build_metric_cards()` — динамическая генерация карточек из OverviewMetrics
- `build_cashflow_chart()` — Plotly график из CashflowDataPoint[]
- `build_recent_transactions()` — таблица из RecentTransaction[]

**Интеграция**:
- DashboardService для данных
- CalendarService для балансов
- GoalService для savings (агрегация по всем ACTIVE целям)

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
