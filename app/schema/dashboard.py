"""TypedDicts для дашборда: дневной и годовой cashflow.

Содержит типы данных для дневного графика cashflow (grouped bars + balance line)
и годового режима (monthly bars + end-of-month balance).
"""
from datetime import date
from decimal import Decimal
from typing import Literal, TypedDict


# --- Пороги баланса для цветовой индикации ---

BalanceStatus = Literal["ok", "attention", "risk"]
"""Статус баланса: ok (зелёный), attention (жёлтый), risk (красный)."""

BALANCE_RISK_THRESHOLD = Decimal("0")
"""Баланс <= 0 — критический риск."""

BALANCE_ATTENTION_THRESHOLD = Decimal("5000")
"""Баланс < 5000 — требует внимания."""


# --- Дневной cashflow (Month mode) ---


class DailyCashflow(TypedDict):
    """Данные cashflow за один день.

    Attributes:
        date: Дата дня.
        income: Сумма доходов за день.
        expense: Сумма расходов за день (положительное число).
        balance: Остаток на конец дня.
    """

    date: date
    income: Decimal
    expense: Decimal
    balance: Decimal


class DailyBalancePoint(TypedDict):
    """Точка баланса с цветовым статусом для маркера минимума.

    Attributes:
        date: Дата точки.
        balance: Остаток на конец дня.
        status: Цветовой статус (ok/attention/risk).
    """

    date: date
    balance: Decimal
    status: BalanceStatus


class MonthlyCashflowData(TypedDict):
    """Полный набор данных для дневного графика (Month mode).

    Attributes:
        daily: Список DailyCashflow за каждый день месяца.
        min_balance_point: День с минимальным балансом (для маркера).
        current_date: Текущая дата (для разделителя факт/прогноз).
    """

    daily: list[DailyCashflow]
    min_balance_point: DailyBalancePoint
    current_date: date


# --- Годовой cashflow (Year mode) ---


class MonthlyCashflow(TypedDict):
    """Данные cashflow за один месяц (для Year mode).

    Attributes:
        month: Номер месяца (1-12).
        label: Короткое название (Янв, Фев, ...).
        income: Сумма доходов за месяц.
        expense: Сумма расходов за месяц (положительное число).
        end_balance: Остаток на конец месяца.
    """

    month: int
    label: str
    income: Decimal
    expense: Decimal
    end_balance: Decimal


class YearlyCashflowData(TypedDict):
    """Полный набор данных для годового графика (Year mode).

    Attributes:
        monthly: Список MonthlyCashflow за каждый месяц года.
        min_balance_point: Месяц с минимальным end_balance (для маркера).
        current_date: Текущая дата (для разделителя факт/прогноз).
        year: Год данных.
    """

    monthly: list[MonthlyCashflow]
    min_balance_point: DailyBalancePoint
    current_date: date
    year: int
