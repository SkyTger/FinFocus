# Review and Merge Plan: 0022-daily-cashflow-chart

## Paths

- **Project root**: `/home/skytiger/PycharmProjects/FinFocus`
- **Worktree**: `/home/skytiger/PycharmProjects/worktrees/0022-daily-cashflow-chart`
- **Protocol artifacts**: `.protocols/0022-daily-cashflow-chart/`
- **PR**: #22

## Workflow

> Работай из project root. Не переходи в worktree.

### Перед каждым шагом
1. Проверь: `pwd` и `git branch --show-current`
2. Сообщи пользователю какой шаг начинаешь

### После каждого шага
1. Запись в `review-log.md` (3-6 буллетов)
2. Коммит в main: `chore(review): step X-m for 0022-daily-cashflow-chart`
3. Проверь окружение снова

---

## Steps

### 1-m. CI/CD
```bash
gh pr checks 22
```
Если failure — стоп, сообщи пользователю.

### 2-m. Локальная верификация
Из project root:
- typecheck, lint, build, test для кода в worktree
- Проблемы → исправления в ветке фичи с тегом `[protocol-0022/2-m-fix]`

### 2.5-m. Security
```bash
bandit -r app/ -q && pip-audit
```

### 3-m. Code Review
1. Сверь `plan.md` и `log.md` с фактом
2. `git diff origin/main...0022-daily-cashflow-chart`
3. Проверь соответствие стандартам
4. Замечания → обсуди с пользователем

### 4-m. Merge
> Требуется явное разрешение пользователя

```bash
git checkout main
git pull origin main
git merge --no-ff 0022-daily-cashflow-chart
git push origin main
```

Конфликты → стоп, согласуй с пользователем.

### 5-m. Knowledge Bank
```bash
/kb-update .protocols/0022-daily-cashflow-chart/plan.md .protocols/0022-daily-cashflow-chart/log.md
```
Затем:
```bash
git add .knowledge-bank/ && git commit -m "docs(knowledge-bank): update after 0022-daily-cashflow-chart [protocol-0022/5-m]"
git push origin main
```

### 5.5-m. Documentation
Update ROADMAP.md, feature_progress.md, CLAUDE.md (if needed).

### 6-m. Cleanup
```bash
git push origin --delete 0022-daily-cashflow-chart
git branch -d 0022-daily-cashflow-chart
git worktree remove /home/skytiger/PycharmProjects/worktrees/0022-daily-cashflow-chart
```

Сообщи о завершении.
