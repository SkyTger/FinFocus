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

### Step 01 — Контракт модели + геттер порога подушки (commit: 2ef26f9)
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

