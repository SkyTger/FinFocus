"""
Запуск приложения FinFocus.
"""
import os

from app.core import setup_logging, logger, init_database, get_db_session
from app.main import app
from app.models.database import User

if __name__ == "__main__":
    # Настраиваем логирование первым делом
    setup_logging()

    # Создаем папку data если её нет
    os.makedirs("data", exist_ok=True)

    # Инициализируем базу данных
    logger.info("Инициализация базы данных...")
    init_database()
    logger.info("База данных готова")

    # Проверка: есть ли данные в БД?
    with get_db_session() as session:
        user_count = session.query(User).count()

    if user_count == 0:
        logger.warning("База данных пустая!")
        logger.info("Запустите: python scripts/seed_database.py")
    else:
        logger.info(f"Найдено пользователей: {user_count}")

    # Запускаем приложение
    debug = os.getenv("DEBUG", "True").lower() == "true"
    port = int(os.getenv("PORT", 8050))

    logger.info(f"Запускаем FinFocus на http://localhost:{port}")
    logger.info("Планировщик бюджета готов к работе!")

    app.run_server(debug=debug, port=port, host="0.0.0.0")
