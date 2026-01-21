"""Интеграционные тесты для множественных целей с приоритетами."""

from datetime import date
from decimal import Decimal

from app.models.database import Goal, GoalStatus
from app.services.allocation_service import AllocationService
from app.services.goal_service import GoalService


def test_create_multiple_goals_with_auto_priority(db_session, test_user):
    """E2E: создание 3+ целей с автоматическим назначением приоритетов.

    Сценарий:
    1. Создать 3 цели без указания priority
    2. Проверить что priorities = [1, 2, 3]
    3. Проверить сортировку в get_all_by_user
    """
    # Arrange
    service = GoalService(db_session)

    # Act - создаем 3 цели без указания priority
    goal1 = service.create_goal(
        user_id=test_user.id,
        name="Отпуск",
        target_amount=Decimal("100000.00"),
        target_date=date(2026, 12, 31),
    )
    db_session.commit()

    goal2 = service.create_goal(
        user_id=test_user.id,
        name="Автомобиль",
        target_amount=Decimal("500000.00"),
        target_date=date(2027, 6, 30),
    )
    db_session.commit()

    goal3 = service.create_goal(
        user_id=test_user.id,
        name="Ремонт",
        target_amount=Decimal("200000.00"),
        target_date=date(2027, 12, 31),
    )
    db_session.commit()

    # Assert - проверяем автоматические приоритеты
    assert goal1.priority == 1
    assert goal2.priority == 2
    assert goal3.priority == 3

    # Assert - проверяем сортировку в get_all_by_user
    all_goals = service.get_all_by_user(test_user.id)
    assert len(all_goals) == 3
    assert all_goals[0].id == goal1.id
    assert all_goals[1].id == goal2.id
    assert all_goals[2].id == goal3.id


def test_priority_reorder_updates_allocation(db_session, test_user):
    """E2E: изменение приоритета пересчитывает распределение.

    Сценарий:
    1. Создать 3 цели с monthly_contribution [примерно 100, 200, 300]
    2. Установить budget = 250
    3. Проверить allocation: [100, 150, 0]
    4. Поменять приоритеты (цель 3 → 1)
    5. Проверить новый allocation: [250, 0, 0]
    """
    # Arrange - создаем цели с разными monthly_contribution
    # Цель 1: target=10000, current=0, 11 месяцев → ~909/мес
    goal1 = Goal(
        user_id=test_user.id,
        name="Цель 1 (низкий взнос)",
        target_amount=Decimal("10000.00"),
        current_amount=Decimal("0"),
        target_date=date(2026, 12, 31),  # ~11 месяцев от сегодня
        status=GoalStatus.ACTIVE,
        priority=1,
    )
    # Цель 2: target=20000, current=0, 11 месяцев → ~1818/мес
    goal2 = Goal(
        user_id=test_user.id,
        name="Цель 2 (средний взнос)",
        target_amount=Decimal("20000.00"),
        current_amount=Decimal("0"),
        target_date=date(2026, 12, 31),
        status=GoalStatus.ACTIVE,
        priority=2,
    )
    # Цель 3: target=30000, current=0, 11 месяцев → ~2727/мес
    goal3 = Goal(
        user_id=test_user.id,
        name="Цель 3 (высокий взнос)",
        target_amount=Decimal("30000.00"),
        current_amount=Decimal("0"),
        target_date=date(2026, 12, 31),
        status=GoalStatus.ACTIVE,
        priority=3,
    )
    db_session.add_all([goal1, goal2, goal3])
    db_session.commit()

    # Установить бюджет
    goal_service = GoalService(db_session)
    goal_service.update_savings_budget(test_user.id, Decimal("2500.00"))
    db_session.commit()

    allocation_service = AllocationService()

    # Act 1 - начальное распределение с приоритетами [1, 2, 3]
    goals = goal_service.get_all_by_user(test_user.id)
    summary1 = allocation_service.calculate_allocation(goals, Decimal("2500.00"))

    # Assert 1 - приоритет 1 получает полностью, приоритет 2 получает остаток
    # goal1 нужно ~870 → получает полностью
    # goal2 нужно ~1740 → получает остаток ~1630
    # goal3 нужно ~2610 → получает 0
    goal1_needed = summary1["results"][0]["monthly_contribution_needed"]

    assert summary1["results"][0]["goal_id"] == goal1.id
    assert summary1["results"][0]["allocated_amount"] == goal1_needed
    assert summary1["results"][0]["is_fully_funded"] is True

    assert summary1["results"][1]["goal_id"] == goal2.id
    # goal2 получает остаток от бюджета
    expected_goal2 = Decimal("2500.00") - goal1_needed
    assert summary1["results"][1]["allocated_amount"] == expected_goal2
    assert summary1["results"][1]["is_fully_funded"] is False

    assert summary1["results"][2]["goal_id"] == goal3.id
    assert summary1["results"][2]["allocated_amount"] == Decimal("0")
    assert summary1["results"][2]["is_fully_funded"] is False

    # Act 2 - меняем приоритет цели 3 на 1 (теперь самая приоритетная)
    goal_service.update_priority(goal3.id, 1)
    db_session.commit()

    # Act 3 - пересчитываем распределение
    goals = goal_service.get_all_by_user(test_user.id)
    summary2 = allocation_service.calculate_allocation(goals, Decimal("2500.00"))

    # Assert 2 - теперь goal3 (приоритет 1) получает весь бюджет
    assert summary2["results"][0]["goal_id"] == goal3.id
    # goal3 нужно больше бюджета, поэтому получает весь доступный
    goal3_needed = summary2["results"][0]["monthly_contribution_needed"]
    assert summary2["results"][0]["allocated_amount"] == Decimal("2500.00")
    assert goal3_needed > Decimal("2500.00")  # проверка что не хватает
    assert summary2["results"][0]["is_fully_funded"] is False

    # goal1 и goal2 сдвинулись вниз и не получают ничего
    assert summary2["results"][1]["allocated_amount"] == Decimal("0")
    assert summary2["results"][1]["is_fully_funded"] is False
    assert summary2["results"][2]["allocated_amount"] == Decimal("0")
    assert summary2["results"][2]["is_fully_funded"] is False


def test_budget_change_updates_allocation(db_session, test_user):
    """E2E: изменение бюджета пересчитывает распределение.

    Сценарий:
    1. Создать 2 цели с monthly_contribution [примерно 1000, 1000]
    2. Установить budget = 1500
    3. Проверить allocation: [1000, 500]
    4. Увеличить budget до 2000
    5. Проверить allocation: [1000, 1000]
    """
    # Arrange - создаем 2 цели с одинаковым monthly_contribution
    goal1 = Goal(
        user_id=test_user.id,
        name="Цель 1",
        target_amount=Decimal("11000.00"),
        current_amount=Decimal("0"),
        target_date=date(2026, 12, 31),  # ~11 месяцев → 1000/мес
        status=GoalStatus.ACTIVE,
        priority=1,
    )
    goal2 = Goal(
        user_id=test_user.id,
        name="Цель 2",
        target_amount=Decimal("11000.00"),
        current_amount=Decimal("0"),
        target_date=date(2026, 12, 31),
        status=GoalStatus.ACTIVE,
        priority=2,
    )
    db_session.add_all([goal1, goal2])
    db_session.commit()

    goal_service = GoalService(db_session)
    allocation_service = AllocationService()

    # Act 1 - устанавливаем бюджет 1500
    goal_service.update_savings_budget(test_user.id, Decimal("1500.00"))
    db_session.commit()

    goals = goal_service.get_all_by_user(test_user.id)
    summary1 = allocation_service.calculate_allocation(goals, Decimal("1500.00"))

    # Assert 1 - goal1 получает полностью, goal2 получает остаток
    goal1_needed = summary1["results"][0]["monthly_contribution_needed"]
    goal2_needed = summary1["results"][1]["monthly_contribution_needed"]

    assert summary1["results"][0]["goal_id"] == goal1.id
    assert summary1["results"][0]["allocated_amount"] == goal1_needed
    assert summary1["results"][0]["is_fully_funded"] is True

    assert summary1["results"][1]["goal_id"] == goal2.id
    # goal2 получает остаток от бюджета
    expected_goal2 = Decimal("1500.00") - goal1_needed
    assert summary1["results"][1]["allocated_amount"] == expected_goal2
    assert summary1["results"][1]["is_fully_funded"] is False

    # Act 2 - увеличиваем бюджет до 2000
    goal_service.update_savings_budget(test_user.id, Decimal("2000.00"))
    db_session.commit()

    summary2 = allocation_service.calculate_allocation(goals, Decimal("2000.00"))

    # Assert 2 - обе цели получают полностью
    # Бюджет 2000 теперь покрывает обе цели (каждая нужна ~960)
    assert summary2["results"][0]["goal_id"] == goal1.id
    assert summary2["results"][0]["allocated_amount"] == goal1_needed
    assert summary2["results"][0]["is_fully_funded"] is True

    assert summary2["results"][1]["goal_id"] == goal2.id
    assert summary2["results"][1]["allocated_amount"] == goal2_needed
    assert summary2["results"][1]["is_fully_funded"] is True

    # Проверяем что обе цели полностью профинансированы
    assert summary2["all_goals_funded"] is True
