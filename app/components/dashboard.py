"""
Dashboard компонент - главная страница с обзором финансов.
"""
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
from dash import callback, ctx, html, dcc, no_update, Input, Output, State
from dash.exceptions import PreventUpdate
from loguru import logger

from app.core.database import get_db_session
from app.services import (
    DashboardService,
    OverviewMetrics,
    CashflowDataPoint,
    RecentTransaction,
)
from app.services.onboarding_service import OnboardingService

DEFAULT_USER_ID = 1


# =============================================================================
# Layout
# =============================================================================


def _build_balance_toast() -> dbc.Toast:
    """Создает Toast для предупреждения о нулевом балансе."""
    return dbc.Toast(
        id="balance-alert-toast",
        header="Настройте начальный баланс",
        icon="warning",
        is_open=False,
        dismissable=True,
        duration=None,  # Не закрывается автоматически
        className="balance-toast",
        style={"position": "fixed", "top": 80, "right": 20, "width": 350},
        children=[
            html.P(
                "Для точных расчётов укажите текущий остаток на счетах.",
                className="mb-2",
            ),
            dcc.Link(
                dbc.Button(
                    "Сверить баланс",
                    color="warning",
                    size="sm",
                ),
                href="/calendar?open_recon=1",
            ),
        ],
    )


def create_dashboard_layout():
    """Создает layout главной страницы дашборда."""
    return html.Div(
        [
            # State хранилище для периода
            dcc.Store(
                id="dashboard-period",
                data={"period": "month"},
            ),
            # Header с переключателем периода
            # КРИТИЧНО: должен быть в статическом layout
            html.Div(
                [
                    html.H5("Overview", className="mb-0"),
                    dbc.RadioItems(
                        id="period-switcher",
                        options=[
                            {"label": "Month", "value": "month"},
                            {"label": "Year", "value": "year"},
                        ],
                        value="month",
                        inline=True,
                        className="btn-group",
                        inputClassName="btn-check",
                        labelClassName="btn btn-outline-secondary btn-sm",
                        labelCheckedClassName="btn btn-secondary btn-sm",
                    ),
                ],
                className="d-flex justify-content-between align-items-center mb-3",
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
            # Toast для предупреждения о нулевом балансе
            _build_balance_toast(),
        ]
    )


# =============================================================================
# Static Components (не зависят от данных)
# =============================================================================


def create_metric_card(data: dict) -> dbc.Card:
    """Создает карточку с метрикой.

    Args:
        data: Словарь с параметрами карточки

    Returns:
        dbc.Card с метрикой
    """
    # Стиль карточки
    card_style = {}
    if data.get("gradient"):
        card_style = {
            "background": "linear-gradient(135deg, #28a745 0%, #20c997 100%)",
            "color": "white",
        }

    # Действия (кнопки)
    actions = []
    if data.get("actions"):
        for action in data["actions"]:
            btn = dbc.Button(
                [html.I(className=f"bi {action['icon']} me-1"), action["label"]],
                size="sm",
                color="light" if data.get("gradient") else "primary",
                outline=not data.get("gradient"),
                className="me-2",
            )
            actions.append(btn)

    # Иконка
    icon = None
    if data.get("icon"):
        icon_color = data.get("icon_color", "primary")
        icon = html.Div(
            [
                html.I(
                    className=f"bi {data['icon']}",
                    style={
                        "fontSize": "1.5rem",
                        "color": f"var(--bs-{icon_color})",
                    },
                )
            ],
            className="mb-2",
        )

    card_content = [
        icon,
        html.H6(data["title"], className="card-subtitle mb-2"),
        html.H3(data["value"], className="card-title mb-1"),
        (
            html.Small(data.get("subtitle", ""), className="text-muted")
            if data.get("subtitle")
            else None
        ),
        html.Div(actions, className="mt-3") if actions else None,
    ]

    return dbc.Card(
        [dbc.CardBody(card_content)],
        color=data.get("color", "white"),
        style=card_style,
        className="h-100 shadow-sm",
    )


def create_ai_assistant_card() -> dbc.Card:
    """Создает карточку AI помощника."""
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H6("AI Assistant", className="card-title mb-3"),
                    html.Div(
                        [
                            html.I(
                                className="bi bi-robot",
                                style={"fontSize": "3rem", "color": "#28a745"},
                            ),
                        ],
                        className="text-center mb-3",
                    ),
                    html.P(
                        "What Can I help with?",
                        className="text-center text-muted mb-3",
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-chat-dots me-2"), "Ask anything"],
                        color="success",
                        size="sm",
                        className="w-100",
                    ),
                ]
            )
        ],
        className="shadow-sm",
    )


def create_exchange_card() -> dbc.Card:
    """Создает карточку с курсами валют."""
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H6("Exchange", className="card-title mb-3"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span("USD", className="fw-bold"),
                                    html.Span(" ⇄ ", className="mx-2"),
                                    html.Span("RUB", className="fw-bold"),
                                ],
                                className="text-center mb-3",
                            ),
                            html.Hr(),
                            html.Div(
                                [
                                    html.Div("$100.00", className="h5 mb-0"),
                                    html.Div("₽9200.00", className="text-muted"),
                                ],
                                className="text-center mb-3",
                            ),
                            dbc.Button(
                                "Exchange",
                                color="success",
                                size="sm",
                                className="w-100",
                            ),
                        ]
                    ),
                ]
            )
        ],
        className="shadow-sm",
    )


# =============================================================================
# Dynamic Build Functions (строят UI из данных)
# =============================================================================


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

    if metrics["savings_name"] != "Нет целей":
        savings_value = f"${metrics['savings_current']:,.2f}"
        savings_subtitle = (
            f"{metrics['savings_progress']:.0f}% of "
            f"${metrics['savings_target']:,.2f}"
        )
    else:
        savings_value = "$0.00"
        savings_subtitle = "Нет активных целей"

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
                    # Заголовок (period-switcher вынесен в статический layout)
                    html.H5("Cashflow", className="card-title mb-3"),
                    dcc.Graph(figure=fig, config={"displayModeBar": False}),
                ]
            )
        ],
        className="shadow-sm",
    )


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
                            className=(
                                "d-flex justify-content-between "
                                "align-items-center mb-3"
                            ),
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
                            tx["category_name"] or "Без категории",
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
                        className=(
                            "d-flex justify-content-between align-items-center mb-3"
                        ),
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

        logger.debug(
            f"Dashboard loaded: period={period}, balance={metrics['total_balance']}"
        )
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


@callback(
    [
        Output("dashboard-overview-cards", "children", allow_duplicate=True),
        Output("dashboard-cashflow-chart", "children", allow_duplicate=True),
        Output("dashboard-statistics-card", "children", allow_duplicate=True),
        Output("dashboard-recent-transactions", "children", allow_duplicate=True),
    ],
    Input("global-transaction-trigger", "data"),
    [State("dashboard-period", "data"), State("url", "pathname")],
    prevent_initial_call=True,
)
def refresh_dashboard_after_crud(
    trigger: dict | None,
    period_state: dict | None,
    pathname: str,
):
    """Обновляет дашборд после CRUD операции с транзакцией.

    Слушает global-transaction-trigger из transaction_modals.py.

    Args:
        trigger: Данные триггера {action, timestamp, source, transaction_id}
        period_state: Текущий период
        pathname: Текущий URL

    Returns:
        Tuple из 4 элементов UI: cards, chart, stats, transactions
    """
    # Guard #1: проверяем наличие триггера
    if not trigger:
        raise PreventUpdate

    # Guard #2: обновляем только если мы на странице dashboard
    if pathname not in ["/", "/dashboard"]:
        raise PreventUpdate

    # Определяем период
    if period_state:
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

        source = trigger.get("source", "unknown")
        action = trigger.get("action", "unknown")
        logger.debug(f"Dashboard обновлен после {action} из {source}")
        return cards, chart, stats, transactions

    except Exception as e:
        logger.error(f"Ошибка обновления дашборда после CRUD: {e}")
        raise PreventUpdate


@callback(
    Output("balance-alert-toast", "is_open"),
    [
        Input("url", "pathname"),
        Input("balance-alert-toast", "is_open"),
    ],
    State("balance-toast-dismissed", "data"),
    prevent_initial_call=False,
)
def toggle_balance_toast(
    pathname: str | None,
    is_open: bool,
    is_dismissed: bool,
) -> bool:
    """Показывает Toast если balance=0 и не dismissed."""
    triggered_id = ctx.triggered_id

    # При закрытии через крестик
    if triggered_id == "balance-alert-toast" and not is_open:
        return False

    # При загрузке Dashboard
    if pathname == "/dashboard" or pathname == "/":
        if is_dismissed:
            return False

        try:
            with get_db_session() as session:
                service = OnboardingService(session)
                status = service.get_status(DEFAULT_USER_ID)

            return status["needs_balance_alert"]

        except Exception:
            return False

    return no_update


@callback(
    Output("balance-toast-dismissed", "data"),
    Input("balance-alert-toast", "is_open"),
    State("balance-toast-dismissed", "data"),
    prevent_initial_call=True,
)
def persist_toast_dismissal(is_open: bool, current: bool) -> bool:
    """Запоминает закрытие Toast до перезагрузки."""
    if not is_open and not current:
        return True
    return no_update
