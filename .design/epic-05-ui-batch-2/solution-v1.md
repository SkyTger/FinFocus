# Solution v1: Daily Cashflow Chart -- DashboardService + Plotly

## Обзор решения

Решение добавляет метод `get_daily_cashflow()` в DashboardService, который использует `CalendarService.calculate_daily_balances()` для получения running balance и прямой SQL-запрос для агрегации income/expense по дням (включая recurring). Результат визуализируется Plotly grouped bar chart с линией баланса, маркером минимума и hover tooltip. Клик на день открывает модал создания операции через существующий Preselection Store Pattern.

Ключевое архитектурное решение: переиспользовать CalendarService для balance calculation (уже включает recurring, exceptions, skipped instances), но выполнить отдельную агрегацию income/expense для столбцов графика. Это обеспечивает корректность данных без дублирования сложной логики recurring.

## Архитектура

### Компоненты

1. **TypedDicts** (`app/schema/dashboard.py` -- НОВЫЙ файл): `DailyCashflow`, `DailyBalancePoint`, `MonthlyCashflowData` -- типизированные структуры для дневных данных.

2. **DashboardService.get_daily_cashflow()** (`app/services/dashboard_service.py`): Метод агрегации, делегирующий calculation of balance на CalendarService и выполняющий прямую SQL-агрегацию income/expense по дням.

3. **_build_daily_cashflow_chart()** (`app/components/dashboard.py`): Plotly figure builder -- grouped bars + scatter line + scatter marker + shapes (today line).

4. **Callbacks** (`app/components/dashboard.py`): Обновление chart при смене периода (month/year), клик на день -> create modal.

### Диаграмма взаимодействия

```
[period-switcher] ──Input──> [load_dashboard_data callback]
                                    │
                                    ├─> DashboardService.get_daily_cashflow(user_id, year, month)
                                    │       │
                                    │       ├─> CalendarService.calculate_daily_balances()  ← running balance
                                    │       ├─> Direct SQL: SUM(income/expense) GROUP BY date  ← bar data
                                    │       ├─> Direct SQL: SUM(recurring income/expense) via CalendarService  ← recurring bar data
                                    │       └─> Python: merge + find min + classify status
                                    │
                                    └─> _build_daily_cashflow_chart(data, period)
                                            │
                                            └─> Plotly figure:
                                                ├─ go.Bar (income, green)
                                                ├─ go.Bar (expense, red)
                                                ├─ go.Scatter (balance line)
                                                ├─ go.Scatter (min marker)
                                                └─ shapes: today line

[daily-cashflow-chart clickData] ──Input──> [open_create_from_chart callback]
                                                │
                                                ├─> Output: create-modal.is_open = True
                                                ├─> Output: preselected-date.data = date.isoformat()
                                                └─> Output: modal-source.data = "chart"
```

## Файловая структура

```
app/schema/dashboard.py          [NEW]  — TypedDicts for daily cashflow
app/schema/__init__.py           [MOD]  — export new TypedDicts
app/services/dashboard_service.py [MOD] — get_daily_cashflow() method
app/services/__init__.py         [MOD]  — export new TypedDicts
app/components/dashboard.py      [MOD]  — _build_daily_cashflow_chart(), callbacks
tests/test_dashboard_service.py  [MOD]  — 10+ unit tests
```

## Ключевые интерфейсы

```python
# === app/schema/dashboard.py (NEW) ===

from datetime import date
from decimal import Decimal
from typing import Literal, TypedDict


class DailyCashflow(TypedDict):
    """Дневные данные cashflow для графика Dashboard."""
    date: date       # день месяца (YYYY-MM-DD)
    income: Decimal  # сумма доходов за день (>= 0)
    expense: Decimal # сумма расходов за день (>= 0, положительное число)
    balance: Decimal # running balance (кумулятивный остаток на конец дня)


class DailyBalancePoint(TypedDict):
    """Маркер минимума баланса для графика."""
    date: date                                      # дата минимума
    balance: Decimal                                # значение минимума
    status: Literal["ok", "attention", "risk"]      # статус баланса


class MonthlyCashflowData(TypedDict):
    """Агрегированные данные для дневного графика за месяц."""
    daily: list[DailyCashflow]                      # дни месяца (1..N)
    min_balance_point: DailyBalancePoint | None      # минимум месяца
    current_date: date                               # сегодня (для подсветки)


# === app/services/dashboard_service.py (additions) ===

def get_daily_cashflow(
    self,
    user_id: int,
    year: int,
    month: int,
) -> MonthlyCashflowData:
    """Возвращает дневной cashflow для графика Dashboard.

    Логика:
    1. Получить daily balances через CalendarService (running balance с recurring)
    2. Агрегировать income/expense по дням (обычные + recurring)
    3. Найти минимум месяца и определить статус
    4. Вернуть MonthlyCashflowData

    Args:
        user_id: ID пользователя
        year: Год
        month: Месяц (1-12)

    Returns:
        MonthlyCashflowData с daily, min_balance_point, current_date
    """
    ...


# === app/components/dashboard.py (additions) ===

def _build_daily_cashflow_chart(
    data: MonthlyCashflowData,
) -> dbc.Card:
    """Строит Plotly grouped bar chart с линией баланса для Dashboard.

    Args:
        data: Агрегированные дневные данные

    Returns:
        dbc.Card с dcc.Graph
    """
    ...


@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("preselected-date", "data", allow_duplicate=True),
        Output("modal-source", "data", allow_duplicate=True),
    ],
    Input("daily-cashflow-chart", "clickData"),
    State("dashboard-period", "data"),
    prevent_initial_call=True,
)
def open_create_from_chart(click_data, period_state):
    """Клик на день графика -> открытие модала создания с preselected датой."""
    ...
```

## Модель данных

Новые TypedDicts (нет изменений в БД-схеме):

| TypedDict | Поля | Источник данных |
|-----------|------|-----------------|
| `DailyCashflow` | date, income, expense, balance | SQL + CalendarService |
| `DailyBalancePoint` | date, balance, status | Python вычисление |
| `MonthlyCashflowData` | daily, min_balance_point, current_date | Aggregate |

Пороги статуса баланса (константы в `dashboard_service.py`):
```python
BALANCE_RISK_THRESHOLD = Decimal("0")       # balance < 0 -> "risk"
BALANCE_ATTENTION_THRESHOLD = Decimal("5000")  # balance < 5000 -> "attention"
# balance >= 5000 -> "ok"
```

## Детали реализации get_daily_cashflow()

### Алгоритм

```python
def get_daily_cashflow(self, user_id: int, year: int, month: int) -> MonthlyCashflowData:
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    today = date.today()

    # 1. Running balance через CalendarService (уже включает recurring)
    daily_balances = self._calendar_service.calculate_daily_balances(
        user_id, first_day, last_day
    )

    # 2. Income/Expense по дням (обычные транзакции)
    daily_income_expense = self._get_daily_income_expense(user_id, first_day, last_day)

    # 3. Income/Expense по дням (recurring транзакции)
    recurring_income_expense = self._get_recurring_income_expense(user_id, first_day, last_day)

    # 4. Merge и формирование DailyCashflow[]
    daily_list: list[DailyCashflow] = []
    for day_num in range(1, last_day.day + 1):
        d = date(year, month, day_num)
        inc_reg = daily_income_expense.get(d, (Decimal("0"), Decimal("0")))
        inc_rec = recurring_income_expense.get(d, (Decimal("0"), Decimal("0")))
        income = inc_reg[0] + inc_rec[0]
        expense = inc_reg[1] + inc_rec[1]
        balance = daily_balances.get(d, Decimal("0"))
        daily_list.append(DailyCashflow(date=d, income=income, expense=expense, balance=balance))

    # 5. Найти минимум
    min_point = None
    if daily_list:
        min_day = min(daily_list, key=lambda d: d["balance"])
        min_balance = min_day["balance"]
        if min_balance < BALANCE_RISK_THRESHOLD:
            status = "risk"
        elif min_balance < BALANCE_ATTENTION_THRESHOLD:
            status = "attention"
        else:
            status = "ok"
        min_point = DailyBalancePoint(
            date=min_day["date"], balance=min_balance, status=status
        )

    return MonthlyCashflowData(
        daily=daily_list,
        min_balance_point=min_point,
        current_date=today,
    )
```

### Вспомогательный метод _get_daily_income_expense()

Прямой SQL-запрос, агрегирующий income/expense по дням за период. Критически важно:
- Исключить recurring шаблоны (`is_recurring == False`)
- Исключить exceptions (`recurring_parent_id == None`)
- INCOME -> income
- EXPENSE -> expense (положительное число)
- ADJUSTMENT: amount > 0 -> income, amount < 0 -> expense (abs)
- TRANSFER: игнорировать
- SAVINGS_RESERVE, SAVINGS_CONTRIBUTION: -> expense

```python
def _get_daily_income_expense(
    self, user_id: int, start_date: date, end_date: date
) -> dict[date, tuple[Decimal, Decimal]]:
    """Агрегирует income и expense по дням (обычные транзакции).

    Returns:
        dict[date, (income, expense)]: Словарь {дата: (доход, расход)}
    """
    results = (
        self.session.query(
            Transaction.transaction_date,
            func.coalesce(func.sum(case(
                (Transaction.transaction_type == TransactionType.INCOME, Transaction.amount),
                (
                    (Transaction.transaction_type == TransactionType.ADJUSTMENT)
                    & (Transaction.amount > 0),
                    Transaction.amount,
                ),
                else_=Decimal("0"),
            )), Decimal("0")).label("daily_income"),
            func.coalesce(func.sum(case(
                (Transaction.transaction_type == TransactionType.EXPENSE, Transaction.amount),
                (Transaction.transaction_type == TransactionType.SAVINGS_RESERVE, Transaction.amount),
                (Transaction.transaction_type == TransactionType.SAVINGS_CONTRIBUTION, Transaction.amount),
                (
                    (Transaction.transaction_type == TransactionType.ADJUSTMENT)
                    & (Transaction.amount < 0),
                    func.abs(Transaction.amount),
                ),
                else_=Decimal("0"),
            )), Decimal("0")).label("daily_expense"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.is_recurring == False,
            Transaction.recurring_parent_id == None,
        )
        .group_by(Transaction.transaction_date)
        .all()
    )
    return {row.transaction_date: (Decimal(str(row.daily_income)), Decimal(str(row.daily_expense))) for row in results}
```

### Вспомогательный метод _get_recurring_income_expense()

Переиспользует `CalendarService._get_recurring_instances_for_period()` (через delegation pattern):

```python
def _get_recurring_income_expense(
    self, user_id: int, start_date: date, end_date: date
) -> dict[date, tuple[Decimal, Decimal]]:
    """Агрегирует income/expense от recurring по дням.

    Returns:
        dict[date, (income, expense)]
    """
    instances = self._calendar_service._get_recurring_instances_for_period(
        user_id, start_date, end_date
    )
    result: dict[date, tuple[Decimal, Decimal]] = {}
    for inst in instances:
        d = inst["date"]
        current = result.get(d, (Decimal("0"), Decimal("0")))
        if inst["transaction_type"] == "income":
            result[d] = (current[0] + inst["amount"], current[1])
        elif inst["transaction_type"] in ("expense", "savings_reserve", "savings_contribution"):
            result[d] = (current[0], current[1] + inst["amount"])
    return result
```

**Примечание**: Доступ к `_get_recurring_instances_for_period` через protected method CalendarService приемлем, поскольку DashboardService уже является consumer CalendarService (он уже хранит `self._calendar_service`). Альтернатива -- вынести этот метод в public API CalendarService. Рекомендация: оставить как protected access для MVP, но добавить TODO-комментарий для рефакторинга.

## Детали реализации _build_daily_cashflow_chart()

```python
STATUS_COLORS = {
    "ok": "#27ae60",
    "attention": "#f39c12",
    "risk": "#c0152f",
}

def _build_daily_cashflow_chart(data: MonthlyCashflowData) -> dbc.Card:
    days = [d["date"].day for d in data["daily"]]
    incomes = [float(d["income"]) for d in data["daily"]]
    expenses = [float(d["expense"]) for d in data["daily"]]
    balances = [float(d["balance"]) for d in data["daily"]]

    fig = go.Figure()

    # 1. Income bars
    fig.add_trace(go.Bar(
        x=days, y=incomes, name="Доходы",
        marker_color="#27ae60", opacity=0.85,
        hovertemplate="<b>%{x} числа</b><br>Доход: %{y:,.0f} ₽<extra></extra>",
    ))

    # 2. Expense bars
    fig.add_trace(go.Bar(
        x=days, y=expenses, name="Расходы",
        marker_color="#e74c3c", opacity=0.85,
        hovertemplate="<b>%{x} числа</b><br>Расход: %{y:,.0f} ₽<extra></extra>",
    ))

    # 3. Balance line
    min_point = data["min_balance_point"]
    line_color = STATUS_COLORS.get(min_point["status"], "#27ae60") if min_point else "#27ae60"

    fig.add_trace(go.Scatter(
        x=days, y=balances, name="Баланс",
        mode="lines+markers",
        line=dict(width=2.5, color=line_color),
        marker=dict(size=4, color=line_color),
        hovertemplate="<b>%{x} числа</b><br>Баланс: %{y:,.0f} ₽<extra></extra>",
        yaxis="y2",  # secondary Y-axis for balance scale
    ))

    # 4. Min marker
    if min_point:
        min_text = f"Мин: {min_point['date'].day}, {format_rub(min_point['balance'])}"
        textposition = "top center" if min_point["balance"] < 0 else "bottom center"
        fig.add_trace(go.Scatter(
            x=[min_point["date"].day],
            y=[float(min_point["balance"])],
            mode="markers+text",
            marker=dict(size=12, symbol="diamond", color=STATUS_COLORS.get(min_point["status"], "#c0152f")),
            text=[min_text],
            textposition=textposition,
            textfont=dict(size=11, color=STATUS_COLORS.get(min_point["status"], "#c0152f")),
            showlegend=False,
            hoverinfo="skip",
            yaxis="y2",
        ))

    # 5. Layout
    shapes = []
    current_day = data["current_date"]
    # Check if today is in this month
    if data["daily"] and data["daily"][0]["date"].month == current_day.month and data["daily"][0]["date"].year == current_day.year:
        shapes.append(dict(
            type="line",
            x0=current_day.day, x1=current_day.day,
            y0=0, y1=1, yref="paper",
            line=dict(color="#3498db", width=2, dash="dot"),
        ))

    # X-axis tick values: multiples of 7
    last_day = data["daily"][-1]["date"].day if data["daily"] else 31
    tickvals = [d for d in [1, 8, 15, 22, 29] if d <= last_day]

    fig.update_layout(
        barmode="group",
        height=350,
        margin=dict(l=40, r=40, t=30, b=30),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        shapes=shapes,
        xaxis=dict(
            tickvals=tickvals,
            ticktext=[str(v) for v in tickvals],
            showgrid=False,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            gridwidth=1,
            title=None,
        ),
        yaxis2=dict(
            overlaying="y",
            side="right",
            showgrid=False,
            title=None,
        ),
    )

    return dbc.Card([
        dbc.CardBody([
            html.H5("Кассовый календарь", className="card-title mb-3"),
            dcc.Graph(
                id="daily-cashflow-chart",
                figure=fig,
                config={"displayModeBar": False},
            ),
        ])
    ], className="shadow-sm")
```

**Важное решение: Secondary Y-axis (yaxis2)**. Balance line может иметь совершенно другой масштаб, чем income/expense bars. Например, bars могут быть 0-50000, а balance -- 10000-500000. Для читаемости используем secondary Y-axis (yaxis2) справа для линии баланса. Это standard Plotly pattern.

**Альтернатива**: Единый Y-axis. Проще, но может привести к тому, что bars будут крошечными на фоне balance line или наоборот. Рекомендация: начать с secondary Y-axis, но если визуально некорректно -- упростить до единого.

## Интеграция с существующим load_dashboard_data callback

Текущий callback `load_dashboard_data` вызывает `build_cashflow_chart(cashflow_data, period)`. Нужно заменить на:
- Для period="month": вызвать `get_daily_cashflow()` -> `_build_daily_cashflow_chart()`
- Для period="year": оставить старый `get_cashflow_data()` -> `build_cashflow_chart()` (или скрыть)

```python
# В load_dashboard_data:
if period == "month":
    today = date.today()
    daily_data = service.get_daily_cashflow(
        user_id=DEFAULT_USER_ID,
        year=today.year,
        month=today.month,
    )
    chart = _build_daily_cashflow_chart(daily_data)
else:
    # Year mode: keep old behavior (monthly aggregation)
    cashflow_data = service.get_cashflow_data(
        user_id=DEFAULT_USER_ID,
        period=period,
    )
    chart = build_cashflow_chart(cashflow_data, period)
```

Аналогично в `refresh_dashboard_after_crud`.

## Callback: open_create_from_chart

```python
@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("preselected-date", "data", allow_duplicate=True),
        Output("modal-source", "data", allow_duplicate=True),
    ],
    Input("daily-cashflow-chart", "clickData"),
    State("dashboard-period", "data"),
    prevent_initial_call=True,
)
def open_create_from_chart(click_data, period_state):
    """Клик на день графика -> модал создания операции."""
    # ADR-003 guard clause
    if click_data is None:
        raise PreventUpdate

    period = period_state.get("period", "month") if period_state else "month"
    if period != "month":
        raise PreventUpdate  # Year mode click not supported yet

    try:
        point = click_data["points"][0]
        day = int(point["x"])
        today = date.today()
        clicked_date = date(today.year, today.month, day)
        return True, clicked_date.isoformat(), "chart"
    except (KeyError, IndexError, ValueError):
        raise PreventUpdate
```

Важно: Для этого callback нужно убедиться, что `set_preselection_on_modal_open()` в `transaction_modals.py` поддерживает `modal_source == "chart"`. Нужно добавить обработку этого source (аналогично "wishlist") -- устанавливать дату из `preselected-date`.

В существующем `set_preselection_on_modal_open` нужно добавить:
```python
if modal_source == "chart":
    date_value = preselected_date if preselected_date else no_update
    return (
        no_update,  # category
        no_update,  # type
        no_update,  # amount
        date_value,  # date
        no_update,  # description
        no_update,  # alert_text
        no_update,  # alert_open
    )
```

## Обработка ошибок

1. **Пустой месяц (нет операций)**: daily list содержит все дни месяца с income=0, expense=0, balance=starting_balance. Визуально: плоская горизонтальная линия баланса на уровне starting_balance, без столбцов. min_balance_point все равно вычисляется (значение = starting_balance, status по порогам).

2. **Несуществующий user_id**: CalendarService.calculate_daily_balances() вернет balances с starting_balance=0. Безопасный fallback.

3. **Ошибка БД в get_daily_cashflow()**: Обрабатывается в load_dashboard_data try/except (уже существует). Показывается error alert.

4. **clickData без ожидаемой структуры**: Guard clause с try/except в open_create_from_chart.

5. **Месяц из будущего/прошлого**: Работает корректно (CalendarService поддерживает любой диапазон дат, включая forecast через recurring).

## План реализации

### Step 1: TypedDicts (app/schema/dashboard.py -- NEW)
- Создать файл `app/schema/dashboard.py`
- Определить `DailyCashflow`, `DailyBalancePoint`, `MonthlyCashflowData`
- Добавить константы `BALANCE_RISK_THRESHOLD`, `BALANCE_ATTENTION_THRESHOLD`
- Обновить `app/schema/__init__.py` -- экспорт
- Обновить `app/services/__init__.py` -- экспорт

### Step 2: DashboardService.get_daily_cashflow() (app/services/dashboard_service.py)
- Добавить `_get_daily_income_expense()` private method
- Добавить `_get_recurring_income_expense()` private method
- Добавить `get_daily_cashflow()` public method
- Импорт новых TypedDicts из `app/schema/dashboard`

### Step 3: Unit тесты (tests/test_dashboard_service.py)
- `TestGetDailyCashflow` class с 10 тестами:
  - `test_basic_income_expense` -- 2 операции (income+expense), проверка daily, balance
  - `test_no_transactions` -- пустой месяц, balance = starting_balance
  - `test_negative_balance_risk_status` -- баланс уходит в минус
  - `test_attention_balance_status` -- 0 <= balance < 5000
  - `test_ok_balance_status` -- balance >= 5000
  - `test_min_balance_in_middle` -- минимум в середине месяца
  - `test_running_balance_cumulative` -- проверка кумулятивности
  - `test_adjustment_positive_as_income` -- ADJUSTMENT > 0
  - `test_adjustment_negative_as_expense` -- ADJUSTMENT < 0
  - `test_transfer_not_counted` -- TRANSFER не учитывается
  - `test_current_date_is_today` -- current_date = today
  - `test_all_days_present` -- len(daily) == monthrange(year, month)[1]
- Запуск: pytest -- все тесты pass

### Step 4: Plotly Chart (_build_daily_cashflow_chart) (app/components/dashboard.py)
- Вспомогательная функция `_build_daily_cashflow_chart(data: MonthlyCashflowData) -> dbc.Card`
- go.Bar x2 (income, expense) + go.Scatter (balance line) + go.Scatter (min marker)
- Layout: barmode="group", hovermode="x unified", shapes (today line)
- X-axis: tickvals [1,8,15,22,29], без vertical grid
- Y-axis: horizontal gridlines rgba(0,0,0,0.1)
- Добавить `id="daily-cashflow-chart"` на dcc.Graph

### Step 5: Callback интеграция (app/components/dashboard.py)
- Обновить `load_dashboard_data`: switch между daily chart (month) и old chart (year)
- Обновить `refresh_dashboard_after_crud`: аналогичный switch
- Добавить callback `open_create_from_chart`: clickData -> create-modal + preselected-date
- Обновить `app/components/transaction_modals.py`: добавить `modal_source == "chart"` handler

### Step 6: Финализация
- Black: переформатировать измененные файлы
- Flake8: проверка E501, F401
- pytest: полный набор (>= 502 тестов)
- Manual testing в браузере

## Зависимости

| Компонент | Зависит от | Тип зависимости |
|-----------|------------|-----------------|
| get_daily_cashflow() | CalendarService.calculate_daily_balances() | Runtime (delegation) |
| get_daily_cashflow() | CalendarService._get_recurring_instances_for_period() | Runtime (protected access) |
| _build_daily_cashflow_chart() | MonthlyCashflowData TypedDict | Type contract |
| _build_daily_cashflow_chart() | format_rub() | Runtime (formatter) |
| open_create_from_chart | Preselection Store Pattern (transaction_modals.py) | Callback chain |
| open_create_from_chart | create-modal (transaction_modals.py) | Output target |
| Tests | conftest.py fixtures (db_session, test_user) | Test infrastructure |

## Риски и mitigation

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| Protected access to CalendarService._get_recurring_instances_for_period() -- ломается при рефакторинге | Средняя | Высокое | Добавить TODO для вынесения в public API; unit тесты покроют regression |
| Dual Y-axis (yaxis2) может визуально запутать пользователя | Средняя | Среднее | Начать с dual; если визуально плохо, переключиться на single Y-axis |
| hovermode="x unified" может некорректно показывать yaxis2 данные | Средняя | Низкое | Тестирование в браузере; fallback на hovermode="closest" |
| clickData формат при grouped bars -- "x" может быть строкой, не int | Средняя | Низкое | int() conversion с try/except |
| Callback ID conflict: "daily-cashflow-chart" должен быть уникальным | Низкая | Высокое | Проверить нет ли такого ID в codebase |
| Performance: 2 запроса (calculate_daily_balances + income/expense) vs 1 | Низкая | Низкое | calculate_daily_balances уже оптимизирован; общее время < 200ms |

## Requirements Traceability Matrix (RTM)

| # | Requirement | Секция spec | Реализация | Тип |
|---|-------------|-------------|------------|-----|
| FR-1 | get_daily_cashflow() returns MonthlyCashflowData | batch-2.md Task 2 | DashboardService.get_daily_cashflow() | Service |
| FR-2 | Running balance includes starting_balance + all ops | batch-2.md Task 2 | CalendarService.calculate_daily_balances() delegation | Service |
| FR-3 | ADJUSTMENT as income/expense, TRANSFER ignored | batch-2.md Task 2 | _get_daily_income_expense() CASE expressions | Service |
| FR-4 | Min balance point with status classification | batch-2.md Task 2 | Python min() + threshold constants | Service |
| FR-5 | Grouped bar chart income/expense | dashboard_ui_spec.md s1 | go.Bar x2, barmode="group" | UI |
| FR-6 | Balance line colored by status | dashboard_ui_spec.md s1 | go.Scatter + STATUS_COLORS[min_status] | UI |
| FR-7 | Min marker with text | dashboard_ui_spec.md s1 | go.Scatter markers+text, diamond | UI |
| FR-8 | X-axis ticks multiples of 7, today line | batch-2.md Task 4 | tickvals + shapes (vertical line) | UI |
| FR-9 | Horizontal gridlines, no vertical | dashboard_ui_spec.md s1 | xaxis.showgrid=False, yaxis.gridcolor rgba | UI |
| FR-10 | Hover tooltip unified | batch-2.md Task 5 | hovermode="x unified" + hovertemplate | UI |
| FR-11 | Click day -> create modal with preselected date | batch-2.md Task 6 | open_create_from_chart callback + Preselection Store | UI |
| FR-12 | Month/Year toggle | batch-2.md Task 7 | Existing period-switcher, conditional chart build | UI |
| NFR-1 | get_daily_cashflow < 200ms | batch-2.md Notes | Batch query (1 SQL + 1 CalendarService call) | Perf |
| NFR-2 | Not N queries per day | batch-2.md Notes | Single calculate_daily_balances() call | Perf |
| NFR-3 | Tests >= 502 | batch-2.md Task 9 | 10+ unit tests for get_daily_cashflow | Test |
| NFR-4 | Black + Flake8 OK | batch-2.md Task 10 | Finalization step | Quality |

## Blast Radius

### Прямые изменения (файлы, которые будут модифицированы/созданы)
| Файл | Действие | Строк (примерно) |
|------|----------|------------------|
| `app/schema/dashboard.py` | **NEW** | ~40 строк (3 TypedDicts + 2 constants) |
| `app/schema/__init__.py` | MOD | +6 строк (import + __all__) |
| `app/services/dashboard_service.py` | MOD | +130 строк (3 methods) |
| `app/services/__init__.py` | MOD | +4 строки (export new TypedDicts) |
| `app/components/dashboard.py` | MOD | +200 строк (chart builder + callback) |
| `app/components/transaction_modals.py` | MOD | +10 строк (chart source handler) |
| `tests/test_dashboard_service.py` | MOD | +180 строк (12 unit tests) |

**Всего**: 7 файлов (1 new + 6 modified), ~570 строк добавлено.

### Связанные файлы (не изменяются, но используются)
- `app/services/calendar_service.py` -- CalendarService.calculate_daily_balances() и _get_recurring_instances_for_period()
- `app/models/database.py` -- Transaction, TransactionType, User ORM models
- `app/utils/formatters.py` -- format_rub()
- `app/core/database.py` -- get_db_session()
- `tests/conftest.py` -- db_session, test_user fixtures

### Проверить после реализации
- `app/components/dashboard.py` -- полная функциональность Dashboard (KPI cards, chart, transactions)
- `app/components/transaction_modals.py` -- Preselection Store Pattern корректно работает с source="chart"
- `app/components/calendar.py` -- нет regression (CalendarService не изменяется)
- `app/components/wishlist.py` -- нет regression (Dashboard wishlist widget)
- Все существующие тесты (492) проходят без regression