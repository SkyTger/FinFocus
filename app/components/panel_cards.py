"""Карточки-двери щитка (EPIC-11, кусок 2, FR-1/FR-2/FR-5).

Чистые build-функции: принимают срезы PanelData, возвращают Dash-дерево.
О БД и сервисах не знают. Ни одна карточка не заводит серверный Input —
переходы делает сам dcc.Link, поэтому класс регрессий C-6 (колбэк на
условно присутствующий элемент) не создаётся вообще. Единственный
интерактивный не-ссылочный элемент — слой-подложка двери Wishlist
(id="panel-wishlist-door"), его обслуживает clientside-триггер через
Store (паттерн проекта, шаги 6-7 протокола).
"""

from dash import dcc, html

from app.schema import (
    AnalyticsCardData,
    CalendarCardData,
    CalendarDaySlice,
    CardStatus,
    GoalsCardData,
    OperationRow,
    OperationsCardData,
    PanelData,
    WishlistCardData,
)
from app.utils.formatters import format_date_human, format_rub

_MINUS = "−"  # типографский минус, как в format_rub

_REST_COLOR = "#dfe6ea"
"""Цвет незакрытого остатка мини-полоски структуры (эскиз v3)."""


def _format_signed(row: OperationRow) -> tuple[str, str]:
    """Сумма операции со знаком по kind: (текст, css-класс).

    kind управляет и знаком, и цветом (TRANSACTION_KIND_MAP):
    expense → «−X ₽» красным, income → «+X ₽» зелёным,
    other → «X ₽» нейтрально (знак не определён семантикой типа).
    """
    amount_text = format_rub(row["amount"])
    if row["kind"] == "expense":
        return f"{_MINUS}{amount_text}", "pnl-op-neg"
    if row["kind"] == "income":
        return f"+{amount_text}", "pnl-op-pos"
    return amount_text, ""


def _door_shell(
    slot: str,
    icon: str,
    title: str,
    body: list,
    href: str | None = None,
) -> html.Div:
    """Каркас двери: цветная шина гнезда, заголовок, тело.

    Заголовок — dcc.Link, если href задан: переход делает браузер,
    серверных Input у двери нет (C-6 неуязвим по построению).
    """
    head_children = [
        html.Span(icon, className="pnl-door-ico", **{"aria-hidden": "true"}),
        html.Span(title, className="pnl-door-title"),
        html.Span("→", className="pnl-door-chev", **{"aria-hidden": "true"}),
    ]
    if href:
        head = dcc.Link(head_children, href=href, className="pnl-door-head")
    else:
        head = html.Div(head_children, className="pnl-door-head")

    return html.Div(
        [head, html.Div(body, className="pnl-door-body")],
        className=f"pnl-door pnl-door-{slot}",
    )


def _failed_body(section_hint: str) -> list:
    """Тело карточки при FAILED: индикация без чисел, дверь остаётся.

    Ссылка-дверь в заголовке продолжает работать — находимость раздела
    не теряется (FR-2), см. таблицу обработки ошибок solution-v4.
    """
    return [
        html.Div(
            [
                html.Span("⚠", className="pnl-door-warn-ico"),
                html.Span("Не удалось загрузить раздел"),
            ],
            className="pnl-door-failed",
        ),
        html.Div(section_hint, className="pnl-door-empty-hint"),
    ]


def _empty_body(text: str, hint: str | None = None) -> list:
    """Тело карточки при EMPTY: смысл раздела без числовых артефактов (AC-5).

    Текст пустого состояния живёт ЗДЕСЬ, в build-функции, а не в данных:
    status — единственный источник правды отрисовки (RTM #81, #96).
    """
    children = [html.Div(text, className="pnl-door-empty")]
    if hint:
        children.append(html.Div(hint, className="pnl-door-empty-hint"))
    return children


def _build_day_window(day: CalendarDaySlice) -> dcc.Link:
    """Окошко дня — dcc.Link на календарь с фокусом дня (FR-3, AC-2)."""
    css = "pnl-day pnl-day-today" if day["is_today"] else "pnl-day"
    children = [
        html.Div(day["label"], className="pnl-day-lab"),
        html.Div(format_date_human(day["date"]), className="pnl-day-date"),
        html.Div(
            format_rub(day["balance"]),
            className="pnl-day-sum pnl-money",
        ),
        html.Div(
            f"свободно {format_rub(day['free'])}",
            className="pnl-day-free pnl-money",
        ),
    ]
    if day["operations_note"]:
        children.append(html.Div(day["operations_note"], className="pnl-day-note"))
    return dcc.Link(children, href=day["href"], className=css)


def build_calendar_card(data: CalendarCardData) -> html.Div:
    """Карточка «Календарь»: сегодня / завтра + маркер просадки.

    Окошек два (решение владельца 2026-08-26, «вчера» убрано); каждое —
    dcc.Link на /calendar?focus_date=<ISO> (FR-3, AC-2).

    Маркер просадки (AC-7) рисуется ТОЛЬКО при status == OK
    (critique-v2, №10). Причина — в теле источника: _window_min_free
    при пустом days возвращает (Decimal("0"), date.today()), а НЕ
    (0, None). Без этой оговорки на чистой базе появилось бы
    «Ближайшая просадка: сегодня, остаток 0 ₽» — числовой артефакт,
    прямо запрещённый AC-5. При status EMPTY/FAILED поля dip_*
    игнорируются целиком, даже если непустые.

    При dip_free <= 0 маркер получает класс pnl-flagline-strong:
    усиление привязано к факту знака числа — порога-вердикта нет
    и константы-порога тоже нет (решение владельца 2026-08-25).
    """
    if data["status"] == CardStatus.FAILED:
        body = _failed_body("Календарь доступен по заголовку карточки")
    elif data["status"] == CardStatus.EMPTY:
        body = _empty_body(
            "Здесь будет прогноз остатка на сегодня и завтра",
            "Добавьте первую операцию — календарь построит прогноз",
        )
    else:
        body = [
            html.Div(
                [_build_day_window(day) for day in data["days"]],
                className="pnl-days",
            )
        ]
        if data["dip_date"] is not None and data["dip_free"] is not None:
            flag_css = "pnl-flagline"
            if data["dip_is_strong"]:
                flag_css += " pnl-flagline-strong"
            body.append(
                dcc.Link(
                    [
                        html.Span(
                            "⚠",
                            className="pnl-flag-ico",
                            **{"aria-hidden": "true"},
                        ),
                        html.Span(
                            [
                                "Ближайшая просадка: ",
                                html.B(format_date_human(data["dip_date"])),
                                ", остаток ",
                                html.B(
                                    format_rub(data["dip_free"]),
                                    className="pnl-money",
                                ),
                            ]
                        ),
                    ],
                    href=data["dip_href"],
                    className=flag_css,
                )
            )

    return _door_shell("calendar", "📅", "Календарь", body, href="/calendar")


def build_goals_card(data: GoalsCardData) -> html.Div:
    """Карточка «Цели»: топ-цель + сводка + подушка одной строкой (AC-4).

    Топ-цель — dcc.Link на /goals?goal=<id> (FR-3). Блок подушки
    прижат к низу карточки (класс pnl-goal-pillow с margin-top:auto) —
    заметка vision-критика эскиза про вертикальный ритм (RTM #66).
    Отдельной карточки подушки в ряду нет — только строка здесь (AC-4).
    """
    if data["status"] == CardStatus.FAILED:
        body = _failed_body("Цели доступны по заголовку карточки")
    elif data["status"] == CardStatus.EMPTY:
        body = _empty_body(
            "Целей пока нет",
            "Заведите первую цель — здесь появится её прогресс",
        )
    else:
        body = []
        if data["top_goal_id"] is not None:
            progress = data["top_goal_progress"]
            sub_parts = [
                html.Span(
                    format_rub(data["top_goal_current"]),
                    className="pnl-money",
                ),
                " из ",
                html.Span(
                    format_rub(data["top_goal_target"]),
                    className="pnl-money",
                ),
            ]
            if data["top_goal_target_date"] is not None:
                sub_parts.append(
                    f" · к {format_date_human(data['top_goal_target_date'])}"
                )
            body.append(
                dcc.Link(
                    [
                        html.Div(
                            [
                                html.Span(
                                    data["top_goal_name"],
                                    className="pnl-goal-name",
                                ),
                                html.Span(
                                    f"{progress:.0f}%",
                                    className="pnl-goal-pct pnl-money",
                                ),
                            ],
                            className="pnl-goal-top",
                        ),
                        html.Div(
                            html.I(style={"width": f"{min(progress, 100)}%"}),
                            className="pnl-bar",
                        ),
                        html.Div(sub_parts, className="pnl-goal-sub"),
                    ],
                    href=data["top_goal_href"],
                    className="pnl-goal-link",
                )
            )
        if data["others_count"] > 0:
            goals_word = (
                "цель"
                if data["others_count"] == 1
                else ("цели" if data["others_count"] < 5 else "целей")
            )
            body.append(html.Div(className="pnl-rule"))
            body.append(
                html.Div(
                    [
                        html.Span(
                            f"Ещё {data['others_count']} {goals_word}",
                            className="pnl-line-k",
                        ),
                        html.Span(
                            data["others_summary"],
                            className=(
                                "pnl-line-v pnl-op-pos"
                                if data["others_behind_count"] == 0
                                else "pnl-line-v pnl-op-neg"
                            ),
                        ),
                    ],
                    className="pnl-line",
                )
            )
        if data["cushion_is_configured"]:
            body.append(
                html.Div(
                    [
                        html.Div(
                            [
                                html.Span("Подушка", className="pnl-line-k"),
                                html.Span(
                                    data["cushion_label"],
                                    className="pnl-line-v pnl-money",
                                ),
                            ],
                            className="pnl-line pnl-pillow",
                        ),
                        html.Div(
                            html.I(
                                style={
                                    "width": f"{min(data['cushion_progress'], 100)}%"
                                }
                            ),
                            className="pnl-bar pnl-bar-thin",
                        ),
                    ],
                    className="pnl-goal-pillow",
                )
            )

    return _door_shell("goals", "🎯", "Цели", body, href="/goals")


def _build_operation_line(row: OperationRow) -> html.Div:
    """Строка операции: название · дата — сумма со знаком по kind."""
    amount_text, amount_css = _format_signed(row)
    title_children: list = [row["title"]]
    if row["is_recurring"]:
        title_children.append(
            html.Span(
                " 🔁",
                className="pnl-op-rec",
                **{"aria-label": "регулярная"},
            )
        )
    title_children.append(f" · {format_date_human(row['date'])}")
    return html.Div(
        [
            html.Span(title_children, className="pnl-line-k"),
            html.Span(
                amount_text,
                className=f"pnl-line-v pnl-money {amount_css}".strip(),
            ),
        ],
        className="pnl-line",
    )


def build_operations_card(data: OperationsCardData) -> html.Div:
    """Карточка «Операции»: 2-3 недавние + 2-3 предстоящие (FR-1.c).

    Заголовки групп — dcc.Link на /transactions с ТЕМИ ЖЕ диапазонами,
    по которым источник отбирал строки (FR-6): recent — [1-е число,
    сегодня], upcoming — [сегодня, конец месяца].

    Показываются только материализованные операции — виртуальные
    инстансы регулярных платежей сюда не попадают (решение владельца
    2026-08-25, см. докстринг OperationsCardData). Маркер 🔁 — у
    материализованных recurring-инстансов.
    """
    if data["status"] == CardStatus.FAILED:
        body = _failed_body("Операции доступны по заголовку карточки")
    elif data["status"] == CardStatus.EMPTY:
        body = _empty_body(
            "Операций в этом месяце нет",
            "Добавьте первую — она появится здесь",
        )
    else:
        body = []
        if data["recent"]:
            body.append(
                dcc.Link("Недавние", href=data["recent_href"], className="pnl-grp")
            )
            body.extend(_build_operation_line(row) for row in data["recent"])
        if data["recent"] and data["upcoming"]:
            body.append(html.Div(className="pnl-rule"))
        if data["upcoming"]:
            body.append(
                dcc.Link(
                    "Предстоящие",
                    href=data["upcoming_href"],
                    className="pnl-grp",
                )
            )
            body.extend(_build_operation_line(row) for row in data["upcoming"])

    return _door_shell("operations", "🧾", "Операции", body, href=data["recent_href"])


def build_analytics_card(data: AnalyticsCardData) -> html.Div:
    """Карточка «Аналитика»: цифра месяца + топ-категория + мини-структура.

    Подпись под цифрой — не просто «расходы августа», а
    «расходы августа · без регулярных и взносов в цели» (мелким
    кеглем, .pnl-note). Это ОБЪЯВЛЕНИЕ расхождения с месячным слоем
    «Платежи» графика над карточкой, а не извинение — оформлено
    симметрично ограничению карточки «Операции» (решение владельца
    2026-08-25). См. докстринг AnalyticsCardData.

    Мини-структура — CSS-полоска, без Plotly (RTM #70).
    """
    if data["status"] == CardStatus.FAILED:
        body = _failed_body("Аналитика доступна по заголовку карточки")
    elif data["status"] == CardStatus.EMPTY:
        body = _empty_body(
            f"Расходы {data['month_label']} появятся здесь",
            "Добавьте расходы с категориями — карточка покажет структуру",
        )
    else:
        body = [
            html.Div(
                [
                    html.Div(
                        format_rub(data["month_total"]),
                        className="pnl-big-sum pnl-money",
                    ),
                    html.Div(
                        f"расходы {data['month_label']}"
                        " · без регулярных и взносов в цели",
                        className="pnl-note",
                    ),
                ]
            ),
            html.Div(className="pnl-rule"),
        ]
        if data["top_category_name"] is not None:
            body.append(
                html.Div(
                    [
                        html.Span(
                            data["top_category_name"],
                            className="pnl-top-cat-name",
                        ),
                        html.Span(
                            f"{format_rub(data['top_category_total'])}"
                            f" · {data['top_category_share']:.0f}%",
                            className="pnl-top-cat-val pnl-money",
                        ),
                    ],
                    className="pnl-top-cat",
                )
            )
            body.append(html.Div("крупнейшая категория месяца", className="pnl-note"))
        if data["structure"]:
            covered = sum(slice_["share"] for slice_ in data["structure"])
            segments = [
                html.Div(
                    style={
                        "width": f"{slice_['share']}%",
                        "background": slice_["color"],
                    },
                    className="pnl-mini-seg",
                )
                for slice_ in data["structure"]
            ]
            if covered < 100:
                segments.append(
                    html.Div(
                        style={
                            "width": f"{100 - covered}%",
                            "background": _REST_COLOR,
                        },
                        className="pnl-mini-seg",
                    )
                )
            legend = [
                html.Span(
                    [
                        html.Span(
                            className="pnl-mini-dot",
                            style={"background": slice_["color"]},
                        ),
                        f"{slice_['name']} {slice_['share']:.0f}%",
                    ],
                    className="pnl-mini-leg-item",
                )
                for slice_ in data["structure"]
            ]
            body.append(
                html.Div(
                    [
                        html.Div(segments, className="pnl-mini-bar"),
                        html.Div(
                            legend
                            + [
                                html.Span(
                                    f"из {format_rub(data['month_total'])}",
                                    className="pnl-mini-total pnl-money",
                                )
                            ],
                            className="pnl-mini-legend",
                        ),
                    ],
                    className="pnl-mini-slot",
                )
            )

    return _door_shell("analytics", "📊", "Аналитика", body, href=data["href"])


def build_wishlist_card(data: WishlistCardData) -> html.Div:
    """Полоса «Wishlist» — двухуровневая дверь (FR-1.e, AC-8).

    Уровень 1: тело полосы открывает модал управления wishlist — через
    clientside timestamp_trigger в Store open-wishlist-trigger (паттерн
    проекта для динамических элементов); серверного Input на сам
    элемент нет.
    Уровень 2: каждая хотелка — dcc.Link на /calendar?wishlist_item=<id>:
    календарь в режиме покупок с фокусом на хотелке (механизм 0023).

    Разделение уровней — слоем-подложкой (ревью 0030, 3.5-m-fix):
    кликабельный узел уровня 1 (id="panel-wishlist-door") — НЕ контейнер
    полосы, а её первый ребёнок, absolute-слой на всю площадь
    (.pnl-wish-hitbox). Ссылки-хотелки лежат ПОВЕРХ него как соседи
    (z-index в CSS), а не дети — клику по хотелке физически нечем
    «всплыть» в кнопку модала. Когда id висел на контейнере, клик по
    хотелке открывал И календарь, И модал поверх него (React-события
    всплывают от вложенной ссылки к родителю; dcc.Link делает
    preventDefault, но не stopPropagation).

    Wishlist — полоса, а не дверь в гриде: иерархия определяет размер
    и позицию, но не факт присутствия (design.md, RTM #57); полоса
    присутствует всегда, как и карточки (FR-2).
    """
    children: list = [
        # Уровень 1 двери: слой-подложка под всей полосой (см. докстринг)
        html.Div(
            id="panel-wishlist-door",
            className="pnl-wish-hitbox",
            role="button",
            tabIndex="0",
        ),
        html.Span("Wishlist", className="pnl-wish-tag"),
    ]

    if data["status"] == CardStatus.FAILED:
        children.append(
            html.Span(
                "⚠ Не удалось загрузить список покупок",
                className="pnl-wish-note",
            )
        )
    elif data["status"] == CardStatus.EMPTY:
        children.append(
            html.Span(
                "Список покупок пуст — нажмите, чтобы добавить первую хотелку",
                className="pnl-wish-note",
            )
        )
    else:
        for item in data["items"]:
            item_children: list = [
                item["name"],
                html.Span(
                    item["amount_label"],
                    className="pnl-wish-price pnl-money",
                ),
            ]
            if item["is_planned"] and item["planned_date_label"]:
                item_children.append(
                    html.Span(
                        f"к {item['planned_date_label']}",
                        className="pnl-wish-planned",
                    )
                )
            children.append(
                dcc.Link(
                    item_children,
                    href=item["href"],
                    className="pnl-wish-item",
                )
            )
        hidden_count = data["total_count"] - len(data["items"])
        if hidden_count > 0:
            children.append(
                html.Span(f"и ещё {hidden_count}", className="pnl-wish-note")
            )

    children.append(html.Span(className="pnl-wish-spacer"))
    children.append(html.Span("Управлять →", className="pnl-wish-manage"))

    return html.Div(children, className="pnl-wish")


def build_cards_row(data: PanelData) -> html.Div:
    """Ряд карточек-дверей (FR-1, FR-2).

    Все пять карточек присутствуют ВСЕГДА — конституция щитка (FR-2):
    и при пустых данных (FR-5), и при сбое блока (NFR-2) карточка
    остаётся на месте, меняется только содержимое.

    ЕДИНСТВЕННЫЙ ИСТОЧНИК ПРАВДЫ отрисовки карточки — её собственный
    data[<slot>]["status"] (решение владельца 2026-08-25: «каждая
    карточка честна сама за себя»). Общего признака пустоты в
    PanelData НЕТ и не будет: layers["is_empty"] — узкий критерий
    модели слоёв, и пользователь с заведёнными целями при is_empty=True
    обязан видеть их прогресс, а не «щиток в режиме первого запуска».
    """
    return html.Div(
        [
            html.Div(
                [
                    build_calendar_card(data["calendar"]),
                    build_goals_card(data["goals"]),
                    build_operations_card(data["operations"]),
                    build_analytics_card(data["analytics"]),
                ],
                className="pnl-slots",
            ),
            build_wishlist_card(data["wishlist"]),
        ]
    )
