"""
Dashboard компонент - главная страница с обзором финансов.
"""
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
from dash import html, dcc


def create_dashboard_layout():
    """Создает layout главной страницы дашборда."""

    return html.Div([
        # Верхние карточки с основными показателями
        create_overview_cards(),

        # Строка с графиками
        dbc.Row([
            # Левая колонка - график Cash Flow
            dbc.Col([
                create_cashflow_chart()
            ], width=8),

            # Правая колонка - AI Assistant и статистика
            dbc.Col([
                create_ai_assistant_card(),
                html.Div(style={"height": "20px"}),  # Отступ
                create_statistics_card()
            ], width=4)
        ], className="mb-4"),

        # Нижняя строка
        dbc.Row([
            # Последние операции
            dbc.Col([
                create_recent_transactions_card()
            ], width=8),

            # Обменные курсы (заглушка как в макете)
            dbc.Col([
                create_exchange_card()
            ], width=4)
        ])
    ])


def create_overview_cards():
    """Создает верхние карточки с основными показателями."""

    # Пока используем тестовые данные
    cards_data = [
        {
            "title": "Total Balance",
            "value": "$20,670",
            "subtitle": "USD",
            "color": "success",
            "gradient": True,
            "actions": [
                {"label": "Deposit", "icon": "bi-plus"},
                {"label": "Send", "icon": "bi-arrow-up-right"}
            ]
        },
        {
            "title": "Income",
            "value": "$14,480.24",
            "color": "light",
            "icon": "bi-arrow-down-left",
            "icon_color": "success"
        },
        {
            "title": "Expense",
            "value": "$14,480.24",
            "color": "light",
            "icon": "bi-arrow-up-right",
            "icon_color": "danger"
        },
        {
            "title": "Savings",
            "value": "$14,480.24",
            "color": "light",
            "icon": "bi-piggy-bank",
            "icon_color": "primary"
        }
    ]

    cards = []
    for card_data in cards_data:
        card = create_metric_card(card_data)
        cards.append(dbc.Col(card, width=3))

    return dbc.Row(cards, className="mb-4")


def create_metric_card(data):
    """Создает карточку с метрикой."""

    # Стиль карточки
    card_style = {}
    if data.get("gradient"):
        card_style = {
            "background": "linear-gradient(135deg, #28a745 0%, #20c997 100%)",
            "color": "white"
        }

    # Действия (кнопки)
    actions = []
    if data.get("actions"):
        for action in data["actions"]:
            btn = dbc.Button([
                html.I(className=f"bi {action['icon']} me-1"),
                action["label"]
            ],
                size="sm",
                color="light" if data.get("gradient") else "primary",
                outline=not data.get("gradient"),
                className="me-2"
            )
            actions.append(btn)

    # Иконка
    icon = None
    if data.get("icon"):
        icon = html.Div([
            html.I(className=f"bi {data['icon']}",
                   style={"fontSize": "1.5rem", "color": f"var(--bs-{data.get('icon_color', 'primary')})"}
                   )
        ], className="mb-2")

    card_content = [
        icon,
        html.H6(data["title"], className="card-subtitle mb-2"),
        html.H3(data["value"], className="card-title mb-1"),
        html.Small(data.get("subtitle", ""), className="text-muted") if data.get("subtitle") else None,
        html.Div(actions, className="mt-3") if actions else None
    ]

    return dbc.Card([
        dbc.CardBody(card_content)
    ],
        color=data.get("color", "white"),
        style=card_style,
        className="h-100 shadow-sm"
    )


def create_cashflow_chart():
    """Создает график денежного потока."""

    # Тестовые данные (как в макете)
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    income_data = [4000, 5000, 4500, 6000, 5500, 7000, 6500, 7500, 6000, 8000, 7000, 8500]
    expense_data = [3000, 3500, 3200, 4000, 3800, 4500, 4200, 5000, 4500, 5500, 5000, 6000]

    fig = go.Figure()

    # Доходы
    fig.add_trace(go.Bar(
        x=months,
        y=income_data,
        name='Income',
        marker_color='#28a745',
        opacity=0.8
    ))

    # Расходы
    fig.add_trace(go.Bar(
        x=months,
        y=expense_data,
        name='Expense',
        marker_color='#17a2b8',
        opacity=0.8
    ))

    fig.update_layout(
        title="Cashflow",
        title_font_size=16,
        barmode='group',
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='#f0f0f0')

    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.H5("Cashflow", className="card-title"),
                html.Div([
                    dbc.Button("This Year", size="sm", color="light", className="me-2"),
                    dbc.DropdownMenu([
                        dbc.DropdownMenuItem("2024"),
                        dbc.DropdownMenuItem("2023"),
                    ], label="2024", size="sm", color="light")
                ])
            ], className="d-flex justify-content-between align-items-center mb-3"),

            dcc.Graph(figure=fig, config={'displayModeBar': False})
        ])
    ], className="shadow-sm")


def create_ai_assistant_card():
    """Создает карточку AI помощника."""

    return dbc.Card([
        dbc.CardBody([
            html.H6("AI Assistant", className="card-title mb-3"),
            html.Div([
                html.I(className="bi bi-robot", style={"fontSize": "3rem", "color": "#28a745"}),
            ], className="text-center mb-3"),
            html.P("What Can I help with?", className="text-center text-muted mb-3"),
            dbc.Button([
                html.I(className="bi bi-chat-dots me-2"),
                "Ask anything"
            ], color="success", size="sm", className="w-100")
        ])
    ], className="shadow-sm")


def create_statistics_card():
    """Создает карточку со статистикой."""

    # Создаем простой пончик
    fig = go.Figure(data=[go.Pie(
        labels=['Income', 'Expense'],
        values=[54800, 53000],
        hole=.6,
        marker_colors=['#28a745', '#17a2b8'],
        showlegend=False
    )])

    fig.update_layout(
        height=150,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='white'
    )

    return dbc.Card([
        dbc.CardBody([
            html.H6("Statistic", className="card-title mb-3"),
            html.Div([
                html.Div("This Month", className="small text-muted mb-2"),
                dcc.Graph(figure=fig, config={'displayModeBar': False}),
                html.Div([
                    html.Div([
                        html.Span("Income ", className="small"),
                        html.Span("$54800", className="fw-bold")
                    ]),
                    html.Div([
                        html.Span("Expense ", className="small"),
                        html.Span("$53000", className="fw-bold")
                    ])
                ])
            ])
        ])
    ], className="shadow-sm")


def create_recent_transactions_card():
    """Создает карточку с последними операциями."""

    # Тестовые данные
    transactions = [
        {"desc": "Dividend Payout", "category": "Investment", "date": "2024-09-25", "amount": "+$200.00",
         "status": "Completed"},
        {"desc": "Grocery Shopping", "category": "Food & Drink", "date": "2024-09-24", "amount":
            "-$84.32", "status": "Completed"},
        {"desc": "Freelance Payment", "category": "Investment", "date": "2024-09-23", "amount":
            "+$500.00", "status": "Completed"},
    ]

    transaction_rows = []
    for tx in transactions:
        row = html.Tr([
            html.Td([
                html.Div(tx["desc"], className="fw-semibold"),
                html.Div(tx["category"], className="small text-muted")
            ]),
            html.Td(tx["date"], className="text-muted"),
            html.Td(tx["amount"], className="fw-bold text-success" if tx["amount"].startswith("+") else
            "fw-bold text-danger"),
            html.Td([
                dbc.Badge(tx["status"], color="success", className="rounded-pill")
            ])
        ])
        transaction_rows.append(row)

    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.H5("Recent Transactions", className="card-title"),
                dbc.Button("This Month", size="sm", color="light")
            ], className="d-flex justify-content-between align-items-center mb-3"),

            dbc.Table([
                html.Tbody(transaction_rows)
            ], borderless=True, hover=True)
        ])
    ], className="shadow-sm")


def create_exchange_card():
    """Создает карточку с курсами валют."""

    return dbc.Card([
        dbc.CardBody([
            html.H6("Exchange", className="card-title mb-3"),
            html.Div([
                html.Div([
                    html.Span("USD", className="fw-bold"),
                    html.Span(" ⇄ ", className="mx-2"),
                    html.Span("RUB", className="fw-bold")
                ], className="text-center mb-3"),
                html.Hr(),
                html.Div([
                    html.Div("$100.00", className="h5 mb-0"),
                    html.Div("₽9200.00", className="text-muted")
                ], className="text-center mb-3"),
                dbc.Button("Exchange", color="success", size="sm", className="w-100")
            ])
        ])
    ], className="shadow-sm")