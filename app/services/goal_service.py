"""Сервис для управления накопительными целями."""

from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.core import ValidationError
from app.models.database import Goal, GoalContribution, GoalStatus, User

# Допустимые значения для User.savings_mode
VALID_SAVINGS_MODES = {"free", "medium", "strict"}


class GoalService:
    """Сервис для операций с целями накопления."""

    def __init__(self, session: Session):
        """Инициализирует сервис целей.

        Args:
            session: SQLAlchemy сессия для работы с БД
        """
        self.session = session

    def _get_budget_service(self):
        """Возвращает BudgetReservationService с текущей сессией.

        Lazy import для избежания circular dependency
        (GoalService <-> BudgetReservationService).

        Returns:
            BudgetReservationService: Инстанс с self.session.
        """
        from app.services.budget_reservation_service import BudgetReservationService

        return BudgetReservationService(self.session)

    def get_next_priority(self, user_id: int) -> int:
        """Возвращает следующий приоритет для новой цели.

        Args:
            user_id: ID пользователя

        Returns:
            int: max(priority среди ACTIVE целей) + 1, или 1 если нет активных
        """
        max_priority = (
            self.session.query(Goal.priority)
            .filter_by(user_id=user_id, status=GoalStatus.ACTIVE)
            .order_by(Goal.priority.desc())
            .first()
        )

        return (max_priority[0] + 1) if max_priority else 1

    def create_goal(
        self,
        user_id: int,
        name: str,
        target_amount: Decimal,
        target_date: date,
        priority: int | None = None,
    ) -> Goal:
        """Создает новую накопительную цель с валидацией бизнес-правил.

        Args:
            user_id: ID пользователя
            name: Название цели
            target_amount: Целевая сумма
            target_date: Дата достижения цели
            priority: Приоритет цели (опционально, auto-assign если не указан)

        Returns:
            Goal: Созданная цель

        Raises:
            ValidationError: Если нарушены бизнес-правила:
                - target_amount <= 0
                - target_date в прошлом
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

        # Auto-priority если не указан
        if priority is None:
            priority = self.get_next_priority(user_id)

        # Создание цели
        goal = Goal(
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            current_amount=Decimal("0"),
            target_date=target_date,
            priority=priority,
            status=GoalStatus.ACTIVE,
        )

        self.session.add(goal)
        self.session.flush()  # Получить ID без commit

        logger.info(
            f"Создана цель {goal.id} '{name}' для user {user_id}: "
            f"{target_amount}, приоритет {priority}"
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

        Для режима from_balance создаёт транзакцию SAVINGS_CONTRIBUTION в календаре.
        Для режима fixed_date транзакция не создаётся (бюджет резервируется recurring).

        Args:
            goal_id: ID цели
            amount: Сумма взноса
            contribution_date: Дата взноса (по умолчанию сегодня)
            description: Описание взноса

        Returns:
            Goal: Обновленная цель

        Raises:
            ValidationError: Если amount <= 0, цель не найдена или цель завершена
        """
        if amount <= 0:
            raise ValidationError("Сумма взноса должна быть больше 0", field="amount")

        goal = self.session.get(Goal, goal_id)
        if not goal:
            raise ValidationError(f"Цель с ID {goal_id} не найдена")

        # Guard: нельзя вносить в COMPLETED цель
        if goal.status == GoalStatus.COMPLETED:
            raise ValidationError(
                f"Невозможно внести взнос в завершенную цель '{goal.name}'"
            )

        # Warning если бюджет не настроен
        user = self.session.get(User, goal.user_id)
        if user and user.monthly_savings_budget == 0:
            logger.warning(f"Взнос {amount} в цель {goal_id} без настроенного бюджета")

        # Создать транзакцию через BudgetReservationService (если from_balance)
        budget_service = self._get_budget_service()
        actual_date = contribution_date or date.today()
        transaction = budget_service.create_contribution_transaction(
            user_id=goal.user_id,
            goal_name=goal.name,
            amount=amount,
            contribution_date=actual_date,
        )

        # Создаём запись взноса с transaction_id
        contribution = GoalContribution(
            goal_id=goal_id,
            amount=amount,
            contribution_date=actual_date,
            description=description,
            transaction_id=transaction.id if transaction else None,
        )
        self.session.add(contribution)

        # Корректировка резерва для fixed_date режима
        budget_service.adjust_reserve_for_contribution(
            user_id=goal.user_id,
            contribution_date=actual_date,
            contribution_amount=amount,
        )

        # Обновляем текущую сумму цели
        goal.current_amount += amount

        # Автоматически завершаем цель если достигнута
        if goal.is_completed:
            goal.status = GoalStatus.COMPLETED
            logger.info(f"Цель {goal_id} '{goal.name}' достигнута!")

        self.session.flush()
        logger.info(
            f"Добавлен взнос {amount} в цель {goal_id}, "
            f"текущая сумма: {goal.current_amount}, "
            f"transaction_id: {transaction.id if transaction else None}"
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

    def get_contribution_by_id(self, contribution_id: int) -> GoalContribution | None:
        """Получает взнос по ID для предзаполнения формы редактирования."""
        return self.session.get(GoalContribution, contribution_id)

    def get_contributions(
        self,
        goal_id: int,
        limit: int = 10,
    ) -> list[GoalContribution]:
        """Получает список взносов цели отсортированный по дате DESC.

        Args:
            goal_id: ID цели
            limit: Максимальное количество записей (default 10)

        Returns:
            list[GoalContribution]: Последние взносы по дате убывания
        """
        return (
            self.session.query(GoalContribution)
            .filter_by(goal_id=goal_id)
            .order_by(GoalContribution.contribution_date.desc())
            .limit(limit)
            .all()
        )

    def update_priority(self, goal_id: int, new_priority: int) -> Goal:
        """Изменяет приоритет цели с автоматическим сдвигом конфликтующих.

        Алгоритм shift-down:
        - Если new < old: сдвинуть цели с priority >= new AND < old на +1
        - Если new > old: сдвинуть цели с priority > old AND <= new на -1
        - Установить new_priority для целевой цели

        Args:
            goal_id: ID цели
            new_priority: Новый приоритет

        Returns:
            Goal: Обновленная цель

        Raises:
            ValidationError: Если цель не найдена или new_priority < 1
        """
        goal = self.session.get(Goal, goal_id)
        if not goal:
            raise ValidationError(f"Цель с ID {goal_id} не найдена")

        if new_priority < 1:
            raise ValidationError("Приоритет должен быть >= 1", field="priority")

        old_priority = goal.priority
        user_id = goal.user_id

        # Пропускаем если приоритет не изменился
        if new_priority == old_priority:
            return goal

        # Shift-down алгоритм
        if new_priority < old_priority:
            # Повышение приоритета (уменьшение числа): сдвиг вниз
            goals_to_shift = (
                self.session.query(Goal)
                .filter(
                    Goal.user_id == user_id,
                    Goal.status == GoalStatus.ACTIVE,
                    Goal.id != goal_id,
                    Goal.priority >= new_priority,
                    Goal.priority < old_priority,
                )
                .all()
            )
            for g in goals_to_shift:
                g.priority += 1
        else:
            # Понижение приоритета (увеличение числа): сдвиг вверх
            goals_to_shift = (
                self.session.query(Goal)
                .filter(
                    Goal.user_id == user_id,
                    Goal.status == GoalStatus.ACTIVE,
                    Goal.id != goal_id,
                    Goal.priority > old_priority,
                    Goal.priority <= new_priority,
                )
                .all()
            )
            for g in goals_to_shift:
                g.priority -= 1

        goal.priority = new_priority
        self.session.flush()

        logger.info(
            f"Изменен приоритет цели {goal_id} " f"с {old_priority} на {new_priority}"
        )

        return goal

    def move_priority_up(self, goal_id: int) -> Goal:
        """Перемещает цель на один приоритет вверх (уменьшает priority).

        Args:
            goal_id: ID цели

        Returns:
            Goal: Обновленная цель

        Raises:
            ValidationError: Если цель не найдена или уже имеет priority=1
        """
        goal = self.session.get(Goal, goal_id)
        if not goal:
            raise ValidationError(f"Цель с ID {goal_id} не найдена")

        if goal.priority <= 1:
            raise ValidationError("Цель уже имеет наивысший приоритет")

        return self.update_priority(goal_id, goal.priority - 1)

    def move_priority_down(self, goal_id: int) -> Goal:
        """Перемещает цель на один приоритет вниз (увеличивает priority).

        Args:
            goal_id: ID цели

        Returns:
            Goal: Обновленная цель

        Raises:
            ValidationError: Если цель не найдена
        """
        goal = self.session.get(Goal, goal_id)
        if not goal:
            raise ValidationError(f"Цель с ID {goal_id} не найдена")

        return self.update_priority(goal_id, goal.priority + 1)

    def get_savings_budget(self, user_id: int) -> Decimal:
        """Получает месячный бюджет накоплений пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Decimal: Месячный бюджет накоплений

        Raises:
            ValidationError: Если пользователь не найден
        """
        from app.models.database import User

        user = self.session.get(User, user_id)
        if not user:
            raise ValidationError(f"Пользователь с ID {user_id} не найден")

        return user.monthly_savings_budget

    def update_savings_budget(self, user_id: int, budget: Decimal) -> None:
        """Обновляет бюджет накоплений пользователя.

        Если пользователь в режиме fixed_date, синхронизирует сумму recurring шаблона.

        Args:
            user_id: ID пользователя
            budget: Новый месячный бюджет (должен быть >= 0)

        Raises:
            ValidationError: Если пользователь не найден или budget < 0
        """
        user = self.session.get(User, user_id)
        if not user:
            raise ValidationError(f"Пользователь с ID {user_id} не найден")

        if budget < 0:
            raise ValidationError(
                "Бюджет должен быть >= 0", field="monthly_savings_budget"
            )

        user.monthly_savings_budget = budget
        self.session.flush()

        # Синхронизировать recurring шаблон если режим fixed_date
        budget_service = self._get_budget_service()
        budget_service.sync_template_amount(user_id)

        logger.info(f"Обновлен бюджет накоплений для user {user_id}: {budget}")

    # TODO: Перенести методы работы с User
    # (get/update_savings_mode, get/update_savings_budget) в отдельный UserService
    # при рефакторинге. Временно размещены здесь для MVP.

    def get_savings_mode(self, user_id: int) -> str:
        """Получает режим накоплений пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            str: "free", "medium" или "strict"

        Raises:
            ValidationError: Если пользователь не найден.
        """
        from app.models.database import User

        user = self.session.get(User, user_id)
        if not user:
            raise ValidationError(f"Пользователь с ID {user_id} не найден")
        return user.savings_mode

    def update_savings_mode(self, user_id: int, mode: str) -> None:
        """Обновляет режим накоплений пользователя.

        Args:
            user_id: ID пользователя.
            mode: Новый режим ("free", "medium", "strict").

        Raises:
            ValidationError: Если пользователь не найден или mode невалидный.
        """
        from app.models.database import User

        if mode not in VALID_SAVINGS_MODES:
            raise ValidationError(
                f"Недопустимый режим накоплений: {mode}. "
                f"Допустимые значения: {', '.join(sorted(VALID_SAVINGS_MODES))}"
            )

        user = self.session.get(User, user_id)
        if not user:
            raise ValidationError(f"Пользователь с ID {user_id} не найден")

        user.savings_mode = mode
        self.session.flush()

        logger.info(f"Обновлен режим накоплений для user {user_id}: {mode}")

    def delete_contribution(self, contribution_id: int) -> bool:
        """Удаляет взнос и пересчитывает exception резерва.

        Алгоритм:
        1. Находит GoalContribution по ID
        2. Если есть transaction_id — удаляет через BudgetReservationService
        3. Иначе — удаляет напрямую
        4. Обновляет Goal.current_amount
        5. Вызывает recalculate_current_month_exception()

        Args:
            contribution_id: ID взноса GoalContribution.

        Returns:
            bool: True если взнос удалён, False если не найден.
        """
        contribution = self.session.get(GoalContribution, contribution_id)
        if not contribution:
            return False

        goal = contribution.goal
        user_id = goal.user_id
        amount = contribution.amount
        contribution_date = contribution.contribution_date

        budget_service = self._get_budget_service()

        # Удаляем транзакцию если есть
        if contribution.transaction_id:
            budget_service.delete_contribution_transaction(contribution.transaction_id)
        else:
            self.session.delete(contribution)

        # Обновляем current_amount
        goal.current_amount -= amount
        if goal.current_amount < Decimal("0"):
            goal.current_amount = Decimal("0")

        # Пересчитываем exception для месяца взноса
        budget_service.recalculate_current_month_exception(
            user_id=user_id,
            reference_date=contribution_date,
        )

        self.session.flush()
        logger.info(
            f"Deleted contribution {contribution_id} for goal {goal.id}, "
            f"amount={amount}, recalculated exception"
        )
        return True
