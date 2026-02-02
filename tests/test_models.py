"""Unit тесты для моделей базы данных.

Тестирование новых полей и свойств модели Transaction
для поддержки повторяющихся операций (recurring).
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.database import (
    Goal,
    GoalContribution,
    GoalStatus,
    Transaction,
    TransactionType,
    User,
)


class TestTransactionAnchorDay:
    """Тесты для property anchor_day."""

    def test_anchor_day_for_recurring(self, db_session, test_user):
        """anchor_day возвращает день месяца для recurring транзакции."""
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 15),
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add(transaction)
        db_session.commit()

        assert transaction.anchor_day == 15

    def test_anchor_day_for_non_recurring(self, db_session, test_user):
        """anchor_day возвращает None для обычной транзакции."""
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 20),
            description="Покупка",
            is_recurring=False,
        )
        db_session.add(transaction)
        db_session.commit()

        assert transaction.anchor_day is None

    def test_anchor_day_guard_clause_logs_error(self, db_session, test_user):
        """Guard clause логирует ошибку при is_recurring=True и date=None."""
        # Создаем транзакцию напрямую в памяти (без БД constraint)
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            is_recurring=True,
            recurring_period="monthly",
        )
        # Принудительно устанавливаем transaction_date=None
        transaction.transaction_date = None

        # Патчим loguru.logger напрямую (импортируется внутри метода)
        with patch("loguru.logger") as mock_logger:
            result = transaction.anchor_day

            assert result is None
            mock_logger.error.assert_called_once()
            error_message = mock_logger.error.call_args[0][0]
            assert "Data integrity issue" in error_message
            assert "is_recurring=True" in error_message


class TestTransactionIsException:
    """Тесты для property is_exception."""

    def test_is_exception_true_when_has_parent(self, db_session, test_user):
        """is_exception возвращает True если есть recurring_parent_id."""
        # Создаем шаблон
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 15),
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add(template)
        db_session.commit()

        # Создаем exception
        exception = Transaction(
            user_id=test_user.id,
            amount=Decimal("5500.00"),  # Измененная сумма
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 2, 15),
            description="Зарплата с премией",
            recurring_parent_id=template.id,
            original_date=date(2026, 2, 15),
        )
        db_session.add(exception)
        db_session.commit()

        assert exception.is_exception is True

    def test_is_exception_false_for_regular_transaction(self, db_session, test_user):
        """is_exception возвращает False для обычной транзакции."""
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 20),
            description="Покупка",
        )
        db_session.add(transaction)
        db_session.commit()

        assert transaction.is_exception is False


class TestTransactionRecurringRelationship:
    """Тесты для self-referential relationship parent/children."""

    def test_recurring_parent_relationship(self, db_session, test_user):
        """Проверка связи recurring_parent и recurring_exceptions."""
        # Создаем шаблон
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 15),
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add(template)
        db_session.commit()

        # Создаем exceptions
        exception1 = Transaction(
            user_id=test_user.id,
            amount=Decimal("5500.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 2, 15),
            description="Зарплата февраль",
            recurring_parent_id=template.id,
            original_date=date(2026, 2, 15),
        )
        exception2 = Transaction(
            user_id=test_user.id,
            amount=Decimal("0.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 3, 15),
            description="Пропущено",
            recurring_parent_id=template.id,
            original_date=date(2026, 3, 15),
            is_skipped=True,
        )
        db_session.add_all([exception1, exception2])
        db_session.commit()

        # Проверяем связи
        assert exception1.recurring_parent == template
        assert exception2.recurring_parent == template
        assert len(template.recurring_exceptions) == 2
        assert exception1 in template.recurring_exceptions
        assert exception2 in template.recurring_exceptions


class TestUniqueConstraintExceptionDate:
    """Тесты для UniqueConstraint на recurring_parent_id + original_date."""

    def test_unique_constraint_prevents_duplicate_exception(
        self, db_session, test_user
    ):
        """UniqueConstraint предотвращает создание двух exceptions на одну дату."""
        # Создаем шаблон
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 15),
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add(template)
        db_session.commit()

        # Первый exception
        exception1 = Transaction(
            user_id=test_user.id,
            amount=Decimal("5500.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 2, 15),
            description="Зарплата с премией",
            recurring_parent_id=template.id,
            original_date=date(2026, 2, 15),
        )
        db_session.add(exception1)
        db_session.commit()

        # Попытка создать дубликат на ту же original_date
        exception2 = Transaction(
            user_id=test_user.id,
            amount=Decimal("4500.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 2, 15),
            description="Дубликат",
            recurring_parent_id=template.id,
            original_date=date(2026, 2, 15),  # Та же дата!
        )
        db_session.add(exception2)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestTransactionTypeSavings:
    """Тесты для новых типов транзакций SAVINGS_RESERVE и SAVINGS_CONTRIBUTION."""

    def test_savings_reserve_type_exists(self):
        """TransactionType.SAVINGS_RESERVE существует и имеет корректное значение."""
        assert TransactionType.SAVINGS_RESERVE.value == "savings_reserve"

    def test_savings_contribution_type_exists(self):
        """TransactionType.SAVINGS_CONTRIBUTION существует и имеет значение."""
        assert TransactionType.SAVINGS_CONTRIBUTION.value == "savings_contribution"

    def test_savings_reserve_transaction(self, db_session, test_user):
        """Можно создать транзакцию типа SAVINGS_RESERVE."""
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("10000.00"),
            transaction_type=TransactionType.SAVINGS_RESERVE,
            transaction_date=date(2026, 2, 1),
            description="Резерв на цели",
        )
        db_session.add(transaction)
        db_session.commit()

        assert transaction.id is not None
        assert transaction.transaction_type == TransactionType.SAVINGS_RESERVE

    def test_savings_contribution_transaction(self, db_session, test_user):
        """Можно создать транзакцию типа SAVINGS_CONTRIBUTION."""
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.SAVINGS_CONTRIBUTION,
            transaction_date=date(2026, 2, 1),
            description="Взнос: Отпуск",
        )
        db_session.add(transaction)
        db_session.commit()

        assert transaction.id is not None
        assert transaction.transaction_type == TransactionType.SAVINGS_CONTRIBUTION


class TestUserReservationMode:
    """Тесты для полей User.reservation_mode и reservation_day."""

    def test_reservation_mode_default(self, db_session):
        """reservation_mode по умолчанию 'from_balance'."""
        user = User(email="test_res@example.com", name="Test Reservation")
        db_session.add(user)
        db_session.commit()

        assert user.reservation_mode == "from_balance"
        assert user.reservation_day is None

    def test_reservation_mode_fixed_date(self, db_session):
        """Можно установить режим fixed_date с днём месяца."""
        user = User(
            email="test_fixed@example.com",
            name="Test Fixed",
            reservation_mode="fixed_date",
            reservation_day=15,
        )
        db_session.add(user)
        db_session.commit()

        assert user.reservation_mode == "fixed_date"
        assert user.reservation_day == 15


class TestGoalContributionTransactionLink:
    """Тесты для GoalContribution.transaction_id FK."""

    def test_contribution_transaction_id_nullable(self, db_session, test_user):
        """transaction_id может быть NULL (взносы до интеграции)."""
        goal = Goal(
            user_id=test_user.id,
            name="Тестовая цель",
            target_amount=Decimal("100000.00"),
            target_date=date(2026, 12, 31),
            status=GoalStatus.ACTIVE,
        )
        db_session.add(goal)
        db_session.commit()

        contribution = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("5000.00"),
            contribution_date=date(2026, 2, 1),
            description="Без связи с транзакцией",
            transaction_id=None,
        )
        db_session.add(contribution)
        db_session.commit()

        assert contribution.id is not None
        assert contribution.transaction_id is None
        assert contribution.transaction is None

    def test_contribution_with_transaction(self, db_session, test_user):
        """Взнос может быть связан с транзакцией."""
        goal = Goal(
            user_id=test_user.id,
            name="Цель со связью",
            target_amount=Decimal("50000.00"),
            target_date=date(2026, 6, 30),
            status=GoalStatus.ACTIVE,
        )
        db_session.add(goal)
        db_session.commit()

        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.SAVINGS_CONTRIBUTION,
            transaction_date=date(2026, 2, 1),
            description="Взнос: Цель со связью",
        )
        db_session.add(transaction)
        db_session.commit()

        contribution = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("5000.00"),
            contribution_date=date(2026, 2, 1),
            description="Взнос со связью",
            transaction_id=transaction.id,
        )
        db_session.add(contribution)
        db_session.commit()

        assert contribution.transaction_id == transaction.id
        assert contribution.transaction == transaction

    # Note: тест SET NULL on delete пропущен — SQLite требует PRAGMA foreign_keys=ON
    # для работы ON DELETE SET NULL. В production с PostgreSQL/MySQL это работает.
