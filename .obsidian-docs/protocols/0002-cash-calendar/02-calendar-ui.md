# Шаг 2: Calendar UI — Компоненты и стили

## Briefing
- **Цель:** Создать UI компоненты календаря (layout, сетка, ячейки дней) и CSS стили. Без callbacks — только статические компоненты.
- **Ключевые файлы:**
  - `app/components/calendar.py` (создать)
  - `app/assets/calendar.css` (создать)
- **Additional info:**
  - Decimal нельзя сериализовать в JSON → использовать `serialize_balances()` / `deserialize_balances()`
  - Локализация месяцев на русском через `MONTH_NAMES_RU`
  - Порог предупреждения `WARNING_BALANCE_THRESHOLD = Decimal('5000')`
  - Цвета: зеленый (положительный), красный (отрицательный), желтый (< 5000)

## Sub-tasks

### 1. Создать константы и утилиты

В начале файла `app/components/calendar.py`:

```python
"""UI компонент кассового календаря."""

import calendar
from datetime import date
from decimal import Decimal
from typing import Any

import dash_bootstrap_components as dbc
from dash import html, dcc

from app.models.database import TransactionType


# ==================== КОНСТАНТЫ ====================

MONTH_NAMES_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}

WEEKDAY_NAMES_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

WARNING_BALANCE_THRESHOLD = Decimal("5000")
MAX_MONTHS_OFFSET = 12
```

### 2. Реализовать утилиты сериализации

```python
def serialize_balances(balances: dict[date, Decimal]) -> dict[str, str]:
    """Сериализует балансы для хранения в dcc.Store.

    Decimal не сериализуется в JSON, поэтому конвертируем в строки.

    Args:
        balances: {date: Decimal}

    Returns:
        dict[str, str]: {"YYYY-MM-DD": "12345.67", ...}
    """
    return {dt.isoformat(): str(balance) for dt, balance in balances.items()}


def deserialize_balances(data: dict[str, str] | None) -> dict[date, Decimal]:
    """Десериализует балансы из dcc.Store.

    Args:
        data: {"YYYY-MM-DD": "12345.67", ...} или None

    Returns:
        dict[date, Decimal]: {date: Decimal}
    """
    if not data:
        return {}
    return {
        date.fromisoformat(dt_str): Decimal(balance_str)
        for dt_str, balance_str in data.items()
    }
```

### 3. Реализовать функции форматирования

```python
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
```

### 4. Создать главный layout

```python
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
                    "balances": {},
                },
            ),
            # Заголовок с навигацией
            html.Div(id="calendar-header"),
            # Карточки статистики
            html.Div(id="calendar-stats", className="mb-4"),
            # Календарная сетка
            html.Div(id="calendar-grid"),
        ],
        className="calendar-container",
    )
```

### 5. Реализовать компонент заголовка

```python
def build_calendar_header(month: int, year: int) -> html.Div:
    """Создает заголовок календаря с навигацией.

    Args:
        month: Текущий месяц (1-12)
        year: Текущий год

    Returns:
        html.Div: Заголовок с кнопками навигации
    """
    # Логика определения disabled для кнопок (+-12 месяцев)
    # Кнопки: prev-month-btn, next-month-btn, today-btn
```

**Компоненты:**
- Кнопка `<` (id=`prev-month-btn`)
- Заголовок "Январь 2026" (минимальная ширина 180px)
- Кнопка `>` (id=`next-month-btn`)
- Кнопка "Сегодня" (id=`today-btn`)

### 6. Реализовать карточки статистики

```python
def build_stats_cards(summary: dict) -> html.Div:
    """Создает карточки статистики над календарем.

    Args:
        summary: MonthSummary dict

    Returns:
        dbc.Row: Три карточки (Доходы, Расходы, Баланс)
    """
```

**Карточки:**
1. Доходы (зеленый, +сумма)
2. Расходы (красный, -сумма)
3. Баланс (зеленый/красный в зависимости от знака)

### 7. Реализовать календарную сетку

```python
def build_calendar_grid(
    month: int,
    year: int,
    balances: dict[date, Decimal],
    transactions: dict[date, list],
) -> html.Div:
    """Создает календарную сетку с днями.

    Args:
        month: Месяц (1-12)
        year: Год
        balances: {date: Decimal}
        transactions: {date: [Transaction, ...]}

    Returns:
        html.Div: Сетка календаря
    """
```

**Структура:**
- Заголовок дней недели (Пн-Вс)
- 4-6 строк недель
- Ячейки дней через `_build_day_cell()`

### 8. Реализовать ячейку дня

```python
def build_day_cell(
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
```

**Элементы ячейки:**
- Номер дня
- Иконки транзакций (↓ доход, ↑ расход)
- Баланс с цветом
- ID для Pattern-Matching: `{"type": "calendar-day", "date": "2026-01-15"}`
- Атрибут `n_clicks=0` для обработки кликов

### 9. Создать CSS стили

Создать файл `app/assets/calendar.css`:

```css
/* Контейнер календаря */
.calendar-container {
    padding: 20px;
}

/* Сетка календаря */
.calendar-grid {
    border: 1px solid #dee2e6;
    border-radius: 8px;
    overflow: hidden;
}

/* Ячейка дня */
.calendar-day {
    width: 14.28%;  /* 100% / 7 */
    min-height: 80px;
    padding: 8px;
    border: 1px solid #dee2e6;
    cursor: pointer;
    transition: background-color 0.2s;
}

.calendar-day:hover {
    background-color: #f8f9fa;
}

/* Сегодняшний день */
.calendar-day-today {
    background-color: #e8f5e9;
    border: 2px solid #4caf50;
}

/* День другого месяца */
.calendar-day-other-month {
    opacity: 0.4;
}

/* Выходной */
.calendar-day-weekend {
    background-color: #fafafa;
}

/* Номер дня */
.calendar-day-number {
    font-weight: bold;
    font-size: 14px;
}

/* Баланс */
.calendar-day-balance {
    font-size: 12px;
    margin-top: 4px;
}

.balance-positive {
    color: #28a745;
}

.balance-negative {
    color: #dc3545;
}

.balance-warning {
    color: #ffc107;
}

/* Иконки транзакций */
.calendar-day-icons {
    font-size: 12px;
    margin-top: 2px;
}

/* Заголовок дней недели */
.calendar-weekday {
    font-weight: 600;
    padding: 8px;
}
```

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно создай:
   - Константы и утилиты в `app/components/calendar.py`
   - Функции форматирования
   - Layout функции
   - CSS стили в `app/assets/calendar.css`

2. **Верификация:**
   ```bash
   black app/components/calendar.py
   flake8 app/components/calendar.py
   ```
   На этом шаге pytest не требуется (UI компоненты).

3. **Фиксация:**
   - Добавь запись в `log.md`
   - Обнови `context.md`: `Current Step` → `3`
   - Проверь main

4. **Коммит:**
   ```bash
   git add .
   git commit -m "feat(calendar): add calendar UI components and CSS [protocol-0002/02]"
   git push
   ```

5. **Отчет пользователю.**

<формат_отчёта_о_шаге>
(Протокол 0002, шаг 2):

**Сделано**: список изменений.

**Проверки**: black, flake8 — результаты.

**Git**: PR, ветка, коммит, main чистая.

**Рабочая папка**: /home/skytiger/PycharmProjects/worktrees/0002-cash-calendar

**Статус протокола**: Шаг 2 завершен, следующий — Шаг 3 (Callbacks).
</формат_отчёта_о_шаге>
