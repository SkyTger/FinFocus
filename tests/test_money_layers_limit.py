"""Тесты лимита трат на день по периодам и нормы «по плану» (протокол 0033).

Ожидаемые числа — из ручного расчёта по фикстуре (log.md протокола,
шаг 2), а не из вывода кода. Даты относительные: опорный день — 3-е
число текущего месяца, «следующий месяц» — через next_month_day; числа
подобраны так, что ожидания верны при любой длине месяца (28–31 день),
а где число от длины зависит — оно выражено через неё.
"""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.database import Transaction, TransactionType, User
from app.schema.money_layers import Horizons
from app.services.money_layers_service import MoneyLayersService
from app.services.recurring_service import RecurringService


def month_len(day: date) -> int:
    """Число дней в месяце даты."""
    return monthrange(day.year, day.month)[1]


def next_month_day(day: date, day_of_month: int) -> date:
    """День следующего месяца (обрезается по длине месяца)."""
    nxt = day.replace(day=month_len(day)) + timedelta(days=1)
    return nxt.replace(day=min(day_of_month, month_len(nxt)))


@pytest.fixture
def service(db_session) -> MoneyLayersService:
    """Сервис модели слоёв на тестовой сессии."""
    return MoneyLayersService(db_session)


@pytest.fixture
def user(db_session) -> User:
    """Пользователь без подушки и бюджета целей: резерв == 0."""
    user = User(
        email="limit@example.com",
        name="Limit User",
        starting_balance=Decimal("10000"),
        monthly_savings_budget=Decimal("0"),
    )
    db_session.add(user)
    db_session.commit()
    return user


def add_txn(session, user_id, amount, txn_type, when, description="Операция"):
    """Разовая операция."""
    txn = Transaction(
        user_id=user_id,
        amount=Decimal(amount),
        transaction_type=txn_type,
        transaction_date=when,
        description=description,
    )
    session.add(txn)
    session.commit()
    return txn


def add_monthly(session, user_id, amount, txn_type, first_date, description):
    """Регулярная ежемесячная операция (шаблон) с первым вхождением first_date."""
    template = Transaction(
        user_id=user_id,
        amount=Decimal(amount),
        transaction_type=txn_type,
        transaction_date=first_date,
        description=description,
        is_recurring=True,
        recurring_period="monthly",
    )
    session.add(template)
    session.commit()
    return template


def build_november(session, user_id, ref, radiator_day):
    """Синтетический «ноябрьский» сценарий (структура как у владельца).

    Опорный день ref — 3-е число месяца M; баланс 10 000. Регулярные:
    доход 120 000 по 5-м и 100 000 по 20-м (с M), перевод 40 000 по
    5-м, подписки 3 000 по 10-м, коммуналка 8 000 по 15-м (с M),
    кредиты 29 800 и 4 870 по 1-м (с M+1). Разовые: ремонт 65 000
    на 13-е (до второго дохода) и «радиатор» 20 000 на radiator_day.
    """
    m5, m10, m15, m20 = (ref.replace(day=d) for d in (5, 10, 15, 20))
    income, expense = TransactionType.INCOME, TransactionType.EXPENSE
    add_monthly(session, user_id, "120000", income, m5, "Зарплата")
    add_monthly(session, user_id, "100000", income, m20, "Аванс")
    add_monthly(session, user_id, "40000", expense, m5, "Перевод")
    add_monthly(session, user_id, "3000", expense, m10, "Подписки")
    add_monthly(session, user_id, "8000", expense, m15, "Коммуналка")
    add_monthly(
        session, user_id, "29800", expense, next_month_day(ref, 1), "Автокредит"
    )
    add_monthly(session, user_id, "4870", expense, next_month_day(ref, 1), "Кредит")
    add_txn(session, user_id, "65000", expense, ref.replace(day=13), "Ремонт")
    add_txn(session, user_id, "20000", expense, radiator_day, "Радиатор")


class TestNovemberScenario:
    """Два узких места: накануне аванса и накануне следующей зарплаты.

    Ручной расчёт (log.md, шаг 2), available = balance (резерв 0):
    M/3..4 10 000; M/5 90 000; M/10 87 000; M/13 22 000; M/15 14 000;
    M/20 114 000; M/23 94 000; M+1/1 59 330; M+1/5 139 330; ...
    Период 1: min available(t)/дней — 14 000 / 17 на M/19 (3.→19.
    включительно = 17 дней). Период 2 от M/20, spent = 14 000:
    (59 330 − 14 000) / дней(M/20..M+1/4) = 45 330 / (len(M) − 15).
    Период 3 от M+1/5, spent = 59 330: min — (128 330 − 59 330) / 15
    = 4 600 на M+1/19 (H = M+1/20, доход).
    """

    def test_two_periods_first_ends_before_second_income(
        self, db_session, service, user
    ):
        """Первый период кончается накануне аванса, лимит потом растёт."""
        ref = date.today().replace(day=3)
        build_november(db_session, user.id, ref, ref.replace(day=23))

        data = service.get_money_layers(user.id, ref)
        periods = data["limit_periods"]
        days_m = month_len(ref)

        assert len(periods) == 3
        first, second, third = periods
        assert first["start"] == ref
        assert first["end"] == ref.replace(day=19)
        assert first["per_day"] == Decimal("14000") / Decimal("17")
        assert second["start"] == ref.replace(day=20)
        assert second["end"] == next_month_day(ref, 4)
        assert second["per_day"] == Decimal("45330") / Decimal(days_m - 15)
        assert third["start"] == next_month_day(ref, 5)
        assert third["end"] == next_month_day(ref, 19)
        assert third["per_day"] == Decimal("4600")
        assert first["per_day"] <= second["per_day"] <= third["per_day"]
        assert all(period["reliable"] for period in periods)
        assert data["horizon_end"] == next_month_day(ref, 20)

    def test_bottleneck_is_end_of_first_period(self, db_session, service, user):
        """Узкое место — 19-е и available этого дня, не «сегодня»."""
        ref = date.today().replace(day=3)
        build_november(db_session, user.id, ref, ref.replace(day=23))

        data = service.get_money_layers(user.id, ref)

        assert data["bottleneck_date"] == ref.replace(day=19)
        assert data["bottleneck_available"] == Decimal("14000")
        assert data["shortfall"] == Decimal("0")

    def test_radiator_before_second_income_gives_shortfall(
        self, db_session, service, user
    ):
        """Радиатор перенесён на 10-е → нехватка 6 000 с 15-го, лимит 0.

        Расчёт: M/10 87 000 − 20 000 = 67 000; M/13 2 000; M/15 −6 000.
        Самое отрицательное отношение −6 000 / 13 — на M/15 → период
        один, per_day 0; shortfall 6 000, первый день минимума M/15.
        """
        ref = date.today().replace(day=3)
        build_november(db_session, user.id, ref, ref.replace(day=10))

        data = service.get_money_layers(user.id, ref)

        assert data["shortfall"] == Decimal("6000")
        assert data["shortfall_date"] == ref.replace(day=15)
        assert data["limit_periods"] == [
            {
                "start": ref,
                "end": ref.replace(day=15),
                "per_day": Decimal("0"),
                "reliable": True,
            }
        ]
        assert data["bottleneck_date"] == ref.replace(day=15)
        assert data["bottleneck_available"] == Decimal("-6000")

    def test_norm_by_plan_for_november(self, db_session, service, user):
        """Норма: регулярные вхождения месяца M (доходы − расходы) ÷ дней.

        В M: 120 000 + 100 000 − 40 000 − 3 000 − 8 000 = 169 000
        (кредиты начинаются с M+1, разовые не входят).
        """
        ref = date.today().replace(day=3)
        build_november(db_session, user.id, ref, ref.replace(day=23))

        data = service.get_money_layers(user.id, ref)

        assert data["norm_per_day"] == Decimal("169000") / Decimal(month_len(ref))


class TestLimitAlgorithm:
    """Алгоритм периодов на синтетическом ряду available."""

    @staticmethod
    def horizons(ref: date, horizon_end: date, has_income: bool) -> Horizons:
        """Horizons для прямого вызова _limit_periods."""
        return Horizons(
            collect_start=ref.replace(day=1),
            window_end=ref + timedelta(days=44),
            horizon_end=horizon_end,
            horizon_has_income_after=has_income,
        )

    def test_counterexample_low_point_over_days_is_wrong(self, service):
        """Контрпример ROADMAP п.10: 10 000 на 16-й день и 15 000 на 37-й.

        «Низшая точка ÷ дни до неё» дала бы 10 000 / 16 = 625 ₽/день —
        и на 37-й день денег не хватит. Верно: 15 000 / 37 ≈ 405,4 → 405.
        """
        ref = date.today()
        dates = [ref + timedelta(days=offset) for offset in range(37)]
        available = {day: Decimal("1000000") for day in dates}
        available[dates[15]] = Decimal("10000")  # 16-й день включительно
        available[dates[36]] = Decimal("15000")  # 37-й день включительно

        periods = service._limit_periods(
            available, dates, self.horizons(ref, dates[-1], True)
        )

        assert periods[0]["end"] == dates[36]
        assert periods[0]["per_day"] == Decimal("15000") / Decimal("37")
        assert int(periods[0]["per_day"]) == 405

    def test_equal_limits_merge_into_one_period(self, service):
        """1 000,4 и 1 000,7 ₽/день → один период «до конца второго».

        Ряд: 10 004 на 10-й день, 20 011 на 20-й, остальное высоко.
        Период 1: 10 004 / 10 = 1 000,4 (20 011 / 20 = 1 000,55 выше).
        Период 2: (20 011 − 10 004) / 10 = 1 000,7. До рубля оба 1 000.
        """
        ref = date.today()
        dates = [ref + timedelta(days=offset) for offset in range(20)]
        available = {day: Decimal("1000000") for day in dates}
        available[dates[9]] = Decimal("10004")
        available[dates[19]] = Decimal("20011")

        periods = service._limit_periods(
            available, dates, self.horizons(ref, dates[-1], True)
        )

        assert periods == [
            {
                "start": ref,
                "end": dates[19],
                "per_day": Decimal("1000.4"),
                "reliable": True,
            }
        ]

    def test_tie_takes_last_day(self, service):
        """При равных отношениях узкое место — ПОЗДНИЙ день.

        5 000 на 5-й день и 10 000 на 10-й: оба 1 000 ₽/день. Обычно
        выбор раннего дня маскирует слияние (остаток периода даёт тот же
        лимит), поэтому поздний день сделан краем расчёта без дохода:
        «последний» даёт ОДИН ненадёжный период до 10-го, «первый» —
        два (надёжный до 5-го и ненадёжный до 10-го, они не сливаются).
        """
        ref = date.today()
        dates = [ref + timedelta(days=offset) for offset in range(10)]
        available = {day: Decimal("1000000") for day in dates}
        available[dates[4]] = Decimal("5000")
        available[dates[9]] = Decimal("10000")

        periods = service._limit_periods(
            available, dates, self.horizons(ref, dates[-1], False)
        )

        assert periods == [
            {
                "start": ref,
                "end": dates[9],
                "per_day": Decimal("1000"),
                "reliable": False,
            }
        ]

    def test_unreliable_period_hits_horizon_without_income(self, service):
        """Период, упёршийся в H без дохода за ним, — reliable False."""
        ref = date.today()
        dates = [ref + timedelta(days=offset) for offset in range(90)]
        available = {day: Decimal("9000") for day in dates}

        periods = service._limit_periods(
            available, dates, self.horizons(ref, dates[-1], False)
        )

        assert periods == [
            {
                "start": ref,
                "end": dates[-1],
                "per_day": Decimal("100"),
                "reliable": False,
            }
        ]

    def test_no_income_in_horizon_end_to_end(self, db_session, service, user):
        """Без доходов: один ненадёжный период до ref + 89 (10 000 / 90)."""
        ref = date.today()

        data = service.get_money_layers(user.id, ref)

        assert data["limit_periods"] == [
            {
                "start": ref,
                "end": ref + timedelta(days=89),
                "per_day": Decimal("10000") / Decimal("90"),
                "reliable": False,
            }
        ]
        assert data["norm_per_day"] is None

    def test_at_most_three_periods(self, service):
        """Периодов не больше трёх, даже если узких мест больше."""
        ref = date.today()
        dates = [ref + timedelta(days=offset) for offset in range(40)]
        # Каждые 10 дней ровно +10 000 · k: отношения растут → 4 узких места
        available = {day: Decimal("1000000") for day in dates}
        for k, index in enumerate((9, 19, 29, 39), start=1):
            available[dates[index]] = Decimal(
                sum(1000 * 10 * j for j in range(1, k + 1))
            )

        periods = service._limit_periods(
            available, dates, self.horizons(ref, dates[-1], True)
        )

        assert [period["per_day"] for period in periods] == [
            Decimal("1000"),
            Decimal("2000"),
            Decimal("3000"),
        ]


class TestNormByPlan:
    """Норма «по плану» не подстраивается под факт (октябрьский сценарий)."""

    def test_norm_ignores_actual_smaller_income(self, db_session, service, user):
        """Зарплата по плану 100 000, фактически пришло 18 190 — норма по плану.

        Шаблоны: доход 100 000 по 5-м, расход 30 000 по 10-м (с M).
        Исключение на M/5: 18 190. Норма = (100 000 − 30 000) / len(M);
        прогноз остатка при этом видит факт: 10 000 + 18 190 на M/6.
        Осознанное поведение (риск в решении консилиума): подпись «по
        плану» — забота UI.
        """
        ref = date.today().replace(day=6)
        salary = add_monthly(
            db_session,
            user.id,
            "100000",
            TransactionType.INCOME,
            ref.replace(day=5),
            "Зарплата",
        )
        add_monthly(
            db_session,
            user.id,
            "30000",
            TransactionType.EXPENSE,
            ref.replace(day=10),
            "Платёж",
        )
        RecurringService(db_session).create_exception(
            salary.id, ref.replace(day=5), new_amount=Decimal("18190")
        )
        db_session.commit()

        data = service.get_money_layers(user.id, ref)

        assert data["today"]["balance"] == Decimal("28190")
        assert data["norm_per_day"] == Decimal("70000") / Decimal(month_len(ref))


def chart_figure(component):
    """Plotly figure единственного dcc.Graph в дереве компонента."""
    from dash import dcc

    stack, graphs = [component], []
    while stack:
        node = stack.pop()
        if isinstance(node, dcc.Graph):
            graphs.append(node)
        children = getattr(node, "children", None)
        if isinstance(children, (list, tuple)):
            stack.extend(children)
        elif children is not None and not isinstance(children, str):
            stack.append(children)
    assert len(graphs) == 1
    return graphs[0].figure


class TestBottleneckOnPanel:
    """Маркер графика и «Ближайшая просадка» на карточке — одна точка."""

    def test_card_and_chart_marker_show_same_bottleneck(
        self, db_session, service, user
    ):
        """«Ноябрь»: карточка и маркер — M/19 и 14 000, не сегодня."""
        from app.components.dashboard import build_layers_chart
        from app.services.panel_service import DashboardPanelService

        ref = date.today().replace(day=3)
        build_november(db_session, user.id, ref, ref.replace(day=23))

        panel = DashboardPanelService(db_session).get_panel_data(user.id, ref)
        card = panel["calendar"]
        figure = chart_figure(build_layers_chart(panel["layers"]))
        markers = [trace for trace in figure.data if trace.type == "scatter"]

        assert card["dip_date"] == ref.replace(day=19) != ref
        assert card["dip_free"] == Decimal("14000")
        assert card["dip_shortfall"] is None
        assert len(markers) == 1
        assert str(markers[0].x[0]).startswith(ref.replace(day=19).isoformat())

    def test_shortfall_on_card_and_chart(self, db_session, service, user):
        """Радиатор на 10-е: обе точки — M/15, «не хватает 6 000 ₽»."""
        from app.components.dashboard import build_layers_chart
        from app.services.panel_service import DashboardPanelService

        ref = date.today().replace(day=3)
        build_november(db_session, user.id, ref, ref.replace(day=10))

        panel = DashboardPanelService(db_session).get_panel_data(user.id, ref)
        card = panel["calendar"]
        figure = chart_figure(build_layers_chart(panel["layers"]))
        markers = [trace for trace in figure.data if trace.type == "scatter"]

        assert card["dip_date"] == ref.replace(day=15)
        assert card["dip_shortfall"] == Decimal("6000")
        assert card["dip_is_strong"] is True
        assert str(markers[0].x[0]).startswith(ref.replace(day=15).isoformat())

    def test_flat_window_without_income_has_no_marker(self, db_session, service, user):
        """История без операций и доходов: узкое место — край расчёта.

        Первый период ненадёжен (H = ref + 89 без дохода) — точку не
        показывают ни карточка, ни график: край расчёта — не узкое место.
        """
        from app.components.dashboard import build_layers_chart
        from app.services.panel_service import DashboardPanelService

        ref = date.today()
        panel = DashboardPanelService(db_session).get_panel_data(user.id, ref)
        figure = chart_figure(build_layers_chart(panel["layers"]))

        assert panel["layers"]["window_is_flat"] is True
        assert panel["calendar"]["dip_date"] is None
        assert [trace for trace in figure.data if trace.type == "scatter"] == []
