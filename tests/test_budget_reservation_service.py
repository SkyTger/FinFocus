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
            target_date=date(2026, 12, 31),
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
            target_date=date(2026, 12, 31),
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
        """get_budget_progress для fixed_date режима."""
        test_user.monthly_savings_budget = Decimal("15000.00")
        test_user.reservation_mode = "fixed_date"
        db_session.commit()

        service = BudgetReservationService(db_session)
        progress = service.get_budget_progress(test_user.id)

        assert progress["mode"] == "fixed_date"
        assert progress["mode_text"] == "Зарезервировано"


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
