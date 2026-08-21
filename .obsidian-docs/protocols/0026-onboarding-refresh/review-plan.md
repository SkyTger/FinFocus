# Review and Merge Plan: 0026-onboarding-refresh

## Paths

- **Project root**: `/home/skytiger/Projects/FinFocus`
- **Worktree**: `/home/skytiger/Projects/worktrees/0026-onboarding-refresh`
- **Protocol artifacts**: `/home/skytiger/Projects/worktrees/0026-onboarding-refresh/.obsidian-docs/protocols/0026-onboarding-refresh`
- **PR**: #26
- **Main branch**: `main`
- **Merge strategy**: `local`

## Workflow

> Работай из project root. Не переходи в worktree.

### Перед каждым шагом
1. Проверь: `pwd` и `git branch --show-current`
2. Сообщи пользователю какой шаг начинаешь

### После каждого шага
1. Запись в `review-log.md` (3-6 буллетов)
2. Коммит в feature-ветку: `chore(review): step X-m for 0026-onboarding-refresh`
3. Проверь окружение снова

---

## Steps

### 1-m. CI/CD
```bash
gh pr checks 26
```
Если failure — стоп, сообщи пользователю.

### 2-m. Локальная верификация
Из project root:
- lint (black --check, flake8), pytest для кода в worktree
- Проблемы → исправления в ветке фичи с тегом `[protocol-0026/2-m-fix]`

### 2.5-m. Security audit
```bash
bandit -r app/ -q && pip-audit
```

### 3-m. Code Review
1. Сверь `plan.md` и `log.md` с фактом
2. `git diff origin/main...0026-onboarding-refresh`
3. Проверь соответствие стандартам
4. Замечания → обсуди с пользователем

### 3.5-m. Fidelity-гейт спека↔итог (advisory)
Ad-hoc протокол из аудита, спеки эпика нет → пропустить с пометкой
в review-log.md (эталон — сам отчёт аудита, сверен в 3-m).

### 4-m. Knowledge Bank
KB обновлён внутри протокола (шаг 03: features.md, ui-components.md).
Проверить достаточность, при необходимости дообновить + коммит.

### 4.5-m. Документация
Task(doc-manager): ТОЛЬКО глобальные файлы (ROADMAP.md,
feature_progress.md; CLAUDE.md — не требуется, формулы/термины не менялись).
Статусы merge-зависимых записей — «на ревью».

### 4.7-m. Плановая сверка KB
Протокол НЕ закрывает шаг эпика (пункт UX-аудита, не чекбокс эпика) —
/kb-audit не предлагается как обязательный.

### 5-m. Merge (local, GitHub)
> Требуется явное разрешение пользователя + зона поражения

```bash
git checkout main && git pull origin main
git merge --no-ff 0026-onboarding-refresh
git push origin main
```

### 6. Cleanup
> Сообщи пользователю: `/protocol-cleanup 0026`
