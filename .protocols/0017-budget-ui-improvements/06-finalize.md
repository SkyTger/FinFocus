# Шаг 6: Финализация

## Briefing

- **Цель:** Полная верификация кода, перевод PR в Ready
- **Ключевые файлы:** Все изменённые в рамках протокола

## Sub-tasks

1. **Полная верификация:**
   ```bash
   black app/ tests/
   flake8 app/ --select=E9,F63,F7,F82
   pytest tests/ -v --tb=short
   ```
   Исправлять до полного прохождения.

2. **Коммит правок** (если были):
   ```bash
   git add . && git commit -m "chore: final QA fixes [protocol-0017/06]"
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
   git add .protocols/0017-budget-ui-improvements/ && git commit -m "docs(protocol): finalize 0017-budget-ui-improvements [protocol-0017/06]"
   git push
   ```

## Критерии приёмки

- [ ] RESERVE_DESCRIPTION = "Резервирование бюджета"
- [ ] Верхняя карточка "Бюджет накоплений (месяц)" удалена
- [ ] "Сводка по целям" показывает "X / Y ₽" (внесено / бюджет)
- [ ] adjust_reserve_for_contribution() работает:
  - [ ] Взнос до резерва → Exception с уменьшенной суммой
  - [ ] Взнос после резерва → нет Exception
  - [ ] Взносы >= бюджета → Exception с 0 и "(внесено досрочно)"
- [ ] Все тесты проходят (396+)
- [ ] Black + Flake8 OK

## Отчёт

```
(Протокол 0017-budget-ui-improvements — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/PycharmProjects/worktrees/0017-budget-ui-improvements
**Статус**: Completed. Ожидается /protocol-review-merge
```
