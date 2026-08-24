# Шаг 1: Контракт модели + лёгкий геттер порога подушки

## Briefing

- **Цель:** Завести контракт модели слоёв (TypedDict'ы + константы) и добавить в `CushionService` лёгкий метод чтения порога подушки без пересчёта баланса.
- **Ключевые файлы:**
  - `app/schema/money_layers.py` — НОВЫЙ
  - `app/schema/__init__.py` — реэкспорт
  - `app/services/cushion_service.py` — ДОБАВЛЕНИЕ метода (единственное разрешённое отступление от C-3)
  - `tests/test_cushion_service.py` — новые тесты
- **Источник правды:** `.obsidian-docs/design/epic-11-panel-batch-1/solution-v4.md`, секция «Ключевые интерфейсы» → блок `app/schema/money_layers.py` и блок `cushion_service.py`. Докстринги в решении приведены целиком — переносить как есть.
- **Соответствует шагам 1–2 плана решения** (оценка 3 ч).

## Sub-tasks

1. **`app/schema/money_layers.py`** — по листингу решения:
   - `LayerKey = Literal["free", "payments", "reserve"]`
   - Константы: `WINDOW_DAYS = 45`, `MAX_MILESTONES_IN_WINDOW = 3`, `MAX_X_TICKS = 11`, `LAYER_COLORS`, `LAYER_LABELS` — каждая с докстрингом из решения
   - `Horizons(NamedTuple)`: `collect_start`, `window_end`, `payments_end`
   - TypedDict'ы: `DayLayers` (включая `reserve_configured`), `UpcomingPayment`, `GoalMilestone`, `TodaySlice`, `MoneyLayersData` (включая `degraded`, `is_empty`, `window_is_flat`, `reserve_configured_today`)
   - Модуль-докстринг с двумя Note: контракт под кусок 1 (стабильность до куска 2 не гарантируется); вердикта в контракте НЕТ (решение владельца п. 3а)
   - **НЕ создавать:** `VerdictLevel`, `VERDICT_TEXTS`, `VERDICT_COLORS`, `DIP_RATIO`, `DIP_FLOOR`
   - Денежные поля — только `Decimal` (C-2)

2. **`app/schema/__init__.py`** — реэкспорт новых типов и констант, добавить в `__all__` (стиль существующего файла).

3. **`CushionService.get_threshold_amount(user_id) -> Decimal`** — по листингу решения:
   - Формула `target * threshold_percent / 100`, **без** вызова `_get_current_balance()`
   - `Decimal("0")` при отсутствии пользователя или ненастроенной подушке — тихий дефолт, **без** `ValidationError`
   - Докстринг с обоснованием: почему не через `get_settings()` (тот тянет полный обход recurring-истории)
   - Существующие методы сервиса **не трогать**

4. **Тесты в `tests/test_cushion_service.py`:**
   - Порог по проценту (target 100 000, percent 30 → 30 000)
   - `target = 0` → `Decimal("0")`
   - Отсутствующий пользователь → `Decimal("0")`, исключения нет
   - **monkeypatch-assert: `calculate_daily_balances` / `get_balance_on_date` не вызывались** — это и есть смысл нового метода

## Проверки шага

- `python -m py_compile app/schema/money_layers.py app/services/cushion_service.py`
- `.venv/bin/pytest tests/test_cushion_service.py -q` — зелёный
- `.venv/bin/black app/schema/money_layers.py app/services/cushion_service.py tests/test_cushion_service.py`
- `.venv/bin/flake8 --select=F app/schema/ app/services/cushion_service.py` — пусто
- Импорт из чистого интерпретатора: `python -c "from app.schema import MoneyLayersData, WINDOW_DAYS; print(WINDOW_DAYS)"` → 45

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile {FILES}`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 2, Next Action: Шаг 2
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(schema): контракт модели слоёв + лёгкий геттер порога подушки [protocol-0028/01]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
