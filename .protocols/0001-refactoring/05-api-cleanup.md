# Шаг 5: Обновление API и cleanup

## Briefing
- **Цель:** Обновить устаревший SQLAlchemy API (.get → session.get), добавить индексы для производительности, удалить мёртвый код, привести импорты в порядок.
- **Ключевые файлы:**
  - `app/models/database.py` (модифицировать)
  - `app/services/transaction_service.py` (модифицировать)
  - `app/services/goal_service.py` (модифицировать)
  - `app/main.py` (модифицировать)
  - `app/components/sidebar.py` (модифицировать) — опционально
- **Additional info:**
  - В SQLAlchemy 2.0 метод `session.query(Model).get(id)` устарел, заменяем на `session.get(Model, id)`
  - Добавляем индексы на user_id и transaction_date для таблицы transactions
  - Удаляем дублирование кода запуска сервера из main.py
  - Обновляем импорт declarative_base на новый API

## Sub-tasks

### 1. Обновить app/models/database.py

**1.1. Обновить импорт declarative_base:**
```python
# Было:
from sqlalchemy.ext.declarative import declarative_base

# Стало:
from sqlalchemy.orm import declarative_base
```

**1.2. Добавить индексы в Transaction:**
```python
from sqlalchemy import Index

class Transaction(Base):
    """Модель финансовой операции (доходы/расходы)."""
    __tablename__ = 'transactions'
    __table_args__ = (
        Index('ix_transactions_user_date', 'user_id', 'transaction_date'),
    )
    # ... остальные поля без изменений ...
```

**1.3. Удалить старые функции (если ещё остались):**
- `create_database_engine()` — удалить (перенесено в core/database.py)
- `create_tables()` — удалить
- `get_session()` — удалить
- `init_database()` — удалить

### 2. Обновить app/services/transaction_service.py

Заменить все вызовы `.query(Model).get(id)` на `session.get(Model, id)`:

```python
# Было (строки 87, 145, 186):
transaction = self.session.query(Transaction).get(transaction_id)

# Стало:
transaction = self.session.get(Transaction, transaction_id)
```

### 3. Обновить app/services/goal_service.py

Заменить все вызовы `.query(Model).get(id)` на `session.get(Model, id)`:

```python
# Было (строки 109, 131, 177, 215):
goal = self.session.query(Goal).get(goal_id)

# Стало:
goal = self.session.get(Goal, goal_id)
```

### 4. Очистить app/main.py

**4.1. Удалить блок дублирования запуска (строки 120-129):**
```python
# УДАЛИТЬ весь этот блок:
# if __name__ == "__main__":
#     debug = os.getenv('DEBUG', 'True').lower() == 'true'
#     port = int(os.getenv('PORT', 8050))
#     app.run_server(...)
```

**4.2. Удалить side effect при импорте (строки 19-21):**
```python
# УДАЛИТЬ:
# DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/finfocus.db')
# engine = init_database(DATABASE_URL)
```

**4.3. Обновить импорты на абсолютные:**
```python
# Было:
from models.database import init_database
from components.dashboard import create_dashboard_layout
from components.sidebar import create_sidebar
from components.transactions import create_transactions_layout

# Стало:
from app.components.dashboard import create_dashboard_layout
from app.components.sidebar import create_sidebar
from app.components.transactions import create_transactions_layout
```

### 5. Обновить app/components/dashboard.py (импорты)

Если есть относительные импорты — заменить на абсолютные.

### 6. Обновить app/components/sidebar.py (опционально)

Если есть относительные импорты — заменить на абсолютные.

### 7. Создать app/core/constants.py (опционально)

```python
"""Константы приложения."""

# Временные ограничения (в днях)
DAYS_IN_MONTH = 30
MAX_FUTURE_DAYS = 365
MIN_GOAL_DAYS = 7

# MVP ограничения (TODO: убрать после добавления auth)
DEFAULT_USER_ID = 1
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 1-7.
2.  **Верификация:**
    - `python -m py_compile app/models/database.py app/services/*.py app/main.py`
    - `python run.py` — приложение запускается
    - Открыть http://localhost:8050/transactions
    - Проверить CRUD операций работает
    - Проверить что индекс создан (в SQLite можно через `.schema transactions`)
    - `grep -r "query.*get" app/services/` — должен вернуть пустой результат
3.  **Фиксация:**
    - Добавь запись в `log.md`
    - Обнови `context.md`: `Current Step` → 6
    - Проверь ветку main
4.  **Коммит**: `git add . && git commit -m "refactor(models): update SQLAlchemy API, add indexes, cleanup [protocol-0001/05]"`. Push.
5.  **Отчет пользователю** в установленном формате.
