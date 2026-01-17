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
- **GoalService** - управление целями, расчет взносов, contributions

**Паттерн**: Service Layer с изолированной бизнес-логикой, session management через flush()

### 3. Data Access Layer (ORM)
**Модели**: `app/models/database.py`
- **User** - пользователи, starting_balance
- **Transaction** - операции (income/expense/transfer)
- **Goal** - накопительные цели
- **GoalContribution** - взносы в цели

**Паттерн**: Active Record через SQLAlchemy, calculated properties (@property)

### 4. Database Layer
**SQLite** (development) / **PostgreSQL** (production)
- Автоинициализация через `init_database()` в `run.py`
- Миграции через Alembic (пока не используется)

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

**D010**: Session management через flush()
- Атомарность операций
- Гибкость для caller (commit/rollback)

## Диаграмма компонентов

```
┌─────────────────────────────────────────┐
│          app/main.py (Entry)            │
│  - Dash app initialization              │
│  - URL routing (display_page callback)  │
└────────────┬────────────────────────────┘
             │
             ├─────────────────┬──────────────────┬──────────────────┐
             ▼                 ▼                  ▼                  ▼
    ┌─────────────────┐ ┌─────────────┐  ┌──────────────┐  ┌─────────────┐
    │   dashboard.py  │ │ sidebar.py  │  │transactions.py│  │ (future)    │
    │   - Metrics     │ │ - Nav links │  │  - CRUD forms │  │             │
    │   - Charts      │ │ - User info │  │  - Table      │  │             │
    └────────┬────────┘ └─────────────┘  └───────┬───────┘  └─────────────┘
             │                                    │
             └──────────────┬─────────────────────┘
                            ▼
                 ┌────────────────────────┐
                 │   app/services/        │
                 │  - TransactionService  │
                 │  - GoalService         │
                 └──────────┬─────────────┘
                            │
                            ▼
                 ┌────────────────────────┐
                 │   app/models/          │
                 │   database.py          │
                 │  - User, Transaction   │
                 │  - Goal, Contribution  │
                 └──────────┬─────────────┘
                            │
                            ▼
                 ┌────────────────────────┐
                 │   SQLite Database      │
                 │   data/finfocus.db     │
                 └────────────────────────┘
```

## Планируемые изменения (Roadmap)

**Фаза 3** (Кассовый календарь):
- Новый компонент `calendar.py`
- Сервис для расчета остатков по дням
- Интеграция с Transaction для прогноза

**Батч 2** (Enhanced Planning):
- Повторяющиеся операции (recurring transactions)
- Множественные цели с приоритетами
- Сервис перераспределения средств

**Батч 3** (Analytics):
- Категоризация операций
- Аналитические графики
- Export/Import сервисы

---

Референсы:
- Детали Pattern-Matching Callbacks: `docs/adr/ADR-003-pattern-matching-callbacks-issue.md`
- История архитектурных решений: `.reports/epics/epic-01-coreMVP/decisions.md`
