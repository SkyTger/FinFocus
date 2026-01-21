"""Тесты миграции 001: добавление monthly_savings_budget в users."""
import sqlite3
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, User
from scripts.migrate_001_savings_budget import (
    column_exists,
    migrate_add_savings_budget,
)


@pytest.fixture
def temp_db():
    """Создает временную SQLite базу для тестов миграции."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    # Создаем базовую схему БД (старая версия без monthly_savings_budget)
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    conn = engine.raw_connection()
    cursor = conn.cursor()

    # Создаем таблицу users без monthly_savings_budget
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL,
            starting_balance NUMERIC(10, 2) DEFAULT 0 NOT NULL,
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


def test_migration_adds_column_when_not_exists(temp_db):
    """Тест: миграция добавляет колонку если она не существует."""
    # Проверяем что колонки нет
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    assert not column_exists(cursor, "users", "monthly_savings_budget")
    conn.close()

    # Запускаем миграцию
    migrate_add_savings_budget(temp_db)

    # Проверяем что колонка появилась
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    assert column_exists(cursor, "users", "monthly_savings_budget")
    conn.close()


def test_migration_idempotent(temp_db):
    """Тест: миграция не падает при повторном запуске (idempotent)."""
    # Первый запуск
    migrate_add_savings_budget(temp_db)

    # Второй запуск не должен упасть
    try:
        migrate_add_savings_budget(temp_db)
    except Exception as e:
        pytest.fail(f"Миграция не idempotent: {e}")

    # Проверяем что колонка все еще существует
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    assert column_exists(cursor, "users", "monthly_savings_budget")
    conn.close()


def test_migration_default_value_zero(temp_db):
    """Тест: колонка monthly_savings_budget имеет default value = 0."""
    # Запускаем миграцию
    migrate_add_savings_budget(temp_db)

    # Создаем пользователя без указания monthly_savings_budget
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (email, name, starting_balance)
        VALUES ('test@example.com', 'Test User', 1000.00)
        """
    )
    conn.commit()

    # Проверяем что monthly_savings_budget = 0
    cursor.execute(
        "SELECT monthly_savings_budget FROM users WHERE email = 'test@example.com'"
    )
    result = cursor.fetchone()
    assert result is not None
    assert Decimal(str(result[0])) == Decimal("0")

    conn.close()
