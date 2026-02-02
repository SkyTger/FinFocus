# Шаг 5: Integration & Tests

## Briefing

- **Цель:** Интегрировать adjust_reserve_for_contribution() с GoalService и написать тесты
- **Ключевые файлы:**
  - `app/services/goal_service.py`
  - `tests/test_budget_reservation_service.py`
- **Доп. информация:** Вызов должен происходить после создания contribution

## Sub-tasks

### 1. Интеграция с GoalService

В `app/services/goal_service.py`, в методе `add_contribution()`:

После строки с созданием транзакции (примерно после вызова `create_contribution_transaction`):
```python
# Корректировка резерва для fixed_date режима
budget_service.adjust_reserve_for_contribution(
    user_id=goal.user_id,
    contribution_date=actual_date,
    contribution_amount=amount
)
```

### 2. Unit тесты для BudgetReservationService

Добавить в `tests/test_budget_reservation_service.py`:

```python
class TestAdjustReserveForContribution:
    """Тесты для adjust_reserve_for_contribution."""

    def test_contribution_before_reserve_date_creates_exception(
        self, db_session, test_user
    ):
        """Взнос до даты резерва создаёт Exception с уменьшенной суммой."""
        # Setup: режим fixed_date, день 15
        test_user.reservation_mode = "fixed_date"
        test_user.reservation_day = 15
        test_user.monthly_savings_budget = Decimal("50000")
        db_session.commit()

        service = BudgetReservationService(db_session)
        # Создать шаблон
        service.set_mode(test_user.id, "fixed_date", 15)
        db_session.commit()

        # Создать цель и взнос (5-е число)
        goal_service = GoalService(db_session)
        goal = goal_service.create_goal(
            user_id=test_user.id,
            name="Test",
            target_amount=Decimal("100000"),
            target_date=date.today() + timedelta(days=365)
        )
        db_session.commit()

        # Вызов
        service.adjust_reserve_for_contribution(
            user_id=test_user.id,
            contribution_date=date(2026, 2, 5),
            contribution_amount=Decimal("10000")
        )
        db_session.commit()

        # Assert: exception создан
        # ... проверить через RecurringService

    def test_contribution_after_reserve_date_no_exception(
        self, db_session, test_user
    ):
        """Взнос после даты резерва не создаёт Exception."""
        # ... аналогично, но дата 20-е

    def test_contribution_equals_budget_zero_amount(
        self, db_session, test_user
    ):
        """Если взносы = бюджету, Exception с суммой 0."""
        # ...

    def test_contribution_exceeds_budget_zero_amount(
        self, db_session, test_user
    ):
        """Если взносы > бюджета, Exception с суммой 0 (не отрицательной)."""
        # ...

    def test_multiple_contributions_cumulative(
        self, db_session, test_user
    ):
        """Несколько взносов — накопительный расчёт."""
        # ...

    def test_from_balance_mode_no_action(
        self, db_session, test_user
    ):
        """В режиме from_balance метод ничего не делает."""
        # ...
```

### 3. Integration тесты

Добавить в `tests/test_redistribution_integration.py` или новый файл:

```python
class TestFixedDateContribution:
    """E2E тесты для fixed_date режима с досрочными взносами."""

    def test_contribution_before_reserve_reduces_amount(
        self, db_session, test_user
    ):
        """E2E: взнос до резерва уменьшает сумму в календаре."""
        # ...

    def test_contribution_after_reserve_no_effect(
        self, db_session, test_user
    ):
        """E2E: взнос после резерва не влияет на прошедший резерв."""
        # ...
```

### 4. Запуск тестов

```bash
pytest tests/test_budget_reservation_service.py -v
pytest tests/test_goal_service.py -v
pytest tests/ -v --tb=short
```

## Workflow

1. Выполни Sub-tasks последовательно
2. Запусти тесты
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 6, Next Action: Финализация
5. Коммит: `git add . && git commit -m "feat(services): integrate adjust_reserve + tests [protocol-0017/05]"`
6. Push
7. Отчёт
