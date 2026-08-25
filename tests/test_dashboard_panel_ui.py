"""Тесты визуального слоя дашборда-щитка (протокол 0029, долг 0028).

Покрывают чистые build-функции app/components/dashboard.py: шапку
«Свободно сегодня», график полос, HTML-легенду, тултипы и расчёт
подписей оси. Формализуют три критерия приёмки протокола 0028,
проверенных тогда только вручную (AC-1, AC-4, AC-5 в UI-части),
и инварианты решений владельца (нет вердикта, нет приветствия,
шапка — не дверь).

БД не используется: функции принимают готовые MoneyLayersData /
UserProfile — фикстуры собираются словарями на относительных датах.
"""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from math import ceil

import pytest
from dash import dcc, html
import dash_bootstrap_components as dbc

from app.components.dashboard import (
    MAX_TOOLTIP_PAYMENTS,
    _axis_tickvals,
    _build_chart_empty_state,
    _build_layer_legend,
    _build_payments_tooltip,
    _build_reserve_tooltip,
    build_free_header,
    build_layers_chart,
)
from app.config.avatars import get_avatar_emoji
from app.schema.money_layers import (
    LAYER_COLORS,
    LAYER_LABELS,
    MAX_X_TICKS,
    WINDOW_DAYS,
)
from app.utils.formatters import format_date_human, format_rub

# ===========================================================================
# Хелперы: обход дерева Dash-компонентов и фикстуры-строители
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


def find_instances(component, component_type) -> list:
    """Все компоненты указанного типа в дереве."""
    return [node for node in iter_tree(component) if isinstance(node, component_type)]


def make_day(day: date, free="5000", payments="2000", reserve="3000"):
    """Один DayLayers с суммой слоёв, равной forecast_balance (AC-3)."""
    free, payments, reserve = Decimal(free), Decimal(payments), Decimal(reserve)
    return {
        "date": day,
        "free": free,
        "payments": payments,
        "reserve": reserve,
        "reserve_configured": reserve,
        "forecast_balance": free + payments + reserve,
    }


def make_payment(when: date, amount="1500", description="Интернет", recurring=False):
    """Один UpcomingPayment."""
    return {
        "date": when,
        "amount": Decimal(amount),
        "description": description,
        "category_name": None,
        "is_recurring": recurring,
    }


def make_layers_data(**overrides):
    """MoneyLayersData для нормального наполненного окна.

    Дни: free=5000 / payments=2000 / reserve=3000, минимум «Свободно»
    на 10-м дне окна. Все даты — от сегодняшнего дня.
    """
    ref = overrides.pop("reference_date", date.today())
    days = [make_day(ref + timedelta(days=offset)) for offset in range(WINDOW_DAYS)]
    min_free_date = ref + timedelta(days=10)
    days[10] = make_day(min_free_date, free="1000")
    _, last_day = monthrange(ref.year, ref.month)
    payments_end = ref.replace(day=last_day)

    data = {
        "days": days,
        "today": {
            "free": Decimal("5000"),
            "balance": Decimal("10000"),
            "payments": Decimal("2000"),
            "reserve": Decimal("3000"),
        },
        "min_free": Decimal("1000"),
        "min_free_date": min_free_date,
        "upcoming_payments": [
            make_payment(ref + timedelta(days=2)),
            make_payment(
                ref + timedelta(days=4),
                amount="4500",
                description="Аренда",
                recurring=True,
            ),
        ],
        "milestones": [],
        "reference_date": ref,
        "window_end": ref + timedelta(days=WINDOW_DAYS - 1),
        "payments_end": payments_end,
        "cushion_threshold": Decimal("2000"),
        "goals_reserve_today": Decimal("1000"),
        "reserve_configured_today": Decimal("3000"),
        "degraded": False,
        "is_empty": False,
        "window_is_flat": False,
    }
    data.update(overrides)
    return data


PROFILE = {"name": "Тест Тестович", "avatar_id": "cat"}


def get_chart_figure(card):
    """Достаёт Plotly figure из dcc.Graph карточки графика."""
    graphs = find_instances(card, dcc.Graph)
    assert len(graphs) == 1, "В карточке графика ожидается ровно один dcc.Graph"
    return graphs[0].figure


# ===========================================================================
# Шапка «Свободно сегодня»
# ===========================================================================


class TestFreeHeader:
    """build_free_header: цифры, инварианты владельца, состояния."""

    def test_amount_matches_today_free_slice(self):
        """AC-1: главная цифра шапки — значение free среза «сегодня»."""
        data = make_layers_data()

        header = build_free_header(data, PROFILE)

        text = joined_text(header)
        assert "Свободно сегодня" in text
        assert format_rub(Decimal("5000")) in text

    def test_breakdown_shows_balance_payments_reserve(self):
        """Разбор шапки: баланс − платежи − резерв с цифрами модели."""
        data = make_layers_data()

        header = build_free_header(data, PROFILE)

        text = joined_text(header)
        assert "баланс" in text
        assert "платежи" in text
        assert "резерв" in text
        assert format_rub(Decimal("10000")) in text
        assert format_rub(Decimal("2000")) in text
        assert format_rub(Decimal("3000")) in text

    def test_no_greeting_in_header(self):
        """Приветствия НЕТ (решение владельца п. 3г) — место у цифры."""
        header = build_free_header(make_layers_data(), PROFILE)

        text = joined_text(header).lower()
        for greeting in ("добрый", "здравствуй", "привет", "утро", "вечер"):
            assert greeting not in text
        assert find_by_id(header, "dashboard-greeting") is None

    def test_no_verdict_for_positive_free(self):
        """Вердикта НЕТ (решение владельца п. 3а): ни оценочных слов,
        ни статусной окраски положительной суммы."""
        header = build_free_header(make_layers_data(), PROFILE)

        text = joined_text(header).lower()
        for verdict_word in ("в порядке", "риск", "внимание", "опасно", "отлично"):
            assert verdict_word not in text
        amount_nodes = [
            node
            for node in iter_tree(header)
            if "pnl-amount" in str(getattr(node, "className", ""))
        ]
        assert len(amount_nodes) == 1
        assert "pnl-negative" not in amount_nodes[0].className

    def test_negative_free_marked_as_negative(self):
        """Единственное исключение: отрицательное «Свободно» — цветом
        риска (факт знака числа, не оценка)."""
        data = make_layers_data()
        data["today"]["free"] = Decimal("-500")

        header = build_free_header(data, PROFILE)

        amount_nodes = [
            node
            for node in iter_tree(header)
            if "pnl-amount" in str(getattr(node, "className", ""))
        ]
        assert len(amount_nodes) == 1
        assert "pnl-negative" in amount_nodes[0].className

    def test_header_is_not_a_door(self):
        """Шапка — не дверь-переход (FR-2.e): без ссылок и без
        кликабельных контейнеров (n_clicks только у кнопок)."""
        header = build_free_header(make_layers_data(), PROFILE)

        assert find_instances(header, dcc.Link) == []
        for node in iter_tree(header):
            if isinstance(node, dbc.Button):
                continue
            assert getattr(node, "n_clicks", None) in (None, 0) or not isinstance(
                node, html.Div
            )
            style = getattr(node, "style", None) or {}
            assert style.get("cursor") != "pointer"

    def test_who_block_has_avatar_recon_and_cog(self):
        """Правый угол: эмодзи аватара, имя, «Сверка», шестерёнка."""
        header = build_free_header(make_layers_data(), PROFILE)

        text = joined_text(header)
        assert get_avatar_emoji(PROFILE["avatar_id"]) in text
        assert PROFILE["name"] in text
        assert find_by_id(header, "open-recon-from-dashboard-header-btn") is not None
        assert find_by_id(header, "dashboard-settings-cog") is not None

    def test_degraded_note_present_when_degraded(self):
        """degraded=True → нейтральная сноска о неполных данных."""
        header = build_free_header(make_layers_data(degraded=True), PROFILE)

        assert "показано без бюджета целей" in joined_text(header)

    def test_degraded_note_absent_by_default(self):
        """Без деградации сноски нет."""
        header = build_free_header(make_layers_data(), PROFILE)

        assert "показано без бюджета целей" not in joined_text(header)

    def test_empty_state_header(self):
        """AC-5 (шапка): чистая база → пустое состояние без «0 ₽»,
        с кнопкой сверки и блоком профиля."""
        header = build_free_header(make_layers_data(is_empty=True), PROFILE)

        text = joined_text(header)
        assert "Пока нечего показать" in text
        assert "Свободно сегодня" not in text
        assert format_rub(Decimal("0")) not in text
        assert find_by_id(header, "open-recon-from-dashboard-empty-btn") is not None
        assert PROFILE["name"] in text


# ===========================================================================
# Подписи оси X
# ===========================================================================


class TestAxisTickvals:
    """_axis_tickvals: MAX_X_TICKS — потолок, границы окна подписаны."""

    @pytest.mark.parametrize("window_len", [1, 2, 5, 11, 12, 44, WINDOW_DAYS, 46, 90])
    def test_never_exceeds_max_ticks(self, window_len):
        """Число подписей никогда не превышает MAX_X_TICKS."""
        start = date.today()
        window = [start + timedelta(days=offset) for offset in range(window_len)]

        ticks = _axis_tickvals(window)

        assert len(ticks) <= MAX_X_TICKS

    @pytest.mark.parametrize("window_len", [1, 11, WINDOW_DAYS, 90])
    def test_first_and_last_days_are_ticked(self, window_len):
        """Первая подпись — начало окна, последняя — его правый край."""
        start = date.today()
        window = [start + timedelta(days=offset) for offset in range(window_len)]

        ticks = _axis_tickvals(window)

        assert ticks[0] == window[0]
        assert ticks[-1] == window[-1]

    @pytest.mark.parametrize("window_len", [1, 5, 11, 12, WINDOW_DAYS, 90])
    def test_no_duplicate_ticks(self, window_len):
        """Дублей подписей нет (правый край не добавляется повторно)."""
        start = date.today()
        window = [start + timedelta(days=offset) for offset in range(window_len)]

        ticks = _axis_tickvals(window)

        assert len(ticks) == len(set(ticks))

    def test_step_is_ceil_of_len_over_max(self):
        """Шаг сетки k = ceil(len / MAX_X_TICKS) — для окна 45 это 5."""
        start = date.today()
        window = [start + timedelta(days=offset) for offset in range(WINDOW_DAYS)]
        expected_step = ceil(WINDOW_DAYS / MAX_X_TICKS)

        ticks = _axis_tickvals(window)

        assert (ticks[1] - ticks[0]).days == expected_step

    def test_empty_window_gives_empty_ticks(self):
        """Пустое окно → пустой список, без исключений."""
        assert _axis_tickvals([]) == []


# ===========================================================================
# График полос
# ===========================================================================


class TestLayersChart:
    """build_layers_chart: стопка, линия «сегодня», минимум, вехи,
    пустые состояния."""

    def test_three_stacked_traces_in_order_with_layer_colors(self):
        """Три полосы снизу вверх — Свободно/Платежи/Резерв, цвета
        из LAYER_COLORS, barmode=stack."""
        fig = get_chart_figure(build_layers_chart(make_layers_data()))

        bars = [trace for trace in fig.data if trace.type == "bar"]
        assert [trace.name for trace in bars] == [
            LAYER_LABELS["free"],
            LAYER_LABELS["payments"],
            LAYER_LABELS["reserve"],
        ]
        assert [trace.marker.color for trace in bars] == [
            LAYER_COLORS["free"],
            LAYER_COLORS["payments"],
            LAYER_COLORS["reserve"],
        ]
        assert fig.layout.barmode == "stack"

    def test_plotly_legend_disabled_html_legend_present(self):
        """Легенда Plotly выключена — вместо неё HTML-легенда (FR-4)."""
        card = build_layers_chart(make_layers_data())

        fig = get_chart_figure(card)
        assert fig.layout.showlegend is False
        legend_nodes = [
            node
            for node in iter_tree(card)
            if "pnl-legend" in str(getattr(node, "className", ""))
        ]
        assert legend_nodes, "HTML-легенда pnl-legend отсутствует в карточке"

    def test_today_line_and_annotation(self):
        """Вертикальная линия «сегодня» стоит на reference_date."""
        data = make_layers_data()

        fig = get_chart_figure(build_layers_chart(data))

        ref_iso = data["reference_date"].isoformat()
        today_lines = [
            shape
            for shape in fig.layout.shapes
            if shape.type == "line" and str(shape.x0).startswith(ref_iso)
        ]
        assert len(today_lines) == 1
        annotation_texts = [ann.text for ann in fig.layout.annotations]
        assert "сегодня" in annotation_texts

    def test_min_free_marker_and_annotation(self):
        """Маркер минимума «Свободно» стоит на min_free_date с подписью."""
        data = make_layers_data()

        fig = get_chart_figure(build_layers_chart(data))

        markers = [trace for trace in fig.data if trace.type == "scatter"]
        assert len(markers) == 1
        assert str(markers[0].x[0]).startswith(data["min_free_date"].isoformat())
        assert markers[0].y[0] == float(data["min_free"])
        min_annotations = [
            ann.text for ann in fig.layout.annotations if "минимум" in ann.text
        ]
        assert min_annotations == [f"минимум: {format_rub(data['min_free'])}"]

    def test_milestones_inside_window_and_beyond(self):
        """Веха в окне — флажок у оси; за краем — стрелка справа."""
        ref = date.today()
        data = make_layers_data(
            milestones=[
                {
                    "goal_id": 1,
                    "name": "Отпуск",
                    "target_date": ref + timedelta(days=20),
                    "target_amount": Decimal("50000"),
                    "progress_percent": 40.0,
                    "beyond_window": False,
                },
                {
                    "goal_id": 2,
                    "name": "Машина",
                    "target_date": ref + timedelta(days=200),
                    "target_amount": Decimal("900000"),
                    "progress_percent": 10.0,
                    "beyond_window": True,
                },
            ]
        )

        fig = get_chart_figure(build_layers_chart(data))

        annotation_texts = [ann.text for ann in fig.layout.annotations]
        assert any(
            text.startswith("🏁") and "Отпуск" in text for text in annotation_texts
        )
        assert any(
            text.startswith("→") and "Машина" in text for text in annotation_texts
        )

    def test_is_empty_renders_no_graph_at_all(self):
        """AC-5 (график): чистая база → dcc.Graph отсутствует в дереве,
        Plotly не вызывается — выродившиеся оси невозможны."""
        card = build_layers_chart(make_layers_data(is_empty=True))

        assert find_instances(card, dcc.Graph) == []
        assert "График появится с первой операцией" in joined_text(card)

    def test_flat_window_still_renders_graph(self):
        """window_is_flat=True — данные есть, окно пустое: график
        рисуется, пустое состояние его НЕ подменяет."""
        flat_days = [
            {
                "date": day["date"],
                "free": Decimal("0"),
                "payments": Decimal("0"),
                "reserve": Decimal("0"),
                "reserve_configured": Decimal("0"),
                "forecast_balance": Decimal("0"),
            }
            for day in make_layers_data()["days"]
        ]
        card = build_layers_chart(make_layers_data(window_is_flat=True, days=flat_days))

        assert len(find_instances(card, dcc.Graph)) == 1
        assert "График появится с первой операцией" not in joined_text(card)

    def test_window_end_in_card_head(self):
        """Заголовок карточки называет правый край окна."""
        data = make_layers_data()

        card = build_layers_chart(data)

        assert f"по {format_date_human(data['window_end'])}" in joined_text(card)

    def test_chart_empty_state_has_no_number_artifacts(self):
        """Пустое состояние — текстовое, без числовых артефактов."""
        empty = _build_chart_empty_state()

        text = joined_text(empty)
        assert "50.001" not in text
        assert "−1" not in text
        assert "График появится" in text


# ===========================================================================
# Легенда и тултипы
# ===========================================================================


class TestLegendAndTooltips:
    """_build_layer_legend и тултипы: состав, AC-4, факт дня резерва."""

    def test_legend_has_three_items_with_tooltips(self):
        """Три элемента легенды с подписями слоёв и тултипом у каждого."""
        legend = _build_layer_legend(make_layers_data())

        text = joined_text(legend)
        for key in ("free", "payments", "reserve"):
            assert LAYER_LABELS[key] in text
            assert find_by_id(legend, f"pnl-legend-{key}") is not None
        tooltips = find_instances(legend, dbc.Tooltip)
        assert len(tooltips) == 3
        assert {tooltip.target for tooltip in tooltips} == {
            "pnl-legend-free",
            "pnl-legend-payments",
            "pnl-legend-reserve",
        }

    def test_payments_tooltip_lists_operations(self):
        """AC-4: тултип «Платежи» — конкретные операции с датой и суммой."""
        data = make_layers_data()

        rows = _build_payments_tooltip(data)

        text = joined_text(html.Div(rows))
        assert "Ближайшие платежи до конца месяца" in text
        first, second = data["upcoming_payments"]
        assert first["description"] in text
        assert format_date_human(first["date"]) in text
        assert format_rub(first["amount"]) in text
        assert f"🔁 {second['description']}" in text

    def test_payments_tooltip_respects_month_boundary(self):
        """Платёж за концом месяца в тултип не попадает (AC-4: «до
        конца месяца»)."""
        data = make_layers_data()
        data["upcoming_payments"] = [
            make_payment(data["payments_end"] + timedelta(days=1), description="Чужой")
        ]

        rows = _build_payments_tooltip(data)

        text = joined_text(html.Div(rows))
        assert "Чужой" not in text
        assert "До конца месяца платежей больше нет" in text

    def test_payments_tooltip_overflow_counter(self):
        """Больше MAX_TOOLTIP_PAYMENTS платежей → счётчик «…и ещё N»."""
        data = make_layers_data()
        data["upcoming_payments"] = [
            make_payment(data["reference_date"], description=f"Платёж {index}")
            for index in range(MAX_TOOLTIP_PAYMENTS + 3)
        ]

        rows = _build_payments_tooltip(data)

        assert "…и ещё 3" in joined_text(html.Div(rows))

    def test_reserve_tooltip_states_fact_when_squeezed(self):
        """Резерв сжат каскадом → тултип говорит факт дня, не настройку."""
        data = make_layers_data()
        data["today"]["reserve"] = Decimal("1800")
        data["reserve_configured_today"] = Decimal("3000")

        rows = _build_reserve_tooltip(data)

        text = joined_text(html.Div(rows))
        assert format_rub(Decimal("1800")) in text
        assert format_rub(Decimal("3000")) in text
        assert "залезаете в подушку" in text

    def test_reserve_tooltip_composition_when_intact(self):
        """Резерв не сжат → тултип раскладывает: порог подушки + бюджет
        целей."""
        rows = _build_reserve_tooltip(make_layers_data())

        text = joined_text(html.Div(rows))
        assert f"Порог подушки {format_rub(Decimal('2000'))}" in text
        assert f"бюджет целей {format_rub(Decimal('1000'))}" in text

    def test_reserve_tooltip_honest_when_degraded(self):
        """degraded → тултип не утверждает состав резерва."""
        rows = _build_reserve_tooltip(make_layers_data(degraded=True))

        assert "состав резерва показан не полностью" in joined_text(html.Div(rows))
