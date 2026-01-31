"""Unit тесты для OnboardingService."""
import pytest
from decimal import Decimal

from app.services.onboarding_service import OnboardingService
from app.models.database import User


class TestOnboardingServiceGetStatus:
    """Тесты для get_status."""

    def test_new_user_first_launch_true(self, db_session):
        """Новый пользователь имеет first_launch=True."""
        user = User(
            email="new@test.com",
            name="Test",
            starting_balance=Decimal("0"),
            first_launch=True,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        status = service.get_status(user.id)

        assert status["first_launch"] is True
        assert status["starting_balance"] == Decimal("0")
        assert status["needs_balance_alert"] is True

    def test_configured_user_first_launch_false(self, db_session):
        """Пользователь с балансом имеет first_launch=False."""
        user = User(
            email="configured@test.com",
            name="Test",
            starting_balance=Decimal("10000"),
            first_launch=False,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        status = service.get_status(user.id)

        assert status["first_launch"] is False
        assert status["needs_balance_alert"] is False

    def test_user_not_found_raises(self, db_session):
        """Несуществующий пользователь вызывает ValueError."""
        service = OnboardingService(db_session)

        with pytest.raises(ValueError, match="not found"):
            service.get_status(99999)


class TestOnboardingServiceComplete:
    """Тесты для complete_with_balance."""

    def test_sets_balance_and_first_launch(self, db_session):
        """complete_with_balance устанавливает баланс и first_launch=False."""
        user = User(
            email="complete@test.com",
            name="Test",
            starting_balance=Decimal("0"),
            first_launch=True,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        service.complete_with_balance(user.id, Decimal("50000"))
        db_session.commit()

        db_session.refresh(user)
        assert user.starting_balance == Decimal("50000")
        assert user.first_launch is False

    def test_allows_negative_balance(self, db_session):
        """Допускает отрицательный баланс (с предупреждением в UI)."""
        user = User(
            email="negative@test.com",
            name="Test",
            starting_balance=Decimal("0"),
            first_launch=True,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        service.complete_with_balance(user.id, Decimal("-5000"))
        db_session.commit()

        db_session.refresh(user)
        assert user.starting_balance == Decimal("-5000")

    def test_complete_user_not_found_raises(self, db_session):
        """complete_with_balance для несуществующего пользователя вызывает ValueError."""
        service = OnboardingService(db_session)

        with pytest.raises(ValueError, match="not found"):
            service.complete_with_balance(99999, Decimal("1000"))


class TestOnboardingServiceSkip:
    """Тесты для skip."""

    def test_skip_sets_first_launch_false(self, db_session):
        """skip устанавливает first_launch=False, баланс не меняет."""
        user = User(
            email="skip@test.com",
            name="Test",
            starting_balance=Decimal("0"),
            first_launch=True,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        service.skip(user.id)
        db_session.commit()

        db_session.refresh(user)
        assert user.first_launch is False
        assert user.starting_balance == Decimal("0")

    def test_skip_user_not_found_raises(self, db_session):
        """skip для несуществующего пользователя вызывает ValueError."""
        service = OnboardingService(db_session)

        with pytest.raises(ValueError, match="not found"):
            service.skip(99999)
