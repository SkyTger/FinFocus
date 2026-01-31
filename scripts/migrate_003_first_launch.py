"""Миграция: добавление колонки first_launch в таблицу users.

Логика:
- Если starting_balance != 0 → first_launch = False (уже настроен)
- Если starting_balance == 0 → first_launch = True (нужен онбординг)
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "finfocus.db"


def migrate():
    """Добавляет колонку first_launch в таблицу users."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем существование колонки
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if "first_launch" not in columns:
        # Добавляем колонку с default=True
        cursor.execute("ALTER TABLE users ADD COLUMN first_launch BOOLEAN DEFAULT 1")

        # Обновляем для пользователей с настроенным балансом
        cursor.execute(
            """
            UPDATE users
            SET first_launch = 0
            WHERE starting_balance != 0
        """
        )

        conn.commit()
        print("Migration complete: first_launch added to users table")
    else:
        print("Column first_launch already exists, skipping")

    conn.close()


if __name__ == "__main__":
    migrate()
