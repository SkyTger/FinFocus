# Шаг 1: Багфикс savings в базе остатка календаря

## Briefing

- **Цель:** `CalendarService._calculate_recurring_before_date` учитывает
  savings-типы симметрично соседним методам; «Свободно сегодня» на щитке
  перестаёт завышаться при savings-операциях до начала периода расчёта;
  задокументированное ограничение куска 1 снято из докстрингов.
- **Ключевые файлы:**
  - `app/services/calendar_service.py:364-406` — дефектный метод: цикл
    суммирования учитывает только `income`/`expense`, savings-инстансы
    молча выпадают
  - `app/services/calendar_service.py:428-436, 460-466` — эталонные
    соседи (`_get_recurring_daily_changes`, `_get_recurring_totals_for_period`):
    savings-типы вычитаются как расход
  - `app/services/money_layers_service.py` — докстринг формулы резерва
    (допущение «Фактическая дата savings-операции совпадает…» и упоминание
    `_calculate_recurring_before_date` около строки 564) — ограничение
    снимается, текст актуализировать
  - `tests/test_calendar_service.py`, `tests/test_money_layers_service.py`
    — существующие тесты; новые регрессионные — рядом с существующими
- **Доп. информация:**
  - Дефект несимметричен: `_calculate_balance_before_date` (обычные
    операции) savings-типы УЖЕ вычитает; exceptions исключены из regular
    query (`recurring_parent_id == None`) и учитываются только в
    recurring-ветке — поэтому перенесённый savings-exception попадает
    ровно в дефектный метод.
  - Фикс минимальный: в цикле `total` добавить вычитание для
    `savings_reserve`/`savings_contribution` (по образцу соседей).
    Заодно актуализировать докстринг метода («INCOME - EXPENSE» → честная
    формула).
  - Ограничение C-3 протокола 0028 на этот протокол НЕ распространяется —
    правка `calendar_service.py` и есть цель протокола.
  - Даты в тестах — ТОЛЬКО через хелперы относительных дат из
    `tests/conftest.py` (защита от протухания, открытый вопрос №6).
  - Если существующие тесты закрепили старое (неверное) поведение —
    поправить ожидания с обоснованием в log.md; это НЕ «подгонка под
    зелёный», а исправление эталона вместе с дефектом. Перед правкой
    каждого такого теста убедиться, что он падает именно из-за новой
    (правильной) базы остатка.

## Sub-tasks

1. Написать падающий регрессионный тест на `calculate_daily_balances`:
   recurring savings-шаблон (или savings-exception, перенесённый с даты
   до начала периода) существует до `start_date` → база остатка должна
   быть уменьшена на его сумму. Проверить оба savings-типа.
2. Написать падающий тест на сценарий из докстринга MoneyLayersService:
   savings-exception перенесён внутри текущего месяца с даты ДО
   reference_date → «Свободно» (free сегодня) больше НЕ завышено.
3. Исправить `_calculate_recurring_before_date`: вычитать
   `savings_reserve`/`savings_contribution` в цикле суммирования;
   актуализировать докстринг метода.
4. Актуализировать докстринг формулы резерва в
   `app/services/money_layers_service.py`: убрать снятое ограничение
   (перенос savings-exception), оставив остальные допущения нетронутыми.
5. Прогнать полный pytest; существующие тесты со старыми ожиданиями —
   разобрать по одному (см. Доп. информация).
6. Mutation-проверка осмысленности новых тестов: временно вернуть старое
   поведение (убрать вычитание savings) → новые тесты обязаны упасть;
   вернуть фикс.

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `/home/skytiger/Projects/FinFocus/.venv/bin/python -m py_compile app/services/calendar_service.py app/services/money_layers_service.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step + 1, Next Action
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "fix(calendar): savings-типы в расчёте остатка до начала периода [protocol-0029/1]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
