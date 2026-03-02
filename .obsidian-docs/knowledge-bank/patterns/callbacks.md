# patterns/callbacks.md

## Суть
Паттерны организации Dash callbacks для устранения дублирования и безопасности

## Ключевые паттерны

### Helper Function for Component Loading (Протокол 0022)

Устранение дублирования между load и refresh callbacks через helper функцию.

**Проблема**: load_dashboard_data и refresh_dashboard_after_crud содержали ~80% идентичного кода — риск десинхронизации при изменениях.

**Решение**: Централизованная функция _load_dashboard_components()

```python
def _load_dashboard_components(user_id: int, period: str, year: int, month: int) -> tuple:
    """
    Загружает все компоненты dashboard.

    ВАЖНО: Единая точка загрузки для устранения дублирования.
    Используется в:
    - load_dashboard_data (initial load)
    - refresh_dashboard_after_crud (refresh после CRUD)

    Returns:
        tuple: (kpi_cards, chart_figure, transactions_table)
    """
    with get_db_session() as session:
        service = DashboardService(session)

        # KPI metrics
        metrics = service.get_overview_metrics(user_id, period, reference_date)
        kpi_cards = _build_kpi_cards(metrics)

        # Chart
        if period == "month":
            data = service.get_daily_cashflow(user_id, year, month)
            chart = _build_daily_cashflow_chart(data)
        else:
            data = service.get_yearly_cashflow(user_id, year)
            chart = _build_yearly_cashflow_chart(data)

        # Recent transactions
        transactions = service.get_recent_transactions(user_id, limit=5)
        table = build_recent_transactions(transactions)

    return kpi_cards, chart, table


@app.callback(
    Output("dashboard-content", "children"),
    Input("url", "pathname"),
    State("dashboard-period-store", "data")
)
def load_dashboard_data(pathname, period_store):
    if pathname != "/dashboard":
        raise PreventUpdate

    user_id = 1
    period = period_store.get("period", "month")
    year = period_store.get("year", date.today().year)
    month = period_store.get("month", date.today().month)

    kpi, chart, table = _load_dashboard_components(user_id, period, year, month)
    return [kpi, chart, table]


@app.callback(
    Output("dashboard-content", "children"),
    Input("global-transaction-trigger", "data"),
    State("dashboard-period-store", "data"),
    prevent_initial_call=True
)
def refresh_dashboard_after_crud(trigger, period_store):
    # ADR-003 Guard Clause
    if trigger is None:
        raise PreventUpdate

    user_id = 1
    period = period_store.get("period", "month")
    year = period_store.get("year", date.today().year)
    month = period_store.get("month", date.today().month)

    kpi, chart, table = _load_dashboard_components(user_id, period, year, month)
    return [kpi, chart, table]
```

**Преимущества**:
- Single Source of Truth для логики загрузки
- Изменения в одном месте → применяются ко всем callbacks
- Проще тестировать (один метод вместо двух callbacks)
- Меньше риск copy-paste ошибок

**Критичные детали**:
- Helper функция module-level (не в классе) — доступна всем callbacks
- Возвращает tuple компонентов (не Dash layout) — flexibility
- Обработка БД в helper, не в callback — separation of concerns
- Docstring ВАЖНО — какие callbacks используют этот helper

---

### ADR-003 Guard Clauses Pattern

4-уровневая система защиты от автовызовов Pattern-Matching callbacks.

**Проблема**: Dash Pattern-Matching callbacks срабатывают автоматически при обновлении DOM (n_clicks=0 при mount).

**Решение**: Цепочка guard clauses для фильтрации

```python
@app.callback(
    Output("create-modal", "is_open"),
    Output("preselected-date", "data"),
    Input({"type": "cashflow-bar", "date": ALL}, "n_clicks"),
    State("dashboard-period-store", "data"),
    prevent_initial_call=True
)
def open_create_from_chart(n_clicks_list, period_store):
    # GUARD CLAUSE #1: triggered_id exists
    if not ctx.triggered_id:
        raise PreventUpdate

    # GUARD CLAUSE #2: correct type
    if ctx.triggered_id.get("type") != "cashflow-bar":
        raise PreventUpdate

    # GUARD CLAUSE #3: n_clicks not None
    triggered = ctx.triggered[0]
    if triggered.get("value") is None:
        raise PreventUpdate

    # GUARD CLAUSE #4: n_clicks > 0 (user click, not mount)
    if triggered.get("value", 0) <= 0:
        raise PreventUpdate

    # GUARD CLAUSE #5 (опционально): business logic guard
    period = period_store.get("period", "month")
    if period != "month":  # Только Month mode поддерживает клик
        raise PreventUpdate

    # Основная логика
    date_str = ctx.triggered_id["date"]
    return True, date_str
```

**Уровни защиты**:
1. **triggered_id exists** — callback был вызван через конкретный Input
2. **correct type** — тип соответствует ожидаемому (для множественных Pattern-Matching)
3. **n_clicks not None** — есть данные (защита от corrupted state)
4. **n_clicks > 0** — реальный клик пользователя, не mount
5. **business logic guard** (опционально) — дополнительная валидация контекста

**Применение**:
- Обязательно для Pattern-Matching callbacks с Input ALL
- Обязательно для callbacks с n_clicks Input
- Опционально для State-only callbacks (но рекомендуется Guard #1)

**Критичные детали**:
- `ctx.triggered_id` — dict для Pattern-Matching, None для обычных callbacks
- `ctx.triggered[0].get("value")` — значение Input, None при mount
- `raise PreventUpdate` — прерывает callback, не обновляет Outputs
- Порядок важен: дешевые проверки (exists/type) перед дорогими (DB queries)

---

### Period Store Pattern (Протокол 0022)

State management через dcc.Store для сохранения контекста (period, year, month).

**Проблема**: Переключение month/year сбрасывало текущий месяц — пользователь терял контекст.

**Решение**: Store с расширенной структурой данных

```python
# В layout
dcc.Store(id="dashboard-period-store", data={
    "period": "month",
    "year": date.today().year,
    "month": date.today().month
})

@app.callback(
    Output("dashboard-period-store", "data"),
    Input("period-switcher", "value"),
    State("dashboard-period-store", "data")
)
def update_period_state(new_period, current_store):
    # ADR-003 Guard Clause
    if new_period is None:
        raise PreventUpdate

    # Сохраняем year/month из текущего Store
    return {
        "period": new_period,
        "year": current_store.get("year", date.today().year),
        "month": current_store.get("month", date.today().month)
    }

@app.callback(
    Output("dashboard-content", "children"),
    Input("dashboard-period-store", "data")
)
def load_dashboard_data(period_store):
    user_id = 1
    period = period_store.get("period", "month")
    year = period_store.get("year", date.today().year)
    month = period_store.get("month", date.today().month)

    kpi, chart, table = _load_dashboard_components(user_id, period, year, month)
    return [kpi, chart, table]
```

**Преимущества**:
- Контекст сохраняется между переключениями period
- Централизованный state для множества callbacks
- Легко расширить (добавить новые поля в dict)
- Сохраняется в сессии браузера (не теряется при refresh страницы)

**Критичные детали**:
- Store data всегда dict (не scalar) — flexibility для расширения
- `.get("key", default)` — защита от missing keys
- State в update callback — merge old и new данных
- Store Output только в одном callback — avoid conflicts

---

### Preselection Store Pattern (Протокол 0020-0022)

Передача данных из источника в create-modal через dcc.Store.

**Проблема**: Клик по bar/wishlist → create-modal должен получить дату/сумму/описание — как передать?

**Решение**: 4 специализированных Stores для preselection

```python
# В transaction_modals.py layout
dcc.Store(id="preselected-date", data=None),
dcc.Store(id="preselected-amount", data=None),
dcc.Store(id="preselected-description", data=None),
dcc.Store(id="preselected-risk-warning", data=None)

# В calendar_wishlist.py (источник)
@app.callback(
    Output("create-modal", "is_open"),
    Output("preselected-date", "data"),
    Output("preselected-amount", "data"),
    Output("preselected-description", "data"),
    Output("preselected-risk-warning", "data"),
    Input({"type": "wishlist-day-cell", "date": ALL}, "n_clicks"),
    State("wishlist-active-item", "data"),
    State("wishlist-safe-dates", "data"),
    prevent_initial_call=True
)
def open_create_from_wishlist_day(n_clicks_list, active_item, safe_dates):
    # ADR-003 guards...

    date_str = ctx.triggered_id["date"]
    item = deserialize_wishlist_item(active_item)

    # Preselection данные
    amount_str = str(item["amount"])
    description = f"Покупка: {item['name']}"

    # Risk warning из safe_dates
    safe_info = safe_dates.get(date_str, {})
    risk_warning = None
    if not safe_info.get("safe"):
        reasons = safe_info.get("reasons", [])
        if "cushion" in reasons:
            risk_warning = "⚠️ Покупка нарушит финансовую подушку"
        elif "negative_balance" in reasons:
            risk_warning = "🚨 Покупка приведёт к отрицательному балансу"

    return True, date_str, amount_str, description, risk_warning

# В transaction_modals.py (приёмник)
@app.callback(
    Output("create-date-picker", "date"),
    Output("create-amount-input", "value"),
    Output("create-description-input", "value"),
    Output("create-risk-warning", "children"),
    Output("create-risk-warning", "style"),
    Input("create-modal", "is_open"),
    State("preselected-date", "data"),
    State("preselected-amount", "data"),
    State("preselected-description", "data"),
    State("preselected-risk-warning", "data"),
    State("modal-source", "data")
)
def set_preselection_on_modal_open(is_open, date, amount, desc, warning, source):
    if not is_open:
        raise PreventUpdate

    # Применяем preselection
    if source == "wishlist" and date:
        warning_style = {"display": "block"} if warning else {"display": "none"}
        return date, amount or "", desc or "", warning or "", warning_style

    # Default values
    return None, "", "", "", {"display": "none"}
```

**Преимущества**:
- Разделение concerns: источник → Stores → приёмник
- Множественные источники (calendar, dashboard, wishlist) → единый приёмник
- Расширяемо (добавить новые Stores для других полей)
- Type safety через TypedDicts в источниках

**Критичные детали**:
- 4 отдельных Stores (не один dict) — flexibility для опциональных полей
- Reset Stores после create → callback create_transaction возвращает None для всех 4 Stores
- modal-source Store — для определения источника открытия (conditional logic)
- State в set_preselection callback — не trigger при изменении Store (только при is_open)

---

### Selective Refresh Pattern (Протокол 0015)

Обновление только страниц, которые открыты, через global trigger + source tracking.

**Проблема**: Создание транзакции → нужно обновить Calendar, Dashboard, Transactions — но все 3 callbacks срабатывают даже если страницы не открыты.

**Решение**: global-transaction-trigger + modal-source Store

```python
# В transaction_modals.py
dcc.Store(id="modal-source", data=None),  # "calendar" | "dashboard" | "transactions"
dcc.Store(id="global-transaction-trigger", data=None)  # Эмиттер

@app.callback(
    Output("create-modal", "is_open"),
    Output("global-transaction-trigger", "data"),
    Input("create-submit-btn", "n_clicks"),
    State("modal-source", "data")
)
def create_transaction(n_clicks, source):
    # ... создание транзакции ...

    # Emit trigger для refresh
    trigger_data = {
        "timestamp": datetime.now().isoformat(),
        "source": source,  # Откуда был открыт модал
        "action": "create"
    }

    return False, trigger_data  # Close modal, emit trigger

# В calendar.py
@app.callback(
    Output("calendar-grid", "children"),
    Input("global-transaction-trigger", "data"),
    State("url", "pathname"),
    prevent_initial_call=True
)
def refresh_calendar_after_transaction(trigger, pathname):
    # Guard: только если мы на странице календаря
    if pathname != "/calendar":
        raise PreventUpdate

    # Guard: trigger не пустой
    if trigger is None:
        raise PreventUpdate

    # Refresh logic...
    return updated_calendar_grid

# В dashboard.py (аналогично)
@app.callback(
    Output("dashboard-content", "children"),
    Input("global-transaction-trigger", "data"),
    State("url", "pathname"),
    prevent_initial_call=True
)
def refresh_dashboard_after_crud(trigger, pathname):
    if pathname != "/dashboard":
        raise PreventUpdate

    if trigger is None:
        raise PreventUpdate

    # Refresh logic...
    return updated_dashboard
```

**Преимущества**:
- Не срабатывает callback если страница не открыта → экономия ресурсов
- Единый trigger для множества страниц → consistency
- Source tracking для аналитики/debugging
- Расширяемо (добавить action type: create/update/delete)

**Критичные детали**:
- `prevent_initial_call=True` — не срабатывает при mount
- pathname guard в НАЧАЛЕ callback — дешевая проверка до DB queries
- trigger dict с timestamp — уникальность для каждого emit (Dash сравнивает по value)
- modal-source устанавливается при открытии модала из разных источников

---

## Критичные решения

**Helper Functions**: Устранение дублирования > copy-paste (maintainability)

**ADR-003 Guards**: 4-уровневая защита обязательна для Pattern-Matching с n_clicks

**Period Store**: Dict с расширенной структурой > scalar для flexibility

**Preselection Stores**: Отдельные Stores > один dict для optional fields

**Selective Refresh**: pathname guard > всегда refresh (performance)

---

Детали: `ui-components.md` (Dashboard, Calendar, Transactions), `code-style.md` (ADR-003), `architecture.md` (Presentation Layer)
