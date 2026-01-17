# modules/services.md

## Суть
Сервисный слой с бизнес-логикой и валидацией для Transaction и Goal операций

## Ключевые файлы
- `app/services/transaction_service.py` - TransactionService CRUD
- `app/services/goal_service.py` - GoalService CRUD + contributions

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

---

Детали: `architecture.md` (Service Layer Pattern), `code-style.md` (Session Management Pattern)
