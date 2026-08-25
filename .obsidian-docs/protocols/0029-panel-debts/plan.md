# 0029-panel-debts — Долги куска 1 Epic-11: savings в базе календаря + тесты визуального слоя щитка

## ADR-style Summary

- **Context**: Протокол 0028 (Epic-11 «щиток», кусок 1) смержен с двумя
  зафиксированными хвостами. (1) Латентный дефект кассового календаря:
  `CalendarService._calculate_recurring_before_date` при расчёте остатка
  ДО начала периода учитывает только income/expense и игнорирует
  savings-типы (SAVINGS_RESERVE, SAVINGS_CONTRIBUTION), тогда как соседние
  методы того же файла (`_get_recurring_daily_changes`,
  `_get_recurring_totals_for_period`) их честно вычитают. Из-за этого
  savings-операция, оказавшаяся раньше начала окна расчёта, завышает
  стартовую базу остатка — и «Свободно сегодня» на щитке. Правка была
  запрещена ограничением C-3 протокола 0028 («существующие сервисы не
  менять») — ROADMAP называет её «кандидат №1 в отдельный протокол до
  начала куска 2». (2) Визуальный слой щитка (шапка, график полос,
  легенда, тултипы, расчёт подписей оси) не покрыт тестами вовсе — три
  критерия приёмки 0028 проверены только вручную; регрессия шестерёнки
  (3.5-m-fix) не ловилась тестами именно поэтому.
- **Problem Statement**: До начала куска 2 (карточки-двери) нужно
  (а) устранить завышение базы остатка savings-операциями и снять
  задокументированное ограничение модели слоёв; (б) закрыть тестовый
  долг визуального слоя щитка, чтобы кусок 2 менял дашборд под защитой
  тестов.
- **Decision**: Один протокол, два независимых шага + финализация.
  Шаг 1 — багфикс `_calculate_recurring_before_date` (вычитать
  savings-типы как расход, симметрично соседним методам) + регрессионные
  тесты, включая сценарий из докстринга MoneyLayersService (перенос
  savings-exception с прошедшей даты внутрь окна); актуализация
  докстрингов, описывающих снятое ограничение. Шаг 2 — unit-тесты чистых
  build-функций щитка (`build_free_header`, `build_layers_chart`,
  `_axis_tickvals`, легенда, тултипы, пустые состояния) в новом
  `tests/test_dashboard_panel_ui.py`.
- **Alternatives**: (а) Делать два отдельных протокола — отклонено:
  оба хвоста маленькие, из одного источника (долги куска 1), не
  пересекаются по файлам; накладные расходы двух протоколов не окупаются.
  (б) Отложить тесты визуального слоя в кусок 2 — отклонено: смысл
  тестов в том, чтобы кусок 2 начинался под их защитой.
- **Consequences**: «Свободно сегодня» перестаёт завышаться при
  savings-операциях до начала периода; известное ограничение куска 1
  снимается из докстрингов и ROADMAP; визуальный слой щитка получает
  регрессионную сетку до начала куска 2. Возможны изменения ожиданий
  в существующих тестах календаря, закрепивших старое (неверное)
  поведение — правятся с обоснованием в log.md.

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Багфикс savings в базе остатка календаря](./01-calendar-savings-fix.md)**: `_calculate_recurring_before_date` учитывает savings-типы; регрессионные тесты; снятие ограничения из докстрингов
- **[Шаг 2: Тесты визуального слоя щитка](./02-panel-ui-tests.md)**: unit-тесты build-функций дашборда (шапка, график, легенда, тултипы, ось, пустые состояния)
- **[Шаг 3: Финализация](./03-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/Projects/FinFocus`
- CWD (worktree): `/home/skytiger/Projects/worktrees/0029-panel-debts`
- Протокол: `.obsidian-docs/protocols/0029-panel-debts/`

**Вся работа ведётся из CWD.**

**Toolset** (venv машинно-локальный, живёт в PROJECT_ROOT):
- COMPILE_CHECK: `/home/skytiger/Projects/FinFocus/.venv/bin/python -m py_compile {FILES}`
- FULL_CHECK: `/home/skytiger/Projects/FinFocus/.venv/bin/black app/ tests/ && /home/skytiger/Projects/FinFocus/.venv/bin/flake8 app/ && /home/skytiger/Projects/FinFocus/.venv/bin/pytest`
- ВАЖНО: black ТОЛЬКО из .venv (системный black 26.x форматирует иначе)
- Известные 6 pre-existing E501 в app/ (открытый вопрос №5 ROADMAP) — не блокер; критерий «flake8 без НОВЫХ замечаний»

### Цикл выполнения шага

См. `~/.claude/templates/protocol/workflow.md.tpl`

### Формат отчёта

См. `~/.claude/templates/protocol/report-format.md.tpl`

---

## Generic Principles

См. `~/.claude/templates/protocol/principles.md.tpl`

---

## Reference Materials

- `app/services/calendar_service.py:364-406` — дефектный `_calculate_recurring_before_date` (суммирует только income/expense)
- `app/services/calendar_service.py:408-466` — эталонные соседи, вычитающие savings-типы (`_get_recurring_daily_changes`, `_get_recurring_totals_for_period`)
- `app/services/money_layers_service.py` — докстринг формулы резерва с описанием снимаемого ограничения («Фактическая дата savings-операции...»)
- `.obsidian-docs/ROADMAP.md` → Epic-11, «Известное ограничение куска 1» — запись, которую снимает шаг 1
- `.obsidian-docs/knowledge-bank/modules/services.md` → MoneyLayersService, блок «Известные допущения и ограничение»
- `app/components/dashboard.py` — build-функции щитка (шаг 2): `build_free_header`, `build_layers_chart`, `_axis_tickvals`, `_build_layer_legend`, `_build_payments_tooltip`, `_build_reserve_tooltip`, `_build_chart_empty_state`, `_build_header_empty_state`
- `tests/test_money_layers_service.py` — 12 кейсов численной трассировки (образец табличного стиля тестов)
- `tests/conftest.py` — хелперы относительных дат (обязательны: тесты не должны протухать от календаря)
- `.obsidian-docs/protocols/0028-money-layers-panel/` — родительский протокол с ограничением C-3
