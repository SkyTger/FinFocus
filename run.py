"""
Запуск приложения FinFocus.
"""
import os

from app.core import (
    setup_logging,
    logger,
    init_database,
    run_all_migrations,
    auto_bootstrap,
)
from app.main import app


if __name__ == "__main__":
    # Настраиваем логирование первым делом
    setup_logging()

    # Создаем папку data если её нет
    os.makedirs("data", exist_ok=True)

    # Инициализируем базу данных
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

    logger.info(f"Запускаем FinFocus на http://localhost:{port}")
    logger.info("Планировщик бюджета готов к работе!")

    app.run_server(debug=debug, port=port, host="0.0.0.0")
