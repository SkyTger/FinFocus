# Шаг 3: Календарь и список операций

## Briefing

- **Цель:** Разовый расход отличим тем же цветом в календаре (точка дня,
  подсказка дня) и в списке операций (значок у строки).
- **Ключевые файлы:** `app/components/calendar.py` (строка операции в
  подсказке :425-460, точки дня :625-640), `app/assets/calendar.css`
  (`.txn-dot` :279-296), `app/components/transactions.py` (значок повтора
  :575-582), тесты `tests/test_calendar_tooltip.py`,
  `tests/test_calendar_tooltip_visual.py` (якорные тесты по тексту CSS),
  тест списка операций — рядом с `tests/test_transactions_system_ops.py`.
- **Доп. информация:** определение «разового» — plan.md. Служебные
  операции (резерв, взносы, корректировки) разовыми не помечать. Иконка списка —
  `bi-flag-fill` (проверено 2026-11-03: есть в bootstrap-icons@1.10.3,
  которую подключает `dbc.icons.BOOTSTRAP` в `app/main.py:55`).

## Sub-tasks

1. Календарь, точки: `txn-dot one-off` (title «Разовый расход») при
   разовом расходе в дне; `expense` — только при расходе серии. CSS
   `.txn-dot.one-off { background-color: var(--color-one-off); }`.
2. Календарь, подсказка дня: строка разового расхода помечена цветом
   разовых (один приём).
3. Список операций: значок разовой траты на месте значка повтора,
   цвет `--color-one-off` (класс в CSS, не инлайн-цвет), `title="Разовая трата"`.
4. Тесты: день только с разовым → точка one-off без expense; день с
   расходом серии → expense без one-off; оба → обе точки; служебные →
   не one-off; строка подсказки; значок в списке у разового и его
   отсутствие у шаблона серии, исключения серии, служебной; якорный тест
   CSS на `.txn-dot.one-off` и класс значка.
5. black / flake8 / pytest.

## Workflow

1. Sub-tasks последовательно
2. `.venv/bin/python -m py_compile <изменённые файлы>`
3. log.md, context.md (Current Step 4)
4. `git status`
5. Коммит: `git add . && git commit -m "feat(ui): разовые траты в календаре и списке операций [protocol-0034-one-off-expenses/03]"`
6. Push — не делать
7. Отчёт
