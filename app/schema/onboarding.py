"""TypedDicts для онбординга."""
from decimal import Decimal
from typing import TypedDict


class UserProfile(TypedDict):
    """Профиль пользователя."""

    name: str
    avatar_id: str


class OnboardingStatus(TypedDict):
    """Статус онбординга пользователя."""

    first_launch: bool
    starting_balance: Decimal
    needs_balance_alert: bool  # True если starting_balance == 0
    name: str
    avatar_id: str
