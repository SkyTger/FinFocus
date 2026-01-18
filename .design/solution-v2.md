# Solution v2: Кассовый календарь с расчетом остатков

## Обзор решения

Решение состоит из трех основных компонентов: (1) **CalendarService** для расчета остатков по дням с SQL агрегацией, (2) **calendar.py** UI компонент для визуализации календарной сетки, (3) Dash callbacks с проверенными guard clauses согласно ADR-003.

### ЧТО ИЗМЕНИЛОСЬ относительно v1:

1. **Decimal сериализация** - добавлены утилиты `serialize_balances()` / `deserialize_balances()` для хранения в dcc.Store как строки
2. **Guard clauses** - полная реализация проверок согласно transactions.py паттерну и ADR-003
3. **refresh_calendar_after_transaction()** - полная сигнатура с allow_duplicate=True
4. **starting_balance fallback** - обработка случая User не найден с fallback на Decimal('0')
5. **TRANSFER транзакции** - явное исключение из расчетов баланса
6. **Локализация** - словарь MONTH_NAMES_RU для русских названий месяцев
7. **Warning threshold** - конфигурируемый порог предупреждения (по умолчанию 5000 руб.)
8. **Валидация +-12 месяцев** - добавлена в change_month() callback
9. **ID модалов** - используется существующий create-modal из transactions.py

## Архитектура

### Компоненты

#### 1. CalendarService (Backend Logic)
**Ответственность**: Бизнес-логика расчета кассовых остатков по датам

**Основные методы**:
- `calculate_daily_balances(user_id, start_date, end_date)` - dict[date, Decimal]
  - Получает starting_balance с fallback на Decimal('0')
  - **TRANSFER транзакции исключаются из расчета**
  - SQL агрегация через GROUP BY transaction_date
  - Кумулятивный расчет остатков

- `get_transactions_by_date(user_id, start_date, end_date)` - dict[date, list[Transaction]]
  - Включает ВСЕ типы транзакций (INCOME, EXPENSE, TRANSFER) для отображения
  - Группировка по датам

- `get_month_summary(user_id, year, month)` - MonthSummary
  - **TRANSFER исключается из total_income и total_expense**
  - Агрегация только INCOME и EXPENSE

#### 2. calendar.py (UI Component)
**Ответственность**: Визуализация календарной сетки

**Новые утилиты**:
- `serialize_balances(balances: dict[date, Decimal]) -> dict[str, str]` - для JSON
- `deserialize_balances(data: dict[str, str]) -> dict[date, Decimal]` - из JSON
- `MONTH_NAMES_RU` - словарь локализации месяцев
- `WARNING_BALANCE_THRESHOLD = Decimal('5000')` - порог предупреждения

#### 3. Dash Callbacks
**Ответственность**: Интерактивность с проверенными guard clauses

**Guard clauses паттерн** (из transactions.py):
```python
# 1. Проверка triggered_id
if not triggered_id:
    raise PreventUpdate

# 2. Проверка типа (для Pattern-Matching)
if not isinstance(triggered_id, dict) or triggered_id.get("type") != "expected-type":
    raise PreventUpdate

# 3. Проверка реального клика (КРИТИЧНО!)
if not ctx.triggered or ctx.triggered[0].get("value") is None:
    raise PreventUpdate
```

### Диаграмма взаимодействия

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTIONS                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [Open /calendar]     [Click < >]      [Click Day]      [CRUD in modal] │
│         │                  │                │                  │        │
│         ▼                  ▼                ▼                  ▼        │
│  load_and_navigate   change_month   open_create_modal   refresh_after  │
│         │                  │                │            _transaction   │
│         │                  │                │                  │        │
│         └──────────────────┼────────────────┼──────────────────┘        │
│                            ▼                │                           │
│                    CalendarService          │                           │
│                            │                │                           │
│     ┌──────────────────────┼────────────────┘                           │
│     │                      │                                            │
│     ▼                      ▼                                            │
│  calculate_         get_transactions_                                   │
│  daily_balances     by_date                                             │
│     │                      │                                            │
│     │    ┌─────────────────┘                                            │
│     │    │                                                              │
│     ▼    ▼                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                        DATABASE                                    │ │
│  │  User.starting_balance + Transaction (INCOME/EXPENSE only)        │ │
│  │  TRANSFER excluded from balance calculations                       │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│                            │                                            │
│                            ▼                                            │
│                   serialize_balances()                                  │
│                            │                                            │
│                            ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  dcc.Store("calendar-state")                                       │ │
│  │  {                                                                 │ │
│  │    "current_month": 1,                                             │ │
│  │    "current_year": 2026,                                           │ │
│  │    "balances": {"2026-01-01": "10000.00", ...}  # строки!         │ │
│  │  }                                                                 │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│                            │                                            │
│                            ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      CALENDAR UI                                   │ │
│  │  Header: [<] [Январь 2026] [>] [Сегодня]                          │ │
│  │  Stats:  [Доходы: +50k] [Расходы: -35k] [Баланс: 15k]            │ │
│  │  Grid:   7x5 cells with day numbers, transaction icons, balances  │ │
│  │  Colors: green (positive), red (negative), yellow (< 5000)        │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Файловая структура

```
app/
├── services/
│   ├── __init__.py              # МОДИФИЦИРУЕТСЯ - добавить CalendarService
│   └── calendar_service.py      # НОВЫЙ - расчет балансов и агрегация
├── components/
│   ├── calendar.py              # НОВЫЙ - UI календаря с callbacks
│   └── transactions.py          # МОДИФИЦИРУЕТСЯ - интеграция (минимум)
├── models/
│   └── database.py              # БЕЗ ИЗМЕНЕНИЙ
├── main.py                      # МОДИФИЦИРУЕТСЯ - роутинг /calendar
└── assets/
    └── calendar.css             # НОВЫЙ - стили календаря
```

## Ключевые интерфейсы

```python
# ======= app/services/calendar_service.py =======

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


class CalendarService:
    """Сервис для расчета кассовых остатков календаря.

    TRANSFER транзакции НЕ учитываются в расчете баланса,
    т.к. это внутренние переводы между счетами пользователя.
    """

    def __init__(self, session: Session):
        """Инициализирует сервис календаря.

        Args:
            session: SQLAlchemy сессия для работы с БД
        """
        self.session = session

    def _get_starting_balance(self, user_id: int) -> Decimal:
        """Получает starting_balance пользователя с fallback.

        Args:
            user_id: ID пользователя

        Returns:
            Decimal: starting_balance или Decimal('0') если User не найден
        """
        user = self.session.get(User, user_id)
        if not user:
            return Decimal("0")  # Fallback вместо исключения
        return user.starting_balance or Decimal("0")

    def calculate_daily_balances(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> dict[date, Decimal]:
        """Рассчитывает остатки средств на каждый день периода.

        Формула: balance(date) = starting_balance
                                + SUM(INCOME until date)
                                - SUM(EXPENSE until date)

        ВАЖНО: TRANSFER транзакции ИСКЛЮЧАЮТСЯ из расчета.

        Args:
            user_id: ID пользователя
            start_date: Начало периода (включительно)
            end_date: Конец периода (включительно)

        Returns:
            dict[date, Decimal]: {date: balance} для каждого дня периода

        Raises:
            ValueError: Если start_date > end_date
        """
        if start_date > end_date:
            raise ValueError("start_date должен быть <= end_date")

        starting_balance = self._get_starting_balance(user_id)

        # SQL агрегация: сумма INCOME и EXPENSE до start_date
        # TRANSFER исключается
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

        initial_balance = starting_balance + (balance_before_period or Decimal("0"))

        # SQL агрегация по дням периода
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

        # Преобразуем в словарь
        changes_by_date = {row.transaction_date: row.daily_change or Decimal("0") for row in daily_changes}

        # Кумулятивный расчет балансов
        balances = {}
        current_balance = initial_balance
        current_date = start_date

        while current_date <= end_date:
            current_balance += changes_by_date.get(current_date, Decimal("0"))
            balances[current_date] = current_balance
            current_date += timedelta(days=1)

        return balances

    def get_transactions_by_date(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> dict[date, list[Transaction]]:
        """Получает операции пользователя, сгруппированные по датам.

        Включает ВСЕ типы транзакций (INCOME, EXPENSE, TRANSFER)
        для отображения в календаре.

        Args:
            user_id: ID пользователя
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            dict[date, list[Transaction]]: {date: [tx1, tx2, ...]}
        """
        transactions = (
            self.session.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
            )
            .order_by(Transaction.transaction_date)
            .all()
        )

        result: dict[date, list[Transaction]] = {}
        for tx in transactions:
            if tx.transaction_date not in result:
                result[tx.transaction_date] = []
            result[tx.transaction_date].append(tx)

        return result

    def get_month_summary(
        self,
        user_id: int,
        year: int,
        month: int,
    ) -> MonthSummary:
        """Получает сводку по месяцу для статистических карточек.

        TRANSFER транзакции НЕ учитываются в total_income/total_expense.

        Args:
            user_id: ID пользователя
            year: Год (например, 2026)
            month: Месяц (1-12)

        Returns:
            MonthSummary: Агрегированные данные месяца
        """
        _, last_day = monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)

        # SQL агрегация
        totals = self.session.query(
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.transaction_type == TransactionType.INCOME, Transaction.amount),
                        else_=Decimal("0"),
                    )
                ),
                Decimal("0"),
            ).label("total_income"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.transaction_type == TransactionType.EXPENSE, Transaction.amount),
                        else_=Decimal("0"),
                    )
                ),
                Decimal("0"),
            ).label("total_expense"),
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.transaction_type.in_([TransactionType.INCOME, TransactionType.EXPENSE]),
        ).first()

        total_income = totals.total_income if totals else Decimal("0")
        total_expense = totals.total_expense if totals else Decimal("0")

        # Балансы на начало и конец месяца
        balances = self.calculate_daily_balances(user_id, start_date, end_date)
        start_balance = balances.get(start_date, Decimal("0"))
        end_balance = balances.get(end_date, Decimal("0"))

        return MonthSummary(
            total_income=total_income,
            total_expense=total_expense,
            start_balance=start_balance,
            end_balance=end_balance,
            month=month,
            year=year,
        )


# ======= app/components/calendar.py =======

import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ALL, ctx, no_update
from dash.exceptions import PreventUpdate
from dateutil.relativedelta import relativedelta
from loguru import logger

from app.core import get_db_session
from app.services.calendar_service import CalendarService, MonthSummary
from app.models.database import TransactionType


# ==================== КОНСТАНТЫ ====================

MONTH_NAMES_RU = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}

WEEKDAY_NAMES_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

# Порог для желтого предупреждения (конфигурируемый)
WARNING_BALANCE_THRESHOLD = Decimal("5000")

# Ограничение навигации: +-12 месяцев от сегодня
MAX_MONTHS_OFFSET = 12


# ==================== УТИЛИТЫ СЕРИАЛИЗАЦИИ ====================

def serialize_balances(balances: dict[date, Decimal]) -> dict[str, str]:
    """Сериализует балансы для хранения в dcc.Store.

    Decimal не сериализуется в JSON, поэтому конвертируем в строки.

    Args:
        balances: {date: Decimal}

    Returns:
        dict[str, str]: {"YYYY-MM-DD": "12345.67", ...}
    """
    return {dt.isoformat(): str(balance) for dt, balance in balances.items()}


def deserialize_balances(data: dict[str, str]) -> dict[date, Decimal]:
    """Десериализует балансы из dcc.Store.

    Args:
        data: {"YYYY-MM-DD": "12345.67", ...}

    Returns:
        dict[date, Decimal]: {date: Decimal}
    """
    if not data:
        return {}
    return {
        date.fromisoformat(dt_str): Decimal(balance_str)
        for dt_str, balance_str in data.items()
    }


def serialize_transactions_for_store(
    transactions: dict[date, list]
) -> dict[str, list[dict[str, Any]]]:
    """Сериализует транзакции для хранения в dcc.Store.

    Args:
        transactions: {date: [Transaction, ...]}

    Returns:
        dict с JSON-совместимыми типами
    """
    result = {}
    for dt, tx_list in transactions.items():
        result[dt.isoformat()] = [
            {
                "id": tx.id,
                "amount": str(tx.amount),  # Decimal -> str
                "transaction_type": tx.transaction_type.value,
                "description": tx.description,
            }
            for tx in tx_list
        ]
    return result


# ==================== ФОРМАТИРОВАНИЕ ====================

def format_balance(balance: Decimal) -> tuple[str, str]:
    """Форматирует баланс с определением CSS класса.

    Args:
        balance: Сумма баланса

    Returns:
        tuple: (отформатированная строка, CSS класс)
    """
    formatted = f"{balance:,.0f}".replace(",", " ")

    if balance < 0:
        return formatted, "balance-negative"
    elif balance < WARNING_BALANCE_THRESHOLD:
        return formatted, "balance-warning"
    else:
        return formatted, "balance-positive"


def format_month_header(month: int, year: int) -> str:
    """Форматирует заголовок месяца на русском.

    Args:
        month: Месяц (1-12)
        year: Год

    Returns:
        str: "Январь 2026"
    """
    return f"{MONTH_NAMES_RU[month]} {year}"


# ==================== UI КОМПОНЕНТЫ ====================

def create_calendar_layout() -> html.Div:
    """Создает layout страницы кассового календаря.

    Returns:
        html.Div: Layout календаря
    """
    today = date.today()

    return html.Div(
        [
            # State хранилище
            dcc.Store(
                id="calendar-state",
                data={
                    "current_month": today.month,
                    "current_year": today.year,
                    "balances": {},  # Будет заполнено при загрузке
                },
            ),
            # Заголовок с навигацией
            html.Div(id="calendar-header"),
            # Карточки статистики
            html.Div(id="calendar-stats", className="mb-4"),
            # Календарная сетка
            html.Div(id="calendar-grid"),
        ]
    )


def _build_calendar_header(month: int, year: int) -> html.Div:
    """Создает заголовок календаря с навигацией.

    Args:
        month: Текущий месяц (1-12)
        year: Текущий год

    Returns:
        html.Div: Заголовок с кнопками навигации
    """
    today = date.today()
    current_date = date(year, month, 1)
    min_date = today - relativedelta(months=MAX_MONTHS_OFFSET)
    max_date = today + relativedelta(months=MAX_MONTHS_OFFSET)

    # Определяем доступность кнопок
    prev_disabled = current_date <= date(min_date.year, min_date.month, 1)
    next_disabled = current_date >= date(max_date.year, max_date.month, 1)
    today_disabled = (month == today.month and year == today.year)

    return html.Div(
        [
            dbc.Button(
                html.I(className="bi bi-chevron-left"),
                id="prev-month-btn",
                color="secondary",
                outline=True,
                disabled=prev_disabled,
                className="me-2",
            ),
            html.H4(
                format_month_header(month, year),
                className="mb-0 mx-3",
                style={"minWidth": "180px", "textAlign": "center"},
            ),
            dbc.Button(
                html.I(className="bi bi-chevron-right"),
                id="next-month-btn",
                color="secondary",
                outline=True,
                disabled=next_disabled,
                className="me-2",
            ),
            dbc.Button(
                "Сегодня",
                id="today-btn",
                color="primary",
                outline=True,
                disabled=today_disabled,
                className="ms-3",
            ),
        ],
        className="d-flex align-items-center justify-content-center mb-4",
    )


def _build_stats_cards(summary: MonthSummary) -> html.Div:
    """Создает карточки статистики над календарем.

    Args:
        summary: Сводка по месяцу

    Returns:
        html.Div: Три карточки (Доходы, Расходы, Баланс)
    """
    balance_diff = summary["total_income"] - summary["total_expense"]
    balance_color = "success" if balance_diff >= 0 else "danger"
    balance_prefix = "+" if balance_diff >= 0 else ""

    return dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P("Доходы", className="text-muted mb-1"),
                            html.H5(
                                f"+{summary['total_income']:,.0f}".replace(",", " "),
                                className="text-success mb-0",
                            ),
                        ]
                    ),
                    className="shadow-sm",
                ),
                width=4,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P("Расходы", className="text-muted mb-1"),
                            html.H5(
                                f"-{summary['total_expense']:,.0f}".replace(",", " "),
                                className="text-danger mb-0",
                            ),
                        ]
                    ),
                    className="shadow-sm",
                ),
                width=4,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P("Баланс", className="text-muted mb-1"),
                            html.H5(
                                f"{balance_prefix}{balance_diff:,.0f}".replace(",", " "),
                                className=f"text-{balance_color} mb-0",
                            ),
                        ]
                    ),
                    className="shadow-sm",
                ),
                width=4,
            ),
        ],
        className="g-3",
    )


def _build_calendar_grid(
    month: int,
    year: int,
    balances: dict[date, Decimal],
    transactions: dict[date, list],
) -> html.Div:
    """Создает календарную сетку с днями, операциями и остатками.

    Args:
        month: Месяц (1-12)
        year: Год
        balances: {date: Decimal}
        transactions: {date: [Transaction, ...]}

    Returns:
        html.Div: Сетка календаря
    """
    today = date.today()
    cal = calendar.Calendar(firstweekday=0)  # Понедельник = 0
    month_days = cal.monthdatescalendar(year, month)

    # Заголовок дней недели
    weekday_header = html.Div(
        [
            html.Div(
                day_name,
                className="calendar-weekday text-center text-muted",
                style={"width": "14.28%"},  # 100% / 7
            )
            for day_name in WEEKDAY_NAMES_RU
        ],
        className="d-flex border-bottom mb-2 pb-2",
    )

    # Строки календаря
    calendar_rows = []
    for week in month_days:
        week_cells = []
        for day_date in week:
            is_current_month = day_date.month == month
            is_today = day_date == today
            is_weekend = day_date.weekday() >= 5

            day_balance = balances.get(day_date, Decimal("0"))
            day_transactions = transactions.get(day_date, [])

            cell = _build_day_cell(
                day_date=day_date,
                balance=day_balance,
                transactions=day_transactions,
                is_today=is_today,
                is_current_month=is_current_month,
                is_weekend=is_weekend,
            )
            week_cells.append(cell)

        calendar_rows.append(
            html.Div(week_cells, className="d-flex")
        )

    return html.Div(
        [weekday_header] + calendar_rows,
        className="calendar-grid",
    )


def _build_day_cell(
    day_date: date,
    balance: Decimal,
    transactions: list,
    is_today: bool = False,
    is_current_month: bool = True,
    is_weekend: bool = False,
) -> html.Div:
    """Создает ячейку одного дня календаря.

    Args:
        day_date: Дата дня
        balance: Остаток на этот день
        transactions: Список транзакций дня
        is_today: Текущий день
        is_current_month: День текущего месяца
        is_weekend: Выходной день

    Returns:
        html.Div: Ячейка дня (кликабельная)
    """
    # CSS классы
    css_classes = ["calendar-day"]
    if is_today:
        css_classes.append("calendar-day-today")
    if not is_current_month:
        css_classes.append("calendar-day-other-month")
    if is_weekend:
        css_classes.append("calendar-day-weekend")

    # Иконки транзакций
    income_count = sum(1 for tx in transactions if tx.transaction_type == TransactionType.INCOME)
    expense_count = sum(1 for tx in transactions if tx.transaction_type == TransactionType.EXPENSE)

    transaction_icons = []
    if income_count > 0:
        transaction_icons.append(
            html.Span("↓", className="text-success me-1", title=f"Доходы: {income_count}")
        )
    if expense_count > 0:
        transaction_icons.append(
            html.Span("↑", className="text-danger me-1", title=f"Расходы: {expense_count}")
        )

    total_tx = len(transactions)
    if total_tx > 2:
        transaction_icons.append(
            html.Span(f"+{total_tx - 2}", className="text-muted small")
        )

    # Форматирование баланса
    balance_text, balance_class = format_balance(balance)

    # Tooltip с деталями
    tooltip_content = _build_day_tooltip(day_date, transactions, balance)

    return html.Div(
        [
            # Номер дня
            html.Div(
                str(day_date.day),
                className="calendar-day-number",
            ),
            # Иконки транзакций
            html.Div(
                transaction_icons,
                className="calendar-day-icons",
            ) if transaction_icons else None,
            # Баланс
            html.Div(
                balance_text,
                className=f"calendar-day-balance {balance_class}",
            ) if is_current_month else None,
        ],
        id={"type": "calendar-day", "date": day_date.isoformat()},
        className=" ".join(css_classes),
        title=tooltip_content,
        n_clicks=0,
    )


def _build_day_tooltip(
    day_date: date,
    transactions: list,
    balance: Decimal,
) -> str:
    """Создает текст tooltip для дня.

    Args:
        day_date: Дата
        transactions: Список транзакций
        balance: Остаток

    Returns:
        str: Текст tooltip
    """
    lines = [day_date.strftime("%d.%m.%Y")]

    if transactions:
        lines.append("---")
        for tx in transactions[:5]:  # Максимум 5 в tooltip
            prefix = "+" if tx.transaction_type == TransactionType.INCOME else "-"
            lines.append(f"{prefix}{tx.amount:,.0f}".replace(",", " "))
        if len(transactions) > 5:
            lines.append(f"...и ещё {len(transactions) - 5}")

    lines.append("---")
    lines.append(f"Остаток: {balance:,.0f}".replace(",", " "))

    return "\n".join(lines)


def _build_error_alert(message: str) -> dbc.Alert:
    """Создает Alert с сообщением об ошибке.

    Args:
        message: Текст ошибки

    Returns:
        dbc.Alert: Компонент Alert
    """
    return dbc.Alert(
        message,
        color="danger",
        dismissable=True,
    )


# ==================== CALLBACKS ====================

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
    pathname: str,
    prev_clicks: int | None,
    next_clicks: int | None,
    today_clicks: int | None,
    state: dict,
):
    """Загружает календарь и обрабатывает навигацию между месяцами.

    Args:
        pathname: Текущий URL
        prev_clicks: Клики на "<"
        next_clicks: Клики на ">"
        today_clicks: Клики на "Сегодня"
        state: Текущее состояние календаря

    Returns:
        tuple: (header, stats, grid, updated_state)
    """
    triggered_id = ctx.triggered_id

    # Guard: проверка URL
    if pathname != "/calendar":
        raise PreventUpdate

    # Определяем текущий месяц/год
    today = date.today()
    current_month = state.get("current_month", today.month)
    current_year = state.get("current_year", today.year)

    # Обработка навигации
    if triggered_id == "prev-month-btn":
        new_date = date(current_year, current_month, 1) - relativedelta(months=1)
        current_month = new_date.month
        current_year = new_date.year
    elif triggered_id == "next-month-btn":
        new_date = date(current_year, current_month, 1) + relativedelta(months=1)
        current_month = new_date.month
        current_year = new_date.year
    elif triggered_id == "today-btn":
        current_month = today.month
        current_year = today.year

    # Валидация +-12 месяцев
    target_date = date(current_year, current_month, 1)
    min_date = today - relativedelta(months=MAX_MONTHS_OFFSET)
    max_date = today + relativedelta(months=MAX_MONTHS_OFFSET)

    if target_date < date(min_date.year, min_date.month, 1):
        raise PreventUpdate
    if target_date > date(max_date.year, max_date.month, 1):
        raise PreventUpdate

    # Загрузка данных
    try:
        with get_db_session() as session:
            service = CalendarService(session)

            # Определяем границы месяца
            _, last_day = calendar.monthrange(current_year, current_month)
            start_date = date(current_year, current_month, 1)
            end_date = date(current_year, current_month, last_day)

            # Получаем данные
            summary = service.get_month_summary(user_id=1, year=current_year, month=current_month)
            balances = service.calculate_daily_balances(user_id=1, start_date=start_date, end_date=end_date)
            transactions = service.get_transactions_by_date(user_id=1, start_date=start_date, end_date=end_date)

            logger.debug(f"Загружен календарь {current_month}/{current_year}")

            # Строим UI
            header = _build_calendar_header(current_month, current_year)
            stats = _build_stats_cards(summary)
            grid = _build_calendar_grid(current_month, current_year, balances, transactions)

            # Обновляем state с сериализацией
            new_state = {
                "current_month": current_month,
                "current_year": current_year,
                "balances": serialize_balances(balances),
            }

            return header, stats, grid, new_state

    except Exception as e:
        logger.error(f"Ошибка загрузки календаря: {e}")
        return (
            _build_calendar_header(current_month, current_year),
            _build_error_alert("Не удалось загрузить данные календаря. Попробуйте обновить страницу."),
            html.Div(),
            state,  # Не обновляем state при ошибке
        )


@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("create-date-picker", "date", allow_duplicate=True),
    ],
    Input({"type": "calendar-day", "date": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_create_modal_from_calendar(n_clicks_list: list[int | None]):
    """Открывает модал создания операции при клике на день календаря.

    Использует существующий create-modal из transactions.py.

    Args:
        n_clicks_list: Список кликов по всем ячейкам дней

    Returns:
        tuple: (is_open, selected_date)
    """
    triggered_id = ctx.triggered_id

    # Guard #1: проверка triggered_id
    if not triggered_id:
        raise PreventUpdate

    # Guard #2: проверка типа
    if not isinstance(triggered_id, dict) or triggered_id.get("type") != "calendar-day":
        raise PreventUpdate

    # Guard #3: проверка реального клика (КРИТИЧНО! см. ADR-003)
    if not ctx.triggered or ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    # Извлекаем дату
    selected_date = triggered_id.get("date")
    if not selected_date:
        raise PreventUpdate

    logger.debug(f"Открыт модал создания из календаря: {selected_date}")
    return True, selected_date


@callback(
    [
        Output("calendar-grid", "children", allow_duplicate=True),
        Output("calendar-stats", "children", allow_duplicate=True),
    ],
    [
        Input("create-submit-btn", "n_clicks"),
        Input("edit-submit-btn", "n_clicks"),
        Input({"type": "delete-btn", "index": ALL}, "n_clicks"),
    ],
    [State("calendar-state", "data")],
    prevent_initial_call=True,
)
def refresh_calendar_after_transaction(
    create_clicks: int | None,
    edit_clicks: int | None,
    delete_clicks_list: list[int | None],
    state: dict,
):
    """Обновляет календарь после создания/изменения/удаления операции.

    Args:
        create_clicks: Клики на "Создать" в модале
        edit_clicks: Клики на "Сохранить" в модале редактирования
        delete_clicks_list: Клики на кнопки удаления
        state: Текущее состояние календаря

    Returns:
        tuple: (grid, stats)
    """
    triggered_id = ctx.triggered_id

    # Guard #1: должен быть триггер
    if not triggered_id:
        raise PreventUpdate

    # Guard #2: проверка реального действия
    if not ctx.triggered or ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    # Проверяем что это действительно CRUD операция
    is_create = triggered_id == "create-submit-btn" and create_clicks
    is_edit = triggered_id == "edit-submit-btn" and edit_clicks
    is_delete = isinstance(triggered_id, dict) and triggered_id.get("type") == "delete-btn"

    if not (is_create or is_edit or is_delete):
        raise PreventUpdate

    # Получаем текущий месяц из state
    current_month = state.get("current_month")
    current_year = state.get("current_year")

    if not current_month or not current_year:
        raise PreventUpdate

    try:
        with get_db_session() as session:
            service = CalendarService(session)

            # Определяем границы месяца
            _, last_day = calendar.monthrange(current_year, current_month)
            start_date = date(current_year, current_month, 1)
            end_date = date(current_year, current_month, last_day)

            # Пересчитываем данные
            summary = service.get_month_summary(user_id=1, year=current_year, month=current_month)
            balances = service.calculate_daily_balances(user_id=1, start_date=start_date, end_date=end_date)
            transactions = service.get_transactions_by_date(user_id=1, start_date=start_date, end_date=end_date)

            logger.debug(f"Календарь обновлен после CRUD операции")

            grid = _build_calendar_grid(current_month, current_year, balances, transactions)
            stats = _build_stats_cards(summary)

            return grid, stats

    except Exception as e:
        logger.error(f"Ошибка обновления календаря: {e}")
        raise PreventUpdate
```

## Модель данных

### MonthSummary TypedDict
```python
class MonthSummary(TypedDict):
    """Агрегированные данные месяца для статистических карточек."""

    total_income: Decimal      # Сумма всех доходов (без TRANSFER)
    total_expense: Decimal     # Сумма всех расходов (без TRANSFER)
    start_balance: Decimal     # Остаток на 1 число месяца
    end_balance: Decimal       # Остаток на последний день месяца
    month: int                 # Месяц (1-12)
    year: int                  # Год
```

### CalendarState (dcc.Store) - ОБНОВЛЕНО
```python
{
    "current_month": int,      # Текущий месяц (1-12)
    "current_year": int,       # Текущий год
    "balances": dict[str, str] # Сериализованные балансы: {"2026-01-15": "12345.67"}
}
```

**ВАЖНО**: Balances хранятся как `dict[str, str]` (ISO date -> Decimal string) для JSON-совместимости.

### Сериализация Decimal
```python
# Сохранение в Store
serialize_balances({date(2026, 1, 15): Decimal("12345.67")})
# -> {"2026-01-15": "12345.67"}

# Извлечение из Store
deserialize_balances({"2026-01-15": "12345.67"})
# -> {date(2026, 1, 15): Decimal("12345.67")}
```

## Обработка ошибок

### CalendarService Exceptions

```python
# ValueError для некорректного диапазона дат
if start_date > end_date:
    raise ValueError("start_date должен быть <= end_date")

# Fallback вместо исключения для отсутствующего User
user = self.session.get(User, user_id)
if not user:
    return Decimal("0")  # Fallback
```

### UI Error Handling с try/except

```python
try:
    with get_db_session() as session:
        service = CalendarService(session)
        # Загрузка данных...
except Exception as e:
    logger.error(f"Ошибка загрузки календаря: {e}")
    return (
        _build_calendar_header(current_month, current_year),
        _build_error_alert("Не удалось загрузить данные календаря."),
        html.Div(),  # Пустая сетка
        state  # Сохраняем текущий state
    )
```

### Guard Clauses Pattern (согласно ADR-003)

```python
# Полный паттерн для Pattern-Matching Callbacks
triggered_id = ctx.triggered_id

# Guard #1: проверка triggered_id существует
if not triggered_id:
    raise PreventUpdate

# Guard #2: проверка типа (для Pattern-Matching с dict ID)
if not isinstance(triggered_id, dict) or triggered_id.get("type") != "calendar-day":
    raise PreventUpdate

# Guard #3: КРИТИЧНО! Проверка реального клика vs автовызов при обновлении DOM
if not ctx.triggered or ctx.triggered[0].get("value") is None:
    raise PreventUpdate
```

## План реализации

### Шаг 1: CalendarService (Backend Logic)
**Время**: 2.5 часа

1. Создать `app/services/calendar_service.py`
2. Реализовать `_get_starting_balance()` с fallback
3. Реализовать `calculate_daily_balances()` с исключением TRANSFER
4. Реализовать `get_transactions_by_date()`
5. Реализовать `get_month_summary()`
6. Добавить `MonthSummary` TypedDict
7. Обновить `app/services/__init__.py`
8. Написать unit тесты

**Критерии готовности**:
- [x] TRANSFER транзакции исключены из расчетов
- [x] Fallback на Decimal('0') для отсутствующего User
- [x] Unit тесты проходят

### Шаг 2: Calendar UI Component + Сериализация
**Время**: 3.5 часа

1. Создать `app/components/calendar.py`
2. Реализовать утилиты сериализации:
   - `serialize_balances()`
   - `deserialize_balances()`
   - `serialize_transactions_for_store()`
3. Реализовать layout функции с локализацией
4. Создать `app/assets/calendar.css` с кастомными стилями
5. Добавить константы (MONTH_NAMES_RU, WARNING_BALANCE_THRESHOLD)

**Критерии готовности**:
- [x] Decimal сериализуется без потери точности
- [x] Месяцы отображаются на русском
- [x] Threshold для warning конфигурируемый

### Шаг 3: Dash Callbacks с Guard Clauses
**Время**: 2.5 часа

1. Реализовать `load_and_navigate_calendar()` с валидацией +-12 месяцев
2. Реализовать `open_create_modal_from_calendar()` с полными guard clauses
3. Реализовать `refresh_calendar_after_transaction()` с allow_duplicate=True

**Критерии готовности**:
- [x] Все 3 guard clauses присутствуют в Pattern-Matching callbacks
- [x] Валидация +-12 месяцев работает
- [x] Нет автовызовов при обновлении календаря

### Шаг 4: Интеграция с Transactions
**Время**: 1 час

1. Обновить `app/main.py` - роутинг `/calendar`
2. Минимальные изменения в `transactions.py` (если требуются)

**Критерии готовности**:
- [x] После CRUD операции календарь обновляется
- [x] Используется существующий create-modal
- [x] Нет конфликтов ID модалов

### Шаг 5: Тестирование и полировка UX
**Время**: 2 часа

1. Функциональное тестирование всех сценариев
2. Тестирование Pattern-Matching (нет автовызовов)
3. Тестирование сериализации Decimal
4. Тестирование навигации +-12 месяцев

**Критерии готовности**:
- [x] Все критерии приёмки из Brief выполнены
- [x] Нет регрессий в transactions.py
- [x] Производительность < 2 сек

### Шаг 6: Документация и Code Review
**Время**: 1 час

1. Обновить ROADMAP.md
2. Обновить feature_progress.md
3. Code review
4. Git commit

**Общее время реализации**: 12.5 часов (~1.5 дня разработки)

## Зависимости

### Новые библиотеки
```
python-dateutil  # Для relativedelta (может потребоваться добавить в requirements.txt)
```

**Примечание**: Проверить, установлен ли `python-dateutil`. Если нет - альтернатива через datetime.

### Обновления существующих файлов
- `app/main.py` - обновить роутинг (1 строка)
- `app/services/__init__.py` - добавить export CalendarService (1 строка)
- `requirements.txt` - добавить python-dateutil (если не установлен)

## Риски и mitigation

| Риск | Вероятность | Воздействие | Mitigation |
|------|-------------|-------------|------------|
| **Decimal сериализация** | Низкая (решено) | Высокое | Утилиты serialize/deserialize с str() |
| **Pattern-Matching автовызовы** | Низкая (решено) | Высокое | 3 guard clauses согласно ADR-003 |
| **starting_balance = None** | Низкая (решено) | Среднее | Fallback на Decimal('0') |
| **TRANSFER в расчетах** | Низкая (решено) | Среднее | Явное исключение в SQL фильтрах |
| **Конфликт ID модалов** | Низкая (решено) | Среднее | Используем существующий create-modal |
| **Производительность SQL** | Низкая | Среднее | SQL агрегация + индекс ix_transactions_user_date |
| **python-dateutil не установлен** | Средняя | Низкое | Fallback на datetime вычисления |

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🔴 BLOCKER-1: Decimal сериализация | Добавлены `serialize_balances()` / `deserialize_balances()` - хранение как `dict[str, str]` |
| 🟡 IMPORTANT-1: Pattern-Matching | Добавлены полные guard clauses: (1) triggered_id, (2) isinstance/type check, (3) ctx.triggered[0].get('value') is None |
| 🟡 IMPORTANT-2: refresh callback | Добавлена полная сигнатура с `allow_duplicate=True`, обработка create/edit/delete |
| 🟡 IMPORTANT-3: starting_balance | `_get_starting_balance()` возвращает Decimal('0') если User не найден |
| 🟡 IMPORTANT-4: TRANSFER | Явно исключается в `calculate_daily_balances()` и `get_month_summary()` через SQL фильтр |
| 🟢 MINOR-1: Локализация | Добавлен `MONTH_NAMES_RU` словарь, функция `format_month_header()` |
| 🟢 MINOR-2: Threshold | Добавлена константа `WARNING_BALANCE_THRESHOLD = Decimal('5000')` |
| 🟢 MINOR-3: Валидация +-12 | Добавлена в `load_and_navigate_calendar()` с `MAX_MONTHS_OFFSET = 12` |
| 🟢 MINOR-4: ID модалов | Используется существующий `create-modal` из transactions.py |

## Ответы на вопросы критика

1. **TRANSFER транзакции**: Исключаются из расчетов баланса, т.к. это внутренние переводы между счетами пользователя (не влияют на общий баланс). В UI календаря TRANSFER отображается как операция (для информации), но не учитывается в remaining balance и summary cards.

2. **Конфликт модалов**: Используется существующий `create-modal` из transactions.py. Callback `open_create_modal_from_calendar()` выводит в `Output("create-modal", "is_open", allow_duplicate=True)` и `Output("create-date-picker", "date", allow_duplicate=True)`. Конфликтов нет, т.к. оба компонента на разных страницах (URL routing).

3. **Мобильная версия**: Вне scope Фазы 3, откладывается на Batch 3. В текущей реализации используется адаптивный Bootstrap Grid для desktop (1024px+). На мобильных устройствах календарь будет масштабироваться, но специальный mobile-first layout не реализуется.

4. **Предзаполнение формы**: При клике по дню ВСЕГДА открывается модал создания операции с предзаполненной датой. Даже если на дне есть существующие операции - пользователь может добавить ещё одну. Для редактирования существующих операций используется страница Transactions. Это соответствует Brief: "Минимум кликов для добавления операции (1 клик по дате -> форма с предзаполненной датой)".

## Критические файлы для реализации

| Файл | Статус | Описание |
|------|--------|----------|
| `app/services/calendar_service.py` | **НОВЫЙ** | Ядро бизнес-логики: расчет остатков с исключением TRANSFER, fallback для starting_balance |
| `app/components/calendar.py` | **НОВЫЙ** | UI календаря: сериализация Decimal, callbacks с guard clauses, локализация |
| `app/assets/calendar.css` | **НОВЫЙ** | Стили календаря |
| `app/main.py` | Модифицировать | Роутинг `/calendar` → `create_calendar_layout()` |
| `app/services/__init__.py` | Модифицировать | Добавить export CalendarService |
| `app/components/transactions.py` | Справка | Pattern guard clauses для копирования |
