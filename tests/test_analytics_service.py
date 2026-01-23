"""Тесты для AnalyticsService."""

from datetime import date
from decimal import Decimal

import pytest

from app.models.database import Category, Transaction, TransactionType, User
from app.services.analytics_service import (
    AnalyticsService,
    MIN_PERCENTAGE_THRESHOLD,
)


@pytest.fixture
def user_with_categories(db_session) -> tuple[User, dict]:
    """Создает пользователя и категории для тестов."""
    user = User(
        email="analytics@test.com",
        name="Analytics User",
        starting_balance=Decimal("10000.00"),
    )
    db_session.add(user)
    db_session.flush()

    # Создаем категории
    cat_food = Category(name="Еда", icon="bi-cart", type="expense", sort_order=1)
    cat_transport = Category(
        name="Транспорт", icon="bi-car-front", type="expense", sort_order=2
    )
    cat_housing = Category(name="Жилье", icon="bi-house", type="expense", sort_order=3)
    cat_salary = Category(
        name="Зарплата", icon="bi-briefcase", type="income", sort_order=101
    )
    db_session.add_all([cat_food, cat_transport, cat_housing, cat_salary])
    db_session.flush()

    categories = {
        "food": cat_food,
        "transport": cat_transport,
        "housing": cat_housing,
        "salary": cat_salary,
    }

    return user, categories


class TestGetExpensesByCategory:
    """Тесты метода get_expenses_by_category."""

    def test_basic_aggregation(self, db_session, user_with_categories):
        """Базовая агрегация с 2-3 категориями."""
        user, cats = user_with_categories

        # Создаем транзакции
        t1 = Transaction(
            user_id=user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=cats["food"].id,
        )
        t2 = Transaction(
            user_id=user.id,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 16),
            category_id=cats["food"].id,
        )
        t3 = Transaction(
            user_id=user.id,
            amount=Decimal("2000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 17),
            category_id=cats["transport"].id,
        )
        db_session.add_all([t1, t2, t3])
        db_session.flush()

        service = AnalyticsService(db_session)
        result = service.get_expenses_by_category(
            user_id=user.id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            group_small=False,
        )

        assert len(result) == 2
        # Проверяем суммы
        totals = {r["category_name"]: r["total"] for r in result}
        assert totals["Еда"] == Decimal("1500.00")
        assert totals["Транспорт"] == Decimal("2000.00")

    def test_includes_uncategorized(self, db_session, user_with_categories):
        """Транзакции без категории включены как 'Без категории'."""
        user, cats = user_with_categories

        # Транзакция с категорией
        t1 = Transaction(
            user_id=user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=cats["food"].id,
        )
        # Транзакция без категории
        t2 = Transaction(
            user_id=user.id,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 16),
            category_id=None,
        )
        db_session.add_all([t1, t2])
        db_session.flush()

        service = AnalyticsService(db_session)
        result = service.get_expenses_by_category(
            user_id=user.id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            group_small=False,
        )

        names = [r["category_name"] for r in result]
        assert "Без категории" in names

        uncategorized = next(r for r in result if r["category_name"] == "Без категории")
        assert uncategorized["total"] == Decimal("500.00")
        assert uncategorized["category_id"] is None

    def test_groups_small_categories(self, db_session, user_with_categories):
        """Категории < 3% объединяются в 'Прочее'."""
        user, cats = user_with_categories

        # Большая категория - 97%
        t1 = Transaction(
            user_id=user.id,
            amount=Decimal("9700.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=cats["food"].id,
        )
        # Маленькая категория - 2%
        t2 = Transaction(
            user_id=user.id,
            amount=Decimal("200.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 16),
            category_id=cats["transport"].id,
        )
        # Маленькая категория - 1%
        t3 = Transaction(
            user_id=user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 17),
            category_id=cats["housing"].id,
        )
        db_session.add_all([t1, t2, t3])
        db_session.flush()

        service = AnalyticsService(db_session)
        result = service.get_expenses_by_category(
            user_id=user.id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            group_small=True,
        )

        names = [r["category_name"] for r in result]
        assert "Еда" in names
        assert "Прочее" in names
        assert "Транспорт" not in names
        assert "Жилье" not in names

        other = next(r for r in result if r["category_name"] == "Прочее")
        assert other["total"] == Decimal("300.00")

    def test_no_grouping(self, db_session, user_with_categories):
        """С group_small=False все категории сохраняются."""
        user, cats = user_with_categories

        # Большая категория
        t1 = Transaction(
            user_id=user.id,
            amount=Decimal("9700.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=cats["food"].id,
        )
        # Маленькая категория
        t2 = Transaction(
            user_id=user.id,
            amount=Decimal("200.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 16),
            category_id=cats["transport"].id,
        )
        db_session.add_all([t1, t2])
        db_session.flush()

        service = AnalyticsService(db_session)
        result = service.get_expenses_by_category(
            user_id=user.id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            group_small=False,
        )

        names = [r["category_name"] for r in result]
        assert "Еда" in names
        assert "Транспорт" in names
        assert "Прочее" not in names

    def test_empty_period(self, db_session, user_with_categories):
        """Пустой период возвращает пустой список."""
        user, _ = user_with_categories

        service = AnalyticsService(db_session)
        result = service.get_expenses_by_category(
            user_id=user.id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        assert result == []

    def test_excludes_income(self, db_session, user_with_categories):
        """INCOME транзакции исключены из агрегации."""
        user, cats = user_with_categories

        # Расход
        t1 = Transaction(
            user_id=user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=cats["food"].id,
        )
        # Доход
        t2 = Transaction(
            user_id=user.id,
            amount=Decimal("50000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 16),
            category_id=cats["salary"].id,
        )
        db_session.add_all([t1, t2])
        db_session.flush()

        service = AnalyticsService(db_session)
        result = service.get_expenses_by_category(
            user_id=user.id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            group_small=False,
        )

        assert len(result) == 1
        assert result[0]["category_name"] == "Еда"
        assert result[0]["total"] == Decimal("1000.00")

    def test_excludes_recurring_templates(self, db_session, user_with_categories):
        """Шаблоны recurring (is_recurring=True) исключены."""
        user, cats = user_with_categories

        # Обычная транзакция
        t1 = Transaction(
            user_id=user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=cats["food"].id,
            is_recurring=False,
        )
        # Шаблон recurring
        t2 = Transaction(
            user_id=user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 16),
            category_id=cats["transport"].id,
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add_all([t1, t2])
        db_session.flush()

        service = AnalyticsService(db_session)
        result = service.get_expenses_by_category(
            user_id=user.id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            group_small=False,
        )

        assert len(result) == 1
        assert result[0]["category_name"] == "Еда"
        assert result[0]["total"] == Decimal("1000.00")

    def test_percentage_calculation(self, db_session, user_with_categories):
        """Проверка расчета процентов (сумма = 100%)."""
        user, cats = user_with_categories

        t1 = Transaction(
            user_id=user.id,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=cats["food"].id,
        )
        t2 = Transaction(
            user_id=user.id,
            amount=Decimal("300.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 16),
            category_id=cats["transport"].id,
        )
        t3 = Transaction(
            user_id=user.id,
            amount=Decimal("200.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 17),
            category_id=cats["housing"].id,
        )
        db_session.add_all([t1, t2, t3])
        db_session.flush()

        service = AnalyticsService(db_session)
        result = service.get_expenses_by_category(
            user_id=user.id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            group_small=False,
        )

        total_percentage = sum(r["percentage"] for r in result)
        assert abs(total_percentage - 100.0) < 0.01

        # Проверяем конкретные проценты
        percentages = {r["category_name"]: r["percentage"] for r in result}
        assert abs(percentages["Еда"] - 50.0) < 0.01
        assert abs(percentages["Транспорт"] - 30.0) < 0.01
        assert abs(percentages["Жилье"] - 20.0) < 0.01

    def test_sorting_by_total_desc(self, db_session, user_with_categories):
        """Результат отсортирован по убыванию суммы."""
        user, cats = user_with_categories

        t1 = Transaction(
            user_id=user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=cats["food"].id,
        )
        t2 = Transaction(
            user_id=user.id,
            amount=Decimal("300.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 16),
            category_id=cats["transport"].id,
        )
        t3 = Transaction(
            user_id=user.id,
            amount=Decimal("200.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 17),
            category_id=cats["housing"].id,
        )
        db_session.add_all([t1, t2, t3])
        db_session.flush()

        service = AnalyticsService(db_session)
        result = service.get_expenses_by_category(
            user_id=user.id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            group_small=False,
        )

        totals = [r["total"] for r in result]
        assert totals == sorted(totals, reverse=True)
        assert result[0]["category_name"] == "Транспорт"
        assert result[1]["category_name"] == "Жилье"
        assert result[2]["category_name"] == "Еда"


class TestGetMonthlyTrends:
    """Тесты метода get_monthly_trends."""

    def test_6_months_with_labels(self, db_session, user_with_categories):
        """Проверка 6 месяцев с корректными month_label."""
        user, cats = user_with_categories

        # Транзакция в январе 2026
        t1 = Transaction(
            user_id=user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=cats["food"].id,
        )
        db_session.add(t1)
        db_session.flush()

        service = AnalyticsService(db_session)
        result = service.get_monthly_trends(
            user_id=user.id,
            months=6,
            reference_date=date(2026, 1, 31),
        )

        assert len(result) == 6

        # Проверяем последний месяц (январь)
        assert result[-1]["month"] == "2026-01"
        assert result[-1]["month_label"] == "Янв"
        assert result[-1]["total"] == Decimal("1000.00")

        # Проверяем формат месяцев
        for trend in result:
            assert len(trend["month"]) == 7  # "YYYY-MM"
            assert trend["month_label"] in [
                "Янв",
                "Фев",
                "Мар",
                "Апр",
                "Май",
                "Июн",
                "Июл",
                "Авг",
                "Сен",
                "Окт",
                "Ноя",
                "Дек",
            ]

    def test_12_months(self, db_session, user_with_categories):
        """Проверка 12 месяцев."""
        user, _ = user_with_categories

        service = AnalyticsService(db_session)
        result = service.get_monthly_trends(
            user_id=user.id,
            months=12,
            reference_date=date(2026, 1, 31),
        )

        assert len(result) == 12

        # Первый месяц должен быть февраль 2025
        assert result[0]["month"] == "2025-02"
        assert result[0]["month_label"] == "Фев"

        # Последний месяц должен быть январь 2026
        assert result[-1]["month"] == "2026-01"
        assert result[-1]["month_label"] == "Янв"

    def test_empty_month(self, db_session, user_with_categories):
        """Месяц без транзакций имеет total=0 и categories=[]."""
        user, _ = user_with_categories

        service = AnalyticsService(db_session)
        result = service.get_monthly_trends(
            user_id=user.id,
            months=3,
            reference_date=date(2026, 1, 31),
        )

        for trend in result:
            assert trend["total"] == Decimal("0")
            assert trend["categories"] == []


class TestGetUncategorizedCount:
    """Тесты метода get_uncategorized_count."""

    def test_count_uncategorized(self, db_session, user_with_categories):
        """Корректный подсчет некатегоризированных транзакций."""
        user, cats = user_with_categories

        # С категорией
        t1 = Transaction(
            user_id=user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=cats["food"].id,
        )
        # Без категории (expense)
        t2 = Transaction(
            user_id=user.id,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 16),
            category_id=None,
        )
        # Без категории (income)
        t3 = Transaction(
            user_id=user.id,
            amount=Decimal("50000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 17),
            category_id=None,
        )
        # Transfer без категории - не должен считаться
        t4 = Transaction(
            user_id=user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.TRANSFER,
            transaction_date=date(2026, 1, 18),
            category_id=None,
        )
        db_session.add_all([t1, t2, t3, t4])
        db_session.flush()

        service = AnalyticsService(db_session)
        count = service.get_uncategorized_count(user_id=user.id)

        assert count == 2  # expense + income без категории

    def test_excludes_recurring_templates(self, db_session, user_with_categories):
        """Шаблоны recurring (is_recurring=True) исключены."""
        user, _ = user_with_categories

        # Обычная транзакция без категории
        t1 = Transaction(
            user_id=user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=None,
            is_recurring=False,
        )
        # Шаблон recurring без категории
        t2 = Transaction(
            user_id=user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 16),
            category_id=None,
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add_all([t1, t2])
        db_session.flush()

        service = AnalyticsService(db_session)
        count = service.get_uncategorized_count(user_id=user.id)

        assert count == 1  # только обычная транзакция

    def test_zero_when_all_categorized(self, db_session, user_with_categories):
        """Возвращает 0 когда все транзакции категоризированы."""
        user, cats = user_with_categories

        t1 = Transaction(
            user_id=user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            category_id=cats["food"].id,
        )
        db_session.add(t1)
        db_session.flush()

        service = AnalyticsService(db_session)
        count = service.get_uncategorized_count(user_id=user.id)

        assert count == 0


class TestMinPercentageThreshold:
    """Тесты константы MIN_PERCENTAGE_THRESHOLD."""

    def test_threshold_value(self):
        """Значение порога = 3.0."""
        assert MIN_PERCENTAGE_THRESHOLD == 3.0
