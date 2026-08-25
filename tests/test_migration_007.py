"""Тесты миграции 007: добавление avatar_id в users."""
import sqlite3
import tempfile
from pathlib import Path

import pytest

from app.core.migrations import run_all_migrations


@pytest.fixture
def temp_db_without_avatar_id():
    """Создает временную SQLite базу без колонки avatar_id."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL,
            starting_balance NUMERIC(10, 2) DEFAULT 0 NOT NULL,
            monthly_savings_budget NUMERIC(10, 2) DEFAULT 0 NOT NULL,
            savings_mode VARCHAR(20) DEFAULT 'free' NOT NULL,
            first_launch BOOLEAN DEFAULT 1,
            cushion_target NUMERIC(12, 2) DEFAULT 0,
            cushion_threshold_percent INTEGER DEFAULT 30,
            cushion_threshold_manual BOOLEAN DEFAULT 0,
            reservation_mode TEXT DEFAULT 'from_balance',
            reservation_day INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            icon VARCHAR(30) DEFAULT 'bi-tag',
            type VARCHAR(10) NOT NULL,
            is_system BOOLEAN DEFAULT 0,
            sort_order INTEGER DEFAULT 0
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            transaction_type VARCHAR(30) NOT NULL,
            transaction_date DATE NOT NULL,
            description VARCHAR(500),
            category_id INTEGER,
            is_recurring BOOLEAN DEFAULT 0,
            recurring_period VARCHAR(20),
            recurring_end_date DATE,
            recurring_parent_id INTEGER,
            original_date DATE,
            is_skipped BOOLEAN DEFAULT 0,
            recurring_anchor_eom BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE goals (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name VARCHAR(200) NOT NULL,
            target_amount NUMERIC(10, 2) NOT NULL,
            current_amount NUMERIC(10, 2) DEFAULT 0,
            target_date DATE NOT NULL,
            status VARCHAR(20) DEFAULT 'active',
            priority INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE goal_contributions (
            id INTEGER PRIMARY KEY,
            goal_id INTEGER NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            contribution_date DATE NOT NULL,
            description VARCHAR(500),
            transaction_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        "CREATE INDEX ix_contribution_date ON goal_contributions(contribution_date)"
    )
    cursor.execute(
        """
        CREATE TABLE wishlist_items (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            category_id INTEGER,
            priority INTEGER DEFAULT 1,
            status VARCHAR(20) DEFAULT 'new',
            planned_date DATE,
            planned_transaction_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        "CREATE INDEX ix_wishlist_user_priority ON wishlist_items(user_id, priority)"
    )

    cursor.execute("INSERT INTO users (email, name) VALUES ('test@test.com', 'Test')")
    conn.commit()
    conn.close()

    yield db_path
    db_path.unlink(missing_ok=True)


class TestMigration007:
    """Тесты миграции 007_avatar_id."""

    def test_migration_007_adds_avatar_id_column(self, temp_db_without_avatar_id):
        """Миграция добавляет колонку avatar_id."""
        applied = run_all_migrations(temp_db_without_avatar_id)

        assert "007_avatar_id" in applied

        conn = sqlite3.connect(str(temp_db_without_avatar_id))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        assert "avatar_id" in columns

    def test_migration_007_idempotent(self, temp_db_without_avatar_id):
        """Повторный запуск миграции безопасен."""
        run_all_migrations(temp_db_without_avatar_id)
        applied = run_all_migrations(temp_db_without_avatar_id)

        assert "007_avatar_id" not in applied

    def test_migration_007_default_value(self, temp_db_without_avatar_id):
        """Существующие записи получают default 'emoji-default'."""
        run_all_migrations(temp_db_without_avatar_id)

        conn = sqlite3.connect(str(temp_db_without_avatar_id))
        cursor = conn.cursor()
        cursor.execute("SELECT avatar_id FROM users WHERE email='test@test.com'")
        row = cursor.fetchone()
        conn.close()

        assert row[0] == "emoji-default"
