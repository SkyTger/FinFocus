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
- Create button → Modal с формой создания
- Transactions table с Edit/Delete кнопками
- Edit modal с формой редактирования

**Callbacks** (Pattern-Matching):
- `toggle_create_modal()` - открытие/закрытие модала создания
- `create_transaction()` - создание операции через TransactionService
- `open_edit_modal()` - открытие модала редактирования (pattern-matching)
- `update_transaction()` - обновление операции
- `delete_transaction()` - удаление операции (pattern-matching)
- `refresh_transactions_table()` - обновление таблицы после изменений

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
- `{"type": "edit-btn", "index": transaction_id}` - pattern-matching ID

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

## Следующие шаги

**Фаза 3** (Кассовый календарь):
- Новый компонент `/app/components/calendar.py`
- Таблица с датами и остатками
- Интеграция с Transaction для расчета

**Фаза 4** (Dashboard integration):
- Callbacks для загрузки реальных данных из БД
- Динамические графики с фильтрами (месяц/год)

---

Детали: `architecture.md` (Presentation Layer), `code-style.md` (Dash Callbacks Pattern)
