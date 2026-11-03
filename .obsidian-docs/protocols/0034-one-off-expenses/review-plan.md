# Review and Merge Plan: 0034-one-off-expenses

## Paths

- **Project root**: `/home/skytiger/Projects/FinFocus`
- **Worktree**: `/home/skytiger/Projects/worktrees/0034-one-off-expenses`
- **Protocol artifacts**: `.obsidian-docs/protocols/0034-one-off-expenses`
- **PR**: #34
- **Main branch**: `main`
- **Merge strategy**: `local`

## Workflow

> **Шаги 1-m…4.7-m — в папке протокола `/home/skytiger/Projects/worktrees/0034-one-off-expenses`** (ветка
> `0034-one-off-expenses`): тесты, правки, документация, коммиты. **Мерж (5-m) — из
> `/home/skytiger/Projects/FinFocus`** (ветка `main`). Git не открывает одну
> ветку в двух папках: правка или коммит из `/home/skytiger/Projects/FinFocus` уйдут в
> `main` в обход ревью, тесты оттуда проверят не тот код.

### Перед каждым шагом
1. Проверь: `pwd` и `git branch --show-current` — шаги 1-m…4.7-m:
   `/home/skytiger/Projects/worktrees/0034-one-off-expenses` и `0034-one-off-expenses`
2. Сообщи пользователю какой шаг начинаешь

### После каждого шага
1. Запись в `review-log.md` (3-6 буллетов)
2. Коммит в feature-ветку: `chore(review): step X-m for 0034-one-off-expenses`
   (до шага 4-m; записи 4-m и 4.7-m входят в коммит 4-m — после него в
   ветку ничего не коммитится, итог мержа — только в отчёте пользователю)
3. Проверь окружение снова

---

## Steps

### 1-m. CI/CD
PR ведётся (`PR_FLOW=yes`):
```bash
gh pr checks 34
```
Если failure — стоп, сообщи пользователю. PR не ведётся → статус
пайплайна ветки в GitLab, если доступен; иначе пропуск с пометкой в
`review-log.md`.

### 2-m. Локальная верификация
В `/home/skytiger/Projects/worktrees/0034-one-off-expenses`:
- typecheck, lint, build, test
- Проблемы → исправления в ветке фичи с тегом `[protocol-0034-one-off-expenses/2-m-fix]`

### 3-m. Code Review
1. Сверь `plan.md` и `log.md` с фактом
2. `git diff origin/main...0034-one-off-expenses`
3. Проверь соответствие стандартам
4. Замечания → обсуди с пользователем

### 3.5-m. Fidelity-гейт спека↔итог (advisory)
1. Найди спеку эпика: `context.md` протокола → батч дизайна, иначе
   `.obsidian-docs/design/<batch>/spec.md`. Спеки нет (ad-hoc) →
   пропусти шаг с пометкой в `review-log.md`.
2. Task(spec-fidelity-validator): в промпт ТОЛЬКО путь к spec.md,
   project root/worktree, `main` и `0034-one-off-expenses`.
   НЕ передавай plan.md/log.md/выводы шага 3-m — верификатор смотрит
   на код чистыми глазами.
3. Полный отчёт → `.obsidian-docs/protocols/0034-one-off-expenses/fidelity-report.md`; человеку —
   вердикты НЕ ПОКРЫТО / СДЕЛАНО ИНАЧЕ. Advisory: мерж не блокирует,
   судит человек.
4. Признано дефектом → fix в ветке фичи с тегом
   `[protocol-0034-one-off-expenses/3.5-m-fix]`; принято как есть →
   фиксация в `review-log.md`.

### 4-m. Документация (история + KB, один коммит)
В `/home/skytiger/Projects/worktrees/0034-one-off-expenses`. Порядок и правила — `/protocol-review-merge`,
«Шаг 4-m: Документация». Кратко:
1. `~/.claude/scripts/doc-paths.sh` → пути; `AMBIGUOUS_…` → стоп, вопрос.
2. Task(doc-manager) UPDATE: пути (+ путь архива с разрешением создать),
   `plan.md`, `log.md`, ветка `0034-one-off-expenses` и последний коммит работы,
   главная ветка `main` (интеграционная — скажи, в какую ветку
   сервера она переносится). Статус сразу «сделано (дата, ветка,
   коммит)» — запись едет в `main` ровно с мержем. Без коммита.
3. `/kb-update` — `plan.md`, `log.md` + «кандидаты в ADR» и «для
   /kb-update» из отчёта doc-manager (+ «закрыт шаг эпика», если так).
   Невнесённые решения от keeper → показать пользователю, записать в review-log.
4. Шаг 4.7-m (ниже) — сейчас, до коммита; его запись — в review-log. Один коммит: `review-*.md` всегда
   (даже если агентам править нечего) + найденные пути; затем `git status
   --porcelain` пуст (иначе — показать пользователю):
```bash
for f in <KB_DIR> <ROADMAP> <FEATURE_PROGRESS> <путь архива> <CLAUDE_MD> .obsidian-docs/protocols/0034-one-off-expenses/review-*.md; do [ -e "$f" ] && printf '%s\0' "$f"; done | xargs -0 git add --
git commit -m "docs: история и KB после 0034-one-off-expenses [protocol-0034-one-off-expenses/4-m]"
git push origin 0034-one-off-expenses
```
Последний коммит ветки перед мержем.

### 4.7-m. Плановая сверка KB (только при закрытии шага эпика; выполняется внутри 4-m, до его коммита)
Если протокол закрывает шаг эпика — предложи пользователю `/kb-audit`
(не запускай сам): плановая точка сверки KB↔код.

### 5-m. Merge

#### Если `local` = `local` (GitHub или интеграционная ветка):
> Требуется явное разрешение пользователя. Из `/home/skytiger/Projects/FinFocus`:
```bash
cd /home/skytiger/Projects/FinFocus
```

```bash
git checkout main
git pull origin main
git merge --no-ff 0034-one-off-expenses
git push origin main
```

Конфликты → стоп, согласуй с пользователем.

#### Если `local` = `mr` (GitLab, мерж в основную ветку сервера):
1. Убедись что все коммиты запушены: `git push origin 0034-one-off-expenses`
2. Сообщи пользователю: "Ветка готова. Проверь, протестируй и выполни merge через MR в GitLab."
3. **СТОП** — ждём подтверждения.

### 6. Cleanup

> Cleanup вынесен в отдельный скилл. Сообщи пользователю:
> `Для завершения выполни /protocol-cleanup 0034-one-off-expenses`
