
# Solution v2: Daily & Yearly Cashflow Chart -- DashboardService + Plotly with Public API

## Обзор решения

Решение добавляет два метода в DashboardService: `get_daily_cashflow()` для дневной агрегации за месяц и `get_yearly_cashflow()` для месячной агрегации за год. Оба используют CalendarService через публичный API (новый метод `get_recurring_income_expense_by_day()`) для получения recurring income/expense, устраняя protected access. Визуализация выполняется Plotly grouped bar chart с линией running balance, маркером минимума, hover tooltip через customdata + format_rub, клик на день открывает модал создания операции. Переключатель Month/Year полностью функционален с раздельными графиками.

## Архитектура

### Компоненты

1. **TypedDicts** (`app/schema/dashboard.py` -- НОВЫЙ файл): `DailyCashflow`, `DailyBalancePoint`, `MonthlyCashflowData`, `MonthlyCashflow`, `YearlyCashflowData` + пороговые константы `BALANCE_RISK_THRESHOLD`, `BALANCE_ATTENTION_THRESHOLD`.

2. **CalendarService.get_recurring_income_expense_by_day()** (`app/services/calendar_service.py`): Новый публичный метод, обёртка над `_get_recurring_instances_for_period()`, возвращающая `dict[date, tuple[Decimal, Decimal]]` (income, expense). Единственная точка правды для классификации recurring типов в контексте income/expense split.

3. **DashboardService.get_daily_cashflow()** (`app/services/dashboard_service.py`): Дневная агрегация за месяц, делегирующая balance на `CalendarService.calculate_daily_balances()` и recurring income/expense на `CalendarService.get_recurring_income_expense_by_day()`.

4. **DashboardService.get_yearly_cashflow()** (`app/services/dashboard_service.py`): Месячная агрегация за год -- по 12 месяцам текущего года, с end-of-month balance из CalendarService.

5. **`_build_daily_cashflow_chart()`** (`app/components/dashboard.py`): Plotly figure builder для Month mode -- grouped bars + scatter line + scatter marker + today shape.

6. **`_build_yearly_cashflow_chart()`** (`app/components/dashboard.py`): Plotly figure builder для Year mode -- grouped bars по месяцам + scatter line end-of-month balance.

7. **`_load_dashboard_components()`** (`app/components/dashboard.py`): Helper-функция, устраняющая дублирование между `load_dashboard_data` и `refresh_dashboard_after_crud`.

8. **Callbacks** (`app/components/dashboard.py`): Обновление chart при смене периода, клик на день -> create modal.

### Диаграмма взаимодействия

```
[period-switcher] ──Input──> [load_dashboard_data callback]
                                    │
                                    └─> _load_dashboard_components(period, period_state)
                                            │
                                    ┌───────┴────────────┐
                                    │                    │
                              period=="month"      period=="year"
                                    │                    │
                    DashboardService.get_daily_cashflow()  DashboardService.get_yearly_cashflow()
                            │                                    │
                            ├─> CalendarService                  ├─> CalendarService
                            │   .calculate_daily_balances()      │   .calculate_daily_balances()
                            │                                    │   (per month end)
                            ├─> Direct SQL:                      ├─> Direct SQL:
                            │   SUM(income/expense) BY date      │   SUM(income/expense) BY month
                            │                                    │
                            ├─> CalendarService                  ├─> CalendarService
                            │   .get_recurring_income_expense    │   .get_recurring_income_expense
                            │   _by_day()                        │   _by_day()
                            │                                    │
                            └─> merge + min + classify           └─> merge + min + classify
                                    │                                    │
                    _build_daily_cashflow_chart(data)    _build_yearly_cashflow_chart(data)
                            │                                    │
                            ├─ go.Bar x2 (income, expense)       ├─ go.Bar x2
                            ├─ go.Scatter (balance line)         ├─ go.Scatter (balance line)
                            ├─ go.Scatter (min marker)           ├─ go.Scatter (min marker)
                            └─ shapes: today line                └─ shapes: current month

[daily-cashflow-chart clickData] ──Input──> [open_create_from_chart callback]
                                                │
                                                ├─> Output: create-modal.is_open = True
                                                ├─> Output: preselected-date.data = date
                                                └─> Output: modal-source.data = "chart"
```

## Файловая структура

```
app/schema/dashboard.py              [NEW]  — TypedDicts + constants (~60 строк)
app/schema/__init__.py               [MOD]  — export new TypedDicts (+8 строк)
app/services/calendar_service.py     [MOD]  — get_recurring_income_expense_by_day() (+35 строк)
app/services/dashboard_service.py    [MOD]  — get_daily_cashflow(), get_yearly_cashflow() (+220 строк)
app/services/__init__.py             [MOD]  — export new TypedDicts (+6 строк)
app/components/dashboard.py          [MOD]  — chart builders + helper + callback (~350 строк)
app/components/transaction_modals.py [MOD]  — chart source handler (+10 строк)
tests/test_dashboard_service.py      [MOD]  — 16 unit tests (+250 строк)
```

## Ключевые интерфейсы

```python
# === app/schema/dashboard.py (NEW) ===

from datetime import date
from decimal import Decimal
from typing import Literal, TypedDict

# Константы порогов статуса баланса.
# Размещены рядом с TypedDicts для единого места правды.
BALANCE_RISK_THRESHOLD = Decimal("0")        # balance < 0 -> "risk"
BALANCE_ATTENTION_THRESHOLD = Decimal("5000") # balance < 5000 -> "attention"
# balance >= 5000 -> "ok"

BalanceStatus = Literal["ok", "attention", "risk"]


class DailyCashflow(TypedDict):
    """Дневные данные cashflow для графика Dashboard."""
    date: date       # день месяца (YYYY-MM-DD)
    income: Decimal  # сумма доходов за день (>= 0)
    expense: Decimal # сумма расходов за день (>= 0, положительное число)
    balance: Decimal # running balance (кумулятивный остаток на конец дня)


class DailyBalancePoint(TypedDict):
    """Маркер минимума баланса для графика."""
    date: date                   # дата минимума
    balance: Decimal             # значение минимума
    status: BalanceStatus        # статус баланса


class MonthlyCashflowData(TypedDict):
    """Агрегированные данные для дневного графика за месяц."""
    daily: list[DailyCashflow]                 # дни месяца (1..N)
    min_balance_point: DailyBalancePoint        # минимум месяца (всегда non-None при непустом daily)
    current_date: date                          # сегодня (для подсветки)


class MonthlyCashflow(TypedDict):
    """Месячные данные для годового графика."""
    month: int            # номер месяца (1-12)
    label: str            # короткое имя ("Янв", "Фев", ...)
    income: Decimal       # суммарный доход за месяц
    expense: Decimal      # суммарный расход за месяц
    end_balance: Decimal  # баланс на конец месяца


class YearlyCashflowData(TypedDict):
    """Агрегированные данные для годового графика."""
    monthly: list[MonthlyCashflow]       # 12 месяцев (или до текущего)
    min_balance_point: DailyBalancePoint  # месяц с минимальным end_balance
    current_date: date                    # сегодня (для подсветки текущего месяца)
    year: int                             # отображаемый год


# === app/services/calendar_service.py (addition) ===

def get_recurring_income_expense_by_day(
    self,
    user_id: int,
    start_date: date,
    end_date: date,
) -> dict[date, tuple[Decimal, Decimal]]:
    """Агрегирует income/expense от recurring операций по дням.

    Public API для DashboardService и аналитики.
    Использует внутренний _get_recurring_instances_for_period()
    как единую точку правды для recurring classification.

    NOTE: ADJUSTMENT recurring практически невозможен —
    ADJUSTMENT создаётся только ReconciliationService.
    Если когда-либо появится recurring ADJUSTMENT, нужно
    обновить классификацию здесь.

    Args:
        user_id: ID пользователя
        start_date: Начало периода
        end_date: Конец периода

    Returns:
        dict[date, (income, expense)]: Словарь {дата: (доход, расход)}
    """
    ...


# === app/services/dashboard_service.py (additions) ===

def get_daily_cashflow(
    self,
    user_id: int,
    year: int,
    month: int,
) -> MonthlyCashflowData:
    """Возвращает дневной cashflow для графика Dashboard.

    Args:
        user_id: ID пользователя
        year: Год
        month: Месяц (1-12)

    Returns:
        MonthlyCashflowData с daily, min_balance_point, current_date
    """
    ...


def get_yearly_cashflow(
    self,
    user_id: int,
    year: int,
) -> YearlyCashflowData:
    """Возвращает годовой cashflow (по месяцам) для графика Dashboard.

    Args:
        user_id: ID пользователя
        year: Год

    Returns:
        YearlyCashflowData с monthly, min_balance_point, current_date, year
    """
    ...


# === app/components/dashboard.py (additions) ===

def _build_daily_cashflow_chart(
    data: MonthlyCashflowData,
) -> dbc.Card:
    """Строит Plotly grouped bar chart с линией баланса (Month mode)."""
    ...


def _build_yearly_cashflow_chart(
    data: YearlyCashflowData,
) -> dbc.Card:
    """Строит Plotly grouped bar chart с линией баланса (Year mode)."""
    ...


def _load_dashboard_components(
    period: str,
    period_state: dict | None = None,
) -> tuple:
    """Загружает все компоненты Dashboard.

    Helper, устраняющий дублирование между load_dashboard_data
    и refresh_dashboard_after_crud.

    Args:
        period: "month" или "year"
        period_state: Данные из dashboard-period Store (year, month)

    Returns:
        Tuple (cards, chart, stats, transactions)
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
    """Клик на день графика -> открытие модала создания с preselected датой.

    NB: batch-2.md использует ID 'create-transaction-modal',
    но реальный ID в codebase -- 'create-modal'
    (см. transaction_modals.py:314).
    """
    ...
```

## Модель данных

Новые TypedDicts (нет изменений в БД-схеме):

| TypedDict | Поля | Источник данных |
|-----------|------|-----------------|
| `DailyCashflow` | date, income, expense, balance | SQL + CalendarService |
| `DailyBalancePoint` | date, balance, status | Python вычисление |
| `MonthlyCashflowData` | daily, min_balance_point, current_date | Aggregate (month) |
| `MonthlyCashflow` | month, label, income, expense, end_balance | SQL + CalendarService |
| `YearlyCashflowData` | monthly, min_balance_point, current_date, year | Aggregate (year) |

Пороги статуса баланса (константы в `app/schema/dashboard.py`):
```python
BALANCE_RISK_THRESHOLD = Decimal("0")        # balance < 0 -> "risk"
BALANCE_ATTENTION_THRESHOLD = Decimal("5000") # balance < 5000 -> "attention"
```

Тип-алиас: `BalanceStatus = Literal["ok", "attention", "risk"]`

## Детали реализации get_daily_cashflow()

### Алгоритм

```python
def get_daily_cashflow(
    self, user_id: int, year: int, month: int
) -> MonthlyCashflowData:
    from calendar import monthrange
    from app.schema.dashboard import (
        BALANCE_RISK_THRESHOLD,
        BALANCE_ATTENTION_THRESHOLD,
        DailyCashflow,
        DailyBalancePoint,
        MonthlyCashflowData,
    )

    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    today = date.today()

    # 1. Running balance через CalendarService (уже включает recurring)
    daily_balances = self._calendar_service.calculate_daily_balances(
        user_id, first_day, last_day
    )

    # 2. Income/Expense по дням (обычные транзакции)
    daily_income_expense = self._get_daily_income_expense(
        user_id, first_day, last_day
    )

    # 3. Income/Expense по дням (recurring) — PUBLIC API
    recurring_income_expense = (
        self._calendar_service.get_recurring_income_expense_by_day(
            user_id, first_day, last_day
        )
    )

    # 4. Merge и формирование DailyCashflow[]
    daily_list: list[DailyCashflow] = []
    for day_num in range(1, last_day.day + 1):
        d = date(year, month, day_num)
        inc_reg, exp_reg = daily_income_expense.get(
            d, (Decimal("0"), Decimal("0"))
        )
        inc_rec, exp_rec = recurring_income_expense.get(
            d, (Decimal("0"), Decimal("0"))
        )
        income = inc_reg + inc_rec
        expense = exp_reg + exp_rec
        balance = daily_balances.get(d, Decimal("0"))
        daily_list.append(
            DailyCashflow(
                date=d, income=income, expense=expense, balance=balance
            )
        )

    # 5. Найти минимум (всегда есть — daily_list гарантированно непуст)
    min_day = min(daily_list, key=lambda x: x["balance"])
    min_balance = min_day["balance"]
    status = _classify_balance_status(min_balance)
    min_point = DailyBalancePoint(
        date=min_day["date"], balance=min_balance, status=status
    )

    return MonthlyCashflowData(
        daily=daily_list,
        min_balance_point=min_point,
        current_date=today,
    )
```

### Helper _classify_balance_status()

Выносим в модуль-уровневую функцию для переиспользования в get_daily_cashflow() и get_yearly_cashflow():

```python
def _classify_balance_status(balance: Decimal) -> BalanceStatus:
    """Классифицирует баланс по порогам.

    Args:
        balance: Значение баланса

    Returns:
        "risk" если < 0, "attention" если < 5000, "ok" иначе
    """
    if balance < BALANCE_RISK_THRESHOLD:
        return "risk"
    elif balance < BALANCE_ATTENTION_THRESHOLD:
        return "attention"
    return "ok"
```

### Вспомогательный метод _get_daily_income_expense()

Прямой SQL-запрос. ADJUSTMENT учитывается как income (>0) или expense (<0) -- это осознанное решение, обоснованное ниже.

```python
def _get_daily_income_expense(
    self, user_id: int, start_date: date, end_date: date
) -> dict[date, tuple[Decimal, Decimal]]:
    """Агрегирует income и expense по дням (обычные транзакции).

    Классификация типов:
    - INCOME -> income
    - EXPENSE, SAVINGS_RESERVE, SAVINGS_CONTRIBUTION -> expense
    - ADJUSTMENT: amount > 0 -> income, amount < 0 -> expense (abs)
    - TRANSFER -> игнорируется

    ADJUSTMENT как income/expense — conscious decision:
    ADJUSTMENT создаётся ReconciliationService для корректировки
    разницы между прогнозом и фактом. На графике визуально
    отображается как обычная операция, т.к. реально влияет на баланс.
    Это проще и корректнее чем скрывать (иначе сумма bars
    не соответствует изменению balance line).

    Returns:
        dict[date, (income, expense)]
    """
    results = (
        self.session.query(
            Transaction.transaction_date,
            func.coalesce(func.sum(case(
                (
                    Transaction.transaction_type == TransactionType.INCOME,
                    Transaction.amount,
                ),
                (
                    (Transaction.transaction_type == TransactionType.ADJUSTMENT)
                    & (Transaction.amount > 0),
                    Transaction.amount,
                ),
                else_=Decimal("0"),
            )), Decimal("0")).label("daily_income"),
            func.coalesce(func.sum(case(
                (
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.amount,
                ),
                (
                    Transaction.transaction_type
                    == TransactionType.SAVINGS_RESERVE,
                    Transaction.amount,
                ),
                (
                    Transaction.transaction_type
                    == TransactionType.SAVINGS_CONTRIBUTION,
                    Transaction.amount,
                ),
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
            Transaction.is_recurring == False,  # noqa: E712
            Transaction.recurring_parent_id == None,  # noqa: E711
        )
        .group_by(Transaction.transaction_date)
        .all()
    )
    return {
        row.transaction_date: (
            Decimal(str(row.daily_income)),
            Decimal(str(row.daily_expense)),
        )
        for row in results
    }
```

## Детали реализации get_yearly_cashflow() (NEW)

### Алгоритм

```python
def get_yearly_cashflow(
    self, user_id: int, year: int
) -> YearlyCashflowData:
    """Возвращает годовой cashflow (по месяцам) для Dashboard Year mode.

    Для каждого из 12 месяцев вычисляет:
    - income/expense (обычные + recurring)
    - end_balance (баланс на последний день месяца)

    Args:
        user_id: ID пользователя
        year: Год

    Returns:
        YearlyCashflowData
    """
    from calendar import monthrange
    from app.schema.dashboard import (
        MonthlyCashflow,
        YearlyCashflowData,
        DailyBalancePoint,
    )

    today = date.today()
    monthly_list: list[MonthlyCashflow] = []

    for month_num in range(1, 13):
        first_day = date(year, month_num, 1)
        last_day = date(year, month_num, monthrange(year, month_num)[1])

        # 1. Income/Expense (обычные)
        month_ie = self._get_monthly_income_expense(user_id, first_day, last_day)

        # 2. Income/Expense (recurring)
        recurring_ie = self._calendar_service.get_recurring_income_expense_by_day(
            user_id, first_day, last_day
        )
        rec_income = sum(v[0] for v in recurring_ie.values())
        rec_expense = sum(v[1] for v in recurring_ie.values())

        total_income = month_ie[0] + rec_income
        total_expense = month_ie[1] + rec_expense

        # 3. End-of-month balance
        end_balance = self._calendar_service.get_balance_on_date(
            user_id, last_day
        )

        monthly_list.append(
            MonthlyCashflow(
                month=month_num,
                label=MONTH_NAMES_RU_SHORT[month_num],
                income=total_income,
                expense=total_expense,
                end_balance=end_balance,
            )
        )

    # 4. Найти минимум
    min_month = min(monthly_list, key=lambda x: x["end_balance"])
    # Для DailyBalancePoint.date используем последний день минимального месяца
    min_last_day = date(
        year, min_month["month"],
        monthrange(year, min_month["month"])[1]
    )
    min_point = DailyBalancePoint(
        date=min_last_day,
        balance=min_month["end_balance"],
        status=_classify_balance_status(min_month["end_balance"]),
    )

    return YearlyCashflowData(
        monthly=monthly_list,
        min_balance_point=min_point,
        current_date=today,
        year=year,
    )
```

### Вспомогательный метод _get_monthly_income_expense()

```python
def _get_monthly_income_expense(
    self, user_id: int, start_date: date, end_date: date
) -> tuple[Decimal, Decimal]:
    """Агрегирует income и expense за период (обычные транзакции).

    Используется get_yearly_cashflow для помесячной агрегации.
    Та же классификация типов что и _get_daily_income_expense,
    но без GROUP BY date (один период → одна пара).

    Returns:
        tuple[Decimal, Decimal]: (total_income, total_expense)
    """
    result = (
        self.session.query(
            func.coalesce(func.sum(case(
                (
                    Transaction.transaction_type == TransactionType.INCOME,
                    Transaction.amount,
                ),
                (
                    (Transaction.transaction_type == TransactionType.ADJUSTMENT)
                    & (Transaction.amount > 0),
                    Transaction.amount,
                ),
                else_=Decimal("0"),
            )), Decimal("0")).label("total_income"),
            func.coalesce(func.sum(case(
                (
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.amount,
                ),
                (
                    Transaction.transaction_type
                    == TransactionType.SAVINGS_RESERVE,
                    Transaction.amount,
                ),
                (
                    Transaction.transaction_type
                    == TransactionType.SAVINGS_CONTRIBUTION,
                    Transaction.amount,
                ),
                (
                    (Transaction.transaction_type == TransactionType.ADJUSTMENT)
                    & (Transaction.amount < 0),
                    func.abs(Transaction.amount),
                ),
                else_=Decimal("0"),
            )), Decimal("0")).label("total_expense"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.is_recurring == False,  # noqa: E712
            Transaction.recurring_parent_id == None,  # noqa: E711
        )
        .first()
    )
    return (
        Decimal(str(result.total_income)) if result else Decimal("0"),
        Decimal(str(result.total_expense)) if result else Decimal("0"),
    )
```

**Замечание по производительности Year mode**: `get_yearly_cashflow()` вызывает `get_balance_on_date()` 12 раз (по одному на месяц). Каждый вызов выполняет 2-3 SQL-запроса. Итого ~36 запросов. Для SQLite с одним пользователем это приемлемо (<500ms). Если станет bottleneck -- оптимизировать через единый `calculate_daily_balances(Jan 1, Dec 31)` и выборку end-of-month дат. Добавить TODO-комментарий.

## Детали реализации CalendarService.get_recurring_income_expense_by_day()

```python
def get_recurring_income_expense_by_day(
    self, user_id: int, start_date: date, end_date: date
) -> dict[date, tuple[Decimal, Decimal]]:
    """Агрегирует income/expense от recurring операций по дням.

    Public API для DashboardService и аналитики.

    NOTE: ADJUSTMENT recurring практически невозможен —
    ADJUSTMENT создаётся только ReconciliationService вручную.
    Если когда-либо появится recurring ADJUSTMENT, нужно
    обновить классификацию здесь и в _get_recurring_daily_changes.

    Args:
        user_id: ID пользователя
        start_date: Начало периода
        end_date: Конец периода

    Returns:
        dict[date, (income, expense)]: {дата: (доход, расход)}
            income и expense — положительные числа (>= 0)
    """
    instances = self._get_recurring_instances_for_period(
        user_id, start_date, end_date
    )
    result: dict[date, tuple[Decimal, Decimal]] = defaultdict(
        lambda: (Decimal("0"), Decimal("0"))
    )
    for inst in instances:
        d = inst["date"]
        inc, exp = result[d]
        if inst["transaction_type"] == "income":
            result[d] = (inc + inst["amount"], exp)
        elif inst["transaction_type"] in (
            "expense", "savings_reserve", "savings_contribution"
        ):
            result[d] = (inc, exp + inst["amount"])
        # TRANSFER и другие типы игнорируются
    return dict(result)
```

## Детали реализации _build_daily_cashflow_chart()

```python
STATUS_COLORS: dict[str, str] = {
    "ok": "#27ae60",
    "attention": "#f39c12",
    "risk": "#c0152f",
}


def _build_daily_cashflow_chart(data: MonthlyCashflowData) -> dbc.Card:
    """Строит Plotly grouped bar chart с линией баланса (Month mode).

    Args:
        data: Дневные данные из get_daily_cashflow()

    Returns:
        dbc.Card с dcc.Graph id="daily-cashflow-chart"
    """
    days = [d["date"].day for d in data["daily"]]
    incomes = [float(d["income"]) for d in data["daily"]]
    expenses = [float(d["expense"]) for d in data["daily"]]
    balances = [float(d["balance"]) for d in data["daily"]]

    # Подготовка customdata для hover с format_rub
    hover_incomes = [format_rub(d["income"]) for d in data["daily"]]
    hover_expenses = [format_rub(d["expense"]) for d in data["daily"]]
    hover_balances = [format_rub(d["balance"]) for d in data["daily"]]

    fig = go.Figure()

    # 1. Income bars
    fig.add_trace(go.Bar(
        x=days, y=incomes, name="Доходы",
        marker_color="#27ae60", opacity=0.85,
        customdata=hover_incomes,
        hovertemplate="<b>%{x} числа</b><br>Доход: %{customdata}<extra></extra>",
    ))

    # 2. Expense bars
    fig.add_trace(go.Bar(
        x=days, y=expenses, name="Расходы",
        marker_color="#e74c3c", opacity=0.85,
        customdata=hover_expenses,
        hovertemplate="<b>%{x} числа</b><br>Расход: %{customdata}<extra></extra>",
    ))

    # 3. Balance line
    min_point = data["min_balance_point"]
    line_color = STATUS_COLORS.get(min_point["status"], "#27ae60")

    fig.add_trace(go.Scatter(
        x=days, y=balances, name="Баланс",
        mode="lines+markers",
        line=dict(width=2.5, color=line_color),
        marker=dict(size=4, color=line_color),
        customdata=hover_balances,
        hovertemplate="<b>%{x} числа</b><br>Баланс: %{customdata}<extra></extra>",
        yaxis="y2",
    ))

    # 4. Min marker
    min_text = f"Мин: {min_point['date'].day}, {format_rub(min_point['balance'])}"
    textposition = "top center" if min_point["balance"] < 0 else "bottom center"
    fig.add_trace(go.Scatter(
        x=[min_point["date"].day],
        y=[float(min_point["balance"])],
        mode="markers+text",
        marker=dict(
            size=12, symbol="diamond",
            color=STATUS_COLORS.get(min_point["status"], "#c0152f"),
        ),
        text=[min_text],
        textposition=textposition,
        textfont=dict(
            size=11,
            color=STATUS_COLORS.get(min_point["status"], "#c0152f"),
        ),
        showlegend=False,
        hoverinfo="skip",
        yaxis="y2",
    ))

    # 5. Layout
    shapes = []
    current_day = data["current_date"]
    # Today line — только если today в этом месяце
    if (data["daily"]
        and data["daily"][0]["date"].month == current_day.month
        and data["daily"][0]["date"].year == current_day.year):
        shapes.append(dict(
            type="line",
            x0=current_day.day, x1=current_day.day,
            y0=0, y1=1, yref="paper",
            line=dict(color="#3498db", width=2, dash="dot"),
        ))

    last_day = data["daily"][-1]["date"].day if data["daily"] else 31
    tickvals = [d for d in [1, 8, 15, 22, 29] if d <= last_day]

    fig.update_layout(
        barmode="group",
        height=350,
        margin=dict(l=40, r=40, t=30, b=30),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
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

## Детали реализации _build_yearly_cashflow_chart() (NEW)

```python
def _build_yearly_cashflow_chart(data: YearlyCashflowData) -> dbc.Card:
    """Строит Plotly grouped bar chart с линией баланса (Year mode).

    X-ось: месяцы (Янв..Дек). Bars: income/expense за месяц.
    Линия: end-of-month balance. Маркер: минимум года.

    Args:
        data: Месячные данные из get_yearly_cashflow()

    Returns:
        dbc.Card с dcc.Graph id="daily-cashflow-chart"
            (тот же ID для переключения figure без re-mount)
    """
    labels = [m["label"] for m in data["monthly"]]
    incomes = [float(m["income"]) for m in data["monthly"]]
    expenses = [float(m["expense"]) for m in data["monthly"]]
    balances = [float(m["end_balance"]) for m in data["monthly"]]

    # Hover с format_rub
    hover_incomes = [format_rub(m["income"]) for m in data["monthly"]]
    hover_expenses = [format_rub(m["expense"]) for m in data["monthly"]]
    hover_balances = [format_rub(m["end_balance"]) for m in data["monthly"]]

    fig = go.Figure()

    # 1. Income bars
    fig.add_trace(go.Bar(
        x=labels, y=incomes, name="Доходы",
        marker_color="#27ae60", opacity=0.85,
        customdata=hover_incomes,
        hovertemplate="<b>%{x}</b><br>Доход: %{customdata}<extra></extra>",
    ))

    # 2. Expense bars
    fig.add_trace(go.Bar(
        x=labels, y=expenses, name="Расходы",
        marker_color="#e74c3c", opacity=0.85,
        customdata=hover_expenses,
        hovertemplate="<b>%{x}</b><br>Расход: %{customdata}<extra></extra>",
    ))

    # 3. Balance line
    min_point = data["min_balance_point"]
    line_color = STATUS_COLORS.get(min_point["status"], "#27ae60")

    fig.add_trace(go.Scatter(
        x=labels, y=balances, name="Баланс",
        mode="lines+markers",
        line=dict(width=2.5, color=line_color),
        marker=dict(size=6, color=line_color),
        customdata=hover_balances,
        hovertemplate="<b>%{x}</b><br>Баланс: %{customdata}<extra></extra>",
        yaxis="y2",
    ))

    # 4. Min marker
    min_month_label = MONTH_NAMES_RU_SHORT.get(
        min_point["date"].month, ""
    )
    min_text = f"Мин: {min_month_label}, {format_rub(min_point['balance'])}"
    textposition = "top center" if min_point["balance"] < 0 else "bottom center"
    fig.add_trace(go.Scatter(
        x=[min_month_label],
        y=[float(min_point["balance"])],
        mode="markers+text",
        marker=dict(
            size=12, symbol="diamond",
            color=STATUS_COLORS.get(min_point["status"], "#c0152f"),
        ),
        text=[min_text],
        textposition=textposition,
        textfont=dict(
            size=11,
            color=STATUS_COLORS.get(min_point["status"], "#c0152f"),
        ),
        showlegend=False,
        hoverinfo="skip",
        yaxis="y2",
    ))

    # 5. Layout
    shapes = []
    current_date = data["current_date"]
    # Подсветка текущего месяца (если год совпадает)
    if current_date.year == data["year"]:
        current_label = MONTH_NAMES_RU_SHORT.get(current_date.month, "")
        if current_label in labels:
            idx = labels.index(current_label)
            shapes.append(dict(
                type="rect",
                x0=idx - 0.5, x1=idx + 0.5,
                y0=0, y1=1, yref="paper",
                fillcolor="rgba(52, 152, 219, 0.08)",
                line=dict(width=0),
                layer="below",
            ))

    fig.update_layout(
        barmode="group",
        height=350,
        margin=dict(l=40, r=40, t=30, b=30),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
        hovermode="x unified",
        shapes=shapes,
        xaxis=dict(showgrid=False),
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
            html.H5(
                f"Кассовый календарь — {data['year']}",
                className="card-title mb-3",
            ),
            dcc.Graph(
                id="daily-cashflow-chart",
                figure=fig,
                config={"displayModeBar": False},
            ),
        ])
    ], className="shadow-sm")
```

## Интеграция callbacks

### Dashboard-period Store расширение

Текущая структура Store: `{"period": "month"}`. Расширяем до:
```python
{"period": "month", "year": 2026, "month": 2}
```

Обновить `update_period_state`:
```python
@callback(
    Output("dashboard-period", "data"),
    Input("period-switcher", "value"),
    prevent_initial_call=True,
)
def update_period_state(period_value: str):
    if not period_value:
        raise PreventUpdate
    today = date.today()
    return {
        "period": period_value,
        "year": today.year,
        "month": today.month,
    }
```

### Helper _load_dashboard_components()

```python
def _load_dashboard_components(
    period: str,
    period_state: dict | None = None,
) -> tuple:
    """Загружает все компоненты Dashboard.

    Единая точка для load_dashboard_data и refresh_dashboard_after_crud.

    Args:
        period: "month" или "year"
        period_state: Данные из dashboard-period Store

    Returns:
        tuple: (cards, chart, stats, transactions)
    """
    today = date.today()
    # Год/месяц из Store (для будущей навигации) или today
    display_year = (
        period_state.get("year", today.year) if period_state else today.year
    )
    display_month = (
        period_state.get("month", today.month) if period_state else today.month
    )

    with get_db_session() as session:
        service = DashboardService(session)

        # Metrics
        metrics = service.get_overview_metrics(
            user_id=DEFAULT_USER_ID,
            period=period,
        )

        # Chart
        if period == "month":
            daily_data = service.get_daily_cashflow(
                user_id=DEFAULT_USER_ID,
                year=display_year,
                month=display_month,
            )
            chart = _build_daily_cashflow_chart(daily_data)
        else:
            yearly_data = service.get_yearly_cashflow(
                user_id=DEFAULT_USER_ID,
                year=display_year,
            )
            chart = _build_yearly_cashflow_chart(yearly_data)

        # Stats & Transactions
        recent_transactions = service.get_recent_transactions(
            user_id=DEFAULT_USER_ID,
            limit=5,
        )

    cards = build_overview_cards(metrics, period)
    stats = build_statistics_card(metrics, period)
    transactions = build_recent_transactions_card(recent_transactions, period)

    return cards, chart, stats, transactions
```

### Обновление load_dashboard_data и refresh_dashboard_after_crud

Оба callback-а заменяют тело на:
```python
# В load_dashboard_data:
    try:
        return _load_dashboard_components(period, period_state)
    except Exception as e:
        logger.error(f"Ошибка загрузки дашборда: {e}")
        error_alert = dbc.Alert(...)
        return error_alert, error_alert, error_alert, error_alert

# В refresh_dashboard_after_crud:
    try:
        return _load_dashboard_components(period, period_state)
    except Exception as e:
        logger.error(f"Ошибка обновления дашборда: {e}")
        raise PreventUpdate
```

### open_create_from_chart callback

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
    """Клик на день графика -> модал создания операции.

    NB: batch-2.md использует ID 'create-transaction-modal',
    но реальный ID в codebase -- 'create-modal'
    (см. transaction_modals.py:314).
    """
    # ADR-003 guard clause
    if click_data is None:
        raise PreventUpdate

    period = period_state.get("period", "month") if period_state else "month"
    if period != "month":
        raise PreventUpdate  # Year mode click -> PreventUpdate

    try:
        point = click_data["points"][0]
        day = int(point["x"])
        # Год/месяц из Store, не из date.today()
        today = date.today()
        display_year = (
            period_state.get("year", today.year) if period_state else today.year
        )
        display_month = (
            period_state.get("month", today.month) if period_state else today.month
        )
        clicked_date = date(display_year, display_month, day)
        return True, clicked_date.isoformat(), "chart"
    except (KeyError, IndexError, ValueError):
        raise PreventUpdate
```

### transaction_modals.py update

В `set_preselection_on_modal_open()` добавить handler для `modal_source == "chart"`:

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

1. **Пустой месяц (нет операций)**: daily list содержит все дни месяца с income=0, expense=0, balance=starting_balance. Визуально: плоская линия, без столбцов. min_balance_point вычисляется (значение = starting_balance).

2. **min_balance_point всегда non-None**: Для дневного графика daily_list гарантированно непуст (monthrange возвращает минимум 28 дней). Для годового -- всегда 12 месяцев. Тип `DailyBalancePoint` (не Optional) отражает эту гарантию. Упрощает потребительский код (нет проверки на None).

3. **Несуществующий user_id**: CalendarService возвращает balances с starting_balance=0. Безопасный fallback.

4. **Ошибка БД**: Обрабатывается в `_load_dashboard_components` try/except через load_dashboard_data.

5. **clickData без ожидаемой структуры**: Guard clause с try/except в `open_create_from_chart`.

6. **Year mode click**: PreventUpdate (клик на месяц не открывает модал -- нет однозначной даты).

7. **CalendarService.calculate_daily_balances вернёт неполный dict**: Код использует `.get(d, Decimal("0"))`. Для пропущенного дня balance=0 неверен, но на практике CalendarService всегда возвращает полный dict (итерирует каждый день). Добавить assert-guard если станет проблемой.

## План реализации

### Step 1: TypedDicts + Constants (app/schema/dashboard.py -- NEW)
- Создать файл `app/schema/dashboard.py`
- Определить `BalanceStatus`, `DailyCashflow`, `DailyBalancePoint`, `MonthlyCashflowData`, `MonthlyCashflow`, `YearlyCashflowData`
- Определить `BALANCE_RISK_THRESHOLD`, `BALANCE_ATTENTION_THRESHOLD`
- Обновить `app/schema/__init__.py` -- экспорт
- Обновить `app/services/__init__.py` -- экспорт

### Step 2: CalendarService public method (app/services/calendar_service.py)
- Добавить `get_recurring_income_expense_by_day()` public method
- Guard comment: "ADJUSTMENT recurring практически невозможен"
- Без изменения существующих protected methods

### Step 3: DashboardService methods (app/services/dashboard_service.py)
- Добавить `_classify_balance_status()` module-level helper
- Добавить `_get_daily_income_expense()` private method
- Добавить `_get_monthly_income_expense()` private method
- Добавить `get_daily_cashflow()` public method
- Добавить `get_yearly_cashflow()` public method
- Импорт TypedDicts из `app/schema/dashboard`

### Step 4: Unit тесты (tests/test_dashboard_service.py)
- `TestGetDailyCashflow` class (12 тестов):
  - `test_basic_income_expense` -- 2 операции, проверка daily, balance
  - `test_no_transactions` -- пустой месяц, balance = starting_balance
  - `test_negative_balance_risk_status` -- баланс < 0, status "risk"
  - `test_attention_balance_status` -- 0 <= balance < 5000, status "attention"
  - `test_ok_balance_status` -- balance >= 5000, status "ok"
  - `test_min_balance_in_middle` -- минимум в середине месяца
  - `test_running_balance_cumulative` -- проверка кумулятивности
  - `test_adjustment_positive_as_income` -- ADJUSTMENT > 0 -> income
  - `test_adjustment_negative_as_expense` -- ADJUSTMENT < 0 -> expense
  - `test_transfer_not_counted` -- TRANSFER не учитывается
  - `test_savings_reserve_as_expense` -- SAVINGS_RESERVE -> expense
  - `test_savings_contribution_as_expense` -- SAVINGS_CONTRIBUTION -> expense
- `TestGetYearlyCashflow` class (4 теста):
  - `test_returns_12_months` -- len(monthly) == 12
  - `test_monthly_income_expense` -- корректная агрегация
  - `test_end_balance_correct` -- end_balance == CalendarService balance
  - `test_min_balance_year` -- минимум года определяется правильно

### Step 5: Plotly Charts (app/components/dashboard.py)
- `_build_daily_cashflow_chart()` -- Month mode chart
- `_build_yearly_cashflow_chart()` -- Year mode chart
- `STATUS_COLORS` dict
- `id="daily-cashflow-chart"` на dcc.Graph (единый для обоих режимов)

### Step 6: Dashboard integration (app/components/dashboard.py)
- `_load_dashboard_components()` helper
- Обновить `load_dashboard_data` и `refresh_dashboard_after_crud` -- делегация на helper
- Обновить `update_period_state` -- расширить Store year/month
- Добавить callback `open_create_from_chart`
- Обновить `app/components/transaction_modals.py` -- chart source handler

### Step 7: Финализация
- Black: переформатировать измененные файлы
- Flake8: проверка E501, F401
- pytest: полный набор (>= 508 тестов: 492 + 16 новых)
- Manual testing в браузере

## Зависимости

| Компонент | Зависит от | Тип зависимости |
|-----------|------------|-----------------|
| get_daily_cashflow() | CalendarService.calculate_daily_balances() | Runtime (delegation) |
| get_daily_cashflow() | CalendarService.get_recurring_income_expense_by_day() | Runtime (public API) |
| get_yearly_cashflow() | CalendarService.get_balance_on_date() | Runtime (public API) |
| get_yearly_cashflow() | CalendarService.get_recurring_income_expense_by_day() | Runtime (public API) |
| _build_daily_cashflow_chart() | MonthlyCashflowData TypedDict | Type contract |
| _build_yearly_cashflow_chart() | YearlyCashflowData TypedDict | Type contract |
| _build_*_chart() | format_rub() | Runtime (formatter) |
| open_create_from_chart | Preselection Store Pattern (transaction_modals.py) | Callback chain |
| open_create_from_chart | create-modal (transaction_modals.py:314) | Output target |
| _load_dashboard_components | DashboardService, get_db_session | Runtime |
| Tests | conftest.py fixtures (db_session, test_user) | Test infrastructure |
| MONTH_NAMES_RU_SHORT | dashboard_service.py (already exists) | Constants |

## Риски и mitigation

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| Dual Y-axis (yaxis2) визуально запутывает | Средняя | Среднее | Начать с dual; если плохо -> single Y-axis. Правая ось без label. |
| hovermode="x unified" с yaxis2 показывает все traces | Средняя | Низкое | customdata + hovertemplate гарантируют корректный формат. Browser test. |
| clickData "x" для month mode может быть float | Средняя | Низкое | int() с try/except |
| Year mode get_balance_on_date() x12 -- медленно при больших данных | Низкая | Среднее | TODO: оптимизация через single calculate_daily_balances(). Приемлемо для MVP (<500ms). |
| Callback ID "daily-cashflow-chart" -- конфликт с другими | Низкая | Высокое | Проверено: нет такого ID в codebase. Используется единый ID для обоих режимов. |
| Year mode click на месяц -- неоднозначная дата | Низкая | Низкое | PreventUpdate для year mode clicks. |

## Requirements Traceability Matrix (RTM)

| # | Requirement | Секция spec | Реализация | Тип |
|---|-------------|-------------|------------|-----|
| FR-1 | get_daily_cashflow() returns MonthlyCashflowData | batch-2.md Task 2 | DashboardService.get_daily_cashflow() | Service |
| FR-2 | Running balance includes starting_balance + all ops | batch-2.md Task 2 | CalendarService.calculate_daily_balances() delegation | Service |
| FR-3 | ADJUSTMENT as income/expense, TRANSFER ignored, SAVINGS_* as expense | batch-2.md Task 2, FR-3 brief | _get_daily_income_expense() CASE expressions + guard comment | Service |
| FR-4 | Min balance point with status classification | batch-2.md Task 2 | _classify_balance_status() + constants in schema | Service |
| FR-5 | Grouped bar chart income/expense | dashboard_ui_spec.md s1 | go.Bar x2, barmode="group" | UI |
| FR-6 | Balance line colored by status | dashboard_ui_spec.md s1 | go.Scatter + STATUS_COLORS[min_status] | UI |
| FR-7 | Min marker with text | dashboard_ui_spec.md s1 | go.Scatter markers+text, diamond | UI |
| FR-8 | X-axis ticks multiples of 7, today line | batch-2.md Task 4 | tickvals + shapes (vertical line) | UI |
| FR-9 | Horizontal gridlines, no vertical | dashboard_ui_spec.md s1 | xaxis.showgrid=False, yaxis.gridcolor rgba | UI |
| FR-10 | Hover tooltip unified with format_rub | batch-2.md Task 5 | customdata + format_rub() + hovertemplate | UI |
| FR-11 | Click day -> create modal with preselected date | batch-2.md Task 6 | open_create_from_chart callback + Preselection Store | UI |
| FR-12 | Month/Year toggle | batch-2.md Task 7 | period-switcher -> _load_dashboard_components conditional | UI |
| FR-13 | Year mode: monthly chart with balance line | dashboard_ui_spec.md s1, user decision | get_yearly_cashflow() + _build_yearly_cashflow_chart() | Service+UI |
| FR-14 | Year mode: min marker for year | dashboard_ui_spec.md s1 | min of end_balance across 12 months | Service |
| NFR-1 | get_daily_cashflow < 200ms | batch-2.md Notes | Batch query (1 SQL + 1 CalendarService call) | Perf |
| NFR-2 | Not N queries per day | batch-2.md Notes | Single calculate_daily_balances() call | Perf |
| NFR-3 | Tests >= 508 | batch-2.md Task 9 | 16 unit tests (12 daily + 4 yearly) | Test |
| NFR-4 | Black + Flake8 OK | batch-2.md Task 10 | Finalization step | Quality |

## Blast Radius

### Прямые изменения (файлы, которые будут модифицированы/созданы)
| Файл | Действие | Строк (примерно) |
|------|----------|------------------|
| `app/schema/dashboard.py` | **NEW** | ~60 строк (5 TypedDicts + 2 constants + 1 alias) |
| `app/schema/__init__.py` | MOD | +8 строк (import + __all__) |
| `app/services/calendar_service.py` | MOD | +35 строк (1 public method) |
| `app/services/dashboard_service.py` | MOD | +220 строк (5 methods: 2 public + 3 private) |
| `app/services/__init__.py` | MOD | +6 строк (export new TypedDicts) |
| `app/components/dashboard.py` | MOD | +350 строк (2 chart builders + 1 helper + 1 callback + refactor 2 existing callbacks) |
| `app/components/transaction_modals.py` | MOD | +10 строк (chart source handler) |
| `tests/test_dashboard_service.py` | MOD | +250 строк (16 unit tests) |

**Всего**: 8 файлов (1 new + 7 modified), ~940 строк добавлено.

### Связанные файлы (не изменяются, но используются)
- `app/services/calendar_service.py` -- CalendarService.calculate_daily_balances(), get_balance_on_date(), _get_recurring_instances_for_period()
- `app/models/database.py` -- Transaction, TransactionType, User ORM models
- `app/utils/formatters.py` -- format_rub()
- `app/core/database.py` -- get_db_session()
- `tests/conftest.py` -- db_session (Session fixture), test_user (starting_balance=10000)

### Проверить после реализации
- `app/components/dashboard.py` -- полная функциональность Dashboard (KPI cards, chart, transactions)
- `app/components/transaction_modals.py` -- Preselection Store Pattern корректно работает с source="chart"
- `app/components/calendar.py` -- нет regression (CalendarService API расширен, не изменён)
- `app/components/wishlist.py` -- нет regression (Dashboard wishlist widget)
- Все существующие тесты (492) проходят без regression
- Browser test: Month chart, Year chart, hover tooltip, click day, period switch

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🔴 1. Protected access CalendarService._get_recurring_instances_for_period | Создан новый public method `CalendarService.get_recurring_income_expense_by_day()`. DashboardService вызывает его вместо protected method. Единая точка правды для recurring classification. |
| 🔴 2. ADJUSTMENT-логика расхождение | Добавлено явное обоснование в docstring `_get_daily_income_expense()`: ADJUSTMENT показывается как income/expense bar -- conscious decision, т.к. реально влияет на баланс (скрывать -> расхождение bars vs line). Добавлены unit тесты `test_adjustment_positive_as_income` и `test_adjustment_negative_as_expense`. |
| 🟡 3. Hardcoded today в callback open_create_from_chart | Callback использует `period_state.get("year")` и `period_state.get("month")` вместо `date.today()`. Store расширен до `{"period": "month", "year": 2026, "month": 2}`. |
| 🟡 4. Несоответствие ID в spec | Добавлен NB-комментарий в docstring `open_create_from_chart`: "batch-2.md использует ID 'create-transaction-modal', но реальный ID в codebase -- 'create-modal' (см. transaction_modals.py:314)." |
| 🟡 5. Навигация по месяцам out of scope | Явно указано: навигация по месяцам НЕ в scope батча 5.2 (только текущий месяц). Store `dashboard-period` расширен для year/month для будущей навигации (готовность). |
| 🟡 6. Дублирование callback логики | Вынесена `_load_dashboard_components()` helper-функция. Оба callback-а (`load_dashboard_data` и `refresh_dashboard_after_crud`) делегируют на неё. |
| 🟡 7. Тесты SAVINGS_RESERVE/CONTRIBUTION | Добавлены 2 теста: `test_savings_reserve_as_expense` и `test_savings_contribution_as_expense`. Итого 16 тестов. |
| 🟢 8. Hover формат %{y:,.0f} | Заменён на `customdata` + `format_rub()`. Hover показывает "15 000 ₽" вместо "15,000 ₽". Единообразие с остальным UI. |
| 🟢 9. Константы в schema | `BALANCE_RISK_THRESHOLD` и `BALANCE_ATTENTION_THRESHOLD` размещены в `app/schema/dashboard.py` рядом с TypedDicts. Импортируются в service. |
| 🟢 10. min_balance_point None | Тип изменён на non-Optional `DailyBalancePoint` (без `| None`). Для month mode daily_list всегда непуст (28-31 день). Для year mode -- всегда 12 месяцев. Упрощает потребительский код. |

## Ответы на вопросы критика

1. **ADJUSTMENT на графике**: ADJUSTMENT показывается как обычный income/expense bar. Обоснование: ADJUSTMENT создаётся ReconciliationService для корректировки разницы факт-прогноз. Он реально влияет на баланс. Если скрыть из bars, то сумма зелёных+красных столбцов за день не будет соответствовать изменению balance line -- это визуальное расхождение вводит в заблуждение сильнее. Пользователь видит корректирующую запись как операцию, т.к. она и есть операция (запись в БД типа Transaction). Для MVP это достаточно. В будущем можно добавить визуальное отличие (штриховка или другой оттенок).

2. **Навигация по месяцам**: НЕ в scope батча 5.2. Всегда показывается текущий месяц (today.year, today.month). Store `dashboard-period` расширен для year/month (`{"period": "month", "year": 2026, "month": 2}`) для подготовки к будущей навигации. Callback `open_create_from_chart` использует Store, а не today -- готов к навигации без рефакторинга.

3. **Recurring ADJUSTMENT**: Практически невозможен. ADJUSTMENT создаётся только `ReconciliationService.create_adjustment()` как одноразовая корректировка. Нет UI для создания recurring ADJUSTMENT. Нет API для этого. Добавлен guard comment в `CalendarService.get_recurring_income_expense_by_day()`: "ADJUSTMENT recurring практически невозможен. Если когда-либо появится -- обновить классификацию здесь и в _get_recurring_daily_changes."

4. **Year mode**: Реализуется ПОЛНОСТЬЮ в этом батче. Новый метод `DashboardService.get_yearly_cashflow()` возвращает `YearlyCashflowData` с 12 месяцами. Новый chart builder `_build_yearly_cashflow_chart()` -- grouped bars по месяцам + линия end-of-month balance + маркер минимума года. Старый `get_cashflow_data()`/`build_cashflow_chart()` сохраняется в коде (не удаляется) но не вызывается из Dashboard callbacks.

