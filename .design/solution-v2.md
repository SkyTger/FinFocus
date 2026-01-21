# Solution v2: Множественные цели с приоритетным распределением взносов (Revised)

## Обзор решения

Решение расширяет систему накопительных целей, добавляя поддержку множественных целей с приоритетами и автоматическим распределением бюджета накоплений. Ключевые изменения относительно v1: добавлено поле `monthly_savings_budget` в модель User, детально описан алгоритм сдвига приоритетов при изменении, определено поведение PAUSED целей (не участвуют в allocation), и UI реализует drag-and-drop для управления порядком приоритетов.

## Учтённые замечания из критики v1

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🔴 **1. Отсутствует хранение monthly_savings_budget** | Добавлено поле `User.monthly_savings_budget` в модель (Numeric(10,2), default=0). UI для редактирования — модал настроек на странице Goals |
| 🔴 **2. Не определена логика сдвига приоритетов** | Детальный алгоритм shift-down с примером: при установке priority=2 все цели с priority>=2 сдвигаются на +1 |
| 🟡 **3. GoalsSummary.monthly_budget не связан с источником** | Явно указан data flow: User.monthly_savings_budget → GoalsSummary.monthly_budget → UI |
| 🟡 **4. Dashboard интеграция неполна** | Формула агрегации: total_target = sum(all goals), total_current = sum(all goals), progress = total_current/total_target |
| 🟡 **5. reorder_priorities() может нарушить консистентность** | Добавлена валидация: список должен содержать ВСЕ активные цели, проверка дубликатов, PAUSED цели сохраняют priority |
| 🟡 **6. Нет UI для ввода приоритета при создании** | Решение: auto-assign (max+1) при создании, drag-and-drop для изменения порядка |

## Ответы на вопросы критика

1. **Вопрос:** monthly_savings_budget — хранить в User модели или вводить каждый раз?
   **Ответ:** Хранить в User модели (добавить поле `monthly_savings_budget = Column(Numeric(10, 2), default=0)`). Это позволяет рассчитывать рекомендуемые взносы при загрузке страницы без ввода пользователем. Редактирование через модал настроек на странице Goals.

2. **Вопрос:** Участвуют ли PAUSED цели в allocation? Сохраняют ли priority при reorder?
   **Ответ:** PAUSED цели НЕ участвуют в allocation (только ACTIVE). При reorder_priorities() PAUSED цели сохраняют свой текущий priority и не входят в список для переупорядочивания. Это логично: приостановленные цели временно "заморожены", но при возобновлении вернутся с тем же приоритетом.

3. **Вопрос:** UI для приоритетов — числовой ввод, drag-and-drop или кнопки?
   **Ответ:** Drag-and-drop для карточек целей. Интуитивно понятен, визуален, не требует знания текущих значений priority. Используем библиотеку `dash-draggable` или нативные HTML5 drag events через callbacks.

4. **Вопрос:** Приоритет при создании — автоназначение или UI выбор?
   **Ответ:** Auto-assign (max+1). Новая цель получает самый низкий приоритет. Пользователь может изменить порядок через drag-and-drop после создания. Это упрощает UX создания цели и избегает конфликтов.

## Архитектура

### Компоненты

**1. User модель (расширение)**
- Новое поле `monthly_savings_budget: Decimal` для хранения бюджета накоплений
- Default = 0 (пользователь должен настроить)

**2. GoalService (расширение)**
- Снятие проверки D009 (ограничение одной цели)
- Новый метод `update_priority()` с алгоритмом shift-down
- Новый метод `reorder_priorities()` с валидацией
- Новый метод `get_next_priority()` для auto-assign
- Обновление сортировки в `get_all_by_user()`

**3. AllocationService (новый)**
- Жадный алгоритм распределения бюджета по приоритетам
- Учитывает только ACTIVE цели
- Возвращает AllocationSummary с детализацией по каждой цели

**4. UserService (новый)**
- Метод `update_savings_budget()` для изменения monthly_savings_budget
- Метод `get_savings_budget()` для получения текущего значения

**5. Goals UI (рефакторинг)**
- Список карточек с drag-and-drop для приоритетов
- Модал настроек бюджета накоплений
- Сводная секция с общим прогрессом
- Pattern-Matching IDs с простыми идентификаторами (не ALL)

**6. DashboardService (обновление)**
- Агрегация savings по всем активным целям

### Диаграмма взаимодействия

```
+------------------+     +------------------+     +------------------+
|    Goals UI      |---->|   GoalService    |---->|     Database     |
|   (goals.py)     |     | (goal_service)   |     | (User, Goal, ..)|
+------------------+     +------------------+     +------------------+
        |                        ^
        |                        |
        v                        |
+------------------+             |
|AllocationService |-------------+
| (allocation_svc) |
+------------------+
        ^
        |
+------------------+
|   UserService    |---- User.monthly_savings_budget
|  (user_service)  |
+------------------+

Flow создания цели:
1. UI -> GoalService.create_goal() (без проверки лимита)
2. GoalService.get_next_priority() -> max + 1
3. GoalService -> DB (INSERT Goal с auto-priority)
4. UI обновляет список карточек

Flow изменения приоритета (drag-and-drop):
1. UI получает новый порядок карточек
2. UI -> GoalService.reorder_priorities(goal_ids_in_order)
3. GoalService валидирует список (все ACTIVE цели, без дубликатов)
4. GoalService обновляет priorities в транзакции
5. UI -> AllocationService.calculate_allocation()
6. UI обновляет рекомендуемые взносы на карточках

Flow расчета рекомендаций:
1. UI загружается
2. UI -> UserService.get_savings_budget()
3. UI -> GoalService.get_all_by_user(status=ACTIVE)
4. UI -> AllocationService.calculate_allocation(goals, budget)
5. UI отображает карточки с allocated_amount
```

## Файловая структура

```
app/models/database.py           — ИЗМЕНЕНИЕ: добавить User.monthly_savings_budget
app/services/allocation_service.py  — НОВЫЙ: расчет распределения бюджета
app/services/user_service.py     — НОВЫЙ: управление настройками пользователя
app/services/goal_service.py     — ИЗМЕНЕНИЕ: снять D009, добавить методы приоритетов
app/services/__init__.py         — ИЗМЕНЕНИЕ: экспорт новых сервисов
app/components/goals.py          — ИЗМЕНЕНИЕ: рефакторинг UI для списка целей
app/components/dashboard.py      — ИЗМЕНЕНИЕ: агрегация по всем целям
app/assets/goals.css             — ИЗМЕНЕНИЕ: стили для списка карточек, drag-and-drop
tests/test_allocation_service.py — НОВЫЙ: тесты распределения (min 7)
tests/test_goal_service.py       — ИЗМЕНЕНИЕ: тесты множественных целей (min 6)
tests/test_user_service.py       — НОВЫЙ: тесты настроек пользователя (min 3)
```

## Ключевые интерфейсы

```python
# app/models/database.py (дополнение к User)

class User(Base):
    # ... existing fields ...
    monthly_savings_budget = Column(Numeric(10, 2), default=0, nullable=False)
    # Бюджет на накопления в месяц. Используется AllocationService
    # для расчета рекомендуемых взносов по целям.


# app/services/user_service.py (НОВЫЙ)

class UserService:
    """Сервис для управления настройками пользователя."""

    def __init__(self, session: Session):
        self.session = session

    def get_savings_budget(self, user_id: int) -> Decimal:
        """Получает месячный бюджет накоплений пользователя.

        Returns:
            Decimal: monthly_savings_budget или 0 если пользователь не найден
        """
        ...

    def update_savings_budget(
        self, user_id: int, budget: Decimal
    ) -> User:
        """Обновляет бюджет накоплений.

        Args:
            user_id: ID пользователя
            budget: Новое значение бюджета (>= 0)

        Raises:
            ValidationError: Если budget < 0 или пользователь не найден
        """
        ...


# app/services/allocation_service.py (НОВЫЙ)

from decimal import Decimal
from typing import TypedDict

from app.models.database import Goal


class AllocationResult(TypedDict):
    """Результат распределения для одной цели."""
    goal_id: int
    goal_name: str
    priority: int
    monthly_contribution_needed: Decimal  # сколько нужно по формуле Goal.monthly_contribution
    allocated_amount: Decimal             # сколько выделено из бюджета
    is_fully_funded: bool                 # allocated >= needed
    shortfall: Decimal                    # max(0, needed - allocated)


class AllocationSummary(TypedDict):
    """Сводка распределения бюджета."""
    total_budget: Decimal                 # User.monthly_savings_budget
    total_allocated: Decimal              # сумма allocated по всем целям
    total_needed: Decimal                 # сумма needed по всем целям
    total_shortfall: Decimal              # сумма shortfall по всем целям
    results: list[AllocationResult]       # детализация по целям
    all_goals_funded: bool                # total_shortfall == 0


class AllocationService:
    """Сервис распределения бюджета накоплений между целями.

    Использует жадный алгоритм: цели обрабатываются в порядке priority (1, 2, 3...),
    каждая получает минимум из (needed, remaining_budget).
    Только ACTIVE цели участвуют в распределении.
    """

    def calculate_allocation(
        self,
        goals: list[Goal],
        monthly_budget: Decimal,
    ) -> AllocationSummary:
        """Распределяет бюджет между целями по приоритету.

        Args:
            goals: Список АКТИВНЫХ целей, отсортированных по priority ASC
            monthly_budget: Общий месячный бюджет (User.monthly_savings_budget)

        Returns:
            AllocationSummary: Сводка с детализацией по каждой цели

        Note:
            - Если goals пустой, возвращает summary с пустым results
            - Если budget <= 0, все цели получают allocated=0
            - Цели с monthly_contribution_needed=0 (достигнутые) пропускаются
        """
        ...


# app/services/goal_service.py (дополнения)

class GoalService:
    # ... существующие методы (create_goal без D009 проверки) ...

    def update_priority(self, goal_id: int, new_priority: int) -> Goal:
        """Изменяет приоритет цели с автоматическим сдвигом конфликтующих.

        Алгоритм shift-down:
        1. Получить текущий priority цели (old_priority)
        2. Если new_priority == old_priority, ничего не делать
        3. Если new_priority < old_priority (повышение приоритета):
           - Сдвинуть все цели с priority >= new_priority AND < old_priority на +1
        4. Если new_priority > old_priority (понижение приоритета):
           - Сдвинуть все цели с priority > old_priority AND <= new_priority на -1
        5. Установить new_priority для цели

        Args:
            goal_id: ID цели
            new_priority: Новый приоритет (>= 1)

        Returns:
            Goal: Обновленная цель

        Raises:
            ValidationError: Если new_priority < 1 или цель не найдена
        """
        ...

    def reorder_priorities(
        self, user_id: int, goal_ids_in_order: list[int]
    ) -> list[Goal]:
        """Переупорядочивает приоритеты АКТИВНЫХ целей.

        Args:
            user_id: ID пользователя
            goal_ids_in_order: Список ID целей в желаемом порядке
                              [0] -> priority=1, [1] -> priority=2, etc.

        Returns:
            list[Goal]: Обновленные цели в новом порядке

        Raises:
            ValidationError:
                - Если список содержит дубликаты
                - Если список не содержит ВСЕ активные цели пользователя
                - Если какой-то goal_id не принадлежит пользователю

        Note:
            PAUSED/COMPLETED цели НЕ должны быть в списке и сохраняют свой priority.
        """
        ...

    def get_next_priority(self, user_id: int) -> int:
        """Возвращает следующий приоритет для новой цели.

        Returns:
            int: max(priority среди ACTIVE целей) + 1, или 1 если нет активных
        """
        ...

    def create_goal(
        self,
        user_id: int,
        name: str,
        target_amount: Decimal,
        target_date: date,
    ) -> Goal:
        """Создает цель с автоматическим назначением приоритета.

        Изменения относительно текущей версии:
        - УБРАНА проверка active_goals_count >= 1 (D009)
        - priority = get_next_priority(user_id) вместо hardcoded 1
        """
        ...
```

## Модель данных

### Изменения в User

```python
# app/models/database.py

class User(Base):
    """Модель пользователя."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    starting_balance = Column(Numeric(10, 2), default=0, nullable=False)

    # НОВОЕ ПОЛЕ
    monthly_savings_budget = Column(Numeric(10, 2), default=0, nullable=False)
    # Ежемесячный бюджет на накопления.
    # Используется AllocationService для расчета рекомендуемых взносов.
    # default=0 означает "не настроено" - UI покажет подсказку.

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    # ... relationships ...
```

### TypedDicts для UI

```python
# app/components/goals.py (расширение)

class GoalDisplayData(TypedDict):
    """Данные для отображения цели в UI."""
    id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date
    status: str
    progress_percentage: float
    monthly_contribution: Decimal  # нужно по формуле
    days_remaining: int
    is_completed: bool
    priority: int                  # ДОБАВИТЬ
    allocated_amount: Decimal | None  # ДОБАВИТЬ - рекомендуемый взнос из бюджета


class GoalsSummary(TypedDict):
    """Сводка по всем активным целям."""
    total_goals_count: int
    total_target_amount: Decimal       # sum(target_amount) всех активных
    total_current_amount: Decimal      # sum(current_amount) всех активных
    total_progress_percentage: float   # total_current / total_target * 100
    monthly_budget: Decimal            # User.monthly_savings_budget
    total_allocated: Decimal           # сумма распределенного бюджета
    total_shortfall: Decimal           # дефицит бюджета
    all_goals_on_track: bool           # all_goals_funded
```

## Алгоритм сдвига приоритетов

### update_priority() — shift-down алгоритм

**Сценарий 1: Повышение приоритета (new < old)**

```
До:  B(1), C(2), D(3), A(4)
Цель A получает priority=2

1. old_priority=4, new_priority=2
2. Сдвигаем все с priority >= 2 AND < 4 на +1:
   - C(2) -> C(3)
   - D(3) -> D(4)
   Результат: B(1), C(3), D(4), A(4)

3. Устанавливаем A.priority = 2
   Результат: B(1), A(2), C(3), D(4)

После: B(1), A(2), C(3), D(4)
```

**Сценарий 2: Понижение приоритета (new > old)**

```
До:  A(1), B(2), C(3), D(4)
Цель A получает priority=3

1. old_priority=1, new_priority=3
2. Сдвигаем все с priority > 1 AND <= 3 на -1:
   - B(2) -> B(1)
   - C(3) -> C(2)
   Результат: A(1), B(1), C(2), D(4)

3. Устанавливаем A.priority = 3
   Результат: B(1), C(2), A(3), D(4)

После: B(1), C(2), A(3), D(4)
```

### reorder_priorities() — bulk update

```python
def reorder_priorities(self, user_id: int, goal_ids_in_order: list[int]) -> list[Goal]:
    # Валидация
    if len(goal_ids_in_order) != len(set(goal_ids_in_order)):
        raise ValidationError("Список содержит дубликаты goal_id")

    active_goals = self.get_all_by_user(user_id, status=GoalStatus.ACTIVE)
    active_ids = {g.id for g in active_goals}

    if set(goal_ids_in_order) != active_ids:
        raise ValidationError(
            "Список должен содержать ровно все активные цели пользователя"
        )

    # Bulk update priorities
    goals_dict = {g.id: g for g in active_goals}
    updated = []

    for new_priority, goal_id in enumerate(goal_ids_in_order, start=1):
        goal = goals_dict[goal_id]
        goal.priority = new_priority
        updated.append(goal)

    self.session.flush()
    return updated
```

## Обработка ошибок

```python
# Использовать существующий ValidationError из app.core

# Сценарии ошибок:

# AllocationService
# - monthly_budget < 0 -> ValidationError("Бюджет накоплений не может быть отрицательным")
# - goals содержит не ACTIVE -> логируем warning, пропускаем (defensive)

# GoalService.update_priority()
# - new_priority < 1 -> ValidationError("Приоритет должен быть не меньше 1")
# - goal_id не найден -> ValidationError(f"Цель с ID {goal_id} не найдена")
# - goal не принадлежит user -> ValidationError("Цель не принадлежит пользователю")

# GoalService.reorder_priorities()
# - Дубликаты в списке -> ValidationError("Список содержит дубликаты")
# - Неполный список -> ValidationError("Список должен содержать все активные цели")
# - goal_id не принадлежит user -> ValidationError("Цель X не принадлежит пользователю")

# UserService.update_savings_budget()
# - budget < 0 -> ValidationError("Бюджет накоплений не может быть отрицательным")
# - user_id не найден -> ValidationError("Пользователь не найден")

# UI обработка ошибок:
# - Все ValidationError показываются через goal-error-alert
# - Timeout на drag-and-drop операции (если запрос завис > 5 сек)
# - Optimistic UI update с откатом при ошибке сервера
```

## План реализации

1. **Фаза 1: Модель и UserService** (~1.5ч)
   - Добавить `monthly_savings_budget` в User модель
   - Создать `app/services/user_service.py` с методами get/update
   - Написать unit тесты (3 теста)
   - Обновить `app/services/__init__.py`

2. **Фаза 2: AllocationService** (~2ч)
   - Создать `app/services/allocation_service.py`
   - Реализовать `calculate_allocation()` с жадным алгоритмом
   - Написать unit тесты (7 тестов):
     - Пустой список целей
     - Одна цель, бюджет покрывает
     - Одна цель, бюджет не покрывает
     - Несколько целей, полное покрытие
     - Несколько целей, частичное покрытие
     - Нулевой бюджет
     - Цель с monthly_contribution=0 (достигнута)
   - Обновить `app/services/__init__.py`

3. **Фаза 3: GoalService расширение** (~2.5ч)
   - Удалить проверку D009 из `create_goal()`
   - Добавить `get_next_priority()` и использовать в `create_goal()`
   - Добавить `update_priority()` с shift-down алгоритмом
   - Добавить `reorder_priorities()` с валидацией
   - Написать unit тесты (6 тестов):
     - create_goal() назначает auto priority
     - update_priority() повышение приоритета
     - update_priority() понижение приоритета
     - reorder_priorities() валидация дубликатов
     - reorder_priorities() валидация неполного списка
     - reorder_priorities() успешное переупорядочивание

4. **Фаза 4: Goals UI рефакторинг** (~5ч)
   - Создать `_build_goals_list()` с карточками и drag-and-drop
   - Добавить модал настройки бюджета накоплений
   - Добавить сводную секцию вверху страницы
   - Обновить callbacks для CRUD множественных целей
   - Интегрировать AllocationService для показа рекомендуемых взносов
   - Использовать Pattern-Matching IDs с `{"type": "goal-card", "index": goal_id}`

5. **Фаза 5: Dashboard интеграция** (~1.5ч)
   - Обновить `DashboardService.get_overview_metrics()`:
     - `savings_current = sum(g.current_amount for g in active_goals)`
     - `savings_target = sum(g.target_amount for g in active_goals)`
     - `savings_progress = (savings_current / savings_target * 100) if savings_target > 0 else 0`
     - `savings_name = f"{len(active_goals)} целей"` если > 1
   - Написать unit тесты для агрегации

6. **Фаза 6: Стили и polish** (~1.5ч)
   - Обновить `goals.css` для drag-and-drop визуализации
   - Добавить индикатор перетаскивания
   - Адаптивность для мобильных (touch events)
   - Финальное тестирование всех сценариев

**Общая оценка**: 14-16 часов

## Зависимости

Новые библиотеки:
- **dash-draggable** (опционально) — для drag-and-drop. Альтернатива: нативные HTML5 drag events через clientside callbacks.

Существующие:
- SQLAlchemy 2.0.23 (ORM)
- Dash 2.17.1 + dbc 1.5.0 (UI)
- loguru (logging)
- decimal (точные вычисления)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Drag-and-drop сложен в Dash | Средняя | Альтернатива: кнопки вверх/вниз для изменения приоритета. Или использовать `dash-draggable` компонент |
| UI становится перегруженным с 10+ целями | Средняя | Collapsible карточки, показывать только top-5, кнопка "Показать все" |
| Pattern-Matching callbacks конфликты | Низкая | Использовать простые IDs с `{"type": "...", "index": goal_id}`, guard clauses из ADR-003 |
| Race condition при reorder | Низкая | Транзакция в session.flush(), optimistic locking если нужно |
| Пользователь не понимает allocation | Средняя | Tooltip с объяснением, показать формулу в модале настроек |
| Миграция существующих данных | Низкая | `monthly_savings_budget` default=0, существующие цели с priority=1 работают |
