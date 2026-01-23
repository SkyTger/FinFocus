"""Скрипт для заполнения таблицы категорий предустановленными значениями.

Запуск: python scripts/seed_categories.py
Идемпотентный: можно запускать повторно.
"""

from app.core import get_db_session
from app.models.database import Category


DEFAULT_CATEGORIES = [
    # Системная категория для коррекций
    {
        "name": "Коррекция",
        "icon": "bi-arrow-repeat",
        "type": "both",
        "is_system": True,
        "sort_order": 0,
    },
    # Расходы
    {
        "name": "Еда и продукты",
        "icon": "bi-cart",
        "type": "expense",
        "is_system": False,
        "sort_order": 1,
    },
    {
        "name": "Транспорт",
        "icon": "bi-car-front",
        "type": "expense",
        "is_system": False,
        "sort_order": 2,
    },
    {
        "name": "Жилье и ЖКХ",
        "icon": "bi-house",
        "type": "expense",
        "is_system": False,
        "sort_order": 3,
    },
    {
        "name": "Связь и интернет",
        "icon": "bi-phone",
        "type": "expense",
        "is_system": False,
        "sort_order": 4,
    },
    {
        "name": "Здоровье",
        "icon": "bi-heart-pulse",
        "type": "expense",
        "is_system": False,
        "sort_order": 5,
    },
    {
        "name": "Одежда",
        "icon": "bi-bag",
        "type": "expense",
        "is_system": False,
        "sort_order": 6,
    },
    {
        "name": "Развлечения",
        "icon": "bi-controller",
        "type": "expense",
        "is_system": False,
        "sort_order": 7,
    },
    {
        "name": "Образование",
        "icon": "bi-book",
        "type": "expense",
        "is_system": False,
        "sort_order": 8,
    },
    {
        "name": "Подарки другим",
        "icon": "bi-gift",
        "type": "expense",
        "is_system": False,
        "sort_order": 9,
    },
    {
        "name": "Прочие расходы",
        "icon": "bi-three-dots",
        "type": "expense",
        "is_system": False,
        "sort_order": 10,
    },
    # Доходы
    {
        "name": "Зарплата",
        "icon": "bi-briefcase",
        "type": "income",
        "is_system": False,
        "sort_order": 101,
    },
    {
        "name": "Подработка",
        "icon": "bi-laptop",
        "type": "income",
        "is_system": False,
        "sort_order": 102,
    },
    {
        "name": "Инвестиции",
        "icon": "bi-graph-up",
        "type": "income",
        "is_system": False,
        "sort_order": 103,
    },
    {
        "name": "Подарки полученные",
        "icon": "bi-gift",
        "type": "income",
        "is_system": False,
        "sort_order": 104,
    },
    {
        "name": "Прочие доходы",
        "icon": "bi-three-dots",
        "type": "income",
        "is_system": False,
        "sort_order": 105,
    },
]


def seed_default_categories() -> int:
    """Заполняет таблицу категорий предустановленными значениями.

    Идемпотентный: пропускает категории, которые уже существуют (по имени).

    Returns:
        Количество добавленных категорий.
    """
    added_count = 0

    with get_db_session() as session:
        existing_names = {c.name for c in session.query(Category).all()}

        for cat_data in DEFAULT_CATEGORIES:
            if cat_data["name"] not in existing_names:
                category = Category(**cat_data)
                session.add(category)
                added_count += 1

        session.commit()

    return added_count


if __name__ == "__main__":
    count = seed_default_categories()
    print(f"Добавлено категорий: {count}")
