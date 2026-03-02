# Шаг 8: Финализация

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
   git add . && git commit -m "chore: final QA fixes [protocol-0012/08]"
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
   git add .protocols/0012-quick-add-chips/ && git commit -m "docs(protocol): finalize 0012-quick-add-chips [protocol-0012/08]"
   git push
   ```

6. **Обновить документацию** (если нужно):
   - `feature_progress.md` — добавить батч Quick-add chips
   - `ROADMAP.md` — отметить завершение задачи

## Отчёт

```
(Протокол 0012-quick-add-chips — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/PycharmProjects/worktrees/0012-quick-add-chips
**Статус**: Completed. Ожидается /protocol-review-merge
```
