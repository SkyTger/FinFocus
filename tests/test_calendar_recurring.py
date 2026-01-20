"""Тесты интеграции CalendarService с recurring операциями."""

from datetime import date
from decimal import Decimal

from app.models.database import Transaction, TransactionType
from app.services.calendar_service import CalendarService
from app.services.recurring_service import RecurringService


class TestDailyBalancesExcludesTemplates:
    """Тесты: recurring шаблоны не должны влиять на баланс."""

    def test_template_not_counted_in_balance(self, db_session, test_user):
        """Recurring шаблон не учитывается в расчете баланса."""
        # Добавляем обычную транзакцию
        regular_txn = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 15),
            description="Обычный доход",
            is_recurring=False,
        )
        # Добавляем recurring шаблон (не должен учитываться)
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("100000.00"),  # Большая сумма
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 15),
            description="Шаблон зарплаты",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add_all([regular_txn, template])
        db_session.commit()

        service = CalendarService(db_session)
        result = service.calculate_daily_balances(
            test_user.id, date(2026, 1, 1), date(2026, 1, 31)
        )

        # Баланс = starting_balance + regular_txn = 10000 + 5000 = 15000
        # Шаблон НЕ должен влиять на баланс
        assert result[date(2026, 1, 15)] == Decimal("15000.00")
        assert result[date(2026, 1, 31)] == Decimal("15000.00")


class TestMonthSummaryExcludesTemplates:
    """Тесты: month_summary не включает recurring шаблоны."""

    def test_month_summary_excludes_templates(self, db_session, test_user):
        """get_month_summary не учитывает recurring шаблоны."""
        # Обычная транзакция
        regular_txn = Transaction(
            user_id=test_user.id,
            amount=Decimal("3000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 10),
            description="Обычный доход",
            is_recurring=False,
        )
        # Recurring шаблон
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("50000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 10),
            description="Шаблон",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add_all([regular_txn, template])
        db_session.commit()

        service = CalendarService(db_session)
        summary = service.get_month_summary(test_user.id, 2026, 1)

        # Только обычная транзакция должна быть учтена
        assert summary["total_income"] == Decimal("3000.00")


class TestYearSummaryExcludesTemplates:
    """Тесты: year_summary не включает recurring шаблоны."""

    def test_year_summary_excludes_templates(self, db_session, test_user):
        """get_year_summary не учитывает recurring шаблоны."""
        # Обычная транзакция
        regular_txn = Transaction(
            user_id=test_user.id,
            amount=Decimal("2000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 3, 15),
            description="Обычный расход",
            is_recurring=False,
        )
        # Recurring шаблон
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("99999.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 3, 15),
            description="Шаблон расходов",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add_all([regular_txn, template])
        db_session.commit()

        service = CalendarService(db_session)
        summary = service.get_year_summary(test_user.id, 2026)

        # Только обычная транзакция должна быть учтена
        assert summary["total_expense"] == Decimal("2000.00")


class TestGetAllTransactionsForPeriod:
    """Тесты для get_all_transactions_for_period."""

    def test_combines_regular_and_recurring(self, db_session, test_user):
        """Объединяет обычные транзакции и recurring instances."""
        # Обычная транзакция
        regular_txn = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 2, 10),
            description="Обычный доход",
            is_recurring=False,
        )
        # Recurring шаблон
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 2, 15),
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add_all([regular_txn, template])
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_all_transactions_for_period(
            test_user.id, date(2026, 2, 1), date(2026, 2, 28)
        )

        # Должны быть: обычная транзакция + виртуальный recurring
        all_txns = [txn for txns in result.values() for txn in txns]
        assert len(all_txns) == 2

        # Проверяем обычную транзакцию
        regular = [t for t in all_txns if not t["is_recurring"]]
        assert len(regular) == 1
        assert regular[0]["amount"] == "1000.00"
        assert regular[0]["is_virtual"] is False

        # Проверяем recurring instance
        recurring = [t for t in all_txns if t["is_recurring"]]
        assert len(recurring) == 1
        assert recurring[0]["amount"] == "5000.00"
        assert recurring[0]["is_virtual"] is True

    def test_exception_replaces_virtual(self, db_session, test_user):
        """Exception заменяет виртуальный экземпляр."""
        # Recurring шаблон
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

        # Создаем exception на февраль
        recurring_service = RecurringService(db_session)
        recurring_service.create_exception(
            template_id=template.id,
            original_date=date(2026, 2, 15),
            new_amount=Decimal("6000.00"),
            new_description="Зарплата с премией",
        )
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_all_transactions_for_period(
            test_user.id, date(2026, 2, 1), date(2026, 2, 28)
        )

        # Должен быть только exception, не виртуальный
        all_txns = [txn for txns in result.values() for txn in txns]
        assert len(all_txns) == 1

        txn = all_txns[0]
        assert txn["amount"] == "6000.00"
        assert txn["is_exception"] is True
        assert txn["is_virtual"] is False

    def test_skipped_not_returned(self, db_session, test_user):
        """Пропущенные экземпляры не возвращаются."""
        # Recurring шаблон
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

        # Пропускаем февральский экземпляр
        recurring_service = RecurringService(db_session)
        recurring_service.skip_instance(template.id, date(2026, 2, 15))
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_all_transactions_for_period(
            test_user.id, date(2026, 2, 1), date(2026, 2, 28)
        )

        # Ничего не должно вернуться
        all_txns = [txn for txns in result.values() for txn in txns]
        assert len(all_txns) == 0

    def test_without_recurring(self, db_session, test_user):
        """include_recurring=False возвращает только обычные транзакции."""
        # Обычная транзакция
        regular_txn = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 2, 10),
            description="Обычный доход",
            is_recurring=False,
        )
        # Recurring шаблон
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 2, 15),
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add_all([regular_txn, template])
        db_session.commit()

        service = CalendarService(db_session)
        result = service.get_all_transactions_for_period(
            test_user.id,
            date(2026, 2, 1),
            date(2026, 2, 28),
            include_recurring=False,
        )

        # Должна быть только обычная транзакция
        all_txns = [txn for txns in result.values() for txn in txns]
        assert len(all_txns) == 1
        assert all_txns[0]["amount"] == "1000.00"


class TestExceptionsExcludedFromRegularCalculations:
    """Тесты: exceptions не дублируются в обычных расчетах."""

    def test_exceptions_excluded_from_balance(self, db_session, test_user):
        """Exceptions не учитываются дважды в расчете баланса."""
        # Recurring шаблон
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
        recurring_service = RecurringService(db_session)
        recurring_service.create_exception(
            template_id=template.id,
            original_date=date(2026, 2, 15),
            new_amount=Decimal("6000.00"),
        )
        db_session.commit()

        service = CalendarService(db_session)

        # calculate_daily_balances должен исключать exceptions
        # (т.к. they should be handled through recurring service)
        result = service.calculate_daily_balances(
            test_user.id, date(2026, 2, 1), date(2026, 2, 28)
        )

        # Баланс должен быть только starting_balance (10000),
        # без учета exception (он должен быть исключен)
        assert result[date(2026, 2, 15)] == Decimal("10000.00")
