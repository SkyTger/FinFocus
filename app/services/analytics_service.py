"""Сервис аналитики для агрегации расходов по категориям.

Предоставляет методы для построения аналитических графиков:
- Donut chart: структура расходов по категориям
- Bar chart: динамика расходов по месяцам
"""
import calendar
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models.database import Transaction, TransactionType, Category
from app.schema.analytics import CategorySummary, MonthlyTrend


if TYPE_CHECKING:
    pass

# Порог для группировки мелких категорий в "Прочее"
MIN_PERCENTAGE_THRESHOLD: float = 3.0

# Русские названия месяцев (сокращенные)
MONTH_LABELS_RU: dict[int, str] = {
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


class AnalyticsService:
    """Сервис аналитики расходов.

    Предоставляет методы для агрегации расходов по категориям
    и формирования данных для графиков.

    Attributes:
        session: SQLAlchemy сессия для работы с БД.
    """

    def __init__(self, session: Session) -> None:
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy сессия для работы с БД.
        """
        self.session = session

    def get_expenses_by_category(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        group_small: bool = True,
    ) -> list[CategorySummary]:
        """Получить агрегацию расходов по категориям за период.

        Выполняет SQL GROUP BY агрегацию с JOIN на Category.
        Исключает шаблоны recurring (is_recurring=True).
        Транзакции без категории объединяются в "Без категории".
        При group_small=True мелкие категории (<3%) объединяются в "Прочее".

        Args:
            user_id: ID пользователя.
            start_date: Начало периода (включительно).
            end_date: Конец периода (включительно).
            group_small: Группировать мелкие категории в "Прочее".

        Returns:
            Список CategorySummary, отсортированный по total DESC.
            Пустой список если нет транзакций за период.
        """
        # SQL агрегация с LEFT JOIN на Category
        query = (
            self.session.query(
                Transaction.category_id,
                Category.name.label("category_name"),
                Category.icon.label("category_icon"),
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .outerjoin(Category, Transaction.category_id == Category.id)
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.is_recurring == False,  # noqa: E712
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                )
            )
            .group_by(
                Transaction.category_id,
                Category.name,
                Category.icon,
            )
        )

        results = query.all()

        if not results:
            return []

        # Рассчитываем grand_total для процентов
        grand_total = sum(row.total for row in results)

        if grand_total == 0:
            return []

        # Формируем CategorySummary для каждой категории
        summaries: list[CategorySummary] = []
        for row in results:
            percentage = float(row.total / grand_total * 100)
            summaries.append(
                CategorySummary(
                    category_id=row.category_id,
                    category_name=row.category_name or "Без категории",
                    category_icon=row.category_icon,
                    total=row.total,
                    percentage=percentage,
                    count=row.count,
                )
            )

        # Группировка мелких категорий в "Прочее"
        if group_small:
            summaries = self._group_small_categories(summaries)

        # Сортировка по total DESC
        summaries.sort(key=lambda x: x["total"], reverse=True)

        return summaries

    def _group_small_categories(
        self, summaries: list[CategorySummary]
    ) -> list[CategorySummary]:
        """Группирует категории с percentage < MIN_PERCENTAGE_THRESHOLD в "Прочее".

        Args:
            summaries: Список CategorySummary для группировки.

        Returns:
            Список с объединенными мелкими категориями.
        """
        large_categories: list[CategorySummary] = []
        small_total = Decimal("0")
        small_count = 0
        small_percentage = 0.0

        for summary in summaries:
            if summary["percentage"] >= MIN_PERCENTAGE_THRESHOLD:
                large_categories.append(summary)
            else:
                small_total += summary["total"]
                small_count += summary["count"]
                small_percentage += summary["percentage"]

        # Добавляем "Прочее" только если есть мелкие категории
        if small_count > 0:
            large_categories.append(
                CategorySummary(
                    category_id=None,
                    category_name="Прочее",
                    category_icon="bi-three-dots",
                    total=small_total,
                    percentage=small_percentage,
                    count=small_count,
                )
            )

        return large_categories

    def get_monthly_trends(
        self,
        user_id: int,
        months: int = 6,
        reference_date: date | None = None,
    ) -> list[MonthlyTrend]:
        """Получить тренды расходов по месяцам.

        Генерирует данные за последние N месяцев для bar chart.
        Каждый месяц содержит агрегацию по категориям.

        Args:
            user_id: ID пользователя.
            months: Количество месяцев (по умолчанию 6).
            reference_date: Дата отсчета (по умолчанию сегодня).

        Returns:
            Список MonthlyTrend от старых к новым месяцам.
        """
        if reference_date is None:
            reference_date = date.today()

        trends: list[MonthlyTrend] = []

        # Генерируем список месяцев от reference_date назад
        for i in range(months - 1, -1, -1):
            # Вычисляем месяц (i месяцев назад от reference_date)
            year = reference_date.year
            month = reference_date.month - i

            # Корректируем год/месяц при переходе через год
            while month <= 0:
                month += 12
                year -= 1

            # Определяем границы месяца
            start_of_month = date(year, month, 1)

            # Конец месяца: последний день месяца
            last_day = calendar.monthrange(year, month)[1]
            end_of_month = date(year, month, last_day)

            # Получаем агрегацию за месяц
            categories = self.get_expenses_by_category(
                user_id=user_id,
                start_date=start_of_month,
                end_date=end_of_month,
                group_small=True,
            )

            # Рассчитываем total за месяц
            total = (
                sum(cat["total"] for cat in categories) if categories else Decimal("0")
            )

            trends.append(
                MonthlyTrend(
                    month=f"{year:04d}-{month:02d}",
                    month_label=MONTH_LABELS_RU[month],
                    categories=categories,
                    total=total,
                )
            )

        return trends

    def get_uncategorized_count(self, user_id: int) -> int:
        """Получить количество транзакций без категории.

        Считает INCOME и EXPENSE транзакции с category_id=NULL.
        Исключает шаблоны recurring (is_recurring=True).

        Args:
            user_id: ID пользователя.

        Returns:
            Количество некатегоризированных транзакций.
        """
        count = (
            self.session.query(func.count(Transaction.id))
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.category_id.is_(None),
                    Transaction.is_recurring == False,  # noqa: E712
                    Transaction.transaction_type.in_(
                        [
                            TransactionType.INCOME,
                            TransactionType.EXPENSE,
                        ]
                    ),
                )
            )
            .scalar()
        )

        return count or 0
