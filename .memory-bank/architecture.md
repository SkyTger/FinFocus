# Архитектура FinFocus

## Тип архитектуры
**Модульное Dash приложение** с трехслойной архитектурой:
- Frontend (Dash Components) → Business Logic (Services) → Data Access (SQLAlchemy ORM) → Database (SQLite/PostgreSQL)

**Характеристики**:
- Single-page application с URL-based routing
- Server-side rendering через Dash callbacks
- Реактивные компоненты с автообновлением

## Слои приложения

### 1. Presentation Layer (UI)
**Компоненты**: `app/components/`
- **dashboard.py** - главная страница с карточками и графиками
- **sidebar.py** - навигация
- **transactions.py** - управление операциями (CRUD формы)

**Паттерн**: Stateless functional components, генерирующие Dash layouts

### 2. Application Layer (Business Logic)
**Сервисы**: `app/services/`
- **TransactionService** - CRUD операций, валидация
- **GoalService** - управление целями, расчет взносов, contributions, приоритеты, бюджет
- **CalendarService** - расчет остатков по дням, агрегация за месяц/год
- **RecurringService** - генерация виртуальных экземпляров, управление exceptions
- **DashboardService** - агрегация метрик, cashflow данные (composition)
- **AllocationService** - жадный алгоритм распределения бюджета между целями
- **RedistributionService** - перераспределение бюджета при достижении цели (Temporary Status Pattern)
- **CategoryService** - справочник категорий, seed, get_frequent_for_type
- **ReconciliationService** - сверка баланса, создание ADJUSTMENT транзакций
- **AnalyticsService** - агрегация расходов по категориям, monthly trends, donut/bar charts

- **BudgetReservationService** - управление резервированием бюджета накоплений, два режима (fixed_date/from_balance)
- **CushionService** - финансовая подушка безопасности, калькулятор сценариев
- **OnboardingService** - onboarding wizard для новых пользователей

**Паттерн**: Service Layer с изолированной бизнес-логикой, session management через flush()

### 3. Data Access Layer (ORM)
**Модели**: `app/models/database.py`
- **User** - пользователи, starting_balance, monthly_savings_budget, savings_mode
- **Transaction** - операции (income/expense/transfer), recurring поля
- **Goal** - накопительные цели, priority
- **GoalContribution** - взносы в цели

**Паттерн**: Active Record через SQLAlchemy, calculated properties (@property)

### 6. Schema Layer (NEW)
**Модуль**: `app/schema/`
- **goals.py** - TypedDicts для накопительных целей
  - AllocationResult, AllocationSummary
  - GoalDisplayData, GoalsSummary

**Паттерн**: Централизованная типизация для переиспользования между services и UI

### 7. Utils Layer (NEW)
**Модуль**: `app/utils/`
- **formatters.py** - функции форматирования для UI
  - format_amount(), format_date(), format_days_remaining()
  - parse_date_safe()

**Паттерн**: DRY для общих утилит отображения

### 4. Database Layer
**SQLite** (development) / **PostgreSQL** (production)
- Автоинициализация через `init_database()` в `run.py`
- Миграции через Alembic (пока не используется)

### 5. Core Infrastructure Layer (NEW)
**Модуль**: `app/core/`
- **database.py** - централизованный session management
  - `get_engine()` - singleton engine factory
  - `get_db_session()` - context manager для сессий
  - `init_database()` - инициализация БД
- **logging.py** - настройка loguru
  - `setup_logging()` - конфигурация логгера
  - Ротация файлов по дням
  - Цветной вывод в консоль + файл
- **exceptions.py** - единые исключения
  - `ValidationError` - для бизнес-правил

**Паттерн**: Infrastructure Layer с singleton factories и context managers

## Ключевые паттерны

### Dash Callbacks Pattern
```python
@callback(
    Output("component-id", "property"),
    Input("trigger-id", "property"),
    prevent_initial_call=True  # Для модалов
)
def handler(input_value):
    # Guard clauses
    if not input_value:
        raise PreventUpdate

    # Business logic
    # ...

    return result
```

**Критично**: Pattern-Matching Callbacks с `ALL`:
- Проверять `ctx.triggered[0].get('value') is None` для фильтрации автовызовов
- Использовать `ctx.triggered_id["index"]` напрямую, избегать поиска в списках

### Service Layer Pattern
```python
class TransactionService:
    def create_transaction(self, session, user_id, data):
        """Создание операции с валидацией."""
        # 1. Валидация
        if not data.get('amount') or data['amount'] <= 0:
            raise ValidationError("Amount must be positive")

        # 2. Создание объекта
        transaction = Transaction(**data)
        session.add(transaction)

        # 3. Flush (не commit!)
        session.flush()  # Caller управляет commit

        return transaction
```

**Принцип**: Сервисы используют `flush()`, caller делает `commit()` для атомарности операций

### Calculated Properties Pattern
```python
class Goal(Base):
    @property
    def monthly_contribution(self) -> Decimal:
        """Guard clauses для edge cases."""
        # Guard: deadline в прошлом
        if self.target_date <= date.today():
            return Decimal('0')

        # Guard: цель достигнута
        if self.current_amount >= self.target_amount:
            return Decimal('0')

        # Расчет
        days_remaining = (self.target_date - date.today()).days
        months_remaining = max(days_remaining / 30, 1)
        return (self.target_amount - self.current_amount) / Decimal(months_remaining)
```

**Принцип**: Guard clauses в начале для предотвращения ошибок (division by zero, negative values)

## Коммуникация между компонентами

### UI → Service → ORM → Database
```
Transactions Component (UI)
    ↓ callback(create_transaction)
TransactionService.create_transaction(session, data)
    ↓ session.add(Transaction)
SQLAlchemy ORM
    ↓ INSERT INTO transactions
SQLite Database
```

### Routing Flow
```
User navigates to /transactions
    ↓
app.layout → dcc.Location(id="url")
    ↓
display_page(pathname="/transactions") callback
    ↓
create_transactions_layout()
    ↓
Render Transactions component with callbacks
```

### Form Submission Flow (Pattern-Matching)
```
User clicks "Create" button
    ↓
toggle_create_modal() - opens modal
    ↓
User fills form → clicks "Submit"
    ↓
create_transaction() callback
    ↓
TransactionService.create_transaction()
    ↓
refresh_transactions_table() - updates table
```

## Важные принципы

### 1. Separation of Concerns
- UI компоненты НЕ содержат бизнес-логику
- Сервисы НЕ знают о Dash callbacks
- ORM модели содержат ТОЛЬКО данные и calculated properties

### 2. Session Management
- Caller создает session и управляет commit
- Сервисы используют flush() для валидации без commit
- Exception в сервисе → caller делает rollback

### 3. Validation Strategy
- Frontend: Dash Input validation (type, required)
- Backend: Service layer validation с ValidationError
- Database: SQLAlchemy constraints (nullable, unique)

### 4. Error Handling
- ValidationError → понятное сообщение на русском
- Database errors → rollback + user-friendly message
- Callbacks → PreventUpdate для пропуска обработки

## Критичные архитектурные решения

**ADR-001**: Dash вместо Flask + React
- Быстрая разработка, встроенная реактивность
- Trade-off: ограниченная кастомизация

**ADR-002**: SQLite для MVP
- Простота, zero-configuration
- Migration path к PostgreSQL через DATABASE_URL

**ADR-003**: Pattern-Matching Callbacks
- Проблема: автовызовы при DOM updates
- Решение: проверка `ctx.triggered[0].get('value') is None`

**D008**: Guard clauses в calculated properties
- Предотвращение division by zero
- Явная обработка edge cases

**~~D009~~**: ~~Одна активная цель в MVP~~ (УДАЛЕНО в протоколе 0006)

**D010**: Session management через flush()
- Атомарность операций
- Гибкость для caller (commit/rollback)

**Протокол 0006**: Множественные цели с приоритетами
- AllocationService с жадным алгоритмом
- TypedDicts в app/schema/ для DRY

**Протокол 0007**: Режимы накоплений (free/medium/strict)
- Множители к monthly_contribution
- User.savings_mode поле

**Протокол 0008**: Перераспределение средств при достижении цели
- RedistributionService с Temporary Status Pattern
- RedistributionPreview TypedDict
- Redistribution Modal UI с confirm/decline callbacks
- NFR: preview < 100ms, аудит-логирование

**Протокол 0016**: Интеграция бюджета накоплений с календарём
- BudgetReservationService с двумя режимами резервирования
- TransactionType: SAVINGS_RESERVE, SAVINGS_CONTRIBUTION
- GoalContribution.transaction_id FK для связи с календарём
- Динамический бюджет: remaining = total - SUM(contributions_this_month)

## Диаграмма компонентов

```
┌─────────────────────────────────────────────────────────┐
│              app/main.py (Entry)                        │
│  - Dash app initialization                              │
│  - URL routing (display_page callback)                  │
└───────────────────┬─────────────────────────────────────┘
                    │
      ┌─────────────┼─────────────┬─────────────┬─────────────┐
      ▼             ▼             ▼             ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────┐ ┌─────────┐
│dashboard │ │calendar  │ │transactions  │ │ goals   │ │sidebar  │
│- Metrics │ │- Grid    │ │  - CRUD      │ │- Cards  │ │- Nav    │
│- Charts  │ │- Stats   │ │  - Modals    │ │- Budget │ │         │
└─────┬────┘ └─────┬────┘ └──────┬───────┘ └────┬────┘ └─────────┘
      │            │              │               │
      └────────────┴──────────────┴───────────────┘
                    │
                    ▼
         ┌──────────────────────────────┐
         │      app/services/           │
         │  - TransactionService        │
         │  - GoalService               │
         │  - CalendarService           │
         │  - RecurringService          │
         │  - DashboardService          │
         │  - AllocationService         │
         │  - RedistributionService     │
         │  - CategoryService           │
         │  - ReconciliationService     │
         │  - AnalyticsService          │
         │  - CushionService            │
         │  - OnboardingService         │
         │  - BudgetReservationService  │
         └──────────────┬───────────────┘
                        │
           ┌────────────┼────────────┬─────────────┐
           ▼            ▼            ▼             ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐  ┌──────────┐
    │app/core/ │ │app/models│ │app/schema│  │app/utils │
    │-database │ │-ORM      │ │-TypedDicts│  │-formatters│
    │-exceptions││          │ │          │  │          │
    │-logging  │ │          │ │          │  │          │
    └────┬─────┘ └─────┬────┘ └──────────┘  └──────────┘
         │             │
         └──────┬──────┘
                ▼
    ┌───────────────────────┐
    │  SQLite Database      │
    │  data/finfocus.db     │
    │  + миграции scripts/  │
    └───────────────────────┘
```

## Планируемые изменения (Roadmap)

**~~Фаза 3~~ Кассовый календарь**: ✅ ЗАВЕРШЕНА (PR #2)

**~~Фаза 4~~ Dashboard integration**: ✅ ЗАВЕРШЕНА (PR #3)

**~~Фаза 5~~ Goals UI**: ✅ ЗАВЕРШЕНА (PR #4)

**~~Батч 2~~ Enhanced Planning**: ✅ ЗАВЕРШЕН (75% → 100%)
- ✅ Повторяющиеся операции (PR #5)
- ✅ Множественные цели с приоритетами (PR #6)
- ✅ Три режима накоплений (PR #7)
- ✅ Перераспределение средств между целями (PR #8)

**~~Батч 3~~ Analytics & UX**: ✅ ЗАВЕРШЕН (100%)
- ✅ Категоризация операций (PR #9)
  - Category модель, TransactionType.ADJUSTMENT
  - CategoryService, ReconciliationService
  - Сверка баланса через модал
- ✅ UX улучшения + Аналитика (PR #10)
  - AnalyticsService (donut/bar charts)
  - Страница /analytics с графиками
- ✅ Восстановление UI компонентов (протокол 0011, PR #11)
  - Chips UI для быстрой категоризации (восстановлен после merge)
  - Bulk actions (multi-select, max 100 транзакций)
  - CSV экспорт с UTF-8 BOM для Excel
  - 13 новых тестов для _pluralize_operations
  - Pattern-Matching callbacks с 3-уровневыми guard clauses (ADR-003)

**Батч 4** (Advanced Features):
- Финансовая подушка безопасности
- Импорт операций из банков
- Уведомления и напоминания

---

Референсы:
- Детали Pattern-Matching Callbacks: `docs/adr/ADR-003-pattern-matching-callbacks-issue.md`
- История архитектурных решений: `.reports/epics/epic-01-coreMVP/decisions.md`, `.reports/epics/epic-02-enhancedPlanning/decisions.md`
