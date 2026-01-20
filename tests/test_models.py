"""Unit тесты для моделей базы данных.

Тестирование новых полей и свойств модели Transaction
для поддержки повторяющихся операций (recurring).
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.database import Transaction, TransactionType


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
