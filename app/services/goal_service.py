"""Сервис для управления накопительными целями."""

from decimal import Decimal
from datetime import date, timedelta
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

        # Валидация: target_date должен быть минимум через 7 дней
        min_target_date = date.today() + timedelta(days=7)
        if target_date < min_target_date:
            raise ValidationError(
                "Дата достижения цели должна быть минимум через 7 дней от сегодня. "
                f"Минимальная дата: {min_target_date.strftime('%d.%m.%Y')}"
            )

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

    def get_by_id(self, goal_id: int) -> Goal:
        """Получает цель по ID.

        Args:
            goal_id: ID цели

        Returns:
            Goal: Найденная цель или None
        """
        return self.session.query(Goal).get(goal_id)

    def get_all_by_user(
        self,
        user_id: int,
        status: GoalStatus = None
    ) -> list[Goal]:
        """Получает все цели пользователя с фильтрацией.

        Args:
            user_id: ID пользователя
            status: Фильтр по статусу (опционально)

        Returns:
            list[Goal]: Список целей, отсортированный по приоритету
        """
        query = self.session.query(Goal).filter_by(user_id=user_id)

        if status:
            query = query.filter(Goal.status == status)

        return query.order_by(Goal.priority.asc()).all()

    def update_goal(
        self,
        goal_id: int,
        name: str = None,
        target_amount: Decimal = None,
        target_date: date = None,
        status: GoalStatus = None
    ) -> Goal:
        """Обновляет существующую цель.

        Args:
            goal_id: ID цели
            name: Новое название (опционально)
            target_amount: Новая целевая сумма (опционально)
            target_date: Новая дата (опционально)
            status: Новый статус (опционально)

        Returns:
            Goal: Обновленная цель

        Raises:
            ValidationError: Если цель не найдена или нарушены бизнес-правила
        """
        goal = self.session.query(Goal).get(goal_id)
        if not goal:
            raise ValidationError(f"Цель с ID {goal_id} не найдена")

        if name is not None:
            goal.name = name

        if target_amount is not None:
            if target_amount <= 0:
                raise ValidationError("Целевая сумма должна быть больше 0")
            goal.target_amount = target_amount

        if target_date is not None:
            min_target_date = date.today() + timedelta(days=7)
            if target_date < min_target_date:
                raise ValidationError(
                    "Дата достижения цели должна быть минимум через 7 дней от сегодня. "
                    f"Минимальная дата: {min_target_date.strftime('%d.%m.%Y')}"
                )
            goal.target_date = target_date

        if status is not None:
            goal.status = status

        self.session.flush()
        return goal

    def delete_goal(self, goal_id: int) -> bool:
        """Удаляет цель по ID.

        Примечание: Удаление цели также удалит все связанные взносы (cascade).

        Args:
            goal_id: ID цели

        Returns:
            bool: True если цель удалена, False если не найдена
        """
        goal = self.session.query(Goal).get(goal_id)
        if not goal:
            return False

        self.session.delete(goal)
        self.session.flush()

        return True