"""TypedDicts для онбординга."""
from decimal import Decimal
from typing import TypedDict


class OnboardingStatus(TypedDict):
    """Статус онбординга пользователя."""

    first_launch: bool
    starting_balance: Decimal
    needs_balance_alert: bool  # True если starting_balance == 0
