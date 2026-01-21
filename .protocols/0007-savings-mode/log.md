# Work Log: 0007 — Три режима накоплений (Savings Mode)

Этот раздел является **журналом**. Записи только добавляются, старые не изменяются.

**Restore context**: protocol-0007#ctx-3
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

---

## Шаг 5: UI selector и callback

**Дата**: 2026-01-21

**Действия**:
- Создана функция `_build_mode_selector()` с RadioItems
- Интегрирован selector в layout через Row/Col (lg=8/4 для адаптивности)
- Создан callback `save_savings_mode()` для сохранения режима в БД
- Обновлены 9 callbacks для передачи savings_mode в `_recalculate_and_render()`
- Добавлены CSS стили (~80 строк) для mode selector

**Изменения файлов**:
- `app/components/goals.py:52-92` — функция _build_mode_selector()
- `app/components/goals.py:1086-1104` — интеграция в layout (Row/Col)
- `app/components/goals.py:1277-1312` — callback save_savings_mode()
- `app/components/goals.py` — обновлены callbacks: create_goal, add_contribution, update_goal, confirm_delete_goal, toggle_goal_status, save_budget, move_priority_up, move_priority_down
- `app/assets/goals.css:301-380` — стили для mode selector

**Обновленные callbacks**:
1. `create_goal` — +State savings_mode, +параметр, +передача в helper
2. `add_contribution` — +State savings_mode, +параметр, +передача в helper
3. `update_goal` — +State savings_mode, +параметр, +передача в helper
4. `confirm_delete_goal` — +State savings_mode, +параметр, +передача в helper
5. `toggle_goal_status` — +State savings_mode, +параметр, +передача в helper
6. `save_budget` — +State savings_mode, +параметр, +передача в helper
7. `move_priority_up` — +State savings_mode, +параметр, +передача в helper
8. `move_priority_down` — +State savings_mode, +параметр, +передача в helper

**Решения**:
- Row/Col с lg=8/4 — summary слева, mode selector справа на десктопах
- `savings_mode or "free"` во всех вызовах — fallback при None из store
- Стили используют фирменный цвет #198754 (primary-green) для консистентности

---

## Шаг 6: Финализация

**Дата**: 2026-01-21

**Действия**:
- Запущен black — переформатировано 2 файла (allocation_service.py, goals.py)
- Запущен flake8 — найдено 5 ошибок, все исправлены:
  - E501 (line too long) в goals.py, goal_service.py, serializers.py
  - F841 (unused variable) в goals.py
- Запущен pytest — все 111 тестов проходят (было 98, добавлено 13 тестов savings_mode)
- PR #7 переведен в статус Ready for Review

**Изменения файлов**:
- `app/components/goals.py` — black форматирование, исправлены длинные строки
- `app/services/allocation_service.py` — black форматирование
- `app/services/goal_service.py` — исправлен длинный комментарий
- `app/utils/serializers.py` — исправлены длинные строки в docstring

**Результаты верификации**:
- Black: 2 файла переформатированы, 44 без изменений
- Flake8: 0 ошибок после исправлений
- Pytest: 111/111 passed in 2.01s

**Коммиты**:
- `8f7b1b7`: chore: final QA fixes [protocol-0007/06]

**PR Status**: Ready for Review
**URL**: https://github.com/SkyTger/FinFocus/pull/7

---

## Протокол завершен

**Итого по протоколу 0007-savings-mode**:
- Шагов выполнено: 7 (0-6)
- Коммитов: 7
- Новых файлов: 4 (migrate_002, test_migration_002, test_savings_mode, serializers)
- Измененных файлов: 6 (database.py, goal_service.py, allocation_service.py, goals.py, goals.css, __init__.py)
- Новых тестов: 13 (3 миграция + 7 savings_mode + 3 allocation modes)
- Всего тестов: 111 (было 98)
- PR: https://github.com/SkyTger/FinFocus/pull/7

**Критерии приёмки**:
- [x] Поле `User.savings_mode` добавлено в модель с default='free'
- [x] `AllocationService.calculate_allocation()` принимает параметр `savings_mode` и применяет множитель
- [x] UI селектор отображает три режима с описаниями
- [x] Изменение режима пересчитывает и обновляет UI allocation
- [x] Миграционный скрипт создан и работает идемпотентно
- [x] Unit тесты покрывают все три режима в AllocationService
- [x] Существующие тесты проходят без изменений
