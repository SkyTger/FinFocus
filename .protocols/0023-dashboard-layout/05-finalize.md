# Шаг 5: Финализация

## Briefing

- **Цель:** CSS стили, полная верификация кода, перевод PR в Ready
- **Ключевые файлы:** Все изменённые в рамках протокола

## Sub-tasks

1. **CSS стили** в custom.css:
   - `.empty-state` — text-align center, padding 40px, icon 2.5rem
   - `.dashboard-split-table` — row hover, consistent padding

2. **Полная верификация:**
   ```bash
   black app/ tests/ && flake8 app/ tests/ && pytest
   ```
   Исправлять до полного прохождения. Target: >= 520 tests.

3. **Коммит правок** (если были):
   ```bash
   git add . && git commit -m "chore: final QA fixes [protocol-0023/05]"
   ```

4. **Перевод PR в Ready:**
   ```bash
   gh pr ready
   ```

5. **Обновить context.md:**
   - Status: `Completed`
   - Next Action: `Ожидается /protocol-review-merge`

6. **Финальный коммит протокола:**
   ```bash
   git add .protocols/0023-dashboard-layout/ && git commit -m "docs(protocol): finalize 0023-dashboard-layout [protocol-0023/05]"
   git push
   ```

## Отчёт

```
(Протокол 0023-dashboard-layout — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/PycharmProjects/worktrees/0023-dashboard-layout
**Статус**: Completed. Ожидается /protocol-review-merge
```
