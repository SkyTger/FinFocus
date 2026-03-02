# Шаг 4: ReconciliationService

## Briefing
- **Цель:** Создать сервис для сверки баланса: расчет ожидаемого баланса, создание корректировки (ADJUSTMENT), формирование preview для UI.
- **Ключевые файлы:**
  - `app/services/reconciliation_service.py` (создать)
  - `app/services/__init__.py` (модифицировать)
  - `tests/test_reconciliation_service.py` (создать)
- **Additional info:**
  - ReconciliationService использует CalendarService для получения ожидаемого баланса
  - ADJUSTMENT транзакция создается с системной категорией "Коррекция"
  - difference = actual_balance - expected_balance (может быть + или -)
  - Сумма ADJUSTMENT = difference (положительная если actual > expected)

## Sub-tasks

### 4.1. Создать app/services/reconciliation_service.py

```python
"""Сервис для сверки баланса.

Предоставляет методы для сверки расчетного баланса с фактическим
и создания корректирующих операций (ADJUSTMENT).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import ValidationError
from app.models.database import Transaction, TransactionType
from app.schema.categories import ReconciliationPreview
from app.services.calendar_service import CalendarService
from app.services.category_service import CategoryService


class ReconciliationService:
    """Сервис для сверки баланса и создания корректировок."""

    def __init__(self, session: Session):
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy session для работы с БД.
        """
        self.session = session
        self.calendar_service = CalendarService(session)
        self.category_service = CategoryService(session)

    def get_expected_balance(self, user_id: int, target_date: date) -> Decimal:
        """Получить расчетный баланс на указанную дату.

        Args:
            user_id: ID пользователя.
            target_date: Дата для расчета баланса.

        Returns:
            Расчетный баланс на конец указанного дня.
        """
        return self.calendar_service.get_balance_on_date(user_id, target_date)

    def calculate_preview(
        self,
        user_id: int,
        target_date: date,
        actual_balance: Decimal
    ) -> ReconciliationPreview:
        """Рассчитать preview для модала сверки.

        Args:
            user_id: ID пользователя.
            target_date: Дата сверки.
            actual_balance: Фактический баланс (введенный пользователем).

        Returns:
            ReconciliationPreview с данными для отображения в модале.
        """
        expected_balance = self.get_expected_balance(user_id, target_date)
        difference = actual_balance - expected_balance
        is_positive = difference >= Decimal("0")

        # Формируем пояснение
        if difference == Decimal("0"):
            explanation = "Баланс совпадает, корректировка не требуется"
        elif is_positive:
            explanation = f"Будет создана корректировка на +{difference:,.2f} ₽"
        else:
            explanation = f"Будет создана корректировка на {difference:,.2f} ₽"

        return ReconciliationPreview(
            expected_balance=str(expected_balance),
            actual_balance=str(actual_balance),
            difference=str(difference),
            is_positive=is_positive,
            target_date=target_date.isoformat(),
            explanation=explanation
        )

    def create_adjustment(
        self,
        user_id: int,
        target_date: date,
        actual_balance: Decimal,
        description: str | None = None
    ) -> Transaction | None:
        """Создать корректирующую операцию (ADJUSTMENT).

        Если разница между фактическим и расчетным балансом равна нулю,
        корректировка не создается.

        Args:
            user_id: ID пользователя.
            target_date: Дата сверки.
            actual_balance: Фактический баланс.
            description: Описание корректировки (опционально).

        Returns:
            Созданная транзакция ADJUSTMENT или None если корректировка не нужна.

        Raises:
            ValidationError: Если системная категория "Коррекция" не найдена.
        """
        expected_balance = self.get_expected_balance(user_id, target_date)
        difference = actual_balance - expected_balance

        # Не создаем корректировку если баланс совпадает
        if difference == Decimal("0"):
            return None

        # Получаем системную категорию "Коррекция"
        correction_category = self.category_service.get_system_category("Коррекция")
        if not correction_category:
            raise ValidationError(
                "Системная категория 'Коррекция' не найдена. "
                "Запустите seed_categories.py"
            )

        # Формируем описание
        if not description:
            if difference > Decimal("0"):
                description = f"Сверка: баланс увеличен на {difference:,.2f} ₽"
            else:
                description = f"Сверка: баланс уменьшен на {abs(difference):,.2f} ₽"

        # Создаем транзакцию ADJUSTMENT
        # ВАЖНО: amount хранит именно difference (может быть отрицательным)
        adjustment = Transaction(
            user_id=user_id,
            amount=difference,  # Может быть + или -
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=target_date,
            description=description,
            category_id=correction_category.id
        )

        self.session.add(adjustment)
        self.session.flush()

        return adjustment
```

### 4.2. Обновить app/services/__init__.py

Добавить экспорт ReconciliationService:

```python
from app.services.reconciliation_service import ReconciliationService

# В __all__ добавить:
"ReconciliationService",
```

### 4.3. Написать unit тесты

Создать файл `tests/test_reconciliation_service.py`:

```python
"""Тесты для ReconciliationService."""

import pytest
from datetime import date
from decimal import Decimal

from app.services.reconciliation_service import ReconciliationService
from app.services.category_service import CategoryService
from app.models.database import Transaction, TransactionType


@pytest.fixture
def seeded_categories(db_session):
    """Фикстура для создания предустановленных категорий."""
    service = CategoryService(db_session)
    service.seed_default_categories()
    db_session.commit()
    return service


class TestReconciliationServiceGetExpectedBalance:
    """Тесты метода get_expected_balance."""

    def test_get_expected_balance_empty(self, db_session, sample_user):
        """Возвращает 0 для пользователя без транзакций."""
        service = ReconciliationService(db_session)
        result = service.get_expected_balance(sample_user.id, date.today())
        assert result == Decimal("0")

    def test_get_expected_balance_with_transactions(
        self, db_session, sample_user
    ):
        """Возвращает корректный баланс с учетом транзакций."""
        # Добавляем транзакции
        income = Transaction(
            user_id=sample_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date.today()
        )
        expense = Transaction(
            user_id=sample_user.id,
            amount=Decimal("300.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today()
        )
        db_session.add_all([income, expense])
        db_session.commit()

        service = ReconciliationService(db_session)
        result = service.get_expected_balance(sample_user.id, date.today())

        assert result == Decimal("700.00")


class TestReconciliationServiceCalculatePreview:
    """Тесты метода calculate_preview."""

    def test_preview_positive_difference(self, db_session, sample_user):
        """Preview корректно рассчитывает положительную разницу."""
        service = ReconciliationService(db_session)
        preview = service.calculate_preview(
            user_id=sample_user.id,
            target_date=date.today(),
            actual_balance=Decimal("500.00")
        )

        assert preview["expected_balance"] == "0"
        assert preview["actual_balance"] == "500.00"
        assert preview["difference"] == "500.00"
        assert preview["is_positive"] is True
        assert "+500" in preview["explanation"]

    def test_preview_negative_difference(self, db_session, sample_user):
        """Preview корректно рассчитывает отрицательную разницу."""
        # Добавляем доход
        income = Transaction(
            user_id=sample_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date.today()
        )
        db_session.add(income)
        db_session.commit()

        service = ReconciliationService(db_session)
        preview = service.calculate_preview(
            user_id=sample_user.id,
            target_date=date.today(),
            actual_balance=Decimal("800.00")
        )

        assert preview["difference"] == "-200.00"
        assert preview["is_positive"] is False
        assert "-200" in preview["explanation"]

    def test_preview_zero_difference(self, db_session, sample_user):
        """Preview корректно обрабатывает нулевую разницу."""
        service = ReconciliationService(db_session)
        preview = service.calculate_preview(
            user_id=sample_user.id,
            target_date=date.today(),
            actual_balance=Decimal("0")
        )

        assert preview["difference"] == "0"
        assert "не требуется" in preview["explanation"]


class TestReconciliationServiceCreateAdjustment:
    """Тесты метода create_adjustment."""

    def test_create_positive_adjustment(
        self, db_session, sample_user, seeded_categories
    ):
        """Создает положительную корректировку."""
        service = ReconciliationService(db_session)
        adjustment = service.create_adjustment(
            user_id=sample_user.id,
            target_date=date.today(),
            actual_balance=Decimal("500.00")
        )

        assert adjustment is not None
        assert adjustment.transaction_type == TransactionType.ADJUSTMENT
        assert adjustment.amount == Decimal("500.00")
        assert adjustment.category_id is not None

    def test_create_negative_adjustment(
        self, db_session, sample_user, seeded_categories
    ):
        """Создает отрицательную корректировку."""
        # Добавляем доход
        income = Transaction(
            user_id=sample_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date.today()
        )
        db_session.add(income)
        db_session.commit()

        service = ReconciliationService(db_session)
        adjustment = service.create_adjustment(
            user_id=sample_user.id,
            target_date=date.today(),
            actual_balance=Decimal("700.00")
        )

        assert adjustment is not None
        assert adjustment.amount == Decimal("-300.00")

    def test_no_adjustment_when_balanced(
        self, db_session, sample_user, seeded_categories
    ):
        """Не создает корректировку если баланс совпадает."""
        service = ReconciliationService(db_session)
        adjustment = service.create_adjustment(
            user_id=sample_user.id,
            target_date=date.today(),
            actual_balance=Decimal("0")
        )

        assert adjustment is None

    def test_raises_without_system_category(self, db_session, sample_user):
        """Выбрасывает ошибку если системная категория не найдена."""
        from app.core import ValidationError

        service = ReconciliationService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_adjustment(
                user_id=sample_user.id,
                target_date=date.today(),
                actual_balance=Decimal("100.00")
            )

        assert "Коррекция" in str(exc_info.value)
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 4.1-4.3.
2.  **Базовая проверка:**
    - `python -m py_compile app/services/reconciliation_service.py`
    - `python -m py_compile tests/test_reconciliation_service.py`
    - Проверь импорт: `python -c "from app.services import ReconciliationService; print('OK')"`
3.  **Фиксация:**
    - Добавь запись в `log.md`
    - Обнови `context.md`: Current Step = 5
    - Проверь ветку main
    - `git add . && git commit -m "feat(services): add ReconciliationService [protocol-0009/04]"`
    - `git push`
4.  **Отчет пользователю** в установленном формате.
