"""Сервис для управления накопительными целями."""

from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session
from app.models.database import Goal, GoalStatus


class ValidationError(Exception):
    """Ошибка валидации бизнес-правил."""
    pass


class GoalService:
    """Сервис для операций с целями накопления."""

    def __init__(self, session: Session):
        """Инициализирует сервис целей.

        Args:
            session: SQLAlchemy сессия для работы с БД
        """
        self.session = session

    def create_goal(
        self,
        user_id: int,
        name: str,
        target_amount: Decimal,
        target_date: date
    ) -> Goal:
        """Создает новую накопительную цель с валидацией бизнес-правил.

        Args:
            user_id: ID пользователя
            name: Название цели
            target_amount: Целевая сумма
            target_date: Дата достижения цели

        Returns:
            Goal: Созданная цель

        Raises:
            ValidationError: Если нарушены бизнес-правила:
                - target_amount <= 0
                - target_date в прошлом
                - у пользователя уже есть активная цель (MVP ограничение)
        """
        # Валидация: target_amount > 0
        if target_amount <= 0:
            raise ValidationError("Целевая сумма должна быть больше 0")

        # Валидация: target_date в будущем
        if target_date <= date.today():
            raise ValidationError("Дата достижения цели должна быть в будущем")

        # Валидация: только одна активная цель (MVP ограничение)
        active_goals_count = self.session.query(Goal).filter_by(
            user_id=user_id,
            status=GoalStatus.ACTIVE
        ).count()

        if active_goals_count >= 1:
            raise ValidationError(
                "В MVP версии можно иметь только одну активную цель. "
                "Завершите или удалите текущую цель перед созданием новой."
            )

        # Создание цели
        goal = Goal(
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            current_amount=Decimal('0'),
            target_date=target_date,
            priority=1,  # В MVP всегда 1
            status=GoalStatus.ACTIVE
        )

        self.session.add(goal)
        self.session.flush()  # Получить ID без commit

        return goal

    def add_contribution(
        self,
        goal_id: int,
        amount: Decimal
    ) -> Goal:
        """Добавляет взнос в цель.

        Args:
            goal_id: ID цели
            amount: Сумма взноса

        Returns:
            Goal: Обновленная цель

        Raises:
            ValidationError: Если amount <= 0 или цель не найдена
        """
        if amount <= 0:
            raise ValidationError("Сумма взноса должна быть больше 0")

        goal = self.session.query(Goal).get(goal_id)
        if not goal:
            raise ValidationError(f"Цель с ID {goal_id} не найдена")

        goal.current_amount += amount

        # Автоматически завершаем цель если достигнута
        if goal.is_completed:
            goal.status = GoalStatus.COMPLETED

        self.session.flush()
        return goal