"""Страница аналитики расходов."""
from datetime import date

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import callback, dcc, html, Input, Output
from dash.exceptions import PreventUpdate

from app.core.database import get_db_session
from app.services.analytics_service import AnalyticsService
from app.utils.formatters import format_rub


# Цветовая палитра для категорий
CATEGORY_COLORS = [
    "#2E7D32",  # green
    "#1565C0",  # blue
    "#EF6C00",  # orange
    "#C62828",  # red
    "#6A1B9A",  # purple
    "#00838F",  # teal
    "#AD1457",  # pink
    "#4527A0",  # deep purple
    "#00695C",  # dark teal
    "#F9A825",  # amber
]


def create_analytics_layout():
    """Создание layout страницы аналитики."""
    return html.Div(
        className="an-page",
        children=[
            # Stores
            dcc.Store(id="analytics-period-store", data={"type": "month"}),
            dcc.Store(id="analytics-bar-mode-store", data="stack"),
            # Glass header — title + period switcher
            html.Div(
                [
                    html.Div(
                        [
                            html.H4(
                                "Аналитика расходов",
                                className="mb-0 fw-semibold",
                            ),
                        ],
                        className="flex-grow-1",
                    ),
                    dbc.RadioItems(
                        id="analytics-period-switcher",
                        options=[
                            {"label": "Месяц", "value": "month"},
                            {"label": "Квартал", "value": "quarter"},
                            {"label": "Год", "value": "year"},
                        ],
                        value="month",
                        inline=True,
                        className="an-period-switcher",
                    ),
                ],
                className="an-glass-header",
            ),
            # Summary cards row
            html.Div(id="summary-cards-row", className="an-summary-row"),
            # Charts row
            dbc.Row(
                [
                    # Donut chart
                    dbc.Col(
                        html.Div(
                            [
                                html.Span(
                                    "СТРУКТУРА РАСХОДОВ",
                                    className="an-card-label",
                                ),
                                dcc.Graph(
                                    id="expenses-donut-chart",
                                    config={"displayModeBar": False},
                                ),
                            ],
                            className="an-chart-card",
                        ),
                        md=5,
                    ),
                    # Bar chart
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            "ДИНАМИКА РАСХОДОВ",
                                            className="an-card-label",
                                        ),
                                        dbc.Switch(
                                            id="bar-mode-switch",
                                            label="Grouped",
                                            value=False,
                                            className="an-bar-switch",
                                        ),
                                    ],
                                    className=(
                                        "d-flex justify-content-between"
                                        " align-items-center"
                                    ),
                                ),
                                dcc.Graph(
                                    id="expenses-bar-chart",
                                    config={"displayModeBar": False},
                                ),
                            ],
                            className="an-chart-card",
                        ),
                        md=7,
                    ),
                ],
                className="g-3",
            ),
        ],
    )


def _build_donut_chart(data: list) -> go.Figure:
    """Построение donut chart структуры расходов.

    Args:
        data: Список CategorySummary с данными по категориям.

    Returns:
        go.Figure: Plotly figure для dcc.Graph.
    """
    if not data:
        # Empty state
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(
            showlegend=False,
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    labels = [d["category_name"] for d in data]
    values = [float(d["total"]) for d in data]
    colors = CATEGORY_COLORS[: len(data)]

    # "Прочее" и "Без категории" серым
    for i, d in enumerate(data):
        if d["category_name"] in ("Прочее", "Без категории"):
            colors[i] = "#9E9E9E"

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                marker=dict(colors=colors),
                textinfo="percent",
                textposition="outside",
                hovertemplate=(
                    "<b>%{label}</b><br>%{value:,.0f} ₽<br>%{percent}<extra></extra>"
                ),
            )
        ]
    )

    # Center text with total
    total = sum(values)
    fig.add_annotation(
        text=f"<b>{format_rub(total)}</b>",
        x=0.5,
        y=0.5,
        font=dict(size=14),
        showarrow=False,
    )

    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        margin=dict(l=20, r=20, t=20, b=60),
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def _build_bar_chart(data: list, barmode: str = "stack") -> go.Figure:
    """Построение bar chart динамики расходов по месяцам.

    Args:
        data: Список MonthlyTrend с данными по месяцам.
        barmode: Режим отображения баров ('stack' или 'group').

    Returns:
        go.Figure: Plotly figure для dcc.Graph.
    """
    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(
            showlegend=False,
            margin=dict(l=40, r=20, t=20, b=40),
            height=350,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    # Собираем все уникальные категории
    all_categories = {}
    for month_data in data:
        for cat in month_data.get("categories", []):
            cat_name = cat["category_name"]
            if cat_name not in all_categories:
                all_categories[cat_name] = len(all_categories)

    # Создаем traces для каждой категории
    traces = []
    for cat_name, idx in all_categories.items():
        y_values = []
        for month_data in data:
            cat_total = 0
            for cat in month_data.get("categories", []):
                if cat["category_name"] == cat_name:
                    cat_total = float(cat["total"])
                    break
            y_values.append(cat_total)

        color = CATEGORY_COLORS[idx % len(CATEGORY_COLORS)]
        if cat_name in ("Прочее", "Без категории"):
            color = "#9E9E9E"

        traces.append(
            go.Bar(
                name=cat_name,
                x=[d["month_label"] for d in data],
                y=y_values,
                marker_color=color,
                hovertemplate=f"<b>{cat_name}</b><br>" + "%{y:,.0f} ₽<extra></extra>",
            )
        )

    fig = go.Figure(data=traces)

    fig.update_layout(
        barmode=barmode,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        margin=dict(l=40, r=20, t=20, b=80),
        height=350,
        yaxis=dict(tickformat=",", gridcolor="rgba(0,0,0,0.06)"),
        xaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def _build_summary_cards(data: list, uncategorized_count: int) -> list:
    """Построение карточек с метриками.

    Args:
        data: Список CategorySummary для расчета метрик.
        uncategorized_count: Количество некатегоризированных транзакций.

    Returns:
        list: Список dbc.Col с карточками.
    """
    total = sum(float(d["total"]) for d in data) if data else 0
    categories_count = len(
        [d for d in data if d["category_name"] not in ("Прочее", "Без категории")]
    )
    top_category = data[0]["category_name"] if data else "—"
    top_percentage = f"{data[0]['percentage']:.0f}%" if data else "—"

    cards = [
        _summary_card("Всего расходов", format_rub(total)),
        _summary_card("Категорий", str(categories_count)),
        _summary_card(
            "Без категории",
            str(uncategorized_count),
            badge="!" if uncategorized_count > 0 else None,
        ),
        _summary_card("Топ категория", f"{top_category} ({top_percentage})"),
    ]

    return cards


def _summary_card(label: str, value: str, badge: str | None = None) -> html.Div:
    """Создает компактную glass-карточку метрики."""
    value_children: list = [html.Span(value, className="an-metric-value")]
    if badge:
        value_children.append(dbc.Badge(badge, color="warning", className="ms-2"))

    return html.Div(
        [
            html.Span(label, className="an-metric-label"),
            html.Div(value_children),
        ],
        className="an-metric-card",
    )


# === CALLBACKS ===


@callback(
    Output("analytics-period-store", "data"),
    Input("analytics-period-switcher", "value"),
)
def update_period_store(period_type):
    """Обновление store с типом периода."""
    return {"type": period_type}


@callback(
    Output("analytics-bar-mode-store", "data"),
    Input("bar-mode-switch", "value"),
)
def update_bar_mode_store(is_grouped):
    """Обновление store с режимом bar chart."""
    return "group" if is_grouped else "stack"


@callback(
    Output("summary-cards-row", "children"),
    Output("expenses-donut-chart", "figure"),
    Output("expenses-bar-chart", "figure"),
    Input("analytics-period-store", "data"),
    Input("analytics-bar-mode-store", "data"),
    Input("global-transaction-trigger", "data"),
    Input("url", "pathname"),
)
def load_analytics_data(period_data, bar_mode, trigger, pathname):
    """Загрузка данных аналитики.

    Обновляет summary cards, donut chart и bar chart при:
    - Изменении периода
    - Изменении режима bar chart
    - CRUD операциях с транзакциями (global-transaction-trigger)
    - Переходе на страницу /analytics
    """
    if pathname != "/analytics":
        raise PreventUpdate

    period_type = period_data.get("type", "month") if period_data else "month"

    # Определяем период
    today = date.today()
    if period_type == "month":
        start_date = today.replace(day=1)
        end_date = today
        months_count = 6
    elif period_type == "quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=quarter_start_month, day=1)
        end_date = today
        months_count = 6
    else:  # year
        start_date = today.replace(month=1, day=1)
        end_date = today
        months_count = 12

    with get_db_session() as session:
        service = AnalyticsService(session)

        # Donut data
        donut_data = service.get_expenses_by_category(
            user_id=1,
            start_date=start_date,
            end_date=end_date,
            group_small=True,
        )

        # Bar data
        bar_data = service.get_monthly_trends(
            user_id=1,
            months=months_count,
        )

        # Uncategorized count
        uncategorized = service.get_uncategorized_count(user_id=1)

    # Build components
    cards = _build_summary_cards(donut_data, uncategorized)
    donut_fig = _build_donut_chart(donut_data)
    bar_fig = _build_bar_chart(bar_data, bar_mode or "stack")

    return cards, donut_fig, bar_fig
