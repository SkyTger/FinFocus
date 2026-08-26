"""
Dashboard компонент - главная страница с обзором финансов.
"""
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
from dash import (
    callback,
    clientside_callback,
    ClientsideFunction,
    ctx,
    html,
    dcc,
    no_update,
    Input,
    Output,
    State,
)
from dash.exceptions import PreventUpdate
from loguru import logger

from app.core.database import get_db_session
from app.components.panel_cards import build_cards_row
from app.services.panel_service import DashboardPanelService
from app.services.onboarding_service import OnboardingService
from app.schema.money_layers import (
    MoneyLayersData,
    LAYER_COLORS,
    LAYER_LABELS,
    MAX_X_TICKS,
)
from app.schema.onboarding import UserProfile
from app.config.avatars import get_avatar_emoji
from datetime import date
from math import ceil

from app.utils.formatters import format_rub, format_date_human

DEFAULT_USER_ID = 1

# Максимум строк платежей в тултипе легенды — дальше «и ещё N»
MAX_TOOLTIP_PAYMENTS = 8

STATUS_COLORS: dict[str, str] = {
    "ok": "#27ae60",
    "attention": "#f39c12",
    "risk": "#c0152f",
}


# =============================================================================
# Layout
# =============================================================================


def _build_balance_banner() -> dbc.Alert:
    """Создает баннер для предупреждения о нулевом балансе."""
    return dbc.Alert(
        id="balance-alert-toast",
        is_open=False,
        dismissable=True,
        className="balance-banner mb-0",
        children=[
            html.Div(
                [
                    html.I(className="bi bi-exclamation-triangle-fill me-2"),
                    html.Span(
                        "Для точных расчётов укажите текущий остаток на счетах.",
                        className="me-3",
                    ),
                    dbc.Button(
                        "Сверить баланс",
                        id="open-recon-from-dashboard-banner-btn",
                        color="dark",
                        size="sm",
                        outline=True,
                        n_clicks=0,
                    ),
                ],
                className="d-flex align-items-center justify-content-center flex-wrap",
            ),
        ],
    )


def _build_recon_button(button_id: str) -> dbc.Button:
    """Кнопка «Сверка» — открывает модал сверки через clientside-триггер.

    Args:
        button_id: ID кнопки (у каждой точки входа свой).

    Returns:
        dbc.Button: Кнопка «Сверка».
    """
    return dbc.Button(
        [html.I(className="bi bi-check2-square me-1"), "Сверка"],
        id=button_id,
        color="success",
        outline=True,
        size="sm",
        n_clicks=0,
    )


def _build_settings_cog() -> dbc.Button:
    """Шестерёнка щитка — второй вход в модал профиля (решение владельца п. 5).

    Первый вход (аватар в сайдбаре) остаётся рабочим: profile_modal
    слушает оба источника.

    Returns:
        dbc.Button: Кнопка-шестерёнка.
    """
    return dbc.Button(
        html.I(className="bi bi-gear"),
        id="dashboard-settings-cog",
        title="Профиль и настройки",
        className="pnl-cog",
        color="link",
        n_clicks=0,
    )


def _build_header_who(profile: UserProfile) -> html.Div:
    """Правый угол шапки: аватар с именем, «Сверка», шестерёнка.

    Состав воспроизводит эскиз буквально
    (.visual/finfocus-panel-dashboard/v3.html:415-418).

    Args:
        profile: Профиль пользователя — единственный источник имени
            и аватара в шапке.

    Returns:
        html.Div с классом pnl-who.
    """
    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        get_avatar_emoji(profile["avatar_id"]),
                        className="pnl-avatar-face",
                        **{"aria-hidden": "true"},
                    ),
                    html.Span(profile["name"], className="pnl-avatar-name"),
                ],
                className="pnl-avatar",
            ),
            _build_recon_button("open-recon-from-dashboard-header-btn"),
            _build_settings_cog(),
        ],
        className="pnl-who",
    )


def _build_header_empty_state(profile: UserProfile) -> html.Div:
    """Шапка при полном отсутствии данных (FR-6).

    Главного числа нет — показывать «0 ₽» как факт было бы неправдой:
    у пользователя не ноль свободных денег, а незаполненная база.

    Args:
        profile: Профиль пользователя.

    Returns:
        html.Div с классом pnl-breaker.
    """
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Пока нечего показать", className="pnl-empty-title"),
                    html.Div(
                        "Добавьте первую операцию или сверьте баланс",
                        className="pnl-empty-hint",
                    ),
                    _build_recon_button("open-recon-from-dashboard-empty-btn"),
                ],
                className="pnl-breaker-main pnl-empty",
            ),
            _build_header_who(profile),
        ],
        className="pnl-breaker",
    )


def build_free_header(
    data: MoneyLayersData,
    profile: UserProfile,
) -> html.Div:
    """Шапка «Свободно сегодня: N ₽» (FR-2, FR-5).

    Состав слева: метка «Свободно сегодня», сумма (tabular-nums),
    разбор «баланс {balance} − платежи {payments} − резерв {reserve}».
    Справа: аватар-эмодзи + имя, кнопка «Сверка»
    (id="open-recon-from-dashboard-header-btn"), шестерёнка
    (id="dashboard-settings-cog" → модал профиля).

    ПРИВЕТСТВИЯ НЕТ (решение владельца п. 3г, 2026-08-24): главное
    место отдано цифре, не вежливости. Состав справа воспроизводит
    эскиз буквально (.visual/finfocus-panel-dashboard/v3.html:415-418
    — аватар-эмодзи, имя, шестерёнка; приветствия в эскизе нет вовсе).
    Хелпер _build_greeting_text() из шапки НЕ вызывается — он удалён
    как мёртвый код вместе с элементом dashboard-greeting.

    Вердикта НЕТ (решение владельца п. 3а): ни чипа, ни сигнальной
    шины, ни оценочной подписи, ни окраски суммы по уровню. Сумма
    рендерится нейтральным цветом текста; единственное исключение —
    отрицательное значение показывается в цвете риска, потому что
    это факт знака числа, а не оценка состояния.

    При data['degraded'] под разбором добавляется нейтральная сноска
    «часть данных недоступна, показано без бюджета целей» — деградация
    обозначена, а не выдана за достоверную цифру.

    Не дверь-переход: на контейнере нет dcc.Link, n_clicks,
    cursor:pointer (FR-2.e).

    Args:
        data: Модель слоёв из MoneyLayersService.
        profile: Профиль (name, avatar_id) из OnboardingService —
            ЕДИНСТВЕННЫЙ источник имени и аватара в шапке. Второго
            чтения профиля за рендер нет: прежний путь через
            _build_greeting_text() открывал собственную сессию
            (critique-v3, №3) и снят вместе с приветствием.

    Returns:
        html.Div с классом pnl-breaker.
    """
    if data["is_empty"]:
        return _build_header_empty_state(profile)

    today = data["today"]
    amount_class = "pnl-amount pnl-money"
    if today["free"] < 0:
        amount_class += " pnl-negative"

    breakdown = [
        html.Span(["баланс ", html.B(format_rub(today["balance"]))]),
        html.Span("−", className="pnl-op"),
        html.Span(["платежи ", html.B(format_rub(today["payments"]))]),
        html.Span("−", className="pnl-op"),
        html.Span(["резерв ", html.B(format_rub(today["reserve"]))]),
    ]

    main_children = [
        html.Div("Свободно сегодня", className="pnl-tag"),
        html.Div(format_rub(today["free"]), className=amount_class),
        html.Div(breakdown, className="pnl-breakdown"),
    ]

    if data["degraded"]:
        main_children.append(
            html.Div(
                "Часть данных недоступна, показано без бюджета целей",
                className="pnl-degraded-note",
            )
        )

    return html.Div(
        [
            html.Div(main_children, className="pnl-breaker-main"),
            _build_header_who(profile),
        ],
        className="pnl-breaker",
    )


def _axis_tickvals(window_dates: list[date]) -> list[date]:
    """Явные даты подписей оси X — без спорных единиц dtick.

    Берёт каждый k-й день окна, где
        k = max(1, ceil(len(window_dates) / MAX_X_TICKS)).
    Для 45 дней k = 5 → индексы 0, 5, …, 40 → 9 подписей, плюс
    принудительно добавляется window_end (последний день окна должен
    быть подписан) → 10. Число подписей НИКОГДА не превышает
    MAX_X_TICKS (critique-v3, замечание №5: прежняя формула
    round(45/11) = 4 давала 12 подписей при константе с именем
    TARGET_X_TICKS = 11 — имя обещало результат, которого функция
    не давала). Константа переименована в MAX_X_TICKS, семантика —
    потолок, и ceil делает потолок соблюдаемым по построению.

    Точное воспроизведение эскиза невозможно и не является целью:
    в v3.html 11 подписей с НЕРАВНОМЕРНЫМ шагом (семантически
    значимые даты, а не сетка). Воспроизводима только плотность
    подписей, и её честнее ограничить сверху.

    Args:
        window_dates: Дни окна по возрастанию.

    Returns:
        list[date]: Даты подписей; первая — reference_date,
            последняя — window_end, дублей нет.
    """
    if not window_dates:
        return []

    step = max(1, ceil(len(window_dates) / MAX_X_TICKS))
    ticks = window_dates[::step]

    # Правый край окна обязан быть подписан — но только если он
    # не попал в сетку сам (иначе дубль подписи на коротком окне).
    # Если сетка уже упёрлась в потолок, край ЗАМЕНЯЕТ её последнюю
    # подпись, а не добавляется сверх MAX_X_TICKS (протокол 0029:
    # при len, кратной MAX_X_TICKS, сетка даёт ровно MAX_X_TICKS
    # подписей и прежний append пробивал потолок)
    if window_dates[-1] not in ticks:
        if len(ticks) >= MAX_X_TICKS:
            ticks[-1] = window_dates[-1]
        else:
            ticks.append(window_dates[-1])

    return ticks


def _build_payments_tooltip(data: MoneyLayersData) -> list:
    """Содержимое тултипа легенды «Платежи» — конкретные операции (AC-4).

    Пользовательские описания вставляются ТОЛЬКО как текст внутри
    html.Div: dangerously_allow_html и dcc.Markdown в этом пути
    запрещены.

    Args:
        data: Модель слоёв.

    Returns:
        list: Строки тултипа.
    """
    payments = [
        payment
        for payment in data["upcoming_payments"]
        if payment["date"] <= data["payments_end"]
    ]

    if not payments:
        return [html.Div("До конца месяца платежей больше нет")]

    rows: list = [html.Div("Ближайшие платежи до конца месяца:")]
    for payment in payments[:MAX_TOOLTIP_PAYMENTS]:
        title = payment["description"] or payment["category_name"] or "Операция"
        prefix = "🔁 " if payment["is_recurring"] else ""
        rows.append(
            html.Div(
                f"{prefix}{title} · {format_date_human(payment['date'])} · "
                f"{format_rub(payment['amount'])}"
            )
        )

    hidden = len(payments) - MAX_TOOLTIP_PAYMENTS
    if hidden > 0:
        rows.append(html.Div(f"…и ещё {hidden}"))

    return rows


def _build_reserve_tooltip(data: MoneyLayersData) -> list:
    """Содержимое тултипа легенды «Резерв» — ФАКТ дня (решение владельца п. 3б).

    Цифра тултипа всегда равна высоте полосы: если остатка меньше
    настроенного резерва, тултип объясняет сжатие, а не утверждает
    настройку, которой в остатке нет.

    Args:
        data: Модель слоёв.

    Returns:
        list: Строки тултипа.
    """
    if data["degraded"]:
        return [
            html.Div("Часть данных недоступна — состав резерва показан не полностью")
        ]

    fact = data["today"]["reserve"]
    configured = data["reserve_configured_today"]

    if fact < configured:
        return [
            html.Div(
                f"В этот день на резерв остаётся {format_rub(fact)} "
                f"из {format_rub(configured)} — вы залезаете в подушку"
            )
        ]

    return [
        html.Div(
            f"Порог подушки {format_rub(data['cushion_threshold'])} + "
            f"бюджет целей {format_rub(data['goals_reserve_today'])}"
        )
    ]


def _build_layer_legend(data: MoneyLayersData) -> html.Div:
    """HTML-легенда вне поля графика с тултипами-пояснениями (FR-4).

    Легенда Plotly отключена (showlegend=False): нужны развёрнутые
    пояснения и доступность с клавиатуры — элементы получают
    tabIndex=0, тултипы срабатывают на hover и focus.

    Args:
        data: Модель слоёв.

    Returns:
        html.Div с классом pnl-legend.
    """
    tooltips = {
        "free": [html.Div("Остаток минус платежи до конца месяца и резерв")],
        "payments": _build_payments_tooltip(data),
        "reserve": _build_reserve_tooltip(data),
    }

    items: list = []
    for key in ("free", "payments", "reserve"):
        element_id = f"pnl-legend-{key}"
        items.append(
            html.Span(
                [
                    html.Span(
                        className=f"pnl-legend-swatch pnl-legend-swatch-{key}",
                    ),
                    html.Span(LAYER_LABELS[key]),
                ],
                id=element_id,
                className="pnl-legend-item",
                tabIndex=0,
            )
        )
        items.append(
            dbc.Tooltip(
                tooltips[key],
                target=element_id,
                trigger="hover focus",
                placement="top",
            )
        )

    return html.Div(items, className="pnl-legend")


def _build_chart_empty_state() -> html.Div:
    """Пустое состояние графика — БЕЗ вызова Plotly (AC-5).

    Отдаёт html.Div вместо dcc.Graph: Plotly не вызывается вовсе,
    поэтому выродившиеся оси −1..1 и подписи вида «50.001k»
    физически невозможны.

    Returns:
        html.Div с текстом и подсказкой.
    """
    return html.Div(
        [
            html.Div("График появится с первой операцией", className="pnl-empty-title"),
            html.Div(
                "Добавьте операцию или сверьте баланс — и здесь появится "
                "разбор ваших денег на 45 дней вперёд",
                className="pnl-empty-hint",
            ),
        ],
        className="pnl-empty py-4",
    )


def build_layers_chart(data: MoneyLayersData) -> dbc.Card:
    """График полос: стопка Свободно/Платежи/Резерв по 45 дням (FR-3).

    Три go.Bar в barmode="stack" (снизу вверх: free, payments, reserve)
    по датам оси X, вертикальная линия «сегодня», маркер минимума слоя
    «Свободно» (data['min_free_date']), вехи целей аннотациями (в окне +
    стрелка за краем). Легенда Plotly отключена (showlegend=False) —
    вынесена в HTML (заметка vision-критика + FR-4).

    Args:
        data: Модель слоёв из MoneyLayersService.

    Returns:
        dbc.Card с dcc.Graph(id="dashboard-layers-chart-graph") либо
        пустым состоянием при data['is_empty'] (FR-6).
    """
    head = html.Div(
        [
            html.H2("Ваши деньги на 45 дней вперёд"),
            html.Span(
                f"по {format_date_human(data['window_end'])}",
                className="pnl-meter-hint",
            ),
        ],
        className="pnl-meter-head",
    )

    if data["is_empty"]:
        return dbc.Card(
            dbc.CardBody([head, _build_chart_empty_state()]),
            className="pnl-meter",
        )

    dates = [day["date"] for day in data["days"]]
    fig = go.Figure()

    # Порядок трасс снизу вверх: свободно → платежи → резерв
    for key in ("free", "payments", "reserve"):
        fig.add_trace(
            go.Bar(
                x=dates,
                y=[float(day[key]) for day in data["days"]],
                name=LAYER_LABELS[key],
                marker_color=LAYER_COLORS[key],
                customdata=[format_rub(day[key]) for day in data["days"]],
                hovertemplate=f"{LAYER_LABELS[key]}: %{{customdata}}<extra></extra>",
            )
        )

    # Линия «сегодня» — левый край окна
    fig.add_shape(
        type="line",
        x0=data["reference_date"],
        x1=data["reference_date"],
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="#7f8c8d", width=1.5, dash="dash"),
    )
    fig.add_annotation(
        x=data["reference_date"],
        y=1,
        yref="paper",
        text="сегодня",
        showarrow=False,
        yshift=12,
        font=dict(size=11, color="#7f8c8d"),
    )

    # Маркер минимума «Свободно» — со сдвигом, чтобы не липнуть к тику даты
    fig.add_trace(
        go.Scatter(
            x=[data["min_free_date"]],
            y=[float(data["min_free"])],
            mode="markers",
            marker=dict(
                symbol="diamond",
                size=11,
                color=LAYER_COLORS["free"],
                line=dict(width=2, color="white"),
            ),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_annotation(
        x=data["min_free_date"],
        y=float(data["min_free"]),
        text=f"минимум: {format_rub(data['min_free'])}",
        showarrow=True,
        arrowhead=0,
        arrowcolor="#7f8c8d",
        ax=0,
        ay=-32,
        font=dict(size=11, color=LAYER_COLORS["free"]),
        bgcolor="rgba(255,255,255,0.85)",
    )

    # Вехи целей: внутри окна — подписи у оси, за краем — стрелка справа
    for milestone in data["milestones"]:
        if milestone["beyond_window"]:
            fig.add_annotation(
                x=data["window_end"],
                y=1,
                yref="paper",
                text=f"→ {milestone['name']} "
                f"({format_date_human(milestone['target_date'])})",
                showarrow=False,
                xanchor="right",
                yshift=12,
                font=dict(size=11, color=LAYER_COLORS["reserve"]),
            )
        else:
            fig.add_annotation(
                x=milestone["target_date"],
                y=0,
                yref="paper",
                text=f"🏁 {milestone['name']}",
                showarrow=False,
                yshift=-26,
                font=dict(size=11, color=LAYER_COLORS["reserve"]),
            )

    fig.update_layout(
        barmode="stack",
        height=340,
        margin=dict(l=50, r=30, t=34, b=48),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        showlegend=False,
        bargap=0.15,
        xaxis=dict(
            type="date",
            tickmode="array",
            tickvals=_axis_tickvals(dates),
            tickformat="%-d %b",
            tickangle=0,
            showgrid=False,
        ),
        yaxis=dict(
            rangemode="tozero",
            tickformat=",.0f",
            separatethousands=True,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            title=None,
        ),
    )

    return dbc.Card(
        dbc.CardBody(
            [
                head,
                _build_layer_legend(data),
                dcc.Graph(
                    id="dashboard-layers-chart-graph",
                    figure=fig,
                    config={"displayModeBar": False},
                ),
            ]
        ),
        className="pnl-meter",
    )


def create_dashboard_layout():
    """Создает layout главной страницы дашборда."""
    return html.Div(
        [
            # Hidden elements (не участвуют в flex layout)
            dcc.Store(
                id="dashboard-period",
                data={"period": "month"},
            ),
            _build_balance_banner(),
            # Visible flex container
            html.Div(
                [
                    # Шапка-щиток: «Свободно сегодня» + профиль + сверка
                    html.Div(
                        id="dashboard-free-header",
                        children=html.Div("Загрузка...", className="text-muted p-4"),
                    ),
                    # График полос — во всю ширину щитка
                    html.Div(id="dashboard-layers-chart"),
                    # Ряд карточек-дверей (FR-1/FR-2): пять фрагментов
                    # разделов, строится build_cards_row из PanelData
                    html.Div(id="dashboard-cards-row"),
                ],
                className="db-page",
            ),
        ]
    )


# =============================================================================
# Dynamic Build Functions (строят UI из данных)
# =============================================================================


# =============================================================================
# Daily / Yearly Cashflow Charts
# =============================================================================


def _load_dashboard_components(period_state: dict | None) -> tuple:
    """Единая точка загрузки данных и построения UI щитка.

    Используется и в load_dashboard_data, и в refresh_dashboard_after_crud.
    Одно чтение профиля и ОДИН сбор PanelData за рендер (FR-6): шапка,
    график и карточки-двери питаются одной моделью, поэтому разойтись
    не могут (AC-3). Сессия на пути сборки щитка одна (было 3 до
    куска 2: сборка компонентов, readonly-подушка, wishlist-виджет
    из layout).

    Параметра period больше нет: переключатель Месяц/Год снят вместе
    со старым графиком, а Store dashboard-period остался в layout лишь
    как guard для клика по столбцу — писателя у него нет, и мёртвый
    аргумент всегда получал бы дефолт.

    Args:
        period_state: Данные из dcc.Store (сохранены для совместимости
            вызовов; на состав щитка не влияют).

    Returns:
        Tuple: (free_header, layers_chart, cards_row)
    """
    with get_db_session() as session:
        profile = OnboardingService(session).get_profile(DEFAULT_USER_ID)
        panel = DashboardPanelService(session).get_panel_data(DEFAULT_USER_ID)

    free_header = build_free_header(panel["layers"], profile)
    layers_chart = build_layers_chart(panel["layers"])
    cards_row = build_cards_row(panel)

    return free_header, layers_chart, cards_row


# =============================================================================
# Callbacks
# =============================================================================


@callback(
    [
        Output("dashboard-free-header", "children"),
        Output("dashboard-layers-chart", "children"),
        Output("dashboard-cards-row", "children"),
    ],
    [
        Input("url", "pathname"),
        Input("profile-updated", "data"),
    ],
    [State("dashboard-period", "data")],
)
def load_dashboard_data(
    pathname: str,
    profile_updated: float | None,
    period_state: dict | None,
):
    """Загружает щиток при навигации или обновлении профиля.

    Триггер profile-updated нужен, чтобы онбординг/правка профиля
    применялись без перезагрузки страницы: от starting_balance зависят
    числа щитка, от имени и аватара — правый угол шапки. Приветствия
    больше нет (решение владельца п. 3г) — имя и аватар обновляются
    первым Output'ом, шапкой.
    """
    # Guard #1: только для страницы dashboard
    if pathname not in ["/", "/dashboard"]:
        raise PreventUpdate

    try:
        return _load_dashboard_components(period_state)
    except Exception:
        logger.opt(exception=True).error("Ошибка загрузки дашборда")
        error_alert = dbc.Alert(
            "Не удалось загрузить данные. Попробуйте обновить страницу.",
            color="danger",
        )
        return (error_alert,) * 3


@callback(
    [
        Output("dashboard-free-header", "children", allow_duplicate=True),
        Output("dashboard-layers-chart", "children", allow_duplicate=True),
        Output("dashboard-cards-row", "children", allow_duplicate=True),
    ],
    Input("global-transaction-trigger", "data"),
    [State("dashboard-period", "data"), State("url", "pathname")],
    prevent_initial_call=True,
)
def refresh_dashboard_after_crud(
    trigger: dict | None,
    period_state: dict | None,
    pathname: str,
):
    """Обновляет щиток после CRUD операции с транзакцией."""
    # Guard #1: проверяем наличие триггера
    if not trigger:
        raise PreventUpdate

    # Guard #2: обновляем только если мы на странице dashboard
    if pathname not in ["/", "/dashboard"]:
        raise PreventUpdate

    try:
        result = _load_dashboard_components(period_state)
        source = trigger.get("source", "unknown")
        action = trigger.get("action", "unknown")
        logger.debug(f"Dashboard обновлен после {action} из {source}")
        return result
    except Exception:
        logger.opt(exception=True).error("Ошибка обновления дашборда после CRUD")
        raise PreventUpdate


@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("preselected-date", "data", allow_duplicate=True),
        Output("modal-source", "data", allow_duplicate=True),
    ],
    Input("dashboard-layers-chart-graph", "clickData"),
    State("dashboard-period", "data"),
    prevent_initial_call=True,
)
def open_create_from_chart(click_data, period_state):
    """Открывает модал создания операции при клике на столбец графика полос.

    Ось X графика — даты (type="date"), поэтому point["x"] приходит
    ISO-строкой, а не номером дня: собирать дату из года и месяца Store,
    как делал прежний график, больше не нужно и нельзя — окно щитка
    пересекает границы месяцев.
    """
    # Guard #1: нет клика
    if click_data is None:
        raise PreventUpdate

    # Guard #2: страница дашборда активна (Store живёт в её layout)
    if not period_state:
        raise PreventUpdate

    try:
        point = click_data["points"][0]
        clicked_date = date.fromisoformat(str(point["x"])[:10])
        return True, clicked_date.isoformat(), "chart"
    except (KeyError, IndexError, ValueError):
        raise PreventUpdate


@callback(
    Output("balance-alert-toast", "is_open"),
    [
        Input("url", "pathname"),
        Input("balance-alert-toast", "is_open"),
        Input("profile-updated", "data"),
    ],
    State("balance-toast-dismissed", "data"),
    prevent_initial_call=False,
)
def toggle_balance_toast(
    pathname: str | None,
    is_open: bool,
    profile_updated: float | None,
    is_dismissed: bool,
) -> bool:
    """Показывает Toast если balance=0 и не dismissed.

    Пересчитывается и при обновлении профиля (profile-updated).
    """
    triggered_id = ctx.triggered_id

    # При закрытии через крестик
    if triggered_id == "balance-alert-toast" and not is_open:
        return False

    # При загрузке Dashboard
    if pathname == "/dashboard" or pathname == "/":
        if is_dismissed:
            return False

        try:
            with get_db_session() as session:
                service = OnboardingService(session)
                status = service.get_status(DEFAULT_USER_ID)

            return status["needs_balance_alert"]

        except Exception:
            return False

    return no_update


@callback(
    Output("balance-toast-dismissed", "data"),
    Input("balance-alert-toast", "is_open"),
    State("balance-toast-dismissed", "data"),
    prevent_initial_call=True,
)
def persist_toast_dismissal(is_open: bool, current: bool) -> bool:
    """Запоминает закрытие Toast до перезагрузки."""
    if not is_open and not current:
        return True
    return no_update


# Clientside callbacks для динамически рендеренных элементов.
# JS функции определены в assets/clientside_triggers.js (namespace: triggers).
# Clientside + prevent_initial_call=True обходит ReferenceError для элементов,
# которых нет в начальном DOM (KPI карточки, empty state кнопки).

# Кнопка "Сверка" в шапке щитка → open-recon-trigger
clientside_callback(
    ClientsideFunction("triggers", "timestamp_trigger"),
    Output("open-recon-trigger", "data", allow_duplicate=True),
    Input("open-recon-from-dashboard-header-btn", "n_clicks"),
    prevent_initial_call=True,
)

# Шестерёнка в шапке щитка → open-profile-trigger (модал профиля).
# Элемент рождается динамически внутри dashboard-free-header, поэтому
# прямой Input в profile_modal сломал бы callback на всех страницах,
# где шестерёнки нет в DOM (в т.ч. вход через аватар в сайдбаре).
clientside_callback(
    ClientsideFunction("triggers", "timestamp_trigger"),
    Output("open-profile-trigger", "data", allow_duplicate=True),
    Input("dashboard-settings-cog", "n_clicks"),
    prevent_initial_call=True,
)

# Кнопка "Сверка" в пустом состоянии шапки → open-recon-trigger
clientside_callback(
    ClientsideFunction("triggers", "timestamp_trigger"),
    Output("open-recon-trigger", "data", allow_duplicate=True),
    Input("open-recon-from-dashboard-empty-btn", "n_clicks"),
    prevent_initial_call=True,
)

# Кнопка "Сверить баланс" в баннере → open-recon-trigger
clientside_callback(
    ClientsideFunction("triggers", "timestamp_trigger"),
    Output("open-recon-trigger", "data", allow_duplicate=True),
    Input("open-recon-from-dashboard-banner-btn", "n_clicks"),
    prevent_initial_call=True,
)

# Тело двери Wishlist (уровень 1) → open-wishlist-trigger (модал управления).
# Элемент рождается динамически внутри dashboard-cards-row — тот же
# паттерн Store-триггера, что у шестерёнки выше (урок протокола 0028):
# прямой Input сломал бы open_wishlist_modal на страницах без двери.
clientside_callback(
    ClientsideFunction("triggers", "timestamp_trigger"),
    Output("open-wishlist-trigger", "data", allow_duplicate=True),
    Input("panel-wishlist-door", "n_clicks"),
    prevent_initial_call=True,
)
