"""
Запуск приложения FinFocus.
"""
import os
import threading
import time
import urllib.request
import webbrowser

from app.core import (
    setup_logging,
    logger,
    init_database,
    run_all_migrations,
    auto_bootstrap,
)
from app.main import app


def _open_browser(url: str, retries: int = 5, delay: float = 1.0) -> None:
    """Открывает браузер после готовности сервера."""
    for _ in range(retries):
        try:
            urllib.request.urlopen(url, timeout=1)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(delay)


if __name__ == "__main__":
    # Настраиваем логирование первым делом
    setup_logging()

    # Инициализируем базу данных (data/ создаётся автоматически через paths)
    logger.info("Инициализация базы данных...")
    init_database()
    logger.info("База данных готова")

    # Запускаем миграции (идемпотентно, для upgrade существующих БД)
    run_all_migrations()

    # Auto-bootstrap: создание пользователя и категорий при первом запуске
    auto_bootstrap()

    # Запускаем приложение
    debug = os.getenv("DEBUG", "False").lower() == "true"
    port = int(os.getenv("PORT", 8050))
    url = f"http://localhost:{port}"

    # Открываем браузер автоматически (если не отключено)
    if not os.getenv("FINFOCUS_NO_BROWSER"):
        threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    logger.info(f"Запускаем FinFocus на {url}")
    logger.info("Планировщик бюджета готов к работе!")

    app.run_server(debug=debug, port=port, host="0.0.0.0")
