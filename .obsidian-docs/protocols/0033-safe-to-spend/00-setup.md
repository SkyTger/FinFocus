# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, подготовить окружение
- Артефакты и первый коммит сделаны при `/protocol-new`; ветка отведена
  от локального `main` (b342d4f, на 2 коммита впереди origin — оба
  docs-коммита уедут в main вместе с мержем). Push и Draft PR — делает
  `/protocol-review-merge` (фоновая сессия идёт «без push»).

## Sub-tasks

1. **Окружение в worktree** (`.venv` главного чекаута песочнице не виден):
   ```bash
   uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements-dev.txt
   ```
   (`requirements-dev.txt` включает runtime-зависимости; если нет —
   доставить `-r requirements.txt`). Проверить: `.venv/bin/black --version`
   → 23.11.0.
2. **Базовая линия:** `.venv/bin/pytest -q` — записать в log.md число
   тестов и результат (ожидается 928 passed; если иначе — записать и
   разобраться ДО шага 1, не начинать правки на красной базе).
   `.venv/bin/flake8 app/` — записать известные pre-existing E501.
3. Обновить `context.md`: Current Step 1, Status In Progress, Next Action
   Шаг 1. Не коммитить отдельно — войдёт в коммит шага 1.
