"""Сервис для управления финансовыми операциями."""

import csv
import io
from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.core import ValidationError
from app.models.database import Category, Transaction, TransactionType

# NFR2: <500ms для bulk update операций
MAX_BULK_UPDATE_SIZE: int = 100


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
        category_id: int | None = None,
        is_recurring: bool = False,
        recurring_period: str | None = None,
        recurring_end_date: date | None = None,
    ) -> Transaction:
        """Создает новую транзакцию или шаблон recurring с валидацией.

        Args:
            user_id: ID пользователя
            amount: Сумма операции
            transaction_type: Тип операции (INCOME/EXPENSE/TRANSFER/ADJUSTMENT)
            transaction_date: Дата операции
            description: Описание операции (опционально)
            category_id: ID категории (опционально, nullable)
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
                - ADJUSTMENT с is_recurring=True
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

        # Валидация: ADJUSTMENT не может быть recurring
        if is_recurring and transaction_type == TransactionType.ADJUSTMENT:
            raise ValidationError(
                "Корректировки не могут быть повторяющимися операциями",
                field="is_recurring",
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
            category_id=category_id,
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
        category_id: int | None = None,
        is_recurring: bool | None = None,
        recurring_period: str | None = None,
        recurring_end_date: date | None = None,
    ) -> Transaction:
        """Обновляет существующую транзакцию.

        Args:
            transaction_id: ID транзакции
            amount: Новая сумма (опционально)
            transaction_type: Новый тип (опционально)
            transaction_date: Новая дата (опционально)
            description: Новое описание (опционально)
            category_id: Новый ID категории (опционально)
            is_recurring: Флаг recurring (опционально)
            recurring_period: Период повторения (опционально)
            recurring_end_date: Дата окончания серии (опционально)

        Returns:
            Transaction: Обновленная транзакция

        Raises:
            ValidationError: Если транзакция не найдена, amount <= 0,
                или ADJUSTMENT с is_recurring=True
        """
        transaction = self.session.get(Transaction, transaction_id)
        if not transaction:
            raise ValidationError(f"Транзакция с ID {transaction_id} не найдена")

        # Определяем итоговые значения для валидации
        new_type = (
            transaction_type
            if transaction_type is not None
            else transaction.transaction_type
        )
        new_is_recurring = (
            is_recurring if is_recurring is not None else transaction.is_recurring
        )

        # Валидация: ADJUSTMENT не может быть recurring
        if new_is_recurring and new_type == TransactionType.ADJUSTMENT:
            raise ValidationError(
                "Корректировки не могут быть повторяющимися операциями",
                field="is_recurring",
            )

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

        if category_id is not None:
            transaction.category_id = category_id

        if is_recurring is not None:
            transaction.is_recurring = is_recurring

        if recurring_period is not None:
            transaction.recurring_period = recurring_period

        if recurring_end_date is not None:
            transaction.recurring_end_date = recurring_end_date

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

    def bulk_update_category(
        self,
        user_id: int,
        transaction_ids: list[int],
        category_id: int | None,
    ) -> int:
        """Массовое обновление категории для списка транзакций.

        Args:
            user_id: ID пользователя (для валидации ownership).
            transaction_ids: Список ID транзакций (max 100).
            category_id: ID новой категории (или None для сброса).

        Returns:
            Количество обновленных записей.

        Raises:
            ValidationError:
                - Если len(transaction_ids) > MAX_BULK_UPDATE_SIZE
                - Если не все транзакции принадлежат пользователю
                - Если category_id не существует (при category_id != None)
        """
        # 1. Валидация размера
        if len(transaction_ids) > MAX_BULK_UPDATE_SIZE:
            raise ValidationError(
                f"Максимум {MAX_BULK_UPDATE_SIZE} операций за раз",
                field="transaction_ids",
            )

        if not transaction_ids:
            return 0

        # 2. Валидация category_id (если указан)
        if category_id is not None:
            category = self.session.query(Category).filter_by(id=category_id).first()
            if not category:
                raise ValidationError(
                    f"Категория с ID {category_id} не найдена",
                    field="category_id",
                )

        # 3. Bulk UPDATE с проверкой ownership
        affected = (
            self.session.query(Transaction)
            .filter(
                Transaction.id.in_(transaction_ids),
                Transaction.user_id == user_id,
                Transaction.is_recurring == False,  # noqa: E712
            )
            .update({"category_id": category_id}, synchronize_session=False)
        )

        # 4. Проверка что все транзакции обновлены
        if affected != len(transaction_ids):
            raise ValidationError(
                f"Не все операции принадлежат пользователю или являются шаблонами "
                f"(запрошено: {len(transaction_ids)}, обновлено: {affected})",
                field="transaction_ids",
            )

        self.session.flush()

        logger.info(
            f"Bulk update category для user {user_id}: "
            f"{affected} транзакций -> category_id={category_id}"
        )

        return affected

    def export_to_csv(
        self,
        user_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        category_id: int | None = None,
        uncategorized_only: bool = False,
    ) -> bytes:
        """Экспортирует транзакции в CSV файл.

        Args:
            user_id: ID пользователя.
            start_date: Фильтр начала периода.
            end_date: Фильтр конца периода.
            category_id: Фильтр по категории.
            uncategorized_only: Только без категории.

        Returns:
            CSV как bytes с UTF-8 BOM для Excel.
            Формат: Дата,Тип,Сумма,Описание,Категория
        """
        # 1. Построение запроса
        query = (
            self.session.query(Transaction, Category)
            .outerjoin(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user_id,
                Transaction.is_recurring == False,  # noqa: E712
            )
        )

        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        if uncategorized_only:
            query = query.filter(Transaction.category_id.is_(None))

        query = query.order_by(Transaction.transaction_date.desc())

        # 2. Генерация CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Дата", "Тип", "Сумма", "Описание", "Категория"])

        # Data
        type_labels = {
            TransactionType.INCOME: "Доход",
            TransactionType.EXPENSE: "Расход",
            TransactionType.TRANSFER: "Перевод",
            TransactionType.ADJUSTMENT: "Корректировка",
        }

        for tx, category in query.all():
            writer.writerow(
                [
                    tx.transaction_date.strftime("%Y-%m-%d"),
                    type_labels.get(tx.transaction_type, str(tx.transaction_type)),
                    str(tx.amount),
                    tx.description or "",
                    category.name if category else "Без категории",
                ]
            )

        # 3. UTF-8 BOM + encode
        csv_content = output.getvalue()
        return b"\xef\xbb\xbf" + csv_content.encode("utf-8")
