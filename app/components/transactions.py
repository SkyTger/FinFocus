"""
Компонент управления финансовыми операциями (транзакциями).
"""
from datetime import date
from decimal import Decimal

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ALL, ctx, no_update
from dash.exceptions import PreventUpdate

from loguru import logger

from app.core import get_db_session, ValidationError
from app.models.database import TransactionType
from app.services import TransactionService, RecurringService, CategoryService
from app.utils.formatters import format_amount, format_date, parse_date_safe


def _build_transactions_table(transactions: list) -> list:
    """Формирует HTML таблицу транзакций.

    Args:
        transactions: Список объектов Transaction

    Returns:
        list: [thead, tbody] для dbc.Table
    """
    # Заголовок таблицы
    table_header = html.Thead(
        [
            html.Tr(
                [
                    html.Th("Дата"),
                    html.Th("Тип"),
                    html.Th("Сумма", className="text-end"),
                    html.Th("Категория"),
                    html.Th("Описание"),
                    html.Th("Действия", className="text-end"),
                ]
            )
        ]
    )

    # Пустая таблица
    if not transactions:
        return [
            table_header,
            html.Tbody(
                [
                    html.Tr(
                        [
                            html.Td(
                                "Нет операций",
                                colSpan=6,
                                className="text-center text-muted",
                            )
                        ]
                    )
                ]
            ),
        ]

    # Строки таблицы
    table_rows = []
    for tx in transactions:
        # Определяем стиль для типа операции
        if tx.transaction_type == TransactionType.INCOME:
            type_badge = dbc.Badge("Доход", color="success", className="rounded-pill")
            amount_class = "text-success fw-bold text-end"
            amount_prefix = "+"
        else:
            type_badge = dbc.Badge("Расход", color="danger", className="rounded-pill")
            amount_class = "text-danger fw-bold text-end"
            amount_prefix = "-"

        # Иконка recurring
        recurring_icon = None
        if tx.is_recurring:
            recurring_icon = html.I(
                className="bi bi-arrow-repeat text-success me-2",
                title="Повторяющаяся операция",
            )

        # Категория с иконкой
        category_cell = []
        if tx.category_rel:
            category_cell = [
                html.I(className=f"{tx.category_rel.icon} me-1"),
                tx.category_rel.name,
            ]
        else:
            category_cell = [html.Span("—", className="text-muted")]

        row = html.Tr(
            [
                html.Td([recurring_icon, format_date(tx.transaction_date)]),
                html.Td(type_badge),
                html.Td(
                    f"{amount_prefix}{format_amount(tx.amount)}", className=amount_class
                ),
                html.Td(category_cell),
                html.Td(tx.description or "-", className="text-muted"),
                html.Td(
                    [
                        dbc.ButtonGroup(
                            [
                                dbc.Button(
                                    html.I(className="bi bi-pencil"),
                                    id={"type": "edit-btn", "index": tx.id},
                                    color="secondary",
                                    size="sm",
                                    outline=True,
                                    className="me-1",
                                ),
                                dbc.Button(
                                    html.I(className="bi bi-trash"),
                                    id={"type": "delete-btn", "index": tx.id},
                                    color="danger",
                                    size="sm",
                                    outline=True,
                                ),
                            ]
                        )
                    ],
                    className="text-end",
                ),
            ]
        )
        table_rows.append(row)

    return [table_header, html.Tbody(table_rows)]


def create_transactions_layout():
    """Создает layout страницы управления операциями.

    Returns:
        dash component: Layout страницы Transactions
    """
    return html.Div(
        [
            # Заголовок с описанием
            html.Div(
                [
                    html.Div(
                        [
                            html.H4("Операции", className="mb-1"),
                            html.P(
                                "Управление доходами и расходами",
                                className="text-muted mb-0",
                            ),
                        ],
                        className="flex-grow-1",
                    ),
                    dbc.Button(
                        [
                            html.I(className="bi bi-plus-circle me-2"),
                            "Добавить операцию",
                        ],
                        id="add-transaction-btn",
                        color="success",
                        className="d-flex align-items-center",
                    ),
                ],
                className="d-flex justify-content-between align-items-center mb-4",
            ),
            # Alert для ошибок валидации
            dbc.Alert(
                id="transaction-error-alert",
                is_open=False,
                color="danger",
                dismissable=True,
                duration=5000,  # Автозакрытие через 5 сек
                className="mb-3",
            ),
            # Панель фильтров
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Checkbox(
                            id="filter-no-category",
                            label="Показать только без категории",
                            value=False,
                        ),
                    ],
                    className="py-2",
                ),
                className="mb-3",
            ),
            # Таблица операций
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.Div(
                                id="transactions-table-container",
                                children=[
                                    dbc.Table(
                                        id="transactions-table",
                                        striped=True,
                                        hover=True,
                                        responsive=True,
                                        className="mb-0",
                                    )
                                ],
                            )
                        ]
                    )
                ],
                className="shadow-sm",
            ),
            # Модальное окно создания
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Добавить операцию")),
                    dbc.ModalBody(
                        [
                            # Сумма
                            dbc.Row(
                                [
                                    dbc.Label(
                                        "Сумма", html_for="create-amount-input", width=3
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Input(
                                                id="create-amount-input",
                                                type="number",
                                                step=0.01,
                                                min=0.01,
                                                placeholder="Введите сумму",
                                                required=True,
                                            )
                                        ],
                                        width=9,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Тип операции
                            dbc.Row(
                                [
                                    dbc.Label(
                                        "Тип операции",
                                        html_for="create-type-select",
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Select(
                                                id="create-type-select",
                                                options=[
                                                    {
                                                        "label": "Доход",
                                                        "value": "INCOME",
                                                    },
                                                    {
                                                        "label": "Расход",
                                                        "value": "EXPENSE",
                                                    },
                                                ],
                                                value="EXPENSE",
                                                required=True,
                                            )
                                        ],
                                        width=9,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Категория (опционально)
                            dbc.Row(
                                [
                                    dbc.Label(
                                        "Категория",
                                        html_for="create-category-dropdown",
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dcc.Dropdown(
                                                id="create-category-dropdown",
                                                placeholder="Выберите категорию",
                                                clearable=True,
                                                options=[],
                                            )
                                        ],
                                        width=9,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Дата
                            dbc.Row(
                                [
                                    dbc.Label(
                                        "Дата", html_for="create-date-picker", width=3
                                    ),
                                    dbc.Col(
                                        [
                                            dcc.DatePickerSingle(
                                                id="create-date-picker",
                                                date=date.today(),
                                                display_format="DD.MM.YYYY",
                                                first_day_of_week=1,
                                                className="w-100",
                                            )
                                        ],
                                        width=9,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Описание
                            dbc.Row(
                                [
                                    dbc.Label(
                                        "Описание",
                                        html_for="create-description-input",
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Textarea(
                                                id="create-description-input",
                                                placeholder="Описание (опционально)",
                                                rows=3,
                                            )
                                        ],
                                        width=9,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Чекбокс "Повторяющаяся операция"
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Checkbox(
                                                id="create-is-recurring",
                                                label="Повторяющаяся операция",
                                                value=False,
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Секция recurring (скрыта по умолчанию)
                            html.Div(
                                id="create-recurring-section",
                                style={"display": "none"},
                                children=[
                                    # Период повторения
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label("Период повторения"),
                                                    dbc.Select(
                                                        id="create-recurring-period",
                                                        options=[
                                                            {
                                                                "label": "Еженедельно",
                                                                "value": "weekly",
                                                            },
                                                            {
                                                                "label": "Раз в 2 недели",  # noqa: E501
                                                                "value": "biweekly",
                                                            },
                                                            {
                                                                "label": "Ежемесячно",
                                                                "value": "monthly",
                                                            },
                                                            {
                                                                "label": "Ежеквартально",  # noqa: E501
                                                                "value": "quarterly",
                                                            },
                                                        ],
                                                        value="monthly",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Дата окончания (опционально)"
                                                    ),
                                                    dbc.Input(
                                                        id="create-recurring-end-date",
                                                        type="date",
                                                        placeholder="Бессрочно",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                ],
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Отмена",
                                id="create-cancel-btn",
                                color="secondary",
                                className="me-2",
                            ),
                            dbc.Button(
                                "Создать", id="create-submit-btn", color="success"
                            ),
                        ]
                    ),
                ],
                id="create-modal",
                is_open=False,
                centered=True,
            ),
            # Модальное окно редактирования
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Редактировать операцию")),
                    dbc.ModalBody(
                        [
                            # Сумма
                            dbc.Row(
                                [
                                    dbc.Label(
                                        "Сумма", html_for="edit-amount-input", width=3
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Input(
                                                id="edit-amount-input",
                                                type="number",
                                                step=0.01,
                                                min=0.01,
                                                required=True,
                                            )
                                        ],
                                        width=9,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Тип операции
                            dbc.Row(
                                [
                                    dbc.Label(
                                        "Тип операции",
                                        html_for="edit-type-select",
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Select(
                                                id="edit-type-select",
                                                options=[
                                                    {
                                                        "label": "Доход",
                                                        "value": "INCOME",
                                                    },
                                                    {
                                                        "label": "Расход",
                                                        "value": "EXPENSE",
                                                    },
                                                ],
                                                required=True,
                                            )
                                        ],
                                        width=9,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Категория
                            dbc.Row(
                                [
                                    dbc.Label(
                                        "Категория",
                                        html_for="edit-category-dropdown",
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dcc.Dropdown(
                                                id="edit-category-dropdown",
                                                placeholder="Выберите категорию",
                                                clearable=True,
                                                options=[],
                                            )
                                        ],
                                        width=9,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Дата
                            dbc.Row(
                                [
                                    dbc.Label(
                                        "Дата", html_for="edit-date-picker", width=3
                                    ),
                                    dbc.Col(
                                        [
                                            dcc.DatePickerSingle(
                                                id="edit-date-picker",
                                                display_format="DD.MM.YYYY",
                                                first_day_of_week=1,
                                                className="w-100",
                                            )
                                        ],
                                        width=9,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Описание
                            dbc.Row(
                                [
                                    dbc.Label(
                                        "Описание",
                                        html_for="edit-description-input",
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Textarea(
                                                id="edit-description-input", rows=3
                                            )
                                        ],
                                        width=9,
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Отмена",
                                id="edit-cancel-btn",
                                color="secondary",
                                className="me-2",
                            ),
                            dbc.Button(
                                "Пропустить",
                                id="edit-skip-instance",
                                color="warning",
                                outline=True,
                                className="me-2",
                                style={"display": "none"},
                            ),
                            dbc.Button(
                                "Сохранить", id="edit-submit-btn", color="success"
                            ),
                        ]
                    ),
                ],
                id="edit-modal",
                is_open=False,
                centered=True,
            ),
            # Store для хранения ID редактируемой транзакции
            dcc.Store(id="edit-transaction-id"),
            # Модальное окно выбора scope редактирования recurring
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Изменить повторяющуюся операцию")),
                    dbc.ModalBody(
                        [
                            html.P("Выберите, что вы хотите изменить:"),
                            dbc.RadioItems(
                                id="recurring-edit-scope",
                                options=[
                                    {
                                        "label": "Только этот экземпляр",
                                        "value": "instance",
                                    },
                                    {
                                        "label": "Всю серию (все экземпляры)",
                                        "value": "all",
                                    },
                                ],
                                value="instance",
                                className="mb-3",
                            ),
                            html.P(
                                "Примечание: изменение серии повлияет на все "
                                "будущие экземпляры.",
                                className="text-muted small",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Отмена",
                                id="recurring-edit-cancel",
                                color="secondary",
                                outline=True,
                                className="me-2",
                            ),
                            dbc.Button(
                                "Продолжить",
                                id="recurring-edit-continue",
                                color="primary",
                            ),
                        ]
                    ),
                ],
                id="recurring-edit-scope-modal",
                is_open=False,
                centered=True,
            ),
            # Store для контекста редактирования recurring
            dcc.Store(id="recurring-edit-context", data=None),
        ]
    )


# ==================== CALLBACKS ====================


@callback(
    Output("transactions-table", "children"),
    [Input("url", "pathname"), Input("filter-no-category", "value")],
)
def load_transactions(pathname, filter_no_category):
    """Загружает список операций из БД с фильтрацией."""
    if pathname != "/transactions":
        raise PreventUpdate

    with get_db_session() as session:
        service = TransactionService(session)
        transactions = service.get_all_by_user(user_id=1)

        # Фильтр по отсутствию категории
        if filter_no_category:
            transactions = [tx for tx in transactions if tx.category_id is None]

        logger.debug(f"Загружено {len(transactions)} транзакций")
        return _build_transactions_table(transactions)


@callback(
    Output("create-modal", "is_open"),
    [Input("add-transaction-btn", "n_clicks"), Input("create-cancel-btn", "n_clicks")],
    [State("create-modal", "is_open")],
    prevent_initial_call=True,
)
def toggle_create_modal(add_clicks, cancel_clicks, is_open):
    """Открывает/закрывает модальное окно создания."""
    triggered_id = ctx.triggered_id

    if not triggered_id:
        raise PreventUpdate

    # Открыть модал при клике на "Добавить"
    if triggered_id == "add-transaction-btn":
        return True

    # Закрыть модал при клике на "Отмена"
    if triggered_id == "create-cancel-btn":
        return False

    raise PreventUpdate


@callback(
    Output("create-recurring-section", "style"),
    Input("create-is-recurring", "value"),
    prevent_initial_call=True,
)
def toggle_recurring_section(is_recurring: bool):
    """Показывает/скрывает секцию настроек recurring."""
    if is_recurring:
        return {"display": "block"}
    return {"display": "none"}


@callback(
    Output("create-category-dropdown", "options"),
    Input("create-type-select", "value"),
    prevent_initial_call=True,
)
def update_create_category_options(transaction_type: str | None):
    """Обновить список категорий при смене типа транзакции."""
    if not transaction_type:
        return []

    with get_db_session() as session:
        service = CategoryService(session)
        # Мапим transaction_type на category_type
        category_type = "income" if transaction_type == "INCOME" else "expense"
        options = service.get_for_dropdown(category_type=category_type)

        return [
            {"label": f"{opt['icon']} {opt['label']}", "value": opt["value"]}
            for opt in options
        ]


@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("transactions-table", "children", allow_duplicate=True),
        Output("create-amount-input", "value"),
        Output("create-type-select", "value"),
        Output("create-category-dropdown", "value"),
        Output("create-date-picker", "date"),
        Output("create-description-input", "value"),
        Output("create-is-recurring", "value"),
        Output("create-recurring-period", "value"),
        Output("create-recurring-end-date", "value"),
        Output("transaction-error-alert", "children", allow_duplicate=True),
        Output("transaction-error-alert", "is_open", allow_duplicate=True),
    ],
    Input("create-submit-btn", "n_clicks"),
    [
        State("create-amount-input", "value"),
        State("create-type-select", "value"),
        State("create-category-dropdown", "value"),
        State("create-date-picker", "date"),
        State("create-description-input", "value"),
        State("create-is-recurring", "value"),
        State("create-recurring-period", "value"),
        State("create-recurring-end-date", "value"),
    ],
    prevent_initial_call=True,
)
def create_transaction(
    n_clicks,
    amount,
    transaction_type,
    category_id,
    date_str,
    description,
    is_recurring,
    recurring_period,
    recurring_end_date,
):
    """Создает новую транзакцию или шаблон recurring через TransactionService."""
    if not n_clicks or not amount:
        raise PreventUpdate

    # Безопасный парсинг даты
    transaction_date = parse_date_safe(date_str)
    if not transaction_date:
        return (
            True,  # Модал остаётся открытым
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            "Неверный формат даты",
            True,  # Показать Alert
        )

    # Парсинг даты окончания recurring (если указана)
    parsed_end_date = None
    if is_recurring and recurring_end_date:
        parsed_end_date = parse_date_safe(recurring_end_date)

    try:
        with get_db_session() as session:
            service = TransactionService(session)
            service.create_transaction(
                user_id=1,
                amount=Decimal(str(amount)),
                transaction_type=TransactionType[transaction_type],
                transaction_date=transaction_date,
                description=description if description else None,
                category_id=category_id,
                is_recurring=is_recurring or False,
                recurring_period=recurring_period if is_recurring else None,
                recurring_end_date=parsed_end_date,
            )
            transactions = service.get_all_by_user(user_id=1)
            log_msg = f"Создана транзакция: {transaction_type} {amount}"
            if is_recurring:
                log_msg += f" (recurring: {recurring_period})"
            logger.info(log_msg)
            # Успех: закрываем модал, очищаем форму, скрываем Alert
            return (
                False,  # is_open
                _build_transactions_table(transactions),  # table
                None,  # amount
                "EXPENSE",  # type
                None,  # category_id
                date.today().isoformat(),  # date
                "",  # description
                False,  # is_recurring
                "monthly",  # recurring_period
                None,  # recurring_end_date
                "",  # alert text
                False,  # alert is_open
            )
    except ValidationError as e:
        logger.warning(f"Ошибка валидации при создании: {e}")
        return (
            True,  # Модал остаётся открытым
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            str(e),  # Текст ошибки
            True,  # Показать Alert
        )


@callback(
    [
        Output("edit-modal", "is_open"),
        Output("edit-transaction-id", "data"),
        Output("edit-amount-input", "value"),
        Output("edit-type-select", "value"),
        Output("edit-category-dropdown", "value"),
        Output("edit-category-dropdown", "options"),
        Output("edit-date-picker", "date"),
        Output("edit-description-input", "value"),
        Output("recurring-edit-scope-modal", "is_open"),
        Output("recurring-edit-context", "data"),
    ],
    [
        Input({"type": "edit-btn", "index": ALL}, "n_clicks"),
        Input("edit-cancel-btn", "n_clicks"),
    ],
    [State("edit-modal", "is_open")],
    prevent_initial_call=True,
)
def open_edit_modal(edit_clicks_list, cancel_click, is_open):
    """Открывает модал редактирования с данными транзакции.

    Для recurring операций показывает диалог выбора scope.
    """
    # Проверяем какая кнопка была нажата
    triggered_id = ctx.triggered_id

    # Если ничего не нажато (initial render)
    if not triggered_id:
        raise PreventUpdate

    # Если нажата кнопка отмены
    if triggered_id == "edit-cancel-btn":
        return False, None, None, None, None, [], None, None, False, None

    # Если нажата кнопка редактирования
    if not isinstance(triggered_id, dict) or triggered_id.get("type") != "edit-btn":
        raise PreventUpdate

    # Проверяем что был реальный клик (не автовызов при обновлении таблицы)
    if not ctx.triggered or ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    transaction_id = triggered_id.get("index")
    if not transaction_id:
        raise PreventUpdate

    with get_db_session() as session:
        service = TransactionService(session)
        tx = service.get_by_id(transaction_id)

        if not tx:
            raise PreventUpdate

        # Проверяем, является ли транзакция recurring
        is_recurring_tx = tx.is_recurring or tx.recurring_parent_id is not None

        if is_recurring_tx:
            # Открываем scope modal для выбора "экземпляр vs серия"
            logger.debug(
                f"Открыт scope modal для recurring транзакции {transaction_id}"
            )
            context = {
                "transaction_id": transaction_id,
                "template_id": tx.recurring_parent_id or transaction_id,
                "instance_date": tx.transaction_date.isoformat(),
                "is_template": tx.is_recurring,
            }
            return False, None, None, None, None, [], None, None, True, context

        # Обычная транзакция — открываем edit modal напрямую
        logger.debug(f"Открыт модал редактирования для транзакции {transaction_id}")

        # Загружаем категории для типа транзакции
        category_service = CategoryService(session)
        category_type = (
            "income" if tx.transaction_type == TransactionType.INCOME else "expense"
        )
        category_options = category_service.get_for_dropdown(category_type=category_type)
        dropdown_options = [
            {"label": f"{opt['icon']} {opt['label']}", "value": opt["value"]}
            for opt in category_options
        ]

        return (
            True,
            transaction_id,
            float(tx.amount),
            tx.transaction_type.name,
            tx.category_id,
            dropdown_options,
            tx.transaction_date.isoformat(),
            tx.description or "",
            False,
            None,
        )


@callback(
    [
        Output("edit-modal", "is_open", allow_duplicate=True),
        Output("transactions-table", "children", allow_duplicate=True),
        Output("transaction-error-alert", "children", allow_duplicate=True),
        Output("transaction-error-alert", "is_open", allow_duplicate=True),
    ],
    Input("edit-submit-btn", "n_clicks"),
    [
        State("edit-transaction-id", "data"),
        State("edit-amount-input", "value"),
        State("edit-type-select", "value"),
        State("edit-category-dropdown", "value"),
        State("edit-date-picker", "date"),
        State("edit-description-input", "value"),
    ],
    prevent_initial_call=True,
)
def update_transaction(
    n_clicks, transaction_id, amount, transaction_type, category_id, date_str, description
):
    """Обновляет транзакцию через TransactionService."""
    if not n_clicks or not transaction_id:
        raise PreventUpdate

    # Безопасный парсинг даты
    transaction_date = parse_date_safe(date_str)
    if not transaction_date:
        return True, no_update, "Неверный формат даты", True

    try:
        with get_db_session() as session:
            service = TransactionService(session)
            service.update_transaction(
                transaction_id=transaction_id,
                amount=Decimal(str(amount)),
                transaction_type=TransactionType[transaction_type],
                transaction_date=transaction_date,
                description=description if description else None,
                category_id=category_id,
            )
            transactions = service.get_all_by_user(user_id=1)
            logger.info(f"Обновлена транзакция {transaction_id}")
            return False, _build_transactions_table(transactions), "", False
    except ValidationError as e:
        logger.warning(f"Ошибка валидации при обновлении: {e}")
        return True, no_update, str(e), True


@callback(
    Output("transactions-table", "children", allow_duplicate=True),
    [Input({"type": "delete-btn", "index": ALL}, "n_clicks")],
    prevent_initial_call=True,
)
def delete_transaction(n_clicks_list):
    """Удаляет транзакцию через TransactionService."""
    triggered_id = ctx.triggered_id

    if not triggered_id:
        raise PreventUpdate

    if not isinstance(triggered_id, dict) or triggered_id.get("type") != "delete-btn":
        raise PreventUpdate

    # Проверяем что был реальный клик (не автовызов при обновлении таблицы)
    if not ctx.triggered or ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    transaction_id = triggered_id.get("index")
    if not transaction_id:
        raise PreventUpdate

    with get_db_session() as session:
        service = TransactionService(session)
        deleted = service.delete_transaction(transaction_id)

        if not deleted:
            raise PreventUpdate

        transactions = service.get_all_by_user(user_id=1)
        logger.info(f"Удалена транзакция {transaction_id}")
        return _build_transactions_table(transactions)


# ==================== RECURRING EDIT CALLBACKS ====================


@callback(
    Output("recurring-edit-scope-modal", "is_open", allow_duplicate=True),
    Input("recurring-edit-cancel", "n_clicks"),
    prevent_initial_call=True,
)
def cancel_recurring_edit_scope(n_clicks):
    """Закрывает модал выбора scope редактирования."""
    if not n_clicks:
        raise PreventUpdate
    return False


@callback(
    [
        Output("edit-modal", "is_open", allow_duplicate=True),
        Output("edit-transaction-id", "data", allow_duplicate=True),
        Output("edit-amount-input", "value", allow_duplicate=True),
        Output("edit-type-select", "value", allow_duplicate=True),
        Output("edit-date-picker", "date", allow_duplicate=True),
        Output("edit-description-input", "value", allow_duplicate=True),
        Output("recurring-edit-scope-modal", "is_open", allow_duplicate=True),
        Output("edit-skip-instance", "style"),
        Output("recurring-edit-context", "data", allow_duplicate=True),
    ],
    Input("recurring-edit-continue", "n_clicks"),
    [
        State("recurring-edit-scope", "value"),
        State("recurring-edit-context", "data"),
    ],
    prevent_initial_call=True,
)
def process_recurring_edit_scope(n_clicks, scope, context):
    """Обрабатывает выбор scope редактирования recurring операции.

    Args:
        n_clicks: Количество кликов на кнопку "Продолжить"
        scope: Выбранный scope ("instance" или "all")
        context: Контекст редактирования (transaction_id, template_id, etc.)

    Returns:
        Tuple с данными для открытия edit modal
    """
    if not n_clicks or not context:
        raise PreventUpdate

    transaction_id = context.get("transaction_id")
    template_id = context.get("template_id")
    instance_date = context.get("instance_date")

    with get_db_session() as session:
        service = TransactionService(session)

        if scope == "all":
            # Редактируем шаблон (всю серию)
            tx = service.get_by_id(template_id)
            logger.debug(f"Редактирование шаблона recurring {template_id}")
            skip_button_style = {"display": "none"}
            updated_context = None  # Не нужен контекст для шаблона
        else:
            # scope == "instance" — редактируем конкретный экземпляр
            tx = service.get_by_id(transaction_id)
            logger.debug(f"Редактирование экземпляра recurring {transaction_id}")
            skip_button_style = {"display": "inline-block"}
            # Сохраняем контекст для кнопки "Пропустить"
            updated_context = {
                "template_id": template_id,
                "instance_date": instance_date,
                "scope": scope,
            }

        if not tx:
            raise PreventUpdate

        return (
            True,  # Открыть edit modal
            tx.id,
            float(tx.amount),
            tx.transaction_type.name,
            tx.transaction_date.isoformat(),
            tx.description or "",
            False,  # Закрыть scope modal
            skip_button_style,
            updated_context,
        )


@callback(
    [
        Output("edit-modal", "is_open", allow_duplicate=True),
        Output("transactions-table", "children", allow_duplicate=True),
    ],
    Input("edit-skip-instance", "n_clicks"),
    State("recurring-edit-context", "data"),
    prevent_initial_call=True,
)
def skip_recurring_instance(n_clicks, context):
    """Пропускает экземпляр recurring операции.

    Создает exception с is_skipped=True для указанной даты.
    """
    if not n_clicks or not context:
        raise PreventUpdate

    template_id = context.get("template_id")
    instance_date_str = context.get("instance_date")

    if not template_id or not instance_date_str:
        raise PreventUpdate

    instance_date = date.fromisoformat(instance_date_str)

    with get_db_session() as session:
        recurring_service = RecurringService(session)
        transaction_service = TransactionService(session)

        # Пропускаем экземпляр через RecurringService
        recurring_service.skip_instance(template_id, instance_date)
        session.commit()

        logger.info(
            f"Пропущен экземпляр recurring {template_id} на дату {instance_date}"
        )

        # Обновляем таблицу транзакций
        transactions = transaction_service.get_all_by_user(user_id=1)
        return False, _build_transactions_table(transactions)
