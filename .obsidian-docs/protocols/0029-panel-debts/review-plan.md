# Review and Merge Plan: 0029-panel-debts

## Paths

- **Project root**: `/home/skytiger/Projects/FinFocus`
- **Worktree**: `/home/skytiger/Projects/worktrees/0029-panel-debts`
- **Protocol artifacts**: `/home/skytiger/Projects/worktrees/0029-panel-debts/.obsidian-docs/protocols/0029-panel-debts`
- **PR**: #29
- **Main branch**: `main`
- **Merge strategy**: `local`

## Workflow

> Работай из project root. Не переходи в worktree.

### Перед каждым шагом
1. Проверь: `pwd` и `git branch --show-current`
2. Сообщи пользователю какой шаг начинаешь

### После каждого шага
1. Запись в `review-log.md` (3-6 буллетов)
2. Коммит в feature-ветку: `chore(review): step X-m for 0029-panel-debts`
3. Проверь окружение снова

---

## Steps

### 1-m. CI/CD — `gh pr checks 29`
### 2-m. Локальная верификация (Python: black из .venv + flake8 + pytest; ruff/mypy в проекте не используются)
### 2.5-m. Security (bandit/pip-audit по доступности)
### 3-m. Code Review — plan.md/log.md vs `git diff origin/main...0029-panel-debts`
### 3.5-m. Fidelity-гейт: спека батча у протокола 0029 отсутствует (ad-hoc протокол по долгам ROADMAP) — эталон: записи ROADMAP «Известное ограничение куска 1» и «Долг куска 1» + докстринг снятого ограничения; проверка чистыми глазами субагентом
### 4-m. Knowledge Bank (/kb-update) + коммит
### 4.5-m. Документация (doc-manager: CLAUDE.md, ROADMAP.md, feature_progress.md; статусы — «на ревью»)
### 4.7-m. Не шаг эпика (долги, не чекбокс) — /kb-audit не предлагается
### 5-m. Merge (local, с явного разрешения, с зоной поражения)
### 6. Cleanup — отдельным скиллом
