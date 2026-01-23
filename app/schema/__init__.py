"""Централизованные типы данных для FinFocus."""
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

__all__ = [
    "AllocationResult",
    "AllocationSummary",
    "GoalDisplayData",
    "GoalsSummary",
    "RedistributionEvent",
    "RedistributionPreview",
    "CategoryOption",
    "ReconciliationPreview",
]
