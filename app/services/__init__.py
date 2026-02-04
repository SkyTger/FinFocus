"""Сервисный слой приложения."""

from app.core import ValidationError
from app.schema.goals import (
    AllocationResult,
    AllocationSummary,
    GoalDisplayData,
    GoalsSummary,
)

from .allocation_service import AllocationService
from .analytics_service import AnalyticsService, MIN_PERCENTAGE_THRESHOLD
from .category_service import CategoryService, MIN_TRANSACTIONS_FOR_FREQUENCY
from .calendar_service import (
    CalendarService,
    MonthSummary,
    TransactionInfo,
    YearSummary,
)
from .dashboard_service import (
    CashflowDataPoint,
    DashboardService,
    OverviewMetrics,
    PeriodType,
    RecentTransaction,
)
from .goal_service import GoalService, VALID_SAVINGS_MODES
from .recurring_service import (
    MAX_FORECAST_DAYS,
    MAX_INSTANCES_PER_CALL,
    VALID_RECURRING_PERIODS,
    RecurringService,
    VirtualTransaction,
)
from .reconciliation_service import ReconciliationService
from .redistribution_service import (
    NFR2_WARNING_THRESHOLD_MS,
    RedistributionService,
)
from .transaction_service import MAX_BULK_UPDATE_SIZE, TransactionService
from .cushion_service import (
    CushionService,
    DEFAULT_THRESHOLD_PERCENT,
    VALID_CALC_MODES,
    _validate_percent,
)
from .onboarding_service import OnboardingService
from .budget_reservation_service import (
    BudgetReservationService,
    RESERVE_DESCRIPTION,
    STATUS_THRESHOLDS,
)
from .wishlist_service import WishlistService, VALID_PRIORITIES

__all__ = [
    # Allocation
    "AllocationService",
    "AllocationResult",
    "AllocationSummary",
    # Analytics
    "AnalyticsService",
    "MIN_PERCENTAGE_THRESHOLD",
    # Category
    "CategoryService",
    "MIN_TRANSACTIONS_FOR_FREQUENCY",
    # Calendar
    "CalendarService",
    "MonthSummary",
    "TransactionInfo",
    "YearSummary",
    # Dashboard
    "CashflowDataPoint",
    "DashboardService",
    "OverviewMetrics",
    "PeriodType",
    "RecentTransaction",
    # Goals
    "GoalService",
    "GoalDisplayData",
    "GoalsSummary",
    "VALID_SAVINGS_MODES",
    # Transactions
    "TransactionService",
    "MAX_BULK_UPDATE_SIZE",
    # Recurring
    "RecurringService",
    "VirtualTransaction",
    "MAX_INSTANCES_PER_CALL",
    "MAX_FORECAST_DAYS",
    "VALID_RECURRING_PERIODS",
    # Reconciliation
    "ReconciliationService",
    # Redistribution
    "RedistributionService",
    "NFR2_WARNING_THRESHOLD_MS",
    # Cushion
    "CushionService",
    "DEFAULT_THRESHOLD_PERCENT",
    "VALID_CALC_MODES",
    "_validate_percent",
    # Onboarding
    "OnboardingService",
    # Budget Reservation
    "BudgetReservationService",
    "RESERVE_DESCRIPTION",
    "STATUS_THRESHOLDS",
    # Wishlist
    "WishlistService",
    "VALID_PRIORITIES",
    # Core
    "ValidationError",
]
