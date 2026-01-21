"""TypedDicts для типизации данных накопительных целей."""
from datetime import date
from decimal import Decimal
from typing import TypedDict


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
