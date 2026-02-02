"""Сервис для управления режимами резервирования бюджета на цели.

Реализует два режима:
- fixed_date: recurring операция "Резерв на цели" в фиксированный день месяца
- from_balance: взносы создаются как SAVINGS_CONTRIBUTION при каждом вкладе

См. solution-v2.md секция "Режимы резервирования".
"""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import (
    GoalContribution,
    Transaction,
    TransactionType,
    User,
)
from app.schema.budget_reservation import (
    BudgetProgress,
    BudgetReservationSettings,
    ReservationMode,
)

# === КОНСТАНТЫ ===

RESERVE_DESCRIPTION: str = "Резерв на цели"
"""Описание для recurring шаблона резерва."""

STATUS_THRESHOLDS: dict[str, int] = {
    "success": 50,  # < 50% использовано
    "warning": 75,  # 50-75%
    "orange": 100,  # 75-100%
    "danger": 101,  # > 100%
}


class BudgetReservationService:
    """Сервис управления режимами резервирования бюджета на накопления."""

    def __init__(self, session: Session):
        """Инициализирует сервис.

        Args:
            session: SQLAlchemy сессия для работы с БД.
        """
        self.session = session

    def get_settings(self, user_id: int) -> BudgetReservationSettings:
        """Получает текущие настройки резервирования.

        Args:
            user_id: ID пользователя.

        Returns:
            BudgetReservationSettings: Настройки режима резервирования.
        """
        user = self.session.get(User, user_id)
        if not user:
            logger.warning(f"User {user_id} not found, returning defaults")
            return BudgetReservationSettings(
                mode="from_balance",
                day_of_month=None,
                monthly_budget=Decimal("0"),
                template_id=None,
            )

        template = self._get_reserve_template(user_id)

        return BudgetReservationSettings(
            mode=user.reservation_mode,  # type: ignore[typeddict-item]
            day_of_month=user.reservation_day,
            monthly_budget=Decimal(user.monthly_savings_budget),
            template_id=template.id if template else None,
        )

    def set_mode(
        self,
        user_id: int,
        mode: ReservationMode,
        day_of_month: int | None = None,
    ) -> BudgetReservationSettings:
        """Устанавливает режим резервирования.

        При переключении на fixed_date создаёт recurring шаблон.
        При переключении на from_balance останавливает существующий шаблон.

        Args:
            user_id: ID пользователя.
            mode: Новый режим ("fixed_date" или "from_balance").
            day_of_month: День месяца для fixed_date (1-31).

        Returns:
            BudgetReservationSettings: Обновлённые настройки.

        Raises:
            ValueError: Если fixed_date без day_of_month.
        """
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        if mode == "fixed_date":
            if day_of_month is None:
                raise ValueError("day_of_month required for fixed_date mode")
            if not 1 <= day_of_month <= 31:
                raise ValueError("day_of_month must be 1-31")

            # Останавливаем старый шаблон если есть
            self._stop_reserve_template(user_id)

            # Создаём новый шаблон
            template = self._create_reserve_template(user_id, day_of_month)

            user.reservation_mode = "fixed_date"
            user.reservation_day = day_of_month
            self.session.flush()

            logger.info(
                f"User {user_id}: set mode=fixed_date, day={day_of_month}, "
                f"template_id={template.id}"
            )

        else:  # from_balance
            # Останавливаем шаблон
            self._stop_reserve_template(user_id)

            user.reservation_mode = "from_balance"
            user.reservation_day = None
            self.session.flush()

            logger.info(f"User {user_id}: set mode=from_balance")

        return self.get_settings(user_id)

    def get_budget_progress(
        self,
        user_id: int,
        reference_date: date | None = None,
    ) -> BudgetProgress:
        """Рассчитывает прогресс использования бюджета в месяце.

        Для fixed_date: сумма = резерв (если дата прошла).
        Для from_balance: сумма = взносы за месяц.

        Args:
            user_id: ID пользователя.
            reference_date: Дата для расчёта (default: today).

        Returns:
            BudgetProgress: Прогресс с процентами и статусом.
        """
        if reference_date is None:
            reference_date = date.today()

        settings = self.get_settings(user_id)
        total_budget = settings["monthly_budget"]

        if settings["mode"] == "fixed_date":
            used = self._get_reserve_sum_for_month(user_id, reference_date)
            mode_text = "Зарезервировано"
        else:
            used = self._get_contributions_sum_for_month(user_id, reference_date)
            mode_text = "Внесено"

        available = total_budget - used if total_budget > 0 else Decimal("0")

        # Расчёт процента
        if total_budget > 0:
            progress_percent = float(used / total_budget * 100)
        else:
            progress_percent = 0.0

        # Определение статуса
        if progress_percent < STATUS_THRESHOLDS["success"]:
            status = "success"
        elif progress_percent < STATUS_THRESHOLDS["warning"]:
            status = "warning"
        elif progress_percent < STATUS_THRESHOLDS["orange"]:
            status = "orange"
        else:
            status = "danger"

        return BudgetProgress(
            total_budget=total_budget,
            used_budget=used,
            available_budget=max(available, Decimal("0")),
            progress_percent=min(progress_percent, 100.0),
            status=status,
            mode=settings["mode"],
            mode_text=mode_text,
        )

    # === Private helpers ===

    def _get_reserve_template(self, user_id: int) -> Transaction | None:
        """Находит активный recurring шаблон резерва.

        Шаблон считается активным если:
        - is_recurring=True
        - transaction_type=SAVINGS_RESERVE
        - recurring_end_date is None OR recurring_end_date >= today

        Args:
            user_id: ID пользователя.

        Returns:
            Transaction | None: Шаблон или None.
        """
        today = date.today()

        template = (
            self.session.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.is_recurring.is_(True),
                Transaction.transaction_type == TransactionType.SAVINGS_RESERVE,
            )
            .filter(
                (Transaction.recurring_end_date.is_(None))
                | (Transaction.recurring_end_date >= today)
            )
            .first()
        )

        return template

    def _create_reserve_template(
        self,
        user_id: int,
        day_of_month: int,
    ) -> Transaction:
        """Создаёт recurring шаблон резерва на цели.

        Использует Anchored-алгоритм:
        - Если day > last_day_of_month, используется last_day
        - recurring_anchor_eom=True для 31-го числа

        Args:
            user_id: ID пользователя.
            day_of_month: День месяца (1-31).

        Returns:
            Transaction: Созданный шаблон.
        """
        user = self.session.get(User, user_id)
        budget = Decimal(user.monthly_savings_budget) if user else Decimal("0")

        today = date.today()
        _, last_day = monthrange(today.year, today.month)

        # Anchored: если день > последнего дня месяца, используем последний
        actual_day = min(day_of_month, last_day)
        start_date = date(today.year, today.month, actual_day)

        # Если дата уже прошла, начинаем со следующего месяца
        if start_date < today:
            if today.month == 12:
                next_month = date(today.year + 1, 1, 1)
            else:
                next_month = date(today.year, today.month + 1, 1)
            _, next_last_day = monthrange(next_month.year, next_month.month)
            actual_day = min(day_of_month, next_last_day)
            start_date = date(next_month.year, next_month.month, actual_day)

        # EOM anchor для 31-го числа
        anchor_eom = day_of_month == 31

        template = Transaction(
            user_id=user_id,
            amount=budget,
            transaction_type=TransactionType.SAVINGS_RESERVE,
            transaction_date=start_date,
            description=RESERVE_DESCRIPTION,
            is_recurring=True,
            recurring_period="monthly",
            recurring_anchor_eom=anchor_eom,
        )

        self.session.add(template)
        self.session.flush()

        logger.info(
            f"Created reserve template {template.id} for user {user_id}: "
            f"day={day_of_month}, start={start_date}, amount={budget}"
        )

        return template

    def _stop_reserve_template(self, user_id: int) -> bool:
        """Останавливает активный recurring шаблон резерва.

        Устанавливает recurring_end_date = вчера (soft delete).

        Args:
            user_id: ID пользователя.

        Returns:
            bool: True если шаблон был остановлен, False если не найден.
        """
        template = self._get_reserve_template(user_id)
        if not template:
            return False

        yesterday = date.today() - timedelta(days=1)
        template.recurring_end_date = yesterday
        self.session.flush()

        logger.info(f"Stopped reserve template {template.id} for user {user_id}")
        return True

    def _get_contributions_sum_for_month(
        self,
        user_id: int,
        reference_date: date,
    ) -> Decimal:
        """Суммирует взносы пользователя за месяц.

        Args:
            user_id: ID пользователя.
            reference_date: Дата в целевом месяце.

        Returns:
            Decimal: Сумма взносов.
        """
        start_of_month = date(reference_date.year, reference_date.month, 1)
        _, last_day = monthrange(reference_date.year, reference_date.month)
        end_of_month = date(reference_date.year, reference_date.month, last_day)

        # Join через Goal для фильтрации по user_id
        from app.models.database import Goal

        result = (
            self.session.query(func.coalesce(func.sum(GoalContribution.amount), 0))
            .join(Goal, GoalContribution.goal_id == Goal.id)
            .filter(
                Goal.user_id == user_id,
                GoalContribution.contribution_date >= start_of_month,
                GoalContribution.contribution_date <= end_of_month,
            )
            .scalar()
        )

        return Decimal(str(result))

    def _get_reserve_sum_for_month(
        self,
        user_id: int,
        reference_date: date,
    ) -> Decimal:
        """Суммирует резервы за месяц (для fixed_date режима).

        Суммирует транзакции типа SAVINGS_RESERVE за месяц.

        Args:
            user_id: ID пользователя.
            reference_date: Дата в целевом месяце.

        Returns:
            Decimal: Сумма резервов.
        """
        start_of_month = date(reference_date.year, reference_date.month, 1)
        _, last_day = monthrange(reference_date.year, reference_date.month)
        end_of_month = date(reference_date.year, reference_date.month, last_day)

        result = (
            self.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.SAVINGS_RESERVE,
                Transaction.transaction_date >= start_of_month,
                Transaction.transaction_date <= end_of_month,
                # Исключаем шаблоны — только реальные или виртуальные экземпляры
                # Шаблоны имеют is_recurring=True, экземпляры is_recurring=False
                Transaction.is_recurring.is_(False),
            )
            .scalar()
        )

        return Decimal(str(result))
