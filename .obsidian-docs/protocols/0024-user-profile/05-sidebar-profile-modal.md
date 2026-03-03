# Шаг 5: Sidebar + Profile Modal

## Briefing

- **Цель:** Сделать sidebar динамическим (профиль из БД), создать глобальный profile modal
- **Ключевые файлы:**
  - `app/components/sidebar.py` — EDIT: динамический профиль, clickable container, callback с loguru
  - `app/components/profile_modal.py` — CREATE: модал редактирования (имя + аватарка), один callback
  - `app/assets/sidebar.css` — EDIT: +sidebar-profile-clickable стили
- **Доп. информация:** См. solution-v3.md секции "5. Sidebar" и "6. Profile Modal". Profile modal использует `with get_db_session()` + `session.commit()`. Sidebar callback реагирует на url.pathname и profile-updated Store.

## Sub-tasks

1. Обновить `app/components/sidebar.py`:
   - Заменить хардкод профиля на динамический блок с id:
     - `sidebar-profile-container` (n_clicks=0, cursor: pointer, className="sidebar-profile-clickable")
     - `sidebar-profile-avatar` (default: "😊")
     - `sidebar-profile-name` (default: "Пользователь")
     - Текст "Профиль ✏️" под именем
   - Добавить callback `update_sidebar_profile`:
     - Input: url.pathname, profile-updated.data
     - Output: sidebar-profile-name.children, sidebar-profile-avatar.children
     - try/except с logger.warning(..., exc_info=True), fallback defaults

2. Создать `app/components/profile_modal.py`:
   - `create_profile_modal()` → dbc.Modal с id="profile-modal"
     - Поля: имя (profile-name-input) + аватарка (profile-avatar-selector RadioItems)
     - Кнопки: "Отмена" (profile-cancel-btn) + "Сохранить" (profile-save-btn)
   - Callback `handle_profile_modal`:
     - Inputs: sidebar-profile-container.n_clicks, profile-save-btn.n_clicks, profile-cancel-btn.n_clicks
     - States: profile-name-input.value, profile-avatar-selector.value
     - Outputs: profile-modal.is_open, profile-name-input.value, profile-avatar-selector.value, profile-updated.data (allow_duplicate=True)
     - Open → load from DB with get_db_session()
     - Save → update_profile() + session.commit() + timestamp
     - Cancel → close
     - ValueError → modal stays open, log warning
     - Exception → modal closes, log error
   - Import: `from dash.exceptions import PreventUpdate`

3. Добавить CSS в `app/assets/sidebar.css`:
   - `.sidebar-profile-clickable` — cursor pointer, border-radius 12px, transition
   - `.sidebar-profile-clickable:hover` — background rgba(46, 204, 113, 0.08)

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/sidebar.py app/components/profile_modal.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 6, Next Action: Шаг 6
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(profile): dynamic sidebar profile and profile edit modal [protocol-0024-user-profile/05]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
