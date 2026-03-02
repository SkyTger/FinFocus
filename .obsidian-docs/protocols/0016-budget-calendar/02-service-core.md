# Шаг 2: BudgetReservationService Core

## Briefing

- **Цель:** Создать сервис управления режимами резервирования
- **Ключевые файлы:**
  - `app/schema/budget_reservation.py` — TypedDicts
  - `app/services/budget_reservation_service.py` — BudgetReservationService
  - `app/services/__init__.py` — экспорт
- **Доп. информация:** См. solution-v2.md секция "Ключевые интерфейсы"

## Sub-tasks

1. **TypedDicts** в `app/schema/budget_reservation.py`:
   ```python
   ReservationMode = Literal["fixed_date", "from_balance"]

   class BudgetReservationSettings(TypedDict):
       mode: ReservationMode
       day_of_month: int | None
       monthly_budget: Decimal
       template_id: int | None

   class BudgetProgress(TypedDict):
       total_budget: Decimal
       used_budget: Decimal
       available_budget: Decimal
       progress_percent: float
       status: str  # success/warning/orange/danger
       mode: ReservationMode
       mode_text: str  # "Распределено" / "Внесено"
   ```

2. **BudgetReservationService** — core методы:
   - `__init__(session)` — с RecurringService injection
   - `get_settings(user_id)` → BudgetReservationSettings
   - `set_mode(user_id, mode, day_of_month)` — с созданием/остановкой recurring шаблона
   - `get_budget_progress(user_id, reference_date)` → BudgetProgress

3. **Private helpers**:
   - `_get_reserve_template(user_id)` — найти активный шаблон
   - `_create_reserve_template(user_id, day_of_month)` — с Anchored-алгоритмом
   - `_stop_reserve_template(user_id)` — soft delete через recurring_end_date
   - `_get_contributions_sum_for_month(user_id, date)` — SQL агрегация

4. **Экспорт** в `app/services/__init__.py`

5. **Unit тесты** `tests/test_budget_reservation_service.py`:
   - get_settings без настроек → default
   - set_mode fixed_date → создаёт шаблон
   - set_mode from_balance → останавливает шаблон
   - get_budget_progress — расчёт процентов и статусов
   - EOM anchor для 31-го числа

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/services/budget_reservation_service.py`
3. Тесты: `pytest tests/test_budget_reservation_service.py -v`
4. Обнови `log.md`
5. Обнови `context.md` — Current Step: 3
6. Коммит: `git add . && git commit -m "feat(services): add BudgetReservationService core [protocol-0016/02]"`
7. Push
