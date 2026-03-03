# Шаг 3: Финализация

## Briefing

- **Цель:** Полная верификация кода, перевод PR в Ready
- **Ключевые файлы:** Все изменённые в рамках протокола

## Sub-tasks

1. **Полная верификация:**
   ```bash
   black app/ && flake8 app/ && pytest -k "not test_budget_change_updates_allocation"
   ```
   Исправлять до полного прохождения.

2. **Ручные проверки:**
   - `bash start.sh` — приложение запускается (если возможно)
   - `shellcheck start.sh` — без критичных предупреждений (если доступен)
   - Повторный запуск start.sh — зависимости не переустанавливаются
   - `pip install -r requirements-dev.txt` — dev зависимости устанавливаются

3. **Коммит правок** (если были):
   ```bash
   git add . && git commit -m "chore: final QA fixes [protocol-0025/03]"
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
   git add .obsidian-docs/protocols/0025-beta-delivery/ && git commit -m "docs(protocol): finalize 0025-beta-delivery [protocol-0025/03]"
   git push
   ```

## Отчёт

```
(Протокол 0025-beta-delivery — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/PycharmProjects/worktrees/0025-beta-delivery
**Статус**: Completed. Ожидается /protocol-review-merge
```
