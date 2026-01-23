"""Скрипт для заполнения таблицы категорий предустановленными значениями.

Запуск: python scripts/seed_categories.py
Идемпотентный: можно запускать повторно.
"""

from app.core import get_db_session
from app.services import CategoryService


def main():
    """Запустить seed категорий."""
    with get_db_session() as session:
        service = CategoryService(session)
        count = service.seed_default_categories()
        session.commit()
        print(f"Добавлено категорий: {count}")


if __name__ == "__main__":
    main()
