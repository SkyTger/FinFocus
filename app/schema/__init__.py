"""Централизованные типы данных для FinFocus."""
from app.schema.analytics import (
    CategorySummary,
    MonthlyTrend,
)
from app.schema.goals import (
    AllocationResult,
    AllocationSummary,
    GoalDisplayData,
    GoalsSummary,
    RedistributionEvent,
    RedistributionPreview,
)
from app.schema.categories import (
    CategoryOption,
    ReconciliationPreview,
)
from app.schema.quick_add import QuickAddChipData
from app.schema.cushion import (
    Percent,
    CushionSettings,
    CushionScenario,
)

__all__ = [
    # Analytics
    "CategorySummary",
    "MonthlyTrend",
    # Goals
    "AllocationResult",
    "AllocationSummary",
    "GoalDisplayData",
    "GoalsSummary",
    "RedistributionEvent",
    "RedistributionPreview",
    # Categories
    "CategoryOption",
    "ReconciliationPreview",
    # Quick-add
    "QuickAddChipData",
    # Cushion
    "Percent",
    "CushionSettings",
    "CushionScenario",
]
