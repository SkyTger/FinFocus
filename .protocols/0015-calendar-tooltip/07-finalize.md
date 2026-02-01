# Шаг 7: Финализация

## Briefing

- **Цель:** Полная верификация кода, перевод PR в Ready
- **Ключевые файлы:** Все изменённые в рамках протокола

## Sub-tasks

1. **Полная верификация:**
   ```bash
   black . && flake8 . && pytest
   ```
   Исправлять до полного прохождения.

2. **Коммит правок** (если были):
   ```bash
   git add . && git commit -m "chore: final QA fixes [protocol-0015/07]"
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
   git add .protocols/0015-calendar-tooltip/ && git commit -m "docs(protocol): finalize 0015-calendar-tooltip [protocol-0015/07]"
   git push
   ```

## Отчёт

```
(Протокол 0015-calendar-tooltip — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/PycharmProjects/worktrees/0015-calendar-tooltip
**Статус**: Completed. Ожидается /protocol-review-merge
```
