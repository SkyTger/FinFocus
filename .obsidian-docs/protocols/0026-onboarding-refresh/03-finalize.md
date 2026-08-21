# Шаг 3: Финализация

## Briefing

- **Цель:** Полная верификация кода, перевод PR в Ready
- **Ключевые файлы:** Все изменённые в рамках протокола

## Sub-tasks

1. **Полная верификация** (венв живёт в PROJECT_ROOT):
   ```bash
   /home/skytiger/Projects/FinFocus/.venv/bin/black app/ tests/ \
     && flake8 app/ \
     && /home/skytiger/Projects/FinFocus/.venv/bin/pytest
   ```
   Исправлять до полного прохождения.
   Известный фон: 6 предсуществующих E501 в main — НЕ чинить в этом
   протоколе (не наш scope), новых E501 не добавлять.

2. **Обновить документацию** (в worktree, поедет с веткой):
   - `knowledge-bank/patterns/callbacks.md` — дашборд в списке подписчиков
     `profile-updated`
   - `knowledge-bank/modules/ui-components.md` — упомянуть новые
     Input'ы/greeting callback в секции Dashboard Component

3. **Коммит правок** (если были):
   ```bash
   git add . && git commit -m "chore: final QA fixes [protocol-0026/03]"
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
   git add .obsidian-docs/protocols/0026-onboarding-refresh/ && git commit -m "docs(protocol): finalize 0026-onboarding-refresh [protocol-0026/03]"
   git push
   ```

## Отчёт

```
(Протокол 0026 — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/Projects/worktrees/0026-onboarding-refresh
**Статус**: Completed. Ожидается /protocol-review-merge
```
