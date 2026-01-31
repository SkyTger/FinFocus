"""
Компонент управления финансовыми операциями (транзакциями).

Модалы создания/редактирования вынесены в transaction_modals.py
для глобальной доступности на всех страницах.

TODO: Заменить hardcoded user_id=1 на auth context после реализации
      системы аутентификации (Batch 4+). Текущий MVP работает в single-user mode.
"""
import dash_bootstrap_components as dbc
from dash import dcc, html, callback, Input, Output, State, ALL, ctx, no_update
from dash.exceptions import PreventUpdate

from app.core.exceptions import ValidationError

from loguru import logger

from app.core import get_db_session
from app.models.database import TransactionType
from app.services import TransactionService, CategoryService
from app.utils.formatters import format_amount, format_date, ICON_TO_EMOJI
from app.schema import QuickAddChipData

# Дефолтные категории для Quick-add chips (name, type)
# Расход: 6 категорий, Доход: 2 категории
DEFAULT_QUICK_ADD_CHIP_NAMES: list[tuple[str, str]] = [
    # Расходы
    ("Еда и продукты", "expense"),
    ("Транспорт", "expense"),
    ("Жилье и ЖКХ", "expense"),
    ("Связь и интернет", "expense"),
    ("Развлечения", "expense"),
    ("Кредиты", "expense"),
    # Доходы
    ("Зарплата", "income"),
    ("Подработка", "income"),
]


def _get_quick_add_chips() -> list[QuickAddChipData]:
    """Получить данные для Quick-add chips.

    Lookup категорий выполняется по имени (name) для защиты от ID mismatch
    между окружениями. Отсутствующие категории логируются как warning.

    Returns:
        list[QuickAddChipData]: Список chips с данными категорий
    """
    chips: list[QuickAddChipData] = []

    with get_db_session() as session:
        service = CategoryService(session)
        all_categories = service.get_all()

        # Индекс по имени для быстрого поиска
        category_by_name = {cat.name: cat for cat in all_categories}

        for name, tx_type in DEFAULT_QUICK_ADD_CHIP_NAMES:
            category = category_by_name.get(name)
            if category is None:
                logger.warning(f"Quick-add chip: категория '{name}' не найдена в БД")
                continue

            chips.append(
                QuickAddChipData(
                    category_id=category.id,
                    name=category.name,
                    icon=category.icon or "bi-tag",
                    type=tx_type,
                )
            )

    return chips


def _build_quick_add_chip(chip_data: QuickAddChipData) -> dbc.Button:
    """Создает одну Quick-add chip кнопку.

    Args:
        chip_data: Данные категории для chip

    Returns:
        dbc.Button: Кнопка-chip с иконкой и названием
    """
    return dbc.Button(
        [
            html.I(className=f"{chip_data['icon']} qa-chip-icon"),
            html.Span(chip_data["name"], className="qa-chip-label"),
        ],
        id={
            "type": "qa-chip",
            "category_id": chip_data["category_id"],
            "tx_type": chip_data["type"],
        },
        color="light",
        className="qa-chip",
        n_clicks=0,
        title=chip_data["name"],
    )


def _build_quick_add_section(chips: list[QuickAddChipData]) -> html.Div:
    """Создает секцию Quick-add chips с группировкой по типу.

    Args:
        chips: Список данных для chips

    Returns:
        html.Div: Секция с chips, разделенная на Расход/Доход
    """
    expense_chips = [c for c in chips if c["type"] == "expense"]
    income_chips = [c for c in chips if c["type"] == "income"]

    sections = []

    # Секция расходов
    if expense_chips:
        sections.append(
            html.Div(
                [
                    html.Span("Расход", className="qa-section-label"),
                    html.Div(
                        [_build_quick_add_chip(c) for c in expense_chips]
                        + [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-three-dots"),
                                    html.Span("Ещё", className="qa-chip-label"),
                                ],
                                id={"type": "qa-more-btn", "tx_type": "expense"},
                                color="outline-secondary",
                                className="qa-chip qa-more-btn",
                                n_clicks=0,
                            )
                        ],
                        className="qa-chips-row",
                    ),
                ],
                className="qa-section",
            )
        )

    # Секция доходов
    if income_chips:
        sections.append(
            html.Div(
                [
                    html.Span("Доход", className="qa-section-label"),
                    html.Div(
                        [_build_quick_add_chip(c) for c in income_chips]
                        + [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-three-dots"),
                                    html.Span("Ещё", className="qa-chip-label"),
                                ],
                                id={"type": "qa-more-btn", "tx_type": "income"},
                                color="outline-secondary",
                                className="qa-chip qa-more-btn",
                                n_clicks=0,
                            )
                        ],
                        className="qa-chips-row",
                    ),
                ],
                className="qa-section",
            )
        )

    return html.Div(sections, className="qa-chip-section mb-3")


def _build_category_more_modal() -> dbc.Modal:
    """Создает модальное окно с полным списком категорий.

    Содержимое загружается динамически при открытии через callback.

    Returns:
        dbc.Modal: Модал с табами Расход/Доход
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle("Выберите категорию"),
                close_button=True,
            ),
            dbc.ModalBody(
                dbc.Tabs(
                    [
                        dbc.Tab(
                            html.Div(
                                id="quick-add-more-expense-grid",
                                className="qa-more-grid",
                            ),
                            label="Расход",
                            tab_id="expense",
                        ),
                        dbc.Tab(
                            html.Div(
                                id="quick-add-more-income-grid",
                                className="qa-more-grid",
                            ),
                            label="Доход",
                            tab_id="income",
                        ),
                    ],
                    id="quick-add-more-tabs",
                    active_tab="expense",
                )
            ),
        ],
        id="quick-add-more-modal",
        is_open=False,
        centered=True,
        size="lg",
        backdrop=True,
    )


def _pluralize_operations(count: int) -> str:
    """Склонение слова 'операция' для счётчика выбранных.

    Args:
        count: Количество выбранных операций

    Returns:
        str: "N операция/операции/операций выбрана/выбраны/выбрано"
    """
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} операция выбрана"
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return f"{count} операции выбраны"
    else:
        return f"{count} операций выбрано"


def _build_bulk_panel() -> html.Div:
    """Строит sticky Bulk Actions Panel (скрыт по умолчанию).

    Returns:
        html.Div: Панель массовых операций с dropdown и кнопкой применения
    """
    return html.Div(
        [
            html.Div(
                [
                    # Счётчик выбранных операций
                    html.Span(
                        id="bulk-selected-count",
                        className="me-3 fw-bold",
                    ),
                    # Dropdown выбора категории
                    dcc.Dropdown(
                        id="bulk-category-dropdown",
                        placeholder="Выберите категорию...",
                        className="me-3",
                        style={"width": "250px", "display": "inline-block"},
                    ),
                    # Кнопка применения
                    dbc.Button(
                        [
                            html.I(className="bi bi-check2-all me-2"),
                            "Применить",
                        ],
                        id="bulk-apply-btn",
                        color="success",
                        size="sm",
                    ),
                ],
                className="d-flex align-items-center justify-content-center",
            ),
        ],
        id="bulk-actions-panel",
        className="tx-bulk-panel",
        style={"display": "none"},
    )


def _build_chips_cell(
    tx,
    frequent_categories: dict,
    all_categories: list,
) -> html.Div:
    """Строит ячейку с chips для быстрой категоризации.

    Args:
        tx: Объект Transaction
        frequent_categories: Кеш частых категорий {"expense": [...], "income": [...]}
        all_categories: Полный список категорий для dropdown

    Returns:
        html.Div: Ячейка с chips или "—" для TRANSFER/ADJUSTMENT
    """
    # Guard: TRANSFER и ADJUSTMENT не категоризируются
    if tx.transaction_type in (TransactionType.TRANSFER, TransactionType.ADJUSTMENT):
        return html.Span("—", className="text-muted")

    # Определяем тип категорий
    category_type = tx.transaction_type.name.lower()
    chips_data = frequent_categories.get(category_type, [])[:5]

    # Если нет частых категорий — показываем только dropdown
    if not chips_data:
        return html.Div(
            [
                dcc.Dropdown(
                    id={"type": "chip-dropdown", "tx_id": tx.id},
                    options=[
                        {
                            "label": (
                                f"{ICON_TO_EMOJI.get(cat.get('icon', ''), '📁')} "
                                f"{cat['label']}"
                            ),
                            "value": cat["value"],
                        }
                        for cat in all_categories
                        if cat.get("type", category_type) == category_type
                    ],
                    placeholder="Выбрать...",
                    className="tx-chip-dropdown",
                    style={"width": "150px"},
                ),
            ],
            className="tx-chips-cell",
        )

    # Строим chips
    chips = []
    for cat in chips_data:
        chip = dbc.Button(
            [
                html.I(className=f"{cat.get('icon', 'bi-tag')} me-1"),
                cat["label"],
            ],
            id={"type": "chip-btn", "tx_id": tx.id, "cat_id": cat["value"]},
            color="light",
            size="sm",
            className="tx-chip me-1 mb-1",
        )
        chips.append(chip)

    # Overflow dropdown для остальных категорий
    overflow_options = [
        {
            "label": f"{ICON_TO_EMOJI.get(cat.get('icon', ''), '📁')} {cat['label']}",
            "value": cat["value"],
        }
        for cat in all_categories
        if cat.get("type", category_type) == category_type
    ]

    overflow_dropdown = dcc.Dropdown(
        id={"type": "chip-dropdown", "tx_id": tx.id},
        options=overflow_options,
        placeholder="...",
        className="tx-chip-dropdown-overflow",
        style={"width": "80px", "display": "inline-block"},
    )

    return html.Div(
        [*chips, overflow_dropdown],
        className="tx-chips-cell d-flex flex-wrap align-items-center",
    )


def _build_transactions_table(
    transactions: list,
    frequent_categories: dict | None = None,
    all_categories: list | None = None,
) -> list:
    """Формирует HTML таблицу транзакций с checkboxes и chips.

    Args:
        transactions: Список объектов Transaction
        frequent_categories: Кеш частых категорий для chips
        all_categories: Полный список категорий для dropdown

    Returns:
        list: [thead, tbody] для dbc.Table
    """
    # Defaults для обратной совместимости
    if frequent_categories is None:
        frequent_categories = {}
    if all_categories is None:
        all_categories = []

    # Заголовок таблицы с checkbox "Select All"
    table_header = html.Thead(
        [
            html.Tr(
                [
                    html.Th(
                        dbc.Checkbox(id="select-all-checkbox", value=False),
                        style={"width": "40px"},
                    ),
                    html.Th("Дата"),
                    html.Th("Тип"),
                    html.Th("Сумма", className="text-end"),
                    html.Th("Категория", style={"minWidth": "200px"}),
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
                                colSpan=7,
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

        # Категория: с иконкой или chips для некатегоризированных
        if tx.category_rel:
            category_cell = [
                html.I(className=f"{tx.category_rel.icon} me-1"),
                tx.category_rel.name,
            ]
        else:
            # Chips для быстрой категоризации
            category_cell = _build_chips_cell(tx, frequent_categories, all_categories)

        row = html.Tr(
            [
                # Checkbox для выбора
                html.Td(
                    dbc.Checkbox(
                        id={"type": "tx-checkbox", "index": tx.id},
                        value=False,
                    ),
                ),
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
            # Stores для состояния выбора и кеша категорий
            dcc.Store(id="selected-transactions", data=[]),
            dcc.Store(id="frequent-categories", data={}),
            # Компонент для скачивания файлов
            dcc.Download(id="export-download"),
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
                    html.Div(
                        [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-download me-2"),
                                    "Экспорт CSV",
                                ],
                                id="export-btn",
                                color="secondary",
                                outline=True,
                                className="d-flex align-items-center me-2",
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
                        className="d-flex",
                    ),
                ],
                className="d-flex justify-content-between align-items-center mb-4",
            ),
            # Quick-add chips секция
            _build_quick_add_section(_get_quick_add_chips()),
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
            # Bulk Actions Panel (sticky bottom, скрыт по умолчанию)
            _build_bulk_panel(),
            # Quick-add More Modal (полный список категорий)
            _build_category_more_modal(),
        ]
    )


# ==================== CALLBACKS ====================


@callback(
    [
        Output("quick-add-more-expense-grid", "children"),
        Output("quick-add-more-income-grid", "children"),
    ],
    Input("quick-add-more-modal", "is_open"),
    prevent_initial_call=True,
)
def load_more_modal_categories(is_open: bool):
    """Загружает категории при открытии модала 'Ещё...'.

    Args:
        is_open: Состояние модала (открыт/закрыт)

    Returns:
        tuple: (expense_grid, income_grid) — списки кнопок категорий
    """
    if not is_open:
        raise PreventUpdate

    with get_db_session() as session:
        service = CategoryService(session)

        # Получаем категории по типам
        expense_categories = service.get_by_type("expense")
        income_categories = service.get_by_type("income")

        def build_category_buttons(categories, tx_type: str):
            """Создает кнопки для списка категорий."""
            if not categories:
                return html.P(
                    "Нет категорий",
                    className="text-muted text-center py-3",
                )

            buttons = []
            for cat in categories:
                buttons.append(
                    dbc.Button(
                        [
                            html.I(className=f"{cat.icon or 'bi-tag'} me-2"),
                            cat.name,
                        ],
                        id={
                            "type": "qa-more-category",
                            "category_id": cat.id,
                            "tx_type": tx_type,
                        },
                        color="outline-secondary",
                        className="qa-more-category-btn m-1",
                        n_clicks=0,
                    )
                )
            return html.Div(buttons, className="d-flex flex-wrap")

        return (
            build_category_buttons(expense_categories, "expense"),
            build_category_buttons(income_categories, "income"),
        )


# ==================== QUICK-ADD CALLBACKS ====================


@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("modal-source", "data", allow_duplicate=True),
        Output("preselected-category", "data", allow_duplicate=True),
        Output("preselected-type", "data", allow_duplicate=True),
        Output("create-category-dropdown", "value", allow_duplicate=True),
        Output("create-type-select", "value", allow_duplicate=True),
    ],
    Input({"type": "qa-chip", "category_id": ALL, "tx_type": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_create_from_quick_add(n_clicks_list):
    """Открывает модал создания с предвыбранной категорией из Quick-add chip.

    Args:
        n_clicks_list: Список n_clicks для всех chips

    Returns:
        tuple: (is_open, modal_source, category_id, tx_type, dropdown_value, type_value)
    """
    # Guard #1: No triggered_id
    if not ctx.triggered_id:
        raise PreventUpdate
    # Guard #2: Not a dict
    if not isinstance(ctx.triggered_id, dict):
        raise PreventUpdate
    # Guard #3: Wrong type
    if ctx.triggered_id.get("type") != "qa-chip":
        raise PreventUpdate
    # Guard #4: No actual click (DOM update trigger)
    if not ctx.triggered:
        raise PreventUpdate
    triggered_value = ctx.triggered[0].get("value")
    if triggered_value is None or triggered_value == 0:
        raise PreventUpdate

    category_id = ctx.triggered_id["category_id"]
    tx_type = ctx.triggered_id["tx_type"].upper()  # "expense" -> "EXPENSE"

    # Напрямую устанавливаем dropdown value для избежания race condition
    return True, "quick-add", category_id, tx_type, category_id, tx_type


@callback(
    [
        Output("quick-add-more-modal", "is_open"),
        Output("quick-add-more-tabs", "active_tab"),
    ],
    Input({"type": "qa-more-btn", "tx_type": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_more_modal(n_clicks_list):
    """Открывает модал 'Ещё...' с активной вкладкой по типу.

    Args:
        n_clicks_list: Список n_clicks для кнопок "Ещё"

    Returns:
        tuple: (is_open, active_tab)
    """
    # Guard #1
    if not ctx.triggered_id:
        raise PreventUpdate
    # Guard #2
    if not isinstance(ctx.triggered_id, dict):
        raise PreventUpdate
    # Guard #3
    if ctx.triggered_id.get("type") != "qa-more-btn":
        raise PreventUpdate
    # Guard #4: No actual click (DOM update trigger)
    if not ctx.triggered:
        raise PreventUpdate
    triggered_value = ctx.triggered[0].get("value")
    if triggered_value is None or triggered_value == 0:
        raise PreventUpdate

    tx_type = ctx.triggered_id["tx_type"]  # "expense" или "income"
    return True, tx_type


@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("modal-source", "data", allow_duplicate=True),
        Output("preselected-category", "data", allow_duplicate=True),
        Output("preselected-type", "data", allow_duplicate=True),
        Output("quick-add-more-modal", "is_open", allow_duplicate=True),
        Output("create-category-dropdown", "value", allow_duplicate=True),
        Output("create-type-select", "value", allow_duplicate=True),
    ],
    Input({"type": "qa-more-category", "category_id": ALL, "tx_type": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def select_from_more_modal(n_clicks_list):
    """Выбирает категорию из модала 'Ещё...' и открывает создание.

    Закрывает модал 'Ещё...' и открывает модал создания с preselection.

    Args:
        n_clicks_list: Список n_clicks для кнопок категорий

    Returns:
        tuple: (create_open, modal_source, category_id, tx_type, more_modal_close,
                dropdown_value, type_value)
    """
    # Guard #1
    if not ctx.triggered_id:
        raise PreventUpdate
    # Guard #2
    if not isinstance(ctx.triggered_id, dict):
        raise PreventUpdate
    # Guard #3
    if ctx.triggered_id.get("type") != "qa-more-category":
        raise PreventUpdate
    # Guard #4: No actual click (DOM update trigger)
    if not ctx.triggered:
        raise PreventUpdate
    triggered_value = ctx.triggered[0].get("value")
    if triggered_value is None or triggered_value == 0:
        raise PreventUpdate

    category_id = ctx.triggered_id["category_id"]
    tx_type = ctx.triggered_id["tx_type"].upper()

    # Закрываем "Ещё...", открываем create с preselection
    # Напрямую устанавливаем dropdown value для избежания race condition
    return True, "quick-add", category_id, tx_type, False, category_id, tx_type


@callback(
    Output("frequent-categories", "data"),
    Input("url", "pathname"),
    State("frequent-categories", "data"),
)
def load_frequent_categories(pathname: str, cached_data: dict | None) -> dict:
    """Загружает частые категории в кеш при первом посещении страницы.

    Args:
        pathname: Текущий URL
        cached_data: Текущий кеш категорий

    Returns:
        dict: Кеш категорий {"expense": [...], "income": [...]}
    """
    if pathname != "/transactions":
        raise PreventUpdate

    # Используем кеш если уже загружен
    if cached_data:
        raise PreventUpdate

    with get_db_session() as session:
        service = CategoryService(session)
        return {
            "expense": service.get_frequent_for_type(
                user_id=1, category_type="expense"
            ),
            "income": service.get_frequent_for_type(user_id=1, category_type="income"),
        }


@callback(
    Output("transactions-table", "children"),
    [
        Input("url", "pathname"),
        Input("filter-no-category", "value"),
        Input("frequent-categories", "data"),
    ],
)
def load_transactions(pathname, filter_no_category, frequent_categories):
    """Загружает список операций из БД с фильтрацией."""
    if pathname != "/transactions":
        raise PreventUpdate

    with get_db_session() as session:
        service = TransactionService(session)
        transactions = service.get_all_by_user(user_id=1)

        # Фильтр по отсутствию категории
        if filter_no_category:
            transactions = [tx for tx in transactions if tx.category_id is None]

        # Загружаем все категории для dropdown
        category_service = CategoryService(session)
        all_categories = category_service.get_for_dropdown()

        logger.debug(f"Загружено {len(transactions)} транзакций")
        return _build_transactions_table(
            transactions,
            frequent_categories=frequent_categories or {},
            all_categories=all_categories,
        )


@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("modal-source", "data", allow_duplicate=True),
        Output("preselected-category", "data", allow_duplicate=True),
        Output("preselected-type", "data", allow_duplicate=True),
        Output("create-category-dropdown", "value", allow_duplicate=True),
        Output("create-type-select", "value", allow_duplicate=True),
    ],
    Input("add-transaction-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_create_modal_from_transactions(n_clicks):
    """Открывает модальное окно создания со страницы транзакций.

    Сбрасывает preselection и форму от Quick-add chips.
    """
    # Строгая проверка: только реальный клик
    if not n_clicks or n_clicks == 0:
        raise PreventUpdate
    if not ctx.triggered_id or ctx.triggered_id != "add-transaction-btn":
        raise PreventUpdate
    # is_open, modal-source, preselected-category, preselected-type,
    # category-dropdown, type-select
    return True, "transactions", None, None, None, "EXPENSE"


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


@callback(
    [
        Output("transactions-table", "children", allow_duplicate=True),
        Output("global-transaction-trigger", "data", allow_duplicate=True),
    ],
    Input({"type": "chip-btn", "tx_id": ALL, "cat_id": ALL}, "n_clicks"),
    State("filter-no-category", "value"),
    State("frequent-categories", "data"),
    prevent_initial_call=True,
)
def chip_assign_category(n_clicks_list, filter_no_category, frequent_categories):
    """Присваивает категорию по клику на chip.

    Использует 3-уровневые guard clauses согласно ADR-003.
    """
    from datetime import datetime

    # Guard #1: triggered_id existence and type
    triggered_id = ctx.triggered_id
    if not triggered_id or not isinstance(triggered_id, dict):
        raise PreventUpdate

    # Guard #2: Correct component type
    if triggered_id.get("type") != "chip-btn":
        raise PreventUpdate

    # Guard #3: Real click (not auto-trigger on DOM update) - ADR-003
    if not ctx.triggered or ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    tx_id = triggered_id.get("tx_id")
    cat_id = triggered_id.get("cat_id")

    if not tx_id or not cat_id:
        raise PreventUpdate

    with get_db_session() as session:
        service = TransactionService(session)
        service.update_transaction(transaction_id=tx_id, category_id=cat_id)
        session.commit()

        # Reload transactions with filter applied
        transactions = service.get_all_by_user(user_id=1)
        if filter_no_category:
            transactions = [tx for tx in transactions if tx.category_id is None]

        # Загружаем категории для таблицы
        category_service = CategoryService(session)
        all_categories = category_service.get_for_dropdown()

        trigger_data = {
            "action": "update",
            "timestamp": datetime.now().isoformat(),
            "source": "transactions",
            "transaction_id": tx_id,
        }

        logger.info(f"Категория {cat_id} присвоена транзакции {tx_id} через chip")
        return (
            _build_transactions_table(
                transactions,
                frequent_categories=frequent_categories or {},
                all_categories=all_categories,
            ),
            trigger_data,
        )


@callback(
    [
        Output("transactions-table", "children", allow_duplicate=True),
        Output("global-transaction-trigger", "data", allow_duplicate=True),
    ],
    Input({"type": "chip-dropdown", "tx_id": ALL}, "value"),
    State("filter-no-category", "value"),
    State("frequent-categories", "data"),
    prevent_initial_call=True,
)
def chip_dropdown_assign_category(values, filter_no_category, frequent_categories):
    """Присваивает категорию из overflow dropdown.

    Использует 3-уровневые guard clauses согласно ADR-003.
    """
    from datetime import datetime

    # Guard #1: triggered_id existence and type
    triggered_id = ctx.triggered_id
    if not triggered_id or not isinstance(triggered_id, dict):
        raise PreventUpdate

    # Guard #2: Correct component type
    if triggered_id.get("type") != "chip-dropdown":
        raise PreventUpdate

    # Guard #3: Real selection (not auto-trigger on DOM update) - ADR-003
    if not ctx.triggered or ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    tx_id = triggered_id.get("tx_id")
    cat_id = ctx.triggered[0].get("value")

    if not tx_id or not cat_id:
        raise PreventUpdate

    with get_db_session() as session:
        service = TransactionService(session)
        service.update_transaction(transaction_id=tx_id, category_id=cat_id)
        session.commit()

        # Reload transactions with filter applied
        transactions = service.get_all_by_user(user_id=1)
        if filter_no_category:
            transactions = [tx for tx in transactions if tx.category_id is None]

        # Загружаем категории для таблицы
        category_service = CategoryService(session)
        all_categories = category_service.get_for_dropdown()

        trigger_data = {
            "action": "update",
            "timestamp": datetime.now().isoformat(),
            "source": "transactions",
            "transaction_id": tx_id,
        }

        logger.info(f"Категория {cat_id} присвоена транзакции {tx_id} через dropdown")
        return (
            _build_transactions_table(
                transactions,
                frequent_categories=frequent_categories or {},
                all_categories=all_categories,
            ),
            trigger_data,
        )


# ==================== BULK SELECTION CALLBACKS ====================


@callback(
    Output("selected-transactions", "data"),
    [
        Input({"type": "tx-checkbox", "index": ALL}, "value"),
        Input("select-all-checkbox", "value"),
    ],
    State({"type": "tx-checkbox", "index": ALL}, "id"),
    prevent_initial_call=True,
)
def update_selection_state(
    checkbox_values: list,
    select_all: bool | None,
    checkbox_ids: list[dict],
) -> list[int]:
    """Обновляет список выбранных транзакций.

    Args:
        checkbox_values: Значения индивидуальных checkboxes
        select_all: Значение "Select All" checkbox
        checkbox_ids: IDs всех checkboxes (для извлечения tx_id)

    Returns:
        list[int]: Список ID выбранных транзакций
    """
    # Определяем что вызвало callback
    triggered = ctx.triggered_id

    # Select All toggled
    if triggered == "select-all-checkbox":
        if select_all:
            # Выбрать все видимые транзакции
            return [cid["index"] for cid in checkbox_ids]
        else:
            return []

    # Individual checkbox toggled
    selected = []
    for cid, value in zip(checkbox_ids, checkbox_values):
        if value:
            selected.append(cid["index"])
    return selected


@callback(
    [
        Output("selected-transactions", "data", allow_duplicate=True),
        Output("select-all-checkbox", "value"),
    ],
    Input("filter-no-category", "value"),
    prevent_initial_call=True,
)
def clear_selection_on_filter_change(filter_value: bool) -> tuple[list, bool]:
    """Сбрасывает выбор при изменении фильтра.

    Критично для WYSIWYG — выбранные элементы должны быть видны.

    Args:
        filter_value: Новое значение фильтра (не используется)

    Returns:
        tuple: ([], False) — пустой selection и unchecked Select All
    """
    return [], False


@callback(
    [
        Output("bulk-actions-panel", "style"),
        Output("bulk-selected-count", "children"),
    ],
    Input("selected-transactions", "data"),
    prevent_initial_call=True,
)
def toggle_bulk_panel(selected: list[int] | None) -> tuple[dict, str]:
    """Показывает/скрывает Bulk Panel.

    Panel скрывается при пустом selection.

    Args:
        selected: Список ID выбранных транзакций

    Returns:
        tuple: (style dict, counter text)
    """
    if not selected or len(selected) == 0:
        return {"display": "none"}, ""

    count_text = _pluralize_operations(len(selected))
    return {"display": "block"}, count_text


@callback(
    [
        Output("transactions-table", "children", allow_duplicate=True),
        Output("selected-transactions", "data", allow_duplicate=True),
        Output("global-transaction-trigger", "data", allow_duplicate=True),
        Output("transaction-error-alert", "children", allow_duplicate=True),
        Output("transaction-error-alert", "is_open", allow_duplicate=True),
    ],
    Input("bulk-apply-btn", "n_clicks"),
    [
        State("bulk-category-dropdown", "value"),
        State("selected-transactions", "data"),
        State("filter-no-category", "value"),
        State("frequent-categories", "data"),
    ],
    prevent_initial_call=True,
)
def bulk_assign_category(
    n_clicks: int | None,
    category_id: int | None,
    selected_ids: list[int],
    filter_no_category: bool,
    frequent_categories: dict,
) -> tuple:
    """Массовое присвоение категории выбранным транзакциям.

    Args:
        n_clicks: Количество кликов на кнопку
        category_id: ID выбранной категории
        selected_ids: Список ID выбранных транзакций
        filter_no_category: Текущее значение фильтра
        frequent_categories: Кеш частых категорий

    Returns:
        tuple: (table, selection, trigger, error_msg, error_open)
    """
    from datetime import datetime

    if not n_clicks:
        raise PreventUpdate

    # Валидация inputs
    if not selected_ids:
        return no_update, no_update, no_update, "Выберите хотя бы одну операцию", True

    if category_id is None:
        return no_update, no_update, no_update, "Выберите категорию", True

    try:
        with get_db_session() as session:
            service = TransactionService(session)
            affected = service.bulk_update_category(
                user_id=1,
                transaction_ids=selected_ids,
                category_id=category_id,
            )
            session.commit()

            # Reload transactions
            transactions = service.get_all_by_user(user_id=1)
            if filter_no_category:
                transactions = [tx for tx in transactions if tx.category_id is None]

            # Загружаем категории
            category_service = CategoryService(session)
            all_categories = category_service.get_for_dropdown()

            trigger_data = {
                "action": "bulk_update",
                "timestamp": datetime.now().isoformat(),
                "source": "transactions",
                "affected_count": affected,
            }

            logger.info(
                f"Bulk update: {affected} транзакций получили категорию {category_id}"
            )

            return (
                _build_transactions_table(
                    transactions,
                    frequent_categories=frequent_categories or {},
                    all_categories=all_categories,
                ),
                [],  # Clear selection
                trigger_data,
                "",
                False,
            )
    except ValidationError as e:
        return no_update, no_update, no_update, str(e), True


# ==================== EXPORT CALLBACK ====================


@callback(
    Output("export-download", "data"),
    Input("export-btn", "n_clicks"),
    State("filter-no-category", "value"),
    prevent_initial_call=True,
)
def export_transactions(n_clicks: int | None, filter_uncategorized: bool) -> dict:
    """Экспортирует транзакции в CSV файл.

    Args:
        n_clicks: Количество кликов на кнопку экспорта
        filter_uncategorized: Экспортировать только без категории

    Returns:
        dict: Данные для dcc.Download (filename + content)
    """
    from datetime import date

    if not n_clicks:
        raise PreventUpdate

    with get_db_session() as session:
        service = TransactionService(session)
        csv_bytes = service.export_to_csv(
            user_id=1,
            uncategorized_only=filter_uncategorized,
        )

        filename = f"finfocus_transactions_{date.today().isoformat()}.csv"
        logger.info(f"Экспорт транзакций в {filename}")

        return dcc.send_bytes(csv_bytes, filename)
