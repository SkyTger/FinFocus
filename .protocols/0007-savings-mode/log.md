# Work Log: 0007 — Три режима накоплений (Savings Mode)

Этот раздел является **журналом**. Записи только добавляются, старые не изменяются.

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
