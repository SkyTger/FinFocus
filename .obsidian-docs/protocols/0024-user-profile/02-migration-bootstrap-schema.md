# Шаг 2: Migration + Bootstrap + Schema

## Briefing

- **Цель:** Миграция 007 для avatar_id, обновление bootstrap, TypedDicts для профиля
- **Ключевые файлы:**
  - `app/core/migrations.py` — EDIT: +миграция 007_avatar_id (идемпотентная через _column_exists)
  - `app/core/bootstrap.py` — EDIT: +avatar_id="emoji-default" в default User creation
  - `app/schema/onboarding.py` — EDIT: +UserProfile TypedDict, +name/avatar_id в OnboardingStatus
- **Доп. информация:** Паттерн миграции из existing migrations.py (проверка _column_exists). Schema расширение backwards-compatible.

## Sub-tasks

1. Добавить миграцию 007 в `app/core/migrations.py`:
   ```python
   if not _column_exists(cursor, "users", "avatar_id"):
       cursor.execute(
           "ALTER TABLE users ADD COLUMN avatar_id VARCHAR(20) DEFAULT 'emoji-default' NOT NULL"
       )
       applied.append("007_avatar_id")
   ```

2. Обновить `app/core/bootstrap.py`:
   - В auto_bootstrap() при создании default User добавить avatar_id="emoji-default"

3. Обновить `app/schema/onboarding.py`:
   - Добавить `UserProfile` TypedDict (name: str, avatar_id: str)
   - Расширить `OnboardingStatus` TypedDict полями name: str, avatar_id: str

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/core/migrations.py app/core/bootstrap.py app/schema/onboarding.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 3, Next Action: Шаг 3
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(profile): add migration 007, bootstrap avatar_id, UserProfile TypedDict [protocol-0024-user-profile/02]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
