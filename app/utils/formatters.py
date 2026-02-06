"""Функции форматирования для отображения данных в UI."""

from datetime import date, datetime
from decimal import Decimal

from loguru import logger

# Типографский минус (U+2212) вместо дефиса-минуса (U+002D)
MINUS_SIGN = "\u2212"

# Маппинг Bootstrap Icons на эмодзи для dropdown категорий
# Используется в transaction_modals.py и других компонентах
ICON_TO_EMOJI: dict[str, str] = {
    "bi-arrow-repeat": "🔄",
    "bi-cart": "🛒",
    "bi-car-front": "🚗",
    "bi-house": "🏠",
    "bi-phone": "📱",
    "bi-heart-pulse": "💊",
    "bi-bag": "👜",
    "bi-controller": "🎮",
    "bi-book": "📚",
    "bi-gift": "🎁",
    "bi-three-dots": "⋯",
    "bi-cash": "💵",
    "bi-briefcase": "💼",
    "bi-graph-up": "📈",
    "bi-piggy-bank": "🐷",
    "bi-tag": "🏷️",
    # Savings types
    "savings_reserve": "💼",
    "savings_contribution": "🎯",
}


def format_rub(
    amount: Decimal | float | int | None,
    show_sign: bool = False,
) -> str:
    """Форматирует сумму в рублях.

    Разделитель тысяч — пробел, символ ₽ в конце.
    Копейки .00 скрываются (15000 → "15 000 ₽", 1234.56 → "1 234.56 ₽").
    Знак минус — типографский U+2212.

    Args:
        amount: Сумма (Decimal, float, int или None)
        show_sign: Добавлять «+» для положительных сумм

    Returns:
        str: Отформатированная строка (например, "15 000 ₽")
    """
    if amount is None:
        return "0 ₽"
    try:
        value = Decimal(str(amount))
    except Exception:
        return "0 ₽"
    is_negative = value < 0
    abs_value = abs(value)
    quantized = abs_value.quantize(Decimal("0.01"))
    int_part = int(quantized)
    frac_part = quantized - int_part
    int_str = f"{int_part:,}".replace(",", " ")
    if frac_part == 0:
        number_str = int_str
    else:
        frac_str = f"{frac_part:.2f}"[1:]
        number_str = f"{int_str}{frac_str}"
    if is_negative:
        result = f"{MINUS_SIGN}{number_str} ₽"
    elif show_sign and value > 0:
        result = f"+{number_str} ₽"
    else:
        result = f"{number_str} ₽"
    return result


def format_amount(amount: Decimal) -> str:
    """Форматирует сумму для отображения (alias для format_rub).

    Args:
        amount: Сумма операции

    Returns:
        str: Отформатированная строка (например, "15 000 ₽")
    """
    return format_rub(amount)


def format_date(date_obj: date) -> str:
    """Форматирует дату для отображения.

    Args:
        date_obj: Объект даты

    Returns:
        str: Дата в формате DD.MM.YYYY
    """
    return date_obj.strftime("%d.%m.%Y")


def format_days_remaining(days: int) -> str:
    """Форматирует оставшиеся дни с правильным склонением.

    Args:
        days: Количество оставшихся дней

    Returns:
        str: Строка с правильным склонением ("1 день", "2 дня", "5 дней")
    """
    if days <= 0:
        return "Срок истёк"

    # Склонение для русского языка
    last_digit = days % 10
    last_two_digits = days % 100

    if 11 <= last_two_digits <= 14:
        return f"{days} дней"
    elif last_digit == 1:
        return f"{days} день"
    elif 2 <= last_digit <= 4:
        return f"{days} дня"
    else:
        return f"{days} дней"


def parse_date_safe(date_str: str | None) -> date | None:
    """Безопасно парсит строку даты.

    Args:
        date_str: Дата в формате YYYY-MM-DD или None

    Returns:
        date | None: Объект date или None при ошибке
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка парсинга даты '{date_str}': {e}")
        return None
