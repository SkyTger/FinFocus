# Шаг 6: Main + Dashboard

## Briefing

- **Цель:** Интегрировать profile modal и Store в main.py, добавить dashboard greeting
- **Ключевые файлы:**
  - `app/main.py` — EDIT: +profile modal, +dcc.Store("profile-updated")
  - `app/components/dashboard.py` — EDIT: inline greeting с именем пользователя
- **Доп. информация:** См. solution-v3.md секции "7. Dashboard greeting" и "8. main.py". Dashboard greeting обновляется только при навигации (документировано, приемлемо для single-user).

## Sub-tasks

1. Обновить `app/main.py`:
   - Добавить import: `from app.components.profile_modal import create_profile_modal`
   - В layout (после onboarding wizard): `create_profile_modal()`
   - Добавить `dcc.Store(id="profile-updated", data=None)` в layout

2. Обновить `app/components/dashboard.py` — `create_dashboard_layout()`:
   - Inline read имени:
     ```python
     greeting_name = "Пользователь"
     try:
         with get_db_session() as session:
             profile = OnboardingService(session).get_profile(DEFAULT_USER_ID)
             greeting_name = profile["name"]
     except Exception:
         logger.warning("Failed to load user name for dashboard greeting", exc_info=True)
     ```
   - Использовать greeting_name в H4: `f"Добро пожаловать, {greeting_name}!"`
   - Добавить комментарий: NOTE — greeting обновляется только при навигации

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/main.py app/components/dashboard.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 7, Next Action: Шаг 7
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(profile): integrate profile modal in main.py, dashboard greeting [protocol-0024-user-profile/06]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
