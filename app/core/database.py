"""Централизованное управление сессиями БД."""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from loguru import logger

# Глобальные объекты (singleton pattern)
_engine = None
_session_factory = None


def get_engine():
    """Возвращает singleton engine.

    Returns:
        Engine: SQLAlchemy engine
    """
    global _engine
    if _engine is None:
        database_url = os.getenv("DATABASE_URL", "sqlite:///data/finfocus.db")
        _engine = create_engine(database_url, echo=False)
        logger.debug(f"Database engine создан: {database_url}")
    return _engine


def _get_session_factory():
    """Возвращает singleton session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = scoped_session(sessionmaker(bind=get_engine()))
        logger.debug("Session factory создана")
    return _session_factory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager для безопасной работы с сессией БД.

    Автоматически делает commit при успехе и rollback при ошибке.

    Yields:
        Session: SQLAlchemy сессия

    Example:
        with get_db_session() as session:
            service = TransactionService(session)
            service.create_transaction(...)
            # commit происходит автоматически
    """
    session = _get_session_factory()()
    try:
        yield session
        session.commit()
        logger.debug("Session commit выполнен")
    except Exception as e:
        session.rollback()
        logger.error(f"Session rollback из-за ошибки: {e}")
        raise
    finally:
        session.close()


def init_database(database_url: str = None) -> None:
    """Инициализирует базу данных — создаёт все таблицы.

    Args:
        database_url: URL базы данных (опционально, берётся из env)
    """
    global _engine
    if database_url:
        os.environ["DATABASE_URL"] = database_url
        _engine = None  # Сбрасываем для пересоздания с новым URL

    from app.models.database import Base

    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("База данных инициализирована")
