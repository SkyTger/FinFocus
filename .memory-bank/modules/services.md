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
- `get_balance_on_date(user_id, target_date)` → `Decimal`
  - Баланс на конец указанного дня (включительно)
- `get_year_summary(user_id, year)` → `YearSummary`
  - Агрегация за год: total_income, total_expense, start_balance, end_balance
- `get_all_transactions_for_period(user_id, start_date, end_date)` → `list[Transaction]`
  - Все транзакции + виртуальные recurring экземпляры за период
  - **КРИТИЧНО**: исключает recurring шаблоны (is_recurring=True, recurring_parent_id=None)

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

## RecurringService (Батч 2 — ЗАВЕРШЕН)

**Файл**: `app/services/recurring_service.py` (~550 строк)

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

**VirtualTransaction TypedDict**:
```python
class VirtualTransaction(TypedDict):
    template_id: int
    user_id: int
    instance_date: str       # ISO format
    amount: str              # Decimal as string (JSON)
    transaction_type: str    # "income" | "expense"
    description: str | None
    is_virtual: bool         # Всегда True
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

## DashboardService (Фаза 4 — ЗАВЕРШЕНА)

**Файл**: `app/services/dashboard_service.py` (~290 строк)

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
- `get_recent_transactions(user_id, limit)` → `list[RecentTransaction]`
  - Последние N транзакций, отсортированных по дате DESC

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

class RecentTransaction(TypedDict):
    id: int
    date: str
    description: str | None
    amount: Decimal
    type: str
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

    # Cashflow за последние 12 месяцев
    cashflow = service.get_cashflow_data(
        user_id=1, period="month", reference_date=date.today()
    )
```

**Composition Pattern**: DashboardService содержит CalendarService и GoalService

**Unit тесты**: 12 тестов в `tests/test_dashboard_service.py`

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

---

Детали: `architecture.md` (Service Layer Pattern), `code-style.md` (Session Management Pattern), `schema.md` (TypedDicts)
