# Шаг 3: AllocationService модификация

## Briefing
- **Цель:** Добавить параметр `savings_mode` в метод `calculate_allocation()` и применить множитель к `monthly_contribution` каждой цели внутри алгоритма распределения.
- **Ключевые файлы:**
  - `app/services/allocation_service.py` (модифицировать — добавить константу и параметр)
  - `tests/test_allocation_service.py` (модифицировать — добавить 3 теста)
- **Additional info:**
  - Множитель применяется ВНУТРИ цикла `for goal in sorted_goals`
  - `monthly_contribution_needed` в результате содержит ADJUSTED (умноженное) значение
  - Default parameter `savings_mode="free"` обеспечивает обратную совместимость
  - Все существующие тесты должны продолжать работать без изменений

## Sub-tasks

1. **Добавить константу SAVINGS_MODE_MULTIPLIERS:**
   - В начале `app/services/allocation_service.py` после импортов:
     ```python
     from decimal import Decimal

     # Множители для режимов накоплений
     SAVINGS_MODE_MULTIPLIERS: dict[str, Decimal] = {
         "free": Decimal("1.0"),     # 100% — минимальные взносы
         "medium": Decimal("1.15"),  # 115% — буфер для страховки
         "strict": Decimal("1.5"),   # 150% — максимизация накоплений
     }
     ```

2. **Добавить параметр в calculate_allocation():**
   - Изменить сигнатуру метода:
     ```python
     def calculate_allocation(
         self,
         goals: list[Goal],
         monthly_budget: Decimal,
         savings_mode: str = "free",  # NEW
     ) -> AllocationSummary:
     ```
   - Обновить docstring

3. **Применить множитель в алгоритме:**
   - Внутри цикла `for goal in sorted_goals`:
     ```python
     # Получаем множитель для режима
     multiplier = SAVINGS_MODE_MULTIPLIERS.get(savings_mode, Decimal("1.0"))

     # Применяем множитель к базовому monthly_contribution
     base_monthly = goal.monthly_contribution
     monthly_needed = base_monthly * multiplier  # ADJUSTED значение
     ```
   - Далее `monthly_needed` используется для:
     - `allocated = min(monthly_needed, remaining_budget)`
     - `result["monthly_contribution_needed"] = monthly_needed`
     - `total_needed += monthly_needed`
     - `shortfall = max(0, monthly_needed - allocated)`

4. **Добавить логирование при неизвестном режиме:**
   - Если `savings_mode` не найден в `SAVINGS_MODE_MULTIPLIERS`, залогировать warning
   - Использовать fallback на `Decimal("1.0")`

5. **Написать 3 unit теста:**
   - В `tests/test_allocation_service.py` добавить:
   - `test_allocation_free_mode` — проверяет множитель 1.0 (monthly_needed = base)
   - `test_allocation_medium_mode` — проверяет множитель 1.15 (monthly_needed = base * 1.15)
   - `test_allocation_strict_mode` — проверяет множитель 1.5 (monthly_needed = base * 1.5)

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи.

2. **Базовая проверка:**
   - `python -m py_compile app/services/allocation_service.py`
   - `python -m py_compile tests/test_allocation_service.py`

3. **Фиксация:**
   - **Добавь запись в `log.md`**: Опиши точку применения множителя и тесты.
   - **Обнови `context.md`**: `Current Step` на 4, подготовь `Next Action` для Шага 4.
   - Проверь ветку main.

4. **Сделай коммит:**
   ```bash
   git add . && git commit -m "feat(allocation): add savings_mode parameter with multipliers [protocol-0007/03]"
   ```
   Сделай пуш.

5. **Отчет пользователю.**

## Детали реализации

### Точка применения множителя (псевдокод)
```python
def calculate_allocation(
    self,
    goals: list[Goal],
    monthly_budget: Decimal,
    savings_mode: str = "free",
) -> AllocationSummary:
    """Распределяет бюджет с учетом режима накоплений."""

    # Получаем множитель с fallback
    multiplier = SAVINGS_MODE_MULTIPLIERS.get(savings_mode, Decimal("1.0"))
    if savings_mode not in SAVINGS_MODE_MULTIPLIERS:
        logger.warning(f"Неизвестный режим накоплений: {savings_mode}, используется 1.0")

    # ... сортировка и фильтрация целей ...

    for goal in sorted_goals:
        # Guard clauses для пропуска...

        # ПРИМЕНЕНИЕ МНОЖИТЕЛЯ
        base_monthly = goal.monthly_contribution
        monthly_needed = base_monthly * multiplier

        # Распределение бюджета
        allocated = min(monthly_needed, remaining_budget)
        remaining_budget -= allocated

        # Формирование результата
        result: AllocationResult = {
            "goal_id": goal.id,
            "goal_name": goal.name,
            "monthly_contribution_needed": monthly_needed,  # ADJUSTED!
            "allocated": allocated,
            "shortfall": max(Decimal("0"), monthly_needed - allocated),
            # ... остальные поля ...
        }
        results.append(result)
        total_needed += monthly_needed

    # ... формирование AllocationSummary ...
```

### Пример теста
```python
def test_allocation_medium_mode(session, test_user):
    """Проверяет что режим medium применяет множитель 1.15."""
    # Создаем цель с monthly_contribution = 1000
    goal = Goal(
        user_id=test_user.id,
        name="Test Goal",
        target_amount=Decimal("12000"),
        current_amount=Decimal("0"),
        target_date=date.today() + timedelta(days=365),
        priority=1,
        status="ACTIVE",
    )
    session.add(goal)
    session.flush()

    service = AllocationService()
    result = service.calculate_allocation(
        goals=[goal],
        monthly_budget=Decimal("5000"),
        savings_mode="medium",  # 1.15x
    )

    # monthly_contribution ~= 1000 (12000 / 12 месяцев)
    # с режимом medium: 1000 * 1.15 = 1150
    assert len(result["results"]) == 1
    allocation = result["results"][0]

    # Проверяем что monthly_contribution_needed содержит adjusted значение
    base_monthly = goal.monthly_contribution
    expected_needed = base_monthly * Decimal("1.15")
    assert allocation["monthly_contribution_needed"] == expected_needed
```
