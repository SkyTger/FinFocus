# Шаг 1: Utils и GoalService Extension

## Briefing
- **Цель:** Создать модуль `formatters.py` с общими функциями форматирования, добавить метод `get_contributions()` в GoalService, обновить импорты в transactions.py для использования общих formatters.
- **Ключевые файлы:**
  - `app/utils/__init__.py` (создать)
  - `app/utils/formatters.py` (создать)
  - `app/services/goal_service.py` (модифицировать)
  - `app/components/transactions.py` (модифицировать)
  - `tests/test_goal_service.py` (модифицировать)
- **Additional info:**
  - Функции `format_amount`, `format_date`, `parse_date_safe` уже реализованы в transactions.py (строки 18-57) — нужно вынести их в formatters.py
  - Добавить новую функцию `format_days_remaining()` для Goals UI
  - GoalContribution импортируется из `app.models.database`

## Sub-tasks

### 1.1 Создать модуль utils

1. **Создать директорию:** `mkdir -p app/utils/`

2. **Создать `app/utils/__init__.py`:**
```python
"""Утилиты и вспомогательные функции."""

from app.utils.formatters import (
    format_amount,
    format_date,
    format_days_remaining,
    parse_date_safe,
)

__all__ = [
    "format_amount",
    "format_date",
    "format_days_remaining",
    "parse_date_safe",
]
```

3. **Создать `app/utils/formatters.py` (~60 строк):**
```python
"""Функции форматирования для отображения данных в UI."""

from datetime import date, datetime
from decimal import Decimal

from loguru import logger


def format_amount(amount: Decimal) -> str:
    """Форматирует сумму для отображения.

    Args:
        amount: Сумма операции

    Returns:
        str: Отформатированная строка (например, "15 000.00 ₽")
    """
    return f"{amount:,.2f} ₽".replace(",", " ")


def format_date(date_obj: date) -> str:
    """Форматирует дату для отображения.

    Args:
        date_obj: Объект даты

    Returns:
        str: Дата в формате DD.MM.YYYY
    """
    return date_obj.strftime("%d.%m.%Y")


def format_days_remaining(days: int) -> str:
    """Форматирует оставшиеся дни с правильным склонением.

    Args:
        days: Количество оставшихся дней

    Returns:
        str: Строка с правильным склонением ("1 день", "2 дня", "5 дней")
    """
    if days <= 0:
        return "Срок истёк"

    # Склонение для русского языка
    last_digit = days % 10
    last_two_digits = days % 100

    if 11 <= last_two_digits <= 14:
        return f"{days} дней"
    elif last_digit == 1:
        return f"{days} день"
    elif 2 <= last_digit <= 4:
        return f"{days} дня"
    else:
        return f"{days} дней"


def parse_date_safe(date_str: str | None) -> date | None:
    """Безопасно парсит строку даты.

    Args:
        date_str: Дата в формате YYYY-MM-DD или None

    Returns:
        date | None: Объект date или None при ошибке
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка парсинга даты '{date_str}': {e}")
        return None
```

### 1.2 Расширить GoalService

4. **Добавить метод `get_contributions()` в `app/services/goal_service.py`:**

Добавить после метода `delete_goal()` (~строка 260):
```python
def get_contributions(
    self,
    goal_id: int,
    limit: int = 10,
) -> list:
    """Получает список взносов цели отсортированный по дате DESC.

    Args:
        goal_id: ID цели
        limit: Максимальное количество записей (default 10)

    Returns:
        list[GoalContribution]: Последние взносы по дате убывания
    """
    return (
        self.session.query(GoalContribution)
        .filter_by(goal_id=goal_id)
        .order_by(GoalContribution.contribution_date.desc())
        .limit(limit)
        .all()
    )
```

### 1.3 Обновить transactions.py

5. **Удалить локальные функции из `app/components/transactions.py`:**
   - Удалить функции `format_amount`, `format_date`, `parse_date_safe` (строки 18-57)
   - Это примерно 40 строк кода

6. **Добавить импорт в `app/components/transactions.py`:**
   - В секцию imports (после строки 16) добавить:
```python
from app.utils.formatters import format_amount, format_date, parse_date_safe
```

### 1.4 Добавить unit тесты

7. **Добавить тесты в `tests/test_goal_service.py`:**

Добавить новые тест-функции:
```python
def test_get_contributions_returns_sorted_desc(session, test_user):
    """Тест: взносы возвращаются отсортированными по дате DESC."""
    service = GoalService(session)
    goal = service.create_goal(
        user_id=test_user.id,
        name="Test Goal",
        target_amount=Decimal("10000"),
        target_date=date.today() + timedelta(days=30),
    )

    # Добавляем взносы в разном порядке
    service.add_contribution(goal.id, Decimal("100"), date(2026, 1, 1), "First")
    service.add_contribution(goal.id, Decimal("200"), date(2026, 1, 15), "Second")
    service.add_contribution(goal.id, Decimal("300"), date(2026, 1, 10), "Third")
    session.commit()

    contributions = service.get_contributions(goal.id)

    assert len(contributions) == 3
    assert contributions[0].description == "Second"  # 15 января
    assert contributions[1].description == "Third"   # 10 января
    assert contributions[2].description == "First"   # 1 января


def test_get_contributions_respects_limit(session, test_user):
    """Тест: limit ограничивает количество возвращаемых записей."""
    service = GoalService(session)
    goal = service.create_goal(
        user_id=test_user.id,
        name="Test Goal",
        target_amount=Decimal("10000"),
        target_date=date.today() + timedelta(days=30),
    )

    # Добавляем 5 взносов
    for i in range(5):
        service.add_contribution(
            goal.id,
            Decimal("100"),
            date.today() - timedelta(days=i),
            f"Contribution {i}"
        )
    session.commit()

    contributions = service.get_contributions(goal.id, limit=3)

    assert len(contributions) == 3


def test_get_contributions_empty_list(session, test_user):
    """Тест: пустой список если нет взносов."""
    service = GoalService(session)
    goal = service.create_goal(
        user_id=test_user.id,
        name="Test Goal",
        target_amount=Decimal("10000"),
        target_date=date.today() + timedelta(days=30),
    )
    session.commit()

    contributions = service.get_contributions(goal.id)

    assert contributions == []


def test_get_contributions_filters_by_goal_id(session, test_user):
    """Тест: возвращает взносы только указанной цели."""
    service = GoalService(session)

    # Создаем первую цель и добавляем взнос
    goal1 = service.create_goal(
        user_id=test_user.id,
        name="Goal 1",
        target_amount=Decimal("10000"),
        target_date=date.today() + timedelta(days=30),
    )
    service.add_contribution(goal1.id, Decimal("100"), description="For Goal 1")

    # Удаляем первую цель чтобы создать вторую (MVP ограничение)
    service.delete_goal(goal1.id)

    goal2 = service.create_goal(
        user_id=test_user.id,
        name="Goal 2",
        target_amount=Decimal("5000"),
        target_date=date.today() + timedelta(days=60),
    )
    service.add_contribution(goal2.id, Decimal("200"), description="For Goal 2")
    session.commit()

    contributions = service.get_contributions(goal2.id)

    assert len(contributions) == 1
    assert contributions[0].description == "For Goal 2"
```

## Workflow (Порядок работы)

**Твоя задача — выполнить `Sub-tasks` выше, строго следуя этому циклу.**

1.  **Выполнение:** Последовательно выполняй подзадачи 1.1-1.4.
2.  **Верификация:** После завершения ВСЕХ подзадач запусти проверки:
    - `black app/utils/ app/components/transactions.py app/services/goal_service.py`
    - `flake8 app/utils/ app/components/transactions.py app/services/goal_service.py`
    - `pytest tests/test_goal_service.py -v`
    - `pytest -v` (все тесты)
    - Исправляй все ошибки, пока проверки не станут "зелеными".
3.  **Фиксация:** После успешной верификации:
    - **Добавь запись в `log.md`**: Опиши, что было сделано.
    - **Обнови `context.md`**: Увеличь `Current Step` на 2 и подготовь `Next Action` для Шага 2.
    - Проверь ветку main в поисках случайно добавленных файлов.
4.  **Сделай коммит:** `git add .` и `git commit -m "feat(utils): add formatters module and get_contributions method [protocol-0004/01]"`. Сделай пуш.
5.  **Отчет пользователю:** Сообщи о завершении шага в установленном формате.

<формат_отчёта_о_шаге>
(Протокол 0004, Шаг 1):

**Сделано**:
- Создан app/utils/formatters.py с функциями format_amount, format_date, format_days_remaining, parse_date_safe
- Добавлен метод get_contributions() в GoalService
- Обновлены импорты в transactions.py
- Добавлены 4 unit теста для get_contributions

**Проверки**: black, flake8, pytest — результаты

**Git**:
- PR: #N
- Ветка: 0004-goals-ui
- Commit: [hash] feat(utils): add formatters module and get_contributions method [protocol-0004/01]
- Push: выполнен
- main: чист

**Рабочая папка**: /home/skytiger/PycharmProjects/worktrees/0004-goals-ui

**Статус протокола**: Шаг 1 завершен. Следующий: Шаг 2 (Goals Layout)
</формат_отчёта_о_шаге>
