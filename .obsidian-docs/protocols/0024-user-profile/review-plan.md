# Review and Merge Plan: 0024-user-profile

## Paths

- **Project root**: `/home/skytiger/PycharmProjects/FinFocus`
- **Worktree**: `/home/skytiger/PycharmProjects/worktrees/0024-user-profile`
- **Protocol artifacts**: `.obsidian-docs/protocols/0024-user-profile/`
- **PR**: #24
- **Main branch**: `main`
- **Merge strategy**: `local`

## Workflow

> Работай из project root. Не переходи в worktree.

### Перед каждым шагом
1. Проверь: `pwd` и `git branch --show-current`
2. Сообщи пользователю какой шаг начинаешь

### После каждого шага
1. Запись в `review-log.md` (3-6 буллетов)
2. Коммит в feature-ветку: `chore(review): step X-m for 0024-user-profile`
3. Проверь окружение снова

---

## Steps

### 1-m. CI/CD
```bash
gh pr checks 24
```
Если failure — стоп, сообщи пользователю.

### 2-m. Локальная верификация
Из project root:
- typecheck, lint, build, test для кода в worktree
- Проблемы → исправления в ветке фичи с тегом `[protocol-0024-user-profile/2-m-fix]`

### 3-m. Code Review
1. Сверь `plan.md` и `log.md` с фактом
2. `git diff origin/main...0024-user-profile`
3. Проверь соответствие стандартам
4. Замечания → обсуди с пользователем

### 4-m. Knowledge Bank
```bash
/kb-update .obsidian-docs/protocols/0024-user-profile/plan.md .obsidian-docs/protocols/0024-user-profile/log.md
```

### 4.5-m. Документация
Task(doc-manager): обнови ТОЛЬКО глобальные файлы (CLAUDE.md, .obsidian-docs/ROADMAP.md, .obsidian-docs/feature_progress.md) по plan.md, log.md. Эпик-документацию НЕ трогай.

### 5-m. Merge
> Требуется явное разрешение пользователя

```bash
git checkout main
git pull origin main
git merge --no-ff 0024-user-profile
git push origin main
```
