"""Unit тесты для RecurringService.

Тестирование Anchored-алгоритма генерации виртуальных экземпляров
из шаблонов повторяющихся операций.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from app.models.database import Transaction, TransactionType
from app.services.recurring_service import RecurringService


class TestGetTemplatesForUser:
    """Тесты для метода get_templates_for_user."""

    def test_empty_when_no_templates(self, db_session, test_user):
        """Возвращает пустой список если нет шаблонов."""
        service = RecurringService(db_session)
        templates = service.get_templates_for_user(test_user.id)
        assert templates == []

    def test_filters_non_recurring(self, db_session, test_user):
        """Фильтрует обычные (не-recurring) транзакции."""
        # Создаем обычную транзакцию
        regular = Transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            description="Обычная транзакция",
            is_recurring=False,
        )
        # Создаем recurring шаблон
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 15),
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add_all([regular, template])
        db_session.commit()

        service = RecurringService(db_session)
        templates = service.get_templates_for_user(test_user.id)

        assert len(templates) == 1
        assert templates[0].id == template.id

    def test_filters_exceptions(self, db_session, test_user):
        """Фильтрует exceptions (транзакции с recurring_parent_id)."""
        # Создаем шаблон
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 15),
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add(template)
        db_session.commit()

        # Создаем exception
        exception = Transaction(
            user_id=test_user.id,
            amount=Decimal("5500.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 2, 15),
            description="Зарплата с премией",
            recurring_parent_id=template.id,
            original_date=date(2026, 2, 15),
        )
        db_session.add(exception)
        db_session.commit()

        service = RecurringService(db_session)
        templates = service.get_templates_for_user(test_user.id)

        assert len(templates) == 1
        assert templates[0].id == template.id


class TestGenerateInstancesMonthly:
    """Тесты для monthly генерации с Anchored-алгоритмом."""

    def test_monthly_anchored_31st(self, db_session, test_user):
        """Anchored-алгоритм: 31 января → 28 февраля → 31 марта."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 31),  # anchor_day = 31
            description="Аренда",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )

        assert len(instances) == 3
        assert instances[0]["instance_date"] == "2026-01-31"
        assert instances[1]["instance_date"] == "2026-02-28"  # Anchored!
        assert instances[2]["instance_date"] == "2026-03-31"  # Возврат к 31

    def test_monthly_normal_15th(self, db_session, test_user):
        """Monthly с anchor_day=15 — без корректировки."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 15),
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 4, 30),
        )

        assert len(instances) == 4
        assert instances[0]["instance_date"] == "2026-01-15"
        assert instances[1]["instance_date"] == "2026-02-15"
        assert instances[2]["instance_date"] == "2026-03-15"
        assert instances[3]["instance_date"] == "2026-04-15"


class TestGenerateInstancesWeekly:
    """Тесты для weekly/biweekly генерации."""

    def test_weekly_generation(self, db_session, test_user):
        """Weekly генерирует каждые 7 дней."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 6),  # Вторник
            description="Продукты",
            is_recurring=True,
            recurring_period="weekly",
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        # 6, 13, 20, 27 января
        assert len(instances) == 4
        assert instances[0]["instance_date"] == "2026-01-06"
        assert instances[1]["instance_date"] == "2026-01-13"
        assert instances[2]["instance_date"] == "2026-01-20"
        assert instances[3]["instance_date"] == "2026-01-27"

    def test_biweekly_generation(self, db_session, test_user):
        """Biweekly генерирует каждые 14 дней."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("2500.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 10),
            description="Аванс",
            is_recurring=True,
            recurring_period="biweekly",
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 28),
        )

        # 10, 24 января; 7, 21 февраля
        assert len(instances) == 4
        assert instances[0]["instance_date"] == "2026-01-10"
        assert instances[1]["instance_date"] == "2026-01-24"
        assert instances[2]["instance_date"] == "2026-02-07"
        assert instances[3]["instance_date"] == "2026-02-21"


class TestGenerateInstancesQuarterly:
    """Тесты для quarterly генерации."""

    def test_quarterly_generation(self, db_session, test_user):
        """Quarterly генерирует каждые 3 месяца."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("15000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            description="Квартальный налог",
            is_recurring=True,
            recurring_period="quarterly",
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        # 15 января, 15 апреля, 15 июля, 15 октября
        assert len(instances) == 4
        assert instances[0]["instance_date"] == "2026-01-15"
        assert instances[1]["instance_date"] == "2026-04-15"
        assert instances[2]["instance_date"] == "2026-07-15"
        assert instances[3]["instance_date"] == "2026-10-15"


class TestGenerateInstancesEndDate:
    """Тесты для recurring_end_date."""

    def test_respects_recurring_end_date(self, db_session, test_user):
        """Учитывает recurring_end_date и останавливает генерацию."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            description="Подписка",
            is_recurring=True,
            recurring_period="monthly",
            recurring_end_date=date(2026, 3, 1),  # Заканчивается 1 марта
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        # Только январь и февраль (март уже после end_date)
        assert len(instances) == 2
        assert instances[0]["instance_date"] == "2026-01-15"
        assert instances[1]["instance_date"] == "2026-02-15"


class TestGenerateInstancesLimits:
    """Тесты для лимитов и защиты."""

    def test_max_instances_limit(self, db_session, test_user):
        """Проверка MAX_INSTANCES_PER_CALL ограничения."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("10.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2020, 1, 1),
            description="Ежедневно (тест лимита)",
            is_recurring=True,
            recurring_period="weekly",  # Еженедельно
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)

        # Запрашиваем на 30 лет вперед (более 1500 недель)
        with patch("app.services.recurring_service.MAX_INSTANCES_PER_CALL", 10):
            instances = service.generate_instances(
                template,
                start_date=date(2020, 1, 1),
                end_date=date(2050, 12, 31),
            )
            # Должно быть ограничено до 10
            assert len(instances) <= 10


class TestGenerateInstancesInvalid:
    """Тесты для невалидных входных данных."""

    def test_invalid_template_not_recurring(self, db_session, test_user):
        """Не-recurring шаблон возвращает пустой список."""
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            description="Обычная транзакция",
            is_recurring=False,
        )
        db_session.add(transaction)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            transaction,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        assert instances == []

    def test_invalid_period(self, db_session, test_user):
        """Невалидный период возвращает пустой список."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            description="Невалидный период",
            is_recurring=True,
            recurring_period="daily",  # Невалидный период!
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        assert instances == []


class TestVirtualTransactionStructure:
    """Тесты для структуры VirtualTransaction."""

    def test_virtual_transaction_fields(self, db_session, test_user):
        """Проверка полей VirtualTransaction."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 15),
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        assert len(instances) == 1
        vt = instances[0]

        assert vt["template_id"] == template.id
        assert vt["user_id"] == test_user.id
        assert vt["instance_date"] == "2026-01-15"
        assert vt["amount"] == "5000.00"
        assert vt["transaction_type"] == "income"
        assert vt["description"] == "Зарплата"
        assert vt["is_virtual"] is True
