# Critique - Solution v1
Date: 2026-02-02
Reviewer: AI Critic (Claude Opus 4.5)

---

## 🎯 Общая оценка

**Рейтинг:** ⭐⭐⭐⭐ (4/5)

**Вердикт:**
- [ ] Отлично, можно кодировать как есть
- [x] Хорошо, с минорными улучшениями
- [ ] Требуются значительные изменения
- [ ] Не рекомендуется, нужен другой подход

**Краткая суммаризация:**
Решение хорошо структурировано, использует существующие паттерны проекта (TypedDict, ADR-003 guards, flush/commit contract). Основная логика каскадного обновления продумана корректно. Требуются уточнения по edge cases и доработка Guard #6 для полной блокировки SAVINGS_CONTRIBUTION.

---

## Сильные стороны

1. **Следование существующим паттернам проекта**
   - ContributionUpdateResult TypedDict соответствует стилю RedistributionPreview, AllocationResult
   - Guard clauses по ADR-003 в calendar.py
   - Flush/commit contract (сервис flush(), caller commit())

2. **Правильная декомпозиция обязанностей**
   - GoalService отвечает за бизнес-логику взносов
   - BudgetReservationService используется для пересчета Exception (не дублируется)
   - UI callbacks тонкие, делегируют в сервис

3. **Полная диаграмма взаимодействия**
   - Четко описан data flow: UI -> Callback -> Service -> DB -> Result -> Toast
   - Понятно какие сущности обновляются на каждом шаге

4. **Учет двух режимов резервирования**
   - Решение корректно различает fixed_date (без transaction_id) и from_balance (с transaction_id)
   - Пересчет Exception вызывается при смене даты между месяцами

5. **Продуманная обработка статусов**
   - COMPLETED -> ACTIVE при уменьшении суммы
   - ACTIVE -> COMPLETED при достижении target_amount
   - status_changed флаг для toast уведомлений

---

## 🔴 Критичные проблемы (Blockers)

### 1. Неполная блокировка SAVINGS_CONTRIBUTION в Calendar tooltip

**Где:**
- `app/components/calendar.py`, секция "Calendar Guard #6"
- Solution-v1.md: "Guard #6 для блокировки SAVINGS_CONTRIBUTION в tooltip"

**Проблема:**
Guard #5 уже блокирует SAVINGS_RESERVE, но Guard #6 для SAVINGS_CONTRIBUTION описан поверхностно. В текущем коде `open_edit_from_tooltip()` после Guard #5 сразу идет логика для виртуальных recurring операций. Нужно определить точную позицию Guard #6 и убедиться, что он покрывает ОБА сценария:
1. Реальная транзакция SAVINGS_CONTRIBUTION (is_virtual=False)
2. Виртуальная операция (хотя SAVINGS_CONTRIBUTION не должна быть recurring по бизнес-логике)

**Почему критично:**
- Если пользователь кликнет на SAVINGS_CONTRIBUTION в tooltip, откроется edit modal с неправильным контекстом
- Изменение через Calendar обойдет логику каскадного обновления Goal.current_amount

**Пример сценария:**
```
User кликает на "Взнос: Отпуск" в calendar tooltip
  -> открывается edit modal для транзакции
  -> user изменяет сумму 5000 -> 3000
  -> Transaction.amount обновляется
  -> GoalContribution.amount НЕ обновляется (!)
  -> Goal.current_amount НЕ обновляется (!)
  -> Данные рассинхронизированы
```

**Рекомендация:**
```python
# Guard #6: SAVINGS_CONTRIBUTION — redirect to Goals UI
if txn_type == "savings_contribution":
    logger.debug("Tooltip: клик на SAVINGS_CONTRIBUTION, redirect to Goals UI")
    raise PreventUpdate
    # TODO: В будущем можно показать toast "Редактируйте взносы на странице Цели"
```

Также добавить тест: `test_calendar_tooltip_blocks_savings_contribution`.

---

## 🟡 Важные проблемы (Should Fix)

### 2. Отсутствует валидация amount > 0 в update_contribution()

**Где:**
- `app/services/goal_service.py`, метод `update_contribution()`
- Solution-v1.md: "Сумма <= 0 -> ValidationError"

**Проблема:**
В описании указано "Сумма <= 0 -> ValidationError", но в интерфейсе метода нет явной проверки. В add_contribution() такая проверка есть (строка 135-136), но для update нужно добавить аналогичную.

**Почему важно:**
- Без валидации можно установить amount=0 или отрицательное значение
- Goal.current_amount может стать отрицательным

**Рекомендация:**
```python
def update_contribution(
    self,
    contribution_id: int,
    amount: Decimal | None = None,
    ...
) -> ContributionUpdateResult:
    # Guard: amount validation
    if amount is not None and amount <= 0:
        return ContributionUpdateResult(
            success=False,
            goal=None,
            status_changed=False,
            new_status=None,
            error="Сумма взноса должна быть больше 0"
        )
```

---

### 3. Race condition при обновлении Goal.current_amount

**Где:**
- `app/services/goal_service.py`, update_contribution() шаг 5

**Проблема:**
При delta calculation `new_amount - old_amount` и последующем `goal.current_amount += delta` возможна race condition, если два пользователя одновременно редактируют взносы одной цели.

**Почему важно:**
- MVP с одним пользователем это не проблема
- При масштабировании до семейного бюджета (несколько пользователей на одну цель) это станет критичным

**Рекомендация:**
Для MVP достаточно документировать ограничение. Для production:
```python
# Вариант A: Optimistic locking с version column
# Вариант B: SELECT FOR UPDATE
goal = self.session.query(Goal).filter_by(id=goal_id).with_for_update().first()
```

Добавить TODO комментарий в код.

---

### 4. Неясна логика пересчета Exception при смене даты

**Где:**
- Solution-v1.md: "При смене даты между месяцами вызвать recalculate_current_month_exception() для обоих месяцев"

**Проблема:**
Не описано, что происходит когда:
1. Дата меняется ВНУТРИ одного месяца (например, 5 января -> 15 января)
2. Дата меняется на прошлый месяц (например, январь -> декабрь прошлого года)

Метод `recalculate_current_month_exception()` имеет guard: `if reserve_date < date.today(): return False`.
Это означает, что для прошлых месяцев пересчет НЕ произойдет.

**Почему важно:**
- При переносе взноса из текущего месяца в прошлый, Exception текущего месяца не пересчитается корректно
- Пользователь может создать inconsistent state

**Рекомендация:**
Добавить в brief.md ограничение: "Дата взноса не может быть изменена на прошлый месяц" ИЛИ расширить логику:
```python
# В update_contribution():
if old_date.month != new_date.month:
    # Для старого месяца — пересчет если >= today
    budget_service.recalculate_current_month_exception(user_id, old_date)
    # Для нового месяца — пересчет если >= today
    budget_service.recalculate_current_month_exception(user_id, new_date)
```

---

### 5. Подтверждение удаления взноса не описано

**Где:**
- Solution-v1.md: "delete_contribution_handler() - удаление с подтверждением"

**Проблема:**
Упомянуто "с подтверждением", но не описан механизм:
- Будет ли confirm modal?
- Browser confirm()?
- Delete без подтверждения?

**Почему важно:**
- Удаление взноса необратимо (нет undo)
- UX ожидания пользователя

**Рекомендация:**
Использовать dbc.Modal для подтверждения по аналогии с delete goal. Добавить в план:
- `_build_delete_contribution_confirm_modal()`
- Store для contribution_to_delete_id
- Callback для confirm/cancel

---

### 6. Не указан механизм синхронизации Transaction при редактировании

**Где:**
- Solution-v1.md: "4. Sync Transaction if exists"

**Проблема:**
При редактировании взноса в режиме from_balance, кроме Transaction.amount, нужно обновить:
- Transaction.transaction_date (если меняется дата)
- Transaction.description (если меняется описание)

В solution указано только "Sync Transaction if exists" без деталей.

**Почему важно:**
- При изменении даты взноса, транзакция в календаре останется на старой дате
- Calendar будет показывать неактуальные данные

**Рекомендация:**
Расширить шаг 4:
```python
# 4. Sync Transaction if exists
if contribution.transaction_id:
    txn = self.session.get(Transaction, contribution.transaction_id)
    if txn:
        if amount is not None:
            txn.amount = amount
        if contribution_date is not None:
            txn.transaction_date = contribution_date
        if description is not None:
            txn.description = f"Взнос: {goal.name}" if not description else description
```

---

## 🟢 Незначительные замечания (Optional)

### 7. Отсутствует локализация сообщений об ошибках

**Где:**
- ContributionUpdateResult.error

**Проблема:**
Сообщения типа "Взнос не найден" hardcoded в сервисе. При интернационализации потребуется рефакторинг.

**Рекомендация:**
Для MVP достаточно. Для будущего — вынести в константы или использовать error codes.

---

### 8. Type hint для new_status

**Где:**
- ContributionUpdateResult TypedDict: `new_status: str | None`

**Рекомендация:**
Использовать Literal для type safety:
```python
from typing import Literal

new_status: Literal["active", "completed"] | None
```

---

### 9. Именование Pattern-Matching IDs

**Где:**
- `{"type": "edit-contribution-btn", "index": contribution_id}`

**Рекомендация:**
Использовать консистентный стиль с остальными компонентами:
```python
# Текущий стиль в проекте (goals.py):
{"type": "goal-card", "goal_id": ...}
# Предлагаемый:
{"type": "contribution-edit-btn", "contribution_id": ...}
```

---

## 📊 Детальный анализ по аспектам

### Аспект 1: Соответствие требованиям

**Статус:** ⚠️ Частично

**Детали:**
- FR-1 (edit amount): Покрыт, но без валидации amount > 0
- FR-2 (edit date): Покрыт частично, нет деталей Exception пересчета
- FR-3 (edit description): Покрыт, нет деталей sync Transaction.description
- FR-4 (delete): Покрыт, но confirmation UI не описан
- FR-5 (block SAVINGS_CONTRIBUTION): Пропущены детали Guard #6
- FR-6 (UI buttons): Покрыт
- FR-7 (edit modal): Покрыт
- FR-8 (toasts): Покрыт

**Комментарий:**
Все требования упомянуты, но некоторые требуют доработки деталей реализации.

### Аспект 2: Архитектурное качество

**Статус:** Хорошо

**Детали:**
- SOLID: SRP соблюден (GoalService - бизнес-логика, BudgetReservationService - резервы)
- Coupling: Низкий, использует существующие сервисы через dependency injection
- Cohesion: Высокий, update_contribution() содержит всю связанную логику

**Проблемы:**
- GoalService уже содержит методы для User (get/update_savings_mode) — TODO есть в коде

### Аспект 3: Производительность

**Статус:** Хорошо

**Детали:**
- Сложность алгоритмов: O(1) для update, O(n) для shift-down при приоритетах
- Bottlenecks: Нет (single session, single commit)
- NFR-2: < 100ms — достижимо

### Аспект 4: Обработка ошибок

**Статус:** ⚠️ Частично

**Детали:**
- Покрытие ошибок: 70%
- Edge cases: amount <= 0 не покрыт в update
- Fallback стратегии: Есть (return error result)

### Аспект 5: Безопасность

**Статус:** Хорошо

**Детали:**
- Input validation: Частично (amount)
- SQL injection protection: Да (SQLAlchemy ORM)
- Secrets management: N/A
- Authorization: Нет проверки user_id (MVP ограничение)

### Аспект 6: Сложность реализации

**Статус:** Хорошо

**Детали:**
- Реалистичность оценки: Да, 8 шагов разумны
- Скрытая сложность: Exception пересчет для прошлых месяцев
- Зависимости: Используются существующие, новых нет

### Аспект 7: Альтернативные подходы

**Статус:** Хорошо

**Детали:**
- Рассмотрены альтернативы: Нет
- Обоснование выбора: Следует существующим паттернам

---

## 🔄 Альтернативные подходы

### Подход A: Единый метод update_or_delete_contribution()

**Идея:**
Объединить update и delete в один метод с флагом delete=True.

**Плюсы:**
- Один callback вместо двух
- Проще тестировать

**Минусы:**
- Нарушает SRP
- Менее читаемый код

**Рекомендация:**
Текущий подход с раздельными методами лучше. Не рекомендую менять.

---

## ❓ Вопросы для архитектора

1. **Режим fixed_date**: При смене даты взноса внутри месяца, нужно ли пересчитывать Exception? (Сейчас пересчет только при смене месяца)

2. **Подтверждение удаления**: Какой UX предпочтителен — dbc.Modal или browser confirm()? С учетом того что delete goal использует Modal.

3. **Редактирование даты на прошлое**: Разрешено ли менять дату взноса на прошлый месяц? Это усложнит логику Exception.

4. **Toast vs Alert**: При ошибке валидации использовать toast или inline alert в модале?

---

## 📋 Рекомендации для следующей итерации

### Обязательно:
1. Детализировать Guard #6 для SAVINGS_CONTRIBUTION с точным кодом и тестом
2. Добавить валидацию amount > 0 в update_contribution()

### Желательно:
3. Описать механизм confirmation для delete_contribution
4. Уточнить логику sync Transaction (amount, date, description)
5. Добавить ограничение/логику для редактирования дат прошлых месяцев

### Опционально:
6. Literal type для new_status
7. Консистентное именование Pattern-Matching IDs

---

## 🔄 Изменения с предыдущей итерации

(Не применимо — это первая итерация v1)

---

## 💭 Заметки критика

Решение демонстрирует хорошее понимание существующей архитектуры проекта. Автор корректно использует паттерны (TypedDict, ADR-003 guards, flush/commit contract) и интегрируется с BudgetReservationService.

Основная область для улучшения — детализация edge cases, особенно:
1. Блокировка SAVINGS_CONTRIBUTION в calendar tooltip
2. Обработка изменения дат между месяцами/в прошлое
3. UI confirmation flow для delete

После исправления критичной проблемы #1 и важных проблем #2, #5, #6 решение будет готово к реализации.