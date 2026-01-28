# Solution v2: Финансовая подушка безопасности

## Обзор решения

Техническое решение для протокола 4.1 с ключевым изменением: **threshold теперь хранится в процентах (0-100)**, а не в абсолютной сумме. Это упрощает валидацию и гарантирует, что маркер порога всегда находится в пределах прогресс-бара.

**Исправления по замечаниям Critique-v1:**
1. threshold <= target валидация больше не нужна (threshold в %)
2. calculate_recommendation: return Decimal("0") при пустых сценариях
3. calculate_recommendation: строгая валидация mode через VALID_MODES
4. Полная детализация 9 callbacks (таблица Input/Output)
5. Refresh карточки через cushion-refresh-trigger Store
6. Переименование в CushionService (как GoalService)
7. TypedDict: все поля required (total=True по умолчанию)
8. CSS prefix `.cushion-*`

## Архитектура

### Компоненты

```
┌─────────────────────────────────────────────────────────────┐
│                         /goals page                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │             Cushion Card Component                   │    │
│  │  - _build_cushion_card_unconfigured()               │    │
│  │  - _build_cushion_card_configured()                 │    │
│  │  - Progress bar + threshold marker                   │    │
│  └────────────────────┬────────────────────────────────┘    │
│                       │ click                                │
│                       ▼                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │             Cushion Modal Component                  │    │
│  │  - Target input (Decimal)                           │    │
│  │  - Threshold % input (0-100)                        │    │
│  │  - Scenarios calculator (Collapse)                  │    │
│  │  - Save/Reset buttons                               │    │
│  └────────────────────┬────────────────────────────────┘    │
│                       │                                      │
├───────────────────────┼─────────────────────────────────────┤
│   dcc.Store           │                                      │
│   ┌──────────────────┐│                                      │
│   │cushion-scenarios-│├──────────────────────────────────┐  │
│   │store             ││ cushion-refresh-trigger          │  │
│   └──────────────────┘│ (triggers card reload)           │  │
│   ┌──────────────────┐└──────────────────────────────────┘  │
│   │cushion-calc-mode │                                      │
│   └──────────────────┘                                      │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    CushionService                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ get_settings(user_id) -> CushionSettings              │  │
│  │ update_settings(user_id, target, threshold_%, manual) │  │
│  │ reset_settings(user_id)                               │  │
│  │ calculate_recommendation(scenarios, mode) -> Decimal  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  CalendarService                             │
│  get_balance_on_date(user_id, today) -> current_amount      │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      User Model                              │
│  cushion_target: Decimal(10,2)                              │
│  cushion_threshold_percent: Integer (0-100)                 │
│  cushion_threshold_manual: Boolean                          │
└─────────────────────────────────────────────────────────────┘
```

### Диаграмма потока данных

```
User opens /goals
       │
       ▼
┌──────────────────┐
│ load_goals_page  │
│ callback         │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│ CushionService.  │────►│ CalendarService. │
│ get_settings()   │     │ get_balance_on   │
└────────┬─────────┘     │ _date()          │
         │               └──────────────────┘
         ▼
┌──────────────────┐
│ CushionSettings  │
│ TypedDict        │
│ - target         │
│ - threshold_%    │
│ - threshold_amt  │
│ - current_amount │
│ - progress       │
│ - is_configured  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ build_cushion_   │
│ card()           │
└────────┬─────────┘
         │
   ┌─────┴─────┐
   │           │
   ▼           ▼
is_configured?
   │           │
   │ False     │ True
   ▼           ▼
┌──────────┐  ┌──────────────┐
│Unconfigur│  │Configured    │
│ed card   │  │card + marker │
└──────────┘  └──────────────┘
```

## Файловая структура

```
app/
├── models/
│   └── database.py          # +3 поля в User (MODIFY)
├── schema/
│   ├── __init__.py          # +exports (MODIFY)
│   └── cushion.py           # NEW: CushionSettings, CushionScenario
├── services/
│   ├── __init__.py          # +CushionService export (MODIFY)
│   └── cushion_service.py   # NEW: CushionService
├── components/
│   └── goals.py             # +cushion card, modal, callbacks (MODIFY)
└── assets/
    └── goals.css            # +.cushion-* styles (MODIFY)

tests/
└── test_cushion_service.py  # NEW: 12+ unit tests
```

## Ключевые интерфейсы

### TypedDicts (app/schema/cushion.py)

```python
from decimal import Decimal
from typing import TypedDict


class CushionSettings(TypedDict):
    """Настройки подушки из User.

    Все поля обязательны (total=True по умолчанию).

    Attributes:
        target: Целевая сумма подушки (cushion_target из User).
        threshold_percent: Порог в процентах 0-100 (cushion_threshold_percent).
        threshold_amount: Вычисляемое: target * threshold_percent / 100.
        threshold_manual: True если порог изменён вручную.
        current_amount: Текущий баланс (из CalendarService).
        progress: Процент выполнения 0-100 (capped).
        is_configured: target > 0.
    """
    target: Decimal
    threshold_percent: int       # 0-100
    threshold_amount: Decimal    # computed: target * percent / 100
    threshold_manual: bool
    current_amount: Decimal
    progress: float              # 0-100
    is_configured: bool


class CushionScenario(TypedDict):
    """Сценарий для калькулятора (не сохраняется в БД).

    Attributes:
        name: Название сценария (не пустое).
        min_amount: Минимальная сумма >= 0.
        max_amount: Максимальная сумма >= min_amount.
    """
    name: str
    min_amount: Decimal
    max_amount: Decimal
```

### CushionService (app/services/cushion_service.py)

```python
from decimal import Decimal
from loguru import logger
from sqlalchemy.orm import Session

from app.core import ValidationError
from app.schema.cushion import CushionSettings, CushionScenario

# Допустимые режимы расчёта
VALID_CALC_MODES = {"sum", "max_scenario"}

# Дефолтный порог при создании/сбросе
DEFAULT_THRESHOLD_PERCENT = 30


class CushionService:
    """Сервис для работы с финансовой подушкой.

    Именование соответствует GoalService (без префикса Safety).
    """

    def __init__(self, session: Session):
        """Инициализирует сервис.

        Args:
            session: SQLAlchemy сессия для работы с БД.
        """
        self.session = session

    def get_settings(self, user_id: int) -> CushionSettings:
        """Получить настройки подушки с вычисленными полями.

        Args:
            user_id: ID пользователя.

        Returns:
            CushionSettings: Полные настройки включая вычисляемые поля.

        Raises:
            ValidationError: Если пользователь не найден.
        """
        user = self._get_user(user_id)
        current = self._get_current_balance(user_id)

        target = user.cushion_target or Decimal("0")
        threshold_percent = user.cushion_threshold_percent or 0

        # Вычисляем threshold_amount
        threshold_amount = target * threshold_percent / 100 if target > 0 else Decimal("0")

        # Вычисляем progress
        progress = 0.0
        if target > 0:
            if current < 0:
                progress = 0.0
            else:
                progress = min(float(current / target * 100), 100.0)

        return CushionSettings(
            target=target,
            threshold_percent=threshold_percent,
            threshold_amount=threshold_amount,
            threshold_manual=user.cushion_threshold_manual,
            current_amount=current,
            progress=progress,
            is_configured=target > 0,
        )

    def update_settings(
        self,
        user_id: int,
        target: Decimal,
        threshold_percent: int,
        threshold_manual: bool,
    ) -> None:
        """Обновить настройки подушки.

        Args:
            user_id: ID пользователя.
            target: Целевая сумма (>= 0).
            threshold_percent: Порог в процентах (0-100).
            threshold_manual: True если порог изменён вручную.

        Raises:
            ValidationError: Если target < 0 или threshold_percent не в 0-100.
        """
        # Валидация
        if target < 0:
            raise ValidationError("Цель должна быть >= 0", field="target")

        if not 0 <= threshold_percent <= 100:
            raise ValidationError(
                "Порог должен быть в диапазоне 0-100%",
                field="threshold_percent"
            )

        user = self._get_user(user_id)
        user.cushion_target = target
        user.cushion_threshold_percent = threshold_percent
        user.cushion_threshold_manual = threshold_manual
        self.session.flush()

        logger.info(
            f"Обновлены настройки подушки для user {user_id}: "
            f"target={target}, threshold={threshold_percent}%"
        )

    def reset_settings(self, user_id: int) -> None:
        """Сбросить настройки подушки.

        При сбросе:
        - target = 0
        - threshold_percent = DEFAULT_THRESHOLD_PERCENT (30)
        - threshold_manual = False

        Args:
            user_id: ID пользователя.
        """
        user = self._get_user(user_id)
        user.cushion_target = Decimal("0")
        user.cushion_threshold_percent = DEFAULT_THRESHOLD_PERCENT
        user.cushion_threshold_manual = False
        self.session.flush()

        logger.info(f"Сброшены настройки подушки для user {user_id}")

    def calculate_recommendation(
        self,
        scenarios: list[CushionScenario],
        mode: str,
    ) -> Decimal:
        """Рассчитать рекомендуемую цель по сценариям.

        Args:
            scenarios: Список сценариев (может быть пустым).
            mode: Режим расчёта ("sum" | "max_scenario").

        Returns:
            Decimal: Рекомендуемая цель. Decimal("0") если scenarios пуст.

        Raises:
            ValidationError: Если mode не в VALID_CALC_MODES.
        """
        # Валидация mode
        if mode not in VALID_CALC_MODES:
            raise ValidationError(
                f"Недопустимый режим расчёта: {mode}. "
                f"Допустимые: {', '.join(sorted(VALID_CALC_MODES))}"
            )

        # Guard: empty scenarios
        if not scenarios:
            return Decimal("0")

        if mode == "sum":
            return sum(s["max_amount"] for s in scenarios)
        else:  # max_scenario
            return max(s["max_amount"] for s in scenarios)

    def _get_current_balance(self, user_id: int) -> Decimal:
        """Получить текущий баланс через CalendarService.

        Args:
            user_id: ID пользователя.

        Returns:
            Decimal: Текущий баланс на сегодня.
        """
        from datetime import date
        from app.services.calendar_service import CalendarService

        calendar_service = CalendarService(self.session)
        return calendar_service.get_balance_on_date(user_id, date.today())

    def _get_user(self, user_id: int):
        """Получить пользователя по ID.

        Args:
            user_id: ID пользователя.

        Returns:
            User: Объект пользователя.

        Raises:
            ValidationError: Если пользователь не найден.
        """
        from app.models.database import User

        user = self.session.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValidationError(f"Пользователь с ID {user_id} не найден")
        return user
```

## Модель данных

### User (обновлённая)

```python
# В app/models/database.py

class User(Base):
    """Модель пользователя."""

    __tablename__ = "users"

    # ... существующие поля ...

    # Финансовая подушка (v2: threshold в процентах)
    cushion_target = Column(Numeric(10, 2), default=0, nullable=False)
    cushion_threshold_percent = Column(Integer, default=30, nullable=False)  # 0-100
    cushion_threshold_manual = Column(Boolean, default=False, nullable=False)
```

### Валидация

```python
# Валидация в CushionService

# threshold_percent: 0-100
if not 0 <= threshold_percent <= 100:
    raise ValidationError("Порог должен быть в диапазоне 0-100%")

# target: >= 0
if target < 0:
    raise ValidationError("Цель должна быть >= 0")

# mode: строгая валидация
VALID_CALC_MODES = {"sum", "max_scenario"}
if mode not in VALID_CALC_MODES:
    raise ValidationError(f"Недопустимый режим: {mode}")
```

## Callback Signatures

| # | Callback | Inputs | Outputs | Pattern-Matching? | ADR-003 Guards | Notes |
|---|----------|--------|---------|-------------------|----------------|-------|
| 1 | `open_cushion_modal` | `Input("cushion-card-btn", "n_clicks")` | `Output("cushion-modal", "is_open")`, `Output("cushion-target-input", "value")`, `Output("cushion-threshold-input", "value")`, `Output("cushion-scenarios-store", "data")` | No | `if not n_clicks: raise PreventUpdate` | Загружает текущие настройки в форму |
| 2 | `update_threshold_on_target_change` | `Input("cushion-target-input", "value")`, `State("cushion-threshold-manual-flag", "data")` | `Output("cushion-threshold-input", "value")`, `Output("cushion-threshold-amount-display", "children")` | No | `if not target: return no_update, no_update` | Пересчитывает threshold_amount, НЕ меняет % если manual |
| 3 | `mark_threshold_manual` | `Input("cushion-threshold-input", "value")` | `Output("cushion-threshold-manual-flag", "data")` | No | `if value is None: raise PreventUpdate` | Устанавливает manual=True при ручном вводе |
| 4 | `manage_scenarios` | `Input({"type": "cushion-add-scenario-btn"}, "n_clicks")`, `Input({"type": "cushion-remove-scenario", "index": ALL}, "n_clicks")`, `State("cushion-scenarios-store", "data")` | `Output("cushion-scenarios-store", "data")`, `Output("cushion-scenarios-container", "children")` | Yes (ALL) | `if not ctx.triggered_id: raise PreventUpdate` | Add: max 5. Remove: по index |
| 5 | `calculate_and_display_recommendation` | `Input("cushion-calc-btn", "n_clicks")`, `State("cushion-scenarios-store", "data")`, `State("cushion-calc-mode", "data")` | `Output("cushion-recommendation-value", "children")`, `Output("cushion-apply-btn", "disabled")` | No | `if not scenarios: return "0 ₽", True` | Apply disabled если 0 или no scenarios |
| 6 | `apply_recommendation` | `Input("cushion-apply-btn", "n_clicks")`, `State("cushion-recommendation-value", "children")` | `Output("cushion-target-input", "value")` | No | `if not n_clicks: raise PreventUpdate` | Парсит сумму из children |
| 7 | `save_cushion_settings` | `Input("cushion-save-btn", "n_clicks")`, `State("cushion-target-input", "value")`, `State("cushion-threshold-input", "value")`, `State("cushion-threshold-manual-flag", "data")` | `Output("cushion-modal", "is_open")`, `Output("cushion-refresh-trigger", "data")`, `Output("cushion-error-alert", "is_open")`, `Output("cushion-error-alert", "children")` | No | `if not n_clicks: raise PreventUpdate` | Flush to DB + close modal + trigger refresh |
| 8 | `reset_cushion_settings` | `Input("cushion-reset-btn", "n_clicks")` | `Output("cushion-target-input", "value")`, `Output("cushion-threshold-input", "value")`, `Output("cushion-threshold-manual-flag", "data")`, `Output("cushion-modal", "is_open")`, `Output("cushion-refresh-trigger", "data")` | No | `if not n_clicks: raise PreventUpdate` | Сбрасывает в DB + close + trigger |
| 9 | `refresh_cushion_card` | `Input("cushion-refresh-trigger", "data")` | `Output("cushion-card-container", "children")` | No | `if data is None: raise PreventUpdate` | Перестраивает карточку после save/reset |

### Guard Clauses Pattern (ADR-003)

Все callbacks следуют паттерну:

```python
@callback(...)
def save_cushion_settings(n_clicks, target_value, threshold_value, manual_flag):
    # Guard #1: No clicks
    if not n_clicks:
        raise PreventUpdate

    # Guard #2: Invalid input
    if target_value is None or target_value < 0:
        return no_update, no_update, True, "Введите положительное число"

    # Guard #3: threshold validation
    if not 0 <= threshold_value <= 100:
        return no_update, no_update, True, "Порог должен быть 0-100%"

    # Main logic
    with get_db_session() as session:
        service = CushionService(session)
        service.update_settings(
            user_id=DEFAULT_USER_ID,
            target=Decimal(str(target_value)),
            threshold_percent=threshold_value,
            threshold_manual=manual_flag,
        )
        session.commit()

    # Return: close modal, trigger refresh, no error
    return False, int(time.time()), False, ""
```

## Обработка ошибок

### Валидация mode

```python
# В CushionService.calculate_recommendation()

VALID_CALC_MODES = {"sum", "max_scenario"}

def calculate_recommendation(self, scenarios, mode):
    if mode not in VALID_CALC_MODES:
        raise ValidationError(
            f"Недопустимый режим расчёта: {mode}. "
            f"Допустимые значения: {', '.join(sorted(VALID_CALC_MODES))}"
        )
    # ...
```

### Empty scenarios

```python
def calculate_recommendation(self, scenarios, mode):
    # Guard: empty scenarios
    if not scenarios:
        return Decimal("0")
    # ...

# В UI callback:
@callback(
    Output("cushion-recommendation-value", "children"),
    Output("cushion-apply-btn", "disabled"),  # NEW: disable Apply
    Input("cushion-calc-btn", "n_clicks"),
    State("cushion-scenarios-store", "data"),
    State("cushion-calc-mode", "data"),
)
def calculate_and_display_recommendation(n_clicks, scenarios, mode):
    if not n_clicks:
        raise PreventUpdate

    # Guard: no scenarios -> disable Apply button
    if not scenarios:
        return "0 ₽", True  # disabled=True

    with get_db_session() as session:
        service = CushionService(session)
        recommendation = service.calculate_recommendation(scenarios, mode)

    return format_amount(recommendation), False  # disabled=False
```

## Refresh механизм

### cushion-refresh-trigger Store

```python
# В create_goals_layout():
dcc.Store(id="cushion-refresh-trigger", data=None)

# После save_cushion_settings:
return False, int(time.time()), False, ""  # data = timestamp

# Callback для refresh карточки:
@callback(
    Output("cushion-card-container", "children"),
    Input("cushion-refresh-trigger", "data"),
    prevent_initial_call=True,
)
def refresh_cushion_card(trigger_data):
    """Обновляет карточку подушки после сохранения/сброса."""
    # Guard: initial или None
    if trigger_data is None:
        raise PreventUpdate

    # Перезагружаем настройки и перестраиваем карточку
    with get_db_session() as session:
        service = CushionService(session)
        settings = service.get_settings(DEFAULT_USER_ID)

    return build_cushion_card(settings)
```

### Диаграмма Refresh Flow

```
User clicks "Сохранить"
         │
         ▼
┌────────────────────────┐
│ save_cushion_settings  │
│ callback               │
│                        │
│ 1. Validate inputs     │
│ 2. CushionService.     │
│    update_settings()   │
│ 3. session.commit()    │
│ 4. Return:             │
│    - modal.is_open=F   │
│    - trigger=timestamp │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ dcc.Store              │
│ cushion-refresh-trigger│
│ data = 1706454321      │
└───────────┬────────────┘
            │ Input
            ▼
┌────────────────────────┐
│ refresh_cushion_card   │
│ callback               │
│                        │
│ 1. CushionService.     │
│    get_settings()      │
│ 2. build_cushion_card()│
│ 3. Return new card     │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ cushion-card-container │
│ (updated UI)           │
└────────────────────────┘
```

## UI Компоненты

### Карточка подушки (Unconfigured)

```python
def _build_cushion_card_unconfigured() -> dbc.Card:
    """Карточка для ненастроенной подушки."""
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    [html.I(className="bi bi-shield-check me-2"), "Финансовая подушка"],
                    className="mb-0 text-white",
                ),
                className="cushion-card-header",
            ),
            dbc.CardBody(
                [
                    html.P(
                        "Создайте финансовую подушку для защиты от непредвиденных расходов",
                        className="text-muted text-center mb-3",
                    ),
                    html.Div(
                        dbc.Button(
                            "Настроить",
                            id="cushion-card-btn",
                            color="success",
                            outline=True,
                        ),
                        className="text-center",
                    ),
                ],
                className="cushion-card-body",
            ),
        ],
        className="cushion-card cushion-card-unconfigured mb-3",
    )
```

### Карточка подушки (Configured)

```python
def _build_cushion_card_configured(settings: CushionSettings) -> dbc.Card:
    """Карточка для настроенной подушки с прогресс-баром."""
    target = settings["target"]
    current = settings["current_amount"]
    progress = settings["progress"]
    threshold_percent = settings["threshold_percent"]

    # Цвет прогресс-бара: зелёный если >= threshold, оранжевый если <
    progress_color = "success" if progress >= threshold_percent else "warning"

    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    [html.I(className="bi bi-shield-check me-2"), "Финансовая подушка"],
                    className="mb-0 text-white",
                ),
                className="cushion-card-header",
            ),
            dbc.CardBody(
                [
                    # Цель и текущий баланс
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Small("Цель", className="text-muted"),
                                    html.H5(format_amount(target), className="mb-0"),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    html.Small("Сейчас", className="text-muted"),
                                    html.H5(format_amount(current), className="mb-0"),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    # Прогресс-бар с маркером порога
                    html.Div(
                        [
                            dbc.Progress(
                                value=progress,
                                color=progress_color,
                                className="cushion-progress-bar",
                                style={"height": "24px"},
                            ),
                            # Маркер порога
                            html.Div(
                                className="cushion-threshold-marker",
                                style={"left": f"{threshold_percent}%"},
                            ),
                        ],
                        className="cushion-progress-container position-relative mb-2",
                    ),
                    # Подпись
                    html.Div(
                        [
                            html.Small(f"{progress:.0f}%", className="text-muted"),
                            html.Small(
                                f"↑ порог ({threshold_percent}%)",
                                className="text-muted ms-2",
                                style={"margin-left": f"calc({threshold_percent}% - 30px)"},
                            ),
                        ],
                        className="d-flex justify-content-between",
                    ),
                    # Кнопка
                    html.Div(
                        dbc.Button(
                            "Настроить",
                            id="cushion-card-btn",
                            color="success",
                            outline=True,
                            size="sm",
                        ),
                        className="text-center mt-3",
                    ),
                ],
                className="cushion-card-body",
            ),
        ],
        className="cushion-card cushion-card-configured mb-3",
    )
```

### CSS стили (.cushion-*)

```css
/* === CUSHION CARD === */
.cushion-card {
    border: none;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    border-radius: 12px;
}

.cushion-card-header {
    background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
    color: white;
    border-radius: 12px 12px 0 0;
    padding: 1rem 1.25rem;
}

.cushion-card-unconfigured {
    border: 2px dashed #dee2e6;
}

.cushion-card-unconfigured .cushion-card-header {
    background: #6c757d;
}

.cushion-card-body {
    padding: 1.25rem;
}

/* === PROGRESS BAR WITH MARKER === */
.cushion-progress-container {
    position: relative;
}

.cushion-progress-bar {
    border-radius: 12px;
    overflow: visible;
}

.cushion-threshold-marker {
    position: absolute;
    top: 0;
    width: 3px;
    height: 100%;
    background-color: #212529;
    border-radius: 2px;
    z-index: 10;
    transform: translateX(-50%);
}

/* === MODAL === */
.cushion-modal .modal-content {
    border-radius: 12px;
    border: none;
}

.cushion-modal .modal-header {
    background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
    color: white;
    border-radius: 12px 12px 0 0;
}

.cushion-scenario-item {
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.75rem;
    background: #f8f9fa;
}

.cushion-recommendation-box {
    background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
}

/* === RESPONSIVE === */
@media (max-width: 576px) {
    .cushion-card-body {
        padding: 1rem;
    }

    .cushion-progress-bar {
        height: 20px !important;
    }
}
```

## План реализации

### Шаг 1: Schema + миграция (app/models/database.py)

```
Задачи:
1. Добавить 3 поля в User:
   - cushion_target: Numeric(10,2), default=0
   - cushion_threshold_percent: Integer, default=30
   - cushion_threshold_manual: Boolean, default=False
2. Пересоздать БД (dev stage)
3. Обновить seed_database.py если необходимо

Оценка: 15 мин
```

### Шаг 2: TypedDicts (app/schema/cushion.py)

```
Задачи:
1. Создать файл app/schema/cushion.py
2. Добавить CushionSettings TypedDict
3. Добавить CushionScenario TypedDict
4. Обновить app/schema/__init__.py

Оценка: 10 мин
```

### Шаг 3: CushionService (app/services/cushion_service.py)

```
Задачи:
1. Создать файл app/services/cushion_service.py
2. Реализовать VALID_CALC_MODES, DEFAULT_THRESHOLD_PERCENT
3. Реализовать get_settings() с вычисляемыми полями
4. Реализовать update_settings() с валидацией
5. Реализовать reset_settings()
6. Реализовать calculate_recommendation() с валидацией mode
7. Обновить app/services/__init__.py

Оценка: 30 мин
```

### Шаг 4: Карточка подушки (app/components/goals.py)

```
Задачи:
1. build_cushion_card(settings) - dispatcher
2. _build_cushion_card_unconfigured() - состояние "Настроить"
3. _build_cushion_card_configured(settings) - с прогресс-баром
4. Интеграция в create_goals_layout() - вверху, над бюджетом
5. Добавить dcc.Store cushion-refresh-trigger

Оценка: 45 мин
```

### Шаг 5: Модал настройки (app/components/goals.py)

```
Задачи:
1. build_cushion_modal() - структура модала
2. _build_scenarios_section() - сворачиваемый блок сценариев
3. _build_scenario_item(index, scenario) - один сценарий
4. Добавить dcc.Store: cushion-scenarios-store, cushion-calc-mode
5. Добавить dcc.Store: cushion-threshold-manual-flag

Оценка: 60 мин
```

### Шаг 6: Callbacks (app/components/goals.py)

```
Задачи:
1. open_cushion_modal() - открытие + загрузка данных
2. update_threshold_on_target_change() - автопересчёт
3. mark_threshold_manual() - флаг ручного ввода
4. manage_scenarios() - add/remove с Pattern-Matching
5. calculate_and_display_recommendation() - расчёт + disable Apply
6. apply_recommendation() - копирование в поле
7. save_cushion_settings() - сохранение + trigger
8. reset_cushion_settings() - сброс + trigger
9. refresh_cushion_card() - обновление карточки

Оценка: 90 мин
```

### Шаг 7: CSS стили (app/assets/goals.css)

```
Задачи:
1. Стили .cushion-card, .cushion-card-header
2. Стили .cushion-progress-container, .cushion-progress-bar
3. Стили .cushion-threshold-marker
4. Стили .cushion-modal, .cushion-scenario-item
5. Responsive стили

Оценка: 30 мин
```

### Шаг 8: Unit тесты (tests/test_cushion_service.py)

```
Тесты:
1. test_get_settings_unconfigured() - target=0
2. test_get_settings_configured() - target>0, вычисления
3. test_get_settings_negative_balance() - progress=0
4. test_get_settings_over_target() - progress=100 (cap)
5. test_update_settings_valid()
6. test_update_settings_negative_target() - ValidationError
7. test_update_settings_invalid_threshold() - 0-100
8. test_reset_settings() - threshold=30%, manual=False
9. test_calculate_recommendation_sum()
10. test_calculate_recommendation_max()
11. test_calculate_recommendation_empty() - return 0
12. test_calculate_recommendation_invalid_mode() - ValidationError

Оценка: 45 мин
```

### Шаг 9: Финализация

```
Задачи:
1. Black форматирование
2. Flake8 проверка
3. pytest (280+ тестов)
4. Ручное тестирование UI

Оценка: 20 мин
```

**Общее время: ~6 часов**

## Риски и mitigation

| Риск | Вероятность | Влияние | Mitigation |
|------|-------------|---------|------------|
| Путаница threshold % vs amount | Низкая | Среднее | threshold_amount вычисляется автоматически и показывается в UI |
| DB schema mismatch | Низкая | Высокое | Пересоздание БД в dev, документация для team |
| Pattern-Matching callbacks race | Низкая | Среднее | ADR-003 guard clauses, prevent_initial_call |
| CalendarService dependency | Низкая | Среднее | Уже протестирован, 792 строки кода |
| CSS z-index conflicts | Низкая | Низкое | .cushion-threshold-marker z-index: 10 |

## Учтённые замечания из критики v1

| Замечание | Как решено |
|-----------|------------|
| **🟡 #1: threshold <= target валидация** | threshold в % (0-100), невозможен > target |
| **🟡 #2: empty scenarios** | return Decimal("0"), disable Apply button |
| **🟡 #3: mode validation** | VALID_CALC_MODES set + ValidationError |
| **🟡 #4: callbacks не детализированы** | Добавлена таблица Callback Signatures с 9 callbacks |
| **🟡 #5: refresh карточки** | cushion-refresh-trigger Store с timestamp |
| **🟢 #1: naming** | Переименован в CushionService (как GoalService) |
| **🟢 #2: TypedDict total** | Все поля required, total=True по умолчанию |
| **🟢 #3: CSS prefix** | .cushion-* для всех стилей |

## Ответы на вопросы критика

### 1. Маркер порога при threshold > target

**Ответ:** Threshold теперь в % (0-100). Маркер **всегда** в пределах прогресс-бара. Позиция = `threshold_percent%`. При threshold_percent=30 маркер на 30% от левого края.

### 2. Автопересчет при reset

**Ответ:** `reset_settings()` устанавливает:
- `cushion_target = 0`
- `cushion_threshold_percent = 30` (DEFAULT)
- `cushion_threshold_manual = False`

При следующем вводе цели порог автоматически пересчитается как 30%.

### 3. Debounce для update_threshold

**Ответ:** Без debounce. Input без `debounce=True`. Мгновенный пересчёт `threshold_amount` при изменении target. Если пользователь вручную изменил %, пересчитывается только отображаемая сумма, но % не меняется.

### 4. Warning при закрытии без сохранения

**Ответ:** Без warning. Модал просто закрывается при клике вне или на X. Проще UX для MVP. Сценарии (временные данные) теряются - это документировано.

### 5. dcc.Store prefix

**Ответ:** Все Store IDs с prefix `cushion-`:
- `cushion-scenarios-store`
- `cushion-calc-mode`
- `cushion-refresh-trigger`
- `cushion-threshold-manual-flag`
- `cushion-error-alert`
