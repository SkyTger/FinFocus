"""Тесты для модели Category и TransactionType.ADJUSTMENT."""

from decimal import Decimal
from datetime import date

from app.models.database import Category, Transaction, TransactionType


class TestCategoryModel:
    """Тесты модели Category."""

    def test_create_category(self, db_session):
        """Категория создается с корректными полями."""
        category = Category(
            name="Тестовая",
            icon="bi-test",
            type="expense",
            is_system=False,
            sort_order=999,
        )
        db_session.add(category)
        db_session.flush()

        assert category.id is not None
        assert category.name == "Тестовая"
        assert category.icon == "bi-test"
        assert category.type == "expense"
        assert category.is_system is False

    def test_category_default_values(self, db_session):
        """Категория имеет корректные значения по умолчанию."""
        category = Category(name="Минимум", type="income")
        db_session.add(category)
        db_session.flush()

        assert category.icon == "bi-tag"
        assert category.is_system is False
        assert category.sort_order == 0

    def test_category_repr(self, db_session):
        """Проверка строкового представления категории."""
        category = Category(name="Тест", type="expense")
        db_session.add(category)
        db_session.flush()

        repr_str = repr(category)
        assert "Category" in repr_str
        assert "Тест" in repr_str
        assert "expense" in repr_str


class TestTransactionCategoryRelation:
    """Тесты связи Transaction -> Category."""

    def test_transaction_with_category(self, db_session, test_user):
        """Транзакция может иметь категорию."""
        category = Category(name="Еда", type="expense")
        db_session.add(category)
        db_session.flush()

        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=category.id,
        )
        db_session.add(transaction)
        db_session.flush()

        assert transaction.category_id == category.id
        assert transaction.category_rel.name == "Еда"

    def test_transaction_without_category(self, db_session, test_user):
        """Транзакция может быть без категории (nullable)."""
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=None,
        )
        db_session.add(transaction)
        db_session.flush()

        assert transaction.category_id is None
        assert transaction.category_rel is None

    def test_category_has_transactions(self, db_session, test_user):
        """Категория содержит список связанных транзакций."""
        category = Category(name="Транспорт", type="expense")
        db_session.add(category)
        db_session.flush()

        tx1 = Transaction(
            user_id=test_user.id,
            amount=Decimal("50.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=category.id,
        )
        tx2 = Transaction(
            user_id=test_user.id,
            amount=Decimal("75.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=category.id,
        )
        db_session.add_all([tx1, tx2])
        db_session.flush()

        assert len(category.transactions) == 2


class TestTransactionTypeAdjustment:
    """Тесты TransactionType.ADJUSTMENT."""

    def test_adjustment_type_exists(self):
        """ADJUSTMENT существует в TransactionType."""
        assert hasattr(TransactionType, "ADJUSTMENT")
        assert TransactionType.ADJUSTMENT.value == "adjustment"

    def test_create_adjustment_transaction(self, db_session, test_user):
        """Можно создать транзакцию типа ADJUSTMENT."""
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("-500.00"),  # Отрицательная корректировка
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today(),
            description="Сверка баланса",
        )
        db_session.add(transaction)
        db_session.flush()

        assert transaction.transaction_type == TransactionType.ADJUSTMENT
        assert transaction.amount == Decimal("-500.00")

    def test_positive_adjustment(self, db_session, test_user):
        """Можно создать положительную корректировку."""
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("200.00"),  # Положительная корректировка
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today(),
            description="Найдены неучтенные средства",
        )
        db_session.add(transaction)
        db_session.flush()

        assert transaction.transaction_type == TransactionType.ADJUSTMENT
        assert transaction.amount == Decimal("200.00")
