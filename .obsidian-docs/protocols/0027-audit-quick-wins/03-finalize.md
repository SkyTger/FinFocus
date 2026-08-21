# Шаг 3: Финализация

## Briefing

- **Цель:** Полная верификация кода, перевод PR в Ready
- **Ключевые файлы:** Все изменённые в рамках протокола

## Sub-tasks

1. **Полная верификация** (black ТОЛЬКО из venv PROJECT_ROOT — 23.11.0;
   системный black 26.x форматирует иначе):
   ```bash
   /home/skytiger/Projects/FinFocus/.venv/bin/black app/ tests/ \
     && flake8 app/ tests/ \
     && /home/skytiger/Projects/FinFocus/.venv/bin/pytest
   ```
   Известный фон: предсуществующие E501 в main НЕ чинить, новых не добавлять.
   Попутное переформатирование чужих файлов black'ом — откатывать
   (вне scope, как в 0026).

2. **Обновить документацию** (в worktree): если менялись публичные
   контракты сервисов — соответствующий modules/*.md в knowledge-bank
   (здесь ожидаемо: только поведение логирования — обновить services.md,
   секция PurchaseRecommendationService, критичные детали fail-open).

3. **Коммит правок** (если были):
   ```bash
   git add . && git commit -m "chore: final QA fixes [protocol-0027/03]"
   ```

4. **PR в Ready:** `gh pr ready`

5. **context.md**: Status: Completed, Next Action: Ожидается /protocol-review-merge

6. **Финальный коммит:**
   ```bash
   git add .obsidian-docs/protocols/0027-audit-quick-wins/ && git commit -m "docs(protocol): finalize 0027-audit-quick-wins [protocol-0027/03]"
   git push
   ```

## Отчёт

```
(Протокол 0027 — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/Projects/worktrees/0027-audit-quick-wins
**Статус**: Completed. Ожидается /protocol-review-merge
```
