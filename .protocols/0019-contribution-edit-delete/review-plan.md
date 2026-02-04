# Review and Merge Plan: 0019-contribution-edit-delete

## Paths

- **Project root**: `/home/skytiger/PycharmProjects/FinFocus`
- **Worktree**: `/home/skytiger/PycharmProjects/worktrees/0019-contribution-edit-delete`
- **Protocol artifacts**: `.protocols/0019-contribution-edit-delete/`
- **PR**: #19

## Workflow

> Работай из project root. Не переходи в worktree.

### Перед каждым шагом
1. Проверь: `pwd` и `git branch --show-current`
2. Сообщи пользователю какой шаг начинаешь

### После каждого шага
1. Запись в `review-log.md` (3-6 буллетов)
2. Коммит в main: `chore(review): step X-m for 0019 [protocol-0019/X-m]`
3. Проверь окружение снова

---

## Steps

### 1-m. CI/CD
```bash
gh pr checks 19
```
Если failure — стоп, сообщи пользователю.

### 2-m. Локальная верификация
Из project root:
- lint, test для кода в worktree
- Проблемы → исправления в ветке фичи с тегом `[protocol-0019/2-m-fix]`

### 3-m. Code Review
1. Сверь `plan.md` и `log.md` с фактом
2. `git diff origin/main...0019-contribution-edit-delete`
3. Проверь соответствие стандартам
4. Замечания → обсуди с пользователем

### 4-m. Merge
> Требуется явное разрешение пользователя

```bash
git checkout main
git pull origin main
git merge --no-ff 0019-contribution-edit-delete
git push origin main
```

### 5-m. Memory Bank
```bash
/mb-update
```

### 6-m. Cleanup
```bash
git push origin --delete 0019-contribution-edit-delete
git branch -d 0019-contribution-edit-delete
git worktree remove ../worktrees/0019-contribution-edit-delete
```
