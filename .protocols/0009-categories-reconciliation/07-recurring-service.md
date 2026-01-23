# Шаг 7: RecurringService

## Briefing
- **Цель:** Добавить category_id в VirtualTransaction TypedDict, обеспечить наследование категории из шаблона в виртуальные экземпляры и exceptions.
- **Ключевые файлы:**
  - `app/services/recurring_service.py` (модифицировать)
  - `tests/test_recurring_service.py` (модифицировать — добавить тесты)
- **Additional info:**
  - VirtualTransaction — локальный TypedDict в recurring_service.py
  - При генерации виртуальных экземпляров category_id копируется из шаблона
  - При создании exception category_id копируется из шаблона (по умолчанию)

## Sub-tasks

### 7.1. Обновить VirtualTransaction TypedDict

В `app/services/recurring_service.py` расширить VirtualTransaction:

```python
class VirtualTransaction(TypedDict):
    """Виртуальный экземпляр recurring операции.

    Не хранится в БД, генерируется динамически.
    TypedDict для совместимости с JSON-сериализацией (dcc.Store).
    """

    template_id: int  # ID шаблона
    user_id: int
    instance_date: str  # ISO format (YYYY-MM-DD)
    amount: str  # Decimal as string для JSON
    transaction_type: str  # "income" | "expense" | "transfer"
    description: str | None
    is_virtual: bool  # Всегда True для виртуальных
    category_id: int | None  # NEW: копируется из шаблона
```

### 7.2. Обновить generate_instances

В методе `generate_instances` добавить копирование category_id:

```python
def generate_instances(
    self,
    template: Transaction,
    start_date: date,
    end_date: date
) -> list[VirtualTransaction]:
    """Генерирует виртуальные экземпляры recurring операции.

    category_id копируется из шаблона.
    """
    # ... существующий код ...

    for instance_date in instance_dates:
        virtual = VirtualTransaction(
            template_id=template.id,
            user_id=template.user_id,
            instance_date=instance_date.isoformat(),
            amount=str(template.amount),
            transaction_type=template.transaction_type.value,
            description=template.description,
            is_virtual=True,
            category_id=template.category_id  # NEW: наследуем из шаблона
        )
        instances.append(virtual)

    return instances
```

### 7.3. Обновить create_exception

В методе `create_exception` добавить копирование category_id из шаблона (если не указан явно):

```python
def create_exception(
    self,
    template_id: int,
    instance_date: date,
    amount: Decimal | None = None,
    description: str | None = None,
    category_id: int | None = None,  # NEW: опциональный параметр
    **kwargs
) -> Transaction:
    """Создать exception для конкретного экземпляра recurring.

    Если category_id не указан, копируется из шаблона.

    Args:
        template_id: ID шаблона recurring.
        instance_date: Дата экземпляра.
        amount: Новая сумма (опционально, по умолчанию из шаблона).
        description: Новое описание (опционально).
        category_id: ID категории (опционально, по умолчанию из шаблона).

    Returns:
        Созданная транзакция-exception.
    """
    template = self.session.query(Transaction).filter_by(id=template_id).first()
    if not template:
        raise ValidationError(f"Шаблон с ID {template_id} не найден")

    # Копируем category_id из шаблона если не указан явно
    if category_id is None:
        category_id = template.category_id

    exception = Transaction(
        user_id=template.user_id,
        amount=amount if amount is not None else template.amount,
        transaction_type=template.transaction_type,
        transaction_date=instance_date,
        description=description if description is not None else template.description,
        category_id=category_id,  # NEW
        is_recurring=False,
        recurring_parent_id=template.id,
        original_date=instance_date,
    )

    self.session.add(exception)
    self.session.flush()

    return exception
```

### 7.4. Написать unit тесты

Добавить тесты в `tests/test_recurring_service.py`:

```python
class TestRecurringServiceCategoryInheritance:
    """Тесты наследования category_id в recurring."""

    def test_virtual_instance_inherits_category(self, db_session, sample_user):
        """Виртуальный экземпляр наследует category_id из шаблона."""
        from app.models.database import Category

        category = Category(name="Зарплата", type="income")
        db_session.add(category)
        db_session.flush()

        template = Transaction(
            user_id=sample_user.id,
            amount=Decimal("50000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 1),
            is_recurring=True,
            recurring_period="monthly",
            category_id=category.id
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        instances = service.generate_instances(
            template,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31)
        )

        assert len(instances) >= 1
        for instance in instances:
            assert instance["category_id"] == category.id

    def test_exception_inherits_category_by_default(
        self, db_session, sample_user
    ):
        """Exception наследует category_id из шаблона по умолчанию."""
        from app.models.database import Category

        category = Category(name="Аренда", type="expense")
        db_session.add(category)
        db_session.flush()

        template = Transaction(
            user_id=sample_user.id,
            amount=Decimal("30000.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 1, 15),
            is_recurring=True,
            recurring_period="monthly",
            category_id=category.id
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        exception = service.create_exception(
            template_id=template.id,
            instance_date=date(2026, 2, 15),
            amount=Decimal("32000.00")  # Изменили сумму
        )

        # category_id должен быть унаследован
        assert exception.category_id == category.id

    def test_exception_can_override_category(self, db_session, sample_user):
        """Exception может иметь свою категорию."""
        from app.models.database import Category

        cat1 = Category(name="Зарплата", type="income")
        cat2 = Category(name="Подработка", type="income")
        db_session.add_all([cat1, cat2])
        db_session.flush()

        template = Transaction(
            user_id=sample_user.id,
            amount=Decimal("50000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 1, 1),
            is_recurring=True,
            recurring_period="monthly",
            category_id=cat1.id
        )
        db_session.add(template)
        db_session.commit()

        service = RecurringService(db_session)
        exception = service.create_exception(
            template_id=template.id,
            instance_date=date(2026, 2, 1),
            category_id=cat2.id  # Явно указываем другую категорию
        )

        assert exception.category_id == cat2.id
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 7.1-7.4.
2.  **Базовая проверка:**
    - `python -m py_compile app/services/recurring_service.py`
    - `python -m py_compile tests/test_recurring_service.py`
3.  **Фиксация:**
    - Добавь запись в `log.md`
    - Обнови `context.md`: Current Step = 8
    - Проверь ветку main
    - `git add . && git commit -m "feat(recurring): add category_id inheritance [protocol-0009/07]"`
    - `git push`
4.  **Отчет пользователю** в установленном формате.
