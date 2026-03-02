# Спецификация: Улучшение UI бюджета накоплений + механика fixed_date

## Контекст

Протокол 0016 реализовал интеграцию бюджета целей с календарём, но выявлены проблемы:
1. Непонятный текст "Резерв на цели: Авто" в календаре
2. Дублирование UI (две карточки про бюджет)
3. Задержка обновления при внесении средств
4. В режиме fixed_date взносы до даты резерва не уменьшают сумму резервирования

## Принятые решения

### UI улучшения

| Проблема | Решение |
|----------|---------|
| "Резерв на цели: Авто" | Изменить на "Резервирование бюджета" |
| Верхняя карточка "Бюджет накоплений (месяц)" | Удалить полностью |
| Формат в "Сводке по целям" | `30 000 / 50 000 ₽` (внесено / бюджет) |
| Задержка refresh | Добавить trigger при внесении |

### Механика fixed_date

**Сценарий:** Пользователь в режиме fixed_date (резерв 15-го числа) вносит взнос до этой даты.

**Поведение:**
1. Взнос ДО даты резерва (например, 5-го):
   - Создаётся SAVINGS_CONTRIBUTION транзакция (как в from_balance)
   - Создаётся/обновляется **Exception** для recurring шаблона на текущий месяц
   - Сумма Exception = `budget - SUM(взносов до даты резерва)`
   - Если сумма >= бюджета → Exception с amount=0 и description="Резервирование бюджета (внесено досрочно)"

2. Взнос ПОСЛЕ даты резерва (например, 20-го):
   - Только SAVINGS_CONTRIBUTION
   - Не влияет на уже прошедший резерв

**Почему Exception, а не изменение шаблона:**
- Шаблон = источник правды (полный бюджет)
- Exception = корректировка для конкретного месяца
- Следующий месяц = чистый лист (нет exception → полная сумма)

## Детали реализации

### Файл 1: `app/services/budget_reservation_service.py`

**Изменение константы:**
```python
# Было:
RESERVE_DESCRIPTION: str = "Резерв на цели"

# Станет:
RESERVE_DESCRIPTION: str = "Резервирование бюджета"
```

**Новый метод:**
```python
def adjust_reserve_for_contribution(
    self,
    user_id: int,
    contribution_date: date,
    contribution_amount: Decimal
) -> None:
    """Корректирует сумму резерва при досрочном взносе (режим fixed_date).

    Создаёт/обновляет Exception для recurring шаблона резервирования.
    Вызывается из GoalService.add_contribution() если:
    - Режим = fixed_date
    - contribution_date < reservation_day текущего месяца

    Args:
        user_id: ID пользователя
        contribution_date: Дата взноса
        contribution_amount: Сумма взноса (для логирования)
    """
```

**Логика метода:**
1. Получить настройки (`get_settings`)
2. Проверить режим = "fixed_date" (guard)
3. Определить дату резерва текущего месяца
4. Если contribution_date >= reserve_date → return (взнос после резерва)
5. Получить шаблон резерва (`_get_reserve_template`)
6. Посчитать сумму взносов до даты резерва в текущем месяце
7. Рассчитать новую сумму: `new_amount = budget - contributions_sum`
8. Если new_amount <= 0:
   - new_amount = 0
   - description = "Резервирование бюджета (внесено досрочно)"
9. Создать/обновить Exception через RecurringService

### Файл 2: `app/services/goal_service.py`

**Изменение в `add_contribution()`:**

После создания SAVINGS_CONTRIBUTION (строка ~170):
```python
# Корректировка резерва для fixed_date режима
budget_service.adjust_reserve_for_contribution(
    user_id=goal.user_id,
    contribution_date=actual_date,
    contribution_amount=amount
)
```

### Файл 3: `app/components/goals.py`

**Удалить:**
- `_build_budget_progress_card()` (строки 390-460)
- `budget-progress-card-container` из layout
- `load_budget_progress_card` callback (строки 3741-3784)

**Изменить `_build_summary_section()`:**

Добавить параметр `budget_progress: BudgetProgress`:
```python
def _build_summary_section(
    goals_summary: GoalsSummary,
    allocation_summary: AllocationSummary,
    budget_progress: BudgetProgress,  # NEW
) -> dbc.Card:
```

Изменить секцию "Бюджет накоплений" (строки 539-556):
```python
dbc.Col(
    [
        html.P(
            "Бюджет накоплений",
            className="text-muted mb-0 small",
        ),
        html.Small(
            "В текущем месяце",
            className="text-muted",
        ),
        html.H5(
            [
                format_amount(budget_progress["used_budget"]),
                html.Span(" / ", className="text-muted"),
                html.Span(
                    format_amount(budget_progress["total_budget"]),
                    className="text-muted",
                ),
            ],
            className="mb-0",
        ),
    ],
    md=6,
),
```

**Обновить callback `load_goals_page`:**
- Добавить вызов `BudgetReservationService.get_budget_progress()`
- Передать в `_build_summary_section()`

**Добавить refresh trigger:**
- После внесения взноса обновлять секцию "Сводка по целям"

### Файл 4: `app/services/recurring_service.py`

**Использовать существующий API:**
```python
RecurringService.create_exception(
    template_id=template.id,
    instance_date=reserve_date,
    amount=new_amount,
    description="Резервирование бюджета" или "Резервирование бюджета (внесено досрочно)"
)
```

## Edge Cases

| Сценарий | Поведение |
|----------|-----------|
| Удаление взноса до даты резерва | Пересчитать Exception (увеличить сумму) |
| Редактирование суммы взноса | Пересчитать Exception |
| Несколько взносов до даты | Накопительный пересчёт (SUM всех взносов) |
| Взносы = бюджету | Exception amount=0, description="(внесено досрочно)" |
| Взносы > бюджета | Exception amount=0 (не уходим в минус) |
| Смена режима fixed_date → from_balance | Exception остаётся (не удаляем) |
| Смена месяца | Новый месяц = нет exception → полная сумма |

## Тесты

### Unit тесты для BudgetReservationService:
1. `test_adjust_reserve_contribution_before_date` — создаёт exception
2. `test_adjust_reserve_contribution_after_date` — не создаёт exception
3. `test_adjust_reserve_contribution_equals_budget` — exception с 0
4. `test_adjust_reserve_contribution_exceeds_budget` — exception с 0
5. `test_adjust_reserve_multiple_contributions` — накопительный расчёт
6. `test_adjust_reserve_from_balance_mode` — ничего не делает

### Integration тесты:
1. `test_fixed_date_contribution_creates_exception` — E2E сценарий
2. `test_contribution_after_reserve_date_no_exception` — E2E сценарий

## Верификация

```bash
black app/ tests/
flake8 app/ --select=E9,F63,F7,F82
pytest tests/ -v --tb=short
```

**Ручная проверка:**
1. Перейти на /goals, проверить что верхняя карточка удалена
2. Проверить "Сводка по целям" — формат "X / Y ₽"
3. Настроить режим fixed_date на 15-е число
4. Внести взнос 5-го числа
5. Проверить в календаре: появился SAVINGS_CONTRIBUTION и уменьшился резерв на 15-е
6. Внести ещё взнос = бюджету
7. Проверить: резерв = 0₽ с пометкой "(внесено досрочно)"
8. Проверить текст в календаре: "Резервирование бюджета (авто)"

## Референсы

- Протокол 0016: `.protocols/0016-budget-calendar/`
- BudgetReservationService: `app/services/budget_reservation_service.py`
- RecurringService (exceptions): `app/services/recurring_service.py:283-310`
- GoalService: `app/services/goal_service.py`
- Goals UI: `app/components/goals.py`