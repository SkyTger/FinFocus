# modules/schema.md

## Суть
Централизованные TypedDicts для типизации данных между сервисами и UI компонентами

## Ключевые файлы
- `app/schema/__init__.py` - экспорты
- `app/schema/goals.py` - TypedDicts для накопительных целей

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

## Критичные решения

**Протокол 0006**: Централизация TypedDicts в отдельном модуле для DRY

**TypedDict > dataclass**: JSON-совместимость критична для dcc.Store в Dash

**Протокол 0008**: Добавлены RedistributionPreview и RedistributionEvent для перераспределения бюджета

**Протокол 0022**: Добавлены Dashboard TypedDicts для дневного/годового cashflow графика

**Serialization**: Decimal → str через `app/utils/serializers.py` для JSON-совместимости

---

Детали: `services.md` (DashboardService, AllocationService, RedistributionService), `ui-components.md` (Dashboard Component, Goals Component), `utils.md` (Serializers)
