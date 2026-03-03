"""Unit тесты для OnboardingService."""
import pytest
from decimal import Decimal

from app.config.avatars import DEFAULT_AVATAR_ID
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

    def test_get_status_includes_name_and_avatar(self, db_session):
        """get_status возвращает name и avatar_id."""
        user = User(
            email="profile@test.com",
            name="Алексей",
            avatar_id="emoji-rocket",
            starting_balance=Decimal("0"),
            first_launch=True,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        status = service.get_status(user.id)

        assert status["name"] == "Алексей"
        assert status["avatar_id"] == "emoji-rocket"


class TestOnboardingServiceComplete:
    """Тесты для complete и complete_with_balance."""

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
        """complete_with_balance для несуществующего user вызывает ValueError."""
        service = OnboardingService(db_session)

        with pytest.raises(ValueError, match="not found"):
            service.complete_with_balance(99999, Decimal("1000"))

    def test_complete_with_name_and_avatar(self, db_session):
        """complete устанавливает имя, аватарку, баланс, first_launch=False."""
        user = User(
            email="full@test.com",
            name="Пользователь",
            starting_balance=Decimal("0"),
            first_launch=True,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        service.complete(user.id, "Иван", "emoji-fox", Decimal("25000"))
        db_session.commit()

        db_session.refresh(user)
        assert user.name == "Иван"
        assert user.avatar_id == "emoji-fox"
        assert user.starting_balance == Decimal("25000")
        assert user.first_launch is False

    def test_complete_sets_first_launch_false(self, db_session):
        """complete устанавливает first_launch=False."""
        user = User(
            email="launch@test.com",
            name="Test",
            starting_balance=Decimal("0"),
            first_launch=True,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        service.complete(user.id, "Тест", DEFAULT_AVATAR_ID, Decimal("0"))
        db_session.commit()

        db_session.refresh(user)
        assert user.first_launch is False

    def test_complete_with_balance_creates_correct_starting_balance(self, db_session):
        """complete с балансом корректно устанавливает starting_balance."""
        user = User(
            email="bal@test.com",
            name="Test",
            starting_balance=Decimal("0"),
            first_launch=True,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        service.complete(user.id, "Тест", DEFAULT_AVATAR_ID, Decimal("99999.99"))
        db_session.commit()

        db_session.refresh(user)
        assert user.starting_balance == Decimal("99999.99")

    def test_complete_invalid_name_empty(self, db_session):
        """complete с пустым именем вызывает ValueError."""
        user = User(
            email="empty@test.com",
            name="Test",
            starting_balance=Decimal("0"),
            first_launch=True,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        with pytest.raises(ValueError, match="1 до 50"):
            service.complete(user.id, "", DEFAULT_AVATAR_ID, Decimal("0"))

    def test_complete_invalid_name_too_long(self, db_session):
        """complete с именем >50 символов вызывает ValueError."""
        user = User(
            email="long@test.com",
            name="Test",
            starting_balance=Decimal("0"),
            first_launch=True,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        with pytest.raises(ValueError, match="1 до 50"):
            service.complete(user.id, "A" * 51, DEFAULT_AVATAR_ID, Decimal("0"))

    def test_complete_invalid_avatar_fallback(self, db_session):
        """complete с невалидной аватаркой использует default."""
        user = User(
            email="avatar@test.com",
            name="Test",
            starting_balance=Decimal("0"),
            first_launch=True,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        service.complete(user.id, "Тест", "invalid-avatar", Decimal("0"))
        db_session.commit()

        db_session.refresh(user)
        assert user.avatar_id == DEFAULT_AVATAR_ID

    def test_complete_with_balance_deprecated_wrapper(self, db_session):
        """complete_with_balance (deprecated) устанавливает defaults."""
        user = User(
            email="compat@test.com",
            name="Test",
            starting_balance=Decimal("0"),
            first_launch=True,
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        service.complete_with_balance(user.id, Decimal("1000"))
        db_session.commit()

        db_session.refresh(user)
        assert user.name == "Пользователь"
        assert user.avatar_id == DEFAULT_AVATAR_ID
        assert user.starting_balance == Decimal("1000")
        assert user.first_launch is False


class TestOnboardingServiceProfile:
    """Тесты для update_profile и get_profile."""

    def test_update_profile(self, db_session):
        """update_profile обновляет name и avatar_id."""
        user = User(
            email="upd@test.com",
            name="Старое",
            avatar_id=DEFAULT_AVATAR_ID,
            starting_balance=Decimal("0"),
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        service.update_profile(user.id, "Новое", "emoji-fire")
        db_session.commit()

        db_session.refresh(user)
        assert user.name == "Новое"
        assert user.avatar_id == "emoji-fire"

    def test_update_profile_user_not_found(self, db_session):
        """update_profile для несуществующего user вызывает ValueError."""
        service = OnboardingService(db_session)

        with pytest.raises(ValueError, match="not found"):
            service.update_profile(99999, "Name", DEFAULT_AVATAR_ID)

    def test_get_profile(self, db_session):
        """get_profile возвращает UserProfile dict."""
        user = User(
            email="get@test.com",
            name="Мария",
            avatar_id="emoji-star",
            starting_balance=Decimal("0"),
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        profile = service.get_profile(user.id)

        assert profile["name"] == "Мария"
        assert profile["avatar_id"] == "emoji-star"

    def test_validate_profile_fields_strips_whitespace(self, db_session):
        """_validate_profile_fields strip-ит пробелы."""
        user = User(
            email="ws@test.com",
            name="Test",
            avatar_id=DEFAULT_AVATAR_ID,
            starting_balance=Decimal("0"),
        )
        db_session.add(user)
        db_session.commit()

        service = OnboardingService(db_session)
        service.update_profile(user.id, "  Имя с пробелами  ", DEFAULT_AVATAR_ID)
        db_session.commit()

        db_session.refresh(user)
        assert user.name == "Имя с пробелами"


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
