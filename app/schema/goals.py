"""TypedDicts для типизации данных накопительных целей."""
from datetime import date
from decimal import Decimal
from typing import Literal, TypedDict

from app.models.database import Goal


class AllocationResult(TypedDict):
    """Результат распределения для одной цели.

    Attributes:
        goal_id: ID цели.
        goal_name: Название цели.
        priority: Приоритет цели (1 = высший).
        monthly_contribution_needed: Необходимый ежемесячный взнос
            (Goal.monthly_contribution).
        allocated_amount: Сколько выделено из бюджета.
        is_fully_funded: Полностью ли профинансирована
            (allocated >= needed).
        shortfall: Дефицит (max(0, needed - allocated)).
        skipped_reason: Причина пропуска
            ("completed", "paused", "zero_contribution") или None.
    """

    goal_id: int
    goal_name: str
    priority: int
    monthly_contribution_needed: Decimal
    allocated_amount: Decimal
    is_fully_funded: bool
    shortfall: Decimal
    skipped_reason: str | None


class AllocationSummary(TypedDict):
    """Сводка распределения бюджета.

    Attributes:
        total_budget: Общий месячный бюджет (User.monthly_savings_budget).
        total_allocated: Сумма выделенных средств по активным целям.
        total_needed: Сумма необходимых средств по активным целям.
        total_shortfall: Сумма дефицитов по активным целям.
        results: Детализация по каждой цели.
        all_goals_funded: Все ли цели полностью профинансированы (total_shortfall == 0).
        budget_not_set: Бюджет не настроен (total_budget == 0).
    """

    total_budget: Decimal
    total_allocated: Decimal
    total_needed: Decimal
    total_shortfall: Decimal
    results: list[AllocationResult]
    all_goals_funded: bool
    budget_not_set: bool


class GoalDisplayData(TypedDict):
    """Данные для отображения цели в UI.

    Attributes:
        id: ID цели.
        name: Название цели.
        target_amount: Целевая сумма.
        current_amount: Текущая накопленная сумма.
        target_date: Целевая дата достижения.
        status: Статус цели ("active", "completed", "paused").
        progress_percentage: Процент выполнения (0-100).
        monthly_contribution: Необходимый ежемесячный взнос.
        days_remaining: Дней до целевой даты.
        is_completed: Цель достигнута.
        priority: Приоритет цели (1 = высший).
        allocated_amount: Выделенная сумма из бюджета
            (None если не распределено).
        allocation_status: Статус распределения
            ("fully_funded", "partial", "not_funded", "skipped") или None.
    """

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
    priority: int
    allocated_amount: Decimal | None
    allocation_status: str | None


class GoalsSummary(TypedDict):
    """Сводка по всем активным целям.

    Attributes:
        total_goals_count: Общее количество целей.
        active_goals_count: Количество активных целей.
        total_target_amount: Сумма целевых значений всех целей.
        total_current_amount: Сумма текущих накоплений всех целей.
        total_progress_percentage: Общий процент выполнения (0-100).
        monthly_budget: Месячный бюджет на накопления.
        total_allocated: Сумма выделенных средств.
        total_shortfall: Сумма дефицитов.
        all_goals_on_track: Все ли цели на треке (без дефицитов).
        budget_not_set: Бюджет не настроен.
    """

    total_goals_count: int
    active_goals_count: int
    total_target_amount: Decimal
    total_current_amount: Decimal
    total_progress_percentage: float
    monthly_budget: Decimal
    total_allocated: Decimal
    total_shortfall: Decimal
    all_goals_on_track: bool
    budget_not_set: bool


class RedistributionPreview(TypedDict):
    """Preview данные для модала перераспределения.

    Используется для отображения влияния достижения цели на остальные цели.
    Содержит сравнение старого и нового распределения бюджета.

    Attributes:
        completed_goal_id: ID завершенной цели.
        completed_goal_name: Название завершенной цели.
        freed_budget: Освободившийся бюджет (ежемесячный взнос завершенной цели).
        was_skipped_in_old_allocation: Была ли цель пропущена в старом распределении
            (например, priority был низкий и бюджета не хватило).
        has_remaining_goals: Есть ли оставшиеся активные цели для перераспределения.
        remaining_goals_count: Количество оставшихся активных целей.
        new_allocation: Новое распределение после завершения цели (или None).
        old_allocation: Старое распределение до завершения цели (или None).
        calculation_time_ms: Время расчета в миллисекундах (NFR-2 verification).
    """

    completed_goal_id: int
    completed_goal_name: str
    freed_budget: Decimal
    was_skipped_in_old_allocation: bool
    has_remaining_goals: bool
    remaining_goals_count: int
    new_allocation: AllocationSummary | None
    old_allocation: AllocationSummary | None
    calculation_time_ms: float


class RedistributionEvent(TypedDict):
    """Структура события перераспределения для аудита (NFR-4).

    Логируется при подтверждении или отклонении перераспределения
    для последующего анализа поведения пользователей.

    Attributes:
        timestamp: ISO-формат времени события.
        user_id: ID пользователя.
        completed_goal_id: ID завершенной цели.
        completed_goal_name: Название завершенной цели.
        freed_budget: Освободившийся бюджет (str для JSON-совместимости).
        remaining_goals_count: Количество оставшихся активных целей.
        action: Действие пользователя ("confirmed" | "declined").
        new_allocation_summary: Сводка нового распределения (dict для JSON).
    """

    timestamp: str
    user_id: int
    completed_goal_id: int
    completed_goal_name: str
    freed_budget: str  # str для JSON
    remaining_goals_count: int
    action: str  # "confirmed" | "declined"
    new_allocation_summary: dict | None


class ContributionInfo(TypedDict):
    """Информация о взносе для confirmation modal."""

    contribution_id: int
    amount: Decimal
    contribution_date: date
    goal_name: str


class ContributionUpdateResult(TypedDict):
    """Результат операции обновления/удаления взноса."""

    success: bool
    goal: Goal | None
    status_changed: bool
    new_status: Literal["active", "completed"] | None
    error: str | None
    contribution_info: ContributionInfo | None
