"""Тесты для CalendarService."""

from datetime import date
from decimal import Decimal

import pytest

from app.models.database import Transaction, TransactionType
from app.services.calendar_service import CalendarService


class TestGetStartingBalance:
    """Тесты для _get_starting_balance."""

    def test_user_with_starting_balance(self, db_session, test_user):
        """Пользователь с starting_balance=10000 → возвращает Decimal('10000')."""
        service = CalendarService(db_session)

        result = service._get_starting_balance(test_user.id)

        assert result == Decimal("10000.00")

    def test_user_not_exists(self, db_session):
        """Пользователь не существует → возвращает Decimal('0')."""
        service = CalendarService(db_session)

        result = service._get_starting_balance(9999)  # несуществующий ID

        assert result == Decimal("0")

    def test_user_with_zero_balance(self, db_session, test_user_zero_balance):
        """Пользователь с starting_balance=0 → возвращает Decimal('0')."""
        service = CalendarService(db_session)

        result = service._get_starting_balance(test_user_zero_balance.id)

        assert result == Decimal("0")


class TestCalculateDailyBalances:
    """Тесты для calculate_daily_balances."""

    def test_empty_period_no_transactions(self, db_session, test_user):
        """Пустой период без транзакций → все дни равны starting_balance."""
        service = CalendarService(db_session)
        start = date(2026, 1, 1)
        end = date(2026, 1, 3)

        result = service.calculate_daily_balances(test_user.id, start, end)

        assert len(result) == 3
        assert result[date(2026, 1, 1)] == Decimal("10000.00")
        assert result[date(2026, 1, 2)] == Decimal("10000.00")
        assert result[date(2026, 1, 3)] == Decimal("10000.00")

    def test_single_income_transaction(self, db_session, test_user):
        """Одна INCOME транзакция → баланс увеличивается."""
        # Добавляем транзакцию
        txn = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 2),
            description="Зарплата",
        )
        db_session.add(txn)
        db_session.commit()

        service = CalendarService(db_session)
        start = date(2026, 1, 1)
        end = date(2026, 1, 3)

        result = service.calculate_daily_balances(test_user.id, start, end)

        assert result[date(2026, 1, 1)] == Decimal("10000.00")  # до транзакции
        assert result[date(2026, 1, 2)] == Decimal("15000.00")  # после INCOME
        assert result[date(2026, 1, 3)] == Decimal("15000.00")  # баланс сохраняется

    def test_single_expense_transaction(self, db_session, test_user):
        """Одна EXPENSE транзакция → баланс уменьшается."""
        txn = Transaction(
            user_id=test_user.id,
            amount=Decimal("3000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 2),
            description="Покупка",
        )
        db_session.add(txn)
        db_session.commit()

        service = CalendarService(db_session)
        start = date(2026, 1, 1)
        end = date(2026, 1, 3)

        result = service.calculate_daily_balances(test_user.id, start, end)

        assert result[date(2026, 1, 1)] == Decimal("10000.00")
        assert result[date(2026, 1, 2)] == Decimal("7000.00")  # 10000 - 3000
        assert result[date(2026, 1, 3)] == Decimal("7000.00")

    def test_transfer_transaction_does_not_affect_balance(self, db_session, test_user):
        """КРИТИЧНО: TRANSFER транзакция НЕ влияет на баланс."""
        txn = Transaction(
            user_id=test_user.id,
            amount=Decimal("2000.00"),
            transaction_type=TransactionType.TRANSFER,
            transaction_date=date(2026, 1, 2),
            description="Перевод между счетами",
        )
        db_session.add(txn)
        db_session.commit()

        service = CalendarService(db_session)
        start = date(2026, 1, 1)
        end = date(2026, 1, 3)

        result = service.calculate_daily_balances(test_user.id, start, end)

        # TRANSFER не должен изменить баланс
        assert result[date(2026, 1, 1)] == Decimal("10000.00")
        assert result[date(2026, 1, 2)] == Decimal("10000.00")
        assert result[date(2026, 1, 3)] == Decimal("10000.00")

    def test_start_date_after_end_date_raises_error(self, db_session, test_user):
        """start_date > end_date → ValueError."""
        service = CalendarService(db_session)
        start = date(2026, 1, 5)
        end = date(2026, 1, 1)

        with pytest.raises(ValueError) as exc_info:
            service.calculate_daily_balances(test_user.id, start, end)

        assert "start_date" in str(exc_info.value)
        assert "end_date" in str(exc_info.value)

    def test_multiple_transactions_same_day(self, db_session, test_user):
        """Несколько транзакций в один день суммируются корректно."""
        # Доход
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("5000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 2),
            )
        )
        # Расход
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("2000.00"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date(2026, 1, 2),
            )
        )
        db_session.commit()

        service = CalendarService(db_session)
        result = service.calculate_daily_balances(
            test_user.id, date(2026, 1, 1), date(2026, 1, 3)
        )

        # 10000 + 5000 - 2000 = 13000
        assert result[date(2026, 1, 2)] == Decimal("13000.00")

    def test_transactions_before_period_affect_starting_balance(
        self, db_session, test_user
    ):
        """Транзакции до периода влияют на начальный баланс периода."""
        # Транзакция ДО периода
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("3000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2025, 12, 25),  # до периода
            )
        )
        db_session.commit()

        service = CalendarService(db_session)
        result = service.calculate_daily_balances(
            test_user.id, date(2026, 1, 1), date(2026, 1, 2)
        )

        # 10000 (starting) + 3000 (до периода) = 13000
        assert result[date(2026, 1, 1)] == Decimal("13000.00")


class TestGetTransactionsByDate:
    """Тесты для get_transactions_by_date."""

    def test_returns_all_transaction_types(self, db_session, test_user):
        """Метод возвращает ВСЕ типы транзакций как dict со строковыми типами."""
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("1000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 1),
            )
        )
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("500.00"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date(2026, 1, 1),
            )
        )
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("200.00"),
                transaction_type=TransactionType.TRANSFER,
                transaction_date=date(2026, 1, 1),
            )
        )
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_transactions_by_date(
            test_user.id, date(2026, 1, 1), date(2026, 1, 1)
        )

        assert len(result[date(2026, 1, 1)]) == 3
        # Проверяем строковые типы вместо Enum
        types = {t["transaction_type"] for t in result[date(2026, 1, 1)]}
        assert "income" in types
        assert "expense" in types
        assert "transfer" in types

    def test_groups_by_date(self, db_session, test_user):
        """Транзакции группируются по датам."""
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("1000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 1),
            )
        )
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("2000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 2),
            )
        )
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_transactions_by_date(
            test_user.id, date(2026, 1, 1), date(2026, 1, 3)
        )

        assert len(result[date(2026, 1, 1)]) == 1
        assert len(result[date(2026, 1, 2)]) == 1
        assert date(2026, 1, 3) not in result  # нет транзакций

    def test_transaction_info_structure(self, db_session, test_user):
        """Возвращаемый dict имеет корректную структуру TransactionInfo."""
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("1000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 1),
                description="Тестовая транзакция",
            )
        )
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_transactions_by_date(
            test_user.id, date(2026, 1, 1), date(2026, 1, 1)
        )

        txn = result[date(2026, 1, 1)][0]
        # Проверяем наличие всех ключей
        assert "id" in txn
        assert "transaction_type" in txn
        assert "amount" in txn
        assert "description" in txn
        # Проверяем типы значений
        assert isinstance(txn["id"], int)
        assert isinstance(txn["transaction_type"], str)
        assert isinstance(txn["amount"], str)
        assert txn["transaction_type"] == "income"
        assert txn["amount"] == "1000.00"
        assert txn["description"] == "Тестовая транзакция"

    def test_transaction_info_with_none_description(self, db_session, test_user):
        """TransactionInfo корректно обрабатывает None description."""
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("500.00"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date(2026, 1, 1),
                description=None,
            )
        )
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_transactions_by_date(
            test_user.id, date(2026, 1, 1), date(2026, 1, 1)
        )

        txn = result[date(2026, 1, 1)][0]
        assert txn["description"] is None


class TestGetMonthSummary:
    """Тесты для get_month_summary."""

    def test_month_with_income_and_expense(self, db_session, test_user):
        """Месяц с INCOME и EXPENSE → корректные суммы."""
        # Доходы
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("50000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 5),
            )
        )
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("10000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 15),
            )
        )
        # Расходы
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("20000.00"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date(2026, 1, 10),
            )
        )
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_month_summary(test_user.id, 2026, 1)

        assert result["total_income"] == Decimal("60000.00")
        assert result["total_expense"] == Decimal("20000.00")
        assert result["start_balance"] == Decimal("10000.00")  # starting_balance
        # end_balance = 10000 + 60000 - 20000 = 50000
        assert result["end_balance"] == Decimal("50000.00")
        assert result["month"] == 1
        assert result["year"] == 2026

    def test_transfer_not_counted_in_summary(self, db_session, test_user):
        """TRANSFER не учитывается в total_income/total_expense."""
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("5000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 5),
            )
        )
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("100000.00"),  # большая сумма
                transaction_type=TransactionType.TRANSFER,
                transaction_date=date(2026, 1, 10),
            )
        )
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_month_summary(test_user.id, 2026, 1)

        # TRANSFER не должен влиять на суммы
        assert result["total_income"] == Decimal("5000.00")
        assert result["total_expense"] == Decimal("0")

    def test_empty_month(self, db_session, test_user):
        """Пустой месяц без транзакций."""
        service = CalendarService(db_session)
        result = service.get_month_summary(test_user.id, 2026, 2)  # февраль

        assert result["total_income"] == Decimal("0")
        assert result["total_expense"] == Decimal("0")
        assert result["start_balance"] == Decimal("10000.00")
        assert result["end_balance"] == Decimal("10000.00")


class TestGetBalanceOnDate:
    """Тесты для get_balance_on_date."""

    def test_balance_includes_target_date(self, db_session, test_user):
        """Баланс включает транзакции на указанную дату."""
        # Arrange
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("5000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 15),
            )
        )
        db_session.commit()

        service = CalendarService(db_session)

        # Act
        result = service.get_balance_on_date(test_user.id, date(2026, 1, 15))

        # Assert - starting_balance (10000) + 5000 = 15000
        assert result == Decimal("15000.00")

    def test_balance_excludes_future_transactions(self, db_session, test_user):
        """Баланс не включает транзакции после указанной даты."""
        # Arrange
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("5000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 20),
            )
        )
        db_session.commit()

        service = CalendarService(db_session)

        # Act
        result = service.get_balance_on_date(test_user.id, date(2026, 1, 15))

        # Assert - только starting_balance, транзакция в будущем
        assert result == Decimal("10000.00")


class TestGetYearSummary:
    """Тесты для get_year_summary."""

    def test_aggregates_full_year(self, db_session, test_user):
        """Агрегирует транзакции за весь год."""
        # Arrange
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("10000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 15),
            )
        )
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("5000.00"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date(2026, 6, 15),
            )
        )
        db_session.commit()

        service = CalendarService(db_session)

        # Act
        result = service.get_year_summary(test_user.id, 2026)

        # Assert
        assert result["total_income"] == Decimal("10000.00")
        assert result["total_expense"] == Decimal("5000.00")
        assert result["year"] == 2026

    def test_empty_year_returns_zeros(self, db_session, test_user):
        """Пустой год возвращает нули."""
        service = CalendarService(db_session)

        result = service.get_year_summary(test_user.id, 2025)

        assert result["total_income"] == Decimal("0")
        assert result["total_expense"] == Decimal("0")


class TestCalendarServiceAdjustment:
    """Тесты обработки ADJUSTMENT в CalendarService."""

    def test_adjustment_positive_increases_balance(self, db_session, test_user):
        """Положительный ADJUSTMENT увеличивает баланс."""
        adjustment = Transaction(
            user_id=test_user.id,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date(2026, 1, 15),
        )
        db_session.add(adjustment)
        db_session.commit()

        service = CalendarService(db_session)
        balance = service.get_balance_on_date(test_user.id, date(2026, 1, 15))

        # starting_balance (10000) + adjustment (500) = 10500
        assert balance == Decimal("10500.00")

    def test_adjustment_negative_decreases_balance(self, db_session, test_user):
        """Отрицательный ADJUSTMENT уменьшает баланс."""
        # Сначала доход
        income = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 10),
        )
        # Затем отрицательная корректировка
        adjustment = Transaction(
            user_id=test_user.id,
            amount=Decimal("-300.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date(2026, 1, 15),
        )
        db_session.add_all([income, adjustment])
        db_session.commit()

        service = CalendarService(db_session)
        balance = service.get_balance_on_date(test_user.id, date(2026, 1, 15))

        # starting_balance (10000) + income (1000) + adjustment (-300) = 10700
        assert balance == Decimal("10700.00")

    def test_adjustment_not_in_month_summary_totals(self, db_session, test_user):
        """ADJUSTMENT не учитывается в total_income/total_expense."""
        income = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 10),
        )
        adjustment = Transaction(
            user_id=test_user.id,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date(2026, 1, 15),
        )
        db_session.add_all([income, adjustment])
        db_session.commit()

        service = CalendarService(db_session)
        summary = service.get_month_summary(test_user.id, 2026, 1)

        # ADJUSTMENT не должен увеличивать total_income
        assert summary["total_income"] == Decimal("1000.00")
        assert summary["total_expense"] == Decimal("0")

    def test_adjustment_affects_daily_balance(self, db_session, test_user):
        """ADJUSTMENT влияет на ежедневный баланс в calculate_daily_balances."""
        adjustment = Transaction(
            user_id=test_user.id,
            amount=Decimal("200.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date(2026, 1, 2),
        )
        db_session.add(adjustment)
        db_session.commit()

        service = CalendarService(db_session)
        result = service.calculate_daily_balances(
            test_user.id, date(2026, 1, 1), date(2026, 1, 3)
        )

        assert result[date(2026, 1, 1)] == Decimal("10000.00")
        assert result[date(2026, 1, 2)] == Decimal("10200.00")  # +200 adjustment
        assert result[date(2026, 1, 3)] == Decimal("10200.00")

    def test_adjustment_not_in_year_summary_totals(self, db_session, test_user):
        """ADJUSTMENT не учитывается в total_income/total_expense годовой сводки."""
        income = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 3, 15),
        )
        adjustment = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date(2026, 6, 15),
        )
        db_session.add_all([income, adjustment])
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_year_summary(test_user.id, 2026)

        # ADJUSTMENT не должен увеличивать total_income
        assert result["total_income"] == Decimal("5000.00")
        assert result["total_expense"] == Decimal("0")


class TestCalendarServiceCategoryFields:
    """Тесты category fields в TransactionInfo."""

    def test_transaction_info_includes_category(self, db_session, test_user):
        """TransactionInfo включает category_id и category_name."""
        from app.models.database import Category

        category = Category(name="Еда", type="expense", icon="bi-cart")
        db_session.add(category)
        db_session.flush()

        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=category.id,
        )
        db_session.add(transaction)
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_transactions_by_date(
            test_user.id, date(2026, 1, 15), date(2026, 1, 15)
        )

        assert date(2026, 1, 15) in result
        tx_info = result[date(2026, 1, 15)][0]
        assert tx_info["category_id"] == category.id
        assert tx_info["category_name"] == "Еда"

    def test_transaction_info_without_category(self, db_session, test_user):
        """TransactionInfo корректно обрабатывает отсутствие категории."""
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=None,
        )
        db_session.add(transaction)
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_transactions_by_date(
            test_user.id, date(2026, 1, 15), date(2026, 1, 15)
        )

        tx_info = result[date(2026, 1, 15)][0]
        assert tx_info["category_id"] is None
        assert tx_info["category_name"] is None

    def test_get_all_transactions_includes_category(self, db_session, test_user):
        """get_all_transactions_for_period включает category fields."""
        from app.models.database import Category

        category = Category(name="Транспорт", type="expense", icon="bi-car-front")
        db_session.add(category)
        db_session.flush()

        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("250.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 20),
            category_id=category.id,
        )
        db_session.add(transaction)
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_all_transactions_for_period(
            test_user.id,
            date(2026, 1, 20),
            date(2026, 1, 20),
            include_recurring=False,
        )

        assert date(2026, 1, 20) in result
        tx_info = result[date(2026, 1, 20)][0]
        assert tx_info["category_id"] == category.id
        assert tx_info["category_name"] == "Транспорт"

    def test_adjustment_in_transactions_by_date(self, db_session, test_user):
        """ADJUSTMENT транзакции отображаются в get_transactions_by_date."""
        adjustment = Transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date(2026, 1, 15),
            description="Сверка баланса",
        )
        db_session.add(adjustment)
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_transactions_by_date(
            test_user.id, date(2026, 1, 15), date(2026, 1, 15)
        )

        assert date(2026, 1, 15) in result
        tx_info = result[date(2026, 1, 15)][0]
        assert tx_info["transaction_type"] == "adjustment"
        assert tx_info["amount"] == "100.00"
        assert tx_info["description"] == "Сверка баланса"
