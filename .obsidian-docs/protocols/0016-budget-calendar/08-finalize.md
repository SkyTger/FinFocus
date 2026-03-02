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

2. **Проверка критериев приёмки** из brief.md:
   - [ ] Пользователь может выбрать режим резервирования в модале бюджета
   - [ ] В режиме "Фиксированная дата" операция "Резерв на цели" появляется в календаре
   - [ ] В режиме "Из остатка" при взносе создается операция "Взнос: {цель}"
   - [ ] Карточка бюджета показывает корректный прогресс
   - [ ] Переключение режима сохраняет историю взносов
   - [ ] Операция "Резерв на цели" не редактируется вручную
   - [ ] Unit тесты покрывают все новые сервисы (>90% coverage)
   - [ ] Black + Flake8 без ошибок

3. **Коммит правок** (если были):
   ```bash
   git add . && git commit -m "chore: final QA fixes [protocol-0016/08]"
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
   git add .protocols/0016-budget-calendar/ && git commit -m "docs(protocol): finalize 0016-budget-calendar [protocol-0016/08]"
   git push
   ```

## Отчёт

```
(Протокол 0016-budget-calendar — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Критерии приёмки**: X/8 выполнено
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/PycharmProjects/worktrees/0016-budget-calendar
**Статус**: Completed. Ожидается /protocol-review-merge
```
