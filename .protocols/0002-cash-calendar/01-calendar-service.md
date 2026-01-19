# Шаг 1: CalendarService — Backend Logic

## Briefing
- **Цель:** Реализовать сервис `CalendarService` для расчета кассовых остатков по дням с SQL агрегацией. Покрыть unit тестами.
- **Ключевые файлы:**
  - `app/services/calendar_service.py` (создать)
  - `app/services/__init__.py` (модифицировать — добавить export)
  - `tests/test_calendar_service.py` (создать)
- **Additional info:**
  - TRANSFER транзакции исключаются из расчетов баланса (это внутренние переводы)
  - Если User не найден — fallback на `Decimal('0')` вместо исключения
  - Формула: `balance(date) = starting_balance + SUM(INCOME until date) - SUM(EXPENSE until date)`

## Sub-tasks

### 1. Создать файл сервиса

Создать файл `app/services/calendar_service.py` со следующей структурой:

```python
"""Сервис для расчета кассовых остатков календаря."""

from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict
from calendar import monthrange

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.models.database import Transaction, TransactionType, User


class MonthSummary(TypedDict):
    """Сводка по месяцу для статистических карточек."""
    total_income: Decimal
    total_expense: Decimal
    start_balance: Decimal
    end_balance: Decimal
    month: int
    year: int
```

### 2. Реализовать класс CalendarService

Класс должен содержать:

**Конструктор:**
```python
def __init__(self, session: Session):
    """Инициализирует сервис календаря.

    Args:
        session: SQLAlchemy сессия для работы с БД
    """
    self.session = session
```

**Приватный метод `_get_starting_balance`:**
- Получает `starting_balance` пользователя
- Если User не найден — возвращает `Decimal('0')` (fallback)
- Если `starting_balance` is None — возвращает `Decimal('0')`

**Публичный метод `calculate_daily_balances`:**
- Сигнатура: `(user_id: int, start_date: date, end_date: date) -> dict[date, Decimal]`
- Валидация: `start_date <= end_date`, иначе `ValueError`
- SQL агрегация:
  1. Получить сумму INCOME и EXPENSE **до** start_date (balance_before_period)
  2. Получить изменения по дням в периоде через GROUP BY
  3. Кумулятивный расчет: `current_balance += change`
- **КРИТИЧНО**: Фильтровать только `INCOME` и `EXPENSE`, исключая `TRANSFER`

**Публичный метод `get_transactions_by_date`:**
- Сигнатура: `(user_id: int, start_date: date, end_date: date) -> dict[date, list[Transaction]]`
- Включает ВСЕ типы транзакций (для отображения в UI)
- Группировка по датам

**Публичный метод `get_month_summary`:**
- Сигнатура: `(user_id: int, year: int, month: int) -> MonthSummary`
- Агрегация `total_income` и `total_expense` (без TRANSFER)
- Использует `calculate_daily_balances` для start_balance и end_balance

### 3. Обновить `app/services/__init__.py`

Добавить export:
```python
from app.services.calendar_service import CalendarService, MonthSummary
```

### 4. Написать unit тесты

Создать файл `tests/test_calendar_service.py`:

**Тесты для `_get_starting_balance`:**
- Пользователь с `starting_balance=10000` → возвращает `Decimal('10000')`
- Пользователь не существует → возвращает `Decimal('0')`
- Пользователь с `starting_balance=None` → возвращает `Decimal('0')`

**Тесты для `calculate_daily_balances`:**
- Пустой период без транзакций → все дни равны starting_balance
- Одна INCOME транзакция → баланс увеличивается
- Одна EXPENSE транзакция → баланс уменьшается
- TRANSFER транзакция → НЕ влияет на баланс (КРИТИЧНО!)
- `start_date > end_date` → `ValueError`

**Тесты для `get_month_summary`:**
- Месяц с INCOME и EXPENSE → корректные суммы
- TRANSFER не учитывается в total_income/total_expense

### 5. SQL запросы (референс)

**Агрегация изменений до периода:**
```python
balance_before_period = self.session.query(
    func.coalesce(
        func.sum(
            case(
                (Transaction.transaction_type == TransactionType.INCOME, Transaction.amount),
                (Transaction.transaction_type == TransactionType.EXPENSE, -Transaction.amount),
                else_=Decimal("0"),
            )
        ),
        Decimal("0"),
    )
).filter(
    Transaction.user_id == user_id,
    Transaction.transaction_date < start_date,
    Transaction.transaction_type.in_([TransactionType.INCOME, TransactionType.EXPENSE]),
).scalar()
```

**Агрегация по дням:**
```python
daily_changes = (
    self.session.query(
        Transaction.transaction_date,
        func.sum(
            case(
                (Transaction.transaction_type == TransactionType.INCOME, Transaction.amount),
                (Transaction.transaction_type == TransactionType.EXPENSE, -Transaction.amount),
                else_=Decimal("0"),
            )
        ).label("daily_change"),
    )
    .filter(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date,
        Transaction.transaction_type.in_([TransactionType.INCOME, TransactionType.EXPENSE]),
    )
    .group_by(Transaction.transaction_date)
    .all()
)
```

## Workflow (Порядок работы)

**Твоя задача — выполнить `Sub-tasks` выше, строго следуя этому циклу.**

1. **Выполнение:** Последовательно выполняй подзадачи:
   - Создай `app/services/calendar_service.py`
   - Реализуй все методы класса
   - Обнови `app/services/__init__.py`
   - Создай тесты в `tests/test_calendar_service.py`

2. **Верификация:** После завершения ВСЕХ подзадач запусти проверки:
   ```bash
   black app/services/calendar_service.py tests/test_calendar_service.py
   flake8 app/services/calendar_service.py tests/test_calendar_service.py
   pytest tests/test_calendar_service.py -v
   ```
   Исправляй ошибки до "зеленых" проверок.

3. **Фиксация:** После успешной верификации:
   - Добавь запись в `log.md`
   - Обнови `context.md`: `Current Step` → `2`
   - Проверь ветку main в поисках случайно добавленных файлов

4. **Коммит:**
   ```bash
   git add .
   git commit -m "feat(calendar): implement CalendarService with daily balances [protocol-0002/01]"
   git push
   ```

5. **Отчет пользователю:** Используй формат из `plan.md`.

<формат_отчёта_о_шаге>
(Протокол 0002, шаг 1):

**Сделано**: список сделанных изменений.

**Проверки**: black, flake8, pytest — результаты.

**Git**:
- PR: WIP: 0002 - Кассовый календарь
- Ветка: 0002-cash-calendar
- Коммит: feat(calendar): implement CalendarService...
- main чистая: да/нет

**Рабочая папка**: /home/skytiger/PycharmProjects/worktrees/0002-cash-calendar

**Статус протокола**: Шаг 1 завершен, следующий — Шаг 2 (Calendar UI).
</формат_отчёта_о_шаге>
