"""
Глобальные модалы для CRUD операций с транзакциями.

Модалы добавляются в main.py layout и доступны на всех страницах.
Содержит:
- create-modal: модал создания операции
- edit-modal: модал редактирования операции
- recurring-edit-scope-modal: модал выбора scope для recurring
- Submit callbacks для CRUD операций
"""
from datetime import date, datetime
from decimal import Decimal

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, no_update, ctx, ALL
from dash.exceptions import PreventUpdate
from loguru import logger

from app.core import get_db_session, ValidationError
from app.models.database import TransactionType
from app.services import TransactionService, RecurringService, CategoryService
from app.utils.formatters import parse_date_safe, ICON_TO_EMOJI


# ==================== TYPE DEFINITIONS ====================


class TransactionTriggerData(dict):
    """Данные события CRUD операции для global-transaction-trigger Store.

    Keys:
        action: "create" | "update" | "delete" | "skip"
        timestamp: ISO format string
        source: "calendar" | "transactions" | None
        transaction_id: int | None
    """

    pass


# ==================== MAIN FACTORY ====================


def create_transaction_modals() -> html.Div:
    """Создает глобальный контейнер с модалами транзакций.

    Добавляется в main.py layout после основного контента.
    Содержит:
    - create-modal: модал создания операции
    - edit-modal: модал редактирования операции
    - recurring-edit-scope-modal: модал выбора scope для recurring
    - dcc.Store компоненты для состояния

    Returns:
        html.Div: Контейнер с модалами
    """
    return html.Div(
        [
            _build_create_modal(),
            _build_edit_modal(),
            _build_recurring_scope_modal(),
            _build_recurring_delete_scope_modal(),
            # State stores
            dcc.Store(id="edit-transaction-id"),
            dcc.Store(id="recurring-edit-context", data=None),
            dcc.Store(id="recurring-delete-context", data=None),  # Delete scope context
            dcc.Store(id="modal-source", data=None),  # Источник открытия модала
            dcc.Store(id="global-transaction-trigger", data=None),  # CRUD events
            # Quick-add preselection stores
            dcc.Store(id="preselected-category", data=None),
            dcc.Store(id="preselected-type", data=None),
        ],
        id="global-transaction-modals-container",
    )


# ==================== MODAL BUILDERS ====================


def _build_create_modal() -> dbc.Modal:
    """Строит модал создания операции."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Добавить операцию")),
            dbc.ModalBody(
                [
                    # Сумма
                    dbc.Row(
                        [
                            dbc.Label("Сумма", html_for="create-amount-input", width=3),
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
                            dbc.Label("Дата", html_for="create-date-picker", width=3),
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
                                                        "label": "Раз в 2 недели",
                                                        "value": "biweekly",
                                                    },
                                                    {
                                                        "label": "Ежемесячно",
                                                        "value": "monthly",
                                                    },
                                                    {
                                                        "label": "Ежеквартально",
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
                                            dbc.Label("Дата окончания (опционально)"),
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
                            # EOM checkbox (скрыт по умолчанию)
                            html.Div(
                                id="create-recurring-anchor-eom-container",
                                style={"display": "none"},
                                children=[
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Checkbox(
                                                        id="create-recurring-anchor-eom",
                                                        label="Последний день месяца",
                                                        value=False,
                                                    ),
                                                    html.Small(
                                                        "Операция будет генерироваться "
                                                        "всегда в последний день месяца",
                                                        className="text-muted",
                                                    ),
                                                ],
                                                width=12,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                ],
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
                    dbc.Button("Создать", id="create-submit-btn", color="success"),
                ]
            ),
        ],
        id="create-modal",
        is_open=False,
        centered=True,
    )


def _build_edit_modal() -> dbc.Modal:
    """Строит модал редактирования операции."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Редактировать операцию")),
            dbc.ModalBody(
                [
                    # Сумма
                    dbc.Row(
                        [
                            dbc.Label("Сумма", html_for="edit-amount-input", width=3),
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
                            dbc.Label("Дата", html_for="edit-date-picker", width=3),
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
                                [dbc.Textarea(id="edit-description-input", rows=3)],
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
                    dbc.Button("Сохранить", id="edit-submit-btn", color="success"),
                ]
            ),
        ],
        id="edit-modal",
        is_open=False,
        centered=True,
    )


def _build_recurring_scope_modal() -> dbc.Modal:
    """Строит модал выбора scope для recurring операций."""
    return dbc.Modal(
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
    )


def _build_recurring_delete_scope_modal() -> dbc.Modal:
    """Строит модал выбора scope для удаления recurring операций.

    Три варианта действия:
    - instance: Пропустить только этот экземпляр (skip_instance)
    - future: Остановить серию с этой даты (stop_template)
    - all: Удалить всю серию (delete_template)
    """
    from app.schema.recurring import DELETE_SCOPE_OPTIONS

    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Удалить повторяющуюся операцию")),
            dbc.ModalBody(
                [
                    html.P("Выберите, что вы хотите удалить:"),
                    dbc.RadioItems(
                        id="recurring-delete-scope",
                        options=[
                            {"label": opt["label"], "value": opt["value"]}
                            for opt in DELETE_SCOPE_OPTIONS
                        ],
                        value="instance",
                        className="mb-3",
                    ),
                    html.P(
                        "Примечание: удаление серии удалит все экземпляры "
                        "и внесённые изменения.",
                        className="text-muted small",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Отмена",
                        id="recurring-delete-cancel",
                        color="secondary",
                        outline=True,
                        className="me-2",
                    ),
                    dbc.Button(
                        "Удалить",
                        id="recurring-delete-continue",
                        color="danger",
                    ),
                ]
            ),
        ],
        id="recurring-delete-scope-modal",
        is_open=False,
        centered=True,
    )


# ==================== CALLBACKS ====================


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
    Output("create-recurring-anchor-eom-container", "style"),
    [
        Input("create-is-recurring", "value"),
        Input("create-recurring-period", "value"),
        Input("create-date-picker", "date"),
    ],
    prevent_initial_call=True,
)
def toggle_eom_checkbox_visibility(is_recurring, period, date_str):
    """Показывает/скрывает EOM checkbox.

    Условия показа (все должны быть True):
    1. is_recurring = True
    2. period = monthly или quarterly
    3. selected_date = последний день текущего месяца
    4. day != 31 (31 уже корректно обрабатывается Anchored)

    Args:
        is_recurring: Checkbox "Повторяющаяся операция"
        period: Период повторения
        date_str: Выбранная дата (ISO string)

    Returns:
        dict: {"display": "block"} или {"display": "none"}
    """
    # Если не recurring — скрываем
    if not is_recurring:
        return {"display": "none"}

    # Если нет даты или периода — скрываем
    if not date_str or not period:
        return {"display": "none"}

    # Парсим дату
    try:
        selected_date = parse_date_safe(date_str)
        if not selected_date:
            return {"display": "none"}
    except Exception:
        return {"display": "none"}

    # Используем RecurringService для проверки
    if RecurringService.should_show_eom_checkbox(selected_date, period):
        return {"display": "block"}

    return {"display": "none"}


@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("modal-source", "data", allow_duplicate=True),
        Output("preselected-category", "data", allow_duplicate=True),
        Output("preselected-type", "data", allow_duplicate=True),
        Output("create-category-dropdown", "value", allow_duplicate=True),
        Output("create-type-select", "value", allow_duplicate=True),
    ],
    Input("create-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def close_create_modal(n_clicks):
    """Закрывает модал создания при нажатии Отмена.

    Сбрасывает preselection и форму от Quick-add chips.
    """
    if not n_clicks:
        raise PreventUpdate
    # is_open, modal-source, preselected-category, preselected-type,
    # category-dropdown, type-select
    return False, None, None, None, None, "EXPENSE"


@callback(
    [
        Output("edit-modal", "is_open", allow_duplicate=True),
        Output("modal-source", "data", allow_duplicate=True),
    ],
    Input("edit-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def close_edit_modal(n_clicks):
    """Закрывает модал редактирования при нажатии Отмена."""
    if not n_clicks:
        raise PreventUpdate
    return False, None


@callback(
    [
        Output("create-category-dropdown", "value", allow_duplicate=True),
        Output("create-type-select", "value", allow_duplicate=True),
    ],
    Input("create-modal", "is_open"),
    [
        State("preselected-category", "data"),
        State("preselected-type", "data"),
        State("modal-source", "data"),
    ],
    prevent_initial_call=True,
)
def set_preselection_on_modal_open(
    is_open, preselected_category, preselected_type, modal_source
):
    """Устанавливает предвыбранные значения при открытии модала создания.

    Применяет preselection из Quick-add chips ТОЛЬКО если источник = "quick-add".

    Args:
        is_open: Состояние модала
        preselected_category: ID предвыбранной категории или None
        preselected_type: Предвыбранный тип ("EXPENSE"|"INCOME") или None
        modal_source: Источник открытия модала

    Returns:
        tuple: (category_value, type_value)
    """
    if not is_open:
        return no_update, no_update

    # Применяем preselection ТОЛЬКО если открыто через Quick-add
    if modal_source != "quick-add":
        return no_update, no_update

    # Применяем preselection если есть, иначе no_update
    category_value = preselected_category if preselected_category else no_update
    type_value = preselected_type if preselected_type else no_update

    return category_value, type_value


@callback(
    Output("create-category-dropdown", "options"),
    Input("create-modal", "is_open"),
    Input("create-type-select", "value"),
    prevent_initial_call=True,
)
def update_create_category_options(is_open: bool, transaction_type: str | None):
    """Обновить список категорий при открытии модала или смене типа."""
    if not is_open:
        raise PreventUpdate

    # Default тип если не выбран
    if not transaction_type:
        transaction_type = "EXPENSE"

    with get_db_session() as session:
        service = CategoryService(session)
        category_type = "income" if transaction_type == "INCOME" else "expense"
        options = service.get_for_dropdown(category_type=category_type)

        return [
            {
                "label": f"{ICON_TO_EMOJI.get(opt['icon'], '📁')} {opt['label']}",
                "value": opt["value"],
            }
            for opt in options
        ]


@callback(
    Output("edit-category-dropdown", "options", allow_duplicate=True),
    Input("edit-type-select", "value"),
    State("edit-modal", "is_open"),
    prevent_initial_call=True,
)
def update_edit_category_options(transaction_type: str | None, is_open: bool):
    """Обновляет список категорий при открытии edit-modal или смене типа."""
    if not is_open:
        raise PreventUpdate

    if not transaction_type:
        raise PreventUpdate

    try:
        with get_db_session() as session:
            service = CategoryService(session)
            category_type = "income" if transaction_type == "INCOME" else "expense"
            options = service.get_for_dropdown(category_type=category_type)

            return [
                {
                    "label": f"{ICON_TO_EMOJI.get(opt['icon'], '📁')} {opt['label']}",
                    "value": opt["value"],
                }
                for opt in options
            ]

    except Exception as e:
        logger.error(f"Ошибка загрузки категорий для edit: {e}")
        return []


@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("global-transaction-trigger", "data", allow_duplicate=True),
        Output("modal-source", "data", allow_duplicate=True),
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
        Output("preselected-category", "data", allow_duplicate=True),
        Output("preselected-type", "data", allow_duplicate=True),
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
        State("create-recurring-anchor-eom", "value"),
        State("modal-source", "data"),
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
    anchor_eom,
    modal_source,
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
            no_update,
            "Неверный формат даты",
            True,  # Показать Alert
            no_update,  # preselected-category
            no_update,  # preselected-type
        )

    # Парсинг даты окончания recurring (если указана)
    parsed_end_date = None
    if is_recurring and recurring_end_date:
        parsed_end_date = parse_date_safe(recurring_end_date)

    try:
        with get_db_session() as session:
            service = TransactionService(session)
            new_tx = service.create_transaction(
                user_id=1,
                amount=Decimal(str(amount)),
                transaction_type=TransactionType[transaction_type],
                transaction_date=transaction_date,
                description=description if description else None,
                category_id=category_id,
                is_recurring=is_recurring or False,
                recurring_period=recurring_period if is_recurring else None,
                recurring_end_date=parsed_end_date,
                recurring_anchor_eom=bool(anchor_eom) if is_recurring else False,
            )
            session.commit()

            log_msg = f"Создана транзакция: {transaction_type} {amount}"
            if is_recurring:
                log_msg += f" (recurring: {recurring_period})"
            logger.info(log_msg)

            # Формируем trigger для обновления страниц
            trigger_data: TransactionTriggerData = {
                "action": "create",
                "timestamp": datetime.now().isoformat(),
                "source": modal_source,
                "transaction_id": new_tx.id,
            }

            # Успех: закрываем модал, очищаем форму, emit trigger
            return (
                False,  # is_open
                trigger_data,  # global-transaction-trigger
                None,  # modal-source reset
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
                None,  # preselected-category reset
                None,  # preselected-type reset
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
            no_update,
            str(e),  # Текст ошибки
            True,  # Показать Alert
            no_update,  # preselected-category
            no_update,  # preselected-type
        )


@callback(
    [
        Output("edit-modal", "is_open", allow_duplicate=True),
        Output("global-transaction-trigger", "data", allow_duplicate=True),
        Output("modal-source", "data", allow_duplicate=True),
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
        State("modal-source", "data"),
    ],
    prevent_initial_call=True,
)
def update_transaction(
    n_clicks,
    transaction_id,
    amount,
    transaction_type,
    category_id,
    date_str,
    description,
    modal_source,
):
    """Обновляет транзакцию через TransactionService."""
    if not n_clicks or not transaction_id:
        raise PreventUpdate

    # Безопасный парсинг даты
    transaction_date = parse_date_safe(date_str)
    if not transaction_date:
        return True, no_update, no_update, "Неверный формат даты", True

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
            session.commit()

            logger.info(f"Обновлена транзакция {transaction_id}")

            # Формируем trigger
            trigger_data: TransactionTriggerData = {
                "action": "update",
                "timestamp": datetime.now().isoformat(),
                "source": modal_source,
                "transaction_id": transaction_id,
            }

            return False, trigger_data, None, "", False

    except ValidationError as e:
        logger.warning(f"Ошибка валидации при обновлении: {e}")
        return True, no_update, no_update, str(e), True


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
        Output("edit-category-dropdown", "value", allow_duplicate=True),
        Output("transaction-error-alert", "children", allow_duplicate=True),
        Output("transaction-error-alert", "is_open", allow_duplicate=True),
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

    При выборе "instance" для виртуальной операции (без transaction_id)
    автоматически создаёт exception через RecurringService.
    """
    if not n_clicks or not context:
        raise PreventUpdate

    transaction_id = context.get("transaction_id")
    template_id = context.get("template_id")
    instance_date_str = context.get("instance_date")

    if not template_id:
        logger.warning("process_recurring_edit_scope: template_id отсутствует")
        raise PreventUpdate

    try:
        with get_db_session() as session:
            tx_service = TransactionService(session)

            if scope == "all":
                # Редактируем шаблон (всю серию)
                tx = tx_service.get_by_id(template_id)
                if not tx:
                    raise PreventUpdate
                logger.debug(f"Редактирование шаблона recurring {template_id}")
                skip_button_style = {"display": "none"}
                updated_context = None  # Не нужен контекст для шаблона
            else:
                # scope == "instance" — редактируем конкретный экземпляр
                if transaction_id:
                    # Exception уже существует — редактируем его
                    tx = tx_service.get_by_id(transaction_id)
                    if not tx:
                        raise PreventUpdate
                    logger.debug(
                        f"Редактирование существующего exception {transaction_id}"
                    )
                else:
                    # Виртуальная операция — создаём exception для редактирования
                    if not instance_date_str:
                        logger.warning(
                            "process_recurring_edit_scope: instance_date отсутствует"
                        )
                        raise PreventUpdate

                    instance_date = date.fromisoformat(instance_date_str)
                    recurring_service = RecurringService(session)

                    # create_exception создаст новый или вернёт существующий
                    tx = recurring_service.create_exception(
                        template_id=template_id,
                        original_date=instance_date,
                    )
                    session.commit()
                    logger.debug(
                        f"Создан exception {tx.id} для шаблона {template_id} "
                        f"на дату {instance_date}"
                    )

                skip_button_style = {"display": "inline-block"}
                # Сохраняем контекст для кнопки "Пропустить"
                updated_context = {
                    "template_id": template_id,
                    "instance_date": instance_date_str,
                    "scope": scope,
                }

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
                tx.category_id,  # Категория для dropdown
                "",  # Нет ошибки
                False,  # Скрыть alert
            )

    except ValidationError as e:
        logger.warning(f"Ошибка при редактировании recurring: {e}")
        return (
            False,  # Закрыть edit modal
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            False,  # Закрыть scope modal
            no_update,
            no_update,
            no_update,
            str(e),  # Текст ошибки
            True,  # Показать alert
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка при редактировании recurring: {e}")
        return (
            False,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            False,
            no_update,
            no_update,
            no_update,
            "Произошла ошибка при обработке операции",
            True,
        )


@callback(
    [
        Output("edit-modal", "is_open", allow_duplicate=True),
        Output("global-transaction-trigger", "data", allow_duplicate=True),
        Output("modal-source", "data", allow_duplicate=True),
    ],
    Input("edit-skip-instance", "n_clicks"),
    [
        State("recurring-edit-context", "data"),
        State("modal-source", "data"),
    ],
    prevent_initial_call=True,
)
def skip_recurring_instance(n_clicks, context, modal_source):
    """Пропускает экземпляр recurring операции."""
    if not n_clicks or not context:
        raise PreventUpdate

    template_id = context.get("template_id")
    instance_date_str = context.get("instance_date")

    if not template_id or not instance_date_str:
        raise PreventUpdate

    instance_date = date.fromisoformat(instance_date_str)

    try:
        with get_db_session() as session:
            recurring_service = RecurringService(session)
            recurring_service.skip_instance(template_id, instance_date)
            session.commit()

            logger.info(
                f"Пропущен экземпляр recurring {template_id} на дату {instance_date}"
            )

            # Emit trigger
            trigger_data: TransactionTriggerData = {
                "action": "skip",
                "timestamp": datetime.now().isoformat(),
                "source": modal_source,
                "transaction_id": None,
            }

            return False, trigger_data, None

    except Exception as e:
        logger.error(f"Ошибка пропуска recurring: {e}")
        raise PreventUpdate


# ==================== DELETE CALLBACKS ====================


@callback(
    Output("recurring-delete-scope-modal", "is_open"),
    Input("recurring-delete-cancel", "n_clicks"),
    prevent_initial_call=True,
)
def cancel_delete_scope(n_clicks):
    """Закрывает модал выбора scope для удаления."""
    if not n_clicks:
        raise PreventUpdate
    return False


@callback(
    [
        Output("recurring-delete-scope-modal", "is_open", allow_duplicate=True),
        Output("recurring-delete-context", "data"),
        Output("global-transaction-trigger", "data", allow_duplicate=True),
    ],
    Input({"type": "delete-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def handle_delete_click(n_clicks_list):
    """Обрабатывает клик на delete-btn (ЕДИНСТВЕННЫЙ callback).

    Решает Callback Collision — вся логика удаления в одном месте.

    - Если recurring → открывает scope modal, сохраняет context
    - Если обычная → удаляет сразу, emits trigger

    ADR-003 Guard Clauses:
    - Guard #1: ctx.triggered_id existence
    - Guard #2: isinstance(triggered_id, dict)
    - Guard #3: triggered_id["type"] == "delete-btn"
    - Guard #4: ctx.triggered[0].get("value") is not None
    """
    triggered_id = ctx.triggered_id

    # Guard #1: проверка наличия triggered_id
    if not triggered_id:
        raise PreventUpdate

    # Guard #2: проверка типа triggered_id
    if not isinstance(triggered_id, dict):
        raise PreventUpdate

    # Guard #3: проверка типа кнопки
    if triggered_id.get("type") != "delete-btn":
        raise PreventUpdate

    # Guard #4: проверка реального клика (не автовызов)
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

        # Проверяем: является ли recurring (шаблон или экземпляр серии)
        is_recurring_related = tx.is_recurring or tx.recurring_parent_id is not None

        if is_recurring_related:
            # Открываем модал выбора scope
            # Определяем template_id
            if tx.is_recurring:
                template_id = tx.id
            else:
                template_id = tx.recurring_parent_id

            # Определяем instance_date
            if tx.original_date:
                instance_date = tx.original_date.isoformat()
            else:
                instance_date = tx.transaction_date.isoformat()

            context = {
                "template_id": template_id,
                "instance_date": instance_date,
            }

            logger.debug(f"Открытие delete scope modal для recurring: {context}")

            # modal_open=True, context, no trigger
            return True, context, no_update

        else:
            # Обычная транзакция — удаляем сразу
            deleted = service.delete_transaction(transaction_id)

            if not deleted:
                raise PreventUpdate

            session.commit()
            logger.info(f"Удалена обычная транзакция {transaction_id}")

            # Emit trigger для обновления других страниц
            trigger_data: TransactionTriggerData = {
                "action": "delete",
                "timestamp": datetime.now().isoformat(),
                "source": "transactions",
                "transaction_id": transaction_id,
            }

            # modal_open=False, no context, trigger
            return False, None, trigger_data


@callback(
    [
        Output("global-transaction-trigger", "data", allow_duplicate=True),
        Output("recurring-delete-scope-modal", "is_open", allow_duplicate=True),
    ],
    Input("recurring-delete-continue", "n_clicks"),
    [
        State("recurring-delete-scope", "value"),
        State("recurring-delete-context", "data"),
    ],
    prevent_initial_call=True,
)
def process_delete_scope(n_clicks, scope: str, context: dict):
    """Выполняет выбранное действие удаления recurring.

    Args:
        n_clicks: Клик на кнопку "Удалить"
        scope: "instance" | "future" | "all"
        context: RecurringDeleteContext {template_id, instance_date}

    Returns:
        tuple: (trigger_data, modal_is_open=False)

    Actions:
        - "instance": RecurringService.skip_instance(template_id, instance_date)
        - "future": RecurringService.stop_template(template_id, stop_date=instance_date)
        - "all": RecurringService.delete_template(template_id)
    """
    # Guard: проверяем клик
    if not n_clicks:
        raise PreventUpdate

    # Guard: проверяем контекст
    if not context:
        raise PreventUpdate

    template_id = context.get("template_id")
    instance_date_str = context.get("instance_date")

    if not template_id or not instance_date_str:
        raise PreventUpdate

    instance_date = date.fromisoformat(instance_date_str)

    try:
        with get_db_session() as session:
            recurring_service = RecurringService(session)

            if scope == "instance":
                # Пропустить только этот экземпляр
                recurring_service.skip_instance(template_id, instance_date)
                logger.info(
                    f"Пропущен экземпляр recurring {template_id}: {instance_date}"
                )
                action = "skip"

            elif scope == "future":
                # Остановить серию с этой даты
                # stop_date должна быть днём ДО instance_date
                from datetime import timedelta

                stop_date = instance_date - timedelta(days=1)
                recurring_service.stop_template(template_id, stop_date)
                logger.info(f"Остановлен шаблон {template_id} с даты {stop_date}")
                action = "delete"

            elif scope == "all":
                # Удалить всю серию
                recurring_service.delete_template(template_id)
                logger.info(f"Удалён шаблон {template_id} и все exceptions")
                action = "delete"

            else:
                # Невалидный scope
                logger.warning(f"Невалидный scope: {scope}")
                raise PreventUpdate

            session.commit()

            # Emit trigger
            trigger_data: TransactionTriggerData = {
                "action": action,
                "timestamp": datetime.now().isoformat(),
                "source": "transactions",
                "transaction_id": template_id,
            }

            return trigger_data, False

    except ValidationError as e:
        logger.error(f"Ошибка удаления recurring: {e}")
        raise PreventUpdate
    except Exception as e:
        logger.error(f"Неожиданная ошибка удаления recurring: {e}")
        raise PreventUpdate
