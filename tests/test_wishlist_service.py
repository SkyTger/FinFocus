"""Unit тесты для WishlistService."""

from datetime import date
from decimal import Decimal

import pytest

from app.core import ValidationError
from app.models.database import Category
from app.services.wishlist_service import WishlistService


@pytest.fixture
def service(db_session):
    """Создаёт WishlistService."""
    return WishlistService(db_session)


@pytest.fixture
def category(db_session):
    """Создаёт тестовую категорию."""
    cat = Category(name="Электроника", icon="bi-phone", type="expense")
    db_session.add(cat)
    db_session.commit()
    return cat


# === create_item ===


def test_create_item_happy_path(service, test_user):
    """Создание покупки с валидными данными."""
    item = service.create_item(
        user_id=test_user.id,
        name="iPhone 16",
        amount=Decimal("99990.00"),
    )
    assert item.id is not None
    assert item.name == "iPhone 16"
    assert item.amount == Decimal("99990.00")
    assert item.priority == 1
    assert item.status == "new"
    assert item.planned_date is None
    assert item.planned_transaction_id is None


def test_create_item_with_category(service, test_user, category):
    """Создание покупки с категорией."""
    item = service.create_item(
        user_id=test_user.id,
        name="Наушники",
        amount=Decimal("5000"),
        category_id=category.id,
    )
    assert item.category_id == category.id


def test_create_item_with_priority_2(service, test_user):
    """Создание покупки с приоритетом 2 (обычная)."""
    item = service.create_item(
        user_id=test_user.id,
        name="Кресло",
        amount=Decimal("15000"),
        priority=2,
    )
    assert item.priority == 2


def test_create_item_empty_name_raises(service, test_user):
    """Пустое имя вызывает ValidationError."""
    with pytest.raises(ValidationError, match="не может быть пустым"):
        service.create_item(test_user.id, "", Decimal("100"))


def test_create_item_whitespace_name_raises(service, test_user):
    """Имя из пробелов вызывает ValidationError."""
    with pytest.raises(ValidationError, match="не может быть пустым"):
        service.create_item(test_user.id, "   ", Decimal("100"))


def test_create_item_long_name_raises(service, test_user):
    """Имя > 100 символов вызывает ValidationError."""
    with pytest.raises(ValidationError, match="длиннее 100"):
        service.create_item(test_user.id, "A" * 101, Decimal("100"))


def test_create_item_name_stripped(service, test_user):
    """Имя обрезается от пробелов."""
    item = service.create_item(test_user.id, "  Телефон  ", Decimal("100"))
    assert item.name == "Телефон"


def test_create_item_zero_amount_raises(service, test_user):
    """amount=0 вызывает ValidationError."""
    with pytest.raises(ValidationError, match="больше 0"):
        service.create_item(test_user.id, "Тест", Decimal("0"))


def test_create_item_negative_amount_raises(service, test_user):
    """Отрицательная сумма вызывает ValidationError."""
    with pytest.raises(ValidationError, match="больше 0"):
        service.create_item(test_user.id, "Тест", Decimal("-100"))


def test_create_item_bad_priority_raises(service, test_user):
    """Невалидный приоритет вызывает ValidationError."""
    with pytest.raises(ValidationError, match="Приоритет"):
        service.create_item(test_user.id, "Тест", Decimal("100"), priority=3)


# === get_all ===


def test_get_all_sorted_by_priority_and_date(service, test_user):
    """Элементы отсортированы по priority ASC, created_at ASC."""
    service.create_item(test_user.id, "P2 first", Decimal("100"), priority=2)
    service.create_item(test_user.id, "P1 first", Decimal("200"), priority=1)
    service.create_item(test_user.id, "P1 second", Decimal("300"), priority=1)

    items = service.get_all(test_user.id)
    assert len(items) == 3
    assert items[0].name == "P1 first"
    assert items[1].name == "P1 second"
    assert items[2].name == "P2 first"


def test_get_all_empty(service, test_user):
    """Пустой список для пользователя без покупок."""
    assert service.get_all(test_user.id) == []


# === get_focus ===


def test_get_focus_only_priority_1(service, test_user):
    """get_focus возвращает только priority=1."""
    service.create_item(test_user.id, "Focus", Decimal("100"), priority=1)
    service.create_item(test_user.id, "Normal", Decimal("200"), priority=2)

    focus = service.get_focus(test_user.id)
    assert len(focus) == 1
    assert focus[0].name == "Focus"


def test_get_focus_limit(service, test_user):
    """get_focus ограничивает количество."""
    for i in range(10):
        service.create_item(test_user.id, f"Item {i}", Decimal("100"))

    focus = service.get_focus(test_user.id, limit=3)
    assert len(focus) == 3


# === get_by_id ===


def test_get_by_id_found(service, test_user):
    """Найден существующий элемент."""
    item = service.create_item(test_user.id, "Test", Decimal("100"))
    found = service.get_by_id(item.id)
    assert found is not None
    assert found.id == item.id


def test_get_by_id_not_found(service):
    """Возвращает None для несуществующего ID."""
    assert service.get_by_id(99999) is None


# === update_item ===


def test_update_item_name_and_amount(service, test_user):
    """Обновление name и amount для status=new."""
    item = service.create_item(test_user.id, "Old", Decimal("100"))
    updated = service.update_item(item.id, name="New", amount=Decimal("200"))
    assert updated.name == "New"
    assert updated.amount == Decimal("200")


def test_update_item_planned_guard_allows_name(service, test_user, db_session):
    """Для planned разрешено менять name."""
    item = service.create_item(test_user.id, "Test", Decimal("100"))
    item.status = "planned"
    db_session.flush()

    updated = service.update_item(item.id, name="New Name")
    assert updated.name == "New Name"


def test_update_item_planned_guard_allows_priority(service, test_user, db_session):
    """Для planned разрешено менять priority."""
    item = service.create_item(test_user.id, "Test", Decimal("100"))
    item.status = "planned"
    db_session.flush()

    updated = service.update_item(item.id, priority=2)
    assert updated.priority == 2


def test_update_item_planned_guard_blocks_amount(service, test_user, db_session):
    """Для planned нельзя менять amount."""
    item = service.create_item(test_user.id, "Test", Decimal("100"))
    item.status = "planned"
    db_session.flush()

    with pytest.raises(ValidationError, match="Нельзя изменить"):
        service.update_item(item.id, amount=Decimal("200"))


def test_update_item_planned_guard_blocks_category(service, test_user, db_session):
    """Для planned нельзя менять category_id."""
    item = service.create_item(test_user.id, "Test", Decimal("100"))
    item.status = "planned"
    db_session.flush()

    with pytest.raises(ValidationError, match="Нельзя изменить"):
        service.update_item(item.id, category_id=1)


def test_update_item_not_found(service):
    """Обновление несуществующего элемента."""
    with pytest.raises(ValidationError, match="не найдена"):
        service.update_item(99999, name="Test")


# === mark_as_planned ===


def test_mark_as_planned(service, test_user):
    """Пометка как запланированной."""
    item = service.create_item(test_user.id, "TV", Decimal("50000"))
    planned = service.mark_as_planned(item.id, date(2026, 3, 15), 42)

    assert planned.status == "planned"
    assert planned.planned_date == date(2026, 3, 15)
    assert planned.planned_transaction_id == 42


def test_mark_as_planned_not_found(service):
    """mark_as_planned для несуществующего элемента."""
    with pytest.raises(ValidationError, match="не найдена"):
        service.mark_as_planned(99999, date(2026, 1, 1), 1)


# === reset_planned ===


def test_reset_planned(service, test_user):
    """Сброс planned → new."""
    item = service.create_item(test_user.id, "TV", Decimal("50000"))
    service.mark_as_planned(item.id, date(2026, 3, 15), 42)
    reset = service.reset_planned(item.id)

    assert reset.status == "new"
    assert reset.planned_date is None
    assert reset.planned_transaction_id is None


# === delete_item ===


def test_delete_item_happy_path(service, test_user):
    """Удаление существующего элемента."""
    item = service.create_item(test_user.id, "Test", Decimal("100"))
    assert service.delete_item(item.id) is True
    assert service.get_by_id(item.id) is None


def test_delete_item_not_found(service):
    """Удаление несуществующего элемента."""
    assert service.delete_item(99999) is False


# === check_orphaned_planned ===


def test_check_orphaned_planned_found(service, test_user, db_session):
    """Обнаружение осиротевших planned-покупок."""
    item = service.create_item(test_user.id, "Test", Decimal("100"))
    item.status = "planned"
    item.planned_date = date(2026, 3, 1)
    item.planned_transaction_id = None  # Orphan
    db_session.flush()

    orphans = service.check_orphaned_planned(test_user.id)
    assert len(orphans) == 1
    assert orphans[0].id == item.id


def test_check_orphaned_planned_none(service, test_user):
    """Нет осиротевших покупок."""
    service.create_item(test_user.id, "Test", Decimal("100"))
    orphans = service.check_orphaned_planned(test_user.id)
    assert len(orphans) == 0


# === to_data ===


def test_to_data_mapping(service, test_user, category):
    """Маппинг ORM → TypedDict."""
    item = service.create_item(
        test_user.id, "Laptop", Decimal("120000"), category_id=category.id
    )
    data = service.to_data(item)

    assert data["id"] == item.id
    assert data["name"] == "Laptop"
    assert data["category_id"] == category.id
    assert data["category_name"] == "Электроника"
    assert data["category_icon"] == "bi-phone"
    assert data["priority"] == 1
    assert data["status"] == "new"
    assert data["planned_date"] is None
    assert data["planned_transaction_id"] is None


def test_to_data_no_category(service, test_user):
    """Маппинг без категории."""
    item = service.create_item(test_user.id, "Test", Decimal("100"))
    data = service.to_data(item)

    assert data["category_id"] is None
    assert data["category_name"] is None
    assert data["category_icon"] is None
