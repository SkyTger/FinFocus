# Solution v1: Cascade Contribution Management

## Обзор решения
Расширяем GoalService новым методом `update_contribution()` для каскадного редактирования взносов с синхронизацией связанных сущностей. Исправляем `delete_contribution()` для корректного отката статуса COMPLETED → ACTIVE независимо от наличия transaction_id. В Calendar tooltip добавляем guard для блокировки SAVINGS_CONTRIBUTION. В Goals UI добавляем кнопки Edit/Delete в таблицу взносов и модал редактирования.

## Архитектура

### Компоненты

1. **GoalService (расширение)**
   - Новый метод `update_contribution()` - основная бизнес-логика редактирования
   - Исправленный `delete_contribution()` - корректный откат статуса для всех режимов
   - Использует `BudgetReservationService.recalculate_current_month_exception()` для пересчета резерва

2. **ContributionUpdateResult TypedDict**
   - Структурированный результат операций edit/delete
   - Содержит флаги status_changed, new_status для UI toast

3. **Calendar Guard (calendar.py)**
   - Guard #6 для блокировки SAVINGS_CONTRIBUTION в tooltip
   - Логирование попыток редактирования

4. **Goals UI (goals.py)**
   - Расширенная `_build_contributions_table()` с кнопками Edit/Delete
   - Новый модал `_build_edit_contribution_modal()`
   - Callbacks для edit/delete операций
   - Toast уведомления при откате статуса

### Диаграмма взаимодействия
```
User clicks Edit in contribution table
          ↓
[Goals UI] → open edit-contribution-modal
          ↓
User submits form
          ↓
[Callback] → GoalService.update_contribution(...)
          ↓
  ┌───────┴───────────────────────┐
  │ update_contribution():         │
  │ 1. Get contribution, goal     │
  │ 2. Calculate delta            │
  │ 3. Update amount/date/desc    │
  │ 4. Sync Transaction if exists │
  │ 5. Update Goal.current_amount │
  │ 6. Check COMPLETED ↔ ACTIVE   │
  │ 7. Recalculate Exception      │
  │ 8. Return result with flags   │
  └───────────────────────────────┘
          ↓
[Callback] → Update UI + Show toast if status_changed
```

## Файловая структура
```
app/schema/goals.py              — +ContributionUpdateResult TypedDict
app/services/goal_service.py     — +update_contribution(), fix delete_contribution()
app/components/calendar.py       — +Guard #6 для SAVINGS_CONTRIBUTION
app/components/goals.py          — +edit modal, +кнопки Edit/Delete, +callbacks, +toasts
tests/test_goal_service.py       — +тесты для update/delete contribution
tests/test_contribution_edit.py  — новый файл с integration тестами
```

## Ключевые интерфейсы

```python
# app/schema/goals.py
class ContributionUpdateResult(TypedDict):
    """Результат операции обновления/удаления взноса."""
    success: bool
    goal: Goal | None           # Обновленная цель
    status_changed: bool        # True если COMPLETED ↔ ACTIVE
    new_status: str | None      # "active" | "completed" | None
    error: str | None           # Сообщение об ошибке


# app/services/goal_service.py
class GoalService:
    def update_contribution(
        self,
        contribution_id: int,
        amount: Decimal | None = None,
        contribution_date: date | None = None,
        description: str | None = None,
    ) -> ContributionUpdateResult:
        """Редактирует взнос с каскадным обновлением связанных сущностей.

        Args:
            contribution_id: ID взноса GoalContribution.
            amount: Новая сумма взноса (если передана).
            contribution_date: Новая дата взноса (если передана).
            description: Новое описание (если передано).

        Returns:
            ContributionUpdateResult с результатом операции.
        """

    def delete_contribution(
        self,
        contribution_id: int,
    ) -> ContributionUpdateResult:
        """Удаляет взнос с откатом состояния цели.

        Теперь корректно откатывает статус COMPLETED → ACTIVE
        для взносов БЕЗ transaction_id (режим fixed_date).

        Returns:
            ContributionUpdateResult с результатом операции.
        """
```

## Модель данных

```python
# ContributionUpdateResult TypedDict
{
    "success": True,
    "goal": <Goal object>,
    "status_changed": True,       # Цель изменила статус
    "new_status": "active",       # или "completed"
    "error": None
}

# При ошибке
{
    "success": False,
    "goal": None,
    "status_changed": False,
    "new_status": None,
    "error": "Взнос не найден"
}
```

## Обработка ошибок

1. **Взнос не найден** → return error result, UI показывает alert
2. **Сумма <= 0** → ValidationError, UI показывает validation message
3. **Дата в будущем при редактировании** → разрешено (нет ограничения)
4. **DB error** → exception propagates, transaction rollback

```python
# Custom error handling в callback
def submit_edit_contribution(...):
    try:
        with get_db_session() as session:
            service = GoalService(session)
            result = service.update_contribution(...)

            if not result["success"]:
                return no_update, True, result["error"]  # error alert

            session.commit()

            # Toast если статус изменился
            if result["status_changed"]:
                toast_message = f"Цель «{result['goal'].name}» снова активна"
                return True, False, toast_message

    except Exception as e:
        logger.exception("Failed to update contribution")
        return no_update, True, str(e)
```

## План реализации

### Шаг 1: Schema (ContributionUpdateResult)
- Добавить TypedDict в `app/schema/goals.py`
- Экспорт в `app/schema/__init__.py`

### Шаг 2: GoalService.update_contribution()
- Реализовать метод с полной логикой:
  1. Получить contribution и goal
  2. Сохранить old_amount, old_date
  3. Обновить поля если переданы
  4. Delta calculation: `new_amount - old_amount`
  5. Обновить Goal.current_amount
  6. Синхронизировать Transaction если есть transaction_id
  7. При смене даты между месяцами вызвать recalculate_current_month_exception() для обоих месяцев
  8. Проверить и обновить статус COMPLETED ↔ ACTIVE
  9. Вернуть ContributionUpdateResult

### Шаг 3: Исправить delete_contribution()
- Добавить проверку и откат статуса ПОСЛЕ обновления current_amount
- Возвращать ContributionUpdateResult вместо bool

### Шаг 4: Calendar Guard #6
- В `open_edit_from_tooltip()` добавить guard после Guard #5
- Логировать попытки редактирования SAVINGS_CONTRIBUTION

### Шаг 5: Goals UI - таблица взносов
- Расширить `_build_contributions_table()`:
  - Добавить колонку "Действия"
  - Кнопки Edit (карандаш) и Delete (корзина) с Pattern-Matching IDs
  - `{"type": "edit-contribution-btn", "index": contribution_id}`
  - `{"type": "delete-contribution-btn", "index": contribution_id}`

### Шаг 6: Goals UI - edit contribution modal
- Создать `_build_edit_contribution_modal()`:
  - dcc.Store для текущего contribution_id
  - Поля: amount, date, description (как в contribution-modal)
  - Кнопки: Отмена, Сохранить

### Шаг 7: Goals UI - callbacks
- `open_edit_contribution_modal()` - открытие модала с предзаполнением
- `submit_edit_contribution()` - сохранение изменений
- `delete_contribution_handler()` - удаление с подтверждением
- Toast callback для показа уведомлений

### Шаг 8: Unit тесты
- Тесты для update_contribution():
  - amount increase/decrease
  - date change within month
  - date change across months (fixed_date exception recalc)
  - status COMPLETED → ACTIVE
  - status ACTIVE → COMPLETED
- Тесты для исправленного delete_contribution():
  - delete без transaction_id с откатом статуса
- Integration тест для calendar guard

## Зависимости
Новых библиотек не требуется. Используются существующие:
- SQLAlchemy (ORM)
- Dash + dash-bootstrap-components (UI)
- loguru (logging)
- pytest (testing)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Race condition при параллельном редактировании | Низкая | Используем session.flush() и single DB transaction |
| Несинхронизированные данные при ошибке | Средняя | Все операции в одной транзакции, rollback при exception |
| Сложность UI callbacks | Средняя | Следуем ADR-003 паттерну guard clauses |
| Пересчет Exception для прошлых месяцев | Низкая | Guard: не пересчитываем если reserve_date < today |

## Critical Files for Implementation
- `app/services/goal_service.py` - Core logic: add update_contribution(), fix delete_contribution()
- `app/schema/goals.py` - Add ContributionUpdateResult TypedDict
- `app/components/goals.py` - UI: edit modal, table buttons, callbacks
- `app/components/calendar.py` - Guard #6 for SAVINGS_CONTRIBUTION blocking
- `tests/test_goal_service.py` - Unit tests for update/delete contribution
