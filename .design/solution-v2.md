# Solution v2: Savings Mode с детализированной интеграцией и точным применением множителя

## Обзор решения
Режим накоплений (`savings_mode`) добавляется как String поле в модель User (вместо SQLAlchemy Enum для совместимости с SQLite миграциями). AllocationService расширяется параметром `savings_mode`, который применяет множитель к `monthly_contribution` каждой цели внутри цикла распределения. Константы множителей хранятся непосредственно в `allocation_service.py`. UI получает RadioItems селектор рядом с кнопкой "Настроить бюджет" в summary section.

## Архитектура

### Компоненты

**1. Модель данных (`app/models/database.py`)**
- Поле `User.savings_mode` как `Column(String(20), default="free", nullable=False)`
- Выбран String вместо SQLAlchemy Enum для упрощения SQLite миграций (ALTER TABLE не поддерживает Enum)
- Валидация значений выполняется на уровне сервиса

**2. AllocationService (`app/services/allocation_service.py`)**
- Новый параметр `savings_mode: str = "free"` в `calculate_allocation()`
- Константы `SAVINGS_MODE_MULTIPLIERS` определены в этом модуле
- Множитель применяется внутри цикла: `monthly_needed = goal.monthly_contribution * multiplier`
- `monthly_contribution_needed` в AllocationResult содержит adjusted (умноженное) значение

**3. GoalService (`app/services/goal_service.py`)**
- Методы `get_savings_mode(user_id)` и `update_savings_mode(user_id, mode)`
- TODO комментарий о переносе в отдельный UserService
- Валидация mode через константу `VALID_SAVINGS_MODES`

**4. Goals UI (`app/components/goals.py`)**
- `dcc.Store(id="goals-savings-mode-store")` для хранения текущего режима
- RadioItems селектор в summary section
- Callback `save_savings_mode()` с пересчетом allocation
- Функция `_recalculate_and_render()` расширена параметром `savings_mode`

### Диаграмма взаимодействия
```
Page Load (/goals)
        ↓
load_goal_data() callback
        ↓
GoalService.get_savings_mode(user_id) → current_mode
        ↓
_recalculate_and_render(session, user_id, budget, savings_mode=current_mode)
        ↓
AllocationService.calculate_allocation(goals, budget, savings_mode)
        ↓
for goal in sorted_goals:
    multiplier = SAVINGS_MODE_MULTIPLIERS[savings_mode]
    monthly_needed = goal.monthly_contribution * multiplier  ← Точка применения
    ...
        ↓
Return AllocationSummary (monthly_contribution_needed = adjusted)
        ↓
UI updated, stores initialized (budget, allocation, savings_mode)

---

User changes mode (RadioItems)
        ↓
save_savings_mode() callback
        ↓
GoalService.update_savings_mode(user_id, new_mode)
        ↓
DB commit (users.savings_mode updated)
        ↓
_recalculate_and_render(session, user_id, budget, savings_mode=new_mode)
        ↓
UI updated with new allocation badges
```

## Файловая структура
```
app/models/database.py              — +User.savings_mode (String, default="free")
app/services/allocation_service.py  — +SAVINGS_MODE_MULTIPLIERS, +параметр savings_mode
app/services/goal_service.py        — +get_savings_mode(), +update_savings_mode(), +VALID_SAVINGS_MODES
app/services/__init__.py            — экспорт VALID_SAVINGS_MODES
app/components/goals.py             — +dcc.Store, +RadioItems, +callback, обновить _recalculate_and_render
app/assets/goals.css                — +стили для mode selector (~15 строк)
scripts/migrate_002_savings_mode.py — миграция БД (новый файл)
tests/test_allocation_service.py    — +3 теста для режимов
tests/test_savings_mode.py          — +5 тестов для GoalService методов (новый файл)
```

## Ключевые интерфейсы

```python
# app/models/database.py
class User(Base):
    # ... existing fields ...
    savings_mode = Column(String(20), default="free", nullable=False)
    # Допустимые значения: "free", "medium", "strict"
    # Валидация на уровне GoalService.update_savings_mode()


# app/services/allocation_service.py
from decimal import Decimal

# Константы бизнес-логики — рядом с алгоритмом использования
SAVINGS_MODE_MULTIPLIERS: dict[str, Decimal] = {
    "free": Decimal("1.0"),     # 100% — минимальные взносы
    "medium": Decimal("1.15"),  # 115% — буфер для страховки
    "strict": Decimal("1.5"),   # 150% — максимизация накоплений
}


class AllocationService:
    def calculate_allocation(
        self,
        goals: list[Goal],
        monthly_budget: Decimal,
        savings_mode: str = "free",  # NEW: default для обратной совместимости
    ) -> AllocationSummary:
        """Распределяет бюджет с учетом режима накоплений.

        Args:
            goals: Список целей для распределения.
            monthly_budget: Месячный бюджет на накопления.
            savings_mode: Режим накоплений ("free", "medium", "strict").

        Returns:
            AllocationSummary: Сводка распределения.
            monthly_contribution_needed в результатах содержит ADJUSTED значение.
        """
        ...


# app/services/goal_service.py
# TODO: Перенести методы User в отдельный UserService при рефакторинге
VALID_SAVINGS_MODES = {"free", "medium", "strict"}


class GoalService:
    def get_savings_mode(self, user_id: int) -> str:
        """Получает режим накоплений пользователя.

        Returns:
            str: "free", "medium" или "strict"

        Raises:
            ValidationError: Если пользователь не найден
        """
        ...

    def update_savings_mode(self, user_id: int, mode: str) -> None:
        """Обновляет режим накоплений пользователя.

        Args:
            mode: Новый режим ("free", "medium", "strict")

        Raises:
            ValidationError: Если пользователь не найден или mode невалидный
        """
        if mode not in VALID_SAVINGS_MODES:
            raise ValidationError(
                f"Недопустимый режим: {mode}. Допустимые: {VALID_SAVINGS_MODES}",
                field="savings_mode"
            )
        ...


# app/components/goals.py
def _recalculate_and_render(
    session,
    user_id: int,
    budget: Decimal,
    savings_mode: str = "free",  # NEW PARAM
):
    """Пересчитывает allocation и возвращает обновленный UI.

    Args:
        savings_mode: Режим накоплений для применения множителя
    """
    ...
    allocation_summary = allocation_service.calculate_allocation(
        goals=all_goals,
        monthly_budget=budget,
        savings_mode=savings_mode,  # Передаем режим
    )
    ...
```

## Модель данных

**Точка применения множителя в AllocationService.calculate_allocation():**
```python
# Внутри цикла for goal in sorted_goals:
# Получаем множитель для текущего режима
multiplier = SAVINGS_MODE_MULTIPLIERS.get(savings_mode, Decimal("1.0"))

# Применяем множитель к базовому monthly_contribution
base_monthly = goal.monthly_contribution  # Property из ORM модели
monthly_needed = base_monthly * multiplier  # ADJUSTED значение

# Далее monthly_needed используется для:
# 1. Расчета allocated = min(monthly_needed, remaining_budget)
# 2. Формирования result.monthly_contribution_needed = monthly_needed (adjusted!)
# 3. Подсчета total_needed += monthly_needed
# 4. Расчета shortfall = max(0, monthly_needed - allocated)
```

**MODE_OPTIONS для UI (константа в goals.py):**
```python
MODE_OPTIONS = {
    "free": {
        "label": "Свободный (100%)",
        "description": "Минимальные взносы точно по графику",
    },
    "medium": {
        "label": "Средний (115%)",
        "description": "+15% буфер для непредвиденных расходов",
    },
    "strict": {
        "label": "Строгий (150%)",
        "description": "Максимизация накоплений для раннего достижения",
    },
}
```

## Обработка ошибок

**GoalService.get_savings_mode():**
- ValidationError если User не существует (аналогично get_savings_budget)
- Default fallback не нужен — поле имеет NOT NULL DEFAULT "free"

**GoalService.update_savings_mode():**
- ValidationError если User не существует
- ValidationError если mode не в VALID_SAVINGS_MODES

**AllocationService.calculate_allocation():**
- Fallback на Decimal("1.0") если savings_mode не найден в MULTIPLIERS
- Логирование warning при неизвестном режиме (для обнаружения багов)
- Обратная совместимость через default parameter

**UI:**
- RadioItems не позволяет выбрать невалидный режим (options фиксированы)
- Graceful handling если savings_mode из БД невалидный (показать как "free")

## План реализации

1. **Миграция БД и модель** (1 шаг)
   - Добавить `User.savings_mode = Column(String(20), default="free", nullable=False)`
   - Создать `scripts/migrate_002_savings_mode.py` (по образцу migrate_001)
   - Idempotent check через `column_exists()`
   - Тест миграции (1 unit test)

2. **GoalService расширение** (1 шаг)
   - Добавить константу `VALID_SAVINGS_MODES = {"free", "medium", "strict"}`
   - Добавить `get_savings_mode(user_id)` метод
   - Добавить `update_savings_mode(user_id, mode)` метод с валидацией
   - 4 unit теста в `tests/test_savings_mode.py`:
     - test_get_savings_mode_default
     - test_get_savings_mode_user_not_found
     - test_update_savings_mode_success
     - test_update_savings_mode_invalid_mode

3. **AllocationService модификация** (1 шаг)
   - Добавить `SAVINGS_MODE_MULTIPLIERS` константу в модуль
   - Добавить параметр `savings_mode: str = "free"` в `calculate_allocation()`
   - Применить множитель внутри цикла к `goal.monthly_contribution`
   - `monthly_contribution_needed` в результате содержит adjusted значение
   - 3 unit теста:
     - test_allocation_free_mode (множитель 1.0)
     - test_allocation_medium_mode (множитель 1.15)
     - test_allocation_strict_mode (множитель 1.5)
   - Убедиться что существующие тесты проходят (default="free")

4. **UI компоненты (часть 1: stores и helper)** (1 шаг)
   - Добавить `dcc.Store(id="goals-savings-mode-store", data=None)` в layout
   - Добавить `MODE_OPTIONS` константу для UI
   - Расширить `_recalculate_and_render()` параметром `savings_mode`
   - Обновить `load_goal_data()`:
     - Читать `savings_mode = service.get_savings_mode(user_id)`
     - Передавать в `_recalculate_and_render()`
     - Инициализировать `goals-savings-mode-store`

5. **UI компоненты (часть 2: selector и callback)** (1 шаг)
   - Создать `_build_mode_selector()` функцию (RadioItems)
   - Интегрировать в `_build_summary_section()` рядом с кнопкой бюджета
   - Создать callback `save_savings_mode()`:
     - Input: RadioItems value change
     - State: budget store
     - Actions: update_savings_mode(), _recalculate_and_render()
     - Output: goal-card-container, goals-savings-mode-store, goals-allocation-store
   - Обновить все callbacks что вызывают `_recalculate_and_render()`:
     - create_goal()
     - save_budget()
     - add_contribution()
     - toggle_goal_status()
     - change_priority()
     - delete_goal()

6. **Стили и интеграционные тесты** (1 шаг)
   - CSS для mode selector в `goals.css` (~15 строк)
   - Интеграционный тест: смена режима пересчитывает allocation
   - Обновить ROADMAP.md (отметить фичу как завершенную)

## Зависимости
Новые библиотеки не требуются. Используются существующие:
- SQLAlchemy (String column type вместо Enum для простоты миграций)
- Dash Bootstrap Components (RadioItems для selector)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Режим не применяется при первой загрузке | Средняя | `load_goal_data()` читает mode из БД и передает в `_recalculate_and_render()` |
| Обратная несовместимость с существующими вызовами AllocationService | Низкая | Default parameter `savings_mode="free"` |
| Миграция не отрабатывает на существующих данных | Низкая | Idempotent check + default="free" для существующих users |
| Callbacks не получают актуальный savings_mode | Средняя | dcc.Store + чтение из БД в каждом callback что вызывает _recalculate_and_render |
| UI перегружен информацией | Низкая | Компактный RadioItems с inline descriptions |
| Невалидный режим в БД | Низкая | Fallback на "free" + logging warning |

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🟡 Неопределено место применения множителя в алгоритме | Явно указано: внутри цикла `for goal in sorted_goals`, применяется к `goal.monthly_contribution`, результат `monthly_needed` используется для allocation. Диаграмма и код показывают точное место. |
| 🟡 SAVINGS_MODE_MULTIPLIERS - неопределено место хранения | Константы размещены непосредственно в `allocation_service.py` рядом с алгоритмом использования. Это обеспечивает cohesion и избегает импорта из database.py. |
| 🟡 Размещение методов savings_mode в GoalService | Оставлено в GoalService с TODO комментарием о переносе в UserService. Это осознанное решение для MVP - минимизация изменений архитектуры. |
| 🟡 Отсутствует обновление существующих вызовов AllocationService | Явно описано: расширить `_recalculate_and_render()` параметром `savings_mode`, обновить все 7 callbacks что её вызывают. План реализации содержит список callbacks. |
| 🟢 SavingsModeInfo TypedDict - избыточен | Убран. Используется простой dict `MODE_OPTIONS` в UI коде. |
| 🟢 adjusted_contribution в AllocationResult - спорная необходимость | Убран. `monthly_contribution_needed` УЖЕ содержит adjusted значение. Дополнительные поля не нужны. |
| 🟢 Риск "Режим не применяется при первой загрузке" - недостаточно раскрыт | Полностью расписан flow: `load_goal_data()` читает mode из БД, передает в `_recalculate_and_render()`, сохраняет в `goals-savings-mode-store`. |

## Ответы на вопросы критика

1. **Вопрос:** Отображение базового vs adjusted взноса — нужно ли UI показывать оба значения?
   **Ответ:** Нет, для MVP достаточно показывать только итоговый (adjusted) взнос. Это упрощает UI и не перегружает пользователя. Базовый взнос можно вычислить делением на множитель, но это усложнение без явной пользы. Если потребуется в будущем — можно добавить tooltip с базовым значением.

2. **Вопрос:** Изменение режима и активные цели — нужно ли показывать предупреждение если бюджет теперь не покрывает все цели?
   **Ответ:** Нет специального предупреждения не нужно. Существующий UI уже показывает shortfall alert ("Недостаток бюджета: X руб") в summary section когда `all_goals_funded=False`. Этого достаточно — пользователь сразу видит последствия изменения режима. Дополнительный confirm dialog создаст friction без пользы.

3. **Вопрос:** Tooltips vs inline descriptions для RadioItems?
   **Ответ:** Inline текст под каждой опцией. Причины: 1) Tooltips на мобильных устройствах работают плохо (нет hover). 2) Информация важная, не должна быть скрыта. 3) Три режима с короткими описаниями (~10 слов каждый) не перегружают UI. Формат: `Свободный (100%)\nМинимальные взносы точно по графику`.

## Критичные файлы для реализации

1. `app/services/allocation_service.py` — SAVINGS_MODE_MULTIPLIERS + параметр savings_mode
2. `app/services/goal_service.py` — методы get/update savings_mode + VALID_SAVINGS_MODES
3. `app/components/goals.py` — расширить _recalculate_and_render(), добавить mode selector, обновить все callbacks
4. `app/models/database.py` — User.savings_mode String column
5. `scripts/migrate_002_savings_mode.py` — миграция БД (по образцу migrate_001)
