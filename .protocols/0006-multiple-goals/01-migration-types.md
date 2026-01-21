# Шаг 1: Миграция и Types

## Briefing
- **Цель:** Добавить поле `monthly_savings_budget` в модель User и создать централизованные TypedDicts для типизации данных между сервисами и UI.
- **Ключевые файлы:**
  - `app/models/database.py` (изменить — добавить поле в User)
  - `app/types/__init__.py` (создать)
  - `app/types/goals.py` (создать)
  - `scripts/migrate_001_savings_budget.py` (создать)
  - `tests/test_migration.py` (создать)
- **Additional info:**
  - Миграция SQLite через ALTER TABLE (без Alembic)
  - TypedDicts из solution-v3.md: AllocationResult, AllocationSummary, GoalDisplayData, GoalsSummary
  - Default для monthly_savings_budget = 0

## Sub-tasks

1. **Обновить User модель** в `app/models/database.py`:
   ```python
   monthly_savings_budget = Column(Numeric(10, 2), default=0, nullable=False)
   ```
   Добавить docstring с описанием поля.

2. **Создать папку types**: `app/types/`

3. **Создать `app/types/__init__.py`**:
   ```python
   """Централизованные типы данных для FinFocus."""
   from app.types.goals import (
       AllocationResult,
       AllocationSummary,
       GoalDisplayData,
       GoalsSummary,
   )

   __all__ = [
       "AllocationResult",
       "AllocationSummary",
       "GoalDisplayData",
       "GoalsSummary",
   ]
   ```

4. **Создать `app/types/goals.py`** с TypedDicts:
   - `AllocationResult` — результат распределения для одной цели
   - `AllocationSummary` — сводка распределения бюджета
   - `GoalDisplayData` — данные для отображения цели в UI
   - `GoalsSummary` — сводка по всем активным целям

   Все поля с типами из solution-v3.md.

5. **Создать скрипт миграции** `scripts/migrate_001_savings_budget.py`:
   - Проверка существования колонки через PRAGMA table_info
   - ALTER TABLE users ADD COLUMN если не существует
   - Idempotent (можно запускать повторно)

6. **Написать тест миграции** `tests/test_migration.py`:
   - Тест: колонка добавляется если не существует
   - Тест: повторный запуск не падает
   - Тест: default value = 0

7. **Запустить миграцию** на dev базе:
   ```bash
   python scripts/migrate_001_savings_budget.py data/finfocus.db
   ```

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-7.

2. **Верификация:** После завершения ВСЕХ подзадач:
   ```bash
   black app/ scripts/
   flake8 app/ scripts/
   pytest tests/test_migration.py -v
   pytest tests/ -v  # Убедиться что существующие тесты не сломались
   ```
   Исправляй все ошибки, пока проверки не станут "зелеными".

3. **Фиксация:**
   - Добавь запись в `log.md`: что сделано, какие решения приняты
   - Обнови `context.md`: `Current Step` = 2, `Next Action` = "Шаг 2: GoalService"
   - Проверь ветку main: `git log main --oneline -5` (убедись что наши файлы там нет)

4. **Коммит:**
   ```bash
   git add .
   git commit -m "feat(models): add monthly_savings_budget and types module [protocol-0006/01]"
   git push
   ```

5. **Отчет пользователю** в установленном формате.
