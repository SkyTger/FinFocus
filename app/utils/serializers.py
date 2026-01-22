"""Сериализаторы для JSON-совместимости данных."""
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schema.goals import RedistributionPreview


def _convert_decimal_to_str(obj: Any) -> Any:
    """Рекурсивно конвертирует Decimal в str для JSON-совместимости.

    Args:
        obj: Любой объект (Decimal, dict, list или примитив).

    Returns:
        Объект с конвертированными Decimal → str.
    """
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimal_to_str(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimal_to_str(item) for item in obj]
    return obj


def _convert_str_to_decimal(obj: Any, decimal_keys: set[str]) -> Any:
    """Рекурсивно конвертирует str обратно в Decimal для указанных ключей.

    Args:
        obj: Любой объект (dict, list или примитив).
        decimal_keys: Множество ключей, значения которых нужно конвертировать в Decimal.

    Returns:
        Объект с конвертированными str → Decimal для указанных ключей.
    """
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k in decimal_keys and isinstance(v, str):
                try:
                    result[k] = Decimal(v)
                except InvalidOperation:
                    result[k] = v  # Оставляем как есть если невалидный Decimal
            else:
                result[k] = _convert_str_to_decimal(v, decimal_keys)
        return result
    if isinstance(obj, list):
        return [_convert_str_to_decimal(item, decimal_keys) for item in obj]
    return obj


# Ключи, которые содержат Decimal значения в RedistributionPreview и AllocationSummary
_DECIMAL_KEYS = {
    "freed_budget",
    "total_budget",
    "total_allocated",
    "total_needed",
    "total_shortfall",
    "monthly_contribution_needed",
    "allocated_amount",
    "shortfall",
}


def serialize_redistribution_preview(preview: RedistributionPreview) -> dict:
    """Сериализует RedistributionPreview для хранения в dcc.Store.

    Конвертирует Decimal поля в str для JSON-совместимости.
    Рекурсивно обрабатывает вложенные AllocationSummary структуры.

    Args:
        preview: RedistributionPreview TypedDict.

    Returns:
        JSON-совместимый dict.
    """
    return _convert_decimal_to_str(dict(preview))


def deserialize_redistribution_preview(data: dict | None) -> RedistributionPreview | None:
    """Десериализует данные из dcc.Store обратно в RedistributionPreview.

    Конвертирует str обратно в Decimal для известных числовых полей.
    Восстанавливает типы для вложенных AllocationSummary структур.

    Args:
        data: JSON-данные из dcc.Store или None.

    Returns:
        RedistributionPreview TypedDict или None если входные данные None.
    """
    if data is None:
        return None

    return _convert_str_to_decimal(data, _DECIMAL_KEYS)


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
