"""Тесты миграции 002: добавление savings_mode в users."""
import sqlite3
import tempfile
from pathlib import Path

import pytest

from scripts.migrate_002_savings_mode import (
    column_exists,
    migrate_add_savings_mode,
)


@pytest.fixture
def temp_db_without_savings_mode():
    """Создает временную SQLite базу без колонки savings_mode."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    # Создаем схему БД (версия с monthly_savings_budget, но без savings_mode)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Создаем таблицу users без savings_mode
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL,
            starting_balance NUMERIC(10, 2) DEFAULT 0 NOT NULL,
            monthly_savings_budget NUMERIC(10, 2) DEFAULT 0 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


def test_migration_adds_savings_mode_column(temp_db_without_savings_mode):
    """Тест: миграция добавляет колонку savings_mode если она не существует."""
    db_path = temp_db_without_savings_mode

    # Проверяем что колонки нет
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    assert not column_exists(cursor, "users", "savings_mode")
    conn.close()

    # Запускаем миграцию
    migrate_add_savings_mode(db_path)

    # Проверяем что колонка появилась
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    assert column_exists(cursor, "users", "savings_mode")
    conn.close()


def test_migration_idempotent(temp_db_without_savings_mode):
    """Тест: миграция не падает при повторном запуске (idempotent)."""
    db_path = temp_db_without_savings_mode

    # Первый запуск
    migrate_add_savings_mode(db_path)

    # Второй запуск не должен упасть
    try:
        migrate_add_savings_mode(db_path)
    except Exception as e:
        pytest.fail(f"Миграция не idempotent: {e}")

    # Проверяем что колонка все еще существует
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    assert column_exists(cursor, "users", "savings_mode")
    conn.close()


def test_existing_users_get_default_free(temp_db_without_savings_mode):
    """Тест: существующие пользователи получают savings_mode='free'."""
    db_path = temp_db_without_savings_mode

    # Создаем пользователя ДО миграции
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (email, name, starting_balance, monthly_savings_budget)
        VALUES ('existing@example.com', 'Existing User', 1000.00, 5000.00)
        """
    )
    conn.commit()
    conn.close()

    # Запускаем миграцию
    migrate_add_savings_mode(db_path)

    # Проверяем что существующий пользователь получил savings_mode='free'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT savings_mode FROM users WHERE email = 'existing@example.com'"
    )
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == "free"
    conn.close()
