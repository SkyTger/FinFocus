"""
Dashboard компонент - главная страница с обзором финансов.
"""
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
from dash import callback, ctx, html, dcc, no_update, Input, Output, State
from dash.exceptions import PreventUpdate
from loguru import logger

from app.core.database import get_db_session
from app.components.wishlist import build_wishlist_widget
from app.services import (
    DashboardService,
    OverviewMetrics,
    CashflowDataPoint,
    RecentTransaction,
)
from app.services.dashboard_service import MONTH_NAMES_RU_SHORT
from app.services.onboarding_service import OnboardingService
from app.schema.dashboard import MonthlyCashflowData, YearlyCashflowData
from datetime import date
from decimal import Decimal

from app.utils.formatters import format_rub

DEFAULT_USER_ID = 1

STATUS_COLORS: dict[str, str] = {
    "ok": "#27ae60",
    "attention": "#f39c12",
    "risk": "#c0152f",
}


# =============================================================================
# Layout
# =============================================================================


def _build_balance_banner() -> dbc.Alert:
    """Создает баннер для предупреждения о нулевом балансе."""
    return dbc.Alert(
        id="balance-alert-toast",
        is_open=False,
        dismissable=True,
        className="balance-banner mb-3",
        children=[
            html.Div(
                [
                    html.I(className="bi bi-exclamation-triangle-fill me-2"),
                    html.Span(
                        "Для точных расчётов укажите текущий остаток на счетах.",
                        className="me-3",
                    ),
                    dcc.Link(
                        dbc.Button(
                            "Сверить баланс",
                            color="dark",
                            size="sm",
                            outline=True,
                        ),
                        href="/calendar?open_recon=1",
                    ),
                ],
                className="d-flex align-items-center justify-content-center flex-wrap",
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
            # Баннер предупреждения о балансе (вверху контента)
            _build_balance_banner(),
            # Header с переключателем периода
            # КРИТИЧНО: должен быть в статическом layout
            html.Div(
                [
                    html.H5("Обзор", className="mb-0"),
                    dbc.RadioItems(
                        id="period-switcher",
                        options=[
                            {"label": "Месяц", "value": "month"},
                            {"label": "Год", "value": "year"},
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
                            build_wishlist_widget(),
                            # TODO: Epic-08 — реализовать AI Assistant
                            # create_ai_assistant_card(),
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
                    # TODO: Epic-08 — реализовать Exchange
                    # dbc.Col([create_exchange_card()], width=4),
                    dbc.Col(width=4),
                ]
            ),
        ]
    )


# =============================================================================
# Static Components (не зависят от данных)
# =============================================================================


def _build_kpi_card(
    title: str,
    value: str,
    subtitle: str = "",
    icon: str = "",
    icon_color: str = "#2c3e50",
    status_border_color: str = "",
    action_button: html.Div | dcc.Link | None = None,
) -> html.Div:
    """Создает KPI-карточку в новом дизайне.

    Args:
        title: Заголовок карточки
        value: Основное значение (уже отформатированное)
        subtitle: Подпись под значением
        icon: Bootstrap icon class (например "bi-wallet2")
        icon_color: Цвет иконки
        status_border_color: Цвет верхней границы (опционально)
        action_button: CTA кнопка (опционально)

    Returns:
        html.Div с KPI-карточкой
    """
    style: dict = {}
    if status_border_color:
        style["borderTop"] = f"3px solid {status_border_color}"

    icon_el = None
    if icon:
        icon_el = html.I(
            className=f"bi {icon}",
            style={"fontSize": "1.5rem", "color": icon_color},
        )

    card_content = [
        html.Div(
            [
                icon_el,
                html.Div(title, className="kpi-title"),
            ],
            className="d-flex align-items-center gap-2 mb-2",
        )
        if icon_el is not None
        else html.Div(title, className="kpi-title mb-2"),
        html.Div(value, className="kpi-number mb-1"),
    ]

    if subtitle:
        card_content.append(html.Div(subtitle, className="kpi-subtitle"))

    if action_button:
        card_content.append(html.Div(action_button, className="mt-2"))

    return html.Div(card_content, className="kpi-card h-100", style=style)


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
    total_balance = format_rub(metrics["total_balance"])
    period_income = format_rub(metrics["period_income"])
    period_expense = format_rub(metrics["period_expense"])

    if metrics["savings_name"] != "Нет целей":
        savings_value = format_rub(metrics["savings_current"])
        savings_subtitle = (
            f"{metrics['savings_progress']:.0f}% из "
            f"{format_rub(metrics['savings_target'])}"
        )
    else:
        savings_value = format_rub(0)
        savings_subtitle = "Нет активных целей"

    period_label = "За месяц" if period == "month" else "За год"

    recon_button = dcc.Link(
        dbc.Button(
            [html.I(className="bi bi-check2-square me-1"), "Сверка"],
            size="sm",
            color="success",
            outline=True,
        ),
        href="/calendar?open_recon=1",
    )

    cards = [
        dbc.Col(
            _build_kpi_card(
                title="Общий баланс",
                value=total_balance,
                icon="bi-wallet2",
                icon_color="#27ae60",
                status_border_color="#2ecc71",
                action_button=recon_button,
            ),
            width=3,
        ),
        dbc.Col(
            _build_kpi_card(
                title=f"Доходы ({period_label})",
                value=period_income,
                icon="bi-arrow-down-left",
                icon_color="#27ae60",
            ),
            width=3,
        ),
        dbc.Col(
            _build_kpi_card(
                title=f"Расходы ({period_label})",
                value=period_expense,
                icon="bi-arrow-up-right",
                icon_color="#e74c3c",
            ),
            width=3,
        ),
        dbc.Col(
            _build_kpi_card(
                title="Накопления",
                value=savings_value,
                subtitle=savings_subtitle,
                icon="bi-piggy-bank",
                icon_color="#3498db",
            ),
            width=3,
        ),
    ]

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
            name="Доходы",
            marker_color="#27ae60",
            opacity=0.8,
        )
    )
    fig.add_trace(
        go.Bar(
            x=labels,
            y=expense_values,
            name="Расходы",
            marker_color="#e74c3c",
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
                    html.H5("Денежный поток", className="card-title mb-3"),
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
        colors = ["#27ae60", "#e74c3c"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Доходы", "Расходы"],
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

    period_label = "За месяц" if period == "month" else "За год"

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H6("Статистика", className="card-title mb-3"),
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
                                            "backgroundColor": "#27ae60",
                                        },
                                    ),
                                    html.Span("Доходы ", className="small"),
                                    html.Span(
                                        format_rub(metrics["period_income"]),
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
                                            "backgroundColor": "#e74c3c",
                                        },
                                    ),
                                    html.Span("Расходы ", className="small"),
                                    html.Span(
                                        format_rub(metrics["period_expense"]),
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
    period_label = "За месяц" if period == "month" else "За год"

    if not transactions:
        return dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.H5(
                                    "Недавние операции",
                                    className="card-title mb-0",
                                ),
                                dbc.Button(period_label, size="sm", color="light"),
                            ],
                            className=(
                                "d-flex justify-content-between "
                                "align-items-center mb-3"
                            ),
                        ),
                        html.P("Нет операций", className="text-muted"),
                    ]
                )
            ],
            className="shadow-sm",
        )

    transaction_rows = []
    for tx in transactions:
        # Форматирование суммы
        if tx["transaction_type"] == "income":
            amount_str = format_rub(tx["amount"], show_sign=True)
            amount_class = "table-amount positive"
        elif tx["transaction_type"] == "expense":
            amount_str = format_rub(-Decimal(str(tx["amount"])))
            amount_class = "table-amount negative"
        else:  # transfer
            amount_str = format_rub(tx["amount"])
            amount_class = "table-amount"

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
                                "Недавние операции",
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
# Daily / Yearly Cashflow Charts
# =============================================================================


def _build_daily_cashflow_chart(data: MonthlyCashflowData) -> dbc.Card:
    """Создает дневной график cashflow (Month mode).

    Grouped bars (income/expense) + линия баланса + маркер минимума.
    Dual Y-axis: левая — bars, правая — balance line.

    Args:
        data: Данные из DashboardService.get_daily_cashflow()

    Returns:
        dbc.Card с графиком Plotly
    """
    days = [d["date"].day for d in data["daily"]]
    incomes = [float(d["income"]) for d in data["daily"]]
    expenses = [float(d["expense"]) for d in data["daily"]]
    balances = [float(d["balance"]) for d in data["daily"]]

    # Customdata для hover: [income, expense, balance] formatted
    customdata = [
        [format_rub(d["income"]), format_rub(d["expense"]), format_rub(d["balance"])]
        for d in data["daily"]
    ]

    fig = go.Figure()

    # Income bars
    fig.add_trace(
        go.Bar(
            x=days,
            y=incomes,
            name="Доходы",
            marker_color="#27ae60",
            opacity=0.8,
            customdata=[c[0] for c in customdata],
            hovertemplate="Доход: %{customdata}<extra></extra>",
        )
    )

    # Expense bars
    fig.add_trace(
        go.Bar(
            x=days,
            y=expenses,
            name="Расходы",
            marker_color="#e74c3c",
            opacity=0.8,
            customdata=[c[1] for c in customdata],
            hovertemplate="Расход: %{customdata}<extra></extra>",
        )
    )

    # Balance line (secondary Y-axis)
    min_point = data["min_balance_point"]
    line_color = STATUS_COLORS.get(min_point["status"], "#27ae60")

    fig.add_trace(
        go.Scatter(
            x=days,
            y=balances,
            name="Баланс",
            mode="lines+markers",
            line=dict(color=line_color, width=2.5),
            marker=dict(size=4, color=line_color),
            yaxis="y2",
            customdata=[c[2] for c in customdata],
            hovertemplate="Баланс: %{customdata}<extra></extra>",
        )
    )

    # Min balance marker (diamond)
    min_day = min_point["date"].day
    min_bal = float(min_point["balance"])
    min_text = f"Мин: {min_day}, {format_rub(min_point['balance'])}"
    marker_color = STATUS_COLORS.get(min_point["status"], "#27ae60")

    fig.add_trace(
        go.Scatter(
            x=[min_day],
            y=[min_bal],
            mode="markers+text",
            marker=dict(
                symbol="diamond",
                size=12,
                color=marker_color,
                line=dict(width=2, color="white"),
            ),
            text=[min_text],
            textposition="top center",
            textfont=dict(size=10, color=marker_color),
            showlegend=False,
            yaxis="y2",
            hoverinfo="skip",
        )
    )

    # Today vertical dashed line
    today = data["current_date"]
    today_day = today.day
    # Проверяем что today_day в диапазоне месяца
    if days and days[0] <= today_day <= days[-1]:
        fig.add_shape(
            type="line",
            x0=today_day,
            x1=today_day,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="#3498db", width=1.5, dash="dash"),
        )

    fig.update_layout(
        barmode="group",
        height=350,
        margin=dict(l=40, r=40, t=30, b=30),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        xaxis=dict(
            tickvals=[1, 8, 15, 22, 29],
            showgrid=False,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            title=None,
        ),
        yaxis2=dict(
            overlaying="y",
            side="right",
            showgrid=False,
            title=None,
        ),
    )

    return dbc.Card(
        dbc.CardBody(
            [
                html.H5("Кассовый календарь", className="card-title mb-3"),
                dcc.Graph(
                    id="daily-cashflow-chart",
                    figure=fig,
                    config={"displayModeBar": False},
                ),
            ]
        ),
        className="shadow-sm",
    )


def _build_yearly_cashflow_chart(data: YearlyCashflowData) -> dbc.Card:
    """Создает годовой график cashflow (Year mode).

    Grouped bars (income/expense) + линия end_balance + маркер минимума.
    X-ось: месяцы (Янв..Дек). Current month highlighted.

    Args:
        data: Данные из DashboardService.get_yearly_cashflow()

    Returns:
        dbc.Card с графиком Plotly
    """
    labels = [m["label"] for m in data["monthly"]]
    incomes = [float(m["income"]) for m in data["monthly"]]
    expenses = [float(m["expense"]) for m in data["monthly"]]
    end_balances = [float(m["end_balance"]) for m in data["monthly"]]

    # Customdata для hover
    customdata = [
        [
            format_rub(m["income"]),
            format_rub(m["expense"]),
            format_rub(m["end_balance"]),
        ]
        for m in data["monthly"]
    ]

    fig = go.Figure()

    # Income bars
    fig.add_trace(
        go.Bar(
            x=labels,
            y=incomes,
            name="Доходы",
            marker_color="#27ae60",
            opacity=0.8,
            customdata=[c[0] for c in customdata],
            hovertemplate="Доход: %{customdata}<extra></extra>",
        )
    )

    # Expense bars
    fig.add_trace(
        go.Bar(
            x=labels,
            y=expenses,
            name="Расходы",
            marker_color="#e74c3c",
            opacity=0.8,
            customdata=[c[1] for c in customdata],
            hovertemplate="Расход: %{customdata}<extra></extra>",
        )
    )

    # Balance line (secondary Y-axis)
    min_point = data["min_balance_point"]
    line_color = STATUS_COLORS.get(min_point["status"], "#27ae60")

    fig.add_trace(
        go.Scatter(
            x=labels,
            y=end_balances,
            name="Баланс",
            mode="lines+markers",
            line=dict(color=line_color, width=2.5),
            marker=dict(size=5, color=line_color),
            yaxis="y2",
            customdata=[c[2] for c in customdata],
            hovertemplate="Баланс: %{customdata}<extra></extra>",
        )
    )

    # Min balance marker (diamond)
    min_month = min_point["date"].month
    min_label = MONTH_NAMES_RU_SHORT.get(min_month, "")
    min_bal = float(min_point["balance"])
    min_text = f"Мин: {min_label}, {format_rub(min_point['balance'])}"
    marker_color = STATUS_COLORS.get(min_point["status"], "#27ae60")

    fig.add_trace(
        go.Scatter(
            x=[min_label],
            y=[min_bal],
            mode="markers+text",
            marker=dict(
                symbol="diamond",
                size=12,
                color=marker_color,
                line=dict(width=2, color="white"),
            ),
            text=[min_text],
            textposition="top center",
            textfont=dict(size=10, color=marker_color),
            showlegend=False,
            yaxis="y2",
            hoverinfo="skip",
        )
    )

    # Current month highlight
    current_month = data["current_date"].month
    current_label = MONTH_NAMES_RU_SHORT.get(current_month, "")
    if current_label in labels:
        idx = labels.index(current_label)
        fig.add_shape(
            type="rect",
            x0=idx - 0.5,
            x1=idx + 0.5,
            y0=0,
            y1=1,
            yref="paper",
            fillcolor="rgba(52,152,219,0.08)",
            line=dict(width=0),
            layer="below",
        )

    year = data["year"]

    fig.update_layout(
        barmode="group",
        height=350,
        margin=dict(l=40, r=40, t=30, b=30),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        xaxis=dict(showgrid=False),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            title=None,
        ),
        yaxis2=dict(
            overlaying="y",
            side="right",
            showgrid=False,
            title=None,
        ),
    )

    return dbc.Card(
        dbc.CardBody(
            [
                html.H5(
                    f"Кассовый календарь — {year}",
                    className="card-title mb-3",
                ),
                dcc.Graph(
                    id="daily-cashflow-chart",
                    figure=fig,
                    config={"displayModeBar": False},
                ),
            ]
        ),
        className="shadow-sm",
    )


def _load_dashboard_components(
    period: str,
    period_state: dict | None,
) -> tuple:
    """Единая точка загрузки данных и построения UI.

    Используется и в load_dashboard_data, и в refresh_dashboard_after_crud.

    Args:
        period: "month" или "year"
        period_state: Данные из dcc.Store (year, month)

    Returns:
        Tuple: (cards, chart, stats, transactions)
    """
    today = date.today()
    year = today.year
    month = today.month
    if period_state:
        year = period_state.get("year", today.year)
        month = period_state.get("month", today.month)

    with get_db_session() as session:
        service = DashboardService(session)

        # Метрики для KPI
        metrics = service.get_overview_metrics(
            user_id=DEFAULT_USER_ID,
            period=period,
        )

        # Дневной или годовой cashflow
        if period == "month":
            daily_data = service.get_daily_cashflow(
                user_id=DEFAULT_USER_ID,
                year=year,
                month=month,
            )
            chart = _build_daily_cashflow_chart(daily_data)
        else:
            yearly_data = service.get_yearly_cashflow(
                user_id=DEFAULT_USER_ID,
                year=year,
            )
            chart = _build_yearly_cashflow_chart(yearly_data)

        recent_transactions = service.get_recent_transactions(
            user_id=DEFAULT_USER_ID,
            limit=5,
        )

    cards = build_overview_cards(metrics, period)
    stats = build_statistics_card(metrics, period)
    transactions = build_recent_transactions_card(recent_transactions, period)

    return cards, chart, stats, transactions


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
    """Загружает данные дашборда при навигации или смене периода."""
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
        return _load_dashboard_components(period, period_state)
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
    """Обновляет состояние периода в dcc.Store."""
    if not period_value:
        raise PreventUpdate

    today = date.today()
    return {"period": period_value, "year": today.year, "month": today.month}


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
    """Обновляет дашборд после CRUD операции с транзакцией."""
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
        result = _load_dashboard_components(period, period_state)
        source = trigger.get("source", "unknown")
        action = trigger.get("action", "unknown")
        logger.debug(f"Dashboard обновлен после {action} из {source}")
        return result
    except Exception as e:
        logger.error(f"Ошибка обновления дашборда после CRUD: {e}")
        raise PreventUpdate


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
    """Открывает модал создания операции при клике на столбец графика.

    Работает только в Month mode. Передает дату клика через preselected-date.
    """
    # Guard #1: нет клика
    if click_data is None:
        raise PreventUpdate

    # Guard #2: только для month mode
    if not period_state or period_state.get("period") != "month":
        raise PreventUpdate

    try:
        point = click_data["points"][0]
        day = int(point["x"])
        year = period_state.get("year", date.today().year)
        month = period_state.get("month", date.today().month)
        clicked_date = date(year, month, day)
        return True, clicked_date.isoformat(), "chart"
    except (KeyError, IndexError, ValueError):
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
