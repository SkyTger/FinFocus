#!/usr/bin/env python
"""
Миграция 001: Добавление поля monthly_savings_budget в таблицу users.

Этот скрипт добавляет колонку monthly_savings_budget (NUMERIC(10,2), default=0)
в таблицу users для хранения ежемесячного бюджета на накопления.

Использование:
    python scripts/migrate_001_savings_budget.py data/finfocus.db

Idempotent: можно запускать повторно, пропускает если колонка уже существует.
"""
import sqlite3
import sys
from pathlib import Path


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Проверяет существование колонки в таблице через PRAGMA table_info.

    Args:
        cursor: SQLite cursor.
        table: Имя таблицы.
        column: Имя колонки.

    Returns:
        True если колонка существует, иначе False.
    """
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate_add_savings_budget(db_path: str) -> None:
    """Выполняет миграцию: добавляет monthly_savings_budget в users.

    Args:
        db_path: Путь к SQLite базе данных.

    Raises:
        sqlite3.Error: Если миграция не удалась.
    """
    db_file = Path(db_path)
    if not db_file.exists():
        print(f"❌ Ошибка: база данных не найдена: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Проверяем существование колонки
        if column_exists(cursor, "users", "monthly_savings_budget"):
            print("✅ Колонка monthly_savings_budget уже существует. Пропуск.")
            return

        # Добавляем колонку
        print("🔄 Добавление колонки monthly_savings_budget...")
        cursor.execute(
            """
            ALTER TABLE users
            ADD COLUMN monthly_savings_budget NUMERIC(10, 2) DEFAULT 0 NOT NULL
            """
        )
        conn.commit()
        print("✅ Миграция завершена успешно.")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"❌ Ошибка миграции: {e}")
        sys.exit(1)

    finally:
        conn.close()


def main() -> None:
    """Точка входа скрипта."""
    if len(sys.argv) < 2:
        print("Использование: python scripts/migrate_001_savings_budget.py <db_path>")
        print("Пример: python scripts/migrate_001_savings_budget.py data/finfocus.db")
        sys.exit(1)

    db_path = sys.argv[1]
    print(f"🚀 Запуск миграции 001 для базы: {db_path}")
    migrate_add_savings_budget(db_path)


if __name__ == "__main__":
    main()
