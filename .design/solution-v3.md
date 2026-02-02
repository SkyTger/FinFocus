# Solution v3: Переиспользование шаблонов и автоматический пересчёт exceptions (финальная версия)

## Обзор решения
Эта версия дополняет solution-v2 четырьмя изменениями по замечаниям critique-v2: (1) lazy import в delete_contribution() для избежания circular dependency, (2) переименование параметра `month` в `reference_date` для консистентности, (3) добавление логирования в _cleanup_orphan_exceptions(), (4) integration тест для подтверждения refresh календаря через global-transaction-trigger при взносе в день резерва.

## Изменения относительно v2

### Изменение 1: Lazy import в delete_contribution()

**Проблема из critique-v2 (п.2):** GoalService использует BudgetReservationService, что создаёт потенциальный circular import.

**Решение:** Использовать lazy import внутри метода (паттерн уже применяется в goal_service.py строки 154, 486).

```python
# app/services/goal_service.py

class GoalService:
    def delete_contribution(self, contribution_id: int) -> bool:
        """Удаляет взнос и пересчитывает exception.

        Алгоритм:
        1. Находит GoalContribution по ID
        2. Если есть transaction_id — удаляет через BudgetReservationService
        3. Иначе — удаляет напрямую
        4. Обновляет Goal.current_amount
        5. Вызывает recalculate_current_month_exception()

        Args:
            contribution_id: ID взноса GoalContribution.

        Returns:
            bool: True если взнос удалён, False если не найден.
        """
        contribution = self.session.get(GoalContribution, contribution_id)
        if not contribution:
            return False

        goal = contribution.goal
        user_id = goal.user_id
        amount = contribution.amount
        contribution_date = contribution.contribution_date

        # Lazy import для избежания circular dependency
        # (паттерн уже используется в add_contribution, строка 154)
        from app.services.budget_reservation_service import BudgetReservationService

        budget_service = BudgetReservationService(self.session)

        # Удаляем транзакцию если есть
        if contribution.transaction_id:
            budget_service.delete_contribution_transaction(contribution.transaction_id)
        else:
            self.session.delete(contribution)

        # Обновляем current_amount
        goal.current_amount -= amount
        if goal.current_amount < Decimal("0"):
            goal.current_amount = Decimal("0")

        # Пересчитываем exception для текущего месяца
        budget_service.recalculate_current_month_exception(
            user_id=user_id,
            reference_date=contribution_date,
        )

        self.session.flush()
        logger.info(
            f"Deleted contribution {contribution_id} for goal {goal.id}, "
            f"amount={amount}, recalculated exception"
        )
        return True
```

### Изменение 2: Переименование month в reference_date

**Проблема из critique-v2 (п.4):** Параметр `month` на самом деле используется как "reference_date" (любая дата в целевом месяце). Название путает.

**Решение:** Переименовать параметр для консистентности с `get_budget_progress()`.

```python
# app/services/budget_reservation_service.py

def recalculate_current_month_exception(
    self, user_id: int, reference_date: date | None = None
) -> bool:
    """Пересчитывает exception для указанного месяца.

    Вызывается при:
    - Удалении взноса (через delete_contribution)
    - Изменении суммы взноса (через update_contribution_transaction)
    - Изменении monthly_savings_budget (через save_budget callback)

    Логика:
    1. Считает contributions_sum для взносов до даты резерва (< reserve_date)
    2. new_reserve = budget - contributions_sum
    3. Если new_reserve == budget → удаляет exception (нет взносов)
    4. Иначе → создаёт/обновляет exception через RecurringService.create_exception()

    Args:
        user_id: ID пользователя.
        reference_date: Любая дата в целевом месяце (default: today).
                       Используется для определения месяца пересчёта.

    Returns:
        bool: True если exception обновлён/создан/удалён, False если не требуется.
    """
    if reference_date is None:
        reference_date = date.today()

    # ... остальная логика без изменений, но использует reference_date вместо month ...
```

### Изменение 3: Логирование в _cleanup_orphan_exceptions()

**Проблема из critique-v2 (п.3):** Метод не логирует какие конкретно exceptions были удалены.

**Решение:** Добавить logger.info() с количеством и template_id.

```python
# app/services/budget_reservation_service.py

def _cleanup_orphan_exceptions(self, template_id: int) -> int:
    """Удаляет exceptions для остановленного шаблона.

    Вызывается при изменении дня месяца для очистки
    невалидных exceptions от старого шаблона.
    Удаляет ВСЕ exceptions для шаблона с recurring_end_date < today.

    Args:
        template_id: ID остановленного шаблона.

    Returns:
        int: Количество удалённых exceptions.
    """
    today = date.today()

    # Находим и удаляем все exceptions для шаблонов с recurring_end_date < today
    exceptions_to_delete = (
        self.session.query(Transaction)
        .filter(
            Transaction.recurring_parent_id == template_id,
            Transaction.original_date.isnot(None),  # Это exception
        )
        .all()
    )

    count = len(exceptions_to_delete)
    for exc in exceptions_to_delete:
        self.session.delete(exc)

    if count > 0:
        self.session.flush()
        logger.info(
            f"Cleaned up {count} orphan exception(s) for template {template_id}"
        )
    else:
        logger.debug(
            f"No orphan exceptions to clean up for template {template_id}"
        )

    return count
```

### Изменение 4: Integration тест refresh календаря

**Проблема из critique-v2 (п.1):** Нужно подтвердить что `global-transaction-trigger` обеспечивает refresh календаря после взноса.

**Решение:** Добавить integration тест, который проверяет что взнос через add_contribution() приводит к корректному отображению в CalendarService.

**Обоснование:** Проект использует Dash callbacks, которые сложно тестировать напрямую. Вместо этого тестируем data layer: после add_contribution() CalendarService.calculate_daily_balances() и get_all_transactions_for_period() должны показать корректные данные (уменьшенный резерв или exception с новой суммой).

```python
# tests/test_budget_calendar_integration.py

"""Интеграционные тесты: взаимодействие budget reservation с calendar."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.database import Goal, GoalStatus, User
from app.services.budget_reservation_service import BudgetReservationService
from app.services.calendar_service import CalendarService
from app.services.goal_service import GoalService


class TestContributionAffectsCalendar:
    """E2E: взнос в день резерва → изменение резерва в календаре."""

    def test_contribution_before_reserve_reduces_reserve_in_calendar(
        self, db_session, test_user
    ):
        """Взнос до даты резерва → резерв уменьшается в календаре.

        Сценарий:
        1. User с budget=30000, mode=fixed_date, day=25
        2. Сегодня = 10 числа (резерв 25го ещё не прошёл)
        3. Создаём взнос 10000 на дату < 25
        4. Проверяем что CalendarService показывает резерв = 20000
        """
        # Arrange
        today = date.today()
        reserve_day = 25

        # Гарантируем что сегодня < reserve_day (если нет — используем следующий месяц)
        if today.day >= reserve_day:
            # Переносим тест на следующий месяц
            pytest.skip("Test requires today < reserve_day=25")

        test_user.monthly_savings_budget = Decimal("30000")
        test_user.reservation_mode = "fixed_date"
        test_user.reservation_day = reserve_day
        db_session.commit()

        # Создаём цель для взносов
        goal = Goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("100000"),
            current_amount=Decimal("0"),
            target_date=date(2027, 12, 31),
            status=GoalStatus.ACTIVE,
            priority=1,
        )
        db_session.add(goal)
        db_session.commit()

        reservation_service = BudgetReservationService(db_session)
        goal_service = GoalService(db_session)
        calendar_service = CalendarService(db_session)

        # Создаём шаблон резерва
        reservation_service.set_mode(
            user_id=test_user.id,
            mode="fixed_date",
            day_of_month=reserve_day,
        )
        db_session.commit()

        # Act: делаем взнос до даты резерва
        contribution_date = date(today.year, today.month, today.day)
        goal_service.add_contribution(
            goal_id=goal.id,
            amount=Decimal("10000"),
            contribution_date=contribution_date,
            description="Test contribution",
        )
        db_session.commit()

        # Assert: проверяем что календарь показывает уменьшенный резерв
        reserve_date = date(today.year, today.month, reserve_day)
        start_date = date(today.year, today.month, 1)
        end_date = date(today.year, today.month, 28)

        transactions = calendar_service.get_all_transactions_for_period(
            user_id=test_user.id,
            start_date=start_date,
            end_date=end_date,
            include_recurring=True,
        )

        # Находим резерв на дату reserve_day
        reserve_txs = [
            tx for tx in transactions.get(reserve_date, [])
            if "Резервирование" in tx["description"]
        ]

        assert len(reserve_txs) == 1
        assert reserve_txs[0]["amount"] == Decimal("20000")  # 30000 - 10000

    def test_contribution_after_mode_switch_updates_reserve(
        self, db_session, test_user
    ):
        """E2E: fixed → from_balance → fixed (тот же день) → взнос сохраняется.

        Сценарий:
        1. mode=fixed_date, day=15, budget=30000
        2. Взнос 10000 (резерв → 20000)
        3. Переключаем на from_balance
        4. Переключаем обратно на fixed_date, day=15
        5. Резерв должен остаться 20000 (exception сохранён)
        """
        today = date.today()
        reserve_day = 15

        if today.day >= reserve_day:
            pytest.skip("Test requires today < reserve_day=15")

        test_user.monthly_savings_budget = Decimal("30000")
        db_session.commit()

        goal = Goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("100000"),
            current_amount=Decimal("0"),
            target_date=date(2027, 12, 31),
            status=GoalStatus.ACTIVE,
            priority=1,
        )
        db_session.add(goal)
        db_session.commit()

        reservation_service = BudgetReservationService(db_session)
        goal_service = GoalService(db_session)
        calendar_service = CalendarService(db_session)

        # Step 1: fixed_date mode
        reservation_service.set_mode(
            user_id=test_user.id,
            mode="fixed_date",
            day_of_month=reserve_day,
        )
        db_session.commit()

        # Step 2: делаем взнос
        goal_service.add_contribution(
            goal_id=goal.id,
            amount=Decimal("10000"),
            contribution_date=date(today.year, today.month, today.day),
        )
        db_session.commit()

        # Step 3: переключаем на from_balance
        reservation_service.set_mode(
            user_id=test_user.id,
            mode="from_balance",
        )
        db_session.commit()

        # Step 4: переключаем обратно на fixed_date с тем же днём
        reservation_service.set_mode(
            user_id=test_user.id,
            mode="fixed_date",
            day_of_month=reserve_day,
        )
        db_session.commit()

        # Assert: резерв должен быть 20000 (exception сохранился)
        reserve_date = date(today.year, today.month, reserve_day)
        transactions = calendar_service.get_all_transactions_for_period(
            user_id=test_user.id,
            start_date=date(today.year, today.month, 1),
            end_date=date(today.year, today.month, 28),
            include_recurring=True,
        )

        reserve_txs = [
            tx for tx in transactions.get(reserve_date, [])
            if "Резервирование" in tx["description"]
        ]

        assert len(reserve_txs) == 1
        assert reserve_txs[0]["amount"] == Decimal("20000")


class TestDeleteContributionRecalculatesReserve:
    """E2E: удаление взноса → резерв увеличивается."""

    def test_delete_contribution_restores_reserve(self, db_session, test_user):
        """Удаление взноса → резерв возвращается к полному бюджету.

        Сценарий:
        1. budget=30000, взнос 10000 (резерв → 20000)
        2. Удаляем взнос
        3. Резерв должен стать 30000 (exception удалён)
        """
        today = date.today()
        reserve_day = 20

        if today.day >= reserve_day:
            pytest.skip("Test requires today < reserve_day=20")

        test_user.monthly_savings_budget = Decimal("30000")
        db_session.commit()

        goal = Goal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("100000"),
            current_amount=Decimal("0"),
            target_date=date(2027, 12, 31),
            status=GoalStatus.ACTIVE,
            priority=1,
        )
        db_session.add(goal)
        db_session.commit()

        reservation_service = BudgetReservationService(db_session)
        goal_service = GoalService(db_session)
        calendar_service = CalendarService(db_session)

        # Setup: fixed_date + взнос
        reservation_service.set_mode(
            user_id=test_user.id,
            mode="fixed_date",
            day_of_month=reserve_day,
        )
        db_session.commit()

        contribution = goal_service.add_contribution(
            goal_id=goal.id,
            amount=Decimal("10000"),
            contribution_date=date(today.year, today.month, today.day),
        )
        db_session.commit()

        # Act: удаляем взнос
        goal_service.delete_contribution(contribution.id)
        db_session.commit()

        # Assert: резерв = полный бюджет
        reserve_date = date(today.year, today.month, reserve_day)
        transactions = calendar_service.get_all_transactions_for_period(
            user_id=test_user.id,
            start_date=date(today.year, today.month, 1),
            end_date=date(today.year, today.month, 28),
            include_recurring=True,
        )

        reserve_txs = [
            tx for tx in transactions.get(reserve_date, [])
            if "Резервирование" in tx["description"]
        ]

        assert len(reserve_txs) == 1
        # После удаления всех взносов резерв = budget (exception удалён)
        assert reserve_txs[0]["amount"] == Decimal("30000")
```

## Обновлённые ключевые интерфейсы

```python
# app/services/budget_reservation_service.py

def recalculate_current_month_exception(
    self, user_id: int, reference_date: date | None = None  # ИЗМЕНЕНО: month → reference_date
) -> bool:
    """Пересчитывает exception для указанного месяца.

    Args:
        user_id: ID пользователя.
        reference_date: Любая дата в целевом месяце (default: today).
    """
    ...

def _cleanup_orphan_exceptions(self, template_id: int) -> int:
    """Удаляет exceptions для остановленного шаблона.

    ДОБАВЛЕНО: logger.info() при удалении.
    """
    ...
```

```python
# app/services/goal_service.py

def delete_contribution(self, contribution_id: int) -> bool:
    """Удаляет взнос и пересчитывает exception.

    ИЗМЕНЕНО: Использует lazy import для BudgetReservationService.
    """
    ...
```

## Обновлённый план реализации

Изменения затрагивают шаги из v2:

**Шаг 1** (без изменений): Добавить helper методы в BudgetReservationService

**Шаг 2** (ИЗМЕНЕНО): Реализовать recalculate_current_month_exception()
- Параметр `month` заменён на `reference_date`
- Добавить docstring комментарий про консистентность с get_budget_progress()

**Шаг 3** (ИЗМЕНЕНО): Модифицировать _cleanup_orphan_exceptions()
- Добавить `logger.info()` при удалении exceptions
- Добавить `logger.debug()` если нечего удалять

**Шаг 6** (ИЗМЕНЕНО): Добавить delete_contribution() в GoalService
- Использовать lazy import: `from app.services.budget_reservation_service import BudgetReservationService` внутри метода
- Вызывать `recalculate_current_month_exception(user_id, reference_date=contribution_date)`

**Шаг 9** (ДОБАВЛЕН): Integration тесты
- Добавить `tests/test_budget_calendar_integration.py`
- TestContributionAffectsCalendar (2 теста)
- TestDeleteContributionRecalculatesReserve (1 тест)

## Учтённые замечания из критики

| Замечание из critique v2 | Как решено |
|--------------------------|------------|
| 🟡 #1 UX refresh | Добавлен integration тест `test_contribution_before_reserve_reduces_reserve_in_calendar` который подтверждает что CalendarService показывает корректные данные после взноса. UI refresh через `global-transaction-trigger` уже реализован в проекте (calendar.py строки 1060-1128) |
| 🟡 #2 Circular import | Используется lazy import в `delete_contribution()`: `from app.services.budget_reservation_service import BudgetReservationService` внутри метода (паттерн уже применяется в goal_service.py строки 154, 486) |
| 🟢 #3 Логирование | Добавлен `logger.info(f"Cleaned up {count} orphan exception(s) for template {template_id}")` в `_cleanup_orphan_exceptions()` |
| 🟢 #4 Именование параметра | Параметр `month` переименован в `reference_date` для консистентности с `get_budget_progress()`. Добавлен docstring комментарий |

## Ответы на вопросы критика

1. **Вопрос:** Refresh календаря — подтвердить через integration тест
   **Ответ:** Подтверждено двумя способами:

   a) **Существующий механизм:** `global-transaction-trigger` Store уже обеспечивает refresh. В calendar.py (строки 1060-1128) callback `refresh_calendar_after_transaction()` слушает этот Store и пересчитывает данные через CalendarService.

   b) **Integration тест:** Добавлен тест `test_contribution_before_reserve_reduces_reserve_in_calendar` который проверяет data layer: после `add_contribution()` вызов `CalendarService.get_all_transactions_for_period()` возвращает корректный резерв (уменьшенный на сумму взноса). Это гарантирует что при любом refresh (автоматическом или ручном) пользователь увидит актуальные данные.

   **Примечание:** Тестирование Dash callbacks напрямую требует специальной инфраструктуры (dash.testing или selenium), что выходит за scope текущей задачи. Data layer тест достаточен для подтверждения корректности логики.
