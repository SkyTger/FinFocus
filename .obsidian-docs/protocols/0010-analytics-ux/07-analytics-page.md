# Шаг 7: Analytics Page

## Briefing
- **Цель:** Создать новую страницу /analytics с визуализацией расходов: donut chart структуры и bar chart динамики.
- **Ключевые файлы:**
  - `app/components/analytics.py` (создать) — layout и callbacks
  - `app/components/__init__.py` (модифицировать) — экспорт
  - `app/components/sidebar.py` (модифицировать) — добавить nav item
  - `app/main.py` (модифицировать) — роутинг
  - `app/assets/analytics.css` (создать) — стили
- **Additional info:**
  - Namespace class: `.analytics-page`
  - Переключатель периода: Месяц/Квартал/Год (RadioItems)
  - Переключатель bar mode: Stacked/Grouped (Switch)
  - Summary cards: Всего расходов, Категорий, Без категории, Топ категория
  - global-transaction-trigger для обновления после CRUD

## Sub-tasks

### 1. Создать файл analytics.py

**Файл:** `app/components/analytics.py`

```python
"""Страница аналитики расходов."""
from datetime import date, timedelta
from decimal import Decimal

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import callback, ctx, dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate

from app.core.database import get_db_session
from app.services.analytics_service import AnalyticsService


# Русские названия месяцев
MONTH_LABELS_RU = [
    "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
    "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"
]

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
        className="analytics-page p-4",
        children=[
            # Header
            html.H2("Аналитика расходов", className="mb-4"),

            # Period switcher
            html.Div([
                dbc.RadioItems(
                    id="analytics-period-switcher",
                    options=[
                        {"label": "Месяц", "value": "month"},
                        {"label": "Квартал", "value": "quarter"},
                        {"label": "Год", "value": "year"},
                    ],
                    value="month",
                    inline=True,
                    className="mb-3",
                ),
            ]),

            # Stores
            dcc.Store(id="analytics-period-store", data={"type": "month"}),
            dcc.Store(id="analytics-bar-mode-store", data="stack"),

            # Summary cards row
            dbc.Row(id="summary-cards-row", className="mb-4"),

            # Charts row
            dbc.Row([
                # Donut chart
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Структура расходов"),
                        dbc.CardBody([
                            dcc.Graph(
                                id="expenses-donut-chart",
                                config={"displayModeBar": False},
                            ),
                        ]),
                    ]),
                ], md=5),

                # Bar chart
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            "Динамика расходов",
                            dbc.Switch(
                                id="bar-mode-switch",
                                label="Grouped",
                                value=False,
                                className="float-end",
                            ),
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                id="expenses-bar-chart",
                                config={"displayModeBar": False},
                            ),
                        ]),
                    ]),
                ], md=7),
            ]),
        ],
    )


def _build_donut_chart(data: list) -> go.Figure:
    """Построение donut chart."""
    if not data:
        # Empty state
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(
            showlegend=False,
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
        )
        return fig

    labels = [d["category_name"] for d in data]
    values = [float(d["total"]) for d in data]
    colors = CATEGORY_COLORS[: len(data)]

    # "Прочее" и "Без категории" серым
    for i, d in enumerate(data):
        if d["category_name"] in ("Прочее", "Без категории"):
            colors[i] = "#9E9E9E"

    fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker=dict(colors=colors),
            textinfo="percent",
            textposition="outside",
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} ₽<br>%{percent}<extra></extra>",
        )
    ])

    # Center text with total
    total = sum(values)
    fig.add_annotation(
        text=f"<b>{total:,.0f}</b><br>₽",
        x=0.5, y=0.5,
        font=dict(size=14),
        showarrow=False,
    )

    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        margin=dict(l=20, r=20, t=20, b=60),
        height=350,
    )

    return fig


def _build_bar_chart(data: list, barmode: str = "stack") -> go.Figure:
    """Построение bar chart динамики."""
    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(
            showlegend=False,
            margin=dict(l=40, r=20, t=20, b=40),
            height=350,
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

        traces.append(go.Bar(
            name=cat_name,
            x=[d["month_label"] for d in data],
            y=y_values,
            marker_color=color,
            hovertemplate=f"<b>{cat_name}</b><br>" + "%{y:,.0f} ₽<extra></extra>",
        ))

    fig = go.Figure(data=traces)

    fig.update_layout(
        barmode=barmode,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        margin=dict(l=40, r=20, t=20, b=80),
        height=350,
        yaxis=dict(tickformat=","),
    )

    return fig


def _build_summary_cards(data: list, uncategorized_count: int) -> list:
    """Построение карточек с метриками."""
    total = sum(float(d["total"]) for d in data) if data else 0
    categories_count = len([d for d in data if d["category_name"] not in ("Прочее", "Без категории")])
    top_category = data[0]["category_name"] if data else "—"
    top_percentage = f"{data[0]['percentage']:.0f}%" if data else "—"

    cards = [
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Всего расходов", className="text-muted"),
                html.H4(f"{total:,.0f} ₽"),
            ]),
        ]), md=3),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Категорий", className="text-muted"),
                html.H4(str(categories_count)),
            ]),
        ]), md=3),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Без категории", className="text-muted"),
                html.H4([
                    str(uncategorized_count),
                    dbc.Badge(
                        "!",
                        color="warning",
                        className="ms-2",
                    ) if uncategorized_count > 0 else None,
                ]),
            ]),
        ]), md=3),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Топ категория", className="text-muted"),
                html.H4(f"{top_category} ({top_percentage})"),
            ]),
        ]), md=3),
    ]

    return cards


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
    """Загрузка данных аналитики."""
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
```

### 2. Обновить экспорты

**Файл:** `app/components/__init__.py`

Добавить:
```python
from app.components.analytics import create_analytics_layout
```

И в `__all__` добавить `"create_analytics_layout"`.

### 3. Добавить nav item в sidebar

**Файл:** `app/components/sidebar.py`

Найти список nav items и добавить "Аналитика" после "Операции":

```python
dbc.NavLink(
    [html.I(className="bi bi-bar-chart me-2"), "Аналитика"],
    href="/analytics",
    active="exact",
),
```

### 4. Добавить роутинг

**Файл:** `app/main.py`

В функции `display_page()` добавить case:

```python
elif pathname == "/analytics":
    return create_analytics_layout()
```

И добавить импорт:
```python
from app.components.analytics import create_analytics_layout
```

### 5. Создать CSS стили

**Файл:** `app/assets/analytics.css`

```css
/* === Analytics Page Namespace === */
.analytics-page {
    max-width: 1400px;
    margin: 0 auto;
}

.analytics-page .card {
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.analytics-page .card-header {
    background-color: #f8f9fa;
    font-weight: 600;
}

/* Summary cards */
.analytics-page .card-body h4 {
    font-weight: 700;
    color: #2E7D32;
}

.analytics-page .card-body h6 {
    font-size: 0.85rem;
}

/* Charts container */
.analytics-page .donut-container,
.analytics-page .bar-container {
    min-height: 350px;
}

/* Period switcher */
.analytics-page .form-check-inline {
    margin-right: 1rem;
}

/* Responsive */
@media (max-width: 768px) {
    .analytics-page .row {
        flex-direction: column;
    }

    .analytics-page .col-md-3,
    .analytics-page .col-md-5,
    .analytics-page .col-md-7 {
        width: 100%;
        margin-bottom: 1rem;
    }
}
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи.

2.  **Базовая проверка:**
    ```bash
    source .venv/bin/activate
    python -m py_compile app/components/analytics.py app/main.py app/components/sidebar.py
    ```

3.  **Фиксация:**
    - **Добавь запись в `log.md`**
    - **Обнови `context.md`**: Current Step = 8
    - Проверь ветку main

4.  **Сделай коммит:**
    ```bash
    git add app/components/analytics.py app/components/__init__.py app/components/sidebar.py app/main.py app/assets/analytics.css .protocols/
    git commit -m "feat(analytics): add /analytics page with donut and bar charts [protocol-0010/07]"
    git push
    ```

5.  **Отчет пользователю** в установленном формате.
