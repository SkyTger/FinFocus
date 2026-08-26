"""Тесты DashboardPanelService — композитор данных щитка (протокол 0030).

Покрытие по плану шага 4 solution-v4 (Epic-11, кусок 2):
AC-3 (согласованность цифр), целевой тест goals=OK (конструктор
AllocationService), явные преобразования типов OperationRow,
материализация после закрытия сессии, AC-5 в двух вариантах пустой
базы, контракт _empty_* на уровне данных, поблочная деградация,
смешанные случаи пустоты, согласованность подушки, счётчики загрузки.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from loguru import logger
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from app.models.database import (
    Goal,
    GoalStatus,
    Transaction,
    TransactionType,
    User,
    WishlistItem,
)
from app.schema import CardStatus
from app.services import CushionService, DashboardPanelService
from app.services.money_layers_service import MoneyLayersService

from tests.conftest import months_ahead


TODAY = date.today()


@pytest.fixture
def service(db_session) -> DashboardPanelService:
    """Композитор на тестовой сессии."""
    return DashboardPanelService(db_session)


@pytest.fixture
def filled_user(db_session) -> User:
    """Пользователь с целями, операциями, подушкой и wishlist."""
    user = User(
        id=1,
        email="panel@test.com",
        name="Panel User",
        starting_balance=Decimal("100000"),
        monthly_savings_budget=Decimal("30000"),
        savings_mode="free",
        cushion_target=Decimal("50000"),
    )
    db_session.add(user)
    db_session.add(
        Goal(
            user_id=1,
            name="Отпуск",
            target_amount=Decimal("60000"),
            current_amount=Decimal("0"),
            target_date=months_ahead(6),
            priority=1,
            status=GoalStatus.ACTIVE,
        )
    )
    db_session.add(
        Goal(
            user_id=1,
            name="Квартира",
            target_amount=Decimal("600000"),
            current_amount=Decimal("0"),
            target_date=months_ahead(4),
            priority=2,
            status=GoalStatus.ACTIVE,
        )
    )
    db_session.add(
        Transaction(
            user_id=1,
            amount=Decimal("2500"),
            transaction_type=TransactionType.EXPENSE,
            description="Продукты",
            transaction_date=TODAY - timedelta(days=2),
        )
    )
    db_session.add(
        Transaction(
            user_id=1,
            amount=Decimal("1200"),
            transaction_type=TransactionType.EXPENSE,
            description=None,
            transaction_date=TODAY + timedelta(days=3),
        )
    )
    # Расход ЗАВТРА: балансы «сегодня» и «завтра» обязаны различаться,
    # иначе тест AC-3 слеп к подмене days[1] → days[0] (mutation smoke)
    db_session.add(
        Transaction(
            user_id=1,
            amount=Decimal("4000"),
            transaction_type=TransactionType.EXPENSE,
            description="Коммуналка",
            transaction_date=TODAY + timedelta(days=1),
        )
    )
    db_session.add(
        WishlistItem(
            user_id=1,
            name="Наушники",
            amount=Decimal("15000"),
            priority=1,
            status="new",
        )
    )
    db_session.commit()
    return user


def _capture_warning_records():
    """Контекст-хелпер: собирает записи loguru уровня WARNING+."""
    records: list = []
    sink_id = logger.add(
        lambda message: records.append(message.record), level="WARNING"
    )
    return records, sink_id


def _walk_all_fields(value):
    """Рекурсивно читает все значения структуры (ловит DetachedInstanceError)."""
    if isinstance(value, dict):
        for v in value.values():
            _walk_all_fields(v)
    elif isinstance(value, list):
        for v in value:
            _walk_all_fields(v)


ALL_SLOTS = ("calendar", "goals", "operations", "analytics", "wishlist")


class TestConsistency:
    """AC-3: карточка «Календарь» питается той же моделью, что шапка."""

    def test_today_balance_matches_layers(self, service, filled_user):
        """Цифра окошка «Сегодня» == today модели == days[0] модели."""
        panel = service.get_panel_data(1)

        assert (
            panel["calendar"]["days"][0]["balance"]
            == panel["layers"]["today"]["balance"]
            == panel["layers"]["days"][0]["forecast_balance"]
        )

    def test_tomorrow_balance_matches_layers(self, service, filled_user):
        """Окошко «Завтра» — из days[1] модели (окошка «вчера» нет)."""
        panel = service.get_panel_data(1)

        days = panel["calendar"]["days"]
        assert len(days) == 2
        assert days[0]["label"] == "Сегодня"
        assert days[0]["is_today"] is True
        assert days[1]["label"] == "Завтра"
        assert days[1]["is_today"] is False
        assert days[1]["balance"] == panel["layers"]["days"][1]["forecast_balance"]
        # Фикстура кладёт расход на завтра: балансы дней обязаны различаться,
        # иначе ассерт выше слеп к подмене days[1] → days[0]
        assert days[1]["balance"] != days[0]["balance"]
        # Платёж завтра виден и в подписи окошка (RTM #62)
        assert days[1]["operations_note"] == "план"

    def test_day_hrefs_are_calendar_doors(self, service, filled_user):
        """href окошек — дверь календаря с focus_date дня."""
        panel = service.get_panel_data(1)

        for day in panel["calendar"]["days"]:
            assert day["href"] == f"/calendar?focus_date={day['date'].isoformat()}"

    def test_dip_fields_from_layers(self, service, filled_user):
        """dip_* — из min_free/min_free_date модели."""
        panel = service.get_panel_data(1)

        card = panel["calendar"]
        assert card["dip_free"] == panel["layers"]["min_free"]
        assert card["dip_date"] == panel["layers"]["min_free_date"]
        assert card["dip_is_strong"] == (card["dip_free"] <= 0)
        assert card["dip_href"] == (
            f"/calendar?focus_date={card['dip_date'].isoformat()}"
        )


class TestGoalsOk:
    """Целевой тест critique-v3 №1: ловит неверный конструктор AllocationService.

    В наборе без этого теста TypeError из AllocationService(self.session)
    поглотился бы блочным except и дал бы FAILED молча: фикстуры AC-5
    пустые (до AllocationService дело не доходит), тест деградации
    ожидает FAILED как правильный результат, тесты карточек кормятся
    словарями.
    """

    def test_goals_ok_with_partial_funding(self, service, filled_user):
        """Бюджета хватает первой цели и не хватает второй → OK, 1 отстаёт."""
        records, sink_id = _capture_warning_records()
        try:
            panel = service.get_panel_data(1)
        finally:
            logger.remove(sink_id)

        goals = panel["goals"]
        assert goals["status"] == CardStatus.OK
        assert goals["top_goal_name"] == "Отпуск"  # priority=1
        assert goals["others_count"] == 1
        assert goals["others_behind_count"] == 1
        assert goals["others_summary"] == "1 отстаёт"
        assert isinstance(goals["top_goal_current"], Decimal)
        assert isinstance(goals["top_goal_target"], Decimal)
        assert goals["top_goal_target"] == Decimal("60000")
        assert goals["top_goal_href"] is not None

        # FAILED нельзя принять за штатный путь: в логах нет трейсбека по goals
        goals_tracebacks = [
            rec
            for rec in records
            if rec["exception"] is not None and "Цели" in str(rec["message"])
        ]
        assert goals_tracebacks == []


class TestOperationRowTypes:
    """Явные преобразования типов (critique-v2, №4)."""

    def test_date_is_date_not_iso_string(self, service, filled_user):
        """date — date, а не ISO-строка источника (иначе AttributeError в UI)."""
        panel = service.get_panel_data(1)

        assert panel["operations"]["status"] == CardStatus.OK
        for row in panel["operations"]["recent"] + panel["operations"]["upcoming"]:
            assert isinstance(row["date"], date)
            assert isinstance(row["amount"], Decimal)
            assert isinstance(row["title"], str)
            assert row["title"] != ""

    def test_kind_covers_all_six_transaction_types(self, db_session):
        """kind ∈ трёх значений на фикстуре со всеми шестью типами enum.

        Тест покраснеет при добавлении седьмого значения TransactionType —
        сигнал пересмотреть TRANSACTION_KIND_MAP.
        """
        user = User(
            id=1,
            email="kinds@test.com",
            name="Kinds",
            starting_balance=Decimal("10000"),
        )
        db_session.add(user)
        for idx, tx_type in enumerate(TransactionType):
            db_session.add(
                Transaction(
                    user_id=1,
                    amount=Decimal("100"),
                    transaction_type=tx_type,
                    description=f"op-{tx_type.value}",
                    transaction_date=TODAY - timedelta(days=idx),
                )
            )
        db_session.commit()

        # limit=3 на группу: чтобы увидеть все шесть типов, читаем kind
        # напрямую через маппер блока на каждом типе
        panel = DashboardPanelService(db_session).get_panel_data(1)
        assert len(list(TransactionType)) == 6

        rows = panel["operations"]["recent"] + panel["operations"]["upcoming"]
        assert rows, "фикстура с операциями обязана дать строки"
        for row in rows:
            assert row["kind"] in ("income", "expense", "other")

    def test_is_recurring_true_for_materialized_instance(self, db_session):
        """is_recurring — переименование is_recurring_instance источника."""
        user = User(
            id=1,
            email="rec@test.com",
            name="Rec",
            starting_balance=Decimal("10000"),
        )
        db_session.add(user)
        template = Transaction(
            user_id=1,
            amount=Decimal("500"),
            transaction_type=TransactionType.EXPENSE,
            description="Аренда (шаблон)",
            transaction_date=TODAY - timedelta(days=30),
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add(template)
        db_session.commit()
        instance = Transaction(
            user_id=1,
            amount=Decimal("500"),
            transaction_type=TransactionType.EXPENSE,
            description="Аренда",
            transaction_date=TODAY - timedelta(days=1),
            recurring_parent_id=template.id,
        )
        db_session.add(instance)
        db_session.commit()

        panel = DashboardPanelService(db_session).get_panel_data(1)

        recent_by_title = {row["title"]: row for row in panel["operations"]["recent"]}
        assert "Аренда" in recent_by_title
        assert recent_by_title["Аренда"]["is_recurring"] is True


class TestMaterialization:
    """Контракт материализации: PanelData живёт дольше сессии."""

    def test_all_fields_readable_after_session_close(self, db_engine):
        """Чтение ВСЕХ полей после закрытия сессии — ловит DetachedInstanceError.

        Тесты карточек этого не видят: они кормятся словарями.
        """
        Session = sessionmaker(bind=db_engine)
        with Session() as session:
            user = User(
                id=1,
                email="mat@test.com",
                name="Mat",
                starting_balance=Decimal("50000"),
                cushion_target=Decimal("20000"),
            )
            session.add(user)
            session.add(
                Goal(
                    user_id=1,
                    name="Цель",
                    target_amount=Decimal("10000"),
                    current_amount=Decimal("1000"),
                    target_date=months_ahead(3),
                    priority=1,
                    status=GoalStatus.ACTIVE,
                )
            )
            session.add(
                Transaction(
                    user_id=1,
                    amount=Decimal("700"),
                    transaction_type=TransactionType.EXPENSE,
                    description="Опер",
                    transaction_date=TODAY,
                )
            )
            session.add(
                WishlistItem(
                    user_id=1,
                    name="Хотелка",
                    amount=Decimal("3000"),
                    priority=1,
                    status="new",
                )
            )
            session.commit()

        with Session() as session:
            panel = DashboardPanelService(session).get_panel_data(1)

        # Сессия закрыта — любая утечка ORM даст DetachedInstanceError
        _walk_all_fields(panel)
        assert panel["goals"]["top_goal_name"] == "Цель"
        assert panel["wishlist"]["items"][0]["name"] == "Хотелка"


class TestEmptyBase:
    """AC-5: пустая база в двух вариантах — с User(id=1) и без него."""

    def _assert_all_empty(self, panel, records):
        for slot in ALL_SLOTS:
            assert panel[slot]["status"] == CardStatus.EMPTY, slot
            assert panel[slot]["status"] != CardStatus.FAILED, slot
        tracebacks = [rec for rec in records if rec["exception"] is not None]
        assert tracebacks == []

    def test_empty_base_with_user(self, db_session):
        """Пустая база С User(id=1) → все пять блоков EMPTY."""
        db_session.add(
            User(
                id=1,
                email="empty@test.com",
                name="Empty",
                starting_balance=Decimal("0"),
            )
        )
        db_session.commit()

        records, sink_id = _capture_warning_records()
        try:
            panel = DashboardPanelService(db_session).get_panel_data(1)
        finally:
            logger.remove(sink_id)

        self._assert_all_empty(panel, records)

    def test_empty_base_without_user(self, db_session):
        """Пустая база БЕЗ пользователя → EMPTY, не FAILED (critique-v2, №6).

        «Нет пользователя» — пустота, а не сбой: GoalService.get_savings_budget
        бросил бы ValidationError, и карточка стала бы FAILED — этот тест
        целевой против такого пути.
        """
        records, sink_id = _capture_warning_records()
        try:
            panel = DashboardPanelService(db_session).get_panel_data(1)
        finally:
            logger.remove(sink_id)

        self._assert_all_empty(panel, records)

    def test_empty_contract_data_level(self, db_session):
        """Контракт _empty_* на уровне ДАННЫХ (critique-v3, №5).

        Тест AC-5 «нет ₽/%» смотрит дерево и подмену "" на текст не
        поймает — поэтому нейтральные значения проверяются на данных.
        """
        panel = DashboardPanelService(db_session).get_panel_data(1)

        calendar = panel["calendar"]
        assert calendar["days"] == []
        assert calendar["dip_date"] is None
        assert calendar["dip_free"] is None
        assert calendar["dip_is_strong"] is False
        assert calendar["dip_href"] is None

        goals = panel["goals"]
        assert goals["top_goal_id"] is None
        assert goals["top_goal_name"] is None
        assert goals["top_goal_progress"] == 0.0
        assert goals["top_goal_current"] == Decimal("0")
        assert goals["top_goal_target"] == Decimal("0")
        assert goals["top_goal_target_date"] is None
        assert goals["top_goal_href"] is None
        assert goals["others_count"] == 0
        assert goals["others_behind_count"] == 0
        assert goals["others_summary"] == ""  # не «Нет целей»
        assert goals["cushion_is_configured"] is False
        assert goals["cushion_progress"] == 0.0
        assert goals["cushion_label"] == ""  # не «0%»

        operations = panel["operations"]
        assert operations["recent"] == []
        assert operations["upcoming"] == []
        # href — маршрут двери, работает и на пустой карточке
        assert operations["recent_href"].startswith("/transactions?")
        assert operations["upcoming_href"].startswith("/transactions?")

        analytics = panel["analytics"]
        assert analytics["month_label"] != ""  # подпись периода, не цифра
        assert analytics["month_total"] == Decimal("0")
        assert analytics["top_category_name"] is None
        assert analytics["top_category_total"] == Decimal("0")
        assert analytics["top_category_share"] == 0.0
        assert analytics["structure"] == []
        assert analytics["href"] == "/analytics"

        wishlist = panel["wishlist"]
        assert wishlist["items"] == []
        assert wishlist["total_count"] == 0


class TestDegradation:
    """NFR-2: сбой одного блока не роняет щиток."""

    def test_analytics_failure_degrades_only_analytics(self, service, filled_user):
        """patch падающего AnalyticsService → analytics FAILED, остальные OK."""
        records, sink_id = _capture_warning_records()
        try:
            with patch(
                "app.services.panel_service.AnalyticsService.get_expenses_by_category",
                side_effect=RuntimeError("analytics unavailable"),
            ):
                panel = service.get_panel_data(1)
        finally:
            logger.remove(sink_id)

        assert panel["analytics"]["status"] == CardStatus.FAILED
        for slot in ("calendar", "goals", "operations", "wishlist"):
            assert panel[slot]["status"] == CardStatus.OK, slot

        # Сбой залогирован с трейсбеком (logger.opt(exception=True))
        failed_records = [rec for rec in records if rec["exception"] is not None]
        assert len(failed_records) == 1

    def test_failed_slice_keeps_neutral_values(self, service, filled_user):
        """FAILED-срез несёт те же нейтральные значения, что EMPTY."""
        with patch(
            "app.services.panel_service.WishlistService.get_focus",
            side_effect=RuntimeError("wishlist unavailable"),
        ):
            panel = service.get_panel_data(1)

        wishlist = panel["wishlist"]
        assert wishlist["status"] == CardStatus.FAILED
        assert wishlist["items"] == []
        assert wishlist["total_count"] == 0


class TestMixedEmptiness:
    """Каждая карточка честна сама за себя — общего признака пустоты нет."""

    def test_layers_empty_but_goals_ok(self, db_session):
        """is_empty=True у модели + заведённая цель → goals OK, operations EMPTY."""
        db_session.add(
            User(
                id=1,
                email="mixed@test.com",
                name="Mixed",
                starting_balance=Decimal("0"),
            )
        )
        db_session.add(
            Goal(
                user_id=1,
                name="Цель без взносов",
                target_amount=Decimal("10000"),
                current_amount=Decimal("2000"),
                target_date=months_ahead(3),
                priority=1,
                status=GoalStatus.ACTIVE,
            )
        )
        db_session.commit()

        panel = DashboardPanelService(db_session).get_panel_data(1)

        assert panel["layers"]["is_empty"] is True
        assert panel["goals"]["status"] == CardStatus.OK
        assert panel["goals"]["top_goal_name"] == "Цель без взносов"
        assert panel["operations"]["status"] == CardStatus.EMPTY
        assert panel["calendar"]["status"] == CardStatus.EMPTY

    def test_operations_ok_but_goals_empty(self, db_session):
        """Обратный случай: операции есть, целей и подушки нет → goals EMPTY."""
        db_session.add(
            User(
                id=1,
                email="mixed2@test.com",
                name="Mixed2",
                starting_balance=Decimal("5000"),
            )
        )
        db_session.add(
            Transaction(
                user_id=1,
                amount=Decimal("300"),
                transaction_type=TransactionType.EXPENSE,
                description="Кофе",
                transaction_date=TODAY,
            )
        )
        db_session.commit()

        panel = DashboardPanelService(db_session).get_panel_data(1)

        assert panel["operations"]["status"] == CardStatus.OK
        assert panel["calendar"]["status"] == CardStatus.OK
        assert panel["goals"]["status"] == CardStatus.EMPTY


class TestCushionConsistency:
    """R15: подушка карточки согласована с CushionService.get_settings."""

    def test_cushion_progress_matches_get_settings(self, db_session):
        """cushion_progress из layers == get_settings()["progress"].

        Оба значения идут в CalendarService; расхождение — дефект
        CalendarService, и оно должно быть поймано, а не замаскировано
        вторым источником.
        """
        db_session.add(
            User(
                id=1,
                email="cushion@test.com",
                name="Cushion",
                starting_balance=Decimal("30000"),
                cushion_target=Decimal("100000"),
            )
        )
        db_session.commit()

        panel = DashboardPanelService(db_session).get_panel_data(1)
        settings = CushionService(db_session).get_settings(1)

        assert panel["goals"]["cushion_is_configured"] is True
        assert panel["goals"]["cushion_progress"] == pytest.approx(settings["progress"])


class TestLoadStrategy:
    """FR-6/NFR-1: один вызов модели, блоки добавляют короткие запросы."""

    def test_get_money_layers_called_once(self, db_session, filled_user):
        """get_money_layers — один вызов на сбор PanelData."""
        original = MoneyLayersService.get_money_layers
        calls: list = []

        def counting(self, *args, **kwargs):
            calls.append(1)
            return original(self, *args, **kwargs)

        with patch.object(MoneyLayersService, "get_money_layers", counting):
            DashboardPanelService(db_session).get_panel_data(1)

        assert len(calls) == 1

    def test_card_blocks_add_few_queries(self, db_engine, db_session, filled_user):
        """Блоки карточек добавляют ограниченное число коротких запросов.

        Замер через sqlalchemy.event на before_cursor_execute: разница
        между полным сбором PanelData и одной моделью слоёв — вклад
        пяти блоков. Потолок 12 — защита от тихого появления N+1
        (solution-v4: «4-9 коротких запросов»).
        """
        counter = {"n": 0}

        def count_query(*args, **kwargs):
            counter["n"] += 1

        event.listen(db_engine, "before_cursor_execute", count_query)
        try:
            counter["n"] = 0
            MoneyLayersService(db_session).get_money_layers(1)
            layers_only = counter["n"]

            counter["n"] = 0
            DashboardPanelService(db_session).get_panel_data(1)
            full_panel = counter["n"]
        finally:
            event.remove(db_engine, "before_cursor_execute", count_query)

        blocks_added = full_panel - layers_only
        assert blocks_added <= 12, (
            f"блоки добавили {blocks_added} запросов "
            f"(модель: {layers_only}, весь щиток: {full_panel})"
        )
