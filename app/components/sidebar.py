"""
Sidebar компонент - боковое меню навигации.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc


def create_sidebar():
    """Создает боковое меню навигации."""

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

    # Пункты меню
    nav_items = [
        {
            "label": "Дашборд",
            "icon": "bi-speedometer2",
            "href": "/dashboard",
            "active": True,
        },
        {"label": "Календарь", "icon": "bi-calendar3", "href": "/calendar"},
        {"label": "Операции", "icon": "bi-list-ul", "href": "/transactions"},
        {"label": "Цели", "icon": "bi-target", "href": "/goals"},
    ]

    # Создаем элементы меню
    nav_links = []
    for item in nav_items:
        link = dbc.NavLink(
            [html.I(className=f"bi {item['icon']} me-3"), item["label"]],
            href=item["href"],
            active=item.get("active", False),
            className="text-dark py-3 px-3 rounded-0 border-0",
        )
        nav_links.append(link)

    # Главное меню
    main_menu = html.Div(
        [
            html.Div("ГЛАВНОЕ МЕНЮ", className="text-muted small fw-bold px-3 mb-2"),
            dbc.Nav(nav_links, vertical=True, className="mb-4"),
        ]
    )

    # Дополнительные пункты
    additional_items = [
        {"label": "Настройки", "icon": "bi-gear", "href": "/settings"},
        {"label": "Справка", "icon": "bi-question-circle", "href": "/help"},
    ]

    additional_links = []
    for item in additional_items:
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

    # Собираем весь sidebar
    sidebar = html.Div(
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
                className="mt-auto",
            ),
        ],
        className="d-flex flex-column h-100 bg-white border-end",
    )

    return sidebar
