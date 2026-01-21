# Solution v1: Savings Mode с применением множителя в AllocationService

## Обзор решения
Режим накоплений (`savings_mode`) добавляется как Enum поле в модель User. AllocationService расширяется параметром `savings_mode`, который применяет множитель к `monthly_contribution` каждой цели перед распределением бюджета. UI получает RadioItems селектор с тремя режимами и их описаниями.

## Архитектура

### Компоненты

**1. Модель данных (`app/models/database.py`)**
- Новый Enum `SavingsMode` с тремя значениями
- Поле `User.savings_mode` со значением по умолчанию `free`
- Константы множителей в отдельном модуле для переиспользования

**2. AllocationService (`app/services/allocation_service.py`)**
- Новый параметр `savings_mode: SavingsMode` в `calculate_allocation()`
- Множитель применяется к `monthly_contribution_needed` до распределения бюджета
- AllocationResult расширяется полем `adjusted_contribution` для отображения в UI

**3. GoalService (`app/services/goal_service.py`)**
- Методы `get_savings_mode(user_id)` и `update_savings_mode(user_id, mode)`
- Аналогично существующим методам для budget

**4. Goals UI (`app/components/goals.py`)**
- RadioItems селектор режима в summary section
- dcc.Store для хранения текущего режима
- Callback для изменения режима с пересчетом allocation

### Диаграмма взаимодействия
```
User clicks mode selector
        ↓
goals.py callback: save_savings_mode()
        ↓
GoalService.update_savings_mode(user_id, new_mode)
        ↓
DB commit (users.savings_mode updated)
        ↓
_recalculate_and_render(session, user_id, budget)
        ↓
AllocationService.calculate_allocation(goals, budget, savings_mode)
        ↓
Multiply each goal.monthly_contribution by MULTIPLIER[mode]
        ↓
Greedy allocation algorithm (unchanged)
        ↓
Return AllocationSummary with adjusted amounts
        ↓
UI updated with new allocation badges
```

## Файловая структура
```
app/models/database.py              — добавить SavingsMode Enum и поле User.savings_mode
app/services/allocation_service.py  — добавить параметр savings_mode, применить множитель
app/services/goal_service.py        — добавить get_savings_mode(), update_savings_mode()
app/services/__init__.py            — экспорт SavingsMode
app/schema/goals.py                 — добавить SavingsModeInfo TypedDict (опционально)
app/components/goals.py             — UI селектор, callbacks, dcc.Store
app/assets/goals.css                — стили для mode selector
scripts/migrate_002_savings_mode.py — миграция БД (новый файл)
tests/test_allocation_service.py    — новые тесты для режимов
tests/test_savings_mode.py          — unit тесты для GoalService методов (новый файл)
```

## Ключевые интерфейсы

```python
# app/models/database.py
from enum import Enum as PyEnum

class SavingsMode(PyEnum):
    """Режимы накоплений для целей."""
    FREE = "free"       # 100% — минимальные взносы
    MEDIUM = "medium"   # 115% — буфер для страховки
    STRICT = "strict"   # 150% — максимизация накоплений


# Константы множителей
SAVINGS_MODE_MULTIPLIERS: dict[SavingsMode, Decimal] = {
    SavingsMode.FREE: Decimal("1.0"),
    SavingsMode.MEDIUM: Decimal("1.15"),
    SavingsMode.STRICT: Decimal("1.5"),
}


class User(Base):
    # ... existing fields ...
    savings_mode = Column(
        Enum(SavingsMode),
        default=SavingsMode.FREE,
        nullable=False
    )


# app/services/allocation_service.py
class AllocationService:
    def calculate_allocation(
        self,
        goals: list[Goal],
        monthly_budget: Decimal,
        savings_mode: SavingsMode = SavingsMode.FREE,  # NEW PARAM
    ) -> AllocationSummary:
        """Распределяет бюджет с учетом режима накоплений."""
        ...


# app/services/goal_service.py
class GoalService:
    def get_savings_mode(self, user_id: int) -> SavingsMode:
        """Получает режим накоплений пользователя."""
        ...

    def update_savings_mode(self, user_id: int, mode: SavingsMode) -> None:
        """Обновляет режим накоплений пользователя."""
        ...
```

## Модель данных

**Расширение AllocationResult (опционально)**
```python
class AllocationResult(TypedDict):
    # ... existing fields ...
    adjusted_contribution: Decimal  # monthly_contribution * multiplier
    savings_mode_multiplier: Decimal  # примененный множитель
```

**SavingsModeInfo для UI**
```python
class SavingsModeInfo(TypedDict):
    """Информация о режиме накоплений для UI."""
    mode: str  # "free", "medium", "strict"
    label: str  # "Свободный", "Средний", "Строгий"
    multiplier: Decimal  # 1.0, 1.15, 1.5
    description: str  # Описание для пользователя
```

## Обработка ошибок

**Валидация в GoalService.update_savings_mode()**
- Проверка существования пользователя (ValidationError)
- Проверка корректности значения mode (ValidationError)

**AllocationService.calculate_allocation()**
- Default значение `SavingsMode.FREE` если параметр не передан
- Обратная совместимость с существующими вызовами

## План реализации

1. **Миграция БД и модель** (1 шаг)
   - Создать `SavingsMode` Enum в `database.py`
   - Добавить поле `User.savings_mode` с default='free'
   - Создать `scripts/migrate_002_savings_mode.py`
   - Добавить константы `SAVINGS_MODE_MULTIPLIERS`

2. **GoalService расширение** (1 шаг)
   - Добавить `get_savings_mode()` метод
   - Добавить `update_savings_mode()` метод
   - Unit тесты в `tests/test_savings_mode.py`

3. **AllocationService модификация** (1 шаг)
   - Добавить параметр `savings_mode` в `calculate_allocation()`
   - Применить множитель к `monthly_needed` в алгоритме
   - Обновить AllocationResult (опционально: `adjusted_contribution`)
   - Тесты для трех режимов в `test_allocation_service.py`

4. **UI компоненты** (2 шага)
   - Добавить dcc.Store для savings_mode
   - Создать `_build_mode_selector()` функцию
   - Интегрировать в summary section
   - Callback `save_savings_mode()` с пересчетом allocation

5. **Стили и финализация** (1 шаг)
   - CSS для mode selector в `goals.css`
   - Интеграционные тесты
   - Документация в ROADMAP.md

## Зависимости
Новые библиотеки не требуются. Используются существующие:
- SQLAlchemy (Enum column type)
- Dash Bootstrap Components (RadioItems)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Режим не применяется при первой загрузке | Средняя | Инициализировать mode из БД в `load_goal_data()` callback |
| Обратная несовместимость с существующими вызовами AllocationService | Низкая | Default parameter `savings_mode=SavingsMode.FREE` |
| Миграция не отрабатывает на существующих данных | Низкая | Idempotent check + default='free' для существующих users |
| UI перегружен информацией | Средняя | Компактный RadioItems с tooltip описаниями |

## Критичные файлы для реализации

1. `app/models/database.py` — SavingsMode Enum + User.savings_mode
2. `app/services/allocation_service.py` — применение множителя
3. `app/components/goals.py` — UI selector и callbacks
4. `app/services/goal_service.py` — методы get/update savings_mode
5. `scripts/migrate_002_savings_mode.py` — миграция БД
