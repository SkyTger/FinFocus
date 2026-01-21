"""Тесты AllocationService для распределения бюджета между целями."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.database import GoalStatus
from app.services.allocation_service import AllocationService
from app.services.goal_service import GoalService


@pytest.fixture
def allocation_service():
    """Создает AllocationService для тестов."""
    return AllocationService()


@pytest.fixture
def goal_service(db_session):
    """Создает GoalService для тестов."""
    return GoalService(db_session)


def test_empty_goals_list(allocation_service):
    """Пустой список целей → пустой results, все totals = 0."""
    budget = Decimal("5000.00")
    summary = allocation_service.calculate_allocation(goals=[], monthly_budget=budget)

    assert summary["total_budget"] == budget
    assert summary["total_allocated"] == Decimal("0")
    assert summary["total_needed"] == Decimal("0")
    assert summary["total_shortfall"] == Decimal("0")
    assert summary["results"] == []
    assert summary["all_goals_funded"] is True
    assert summary["budget_not_set"] is False


def test_single_goal_fully_funded(allocation_service, goal_service, test_user):
    """Одна цель, бюджет покрывает → is_fully_funded=True, shortfall=0."""
    target_date = date.today() + timedelta(days=90)
    goal = goal_service.create_goal(
        user_id=test_user.id,
        name="Emergency Fund",
        target_amount=Decimal("10000.00"),
        target_date=target_date,
        priority=1,
    )

    # monthly_contribution ≈ 10000 / 3 = 3333.33
    # budget = 5000 > needed → fully funded
    budget = Decimal("5000.00")
    summary = allocation_service.calculate_allocation(
        goals=[goal], monthly_budget=budget
    )

    assert summary["total_budget"] == budget
    assert summary["total_allocated"] == goal.monthly_contribution
    assert summary["total_needed"] == goal.monthly_contribution
    assert summary["total_shortfall"] == Decimal("0")
    assert summary["all_goals_funded"] is True
    assert summary["budget_not_set"] is False

    result = summary["results"][0]
    assert result["goal_id"] == goal.id
    assert result["goal_name"] == "Emergency Fund"
    assert result["priority"] == 1
    assert result["monthly_contribution_needed"] == goal.monthly_contribution
    assert result["allocated_amount"] == goal.monthly_contribution
    assert result["is_fully_funded"] is True
    assert result["shortfall"] == Decimal("0")
    assert result["skipped_reason"] is None


def test_single_goal_partially_funded(allocation_service, goal_service, test_user):
    """Одна цель, бюджет НЕ покрывает → is_fully_funded=False, shortfall > 0."""
    target_date = date.today() + timedelta(days=90)
    goal = goal_service.create_goal(
        user_id=test_user.id,
        name="Vacation",
        target_amount=Decimal("10000.00"),
        target_date=target_date,
        priority=1,
    )

    # monthly_contribution ≈ 10000 / 3 = 3333.33
    # budget = 2000 < needed → partially funded
    budget = Decimal("2000.00")
    needed = goal.monthly_contribution
    summary = allocation_service.calculate_allocation(
        goals=[goal], monthly_budget=budget
    )

    assert summary["total_budget"] == budget
    assert (
        summary["total_allocated"] == budget
    )  # allocated = min(needed, budget) = budget
    assert summary["total_needed"] == needed
    assert summary["total_shortfall"] == needed - budget
    assert summary["all_goals_funded"] is False
    assert summary["budget_not_set"] is False

    result = summary["results"][0]
    assert result["allocated_amount"] == budget
    assert result["is_fully_funded"] is False
    assert result["shortfall"] == needed - budget
    assert result["skipped_reason"] is None


def test_multiple_goals_full_coverage(allocation_service, goal_service, test_user):
    """Несколько целей, бюджет покрывает все → all_goals_funded=True."""
    target_date = date.today() + timedelta(days=180)

    # Создаем 3 цели с приоритетами 1, 2, 3
    goal1 = goal_service.create_goal(
        user_id=test_user.id,
        name="Emergency Fund",
        target_amount=Decimal("6000.00"),
        target_date=target_date,
        priority=1,
    )
    goal2 = goal_service.create_goal(
        user_id=test_user.id,
        name="Vacation",
        target_amount=Decimal("6000.00"),
        target_date=target_date,
        priority=2,
    )
    goal3 = goal_service.create_goal(
        user_id=test_user.id,
        name="New Laptop",
        target_amount=Decimal("6000.00"),
        target_date=target_date,
        priority=3,
    )

    # monthly_contribution each ≈ 6000 / 6 = 1000
    # total_needed = 3000
    # budget = 5000 > total_needed → all funded
    budget = Decimal("5000.00")
    summary = allocation_service.calculate_allocation(
        goals=[goal1, goal2, goal3], monthly_budget=budget
    )

    total_needed = (
        goal1.monthly_contribution
        + goal2.monthly_contribution
        + goal3.monthly_contribution
    )

    assert summary["total_budget"] == budget
    assert summary["total_allocated"] == total_needed
    assert summary["total_needed"] == total_needed
    assert summary["total_shortfall"] == Decimal("0")
    assert summary["all_goals_funded"] is True

    # Проверяем что каждая цель fully funded
    for result in summary["results"]:
        assert result["is_fully_funded"] is True
        assert result["shortfall"] == Decimal("0")
        assert result["skipped_reason"] is None


def test_multiple_goals_partial_coverage(allocation_service, goal_service, test_user):
    """3 цели с приоритетами 1,2,3, бюджет покрывает только 1.5 цели.

    Цель 1: fully funded
    Цель 2: partially funded
    Цель 3: not funded (allocated=0)
    """
    target_date = date.today() + timedelta(days=90)

    # Создаем 3 цели, каждая требует ≈ 3333.33/month
    goal1 = goal_service.create_goal(
        user_id=test_user.id,
        name="Priority 1",
        target_amount=Decimal("10000.00"),
        target_date=target_date,
        priority=1,
    )
    goal2 = goal_service.create_goal(
        user_id=test_user.id,
        name="Priority 2",
        target_amount=Decimal("10000.00"),
        target_date=target_date,
        priority=2,
    )
    goal3 = goal_service.create_goal(
        user_id=test_user.id,
        name="Priority 3",
        target_amount=Decimal("10000.00"),
        target_date=target_date,
        priority=3,
    )

    # budget = 5000 покрывает только goal1 (3333.33) + часть goal2 (1666.67)
    budget = Decimal("5000.00")
    summary = allocation_service.calculate_allocation(
        goals=[goal1, goal2, goal3], monthly_budget=budget
    )

    needed1 = goal1.monthly_contribution
    needed2 = goal2.monthly_contribution
    needed3 = goal3.monthly_contribution
    total_needed = needed1 + needed2 + needed3

    assert summary["total_budget"] == budget
    assert summary["total_allocated"] == budget
    assert summary["total_needed"] == total_needed
    assert summary["total_shortfall"] == total_needed - budget
    assert summary["all_goals_funded"] is False

    results = summary["results"]
    # Goal 1: fully funded
    assert results[0]["goal_name"] == "Priority 1"
    assert results[0]["allocated_amount"] == needed1
    assert results[0]["is_fully_funded"] is True
    assert results[0]["shortfall"] == Decimal("0")

    # Goal 2: partially funded
    assert results[1]["goal_name"] == "Priority 2"
    assert results[1]["allocated_amount"] == budget - needed1
    assert results[1]["is_fully_funded"] is False
    assert results[1]["shortfall"] == needed2 - (budget - needed1)

    # Goal 3: not funded
    assert results[2]["goal_name"] == "Priority 3"
    assert results[2]["allocated_amount"] == Decimal("0")
    assert results[2]["is_fully_funded"] is False
    assert results[2]["shortfall"] == needed3


def test_zero_budget(allocation_service, goal_service, test_user):
    """Нулевой бюджет → budget_not_set=True, все allocated=0."""
    target_date = date.today() + timedelta(days=90)
    goal = goal_service.create_goal(
        user_id=test_user.id,
        name="Goal",
        target_amount=Decimal("10000.00"),
        target_date=target_date,
        priority=1,
    )

    budget = Decimal("0")
    summary = allocation_service.calculate_allocation(
        goals=[goal], monthly_budget=budget
    )

    needed = goal.monthly_contribution

    assert summary["total_budget"] == Decimal("0")
    assert summary["total_allocated"] == Decimal("0")
    assert summary["total_needed"] == needed
    assert summary["total_shortfall"] == needed
    assert summary["all_goals_funded"] is False
    assert summary["budget_not_set"] is True

    result = summary["results"][0]
    assert result["allocated_amount"] == Decimal("0")
    assert result["is_fully_funded"] is False
    assert result["shortfall"] == needed


def test_mixed_statuses(allocation_service, goal_service, test_user, db_session):
    """Цели с разными статусами (ACTIVE, PAUSED, COMPLETED).

    ACTIVE получают allocation, остальные — skipped_reason.
    """
    target_date = date.today() + timedelta(days=90)

    # Goal 1: ACTIVE
    goal1 = goal_service.create_goal(
        user_id=test_user.id,
        name="Active Goal",
        target_amount=Decimal("10000.00"),
        target_date=target_date,
        priority=1,
    )

    # Goal 2: PAUSED
    goal2 = goal_service.create_goal(
        user_id=test_user.id,
        name="Paused Goal",
        target_amount=Decimal("10000.00"),
        target_date=target_date,
        priority=2,
    )
    goal2.status = GoalStatus.PAUSED
    db_session.commit()

    # Goal 3: COMPLETED
    goal3 = goal_service.create_goal(
        user_id=test_user.id,
        name="Completed Goal",
        target_amount=Decimal("10000.00"),
        target_date=target_date,
        priority=3,
    )
    goal3.status = GoalStatus.COMPLETED
    db_session.commit()

    # Goal 4: ACTIVE but monthly_contribution = 0 (target_date in past)
    # Создаем с валидной датой, затем меняем на прошлое (минуя валидацию)
    goal4 = goal_service.create_goal(
        user_id=test_user.id,
        name="Expired Goal",
        target_amount=Decimal("10000.00"),
        target_date=target_date,
        priority=4,
    )
    goal4.target_date = date.today() - timedelta(days=10)  # Переводим в прошлое
    db_session.commit()

    budget = Decimal("5000.00")
    summary = allocation_service.calculate_allocation(
        goals=[goal1, goal2, goal3, goal4], monthly_budget=budget
    )

    # Только goal1 должна получить allocation
    needed1 = goal1.monthly_contribution
    assert summary["total_allocated"] == needed1
    assert summary["total_needed"] == needed1
    assert summary["total_shortfall"] == Decimal("0")
    assert summary["all_goals_funded"] is True

    results = summary["results"]

    # Goal 1: ACTIVE - allocated
    assert results[0]["goal_name"] == "Active Goal"
    assert results[0]["allocated_amount"] == needed1
    assert results[0]["is_fully_funded"] is True
    assert results[0]["skipped_reason"] is None

    # Goal 2: PAUSED - skipped
    assert results[1]["goal_name"] == "Paused Goal"
    assert results[1]["allocated_amount"] == Decimal("0")
    assert results[1]["skipped_reason"] == "paused"

    # Goal 3: COMPLETED - skipped
    assert results[2]["goal_name"] == "Completed Goal"
    assert results[2]["allocated_amount"] == Decimal("0")
    assert results[2]["skipped_reason"] == "completed"

    # Goal 4: zero_contribution - skipped
    assert results[3]["goal_name"] == "Expired Goal"
    assert results[3]["allocated_amount"] == Decimal("0")
    assert results[3]["skipped_reason"] == "zero_contribution"
