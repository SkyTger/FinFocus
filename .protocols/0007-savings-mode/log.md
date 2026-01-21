# Work Log: 0007 — Три режима накоплений (Savings Mode)

Этот раздел является **журналом**. Записи только добавляются, старые не изменяются.

**Restore context**: protocol-0007#ctx-2
**Restore context**: protocol-0007#ctx-1

---

## Шаг 0: Подготовка и фиксация плана

**Дата**: 2026-01-21

**Действия**:
- Создана ветка `0007-savings-mode` и worktree
- Созданы артефакты протокола: `plan.md`, `context.md`, `log.md`, файлы шагов 00-06
- План основан на `.design/brief.md` и `.design/solution-v2.md`

**Решения**:
- Выбрано 6 шагов (вместо изначальных 6 из solution-v2) — оптимальная декомпозиция для итераций
- String вместо SQLAlchemy Enum для `savings_mode` — упрощает миграции SQLite
- Константы `SAVINGS_MODE_MULTIPLIERS` размещаются в `allocation_service.py` — cohesion с алгоритмом

**Особенности**:
- На промежуточных шагах только базовая проверка синтаксиса (py_compile)
- Полная верификация (black, flake8, pytest) на финальном шаге 6

---

## Шаг 1: Миграция БД и модель User

**Дата**: 2026-01-21

**Действия**:
- Добавлено поле `savings_mode` в модель `User` (String(20), default="free", nullable=False)
- Создан миграционный скрипт `scripts/migrate_002_savings_mode.py` (idempotent)
- Написаны 3 unit теста в `tests/test_migration_002.py`

**Изменения файлов**:
- `app/models/database.py:65-67` — добавлено поле с комментарием
- `scripts/migrate_002_savings_mode.py` — новый файл (~90 строк)
- `tests/test_migration_002.py` — новый файл (~100 строк)

**Решения**:
- String вместо Enum для `savings_mode` — SQLite не поддерживает ALTER TABLE для Enum
- Валидация допустимых значений будет на уровне сервиса (GoalService.update_savings_mode)
- Фикстура теста создает схему с monthly_savings_budget, но без savings_mode

---

## Шаг 2: GoalService расширение

**Дата**: 2026-01-21

**Действия**:
- Добавлена константа `VALID_SAVINGS_MODES = {"free", "medium", "strict"}`
- Добавлен метод `get_savings_mode(user_id: int) -> str`
- Добавлен метод `update_savings_mode(user_id: int, mode: str) -> None`
- Обновлены экспорты в `app/services/__init__.py`
- Написаны 6 unit тестов в `tests/test_savings_mode.py`

**Изменения файлов**:
- `app/services/goal_service.py:12-14` — константа VALID_SAVINGS_MODES
- `app/services/goal_service.py:453-500` — методы get/update_savings_mode с TODO
- `app/services/__init__.py:25,55` — экспорт VALID_SAVINGS_MODES
- `tests/test_savings_mode.py` — новый файл (~90 строк)

**Решения**:
- Методы размещены в GoalService с TODO о переносе в UserService при рефакторинге
- Паттерн аналогичен существующим get/update_savings_budget

---

## Шаг 3: AllocationService модификация

**Дата**: 2026-01-21

**Действия**:
- Добавлена константа `SAVINGS_MODE_MULTIPLIERS` с множителями {free: 1.0, medium: 1.15, strict: 1.5}
- Добавлен параметр `savings_mode: str = "free"` в `calculate_allocation()`
- Множитель применяется внутри цикла: `monthly_needed = base_monthly * multiplier`
- Добавлено логирование warning при неизвестном режиме (fallback на 1.0)
- Написаны 3 unit теста для каждого режима

**Изменения файлов**:
- `app/services/allocation_service.py:10-15` — константа SAVINGS_MODE_MULTIPLIERS
- `app/services/allocation_service.py:29,56-61,87-89` — параметр и применение множителя
- `tests/test_allocation_service.py:350-430` — 3 теста (free, medium, strict)

**Решения**:
- Множитель применяется ВНУТРИ цикла, а не к итоговому total_needed — обеспечивает корректный расчет для каждой цели
- `monthly_contribution_needed` в результате содержит ADJUSTED значение (base * multiplier)
- Default `savings_mode="free"` обеспечивает полную обратную совместимость

---

## Шаг 4: UI stores и helper

**Дата**: 2026-01-21

**Действия**:
- Добавлена константа `MODE_OPTIONS` с label/description для каждого режима
- Добавлен `dcc.Store(id="goals-savings-mode-store")` в layout
- Расширена функция `_recalculate_and_render()` параметром `savings_mode`
- Обновлен `load_goal_data()` callback: новый Output, чтение режима из БД, передача в helper

**Изменения файлов**:
- `app/components/goals.py:35-49` — константа MODE_OPTIONS
- `app/components/goals.py:1122-1123` — dcc.Store для savings_mode
- `app/components/goals.py:979-1017` — расширение _recalculate_and_render
- `app/components/goals.py:1136-1216` — обновление load_goal_data callback

**Решения**:
- MODE_OPTIONS содержит готовые label/description для UI selector (Шаг 5)
- Все stores инициализируются при загрузке страницы /goals
- Helper принимает default `savings_mode="free"` для обратной совместимости с другими callbacks
