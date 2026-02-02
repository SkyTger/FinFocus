"""Сервис для управления режимами резервирования бюджета на цели.

Реализует два режима:
- fixed_date: recurring операция "Резервирование бюджета" в фиксированный день месяца
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
    Goal,
    GoalContribution,
    GoalStatus,
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

RESERVE_DESCRIPTION: str = "Резервирование бюджета"
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

        При переключении на fixed_date:
        - Если шаблон с тем же днём существует → реактивируем (exceptions сохраняются!)
        - Если день изменился → останавливаем старый, чистим exceptions, создаём новый
        - Если нет шаблона → создаём новый

        При переключении на from_balance:
        - Останавливаем шаблон (exceptions НЕ чистим — пригодятся при возврате)

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

            # Поиск существующего шаблона (включая остановленный)
            existing_template = self._find_any_reserve_template(user_id)

            if existing_template:
                existing_day = self._get_template_day(existing_template)

                if existing_day == day_of_month:
                    # Тот же день — реактивируем (exceptions сохраняются!)
                    if existing_template.recurring_end_date is not None:
                        existing_template.recurring_end_date = None
                        self.session.flush()
                        logger.info(
                            f"Reactivated template {existing_template.id} "
                            f"for user {user_id}"
                        )
                    else:
                        logger.debug(
                            f"Template {existing_template.id} already active "
                            f"for user {user_id}"
                        )
                else:
                    # Другой день — останавливаем старый, чистим exceptions
                    self._stop_reserve_template(user_id)
                    self._cleanup_orphan_exceptions(existing_template.id)
                    # Создаём новый шаблон
                    self._create_reserve_template(user_id, day_of_month)
            else:
                # Нет шаблона — создаём новый
                self._create_reserve_template(user_id, day_of_month)

            user.reservation_mode = "fixed_date"
            user.reservation_day = day_of_month
            self.session.flush()

            logger.info(f"User {user_id}: set mode=fixed_date, day={day_of_month}")

        else:  # from_balance
            # Останавливаем шаблон (exceptions НЕ чистим — пригодятся при возврате)
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

        Единообразно для обоих режимов считает взносы (contributions),
        а не резервы. Это обеспечивает консистентное отображение прогресса
        независимо от режима резервирования.

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

        # Единообразный расчёт: взносы за месяц (для обоих режимов)
        used = self._get_contributions_sum_for_month(user_id, reference_date)

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
            mode_text="Внесено",  # Единообразно для обоих режимов
        )

    def recalculate_current_month_exception(
        self,
        user_id: int,
        reference_date: date | None = None,
    ) -> bool:
        """Пересчитывает exception резерва для месяца на основе взносов.

        Вызывается при:
        - Добавлении взноса (GoalService.add_contribution)
        - Удалении взноса
        - Изменении суммы взноса

        Логика:
        - Если взносов нет → удаляем exception (резерв = полный бюджет)
        - Если есть взносы → создаём/обновляем exception с уменьшенной суммой

        Args:
            user_id: ID пользователя.
            reference_date: Дата в целевом месяце. По умолчанию — сегодня.
                           Используется для определения месяца и даты резерва.

        Returns:
            bool: True если exception был изменён/удалён, False если не применимо.
        """
        if reference_date is None:
            reference_date = date.today()

        settings = self.get_settings(user_id)

        # Guard: только fixed_date режим
        if settings["mode"] != "fixed_date":
            return False

        reserve_date = self._get_reserve_date_for_month(user_id, reference_date)
        if reserve_date is None:
            return False

        # Guard: не пересчитываем прошедшие даты
        # Если reserve_date == today, recurring экземпляр ещё не материализован
        if reserve_date < date.today():
            logger.debug(f"Reserve date {reserve_date} already passed, skipping recalc")
            return False

        template = self._get_reserve_template(user_id)
        if not template:
            logger.warning(f"No active template for user {user_id}, skipping recalc")
            return False

        # Считаем взносы ДО даты резерва (< reserve_date)
        contributions_sum = self._get_contributions_sum_for_month(
            user_id, reference_date, before_date=reserve_date
        )

        budget = settings["monthly_budget"]
        new_reserve = budget - contributions_sum

        if new_reserve == budget:
            # Нет взносов — удаляем exception (резерв = полный бюджет)
            deleted = self._delete_exception_for_date(template.id, reserve_date)
            if deleted:
                logger.info(
                    f"User {user_id}: removed exception for {reserve_date}, "
                    f"reserve = full budget {budget}"
                )
            return deleted
        else:
            # Создаём/обновляем exception с уменьшенной суммой
            from app.services import RecurringService

            recurring_service = RecurringService(self.session)
            recurring_service.create_exception(
                template_id=template.id,
                original_date=reserve_date,
                new_amount=max(new_reserve, Decimal("0")),
            )

            logger.info(
                f"User {user_id}: updated exception for {reserve_date}, "
                f"contributions={contributions_sum}, new_reserve={new_reserve}"
            )
            return True

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
        before_date: date | None = None,
    ) -> Decimal:
        """Суммирует взносы пользователя за месяц.

        Args:
            user_id: ID пользователя.
            reference_date: Дата в целевом месяце.
            before_date: Если указано, считает взносы строго ДО этой даты.
                         Используется для расчёта досрочных взносов до резерва.

        Returns:
            Decimal: Сумма взносов.
        """
        start_of_month = date(reference_date.year, reference_date.month, 1)

        if before_date is not None:
            # Взносы строго ДО указанной даты (< before_date)
            end_filter = GoalContribution.contribution_date < before_date
        else:
            # Весь месяц включительно
            _, last_day = monthrange(reference_date.year, reference_date.month)
            end_of_month = date(reference_date.year, reference_date.month, last_day)
            end_filter = GoalContribution.contribution_date <= end_of_month

        # Join через Goal для фильтрации по user_id
        result = (
            self.session.query(func.coalesce(func.sum(GoalContribution.amount), 0))
            .join(Goal, GoalContribution.goal_id == Goal.id)
            .filter(
                Goal.user_id == user_id,
                GoalContribution.contribution_date >= start_of_month,
                end_filter,
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

    def _find_any_reserve_template(self, user_id: int) -> Transaction | None:
        """Находит любой recurring шаблон резерва (включая остановленный).

        В отличие от _get_reserve_template(), не фильтрует по recurring_end_date.
        Используется для переиспользования существующего шаблона при смене режима.

        Args:
            user_id: ID пользователя.

        Returns:
            Transaction | None: Последний созданный шаблон или None.
        """
        template = (
            self.session.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.is_recurring.is_(True),
                Transaction.transaction_type == TransactionType.SAVINGS_RESERVE,
            )
            .order_by(Transaction.created_at.desc())
            .first()
        )

        return template

    def _get_template_day(self, template: Transaction) -> int:
        """Извлекает день месяца из шаблона резерва.

        Args:
            template: Шаблон транзакции (is_recurring=True).

        Returns:
            int: День месяца (1-31). Для EOM anchor возвращает 31.
        """
        if template.recurring_anchor_eom:
            return 31

        # anchor_day — property, возвращает день из transaction_date
        return template.anchor_day or template.transaction_date.day

    def _get_reserve_date_for_month(
        self,
        user_id: int,
        reference_date: date,
    ) -> date | None:
        """Возвращает дату резерва для указанного месяца.

        Учитывает короткие месяцы: min(day_of_month, last_day_of_month).

        Args:
            user_id: ID пользователя.
            reference_date: Дата в целевом месяце.

        Returns:
            date | None: Дата резерва или None если режим != fixed_date.
        """
        settings = self.get_settings(user_id)

        if settings["mode"] != "fixed_date":
            return None

        day_of_month = settings["day_of_month"]
        if day_of_month is None:
            return None

        _, last_day = monthrange(reference_date.year, reference_date.month)
        actual_day = min(day_of_month, last_day)

        return date(reference_date.year, reference_date.month, actual_day)

    def _delete_exception_for_date(
        self,
        template_id: int,
        target_date: date,
    ) -> bool:
        """Удаляет exception для конкретной даты.

        Используется когда нет взносов — резерв должен быть полным (из шаблона).

        Args:
            template_id: ID шаблона.
            target_date: Дата экземпляра (original_date).

        Returns:
            bool: True если exception был удалён, False если не существовал.
        """
        exception = (
            self.session.query(Transaction)
            .filter(
                Transaction.recurring_parent_id == template_id,
                Transaction.original_date == target_date,
            )
            .first()
        )

        if not exception:
            return False

        self.session.delete(exception)
        self.session.flush()

        logger.info(
            f"Deleted exception for template {template_id} on date {target_date}"
        )

        return True

    def _cleanup_orphan_exceptions(self, template_id: int) -> int:
        """Удаляет exceptions для остановленного шаблона.

        Вызывается при изменении дня месяца для очистки
        невалидных exceptions от старого шаблона.
        Удаляет ВСЕ exceptions для шаблона с recurring_end_date < today.

        Args:
            template_id: ID остановленного шаблона.

        Returns:
            int: Количество удалённых exceptions.
        """
        # Находим и удаляем все exceptions для шаблона
        exceptions_to_delete = (
            self.session.query(Transaction)
            .filter(
                Transaction.recurring_parent_id == template_id,
                Transaction.original_date.isnot(None),  # Это exception
            )
            .all()
        )

        count = len(exceptions_to_delete)
        for exc in exceptions_to_delete:
            self.session.delete(exc)

        if count > 0:
            self.session.flush()
            logger.info(
                f"Cleaned up {count} orphan exception(s) for template {template_id}"
            )
        else:
            logger.debug(f"No orphan exceptions to clean up for template {template_id}")

        return count

    # === CRUD методы для SAVINGS_CONTRIBUTION ===

    def create_contribution_transaction(
        self,
        user_id: int,
        goal_name: str,
        amount: Decimal,
        contribution_date: date,
    ) -> Transaction | None:
        """Создаёт транзакцию SAVINGS_CONTRIBUTION для режима from_balance.

        В режиме fixed_date транзакции создаются автоматически через recurring,
        поэтому метод возвращает None.

        Args:
            user_id: ID пользователя.
            goal_name: Название цели для описания транзакции.
            amount: Сумма взноса.
            contribution_date: Дата взноса.

        Returns:
            Transaction | None: Созданная транзакция или None для fixed_date.
        """
        settings = self.get_settings(user_id)
        if settings["mode"] == "fixed_date":
            logger.debug(f"User {user_id} in fixed_date mode, skipping transaction")
            return None

        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=TransactionType.SAVINGS_CONTRIBUTION,
            transaction_date=contribution_date,
            description=f"Взнос: {goal_name}",
            category_id=None,  # Не расход с категорией
        )

        self.session.add(transaction)
        self.session.flush()

        logger.info(
            f"Created contribution transaction {transaction.id} for user {user_id}: "
            f"goal={goal_name}, amount={amount}"
        )

        return transaction

    def update_contribution_transaction(
        self,
        transaction_id: int,
        new_amount: Decimal,
    ) -> bool:
        """Обновляет сумму транзакции и синхронизирует GoalContribution.

        Args:
            transaction_id: ID транзакции.
            new_amount: Новая сумма.

        Returns:
            bool: True если обновление успешно, False если транзакция не найдена.
        """
        transaction = self.session.get(Transaction, transaction_id)
        if not transaction:
            logger.warning(f"Transaction {transaction_id} not found")
            return False

        if transaction.transaction_type != TransactionType.SAVINGS_CONTRIBUTION:
            logger.warning(f"Transaction {transaction_id} is not SAVINGS_CONTRIBUTION")
            return False

        old_amount = transaction.amount
        delta = new_amount - old_amount

        # Обновляем транзакцию
        transaction.amount = new_amount
        self.session.flush()

        # Находим связанный GoalContribution
        contribution = (
            self.session.query(GoalContribution)
            .filter(GoalContribution.transaction_id == transaction_id)
            .first()
        )

        if contribution:
            # Обновляем GoalContribution
            contribution.amount = new_amount

            # Обновляем Goal.current_amount
            goal = contribution.goal
            goal.current_amount = goal.current_amount + delta

            # Проверяем статус
            if goal.current_amount >= goal.target_amount:
                if goal.status != GoalStatus.COMPLETED:
                    goal.status = GoalStatus.COMPLETED
                    logger.info(f"Goal {goal.id} marked as COMPLETED")
            else:
                if goal.status == GoalStatus.COMPLETED:
                    goal.status = GoalStatus.ACTIVE
                    logger.info(f"Goal {goal.id} reverted to ACTIVE")

            self.session.flush()

            # Пересчитываем exception для месяца взноса
            self.recalculate_current_month_exception(
                user_id=goal.user_id,
                reference_date=contribution.contribution_date,
            )

        logger.info(
            f"Updated transaction {transaction_id}: {old_amount} -> {new_amount}"
        )
        return True

    def delete_contribution_transaction(self, transaction_id: int) -> bool:
        """Удаляет транзакцию и связанный GoalContribution.

        Args:
            transaction_id: ID транзакции.

        Returns:
            bool: True если удаление успешно, False если не найдена.
        """
        transaction = self.session.get(Transaction, transaction_id)
        if not transaction:
            logger.warning(f"Transaction {transaction_id} not found")
            return False

        if transaction.transaction_type != TransactionType.SAVINGS_CONTRIBUTION:
            logger.warning(f"Transaction {transaction_id} is not SAVINGS_CONTRIBUTION")
            return False

        # Находим связанный GoalContribution
        contribution = (
            self.session.query(GoalContribution)
            .filter(GoalContribution.transaction_id == transaction_id)
            .first()
        )

        if contribution:
            amount = contribution.amount
            goal = contribution.goal

            # Уменьшаем Goal.current_amount
            goal.current_amount = goal.current_amount - amount

            # Откатываем статус если был COMPLETED
            if goal.status == GoalStatus.COMPLETED:
                goal.status = GoalStatus.ACTIVE
                logger.info(f"Goal {goal.id} reverted to ACTIVE")

            # Удаляем GoalContribution
            self.session.delete(contribution)

        # Удаляем транзакцию
        self.session.delete(transaction)
        self.session.flush()

        logger.info(f"Deleted transaction {transaction_id}")
        return True

    def sync_template_amount(self, user_id: int) -> bool:
        """Синхронизирует сумму recurring шаблона с monthly_savings_budget.

        Вызывается при изменении бюджета пользователем.

        Args:
            user_id: ID пользователя.

        Returns:
            bool: True если шаблон обновлён, False если не найден.
        """
        template = self._get_reserve_template(user_id)
        if not template:
            logger.debug(f"No active template for user {user_id}")
            return False

        user = self.session.get(User, user_id)
        if not user:
            return False

        new_amount = Decimal(user.monthly_savings_budget)

        if template.amount != new_amount:
            old_amount = template.amount
            template.amount = new_amount
            self.session.flush()

            logger.info(
                f"Synced template {template.id} amount: {old_amount} -> {new_amount}"
            )

        return True

    def adjust_reserve_for_contribution(
        self,
        user_id: int,
        contribution_date: date,
        contribution_amount: Decimal,
    ) -> None:
        """Корректирует сумму резерва при досрочном взносе (режим fixed_date).

        Создаёт/обновляет Exception для recurring шаблона резервирования.
        Вызывается из GoalService.add_contribution() если:
        - Режим = fixed_date
        - contribution_date < reservation_day текущего месяца

        Args:
            user_id: ID пользователя.
            contribution_date: Дата взноса.
            contribution_amount: Сумма взноса (для логирования).
        """
        # 1. Получить настройки
        settings = self.get_settings(user_id)

        # 2. Guard: только для fixed_date режима
        if settings["mode"] != "fixed_date":
            return

        # 3. Определить дату резерва текущего месяца
        reserve_day = settings["day_of_month"]
        if reserve_day is None:
            return

        # Дата резерва в текущем месяце (учитываем короткие месяцы)
        _, last_day = monthrange(contribution_date.year, contribution_date.month)
        reserve_date = date(
            contribution_date.year,
            contribution_date.month,
            min(reserve_day, last_day),
        )

        # 4. Guard: взнос после резерва — не корректируем
        if contribution_date >= reserve_date:
            return

        # 5. Получить шаблон резерва
        template = self._get_reserve_template(user_id)
        if not template:
            return

        # 6. Посчитать сумму взносов до даты резерва в текущем месяце
        month_start = date(contribution_date.year, contribution_date.month, 1)
        contributions_sum = (
            self.session.query(func.coalesce(func.sum(GoalContribution.amount), 0))
            .join(Goal, Goal.id == GoalContribution.goal_id)
            .filter(
                Goal.user_id == user_id,
                GoalContribution.contribution_date >= month_start,
                GoalContribution.contribution_date < reserve_date,
            )
            .scalar()
        )
        contributions_sum = Decimal(str(contributions_sum))

        # 7. Рассчитать новую сумму
        budget = settings["monthly_budget"]
        new_amount = max(budget - contributions_sum, Decimal("0"))

        # 8. Определить description
        if new_amount == 0:
            description = f"{RESERVE_DESCRIPTION} (внесено досрочно)"
        else:
            description = RESERVE_DESCRIPTION

        # 9. Создать/обновить Exception
        from app.services import RecurringService

        recurring_service = RecurringService(self.session)
        recurring_service.create_exception(
            template_id=template.id,
            original_date=reserve_date,
            new_amount=new_amount,
            new_description=description,
        )

        logger.info(
            f"User {user_id}: adjusted reserve for {reserve_date}, "
            f"contribution={contribution_amount}, new_amount={new_amount}"
        )
