"""Якорные тесты визуального слоя тултипа дня календаря (calendar.css).

Закрывают находку UX-аудита 2026-08-20 (P2): тултип дня обрезался
правым краем сетки в колонках СБ/ВС. Причина была не в правиле
переноса тултипа налево (оно совпадало и совпадает), а в двух
`overflow: hidden` — у `.calendar-grid-wrapper` и у `.calendar-grid`:
абсолютно позиционированный тултип пятницы открывался направо,
выходил за край сетки и молча отрезался. Эти `overflow: hidden`
появились в редизайне «стекла» (3f1fa90) и откатили правку 51db795,
которая ставила `overflow: visible` именно ради тултипа.

Механика тестов та же, что в tests/test_nav_rail_visual.py: CSS
проверяется как текст (парсера CSS в проекте нет осознанно),
комментарии вырезаются, чтобы упоминание свойства в пояснении не
давало ложного результата. Это тесты-якоря против регрессии
«правку сделали, эффекта не заметили», а не тесты рендеринга —
сам факт, что тултип виден целиком, подтверждается только в браузере.
"""

import pathlib
import re
from datetime import date

from app.components.calendar import build_calendar_grid

CALENDAR_CSS = (
    pathlib.Path(__file__).resolve().parent.parent / "app" / "assets" / "calendar.css"
)

# Колонки, у которых тултип открывается НАЛЕВО: Пт, Сб, Вс.
# nth-child считается внутри .calendar-week-row, где ровно 7 ячеек.
LEFT_SIDE_SELECTORS = (
    ".calendar-day:nth-child(7n-2)",
    ".calendar-day:nth-child(7n-1)",
    ".calendar-day:nth-child(7n)",
)


def _css_without_comments() -> str:
    """Текст calendar.css без /* ... */."""
    css = CALENDAR_CSS.read_text(encoding="utf-8")
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _rule_bodies(css: str, selector: str) -> str:
    """Все тела правил для точного селектора, склеенные в одну строку.

    Селектор ищется целиком среди участников группы (`a, b { ... }`):
    правило переноса тултипа записано именно группой из трёх селекторов.
    """
    bodies = [
        body
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
        if selector in {s.strip() for s in selectors.split(",")}
    ]
    assert bodies, f"правило {selector} не найдено в calendar.css"
    return "\n".join(bodies)


class TestTooltipNotClippedByGrid:
    """Контейнеры сетки не отрезают абсолютный тултип."""

    def test_grid_containers_have_no_overflow_hidden(self):
        """Ни обёртка сетки, ни сама сетка не объявляют overflow.

        Любое значение, кроме visible (hidden, clip, auto, scroll),
        режет тултип по краю контейнера независимо от того, с какой
        стороны ячейки он открыт.
        """
        css = _css_without_comments()
        for selector in (".calendar-grid-wrapper", ".calendar-grid"):
            body = _rule_bodies(css, selector)
            overflow = re.findall(r"overflow(?:-[xy])?\s*:\s*([\w-]+)", body)
            assert all(value == "visible" for value in overflow), (
                f"{selector} объявляет overflow {overflow} — "
                "тултип дня будет обрезан краем сетки"
            )


class TestTooltipSideRule:
    """Правило переноса тултипа налево целит в реальные колонки разметки."""

    def test_left_side_rule_covers_fri_sat_sun(self):
        """Правило `right: 100%` стоит на Пт, Сб и Вс (7n-2, 7n-1, 7n).

        Пятница обязательна: справа от неё до края сетки ~230px при
        ширине тултипа до 300px — направо он не помещается.
        """
        css = _css_without_comments()
        for selector in LEFT_SIDE_SELECTORS:
            body = _rule_bodies(css, f"{selector} .calendar-day-tooltip")
            assert re.search(
                r"right\s*:\s*100%", body
            ), f"у {selector} тултип не перенесён налево (нет right: 100%)"
            assert re.search(
                r"left\s*:\s*auto", body
            ), f"у {selector} не сброшено left: 100% базового правила"
            # Парное hover-правило снимает сдвиг анимации — без него
            # тултип «висит» смещённым на 8px.
            _rule_bodies(css, f"{selector}:hover .calendar-day-tooltip")

    def test_week_row_holds_exactly_seven_day_cells(self):
        """В каждой строке недели ровно 7 ячеек .calendar-day и ничего кроме.

        На этом стоит арифметика nth-child: 7n-2 = Пт, 7n-1 = Сб,
        7n = Вс. Лишний или пропущенный соседний элемент в строке
        молча сдвинул бы правило на другую колонку.
        """
        grid_wrapper = build_calendar_grid(
            month=9, year=2026, balances={}, transactions={}
        )
        grid = grid_wrapper.children[1]
        assert grid.className == "calendar-grid"

        week_rows = grid.children
        assert week_rows, "сетка без строк недель"
        for week_row in week_rows:
            assert week_row.className == "calendar-week-row"
            cells = week_row.children
            assert len(cells) == 7, f"в строке недели {len(cells)} ячеек, а не 7"
            for cell in cells:
                assert "calendar-day" in cell.className.split()

        # Порядок дней: первая ячейка — понедельник, 6-я и 7-я — выходные.
        first_week = week_rows[0].children
        first_date = date.fromisoformat(first_week[0].children[0].id["date"])
        assert first_date.weekday() == 0, "первая колонка сетки — не понедельник"
