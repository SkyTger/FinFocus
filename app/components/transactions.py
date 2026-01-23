"""
Компонент управления финансовыми операциями (транзакциями).

Модалы создания/редактирования вынесены в transaction_modals.py
для глобальной доступности на всех страницах.
"""
import dash_bootstrap_components as dbc
from dash import html, callback, Input, Output, State, ALL, ctx
from dash.exceptions import PreventUpdate

from loguru import logger

from app.core import get_db_session
from app.models.database import TransactionType
from app.services import TransactionService, CategoryService
from app.utils.formatters import format_amount, format_date, ICON_TO_EMOJI


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

    Модалы создания/редактирования находятся в глобальном layout (main.py).

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
            # Alert для ошибок валидации находится в main.py (глобальный)
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
            # Модалы теперь в глобальном layout (main.py -> transaction_modals.py)
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
    [
        Output("create-modal", "is_open"),
        Output("modal-source", "data"),
    ],
    Input("add-transaction-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_create_modal_from_transactions(n_clicks):
    """Открывает модальное окно создания со страницы транзакций."""
    # Строгая проверка: только реальный клик
    if not n_clicks or n_clicks == 0:
        raise PreventUpdate
    if not ctx.triggered_id or ctx.triggered_id != "add-transaction-btn":
        raise PreventUpdate
    return True, "transactions"


@callback(
    [
        Output("edit-modal", "is_open"),
        Output("modal-source", "data", allow_duplicate=True),
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
    Input({"type": "edit-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_edit_modal(edit_clicks_list):
    """Открывает модал редактирования с данными транзакции.

    Для recurring операций показывает диалог выбора scope.
    """
    # Проверяем какая кнопка была нажата
    triggered_id = ctx.triggered_id

    # Если ничего не нажато (initial render)
    if not triggered_id:
        raise PreventUpdate

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
            return (
                False,
                "transactions",
                None,
                None,
                None,
                None,
                [],
                None,
                None,
                True,
                context,
            )

        # Обычная транзакция — открываем edit modal напрямую
        logger.debug(f"Открыт модал редактирования для транзакции {transaction_id}")

        # Загружаем категории для типа транзакции
        category_service = CategoryService(session)
        category_type = (
            "income" if tx.transaction_type == TransactionType.INCOME else "expense"
        )
        category_options = category_service.get_for_dropdown(
            category_type=category_type
        )
        dropdown_options = [
            {
                "label": f"{ICON_TO_EMOJI.get(opt['icon'], '📁')} {opt['label']}",
                "value": opt["value"],
            }
            for opt in category_options
        ]

        return (
            True,
            "transactions",
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
        Output("transactions-table", "children", allow_duplicate=True),
        Output("global-transaction-trigger", "data", allow_duplicate=True),
    ],
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

        # Emit trigger для обновления других страниц
        from datetime import datetime

        trigger_data = {
            "action": "delete",
            "timestamp": datetime.now().isoformat(),
            "source": "transactions",
            "transaction_id": transaction_id,
        }

        return _build_transactions_table(transactions), trigger_data


@callback(
    Output("transactions-table", "children", allow_duplicate=True),
    Input("global-transaction-trigger", "data"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def refresh_table_after_crud(trigger, pathname):
    """Обновляет таблицу после CRUD операции из другой страницы.

    Срабатывает когда:
    - Транзакция создана/обновлена из календаря
    - И пользователь на странице /transactions

    Args:
        trigger: Данные триггера с action, timestamp, source
        pathname: Текущий URL

    Returns:
        Обновленная таблица транзакций
    """
    if not trigger:
        raise PreventUpdate

    # Обновляем только если мы на странице транзакций
    if pathname != "/transactions":
        raise PreventUpdate

    # Не обновляем если источник — сама страница transactions
    # (уже обновлено через прямой Output)
    source = trigger.get("source")
    if source == "transactions":
        raise PreventUpdate

    with get_db_session() as session:
        service = TransactionService(session)
        transactions = service.get_all_by_user(user_id=1)

        logger.debug(f"Таблица транзакций обновлена после CRUD из {source}")
        return _build_transactions_table(transactions)
