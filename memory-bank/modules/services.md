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

**Session Management Pattern** (КРИТИЧНО):
- Сервисы используют `session.flush()` для валидации + ID generation
- Caller управляет `session.commit()` для атомарности
- Exception в сервисе → caller делает `session.rollback()`

**ValidationError**:
- Кастомный exception для бизнес-правил
- Сообщения на русском языке
- Обрабатывается в UI callbacks

**Data Integrity**:
- GoalService.add_contribution автоматически обновляет current_amount
- Статус цели автоматически меняется на COMPLETED при достижении

## Критичные решения

**D010**: Session management через flush() вместо commit() для гибкости caller

**BUG-001**: Seed script должен использовать GoalService.add_contribution вместо hardcoded current_amount

**BUG-003**: target_date валидация - минимум 7 дней от сегодня

---

Детали: `architecture.md` (Service Layer Pattern), `code-style.md` (Session Management Pattern)
