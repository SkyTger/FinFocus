# Review and Merge Plan: 0013-safety-cushion

## Paths

- **Project root**: `/home/skytiger/PycharmProjects/FinFocus`
- **Worktree**: `/home/skytiger/PycharmProjects/worktrees/0013-safety-cushion`
- **Protocol artifacts**: `.protocols/0013-safety-cushion/`
- **PR**: #13

## Workflow

> Работай из project root. Не переходи в worktree.

### Перед каждым шагом
1. Проверь: `pwd` и `git branch --show-current`
2. Сообщи пользователю какой шаг начинаешь

### После каждого шага
1. Запись в `review-log.md` (3-6 буллетов)
2. Коммит в main: `chore(review): step X-m for 0013-safety-cushion`
3. Проверь окружение снова

---

## Steps

### 1-m. CI/CD
```bash
gh pr checks 13
```
Если failure — стоп, сообщи пользователю.

### 2-m. Локальная верификация
Из project root:
- typecheck, lint, build, test для кода в worktree
- Проблемы → исправления в ветке фичи с тегом `[protocol-0013-safety-cushion/2-m-fix]`

### 3-m. Code Review
1. Сверь `plan.md` и `log.md` с фактом
2. `git diff origin/main...0013-safety-cushion`
3. Проверь соответствие стандартам
4. Замечания → обсуди с пользователем

### 4-m. Merge
> Требуется явное разрешение пользователя

```bash
git checkout main
git pull origin main
git merge --no-ff 0013-safety-cushion
git push origin main
```

Конфликты → стоп, согласуй с пользователем.

### 5-m. Memory Bank
```bash
/mb-update .protocols/0013-safety-cushion/plan.md .protocols/0013-safety-cushion/log.md
```
Затем:
```bash
git add .memory-bank/ && git commit -m "docs(memory-bank): update after 0013-safety-cushion [protocol-0013-safety-cushion/5-m]"
git push origin main
```

### 6-m. Cleanup
```bash
git push origin --delete 0013-safety-cushion
git branch -d 0013-safety-cushion
git worktree remove /home/skytiger/PycharmProjects/worktrees/0013-safety-cushion
```

Сообщи о завершении.