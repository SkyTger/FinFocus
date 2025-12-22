"""
Компонент управления финансовыми операциями (транзакциями).
"""
from datetime import date, datetime
from decimal import Decimal

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ALL, ctx
from dash.exceptions import PreventUpdate

from models.database import get_session, create_database_engine, TransactionType
from services.transaction_service import TransactionService, ValidationError


def format_amount(amount: Decimal) -> str:
    """Форматирует сумму для отображения.

    Args:
        amount: Сумма операции

    Returns:
        str: Отформатированная строка (например, "15 000.00 ₽")
    """
    return f"{amount:,.2f} ₽".replace(",", " ")


def format_date(date_obj: date) -> str:
    """Форматирует дату для отображения.

    Args:
        date_obj: Объект даты

    Returns:
        str: Дата в формате DD.MM.YYYY
    """
    return date_obj.strftime("%d.%m.%Y")


def create_transactions_layout():
    """Создает layout страницы управления операциями.

    Returns:
        dash component: Layout страницы Transactions
    """
    return html.Div([
        # Заголовок с описанием
        html.Div([
            html.Div([
                html.H4("Операции", className="mb-1"),
                html.P("Управление доходами и расходами", className="text-muted mb-0")
            ], className="flex-grow-1"),
            dbc.Button([
                html.I(className="bi bi-plus-circle me-2"),
                "Добавить операцию"
            ], id="add-transaction-btn", color="success", className="d-flex align-items-center")
        ], className="d-flex justify-content-between align-items-center mb-4"),

        # Таблица операций
        dbc.Card([
            dbc.CardBody([
                html.Div(id="transactions-table-container", children=[
                    dbc.Table(
                        id="transactions-table",
                        striped=True,
                        hover=True,
                        responsive=True,
                        className="mb-0"
                    )
                ])
            ])
        ], className="shadow-sm"),

        # Модальное окно создания
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Добавить операцию")),
            dbc.ModalBody([
                # Сумма
                dbc.Row([
                    dbc.Label("Сумма", html_for="create-amount-input", width=3),
                    dbc.Col([
                        dbc.Input(
                            id="create-amount-input",
                            type="number",
                            step=0.01,
                            min=0.01,
                            placeholder="Введите сумму",
                            required=True
                        )
                    ], width=9)
                ], className="mb-3"),

                # Тип операции
                dbc.Row([
                    dbc.Label("Тип операции", html_for="create-type-select", width=3),
                    dbc.Col([
                        dbc.Select(
                            id="create-type-select",
                            options=[
                                {"label": "Доход", "value": "INCOME"},
                                {"label": "Расход", "value": "EXPENSE"}
                            ],
                            value="EXPENSE",
                            required=True
                        )
                    ], width=9)
                ], className="mb-3"),

                # Дата
                dbc.Row([
                    dbc.Label("Дата", html_for="create-date-picker", width=3),
                    dbc.Col([
                        dcc.DatePickerSingle(
                            id="create-date-picker",
                            date=date.today(),
                            display_format="DD.MM.YYYY",
                            first_day_of_week=1,
                            className="w-100"
                        )
                    ], width=9)
                ], className="mb-3"),

                # Описание
                dbc.Row([
                    dbc.Label("Описание", html_for="create-description-input", width=3),
                    dbc.Col([
                        dbc.Textarea(
                            id="create-description-input",
                            placeholder="Введите описание (опционально)",
                            rows=3
                        )
                    ], width=9)
                ], className="mb-3"),
            ]),
            dbc.ModalFooter([
                dbc.Button("Отмена", id="create-cancel-btn", color="secondary", className="me-2"),
                dbc.Button("Создать", id="create-submit-btn", color="success")
            ])
        ], id="create-modal", is_open=False, centered=True),

        # Модальное окно редактирования
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Редактировать операцию")),
            dbc.ModalBody([
                # Сумма
                dbc.Row([
                    dbc.Label("Сумма", html_for="edit-amount-input", width=3),
                    dbc.Col([
                        dbc.Input(
                            id="edit-amount-input",
                            type="number",
                            step=0.01,
                            min=0.01,
                            required=True
                        )
                    ], width=9)
                ], className="mb-3"),

                # Тип операции
                dbc.Row([
                    dbc.Label("Тип операции", html_for="edit-type-select", width=3),
                    dbc.Col([
                        dbc.Select(
                            id="edit-type-select",
                            options=[
                                {"label": "Доход", "value": "INCOME"},
                                {"label": "Расход", "value": "EXPENSE"}
                            ],
                            required=True
                        )
                    ], width=9)
                ], className="mb-3"),

                # Дата
                dbc.Row([
                    dbc.Label("Дата", html_for="edit-date-picker", width=3),
                    dbc.Col([
                        dcc.DatePickerSingle(
                            id="edit-date-picker",
                            display_format="DD.MM.YYYY",
                            first_day_of_week=1,
                            className="w-100"
                        )
                    ], width=9)
                ], className="mb-3"),

                # Описание
                dbc.Row([
                    dbc.Label("Описание", html_for="edit-description-input", width=3),
                    dbc.Col([
                        dbc.Textarea(
                            id="edit-description-input",
                            rows=3
                        )
                    ], width=9)
                ], className="mb-3"),
            ]),
            dbc.ModalFooter([
                dbc.Button("Отмена", id="edit-cancel-btn", color="secondary", className="me-2"),
                dbc.Button("Сохранить", id="edit-submit-btn", color="success")
            ])
        ], id="edit-modal", is_open=False, centered=True),

        # Store для хранения ID редактируемой транзакции
        dcc.Store(id="edit-transaction-id")
    ])


# ==================== CALLBACKS ====================

@callback(
    Output("transactions-table", "children"),
    Input("url", "pathname")
)
def load_transactions(pathname):
    """Загружает список операций из БД.

    Returns:
        list: Строки таблицы с операциями
    """
    if pathname != "/transactions":
        raise PreventUpdate

    # Получаем сессию БД
    engine = create_database_engine()
    session = get_session(engine)

    try:
        # Загружаем операции для user_id=1 (hardcode для MVP)
        service = TransactionService(session)
        transactions = service.get_all_by_user(user_id=1)

        # Формируем строки таблицы
        if not transactions:
            return [
                html.Thead([
                    html.Tr([
                        html.Th("Дата"),
                        html.Th("Тип"),
                        html.Th("Сумма"),
                        html.Th("Описание"),
                        html.Th("Действия", className="text-end")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td("Нет операций", colSpan=5, className="text-center text-muted")
                    ])
                ])
            ]

        # Создаем заголовок таблицы
        table_header = html.Thead([
            html.Tr([
                html.Th("Дата"),
                html.Th("Тип"),
                html.Th("Сумма", className="text-end"),
                html.Th("Описание"),
                html.Th("Действия", className="text-end")
            ])
        ])

        # Создаем строки для каждой транзакции
        table_rows = []
        for tx in transactions:
            # Определяем цвет для типа операции
            if tx.transaction_type == TransactionType.INCOME:
                type_badge = dbc.Badge("Доход", color="success", className="rounded-pill")
                amount_class = "text-success fw-bold text-end"
                amount_prefix = "+"
            else:
                type_badge = dbc.Badge("Расход", color="danger", className="rounded-pill")
                amount_class = "text-danger fw-bold text-end"
                amount_prefix = "-"

            row = html.Tr([
                html.Td(format_date(tx.transaction_date)),
                html.Td(type_badge),
                html.Td(f"{amount_prefix}{format_amount(tx.amount)}", className=amount_class),
                html.Td(tx.description or "-", className="text-muted"),
                html.Td([
                    dbc.ButtonGroup([
                        dbc.Button(
                            html.I(className="bi bi-pencil"),
                            id={"type": "edit-btn", "index": tx.id},
                            color="secondary",
                            size="sm",
                            outline=True,
                            className="me-1"
                        ),
                        dbc.Button(
                            html.I(className="bi bi-trash"),
                            id={"type": "delete-btn", "index": tx.id},
                            color="danger",
                            size="sm",
                            outline=True
                        )
                    ])
                ], className="text-end")
            ])
            table_rows.append(row)

        table_body = html.Tbody(table_rows)

        return [table_header, table_body]

    finally:
        session.close()


@callback(
    Output("create-modal", "is_open"),
    [Input("add-transaction-btn", "n_clicks"),
     Input("create-cancel-btn", "n_clicks")],
    [State("create-modal", "is_open")],
    prevent_initial_call=True
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
    [Output("create-modal", "is_open", allow_duplicate=True),
     Output("transactions-table", "children", allow_duplicate=True),
     Output("create-amount-input", "value"),
     Output("create-type-select", "value"),
     Output("create-date-picker", "date"),
     Output("create-description-input", "value")],
    Input("create-submit-btn", "n_clicks"),
    [State("create-amount-input", "value"),
     State("create-type-select", "value"),
     State("create-date-picker", "date"),
     State("create-description-input", "value")],
    prevent_initial_call=True
)
def create_transaction(n_clicks, amount, transaction_type, date_str, description):
    """Создает новую транзакцию через TransactionService.

    Returns:
        tuple: (is_open=False, обновленная таблица, очищенные поля формы)
    """
    if not n_clicks or not amount:
        raise PreventUpdate

    # Получаем сессию БД
    engine = create_database_engine()
    session = get_session(engine)

    try:
        # Конвертируем строку даты в объект date
        transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Создаем транзакцию
        service = TransactionService(session)
        service.create_transaction(
            user_id=1,  # Hardcode для MVP
            amount=Decimal(str(amount)),
            transaction_type=TransactionType[transaction_type],
            transaction_date=transaction_date,
            description=description if description else None
        )

        # Коммитим изменения
        session.commit()

        # Загружаем обновленный список транзакций
        transactions = service.get_all_by_user(user_id=1)

        # Формируем обновленную таблицу (код идентичен load_transactions)
        if not transactions:
            updated_table = [
                html.Thead([
                    html.Tr([
                        html.Th("Дата"),
                        html.Th("Тип"),
                        html.Th("Сумма"),
                        html.Th("Описание"),
                        html.Th("Действия", className="text-end")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td("Нет операций", colSpan=5, className="text-center text-muted")
                    ])
                ])
            ]
        else:
            table_header = html.Thead([
                html.Tr([
                    html.Th("Дата"),
                    html.Th("Тип"),
                    html.Th("Сумма", className="text-end"),
                    html.Th("Описание"),
                    html.Th("Действия", className="text-end")
                ])
            ])

            table_rows = []
            for tx in transactions:
                if tx.transaction_type == TransactionType.INCOME:
                    type_badge = dbc.Badge("Доход", color="success", className="rounded-pill")
                    amount_class = "text-success fw-bold text-end"
                    amount_prefix = "+"
                else:
                    type_badge = dbc.Badge("Расход", color="danger", className="rounded-pill")
                    amount_class = "text-danger fw-bold text-end"
                    amount_prefix = "-"

                row = html.Tr([
                    html.Td(format_date(tx.transaction_date)),
                    html.Td(type_badge),
                    html.Td(f"{amount_prefix}{format_amount(tx.amount)}", className=amount_class),
                    html.Td(tx.description or "-", className="text-muted"),
                    html.Td([
                        dbc.ButtonGroup([
                            dbc.Button(
                                html.I(className="bi bi-pencil"),
                                id={"type": "edit-btn", "index": tx.id},
                                color="secondary",
                                size="sm",
                                outline=True,
                                className="me-1"
                            ),
                            dbc.Button(
                                html.I(className="bi bi-trash"),
                                id={"type": "delete-btn", "index": tx.id},
                                color="danger",
                                size="sm",
                                outline=True
                            )
                        ])
                    ], className="text-end")
                ])
                table_rows.append(row)

            updated_table = [table_header, html.Tbody(table_rows)]

        # Закрываем модал и очищаем форму
        return False, updated_table, None, "EXPENSE", date.today().isoformat(), ""

    except ValidationError as e:
        # Пока не закрываем модал при ошибке валидации
        # TODO: Добавить отображение ошибки пользователю
        raise PreventUpdate

    finally:
        session.close()


@callback(
    [Output("edit-modal", "is_open"),
     Output("edit-transaction-id", "data"),
     Output("edit-amount-input", "value"),
     Output("edit-type-select", "value"),
     Output("edit-date-picker", "date"),
     Output("edit-description-input", "value")],
    [Input({"type": "edit-btn", "index": ALL}, "n_clicks"),
     Input("edit-cancel-btn", "n_clicks")],
    [State("edit-modal", "is_open")],
    prevent_initial_call=True
)
def open_edit_modal(edit_clicks_list, cancel_click, is_open):
    """Открывает модал редактирования с данными транзакции."""
    # Проверяем какая кнопка была нажата
    triggered_id = ctx.triggered_id

    # Если ничего не нажато (initial render)
    if not triggered_id:
        raise PreventUpdate

    # Если нажата кнопка отмены
    if triggered_id == "edit-cancel-btn":
        return False, None, None, None, None, None

    # Если нажата кнопка редактирования
    if not isinstance(triggered_id, dict) or triggered_id.get("type") != "edit-btn":
        raise PreventUpdate

    # Проверяем что был реальный клик (не автовызов при обновлении таблицы)
    if not ctx.triggered or ctx.triggered[0].get('value') is None:
        raise PreventUpdate

    transaction_id = triggered_id.get("index")
    if not transaction_id:
        raise PreventUpdate

    # Загружаем данные транзакции
    engine = create_database_engine()
    session = get_session(engine)

    try:
        service = TransactionService(session)
        tx = service.get_by_id(transaction_id)

        if not tx:
            raise PreventUpdate

        return (
            True,
            transaction_id,
            float(tx.amount),
            tx.transaction_type.name,
            tx.transaction_date.isoformat(),
            tx.description or ""
        )

    finally:
        session.close()


@callback(
    [Output("edit-modal", "is_open", allow_duplicate=True),
     Output("transactions-table", "children", allow_duplicate=True)],
    Input("edit-submit-btn", "n_clicks"),
    [State("edit-transaction-id", "data"),
     State("edit-amount-input", "value"),
     State("edit-type-select", "value"),
     State("edit-date-picker", "date"),
     State("edit-description-input", "value")],
    prevent_initial_call=True
)
def update_transaction(n_clicks, transaction_id, amount, transaction_type, date_str, description):
    """Обновляет транзакцию через TransactionService."""
    if not n_clicks or not transaction_id:
        raise PreventUpdate

    # Получаем сессию БД
    engine = create_database_engine()
    session = get_session(engine)

    try:
        # Конвертируем строку даты в объект date
        transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Обновляем транзакцию
        service = TransactionService(session)
        service.update_transaction(
            transaction_id=transaction_id,
            amount=Decimal(str(amount)),
            transaction_type=TransactionType[transaction_type],
            transaction_date=transaction_date,
            description=description if description else None
        )

        # Коммитим изменения
        session.commit()

        # Загружаем обновленный список транзакций
        transactions = service.get_all_by_user(user_id=1)

        # Формируем обновленную таблицу
        if not transactions:
            updated_table = [
                html.Thead([
                    html.Tr([
                        html.Th("Дата"),
                        html.Th("Тип"),
                        html.Th("Сумма"),
                        html.Th("Описание"),
                        html.Th("Действия", className="text-end")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td("Нет операций", colSpan=5, className="text-center text-muted")
                    ])
                ])
            ]
        else:
            table_header = html.Thead([
                html.Tr([
                    html.Th("Дата"),
                    html.Th("Тип"),
                    html.Th("Сумма", className="text-end"),
                    html.Th("Описание"),
                    html.Th("Действия", className="text-end")
                ])
            ])

            table_rows = []
            for tx in transactions:
                if tx.transaction_type == TransactionType.INCOME:
                    type_badge = dbc.Badge("Доход", color="success", className="rounded-pill")
                    amount_class = "text-success fw-bold text-end"
                    amount_prefix = "+"
                else:
                    type_badge = dbc.Badge("Расход", color="danger", className="rounded-pill")
                    amount_class = "text-danger fw-bold text-end"
                    amount_prefix = "-"

                row = html.Tr([
                    html.Td(format_date(tx.transaction_date)),
                    html.Td(type_badge),
                    html.Td(f"{amount_prefix}{format_amount(tx.amount)}", className=amount_class),
                    html.Td(tx.description or "-", className="text-muted"),
                    html.Td([
                        dbc.ButtonGroup([
                            dbc.Button(
                                html.I(className="bi bi-pencil"),
                                id={"type": "edit-btn", "index": tx.id},
                                color="secondary",
                                size="sm",
                                outline=True,
                                className="me-1"
                            ),
                            dbc.Button(
                                html.I(className="bi bi-trash"),
                                id={"type": "delete-btn", "index": tx.id},
                                color="danger",
                                size="sm",
                                outline=True
                            )
                        ])
                    ], className="text-end")
                ])
                table_rows.append(row)

            updated_table = [table_header, html.Tbody(table_rows)]

        # Закрываем модал
        return False, updated_table

    except ValidationError as e:
        # Пока не закрываем модал при ошибке
        raise PreventUpdate

    finally:
        session.close()


@callback(
    Output("transactions-table", "children", allow_duplicate=True),
    [Input({"type": "delete-btn", "index": ALL}, "n_clicks")],
    prevent_initial_call=True
)
def delete_transaction(n_clicks_list):
    """Удаляет транзакцию через TransactionService."""
    # Проверяем какая кнопка была нажата
    triggered_id = ctx.triggered_id

    # Если ничего не нажато (initial render или обновление таблицы)
    if not triggered_id:
        raise PreventUpdate

    if not isinstance(triggered_id, dict) or triggered_id.get("type") != "delete-btn":
        raise PreventUpdate

    # Проверяем что был реальный клик (не автовызов при обновлении таблицы)
    if not ctx.triggered or ctx.triggered[0].get('value') is None:
        raise PreventUpdate

    transaction_id = triggered_id.get("index")
    if not transaction_id:
        raise PreventUpdate

    # Получаем сессию БД
    engine = create_database_engine()
    session = get_session(engine)

    try:
        # Удаляем транзакцию
        service = TransactionService(session)
        deleted = service.delete_transaction(transaction_id)

        if not deleted:
            raise PreventUpdate

        # Коммитим изменения
        session.commit()

        # Загружаем обновленный список транзакций
        transactions = service.get_all_by_user(user_id=1)

        # Формируем обновленную таблицу
        if not transactions:
            return [
                html.Thead([
                    html.Tr([
                        html.Th("Дата"),
                        html.Th("Тип"),
                        html.Th("Сумма"),
                        html.Th("Описание"),
                        html.Th("Действия", className="text-end")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td("Нет операций", colSpan=5, className="text-center text-muted")
                    ])
                ])
            ]

        table_header = html.Thead([
            html.Tr([
                html.Th("Дата"),
                html.Th("Тип"),
                html.Th("Сумма", className="text-end"),
                html.Th("Описание"),
                html.Th("Действия", className="text-end")
            ])
        ])

        table_rows = []
        for tx in transactions:
            if tx.transaction_type == TransactionType.INCOME:
                type_badge = dbc.Badge("Доход", color="success", className="rounded-pill")
                amount_class = "text-success fw-bold text-end"
                amount_prefix = "+"
            else:
                type_badge = dbc.Badge("Расход", color="danger", className="rounded-pill")
                amount_class = "text-danger fw-bold text-end"
                amount_prefix = "-"

            row = html.Tr([
                html.Td(format_date(tx.transaction_date)),
                html.Td(type_badge),
                html.Td(f"{amount_prefix}{format_amount(tx.amount)}", className=amount_class),
                html.Td(tx.description or "-", className="text-muted"),
                html.Td([
                    dbc.ButtonGroup([
                        dbc.Button(
                            html.I(className="bi bi-pencil"),
                            id={"type": "edit-btn", "index": tx.id},
                            color="secondary",
                            size="sm",
                            outline=True,
                            className="me-1"
                        ),
                        dbc.Button(
                            html.I(className="bi bi-trash"),
                            id={"type": "delete-btn", "index": tx.id},
                            color="danger",
                            size="sm",
                            outline=True
                        )
                    ])
                ], className="text-end")
            ])
            table_rows.append(row)

        return [table_header, html.Tbody(table_rows)]

    finally:
        session.close()