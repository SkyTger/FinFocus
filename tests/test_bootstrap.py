"""Тесты для auto-bootstrap и миграций."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.bootstrap import auto_bootstrap
from app.core.migrations import run_all_migrations
from app.models.database import Base, User, Category


# --- Тесты auto_bootstrap ---


class TestAutoBootstrap:
    """Тесты автоинициализации пользователя и категорий."""

    def test_creates_user_on_empty_db(self, db_engine):
        """auto_bootstrap создаёт User(id=1) если таблица пустая."""
        Session = sessionmaker(bind=db_engine)

        with patch("app.core.bootstrap.get_db_session") as mock_ctx:
            session = Session()
            mock_ctx.return_value.__enter__ = lambda s: session
            mock_ctx.return_value.__exit__ = lambda s, *a: session.close()

            result = auto_bootstrap()

        session2 = Session()
        users = session2.query(User).all()
        session2.close()

        assert result["user_created"] is True
        assert len(users) == 1
        assert users[0].name == "Пользователь"
        assert users[0].email == "user@local"
        assert users[0].first_launch is True

    def test_seeds_categories_on_empty_db(self, db_engine):
        """auto_bootstrap сидит категории если таблица пустая."""
        Session = sessionmaker(bind=db_engine)

        with patch("app.core.bootstrap.get_db_session") as mock_ctx:
            session = Session()
            mock_ctx.return_value.__enter__ = lambda s: session
            mock_ctx.return_value.__exit__ = lambda s, *a: session.close()

            result = auto_bootstrap()

        session2 = Session()
        count = session2.query(Category).count()
        session2.close()

        assert result["categories_seeded"] is True
        assert count >= 16

    def test_skips_user_if_already_exists(self, db_session, test_user):
        """auto_bootstrap не создаёт дубликат если User уже есть."""
        assert db_session.query(User).count() == 1

        with patch("app.core.bootstrap.get_db_session") as mock_ctx:
            mock_ctx.return_value.__enter__ = lambda s: db_session
            mock_ctx.return_value.__exit__ = lambda s, *a: None

            result = auto_bootstrap()

        assert result["user_created"] is False
        assert db_session.query(User).count() == 1

    def test_skips_categories_if_already_exist(self, db_session):
        """auto_bootstrap не дублирует категории при повторном вызове."""
        with patch("app.core.bootstrap.get_db_session") as mock_ctx:
            mock_ctx.return_value.__enter__ = lambda s: db_session
            mock_ctx.return_value.__exit__ = lambda s, *a: None
            auto_bootstrap()

        first_count = db_session.query(Category).count()

        with patch("app.core.bootstrap.get_db_session") as mock_ctx:
            mock_ctx.return_value.__enter__ = lambda s: db_session
            mock_ctx.return_value.__exit__ = lambda s, *a: None
            result = auto_bootstrap()

        assert result["categories_seeded"] is False
        assert db_session.query(Category).count() == first_count

    def test_returns_both_false_when_data_exists(self, db_session, test_user):
        """auto_bootstrap возвращает False для обоих если данные уже есть."""
        from app.services.category_service import CategoryService

        CategoryService(db_session).seed_default_categories()
        db_session.commit()

        with patch("app.core.bootstrap.get_db_session") as mock_ctx:
            mock_ctx.return_value.__enter__ = lambda s: db_session
            mock_ctx.return_value.__exit__ = lambda s, *a: None
            result = auto_bootstrap()

        assert result == {"user_created": False, "categories_seeded": False}


# --- Тесты миграций ---


@pytest.fixture
def legacy_db():
    """Создаёт временную БД с минимальной 'старой' схемой (без полей миграций)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            starting_balance NUMERIC(10, 2) DEFAULT 0 NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            amount NUMERIC(10, 2) NOT NULL,
            transaction_type VARCHAR(20) NOT NULL,
            transaction_date DATE NOT NULL,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE goals (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name VARCHAR(100) NOT NULL,
            target_amount NUMERIC(12, 2) NOT NULL
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE goal_contributions (
            id INTEGER PRIMARY KEY,
            goal_id INTEGER NOT NULL REFERENCES goals(id),
            amount NUMERIC(10, 2) NOT NULL,
            contribution_date DATE NOT NULL
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY,
            name VARCHAR(50) NOT NULL
        )
    """
    )

    # Тестовый пользователь с ненулевым балансом
    cursor.execute(
        "INSERT INTO users (id, email, name, starting_balance) "
        "VALUES (1, 'test@local', 'Тест', 5000)"
    )

    conn.commit()
    conn.close()

    yield db_path

    db_path.unlink(missing_ok=True)


class TestMigrations:
    """Тесты автоматического запуска миграций."""

    def test_all_migrations_applied(self, legacy_db):
        """Все миграции применяются к старой схеме."""
        applied = run_all_migrations(legacy_db)

        assert "001_savings_budget" in applied
        assert "002_savings_mode" in applied
        assert "003_first_launch" in applied
        assert "004_recurring_anchor_eom" in applied
        assert "006_wishlist_table" in applied

    def test_idempotent_second_run(self, legacy_db):
        """Повторный запуск не применяет миграции."""
        run_all_migrations(legacy_db)
        applied = run_all_migrations(legacy_db)

        assert applied == []

    def test_migration_001_adds_savings_budget(self, legacy_db):
        """Миграция 001 добавляет monthly_savings_budget."""
        run_all_migrations(legacy_db)

        conn = sqlite3.connect(str(legacy_db))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        assert "monthly_savings_budget" in columns

    def test_migration_003_sets_first_launch_false_for_existing_user(self, legacy_db):
        """Миграция 003 ставит first_launch=False для users с ненулевым балансом."""
        run_all_migrations(legacy_db)

        conn = sqlite3.connect(str(legacy_db))
        cursor = conn.cursor()
        cursor.execute("SELECT first_launch FROM users WHERE id = 1")
        result = cursor.fetchone()
        conn.close()

        assert result[0] == 0

    def test_migration_006_creates_wishlist_table(self, legacy_db):
        """Миграция 006 создаёт таблицу wishlist_items."""
        run_all_migrations(legacy_db)

        conn = sqlite3.connect(str(legacy_db))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='wishlist_items'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None

    def test_nonexistent_db_returns_empty(self):
        """Если БД не существует — возвращает пустой список."""
        applied = run_all_migrations(Path("/tmp/nonexistent_finfocus.db"))
        assert applied == []

    def test_fresh_db_no_migrations_needed(self):
        """Для свежей БД (через init_database) миграции не нужны."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            engine = create_engine(f"sqlite:///{db_path}")
            Base.metadata.create_all(engine)
            engine.dispose()

            applied = run_all_migrations(db_path)
            assert applied == []
        finally:
            db_path.unlink(missing_ok=True)
