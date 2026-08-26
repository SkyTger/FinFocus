"""Sidebar компонент - боковое меню навигации.

Куском 2 (протокол 0030) файл стал ЧИСТЫМ: оба колбэка удалены
(highlight_active_sidebar, update_sidebar_profile), их обязанности
переехали в построение create_sidebar(pathname, profile). Сайдбар
рендерится колбэком render_sidebar_slot (app/main.py) и на дашборде
отсутствует — Output на его узлы из другого колбэка был бы гонкой
с render_sidebar_slot, а не шумом в логах (см. докстринг create_sidebar).
"""
import dash_bootstrap_components as dbc
from dash import html

from app.config.avatars import get_avatar_emoji
from app.schema.onboarding import UserProfile

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


def create_sidebar(pathname: str | None, profile_data: UserProfile) -> dbc.Card:
    """Сайдбар — ЧИСТАЯ функция: ни БД, ни колбэков, ни литералов профиля.

    Изменение куска 2 (critique-v2, блокер №2): оба колбэка файла
    удалены, обе их обязанности переехали в построение.

      * подсветка активного пункта: было highlight_active_sidebar
        (Output "sidebar-nav") ← Input url.pathname; стало
        _build_nav_links(pathname) на построении. Прежде
        _build_nav_links получал захардкоженный "/dashboard", и без
        колбэка подсветка была бы всегда на «Дашборде».
      * имя и аватар: было update_sidebar_profile (Output
        "sidebar-profile-name"/"-avatar") ← Input url.pathname
        + profile-updated; стало — аргумент profile_data.

    Почему не guard, а удаление: после FR-2 сайдбар рендерится
    колбэком render_sidebar_slot по тому же Input("url", "pathname"),
    и оба прежних колбэка писали бы children в узлы, которые
    render_sidebar_slot в этот же момент создаёт или удаляет. Порядок
    применения Output'ов Dash не гарантирует — это гонка, а не шум
    в логах. Guard на pathname её не снимает, а лишь маскирует
    (и во втором случае давал бы «Пользователь» + 😊 после каждого
    перехода — регрессия Epic-09 фазы 2).
    Результат: у сайдбара НЕТ ни одного серверного колбэка; клик по
    аватару уходит clientside-триггером в Store open-profile-trigger
    (app/main.py) — единственный вход открытия модала профиля.

    Args:
        pathname: Текущий путь для подсветки; None → "/dashboard"
            (сохраняет прежнее поведение _build_nav_links).
        profile_data: Имя и avatar_id пользователя. Аватар-эмодзи
            получается get_avatar_emoji(profile_data["avatar_id"]) —
            как в удалённом колбэке.
    """
    # Профиль пользователя (clickable — clientside-триггер в main.py)
    profile = html.Div(
        [
            html.Div(
                html.Span(
                    get_avatar_emoji(profile_data["avatar_id"]),
                    id="sidebar-profile-avatar",
                ),
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
                        profile_data["name"],
                        id="sidebar-profile-name",
                        className="fw-bold",
                        style={"fontSize": "14px", "lineHeight": "1.2"},
                    ),
                    html.Div(
                        "Профиль \u270f\ufe0f",
                        className="text-muted",
                        style={"fontSize": "12px"},
                    ),
                ]
            ),
        ],
        id="sidebar-profile-container",
        n_clicks=0,
        className=(
            "d-flex align-items-center gap-3 px-4 pt-4 pb-2"
            " sidebar-profile-clickable"
        ),
    )

    # Навигация (без заголовков секций, как в Stitch)
    nav = html.Div(
        [
            dbc.Nav(
                _build_nav_links(pathname or "/dashboard"),
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
