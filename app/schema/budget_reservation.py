"""TypedDicts для интеграции бюджета целей с календарём."""

from decimal import Decimal
from typing import Literal, TypedDict

ReservationMode = Literal["fixed_date", "from_balance"]


class BudgetReservationSettings(TypedDict):
    """Настройки режима резервирования бюджета на цели.

    Attributes:
        mode: Режим резервирования.
            "fixed_date" — recurring операция "Резерв на цели" в фиксированный день.
            "from_balance" — взносы создаются как операции при каждом вкладе.
        day_of_month: День месяца для fixed_date режима (1-31), None для from_balance.
        monthly_budget: Ежемесячный бюджет на цели из User.monthly_savings_budget.
        template_id: ID recurring шаблона для fixed_date режима, None для from_balance.
    """

    mode: ReservationMode
    day_of_month: int | None
    monthly_budget: Decimal
    template_id: int | None


class BudgetProgress(TypedDict):
    """Прогресс использования бюджета в текущем месяце.

    Attributes:
        total_budget: Ежемесячный бюджет на цели.
        used_budget: Сумма уже распределённых/внесённых средств.
        available_budget: Оставшийся бюджет (total - used).
        progress_percent: Процент использования (0-100).
        status: Цветовой статус ("success", "warning", "orange", "danger").
        mode: Текущий режим резервирования.
        mode_text: Текст для UI ("Распределено" / "Внесено").
    """

    total_budget: Decimal
    used_budget: Decimal
    available_budget: Decimal
    progress_percent: float
    status: str  # "success" | "warning" | "orange" | "danger"
    mode: ReservationMode
    mode_text: str


class ContributionRecord(TypedDict):
    """Запись о взносе для создания транзакции.

    Используется при создании взноса из режима from_balance.

    Attributes:
        goal_id: ID цели.
        goal_name: Название цели для описания транзакции.
        amount: Сумма взноса.
        date: Дата взноса (ISO format string).
    """

    goal_id: int
    goal_name: str
    amount: Decimal
    date: str  # ISO format
