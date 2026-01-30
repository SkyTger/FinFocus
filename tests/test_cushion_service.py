"""Тесты для CushionService."""

from decimal import Decimal

import pytest

from app.core import ValidationError
from app.schema.cushion import CushionScenario, Percent
from app.services.cushion_service import (
    CushionService,
    DEFAULT_THRESHOLD_PERCENT,
    _validate_percent,
)


class TestValidatePercent:
    """Тесты для функции _validate_percent()."""

    def test_validate_percent_valid_zero(self):
        """_validate_percent возвращает Percent(0) для 0."""
        result = _validate_percent(0)
        assert result == Percent(0)
        assert isinstance(result, int)

    def test_validate_percent_valid_thirty(self):
        """_validate_percent возвращает Percent(30) для 30."""
        result = _validate_percent(30)
        assert result == Percent(30)

    def test_validate_percent_valid_hundred(self):
        """_validate_percent возвращает Percent(100) для 100."""
        result = _validate_percent(100)
        assert result == Percent(100)

    def test_validate_percent_invalid_negative(self):
        """_validate_percent выбрасывает ValidationError для -1."""
        with pytest.raises(ValidationError) as exc_info:
            _validate_percent(-1)
        assert "0-100" in str(exc_info.value)
        assert exc_info.value.field == "threshold_percent"

    def test_validate_percent_invalid_over_hundred(self):
        """_validate_percent выбрасывает ValidationError для 101."""
        with pytest.raises(ValidationError) as exc_info:
            _validate_percent(101)
        assert "0-100" in str(exc_info.value)


class TestGetSettings:
    """Тесты для метода get_settings()."""

    def test_get_settings_not_configured(self, db_session, test_user):
        """get_settings возвращает is_configured=False когда target=0."""
        service = CushionService(db_session)
        settings = service.get_settings(test_user.id)

        assert settings["is_configured"] is False
        assert settings["target"] == Decimal("0")
        assert settings["threshold_percent"] == DEFAULT_THRESHOLD_PERCENT
        assert settings["threshold_manual"] is False

    def test_get_settings_configured(self, db_session, test_user):
        """get_settings возвращает is_configured=True когда target>0."""
        test_user.cushion_target = Decimal("50000")
        db_session.commit()

        service = CushionService(db_session)
        settings = service.get_settings(test_user.id)

        assert settings["is_configured"] is True
        assert settings["target"] == Decimal("50000")

    def test_get_settings_threshold_amount_computed(self, db_session, test_user):
        """get_settings вычисляет threshold_amount = target * percent / 100."""
        test_user.cushion_target = Decimal("100000")
        test_user.cushion_threshold_percent = 25
        db_session.commit()

        service = CushionService(db_session)
        settings = service.get_settings(test_user.id)

        # 100000 * 25 / 100 = 25000
        assert settings["threshold_amount"] == Decimal("25000")

    def test_get_settings_progress_calculation(self, db_session, test_user):
        """get_settings вычисляет progress на основе current/target."""
        # test_user имеет starting_balance=10000
        test_user.cushion_target = Decimal("50000")
        db_session.commit()

        service = CushionService(db_session)
        settings = service.get_settings(test_user.id)

        # 10000 / 50000 * 100 = 20%
        assert settings["progress"] == pytest.approx(20.0, rel=0.01)
        assert settings["current_amount"] == Decimal("10000")

    def test_get_settings_progress_capped_at_100(self, db_session, test_user):
        """get_settings ограничивает progress до 100% когда current > target."""
        # test_user имеет starting_balance=10000
        test_user.cushion_target = Decimal("5000")  # меньше баланса
        db_session.commit()

        service = CushionService(db_session)
        settings = service.get_settings(test_user.id)

        assert settings["progress"] == 100.0

    def test_get_settings_progress_zero_for_negative_balance(
        self, db_session, test_user
    ):
        """get_settings возвращает progress=0 когда баланс отрицательный."""
        test_user.starting_balance = Decimal("-5000")
        test_user.cushion_target = Decimal("50000")
        db_session.commit()

        service = CushionService(db_session)
        settings = service.get_settings(test_user.id)

        assert settings["progress"] == 0.0
        assert settings["current_amount"] == Decimal("-5000")

    def test_get_settings_user_not_found(self, db_session):
        """get_settings выбрасывает ValidationError если пользователь не найден."""
        service = CushionService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.get_settings(99999)
        assert "не найден" in str(exc_info.value)


class TestUpdateSettings:
    """Тесты для метода update_settings()."""

    def test_update_settings_valid(self, db_session, test_user):
        """update_settings обновляет все поля корректно."""
        service = CushionService(db_session)
        service.update_settings(
            user_id=test_user.id,
            target=Decimal("100000"),
            threshold_percent=50,
            threshold_manual=True,
        )
        db_session.commit()

        # Проверяем через get_settings
        settings = service.get_settings(test_user.id)
        assert settings["target"] == Decimal("100000")
        assert settings["threshold_percent"] == Percent(50)
        assert settings["threshold_manual"] is True

    def test_update_settings_invalid_negative_target(self, db_session, test_user):
        """update_settings выбрасывает ValidationError для target < 0."""
        service = CushionService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.update_settings(
                user_id=test_user.id,
                target=Decimal("-100"),
                threshold_percent=30,
                threshold_manual=False,
            )
        assert exc_info.value.field == "target"

    def test_update_settings_invalid_threshold_percent(self, db_session, test_user):
        """update_settings выбрасывает ValidationError для threshold > 100."""
        service = CushionService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.update_settings(
                user_id=test_user.id,
                target=Decimal("50000"),
                threshold_percent=150,
                threshold_manual=False,
            )
        assert exc_info.value.field == "threshold_percent"


class TestResetSettings:
    """Тесты для метода reset_settings()."""

    def test_reset_settings_to_defaults(self, db_session, test_user):
        """reset_settings сбрасывает все поля к default значениям."""
        # Сначала устанавливаем кастомные значения
        test_user.cushion_target = Decimal("100000")
        test_user.cushion_threshold_percent = 50
        test_user.cushion_threshold_manual = True
        db_session.commit()

        service = CushionService(db_session)
        service.reset_settings(test_user.id)
        db_session.commit()

        settings = service.get_settings(test_user.id)
        assert settings["target"] == Decimal("0")
        assert settings["threshold_percent"] == DEFAULT_THRESHOLD_PERCENT
        assert settings["threshold_manual"] is False
        assert settings["is_configured"] is False


class TestCalculateRecommendation:
    """Тесты для метода calculate_recommendation()."""

    def test_calculate_recommendation_sum_mode(self, db_session, test_user):
        """calculate_recommendation в режиме sum суммирует max_amount сценариев."""
        service = CushionService(db_session)
        scenarios: list[CushionScenario] = [
            CushionScenario(
                name="Scenario 1",
                min_amount=Decimal("1000"),
                max_amount=Decimal("2000"),
            ),
            CushionScenario(
                name="Scenario 2", min_amount=Decimal("500"), max_amount=Decimal("1000")
            ),
        ]

        result = service.calculate_recommendation(scenarios, mode="sum")

        assert result == Decimal("3000")  # 2000 + 1000

    def test_calculate_recommendation_max_scenario_mode(self, db_session, test_user):
        """calculate_recommendation: max_scenario берёт max(max_amount)."""
        service = CushionService(db_session)
        scenarios: list[CushionScenario] = [
            CushionScenario(
                name="Scenario 1",
                min_amount=Decimal("1000"),
                max_amount=Decimal("5000"),
            ),
            CushionScenario(
                name="Scenario 2", min_amount=Decimal("500"), max_amount=Decimal("3000")
            ),
        ]

        result = service.calculate_recommendation(scenarios, mode="max_scenario")

        assert result == Decimal("5000")

    def test_calculate_recommendation_empty_scenarios(self, db_session, test_user):
        """calculate_recommendation возвращает 0 для пустого списка сценариев."""
        service = CushionService(db_session)

        result_sum = service.calculate_recommendation([], mode="sum")
        result_max = service.calculate_recommendation([], mode="max_scenario")

        assert result_sum == Decimal("0")
        assert result_max == Decimal("0")

    def test_calculate_recommendation_invalid_mode(self, db_session, test_user):
        """calculate_recommendation выбрасывает ValidationError для неверного mode."""
        service = CushionService(db_session)
        scenarios: list[CushionScenario] = [
            CushionScenario(
                name="Scenario 1",
                min_amount=Decimal("1000"),
                max_amount=Decimal("2000"),
            ),
        ]

        with pytest.raises(ValidationError) as exc_info:
            service.calculate_recommendation(scenarios, mode="invalid")
        assert "Неверный режим" in str(exc_info.value)
        assert exc_info.value.field == "mode"
