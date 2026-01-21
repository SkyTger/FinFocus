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

## Важное

**JSON-совместимость**:
- Decimal → строка при сериализации в dcc.Store
- date → ISO строка при сериализации
- Для Decimal используются утилиты из `app/utils/formatters.py`

**Где используются**:
- `app/services/allocation_service.py` — AllocationResult, AllocationSummary
- `app/components/goals.py` — все 4 TypedDicts
- `tests/` — для типизации тестовых данных

## Критичные решения

**Протокол 0006**: Централизация TypedDicts в отдельном модуле для DRY

**TypedDict > dataclass**: JSON-совместимость критична для dcc.Store в Dash

---

Детали: `services.md` (AllocationService), `ui-components.md` (Goals Component)
