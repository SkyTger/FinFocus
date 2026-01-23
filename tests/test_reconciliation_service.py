"""Тесты для ReconciliationService."""

import pytest
from datetime import date
from decimal import Decimal

from app.core import ValidationError
from app.models.database import Transaction, TransactionType
from app.services.category_service import CategoryService
from app.services.reconciliation_service import ReconciliationService


@pytest.fixture
def seeded_categories(db_session):
    """Фикстура для создания предустановленных категорий."""
    service = CategoryService(db_session)
    service.seed_default_categories()
    db_session.commit()
    return service


class TestReconciliationServiceGetExpectedBalance:
    """Тесты метода get_expected_balance."""

    def test_get_expected_balance_empty(self, db_session, test_user_zero_balance):
        """Возвращает 0 для пользователя без транзакций (starting_balance=0)."""
        service = ReconciliationService(db_session)
        result = service.get_expected_balance(test_user_zero_balance.id, date.today())
        assert result == Decimal("0")

    def test_get_expected_balance_with_starting_balance(self, db_session, test_user):
        """Возвращает starting_balance для пользователя без транзакций."""
        service = ReconciliationService(db_session)
        result = service.get_expected_balance(test_user.id, date.today())
        # test_user имеет starting_balance=10000
        assert result == Decimal("10000.00")

    def test_get_expected_balance_with_transactions(
        self, db_session, test_user_zero_balance
    ):
        """Возвращает корректный баланс с учетом транзакций."""
        # Добавляем транзакции
        income = Transaction(
            user_id=test_user_zero_balance.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date.today(),
        )
        expense = Transaction(
            user_id=test_user_zero_balance.id,
            amount=Decimal("300.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )
        db_session.add_all([income, expense])
        db_session.commit()

        service = ReconciliationService(db_session)
        result = service.get_expected_balance(test_user_zero_balance.id, date.today())

        assert result == Decimal("700.00")


class TestReconciliationServiceCalculatePreview:
    """Тесты метода calculate_preview."""

    def test_preview_positive_difference(self, db_session, test_user_zero_balance):
        """Preview корректно рассчитывает положительную разницу."""
        service = ReconciliationService(db_session)
        preview = service.calculate_preview(
            user_id=test_user_zero_balance.id,
            target_date=date.today(),
            actual_balance=Decimal("500.00"),
        )

        # Decimal("0") -> "0", Decimal("0.00") -> "0.00"
        assert Decimal(preview["expected_balance"]) == Decimal("0")
        assert preview["actual_balance"] == "500.00"
        assert preview["difference"] == "500.00"
        assert preview["is_positive"] is True
        assert "+500" in preview["explanation"]

    def test_preview_negative_difference(self, db_session, test_user_zero_balance):
        """Preview корректно рассчитывает отрицательную разницу."""
        # Добавляем доход
        income = Transaction(
            user_id=test_user_zero_balance.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date.today(),
        )
        db_session.add(income)
        db_session.commit()

        service = ReconciliationService(db_session)
        preview = service.calculate_preview(
            user_id=test_user_zero_balance.id,
            target_date=date.today(),
            actual_balance=Decimal("800.00"),
        )

        assert preview["difference"] == "-200.00"
        assert preview["is_positive"] is False
        assert "-200" in preview["explanation"]

    def test_preview_zero_difference(self, db_session, test_user_zero_balance):
        """Preview корректно обрабатывает нулевую разницу."""
        service = ReconciliationService(db_session)
        preview = service.calculate_preview(
            user_id=test_user_zero_balance.id,
            target_date=date.today(),
            actual_balance=Decimal("0"),
        )

        assert Decimal(preview["difference"]) == Decimal("0")
        assert "не требуется" in preview["explanation"]


class TestReconciliationServiceCreateAdjustment:
    """Тесты метода create_adjustment."""

    def test_create_positive_adjustment(
        self, db_session, test_user_zero_balance, seeded_categories
    ):
        """Создает положительную корректировку."""
        service = ReconciliationService(db_session)
        adjustment = service.create_adjustment(
            user_id=test_user_zero_balance.id,
            target_date=date.today(),
            actual_balance=Decimal("500.00"),
        )

        assert adjustment is not None
        assert adjustment.transaction_type == TransactionType.ADJUSTMENT
        assert adjustment.amount == Decimal("500.00")
        assert adjustment.category_id is not None

    def test_create_negative_adjustment(
        self, db_session, test_user_zero_balance, seeded_categories
    ):
        """Создает отрицательную корректировку."""
        # Добавляем доход
        income = Transaction(
            user_id=test_user_zero_balance.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date.today(),
        )
        db_session.add(income)
        db_session.commit()

        service = ReconciliationService(db_session)
        adjustment = service.create_adjustment(
            user_id=test_user_zero_balance.id,
            target_date=date.today(),
            actual_balance=Decimal("700.00"),
        )

        assert adjustment is not None
        assert adjustment.amount == Decimal("-300.00")

    def test_no_adjustment_when_balanced(
        self, db_session, test_user_zero_balance, seeded_categories
    ):
        """Не создает корректировку если баланс совпадает."""
        service = ReconciliationService(db_session)
        adjustment = service.create_adjustment(
            user_id=test_user_zero_balance.id,
            target_date=date.today(),
            actual_balance=Decimal("0"),
        )

        assert adjustment is None

    def test_raises_without_system_category(self, db_session, test_user_zero_balance):
        """Выбрасывает ошибку если системная категория не найдена."""
        service = ReconciliationService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_adjustment(
                user_id=test_user_zero_balance.id,
                target_date=date.today(),
                actual_balance=Decimal("100.00"),
            )

        assert "Коррекция" in str(exc_info.value)

    def test_custom_description(
        self, db_session, test_user_zero_balance, seeded_categories
    ):
        """Можно задать пользовательское описание."""
        service = ReconciliationService(db_session)
        adjustment = service.create_adjustment(
            user_id=test_user_zero_balance.id,
            target_date=date.today(),
            actual_balance=Decimal("100.00"),
            description="Мое описание",
        )

        assert adjustment is not None
        assert adjustment.description == "Мое описание"
