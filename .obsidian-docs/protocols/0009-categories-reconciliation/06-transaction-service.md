# Шаг 6: TransactionService

## Briefing
- **Цель:** Заменить параметр category (str) на category_id (int), добавить валидацию что ADJUSTMENT не может быть recurring.
- **Ключевые файлы:**
  - `app/services/transaction_service.py` (модифицировать)
  - `tests/test_transaction_service.py` (модифицировать — добавить тесты)
- **Additional info:**
  - category_id nullable — категория опциональна (ленивый подход)
  - Валидация: is_recurring=True + transaction_type=ADJUSTMENT = ValidationError
  - Сохранить обратную совместимость сигнатуры (category_id как keyword argument)

## Sub-tasks

### 6.1. Обновить метод create_transaction

В `app/services/transaction_service.py`:

1. **Удалить** параметр `category: str | None = None` (если существует)
2. **Добавить** параметр `category_id: int | None = None`
3. **Добавить** валидацию ADJUSTMENT + recurring

```python
def create_transaction(
    self,
    user_id: int,
    amount: Decimal,
    transaction_type: TransactionType,
    transaction_date: date,
    description: str | None = None,
    category_id: int | None = None,  # CHANGED: was category (str)
    is_recurring: bool = False,
    recurring_period: str | None = None,
    recurring_end_date: date | None = None,
) -> Transaction:
    """Создает новую транзакцию или шаблон recurring.

    Args:
        user_id: ID пользователя.
        amount: Сумма операции (> 0).
        transaction_type: Тип операции (INCOME, EXPENSE, TRANSFER, ADJUSTMENT).
        transaction_date: Дата операции.
        description: Описание (опционально).
        category_id: ID категории (опционально, nullable).
        is_recurring: Создать как recurring шаблон.
        recurring_period: Период повтора (weekly, monthly, etc.).
        recurring_end_date: Дата окончания повторов.

    Returns:
        Созданная транзакция.

    Raises:
        ValidationError: Если данные невалидны.
    """
    # Существующие валидации...

    # NEW: ADJUSTMENT не может быть recurring
    if is_recurring and transaction_type == TransactionType.ADJUSTMENT:
        raise ValidationError(
            "Корректировки не могут быть повторяющимися операциями"
        )

    # Создание транзакции
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        transaction_type=transaction_type,
        transaction_date=transaction_date,
        description=description,
        category_id=category_id,  # CHANGED
        is_recurring=is_recurring,
        recurring_period=recurring_period,
        recurring_end_date=recurring_end_date,
    )

    self.session.add(transaction)
    self.session.flush()

    return transaction
```

### 6.2. Обновить метод update_transaction

Добавить поддержку обновления category_id:

```python
def update_transaction(
    self,
    transaction_id: int,
    **kwargs
) -> Transaction:
    """Обновляет транзакцию.

    Поддерживаемые поля для обновления:
    - amount, transaction_type, transaction_date, description
    - category_id (NEW)
    - is_recurring, recurring_period, recurring_end_date

    Raises:
        ValidationError: Если транзакция не найдена или данные невалидны.
    """
    transaction = self.get_by_id(transaction_id)
    if not transaction:
        raise ValidationError(f"Транзакция с ID {transaction_id} не найдена")

    # NEW: Валидация ADJUSTMENT + recurring при обновлении
    new_type = kwargs.get("transaction_type", transaction.transaction_type)
    new_is_recurring = kwargs.get("is_recurring", transaction.is_recurring)

    if new_is_recurring and new_type == TransactionType.ADJUSTMENT:
        raise ValidationError(
            "Корректировки не могут быть повторяющимися операциями"
        )

    # Обновление полей
    allowed_fields = [
        "amount", "transaction_type", "transaction_date",
        "description", "category_id",  # NEW
        "is_recurring", "recurring_period", "recurring_end_date"
    ]

    for field, value in kwargs.items():
        if field in allowed_fields:
            setattr(transaction, field, value)

    self.session.flush()
    return transaction
```

### 6.3. Написать unit тесты

Добавить тесты в `tests/test_transaction_service.py`:

```python
class TestTransactionServiceCategoryId:
    """Тесты category_id в TransactionService."""

    def test_create_with_category_id(self, db_session, sample_user):
        """Транзакция создается с category_id."""
        from app.models.database import Category

        category = Category(name="Еда", type="expense")
        db_session.add(category)
        db_session.flush()

        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=sample_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=category.id
        )

        assert transaction.category_id == category.id

    def test_create_without_category_id(self, db_session, sample_user):
        """Транзакция создается без category_id (nullable)."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=sample_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today()
        )

        assert transaction.category_id is None

    def test_update_category_id(self, db_session, sample_user):
        """category_id можно обновить."""
        from app.models.database import Category

        category = Category(name="Еда", type="expense")
        db_session.add(category)
        db_session.flush()

        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=sample_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today()
        )

        updated = service.update_transaction(
            transaction.id,
            category_id=category.id
        )

        assert updated.category_id == category.id


class TestTransactionServiceAdjustmentValidation:
    """Тесты валидации ADJUSTMENT + recurring."""

    def test_adjustment_cannot_be_recurring(self, db_session, sample_user):
        """ADJUSTMENT не может быть recurring."""
        from app.core import ValidationError

        service = TransactionService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_transaction(
                user_id=sample_user.id,
                amount=Decimal("100.00"),
                transaction_type=TransactionType.ADJUSTMENT,
                transaction_date=date.today(),
                is_recurring=True,
                recurring_period="monthly"
            )

        assert "повторяющимися" in str(exc_info.value)

    def test_adjustment_single_allowed(self, db_session, sample_user):
        """ADJUSTMENT без recurring создается успешно."""
        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=sample_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today()
        )

        assert transaction.transaction_type == TransactionType.ADJUSTMENT
        assert transaction.is_recurring is False

    def test_update_to_adjustment_recurring_fails(self, db_session, sample_user):
        """Нельзя обновить recurring транзакцию в ADJUSTMENT."""
        from app.core import ValidationError

        service = TransactionService(db_session)
        transaction = service.create_transaction(
            user_id=sample_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            is_recurring=True,
            recurring_period="monthly"
        )

        with pytest.raises(ValidationError):
            service.update_transaction(
                transaction.id,
                transaction_type=TransactionType.ADJUSTMENT
            )
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 6.1-6.3.
2.  **Базовая проверка:**
    - `python -m py_compile app/services/transaction_service.py`
    - `python -m py_compile tests/test_transaction_service.py`
3.  **Фиксация:**
    - Добавь запись в `log.md`
    - Обнови `context.md`: Current Step = 7
    - Проверь ветку main
    - `git add . && git commit -m "feat(transactions): add category_id and ADJUSTMENT validation [protocol-0009/06]"`
    - `git push`
4.  **Отчет пользователю** в установленном формате.
