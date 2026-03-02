# Review and Merge Plan: 0016-budget-calendar

## Paths

- **Project root**: `/home/skytiger/PycharmProjects/FinFocus`
- **Worktree**: `/home/skytiger/PycharmProjects/worktrees/0016-budget-calendar`
- **Protocol artifacts**: `.protocols/0016-budget-calendar/`
- **PR**: #16

## Workflow

> Работай из project root. Не переходи в worktree.

### Перед каждым шагом
1. Проверь: `pwd` и `git branch --show-current`
2. Сообщи пользователю какой шаг начинаешь

### После каждого шага
1. Запись в `review-log.md` (3-6 буллетов)
2. Коммит в main: `chore(review): step X-m for 0016-budget-calendar`
3. Проверь окружение снова

---

## Steps

### 1-m. CI/CD
```bash
gh pr checks 16
```
Если failure — стоп, сообщи пользователю.

### 2-m. Локальная верификация
Из project root:
- typecheck, lint, build, test для кода в worktree
- Проблемы → исправления в ветке фичи с тегом `[protocol-0016-budget-calendar/2-m-fix]`

### 3-m. Code Review
1. Сверь `plan.md` и `log.md` с фактом
2. `git diff origin/main...0016-budget-calendar`
3. Проверь соответствие стандартам
4. Замечания → обсуди с пользователем

### 4-m. Merge
> Требуется явное разрешение пользователя

```bash
git checkout main
git pull origin main
git merge --no-ff 0016-budget-calendar
git push origin main
```

Конфликты → стоп, согласуй с пользователем.

### 5-m. Memory Bank
```bash
/mb-update .protocols/0016-budget-calendar/plan.md .protocols/0016-budget-calendar/log.md
```
Затем:
```bash
git add .memory-bank/ && git commit -m "docs(memory-bank): update after 0016-budget-calendar [protocol-0016-budget-calendar/5-m]"
git push origin main
```

### 6-m. Cleanup
```bash
git push origin --delete 0016-budget-calendar
git branch -d 0016-budget-calendar
git worktree remove ../worktrees/0016-budget-calendar
```

Сообщи о завершении.
