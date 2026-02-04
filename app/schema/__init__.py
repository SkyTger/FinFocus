"""Централизованные типы данных для FinFocus."""
from app.schema.analytics import (
    CategorySummary,
    MonthlyTrend,
)
from app.schema.goals import (
    AllocationResult,
    AllocationSummary,
    ContributionInfo,
    ContributionUpdateResult,
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
from app.schema.onboarding import OnboardingStatus
from app.schema.recurring import (
    RecurringDeleteContext,
    DELETE_SCOPE_OPTIONS,
)
from app.schema.budget_reservation import (
    ReservationMode,
    BudgetReservationSettings,
    BudgetProgress,
    ContributionRecord,
)
from app.schema.wishlist import (
    WishlistItemData,
    SafeDateInfo,
    HoverBalances,
)

__all__ = [
    # Analytics
    "CategorySummary",
    "MonthlyTrend",
    # Goals
    "AllocationResult",
    "AllocationSummary",
    "ContributionInfo",
    "ContributionUpdateResult",
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
    # Onboarding
    "OnboardingStatus",
    # Recurring
    "RecurringDeleteContext",
    "DELETE_SCOPE_OPTIONS",
    # Budget Reservation
    "ReservationMode",
    "BudgetReservationSettings",
    "BudgetProgress",
    "ContributionRecord",
    # Wishlist
    "WishlistItemData",
    "SafeDateInfo",
    "HoverBalances",
]
