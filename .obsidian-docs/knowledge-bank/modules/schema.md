---
name: schema
description: TypedDict-контракты FinFocus (app/schema/) — Goals, Onboarding, Dashboard, MoneyLayers
type: reference
originSessionId: -
---

# modules/schema.md

## Суть
Централизованные TypedDicts для типизации данных между сервисами и UI компонентами

## Ключевые файлы
- `app/schema/__init__.py` - экспорты
- `app/schema/goals.py` - TypedDicts для накопительных целей
- `app/schema/onboarding.py` - UserProfile, OnboardingStatus (расширен в протоколе 0024)
- `app/schema/money_layers.py` - контракт модели «свободно/платежи/резерв» (протокол 0028)

## Цели модуля

**Создан в**: Протокол 0006 (Multiple Goals)

**Причина**: Избежать дублирования TypedDict определений между сервисами и UI

**Принцип**: Single Source of Truth для структур данных

## TypedDicts для Goals

### AllocationResult
Результат распределения бюджета для одной цели.

```python
class AllocationResult(TypedDict):
    goal_id: int
    goal_name: str
    priority: int
    monthly_contribution_needed: Decimal   # Base monthly_contribution * savings_mode multiplier
    allocated_amount: Decimal
    is_fully_funded: bool
    shortfall: Decimal
    skipped_reason: str | None             # "completed" | "paused" | "zero_contribution" | None
```

**Использование**: Возвращается AllocationService.calculate_allocation()

### AllocationSummary
Сводка распределения бюджета по всем целям.

```python
class AllocationSummary(TypedDict):
    total_budget: Decimal                  # User.monthly_savings_budget
    total_allocated: Decimal
    total_needed: Decimal
    total_shortfall: Decimal
    results: list[AllocationResult]        # Детализация по каждой цели
    all_goals_funded: bool                 # total_shortfall == 0
    budget_not_set: bool                   # total_budget == 0
```

**Использование**: Возвращается AllocationService.calculate_allocation(), используется в Goals UI

### GoalDisplayData
Данные для отображения одной цели в UI.

```python
class GoalDisplayData(TypedDict):
    id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date
    status: str                            # "active" | "completed" | "paused"
    progress_percentage: float
    monthly_contribution: Decimal
    days_remaining: int
    is_completed: bool
    priority: int
    allocated_amount: Decimal | None       # Из AllocationResult или None
    allocation_status: str | None          # "fully_funded" | "partial" | "not_funded" | "skipped" | None
```

**Использование**: Формируется в Goals UI для отображения карточки цели

### GoalsSummary
Сводка по всем активным целям для Summary Section.

```python
class GoalsSummary(TypedDict):
    total_goals_count: int
    active_goals_count: int
    total_target_amount: Decimal
    total_current_amount: Decimal
    total_progress_percentage: float
    monthly_budget: Decimal
    total_allocated: Decimal
    total_shortfall: Decimal
    all_goals_on_track: bool               # Нет дефицитов
    budget_not_set: bool                   # Бюджет не настроен
```

**Использование**: Формируется в Goals UI для Summary Section

### RedistributionPreview (Протокол 0008)
Preview перераспределения бюджета при достижении цели.

```python
class RedistributionPreview(TypedDict):
    completed_goal_id: int
    completed_goal_name: str
    freed_budget: Decimal                  # Освободившийся бюджет
    old_allocation: AllocationSummary      # Allocation ДО завершения цели
    new_allocation: AllocationSummary | None  # Allocation ПОСЛЕ (None если нет оставшихся целей)
    has_remaining_goals: bool              # Есть ли активные цели для перераспределения
    calculation_time_ms: float             # NFR-2: timing для мониторинга
```

**Использование**: Возвращается RedistributionService.calculate_redistribution_preview(), используется в Redistribution Modal UI

### RedistributionEvent (Протокол 0008)
Аудит-лог события перераспределения.

```python
class RedistributionEvent(TypedDict):
    event_type: str                        # "redistribution"
    action: str                            # "confirmed" | "declined"
    timestamp: str                         # ISO format
    user_id: int
    completed_goal_id: int
    completed_goal_name: str
    freed_budget: str                      # Decimal as string
    has_remaining_goals: bool
    old_total_allocated: str | None        # Decimal as string
    new_total_allocated: str | None        # Decimal as string
```

**Использование**: Формируется RedistributionService.log_redistribution_event() для loguru аудита

## Важное

**JSON-совместимость**:
- Decimal → строка при сериализации в dcc.Store
- date → ISO строка при сериализации
- Для Decimal используются утилиты из `app/utils/formatters.py`

**Где используются**:
- `app/services/allocation_service.py` — AllocationResult, AllocationSummary
- `app/services/redistribution_service.py` — RedistributionPreview, RedistributionEvent
- `app/components/goals.py` — все 6 TypedDicts
- `app/utils/serializers.py` — serialize/deserialize для RedistributionPreview
- `tests/` — для типизации тестовых данных

## TypedDicts для Onboarding / Profile (Протокол 0024)

### UserProfile
Данные профиля пользователя.

```python
class UserProfile(TypedDict):
    name: str        # Имя пользователя (обязательно, непустое)
    avatar_id: str   # ID аватара из app/config/avatars.py
```

**Использование**: возвращается `OnboardingService.get_profile()`, принимается `OnboardingService.update_profile()`

### OnboardingStatus (расширен)
```python
class OnboardingStatus(TypedDict):
    first_launch: bool
    starting_balance: Decimal
    name: str | None       # NEW (протокол 0024)
    avatar_id: str | None  # NEW (протокол 0024)
```

**Использование**: `OnboardingService.get_status()`, полоска-меню (`render_nav_rail_slot`) и окно профиля для reactive обновлений

---

## TypedDicts для Dashboard (Протокол 0022)

### BalanceStatus
Status классификатор для баланса.

```python
BalanceStatus = Literal["ok", "attention", "risk"]

# Константы порогов
BALANCE_RISK_THRESHOLD = Decimal("5000")      # Критичный порог
BALANCE_ATTENTION_THRESHOLD = Decimal("15000") # Порог предупреждения
```

### DailyCashflowData
Данные одного дня для дневного графика.

```python
class DailyBalancePoint(TypedDict):
    date: str              # ISO format
    balance: str           # Decimal as string
    status: BalanceStatus  # "ok" | "attention" | "risk"

class DailyCashflow(TypedDict):
    date: str              # ISO format
    income: str            # Decimal as string
    expense: str           # Decimal as string
    balance_point: DailyBalancePoint
```

### MonthlyCashflowData
Агрегированные данные месяца для графика.

```python
class MonthlyCashflowData(TypedDict):
    month: str                          # "2026-02"
    month_label: str                    # "Фев"
    daily_cashflow: list[DailyCashflow] # Дневные данные
    start_balance: str                  # Decimal as string
    end_balance: str                    # Decimal as string
    min_balance: str                    # Decimal as string
    min_balance_date: str               # ISO format
    total_income: str                   # Decimal as string
    total_expense: str                  # Decimal as string
```

**Использование**: Возвращается DashboardService.get_daily_cashflow()

### YearlyCashflowData
Агрегированные данные года для графика.

```python
class MonthlyCashflow(TypedDict):
    month: str           # "2026-02"
    month_label: str     # "Фев"
    income: str          # Decimal as string (month total)
    expense: str         # Decimal as string (month total)
    end_balance: str     # Decimal as string (EOM balance)
    status: BalanceStatus

class YearlyCashflowData(TypedDict):
    year: int
    monthly_data: list[MonthlyCashflow]  # 12 месяцев
    start_balance: str                   # Decimal as string (Jan 1)
    end_balance: str                     # Decimal as string (Dec 31)
    min_balance: str                     # Decimal as string (year minimum)
    min_balance_date: str                # ISO format
    total_income: str                    # Decimal as string
    total_expense: str                   # Decimal as string
```

**Использование**: Возвращается DashboardService.get_yearly_cashflow()

**Критичные детали**:
- **BalanceStatus классификация**: ok (≥ 15000), attention (5000-15000), risk (< 5000)
- **min_balance tracking**: для маркера минимума на графике
- **end_balance**: для Year mode — баланс на конец месяца (EOM)
- **Decimal serialization**: все денежные суммы → string для JSON

**Замечание (протокол 0028)**: этот блок TypedDicts обслуживал старый
дневной/годовой график дашборда (`_build_daily_cashflow_chart` и др.),
который протокол 0028 удалил вместе с переключателем Месяц/Год. Типы
здесь оставлены как есть — DashboardService их не потерял, но UI-слой,
их использовавший, больше не существует (заменён `MoneyLayersData`,
см. ниже).

## TypedDicts для MoneyLayers (Протокол 0028)

`app/schema/money_layers.py` — контракт модели «свободно/платежи/резерв»
(Epic-11 «щиток», кусок 1 из 3). Докстринг модуля прямо предупреждает:
контракт спроектирован под кусок 1, стабильность до куска 2
(карточки-двери) не гарантируется.

### LayerKey / константы

```python
LayerKey = Literal["free", "payments", "reserve"]

WINDOW_DAYS = 45                  # длина окна оси графика
MAX_MILESTONES_IN_WINDOW = 3      # макс. вех целей внутри окна (+1 beyond_window)
MAX_X_TICKS = 11                  # ПОТОЛОК подписей оси X (не цель — k = ceil(len/MAX_X_TICKS))

LAYER_COLORS: dict[LayerKey, str] = {
    "free": "#2ecc71", "payments": "#f0b775", "reserve": "#3498db"
}
LAYER_LABELS: dict[LayerKey, str] = {
    "free": "Свободно", "payments": "Платежи", "reserve": "Резерв целей и подушки"
}
```

### Horizons (NamedTuple)
`collect_start` (1-е число месяца reference_date) / `window_end`
(reference_date + 44) / `payments_end` (конец месяца reference_date).

### DayLayers
```python
class DayLayers(TypedDict):
    date: date
    free: Decimal
    payments: Decimal
    reserve: Decimal                # ФАКТ дня после каскада _split_day
    reserve_configured: Decimal     # ДО каскада — для честного тултипа
    forecast_balance: Decimal
```
Инвариант: `free + payments + reserve == forecast_balance` (AC-3).

### UpcomingPayment / GoalMilestone / TodaySlice
- `UpcomingPayment` — date/amount (всегда > 0)/description/category_name/is_recurring — для тултипа легенды «Платежи»
- `GoalMilestone` — goal_id/name/target_date/target_amount/progress_percent/beyond_window — материализован из ORM Goal ВНУТРИ сессии (иначе DetachedInstanceError на `progress_percentage`)
- `TodaySlice` — free/balance/payments/reserve на reference_date, источник цифр шапки. **Полей вердикта (level/text/dip_threshold) НЕТ** — решение владельца, шапка не выносит оценок

### MoneyLayersData — корневой контракт
```python
class MoneyLayersData(TypedDict):
    days: list[DayLayers]
    today: TodaySlice
    min_free: Decimal
    min_free_date: date
    upcoming_payments: list[UpcomingPayment]
    milestones: list[GoalMilestone]
    reference_date: date
    window_end: date
    payments_end: date
    cushion_threshold: Decimal
    goals_reserve_today: Decimal
    reserve_configured_today: Decimal
    degraded: bool           # часть модели посчитана fail-open
    is_empty: bool           # данных нет ВООБЩЕ (не «нули в окне»)
    window_is_flat: bool     # данные есть, но окно без операций — график всё равно рисуется
```

**Критичные детали**:
- Вердикт-типов (`ok`/`dip`/`problem`) в контракте НЕТ — снят решением
  владельца, `min_free` используется только маркером минимума на графике
- `is_empty` != `window_is_flat`: первое — «нет данных вообще» (чистая
  база, пустое состояние вместо графика), второе — «данные есть, окно
  пустое» (график рисуется плоской стопкой)
- Единственный источник цифр и для шапки, и для графика — оба строятся
  из одного `MoneyLayersData` за один вызов `get_money_layers`

## TypedDicts для Panel Cards (Протокол 0030)

**Файл**: `app/schema/panel.py`

Контракты пяти карточек-дверей щитка: `CardStatus` (Enum OK/EMPTY/FAILED —
единственный источник правды отрисовки карточки), `CalendarDaySlice` /
`CalendarCardData` (ДВА окошка — сегодня и завтра; «вчера» убрано решением
владельца 2026-08-26), `GoalsCardData`, `OperationRow` / `OperationsCardData`
(только материализованные операции — решение владельца 2026-08-25),
`AnalyticsCategorySlice` / `AnalyticsCardData` (только расходы; объявленное
расхождение с месячным слоем «Платежи» графика), `WishlistCardRow` /
`WishlistCardData`, `PanelData` (без `is_new_user` — общего признака
пустоты нет, каждая карточка честна сама за себя).

**`TRANSACTION_KIND_MAP`** — сведение шести значений `TransactionType` к
трём `kind` ("income"/"expense"/"other"): savings_* → expense (деньги
уходят из остатка, та же трактовка, что у слоя «Платежи»); transfer и
adjustment → other (направление определяется суммой, не типом). Неизвестное
значение → "other" через `.get()`; тест на все шесть значений покраснеет
при добавлении седьмого.

Константы: `OPERATIONS_PER_GROUP = 3`, `MINI_STRUCTURE_CATEGORIES = 3`.
Константы-порога усиления маркера просадки НЕТ — прямое `dip_free <= 0`
(факт знака, решение владельца).

## Критичные решения

**Протокол 0006**: Централизация TypedDicts в отдельном модуле для DRY

**TypedDict > dataclass**: JSON-совместимость критична для dcc.Store в Dash

**Протокол 0008**: Добавлены RedistributionPreview и RedistributionEvent для перераспределения бюджета

**Протокол 0022**: Добавлены Dashboard TypedDicts для дневного/годового cashflow графика

**Протокол 0024**: Добавлены UserProfile TypedDict; OnboardingStatus расширен полями name и avatar_id

**Протокол 0028**: Добавлен `app/schema/money_layers.py` —
контракт модели «свободно/платежи/резерв» (Epic-11, кусок 1). Новый
модуль, не расширение существующего — реэкспорт добавлен в
`app/schema/__init__.py` (12 имён + блок в `__all__`)

**Serialization**: Decimal → str через `app/utils/serializers.py` для JSON-совместимости

---

Детали: `services.md` (DashboardService, MoneyLayersService, AllocationService, RedistributionService), `ui-components.md` (Dashboard-щиток, Goals Component), `utils.md` (Serializers)
