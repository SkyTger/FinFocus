# Шаг 3: Формула резерва «по дате D» + вехи целей

## Briefing

- **Цель:** Реализовать единую формулу слоя «Резерв» без ветвления по режиму резервирования и материализовать вехи целей внутри сессии.
- **Ключевые файлы:**
  - `app/services/money_layers_service.py` — `_goals_part_by_day`, `_goal_milestones`, снятие заглушки в `get_money_layers`
  - Читать (не менять): `app/services/budget_reservation_service.py` (`get_settings` — только `monthly_budget`), `app/services/goal_service.py:222-239` (`get_all_by_user` возвращает ORM-объекты)
- **Источник правды:** solution-v4.md — докстринг `_goals_part_by_day` целиком (с двумя Note про допущения и Note про ограничение) + «Численная трассировка» (12 кейсов).
- **Соответствует шагам 4–5 плана решения** (оценка 4 ч).

## Это самый тонкий шаг протокола

Две предыдущие версии решения здесь ошиблись, и оба раза дефект был невидим для инварианта AC-3. Формула проверена критиком независимым пересчётом на 12 кейсах — **реализовывать буквально по решению, не «упрощая по ходу»**.

## Sub-tasks

1. **`_goals_part_by_day(savings_by_date, window_dates, monthly_budget)`:**
   ```
   consumed(D)   = Σ savings_by_date[d], d в [month_start(D), D]
   committed(D)  = Σ savings_by_date[d], d в (D, month_end(D)]
   goals_part(D) = max(0, monthly_budget − consumed(D) − committed(D))
   ```
   - Месяц берётся **по дню D** — никакого наследования базы через границу месяца
   - **`committed(D)` НЕ ограничен `window_end`**: суммирует до `month_end(D)` включительно, даже если `month_end(D) > window_end`. Ключи за окном в `savings_by_date` присутствуют (шаг 2) и отбрасывать их нельзя — иначе «Свободно» завышается (это исправление замечания критики v3 №2)
   - Реализация — префиксные/суффиксные проходы в разрезе месяцев окна, линейно
   - Никаких вызовов `get_budget_progress` и `_get_reserve_sum_for_month` — формула их не требует

2. **Докстринг `_goals_part_by_day`** — перенести из решения полностью, включая:
   - Смысл слагаемых (`consumed` — уже ушло из баланса; `committed` — лежит в слое «Платежи»)
   - Note: суммирование не ограничено окном (с обоснованием направления ошибки)
   - Note: **допущение «бюджет не менялся внутри месяца»** — с доказательством (`sync_template_amount` обновляет только `template.amount`, exceptions не переписывает) и **обоими направлениями ошибки** (уменьшен → числа корректны, теряется бит о превышении; увеличен → «Свободно» занижено, безопасная сторона). Перерасход обрезается `max(0, …)` **без признака в UI** — решение владельца п. 3в
   - Note: **ограничение** «savings-exception, перенесённый внутри месяца с даты до `reference_date`» → «Свободно» завышается; причина — латентный дефект `_calculate_recurring_before_date`, править запрещено C-3
   - Note: `budget(D) == monthly_budget` для любого D (месячной истории бюджета в схеме нет)

3. **`_goal_milestones(user_id, reference_date, window_end)`:**
   - `GoalService.get_all_by_user` возвращает `list[Goal]` — **материализовать поля внутри сессии**, включая вычисляемое `progress_percentage`, иначе `DetachedInstanceError` после закрытия сессии
   - До `MAX_MILESTONES_IN_WINDOW = 3` вех в окне (ближайшие по `target_date`) + не более одной с `beyond_window=True`

4. **Снять заглушку** в `get_money_layers`: подключить реальный `goals_part`, заполнить `reserve_configured` (до каскада) и `reserve` (после), `goals_reserve_today`, `reserve_configured_today`.

5. **Fail-open + `degraded`:** сбой чтения бюджета → `monthly_budget = 0`, `degraded = True`, `logger.opt(exception=True).warning(...)`; сбой `GoalService` → `milestones = []`, `degraded = True`; сбой `get_threshold_amount` → `cushion_threshold = 0`, `degraded = True`. Сбой `calculate_daily_balances` **не глотать**.

## Проверки шага

- `python -m py_compile app/services/money_layers_service.py`
- **Ручная сверка с трассировкой решения** (до написания тестов шага 4): собрать на реальной или тестовой БД конфигурацию кейса 2 (`fixed_date`, бюджет 15 000, резерв 25-го, взнос 5 000 частичный) → `goals_part` на сегодня == **5 000**, не 0 и не 15 000
- Кейс 9 (границы месяцев, взносов нет): `goals_part` на последнем дне месяца, 1-м числе следующего и после резерва следующего месяца == **0**; на правом крае окна (месяц без резерва в окне) == один `monthly_budget`, не два
- `.venv/bin/black` + `.venv/bin/flake8 --select=F` — чисто
- `.venv/bin/pytest -q` — 565 зелёные

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile {FILES}`
3. Обнови `log.md` — **обязательно записать фактические числа ручной сверки** (кейсы 2 и 9)
4. Обнови `context.md` — Current Step: 4, Next Action: Шаг 4
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(services): единая формула резерва по дате D + вехи целей [protocol-0028/03]"`
7. Push
8. Отчёт
