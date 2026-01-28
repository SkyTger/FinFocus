# Solution v1: Финансовая подушка безопасности

## Обзор решения
Решение добавляет функциональность финансовой подушки безопасности как расширение модели User (не как отдельную цель). Backend реализуется через SafetyCushionService, который использует CalendarService для получения текущего баланса. UI интегрируется в существующую страницу /goals с отдельной карточкой и модалом настройки, следуя паттернам проекта (TypedDicts, Service Layer, Dash callbacks с ADR-003 guard clauses).

## Архитектура

### Компоненты

**1. Data Layer (app/models/database.py)**
- Расширение модели User тремя полями для хранения настроек подушки
- Декларативный подход SQLAlchemy, совместимый с существующей схемой

**2. Schema Layer (app/schema/cushion.py)**
- `CushionSettings` - TypedDict для передачи данных между Service и UI
- `CushionScenario` - TypedDict для калькулятора (не персистируется)

**3. Service Layer (app/services/cushion_service.py)**
- `SafetyCushionService` - бизнес-логика подушки
- Зависимость от CalendarService для получения текущего баланса
- Чистый интерфейс для UI callbacks

**4. UI Layer (app/components/goals.py)**
- Карточка подушки (`build_cushion_card()`)
- Модал настройки (`build_cushion_modal()`)
- dcc.Store компоненты для state management
- Callbacks для CRUD операций

**5. CSS Layer (app/assets/goals.css)**
- Стили `.cushion-*` для карточки и модала
- Кастомный прогресс-бар с маркером порога

### Диаграмма взаимодействия

```
┌──────────────────────────────────────────────────────────────────┐
│                         /goals Page                               │
├──────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Cushion Card (build_cushion_card)              │ │
│  │  ┌─────────────────┐  ┌──────────────────────────────────┐ │ │
│  │  │  Unconfigured   │  │         Configured               │ │ │
│  │  │  [Настроить]    │  │  Progress Bar + Threshold Marker │ │ │
│  │  └────────┬────────┘  └────────────────┬─────────────────┘ │ │
│  │           │                             │                    │ │
│  │           └─────────┬───────────────────┘                    │ │
│  └─────────────────────┼───────────────────────────────────────┘ │
│                        │ click "Настроить"                       │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Cushion Modal (build_cushion_modal)            │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │  Target Input  │  Threshold Input (auto 30%)          │  │ │
│  │  ├───────────────────────────────────────────────────────┤  │ │
│  │  │  Collapsible: Scenario Calculator                     │  │ │
│  │  │   - Scenario 1-5 (name, min, max)                     │  │ │
│  │  │   - Mode: sum / max_scenario                          │  │ │
│  │  │   - [Применить] recommendation                        │  │ │
│  │  ├───────────────────────────────────────────────────────┤  │ │
│  │  │  [Сбросить]                    [Сохранить]            │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                        │ save
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│                    SafetyCushionService                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  get_settings(user_id) → CushionSettings                   │  │
│  │    └── CalendarService.get_balance_on_date(today)          │  │
│  │  update_settings(user_id, target, threshold, manual)       │  │
│  │  reset_settings(user_id)                                   │  │
│  │  calculate_recommendation(scenarios, mode)                 │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                        │ read/write
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│                    User Model (database.py)                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  + cushion_target: Decimal(10,2) = 0                       │  │
│  │  + cushion_threshold: Decimal(10,2) = 0                    │  │
│  │  + cushion_threshold_manual: Boolean = False               │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## Файловая структура

```
app/models/database.py           — +3 поля в User (cushion_target, cushion_threshold, cushion_threshold_manual)
app/schema/cushion.py            — НОВЫЙ: CushionSettings, CushionScenario TypedDicts
app/schema/__init__.py           — +export CushionSettings, CushionScenario
app/services/cushion_service.py  — НОВЫЙ: SafetyCushionService (~80 строк)
app/services/__init__.py         — +export SafetyCushionService
app/components/goals.py          — +build_cushion_card(), build_cushion_modal(), +7 callbacks (~200 строк)
app/assets/goals.css             — +стили .cushion-* (~60 строк)
tests/test_cushion_service.py    — НОВЫЙ: 7+ unit тестов
```

## Ключевые интерфейсы

```python
# app/schema/cushion.py
from decimal import Decimal
from typing import TypedDict


class CushionSettings(TypedDict):
    """Настройки подушки из User с вычисленными полями."""
    target: Decimal           # cushion_target
    threshold: Decimal        # cushion_threshold
    threshold_manual: bool    # cushion_threshold_manual
    current_amount: Decimal   # вычисляется через CalendarService
    progress: float           # вычисляется: min(current/target*100, 100) или 0
    is_configured: bool       # target > 0


class CushionScenario(TypedDict):
    """Сценарий для калькулятора (не сохраняется в БД)."""
    name: str
    min_amount: Decimal
    max_amount: Decimal


# app/services/cushion_service.py
from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session

from app.models.database import User
from app.schema.cushion import CushionSettings, CushionScenario
from app.services.calendar_service import CalendarService


class SafetyCushionService:
    """Сервис для работы с финансовой подушкой безопасности."""

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: SQLAlchemy сессия для работы с БД
        """
        ...

    def get_settings(self, user_id: int) -> CushionSettings:
        """Получает настройки подушки с вычисленными полями.

        Вычисляет current_amount через CalendarService.get_balance_on_date().
        Вычисляет progress с учетом edge cases (negative balance, over target).

        Args:
            user_id: ID пользователя

        Returns:
            CushionSettings: Настройки с вычисленными полями
        """
        ...

    def update_settings(
        self,
        user_id: int,
        target: Decimal,
        threshold: Decimal,
        threshold_manual: bool,
    ) -> None:
        """Обновляет настройки подушки.

        Args:
            user_id: ID пользователя
            target: Целевая сумма (>= 0)
            threshold: Минимальный порог (>= 0)
            threshold_manual: True если порог изменен вручную
        """
        ...

    def reset_settings(self, user_id: int) -> None:
        """Сбрасывает настройки подушки (обнуляет все поля)."""
        ...

    def calculate_recommendation(
        self,
        scenarios: list[CushionScenario],
        mode: str,  # "sum" | "max_scenario"
    ) -> Decimal:
        """Рассчитывает рекомендуемую цель по сценариям.

        Args:
            scenarios: Список сценариев
            mode: Режим расчета ("sum" для суммы, "max_scenario" для максимума)

        Returns:
            Decimal: Рекомендуемая сумма
        """
        ...


# app/components/goals.py - новые функции
def build_cushion_card(settings: CushionSettings) -> dbc.Card:
    """Строит карточку подушки безопасности.

    Args:
        settings: Настройки подушки из SafetyCushionService

    Returns:
        dbc.Card: Карточка с двумя состояниями (unconfigured/configured)
    """
    ...


def build_cushion_modal() -> dbc.Modal:
    """Строит модал настройки подушки.

    Включает:
    - Поле цели (число >= 0)
    - Поле порога (по умолчанию 30% от цели)
    - Collapsible секция с калькулятором сценариев
    - Кнопки Сбросить / Сохранить

    Returns:
        dbc.Modal: Модал настройки
    """
    ...


# Callbacks (7 штук):
# 1. open_cushion_modal() - открытие модала, загрузка текущих настроек
# 2. update_threshold_on_target_change() - автопересчет порога (30%)
# 3. add_scenario() - добавление сценария (Pattern-Matching)
# 4. remove_scenario() - удаление сценария (Pattern-Matching)
# 5. calculate_and_display_recommendation() - расчет рекомендации
# 6. apply_recommendation() - копирование в поле цели
# 7. save_or_reset_cushion() - сохранение/сброс настроек, закрытие модала
```

## Модель данных

### User (расширение)

```python
# app/models/database.py - добавить в класс User

class User(Base):
    # ... существующие поля ...

    # Финансовая подушка безопасности
    cushion_target = Column(Numeric(10, 2), default=0, nullable=False)
    cushion_threshold = Column(Numeric(10, 2), default=0, nullable=False)
    cushion_threshold_manual = Column(Boolean, default=False, nullable=False)
```

### dcc.Store компоненты (UI state)

```python
# В create_goals_layout() или goals.py

# Временные данные модала (не персистируются)
dcc.Store(id="cushion-scenarios-store", data=[])      # list[dict] - сценарии
dcc.Store(id="cushion-calc-mode", data="max_scenario") # str - режим расчета
dcc.Store(id="cushion-modal-trigger", data=0)         # int - триггер refresh
```

### Edge Cases (согласно спецификации)

| Случай | Поведение progress |
|--------|-------------------|
| `current_amount < 0` | `progress = 0.0` |
| `current_amount > target` | `progress = 100.0` (cap) |
| `target = 0` | `is_configured = False`, показать "Настроить" |
| `threshold > target` | Разрешено (пользователь может захотеть высокий порог) |

## Обработка ошибок

**Валидация в UI callbacks:**
- Цель: число >= 0, иначе показать toast "Введите положительное число"
- Порог: число >= 0, иначе показать toast
- Сценарий: name не пустое, max >= min

**Валидация в сервисе:**
- `get_settings`: Если user не найден - return CushionSettings с defaults (не raise)
- `update_settings`: Если user не найден - логировать warning, no-op

**Guard clauses в callbacks (ADR-003):**
```python
@callback(...)
def some_cushion_callback(...):
    # Guard #1: проверка реального клика
    if ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    # Guard #2: проверка triggered_id
    if not ctx.triggered_id:
        raise PreventUpdate

    # Business logic...
```

## План реализации

### Шаг 1: Schema + миграция БД (~15 мин)
**Файлы:** `app/models/database.py`
- Добавить 3 поля в User
- Удалить `data/finfocus.db`, перезапустить приложение для пересоздания

### Шаг 2: TypedDicts (~10 мин)
**Файлы:** `app/schema/cushion.py` (новый), `app/schema/__init__.py`
- Создать CushionSettings, CushionScenario
- Обновить экспорты

### Шаг 3: SafetyCushionService (~30 мин)
**Файлы:** `app/services/cushion_service.py` (новый), `app/services/__init__.py`
- Реализовать все 4 метода
- Интеграция с CalendarService

### Шаг 4: Карточка подушки (~30 мин)
**Файлы:** `app/components/goals.py`
- `build_cushion_card()` с двумя состояниями
- `_build_cushion_card_unconfigured()`, `_build_cushion_card_configured()`
- Интеграция в `create_goals_layout()` (вверху, над budget)

### Шаг 5: Модал настройки (~45 мин)
**Файлы:** `app/components/goals.py`
- `build_cushion_modal()` с полями и collapsible сценариями
- dcc.Store компоненты
- 7 callbacks с ADR-003 guard clauses

### Шаг 6: CSS стили (~20 мин)
**Файлы:** `app/assets/goals.css`
- `.cushion-card`, `.cushion-card-unconfigured`
- `.cushion-progress-bar`, `.cushion-threshold-marker`
- Responsive breakpoints

### Шаг 7: Unit тесты (~30 мин)
**Файлы:** `tests/test_cushion_service.py` (новый)
- 7+ тестов для SafetyCushionService
- Использовать фикстуры из conftest.py

### Шаг 8: Финализация (~15 мин)
- Black форматирование
- Flake8 проверка
- Pytest all tests
- Обновить ROADMAP.md, feature_progress.md

**Общее время:** ~3-4 часа

## Зависимости

**Существующие (без изменений):**
- `sqlalchemy` - ORM
- `dash`, `dash_bootstrap_components` - UI
- `loguru` - логирование

**Новые:** Не требуются

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| CalendarService.get_balance_on_date медленный | Низкая | Метод уже оптимизирован, используется в других местах |
| Конфликт CSS классов с существующими | Низкая | Префикс `.cushion-*` изолирует стили |
| Дублирование логики автопересчета порога | Средняя | Вынести в helper функцию `_calculate_default_threshold(target)` |
| Сложность модала с динамическими сценариями | Средняя | Pattern-Matching callbacks уже используются в проекте (quick-add chips) |
| Пользователь может ввести некорректные данные | Средняя | Валидация на уровне UI (disabled кнопка) + toast ошибки |
