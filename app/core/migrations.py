"""Автоматический запуск всех миграций БД.

Вызывается из run.py при старте приложения.
Все миграции идемпотентны — безопасно при повторных запусках.
"""

import sqlite3
from pathlib import Path

from loguru import logger

DB_PATH = Path("data/finfocus.db")


def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Проверяет существование колонки в таблице."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    """Проверяет существование таблицы."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    return table in tables


def _index_exists(cursor: sqlite3.Cursor, table: str, index_name: str) -> bool:
    """Проверяет существование индекса."""
    cursor.execute(f"PRAGMA index_list({table})")
    indexes = {idx[1] for idx in cursor.fetchall()}
    return index_name in indexes


def run_all_migrations(db_path: Path | None = None) -> list[str]:
    """Запускает все миграции последовательно.

    Args:
        db_path: Путь к БД. По умолчанию data/finfocus.db.

    Returns:
        Список применённых миграций.
    """
    path = str(db_path or DB_PATH)
    if not Path(path).exists():
        logger.debug(
            "БД не найдена, миграции не требуются (init_database создаст схему)"
        )
        return []

    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    applied: list[str] = []

    try:
        # 001: monthly_savings_budget
        if not _column_exists(cursor, "users", "monthly_savings_budget"):
            cursor.execute(
                "ALTER TABLE users "
                "ADD COLUMN monthly_savings_budget NUMERIC(10, 2) DEFAULT 0 NOT NULL"
            )
            applied.append("001_savings_budget")

        # 002: savings_mode
        if not _column_exists(cursor, "users", "savings_mode"):
            cursor.execute(
                "ALTER TABLE users "
                "ADD COLUMN savings_mode VARCHAR(20) DEFAULT 'free' NOT NULL"
            )
            applied.append("002_savings_mode")

        # 003: first_launch
        if not _column_exists(cursor, "users", "first_launch"):
            cursor.execute(
                "ALTER TABLE users ADD COLUMN first_launch BOOLEAN DEFAULT 1"
            )
            cursor.execute(
                "UPDATE users SET first_launch = 0 WHERE starting_balance != 0"
            )
            applied.append("003_first_launch")

        # 004: recurring_anchor_eom
        if not _column_exists(cursor, "transactions", "recurring_anchor_eom"):
            cursor.execute(
                "ALTER TABLE transactions "
                "ADD COLUMN recurring_anchor_eom BOOLEAN DEFAULT 0 NOT NULL"
            )
            applied.append("004_recurring_anchor_eom")

        # 005: reservation fields + contribution.transaction_id
        user_cols = {
            row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()
        }
        if "reservation_mode" not in user_cols:
            cursor.execute(
                "ALTER TABLE users "
                "ADD COLUMN reservation_mode TEXT DEFAULT 'from_balance'"
            )
            applied.append("005_reservation_mode")

        if "reservation_day" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN reservation_day INTEGER")
            applied.append("005_reservation_day")

        contrib_cols = {
            row[1]
            for row in cursor.execute(
                "PRAGMA table_info(goal_contributions)"
            ).fetchall()
        }
        if "transaction_id" not in contrib_cols:
            cursor.execute(
                "ALTER TABLE goal_contributions ADD COLUMN transaction_id INTEGER "
                "REFERENCES transactions(id) ON DELETE SET NULL"
            )
            applied.append("005_contribution_transaction_id")

        if not _index_exists(cursor, "goal_contributions", "ix_contribution_date"):
            cursor.execute(
                "CREATE INDEX ix_contribution_date "
                "ON goal_contributions(contribution_date)"
            )
            applied.append("005_ix_contribution_date")

        # 006: wishlist_items
        if not _table_exists(cursor, "wishlist_items"):
            cursor.execute(
                """
                CREATE TABLE wishlist_items (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    name VARCHAR(100) NOT NULL,
                    amount NUMERIC(10, 2) NOT NULL,
                    category_id INTEGER REFERENCES categories(id),
                    priority INTEGER DEFAULT 1,
                    status VARCHAR(20) NOT NULL DEFAULT 'new',
                    planned_date DATE,
                    planned_transaction_id INTEGER
                        REFERENCES transactions(id) ON DELETE SET NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            applied.append("006_wishlist_table")

        if _table_exists(cursor, "wishlist_items") and not _index_exists(
            cursor, "wishlist_items", "ix_wishlist_user_priority"
        ):
            cursor.execute(
                "CREATE INDEX ix_wishlist_user_priority "
                "ON wishlist_items(user_id, priority)"
            )
            applied.append("006_ix_wishlist_user_priority")

        conn.commit()

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Ошибка миграции: {e}")
        raise

    finally:
        conn.close()

    if applied:
        logger.info(f"Применены миграции: {', '.join(applied)}")
    else:
        logger.debug("Все миграции уже применены")

    return applied
