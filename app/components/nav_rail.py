"""Nav Rail — узкая полоска-меню (Epic-11, кусок 3, протокол 0031).

Заменяет широкий сайдбар (228px) полоской иконок (60px) на всех
страницах, кроме дашборда: содержимому возвращается 228px ширины,
а сам дашборд остаётся щитком без навигации сбоку (кусок 2, AC-1).

НАСЛЕДУЕМЫЕ ИНВАРИАНТЫ (от sidebar.py после куска 2):

  1. Ни одного `@callback` в модуле. Полоска рендерится слот-колбэком
     в app/main.py; Output на её узлы из другого колбэка был бы гонкой
     с этим слот-колбэком, а не шумом в логах.
  2. Ни одного обращения к БД. Профиль приходит аргументом —
     функция чистая и тестируется без сессии.
  3. Вход в профиль — ТОЛЬКО через Store `open-profile-trigger`
     (clientside-триггер в main.py). Прямой серверный Input на узел
     полоски молча отключил бы колбэк профиля на дашборде, где
     полоски нет: клиентский рендерер Dash при отсутствии одного из
     Input'ов перестаёт отправлять запрос целиком, и ошибки в консоли
     при этом нет (протоколы 0026, 0028, 0030).

ЧЕГО В ПОЛОСКЕ НЕТ (осознанно):

  * «Настройки» (FR-4) — маршрута /settings не существует, пункт вёл
    на 404 (P1 UX-аудита 2026-08-20). Возвращать вместе со страницей.
  * Версия (FR-5) — переехала в окно профиля (шаг 3 протокола).
  * Имя пользователя — в 60px не помещается. Компенсируется окном
    профиля, где имя и так первое поле (RTM #68).
"""

from typing import TypedDict

from dash import dcc, html

from app.config.avatars import get_avatar_emoji
from app.schema.onboarding import UserProfile


class RailSection(TypedDict):
    """Один раздел полоски."""

    label: str
    icon: str
    href: str


# Ровно четыре раздела. Дашборда здесь НЕТ — на него ведёт знак-домик
# наверху полоски (см. _build_logo).
RAIL_SECTIONS: list[RailSection] = [
    {"label": "Календарь", "icon": "bi-calendar3", "href": "/calendar"},
    {"label": "Операции", "icon": "bi-list-ul", "href": "/transactions"},
    {"label": "Аналитика", "icon": "bi-bar-chart", "href": "/analytics"},
    {"label": "Цели", "icon": "bi-target", "href": "/goals"},
]


def _build_tip(label: str) -> html.Span:
    """Язычок с подписью, всплывающий справа от слота.

    Скрыт от скринридеров: подпись уже есть в aria-label носителя,
    иначе она читалась бы дважды.
    """
    return html.Span(label, className="nav-rail-tip", **{"aria-hidden": "true"})


def _build_logo() -> dcc.Link:
    """Знак-домик наверху — вход на дашборд.

    Домик, а не изображение электрощитка (решение владельца):
    метафора щитка описывает устройство дашборда, а иконка должна
    читаться как «Домой» без объяснений.
    """
    return dcc.Link(
        [
            html.I(className="bi bi-house-door", **{"aria-hidden": "true"}),
            _build_tip("Дашборд"),
        ],
        href="/dashboard",
        className="nav-rail-logo",
        title="На дашборд",
    )


def _build_section_slot(section: RailSection, is_active: bool) -> dcc.Link:
    """Слот одного раздела.

    Класс слота несёт САМА ссылка, а знак вложен внутрь: зона нажатия
    должна быть все 44×44 (WCAG 2.5.5 Target Size), а не 22px знака.

    ДОСТУПНОЕ ИМЯ — через `title`, а не `aria-label`. Шаг 5 протокола
    предписывал `aria-label` + `aria-current="page"`, и то же велел
    проверить на построении — проверка показала, что так нельзя:
    `dcc.Link` в dash 2.17.1 принимает жёсткий список пропсов
    (children, href, target, refresh, title, className, style, id,
    loading_state) и на любой `aria-*` бросает TypeError прямо при
    построении layout. Произвольные атрибуты пропускают только
    `html.*`-компоненты.

    Заменить `dcc.Link` на `html.A` ради `aria-*` нельзя: `html.A`
    делает полную перезагрузку страницы, а это ломает и клиентскую
    навигацию, и переиспользование узла полоски, на котором стоит
    анимация разворота (шаг 1 протокола, шаг 8 реализации).

    `title` — валидное доступное имя по HTML-спецификации: при
    отсутствии текстового содержимого и `aria-label` скринридер
    берёт его. Побочно даёт нативную подсказку браузера.

    Цена компромисса: активный раздел не помечен `aria-current`,
    для скринридера он неотличим от остальных. Визуально и для
    зрячих пользователей он подсвечен классом-пилюлей.
    """
    class_name = "nav-rail-slot"
    if is_active:
        class_name += " nav-rail-slot--active"

    return dcc.Link(
        [
            html.I(className=f"bi {section['icon']}", **{"aria-hidden": "true"}),
            _build_tip(section["label"]),
        ],
        href=section["href"],
        className=class_name,
        title=section["label"],
    )


def _build_avatar(profile_data: UserProfile) -> html.Div:
    """Аватар внизу полоски — вход в окно профиля.

    Серверного Input на этот узел нет и не должно появиться
    (инвариант 3 докстринга модуля): клик уходит clientside-триггером
    в Store `open-profile-trigger`. `n_clicks=0` нужен именно для
    того, чтобы clientside-триггер имел за что зацепиться.
    """
    return html.Div(
        [
            html.Span(
                get_avatar_emoji(profile_data["avatar_id"]),
                **{"aria-hidden": "true"},
            ),
            _build_tip("Профиль"),
        ],
        id="nav-rail-avatar",
        n_clicks=0,
        className="nav-rail-avatar",
        **{"aria-label": "Открыть профиль", "role": "button"},
    )


def create_nav_rail(pathname: str | None, profile_data: UserProfile) -> html.Div:
    """Полоска-меню — ЧИСТАЯ функция: ни БД, ни колбэков.

    Про `id="nav-rail"`: это носитель React-идентичности узла. Ключ
    обёртки в dash-renderer 2.17.1 — `stringifyId(component.props.id)`
    (`createContainer`), поэтому при переходе раздел→раздел React
    сопоставляет старый и новый узел по имени и ПАТЧИТ существующий
    вместо пересоздания. На этом стоит анимация разворота (шаг 8):
    она играет только на монтировании, то есть при входе с дашборда,
    а не на каждом переходе между разделами.

    Эмпирика — шаг 1 протокола: узел переиспользуется в обоих режимах
    (с `id` и без), проверено прямым сравнением ссылки на DOM-узел
    до и после перехода.

    `id` здесь — НЕ приглашение вешать на узел Input или Output.
    Output был бы гонкой со слот-колбэком, который этот же узел
    создаёт и удаляет (порядок применения Output'ов Dash не
    гарантирует), а Input молча отключил бы колбэк на дашборде,
    где полоски нет.

    Проп `key` не ставится нигде: на реконсиляцию обёртки он не
    влияет (ключ берётся из `id`), а `dcc.Link` его вообще не
    принимает — в dash 2.17.1 это TypeError на построении.

    Функция тотальна: любой pathname допустим, ни один раздел просто
    не окажется активным.

    Args:
        pathname: Текущий путь для подсветки активного раздела.
            None и "/" нормализуются в "/dashboard" — тогда активных
            разделов нет (дашборда в списке нет, на него ведёт логотип).
        profile_data: Имя и avatar_id пользователя. Имя в полоску не
            попадает (не влезает в 60px), используется только avatar_id.

    Returns:
        html.Div: Кожух полоски с единственным ребёнком .nav-rail-inner.
    """
    active_pathname = pathname or "/dashboard"
    if active_pathname == "/":
        active_pathname = "/dashboard"

    slots = [
        _build_section_slot(section, section["href"] == active_pathname)
        for section in RAIL_SECTIONS
    ]

    inner = html.Div(
        [
            _build_logo(),
            html.Div(className="nav-rail-sep"),
            html.Nav(slots, className="nav-rail-nav"),
            html.Div(className="nav-rail-spacer"),
            _build_avatar(profile_data),
        ],
        className="nav-rail-inner",
    )

    return html.Div(
        inner,
        id="nav-rail",
        className="nav-rail",
    )
