"""TypedDicts для аналитического модуля.

Содержит типы данных для агрегации расходов по категориям
и построения графиков (donut chart, bar chart).
"""
from decimal import Decimal
from typing import TypedDict


class CategorySummary(TypedDict):
    """Агрегация по категории для donut chart.

    Attributes:
        category_id: ID категории (None = "Без категории" или "Прочее").
        category_name: Название категории для UI.
        category_icon: Bootstrap icon класс (bi-cart, etc.) или emoji для "Прочее".
        total: Общая сумма расходов по категории.
        percentage: Процент от общей суммы (0-100).
        count: Количество транзакций в категории.
    """

    category_id: int | None
    category_name: str
    category_icon: str | None
    total: Decimal
    percentage: float
    count: int


class MonthlyTrend(TypedDict):
    """Данные за месяц для bar chart трендов.

    Attributes:
        month: Месяц в формате ISO "YYYY-MM".
        month_label: Сокращенное название на русском (Янв, Фев, ...).
        categories: Список агрегаций по категориям за месяц.
        total: Общая сумма расходов за месяц.
    """

    month: str  # "2026-01"
    month_label: str  # "Янв"
    categories: list[CategorySummary]
    total: Decimal
