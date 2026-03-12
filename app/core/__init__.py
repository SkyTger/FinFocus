"""Core модуль приложения — инфраструктурные компоненты."""

from .logging import setup_logging, logger
from .database import get_db_session, get_engine, init_database
from .exceptions import ValidationError
from .migrations import run_all_migrations
from .bootstrap import auto_bootstrap
from .paths import (
    get_app_dir,
    get_bundle_dir,
    get_data_dir,
    get_logs_dir,
    get_assets_dir,
)

__all__ = [
    "setup_logging",
    "logger",
    "get_db_session",
    "get_engine",
    "init_database",
    "run_all_migrations",
    "auto_bootstrap",
    "ValidationError",
    "get_app_dir",
    "get_bundle_dir",
    "get_data_dir",
    "get_logs_dir",
    "get_assets_dir",
]
