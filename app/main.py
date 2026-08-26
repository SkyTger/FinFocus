"""
Главное приложение FinFocus - планировщик бюджета.
"""
from dotenv import load_dotenv

from app.core.paths import get_app_dir, get_assets_dir

import dash
import time
from dash import (
    dcc,
    html,
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    ClientsideFunction,
)
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from loguru import logger

from app.components.dashboard import create_dashboard_layout
from app.components.sidebar import create_sidebar
from app.config.avatars import DEFAULT_AVATAR_ID
from app.core.database import get_db_session
from app.schema.onboarding import UserProfile
from app.services.onboarding_service import OnboardingService
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
from app.components.profile_modal import create_profile_modal
from app.components.wishlist import create_wishlist_modal

# Загружаем переменные окружения (.env рядом с exe в frozen, опционален)
load_dotenv(get_app_dir() / ".env", override=False)

# Создаем Dash приложение
app = dash.Dash(
    __name__,
    assets_folder=str(get_assets_dir()),
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
        html.Div(
            [
                # Sidebar-слот: наполняется render_sidebar_slot;
                # на дашборде пуст, колонку скрывает CSS :empty
                html.Div(id="sidebar-slot", className="sidebar-column"),
                # Основной контент
                html.Div(
                    [
                        html.Div(id="page-header"),
                        dbc.Alert(
                            id="transaction-error-alert",
                            is_open=False,
                            color="danger",
                            dismissable=True,
                            duration=5000,
                        ),
                        html.Div(id="page-content"),
                    ],
                    className="main-content",
                ),
            ],
            className="app-layout",
        ),
        # Глобальные модалы транзакций (доступны на всех страницах)
        create_transaction_modals(),
        # Wishlist модал (отложенные покупки)
        create_wishlist_modal(),
        # Reconciliation модал (глобальный — доступен с Calendar и Dashboard)
        create_reconciliation_modal(),
        # Onboarding wizard (blocking modal при first_launch)
        create_onboarding_wizard(),
        # Profile modal (глобальный — редактирование профиля)
        create_profile_modal(),
        # Store для обновления sidebar при изменении профиля
        dcc.Store(id="profile-updated", data=None),
        # Глобальный store для toast dismissal (до перезагрузки)
        dcc.Store(id="balance-toast-dismissed", data=False),
        # Trigger для автооткрытия reconciliation modal (timestamp-based)
        dcc.Store(id="open-recon-trigger", data=None),
        # Trigger для открытия профиля из шестерёнки щитка (timestamp-based)
        dcc.Store(id="open-profile-trigger", data=None),
        # Trigger для открытия модала wishlist из двери щитка (timestamp-based)
        dcc.Store(id="open-wishlist-trigger", data=None),
        # Wishlist: ID активного элемента для планирования в календаре
        dcc.Store(id="wishlist-active-item", data=None),
    ],
    fluid=True,
    className="p-0 app-container",
)


DEFAULT_USER_ID = 1


@callback(
    Output("sidebar-slot", "children"),
    Input("url", "pathname"),
    Input("profile-updated", "data"),
)
def render_sidebar_slot(pathname: str | None, profile_updated: float | None):
    """Сайдбар есть на всех страницах, КРОМЕ дашборда (FR-2, AC-1).

    ЕДИНСТВЕННЫЙ колбэк сайдбара. Оба прежних — highlight_active_sidebar
    (Output sidebar-nav) и update_sidebar_profile (Output
    sidebar-profile-name/-avatar) — УДАЛЕНЫ (critique-v2, блокер №2;
    Подход B критика, принят владельцем): после снятия сайдбара с
    дашборда их Output'ы стали бы условно присутствующими, а гонку
    с перерисовкой слота guard по pathname не снимает. Чтение профиля
    переехало сюда, create_sidebar стала чистой функцией.

    Оба Input'а — на элементы, присутствующие ВСЕГДА: dcc.Location
    "url" и dcc.Store "profile-updated" живут в глобальном layout.
    Правило C-6 соблюдено с обеих сторон: ни Input, ни Output не
    смотрит на условно присутствующий узел.

    profile-updated как Input, а не State: правка профиля обязана
    перерисовать сайдбар (тот же Store уже слушает load_dashboard_data).
    Guard'а на пустой Store здесь НЕ нужно — колбэк идемпотентен:
    он не открывает модалов, а перерисовка сайдбара тем же
    содержимым не наблюдаема.

    ЦЕНА (стратегия загрузки solution-v4): одна сессия и одно чтение
    профиля на каждый переход между разделами. На /dashboard сессии
    НЕТ — возвращается [] до её открытия. Сбой чтения профиля НЕ
    обрушивает сайдбар: except → профиль-заглушка + лог, навигация
    остаётся рабочей (находимость разделов важнее имени).

    Колонка скрывается ОДНИМ механизмом — CSS-правилом
    .sidebar-column:empty { display: none } (critique-v1, №9),
    поэтому className не переключается и Output'а на него нет.
    """
    if pathname in (None, "/", "/dashboard"):
        return []  # сессия НЕ открывается

    try:
        with get_db_session() as session:
            profile = OnboardingService(session).get_profile(DEFAULT_USER_ID)
    except Exception:
        logger.opt(exception=True).warning(
            "Не удалось прочитать профиль для сайдбара — "
            "рисуем сайдбар с профилем-заглушкой (навигация не теряется)"
        )
        profile = UserProfile(name="Пользователь", avatar_id=DEFAULT_AVATAR_ID)

    return create_sidebar(pathname, profile)


# Аватар в сайдбаре → open-profile-trigger (модал профиля).
# Сайдбар рендерится динамически в sidebar-slot и на дашборде
# отсутствует — прямой Input в handle_profile_modal молча отключил бы
# колбэк на дашборде целиком, включая вход через шестерёнку (класс
# регрессий C-6 «наоборот», риск R1 solution-v4). Тот же паттерн
# Store-триггера, что у шестерёнки щитка (урок протокола 0028).
clientside_callback(
    ClientsideFunction("triggers", "timestamp_trigger"),
    Output("open-profile-trigger", "data", allow_duplicate=True),
    Input("sidebar-profile-container", "n_clicks"),
    prevent_initial_call=True,
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
        # Главная страница — дашборд (заголовок встроен в glass-header)
        return create_dashboard_layout(), html.Div(style={"display": "none"})

    elif pathname == "/calendar":
        # Кассовый календарь (заголовок встроен в glass-header)
        return create_calendar_layout(), html.Div(style={"display": "none"})

    elif pathname == "/goals":
        # Накопительные цели (заголовок встроен в layout)
        return create_goals_layout(), html.Div(style={"display": "none"})

    elif pathname == "/transactions":
        # Страница операций (заголовок встроен в glass-header)
        return create_transactions_layout(), html.Div(style={"display": "none"})

    elif pathname == "/analytics":
        # Страница аналитики (заголовок встроен в glass-header)
        return create_analytics_layout(), html.Div(style={"display": "none"})

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
