"""Тесты методов работы с savings_mode в GoalService."""
import pytest

from app.core import ValidationError
from app.services import GoalService, VALID_SAVINGS_MODES


class TestGetSavingsMode:
    """Тесты метода get_savings_mode()."""

    def test_get_savings_mode_default(self, db_session, test_user):
        """Тест: новый пользователь имеет savings_mode='free' по умолчанию."""
        service = GoalService(db_session)

        mode = service.get_savings_mode(test_user.id)

        assert mode == "free"

    def test_get_savings_mode_user_not_found(self, db_session):
        """Тест: ValidationError если пользователь не найден."""
        service = GoalService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.get_savings_mode(99999)

        assert "не найден" in str(exc_info.value)


class TestUpdateSavingsMode:
    """Тесты метода update_savings_mode()."""

    def test_update_savings_mode_success(self, db_session, test_user):
        """Тест: успешное обновление режима накоплений."""
        service = GoalService(db_session)

        # Проверяем начальное значение
        assert service.get_savings_mode(test_user.id) == "free"

        # Обновляем на medium
        service.update_savings_mode(test_user.id, "medium")
        db_session.commit()

        assert service.get_savings_mode(test_user.id) == "medium"

        # Обновляем на strict
        service.update_savings_mode(test_user.id, "strict")
        db_session.commit()

        assert service.get_savings_mode(test_user.id) == "strict"

        # Возвращаем на free
        service.update_savings_mode(test_user.id, "free")
        db_session.commit()

        assert service.get_savings_mode(test_user.id) == "free"

    def test_update_savings_mode_invalid_mode(self, db_session, test_user):
        """Тест: ValidationError для невалидного режима."""
        service = GoalService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.update_savings_mode(test_user.id, "invalid_mode")

        error_msg = str(exc_info.value)
        assert "Недопустимый режим накоплений" in error_msg
        assert "invalid_mode" in error_msg

    def test_update_savings_mode_user_not_found(self, db_session):
        """Тест: ValidationError если пользователь не найден."""
        service = GoalService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.update_savings_mode(99999, "medium")

        assert "не найден" in str(exc_info.value)


class TestValidSavingsModes:
    """Тесты константы VALID_SAVINGS_MODES."""

    def test_valid_savings_modes_content(self):
        """Тест: константа содержит ровно три режима."""
        assert VALID_SAVINGS_MODES == {"free", "medium", "strict"}

    def test_all_modes_can_be_set(self, db_session, test_user):
        """Тест: все валидные режимы могут быть установлены."""
        service = GoalService(db_session)

        for mode in VALID_SAVINGS_MODES:
            service.update_savings_mode(test_user.id, mode)
            db_session.commit()
            assert service.get_savings_mode(test_user.id) == mode
