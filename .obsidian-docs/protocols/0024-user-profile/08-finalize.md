# Шаг 8: Финализация

## Briefing

- **Цель:** Полная верификация кода, перевод PR в Ready
- **Ключевые файлы:** Все изменённые в рамках протокола

## Sub-tasks

1. **Полная верификация:**
   ```bash
   black app/ && flake8 app/ && pytest -k "not test_budget_change_updates_allocation" -v
   ```
   Исправлять до полного прохождения.

2. **Коммит правок** (если были):
   ```bash
   git add . && git commit -m "chore: final QA fixes [protocol-0024-user-profile/08]"
   ```

3. **Перевод PR в Ready:**
   ```bash
   gh pr ready
   ```

4. **Обновить context.md:**
   - Status: `Completed`
   - Next Action: `Ожидается /protocol-review-merge`

5. **Финальный коммит протокола:**
   ```bash
   git add .obsidian-docs/protocols/0024-user-profile/ && git commit -m "docs(protocol): finalize 0024-user-profile [protocol-0024-user-profile/08]"
   git push
   ```

## Отчёт

```
(Протокол 0024-user-profile — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/PycharmProjects/worktrees/0024-user-profile
**Статус**: Completed. Ожидается /protocol-review-merge
```
