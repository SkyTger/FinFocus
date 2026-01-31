"""UI компонент кассового календаря."""

import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ALL, ctx, no_update
from dash.exceptions import PreventUpdate
from dateutil.relativedelta import relativedelta
from loguru import logger

from app.core.database import get_db_session
from app.core.exceptions import ValidationError
from app.services.calendar_service import CalendarService, TransactionInfo
from app.services.reconciliation_service import ReconciliationService


# ==================== КОНСТАНТЫ ====================

MONTH_NAMES_RU = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}

WEEKDAY_NAMES_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

WARNING_BALANCE_THRESHOLD = Decimal("5000")
MAX_MONTHS_OFFSET = 12


# ==================== УТИЛИТЫ СЕРИАЛИЗАЦИИ ====================


def serialize_balances(balances: dict[date, Decimal]) -> dict[str, str]:
    """Сериализует балансы для хранения в dcc.Store.

    Decimal не сериализуется в JSON, поэтому конвертируем в строки.

    Args:
        balances: {date: Decimal}

    Returns:
        dict[str, str]: {"YYYY-MM-DD": "12345.67", ...}
    """
    return {dt.isoformat(): str(balance) for dt, balance in balances.items()}


def deserialize_balances(data: dict[str, str] | None) -> dict[date, Decimal]:
    """Десериализует балансы из dcc.Store.

    Args:
        data: {"YYYY-MM-DD": "12345.67", ...} или None

    Returns:
        dict[date, Decimal]: {date: Decimal}
    """
    if not data:
        return {}
    return {
        date.fromisoformat(dt_str): Decimal(balance_str)
        for dt_str, balance_str in data.items()
    }


# ==================== ФУНКЦИИ ФОРМАТИРОВАНИЯ ====================


def format_balance(balance: Decimal) -> tuple[str, str]:
    """Форматирует баланс с определением CSS класса.

    Args:
        balance: Сумма баланса

    Returns:
        tuple: (отформатированная строка, CSS класс)
    """
    formatted = f"{balance:,.0f}".replace(",", " ")

    if balance < 0:
        return formatted, "balance-negative"
    elif balance < WARNING_BALANCE_THRESHOLD:
        return formatted, "balance-warning"
    else:
        return formatted, "balance-positive"


def format_month_header(month: int, year: int) -> str:
    """Форматирует заголовок месяца на русском.

    Args:
        month: Месяц (1-12)
        year: Год

    Returns:
        str: "Январь 2026"
    """
    return f"{MONTH_NAMES_RU[month]} {year}"


# ==================== КОМПОНЕНТ ЗАГОЛОВКА ====================


def build_calendar_header(month: int, year: int) -> html.Div:
    """Создает заголовок календаря с навигацией.

    Args:
        month: Текущий месяц (1-12)
        year: Текущий год

    Returns:
        html.Div: Заголовок с кнопками навигации
    """
    today = date.today()

    # Вычисляем смещение от текущего месяца
    current_offset = (year - today.year) * 12 + (month - today.month)

    # Определяем disabled для кнопок (+-12 месяцев)
    prev_disabled = current_offset <= -MAX_MONTHS_OFFSET
    next_disabled = current_offset >= MAX_MONTHS_OFFSET

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.ButtonGroup(
                            [
                                dbc.Button(
                                    html.I(className="bi bi-chevron-left"),
                                    id="prev-month-btn",
                                    color="outline-secondary",
                                    disabled=prev_disabled,
                                    n_clicks=0,
                                ),
                                dbc.Button(
                                    html.I(className="bi bi-chevron-right"),
                                    id="next-month-btn",
                                    color="outline-secondary",
                                    disabled=next_disabled,
                                    n_clicks=0,
                                ),
                            ],
                            size="sm",
                        ),
                        width="auto",
                    ),
                    dbc.Col(
                        html.H4(
                            format_month_header(month, year),
                            className="mb-0 text-center calendar-month-title",
                        ),
                        width="auto",
                        style={"minWidth": "180px"},
                    ),
                    dbc.Col(
                        dbc.Button(
                            "Сегодня",
                            id="today-btn",
                            color="outline-primary",
                            size="sm",
                            n_clicks=0,
                            disabled=(month == today.month and year == today.year),
                        ),
                        width="auto",
                    ),
                    # Кнопка сверки
                    dbc.Col(
                        dbc.Button(
                            [html.I(className="bi bi-calculator me-1"), "Сверка"],
                            id="open-reconciliation-btn",
                            color="outline-secondary",
                            size="sm",
                            n_clicks=0,
                        ),
                        width="auto",
                        className="ms-auto",
                    ),
                ],
                className="align-items-center mb-4",
            ),
        ],
        className="calendar-header",
    )


# ==================== ГЛАВНЫЙ LAYOUT ====================


def create_calendar_layout() -> html.Div:
    """Создает layout страницы кассового календаря.

    Returns:
        html.Div: Layout календаря
    """
    today = date.today()

    return html.Div(
        [
            # State хранилище
            dcc.Store(
                id="calendar-state",
                data={
                    "current_month": today.month,
                    "current_year": today.year,
                    "balances": {},
                },
            ),
            # Триггер обновления календаря после сверки
            dcc.Store(id="calendar-refresh-trigger", data=None),
            # Заголовок с навигацией (с начальными кнопками)
            html.Div(
                id="calendar-header",
                children=build_calendar_header(today.month, today.year),
            ),
            # Карточки статистики (загрузка...)
            html.Div(
                id="calendar-stats",
                className="mb-4",
                children=html.Div("Загрузка...", className="text-muted"),
            ),
            # Календарная сетка (загрузка...)
            html.Div(
                id="calendar-grid",
                children=html.Div("Загрузка календаря...", className="text-muted"),
            ),
            # Модал сверки баланса
            create_reconciliation_modal(),
        ],
        className="calendar-container",
    )


# ==================== КАРТОЧКИ СТАТИСТИКИ ====================


def build_stats_cards(summary: dict[str, Any]) -> dbc.Row:
    """Создает карточки статистики над календарем.

    Args:
        summary: MonthSummary dict с ключами:
            - total_income: Decimal
            - total_expense: Decimal
            - start_balance: Decimal
            - end_balance: Decimal

    Returns:
        dbc.Row: Три карточки (Доходы, Расходы, Баланс на конец месяца)
    """
    total_income = summary.get("total_income", Decimal("0"))
    total_expense = summary.get("total_expense", Decimal("0"))
    end_balance = summary.get("end_balance", Decimal("0"))

    income_formatted, _ = format_balance(total_income)
    expense_formatted, _ = format_balance(total_expense)
    balance_formatted, balance_class = format_balance(end_balance)

    return dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P("Доходы", className="text-muted mb-1"),
                            html.H5(
                                f"+{income_formatted} ₽",
                                className="text-success mb-0",
                            ),
                        ]
                    ),
                    className="stats-card",
                ),
                md=4,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P("Расходы", className="text-muted mb-1"),
                            html.H5(
                                f"-{expense_formatted} ₽",
                                className="text-danger mb-0",
                            ),
                        ]
                    ),
                    className="stats-card",
                ),
                md=4,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P("Баланс на конец", className="text-muted mb-1"),
                            html.H5(
                                f"{balance_formatted} ₽",
                                className=f"{balance_class} mb-0",
                            ),
                        ]
                    ),
                    className="stats-card",
                ),
                md=4,
            ),
        ],
        className="mb-4",
    )


# ==================== КАЛЕНДАРНАЯ СЕТКА ====================


def build_calendar_grid(
    month: int,
    year: int,
    balances: dict[date, Decimal],
    transactions: dict[date, list[TransactionInfo]],
) -> html.Div:
    """Создает календарную сетку с днями.

    Args:
        month: Месяц (1-12)
        year: Год
        balances: {date: Decimal} — балансы по дням
        transactions: {date: [TransactionInfo, ...]} — данные транзакций по датам

    Returns:
        html.Div: Сетка календаря
    """
    today = date.today()

    # Заголовок дней недели
    weekday_header = html.Div(
        [
            html.Div(
                day_name,
                className="calendar-weekday text-center",
            )
            for day_name in WEEKDAY_NAMES_RU
        ],
        className="calendar-weekday-row d-flex",
    )

    # Получаем матрицу дней месяца
    cal = calendar.Calendar(firstweekday=0)  # Понедельник = 0
    month_days = cal.monthdatescalendar(year, month)

    # Создаем строки недель
    week_rows = []
    for week in month_days:
        day_cells = []
        for day_date in week:
            is_current_month = day_date.month == month
            is_today = day_date == today
            is_weekend = day_date.weekday() >= 5  # Сб=5, Вс=6

            day_balance = balances.get(day_date, Decimal("0"))
            day_transactions = transactions.get(day_date, [])

            day_cell = build_day_cell(
                day_date=day_date,
                balance=day_balance,
                transactions=day_transactions,
                is_today=is_today,
                is_current_month=is_current_month,
                is_weekend=is_weekend,
            )
            day_cells.append(day_cell)

        week_row = html.Div(day_cells, className="calendar-week-row d-flex")
        week_rows.append(week_row)

    return html.Div(
        [weekday_header] + week_rows,
        className="calendar-grid",
    )


# ==================== ЯЧЕЙКА ДНЯ ====================


def build_day_cell(
    day_date: date,
    balance: Decimal,
    transactions: list[TransactionInfo],
    is_today: bool = False,
    is_current_month: bool = True,
    is_weekend: bool = False,
) -> html.Div:
    """Создает ячейку одного дня календаря.

    Args:
        day_date: Дата дня
        balance: Остаток на этот день
        transactions: Список данных транзакций дня (TransactionInfo dict)
        is_today: Текущий день
        is_current_month: День текущего месяца
        is_weekend: Выходной день

    Returns:
        html.Div: Ячейка дня (кликабельная)
    """
    # Формируем CSS классы
    css_classes = ["calendar-day"]
    if is_today:
        css_classes.append("calendar-day-today")
    if not is_current_month:
        css_classes.append("calendar-day-other-month")
    if is_weekend:
        css_classes.append("calendar-day-weekend")

    # Добавляем класс если есть виртуальные (recurring) транзакции
    has_virtual = any(t.get("is_virtual") for t in transactions)
    if has_virtual:
        css_classes.append("has-virtual")

    # Форматируем баланс
    balance_text, balance_class = format_balance(balance)

    # Иконки транзакций — dict-доступ вместо ORM
    icons = []
    has_income = any(t.get("transaction_type") == "income" for t in transactions)
    has_expense = any(t.get("transaction_type") == "expense" for t in transactions)
    has_recurring = any(
        t.get("is_recurring") or t.get("is_virtual") for t in transactions
    )
    has_skipped = any(t.get("is_skipped") for t in transactions)
    has_exception = any(
        t.get("recurring_parent_id") and not t.get("is_skipped") for t in transactions
    )

    if has_income:
        icons.append(html.Span("↓", className="text-success me-1", title="Доход"))
    if has_expense:
        icons.append(html.Span("↑", className="text-danger me-1", title="Расход"))
    if has_recurring:
        # Определяем класс recurring иконки
        recurring_class = "bi bi-arrow-repeat recurring-indicator"
        recurring_title = "Повторяющаяся операция"
        if has_skipped:
            recurring_class += " skipped"
            recurring_title = "Пропущенная операция"
        icons.append(
            html.I(
                className=recurring_class,
                title=recurring_title,
            )
        )
        # Добавляем иконку изменённого экземпляра
        if has_exception:
            icons.append(
                html.I(
                    className="bi bi-pencil-fill exception-indicator",
                    title="Изменённый экземпляр",
                )
            )

    return html.Div(
        [
            # Номер дня
            html.Div(
                str(day_date.day),
                className="calendar-day-number",
            ),
            # Иконки транзакций
            html.Div(
                icons,
                className="calendar-day-icons",
            )
            if icons
            else None,
            # Баланс
            html.Div(
                f"{balance_text} ₽",
                className=f"calendar-day-balance {balance_class}",
            )
            if is_current_month
            else None,
        ],
        id={"type": "calendar-day", "date": day_date.isoformat()},
        n_clicks=0,
        className=" ".join(css_classes),
    )


# ==================== МОДАЛ СВЕРКИ ====================


def create_reconciliation_modal() -> dbc.Modal:
    """Создает модал сверки баланса.

    Returns:
        dbc.Modal: Модал с формой сверки
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Сверка баланса")),
            dbc.ModalBody(
                [
                    # Выбор даты
                    html.Div(
                        [
                            dbc.Label("Дата сверки"),
                            dcc.DatePickerSingle(
                                id="reconciliation-date",
                                date=date.today().isoformat(),
                                display_format="DD.MM.YYYY",
                                first_day_of_week=1,
                                className="d-block",
                            ),
                        ],
                        className="mb-3",
                    ),
                    # Расчетный баланс (readonly)
                    html.Div(
                        [
                            dbc.Label("Расчетный баланс"),
                            dbc.Input(
                                id="reconciliation-expected",
                                type="text",
                                disabled=True,
                                className="text-end",
                            ),
                        ],
                        className="mb-3",
                    ),
                    # Фактический баланс (ввод)
                    html.Div(
                        [
                            dbc.Label("Фактический баланс"),
                            dbc.Input(
                                id="reconciliation-actual",
                                type="number",
                                step="0.01",
                                placeholder="Введите фактический баланс",
                            ),
                        ],
                        className="mb-3",
                    ),
                    # Preview разницы
                    html.Div(id="reconciliation-preview", className="mt-3"),
                    # Сообщение об ошибке/успехе
                    html.Div(id="reconciliation-message", className="mt-2"),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Отмена",
                        id="cancel-reconciliation-btn",
                        color="secondary",
                        n_clicks=0,
                    ),
                    dbc.Button(
                        "Применить",
                        id="apply-reconciliation-btn",
                        color="primary",
                        n_clicks=0,
                    ),
                ]
            ),
        ],
        id="reconciliation-modal",
        is_open=False,
        centered=True,
    )


# ==================== CALLBACKS ====================

# Константа для user_id (временно, до реализации авторизации)
DEFAULT_USER_ID = 1


@callback(
    [
        Output("calendar-header", "children"),
        Output("calendar-stats", "children"),
        Output("calendar-grid", "children"),
        Output("calendar-state", "data"),
    ],
    [
        Input("url", "pathname"),
        Input("prev-month-btn", "n_clicks"),
        Input("next-month-btn", "n_clicks"),
        Input("today-btn", "n_clicks"),
    ],
    [State("calendar-state", "data")],
)
def load_and_navigate_calendar(
    pathname: str,
    prev_clicks: int | None,
    next_clicks: int | None,
    today_clicks: int | None,
    state: dict | None,
):
    """Загружает календарь и обрабатывает навигацию между месяцами.

    Args:
        pathname: Текущий URL путь
        prev_clicks: Клики на кнопку "назад"
        next_clicks: Клики на кнопку "вперед"
        today_clicks: Клики на кнопку "сегодня"
        state: Текущее состояние календаря

    Returns:
        tuple: (header, stats, grid, updated_state)
    """
    # Guard: только для страницы календаря
    if pathname != "/calendar":
        raise PreventUpdate

    today = date.today()

    # Инициализация state при первом вызове
    if state is None:
        state = {}

    # Получаем текущий месяц/год из state или используем сегодня
    current_month = state.get("current_month", today.month)
    current_year = state.get("current_year", today.year)
    current_date = date(current_year, current_month, 1)

    # Определяем какая кнопка была нажата
    triggered_id = ctx.triggered_id

    if triggered_id == "prev-month-btn":
        new_date = current_date - relativedelta(months=1)
        current_month = new_date.month
        current_year = new_date.year
    elif triggered_id == "next-month-btn":
        new_date = current_date + relativedelta(months=1)
        current_month = new_date.month
        current_year = new_date.year
    elif triggered_id == "today-btn":
        current_month = today.month
        current_year = today.year

    # Валидация +-12 месяцев
    current_offset = (current_year - today.year) * 12 + (current_month - today.month)
    if current_offset < -MAX_MONTHS_OFFSET:
        current_month = (today - relativedelta(months=MAX_MONTHS_OFFSET)).month
        current_year = (today - relativedelta(months=MAX_MONTHS_OFFSET)).year
    elif current_offset > MAX_MONTHS_OFFSET:
        current_month = (today + relativedelta(months=MAX_MONTHS_OFFSET)).month
        current_year = (today + relativedelta(months=MAX_MONTHS_OFFSET)).year

    # Загружаем данные
    try:
        # Вычисляем диапазон дат для месяца
        start_date = date(current_year, current_month, 1)
        # Последний день месяца
        if current_month == 12:
            end_date = date(current_year, 12, 31)
        else:
            end_date = date(current_year, current_month + 1, 1) - timedelta(days=1)

        with get_db_session() as session:
            service = CalendarService(session)

            # Получаем данные за месяц (включая recurring)
            balances = service.calculate_daily_balances(
                user_id=DEFAULT_USER_ID,
                start_date=start_date,
                end_date=end_date,
            )
            transactions_by_date = service.get_all_transactions_for_period(
                user_id=DEFAULT_USER_ID,
                start_date=start_date,
                end_date=end_date,
                include_recurring=True,
            )
            summary = service.get_month_summary(
                user_id=DEFAULT_USER_ID,
                year=current_year,
                month=current_month,
            )

        # Строим UI компоненты
        header = build_calendar_header(current_month, current_year)
        stats = build_stats_cards(summary)
        grid = build_calendar_grid(
            current_month, current_year, balances, transactions_by_date
        )

        # Обновляем state
        new_state = {
            "current_month": current_month,
            "current_year": current_year,
            "balances": serialize_balances(balances),
        }

        return header, stats, grid, new_state

    except Exception as e:
        logger.error(f"Ошибка загрузки календаря: {e}")
        return (
            build_calendar_header(current_month, current_year),
            dbc.Alert("Не удалось загрузить данные", color="danger"),
            html.Div(),
            state,
        )


@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("create-date-picker", "date", allow_duplicate=True),
        Output("modal-source", "data", allow_duplicate=True),
    ],
    Input({"type": "calendar-day", "date": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_create_modal_from_calendar(n_clicks_list: list[int | None]):
    """Открывает модал создания операции при клике на день календаря.

    Args:
        n_clicks_list: Список кликов по ячейкам дней

    Returns:
        tuple: (is_open, selected_date, modal_source)
    """
    triggered_id = ctx.triggered_id

    # Guard #1: проверка triggered_id существует
    if not triggered_id:
        raise PreventUpdate

    # Guard #2: проверка типа (для Pattern-Matching)
    if not isinstance(triggered_id, dict) or triggered_id.get("type") != "calendar-day":
        raise PreventUpdate

    # Guard #3: проверка реального клика (НЕ автовызов при DOM update!)
    if not ctx.triggered or ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    # Guard #4: находим индекс нажатой кнопки и проверяем её n_clicks
    # При первичном рендере или автовызове n_clicks будет None или 0
    clicked_idx = None
    for idx, item in enumerate(ctx.inputs_list[0]):
        if item.get("id") == triggered_id:
            clicked_idx = idx
            break

    if clicked_idx is None:
        raise PreventUpdate

    # Проверяем что это реальный клик (not None and not 0)
    n_clicks = n_clicks_list[clicked_idx]
    if n_clicks is None or n_clicks == 0:
        raise PreventUpdate

    # Извлекаем дату
    selected_date = triggered_id.get("date")
    if not selected_date:
        raise PreventUpdate

    logger.debug(f"Открыт модал создания из календаря: {selected_date}")
    return True, selected_date, "calendar"


@callback(
    [
        Output("calendar-grid", "children", allow_duplicate=True),
        Output("calendar-stats", "children", allow_duplicate=True),
        Output("calendar-state", "data", allow_duplicate=True),
    ],
    [Input("global-transaction-trigger", "data")],
    [State("calendar-state", "data"), State("url", "pathname")],
    prevent_initial_call=True,
)
def refresh_calendar_after_transaction(
    trigger: dict | None,
    state: dict,
    pathname: str,
):
    """Обновляет календарь после CRUD операции с транзакцией.

    Слушает global-transaction-trigger из transaction_modals.py.

    Args:
        trigger: Данные триггера {action, timestamp, source, transaction_id}
        state: Текущее состояние календаря
        pathname: Текущий URL

    Returns:
        tuple: (grid, stats, updated_state)
    """
    # Guard #1: проверяем наличие триггера
    if not trigger:
        raise PreventUpdate

    # Guard #2: обновляем только если мы на странице календаря
    if pathname != "/calendar":
        raise PreventUpdate

    # Получаем текущий месяц из state
    today = date.today()
    current_month = state.get("current_month", today.month)
    current_year = state.get("current_year", today.year)

    # Пересчитываем данные
    try:
        # Вычисляем диапазон дат для месяца
        start_date = date(current_year, current_month, 1)
        if current_month == 12:
            end_date = date(current_year, 12, 31)
        else:
            end_date = date(current_year, current_month + 1, 1) - timedelta(days=1)

        with get_db_session() as session:
            service = CalendarService(session)

            balances = service.calculate_daily_balances(
                user_id=DEFAULT_USER_ID,
                start_date=start_date,
                end_date=end_date,
            )
            transactions_by_date = service.get_all_transactions_for_period(
                user_id=DEFAULT_USER_ID,
                start_date=start_date,
                end_date=end_date,
                include_recurring=True,
            )
            summary = service.get_month_summary(
                user_id=DEFAULT_USER_ID,
                year=current_year,
                month=current_month,
            )

        # Строим обновленные компоненты
        grid = build_calendar_grid(
            current_month, current_year, balances, transactions_by_date
        )
        stats = build_stats_cards(summary)

        # Обновляем state
        new_state = {
            "current_month": current_month,
            "current_year": current_year,
            "balances": serialize_balances(balances),
        }

        source = trigger.get("source", "unknown")
        action = trigger.get("action", "unknown")
        logger.debug(f"Календарь обновлен после {action} из {source}")
        return grid, stats, new_state

    except Exception as e:
        logger.error(f"Ошибка обновления календаря: {e}")
        raise PreventUpdate


# ==================== CALLBACKS СВЕРКИ ====================


@callback(
    [
        Output("reconciliation-modal", "is_open"),
        Output("reconciliation-expected", "value"),
        Output("reconciliation-actual", "value"),
        Output("reconciliation-preview", "children"),
        Output("reconciliation-message", "children"),
    ],
    [
        Input("open-reconciliation-btn", "n_clicks"),
        Input("cancel-reconciliation-btn", "n_clicks"),
        Input("reconciliation-date", "date"),
        Input("open-recon-trigger", "data"),
    ],
    State("reconciliation-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_reconciliation_modal(
    open_clicks: int | None,
    cancel_clicks: int | None,
    selected_date: str | None,
    recon_trigger: int | None,
    is_open: bool,
):
    """Открывает/закрывает модал сверки и загружает расчетный баланс.

    Args:
        open_clicks: Клики на кнопку открытия
        cancel_clicks: Клики на кнопку отмены
        selected_date: Выбранная дата
        recon_trigger: Timestamp trigger из query param ?open_recon=1
        is_open: Текущее состояние модала

    Returns:
        tuple: (is_open, expected_balance, actual_value, preview, message)
    """
    triggered_id = ctx.triggered_id

    # Auto-open from query parameter trigger (timestamp-based)
    if triggered_id == "open-recon-trigger":
        if not recon_trigger:
            raise PreventUpdate

        target_date = date.today()

        try:
            with get_db_session() as session:
                service = ReconciliationService(session)
                expected = service.get_expected_balance(
                    user_id=DEFAULT_USER_ID, target_date=target_date
                )
            return True, f"{expected:,.2f} ₽", None, "", ""

        except Exception as e:
            logger.error(f"Ошибка auto-open reconciliation: {e}")
            return True, "Ошибка", None, "", ""

    # Закрытие по кнопке "Отмена" — требуем реальный клик
    if triggered_id == "cancel-reconciliation-btn":
        if cancel_clicks is None or cancel_clicks == 0:
            raise PreventUpdate
        return False, "", None, "", ""

    # Открытие модала по кнопке — требуем реальный клик
    if triggered_id == "open-reconciliation-btn":
        if open_clicks is None or open_clicks == 0:
            raise PreventUpdate

    # Изменение даты — только если модал УЖЕ открыт
    if triggered_id == "reconciliation-date" and not is_open:
        raise PreventUpdate

    # Открытие модала или изменение даты при открытом модале
    if triggered_id == "open-reconciliation-btn" or (
        triggered_id == "reconciliation-date" and is_open
    ):
        target_date = (
            date.fromisoformat(selected_date) if selected_date else date.today()
        )

        try:
            with get_db_session() as session:
                service = ReconciliationService(session)
                expected = service.get_expected_balance(
                    user_id=DEFAULT_USER_ID, target_date=target_date
                )

            # При открытии — очищаем поля, при смене даты — оставляем модал открытым
            should_open = True if triggered_id == "open-reconciliation-btn" else is_open
            return should_open, f"{expected:,.2f} ₽", None, "", ""

        except Exception as e:
            logger.error(f"Ошибка получения баланса для сверки: {e}")
            return (
                True,
                "Ошибка",
                None,
                "",
                dbc.Alert(str(e), color="danger"),
            )

    return is_open, "", None, "", ""


@callback(
    Output("reconciliation-preview", "children", allow_duplicate=True),
    [Input("reconciliation-actual", "value")],
    [State("reconciliation-date", "date")],
    prevent_initial_call=True,
)
def update_reconciliation_preview(
    actual_value: float | None,
    selected_date: str | None,
):
    """Обновляет preview разницы при вводе фактического баланса.

    Args:
        actual_value: Введенный фактический баланс
        selected_date: Выбранная дата сверки

    Returns:
        Preview с разницей и пояснением
    """
    if actual_value is None or selected_date is None:
        return ""

    try:
        target_date = date.fromisoformat(selected_date)
        actual_balance = Decimal(str(actual_value))

        with get_db_session() as session:
            service = ReconciliationService(session)
            preview = service.calculate_preview(
                user_id=DEFAULT_USER_ID,
                target_date=target_date,
                actual_balance=actual_balance,
            )

        # Стилизация в зависимости от разницы
        diff = Decimal(preview["difference"])
        if diff == Decimal("0"):
            color = "success"
            icon = "bi-check-circle"
            text_class = "text-success"
        elif diff > Decimal("0"):
            color = "info"
            icon = "bi-plus-circle"
            text_class = "text-primary"
        else:
            color = "warning"
            icon = "bi-dash-circle"
            text_class = "text-danger"

        return dbc.Alert(
            [
                html.I(className=f"bi {icon} me-2"),
                html.Strong(f"Разница: {diff:+,.2f} ₽", className=text_class),
                html.Br(),
                html.Small(preview["explanation"]),
            ],
            color=color,
            className="mb-0",
        )

    except Exception as e:
        logger.error(f"Ошибка расчета preview сверки: {e}")
        return dbc.Alert(f"Ошибка расчета: {e}", color="danger")


@callback(
    [
        Output("reconciliation-message", "children", allow_duplicate=True),
        Output("reconciliation-modal", "is_open", allow_duplicate=True),
        Output("calendar-refresh-trigger", "data"),
    ],
    [Input("apply-reconciliation-btn", "n_clicks")],
    [
        State("reconciliation-date", "date"),
        State("reconciliation-actual", "value"),
    ],
    prevent_initial_call=True,
)
def apply_reconciliation(
    n_clicks: int | None,
    selected_date: str | None,
    actual_value: float | None,
):
    """Применяет сверку и создает корректировку.

    Args:
        n_clicks: Клики на кнопку применения
        selected_date: Выбранная дата
        actual_value: Введенный фактический баланс

    Returns:
        tuple: (message, is_open, refresh_trigger)
    """
    # Guard: проверка реального клика
    if ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    if actual_value is None:
        return (
            dbc.Alert("Введите фактический баланс", color="warning"),
            True,
            no_update,
        )

    try:
        target_date = date.fromisoformat(selected_date)
        actual_balance = Decimal(str(actual_value))

        with get_db_session() as session:
            service = ReconciliationService(session)
            adjustment = service.create_adjustment(
                user_id=DEFAULT_USER_ID,
                target_date=target_date,
                actual_balance=actual_balance,
            )
            session.commit()

            if adjustment is None:
                return (
                    dbc.Alert("Баланс совпадает, корректировка не нужна", color="info"),
                    False,
                    no_update,
                )

            logger.info(
                f"Создана корректировка: {adjustment.amount:+,.2f} ₽ "
                f"на {target_date}"
            )
            return (
                dbc.Alert(
                    f"Корректировка на {adjustment.amount:+,.2f} ₽ создана",
                    color="success",
                ),
                False,  # Закрыть модал
                {"timestamp": datetime.now().isoformat()},  # Триггер обновления
            )

    except ValidationError as e:
        return dbc.Alert(str(e), color="danger"), True, no_update
    except Exception as e:
        logger.error(f"Ошибка создания корректировки: {e}")
        return dbc.Alert(f"Ошибка: {e}", color="danger"), True, no_update


@callback(
    [
        Output("calendar-grid", "children", allow_duplicate=True),
        Output("calendar-stats", "children", allow_duplicate=True),
        Output("calendar-state", "data", allow_duplicate=True),
    ],
    [Input("calendar-refresh-trigger", "data")],
    [State("calendar-state", "data")],
    prevent_initial_call=True,
)
def refresh_calendar_after_reconciliation(
    trigger: dict | None,
    state: dict,
):
    """Обновляет календарь после применения сверки.

    Args:
        trigger: Данные триггера с timestamp
        state: Текущее состояние календаря

    Returns:
        tuple: (grid, stats, updated_state)
    """
    if not trigger:
        raise PreventUpdate

    # Получаем текущий месяц из state
    today = date.today()
    current_month = state.get("current_month", today.month)
    current_year = state.get("current_year", today.year)

    try:
        # Вычисляем диапазон дат для месяца
        start_date = date(current_year, current_month, 1)
        if current_month == 12:
            end_date = date(current_year, 12, 31)
        else:
            end_date = date(current_year, current_month + 1, 1) - timedelta(days=1)

        with get_db_session() as session:
            service = CalendarService(session)

            balances = service.calculate_daily_balances(
                user_id=DEFAULT_USER_ID,
                start_date=start_date,
                end_date=end_date,
            )
            transactions_by_date = service.get_all_transactions_for_period(
                user_id=DEFAULT_USER_ID,
                start_date=start_date,
                end_date=end_date,
                include_recurring=True,
            )
            summary = service.get_month_summary(
                user_id=DEFAULT_USER_ID,
                year=current_year,
                month=current_month,
            )

        # Строим обновленные компоненты
        grid = build_calendar_grid(
            current_month, current_year, balances, transactions_by_date
        )
        stats = build_stats_cards(summary)

        # Обновляем state
        new_state = {
            "current_month": current_month,
            "current_year": current_year,
            "balances": serialize_balances(balances),
        }

        logger.debug("Календарь обновлен после сверки")
        return grid, stats, new_state

    except Exception as e:
        logger.error(f"Ошибка обновления календаря после сверки: {e}")
        raise PreventUpdate
