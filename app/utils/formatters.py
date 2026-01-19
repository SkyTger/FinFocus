"""Функции форматирования для отображения данных в UI."""

from datetime import date, datetime
from decimal import Decimal

from loguru import logger


def format_amount(amount: Decimal) -> str:
    """Форматирует сумму для отображения.

    Args:
        amount: Сумма операции

    Returns:
        str: Отформатированная строка (например, "15 000.00 ₽")
    """
    return f"{amount:,.2f} ₽".replace(",", " ")


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
