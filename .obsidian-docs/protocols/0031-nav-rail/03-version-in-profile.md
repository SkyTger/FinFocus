# Шаг 3: Версия в окне профиля

## Briefing

- **Цель:** FR-5/AC-9 — версия показывается в окне профиля, берётся из проекта.
- **Ключевые файлы:**
  - `app/components/profile_modal.py:62` — `ModalFooter`
  - `tests/test_profile_modal_callbacks.py` — расширяется
- **Доп. информация:** Колбэк `handle_profile_modal` НЕ трогать.

## Sub-tasks

1. В `create_profile_modal`, в `ModalFooter` перед кнопками:
   ```python
   html.Span(
       f"FinFocus v{__version__}",
       className="profile-modal-version text-muted small me-auto",
   )
   ```
   Импорт `from app import __version__`. Вычисляется на **построении**: модал живёт в глобальном layout и присутствует всегда, поэтому ни колбэка, ни Store не нужно.

2. В докстринге фрагмента отметить: **этот импорт — единственное, что делает `app/version.py` достижимым по графу импортов от `run.py`**, то есть попадающим в PyInstaller-бандл. Убирать строку версии отсюда без переноса импорта нельзя.

3. Расширить `tests/test_profile_modal_callbacks.py`: версия присутствует в дереве модала.

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка: `.venv/bin/python -m py_compile app/components/profile_modal.py`
3. `.venv/bin/python -m pytest tests/test_profile_modal_callbacks.py tests/test_version.py -v`
4. Обнови `log.md`, `context.md` (Current Step 4)
5. Коммит: `feat(profile): версия проекта в окне профиля [protocol-0031/03]`
6. Push, отчёт
