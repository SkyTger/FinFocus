"""Тесты модели «свободно / платежи / резерв» (EPIC-11, кусок 1).

Главное, что проверяют эти тесты, — РАСКЛАДКУ по слоям, а не сумму.
Инвариант AC-3 (free + payments + reserve == balance) зелёный при любой
неверной раскладке: именно поэтому два блокера формулы резерва дожили
до третьей итерации проектирования. Блок A («таблица ожидаемых слоёв»)
проверяет каждое из трёх чисел явно.

Даты во всех тестах относительные (KB testing.md): pytest.skip
не используется — самоотключение тестов уже стоило проекту пяти месяцев
тихого падения покрытия (открытый вопрос №6 ROADMAP).
"""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.database import (
    Goal,
    GoalStatus,
    Transaction,
    TransactionType,
    User,
)
from app.services.money_layers_service import MoneyLayersService
from app.schema.money_layers import WINDOW_DAYS


# --- Общая конфигурация трассировки решения ---

BUDGET = Decimal("15000")
"""monthly_savings_budget единой конфигурации трассировки."""

CUSHION_TARGET = Decimal("100000")
CUSHION_PERCENT = 30
CUSHION_THRESHOLD = Decimal("30000")
"""Порог подушки: 100 000 * 30 / 100."""


def month_start(day: date) -> date:
    """Первое число месяца указанной даты."""
    return day.replace(day=1)


def month_end(day: date) -> date:
    """Последний день месяца указанной даты."""
    return day.replace(day=monthrange(day.year, day.month)[1])


def next_month_day(day: date, day_of_month: int) -> date:
    """День следующего месяца (обрезается по длине месяца)."""
    nxt = month_end(day) + timedelta(days=1)
    _, last = monthrange(nxt.year, nxt.month)
    return nxt.replace(day=min(day_of_month, last))


@pytest.fixture
def service(db_session) -> MoneyLayersService:
    """Сервис модели слоёв на тестовой сессии."""
    return MoneyLayersService(db_session)


@pytest.fixture
def layers_user(db_session) -> User:
    """Пользователь по конфигурации трассировки решения.

    Баланс 84 500, бюджет накоплений 15 000, подушка 100 000 с порогом
    30% (== 30 000) — те же числа, что в проверочном примере эскиза.
    """
    user = User(
        email="layers@example.com",
        name="Layers User",
        starting_balance=Decimal("84500.00"),
        monthly_savings_budget=BUDGET,
        cushion_target=CUSHION_TARGET,
        cushion_threshold_percent=CUSHION_PERCENT,
    )
    db_session.add(user)
    db_session.commit()
    return user


def add_txn(
    session,
    user_id: int,
    amount: Decimal,
    txn_type: TransactionType,
    when: date,
    description: str = "Операция",
) -> Transaction:
    """Создаёт обычную транзакцию указанного типа и даты."""
    txn = Transaction(
        user_id=user_id,
        amount=amount,
        transaction_type=txn_type,
        transaction_date=when,
        description=description,
    )
    session.add(txn)
    session.commit()
    return txn


# ===========================================================================
# Блок A — таблица ожидаемых слоёв (главный блок)
# ===========================================================================


class TestExpectedLayersTable:
    """Числа по ВСЕМ трём слоям для кейсов трассировки решения.

    Каждый кейс задаёт savings_by_date напрямую — ровно то, что модель
    получает от сбора операций, — и проверяет goals_part по формуле
    от даты D. Так тест ловит неверную раскладку, которую инвариант
    суммы пропускает.
    """

    @pytest.mark.parametrize(
        "case, savings_offsets, budget, day_offset, expected_goals",
        [
            # Кейсы 1-3: fixed_date, доля взноса (на этом упала v2)
            ("1: взноса нет", {3: "15000"}, BUDGET, 0, "0"),
            ("2: взнос 5000 частичный", {3: "10000"}, BUDGET, 0, "5000"),
            ("3: взнос полный", {3: "0"}, BUDGET, 0, "15000"),
            # Кейсы 4-6: день относительно даты резерва
            ("4: день до резерва", {3: "15000"}, BUDGET, 2, "0"),
            ("5: день после резерва", {3: "15000"}, BUDGET, 4, "0"),
            ("6: частичный, день после", {3: "10000"}, BUDGET, 4, "5000"),
            # Кейсы 7-8: from_balance
            ("7: взнос в прошлом", {-5: "5000"}, BUDGET, 0, "10000"),
            ("8: взнос с будущей датой", {6: "5000"}, BUDGET, 0, "10000"),
            # Кейсы 10-11: смена бюджета внутри месяца
            ("10: бюджет уменьшен", {3: "10000"}, Decimal("8000"), 0, "0"),
            ("11: бюджет увеличен", {-5: "8000"}, Decimal("20000"), 0, "12000"),
        ],
    )
    def test_goals_part_matches_trace(
        self, service, case, savings_offsets, budget, day_offset, expected_goals
    ):
        """goals_part(D) совпадает с численной трассировкой решения."""
        # Опорный день — середина месяца, чтобы все смещения остались в нём
        today = date.today().replace(day=15)
        savings = {
            today + timedelta(days=offset): Decimal(amount)
            for offset, amount in savings_offsets.items()
        }
        target_day = today + timedelta(days=day_offset)

        result = service._goals_part_by_day(savings, [target_day], budget)

        assert result[target_day] == Decimal(expected_goals), case

    def test_case_2_partial_contribution_not_double_counted(self, service):
        """Кейс 2: частичный взнос 5 000 из 15 000 → goals_part == 5 000.

        Регрессия на блокер №1 v2: там формула вычитала расход дважды
        и показывала 0 вместо 5 000 — денег, которые физически лежат
        в остатке.
        """
        today = date.today().replace(day=15)
        reserve_day = today + timedelta(days=3)

        result = service._goals_part_by_day(
            {reserve_day: Decimal("10000")}, [today], BUDGET
        )

        assert result[today] == Decimal("5000")

    def test_case_8_future_dated_contribution(self, service):
        """Кейс 8: взнос с будущей датой → goals_part == 10 000 (v2: 5 000)."""
        today = date.today().replace(day=15)
        contribution_day = today + timedelta(days=6)

        result = service._goals_part_by_day(
            {contribution_day: Decimal("5000")}, [today], BUDGET
        )

        assert result[today] == Decimal("10000")

    def test_case_9_month_boundaries_no_accumulation(self, service):
        """Кейс 9: резервы соседних месяцев не накапливаются.

        Регрессия на блокер №2 v2: там goals_part наследовал базу через
        границу месяца и давал 15 000 / 30 000 / 30 000 там, где должен
        быть 0.
        """
        today = date.today().replace(day=15)
        this_reserve = today.replace(day=25)
        next_reserve = next_month_day(today, 25)
        savings = {this_reserve: BUDGET, next_reserve: BUDGET}

        days = [
            today,
            month_end(today),
            next_month_day(today, 1),
            next_reserve - timedelta(days=1),
            next_reserve + timedelta(days=1),
            month_end(next_reserve),
        ]
        result = service._goals_part_by_day(savings, days, BUDGET)

        assert result[today] == Decimal("0")
        assert result[month_end(today)] == Decimal("0")
        assert result[next_month_day(today, 1)] == Decimal("0")
        assert result[next_reserve - timedelta(days=1)] == Decimal("0")
        assert result[next_reserve + timedelta(days=1)] == Decimal("0")
        assert result[month_end(next_reserve)] == Decimal("0")

    def test_case_9_next_month_budget_not_inherited(self, service):
        """Кейс 9, ядро блокера №2: месяц берётся ПО ДНЮ D.

        Отдельно от предыдущего теста: если границы суммирования взять
        по месяцу reference_date, а не дня D, резерв следующего месяца
        уедет в committed для дней первого месяца и наоборот — числа
        поплывут именно так, как в v2.
        """
        today = date.today().replace(day=15)
        this_reserve = today.replace(day=25)
        next_reserve = next_month_day(today, 25)
        # Частичный взнос в первом месяце: верная формула даёт НЕнулевой
        # остаток бюджета. Нулевое ожидание такую мутацию замаскировало бы —
        # max(0, ...) обрезает и правильный, и испорченный результат в 0.
        savings = {this_reserve: Decimal("10000"), next_reserve: BUDGET}

        # Дни ПЕРВОГО месяца: резерв ВТОРОГО месяца не должен в них попадать
        before_reserve = today
        after_reserve = this_reserve + timedelta(days=1)
        last_day = month_end(today)

        result = service._goals_part_by_day(
            savings, [before_reserve, after_reserve, last_day], BUDGET
        )

        assert result[before_reserve] == Decimal("5000")
        assert result[after_reserve] == Decimal("5000")
        assert result[last_day] == Decimal("5000")

    def test_case_9_month_without_reserve_holds_one_budget(self, service):
        """Кейс 9, правый край: месяц без резерва держит ОДИН бюджет."""
        today = date.today().replace(day=15)
        savings = {today.replace(day=25): BUDGET, next_month_day(today, 25): BUDGET}
        # Третий месяц: резерва в собранном материале нет
        far_day = next_month_day(next_month_day(today, 5), 5)

        result = service._goals_part_by_day(savings, [far_day], BUDGET)

        assert result[far_day] == BUDGET

    def test_case_10_overspend_clipped_without_ui_flag(self, service, layers_user):
        """Кейс 10: перерасход обрезается до 0 и НЕ помечается в контракте.

        Решение владельца п. 3в — «промолчать». Тест защищает именно
        отсутствие признака: иначе молчание было бы подразумеваемым,
        а не зафиксированным.
        """
        today = date.today().replace(day=15)
        savings = {today + timedelta(days=3): Decimal("10000")}

        result = service._goals_part_by_day(savings, [today], Decimal("8000"))

        assert result[today] == Decimal("0")

        # В контракте нет ни одного поля про превышение бюджета
        data = service.get_money_layers(layers_user.id)
        overspend_keys = [
            key
            for key in data
            if "overspend" in key or "exceed" in key or "over_budget" in key
        ]
        assert overspend_keys == []

    def test_case_11_increased_budget_underestimates_free(self, service):
        """Кейс 11: бюджет увеличен после полного взноса → 12 000.

        «Свободно» занижается — безопасное направление ошибки,
        объявленное в докстринге формулы.
        """
        today = date.today().replace(day=15)
        savings = {today - timedelta(days=5): Decimal("8000")}

        result = service._goals_part_by_day(savings, [today], Decimal("20000"))

        assert result[today] == Decimal("12000")

    def test_reserve_configured_includes_cushion_and_goals(
        self, db_session, service, layers_user
    ):
        """reserve_configured == порог подушки + goals_part (кейс 11 числами)."""
        today = date.today()
        layers_user.monthly_savings_budget = Decimal("20000")
        add_txn(
            db_session,
            layers_user.id,
            Decimal("8000"),
            TransactionType.SAVINGS_CONTRIBUTION,
            month_start(today),
        )

        data = service.get_money_layers(layers_user.id, today)

        assert data["cushion_threshold"] == CUSHION_THRESHOLD
        assert data["goals_reserve_today"] == Decimal("12000")
        assert data["reserve_configured_today"] == Decimal("42000")

    def test_trace_example_layers(self, db_session, service, layers_user):
        """Проверочный пример решения: 84 500 → free 17 000.

        Остаток 84 500, платежи до конца месяца 37 500 (включая резерв
        целей 15 000), порог подушки 30 000 → free = 17 000.
        """
        today = date.today().replace(day=1)
        add_txn(
            db_session,
            layers_user.id,
            BUDGET,
            TransactionType.SAVINGS_RESERVE,
            today + timedelta(days=3),
            "Резерв на цели",
        )
        add_txn(
            db_session,
            layers_user.id,
            Decimal("22500"),
            TransactionType.EXPENSE,
            today + timedelta(days=5),
        )

        data = service.get_money_layers(layers_user.id, today)

        assert data["today"]["balance"] == Decimal("84500.00")
        assert data["today"]["payments"] == Decimal("37500.00")
        assert data["today"]["reserve"] == CUSHION_THRESHOLD
        assert data["today"]["free"] == Decimal("17000.00")


# ===========================================================================
# Блок B — инвариант AC-3
# ===========================================================================


class TestLayersInvariant:
    """free + payments + reserve == forecast_balance на каждом дне окна."""

    @pytest.mark.parametrize(
        "starting_balance, expense, txn_type",
        [
            ("84500", "22500", TransactionType.EXPENSE),
            ("0", "5000", TransactionType.EXPENSE),
            ("1000", "50000", TransactionType.EXPENSE),  # уход в минус
            ("84500", "15000", TransactionType.SAVINGS_RESERVE),
            ("84500", "15000", TransactionType.SAVINGS_CONTRIBUTION),
        ],
    )
    def test_sum_equals_balance_every_day(
        self, db_session, service, layers_user, starting_balance, expense, txn_type
    ):
        """Сумма слоёв равна прогнозному остатку на всех 45 днях."""
        layers_user.starting_balance = Decimal(starting_balance)
        db_session.commit()
        add_txn(
            db_session,
            layers_user.id,
            Decimal(expense),
            txn_type,
            date.today() + timedelta(days=4),
        )

        data = service.get_money_layers(layers_user.id)

        assert len(data["days"]) == WINDOW_DAYS
        for day in data["days"]:
            assert (
                day["free"] + day["payments"] + day["reserve"]
                == day["forecast_balance"]
            ), day["date"]

    def test_forecast_matches_calendar_service(self, db_session, service, layers_user):
        """forecast_balance берётся из CalendarService без пересчёта."""
        from app.services.calendar_service import CalendarService

        today = date.today()
        add_txn(
            db_session,
            layers_user.id,
            Decimal("12000"),
            TransactionType.EXPENSE,
            today + timedelta(days=2),
        )

        data = service.get_money_layers(layers_user.id, today)
        expected = CalendarService(db_session).calculate_daily_balances(
            layers_user.id, today, data["window_end"]
        )

        for day in data["days"]:
            assert day["forecast_balance"] == expected[day["date"]]

    def test_invariant_holds_across_month_boundary(
        self, db_session, service, layers_user
    ):
        """Инвариант держится по обе стороны границы месяца."""
        today = date.today()
        add_txn(
            db_session,
            layers_user.id,
            Decimal("9000"),
            TransactionType.EXPENSE,
            next_month_day(today, 3),
        )

        data = service.get_money_layers(layers_user.id, today)
        boundary_days = [
            day
            for day in data["days"]
            if day["date"] >= month_end(today) - timedelta(days=1)
        ]

        assert boundary_days
        for day in boundary_days:
            assert (
                day["free"] + day["payments"] + day["reserve"]
                == day["forecast_balance"]
            )


# ===========================================================================
# Блок C — «таяние» платежей
# ===========================================================================


class TestPaymentsMelting:
    """Слой «Платежи» тает к концу месяца и обнуляется за его границей."""

    def test_payments_monotonically_non_increasing(
        self, db_session, service, layers_user
    ):
        """payments(D) монотонно не растёт по окну (FR-1.d)."""
        today = date.today().replace(day=1)
        for offset in (2, 5, 9):
            add_txn(
                db_session,
                layers_user.id,
                Decimal("3000"),
                TransactionType.EXPENSE,
                today + timedelta(days=offset),
            )

        data = service.get_money_layers(layers_user.id, today)
        values = [day["payments"] for day in data["days"]]

        assert all(values[i] >= values[i + 1] for i in range(len(values) - 1))

    def test_payments_zero_at_and_after_payments_end(
        self, db_session, service, layers_user
    ):
        """payments(D) == 0 на payments_end и за границей месяца (C-5)."""
        today = date.today().replace(day=1)
        add_txn(
            db_session,
            layers_user.id,
            Decimal("7000"),
            TransactionType.EXPENSE,
            today + timedelta(days=3),
        )
        add_txn(
            db_session,
            layers_user.id,
            Decimal("4000"),
            TransactionType.EXPENSE,
            next_month_day(today, 10),
        )

        data = service.get_money_layers(layers_user.id, today)

        for day in data["days"]:
            if day["date"] >= data["payments_end"]:
                assert day["payments"] == Decimal("0"), day["date"]

    def test_payments_excludes_same_day_payment(self, db_session, service, layers_user):
        """Платёж дня D не входит в payments(D) — он уже вычтен из баланса."""
        today = date.today().replace(day=1)
        payment_day = today + timedelta(days=4)
        add_txn(
            db_session,
            layers_user.id,
            Decimal("6000"),
            TransactionType.EXPENSE,
            payment_day,
        )

        data = service.get_money_layers(layers_user.id, today)
        by_date = {day["date"]: day for day in data["days"]}

        assert by_date[payment_day - timedelta(days=1)]["payments"] == Decimal("6000")
        assert by_date[payment_day]["payments"] == Decimal("0")


# ===========================================================================
# Блок D — каскад _split_day
# ===========================================================================


class TestSplitDayCascade:
    """Единственный механизм обрезки слоёв."""

    @pytest.mark.parametrize(
        "balance, payments, reserve, expected",
        [
            # Хватает на всё
            ("100", "30", "20", ("50", "30", "20")),
            # Дефицит гасится из резерва
            ("40", "30", "20", ("0", "30", "10")),
            # Резерв в ноль, затем сжимаются платежи
            ("10", "30", "20", ("0", "10", "0")),
            # Ровно в ноль
            ("50", "30", "20", ("0", "30", "20")),
            # Отрицательный баланс
            ("-15", "30", "20", ("-15", "0", "0")),
            # Полностью пустой день
            ("0", "0", "0", ("0", "0", "0")),
        ],
    )
    def test_split_branches(self, service, balance, payments, reserve, expected):
        """Каскад даёт ожидаемые слои, их сумма всегда равна балансу."""
        result = service._split_day(
            Decimal(balance), Decimal(payments), Decimal(reserve)
        )

        assert result == tuple(Decimal(value) for value in expected)
        assert sum(result) == Decimal(balance)

    def test_compressed_reserve_equals_balance_without_payments(self, service):
        """Сжатая полоса: reserve == balance, когда платежей нет.

        Пример решения: порог 30 000, баланс 18 000 → резерв сжимается
        до 18 000, free = 0. Тултип обязан говорить факт (18 000 из
        30 000), а не настройку.
        """
        free, payments, reserve = service._split_day(
            Decimal("18000"), Decimal("0"), Decimal("30000")
        )

        assert free == Decimal("0")
        assert payments == Decimal("0")
        assert reserve == Decimal("18000")

    def test_reserve_configured_survives_compression(
        self, db_session, service, layers_user
    ):
        """reserve_configured хранит настройку, reserve — факт после каскада."""
        layers_user.starting_balance = Decimal("18000")
        db_session.commit()

        data = service.get_money_layers(layers_user.id)
        today = data["days"][0]

        # savings-операций нет → весь бюджет целей лежит в остатке
        assert today["reserve_configured"] == CUSHION_THRESHOLD + BUDGET
        assert today["reserve"] == Decimal("18000")
        assert today["reserve"] < today["reserve_configured"]


# ===========================================================================
# Блок E — порог подушки
# ===========================================================================


class TestCushionThreshold:
    """В слой «Резерв» входит ПОРОГ подушки, а не её цель."""

    def test_threshold_used_not_target(self, service, layers_user):
        """Используется порог 30 000, а не цель 100 000."""
        data = service.get_money_layers(layers_user.id)

        assert data["cushion_threshold"] == CUSHION_THRESHOLD
        assert data["cushion_threshold"] != CUSHION_TARGET

    def test_overaccumulated_cushion_does_not_inflate_reserve(
        self, db_session, service, layers_user
    ):
        """Перенакопленная подушка не раздувает резерв.

        Находка UX-аудита «922 155 из 100 000»: сколько бы ни было
        накоплено, в слое «Резерв» лежит настроенный порог.
        """
        layers_user.starting_balance = Decimal("922155")
        db_session.commit()

        data = service.get_money_layers(layers_user.id)

        # Вклад подушки в слой «Резерв» — ровно порог, независимо от накопленного
        assert data["cushion_threshold"] == CUSHION_THRESHOLD
        assert (
            data["days"][0]["reserve_configured"] - data["goals_reserve_today"]
            == CUSHION_THRESHOLD
        )
        # Остатка хватает — слой не сжат
        assert data["days"][0]["reserve"] == data["days"][0]["reserve_configured"]

    def test_no_cushion_configured_gives_zero_threshold(self, db_session, service):
        """Ненастроенная подушка → порог 0, слой резерва без неё."""
        user = User(
            email="nocushion@example.com",
            name="No Cushion",
            starting_balance=Decimal("50000"),
            monthly_savings_budget=Decimal("0"),
        )
        db_session.add(user)
        db_session.commit()

        data = MoneyLayersService(db_session).get_money_layers(user.id)

        assert data["cushion_threshold"] == Decimal("0")
        assert data["days"][0]["reserve_configured"] == Decimal("0")


# ===========================================================================
# Блок F — границы
# ===========================================================================


class TestBoundaries:
    """Границы месяцев, года и правый край окна."""

    def test_window_length_is_45_days(self, service, layers_user):
        """Окно всегда WINDOW_DAYS дней, включая сегодня."""
        today = date.today()

        data = service.get_money_layers(layers_user.id, today)

        assert len(data["days"]) == WINDOW_DAYS
        assert data["days"][0]["date"] == today
        assert data["window_end"] == today + timedelta(days=WINDOW_DAYS - 1)

    @pytest.mark.parametrize("day_of_month", [1, 15, 28])
    def test_horizons_for_various_reference_days(
        self, service, layers_user, day_of_month
    ):
        """Горизонты корректны для начала, середины и конца месяца."""
        reference = date.today().replace(day=day_of_month)

        horizons = service._horizons(reference)

        assert horizons.collect_start == month_start(reference)
        assert horizons.payments_end == month_end(reference)
        assert horizons.window_end == reference + timedelta(days=WINDOW_DAYS - 1)

    def test_window_spans_three_months(self, service):
        """Окно 45 дней от конца декабря захватывает три месяца и год."""
        reference = date(date.today().year, 12, 25)

        horizons = service._horizons(reference)
        months = {
            (reference + timedelta(days=offset)).month for offset in range(WINDOW_DAYS)
        }

        assert horizons.window_end.year == reference.year + 1
        assert len(months) == 3

    def test_february_month_end(self, service):
        """Конец февраля считается по фактической длине месяца."""
        year = date.today().year
        february = date(year, 2, 10)
        _, last_day = monthrange(year, 2)

        horizons = service._horizons(february)

        assert horizons.payments_end == date(year, 2, last_day)

    def test_case_12_moved_exception_beyond_window(self, service):
        """Кейс 12: savings-операция за window_end учитывается в committed.

        Резерв перенесён с 25-го числа второго месяца на 8-е число
        третьего — ключ лежит за правым краем окна, но внутри месяца
        дня D, поэтому обязан уменьшать goals_part.
        """
        today = date.today().replace(day=15)
        this_reserve = today.replace(day=25)
        moved_to = next_month_day(next_month_day(today, 1), 8)
        savings = {this_reserve: BUDGET, moved_to: BUDGET}

        last_day_of_second = month_end(next_month_day(today, 1))
        day_in_third = moved_to - timedelta(days=3)
        result = service._goals_part_by_day(
            savings, [last_day_of_second, day_in_third], BUDGET
        )

        # Во втором месяце savings нет вовсе — бюджет целиком в остатке
        assert result[last_day_of_second] == BUDGET
        # В третьем месяце перенесённый резерв ещё предстоит — goals_part 0
        assert result[day_in_third] == Decimal("0")

    def test_savings_by_date_keeps_keys_beyond_window(
        self, db_session, service, layers_user
    ):
        """Сбор операций не фильтрует savings по границам окна."""
        today = date.today()
        horizons = service._horizons(today)
        inside = today + timedelta(days=2)
        add_txn(
            db_session,
            layers_user.id,
            Decimal("5000"),
            TransactionType.SAVINGS_CONTRIBUTION,
            inside,
        )

        _, savings_by_date = service._collect_operations(
            layers_user.id, horizons.collect_start, horizons.window_end, today
        )

        assert savings_by_date[inside] == Decimal("5000")


# ===========================================================================
# Блок G — пустые состояния
# ===========================================================================


class TestEmptyStates:
    """is_empty («данных нет вообще») против window_is_flat."""

    def test_clean_database_is_empty(self, db_session, test_user_zero_balance):
        """Чистая база → is_empty=True (FR-6)."""
        data = MoneyLayersService(db_session).get_money_layers(
            test_user_zero_balance.id
        )

        assert data["is_empty"] is True

    def test_skipped_onboarding_still_empty(self, db_session, test_user_zero_balance):
        """Пропущенный онбординг не создаёт данных — is_empty остаётся True.

        Флаг first_launch для критерия не годится: skip() сбрасывает его,
        ничего не создавая.
        """
        from app.services.onboarding_service import OnboardingService

        OnboardingService(db_session).skip(test_user_zero_balance.id)

        data = MoneyLayersService(db_session).get_money_layers(
            test_user_zero_balance.id
        )

        assert data["is_empty"] is True

    def test_history_with_empty_window_is_flat_not_empty(
        self, db_session, service, layers_user
    ):
        """История есть, окно пустое → график рисуется плоским."""
        data = service.get_money_layers(layers_user.id)

        assert data["is_empty"] is False
        assert data["window_is_flat"] is True

    def test_window_with_operations_is_not_flat(self, db_session, service, layers_user):
        """Операция в окне → window_is_flat=False."""
        add_txn(
            db_session,
            layers_user.id,
            Decimal("3000"),
            TransactionType.EXPENSE,
            date.today() + timedelta(days=3),
        )

        data = service.get_money_layers(layers_user.id)

        assert data["window_is_flat"] is False

    def test_is_empty_makes_no_database_queries(self, service, monkeypatch):
        """_is_empty — чистая функция: обращений к БД внутри нет."""
        calls: list[str] = []

        def _tracked(*args, **kwargs):
            calls.append("query")
            raise AssertionError("_is_empty не должен обращаться к БД")

        monkeypatch.setattr(service.session, "query", _tracked)
        monkeypatch.setattr(service.session, "get", _tracked)

        result = service._is_empty([], {}, [], False, Decimal("0"))

        assert result is True
        assert calls == []


# ===========================================================================
# Блок H — типы операций
# ===========================================================================


class TestOperationTypes:
    """Классификация операций повторяет DashboardService."""

    def test_negative_adjustment_is_payment(self, db_session, service, layers_user):
        """ADJUSTMENT с отрицательной суммой → платёж на abs(amount)."""
        today = date.today().replace(day=1)
        add_txn(
            db_session,
            layers_user.id,
            Decimal("-4000"),
            TransactionType.ADJUSTMENT,
            today + timedelta(days=3),
            "Корректировка вниз",
        )

        data = service.get_money_layers(layers_user.id, today)
        amounts = [
            payment["amount"]
            for payment in data["upcoming_payments"]
            if payment["description"] == "Корректировка вниз"
        ]

        assert amounts == [Decimal("4000")]

    def test_positive_adjustment_is_not_payment(self, db_session, service, layers_user):
        """ADJUSTMENT с положительной суммой платежом не является."""
        today = date.today().replace(day=1)
        add_txn(
            db_session,
            layers_user.id,
            Decimal("4000"),
            TransactionType.ADJUSTMENT,
            today + timedelta(days=3),
            "Корректировка вверх",
        )

        data = service.get_money_layers(layers_user.id, today)
        descriptions = [payment["description"] for payment in data["upcoming_payments"]]

        assert "Корректировка вверх" not in descriptions

    def test_income_and_transfer_are_not_payments(
        self, db_session, service, layers_user
    ):
        """INCOME и TRANSFER в слой «Платежи» не попадают."""
        today = date.today().replace(day=1)
        add_txn(
            db_session,
            layers_user.id,
            Decimal("50000"),
            TransactionType.INCOME,
            today + timedelta(days=2),
            "Зарплата",
        )
        add_txn(
            db_session,
            layers_user.id,
            Decimal("1000"),
            TransactionType.TRANSFER,
            today + timedelta(days=2),
            "Перевод",
        )

        data = service.get_money_layers(layers_user.id, today)
        descriptions = [payment["description"] for payment in data["upcoming_payments"]]

        assert "Зарплата" not in descriptions
        assert "Перевод" not in descriptions

    def test_savings_types_are_payments_and_savings(
        self, db_session, service, layers_user
    ):
        """Savings-операции попадают и в платежи, и в savings_by_date."""
        today = date.today().replace(day=1)
        when = today + timedelta(days=3)
        add_txn(
            db_session,
            layers_user.id,
            Decimal("15000"),
            TransactionType.SAVINGS_RESERVE,
            when,
            "Резерв на цели",
        )

        horizons = service._horizons(today)
        payments, savings_by_date = service._collect_operations(
            layers_user.id, horizons.collect_start, horizons.window_end, today
        )

        assert any(payment["amount"] == Decimal("15000") for payment in payments)
        assert savings_by_date[when] == Decimal("15000")


# ===========================================================================
# Блок I — детач
# ===========================================================================


class TestDetachSafety:
    """Результат читается после закрытия сессии."""

    def test_data_readable_after_session_close(self, db_session, layers_user):
        """Все поля модели материализованы — DetachedInstanceError нет."""
        today = date.today()
        db_session.add(
            Goal(
                user_id=layers_user.id,
                name="Отпуск",
                target_amount=Decimal("50000"),
                current_amount=Decimal("10000"),
                target_date=today + timedelta(days=10),
                status=GoalStatus.ACTIVE,
                priority=1,
            )
        )
        db_session.commit()

        data = MoneyLayersService(db_session).get_money_layers(layers_user.id, today)
        db_session.close()

        assert data["today"]["free"] is not None
        assert data["milestones"][0]["name"] == "Отпуск"
        assert data["milestones"][0]["progress_percent"] == pytest.approx(20.0)
        assert data["days"][0]["forecast_balance"] is not None

    def test_milestones_limited_and_marked_beyond_window(
        self, db_session, service, layers_user
    ):
        """До 3 вех в окне + не более одной за его краем."""
        today = date.today()
        for index, offset in enumerate((3, 6, 9, 12), start=1):
            db_session.add(
                Goal(
                    user_id=layers_user.id,
                    name=f"Цель {index}",
                    target_amount=Decimal("10000"),
                    current_amount=Decimal("0"),
                    target_date=today + timedelta(days=offset),
                    status=GoalStatus.ACTIVE,
                    priority=index,
                )
            )
        db_session.add(
            Goal(
                user_id=layers_user.id,
                name="Далёкая цель",
                target_amount=Decimal("10000"),
                current_amount=Decimal("0"),
                target_date=today + timedelta(days=WINDOW_DAYS + 10),
                status=GoalStatus.ACTIVE,
                priority=9,
            )
        )
        db_session.commit()

        data = service.get_money_layers(layers_user.id, today)
        in_window = [m for m in data["milestones"] if not m["beyond_window"]]
        beyond = [m for m in data["milestones"] if m["beyond_window"]]

        assert len(in_window) == 3
        assert len(beyond) == 1
        assert beyond[0]["name"] == "Далёкая цель"


# ===========================================================================
# Блок J — fail-open
# ===========================================================================


class TestFailOpen:
    """Сбой части модели деградирует, а не роняет дашборд."""

    def test_budget_failure_sets_degraded(
        self, db_session, service, layers_user, monkeypatch
    ):
        """Сбой чтения бюджета → degraded=True, goals_part == 0."""
        from app.services.budget_reservation_service import BudgetReservationService

        def _boom(*args, **kwargs):
            raise RuntimeError("настройки резервирования недоступны")

        monkeypatch.setattr(BudgetReservationService, "get_settings", _boom)

        data = service.get_money_layers(layers_user.id)

        assert data["degraded"] is True
        assert data["goals_reserve_today"] == Decimal("0")
        assert data["reserve_configured_today"] == CUSHION_THRESHOLD

    def test_budget_failure_keeps_invariant(
        self, db_session, service, layers_user, monkeypatch
    ):
        """При деградации сумма слоёв по-прежнему равна балансу."""
        from app.services.budget_reservation_service import BudgetReservationService

        monkeypatch.setattr(
            BudgetReservationService,
            "get_settings",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("сбой")),
        )

        data = service.get_money_layers(layers_user.id)

        for day in data["days"]:
            assert (
                day["free"] + day["payments"] + day["reserve"]
                == day["forecast_balance"]
            )

    def test_budget_failure_logs_traceback(
        self, db_session, service, layers_user, monkeypatch
    ):
        """Деградация пишется в лог с трейсбеком (идиома loguru)."""
        from loguru import logger

        from app.services.budget_reservation_service import BudgetReservationService

        monkeypatch.setattr(
            BudgetReservationService,
            "get_settings",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("сбой")),
        )

        records: list[str] = []
        sink_id = logger.add(records.append, level="WARNING", backtrace=True)
        try:
            service.get_money_layers(layers_user.id)
        finally:
            logger.remove(sink_id)

        assert any("бюджет накоплений" in record for record in records)
        assert any("Traceback" in record for record in records)

    def test_goals_failure_sets_degraded(
        self, db_session, service, layers_user, monkeypatch
    ):
        """Сбой чтения целей → degraded=True, вехи пустые."""
        from app.services.goal_service import GoalService

        monkeypatch.setattr(
            GoalService,
            "get_all_by_user",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("сбой")),
        )

        data = service.get_money_layers(layers_user.id)

        assert data["degraded"] is True
        assert data["milestones"] == []

    def test_balance_failure_is_not_swallowed(
        self, db_session, service, layers_user, monkeypatch
    ):
        """Сбой расчёта баланса пробрасывается — без остатка модели нет."""
        from app.services.calendar_service import CalendarService

        monkeypatch.setattr(
            CalendarService,
            "calculate_daily_balances",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("нет базы")),
        )

        with pytest.raises(RuntimeError):
            service.get_money_layers(layers_user.id)

    def test_missing_user_returns_empty_model(self, db_session, service):
        """Отсутствующий пользователь → корректная пустая модель, без исключения."""
        data = service.get_money_layers(99999)

        assert data["is_empty"] is True
        assert len(data["days"]) == WINDOW_DAYS
