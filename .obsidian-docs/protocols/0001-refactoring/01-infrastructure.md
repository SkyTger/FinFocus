# Шаг 1: Инфраструктура — Session Management + loguru

## Briefing
- **Цель:** Создать централизованную систему управления сессиями БД (singleton pattern) и настроить логирование через loguru. Это фундамент для всех последующих изменений.
- **Ключевые файлы:**
  - `app/core/__init__.py` (создать)
  - `app/core/database.py` (создать) — session factory
  - `app/core/logging.py` (создать) — loguru setup
  - `app/models/database.py` (модифицировать) — убрать дублирующиеся функции
  - `run.py` (модифицировать) — интегрировать логирование
  - `requirements.txt` (модифицировать) — добавить loguru
- **Additional info:**
  - Используем scoped_session для thread safety (Dash может работать в нескольких потоках)
  - loguru настраиваем с ротацией логов по дням, хранение 7 дней
  - Папка logs/ добавляется в .gitignore

## Sub-tasks

### 1. Добавить loguru в зависимости
- Добавить `loguru>=0.7.0` в `requirements.txt`

### 2. Создать структуру app/core/
- Создать папку `app/core/`
- Создать файл `app/core/__init__.py`:
```python
"""Core модуль приложения — инфраструктурные компоненты."""

from .logging import setup_logging, logger
from .database import get_db_session, get_engine, init_database

__all__ = ['setup_logging', 'logger', 'get_db_session', 'get_engine', 'init_database']
```

### 3. Создать app/core/logging.py
```python
"""Настройка логирования через loguru."""

import sys
from pathlib import Path
from loguru import logger

def setup_logging(log_dir: str = "logs", level: str = "INFO") -> None:
    """Настраивает loguru для приложения.

    Args:
        log_dir: Папка для файлов логов
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
    """
    # Создаём папку для логов
    Path(log_dir).mkdir(exist_ok=True)

    # Убираем default handler
    logger.remove()

    # Console output
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        level=level,
        colorize=True
    )

    # File output с ротацией
    logger.add(
        f"{log_dir}/finfocus_{{time:YYYY-MM-DD}}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
        encoding="utf-8"
    )

    logger.info("Логирование настроено")
```

### 4. Создать app/core/database.py
```python
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
        database_url = os.getenv('DATABASE_URL', 'sqlite:///data/finfocus.db')
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
        os.environ['DATABASE_URL'] = database_url
        _engine = None  # Сбрасываем для пересоздания с новым URL

    from app.models.database import Base
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("База данных инициализирована")
```

### 5. Обновить app/models/database.py
- Убрать функции `create_database_engine()`, `create_tables()`, `get_session()`, `init_database()`
- Оставить только модели (User, Transaction, Goal, GoalContribution) и enums
- Обновить импорт declarative_base на новый API

### 6. Обновить run.py
- Добавить импорт и вызов `setup_logging()` в начале
- Заменить `print()` на `logger.info()`
- Использовать `init_database()` из `app.core`
- Использовать `get_db_session()` вместо ручного создания session

### 7. Добавить logs/ в .gitignore
- Добавить строку `logs/` в `.gitignore`

## Workflow (Порядок работы)

**Твоя задача — выполнить `Sub-tasks` выше, строго следуя этому циклу.**

1.  **Выполнение:** Последовательно выполняй подзадачи 1-7.
2.  **Верификация:** После завершения ВСЕХ подзадач:
    - `python -m py_compile app/core/logging.py app/core/database.py app/models/database.py run.py`
    - `python run.py` — приложение должно запуститься, в консоли появятся цветные логи
    - Проверить создание файла `logs/finfocus_YYYY-MM-DD.log`
    - Открыть http://localhost:8050/transactions — страница должна работать
3.  **Фиксация:** После успешной верификации:
    - Добавь запись в `log.md`
    - Обнови `context.md`: `Current Step` → 2
    - Проверь ветку main на отсутствие наших файлов
4.  **Коммит**: `git add . && git commit -m "feat(core): add session factory and loguru logging [protocol-0001/01]"`. Push.
5.  **Отчет пользователю** в установленном формате.
