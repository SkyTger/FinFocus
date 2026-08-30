"""
UI компоненты приложения FinFocus.
"""
from app.components.analytics import create_analytics_layout
from app.components.calendar import create_calendar_layout
from app.components.dashboard import create_dashboard_layout
from app.components.goals import create_goals_layout
from app.components.transactions import create_transactions_layout
from app.components.transaction_modals import create_transaction_modals
from app.components.onboarding_wizard import create_onboarding_wizard
from app.components.wishlist import create_wishlist_modal
import app.components.calendar_wishlist  # noqa: F401 — register callbacks

__all__ = [
    "create_analytics_layout",
    "create_calendar_layout",
    "create_dashboard_layout",
    "create_goals_layout",
    "create_transactions_layout",
    "create_transaction_modals",
    "create_onboarding_wizard",
    "create_wishlist_modal",
]
