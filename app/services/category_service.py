"""Сервис для работы с категориями операций.

Предоставляет методы для получения и фильтрации категорий,
а также seed предустановленных категорий.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import Category, Transaction
from app.schema.categories import CategoryOption


# Константы
MIN_TRANSACTIONS_FOR_FREQUENCY: int = 3  # Fallback если < 3 транзакций с категориями


# Предустановленные категории для seed
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
    {
        "name": "Кредиты",
        "icon": "bi-bank",
        "type": "expense",
        "is_system": False,
        "sort_order": 11,
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


class CategoryService:
    """Сервис для работы с категориями операций."""

    def __init__(self, session: Session):
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy session для работы с БД.
        """
        self.session = session

    def get_all(self) -> list[Category]:
        """Получить все категории, отсортированные по sort_order.

        Returns:
            Список всех категорий.
        """
        return self.session.query(Category).order_by(Category.sort_order).all()

    def get_by_id(self, category_id: int) -> Category | None:
        """Получить категорию по ID.

        Args:
            category_id: ID категории.

        Returns:
            Категория или None если не найдена.
        """
        return self.session.query(Category).filter_by(id=category_id).first()

    def get_by_type(self, category_type: str) -> list[Category]:
        """Получить категории по типу.

        Args:
            category_type: Тип категории ("income", "expense", "both").

        Returns:
            Список категорий указанного типа + категории с type="both".
        """
        return (
            self.session.query(Category)
            .filter((Category.type == category_type) | (Category.type == "both"))
            .order_by(Category.sort_order)
            .all()
        )

    def get_for_dropdown(
        self, category_type: str | None = None, include_system: bool = False
    ) -> list[CategoryOption]:
        """Получить категории в формате для dropdown UI.

        Args:
            category_type: Фильтр по типу ("income", "expense") или None для всех.
            include_system: Включать ли системные категории (is_system=True).

        Returns:
            Список CategoryOption для использования в dcc.Dropdown.
        """
        query = self.session.query(Category)

        # Фильтр по типу
        if category_type:
            query = query.filter(
                (Category.type == category_type) | (Category.type == "both")
            )

        # Фильтр системных категорий
        if not include_system:
            query = query.filter(Category.is_system == False)  # noqa: E712

        categories = query.order_by(Category.sort_order).all()

        return [
            CategoryOption(label=cat.name, value=cat.id, icon=cat.icon)
            for cat in categories
        ]

    def get_system_category(self, name: str = "Коррекция") -> Category | None:
        """Получить системную категорию по имени.

        Args:
            name: Имя системной категории.

        Returns:
            Системная категория или None.
        """
        return self.session.query(Category).filter_by(name=name, is_system=True).first()

    def seed_default_categories(self) -> int:
        """Заполнить таблицу предустановленными категориями.

        Идемпотентный метод: пропускает категории, которые уже существуют.

        Returns:
            Количество добавленных категорий.
        """
        existing_names = {c.name for c in self.session.query(Category).all()}
        added_count = 0

        for cat_data in DEFAULT_CATEGORIES:
            if cat_data["name"] not in existing_names:
                category = Category(**cat_data)
                self.session.add(category)
                added_count += 1

        self.session.flush()
        return added_count

    def get_frequent_for_type(
        self,
        user_id: int,
        category_type: str,
        limit: int = 6,
    ) -> list[CategoryOption]:
        """Получить часто используемые категории пользователя.

        Сортировка по частоте использования (COUNT transactions WHERE user_id=X).

        Args:
            user_id: ID пользователя.
            category_type: Тип категории для фильтрации ("income" | "expense").
            limit: Максимальное количество (default 6 для chips).

        Returns:
            Список CategoryOption отсортированный по частоте DESC.

        Fallback:
            Если у пользователя < MIN_TRANSACTIONS_FOR_FREQUENCY транзакций
            с категориями данного типа, возвращает top-N по sort_order.
        """
        # 1. Подсчет транзакций с категориями данного типа у пользователя
        user_tx_count = (
            self.session.query(func.count(Transaction.id))
            .join(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user_id,
                Category.type == category_type,
            )
            .scalar()
        ) or 0

        # 2. Fallback если мало данных
        if user_tx_count < MIN_TRANSACTIONS_FOR_FREQUENCY:
            categories = (
                self.session.query(Category)
                .filter(Category.type == category_type)
                .order_by(Category.sort_order)
                .limit(limit)
                .all()
            )
            return [
                CategoryOption(
                    label=cat.name,
                    value=cat.id,
                    icon=cat.icon,
                )
                for cat in categories
            ]

        # 3. Основной запрос: категории отсортированные по частоте
        frequency_query = (
            self.session.query(
                Category,
                func.count(Transaction.id).label("tx_count"),
            )
            .join(Transaction, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user_id,
                Category.type == category_type,
            )
            .group_by(Category.id)
            .order_by(func.count(Transaction.id).desc())
            .limit(limit)
        )

        return [
            CategoryOption(
                label=cat.name,
                value=cat.id,
                icon=cat.icon,
            )
            for cat, _ in frequency_query.all()
        ]
