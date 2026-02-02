"""Тесты для GoalService."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

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


class TestAddContributionWithTransaction:
    """Тесты для интеграции add_contribution с транзакциями."""

    def test_add_contribution_creates_transaction_from_balance_mode(
        self, db_session, test_user
    ):
        """add_contribution создаёт транзакцию в режиме from_balance."""
        from app.models.database import Transaction, TransactionType

        # По умолчанию режим from_balance
        service = GoalService(db_session)
        goal = service.create_goal(
            user_id=test_user.id,
            name="Цель с транзакцией",
            target_amount=Decimal("50000"),
            target_date=date.today() + timedelta(days=180),
        )

        service.add_contribution(goal.id, Decimal("5000"))
        db_session.commit()

        # Проверяем создание транзакции
        transactions = (
            db_session.query(Transaction)
            .filter(
                Transaction.user_id == test_user.id,
                Transaction.transaction_type == TransactionType.SAVINGS_CONTRIBUTION,
            )
            .all()
        )

        assert len(transactions) == 1
        assert transactions[0].amount == Decimal("5000")
        assert transactions[0].description == "Взнос: Цель с транзакцией"

        # Проверяем GoalContribution имеет transaction_id
        contributions = service.get_contributions(goal.id)
        assert len(contributions) == 1
        assert contributions[0].transaction_id == transactions[0].id

    def test_add_contribution_no_transaction_in_fixed_date_mode(
        self, db_session, test_user
    ):
        """add_contribution не создаёт транзакцию в режиме fixed_date."""
        from app.models.database import Transaction, TransactionType

        # Устанавливаем режим fixed_date
        test_user.reservation_mode = "fixed_date"
        test_user.reservation_day = 15
        db_session.commit()

        service = GoalService(db_session)
        goal = service.create_goal(
            user_id=test_user.id,
            name="Цель fixed_date",
            target_amount=Decimal("30000"),
            target_date=date.today() + timedelta(days=120),
        )

        service.add_contribution(goal.id, Decimal("3000"))
        db_session.commit()

        # Проверяем что транзакция НЕ создана
        transactions = (
            db_session.query(Transaction)
            .filter(
                Transaction.user_id == test_user.id,
                Transaction.transaction_type == TransactionType.SAVINGS_CONTRIBUTION,
            )
            .all()
        )

        assert len(transactions) == 0

        # Проверяем GoalContribution имеет transaction_id = None
        contributions = service.get_contributions(goal.id)
        assert len(contributions) == 1
        assert contributions[0].transaction_id is None

    def test_add_contribution_to_completed_goal_raises_error(
        self, db_session, test_user
    ):
        """add_contribution в COMPLETED цель вызывает ValidationError."""
        from app.core import ValidationError
        from app.models.database import GoalStatus

        service = GoalService(db_session)
        goal = service.create_goal(
            user_id=test_user.id,
            name="Завершённая цель",
            target_amount=Decimal("10000"),
            target_date=date.today() + timedelta(days=30),
        )

        # Завершаем цель
        goal.status = GoalStatus.COMPLETED
        goal.current_amount = Decimal("10000")
        db_session.commit()

        with pytest.raises(ValidationError, match="завершенную цель"):
            service.add_contribution(goal.id, Decimal("1000"))


class TestUpdateSavingsBudgetWithSync:
    """Тесты для update_savings_budget с синхронизацией шаблона."""

    def test_update_budget_syncs_template_in_fixed_date_mode(
        self, db_session, test_user
    ):
        """update_savings_budget синхронизирует шаблон в режиме fixed_date."""
        from app.services.budget_reservation_service import BudgetReservationService
        from app.models.database import Transaction

        # Устанавливаем начальный бюджет и режим fixed_date
        test_user.monthly_savings_budget = Decimal("10000")
        db_session.commit()

        budget_service = BudgetReservationService(db_session)
        budget_service.set_mode(test_user.id, "fixed_date", day_of_month=15)
        db_session.commit()

        settings = budget_service.get_settings(test_user.id)
        template_id = settings["template_id"]

        # Обновляем бюджет через GoalService
        service = GoalService(db_session)
        service.update_savings_budget(test_user.id, Decimal("20000"))
        db_session.commit()

        # Проверяем что шаблон обновлён
        template = db_session.get(Transaction, template_id)
        assert template.amount == Decimal("20000")
