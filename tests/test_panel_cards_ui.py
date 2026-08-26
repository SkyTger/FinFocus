"""Тесты визуального слоя карточек-дверей щитка (протокол 0030, шаг 8).

Покрывают чистые build-функции app/components/panel_cards.py по плану
шага 10 solution-v4: конституция FR-2 (пять карточек при любом
статусе), AC-5 (пустые состояния без числовых артефактов), AC-7
(усиление маркера просадки — факт знака), оговорка #91 (dip_* при
status != OK не рисуются), href'ы дверей, подпись объявленного
расхождения в Аналитике (#87), AC-4 (подушка — строка в Целях, не
карточка), смешанный случай пустоты (#81).

БД не используется: build-функции принимают готовые срезы PanelData —
фикстуры собираются словарями на относительных датах.
"""

from datetime import date, timedelta
from decimal import Decimal

from dash import dcc

from app.components.panel_cards import (
    build_analytics_card,
    build_calendar_card,
    build_cards_row,
    build_goals_card,
    build_operations_card,
    build_wishlist_card,
)
from app.schema import CardStatus

TODAY = date.today()
TOMORROW = TODAY + timedelta(days=1)


# ===========================================================================
# Хелперы: обход дерева Dash-компонентов (стиль test_dashboard_panel_ui)
# ===========================================================================


def iter_tree(component):
    """Рекурсивный обход дерева Dash-компонентов (включая строки-листья)."""
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        yield from iter_tree(child)


def all_texts(component) -> list[str]:
    """Все строковые узлы дерева."""
    return [node for node in iter_tree(component) if isinstance(node, str)]


def joined_text(component) -> str:
    """Все тексты дерева одной строкой (для поиска подстрок)."""
    return " | ".join(all_texts(component))


def find_by_id(component, element_id):
    """Первый компонент с указанным id (None, если нет)."""
    for node in iter_tree(component):
        if getattr(node, "id", None) == element_id:
            return node
    return None


def all_classes(component) -> str:
    """Все className дерева одной строкой."""
    return " ".join(
        getattr(node, "className", "") or "" for node in iter_tree(component)
    )


def all_hrefs(component) -> list[str]:
    """href всех dcc.Link дерева."""
    return [
        node.href
        for node in iter_tree(component)
        if isinstance(node, dcc.Link) and getattr(node, "href", None)
    ]


# ===========================================================================
# Фикстуры-строители срезов
# ===========================================================================


def make_calendar(status=CardStatus.OK, dip_free=Decimal("9800"), **overrides):
    data = {
        "status": status,
        "days": [
            {
                "date": TODAY,
                "label": "Сегодня",
                "is_today": True,
                "balance": Decimal("116440"),
                "free": Decimal("36440"),
                "operations_note": "1 операция",
                "href": f"/calendar?focus_date={TODAY.isoformat()}",
            },
            {
                "date": TOMORROW,
                "label": "Завтра",
                "is_today": False,
                "balance": Decimal("86440"),
                "free": Decimal("36440"),
                "operations_note": "план",
                "href": f"/calendar?focus_date={TOMORROW.isoformat()}",
            },
        ],
        "dip_date": TODAY + timedelta(days=9),
        "dip_free": dip_free,
        "dip_is_strong": dip_free <= 0,
        "dip_href": f"/calendar?focus_date={(TODAY + timedelta(days=9)).isoformat()}",
    }
    data.update(overrides)
    return data


def make_empty_calendar(**overrides):
    data = {
        "status": CardStatus.EMPTY,
        "days": [],
        "dip_date": None,
        "dip_free": None,
        "dip_is_strong": False,
        "dip_href": None,
    }
    data.update(overrides)
    return data


def make_goals(status=CardStatus.OK):
    return {
        "status": status,
        "top_goal_id": 1,
        "top_goal_name": "Отпуск",
        "top_goal_progress": 68.0,
        "top_goal_current": Decimal("102000"),
        "top_goal_target": Decimal("150000"),
        "top_goal_target_date": TODAY + timedelta(days=50),
        "top_goal_href": "/goals?goal=1",
        "others_count": 2,
        "others_behind_count": 0,
        "others_summary": "по плану",
        "cushion_is_configured": True,
        "cushion_progress": 78.0,
        "cushion_label": "78% из 100 000 ₽",
    }


def make_empty_goals():
    return {
        "status": CardStatus.EMPTY,
        "top_goal_id": None,
        "top_goal_name": None,
        "top_goal_progress": 0.0,
        "top_goal_current": Decimal("0"),
        "top_goal_target": Decimal("0"),
        "top_goal_target_date": None,
        "top_goal_href": None,
        "others_count": 0,
        "others_behind_count": 0,
        "others_summary": "",
        "cushion_is_configured": False,
        "cushion_progress": 0.0,
        "cushion_label": "",
    }


def make_operations(status=CardStatus.OK):
    return {
        "status": status,
        "recent": [
            {
                "date": TODAY,
                "title": "Продукты",
                "amount": Decimal("2340"),
                "kind": "expense",
                "is_recurring": False,
            }
        ],
        "upcoming": [
            {
                "date": TOMORROW,
                "title": "Аренда",
                "amount": Decimal("30000"),
                "kind": "expense",
                "is_recurring": True,
            },
            {
                "date": TODAY + timedelta(days=8),
                "title": "Зарплата",
                "amount": Decimal("120000"),
                "kind": "income",
                "is_recurring": False,
            },
        ],
        "recent_href": (
            f"/transactions?start={TODAY.replace(day=1).isoformat()}"
            f"&end={TODAY.isoformat()}"
        ),
        "upcoming_href": f"/transactions?start={TODAY.isoformat()}&end=x",
    }


def make_empty_operations():
    data = make_operations(CardStatus.EMPTY)
    data["recent"] = []
    data["upcoming"] = []
    return data


def make_analytics(status=CardStatus.OK):
    return {
        "status": status,
        "month_label": "августа",
        "month_total": Decimal("78400"),
        "top_category_name": "Продукты",
        "top_category_total": Decimal("24300"),
        "top_category_share": 31.0,
        "structure": [
            {
                "name": "Продукты",
                "total": Decimal("24300"),
                "share": 31.0,
                "color": "#2E7D32",
            },
            {
                "name": "Транспорт",
                "total": Decimal("12000"),
                "share": 15.0,
                "color": "#1565C0",
            },
        ],
        "href": "/analytics",
    }


def make_empty_analytics():
    return {
        "status": CardStatus.EMPTY,
        "month_label": "августа",
        "month_total": Decimal("0"),
        "top_category_name": None,
        "top_category_total": Decimal("0"),
        "top_category_share": 0.0,
        "structure": [],
        "href": "/analytics",
    }


def make_wishlist(status=CardStatus.OK):
    return {
        "status": status,
        "items": [
            {
                "item_id": 1,
                "name": "Наушники",
                "amount_label": "18 500 ₽",
                "is_planned": True,
                "planned_date_label": "5 сентября",
                "href": "/calendar?wishlist_item=1",
            }
        ],
        "total_count": 3,
    }


def make_empty_wishlist():
    return {"status": CardStatus.EMPTY, "items": [], "total_count": 0}


def make_panel(**overrides):
    data = {
        "layers": {},
        "reference_date": TODAY,
        "calendar": make_calendar(),
        "goals": make_goals(),
        "operations": make_operations(),
        "analytics": make_analytics(),
        "wishlist": make_wishlist(),
    }
    data.update(overrides)
    return data


def make_empty_panel():
    return make_panel(
        calendar=make_empty_calendar(),
        goals=make_empty_goals(),
        operations=make_empty_operations(),
        analytics=make_empty_analytics(),
        wishlist=make_empty_wishlist(),
    )


ALL_TITLES = ("Календарь", "Цели", "Операции", "Аналитика")


# ===========================================================================
# FR-2: конституция щитка — все карточки присутствуют при любом статусе
# ===========================================================================


class TestCardsConstitution:
    """Пять карточек присутствуют ВСЕГДА (FR-2)."""

    def test_all_cards_present_on_ok(self):
        tree = build_cards_row(make_panel())
        text = joined_text(tree)
        for title in ALL_TITLES:
            assert title in text
        assert find_by_id(tree, "panel-wishlist-door") is not None

    def test_all_cards_present_on_empty(self):
        """Пустые данные не убирают карточки — меняется только содержимое."""
        tree = build_cards_row(make_empty_panel())
        text = joined_text(tree)
        for title in ALL_TITLES:
            assert title in text
        assert find_by_id(tree, "panel-wishlist-door") is not None

    def test_all_cards_present_on_failed(self):
        """Сбой блока не убирает карточку (NFR-2): дверь остаётся."""
        panel = make_panel(
            calendar={**make_empty_calendar(), "status": CardStatus.FAILED},
            goals={**make_empty_goals(), "status": CardStatus.FAILED},
            operations={**make_empty_operations(), "status": CardStatus.FAILED},
            analytics={**make_empty_analytics(), "status": CardStatus.FAILED},
            wishlist={**make_empty_wishlist(), "status": CardStatus.FAILED},
        )
        tree = build_cards_row(panel)
        text = joined_text(tree)
        for title in ALL_TITLES:
            assert title in text
        # Двери-заголовки живы даже при FAILED
        assert "/calendar" in all_hrefs(tree)
        assert "/goals" in all_hrefs(tree)
        assert "/analytics" in all_hrefs(tree)


# ===========================================================================
# AC-5: пустые состояния без числовых артефактов
# ===========================================================================


class TestEmptyStates:
    """Пустая карточка — смысл раздела, ни ₽, ни %, ни нулей."""

    def test_no_currency_or_percent_in_empty_tree(self):
        tree = build_cards_row(make_empty_panel())
        text = joined_text(tree)
        assert "₽" not in text
        assert "%" not in text
        assert "0 " not in text and " 0" not in text

    def test_empty_calendar_has_no_day_windows(self):
        tree = build_calendar_card(make_empty_calendar())
        assert "pnl-day" not in all_classes(tree).replace("pnl-days", "")

    def test_failed_card_has_no_numbers(self):
        """FAILED — индикация без чисел, дверь работает."""
        tree = build_calendar_card(
            {**make_empty_calendar(), "status": CardStatus.FAILED}
        )
        text = joined_text(tree)
        assert "Не удалось загрузить раздел" in text
        assert "₽" not in text


# ===========================================================================
# AC-7 и оговорка #91: маркер просадки
# ===========================================================================


class TestDipMarker:
    """Маркер просадки: усиление — факт знака, при status != OK не рисуется."""

    def test_positive_min_no_strong_class(self):
        tree = build_calendar_card(make_calendar(dip_free=Decimal("9800")))
        classes = all_classes(tree)
        assert "pnl-flagline" in classes
        assert "pnl-flagline-strong" not in classes

    def test_zero_or_negative_min_strong_class(self):
        tree = build_calendar_card(make_calendar(dip_free=Decimal("-100")))
        assert "pnl-flagline-strong" in all_classes(tree)
        tree_zero = build_calendar_card(make_calendar(dip_free=Decimal("0")))
        assert "pnl-flagline-strong" in all_classes(tree_zero)

    def test_empty_status_ignores_nonempty_dip_fields(self):
        """Целевой тест #91: EMPTY при непустых dip_* → маркера в дереве НЕТ.

        _window_min_free на пустом окне возвращает (Decimal("0"),
        date.today()), а не None — без оговорки чистая база дала бы
        «Ближайшая просадка: сегодня, 0 ₽», числовой артефакт AC-5.
        """
        data = make_empty_calendar(
            dip_date=TODAY,
            dip_free=Decimal("0"),
            dip_is_strong=True,
            dip_href="/calendar?focus_date=x",
        )
        tree = build_calendar_card(data)
        assert "pnl-flagline" not in all_classes(tree)
        assert "просадка" not in joined_text(tree).lower()


# ===========================================================================
# Карточка «Календарь»: два окошка (решение владельца 2026-08-26)
# ===========================================================================


class TestCalendarWindows:
    """Окошек два — сегодня и завтра; «вчера» убрано решением владельца."""

    def test_two_windows_today_and_tomorrow(self):
        tree = build_calendar_card(make_calendar())
        labels = [
            node for node in all_texts(tree) if node in ("Вчера", "Сегодня", "Завтра")
        ]
        assert labels == ["Сегодня", "Завтра"]

    def test_windows_are_calendar_doors(self):
        tree = build_calendar_card(make_calendar())
        hrefs = all_hrefs(tree)
        assert f"/calendar?focus_date={TODAY.isoformat()}" in hrefs
        assert f"/calendar?focus_date={TOMORROW.isoformat()}" in hrefs

    def test_today_window_marked(self):
        tree = build_calendar_card(make_calendar())
        assert "pnl-day-today" in all_classes(tree)


# ===========================================================================
# href'ы всех дверей
# ===========================================================================


class TestDoorHrefs:
    """Каждая дверь ведёт в свой раздел (FR-1, FR-3, AC-2)."""

    def test_all_door_hrefs(self):
        tree = build_cards_row(make_panel())
        hrefs = all_hrefs(tree)
        assert "/calendar" in hrefs  # заголовок Календаря
        assert "/goals" in hrefs  # заголовок Целей
        assert "/goals?goal=1" in hrefs  # топ-цель
        assert "/analytics" in hrefs  # Аналитика
        assert any(h.startswith("/transactions?start=") for h in hrefs)
        assert "/calendar?wishlist_item=1" in hrefs  # хотелка, уровень 2

    def test_wishlist_door_node_present(self):
        """Уровень 1 двери Wishlist — узел для clientside-триггера.

        Узел — слой-подложка ВНУТРИ полосы, а не сам контейнер
        (3.5-m-fix ревью 0030): id на контейнере ловил всплытие клика
        от вложенных ссылок-хотелок и открывал модал поверх календаря.
        """
        tree = build_wishlist_card(make_wishlist())
        assert getattr(tree, "id", None) is None  # контейнер без id
        door = find_by_id(tree, "panel-wishlist-door")
        assert door is not None
        assert "pnl-wish-hitbox" in (door.className or "")

    def test_wishlist_links_not_inside_door_node(self):
        """AC-8: хотелки — НЕ потомки узла уровня 1 (регрессия 3.5-m-fix).

        Клик по dcc.Link, вложенному в кликабельный узел, всплывает и
        инкрементит его n_clicks — модал открывался поверх календаря.
        Слой-подложка обязан быть пустым, ссылки — его соседями.
        """
        tree = build_wishlist_card(make_wishlist())
        door = find_by_id(tree, "panel-wishlist-door")
        # внутри узла двери нет НИЧЕГО — тем более ссылок
        assert list(iter_tree(door)) == [door]
        # ссылки-хотелки при этом в полосе есть
        assert "/calendar?wishlist_item=1" in all_hrefs(tree)


# ===========================================================================
# Карточка «Аналитика»: только расходы + объявленное расхождение
# ===========================================================================


class TestAnalyticsCard:
    """Только расходы; расхождение с графиком объявлено, не скрыто."""

    def test_no_income_word_in_tree(self):
        """Показателя «Доходы за месяц» нет ни в каком виде (RTM #13)."""
        tree = build_analytics_card(make_analytics())
        assert "Доход" not in joined_text(tree)

    def test_discrepancy_note_present(self):
        """Подпись объявленного расхождения (#87): «без регулярных...»."""
        tree = build_analytics_card(make_analytics())
        text = joined_text(tree)
        assert "расходы августа" in text
        assert "без регулярных и взносов в цели" in text

    def test_mini_structure_without_plotly(self):
        """Мини-структура — CSS-полоска (RTM #70), Plotly в карточке нет."""
        tree = build_analytics_card(make_analytics())
        assert "pnl-mini-bar" in all_classes(tree)
        types = {type(node).__name__ for node in iter_tree(tree)}
        assert "Graph" not in types


# ===========================================================================
# AC-4: подушка — строка внутри карточки «Цели», не отдельная карточка
# ===========================================================================


class TestCushionRow:
    """Подушка живёт строкой в Целях; отдельной карточки в ряду нет."""

    def test_cushion_row_inside_goals_card(self):
        tree = build_goals_card(make_goals())
        text = joined_text(tree)
        assert "Подушка" in text
        assert "78% из 100 000 ₽" in text
        assert "pnl-bar-thin" in all_classes(tree)

    def test_no_cushion_card_in_row(self):
        """В ряду ровно 4 двери + wishlist-полоса — подушки-карточки нет."""
        tree = build_cards_row(make_panel())
        door_titles = [
            node for node in all_texts(tree) if node in ALL_TITLES + ("Подушка",)
        ]
        assert door_titles.count("Подушка") == 1  # строка в Целях
        classes = all_classes(tree)
        slots = [
            slot
            for slot in ("calendar", "goals", "operations", "analytics")
            if f"pnl-door-{slot}" in classes
        ]
        assert len(slots) == 4  # ровно четыре гнезда, пятого (подушки) нет
        assert "pnl-door-cushion" not in classes

    def test_unconfigured_cushion_hidden(self):
        data = make_goals()
        data["cushion_is_configured"] = False
        data["cushion_progress"] = 0.0
        data["cushion_label"] = ""
        tree = build_goals_card(data)
        assert "Подушка" not in joined_text(tree)


# ===========================================================================
# Смешанный случай пустоты (#81): карточки честны сами за себя
# ===========================================================================


class TestMixedEmptiness:
    """Общего признака пустоты нет — статус каждой карточки независим."""

    def test_goals_ok_while_others_empty(self):
        panel = make_empty_panel()
        panel["goals"] = make_goals()
        tree = build_cards_row(panel)
        text = joined_text(tree)
        assert "Отпуск" in text  # цель с цифрами
        assert "Операций в этом месяце нет" in text  # операции пусты

    def test_operations_ok_while_goals_empty(self):
        panel = make_empty_panel()
        panel["operations"] = make_operations()
        tree = build_cards_row(panel)
        text = joined_text(tree)
        assert "Продукты" in text
        assert "Целей пока нет" in text


# ===========================================================================
# Карточка «Операции»: группы и маркер регулярной
# ===========================================================================


class TestOperationsCard:
    def test_groups_and_recurring_marker(self):
        tree = build_operations_card(make_operations())
        text = joined_text(tree)
        assert "Недавние" in text
        assert "Предстоящие" in text
        assert "🔁" in text  # материализованный recurring-инстанс

    def test_group_links_carry_source_ranges(self):
        data = make_operations()
        tree = build_operations_card(data)
        hrefs = all_hrefs(tree)
        assert data["recent_href"] in hrefs
        assert data["upcoming_href"] in hrefs

    def test_amount_signs_by_kind(self):
        tree = build_operations_card(make_operations())
        text = joined_text(tree)
        assert "−30 000 ₽" in text  # expense — типографский минус
        assert "+120 000 ₽" in text  # income
