# Шаг 3: Dash Callbacks — Интерактивность

## Briefing
- **Цель:** Реализовать Dash callbacks для навигации по месяцам, загрузки данных и открытия модала создания операции. Применить guard clauses согласно ADR-003.
- **Ключевые файлы:**
  - `app/components/calendar.py` (модифицировать — добавить callbacks)
- **Additional info:**
  - **КРИТИЧНО**: Pattern-Matching Callbacks требуют 3 guard clauses
  - Используем существующий `create-modal` из transactions.py (не создаем новый)
  - Навигация ограничена +-12 месяцев от сегодня
  - Для тестирования transactions.py должен быть импортирован (для регистрации модалов)

## Sub-tasks

### 1. Добавить необходимые импорты

В начало `app/components/calendar.py` добавить:

```python
from dash import callback, Input, Output, State, ALL, ctx
from dash.exceptions import PreventUpdate
from dateutil.relativedelta import relativedelta
from loguru import logger

from app.core.database import get_db_session
from app.services.calendar_service import CalendarService
```

### 2. Реализовать callback загрузки и навигации

```python
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
    """Загружает календарь и обрабатывает навигацию между месяцами."""
```

**Логика:**
1. Guard: `pathname != "/calendar"` → `PreventUpdate`
2. Определить текущий месяц/год из state
3. Обработать навигацию:
   - `prev-month-btn` → месяц - 1
   - `next-month-btn` → месяц + 1
   - `today-btn` → текущий месяц
4. Валидация +-12 месяцев
5. Загрузить данные через CalendarService
6. Построить UI компоненты
7. Обновить state с сериализованными балансами

**Обработка ошибок:**
```python
try:
    with get_db_session() as session:
        service = CalendarService(session)
        # ... загрузка данных
except Exception as e:
    logger.error(f"Ошибка загрузки календаря: {e}")
    return (
        build_calendar_header(current_month, current_year),
        dbc.Alert("Не удалось загрузить данные", color="danger"),
        html.Div(),
        state,
    )
```

### 3. Реализовать callback открытия модала

```python
@callback(
    [
        Output("create-modal", "is_open", allow_duplicate=True),
        Output("create-date-picker", "date", allow_duplicate=True),
    ],
    Input({"type": "calendar-day", "date": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_create_modal_from_calendar(n_clicks_list: list[int | None]):
    """Открывает модал создания операции при клике на день календаря."""
```

**Guard clauses (КРИТИЧНО!):**
```python
triggered_id = ctx.triggered_id

# Guard #1: проверка triggered_id существует
if not triggered_id:
    raise PreventUpdate

# Guard #2: проверка типа (для Pattern-Matching)
if not isinstance(triggered_id, dict) or triggered_id.get("type") != "calendar-day":
    raise PreventUpdate

# Guard #3: проверка реального клика (НЕ автовызов при DOM update!)
if not ctx.triggered or ctx.triggered[0].get("value") is None:
    raise PreventUpdate

# Извлекаем дату
selected_date = triggered_id.get("date")
if not selected_date:
    raise PreventUpdate

logger.debug(f"Открыт модал создания из календаря: {selected_date}")
return True, selected_date
```

### 4. Реализовать callback обновления после CRUD

```python
@callback(
    [
        Output("calendar-grid", "children", allow_duplicate=True),
        Output("calendar-stats", "children", allow_duplicate=True),
        Output("calendar-state", "data", allow_duplicate=True),
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
    """Обновляет календарь после создания/изменения/удаления операции."""
```

**Guard clauses:**
```python
triggered_id = ctx.triggered_id

# Guard #1
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
```

**Логика:**
1. Получить текущий месяц из state
2. Пересчитать данные через CalendarService
3. Вернуть обновленные grid, stats и state

### 5. Проверить зависимость python-dateutil

Перед использованием `relativedelta` убедиться что библиотека установлена:
```bash
pip show python-dateutil
```

Если не установлена — добавить в `requirements.txt`:
```
python-dateutil>=2.8.2
```

## Важные детали

### ID модалов из transactions.py

Callback `open_create_modal_from_calendar` использует:
- `Output("create-modal", "is_open")` — существующий модал
- `Output("create-date-picker", "date")` — существующий date picker

Эти компоненты определены в `app/components/transactions.py`. Убедись что при тестировании transactions.py импортирован.

### Порядок импортов в main.py

Для корректной работы callbacks календарь должен импортироваться ПОСЛЕ transactions:
```python
from app.components import transactions  # Сначала (регистрирует модалы)
from app.components import calendar      # Потом (использует модалы)
```

### allow_duplicate=True

Используется для outputs, которые обновляются несколькими callbacks:
- `create-modal.is_open` — из transactions.py и calendar.py
- `create-date-picker.date` — из transactions.py и calendar.py
- `calendar-grid.children` — из load_and_navigate и refresh_after_transaction

## Workflow (Порядок работы)

1. **Выполнение:** Добавь callbacks в `app/components/calendar.py`:
   - `load_and_navigate_calendar()`
   - `open_create_modal_from_calendar()`
   - `refresh_calendar_after_transaction()`

2. **Верификация:**
   ```bash
   black app/components/calendar.py
   flake8 app/components/calendar.py
   ```

3. **Фиксация:**
   - Добавь запись в `log.md`
   - Обнови `context.md`: `Current Step` → `4`

4. **Коммит:**
   ```bash
   git add .
   git commit -m "feat(calendar): add navigation and modal callbacks [protocol-0002/03]"
   git push
   ```

5. **Отчет пользователю.**

<формат_отчёта_о_шаге>
(Протокол 0002, шаг 3):

**Сделано**: список изменений.

**Проверки**: black, flake8 — результаты.

**Git**: PR, ветка, коммит, main чистая.

**Рабочая папка**: /home/skytiger/PycharmProjects/worktrees/0002-cash-calendar

**Статус протокола**: Шаг 3 завершен, следующий — Шаг 4 (Интеграция).
</формат_отчёта_о_шаге>
