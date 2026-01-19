# Шаг 4: Рефакторинг Dashboard UI

## Briefing
- **Цель:** Переписать `app/components/dashboard.py` для работы с реальными данными через DashboardService, добавить callbacks и dcc.Store для переключения периода.
- **Ключевые файлы:**
  - `app/components/dashboard.py` (изменить)
  - `app/components/calendar.py` (референс для паттернов callbacks)
- **Additional info:**
  - Следовать паттерну callbacks из calendar.py (guard clauses, ADR-003)
  - dcc.Store для хранения текущего периода
  - Функции `build_*` принимают данные как параметры
  - DEFAULT_USER_ID = 1 (hardcoded до авторизации)
  - При пустой БД показывать нули, не ошибки
  - Исправить E501 ошибки (строки > 88 символов)

## Sub-tasks

### 4.1. Добавить импорты

В начало файла добавить:
```python
from dash import callback, ctx, Input, Output, State
from dash.exceptions import PreventUpdate
from loguru import logger

from app.core.database import get_db_session
from app.services import (
    DashboardService,
    OverviewMetrics,
    CashflowDataPoint,
    RecentTransaction,
)

DEFAULT_USER_ID = 1
```

### 4.2. Рефакторинг create_dashboard_layout()

Заменить функцию на:
```python
def create_dashboard_layout():
    """Создает layout главной страницы дашборда."""
    return html.Div(
        [
            # State хранилище для периода
            dcc.Store(
                id="dashboard-period",
                data={"period": "month"},
            ),
            # Верхние карточки (динамические)
            html.Div(
                id="dashboard-overview-cards",
                children=html.Div("Загрузка...", className="text-muted p-4"),
            ),
            # Строка с графиками
            dbc.Row(
                [
                    dbc.Col(
                        [html.Div(id="dashboard-cashflow-chart")],
                        width=8,
                    ),
                    dbc.Col(
                        [
                            create_ai_assistant_card(),
                            html.Div(style={"height": "20px"}),
                            html.Div(id="dashboard-statistics-card"),
                        ],
                        width=4,
                    ),
                ],
                className="mb-4",
            ),
            # Нижняя строка
            dbc.Row(
                [
                    dbc.Col(
                        [html.Div(id="dashboard-recent-transactions")],
                        width=8,
                    ),
                    dbc.Col([create_exchange_card()], width=4),
                ]
            ),
        ]
    )
```

### 4.3. Создать функцию build_overview_cards()

```python
def build_overview_cards(metrics: OverviewMetrics, period: str) -> dbc.Row:
    """Создает верхние карточки с реальными данными.

    Args:
        metrics: Метрики из DashboardService
        period: "month" или "year"

    Returns:
        dbc.Row с 4 карточками метрик
    """
    # Форматирование
    total_balance = f"${metrics['total_balance']:,.2f}"
    period_income = f"${metrics['period_income']:,.2f}"
    period_expense = f"${metrics['period_expense']:,.2f}"

    if metrics["savings_name"]:
        savings_value = f"${metrics['savings_current']:,.2f}"
        savings_subtitle = (
            f"{metrics['savings_progress']:.0f}% of "
            f"${metrics['savings_target']:,.2f}"
        )
    else:
        savings_value = "$0.00"
        savings_subtitle = "No active goal"

    period_label = "This Month" if period == "month" else "This Year"

    cards_data = [
        {
            "title": "Total Balance",
            "value": total_balance,
            "subtitle": "USD",
            "color": "success",
            "gradient": True,
            "actions": [
                {"label": "Deposit", "icon": "bi-plus"},
                {"label": "Send", "icon": "bi-arrow-up-right"},
            ],
        },
        {
            "title": f"Income ({period_label})",
            "value": period_income,
            "color": "light",
            "icon": "bi-arrow-down-left",
            "icon_color": "success",
        },
        {
            "title": f"Expense ({period_label})",
            "value": period_expense,
            "color": "light",
            "icon": "bi-arrow-up-right",
            "icon_color": "danger",
        },
        {
            "title": "Savings",
            "value": savings_value,
            "subtitle": savings_subtitle,
            "color": "light",
            "icon": "bi-piggy-bank",
            "icon_color": "primary",
        },
    ]

    cards = [dbc.Col(create_metric_card(data), width=3) for data in cards_data]
    return dbc.Row(cards, className="mb-4")
```

### 4.4. Создать функцию build_cashflow_chart()

```python
def build_cashflow_chart(
    cashflow_data: list[CashflowDataPoint],
    period: str,
) -> dbc.Card:
    """Создает график денежного потока с реальными данными.

    Args:
        cashflow_data: Данные из DashboardService
        period: "month" или "year"

    Returns:
        dbc.Card с графиком Plotly
    """
    labels = [d["label"] for d in cashflow_data]
    income_values = [float(d["income"]) for d in cashflow_data]
    expense_values = [float(d["expense"]) for d in cashflow_data]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=labels,
            y=income_values,
            name="Income",
            marker_color="#28a745",
            opacity=0.8,
        )
    )
    fig.add_trace(
        go.Bar(
            x=labels,
            y=expense_values,
            name="Expense",
            marker_color="#17a2b8",
            opacity=0.8,
        )
    )

    fig.update_layout(
        barmode="group",
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.H5("Cashflow", className="card-title mb-0"),
                            dbc.RadioItems(
                                id="period-switcher",
                                options=[
                                    {"label": "Month", "value": "month"},
                                    {"label": "Year", "value": "year"},
                                ],
                                value=period,
                                inline=True,
                                className="btn-group",
                                inputClassName="btn-check",
                                labelClassName="btn btn-outline-secondary btn-sm",
                                labelCheckedClassName="btn btn-secondary btn-sm",
                            ),
                        ],
                        className="d-flex justify-content-between align-items-center mb-3",
                    ),
                    dcc.Graph(figure=fig, config={"displayModeBar": False}),
                ]
            )
        ],
        className="shadow-sm",
    )
```

### 4.5. Создать функцию build_statistics_card()

```python
def build_statistics_card(metrics: OverviewMetrics, period: str) -> dbc.Card:
    """Создает карточку со статистикой (pie chart).

    Args:
        metrics: Метрики из DashboardService
        period: "month" или "year"

    Returns:
        dbc.Card с donut chart
    """
    income = float(metrics["period_income"])
    expense = float(metrics["period_expense"])

    # Guard: если нет данных, показываем placeholder
    if income == 0 and expense == 0:
        values = [1, 1]
        colors = ["#e9ecef", "#e9ecef"]
    else:
        values = [income, expense]
        colors = ["#28a745", "#17a2b8"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Income", "Expense"],
                values=values,
                hole=0.6,
                marker_colors=colors,
                showlegend=False,
                textinfo="none",
            )
        ]
    )
    fig.update_layout(
        height=150,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="white",
    )

    period_label = "This Month" if period == "month" else "This Year"

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H6("Statistic", className="card-title mb-3"),
                    html.Div(period_label, className="small text-muted mb-2"),
                    dcc.Graph(figure=fig, config={"displayModeBar": False}),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        className="d-inline-block rounded-circle me-2",
                                        style={
                                            "width": "10px",
                                            "height": "10px",
                                            "backgroundColor": "#28a745",
                                        },
                                    ),
                                    html.Span("Income ", className="small"),
                                    html.Span(
                                        f"${metrics['period_income']:,.0f}",
                                        className="fw-bold",
                                    ),
                                ],
                                className="mb-1",
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        className="d-inline-block rounded-circle me-2",
                                        style={
                                            "width": "10px",
                                            "height": "10px",
                                            "backgroundColor": "#17a2b8",
                                        },
                                    ),
                                    html.Span("Expense ", className="small"),
                                    html.Span(
                                        f"${metrics['period_expense']:,.0f}",
                                        className="fw-bold",
                                    ),
                                ]
                            ),
                        ]
                    ),
                ]
            )
        ],
        className="shadow-sm",
    )
```

### 4.6. Создать функцию build_recent_transactions_card()

```python
def build_recent_transactions_card(
    transactions: list[RecentTransaction],
    period: str,
) -> dbc.Card:
    """Создает карточку с последними операциями.

    Args:
        transactions: Список транзакций из DashboardService
        period: "month" или "year" (для label)

    Returns:
        dbc.Card с таблицей транзакций
    """
    period_label = "This Month" if period == "month" else "This Year"

    if not transactions:
        return dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.H5(
                                    "Recent Transactions",
                                    className="card-title mb-0",
                                ),
                                dbc.Button(period_label, size="sm", color="light"),
                            ],
                            className="d-flex justify-content-between align-items-center mb-3",
                        ),
                        html.P("No transactions yet", className="text-muted"),
                    ]
                )
            ],
            className="shadow-sm",
        )

    transaction_rows = []
    for tx in transactions:
        # Форматирование суммы
        if tx["transaction_type"] == "income":
            amount_str = f"+${tx['amount']:,.2f}"
            amount_class = "fw-bold text-success"
        elif tx["transaction_type"] == "expense":
            amount_str = f"-${tx['amount']:,.2f}"
            amount_class = "fw-bold text-danger"
        else:  # transfer
            amount_str = f"${tx['amount']:,.2f}"
            amount_class = "fw-bold text-muted"

        row = html.Tr(
            [
                html.Td(
                    [
                        html.Div(
                            tx["description"] or "No description",
                            className="fw-semibold",
                        ),
                        html.Div(
                            tx["category"] or "Uncategorized",
                            className="small text-muted",
                        ),
                    ]
                ),
                html.Td(tx["date"], className="text-muted"),
                html.Td(amount_str, className=amount_class),
                html.Td(
                    [
                        dbc.Badge(
                            "Completed",
                            color="success",
                            className="rounded-pill",
                        )
                    ]
                ),
            ]
        )
        transaction_rows.append(row)

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.H5(
                                "Recent Transactions",
                                className="card-title mb-0",
                            ),
                            dbc.Button(period_label, size="sm", color="light"),
                        ],
                        className="d-flex justify-content-between align-items-center mb-3",
                    ),
                    dbc.Table(
                        [html.Tbody(transaction_rows)],
                        borderless=True,
                        hover=True,
                    ),
                ]
            )
        ],
        className="shadow-sm",
    )
```

### 4.7. Добавить главный callback load_dashboard_data()

Добавить в конец файла:
```python
# =============================================================================
# Callbacks
# =============================================================================


@callback(
    [
        Output("dashboard-overview-cards", "children"),
        Output("dashboard-cashflow-chart", "children"),
        Output("dashboard-statistics-card", "children"),
        Output("dashboard-recent-transactions", "children"),
    ],
    [
        Input("url", "pathname"),
        Input("period-switcher", "value"),
    ],
    [State("dashboard-period", "data")],
)
def load_dashboard_data(
    pathname: str,
    period_value: str | None,
    period_state: dict | None,
):
    """Загружает данные дашборда при навигации или смене периода.

    Срабатывает:
    - При переходе на /dashboard или /
    - При изменении period-switcher

    Args:
        pathname: Текущий URL
        period_value: Значение переключателя периода
        period_state: Состояние из dcc.Store

    Returns:
        Tuple из 4 элементов UI: cards, chart, stats, transactions
    """
    # Guard #1: только для страницы dashboard
    if pathname not in ["/", "/dashboard"]:
        raise PreventUpdate

    # Определяем период
    if period_value:
        period = period_value
    elif period_state:
        period = period_state.get("period", "month")
    else:
        period = "month"

    try:
        with get_db_session() as session:
            service = DashboardService(session)

            # Загружаем все данные
            metrics = service.get_overview_metrics(
                user_id=DEFAULT_USER_ID,
                period=period,
            )
            cashflow_data = service.get_cashflow_data(
                user_id=DEFAULT_USER_ID,
                period=period,
            )
            recent_transactions = service.get_recent_transactions(
                user_id=DEFAULT_USER_ID,
                limit=5,
            )

        # Строим UI компоненты
        cards = build_overview_cards(metrics, period)
        chart = build_cashflow_chart(cashflow_data, period)
        stats = build_statistics_card(metrics, period)
        transactions = build_recent_transactions_card(recent_transactions, period)

        logger.debug(f"Dashboard loaded: period={period}, balance={metrics['total_balance']}")
        return cards, chart, stats, transactions

    except Exception as e:
        logger.error(f"Ошибка загрузки дашборда: {e}")
        error_alert = dbc.Alert(
            "Не удалось загрузить данные. Попробуйте обновить страницу.",
            color="danger",
        )
        return error_alert, error_alert, error_alert, error_alert


@callback(
    Output("dashboard-period", "data"),
    Input("period-switcher", "value"),
    prevent_initial_call=True,
)
def update_period_state(period_value: str):
    """Обновляет состояние периода в dcc.Store.

    Args:
        period_value: Новое значение периода

    Returns:
        dict с обновленным периодом
    """
    if not period_value:
        raise PreventUpdate

    return {"period": period_value}
```

### 4.8. Удалить старую функцию create_overview_cards()

Удалить функцию `create_overview_cards()` (она заменена на `build_overview_cards()`).

### 4.9. Исправить E501 ошибки

Проверить и исправить строки длиннее 88 символов в оставшихся функциях (create_metric_card, create_ai_assistant_card, etc.).

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 4.1-4.9.
2. **Верификация:** После завершения ВСЕХ подзадач запусти проверки:
   ```bash
   cd /home/skytiger/PycharmProjects/worktrees/0003-dashboard-integration
   black app/components/dashboard.py
   flake8 app/components/dashboard.py
   python -c "from app.components.dashboard import create_dashboard_layout; print('OK')"
   ```
3. **Фиксация:** После успешной верификации:
   - Добавь запись в `log.md`
   - Обнови `context.md`: `Current Step` = 5
   - Проверь ветку main
4. **Коммит**: `git add . && git commit -m "feat(dashboard): integrate with real data via callbacks [protocol-0003/04]"`. Push.
5. **Отчет пользователю** в установленном формате.
