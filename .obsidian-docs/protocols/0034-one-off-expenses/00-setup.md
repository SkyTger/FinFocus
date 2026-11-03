# Шаг 0: Подготовка

## Briefing

- **Цель:** Окружение в worktree и базовая линия тестов.
- Артефакты и первый коммит сделаны при `/protocol-new`, ветка отведена
  от `origin/main` (c549b54), запушена, Draft PR открыт. Фоновая сессия
  идёт «без push» — ветку отправит `/protocol-review-merge`.

## Sub-tasks

1. **Окружение** (`.venv` главного чекаута песочнице не виден):
   ```bash
   uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements-dev.txt
   ```
   Проверить: `.venv/bin/black --version` → 23.11.0; `.venv/bin/flake8 --version`.
2. **Базовая линия:** `.venv/bin/pytest -q` — записать в log.md число
   (ожидается 976 passed). Иначе — записать и разобраться ДО шага 1.
   `.venv/bin/flake8 app/` — записать pre-existing E501 (ожидается 3).
3. `context.md`: Current Step 1, Status In Progress, Next Action Шаг 1.
   Отдельно не коммитить — войдёт в коммит шага 1.
