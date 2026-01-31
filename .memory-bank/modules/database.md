# modules/database.md

## Суть
SQLAlchemy ORM модели для доменных сущностей: User, Transaction, Goal, GoalContribution

## Ключевые файлы
- `app/models/database.py` - все ORM модели и database initialization

## Модели данных

### User
```python
starting_balance: Decimal          # Начальный баланс для кассового календаря
monthly_savings_budget: Decimal    # Месячный бюджет на накопления (default=0)
savings_mode: String(20)           # Режим накоплений: free/medium/strict (default="free")
first_launch: Boolean              # Флаг первого запуска для onboarding (default=True)

# Формула остатка: starting_balance + SUM(доходы) - SUM(расходы) до даты
# TRANSFER транзакции исключаются из расчетов баланса
```
**Relationships**: transactions (1:N), goals (1:N)

### Transaction
```python
amount: Decimal                # Сумма операции
transaction_type: Enum         # INCOME | EXPENSE | TRANSFER
transaction_date: Date         # Дата операции
is_recurring: Boolean          # Повторяющаяся операция (шаблон)
recurring_period: String       # weekly | biweekly | monthly | quarterly (nullable)
recurring_end_date: Date       # Дата окончания серии (nullable)
recurring_parent_id: Integer   # ID родительского шаблона для exceptions (nullable)
original_date: Date            # Исходная дата для exceptions (nullable)
is_skipped: Boolean            # Пропущенный экземпляр (default=False)
```

**Relationships**: user (N:1)

**Property**:
- `anchor_day` - день месяца шаблона для Anchored-алгоритма (guard clause для None)

**UniqueConstraint**: (recurring_parent_id, original_date) - один exception на дату

### Goal
```python
target_amount: Decimal    # Целевая сумма
current_amount: Decimal   # Текущая сумма (автообновляется через contributions)
target_date: Date         # Дедлайн
status: Enum              # ACTIVE | COMPLETED | PAUSED
priority: Integer         # Приоритет (1 = самый важный, default=1, nullable=False)
```

**Calculated Properties**:
- `progress_percentage` - min((current/target)*100, 100)
- `is_completed` - current >= target
- `monthly_contribution` - (target - current) / months_remaining с guard clauses

**Relationships**: user (N:1), contributions (1:N)

**Index**: idx_user_priority на (user_id, priority) для быстрой сортировки

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

**~~D009~~**: ~~MVP ограничение - одна активная цель на пользователя~~ (УДАЛЕНО в протоколе 0006)

**Протокол 0005**: Расширена Transaction для recurring (6 новых полей), UniqueConstraint

**Протокол 0006**: User.monthly_savings_budget, Goal.priority, idx_user_priority

**Протокол 0007**: User.savings_mode (free/medium/strict)

**Протокол 0014**: User.first_launch (Boolean, default=True) для onboarding wizard

---

Детали: `architecture.md`, `tech-stack.md` (SQLAlchemy 2.0.23)
