"""UI компонент для управления накопительными целями."""

from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict

import dash_bootstrap_components as dbc
from dash import html, dcc

from app.utils.formatters import (
    format_amount,
    format_date,
    format_days_remaining,
)


# Константы
DEFAULT_USER_ID = 1
MIN_GOAL_DAYS = 7  # Минимум 7 дней до дедлайна


class GoalDisplayData(TypedDict):
    """Данные для отображения цели в UI."""

    id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date
    status: str
    progress_percentage: float
    monthly_contribution: Decimal
    days_remaining: int
    is_completed: bool


class ContributionDisplayData(TypedDict):
    """Данные для отображения взноса в истории."""

    id: int
    amount: Decimal
    contribution_date: date
    description: str | None


def _goal_to_display_data(goal) -> GoalDisplayData:
    """Конвертирует ORM Goal в GoalDisplayData для UI.

    Args:
        goal: SQLAlchemy Goal объект

    Returns:
        GoalDisplayData: TypedDict с данными для отображения
    """
    days_remaining = (goal.target_date - date.today()).days
    return GoalDisplayData(
        id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        status=goal.status.value,
        progress_percentage=goal.progress_percentage,
        monthly_contribution=goal.monthly_contribution,
        days_remaining=days_remaining,
        is_completed=goal.is_completed,
    )


def _build_empty_state() -> dbc.Card:
    """Создает empty state карточку когда нет активной цели.

    Returns:
        dbc.Card: Карточка с призывом создать цель
    """
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.I(
                            className="bi bi-bullseye",
                            style={"fontSize": "4rem", "color": "#6c757d"},
                        ),
                        html.H4("Нет активной цели", className="mt-3 text-muted"),
                        html.P(
                            "Создайте накопительную цель, "
                            "чтобы начать откладывать деньги",
                            className="text-muted",
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-plus-lg me-2"), "Создать цель"],
                            id="create-goal-btn",
                            color="success",
                            size="lg",
                            className="mt-3",
                        ),
                    ],
                    className="text-center py-5",
                )
            ]
        ),
        className="goal-empty-state",
    )


def _build_progress_bar(progress: float, current: Decimal, target: Decimal) -> html.Div:
    """Создает прогресс-бар с подписями.

    Args:
        progress: Процент выполнения (0-100)
        current: Текущая накопленная сумма
        target: Целевая сумма

    Returns:
        html.Div: Bootstrap Progress с подписями
    """
    # Определяем цвет прогресса
    if progress >= 100:
        color = "success"
    elif progress >= 75:
        color = "info"
    elif progress >= 50:
        color = "primary"
    elif progress >= 25:
        color = "warning"
    else:
        color = "secondary"

    return html.Div(
        [
            html.Div(
                [
                    html.Span(format_amount(current), className="fw-bold"),
                    html.Span(" / ", className="text-muted"),
                    html.Span(format_amount(target), className="text-muted"),
                ],
                className="d-flex justify-content-between mb-2",
            ),
            dbc.Progress(
                value=progress,
                color=color,
                className="goal-progress",
                style={"height": "24px"},
                label=f"{progress:.1f}%",
            ),
        ],
        className="goal-progress-container mb-4",
    )


def _build_action_buttons(goal_data: GoalDisplayData) -> dbc.ButtonGroup:
    """Создает группу кнопок действий над целью.

    Args:
        goal_data: Данные цели для определения доступных действий

    Returns:
        dbc.ButtonGroup: Кнопки Edit, Pause/Resume, Delete
    """
    is_active = goal_data["status"] == "ACTIVE"
    is_completed = goal_data["is_completed"]

    # Кнопка Pause/Resume
    if is_active:
        toggle_btn = dbc.Button(
            [html.I(className="bi bi-pause-fill me-1"), "Приостановить"],
            id="toggle-status-btn",
            color="warning",
            outline=True,
            size="sm",
            disabled=is_completed,
        )
    else:
        toggle_btn = dbc.Button(
            [html.I(className="bi bi-play-fill me-1"), "Возобновить"],
            id="toggle-status-btn",
            color="success",
            outline=True,
            size="sm",
            disabled=is_completed,
        )

    return dbc.ButtonGroup(
        [
            dbc.Button(
                [html.I(className="bi bi-pencil me-1"), "Редактировать"],
                id="edit-goal-btn",
                color="primary",
                outline=True,
                size="sm",
                disabled=is_completed,
            ),
            toggle_btn,
            dbc.Button(
                [html.I(className="bi bi-trash me-1"), "Удалить"],
                id="delete-goal-btn",
                color="danger",
                outline=True,
                size="sm",
            ),
        ],
        className="mt-3",
    )


def _build_goal_card(goal_data: GoalDisplayData | None) -> dbc.Card:
    """Создает карточку активной цели или empty state.

    Args:
        goal_data: Данные цели или None если нет активной

    Returns:
        dbc.Card: Карточка с информацией о цели или empty state
    """
    if goal_data is None:
        return _build_empty_state()

    # Определяем badge статуса
    status_badges = {
        "ACTIVE": dbc.Badge("Активна", color="success", className="ms-2"),
        "PAUSED": dbc.Badge("Приостановлена", color="warning", className="ms-2"),
        "COMPLETED": dbc.Badge("Завершена", color="info", className="ms-2"),
    }
    status_badge = status_badges.get(goal_data["status"], None)

    # Метрики
    metrics_row = dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P("Накоплено", className="text-muted mb-1 small"),
                            html.H5(
                                format_amount(goal_data["current_amount"]),
                                className="mb-0 text-success",
                            ),
                        ]
                    ),
                    className="goal-metric-card",
                ),
                md=4,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P(
                                "Рекомендуемый взнос", className="text-muted mb-1 small"
                            ),
                            html.H5(
                                format_amount(goal_data["monthly_contribution"])
                                + "/мес",
                                className="mb-0 text-primary",
                            ),
                        ]
                    ),
                    className="goal-metric-card",
                ),
                md=4,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P("Осталось", className="text-muted mb-1 small"),
                            html.H5(
                                format_days_remaining(goal_data["days_remaining"]),
                                className="mb-0",
                            ),
                        ]
                    ),
                    className="goal-metric-card",
                ),
                md=4,
            ),
        ],
        className="mb-3",
    )

    return dbc.Card(
        [
            dbc.CardHeader(
                html.Div(
                    [
                        html.H4(
                            [goal_data["name"], status_badge],
                            className="mb-0",
                        ),
                        html.Small(
                            f"Дедлайн: {format_date(goal_data['target_date'])}",
                            className="text-muted",
                        ),
                    ],
                    className="d-flex justify-content-between align-items-center",
                )
            ),
            dbc.CardBody(
                [
                    _build_progress_bar(
                        goal_data["progress_percentage"],
                        goal_data["current_amount"],
                        goal_data["target_amount"],
                    ),
                    metrics_row,
                    html.Div(
                        [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-plus-circle me-2"),
                                    "Внести взнос",
                                ],
                                id="add-contribution-btn",
                                color="success",
                                className="me-2",
                                disabled=goal_data["is_completed"]
                                or goal_data["status"] == "PAUSED",
                            ),
                            _build_action_buttons(goal_data),
                        ],
                        className="d-flex justify-content-between align-items-center",
                    ),
                ]
            ),
        ],
        className="goal-card mb-4",
    )


def _build_contributions_table(
    contributions: list[ContributionDisplayData],
) -> html.Div:
    """Создает таблицу истории взносов или empty state.

    Args:
        contributions: Список взносов для отображения

    Returns:
        html.Div: Таблица или empty state с мотивирующим текстом
    """
    if not contributions:
        return html.Div(
            [
                html.I(
                    className="bi bi-piggy-bank",
                    style={"fontSize": "2rem", "color": "#6c757d"},
                ),
                html.P(
                    "Пока нет взносов. Сделайте первый шаг к своей цели!",
                    className="text-muted mt-2 mb-0",
                ),
            ],
            className="text-center py-4",
        )

    # Заголовок таблицы
    table_header = html.Thead(
        html.Tr(
            [
                html.Th("Дата"),
                html.Th("Сумма"),
                html.Th("Описание"),
            ]
        )
    )

    # Строки таблицы
    table_rows = []
    for contrib in contributions:
        table_rows.append(
            html.Tr(
                [
                    html.Td(format_date(contrib["contribution_date"])),
                    html.Td(
                        format_amount(contrib["amount"]),
                        className="text-success fw-bold",
                    ),
                    html.Td(
                        contrib["description"] or "-",
                        className="text-muted",
                    ),
                ]
            )
        )

    table_body = html.Tbody(table_rows)

    return dbc.Table(
        [table_header, table_body],
        striped=True,
        hover=True,
        responsive=True,
        className="contributions-table",
    )


def _build_create_goal_modal() -> dbc.Modal:
    """Создает модал для создания новой цели."""
    min_date = (date.today() + timedelta(days=MIN_GOAL_DAYS)).isoformat()

    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Создать цель")),
            dbc.ModalBody(
                [
                    dbc.Row(
                        [
                            dbc.Label("Название цели", width=4),
                            dbc.Col(
                                dbc.Input(
                                    id="create-goal-name-input",
                                    type="text",
                                    placeholder="Например: Отпуск в Турции",
                                    required=True,
                                ),
                                width=8,
                            ),
                        ],
                        className="mb-3",
                    ),
                    dbc.Row(
                        [
                            dbc.Label("Целевая сумма", width=4),
                            dbc.Col(
                                dbc.Input(
                                    id="create-goal-amount-input",
                                    type="number",
                                    min=0.01,
                                    step=0.01,
                                    placeholder="100000",
                                    required=True,
                                ),
                                width=8,
                            ),
                        ],
                        className="mb-3",
                    ),
                    dbc.Row(
                        [
                            dbc.Label("Дата достижения", width=4),
                            dbc.Col(
                                dcc.DatePickerSingle(
                                    id="create-goal-date-picker",
                                    min_date_allowed=min_date,
                                    date=min_date,
                                    display_format="DD.MM.YYYY",
                                    placeholder="Выберите дату",
                                ),
                                width=8,
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
                        id="create-goal-cancel-btn",
                        color="secondary",
                        outline=True,
                    ),
                    dbc.Button(
                        "Создать",
                        id="create-goal-submit-btn",
                        color="success",
                    ),
                ]
            ),
        ],
        id="create-goal-modal",
        is_open=False,
    )


def _build_edit_goal_modal() -> dbc.Modal:
    """Создает модал для редактирования цели."""
    min_date = (date.today() + timedelta(days=MIN_GOAL_DAYS)).isoformat()

    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Редактировать цель")),
            dbc.ModalBody(
                [
                    dbc.Row(
                        [
                            dbc.Label("Название цели", width=4),
                            dbc.Col(
                                dbc.Input(
                                    id="edit-goal-name-input",
                                    type="text",
                                    required=True,
                                ),
                                width=8,
                            ),
                        ],
                        className="mb-3",
                    ),
                    dbc.Row(
                        [
                            dbc.Label("Целевая сумма", width=4),
                            dbc.Col(
                                dbc.Input(
                                    id="edit-goal-amount-input",
                                    type="number",
                                    min=0.01,
                                    step=0.01,
                                    required=True,
                                ),
                                width=8,
                            ),
                        ],
                        className="mb-3",
                    ),
                    dbc.Row(
                        [
                            dbc.Label("Дата достижения", width=4),
                            dbc.Col(
                                dcc.DatePickerSingle(
                                    id="edit-goal-date-picker",
                                    min_date_allowed=min_date,
                                    display_format="DD.MM.YYYY",
                                ),
                                width=8,
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
                        id="edit-goal-cancel-btn",
                        color="secondary",
                        outline=True,
                    ),
                    dbc.Button(
                        "Сохранить",
                        id="edit-goal-submit-btn",
                        color="primary",
                    ),
                ]
            ),
        ],
        id="edit-goal-modal",
        is_open=False,
    )


def _build_contribution_modal() -> dbc.Modal:
    """Создает модал для добавления взноса."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Внести взнос")),
            dbc.ModalBody(
                [
                    dbc.Row(
                        [
                            dbc.Label("Сумма взноса", width=4),
                            dbc.Col(
                                dbc.Input(
                                    id="contribution-amount-input",
                                    type="number",
                                    min=0.01,
                                    step=0.01,
                                    placeholder="5000",
                                    required=True,
                                ),
                                width=8,
                            ),
                        ],
                        className="mb-3",
                    ),
                    dbc.Row(
                        [
                            dbc.Label("Дата взноса", width=4),
                            dbc.Col(
                                dcc.DatePickerSingle(
                                    id="contribution-date-picker",
                                    date=date.today().isoformat(),
                                    display_format="DD.MM.YYYY",
                                ),
                                width=8,
                            ),
                        ],
                        className="mb-3",
                    ),
                    dbc.Row(
                        [
                            dbc.Label("Описание", width=4),
                            dbc.Col(
                                dbc.Textarea(
                                    id="contribution-description-input",
                                    placeholder="Необязательно",
                                    rows=2,
                                ),
                                width=8,
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
                        id="contribution-cancel-btn",
                        color="secondary",
                        outline=True,
                    ),
                    dbc.Button(
                        "Внести",
                        id="contribution-submit-btn",
                        color="success",
                    ),
                ]
            ),
        ],
        id="contribution-modal",
        is_open=False,
    )


def create_goals_layout() -> html.Div:
    """Создает layout страницы накопительных целей.

    Returns:
        html.Div: Полный layout страницы Goals
    """
    return html.Div(
        [
            # Заголовок страницы
            html.Div(
                [
                    html.Div(
                        [
                            html.H2("Накопительные цели", className="mb-0"),
                            html.P(
                                "Ставьте финансовые цели и отслеживайте прогресс",
                                className="text-muted mb-0",
                            ),
                        ]
                    ),
                ],
                className="d-flex justify-content-between align-items-center mb-4",
            ),
            # Alert для ошибок
            dbc.Alert(
                id="goal-error-alert",
                is_open=False,
                color="danger",
                dismissable=True,
                duration=5000,
            ),
            # Карточка цели (динамический контент)
            html.Div(id="goal-card-container"),
            # История взносов
            dbc.Card(
                [
                    dbc.CardHeader(html.H5("История взносов", className="mb-0")),
                    dbc.CardBody(html.Div(id="contributions-table-container")),
                ],
                className="mt-4",
            ),
            # Модалы
            _build_create_goal_modal(),
            _build_edit_goal_modal(),
            _build_contribution_modal(),
            # Confirm Dialog для удаления
            dcc.ConfirmDialog(
                id="confirm-delete-goal",
                message="Вы уверены? Цель и все взносы будут удалены "
                "без возможности восстановления.",
            ),
            # Store для ID текущей цели
            dcc.Store(id="current-goal-id", data=None),
        ],
        className="goals-container",
    )
