# Review and Merge Plan: 0027-audit-quick-wins

## Paths

- **Project root**: `/home/skytiger/Projects/FinFocus`
- **Worktree**: `/home/skytiger/Projects/worktrees/0027-audit-quick-wins`
- **Protocol artifacts**: `/home/skytiger/Projects/worktrees/0027-audit-quick-wins/.obsidian-docs/protocols/0027-audit-quick-wins`
- **PR**: #27
- **Main branch**: `main`
- **Merge strategy**: `local`

## Steps

### 1-m. CI/CD — `gh pr checks 27`
### 2-m. Локальная верификация — black (venv 23.11.0!), flake8, pytest
### 2.5-m. Security — bandit app/; pip-audit: requirements.txt не менялся,
findings ревью 0026 остаются в силе (открытый вопрос №8 ROADMAP)
### 3-m. Code review — субагент code-reviewer по diff origin/main...ветка
### 3.5-m. Fidelity-гейт — пропустить: ад-хок протокол из аудита, спеки нет
### 4-m. Knowledge Bank — обновлён в протоколе (services.md), проверить достаточность
### 4.5-m. Task(doc-manager) — ROADMAP (пп. 2-3 плана аудита → выполнено),
feature_progress (запись батча, статус «на ревью»)
### 4.7-m. Не закрывает шаг эпика — /kb-audit не обязателен
### 5-m. Merge (local) — с разрешения пользователя + зона поражения
### 6. Cleanup — /protocol-cleanup 0027
