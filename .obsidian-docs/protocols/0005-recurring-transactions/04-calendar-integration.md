# Шаг 4: Интеграция с CalendarService

## Briefing
- **Цель:** Интегрировать RecurringService с CalendarService. Добавить фильтрацию recurring шаблонов во все существующие методы. Создать новый метод get_all_transactions_for_period().
- **Ключевые файлы:**
  - `app/services/calendar_service.py` (изменить)
  - `tests/test_calendar_service.py` (расширить)
  - `tests/test_calendar_recurring.py` (создать)
- **Additional info:**
  - Все существующие методы CalendarService должны исключать:
    - `is_recurring=True` (шаблоны)
    - `recurring_parent_id IS NOT NULL` (exceptions учитываются отдельно)
  - Новый метод объединяет реальные транзакции + recurring instances

## Sub-tasks

### 1. Изменить метод `_calculate_balance_before_date()`

**Файл:** `app/services/calendar_service.py`, строки ~146-187

**БЫЛО:**
```python
.filter(
    Transaction.user_id == user_id,
    Transaction.transaction_date < before_date,
    Transaction.transaction_type.in_(
        [TransactionType.INCOME, TransactionType.EXPENSE]
    ),
)
```

**СТАЛО:**
```python
.filter(
    Transaction.user_id == user_id,
    Transaction.transaction_date < before_date,
    Transaction.transaction_type.in_(
        [TransactionType.INCOME, TransactionType.EXPENSE]
    ),
    # Исключаем recurring шаблоны
    Transaction.is_recurring == False,  # noqa: E712
    # Исключаем exceptions (учитываются в recurring расчетах)
    Transaction.recurring_parent_id == None,  # noqa: E711
)
```

### 2. Изменить метод `_get_daily_changes()`

**Файл:** `app/services/calendar_service.py`, строки ~189-234

Добавить аналогичные фильтры:
```python
Transaction.is_recurring == False,  # noqa: E712
Transaction.recurring_parent_id == None,  # noqa: E711
```

### 3. Изменить метод `get_transactions_by_date()`

**Файл:** `app/services/calendar_service.py`, строки ~236-280

Добавить фильтр (только `is_recurring`, exceptions здесь нужны):
```python
Transaction.is_recurring == False,  # noqa: E712
```

### 4. Изменить метод `get_month_summary()`

**Файл:** `app/services/calendar_service.py`, строки ~282-353

Добавить фильтры:
```python
Transaction.is_recurring == False,  # noqa: E712
Transaction.recurring_parent_id == None,  # noqa: E711
```

### 5. Изменить метод `get_year_summary()`

**Файл:** `app/services/calendar_service.py`, строки ~380-443

Добавить фильтры:
```python
Transaction.is_recurring == False,  # noqa: E712
Transaction.recurring_parent_id == None,  # noqa: E711
```

### 6. Создать TypedDict TransactionInfo

В начале файла `calendar_service.py` добавить:

```python
class TransactionInfo(TypedDict):
    """Информация о транзакции для отображения."""
    id: int | None  # None для виртуальных
    template_id: int | None  # ID шаблона для recurring
    amount: str  # Decimal as string
    transaction_type: str
    description: str | None
    date: str  # ISO format
    is_virtual: bool
    is_recurring: bool
    is_exception: bool
```

### 7. Добавить метод `get_all_transactions_for_period()`

```python
def get_all_transactions_for_period(
    self,
    user_id: int,
    start_date: date,
    end_date: date,
    include_recurring: bool = True,
) -> dict[date, list[TransactionInfo]]:
    """Получает все транзакции включая recurring для периода.

    Объединяет:
    - Обычные транзакции из БД (is_recurring=False, recurring_parent_id=None)
    - Виртуальные recurring экземпляры из RecurringService (если include_recurring=True)
    - Exceptions заменяют виртуальные на соответствующие даты

    Args:
        user_id: ID пользователя.
        start_date: Начало периода.
        end_date: Конец периода.
        include_recurring: Включать ли recurring операции.

    Returns:
        Словарь: дата -> список транзакций.
    """
    from collections import defaultdict
    from app.services.recurring_service import RecurringService, VirtualTransaction

    result: dict[date, list[TransactionInfo]] = defaultdict(list)

    # 1. Получить обычные транзакции (не шаблоны, не exceptions)
    regular_transactions = (
        self.session.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.is_recurring == False,  # noqa: E712
            Transaction.recurring_parent_id == None,  # noqa: E711
        )
        .order_by(Transaction.transaction_date, Transaction.id)
        .all()
    )

    for txn in regular_transactions:
        result[txn.transaction_date].append(TransactionInfo(
            id=txn.id,
            template_id=None,
            amount=str(txn.amount),
            transaction_type=txn.transaction_type.value,
            description=txn.description,
            date=txn.transaction_date.isoformat(),
            is_virtual=False,
            is_recurring=False,
            is_exception=False,
        ))

    # 2. Добавить recurring экземпляры (если запрошено)
    if include_recurring:
        recurring_service = RecurringService(self.session)
        recurring_instances = recurring_service.get_instances_with_exceptions(
            user_id, start_date, end_date
        )

        for instance in recurring_instances:
            if isinstance(instance, dict):  # VirtualTransaction
                instance_date = date.fromisoformat(instance["instance_date"])
                result[instance_date].append(TransactionInfo(
                    id=None,
                    template_id=instance["template_id"],
                    amount=instance["amount"],
                    transaction_type=instance["transaction_type"],
                    description=instance["description"],
                    date=instance["instance_date"],
                    is_virtual=True,
                    is_recurring=True,
                    is_exception=False,
                ))
            else:  # Transaction (exception)
                result[instance.transaction_date].append(TransactionInfo(
                    id=instance.id,
                    template_id=instance.recurring_parent_id,
                    amount=str(instance.amount),
                    transaction_type=instance.transaction_type.value,
                    description=instance.description,
                    date=instance.transaction_date.isoformat(),
                    is_virtual=False,
                    is_recurring=True,
                    is_exception=True,
                ))

    logger.debug(
        f"get_all_transactions_for_period: {sum(len(v) for v in result.values())} "
        f"транзакций для пользователя {user_id} в периоде {start_date} - {end_date}"
    )

    return dict(result)
```

### 8. Обновить `calculate_daily_balances()` для учета recurring

Модифицировать метод для использования `get_all_transactions_for_period()`:

```python
def calculate_daily_balances(
    self,
    user_id: int,
    year: int,
    month: int,
    include_recurring: bool = True,
) -> dict[date, Decimal]:
    """Рассчитывает остатки по дням месяца.

    Args:
        user_id: ID пользователя.
        year: Год.
        month: Месяц.
        include_recurring: Включать ли recurring операции.

    Returns:
        Словарь: дата -> остаток на конец дня.
    """
    # ... существующая логика с учетом include_recurring параметра ...
```

### 9. Обновить экспорты в `app/services/__init__.py`

```python
from app.services.calendar_service import (
    CalendarService,
    MonthSummary,
    YearSummary,
    TransactionInfo,  # NEW
)
```

### 10. Написать integration тесты

Создать `tests/test_calendar_recurring.py`:

1. **test_daily_balances_excludes_templates** — шаблоны не влияют на баланс
2. **test_daily_balances_with_recurring** — recurring instances учитываются
3. **test_daily_balances_exception_replaces_virtual** — exception заменяет виртуальный
4. **test_daily_balances_skipped_not_counted** — пропущенные не учитываются
5. **test_get_all_transactions_combines** — объединение regular + recurring
6. **test_month_summary_excludes_templates** — month_summary без шаблонов
7. **test_year_summary_excludes_templates** — year_summary без шаблонов

### 11. Обновить существующие тесты

В `tests/test_calendar_service.py` добавить:
- Фикстуры для recurring шаблонов
- Проверки что существующие тесты по-прежнему проходят

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-11.
2. **Верификация:** После завершения ВСЕХ подзадач запусти:
   - `black app/services/calendar_service.py tests/test_calendar_*.py`
   - `flake8 app/services/calendar_service.py tests/test_calendar_*.py`
   - `pytest tests/test_calendar_service.py tests/test_calendar_recurring.py -v`
3. **Фиксация:** После успешной верификации:
   - **Добавь запись в `log.md`**: Опиши изменения в CalendarService.
   - **Обнови `context.md`**: Увеличь `Current Step` на 1.
   - Проверь ветку main.
4. **Сделай коммит**: `git add . && git commit -m "feat(services): integrate recurring with CalendarService [protocol-0005/04]"`. Сделай пуш.
5. **Отчет пользователю** по установленному формату.
