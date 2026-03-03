"""Автоматическая инициализация данных при первом запуске.

Идемпотентно — безопасно при повторных запусках.
"""

from decimal import Decimal

from loguru import logger

from app.core.database import get_db_session
from app.models.database import User, Category
from app.services.category_service import CategoryService


def auto_bootstrap() -> dict[str, bool]:
    """Инициализирует пользователя по умолчанию и категории, если их нет.

    Returns:
        Словарь с признаками выполненных действий:
        {'user_created': bool, 'categories_seeded': bool}
    """
    result = {"user_created": False, "categories_seeded": False}

    with get_db_session() as session:
        if session.query(User).count() == 0:
            default_user = User(
                name="Пользователь",
                email="user@local",
                starting_balance=Decimal("0"),
                avatar_id="emoji-default",
                first_launch=True,
            )
            session.add(default_user)
            session.flush()
            logger.info(f"Создан пользователь по умолчанию (id={default_user.id})")
            result["user_created"] = True

        if session.query(Category).count() == 0:
            service = CategoryService(session)
            count = service.seed_default_categories()
            logger.info(f"Добавлено {count} предустановленных категорий")
            result["categories_seeded"] = True

        session.commit()

    return result
