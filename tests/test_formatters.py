"""Тесты для format_rub() и format_amount()."""

from decimal import Decimal

from app.utils.formatters import format_amount, format_rub


class TestFormatRub:
    """Тесты глобального форматтера format_rub()."""

    def test_format_rub_positive_integer(self) -> None:
        """Целое положительное число без копеек."""
        assert format_rub(15000) == "15 000 ₽"

    def test_format_rub_positive_decimal(self) -> None:
        """Дробное число с копейками."""
        assert format_rub(1234.56) == "1 234.56 ₽"

    def test_format_rub_negative(self) -> None:
        """Отрицательное число с типографским минусом U+2212."""
        result = format_rub(-1200)
        assert result == "\u22121 200 ₽"

    def test_format_rub_zero(self) -> None:
        """Ноль без знака."""
        assert format_rub(0) == "0 ₽"

    def test_format_rub_none(self) -> None:
        """None возвращает '0 ₽'."""
        assert format_rub(None) == "0 ₽"

    def test_format_rub_show_sign_positive(self) -> None:
        """Положительное с show_sign добавляет '+'."""
        assert format_rub(500, show_sign=True) == "+500 ₽"

    def test_format_rub_show_sign_negative(self) -> None:
        """Отрицательное с show_sign использует типографский минус."""
        assert format_rub(-500, show_sign=True) == "\u2212500 ₽"

    def test_format_rub_show_sign_zero(self) -> None:
        """Ноль с show_sign без знака."""
        assert format_rub(0, show_sign=True) == "0 ₽"

    def test_format_rub_decimal_type(self) -> None:
        """Decimal тип корректно обрабатывается."""
        assert format_rub(Decimal("15000.50")) == "15 000.50 ₽"

    def test_format_amount_alias(self) -> None:
        """format_amount() является alias для format_rub()."""
        assert format_amount(Decimal("1000")) == format_rub(Decimal("1000"))
