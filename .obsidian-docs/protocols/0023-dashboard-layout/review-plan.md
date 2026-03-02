# Review and Merge Plan: 0023-dashboard-layout

## Paths

- **Project root**: `/home/skytiger/PycharmProjects/FinFocus`
- **Worktree**: `/home/skytiger/PycharmProjects/worktrees/0023-dashboard-layout`
- **Protocol artifacts**: `.protocols/0023-dashboard-layout/`
- **PR**: #23

## Workflow

> Работай из project root. Не переходи в worktree.

### Перед каждым шагом
1. Проверь: `pwd` и `git branch --show-current`
2. Сообщи пользователю какой шаг начинаешь

### После каждого шага
1. Запись в `review-log.md` (3-6 буллетов)
2. Коммит в main: `chore(review): step X-m for 0023-dashboard-layout`
3. Проверь окружение снова

---

## Steps

### 1-m. CI/CD
```bash
gh pr checks 23
```
Если failure — стоп, сообщи пользователю.

### 2-m. Локальная верификация
Из project root:
- typecheck, lint, build, test для кода в worktree
- Проблемы → исправления в ветке фичи с тегом `[protocol-0023/2-m-fix]`

### 2.5-m. Security
```bash
bandit -r app/ -q && pip-audit && safety check
```

### 3-m. Code Review
1. Сверь `plan.md` и `log.md` с фактом
2. `git diff origin/main...0023-dashboard-layout`
3. Проверь соответствие стандартам
4. Замечания → обсуди с пользователем

### 4-m. Merge
> Требуется явное разрешение пользователя

```bash
git checkout main
git pull origin main
git merge --no-ff 0023-dashboard-layout
git push origin main
```

Конфликты → стоп, согласуй с пользователем.

### 5-m. Knowledge Bank
```bash
/kb-update .protocols/0023-dashboard-layout/plan.md .protocols/0023-dashboard-layout/log.md
```
Затем:
```bash
git add .knowledge-bank/ && git commit -m "docs(knowledge-bank): update after 0023-dashboard-layout [protocol-0023/5-m]"
git push origin main
```

### 5.5-m. Documentation Update
Обновить ROADMAP.md, feature_progress.md по plan.md и log.md.

### 6-m. Cleanup
```bash
git push origin --delete 0023-dashboard-layout
git branch -d 0023-dashboard-layout
git worktree remove ../worktrees/0023-dashboard-layout
```

Сообщи о завершении.
