"""
Главное приложение FinFocus - планировщик бюджета.
"""
from dotenv import load_dotenv

import dash
import time
from dash import dcc, html, Input, Output, State, callback
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from app.components.dashboard import create_dashboard_layout
from app.components.sidebar import create_sidebar
from app.components.transactions import (
    create_transactions_layout,
)  # Сначала transactions
from app.components.calendar import (
    create_calendar_layout,
    create_reconciliation_modal,
)  # Потом calendar
from app.components.goals import create_goals_layout  # Потом goals
from app.components.transaction_modals import create_transaction_modals
from app.components.analytics import create_analytics_layout  # Аналитика
from app.components.onboarding_wizard import create_onboarding_wizard
from app.components.wishlist import create_wishlist_modal

# Загружаем переменные окружения
load_dotenv()

# Создаем Dash приложение
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,  # Bootstrap тема
        dbc.icons.BOOTSTRAP,  # Bootstrap иконки
    ],
    suppress_callback_exceptions=True,  # Для мультистраничного приложения
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

# Настройки приложения
app.title = "FinFocus - Планировщик бюджета"
server = app.server  # Для деплоя

# Основной layout приложения
app.layout = dbc.Container(
    [
        # URL компонент для роутинга
        dcc.Location(id="url", refresh=False),
        # Главная структура с sidebar
        dbc.Row(
            [
                # Sidebar (левая панель навигации)
                dbc.Col(
                    create_sidebar(),
                    width=3,
                    className="bg-light vh-100 p-0",
                    style={"position": "fixed", "left": 0, "top": 0, "height": "100vh"},
                ),
                # Основной контент
                dbc.Col(
                    [
                        # Заголовок страницы
                        html.Div(id="page-header", className="mb-4"),
                        # Глобальный Alert для ошибок транзакций
                        dbc.Alert(
                            id="transaction-error-alert",
                            is_open=False,
                            color="danger",
                            dismissable=True,
                            duration=5000,
                            className="mb-3",
                        ),
                        # Контент страницы
                        html.Div(id="page-content"),
                    ],
                    width=9,
                    style={"margin-left": "25%"},
                ),  # Отступ для sidebar
            ],
            className="g-0",
        ),  # Убираем отступы между колонками
        # Глобальные модалы транзакций (доступны на всех страницах)
        create_transaction_modals(),
        # Wishlist модал (отложенные покупки)
        create_wishlist_modal(),
        # Reconciliation модал (глобальный — доступен с Calendar и Dashboard)
        create_reconciliation_modal(),
        # Onboarding wizard (blocking modal при first_launch)
        create_onboarding_wizard(),
        # Глобальный store для toast dismissal (до перезагрузки)
        dcc.Store(id="balance-toast-dismissed", data=False),
        # Trigger для автооткрытия reconciliation modal (timestamp-based)
        dcc.Store(id="open-recon-trigger", data=None),
        # Wishlist: ID активного элемента для планирования в календаре
        dcc.Store(id="wishlist-active-item", data=None),
    ],
    fluid=True,
    className="p-0",
)


# Единый callback для обработки query params (?open_recon=1, ?wishlist_item=ID)
@callback(
    [
        Output("open-recon-trigger", "data"),
        Output("wishlist-active-item", "data"),
        Output("url", "search"),
    ],
    Input("url", "search"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def handle_calendar_query_params(url_search: str | None, pathname: str | None):
    """Обрабатывает query params и устанавливает triggers.

    - ?open_recon=1 → open-recon-trigger (timestamp)
    - ?wishlist_item=ID → wishlist-active-item (int)
    Очищает url.search после обработки.
    """
    if not url_search:
        raise PreventUpdate

    from urllib.parse import parse_qs

    params = parse_qs(url_search.lstrip("?"))
    recon_trigger = None
    wishlist_item = None

    if pathname == "/calendar":
        if "open_recon" in params:
            recon_trigger = int(time.time() * 1000)

        if "wishlist_item" in params:
            try:
                wishlist_item = int(params["wishlist_item"][0])
            except (ValueError, IndexError):
                pass

    if recon_trigger is None and wishlist_item is None:
        raise PreventUpdate

    return recon_trigger, wishlist_item, ""


# Callback для роутинга страниц
@callback(
    [Output("page-content", "children"), Output("page-header", "children")],
    [Input("url", "pathname")],
)
def display_page(pathname):
    """
    Роутинг между страницами приложения.
    """
    if pathname is None or pathname == "/" or pathname == "/dashboard":
        # Главная страница - дашборд
        return create_dashboard_layout(), create_page_header(
            "Дашборд", "Обзор финансов"
        )

    elif pathname == "/calendar":
        # Кассовый календарь
        return create_calendar_layout(), create_page_header(
            "Календарь", "Кассовый календарь"
        )

    elif pathname == "/goals":
        # Накопительные цели
        return create_goals_layout(), create_page_header("Цели", "Накопительные цели")

    elif pathname == "/transactions":
        # Страница операций
        return create_transactions_layout(), create_page_header(
            "Операции", "Управление доходами и расходами"
        )

    elif pathname == "/analytics":
        # Страница аналитики
        return create_analytics_layout(), create_page_header(
            "Аналитика", "Анализ расходов по категориям"
        )

    else:
        # 404 страница
        return html.Div(
            [
                html.H1("404", className="display-1 text-muted"),
                html.P("Страница не найдена"),
                dbc.Button("На главную", href="/", color="primary"),
            ],
            className="text-center mt-5",
        ), create_page_header("Ошибка", "Страница не найдена")


def create_page_header(title: str, subtitle: str = ""):
    """Создает заголовок страницы."""
    return html.Div(
        [
            html.H1(title, className="h2 mb-0"),
            html.P(subtitle, className="text-muted") if subtitle else None,
            html.Hr(),
        ]
    )
