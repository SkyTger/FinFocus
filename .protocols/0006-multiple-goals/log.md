# Work Log: 0006 — Множественные накопительные цели с приоритетами

Этот раздел является **журналом**. Записи только добавляются, старые не изменяются.

---

## Restore context: protocol-0006#ctx-4

---

## Restore context: protocol-0006#ctx-3

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

---

## Шаг 3: AllocationService (2026-01-21)

**Действия:**
- Создан новый сервис AllocationService для распределения бюджета накоплений между целями
- Реализован жадный алгоритм в calculate_allocation():
  - Сортировка целей по priority ASC (1, 2, 3...)
  - Для каждой цели: allocated = min(monthly_contribution, remaining_budget)
  - COMPLETED цели → skipped_reason="completed"
  - PAUSED цели → skipped_reason="paused"
  - Цели с monthly_contribution <= 0 → skipped_reason="zero_contribution"
- Обновлен app/services/__init__.py с экспортами AllocationService и TypedDicts
- Написаны 7 unit тестов для всех сценариев распределения

**Решения:**
- Жадный алгоритм выделяет бюджет строго по приоритету (высший получает первым)
- TypedDicts (AllocationResult, AllocationSummary) используются для типизации результата
- Метод calculate_allocation() не зависит от session — чистая функция на основе списка целей

**Верификация:**
- ✅ black: 2 файла отформатированы (allocation_service.py, test_allocation_service.py)
- ✅ flake8: без ошибок
- ✅ pytest: 93/93 тестов прошли (включая 7 новых тестов AllocationService)

**Написаны тесты** (tests/test_allocation_service.py, 7 тестов):
- test_empty_goals_list — пустой список целей → empty results, totals = 0
- test_single_goal_fully_funded — одна цель, бюджет покрывает полностью
- test_single_goal_partially_funded — одна цель, бюджет частично
- test_multiple_goals_full_coverage — несколько целей, бюджет покрывает все
- test_multiple_goals_partial_coverage — 3 цели, бюджет покрывает только 1.5
- test_zero_budget — нулевой бюджет → budget_not_set=True
- test_mixed_statuses — цели с разными статусами (ACTIVE, PAUSED, COMPLETED)

**Файлы изменены:**
- app/services/allocation_service.py (создан, 113 строк)
- app/services/__init__.py (+4 импорта, +4 экспорта в __all__)
- tests/test_allocation_service.py (создан, 311 строк)

---

## Шаг 4: Goals UI — список целей (2026-01-21)

**Действия:**
- Рефакторинг Goals UI для отображения списка карточек целей вместо одной карточки
- Созданы новые UI функции:
  - _build_summary_section() — сводная секция с общим прогрессом и статусом распределения (127 строк)
  - _build_budget_alert() — info-alert для ненастроенного бюджета
  - _build_goals_list() — список карточек целей с сортировкой по priority
- Переписан _build_goal_card() для поддержки списка:
  - Добавлено отображение allocated_amount (если есть)
  - Добавлен allocation_status badge ("Полностью", "Частично", "Не профинансирована", "Пропущена")
  - Добавлен priority badge (#1, #2, #3...)
  - Добавлены кнопки ↑↓ для изменения приоритетов (pattern-matching IDs)
  - Metrics row адаптирован для 4 колонок (allocation section)
- Обновлен _build_action_buttons() для pattern-matching IDs (edit, toggle, delete)
- Переписан load_goal_data() callback:
  - Загружает ВСЕ цели (ACTIVE + PAUSED)
  - Получает бюджет через get_savings_budget()
  - Вызывает AllocationService.calculate_allocation()
  - Формирует GoalsSummary
  - Строит layout: summary + alert + goals_list
- Обновлен create_goals_layout(): добавлена кнопка "Создать цель" в заголовок
- Обновлен toggle_create_goal_modal(): слушает обе кнопки (empty state + header)
- Удалены дублирующие TypedDicts (GoalDisplayData теперь импортируется из app.services)

**Стили** (app/assets/goals.css, +95 строк):
- .goals-list — flexbox контейнер для списка карточек
- .goal-card-priority — badge с номером приоритета
- .goal-card-allocation — секция с allocated_amount (gradient background)
- .priority-btn — кнопки ↑↓ с hover эффектом
- .summary-section — сводная секция (gradient header, shadow)
- .budget-alert — info-alert с левым border
- .create-goal-header-btn — кнопка в заголовке
- Адаптивность: 768px, 576px breakpoints

**Решения:**
- Layout остался тем же (goal-card-container), но внутри возвращается html.Div со списком элементов
- Pattern-matching IDs используются для всех кнопок действий (готовность к callbacks в Шаге 5)
- AllocationResult преобразуется в dict для удобного доступа по goal_id
- История взносов показывается для первой цели (по приоритету)

**Верификация:**
- ✅ black: 1 файл отформатирован (goals.py)
- ✅ flake8: без ошибок (1 noqa: E501 для длинной строки)
- ✅ pytest: 93/93 тестов прошли

**Файлы изменены:**
- app/components/goals.py (+380 строк новой логики, -100 строк удалено)
- app/assets/goals.css (+95 строк новых стилей)

---

## Шаг 5: Goals UI — Callbacks (2026-01-21)

**Действия:**
- Добавлены dcc.Store компоненты для хранения budget и allocation состояний
- Создана helper функция `_recalculate_and_render()` (~80 строк) для переиспользования логики пересчета allocation
- Реализованы 3 callback'а модала бюджета:
  - `open_budget_modal()` — открывает модал с текущим значением бюджета из Store или БД
  - `close_budget_modal()` — закрывает модал при клике на Отмена
  - `save_budget()` — сохраняет бюджет в БД и пересчитывает allocation для всех целей
- Реализованы 2 Pattern-Matching callback'а для изменения приоритетов:
  - `move_priority_up()` — повышает приоритет цели (уменьшает priority на 1)
  - `move_priority_down()` — понижает приоритет цели (увеличивает priority на 1)
- Обновлен callback `load_goal_data()`:
  - Добавлены Outputs для budget-store и allocation-store
  - Инициализирует stores при первой загрузке страницы
  - Использует `_recalculate_and_render()` для построения UI
- Добавлен импорт ALL из dash для Pattern-Matching callbacks

**Решения:**
- Helper функция `_recalculate_and_render()` инкапсулирует логику загрузки целей, вызова AllocationService и построения UI компонентов
- Все новые callbacks используют guard clauses согласно ADR-003 (проверка `ctx.triggered[0].get('value') is None`)
- Budget и allocation stores обеспечивают синхронизацию состояния между callback'ами без повторных запросов к БД
- При изменении бюджета или приоритетов автоматически пересчитывается allocation и обновляется UI

**Верификация:**
- ✅ black: без изменений
- ✅ flake8: без ошибок (добавлены 2 noqa: E501 для длинных строк)
- ✅ pytest: 93/93 тестов прошли

**Файлы изменены:**
- app/components/goals.py (+275 строк: helper функция, 5 новых callbacks, обновлен load_goal_data, добавлен импорт ALL)
