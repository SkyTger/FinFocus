"""TypedDicts для типизации данных категорий и сверки.

Централизованные типы для переиспользования между services и UI.
Все Decimal-значения представлены как строки для JSON-совместимости (dcc.Store).
"""

from typing import TypedDict


class CategoryOption(TypedDict):
    """Опция категории для dropdown в UI.

    Используется для передачи данных из CategoryService в callbacks.
    """

    label: str  # "Еда и продукты"
    value: int  # category_id
    icon: str  # "bi-cart"


class ReconciliationPreview(TypedDict):
    """Предпросмотр сверки для модала.

    Все Decimal конвертируются в строки для JSON-совместимости (dcc.Store).
    """

    expected_balance: str  # "15000.00" — расчетный баланс из CalendarService
    actual_balance: str  # "14200.00" — фактический баланс (user input)
    difference: str  # "-800.00" — разница (actual - expected)
    is_positive: bool  # False если difference < 0
    target_date: str  # "2026-01-22" — дата сверки (ISO format)
    explanation: str  # "Будет создана корректировка на -800 ₽"
