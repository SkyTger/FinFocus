"""Тесты для TransactionService."""

from datetime import date
from decimal import Decimal

import pytest

from app.core import ValidationError
from app.models.database import Category, TransactionType
from app.services.transaction_service import TransactionService


class TestTransactionServiceCreate:
    """Тесты создания транзакций."""

    def test_create_basic_transaction(self, db_session, test_user):
        """Создание базовой транзакции."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            description="Тестовая транзакция",
        )

        assert transaction.id is not None
        assert transaction.amount == Decimal("100.00")
        assert transaction.transaction_type == TransactionType.EXPENSE
        assert transaction.description == "Тестовая транзакция"

    def test_create_with_zero_amount_fails(self, db_session, test_user):
        """Нельзя создать транзакцию с нулевой суммой."""
        service = TransactionService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_transaction(
                user_id=test_user.id,
                amount=Decimal("0"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date.today(),
            )

        assert "больше 0" in str(exc_info.value)


class TestTransactionServiceCategoryId:
    """Тесты category_id в TransactionService."""

    def test_create_with_category_id(self, db_session, test_user):
        """Транзакция создается с category_id."""
        category = Category(name="Еда", type="expense")
        db_session.add(category)
        db_session.flush()

        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=category.id,
        )

        assert transaction.category_id == category.id

    def test_create_without_category_id(self, db_session, test_user):
        """Транзакция создается без category_id (nullable)."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )

        assert transaction.category_id is None

    def test_update_category_id(self, db_session, test_user):
        """category_id можно обновить."""
        category = Category(name="Еда", type="expense")
        db_session.add(category)
        db_session.flush()

        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )

        updated = service.update_transaction(
            transaction.id,
            category_id=category.id,
        )

        assert updated.category_id == category.id


class TestTransactionServiceAdjustmentValidation:
    """Тесты валидации ADJUSTMENT + recurring."""

    def test_adjustment_cannot_be_recurring(self, db_session, test_user):
        """ADJUSTMENT не может быть recurring."""
        service = TransactionService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_transaction(
                user_id=test_user.id,
                amount=Decimal("100.00"),
                transaction_type=TransactionType.ADJUSTMENT,
                transaction_date=date.today(),
                is_recurring=True,
                recurring_period="monthly",
            )

        assert "повторяющимися" in str(exc_info.value)

    def test_adjustment_single_allowed(self, db_session, test_user):
        """ADJUSTMENT без recurring создается успешно."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today(),
        )

        assert transaction.transaction_type == TransactionType.ADJUSTMENT
        assert transaction.is_recurring is False

    def test_update_to_adjustment_recurring_fails(self, db_session, test_user):
        """Нельзя обновить recurring транзакцию в ADJUSTMENT."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            is_recurring=True,
            recurring_period="monthly",
        )

        with pytest.raises(ValidationError) as exc_info:
            service.update_transaction(
                transaction.id,
                transaction_type=TransactionType.ADJUSTMENT,
            )

        assert "повторяющимися" in str(exc_info.value)

    def test_update_adjustment_to_recurring_fails(self, db_session, test_user):
        """Нельзя сделать ADJUSTMENT recurring через update."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today(),
        )

        with pytest.raises(ValidationError) as exc_info:
            service.update_transaction(
                transaction.id,
                is_recurring=True,
            )

        assert "повторяющимися" in str(exc_info.value)


class TestTransactionServiceUpdate:
    """Тесты обновления транзакций."""

    def test_update_amount(self, db_session, test_user):
        """Обновление суммы транзакции."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )

        updated = service.update_transaction(
            transaction.id,
            amount=Decimal("200.00"),
        )

        assert updated.amount == Decimal("200.00")

    def test_update_nonexistent_fails(self, db_session):
        """Обновление несуществующей транзакции."""
        service = TransactionService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.update_transaction(99999, amount=Decimal("100.00"))

        assert "не найдена" in str(exc_info.value)


class TestTransactionServiceDelete:
    """Тесты удаления транзакций."""

    def test_delete_existing(self, db_session, test_user):
        """Удаление существующей транзакции."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )

        result = service.delete_transaction(transaction.id)

        assert result is True
        assert service.get_by_id(transaction.id) is None

    def test_delete_nonexistent(self, db_session):
        """Удаление несуществующей транзакции возвращает False."""
        service = TransactionService(db_session)

        result = service.delete_transaction(99999)

        assert result is False
