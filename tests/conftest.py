"""Фикстуры для тестов FinFocus."""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, User


@pytest.fixture(scope="function")
def db_engine():
    """Создает in-memory SQLite engine для тестов."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Создает сессию БД для тестов."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_user(db_session) -> User:
    """Создает тестового пользователя с starting_balance=10000."""
    user = User(
        email="test@example.com",
        name="Test User",
        starting_balance=Decimal("10000.00"),
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_user_zero_balance(db_session) -> User:
    """Создает тестового пользователя с starting_balance=0."""
    user = User(
        email="zero@example.com",
        name="Zero Balance User",
        starting_balance=Decimal("0"),
    )
    db_session.add(user)
    db_session.commit()
    return user
