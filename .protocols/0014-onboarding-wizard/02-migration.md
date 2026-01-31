# Шаг 2: Migration Script

## Briefing

- **Цель:** Создать скрипт миграции для добавления first_launch колонки
- **Ключевые файлы:**
  - `scripts/migrate_first_launch.py` — NEW: миграция
- **Доп. информация:** Существующие пользователи с starting_balance != 0 → first_launch = False

## Sub-tasks

1. **Создать скрипт миграции** (`scripts/migrate_first_launch.py`):
   ```python
   """Миграция: добавление колонки first_launch в таблицу users.

   Логика:
   - Если starting_balance != 0 → first_launch = False (уже настроен)
   - Если starting_balance == 0 → first_launch = True (нужен онбординг)
   """
   import sqlite3
   from pathlib import Path

   DB_PATH = Path(__file__).parent.parent / "data" / "finfocus.db"

   def migrate():
       conn = sqlite3.connect(DB_PATH)
       cursor = conn.cursor()

       # Проверяем существование колонки
       cursor.execute("PRAGMA table_info(users)")
       columns = [col[1] for col in cursor.fetchall()]

       if "first_launch" not in columns:
           # Добавляем колонку с default=True
           cursor.execute("ALTER TABLE users ADD COLUMN first_launch BOOLEAN DEFAULT 1")

           # Обновляем для пользователей с настроенным балансом
           cursor.execute("""
               UPDATE users
               SET first_launch = 0
               WHERE starting_balance != 0
           """)

           conn.commit()
           print(f"Migration complete: first_launch added to users table")
       else:
           print("Column first_launch already exists, skipping")

       conn.close()

   if __name__ == "__main__":
       migrate()
   ```

2. **Запустить миграцию** (если есть тестовая БД):
   ```bash
   python scripts/migrate_first_launch.py
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile scripts/migrate_first_launch.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 3, Next Action: Шаг 3
5. Коммит: `git add . && git commit -m "feat(scripts): add first_launch migration [protocol-0014/02]"`
6. Push
7. Отчёт по формату
