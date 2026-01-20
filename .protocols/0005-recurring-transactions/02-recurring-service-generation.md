# Шаг 2: RecurringService — генерация экземпляров

## Briefing
- **Цель:** Создать RecurringService с Anchored-алгоритмом генерации виртуальных экземпляров из шаблонов. Реализовать константы защиты (MAX_INSTANCES_PER_CALL) и базовые методы.
- **Ключевые файлы:**
  - `app/services/recurring_service.py` (создать)
  - `app/services/__init__.py` (обновить экспорты)
  - `tests/test_recurring_service.py` (создать)
- **Additional info:**
  - VirtualTransaction — TypedDict для JSON-сериализации (совместимость с dcc.Store)
  - Anchored-алгоритм: 31 января → 28 февраля → 31 марта (возвращаемся к anchor_day)
  - Периоды: weekly, biweekly, monthly, quarterly

## Sub-tasks

### 1. Создать файл `app/services/recurring_service.py`

```python
"""Сервис для управления повторяющимися операциями.

Реализует Anchored-алгоритм генерации виртуальных экземпляров
из шаблонов с поддержкой exceptions.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict
from calendar import monthrange

from loguru import logger
from sqlalchemy.orm import Session

from app.models.database import Transaction, TransactionType


# === КОНСТАНТЫ ===

MAX_INSTANCES_PER_CALL: int = 1000
"""Максимальное количество экземпляров за один вызов generate_instances().
Защита от DoS при бессрочных шаблонах или некорректных параметрах."""

MAX_FORECAST_DAYS: int = 366
"""Максимальный горизонт прогноза (дней). Соответствует 12 месяцам вперед."""

VALID_RECURRING_PERIODS: frozenset[str] = frozenset({
    "weekly",
    "biweekly",
    "monthly",
    "quarterly",
})
"""Допустимые периоды повторения."""
```

### 2. Создать TypedDict VirtualTransaction

```python
class VirtualTransaction(TypedDict):
    """Виртуальный экземпляр recurring операции.

    Не хранится в БД, генерируется динамически.
    TypedDict для совместимости с JSON-сериализацией (dcc.Store).
    """
    template_id: int  # ID шаблона
    user_id: int
    instance_date: str  # ISO format (YYYY-MM-DD)
    amount: str  # Decimal as string для JSON
    transaction_type: str  # "income" | "expense" | "transfer"
    description: str | None
    is_virtual: bool  # Всегда True для виртуальных
```

### 3. Создать класс RecurringService

```python
class RecurringService:
    """Сервис для управления повторяющимися операциями."""

    def __init__(self, session: Session):
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy session для работы с БД.
        """
        self.session = session
```

### 4. Реализовать метод get_templates_for_user

```python
def get_templates_for_user(self, user_id: int) -> list[Transaction]:
    """Получает все активные recurring шаблоны пользователя.

    Args:
        user_id: ID пользователя.

    Returns:
        Список шаблонов (is_recurring=True, recurring_parent_id=None).
    """
    logger.debug(f"Получение шаблонов для пользователя {user_id}")

    templates = (
        self.session.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_recurring == True,  # noqa: E712
            Transaction.recurring_parent_id == None,  # noqa: E711
        )
        .order_by(Transaction.transaction_date)
        .all()
    )

    logger.info(f"Найдено {len(templates)} шаблонов для пользователя {user_id}")
    return templates
```

### 5. Реализовать Anchored-алгоритм генерации дат

```python
def _get_anchored_date(self, anchor_day: int, year: int, month: int) -> date:
    """Вычисляет дату по Anchored-алгоритму.

    Args:
        anchor_day: Исходный день месяца (1-31).
        year: Год.
        month: Месяц (1-12).

    Returns:
        Дата с учетом ограничений месяца.
        Например: anchor_day=31, февраль → 28 (или 29).
    """
    _, last_day = monthrange(year, month)
    actual_day = min(anchor_day, last_day)
    return date(year, month, actual_day)


def _generate_dates(
    self,
    start_date: date,
    end_date: date,
    period: str,
    anchor_day: int,
    recurring_end_date: date | None,
) -> list[date]:
    """Генерирует даты экземпляров по Anchored-алгоритму.

    Args:
        start_date: Начало периода генерации.
        end_date: Конец периода генерации.
        period: Период повторения (weekly, biweekly, monthly, quarterly).
        anchor_day: День месяца для привязки (1-31).
        recurring_end_date: Дата окончания серии (None = бессрочно).

    Returns:
        Список дат экземпляров в заданном периоде.
    """
    # Guard: валидация периода
    if period not in VALID_RECURRING_PERIODS:
        logger.warning(f"Неизвестный период: {period}")
        return []

    # Guard: end_date серии
    effective_end = min(end_date, recurring_end_date) if recurring_end_date else end_date

    dates: list[date] = []
    current = start_date

    if period == "weekly":
        # Для weekly используем простой шаг в 7 дней
        while current <= effective_end and len(dates) < MAX_INSTANCES_PER_CALL:
            dates.append(current)
            current += timedelta(days=7)

    elif period == "biweekly":
        # Для biweekly шаг в 14 дней
        while current <= effective_end and len(dates) < MAX_INSTANCES_PER_CALL:
            dates.append(current)
            current += timedelta(days=14)

    elif period == "monthly":
        # Anchored: каждый месяц возвращаемся к anchor_day
        while current <= effective_end and len(dates) < MAX_INSTANCES_PER_CALL:
            dates.append(current)
            # Переход к следующему месяцу
            if current.month == 12:
                next_year, next_month = current.year + 1, 1
            else:
                next_year, next_month = current.year, current.month + 1
            current = self._get_anchored_date(anchor_day, next_year, next_month)

    elif period == "quarterly":
        # Anchored: каждые 3 месяца
        while current <= effective_end and len(dates) < MAX_INSTANCES_PER_CALL:
            dates.append(current)
            # Переход через 3 месяца
            new_month = current.month + 3
            if new_month > 12:
                next_year = current.year + 1
                next_month = new_month - 12
            else:
                next_year = current.year
                next_month = new_month
            current = self._get_anchored_date(anchor_day, next_year, next_month)

    return [d for d in dates if start_date <= d <= effective_end]
```

### 6. Реализовать метод generate_instances

```python
def generate_instances(
    self,
    template: Transaction,
    start_date: date,
    end_date: date,
) -> list[VirtualTransaction]:
    """Генерирует виртуальные экземпляры шаблона в периоде.

    Использует Anchored-алгоритм: сохраняем исходный день месяца.

    ЗАЩИТА от DoS: генерация ограничена MAX_INSTANCES_PER_CALL.

    Args:
        template: Шаблон (Transaction с is_recurring=True).
        start_date: Начало периода.
        end_date: Конец периода.

    Returns:
        Список виртуальных экземпляров.
    """
    # Guard: валидация шаблона
    if not template.is_recurring:
        logger.warning(
            f"generate_instances вызван для не-recurring транзакции {template.id}"
        )
        return []

    # Guard: anchor_day должен быть валиден
    anchor_day = template.anchor_day
    if anchor_day is None:
        logger.error(
            f"Template {template.id} имеет is_recurring=True, "
            f"но anchor_day=None (transaction_date={template.transaction_date})"
        )
        return []

    # Guard: период должен быть валиден
    if template.recurring_period not in VALID_RECURRING_PERIODS:
        logger.warning(
            f"Template {template.id} имеет невалидный период: {template.recurring_period}"
        )
        return []

    # Определяем start_date шаблона
    template_start = template.transaction_date

    # Генерируем даты начиная с первой даты >= start_date
    effective_start = max(template_start, start_date)

    # Для monthly/quarterly нужно найти первую дату в периоде
    if template.recurring_period in ("monthly", "quarterly"):
        # Начинаем с anchor_day в месяце effective_start
        effective_start = self._get_anchored_date(
            anchor_day, effective_start.year, effective_start.month
        )
        # Если эта дата раньше template_start или start_date, переходим к следующему периоду
        if effective_start < template_start or effective_start < start_date:
            if template.recurring_period == "monthly":
                months_to_add = 1
            else:  # quarterly
                months_to_add = 3
            new_month = effective_start.month + months_to_add
            if new_month > 12:
                effective_start = self._get_anchored_date(
                    anchor_day, effective_start.year + 1, new_month - 12
                )
            else:
                effective_start = self._get_anchored_date(
                    anchor_day, effective_start.year, new_month
                )

    dates = self._generate_dates(
        effective_start,
        end_date,
        template.recurring_period,
        anchor_day,
        template.recurring_end_date,
    )

    # Ограничение количества
    if len(dates) >= MAX_INSTANCES_PER_CALL:
        logger.warning(
            f"Достигнут лимит {MAX_INSTANCES_PER_CALL} экземпляров "
            f"для шаблона {template.id}. Генерация прервана."
        )

    results: list[VirtualTransaction] = []
    for instance_date in dates:
        results.append(VirtualTransaction(
            template_id=template.id,
            user_id=template.user_id,
            instance_date=instance_date.isoformat(),
            amount=str(template.amount),
            transaction_type=template.transaction_type.value,
            description=template.description,
            is_virtual=True,
        ))

    logger.debug(
        f"Сгенерировано {len(results)} экземпляров для шаблона {template.id} "
        f"в периоде {start_date} - {end_date}"
    )

    return results
```

### 7. Обновить `app/services/__init__.py`

Добавить экспорты:

```python
from app.services.recurring_service import (
    RecurringService,
    VirtualTransaction,
    MAX_INSTANCES_PER_CALL,
    MAX_FORECAST_DAYS,
    VALID_RECURRING_PERIODS,
)
```

### 8. Написать unit тесты

Создать `tests/test_recurring_service.py` с тестами:

1. **test_get_templates_for_user_empty** — нет шаблонов
2. **test_get_templates_for_user_filters_non_recurring** — фильтрация не-recurring
3. **test_get_templates_for_user_filters_exceptions** — фильтрация exceptions
4. **test_generate_instances_monthly_anchored** — monthly с anchor_day=31 (февраль → март)
5. **test_generate_instances_monthly_normal** — monthly с anchor_day=15
6. **test_generate_instances_weekly** — weekly генерация
7. **test_generate_instances_biweekly** — biweekly генерация
8. **test_generate_instances_quarterly** — quarterly генерация
9. **test_generate_instances_respects_end_date** — учет recurring_end_date
10. **test_generate_instances_max_limit** — проверка MAX_INSTANCES_PER_CALL
11. **test_generate_instances_invalid_template** — не-recurring шаблон
12. **test_generate_instances_invalid_period** — невалидный период

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-8.
2. **Верификация:** После завершения ВСЕХ подзадач запусти:
   - `black app/services/recurring_service.py tests/test_recurring_service.py`
   - `flake8 app/services/recurring_service.py tests/test_recurring_service.py`
   - `pytest tests/test_recurring_service.py -v`
   - Исправляй все ошибки, пока проверки не станут "зелеными".
3. **Фиксация:** После успешной верификации:
   - **Добавь запись в `log.md`**: Опиши созданные методы и Anchored-алгоритм.
   - **Обнови `context.md`**: Увеличь `Current Step` на 1.
   - Проверь ветку main.
4. **Сделай коммит**: `git add . && git commit -m "feat(services): add RecurringService with Anchored generation [protocol-0005/02]"`. Сделай пуш.
5. **Отчет пользователю** по установленному формату.
