# Review and Merge Plan: 0031-nav-rail

## Paths

- **Project root**: `/home/skytiger/Projects/FinFocus`
- **Worktree**: `/home/skytiger/Projects/worktrees/0031-nav-rail`
- **Protocol artifacts**: `.obsidian-docs/protocols/0031-nav-rail`
- **PR**: #31
- **Main branch**: `main`
- **Merge strategy**: `local`

## Workflow

> Работай из project root. Не переходи в worktree.

### Перед каждым шагом
1. Проверь: `pwd` и `git branch --show-current`
2. Сообщи пользователю какой шаг начинаешь

### После каждого шага
1. Запись в `review-log.md` (3-6 буллетов)
2. Коммит в feature-ветку: `chore(review): step X-m for 0031-nav-rail`
3. Проверь окружение снова

---

## Steps

### 1-m. CI/CD
```bash
gh pr checks 31
```
Если failure — стоп, сообщи пользователю.

### 2-m. Локальная верификация
Из project root:
- typecheck, lint, build, test для кода в worktree
- Проблемы → исправления в ветке фичи с тегом `[protocol-0031-nav-rail/2-m-fix]`

### 3-m. Code Review
1. Сверь `plan.md` и `log.md` с фактом
2. `git diff origin/main...0031-nav-rail`
3. Проверь соответствие стандартам
4. Замечания → обсуди с пользователем

### 3.5-m. Fidelity-гейт спека↔итог (advisory)
1. Найди спеку эпика: `context.md` протокола → батч дизайна, иначе
   `.obsidian-docs/design/<batch>/spec.md`. Спеки нет (ad-hoc) →
   пропусти шаг с пометкой в `review-log.md`.
2. Task(spec-fidelity-validator): в промпт ТОЛЬКО путь к spec.md,
   project root/worktree, `main` и `0031-nav-rail`.
   НЕ передавай plan.md/log.md/выводы шага 3-m — верификатор смотрит
   на код чистыми глазами.
3. Полный отчёт → `.obsidian-docs/protocols/0031-nav-rail/fidelity-report.md`; человеку —
   вердикты НЕ ПОКРЫТО / СДЕЛАНО ИНАЧЕ. Advisory: мерж не блокирует,
   судит человек.
4. Признано дефектом → fix в ветке фичи с тегом
   `[protocol-0031-nav-rail/3.5-m-fix]`; принято как есть →
   фиксация в `review-log.md`.

### 4-m. Knowledge Bank
```bash
/kb-update .obsidian-docs/protocols/0031-nav-rail/plan.md .obsidian-docs/protocols/0031-nav-rail/log.md
```
**Если протокол закрывает шаг эпика** (чекбокс шага в ROADMAP) —
дополнительно обнови «состояние проекта» в `knowledge-bank/README.md`
(реализованное, диапазон ADR): обзорные доки не привязаны к батчам и
стареют молча.
Затем:
```bash
git add .obsidian-docs/knowledge-bank/ && git commit -m "docs(knowledge-bank): update after 0031-nav-rail [protocol-0031-nav-rail/4-m]"
git push origin 0031-nav-rail
```

### 4.5-m. Документация
Task(doc-manager): обнови ТОЛЬКО глобальные файлы (CLAUDE.md, .obsidian-docs/ROADMAP.md, .obsidian-docs/feature_progress.md) по plan.md, log.md. Эпик-документацию НЕ трогай. Статусы merge-зависимых записей пиши как «на ревью» — в «смержено» их переведёт `/protocol-cleanup`.
```bash
git add -A && git commit -m "docs: update after 0031-nav-rail [protocol-0031-nav-rail/4.5-m]"
git push origin 0031-nav-rail
```

### 4.7-m. Плановая сверка KB (только при закрытии шага эпика)
Если протокол закрывает шаг эпика — предложи пользователю `/kb-audit`
(не запускай сам): плановая точка сверки KB↔код.

### 5-m. Merge

#### Если `local` = `local` (GitHub):
> Требуется явное разрешение пользователя

```bash
git checkout main
git pull origin main
git merge --no-ff 0031-nav-rail
git push origin main
```

Конфликты → стоп, согласуй с пользователем.

#### Если `local` = `mr` (GitLab):
1. Убедись что все коммиты запушены: `git push origin 0031-nav-rail`
2. Сообщи пользователю: "Ветка готова. Проверь, протестируй и выполни merge через MR в GitLab."
3. **СТОП** — ждём подтверждения.

### 6. Cleanup

> Cleanup вынесен в отдельный скилл. Сообщи пользователю:
> `Для завершения выполни /protocol-cleanup 0031-nav-rail`
