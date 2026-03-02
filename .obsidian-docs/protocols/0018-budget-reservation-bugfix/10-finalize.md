# Шаг 10: Финализация

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
   git add . && git commit -m "chore: final QA fixes [protocol-0018/10]"
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
   git add .protocols/0018-budget-reservation-bugfix/ && git commit -m "docs(protocol): finalize 0018-budget-reservation-bugfix [protocol-0018/10]"
   git push
   ```

## Отчёт

```
(Протокол 0018-budget-reservation-bugfix — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/PycharmProjects/worktrees/0018-budget-reservation-bugfix
**Статус**: Completed. Ожидается /protocol-review-merge
```
