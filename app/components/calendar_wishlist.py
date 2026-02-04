"""Wishlist-специфичная логика для календаря.

Содержит overlay-баннер, ячейки дней с safe/unsafe маркерами,
и сетку календаря в wishlist-mode.
"""

import calendar as cal_mod
from datetime import date
from decimal import Decimal

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, no_update
from dash.exceptions import PreventUpdate
from loguru import logger

from app.schema.wishlist import SafeDateInfo
from app.services import CalendarService, TransactionInfo
from app.utils.formatters import format_amount


def build_wishlist_overlay_banner(
    item_name: str,
    item_amount: str,
    safe_dates_map: dict[str, SafeDateInfo],
) -> html.Div:
    """Overlay-баннер для wishlist-mode в календаре.

    Args:
        item_name: Название покупки.
        item_amount: Форматированная сумма.
        safe_dates_map: Карта безопасности дат.

    Returns:
        html.Div: Баннер.
    """
    safe_count = sum(1 for v in safe_dates_map.values() if v["safe"])
    total_count = len(safe_dates_map)

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.I(className="bi bi-bag-heart me-2"),
                            html.Strong(item_name),
                            html.Span(f" — {item_amount}", className="ms-1"),
                        ],
                        className="d-flex align-items-center",
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-x-lg me-1"), "Отмена"],
                        id="cancel-wishlist-mode-btn",
                        color="light",
                        size="sm",
                    ),
                ],
                className="d-flex justify-content-between align-items-center mb-2",
            ),
            html.Div(
                [
                    html.Span(
                        [
                            html.Span(
                                "", className="wishlist-marker safe me-1"
                            ),
                            "Безопасно",
                        ],
                        className="me-3",
                    ),
                    html.Span(
                        [
                            html.Span(
                                "", className="wishlist-marker unsafe me-1"
                            ),
                            "Риск",
                        ],
                        className="me-3",
                    ),
                    html.Span(
                        f"{safe_count} из {total_count} дней безопасны",
                        className="text-muted small",
                    ),
                ],
                className="d-flex align-items-center",
            ),
        ],
        className="wishlist-overlay-banner p-3 mb-3",
    )


def build_wishlist_day_cell(
    day_date: date,
    balance: Decimal,
    transactions: list[TransactionInfo],
    safe_info: SafeDateInfo | None,
    is_today: bool = False,
    is_current_month: bool = True,
    is_weekend: bool = False,
    is_past: bool = False,
) -> html.Div:
    """Ячейка дня календаря в wishlist-mode.

    Args:
        day_date: Дата дня.
        balance: Баланс на этот день.
        transactions: Список транзакций дня.
        safe_info: Информация о безопасности (None для past days).
        is_today: Текущий день.
        is_current_month: День текущего месяца.
        is_weekend: Выходной.
        is_past: Прошлый день.

    Returns:
        html.Div: Ячейка дня.
    """
    css_classes = ["calendar-day", "wishlist-day"]

    if is_today:
        css_classes.append("calendar-day-today")
    if not is_current_month:
        css_classes.append("calendar-day-other-month")
    if is_weekend:
        css_classes.append("calendar-day-weekend")
    if is_past:
        css_classes.append("past-day-wishlist")

    # Safe/unsafe маркер
    if safe_info is not None:
        if safe_info["safe"]:
            css_classes.append("wishlist-day-safe")
        else:
            css_classes.append("wishlist-day-unsafe")

    # Tooltip для unsafe reasons
    title = ""
    if safe_info and not safe_info["safe"]:
        reason_texts = []
        for r in safe_info["reasons"]:
            if r == "negative_balance":
                reason_texts.append("Баланс уйдет в минус")
            elif r == "cushion":
                reason_texts.append("Ниже порога подушки")
        title = "; ".join(reason_texts)

    # Баланс с data-date атрибутом
    balance_el = html.Span(
        format_amount(balance),
        className="calendar-day-balance",
        **{"data-date": day_date.isoformat()},
    )

    # Транзакции дня (иконки)
    txn_icons = []
    for txn in transactions[:3]:
        icon_class = "bi-arrow-up-circle text-success" if txn.get("type") == "income" else "bi-arrow-down-circle text-danger"
        txn_icons.append(html.I(className=f"{icon_class} me-1", style={"fontSize": "0.7rem"}))

    cell_content = [
        html.Div(
            str(day_date.day),
            className="calendar-day-number",
        ),
        balance_el,
    ]

    if txn_icons:
        cell_content.append(
            html.Div(txn_icons, className="calendar-day-icons")
        )

    return html.Div(
        cell_content,
        className=" ".join(css_classes),
        title=title,
        id={"type": "wishlist-day-cell", "date": day_date.isoformat()},
    )


def build_wishlist_calendar_grid(
    month: int,
    year: int,
    balances: dict[date, Decimal],
    transactions: dict[date, list[TransactionInfo]],
    safe_dates_map: dict[str, SafeDateInfo],
) -> html.Div:
    """Календарная сетка в wishlist-mode.

    Args:
        month: Месяц (1-12).
        year: Год.
        balances: Балансы по дням.
        transactions: Транзакции по дням.
        safe_dates_map: Карта безопасности.

    Returns:
        html.Div: Сетка с CSS классом .wishlist-mode.
    """
    today = date.today()

    # Заголовок дней недели
    weekday_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    weekday_header = html.Div(
        [
            html.Div(name, className="calendar-weekday-header")
            for name in weekday_names
        ],
        className="calendar-weekday-row",
    )

    # Строим сетку по неделям
    first_day = date(year, month, 1)
    last_day_num = cal_mod.monthrange(year, month)[1]

    # Первый день недели (0=Пн)
    start_weekday = first_day.weekday()

    weeks = []
    current_week = []

    # Заполняем пустые ячейки до первого дня
    for _ in range(start_weekday):
        current_week.append(
            html.Div(className="calendar-day calendar-day-empty")
        )

    for day_num in range(1, last_day_num + 1):
        d = date(year, month, day_num)
        is_today = d == today
        is_weekend = d.weekday() >= 5
        is_past = d < today

        balance = balances.get(d, Decimal("0"))
        day_txns = transactions.get(d, [])
        safe_info = safe_dates_map.get(d.isoformat())

        cell = build_wishlist_day_cell(
            day_date=d,
            balance=balance,
            transactions=day_txns,
            safe_info=safe_info,
            is_today=is_today,
            is_current_month=True,
            is_weekend=is_weekend,
            is_past=is_past,
        )
        current_week.append(cell)

        if len(current_week) == 7:
            weeks.append(
                html.Div(current_week, className="calendar-week-row")
            )
            current_week = []

    # Заполняем оставшиеся ячейки
    while len(current_week) > 0 and len(current_week) < 7:
        current_week.append(
            html.Div(className="calendar-day calendar-day-empty")
        )

    if current_week:
        weeks.append(html.Div(current_week, className="calendar-week-row"))

    return html.Div(
        [weekday_header, *weeks],
        className="calendar-grid wishlist-mode",
    )


# === Callback ===


@callback(
    Output("wishlist-active-item", "data", allow_duplicate=True),
    Input("cancel-wishlist-mode-btn", "n_clicks"),
    prevent_initial_call=True,
)
def cancel_wishlist_mode(n_clicks):
    """Отменяет wishlist-mode в календаре."""
    if not n_clicks:
        raise PreventUpdate
    return None
