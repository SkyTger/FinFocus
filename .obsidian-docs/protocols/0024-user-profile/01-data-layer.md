# Шаг 1: Data Layer

## Briefing

- **Цель:** Создать конфиг аватарок и добавить avatar_id в модель User
- **Ключевые файлы:**
  - `app/config/__init__.py` — CREATE: пустой `__init__`
  - `app/config/avatars.py` — CREATE: AVATARS dict (10 emoji), DEFAULT_AVATAR_ID, get_avatar_emoji()
  - `app/models/database.py` — EDIT: +avatar_id Column(String(20)) в User
- **Доп. информация:** См. solution-v3.md секции "1. Конфиг аватарок" и "Модель данных"

## Sub-tasks

1. Создать `app/config/__init__.py` (пустой файл для пакета)

2. Создать `app/config/avatars.py`:
   - AVATARS dict с 10 emoji-вариантами (emoji-default, emoji-rocket, emoji-fox, emoji-cat, emoji-coffee, emoji-star, emoji-fire, emoji-crystal, emoji-leaf, emoji-target)
   - DEFAULT_AVATAR_ID = "emoji-default"
   - get_avatar_emoji(avatar_id) -> str с fallback на default

3. Добавить в User модель (`app/models/database.py`):
   ```python
   avatar_id = Column(String(20), default="emoji-default", nullable=False)
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/config/avatars.py app/models/database.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 2, Next Action: Шаг 2
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(profile): add avatars config and avatar_id to User model [protocol-0024-user-profile/01]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
