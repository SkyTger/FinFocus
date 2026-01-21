"""Тесты методов управления приоритетами в GoalService."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.database import User
from app.services.goal_service import GoalService


@pytest.fixture
def goal_service(db_session):
    """Создает GoalService для тестов."""
    return GoalService(db_session)


@pytest.fixture
def user_with_budget(db_session) -> User:
    """Создает пользователя с monthly_savings_budget=5000."""
    user = User(
        email="budget@example.com",
        name="Budget User",
        starting_balance=Decimal("10000.00"),
        monthly_savings_budget=Decimal("5000.00"),
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_get_next_priority_empty(goal_service, test_user):
    """Тест: get_next_priority возвращает 1 если нет активных целей."""
    next_priority = goal_service.get_next_priority(test_user.id)
    assert next_priority == 1


def test_get_next_priority_with_goals(goal_service, test_user):
    """Тест: get_next_priority возвращает max+1."""
    # Создаем 3 цели с приоритетами 1, 2, 3
    target_date = date.today() + timedelta(days=30)
    for i in range(1, 4):
        goal_service.create_goal(
            user_id=test_user.id,
            name=f"Goal {i}",
            target_amount=Decimal("1000.00"),
            target_date=target_date,
            priority=i,
        )

    next_priority = goal_service.get_next_priority(test_user.id)
    assert next_priority == 4


def test_create_goal_auto_priority(goal_service, test_user):
    """Тест: create_goal с auto-priority работает корректно."""
    target_date = date.today() + timedelta(days=30)

    # Создаем первую цель без указания priority
    goal1 = goal_service.create_goal(
        user_id=test_user.id,
        name="Goal 1",
        target_amount=Decimal("1000.00"),
        target_date=target_date,
    )
    assert goal1.priority == 1

    # Создаем вторую цель без указания priority
    goal2 = goal_service.create_goal(
        user_id=test_user.id,
        name="Goal 2",
        target_amount=Decimal("2000.00"),
        target_date=target_date,
    )
    assert goal2.priority == 2

    # Создаем третью цель с явным priority
    goal3 = goal_service.create_goal(
        user_id=test_user.id,
        name="Goal 3",
        target_amount=Decimal("3000.00"),
        target_date=target_date,
        priority=1,
    )
    assert goal3.priority == 1


def test_update_priority_shift_up(goal_service, test_user):
    """Тест: update_priority сдвигает цели вверх при повышении приоритета."""
    target_date = date.today() + timedelta(days=30)

    # Создаем 4 цели с приоритетами 1, 2, 3, 4
    goals = []
    for i in range(1, 5):
        goal = goal_service.create_goal(
            user_id=test_user.id,
            name=f"Goal {i}",
            target_amount=Decimal("1000.00"),
            target_date=target_date,
            priority=i,
        )
        goals.append(goal)

    # Повышаем приоритет 4-й цели до 2 (сдвиг вниз целей 2 и 3)
    goal_service.update_priority(goals[3].id, 2)

    # Проверяем новые приоритеты
    goal_service.session.refresh(goals[0])
    goal_service.session.refresh(goals[1])
    goal_service.session.refresh(goals[2])
    goal_service.session.refresh(goals[3])

    assert goals[0].priority == 1  # Goal 1 не изменился
    assert goals[1].priority == 3  # Goal 2 сдвинут вниз (2→3)
    assert goals[2].priority == 4  # Goal 3 сдвинут вниз (3→4)
    assert goals[3].priority == 2  # Goal 4 переместился (4→2)


def test_update_priority_shift_down(goal_service, test_user):
    """Тест: update_priority сдвигает цели вниз при понижении приоритета."""
    target_date = date.today() + timedelta(days=30)

    # Создаем 4 цели с приоритетами 1, 2, 3, 4
    goals = []
    for i in range(1, 5):
        goal = goal_service.create_goal(
            user_id=test_user.id,
            name=f"Goal {i}",
            target_amount=Decimal("1000.00"),
            target_date=target_date,
            priority=i,
        )
        goals.append(goal)

    # Понижаем приоритет 2-й цели до 4 (сдвиг вверх целей 3 и 4)
    goal_service.update_priority(goals[1].id, 4)

    # Проверяем новые приоритеты
    goal_service.session.refresh(goals[0])
    goal_service.session.refresh(goals[1])
    goal_service.session.refresh(goals[2])
    goal_service.session.refresh(goals[3])

    assert goals[0].priority == 1  # Goal 1 не изменился
    assert goals[1].priority == 4  # Goal 2 переместился (2→4)
    assert goals[2].priority == 2  # Goal 3 сдвинут вверх (3→2)
    assert goals[3].priority == 3  # Goal 4 сдвинут вверх (4→3)


def test_move_priority_up_down(goal_service, test_user):
    """Тест: convenience методы move_priority_up/down работают."""
    target_date = date.today() + timedelta(days=30)

    # Создаем 3 цели
    goal1 = goal_service.create_goal(
        user_id=test_user.id,
        name="Goal 1",
        target_amount=Decimal("1000.00"),
        target_date=target_date,
        priority=1,
    )
    goal2 = goal_service.create_goal(
        user_id=test_user.id,
        name="Goal 2",
        target_amount=Decimal("2000.00"),
        target_date=target_date,
        priority=2,
    )
    goal3 = goal_service.create_goal(
        user_id=test_user.id,
        name="Goal 3",
        target_amount=Decimal("3000.00"),
        target_date=target_date,
        priority=3,
    )

    # Перемещаем Goal 3 вверх (3→2)
    goal_service.move_priority_up(goal3.id)
    goal_service.session.refresh(goal2)
    goal_service.session.refresh(goal3)
    assert goal3.priority == 2
    assert goal2.priority == 3

    # Перемещаем Goal 1 вниз (1→2)
    goal_service.move_priority_down(goal1.id)
    goal_service.session.refresh(goal1)
    goal_service.session.refresh(goal3)
    assert goal1.priority == 2
    assert goal3.priority == 1


def test_get_savings_budget(goal_service, user_with_budget):
    """Тест: get_savings_budget возвращает корректное значение."""
    budget = goal_service.get_savings_budget(user_with_budget.id)
    assert budget == Decimal("5000.00")


def test_update_savings_budget(goal_service, test_user):
    """Тест: update_savings_budget обновляет бюджет пользователя."""
    # Изначально бюджет = 0 (default)
    assert test_user.monthly_savings_budget == Decimal("0")

    # Обновляем бюджет
    goal_service.update_savings_budget(test_user.id, Decimal("10000.00"))

    # Проверяем
    goal_service.session.refresh(test_user)
    assert test_user.monthly_savings_budget == Decimal("10000.00")
