"""Сервис для агрегации данных дашборда."""

from datetime import date
from decimal import Decimal
from typing import Literal, TypedDict

from dateutil.relativedelta import relativedelta
from sqlalchemy import case, desc, func
from sqlalchemy.orm import Session

from app.models.database import GoalStatus, Transaction, TransactionType
from app.services.calendar_service import CalendarService
from app.services.goal_service import GoalService

PeriodType = Literal["month", "year"]

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
    ) -> list[RecentTransaction]:
        """Получает последние транзакции с информацией о категории.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество (по умолчанию 5)

        Returns:
            list[RecentTransaction]: последние транзакции
                с category_name и category_icon

        Note:
            - Исключает recurring шаблоны (is_recurring=True без parent)
            - Сортировка: transaction_date DESC, id DESC (для стабильности)
        """
        transactions = (
            self.session.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .filter(Transaction.is_recurring == False)  # noqa: E712
            .filter(Transaction.recurring_parent_id == None)  # noqa: E711
            .order_by(desc(Transaction.transaction_date), desc(Transaction.id))
            .limit(limit)
            .all()
        )

        return [
            RecentTransaction(
                id=t.id,
                description=t.description,
                category_name=t.category_rel.name if t.category_rel else None,
                category_icon=t.category_rel.icon if t.category_rel else None,
                date=t.transaction_date.isoformat(),
                amount=t.amount,
                transaction_type=t.transaction_type.value,
            )
            for t in transactions
        ]
