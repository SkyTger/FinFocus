"""Сервис расчёта безопасных дат для отложенных покупок."""

import calendar
from datetime import date
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.schema.wishlist import HoverBalances, SafeDateInfo
from app.services.calendar_service import CalendarService
from app.services.cushion_service import CushionService
from app.utils.formatters import format_amount


class PurchaseRecommendationService:
    """Рассчитывает безопасные даты покупок на основе кассового прогноза.

    Использует CalendarService для прогноза балансов и CushionService
    для порога подушки безопасности.
    """

    def __init__(self, session: Session):
        """Инициализирует сервис.

        Args:
            session: SQLAlchemy сессия для работы с БД.
        """
        self.session = session
        self._calendar_service = CalendarService(session)
        self._cushion_service = CushionService(session)

    def get_safe_dates_map(
        self,
        user_id: int,
        amount: Decimal,
        year: int,
        month: int,
    ) -> dict[str, SafeDateInfo]:
        """Рассчитывает карту безопасности дат для покупки.

        Для каждого дня-кандидата (>= today) вычисляет, можно ли совершить
        покупку на сумму amount, не уходя в минус и не опуская баланс
        ниже порога подушки безопасности до конца месяца.

        Args:
            user_id: ID пользователя.
            amount: Сумма покупки.
            year: Год.
            month: Месяц.

        Returns:
            dict[str, SafeDateInfo]: ISO-дата → информация о безопасности.
                Прошлые дни не включаются.
        """
        today = date.today()
        last_day = calendar.monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, last_day)

        # Получаем балансы на каждый день
        daily_balances = self._calendar_service.calculate_daily_balances(
            user_id, start, end
        )

        # Получаем порог подушки
        try:
            cushion = self._cushion_service.get_settings(user_id)
            threshold = cushion["threshold_amount"]
        except Exception:
            threshold = Decimal("0")

        result: dict[str, SafeDateInfo] = {}

        for day_num in range(1, last_day + 1):
            candidate = date(year, month, day_num)

            # Пропускаем прошлые дни
            if candidate < today:
                continue

            reasons: list[str] = []

            # Вычисляем минимальный баланс от дня покупки до конца месяца
            min_balance_after = None
            for future_day in range(day_num, last_day + 1):
                future_date = date(year, month, future_day)
                base_balance = daily_balances.get(future_date, Decimal("0"))
                balance_after = base_balance - amount

                if min_balance_after is None or balance_after < min_balance_after:
                    min_balance_after = balance_after

            if min_balance_after is None:
                min_balance_after = Decimal("0") - amount

            # Проверка: отрицательный баланс
            if min_balance_after < Decimal("0"):
                reasons.append("negative_balance")

            # Проверка: ниже порога подушки
            if threshold > Decimal("0") and min_balance_after < threshold:
                reasons.append("cushion")

            safe = len(reasons) == 0

            result[candidate.isoformat()] = SafeDateInfo(
                safe=safe,
                reasons=reasons,
            )

        logger.debug(
            f"Safe dates map for user {user_id}, amount={amount}, "
            f"{year}-{month:02d}: "
            f"{sum(1 for v in result.values() if v['safe'])}/{len(result)} safe"
        )

        return result

    def precalculate_hover_data(
        self,
        user_id: int,
        amount: Decimal,
        year: int,
        month: int,
    ) -> HoverBalances:
        """Предрассчитывает балансы для JS hover в календаре.

        Args:
            user_id: ID пользователя.
            amount: Сумма покупки.
            year: Год.
            month: Месяц.

        Returns:
            HoverBalances: Базовые балансы и балансы по кандидатам.
        """
        today = date.today()
        last_day = calendar.monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, last_day)

        daily_balances = self._calendar_service.calculate_daily_balances(
            user_id, start, end
        )

        # base_balances: все дни месяца
        base_balances: dict[str, str] = {}
        for day_num in range(1, last_day + 1):
            d = date(year, month, day_num)
            balance = daily_balances.get(d, Decimal("0"))
            base_balances[d.isoformat()] = format_amount(balance)

        # by_candidate: для каждого candidate >= today
        by_candidate: dict[str, dict[str, str]] = {}
        for day_num in range(1, last_day + 1):
            candidate = date(year, month, day_num)
            if candidate < today:
                continue

            adjusted: dict[str, str] = {}
            for i in range(1, last_day + 1):
                d = date(year, month, i)
                base = daily_balances.get(d, Decimal("0"))
                # После дня покупки баланс уменьшается на amount
                if d >= candidate:
                    adjusted[d.isoformat()] = format_amount(base - amount)
                else:
                    adjusted[d.isoformat()] = format_amount(base)

            by_candidate[candidate.isoformat()] = adjusted

        return HoverBalances(
            base_balances=base_balances,
            by_candidate=by_candidate,
        )
