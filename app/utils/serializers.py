"""Сериализаторы для JSON-совместимости данных."""
from decimal import Decimal
from typing import Any


def serialize_allocation_summary(summary: dict | None) -> dict | None:
    """Сериализует AllocationSummary для хранения в dcc.Store.

    Конвертирует Decimal поля в float для JSON-совместимости.

    Note: float conversion is acceptable for MVP (sums < 10^15,
    precision ~15-16 digits). For production with larger sums or
    high-precision requirements, consider using str().

    Args:
        summary: AllocationSummary TypedDict или None

    Returns:
        JSON-совместимый dict или None
    """
    if summary is None:
        return None

    def convert_decimal(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, dict):
            return {k: convert_decimal(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert_decimal(item) for item in obj]
        return obj

    return convert_decimal(summary)
