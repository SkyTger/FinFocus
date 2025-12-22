# Technical Details - Epic 01: Core MVP

## 🏗️ Архитектура

### Общая структура приложения

```
┌─────────────────────────────────────────┐
│         Dash Application                 │
│  (app/main.py - routing & layout)       │
└──────────┬──────────────────────────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼───┐    ┌───▼────┐
│  UI   │    │ Services│
│Components│  │ (Business)│
└───┬───┘    └───┬────┘
    │            │
    │       ┌────▼─────┐
    │       │  Models  │
    │       │(SQLAlchemy)│
    │       └────┬─────┘
    │            │
    └────────┬───▼──────┐
             │ Database │
             │ (SQLite) │
             └──────────┘
```

### Технологический стек

**Backend**:
- Python 3.12
- SQLAlchemy 2.0.23 (ORM)
- SQLite (разработка) / PostgreSQL (production)

**Frontend**:
- Dash 2.17.1 (Python web framework)
- Dash Bootstrap Components 1.5.0
- Plotly 5.17.0 (визуализация данных)
- Bootstrap 5.x (CSS framework)
- Bootstrap Icons (иконки)

**Testing**:
- pytest (unit тесты)
- pytest-cov (coverage)

**Code Quality**:
- flake8 (linting)
- black (formatting)

---

## 📦 Модули и функции

### Модуль: Database Models (`app/models/database.py`)

#### User Model

```python
class User(Base):
    __tablename__ = 'users'

    id: int                      # Primary key
    email: str                   # Unique, not null
    name: str                    # Not null
    created_at: datetime         # Auto-generated
    updated_at: datetime         # Auto-updated

    # Relationships
    transactions: List[Transaction]  # Cascade delete
    goals: List[Goal]                # Cascade delete
```

**Описание**: Модель пользователя приложения

**Связи**:
- `transactions` → one-to-many к Transaction
- `goals` → one-to-many к Goal

---

#### Transaction Model

```python
class Transaction(Base):
    __tablename__ = 'transactions'

    id: int                          # Primary key
    user_id: int                     # Foreign key → users.id
    amount: Decimal(10, 2)           # Денежная сумма (точность до копеек)
    transaction_type: TransactionType  # Enum: INCOME/EXPENSE/TRANSFER
    transaction_date: date           # Дата операции
    description: str                 # Опциональное описание
    category: str                    # Категория (для Батча 3)
    is_recurring: bool               # Повторяющаяся операция (для Батча 2)
    recurring_period: str            # Период повтора (для Батча 2)
    created_at: datetime             # Auto-generated
    updated_at: datetime             # Auto-updated

    # Relationships
    user: User
```

**Описание**: Финансовая операция (доход/расход/перевод)

**Enum TransactionType**:
- `INCOME` - доход
- `EXPENSE` - расход
- `TRANSFER` - перевод (между счетами, для будущего)

**Пример использования**:
```python
from app.models.database import Transaction, TransactionType
from decimal import Decimal
from datetime import date

transaction = Transaction(
    user_id=1,
    amount=Decimal('5000.00'),
    transaction_type=TransactionType.INCOME,
    transaction_date=date(2025, 1, 15),
    description="Зарплата за январь"
)
```

---

#### Goal Model

```python
class Goal(Base):
    __tablename__ = 'goals'

    id: int                      # Primary key
    user_id: int                 # Foreign key → users.id
    name: str                    # Название цели
    target_amount: Decimal(10, 2)  # Целевая сумма
    current_amount: Decimal(10, 2) # Текущая накопленная сумма
    target_date: date            # Целевая дата достижения
    status: GoalStatus           # Enum: ACTIVE/COMPLETED/PAUSED
    monthly_contribution: Decimal(10, 2)  # Расчетный ежемесячный взнос
    priority: int                # Приоритет (для Батча 2)
    created_at: datetime         # Auto-generated
    updated_at: datetime         # Auto-updated

    # Relationships
    user: User
    contributions: List[GoalContribution]  # Cascade delete

    # Calculated properties
    @property
    def progress_percentage(self) -> float

    @property
    def is_completed(self) -> bool
```

**Описание**: Накопительная цель пользователя

**Enum GoalStatus**:
- `ACTIVE` - активная цель
- `COMPLETED` - цель достигнута
- `PAUSED` - цель приостановлена

**Calculated Properties**:

```python
@property
def progress_percentage(self) -> float:
    """Процент выполнения цели"""
    if self.target_amount == 0:
        return 0
    return float(self.current_amount / self.target_amount * 100)

@property
def is_completed(self) -> bool:
    """Достигнута ли цель"""
    return self.current_amount >= self.target_amount
```

**Пример использования**:
```python
from app.models.database import Goal, GoalStatus
from decimal import Decimal
from datetime import date

goal = Goal(
    user_id=1,
    name="Отпуск в Турции",
    target_amount=Decimal('150000.00'),
    current_amount=Decimal('50000.00'),
    target_date=date(2025, 7, 1),
    status=GoalStatus.ACTIVE
)

# Calculated properties
print(goal.progress_percentage)  # 33.33
print(goal.is_completed)         # False
```

---

#### GoalContribution Model

```python
class GoalContribution(Base):
    __tablename__ = 'goal_contributions'

    id: int                      # Primary key
    goal_id: int                 # Foreign key → goals.id
    amount: Decimal(10, 2)       # Сумма взноса
    contribution_date: date      # Дата взноса
    description: str             # Опциональное описание
    created_at: datetime         # Auto-generated

    # Relationships
    goal: Goal
```

**Описание**: Взнос в накопительную цель

**Пример использования**:
```python
from app.models.database import GoalContribution
from decimal import Decimal
from datetime import date

contribution = GoalContribution(
    goal_id=1,
    amount=Decimal('10000.00'),
    contribution_date=date(2025, 1, 31),
    description="Взнос за январь"
)
```

---

### Модуль: Database Initialization (`app/models/database.py`)

#### `create_database_engine(database_url: str) -> Engine`

**Описание**: Создает движок SQLAlchemy для подключения к базе данных

**Входные данные**:
- `database_url` (str, default: `"sqlite:///data/finfocus.db"`) - URL базы данных

**Выходные данные**: SQLAlchemy Engine

**Пример использования**:
```python
from app.models.database import create_database_engine

engine = create_database_engine()  # SQLite по умолчанию
# или
engine = create_database_engine("postgresql://user:pass@localhost/finfocus")
```

---

#### `create_tables(engine: Engine) -> None`

**Описание**: Создает все таблицы в базе данных согласно моделям

**Входные данные**:
- `engine` (Engine) - движок базы данных

**Выходные данные**: None (side effect: создание таблиц)

**Пример использования**:
```python
from app.models.database import create_database_engine, create_tables

engine = create_database_engine()
create_tables(engine)
```

---

#### `get_session(engine: Engine) -> Session`

**Описание**: Создает сессию для работы с базой данных

**Входные данные**:
- `engine` (Engine) - движок базы данных

**Выходные данные**: SQLAlchemy Session

**Пример использования**:
```python
from app.models.database import create_database_engine, get_session

engine = create_database_engine()
session = get_session(engine)

# Использование
user = session.query(User).first()
session.add(new_transaction)
session.commit()
session.close()
```

---

#### `init_database(database_url: str) -> Engine`

**Описание**: Инициализирует базу данных (создает движок и таблицы)

**Входные данные**:
- `database_url` (str, default: `"sqlite:///data/finfocus.db"`) - URL базы данных

**Выходные данные**: SQLAlchemy Engine

**Пример использования**:
```python
from app.models.database import init_database

# Инициализация при старте приложения
engine = init_database()  # Создаст data/finfocus.db и все таблицы
```

---

### Сервисный слой (app/services/)

#### TransactionService

**Ответственность**: CRUD операции для финансовых транзакций

**Публичные методы**:
1. `create_transaction(user_id, amount, transaction_type, transaction_date, description=None, category=None) -> Transaction`
   - Валидация: amount > 0, date не более 1 года в будущем
   - Возвращает: Transaction (не закоммиченный)

2. `get_by_id(transaction_id: int) -> Transaction | None`
   - Возвращает транзакцию по ID или None

3. `get_all_by_user(user_id: int, transaction_type=None, start_date=None, end_date=None) -> List[Transaction]`
   - Фильтрация по типу, диапазону дат
   - Сортировка: transaction_date DESC (новые первыми)

4. `update_transaction(transaction_id, amount=None, transaction_type=None, ...) -> Transaction`
   - Обновление с валидацией
   - Поддерживает partial updates

5. `delete_transaction(transaction_id: int) -> bool`
   - Возвращает True если удалена, False если не найдена

**Валидации**:
- amount > 0
- transaction_date не более 1 года в будущем (защита от ошибок ввода)
- transaction_type из TransactionType enum

**Статус**: ✅ Реализовано (Commit 1211796)

---

#### GoalService (расширен в Фазе 1)

**Добавлены методы**:
1. `get_by_id(goal_id: int) -> Goal | None`
2. `get_all_by_user(user_id: int, status: GoalStatus = None) -> List[Goal]`
3. `update_goal(goal_id, name=None, target_amount=None, target_date=None) -> Goal`
4. `delete_goal(goal_id: int) -> bool`

**Улучшенная валидация**:
- target_date >= today + 7 days (минимум неделя для реалистичных накоплений)
- Понятные ValidationError сообщения с минимальной датой в формате DD.MM.YYYY

**Статус**: ✅ Расширен (Commit 1211796)

---

### Модуль: Dash Application (`app/main.py`)

#### URL Routing

**Callback**: `display_page(pathname: str) -> Component`

**Описание**: Роутинг страниц на основе URL pathname

**URL структура**:
- `/` или `/dashboard` → Dashboard overview
- `/calendar` → Кассовый календарь
- `/goals` → Управление целями
- `/transactions` → Список операций

**Входные данные**:
- `pathname` (str) - текущий URL path из `dcc.Location`

**Выходные данные**: Dash Component (layout страницы)

**Пример**:
```python
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/' or pathname == '/dashboard':
        return dashboard_layout()
    elif pathname == '/calendar':
        return calendar_layout()
    elif pathname == '/goals':
        return goals_layout()
    elif pathname == '/transactions':
        return transactions_layout()
    else:
        return html.Div("404: Страница не найдена")
```

---

### Модуль: Dashboard Component (`app/components/dashboard.py`)

#### `dashboard_layout() -> Component`

**Описание**: Генерирует layout Dashboard страницы

**Выходные данные**: dbc.Container с карточками и графиками

**Структура**:
- Карточки показателей (доходы, расходы, остаток, цели)
- График cashflow (Plotly bar chart)
- Donut chart структуры расходов

**Пример**:
```python
from app.components.dashboard import dashboard_layout

layout = dashboard_layout()
```

---

### Модуль: Sidebar Component (`app/components/sidebar.py`)

#### `sidebar_layout() -> Component`

**Описание**: Генерирует sidebar навигацию

**Выходные данные**: dbc.Nav с навигационными ссылками

**Структура**:
- Логотип и название приложения
- Навигационные ссылки (Dashboard, Calendar, Goals, Transactions)
- User profile блок
- AI assistant кнопка

**Пример**:
```python
from app.components.sidebar import sidebar_layout

sidebar = sidebar_layout()
```

---

## 🗄️ Конфигурация

### Environment Variables (`.env`)

```bash
# Database
DATABASE_URL=sqlite:///data/finfocus.db  # URL базы данных
# DATABASE_URL=postgresql://user:pass@localhost/finfocus  # для production

# Application
PORT=8050                  # Порт для Dash приложения
DEBUG=True                 # Debug режим (True для разработки)
SECRET_KEY=your-secret-key # Secret key для Flask sessions

# Logging
LOG_LEVEL=INFO             # Уровень логирования (DEBUG/INFO/WARNING/ERROR)
```

**ВАЖНО**: Файл `.env` добавлен в `.gitignore` и не публикуется в репозиторий!

---

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Transactions table
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,  -- INCOME/EXPENSE/TRANSFER
    transaction_date DATE NOT NULL,
    description VARCHAR(500),
    category VARCHAR(100),
    is_recurring BOOLEAN DEFAULT FALSE,
    recurring_period VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Goals table
CREATE TABLE goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    target_amount DECIMAL(10, 2) NOT NULL,
    current_amount DECIMAL(10, 2) DEFAULT 0,
    target_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE/COMPLETED/PAUSED
    monthly_contribution DECIMAL(10, 2),
    priority INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Goal Contributions table
CREATE TABLE goal_contributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id INTEGER NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    contribution_date DATE NOT NULL,
    description VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_transactions_user_date ON transactions(user_id, transaction_date);
CREATE INDEX idx_goals_user_status ON goals(user_id, status);
CREATE INDEX idx_contributions_goal_date ON goal_contributions(goal_id, contribution_date);
```

---

## 🔄 Инварианты

### Бизнес-инварианты

- ✅ **Transaction amount**: всегда положительное число (валидация в UI и сервисе)
- ✅ **Goal target_amount**: всегда > 0 (валидация в UI и сервисе)
- ✅ **Goal current_amount**: 0 ≤ current_amount ≤ target_amount (рассчитывается из contributions)
- ✅ **Goal target_date**: всегда в будущем при создании (валидация)
- ✅ **Transaction date**: не может быть более чем на 1 год в будущем (валидация)
- ✅ **User email**: уникальный (constraint в БД)
- ✅ **Cascade deletes**: при удалении User удаляются все его transactions и goals

### Технические инварианты

- ✅ **Decimal precision**: все денежные поля имеют точность Decimal(10, 2)
- ✅ **DateTime auto-update**: updated_at обновляется автоматически при изменении записи
- ✅ **Relationships integrity**: Foreign keys обеспечивают целостность данных
- ✅ **Session management**: каждая операция БД использует session для транзакционности

---

## ⚡ Производительность

### Целевые метрики

- **Загрузка Dashboard**: < 3 сек для 100 операций
- **Загрузка Calendar**: < 2 сек для 365 дней
- **CRUD операции**: < 500ms response time
- **Plotly графики**: < 1 сек для рендеринга 100 точек данных

### Оптимизации

**Database**:
- Indexes на часто запрашиваемые поля (user_id, transaction_date, status)
- Eager loading для relationships (использовать `joinedload` для избежания N+1)
- Connection pooling (SQLAlchemy default)

**Frontend**:
- Lazy loading для Plotly графиков
- Pagination для списков транзакций (20-50 записей на страницу)
- Debouncing для search/filter inputs

**Caching** (для будущего):
- Redis для кеширования Dashboard метрик
- TTL: 5 минут для агрегированных данных

---

## 🧪 Тестирование

### Unit тесты

**Coverage target**: ≥ 80% для всех модулей

**Тест-план**:

```
tests/
├── test_models.py              # SQLAlchemy модели
│   ├── test_user_model
│   ├── test_transaction_model
│   ├── test_goal_model
│   └── test_goal_contribution_model
│
├── test_services/
│   ├── test_transaction_service.py  # CRUD транзакций
│   ├── test_goal_service.py         # CRUD целей
│   ├── test_calendar_service.py     # Расчет календаря
│   └── test_dashboard_service.py    # Dashboard метрики
│
└── test_components/
    ├── test_dashboard.py        # Dashboard layout
    └── test_sidebar.py          # Sidebar navigation
```

**Примеры**:
```python
# tests/test_models.py
def test_goal_progress_percentage():
    goal = Goal(target_amount=Decimal('100'), current_amount=Decimal('33.33'))
    assert goal.progress_percentage == 33.33

def test_goal_is_completed():
    goal = Goal(target_amount=Decimal('100'), current_amount=Decimal('150'))
    assert goal.is_completed is True
```

---

## 📚 API Спецификация (для будущих сервисов)

### Transaction Service (планируется)

```python
class TransactionService:
    """Сервис для работы с транзакциями"""

    def create_transaction(user_id, amount, type, date, description) -> Transaction
    def get_user_transactions(user_id, start_date, end_date) -> List[Transaction]
    def update_transaction(transaction_id, **kwargs) -> Transaction
    def delete_transaction(transaction_id) -> bool
```

### Goal Service (планируется)

```python
class GoalService:
    """Сервис для работы с целями"""

    def create_goal(user_id, name, target_amount, target_date) -> Goal
    def add_contribution(goal_id, amount, date, description) -> GoalContribution
    def calculate_monthly_contribution(goal_id) -> Decimal
    def get_user_goals(user_id, status) -> List[Goal]
```

### Calendar Service (планируется)

```python
class CalendarService:
    """Сервис для кассового календаря"""

    def calculate_daily_balances(user_id, start_date, end_date) -> List[Dict]
    # Returns: [{"date": date, "income": Decimal, "expense": Decimal, "balance": Decimal}]
```

---

*Технические детали обновляются при добавлении новых модулей и функций*
*Формат: модули → функции → примеры → спецификации*