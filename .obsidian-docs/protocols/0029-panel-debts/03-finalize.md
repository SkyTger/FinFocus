# Шаг 3: Финализация

## Briefing

- **Цель:** Полная верификация кода, перевод PR в Ready
- **Ключевые файлы:** Все изменённые в рамках протокола

## Sub-tasks

1. **Полная верификация:**
   ```bash
   /home/skytiger/Projects/FinFocus/.venv/bin/black app/ tests/ && /home/skytiger/Projects/FinFocus/.venv/bin/flake8 app/ && /home/skytiger/Projects/FinFocus/.venv/bin/pytest
   ```
   Исправлять до полного прохождения. Критерий flake8 — без НОВЫХ
   замечаний (6 pre-existing E501 известны, открытый вопрос №5 ROADMAP).

2. **Коммит правок** (если были):
   ```bash
   git add . && git commit -m "chore: final QA fixes [protocol-0029/3]"
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
   git add .obsidian-docs/protocols/0029-panel-debts/ && git commit -m "docs(protocol): finalize 0029-panel-debts [protocol-0029/3]"
   git push
   ```

## Отчёт

```
(Протокол 0029 — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/Projects/worktrees/0029-panel-debts
**Статус**: Completed. Ожидается /protocol-review-merge
```
