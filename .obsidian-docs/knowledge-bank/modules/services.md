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
- `create_transaction(user_id, amount, transaction_type, transaction_date, description, category_id)` - создание
- `get_by_id(transaction_id)` - получение по ID
- `get_all_by_user(user_id, transaction_type, start_date, end_date)` - список с фильтрацией
- `update_transaction(transaction_id, **kwargs)` - обновление
- `delete_transaction(transaction_id)` - удаление

**Bulk операции** (Протокол 0010):
- `bulk_update_category(transaction_ids, category_id, user_id)` → `int`
  - Массовое назначение категории (max 100 транзакций)
  - Валидация ownership, исключает recurring шаблоны
- `export_to_csv(user_id, start_date, end_date, category_id, uncategorized_only)` → `bytes`
  - CSV экспорт с UTF-8 BOM для Excel
  - Формат: Дата, Тип, Сумма, Описание, Категория

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
- `create_goal(user_id, name, target_amount, target_date, priority=None)` - создание цели
  - priority авто-генерируется через get_next_priority() если None
- `get_by_id(goal_id)` - получение по ID
- `get_all_by_user(user_id)` - список целей пользователя (сортировка по priority ASC)
- `update_goal(goal_id, **kwargs)` - обновление
- `delete_goal(goal_id)` - удаление
- `get_contributions(goal_id)` - получить все взносы цели
- `delete_contribution(contribution_id)` - удаляет взнос, синхронизирует Goal.current_amount, пересчитывает exception (Протокол 0018)

**Contributions**:
- `add_contribution(goal_id, amount, contribution_date)` - добавление взноса
  - Автоматически обновляет `goal.current_amount`
  - Автоматически меняет статус на COMPLETED если достигнута

**Priority Management** (Протокол 0006):
- `get_next_priority(user_id)` - возвращает max(priority) + 1
- `update_priority(goal_id, new_priority)` - shift-down алгоритм для переприоритизации
- `move_priority_up(goal_id)` - уменьшает priority на 1 (повышает важность)
- `move_priority_down(goal_id)` - увеличивает priority на 1 (понижает важность)

**Budget Management** (Протокол 0006):
- `get_savings_budget(user_id)` - получает User.monthly_savings_budget
- `update_savings_budget(user_id, budget)` - обновляет бюджет с валидацией >= 0

**Savings Mode** (Протокол 0007):
- `get_savings_mode(user_id)` - возвращает режим накоплений (free/medium/strict)
- `update_savings_mode(user_id, mode)` - обновляет режим с валидацией

**Валидация**:
- target_amount > 0
- target_date в будущем (минимум 7 дней от сегодня)
- contribution amount > 0
- budget >= 0
- savings_mode в {"free", "medium", "strict"}

**Пример использования**:
```python
service = GoalService(session)

# Создание цели (priority авто-генерируется)
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

# Настройка бюджета накоплений
service.update_savings_budget(user_id=1, budget=Decimal('15000.00'))

# Изменение режима накоплений
service.update_savings_mode(user_id=1, mode="medium")

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

## CalendarService (Фаза 3 + Протокол 0015 — ЗАВЕРШЕНА)

**Файл**: `app/services/calendar_service.py` (~330 строк после протокола 0015)

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
- `get_balance_on_date(user_id, target_date)` → `Decimal`
  - Баланс на конец указанного дня (включительно)
- `get_year_summary(user_id, year)` → `YearSummary`
  - Агрегация за год: total_income, total_expense, start_balance, end_balance
- `get_all_transactions_for_period(user_id, start_date, end_date)` → `list[TransactionInfo]` (Протокол 0015 — возвращает TypedDict)
  - Все транзакции + виртуальные recurring экземпляры за период
  - **КРИТИЧНО**: исключает recurring шаблоны (is_recurring=True, recurring_parent_id=None)
  - **NEW**: Возвращает TransactionInfo с полями is_skipped, category_icon для tooltip UI
- `get_recurring_income_expense_by_day(user_id, start_date, end_date)` → `dict[date, tuple[Decimal, Decimal]]` **(Протокол 0022 — PUBLIC)**
  - Публичная обёртка над _get_recurring_instances_for_period()
  - Возвращает (income, expense) по дням только для recurring операций
  - Guard: ADJUSTMENT recurring практически невозможен (защита от некорректных данных)

**TypedDict**:
```python
class MonthSummary(TypedDict):
    total_income: Decimal
    total_expense: Decimal
    start_balance: Decimal
    end_balance: Decimal

class YearSummary(TypedDict):
    total_income: Decimal
    total_expense: Decimal
    start_balance: Decimal
    end_balance: Decimal

# Протокол 0015: расширен TransactionInfo
class TransactionInfo(TypedDict):
    id: int
    user_id: int
    amount: Decimal
    transaction_type: str
    transaction_date: str          # ISO format
    description: str | None
    category_id: int | None
    category_name: str | None
    category_icon: str | None      # NEW (0015): для emoji в tooltip
    is_recurring: bool
    recurring_parent_id: int | None
    original_date: str | None      # ISO format
    is_virtual: bool
    template_id: int | None
    is_skipped: bool               # NEW (0015): для strikethrough в tooltip
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

    # Баланс на конкретную дату
    balance = service.get_balance_on_date(user_id=1, target_date=date(2026, 1, 15))
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

**Unit тесты**: 19 тестов в `tests/test_calendar_service.py`
- Покрытие: пустые данные, один день, несколько дней, TRANSFER исключение, get_balance_on_date, get_year_summary

## RecurringService (Батч 2 + Протокол 0015 — ЗАВЕРШЕН)

**Файл**: `app/services/recurring_service.py` (~570 строк после протокола 0015)

**Инициализация**: `RecurringService(session)` - принимает SQLAlchemy session

**Константы**:
```python
MAX_INSTANCES_PER_CALL = 1000  # Защита от DoS
MAX_FORECAST_DAYS = 366        # Горизонт прогноза
VALID_RECURRING_PERIODS = {"weekly", "biweekly", "monthly", "quarterly"}
```

**Методы**:
- `get_templates_for_user(user_id)` → `list[Transaction]`
  - Получить все шаблоны (is_recurring=True, recurring_parent_id=None)
- `generate_instances(template, start_date, end_date)` → `list[VirtualTransaction]`
  - Anchored-алгоритм генерации виртуальных экземпляров
  - Сохраняет исходный день месяца при переходе (31 янв → 28 фев → 31 мар)
  - **NEW (0015)**: Заполняет is_skipped=False, category_icon из template.category_rel
- `get_instances_with_exceptions(template, start_date, end_date)` → `list[Transaction | VirtualTransaction]`
  - Объединяет виртуальные экземпляры с exceptions
  - Заменяет виртуальные на exceptions если есть
  - Исключает is_skipped=True
- `create_exception(template_id, instance_date, **kwargs)` → `Transaction`
  - Создать/обновить exception для конкретной даты
- `skip_instance(template_id, instance_date)` → `Transaction`
  - Пометить экземпляр как пропущенный (is_skipped=True)
- `stop_template(template_id, stop_date)` → `Transaction`
  - Остановить серию с определенной даты (soft delete)
- `delete_template(template_id)` → `bool`
  - Удалить шаблон и все exceptions (CASCADE)

**VirtualTransaction TypedDict** (Протокол 0015 — расширен):
```python
class VirtualTransaction(TypedDict):
    template_id: int
    user_id: int
    instance_date: str       # ISO format
    amount: str              # Decimal as string (JSON)
    transaction_type: str    # "income" | "expense"
    description: str | None
    is_virtual: bool         # Всегда True
    is_skipped: bool         # NEW (0015): для strikethrough в tooltip
    category_icon: str | None  # NEW (0015): для emoji в tooltip
```

**Anchored-алгоритм**:
```
Шаблон с 31 января:
- Февраль: min(31, 28) = 28
- Март: min(31, 31) = 31
- Апрель: min(31, 30) = 30
```

**Пример использования**:
```python
from app.services import RecurringService

with get_db_session() as session:
    service = RecurringService(session)

    # Получить виртуальные экземпляры
    templates = service.get_templates_for_user(user_id=1)
    for template in templates:
        instances = service.get_instances_with_exceptions(
            template, start_date, end_date
        )

    # Пропустить экземпляр
    service.skip_instance(template_id=5, instance_date=date(2026, 2, 15))
    session.commit()
```

**Unit тесты**: 28 тестов в `tests/test_recurring_service.py`
- Покрытие: generate, exceptions, skip, stop, delete, anchored edge cases

## DashboardService (Фаза 4 + Протокол 0022-0023 — ЗАВЕРШЕНА)

**Файл**: `app/services/dashboard_service.py` (~700 строк после протокола 0023)

**Инициализация**: `DashboardService(session)` - принимает SQLAlchemy session

**Методы**:
- `get_overview_metrics(user_id, period, reference_date)` → `OverviewMetrics`
  - Агрегирует balance, income, expense, savings за указанный период
  - Использует CalendarService и GoalService (composition)
  - period: "month" или "year"
- `get_cashflow_data(user_id, period, reference_date)` → `list[CashflowDataPoint]`
  - period="month": последние 12 месяцев
  - period="year": последние 5 лет
  - Один SQL-запрос с GROUP BY (оптимизация)
- `get_recent_transactions(user_id, limit, reference_date=None)` → `list[RecentTransaction]` **(Протокол 0023 — рефакторинг)**
  - Транзакции за текущий месяц ДО reference_date (не включая), DESC sort
  - **NEW**: reference_date параметр для фильтрации (default: today)
  - Month range filter: first_of_month..reference_date
  - Recurring фильтр: исключает шаблоны (is_recurring=True, recurring_parent_id=None), включает instances
  - Маппинг через _map_transactions() helper
- `get_upcoming_transactions(user_id, limit, reference_date=None)` → `list[RecentTransaction]` **(Протокол 0023 — NEW)**
  - Транзакции ПОСЛЕ reference_date (включая) до конца месяца, ASC sort
  - Month range filter: reference_date..end_of_month
  - Аналогичный recurring фильтр как в get_recent_transactions
  - Маппинг через _map_transactions() helper
- `get_daily_cashflow(user_id, year, month)` → `MonthlyCashflowData` **(Протокол 0022)**
  - Дневной cashflow с running balance для одного месяца
  - Merge regular + recurring операций по дням
  - Расчет min_balance и min_balance_date для маркера на графике
  - Классификация статуса баланса (ok/attention/risk)
- `get_yearly_cashflow(user_id, year)` → `YearlyCashflowData` **(Протокол 0022)**
  - Cashflow по месяцам за год с end-of-month балансами
  - **Оптимизация**: один calculate_daily_balances(Jan 1, Dec 31) вместо 12x
  - Агрегация recurring через protected _get_recurring_totals_for_period()
  - Классификация статуса для каждого месяца

**TypedDicts**:
```python
class OverviewMetrics(TypedDict):
    total_balance: Decimal
    period_income: Decimal
    period_expense: Decimal
    savings_amount: Decimal | None
    savings_name: str | None

class CashflowDataPoint(TypedDict):
    period_label: str
    income: Decimal
    expense: Decimal

class RecentTransaction(TypedDict):  # Протокол 0023: расширен
    id: int
    date: str
    description: str | None
    amount: Decimal
    type: str
    is_recurring_instance: bool  # NEW: для иконки 🔁 в таблице

# Протокол 0022: новые TypedDicts см. schema.md
# MonthlyCashflowData, YearlyCashflowData, DailyCashflow, DailyBalancePoint, MonthlyCashflow
```

**Пример использования**:
```python
from app.services import DashboardService

with get_db_session() as session:
    service = DashboardService(session)

    # Метрики за месяц
    metrics = service.get_overview_metrics(
        user_id=1, period="month", reference_date=date.today()
    )

    # Дневной cashflow за январь 2026 (Протокол 0022)
    daily = service.get_daily_cashflow(user_id=1, year=2026, month=1)
    # {"month": "2026-01", "daily_cashflow": [...], "min_balance": "12500.00", ...}

    # Годовой cashflow за 2026 (Протокол 0022)
    yearly = service.get_yearly_cashflow(user_id=1, year=2026)
    # {"year": 2026, "monthly_data": [12 месяцев], "min_balance": "8000.00", ...}
```

**Внутренние методы** (Протокол 0022-0023):
- `_classify_balance_status(balance)` → `BalanceStatus`
  - Классификация по порогам BALANCE_RISK/ATTENTION_THRESHOLD
  - "risk" < 5000, "attention" 5000-15000, "ok" ≥ 15000
- `_get_daily_income_expense(user_id, start_date, end_date)` → `dict[date, tuple[Decimal, Decimal]]`
  - SQL агрегация с CASE для INCOME/EXPENSE/SAVINGS/ADJUSTMENT
  - GROUP BY transaction_date
  - **ADJUSTMENT logic**: amount > 0 → income, amount < 0 → expense(abs)
- `_get_monthly_income_expense(user_id, year, month)` → `tuple[Decimal, Decimal]`
  - Переиспользует _get_daily_income_expense() с sum() (рекомендация critique)
- `_map_transactions(results)` → `list[RecentTransaction]` **(Протокол 0023 — NEW)**
  - Helper для маппинга SQLAlchemy results → RecentTransaction TypedDict
  - Устраняет дублирование между get_recent_transactions и get_upcoming_transactions
  - Добавляет is_recurring_instance: bool поле

**Composition Pattern**: DashboardService содержит CalendarService и GoalService

**Критичные детали** (Протокол 0022):
- **ADJUSTMENT классификация**: положительная корректировка → income, отрицательная → expense (documented в docstring)
- **Year mode оптимизация**: один SQL расчет балансов (Jan 1 - Dec 31) вместо 12 отдельных запросов
- **Protected access допустим**: _get_recurring_totals_for_period() из CalendarService (тот же сервисный слой)
- **Min balance tracking**: сквозной поиск минимального баланса для diamond marker на графике
- **End-of-month балансы**: для Year mode берется balance[last_day_of_month] из calculate_daily_balances()

**Unit тесты**: 44 тестов в `tests/test_dashboard_service.py` (19 старых + 16 протокол 0022 + 9 протокол 0023)
- TestGetDailyCashflow: 12 тестов (basic, no txn, status classification, min tracking, cumulative, adjustment/transfer/savings)
- TestGetYearlyCashflow: 4 теста (12 months, income/expense, end balance, min year)
- TestGetRecentTransactionsRefactored: 3 теста (reference_date filter, recurring filter, month boundary) **(Протокол 0023)**
- TestGetUpcomingTransactions: 6 тестов (basic, limit, recurring, no upcoming, across months, past ref date) **(Протокол 0023)**

## AllocationService (Батч 2 — ЗАВЕРШЕН)

**Файл**: `app/services/allocation_service.py` (~200 строк)

**Константы**:
```python
SAVINGS_MODE_MULTIPLIERS = {
    "free": 1.0,    # минимальные взносы точно по графику
    "medium": 1.15, # +15% буфер для страховки
    "strict": 1.5   # агрессивные накопления
}
```

**Инициализация**: `AllocationService(session)` - принимает SQLAlchemy session

**Методы**:
- `calculate_allocation(user_id, savings_mode="free")` → `AllocationSummary`
  - Жадный алгоритм распределения бюджета по приоритетам
  - Применяет множитель savings_mode к monthly_contribution каждой цели
  - Обрабатывает статусы: COMPLETED, PAUSED, zero_contribution → skipped

**Жадный алгоритм**:
```
1. Сортировка целей по priority ASC (1, 2, 3...)
2. Для каждой цели:
   - monthly_needed = goal.monthly_contribution * SAVINGS_MODE_MULTIPLIERS[mode]
   - allocated = min(monthly_needed, budget_remaining)
   - budget_remaining -= allocated
3. Возврат AllocationSummary с детализацией
```

**TypedDict**: `AllocationSummary`, `AllocationResult` (см. [schema.md])

**Пример использования**:
```python
from app.services import AllocationService

with get_db_session() as session:
    service = AllocationService(session)

    # Распределение в режиме "free"
    summary = service.calculate_allocation(user_id=1, savings_mode="free")
    # summary['all_goals_funded'] → True/False
    # summary['results'] → список AllocationResult для каждой цели

    # Распределение в режиме "strict"
    summary = service.calculate_allocation(user_id=1, savings_mode="strict")
```

**Unit тесты**: 10 тестов в `tests/test_allocation_service.py`
- Покрытие: все сценарии распределения, режимы free/medium/strict, edge cases

## RedistributionService (Протокол 0008 — ЗАВЕРШЕН, PR #8)

**Файл**: `app/services/redistribution_service.py` (~200 строк)

**Инициализация**: `RedistributionService(session, allocation_service)` - DI pattern

**Методы**:
- `calculate_redistribution_preview(completed_goal, monthly_budget, savings_mode)` → `RedistributionPreview`
  - Рассчитывает OLD и NEW allocation при достижении цели
  - Использует "Temporary Status Pattern" для временного изменения статуса цели
  - Определяет freed_budget через _get_freed_budget_from_allocation()
  - Возвращает полный preview с has_remaining_goals, timing информацией
- `log_redistribution_event(...)` → `RedistributionEvent`
  - Аудит-логирование события (NFR-4)
  - Поддерживает два способа вызова: с preview или с развернутыми параметрами
  - action: "confirmed" | "declined"

**Temporary Status Pattern**:
```python
original_status = completed_goal.status
try:
    completed_goal.status = GoalStatus.ACTIVE  # Временно восстанавливаем
    old_allocation = allocation_service.calculate_allocation(...)
finally:
    completed_goal.status = original_status  # Гарантированно восстанавливаем
```

**TypedDicts**: `RedistributionPreview`, `RedistributionEvent` (см. [schema.md])

**Пример использования**:
```python
from app.services import RedistributionService, AllocationService

with get_db_session() as session:
    allocation_service = AllocationService(session)
    service = RedistributionService(session, allocation_service)

    # Расчет preview при достижении цели
    preview = service.calculate_redistribution_preview(
        completed_goal=goal,
        monthly_budget=Decimal("15000"),
        savings_mode="free"
    )

    # Логирование события
    service.log_redistribution_event(
        preview=preview,
        action="confirmed",
        new_allocation=preview["new_allocation"]
    )
```

**NFR (Non-Functional Requirements)**:
- NFR-1: Preview за < 100ms (timing logs)
- NFR-2: WARNING при > 50ms через loguru
- NFR-4: Аудит-логирование событий

**Unit тесты**: 16 тестов в `tests/test_redistribution_service.py`
**Integration тесты**: 7 тестов в `tests/test_redistribution_integration.py`
- Покрытие: preview calculation, temporary status pattern, freed budget, logging, E2E scenarios

## CategoryService (Протокол 0009 — ЗАВЕРШЕН)

**Файл**: `app/services/category_service.py` (~120 строк)

**Инициализация**: `CategoryService(session)` - принимает SQLAlchemy session

**Методы**:
- `get_all(type_filter=None)` → `list[Category]`
  - Все категории, опционально фильтр по type ("income"/"expense"/"both")
  - Сортировка: type ASC, sort_order ASC
- `get_by_id(category_id)` → `Category | None`
  - Получить категорию по ID
- `get_by_type(category_type)` → `list[Category]`
  - Категории конкретного типа (включает "both")
- `get_for_dropdown(category_type)` → `list[CategoryOption]`
  - Для UI dropdown: возвращает CategoryOption TypedDict
- `get_system_category(name)` → `Category | None`
  - Получить системную категорию по имени (например "Коррекция")
- `seed_default_categories()` → `int`
  - Идемпотентный seed 16 предустановленных категорий
  - Возвращает количество добавленных
- `get_frequent_for_type(user_id, category_type, limit=6)` → `list[CategoryOption]` (Протокол 0010)
  - Часто используемые категории пользователя для chips UI
  - SQL агрегация COUNT transactions по category_id
  - Fallback на sort_order при cold start (< 3 транзакций)

**TypedDict**:
```python
class CategoryOption(TypedDict):
    value: int        # category.id
    label: str        # category.name
    icon: str         # category.icon
```

**Пример использования**:
```python
from app.services import CategoryService

with get_db_session() as session:
    service = CategoryService(session)

    # Для dropdown в форме создания expense
    options = service.get_for_dropdown("expense")
    # [{"value": 1, "label": "Еда и продукты", "icon": "bi-cart"}, ...]

    # Seed категорий (idempotent)
    added = service.seed_default_categories()
```

**Unit тесты**: 20 тестов в `tests/test_category_service.py` (включая 5 для get_frequent_for_type)

## ReconciliationService (Протокол 0009 — ЗАВЕРШЕН)

**Файл**: `app/services/reconciliation_service.py` (~100 строк)

**Инициализация**: `ReconciliationService(session)` - принимает SQLAlchemy session

**Методы**:
- `get_expected_balance(user_id, target_date)` → `Decimal`
  - Расчетный баланс на указанную дату
  - Использует CalendarService.get_balance_on_date()
- `calculate_preview(user_id, target_date, actual_balance)` → `ReconciliationPreview`
  - Preview для модала сверки
  - Вычисляет разницу и explanation текст
- `create_adjustment(user_id, target_date, actual_balance, category_id=None)` → `Transaction | None`
  - Создает ADJUSTMENT транзакцию
  - Возвращает None если разница = 0
  - По умолчанию использует системную категорию "Коррекция"

**TypedDict**:
```python
class ReconciliationPreview(TypedDict):
    expected_balance: str      # Decimal as string
    actual_balance: str        # Decimal as string
    difference: str            # Decimal as string (actual - expected)
    explanation: str           # Текст для UI
    target_date: str           # ISO date
```

**Пример использования**:
```python
from app.services import ReconciliationService

with get_db_session() as session:
    service = ReconciliationService(session)

    # Preview для модала
    preview = service.calculate_preview(
        user_id=1,
        target_date=date.today(),
        actual_balance=Decimal("14200")
    )
    # {"difference": "-800.00", "explanation": "Фактический баланс меньше...", ...}

    # Создание корректировки
    adjustment = service.create_adjustment(
        user_id=1,
        target_date=date.today(),
        actual_balance=Decimal("14200")
    )
    session.commit()
```

**Unit тесты**: 11 тестов в `tests/test_reconciliation_service.py`

## Критичные решения

**D010**: Session management через flush() вместо commit() для гибкости caller

**BUG-001**: Seed script должен использовать GoalService.add_contribution вместо hardcoded current_amount

**BUG-003**: target_date валидация - минимум 7 дней от сегодня

**Фаза 3**: TRANSFER транзакции исключаются из CalendarService расчетов баланса

**Протокол 0006**: Удалено ограничение D009 (одна активная цель), добавлены приоритеты и AllocationService

**Протокол 0007**: Добавлены режимы накоплений (free/medium/strict) с множителями

**Протокол 0008**: RedistributionService для перераспределения бюджета при достижении цели

**Протокол 0009**: CategoryService и ReconciliationService для категоризации и сверки баланса

**Протокол 0010**: AnalyticsService для аналитики расходов + bulk_update_category/export_to_csv в TransactionService

## AnalyticsService (Протокол 0010 — ЗАВЕРШЕН)

**Файл**: `app/services/analytics_service.py` (~290 строк)

**Инициализация**: `AnalyticsService(session)` - принимает SQLAlchemy session

**Константы**:
```python
MIN_PERCENTAGE_THRESHOLD = 3.0  # Порог для группировки в "Прочее"
MONTH_LABELS_RU = {1: "Янв", 2: "Фев", ...}  # Русские названия месяцев
```

**Методы**:
- `get_expenses_by_category(user_id, start_date, end_date, group_small=True)` → `list[CategorySummary]`
  - SQL GROUP BY агрегация с LEFT JOIN на Category
  - Исключает шаблоны recurring (is_recurring=True)
  - При group_small=True категории < 3% объединяются в "Прочее"
- `get_monthly_trends(user_id, months=6, reference_date=None)` → `list[MonthlyTrend]`
  - Тренды расходов за N месяцев для bar chart
  - Каждый месяц содержит агрегацию по категориям
- `get_uncategorized_count(user_id)` → `int`
  - Количество транзакций без категории

**TypedDicts** (app/schema/analytics.py):
```python
class CategorySummary(TypedDict):
    category_id: int | None
    category_name: str
    category_icon: str | None
    total: Decimal
    percentage: float
    count: int

class MonthlyTrend(TypedDict):
    month: str           # "2026-01"
    month_label: str     # "Янв"
    categories: list[CategorySummary]
    total: Decimal
```

**Пример использования**:
```python
from app.services import AnalyticsService

with get_db_session() as session:
    service = AnalyticsService(session)

    # Структура расходов за январь
    expenses = service.get_expenses_by_category(
        user_id=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31)
    )
    # [{"category_name": "Еда", "total": Decimal("18000"), "percentage": 40.0}, ...]

    # Динамика за 6 месяцев
    trends = service.get_monthly_trends(user_id=1, months=6)

    # Количество некатегоризированных
    count = service.get_uncategorized_count(user_id=1)
```

**Unit тесты**: 16 тестов в `tests/test_analytics_service.py`
- Покрытие: агрегация, группировка мелких категорий, uncategorized, monthly trends

## OnboardingService (Протокол 0014 + Протокол 0024 — расширен)

**Файл**: `app/services/onboarding_service.py` (~130 строк после протокола 0024)

**Инициализация**: `OnboardingService(session)` - принимает SQLAlchemy session

**Методы**:
- `get_status(user_id)` → `OnboardingStatus`
  - Возвращает статус onboarding пользователя
  - first_launch — требуется ли показ wizard
  - starting_balance — текущий баланс
  - needs_balance_alert — показывать ли toast (balance=0; условие first_launch убрано из кода — см. onboarding_service.py:80)
  - **NEW (0024)**: name, avatar_id — для sidebar и dashboard greeting
- `complete(user_id, name, avatar_id, starting_balance)` → `None` **(NEW 0024 — заменяет complete_with_balance)**
  - Завершение onboarding с именем + аватаром + балансом
  - Валидация через `_validate_profile_fields(name, avatar_id)`
  - Обновляет User.first_launch=False, name, avatar_id, starting_balance
  - **Flush/commit contract**: session.flush(), caller commit()
- `complete_with_balance(user_id, starting_balance)` → `None` **(deprecated, для совместимости)**
- `skip(user_id)` → `None`
  - Пропуск onboarding (для опытных пользователей)
  - Обновляет User.first_launch=False, starting_balance остается 0
  - **Flush/commit contract**: session.flush(), caller commit()
- `update_profile(user_id, name, avatar_id)` → `None` **(NEW 0024)**
  - Обновление профиля (имя + аватар) в любой момент (не только при onboarding)
  - Валидация через `_validate_profile_fields()`
  - Доступно через ProfileModal
- `get_profile(user_id)` → `UserProfile` **(NEW 0024)**
  - Возвращает `{"name": ..., "avatar_id": ...}` для ProfileModal
- `_validate_profile_fields(name, avatar_id)` → `None` **(NEW 0024)**
  - Приватная валидация: name непустое; avatar_id в списке `app/config/avatars.AVATARS`
  - Поднимает ValidationError

**TypedDict** (app/schema/onboarding.py):
```python
class OnboardingStatus(TypedDict):
    first_launch: bool               # Требуется ли wizard
    starting_balance: Decimal        # Текущий баланс
    needs_balance_alert: bool        # Показывать ли toast
    name: str | None                 # NEW (0024): имя пользователя
    avatar_id: str | None            # NEW (0024): ID аватара

class UserProfile(TypedDict):       # NEW (0024)
    name: str
    avatar_id: str
```

**Пример использования**:
```python
from app.services import OnboardingService

with get_db_session() as session:
    service = OnboardingService(session)

    # Проверка статуса
    status = service.get_status(user_id=1)
    # {"first_launch": False, "starting_balance": Decimal("50000"), "name": "Иван", "avatar_id": "cat", ...}

    # Завершение onboarding (протокол 0024)
    service.complete(user_id=1, name="Иван", avatar_id="cat", starting_balance=Decimal("50000"))

    # Обновление профиля после onboarding
    service.update_profile(user_id=1, name="Иван", avatar_id="fox")

    # Получение профиля для ProfileModal
    profile = service.get_profile(user_id=1)
    # {"name": "Иван", "avatar_id": "fox"}
```

**Критичные детали**:
- **Flush/commit contract**: сервис вызывает session.flush() для валидации и ID generation, caller управляет commit() через context manager
- **Fail-closed DB strategy**: UI callback скрывает wizard при ошибке БД, не блокирует приложение
- **needs_balance_alert logic**: True если balance=0 (условие first_launch в коде отсутствует — onboarding_service.py:80; доки исправлены при ревью 0026)
- **avatar_id валидация**: проверяется против `app/config/avatars.AVATARS` dict (не произвольные строки)

**Unit тесты**: расширены в `tests/test_onboarding_service.py` (протокол 0024 добавил тесты для complete(), update_profile(), get_profile(), _validate_profile_fields())

---

## BudgetReservationService (Протокол 0016-0018 — ЗАВЕРШЕН)

**Файл**: `app/services/budget_reservation_service.py` (~600 строк после протокола 0018)

**Инициализация**: `BudgetReservationService(session)` - принимает SQLAlchemy session

**Константы**:
```python
VALID_RESERVATION_MODES = {"fixed_date", "from_balance"}
MIN_RESERVATION_DAY = 1
MAX_RESERVATION_DAY = 28  # Безопасно для всех месяцев
RESERVE_DESCRIPTION = "Резервирование бюджета"  # Протокол 0017
```

**Методы**:
- `get_settings(user_id)` → `BudgetReservationSettings`
  - Возвращает текущие настройки резервирования пользователя
  - mode — "fixed_date" или "from_balance"
  - day — день месяца для fixed_date режима (1-28)
- `set_mode(user_id, mode, day=None)` → `None`
  - Изменение режима резервирования
  - **NEW (Протокол 0018)**: переиспользует шаблон если день совпадает (exceptions сохраняются)
  - В режиме fixed_date создаёт/обновляет recurring шаблон "Резервирование бюджета"
  - В режиме from_balance останавливает recurring шаблон (но НЕ чистит exceptions)
  - Валидация: mode in VALID_MODES, day в диапазоне [1, 28]
- `recalculate_current_month_exception(user_id, reference_date=None)` → `bool` **(Протокол 0018)**
  - Пересчитывает exception для указанного месяца после изменений
  - Вызывается при удалении взноса, изменении суммы взноса, изменении бюджета
  - Логика: contributions_sum до reserve_date → new_reserve = budget - contributions_sum
  - Если contributions_sum == 0 → удаляет exception, иначе создаёт/обновляет
- `get_budget_progress(user_id, year, month)` → `BudgetProgress`
  - Возвращает прогресс использования бюджета за месяц
  - total_budget — User.monthly_savings_budget
  - contributions_sum — сумма взносов за месяц (через GoalContribution)
  - remaining_budget — доступный остаток
  - all_allocated — все цели получили полное финансирование (True/False)
  - records — список ContributionRecord (цель, взнос, дата)
- `create_contribution_transaction(user_id, goal_id, amount, date, contribution_id=None)` → `Transaction`
  - Создаёт SAVINGS_CONTRIBUTION транзакцию в режиме from_balance
  - Связывает с GoalContribution через transaction_id
  - description = "Взнос: {goal.name}"
- `update_contribution_transaction(contribution_id, new_amount)` → `None`
  - Синхронизирует Transaction ↔ GoalContribution ↔ Goal.current_amount
  - Обновляет все 3 сущности атомарно
- `delete_contribution_transaction(contribution_id)` → `None`
  - Каскадное удаление Transaction + GoalContribution с обновлением Goal
- `sync_template_amount(user_id)` → `None`
  - Синхронизация суммы recurring шаблона "Резервирование бюджета" с User.monthly_savings_budget
  - Используется при изменении бюджета в режиме fixed_date
- `adjust_reserve_for_contribution(user_id, contribution_amount, contribution_date)` → `None` **(Протокол 0017)**
  - Коррекция резерва при досрочных взносах в режиме fixed_date
  - Если взнос ДО даты резерва → создаёт Exception для recurring с уменьшенной суммой
  - Новая сумма = original_amount - SUM(contributions_before_reserve_date)
  - Если взносы ≥ бюджета → description "(внесено досрочно)", сумма 0
  - В режиме from_balance ничего не делает (guard clause)

**TypedDicts** (app/schema/budget_reservation.py):
```python
ReservationMode = Literal["fixed_date", "from_balance"]

class BudgetReservationSettings(TypedDict):
    mode: ReservationMode
    day: int | None

class BudgetProgress(TypedDict):
    total_budget: Decimal
    contributions_sum: Decimal
    remaining_budget: Decimal
    all_allocated: bool
    records: list[ContributionRecord]

class ContributionRecord(TypedDict):
    goal_name: str
    amount: Decimal
    date: str  # ISO format
```

**Пример использования**:
```python
from app.services import BudgetReservationService

with get_db_session() as session:
    service = BudgetReservationService(session)

    # Получить настройки
    settings = service.get_settings(user_id=1)
    # {"mode": "from_balance", "day": None}

    # Изменить режим на fixed_date с днём 5
    service.set_mode(user_id=1, mode="fixed_date", day=5)
    # Создан recurring шаблон "Резерв на цели" на 5-е число

    # Прогресс бюджета за месяц
    progress = service.get_budget_progress(user_id=1, year=2026, month=2)
    # {"total_budget": Decimal("15000"), "contributions_sum": Decimal("8000"), ...}

    # Создать взнос с транзакцией (режим from_balance)
    tx = service.create_contribution_transaction(
        user_id=1,
        goal_id=5,
        amount=Decimal("3000"),
        date=date(2026, 2, 15),
        contribution_id=12
    )
    # Создана SAVINGS_CONTRIBUTION транзакция "Взнос: Отпуск"

    session.commit()
```

**Внутренние методы**:
- `_get_reserve_template(user_id)` → `Transaction | None` — получение активного шаблона резервирования
- `_find_any_reserve_template(user_id)` → `Transaction | None` — **NEW (0018)**: поиск любого шаблона (включая остановленный)
- `_get_template_day(template)` → `int` — **NEW (0018)**: извлечение дня из шаблона (EOM → 31)
- `_get_reserve_date_for_month(user_id, reference_date)` → `date | None` — **NEW (0018)**: дата резерва с учётом коротких месяцев
- `_delete_exception_for_date(template_id, target_date)` → `bool` — **NEW (0018)**: удаление exception для даты
- `_cleanup_orphan_exceptions(template_id)` → `int` — **NEW (0018)**: удаление orphan exceptions с логированием
- `_create_reserve_template(user_id, day)` → `Transaction` — создание recurring шаблона
- `_stop_reserve_template(user_id)` → `None` — остановка шаблона (set recurring_end_date)

**Критичные детали**:
- **Два режима резервирования**:
  - **fixed_date** — вся сумма бюджета резервируется в календаре на указанную дату (recurring операция)
  - **from_balance** — операции создаются только при взносах в цели
- **Динамический бюджет**: `remaining = total_budget - SUM(contributions этого месяца)`
- **FK связь**: GoalContribution.transaction_id → Transaction.id (SET NULL при удалении транзакции)
- **Синхронизация**: update/delete contribution → синхронизация Transaction + GoalContribution + Goal.current_amount
- **SAVINGS операции не влияют на расчет целей**, но уменьшают баланс в календаре
- **Validation**: day в диапазоне [1, 28] для безопасности (февраль)
- **adjust_reserve_for_contribution (Протокол 0017)**:
  - Создаёт Exception для recurring шаблона при досрочном взносе (до reserve_date)
  - Exception сумма = original_amount - SUM(contributions_before_reserve_date)
  - Description "(внесено досрочно)" когда взносы покрыли бюджет полностью
  - Guard: ничего не делает в режиме from_balance
- **Переиспользование шаблонов (Протокол 0018)**:
  - set_mode() переиспользует шаблон если день совпадает (exceptions сохраняются)
  - from_balance → fixed_date → exceptions НЕ чистятся при переключении на from_balance
  - Изменение дня → stop старый + cleanup orphan exceptions + create new
- **recalculate_current_month_exception (Протокол 0018)**:
  - Вызывается при delete_contribution, update_contribution, изменении бюджета
  - Пересчитывает exception только для будущих дат (reserve_date > today)
  - Если contributions_sum == 0 → удаляет exception, иначе создаёт/обновляет

**Unit тесты**: 45 тестов в `tests/test_budget_reservation_service.py` (было 32, +13 для протокола 0018)
- TestGetSettings (4), TestSetMode (6), TestGetBudgetProgress (4)
- TestCRUD (12): create/update/delete contribution transactions
- TestAdjustReserveForContribution (6): досрочные взносы, edge cases (Протокол 0017)
- TestFindAnyReserveTemplate (4), TestGetTemplateDay (2) — **NEW (0018)**
- TestCleanupOrphanExceptions (2), TestRecalculateCurrentMonthException (4) — **NEW (0018)**
- TestUpdateContributionRecalc (1) — **NEW (0018)**

**Integration тесты**: 3 теста в `tests/test_budget_calendar_integration.py` (Протокол 0018)
- test_contribution_before_reserve_reduces_reserve_in_calendar — E2E взнос до резерва
- test_contribution_after_mode_switch_updates_reserve — E2E переключение режимов
- test_delete_contribution_restores_reserve — E2E удаление взноса

**Integration с другими сервисами**:
- GoalService: add_contribution() создаёт SAVINGS_CONTRIBUTION через BudgetReservationService (from_balance) и вызывает adjust_reserve_for_contribution() (fixed_date)
- CalendarService: _calculate_balance_before_date() и _get_daily_changes() обрабатывают SAVINGS типы
- RecurringService: генерирует виртуальные экземпляры для "Резервирование бюджета" шаблона, создаёт Exceptions при adjust_reserve

---

## CushionService (Протокол 0013 — ЗАВЕРШЕН)

**Файл**: `app/services/cushion_service.py` (~180 строк)

**Инициализация**: `CushionService(session)` - принимает SQLAlchemy session

**Константы**:
```python
DEFAULT_THRESHOLD_PERCENT: Percent = 30  # Порог риска по умолчанию
VALID_CALC_MODES = {"sum", "max_scenario"}  # Режимы калькулятора
```

**Методы**:
- `get_settings(user_id)` → `CushionSettings`
  - Возвращает настройки подушки с вычисляемыми полями
  - progress_percent — текущий прогресс (User.current_balance / cushion_target)
  - threshold_amount — сумма порога (auto из percent или manual)
  - status — 4 варианта: "not_configured", "danger", "warning", "info", "success"
- `update_settings(user_id, target, threshold_percent, threshold_manual)` → `None`
  - Обновление настроек с валидацией
  - Валидация: target >= 0, threshold_percent в [0, 100]
- `reset_settings(user_id)` → `None`
  - Сброс к default: target=0, threshold=30%, manual=None
- `calculate_recommendation(user_id, scenarios, calc_mode)` → `Decimal`
  - Расчет рекомендации по сценариям
  - calc_mode="sum" — сумма всех сценариев
  - calc_mode="max_scenario" — максимальный из сценариев
  - Валидация: calc_mode in VALID_CALC_MODES

**TypedDicts** (app/schema/cushion.py):
```python
Percent = NewType("Percent", int)  # Type alias для 0-100 range

class CushionSettings(TypedDict):
    cushion_target: Decimal | None
    cushion_threshold_percent: Percent
    cushion_threshold_manual: Decimal | None
    current_balance: Decimal
    progress_percent: float  # computed
    threshold_amount: Decimal | None  # computed
    status: str  # computed: "not_configured" | "danger" | "warning" | "info" | "success"

class CushionScenario(TypedDict):
    name: str
    amount: Decimal
```

**Пример использования**:
```python
from app.services import CushionService

with get_db_session() as session:
    service = CushionService(session)

    # Получить настройки
    settings = service.get_settings(user_id=1)
    # {"cushion_target": None, "status": "not_configured", ...}

    # Обновить настройки
    service.update_settings(
        user_id=1,
        target=Decimal("150000"),
        threshold_percent=30,
        threshold_manual=None
    )

    # Расчет рекомендации
    scenarios = [
        {"name": "Продукты", "amount": Decimal("15000")},
        {"name": "Коммуналка", "amount": Decimal("8000")},
    ]
    recommendation = service.calculate_recommendation(
        user_id=1, scenarios=scenarios, calc_mode="sum"
    )
    # Decimal("23000")

    session.commit()
```

**Внутренние методы**:
- `_validate_percent(value)` → `bool` — валидация диапазона 0-100

**Вычисляемые поля**:
- `progress_percent` = (current_balance / cushion_target) * 100, cap at 100%
- `threshold_amount` = threshold_manual OR (cushion_target * threshold_percent / 100)
- `status`:
  - "not_configured" если target is None or 0
  - "danger" если progress < threshold
  - "warning" если threshold <= progress < 50%
  - "info" если 50% <= progress < 100%
  - "success" если progress >= 100%

**Критичные детали**:
- Percent NewType для type safety (IDE и mypy помощь)
- cushion_threshold_manual приоритетнее чем percent (если установлен)
- Прогресс берется из User.current_balance (требует актуализации)
- Подушка НЕ Goal — не участвует в AllocationService распределении

**Unit тесты**: 20 тестов в `tests/test_cushion_service.py`
- TestValidatePercent: 5 тестов (valid 0/30/100, invalid -1/101)
- TestGetSettings: 7 тестов (not configured, configured, threshold_amount, progress, cap 100%, negative balance, user not found)
- TestUpdateSettings: 3 теста (valid, invalid target, invalid percent)
- TestResetSettings: 1 тест
- TestCalculateRecommendation: 4 теста (sum, max_scenario, empty, invalid mode)

---

## WishlistService (Протокол 0020 — ЗАВЕРШЕН)

**Файл**: `app/services/wishlist_service.py` (~270 строк)

**Инициализация**: `WishlistService(session)` - принимает SQLAlchemy session

**CRUD методы**:
- `create_item(user_id, name, amount, category_id=None, priority=1)` → `WishlistItem`
  - Валидация: name (1-100 chars), amount > 0, priority in {1, 2}
- `get_all(user_id)` → `list[WishlistItem]`
  - Сортировка: priority ASC, created_at DESC
- `get_focus(user_id, limit=5)` → `list[WishlistItem]`
  - Только фокусные (priority=1), sorted, limit для Dashboard виджета
- `get_by_id(item_id)` → `WishlistItem | None`
- `update_item(item_id, **updates)` → `WishlistItem`
  - Planned guard: статус "planned" → можно менять только name, priority
- `delete_item(item_id)` → `bool`

**Planning workflow**:
- `mark_as_planned(item_id, planned_date, transaction_id)` → `WishlistItem`
  - status → "planned", сохраняет дату и FK
- `reset_planned(item_id)` → `WishlistItem`
  - status → "new", обнуляет planned_date, planned_transaction_id
- `check_orphaned_planned(user_id)` → `list[WishlistItem]`
  - Поиск хотелок со статусом "planned" и planned_transaction_id=NULL (orphan)

**Utility**:
- `to_data(item)` → `WishlistItemData`
  - Конвертация ORM → TypedDict для Dash UI

**Пример использования**:
```python
from app.services import WishlistService

with get_db_session() as session:
    service = WishlistService(session)

    # Создать хотелку
    item = service.create_item(
        user_id=1,
        name="Аккумулятор",
        amount=Decimal("3500"),
        category_id=5,
        priority=1
    )

    # Получить фокусные для Dashboard
    focus = service.get_focus(user_id=1, limit=5)

    # Запланировать
    service.mark_as_planned(
        item_id=item.id,
        planned_date=date(2026, 2, 15),
        transaction_id=123
    )

    # Обнаружить orphan (после удаления транзакции)
    orphans = service.check_orphaned_planned(user_id=1)
    for orphan in orphans:
        service.reset_planned(orphan.id)

    session.commit()
```

**Критичные детали**:
- **Planned guard**: статус "planned" блокирует изменение amount, category_id, status напрямую
- **Orphan detection**: check_orphaned_planned() для очистки после удаления транзакций
- **Priority constraint**: check(priority IN (1, 2)) на уровне БД
- **to_data()**: сериализация Decimal → string для JSON Store

**Unit тесты**: 31 тест в `tests/test_wishlist_service.py`
- TestCRUD: 9 тестов (create, get_all, get_focus, get_by_id, update, delete)
- TestValidation: 5 тестов (name length, amount, priority, planned guard)
- TestPlanning: 4 теста (mark_as_planned, reset_planned, check_orphaned)
- TestToData: 2 теста (serialization, null handling)

---

## PurchaseRecommendationService (Протокол 0020 — ЗАВЕРШЕН)

**Файл**: `app/services/purchase_recommendation_service.py` (~160 строк)

**Инициализация**: `PurchaseRecommendationService(session)` - принимает SQLAlchemy session

**Константы**:
```python
VALID_REASONS = {"negative_balance", "cushion"}
```

**Методы**:
- `get_safe_dates_map(user_id, amount, year, month)` → `dict[date, SafeDateInfo]`
  - Карта безопасности для каждого дня месяца
  - safe=True если покупка не нарушает threshold подушки И баланс ≥ 0
  - reasons: list["cushion" | "negative_balance"]
  - Формула: min(balance[d:end_month] - amount) для каждого кандидата
- `precalculate_hover_data(user_id, amount, year, month)` → `dict[str, dict[str, str]]`
  - Предрассчет балансов для JS hover (каскадный пересчет)
  - Структура: {candidate_date_iso: {day_iso: balance_str, ...}, ...}
  - base_balances: {day_iso: balance_str} — исходные балансы для восстановления
  - by_candidate: {candidate_date_iso: {day_iso: adjusted_balance_str}}
  - ~960 значений (~30KB) для dcc.Store

**TypedDicts** (app/schema/wishlist.py):
```python
class SafeDateInfo(TypedDict):
    safe: bool
    reasons: list[str]  # ["cushion"] | ["negative_balance"] | обе

class HoverBalances(TypedDict):
    base_balances: dict[str, str]          # Исходные балансы
    by_candidate: dict[str, dict[str, str]] # Каскадный пересчет
```

**Пример использования**:
```python
from app.services import PurchaseRecommendationService

with get_db_session() as session:
    service = PurchaseRecommendationService(session)

    # Карта безопасности дней
    safe_dates = service.get_safe_dates_map(
        user_id=1,
        amount=Decimal("3500"),
        year=2026,
        month=2
    )
    # {date(2026,2,1): {safe: True, reasons: []}, date(2026,2,12): {safe: False, reasons: ["cushion"]}, ...}

    # Данные для hover
    hover_data = service.precalculate_hover_data(
        user_id=1,
        amount=Decimal("3500"),
        year=2026,
        month=2
    )
    # {base_balances: {"2026-02-01": "50000.00", ...}, by_candidate: {"2026-02-05": {"2026-02-05": "46500.00", ...}}}
```

**Внутренние методы**:
- `_is_safe_date(balances, amount, candidate_date, threshold_amount)` — проверка безопасности
- `_get_reasons(balances, amount, candidate_date, threshold_amount)` — список причин

**Интеграция**:
- CalendarService.calculate_daily_balances() — базовые балансы месяца
- CushionService.get_settings() — threshold_amount для проверки подушки

**Критичные детали**:
- **Каскадная проверка**: min(balance[d:end_month]) для всех дней от кандидата до конца месяца
- **Два критерия**: подушка (cushion) И отрицательный баланс (negative_balance)
- **Предрассчет hover**: ~200ms при открытии режима, hover < 1ms на клиенте (clientside JS)
- **Decimal serialization**: все балансы → string для JSON Store

**Unit тесты**: 11 тестов в `tests/test_purchase_recommendation.py`
- TestSafeDatesMap: 5 тестов (safe day, cushion violation, negative balance, both, cushion disabled)
- TestPrecalculateHoverData: 4 теста (structure, base_balances, by_candidate, empty month)
- TestEdgeCases: 2 теста (EOM dates, leap year)

---

Детали: `architecture.md` (Service Layer Pattern), `code-style.md` (Session Management Pattern), `schema.md` (TypedDicts)
