# modules/database.md

## Суть
SQLAlchemy ORM модели для доменных сущностей: User, Transaction, Goal, GoalContribution

## Ключевые файлы
- `app/models/database.py` - все ORM модели и database initialization

## Модели данных

### User
```python
starting_balance: Decimal  # Начальный баланс для кассового календаря
# Формула остатка: starting_balance + SUM(доходы) - SUM(расходы) до даты
```
**Relationships**: transactions (1:N), goals (1:N)

### Transaction
```python
amount: Decimal           # Сумма операции
transaction_type: Enum    # INCOME | EXPENSE | TRANSFER
transaction_date: Date    # Дата операции
is_recurring: Boolean     # Повторяющаяся операция (для Батча 2)
```
**Relationships**: user (N:1)

### Goal
```python
target_amount: Decimal    # Целевая сумма
current_amount: Decimal   # Текущая сумма (автообновляется через contributions)
target_date: Date         # Дедлайн
status: Enum              # ACTIVE | COMPLETED | PAUSED
```

**Calculated Properties**:
- `progress_percentage` - min((current/target)*100, 100)
- `is_completed` - current >= target
- `monthly_contribution` - (target - current) / months_remaining с guard clauses

**Relationships**: user (N:1), contributions (1:N)

### GoalContribution
```python
amount: Decimal           # Сумма взноса
contribution_date: Date   # Дата взноса
```
**Relationships**: goal (N:1)

## Важное

**Guard Clauses** в `Goal.monthly_contribution`:
- target_date в прошлом → return 0
- target_date не установлен → return 0
- цель достигнута → return 0
- Минимум 1 месяц для расчета

**Session Management**:
- Инициализация: `init_database(database_url)` в `run.py`
- Session creation: `get_session(engine)`
- Автосоздание таблиц при первом запуске

**Enums**:
- `TransactionType`: INCOME, EXPENSE, TRANSFER
- `GoalStatus`: ACTIVE, COMPLETED, PAUSED

## Критичные решения

**D008**: Guard clauses для предотвращения division by zero в monthly_contribution

**D009**: MVP ограничение - одна активная цель на пользователя (временно)

---

Детали: `architecture.md`, `tech-stack.md` (SQLAlchemy 2.0.23)
