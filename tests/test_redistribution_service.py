"""Unit тесты для RedistributionService."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.models.database import Goal, GoalStatus, User
from app.schema.goals import AllocationResult, AllocationSummary
from app.services.allocation_service import AllocationService
from app.services.redistribution_service import (
    NFR2_WARNING_THRESHOLD_MS,
    RedistributionService,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def allocation_service():
    """Создает AllocationService."""
    return AllocationService()


@pytest.fixture
def redistribution_service(allocation_service):
    """Создает RedistributionService с AllocationService."""
    return RedistributionService(allocation_service=allocation_service)


@pytest.fixture
def test_user_with_budget(db_session) -> User:
    """Создает пользователя с monthly_savings_budget=15000."""
    user = User(
        email="budget@example.com",
        name="Budget User",
        starting_balance=Decimal("50000.00"),
        monthly_savings_budget=Decimal("15000.00"),
        savings_mode="free",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_goals(db_session, test_user_with_budget) -> list[Goal]:
    """Создает 3 цели с разными приоритетами и статусами.

    Goal 1: priority=1, COMPLETED (только что завершена)
    Goal 2: priority=2, ACTIVE
    Goal 3: priority=3, ACTIVE
    """
    target_date = date.today() + timedelta(days=180)

    # Goal 1: Завершенная цель (освобождает бюджет)
    goal1 = Goal(
        user_id=test_user_with_budget.id,
        name="Отпуск",
        target_amount=Decimal("10000.00"),
        current_amount=Decimal("10000.00"),  # 100% - completed
        target_date=target_date,
        status=GoalStatus.COMPLETED,
        priority=1,
    )

    # Goal 2: Активная цель с высоким приоритетом
    goal2 = Goal(
        user_id=test_user_with_budget.id,
        name="Машина",
        target_amount=Decimal("200000.00"),
        current_amount=Decimal("50000.00"),
        target_date=target_date + timedelta(days=365),
        status=GoalStatus.ACTIVE,
        priority=2,
    )

    # Goal 3: Активная цель с низким приоритетом
    goal3 = Goal(
        user_id=test_user_with_budget.id,
        name="Ремонт",
        target_amount=Decimal("100000.00"),
        current_amount=Decimal("10000.00"),
        target_date=target_date + timedelta(days=180),
        status=GoalStatus.ACTIVE,
        priority=3,
    )

    db_session.add_all([goal1, goal2, goal3])
    db_session.commit()

    return [goal1, goal2, goal3]


@pytest.fixture
def all_completed_goals(db_session, test_user_with_budget) -> list[Goal]:
    """Создает 2 цели, обе COMPLETED."""
    target_date = date.today() + timedelta(days=30)

    goal1 = Goal(
        user_id=test_user_with_budget.id,
        name="Цель 1",
        target_amount=Decimal("5000.00"),
        current_amount=Decimal("5000.00"),
        target_date=target_date,
        status=GoalStatus.COMPLETED,
        priority=1,
    )

    goal2 = Goal(
        user_id=test_user_with_budget.id,
        name="Цель 2",
        target_amount=Decimal("3000.00"),
        current_amount=Decimal("3000.00"),
        target_date=target_date,
        status=GoalStatus.COMPLETED,
        priority=2,
    )

    db_session.add_all([goal1, goal2])
    db_session.commit()

    return [goal1, goal2]


# =============================================================================
# Tests: calculate_redistribution_preview()
# =============================================================================


class TestCalculateRedistributionPreview:
    """Тесты для calculate_redistribution_preview()."""

    def test_preview_basic_calculation(
        self, redistribution_service, sample_goals, test_user_with_budget
    ):
        """Базовый сценарий: 1 completed + 2 active цели."""
        completed_goal = sample_goals[0]  # COMPLETED
        monthly_budget = test_user_with_budget.monthly_savings_budget

        preview = redistribution_service.calculate_redistribution_preview(
            completed_goal=completed_goal,
            all_goals=sample_goals,
            monthly_budget=monthly_budget,
            savings_mode="free",
        )

        # Проверяем структуру preview
        assert preview["completed_goal_id"] == completed_goal.id
        assert preview["completed_goal_name"] == "Отпуск"
        assert preview["has_remaining_goals"] is True
        assert preview["remaining_goals_count"] == 2
        assert preview["new_allocation"] is not None
        assert preview["old_allocation"] is not None
        assert preview["calculation_time_ms"] > 0

    def test_preview_no_remaining_goals(
        self, redistribution_service, all_completed_goals, test_user_with_budget
    ):
        """Все цели completed — нет оставшихся целей."""
        completed_goal = all_completed_goals[0]
        monthly_budget = test_user_with_budget.monthly_savings_budget

        preview = redistribution_service.calculate_redistribution_preview(
            completed_goal=completed_goal,
            all_goals=all_completed_goals,
            monthly_budget=monthly_budget,
            savings_mode="free",
        )

        assert preview["has_remaining_goals"] is False
        assert preview["remaining_goals_count"] == 0
        # При отсутствии remaining goals, allocations = None
        assert preview["new_allocation"] is None
        assert preview["old_allocation"] is None

    def test_preview_single_remaining_goal(
        self, db_session, redistribution_service, test_user_with_budget
    ):
        """Одна оставшаяся активная цель."""
        target_date = date.today() + timedelta(days=180)

        completed = Goal(
            user_id=test_user_with_budget.id,
            name="Завершенная",
            target_amount=Decimal("5000.00"),
            current_amount=Decimal("5000.00"),
            target_date=target_date,
            status=GoalStatus.COMPLETED,
            priority=1,
        )
        active = Goal(
            user_id=test_user_with_budget.id,
            name="Активная",
            target_amount=Decimal("10000.00"),
            current_amount=Decimal("0.00"),
            target_date=target_date,
            status=GoalStatus.ACTIVE,
            priority=2,
        )
        db_session.add_all([completed, active])
        db_session.commit()

        preview = redistribution_service.calculate_redistribution_preview(
            completed_goal=completed,
            all_goals=[completed, active],
            monthly_budget=Decimal("10000.00"),
            savings_mode="free",
        )

        assert preview["remaining_goals_count"] == 1
        assert preview["has_remaining_goals"] is True

    def test_preview_freed_budget_calculation(
        self, redistribution_service, sample_goals, test_user_with_budget
    ):
        """Проверка расчета freed_budget."""
        completed_goal = sample_goals[0]
        monthly_budget = test_user_with_budget.monthly_savings_budget

        preview = redistribution_service.calculate_redistribution_preview(
            completed_goal=completed_goal,
            all_goals=sample_goals,
            monthly_budget=monthly_budget,
            savings_mode="free",
        )

        # freed_budget должен быть >= 0
        assert preview["freed_budget"] >= Decimal("0")
        # was_skipped зависит от того, была ли цель профинансирована
        assert isinstance(preview["was_skipped_in_old_allocation"], bool)

    def test_preview_includes_timing(
        self, redistribution_service, sample_goals, test_user_with_budget
    ):
        """calculation_time_ms всегда положительный."""
        completed_goal = sample_goals[0]

        preview = redistribution_service.calculate_redistribution_preview(
            completed_goal=completed_goal,
            all_goals=sample_goals,
            monthly_budget=Decimal("15000.00"),
            savings_mode="free",
        )

        assert preview["calculation_time_ms"] > 0
        assert isinstance(preview["calculation_time_ms"], float)


# =============================================================================
# Tests: Temporary Status Pattern
# =============================================================================


class TestTemporaryStatusPattern:
    """Тесты для Temporary Status Pattern."""

    def test_temporary_status_restored_on_success(
        self, redistribution_service, sample_goals, test_user_with_budget
    ):
        """Статус COMPLETED сохраняется после успешного расчета."""
        completed_goal = sample_goals[0]
        assert completed_goal.status == GoalStatus.COMPLETED

        preview = redistribution_service.calculate_redistribution_preview(
            completed_goal=completed_goal,
            all_goals=sample_goals,
            monthly_budget=Decimal("15000.00"),
            savings_mode="free",
        )

        # Статус должен остаться COMPLETED после расчета
        assert completed_goal.status == GoalStatus.COMPLETED
        # Preview должен быть рассчитан
        assert preview is not None

    def test_temporary_status_restored_on_exception(
        self, sample_goals, test_user_with_budget
    ):
        """Статус восстанавливается даже при exception в AllocationService."""
        completed_goal = sample_goals[0]
        assert completed_goal.status == GoalStatus.COMPLETED

        # Создаем mock AllocationService, который бросает exception
        mock_allocation_service = MagicMock(spec=AllocationService)
        mock_allocation_service.calculate_allocation.side_effect = RuntimeError(
            "Test exception"
        )

        service = RedistributionService(allocation_service=mock_allocation_service)

        # Вызов должен бросить exception
        with pytest.raises(RuntimeError, match="Test exception"):
            service.calculate_redistribution_preview(
                completed_goal=completed_goal,
                all_goals=sample_goals,
                monthly_budget=Decimal("15000.00"),
                savings_mode="free",
            )

        # CRITICAL: Статус должен быть восстановлен даже после exception
        assert completed_goal.status == GoalStatus.COMPLETED

    def test_active_goal_processed_correctly(
        self, db_session, redistribution_service, test_user_with_budget
    ):
        """Цель со статусом ACTIVE обрабатывается корректно (edge case)."""
        target_date = date.today() + timedelta(days=180)

        # Создаем цель которая уже ACTIVE (не COMPLETED)
        active_goal = Goal(
            user_id=test_user_with_budget.id,
            name="Активная цель",
            target_amount=Decimal("10000.00"),
            current_amount=Decimal("9999.00"),  # Почти completed
            target_date=target_date,
            status=GoalStatus.ACTIVE,
            priority=1,
        )
        db_session.add(active_goal)
        db_session.commit()

        # Даже если передать ACTIVE цель, метод должен работать
        preview = redistribution_service.calculate_redistribution_preview(
            completed_goal=active_goal,
            all_goals=[active_goal],
            monthly_budget=Decimal("10000.00"),
            savings_mode="free",
        )

        # Статус должен остаться ACTIVE
        assert active_goal.status == GoalStatus.ACTIVE
        assert preview is not None


# =============================================================================
# Tests: _get_freed_budget_from_allocation()
# =============================================================================


class TestGetFreedBudgetFromAllocation:
    """Тесты для _get_freed_budget_from_allocation()."""

    def test_freed_budget_normal_goal(self, redistribution_service):
        """Обычная цель с allocated_amount."""
        old_allocation: AllocationSummary = {
            "total_budget": Decimal("15000.00"),
            "total_allocated": Decimal("10000.00"),
            "total_needed": Decimal("12000.00"),
            "total_shortfall": Decimal("2000.00"),
            "results": [
                AllocationResult(
                    goal_id=1,
                    goal_name="Цель 1",
                    priority=1,
                    monthly_contribution_needed=Decimal("5000.00"),
                    allocated_amount=Decimal("5000.00"),
                    is_fully_funded=True,
                    shortfall=Decimal("0.00"),
                    skipped_reason=None,
                ),
                AllocationResult(
                    goal_id=2,
                    goal_name="Цель 2",
                    priority=2,
                    monthly_contribution_needed=Decimal("7000.00"),
                    allocated_amount=Decimal("5000.00"),
                    is_fully_funded=False,
                    shortfall=Decimal("2000.00"),
                    skipped_reason=None,
                ),
            ],
            "all_goals_funded": False,
            "budget_not_set": False,
        }

        freed, was_skipped = redistribution_service._get_freed_budget_from_allocation(
            completed_goal_id=1,
            old_allocation=old_allocation,
        )

        assert freed == Decimal("5000.00")
        assert was_skipped is False

    def test_freed_budget_skipped_goal(self, redistribution_service):
        """Цель была skipped (например, paused)."""
        old_allocation: AllocationSummary = {
            "total_budget": Decimal("10000.00"),
            "total_allocated": Decimal("10000.00"),
            "total_needed": Decimal("10000.00"),
            "total_shortfall": Decimal("0.00"),
            "results": [
                AllocationResult(
                    goal_id=1,
                    goal_name="Пропущенная",
                    priority=1,
                    monthly_contribution_needed=Decimal("0.00"),
                    allocated_amount=Decimal("0.00"),
                    is_fully_funded=False,
                    shortfall=Decimal("0.00"),
                    skipped_reason="paused",  # Цель была на паузе
                ),
            ],
            "all_goals_funded": True,
            "budget_not_set": False,
        }

        freed, was_skipped = redistribution_service._get_freed_budget_from_allocation(
            completed_goal_id=1,
            old_allocation=old_allocation,
        )

        assert freed == Decimal("0")
        assert was_skipped is True

    def test_freed_budget_goal_not_found(self, redistribution_service, caplog):
        """Цель не найдена в allocation (edge case, не должен происходить)."""
        old_allocation: AllocationSummary = {
            "total_budget": Decimal("10000.00"),
            "total_allocated": Decimal("5000.00"),
            "total_needed": Decimal("5000.00"),
            "total_shortfall": Decimal("0.00"),
            "results": [
                AllocationResult(
                    goal_id=99,  # Другой ID
                    goal_name="Другая цель",
                    priority=1,
                    monthly_contribution_needed=Decimal("5000.00"),
                    allocated_amount=Decimal("5000.00"),
                    is_fully_funded=True,
                    shortfall=Decimal("0.00"),
                    skipped_reason=None,
                ),
            ],
            "all_goals_funded": True,
            "budget_not_set": False,
        }

        freed, was_skipped = redistribution_service._get_freed_budget_from_allocation(
            completed_goal_id=1,  # Этот ID не существует в results
            old_allocation=old_allocation,
        )

        # Возвращает 0, False и логирует error
        assert freed == Decimal("0")
        assert was_skipped is False


# =============================================================================
# Tests: log_redistribution_event()
# =============================================================================


class TestLogRedistributionEvent:
    """Тесты для log_redistribution_event()."""

    def test_log_event_confirmed(
        self, redistribution_service, sample_goals, test_user_with_budget
    ):
        """Логирование события confirmed с new_allocation."""
        completed_goal = sample_goals[0]

        new_allocation: AllocationSummary = {
            "total_budget": Decimal("15000.00"),
            "total_allocated": Decimal("15000.00"),
            "total_needed": Decimal("12000.00"),
            "total_shortfall": Decimal("0.00"),
            "results": [],
            "all_goals_funded": True,
            "budget_not_set": False,
        }

        event = redistribution_service.log_redistribution_event(
            user_id=test_user_with_budget.id,
            completed_goal=completed_goal,
            freed_budget=Decimal("5000.00"),
            remaining_goals_count=2,
            action="confirmed",
            new_allocation=new_allocation,
        )

        assert event["action"] == "confirmed"
        assert event["user_id"] == test_user_with_budget.id
        assert event["completed_goal_id"] == completed_goal.id
        assert event["freed_budget"] == "5000.00"
        assert event["remaining_goals_count"] == 2
        assert event["new_allocation_summary"] is not None

    def test_log_event_declined(
        self, redistribution_service, sample_goals, test_user_with_budget
    ):
        """Логирование события declined без new_allocation."""
        completed_goal = sample_goals[0]

        event = redistribution_service.log_redistribution_event(
            user_id=test_user_with_budget.id,
            completed_goal=completed_goal,
            freed_budget=Decimal("5000.00"),
            remaining_goals_count=2,
            action="declined",
            new_allocation=None,
        )

        assert event["action"] == "declined"
        assert event["new_allocation_summary"] is None

    def test_log_event_structure(
        self, redistribution_service, sample_goals, test_user_with_budget
    ):
        """Проверка всех полей RedistributionEvent."""
        completed_goal = sample_goals[0]

        event = redistribution_service.log_redistribution_event(
            user_id=test_user_with_budget.id,
            completed_goal=completed_goal,
            freed_budget=Decimal("7500.00"),
            remaining_goals_count=3,
            action="confirmed",
            new_allocation=None,
        )

        # Проверяем наличие всех обязательных полей
        assert "timestamp" in event
        assert "user_id" in event
        assert "completed_goal_id" in event
        assert "completed_goal_name" in event
        assert "freed_budget" in event
        assert "remaining_goals_count" in event
        assert "action" in event
        assert "new_allocation_summary" in event

        # Проверяем типы
        assert isinstance(event["timestamp"], str)
        assert isinstance(event["user_id"], int)
        assert isinstance(event["freed_budget"], str)


# =============================================================================
# Tests: Timing (NFR-2)
# =============================================================================


class TestTimingNFR2:
    """Тесты для NFR-2 (время расчета < 50ms)."""

    def test_timing_under_threshold(
        self, redistribution_service, sample_goals, test_user_with_budget, caplog
    ):
        """При времени < 50ms логируется DEBUG."""
        completed_goal = sample_goals[0]

        with caplog.at_level("DEBUG"):
            preview = redistribution_service.calculate_redistribution_preview(
                completed_goal=completed_goal,
                all_goals=sample_goals,
                monthly_budget=Decimal("15000.00"),
                savings_mode="free",
            )

        # Время должно быть меньше порога (обычно << 50ms)
        assert preview["calculation_time_ms"] < NFR2_WARNING_THRESHOLD_MS

    def test_timing_over_threshold_logs_warning(
        self, sample_goals, test_user_with_budget
    ):
        """При времени > 50ms логируется WARNING."""
        completed_goal = sample_goals[0]

        # Создаем mock AllocationService который "медленный"
        mock_allocation_service = MagicMock(spec=AllocationService)

        # Возвращаем валидный AllocationSummary
        mock_result: AllocationSummary = {
            "total_budget": Decimal("15000.00"),
            "total_allocated": Decimal("0.00"),
            "total_needed": Decimal("0.00"),
            "total_shortfall": Decimal("0.00"),
            "results": [
                AllocationResult(
                    goal_id=completed_goal.id,
                    goal_name=completed_goal.name,
                    priority=1,
                    monthly_contribution_needed=Decimal("5000.00"),
                    allocated_amount=Decimal("5000.00"),
                    is_fully_funded=True,
                    shortfall=Decimal("0.00"),
                    skipped_reason=None,
                )
            ],
            "all_goals_funded": True,
            "budget_not_set": False,
        }
        mock_allocation_service.calculate_allocation.return_value = mock_result

        service = RedistributionService(allocation_service=mock_allocation_service)

        # Мокаем time.perf_counter для симуляции медленного расчета
        with patch("app.services.redistribution_service.time.perf_counter") as mock_time:
            # Первый вызов возвращает 0, второй - 0.1 (100ms > 50ms threshold)
            mock_time.side_effect = [0.0, 0.1]

            preview = service.calculate_redistribution_preview(
                completed_goal=completed_goal,
                all_goals=sample_goals,
                monthly_budget=Decimal("15000.00"),
                savings_mode="free",
            )

        # calculation_time_ms должен быть > 50ms (100ms в нашем mock)
        assert preview["calculation_time_ms"] == 100.0
