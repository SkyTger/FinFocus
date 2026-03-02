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
        css_class = "text-dark py-3 px-3 border-0"
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
    """Создает боковое меню навигации в card-контейнере (Stitch design)."""

    # Профиль пользователя (вверху, как в Stitch)
    profile = html.Div(
        [
            html.Div(
                "🦊",
                className="d-flex align-items-center justify-content-center",
                style={
                    "width": "48px",
                    "height": "48px",
                    "borderRadius": "50%",
                    "background": "rgba(46, 204, 113, 0.15)",
                    "border": "1px solid rgba(255,255,255,0.4)",
                    "fontSize": "1.5rem",
                },
            ),
            html.Div(
                [
                    html.Div(
                        "Иван Иванов",
                        className="fw-bold",
                        style={"fontSize": "14px", "lineHeight": "1.2"},
                    ),
                    html.Div(
                        "FinFocus",
                        className="text-muted",
                        style={"fontSize": "12px"},
                    ),
                ]
            ),
        ],
        className="d-flex align-items-center gap-3 px-4 pt-4 pb-2",
    )

    # Навигация (без заголовков секций, как в Stitch)
    nav = html.Div(
        [
            dbc.Nav(
                _build_nav_links("/dashboard"),
                id="sidebar-nav",
                vertical=True,
                className="sidebar-nav px-2",
            ),
        ],
        className="flex-grow-1 py-2",
    )

    # Настройки внизу (mt-auto pushes to bottom)
    settings_link = dbc.NavLink(
        [html.I(className="bi bi-gear me-3"), "Настройки"],
        href="/settings",
        className="text-dark py-3 px-3 border-0",
        style={"borderRadius": "9999px"},
    )

    bottom = html.Div(
        [
            html.Div(
                dbc.Nav([settings_link], vertical=True),
                className="px-2",
            ),
            html.Div(className="sidebar-separator"),
            html.Div(
                html.Span("v1.0.0", className="text-muted small"),
                className="text-center pb-4",
            ),
        ],
        className="mt-auto",
    )

    sidebar_content = html.Div(
        [profile, nav, bottom],
        style={"display": "flex", "flexDirection": "column", "height": "100%"},
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
