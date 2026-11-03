# Work Log: 0033-safe-to-spend — «Можно тратить» одной моделью для всего щитка

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-NNNN#ctx-N -->
Restore context: protocol-0033#ctx-1 (2026-11-03, фон «без остановок, без push»; диагноз A — свежий старт)

---

## Step Log

<!--
Формат записи:
### Step XX — [название] (commit: abc1234)
- Что сделано
- Неочевидные решения и почему
- Проблемы и как решены
-->

### Step 00 — Подготовка (без отдельного коммита, войдёт в коммит шага 1)
- Окружение: `.venv` в worktree через uv (Python 3.12.3), `black 23.11.0`.
- Базовая линия: **928 passed**. flake8 `app/` — 3 pre-existing E501:
  `app/components/goals.py:3085`, `app/services/dashboard_service.py:375`,
  `:424` (актуальный список; в ROADMAP №5 перечень устарел).
- Шаблоны `~/.claude/templates/protocol/workflow.md.tpl` и
  `report-format.md.tpl` в песочнице недоступны (каталога нет) — шёл по
  секциям Workflow файлов шагов, они самодостаточны.
- В worktree лежат неотслеживаемые `.bashrc`, `.gitconfig`, `.idea`,
  `.vscode` и т.п. — артефакты песочницы; в коммиты не берутся
  (`git add -u` + явные пути вместо `git add .`).

### Step 01 — Модель слоёв на удлинённом горизонте

**Прогон ДО правки тестов** (новая модель, старые тесты): 20 failed, 908 passed.
Ни одно падение не вызвано ошибкой реализации:

| Тест | Почему упал |
|---|---|
| `test_money_layers_service.py::TestExpectedLayersTable::test_trace_example_layers` | новый смысл: payments 52 500 вместо 37 500 (расчёт ниже) |
| `…::TestPaymentsMelting::test_payments_zero_at_and_after_payments_end` | новый смысл: `payments_end` удалён (C-5 отменён) |
| `…::TestBoundaries::test_horizons_for_various_reference_days[1/15/28]` | новый смысл: `Horizons.payments_end` удалён |
| `…::TestBoundaries::test_february_month_end` | новый смысл: проверял `payments_end` |
| `…::TestBoundaries::test_savings_by_date_keeps_keys_beyond_window` | контракт: `_collect_operations` теперь отдаёт ещё даты доходов (3-кортеж) |
| `…::TestOperationTypes::test_savings_types_are_payments_and_savings` | то же — 3-кортеж |
| `test_panel_service.py::TestConsistency::test_dip_fields_from_layers` | контракт: `min_free*` удалены → `bottleneck_*` |
| `test_dashboard_panel_ui.py::TestLayersChart::*` (7) и `TestLegendAndTooltips::*` (4) | фикстура `make_layers_data` без новых полей (`KeyError: bottleneck_date`); маркер и тултип читают `bottleneck_*` / `horizon_end` |

`test_payments_monotonically_non_increasing` остался зелёным — без доходов
доступное только убывает, свойство верно и в новой модели; докстринг уточнён
(«без доходов»), смысл нового слоя покрывают новые тесты.

**Ручной расчёт `test_trace_example_layers`** (ref = 1-е число, баланс 84 500,
порог подушки 30 000, бюджет целей 15 000, резерв на цели 15 000 на ref+3,
расход 22 500 на ref+5, доходов нет → H = ref+89, это три месяца):
- goals_part: дни текущего месяца — 0 (до ref+3 committed 15 000, после —
  consumed 15 000); дни следующих двух месяцев — 15 000 (savings-операций
  в них нет — месяц без резерва держит один бюджет, кейс 9).
- available: ref..ref+2 = 84 500 − 30 000 = 54 500; ref+3..ref+4 =
  69 500 − 30 000 = 39 500; ref+5..конец месяца = 47 000 − 30 000 = 17 000;
  следующие месяцы = 47 000 − 45 000 = **2 000**.
- m(ref) = 2 000 → payments_raw = 54 500 − 2 000 = 52 500; каскад:
  84 500 − 52 500 − 30 000 = 2 000 ≥ 0. Итог: **free 2 000, payments 52 500,
  reserve 30 000**. Бюджет целей следующего месяца без дохода в горизонте
  берётся из сегодняшних денег — свойство неизменного правила резерва.

**Сделано:**
- Схема: `Horizons` — `collect_start, window_end, horizon_end,
  horizon_has_income_after`; `LimitPeriod`; `MoneyLayersData` получил
  `limit_periods, bottleneck_date, bottleneck_available, shortfall,
  shortfall_date, norm_per_day, horizon_end`; `min_free`, `min_free_date`,
  `payments_end` удалены. `HORIZON_CAP_DAYS = 90` рядом с `WINDOW_DAYS`.
- Модель: один сбор операций `[1-е число месяца ref, конец месяца ref+89]`
  (платежи, savings, даты доходов) → H → прогноз остатка и резерв на
  `[ref, H]` → `available` → `_suffix_min` (справа налево) → `_split_day`
  без изменений с входом `available(D) − m(D)`. `_payments_tail_by_day`
  и `_window_min_free` удалены, добавлены `_suffix_min`, `_shortfall`.
  `limit_periods = []`, `norm_per_day = None` — заполнит шаг 2;
  `bottleneck_*` временно = день минимума available на `[ref, H]`.
- `window_is_flat` теперь смотрит только на операции в пределах оси
  (иначе расширенный сбор тихо гасил бы «плоское окно»).
- `upcoming_payments` — платежи `[ref, H]`.
- Читатели удалённых полей — минимальная замена: `panel_service.py`
  (dip_* ← bottleneck_*, `None` → reference_date), `dashboard.py` (маркер,
  фильтр тултипа по `horizon_end`). Смысловые правки — шаги 3–4. Маркер
  может стоять за осью (минимум на [ref, H] бывает после window_end) —
  переходное состояние, обработка «узкое место за краем оси» в шаге 3.

**Новые тесты** (`TestSuffixMinimumModel`, 10 шт.; расчёты в докстрингах):
доход до платежа (50 000 / 0 вместо ложного нуля); платёж через границу
месяца (payments 20 000 в последний день месяца); платёж за краем оси
(H = ref+60, последний день оси payments 15 000, free 35 000); нет доходов
после оси (H = ref+89, флаг False); нехватка (6 137 на ref+5, free 0,
payments 10 000); нехватка с резервом 3 000 (резерв ужимается первым);
взнос на цели с авансом/без (50 000/0 и 40 000/10 000); плоское окно
при операции только за осью; `_suffix_min` на ряду. Плюс замены
переписанных: `test_payments_not_cut_at_month_end`,
`test_horizon_stops_at_first_income_after_window`,
`test_income_beyond_cap_does_not_set_horizon`.

**Неочевидное — пример со взносом.** Буквально по примеру консилиума
(один месяц) «без аванса» дало бы free 30 000, а не 40 000: в следующем
месяце savings-операций нет, и неизменное правило резерва снова держит
бюджет целей 10 000 (кейс 9). Это не дефект формулы, а то, что пример
рассматривает один месяц. Фикстура изолирует месяц доходом 100 000 на
1-е следующего месяца в обоих вариантах — объяснено в докстринге теста.
Следствие для пользователя с бюджетом целей и без регулярного резерва:
бюджет следующих месяцев без дохода в горизонте берётся из сегодняшних
денег (у владельца бюджет целей не задан — на приёмку не влияет).

**Мутационная проверка**: H = window_end → 8 тестов красные (в т.ч.
«платёж за краем оси»); минимум только по оси → 2 красных. Код восстановлен.

**Итог шага**: 939 passed (было 928, +11), black чист, flake8 — только
3 pre-existing E501.
