"""Централизованное определение путей приложения.

Поддерживает два режима:
- Normal: пути относительно корня проекта
- Frozen (PyInstaller): bundle dir (sys._MEIPASS) для assets,
  app dir (директория exe) для данных пользователя
"""

import sys
from pathlib import Path


def is_frozen() -> bool:
    """Проверяет, запущено ли приложение из PyInstaller бандла."""
    return getattr(sys, "frozen", False)


def get_bundle_dir() -> Path:
    """Возвращает директорию с файлами бандла (assets, код).

    - Frozen: sys._MEIPASS (временная директория PyInstaller)
    - Normal: корень проекта
    """
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def get_app_dir() -> Path:
    """Возвращает директорию приложения (для данных пользователя).

    - Frozen: директория, где лежит exe
    - Normal: корень проекта
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def get_data_dir() -> Path:
    """Возвращает путь к директории данных (data/).

    Автоматически создаёт директорию если не существует.
    """
    data_dir = get_app_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_logs_dir() -> Path:
    """Возвращает путь к директории логов (logs/).

    Автоматически создаёт директорию если не существует.
    """
    logs_dir = get_app_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_assets_dir() -> Path:
    """Возвращает путь к директории assets.

    - Frozen: внутри бандла (sys._MEIPASS/app/assets/)
    - Normal: app/assets/ от корня проекта
    """
    return get_bundle_dir() / "app" / "assets"
