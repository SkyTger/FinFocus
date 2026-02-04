"""Unit тесты для PurchaseRecommendationService."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.models.database import Transaction, TransactionType
from app.services.purchase_recommendation_service import (
    PurchaseRecommendationService,
)


@pytest.fixture
def service(db_session):
    """Создаёт PurchaseRecommendationService."""
    return PurchaseRecommendationService(db_session)


def _add_income(db_session, user, amount, txn_date):
    """Хелпер: добавляет доходную транзакцию."""
    txn = Transaction(
        user_id=user.id,
        amount=Decimal(str(amount)),
        transaction_type=TransactionType.INCOME,
        transaction_date=txn_date,
        description="Test income",
    )
    db_session.add(txn)
    db_session.commit()


def _add_expense(db_session, user, amount, txn_date):
    """Хелпер: добавляет расходную транзакцию."""
    txn = Transaction(
        user_id=user.id,
        amount=Decimal(str(amount)),
        transaction_type=TransactionType.EXPENSE,
        transaction_date=txn_date,
        description="Test expense",
    )
    db_session.add(txn)
    db_session.commit()


# === get_safe_dates_map ===


@patch("app.services.purchase_recommendation_service.date")
def test_safe_dates_all_safe(mock_date, service, test_user):
    """Все дни безопасны при большом балансе."""
    mock_date.today.return_value = date(2026, 3, 1)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    # starting_balance=10000, покупка на 100
    result = service.get_safe_dates_map(test_user.id, Decimal("100"), 2026, 3)

    assert len(result) == 31  # все дни марта
    for info in result.values():
        assert info["safe"] is True
        assert info["reasons"] == []


@patch("app.services.purchase_recommendation_service.date")
def test_safe_dates_past_days_excluded(mock_date, service, test_user):
    """Прошлые дни не включаются."""
    mock_date.today.return_value = date(2026, 3, 15)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    result = service.get_safe_dates_map(test_user.id, Decimal("100"), 2026, 3)

    # Дни 1-14 не включены
    assert "2026-03-01" not in result
    assert "2026-03-14" not in result
    # Дни 15-31 включены
    assert "2026-03-15" in result
    assert "2026-03-31" in result
    assert len(result) == 17  # 15-31 = 17 дней


@patch("app.services.purchase_recommendation_service.date")
def test_safe_dates_negative_balance(mock_date, service, test_user_zero_balance, db_session):
    """Обнаружение отрицательного баланса."""
    mock_date.today.return_value = date(2026, 3, 1)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    # У пользователя баланс 0, покупка на 1000
    result = service.get_safe_dates_map(
        test_user_zero_balance.id, Decimal("1000"), 2026, 3
    )

    # Все дни unsafe
    for info in result.values():
        assert info["safe"] is False
        assert "negative_balance" in info["reasons"]


@patch("app.services.purchase_recommendation_service.date")
def test_safe_dates_cushion_threshold(mock_date, service, test_user, db_session):
    """Порог подушки безопасности учитывается."""
    mock_date.today.return_value = date(2026, 3, 1)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    # Настраиваем подушку: target=20000, threshold=30% → threshold_amount=6000
    test_user.cushion_target = Decimal("20000")
    test_user.cushion_threshold_percent = 30
    db_session.commit()

    # starting_balance=10000, покупка на 5000 → остаток 5000 < 6000 threshold
    result = service.get_safe_dates_map(test_user.id, Decimal("5000"), 2026, 3)

    for info in result.values():
        assert info["safe"] is False
        assert "cushion" in info["reasons"]


@patch("app.services.purchase_recommendation_service.date")
def test_safe_dates_mixed(mock_date, service, test_user, db_session):
    """Смешанный результат: safe и unsafe дни."""
    mock_date.today.return_value = date(2026, 3, 1)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    # Добавляем доход 20000 на 15 марта
    _add_income(db_session, test_user, 20000, date(2026, 3, 15))
    # Добавляем расход 25000 на 20 марта
    _add_expense(db_session, test_user, 25000, date(2026, 3, 20))

    # starting_balance=10000, покупка на 8000
    # До 15 марта: 10000 - 8000 = 2000 (OK)
    # После 15 марта: 30000 - 8000 = 22000 (OK)
    # Но после 20 марта: 5000 - 8000 = -3000 (NOT OK, если купить до 20го)
    result = service.get_safe_dates_map(test_user.id, Decimal("8000"), 2026, 3)

    # Дни до 15 марта unsafe (10000-8000=2000, но после 20 марта будет 5000-8000=-3000)
    assert result["2026-03-01"]["safe"] is False

    # Дни после 20 марта: 5000-8000=-3000 (unsafe)
    assert result["2026-03-20"]["safe"] is False


# === precalculate_hover_data ===


@patch("app.services.purchase_recommendation_service.date")
def test_hover_base_balances(mock_date, service, test_user):
    """base_balances содержит все дни месяца."""
    mock_date.today.return_value = date(2026, 3, 1)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    result = service.precalculate_hover_data(
        test_user.id, Decimal("100"), 2026, 3
    )

    assert len(result["base_balances"]) == 31  # все дни марта


@patch("app.services.purchase_recommendation_service.date")
def test_hover_by_candidate_excludes_past(mock_date, service, test_user):
    """by_candidate не содержит прошлые дни."""
    mock_date.today.return_value = date(2026, 3, 15)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    result = service.precalculate_hover_data(
        test_user.id, Decimal("100"), 2026, 3
    )

    assert "2026-03-01" not in result["by_candidate"]
    assert "2026-03-14" not in result["by_candidate"]
    assert "2026-03-15" in result["by_candidate"]


@patch("app.services.purchase_recommendation_service.date")
def test_hover_candidate_calculation(mock_date, service, test_user):
    """by_candidate корректно вычитает amount начиная с дня покупки."""
    mock_date.today.return_value = date(2026, 3, 1)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    amount = Decimal("1000")
    result = service.precalculate_hover_data(
        test_user.id, amount, 2026, 3
    )

    base = result["base_balances"]
    candidate_day5 = result["by_candidate"]["2026-03-05"]

    # До дня покупки — баланс не изменяется
    assert candidate_day5["2026-03-01"] == base["2026-03-01"]
    assert candidate_day5["2026-03-04"] == base["2026-03-04"]

    # С дня покупки — баланс уменьшен на amount
    # base: 10000, candidate: 10000 - 1000 = 9000
    assert candidate_day5["2026-03-05"] != base["2026-03-05"]
    assert candidate_day5["2026-03-31"] != base["2026-03-31"]


@patch("app.services.purchase_recommendation_service.date")
def test_hover_all_candidates_have_all_days(mock_date, service, test_user):
    """Каждый candidate содержит данные по всем дням месяца."""
    mock_date.today.return_value = date(2026, 3, 28)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    result = service.precalculate_hover_data(
        test_user.id, Decimal("100"), 2026, 3
    )

    for candidate_date, adjusted in result["by_candidate"].items():
        assert len(adjusted) == 31, (
            f"Candidate {candidate_date} should have 31 entries"
        )


@patch("app.services.purchase_recommendation_service.date")
def test_safe_dates_first_day_of_month(mock_date, service, test_user):
    """Первый день месяца корректно обрабатывается."""
    mock_date.today.return_value = date(2026, 3, 1)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    result = service.get_safe_dates_map(test_user.id, Decimal("100"), 2026, 3)
    assert "2026-03-01" in result


@patch("app.services.purchase_recommendation_service.date")
def test_safe_dates_last_day_of_month(mock_date, service, test_user):
    """Последний день месяца корректно обрабатывается."""
    mock_date.today.return_value = date(2026, 3, 31)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    result = service.get_safe_dates_map(test_user.id, Decimal("100"), 2026, 3)
    assert "2026-03-31" in result
    assert len(result) == 1
