"""Фикстуры для тестов FinFocus."""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, User


@pytest.fixture(scope="function")
def db_engine():
    """Создает in-memory SQLite engine для тестов."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Создает сессию БД для тестов."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_user(db_session) -> User:
    """Создает тестового пользователя с starting_balance=10000."""
    user = User(
        email="test@example.com",
        name="Test User",
        starting_balance=Decimal("10000.00"),
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_user_zero_balance(db_session) -> User:
    """Создает тестового пользователя с starting_balance=0."""
    user = User(
        email="zero@example.com",
        name="Zero Balance User",
        starting_balance=Decimal("0"),
    )
    db_session.add(user)
    db_session.commit()
    return user


# ---------------------------------------------------------------------------
# Хелперы для дат, устойчивых к течению календарного времени
#
# Сервисы (BudgetReservationService, Goal.monthly_contribution) строят свои
# расчёты от date.today(). Захардкоженные даты в тестах "протухают": тест,
# зелёный в феврале, падает в августе. Хелперы ниже привязывают тестовые
# даты к текущему дню, поэтому тесты остаются валидными в любой момент.
# ---------------------------------------------------------------------------


def reserve_period_start(day_of_month: int, today: date | None = None) -> date:
    """Возвращает дату резерва, которую создаст BudgetReservationService.

    Повторяет Anchored-логику _create_reserve_template(): если день месяца
    уже прошёл, резерв стартует со следующего месяца; день обрезается по
    длине месяца.

    Args:
        day_of_month: День месяца резерва (1-31).
        today: Опорная дата (default: date.today()).

    Returns:
        date: Дата первого экземпляра резерва.
    """
    if today is None:
        today = date.today()

    _, last_day = monthrange(today.year, today.month)
    start = date(today.year, today.month, min(day_of_month, last_day))

    if start < today:
        if today.month == 12:
            nxt = date(today.year + 1, 1, 1)
        else:
            nxt = date(today.year, today.month + 1, 1)
        _, next_last = monthrange(nxt.year, nxt.month)
        start = date(nxt.year, nxt.month, min(day_of_month, next_last))

    return start


def days_before(reference: date, days: int = 1) -> date:
    """Дата на N дней раньше reference."""
    return reference - timedelta(days=days)


def days_after(reference: date, days: int = 1) -> date:
    """Дата на N дней позже reference."""
    return reference + timedelta(days=days)


def far_future_date(years: int = 1) -> date:
    """Дата заведомо в будущем — для target_date целей.

    Использует 31 декабря через `years` лет от текущего года, чтобы
    target_date никогда не оказался в прошлом.
    """
    return date(date.today().year + years, 12, 31)


def months_ahead(months: int) -> date:
    """Дата примерно через `months` месяцев от сегодня.

    Нужна тестам, чьи ожидания зависят от размера monthly_contribution:
    Goal.monthly_contribution делит остаток на (дни до target_date / 30),
    поэтому фиксированный target_date "протухает" по мере приближения.

    Args:
        months: Сколько месяцев отсчитать вперёд.

    Returns:
        date: Дата через указанное число месяцев (30 дней = месяц).
    """
    return date.today() + timedelta(days=30 * months)


def upcoming_reserve_day(min_gap_days: int = 2) -> int:
    """Подбирает день месяца для резерва, который ещё не прошёл.

    Заменяет паттерн `if today.day >= reserve_day: pytest.skip(...)`:
    вместо самоотключения теста в конце месяца день резерва выбирается
    относительно сегодняшней даты, поэтому сценарий "взнос до даты
    резерва" воспроизводится в любой день.

    В конце месяца (когда до конца осталось меньше min_gap_days) резерв
    неизбежно уезжает в следующий месяц — BudgetReservationService
    переносит серию вперёд, если день уже прошёл. Это нормально: месяц
    резерва нужно брать из reserve_period_start(day), а не считать
    текущим. Тест остаётся валидным, просто работает со следующим месяцем.

    Args:
        min_gap_days: Желаемый зазор между сегодня и днём резерва.

    Returns:
        int: День месяца (1-28) — существует в любом месяце, включая февраль.
    """
    today = date.today()
    candidate = today.day + min_gap_days

    # Держимся в пределах 28, чтобы день существовал в любом месяце.
    # Если зазор не влезает в текущий месяц, берём ранний день —
    # резерв уедет в следующий месяц, и это учтено вызывающим кодом.
    if candidate > 28:
        return min(min_gap_days, 28)

    return candidate
