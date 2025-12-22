"""Сервис для управления финансовыми операциями."""

from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from models.database import Transaction, TransactionType


class ValidationError(Exception):
    """Ошибка валидации бизнес-правил."""
    pass


class TransactionService:
    """Сервис для операций с финансовыми транзакциями."""

    def __init__(self, session: Session):
        """Инициализирует сервис транзакций.

        Args:
            session: SQLAlchemy сессия для работы с БД
        """
        self.session = session

    def create_transaction(
        self,
        user_id: int,
        amount: Decimal,
        transaction_type: TransactionType,
        transaction_date: date,
        description: str = None,
        category: str = None
    ) -> Transaction:
        """Создает новую транзакцию с валидацией бизнес-правил.

        Args:
            user_id: ID пользователя
            amount: Сумма операции
            transaction_type: Тип операции (INCOME/EXPENSE/TRANSFER)
            transaction_date: Дата операции
            description: Описание операции (опционально)
            category: Категория операции (опционально)

        Returns:
            Transaction: Созданная транзакция

        Raises:
            ValidationError: Если нарушены бизнес-правила:
                - amount <= 0
                - transaction_date > 1 год в будущем
        """
        # Валидация: amount > 0
        if amount <= 0:
            raise ValidationError("Сумма операции должна быть больше 0")

        # Валидация: дата не более 1 года в будущем
        max_future_date = date.today() + timedelta(days=365)
        if transaction_date > max_future_date:
            raise ValidationError(
                "Дата операции не может быть более чем на 1 год в будущем"
            )

        # Создание транзакции
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            transaction_date=transaction_date,
            description=description,
            category=category
        )

        self.session.add(transaction)
        self.session.flush()  # Получить ID без commit

        return transaction

    def get_by_id(self, transaction_id: int) -> Transaction:
        """Получает транзакцию по ID.

        Args:
            transaction_id: ID транзакции

        Returns:
            Transaction: Найденная транзакция или None
        """
        return self.session.query(Transaction).get(transaction_id)

    def get_all_by_user(
        self,
        user_id: int,
        transaction_type: TransactionType = None,
        start_date: date = None,
        end_date: date = None
    ) -> list[Transaction]:
        """Получает все транзакции пользователя с фильтрацией.

        Args:
            user_id: ID пользователя
            transaction_type: Фильтр по типу (опционально)
            start_date: Начало периода (опционально)
            end_date: Конец периода (опционально)

        Returns:
            list[Transaction]: Список транзакций, отсортированный по дате (DESC)
        """
        query = self.session.query(Transaction).filter_by(user_id=user_id)

        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)

        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)

        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)

        return query.order_by(Transaction.transaction_date.desc()).all()

    def update_transaction(
        self,
        transaction_id: int,
        amount: Decimal = None,
        transaction_type: TransactionType = None,
        transaction_date: date = None,
        description: str = None,
        category: str = None
    ) -> Transaction:
        """Обновляет существующую транзакцию.

        Args:
            transaction_id: ID транзакции
            amount: Новая сумма (опционально)
            transaction_type: Новый тип (опционально)
            transaction_date: Новая дата (опционально)
            description: Новое описание (опционально)
            category: Новая категория (опционально)

        Returns:
            Transaction: Обновленная транзакция

        Raises:
            ValidationError: Если транзакция не найдена или amount <= 0
        """
        transaction = self.session.query(Transaction).get(transaction_id)
        if not transaction:
            raise ValidationError(f"Транзакция с ID {transaction_id} не найдена")

        # Обновление полей (только если переданы новые значения)
        if amount is not None:
            if amount <= 0:
                raise ValidationError("Сумма операции должна быть больше 0")
            transaction.amount = amount

        if transaction_type is not None:
            transaction.transaction_type = transaction_type

        if transaction_date is not None:
            max_future_date = date.today() + timedelta(days=365)
            if transaction_date > max_future_date:
                raise ValidationError(
                    "Дата операции не может быть более чем на 1 год в будущем"
                )
            transaction.transaction_date = transaction_date

        if description is not None:
            transaction.description = description

        if category is not None:
            transaction.category = category

        # updated_at обновится автоматически через onupdate
        self.session.flush()

        return transaction

    def delete_transaction(self, transaction_id: int) -> bool:
        """Удаляет транзакцию по ID.

        Args:
            transaction_id: ID транзакции

        Returns:
            bool: True если транзакция удалена, False если не найдена
        """
        transaction = self.session.query(Transaction).get(transaction_id)
        if not transaction:
            return False

        self.session.delete(transaction)
        self.session.flush()

        return True