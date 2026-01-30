"""UI компонент для управления накопительными целями."""

import time
from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ctx, no_update, ALL
from dash.exceptions import PreventUpdate
from loguru import logger

from app.core import get_db_session
from app.models.database import GoalStatus
from app.schema.cushion import CushionSettings
from app.services import (
    GoalService,
    AllocationService,
    RedistributionService,
    AllocationResult,
    AllocationSummary,
    GoalDisplayData,
    GoalsSummary,
)
from app.utils.formatters import (
    format_amount,
    format_date,
    format_days_remaining,
    parse_date_safe,
)
from app.utils.serializers import (
    serialize_allocation_summary,
    serialize_redistribution_preview,
    deserialize_redistribution_preview,
)


# Константы
DEFAULT_USER_ID = 1
MIN_GOAL_DAYS = 7  # Минимум 7 дней до дедлайна

# Опции режимов накоплений для UI
MODE_OPTIONS = {
    "free": {
        "label": "Свободный (100%)",
        "description": "Минимальные взносы точно по графику",
    },
    "medium": {
        "label": "Средний (115%)",
        "description": "+15% буфер для непредвиденных расходов",
    },
    "strict": {
        "label": "Строгий (150%)",
        "description": "Максимизация накоплений для раннего достижения",
    },
}


def _build_cushion_card(settings: CushionSettings | None) -> dbc.Card:
    """Карточка финансовой подушки безопасности.

    Два состояния:
    - Не настроена (target=0): приглашение + кнопка "Настроить"
    - Настроена (target>0): цель, текущая сумма, прогресс-бар с маркером порога

    Args:
        settings: Настройки подушки или None

    Returns:
        dbc.Card: Карточка подушки
    """
    if not settings or not settings.get("is_configured"):
        # Состояние "Не настроена"
        return dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.I(
                                    className="bi bi-shield-check cushion-icon-large"
                                ),
                                html.Div(
                                    [
                                        html.H5(
                                            "Финансовая подушка",
                                            className="cushion-title mb-1",
                                        ),
                                        html.P(
                                            "Создайте резервный фонд для "
                                            "непредвиденных расходов",
                                            className="text-muted mb-0 small",
                                        ),
                                    ]
                                ),
                            ],
                            className="d-flex align-items-center gap-3 mb-3",
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-gear me-2"), "Настроить"],
                            id="cushion-setup-btn",
                            color="primary",
                            outline=True,
                        ),
                    ]
                )
            ],
            className="cushion-card cushion-not-configured mb-4",
        )

    # Состояние "Настроена"
    target = settings["target"]
    current = settings["current_amount"]
    progress = settings["progress"]
    threshold_percent = settings["threshold_percent"]

    # Определяем статус прогресса
    if current < 0:
        progress_color = "danger"
        status_text = "Отрицательный баланс"
        status_icon = "bi-exclamation-triangle"
    elif progress < threshold_percent:
        progress_color = "warning"
        status_text = "Ниже порога безопасности"
        status_icon = "bi-exclamation-circle"
    elif progress < 100:
        progress_color = "info"
        status_text = "В процессе накопления"
        status_icon = "bi-arrow-up-circle"
    else:
        progress_color = "success"
        status_text = "Цель достигнута"
        status_icon = "bi-check-circle"

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    # Header с заголовком и кнопкой
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.I(
                                        className="bi bi-shield-check cushion-icon-large"
                                    ),
                                    html.H5(
                                        "Финансовая подушка",
                                        className="cushion-title mb-0 ms-2",
                                    ),
                                ],
                                className="d-flex align-items-center",
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-pencil me-1"), "Изменить"],
                                id="cushion-edit-btn",
                                color="secondary",
                                outline=True,
                                size="sm",
                            ),
                        ],
                        className="d-flex justify-content-between align-items-center "
                        "mb-3",
                    ),
                    # Статус
                    html.Div(
                        [
                            html.I(className=f"bi {status_icon} me-2"),
                            html.Span(status_text),
                        ],
                        className=f"cushion-status cushion-status-{progress_color} mb-3",
                    ),
                    # Суммы
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        "Накоплено", className="text-muted small"
                                    ),
                                    html.H4(
                                        format_amount(current),
                                        className="mb-0 cushion-amount",
                                    ),
                                ],
                                className="cushion-amount-block",
                            ),
                            html.Div(
                                [
                                    html.Span("Цель", className="text-muted small"),
                                    html.H4(
                                        format_amount(target),
                                        className="mb-0 text-muted",
                                    ),
                                ],
                                className="cushion-amount-block",
                            ),
                        ],
                        className="d-flex gap-4 mb-3",
                    ),
                    # Прогресс-бар с маркером порога
                    html.Div(
                        [
                            dbc.Progress(
                                value=min(progress, 100),
                                color=progress_color,
                                className="cushion-progress",
                                style={"height": "12px"},
                            ),
                            # Маркер порога
                            html.Div(
                                className="cushion-threshold-marker",
                                style={"left": f"{threshold_percent}%"},
                                title=f"Порог безопасности: {threshold_percent}%",
                            ),
                        ],
                        className="cushion-progress-container position-relative",
                    ),
                    # Подпись прогресса
                    html.Div(
                        [
                            html.Span(
                                f"{progress:.1f}%",
                                className="cushion-progress-text",
                            ),
                            html.Span(
                                f"Порог: {threshold_percent}%",
                                className="text-muted small",
                            ),
                        ],
                        className="d-flex justify-content-between mt-2",
                    ),
                ]
            )
        ],
        className=f"cushion-card cushion-configured cushion-{progress_color} mb-4",
    )


def _build_mode_selector(current_mode: str) -> dbc.Card:
    """Создает RadioItems для выбора режима накоплений.

    Args:
        current_mode: Текущий режим ("free", "medium", "strict")

    Returns:
        dbc.Card: Карточка с переключателем режимов
    """
    options = [
        {
            "label": html.Div(
                [
                    html.Span(MODE_OPTIONS[mode]["label"], className="mode-label"),
                    html.Br(),
                    html.Small(
                        MODE_OPTIONS[mode]["description"], className="mode-description"
                    ),
                ]
            ),
            "value": mode,
        }
        for mode in ["free", "medium", "strict"]
    ]

    return dbc.Card(
        [
            dbc.CardHeader(html.H6("Режим накоплений", className="mb-0")),
            dbc.CardBody(
                [
                    dbc.RadioItems(
                        id="savings-mode-selector",
                        options=options,
                        value=current_mode,
                        className="savings-mode-radio",
                    ),
                ]
            ),
        ],
        className="mode-selector-card",
    )


def _safe_budget_decimal(budget) -> Decimal:
    """Безопасно конвертирует budget в Decimal.

    Используется в callbacks для преобразования данных из dcc.Store.

    Args:
        budget: Значение из goals-budget-store (может быть None, str, int, float)

    Returns:
        Decimal: Конвертированное значение или Decimal("0") если budget пустой
    """
    return Decimal(str(budget)) if budget else Decimal("0")


class ContributionDisplayData(TypedDict):
    """Данные для отображения взноса в истории."""

    id: int
    amount: Decimal
    contribution_date: date
    description: str | None


def _goal_to_display_data(
    goal, allocated_amount: Decimal | None = None, allocation_status: str | None = None
) -> GoalDisplayData:
    """Конвертирует ORM Goal в GoalDisplayData для UI.

    Args:
        goal: SQLAlchemy Goal объект
        allocated_amount: Выделенная сумма из бюджета (опционально)
        allocation_status: Статус распределения (опционально)

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
        priority=goal.priority,
        allocated_amount=allocated_amount,
        allocation_status=allocation_status,
    )


def _build_empty_state() -> dbc.Card:
    """Создает empty state карточку когда нет активной цели.

    Returns:
        dbc.Card: Карточка с призывом создать цель
    """
    return dbc.Card(
        dbc.CardBody(
            html.Div(
                [
                    html.I(
                        className="bi bi-bullseye",
                        style={"fontSize": "4rem", "color": "#6c757d"},
                    ),
                    html.H4("Нет активной цели", className="mt-3 text-muted"),
                    html.P(
                        "Создайте накопительную цель с помощью кнопки выше, "
                        "чтобы начать откладывать деньги",
                        className="text-muted",
                    ),
                    # Кнопка УДАЛЕНА - используется create-goal-btn-header в header
                ],
                className="text-center py-5",
            )
        ),
        className="goal-empty-state",
    )


def _build_budget_alert() -> dbc.Alert:
    """Строит info-alert с призывом настроить бюджет.

    Returns:
        dbc.Alert: Bootstrap Alert с информацией о ненастроенном бюджете
    """
    return dbc.Alert(
        [
            html.I(className="bi bi-info-circle me-2"),
            "Бюджет накоплений не настроен. Настройте его для получения "
            "рекомендаций по взносам.",
        ],
        color="info",
        dismissable=True,
        className="budget-alert mb-3",
    )


def _build_summary_section(
    goals_summary: GoalsSummary,
    allocation_summary: AllocationSummary,
) -> dbc.Card:
    """Строит сводную секцию с общим прогрессом и статусом распределения.

    Args:
        goals_summary: Сводка по всем активным целям
        allocation_summary: Результат распределения бюджета

    Returns:
        dbc.Card: Карточка со сводной информацией
    """
    # Статус распределения
    if allocation_summary["all_goals_funded"]:
        distribution_status = dbc.Alert(
            [
                html.I(className="bi bi-check-circle me-2"),
                "Все цели полностью профинансированы",
            ],
            color="success",
            className="mb-0",
        )
    else:
        shortfall = allocation_summary["total_shortfall"]
        distribution_status = dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle me-2"),
                f"Недостаток бюджета: {format_amount(shortfall)}",
            ],
            color="warning",
            className="mb-0",
        )

    # Бюджет накоплений
    budget_display = (
        format_amount(goals_summary["monthly_budget"])
        if not allocation_summary["budget_not_set"]
        else "Не настроен"
    )

    return dbc.Card(
        [
            dbc.CardHeader(html.H5("Сводка по целям", className="mb-0")),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.P(
                                        "Общий прогресс",
                                        className="text-muted mb-1 small",
                                    ),
                                    html.H5(
                                        [
                                            format_amount(
                                                goals_summary["total_current_amount"]
                                            ),
                                            html.Span(" / ", className="text-muted"),
                                            html.Span(
                                                format_amount(
                                                    goals_summary["total_target_amount"]
                                                ),
                                                className="text-muted",
                                            ),
                                            html.Small(
                                                f" ({goals_summary['total_progress_percentage']:.1f}%)",  # noqa: E501
                                                className="text-muted ms-2",
                                            ),
                                        ],
                                        className="mb-0",
                                    ),
                                ],
                                md=6,
                            ),
                            dbc.Col(
                                [
                                    html.P(
                                        "Бюджет накоплений",
                                        className="text-muted mb-1 small",
                                    ),
                                    html.H5(
                                        [
                                            budget_display,
                                            html.Span(
                                                "/мес", className="text-muted ms-1"
                                            ),
                                        ],
                                        className="mb-0",
                                    ),
                                ],
                                md=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    distribution_status,
                    html.Div(
                        dbc.Button(
                            [
                                html.I(className="bi bi-gear me-2"),
                                "Настроить бюджет",
                            ],
                            id="open-budget-modal-btn",
                            color="primary",
                            outline=True,
                            size="sm",
                            className="mt-3",
                        ),
                        className="text-end",
                    ),
                ]
            ),
        ],
        className="summary-section mb-4",
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
    is_active = goal_data["status"] == "active"
    is_completed = goal_data["is_completed"]
    goal_id = goal_data["id"]

    # Кнопка Pause/Resume
    if is_active:
        toggle_btn = dbc.Button(
            [html.I(className="bi bi-pause-fill me-1"), "Приостановить"],
            id={"type": "toggle-status-btn", "index": goal_id},
            color="warning",
            outline=True,
            size="sm",
            disabled=is_completed,
        )
    else:
        toggle_btn = dbc.Button(
            [html.I(className="bi bi-play-fill me-1"), "Возобновить"],
            id={"type": "toggle-status-btn", "index": goal_id},
            color="success",
            outline=True,
            size="sm",
            disabled=is_completed,
        )

    return dbc.ButtonGroup(
        [
            dbc.Button(
                [html.I(className="bi bi-pencil me-1"), "Редактировать"],
                id={"type": "edit-goal-btn", "index": goal_id},
                color="primary",
                outline=True,
                size="sm",
                disabled=is_completed,
            ),
            toggle_btn,
            dbc.Button(
                [html.I(className="bi bi-trash me-1"), "Удалить"],
                id={"type": "delete-goal-btn", "index": goal_id},
                color="danger",
                outline=True,
                size="sm",
            ),
        ],
        size="sm",
    )


def _build_goal_card(goal_data: GoalDisplayData) -> dbc.Card:
    """Создает карточку цели для списка с приоритетами и allocation.

    Args:
        goal_data: Данные цели с allocated_amount и allocation_status

    Returns:
        dbc.Card: Карточка с информацией о цели
    """
    # Определяем badge статуса
    status_badges = {
        "active": dbc.Badge("Активна", color="success", className="ms-2"),
        "paused": dbc.Badge("Приостановлена", color="warning", className="ms-2"),
        "completed": dbc.Badge("Завершена", color="info", className="ms-2"),
    }
    status_badge = status_badges.get(goal_data["status"], None)

    # Badge приоритета
    priority_badge = dbc.Badge(
        f"#{goal_data['priority']}",
        color="secondary",
        className="goal-card-priority me-2",
    )

    # Badge allocation status
    allocation_badge = None
    if goal_data.get("allocation_status"):
        allocation_badges = {
            "fully_funded": dbc.Badge("Полностью", color="success", className="ms-2"),
            "partial": dbc.Badge("Частично", color="warning", className="ms-2"),
            "not_funded": dbc.Badge(
                "Не профинансирована", color="danger", className="ms-2"
            ),
            "skipped": dbc.Badge("Пропущена", color="secondary", className="ms-2"),
        }
        allocation_badge = allocation_badges.get(goal_data["allocation_status"])

    # Кнопки приоритетов (arrows)
    priority_buttons = dbc.ButtonGroup(
        [
            dbc.Button(
                html.I(className="bi bi-arrow-up"),
                id={"type": "priority-up-btn", "index": goal_data["id"]},
                color="light",
                size="sm",
                outline=True,
                className="priority-btn",
            ),
            dbc.Button(
                html.I(className="bi bi-arrow-down"),
                id={"type": "priority-down-btn", "index": goal_data["id"]},
                color="light",
                size="sm",
                outline=True,
                className="priority-btn",
            ),
        ],
        size="sm",
    )

    # Allocation секция (если есть)
    allocation_section = None
    if goal_data.get("allocated_amount") is not None:
        allocation_section = dbc.Card(
            dbc.CardBody(
                [
                    html.P("Выделено из бюджета", className="text-muted mb-1 small"),
                    html.H5(
                        [
                            format_amount(goal_data["allocated_amount"]),
                            html.Span("/мес", className="text-muted ms-1"),
                            allocation_badge if allocation_badge else None,
                        ],
                        className="mb-0",
                    ),
                ],
            ),
            className="goal-metric-card goal-card-allocation",
        )

    # Метрики
    metric_cols = [
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
            md=3 if allocation_section else 4,
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.P(
                            "Рекомендуемый взнос",
                            className="text-muted mb-1 small",
                        ),
                        html.H5(
                            format_amount(goal_data["monthly_contribution"]) + "/мес",
                            className="mb-0 text-primary",
                        ),
                    ]
                ),
                className="goal-metric-card",
            ),
            md=3 if allocation_section else 4,
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
            md=3 if allocation_section else 4,
        ),
    ]

    if allocation_section:
        metric_cols.append(dbc.Col(allocation_section, md=3))

    metrics_row = dbc.Row(metric_cols, className="mb-3")

    return dbc.Card(
        [
            dbc.CardHeader(
                html.Div(
                    [
                        html.Div(
                            [
                                priority_badge,
                                html.H5(
                                    [goal_data["name"], status_badge],
                                    className="d-inline mb-0",
                                ),
                            ],
                            className="d-flex align-items-center",
                        ),
                        html.Div(
                            [
                                html.Small(
                                    f"Дедлайн: {format_date(goal_data['target_date'])}",
                                    className="text-muted me-3",
                                ),
                                priority_buttons,
                            ],
                            className="d-flex align-items-center",
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
                                id={
                                    "type": "add-contribution-btn",
                                    "index": goal_data["id"],
                                },
                                color="success",
                                className="me-2",
                                size="sm",
                                disabled=goal_data["is_completed"]
                                or goal_data["status"] == "paused",
                            ),
                            _build_action_buttons(goal_data),
                        ],
                        className="d-flex justify-content-between align-items-center",
                    ),
                ]
            ),
        ],
        className="goal-card mb-3",
    )


def _build_goals_list(
    goals: list,
    allocation_results: dict[int, AllocationResult],
) -> html.Div:
    """Строит список карточек целей с сортировкой по приоритету.

    Args:
        goals: Список ORM Goal объектов
        allocation_results: Словарь {goal_id: AllocationResult}

    Returns:
        html.Div: Контейнер со списком карточек целей
    """
    if not goals:
        return _build_empty_state()

    # Сортировка по priority
    sorted_goals = sorted(goals, key=lambda g: g.priority)

    # Построение карточек
    goal_cards = []
    for goal in sorted_goals:
        # Конвертируем Goal в GoalDisplayData
        goal_display = _goal_to_display_data(goal)

        # Добавляем allocation данные если есть
        if goal.id in allocation_results:
            allocation = allocation_results[goal.id]
            goal_display["allocated_amount"] = allocation["allocated_amount"]

            # Определяем allocation_status
            if allocation["skipped_reason"]:
                goal_display["allocation_status"] = "skipped"
            elif allocation["is_fully_funded"]:
                goal_display["allocation_status"] = "fully_funded"
            elif allocation["allocated_amount"] > Decimal("0"):
                goal_display["allocation_status"] = "partial"
            else:
                goal_display["allocation_status"] = "not_funded"
        else:
            goal_display["allocated_amount"] = None
            goal_display["allocation_status"] = None

        # Добавляем priority для отображения
        goal_display["priority"] = goal.priority

        goal_cards.append(_build_goal_card(goal_display))

    return html.Div(goal_cards, className="goals-list")


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


def _build_cushion_modal() -> dbc.Modal:
    """Модал настройки финансовой подушки безопасности.

    Содержит:
    - Поле "Цель подушки" (число >= 0)
    - Поле "Минимальный остаток" (порог, по умолчанию 30% от цели)
    - Collapsible секция "Рассчитать по сценариям"
    - Кнопки: Сохранить, Сбросить, Отмена

    Returns:
        dbc.Modal: Модал настройки подушки
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Настройка финансовой подушки")),
            dbc.ModalBody(
                [
                    # Поле цели
                    dbc.Row(
                        [
                            dbc.Label("Цель подушки", width=4),
                            dbc.Col(
                                dbc.Input(
                                    id="cushion-target-input",
                                    type="number",
                                    min=0,
                                    step=1000,
                                    placeholder="300000",
                                ),
                                width=8,
                            ),
                        ],
                        className="mb-3",
                    ),
                    # Поле порога
                    dbc.Row(
                        [
                            dbc.Label("Порог безопасности", width=4),
                            dbc.Col(
                                dbc.InputGroup(
                                    [
                                        dbc.Input(
                                            id="cushion-threshold-input",
                                            type="number",
                                            min=0,
                                            max=100,
                                            value=30,
                                        ),
                                        dbc.InputGroupText("%"),
                                    ]
                                ),
                                width=8,
                            ),
                        ],
                        className="mb-2",
                    ),
                    html.P(
                        "При достижении этого порога баланс считается в зоне риска",
                        className="text-muted small mb-4",
                    ),
                    # Collapsible калькулятор сценариев
                    html.Div(
                        [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-calculator me-2"),
                                    "Рассчитать по сценариям",
                                ],
                                id="cushion-toggle-calculator-btn",
                                color="secondary",
                                outline=True,
                                size="sm",
                                className="mb-3",
                            ),
                            dbc.Collapse(
                                [
                                    html.Hr(),
                                    html.H6(
                                        "Сценарии непредвиденных расходов",
                                        className="mb-3",
                                    ),
                                    html.P(
                                        "Добавьте возможные расходы для расчёта "
                                        "рекомендуемого размера подушки",
                                        className="text-muted small mb-3",
                                    ),
                                    # Список сценариев
                                    html.Div(id="cushion-scenarios-list"),
                                    # Кнопка добавления
                                    dbc.Button(
                                        [
                                            html.I(className="bi bi-plus me-1"),
                                            "Добавить сценарий",
                                        ],
                                        id="cushion-add-scenario-btn",
                                        color="secondary",
                                        outline=True,
                                        size="sm",
                                        className="mb-3",
                                    ),
                                    # Режим расчёта
                                    html.Hr(),
                                    dbc.Label("Режим расчёта", className="small"),
                                    dbc.RadioItems(
                                        id="cushion-calc-mode",
                                        options=[
                                            {
                                                "label": "Сумма всех сценариев",
                                                "value": "sum",
                                            },
                                            {
                                                "label": "По самому дорогому",
                                                "value": "max_scenario",
                                            },
                                        ],
                                        value="sum",
                                        inline=True,
                                        className="mb-3",
                                    ),
                                    # Рекомендация
                                    dbc.Alert(
                                        id="cushion-recommendation",
                                        color="info",
                                        className="mb-3",
                                    ),
                                    # Кнопка применения
                                    dbc.Button(
                                        "Применить рекомендацию",
                                        id="cushion-apply-recommendation-btn",
                                        color="primary",
                                        outline=True,
                                        size="sm",
                                    ),
                                ],
                                id="cushion-calculator-collapse",
                                is_open=False,
                            ),
                        ],
                        className="cushion-calculator-section",
                    ),
                    # Store для сценариев
                    dcc.Store(id="cushion-scenarios-store", data=[]),
                    # Store для manual flag (threshold изменён вручную)
                    dcc.Store(id="cushion-threshold-manual-flag", data=False),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Сбросить",
                        id="cushion-reset-btn",
                        color="danger",
                        outline=True,
                        className="me-auto",
                    ),
                    dbc.Button(
                        "Отмена",
                        id="cushion-cancel-btn",
                        color="secondary",
                        outline=True,
                    ),
                    dbc.Button(
                        "Сохранить",
                        id="cushion-save-btn",
                        color="primary",
                    ),
                ]
            ),
        ],
        id="cushion-modal",
        is_open=False,
        size="lg",
    )


def _build_budget_modal() -> dbc.Modal:
    """Создает модал для настройки месячного бюджета накоплений.

    Returns:
        dbc.Modal: Модал с формой настройки бюджета
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Настройка бюджета накоплений")),
            dbc.ModalBody(
                [
                    dbc.Row(
                        [
                            dbc.Label("Месячный бюджет", width=4),
                            dbc.Col(
                                dbc.Input(
                                    id="budget-input",
                                    type="number",
                                    min=0,
                                    step=0.01,
                                    placeholder="10000",
                                    required=True,
                                ),
                                width=8,
                            ),
                        ],
                        className="mb-3",
                    ),
                    html.P(
                        "Укажите сумму, которую вы планируете откладывать ежемесячно на все цели.",  # noqa: E501
                        className="text-muted small",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Отмена",
                        id="budget-cancel-btn",
                        color="secondary",
                        outline=True,
                    ),
                    dbc.Button(
                        "Сохранить",
                        id="save-budget-btn",
                        color="primary",
                    ),
                ]
            ),
        ],
        id="budget-modal",
        is_open=False,
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


# === REDISTRIBUTION MODAL HELPER FUNCTIONS ===


def _build_congratulation_section(preview: dict) -> html.Div:
    """Строит секцию поздравления с достижением цели.

    Структура:
    - Иконка трофея (bi-trophy-fill)
    - "Поздравляем!" (h5)
    - "Цель '{completed_goal_name}' достигнута!" (p)

    Args:
        preview: Десериализованный RedistributionPreview

    Returns:
        html.Div с congratulation контентом
    """
    goal_name = preview.get("completed_goal_name", "Цель")

    return html.Div(
        [
            html.I(
                className="bi bi-trophy-fill text-warning",
                style={"fontSize": "2.5rem"},
            ),
            html.H5("Поздравляем!", className="mt-2 mb-1"),
            html.P(
                f"Цель «{goal_name}» достигнута!",
                className="text-muted mb-0",
            ),
        ],
        className="congratulation-section text-center py-3",
    )


def _build_freed_budget_section(preview: dict) -> html.Div:
    """Строит секцию отображения освободившегося бюджета.

    Структура:
    - Label: "Освободился бюджет:" (p.freed-budget-label)
    - Value: format_amount(freed_budget) + "/мес" (span.freed-budget-value)
    - Если was_skipped_in_old_allocation=True:
      - Alert info: "Эта цель ранее не получала финансирования"

    Args:
        preview: Десериализованный RedistributionPreview

    Returns:
        html.Div с freed-budget контентом
    """
    freed_budget = preview.get("freed_budget", Decimal("0"))
    was_skipped = preview.get("was_skipped_in_old_allocation", False)

    children = [
        html.P("Освободился бюджет:", className="freed-budget-label mb-1"),
        html.Span(
            f"{format_amount(freed_budget)}/мес",
            className="freed-budget-value",
        ),
    ]

    # Если цель была пропущена в старом распределении - показываем info alert
    if was_skipped:
        children.append(
            dbc.Alert(
                [
                    html.I(className="bi bi-info-circle me-2"),
                    "Эта цель ранее не получала финансирования "
                    "из-за более приоритетных целей",
                ],
                color="info",
                className="mt-2 mb-0",
            )
        )

    return html.Div(children, className="freed-budget text-center py-2")


def _build_preview_section(preview_data: dict | None) -> html.Div:
    """Строит секцию сравнения OLD vs NEW allocation.

    Args:
        preview_data: RedistributionPreview данные или None

    Returns:
        html.Div: Таблица сравнения или info-сообщение
    """
    # Guard: нет данных preview
    if not preview_data:
        return html.Div(
            html.P(
                "Нет данных для отображения",
                className="text-muted text-center py-3",
            )
        )

    old_allocation = preview_data.get("old_allocation")
    new_allocation = preview_data.get("new_allocation")

    # Guard: нет оставшихся целей
    if not new_allocation or not new_allocation.get("results"):
        return html.Div(
            [
                html.I(
                    className="bi bi-info-circle text-info",
                    style={"fontSize": "2rem"},
                ),
                html.P(
                    "Нет оставшихся активных целей для перераспределения",
                    className="text-muted mt-2 mb-0",
                ),
            ],
            className="text-center py-4",
        )

    # Создаем словарь для быстрого доступа к OLD allocation по goal_id
    old_results_map = {}
    if old_allocation and old_allocation.get("results"):
        old_results_map = {r["goal_id"]: r for r in old_allocation["results"]}

    # Строим строки таблицы (только для активных целей без skipped_reason)
    table_rows = []
    for result in new_allocation["results"]:
        # Пропускаем цели с skipped_reason (completed, paused, zero_contribution)
        if result.get("skipped_reason") is not None:
            continue

        goal_id = result["goal_id"]
        goal_name = result["goal_name"]
        new_amount = Decimal(str(result["allocated_amount"]))

        # Получаем OLD amount (0 если цели не было в OLD)
        old_result = old_results_map.get(goal_id)
        old_amount = (
            Decimal(str(old_result["allocated_amount"])) if old_result else Decimal("0")
        )

        # Вычисляем изменение
        change = new_amount - old_amount

        # Определяем класс для цвета изменения
        change_class = ""
        change_prefix = ""
        if change > 0:
            change_class = "change-positive"
            change_prefix = "+"
        elif change < 0:
            change_class = "change-negative"

        # Добавляем строку
        table_rows.append(
            html.Tr(
                [
                    html.Td(goal_name, className="goal-name-cell"),
                    html.Td(format_amount(old_amount), className="text-end"),
                    html.Td(format_amount(new_amount), className="text-end fw-bold"),
                    html.Td(
                        f"{change_prefix}{format_amount(change)}",
                        className=f"text-end {change_class}",
                    ),
                ]
            )
        )

    # Итоговая строка
    old_total = (
        Decimal(str(old_allocation["total_allocated"]))
        if old_allocation
        else Decimal("0")
    )  # noqa: E501
    new_total = Decimal(str(new_allocation["total_allocated"]))
    total_change = new_total - old_total

    total_change_class = "change-positive" if total_change > 0 else ""
    total_change_prefix = "+" if total_change > 0 else ""

    table_rows.append(
        html.Tr(
            [
                html.Td(html.Strong("Итого"), className="goal-name-cell"),
                html.Td(format_amount(old_total), className="text-end"),
                html.Td(format_amount(new_total), className="text-end fw-bold"),
                html.Td(
                    f"{total_change_prefix}{format_amount(total_change)}",
                    className=f"text-end {total_change_class}",
                ),
            ],
            className="table-active",
        )
    )

    return html.Div(
        [
            html.H6("Изменение распределения бюджета", className="mb-3"),
            dbc.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Цель"),
                                html.Th("Было", className="text-end"),
                                html.Th("Станет", className="text-end"),
                                html.Th("Изменение", className="text-end"),
                            ]
                        )
                    ),
                    html.Tbody(table_rows),
                ],
                striped=True,
                hover=True,
                responsive=True,
                className="preview-table mb-0",
            ),
        ]
    )


def _build_redistribution_modal() -> dbc.Modal:
    """Создает модал для перераспределения средств при достижении цели.

    Структура модала:
    - ModalHeader: "Цель достигнута!"
    - ModalBody:
      - Congratulation section (название цели, сумма)
      - Freed budget display
      - Preview section (таблица сравнения OLD vs NEW)
    - ModalFooter:
      - Button "Перераспределить" (confirm) со Spinner
      - Button "Закрыть" (decline)

    Returns:
        dbc.Modal: Модал перераспределения
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [
                        html.I(className="bi bi-trophy-fill text-warning me-2"),
                        "Цель достигнута!",
                    ]
                ),
                close_button=True,
            ),
            dbc.ModalBody(
                [
                    # Congratulation section (заполняется через callback)
                    html.Div(
                        id="redistribution-congratulation-section",
                        className="congratulation-section mb-4",
                    ),
                    # Freed budget display
                    html.Div(
                        id="redistribution-freed-budget",
                        className="freed-budget mb-4",
                    ),
                    # Preview section
                    html.Div(
                        id="redistribution-preview-section",
                        className="preview-section",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Закрыть",
                        id="decline-redistribution-btn",
                        color="secondary",
                        outline=True,
                    ),
                    dbc.Button(
                        [
                            dbc.Spinner(
                                size="sm",
                                id="confirm-redistribution-spinner",
                                spinner_class_name="me-2",
                            ),
                            html.Span(
                                "Перераспределить",
                                id="confirm-redistribution-text",
                            ),
                        ],
                        id="confirm-redistribution-btn",
                        color="success",
                    ),
                ]
            ),
        ],
        id="redistribution-modal",
        is_open=False,
        centered=True,
        className="redistribution-modal",
    )


def _recalculate_and_render(
    session, user_id: int, budget: Decimal, savings_mode: str = "free"
):
    """Пересчитывает allocation и возвращает обновленный UI.

    Helper функция для переиспользования логики пересчета в callbacks.
    Загружает все цели, вызывает AllocationService, строит UI компоненты.

    Args:
        session: SQLAlchemy session
        user_id: ID пользователя
        budget: Месячный бюджет накоплений
        savings_mode: Режим накоплений ("free", "medium", "strict")

    Returns:
        Tuple[goals_container_children, allocation_summary_dict, goals_summary_dict]
    """
    service = GoalService(session)
    allocation_service = AllocationService()

    # Получаем все цели (ACTIVE + PAUSED)
    active_goals = service.get_all_by_user(user_id=user_id, status=GoalStatus.ACTIVE)
    paused_goals = service.get_all_by_user(user_id=user_id, status=GoalStatus.PAUSED)
    all_goals = active_goals + paused_goals

    # Если нет целей - empty state
    if not all_goals:
        return (
            [_build_empty_state()],
            None,  # allocation_summary
            None,  # goals_summary
        )

    # Расчет allocation
    allocation_summary = allocation_service.calculate_allocation(
        goals=all_goals,
        monthly_budget=budget,
        savings_mode=savings_mode,
    )

    # Формируем GoalsSummary
    total_target = sum(g.target_amount for g in all_goals)
    total_current = sum(g.current_amount for g in all_goals)
    goals_summary = GoalsSummary(
        total_goals_count=len(all_goals),
        active_goals_count=len(active_goals),
        total_target_amount=total_target,
        total_current_amount=total_current,
        total_progress_percentage=(
            float(total_current / total_target * 100) if total_target > 0 else 0
        ),
        monthly_budget=budget,
        total_allocated=allocation_summary["total_allocated"],
        total_shortfall=allocation_summary["total_shortfall"],
        all_goals_on_track=allocation_summary["all_goals_funded"],
        budget_not_set=allocation_summary["budget_not_set"],
    )

    # Преобразуем AllocationResult в dict для удобства
    allocation_dict = {r["goal_id"]: r for r in allocation_summary["results"]}

    # Строим layout
    goals_container_children = []

    # 1. Summary section + Mode selector (Row для адаптивности)
    goals_container_children.append(
        dbc.Row(
            [
                dbc.Col(
                    _build_summary_section(goals_summary, allocation_summary),
                    lg=8,
                    md=12,
                    className="mb-3 mb-lg-0",
                ),
                dbc.Col(
                    _build_mode_selector(savings_mode),
                    lg=4,
                    md=12,
                ),
            ],
            className="mb-4",
        )
    )

    # 2. Budget alert (если бюджет не настроен)
    if allocation_summary["budget_not_set"]:
        goals_container_children.append(_build_budget_alert())

    # 3. Goals list
    goals_container_children.append(_build_goals_list(all_goals, allocation_dict))

    return (
        goals_container_children,
        allocation_summary,  # для store
        goals_summary,  # для использования в callbacks if needed
    )


def create_goals_layout() -> html.Div:
    """Создает layout страницы накопительных целей.

    Returns:
        html.Div: Полный layout страницы Goals
    """
    return html.Div(
        [
            # Заголовок страницы с кнопкой создания
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
                    dbc.Button(
                        [html.I(className="bi bi-plus-lg me-2"), "Создать цель"],
                        id="create-goal-btn-header",
                        color="success",
                        className="create-goal-header-btn",
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
            # Карточка подушки безопасности (динамический контент)
            html.Div(id="cushion-card-container"),
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
            _build_cushion_modal(),
            _build_budget_modal(),
            _build_create_goal_modal(),
            _build_edit_goal_modal(),
            _build_contribution_modal(),
            _build_redistribution_modal(),
            # Confirm Dialog для удаления
            dcc.ConfirmDialog(
                id="confirm-delete-goal",
                message="Вы уверены? Цель и все взносы будут удалены "
                "без возможности восстановления.",
            ),
            # Store для ID текущей цели
            dcc.Store(id="current-goal-id", data=None),
            # Store для бюджета накоплений
            dcc.Store(id="goals-budget-store", data=None),
            # Store для результатов allocation
            dcc.Store(id="goals-allocation-store", data=None),
            # Store для режима накоплений
            dcc.Store(id="goals-savings-mode-store", data=None),
            # Store для preview перераспределения
            dcc.Store(id="redistribution-preview-store", data=None),
            # Store для состояния кнопки confirm (disabled во время обработки)
            dcc.Store(id="redistribution-btn-disabled-store", data=False),
            # Store для настроек подушки безопасности
            dcc.Store(id="cushion-settings-store", data=None),
            # Store для триггера обновления подушки
            dcc.Store(id="cushion-refresh-trigger", data=0),
        ],
        className="goals-container",
    )


# --- Callbacks (все с prevent_initial_call=True) ---


@callback(
    [
        Output("goal-card-container", "children"),
        Output("contributions-table-container", "children"),
        Output("current-goal-id", "data"),
        Output("goals-budget-store", "data"),
        Output("goals-allocation-store", "data"),
        Output("goals-savings-mode-store", "data"),
    ],
    Input("url", "pathname"),
)
def load_goal_data(pathname: str):
    """Загружает данные всех целей с распределением бюджета.

    Callback срабатывает при переходе на /goals.
    Загружает ACTIVE и PAUSED цели, вызывает AllocationService,
    строит summary section и список карточек целей.
    Инициализирует budget, allocation и savings_mode stores.

    Args:
        pathname: Текущий URL

    Returns:
        Tuple[goals_container, contributions_table, first_goal_id,
              budget, allocation, savings_mode]
    """
    if pathname != "/goals":
        raise PreventUpdate

    with get_db_session() as session:
        service = GoalService(session)

        # Получаем бюджет и режим накоплений
        monthly_budget = service.get_savings_budget(DEFAULT_USER_ID)
        savings_mode = service.get_savings_mode(DEFAULT_USER_ID)

        # Получаем все цели (ACTIVE + PAUSED)
        active_goals = service.get_all_by_user(
            user_id=DEFAULT_USER_ID, status=GoalStatus.ACTIVE
        )
        paused_goals = service.get_all_by_user(
            user_id=DEFAULT_USER_ID, status=GoalStatus.PAUSED
        )
        all_goals = active_goals + paused_goals

        # Если нет целей - empty state
        if not all_goals:
            return (
                _build_empty_state(),
                _build_contributions_table([]),
                None,
                monthly_budget,  # инициализируем budget store
                None,  # allocation store пуст
                savings_mode,  # инициализируем savings_mode store
            )

        # Пересчитываем allocation и строим UI
        goals_container_children, allocation_summary, _ = _recalculate_and_render(
            session, DEFAULT_USER_ID, monthly_budget, savings_mode=savings_mode
        )

        # История взносов для первой цели (по приоритету)
        first_goal = sorted(all_goals, key=lambda g: g.priority)[0]
        contributions = service.get_contributions(first_goal.id, limit=10)
        contrib_data = [
            ContributionDisplayData(
                id=c.id,
                amount=c.amount,
                contribution_date=c.contribution_date,
                description=c.description,
            )
            for c in contributions
        ]

        return (
            html.Div(goals_container_children),
            _build_contributions_table(contrib_data),
            first_goal.id,
            monthly_budget,  # инициализируем budget store
            allocation_summary,  # инициализируем allocation store
            savings_mode,  # инициализируем savings_mode store
        )


@callback(
    Output("goal-card-container", "children", allow_duplicate=True),
    Output("goals-allocation-store", "data", allow_duplicate=True),
    Output("goals-savings-mode-store", "data", allow_duplicate=True),
    Input("savings-mode-selector", "value"),
    State("goals-budget-store", "data"),
    prevent_initial_call=True,
)
def save_savings_mode(new_mode, budget):
    """Сохраняет выбранный режим накоплений и пересчитывает allocation.

    Args:
        new_mode: Новый режим ("free", "medium", "strict")
        budget: Текущий бюджет из store

    Returns:
        Tuple[goals_container, allocation_data, savings_mode]
    """
    if new_mode is None:
        raise PreventUpdate

    with get_db_session() as session:
        service = GoalService(session)
        service.update_savings_mode(DEFAULT_USER_ID, new_mode)
        session.commit()

        budget_decimal = _safe_budget_decimal(budget)
        goals_container_children, allocation_summary, _ = _recalculate_and_render(
            session, DEFAULT_USER_ID, budget_decimal, savings_mode=new_mode
        )

        return (
            html.Div(goals_container_children),
            allocation_summary,
            new_mode,
        )


@callback(
    Output("create-goal-modal", "is_open"),
    [
        Input("create-goal-btn-header", "n_clicks"),
        Input("create-goal-cancel-btn", "n_clicks"),
    ],
    State("create-goal-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_create_goal_modal(create_clicks, cancel_clicks, is_open):
    """Открывает/закрывает модал создания цели.

    Кнопка "Создать цель" находится в header страницы (create-goal-btn-header)
    и всегда доступна. Empty state больше не содержит дублирующую кнопку.
    """
    # Guard: проверка реального клика (ADR-003)
    if ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    if not ctx.triggered_id:
        raise PreventUpdate

    if ctx.triggered_id == "create-goal-btn-header":
        return True

    if ctx.triggered_id == "create-goal-cancel-btn":
        return False

    return is_open


@callback(
    [
        Output("create-goal-modal", "is_open", allow_duplicate=True),
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("contributions-table-container", "children", allow_duplicate=True),
        Output("current-goal-id", "data", allow_duplicate=True),
        Output("goals-allocation-store", "data", allow_duplicate=True),
        Output("create-goal-name-input", "value"),
        Output("create-goal-amount-input", "value"),
        Output("create-goal-date-picker", "date"),
        Output("goal-error-alert", "children"),
        Output("goal-error-alert", "is_open"),
    ],
    Input("create-goal-submit-btn", "n_clicks"),
    [
        State("create-goal-name-input", "value"),
        State("create-goal-amount-input", "value"),
        State("create-goal-date-picker", "date"),
        State("goals-budget-store", "data"),
        State("goals-savings-mode-store", "data"),
    ],
    prevent_initial_call=True,
)
def create_goal(n_clicks, name, target_amount, target_date_str, budget, savings_mode):
    """Создает новую накопительную цель."""
    if not n_clicks:
        raise PreventUpdate

    # Валидация на стороне UI
    if not name or not name.strip():
        return (
            True,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            "Укажите название цели",
            True,
        )

    if not target_amount or target_amount <= 0:
        return (
            True,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            "Укажите положительную сумму",
            True,
        )

    # Парсим дату
    target_date = parse_date_safe(target_date_str)
    if not target_date:
        return (
            True,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            "Укажите дату достижения цели",
            True,
        )

    try:
        with get_db_session() as session:
            service = GoalService(session)
            goal = service.create_goal(
                user_id=DEFAULT_USER_ID,
                name=name.strip(),
                target_amount=Decimal(str(target_amount)),
                target_date=target_date,
            )
            session.commit()

            logger.info(f"Создана цель: {goal.name} (id={goal.id})")

            # Пересчитываем allocation и строим UI
            budget_decimal = _safe_budget_decimal(budget)
            goals_container_children, allocation_summary, _ = _recalculate_and_render(
                session,
                DEFAULT_USER_ID,
                budget_decimal,
                savings_mode=savings_mode or "free",
            )

            # История взносов для созданной цели
            contributions = service.get_contributions(goal.id, limit=10)
            contrib_data = [
                ContributionDisplayData(
                    id=c.id,
                    amount=c.amount,
                    contribution_date=c.contribution_date,
                    description=c.description,
                )
                for c in contributions
            ]

            # Успех: закрываем модал, очищаем форму, обновляем UI
            min_date = (date.today() + timedelta(days=MIN_GOAL_DAYS)).isoformat()
            return (
                False,  # close modal
                html.Div(goals_container_children),
                _build_contributions_table(contrib_data),
                goal.id,
                serialize_allocation_summary(
                    allocation_summary
                ),  # сериализуем для Store
                "",  # clear name
                None,  # clear amount
                min_date,  # reset date
                "",
                False,
            )

    except Exception as e:
        logger.warning(f"Ошибка создания цели: {e}")
        return (
            True,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            str(e),
            True,
        )


@callback(
    [
        Output("contribution-modal", "is_open"),
        Output("current-goal-id", "data", allow_duplicate=True),
    ],
    [
        Input({"type": "add-contribution-btn", "index": ALL}, "n_clicks"),
        Input("contribution-cancel-btn", "n_clicks"),
    ],
    State("contribution-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_contribution_modal(add_clicks_list, cancel_clicks, is_open):
    """Открывает/закрывает модал добавления взноса."""
    # Guard: проверка реального клика (ADR-003)
    if ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    triggered_id = ctx.triggered_id

    # Pattern-Matching button clicked
    if (
        isinstance(triggered_id, dict)
        and triggered_id.get("type") == "add-contribution-btn"
    ):
        goal_id = triggered_id["index"]
        return True, goal_id

    if triggered_id == "contribution-cancel-btn":
        return False, no_update

    return is_open, no_update


@callback(
    [
        Output("contribution-modal", "is_open", allow_duplicate=True),
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("contributions-table-container", "children", allow_duplicate=True),
        Output("goals-allocation-store", "data", allow_duplicate=True),
        Output("contribution-amount-input", "value"),
        Output("contribution-date-picker", "date"),
        Output("contribution-description-input", "value"),
        Output("goal-error-alert", "children", allow_duplicate=True),
        Output("goal-error-alert", "is_open", allow_duplicate=True),
        # Redistribution outputs (protocol-0008)
        Output("redistribution-modal", "is_open"),
        Output("redistribution-preview-store", "data"),
        Output("redistribution-btn-disabled-store", "data"),
    ],
    Input("contribution-submit-btn", "n_clicks"),
    [
        State("current-goal-id", "data"),
        State("contribution-amount-input", "value"),
        State("contribution-date-picker", "date"),
        State("contribution-description-input", "value"),
        State("goals-budget-store", "data"),
        State("goals-savings-mode-store", "data"),
    ],
    prevent_initial_call=True,
)
def add_contribution(
    n_clicks, goal_id, amount, date_str, description, budget, savings_mode
):
    """Добавляет взнос в цель.

    При достижении цели (just-completed) открывает модал перераспределения.
    """
    if not n_clicks or not goal_id:
        raise PreventUpdate

    if not amount or amount <= 0:
        return (
            True,  # contribution-modal stays open
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            "Укажите положительную сумму",
            True,
            # Redistribution outputs - no changes
            no_update,
            no_update,
            no_update,
        )

    contribution_date = parse_date_safe(date_str)

    start_time = time.perf_counter()

    try:
        with get_db_session() as session:
            goal_service = GoalService(session)

            # Just-completed detection: проверяем состояние ДО взноса
            goal_before = goal_service.get_by_id(goal_id)
            if not goal_before:
                raise ValueError(f"Цель {goal_id} не найдена")
            was_completed_before = goal_before.is_completed

            # Добавляем взнос
            goal = goal_service.add_contribution(
                goal_id=goal_id,
                amount=Decimal(str(amount)),
                contribution_date=contribution_date,
                description=description.strip() if description else None,
            )
            session.commit()

            # Just-completed detection: проверяем состояние ПОСЛЕ взноса
            just_completed = goal.is_completed and not was_completed_before

            logger.info(
                f"Добавлен взнос {amount} в цель {goal_id}"
                f"{' (цель достигнута!)' if just_completed else ''}"
            )

            # Пересчитываем allocation и строим UI
            budget_decimal = _safe_budget_decimal(budget)
            mode = savings_mode or "free"
            goals_container_children, allocation_summary, _ = _recalculate_and_render(
                session,
                DEFAULT_USER_ID,
                budget_decimal,
                savings_mode=mode,
            )

            # Получаем обновленную историю взносов
            contributions = goal_service.get_contributions(goal.id, limit=10)
            contrib_data = [
                ContributionDisplayData(
                    id=c.id,
                    amount=c.amount,
                    contribution_date=c.contribution_date,
                    description=c.description,
                )
                for c in contributions
            ]

            # Базовые outputs
            base_outputs = (
                False,  # close contribution modal
                html.Div(goals_container_children),
                _build_contributions_table(contrib_data),
                serialize_allocation_summary(allocation_summary),
                None,  # clear amount
                date.today().isoformat(),  # reset date
                "",  # clear description
                "",
                False,
            )

            # Redistribution outputs
            if just_completed:
                # Вычисляем preview перераспределения
                allocation_service = AllocationService()
                redistribution_service = RedistributionService(allocation_service)

                all_goals = goal_service.get_all_by_user(DEFAULT_USER_ID)
                preview = redistribution_service.calculate_redistribution_preview(
                    completed_goal=goal,
                    all_goals=all_goals,
                    monthly_budget=budget_decimal,
                    savings_mode=mode,
                )

                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.info(
                    f"add_contribution with redistribution preview: {elapsed_ms:.2f}ms"
                )

                redistribution_outputs = (
                    True,  # open redistribution modal
                    serialize_redistribution_preview(preview),
                    False,  # btn not disabled
                )
            else:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(f"add_contribution: {elapsed_ms:.2f}ms")

                redistribution_outputs = (
                    False,  # redistribution modal stays closed
                    None,  # no preview data
                    False,  # btn not disabled
                )

            return base_outputs + redistribution_outputs

    except Exception as e:
        logger.warning(f"Ошибка добавления взноса: {e}")
        return (
            True,  # contribution modal stays open
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            str(e),
            True,
            # Redistribution outputs - no changes
            no_update,
            no_update,
            no_update,
        )


@callback(
    [
        Output("edit-goal-modal", "is_open"),
        Output("edit-goal-name-input", "value"),
        Output("edit-goal-amount-input", "value"),
        Output("edit-goal-date-picker", "date"),
        Output("current-goal-id", "data", allow_duplicate=True),
    ],
    [
        Input({"type": "edit-goal-btn", "index": ALL}, "n_clicks"),
        Input("edit-goal-cancel-btn", "n_clicks"),
    ],
    State("edit-goal-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_edit_modal(edit_clicks_list, cancel_clicks, is_open):
    """Открывает/закрывает модал редактирования с загрузкой данных.

    Pattern-Matching callback - goal_id извлекается из triggered_id["index"].
    При открытии загружаем актуальные данные цели из БД.
    """
    # Guard: проверка реального клика (ADR-003)
    if ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    triggered_id = ctx.triggered_id

    if triggered_id == "edit-goal-cancel-btn":
        return False, no_update, no_update, no_update, no_update

    # Pattern-Matching button clicked
    if isinstance(triggered_id, dict) and triggered_id.get("type") == "edit-goal-btn":
        goal_id = triggered_id["index"]

        with get_db_session() as session:
            service = GoalService(session)
            goal = service.get_by_id(goal_id)

            if not goal:
                raise PreventUpdate

            return (
                True,
                goal.name,
                float(goal.target_amount),
                goal.target_date.isoformat(),
                goal_id,
            )

    raise PreventUpdate


@callback(
    [
        Output("edit-goal-modal", "is_open", allow_duplicate=True),
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("goals-allocation-store", "data", allow_duplicate=True),
        Output("goal-error-alert", "children", allow_duplicate=True),
        Output("goal-error-alert", "is_open", allow_duplicate=True),
    ],
    Input("edit-goal-submit-btn", "n_clicks"),
    [
        State("current-goal-id", "data"),
        State("edit-goal-name-input", "value"),
        State("edit-goal-amount-input", "value"),
        State("edit-goal-date-picker", "date"),
        State("goals-budget-store", "data"),
        State("goals-savings-mode-store", "data"),
    ],
    prevent_initial_call=True,
)
def update_goal(
    n_clicks, goal_id, name, target_amount, target_date_str, budget, savings_mode
):
    """Обновляет параметры цели."""
    if not n_clicks or not goal_id:
        raise PreventUpdate

    target_date = parse_date_safe(target_date_str)

    try:
        with get_db_session() as session:
            service = GoalService(session)
            service.update_goal(
                goal_id=goal_id,
                name=name.strip() if name else None,
                target_amount=Decimal(str(target_amount)) if target_amount else None,
                target_date=target_date,
            )
            session.commit()

            logger.info(f"Обновлена цель {goal_id}")

            # Пересчитываем allocation и строим UI
            budget_decimal = _safe_budget_decimal(budget)
            goals_container_children, allocation_summary, _ = _recalculate_and_render(
                session,
                DEFAULT_USER_ID,
                budget_decimal,
                savings_mode=savings_mode or "free",
            )

            return (
                False,
                html.Div(goals_container_children),
                serialize_allocation_summary(
                    allocation_summary
                ),  # сериализуем для Store
                "",
                False,
            )

    except Exception as e:
        logger.warning(f"Ошибка обновления цели: {e}")
        return True, no_update, no_update, str(e), True


@callback(
    [
        Output("confirm-delete-goal", "displayed"),
        Output("current-goal-id", "data", allow_duplicate=True),
    ],
    Input({"type": "delete-goal-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def request_delete_goal(n_clicks_list):
    """Открывает диалог подтверждения удаления.

    Использует dcc.ConfirmDialog - нативный браузерный диалог.
    Pattern-Matching callback - goal_id извлекается из triggered_id["index"].
    """
    # DEBUG: Remove after BUG-02 resolved
    logger.debug(f"request_delete_goal called: ctx.triggered={ctx.triggered}")
    logger.debug(f"triggered_id={ctx.triggered_id}")
    logger.debug(f"n_clicks_list={n_clicks_list}")

    # Guard: проверка реального клика (ADR-003)
    if ctx.triggered[0].get("value") is None:
        logger.debug("Guard clause: value is None, raising PreventUpdate")
        raise PreventUpdate

    triggered_id = ctx.triggered_id
    if (
        not isinstance(triggered_id, dict)
        or triggered_id.get("type") != "delete-goal-btn"
    ):
        logger.debug("Guard clause: invalid triggered_id, raising PreventUpdate")
        raise PreventUpdate

    goal_id = triggered_id["index"]
    logger.debug(f"Opening delete confirmation for goal_id={goal_id}")
    return True, goal_id


@callback(
    [
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("contributions-table-container", "children", allow_duplicate=True),
        Output("current-goal-id", "data", allow_duplicate=True),
        Output("goals-allocation-store", "data", allow_duplicate=True),
    ],
    Input("confirm-delete-goal", "submit_n_clicks"),
    [
        State("current-goal-id", "data"),
        State("goals-budget-store", "data"),
        State("goals-savings-mode-store", "data"),
    ],
    prevent_initial_call=True,
)
def confirm_delete_goal(submit_clicks, goal_id, budget, savings_mode):
    """Удаляет цель после подтверждения.

    Callback срабатывает при клике "OK" в ConfirmDialog.
    """
    if not submit_clicks or not goal_id:
        raise PreventUpdate

    with get_db_session() as session:
        service = GoalService(session)
        deleted = service.delete_goal(goal_id)
        session.commit()

        if not deleted:
            raise PreventUpdate

        logger.info(f"Удалена цель {goal_id}")

        # Пересчитываем allocation и строим UI
        budget_decimal = _safe_budget_decimal(budget)
        goals_container_children, allocation_summary, _ = _recalculate_and_render(
            session,
            DEFAULT_USER_ID,
            budget_decimal,
            savings_mode=savings_mode or "free",
        )

        # Если есть оставшиеся цели - показываем contributions первой по priority
        active_goals = service.get_all_by_user(
            user_id=DEFAULT_USER_ID, status=GoalStatus.ACTIVE
        )
        paused_goals = service.get_all_by_user(
            user_id=DEFAULT_USER_ID, status=GoalStatus.PAUSED
        )
        all_goals = active_goals + paused_goals

        if all_goals:
            # Сортируем по priority и берем первую
            first_goal = sorted(all_goals, key=lambda g: g.priority)[0]
            contributions = service.get_contributions(first_goal.id, limit=10)
            contrib_data = [
                ContributionDisplayData(
                    id=c.id,
                    amount=c.amount,
                    contribution_date=c.contribution_date,
                    description=c.description,
                )
                for c in contributions
            ]
            return (
                html.Div(goals_container_children),
                _build_contributions_table(contrib_data),
                first_goal.id,
                serialize_allocation_summary(allocation_summary),
            )
        else:
            # Нет целей - empty state
            return (
                html.Div(goals_container_children),
                _build_contributions_table([]),
                None,
                None,
            )


@callback(
    [
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("goals-allocation-store", "data", allow_duplicate=True),
    ],
    Input({"type": "toggle-status-btn", "index": ALL}, "n_clicks"),
    [
        State("goals-budget-store", "data"),
        State("goals-savings-mode-store", "data"),
    ],
    prevent_initial_call=True,
)
def toggle_goal_status(n_clicks_list, budget, savings_mode):
    """Переключает статус цели ACTIVE <-> PAUSED.

    Бизнес-правила:
    - ACTIVE -> PAUSED: всегда разрешено
    - PAUSED -> ACTIVE: разрешено
    - COMPLETED -> любой: запрещено (возврат из COMPLETED не поддерживается)

    Pattern-Matching callback - goal_id извлекается из triggered_id["index"].
    После изменения статуса пересчитывает allocation.
    """
    # Guard: проверка реального клика (ADR-003)
    if ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    triggered_id = ctx.triggered_id
    if (
        not isinstance(triggered_id, dict)
        or triggered_id.get("type") != "toggle-status-btn"
    ):
        raise PreventUpdate

    goal_id = triggered_id["index"]

    with get_db_session() as session:
        service = GoalService(session)
        goal = service.get_by_id(goal_id)

        if not goal:
            raise PreventUpdate

        # Бизнес-правила переключения статуса
        if goal.status == GoalStatus.COMPLETED:
            # Нельзя менять статус завершенной цели
            raise PreventUpdate

        # Определяем новый статус
        new_status = (
            GoalStatus.PAUSED if goal.status == GoalStatus.ACTIVE else GoalStatus.ACTIVE
        )

        service.update_goal(goal_id, status=new_status)
        session.commit()

        logger.info(f"Статус цели {goal_id} изменен на {new_status.value}")

        # Пересчитываем allocation и UI
        budget_decimal = _safe_budget_decimal(budget)
        goals_container, allocation_data, _ = _recalculate_and_render(
            session,
            DEFAULT_USER_ID,
            budget_decimal,
            savings_mode=savings_mode or "free",
        )

        return goals_container, serialize_allocation_summary(allocation_data)


@callback(
    [
        Output("budget-modal", "is_open"),
        Output("budget-input", "value"),
    ],
    Input("open-budget-modal-btn", "n_clicks"),
    State("goals-budget-store", "data"),
    prevent_initial_call=True,
)
def open_budget_modal(n_clicks, current_budget):
    """Открывает модал настройки бюджета с текущим значением.

    Args:
        n_clicks: Количество кликов на кнопку открытия
        current_budget: Текущий бюджет из Store (может быть None)

    Returns:
        Tuple[is_open, budget_value]
    """
    if not n_clicks:
        raise PreventUpdate

    # Загружаем текущий бюджет из БД если не в Store
    if current_budget is None:
        with get_db_session() as session:
            service = GoalService(session)
            current_budget = service.get_savings_budget(DEFAULT_USER_ID)

    # Конвертируем Decimal в float для Input
    budget_value = float(current_budget) if current_budget else None

    return True, budget_value


@callback(
    [
        Output("budget-modal", "is_open", allow_duplicate=True),
        Output("budget-cancel-btn", "n_clicks"),
    ],
    Input("budget-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def close_budget_modal(n_clicks):
    """Закрывает модал настройки бюджета при клике на Отмена.

    Args:
        n_clicks: Количество кликов на кнопку Отмена

    Returns:
        Tuple[is_open, reset_n_clicks]
    """
    if not n_clicks:
        raise PreventUpdate

    return False, 0


@callback(
    [
        Output("budget-modal", "is_open", allow_duplicate=True),
        Output("goals-budget-store", "data", allow_duplicate=True),
        Output("goals-allocation-store", "data", allow_duplicate=True),
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("goal-error-alert", "children", allow_duplicate=True),
        Output("goal-error-alert", "is_open", allow_duplicate=True),
    ],
    Input("save-budget-btn", "n_clicks"),
    [
        State("budget-input", "value"),
        State("goals-savings-mode-store", "data"),
    ],
    prevent_initial_call=True,
)
def save_budget(n_clicks, budget_value, savings_mode):
    """Сохраняет бюджет и пересчитывает allocation для всех целей.

    Args:
        n_clicks: Количество кликов на кнопку Сохранить
        budget_value: Значение бюджета из Input

    Returns:
        Tuple[is_open, budget_store, allocation_store, goals_container, error_msg, error_open]  # noqa: E501
    """
    if not n_clicks:
        raise PreventUpdate

    # Валидация
    if budget_value is None or budget_value < 0:
        return (
            True,  # keep modal open
            no_update,
            no_update,
            no_update,
            "Бюджет должен быть неотрицательным числом",
            True,
        )

    budget = Decimal(str(budget_value))

    try:
        with get_db_session() as session:
            service = GoalService(session)

            # Сохраняем бюджет в БД
            service.update_savings_budget(DEFAULT_USER_ID, budget)
            session.commit()

            # Пересчитываем allocation и строим UI
            goals_container_children, allocation_summary, _ = _recalculate_and_render(
                session, DEFAULT_USER_ID, budget, savings_mode=savings_mode or "free"
            )

            logger.info(f"Бюджет накоплений обновлен: {budget}")

            return (
                False,  # close modal
                budget,  # update budget store
                serialize_allocation_summary(
                    allocation_summary
                ),  # update allocation store
                html.Div(goals_container_children),  # update goals container
                "",
                False,
            )

    except Exception as e:
        logger.error(f"Ошибка сохранения бюджета: {e}")
        return (
            True,
            no_update,
            no_update,
            no_update,
            f"Ошибка сохранения: {str(e)}",
            True,
        )


@callback(
    [
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("goals-allocation-store", "data", allow_duplicate=True),
    ],
    Input({"type": "priority-up-btn", "index": ALL}, "n_clicks"),
    [
        State("goals-budget-store", "data"),
        State("goals-savings-mode-store", "data"),
    ],
    prevent_initial_call=True,
)
def move_priority_up(n_clicks_list, budget, savings_mode):
    """Перемещает цель на один приоритет вверх (уменьшает priority на 1).

    Pattern-Matching callback с guard clauses согласно ADR-003.
    После изменения приоритета пересчитывает allocation.

    Args:
        n_clicks_list: Список кликов на все кнопки priority-up
        budget: Текущий бюджет из Store

    Returns:
        Tuple[goals_container, allocation_store]
    """
    # Guard: проверка автовызова при DOM updates (ADR-003)
    if ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    triggered_id = ctx.triggered_id

    # Guard: проверка валидного triggered_id
    if not triggered_id or not triggered_id.get("index"):
        raise PreventUpdate

    goal_id = triggered_id["index"]

    try:
        with get_db_session() as session:
            service = GoalService(session)

            # Получаем текущий бюджет если не в Store
            if budget is None:
                budget = service.get_savings_budget(DEFAULT_USER_ID)

            # Перемещаем приоритет вверх
            service.move_priority_up(goal_id)
            session.commit()

            # Пересчитываем allocation и строим UI
            goals_container_children, allocation_summary, _ = _recalculate_and_render(
                session, DEFAULT_USER_ID, budget, savings_mode=savings_mode or "free"
            )

            logger.info(f"Приоритет цели {goal_id} повышен")

            return (
                html.Div(goals_container_children),
                serialize_allocation_summary(allocation_summary),
            )

    except Exception as e:
        logger.error(f"Ошибка изменения приоритета: {e}")
        raise PreventUpdate


@callback(
    [
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("goals-allocation-store", "data", allow_duplicate=True),
    ],
    Input({"type": "priority-down-btn", "index": ALL}, "n_clicks"),
    [
        State("goals-budget-store", "data"),
        State("goals-savings-mode-store", "data"),
    ],
    prevent_initial_call=True,
)
def move_priority_down(n_clicks_list, budget, savings_mode):
    """Перемещает цель на один приоритет вниз (увеличивает priority на 1).

    Pattern-Matching callback с guard clauses согласно ADR-003.
    После изменения приоритета пересчитывает allocation.

    Args:
        n_clicks_list: Список кликов на все кнопки priority-down
        budget: Текущий бюджет из Store

    Returns:
        Tuple[goals_container, allocation_store]
    """
    # Guard: проверка автовызова при DOM updates (ADR-003)
    if ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    triggered_id = ctx.triggered_id

    # Guard: проверка валидного triggered_id
    if not triggered_id or not triggered_id.get("index"):
        raise PreventUpdate

    goal_id = triggered_id["index"]

    try:
        with get_db_session() as session:
            service = GoalService(session)

            # Получаем текущий бюджет если не в Store
            if budget is None:
                budget = service.get_savings_budget(DEFAULT_USER_ID)

            # Перемещаем приоритет вниз
            service.move_priority_down(goal_id)
            session.commit()

            # Пересчитываем allocation и строим UI
            goals_container_children, allocation_summary, _ = _recalculate_and_render(
                session, DEFAULT_USER_ID, budget, savings_mode=savings_mode or "free"
            )

            logger.info(f"Приоритет цели {goal_id} понижен")

            return (
                html.Div(goals_container_children),
                serialize_allocation_summary(allocation_summary),
            )

    except Exception as e:
        logger.error(f"Ошибка изменения приоритета: {e}")
        raise PreventUpdate


# =============================================================================
# Redistribution Callbacks (protocol-0008)
# =============================================================================


@callback(
    [
        Output("redistribution-modal", "is_open", allow_duplicate=True),
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("goals-allocation-store", "data", allow_duplicate=True),
        Output("confirm-redistribution-btn", "disabled"),
        Output("confirm-redistribution-spinner", "style"),
        Output("confirm-redistribution-text", "children"),
    ],
    Input("confirm-redistribution-btn", "n_clicks"),
    [
        State("redistribution-preview-store", "data"),
        State("goals-budget-store", "data"),
        State("goals-savings-mode-store", "data"),
        State("redistribution-btn-disabled-store", "data"),
    ],
    prevent_initial_call=True,
)
def confirm_redistribution(n_clicks, preview_data, budget, savings_mode, btn_disabled):
    """Подтверждает перераспределение средств после достижения цели.

    Логирует событие и пересчитывает allocation для обновления UI.
    """
    # Guard clauses
    if not n_clicks:
        raise PreventUpdate
    if btn_disabled:
        raise PreventUpdate  # Debounce protection

    start_time = time.perf_counter()

    # Deserialize preview
    preview = deserialize_redistribution_preview(preview_data)
    if not preview:
        logger.warning("confirm_redistribution: empty preview data")
        raise PreventUpdate

    try:
        with get_db_session() as session:
            allocation_service = AllocationService()
            redistribution_service = RedistributionService(allocation_service)

            # Логируем событие подтверждения
            redistribution_service.log_redistribution_event(
                preview=preview,
                action="confirmed",
            )

            # Пересчитываем allocation и строим UI
            budget_decimal = _safe_budget_decimal(budget)
            mode = savings_mode or "free"
            goals_container_children, allocation_summary, _ = _recalculate_and_render(
                session,
                DEFAULT_USER_ID,
                budget_decimal,
                savings_mode=mode,
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"confirm_redistribution: {elapsed_ms:.2f}ms")

            return (
                False,  # close modal
                html.Div(goals_container_children),
                serialize_allocation_summary(allocation_summary),
                True,  # keep btn disabled (prevent double-click)
                {"display": "none"},  # hide spinner
                "Перераспределить",  # reset button text
            )

    except Exception as e:
        logger.error(f"Ошибка подтверждения перераспределения: {e}")
        return (
            True,  # keep modal open
            no_update,
            no_update,
            False,  # re-enable button
            {"display": "none"},  # hide spinner
            "Перераспределить",
        )


@callback(
    Output("redistribution-modal", "is_open", allow_duplicate=True),
    Input("decline-redistribution-btn", "n_clicks"),
    State("redistribution-preview-store", "data"),
    prevent_initial_call=True,
)
def decline_redistribution(n_clicks, preview_data):
    """Отклоняет перераспределение средств.

    Логирует событие отклонения и закрывает модал.
    """
    # Guard clause
    if not n_clicks:
        raise PreventUpdate

    # Deserialize preview для логирования
    preview = deserialize_redistribution_preview(preview_data)

    if preview:
        try:
            allocation_service = AllocationService()
            redistribution_service = RedistributionService(allocation_service)

            # Логируем событие отклонения
            redistribution_service.log_redistribution_event(
                preview=preview,
                action="declined",
            )

            logger.info(
                f"Перераспределение отклонено для цели "
                f"{preview.get('completed_goal_name', 'unknown')}"
            )

        except Exception as e:
            logger.warning(f"Ошибка логирования отклонения: {e}")
            # Не блокируем закрытие модала при ошибке логирования

    return False  # close modal


# === REDISTRIBUTION MODAL CONTENT CALLBACK ===


@callback(
    [
        Output("redistribution-congratulation-section", "children"),
        Output("redistribution-freed-budget", "children"),
        Output("redistribution-preview-section", "children"),
    ],
    Input("redistribution-preview-store", "data"),
    prevent_initial_call=True,
)
def populate_redistribution_modal(
    preview_data: dict | None,
) -> tuple[html.Div, html.Div, html.Div]:
    """Заполняет содержимое модала перераспределения.

    Callback срабатывает при изменении данных в redistribution-preview-store.
    Десериализует данные и вызывает helper функции для построения UI секций.

    Args:
        preview_data: JSON данные из dcc.Store или None

    Returns:
        Tuple из трех html.Div для секций модала

    Raises:
        PreventUpdate: При отсутствии реального триггера или None данных
    """
    # Guard clause (ADR-003 compliance)
    if not ctx.triggered or ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    # Null data check
    if preview_data is None:
        return (html.Div(), html.Div(), html.Div())

    # Deserialize with error handling
    try:
        preview = deserialize_redistribution_preview(preview_data)
    except Exception as e:
        logger.warning(f"populate_redistribution_modal: deserialize error: {e}")
        return (
            html.Div("Ошибка загрузки данных", className="text-muted"),
            html.Div(),
            html.Div(),
        )

    # Build all three sections
    congratulation = _build_congratulation_section(preview)
    freed_budget = _build_freed_budget_section(preview)
    preview_section = _build_preview_section(preview)

    return (congratulation, freed_budget, preview_section)
