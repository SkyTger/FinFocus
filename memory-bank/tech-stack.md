# Технологический стек FinFocus

## Runtime Environment
**Python 3.12** - минимальная требуемая версия, type annotations обязательны

## Core Framework

### Dash 2.17.1
**Назначение**: Основной фреймворк для веб-приложения
- Reactive components с server-side rendering
- Built-in callbacks для interactivity
- Hot-reload в development mode

**Ключевые модули**:
- `dash.Dash` - главный app instance
- `dash.dcc` - core components (Location, Input, etc.)
- `dash.html` - HTML элементы
- `dash.callback` - декоратор для callbacks

### Dash Bootstrap Components 1.5.0
**Назначение**: UI библиотека для layouts и styling
- Bootstrap Grid system
- Готовые компоненты: Modal, Table, Card, Button
- Bootstrap Icons через `dbc.icons.BOOTSTRAP`

**Примеры использования**:
```python
import dash_bootstrap_components as dbc

# Layout
dbc.Row([
    dbc.Col(content, width=3),
    dbc.Col(main, width=9)
])

# Components
dbc.Modal([...], id="modal", is_open=False)
dbc.Table.from_dataframe(df, striped=True, hover=True)
```

### Plotly 5.17.0
**Назначение**: Интерактивные графики и визуализации
- Cashflow bar charts
- Donut charts для структуры расходов
- Time-series для динамики

**Примеры**:
```python
import plotly.graph_objs as go

fig = go.Figure(data=[
    go.Bar(x=dates, y=amounts, name="Доходы")
])
```

## Database Stack

### SQLAlchemy 2.0.23
**Назначение**: ORM для работы с базой данных
- Declarative models (User, Transaction, Goal, GoalContribution)
- Relationship management
- Session handling

**Ключевые паттерны**:
```python
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    transactions = relationship("Transaction", back_populates="user")
```

**Session management**:
- `session.flush()` - валидация без commit (в сервисах)
- `session.commit()` - финальное сохранение (в caller)
- `session.rollback()` - откат при ошибках

### SQLite (development) / PostgreSQL (production)
**Development**: `sqlite:///data/finfocus.db`
- Zero-configuration
- File-based, легко удалить и пересоздать
- Автоинициализация через `init_database()`

**Production** (planned): PostgreSQL через `DATABASE_URL` env variable
- Migration path через Alembic

### Alembic 1.13.1
**Назначение**: Database migrations (пока не используется)
- Планируется для production deployments
- Версионирование схемы БД

## Development Tools

### pytest 7.4.3
**Назначение**: Unit testing framework
- Тесты в `tests/` директории
- Fixtures для session management
- Параметризация тестов

**Команды**:
```bash
pytest                # Все тесты
pytest -v             # Verbose
pytest --cov          # С coverage
pytest tests/test_models.py  # Specific file
```

### pytest-cov 4.1.0
**Назначение**: Code coverage для pytest
- Цель: 80% покрытие для Core MVP
- Отчеты в терминал и HTML

### black 23.11.0
**Назначение**: Автоматическое форматирование кода
- PEP8 compliant
- Line length: 88 (default)
- Strings: двойные кавычки

**Команды**:
```bash
black app/           # Format all
black --check app/   # Check without changes
```

### flake8 6.1.0
**Назначение**: Линтер для проверки кода
- PEP8 violations
- Unused imports, variables
- Code complexity

**Приоритеты**:
1. F-category (errors) - критичные
2. E-category (PEP8) - высокие
3. W-category (warnings) - средние

**Команды**:
```bash
flake8 app/
```

## Utilities

### python-dotenv 1.0.0
**Назначение**: Управление environment variables
- `.env` файл для локальных настроек
- `load_dotenv()` в `app/main.py`

**Переменные**:
- `DATABASE_URL` - connection string (default: sqlite:///data/finfocus.db)
- `DEBUG` - debug mode (default: True)
- `PORT` - HTTP port (default: 8050)

### python-dateutil 2.8.2
**Назначение**: Работа с датами
- Parsing ISO dates
- Date arithmetic для расчетов

## Dependency Tree (критичные зависимости)

```
FinFocus
├── Dash 2.17.1
│   ├── Flask (built-in)
│   ├── Plotly 5.17.0
│   └── werkzeug
├── dash-bootstrap-components 1.5.0
│   └── Bootstrap CSS/JS (CDN)
├── SQLAlchemy 2.0.23
│   └── greenlet (async support)
├── pytest 7.4.3
│   └── pytest-cov 4.1.0
└── python-dotenv 1.0.0
```

## Version Constraints

**Критичные**:
- `Python >= 3.12` - type annotations, match-case
- `Dash >= 2.17` - prevent_initial_call в callbacks
- `SQLAlchemy >= 2.0` - новый API (declarative_base)

**Рекомендуемые**:
- Все версии зафиксированы в `requirements.txt` для reproducibility
- Обновления только после тестирования в dev окружении

## Planned Additions (Roadmap)

**Батч 3** (Analytics):
- `pandas` - для аналитики и aggregations
- `openpyxl` - для Excel export

**Батч 4** (Advanced):
- `celery` - для background tasks (импорт банковских выписок)
- `redis` - для celery broker

**Production**:
- `gunicorn` - WSGI server для production
- `psycopg2` - PostgreSQL adapter

## Environment Setup

```bash
# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Инициализация БД (автоматически при запуске)
python run.py
```

## Performance Considerations

**Dash Performance**:
- Используется `prevent_initial_call=True` для предотвращения лишних вычислений
- Lazy loading компонентов (пока не реализовано)
- Client-side callbacks для простых операций (planned)

**Database Performance**:
- SQLite достаточно для < 10K операций
- Индексы на часто запрашиваемые поля (planned)
- Connection pooling для PostgreSQL (production)

**Frontend Performance**:
- Bootstrap CSS через CDN
- Минификация assets (planned для production)
- Lazy loading Plotly charts (planned)

---

Референсы:
- `requirements.txt` - полный список зависимостей
- Dash Documentation: https://dash.plotly.com/
- SQLAlchemy 2.0 Migration Guide: https://docs.sqlalchemy.org/en/20/changelog/migration_20.html
