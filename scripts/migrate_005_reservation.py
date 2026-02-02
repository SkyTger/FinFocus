"""Миграция: режим резервирования и связь взносов с транзакциями.

Добавляет:
- users.reservation_mode (default: "from_balance")
- users.reservation_day (nullable)
- goal_contributions.transaction_id (FK, nullable)
- Index ix_contribution_date

Idempotent: проверяет PRAGMA table_info перед ALTER.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "finfocus.db"


def get_columns(cursor, table: str) -> set[str]:
    """Возвращает множество имён колонок таблицы."""
    cursor.execute(f"PRAGMA table_info({table})")
    return {col[1] for col in cursor.fetchall()}


def get_indexes(cursor, table: str) -> set[str]:
    """Возвращает множество имён индексов таблицы."""
    cursor.execute(f"PRAGMA index_list({table})")
    return {idx[1] for idx in cursor.fetchall()}


def migrate():
    """Выполняет миграцию."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    changes = []

    # === Users table ===
    user_cols = get_columns(cursor, "users")

    if "reservation_mode" not in user_cols:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN reservation_mode TEXT DEFAULT 'from_balance'"
        )
        changes.append("users.reservation_mode")

    if "reservation_day" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN reservation_day INTEGER")
        changes.append("users.reservation_day")

    # === GoalContributions table ===
    contrib_cols = get_columns(cursor, "goal_contributions")

    if "transaction_id" not in contrib_cols:
        cursor.execute(
            "ALTER TABLE goal_contributions ADD COLUMN transaction_id INTEGER "
            "REFERENCES transactions(id) ON DELETE SET NULL"
        )
        changes.append("goal_contributions.transaction_id")

    # === Index ===
    contrib_indexes = get_indexes(cursor, "goal_contributions")

    if "ix_contribution_date" not in contrib_indexes:
        cursor.execute(
            "CREATE INDEX ix_contribution_date ON goal_contributions(contribution_date)"
        )
        changes.append("ix_contribution_date index")

    conn.commit()
    conn.close()

    if changes:
        print(f"Migration complete: {', '.join(changes)}")
    else:
        print("All columns/indexes already exist, skipping")


if __name__ == "__main__":
    migrate()
