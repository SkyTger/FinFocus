# Solution v2: Goals UI Component с Simple Callbacks и Confirm Dialog

## Обзор решения
UI компонент `goals.py` для управления одной накопительной целью в MVP. Ключевое отличие от v1: явное использование **простых callbacks без Pattern-Matching** (одна цель = один ID в dcc.Store), детализированный Confirm Dialog через `dcc.ConfirmDialog`, и вынос format-функций в отдельный модуль `app/utils/formatters.py` для DRY. Все callbacks используют `prevent_initial_call=True` без необходимости в ADR-003 guard clauses для Pattern-Matching.

## Архитектура

### Компоненты
1. **goals.py** (~550-650 строк) - UI компонент с layout и простыми callbacks
2. **goals.css** (~120-150 строк) - стили для прогресс-бара, карточек, empty state
3. **formatters.py** (~60 строк) - общие функции форматирования (вынесено из transactions.py)
4. **GoalService** - существующий сервис + новый метод `get_contributions()`
5. **main.py** - обновление роутинга /goals

### Диаграмма взаимодействия
```
┌─────────────────────────────────────────────────────────────────────────┐
│                              goals.py                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  Layout:                                                                 │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ create_goals_layout()                                              │  │
│  │   ├── Goal Card Container                                          │  │
│  │   │   ├── Empty State (нет активной цели)                         │  │
│  │   │   └── Goal Card (активная цель)                                │  │
│  │   │       ├── Progress Bar (визуальный + проценты)                │  │
│  │   │       ├── Metrics Row (текущая/целевая/рекомендуемый взнос)   │  │
│  │   │       ├── Days Remaining Badge                                 │  │
│  │   │       └── Action Buttons (Edit | Pause | Delete)              │  │
│  │   ├── Contributions History Card                                   │  │
│  │   │   ├── Add Contribution Button                                  │  │
│  │   │   └── Table/Empty State                                        │  │
│  │   ├── Create Goal Modal                                            │  │
│  │   ├── Add Contribution Modal                                       │  │
│  │   ├── Edit Goal Modal                                              │  │
│  │   ├── dcc.ConfirmDialog (delete confirmation)                      │  │
│  │   ├── dbc.Alert (error display)                                    │  │
│  │   └── dcc.Store (current-goal-id)                                  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  Callbacks (ВСЕ с prevent_initial_call=True):                           │
│  ├── load_goal_data() - pathname → load active goal + contributions    │
│  ├── toggle_create_goal_modal() - simple toggle                        │
│  ├── create_goal() - submit → GoalService.create_goal()                │
│  ├── toggle_contribution_modal() - simple toggle                       │
│  ├── add_contribution() - submit → GoalService.add_contribution()      │
│  ├── toggle_edit_modal() - simple toggle, load goal data to form       │
│  ├── update_goal() - submit → GoalService.update_goal()                │
│  ├── request_delete_goal() - click → open ConfirmDialog                │
│  ├── confirm_delete_goal() - confirm → GoalService.delete_goal()       │
│  └── toggle_goal_status() - click → GoalService.update_goal(status)    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         formatters.py (NEW)                              │
├─────────────────────────────────────────────────────────────────────────┤
│  format_amount(Decimal) → "15 000.00 ₽"                                 │
│  format_date(date) → "15.06.2026"                                       │
│  format_days_remaining(int) → "15 дней" / "1 день" / "Срок истёк"       │
│  parse_date_safe(str) → date | None                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    GoalService (existing + extension)                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ✅ create_goal(user_id, name, target_amount, target_date)              │
│  ✅ add_contribution(goal_id, amount, date, description)                │
│  ✅ get_by_id(goal_id) → Goal | None                                    │
│  ✅ get_all_by_user(user_id, status=None) → list[Goal]                  │
│  ✅ update_goal(goal_id, name, target_amount, target_date, status)      │
│  ✅ delete_goal(goal_id) → bool                                         │
│  ➕ get_contributions(goal_id, limit=10) → list[GoalContribution] NEW   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Файловая структура
```
app/
├── components/
│   ├── __init__.py           # + export create_goals_layout
│   ├── goals.py              # НОВЫЙ: ~550-650 строк
│   └── transactions.py       # - remove format_amount, format_date → import from utils
├── services/
│   ├── goal_service.py       # + get_contributions() метод (~15 строк)
│   └── __init__.py           # (без изменений)
├── utils/
│   ├── __init__.py           # НОВЫЙ: export formatters
│   └── formatters.py         # НОВЫЙ: ~60 строк (общие функции)
├── assets/
│   └── goals.css             # НОВЫЙ: ~120-150 строк
└── main.py                   # обновить роутинг /goals

tests/
└── test_goal_service.py      # НОВЫЙ: ~80-100 строк (для get_contributions)
```

## Ключевые интерфейсы

```python
# app/utils/formatters.py

from datetime import date
from decimal import Decimal

def format_amount(amount: Decimal) -> str:
    """Форматирует сумму для отображения.

    Args:
        amount: Сумма операции

    Returns:
        str: Отформатированная строка (например, "15 000.00 ₽")
    """
    return f"{amount:,.2f} ₽".replace(",", " ")


def format_date(date_obj: date) -> str:
    """Форматирует дату для отображения.

    Args:
        date_obj: Объект даты

    Returns:
        str: Дата в формате DD.MM.YYYY
    """
    return date_obj.strftime("%d.%m.%Y")


def format_days_remaining(days: int) -> str:
    """Форматирует оставшиеся дни с правильным склонением.

    Args:
        days: Количество оставшихся дней

    Returns:
        str: Строка с правильным склонением ("1 день", "2 дня", "5 дней")
    """
    if days <= 0:
        return "Срок истёк"

    # Склонение для русского языка
    last_digit = days % 10
    last_two_digits = days % 100

    if last_two_digits >= 11 and last_two_digits <= 14:
        return f"{days} дней"
    elif last_digit == 1:
        return f"{days} день"
    elif last_digit >= 2 and last_digit <= 4:
        return f"{days} дня"
    else:
        return f"{days} дней"


def parse_date_safe(date_str: str | None) -> date | None:
    """Безопасно парсит строку даты.

    Args:
        date_str: Дата в формате YYYY-MM-DD или None

    Returns:
        date | None: Объект date или None при ошибке
    """
    if not date_str:
        return None
    try:
        from datetime import datetime
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
```

```python
# app/components/goals.py

from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ctx, no_update
from dash.exceptions import PreventUpdate
from loguru import logger

from app.core import get_db_session, ValidationError
from app.models.database import GoalStatus
from app.services import GoalService
from app.utils.formatters import format_amount, format_date, format_days_remaining, parse_date_safe


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
    is_completed: bool


class ContributionDisplayData(TypedDict):
    """Данные для отображения взноса в истории."""
    id: int
    amount: Decimal
    contribution_date: date
    description: str | None


def create_goals_layout() -> html.Div:
    """Создает layout страницы накопительных целей.

    Returns:
        html.Div: Полный layout страницы Goals
    """
    ...


def _build_goal_card(goal_data: GoalDisplayData | None) -> dbc.Card:
    """Создает карточку активной цели или empty state.

    Args:
        goal_data: Данные цели или None если нет активной

    Returns:
        dbc.Card: Карточка с информацией о цели или empty state
    """
    if goal_data is None:
        return _build_empty_state()
    ...


def _build_empty_state() -> dbc.Card:
    """Создает empty state карточку когда нет активной цели.

    Returns:
        dbc.Card: Карточка с призывом создать цель
    """
    ...


def _build_progress_bar(progress: float, current: Decimal, target: Decimal) -> html.Div:
    """Создает прогресс-бар с подписями.

    Args:
        progress: Процент выполнения (0-100)
        current: Текущая накопленная сумма
        target: Целевая сумма

    Returns:
        html.Div: Bootstrap Progress с подписями
    """
    ...


def _build_contributions_table(contributions: list[ContributionDisplayData]) -> html.Div:
    """Создает таблицу истории взносов или empty state.

    Args:
        contributions: Список взносов для отображения

    Returns:
        html.Div: Таблица или empty state с мотивирующим текстом
    """
    ...


def _build_action_buttons(goal_data: GoalDisplayData) -> dbc.ButtonGroup:
    """Создает группу кнопок действий над целью.

    Args:
        goal_data: Данные цели для определения доступных действий

    Returns:
        dbc.ButtonGroup: Кнопки Edit, Pause/Resume, Delete

    Note:
        - Кнопка "Добавить взнос" скрыта для COMPLETED/PAUSED целей
        - Кнопка "Возобновить" показывается только для PAUSED целей
    """
    ...


def _goal_to_display_data(goal) -> GoalDisplayData:
    """Конвертирует ORM Goal в GoalDisplayData для UI.

    Args:
        goal: SQLAlchemy Goal объект

    Returns:
        GoalDisplayData: TypedDict с данными для отображения
    """
    days_remaining = (goal.target_date - date.today()).days
    return GoalDisplayData(
        id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        status=goal.status.value,
        progress_percentage=goal.progress_percentage,
        monthly_contribution=goal.monthly_contribution,
        days_remaining=days_remaining,
        is_completed=goal.is_completed,
    )


# --- Callbacks (все с prevent_initial_call=True) ---

@callback(
    [
        Output("goal-card-container", "children"),
        Output("contributions-table-container", "children"),
        Output("current-goal-id", "data"),
    ],
    Input("url", "pathname"),
)
def load_goal_data(pathname: str):
    """Загружает данные активной цели и историю взносов.

    Callback срабатывает при переходе на /goals.
    Если нет активной цели, показывает empty state.

    Args:
        pathname: Текущий URL

    Returns:
        Tuple[goal_card, contributions_table, goal_id]
    """
    if pathname != "/goals":
        raise PreventUpdate

    with get_db_session() as session:
        service = GoalService(session)
        # Получаем активную цель пользователя
        goals = service.get_all_by_user(user_id=1, status=GoalStatus.ACTIVE)

        if not goals:
            # Empty state - нет активной цели
            return _build_empty_state(), _build_contributions_table([]), None

        goal = goals[0]  # MVP: одна активная цель
        goal_data = _goal_to_display_data(goal)

        # Получаем историю взносов
        contributions = service.get_contributions(goal.id, limit=10)
        contrib_data = [
            ContributionDisplayData(
                id=c.id,
                amount=c.amount,
                contribution_date=c.contribution_date,
                description=c.description,
            )
            for c in contributions
        ]

        return (
            _build_goal_card(goal_data),
            _build_contributions_table(contrib_data),
            goal.id,
        )


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
    """Открывает/закрывает модал создания цели.

    Simple callback без Pattern-Matching - guard clauses из ADR-003 не нужны.
    """
    triggered_id = ctx.triggered_id
    if triggered_id == "create-goal-btn":
        return True
    if triggered_id == "create-goal-cancel-btn":
        return False
    return is_open


@callback(
    [
        Output("create-goal-modal", "is_open", allow_duplicate=True),
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("contributions-table-container", "children", allow_duplicate=True),
        Output("current-goal-id", "data", allow_duplicate=True),
        Output("create-goal-name-input", "value"),
        Output("create-goal-amount-input", "value"),
        Output("create-goal-date-picker", "date"),
        Output("goal-error-alert", "children"),
        Output("goal-error-alert", "is_open"),
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
    if not n_clicks or not name or not target_amount:
        raise PreventUpdate

    # Парсим дату
    target_date = parse_date_safe(target_date_str)
    if not target_date:
        return True, no_update, no_update, no_update, no_update, no_update, no_update, "Укажите дату достижения цели", True

    try:
        with get_db_session() as session:
            service = GoalService(session)
            goal = service.create_goal(
                user_id=1,
                name=name.strip(),
                target_amount=Decimal(str(target_amount)),
                target_date=target_date,
            )

            goal_data = _goal_to_display_data(goal)

            logger.info(f"Создана цель: {goal.name} ({goal.id})")

            # Успех: закрываем модал, очищаем форму, обновляем карточку
            min_date = (date.today() + timedelta(days=7)).isoformat()
            return (
                False,  # close modal
                _build_goal_card(goal_data),
                _build_contributions_table([]),  # нет взносов
                goal.id,
                "",  # clear name
                None,  # clear amount
                min_date,  # reset date
                "",
                False,
            )
    except ValidationError as e:
        logger.warning(f"Ошибка создания цели: {e}")
        return True, no_update, no_update, no_update, no_update, no_update, no_update, str(e), True


@callback(
    Output("edit-goal-modal", "is_open"),
    Output("edit-goal-name-input", "value"),
    Output("edit-goal-amount-input", "value"),
    Output("edit-goal-date-picker", "date"),
    [
        Input("edit-goal-btn", "n_clicks"),
        Input("edit-goal-cancel-btn", "n_clicks"),
    ],
    State("current-goal-id", "data"),
    State("edit-goal-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_edit_modal(edit_clicks, cancel_clicks, goal_id, is_open):
    """Открывает/закрывает модал редактирования с загрузкой данных.

    Simple callback - goal_id берем из dcc.Store, не нужен Pattern-Matching.
    При открытии загружаем актуальные данные цели из БД.
    """
    triggered_id = ctx.triggered_id

    if triggered_id == "edit-goal-cancel-btn":
        return False, no_update, no_update, no_update

    if triggered_id == "edit-goal-btn":
        if not goal_id:
            raise PreventUpdate

        with get_db_session() as session:
            service = GoalService(session)
            goal = service.get_by_id(goal_id)

            if not goal:
                raise PreventUpdate

            return (
                True,
                goal.name,
                float(goal.target_amount),
                goal.target_date.isoformat(),
            )

    raise PreventUpdate


@callback(
    [
        Output("edit-goal-modal", "is_open", allow_duplicate=True),
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("goal-error-alert", "children", allow_duplicate=True),
        Output("goal-error-alert", "is_open", allow_duplicate=True),
    ],
    Input("edit-goal-submit-btn", "n_clicks"),
    [
        State("current-goal-id", "data"),
        State("edit-goal-name-input", "value"),
        State("edit-goal-amount-input", "value"),
        State("edit-goal-date-picker", "date"),
    ],
    prevent_initial_call=True,
)
def update_goal(n_clicks, goal_id, name, target_amount, target_date_str):
    """Обновляет параметры цели."""
    if not n_clicks or not goal_id:
        raise PreventUpdate

    target_date = parse_date_safe(target_date_str)

    try:
        with get_db_session() as session:
            service = GoalService(session)
            goal = service.update_goal(
                goal_id=goal_id,
                name=name.strip() if name else None,
                target_amount=Decimal(str(target_amount)) if target_amount else None,
                target_date=target_date,
            )

            goal_data = _goal_to_display_data(goal)
            logger.info(f"Обновлена цель {goal_id}")

            return False, _build_goal_card(goal_data), "", False
    except ValidationError as e:
        logger.warning(f"Ошибка обновления цели: {e}")
        return True, no_update, str(e), True


@callback(
    Output("confirm-delete-goal", "displayed"),
    Input("delete-goal-btn", "n_clicks"),
    State("current-goal-id", "data"),
    prevent_initial_call=True,
)
def request_delete_goal(n_clicks, goal_id):
    """Открывает диалог подтверждения удаления.

    Использует dcc.ConfirmDialog - нативный браузерный диалог.
    """
    if not n_clicks or not goal_id:
        raise PreventUpdate
    return True


@callback(
    [
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("contributions-table-container", "children", allow_duplicate=True),
        Output("current-goal-id", "data", allow_duplicate=True),
    ],
    Input("confirm-delete-goal", "submit_n_clicks"),
    State("current-goal-id", "data"),
    prevent_initial_call=True,
)
def confirm_delete_goal(submit_clicks, goal_id):
    """Удаляет цель после подтверждения.

    Callback срабатывает при клике "OK" в ConfirmDialog.
    """
    if not submit_clicks or not goal_id:
        raise PreventUpdate

    with get_db_session() as session:
        service = GoalService(session)
        deleted = service.delete_goal(goal_id)

        if not deleted:
            raise PreventUpdate

        logger.info(f"Удалена цель {goal_id}")

        # Показываем empty state
        return _build_empty_state(), _build_contributions_table([]), None


@callback(
    Output("goal-card-container", "children", allow_duplicate=True),
    Input("toggle-status-btn", "n_clicks"),
    State("current-goal-id", "data"),
    prevent_initial_call=True,
)
def toggle_goal_status(n_clicks, goal_id):
    """Переключает статус цели ACTIVE <-> PAUSED.

    Бизнес-правила:
    - ACTIVE -> PAUSED: всегда разрешено
    - PAUSED -> ACTIVE: разрешено (в MVP нет других активных целей)
    - COMPLETED -> любой: запрещено (возврат из COMPLETED не поддерживается)
    """
    if not n_clicks or not goal_id:
        raise PreventUpdate

    with get_db_session() as session:
        service = GoalService(session)
        goal = service.get_by_id(goal_id)

        if not goal:
            raise PreventUpdate

        # Бизнес-правила переключения статуса
        if goal.status == GoalStatus.COMPLETED:
            # Нельзя менять статус завершенной цели
            raise PreventUpdate

        # Определяем новый статус
        new_status = GoalStatus.PAUSED if goal.status == GoalStatus.ACTIVE else GoalStatus.ACTIVE

        updated_goal = service.update_goal(goal_id, status=new_status)
        goal_data = _goal_to_display_data(updated_goal)

        logger.info(f"Статус цели {goal_id} изменен на {new_status.value}")

        return _build_goal_card(goal_data)
```

```python
# app/services/goal_service.py - расширение

def get_contributions(
    self,
    goal_id: int,
    limit: int = 10,
) -> list:
    """Получает список взносов цели отсортированный по дате DESC.

    Args:
        goal_id: ID цели
        limit: Максимальное количество записей (default 10)

    Returns:
        list[GoalContribution]: Последние взносы по дате убывания
    """
    from app.models.database import GoalContribution
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
# current-goal-id: хранит ID активной цели
# Обновляется при каждом CRUD для синхронизации
{
    "goal_id": int | None
}
```

### Синхронизация Store и UI
При каждой CRUD операции обновляем одновременно:
1. `goal-card-container` - визуальная карточка цели
2. `contributions-table-container` - таблица взносов
3. `current-goal-id` - Store с ID (для последующих операций)

Это гарантирует что Store всегда синхронизирован с UI.

### Layout компоненты
```python
# dcc.Store для ID цели
dcc.Store(id="current-goal-id", data=None),

# Confirm Dialog для удаления
dcc.ConfirmDialog(
    id="confirm-delete-goal",
    message="Вы уверены? Цель и все взносы будут удалены без возможности восстановления.",
),

# Alert для ошибок
dbc.Alert(
    id="goal-error-alert",
    is_open=False,
    color="danger",
    dismissable=True,
    duration=5000,
),
```

## Обработка ошибок

### Стратегия
1. **ValidationError от GoalService** - отображение в `dbc.Alert` с `is_open=True`
2. **Goal not found** - показ empty state с кнопкой "Создать цель"
3. **DB errors** - логирование через loguru, generic Alert с текстом "Произошла ошибка"
4. **Concurrent updates** - пере-загрузка данных из БД при каждом открытии модала редактирования

### Guard Clauses (упрощенные)
```python
# Для simple callbacks достаточно проверки triggered_id
@callback(..., prevent_initial_call=True)
def toggle_modal(click1, click2, is_open):
    triggered_id = ctx.triggered_id

    if triggered_id == "btn-open":
        return True
    if triggered_id == "btn-close":
        return False

    raise PreventUpdate
```

**Важно**: Pattern-Matching guard clauses из ADR-003 НЕ НУЖНЫ для goals.py, потому что одна активная цель = один набор кнопок с обычными ID.

## План реализации

### Фаза 1: Utils и GoalService Extension (~45 мин)
1. Создать директорию `app/utils/` с `__init__.py`
2. Создать `formatters.py` с `format_amount()`, `format_date()`, `format_days_remaining()`, `parse_date_safe()`
3. Добавить метод `get_contributions()` в `goal_service.py`
4. Обновить импорты в `transactions.py` (использовать formatters)
5. Написать unit тесты для `get_contributions()` (~4-6 тестов)

### Фаза 2: Goals Layout (~2 часа)
1. Создать `goals.py` со структурой:
   - `create_goals_layout()` - основной layout
   - `_build_goal_card()` - карточка цели
   - `_build_empty_state()` - состояние "нет цели"
   - `_build_progress_bar()` - визуальный прогресс
   - `_build_contributions_table()` - история взносов
   - `_build_action_buttons()` - кнопки действий
2. Создать модалы (Create, Edit, Contribution)
3. Добавить dcc.Store и dcc.ConfirmDialog

### Фаза 3: Goals Callbacks (~1.5 часа)
1. `load_goal_data()` - загрузка при переходе
2. `toggle_create_goal_modal()` + `create_goal()`
3. `toggle_contribution_modal()` + `add_contribution()`
4. `toggle_edit_modal()` + `update_goal()`
5. `request_delete_goal()` + `confirm_delete_goal()`
6. `toggle_goal_status()`

### Фаза 4: Стили и интеграция (~45 мин)
1. Создать `goals.css`:
   - Стили прогресс-бара
   - Стили карточки цели
   - Empty state стили
   - Адаптивность (768px, 576px)
2. Обновить `main.py` роутинг
3. Обновить `components/__init__.py`

### Фаза 5: Тестирование и QA (~1 час)
1. Ручное тестирование flows:
   - Создание цели
   - Добавление взноса
   - Редактирование
   - Удаление с подтверждением
   - Смена статуса
2. Проверка UI валидации форм
3. black + flake8
4. pytest (33+ тестов)

**Общая оценка: 6-7 часов**

## Зависимости

### Существующие (не требуют установки)
- dash, dash-bootstrap-components, plotly
- sqlalchemy, loguru
- pytest (для тестов)

### Новые библиотеки
- Не требуются

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| dcc.ConfirmDialog не работает в некоторых браузерах | Низкая | Резервный вариант: dbc.Modal с кнопками Да/Нет |
| UI форма не блокирует submit при невалидных данных | Средняя | Использовать `required=True`, `min`, `minDate` атрибуты в Input |
| Store устаревает при параллельных запросах | Низкая | Всегда обновлять Store при CRUD операциях |
| format_days_remaining неправильно склоняет | Низкая | Unit тесты для edge cases (1, 2, 5, 11, 21, 22) |
| DatePickerSingle показывает английские месяцы | Средняя | Использовать `locale` параметр или смириться для MVP |

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🔴 Отсутствие детализации Edit Goal callback с Pattern-Matching | Явно решено: **Pattern-Matching НЕ НУЖЕН** для одной активной цели. Используем простой callback с goal_id из dcc.Store. См. `toggle_edit_modal()` |
| 🔴 Отсутствие Confirm Dialog для удаления (FR-06) | Добавлен `dcc.ConfirmDialog` с `id="confirm-delete-goal"`. Двухшаговый процесс: `request_delete_goal()` открывает диалог, `confirm_delete_goal()` выполняет удаление |
| 🟡 Несоответствие UI State между dcc.Store и reload | Все CRUD операции одновременно обновляют `current-goal-id`, `goal-card-container`, `contributions-table-container`. Store всегда синхронизирован |
| 🟡 Отсутствие toggle_goal_status callback детализации | Добавлен полный callback с бизнес-правилами: ACTIVE↔PAUSED разрешено, из COMPLETED запрещено |
| 🟡 Дублирование format функций | Вынесены в `app/utils/formatters.py`. Transactions.py будет импортировать оттуда |
| 🟡 Отсутствие UI валидации форм | Описаны атрибуты: `required=True`, `min=0.01`, `minDate` (7 дней от сегодня) |
| 🟢 Empty state для истории взносов | Добавлен в `_build_contributions_table()` с текстом "Сделайте первый взнос!" |
| 🟢 days_remaining источник | Вычисляется в `_goal_to_display_data()`: `(goal.target_date - date.today()).days` |
| 🟢 Локализация DatePickerSingle | Отмечен как risk, используем `display_format="DD.MM.YYYY"`, полная локализация - опционально для MVP |

## Ответы на вопросы критика

1. **Вопрос:** Pattern-Matching для Edit/Delete - планируется ли использовать учитывая одну активную цель?
   **Ответ:** Нет. Pattern-Matching НЕ НУЖЕН для MVP с одной активной целью. Используем простые callbacks с `goal_id` из `dcc.Store`. Это упрощает код и исключает риски регрессий из ADR-003. Для Batch 2 с множественными целями можно добавить Pattern-Matching позже.

2. **Вопрос:** Confirm Dialog реализация - dcc.ConfirmDialog или dbc.Modal?
   **Ответ:** Используем `dcc.ConfirmDialog` (нативный браузерный) для MVP. Причины:
   - Простота реализации (1 компонент vs 3 для Modal)
   - Гарантированная работа во всех браузерах
   - Не требует дополнительных callbacks для toggle
   - Для стилизованного confirm в будущем легко заменить на dbc.Modal

3. **Вопрос:** Ручное завершение цели - должен ли пользователь иметь возможность установить COMPLETED вручную?
   **Ответ:** Нет, только автоматически при достижении `current_amount >= target_amount` (логика в `GoalService.add_contribution()`). Причины:
   - Упрощает UI (нет лишней кнопки/опции)
   - Соответствует интуитивному поведению (достиг цели = завершено)
   - Возврат из COMPLETED не поддерживается (нужно создать новую цель)

4. **Вопрос:** History limit=10 - нужна ли пагинация или "Показать все"?
   **Ответ:** Для MVP limit=10 достаточно. Причины:
   - Средний пользователь делает 1-2 взноса в месяц = ~24 взноса/год
   - 10 последних покрывает ~5-10 месяцев активности
   - Пагинация усложняет UI без явной пользы
   - В Batch 3 (Analytics) можно добавить полную историю с фильтрами

5. **Вопрос:** format функции - вынести сейчас или отложить?
   **Ответ:** Вынести сейчас в `app/utils/formatters.py`. Причины:
   - Предотвращает дублирование с transactions.py
   - Минимальные усилия (~30 мин)
   - Улучшает поддерживаемость кода
   - Соответствует принципу DRY
