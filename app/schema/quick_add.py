"""TypedDicts для Quick-add chips."""

from typing import TypedDict


class QuickAddChipData(TypedDict):
    """Данные для Quick-add chip.

    Attributes:
        category_id: ID категории в БД
        name: Название категории ("Еда и продукты")
        icon: Bootstrap иконка ("bi-cart")
        type: Тип транзакции ("expense" | "income")
    """

    category_id: int
    name: str
    icon: str
    type: str
