"""Сервис для агрегации данных дашборда."""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal, TypedDict

from dateutil.relativedelta import relativedelta
from sqlalchemy import asc, case, desc, func
from sqlalchemy.orm import Session

from app.models.database import GoalStatus, Transaction, TransactionType
from app.schema.dashboard import (
    BALANCE_ATTENTION_THRESHOLD,
    BALANCE_RISK_THRESHOLD,
    BalanceStatus,
    DailyBalancePoint,
    DailyCashflow,
    MonthlyCashflow,
    MonthlyCashflowData,
    YearlyCashflowData,
)
from app.services.calendar_service import CalendarService
from app.services.goal_service import GoalService

PeriodType = Literal["month", "year"]


def _classify_balance_status(balance: Decimal) -> BalanceStatus:
    """Определяет цветовой статус баланса по порогам.

    Args:
        balance: Остаток на конец дня.

    Returns:
        BalanceStatus: "risk" если <= 0, "attention" если < 5000, "ok" иначе.
    """
    if balance <= BALANCE_RISK_THRESHOLD:
        return "risk"
    elif balance < BALANCE_ATTENTION_THRESHOLD:
        return "attention"
    return "ok"


MONTH_NAMES_RU_SHORT = {
    1: "Янв",
    2: "Фев",
    3: "Мар",
    4: "Апр",
    5: "Май",
    6: "Июн",
    7: "Июл",
    8: "Авг",
    9: "Сен",
    10: "Окт",
    11: "Ноя",
    12: "Дек",
}


class OverviewMetrics(TypedDict):
    """Метрики для верхних карточек дашборда."""

    total_balance: Decimal
    period_income: Decimal
    period_expense: Decimal
    savings_current: Decimal
    savings_target: Decimal
    savings_name: str | None
    savings_progress: float


class CashflowDataPoint(TypedDict):
    """Точка данных для графика Cashflow."""

    label: str
    income: Decimal
    expense: Decimal


class RecentTransaction(TypedDict):
    """Данные транзакции для списка на дашборде."""

    id: int
    description: str | None
    category_name: str | None  # Название категории (из relationship)
    category_icon: str | None  # Иконка категории для UI
    date: str
    amount: Decimal
    transaction_type: str
    is_recurring_instance: bool  # True если recurring_parent_id != None


class DashboardService:
    """Сервис для агрегации данных дашборда.

    Использует CalendarService для расчета балансов и GoalService
    для получения данных о накопительных целях.

    Note: Для несуществующего user_id возвращает нулевые метрики.
    date.today() использует локальное время сервера.
    """

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: SQLAlchemy сессия для работы с БД
        """
        self.session = session
        self._calendar_service = CalendarService(session)
        self._goal_service = GoalService(session)

    def get_overview_metrics(
        self,
        user_id: int,
        period: PeriodType = "month",
        reference_date: date | None = None,
    ) -> OverviewMetrics:
        """Получает метрики для верхних карточек.

        Args:
            user_id: ID пользователя
            period: "month" или "year"
            reference_date: Дата отсчета (по умолчанию сегодня)

        Returns:
            OverviewMetrics с полями total_balance, period_income,
            period_expense, savings_*
        """
        if reference_date is None:
            reference_date = date.today()

        # 1. Total Balance на сегодня
        total_balance = self._calendar_service.get_balance_on_date(
            user_id, reference_date
        )

        # 2. Income/Expense за период
        if period == "month":
            summary = self._calendar_service.get_month_summary(
                user_id, reference_date.year, reference_date.month
            )
            period_income = summary["total_income"]
            period_expense = summary["total_expense"]
        else:  # year
            summary = self._calendar_service.get_year_summary(
                user_id, reference_date.year
            )
            period_income = summary["total_income"]
            period_expense = summary["total_expense"]

        # 3. Savings из всех активных целей
        active_goals = self._goal_service.get_all_by_user(
            user_id, status=GoalStatus.ACTIVE
        )

        if active_goals:
            # Агрегация по всем активным целям
            savings_current = sum(g.current_amount for g in active_goals)
            savings_target = sum(g.target_amount for g in active_goals)
            savings_progress = (
                float(savings_current / savings_target * 100)
                if savings_target > 0
                else 0.0
            )

            # Название зависит от количества целей
            if len(active_goals) == 1:
                savings_name = active_goals[0].name
            else:
                savings_name = f"{len(active_goals)} целей"
        else:
            savings_current = Decimal("0")
            savings_target = Decimal("0")
            savings_name = "Нет целей"
            savings_progress = 0.0

        return OverviewMetrics(
            total_balance=total_balance,
            period_income=period_income,
            period_expense=period_expense,
            savings_current=savings_current,
            savings_target=savings_target,
            savings_name=savings_name,
            savings_progress=savings_progress,
        )

    def get_cashflow_data(
        self,
        user_id: int,
        period: PeriodType = "month",
        reference_date: date | None = None,
    ) -> list[CashflowDataPoint]:
        """Получает данные для графика Cashflow.

        Args:
            user_id: ID пользователя
            period: определяет группировку данных
            reference_date: Дата отсчета (по умолчанию сегодня)

        Returns:
            list[CashflowDataPoint]: данные для графика

        Behavior by period:
            - month: последние 12 месяцев, группировка по месяцам
            - year: последние 5 лет, группировка по годам
        """
        if reference_date is None:
            reference_date = date.today()

        if period == "month":
            return self._get_monthly_cashflow(user_id, reference_date)
        else:
            return self._get_yearly_cashflow(user_id, reference_date)

    def _get_monthly_cashflow(
        self, user_id: int, reference_date: date
    ) -> list[CashflowDataPoint]:
        """Получает cashflow за последние 12 месяцев."""
        start_date = (reference_date - relativedelta(months=11)).replace(day=1)

        results = (
            self.session.query(
                func.strftime("%Y", Transaction.transaction_date).label("year"),
                func.strftime("%m", Transaction.transaction_date).label("month"),
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
                ).label("income"),
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
                ).label("expense"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_type.in_(
                    [TransactionType.INCOME, TransactionType.EXPENSE]
                ),
            )
            .group_by("year", "month")
            .order_by("year", "month")
            .all()
        )

        # Формируем словарь результатов
        results_dict = {(r.year, r.month): r for r in results}

        # Формируем список за все 12 месяцев (включая пустые)
        data_points = []
        current = start_date

        for _ in range(12):
            key = (str(current.year), str(current.month).zfill(2))
            if key in results_dict:
                r = results_dict[key]
                income = Decimal(str(r.income)) if r.income else Decimal("0")
                expense = Decimal(str(r.expense)) if r.expense else Decimal("0")
            else:
                income = Decimal("0")
                expense = Decimal("0")

            data_points.append(
                CashflowDataPoint(
                    label=MONTH_NAMES_RU_SHORT[current.month],
                    income=income,
                    expense=expense,
                )
            )
            current = current + relativedelta(months=1)

        return data_points

    def _get_yearly_cashflow(
        self, user_id: int, reference_date: date
    ) -> list[CashflowDataPoint]:
        """Получает cashflow за последние 5 лет."""
        current_year = reference_date.year
        start_year = current_year - 4

        results = (
            self.session.query(
                func.strftime("%Y", Transaction.transaction_date).label("year"),
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
                ).label("income"),
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
                ).label("expense"),
            )
            .filter(
                Transaction.user_id == user_id,
                func.strftime("%Y", Transaction.transaction_date) >= str(start_year),
                Transaction.transaction_type.in_(
                    [TransactionType.INCOME, TransactionType.EXPENSE]
                ),
            )
            .group_by("year")
            .order_by("year")
            .all()
        )

        results_dict = {r.year: r for r in results}
        data_points = []

        for year in range(start_year, current_year + 1):
            key = str(year)
            if key in results_dict:
                r = results_dict[key]
                income = Decimal(str(r.income)) if r.income else Decimal("0")
                expense = Decimal(str(r.expense)) if r.expense else Decimal("0")
            else:
                income = Decimal("0")
                expense = Decimal("0")

            data_points.append(
                CashflowDataPoint(
                    label=str(year),
                    income=income,
                    expense=expense,
                )
            )

        return data_points

    def get_recent_transactions(
        self,
        user_id: int,
        limit: int = 5,
        reference_date: date | None = None,
    ) -> list[RecentTransaction]:
        """Получает недавние операции (1 число месяца..reference_date).

        INTENTIONAL SEMANTIC CHANGE: предыдущая версия возвращала последние N
        транзакций за все время. Новая версия фильтрует по текущему месяцу
        (first_of_month..reference_date). При отсутствии данных — пустой список.

        Фильтрация:
        - Исключает recurring шаблоны (is_recurring=True AND recurring_parent_id IS NULL)
        - Включает recurring instances (recurring_parent_id IS NOT NULL)
        - Включает обычные транзакции (is_recurring=False)

        Args:
            user_id: ID пользователя
            limit: Максимальное количество (по умолчанию 5)
            reference_date: Дата отсчета (по умолчанию сегодня)

        Returns:
            list[RecentTransaction]: транзакции, сортировка date DESC, id DESC
        """
        if reference_date is None:
            reference_date = date.today()

        first_of_month = reference_date.replace(day=1)

        transactions = (
            self.session.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= first_of_month,
                Transaction.transaction_date <= reference_date,
                # Исключить только шаблоны recurring
                ~(
                    (Transaction.is_recurring == True)  # noqa: E712
                    & (Transaction.recurring_parent_id == None)  # noqa: E711
                ),
            )
            .order_by(desc(Transaction.transaction_date), desc(Transaction.id))
            .limit(limit)
            .all()
        )

        return self._map_transactions(transactions)

    def get_upcoming_transactions(
        self,
        user_id: int,
        limit: int = 5,
        reference_date: date | None = None,
    ) -> list[RecentTransaction]:
        """Получает предстоящие операции (reference_date..конец месяца).

        Фильтрация идентична get_recent_transactions():
        - Исключает recurring шаблоны (is_recurring=True AND recurring_parent_id IS NULL)
        - Включает recurring instances (recurring_parent_id IS NOT NULL)

        Args:
            user_id: ID пользователя
            limit: Максимальное количество (по умолчанию 5)
            reference_date: Дата отсчета (по умолчанию сегодня)

        Returns:
            list[RecentTransaction]: предстоящие операции, сортировка date ASC, id ASC
        """
        if reference_date is None:
            reference_date = date.today()

        _, last_day_num = monthrange(reference_date.year, reference_date.month)
        end_of_month = date(
            reference_date.year, reference_date.month, last_day_num
        )

        transactions = (
            self.session.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= reference_date,
                Transaction.transaction_date <= end_of_month,
                # Исключить только шаблоны recurring
                ~(
                    (Transaction.is_recurring == True)  # noqa: E712
                    & (Transaction.recurring_parent_id == None)  # noqa: E711
                ),
            )
            .order_by(asc(Transaction.transaction_date), asc(Transaction.id))
            .limit(limit)
            .all()
        )

        return self._map_transactions(transactions)

    def _map_transactions(
        self, transactions: list[Transaction]
    ) -> list[RecentTransaction]:
        """Маппит ORM объекты Transaction в RecentTransaction TypedDict."""
        return [
            RecentTransaction(
                id=t.id,
                description=t.description,
                category_name=t.category_rel.name if t.category_rel else None,
                category_icon=t.category_rel.icon if t.category_rel else None,
                date=t.transaction_date.isoformat(),
                amount=t.amount,
                transaction_type=t.transaction_type.value,
                is_recurring_instance=t.recurring_parent_id is not None,
            )
            for t in transactions
        ]

    # --- Daily/Yearly Cashflow (Batch 5.2) ---

    def _get_daily_income_expense(
        self, user_id: int, start_date: date, end_date: date
    ) -> dict[date, tuple[Decimal, Decimal]]:
        """Получает доходы и расходы обычных транзакций по дням.

        Классификация типов:
        - INCOME → income
        - EXPENSE, SAVINGS_RESERVE, SAVINGS_CONTRIBUTION → expense
        - ADJUSTMENT: amount > 0 → income, amount < 0 → expense(abs)
          (Сознательное решение: ADJUSTMENT представляет реальное изменение
          баланса и должен отображаться в cashflow графике.)
        - TRANSFER → игнорируется

        Фильтры: is_recurring=False, recurring_parent_id=None
        (recurring учитываются отдельно через CalendarService).

        Args:
            user_id: ID пользователя.
            start_date: Начало периода (включительно).
            end_date: Конец периода (включительно).

        Returns:
            dict[date, tuple[Decimal, Decimal]]: {дата: (income, expense)}.
        """
        rows = (
            self.session.query(
                Transaction.transaction_date,
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Transaction.transaction_type == TransactionType.INCOME,
                                Transaction.amount,
                            ),
                            (
                                (
                                    Transaction.transaction_type
                                    == TransactionType.ADJUSTMENT
                                )
                                & (Transaction.amount > 0),
                                Transaction.amount,
                            ),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("day_income"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Transaction.transaction_type == TransactionType.EXPENSE,
                                Transaction.amount,
                            ),
                            (
                                Transaction.transaction_type
                                == TransactionType.SAVINGS_RESERVE,
                                Transaction.amount,
                            ),
                            (
                                Transaction.transaction_type
                                == TransactionType.SAVINGS_CONTRIBUTION,
                                Transaction.amount,
                            ),
                            (
                                (
                                    Transaction.transaction_type
                                    == TransactionType.ADJUSTMENT
                                )
                                & (Transaction.amount < 0),
                                func.abs(Transaction.amount),
                            ),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("day_expense"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_recurring == False,  # noqa: E712
                Transaction.recurring_parent_id == None,  # noqa: E711
                Transaction.transaction_type != TransactionType.TRANSFER,
            )
            .group_by(Transaction.transaction_date)
            .all()
        )

        return {
            row.transaction_date: (
                Decimal(str(row.day_income)),
                Decimal(str(row.day_expense)),
            )
            for row in rows
        }

    def get_daily_cashflow(
        self,
        user_id: int,
        year: int,
        month: int,
        reference_date: date | None = None,
    ) -> MonthlyCashflowData:
        """Получает данные дневного cashflow за месяц.

        Объединяет обычные транзакции и recurring для каждого дня.
        Рассчитывает running balance через CalendarService.

        Args:
            user_id: ID пользователя.
            year: Год.
            month: Месяц (1-12).
            reference_date: Текущая дата для разделителя факт/прогноз.

        Returns:
            MonthlyCashflowData с daily list, min_balance_point, current_date.
        """
        if reference_date is None:
            reference_date = date.today()

        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        # 1. Running balance за каждый день
        balances = self._calendar_service.calculate_daily_balances(
            user_id, first_day, last_day
        )

        # 2. Обычные транзакции по дням
        regular = self._get_daily_income_expense(user_id, first_day, last_day)

        # 3. Recurring по дням
        recurring = self._calendar_service.get_recurring_income_expense_by_day(
            user_id, first_day, last_day
        )

        # 4. Merge: day-by-day
        daily_list: list[DailyCashflow] = []
        min_balance = None
        min_balance_date = first_day

        current = first_day
        while current <= last_day:
            reg_inc, reg_exp = regular.get(current, (Decimal("0"), Decimal("0")))
            rec_inc, rec_exp = recurring.get(current, (Decimal("0"), Decimal("0")))
            day_income = reg_inc + rec_inc
            day_expense = reg_exp + rec_exp
            day_balance = balances.get(current, Decimal("0"))

            daily_list.append(
                DailyCashflow(
                    date=current,
                    income=day_income,
                    expense=day_expense,
                    balance=day_balance,
                )
            )

            if min_balance is None or day_balance < min_balance:
                min_balance = day_balance
                min_balance_date = current

            current += timedelta(days=1)

        # min_balance гарантированно non-None (daily_list непуст)
        min_point = DailyBalancePoint(
            date=min_balance_date,
            balance=min_balance if min_balance is not None else Decimal("0"),
            status=_classify_balance_status(
                min_balance if min_balance is not None else Decimal("0")
            ),
        )

        return MonthlyCashflowData(
            daily=daily_list,
            min_balance_point=min_point,
            current_date=reference_date,
        )

    def _get_monthly_income_expense(
        self, user_id: int, year: int, month: int
    ) -> tuple[Decimal, Decimal]:
        """Получает суммарные доходы и расходы за месяц.

        Переиспользует _get_daily_income_expense() и суммирует результаты.
        Рекомендация critique-v2: не дублировать SQL CASE.

        Args:
            user_id: ID пользователя.
            year: Год.
            month: Месяц (1-12).

        Returns:
            tuple[Decimal, Decimal]: (total_income, total_expense).
        """
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        daily = self._get_daily_income_expense(user_id, first_day, last_day)

        total_income = Decimal("0")
        total_expense = Decimal("0")
        for inc, exp in daily.values():
            total_income += inc
            total_expense += exp

        return total_income, total_expense

    def get_yearly_cashflow(
        self,
        user_id: int,
        year: int,
        reference_date: date | None = None,
    ) -> YearlyCashflowData:
        """Получает данные годового cashflow (12 месяцев).

        Оптимизация по рекомендации critique-v2: один вызов
        calculate_daily_balances(Jan 1, Dec 31) вместо 12x get_balance_on_date.

        Args:
            user_id: ID пользователя.
            year: Год.
            reference_date: Текущая дата для разделителя факт/прогноз.

        Returns:
            YearlyCashflowData с monthly list, min_balance_point, year.
        """
        if reference_date is None:
            reference_date = date.today()

        first_day = date(year, 1, 1)
        last_day = date(year, 12, 31)

        # Один вызов для всех балансов за год (оптимизация)
        all_balances = self._calendar_service.calculate_daily_balances(
            user_id, first_day, last_day
        )

        monthly_list: list[MonthlyCashflow] = []
        min_balance = None
        min_balance_date = first_day

        for m in range(1, 13):
            month_last_day = date(year, m, monthrange(year, m)[1])

            # Regular + recurring income/expense
            reg_inc, reg_exp = self._get_monthly_income_expense(user_id, year, m)
            rec_inc, rec_exp = self._calendar_service._get_recurring_totals_for_period(
                user_id,
                date(year, m, 1),
                month_last_day,
            )

            month_income = reg_inc + rec_inc
            month_expense = reg_exp + rec_exp
            end_balance = all_balances.get(month_last_day, Decimal("0"))

            monthly_list.append(
                MonthlyCashflow(
                    month=m,
                    label=MONTH_NAMES_RU_SHORT[m],
                    income=month_income,
                    expense=month_expense,
                    end_balance=end_balance,
                )
            )

            if min_balance is None or end_balance < min_balance:
                min_balance = end_balance
                min_balance_date = month_last_day

        min_point = DailyBalancePoint(
            date=min_balance_date,
            balance=min_balance if min_balance is not None else Decimal("0"),
            status=_classify_balance_status(
                min_balance if min_balance is not None else Decimal("0")
            ),
        )

        return YearlyCashflowData(
            monthly=monthly_list,
            min_balance_point=min_point,
            current_date=reference_date,
            year=year,
        )
