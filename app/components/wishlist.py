"""UI компонент для управления списком отложенных покупок (Wishlist)."""

from decimal import Decimal, InvalidOperation

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ctx, no_update, ALL
from dash.exceptions import PreventUpdate
from loguru import logger

from app.core import get_db_session
from app.services import (
    CategoryService,
    TransactionService,
    WishlistService,
)

# Константы
DEFAULT_USER_ID = 1


# === Widget (Dashboard карточка) ===


def build_wishlist_widget() -> dbc.Card:
    """Виджет списка покупок для Dashboard.

    Показывает до 5 фокусных покупок (priority=1) и кнопку «Все покупки».

    Returns:
        dbc.Card: Карточка виджета.
    """
    try:
        with get_db_session() as session:
            svc = WishlistService(session)
            items = svc.get_focus(DEFAULT_USER_ID, limit=5)
            items_data = [svc.to_data(i) for i in items]
    except Exception as e:
        logger.error(f"Error loading wishlist widget: {e}")
        items_data = []

    if not items_data:
        body_content = [
            html.P(
                "Нет отложенных покупок",
                className="text-muted text-center my-3",
            ),
        ]
    else:
        body_content = [_build_widget_item(item) for item in items_data]

    return dbc.Card(
        [
            dbc.CardHeader(
                html.Div(
                    [
                        html.H6(
                            [
                                html.I(className="bi bi-bag-heart me-2"),
                                "Отложенные покупки",
                            ],
                            className="mb-0",
                        ),
                        dbc.Button(
                            "Все покупки",
                            id="open-wishlist-modal-btn",
                            color="link",
                            size="sm",
                            className="p-0",
                        ),
                    ],
                    className="d-flex justify-content-between align-items-center",
                ),
            ),
            dbc.CardBody(body_content, className="wishlist-widget-body"),
        ],
        className="wishlist-widget mb-3",
    )


def _build_widget_item(item: dict) -> html.Div:
    """Карточка одной покупки в виджете."""
    status_badge = None
    if item["status"] == "planned":
        status_badge = dbc.Badge(
            f"Запланировано: {item['planned_date']}"
            if item["planned_date"]
            else "Запланировано",
            color="success",
            className="ms-2",
        )

    icon = item.get("category_icon") or "bi-bag"

    return html.Div(
        [
            html.Div(
                [
                    html.I(className=f"{icon} me-2 text-muted"),
                    html.Span(item["name"], className="fw-medium"),
                    status_badge,
                ],
                className="d-flex align-items-center",
            ),
            html.Span(
                item["amount"],
                className="text-nowrap fw-bold",
            ),
        ],
        className=(
            "d-flex justify-content-between align-items-center"
            " py-2 border-bottom wishlist-widget-item"
        ),
    )


# === Modal ===


def create_wishlist_modal() -> html.Div:
    """Создаёт модал управления списком покупок.

    Returns:
        html.Div: Контейнер с модалом и Stores.
    """
    return html.Div(
        [
            dcc.Store(id="wishlist-replan-item-id"),
            dcc.Store(id="wishlist-refresh-trigger"),
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(
                            [
                                html.I(className="bi bi-bag-heart me-2"),
                                "Отложенные покупки",
                            ]
                        ),
                        close_button=True,
                    ),
                    dbc.ModalBody(
                        [
                            _build_add_form(),
                            html.Hr(),
                            html.Div(id="wishlist-items-container"),
                        ]
                    ),
                ],
                id="wishlist-modal",
                is_open=False,
                size="lg",
                scrollable=True,
            ),
            _build_replan_confirm_modal(),
        ]
    )


def _build_add_form() -> dbc.Card:
    """Inline-форма добавления покупки."""
    return dbc.Card(
        dbc.CardBody(
            [
                html.H6("Добавить покупку", className="mb-3"),
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Input(
                                id="wishlist-add-name",
                                placeholder="Название",
                                type="text",
                                maxLength=100,
                            ),
                            md=4,
                        ),
                        dbc.Col(
                            dbc.Input(
                                id="wishlist-add-amount",
                                placeholder="Сумма",
                                type="number",
                                min=0.01,
                                step=0.01,
                            ),
                            md=3,
                        ),
                        dbc.Col(
                            dcc.Dropdown(
                                id="wishlist-add-category",
                                placeholder="Категория",
                                clearable=True,
                            ),
                            md=3,
                        ),
                        dbc.Col(
                            dbc.Button(
                                html.I(className="bi bi-plus-lg"),
                                id="wishlist-add-btn",
                                color="primary",
                                className="w-100",
                            ),
                            md=2,
                        ),
                    ],
                    className="g-2",
                ),
                dbc.Alert(
                    id="wishlist-add-error",
                    color="danger",
                    is_open=False,
                    className="mt-2 mb-0",
                    dismissable=True,
                ),
            ]
        ),
        className="wishlist-add-form mb-3",
    )


def _build_replan_confirm_modal() -> dbc.Modal:
    """Модал подтверждения перепланирования."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle("Перепланирование"),
                close_button=True,
            ),
            dbc.ModalBody(
                [
                    html.P(
                        "Текущая запланированная транзакция будет удалена. "
                        "Вы сможете выбрать новую дату в календаре."
                    ),
                    html.P(
                        "Это действие нельзя отменить.",
                        className="text-muted small",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Отмена",
                        id="cancel-replan-btn",
                        color="secondary",
                        outline=True,
                    ),
                    dbc.Button(
                        "Переплан.",
                        id="confirm-replan-btn",
                        color="warning",
                    ),
                ]
            ),
        ],
        id="replan-confirm-modal",
        is_open=False,
        centered=True,
    )


def _build_items_list(items_data: list[dict]) -> html.Div:
    """Рендер списка покупок внутри модала."""
    focus = [i for i in items_data if i["priority"] == 1]
    later = [i for i in items_data if i["priority"] == 2]

    sections = []

    if focus:
        sections.append(
            html.Div(
                [
                    html.H6(
                        [
                            html.Span("", className="wishlist-priority-dot focus me-2"),
                            "Фокусные покупки",
                        ],
                        className="mb-2",
                    ),
                    *[_build_modal_item(i) for i in focus],
                ],
                className="mb-3",
            )
        )

    if later:
        sections.append(
            html.Div(
                [
                    html.H6(
                        [
                            html.Span("", className="wishlist-priority-dot later me-2"),
                            "Отложенные",
                        ],
                        className="mb-2",
                    ),
                    *[_build_modal_item(i) for i in later],
                ],
            )
        )

    if not sections:
        sections.append(
            html.P(
                "Список пуст. Добавьте первую покупку!",
                className="text-muted text-center my-4",
            )
        )

    return html.Div(sections)


def _build_modal_item(item: dict) -> dbc.Card:
    """Карточка покупки внутри модала."""
    item_id = item["id"]
    is_planned = item["status"] == "planned"
    icon = item.get("category_icon") or "bi-bag"

    # Кнопки действий
    action_buttons = []

    if is_planned:
        # Для planned: Переплан. кнопка
        action_buttons.append(
            dbc.Button(
                [html.I(className="bi bi-arrow-repeat me-1"), "Переплан."],
                id={"type": "wishlist-replan-btn", "index": item_id},
                color="warning",
                size="sm",
                outline=True,
                className="me-1",
            )
        )
    else:
        # Для new: Запланировать кнопка
        action_buttons.append(
            dbc.Button(
                [html.I(className="bi bi-calendar-check me-1"), "Дата"],
                id={"type": "wishlist-plan-btn", "index": item_id},
                color="success",
                size="sm",
                outline=True,
                className="me-1",
            )
        )

    action_buttons.extend(
        [
            dbc.Button(
                html.I(className="bi bi-pencil"),
                id={"type": "wishlist-edit-btn", "index": item_id},
                color="secondary",
                size="sm",
                outline=True,
                className="me-1",
            ),
            dbc.Button(
                html.I(className="bi bi-trash"),
                id={"type": "wishlist-delete-btn", "index": item_id},
                color="danger",
                size="sm",
                outline=True,
            ),
        ]
    )

    # Status badge
    status_badge = None
    if is_planned and item.get("planned_date"):
        status_badge = dbc.Badge(
            item["planned_date"],
            color="success",
            className="ms-2",
        )

    category_text = item.get("category_name") or ""

    return dbc.Card(
        dbc.CardBody(
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.I(className=f"{icon} me-2"),
                                html.Strong(item["name"]),
                                status_badge,
                            ],
                            className="d-flex align-items-center",
                        ),
                        md=5,
                    ),
                    dbc.Col(
                        html.Span(category_text, className="text-muted small"),
                        md=2,
                    ),
                    dbc.Col(
                        html.Span(item["amount"], className="fw-bold"),
                        md=2,
                        className="text-end",
                    ),
                    dbc.Col(
                        html.Div(
                            action_buttons,
                            className="d-flex justify-content-end",
                        ),
                        md=3,
                    ),
                ],
                className="align-items-center",
            ),
            className="py-2",
        ),
        className="wishlist-item-card mb-2",
    )


# === Callbacks ===


@callback(
    Output("wishlist-modal", "is_open", allow_duplicate=True),
    Output("wishlist-items-container", "children"),
    Output("wishlist-add-category", "options"),
    Input("open-wishlist-modal-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_wishlist_modal(n_clicks):
    """Открывает модал и загружает данные."""
    if not n_clicks:
        raise PreventUpdate

    try:
        with get_db_session() as session:
            svc = WishlistService(session)
            items = svc.get_all(DEFAULT_USER_ID)
            items_data = [svc.to_data(i) for i in items]

            cat_svc = CategoryService(session)
            cat_options = cat_svc.get_for_dropdown(category_type="expense")
            dropdown_opts = [
                {"label": f"{opt['icon']} {opt['label']}", "value": opt["value"]}
                for opt in cat_options
            ]
    except Exception as e:
        logger.error(f"Error opening wishlist modal: {e}")
        items_data = []
        dropdown_opts = []

    return True, _build_items_list(items_data), dropdown_opts


@callback(
    Output("wishlist-modal", "is_open", allow_duplicate=True),
    Input("wishlist-modal", "is_open"),
    prevent_initial_call=True,
)
def close_wishlist_modal_on_escape(is_open):
    """Закрывает модал по close_button."""
    return is_open


@callback(
    Output("wishlist-items-container", "children", allow_duplicate=True),
    Output("wishlist-add-name", "value"),
    Output("wishlist-add-amount", "value"),
    Output("wishlist-add-category", "value"),
    Output("wishlist-add-error", "children"),
    Output("wishlist-add-error", "is_open"),
    Input("wishlist-add-btn", "n_clicks"),
    State("wishlist-add-name", "value"),
    State("wishlist-add-amount", "value"),
    State("wishlist-add-category", "value"),
    prevent_initial_call=True,
)
def add_wishlist_item(n_clicks, name, amount, category_id):
    """Добавляет покупку через inline-форму."""
    if not n_clicks:
        raise PreventUpdate

    if not name or not name.strip():
        return no_update, no_update, no_update, no_update, "Введите название", True

    if not amount:
        return no_update, no_update, no_update, no_update, "Введите сумму", True

    try:
        amount_dec = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        return no_update, no_update, no_update, no_update, "Некорректная сумма", True

    try:
        with get_db_session() as session:
            svc = WishlistService(session)
            svc.create_item(
                user_id=DEFAULT_USER_ID,
                name=name.strip(),
                amount=amount_dec,
                category_id=int(category_id) if category_id else None,
            )
            session.commit()

            # Обновляем список
            items = svc.get_all(DEFAULT_USER_ID)
            items_data = [svc.to_data(i) for i in items]
    except Exception as e:
        logger.error(f"Error adding wishlist item: {e}")
        return no_update, no_update, no_update, no_update, str(e), True

    return _build_items_list(items_data), "", None, None, "", False


@callback(
    Output("wishlist-items-container", "children", allow_duplicate=True),
    Input({"type": "wishlist-delete-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def delete_wishlist_item(n_clicks_list):
    """Удаляет покупку."""
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        raise PreventUpdate

    item_id = triggered["index"]

    try:
        with get_db_session() as session:
            svc = WishlistService(session)
            svc.delete_item(item_id)
            session.commit()

            items = svc.get_all(DEFAULT_USER_ID)
            items_data = [svc.to_data(i) for i in items]
    except Exception as e:
        logger.error(f"Error deleting wishlist item {item_id}: {e}")
        raise PreventUpdate

    return _build_items_list(items_data)


@callback(
    Output("wishlist-items-container", "children", allow_duplicate=True),
    Input({"type": "wishlist-edit-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def edit_wishlist_item(n_clicks_list):
    """Переключает приоритет покупки (упрощённый inline-edit).

    Полноценный edit modal — future scope. Для MVP меняем priority: 1↔2.
    """
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        raise PreventUpdate

    item_id = triggered["index"]

    try:
        with get_db_session() as session:
            svc = WishlistService(session)
            item = svc.get_by_id(item_id)
            if item:
                new_priority = 2 if item.priority == 1 else 1
                svc.update_item(item_id, priority=new_priority)
                session.commit()

            items = svc.get_all(DEFAULT_USER_ID)
            items_data = [svc.to_data(i) for i in items]
    except Exception as e:
        logger.error(f"Error editing wishlist item {item_id}: {e}")
        raise PreventUpdate

    return _build_items_list(items_data)


@callback(
    Output("replan-confirm-modal", "is_open", allow_duplicate=True),
    Output("wishlist-replan-item-id", "data"),
    Input({"type": "wishlist-replan-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_replan_confirm(n_clicks_list):
    """Открывает confirm dialog для перепланирования."""
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        raise PreventUpdate

    return True, triggered["index"]


@callback(
    Output("replan-confirm-modal", "is_open", allow_duplicate=True),
    Input("cancel-replan-btn", "n_clicks"),
    prevent_initial_call=True,
)
def cancel_replan(n_clicks):
    """Закрывает confirm dialog."""
    if not n_clicks:
        raise PreventUpdate
    return False


@callback(
    Output("replan-confirm-modal", "is_open", allow_duplicate=True),
    Output("wishlist-items-container", "children", allow_duplicate=True),
    Output("url", "pathname", allow_duplicate=True),
    Output("url", "search", allow_duplicate=True),
    Input("confirm-replan-btn", "n_clicks"),
    State("wishlist-replan-item-id", "data"),
    prevent_initial_call=True,
)
def execute_replan(n_clicks, item_id):
    """Удаляет транзакцию → reset_planned → redirect /calendar?wishlist_item=ID."""
    if not n_clicks:
        raise PreventUpdate

    if not item_id:
        raise PreventUpdate

    try:
        with get_db_session() as session:
            svc = WishlistService(session)
            item = svc.get_by_id(item_id)
            if not item:
                raise PreventUpdate

            # Удаляем привязанную транзакцию
            if item.planned_transaction_id:
                txn_svc = TransactionService(session)
                txn_svc.delete_transaction(item.planned_transaction_id)

            # Сбрасываем planned
            svc.reset_planned(item_id)
            session.commit()

    except Exception as e:
        logger.error(f"Error replanning wishlist item {item_id}: {e}")
        raise PreventUpdate

    # Redirect в календарь для выбора новой даты
    return False, no_update, "/calendar", f"?wishlist_item={item_id}"


@callback(
    Output("url", "pathname", allow_duplicate=True),
    Output("url", "search", allow_duplicate=True),
    Output("wishlist-modal", "is_open", allow_duplicate=True),
    Input({"type": "wishlist-plan-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def navigate_to_calendar_for_planning(n_clicks_list):
    """Запланировать: redirect /calendar?wishlist_item=ID."""
    if not n_clicks_list or not any(n_clicks_list):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        raise PreventUpdate

    item_id = triggered["index"]
    return "/calendar", f"?wishlist_item={item_id}", False


@callback(
    Output("wishlist-active-item", "data", allow_duplicate=True),
    Output("wishlist-refresh-trigger", "data", allow_duplicate=True),
    Input("global-transaction-trigger", "data"),
    State("wishlist-active-item", "data"),
    prevent_initial_call=True,
)
def handle_wishlist_after_transaction(trigger_data, wishlist_item_id):
    """Обрабатывает wishlist после создания/удаления транзакции.

    Два сценария:
    1. source="wishlist" → mark_as_planned (создание из wishlist-mode)
    2. action="delete" → orphan detection (удалена транзакция planned item)
    """
    if not trigger_data or not isinstance(trigger_data, dict):
        raise PreventUpdate

    from datetime import datetime

    # Сценарий 1: создание транзакции из wishlist-mode → mark as planned
    if trigger_data.get("source") == "wishlist":
        item_id = trigger_data.get("wishlist_item_id")
        transaction_id = trigger_data.get("transaction_id")

        if not item_id or not transaction_id:
            raise PreventUpdate

        try:
            with get_db_session() as session:
                svc = WishlistService(session)
                txn_svc = TransactionService(session)
                tx = txn_svc.get_by_id(transaction_id)
                if not tx:
                    logger.warning(
                        f"mark_wishlist_planned: transaction {transaction_id} not found"
                    )
                    raise PreventUpdate

                svc.mark_as_planned(item_id, tx.transaction_date, transaction_id)
                session.commit()
                logger.info(
                    f"Wishlist item {item_id} marked as planned "
                    f"(txn={transaction_id}, date={tx.transaction_date})"
                )
        except Exception as e:
            logger.error(f"Error marking wishlist planned: {e}")
            raise PreventUpdate

        return None, {"timestamp": datetime.now().isoformat()}

    # Сценарий 2: удаление транзакции → orphan detection
    if trigger_data.get("action") == "delete":
        try:
            with get_db_session() as session:
                svc = WishlistService(session)
                orphans = svc.check_orphaned_planned(DEFAULT_USER_ID)

                if not orphans:
                    raise PreventUpdate

                for orphan in orphans:
                    svc.reset_planned(orphan.id)
                    logger.info(f"Reset orphaned wishlist item {orphan.id}")

                session.commit()
        except PreventUpdate:
            raise
        except Exception as e:
            logger.error(f"Error detecting orphaned wishlist items: {e}")
            raise PreventUpdate

        return no_update, {"timestamp": datetime.now().isoformat()}

    raise PreventUpdate
