"""Тесты отметки разовых трат в календаре и списке операций (протокол 0034).

Разовый расход — expense вне серии (не шаблон, не виртуальный экземпляр,
не исключение серии). Отмечается одним цветом (--color-one-off): точка
дня и полоска строки подсказки в календаре, флажок в списке операций.
БД не используется: функции принимают TransactionInfo / Transaction в
памяти; CSS проверяется как текст (якоря, как test_calendar_tooltip_visual).
"""

import pathlib
import re
from datetime import date, timedelta
from decimal import Decimal

import pytest
from dash import html

from app.components.calendar import _build_tooltip_transaction_row, build_day_cell
from app.components.transactions import _build_transactions_table
from app.models.database import Transaction, TransactionType

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "app" / "assets"


def iter_tree(component):
    """Рекурсивный обход дерева Dash-компонентов."""
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        yield from iter_tree(child)


def class_names(component) -> list[str]:
    """className всех узлов дерева."""
    return [
        str(getattr(node, "className", None))
        for node in iter_tree(component)
        if getattr(node, "className", None)
    ]


def make_info(**kwargs) -> dict:
    """TransactionInfo со значениями по умолчанию — разовый расход."""
    base = {
        "id": 1,
        "template_id": None,
        "transaction_type": "expense",
        "amount": "1000",
        "description": "Ремонт",
        "date": date.today().isoformat(),
        "is_virtual": False,
        "is_recurring": False,
        "is_exception": False,
        "is_skipped": False,
        "category_id": None,
        "category_name": None,
        "category_icon": None,
    }
    base.update(kwargs)
    return base


SERIES_INSTANCE = {"is_virtual": True, "is_recurring": True, "id": None}
SERIES_EXCEPTION = {"is_recurring": True, "is_exception": True, "template_id": 7}


def day_dots(transactions) -> list[str]:
    """Классы точек ячейки дня."""
    cell = build_day_cell(date.today(), Decimal("10000"), transactions)
    return [name for name in class_names(cell) if name.startswith("txn-dot")]


def css_text(name: str) -> str:
    """Текст CSS-файла без комментариев."""
    css = (ASSETS / name).read_text(encoding="utf-8")
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def rule_body(css: str, selector: str) -> str:
    """Тело правила для точного селектора."""
    bodies = [
        body
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
        if selector in {part.strip() for part in selectors.split(",")}
    ]
    assert bodies, f"правило {selector} не найдено"
    return "\n".join(bodies)


class TestCalendarDots:
    """Точки дня календаря."""

    def test_only_one_off_gives_one_off_dot_without_expense(self):
        """День только с разовым — точка one-off, без expense."""
        assert day_dots([make_info()]) == ["txn-dot one-off"]

    @pytest.mark.parametrize("series", [SERIES_INSTANCE, SERIES_EXCEPTION])
    def test_series_expense_gives_expense_dot_without_one_off(self, series):
        """Расход серии (экземпляр или исключение) — expense, без one-off."""
        dots = day_dots([make_info(**series)])

        assert "txn-dot expense" in dots
        assert "txn-dot one-off" not in dots

    def test_both_kinds_give_both_dots(self):
        """Разовый и расход серии в одном дне — обе точки."""
        dots = day_dots([make_info(), make_info(id=2, **SERIES_EXCEPTION)])

        assert "txn-dot expense" in dots and "txn-dot one-off" in dots

    @pytest.mark.parametrize(
        "txn_type", ["savings_reserve", "savings_contribution", "adjustment"]
    )
    def test_service_operations_not_one_off(self, txn_type):
        """Служебные операции вне серии — не разовые."""
        assert "txn-dot one-off" not in day_dots([make_info(transaction_type=txn_type)])

    def test_one_off_dot_title(self):
        """Подсказка точки — «Разовый расход»."""
        cell = build_day_cell(date.today(), Decimal("10000"), [make_info()])
        [dot] = [
            node
            for node in iter_tree(cell)
            if getattr(node, "className", None) == "txn-dot one-off"
        ]

        assert dot.title == "Разовый расход"


class TestTooltipRow:
    """Строка операции в подсказке дня календаря."""

    def test_one_off_row_marked(self):
        """Строка разового расхода несёт класс one-off."""
        row = _build_tooltip_transaction_row(make_info(), date.today())

        assert "one-off" in row.className.split()

    @pytest.mark.parametrize(
        "kwargs",
        [
            SERIES_INSTANCE,
            SERIES_EXCEPTION,
            {"transaction_type": "income"},
            {"transaction_type": "savings_reserve"},
            {"transaction_type": "adjustment", "amount": "-500"},
        ],
    )
    def test_other_rows_not_marked(self, kwargs):
        """Серии, доход и служебные — без отметки разовых."""
        row = _build_tooltip_transaction_row(make_info(**kwargs), date.today())

        assert "one-off" not in row.className.split()


def make_tx(
    tx_type: TransactionType = TransactionType.EXPENSE,
    *,
    is_recurring: bool = False,
    parent_id: int | None = None,
) -> Transaction:
    """Транзакция в памяти (без БД), дата — относительная."""
    return Transaction(
        id=1,
        user_id=1,
        amount=Decimal("1000"),
        transaction_type=tx_type,
        transaction_date=date.today() - timedelta(days=2),
        description="Операция",
        is_recurring=is_recurring,
        recurring_parent_id=parent_id,
    )


def row_icons(tx: Transaction) -> list:
    """Иконки (html.I) строки списка операций."""
    _, tbody = _build_transactions_table([tx])
    return [node for node in iter_tree(tbody) if isinstance(node, html.I)]


def flag_icons(tx: Transaction) -> list:
    """Флажки разовой траты в строке."""
    return [icon for icon in row_icons(tx) if "bi-flag-fill" in icon.className]


class TestTransactionsListIcon:
    """Значок разовой траты в списке операций."""

    def test_one_off_expense_has_flag(self):
        """Разовый расход — флажок цвета разовых с подсказкой."""
        [flag] = flag_icons(make_tx())

        assert "tx-one-off-icon" in flag.className
        assert flag.title == "Разовая трата"
        assert not any(
            "bi-arrow-repeat" in icon.className for icon in row_icons(make_tx())
        )

    def test_series_template_has_repeat_not_flag(self):
        """Шаблон серии — значок повтора, без флажка."""
        tx = make_tx(is_recurring=True)

        assert flag_icons(tx) == []
        assert any("bi-arrow-repeat" in icon.className for icon in row_icons(tx))

    def test_series_exception_has_no_flag(self):
        """Исключение серии — не разовое."""
        assert flag_icons(make_tx(parent_id=5)) == []

    @pytest.mark.parametrize(
        "tx_type",
        [
            TransactionType.SAVINGS_RESERVE,
            TransactionType.SAVINGS_CONTRIBUTION,
            TransactionType.ADJUSTMENT,
            TransactionType.INCOME,
        ],
    )
    def test_non_expense_has_no_flag(self, tx_type):
        """Служебные, корректировка и доход — без флажка."""
        assert flag_icons(make_tx(tx_type)) == []


class TestOneOffCssAnchors:
    """Якоря CSS: один токен цвета разовых во всех местах."""

    def test_calendar_dot_uses_token(self):
        """.txn-dot.one-off красится токеном --color-one-off."""
        body = rule_body(css_text("calendar.css"), ".txn-dot.one-off")

        assert "var(--color-one-off)" in body

    def test_tooltip_row_uses_token(self):
        """Полоска строки подсказки — токен разовых."""
        body = rule_body(css_text("calendar.css"), ".tooltip-txn-row.one-off")

        assert "var(--color-one-off)" in body

    def test_list_icon_uses_token(self):
        """Флажок в списке — класс с токеном, не инлайн-цвет."""
        body = rule_body(css_text("transactions.css"), ".tx-one-off-icon")

        assert "var(--color-one-off)" in body
