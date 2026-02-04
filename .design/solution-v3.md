# Solution v3: Cascade Contribution Management with Full Guard Coverage and Critique Resolution

## Обзор решения
Расширяем GoalService методами `update_contribution()` и `get_contribution_by_id()` для каскадного редактирования взносов с синхронизацией всех связанных сущностей (GoalContribution, Transaction, Goal.current_amount, Exception). Исправляем `delete_contribution()` для возврата ContributionUpdateResult с флагами статуса. В Calendar tooltip добавляем Guard #6 для блокировки SAVINGS_CONTRIBUTION. В Goals UI добавляем кнопки Edit/Delete с confirmation modal, показывающим сумму и дату удаляемого взноса.

## Архитектура

### Компоненты

1. **GoalService (расширение)**
   - Новый метод `update_contribution()` - основная бизнес-логика редактирования с явной обработкой None/пустая строка для description
   - Новый метод `get_contribution_by_id()` - получение взноса для предзаполнения формы
   - Исправленный `delete_contribution()` - возвращает ContributionUpdateResult с флагами status_changed и new_status

2. **ContributionUpdateResult TypedDict**
   - Структурированный результат операций edit/delete
   - `new_status: Literal["active", "completed"] | None` для type safety
   - `contribution_info` для delete confirmation (сумма, дата)

3. **Calendar Guard #6 (calendar.py)**
   - Полная блокировка SAVINGS_CONTRIBUTION в tooltip (после Guard #5)
   - Комментарий уточнен: "по дизайну не recurring, guard для defensive programming"

4. **Goals UI (goals.py)**
   - Расширенная `_build_contributions_table()` с колонкой "Действия"
   - Модал редактирования с inline alert для ошибок
   - Confirmation modal с отображением суммы и даты: "Удалить взнос 5 000 ₽ от 15.01.2026?"
   - Toast уведомления при откате статуса COMPLETED -> ACTIVE

### Диаграмма взаимодействия
```
User clicks Edit in contribution table
          |
[Goals UI] -> open edit-contribution-modal (prefill from GoalService.get_contribution_by_id)
          |
User submits form
          |
[Callback] -> GoalService.update_contribution(...)
          |
  +-------+-------------------------------------------+
  | update_contribution():                            |
  | 1. Guard #1: amount > 0 (если передан)           |
  | 2. Guard #2: date не в прошлом месяце            |
  | 3. Guard #3: contribution not found               |
  | 4. Сохранить old_amount, old_date                 |
  | 5. Обновить GoalContribution fields               |
  | 6. Delta: new_amount - old_amount                 |
  | 7. Goal.current_amount += delta                   |
  | 8. Sync Transaction (amount, date, description)   |
  | 9. If date changed AND date != old_date:          |
  |    -> recalculate Exception для обоих месяцев     |
  | 10. Check COMPLETED <-> ACTIVE status change      |
  | 11. Return ContributionUpdateResult               |
  +---------------------------------------------------+
          |
[Callback] -> Update UI + inline alert (error) OR toast (status_changed)


User clicks Delete in contribution table
          |
[Goals UI] -> open delete-confirmation-modal
          |    (shows: "Удалить взнос {amount} от {date}?")
          |
User confirms
          |
[Callback] -> GoalService.delete_contribution(...)
          |    -> returns ContributionUpdateResult с status_changed
          |
[Callback] -> Update UI + toast (if status_changed: "Цель «X» снова активна")
```

## Файловая структура
```
app/schema/goals.py              — +ContributionUpdateResult TypedDict с Literal type
app/services/goal_service.py     — +update_contribution(), +get_contribution_by_id(), fix delete_contribution()
app/components/calendar.py       — +Guard #6 для SAVINGS_CONTRIBUTION (после Guard #5)
app/components/goals.py          — +edit modal, +delete confirm modal, +кнопки Edit/Delete, +callbacks, +toasts
tests/test_goal_service.py       — +тесты для update/delete contribution
tests/test_contribution_edit.py  — новый файл с integration тестами
```

## Ключевые интерфейсы

```python
# app/schema/goals.py
from typing import Literal, TypedDict
from datetime import date
from decimal import Decimal
from app.models.database import Goal

class ContributionInfo(TypedDict):
    """Информация о взносе для confirmation modal."""
    contribution_id: int
    amount: Decimal
    contribution_date: date
    goal_name: str

class ContributionUpdateResult(TypedDict):
    """Результат операции обновления/удаления взноса."""
    success: bool
    goal: Goal | None                                    # Обновленная цель
    status_changed: bool                                 # True если COMPLETED <-> ACTIVE
    new_status: Literal["active", "completed"] | None    # Literal для type safety
    error: str | None                                    # Локализованное сообщение
    contribution_info: ContributionInfo | None           # Для delete confirmation UI


# app/services/goal_service.py
class GoalService:
    def get_contribution_by_id(
        self,
        contribution_id: int,
    ) -> GoalContribution | None:
        """Получает взнос по ID для предзаполнения формы редактирования.

        Args:
            contribution_id: ID взноса GoalContribution.

        Returns:
            GoalContribution | None: Взнос или None если не найден.
        """

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
        - contribution_date: None = не изменять, date = установить (не в прошлом месяце)
        - description:
            - None = не изменять
            - "" (пустая строка) = очистить (Transaction.description = "Взнос: {goal.name}")
            - непустая строка = установить как есть

        Пересчет Exception (шаг 9):
        - Выполняется только если contribution_date is not None AND contribution_date != old_date
        - Пересчитывает для обоих месяцев: old_date и new_date

        Args:
            contribution_id: ID взноса GoalContribution.
            amount: Новая сумма взноса (должна быть > 0).
            contribution_date: Новая дата взноса (не может быть в прошлом месяце).
            description: Новое описание (см. обработку выше).

        Returns:
            ContributionUpdateResult с результатом операции.

        Note:
            TODO: Для multi-user production добавить SELECT FOR UPDATE
            для предотвращения race condition при одновременном редактировании.
        """

    def delete_contribution(
        self,
        contribution_id: int,
    ) -> ContributionUpdateResult:
        """Удаляет взнос с откатом состояния цели.

        Исправлено: корректно откатывает статус COMPLETED -> ACTIVE
        для взносов БЕЗ transaction_id (режим fixed_date).

        Returns:
            ContributionUpdateResult с результатом операции и флагами статуса.
        """
```

## Модель данных

```python
# ContributionUpdateResult TypedDict - успех update
{
    "success": True,
    "goal": <Goal object>,
    "status_changed": True,       # Цель изменила статус
    "new_status": "active",       # Literal: откат после уменьшения amount
    "error": None,
    "contribution_info": None     # Не используется для update
}

# ContributionUpdateResult TypedDict - успех delete
{
    "success": True,
    "goal": <Goal object>,
    "status_changed": True,
    "new_status": "active",
    "error": None,
    "contribution_info": {        # Для UI toast/log
        "contribution_id": 123,
        "amount": Decimal("5000"),
        "contribution_date": date(2026, 1, 15),
        "goal_name": "Отпуск"
    }
}

# ContributionUpdateResult TypedDict - ошибка
{
    "success": False,
    "goal": None,
    "status_changed": False,
    "new_status": None,
    "error": "Сумма взноса должна быть больше 0",  # Локализованное
    "contribution_info": None
}

# Pattern-Matching IDs для кнопок
{
    "type": "contribution-edit-btn",
    "contribution_id": 123  # int, не index
}
{
    "type": "contribution-delete-btn",
    "contribution_id": 123
}
```

## Обработка ошибок

### Валидация в update_contribution()
```python
def update_contribution(
    self,
    contribution_id: int,
    amount: Decimal | None = None,
    contribution_date: date | None = None,
    description: str | None = None,
) -> ContributionUpdateResult:
    """Редактирует взнос с каскадным обновлением связанных сущностей.

    Обработка description:
    - None = не изменять текущее значение
    - "" = очистить (установить default "Взнос: {goal.name}")
    - непустая строка = установить как есть
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

    # Guard #2: Дата не в прошлом месяце
    if contribution_date is not None:
        today = date.today()
        if (contribution_date.year, contribution_date.month) < (today.year, today.month):
            return ContributionUpdateResult(
                success=False,
                goal=None,
                status_changed=False,
                new_status=None,
                error="Дата взноса не может быть в прошлом месяце",
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

    # 8. Sync Transaction если есть
    if contribution.transaction_id:
        txn = self.session.get(Transaction, contribution.transaction_id)
        if txn:
            txn.amount = new_amount
            txn.transaction_date = contribution.contribution_date
            # description: "" -> default, непустая -> as is, None -> не трогаем
            if description is not None:
                txn.description = description if description else f"Взнос: {goal.name}"

    # 9. Пересчет Exception - ТОЛЬКО если дата была передана И отличается от старой
    # (критика 🟡 #2: явное условие)
    if contribution_date is not None and contribution_date != old_date:
        from app.services.budget_reservation_service import BudgetReservationService
        budget_service = BudgetReservationService(self.session)
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

### Исправленный delete_contribution() с ContributionUpdateResult
```python
def delete_contribution(
    self,
    contribution_id: int,
) -> ContributionUpdateResult:
    """Удаляет взнос с откатом состояния цели.

    Возвращает ContributionUpdateResult с флагами для UI:
    - status_changed: True если COMPLETED -> ACTIVE
    - contribution_info: сумма и дата для toast/confirmation
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

    # Сохраняем info для confirmation UI
    contribution_info = ContributionInfo(
        contribution_id=contribution_id,
        amount=amount,
        contribution_date=contribution_date,
        goal_name=goal.name,
    )

    # Lazy import
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

    # Пересчитываем exception
    budget_service.recalculate_current_month_exception(
        user_id=user_id,
        reference_date=contribution_date,
    )

    # КРИТИЧНО: откат статуса для ОБОИХ путей (с и без transaction_id)
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

### Calendar Guard #6 с уточненным комментарием
```python
# app/components/calendar.py, в open_edit_from_tooltip(), после Guard #5

# Guard #5: SAVINGS_RESERVE — read-only, игнорируем клики
if txn_type == "savings_reserve":
    logger.debug("Tooltip: клик на SAVINGS_RESERVE ignored (read-only)")
    raise PreventUpdate

# Guard #6: SAVINGS_CONTRIBUTION — редактирование через Goals UI
# Примечание: SAVINGS_CONTRIBUTION по дизайну не может быть recurring
# (создается только реальная транзакция в режиме from_balance).
# Этот guard добавлен для defensive programming на случай будущих изменений архитектуры.
if txn_type == "savings_contribution":
    logger.debug("Tooltip: клик на SAVINGS_CONTRIBUTION ignored (use Goals UI)")
    raise PreventUpdate
```

### Delete confirmation modal с суммой и датой
```python
def _build_delete_contribution_confirm_modal() -> dbc.Modal:
    """Модал подтверждения удаления взноса.

    Показывает сумму и дату удаляемого взноса для clarity.
    Формат: "Удалить взнос 5 000 ₽ от 15.01.2026?"
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle("Удаление взноса"),
                close_button=True,
            ),
            dbc.ModalBody(
                [
                    html.P(
                        id="delete-contribution-message",
                        # Заполняется динамически: "Удалить взнос {amount} от {date}?"
                    ),
                    html.P(
                        "Это действие нельзя отменить.",
                        className="text-muted small",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Отмена",
                        id="cancel-delete-contribution-btn",
                        color="secondary",
                        outline=True,
                    ),
                    dbc.Button(
                        "Удалить",
                        id="confirm-delete-contribution-btn",
                        color="danger",
                    ),
                ]
            ),
        ],
        id="delete-contribution-confirm-modal",
        is_open=False,
        centered=True,
    )
```

## План реализации

### Шаг 1: Schema (ContributionUpdateResult, ContributionInfo)
- Добавить TypedDicts в `app/schema/goals.py`
- ContributionInfo для delete confirmation
- Literal type для new_status
- Экспорт в `app/schema/__init__.py`

### Шаг 2: GoalService.get_contribution_by_id()
- Простой метод для получения взноса по ID
- Для предзаполнения формы edit modal

### Шаг 3: GoalService.update_contribution()
- Реализовать с полной логикой каскадного обновления
- Явная обработка description: None vs "" vs непустая строка
- Явное условие пересчета Exception: `if contribution_date is not None and contribution_date != old_date`
- TODO комментарий для SELECT FOR UPDATE

### Шаг 4: Исправить delete_contribution()
- Return type: ContributionUpdateResult вместо bool
- contribution_info для UI (сумма, дата, goal_name)
- Единая логика отката статуса для обоих путей

### Шаг 5: Calendar Guard #6
- Добавить после Guard #5 в `open_edit_from_tooltip()`
- Уточненный комментарий про defensive programming
- logger.debug для отладки

### Шаг 6: Goals UI - таблица взносов
- Расширить `_build_contributions_table()`:
  - Добавить колонку "Действия"
  - Кнопки Edit (bi-pencil) и Delete (bi-trash)
  - Pattern-Matching IDs с contribution_id

### Шаг 7: Goals UI - edit contribution modal
- `_build_edit_contribution_modal()`:
  - dcc.Store для contribution_id
  - Поля: amount, date, description
  - Inline dbc.Alert для ошибок
  - Кнопки: Отмена, Сохранить

### Шаг 8: Goals UI - delete confirmation modal
- `_build_delete_contribution_confirm_modal()`:
  - dcc.Store для contribution_id и info
  - Динамический текст: "Удалить взнос {amount} от {date}?"
  - Кнопки: Отмена, Удалить (danger)

### Шаг 9: Goals UI - callbacks
- `open_edit_contribution_modal()` - Pattern-Matching + prefill
- `submit_edit_contribution()` - inline alert или toast
- `open_delete_contribution_modal()` - заполнение message
- `confirm_delete_contribution()` - toast при status_changed

### Шаг 10: Unit тесты
- update_contribution():
  - `test_update_contribution_amount_increase`
  - `test_update_contribution_amount_decrease`
  - `test_update_contribution_amount_zero_error`
  - `test_update_contribution_amount_negative_error`
  - `test_update_contribution_date_within_month`
  - `test_update_contribution_date_across_months_recalculates_exception`
  - `test_update_contribution_date_past_month_error`
  - `test_update_contribution_date_none_no_recalculate` (NEW: критика 🟡 #2)
  - `test_update_contribution_description_sync_transaction`
  - `test_update_contribution_description_empty_string_clears` (NEW: критика 🟢 #4)
  - `test_update_contribution_description_none_no_change` (NEW: критика 🟢 #4)
  - `test_update_contribution_status_completed_to_active`
  - `test_update_contribution_status_active_to_completed`
  - `test_update_contribution_exact_boundary_active` (NEW: критика 🟢 #3)
  - `test_update_contribution_not_found`
- delete_contribution():
  - `test_delete_contribution_with_transaction_id_reverts_status`
  - `test_delete_contribution_without_transaction_id_reverts_status`
  - `test_delete_contribution_returns_contribution_info`
  - `test_delete_contribution_recalculates_exception`
- Calendar guard:
  - `test_calendar_tooltip_blocks_savings_contribution`

## Зависимости
Новых библиотек не требуется. Используются существующие:
- SQLAlchemy (ORM)
- Dash + dash-bootstrap-components (UI)
- loguru (logging)
- pytest (testing)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Race condition при параллельном редактировании | Низкая (MVP = 1 user) | TODO для SELECT FOR UPDATE; single session; flush() без commit() |
| Несинхронизированные данные при ошибке | Средняя | Все операции в одной транзакции; return error ДО изменений |
| Сложность UI callbacks | Средняя | ADR-003 guard clauses; Pattern-Matching с contribution_id |
| Пересчет Exception для прошлых месяцев | Низкая | Запрет смены даты на прошлый месяц (Guard #2) |
| Некорректный статус при удалении | Была средняя | Единая логика отката для обоих путей (с/без transaction_id) |
| Путаница с description None vs "" | Низкая | Явная документация в docstring и тесты |

## Учтённые замечания из критики

| Замечание из critique v2 | Как решено |
|--------------------------|------------|
| 🟡 #1: Уточнить комментарий Guard #6 про виртуальные SAVINGS_CONTRIBUTION | Комментарий расширен: "по дизайну не может быть recurring, guard для defensive programming на случай будущих изменений архитектуры" |
| 🟡 #2: Явно описать условие пересчета Exception | Добавлено явное условие: `if contribution_date is not None and contribution_date != old_date`. Добавлен тест `test_update_contribution_date_none_no_recalculate` |
| 🟢 #3: Добавить тест boundary case для status change | Добавлен тест `test_update_contribution_exact_boundary_active` — новая сумма точно на границе completed/active |
| 🟢 #4: Описать обработку description == "" vs None | Добавлено в docstring: None = не изменять, "" = очистить (default "Взнос: {goal.name}"), непустая = установить. Добавлены тесты `test_update_contribution_description_empty_string_clears` и `test_update_contribution_description_none_no_change` |

## Ответы на вопросы критика

1. **Вопрос:** Delete confirmation UX — показывать ли сумму и дату удаляемого взноса?
   **Ответ:** Да, показывать. Формат: "Удалить взнос 5 000 ₽ от 15.01.2026?" (решение пользователя). Это улучшает UX, предотвращая случайное удаление неправильного взноса. Реализуется через ContributionInfo TypedDict и динамический `delete-contribution-message` в модале.

2. **Вопрос:** Batch delete TODO — стоит ли добавить для future?
   **Ответ:** Нет, не нужен (решение пользователя). Brief явно указывает "out of scope". Добавление TODO создаст лишний шум в коде. Если потребуется в будущем — будет отдельная задача.

## Critical Files for Implementation
- `app/services/goal_service.py` - Core logic: add update_contribution(), get_contribution_by_id(), fix delete_contribution() to return ContributionUpdateResult
- `app/schema/goals.py` - Add ContributionUpdateResult and ContributionInfo TypedDicts with Literal type
- `app/components/goals.py` - UI: edit modal, delete confirm modal with amount/date, table buttons, callbacks, toasts
- `app/components/calendar.py` - Guard #6 for SAVINGS_CONTRIBUTION blocking with defensive programming comment (line ~1045)
- `tests/test_goal_service.py` - Unit tests for update/delete contribution including new boundary and description tests
