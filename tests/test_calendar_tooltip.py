"""Unit тесты для tooltip функций календаря."""

from datetime import date
from decimal import Decimal

import pytest
from dash import html

from app.components.calendar import (
    _build_tooltip_balance,
    _build_tooltip_transaction_row,
    _build_day_tooltip,
    MAX_VISIBLE_TRANSACTIONS,
)
from app.services.calendar_service import TransactionInfo


# ==================== TransactionInfo ====================


class TestTransactionInfoFields:
    """Тесты полей TransactionInfo."""

    def test_transaction_info_has_category_icon(self):
        """TransactionInfo должен иметь поле category_icon."""
        info: TransactionInfo = {
            "id": 1,
            "template_id": None,
            "transaction_type": "expense",
            "amount": "1000",
            "description": "Test",
            "date": "2026-01-15",
            "is_virtual": False,
            "is_recurring": False,
            "is_exception": False,
            "is_skipped": False,
            "category_id": 1,
            "category_name": "Продукты",
            "category_icon": "bi-cart",
        }
        assert info["category_icon"] == "bi-cart"

    def test_transaction_info_has_is_skipped(self):
        """TransactionInfo должен иметь поле is_skipped."""
        info: TransactionInfo = {
            "id": 1,
            "template_id": None,
            "transaction_type": "expense",
            "amount": "1000",
            "description": "Test",
            "date": "2026-01-15",
            "is_virtual": False,
            "is_recurring": False,
            "is_exception": False,
            "is_skipped": True,
            "category_id": 1,
            "category_name": "Продукты",
            "category_icon": "bi-cart",
        }
        assert info["is_skipped"] is True


# ==================== _build_tooltip_balance ====================


class TestBuildTooltipBalance:
    """Тесты для _build_tooltip_balance()."""

    def test_positive_balance_has_positive_class(self):
        """Положительный баланс должен иметь класс positive."""
        result = _build_tooltip_balance(Decimal("10000"))
        assert isinstance(result, html.Div)
        # Проверяем className всего контейнера
        assert "tooltip-balance" in result.className
        # Проверяем что есть positive класс у значения
        value_span = result.children[1]
        assert "positive" in value_span.className

    def test_negative_balance_has_negative_class(self):
        """Отрицательный баланс должен иметь класс negative."""
        result = _build_tooltip_balance(Decimal("-5000"))
        value_span = result.children[1]
        assert "negative" in value_span.className

    def test_zero_balance_has_positive_class(self):
        """Нулевой баланс должен иметь класс positive (>= 0)."""
        result = _build_tooltip_balance(Decimal("0"))
        value_span = result.children[1]
        assert "positive" in value_span.className

    def test_balance_formatted_with_spaces(self):
        """Баланс должен быть отформатирован с пробелами."""
        result = _build_tooltip_balance(Decimal("1234567"))
        value_span = result.children[1]
        # Проверяем что "1 234 567 ₽" в children
        assert "1 234 567" in value_span.children


# ==================== _build_tooltip_transaction_row ====================


class TestBuildTooltipTransactionRow:
    """Тесты для _build_tooltip_transaction_row()."""

    def _make_txn(self, **kwargs) -> TransactionInfo:
        """Создает транзакцию с дефолтными значениями."""
        base: TransactionInfo = {
            "id": 1,
            "template_id": None,
            "transaction_type": "expense",
            "amount": "1000",
            "description": "Test transaction",
            "date": "2026-01-15",
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

    def test_income_amount_has_plus_sign(self):
        """Доход должен отображаться с плюсом."""
        txn = self._make_txn(transaction_type="income", amount="5000")
        result = _build_tooltip_transaction_row(txn, date(2026, 1, 15))
        amount_span = result.children[2]
        assert "+5 000" in amount_span.children
        assert "income" in amount_span.className

    def test_expense_amount_has_minus_sign(self):
        """Расход должен отображаться с минусом."""
        txn = self._make_txn(transaction_type="expense", amount="3000")
        result = _build_tooltip_transaction_row(txn, date(2026, 1, 15))
        amount_span = result.children[2]
        assert "-3 000" in amount_span.children
        assert "expense" in amount_span.className

    def test_skipped_row_has_skipped_class(self):
        """Пропущенная операция должна иметь класс skipped."""
        txn = self._make_txn(is_skipped=True)
        result = _build_tooltip_transaction_row(txn, date(2026, 1, 15))
        assert "skipped" in result.className

    def test_recurring_has_icon(self):
        """Повторяющаяся операция должна иметь иконку 🔁."""
        txn = self._make_txn(is_recurring=True)
        result = _build_tooltip_transaction_row(txn, date(2026, 1, 15))
        icon_span = result.children[0]
        assert "🔁" in icon_span.children

    def test_virtual_has_icon(self):
        """Виртуальная операция должна иметь иконку 🔁."""
        txn = self._make_txn(is_virtual=True, template_id=1)
        result = _build_tooltip_transaction_row(txn, date(2026, 1, 15))
        icon_span = result.children[0]
        assert "🔁" in icon_span.children

    def test_no_category_uses_default_emoji(self):
        """Операция без категории должна использовать 📋."""
        txn = self._make_txn(category_icon=None)
        result = _build_tooltip_transaction_row(txn, date(2026, 1, 15))
        icon_span = result.children[0]
        assert "📋" in icon_span.children

    def test_category_icon_mapped_to_emoji(self):
        """Иконка категории должна маппиться в emoji."""
        txn = self._make_txn(category_icon="bi-cart")
        result = _build_tooltip_transaction_row(txn, date(2026, 1, 15))
        icon_span = result.children[0]
        # bi-cart -> 🛒
        assert "🛒" in icon_span.children

    def test_row_has_pattern_matching_id(self):
        """Строка должна иметь Pattern-Matching ID."""
        txn = self._make_txn(id=42, is_virtual=False, template_id=None)
        result = _build_tooltip_transaction_row(txn, date(2026, 1, 15))
        assert result.id["type"] == "tooltip-txn"
        assert result.id["id"] == 42
        assert result.id["is_virtual"] is False
        # template_id = -1 placeholder for None (Dash restriction)
        assert result.id["template_id"] == -1


# ==================== _build_day_tooltip ====================


class TestBuildDayTooltip:
    """Тесты для _build_day_tooltip()."""

    def _make_txn(self, **kwargs) -> TransactionInfo:
        """Создает транзакцию с дефолтными значениями."""
        base: TransactionInfo = {
            "id": 1,
            "template_id": None,
            "transaction_type": "expense",
            "amount": "1000",
            "description": "Test",
            "date": "2026-01-15",
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

    def test_empty_transactions_returns_none(self):
        """Пустой список транзакций должен вернуть None."""
        result = _build_day_tooltip(date(2026, 1, 15), Decimal("10000"), [])
        assert result is None

    def test_few_transactions_no_expand(self):
        """Меньше MAX_VISIBLE транзакций — нет кнопки expand."""
        transactions = [self._make_txn(id=i) for i in range(3)]
        result = _build_day_tooltip(date(2026, 1, 15), Decimal("10000"), transactions)
        assert result is not None
        # Проверяем что нет expand button
        has_expand_btn = any(
            hasattr(child, "className") and "tooltip-expand-btn" in str(child.className)
            for child in result.children
            if hasattr(child, "className")
        )
        assert not has_expand_btn

    def test_many_transactions_has_expand(self):
        """Больше MAX_VISIBLE транзакций — есть кнопка expand."""
        transactions = [self._make_txn(id=i) for i in range(MAX_VISIBLE_TRANSACTIONS + 3)]
        result = _build_day_tooltip(date(2026, 1, 15), Decimal("10000"), transactions)
        assert result is not None
        # Проверяем наличие expand button
        has_expand_btn = any(
            hasattr(child, "className") and "tooltip-expand-btn" in str(child.className)
            for child in result.children
            if hasattr(child, "className")
        )
        assert has_expand_btn

    def test_has_aria_attributes(self):
        """Tooltip должен иметь ARIA атрибуты."""
        transactions = [self._make_txn()]
        result = _build_day_tooltip(date(2026, 1, 15), Decimal("10000"), transactions)
        assert result.role == "tooltip"
        # aria-label через **kwargs

    def test_tooltip_has_balance_header(self):
        """Tooltip должен иметь header с балансом."""
        transactions = [self._make_txn()]
        result = _build_day_tooltip(date(2026, 1, 15), Decimal("5000"), transactions)
        # Первый или второй элемент (после checkbox если есть) — баланс
        balance_found = any(
            hasattr(child, "className") and "tooltip-balance" in str(child.className)
            for child in result.children
            if hasattr(child, "className")
        )
        assert balance_found

    def test_hidden_txns_container_exists_when_many(self):
        """При большом количестве транзакций есть контейнер hidden."""
        transactions = [self._make_txn(id=i) for i in range(MAX_VISIBLE_TRANSACTIONS + 2)]
        result = _build_day_tooltip(date(2026, 1, 15), Decimal("10000"), transactions)
        # Проверяем наличие hidden container
        has_hidden = any(
            hasattr(child, "className") and "tooltip-hidden-txns" in str(child.className)
            for child in result.children
            if hasattr(child, "className")
        )
        assert has_hidden
