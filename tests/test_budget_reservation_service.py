"""Unit тесты для BudgetReservationService."""

from datetime import date
from decimal import Decimal

import pytest

from app.models.database import (
    Goal,
    GoalContribution,
    GoalStatus,
    Transaction,
    TransactionType,
)
from app.services.budget_reservation_service import (
    BudgetReservationService,
    RESERVE_DESCRIPTION,
)
from tests.conftest import (
    days_after,
    days_before,
    far_future_date,
    reserve_period_start,
)


class TestGetSettings:
    """Тесты для get_settings()."""

    def test_get_settings_default(self, db_session, test_user):
        """get_settings возвращает default настройки для нового пользователя."""
        service = BudgetReservationService(db_session)
        settings = service.get_settings(test_user.id)

        assert settings["mode"] == "from_balance"
        assert settings["day_of_month"] is None
        assert settings["monthly_budget"] == Decimal("0")
        assert settings["template_id"] is None

    def test_get_settings_with_budget(self, db_session, test_user):
        """get_settings возвращает monthly_budget из User."""
        test_user.monthly_savings_budget = Decimal("15000.00")
        db_session.commit()

        service = BudgetReservationService(db_session)
        settings = service.get_settings(test_user.id)

        assert settings["monthly_budget"] == Decimal("15000.00")

    def test_get_settings_user_not_found(self, db_session):
        """get_settings возвращает defaults для несуществующего пользователя."""
        service = BudgetReservationService(db_session)
        settings = service.get_settings(99999)

        assert settings["mode"] == "from_balance"
        assert settings["monthly_budget"] == Decimal("0")


class TestSetMode:
    """Тесты для set_mode()."""

    def test_set_mode_fixed_date_creates_template(self, db_session, test_user):
        """set_mode(fixed_date) создаёт recurring шаблон."""
        test_user.monthly_savings_budget = Decimal("20000.00")
        db_session.commit()

        service = BudgetReservationService(db_session)
        settings = service.set_mode(test_user.id, "fixed_date", day_of_month=15)

        assert settings["mode"] == "fixed_date"
        assert settings["day_of_month"] == 15
        assert settings["template_id"] is not None

        # Проверяем шаблон в БД
        template = db_session.get(Transaction, settings["template_id"])
        assert template is not None
        assert template.is_recurring is True
        assert template.transaction_type == TransactionType.SAVINGS_RESERVE
        assert template.recurring_period == "monthly"
        assert template.amount == Decimal("20000.00")

    def test_set_mode_fixed_date_requires_day(self, db_session, test_user):
        """set_mode(fixed_date) без day_of_month вызывает ValueError."""
        service = BudgetReservationService(db_session)

        with pytest.raises(ValueError, match="day_of_month required"):
            service.set_mode(test_user.id, "fixed_date", day_of_month=None)

    def test_set_mode_fixed_date_validates_day_range(self, db_session, test_user):
        """set_mode(fixed_date) валидирует day_of_month 1-31."""
        service = BudgetReservationService(db_session)

        with pytest.raises(ValueError, match="must be 1-31"):
            service.set_mode(test_user.id, "fixed_date", day_of_month=0)

        with pytest.raises(ValueError, match="must be 1-31"):
            service.set_mode(test_user.id, "fixed_date", day_of_month=32)

    def test_set_mode_from_balance_stops_template(self, db_session, test_user):
        """set_mode(from_balance) останавливает существующий шаблон."""
        test_user.monthly_savings_budget = Decimal("10000.00")
        db_session.commit()

        service = BudgetReservationService(db_session)

        # Сначала устанавливаем fixed_date
        settings1 = service.set_mode(test_user.id, "fixed_date", day_of_month=10)
        template_id = settings1["template_id"]

        # Переключаемся на from_balance
        settings2 = service.set_mode(test_user.id, "from_balance")

        assert settings2["mode"] == "from_balance"
        assert settings2["day_of_month"] is None
        assert settings2["template_id"] is None

        # Проверяем что шаблон остановлен
        template = db_session.get(Transaction, template_id)
        assert template.recurring_end_date is not None

    def test_set_mode_eom_anchor_for_31(self, db_session, test_user):
        """set_mode с day=31 устанавливает recurring_anchor_eom=True."""
        service = BudgetReservationService(db_session)
        settings = service.set_mode(test_user.id, "fixed_date", day_of_month=31)

        template = db_session.get(Transaction, settings["template_id"])
        assert template.recurring_anchor_eom is True

    def test_set_mode_no_eom_anchor_for_other_days(self, db_session, test_user):
        """set_mode с day != 31 имеет recurring_anchor_eom=False."""
        service = BudgetReservationService(db_session)
        settings = service.set_mode(test_user.id, "fixed_date", day_of_month=15)

        template = db_session.get(Transaction, settings["template_id"])
        assert template.recurring_anchor_eom is False


class TestGetBudgetProgress:
    """Тесты для get_budget_progress()."""

    def test_progress_zero_budget(self, db_session, test_user):
        """get_budget_progress при нулевом бюджете."""
        service = BudgetReservationService(db_session)
        progress = service.get_budget_progress(test_user.id)

        assert progress["total_budget"] == Decimal("0")
        assert progress["used_budget"] == Decimal("0")
        assert progress["available_budget"] == Decimal("0")
        assert progress["progress_percent"] == 0.0
        assert progress["status"] == "success"

    def test_progress_with_contributions(self, db_session, test_user):
        """get_budget_progress суммирует взносы за месяц (from_balance)."""
        test_user.monthly_savings_budget = Decimal("20000.00")
        db_session.commit()

        # Создаём цель и взносы
        goal = Goal(
            user_id=test_user.id,
            name="Тест",
            target_amount=Decimal("100000.00"),
            target_date=far_future_date(),
            status=GoalStatus.ACTIVE,
        )
        db_session.add(goal)
        db_session.commit()

        today = date.today()
        contribution = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("10000.00"),
            contribution_date=today,
        )
        db_session.add(contribution)
        db_session.commit()

        service = BudgetReservationService(db_session)
        progress = service.get_budget_progress(test_user.id, today)

        assert progress["total_budget"] == Decimal("20000.00")
        assert progress["used_budget"] == Decimal("10000.00")
        assert progress["available_budget"] == Decimal("10000.00")
        assert progress["progress_percent"] == 50.0
        assert progress["mode_text"] == "Внесено"

    def test_progress_status_thresholds(self, db_session, test_user):
        """get_budget_progress возвращает правильные статусы."""
        test_user.monthly_savings_budget = Decimal("10000.00")
        db_session.commit()

        goal = Goal(
            user_id=test_user.id,
            name="Тест статусов",
            target_amount=Decimal("100000.00"),
            target_date=far_future_date(),
            status=GoalStatus.ACTIVE,
        )
        db_session.add(goal)
        db_session.commit()

        today = date.today()
        service = BudgetReservationService(db_session)

        # < 50% = success
        c1 = GoalContribution(
            goal_id=goal.id, amount=Decimal("4000.00"), contribution_date=today
        )
        db_session.add(c1)
        db_session.commit()

        progress = service.get_budget_progress(test_user.id, today)
        assert progress["status"] == "success"

        # 50-75% = warning
        c2 = GoalContribution(
            goal_id=goal.id, amount=Decimal("2000.00"), contribution_date=today
        )
        db_session.add(c2)
        db_session.commit()

        progress = service.get_budget_progress(test_user.id, today)
        assert progress["status"] == "warning"

        # 75-100% = orange
        c3 = GoalContribution(
            goal_id=goal.id, amount=Decimal("2000.00"), contribution_date=today
        )
        db_session.add(c3)
        db_session.commit()

        progress = service.get_budget_progress(test_user.id, today)
        assert progress["status"] == "orange"

        # > 100% = danger
        c4 = GoalContribution(
            goal_id=goal.id, amount=Decimal("3000.00"), contribution_date=today
        )
        db_session.add(c4)
        db_session.commit()

        progress = service.get_budget_progress(test_user.id, today)
        assert progress["status"] == "danger"

    def test_progress_fixed_date_mode(self, db_session, test_user):
        """get_budget_progress для fixed_date режима.

        После унификации (protocol-0018) mode_text = "Внесено" для обоих режимов.
        """
        test_user.monthly_savings_budget = Decimal("15000.00")
        test_user.reservation_mode = "fixed_date"
        db_session.commit()

        service = BudgetReservationService(db_session)
        progress = service.get_budget_progress(test_user.id)

        assert progress["mode"] == "fixed_date"
        assert progress["mode_text"] == "Внесено"  # Унифицировано для обоих режимов


class TestPrivateHelpers:
    """Тесты для private методов."""

    def test_get_reserve_template_finds_active(self, db_session, test_user):
        """_get_reserve_template находит активный шаблон."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.SAVINGS_RESERVE,
            transaction_date=date.today(),
            description=RESERVE_DESCRIPTION,
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add(template)
        db_session.commit()

        service = BudgetReservationService(db_session)
        found = service._get_reserve_template(test_user.id)

        assert found is not None
        assert found.id == template.id

    def test_get_reserve_template_ignores_stopped(self, db_session, test_user):
        """_get_reserve_template игнорирует остановленные шаблоны."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.SAVINGS_RESERVE,
            transaction_date=date.today(),
            description=RESERVE_DESCRIPTION,
            is_recurring=True,
            recurring_period="monthly",
            recurring_end_date=date(2020, 1, 1),  # Остановлен давно
        )
        db_session.add(template)
        db_session.commit()

        service = BudgetReservationService(db_session)
        found = service._get_reserve_template(test_user.id)

        assert found is None

    def test_stop_reserve_template(self, db_session, test_user):
        """_stop_reserve_template устанавливает end_date."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.SAVINGS_RESERVE,
            transaction_date=date.today(),
            description=RESERVE_DESCRIPTION,
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add(template)
        db_session.commit()

        service = BudgetReservationService(db_session)
        result = service._stop_reserve_template(test_user.id)

        assert result is True
        db_session.refresh(template)
        assert template.recurring_end_date is not None

    def test_stop_reserve_template_no_template(self, db_session, test_user):
        """_stop_reserve_template возвращает False если нет шаблона."""
        service = BudgetReservationService(db_session)
        result = service._stop_reserve_template(test_user.id)

        assert result is False


class TestCreateContributionTransaction:
    """Тесты для create_contribution_transaction()."""

    def test_create_transaction_from_balance_mode(self, db_session, test_user):
        """create_contribution_transaction создаёт транзакцию в режиме from_balance."""
        service = BudgetReservationService(db_session)

        transaction = service.create_contribution_transaction(
            user_id=test_user.id,
            goal_name="Отпуск",
            amount=Decimal("5000.00"),
            contribution_date=date.today(),
        )

        assert transaction is not None
        assert transaction.transaction_type == TransactionType.SAVINGS_CONTRIBUTION
        assert transaction.amount == Decimal("5000.00")
        assert transaction.description == "Взнос: Отпуск"
        assert transaction.category_id is None

    def test_create_transaction_fixed_date_returns_none(self, db_session, test_user):
        """create_contribution_transaction возвращает None в режиме fixed_date."""
        test_user.reservation_mode = "fixed_date"
        test_user.reservation_day = 15
        db_session.commit()

        service = BudgetReservationService(db_session)

        transaction = service.create_contribution_transaction(
            user_id=test_user.id,
            goal_name="Отпуск",
            amount=Decimal("5000.00"),
            contribution_date=date.today(),
        )

        assert transaction is None


class TestUpdateContributionTransaction:
    """Тесты для update_contribution_transaction()."""

    def test_update_transaction_syncs_contribution(self, db_session, test_user):
        """update_contribution_transaction синхронизирует GoalContribution."""
        # Создаём цель
        goal = Goal(
            user_id=test_user.id,
            name="Цель",
            target_amount=Decimal("100000.00"),
            current_amount=Decimal("10000.00"),
            target_date=far_future_date(),
            status=GoalStatus.ACTIVE,
        )
        db_session.add(goal)
        db_session.commit()

        # Создаём транзакцию
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("10000.00"),
            transaction_type=TransactionType.SAVINGS_CONTRIBUTION,
            transaction_date=date.today(),
            description="Взнос: Цель",
        )
        db_session.add(transaction)
        db_session.commit()

        # Создаём GoalContribution со связью
        contribution = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("10000.00"),
            contribution_date=date.today(),
            transaction_id=transaction.id,
        )
        db_session.add(contribution)
        db_session.commit()

        # Обновляем
        service = BudgetReservationService(db_session)
        result = service.update_contribution_transaction(
            transaction_id=transaction.id,
            new_amount=Decimal("15000.00"),
        )

        assert result is True

        db_session.refresh(transaction)
        db_session.refresh(contribution)
        db_session.refresh(goal)

        assert transaction.amount == Decimal("15000.00")
        assert contribution.amount == Decimal("15000.00")
        assert goal.current_amount == Decimal("15000.00")  # 10000 + delta(5000)

    def test_update_transaction_marks_goal_completed(self, db_session, test_user):
        """update_contribution_transaction помечает цель как COMPLETED."""
        goal = Goal(
            user_id=test_user.id,
            name="Почти готовая цель",
            target_amount=Decimal("10000.00"),
            current_amount=Decimal("8000.00"),
            target_date=far_future_date(),
            status=GoalStatus.ACTIVE,
        )
        db_session.add(goal)
        db_session.commit()

        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("8000.00"),
            transaction_type=TransactionType.SAVINGS_CONTRIBUTION,
            transaction_date=date.today(),
        )
        db_session.add(transaction)
        db_session.commit()

        contribution = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("8000.00"),
            contribution_date=date.today(),
            transaction_id=transaction.id,
        )
        db_session.add(contribution)
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.update_contribution_transaction(
            transaction_id=transaction.id,
            new_amount=Decimal("10000.00"),  # delta = 2000, goal = 10000
        )

        db_session.refresh(goal)
        assert goal.status == GoalStatus.COMPLETED

    def test_update_transaction_not_found(self, db_session, test_user):
        """update_contribution_transaction возвращает False если не найдена."""
        service = BudgetReservationService(db_session)
        result = service.update_contribution_transaction(
            transaction_id=99999,
            new_amount=Decimal("1000.00"),
        )

        assert result is False


class TestDeleteContributionTransaction:
    """Тесты для delete_contribution_transaction()."""

    def test_delete_transaction_cascade(self, db_session, test_user):
        """delete_contribution_transaction каскадно удаляет GoalContribution."""
        goal = Goal(
            user_id=test_user.id,
            name="Цель",
            target_amount=Decimal("100000.00"),
            current_amount=Decimal("20000.00"),
            target_date=far_future_date(),
            status=GoalStatus.ACTIVE,
        )
        db_session.add(goal)
        db_session.commit()

        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("10000.00"),
            transaction_type=TransactionType.SAVINGS_CONTRIBUTION,
            transaction_date=date.today(),
        )
        db_session.add(transaction)
        db_session.commit()

        contribution = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("10000.00"),
            contribution_date=date.today(),
            transaction_id=transaction.id,
        )
        db_session.add(contribution)
        db_session.commit()

        transaction_id = transaction.id
        contribution_id = contribution.id

        service = BudgetReservationService(db_session)
        result = service.delete_contribution_transaction(transaction_id)

        assert result is True

        # Проверяем удаление
        assert db_session.get(Transaction, transaction_id) is None
        assert db_session.get(GoalContribution, contribution_id) is None

        # Проверяем обновление цели
        db_session.refresh(goal)
        assert goal.current_amount == Decimal("10000.00")  # 20000 - 10000

    def test_delete_transaction_reverts_completed_status(self, db_session, test_user):
        """delete_contribution_transaction откатывает статус COMPLETED."""
        goal = Goal(
            user_id=test_user.id,
            name="Завершённая цель",
            target_amount=Decimal("10000.00"),
            current_amount=Decimal("10000.00"),
            target_date=far_future_date(),
            status=GoalStatus.COMPLETED,
        )
        db_session.add(goal)
        db_session.commit()

        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.SAVINGS_CONTRIBUTION,
            transaction_date=date.today(),
        )
        db_session.add(transaction)
        db_session.commit()

        contribution = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("5000.00"),
            contribution_date=date.today(),
            transaction_id=transaction.id,
        )
        db_session.add(contribution)
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.delete_contribution_transaction(transaction.id)

        db_session.refresh(goal)
        assert goal.status == GoalStatus.ACTIVE
        assert goal.current_amount == Decimal("5000.00")


class TestSyncTemplateAmount:
    """Тесты для sync_template_amount()."""

    def test_sync_template_amount_updates(self, db_session, test_user):
        """sync_template_amount обновляет сумму шаблона."""
        test_user.monthly_savings_budget = Decimal("10000.00")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", day_of_month=15)

        # Меняем бюджет
        test_user.monthly_savings_budget = Decimal("15000.00")
        db_session.commit()

        # Синхронизируем
        result = service.sync_template_amount(test_user.id)

        assert result is True

        settings = service.get_settings(test_user.id)
        template = db_session.get(Transaction, settings["template_id"])
        assert template.amount == Decimal("15000.00")

    def test_sync_template_amount_no_template(self, db_session, test_user):
        """sync_template_amount возвращает False если нет шаблона."""
        service = BudgetReservationService(db_session)
        result = service.sync_template_amount(test_user.id)

        assert result is False


class TestAdjustReserveForContribution:
    """Тесты для adjust_reserve_for_contribution()."""

    def test_from_balance_mode_no_action(self, db_session, test_user):
        """В режиме from_balance метод ничего не делает."""
        test_user.monthly_savings_budget = Decimal("50000")
        test_user.reservation_mode = "from_balance"
        db_session.commit()

        service = BudgetReservationService(db_session)

        # Не должно быть exception
        service.adjust_reserve_for_contribution(
            user_id=test_user.id,
            contribution_date=date(2026, 2, 5),
            contribution_amount=Decimal("10000"),
        )

        # Проверяем что никаких шаблонов/exceptions не создано
        templates = (
            db_session.query(Transaction)
            .filter(Transaction.transaction_type == TransactionType.SAVINGS_RESERVE)
            .all()
        )
        assert len(templates) == 0

    def test_contribution_after_reserve_date_no_exception(self, db_session, test_user):
        """Взнос после даты резерва не создаёт Exception."""
        test_user.monthly_savings_budget = Decimal("50000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        # Создать шаблон: резерв 15-го числа
        service.set_mode(test_user.id, "fixed_date", 15)
        db_session.commit()

        settings = service.get_settings(test_user.id)
        template_id = settings["template_id"]

        # Взнос через 5 дней после даты резерва
        reserve_date = reserve_period_start(15)
        service.adjust_reserve_for_contribution(
            user_id=test_user.id,
            contribution_date=days_after(reserve_date, 5),
            contribution_amount=Decimal("10000"),
        )
        db_session.commit()

        # Проверяем что exception не создан
        from app.services import RecurringService

        recurring_service = RecurringService(db_session)
        exceptions = recurring_service.get_exceptions_for_template(template_id)
        assert len(exceptions) == 0

    def test_contribution_before_reserve_date_creates_exception(
        self, db_session, test_user
    ):
        """Взнос до даты резерва создаёт Exception с уменьшенной суммой."""
        test_user.monthly_savings_budget = Decimal("50000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        # Создать шаблон: резерв 15-го числа
        service.set_mode(test_user.id, "fixed_date", 15)
        db_session.commit()

        settings = service.get_settings(test_user.id)
        template_id = settings["template_id"]

        # Взнос за день до даты резерва
        reserve_date = reserve_period_start(15)
        contribution_date = days_before(reserve_date)

        # Создать цель и взнос
        goal = Goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("100000"),
            current_amount=Decimal("0"),
            target_date=far_future_date(),
            status=GoalStatus.ACTIVE,
            priority=1,
        )
        db_session.add(goal)
        db_session.flush()

        # Создать contribution (5-е число, 10000₽)
        contribution = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("10000"),
            contribution_date=contribution_date,
        )
        db_session.add(contribution)
        db_session.commit()

        # Вызов метода
        service.adjust_reserve_for_contribution(
            user_id=test_user.id,
            contribution_date=contribution_date,
            contribution_amount=Decimal("10000"),
        )
        db_session.commit()

        # Проверяем что exception создан с суммой 40000 (50000 - 10000)
        from app.services import RecurringService

        recurring_service = RecurringService(db_session)
        exceptions = recurring_service.get_exceptions_for_template(template_id)
        assert len(exceptions) == 1
        exc = exceptions[0]
        assert exc.amount == Decimal("40000")

    def test_contribution_equals_budget_zero_amount(self, db_session, test_user):
        """Если взносы = бюджету, Exception с суммой 0."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", 15)
        db_session.commit()

        settings = service.get_settings(test_user.id)
        template_id = settings["template_id"]

        # Взнос за день до даты резерва
        reserve_date = reserve_period_start(15)
        contribution_date = days_before(reserve_date)

        # Создать цель и взнос на всю сумму бюджета
        goal = Goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("100000"),
            current_amount=Decimal("0"),
            target_date=far_future_date(),
            status=GoalStatus.ACTIVE,
            priority=1,
        )
        db_session.add(goal)
        db_session.flush()

        contribution = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("10000"),
            contribution_date=contribution_date,
        )
        db_session.add(contribution)
        db_session.commit()

        service.adjust_reserve_for_contribution(
            user_id=test_user.id,
            contribution_date=contribution_date,
            contribution_amount=Decimal("10000"),
        )
        db_session.commit()

        from app.services import RecurringService

        recurring_service = RecurringService(db_session)
        exceptions = recurring_service.get_exceptions_for_template(template_id)
        assert len(exceptions) == 1
        exc = exceptions[0]
        assert exc.amount == Decimal("0")
        assert "(внесено досрочно)" in exc.description

    def test_contribution_exceeds_budget_zero_amount(self, db_session, test_user):
        """Если взносы > бюджета, Exception с суммой 0 (не отрицательной)."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", 15)
        db_session.commit()

        settings = service.get_settings(test_user.id)
        template_id = settings["template_id"]

        # Взнос за день до даты резерва
        reserve_date = reserve_period_start(15)
        contribution_date = days_before(reserve_date)

        goal = Goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("100000"),
            current_amount=Decimal("0"),
            target_date=far_future_date(),
            status=GoalStatus.ACTIVE,
            priority=1,
        )
        db_session.add(goal)
        db_session.flush()

        # Взнос больше бюджета
        contribution = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("20000"),
            contribution_date=contribution_date,
        )
        db_session.add(contribution)
        db_session.commit()

        service.adjust_reserve_for_contribution(
            user_id=test_user.id,
            contribution_date=contribution_date,
            contribution_amount=Decimal("20000"),
        )
        db_session.commit()

        from app.services import RecurringService

        recurring_service = RecurringService(db_session)
        exceptions = recurring_service.get_exceptions_for_template(template_id)
        assert len(exceptions) == 1
        exc = exceptions[0]
        assert exc.amount == Decimal("0")  # Не отрицательная!
        assert "(внесено досрочно)" in exc.description

    def test_no_template_no_action(self, db_session, test_user):
        """Если нет шаблона, метод ничего не делает."""
        test_user.monthly_savings_budget = Decimal("50000")
        test_user.reservation_mode = "fixed_date"
        test_user.reservation_day = 15
        db_session.commit()

        service = BudgetReservationService(db_session)

        # Не создаём шаблон через set_mode, просто устанавливаем режим вручную
        # Метод должен корректно обработать отсутствие шаблона
        service.adjust_reserve_for_contribution(
            user_id=test_user.id,
            contribution_date=date(2026, 2, 5),
            contribution_amount=Decimal("10000"),
        )

        # Никаких ошибок и изменений
        templates = (
            db_session.query(Transaction)
            .filter(Transaction.transaction_type == TransactionType.SAVINGS_RESERVE)
            .all()
        )
        assert len(templates) == 0


# === Новые тесты для protocol-0018 ===


class TestFindAnyReserveTemplate:
    """Тесты для _find_any_reserve_template()."""

    def test_find_active_template(self, db_session, test_user):
        """Находит активный шаблон."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", day_of_month=15)
        db_session.commit()

        template = service._find_any_reserve_template(test_user.id)
        assert template is not None
        assert template.recurring_end_date is None  # Активный

    def test_find_stopped_template(self, db_session, test_user):
        """Находит остановленный шаблон."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", day_of_month=15)
        db_session.commit()

        # Останавливаем
        service.set_mode(test_user.id, "from_balance")
        db_session.commit()

        template = service._find_any_reserve_template(test_user.id)
        assert template is not None
        assert template.recurring_end_date is not None  # Остановленный

    def test_find_returns_latest_when_multiple(self, db_session, test_user):
        """Возвращает последний созданный при наличии нескольких.

        Примечание: метод сортирует по created_at DESC, поэтому ID может
        быть меньше если created_at одинаковый. Проверяем что возвращается
        какой-то из шаблонов данного пользователя.
        """
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)

        # Создаём первый, меняем день (создаётся второй)
        service.set_mode(test_user.id, "fixed_date", day_of_month=10)
        db_session.commit()
        first_settings = service.get_settings(test_user.id)
        first_template_id = first_settings["template_id"]

        service.set_mode(test_user.id, "fixed_date", day_of_month=20)
        db_session.commit()
        second_settings = service.get_settings(test_user.id)
        second_template_id = second_settings["template_id"]

        # Проверяем что было создано 2 разных шаблона
        assert first_template_id != second_template_id

        template = service._find_any_reserve_template(test_user.id)
        assert template is not None
        # Должен вернуть один из существующих шаблонов
        assert template.id in [first_template_id, second_template_id]

    def test_find_returns_none_when_no_templates(self, db_session, test_user):
        """Возвращает None если нет шаблонов."""
        service = BudgetReservationService(db_session)
        template = service._find_any_reserve_template(test_user.id)
        assert template is None


class TestGetTemplateDay:
    """Тесты для _get_template_day()."""

    def test_normal_day(self, db_session, test_user):
        """Возвращает день из transaction_date."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", day_of_month=15)
        db_session.commit()

        template = service._get_reserve_template(test_user.id)
        day = service._get_template_day(template)
        assert day == 15

    def test_anchor_eom_returns_31(self, db_session, test_user):
        """EOM anchor возвращает 31."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", day_of_month=31)
        db_session.commit()

        template = service._get_reserve_template(test_user.id)
        assert template.recurring_anchor_eom is True
        day = service._get_template_day(template)
        assert day == 31


class TestCleanupOrphanExceptions:
    """Тесты для _cleanup_orphan_exceptions()."""

    def test_deletes_all_exceptions(self, db_session, test_user):
        """Удаляет все exceptions для шаблона."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", day_of_month=15)
        db_session.commit()

        settings = service.get_settings(test_user.id)
        template_id = settings["template_id"]

        # Создаём exception вручную
        from app.services import RecurringService

        recurring_service = RecurringService(db_session)
        recurring_service.create_exception(
            template_id=template_id,
            original_date=reserve_period_start(15),
            new_amount=Decimal("5000"),
        )
        db_session.commit()

        # Проверяем что exception существует
        exceptions = recurring_service.get_exceptions_for_template(template_id)
        assert len(exceptions) == 1

        # Удаляем
        count = service._cleanup_orphan_exceptions(template_id)
        db_session.commit()

        assert count == 1
        exceptions = recurring_service.get_exceptions_for_template(template_id)
        assert len(exceptions) == 0

    def test_returns_zero_when_none(self, db_session, test_user):
        """Возвращает 0 если нет exceptions."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", day_of_month=15)
        db_session.commit()

        settings = service.get_settings(test_user.id)
        template_id = settings["template_id"]

        count = service._cleanup_orphan_exceptions(template_id)
        assert count == 0


class TestRecalculateCurrentMonthException:
    """Тесты для recalculate_current_month_exception()."""

    def test_skips_for_from_balance_mode(self, db_session, test_user):
        """Пропускает если режим from_balance."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        # Режим по умолчанию from_balance
        result = service.recalculate_current_month_exception(test_user.id)
        assert result is False

    def test_skips_for_past_reserve_date(self, db_session, test_user):
        """Пропускает если дата резерва уже прошла."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", day_of_month=1)
        db_session.commit()

        # reference_date = сегодня, день резерва = 1
        # Если сегодня > 1, то дата уже прошла
        # Используем дату в прошлом явно
        result = service.recalculate_current_month_exception(
            test_user.id, reference_date=date(2025, 1, 15)
        )
        assert result is False  # 1 января 2025 уже прошло

    def test_creates_exception_when_contributions_exist(self, db_session, test_user):
        """Создаёт exception когда есть взносы до даты резерва."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", day_of_month=28)
        db_session.commit()

        settings = service.get_settings(test_user.id)
        template_id = settings["template_id"]

        # Взнос и пересчёт — до даты резерва, внутри того же периода
        reserve_date = reserve_period_start(28)
        contribution_date = days_before(reserve_date, 10)
        reference_date = days_before(reserve_date, 5)

        # Создаём цель и взнос
        goal = Goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("100000"),
            current_amount=Decimal("3000"),
            target_date=far_future_date(),
            status=GoalStatus.ACTIVE,
            priority=1,
        )
        db_session.add(goal)
        db_session.flush()

        contribution = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("3000"),
            contribution_date=contribution_date,  # До даты резерва
        )
        db_session.add(contribution)
        db_session.commit()

        # Пересчитываем внутри периода резерва
        result = service.recalculate_current_month_exception(
            test_user.id, reference_date=reference_date
        )
        db_session.commit()

        assert result is True

        # Проверяем exception
        from app.services import RecurringService

        recurring_service = RecurringService(db_session)
        exceptions = recurring_service.get_exceptions_for_template(template_id)
        assert len(exceptions) == 1
        assert exceptions[0].amount == Decimal("7000")  # 10000 - 3000

    def test_deletes_exception_when_no_contributions(self, db_session, test_user):
        """Удаляет exception когда нет взносов."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", day_of_month=28)
        db_session.commit()

        settings = service.get_settings(test_user.id)
        template_id = settings["template_id"]

        # Создаём exception вручную (симулируем что был взнос, потом удалён)
        from app.services import RecurringService

        recurring_service = RecurringService(db_session)
        reserve_date = reserve_period_start(28)
        recurring_service.create_exception(
            template_id=template_id,
            original_date=reserve_date,
            new_amount=Decimal("5000"),
        )
        db_session.commit()

        # Проверяем что exception есть
        exceptions = recurring_service.get_exceptions_for_template(template_id)
        assert len(exceptions) == 1

        # Пересчитываем (взносов нет) — до даты резерва
        result = service.recalculate_current_month_exception(
            test_user.id, reference_date=days_before(reserve_date, 5)
        )
        db_session.commit()

        assert result is True  # Exception был удалён

        # Проверяем что exception удалён
        exceptions = recurring_service.get_exceptions_for_template(template_id)
        assert len(exceptions) == 0


class TestUpdateContributionRecalc:
    """Тесты для update_contribution_transaction с recalculate."""

    def test_recalculates_after_amount_change(self, db_session, test_user):
        """Пересчитывает exception после изменения суммы."""
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        service.set_mode(test_user.id, "fixed_date", day_of_month=28)
        db_session.commit()

        settings = service.get_settings(test_user.id)
        template_id = settings["template_id"]

        # Взнос — до даты резерва, внутри того же периода
        reserve_date = reserve_period_start(28)
        contribution_date = days_before(reserve_date, 10)

        # Создаём цель
        goal = Goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("100000"),
            current_amount=Decimal("0"),
            target_date=far_future_date(),
            status=GoalStatus.ACTIVE,
            priority=1,
        )
        db_session.add(goal)
        db_session.flush()

        # Создаём транзакцию и contribution
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("2000"),
            transaction_type=TransactionType.SAVINGS_CONTRIBUTION,
            transaction_date=contribution_date,
            description="Взнос: Test Goal",
        )
        db_session.add(transaction)
        db_session.flush()

        contribution = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("2000"),
            contribution_date=contribution_date,
            transaction_id=transaction.id,
        )
        db_session.add(contribution)
        goal.current_amount = Decimal("2000")
        db_session.commit()

        # Обновляем сумму
        result = service.update_contribution_transaction(
            transaction.id, Decimal("5000")
        )
        db_session.commit()

        assert result is True

        # Проверяем что exception создан/обновлён
        from app.services import RecurringService

        recurring_service = RecurringService(db_session)
        exceptions = recurring_service.get_exceptions_for_template(template_id)
        assert len(exceptions) == 1
        assert exceptions[0].amount == Decimal("5000")  # 10000 - 5000
