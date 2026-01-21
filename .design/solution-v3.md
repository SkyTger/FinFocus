# Solution v3: Множественные цели с приоритетным распределением взносов (Final)

## Обзор решения

Решение расширяет систему накопительных целей для поддержки множественных активных целей с приоритетами и автоматическим распределением бюджета накоплений. Включает: (1) снятие ограничения D009 в GoalService, (2) новый AllocationService для расчета рекомендуемых взносов, (3) обновление UI для списка целей с возможностью изменения приоритетов кнопками вверх/вниз, (4) модал настройки бюджета накоплений. Drag-and-drop отложен до verification spike.

## Учтённые замечания из критики v2

| Замечание из critique v2 | Как решено |
|--------------------------|------------|
| **#1** Выбор dash-draggable требует верификации | Fallback реализация через кнопки "Вверх"/"Вниз". Drag-and-drop опционально добавить позже после verification spike (1ч) |
| **#2** UserService создает circular dependency risk | UserService исключен. Метод `get_savings_budget()` и `update_savings_budget()` добавлены в GoalService (scope settings для целей, логически связаны) |
| **#3** Не описана миграция БД для monthly_savings_budget | Добавлен ALTER TABLE script для SQLite в Фазе 1 |
| **#4** UI-индикатор для "бюджет не настроен" | Добавлен info-alert при monthly_savings_budget=0 с призывом настроить |
| **#5** TypedDicts можно централизовать | Создан `app/types/goals.py` для переиспользования между services и components |
| **#6** Нет fallback для Goal.monthly_contribution=0 | Добавлено поле `skipped_reason` в AllocationResult |
| **#7** Test count превышает требования brief | Уточнено покрытие: 7 тестов AllocationService + 6 GoalService + 3 интеграционных = 16 (>10 минимальных) |

## Ответы на вопросы критика

1. **Verification spike для dash-draggable** — Реализуем MVP с кнопками "Вверх"/"Вниз" для изменения приоритета. После релиза можно провести 1-часовой spike для dash-draggable и добавить drag-and-drop как enhancement. Это снижает риск и не блокирует основной функционал.

2. **Миграция БД** — Добавлен скрипт:
   ```sql
   ALTER TABLE users ADD COLUMN monthly_savings_budget NUMERIC(10,2) DEFAULT 0 NOT NULL;
   ```
   Выполняется вручную или через `scripts/migrate_001_savings_budget.py` с проверкой существования колонки.

3. **Scope UserService** — UserService исключен из решения. Методы `get_savings_budget()` и `update_savings_budget()` добавлены в GoalService, т.к. логически связаны с настройками накопительных целей. Это устраняет риск circular dependency.

## Архитектура

### Компоненты

**1. User модель (расширение)**
- Новое поле `monthly_savings_budget: Numeric(10,2)` — бюджет накоплений в месяц
- Default = 0, nullable = False
- При = 0 UI показывает подсказку настроить бюджет

**2. GoalService (расширение)**
- Удалена проверка D009 (ограничение одной цели) из `create_goal()`
- Новые методы управления приоритетами: `get_next_priority()`, `update_priority()`, `reorder_priorities()`
- Новые методы бюджета: `get_savings_budget()`, `update_savings_budget()`
- Обновлена сортировка в `get_all_by_user()` — всегда по priority ASC

**3. AllocationService (новый)**
- Жадный алгоритм распределения бюджета по приоритетам
- Учитывает только ACTIVE цели с monthly_contribution > 0
- Возвращает AllocationSummary с детализацией и skipped_reason для пропущенных целей

**4. Types модуль (новый)**
- `app/types/goals.py` — централизованные TypedDicts для Goals
- AllocationResult, AllocationSummary, GoalDisplayData, GoalsSummary

**5. Goals UI (рефакторинг)**
- Список карточек целей вместо одной карточки
- Кнопки вверх/вниз для изменения приоритета
- Модал настройки бюджета накоплений
- Сводная секция с общим прогрессом и статусом распределения
- Info-alert при budget=0

**6. DashboardService (обновление)**
- Агрегация savings по всем активным целям
- Формула: `total = sum(all active)`, `progress = total_current / total_target * 100`

### Диаграмма взаимодействия

```
                    +------------------+
                    |    Goals UI      |
                    |   (goals.py)     |
                    +--------+---------+
                             |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
+------------------+ +------------------+ +------------------+
|   GoalService    | |AllocationService | |     Database     |
| (goal_service)   | | (allocation_svc) | | (User, Goal, ..)|
+------------------+ +------------------+ +------------------+
          |                  |                  ^
          |                  |                  |
          +------------------+------------------+
                             |
                    (session.query / flush)

Flow создания цели:
1. UI -> GoalService.create_goal() (БЕЗ проверки лимита D009)
2. GoalService.get_next_priority() -> max(active priorities) + 1
3. GoalService -> DB (INSERT Goal с auto-priority)
4. UI -> AllocationService.calculate_allocation()
5. UI обновляет список карточек с allocated_amount

Flow изменения приоритета (кнопки вверх/вниз):
1. UI клик "вверх" на цели с priority=2
2. UI -> GoalService.update_priority(goal_id, new_priority=1)
3. GoalService применяет shift-down алгоритм
4. UI -> AllocationService.calculate_allocation()
5. UI обновляет список и рекомендуемые взносы

Flow настройки бюджета:
1. UI открывает модал настроек
2. Пользователь вводит сумму
3. UI -> GoalService.update_savings_budget(user_id, budget)
4. UI -> AllocationService.calculate_allocation(goals, new_budget)
5. UI обновляет сводную секцию и карточки
```

## Файловая структура

```
app/models/database.py           — ИЗМЕНЕНИЕ: добавить User.monthly_savings_budget
app/types/__init__.py            — НОВЫЙ: экспорт типов
app/types/goals.py               — НОВЫЙ: централизованные TypedDicts
app/services/allocation_service.py  — НОВЫЙ: расчет распределения бюджета
app/services/goal_service.py     — ИЗМЕНЕНИЕ: снять D009, добавить методы приоритетов и бюджета
app/services/__init__.py         — ИЗМЕНЕНИЕ: экспорт новых сервисов и типов
app/components/goals.py          — ИЗМЕНЕНИЕ: рефакторинг UI для списка целей
app/components/dashboard.py      — ИЗМЕНЕНИЕ: агрегация по всем целям
app/assets/goals.css             — ИЗМЕНЕНИЕ: стили для списка карточек
scripts/migrate_001_savings_budget.py  — НОВЫЙ: миграция БД
tests/test_allocation_service.py — НОВЫЙ: тесты распределения (7 тестов)
tests/test_goal_service_priority.py   — НОВЫЙ: тесты приоритетов (6 тестов)
tests/test_goals_integration.py  — НОВЫЙ: интеграционные тесты (3 теста)
```

## Ключевые интерфейсы

```python
# app/models/database.py (дополнение к User)

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
    # При = 0 UI показывает подсказку настроить бюджет.

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    # ... relationships ...


# app/types/goals.py (НОВЫЙ)

from decimal import Decimal
from typing import TypedDict
from datetime import date


class AllocationResult(TypedDict):
    """Результат распределения для одной цели."""
    goal_id: int
    goal_name: str
    priority: int
    monthly_contribution_needed: Decimal  # Goal.monthly_contribution
    allocated_amount: Decimal             # сколько выделено из бюджета
    is_fully_funded: bool                 # allocated >= needed
    shortfall: Decimal                    # max(0, needed - allocated)
    skipped_reason: str | None            # "completed", "paused", "zero_contribution"


class AllocationSummary(TypedDict):
    """Сводка распределения бюджета."""
    total_budget: Decimal                 # User.monthly_savings_budget
    total_allocated: Decimal              # сумма allocated по активным целям
    total_needed: Decimal                 # сумма needed по активным целям
    total_shortfall: Decimal              # сумма shortfall по активным целям
    results: list[AllocationResult]       # детализация по всем целям
    all_goals_funded: bool                # total_shortfall == 0
    budget_not_set: bool                  # total_budget == 0


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
    priority: int
    allocated_amount: Decimal | None
    allocation_status: str | None  # "fully_funded", "partial", "not_funded", "skipped"


class GoalsSummary(TypedDict):
    """Сводка по всем активным целям."""
    total_goals_count: int
    active_goals_count: int
    total_target_amount: Decimal
    total_current_amount: Decimal
    total_progress_percentage: float
    monthly_budget: Decimal
    total_allocated: Decimal
    total_shortfall: Decimal
    all_goals_on_track: bool
    budget_not_set: bool


# app/services/allocation_service.py (НОВЫЙ)

from decimal import Decimal

from app.models.database import Goal, GoalStatus
from app.types.goals import AllocationResult, AllocationSummary


class AllocationService:
    """Сервис распределения бюджета накоплений между целями.

    Использует жадный алгоритм: цели обрабатываются в порядке priority (1, 2, 3...),
    каждая получает минимум из (needed, remaining_budget).
    Только ACTIVE цели с monthly_contribution > 0 получают allocation.
    """

    def calculate_allocation(
        self,
        goals: list[Goal],
        monthly_budget: Decimal,
    ) -> AllocationSummary:
        """Распределяет бюджет между целями по приоритету.

        Args:
            goals: Список целей (любого статуса), отсортированных по priority ASC
            monthly_budget: Общий месячный бюджет (User.monthly_savings_budget)

        Returns:
            AllocationSummary: Сводка с детализацией по каждой цели

        Algorithm:
            1. Фильтруем только ACTIVE цели с monthly_contribution > 0
            2. Сортируем по priority ASC (если не отсортированы)
            3. Для каждой цели: allocated = min(needed, remaining_budget)
            4. remaining_budget -= allocated
            5. Записываем shortfall = max(0, needed - allocated)
            6. PAUSED/COMPLETED цели получают allocated=0, skipped_reason

        Note:
            - Если goals пустой, возвращает summary с пустым results
            - Если budget <= 0, все цели получают allocated=0
            - budget_not_set=True если monthly_budget == 0
        """
        ...


# app/services/goal_service.py (дополнения)

class GoalService:
    """Сервис для операций с целями накопления."""

    # === НОВЫЕ МЕТОДЫ ПРИОРИТЕТОВ ===

    def get_next_priority(self, user_id: int) -> int:
        """Возвращает следующий приоритет для новой цели.

        Returns:
            int: max(priority среди ACTIVE целей) + 1, или 1 если нет активных
        """
        ...

    def update_priority(self, goal_id: int, new_priority: int) -> Goal:
        """Изменяет приоритет цели с автоматическим сдвигом конфликтующих.

        Алгоритм shift-down:
        1. Если new_priority < old_priority (повышение):
           - Сдвинуть цели с priority >= new AND < old на +1
        2. Если new_priority > old_priority (понижение):
           - Сдвинуть цели с priority > old AND <= new на -1
        3. Установить new_priority для цели

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
        """Переупорядочивает приоритеты АКТИВНЫХ целей (bulk update).

        Args:
            user_id: ID пользователя
            goal_ids_in_order: Список ID в желаемом порядке [0] -> priority=1

        Returns:
            list[Goal]: Обновленные цели

        Raises:
            ValidationError: При дубликатах или неполном списке
        """
        ...

    def move_priority_up(self, goal_id: int) -> Goal:
        """Перемещает цель на один приоритет вверх (уменьшает priority).

        Convenience method для UI кнопки "Вверх".
        Если уже priority=1, возвращает цель без изменений.
        """
        ...

    def move_priority_down(self, goal_id: int) -> Goal:
        """Перемещает цель на один приоритет вниз (увеличивает priority).

        Convenience method для UI кнопки "Вниз".
        Если уже последний приоритет, возвращает цель без изменений.
        """
        ...

    # === НОВЫЕ МЕТОДЫ БЮДЖЕТА (вместо UserService) ===

    def get_savings_budget(self, user_id: int) -> Decimal:
        """Получает месячный бюджет накоплений пользователя.

        Returns:
            Decimal: monthly_savings_budget или Decimal(0) если не найден
        """
        ...

    def update_savings_budget(self, user_id: int, budget: Decimal) -> None:
        """Обновляет бюджет накоплений пользователя.

        Args:
            user_id: ID пользователя
            budget: Новое значение (>= 0)

        Raises:
            ValidationError: Если budget < 0 или пользователь не найден
        """
        ...

    # === ИЗМЕНЕНИЕ create_goal ===

    def create_goal(
        self,
        user_id: int,
        name: str,
        target_amount: Decimal,
        target_date: date,
    ) -> Goal:
        """Создает цель с автоматическим назначением приоритета.

        ИЗМЕНЕНИЯ относительно текущей версии:
        - УДАЛЕНА проверка active_goals_count >= 1 (D009)
        - priority = get_next_priority(user_id) вместо hardcoded 1
        """
        ...
```

## Модель данных

### Изменения в User

```python
# app/models/database.py

class User(Base):
    """Модель пользователя.

    Attributes:
        starting_balance: Начальный баланс для расчета кассового календаря.
        monthly_savings_budget: Бюджет на накопления в месяц.
            Используется AllocationService для рекомендуемых взносов.
            При = 0 UI показывает подсказку настроить бюджет.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    starting_balance = Column(Numeric(10, 2), default=0, nullable=False)
    monthly_savings_budget = Column(Numeric(10, 2), default=0, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    # ... relationships ...
```

### Миграция SQLite

```python
# scripts/migrate_001_savings_budget.py

"""Миграция: добавление monthly_savings_budget в таблицу users."""

import sqlite3
from pathlib import Path


def migrate(db_path: str = "data/finfocus.db") -> bool:
    """Добавляет колонку monthly_savings_budget в users.

    Args:
        db_path: Путь к SQLite базе данных

    Returns:
        bool: True если миграция выполнена, False если колонка уже существует
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Проверяем существование колонки
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if "monthly_savings_budget" in columns:
        print("Колонка monthly_savings_budget уже существует")
        conn.close()
        return False

    # Добавляем колонку
    cursor.execute(
        """
        ALTER TABLE users
        ADD COLUMN monthly_savings_budget NUMERIC(10,2) DEFAULT 0 NOT NULL
        """
    )
    conn.commit()
    conn.close()
    print("Миграция выполнена: добавлена колонка monthly_savings_budget")
    return True


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/finfocus.db"
    migrate(db_path)
```

## Алгоритм распределения бюджета

```python
def calculate_allocation(
    self,
    goals: list[Goal],
    monthly_budget: Decimal,
) -> AllocationSummary:
    """Жадный алгоритм распределения бюджета."""
    results: list[AllocationResult] = []
    remaining_budget = max(monthly_budget, Decimal("0"))
    total_allocated = Decimal("0")
    total_needed = Decimal("0")
    total_shortfall = Decimal("0")

    # Сортируем по priority на случай если не отсортированы
    sorted_goals = sorted(goals, key=lambda g: g.priority)

    for goal in sorted_goals:
        needed = goal.monthly_contribution
        skipped_reason: str | None = None

        # Определяем причину пропуска
        if goal.status == GoalStatus.COMPLETED:
            skipped_reason = "completed"
            allocated = Decimal("0")
        elif goal.status == GoalStatus.PAUSED:
            skipped_reason = "paused"
            allocated = Decimal("0")
        elif needed <= 0:
            skipped_reason = "zero_contribution"
            allocated = Decimal("0")
        else:
            # Активная цель с положительным needed
            allocated = min(needed, remaining_budget)
            remaining_budget -= allocated
            total_needed += needed
            total_allocated += allocated
            shortfall = max(Decimal("0"), needed - allocated)
            total_shortfall += shortfall

        is_fully_funded = allocated >= needed if needed > 0 else True
        shortfall = max(Decimal("0"), needed - allocated) if skipped_reason is None else Decimal("0")

        results.append(AllocationResult(
            goal_id=goal.id,
            goal_name=goal.name,
            priority=goal.priority,
            monthly_contribution_needed=needed,
            allocated_amount=allocated,
            is_fully_funded=is_fully_funded,
            shortfall=shortfall,
            skipped_reason=skipped_reason,
        ))

    return AllocationSummary(
        total_budget=monthly_budget,
        total_allocated=total_allocated,
        total_needed=total_needed,
        total_shortfall=total_shortfall,
        results=results,
        all_goals_funded=total_shortfall == 0,
        budget_not_set=monthly_budget == 0,
    )
```

## Алгоритм сдвига приоритетов

### update_priority() — shift-down алгоритм

**Сценарий 1: Повышение приоритета (new < old)**

```
До:  B(1), C(2), D(3), A(4)
Цель A получает priority=2

1. old=4, new=2
2. Сдвигаем цели с priority >= 2 AND < 4 на +1:
   - C(2) -> C(3)
   - D(3) -> D(4)
3. A.priority = 2

После: B(1), A(2), C(3), D(4)
```

**Сценарий 2: Понижение приоритета (new > old)**

```
До:  A(1), B(2), C(3), D(4)
Цель A получает priority=3

1. old=1, new=3
2. Сдвигаем цели с priority > 1 AND <= 3 на -1:
   - B(2) -> B(1)
   - C(3) -> C(2)
3. A.priority = 3

После: B(1), C(2), A(3), D(4)
```

### move_priority_up/down — convenience methods

```python
def move_priority_up(self, goal_id: int) -> Goal:
    """Перемещает цель на один приоритет вверх."""
    goal = self.session.get(Goal, goal_id)
    if not goal:
        raise ValidationError(f"Цель с ID {goal_id} не найдена")

    if goal.priority <= 1:
        return goal  # Уже первый, ничего не делаем

    return self.update_priority(goal_id, goal.priority - 1)


def move_priority_down(self, goal_id: int) -> Goal:
    """Перемещает цель на один приоритет вниз."""
    goal = self.session.get(Goal, goal_id)
    if not goal:
        raise ValidationError(f"Цель с ID {goal_id} не найдена")

    # Находим максимальный приоритет среди ACTIVE целей
    max_priority = (
        self.session.query(func.max(Goal.priority))
        .filter_by(user_id=goal.user_id, status=GoalStatus.ACTIVE)
        .scalar()
    ) or 1

    if goal.priority >= max_priority:
        return goal  # Уже последний, ничего не делаем

    return self.update_priority(goal_id, goal.priority + 1)
```

## Обработка ошибок

```python
# Использовать существующий ValidationError из app.core

# AllocationService
# - Не бросает исключений, defensive programming
# - monthly_budget < 0 -> трактуется как 0
# - Неожиданные статусы -> skipped_reason="unknown"

# GoalService.update_priority()
# - new_priority < 1 -> ValidationError("Приоритет должен быть не меньше 1")
# - goal_id не найден -> ValidationError(f"Цель с ID {goal_id} не найдена")
# - goal не принадлежит user -> ValidationError("Цель не принадлежит пользователю")

# GoalService.reorder_priorities()
# - Дубликаты в списке -> ValidationError("Список содержит дубликаты")
# - Неполный список -> ValidationError("Список должен содержать все активные цели")
# - goal_id не принадлежит user -> ValidationError("Цель X не принадлежит пользователю")

# GoalService.update_savings_budget()
# - budget < 0 -> ValidationError("Бюджет накоплений не может быть отрицательным")
# - user_id не найден -> ValidationError("Пользователь не найден")

# UI обработка ошибок:
# - ValidationError показывается через goal-error-alert
# - При budget_not_set=True показывается info-alert с призывом настроить бюджет
# - Optimistic UI updates НЕ используются (проще и надежнее)
```

## План реализации

1. **Фаза 0: Миграция и Types** (~1ч)
   - Создать `scripts/migrate_001_savings_budget.py`
   - Создать `app/types/goals.py` с TypedDicts
   - Запустить миграцию на dev базе
   - Обновить `app/types/__init__.py`

2. **Фаза 1: GoalService расширение** (~2.5ч)
   - Добавить `monthly_savings_budget` в User модель
   - Удалить проверку D009 из `create_goal()`
   - Добавить `get_next_priority()` и использовать в `create_goal()`
   - Добавить `update_priority()` с shift-down алгоритмом
   - Добавить `reorder_priorities()` с валидацией
   - Добавить `move_priority_up()`, `move_priority_down()`
   - Добавить `get_savings_budget()`, `update_savings_budget()`
   - Написать unit тесты (6 тестов в test_goal_service_priority.py)

3. **Фаза 2: AllocationService** (~2ч)
   - Создать `app/services/allocation_service.py`
   - Реализовать `calculate_allocation()` с жадным алгоритмом
   - Написать unit тесты (7 тестов в test_allocation_service.py):
     - Пустой список целей
     - Одна цель, бюджет покрывает
     - Одна цель, бюджет не покрывает
     - Несколько целей, полное покрытие
     - Несколько целей, частичное покрытие
     - Нулевой бюджет (budget_not_set=True)
     - Цели с разными статусами (ACTIVE, PAUSED, COMPLETED)
   - Обновить `app/services/__init__.py`

4. **Фаза 3: Goals UI рефакторинг** (~5ч)
   - Создать `_build_goals_list()` вместо `_build_goal_card()`
   - Добавить кнопки "Вверх"/"Вниз" для каждой карточки
   - Добавить модал настройки бюджета накоплений
   - Добавить сводную секцию вверху страницы
   - Добавить info-alert при budget_not_set
   - Обновить callbacks для CRUD множественных целей
   - Интегрировать AllocationService для allocated_amount
   - Использовать TypedDicts из `app/types/goals.py`

5. **Фаза 4: Dashboard интеграция** (~1.5ч)
   - Обновить `DashboardService.get_overview_metrics()`:
     - `savings_current = sum(g.current_amount for g in active_goals)`
     - `savings_target = sum(g.target_amount for g in active_goals)`
     - `savings_progress = (current / target * 100) if target > 0 else 0`
     - `savings_name = f"{len(active_goals)} целей"` если > 1
   - Написать unit тесты для агрегации

6. **Фаза 5: Стили и интеграционные тесты** (~1.5ч)
   - Обновить `goals.css` для списка карточек
   - Добавить стили для кнопок приоритетов
   - Добавить стили для info-alert и сводной секции
   - Написать интеграционные тесты (3 теста)
   - Финальное тестирование всех сценариев

**Общая оценка**: 13.5-16 часов

## Зависимости

**Новые библиотеки**: НЕТ

**Существующие**:
- SQLAlchemy 2.0.23 (ORM)
- Dash 2.17.1 + dbc 1.5.0 (UI)
- loguru (logging)
- decimal (точные вычисления)

**Опционально для будущего enhancement**:
- `dash-draggable` — для drag-and-drop приоритетов (требует verification spike)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| UI становится перегруженным с 10+ целями | Средняя | Collapsible карточки, показывать только top-5, кнопка "Показать все" |
| Pattern-Matching callbacks конфликты | Низкая | Использовать простые IDs с `{"type": "goal-card", "index": goal_id}`, guard clauses из ADR-003 |
| Race condition при reorder | Низкая | Транзакция в session.flush(), кнопки вверх/вниз атомарны |
| Пользователь не понимает allocation | Средняя | Tooltip с объяснением, info-alert при budget_not_set |
| Миграция существующих данных | Очень низкая | `monthly_savings_budget` default=0, существующие цели с priority=1 работают |
| Кнопки вверх/вниз менее интуитивны чем drag-and-drop | Средняя | Достаточно для MVP. Drag-and-drop можно добавить позже после verification spike |

## Критерии приёмки (из brief)

- [x] Пользователь может создать 3+ активных цели одновременно
- [x] Цели отображаются в порядке приоритета (1 первый)
- [x] Изменение приоритета цели работает через UI (кнопки вверх/вниз)
- [x] Расчет распределения взносов корректно учитывает приоритеты
- [x] Dashboard показывает сводку по всем активным целям
- [x] Unit тесты покрывают новую логику распределения (16 > 10)
- [x] Существующие тесты проходят без регрессий
