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
reservation_mode: String(20)       # Режим резервирования бюджета: fixed_date/from_balance (default="from_balance")
reservation_day: Integer           # День месяца для резервирования в режиме fixed_date (1-28, nullable)

# Формула остатка: starting_balance + SUM(доходы) - SUM(расходы) до даты
# TRANSFER, SAVINGS_RESERVE, SAVINGS_CONTRIBUTION исключаются при расчете для целей, но учитываются в балансе
```
**Relationships**: transactions (1:N), goals (1:N)

### Transaction
```python
amount: Decimal                # Сумма операции
transaction_type: Enum         # INCOME | EXPENSE | TRANSFER | ADJUSTMENT | SAVINGS_RESERVE | SAVINGS_CONTRIBUTION
transaction_date: Date         # Дата операции
is_recurring: Boolean          # Повторяющаяся операция (шаблон)
recurring_period: String       # weekly | biweekly | monthly | quarterly (nullable)
recurring_end_date: Date       # Дата окончания серии (nullable)
recurring_parent_id: Integer   # ID родительского шаблона для exceptions (nullable)
original_date: Date            # Исходная дата для exceptions (nullable)
is_skipped: Boolean            # Пропущенный экземпляр (default=False)
category_id: Integer           # FK к Category (nullable)
```

**Relationships**:
- user (N:1)
- category (N:1, nullable)

**Property**:
- `anchor_day` - день месяца шаблона для Anchored-алгоритма (guard clause для None)

**UniqueConstraint**: (recurring_parent_id, original_date) - один exception на дату

**TransactionType расширен** (Протокол 0009, 0016):
- ADJUSTMENT — корректировка баланса при сверке (не может быть recurring)
- SAVINGS_RESERVE — резервирование бюджета накоплений (режим fixed_date)
- SAVINGS_CONTRIBUTION — взнос в накопительную цель (режим from_balance)

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
transaction_id: Integer   # FK к Transaction (nullable, SET NULL) — связь с операцией в календаре
```
**Relationships**:
- goal (N:1)
- transaction (N:1, nullable, ondelete=SET NULL)

**Index**: ix_contribution_date на (contribution_date) для быстрой фильтрации по месяцам

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
- `TransactionType`: INCOME, EXPENSE, TRANSFER, ADJUSTMENT, SAVINGS_RESERVE, SAVINGS_CONTRIBUTION
- `GoalStatus`: ACTIVE, COMPLETED, PAUSED
- `ReservationMode` (app/schema/budget_reservation.py): "fixed_date" | "from_balance"

## Критичные решения

**D008**: Guard clauses для предотвращения division by zero в monthly_contribution

**~~D009~~**: ~~MVP ограничение - одна активная цель на пользователя~~ (УДАЛЕНО в протоколе 0006)

**Протокол 0005**: Расширена Transaction для recurring (6 новых полей), UniqueConstraint

**Протокол 0006**: User.monthly_savings_budget, Goal.priority, idx_user_priority

**Протокол 0007**: User.savings_mode (free/medium/strict)

**Протокол 0014**: User.first_launch (Boolean, default=True) для onboarding wizard

**Протокол 0016**: User.reservation_mode/reservation_day, TransactionType +SAVINGS_RESERVE/+SAVINGS_CONTRIBUTION, GoalContribution.transaction_id FK

**Протокол 0020**: WishlistItem модель для отложенных покупок

### WishlistItem (Протокол 0020)
```python
name: String(100)           # Название покупки (обязательно)
amount: Decimal             # Сумма (обязательно, > 0)
category_id: Integer        # FK к Category (nullable)
priority: Integer           # 1=фокус, 2=потом (default=1, check constraint)
status: String(20)          # "new" | "planned" (default="new")
planned_date: Date          # Дата запланирована (nullable)
planned_transaction_id: Integer  # FK к Transaction (nullable, ON DELETE SET NULL)
```

**Relationships**:
- user (N:1)
- category_rel (N:1, nullable)
- planned_transaction (N:1, nullable, ondelete=SET NULL)

**Indexes**:
- ix_wishlist_user_priority на (user_id, priority, status) для фильтрации

**Orphan Detection**: При удалении Transaction → planned_transaction_id становится NULL, callback сбрасывает статус

---

Детали: `architecture.md`, `tech-stack.md` (SQLAlchemy 2.0.23)
