# Solution v1: Goals UI Component с CRUD операциями

## Обзор решения
Создать UI компонент `goals.py` по образцу `transactions.py`, использующий существующий GoalService для CRUD операций. Компонент будет отображать карточку активной цели с прогресс-баром, рекомендованным взносом и историей contributions. Модальные формы обеспечат создание цели, добавление взносов и редактирование. Применяется ADR-003 pattern для guard clauses в callbacks.

## Архитектура

### Компоненты
1. **goals.py** (~600-800 строк) - UI компонент с layout и callbacks
2. **goals.css** (~100-150 строк) - стили для прогресс-бара и карточек
3. **GoalService** - существующий, возможно расширение для истории contributions
4. **main.py** - обновление роутинга /goals

### Диаграмма взаимодействия
```
┌─────────────────────────────────────────────────────────────────┐
│                         goals.py                                 │
├─────────────────────────────────────────────────────────────────┤
│  Layout:                                                        │
│  ┌─────────────────────────────────────────────────────────────┤
│  │ create_goals_layout()                                        │
│  │   ├── Goal Card (active goal or empty state)                │
│  │   │   ├── Progress Bar                                      │
│  │   │   ├── Monthly Contribution Recommendation               │
│  │   │   └── Action Buttons (Edit, Pause, Delete)              │
│  │   ├── Contributions History Table                           │
│  │   ├── Create Goal Modal                                     │
│  │   ├── Add Contribution Modal                                │
│  │   ├── Edit Goal Modal                                       │
│  │   └── dcc.Store (goal-id, refresh-trigger)                  │
│  └─────────────────────────────────────────────────────────────┤
│  Callbacks:                                                     │
│  ├── load_goal_data() - Input: url.pathname                    │
│  ├── toggle_create_goal_modal() - prevent_initial_call=True    │
│  ├── create_goal() - создание цели                             │
│  ├── toggle_contribution_modal() - prevent_initial_call=True   │
│  ├── add_contribution() - внесение взноса                      │
│  ├── open_edit_modal() - Pattern-Matching с guard clause       │
│  ├── update_goal() - сохранение изменений                      │
│  ├── delete_goal() - удаление с подтверждением                 │
│  └── toggle_goal_status() - ACTIVE ↔ PAUSED                    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GoalService (existing)                       │
├─────────────────────────────────────────────────────────────────┤
│  ✅ create_goal(user_id, name, target_amount, target_date)     │
│  ✅ add_contribution(goal_id, amount, date, description)       │
│  ✅ get_by_id(goal_id)                                          │
│  ✅ get_all_by_user(user_id, status=None)                      │
│  ✅ update_goal(goal_id, name, target_amount, target_date, st) │
│  ✅ delete_goal(goal_id)                                        │
│  ➕ get_contributions(goal_id, limit=10) - НОВЫЙ МЕТОД         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SQLAlchemy Models                          │
├─────────────────────────────────────────────────────────────────┤
│  Goal                          GoalContribution                 │
│  ├── id                        ├── id                          │
│  ├── name                      ├── goal_id                     │
│  ├── target_amount             ├── amount                      │
│  ├── current_amount            ├── contribution_date           │
│  ├── target_date               ├── description                 │
│  ├── status                    └── created_at                  │
│  ├── priority                                                   │
│  ├── progress_percentage @prop                                  │
│  ├── is_completed @prop                                         │
│  └── monthly_contribution @prop                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Файловая структура
```
app/
├── components/
│   ├── __init__.py           # + export create_goals_layout
│   ├── goals.py              # НОВЫЙ: ~600-800 строк
│   └── ...
├── services/
│   ├── goal_service.py       # + get_contributions() метод
│   └── __init__.py           # (без изменений)
├── assets/
│   └── goals.css             # НОВЫЙ: ~100-150 строк
└── main.py                   # обновить роутинг /goals

tests/
└── test_goal_service.py      # НОВЫЙ: ~100-150 строк
```

## Ключевые интерфейсы

```python
# app/components/goals.py

from datetime import date
from decimal import Decimal
from typing import TypedDict

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ctx, no_update
from dash.exceptions import PreventUpdate
from loguru import logger

from app.core import get_db_session, ValidationError
from app.models.database import GoalStatus
from app.services import GoalService


class GoalDisplayData(TypedDict):
    """Данные для отображения цели в UI."""
    id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date
    status: str
    progress_percentage: float
    monthly_contribution: Decimal
    days_remaining: int


class ContributionDisplayData(TypedDict):
    """Данные для отображения взноса в истории."""
    id: int
    amount: Decimal
    contribution_date: str  # форматированная дата
    description: str | None


def create_goals_layout() -> html.Div:
    """Создает layout страницы накопительных целей.

    Returns:
        html.Div с полным layout страницы Goals
    """
    ...


def _build_goal_card(goal_data: GoalDisplayData | None) -> dbc.Card:
    """Создает карточку активной цели или empty state.

    Args:
        goal_data: Данные цели или None если нет активной

    Returns:
        dbc.Card с информацией о цели
    """
    ...


def _build_progress_bar(progress: float, current: Decimal, target: Decimal) -> html.Div:
    """Создает прогресс-бар с подписями.

    Args:
        progress: Процент выполнения (0-100)
        current: Текущая накопленная сумма
        target: Целевая сумма

    Returns:
        html.Div с Bootstrap Progress
    """
    ...


def _build_contributions_table(contributions: list[ContributionDisplayData]) -> dbc.Table:
    """Создает таблицу истории взносов.

    Args:
        contributions: Список взносов для отображения

    Returns:
        dbc.Table с историей
    """
    ...


# --- Callbacks ---

@callback(
    Output("goal-card-container", "children"),
    Output("contributions-table-container", "children"),
    Input("url", "pathname"),
)
def load_goal_data(pathname: str):
    """Загружает данные активной цели и историю взносов.

    Args:
        pathname: Текущий URL

    Returns:
        Tuple[goal_card, contributions_table]
    """
    # Guard: только для /goals
    if pathname != "/goals":
        raise PreventUpdate
    ...


@callback(
    Output("create-goal-modal", "is_open"),
    [
        Input("create-goal-btn", "n_clicks"),
        Input("create-goal-cancel-btn", "n_clicks"),
    ],
    State("create-goal-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_create_goal_modal(create_clicks, cancel_clicks, is_open):
    """Открывает/закрывает модал создания цели."""
    ...


@callback(
    [
        Output("create-goal-modal", "is_open", allow_duplicate=True),
        Output("goal-card-container", "children", allow_duplicate=True),
        # ... reset form fields
        Output("goal-error-alert", "children", allow_duplicate=True),
        Output("goal-error-alert", "is_open", allow_duplicate=True),
    ],
    Input("create-goal-submit-btn", "n_clicks"),
    [
        State("create-goal-name-input", "value"),
        State("create-goal-amount-input", "value"),
        State("create-goal-date-picker", "date"),
    ],
    prevent_initial_call=True,
)
def create_goal(n_clicks, name, target_amount, target_date_str):
    """Создает новую накопительную цель."""
    ...


@callback(
    Output("add-contribution-modal", "is_open"),
    [
        Input("add-contribution-btn", "n_clicks"),
        Input("add-contribution-cancel-btn", "n_clicks"),
    ],
    State("add-contribution-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_contribution_modal(add_clicks, cancel_clicks, is_open):
    """Открывает/закрывает модал добавления взноса."""
    ...


@callback(
    [
        Output("add-contribution-modal", "is_open", allow_duplicate=True),
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("contributions-table-container", "children", allow_duplicate=True),
        # ... reset form fields
        Output("goal-error-alert", "children", allow_duplicate=True),
        Output("goal-error-alert", "is_open", allow_duplicate=True),
    ],
    Input("add-contribution-submit-btn", "n_clicks"),
    [
        State("current-goal-id", "data"),
        State("add-contribution-amount-input", "value"),
        State("add-contribution-date-picker", "date"),
        State("add-contribution-description-input", "value"),
    ],
    prevent_initial_call=True,
)
def add_contribution(n_clicks, goal_id, amount, date_str, description):
    """Добавляет взнос в активную цель."""
    ...


# app/services/goal_service.py - расширение

def get_contributions(
    self,
    goal_id: int,
    limit: int = 10,
) -> list[GoalContribution]:
    """Получает список взносов цели отсортированный по дате DESC.

    Args:
        goal_id: ID цели
        limit: Максимальное количество записей

    Returns:
        list[GoalContribution]: Последние взносы
    """
    return (
        self.session.query(GoalContribution)
        .filter_by(goal_id=goal_id)
        .order_by(GoalContribution.contribution_date.desc())
        .limit(limit)
        .all()
    )
```

## Модель данных

### UI State (dcc.Store)
```python
# goal-store: хранит ID активной цели для callbacks
{
    "goal_id": int | None
}

# Альтернатива: использовать State напрямую из БД каждый раз
```

### Форматирование для UI
```python
def format_amount(amount: Decimal) -> str:
    """15000.00 -> '15 000.00 ₽'"""
    return f"{amount:,.2f} ₽".replace(",", " ")

def format_date(date_obj: date) -> str:
    """2026-06-15 -> '15.06.2026'"""
    return date_obj.strftime("%d.%m.%Y")

def format_days_remaining(days: int) -> str:
    """Форматирует оставшиеся дни с правильным склонением."""
    if days <= 0:
        return "Срок истёк"
    if days == 1:
        return "1 день"
    if days < 5:
        return f"{days} дня"
    return f"{days} дней"
```

## Обработка ошибок

### Стратегия
1. **ValidationError от GoalService** - показать в Alert с `is_open=True`
2. **Goal not found** - показать empty state с кнопкой "Создать цель"
3. **DB errors** - логировать через loguru, показать generic Alert
4. **Pattern-Matching callback без клика** - `raise PreventUpdate` (ADR-003)

### Guard Clauses Pattern (обязательно)
```python
@callback(...)
def some_pattern_matching_callback(n_clicks_list):
    """Callback с Pattern-Matching Input."""
    triggered_id = ctx.triggered_id

    # Guard #1: проверка triggered_id
    if not triggered_id:
        raise PreventUpdate

    # Guard #2: проверка типа (для Pattern-Matching)
    if not isinstance(triggered_id, dict) or triggered_id.get("type") != "expected-type":
        raise PreventUpdate

    # Guard #3: проверка реального клика (ADR-003 КРИТИЧНО!)
    if not ctx.triggered or ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    # Теперь безопасно извлекать index
    item_id = triggered_id.get("index")
    ...
```

## План реализации

### Фаза 1: GoalService Extension (~30 мин)
1. Добавить метод `get_contributions(goal_id, limit)` в `goal_service.py`
2. Обновить `__init__.py` с экспортом (если нужно)
3. Написать unit тесты для нового метода

### Фаза 2: Goals Layout (~2 часа)
1. Создать `goals.py` со структурой layout
2. Реализовать `create_goals_layout()` с:
   - Goal Card container
   - Empty state (нет активной цели)
   - Contributions table container
   - Create Goal Modal
   - Add Contribution Modal
   - Edit Goal Modal
   - Alert для ошибок
   - dcc.Store для goal_id

### Фаза 3: Goals Callbacks (~2 часа)
1. `load_goal_data()` - загрузка при переходе на /goals
2. `toggle_create_goal_modal()` + `create_goal()`
3. `toggle_contribution_modal()` + `add_contribution()`
4. `toggle_edit_modal()` + `update_goal()`
5. `delete_goal()` с confirm dialog

### Фаза 4: Стили и интеграция (~1 час)
1. Создать `goals.css` с:
   - Progress bar styling
   - Goal card styling
   - Empty state styling
2. Обновить `main.py` роутинг
3. Обновить `components/__init__.py`

### Фаза 5: Тестирование и QA (~1 час)
1. Ручное тестирование всех flows
2. Проверка guard clauses (нет автосрабатываний)
3. black + flake8
4. pytest (все 33+ тестов)

**Общая оценка: 6-8 часов**

## Зависимости

### Существующие (не требуют установки)
- dash, dash-bootstrap-components, plotly
- sqlalchemy, loguru
- pytest (для тестов)

### Новые библиотеки
- Не требуются

## Риски и mitigation

| Риск | Вероятность | Impact | Mitigation |
|------|-------------|--------|------------|
| Pattern-Matching callback регрессии | Средняя | Высокий | Строго следовать ADR-003 guard clauses pattern из transactions.py |
| Сложность UI состояния | Низкая | Средний | Использовать dcc.Store для goal_id, минимизировать state |
| Конфликт стилей | Низкая | Низкий | Изолировать стили в goals.css с уникальными классами |
| ValidationError не отображается | Низкая | Средний | Тестировать edge cases: пустые поля, прошедшие даты |
| monthly_contribution = 0 при дедлайне | Низкая | Низкий | UI отображает "Срок истёк" вместо 0 |
