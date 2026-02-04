"""Сервис для управления списком отложенных покупок (Wishlist)."""

from datetime import date
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.core import ValidationError
from app.models.database import WishlistItem
from app.schema.wishlist import WishlistItemData
from app.utils.formatters import format_amount

# Допустимые приоритеты: 1 = фокус, 2 = обычная
VALID_PRIORITIES = {1, 2}

# Поля, разрешённые для update в зависимости от статуса
_ALLOWED_FIELDS_NEW = {"name", "amount", "category_id", "priority"}
_ALLOWED_FIELDS_PLANNED = {"name", "priority"}


class WishlistService:
    """Сервис CRUD операций для отложенных покупок.

    Паттерн flush/commit: сервис вызывает flush(), caller делает commit().
    """

    def __init__(self, session: Session):
        """Инициализирует сервис.

        Args:
            session: SQLAlchemy сессия для работы с БД.
        """
        self.session = session

    def create_item(
        self,
        user_id: int,
        name: str,
        amount: Decimal,
        category_id: int | None = None,
        priority: int = 1,
    ) -> WishlistItem:
        """Создаёт новый элемент списка покупок.

        Args:
            user_id: ID пользователя.
            name: Название покупки (1-100 символов).
            amount: Стоимость покупки (> 0).
            category_id: ID категории (опционально).
            priority: Приоритет (1 = фокус, 2 = обычная).

        Returns:
            WishlistItem: Созданный элемент.

        Raises:
            ValidationError: При невалидных данных.
        """
        # Валидация name
        if not name or not name.strip():
            raise ValidationError("Название покупки не может быть пустым")
        name = name.strip()
        if len(name) > 100:
            raise ValidationError("Название покупки не может быть длиннее 100 символов")

        # Валидация amount
        if amount <= Decimal("0"):
            raise ValidationError("Сумма покупки должна быть больше 0")

        # Валидация priority
        if priority not in VALID_PRIORITIES:
            raise ValidationError(f"Приоритет должен быть одним из: {VALID_PRIORITIES}")

        item = WishlistItem(
            user_id=user_id,
            name=name,
            amount=amount,
            category_id=category_id,
            priority=priority,
        )
        self.session.add(item)
        self.session.flush()

        logger.info(
            f"Created wishlist item {item.id}: '{name}', "
            f"amount={amount}, priority={priority}"
        )
        return item

    def get_all(self, user_id: int) -> list[WishlistItem]:
        """Возвращает все элементы списка покупок пользователя.

        Сортировка: priority ASC, created_at ASC.

        Args:
            user_id: ID пользователя.

        Returns:
            list[WishlistItem]: Отсортированный список.
        """
        return (
            self.session.query(WishlistItem)
            .filter(WishlistItem.user_id == user_id)
            .order_by(WishlistItem.priority.asc(), WishlistItem.created_at.asc())
            .all()
        )

    def get_focus(self, user_id: int, limit: int = 5) -> list[WishlistItem]:
        """Возвращает фокусные покупки (priority=1).

        Args:
            user_id: ID пользователя.
            limit: Максимальное количество элементов.

        Returns:
            list[WishlistItem]: Фокусные элементы.
        """
        return (
            self.session.query(WishlistItem)
            .filter(
                WishlistItem.user_id == user_id,
                WishlistItem.priority == 1,
            )
            .order_by(WishlistItem.created_at.asc())
            .limit(limit)
            .all()
        )

    def get_by_id(self, item_id: int) -> WishlistItem | None:
        """Возвращает элемент по ID.

        Args:
            item_id: ID элемента.

        Returns:
            WishlistItem | None: Элемент или None.
        """
        return self.session.get(WishlistItem, item_id)

    def update_item(self, item_id: int, **updates) -> WishlistItem:
        """Обновляет элемент списка покупок.

        Для status="planned" разрешены только name и priority.
        Для status="new" — name, amount, category_id, priority.

        Args:
            item_id: ID элемента.
            **updates: Поля для обновления.

        Returns:
            WishlistItem: Обновлённый элемент.

        Raises:
            ValidationError: При невалидных данных или запрещённых полях.
        """
        item = self.session.get(WishlistItem, item_id)
        if not item:
            raise ValidationError("Покупка не найдена")

        # Определяем разрешённые поля по статусу
        allowed = (
            _ALLOWED_FIELDS_PLANNED if item.status == "planned" else _ALLOWED_FIELDS_NEW
        )
        forbidden = set(updates.keys()) - allowed
        if forbidden:
            raise ValidationError(
                f"Нельзя изменить поля {forbidden} для статуса '{item.status}'"
            )

        # Валидация значений
        if "name" in updates:
            name = updates["name"]
            if not name or not name.strip():
                raise ValidationError("Название покупки не может быть пустым")
            name = name.strip()
            if len(name) > 100:
                raise ValidationError(
                    "Название покупки не может быть длиннее 100 символов"
                )
            updates["name"] = name

        if "amount" in updates:
            if updates["amount"] <= Decimal("0"):
                raise ValidationError("Сумма покупки должна быть больше 0")

        if "priority" in updates:
            if updates["priority"] not in VALID_PRIORITIES:
                raise ValidationError(
                    f"Приоритет должен быть одним из: {VALID_PRIORITIES}"
                )

        for key, value in updates.items():
            setattr(item, key, value)

        self.session.flush()
        logger.info(f"Updated wishlist item {item_id}: {list(updates.keys())}")
        return item

    def mark_as_planned(
        self,
        item_id: int,
        planned_date: date,
        transaction_id: int,
    ) -> WishlistItem:
        """Помечает покупку как запланированную.

        Args:
            item_id: ID элемента.
            planned_date: Дата покупки.
            transaction_id: ID созданной транзакции.

        Returns:
            WishlistItem: Обновлённый элемент.

        Raises:
            ValidationError: Если элемент не найден.
        """
        item = self.session.get(WishlistItem, item_id)
        if not item:
            raise ValidationError("Покупка не найдена")

        item.status = "planned"
        item.planned_date = planned_date
        item.planned_transaction_id = transaction_id

        self.session.flush()
        logger.info(
            f"Wishlist item {item_id} marked as planned: "
            f"date={planned_date}, txn={transaction_id}"
        )
        return item

    def reset_planned(self, item_id: int) -> WishlistItem:
        """Сбрасывает статус planned на new.

        Args:
            item_id: ID элемента.

        Returns:
            WishlistItem: Обновлённый элемент.

        Raises:
            ValidationError: Если элемент не найден.
        """
        item = self.session.get(WishlistItem, item_id)
        if not item:
            raise ValidationError("Покупка не найдена")

        item.status = "new"
        item.planned_date = None
        item.planned_transaction_id = None

        self.session.flush()
        logger.info(f"Wishlist item {item_id} reset to new")
        return item

    def delete_item(self, item_id: int) -> bool:
        """Удаляет элемент списка покупок.

        НЕ удаляет привязанную транзакцию (ON DELETE SET NULL в FK).

        Args:
            item_id: ID элемента.

        Returns:
            bool: True если удалён, False если не найден.
        """
        item = self.session.get(WishlistItem, item_id)
        if not item:
            return False

        self.session.delete(item)
        self.session.flush()
        logger.info(f"Deleted wishlist item {item_id}")
        return True

    def check_orphaned_planned(self, user_id: int) -> list[WishlistItem]:
        """Возвращает «осиротевшие» planned-покупки (без транзакции).

        Это покупки со status="planned" и planned_transaction_id IS NULL.
        Возникают при удалении транзакции через Calendar UI.

        Args:
            user_id: ID пользователя.

        Returns:
            list[WishlistItem]: Осиротевшие элементы.
        """
        return (
            self.session.query(WishlistItem)
            .filter(
                WishlistItem.user_id == user_id,
                WishlistItem.status == "planned",
                WishlistItem.planned_transaction_id.is_(None),
            )
            .all()
        )

    def to_data(self, item: WishlistItem) -> WishlistItemData:
        """Конвертирует ORM объект в WishlistItemData TypedDict.

        Args:
            item: WishlistItem ORM объект.

        Returns:
            WishlistItemData: Данные для UI.
        """
        category_name = None
        category_icon = None
        if item.category_rel:
            category_name = item.category_rel.name
            category_icon = item.category_rel.icon

        return WishlistItemData(
            id=item.id,
            name=item.name,
            amount=format_amount(item.amount),
            category_id=item.category_id,
            category_name=category_name,
            category_icon=category_icon,
            priority=item.priority,
            status=item.status,
            planned_date=item.planned_date.isoformat() if item.planned_date else None,
            planned_transaction_id=item.planned_transaction_id,
        )
