# Work Log: 0006 — Множественные накопительные цели с приоритетами

Этот раздел является **журналом**. Записи только добавляются, старые не изменяются.

---

## Restore context: protocol-0006#ctx-2

---

## Шаг 0: Подготовка (2026-01-21)

**Действия:**
- Создана ветка `0006-multiple-goals` от `origin/main`
- Создан worktree в `/home/skytiger/PycharmProjects/worktrees/0006-multiple-goals`
- Сгенерированы артефакты протокола (plan.md, context.md, log.md, 00-07 step files)

**Решения:**
- Разбил реализацию на 7 шагов для управляемости
- Шаги 4 и 5 разделены: сначала UI layout, потом callbacks (уменьшает сложность каждого шага)
- Dashboard интеграция в отдельном шаге 6 (не смешивать с Goals UI)

**Ожидание:** Утверждение плана пользователем перед созданием PR.

---

## Шаг 1: Миграция и Types (2026-01-21)

**Действия:**
- Добавлено поле `monthly_savings_budget: Numeric(10,2)` в модель User (app/models/database.py)
- Создан модуль `app/types/` с централизованными TypedDicts
  - AllocationResult — результат распределения для одной цели
  - AllocationSummary — сводка распределения бюджета
  - GoalDisplayData — данные для отображения цели в UI
  - GoalsSummary — сводка по всем активным целям
- Создан скрипт миграции `scripts/migrate_001_savings_budget.py` (idempotent, SQLite)
- Написаны 3 unit теста миграции (tests/test_migration.py)
  - test_migration_adds_column_when_not_exists
  - test_migration_idempotent
  - test_migration_default_value_zero
- Выполнена миграция dev базы data/finfocus.db

**Решения:**
- Default для monthly_savings_budget = 0 (бюджет не настроен изначально)
- TypedDicts в отдельном модуле для переиспользования между services и UI
- Миграция проверяет существование колонки через PRAGMA table_info (idempotent)

**Верификация:**
- ✅ black: 2 файла отформатированы (seed scripts)
- ✅ flake8: без ошибок (добавлены noqa: E402 для sys.path манипуляций)
- ✅ pytest: 78/78 тестов прошли (включая 3 новых теста миграции)

**Файлы изменены:**
- app/models/database.py (+1 поле + docstring)
- app/types/__init__.py (создан)
- app/types/goals.py (создан, 4 TypedDicts)
- scripts/migrate_001_savings_budget.py (создан, 93 строки)
- tests/test_migration.py (создан, 3 теста)
- scripts/seed_database.py (flake8 fixes)
- scripts/seed_test_data.py (flake8 fixes)
