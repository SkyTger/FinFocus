# Шаг 2: Каркас MoneyLayersService

## Briefing

- **Цель:** Собрать сервис без формулы резерва: три горизонта, единый сбор операций, суффиксные суммы платежей, каскад сжатия, срез дня, минимум окна, определение пустого состояния.
- **Ключевые файлы:**
  - `app/services/money_layers_service.py` — НОВЫЙ
  - `app/services/__init__.py` — реэкспорт
  - Читать (не менять): `app/services/calendar_service.py` (`calculate_daily_balances`, `get_all_transactions_for_period`), `app/services/dashboard_service.py:476-545` (классификация типов операций — повторить её)
- **Источник правды:** solution-v4.md, секция «Ключевые интерфейсы» → блок `money_layers_service.py`. Докстринги перенести целиком, включая оба Note про допущения в докстринге класса.
- **Соответствует шагу 3 плана решения** (оценка 4.5 ч).

## Sub-tasks

1. **`_horizons(reference_date) -> Horizons`** — три границы:
   - `collect_start = month_start(reference_date)` — **1-е число месяца**, не сегодня. Причина в докстринге: `consumed(reference_date)` требует savings-операций за прошедшие дни текущего месяца.
   - `window_end = reference_date + WINDOW_DAYS - 1`
   - `payments_end = month_end(reference_date)` — только арифметический фильтр слоя «Платежи», сбор данных им НЕ ограничен

2. **`_forecast_balances()`** — делегат в `CalendarService.calculate_daily_balances(user_id, reference_date, window_end)`. Единственный источник остатка → инвариант AC-3 по построению.

3. **`_collect_operations(user_id, collect_start, window_end)`** — **ОДИН** вызов `get_all_transactions_for_period`, две выходные структуры:
   - `payments: list[UpcomingPayment]` — расходные с датой `>= reference_date`
   - `savings_by_date: dict[date, Decimal]` — только `savings_reserve` + `savings_contribution`, **ключ = фактическая дата операции**, **БЕЗ фильтра по границам окна** (критично: ключ может лежать за `window_end`)
   - Классификация типов: `expense`/`savings_reserve`/`savings_contribution` → платёж; `adjustment` с `Decimal(amount) < 0` → платёж на `abs(...)`; `income`/`transfer` → нет; `is_skipped=True` отбрасывать
   - Докстринг: механика расхождения `transaction_date`/`original_date` со ссылками на код (см. решение)

4. **`_payments_tail_by_day()`** — суффиксные суммы `Σ` платежей в `(D, payments_end]`, строго «после D» (платёж дня D уже вычтен из баланса). `payments(D) = 0` для `D >= payments_end`. Один проход справа налево.

5. **`_split_day(balance, payments, reserve)`** — **единственный** механизм обрезки:
   - `free = balance − payments − reserve`; если `>= 0` — готово
   - Иначе `free = 0`, дефицит гасится сначала из `reserve`, затем из `payments`
   - Если `balance < 0` → `free = balance`, `payments = reserve = 0`
   - Сумма == `balance` во всех ветках
   - **`min(threshold, balance)` в `cushion_part` НЕ добавлять** (решение владельца п. 3б)

6. **`_today_slice(days)`** — четыре числа разбора, без вердикта.

7. **`_window_min_free(days)`** — минимум слоя «Свободно» по всем 45 дням, первая дата при равенстве. Используется только графиком (FR-3.e).

8. **`_is_empty(...)`** — чистая функция **без запросов**: `starting_balance == 0` И шаблонов нет И операций в диапазоне нет И все `forecast_balance == 0`. Докстринг: почему `first_launch` не годится (`skip()` сбрасывает флаг, не создавая данных).

9. **`get_money_layers(user_id, reference_date=None)`** — публичный метод: собрать всё, вернуть `MoneyLayersData`. Формулу резерва пока подставить заглушкой `goals_part = 0` (реальная — шаг 3), пометив `TODO(step-3)`; `cushion_part = cushion_threshold` уже рабочий.

10. **`app/services/__init__.py`** — реэкспорт `MoneyLayersService` и типов.

## Проверки шага

- `python -m py_compile app/services/money_layers_service.py`
- Smoke: `python -c "from app.core import get_db_session; from app.services import MoneyLayersService; ..."` — вызов на реальной БД не падает, длина `days` == 45
- `.venv/bin/black` + `.venv/bin/flake8 --select=F` — чисто
- `.venv/bin/pytest -q` — 565 прежних зелёные (новый сервис пока никем не вызывается)

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile {FILES}`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 3, Next Action: Шаг 3
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(services): каркас MoneyLayersService — горизонты, сбор, каскад [protocol-0028/02]"`
7. Push
8. Отчёт
