# Solution v2: Cascade Contribution Management with Full Guard Coverage

## Обзор решения
Расширяем GoalService новым методом `update_contribution()` для каскадного редактирования взносов с синхронизацией всех связанных сущностей (GoalContribution, Transaction, Goal.current_amount, Exception). Исправляем `delete_contribution()` для корректного отката статуса COMPLETED -> ACTIVE независимо от наличия transaction_id. В Calendar tooltip добавляем Guard #6 для полной блокировки SAVINGS_CONTRIBUTION. В Goals UI добавляем кнопки Edit/Delete в таблице взносов, модал редактирования с inline alert для ошибок и dbc.Modal для подтверждения удаления.

## Архитектура

### Компоненты

1. **GoalService (расширение)**
   - Новый метод `update_contribution()` - основная бизнес-логика редактирования
   - Новый метод `get_contribution_by_id()` - получение взноса для предзаполнения формы
   - Исправленный `delete_contribution()` - возвращает ContributionUpdateResult с флагами статуса
   - Использует `BudgetReservationService.recalculate_current_month_exception()` для пересчета резерва

2. **ContributionUpdateResult TypedDict**
   - Структурированный результат операций edit/delete
   - Содержит флаги `status_changed`, `new_status` для UI toast
   - Literal type для `new_status` обеспечивает type safety

3. **Calendar Guard #6 (calendar.py)**
   - Полная блокировка SAVINGS_CONTRIBUTION в tooltip (после Guard #5)
   - Логирование попыток редактирования
   - Покрывает и реальные транзакции, и гипотетические виртуальные

4. **Goals UI (goals.py)**
   - Расширенная `_build_contributions_table()` с колонкой "Действия"
   - Новый модал `_build_edit_contribution_modal()` с inline alert для ошибок
   - Новый модал `_build_delete_contribution_confirm_modal()` (dbc.Modal)
   - Callbacks для edit/delete операций с Pattern-Matching IDs
   - Toast уведомления при откате статуса

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
  | 1. Validate amount > 0                           |
  | 2. Validate date not in past month               |
  | 3. Get contribution, goal                        |
  | 4. Save old_amount, old_date                     |
  | 5. Update contribution fields                    |
  | 6. Delta calculation: new_amount - old_amount    |
  | 7. Update Goal.current_amount                    |
  | 8. Sync Transaction (amount, date, description)  |
  | 9. If date changed -> recalculate Exception      |
  | 10. Check COMPLETED <-> ACTIVE status change     |
  | 11. Return ContributionUpdateResult with flags   |
  +---------------------------------------------------+
          |
[Callback] -> Update UI + Show inline alert on error OR toast if status_changed
```

## Файловая структура
```
app/schema/goals.py              — +ContributionUpdateResult TypedDict с Literal type
app/services/goal_service.py     — +update_contribution(), +get_contribution_by_id(), fix delete_contribution()
app/components/calendar.py       — +Guard #6 для SAVINGS_CONTRIBUTION (полная блокировка)
app/components/goals.py          — +edit modal, +delete confirm modal, +кнопки Edit/Delete, +callbacks, +toasts
tests/test_goal_service.py       — +тесты для update/delete contribution
tests/test_contribution_edit.py  — новый файл с integration тестами (calendar guard, UI flow)
```

## Ключевые интерфейсы

```python
# app/schema/goals.py
from typing import Literal, TypedDict
from app.models.database import Goal

class ContributionUpdateResult(TypedDict):
    """Результат операции обновления/удаления взноса."""
    success: bool
    goal: Goal | None                                    # Обновленная цель
    status_changed: bool                                 # True если COMPLETED <-> ACTIVE
    new_status: Literal["active", "completed"] | None    # Literal type для type safety
    error: str | None                                    # Сообщение об ошибке (локализовано)


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

        Алгоритм:
        1. Валидация: amount > 0 (если передан)
        2. Валидация: contribution_date не в прошлом месяце
        3. Получить contribution и goal
        4. Сохранить old_amount, old_date
        5. Обновить поля GoalContribution (если переданы)
        6. Delta calculation: new_amount - old_amount
        7. Goal.current_amount += delta
        8. Sync Transaction если contribution.transaction_id:
           - Transaction.amount = new_amount
           - Transaction.transaction_date = new_date
           - Transaction.description = new_description (или "Взнос: {goal.name}")
        9. Если дата изменилась (любой месяц или внутри для fixed_date):
           - recalculate_current_month_exception(old_date)
           - recalculate_current_month_exception(new_date)
        10. Проверить статус:
           - was_completed = (goal.status == COMPLETED)
           - is_completed_now = goal.is_completed (property)
           - Если was_completed AND NOT is_completed_now -> status = ACTIVE
           - Если NOT was_completed AND is_completed_now -> status = COMPLETED
        11. Return ContributionUpdateResult

        Args:
            contribution_id: ID взноса GoalContribution.
            amount: Новая сумма взноса (должна быть > 0).
            contribution_date: Новая дата взноса (не может быть в прошлом месяце).
            description: Новое описание.

        Returns:
            ContributionUpdateResult с результатом операции.
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
# ContributionUpdateResult TypedDict - успех
{
    "success": True,
    "goal": <Goal object>,
    "status_changed": True,       # Цель изменила статус
    "new_status": "active",       # Literal type: "active" | "completed"
    "error": None
}

# ContributionUpdateResult TypedDict - ошибка
{
    "success": False,
    "goal": None,
    "status_changed": False,
    "new_status": None,
    "error": "Сумма взноса должна быть больше 0"  # Локализованное сообщение
}

# Pattern-Matching IDs для кнопок (консистентно с проектом)
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
    # Guard #1: Валидация amount > 0
    if amount is not None and amount <= Decimal("0"):
        return ContributionUpdateResult(
            success=False,
            goal=None,
            status_changed=False,
            new_status=None,
            error="Сумма взноса должна быть больше 0"
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
                error="Дата взноса не может быть в прошлом месяце"
            )

    # Guard #3: Взнос не найден
    contribution = self.session.get(GoalContribution, contribution_id)
    if not contribution:
        return ContributionUpdateResult(
            success=False,
            goal=None,
            status_changed=False,
            new_status=None,
            error="Взнос не найден"
        )

    # ... основная логика ...
```

### UI обработка ошибок (inline alert в модале)
```python
# Callback submit_edit_contribution
def submit_edit_contribution(submit_clicks, amount_value, ...):
    # Guard: ADR-003 pattern
    if ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    try:
        with get_db_session() as session:
            service = GoalService(session)
            result = service.update_contribution(
                contribution_id=contribution_id,
                amount=Decimal(str(amount_value)) if amount_value else None,
                contribution_date=date.fromisoformat(date_value) if date_value else None,
                description=description_value if description_value else None,
            )

            if not result["success"]:
                # Inline alert в модале (модал остается открытым)
                return (
                    True,       # modal stays open
                    no_update,  # contributions table
                    no_update,  # allocation store
                    result["error"],  # inline alert message
                    True,       # show alert
                    False,      # hide toast
                    "",         # toast message
                )

            session.commit()

            # Toast если статус изменился
            if result["status_changed"]:
                goal_name = result["goal"].name
                if result["new_status"] == "active":
                    toast_msg = f"Цель «{goal_name}» снова активна"
                else:
                    toast_msg = f"Цель «{goal_name}» достигнута!"
                return (
                    False, updated_table, allocation_data, "", False, True, toast_msg
                )

            return (
                False, updated_table, allocation_data, "", False, False, ""
            )

    except Exception as e:
        logger.exception("Failed to update contribution")
        return (
            True, no_update, no_update, f"Ошибка: {e}", True, False, ""
        )
```

## План реализации

### Шаг 1: Schema (ContributionUpdateResult)
- Добавить TypedDict в `app/schema/goals.py` с Literal type для new_status
- Экспорт в `app/schema/__init__.py`

### Шаг 2: GoalService.get_contribution_by_id()
- Простой метод для получения взноса по ID (для предзаполнения формы)

### Шаг 3: GoalService.update_contribution()
- Реализовать метод с полной логикой каскадного обновления:
  1. Валидация amount > 0
  2. Валидация: дата не в прошлом месяце
  3. Получить contribution и goal
  4. Сохранить old_amount, old_date
  5. Обновить поля GoalContribution если переданы
  6. Delta calculation: `new_amount - old_amount`
  7. Обновить Goal.current_amount
  8. Синхронизировать Transaction если есть transaction_id:
     - `txn.amount = new_amount`
     - `txn.transaction_date = new_date`
     - `txn.description = new_description or f"Взнос: {goal.name}"`
  9. При смене даты (любой, включая внутри месяца для fixed_date):
     - `recalculate_current_month_exception(user_id, old_date)`
     - `recalculate_current_month_exception(user_id, new_date)`
  10. Проверить и обновить статус COMPLETED <-> ACTIVE
  11. Вернуть ContributionUpdateResult
- Добавить TODO комментарий о SELECT FOR UPDATE для future multi-user

### Шаг 4: Исправить delete_contribution()
- Изменить return type с bool на ContributionUpdateResult
- Добавить проверку и откат статуса ПОСЛЕ обновления current_amount
- Для обоих путей (с transaction_id и без):
  ```python
  # После: goal.current_amount -= amount
  status_changed = False
  new_status = None
  if goal.status == GoalStatus.COMPLETED and not goal.is_completed:
      goal.status = GoalStatus.ACTIVE
      status_changed = True
      new_status = "active"
      logger.info(f"Goal {goal.id} reverted to ACTIVE after contribution delete")
  ```

### Шаг 5: Calendar Guard #6
- В `open_edit_from_tooltip()` добавить guard после Guard #5:
  ```python
  # Guard #5: SAVINGS_RESERVE — read-only, игнорируем клики
  if txn_type == "savings_reserve":
      logger.debug("Tooltip: клик на SAVINGS_RESERVE ignored (read-only)")
      raise PreventUpdate

  # Guard #6: SAVINGS_CONTRIBUTION — редактирование через Goals UI
  if txn_type == "savings_contribution":
      logger.debug("Tooltip: клик на SAVINGS_CONTRIBUTION ignored (use Goals UI)")
      raise PreventUpdate
  ```

### Шаг 6: Goals UI - таблица взносов
- Расширить `_build_contributions_table()`:
  - Добавить колонку "Действия"
  - Кнопки Edit (bi-pencil) и Delete (bi-trash) с Pattern-Matching IDs
  - `{"type": "contribution-edit-btn", "contribution_id": contribution.id}`
  - `{"type": "contribution-delete-btn", "contribution_id": contribution.id}`

### Шаг 7: Goals UI - edit contribution modal
- Создать `_build_edit_contribution_modal()`:
  - dcc.Store для текущего contribution_id ("edit-contribution-id")
  - Поля: amount, date, description (аналогично contribution-modal)
  - Inline dbc.Alert для ошибок валидации (id="edit-contribution-error")
  - Кнопки: Отмена, Сохранить

### Шаг 8: Goals UI - delete confirmation modal
- Создать `_build_delete_contribution_confirm_modal()`:
  - dbc.Modal (не dcc.ConfirmDialog) для консистентности с delete goal
  - dcc.Store для ID удаляемого взноса ("delete-contribution-id")
  - Текст: "Вы уверены, что хотите удалить этот взнос? Это действие нельзя отменить."
  - Кнопки: Отмена, Удалить (color="danger")

### Шаг 9: Goals UI - callbacks
- `open_edit_contribution_modal()`:
  - Pattern-Matching Input на contribution-edit-btn
  - Загружает contribution через GoalService.get_contribution_by_id()
  - Предзаполняет форму
- `submit_edit_contribution()`:
  - Вызывает GoalService.update_contribution()
  - При ошибке показывает inline alert
  - При успехе обновляет таблицу и allocation
  - При status_changed показывает toast
- `open_delete_contribution_modal()`:
  - Открывает confirmation modal
  - Сохраняет contribution_id в Store
- `confirm_delete_contribution()`:
  - Вызывает GoalService.delete_contribution()
  - При status_changed показывает toast
  - Обновляет таблицу и allocation

### Шаг 10: Unit тесты
- Тесты для update_contribution():
  - `test_update_contribution_amount_increase`
  - `test_update_contribution_amount_decrease`
  - `test_update_contribution_amount_zero_error`
  - `test_update_contribution_amount_negative_error`
  - `test_update_contribution_date_within_month`
  - `test_update_contribution_date_across_months_recalculates_exception`
  - `test_update_contribution_date_past_month_error`
  - `test_update_contribution_description_sync_transaction`
  - `test_update_contribution_status_completed_to_active`
  - `test_update_contribution_status_active_to_completed`
  - `test_update_contribution_not_found`
- Тесты для исправленного delete_contribution():
  - `test_delete_contribution_with_transaction_id_reverts_status`
  - `test_delete_contribution_without_transaction_id_reverts_status`
  - `test_delete_contribution_recalculates_exception`
- Integration тест для calendar guard:
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
| Race condition при параллельном редактировании | Низкая (MVP = 1 user) | TODO комментарий для SELECT FOR UPDATE; single session; flush() без commit() |
| Несинхронизированные данные при ошибке | Средняя | Все операции в одной транзакции БД; ContributionUpdateResult возвращает error ДО изменений |
| Сложность UI callbacks | Средняя | ADR-003 guard clauses; Pattern-Matching с contribution_id (не index) |
| Пересчет Exception для прошлых месяцев | Низкая | Запрет смены даты на прошлый месяц (валидация) |
| Некорректный статус при удалении | Средняя (была) | Единая логика отката статуса для обоих путей (с/без transaction_id) |

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🔴 #1: Неполная блокировка SAVINGS_CONTRIBUTION в Calendar tooltip | Guard #6 добавлен после Guard #5 с полным покрытием реальных и виртуальных транзакций; добавлен тест `test_calendar_tooltip_blocks_savings_contribution` |
| 🟡 #2: Отсутствует валидация amount > 0 в update_contribution() | Guard clause в начале метода с return error result; аналогично add_contribution() |
| 🟡 #3: Race condition при обновлении Goal.current_amount | Документировано как TODO для multi-user; MVP = 1 user = низкий риск; предложен SELECT FOR UPDATE для production |
| 🟡 #4: Неясна логика пересчета Exception при смене даты | Всегда пересчитывать для обоих месяцев (old_date и new_date) при любой смене даты в режиме fixed_date; запрет переноса на прошлый месяц |
| 🟡 #5: Подтверждение удаления взноса не описано | dbc.Modal для консистентности с delete goal; Store для ID; кнопки Отмена/Удалить |
| 🟡 #6: Не указан механизм синхронизации Transaction при редактировании | Явный sync: `txn.amount = new_amount`, `txn.transaction_date = new_date`, `txn.description = new_description or f"Взнос: {goal.name}"` |
| 🟢 #7: Отсутствует локализация сообщений об ошибках | Все сообщения на русском; централизованы в return statements для будущей i18n |
| 🟢 #8: Type hint для new_status | `Literal["active", "completed"] \| None` вместо `str \| None` |
| 🟢 #9: Именование Pattern-Matching IDs | `{"type": "contribution-edit-btn", "contribution_id": ...}` вместо `{"type": "edit-contribution-btn", "index": ...}` |

## Ответы на вопросы критика

1. **Вопрос:** При смене даты взноса внутри месяца, нужно ли пересчитывать Exception?
   **Ответ:** Да, пересчитывать Exception всегда при любой смене даты в режиме fixed_date. Это гарантирует консистентность если взнос переносится до/после reserve_day. Например, если reserve_day=15, а взнос был 10-го числа и переносится на 20-е, Exception должен пересчитаться: до переноса взнос учитывался в уменьшении резерва (был < 15), после — уже не должен (стал > 15). Вызов `recalculate_current_month_exception()` идемпотентен и корректно обрабатывает оба случая.

2. **Вопрос:** Какой UX предпочтителен для подтверждения удаления?
   **Ответ:** dbc.Modal для консистентности с delete goal. Модал содержит: заголовок "Удаление взноса", текст предупреждения, кнопки Отмена (secondary) и Удалить (danger). dcc.Store хранит contribution_id для передачи между callbacks.

3. **Вопрос:** Разрешено ли менять дату взноса на прошлый месяц?
   **Ответ:** Нет, запрещено. Валидация в update_contribution() проверяет `(contribution_date.year, contribution_date.month) < (today.year, today.month)` и возвращает ошибку. Обоснование: проще реализация, меньше edge cases с Exception для прошлых месяцев (guard в recalculate: `if reserve_date < date.today(): return False`), пользовательский сценарий переноса в прошлое редок.

4. **Вопрос:** При ошибке валидации использовать toast или inline alert?
   **Ответ:** Inline alert в модале (стандартный паттерн проекта для форм). Модал остается открытым, пользователь видит ошибку рядом с полем ввода, может исправить и повторить. Toast используется только для успешных операций с побочным эффектом (status_changed). dbc.Alert с id="edit-contribution-error" показывается при success=False.

## Critical Files for Implementation
- `app/services/goal_service.py` - Core logic: add update_contribution(), get_contribution_by_id(), fix delete_contribution() return type
- `app/schema/goals.py` - Add ContributionUpdateResult TypedDict with Literal type
- `app/components/goals.py` - UI: edit modal, delete confirm modal, table buttons, callbacks, toasts
- `app/components/calendar.py` - Guard #6 for SAVINGS_CONTRIBUTION blocking (line ~1045)
- `tests/test_goal_service.py` - Unit tests for update/delete contribution
