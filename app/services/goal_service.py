"""Сервис для управления накопительными целями."""

from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.core import ValidationError
from app.models.database import Goal, GoalContribution, GoalStatus


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
        target_date: date,
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
            raise ValidationError(
                "Целевая сумма должна быть больше 0", field="target_amount"
            )

        # Валидация: target_date должен быть минимум через 7 дней
        min_target_date = date.today() + timedelta(days=7)
        if target_date < min_target_date:
            min_date_str = min_target_date.strftime("%d.%m.%Y")
            raise ValidationError(
                "Дата достижения цели должна быть минимум через 7 дней. "
                f"Минимальная дата: {min_date_str}",
                field="target_date",
            )

        # Валидация: только одна активная цель (MVP ограничение)
        active_goals_count = (
            self.session.query(Goal)
            .filter_by(user_id=user_id, status=GoalStatus.ACTIVE)
            .count()
        )

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
            current_amount=Decimal("0"),
            target_date=target_date,
            priority=1,  # В MVP всегда 1
            status=GoalStatus.ACTIVE,
        )

        self.session.add(goal)
        self.session.flush()  # Получить ID без commit

        logger.info(
            f"Создана цель {goal.id} '{name}' для user {user_id}: "
            f"{target_amount}"
        )

        return goal

    def add_contribution(
        self,
        goal_id: int,
        amount: Decimal,
        contribution_date: date | None = None,
        description: str | None = None,
    ) -> Goal:
        """Добавляет взнос в цель с созданием записи GoalContribution.

        Args:
            goal_id: ID цели
            amount: Сумма взноса
            contribution_date: Дата взноса (по умолчанию сегодня)
            description: Описание взноса

        Returns:
            Goal: Обновленная цель

        Raises:
            ValidationError: Если amount <= 0 или цель не найдена
        """
        if amount <= 0:
            raise ValidationError(
                "Сумма взноса должна быть больше 0", field="amount"
            )

        goal = self.session.get(Goal, goal_id)
        if not goal:
            raise ValidationError(f"Цель с ID {goal_id} не найдена")

        # Создаём запись взноса
        contribution = GoalContribution(
            goal_id=goal_id,
            amount=amount,
            contribution_date=contribution_date or date.today(),
            description=description,
        )
        self.session.add(contribution)

        # Обновляем текущую сумму цели
        goal.current_amount += amount

        # Автоматически завершаем цель если достигнута
        if goal.is_completed:
            goal.status = GoalStatus.COMPLETED
            logger.info(f"Цель {goal_id} '{goal.name}' достигнута!")

        self.session.flush()
        logger.info(
            f"Добавлен взнос {amount} в цель {goal_id}, "
            f"текущая сумма: {goal.current_amount}"
        )
        return goal

    def get_by_id(self, goal_id: int) -> Goal | None:
        """Получает цель по ID.

        Args:
            goal_id: ID цели

        Returns:
            Goal: Найденная цель или None
        """
        return self.session.get(Goal, goal_id)

    def get_all_by_user(
        self, user_id: int, status: GoalStatus | None = None
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
        name: str | None = None,
        target_amount: Decimal | None = None,
        target_date: date | None = None,
        status: GoalStatus | None = None,
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
        goal = self.session.get(Goal, goal_id)
        if not goal:
            raise ValidationError(f"Цель с ID {goal_id} не найдена")

        if name is not None:
            goal.name = name

        if target_amount is not None:
            if target_amount <= 0:
                raise ValidationError(
                    "Целевая сумма должна быть больше 0", field="target_amount"
                )
            goal.target_amount = target_amount

        if target_date is not None:
            min_target_date = date.today() + timedelta(days=7)
            if target_date < min_target_date:
                min_date_str = min_target_date.strftime("%d.%m.%Y")
                raise ValidationError(
                    "Дата достижения цели должна быть минимум через 7 дней. "
                    f"Минимальная дата: {min_date_str}",
                    field="target_date",
                )
            goal.target_date = target_date

        if status is not None:
            goal.status = status

        self.session.flush()

        logger.info(f"Обновлена цель {goal_id}")

        return goal

    def delete_goal(self, goal_id: int) -> bool:
        """Удаляет цель по ID.

        Примечание: Удаление цели также удалит все связанные взносы (cascade).

        Args:
            goal_id: ID цели

        Returns:
            bool: True если цель удалена, False если не найдена
        """
        goal = self.session.get(Goal, goal_id)
        if not goal:
            return False

        self.session.delete(goal)
        self.session.flush()

        logger.info(f"Удалена цель {goal_id}")

        return True
