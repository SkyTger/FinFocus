"""TypedDicts для финансовой подушки безопасности."""

from decimal import Decimal
from typing import NewType, TypedDict

Percent = NewType("Percent", int)


class CushionSettings(TypedDict):
    """Настройки и состояние подушки безопасности.

    Attributes:
        target: Целевой размер подушки в валюте.
        threshold_percent: Процент заполнения (0-100) для предупреждений.
        threshold_amount: Вычисленная сумма порога (target * threshold_percent / 100).
        threshold_manual: True если порог задан вручную, False если по проценту.
        current_amount: Текущий накопленный размер подушки.
        progress: Прогресс заполнения в процентах (0-100).
        is_configured: True если пользователь настроил подушку.
    """

    target: Decimal
    threshold_percent: Percent  # 0-100
    threshold_amount: Decimal  # computed
    threshold_manual: bool
    current_amount: Decimal
    progress: float  # 0-100
    is_configured: bool


class CushionScenario(TypedDict):
    """Сценарий расчета целевого размера подушки.

    Используется для UI с подсказками: "Минимальный" (3 мес),
    "Рекомендуемый" (6 мес), "Консервативный" (12 мес).

    Attributes:
        name: Название сценария.
        min_amount: Минимальная сумма для сценария.
        max_amount: Максимальная сумма для сценария.
    """

    name: str
    min_amount: Decimal
    max_amount: Decimal
