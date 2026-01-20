"""Сервисный слой приложения."""

from app.core import ValidationError

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
