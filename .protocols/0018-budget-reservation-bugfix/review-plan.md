# Review and Merge Plan: 0018-budget-reservation-bugfix

## Paths

- **Project root**: `/home/skytiger/PycharmProjects/FinFocus`
- **Worktree**: `/home/skytiger/PycharmProjects/worktrees/0018-budget-reservation-bugfix`
- **Protocol artifacts**: `.protocols/0018-budget-reservation-bugfix/`
- **PR**: #18

## Workflow

> Работай из project root. Не переходи в worktree.

### Перед каждым шагом
1. Проверь: `pwd` и `git branch --show-current`
2. Сообщи пользователю какой шаг начинаешь

### После каждого шага
1. Запись в `review-log.md` (3-6 буллетов)
2. Коммит в main: `chore(review): step X-m for 0018-budget-reservation-bugfix`
3. Проверь окружение снова

---

## Steps

### 1-m. CI/CD
```bash
gh pr checks 18
```
Если failure — стоп, сообщи пользователю.

### 2-m. Локальная верификация
Из project root:
- typecheck, lint, build, test для кода в worktree
- Проблемы → исправления в ветке фичи с тегом `[protocol-0018/2-m-fix]`

### 3-m. Code Review
1. Сверь `plan.md` и `log.md` с фактом
2. `git diff origin/main...0018-budget-reservation-bugfix`
3. Проверь соответствие стандартам
4. Замечания → обсуди с пользователем

### 4-m. Merge
> Требуется явное разрешение пользователя

```bash
git checkout main
git pull origin main
git merge --no-ff 0018-budget-reservation-bugfix
git push origin main
```

Конфликты → стоп, согласуй с пользователем.

### 5-m. Memory Bank
```bash
/mb-update .protocols/0018-budget-reservation-bugfix/plan.md .protocols/0018-budget-reservation-bugfix/log.md
```
Затем:
```bash
git add .memory-bank/ && git commit -m "docs(memory-bank): update after 0018-budget-reservation-bugfix [protocol-0018/5-m]"
git push origin main
```

### 6-m. Cleanup
```bash
git push origin --delete 0018-budget-reservation-bugfix
git branch -d 0018-budget-reservation-bugfix
git worktree remove ../worktrees/0018-budget-reservation-bugfix
```

Сообщи о завершении.
