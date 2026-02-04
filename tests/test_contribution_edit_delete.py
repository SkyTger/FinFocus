"""Тесты для update_contribution() и delete_contribution() в GoalService."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.models.database import GoalContribution, GoalStatus, Transaction, TransactionType
from app.services.goal_service import GoalService


# ─── Helpers ────────────────────────────────────────────────────────────────

def _create_goal_with_contribution(
    db_session, test_user, amount=Decimal("5000"), target=Decimal("50000"),
    contribution_date=None, description="Тестовый взнос",
):
    """Создает цель и один взнос, возвращает (goal, contribution)."""
    service = GoalService(db_session)
    goal = service.create_goal(
        user_id=test_user.id,
        name="Тестовая цель",
        target_amount=target,
        target_date=date.today() + timedelta(days=90),
    )
    db_session.flush()

    goal = service.add_contribution(
        goal_id=goal.id,
        amount=amount,
        contribution_date=contribution_date or date.today(),
        description=description,
    )
    db_session.flush()

    contribution = service.get_contributions(goal.id, limit=1)[0]
    return goal, contribution


# ─── update_contribution: Amount ────────────────────────────────────────────


class TestUpdateContributionAmount:
    """Тесты обновления суммы взноса."""

    def test_update_contribution_amount_increase(self, db_session, test_user):
        """Увеличение суммы → goal.current_amount увеличивается."""
        goal, contrib = _create_goal_with_contribution(db_session, test_user)
        service = GoalService(db_session)

        result = service.update_contribution(
            contribution_id=contrib.id,
            amount=Decimal("8000"),
        )

        assert result["success"] is True
        assert result["goal"].current_amount == Decimal("8000")

    def test_update_contribution_amount_decrease(self, db_session, test_user):
        """Уменьшение суммы → goal.current_amount уменьшается."""
        goal, contrib = _create_goal_with_contribution(db_session, test_user)
        service = GoalService(db_session)

        result = service.update_contribution(
            contribution_id=contrib.id,
            amount=Decimal("2000"),
        )

        assert result["success"] is True
        assert result["goal"].current_amount == Decimal("2000")

    def test_update_contribution_amount_zero_error(self, db_session, test_user):
        """amount=0 → error."""
        goal, contrib = _create_goal_with_contribution(db_session, test_user)
        service = GoalService(db_session)

        result = service.update_contribution(
            contribution_id=contrib.id,
            amount=Decimal("0"),
        )

        assert result["success"] is False
        assert "больше 0" in result["error"]

    def test_update_contribution_amount_negative_error(self, db_session, test_user):
        """amount<0 → error."""
        goal, contrib = _create_goal_with_contribution(db_session, test_user)
        service = GoalService(db_session)

        result = service.update_contribution(
            contribution_id=contrib.id,
            amount=Decimal("-100"),
        )

        assert result["success"] is False
        assert "больше 0" in result["error"]


# ─── update_contribution: Date ──────────────────────────────────────────────


class TestUpdateContributionDate:
    """Тесты обновления даты взноса."""

    def test_update_contribution_date_within_month(self, db_session, test_user):
        """Смена даты в рамках текущего месяца → success."""
        today = date.today()
        goal, contrib = _create_goal_with_contribution(
            db_session, test_user, contribution_date=today,
        )
        service = GoalService(db_session)

        # Другой день в текущем месяце
        new_date = today.replace(day=1)

        result = service.update_contribution(
            contribution_id=contrib.id,
            contribution_date=new_date,
        )

        assert result["success"] is True

    def test_update_contribution_date_across_months_recalculates_exception(
        self, db_session, test_user
    ):
        """Смена даты между месяцами → recalculate для обоих месяцев."""
        today = date.today()
        goal, contrib = _create_goal_with_contribution(
            db_session, test_user, contribution_date=today,
        )
        service = GoalService(db_session)

        # Следующий месяц
        if today.month < 12:
            new_date = today.replace(month=today.month + 1, day=1)
        else:
            new_date = today.replace(year=today.year + 1, month=1, day=1)

        with patch.object(service, "_get_budget_service") as mock_budget:
            mock_svc = mock_budget.return_value
            result = service.update_contribution(
                contribution_id=contrib.id,
                contribution_date=new_date,
            )

        assert result["success"] is True
        assert mock_svc.recalculate_current_month_exception.call_count == 2

    def test_update_contribution_date_past_month_error(self, db_session, test_user):
        """Guard #2a: дата в прошлом месяце → error."""
        goal, contrib = _create_goal_with_contribution(db_session, test_user)
        service = GoalService(db_session)

        today = date.today()
        if today.month > 1:
            past_date = today.replace(month=today.month - 1, day=1)
        else:
            past_date = today.replace(year=today.year - 1, month=12, day=1)

        result = service.update_contribution(
            contribution_id=contrib.id,
            contribution_date=past_date,
        )

        assert result["success"] is False
        assert "прошлом месяце" in result["error"]

    def test_update_contribution_date_none_no_recalculate(self, db_session, test_user):
        """date=None → не пересчитывать Exception."""
        goal, contrib = _create_goal_with_contribution(db_session, test_user)
        service = GoalService(db_session)

        with patch.object(service, "_get_budget_service") as mock_budget:
            result = service.update_contribution(
                contribution_id=contrib.id,
                amount=Decimal("6000"),
                contribution_date=None,
            )

        assert result["success"] is True
        mock_budget.return_value.recalculate_current_month_exception.assert_not_called()

    def test_update_contribution_date_far_future_error(self, db_session, test_user):
        """Guard #2b: дата через 2+ месяца → error."""
        goal, contrib = _create_goal_with_contribution(db_session, test_user)
        service = GoalService(db_session)

        today = date.today()
        far_future = today.replace(year=today.year + 1)

        result = service.update_contribution(
            contribution_id=contrib.id,
            contribution_date=far_future,
        )

        assert result["success"] is False
        assert "через месяц" in result["error"]

    def test_update_contribution_date_next_month_ok(self, db_session, test_user):
        """Дата в следующем месяце → ok."""
        goal, contrib = _create_goal_with_contribution(db_session, test_user)
        service = GoalService(db_session)

        today = date.today()
        if today.month < 12:
            next_month = today.replace(month=today.month + 1, day=1)
        else:
            next_month = today.replace(year=today.year + 1, month=1, day=1)

        result = service.update_contribution(
            contribution_id=contrib.id,
            contribution_date=next_month,
        )

        assert result["success"] is True


# ─── update_contribution: Description ───────────────────────────────────────


class TestUpdateContributionDescription:
    """Тесты обновления описания взноса."""

    def test_update_contribution_description_sync_transaction(
        self, db_session, test_user
    ):
        """Описание синхронизируется с Transaction."""
        goal, contrib = _create_goal_with_contribution(db_session, test_user)

        # Проверяем что transaction_id существует
        if not contrib.transaction_id:
            pytest.skip("No transaction_id on contribution (fixed_date mode)")

        service = GoalService(db_session)
        result = service.update_contribution(
            contribution_id=contrib.id,
            description="Новое описание",
        )

        assert result["success"] is True
        txn = db_session.get(Transaction, contrib.transaction_id)
        assert txn.description == "Новое описание"

    def test_update_contribution_description_empty_string_clears(
        self, db_session, test_user
    ):
        """Пустая строка → очистить описание (Transaction = default)."""
        goal, contrib = _create_goal_with_contribution(
            db_session, test_user, description="Старое описание"
        )
        service = GoalService(db_session)

        result = service.update_contribution(
            contribution_id=contrib.id,
            description="",
        )

        assert result["success"] is True
        # GoalContribution.description → None
        updated_contrib = db_session.get(GoalContribution, contrib.id)
        assert updated_contrib.description is None

    def test_update_contribution_description_none_no_change(
        self, db_session, test_user
    ):
        """None → не изменять описание."""
        goal, contrib = _create_goal_with_contribution(
            db_session, test_user, description="Оригинал"
        )
        service = GoalService(db_session)

        result = service.update_contribution(
            contribution_id=contrib.id,
            amount=Decimal("6000"),
            description=None,
        )

        assert result["success"] is True
        updated_contrib = db_session.get(GoalContribution, contrib.id)
        assert updated_contrib.description == "Оригинал"


# ─── update_contribution: Status ────────────────────────────────────────────


class TestUpdateContributionStatus:
    """Тесты изменения статуса цели при обновлении взноса."""

    def test_update_contribution_status_completed_to_active(
        self, db_session, test_user
    ):
        """Уменьшение суммы → COMPLETED→ACTIVE."""
        goal, contrib = _create_goal_with_contribution(
            db_session, test_user,
            amount=Decimal("10000"), target=Decimal("10000"),
        )
        assert goal.status == GoalStatus.COMPLETED

        service = GoalService(db_session)
        result = service.update_contribution(
            contribution_id=contrib.id,
            amount=Decimal("5000"),
        )

        assert result["success"] is True
        assert result["status_changed"] is True
        assert result["new_status"] == "active"
        assert result["goal"].status == GoalStatus.ACTIVE

    def test_update_contribution_status_active_to_completed(
        self, db_session, test_user
    ):
        """Увеличение до target → ACTIVE→COMPLETED."""
        goal, contrib = _create_goal_with_contribution(
            db_session, test_user,
            amount=Decimal("5000"), target=Decimal("10000"),
        )
        assert goal.status == GoalStatus.ACTIVE

        service = GoalService(db_session)
        result = service.update_contribution(
            contribution_id=contrib.id,
            amount=Decimal("10000"),
        )

        assert result["success"] is True
        assert result["status_changed"] is True
        assert result["new_status"] == "completed"
        assert result["goal"].status == GoalStatus.COMPLETED

    def test_update_contribution_exact_boundary_active(self, db_session, test_user):
        """Сумма точно на границе (current == target) → completed."""
        goal, contrib = _create_goal_with_contribution(
            db_session, test_user,
            amount=Decimal("5000"), target=Decimal("10000"),
        )
        service = GoalService(db_session)

        # Exactly equal to target
        result = service.update_contribution(
            contribution_id=contrib.id,
            amount=Decimal("10000"),
        )

        assert result["success"] is True
        assert result["goal"].current_amount == Decimal("10000")
        assert result["goal"].status == GoalStatus.COMPLETED


# ─── update_contribution: Error ─────────────────────────────────────────────


class TestUpdateContributionError:
    """Тесты ошибок."""

    def test_update_contribution_not_found(self, db_session, test_user):
        """Несуществующий ID → error."""
        service = GoalService(db_session)

        result = service.update_contribution(
            contribution_id=999999,
            amount=Decimal("100"),
        )

        assert result["success"] is False
        assert "не найден" in result["error"]


# ─── delete_contribution ────────────────────────────────────────────────────


class TestDeleteContribution:
    """Тесты удаления взносов."""

    def test_delete_contribution_with_transaction_id_reverts_status(
        self, db_session, test_user
    ):
        """Удаление с transaction_id → COMPLETED→ACTIVE."""
        goal, contrib = _create_goal_with_contribution(
            db_session, test_user,
            amount=Decimal("10000"), target=Decimal("10000"),
        )
        assert goal.status == GoalStatus.COMPLETED
        # Might have transaction_id depending on mode

        service = GoalService(db_session)
        result = service.delete_contribution(contrib.id)

        assert result["success"] is True
        assert result["status_changed"] is True
        assert result["new_status"] == "active"
        assert result["goal"].status == GoalStatus.ACTIVE
        assert result["goal"].current_amount == Decimal("0")

    def test_delete_contribution_without_transaction_id_reverts_status(
        self, db_session, test_user
    ):
        """Удаление взноса без transaction_id → COMPLETED→ACTIVE."""
        service = GoalService(db_session)
        goal = service.create_goal(
            user_id=test_user.id,
            name="Тестовая цель",
            target_amount=Decimal("5000"),
            target_date=date.today() + timedelta(days=90),
        )
        db_session.flush()

        # Создаем GoalContribution напрямую (без transaction_id)
        contrib = GoalContribution(
            goal_id=goal.id,
            amount=Decimal("5000"),
            contribution_date=date.today(),
            description="Manual",
            transaction_id=None,
        )
        db_session.add(contrib)
        goal.current_amount = Decimal("5000")
        goal.status = GoalStatus.COMPLETED
        db_session.flush()

        result = service.delete_contribution(contrib.id)

        assert result["success"] is True
        assert result["status_changed"] is True
        assert result["new_status"] == "active"

    def test_delete_contribution_returns_contribution_info(
        self, db_session, test_user
    ):
        """Проверяет ВСЕ 4 поля ContributionInfo."""
        today = date.today()
        goal, contrib = _create_goal_with_contribution(
            db_session, test_user,
            amount=Decimal("5000"),
            contribution_date=today,
        )
        contribution_id = contrib.id

        service = GoalService(db_session)
        result = service.delete_contribution(contribution_id)

        assert result["success"] is True
        assert result["contribution_info"] is not None

        info = result["contribution_info"]
        assert info["contribution_id"] == contribution_id
        assert info["amount"] == Decimal("5000")
        assert info["contribution_date"] == today
        assert info["goal_name"] == "Тестовая цель"

    def test_delete_contribution_recalculates_exception(self, db_session, test_user):
        """recalculate_current_month_exception вызывается при удалении."""
        goal, contrib = _create_goal_with_contribution(db_session, test_user)
        service = GoalService(db_session)

        with patch.object(service, "_get_budget_service") as mock_budget:
            mock_svc = mock_budget.return_value
            service.delete_contribution(contrib.id)

        mock_svc.recalculate_current_month_exception.assert_called_once()

    def test_delete_contribution_with_transaction_no_double_decrement(
        self, db_session, test_user
    ):
        """Вариант A: current_amount уменьшается ровно на сумму взноса (не x2)."""
        goal, contrib = _create_goal_with_contribution(
            db_session, test_user,
            amount=Decimal("3000"), target=Decimal("50000"),
        )
        initial_amount = goal.current_amount
        assert initial_amount == Decimal("3000")

        service = GoalService(db_session)
        result = service.delete_contribution(contrib.id)

        assert result["success"] is True
        # current_amount should be 0, NOT -3000
        assert result["goal"].current_amount == Decimal("0")


# ─── delete_contribution: Not Found ─────────────────────────────────────────


class TestDeleteContributionNotFound:
    """Тесты для несуществующего взноса."""

    def test_delete_contribution_not_found(self, db_session, test_user):
        """Несуществующий ID → error."""
        service = GoalService(db_session)
        result = service.delete_contribution(999999)

        assert result["success"] is False
        assert "не найден" in result["error"]
