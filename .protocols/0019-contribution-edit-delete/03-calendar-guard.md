# Шаг 3: Calendar Guard #6

## Briefing

- **Цель:** Добавить Guard #6 в calendar tooltip для блокировки кликов на SAVINGS_CONTRIBUTION операции. Пользователи должны редактировать взносы только через Goals UI.
- **Ключевые файлы:**
  - `app/components/calendar.py` — open_edit_from_tooltip(), после Guard #5 (~строка 1030-1045)
- **Доп. информация:** Guard #5 уже блокирует SAVINGS_RESERVE. Guard #6 аналогичен по структуре.

## Sub-tasks

1. **Найти Guard #5 в `app/components/calendar.py`:**
   - Найти строку с `if txn_type == "savings_reserve":` в функции `open_edit_from_tooltip()`

2. **Добавить Guard #6 сразу ПОСЛЕ Guard #5:**
   ```python
   # Guard #6: SAVINGS_CONTRIBUTION — редактирование через Goals UI
   # Примечание: SAVINGS_CONTRIBUTION по дизайну не может быть recurring
   # (создается только реальная транзакция в режиме from_balance).
   # Этот guard добавлен для defensive programming на случай будущих изменений архитектуры.
   if txn_type == "savings_contribution":
       logger.debug("Tooltip: клик на SAVINGS_CONTRIBUTION ignored (use Goals UI)")
       raise PreventUpdate
   ```

3. **Проверить что PreventUpdate импортирован** (должен быть, т.к. Guard #5 уже использует его)

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка: `python -m py_compile app/components/calendar.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 4, Next Action: Шаг 4
5. Коммит: `git add . && git commit -m "fix(calendar): block SAVINGS_CONTRIBUTION edit in tooltip [protocol-0019/03]"`
6. Push
7. Отчёт
