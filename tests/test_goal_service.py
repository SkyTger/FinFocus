"""Тесты для GoalService."""

from datetime import date, timedelta
from decimal import Decimal

from app.services.goal_service import GoalService


class TestGetContributions:
    """Тесты для метода get_contributions()."""

    def test_get_contributions_returns_sorted_desc(self, db_session, test_user):
        """Тест: взносы возвращаются отсортированными по дате DESC."""
        service = GoalService(db_session)
        goal = service.create_goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("10000"),
            target_date=date.today() + timedelta(days=30),
        )

        # Добавляем взносы в разном порядке
        service.add_contribution(goal.id, Decimal("100"), date(2026, 1, 1), "First")
        service.add_contribution(goal.id, Decimal("200"), date(2026, 1, 15), "Second")
        service.add_contribution(goal.id, Decimal("300"), date(2026, 1, 10), "Third")
        db_session.commit()

        contributions = service.get_contributions(goal.id)

        assert len(contributions) == 3
        assert contributions[0].description == "Second"  # 15 января
        assert contributions[1].description == "Third"  # 10 января
        assert contributions[2].description == "First"  # 1 января

    def test_get_contributions_respects_limit(self, db_session, test_user):
        """Тест: limit ограничивает количество возвращаемых записей."""
        service = GoalService(db_session)
        goal = service.create_goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("10000"),
            target_date=date.today() + timedelta(days=30),
        )

        # Добавляем 5 взносов
        for i in range(5):
            service.add_contribution(
                goal.id,
                Decimal("100"),
                date.today() - timedelta(days=i),
                f"Contribution {i}",
            )
        db_session.commit()

        contributions = service.get_contributions(goal.id, limit=3)

        assert len(contributions) == 3

    def test_get_contributions_empty_list(self, db_session, test_user):
        """Тест: пустой список если нет взносов."""
        service = GoalService(db_session)
        goal = service.create_goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("10000"),
            target_date=date.today() + timedelta(days=30),
        )
        db_session.commit()

        contributions = service.get_contributions(goal.id)

        assert contributions == []

    def test_get_contributions_filters_by_goal_id(self, db_session, test_user):
        """Тест: возвращает взносы только указанной цели."""
        service = GoalService(db_session)

        # Создаем первую цель и добавляем взнос
        goal1 = service.create_goal(
            user_id=test_user.id,
            name="Goal 1",
            target_amount=Decimal("10000"),
            target_date=date.today() + timedelta(days=30),
        )
        service.add_contribution(goal1.id, Decimal("100"), description="For Goal 1")

        # Удаляем первую цель чтобы создать вторую (MVP ограничение)
        service.delete_goal(goal1.id)

        goal2 = service.create_goal(
            user_id=test_user.id,
            name="Goal 2",
            target_amount=Decimal("5000"),
            target_date=date.today() + timedelta(days=60),
        )
        service.add_contribution(goal2.id, Decimal("200"), description="For Goal 2")
        db_session.commit()

        contributions = service.get_contributions(goal2.id)

        assert len(contributions) == 1
        assert contributions[0].description == "For Goal 2"
