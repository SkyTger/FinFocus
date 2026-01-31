"""Unit тесты для RecurringService.

Тестирование Anchored-алгоритма генерации виртуальных экземпляров
из шаблонов повторяющихся операций.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.core.exceptions import ValidationError
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


# === Тесты для CRUD exceptions ===


class TestCreateException:
    """Тесты для метода create_exception."""

    def test_create_exception_new(self, db_session, test_user):
        """Создание нового exception."""
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
        exception = service.create_exception(
            template_id=template.id,
            original_date=date(2026, 2, 15),
            new_amount=Decimal("5500.00"),
            new_description="Зарплата с премией",
        )
        db_session.commit()

        assert exception.id is not None
        assert exception.recurring_parent_id == template.id
        assert exception.original_date == date(2026, 2, 15)
        assert exception.amount == Decimal("5500.00")
        assert exception.description == "Зарплата с премией"
        assert exception.is_skipped is False

    def test_create_exception_update_existing(self, db_session, test_user):
        """Обновление существующего exception."""
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

        # Создаем первый exception
        exc1 = service.create_exception(
            template_id=template.id,
            original_date=date(2026, 2, 15),
            new_amount=Decimal("5500.00"),
        )
        db_session.commit()
        exc1_id = exc1.id

        # Обновляем тот же exception
        exc2 = service.create_exception(
            template_id=template.id,
            original_date=date(2026, 2, 15),
            new_amount=Decimal("6000.00"),
        )
        db_session.commit()

        # Должен быть тот же объект
        assert exc2.id == exc1_id
        assert exc2.amount == Decimal("6000.00")

    def test_create_exception_invalid_date(self, db_session, test_user):
        """original_date раньше начала серии вызывает ошибку."""
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

        with pytest.raises(ValidationError) as exc_info:
            service.create_exception(
                template_id=template.id,
                original_date=date(2025, 12, 15),  # Раньше начала!
            )

        assert "раньше начала серии" in str(exc_info.value)


class TestSkipInstance:
    """Тесты для метода skip_instance."""

    def test_skip_instance_new(self, db_session, test_user):
        """Пропуск нового экземпляра."""
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
        skipped = service.skip_instance(template.id, date(2026, 2, 15))
        db_session.commit()

        assert skipped.is_skipped is True
        assert skipped.original_date == date(2026, 2, 15)
        assert skipped.recurring_parent_id == template.id

    def test_skip_instance_existing(self, db_session, test_user):
        """Пропуск существующего exception."""
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

        # Сначала создаем exception
        exc = service.create_exception(
            template_id=template.id,
            original_date=date(2026, 2, 15),
            new_amount=Decimal("5500.00"),
        )
        db_session.commit()
        assert exc.is_skipped is False

        # Теперь пропускаем
        skipped = service.skip_instance(template.id, date(2026, 2, 15))
        db_session.commit()

        assert skipped.id == exc.id
        assert skipped.is_skipped is True


class TestStopTemplate:
    """Тесты для метода stop_template."""

    def test_stop_template(self, db_session, test_user):
        """Soft delete шаблона."""
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
        stopped = service.stop_template(template.id, stop_date=date(2026, 6, 30))
        db_session.commit()

        assert stopped.recurring_end_date == date(2026, 6, 30)
        assert stopped.is_recurring is True  # Шаблон не удален


class TestDeleteTemplate:
    """Тесты для метода delete_template."""

    def test_delete_template_cascades(self, db_session, test_user):
        """Hard delete с CASCADE удаляет exceptions."""
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
        template_id = template.id

        service = RecurringService(db_session)

        # Создаем exceptions
        service.create_exception(template_id, date(2026, 2, 15))
        service.create_exception(template_id, date(2026, 3, 15))
        db_session.commit()

        # Проверяем что exceptions созданы
        exceptions = service.get_exceptions_for_template(template_id)
        assert len(exceptions) == 2

        # Удаляем шаблон
        result = service.delete_template(template_id)
        db_session.commit()

        assert result is True

        # Проверяем что шаблон и exceptions удалены
        deleted_template = db_session.get(Transaction, template_id)
        assert deleted_template is None

        remaining_exceptions = (
            db_session.query(Transaction)
            .filter(Transaction.recurring_parent_id == template_id)
            .all()
        )
        assert len(remaining_exceptions) == 0


class TestUpdateTemplatePeriod:
    """Тесты для метода update_template_period."""

    def test_update_period_deletes_future_exceptions(self, db_session, test_user):
        """Изменение периода удаляет future exceptions."""
        today = date.today()

        # Шаблон начинается 60 дней назад
        template_start = today - timedelta(days=60)

        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=template_start,
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)

        # Создаем past и future exceptions относительно today
        past_date = today - timedelta(days=30)
        future_date = today + timedelta(days=30)

        service.create_exception(template.id, past_date)
        service.create_exception(template.id, future_date)
        db_session.commit()

        # Изменяем период
        updated = service.update_template_period(template.id, "weekly")
        db_session.commit()

        assert updated.recurring_period == "weekly"

        # Проверяем: past exception остался, future удален
        exceptions = service.get_exceptions_for_template(template.id)
        assert len(exceptions) == 1
        assert exceptions[0].original_date == past_date


class TestGetInstancesWithExceptions:
    """Тесты для метода get_instances_with_exceptions."""

    def test_replaces_virtual_with_exception(self, db_session, test_user):
        """Заменяет виртуальные экземпляры на exceptions."""
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

        # Создаем exception на февраль
        service.create_exception(
            template.id,
            date(2026, 2, 15),
            new_amount=Decimal("5500.00"),
        )
        db_session.commit()

        # Получаем экземпляры
        instances = service.get_instances_with_exceptions(
            test_user.id,
            date(2026, 1, 1),
            date(2026, 3, 31),
        )

        assert len(instances) == 3

        # Январь — виртуальный
        jan = instances[0]
        assert isinstance(jan, dict)
        assert jan["is_virtual"] is True

        # Февраль — exception (Transaction)
        feb = instances[1]
        assert isinstance(feb, Transaction)
        assert feb.amount == Decimal("5500.00")

        # Март — виртуальный
        mar = instances[2]
        assert isinstance(mar, dict)
        assert mar["is_virtual"] is True

    def test_skipped_instances_not_returned(self, db_session, test_user):
        """Пропущенные экземпляры не возвращаются."""
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

        # Пропускаем февраль
        service.skip_instance(template.id, date(2026, 2, 15))
        db_session.commit()

        # Получаем экземпляры
        instances = service.get_instances_with_exceptions(
            test_user.id,
            date(2026, 1, 1),
            date(2026, 3, 31),
        )

        # Должно быть 2: январь и март (февраль пропущен)
        assert len(instances) == 2

        dates = [
            i["instance_date"]
            if isinstance(i, dict)
            else i.transaction_date.isoformat()
            for i in instances
        ]
        assert "2026-01-15" in dates
        assert "2026-02-15" not in dates
        assert "2026-03-15" in dates


class TestRecurringServiceCategoryInheritance:
    """Тесты наследования category_id в recurring операциях."""

    def test_virtual_instance_inherits_category(self, db_session, test_user):
        """Виртуальный экземпляр наследует category_id из шаблона."""
        from app.models.database import Category

        # Создаем категорию
        category = Category(name="Зарплата", icon="bi-briefcase", type="income")
        db_session.add(category)
        db_session.flush()

        # Создаем шаблон с категорией
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("50000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 15),
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
            category_id=category.id,
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template, start_date=date(2026, 1, 1), end_date=date(2026, 3, 31)
        )

        assert len(instances) >= 1
        for instance in instances:
            assert instance["category_id"] == category.id
            assert instance["category_name"] == "Зарплата"

    def test_virtual_instance_handles_no_category(self, db_session, test_user):
        """Виртуальный экземпляр корректно обрабатывает отсутствие категории."""
        # Создаем шаблон БЕЗ категории
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 10),
            description="Разные расходы",
            is_recurring=True,
            recurring_period="monthly",
            category_id=None,
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template, start_date=date(2026, 1, 1), end_date=date(2026, 2, 28)
        )

        assert len(instances) >= 1
        for instance in instances:
            assert instance["category_id"] is None
            assert instance["category_name"] is None

    def test_exception_inherits_category_by_default(self, db_session, test_user):
        """Exception наследует category_id из шаблона по умолчанию."""
        from app.models.database import Category

        # Создаем категорию
        category = Category(name="Аренда", icon="bi-house", type="expense")
        db_session.add(category)
        db_session.flush()

        # Создаем шаблон с категорией
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("30000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 1),
            description="Аренда квартиры",
            is_recurring=True,
            recurring_period="monthly",
            category_id=category.id,
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)

        # Создаем exception БЕЗ указания category_id
        exception = service.create_exception(
            template_id=template.id,
            original_date=date(2026, 2, 1),
            new_amount=Decimal("32000.00"),  # Изменили только сумму
        )
        db_session.commit()

        # category_id должен быть унаследован из шаблона
        assert exception.category_id == category.id

    def test_exception_can_override_category(self, db_session, test_user):
        """Exception может иметь свою категорию, отличную от шаблона."""
        from app.models.database import Category

        # Создаем две категории
        cat_salary = Category(name="Зарплата", icon="bi-briefcase", type="income")
        cat_bonus = Category(name="Премия", icon="bi-gift", type="income")
        db_session.add_all([cat_salary, cat_bonus])
        db_session.flush()

        # Создаем шаблон с категорией "Зарплата"
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("50000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 15),
            description="Зарплата",
            is_recurring=True,
            recurring_period="monthly",
            category_id=cat_salary.id,
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)

        # Создаем exception с ДРУГОЙ категорией "Премия"
        exception = service.create_exception(
            template_id=template.id,
            original_date=date(2026, 2, 15),
            new_description="Зарплата + премия",
            category_id=cat_bonus.id,  # Явно указываем другую категорию
        )
        db_session.commit()

        # category_id должен быть переопределен
        assert exception.category_id == cat_bonus.id
        assert exception.category_id != template.category_id


# === Тесты для EOM (End of Month) Anchor ===


class TestIsEndOfMonth:
    """Тесты для статического метода is_end_of_month."""

    def test_is_end_of_month_28_february(self):
        """28 февраля в не-високосном году — последний день."""
        assert RecurringService.is_end_of_month(date(2026, 2, 28)) is True

    def test_is_end_of_month_29_february_leap(self):
        """29 февраля в високосном году — последний день."""
        assert RecurringService.is_end_of_month(date(2024, 2, 29)) is True

    def test_is_end_of_month_30_april(self):
        """30 апреля — последний день (30-дневный месяц)."""
        assert RecurringService.is_end_of_month(date(2026, 4, 30)) is True

    def test_is_end_of_month_31_january(self):
        """31 января — последний день (31-дневный месяц)."""
        assert RecurringService.is_end_of_month(date(2026, 1, 31)) is True

    def test_is_end_of_month_30_november(self):
        """30 ноября — последний день."""
        assert RecurringService.is_end_of_month(date(2026, 11, 30)) is True

    def test_is_end_of_month_false_27_february(self):
        """27 февраля — НЕ последний день."""
        assert RecurringService.is_end_of_month(date(2026, 2, 27)) is False

    def test_is_end_of_month_false_15_march(self):
        """15 марта — НЕ последний день."""
        assert RecurringService.is_end_of_month(date(2026, 3, 15)) is False

    def test_is_end_of_month_false_30_january(self):
        """30 января — НЕ последний день (в январе 31 день)."""
        assert RecurringService.is_end_of_month(date(2026, 1, 30)) is False


class TestShouldShowEomCheckbox:
    """Тесты для статического метода should_show_eom_checkbox."""

    def test_show_checkbox_30_april_monthly(self):
        """30 апреля + monthly → показывать checkbox."""
        assert (
            RecurringService.should_show_eom_checkbox(date(2026, 4, 30), "monthly")
            is True
        )

    def test_show_checkbox_28_february_monthly(self):
        """28 февраля + monthly → показывать checkbox."""
        assert (
            RecurringService.should_show_eom_checkbox(date(2026, 2, 28), "monthly")
            is True
        )

    def test_show_checkbox_30_november_quarterly(self):
        """30 ноября + quarterly → показывать checkbox."""
        assert (
            RecurringService.should_show_eom_checkbox(date(2026, 11, 30), "quarterly")
            is True
        )

    def test_hide_checkbox_31_january_monthly(self):
        """31 января + monthly → НЕ показывать (31 уже корректно в Anchored)."""
        assert (
            RecurringService.should_show_eom_checkbox(date(2026, 1, 31), "monthly")
            is False
        )

    def test_hide_checkbox_15_march_monthly(self):
        """15 марта + monthly → НЕ показывать (не последний день)."""
        assert (
            RecurringService.should_show_eom_checkbox(date(2026, 3, 15), "monthly")
            is False
        )

    def test_hide_checkbox_30_april_weekly(self):
        """30 апреля + weekly → НЕ показывать (период не monthly/quarterly)."""
        assert (
            RecurringService.should_show_eom_checkbox(date(2026, 4, 30), "weekly")
            is False
        )

    def test_hide_checkbox_28_february_biweekly(self):
        """28 февраля + biweekly → НЕ показывать (период не monthly/quarterly)."""
        assert (
            RecurringService.should_show_eom_checkbox(date(2026, 2, 28), "biweekly")
            is False
        )


class TestGetAnchoredDateWithEom:
    """Тесты для _get_anchored_date с параметром anchor_eom."""

    def test_eom_mode_returns_last_day_february(self, db_session):
        """EOM режим возвращает последний день февраля."""
        service = RecurringService(db_session)
        result = service._get_anchored_date(28, 2026, 2, anchor_eom=True)
        assert result == date(2026, 2, 28)

    def test_eom_mode_returns_last_day_march(self, db_session):
        """EOM режим возвращает 31 марта (последний день)."""
        service = RecurringService(db_session)
        result = service._get_anchored_date(28, 2026, 3, anchor_eom=True)
        assert result == date(2026, 3, 31)  # Не 28!

    def test_eom_mode_returns_last_day_april(self, db_session):
        """EOM режим возвращает 30 апреля (последний день)."""
        service = RecurringService(db_session)
        result = service._get_anchored_date(28, 2026, 4, anchor_eom=True)
        assert result == date(2026, 4, 30)

    def test_anchored_mode_respects_anchor_day(self, db_session):
        """Anchored режим (anchor_eom=False) сохраняет anchor_day."""
        service = RecurringService(db_session)
        result = service._get_anchored_date(28, 2026, 3, anchor_eom=False)
        assert result == date(2026, 3, 28)  # Anchored, не последний день


class TestGenerateInstancesWithEom:
    """Тесты для generate_instances с recurring_anchor_eom=True."""

    def test_eom_generates_last_days(self, db_session, test_user):
        """EOM режим генерирует последние дни каждого месяца."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 2, 28),  # Последний день февраля
            description="Оплата в конце месяца",
            is_recurring=True,
            recurring_period="monthly",
            recurring_anchor_eom=True,  # EOM режим!
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 31),
        )

        assert len(instances) == 4
        # 28 фев → 31 мар → 30 апр → 31 май
        assert instances[0]["instance_date"] == "2026-02-28"
        assert instances[1]["instance_date"] == "2026-03-31"
        assert instances[2]["instance_date"] == "2026-04-30"
        assert instances[3]["instance_date"] == "2026-05-31"

    def test_eom_quarterly(self, db_session, test_user):
        """EOM режим работает для quarterly."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 2, 28),
            description="Квартальный платёж в конце месяца",
            is_recurring=True,
            recurring_period="quarterly",
            recurring_anchor_eom=True,
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 11, 30),
        )

        assert len(instances) == 4
        # 28 фев → 31 май → 31 авг → 30 ноя
        assert instances[0]["instance_date"] == "2026-02-28"
        assert instances[1]["instance_date"] == "2026-05-31"
        assert instances[2]["instance_date"] == "2026-08-31"
        assert instances[3]["instance_date"] == "2026-11-30"

    def test_anchored_mode_default(self, db_session, test_user):
        """По умолчанию recurring_anchor_eom=False (Anchored режим)."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 2, 28),
            description="Оплата 28-го числа",
            is_recurring=True,
            recurring_period="monthly",
            # recurring_anchor_eom=False по умолчанию
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 31),
        )

        assert len(instances) == 4
        # Anchored: 28 фев → 28 мар → 28 апр → 28 май
        assert instances[0]["instance_date"] == "2026-02-28"
        assert instances[1]["instance_date"] == "2026-03-28"
        assert instances[2]["instance_date"] == "2026-04-28"
        assert instances[3]["instance_date"] == "2026-05-28"

    def test_eom_leap_year_february(self, db_session, test_user):
        """EOM режим корректно обрабатывает високосный год."""
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2024, 1, 31),
            description="Оплата в конце месяца",
            is_recurring=True,
            recurring_period="monthly",
            recurring_anchor_eom=True,
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        assert len(instances) == 3
        # 31 янв → 29 фев (високосный!) → 31 мар
        assert instances[0]["instance_date"] == "2024-01-31"
        assert instances[1]["instance_date"] == "2024-02-29"
        assert instances[2]["instance_date"] == "2024-03-31"
