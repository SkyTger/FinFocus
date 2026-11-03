# Шаг 1: Признак разового расхода в модели

## Briefing

- **Цель:** Модель знает, какие предстоящие платежи — разовые расходы, и
  отдаёт графику и шапке одну группировку (единый источник, как
  `bottleneck_marker`). Формулы слоёв не меняются.
- **Ключевые файлы:** `app/schema/money_layers.py` (`UpcomingPayment`,
  новый `OneOffMark`; экспорт в `app/schema/__init__.py`, если там
  перечислены типы), `app/services/money_layers_service.py`
  (`_collect_operations` :425-560, рядом с `bottleneck_marker` :49-90),
  новый `tests/test_one_off_expenses.py`.
- **Доп. информация:** определение «разового расхода» — plan.md,
  раздел «Спецификация». Все места, где `UpcomingPayment` создаётся
  литералом (grep по тестам и `app/`), получают новое поле — иначе
  TypedDict-контракт разъедется.

## Sub-tasks

1. `UpcomingPayment.is_one_off: bool` + докстринг; `OneOffMark` (date,
   total, items).
2. `_collect_operations`: `is_one_off = txn_type == "expense" and not
   txn["is_recurring"] and not txn["is_virtual"]`.
3. `one_off_marks(data)` и `one_off_total_until(data, end)` — чистые
   функции модуля, докстринги по-русски.
4. Тесты (через реальный сервис на тестовой БД, как соседние тесты
   модели слоёв, даты относительные):
   - разовый расход → `is_one_off=True`; экземпляр серии, шаблон,
     исключение серии (перенесённый экземпляр), savings_reserve,
     savings_contribution, отрицательная корректировка → False;
   - группировка: два разовых в один день → одна отметка, total — сумма,
     items по убыванию суммы; разовый за `window_end` в отметки не
     попадает, но в `one_off_total_until` с концом за осью — попадает;
   - `one_off_total_until` включает обе границы; пустой результат → 0;
   - регресс: слои/лимит/узкое место на том же наборе данных не
     изменились от наличия разовых — сравнить с ожиданием, посчитанным
     вручную в тесте (не со снимком текущего вывода).
5. black / flake8 / pytest — все прежние тесты зелёные без правки ожиданий.

## Workflow

1. Sub-tasks последовательно
2. `.venv/bin/python -m py_compile <изменённые файлы>`
3. log.md, context.md (Current Step 2)
4. `git status` — нет посторонних файлов
5. Коммит: `git add . && git commit -m "feat(layers): признак разового расхода и группировка по дням [protocol-0034-one-off-expenses/01]"`
6. Push — не делать
7. Отчёт
