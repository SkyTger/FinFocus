"""Тесты для TransactionService."""

from datetime import date
from decimal import Decimal

import pytest

from app.core import ValidationError
from app.models.database import Category, TransactionType
from app.services.transaction_service import TransactionService


class TestTransactionServiceCreate:
    """Тесты создания транзакций."""

    def test_create_basic_transaction(self, db_session, test_user):
        """Создание базовой транзакции."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            description="Тестовая транзакция",
        )

        assert transaction.id is not None
        assert transaction.amount == Decimal("100.00")
        assert transaction.transaction_type == TransactionType.EXPENSE
        assert transaction.description == "Тестовая транзакция"

    def test_create_with_zero_amount_fails(self, db_session, test_user):
        """Нельзя создать транзакцию с нулевой суммой."""
        service = TransactionService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_transaction(
                user_id=test_user.id,
                amount=Decimal("0"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date.today(),
            )

        assert "больше 0" in str(exc_info.value)


class TestTransactionServiceCategoryId:
    """Тесты category_id в TransactionService."""

    def test_create_with_category_id(self, db_session, test_user):
        """Транзакция создается с category_id."""
        category = Category(name="Еда", type="expense")
        db_session.add(category)
        db_session.flush()

        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=category.id,
        )

        assert transaction.category_id == category.id

    def test_create_without_category_id(self, db_session, test_user):
        """Транзакция создается без category_id (nullable)."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )

        assert transaction.category_id is None

    def test_update_category_id(self, db_session, test_user):
        """category_id можно обновить."""
        category = Category(name="Еда", type="expense")
        db_session.add(category)
        db_session.flush()

        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )

        updated = service.update_transaction(
            transaction.id,
            category_id=category.id,
        )

        assert updated.category_id == category.id


class TestTransactionServiceAdjustmentValidation:
    """Тесты валидации ADJUSTMENT + recurring."""

    def test_adjustment_cannot_be_recurring(self, db_session, test_user):
        """ADJUSTMENT не может быть recurring."""
        service = TransactionService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_transaction(
                user_id=test_user.id,
                amount=Decimal("100.00"),
                transaction_type=TransactionType.ADJUSTMENT,
                transaction_date=date.today(),
                is_recurring=True,
                recurring_period="monthly",
            )

        assert "повторяющимися" in str(exc_info.value)

    def test_adjustment_single_allowed(self, db_session, test_user):
        """ADJUSTMENT без recurring создается успешно."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today(),
        )

        assert transaction.transaction_type == TransactionType.ADJUSTMENT
        assert transaction.is_recurring is False

    def test_update_to_adjustment_recurring_fails(self, db_session, test_user):
        """Нельзя обновить recurring транзакцию в ADJUSTMENT."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            is_recurring=True,
            recurring_period="monthly",
        )

        with pytest.raises(ValidationError) as exc_info:
            service.update_transaction(
                transaction.id,
                transaction_type=TransactionType.ADJUSTMENT,
            )

        assert "повторяющимися" in str(exc_info.value)

    def test_update_adjustment_to_recurring_fails(self, db_session, test_user):
        """Нельзя сделать ADJUSTMENT recurring через update."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today(),
        )

        with pytest.raises(ValidationError) as exc_info:
            service.update_transaction(
                transaction.id,
                is_recurring=True,
            )

        assert "повторяющимися" in str(exc_info.value)


class TestTransactionServiceUpdate:
    """Тесты обновления транзакций."""

    def test_update_amount(self, db_session, test_user):
        """Обновление суммы транзакции."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )

        updated = service.update_transaction(
            transaction.id,
            amount=Decimal("200.00"),
        )

        assert updated.amount == Decimal("200.00")

    def test_update_nonexistent_fails(self, db_session):
        """Обновление несуществующей транзакции."""
        service = TransactionService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.update_transaction(99999, amount=Decimal("100.00"))

        assert "не найдена" in str(exc_info.value)


class TestTransactionServiceDelete:
    """Тесты удаления транзакций."""

    def test_delete_existing(self, db_session, test_user):
        """Удаление существующей транзакции."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )

        result = service.delete_transaction(transaction.id)

        assert result is True
        assert service.get_by_id(transaction.id) is None

    def test_delete_nonexistent(self, db_session):
        """Удаление несуществующей транзакции возвращает False."""
        service = TransactionService(db_session)

        result = service.delete_transaction(99999)

        assert result is False


class TestBulkUpdateCategory:
    """Тесты метода bulk_update_category."""

    def test_bulk_update_success(self, db_session, test_user):
        """Успешное обновление 5 транзакций."""
        category = Category(name="Еда", type="expense")
        db_session.add(category)
        db_session.flush()

        service = TransactionService(db_session)

        # Создаем 5 транзакций без категории
        tx_ids = []
        for i in range(5):
            tx = service.create_transaction(
                user_id=test_user.id,
                amount=Decimal(f"{(i + 1) * 100}.00"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date.today(),
            )
            tx_ids.append(tx.id)

        # Массово обновляем категорию
        affected = service.bulk_update_category(
            user_id=test_user.id,
            transaction_ids=tx_ids,
            category_id=category.id,
        )

        assert affected == 5

        # Проверяем что все обновились
        for tx_id in tx_ids:
            tx = service.get_by_id(tx_id)
            assert tx.category_id == category.id

    def test_bulk_update_validates_ownership(self, db_session, test_user):
        """Проверка что user_id валидируется."""
        from app.models.database import User

        other_user = User(
            email="other@test.com",
            name="Other User",
            starting_balance=Decimal("0"),
        )
        db_session.add(other_user)
        db_session.flush()

        service = TransactionService(db_session)

        # Создаем транзакцию для test_user
        tx = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )

        # Пытаемся обновить от имени другого пользователя
        with pytest.raises(ValidationError) as exc_info:
            service.bulk_update_category(
                user_id=other_user.id,
                transaction_ids=[tx.id],
                category_id=None,
            )

        assert "принадлежат пользователю" in str(exc_info.value)

    def test_bulk_update_rejects_foreign_transactions(self, db_session, test_user):
        """ValidationError если транзакция чужая."""
        from app.models.database import User

        other_user = User(
            email="foreign@test.com",
            name="Foreign User",
            starting_balance=Decimal("0"),
        )
        db_session.add(other_user)
        db_session.flush()

        service = TransactionService(db_session)

        # Создаем транзакцию для другого пользователя
        tx_other = service.create_transaction(
            user_id=other_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )

        # Пытаемся обновить от имени test_user
        with pytest.raises(ValidationError):
            service.bulk_update_category(
                user_id=test_user.id,
                transaction_ids=[tx_other.id],
                category_id=None,
            )

    def test_bulk_update_exceeds_limit(self, db_session, test_user):
        """ValidationError при >100 записях."""
        from app.services.transaction_service import MAX_BULK_UPDATE_SIZE

        service = TransactionService(db_session)

        # Создаем список из 101 ID (больше лимита)
        tx_ids = list(range(1, MAX_BULK_UPDATE_SIZE + 2))

        with pytest.raises(ValidationError) as exc_info:
            service.bulk_update_category(
                user_id=test_user.id,
                transaction_ids=tx_ids,
                category_id=None,
            )

        assert str(MAX_BULK_UPDATE_SIZE) in str(exc_info.value)

    def test_bulk_update_invalid_category(self, db_session, test_user):
        """ValidationError при несуществующей категории."""
        service = TransactionService(db_session)

        tx = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )

        with pytest.raises(ValidationError) as exc_info:
            service.bulk_update_category(
                user_id=test_user.id,
                transaction_ids=[tx.id],
                category_id=99999,  # Несуществующая категория
            )

        assert "не найдена" in str(exc_info.value)

    def test_bulk_update_excludes_recurring_templates(self, db_session, test_user):
        """Шаблоны (is_recurring=True) не обновляются."""
        category = Category(name="Транспорт", type="expense")
        db_session.add(category)
        db_session.flush()

        service = TransactionService(db_session)

        # Создаем recurring шаблон
        template = service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            is_recurring=True,
            recurring_period="monthly",
        )

        # Пытаемся обновить шаблон
        with pytest.raises(ValidationError) as exc_info:
            service.bulk_update_category(
                user_id=test_user.id,
                transaction_ids=[template.id],
                category_id=category.id,
            )

        assert "шаблонами" in str(exc_info.value)

    def test_bulk_update_empty_list(self, db_session, test_user):
        """Пустой список возвращает 0."""
        service = TransactionService(db_session)

        affected = service.bulk_update_category(
            user_id=test_user.id,
            transaction_ids=[],
            category_id=None,
        )

        assert affected == 0


class TestExportToCsv:
    """Тесты метода export_to_csv."""

    def test_export_csv_utf8_bom(self, db_session, test_user):
        """Проверка что результат начинается с UTF-8 BOM."""
        service = TransactionService(db_session)

        # Создаем транзакцию
        service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            description="Тест",
        )

        csv_bytes = service.export_to_csv(user_id=test_user.id)

        # UTF-8 BOM: 0xEF, 0xBB, 0xBF
        assert csv_bytes[:3] == b"\xef\xbb\xbf"

    def test_export_csv_with_filters(self, db_session, test_user):
        """Проверка фильтров start_date, end_date."""
        service = TransactionService(db_session)

        # Создаем транзакции в разные даты
        service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 1),
            description="Январь",
        )
        service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("200.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 2, 1),
            description="Февраль",
        )

        # Экспортируем только январь
        csv_bytes = service.export_to_csv(
            user_id=test_user.id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        csv_content = csv_bytes.decode("utf-8-sig")
        assert "Январь" in csv_content
        assert "Февраль" not in csv_content

    def test_export_csv_uncategorized_only(self, db_session, test_user):
        """Проверка фильтра uncategorized_only."""
        category = Category(name="Еда", type="expense")
        db_session.add(category)
        db_session.flush()

        service = TransactionService(db_session)

        # С категорией
        service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            description="С категорией",
            category_id=category.id,
        )
        # Без категории
        service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("200.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            description="Без категории TX",
        )

        csv_bytes = service.export_to_csv(
            user_id=test_user.id,
            uncategorized_only=True,
        )

        csv_content = csv_bytes.decode("utf-8-sig")
        assert "Без категории TX" in csv_content
        assert "С категорией" not in csv_content

    def test_export_csv_correct_format(self, db_session, test_user):
        """Проверка формата и заголовков."""
        category = Category(name="Транспорт", type="expense")
        db_session.add(category)
        db_session.flush()

        service = TransactionService(db_session)

        service.create_transaction(
            user_id=test_user.id,
            amount=Decimal("500.50"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            description="Такси",
            category_id=category.id,
        )

        csv_bytes = service.export_to_csv(user_id=test_user.id)
        csv_content = csv_bytes.decode("utf-8-sig")
        lines = csv_content.strip().splitlines()  # splitlines handles CRLF

        # Проверяем заголовок
        assert lines[0] == "Дата,Тип,Сумма,Описание,Категория"

        # Проверяем данные
        assert "2026-01-15" in lines[1]
        assert "Расход" in lines[1]
        assert "500.50" in lines[1]
        assert "Такси" in lines[1]
        assert "Транспорт" in lines[1]

    def test_export_csv_empty(self, db_session, test_user):
        """Экспорт без транзакций возвращает только заголовок."""
        service = TransactionService(db_session)

        csv_bytes = service.export_to_csv(user_id=test_user.id)
        csv_content = csv_bytes.decode("utf-8-sig")
        lines = csv_content.strip().splitlines()  # splitlines handles CRLF

        # Только заголовок
        assert len(lines) == 1
        assert lines[0] == "Дата,Тип,Сумма,Описание,Категория"
