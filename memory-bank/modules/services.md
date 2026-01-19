# modules/services.md

## Суть
Сервисный слой с бизнес-логикой и валидацией для Transaction, Goal и Calendar операций

## Ключевые файлы
- `app/services/transaction_service.py` - TransactionService CRUD
- `app/services/goal_service.py` - GoalService CRUD + contributions
- `app/services/calendar_service.py` - CalendarService расчет остатков (Фаза 3)

## TransactionService

**Инициализация**: `TransactionService(session)` - принимает SQLAlchemy session

**CRUD методы**:
- `create_transaction(user_id, amount, transaction_type, transaction_date, description, category)` - создание
- `get_by_id(transaction_id)` - получение по ID
- `get_all_by_user(user_id, transaction_type, start_date, end_date)` - список с фильтрацией
- `update_transaction(transaction_id, **kwargs)` - обновление
- `delete_transaction(transaction_id)` - удаление

**Валидация**:
- amount > 0 (положительная сумма)
- transaction_type in [INCOME, EXPENSE, TRANSFER]
- transaction_date не более 1 года в будущем

**Пример использования**:
```python
service = TransactionService(session)
transaction = service.create_transaction(
    user_id=1,
    amount=Decimal('1500.00'),
    transaction_type=TransactionType.INCOME,
    transaction_date=date.today(),
    description='Зарплата'
)
session.commit()  # Caller управляет commit
```

## GoalService

**Инициализация**: `GoalService(session)` - принимает SQLAlchemy session

**CRUD методы**:
- `create_goal(user_id, name, target_amount, target_date)` - создание цели
- `get_by_id(goal_id)` - получение по ID
- `get_all_by_user(user_id)` - список целей пользователя
- `update_goal(goal_id, **kwargs)` - обновление
- `delete_goal(goal_id)` - удаление

**Contributions**:
- `add_contribution(goal_id, amount, contribution_date)` - добавление взноса
  - Автоматически обновляет `goal.current_amount`
  - Автоматически меняет статус на COMPLETED если достигнута

**Валидация**:
- target_amount > 0
- target_date в будущем (не в прошлом)
- у пользователя только 1 активная цель (MVP ограничение)
- contribution amount > 0

**Пример использования**:
```python
service = GoalService(session)

# Создание цели
goal = service.create_goal(
    user_id=1,
    name='Отпуск',
    target_amount=Decimal('50000.00'),
    target_date=date(2025, 6, 1)
)

# Добавление взноса
service.add_contribution(
    goal_id=goal.id,
    amount=Decimal('5000.00'),
    contribution_date=date.today()
)
session.commit()
```

## Важное

**Session Management (КРИТИЧНО)**:
- Централизованный session management через `app/core/database.py`
- Context manager `get_db_session()` для автоматического commit/rollback
- Сервисы используют `session.flush()` для валидации + ID generation
- Caller управляет `session.commit()` через context manager

**Использование get_db_session():**
```python
from app.core import get_db_session

with get_db_session() as session:
    service = TransactionService(session)
    tx = service.create_transaction(...)
    # commit происходит автоматически при выходе из with
    # rollback при exception
```

**ValidationError (КРИТИЧНО)**:
- Единый класс в `app/core/exceptions.py`
- Атрибут `field` для подсветки ошибок в UI
- Сообщения на русском языке
- Экспортируется через `from app.core import ValidationError`

**Использование ValidationError:**
```python
from app.core import ValidationError

raise ValidationError("Сумма должна быть больше 0", field="amount")
# __str__ вернёт: "[amount] Сумма должна быть больше 0"
```

**Data Integrity**:
- GoalService.add_contribution автоматически обновляет current_amount
- Статус цели автоматически меняется на COMPLETED при достижении

## Критичные решения

**D010**: Session management через flush() вместо commit() для гибкости caller

**BUG-001**: Seed script должен использовать GoalService.add_contribution вместо hardcoded current_amount

**BUG-003**: target_date валидация - минимум 7 дней от сегодня

## CalendarService (Фаза 3 — ЗАВЕРШЕНА)

**Файл**: `app/services/calendar_service.py` (~310 строк)

**Инициализация**: `CalendarService(session)` - принимает SQLAlchemy session

**Методы**:
- `calculate_daily_balances(user_id, start_date, end_date)` → `dict[date, Decimal]`
  - Кумулятивный расчет остатков по дням
  - Начинается с `User.starting_balance` (fallback: 0)
  - **КРИТИЧНО**: TRANSFER транзакции исключаются из расчетов
- `get_transactions_by_date(user_id, start_date, end_date)` → `dict[date, list[Transaction]]`
  - Группировка транзакций по датам
  - Для отображения иконок доходов/расходов в ячейках
- `get_month_summary(user_id, year, month)` → `MonthSummary`
  - Агрегация за месяц: total_income, total_expense, start_balance, end_balance

**TypedDict**:
```python
class MonthSummary(TypedDict):
    total_income: Decimal
    total_expense: Decimal
    start_balance: Decimal
    end_balance: Decimal
```

**Пример использования**:
```python
from app.services import CalendarService

with get_db_session() as session:
    service = CalendarService(session)

    # Расчет остатков за январь
    balances = service.calculate_daily_balances(
        user_id=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31)
    )
    # {date(2026,1,1): Decimal('10000'), date(2026,1,2): Decimal('9500'), ...}

    # Сводка по месяцу
    summary = service.get_month_summary(user_id=1, year=2026, month=1)
    # {'total_income': Decimal('50000'), 'total_expense': Decimal('35000'), ...}
```

**Внутренние методы**:
- `_get_starting_balance(user_id)` — получение начального баланса
- `_calculate_balance_before_date(user_id, date)` — баланс на начало периода
- `_get_daily_changes(user_id, start_date, end_date)` — SQL агрегация изменений

**SQL агрегация** (производительность):
```python
# GROUP BY transaction_date для эффективности
case(
    (Transaction.transaction_type == TransactionType.INCOME, Transaction.amount),
    else_=-Transaction.amount
)
```

**Unit тесты**: 15 тестов в `tests/test_calendar_service.py`
- Покрытие: пустые данные, один день, несколько дней, TRANSFER исключение

## Критичные решения

**D010**: Session management через flush() вместо commit() для гибкости caller

**BUG-001**: Seed script должен использовать GoalService.add_contribution вместо hardcoded current_amount

**BUG-003**: target_date валидация - минимум 7 дней от сегодня

**Фаза 3**: TRANSFER транзакции исключаются из CalendarService расчетов баланса

---

Детали: `architecture.md` (Service Layer Pattern), `code-style.md` (Session Management Pattern)
