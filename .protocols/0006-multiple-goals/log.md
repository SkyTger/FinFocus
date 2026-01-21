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

---

## Шаг 2: GoalService — приоритеты и бюджет (2026-01-21)

**Действия:**
- Удалено ограничение D009 из create_goal() — теперь можно создавать множественные активные цели
- Добавлен метод get_next_priority(user_id) — возвращает max(priority) + 1
- Обновлен create_goal() для auto-priority — параметр priority: int | None = None
- Добавлен метод update_priority(goal_id, new_priority) с shift-down алгоритмом:
  - Если new < old: сдвиг целей с priority >= new AND < old на +1
  - Если new > old: сдвиг целей с priority > old AND <= new на -1
- Добавлены convenience методы:
  - move_priority_up(goal_id) — уменьшает priority на 1
  - move_priority_down(goal_id) — увеличивает priority на 1
- Добавлены методы управления бюджетом:
  - get_savings_budget(user_id) — получает User.monthly_savings_budget
  - update_savings_budget(user_id, budget) — обновляет бюджет с валидацией >= 0
- get_all_by_user() уже сортирует по priority ASC (строка 177)

**Решения:**
- Методы бюджета добавлены в GoalService (не UserService) чтобы избежать circular dependency
- Shift-down алгоритм использует диапазоны для bulk update
- Convenience методы move_up/down делегируют update_priority() для DRY

**Верификация:**
- ✅ black: 1 файл отформатирован (goal_service.py)
- ✅ flake8: без ошибок
- ✅ pytest: 86/86 тестов прошли (включая 8 новых тестов приоритетов)

**Написаны тесты** (tests/test_goal_service_priority.py, 8 тестов):
- test_get_next_priority_empty — возвращает 1 если нет целей
- test_get_next_priority_with_goals — возвращает max+1
- test_create_goal_auto_priority — auto-priority работает
- test_update_priority_shift_up — сдвиг вверх при повышении приоритета
- test_update_priority_shift_down — сдвиг вниз при понижении приоритета
- test_move_priority_up_down — convenience методы работают
- test_get_savings_budget — получение бюджета
- test_update_savings_budget — обновление бюджета

**Файлы изменены:**
- app/services/goal_service.py (+171 строка, -12 строк удалено D009)
- tests/test_goal_service_priority.py (создан, 186 строк)
