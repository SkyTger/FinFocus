---
name: code-style
description: Стандарты кода FinFocus — русские docstrings, type annotations, batch process (план→батч), git conventions
type: reference
originSessionId: a7066508-1d51-418c-a40d-a34902bde2ab
---

# Стандарты кода FinFocus

## Общие принципы

**Evidence > assumptions | Code > documentation | Efficiency > verbosity**

### Язык документации
- **Docstrings**: Русский язык для функций и классов
- **Comments**: Русский для пояснений логики
- **Code**: English для переменных, функций, классов (Python convention)
- **Git commits**: Английский (`feat: add transaction service`)

## Python Style Guide

### PEP8 Compliance
**Black** (88 chars) + **flake8** для автоматической проверки

**Приоритеты flake8**:
1. F-category (errors) - КРИТИЧНО, исправлять сразу
2. E-category (PEP8) - высокий приоритет
3. W-category (warnings) - средний приоритет

### Type Annotations (ОБЯЗАТЕЛЬНО)
```python
# ✅ Правильно
def create_transaction(
    session: Session,
    user_id: int,
    data: dict
) -> Transaction:
    """Создает новую финансовую операцию."""
    pass

# ❌ Неправильно
def create_transaction(session, user_id, data):
    pass
```

**Исключения**:
- Dash callbacks (типы выводятся из Input/Output)
- Внутренние helper функции (опционально)

### Docstrings (ОБЯЗАТЕЛЬНО для public API)
```python
class TransactionService:
    """Сервис для управления финансовыми операциями.

    Предоставляет CRUD операции для Transaction модели
    с валидацией и бизнес-логикой.
    """

    def create_transaction(
        self,
        session: Session,
        user_id: int,
        data: dict
    ) -> Transaction:
        """Создает новую финансовую операцию.

        Args:
            session: SQLAlchemy session для работы с БД.
            user_id: ID пользователя-владельца операции.
            data: Словарь с данными операции (amount, type, date, etc.).

        Returns:
            Transaction: Созданный объект операции.

        Raises:
            ValidationError: Если данные невалидны (amount <= 0, etc.).
        """
        # Guard clauses
        if not data.get('amount') or data['amount'] <= 0:
            raise ValidationError("Сумма должна быть положительной")

        # Business logic
        transaction = Transaction(user_id=user_id, **data)
        session.add(transaction)
        session.flush()  # Caller управляет commit

        return transaction
```

### Именование (Naming Conventions)

**Файлы и директории**:
- `snake_case.py` для Python модулей
- `lowercase` для директорий (`app/components/`, `app/services/`)

**Классы**:
- `PascalCase` для классов (`TransactionService`, `Goal`)
- `SCREAMING_SNAKE_CASE` для Enum значений (`INCOME`, `EXPENSE`)

**Функции и переменные**:
- `snake_case` для функций и переменных
- Глаголы для функций (`create_transaction`, `calculate_balance`)
- Существительные для переменных (`user_id`, `target_amount`)

**Константы**:
- `UPPERCASE` для глобальных констант (`DATABASE_URL`, `DEFAULT_PORT`)

**Dash Components IDs**:
- `kebab-case` для component IDs (`transaction-table`, `create-modal`)
- Префиксы для группировки (`edit-btn-`, `delete-btn-`)

## Import Style

### Порядок импортов (PEP8)
```python
# 1. Стандартная библиотека
import os
from datetime import datetime, date

# 2. Сторонние библиотеки
from dash import dcc, html, callback, Input, Output
import dash_bootstrap_components as dbc
from sqlalchemy import Column, Integer, String

# 3. Локальные модули
from models.database import User, Transaction
from services.transaction_service import TransactionService
```

### Абсолютные импорты (ОБЯЗАТЕЛЬНО)
```python
# ✅ Правильно
from app.models.database import User
from app.services.transaction_service import TransactionService

# ❌ Неправильно
from ..models.database import User
from .transaction_service import TransactionService
```

**Исключение**: внутри одного модуля можно использовать относительные

## Code Patterns

### Guard Clauses Pattern
```python
# ✅ Правильно - guard clauses в начале
def monthly_contribution(self) -> Decimal:
    """Расчет ежемесячного взноса."""
    # Guard: нет deadline
    if not self.target_date:
        return Decimal('0')

    # Guard: deadline в прошлом
    if self.target_date <= date.today():
        return Decimal('0')

    # Guard: цель достигнута
    if self.current_amount >= self.target_amount:
        return Decimal('0')

    # Основная логика
    days_remaining = (self.target_date - date.today()).days
    months_remaining = max(days_remaining / 30, 1)
    return (self.target_amount - self.current_amount) / Decimal(months_remaining)

# ❌ Неправильно - вложенные if
def monthly_contribution(self) -> Decimal:
    if self.target_date:
        if self.target_date > date.today():
            if self.current_amount < self.target_amount:
                # логика
                pass
    return Decimal('0')
```

### Session Management Pattern (Сервисы)
```python
# Сервис использует flush(), caller делает commit
class TransactionService:
    def create_transaction(self, session: Session, data: dict) -> Transaction:
        transaction = Transaction(**data)
        session.add(transaction)
        session.flush()  # Валидация + ID generation, НЕ commit
        return transaction

# Caller управляет транзакцией
def create_transaction_callback(...):
    session = get_session()
    try:
        transaction = TransactionService().create_transaction(session, data)
        session.commit()  # Атомарность
        return success_message
    except Exception as e:
        session.rollback()
        return error_message
    finally:
        session.close()
```

### Dash Callbacks Pattern
```python
# Pattern 1: Simple callback
@callback(
    Output("output-id", "children"),
    Input("input-id", "value"),
    prevent_initial_call=True  # Для модалов и форм
)
def update_output(input_value):
    # Guard clause
    if not input_value:
        raise PreventUpdate

    # Logic
    return f"Result: {input_value}"

# Pattern 2: Pattern-Matching Callback (КРИТИЧНО)
@callback(
    Output("edit-modal", "is_open"),
    Input({"type": "edit-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def open_edit_modal(edit_clicks_list):
    # КРИТИЧНО: проверка автовызова при DOM updates
    if ctx.triggered[0].get('value') is None:
        raise PreventUpdate

    # Используем triggered_id напрямую
    triggered_id = ctx.triggered_id
    if not triggered_id or not triggered_id.get("index"):
        raise PreventUpdate

    transaction_id = triggered_id["index"]
    # ... логика
    return True
```

## Error Handling

### ValidationError Pattern
```python
class ValidationError(Exception):
    """Ошибка валидации данных."""
    pass

# В сервисах
def create_transaction(self, session, data):
    if not data.get('amount') or data['amount'] <= 0:
        raise ValidationError("Сумма должна быть положительной")

    if data.get('transaction_type') not in ['income', 'expense']:
        raise ValidationError("Неверный тип операции")

# В callbacks
try:
    transaction = service.create_transaction(session, data)
    session.commit()
    return dbc.Alert("Операция создана", color="success")
except ValidationError as e:
    session.rollback()
    return dbc.Alert(str(e), color="danger")
```

### PreventUpdate Pattern (Dash)
```python
from dash.exceptions import PreventUpdate

@callback(...)
def handler(input_value):
    # Пропустить обработку если нет изменений
    if not input_value or input_value == previous_value:
        raise PreventUpdate

    # Обработка
    return result
```

## Git Workflow

### Ветки (Branches)
```bash
# Feature development
git checkout -b feature/cash-calendar

# Bug fixes
git checkout -b bugfix/transaction-validation

# Hotfixes for production
git checkout -b hotfix/pattern-matching-callbacks
```

### Коммиты (Commits)
**Формат**: `type: short_description`

**Types**:
- `feat:` - новая функциональность
- `fix:` - исправление бага
- `refactor:` - рефакторинг без изменения функциональности
- `docs:` - обновление документации
- `test:` - добавление/изменение тестов
- `chore:` - технические изменения (зависимости, конфигурация)

**Примеры**:
```bash
git commit -m "feat: add TransactionService CRUD methods"
git commit -m "fix: prevent auto-deletion in pattern-matching callbacks"
git commit -m "refactor: simplify guard clauses in Goal.monthly_contribution"
git commit -m "docs: update ROADMAP.md with Phase 2 completion"
```

## Batch Process (план → батч)

### План-режим (БЕЗ правок кода)
1. Прочитать `ROADMAP.md` и `feature_progress.md`
2. Сформировать "План батча" (1-3 файла максимум)
3. Указать действия и ожидаемый эффект
4. **ЖДАТЬ** подтверждения пользователя

### Батч-режим (ПОСЛЕ подтверждения)
1. Редактировать **ТОЛЬКО** согласованные файлы
2. Показать diffs для review
3. Выполнить quality checks:
   ```bash
   black app/
   flake8 app/
   pytest
   ```
4. **По завершении**: обновить `ROADMAP.md` + `feature_progress.md`

**Ограничения**:
- ❌ НЕ править файлы вне списка батча
- ❌ Длинные списки/логи сохранять в `.reports/notes/*.md`, НЕ в чат

## Minimal Changes Principle

**Принцип**: Сохранять существующее поведение, минимальные изменения

```python
# ❌ Неправильно - полная переписывание
def old_function(x):
    return x * 2

def new_function(value: int) -> int:
    """Completely rewritten."""
    result = value + value
    return result

# ✅ Правильно - минимальные изменения
def old_function(x: int) -> int:  # Добавлены типы
    """Умножает значение на 2."""  # Добавлен docstring
    return x * 2  # Логика не изменилась
```

## Code Review Checklist

**Перед созданием PR**:
- [ ] Black форматирование применено (`black app/`)
- [ ] Flake8 без критичных ошибок (`flake8 app/`)
- [ ] Type annotations добавлены для public API
- [ ] Docstrings на русском для новых функций
- [ ] Guard clauses в начале функций
- [ ] Session management pattern соблюден (flush вместо commit)
- [ ] Pattern-Matching Callbacks проверены на автовызовы
- [ ] Тесты написаны для новой функциональности (если applicable)
- [ ] `ROADMAP.md` обновлен с прогрессом
- [ ] `feature_progress.md` обновлен после батча

## Anti-Patterns (НЕ ДЕЛАТЬ)

### ❌ Глобальные переменные
```python
# ❌ Неправильно
current_user = None

def get_user():
    global current_user
    return current_user
```

### ❌ Секреты в коде
```python
# ❌ Неправильно
DATABASE_PASSWORD = "secret123"

# ✅ Правильно
import os
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
```

### ❌ Хардкод вместо констант
```python
# ❌ Неправильно
if amount > 1000000:
    ...

# ✅ Правильно
MAX_TRANSACTION_AMOUNT = Decimal('1000000')
if amount > MAX_TRANSACTION_AMOUNT:
    ...
```

### ❌ Игнорирование ошибок
```python
# ❌ Неправильно
try:
    session.commit()
except:
    pass  # Silent failure

# ✅ Правильно
try:
    session.commit()
except SQLAlchemyError as e:
    logger.error(f"Database commit failed: {e}")
    session.rollback()
    raise
```

---

Референсы:
- PEP8: https://peps.python.org/pep-0008/
- Black: https://black.readthedocs.io/
- Type Hints: https://docs.python.org/3/library/typing.html
