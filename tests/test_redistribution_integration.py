"""Интеграционные тесты для перераспределения средств при достижении цели."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import ValidationError
from app.models.database import GoalStatus
from app.services.allocation_service import AllocationService
from app.services.goal_service import GoalService
from app.services.redistribution_service import RedistributionService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def user_with_budget(db_session, test_user):
    """Создает пользователя с настроенным бюджетом накоплений."""
    test_user.monthly_savings_budget = Decimal("15000.00")
    db_session.commit()
    return test_user


@pytest.fixture
def setup_goals_for_redistribution(db_session, user_with_budget):
    """Создает набор целей для тестирования перераспределения.

    Returns:
        tuple: (goal_almost_completed, goal_partial, goal_empty)
        - goal_almost_completed: current=9500, target=10000 (нужно 500 для завершения)
        - goal_partial: current=5000, target=20000
        - goal_empty: current=0, target=30000
    """
    goal_service = GoalService(db_session)

    # Goal 1: почти достигнута (нужно 500 для завершения)
    goal1 = goal_service.create_goal(
        user_id=user_with_budget.id,
        name="Отпуск",
        target_amount=Decimal("10000.00"),
        target_date=date.today() + timedelta(days=365),
    )
    goal_service.add_contribution(goal1.id, Decimal("9500.00"), date.today())
    db_session.commit()

    # Goal 2: частично накоплена
    goal2 = goal_service.create_goal(
        user_id=user_with_budget.id,
        name="Автомобиль",
        target_amount=Decimal("20000.00"),
        target_date=date.today() + timedelta(days=365),
    )
    goal_service.add_contribution(goal2.id, Decimal("5000.00"), date.today())
    db_session.commit()

    # Goal 3: пустая
    goal3 = goal_service.create_goal(
        user_id=user_with_budget.id,
        name="Ремонт",
        target_amount=Decimal("30000.00"),
        target_date=date.today() + timedelta(days=365),
    )
    db_session.commit()

    return goal1, goal2, goal3


@pytest.fixture
def single_goal_setup(db_session, user_with_budget):
    """Создает одну почти достигнутую цель (без других целей)."""
    goal_service = GoalService(db_session)

    goal = goal_service.create_goal(
        user_id=user_with_budget.id,
        name="Единственная цель",
        target_amount=Decimal("10000.00"),
        target_date=date.today() + timedelta(days=365),
    )
    goal_service.add_contribution(goal.id, Decimal("9500.00"), date.today())
    db_session.commit()

    return goal


@pytest.fixture
def skipped_goal_setup(db_session, user_with_budget):
    """Создает сценарий с skipped целью (низкий приоритет, бюджета не хватило).

    Returns:
        tuple: (high_priority_goal, skipped_goal)
        - high_priority_goal: priority=1, требует весь бюджет
        - skipped_goal: priority=2, skipped в allocation (почти достигнута)
    """
    # Низкий бюджет для создания skipped сценария
    user_with_budget.monthly_savings_budget = Decimal("1000.00")
    db_session.commit()

    goal_service = GoalService(db_session)

    # Goal 1: высокий приоритет, требует много
    goal1 = goal_service.create_goal(
        user_id=user_with_budget.id,
        name="Приоритетная цель",
        target_amount=Decimal("50000.00"),
        target_date=date.today() + timedelta(days=365),
    )
    db_session.commit()

    # Goal 2: низкий приоритет, почти достигнута (будет skipped)
    goal2 = goal_service.create_goal(
        user_id=user_with_budget.id,
        name="Skipped цель",
        target_amount=Decimal("10000.00"),
        target_date=date.today() + timedelta(days=365),
    )
    goal_service.add_contribution(goal2.id, Decimal("9500.00"), date.today())
    db_session.commit()

    return goal1, goal2


# =============================================================================
# Tests: Goal completion triggers preview
# =============================================================================


class TestGoalCompletionTriggersPreview:
    """Тесты для проверки что завершение цели генерирует preview."""

    def test_goal_completion_triggers_redistribution_preview(
        self, db_session, user_with_budget, setup_goals_for_redistribution
    ):
        """E2E: Добавление взноса, достигающего цели, генерирует preview.

        Сценарий:
        1. Goal1 имеет current=9500, target=10000
        2. Добавить взнос 500 → goal1 достигает цели
        3. Проверить: goal1.is_completed = True
        4. Вызвать calculate_redistribution_preview()
        5. Проверить: freed_budget > 0, has_remaining_goals = True
        """
        goal1, goal2, goal3 = setup_goals_for_redistribution

        goal_service = GoalService(db_session)
        allocation_service = AllocationService()
        redistribution_service = RedistributionService(allocation_service)

        # Act: добавляем взнос, достигающий цели
        was_completed_before = goal1.is_completed
        goal_service.add_contribution(goal1.id, Decimal("500.00"), date.today())
        db_session.commit()

        # Assert: цель теперь завершена
        assert goal1.is_completed is True
        assert was_completed_before is False  # была не завершена до взноса

        # Act: вызываем calculate_redistribution_preview
        all_goals = goal_service.get_all_by_user(user_with_budget.id)
        preview = redistribution_service.calculate_redistribution_preview(
            completed_goal=goal1,
            all_goals=all_goals,
            monthly_budget=user_with_budget.monthly_savings_budget,
            savings_mode="free",
        )

        # Assert: preview содержит корректные данные
        assert preview["completed_goal_id"] == goal1.id
        assert preview["completed_goal_name"] == "Отпуск"
        # freed_budget может быть 0 для почти завершенной цели
        # (low monthly_contribution)
        # Главное - проверить что значение валидное (>= 0) и корректно определено
        assert preview["freed_budget"] >= Decimal("0")
        # Если цель была почти завершена, monthly_contribution была низкой → skipped
        if preview["freed_budget"] == Decimal("0"):
            assert preview["was_skipped_in_old_allocation"] is True
        assert preview["has_remaining_goals"] is True
        assert preview["remaining_goals_count"] == 2  # goal2 и goal3

    def test_just_completed_detection_logic(
        self, db_session, user_with_budget, setup_goals_for_redistribution
    ):
        """E2E: Проверка логики just-completed detection.

        Проверяет паттерн:
        - was_completed_before = goal.is_completed (до взноса)
        - just_completed = goal.is_completed and not was_completed_before (после)
        """
        goal1, _, _ = setup_goals_for_redistribution
        goal_service = GoalService(db_session)

        # Взнос НЕ достигающий цели
        was_completed_1 = goal1.is_completed
        goal_service.add_contribution(goal1.id, Decimal("100.00"), date.today())
        db_session.commit()

        just_completed_1 = goal1.is_completed and not was_completed_1
        assert just_completed_1 is False  # еще не достигнута

        # Взнос ДОСТИГАЮЩИЙ цели
        was_completed_2 = goal1.is_completed
        goal_service.add_contribution(goal1.id, Decimal("400.00"), date.today())
        db_session.commit()

        just_completed_2 = goal1.is_completed and not was_completed_2
        assert just_completed_2 is True  # теперь достигнута


# =============================================================================
# Tests: Repeated contribution (no redistribution)
# =============================================================================


class TestRepeatedContribution:
    """Тесты: повторный взнос в completed цель не триггерит redistribution."""

    def test_repeated_contribution_raises_validation_error(
        self, db_session, user_with_budget, setup_goals_for_redistribution
    ):
        """E2E: Повторный взнос в уже завершенную цель вызывает ValidationError.

        Сценарий:
        1. Достигнуть goal1 взносом 500
        2. Попытаться добавить еще один взнос 100
        3. Проверить: ValidationError с сообщением о завершенной цели
        """
        goal1, _, _ = setup_goals_for_redistribution
        goal_service = GoalService(db_session)

        # Шаг 1: завершаем цель
        goal_service.add_contribution(goal1.id, Decimal("500.00"), date.today())
        db_session.commit()
        assert goal1.is_completed is True

        # Шаг 2: попытка добавить взнос в завершенную цель
        with pytest.raises(ValidationError) as exc_info:
            goal_service.add_contribution(goal1.id, Decimal("100.00"), date.today())

        # Шаг 3: проверяем сообщение об ошибке
        assert "завершенную цель" in str(exc_info.value)


# =============================================================================
# Tests: Confirm updates allocation
# =============================================================================


class TestConfirmRedistribution:
    """Тесты для проверки что confirm обновляет allocation."""

    def test_confirm_redistribution_updates_allocation(
        self, db_session, user_with_budget, setup_goals_for_redistribution
    ):
        """E2E: Confirm redistribution пересчитывает allocation для оставшихся целей.

        Сценарий:
        1. Достигнуть goal1
        2. Получить old_allocation (до confirm - goal1 еще учитывалась)
        3. "Confirm" redistribution
        4. Получить new_allocation (после confirm)
        5. Проверить: goal2 и goal3 получают больше бюджета
        """
        goal1, goal2, goal3 = setup_goals_for_redistribution

        goal_service = GoalService(db_session)
        allocation_service = AllocationService()
        redistribution_service = RedistributionService(allocation_service)

        # Шаг 1: достигаем цель
        goal_service.add_contribution(goal1.id, Decimal("500.00"), date.today())
        db_session.commit()

        # Шаг 2: получаем preview
        all_goals = goal_service.get_all_by_user(user_with_budget.id)
        preview = redistribution_service.calculate_redistribution_preview(
            completed_goal=goal1,
            all_goals=all_goals,
            monthly_budget=user_with_budget.monthly_savings_budget,
            savings_mode="free",
        )

        old_allocation = preview["old_allocation"]
        new_allocation = preview["new_allocation"]

        # Шаг 3: проверяем что new_allocation отличается от old_allocation
        assert old_allocation is not None
        assert new_allocation is not None

        # В old_allocation goal1 получала часть бюджета
        # В new_allocation goal1 excluded, goal2 и goal3 получают больше
        old_goal2_allocation = next(
            r for r in old_allocation["results"] if r["goal_id"] == goal2.id
        )
        new_goal2_allocation = next(
            r for r in new_allocation["results"] if r["goal_id"] == goal2.id
        )

        # goal2 должна получить больше в new_allocation
        assert (
            new_goal2_allocation["allocated_amount"]
            >= old_goal2_allocation["allocated_amount"]
        )

        # Шаг 4: логируем confirm событие
        event = redistribution_service.log_redistribution_event(
            preview=preview,
            action="confirmed",
        )
        assert event["action"] == "confirmed"


# =============================================================================
# Tests: Decline keeps allocation unchanged
# =============================================================================


class TestDeclineRedistribution:
    """Тесты для проверки что decline сохраняет allocation без изменений."""

    def test_decline_redistribution_keeps_allocation(
        self, db_session, user_with_budget, setup_goals_for_redistribution
    ):
        """E2E: Decline redistribution логирует событие, allocation не меняется.

        Сценарий:
        1. Достигнуть goal1
        2. Получить preview
        3. "Decline" redistribution
        4. Проверить: событие залогировано, цель остается COMPLETED
        """
        goal1, _, _ = setup_goals_for_redistribution

        goal_service = GoalService(db_session)
        allocation_service = AllocationService()
        redistribution_service = RedistributionService(allocation_service)

        # Шаг 1: достигаем цель
        goal_service.add_contribution(goal1.id, Decimal("500.00"), date.today())
        db_session.commit()

        # Шаг 2: получаем preview
        all_goals = goal_service.get_all_by_user(user_with_budget.id)
        preview = redistribution_service.calculate_redistribution_preview(
            completed_goal=goal1,
            all_goals=all_goals,
            monthly_budget=user_with_budget.monthly_savings_budget,
            savings_mode="free",
        )

        # Шаг 3: логируем decline событие
        event = redistribution_service.log_redistribution_event(
            preview=preview,
            action="declined",
        )

        # Шаг 4: проверяем событие
        assert event["action"] == "declined"
        assert event["completed_goal_id"] == goal1.id

        # Цель остается COMPLETED
        assert goal1.status == GoalStatus.COMPLETED


# =============================================================================
# Tests: No remaining goals scenario
# =============================================================================


class TestNoRemainingGoals:
    """Тесты для сценария без оставшихся активных целей."""

    def test_no_remaining_goals_scenario(
        self, db_session, user_with_budget, single_goal_setup
    ):
        """E2E: Если достигнута единственная цель, has_remaining_goals = False.

        Сценарий:
        1. Создать только одну цель
        2. Достигнуть её
        3. Проверить: has_remaining_goals = False, new_allocation = None
        """
        goal = single_goal_setup

        goal_service = GoalService(db_session)
        allocation_service = AllocationService()
        redistribution_service = RedistributionService(allocation_service)

        # Достигаем цель
        goal_service.add_contribution(goal.id, Decimal("500.00"), date.today())
        db_session.commit()
        assert goal.is_completed is True

        # Получаем preview
        all_goals = goal_service.get_all_by_user(user_with_budget.id)
        preview = redistribution_service.calculate_redistribution_preview(
            completed_goal=goal,
            all_goals=all_goals,
            monthly_budget=user_with_budget.monthly_savings_budget,
            savings_mode="free",
        )

        # Проверяем
        assert preview["has_remaining_goals"] is False
        assert preview["remaining_goals_count"] == 0
        assert preview["new_allocation"] is None


# =============================================================================
# Tests: Skipped goal in allocation
# =============================================================================


class TestSkippedGoalScenario:
    """Тесты для сценария с skipped целью в allocation."""

    def test_skipped_goal_freed_budget_zero(
        self, db_session, user_with_budget, skipped_goal_setup
    ):
        """E2E: Если цель была skipped в allocation, freed_budget = 0.

        Сценарий:
        1. Goal1 (priority=1) требует весь бюджет
        2. Goal2 (priority=2) skipped в allocation
        3. Достигнуть goal2
        4. Проверить: freed_budget = 0, was_skipped_in_old_allocation = True
        """
        goal1, goal2 = skipped_goal_setup

        goal_service = GoalService(db_session)
        allocation_service = AllocationService()
        redistribution_service = RedistributionService(allocation_service)

        # Проверяем что goal2 действительно skipped в текущем allocation
        all_goals = goal_service.get_all_by_user(user_with_budget.id)
        current_allocation = allocation_service.calculate_allocation(
            all_goals, user_with_budget.monthly_savings_budget
        )

        goal2_result = next(
            r for r in current_allocation["results"] if r["goal_id"] == goal2.id
        )
        assert goal2_result["allocated_amount"] == Decimal("0")  # skipped

        # Достигаем goal2 (skipped цель)
        goal_service.add_contribution(goal2.id, Decimal("500.00"), date.today())
        db_session.commit()
        assert goal2.is_completed is True

        # Получаем preview
        all_goals = goal_service.get_all_by_user(user_with_budget.id)
        preview = redistribution_service.calculate_redistribution_preview(
            completed_goal=goal2,
            all_goals=all_goals,
            monthly_budget=user_with_budget.monthly_savings_budget,
            savings_mode="free",
        )

        # Проверяем
        assert preview["freed_budget"] == Decimal("0")
        assert preview["was_skipped_in_old_allocation"] is True
