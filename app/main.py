"""
Главное приложение FinFocus - планировщик бюджета.
"""
from dotenv import load_dotenv

from app.core.paths import get_app_dir, get_assets_dir

import dash
import time
from datetime import date
from dash import (
    dcc,
    html,
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    ClientsideFunction,
    no_update,
)
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from loguru import logger

from app.components.dashboard import create_dashboard_layout
from app.components.nav_rail import create_nav_rail
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
        # Главная структура: полоска-меню + контент
        html.Div(
            [
                # Слот полоски-меню: наполняется render_nav_rail_slot;
                # на дашборде пуст, колонку скрывает CSS :empty
                html.Div(id="nav-rail-slot", className="nav-rail-column"),
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
        # Store для обновления полоски-меню при изменении профиля
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
        # Фокус дня календаря из дверей щитка: {"value": ISO, "ts": мс}
        dcc.Store(id="calendar-focus-date", data=None),
        # Фокус цели из карточки щитка: {"value": goal_id, "ts": мс}
        dcc.Store(id="goals-focus-goal", data=None),
    ],
    fluid=True,
    className="p-0 app-container",
)


DEFAULT_USER_ID = 1


@callback(
    Output("nav-rail-slot", "children"),
    Input("url", "pathname"),
    Input("profile-updated", "data"),
)
def render_nav_rail_slot(pathname: str | None, profile_updated: float | None):
    """Полоска-меню есть на всех страницах, КРОМЕ дашборда (FR-2, AC-1).

    ЕДИНСТВЕННЫЙ колбэк навигации. Оба прежних колбэка сайдбара —
    highlight_active_sidebar (Output sidebar-nav) и
    update_sidebar_profile (Output sidebar-profile-name/-avatar) —
    были удалены ещё куском 2 (critique-v2, блокер №2; Подход B
    критика, принят владельцем): после снятия навигации с дашборда
    их Output'ы стали бы условно присутствующими, а гонку с
    перерисовкой слота guard по pathname не снимает. Чтение профиля
    живёт здесь, create_nav_rail — чистая функция.

    Оба Input'а — на элементы, присутствующие ВСЕГДА: dcc.Location
    "url" и dcc.Store "profile-updated" живут в глобальном layout.
    Правило C-6 соблюдено с обеих сторон: ни Input, ни Output не
    смотрит на условно присутствующий узел.

    profile-updated как Input, а не State: правка профиля обязана
    перерисовать полоску (тот же Store уже слушает
    load_dashboard_data). Guard'а на пустой Store здесь НЕ нужно —
    колбэк идемпотентен: он не открывает модалов, а перерисовка
    полоски тем же содержимым не наблюдаема.

    ВОЗВРАТ — РОВНО ОДИН КОМПОНЕНТ, НЕ СПИСОК. Это часть механизма
    FR-2: React сопоставляет старый и новый узел по ключу обёртки
    (`stringifyId(props.id)` — отсюда id="nav-rail") И по позиции
    среди детей. Единственный ребёнок держит позицию стабильной, и
    полоска при переходе раздел→раздел патчится, а не пересоздаётся —
    иначе анимация разворота (шаг 8) играла бы на каждом переходе.
    Обернуть возврат в список — значит сломать это молча: визуально
    всё останется на месте, поедет только анимация.

    ЦЕНА (стратегия загрузки solution-v4): одна сессия и одно чтение
    профиля на каждый переход между разделами. На /dashboard сессии
    НЕТ — возвращается [] до её открытия. Сбой чтения профиля НЕ
    обрушивает полоску: except → профиль-заглушка + лог, навигация
    остаётся рабочей (находимость разделов важнее аватара).

    Колонка скрывается ОДНИМ механизмом — CSS-правилом
    .nav-rail-column:empty { display: none } (critique-v1, №9),
    поэтому className не переключается и Output'а на него нет.
    """
    if pathname in (None, "/", "/dashboard"):
        return []  # сессия НЕ открывается

    try:
        with get_db_session() as session:
            profile = OnboardingService(session).get_profile(DEFAULT_USER_ID)
    except Exception:
        logger.opt(exception=True).warning(
            "Не удалось прочитать профиль для полоски-меню — "
            "рисуем полоску с профилем-заглушкой (навигация не теряется)"
        )
        profile = UserProfile(name="Пользователь", avatar_id=DEFAULT_AVATAR_ID)

    return create_nav_rail(pathname, profile)


# Аватар в полоске-меню → open-profile-trigger (модал профиля).
# Полоска рендерится динамически в nav-rail-slot и на дашборде
# отсутствует — прямой Input в handle_profile_modal молча отключил бы
# колбэк на дашборде целиком, включая вход через шестерёнку (класс
# регрессий C-6 «наоборот», риск R1 solution-v4). Тот же паттерн
# Store-триггера, что у шестерёнки щитка (урок протокола 0028).
clientside_callback(
    ClientsideFunction("triggers", "timestamp_trigger"),
    Output("open-profile-trigger", "data", allow_duplicate=True),
    Input("nav-rail-avatar", "n_clicks"),
    prevent_initial_call=True,
)


_OWNED_SEARCH_PATHS = frozenset({"/calendar", "/goals"})
"""КОНТРАКТ ВЛАДЕНИЯ url.search (critique-v1, блокер №1 solution-v4).

url.search — Input не только у handle_panel_query_params. Второй
читатель — apply_url_date_filter (transactions.py): читает ?start=&end=
для /transactions, в search НЕ пишет, работает с протокола 0023. Если
бы этот колбэк чистил search на /transactions, фильтр периода перестал
бы применяться (или применялся недетерминированно — гонка двух
Output'ов на один Input), то есть сломалась бы уже работающая дверь
Операций.

Правило: чистим search ТОЛЬКО для путей, чьи параметры разобрали сами.
Для /transactions — PreventUpdate. Идемпотентность там обеспечена самим
разделом: повторное применение того же периода не наблюдаемо.
"""


# Единый callback для обработки query params дверей щитка
@callback(
    [
        Output("open-recon-trigger", "data"),
        Output("wishlist-active-item", "data"),
        Output("calendar-focus-date", "data"),
        Output("goals-focus-goal", "data"),
        Output("url", "search"),
    ],
    Input("url", "search"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def handle_panel_query_params(url_search: str | None, pathname: str | None):
    """Разбирает query params дверей щитка и раскладывает по Store'ам.

    Расширение механизма протоколов 0023/0028, а не новый механизм:

      РАЗБИРАЕТ САМ и очищает search (_OWNED_SEARCH_PATHS):
        /calendar?open_recon=1      → open-recon-trigger    (было)
        /calendar?wishlist_item=ID  → wishlist-active-item  (было)
        /calendar?focus_date=ISO    → calendar-focus-date   (НОВОЕ, FR-3)
        /goals?goal=ID              → goals-focus-goal      (НОВОЕ, FR-3)

      НЕ ТРОГАЕТ (PreventUpdate, search принадлежит разделу):
        /transactions?start=&end=   → apply_url_date_filter (0023)
        /analytics                  → params не нужны: раздел уже
                                      открывается на текущем месяце

    ФОРМАТ ЗНАЧЕНИЯ новых Store'ов — dict, не скаляр (critique-v2, №7):
        {"value": <date ISO | goal_id>, "ts": <int мс>}
    ts обязателен: два клика подряд по «завтра» должны сработать
    дважды, а Store сравнивается по значению. Он же — ключ
    идемпотентности приёмника (guard в load_and_navigate_calendar
    и apply_goal_focus).

    Битые значения (?focus_date=abc, ?goal=x) игнорируются молча —
    не повод падать; если ни один параметр не распознан, PreventUpdate,
    и search сохраняется.
    """
    if not url_search or pathname not in _OWNED_SEARCH_PATHS:
        raise PreventUpdate

    from urllib.parse import parse_qs

    params = parse_qs(url_search.lstrip("?"))
    now_ms = int(time.time() * 1000)
    recon_trigger = None
    wishlist_item = None
    focus_date = None
    focus_goal = None

    if pathname == "/calendar":
        if "open_recon" in params:
            recon_trigger = now_ms

        if "wishlist_item" in params:
            try:
                wishlist_item = int(params["wishlist_item"][0])
            except (ValueError, IndexError):
                pass

        if "focus_date" in params:
            try:
                iso_value = params["focus_date"][0]
                date.fromisoformat(iso_value)  # валидация, битое — молча мимо
                focus_date = {"value": iso_value, "ts": now_ms}
            except (ValueError, IndexError):
                pass

    if pathname == "/goals" and "goal" in params:
        try:
            focus_goal = {"value": int(params["goal"][0]), "ts": now_ms}
        except (ValueError, IndexError):
            pass

    if all(v is None for v in (recon_trigger, wishlist_item, focus_date, focus_goal)):
        raise PreventUpdate

    # Нераспознанные параметры → no_update, НЕ None: запись в Store —
    # даже того же значения — триггерит его подписчиков. None в
    # wishlist-active-item перерисовал бы календарь ВТОРОЙ раз, уже без
    # фокуса (triggered_id сменился бы на wishlist-active-item), и
    # подсветка дня гасла бы в той же секунде, что появилась.
    return (
        recon_trigger if recon_trigger is not None else no_update,
        wishlist_item if wishlist_item is not None else no_update,
        focus_date if focus_date is not None else no_update,
        focus_goal if focus_goal is not None else no_update,
        "",
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
