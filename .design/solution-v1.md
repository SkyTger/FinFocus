# Solution v1: Переиспользование шаблонов и автоматический пересчёт exceptions

## Обзор решения
Решение состоит из трёх ключевых изменений в BudgetReservationService: (1) переиспользование существующего шаблона при переключении режимов вместо создания нового, (2) добавление метода recalculate_current_month_exception() для пересчёта при изменениях взносов/бюджета, (3) унификация логики get_budget_progress() для показа взносов вместо резервов. Дополнительно интегрируем пересчёт в GoalService и callback save_budget.

## Архитектура

### Компоненты

**BudgetReservationService (модифицируется)**
- Добавляется `_find_any_reserve_template()` — поиск любого шаблона включая остановленный
- Добавляется `_get_template_day()` — извлечение дня из шаблона
- Добавляется `_cleanup_orphan_exceptions()` — удаление orphan exceptions
- Добавляется `_get_reserve_date_for_month()` — вычисление даты резерва
- Добавляется `_delete_exception_for_date()` — удаление exception по дате
- Добавляется `recalculate_current_month_exception()` — пересчёт exception
- Модифицируется `set_mode()` — логика переиспользования шаблона
- Модифицируется `get_budget_progress()` — единообразный расчёт used_budget

**GoalService (модифицируется)**
- Добавляется `delete_contribution()` — удаление взноса с пересчётом exception

**goals.py callbacks (модифицируется)**
- `save_budget()` — добавить вызов recalculate после изменения бюджета

### Диаграмма взаимодействия

```
set_mode("fixed_date", day=15)
    │
    ▼
_find_any_reserve_template()
    │
    ├─ Найден с day=15 ──► Реактивировать (recurring_end_date=None)
    │                      Exceptions сохраняются!
    │
    └─ Найден с day≠15 ──► _stop_reserve_template()
       или не найден       _cleanup_orphan_exceptions()
                           _create_reserve_template()

add_contribution() / delete_contribution()
    │
    ▼
adjust_reserve_for_contribution() / recalculate_current_month_exception()
    │
    ▼
RecurringService.create_exception()
    │
    ▼
Calendar показывает корректный резерв
```

## Файловая структура

```
app/services/budget_reservation_service.py  — основные изменения (6 новых методов, 2 модификации)
app/services/goal_service.py                — новый метод delete_contribution()
app/components/goals.py                     — вызов recalculate в save_budget callback
tests/test_budget_reservation_service.py    — новые тестовые классы
```

## Ключевые интерфейсы

```python
# app/services/budget_reservation_service.py

class BudgetReservationService:
    """Сервис управления режимами резервирования бюджета на накопления."""

    def _find_any_reserve_template(self, user_id: int) -> Transaction | None:
        """Находит любой recurring шаблон резерва (включая остановленный).

        Ищет последний созданный шаблон SAVINGS_RESERVE для переиспользования.

        Returns:
            Transaction | None: Шаблон или None если не найден.
        """
        ...

    def _get_template_day(self, template: Transaction) -> int:
        """Извлекает день месяца из шаблона.

        Для EOM anchor (recurring_anchor_eom=True) возвращает 31.

        Returns:
            int: День месяца (1-31).
        """
        ...

    def _cleanup_orphan_exceptions(self, template_id: int) -> int:
        """Удаляет exceptions для дат после recurring_end_date.

        Вызывается при изменении дня месяца для очистки
        невалидных exceptions от старого шаблона.

        Returns:
            int: Количество удалённых exceptions.
        """
        ...

    def _get_reserve_date_for_month(
        self, user_id: int, reference_date: date
    ) -> date | None:
        """Возвращает дату резерва для указанного месяца.

        Учитывает короткие месяцы (min(day_of_month, last_day)).

        Returns:
            date | None: Дата резерва или None если режим != fixed_date.
        """
        ...

    def _delete_exception_for_date(
        self, template_id: int, target_date: date
    ) -> bool:
        """Удаляет exception для конкретной даты.

        Используется при пересчёте когда взносов нет.

        Returns:
            bool: True если exception удалён, False если не существовал.
        """
        ...

    def recalculate_current_month_exception(
        self, user_id: int, month: date | None = None
    ) -> bool:
        """Пересчитывает exception для текущего/указанного месяца.

        Вызывается при:
        - Удалении взноса
        - Изменении суммы взноса
        - Изменении monthly_savings_budget

        Args:
            user_id: ID пользователя.
            month: Дата в целевом месяце (default: today).

        Returns:
            bool: True если exception обновлён/создан, False если не требуется.
        """
        ...

    def set_mode(
        self,
        user_id: int,
        mode: ReservationMode,
        day_of_month: int | None = None,
    ) -> BudgetReservationSettings:
        """Устанавливает режим резервирования с переиспользованием шаблона.

        При переключении на fixed_date:
        1. Ищет существующий шаблон (включая остановленный)
        2. Если день совпадает — реактивирует (exceptions сохраняются)
        3. Если день изменился — останавливает старый, чистит orphan exceptions,
           создаёт новый
        """
        ...

    def get_budget_progress(
        self,
        user_id: int,
        reference_date: date | None = None,
    ) -> BudgetProgress:
        """Рассчитывает прогресс использования бюджета.

        Изменение: единообразно для обоих режимов считает взносы,
        а не резервы. mode_text = "Внесено" для обоих режимов.
        """
        ...
```

```python
# app/services/goal_service.py

class GoalService:
    """Сервис для операций с целями накопления."""

    def delete_contribution(self, contribution_id: int) -> bool:
        """Удаляет взнос и пересчитывает exception.

        Args:
            contribution_id: ID взноса GoalContribution.

        Returns:
            bool: True если взнос удалён, False если не найден.
        """
        ...
```

## Модель данных

Изменений в схеме БД не требуется. Используются существующие структуры:

```python
# Существующие TypedDicts
BudgetReservationSettings = TypedDict(
    "BudgetReservationSettings",
    {
        "mode": ReservationMode,
        "day_of_month": int | None,
        "monthly_budget": Decimal,
        "template_id": int | None,
    },
)

BudgetProgress = TypedDict(
    "BudgetProgress",
    {
        "total_budget": Decimal,
        "used_budget": Decimal,  # Теперь всегда взносы, не резервы
        "available_budget": Decimal,
        "progress_percent": float,
        "status": str,
        "mode": ReservationMode,
        "mode_text": str,  # Теперь всегда "Внесено"
    },
)
```

## Обработка ошибок

**Стратегия: Fail-safe with logging**
- Отсутствие шаблона при пересчёте — логируем, возвращаем False (не ошибка)
- Прошедшая дата резерва — логируем, не пересчитываем (корректное поведение)
- Отсутствие пользователя — ValueError (существующее поведение)
- Невалидный day_of_month — ValueError (существующее поведение)

```python
# Паттерн обработки в recalculate_current_month_exception
def recalculate_current_month_exception(self, user_id: int, month: date | None = None) -> bool:
    if month is None:
        month = date.today()

    settings = self.get_settings(user_id)

    # Guard: только fixed_date режим
    if settings["mode"] != "fixed_date":
        return False

    reserve_date = self._get_reserve_date_for_month(user_id, month)
    if reserve_date is None:
        return False

    # Guard: не пересчитываем прошедшие даты
    if reserve_date <= date.today():
        logger.debug(f"Reserve date {reserve_date} already passed, skipping recalc")
        return False

    template = self._get_reserve_template(user_id)
    if not template:
        logger.warning(f"No active template for user {user_id}, skipping recalc")
        return False

    # ... пересчёт
```

## План реализации

1. **Добавить helper методы в BudgetReservationService** (~60 строк)
   - `_find_any_reserve_template()`
   - `_get_template_day()`
   - `_cleanup_orphan_exceptions()`
   - `_get_reserve_date_for_month()`
   - `_delete_exception_for_date()`

2. **Реализовать recalculate_current_month_exception()** (~50 строк)
   - Логика пересчёта из спецификации
   - Обработка случая "нет взносов — удалить exception"

3. **Модифицировать set_mode()** (~30 строк изменений)
   - Добавить логику поиска существующего шаблона
   - Условие реактивации vs создания нового

4. **Модифицировать get_budget_progress()** (~10 строк изменений)
   - Единообразный расчёт через _get_contributions_sum_for_month
   - mode_text = "Внесено" для обоих режимов

5. **Добавить delete_contribution() в GoalService** (~30 строк)
   - Удаление взноса
   - Обновление Goal.current_amount
   - Вызов recalculate_current_month_exception

6. **Интегрировать в save_budget callback** (~5 строк)
   - Вызов recalculate после изменения бюджета

7. **Unit тесты для новых методов** (~150 строк)
   - TestSetModeReuse
   - TestRecalculateException
   - TestBudgetProgressUnified

8. **Integration тесты** (~50 строк)
   - TestModeSwitch E2E сценарии

9. **Финализация** (lint, format, full test suite)

## Зависимости

Новых библиотек не требуется. Используются существующие:
- SQLAlchemy (ORM)
- loguru (logging)
- datetime, decimal (stdlib)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Регрессия в CalendarService при изменении get_budget_progress | Средняя | Calendar использует виртуальные экземпляры, не get_budget_progress напрямую. Добавить integration тесты calendar + reservation |
| Некорректная логика EOM anchor при _get_template_day | Низкая | Отдельные unit тесты для day=31 и anchor_eom=True |
| Race condition при параллельных вызовах recalculate | Низкая | Single-user приложение в MVP. Для multi-user добавить pessimistic locking |
| Orphan exceptions не удаляются для старых шаблонов | Средняя | _cleanup_orphan_exceptions вызывается только при смене дня. Существующие orphan exceptions от предыдущих багов останутся. Можно добавить migration script при необходимости |
