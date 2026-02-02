"""Сервис для расчета кассовых остатков календаря."""

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict

from loguru import logger
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.database import Transaction, TransactionType, User


class MonthSummary(TypedDict):
    """Сводка по месяцу для статистических карточек."""

    total_income: Decimal
    total_expense: Decimal
    start_balance: Decimal
    end_balance: Decimal
    month: int
    year: int


class TransactionInfo(TypedDict):
    """Информация о транзакции для UI календаря.

    Используется вместо ORM-объекта Transaction для передачи
    данных из CalendarService в UI-компоненты после закрытия сессии БД.
    Поддерживает как обычные транзакции, так и recurring instances.
    """

    id: int | None  # ID транзакции (None для виртуальных recurring)
    template_id: int | None  # ID шаблона для recurring (None для обычных)
    transaction_type: str  # income/expense/savings_reserve/savings_contribution/...
    amount: str  # Decimal в строковом формате
    description: str | None  # Описание
    date: str  # ISO format (YYYY-MM-DD)
    is_virtual: bool  # True для виртуальных recurring instances
    is_recurring: bool  # True для recurring (виртуальных и exceptions)
    is_exception: bool  # True для exceptions (материализованных recurring)
    is_skipped: bool  # True для пропущенных recurring instances
    category_id: int | None  # ID категории (None = без категории)
    category_name: str | None  # Название категории для UI
    category_icon: str | None  # Bootstrap icon class (bi-cart, etc.)


class YearSummary(TypedDict):
    """Сводка по году для дашборда."""

    total_income: Decimal
    total_expense: Decimal
    year: int


class CalendarService:
    """Сервис для расчета кассовых остатков по дням.

    Предоставляет методы для:
    - Расчета ежедневных балансов за период
    - Получения транзакций по датам
    - Формирования сводки по месяцу

    Примечание: TRANSFER транзакции исключаются из расчетов баланса,
    так как они являются внутренними переводами между счетами.
    """

    def __init__(self, session: Session):
        """Инициализирует сервис календаря.

        Args:
            session: SQLAlchemy сессия для работы с БД
        """
        self.session = session

    def _get_starting_balance(self, user_id: int) -> Decimal:
        """Получает начальный баланс пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Decimal: Начальный баланс или Decimal('0') если пользователь
                     не найден или starting_balance не установлен
        """
        user = self.session.query(User).filter(User.id == user_id).first()

        # Guard: пользователь не найден
        if user is None:
            logger.warning(f"User {user_id} не найден, используем starting_balance=0")
            return Decimal("0")

        # Guard: starting_balance не установлен
        if user.starting_balance is None:
            return Decimal("0")

        return Decimal(str(user.starting_balance))

    def calculate_daily_balances(
        self, user_id: int, start_date: date, end_date: date
    ) -> dict[date, Decimal]:
        """Рассчитывает баланс на каждый день периода.

        Формула: balance(date) = starting_balance + SUM(INCOME) - SUM(EXPENSE)
        где суммы считаются от начала времен до указанной даты включительно.

        TRANSFER транзакции не учитываются в расчете баланса.

        Args:
            user_id: ID пользователя
            start_date: Начало периода (включительно)
            end_date: Конец периода (включительно)

        Returns:
            dict[date, Decimal]: Словарь {дата: баланс на конец дня}

        Raises:
            ValueError: Если start_date > end_date
        """
        # Guard: валидация дат
        if start_date > end_date:
            raise ValueError(
                f"start_date ({start_date}) не может быть позже end_date ({end_date})"
            )

        starting_balance = self._get_starting_balance(user_id)

        # 1. Получить сумму изменений ДО начала периода (обычные + recurring)
        balance_before_period = self._calculate_balance_before_date(user_id, start_date)
        recurring_before_period = self._calculate_recurring_before_date(
            user_id, start_date
        )

        # 2. Получить изменения по дням в периоде (обычные + recurring)
        daily_changes = self._get_daily_changes(user_id, start_date, end_date)
        recurring_daily = self._get_recurring_daily_changes(
            user_id, start_date, end_date
        )

        # Объединяем изменения
        all_daily_changes: dict[date, Decimal] = defaultdict(Decimal)
        for d, change in daily_changes.items():
            all_daily_changes[d] += change
        for d, change in recurring_daily.items():
            all_daily_changes[d] += change

        # 3. Кумулятивный расчет балансов
        result: dict[date, Decimal] = {}
        current_balance = (
            starting_balance + balance_before_period + recurring_before_period
        )

        current_date = start_date
        while current_date <= end_date:
            # Добавить изменение за текущий день (если есть)
            if current_date in all_daily_changes:
                current_balance += all_daily_changes[current_date]
            result[current_date] = current_balance
            current_date += timedelta(days=1)

        logger.debug(
            f"Рассчитаны балансы для user {user_id}: "
            f"{start_date} - {end_date}, {len(result)} дней"
        )

        return result

    def _calculate_balance_before_date(
        self, user_id: int, before_date: date
    ) -> Decimal:
        """Рассчитывает сумму всех изменений баланса до указанной даты.

        ADJUSTMENT учитывается как прямое изменение баланса.

        Args:
            user_id: ID пользователя
            before_date: Дата, до которой считать (не включительно)

        Returns:
            Decimal: Сумма изменений (INCOME + ADJUSTMENT - EXPENSE)
        """
        result = (
            self.session.query(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Transaction.transaction_type == TransactionType.INCOME,
                                Transaction.amount,
                            ),
                            (
                                Transaction.transaction_type
                                == TransactionType.ADJUSTMENT,
                                Transaction.amount,
                            ),
                            (
                                Transaction.transaction_type == TransactionType.EXPENSE,
                                -Transaction.amount,
                            ),
                            (
                                Transaction.transaction_type
                                == TransactionType.SAVINGS_RESERVE,
                                -Transaction.amount,
                            ),
                            (
                                Transaction.transaction_type
                                == TransactionType.SAVINGS_CONTRIBUTION,
                                -Transaction.amount,
                            ),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                )
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date < before_date,
                Transaction.transaction_type.in_(
                    [
                        TransactionType.INCOME,
                        TransactionType.EXPENSE,
                        TransactionType.ADJUSTMENT,
                        TransactionType.SAVINGS_RESERVE,
                        TransactionType.SAVINGS_CONTRIBUTION,
                    ]
                ),
                # Исключаем recurring шаблоны (учитываются отдельно)
                Transaction.is_recurring == False,  # noqa: E712
                # Исключаем exceptions (учитываются в recurring расчетах)
                Transaction.recurring_parent_id == None,  # noqa: E711
            )
            .scalar()
        )

        return Decimal(str(result)) if result else Decimal("0")

    def _get_daily_changes(
        self, user_id: int, start_date: date, end_date: date
    ) -> dict[date, Decimal]:
        """Получает изменения баланса по дням в периоде.

        ADJUSTMENT обрабатывается как прямое изменение баланса:
        - положительный amount увеличивает баланс
        - отрицательный amount уменьшает баланс

        Args:
            user_id: ID пользователя
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            dict[date, Decimal]: Словарь {дата: изменение баланса за день}
        """
        daily_changes_query = (
            self.session.query(
                Transaction.transaction_date,
                func.sum(
                    case(
                        (
                            Transaction.transaction_type == TransactionType.INCOME,
                            Transaction.amount,
                        ),
                        (
                            Transaction.transaction_type == TransactionType.ADJUSTMENT,
                            Transaction.amount,
                        ),
                        (
                            Transaction.transaction_type == TransactionType.EXPENSE,
                            -Transaction.amount,
                        ),
                        (
                            Transaction.transaction_type
                            == TransactionType.SAVINGS_RESERVE,
                            -Transaction.amount,
                        ),
                        (
                            Transaction.transaction_type
                            == TransactionType.SAVINGS_CONTRIBUTION,
                            -Transaction.amount,
                        ),
                        else_=Decimal("0"),
                    )
                ).label("daily_change"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.transaction_type.in_(
                    [
                        TransactionType.INCOME,
                        TransactionType.EXPENSE,
                        TransactionType.ADJUSTMENT,
                        TransactionType.SAVINGS_RESERVE,
                        TransactionType.SAVINGS_CONTRIBUTION,
                    ]
                ),
                # Исключаем recurring шаблоны (учитываются отдельно)
                Transaction.is_recurring == False,  # noqa: E712
                # Исключаем exceptions (учитываются в recurring расчетах)
                Transaction.recurring_parent_id == None,  # noqa: E711
            )
            .group_by(Transaction.transaction_date)
            .all()
        )

        return {
            row.transaction_date: Decimal(str(row.daily_change))
            for row in daily_changes_query
        }

    def _get_recurring_instances_for_period(
        self, user_id: int, start_date: date, end_date: date
    ) -> list[dict]:
        """Получает все recurring экземпляры для периода с учётом exceptions.

        Возвращает объединённый список:
        - Виртуальные экземпляры (генерируются из шаблонов)
        - Заменены на exceptions где есть
        - Исключены skipped экземпляры

        Args:
            user_id: ID пользователя
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            Список словарей с полями: date, amount, transaction_type
        """
        from app.services.recurring_service import RecurringService

        recurring_service = RecurringService(self.session)
        instances = recurring_service.get_instances_with_exceptions(
            user_id, start_date, end_date
        )

        results = []
        for instance in instances:
            if isinstance(instance, dict):  # VirtualTransaction
                results.append(
                    {
                        "date": date.fromisoformat(instance["instance_date"]),
                        "amount": Decimal(instance["amount"]),
                        "transaction_type": instance["transaction_type"],
                    }
                )
            else:  # Transaction (exception)
                # Пропускаем skipped
                if instance.is_skipped:
                    continue
                results.append(
                    {
                        "date": instance.transaction_date,
                        "amount": instance.amount,
                        "transaction_type": instance.transaction_type.value,
                    }
                )

        return results

    def _calculate_recurring_before_date(
        self, user_id: int, before_date: date
    ) -> Decimal:
        """Рассчитывает сумму recurring операций до указанной даты.

        Args:
            user_id: ID пользователя
            before_date: Дата, до которой считать (не включительно)

        Returns:
            Decimal: Сумма изменений (INCOME - EXPENSE) от recurring
        """
        from app.services.recurring_service import RecurringService

        # Определяем начало периода для recurring
        # Берём самую раннюю дату шаблона или год назад (для безопасности)
        recurring_service = RecurringService(self.session)
        templates = recurring_service.get_templates_for_user(user_id)

        if not templates:
            return Decimal("0")

        # Находим самую раннюю дату начала шаблона
        earliest_template_date = min(t.transaction_date for t in templates)

        # Если before_date раньше самого раннего шаблона — recurring нет
        if before_date <= earliest_template_date:
            return Decimal("0")

        # Получаем все recurring экземпляры от начала до before_date-1
        instances = self._get_recurring_instances_for_period(
            user_id,
            earliest_template_date,
            before_date - timedelta(days=1),
        )

        total = Decimal("0")
        for inst in instances:
            if inst["transaction_type"] == "income":
                total += inst["amount"]
            elif inst["transaction_type"] == "expense":
                total -= inst["amount"]

        return total

    def _get_recurring_daily_changes(
        self, user_id: int, start_date: date, end_date: date
    ) -> dict[date, Decimal]:
        """Получает изменения баланса от recurring операций по дням.

        Args:
            user_id: ID пользователя
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            dict[date, Decimal]: Словарь {дата: изменение баланса за день}
        """
        instances = self._get_recurring_instances_for_period(
            user_id, start_date, end_date
        )

        daily_changes: dict[date, Decimal] = defaultdict(Decimal)
        for inst in instances:
            if inst["transaction_type"] == "income":
                daily_changes[inst["date"]] += inst["amount"]
            elif inst["transaction_type"] in (
                "expense",
                "savings_reserve",
                "savings_contribution",
            ):
                daily_changes[inst["date"]] -= inst["amount"]

        return dict(daily_changes)

    def _get_recurring_totals_for_period(
        self, user_id: int, start_date: date, end_date: date
    ) -> tuple[Decimal, Decimal]:
        """Получает суммы доходов и расходов от recurring за период.

        Args:
            user_id: ID пользователя
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            tuple[Decimal, Decimal]: (total_income, total_expense)
        """
        instances = self._get_recurring_instances_for_period(
            user_id, start_date, end_date
        )

        total_income = Decimal("0")
        total_expense = Decimal("0")

        for inst in instances:
            if inst["transaction_type"] == "income":
                total_income += inst["amount"]
            elif inst["transaction_type"] in (
                "expense",
                "savings_reserve",
                "savings_contribution",
            ):
                total_expense += inst["amount"]

        return total_income, total_expense

    def get_transactions_by_date(
        self, user_id: int, start_date: date, end_date: date
    ) -> dict[date, list[TransactionInfo]]:
        """Получает транзакции пользователя, сгруппированные по датам.

        Возвращает легковесные словари вместо ORM-объектов для безопасного
        использования после закрытия сессии БД.

        В отличие от calculate_daily_balances, этот метод включает ВСЕ типы
        транзакций (включая TRANSFER и ADJUSTMENT) для отображения в UI.

        Args:
            user_id: ID пользователя
            start_date: Начало периода (включительно)
            end_date: Конец периода (включительно)

        Returns:
            dict[date, list[TransactionInfo]]: Словарь {дата: данные транзакций}
                (НЕ ORM-объекты!)
        """
        transactions = (
            self.session.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                # Исключаем recurring шаблоны (учитываются отдельно)
                Transaction.is_recurring == False,  # noqa: E712
            )
            .order_by(Transaction.transaction_date, Transaction.id)
            .all()
        )

        result: dict[date, list[TransactionInfo]] = defaultdict(list)
        for txn in transactions:
            is_exception = txn.recurring_parent_id is not None
            txn_info: TransactionInfo = {
                "id": txn.id,
                "template_id": txn.recurring_parent_id,
                "transaction_type": (
                    txn.transaction_type.value if txn.transaction_type else "unknown"
                ),
                "amount": str(txn.amount) if txn.amount is not None else "0",
                "description": txn.description,
                "date": txn.transaction_date.isoformat(),
                "is_virtual": False,
                "is_recurring": is_exception,
                "is_exception": is_exception,
                "category_id": txn.category_id,
                "category_name": txn.category_rel.name if txn.category_rel else None,
            }
            result[txn.transaction_date].append(txn_info)

        return dict(result)

    def get_month_summary(self, user_id: int, year: int, month: int) -> MonthSummary:
        """Формирует сводку по месяцу для статистических карточек.

        Args:
            user_id: ID пользователя
            year: Год
            month: Месяц (1-12)

        Returns:
            MonthSummary: Сводка с total_income, total_expense,
                          start_balance, end_balance
        """
        # Определяем границы месяца
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        # Получаем балансы на начало и конец месяца
        daily_balances = self.calculate_daily_balances(user_id, first_day, last_day)

        # Агрегируем INCOME и EXPENSE за месяц
        income_expense = (
            self.session.query(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Transaction.transaction_type == TransactionType.INCOME,
                                Transaction.amount,
                            ),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("total_income"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Transaction.transaction_type == TransactionType.EXPENSE,
                                Transaction.amount,
                            ),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("total_expense"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= first_day,
                Transaction.transaction_date <= last_day,
                Transaction.transaction_type.in_(
                    [TransactionType.INCOME, TransactionType.EXPENSE]
                ),
                # Исключаем recurring шаблоны (учитываются отдельно)
                Transaction.is_recurring == False,  # noqa: E712
                # Исключаем exceptions (учитываются в recurring расчетах)
                Transaction.recurring_parent_id == None,  # noqa: E711
            )
            .first()
        )

        # Добавляем recurring суммы
        recurring_income, recurring_expense = self._get_recurring_totals_for_period(
            user_id, first_day, last_day
        )

        total_income = Decimal(str(income_expense.total_income)) + recurring_income
        total_expense = Decimal(str(income_expense.total_expense)) + recurring_expense

        # Баланс на начало месяца = баланс на день ДО первого дня
        # (т.е. баланс на конец предыдущего дня)
        starting_balance = self._get_starting_balance(user_id)
        balance_before_month = self._calculate_balance_before_date(user_id, first_day)
        recurring_before_month = self._calculate_recurring_before_date(
            user_id, first_day
        )
        start_balance = starting_balance + balance_before_month + recurring_before_month

        return MonthSummary(
            total_income=total_income,
            total_expense=total_expense,
            start_balance=start_balance,
            end_balance=daily_balances[last_day],
            month=month,
            year=year,
        )

    def get_balance_on_date(self, user_id: int, target_date: date) -> Decimal:
        """Рассчитывает баланс пользователя на указанную дату (включительно).

        Формула: starting_balance + SUM(INCOME) - SUM(EXPENSE)
        до target_date включительно.

        TRANSFER транзакции не учитываются.

        Args:
            user_id: ID пользователя
            target_date: Дата на которую считается баланс (включительно)

        Returns:
            Decimal: Баланс на конец дня target_date

        Note:
            Для несуществующего user_id возвращает Decimal('0').
        """
        starting_balance = self._get_starting_balance(user_id)
        # +1 день т.к. _calculate_balance_before_date НЕ включает дату
        changes_up_to_date = self._calculate_balance_before_date(
            user_id, target_date + timedelta(days=1)
        )
        recurring_up_to_date = self._calculate_recurring_before_date(
            user_id, target_date + timedelta(days=1)
        )
        return starting_balance + changes_up_to_date + recurring_up_to_date

    def get_year_summary(self, user_id: int, year: int) -> YearSummary:
        """Формирует сводку по году.

        Args:
            user_id: ID пользователя
            year: Год (например, 2026)

        Returns:
            YearSummary: Сводка с total_income, total_expense за год
        """
        first_day = date(year, 1, 1)
        last_day = date(year, 12, 31)

        result = (
            self.session.query(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Transaction.transaction_type == TransactionType.INCOME,
                                Transaction.amount,
                            ),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("total_income"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Transaction.transaction_type == TransactionType.EXPENSE,
                                Transaction.amount,
                            ),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("total_expense"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= first_day,
                Transaction.transaction_date <= last_day,
                Transaction.transaction_type.in_(
                    [TransactionType.INCOME, TransactionType.EXPENSE]
                ),
                # Исключаем recurring шаблоны (учитываются отдельно)
                Transaction.is_recurring == False,  # noqa: E712
                # Исключаем exceptions (учитываются в recurring расчетах)
                Transaction.recurring_parent_id == None,  # noqa: E711
            )
            .first()
        )

        # Добавляем recurring суммы
        recurring_income, recurring_expense = self._get_recurring_totals_for_period(
            user_id, first_day, last_day
        )

        total_income = (
            Decimal(str(result.total_income)) if result.total_income else Decimal("0")
        ) + recurring_income
        total_expense = (
            Decimal(str(result.total_expense)) if result.total_expense else Decimal("0")
        ) + recurring_expense

        return YearSummary(
            total_income=total_income,
            total_expense=total_expense,
            year=year,
        )

    def get_all_transactions_for_period(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        include_recurring: bool = True,
    ) -> dict[date, list[TransactionInfo]]:
        """Получает все транзакции включая recurring для периода.

        Объединяет:
        - Обычные транзакции из БД (is_recurring=False, recurring_parent_id=None)
        - Виртуальные recurring экземпляры из RecurringService (если include_recurring)
        - Exceptions заменяют виртуальные на соответствующие даты

        Args:
            user_id: ID пользователя.
            start_date: Начало периода.
            end_date: Конец периода.
            include_recurring: Включать ли recurring операции.

        Returns:
            Словарь: дата -> список транзакций.
        """
        from app.services.recurring_service import RecurringService

        result: dict[date, list[TransactionInfo]] = defaultdict(list)

        # 1. Получить обычные транзакции (не шаблоны, не exceptions)
        regular_transactions = (
            self.session.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_recurring == False,  # noqa: E712
                Transaction.recurring_parent_id == None,  # noqa: E711
            )
            .order_by(Transaction.transaction_date, Transaction.id)
            .all()
        )

        for txn in regular_transactions:
            result[txn.transaction_date].append(
                TransactionInfo(
                    id=txn.id,
                    template_id=None,
                    amount=str(txn.amount),
                    transaction_type=txn.transaction_type.value,
                    description=txn.description,
                    date=txn.transaction_date.isoformat(),
                    is_virtual=False,
                    is_recurring=False,
                    is_exception=False,
                    is_skipped=False,  # Regular transactions cannot be skipped
                    category_id=txn.category_id,
                    category_name=txn.category_rel.name if txn.category_rel else None,
                    category_icon=txn.category_rel.icon if txn.category_rel else None,
                )
            )

        # 2. Добавить recurring экземпляры (если запрошено)
        if include_recurring:
            recurring_service = RecurringService(self.session)
            recurring_instances = recurring_service.get_instances_with_exceptions(
                user_id, start_date, end_date
            )

            for instance in recurring_instances:
                if isinstance(instance, dict):  # VirtualTransaction
                    instance_date = date.fromisoformat(instance["instance_date"])
                    result[instance_date].append(
                        TransactionInfo(
                            id=None,
                            template_id=instance["template_id"],
                            amount=instance["amount"],
                            transaction_type=instance["transaction_type"],
                            description=instance["description"],
                            date=instance["instance_date"],
                            is_virtual=True,
                            is_recurring=True,
                            is_exception=False,
                            is_skipped=instance.get("is_skipped", False),
                            category_id=instance.get("category_id"),
                            category_name=instance.get("category_name"),
                            category_icon=instance.get("category_icon"),
                        )
                    )
                else:  # Transaction (exception)
                    result[instance.transaction_date].append(
                        TransactionInfo(
                            id=instance.id,
                            template_id=instance.recurring_parent_id,
                            amount=str(instance.amount),
                            transaction_type=instance.transaction_type.value,
                            description=instance.description,
                            date=instance.transaction_date.isoformat(),
                            is_virtual=False,
                            is_recurring=True,
                            is_exception=True,
                            is_skipped=instance.is_skipped,
                            category_id=instance.category_id,
                            category_name=(
                                instance.category_rel.name
                                if instance.category_rel
                                else None
                            ),
                            category_icon=(
                                instance.category_rel.icon
                                if instance.category_rel
                                else None
                            ),
                        )
                    )

        logger.debug(
            f"get_all_transactions_for_period: {sum(len(v) for v in result.values())} "
            f"транзакций для пользователя {user_id} в периоде {start_date} - {end_date}"
        )

        return dict(result)
