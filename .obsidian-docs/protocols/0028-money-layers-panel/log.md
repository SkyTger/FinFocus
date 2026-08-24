# Work Log: 0028-money-layers-panel — Модель «свободно/платежи/резерв» + шапка + график полос

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0028#ctx-N -->

Restore context: protocol-0028#ctx-1

---

## Step Log

<!--
Формат записи:
### Step XX — [название] (commit: abc1234)
- Что сделано
- Неочевидные решения и почему
- Проблемы и как решены
-->

### Step 00 — Setup (commit: ee340c4)
- Созданы артефакты протокола: plan.md, context.md, log.md, 9 файлов шагов (00–08)
- Draft PR #28 открыт
- Восстановление контекста ctx-1: запись о шаге 0 в журнале отсутствовала (сессия
  прервалась после коммита), context.md уже был переведён на шаг 1 — досоздано

### Step 01 — Контракт модели + геттер порога подушки (commit: 993df2a)
- `app/schema/money_layers.py` — новый: `LayerKey`, константы (`WINDOW_DAYS`,
  `MAX_MILESTONES_IN_WINDOW`, `MAX_X_TICKS`, `LAYER_COLORS`, `LAYER_LABELS`),
  `Horizons(NamedTuple)`, TypedDict'ы `DayLayers` / `UpcomingPayment` /
  `GoalMilestone` / `TodaySlice` / `MoneyLayersData`. Докстринги перенесены
  из solution-v4.md целиком, включая оба Note модуля
- Вердикт-типы и `DIP_*` НЕ созданы (решение владельца п. 3а) — проверено
- `app/schema/__init__.py` — реэкспорт 12 имён + блок в `__all__`
- `CushionService.get_threshold_amount()` — добавлен перед `get_settings`;
  формула `target * percent / 100` без `_get_current_balance()`,
  `Decimal("0")` при отсутствии пользователя или `target <= 0`.
  Существующие методы не тронуты (единственное разрешённое отступление от C-3)
- Неочевидное: метод не переиспользует `_get_user()` намеренно — тот бросает
  `ValidationError`, а контракт требует тихого дефолта на чистой базе
- +4 теста в `tests/test_cushion_service.py` (класс `TestGetThresholdAmount`),
  включая monkeypatch-assert: `calculate_daily_balances` и
  `get_balance_on_date` подменены на падающие заглушки — вызов любой из них
  провалит тест. Это и есть смысл нового метода
- Проверки: py_compile OK; `pytest tests/test_cushion_service.py` — 24 passed;
  полный прогон — 569 passed (565 базовых + 4); black — переформатирован
  1 тестовый файл; flake8 (полный, не только F) — пусто;
  импорт из чистого интерпретатора `from app.schema import MoneyLayersData,
  WINDOW_DAYS` → 45
- Окружение: `.venv` внутри worktree отсутствует (машинно-локальный), все
  проверки прогнаны из `/home/skytiger/Projects/FinFocus/.venv`
  (Python 3.10.12, black 23.11.0 — соответствует правилу «black только из .venv»)

### Step 02 — Каркас MoneyLayersService (commit: 427e969)
- `app/services/money_layers_service.py` — новый: `_horizons`, `_forecast_balances`,
  `_collect_operations`, `_payments_tail_by_day`, `_split_day`, `_today_slice`,
  `_window_min_free`, `_goal_milestones`, `_is_empty`, публичный
  `get_money_layers`. Докстринги перенесены из solution-v4.md целиком,
  включая оба Note класса про допущения согласованности данных
- Формула резерва — заглушка `goals_part = 0` с пометкой `TODO(step-3)`;
  `cushion_part` уже рабочий (через `get_threshold_amount` шага 1)
- Модуль-хелперы `_month_start` / `_month_end` и константы `_PAYMENT_TYPES` /
  `_SAVINGS_TYPES` — классификация повторяет `DashboardService`
  (dashboard_service.py:476-545), проверена по исходнику
- Добавлен приватный `_user_data_markers` — не был в листинге решения, но
  требуется: `_is_empty` по контракту принимает `starting_balance` и
  `has_recurring_templates` готовыми, а брать их откуда-то нужно. Взяты
  два лёгких запроса (`session.get(User)` + `get_templates_for_user`),
  как предписывает Note контракта — без `count(transactions)` по всей истории
- Fail-open деградация: порог подушки и вехи целей обёрнуты в try с
  `logger.opt(exception=True)` (идиома loguru, не `exc_info`) и `degraded=True`;
  сбой расчёта баланса намеренно не глотается
- `app/services/__init__.py` — реэкспорт `MoneyLayersService`
- Проверки: py_compile OK; flake8 (полный) — пусто; black — переформатирован
  1 файл; полный прогон 569 passed (регрессий нет, сервис пока никем не вызван)
- Smoke на in-memory БД (в worktree своей БД нет — файл `data/finfocus.db`
  создался пустым при первой попытке и удалён): 45 дней окна, инвариант AC-3
  без нарушений, таяние платежей монотонно, за `payments_end` платежи 0,
  пустой пользователь → `is_empty=True`
- Отдельно прогнан каскад `_split_day` по 6 веткам (хватает всем / сжат резерв /
  резерв в ноль + сжаты платежи / ровно в ноль / отрицательный баланс / нули) —
  сумма слоёв равна балансу во всех

