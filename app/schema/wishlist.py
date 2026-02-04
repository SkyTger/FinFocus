"""Типы данных для функциональности Wishlist (отложенные покупки)."""

from typing import TypedDict


class WishlistItemData(TypedDict):
    """Данные элемента списка покупок для UI."""

    id: int
    name: str
    amount: str  # Форматированная строка для отображения
    category_id: int | None
    category_name: str | None
    category_icon: str | None
    priority: int  # 1 = фокус, 2 = обычная
    status: str  # "new" | "planned"
    planned_date: str | None  # ISO format
    planned_transaction_id: int | None


class SafeDateInfo(TypedDict):
    """Информация о безопасности даты для покупки."""

    safe: bool
    reasons: list[str]  # "negative_balance", "cushion"


class HoverBalances(TypedDict):
    """Предрассчитанные балансы для JS hover в календаре."""

    base_balances: dict[str, str]  # date_iso -> balance_str
    by_candidate: dict[str, dict[str, str]]  # candidate_date_iso -> {day_iso: balance_str}
