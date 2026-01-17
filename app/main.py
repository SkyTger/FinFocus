"""
Главное приложение FinFocus - планировщик бюджета.
"""
import os
from dotenv import load_dotenv

import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc

from app.components.dashboard import create_dashboard_layout
from app.components.sidebar import create_sidebar
from app.components.transactions import create_transactions_layout

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
                        # Контент страницы
                        html.Div(id="page-content"),
                    ],
                    width=9,
                    style={"margin-left": "25%"},
                ),  # Отступ для sidebar
            ],
            className="g-0",
        ),  # Убираем отступы между колонками
    ],
    fluid=True,
    className="p-0",
)


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
        # Кассовый календарь (пока заглушка)
        return html.Div(
            [
                html.H2("Кассовый календарь"),
                html.P("Здесь будет календарь с операциями и остатками"),
            ]
        ), create_page_header("Календарь", "Кассовый календарь")

    elif pathname == "/goals":
        # Накопительные цели (пока заглушка)
        return html.Div(
            [html.H2("Накопительные цели"), html.P("Здесь будут цели накоплений")]
        ), create_page_header("Цели", "Накопительные цели")

    elif pathname == "/transactions":
        # Страница операций
        return create_transactions_layout(), create_page_header(
            "Операции", "Управление доходами и расходами"
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


if __name__ == "__main__":
    # Настройки для разработки
    debug = os.getenv("DEBUG", "True").lower() == "true"
    port = int(os.getenv("PORT", 8050))

    app.run_server(debug=debug, port=port, host="0.0.0.0")  # Доступ извне (для Docker)
