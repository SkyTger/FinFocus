"""Тесты признака разового расхода и группировки засечек (протокол 0034).

Разовый расход — expense, не принадлежащий серии. Модель слоёв его
только помечает: формулы слоёв, лимита и узкого места не меняются.
Даты относительные; регресс сверяется с ручным расчётом «ноябрьского»
сценария из tests/test_money_layers_limit.py, а не со снимком вывода.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.database import TransactionType, User
from app.services.money_layers_service import (
    MoneyLayersService,
    one_off_marks,
    one_off_total_until,
)
from app.services.recurring_service import RecurringService
from tests.test_money_layers_limit import add_monthly, add_txn, build_november


@pytest.fixture
def service(db_session) -> MoneyLayersService:
    """Сервис модели слоёв на тестовой сессии."""
    return MoneyLayersService(db_session)


@pytest.fixture
def user(db_session) -> User:
    """Пользователь без подушки и бюджета целей."""
    user = User(
        email="oneoff@example.com",
        name="One-off User",
        starting_balance=Decimal("100000"),
        monthly_savings_budget=Decimal("0"),
    )
    db_session.add(user)
    db_session.commit()
    return user


def payments_by_description(data) -> dict[str, list[dict]]:
    """Платежи модели, сгруппированные по описанию."""
    result: dict[str, list[dict]] = {}
    for payment in data["upcoming_payments"]:
        result.setdefault(payment["description"], []).append(payment)
    return result


class TestIsOneOffFlag:
    """Признак is_one_off у предстоящих платежей."""

    def test_plain_expense_is_one_off(self, db_session, service, user):
        """Обычный расход без серии — разовый."""
        ref = date.today()
        add_txn(
            db_session,
            user.id,
            "5000",
            TransactionType.EXPENSE,
            ref + timedelta(days=3),
            "Ремонт",
        )

        data = service.get_money_layers(user.id, ref)
        [payment] = payments_by_description(data)["Ремонт"]

        assert payment["is_one_off"] is True
        assert payment["is_recurring"] is False

    def test_series_instances_are_not_one_off(self, db_session, service, user):
        """Виртуальные экземпляры шаблона серии — не разовые."""
        ref = date.today()
        add_monthly(
            db_session,
            user.id,
            "3000",
            TransactionType.EXPENSE,
            ref + timedelta(days=2),
            "Подписки",
        )

        data = service.get_money_layers(user.id, ref)
        instances = payments_by_description(data)["Подписки"]

        assert instances  # хотя бы одно вхождение в горизонте
        assert all(item["is_one_off"] is False for item in instances)

    def test_moved_series_exception_is_not_one_off(self, db_session, service, user):
        """Исключение серии (перенесённый экземпляр) — не разовое."""
        ref = date.today()
        first = ref + timedelta(days=5)
        template = add_monthly(
            db_session, user.id, "29800", TransactionType.EXPENSE, first, "Автокредит"
        )
        RecurringService(db_session).create_exception(
            template.id,
            original_date=first,
            new_date=ref + timedelta(days=2),
            new_description="Автокредит перенесён",
        )

        data = service.get_money_layers(user.id, ref)
        [moved] = payments_by_description(data)["Автокредит перенесён"]

        assert moved["date"] == ref + timedelta(days=2)
        assert moved["is_one_off"] is False

    @pytest.mark.parametrize(
        "txn_type",
        [TransactionType.SAVINGS_RESERVE, TransactionType.SAVINGS_CONTRIBUTION],
    )
    def test_savings_operations_are_not_one_off(
        self, db_session, service, user, txn_type
    ):
        """Служебные savings-операции вне серии — не разовые."""
        ref = date.today()
        add_txn(
            db_session, user.id, "7000", txn_type, ref + timedelta(days=4), "Служебная"
        )

        data = service.get_money_layers(user.id, ref)
        [payment] = payments_by_description(data)["Служебная"]

        assert payment["is_one_off"] is False

    def test_negative_adjustment_is_payment_but_not_one_off(
        self, db_session, service, user
    ):
        """Отрицательная корректировка сверки — платёж, но не разовый."""
        ref = date.today()
        add_txn(
            db_session,
            user.id,
            "-500",
            TransactionType.ADJUSTMENT,
            ref + timedelta(days=1),
            "Сверка",
        )

        data = service.get_money_layers(user.id, ref)
        [payment] = payments_by_description(data)["Сверка"]

        assert payment["amount"] == Decimal("500")
        assert payment["is_one_off"] is False


class TestOneOffMarks:
    """Группировка разовых расходов по дням окна оси."""

    def test_same_day_expenses_form_one_mark(self, db_session, service, user):
        """Два разовых в один день → одна отметка, items по убыванию суммы."""
        ref = date.today()
        day = ref + timedelta(days=6)
        expense = TransactionType.EXPENSE
        add_txn(db_session, user.id, "1200", expense, day, "Цветы")
        add_txn(db_session, user.id, "8000", expense, day, "Подарок")
        add_txn(db_session, user.id, "900", expense, ref + timedelta(days=2), "Такси")

        marks = one_off_marks(service.get_money_layers(user.id, ref))

        assert [mark["date"] for mark in marks] == [ref + timedelta(days=2), day]
        assert marks[1]["total"] == Decimal("9200")
        assert [item["description"] for item in marks[1]["items"]] == [
            "Подарок",
            "Цветы",
        ]

    def test_series_and_service_ops_do_not_form_marks(self, db_session, service, user):
        """Только серии и служебные — засечек нет вовсе."""
        ref = date.today()
        add_monthly(
            db_session,
            user.id,
            "3000",
            TransactionType.EXPENSE,
            ref + timedelta(days=2),
            "Подписки",
        )
        add_txn(
            db_session,
            user.id,
            "7000",
            TransactionType.SAVINGS_RESERVE,
            ref + timedelta(days=4),
            "Резерв",
        )

        assert one_off_marks(service.get_money_layers(user.id, ref)) == []

    def test_expense_beyond_window_counts_in_total_not_in_marks(
        self, db_session, service, user
    ):
        """Разовый за window_end: не засечка, но в сумме до даты за осью."""
        ref = date.today()
        # Доход за осью — чтобы горизонт H ушёл дальше window_end
        add_txn(
            db_session,
            user.id,
            "50000",
            TransactionType.INCOME,
            ref + timedelta(days=60),
            "Зарплата",
        )
        add_txn(
            db_session,
            user.id,
            "4000",
            TransactionType.EXPENSE,
            ref + timedelta(days=50),
            "Страховка",
        )

        data = service.get_money_layers(user.id, ref)

        assert data["window_end"] < ref + timedelta(days=50) <= data["horizon_end"]
        assert one_off_marks(data) == []
        assert one_off_total_until(data, ref + timedelta(days=55)) == Decimal("4000")


class TestOneOffTotalUntil:
    """Сумма разовых расходов до даты включительно."""

    def test_both_bounds_inclusive(self, db_session, service, user):
        """Расход сегодня и в день end входят, после end — нет."""
        ref = date.today()
        expense = TransactionType.EXPENSE
        add_txn(db_session, user.id, "100", expense, ref, "Сегодня")
        add_txn(db_session, user.id, "200", expense, ref + timedelta(days=5), "Конец")
        add_txn(db_session, user.id, "400", expense, ref + timedelta(days=6), "После")

        data = service.get_money_layers(user.id, ref)

        assert one_off_total_until(data, ref + timedelta(days=5)) == Decimal("300")

    def test_empty_is_zero(self, db_session, service, user):
        """Нет разовых — Decimal 0."""
        ref = date.today()

        data = service.get_money_layers(user.id, ref)

        assert one_off_total_until(data, ref + timedelta(days=10)) == Decimal("0")


class TestLayersUnchanged:
    """Регресс: разовые только помечены, формулы модели не тронуты."""

    def test_november_scenario_numbers_and_marks(self, db_session, service, user):
        """Ручной расчёт test_money_layers_limit + две засечки разовых.

        Ремонт 65 000 на 13-е и Радиатор 20 000 на 23-е — разовые; узкое
        место 19-е с available 14 000, нехватки нет, лимит первого
        периода 14 000 / 17. До узкого места разовый — только ремонт.
        """
        user.starting_balance = Decimal("10000")
        db_session.commit()
        ref = date.today().replace(day=3)
        build_november(db_session, user.id, ref, ref.replace(day=23))

        data = service.get_money_layers(user.id, ref)

        assert data["bottleneck_date"] == ref.replace(day=19)
        assert data["bottleneck_available"] == Decimal("14000")
        assert data["shortfall"] == Decimal("0")
        assert data["limit_periods"][0]["per_day"] == Decimal("14000") / Decimal(17)
        for day in data["days"]:
            assert (
                day["free"] + day["payments"] + day["reserve"]
                == day["forecast_balance"]
            )

        marks = one_off_marks(data)
        assert [(mark["date"], mark["total"]) for mark in marks] == [
            (ref.replace(day=13), Decimal("65000")),
            (ref.replace(day=23), Decimal("20000")),
        ]
        one_off_names = {
            item["description"]
            for item in data["upcoming_payments"]
            if item["is_one_off"]
        }
        assert one_off_names == {"Ремонт", "Радиатор"}
        assert one_off_total_until(data, data["bottleneck_date"]) == Decimal("65000")
