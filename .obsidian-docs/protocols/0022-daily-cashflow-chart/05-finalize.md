# Шаг 5: Финализация

## Briefing

- **Цель:** Полная верификация кода, перевод PR в Ready
- **Ключевые файлы:** Все изменённые в рамках протокола

## Sub-tasks

1. **Полная верификация:**
   ```bash
   black . && flake8 . && pytest
   ```
   Исправлять до полного прохождения.
   Ожидаемый результат: pytest >= 508 тестов (492 + 16 новых).

2. **Коммит правок** (если были):
   ```bash
   git add . && git commit -m "chore: final QA fixes [protocol-0022/05]"
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
   git add .protocols/0022-daily-cashflow-chart/ && git commit -m "docs(protocol): finalize 0022-daily-cashflow-chart [protocol-0022/05]"
   git push
   ```
