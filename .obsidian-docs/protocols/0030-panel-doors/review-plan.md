# Review and Merge Plan: 0030-panel-doors

## Paths

- **Project root**: `/home/skytiger/Projects/FinFocus`
- **Worktree**: `/home/skytiger/Projects/worktrees/0030-panel-doors`
- **Protocol artifacts**: `/home/skytiger/Projects/worktrees/0030-panel-doors/.obsidian-docs/protocols/0030-panel-doors`
- **PR**: #30
- **Main branch**: `main`
- **Merge strategy**: `local`

## Workflow

> Работай из project root. Не переходи в worktree.

### Перед каждым шагом
1. Проверь: `pwd` и `git branch --show-current`
2. Сообщи пользователю какой шаг начинаешь

### После каждого шага
1. Запись в `review-log.md` (3-6 буллетов)
2. Коммит в feature-ветку: `chore(review): step X-m for 0030`
3. Проверь окружение снова

---

## Steps

### 1-m. CI/CD
```bash
gh pr checks 30
```
Если failure — стоп, сообщи пользователю.

### 2-m. Локальная верификация
Из project root:
- typecheck, lint, build, test для кода в worktree
- Проблемы → исправления в ветке фичи с тегом `[protocol-0030/2-m-fix]`

### 3-m. Code Review
1. Сверь `plan.md` и `log.md` с фактом
2. `git diff origin/main...0030-panel-doors`
3. Проверь соответствие стандартам
4. Замечания → обсуди с пользователем

### 3.5-m. Fidelity-гейт спека↔итог (advisory)
1. Спека эпика: `.obsidian-docs/design/epic-11-panel-batch-2/spec.md`
2. Task(spec-fidelity-validator): в промпт ТОЛЬКО путь к spec.md,
   project root/worktree, `main` и `0030-panel-doors`.
   НЕ передавай plan.md/log.md/выводы шага 3-m.
3. Полный отчёт → `fidelity-report.md`; человеку — вердикты
   НЕ ПОКРЫТО / СДЕЛАНО ИНАЧЕ. Advisory: мерж не блокирует.
4. Признано дефектом → fix с тегом `[protocol-0030/3.5-m-fix]`;
   принято как есть → фиксация в `review-log.md`.

### 4-m. Knowledge Bank
`/kb-update` по plan.md + log.md протокола. Протокол закрывает шаг
эпика (кусок 2 Epic-11 в ROADMAP) → дополнительно обновить «состояние
проекта» в `knowledge-bank/README.md` (если ведётся).
Коммит: `docs(knowledge-bank): update after 0030 [protocol-0030/4-m]`

### 4.5-m. Документация
Task(doc-manager): ТОЛЬКО глобальные файлы (CLAUDE.md,
.obsidian-docs/ROADMAP.md, feature_progress.md). Статусы
merge-зависимых записей — «на ревью».
Коммит: `docs: update after 0030 [protocol-0030/4.5-m]`

### 4.7-m. Плановая сверка KB
Протокол закрывает шаг эпика → предложить пользователю `/kb-audit`
(не запускать самому).

### 5-m. Merge (local, GitHub)
> Требуется явное разрешение пользователя + гейт зоны поражения

```bash
git checkout main
git pull origin main
git merge --no-ff 0030-panel-doors
git push origin main
```

### 6. Cleanup
После merge: `/protocol-cleanup 0030`
