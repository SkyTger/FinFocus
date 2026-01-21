#!/usr/bin/env python
"""
Миграция 002: Добавление поля savings_mode в таблицу users.

Этот скрипт добавляет колонку savings_mode (VARCHAR(20), default='free')
в таблицу users для хранения режима накоплений.

Допустимые значения: "free", "medium", "strict"
Валидация выполняется на уровне сервиса (GoalService.update_savings_mode).

Использование:
    python scripts/migrate_002_savings_mode.py data/finfocus.db

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


def migrate_add_savings_mode(db_path: str) -> None:
    """Выполняет миграцию: добавляет savings_mode в users.

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
        if column_exists(cursor, "users", "savings_mode"):
            print("✅ Колонка savings_mode уже существует. Пропуск.")
            return

        # Добавляем колонку
        print("🔄 Добавление колонки savings_mode...")
        cursor.execute(
            """
            ALTER TABLE users
            ADD COLUMN savings_mode VARCHAR(20) DEFAULT 'free' NOT NULL
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
        print("Использование: python scripts/migrate_002_savings_mode.py <db_path>")
        print("Пример: python scripts/migrate_002_savings_mode.py data/finfocus.db")
        sys.exit(1)

    db_path = sys.argv[1]
    print(f"🚀 Запуск миграции 002 для базы: {db_path}")
    migrate_add_savings_mode(db_path)


if __name__ == "__main__":
    main()
