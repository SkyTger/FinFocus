# Work Log: 0024-user-profile — User Profile — Персонализация приложения

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

Restore context: protocol-0024#ctx-1

---

## Step Log

### Step 01 — Data Layer
- Создан `app/config/__init__.py` (пустой)
- Создан `app/config/avatars.py` — 10 emoji аватарок, DEFAULT_AVATAR_ID, get_avatar_emoji()
- Добавлен `avatar_id` Column(String(20)) в User модель
