# Шаг 5: CalendarService

## Briefing
- **Цель:** Добавить обработку ADJUSTMENT в расчетах баланса, расширить TransactionInfo полями category_id и category_name.
- **Ключевые файлы:**
  - `app/services/calendar_service.py` (модифицировать)
  - `tests/test_calendar_service.py` (модифицировать — добавить тесты)
- **Additional info:**
  - ADJUSTMENT влияет на баланс: положительный увеличивает, отрицательный уменьшает
  - ADJUSTMENT НЕ должен учитываться в total_income/total_expense (это не доход/расход)
  - TransactionInfo используется для UI календаря — нужны category_id и category_name

## Sub-tasks

### 5.1. Обновить TransactionInfo TypedDict

В `app/services/calendar_service.py` расширить TransactionInfo:

```python
class TransactionInfo(TypedDict):
    """Информация о транзакции для UI календаря.

    Используется вместо ORM-объекта Transaction для передачи
    данных из CalendarService в UI-компоненты после закрытия сессии БД.
    Поддерживает как обычные транзакции, так и recurring instances.
    """

    id: int | None  # ID транзакции (None для виртуальных recurring)
    template_id: int | None  # ID шаблона для recurring (None для обычных)
    transaction_type: str  # "income" | "expense" | "transfer" | "adjustment"
    amount: str  # Decimal в строковом формате
    description: str | None  # Описание
    date: str  # ISO format (YYYY-MM-DD)
    is_virtual: bool  # True для виртуальных recurring instances
    is_recurring: bool  # True для recurring (виртуальных и exceptions)
    is_exception: bool  # True для exceptions (материализованных recurring)
    category_id: int | None  # NEW: ID категории (None = без категории)
    category_name: str | None  # NEW: Название категории для UI
```

### 5.2. Обновить _get_daily_changes для ADJUSTMENT

В методе `_get_daily_changes` добавить обработку ADJUSTMENT:

```python
def _get_daily_changes(
    self,
    user_id: int,
    start_date: date,
    end_date: date
) -> dict[date, Decimal]:
    """Получить изменения баланса по дням.

    ADJUSTMENT обрабатывается как прямое изменение баланса:
    - положительный amount увеличивает баланс
    - отрицательный amount уменьшает баланс
    """
    # ... существующий код ...

    # Обновить CASE для учета ADJUSTMENT
    amount_case = case(
        (Transaction.transaction_type == TransactionType.INCOME, Transaction.amount),
        (Transaction.transaction_type == TransactionType.ADJUSTMENT, Transaction.amount),  # NEW
        else_=-Transaction.amount  # EXPENSE
    )

    # ... остальной код ...
```

### 5.3. Обновить _calculate_balance_before_date для ADJUSTMENT

В методе `_calculate_balance_before_date` аналогично добавить ADJUSTMENT:

```python
def _calculate_balance_before_date(
    self,
    user_id: int,
    target_date: date
) -> Decimal:
    """Рассчитать баланс до указанной даты (не включая её).

    ADJUSTMENT учитывается как прямое изменение баланса.
    """
    # ... существующий код ...

    # Обновить CASE для учета ADJUSTMENT
    amount_case = case(
        (Transaction.transaction_type == TransactionType.INCOME, Transaction.amount),
        (Transaction.transaction_type == TransactionType.ADJUSTMENT, Transaction.amount),  # NEW
        else_=-Transaction.amount
    )

    # ... остальной код ...
```

### 5.4. Убедиться что ADJUSTMENT НЕ учитывается в get_month_summary

Проверить метод `get_month_summary` — ADJUSTMENT **НЕ должен** учитываться в `total_income` и `total_expense`:

```python
def get_month_summary(self, user_id: int, year: int, month: int) -> MonthSummary:
    """Получить сводку по месяцу.

    ADJUSTMENT не учитывается в total_income/total_expense,
    так как это не настоящий доход/расход, а корректировка.
    """
    # ... существующий код фильтрует только INCOME и EXPENSE ...
    # Убедиться что ADJUSTMENT не включен в расчет total_income/total_expense
```

### 5.5. Обновить get_transactions_by_date для category fields

В методе `get_transactions_by_date` добавить заполнение category_id и category_name:

```python
def get_transactions_by_date(
    self,
    user_id: int,
    start_date: date,
    end_date: date
) -> dict[date, list[TransactionInfo]]:
    """Получить транзакции сгруппированные по датам."""
    # ... существующий код ...

    # При создании TransactionInfo добавить category fields
    for tx in transactions:
        info = TransactionInfo(
            id=tx.id,
            template_id=getattr(tx, 'recurring_parent_id', None),
            transaction_type=tx.transaction_type.value,
            amount=str(tx.amount),
            description=tx.description,
            date=tx.transaction_date.isoformat(),
            is_virtual=False,
            is_recurring=tx.is_recurring if hasattr(tx, 'is_recurring') else False,
            is_exception=tx.recurring_parent_id is not None if hasattr(tx, 'recurring_parent_id') else False,
            category_id=tx.category_id,  # NEW
            category_name=tx.category_rel.name if tx.category_rel else None  # NEW
        )
        # ... добавить в result ...
```

### 5.6. Обновить get_all_transactions_for_period для category fields

Аналогично обновить метод `get_all_transactions_for_period`.

### 5.7. Написать unit тесты

Добавить тесты в `tests/test_calendar_service.py`:

```python
class TestCalendarServiceAdjustment:
    """Тесты обработки ADJUSTMENT в CalendarService."""

    def test_adjustment_positive_increases_balance(
        self, db_session, sample_user
    ):
        """Положительный ADJUSTMENT увеличивает баланс."""
        adjustment = Transaction(
            user_id=sample_user.id,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today()
        )
        db_session.add(adjustment)
        db_session.commit()

        service = CalendarService(db_session)
        balance = service.get_balance_on_date(sample_user.id, date.today())

        assert balance == Decimal("500.00")

    def test_adjustment_negative_decreases_balance(
        self, db_session, sample_user
    ):
        """Отрицательный ADJUSTMENT уменьшает баланс."""
        # Сначала доход
        income = Transaction(
            user_id=sample_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date.today()
        )
        # Затем отрицательная корректировка
        adjustment = Transaction(
            user_id=sample_user.id,
            amount=Decimal("-300.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today()
        )
        db_session.add_all([income, adjustment])
        db_session.commit()

        service = CalendarService(db_session)
        balance = service.get_balance_on_date(sample_user.id, date.today())

        assert balance == Decimal("700.00")

    def test_adjustment_not_in_month_summary_totals(
        self, db_session, sample_user
    ):
        """ADJUSTMENT не учитывается в total_income/total_expense."""
        income = Transaction(
            user_id=sample_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date.today()
        )
        adjustment = Transaction(
            user_id=sample_user.id,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today()
        )
        db_session.add_all([income, adjustment])
        db_session.commit()

        service = CalendarService(db_session)
        today = date.today()
        summary = service.get_month_summary(sample_user.id, today.year, today.month)

        # ADJUSTMENT не должен увеличивать total_income
        assert summary["total_income"] == Decimal("1000.00")
        assert summary["total_expense"] == Decimal("0")


class TestCalendarServiceCategoryFields:
    """Тесты category fields в TransactionInfo."""

    def test_transaction_info_includes_category(
        self, db_session, sample_user
    ):
        """TransactionInfo включает category_id и category_name."""
        from app.models.database import Category

        category = Category(name="Еда", type="expense", icon="bi-cart")
        db_session.add(category)
        db_session.flush()

        transaction = Transaction(
            user_id=sample_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=category.id
        )
        db_session.add(transaction)
        db_session.commit()

        service = CalendarService(db_session)
        today = date.today()
        result = service.get_transactions_by_date(
            sample_user.id, today, today
        )

        assert today in result
        tx_info = result[today][0]
        assert tx_info["category_id"] == category.id
        assert tx_info["category_name"] == "Еда"

    def test_transaction_info_without_category(
        self, db_session, sample_user
    ):
        """TransactionInfo корректно обрабатывает отсутствие категории."""
        transaction = Transaction(
            user_id=sample_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=None
        )
        db_session.add(transaction)
        db_session.commit()

        service = CalendarService(db_session)
        today = date.today()
        result = service.get_transactions_by_date(
            sample_user.id, today, today
        )

        tx_info = result[today][0]
        assert tx_info["category_id"] is None
        assert tx_info["category_name"] is None
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 5.1-5.7.
2.  **Базовая проверка:**
    - `python -m py_compile app/services/calendar_service.py`
    - `python -m py_compile tests/test_calendar_service.py`
3.  **Фиксация:**
    - Добавь запись в `log.md`
    - Обнови `context.md`: Current Step = 6
    - Проверь ветку main
    - `git add . && git commit -m "feat(calendar): add ADJUSTMENT handling and category fields [protocol-0009/05]"`
    - `git push`
4.  **Отчет пользователю** в установленном формате.
