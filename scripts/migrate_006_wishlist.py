"""Миграция: таблица wishlist_items для отложенных покупок.

Добавляет:
- Таблица wishlist_items (CREATE TABLE IF NOT EXISTS)
- Index ix_wishlist_user_priority

Idempotent: проверяет существование таблицы перед CREATE.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "finfocus.db"


def get_tables(cursor) -> set[str]:
    """Возвращает множество имён таблиц в БД."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cursor.fetchall()}


def get_indexes(cursor, table: str) -> set[str]:
    """Возвращает множество имён индексов таблицы."""
    cursor.execute(f"PRAGMA index_list({table})")
    return {idx[1] for idx in cursor.fetchall()}


def migrate():
    """Выполняет миграцию."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    changes = []

    tables = get_tables(cursor)

    if "wishlist_items" not in tables:
        cursor.execute("""
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
        """)
        changes.append("wishlist_items table")

    # Index
    indexes = get_indexes(cursor, "wishlist_items") if "wishlist_items" in get_tables(cursor) else set()

    if "ix_wishlist_user_priority" not in indexes:
        cursor.execute(
            "CREATE INDEX ix_wishlist_user_priority "
            "ON wishlist_items(user_id, priority)"
        )
        changes.append("ix_wishlist_user_priority index")

    conn.commit()
    conn.close()

    if changes:
        print(f"Migration complete: {', '.join(changes)}")
    else:
        print("Table wishlist_items already exists, skipping")


if __name__ == "__main__":
    migrate()
