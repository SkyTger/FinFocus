# Шаг 1: Миграция БД и модель User

## Briefing
- **Цель:** Добавить поле `savings_mode` в модель User и создать идемпотентный миграционный скрипт для SQLite.
- **Ключевые файлы:**
  - `app/models/database.py` (модифицировать — добавить поле)
  - `scripts/migrate_002_savings_mode.py` (создать — миграция)
  - `tests/test_migration_002.py` (создать — тест миграции)
- **Additional info:**
  - Поле `savings_mode` — String(20), default="free", nullable=False
  - String вместо Enum для упрощения SQLite миграций (ALTER TABLE не поддерживает Enum)
  - Допустимые значения: "free", "medium", "strict" (валидация на уровне сервиса)
  - Образец миграции: `scripts/migrate_001_savings_budget.py`

## Sub-tasks

1. **Добавить поле в модель User:**
   - Открыть `app/models/database.py`
   - В класс `User` добавить:
     ```python
     savings_mode = Column(String(20), default="free", nullable=False)
     ```
   - Добавить комментарий о допустимых значениях

2. **Создать миграционный скрипт:**
   - Создать файл `scripts/migrate_002_savings_mode.py`
   - Реализовать idempotent проверку через `column_exists()`
   - Добавить колонку `savings_mode` с DEFAULT 'free'
   - Использовать паттерн из `migrate_001_savings_budget.py`

3. **Написать тест миграции:**
   - Создать `tests/test_migration_002.py`
   - Тест: миграция добавляет колонку
   - Тест: повторный запуск миграции безопасен (idempotent)
   - Тест: существующие пользователи получают default="free"

## Workflow (Порядок работы)

**Твоя задача — выполнить `Sub-tasks` выше, строго следуя этому циклу.**

1. **Выполнение:** Последовательно выполняй подзадачи.

2. **Базовая проверка:** Убедись что код синтаксически корректен:
   - `python -m py_compile app/models/database.py`
   - `python -m py_compile scripts/migrate_002_savings_mode.py`
   - `python -m py_compile tests/test_migration_002.py`

3. **Фиксация:** После успешной базовой проверки:
   - **Добавь запись в `log.md`**: Опиши добавленное поле и миграцию.
   - **Обнови `context.md`**: `Current Step` на 2, подготовь `Next Action` для Шага 2.
   - Проверь ветку main в поисках случайно добавленных файлов.

4. **Сделай коммит:**
   ```bash
   git add . && git commit -m "feat(model): add User.savings_mode field [protocol-0007/01]"
   ```
   Сделай пуш.

5. **Отчет пользователю:** Сообщи о завершении шага в установленном формате.

## Детали реализации

### Модель User (добавить после monthly_savings_budget)
```python
# Режим накоплений: "free" (100%), "medium" (115%), "strict" (150%)
# Валидация допустимых значений в GoalService.update_savings_mode()
savings_mode = Column(String(20), default="free", nullable=False)
```

### Миграционный скрипт (структура)
```python
#!/usr/bin/env python3
"""Миграция 002: Добавление поля savings_mode в таблицу users.

Идемпотентная миграция — можно запускать повторно.
"""
import sqlite3
from pathlib import Path


def column_exists(cursor, table: str, column: str) -> bool:
    """Проверяет существование колонки в таблице."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate(db_path: str) -> None:
    """Выполняет миграцию."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        if not column_exists(cursor, "users", "savings_mode"):
            cursor.execute(
                "ALTER TABLE users ADD COLUMN savings_mode VARCHAR(20) "
                "NOT NULL DEFAULT 'free'"
            )
            conn.commit()
            print("✓ Колонка savings_mode добавлена")
        else:
            print("→ Колонка savings_mode уже существует, пропуск")
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "data" / "finfocus.db"
    if not db_path.exists():
        print(f"База данных не найдена: {db_path}")
        exit(1)
    migrate(str(db_path))
```
