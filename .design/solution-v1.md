# Solution v1: Множественные цели с приоритетным распределением взносов

## Обзор решения

Решение расширяет существующую систему целей, снимая ограничение D009 и добавляя сервис распределения рекомендуемых взносов. GoalService получает новые методы для работы с множественными целями, а UI переписывается для отображения списка целей с карточками. Новый PriorityAllocationService отвечает за расчет распределения бюджета накоплений между целями по приоритету.

## Архитектура

### Компоненты

**1. GoalService (расширение)**
- Снятие проверки ограничения одной активной цели
- Новый метод `update_priority()` для изменения приоритета
- Новый метод `reorder_priorities()` для переупорядочивания
- Обновление `get_all_by_user()` для возврата сортированного списка

**2. AllocationService (новый)**
Отдельный сервис для расчета распределения бюджета между целями:
- Принимает общий бюджет накоплений и список активных целей
- Распределяет средства по приоритету (жадный алгоритм)
- Возвращает рекомендуемый взнос для каждой цели

**3. Goals UI (рефакторинг)**
- Замена одиночной карточки на список карточек
- Добавление поля приоритета в формы создания/редактирования
- Новый блок сводной статистики
- Интеграция с AllocationService для отображения рекомендаций

**4. Dashboard (минорное обновление)**
- Изменение метода получения savings данных: агрегация по всем активным целям

### Диаграмма взаимодействия

```
+----------------+     +----------------+     +------------------+
|   Goals UI     |---->|  GoalService   |---->|    Database      |
| (goals.py)     |     | (goal_service) |     | (Goal, Contrib.) |
+----------------+     +----------------+     +------------------+
        |                     ^
        v                     |
+------------------+          |
| AllocationService|----------+
| (allocation_svc) |
+------------------+

Flow создания цели:
1. UI -> GoalService.create_goal() (без проверки лимита)
2. GoalService -> DB (INSERT Goal с priority)
3. GoalService -> auto-assign priority (max+1 если не указан)

Flow расчета рекомендаций:
1. UI загружает страницу
2. UI -> GoalService.get_all_by_user(status=ACTIVE)
3. UI -> AllocationService.calculate_allocation(goals, budget)
4. UI отображает карточки с рекомендуемыми взносами
```

## Файловая структура

```
app/services/allocation_service.py  — НОВЫЙ: расчет распределения бюджета
app/services/goal_service.py        — ИЗМЕНЕНИЕ: снять D009, добавить методы приоритетов
app/services/__init__.py            — ИЗМЕНЕНИЕ: экспорт AllocationService
app/components/goals.py             — ИЗМЕНЕНИЕ: рефакторинг UI для списка целей
app/components/dashboard.py         — ИЗМЕНЕНИЕ: агрегация по всем целям
app/assets/goals.css                — ИЗМЕНЕНИЕ: стили для списка карточек
tests/test_allocation_service.py    — НОВЫЙ: тесты распределения
tests/test_goal_service.py          — ИЗМЕНЕНИЕ: тесты множественных целей
```

## Ключевые интерфейсы

```python
# app/services/allocation_service.py

from decimal import Decimal
from typing import TypedDict


class AllocationResult(TypedDict):
    """Результат распределения для одной цели."""
    goal_id: int
    goal_name: str
    priority: int
    monthly_contribution_needed: Decimal  # сколько нужно по формуле
    allocated_amount: Decimal             # сколько выделено из бюджета
    is_fully_funded: bool                 # покрывает ли allocated нужды
    shortfall: Decimal                    # дефицит (если allocated < needed)


class AllocationSummary(TypedDict):
    """Сводка распределения бюджета."""
    total_budget: Decimal
    total_allocated: Decimal
    total_shortfall: Decimal
    results: list[AllocationResult]
    all_goals_funded: bool


class AllocationService:
    """Сервис распределения бюджета накоплений между целями.

    Использует жадный алгоритм: сначала полностью финансируется
    цель с приоритетом 1, затем остаток идет на приоритет 2 и т.д.
    """

    def calculate_allocation(
        self,
        goals: list[Goal],
        monthly_budget: Decimal,
    ) -> AllocationSummary:
        """Распределяет бюджет между целями по приоритету.

        Args:
            goals: Список активных целей (должны быть отсортированы по priority)
            monthly_budget: Общий месячный бюджет на накопления

        Returns:
            AllocationSummary: Сводка распределения с детализацией по целям
        """
        ...


# app/services/goal_service.py (дополнения)

class GoalService:
    # ... существующие методы ...

    def update_priority(self, goal_id: int, new_priority: int) -> Goal:
        """Изменяет приоритет цели.

        Автоматически сдвигает приоритеты других целей при конфликте.

        Args:
            goal_id: ID цели
            new_priority: Новый приоритет (1 = самый важный)

        Returns:
            Goal: Обновленная цель

        Raises:
            ValidationError: Если new_priority < 1 или цель не найдена
        """
        ...

    def reorder_priorities(self, user_id: int, goal_ids_in_order: list[int]) -> list[Goal]:
        """Переупорядочивает приоритеты целей согласно переданному порядку.

        Args:
            user_id: ID пользователя
            goal_ids_in_order: Список ID целей в желаемом порядке приоритетов
                              [0] получает priority=1, [1] получает priority=2, etc.

        Returns:
            list[Goal]: Обновленные цели

        Raises:
            ValidationError: Если какой-то goal_id не принадлежит пользователю
        """
        ...

    def get_next_priority(self, user_id: int) -> int:
        """Возвращает следующий доступный приоритет для новой цели.

        Returns:
            int: max(existing priorities) + 1, или 1 если целей нет
        """
        ...
```

## Модель данных

Модель Goal уже имеет поле priority:

```python
# app/models/database.py (существующее)
class Goal(Base):
    # ... existing fields ...
    priority = Column(Integer, default=1)  # Уже существует!
```

TypedDict для UI:

```python
# app/components/goals.py (расширение GoalDisplayData)

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
    priority: int                    # ДОБАВИТЬ
    allocated_amount: Decimal | None  # ДОБАВИТЬ - рекомендуемый взнос из бюджета


class GoalsSummary(TypedDict):
    """Сводка по всем активным целям."""
    total_goals_count: int
    total_target_amount: Decimal
    total_current_amount: Decimal
    total_progress_percentage: float
    monthly_budget: Decimal           # настройка пользователя
    total_shortfall: Decimal
    all_goals_on_track: bool
```

## Обработка ошибок

```python
# Использовать существующий ValidationError
from app.core import ValidationError

# Сценарии ошибок:
# 1. priority < 1 -> ValidationError("Приоритет должен быть не меньше 1")
# 2. goal_id не найден -> ValidationError(f"Цель с ID {goal_id} не найдена")
# 3. monthly_budget < 0 -> ValidationError("Бюджет накоплений не может быть отрицательным")

# UI показывает ошибки через существующий goal-error-alert
```

## План реализации

1. **Фаза 1: AllocationService** (~2ч)
   - Создать `app/services/allocation_service.py`
   - Реализовать `calculate_allocation()` с жадным алгоритмом
   - Написать unit тесты (5-7 тестов)
   - Обновить `app/services/__init__.py`

2. **Фаза 2: GoalService расширение** (~1.5ч)
   - Удалить проверку D009 из `create_goal()`
   - Добавить метод `update_priority()`
   - Добавить метод `reorder_priorities()`
   - Добавить метод `get_next_priority()`
   - Написать unit тесты (5-6 тестов)

3. **Фаза 3: Goals UI рефакторинг** (~4ч)
   - Переписать `_build_goal_card()` для работы со списком
   - Создать `_build_goals_list()` с карточками
   - Добавить поле приоритета в модалы создания/редактирования
   - Добавить сводную секцию вверху страницы
   - Обновить callbacks для работы с множественными целями
   - Использовать Pattern-Matching IDs для кнопок действий

4. **Фаза 4: Dashboard интеграция** (~1ч)
   - Обновить `DashboardService.get_overview_metrics()` для агрегации
   - Показывать общий savings прогресс по всем целям

5. **Фаза 5: Стили и polish** (~1ч)
   - Обновить `goals.css` для списка карточек
   - Адаптивность для мобильных
   - Финальное тестирование

**Общая оценка**: 10-12 часов

## Зависимости

Новые библиотеки не требуются. Используются существующие:
- SQLAlchemy 2.0.23 (ORM)
- Dash 2.17.1 + dbc 1.5.0 (UI)
- loguru (logging)
- decimal (точные вычисления)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| UI становится сложным с множеством карточек | Средняя | Пагинация или collapsible cards, показывать max 5 раскрытых |
| Pattern-Matching callbacks конфликтуют (как в D011) | Средняя | Использовать простые IDs с goal_id в data attribute, избегать ALL pattern |
| Производительность при 20+ целях | Низкая | Lazy loading, ограничить запрос 20 целями с пагинацией |
| Пользователь не понимает систему приоритетов | Средняя | Добавить tooltip с объяснением, показать пример распределения |
| Конфликт приоритетов при одновременном редактировании | Низкая | reorder_priorities() использует транзакцию, lock на уровне session |
