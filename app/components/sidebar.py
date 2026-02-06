"""
Sidebar компонент - боковое меню навигации.
"""
import dash_bootstrap_components as dbc
from dash import html, callback, Input, Output


# Определения пунктов меню
MAIN_NAV_ITEMS = [
    {"label": "Дашборд", "icon": "bi-speedometer2", "href": "/dashboard"},
    {"label": "Календарь", "icon": "bi-calendar3", "href": "/calendar"},
    {"label": "Операции", "icon": "bi-list-ul", "href": "/transactions"},
    {"label": "Аналитика", "icon": "bi-bar-chart", "href": "/analytics"},
    {"label": "Цели", "icon": "bi-target", "href": "/goals"},
]

ADDITIONAL_NAV_ITEMS = [
    {"label": "Настройки", "icon": "bi-gear", "href": "/settings"},
    {"label": "Справка", "icon": "bi-question-circle", "href": "/help"},
]


def _build_nav_links(active_pathname: str = "/dashboard") -> list:
    """Создает список NavLink с active highlight.

    Args:
        active_pathname: Текущий URL pathname

    Returns:
        list: Список dbc.NavLink
    """
    # Normalize pathname: "/" → "/dashboard"
    if active_pathname == "/":
        active_pathname = "/dashboard"

    nav_links = []
    for item in MAIN_NAV_ITEMS:
        is_active = item["href"] == active_pathname
        css_class = "text-dark py-3 px-3 rounded-0 border-0"
        if is_active:
            css_class += " sidebar-nav-item-active"

        link = dbc.NavLink(
            [html.I(className=f"bi {item['icon']} me-3"), item["label"]],
            href=item["href"],
            active=is_active,
            className=css_class,
        )
        nav_links.append(link)
    return nav_links


def create_sidebar():
    """Создает боковое меню навигации в card-контейнере."""

    # Логотип и заголовок
    header = html.Div(
        [
            html.Div(
                [
                    html.I(
                        className="bi bi-currency-dollar text-success me-2",
                        style={"fontSize": "1.5rem"},
                    ),
                    html.Span("FinFocus", className="h4 mb-0 text-dark fw-bold"),
                ],
                className="d-flex align-items-center p-3",
            )
        ]
    )

    # Информация о пользователе (пока заглушка)
    user_info = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.I(
                                className="bi bi-person-circle",
                                style={"fontSize": "2rem"},
                            ),
                        ],
                        className="me-3",
                    ),
                    html.Div(
                        [
                            html.Div("Иван Иванов", className="fw-semibold"),
                            html.Div("Личный аккаунт", className="text-muted small"),
                        ]
                    ),
                ],
                className="d-flex align-items-center p-3 bg-light rounded mx-3 mb-3",
            )
        ]
    )

    # Главное меню
    main_menu = html.Div(
        [
            html.Div("ГЛАВНОЕ МЕНЮ", className="text-muted small fw-bold px-3 mb-2"),
            dbc.Nav(
                _build_nav_links("/dashboard"),
                id="sidebar-nav",
                vertical=True,
                className="mb-4",
            ),
        ]
    )

    # Дополнительные пункты
    additional_links = []
    for item in ADDITIONAL_NAV_ITEMS:
        link = dbc.NavLink(
            [html.I(className=f"bi {item['icon']} me-3"), item["label"]],
            href=item["href"],
            className="text-dark py-2 px-3 rounded-0 border-0",
        )
        additional_links.append(link)

    additional_menu = html.Div(
        [
            html.Div("НАСТРОЙКИ", className="text-muted small fw-bold px-3 mb-2"),
            dbc.Nav(additional_links, vertical=True),
        ]
    )

    # Собираем sidebar и оборачиваем в Card
    sidebar_content = html.Div(
        [
            header,
            user_info,
            main_menu,
            additional_menu,
            # Футер sidebar
            html.Div(
                [
                    html.Hr(className="mx-3"),
                    html.Div(
                        [html.Span("v1.0.0", className="text-muted small")],
                        className="text-center p-3",
                    ),
                ],
            ),
        ],
    )

    return dbc.Card(
        sidebar_content,
        className="sidebar-card",
    )


# ==================== CALLBACKS ====================


@callback(
    Output("sidebar-nav", "children"),
    Input("url", "pathname"),
)
def highlight_active_sidebar(pathname: str | None):
    """Обновляет active state в sidebar при смене страницы.

    Args:
        pathname: Текущий URL pathname

    Returns:
        list: Обновленные NavLink с active highlight
    """
    if pathname is None:
        pathname = "/dashboard"
    return _build_nav_links(pathname)
