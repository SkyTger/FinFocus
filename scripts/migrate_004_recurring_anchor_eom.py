"""Миграция: добавление колонки recurring_anchor_eom в таблицу transactions.

Логика:
- Колонка Boolean, default=False
- Для существующих шаблонов оставляем False (Anchored-алгоритм)
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "finfocus.db"


def migrate():
    """Добавляет колонку recurring_anchor_eom в таблицу transactions."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем существование колонки
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [col[1] for col in cursor.fetchall()]

    if "recurring_anchor_eom" not in columns:
        # Добавляем колонку с default=False (0)
        cursor.execute(
            "ALTER TABLE transactions ADD COLUMN recurring_anchor_eom BOOLEAN DEFAULT 0 NOT NULL"
        )
        conn.commit()
        print("Migration complete: recurring_anchor_eom added to transactions table")
    else:
        print("Column recurring_anchor_eom already exists, skipping")

    conn.close()


if __name__ == "__main__":
    migrate()
