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
    """Минимальные данные о транзакции для UI календаря.

    Используется вместо ORM-объекта Transaction для передачи
    данных из CalendarService в UI-компоненты после закрытия сессии БД.
    Поле description добавлено для расширяемости (tooltip в будущем).
    """

    id: int  # ID транзакции
    transaction_type: str  # "income" | "expense" | "transfer"
    amount: str  # Decimal в строковом формате
    description: str | None  # Описание (для будущих tooltip)


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

        # 1. Получить сумму изменений ДО начала периода
        balance_before_period = self._calculate_balance_before_date(user_id, start_date)

        # 2. Получить изменения по дням в периоде
        daily_changes = self._get_daily_changes(user_id, start_date, end_date)

        # 3. Кумулятивный расчет балансов
        result: dict[date, Decimal] = {}
        current_balance = starting_balance + balance_before_period

        current_date = start_date
        while current_date <= end_date:
            # Добавить изменение за текущий день (если есть)
            if current_date in daily_changes:
                current_balance += daily_changes[current_date]
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

        Args:
            user_id: ID пользователя
            before_date: Дата, до которой считать (не включительно)

        Returns:
            Decimal: Сумма изменений (INCOME - EXPENSE)
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
                                Transaction.transaction_type == TransactionType.EXPENSE,
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
                    [TransactionType.INCOME, TransactionType.EXPENSE]
                ),
            )
            .scalar()
        )

        return Decimal(str(result)) if result else Decimal("0")

    def _get_daily_changes(
        self, user_id: int, start_date: date, end_date: date
    ) -> dict[date, Decimal]:
        """Получает изменения баланса по дням в периоде.

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
                            Transaction.transaction_type == TransactionType.EXPENSE,
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
                    [TransactionType.INCOME, TransactionType.EXPENSE]
                ),
            )
            .group_by(Transaction.transaction_date)
            .all()
        )

        return {
            row.transaction_date: Decimal(str(row.daily_change))
            for row in daily_changes_query
        }

    def get_transactions_by_date(
        self, user_id: int, start_date: date, end_date: date
    ) -> dict[date, list[TransactionInfo]]:
        """Получает транзакции пользователя, сгруппированные по датам.

        Возвращает легковесные словари вместо ORM-объектов для безопасного
        использования после закрытия сессии БД.

        В отличие от calculate_daily_balances, этот метод включает ВСЕ типы
        транзакций (включая TRANSFER) для отображения в UI.

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
            )
            .order_by(Transaction.transaction_date, Transaction.id)
            .all()
        )

        result: dict[date, list[TransactionInfo]] = defaultdict(list)
        for txn in transactions:
            # Defensive coding: защита от corrupted data
            txn_info: TransactionInfo = {
                "id": txn.id,
                "transaction_type": (
                    txn.transaction_type.value if txn.transaction_type else "unknown"
                ),
                "amount": str(txn.amount) if txn.amount is not None else "0",
                "description": txn.description,
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
            )
            .first()
        )

        # Баланс на начало месяца = баланс на день ДО первого дня
        # (т.е. баланс на конец предыдущего дня)
        starting_balance = self._get_starting_balance(user_id)
        balance_before_month = self._calculate_balance_before_date(user_id, first_day)
        start_balance = starting_balance + balance_before_month

        return MonthSummary(
            total_income=Decimal(str(income_expense.total_income)),
            total_expense=Decimal(str(income_expense.total_expense)),
            start_balance=start_balance,
            end_balance=daily_balances[last_day],
            month=month,
            year=year,
        )
