ы# Спецификация: Исправление багов режима fixed_date

## Контекст

Протоколы 0016-0017 реализовали интеграцию бюджета целей с календарём и режим `fixed_date`. При тестировании выявлены критические баги:

1. **Взносы не учитываются после переключения режима** — при переключении `from_balance → fixed_date → from_balance → fixed_date` ранее внесённые суммы "забываются"
2. **Exception сбрасывается при переключении режима** — досрочный взнос создаёт exception (резерв 50000→40000), но после переключения режимов exception теряется и резерв снова показывает полную сумму

## Анализ корневых причин

### Причина 1: Создание нового шаблона при каждом переключении

```python
# set_mode() в budget_reservation_service.py
def set_mode(self, user_id, mode, day_of_month):
    if mode == "fixed_date":
        self._stop_reserve_template(user_id)      # Останавливает старый (recurring_end_date=yesterday)
        template = self._create_reserve_template(user_id, day_of_month)  # Создаёт НОВЫЙ
```

**Проблема:**
- Exceptions привязаны к `recurring_parent_id` (ID старого шаблона)
- Новый шаблон имеет новый ID → старые exceptions не применяются
- `get_instances_with_exceptions()` генерирует виртуальные экземпляры только для активных шаблонов

### Причина 2: Отсутствие пересчёта exceptions

При изменении взносов/бюджета exceptions НЕ пересчитываются:

| Операция | Текущее поведение | Ожидаемое |
|----------|-------------------|-----------|
| Удаление взноса | Exception не обновляется | Пересчитать exception |
| Изменение суммы взноса | Exception не обновляется | Пересчитать exception |
| Изменение бюджета | Только шаблон обновляется | Пересчитать все exceptions месяца |

### Причина 3: Несогласованность `used_budget`

В режиме `fixed_date`:
- `_get_reserve_sum_for_month()` суммирует только `SAVINGS_RESERVE` транзакции
- Виртуальные экземпляры НЕ в БД → до даты резерва `used = 0`
- Досрочные взносы (GoalContribution) НЕ учитываются в `used`

**Результат:** пользователь внёс 10000, но UI показывает "Зарезервировано: 0 / 50000"

---

## Принятые решения

### Решение 1: Переиспользование шаблона

**Логика `set_mode("fixed_date", day)`:**

```
1. Найти существующий шаблон (даже остановленный)
2. ЕСЛИ день совпадает:
   - Реактивировать шаблон (recurring_end_date = None)
   - Exceptions сохранятся
3. ИНАЧЕ (день изменился):
   - Остановить старый шаблон
   - Удалить orphan exceptions (для дат после recurring_end_date)
   - Создать новый шаблон
```

**Почему так:**
- Сохраняет exceptions при переключении режимов (если день тот же)
- Корректно обрабатывает изменение дня резервирования
- Не накапливает мёртвые exceptions

### Решение 2: Пересчёт exceptions

**Новый метод `recalculate_current_month_exception()`:**

Вызывается при:
- `adjust_reserve_for_contribution()` — уже есть
- Удалении взноса (GoalContribution)
- Изменении суммы взноса
- Изменении `monthly_savings_budget`

**Алгоритм:**
```python
def recalculate_current_month_exception(self, user_id: int, month: date) -> None:
    """Пересчитывает exception для указанного месяца."""
    settings = self.get_settings(user_id)
    if settings["mode"] != "fixed_date":
        return

    reserve_date = self._get_reserve_date_for_month(user_id, month)
    if reserve_date is None or reserve_date <= date.today():
        # Дата уже прошла — не трогаем
        return

    contributions_sum = self._get_contributions_before_reserve(user_id, reserve_date)
    new_amount = max(settings["monthly_budget"] - contributions_sum, Decimal("0"))

    template = self._get_reserve_template(user_id)
    if not template:
        return

    # Создать/обновить exception
    recurring_service.create_exception(
        template_id=template.id,
        original_date=reserve_date,
        new_amount=new_amount,
        new_description=self._get_reserve_description(new_amount),
    )
```

### Решение 3: Исправление `used_budget`

**Для режима `fixed_date`:**

```python
# Текущее (неправильное):
used = self._get_reserve_sum_for_month(user_id, reference_date)

# Исправленное:
used = (
    self._get_reserve_sum_for_month(user_id, reference_date)  # Резервы (если дата прошла)
    + self._get_contributions_sum_for_month(user_id, reference_date)  # + Взносы
)
```

**Но это создаёт двойной учёт!** Если резерв 50000 и взнос 10000, то used = 50000 + 10000 = 60000?

**Правильная логика:**
- Резерв УЖЕ уменьшен на сумму взносов (через exception)
- `used = reserves + contributions` даст `40000 + 10000 = 50000` ✓

**НО:** до даты резерва reserves = 0 (виртуальный экземпляр не в БД).

**Финальное решение:**

```python
def get_budget_progress(self, user_id, reference_date):
    settings = self.get_settings(user_id)
    total_budget = settings["monthly_budget"]

    if settings["mode"] == "fixed_date":
        # Взносы всегда учитываются
        contributions = self._get_contributions_sum_for_month(user_id, reference_date)

        # Резерв учитывается только если дата прошла
        reserve_date = self._get_reserve_date_for_month(user_id, reference_date)
        if reserve_date and reserve_date <= reference_date:
            reserves = self._get_reserve_sum_for_month(user_id, reference_date)
        else:
            reserves = Decimal("0")

        used = contributions + reserves
        mode_text = "Использовано"  # Изменить с "Зарезервировано"
    else:
        used = self._get_contributions_sum_for_month(user_id, reference_date)
        mode_text = "Внесено"

    # ... rest of calculation
```

**Альтернатива (проще):** Всегда показывать взносы, игнорировать резерв в `used`:

```python
# Для обоих режимов:
used = self._get_contributions_sum_for_month(user_id, reference_date)
mode_text = "Внесено"
```

**Рекомендация:** использовать альтернативу — единообразно для обоих режимов.

---

## Детали реализации

### Файл 1: `app/services/budget_reservation_service.py`

#### Изменение 1.1: `set_mode()` — переиспользование шаблона

```python
def set_mode(self, user_id: int, mode: ReservationMode, day_of_month: int | None = None):
    user = self.session.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    if mode == "fixed_date":
        if day_of_month is None:
            raise ValueError("day_of_month required for fixed_date mode")
        if not 1 <= day_of_month <= 31:
            raise ValueError("day_of_month must be 1-31")

        # Ищем существующий шаблон (включая остановленный)
        existing_template = self._find_any_reserve_template(user_id)

        if existing_template and self._get_template_day(existing_template) == day_of_month:
            # День совпадает — реактивируем
            existing_template.recurring_end_date = None
            self.session.flush()
            logger.info(f"Reactivated template {existing_template.id} for user {user_id}")
        else:
            # День изменился или шаблона нет — создаём новый
            if existing_template:
                self._stop_reserve_template(user_id)
                self._cleanup_orphan_exceptions(existing_template.id)
            template = self._create_reserve_template(user_id, day_of_month)

        user.reservation_mode = "fixed_date"
        user.reservation_day = day_of_month
        self.session.flush()

    else:  # from_balance
        self._stop_reserve_template(user_id)
        user.reservation_mode = "from_balance"
        user.reservation_day = None
        self.session.flush()

    return self.get_settings(user_id)
```

#### Изменение 1.2: Новые helper методы

```python
def _find_any_reserve_template(self, user_id: int) -> Transaction | None:
    """Находит любой recurring шаблон резерва (включая остановленный)."""
    return (
        self.session.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_recurring.is_(True),
            Transaction.transaction_type == TransactionType.SAVINGS_RESERVE,
        )
        .order_by(Transaction.id.desc())  # Последний созданный
        .first()
    )

def _get_template_day(self, template: Transaction) -> int:
    """Извлекает день месяца из шаблона."""
    # Для EOM anchor возвращаем 31
    if template.recurring_anchor_eom:
        return 31
    return template.transaction_date.day

def _cleanup_orphan_exceptions(self, template_id: int) -> int:
    """Удаляет exceptions для дат после recurring_end_date."""
    template = self.session.get(Transaction, template_id)
    if not template or not template.recurring_end_date:
        return 0

    deleted = (
        self.session.query(Transaction)
        .filter(
            Transaction.recurring_parent_id == template_id,
            Transaction.original_date > template.recurring_end_date,
        )
        .delete()
    )
    self.session.flush()
    logger.info(f"Cleaned up {deleted} orphan exceptions for template {template_id}")
    return deleted

def _get_reserve_date_for_month(self, user_id: int, reference_date: date) -> date | None:
    """Возвращает дату резерва для указанного месяца."""
    settings = self.get_settings(user_id)
    if settings["day_of_month"] is None:
        return None

    _, last_day = monthrange(reference_date.year, reference_date.month)
    return date(
        reference_date.year,
        reference_date.month,
        min(settings["day_of_month"], last_day),
    )
```

#### Изменение 1.3: `recalculate_current_month_exception()`

```python
def recalculate_current_month_exception(self, user_id: int, month: date | None = None) -> bool:
    """Пересчитывает exception для текущего/указанного месяца.

    Вызывается при:
    - Удалении взноса
    - Изменении суммы взноса
    - Изменении monthly_savings_budget

    Returns:
        True если exception был обновлён/создан, False если не требуется.
    """
    if month is None:
        month = date.today()

    settings = self.get_settings(user_id)
    if settings["mode"] != "fixed_date":
        return False

    reserve_date = self._get_reserve_date_for_month(user_id, month)
    if reserve_date is None:
        return False

    # Если дата резерва уже прошла — не пересчитываем
    if reserve_date <= date.today():
        return False

    template = self._get_reserve_template(user_id)
    if not template:
        return False

    # Считаем взносы до даты резерва
    month_start = date(month.year, month.month, 1)
    contributions_sum = (
        self.session.query(func.coalesce(func.sum(GoalContribution.amount), 0))
        .join(Goal, Goal.id == GoalContribution.goal_id)
        .filter(
            Goal.user_id == user_id,
            GoalContribution.contribution_date >= month_start,
            GoalContribution.contribution_date < reserve_date,
        )
        .scalar()
    )
    contributions_sum = Decimal(str(contributions_sum))

    budget = settings["monthly_budget"]
    new_amount = max(budget - contributions_sum, Decimal("0"))

    # Определяем description
    if new_amount == 0:
        description = f"{RESERVE_DESCRIPTION} (внесено досрочно)"
    else:
        description = RESERVE_DESCRIPTION

    # Если взносов нет — удаляем exception (если есть)
    if contributions_sum == 0:
        self._delete_exception_for_date(template.id, reserve_date)
        return True

    # Создаём/обновляем exception
    from app.services import RecurringService
    recurring_service = RecurringService(self.session)
    recurring_service.create_exception(
        template_id=template.id,
        original_date=reserve_date,
        new_amount=new_amount,
        new_description=description,
    )

    logger.info(
        f"User {user_id}: recalculated exception for {reserve_date}, "
        f"contributions={contributions_sum}, new_amount={new_amount}"
    )
    return True

def _delete_exception_for_date(self, template_id: int, target_date: date) -> bool:
    """Удаляет exception для конкретной даты."""
    deleted = (
        self.session.query(Transaction)
        .filter(
            Transaction.recurring_parent_id == template_id,
            Transaction.original_date == target_date,
        )
        .delete()
    )
    if deleted:
        self.session.flush()
        logger.info(f"Deleted exception for template {template_id} on {target_date}")
    return deleted > 0
```

#### Изменение 1.4: `get_budget_progress()` — единообразный расчёт

```python
def get_budget_progress(self, user_id: int, reference_date: date | None = None) -> BudgetProgress:
    if reference_date is None:
        reference_date = date.today()

    settings = self.get_settings(user_id)
    total_budget = settings["monthly_budget"]

    # Единообразно для обоих режимов: считаем взносы
    used = self._get_contributions_sum_for_month(user_id, reference_date)
    mode_text = "Внесено"

    available = total_budget - used if total_budget > 0 else Decimal("0")

    # ... rest unchanged
```

### Файл 2: `app/services/goal_service.py`

#### Изменение 2.1: Интеграция пересчёта при удалении

```python
def delete_contribution(self, contribution_id: int) -> bool:
    """Удаляет взнос и пересчитывает exception."""
    contribution = self.session.get(GoalContribution, contribution_id)
    if not contribution:
        return False

    goal = contribution.goal
    amount = contribution.amount
    contribution_date = contribution.contribution_date

    # Удаляем взнос
    goal.current_amount -= amount
    if goal.status == GoalStatus.COMPLETED and goal.current_amount < goal.target_amount:
        goal.status = GoalStatus.ACTIVE

    self.session.delete(contribution)
    self.session.flush()

    # Пересчитываем exception
    budget_service = BudgetReservationService(self.session)
    budget_service.recalculate_current_month_exception(goal.user_id, contribution_date)

    return True
```

### Файл 3: `app/components/goals.py`

#### Изменение 3.1: Callback для изменения бюджета

В callback `update_budget()` добавить вызов пересчёта:

```python
@callback(...)
def update_budget(...):
    # ... existing code ...

    # После изменения бюджета — пересчитать exception
    budget_service.recalculate_current_month_exception(user_id)

    session.commit()
```

---

## Миграция данных

**Не требуется.** Изменения затрагивают только логику, не схему БД.

При первом взносе после обновления — exception будет пересчитан корректно.

---

## Тестирование

### Unit тесты

```python
class TestSetModeReuse:
    """Тесты переиспользования шаблона."""

    def test_reactivate_same_day(self):
        """Шаблон реактивируется если день совпадает."""

    def test_new_template_different_day(self):
        """Новый шаблон если день изменился."""

    def test_cleanup_orphan_exceptions(self):
        """Orphan exceptions удаляются."""

class TestRecalculateException:
    """Тесты пересчёта exception."""

    def test_delete_contribution_recalculates(self):
        """Удаление взноса пересчитывает exception."""

    def test_budget_change_recalculates(self):
        """Изменение бюджета пересчитывает exception."""

    def test_no_contributions_deletes_exception(self):
        """Если взносов нет — exception удаляется."""

    def test_past_reserve_date_no_recalc(self):
        """Дата резерва прошла — не пересчитываем."""

class TestBudgetProgressUnified:
    """Тесты единообразного used_budget."""

    def test_fixed_date_shows_contributions(self):
        """fixed_date показывает взносы, не резервы."""

    def test_from_balance_shows_contributions(self):
        """from_balance показывает взносы."""
```

### Integration тесты

```python
class TestModeSwitch:
    """E2E тесты переключения режимов."""

    def test_switch_preserves_exception(self):
        """fixed_date → from_balance → fixed_date сохраняет exception."""

    def test_contribution_before_reserve_after_switch(self):
        """Взнос до резерва работает после переключения режимов."""
```

---

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Регрессия в существующих тестах | Средняя | Прогон полного test suite перед merge |
| Некорректная логика EOM anchor | Низкая | Отдельные тесты для 31-го числа |
| Performance при частом пересчёте | Низкая | Пересчёт только для будущих дат |

---

## План реализации

| Шаг | Описание | Файлы |
|-----|----------|-------|
| 1 | Helper методы (`_find_any_reserve_template`, `_get_template_day`, etc.) | budget_reservation_service.py |
| 2 | `set_mode()` — переиспользование шаблона | budget_reservation_service.py |
| 3 | `recalculate_current_month_exception()` | budget_reservation_service.py |
| 4 | `get_budget_progress()` — единообразный расчёт | budget_reservation_service.py |
| 5 | Интеграция в GoalService | goal_service.py |
| 6 | Интеграция в callbacks (update_budget) | goals.py |
| 7 | Unit тесты | test_budget_reservation_service.py |
| 8 | Integration тесты | test_budget_integration.py |
| 9 | Финализация (lint, format, full test) | — |

**Оценка:** 6-8 шагов протокола