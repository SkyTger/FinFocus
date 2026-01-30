"""Сервис для управления финансовой подушкой безопасности."""

from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.core import ValidationError
from app.schema.cushion import CushionSettings, CushionScenario, Percent


# Допустимые режимы расчёта рекомендации
VALID_CALC_MODES = {"sum", "max_scenario"}

# 30% от цели — типичный рекомендуемый минимальный остаток.
# При достижении этого порога баланс считается "в зоне риска".
# Источник: стандартная практика финансового планирования.
DEFAULT_THRESHOLD_PERCENT: Percent = Percent(30)


def _validate_percent(value: int) -> Percent:
    """Валидирует и преобразует int в Percent (0-100).

    Args:
        value: Значение в процентах для проверки.

    Returns:
        Percent: Валидированное значение как NewType Percent.

    Raises:
        ValidationError: Если value не в диапазоне 0-100.
    """
    if not 0 <= value <= 100:
        raise ValidationError(
            "Порог должен быть в диапазоне 0-100%", field="threshold_percent"
        )
    return Percent(value)


class CushionService:
    """Сервис управления финансовой подушкой безопасности.

    Предоставляет CRUD операции для настроек подушки пользователя
    и калькулятор рекомендуемого размера на основе сценариев.
    """

    def __init__(self, session: Session):
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy сессия для работы с БД.
        """
        self.session = session

    def _get_user(self, user_id: int):
        """Получить пользователя по ID.

        Args:
            user_id: ID пользователя.

        Returns:
            User: Объект пользователя.

        Raises:
            ValidationError: Если пользователь не найден.
        """
        # Импорт внутри метода для избежания circular import
        from app.models.database import User

        user = self.session.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValidationError("Пользователь не найден", field="user_id")
        return user

    def _get_current_balance(self, user_id: int) -> Decimal:
        """Получить текущий баланс пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            Decimal: Текущий баланс на сегодня.
        """
        from datetime import date

        from app.services.calendar_service import CalendarService

        cal_service = CalendarService(self.session)
        return cal_service.get_balance_on_date(user_id, date.today())

    def get_settings(self, user_id: int) -> CushionSettings:
        """Получить настройки подушки с вычисленными полями.

        Args:
            user_id: ID пользователя.

        Returns:
            CushionSettings: Полные настройки включая вычисляемые поля.

        Raises:
            ValidationError: Если пользователь не найден.
        """
        user = self._get_user(user_id)
        current = self._get_current_balance(user_id)

        target = user.cushion_target or Decimal("0")
        # Используем Percent для type safety
        threshold_percent = Percent(user.cushion_threshold_percent or 0)

        # Вычисляем threshold_amount
        threshold_amount = (
            target * threshold_percent / 100 if target > 0 else Decimal("0")
        )

        # Вычисляем progress
        progress = 0.0
        if target > 0:
            if current < 0:
                progress = 0.0
            else:
                progress = min(float(current / target * 100), 100.0)

        return CushionSettings(
            target=target,
            threshold_percent=threshold_percent,
            threshold_amount=threshold_amount,
            threshold_manual=user.cushion_threshold_manual,
            current_amount=current,
            progress=progress,
            is_configured=target > 0,
        )

    def update_settings(
        self,
        user_id: int,
        target: Decimal,
        threshold_percent: int,
        threshold_manual: bool,
    ) -> None:
        """Обновить настройки подушки.

        Args:
            user_id: ID пользователя.
            target: Целевая сумма (>= 0).
            threshold_percent: Порог в процентах (0-100).
            threshold_manual: True если порог изменён вручную.

        Raises:
            ValidationError: Если target < 0 или threshold_percent не в 0-100.
        """
        # Валидация target
        if target < 0:
            raise ValidationError("Цель должна быть >= 0", field="target")

        # Валидация threshold с использованием _validate_percent
        validated_percent = _validate_percent(threshold_percent)

        user = self._get_user(user_id)
        user.cushion_target = target
        user.cushion_threshold_percent = validated_percent
        user.cushion_threshold_manual = threshold_manual
        self.session.flush()

        logger.info(
            f"Обновлены настройки подушки для user {user_id}: "
            f"target={target}, threshold={validated_percent}%"
        )

    def reset_settings(self, user_id: int) -> None:
        """Сбросить настройки подушки.

        При сбросе:
        - target = 0
        - threshold_percent = DEFAULT_THRESHOLD_PERCENT (30%)
        - threshold_manual = False

        Args:
            user_id: ID пользователя.
        """
        user = self._get_user(user_id)
        user.cushion_target = Decimal("0")
        user.cushion_threshold_percent = DEFAULT_THRESHOLD_PERCENT  # Percent(30)
        user.cushion_threshold_manual = False
        self.session.flush()

        logger.info(f"Сброшены настройки подушки для user {user_id}")

    def calculate_recommendation(
        self, scenarios: list[CushionScenario], mode: str
    ) -> Decimal:
        """Рассчитать рекомендуемый размер подушки на основе сценариев.

        Args:
            scenarios: Список сценариев с min_amount и max_amount.
            mode: Режим расчёта:
                - "sum": сумма max_amount всех сценариев
                - "max_scenario": максимальный max_amount среди сценариев

        Returns:
            Decimal: Рекомендуемый размер подушки.

        Raises:
            ValidationError: Если mode не в VALID_CALC_MODES.
        """
        if mode not in VALID_CALC_MODES:
            raise ValidationError(f"Неверный режим расчёта: {mode}", field="mode")

        if mode == "sum":
            return sum((s["max_amount"] for s in scenarios), Decimal("0"))
        else:  # max_scenario
            return max((s["max_amount"] for s in scenarios), default=Decimal("0"))
