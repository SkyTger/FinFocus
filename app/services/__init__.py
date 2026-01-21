"""Сервисный слой приложения."""

from app.core import ValidationError
from app.types.goals import (
    AllocationResult,
    AllocationSummary,
    GoalDisplayData,
    GoalsSummary,
)

from .allocation_service import AllocationService
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
from .goal_service import GoalService
from .recurring_service import (
    MAX_FORECAST_DAYS,
    MAX_INSTANCES_PER_CALL,
    VALID_RECURRING_PERIODS,
    RecurringService,
    VirtualTransaction,
)
from .transaction_service import TransactionService

__all__ = [
    # Allocation
    "AllocationService",
    "AllocationResult",
    "AllocationSummary",
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
    # Transactions
    "TransactionService",
    # Recurring
    "RecurringService",
    "VirtualTransaction",
    "MAX_INSTANCES_PER_CALL",
    "MAX_FORECAST_DAYS",
    "VALID_RECURRING_PERIODS",
    # Core
    "ValidationError",
]
