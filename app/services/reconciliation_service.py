"""Сервис для сверки баланса.

Предоставляет методы для сверки расчетного баланса с фактическим
и создания корректирующих операций (ADJUSTMENT).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import ValidationError
from app.models.database import Transaction, TransactionType
from app.schema.categories import ReconciliationPreview
from app.services.calendar_service import CalendarService
from app.services.category_service import CategoryService


class ReconciliationService:
    """Сервис для сверки баланса и создания корректировок."""

    def __init__(self, session: Session):
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy session для работы с БД.
        """
        self.session = session
        self.calendar_service = CalendarService(session)
        self.category_service = CategoryService(session)

    def get_expected_balance(self, user_id: int, target_date: date) -> Decimal:
        """Получить расчетный баланс на указанную дату.

        Args:
            user_id: ID пользователя.
            target_date: Дата для расчета баланса.

        Returns:
            Расчетный баланс на конец указанного дня.
        """
        return self.calendar_service.get_balance_on_date(user_id, target_date)

    def calculate_preview(
        self, user_id: int, target_date: date, actual_balance: Decimal
    ) -> ReconciliationPreview:
        """Рассчитать preview для модала сверки.

        Args:
            user_id: ID пользователя.
            target_date: Дата сверки.
            actual_balance: Фактический баланс (введенный пользователем).

        Returns:
            ReconciliationPreview с данными для отображения в модале.
        """
        expected_balance = self.get_expected_balance(user_id, target_date)
        difference = actual_balance - expected_balance
        is_positive = difference >= Decimal("0")

        # Формируем пояснение
        if difference == Decimal("0"):
            explanation = "Баланс совпадает, корректировка не требуется"
        elif is_positive:
            explanation = f"Будет создана корректировка на +{difference:,.2f} ₽"
        else:
            explanation = f"Будет создана корректировка на {difference:,.2f} ₽"

        return ReconciliationPreview(
            expected_balance=str(expected_balance),
            actual_balance=str(actual_balance),
            difference=str(difference),
            is_positive=is_positive,
            target_date=target_date.isoformat(),
            explanation=explanation,
        )

    def create_adjustment(
        self,
        user_id: int,
        target_date: date,
        actual_balance: Decimal,
        description: str | None = None,
    ) -> Transaction | None:
        """Создать корректирующую операцию (ADJUSTMENT).

        Если разница между фактическим и расчетным балансом равна нулю,
        корректировка не создается.

        Args:
            user_id: ID пользователя.
            target_date: Дата сверки.
            actual_balance: Фактический баланс.
            description: Описание корректировки (опционально).

        Returns:
            Созданная транзакция ADJUSTMENT или None если корректировка не нужна.

        Raises:
            ValidationError: Если системная категория "Коррекция" не найдена.
        """
        expected_balance = self.get_expected_balance(user_id, target_date)
        difference = actual_balance - expected_balance

        # Не создаем корректировку если баланс совпадает
        if difference == Decimal("0"):
            return None

        # Получаем системную категорию "Коррекция"
        correction_category = self.category_service.get_system_category("Коррекция")
        if not correction_category:
            raise ValidationError(
                "Системная категория 'Коррекция' не найдена. "
                "Запустите seed_categories.py"
            )

        # Формируем описание
        if not description:
            if difference > Decimal("0"):
                description = f"Сверка: баланс увеличен на {difference:,.2f} ₽"
            else:
                description = f"Сверка: баланс уменьшен на {abs(difference):,.2f} ₽"

        # Создаем транзакцию ADJUSTMENT
        # ВАЖНО: amount хранит именно difference (может быть отрицательным)
        adjustment = Transaction(
            user_id=user_id,
            amount=difference,  # Может быть + или -
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=target_date,
            description=description,
            category_id=correction_category.id,
        )

        self.session.add(adjustment)
        self.session.flush()

        return adjustment
