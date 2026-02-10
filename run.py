"""
Запуск приложения FinFocus.
"""
import os
from decimal import Decimal

from app.core import setup_logging, logger, init_database, get_db_session
from app.main import app
from app.models.database import User, Category
from app.services.category_service import CategoryService


def auto_bootstrap() -> None:
    """Автоинициализация при первом запуске.

    Создаёт пользователя по умолчанию и сидит категории,
    если база данных пустая. Идемпотентно — безопасно при повторных запусках.
    """
    with get_db_session() as session:
        user_count = session.query(User).count()
        category_count = session.query(Category).count()

        if user_count == 0:
            default_user = User(
                name="Пользователь",
                email="user@local",
                starting_balance=Decimal("0"),
                first_launch=True,
            )
            session.add(default_user)
            session.flush()
            logger.info(f"Создан пользователь по умолчанию (id={default_user.id})")

        if category_count == 0:
            service = CategoryService(session)
            count = service.seed_default_categories()
            logger.info(f"Добавлено {count} предустановленных категорий")

        session.commit()


if __name__ == "__main__":
    # Настраиваем логирование первым делом
    setup_logging()

    # Создаем папку data если её нет
    os.makedirs("data", exist_ok=True)

    # Инициализируем базу данных
    logger.info("Инициализация базы данных...")
    init_database()
    logger.info("База данных готова")

    # Auto-bootstrap: создание пользователя и категорий при первом запуске
    auto_bootstrap()

    # Запускаем приложение
    debug = os.getenv("DEBUG", "False").lower() == "true"
    port = int(os.getenv("PORT", 8050))

    logger.info(f"Запускаем FinFocus на http://localhost:{port}")
    logger.info("Планировщик бюджета готов к работе!")

    app.run_server(debug=debug, port=port, host="0.0.0.0")
