# Solution v4: Cascade Contribution Management -- Critique-v3 Full Resolution

## Обзор решения
Данная итерация исправляет все 5 замечаний из critique-v3. Основные изменения: (1) delete_contribution() переписан по Варианту A -- удаление Transaction и GoalContribution напрямую без вызова delete_contribution_transaction(), что устраняет двойное уменьшение current_amount; (2) добавлен Guard #2b для верхней границы даты (текущий месяц + 1); (3) lazy import вынесен в _get_budget_service(); (4) goal_name сохраняется в переменную до commit() для защиты от detached state; (5) тест contribution_info расширен проверкой всех 4 полей.

## Изменения относительно v3

### Изменение 1: delete_contribution() -- Вариант A (удалять напрямую)

Полностью переписанный метод. Ключевое отличие: НЕ вызываем `budget_service.delete_contribution_transaction()`, а удаляем Transaction и GoalContribution через `session.delete()` напрямую. Это дает единый контроль над `goal.current_amount` в одном месте.

```python
def delete_contribution(
    self,
    contribution_id: int,
) -> ContributionUpdateResult:
    """Удаляет взнос с откатом состояния цели.

    Вариант A: удаляем Transaction и GoalContribution напрямую,
    НЕ вызывая BudgetReservationService.delete_contribution_transaction()
    чтобы избежать двойного уменьшения Goal.current_amount.

    Returns:
        ContributionUpdateResult с результатом операции и флагами статуса.
    """
    contribution = self.session.get(GoalContribution, contribution_id)
    if not contribution:
        return ContributionUpdateResult(
            success=False,
            goal=None,
            status_changed=False,
            new_status=None,
            error="Взнос не найден",
            contribution_info=None,
        )

    goal = contribution.goal
    user_id = goal.user_id
    amount = contribution.amount
    contribution_date = contribution.contribution_date

    # Сохраняем goal_name ДО любых операций (защита от detached state)
    goal_name = goal.name

    # Сохраняем info для confirmation UI
    contribution_info = ContributionInfo(
        contribution_id=contribution_id,
        amount=amount,
        contribution_date=contribution_date,
        goal_name=goal_name,
    )

    # --- Удаление напрямую (Вариант A) ---
    # НЕ вызываем budget_service.delete_contribution_transaction()
    # т.к. он уже содержит логику уменьшения current_amount и отката статуса.
    # Вместо этого удаляем Transaction и GoalContribution вручную.
    if contribution.transaction_id:
        txn = self.session.get(Transaction, contribution.transaction_id)
        if txn:
            self.session.delete(txn)
    self.session.delete(contribution)

    # --- Единственное место обновления current_amount ---
    goal.current_amount -= amount
    if goal.current_amount < Decimal("0"):
        goal.current_amount = Decimal("0")

    # Пересчитываем exception
    budget_service = self._get_budget_service()
    budget_service.recalculate_current_month_exception(
        user_id=user_id,
        reference_date=contribution_date,
    )

    # Откат статуса COMPLETED -> ACTIVE (единственное место)
    status_changed = False
    new_status: Literal["active", "completed"] | None = None

    if goal.status == GoalStatus.COMPLETED and not goal.is_completed:
        goal.status = GoalStatus.ACTIVE
        status_changed = True
        new_status = "active"
        logger.info(f"Goal {goal.id} reverted to ACTIVE after contribution delete")

    self.session.flush()
    logger.info(
        f"Deleted contribution {contribution_id} for goal {goal.id}, "
        f"amount={amount}, status_changed={status_changed}"
    )

    return ContributionUpdateResult(
        success=True,
        goal=goal,
        status_changed=status_changed,
        new_status=new_status,
        error=None,
        contribution_info=contribution_info,
    )
```

**Что изменилось по сравнению с v3:**
- Строка `budget_service.delete_contribution_transaction(contribution.transaction_id)` заменена на прямое удаление Transaction + GoalContribution
- Устранено двойное уменьшение `goal.current_amount`
- Устранено дублирование отката статуса COMPLETED -> ACTIVE
- Добавлена строка `goal_name = goal.name` до flush (замечание #4)
- Lazy import заменен на `self._get_budget_service()` (замечание #3)

---

### Изменение 2: Guard #2b -- верхняя граница даты (текущий месяц + 1)

Добавляется в `update_contribution()` сразу после Guard #2a (проверка прошлого месяца).

```python
# Guard #2: Валидация даты
if contribution_date is not None:
    today = date.today()
    # Guard #2a: нижняя граница — не в прошлом месяце
    if (contribution_date.year, contribution_date.month) < (today.year, today.month):
        return ContributionUpdateResult(
            success=False,
            goal=None,
            status_changed=False,
            new_status=None,
            error="Дата взноса не может быть в прошлом месяце",
            contribution_info=None,
        )

    # Guard #2b: верхняя граница (текущий месяц + 1)
    if today.month < 12:
        max_year, max_month = today.year, today.month + 1
    else:
        max_year, max_month = today.year + 1, 1

    if (contribution_date.year, contribution_date.month) > (max_year, max_month):
        return ContributionUpdateResult(
            success=False,
            goal=None,
            status_changed=False,
            new_status=None,
            error="Дата взноса не может быть более чем через месяц",
            contribution_info=None,
        )
```

**Обоснование:** Пользователь решил ограничить дату взноса текущим месяцем + 1. Это предотвращает случайный ввод дат далеко в будущем и некорректный пересчет Exception для отдаленных месяцев.

---

### Изменение 3: _get_budget_service() helper

Приватный метод в GoalService для устранения дублирования lazy import.

```python
# app/services/goal_service.py, в классе GoalService

def _get_budget_service(self):
    """Возвращает BudgetReservationService с текущей сессией.

    Lazy import для избежания circular dependency
    (GoalService <-> BudgetReservationService).

    Returns:
        BudgetReservationService: Инстанс с self.session.
    """
    from app.services.budget_reservation_service import BudgetReservationService

    return BudgetReservationService(self.session)
```

**Места замены (4 вхождения):**
1. `add_contribution()` (строка 154-156) -- заменить на `self._get_budget_service()`
2. `update_savings_budget()` (строка 486-488) -- заменить на `self._get_budget_service()`
3. `update_contribution()` (новый метод, шаг 9) -- использовать `self._get_budget_service()`
4. `delete_contribution()` (исправленный метод) -- использовать `self._get_budget_service()`

---

### Изменение 4: Detached state -- сохранение goal_name до commit()

**Анализ проблемы:** Текущий `get_db_session()` использует `sessionmaker()` с дефолтным `expire_on_commit=True`. После `session.commit()` (который вызывается автоматически при выходе из `with get_db_session()`) все ORM-атрибуты объектов "протухают" (expired). Обращение к `result["goal"].name` после commit() вызовет lazy load, который сработает только если сессия ещё открыта.

**Решение:** В callbacks сохранять нужные скалярные значения из `result["goal"]` ДО выхода из `with get_db_session()`.

**В delete_contribution() (сервис):** уже исправлено (см. Изменение 1): `goal_name = goal.name` сохраняется до flush().

**В callbacks (goals.py):** Паттерн использования:

```python
# confirm_delete_contribution callback
with get_db_session() as session:
    service = GoalService(session)
    result = service.delete_contribution(contribution_id)

    if result["success"]:
        # Сохраняем скалярные данные ДО автоматического commit
        status_changed = result["status_changed"]
        new_status = result["new_status"]
        # goal_name уже в contribution_info (сохранен в сервисе)
        goal_name = result["contribution_info"]["goal_name"]
        amount = result["contribution_info"]["amount"]

# После выхода из with: используем ТОЛЬКО скалярные переменные
if status_changed and new_status == "active":
    toast_message = f'Цель "{goal_name}" снова активна'
```

```python
# submit_edit_contribution callback
with get_db_session() as session:
    service = GoalService(session)
    result = service.update_contribution(...)

    if result["success"]:
        status_changed = result["status_changed"]
        new_status = result["new_status"]
        goal_name = result["goal"].name  # безопасно: session ещё открыта
        goal_id = result["goal"].id

# После выхода: используем скалярные переменные
```

---

### Изменение 5: Тест contribution_info -- проверка всех 4 полей

```python
def test_delete_contribution_returns_contribution_info(self, session, user):
    """Проверяет что delete возвращает полный ContributionInfo для UI."""
    goal = GoalService(session).create_goal(
        user_id=user.id,
        name="Отпуск",
        target_amount=Decimal("50000"),
        target_date=date.today() + timedelta(days=90),
    )
    session.flush()

    contribution_date = date.today()
    goal = GoalService(session).add_contribution(
        goal_id=goal.id,
        amount=Decimal("5000"),
        contribution_date=contribution_date,
        description="Первый взнос",
    )
    session.flush()

    contribution = GoalService(session).get_contributions(goal.id, limit=1)[0]
    result = GoalService(session).delete_contribution(contribution.id)

    assert result["success"] is True
    assert result["contribution_info"] is not None

    info = result["contribution_info"]
    # Проверяем ВСЕ 4 поля ContributionInfo
    assert info["contribution_id"] == contribution.id
    assert info["amount"] == Decimal("5000")
    assert info["contribution_date"] == contribution_date
    assert info["goal_name"] == "Отпуск"
```

---

## Обновленный update_contribution() (полный, с учетом изменений 2 и 3)

```python
def update_contribution(
    self,
    contribution_id: int,
    amount: Decimal | None = None,
    contribution_date: date | None = None,
    description: str | None = None,
) -> ContributionUpdateResult:
    """Редактирует взнос с каскадным обновлением связанных сущностей.

    Обработка параметров:
    - amount: None = не изменять, >0 = установить, <=0 = ошибка
    - contribution_date: None = не изменять, date = установить
      (не в прошлом месяце, не далее текущий+1 месяц)
    - description:
        - None = не изменять
        - "" (пустая строка) = очистить (Transaction.description = "Взнос: {goal.name}")
        - непустая строка = установить как есть

    Пересчет Exception (шаг 9):
    - Выполняется только если contribution_date is not None AND contribution_date != old_date
    - Пересчитывает для обоих месяцев: old_date и new_date
    """
    # Guard #1: Валидация amount > 0
    if amount is not None and amount <= Decimal("0"):
        return ContributionUpdateResult(
            success=False,
            goal=None,
            status_changed=False,
            new_status=None,
            error="Сумма взноса должна быть больше 0",
            contribution_info=None,
        )

    # Guard #2: Валидация даты
    if contribution_date is not None:
        today = date.today()
        # Guard #2a: нижняя граница — не в прошлом месяце
        if (contribution_date.year, contribution_date.month) < (today.year, today.month):
            return ContributionUpdateResult(
                success=False,
                goal=None,
                status_changed=False,
                new_status=None,
                error="Дата взноса не может быть в прошлом месяце",
                contribution_info=None,
            )

        # Guard #2b: верхняя граница — не далее текущий месяц + 1
        if today.month < 12:
            max_year, max_month = today.year, today.month + 1
        else:
            max_year, max_month = today.year + 1, 1

        if (contribution_date.year, contribution_date.month) > (max_year, max_month):
            return ContributionUpdateResult(
                success=False,
                goal=None,
                status_changed=False,
                new_status=None,
                error="Дата взноса не может быть более чем через месяц",
                contribution_info=None,
            )

    # Guard #3: Взнос не найден
    contribution = self.session.get(GoalContribution, contribution_id)
    if not contribution:
        return ContributionUpdateResult(
            success=False,
            goal=None,
            status_changed=False,
            new_status=None,
            error="Взнос не найден",
            contribution_info=None,
        )

    goal = contribution.goal
    old_amount = contribution.amount
    old_date = contribution.contribution_date

    # 5. Обновить поля GoalContribution
    if amount is not None:
        contribution.amount = amount
    if contribution_date is not None:
        contribution.contribution_date = contribution_date
    if description is not None:
        # "" = очистить, непустая = установить
        contribution.description = description if description else None

    # 6. Delta calculation
    new_amount = contribution.amount
    delta = new_amount - old_amount

    # 7. Update Goal.current_amount
    goal.current_amount += delta
    if goal.current_amount < Decimal("0"):
        goal.current_amount = Decimal("0")

    # 8. Sync Transaction если есть
    if contribution.transaction_id:
        txn = self.session.get(Transaction, contribution.transaction_id)
        if txn:
            txn.amount = new_amount
            txn.transaction_date = contribution.contribution_date
            # description: "" -> default, непустая -> as is, None -> не трогаем
            if description is not None:
                txn.description = description if description else f"Взнос: {goal.name}"

    # 9. Пересчет Exception — ТОЛЬКО если дата передана И отличается от старой
    if contribution_date is not None and contribution_date != old_date:
        budget_service = self._get_budget_service()
        budget_service.recalculate_current_month_exception(goal.user_id, old_date)
        budget_service.recalculate_current_month_exception(goal.user_id, contribution_date)

    # 10. Check status change
    was_completed = goal.status == GoalStatus.COMPLETED
    is_completed_now = goal.is_completed

    status_changed = False
    new_status: Literal["active", "completed"] | None = None

    if was_completed and not is_completed_now:
        goal.status = GoalStatus.ACTIVE
        status_changed = True
        new_status = "active"
        logger.info(f"Goal {goal.id} reverted to ACTIVE after contribution update")
    elif not was_completed and is_completed_now:
        goal.status = GoalStatus.COMPLETED
        status_changed = True
        new_status = "completed"
        logger.info(f"Goal {goal.id} marked COMPLETED after contribution update")

    self.session.flush()

    return ContributionUpdateResult(
        success=True,
        goal=goal,
        status_changed=status_changed,
        new_status=new_status,
        error=None,
        contribution_info=None,
    )
```

---

## Обновленный план реализации

Изменены только шаги, затронутые исправлениями. Остальные шаги из solution-v3 остаются без изменений.

### Шаг 2 (обновлен): GoalService._get_budget_service() + get_contribution_by_id()

- Добавить приватный метод `_get_budget_service()` в GoalService
- Заменить все 4 вхождения lazy import на вызов `self._get_budget_service()`
- Добавить `get_contribution_by_id()` (без изменений относительно v3)

### Шаг 3 (обновлен): GoalService.update_contribution()

- Guard #2 разбит на #2a (нижняя граница) и #2b (верхняя граница: текущий месяц + 1)
- Шаг 9 использует `self._get_budget_service()` вместо inline lazy import

### Шаг 4 (обновлен): Исправить delete_contribution()

- Реализовать по Варианту A: прямое удаление Transaction + GoalContribution
- НЕ вызывать `budget_service.delete_contribution_transaction()`
- `goal_name = goal.name` сохраняется ДО flush()
- Использовать `self._get_budget_service()` для recalculate_current_month_exception

### Шаг 9 (обновлен): Goals UI callbacks

- В callbacks: сохранять скалярные данные из result ДО выхода из `with get_db_session()`
- Не обращаться к `result["goal"].name` после commit

---

## Обновленный тест-план (22 теста, было 20)

**update_contribution() -- 17 тестов (+2):**
- test_update_contribution_amount_increase
- test_update_contribution_amount_decrease
- test_update_contribution_amount_zero_error
- test_update_contribution_amount_negative_error
- test_update_contribution_date_within_month
- test_update_contribution_date_across_months_recalculates_exception
- test_update_contribution_date_past_month_error
- test_update_contribution_date_none_no_recalculate
- **test_update_contribution_date_far_future_error** (NEW: Guard #2b)
- **test_update_contribution_date_next_month_ok** (NEW: Guard #2b)
- test_update_contribution_description_sync_transaction
- test_update_contribution_description_empty_string_clears
- test_update_contribution_description_none_no_change
- test_update_contribution_status_completed_to_active
- test_update_contribution_status_active_to_completed
- test_update_contribution_exact_boundary_active
- test_update_contribution_not_found

**delete_contribution() -- 5 тестов (+1):**
- test_delete_contribution_with_transaction_id_reverts_status
- test_delete_contribution_without_transaction_id_reverts_status
- test_delete_contribution_returns_contribution_info (расширен: все 4 поля)
- test_delete_contribution_recalculates_exception
- **test_delete_contribution_with_transaction_no_double_decrement** (NEW: верификация Варианта A)

**Calendar guard -- 1 тест:**
- test_calendar_tooltip_blocks_savings_contribution

---

## Учтённые замечания из критики

| Замечание из critique v3 | Как решено |
|--------------------------|------------|
| 🟡 #1: Двойное уменьшение Goal.current_amount при delete с transaction_id | Вариант A: НЕ вызываем `delete_contribution_transaction()`. Удаляем Transaction и GoalContribution через `session.delete()` напрямую. Единственное место обновления `current_amount` -- в `delete_contribution()`. Добавлен тест `test_delete_contribution_with_transaction_no_double_decrement`. |
| 🟡 #2: Отсутствует верхняя граница даты взноса | Добавлен Guard #2b: `(contribution_date.year, contribution_date.month) > (max_year, max_month)` где max = текущий месяц + 1. Два новых теста: `far_future_error` и `next_month_ok`. |
| 🟢 #3: Lazy import дублируется | Создан `_get_budget_service()` helper. Заменены все 4 вхождения lazy import в GoalService (add_contribution, update_savings_budget, update_contribution, delete_contribution). |
| 🟢 #4: Detached state после commit() | В `delete_contribution()`: `goal_name = goal.name` сохраняется ДО flush()/commit(). В callbacks: скалярные данные извлекаются из result внутри `with get_db_session()` блока, до автоматического commit. Паттерн задокументирован. |
| 🟢 #5: Тест contribution_info не проверяет все поля | Тест расширен: проверяются все 4 поля ContributionInfo (`contribution_id`, `amount`, `contribution_date`, `goal_name`). |

## Ответы на вопросы критика

1. **Вопрос:** Верхняя граница даты взноса -- допустимо ли устанавливать дату на несколько месяцев вперед?
   **Ответ:** Нет, ограничиваем текущим месяцем + 1 (решение пользователя). Обоснование: (a) `recalculate_current_month_exception()` содержит guard `if reserve_date < date.today(): return False`, поэтому далекие будущие даты могут некорректно обрабатываться; (b) взнос в далекое будущее не имеет практического смысла в MVP; (c) защита от случайного ввода.

2. **Вопрос:** Detached state после commit() -- как обрабатывается доступ к `result["goal"].name`?
   **Ответ:** `get_db_session()` использует дефолтный `expire_on_commit=True`. Решение: сохранять все нужные скалярные значения в локальные переменные ДО выхода из `with get_db_session()`. Менять `expire_on_commit=False` не стоит -- это глобальное изменение с побочными эффектами.
