"""Сервис для управления финансовыми операциями."""

from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.core import ValidationError
from app.models.database import Transaction, TransactionType


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
        description: str | None = None,
        category: str | None = None,
        is_recurring: bool = False,
        recurring_period: str | None = None,
        recurring_end_date: date | None = None,
    ) -> Transaction:
        """Создает новую транзакцию или шаблон recurring с валидацией.

        Args:
            user_id: ID пользователя
            amount: Сумма операции
            transaction_type: Тип операции (INCOME/EXPENSE/TRANSFER)
            transaction_date: Дата операции
            description: Описание операции (опционально)
            category: Категория операции (опционально)
            is_recurring: Флаг повторяющейся операции
            recurring_period: Период повторения (weekly/biweekly/monthly/quarterly)
            recurring_end_date: Дата окончания серии (опционально)

        Returns:
            Transaction: Созданная транзакция или шаблон

        Raises:
            ValidationError: Если нарушены бизнес-правила:
                - amount <= 0
                - transaction_date > 1 год в будущем
                - recurring без периода
                - недопустимый период
        """
        # Валидация: amount > 0
        if amount <= 0:
            raise ValidationError("Сумма операции должна быть больше 0", field="amount")

        # Валидация: дата не более 1 года в будущем
        max_future_date = date.today() + timedelta(days=365)
        if transaction_date > max_future_date:
            raise ValidationError(
                "Дата операции не может быть более чем на 1 год в будущем",
                field="transaction_date",
            )

        # Валидация recurring полей
        if is_recurring:
            if not recurring_period:
                raise ValidationError(
                    "Период повторения обязателен для recurring операций",
                    field="recurring_period",
                )

            from app.services.recurring_service import VALID_RECURRING_PERIODS

            if recurring_period not in VALID_RECURRING_PERIODS:
                raise ValidationError(
                    f"Недопустимый период: {recurring_period}. "
                    f"Допустимые: {', '.join(VALID_RECURRING_PERIODS)}",
                    field="recurring_period",
                )

        # Создание транзакции
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            transaction_date=transaction_date,
            description=description,
            category=category,
            is_recurring=is_recurring,
            recurring_period=recurring_period if is_recurring else None,
            recurring_end_date=recurring_end_date if is_recurring else None,
        )

        self.session.add(transaction)
        self.session.flush()  # Получить ID без commit

        log_msg = (
            f"Создана транзакция {transaction.id} для user {user_id}: "
            f"{transaction_type.value} {amount}"
        )
        if is_recurring:
            log_msg += f" (recurring: {recurring_period})"
        logger.info(log_msg)

        return transaction

    def get_by_id(self, transaction_id: int) -> Transaction | None:
        """Получает транзакцию по ID.

        Args:
            transaction_id: ID транзакции

        Returns:
            Transaction: Найденная транзакция или None
        """
        return self.session.get(Transaction, transaction_id)

    def get_all_by_user(
        self,
        user_id: int,
        transaction_type: TransactionType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Transaction]:
        """Получает все транзакции пользователя с фильтрацией.

        Args:
            user_id: ID пользователя
            transaction_type: Фильтр по типу (опционально)
            start_date: Начало периода (опционально)
            end_date: Конец периода (опционально)

        Returns:
            list[Transaction]: Список транзакций, отсортированный по дате
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
        amount: Decimal | None = None,
        transaction_type: TransactionType | None = None,
        transaction_date: date | None = None,
        description: str | None = None,
        category: str | None = None,
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
        transaction = self.session.get(Transaction, transaction_id)
        if not transaction:
            raise ValidationError(f"Транзакция с ID {transaction_id} не найдена")

        # Обновление полей (только если переданы новые значения)
        if amount is not None:
            if amount <= 0:
                raise ValidationError(
                    "Сумма операции должна быть больше 0", field="amount"
                )
            transaction.amount = amount

        if transaction_type is not None:
            transaction.transaction_type = transaction_type

        if transaction_date is not None:
            max_future_date = date.today() + timedelta(days=365)
            if transaction_date > max_future_date:
                raise ValidationError(
                    "Дата операции не может быть более чем на 1 год в будущем",
                    field="transaction_date",
                )
            transaction.transaction_date = transaction_date

        if description is not None:
            transaction.description = description

        if category is not None:
            transaction.category = category

        # updated_at обновится автоматически через onupdate
        self.session.flush()

        logger.info(f"Обновлена транзакция {transaction_id}")

        return transaction

    def delete_transaction(self, transaction_id: int) -> bool:
        """Удаляет транзакцию по ID.

        Args:
            transaction_id: ID транзакции

        Returns:
            bool: True если транзакция удалена, False если не найдена
        """
        transaction = self.session.get(Transaction, transaction_id)
        if not transaction:
            return False

        self.session.delete(transaction)
        self.session.flush()

        logger.info(f"Удалена транзакция {transaction_id}")

        return True
