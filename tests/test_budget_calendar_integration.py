"""Интеграционные тесты: взаимодействие budget reservation с calendar."""

from datetime import date
from decimal import Decimal

import pytest

from app.models.database import Goal, GoalStatus
from app.services.budget_reservation_service import BudgetReservationService
from app.services.calendar_service import CalendarService
from app.services.goal_service import GoalService


class TestContributionAffectsCalendar:
    """E2E: взнос в день резерва -> изменение резерва в календаре."""

    def test_contribution_before_reserve_reduces_reserve_in_calendar(
        self, db_session, test_user
    ):
        """Взнос до даты резерва -> резерв уменьшается в календаре.

        Сценарий:
        1. User с budget=30000, mode=fixed_date, day=25
        2. Сегодня = 10 числа (резерв 25го ещё не прошёл)
        3. Создаём взнос 10000 на дату < 25
        4. Проверяем что CalendarService показывает резерв = 20000
        """
        # Arrange
        today = date.today()
        reserve_day = 25

        # Гарантируем что сегодня < reserve_day (если нет — skip)
        if today.day >= reserve_day:
            pytest.skip("Test requires today < reserve_day=25")

        test_user.monthly_savings_budget = Decimal("30000")
        test_user.reservation_mode = "fixed_date"
        test_user.reservation_day = reserve_day
        db_session.commit()

        # Создаём цель для взносов
        goal = Goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("100000"),
            current_amount=Decimal("0"),
            target_date=date(2027, 12, 31),
            status=GoalStatus.ACTIVE,
            priority=1,
        )
        db_session.add(goal)
        db_session.commit()

        reservation_service = BudgetReservationService(db_session)
        goal_service = GoalService(db_session)
        calendar_service = CalendarService(db_session)

        # Создаём шаблон резерва
        reservation_service.set_mode(
            user_id=test_user.id,
            mode="fixed_date",
            day_of_month=reserve_day,
        )
        db_session.commit()

        # Act: делаем взнос до даты резерва
        contribution_date = date(today.year, today.month, today.day)
        goal_service.add_contribution(
            goal_id=goal.id,
            amount=Decimal("10000"),
            contribution_date=contribution_date,
            description="Test contribution",
        )
        db_session.commit()

        # Assert: проверяем что календарь показывает уменьшенный резерв
        reserve_date = date(today.year, today.month, reserve_day)
        start_date = date(today.year, today.month, 1)
        end_date = date(today.year, today.month, 28)

        transactions = calendar_service.get_all_transactions_for_period(
            user_id=test_user.id,
            start_date=start_date,
            end_date=end_date,
            include_recurring=True,
        )

        # Находим резерв на дату reserve_day
        reserve_txs = [
            tx
            for tx in transactions.get(reserve_date, [])
            if "Резервирование" in tx["description"]
        ]

        assert len(reserve_txs) == 1
        # amount может быть строкой или Decimal — конвертируем для сравнения
        assert Decimal(str(reserve_txs[0]["amount"])) == Decimal(
            "20000"
        )  # 30000 - 10000

    def test_contribution_after_mode_switch_updates_reserve(
        self, db_session, test_user
    ):
        """E2E: fixed -> from_balance -> fixed (тот же день) -> взнос сохраняется.

        Сценарий:
        1. mode=fixed_date, day=15, budget=30000
        2. Взнос 10000 (резерв -> 20000)
        3. Переключаем на from_balance
        4. Переключаем обратно на fixed_date, day=15
        5. Резерв должен остаться 20000 (exception сохранён)
        """
        today = date.today()
        reserve_day = 15

        if today.day >= reserve_day:
            pytest.skip("Test requires today < reserve_day=15")

        test_user.monthly_savings_budget = Decimal("30000")
        db_session.commit()

        goal = Goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("100000"),
            current_amount=Decimal("0"),
            target_date=date(2027, 12, 31),
            status=GoalStatus.ACTIVE,
            priority=1,
        )
        db_session.add(goal)
        db_session.commit()

        reservation_service = BudgetReservationService(db_session)
        goal_service = GoalService(db_session)
        calendar_service = CalendarService(db_session)

        # Step 1: fixed_date mode
        reservation_service.set_mode(
            user_id=test_user.id,
            mode="fixed_date",
            day_of_month=reserve_day,
        )
        db_session.commit()

        # Step 2: делаем взнос
        goal_service.add_contribution(
            goal_id=goal.id,
            amount=Decimal("10000"),
            contribution_date=date(today.year, today.month, today.day),
        )
        db_session.commit()

        # Step 3: переключаем на from_balance
        reservation_service.set_mode(
            user_id=test_user.id,
            mode="from_balance",
        )
        db_session.commit()

        # Step 4: переключаем обратно на fixed_date с тем же днём
        reservation_service.set_mode(
            user_id=test_user.id,
            mode="fixed_date",
            day_of_month=reserve_day,
        )
        db_session.commit()

        # Assert: резерв должен быть 20000 (exception сохранился)
        reserve_date = date(today.year, today.month, reserve_day)
        transactions = calendar_service.get_all_transactions_for_period(
            user_id=test_user.id,
            start_date=date(today.year, today.month, 1),
            end_date=date(today.year, today.month, 28),
            include_recurring=True,
        )

        reserve_txs = [
            tx
            for tx in transactions.get(reserve_date, [])
            if "Резервирование" in tx["description"]
        ]

        assert len(reserve_txs) == 1
        # amount может быть строкой или Decimal — конвертируем для сравнения
        assert Decimal(str(reserve_txs[0]["amount"])) == Decimal("20000")


class TestDeleteContributionRecalculatesReserve:
    """E2E: удаление взноса -> резерв увеличивается."""

    def test_delete_contribution_restores_reserve(self, db_session, test_user):
        """Удаление взноса -> резерв возвращается к полному бюджету.

        Сценарий:
        1. budget=30000, взнос 10000 (резерв -> 20000)
        2. Удаляем взнос
        3. Резерв должен стать 30000 (exception удалён)
        """
        today = date.today()
        reserve_day = 20

        if today.day >= reserve_day:
            pytest.skip("Test requires today < reserve_day=20")

        test_user.monthly_savings_budget = Decimal("30000")
        db_session.commit()

        goal = Goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("100000"),
            current_amount=Decimal("0"),
            target_date=date(2027, 12, 31),
            status=GoalStatus.ACTIVE,
            priority=1,
        )
        db_session.add(goal)
        db_session.commit()

        reservation_service = BudgetReservationService(db_session)
        goal_service = GoalService(db_session)
        calendar_service = CalendarService(db_session)

        # Setup: fixed_date + взнос
        reservation_service.set_mode(
            user_id=test_user.id,
            mode="fixed_date",
            day_of_month=reserve_day,
        )
        db_session.commit()

        contribution = goal_service.add_contribution(
            goal_id=goal.id,
            amount=Decimal("10000"),
            contribution_date=date(today.year, today.month, today.day),
        )
        db_session.commit()

        # Act: удаляем взнос
        goal_service.delete_contribution(contribution.id)
        db_session.commit()

        # Assert: резерв = полный бюджет
        reserve_date = date(today.year, today.month, reserve_day)
        transactions = calendar_service.get_all_transactions_for_period(
            user_id=test_user.id,
            start_date=date(today.year, today.month, 1),
            end_date=date(today.year, today.month, 28),
            include_recurring=True,
        )

        reserve_txs = [
            tx
            for tx in transactions.get(reserve_date, [])
            if "Резервирование" in tx["description"]
        ]

        assert len(reserve_txs) == 1
        # После удаления всех взносов резерв = budget (exception удалён)
        # amount может быть строкой или Decimal — конвертируем для сравнения
        assert Decimal(str(reserve_txs[0]["amount"])) == Decimal("30000")
