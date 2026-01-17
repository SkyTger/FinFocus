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
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        format=console_format,
        level=level,
        colorize=True,
    )

    # File output с ротацией
    logger.add(
        f"{log_dir}/finfocus_{{time:YYYY-MM-DD}}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
        encoding="utf-8",
    )

    logger.info("Логирование настроено")
