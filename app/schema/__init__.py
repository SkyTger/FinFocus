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
from app.schema.onboarding import OnboardingStatus, UserProfile
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
from app.schema.dashboard import (
    BalanceStatus,
    BALANCE_RISK_THRESHOLD,
    BALANCE_ATTENTION_THRESHOLD,
    DailyCashflow,
    DailyBalancePoint,
    MonthlyCashflowData,
    MonthlyCashflow,
    YearlyCashflowData,
)

from app.schema.panel import (
    OPERATIONS_PER_GROUP,
    MINI_STRUCTURE_CATEGORIES,
    TRANSACTION_KIND_MAP,
    CardStatus,
    CalendarDaySlice,
    CalendarCardData,
    GoalsCardData,
    OperationRow,
    OperationsCardData,
    AnalyticsCategorySlice,
    AnalyticsCardData,
    WishlistCardRow,
    WishlistCardData,
    PanelData,
)

from app.schema.money_layers import (
    LayerKey,
    WINDOW_DAYS,
    MAX_MILESTONES_IN_WINDOW,
    MAX_X_TICKS,
    LAYER_COLORS,
    LAYER_LABELS,
    Horizons,
    DayLayers,
    UpcomingPayment,
    GoalMilestone,
    TodaySlice,
    MoneyLayersData,
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
    # Onboarding / Profile
    "OnboardingStatus",
    "UserProfile",
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
    # Dashboard cashflow
    "BalanceStatus",
    "BALANCE_RISK_THRESHOLD",
    "BALANCE_ATTENTION_THRESHOLD",
    "DailyCashflow",
    "DailyBalancePoint",
    "MonthlyCashflowData",
    "MonthlyCashflow",
    "YearlyCashflowData",
    # Panel cards (EPIC-11, кусок 2)
    "OPERATIONS_PER_GROUP",
    "MINI_STRUCTURE_CATEGORIES",
    "TRANSACTION_KIND_MAP",
    "CardStatus",
    "CalendarDaySlice",
    "CalendarCardData",
    "GoalsCardData",
    "OperationRow",
    "OperationsCardData",
    "AnalyticsCategorySlice",
    "AnalyticsCardData",
    "WishlistCardRow",
    "WishlistCardData",
    "PanelData",
    # Money layers (EPIC-11, кусок 1)
    "LayerKey",
    "WINDOW_DAYS",
    "MAX_MILESTONES_IN_WINDOW",
    "MAX_X_TICKS",
    "LAYER_COLORS",
    "LAYER_LABELS",
    "Horizons",
    "DayLayers",
    "UpcomingPayment",
    "GoalMilestone",
    "TodaySlice",
    "MoneyLayersData",
]
