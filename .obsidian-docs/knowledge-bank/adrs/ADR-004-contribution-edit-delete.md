---
name: adr-004-contribution-edit-delete
description: ADR-004 — решение о редактировании и удалении взносов в цели (GoalContribution), каскадная синхронизация с Transaction/Goal
type: project
originSessionId: a7066508-1d51-418c-a40d-a34902bde2ab
---

# ADR-004: Редактирование и удаление взносов в цели

**Статус**: Принято
**Дата**: 2026-02-02
**Контекст**: Протокол 0019 (планируется)

## Контекст

Взносы в накопительные цели (GoalContribution) сейчас можно только создавать и удалять. Редактирование не реализовано. Пользователь хочет иметь возможность:
1. Редактировать сумму, дату и описание взноса
2. Удалять взнос с корректным откатом состояния цели

### Текущее состояние

| Операция | Статус | Метод |
|----------|--------|-------|
| Создание | ✅ | `GoalService.add_contribution()` |
| Удаление | ⚠️ Частичное | `GoalService.delete_contribution()` |
| Редактирование | ❌ | Не реализовано |

### Выявленные проблемы

#### Проблема 1: SAVINGS_CONTRIBUTION кликабельна в calendar tooltip

**Критичность**: Высокая

В `calendar.py:open_edit_from_tooltip()`:
- `SAVINGS_RESERVE` заблокирована (guard на строках 1041-1044)
- `SAVINGS_CONTRIBUTION` **НЕ заблокирована**

При клике на SAVINGS_CONTRIBUTION в tooltip:
1. Открывается стандартный edit modal
2. `TransactionService.update_transaction()` обновляет Transaction
3. **GoalContribution.amount НЕ обновляется**
4. **Goal.current_amount НЕ обновляется**
5. **Рассинхронизация данных!**

#### Проблема 2: delete_contribution() не откатывает статус для взносов без transaction_id

**Критичность**: Средняя

```python
# GoalService.delete_contribution()
if contribution.transaction_id:
    budget_service.delete_contribution_transaction(...)  # ← Откат статуса ЕСТЬ
else:
    self.session.delete(contribution)  # ← Откат статуса ОТСУТСТВУЕТ!
```

В режиме `fixed_date` взносы создаются без transaction_id. При их удалении:
- Goal.current_amount уменьшается ✅
- Статус COMPLETED → ACTIVE **НЕ откатывается** ❌

#### Проблема 3: update_contribution_transaction() работает только для from_balance

**Критичность**: Средняя

`BudgetReservationService.update_contribution_transaction()` существует и работает корректно:
- Обновляет Transaction + GoalContribution + Goal.current_amount
- Проверяет статус COMPLETED ↔ ACTIVE
- Вызывает `recalculate_current_month_exception()`

**НО**: Работает только для взносов с `transaction_id` (режим from_balance).
Для режима `fixed_date` (взносы без transaction_id) логика отсутствует.

## Решение

### 1. Блокировка SAVINGS_CONTRIBUTION в calendar tooltip

**Файл**: `app/components/calendar.py`

Добавить guard после проверки SAVINGS_RESERVE:

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

**Обоснование**: Взносы — часть логики целей, не обычные транзакции. Редактирование должно происходить через Goals UI для консистентности.

### 2. Новый метод GoalService.update_contribution()

**Файл**: `app/services/goal_service.py`

```python
def update_contribution(
    self,
    contribution_id: int,
    amount: Decimal | None = None,
    contribution_date: date | None = None,
    description: str | None = None,
) -> ContributionUpdateResult:
    """Редактирует взнос с каскадным обновлением связанных сущностей.

    Алгоритм:
    1. Получить GoalContribution, сохранить old_amount, old_date
    2. Обновить поля (если переданы)
    3. Если amount изменился:
       - delta = new_amount - old_amount
       - Goal.current_amount += delta
       - Если есть transaction_id → обновить Transaction.amount
    4. Если date изменился:
       - Если есть transaction_id → обновить Transaction.transaction_date
       - [fixed_date] пересчитать Exception для старого И нового месяца
    5. Если description изменился и есть transaction_id:
       - Обновить Transaction.description
    6. Проверить статус:
       - was_completed = (status == COMPLETED)
       - is_completed_now = Goal.is_completed
       - Если was_completed AND NOT is_completed_now → status = ACTIVE
       - Если NOT was_completed AND is_completed_now → status = COMPLETED
    7. Вернуть результат с флагом status_changed

    Returns:
        ContributionUpdateResult с success, goal, status_changed, new_status, error
    """
```

### 3. Исправление delete_contribution()

**Файл**: `app/services/goal_service.py`

Добавить откат статуса для взносов без transaction_id:

```python
def delete_contribution(self, contribution_id: int) -> ContributionUpdateResult:
    # ... существующая логика ...

    # После обновления current_amount:
    goal.current_amount -= amount
    if goal.current_amount < Decimal("0"):
        goal.current_amount = Decimal("0")

    # НОВОЕ: Проверка отката статуса
    status_changed = False
    new_status = None
    if goal.status == GoalStatus.COMPLETED and not goal.is_completed:
        goal.status = GoalStatus.ACTIVE
        status_changed = True
        new_status = "active"
        logger.info(f"Goal {goal.id} reverted to ACTIVE after contribution delete")

    # ... recalculate_current_month_exception ...

    return ContributionUpdateResult(
        success=True,
        goal=goal,
        status_changed=status_changed,
        new_status=new_status,
        error=None,
    )
```

### 4. TypedDict для результата

**Файл**: `app/schema/goals.py`

```python
class ContributionUpdateResult(TypedDict):
    success: bool
    goal: Goal | None
    status_changed: bool        # True если COMPLETED ↔ ACTIVE
    new_status: str | None      # "active" | "completed" | None
    error: str | None
```

### 5. Goals UI: кнопки Edit/Delete в таблице взносов

**Файл**: `app/components/goals.py`

- Добавить кнопки Edit (карандаш) и Delete (корзина) для каждого взноса
- Модал редактирования (copy от contribution-modal, но с предзаполнением)
- Callbacks для edit/delete с Pattern-Matching IDs
- Toast уведомления:
  - При удалении: "Взнос удалён"
  - При откате статуса: "Цель «{name}» снова активна и участвует в распределении бюджета"

### 6. Пересчёт Exception при смене месяца

**Файл**: `app/services/budget_reservation_service.py`

При изменении даты взноса между месяцами (режим fixed_date):

```python
# В update_contribution():
if old_month != new_month:
    # Пересчитать exception для старого месяца (взнос ушёл)
    budget_service.recalculate_current_month_exception(user_id, old_date)
    # Пересчитать exception для нового месяца (взнос пришёл)
    budget_service.recalculate_current_month_exception(user_id, new_date)
```

## Альтернативы (отвергнуты)

### Альтернатива A: Редактирование через calendar tooltip

**Описание**: Разрешить редактирование SAVINGS_CONTRIBUTION через стандартный edit modal.

**Причина отказа**:
- Нужно модифицировать `TransactionService.update_transaction()` для определения типа
- Смешивание логики транзакций и взносов
- Взносы имеют специфичную логику (Goal.current_amount, статус, Exception)
- Нарушение Single Responsibility Principle

### Альтернатива B: Универсальный contribution через calendar

**Описание**: Редактирование взноса через calendar redirect на Goals.

**Причина отказа**:
- Сложная навигация (redirect + scroll + highlight)
- Пользователь теряет контекст
- Проще заблокировать клик и показать hint

## Последствия

### Положительные

1. **Консистентность**: Все операции с взносами через Goals UI
2. **Целостность данных**: GoalContribution, Transaction, Goal.current_amount всегда синхронизированы
3. **Корректный откат статуса**: COMPLETED → ACTIVE при уменьшении суммы или удалении
4. **UX**: Понятные кнопки Edit/Delete, toast уведомления

### Отрицательные

1. **Дополнительный код**: ~300-400 строк в goals.py
2. **Блокировка в calendar**: Пользователь не может редактировать взнос напрямую из календаря

### Нейтральные

1. **Обратная совместимость**: Существующие взносы продолжат работать
2. **Миграция не требуется**: Изменения только в бизнес-логике и UI

## Связанные файлы

| Файл | Изменения |
|------|-----------|
| `app/services/goal_service.py` | +update_contribution(), fix delete_contribution() |
| `app/services/budget_reservation_service.py` | Без изменений (уже есть update_contribution_transaction) |
| `app/components/calendar.py` | +guard для SAVINGS_CONTRIBUTION |
| `app/components/goals.py` | +edit modal, +callbacks, +toasts |
| `app/schema/goals.py` | +ContributionUpdateResult TypedDict |
| `tests/test_goal_service.py` | +тесты для update/delete contribution |

## Тестовые сценарии

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Edit amount (увеличение) | Goal.current_amount увеличивается, возможен COMPLETED |
| Edit amount (уменьшение) | Goal.current_amount уменьшается, возможен откат ACTIVE |
| Edit date (в пределах месяца) | Transaction.date обновляется |
| Edit date (между месяцами, fixed_date) | Оба месяца пересчитаны (Exception) |
| Delete (from_balance) | Transaction + GoalContribution удалены |
| Delete (fixed_date) | GoalContribution удалён, Exception пересчитан |
| Delete с откатом COMPLETED | Статус → ACTIVE, toast показан |
| Click SAVINGS_CONTRIBUTION в calendar | PreventUpdate (заблокировано) |

## Ссылки

- [features.md](../features.md) — описание накопительных целей
- [modules/services.md](../modules/services.md) — GoalService, BudgetReservationService
- [ADR-003](../../docs/adr/ADR-003-pattern-matching-callbacks-issue.md) — Pattern-Matching callbacks
