# Solution v1: Кассовый календарь с расчетом остатков

## Обзор решения

Решение состоит из трех основных компонентов: (1) **CalendarService** для расчета остатков по дням с агрегацией операций через SQL, (2) **calendar.py** UI компонент для визуализации календарной сетки с операциями и остатками, (3) Dash callbacks для навигации и интеграции с формами создания/редактирования операций. Расчет остатков выполняется на backend с точностью Decimal, результаты кэшируются в dcc.Store для быстрого переключения месяцев.

## Архитектура

### Компоненты

#### 1. CalendarService (Backend Logic)
**Ответственность**: Бизнес-логика расчета кассовых остатков по датам

**Основные методы**:
- `calculate_daily_balances(user_id, start_date, end_date)` → dict[date, Decimal]
  - Получает starting_balance пользователя
  - Агрегирует доходы/расходы через SQL GROUP BY transaction_date
  - Рассчитывает накопительный остаток для каждого дня периода
  - Возвращает словарь: {date: balance}

- `get_transactions_by_date(user_id, start_date, end_date)` → dict[date, list[Transaction]]
  - Получает все операции пользователя за период
  - Группирует их по датам для отображения в календаре
  - Возвращает словарь: {date: [tx1, tx2, ...]}

- `get_month_summary(user_id, year, month)` → MonthSummary
  - Получает агрегированные данные за месяц:
    - total_income (сумма доходов)
    - total_expense (сумма расходов)
    - start_balance (остаток на начало месяца)
    - end_balance (остаток на конец месяца)
  - Используется для карточек статистики над календарем

**Оптимизация производительности**:
- SQL агрегация вместо Python циклов (в 10-20x быстрее)
- Один запрос для получения всех операций месяца
- Кэширование балансов в памяти для повторных вычислений
- Индекс `ix_transactions_user_date` обеспечивает быстрые range queries

#### 2. calendar.py (UI Component)
**Ответственность**: Визуализация календарной сетки с операциями и остатками

**Layout структура**:
```
┌──────────────────────────────────────────────┐
│  Header: [< Prev] [Январь 2026] [Next >]    │
│  Stats Cards: [Доходы] [Расходы] [Баланс]   │
├──────────────────────────────────────────────┤
│  Week Days: [Пн] [Вт] [Ср] [Чт] [Пт] [Сб] [Вс]
├──────────────────────────────────────────────┤
│  Calendar Grid (7 columns x 5-6 rows):       │
│  ┌───────┬───────┬───────┬───────┬──...      │
│  │ 1     │ 2     │ 3     │ 4     │           │
│  │ ↓↑    │       │ ↓     │       │           │
│  │ 15.5k │ 12.3k │ 18.2k │ 18.2k │           │
│  └───────┴───────┴───────┴───────┴──...      │
└──────────────────────────────────────────────┘
```

**Функции**:
- `create_calendar_layout()` - главная layout функция
- `_build_calendar_header(month, year)` - заголовок с навигацией
- `_build_stats_cards(month_summary)` - карточки статистики
- `_build_calendar_grid(calendar_data)` - сетка календаря
- `_build_day_cell(date, transactions, balance)` - ячейка одного дня
- `_format_balance(balance)` - форматирование остатка с цветом

**Стилизация**:
- Bootstrap Grid для адаптивности
- Кастомные CSS классы для цветовой индикации:
  - `.balance-positive` (зеленый)
  - `.balance-negative` (красный)
  - `.balance-warning` (желтый, < 10% от starting_balance)
- `.calendar-day` - базовый стиль ячейки дня
- `.calendar-day-today` - текущий день
- `.calendar-day-weekend` - выходные

#### 3. Dash Callbacks
**Ответственность**: Интерактивность и state management

**Callbacks**:
1. `load_calendar()` - загрузка календаря при входе на страницу
   - Input: `url.pathname` == "/calendar"
   - Output: calendar grid + stats cards + dcc.Store с данными

2. `change_month()` - переключение между месяцами
   - Input: prev_btn.n_clicks, next_btn.n_clicks, today_btn.n_clicks
   - State: current_month, current_year (из dcc.Store)
   - Output: calendar grid + header + updated store

3. `open_create_modal_from_calendar()` - открытие формы создания операции
   - Input: day_cell.n_clicks (Pattern-Matching ALL)
   - Output: create_modal.is_open + create_date_picker.date (предзаполнение)

4. `refresh_calendar_after_transaction()` - обновление после создания/изменения операции
   - Input: create_submit_btn.n_clicks, edit_submit_btn.n_clicks, delete_btn.n_clicks
   - Output: calendar grid + stats cards (пересчет балансов)

**State Management**:
- `dcc.Store(id="calendar-state")` хранит:
  ```python
  {
    "current_month": 1,  # 1-12
    "current_year": 2026,
    "balances": {date_str: float},  # Кэш балансов
    "transactions": {date_str: [tx_dict]}  # Кэш операций
  }
  ```

### Диаграмма взаимодействия

```
User Action → Dash Callback → CalendarService → Database → CalendarService → Callback → UI Update

Пример 1: Загрузка календаря
[User opens /calendar]
  → load_calendar() callback
  → CalendarService.get_month_summary(2026, 1)
  → CalendarService.calculate_daily_balances(2026-01-01, 2026-01-31)
  → CalendarService.get_transactions_by_date(2026-01-01, 2026-01-31)
  → [SQL queries to Transaction table]
  → Returns {balances: {...}, transactions: {...}, summary: {...}}
  → Callback builds calendar grid HTML
  → [UI renders calendar]

Пример 2: Переключение месяца
[User clicks "Next >"]
  → change_month() callback
  → ctx.triggered_id == "next-month-btn"
  → Increment current_month in State
  → CalendarService.calculate_daily_balances(new month)
  → Update calendar grid + header
  → [UI re-renders with new month]

Пример 3: Создание операции из календаря
[User clicks day cell 15]
  → open_create_modal_from_calendar() callback
  → Extract date from triggered_id["index"] (2026-01-15)
  → Open create_modal + set create_date_picker = 2026-01-15
  → [User fills form and submits]
  → create_transaction() callback (existing in transactions.py)
  → TransactionService.create_transaction(...)
  → refresh_calendar_after_transaction() callback
  → Re-calculate balances for month
  → Update calendar grid
  → [UI shows new transaction on calendar]
```

## Файловая структура

```
app/
├── services/
│   └── calendar_service.py       # НОВЫЙ - расчет балансов и агрегация операций
├── components/
│   └── calendar.py                # НОВЫЙ - UI календаря
│   └── transactions.py            # МОДИФИЦИРУЕТСЯ - добавить интеграцию с календарем
├── models/
│   └── database.py                # БЕЗ ИЗМЕНЕНИЙ - модели уже готовы
├── main.py                        # МОДИФИЦИРУЕТСЯ - обновить роутинг для /calendar
└── assets/
    └── calendar.css               # НОВЫЙ - стили календаря
```

## Ключевые интерфейсы

```python
# ======= app/services/calendar_service.py =======

from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import func
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


class CalendarService:
    """Сервис для расчета кассовых остатков календаря."""

    def __init__(self, session: Session):
        """Инициализирует сервис календаря.

        Args:
            session: SQLAlchemy сессия для работы с БД
        """
        self.session = session

    def calculate_daily_balances(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> dict[date, Decimal]:
        """Рассчитывает остатки средств на каждый день периода.

        Формула: balance(date) = starting_balance
                                + SUM(income until date)
                                - SUM(expense until date)

        Args:
            user_id: ID пользователя
            start_date: Начало периода (включительно)
            end_date: Конец периода (включительно)

        Returns:
            dict[date, Decimal]: {date: balance} для каждого дня периода

        Example:
            >>> service.calculate_daily_balances(1, date(2026,1,1), date(2026,1,31))
            {
                date(2026, 1, 1): Decimal('10000.00'),
                date(2026, 1, 2): Decimal('9500.00'),
                # ... каждый день месяца
            }
        """
        ...

    def get_transactions_by_date(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> dict[date, list[Transaction]]:
        """Получает операции пользователя, сгруппированные по датам.

        Args:
            user_id: ID пользователя
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            dict[date, list[Transaction]]: {date: [tx1, tx2, ...]}
        """
        ...

    def get_month_summary(
        self,
        user_id: int,
        year: int,
        month: int,
    ) -> MonthSummary:
        """Получает сводку по месяцу для статистических карточек.

        Args:
            user_id: ID пользователя
            year: Год (например, 2026)
            month: Месяц (1-12)

        Returns:
            MonthSummary: Агрегированные данные месяца
        """
        ...


# ======= app/components/calendar.py =======

import calendar
from datetime import date, timedelta
from decimal import Decimal

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ALL, ctx
from dash.exceptions import PreventUpdate

from app.core import get_db_session
from app.services.calendar_service import CalendarService
from app.models.database import TransactionType


def create_calendar_layout():
    """Создает layout страницы кассового календаря.

    Returns:
        dash component: Layout календаря
    """
    ...


def _build_calendar_header(month: int, year: int) -> html.Div:
    """Создает заголовок календаря с навигацией."""
    ...


def _build_stats_cards(summary: dict) -> html.Div:
    """Создает карточки статистики над календарем."""
    ...


def _build_calendar_grid(
    month: int,
    year: int,
    balances: dict[date, Decimal],
    transactions: dict[date, list]
) -> html.Div:
    """Создает календарную сетку с днями, операциями и остатками."""
    ...


def _build_day_cell(
    day_date: date,
    balance: Decimal,
    transactions: list,
    is_today: bool = False
) -> html.Div:
    """Создает ячейку одного дня календаря."""
    ...


# ======= Callbacks =======

@callback(
    [
        Output("calendar-header", "children"),
        Output("calendar-stats", "children"),
        Output("calendar-grid", "children"),
        Output("calendar-state", "data"),
    ],
    [
        Input("url", "pathname"),
        Input("prev-month-btn", "n_clicks"),
        Input("next-month-btn", "n_clicks"),
        Input("today-btn", "n_clicks"),
    ],
    [State("calendar-state", "data")],
    prevent_initial_call=True,
)
def load_and_navigate_calendar(
    pathname,
    prev_clicks,
    next_clicks,
    today_clicks,
    state
):
    """Загружает календарь и обрабатывает навигацию между месяцами."""
    ...


@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("create-date-picker", "date", allow_duplicate=True),
    ],
    Input({"type": "calendar-day", "date": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_create_modal_from_calendar(n_clicks_list):
    """Открывает модал создания операции при клике на день календаря."""
    ...
```

## Модель данных

### MonthSummary TypedDict
```python
class MonthSummary(TypedDict):
    """Агрегированные данные месяца для статистических карточек."""

    total_income: Decimal      # Сумма всех доходов за месяц
    total_expense: Decimal     # Сумма всех расходов за месяц
    start_balance: Decimal     # Остаток на начало месяца (1 число)
    end_balance: Decimal       # Остаток на конец месяца (последний день)
    month: int                 # Месяц (1-12)
    year: int                  # Год (например, 2026)
```

### CalendarState (dcc.Store)
```python
{
    "current_month": int,      # Текущий отображаемый месяц (1-12)
    "current_year": int,       # Текущий отображаемый год (например, 2026)
}
```

### Balance Dictionary
```python
dict[date, Decimal]            # {date(2026,1,1): Decimal('10000.00'), ...}
```

### Transactions Dictionary
```python
dict[date, list[Transaction]]  # {date(2026,1,1): [tx1, tx2], ...}
```

## Обработка ошибок

### CalendarService Exceptions

```python
# В calculate_daily_balances()
if start_date > end_date:
    raise ValueError("start_date должен быть <= end_date")

if not user:
    raise ValueError(f"Пользователь {user_id} не найден")
```

### UI Error Handling

```python
# В callbacks - обертка try/except с fallback UI
try:
    # Загрузка данных календаря
    with get_db_session() as session:
        service = CalendarService(session)
        # ...
except Exception as e:
    logger.error(f"Ошибка загрузки календаря: {e}")
    return (
        _build_calendar_header(current_month, current_year),
        _build_error_alert("Не удалось загрузить данные календаря. Попробуйте обновить страницу."),
        html.Div(),  # Пустая сетка
        state  # Не обновляем state
    )
```

### Database Errors
- SQLAlchemy exceptions логируются через loguru logger
- Пользователю показывается dbc.Alert с понятным сообщением
- State календаря сохраняется (не сбрасывается на начальное значение)

## План реализации

### Шаг 1: CalendarService (Backend Logic)
**Время**: 2 часа

1. Создать `app/services/calendar_service.py`
2. Реализовать `CalendarService` класс с методами:
   - `calculate_daily_balances()` - SQL агрегация + кумулятивный расчет
   - `get_transactions_by_date()` - группировка операций по датам
   - `get_month_summary()` - агрегация доходов/расходов месяца
3. Добавить `MonthSummary` TypedDict для type hints
4. Написать unit тесты для edge cases

**Критерии готовности**:
- Все методы возвращают Decimal (не float)
- Unit тесты проходят
- SQL запросы используют индексы

### Шаг 2: Calendar UI Component
**Время**: 3 часа

1. Создать `app/components/calendar.py`
2. Реализовать layout функции
3. Создать `app/assets/calendar.css` с кастомными стилями
4. Использовать Python `calendar` модуль для генерации сетки

**Критерии готовности**:
- Календарь корректно отображает все дни месяца
- Выходные визуально отличаются
- Текущий день выделяется

### Шаг 3: Dash Callbacks (Интерактивность)
**Время**: 2 часа

1. Реализовать `load_and_navigate_calendar()`
2. Реализовать `open_create_modal_from_calendar()`

**Критерии готовности**:
- Навигация работает без задержек (< 500ms)
- Клик по дню открывает модал с правильной датой
- Нет автовызовов при обновлении календаря

### Шаг 4: Интеграция с Transactions
**Время**: 1 час

1. Модифицировать `app/components/transactions.py`
2. Обновить `app/main.py`

**Критерии готовности**:
- После создания операции календарь обновляется
- После редактирования операции балансы пересчитываются
- После удаления операции календарь обновляется

### Шаг 5: Тестирование и полировка UX
**Время**: 2 часа

1. Функциональное тестирование
2. UX полировка
3. Обработка ошибок

**Критерии готовности**:
- Все критерии приёмки из Brief выполнены
- Производительность соответствует требованиям
- Нет критических UI багов

### Шаг 6: Документация и Code Review
**Время**: 1 час

1. Обновить документацию
2. Code review
3. Git commit

**Общее время реализации**: 11 часов (1.5 дня разработки)

## Зависимости

### Новые библиотеки
**Не требуются** - все зависимости уже установлены:
- `calendar` (Python standard library)
- `datetime`, `timedelta` (Python standard library)
- `sqlalchemy.func` (уже используется)
- `dash`, `dash_bootstrap_components`, `plotly` (уже установлены)

### Обновления существующих файлов
- `app/main.py` - обновить роутинг (1 строка изменения)
- `app/components/transactions.py` - добавить callback интеграции (10 строк)
- `requirements.txt` - без изменений

## Риски и mitigation

| Риск | Вероятность | Воздействие | Mitigation |
|------|-------------|-------------|------------|
| **Производительность SQL при большом количестве операций** | Средняя | Высокое | - Использовать SQL агрегацию (GROUP BY) вместо Python циклов<br>- Индекс `ix_transactions_user_date` уже существует<br>- Ограничить period загрузки (текущий месяц ± 12 месяцев)<br>- При необходимости добавить PostgreSQL MATERIALIZED VIEW для кэширования |
| **Сложность Dash Pattern-Matching для кликов по дням** | Средняя | Среднее | - Использовать проверенный паттерн из transactions.py (проверка `ctx.triggered[0].get('value')`)<br>- Guard clauses для предотвращения автовызовов<br>- Тестирование на реальных данных |
| **UX календаря - пользователи не понимают концепцию** | Низкая | Высокое | - Добавить подсказки (tooltips) на ключевые элементы<br>- Цветовая индикация остатков (красный = опасность)<br>- Статистические карточки над календарем для контекста<br>- При необходимости добавить онбординг (Batch 4) |
| **Точность расчетов Decimal при округлении** | Низкая | Среднее | - Использовать `Decimal` везде (не float)<br>- Unit тесты на граничные случаи<br>- Проверка precision в SQL запросах |
| **Регрессия в существующем функционале Transactions** | Низкая | Среднее | - Минимальные изменения в transactions.py (только добавление callback)<br>- Тестирование Create/Edit/Delete после интеграции<br>- Code review перед коммитом |
| **Задержка разработки из-за сложности** | Средняя | Низкое | - Инкрементальная реализация (6 шагов по 1-3 часа)<br>- Приоритизация Must Have функций<br>- Буфер времени 20% (11 часов → 13 часов) |

## Критические файлы для реализации

| Файл | Статус | Описание |
|------|--------|----------|
| `app/services/calendar_service.py` | **НОВЫЙ** | Ядро бизнес-логики расчета остатков, SQL агрегация операций |
| `app/components/calendar.py` | **НОВЫЙ** | UI компонент календарной сетки, визуализация операций и остатков, Dash callbacks |
| `app/assets/calendar.css` | **НОВЫЙ** | Стили календаря |
| `app/models/database.py` | Справка | Существующие модели (User, Transaction, TransactionType) |
| `app/components/transactions.py` | Модифицировать | Добавить callback интеграции для обновления календаря после CRUD |
| `app/main.py` | Модифицировать | Обновить роутинг `/calendar` → `create_calendar_layout()` |
