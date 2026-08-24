# Solution v4: MoneyLayersService — единая формула резерва «по дате D», шапка без вердикта и без приветствия

## Обзор решения

Это **полировка v3**, не переработка. Архитектура, контракт, формула резерва, горизонты и план шагов сохранены. Формула резерва подтверждена независимым пересчётом критика на всех девяти кейсах и **не меняется ни в одном символе**.

Пять точечных правок, закрывающих все замечания critique-v3:

1. **Допущение «бюджет не менялся внутри месяца» объявлено явно** (решение владельца п. 3в). Докстринг `_goals_part_by_day` получает раздел о том, что `monthly_budget` — текущая настройка, а savings-операции месяца могли быть зафиксированы при другом бюджете. Перерасход (`consumed + committed > monthly_budget`) обрезается до нуля **без признака в UI** — решение владельца, промолчать. В блок A шага 6 добавлены **два параметра**: бюджет уменьшен после частичного взноса; бюджет увеличен после полного. Формула не тронута. (🟡№1)

2. **Поведение savings-операций с фактической датой вне окна определено, с доказательством по коду.** Проверка механики дала результат **точнее версии критика**: `create_exception(new_date=...)` — параметр **без единого вызывающего** во всём коде, но расхождение `transaction_date` / `original_date` достижимо двухшаговым путём UI (создать exception → отредактировать его дату в модале операции, `update_transaction` не трогает `original_date`). При этом ключевое: **баланс и наш сбор используют одну и ту же выборку** (`get_instances_with_exceptions` → отбор по `original_date`, раскладка по `transaction_date`), поэтому «сдвинутого влево» расхождения между слоями и балансом нет — оно целиком поглощается уже задокументированным латентным дефектом `_calculate_recurring_before_date`. Реализуемая правка — ровно один `if`: **не отбрасывать** savings-операции с датой за `window_end`, учитывать их в `committed(D)` для тех D, чей `month_end(D)` их накрывает. Плюс тест в блок F и запись ограничения с направлением ошибки. (🟡№2)

3. **Приветствие «Привет, {имя}» с дашборда снято** (решение владельца п. 3г). Шапка = аватарка + имя справа, как в эскизе (проверено по `v3.html:415-418` — приветствия в эскизе нет вовсе). Следствия: `_build_greeting_text()` теряет **оба** своих вызывающих (`dashboard.py:111` layout, `:1386` callback — grep дал ровно два) и **удаляется как мёртвый код** вместе с `TestBuildGreetingText`; лишний запрос профиля за рендер снят (🟢№3); «пустой» `exc_info=True` уходит вместе с хелпером (🟢№4). Состав правок `tests/test_dashboard_callbacks.py` пересмотрен: **четыре** позиции вместо трёх, оценка шага 13 — 1.5 → 2 ч.

4. **`TARGET_X_TICKS` переименована в `MAX_X_TICKS`** с формулой, гарантирующей ненарушение потолка (`k = ceil(n / MAX_X_TICKS)`). Проверено по эскизу: там ровно 11 подписей, но с **неравномерным** шагом (семантические даты: 22/25/28 авг, 1/5/10/15/20/25/30 сент, 5 окт) — равномерная сетка эскиз не воспроизводит в принципе, поэтому честнее объявить потолок, чем цель. (🟢№5)

5. RTM дополнена строкой о снятом приветствии; NFR-1 пересчитан (запрос профиля в шапке отсутствует по построению — `profile` уже передан аргументом).

## Архитектура

### Компоненты

**1. `app/schema/money_layers.py` (новый) — контракт модели**

TypedDict'ы `DayLayers`, `UpcomingPayment`, `GoalMilestone`, `TodaySlice`, `MoneyLayersData`; `Horizons`; литерал `LayerKey`; константы `WINDOW_DAYS = 45`, `MAX_MILESTONES_IN_WINDOW = 3`, `MAX_X_TICKS = 11`, `LAYER_COLORS`, `LAYER_LABELS`. Ноль зависимостей от Dash/SQLAlchemy (стиль `app/schema/dashboard.py`). Пометка в модуль-докстринге: контракт спроектирован под кусок 1 и не претендует на стабильность до куска 2.

Всё, что относилось к вердикту (`VerdictLevel`, `VERDICT_TEXTS`, `VERDICT_COLORS`, `DIP_RATIO`, `DIP_FLOOR`), **не создаётся** — решение владельца п. 3а.

**2. `app/services/money_layers_service.py` (новый) — ядро FR-1**

Единственный публичный метод `get_money_layers(user_id, reference_date=None) -> MoneyLayersData`. Read-only.

Три диапазона дат (без изменений относительно v3):

| Диапазон | Границы | Назначение |
|---|---|---|
| **Окно оси** `[reference_date, window_end]` | `reference_date + 44` (45 дней вкл.) | Дни в `days[]`, ось X, зона поиска минимума, вехи целей |
| **Диапазон сбора операций** `[collect_start, window_end]` | `collect_start = month_start(reference_date)` | ЕДИНСТВЕННЫЙ вызов `get_all_transactions_for_period`. Левая граница — начало месяца `reference_date`, потому что `consumed(reference_date)` требует savings-операций **до** сегодня в пределах текущего месяца |
| **Горизонт слоя «Платежи»** `payments_end` | последний день календарного месяца `reference_date` | Чисто арифметический фильтр суффиксной суммы (C-5) |

Приватные шаги (состав тот же, что в v3):

- `_horizons(reference_date) -> Horizons` → `(collect_start, window_end, payments_end)`;
- `_forecast_balances()` → `CalendarService.calculate_daily_balances(user_id, reference_date, window_end)` — единственный источник прогнозного остатка (AC-3 по построению);
- `_collect_operations()` → **один** `CalendarService.get_all_transactions_for_period(user_id, collect_start, window_end)`. Возвращает `payments: list[UpcomingPayment]` (расходные операции) и `savings_by_date: dict[date, Decimal]`. **Уточнение v4:** `savings_by_date` ключуется по **фактической дате операции** и **не фильтруется** по границам окна;
- `_payments_tail_by_day()` → `payments(D) = Σ` платежей с датой в `(D, payments_end]`, только с датой `>= reference_date`. `payments(D) = 0` для `D >= payments_end` — видимая честность C-5;
- `_goals_part_by_day()` → единая формула (ниже);
- `_split_day()` → каскад сжатия слоёв, сумма == остаток во всех ветках. **Единственный** механизм обрезки «Резерва» (решение владельца п. 3б);
- `_today_slice()` → `TodaySlice` (free/balance/payments/reserve на `reference_date`);
- `_window_min_free()` → `(min_free, min_free_date)` по всему окну — для маркера графика FR-3.e;
- `_goal_milestones()` → материализация активных целей в `GoalMilestone` **внутри сессии**;
- `_is_empty()` → чистая функция от уже полученных данных, **без запросов**.

**Семантика слоя «Резерв» — единая формула (не меняется).**

```
cushion_part           = cushion_threshold                     # константа по окну
month_start(D)         = date(D.year, D.month, 1)
month_end(D)           = date(D.year, D.month, monthrange(D.year, D.month)[1])
consumed(D)            = Σ savings_by_date[d] для d в [month_start(D), D]
committed(D)           = Σ savings_by_date[d] для d в (D, month_end(D)]
goals_part(D)          = max(0, monthly_budget − consumed(D) − committed(D))
reserve_raw(D)         = cushion_part + goals_part(D)
```

Три свойства, подтверждённые независимым пересчётом критика:

- **Ноль двойного счёта.** Каждая savings-операция попадает ровно в одно из двух слагаемых — по своей дате относительно D.
- **Ноль наследования через границу месяца.** Месяц берётся по дню D; максимум `goals_part` по окну равен одному `monthly_budget`.
- **Ноль зависимости от режима.** Формула спрашивает у кассового календаря «какие savings-операции стоят на этих датах».

**НОВОЕ в v4 — область суммирования `committed(D)` не ограничена окном (🟡№2).**

`consumed(D)` и `committed(D)` суммируют по **всем** ключам `savings_by_date`, попадающим в соответствующий интервал месяца дня D, **включая ключи за `window_end`**. Это ровно один дополнительный `if` (снятие фильтра, а не добавление ветки), и он нужен потому, что `savings_by_date` физически может содержать даты вне `[collect_start, window_end]`: `get_instances_with_exceptions` отбирает exceptions по `original_date` в диапазоне, а раскладывает по `transaction_date` (`recurring_service.py:691-695`, `:706-710`; `calendar_service.py:845`), и у перенесённого exception эти даты не совпадают.

Смысл правки: для дня D у правого края окна операция, чей `transaction_date` лежит между `window_end` и `month_end(D)`, — это реальное «ещё предстоит уйти в этом месяце». Её учёт в `committed(D)` снижает `goals_part(D)`, то есть **не завышает** «Свободно». Направление правки консервативно.

**Допущение согласованности данных (обязательство решения п. 3в и ответ на 🟡№2).**

Формула корректна при двух допущениях, и оба теперь объявлены в докстрингах, а не подразумеваются:

| Допущение | Чем нарушается | Что делает модель | Направление ошибки |
|---|---|---|---|
| `monthly_budget` согласован с суммами savings-операций месяца («бюджет не менялся внутри месяца») | Смена бюджета внутри месяца: `sync_template_amount` (`budget_reservation_service.py:808-839`) обновляет **только** `template.amount`, существующие exceptions не переписывает | `goals_part` отражает **текущую настройку**, а не историю; перерасход обрезается `max(0, …)` **без признака в UI** (решение владельца п. 3в) | При уменьшении бюджета — `goals_part` = 0, теряется только информация «обещано сверх бюджета», числа корректны. При увеличении — `goals_part` завышен на разницу, «Свободно» **занижено** (безопасная сторона) |
| Фактическая дата savings-операции совпадает с датой, по которой её видит кассовый календарь | Перенос даты exception: `transaction_date` уезжает, `original_date` остаётся | `savings_by_date` ключуется по **фактической** дате; операции за `window_end` учитываются в `committed(D)`, если `month_end(D)` их накрывает | См. разбор трёх случаев ниже |

**Разбор перенесённого exception по трём случаям (доказательство по коду, ответ на `[факт]`-вопрос критика).**

Обе стороны — и наш сбор, и расчёт баланса — идут через **одну и ту же** функцию `get_instances_with_exceptions(user_id, start, end)` с **одинаковой** семантикой (отбор по `original_date`, раскладка по `transaction_date`). Поэтому расхождение между слоями и балансом возникает не из-за разных правил, а только из-за разных **диапазонов** вызова:

| Случай | `original_date` | `transaction_date` | Видит наш сбор `[collect_start, window_end]` | Видит баланс окна `_get_recurring_daily_changes(ref, window_end)` | Итог |
|---|---|---|---|---|---|
| **1. Сдвиг вправо** | в `[collect_start, window_end]` | `> window_end` | **Да**, с ключом за `window_end` | Нет (за пределами окна баланса — и не должен: деньги уйдут после окна) | В v3 отбрасывалась → `committed(D)` недосчитан. **В v4 учитывается** в `committed(D)` при `transaction_date <= month_end(D)`. Расхождения нет |
| **2. Сдвиг влево, за `collect_start`** | `< collect_start` | в окне | **Нет** (`original_date` вне диапазона отбора) | **Нет** (та же причина — тот же отбор по `original_date`) | Баланс её тоже **не видит**: `_calculate_recurring_before_date` (`calendar_service.py:396-406`) считает только income/expense и savings **игнорирует**. Слои и баланс согласованы; расхождение с реальностью — это **уже задокументированный латентный дефект** `_calculate_recurring_before_date`, вне scope по C-3 |
| **3. Сдвиг внутри месяца, `original_date < reference_date`** | в `[collect_start, ref−1]` | в окне | **Да** | **Нет** (`original_date < ref`, отбор её не берёт) | Наш `consumed/committed` её учитывает, баланс — нет. Направление: лишнее слагаемое **уменьшает** `goals_part` → **уменьшает** резерв → **увеличивает** «Свободно». Единственная опасная сторона; фиксируется как ограничение (ниже) |

**Достижимость входа проверена по коду и оказалась узкой.** Параметр `create_exception(new_date=...)` (`recurring_service.py:405`, `:464-465`, `:484`) **не имеет ни одного вызывающего**: grep по `new_date` даёт только сам `recurring_service.py` и не связанную локальную переменную в `app/components/calendar.py:816-822` (навигация по месяцам). Все три реальных вызова `create_exception` (`budget_reservation_service.py:294`, `:916`, `transaction_modals.py:1163`) передают только `original_date` (+ сумма/описание), то есть создают exception **с совпадающими датами**.

Расхождение достижимо **двухшаговым** путём: `process_recurring_edit_scope` создаёт exception с `transaction_date == original_date` (`transaction_modals.py:1163-1166`), после чего пользователь меняет дату в модале правки операции — `TransactionService.update_transaction` присваивает `transaction.transaction_date` и **`original_date` не трогает** (`transaction_service.py:236-243`). Вход реален, но требует ручного переноса конкретного экземпляра регулярной операции резерва/взноса.

**Ограничение, фиксируемое явно (случай 3).** Если savings-exception перенесён внутри текущего месяца с даты **до** `reference_date` на дату **внутри окна**, слои учтут его, а прогнозный остаток — нет (из-за латентного дефекта `_calculate_recurring_before_date`), и «Свободно» окажется **завышено** на сумму операции. Инвариант AC-3 это не поймает (он по построению слеп: `free` выводится вычитанием). Правка невозможна в рамках куска 1: она требует исправления `_calculate_recurring_before_date`, что запрещено C-3. Ограничение записывается в осадок решений одним пунктом с латентным дефектом, чьим следствием оно является — это не отдельный дефект модели, а его проявление.

**Почему `committed(D)` ограничен `month_end(D)`, а слой «Платежи» — `payments_end`** (без изменений). Это разные величины. `payments_end` = конец месяца **`reference_date`** (C-5 буквально). `month_end(D)` = конец месяца **дня D**. Для `D <= payments_end` они совпадают, и `committed(D)` равен savings-части слоя «Платежи» — деньги лежат в оранжевом и потому вычтены из синего. Для `D > payments_end` оранжевый слой пуст (C-5), но синий живёт по бюджету месяца дня D.

**Обрезка «Резерва» — один механизм** (решение владельца п. 3б, без изменений). `cushion_part = cushion_threshold` без `min(..., balance)`. Дефицит гасится каскадом `_split_day`: сначала `reserve`, затем `payments`.

**Честная подпись слоя** (обязательство п. 3б, без изменений). Тултип «Резерв» строится из **фактического** значения дня; поле `reserve_configured` в контракте делает расхождение цифры и картинки невозможным конструктивно.

**3. `app/services/cushion_service.py` (изменяется — ДОБАВЛЕНИЕ метода)**

`get_threshold_amount(user_id) -> Decimal` — `target * percent / 100` без `_get_current_balance()`. Проверено: `threshold_amount` в `get_settings` (`cushion_service.py:104-107`) от баланса не зависит. Возвращает `Decimal("0")` при отсутствии пользователя.

**4. `app/components/dashboard.py` (изменяется) — FR-2…FR-6**

- `build_free_header(data, profile) -> html.Div` (переименован из `build_verdict_header`). Состав: метка «Свободно сегодня», сумма, разбор «баланс − платежи − резерв», аватар+имя, кнопка «Сверка», шестерёнка. **Приветствия нет** (решение владельца п. 3г). Без чипа, без сигнальной шины, без окраски по уровню.
- **`_build_greeting_text()` УДАЛЯЕТСЯ** (`dashboard.py:82-91`) — мёртвый код после снятия обоих вызывающих (п. 3г, обоснование ниже).
- `build_layers_chart(data) -> dbc.Card` — вместо `_build_daily_cashflow_chart()` / `_build_yearly_cashflow_chart()`.
- `_build_layer_legend(data)` / `_build_payments_tooltip(data)` / `_build_reserve_tooltip(data)` — HTML-легенда вне поля графика (`showlegend=False`) с `dbc.Tooltip` (FR-4 + заметка vision-критика). Только текстовые компоненты; `dangerously_allow_html` и `dcc.Markdown` в новых путях запрещены.
- `_build_header_empty_state()` / `_build_chart_empty_state()` — FR-6.
- `_axis_tickvals(dates) -> list[date]` — явный список тиков (заменяет `_axis_dtick`).
- `_load_dashboard_components(period_state)` — сигнатура сокращается.
- `open_create_from_chart` перепривязывается на `dashboard-layers-chart-graph`, дата из `point["x"]` (ISO-строка).

**Судьба `_build_greeting_text()` — удаление (решение по п. 3г, проверено grep'ом).** Хелпер имел ровно два вызывающих, и оба снимаются этим куском:

| Вызывающий | Что с ним | Почему |
|---|---|---|
| `dashboard.py:111` — `html.H4(_build_greeting_text(), id="dashboard-greeting")` в `create_dashboard_layout` | Удаляется вместе с элементом `dashboard-greeting` (:108-112) | FR-2.f: шапка заменяет KPI-ряд и glass-header; приветствия в шапке нет (п. 3г) |
| `dashboard.py:1386` — 7-й Output `load_dashboard_data` | Удаляется вместе с Output `dashboard-greeting` (:1348) | Тот же |

Третьего вызывающего нет (`grep -rn "_build_greeting_text" app/ tests/` → только эти две строки в `app/` плюс импорт и тесты в `tests/test_dashboard_callbacks.py:20`, `:90`, `:100`). Следствия:

- Хелпер **удаляется** — оставлять функцию, открывающую сессию БД и не имеющую вызывающих, значит заводить мёртвый код в файле, из которого этот кусок мёртвый код как раз вычищает (шаг 12).
- `TestBuildGreetingText` (`tests/test_dashboard_callbacks.py:73-102`) **удаляется** вместе с хелпером — тесты удалённой функции не оставляют. Импорт `_build_greeting_text` из :20 снимается.
- `logger.warning(..., exc_info=True)` (`dashboard.py:90`) — «пустая» для loguru идиома (протокол 0027) — исчезает вместе с телом функции. Замечание 🟢№4 закрывается физически, а не оговоркой в NFR-2.
- Дух протоколов 0024/0026 сохраняется и **усиливается**: отдельного Output/callback'а на приветствие нет, потому что нет самого приветствия. Регрессионная защита подписки на `profile-updated` **не ослабляется**: `Input("profile-updated", "data")` остаётся у `load_dashboard_data` (тест :50) и у `toggle_balance_toast` (тест :57) — оба **не трогаются**. Обновление имени и аватара после правки профиля обеспечивается тем же Input'ом, но через шапку: `profile` передаётся аргументом в `build_free_header`.
- **Лишний запрос профиля за рендер снят по построению** (🟢№3): `_build_greeting_text` открывала собственный `get_db_session()` и читала профиль второй раз при уже переданном `profile`. Теперь профиль читается один раз в `_load_dashboard_components` и передаётся аргументом. Параметр `profile` осмыслен: он единственный источник аватара (`get_avatar_emoji(profile['avatar_id'])`) и имени в правом блоке шапки — ровно состав эскиза (`v3.html:415-418`: 🦊 + «Иван» + шестерёнка, приветствия в эскизе нет).

**5. `app/components/profile_modal.py` (изменяется — прямые изменения, решение владельца)**

Второй `Input("dashboard-settings-cog", "n_clicks")` и ветка `triggered_id in ("sidebar-profile-container", "dashboard-settings-cog")` вместо жёсткого `==` (:119). Единственный Input сейчас — `sidebar-profile-container` (:96). `suppress_callback_exceptions=True` (`main.py:41`) снимает риск отсутствия элемента вне дашборда.

**6. `app/assets/panel.css` (новый) — стили `pnl-*`** на CSS-переменных проекта. Отдельный файл — установленный паттерн (`analytics.css`, `calendar.css`, `goals.css`, `wishlist.css`). Класс приветствия не заводится (п. 3г).

### Диаграмма взаимодействия

```
┌───────────────────────────────────────────────────────────────────┐
│ app/components/dashboard.py                                       │
│   load_dashboard_data(pathname, profile_updated, period_state)    │
│   refresh_dashboard_after_crud(trigger, period_state, pathname)   │
│                    │                                              │
│                    ▼                                              │
│   _load_dashboard_components(period_state)   ← «period» УБРАН      │
│       ├─ OnboardingService.get_profile()  [1 раз, для шапки]      │
│       └─ MoneyLayersService.get_money_layers()                     │
│   ✗ _build_greeting_text()  — УДАЛЁН (п. 3г): второго запроса      │
│                                профиля за рендер больше нет        │
└────────────────────┬──────────────────────────────────────────────┘
                     │ get_money_layers(user_id)   [1 вызов]
                     ▼
┌───────────────────────────────────────────────────────────────────┐
│ MoneyLayersService   (НОВЫЙ, read-only, без flush/commit)          │
│                                                                   │
│  _horizons()  → collect_start = month_start(ref)                  │
│                 window_end    = ref + 44        (ось, 45 дней)    │
│                 payments_end  = month_end(ref)  (C-5)             │
│                                                                   │
│  _forecast_balances(ref .. window_end) ──────────────┐            │
│                                                       │            │
│  _collect_operations(collect_start .. window_end) ────┼──┐  ОДИН   │
│      ├─► payments:        list[UpcomingPayment]       │  │  вызов  │
│      └─► savings_by_date: dict[date, Decimal]         │  │         │
│           ключ = ФАКТИЧЕСКАЯ дата операции,           │  │         │
│           БЕЗ фильтра по границам окна (🟡№2)         │  │         │
│                                                       │  │         │
│  _payments_tail_by_day()  Σ в (D, payments_end]  ─────┤  │         │
│  _goals_part_by_day()     ЕДИНАЯ формула по месяцу D ─┤  │         │
│      goals(D)=max(0, budget − consumed(D) − committed(D))         │
│      committed(D) НЕ ограничен window_end: считает до             │
│      month_end(D) включительно (+1 if, 🟡№2)                      │
│  reserve_raw(D) = cushion_threshold + goals(D)   БЕЗ min()        │
│                                                       │  │         │
│  _split_day()  free = bal − pay − res (+каскад)  ─────┘  │  ← ЕДИН-│
│                                                          │    СТВЕН-│
│  _today_slice()      срез reference_date                 │    НАЯ  │
│  _window_min_free()  минимум по 45 дням (FR-3.e)         │    обрез-│
│  _goal_milestones()  материализация В СЕССИИ ──┐         │    ка   │
│  _is_empty()  БЕЗ запроса: из days+savings+     │        │  (п.3б) │
│               templates_exist+starting_balance  │        │         │
└────────────────────────────────────────────────┼────────┼─────────┘
                                                 │        │
        ┌────────────────────────────────────────┘        │
        ▼                     ▼                  ▼        ▼
┌──────────────┐  ┌───────────────────────┐  ┌────────────────────────┐
│ GoalService  │  │ CushionService        │  │ CalendarService        │
│ get_all_by_  │  │ get_threshold_amount()│  │ calculate_daily_       │
│ user(ACTIVE) │  │   ← НОВЫЙ, БЕЗ        │  │   balances             │
└──────────────┘  │     пересчёта баланса │  │ get_all_transactions_  │
                  └───────────────────────┘  │   for_period  (1 раз)  │
                  ┌───────────────────────┐  └──────────┬─────────────┘
                  │ BudgetReservation     │             ▼
                  │ Service               │      RecurringService
                  │ get_settings() →      │      get_instances_with_
                  │   monthly_budget      │        exceptions:
                  │   ТОЛЬКО              │      отбор по original_date,
                  └───────────────────────┘      раскладка по
                    ✗ get_budget_progress        transaction_date
                    ✗ _get_reserve_sum_for_month  ↑ ОДНА выборка и для
                    ✗ mode / day_of_month           баланса, и для нас
                     ↑ ни один существующий метод не меняется (C-3)

Возврат: MoneyLayersData ─┬─► build_free_header(data, profile)
                          │      «Свободно сегодня: N ₽» + разбор,
                          │      аватар+имя справа, БЕЗ приветствия,
                          │      БЕЗ вердикта
                          ├─► build_layers_chart()   stacked bars 45 дней
                          │                          + маркер min_free
                          └─► _build_layer_legend()  dbc.Tooltip (FR-4)

app/components/profile_modal.py ← НОВЫЙ Input("dashboard-settings-cog")
```

## Файловая структура

```
НОВЫЕ:
app/schema/money_layers.py            TypedDict'ы модели, LayerKey, константы
                                      (WINDOW_DAYS=45, MAX_MILESTONES_IN_WINDOW=3,
                                       MAX_X_TICKS=11, LAYER_COLORS, LAYER_LABELS)
                                      БЕЗ VerdictLevel/VERDICT_*/DIP_* (п. 3а)
app/services/money_layers_service.py  MoneyLayersService: композиция над Calendar/
                                      Cushion/BudgetReservation(только budget)/Goal
app/assets/panel.css                  Стили pnl-* (шапка + блок графика + легенда)
tests/test_money_layers_service.py    Таблица ожидаемых слоёв, инвариант AC-3,
                                      «таяние», границы месяцев, порог подушки,
                                      is_empty, детач, fail-open,
                                      смена бюджета внутри месяца, перенос exception

ИЗМЕНЯЕМЫЕ:
app/services/cushion_service.py       +get_threshold_amount() — ДОБАВЛЕНИЕ метода
app/components/dashboard.py           крупнейший blast — см. Blast Radius;
                                      УДАЛЕНИЕ _build_greeting_text() (п. 3г)
app/components/profile_modal.py       +Input("dashboard-settings-cog") и ветка
app/schema/__init__.py                реэкспорт новых типов + __all__
app/services/__init__.py              реэкспорт MoneyLayersService + типов + __all__
app/assets/custom.css                 чистка: #dashboard-overview-cards,
                                      .db-period-switcher, .kpi-*
tests/test_dashboard_callbacks.py     ЧЕТЫРЕ позиции (докстринг модуля, импорт :20,
                                      3 теста, УДАЛЕНИЕ класса TestBuildGreetingText)
tests/test_cushion_service.py         +тесты get_threshold_amount

НЕ ИЗМЕНЯЮТСЯ (доказательство C-3):
app/services/calendar_service.py, dashboard_service.py, goal_service.py,
budget_reservation_service.py, recurring_service.py, transaction_service.py,
app/components/sidebar.py, app/components/transaction_modals.py (кроме парсинга
клика по графику), tests/test_dashboard_service.py, tests/test_calendar_service.py,
tests/test_budget_reservation_service.py, tests/test_goal_service.py
```

## Ключевые интерфейсы

```python
# app/schema/money_layers.py
"""Контракт модели «свободно / платежи / резерв» по дням (EPIC-11, кусок 1).

Note:
    Контракт спроектирован под кусок 1 (шапка + график полос).
    Стабильность до куска 2 (карточки-двери) не гарантируется —
    осознанное решение, зафиксировано в memory/spec-context/epic-11.md.

Note:
    Цветового вердикта состояния (ok/dip/problem) в контракте НЕТ —
    решение владельца 2026-08-24 (memory/spec-context/epic-11.md, п. 3а):
    любой порог просадки произволен, проблемные дни пользователь видит
    на самом графике. Поле min_free оставлено не для вердикта, а для
    маркера минимума на графике (FR-3.e).
"""

from datetime import date
from decimal import Decimal
from typing import Literal, NamedTuple, TypedDict

LayerKey = Literal["free", "payments", "reserve"]
"""Ключ слоя декомпозиции прогнозного остатка."""

WINDOW_DAYS = 45
"""Длина окна оси графика в днях (включая сегодня).

Соответствует принятому эскизу .visual/finfocus-panel-dashboard/v3.html
(22 авг — 5 окт 2026). Горизонт слоя «Платежи» — отдельная величина,
конец календарного месяца (C-5), см. MoneyLayersService._horizons.
"""

MAX_MILESTONES_IN_WINDOW = 3
"""Максимум вех целей внутри окна (ближайшие по target_date).

Остальные попадают сводкой «и ещё N целей» в тултип слоя «Резерв»:
45-дневная ось не должна зарастать флажками (заметка vision-критика
про вертикальный ритм). Плюс не более одной вехи beyond_window.
"""

MAX_X_TICKS = 11
"""ПОТОЛОК числа подписей на оси X — не цель, а верхняя граница.

Переименована из TARGET_X_TICKS (critique-v3, замечание №5): прежнее
имя обещало результат, которого функция не давала (round(45/11) = 4 →
12 подписей при заявленных 11). Теперь _axis_tickvals использует
k = ceil(len / MAX_X_TICKS), что гарантирует len(tickvals) <= MAX_X_TICKS.

Почему потолок, а не цель: в эскизе v3 ровно 11 подписей, но с
НЕРАВНОМЕРНЫМ шагом — 22/25/28 авг, 1/5/10/15/20/25/30 сент, 5 окт
(v3.html:575-596), то есть семантически значимые даты, а не сетка.
Равномерная сетка эскиз не воспроизводит в принципе; воспроизводима
только плотность подписей, и её честнее ограничить сверху.
"""

LAYER_COLORS: dict[LayerKey, str] = {
    "free": "#2ecc71",      # Свободно — зелёный (эскиз v3)
    "payments": "#f0b775",  # Платежи — оранжевый приглушённый (эскиз v3)
    "reserve": "#3498db",   # Резерв — синий (эскиз v3)
}
"""Цвета слоёв графика — единственный источник правды (паттерн STATUS_COLORS)."""

LAYER_LABELS: dict[LayerKey, str] = {
    "free": "Свободно",
    "payments": "Платежи",
    "reserve": "Резерв целей и подушки",
}
"""Подписи слоёв в HTML-легенде (формулировки эскиза v3)."""


class Horizons(NamedTuple):
    """Три границы модели — почему их три, см. докстринг _horizons.

    Attributes:
        collect_start: Левая граница ЕДИНСТВЕННОГО сбора операций —
            начало календарного месяца reference_date. Нужна потому,
            что consumed(reference_date) требует savings-операций,
            датированных ДО сегодня в пределах текущего месяца.
        window_end: Последний день окна оси (reference_date + 44).
        payments_end: Последний день горизонта слоя «Платежи»
            (конец календарного месяца reference_date, C-5).
    """

    collect_start: date
    window_end: date
    payments_end: date


class DayLayers(TypedDict):
    """Декомпозиция прогнозного остатка одного дня окна на три слоя.

    Инвариант: free + payments + reserve == forecast_balance (AC-3).

    Attributes:
        date: Дата дня окна.
        free: Слой «Свободно» — реально доступные деньги.
        payments: Слой «Платежи» — уйдут на запланированные платежи
            в интервале (date, конец календарного месяца reference_date].
            За границей месяца всегда 0 — видимое ограничение C-5.
        reserve: Слой «Резерв» — ФАКТ дня после каскада _split_day.
            Может быть меньше reserve_configured, если остатка меньше:
            это и есть сигнал «вы залезаете в подушку».
        reserve_configured: Настроенный резерв дня ДО каскада
            (cushion_threshold + goals_part). Нужен тултипу, чтобы
            честно объяснить сжатие, а не утверждать настройку
            (решение владельца п. 3б).
        forecast_balance: Прогнозный остаток из CalendarService.
    """

    date: date
    free: Decimal
    payments: Decimal
    reserve: Decimal
    reserve_configured: Decimal
    forecast_balance: Decimal


class UpcomingPayment(TypedDict):
    """Предстоящий платёж для слоя «Платежи» и тултипа легенды (FR-4).

    Attributes:
        date: Дата платежа (ФАКТИЧЕСКАЯ дата операции).
        amount: Сумма, всегда положительная (для ADJUSTMENT — abs).
        description: Описание операции или None.
        category_name: Название категории или None.
        is_recurring: True для регулярных операций (маркер 🔁).
    """

    date: date
    amount: Decimal
    description: str | None
    category_name: str | None
    is_recurring: bool


class GoalMilestone(TypedDict):
    """Веха цели на оси времени графика (FR-3.c).

    Материализуется из ORM-объекта Goal ВНУТРИ сессии — иначе
    DetachedInstanceError на вычисляемом property progress_percentage
    (образец: TransactionInfo, calendar_service.py:27-33).

    Attributes:
        goal_id: ID цели.
        name: Название цели.
        target_date: Дата достижения.
        target_amount: Целевая сумма.
        progress_percent: Прогресс 0..100 (Goal.progress_percentage).
        beyond_window: True — цель за правым краем окна 45 дней
            (рисуется стрелкой-аннотацией у края, как в эскизе v3).
    """

    goal_id: int
    name: str
    target_date: date
    target_amount: Decimal
    progress_percent: float
    beyond_window: bool


class TodaySlice(TypedDict):
    """Срез модели на reference_date — источник цифр шапки (FR-2).

    Пришёл на место LayersVerdict из v2. Поля level / text /
    dip_threshold УДАЛЕНЫ решением владельца (п. 3а): шапка
    не выносит оценок, только показывает разбор. Минимум окна
    переехал в MoneyLayersData — он нужен графику, не шапке.

    Attributes:
        free: Слой «Свободно» на reference_date — главное число шапки.
        balance: Прогнозный остаток на reference_date (разбор).
        payments: Слой «Платежи» на reference_date (разбор).
        reserve: Слой «Резерв» на reference_date, ФАКТ дня (разбор).
    """

    free: Decimal
    balance: Decimal
    payments: Decimal
    reserve: Decimal


class MoneyLayersData(TypedDict):
    """Полный результат модели FR-1 — единый источник шапки и графика.

    Attributes:
        days: Декомпозиция по дням окна (reference_date .. window_end).
        today: Срез «сегодня» для шапки.
        min_free: Минимум слоя «Свободно» по ВСЕМУ окну — для маркера
            минимума на графике (FR-3.e). НЕ используется для оценки
            состояния: вердикта в куске 1 нет (решение владельца п. 3а).
        min_free_date: Дата этого минимума (первая при равенстве).
        upcoming_payments: Платежи до payments_end для тултипа (FR-4).
        milestones: Вехи целей для оси времени (FR-3.c).
        reference_date: Дата отсчёта («сегодня»).
        window_end: Последний день окна оси (reference_date + 44).
        payments_end: Последний день горизонта платежей (конец месяца, C-5).
        cushion_threshold: Порог подушки в слое «Резерв» (расшифровка).
        goals_reserve_today: Часть слоя «Резерв» от бюджета целей на сегодня
            (до каскада — настроенная).
        reserve_configured_today: cushion_threshold + goals_reserve_today.
            Сравнение с today['reserve'] показывает, сжат ли слой —
            тултип обязан говорить факт, а не настройку (п. 3б).
        degraded: True — часть модели посчитана в деградации (fail-open,
            см. «Обработка ошибок»). UI помечает разбор оговоркой
            «часть данных недоступна» и НЕ показывает заниженные числа
            как достоверные.
        is_empty: True — у пользователя нет данных ВООБЩЕ (FR-6);
            НЕ «нули в окне». Считается без отдельного запроса.
        window_is_flat: True — данные есть, но в окне ни одной операции
            (график рисуется плоским, пустое состояние НЕ подменяет его).
    """

    days: list[DayLayers]
    today: TodaySlice
    min_free: Decimal
    min_free_date: date
    upcoming_payments: list[UpcomingPayment]
    milestones: list[GoalMilestone]
    reference_date: date
    window_end: date
    payments_end: date
    cushion_threshold: Decimal
    goals_reserve_today: Decimal
    reserve_configured_today: Decimal
    degraded: bool
    is_empty: bool
    window_is_flat: bool
```

```python
# app/services/money_layers_service.py

class MoneyLayersService:
    """Модель «свободно / платежи / резерв» по дням (FR-1).

    Read-only надстройка: композиция над CalendarService (прогнозный
    остаток и перечень операций), BudgetReservationService (только
    monthly_budget), CushionService (порог подушки) и GoalService (вехи).
    Ни одного существующего метода не меняет, в БД не пишет (C-2, C-3).

    Два горизонта показа (решение владельца 2026-08-24):
        * окно оси — WINDOW_DAYS = 45 дней от reference_date (эскиз v3);
        * горизонт слоя «Платежи» — конец календарного месяца (C-5).
          За границей месяца payments(D) == 0: ограничение видно честно,
          а не скрыто сужением оси.

    Инвариант декомпозиции: для каждого дня D окна
        free(D) + payments(D) + reserve(D) == CalendarService.balance(D)
    (AC-3) — обеспечен конструктивно, free выводится вычитанием, а
    _split_day сохраняет сумму во всех ветках.

    Note:
        Слой «Резерв» считается ОДНОЙ формулой от даты D, без ветвления
        по режиму резервирования. Формула спрашивает у кассового
        календаря «какие savings-операции стоят на этих датах»,
        а не у BudgetReservationService «сколько израсходовано за
        месяц»: get_budget_progress отвечает на другой вопрос
        (докстринг budget_reservation_service.py:173-179 — «единообразно
        для обоих режимов считает взносы»), и попытка вывести из него
        «сколько лежит в остатке на день D» даёт двойной счёт при
        частичном взносе (critique-v2, блокер №1).

    Note:
        ДОПУЩЕНИЯ СОГЛАСОВАННОСТИ ДАННЫХ (critique-v3, №1 и №2).
        Модель читает настройку (monthly_budget, порог подушки) и
        историю (savings-операции) одновременно, поэтому обязана
        сказать, что будет, если они разошлись:

        1. «Бюджет не менялся внутри месяца» — см. _goals_part_by_day.
        2. «Фактическая дата savings-операции совпадает с датой, по
           которой её видит кассовый календарь» — см. _collect_operations.

        Оба допущения верны в норме и нарушаются штатными действиями
        пользователя. Направления ошибки перечислены в докстрингах
        соответствующих методов — необъявленное допущение в финансовой
        модели ведёт себя как дефект, потому что тесты пишут
        по объявленному контракту.
    """

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: SQLAlchemy сессия для работы с БД.
        """

    def get_money_layers(
        self,
        user_id: int,
        reference_date: date | None = None,
    ) -> MoneyLayersData:
        """Строит модель слоёв на окно 45 дней от reference_date.

        Args:
            user_id: ID пользователя.
            reference_date: Дата отсчёта (по умолчанию date.today()).

        Returns:
            MoneyLayersData: Дни окна, срез «сегодня», минимум окна,
                платежи, вехи целей. Все ORM-объекты материализованы —
                результат безопасен после закрытия сессии.

        Note:
            Никогда не бросает при отсутствии данных — возвращает
            корректную модель с is_empty=True (FR-6). Сбои частей
            (бюджет целей, подушка, цели) деградируют fail-open с
            логом logger.opt(exception=True) (NFR-2) и выставляют
            degraded=True, чтобы UI не показал заниженные числа как
            достоверные. Сбой calculate_daily_balances не глотается —
            без остатка модели нет.
        """

    # --- Приватные шаги ---

    def _horizons(self, reference_date: date) -> Horizons:
        """Три границы модели: сбор операций, ось, слой «Платежи».

        Границ три, а не две (в v2 их было две, и данных за границей
        месяца было нечем считать — critique-v2, №6):

        * collect_start = 1-е число месяца reference_date. Единственный
          сбор операций начинается ОТ НАЧАЛА МЕСЯЦА, а не от сегодня,
          потому что consumed(reference_date) по формуле резерва —
          это savings-операции в [month_start, reference_date], то есть
          в том числе УЖЕ ПРОШЕДШИЕ дни текущего месяца (взнос 10-го
          при сегодня 22-м).
        * window_end = reference_date + WINDOW_DAYS - 1 (ось графика).
        * payments_end = последний день месяца reference_date (C-5) —
          применяется ТОЛЬКО как арифметический фильтр суффиксной
          суммы слоя «Платежи», сбор операций им не ограничен.

        Returns:
            Horizons: (collect_start, window_end, payments_end).
        """

    def _collect_operations(
        self, user_id: int, collect_start: date, window_end: date
    ) -> tuple[list[UpcomingPayment], dict[date, Decimal]]:
        """ОДИН сбор операций на весь диапазон — платежи + savings.

        Один вызов CalendarService.get_all_transactions_for_period
        (collect_start .. window_end) обслуживает и слой «Платежи»,
        и формулу резерва. Второго вызова нет (NFR-1).

        Классификация повторяет DashboardService._get_daily_income_expense
        (dashboard_service.py:476-545):
          * expense / savings_reserve / savings_contribution → платёж
            на amount;
          * adjustment с Decimal(amount) < 0 → платёж на abs(amount)
            (знак хранится в самом amount: ReconciliationService
            создаёт транзакцию с amount=difference, которая может быть
            отрицательной, reconciliation_service.py:131-135;
            get_all_transactions_for_period сериализует amount=str(txn.amount),
            calendar_service.py:803/:849 — знак сохраняется);
          * income / transfer → не платёж.
        Пропущенные (is_skipped=True) отбрасываются — их нет и в балансе.

        КЛЮЧЕВАНИЕ savings_by_date — ПО ФАКТИЧЕСКОЙ ДАТЕ ОПЕРАЦИИ
        (critique-v3, №2). Ключ — TransactionInfo['date'], то есть
        Transaction.transaction_date для реальных строк и instance_date
        для виртуальных. НЕ original_date. Словарь НЕ фильтруется
        по границам окна: он может содержать даты за window_end
        (и, теоретически, до collect_start).

        Почему так может получиться. RecurringService
        .get_instances_with_exceptions(user_id, start, end):
          * отбирает exceptions по original_date в [start, end]
            (get_exceptions_for_template, recurring_service.py:390-393),
          * подставляет их вместо виртуального инстанса по ключу
            (template_id, instance_date) (:704-710),
          * а вызывающий раскладывает их по transaction_date
            (calendar_service.py:845).
        У перенесённого exception original_date и transaction_date
        не совпадают, поэтому операция попадает в результат с датой,
        которая может лежать вне запрошенного диапазона.

        ВАЖНО: ту же самую выборку с той же семантикой использует
        расчёт баланса (_get_recurring_daily_changes → тот же
        get_instances_with_exceptions, раскладка по transaction_date,
        calendar_service.py:353-357). Правила отбора у нас и у баланса
        ОДИНАКОВЫ — расхождение возможно только из-за разных
        диапазонов вызова, и разобрано в докстринге _goals_part_by_day.

        Достижимость переноса (проверено grep'ом): параметр
        create_exception(new_date=...) (recurring_service.py:405)
        не имеет ни одного вызывающего — все три call-site
        (budget_reservation_service.py:294, :916,
        transaction_modals.py:1163) передают только original_date.
        Расхождение достижимо двухшаговым путём UI: exception
        создаётся с совпадающими датами, затем пользователь меняет
        дату в модале правки операции — TransactionService
        .update_transaction присваивает transaction_date и
        original_date НЕ трогает (transaction_service.py:236-243).

        Returns:
            tuple: (payments, savings_by_date), где
                payments — расходные операции с датой >= reference_date
                    (прошедшие дни месяца в слой «Платежи» не входят:
                    они уже вычтены из balance);
                savings_by_date — {ФАКТИЧЕСКАЯ дата: Σ savings_reserve +
                    savings_contribution} по всему собранному материалу,
                    включая прошедшие дни месяца и даты за window_end.
                    Ровно эти суммы CalendarService вычитает из баланса
                    (_get_daily_changes :270-283 для обычных,
                    _get_recurring_daily_changes :426-437 для recurring
                    и exceptions) — потому формула резерва и не двоится.
        """

    def _payments_tail_by_day(
        self,
        payments: list[UpcomingPayment],
        window_dates: list[date],
        payments_end: date,
    ) -> dict[date, Decimal]:
        """Суффиксные суммы платежей: {D: Σ платежей в (D, payments_end]}.

        Строго «после D»: платежи с датой ровно D уже вычтены из
        forecast_balance(D) кассовым календарём — иначе двойной счёт.
        Даёт «таяние» (FR-1.d): монотонно не растёт, payments(payments_end)
        == 0 и payments(D) == 0 для всех D > payments_end (C-5 видимо).
        Один проход справа налево, O(len(window_dates) + len(payments)).
        """

    def _goals_part_by_day(
        self,
        savings_by_date: dict[date, Decimal],
        window_dates: list[date],
        monthly_budget: Decimal,
    ) -> dict[date, Decimal]:
        """Бюджет целей, ещё лежащий в остатке на день D — ЕДИНАЯ формула.

        Для каждого дня D окна (месяц берётся ПО ДНЮ D, никакого
        наследования базы через границу месяца — critique-v2, блокер №2):

            consumed(D)  = Σ savings_by_date[d], d в [month_start(D), D]
            committed(D) = Σ savings_by_date[d], d в (D, month_end(D)]
            goals(D)     = max(0, monthly_budget − consumed(D) − committed(D))

        Смысл слагаемых:
          * consumed(D) — savings-операции, уже вычтенные из balance(D)
            кассовым календарём. Их нельзя держать в синем слое: денег
            в остатке нет.
          * committed(D) — savings-операции, которым ещё предстоит уйти
            в пределах месяца дня D. Они лежат в слое «Платежи»
            (та же операция — тот же список), поэтому вычитаются, чтобы
            не удвоиться.
        Каждая операция попадает РОВНО в одно слагаемое — по своей дате
        относительно D. Двойного вычитания нет ни в одном режиме
        резервирования: формула вообще не знает о режиме.

        Note:
            Суммирование НЕ ограничено границами окна (critique-v3, №2):
            committed(D) считает до month_end(D) включительно, даже если
            month_end(D) > window_end. Savings-операция, чья фактическая
            дата лежит за правым краем окна, но внутри месяца дня D, —
            это реальное «ещё предстоит уйти в этом месяце», и её учёт
            уменьшает goals_part(D), то есть НЕ завышает «Свободно».
            savings_by_date такие ключи содержит (см. _collect_operations),
            и отбрасывать их нельзя.

        Note:
            Для D за границей месяца reference_date данные есть:
            сбор операций идёт до window_end (см. _horizons). В v2 этой
            ветке формулы не было чем считать (critique-v2, №6).

        Note:
            Прошлые месяцы в окно не попадают (окно начинается сегодня),
            поэтому month_start(D) >= collect_start для всех D окна,
            КРОМЕ вырожденного случая reference_date == 1-е число, где
            они совпадают. Данных всегда достаточно.

        Note:
            ДОПУЩЕНИЕ «БЮДЖЕТ НЕ МЕНЯЛСЯ ВНУТРИ МЕСЯЦА»
            (critique-v3, №1; решение владельца п. 3в).

            monthly_savings_budget — ОДНА настройка на все месяцы
            (users.monthly_savings_budget, database.py:99), месячной
            истории бюджета в схеме нет (C-4). Поэтому budget(D) ==
            monthly_budget для любого D.

            При этом суммы savings-операций месяца зафиксированы
            НА МОМЕНТ ПРОШЛЫХ ОПЕРАЦИЙ и при смене бюджета не
            переписываются: BudgetReservationService
            .sync_template_amount (:808-839) обновляет ТОЛЬКО
            template.amount и существующие exceptions не трогает;
            recalculate_current_month_exception вызывается из путей
            взноса, а не из пути смены бюджета, и содержит guard
            if reserve_date < date.today(): return (:263-265).

            Следствие: формула отражает ТЕКУЩУЮ НАСТРОЙКУ, а не
            историю. Два параметра поведения:

            * бюджет УМЕНЬШЕН после частичного взноса (обещано целям
              больше текущего бюджета): consumed + committed >
              monthly_budget, и max(0, …) обрезает перерасход
              ДО НУЛЯ. Признака «обещано сверх бюджета» в UI НЕТ —
              решение владельца п. 3в: цифры остаются корректными
              (деньги действительно сидят в слое «Платежи» и уйдут),
              теряется только информация о превышении. Различие
              «goals_part = 0, потому что бюджет исчерпан» и
              «= 0, потому что обещано больше бюджета» модель
              сознательно НЕ различает: жизненный цикл целей и
              превышение — отдельный открытый вопрос ROADMAP №9.
            * бюджет УВЕЛИЧЕН после полного взноса: goals_part
              завышается на разницу, «Свободно» ЗАНИЖАЕТСЯ.
              Направление безопасное (показать меньше свободных
              денег, чем есть, не опасно — та же асимметрия, что
              для правого края окна).

            Оба параметра — в блоке A шага 6 с числами по трём слоям.

        Note:
            ОГРАНИЧЕНИЕ: перенесённый exception внутри текущего месяца
            (critique-v3, №2, случай 3). Если savings-exception
            перенесён с даты ДО reference_date на дату внутри окна,
            наш сбор его видит (original_date >= collect_start), а
            прогнозный остаток — нет: _get_recurring_daily_changes
            (ref .. window_end) его не отбирает (original_date < ref),
            а _calculate_recurring_before_date (calendar_service.py
            :396-406) считает только income/expense и savings
            ИГНОРИРУЕТ. Направление ошибки: лишнее слагаемое
            уменьшает goals_part → уменьшает reserve → «Свободно»
            ЗАВЫШАЕТСЯ. Инвариант AC-3 это не поймает (он слеп
            к раскладке). Правка требует исправления
            _calculate_recurring_before_date, что запрещено C-3 —
            ограничение записано в осадок решений одним пунктом
            с латентным дефектом, чьим следствием является.
            Симметричный случай (original_date < collect_start,
            дата внутри окна) расхождения НЕ даёт: его не видит
            ни наш сбор, ни баланс — обе стороны используют одну
            выборку get_instances_with_exceptions.
        """

    def _split_day(
        self, balance: Decimal, payments: Decimal, reserve: Decimal
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Каскад сжатия слоёв — ЕДИНСТВЕННЫЙ механизм обрезки (п. 3б).

        1. free = balance − payments − reserve; если free >= 0 — готово.
        2. Иначе free = 0, дефицит гасится сначала из reserve
           (до нуля), затем из payments.
        3. Если balance < 0 — free = balance (отрицательное),
           payments = reserve = 0.

        Порядок гашения (сначала reserve, потом payments) фиксирован
        и продуктово осмыслен: «сначала вы залезаете в подушку, и лишь
        потом не хватает на обязательные платежи».

        Второго механизма сжатия нет: min(threshold, balance) из v2
        убран из cushion_part решением владельца (п. 3б) — два
        независимых сжатия одного слоя давали неопределённый порядок
        применения и «дышащую» синюю полосу без объяснения
        (critique-v2, №4).

        Returns:
            tuple[Decimal, Decimal, Decimal]: (free, payments, reserve),
                сумма которых равна balance при любом входе.
        """

    def _today_slice(self, days: list[DayLayers]) -> TodaySlice:
        """Срез первого дня окна (== reference_date) для шапки.

        Вердикта не считает: уровней состояния в куске 1 нет
        (решение владельца п. 3а). Только четыре числа разбора.
        """

    def _window_min_free(self, days: list[DayLayers]) -> tuple[Decimal, date]:
        """Минимум слоя «Свободно» по ВСЕМУ окну — для маркера (FR-3.e).

        Минимум ищется по всем 45 дням, а не по остатку месяца:
        просадка после зарплаты (эскиз: 4 сентября) обязана попадать
        в кадр. При равенстве берётся первая дата.

        Note:
            Величина используется ТОЛЬКО графиком (маркер минимума).
            Оценочного вывода из неё не делается — вердикт снят
            решением владельца.
        """

    def _goal_milestones(
        self, user_id: int, reference_date: date, window_end: date
    ) -> list[GoalMilestone]:
        """Вехи активных целей: в окне + ближайшая за его краем.

        Материализует поля ORM-объектов Goal (включая вычисляемое
        property progress_percentage) в GoalMilestone ВНУТРИ сессии —
        GoalService.get_all_by_user возвращает list[Goal], и обращение
        к нему после закрытия сессии даст DetachedInstanceError.

        Returns:
            list[GoalMilestone]: до MAX_MILESTONES_IN_WINDOW вех внутри
                окна (ближайшие по target_date) + не более одной
                с beyond_window=True (ближайшая после window_end).
        """

    def _is_empty(
        self,
        days: list[DayLayers],
        savings_by_date: dict[date, Decimal],
        payments: list[UpcomingPayment],
        has_recurring_templates: bool,
        starting_balance: Decimal,
    ) -> bool:
        """«Нет данных вообще» — БЕЗ отдельного запроса (critique-v2, №8).

        Критерий: starting_balance == 0 И recurring-шаблонов нет
        И в диапазоне сбора нет ни платежей, ни savings-операций
        И forecast_balance каждого дня окна == 0.

        Почему это корректно для AC-5 (чистая база): на чистой базе
        все четыре условия истинны по построению — операций нет,
        шаблонов нет, starting_balance = 0, значит и балансы нулевые.

        Почему это не ломает window_is_flat: у пользователя с историей
        и пустым окном forecast_balance(D) != 0 (накопленный остаток) —
        либо starting_balance != 0, либо есть шаблоны. Такой
        пользователь получает is_empty=False, window_is_flat=True
        и ВИДИТ график (плоская стопка), а не «Добавьте первую
        операцию». Единственный ложноположительный сценарий —
        история, которая свела остаток ровно в 0.00 и не оставила
        ни одного шаблона, при starting_balance == 0 и полностью
        пустом окне; для него пустое состояние с кнопкой «Сверка»
        всё равно осмысленно (показывать плоскую нулевую стопку
        не информативнее).

        Note:
            Флаг users.first_launch для критерия не годится:
            OnboardingService.skip() сбрасывает его в False, не создавая
            данных (onboarding_service.py:168-182).

        Note:
            has_recurring_templates берётся из уже выполненной работы
            (наличие виртуальных инстансов в собранном диапазоне ИЛИ
            один лёгкий exists-запрос через RecurringService, если
            диапазон пуст) — отдельного count(transactions) по всей
            истории, как в v2, нет.
        """
```

```python
# app/services/cushion_service.py — ДОБАВЛЯЕМЫЙ метод

    def get_threshold_amount(self, user_id: int) -> Decimal:
        """Порог подушки без пересчёта баланса.

        Лёгкая альтернатива get_settings() для потребителей, которым
        нужен только порог: get_settings() внутри вызывает
        _get_current_balance() → CalendarService.get_balance_on_date(),
        а тот полностью обходит recurring-историю от самого раннего
        шаблона (calendar_service.py:364-407). Для threshold_amount
        баланс не нужен вовсе — формула target * percent / 100
        (см. get_settings, строки 104-107; баланс участвует только
        в current_amount и progress, :100 и :113-118).

        Args:
            user_id: ID пользователя.

        Returns:
            Decimal: Порог подушки; Decimal("0") если пользователь
                не найден или подушка не настроена (target == 0).
                Не бросает ValidationError — отсутствие пользователя
                на чистой базе штатно (в отличие от _get_user).
        """
```

```python
# app/components/dashboard.py — новые/изменённые строители и точка загрузки

def build_free_header(
    data: MoneyLayersData,
    profile: UserProfile,
) -> html.Div:
    """Шапка «Свободно сегодня: N ₽» (FR-2, FR-5).

    Состав слева: метка «Свободно сегодня», сумма (tabular-nums),
    разбор «баланс {balance} − платежи {payments} − резерв {reserve}».
    Справа: аватар-эмодзи + имя, кнопка «Сверка»
    (id="open-recon-from-dashboard-header-btn"), шестерёнка
    (id="dashboard-settings-cog" → модал профиля).

    ПРИВЕТСТВИЯ НЕТ (решение владельца п. 3г, 2026-08-24): главное
    место отдано цифре, не вежливости. Состав справа воспроизводит
    эскиз буквально (.visual/finfocus-panel-dashboard/v3.html:415-418
    — аватар-эмодзи, имя, шестерёнка; приветствия в эскизе нет вовсе).
    Хелпер _build_greeting_text() из шапки НЕ вызывается — он удалён
    как мёртвый код вместе с элементом dashboard-greeting.

    Вердикта НЕТ (решение владельца п. 3а): ни чипа, ни сигнальной
    шины, ни оценочной подписи, ни окраски суммы по уровню. Сумма
    рендерится нейтральным цветом текста; единственное исключение —
    отрицательное значение показывается в цвете риска, потому что
    это факт знака числа, а не оценка состояния.

    При data['degraded'] под разбором добавляется нейтральная сноска
    «часть данных недоступна, показано без бюджета целей» — деградация
    обозначена, а не выдана за достоверную цифру.

    Не дверь-переход: на контейнере нет dcc.Link, n_clicks,
    cursor:pointer (FR-2.e).

    Args:
        data: Модель слоёв из MoneyLayersService.
        profile: Профиль (name, avatar_id) из OnboardingService —
            ЕДИНСТВЕННЫЙ источник имени и аватара в шапке. Второго
            чтения профиля за рендер нет: прежний путь через
            _build_greeting_text() открывал собственную сессию
            (critique-v3, №3) и снят вместе с приветствием.

    Returns:
        html.Div с классом pnl-breaker.
    """


def build_layers_chart(data: MoneyLayersData) -> dbc.Card:
    """График полос: стопка Свободно/Платежи/Резерв по 45 дням (FR-3).

    Три go.Bar в barmode="stack" (снизу вверх: free, payments, reserve)
    по датам оси X, вертикальная линия «сегодня», маркер минимума слоя
    «Свободно» (data['min_free_date']), вехи целей аннотациями (в окне +
    стрелка за краем). Легенда Plotly отключена (showlegend=False) —
    вынесена в HTML (заметка vision-критика + FR-4).

    Args:
        data: Модель слоёв из MoneyLayersService.

    Returns:
        dbc.Card с dcc.Graph(id="dashboard-layers-chart-graph") либо
        пустым состоянием при data['is_empty'] (FR-6).
    """


def _axis_tickvals(window_dates: list[date]) -> list[date]:
    """Явные даты подписей оси X — без спорных единиц dtick.

    Берёт каждый k-й день окна, где
        k = max(1, ceil(len(window_dates) / MAX_X_TICKS)).
    Для 45 дней k = 5 → индексы 0, 5, …, 40 → 9 подписей, плюс
    принудительно добавляется window_end (последний день окна должен
    быть подписан) → 10. Число подписей НИКОГДА не превышает
    MAX_X_TICKS (critique-v3, замечание №5: прежняя формула
    round(45/11) = 4 давала 12 подписей при константе с именем
    TARGET_X_TICKS = 11 — имя обещало результат, которого функция
    не давала). Константа переименована в MAX_X_TICKS, семантика —
    потолок, и ceil делает потолок соблюдаемым по построению.

    Точное воспроизведение эскиза невозможно и не является целью:
    в v3.html 11 подписей с НЕРАВНОМЕРНЫМ шагом (22/25/28 авг,
    1/5/10/15/20/25/30 сент, 5 окт — v3.html:575-596), то есть
    семантически значимые даты. Воспроизводима только плотность.

    Заменяет _axis_dtick из v2: там докстринг обещал миллисекунды,
    а формула возвращала дни (critique-v2, №10). Plotly для оси
    type="date" принимает dtick и в миллисекундах, и строкой ("D4",
    "M1"), и обе записи легко перепутать. Явные tickvals + tickmode
    ="array" снимают неоднозначность единиц полностью.

    Args:
        window_dates: Даты окна по возрастанию (data['days'] → date).

    Returns:
        list[date]: Даты для xaxis.tickvals (первая — reference_date,
            последняя — window_end), len <= MAX_X_TICKS.
    """


def _load_dashboard_components(period_state: dict | None) -> tuple:
    """Единая точка загрузки данных и построения UI дашборда.

    Аргумент `period` УДАЛЁН из сигнатуры (было `(period, period_state)`,
    dashboard.py:1255-1258). Причина: period-switcher снимается вместе
    с callback'ом update_period_state, единственным Input которого он
    был (:1397-1408) — Store dashboard-period перестаёт обновляться,
    и аргумент навсегда получал бы дефолт "month" из layout. Мёртвый
    параметр, с которым пришлось бы спорить весь кусок 2 (critique-v2,
    №3), не заводится вовсе.

    Store dashboard-period ОСТАЁТСЯ в layout с data={"period":"month"}:
    его читает open_create_from_chart как guard. period_state
    по-прежнему передаётся — на случай, если кусок 2 вернёт выбор
    периода.

    Профиль читается ЗДЕСЬ ОДИН РАЗ (OnboardingService.get_profile)
    и передаётся в build_free_header аргументом. Прежний второй
    источник (_build_greeting_text с собственной сессией) удалён
    вместе с приветствием (решение владельца п. 3г; critique-v3, №3).

    Args:
        period_state: Данные из dcc.Store dashboard-period.

    Returns:
        tuple: (free_header, layers_chart, recent, upcoming, cushion)
            — 5 значений вместо прежних 6 (ушли cards+stats,
            пришёл free_header).
    """
```

**Состав Output'ов после правки:**

| Callback | Outputs (в порядке) / Inputs |
|---|---|
| `load_dashboard_data` | Outputs: `dashboard-free-header.children`, `dashboard-layers-chart.children`, `dashboard-recent-transactions.children`, `dashboard-upcoming-transactions.children`, `dashboard-cushion-card.children` — **5** (было 7). Output `dashboard-greeting` удаляется. Inputs: `url.pathname`, `profile-updated.data` (**`period-switcher.value` снят**). State: `dashboard-period.data`. Сигнатура становится `(pathname, profile_updated, period_state)`. Ветка ошибки: `(error_alert,) * 5` |
| `refresh_dashboard_after_crud` | те же 5 с `allow_duplicate=True` (было 6); сигнатура не меняется, но `period` больше не выводится из Store |
| `update_period_state` | **удаляется** вместе с `period-switcher` |
| `open_create_from_chart` | Input → `dashboard-layers-chart-graph.clickData`; guard по `period_state` сохраняется; дата берётся из `point["x"]` (ISO-строка) вместо `int(point["x"])` |

**Судьба `dashboard-greeting` и `_build_greeting_text` (решение владельца п. 3г).** Элемент (`:108-112`), Output (`:1348`) и **сам хелпер** (`:82-91`) удаляются. Приветствие в шапку **не переносится** — его на дашборде больше нет. Основание: решение владельца («главное место отдано цифре, не вежливости») + эскиз, где приветствия нет. Grep подтвердил, что вызывающих у хелпера ровно два и оба снимаются, значит хелпер становится мёртвым кодом → удаляется вместе с `TestBuildGreetingText` и импортом на `:20` теста. Дух протоколов 0024/0026 не нарушен: отдельного Output/callback'а на приветствие не появляется, а подписка на `profile-updated` сохранена у обоих callback'ов (тесты `:50`, `:57` не трогаются) — имя и аватар в шапке обновляются после правки профиля тем же Input'ом.

## Модель данных

Схема БД не меняется (C-4) — проверено по коду, всё сырьё есть.

| Что нужно модели | Откуда берётся (проверено) | Достаточность |
|---|---|---|
| Прогнозный остаток по дням окна | `CalendarService.calculate_daily_balances` (`users.starting_balance` + `transactions` + recurring, `calendar_service.py:100-167`) | достаточно |
| Платежи и savings-операции всего диапазона | **один** `CalendarService.get_all_transactions_for_period` → `TransactionInfo` (`amount` строкой **со знаком** — `str(txn.amount)`, :803/:849; есть `description`, `category_name`, `is_recurring`, `is_exception`, `is_skipped`; `date` — **фактическая** дата операции) | достаточно, с объявленным допущением о согласованности дат (см. `_collect_operations`) |
| Порог подушки | `users.cushion_target`, `users.cushion_threshold_percent` через новый `CushionService.get_threshold_amount` | достаточно (колонки суммы порога в схеме нет — только процент + булев флаг, `database.py:105-107`) |
| Месячный бюджет целей | `users.monthly_savings_budget` (`database.py:99`) через `BudgetReservationService.get_settings()['monthly_budget']` | достаточно, с объявленным допущением «бюджет не менялся внутри месяца» (см. `_goals_part_by_day`) |
| ~~Режим резервирования~~ | **не требуется** — формула не ветвится по режиму | — |
| ~~`used_budget` / материализованный резерв~~ | **не требуется** — `get_budget_progress` и `_get_reserve_sum_for_month` из пути модели ушли | — |
| Вехи целей | `goals.target_date/target_amount/current_amount/status` через `GoalService.get_all_by_user(ACTIVE)` (`target_date` NOT NULL, `database.py:260`) | достаточно |
| Аватар и имя для шапки | `users.avatar_id`, `users.name` через `OnboardingService.get_profile` — **один** вызов, результат передаётся в `build_free_header` аргументом (второго чтения профиля нет, см. п. 3г) | достаточно |
| Наличие recurring-шаблонов для `is_empty` | `RecurringService.get_templates_for_user` (`recurring_service.py:114-137`) — один лёгкий запрос, и то только когда собранный диапазон пуст | достаточно |
| ~~Текст приветствия~~ | **не требуется** — приветствие снято с дашборда (решение владельца п. 3г) | — |

**Вывод по C-4:** миграции не нужны, отдельного решения об изменении схемы не требуется.

### Численная трассировка формулы резерва

Единая конфигурация, если не сказано иное: `monthly_budget = 15 000`, `cushion_threshold = 30 000`, режим `fixed_date` c датой резерва 25-е (recurring `SAVINGS_RESERVE` 15 000 на 25-е каждого месяца), `reference_date = 22 августа`. Все кейсы проверены против фактического поведения кода: `_get_recurring_daily_changes` вычитает `savings_reserve`/`savings_contribution` из баланса (`calendar_service.py:426-437`); `_get_daily_changes` вычитает их же для обычных транзакций (`:270-283`) и исключает exceptions (`:230-233`), которые приходят через recurring-ветку; `get_all_transactions_for_period` возвращает и виртуальные инстансы, и exceptions вместо них (`:817-870`, `recurring_service.py:699-714`).

**Кейсы 1–9 сохранены без изменений — они независимо пересчитаны критиком по коду и подтверждены (critique-v3, сильные стороны 1–2).**

**Кейсы 1–3: `fixed_date`, доля взноса (это ровно то, на чём v2 упал).**

| # | Взнос | Что в БД | `savings_by_date` в августе | `consumed(22)` | `committed(22)` | `goals_part(22)` | Ожидание | v2 давал |
|---|---|---|---|---|---|---|---|---|
| 1 | нет | виртуальный инстанс 25 авг = 15 000 | {25 авг: 15 000} | 0 | 15 000 | max(0, 15 000−0−15 000) = **0** | 0 — бюджет ещё в слое «Платежи», уйдёт 25-го | 0 ✓ |
| 2 | **5 000** 10 авг (частичный) | exception 25 авг = 10 000 (`budget−contributions`, `budget_reservation_service.py:290-298`), транзакции взноса НЕТ (`:669-672`) | {25 авг: 10 000} | 0 | 10 000 | max(0, 15 000−0−10 000) = **5 000** | 5 000 — именно столько отдано цели и физически лежит в остатке | **0** ✗ (двойное вычитание) |
| 3 | 15 000 полностью | exception 25 авг = 0 (`max(new_reserve,0)`) | {25 авг: 0} | 0 | 0 | max(0, 15 000−0−0) = **15 000** | 15 000 — весь бюджет лежит в остатке, резерв не уйдёт | 15 000 ✓ |

Кейс 2 — тот самый интервал между вырожденными границами, на котором формула v2 врала. Новая формула даёт правильные 5 000.

**Кейсы 4–5: день относительно даты резерва (`fixed_date`, взносов нет).**

| # | D | `consumed(D)` = Σ в [1 авг, D] | `committed(D)` = Σ в (D, 31 авг] | `goals_part(D)` | Смысл |
|---|---|---|---|---|---|
| 4 | 24 авг (до резерва) | 0 | 15 000 | max(0, 15 000−0−15 000) = **0** | бюджет в оранжевом слое |
| 5 | 26 авг (после резерва) | 15 000 | 0 | max(0, 15 000−15 000−0) = **0** | резерв ушёл из баланса — синий слой его не держит |

**Кейс 6: `fixed_date`, частичный взнос, день после резерва.** Взнос 5 000 сделан 10 авг, exception 25 авг = 10 000. D = 26 авг: `consumed` = 10 000, `committed` = 0 → `goals_part = 5 000`. Верно: 10 000 ушли резервом, 5 000 остались в остатке.

**Кейсы 7–8: `from_balance` (взнос создаёт `SAVINGS_CONTRIBUTION`, recurring-шаблона резерва нет).**

| # | Взнос | `savings_by_date` | D | `consumed(D)` | `committed(D)` | `goals_part(D)` | Ожидание | v2 давал |
|---|---|---|---|---|---|---|---|---|
| 7 | 5 000 **10 авг** (прошлое) | {10 авг: 5 000} | 22 авг | 5 000 | 0 | max(0, 15 000−5 000−0) = **10 000** | 10 000 — остаток бюджета ещё не тронут | 10 000 ✓ |
| 8 | 5 000 **28 авг** (**будущая** дата, `goal_service.py:126-131`) | {28 авг: 5 000} | 22 авг | 0 | 5 000 | max(0, 15 000−0−5 000) = **10 000** | 10 000 — 5 000 в слое «Платежи», 10 000 в синем | **5 000** ✗ |

**Кейс 9: граница месяца и правый край окна (это блокер №2 v2).** `fixed_date`, резерв 15 000 25-го каждого месяца, взносов нет, зарплата 120 000 5-го, `reference_date = 22 авг`, `window_end = 5 окт`. `savings_by_date` = {25 авг: 15 000, 25 сент: 15 000}.

| D | месяц D | `consumed(D)` | `committed(D)` | `goals_part(D)` | v2 давал | Комментарий |
|---|---|---|---|---|---|---|
| 22 авг | авг | 0 | 15 000 (25 авг) | **0** | 0 | бюджет августа в «Платежах» |
| 31 авг | авг | 15 000 (25 авг) | 0 | **0** | **15 000** ✗ | резерв августа исполнен |
| 1 сент | сент | 0 | 15 000 (25 сент) | **0** | 15 000 ✗ | новый месяц; оранжевый слой при этом 0 (C-5) |
| 24 сент | сент | 0 | 15 000 | **0** | 15 000 ✗ | |
| 26 сент | сент | 15 000 (25 сент) | 0 | **0** | **30 000** ✗ | v2 накапливал оба исполненных резерва |
| 30 сент | сент | 15 000 | 0 | **0** | 30 000 ✗ | |
| 5 окт | окт | 0 | 0 (резерв 25 окт вне окна и вне диапазона сбора) | **15 000** | 30 000 ✗ | бюджет октября целиком в остатке — правильно держать в синем |

`goals_part` на 45-дневном окне не накапливается: максимум по окну равен `monthly_budget`. Особый случай 5 окт: `committed(5 окт) = 0`, потому что резерв 25 октября лежит за `window_end` и в диапазон сбора не входит — то же ограничение горизонта, что C-5 для платежей, и оно консервативно в **безопасную** сторону.

**НОВЫЕ КЕЙСЫ v4 — смена бюджета внутри месяца (🟡№1, решение владельца п. 3в).**

Конфигурация: `cushion_threshold = 30 000`, `reference_date = 22 августа`.

| # | Сценарий | Настройка на 22 авг | `savings_by_date` | `consumed(22)` | `committed(22)` | `goals_part(22)` | `reserve_configured(22)` | Что видит пользователь | Направление ошибки |
|---|---|---|---|---|---|---|---|---|---|
| **10** | **Бюджет УМЕНЬШЕН после частичного взноса.** Был 15 000; взнос 5 000 сделан 10 авг → exception 25 авг = 10 000 (`budget − contributions`); 20 авг бюджет снижен до **8 000** — `sync_template_amount` (`:808-839`) поменяла только `template.amount`, exception остался 10 000 | `monthly_budget = 8 000` | {25 авг: 10 000} | 0 | 10 000 | max(0, 8 000 − 0 − 10 000) = **0** (обрезано с −2 000) | 30 000 + 0 = **30 000** | Синий = 30 000 (только подушка); 10 000 видны в оранжевом слое и уйдут 25-го. **Признака «обещано сверх бюджета» НЕТ** (решение владельца п. 3в) | Числа корректны: деньги действительно в «Платежах». Потеряна только информация о превышении на 2 000 |
| **11** | **Бюджет УВЕЛИЧЕН после полного взноса.** Был 8 000, режим `from_balance`, взнос 8 000 сделан 10 авг (`SAVINGS_CONTRIBUTION`); 20 авг бюджет поднят до **20 000** | `monthly_budget = 20 000` | {10 авг: 8 000} | 8 000 | 0 | max(0, 20 000 − 8 000 − 0) = **12 000** | 30 000 + 12 000 = **42 000** | Синий = 42 000: модель держит 12 000 как «ещё не отданный бюджет августа». Физически эти 12 000 обещаны только настройкой | «Свободно» **занижено** на 12 000 — БЕЗОПАСНАЯ сторона (та же асимметрия, что для кейса 5 окт) |

Оба кейса — не арифметическая ошибка формулы, а следствие допущения «`monthly_budget` согласован с суммами savings-операций месяца». Допущение объявлено в докстринге `_goals_part_by_day`; оба параметра — в блоке A шага 6 с числами по трём слоям.

**НОВЫЙ КЕЙС v4 — перенесённый exception (🟡№2).**

Конфигурация: `monthly_budget = 15 000`, `cushion_threshold = 30 000`, `fixed_date`, резерв 25-го, `reference_date = 22 августа`, `window_end = 5 октября`, `collect_start = 1 августа`. Пользователь перенёс инстанс резерва **25 сентября на 8 октября** (двухшаговый путь: exception создан с совпадающими датами → дата изменена в модале правки; `original_date = 25 сент`, `transaction_date = 8 окт`).

| # | D | Что в `savings_by_date` | `consumed(D)` | `committed(D)` | `goals_part(D)` | v3 давал | Комментарий |
|---|---|---|---|---|---|---|---|
| **12a** | 30 сент | {25 авг: 15 000, **8 окт: 15 000**} — ключ 8 окт **за `window_end`**, но словарь не фильтруется (v4) | 0 (в сентябре savings нет) | 0 — `month_end(30 сент)` = 30 сент, 8 окт **не** попадает | **15 000** | 15 000 (тот же результат) | Бюджет сентября никуда в сентябре не уйдёт — правильно держать в синем |
| **12b** | 5 окт (правый край окна) | то же | 0 (в октябре до 5-го savings нет) | **15 000** (8 окт ≤ `month_end(5 окт)` = 31 окт) | max(0, 15 000 − 0 − 15 000) = **0** | **15 000** ✗ | v3 отбросил бы ключ за `window_end` и показал бы 15 000 в синем, хотя эти деньги уйдут 8 октября. v4 учитывает — «Свободно» не завышено |

Кейс 12b — ровно тот вход, на котором `committed(D)` в v3 недосчитывался. Правка (снятие фильтра по `window_end`) даёт корректный 0 и **не завышает** «Свободно». Тест — в блоке F шага 6 с числами по трём слоям.

Симметричный случай (перенос **внутри** текущего месяца с даты до `reference_date`) даёт расхождение, которое модель исправить не может — оно живёт в `_calculate_recurring_before_date` (C-3). Зафиксировано ограничением в докстринге `_goals_part_by_day` и в осадке решений; направление — «Свободно» завышается.

**Проверка примера эскиза (сходимость AC-3 и главного числа).** Остаток 84 500 на 22 авг, платежи до конца месяца 37 500 (включая резерв 15 000 на 25-е), бюджет целей 15 000, порог подушки 30 000:

| D | balance | payments (D, 31 авг] | reserve_configured | reserve (факт) | free |
|---|---|---|---|---|---|
| 22 авг | 84 500 | 37 500 | 30 000 + 0 = 30 000 | 30 000 | 17 000 |
| 25 авг | 54 500 | 7 500 | 30 000 + 0 = 30 000 | 30 000 | 17 000 |
| 28 авг | 48 300 | 1 300 | 30 000 + 0 = 30 000 | 30 000 | 17 000 |
| 31 авг | 47 000 | 0 | 30 000 + 0 = 30 000 | 30 000 | 17 000 |
| 5 сент (+120 000) | 167 000 | 0 | 30 000 + 0 = 30 000 | 30 000 | 137 000 |

Сумма слоёв == balance на каждой строке (AC-3); `payments` тает до 0 (FR-1.d) и остаётся 0 за 31 августа (C-5 видимо). Отличие от арифметики эскиза (32 000): recurring-резерв целей физически входит в список операций и сидит в оранжевом слое; корректный разбор — 84 500 − 37 500 − 30 000 = 17 000. Расхождение фиксируется явно в осадке решений.

**Пример сжатой полосы (проверка п. 3б, честная подпись).** Порог подушки 30 000, бюджет целей 0, `balance(4 сент) = 18 000`, `payments(4 сент) = 0`:
- `reserve_configured = 30 000`, `reserve_raw = 30 000`;
- `_split_day(18 000, 0, 30 000)`: `free = −12 000 < 0` → `free = 0`, дефицит 12 000 гасится из reserve → `reserve = 18 000`, `payments = 0`;
- `DayLayers`: `free = 0`, `payments = 0`, `reserve = 18 000`, `reserve_configured = 30 000`, сумма = 18 000 == balance ✓;
- тултип: «В этот день на резерв остаётся 18 000 ₽ из 30 000 ₽ — вы залезаете в подушку».

## Обработка ошибок

Четыре уровня, по образцу `PurchaseRecommendationService.get_safe_dates_map` (`purchase_recommendation_service.py:72-83` — fail-open + `logger.opt(exception=True)`, идиома протокола 0027: loguru игнорирует `exc_info`).

1. **Штатное отсутствие данных — тихий дефолт, без лога.** Пользователь не найден / подушка не настроена → `get_threshold_amount` возвращает `Decimal("0")` без исключения и без варнинга. `BudgetReservationService.get_settings` для отсутствующего пользователя сам возвращает дефолт с `monthly_budget = 0` (`:65-72`) — штатный путь чистой базы, шума не создаём.

2. **Сбой компонента — fail-open + лог с трейсбеком + `degraded=True`.** Сбой чтения бюджета → `monthly_budget = 0` → `goals_part = 0`; сбой `GoalService` → `milestones = []`; неожиданный сбой `get_threshold_amount` → `cushion_threshold = 0`. Каждый — `logger.opt(exception=True).warning(...)` (NFR-2). Инвариант AC-3 сохраняется.
   **Направление деградации обозначается в UI, а не только в логах.** `goals_part = 0` или `cushion_threshold = 0` означает, что весь резерв уходит в «Свободно» — деградация в **опасную** сторону. Решение: флаг `degraded` в модели, в шапке — нейтральная сноска под разбором «часть данных недоступна, показано без бюджета целей», и **отсутствие** утверждающей сноски слоя «Резерв» в тултипе. Число не подменяется и не скрывается. Тест: monkeypatch-падение чтения бюджета → `degraded is True` и сноска в DOM.

3. **Сбой `calculate_daily_balances` не глотается** — без остатка модели нет, исключение уходит в callback (уровень 5).

4. **Границы горизонтов.**
   - `reference_date` = последний день месяца → `payments_end == reference_date`, `payments(D) == 0` для всех дней окна (модель валидна). `collect_start` = 1-е число того же месяца, `consumed` считается корректно.
   - `reference_date` = 1-е число → `collect_start == reference_date`, окно и диапазон сбора совпадают слева.
   - Февраль / 31-е / переход через год: `monthrange` в `_horizons` и в `_goals_part_by_day`; окно 45 дней всегда пересекает минимум две границы месяца, а при `reference_date` в конце месяца — три (25 дек → окно до 7 фев). Тесты на все три.
   - **Ключ `savings_by_date` за `window_end`** (перенесённый exception, 🟡№2): не отбрасывается; `committed(D)` учитывает его при `key <= month_end(D)`. Ключ до `collect_start` (перенос назад) арифметически не попадает ни в `consumed(D)`, ни в `committed(D)` ни для одного D окна (`month_start(D) >= collect_start`) — молча игнорируется, что согласовано с балансом (см. случай 2 в разборе).
   - `calculate_daily_balances(ref, ref+44)` — `start < end` всегда, `ValueError` (`calendar_service.py:122-126`) недостижим.
   - Окно 45 дней укладывается в `MAX_FORECAST_DAYS = 366` (`recurring_service.py:25`).

5. **Callback'и Dash.** `load_dashboard_data`: `try/except` → `dbc.Alert("Не удалось загрузить данные...")` во все 5 Output'ов; `logger.error(f"...{e}")` (`dashboard.py:1389`) заменяется на `logger.opt(exception=True).error(...)` — сейчас трейсбека нет (NFR-2). `refresh_dashboard_after_crud` (`:1451`) — то же, затем `PreventUpdate`. **Третий «пустой» `exc_info=True` в `_build_greeting_text` (`:90`) не правится, а исчезает** вместе с удаляемым хелпером (решение владельца п. 3г) — 🟢№4 закрывается физически, отдельной оговорки в NFR-2 не требуется.

**Пустое состояние (FR-6, AC-5):**

- `is_empty=True` ⟺ критерий `_is_empty` (без запроса). Шапка рендерит `_build_header_empty_state()` («Пока нечего показать» + «Добавьте первую операцию или сверьте баланс» + кнопка «Сверка»), график — `_build_chart_empty_state()`: **вместо `dcc.Graph` отдаётся `html.Div`**, Plotly не вызывается → оси −1..1 и «50.001k» физически невозможны (AC-5).
- `window_is_flat=True` (данные есть, в окне ни одной операции) — **график рисуется**: плоская стопка на уровне остатка. Пустое состояние здесь **не** подменяет график. Отдельный тест.
- Для непустых, но малых данных оси фиксируются: `yaxis=dict(rangemode="tozero", tickformat=",.0f", separatethousands=True)`, `xaxis=dict(type="date", tickmode="array", tickvals=_axis_tickvals(...), tickformat="%-d %b", tickangle=0)`.

**Безопасность.** Тултип легенды рендерит пользовательский `description` только через `html.Div`/`html.Span` — Dash экранирует текст. `dangerously_allow_html` и `dcc.Markdown` в новых путях запрещены (правило реализации).

## План реализации

Оценки — в человеко-часах для одного разработчика, знакомого с проектом. Итого **≈ 31.5–37.5 ч** (v3: 31–37; шаг 6 +0.5 ч на три новых параметра/теста, шаг 13 +0.5 ч на удаление класса тестов, шаг 8 −0.5 ч на снятии приветствия).

| # | Шаг | Оценка | Зависит от |
|---|---|---|---|
| 1 | `app/schema/money_layers.py` — TypedDict'ы (`DayLayers`, `UpcomingPayment`, `GoalMilestone`, `TodaySlice`, `MoneyLayersData`), `Horizons`, `LayerKey`, константы (`WINDOW_DAYS`, `MAX_MILESTONES_IN_WINDOW`, **`MAX_X_TICKS`**, `LAYER_COLORS`, `LAYER_LABELS`) + реэкспорт в `app/schema/__init__.py`. Вердикт-типов и `DIP_*` НЕ создавать (п. 3а) | **1.5 ч** | — |
| 2 | `CushionService.get_threshold_amount()` + тесты в `tests/test_cushion_service.py` (порог по проценту, `target=0`, отсутствующий пользователь, monkeypatch-assert «`calculate_daily_balances` не вызывался») | **1.5 ч** | — |
| 3 | `app/services/money_layers_service.py` — каркас: `_horizons`, `_forecast_balances`, `_collect_operations` (**один** вызов, две выходные структуры, **без фильтра `savings_by_date` по окну** — 🟡№2), `_payments_tail_by_day`, `_split_day`, `_today_slice`, `_window_min_free`, `_is_empty` + реэкспорт в `app/services/__init__.py` | **4.5 ч** | 1, 2 |
| 4 | `_goals_part_by_day` — **единая** формула от даты D. Два префиксных/суффиксных прохода по `savings_by_date` в разрезе месяцев окна; `committed(D)` суммирует **до `month_end(D)` включительно, не обрезая по `window_end`** (🟡№2 — один дополнительный `if` при построении суффиксных сумм). Докстринг с **двумя объявленными допущениями** и ограничением (п. 3в + 🟡№2) | **2.5 ч** | 3 |
| 5 | `_goal_milestones` (материализация в сессии, ≤`MAX_MILESTONES_IN_WINDOW` в окне + одна `beyond_window`) | **1.5 ч** | 3 |
| 6 | `tests/test_money_layers_service.py`. **Блок A — «таблица ожидаемых слоёв» (обязателен)**: `@pytest.mark.parametrize` с явными **числами по всем трём слоям** для матрицы `режим (fixed_date / from_balance) × доля взноса (0 / частичный / полный бюджет) × позиция дня (до даты резерва / день резерва / после / последний день месяца / первый день следующего / после резерва следующего месяца / правый край окна)`. Обязательно включены кейсы 1–9 (в т.ч. кейс 2 → `goals_part == 5 000`; кейс 8 → `10 000`; кейс 9 → 31 авг/26 сент/30 сент → 0) **плюс ДВА новых параметра «смена бюджета внутри месяца»** (🟡№1, п. 3в): кейс 10 — бюджет уменьшен после частичного взноса → `goals_part == 0`, `reserve_configured == 30 000`, **и ассерт отсутствия признака перерасхода в контракте** (промолчать — решение владельца); кейс 11 — бюджет увеличен после полного взноса → `goals_part == 12 000`, `reserve_configured == 42 000`. **Блок B** — инвариант AC-3 параметризованно по всем 45 дням. **Блок C** — «таяние» и `payments == 0` за `payments_end`; `payments(D)` не включает платежи дня D. **Блок D** — `_split_day` три ветки с assert суммы; сжатая полоса. **Блок E** — `cushion_part` НЕ сжимается вне каскада (перенакопленная подушка 922 155 при пороге 30 000 → `reserve_configured == 30 000`). **Блок F** — границы: последний день месяца, 1-е число, февраль, 31-е, переход через год, окно через три месяца, **плюс НОВЫЙ тест «exception перенесён в другой месяц»** (🟡№2, кейс 12): exception с `original_date = 25 сент` и `transaction_date = 8 окт` (создаётся через `create_exception` + прямая правка `transaction_date`, как это делает `update_transaction`) → числа по трём слоям для D = 30 сент (`goals_part == 15 000`) и D = 5 окт (`goals_part == 0`, «Свободно» не завышено), плюс assert «ключ за `window_end` присутствует в `savings_by_date`». **Блок G** — `is_empty` vs `window_is_flat` + assert «в `_is_empty` нет обращений к БД». **Блок H** — ADJUSTMENT оба знака; `is_skipped` не в слое. **Блок I** — детач. **Блок J** — fail-open: `degraded is True`, `goals_part == 0`, лог с трейсбеком. Даты относительные (`date.today()` + хелперы `conftest.py`), без `pytest.skip`. Всего ~37 тестов | **9.5 ч** (v3: 9 ч) | 3, 4, 5 |
| 7 | `app/assets/panel.css` — `pnl-*` из эскиза v3 на переменных проекта, `tabular-nums`, вертикальный ритм, `@media (prefers-reduced-motion: reduce)`. Классы сигнальной шины, чипа вердикта и приветствия НЕ заводить (пп. 3а, 3г) | **2 ч** | — |
| 8 | `build_free_header()` + `_build_header_empty_state()`; кнопка «Сверка» с новым id; шестерёнка `dashboard-settings-cog`; аватар+имя справа из переданного `profile`; сноска `degraded`. **Приветствие НЕ строится** (п. 3г) — состав шапки на один элемент короче v3 | **2 ч** (v3: 2.5) | 1, 7 |
| 9 | `build_layers_chart()` + `_build_layer_legend()` + `_build_payments_tooltip()` + `_build_reserve_tooltip()` (честная подпись, п. 3б) + `_build_chart_empty_state()` + `_axis_tickvals()` (**`ceil` по `MAX_X_TICKS`**, 🟢№5); заметки vision-критика (легенда вне поля, ярлык минимума со сдвигом `yshift`/`ay`) | **4 ч** | 1, 7 |
| 10 | `profile_modal.py` — второй Input и ветка `triggered_id in (...)`; ручная проверка обеих ветвей | **0.5 ч** | 8 |
| 11 | Переключение `_load_dashboard_components` (**сигнатура `(period_state)`**, один вызов `get_profile`) и callback'ов: новые Output-ID, 5 значений, снятие `Input("period-switcher","value")` и callback'а `update_period_state`, **снятие Output `dashboard-greeting`**, перепривязка `open_create_from_chart` на `dashboard-layers-chart-graph` + ISO-дата, clientside «Сверка» на новый id, `logger.opt(exception=True)` в обеих ветках ошибок | **3 ч** | 8, 9 |
| 12 | Удаление мёртвого кода в `dashboard.py`: **`_build_greeting_text()` (`:82-91`) и элемент `dashboard-greeting` (`:108-112`) — решение владельца п. 3г**, плюс `build_overview_cards`, `_build_kpi_card`, `build_cashflow_chart`, `_build_daily_cashflow_chart`, `_build_yearly_cashflow_chart`, `build_statistics_card`, `create_ai_assistant_card`, `create_exchange_card`, `build_recent_transactions_card`; проверить, что импорты `OnboardingService`/`get_db_session` в модуле остались нужны другим путям; + чистка `custom.css` (`#dashboard-overview-cards`, `.db-period-switcher`, `.kpi-*`) | **2 ч** | 11 |
| 13 | `tests/test_dashboard_callbacks.py` — **ЧЕТЫРЕ позиции** (пересмотрено под п. 3г): (1) **удалить класс `TestBuildGreetingText`** (`:73-102`, 2 теста) и импорт `_build_greeting_text` (`:20`) — хелпер удалён; (2) `test_load_dashboard_data_decorator_declares_greeting_output` (`:62-70`) → переориентировать на `Output("dashboard-free-header", "children")`, переименовать; (3) `test_returns_seven_values_with_greeting_last` (`:186-210`) → **5** значений, ассерт приветствия **снимается** (приветствия нет), вместо него — ассерт наличия имени профиля в содержимом шапки, переименовать; (4) `test_wrong_pathname_prevents_update` (`:212-222`) → снять `period_value=`. Плюс докстринг модуля (`:1-12`): «Приветствие обновляется внутри load_dashboard_data (7-й Output)» → «Приветствие снято с дашборда (решение владельца п. 3г); имя и аватар обновляются первым Output'ом шапки». Проверки: не осталось `period_value=` и `_build_greeting_text` | **2 ч** (v3: 1.5) | 11, 12 |
| 14 | Прогон `pytest -q` (565 прежних − 2 удалённых + новые), `black`, `flake8`; ручная AC-1…AC-6 на наполненной и чистой базе; замер NFR-1 | **2.5 ч** | все |

Порядок сохраняет принцип «тесты модели до UI». Шаг 6 — самый дорогой не случайно: отсутствие таблицы ожидаемых слоёв было причиной, по которой оба блокера дожили до v2, и оба новых входа v4 добавлены **в ту же матрицу**, а не рядом с ней.

## Зависимости

Новых библиотек нет. `plotly.graph_objs` (`go.Bar` + `barmode="stack"`), `dash_bootstrap_components.Tooltip`, `calendar.monthrange`, `math.ceil`, `datetime.timedelta` — всё используется в проекте. Окно 45 дней укладывается в `MAX_FORECAST_DAYS = 366`.

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Единая формула резерва даёт неверную раскладку на конфигурации, не попавшей в таблицу | **Низкая** | Формула не ветвится и оперирует одним источником — списком savings-операций из того же кассового календаря, что даёт баланс. Формула независимо пересчитана критиком по коду на всех 9 кейсах. Блок A шага 6 задаёт **числами все три слоя** по матрице `режим × доля взноса × позиция дня` и включает 9 трассированных кейсов **плюс два новых входа «смена бюджета внутри месяца»**. Инвариант AC-3 (блок B) не считается главной защитой: он по построению слеп к раскладке |
| **Расхождение настройки и истории (бюджет менялся внутри месяца)** | **Средняя** | Не устраняется, а **объявляется**: допущение в докстринге `_goals_part_by_day` с обоими направлениями ошибки; поведение при перерасходе зафиксировано решением владельца п. 3в (промолчать, `max(0,…)`); два параметра в блоке A. Опасного направления нет: при уменьшении бюджета числа корректны, при увеличении «Свободно» занижается. Различение «бюджет исчерпан» / «обещано больше бюджета» сознательно не вводится — открытый вопрос ROADMAP №9 |
| **Расхождение фактической даты savings-операции и даты, по которой её видит баланс (перенесённый exception)** | **Низкая** | Достижимость проверена по коду и оказалась узкой: `create_exception(new_date=...)` **не имеет вызывающих**, расхождение возможно только двухшаговым путём UI. Три случая разобраны с направлением ошибки (докстринг `_goals_part_by_day`). Случай «сдвиг вправо» **исправлен** снятием фильтра по `window_end` (+1 `if`) — тест в блоке F с числами по трём слоям. Случай «сдвиг влево за `collect_start`» расхождения не даёт (одна выборка у нас и у баланса). Случай «сдвиг внутри месяца» назван ограничением с направлением («Свободно» завышается) и привязан к латентному дефекту `_calculate_recurring_before_date`, который C-3 не даёт править |
| Границы месяцев в `_goals_part_by_day` реализованы с off-by-one | Средняя | Границы прописаны в докстринге интервалами; блок F шага 6 покрывает первый день месяца, последний день месяца, февраль, 31-е, переход через год, окно через три месяца **и перенесённый exception за `window_end`**; блок A содержит по дню с каждой стороны каждой границы |
| «Свободно сегодня» на числах эскиза даёт 17 000, а не 32 000 | Средняя | Расхождение с моковым числом эскиза зафиксировано явно (в осадок решений) с обоснованием: recurring-резерв целей физически входит в список операций и уже сидит в слое «Платежи». Композиция эскиза не меняется. Проверка на шаге 14 |
| Сбор операций на диапазон `[month_start, window_end]` (до 75 дней) дороже v2 | Средняя | Цена источника данных за границей месяца. Вызов один. Компенсация: сняты `get_budget_progress` (с вложенным `get_settings`, `:190`), `_get_reserve_sum_for_month`, `count(transactions)`, полный обход recurring-истории в `get_threshold_amount` **и второе чтение профиля** (п. 3г). Замер на шаге 14 |
| `free` уходит в минус при остатке ниже платежей+резерва | Средняя | Детерминированный каскад `_split_day` (единственный механизм, п. 3б); блок D шага 6 на все три ветки с assert суммы |
| Сжатая синяя полоса воспринимается как ошибка расчёта | Низкая | Честная подпись (п. 3б): тултип называет ФАКТ дня и настройку рядом; `reserve_configured` в контракте гарантирует, что UI не может утверждать настройку вместо факта |
| Fail-open по бюджету целей показывает больше свободных денег, чем есть | Средняя | Флаг `degraded` + нейтральная сноска в разборе шапки + отсутствие утверждающего тултипа «Резерв»; тест в блоке J шага 6 |
| Снятие `period-switcher` ломает вызовы `load_dashboard_data` в тестах | Низкая | Полный список закрыт grep'ом: `period_value=` в `tests/test_dashboard_callbacks.py:204`, `:219` |
| **Удаление `_build_greeting_text` ломает регрессионную защиту протокола 0026** | **Низкая** | Проверено grep'ом: у хелпера ровно два вызывающих (`dashboard.py:111`, `:1386`), оба снимаются этим куском → мёртвый код. Защита протокола 0026 — это подписка на `profile-updated`, а не приветствие: `Input("profile-updated", "data")` остаётся у `load_dashboard_data` и `toggle_balance_toast`, оба теста (`:50`, `:57`) **не трогаются**. Имя и аватар в шапке обновляются тем же Input'ом. Отдельного Output/callback'а на приветствие не появляется — запрет протокола 0024 соблюдён строже, чем в v3 |
| Латентный дефект `_calculate_recurring_before_date` (учитывает только income/expense, `:396-406`, тогда как `_get_recurring_daily_changes` `:426-437` учитывает и `savings_*`) искажает базу окна | Средняя | Подтверждено проверкой по коду. Инвариант AC-3 не ломает, но абсолютные величины «Свободно» могут смещаться у пользователей с давним recurring-резервом. **Является причиной третьего случая перенесённого exception** (см. соответствующий риск). Правка вне scope (C-3); кандидат на отдельный протокол, запись в осадок одним пунктом со следствием |
| Тултип легенды (FR-4) hover-only — не работает на touch | Низкая (в scope) | `dbc.Tooltip(trigger="hover focus")` + элемент с `tabIndex=0`. Полноценный touch — Epic-08 |
| Аватар в шапке дублирует аватар в сайдбаре (C-1 запрещает трогать сайдбар) | Средняя | Осознанная временная цена куска 1, снимается в куске 3. В осадке решений |
| Правка `profile_modal.py` ломает вход в профиль из сайдбара | Низкая | Ветка расширяется через `triggered_id in (...)`; ручная проверка обоих входов (шаг 10) |
| Вехи целей загромождают 45-дневную ось | Низкая | ≤`MAX_MILESTONES_IN_WINDOW = 3` в окне, остальные — сводкой в тултипе; одна стрелка-аннотация `beyond_window` |

## Requirements Traceability Matrix (RTM)

| # | Requirement (дословно из спецификации) | Секция spec | Реализация в solution | Тип |
|---|---|---|---|---|
| FR-1.a | «Для каждого дня горизонта (текущий календарный месяц, начиная с сегодня) модель выдаёт декомпозицию прогнозного остатка на три слоя» | FR-1 | **ОСОЗНАННОЕ ОТСТУПЛЕНИЕ, решение владельца 2026-08-24 (п. 2):** окно оси — 45 дней (`WINDOW_DAYS`), а не календарный месяц. Календарным месяцем ограничен только слой «Платежи» (`payments_end`). C-5 в design.md ограничивает *слой*, не ось | FR |
| FR-1.b | «*Свободно* — реально доступные деньги» | FR-1 | `DayLayers['free']` = `balance − payments − reserve` через `_split_day()` | FR |
| FR-1.c | «*Платежи* — деньги ещё на счету, но уйдут на уже запланированные платежи (регулярные + разовые предстоящие) до конца календарного месяца» | FR-1 | `_collect_operations` → `_payments_tail_by_day` — суффиксная сумма в `(D, payments_end]`, только для платежей с датой `>= reference_date`; за `payments_end` слой строго `0` | FR |
| FR-1.d | «слой "тает" по мере исполнения платежей и пересчитывается на границе месяца» | FR-1 | Суффиксная сумма даёт монотонное таяние; `payments(payments_end) == 0`. «Пересчёт на границе месяца» = `payments_end` привязан к месяцу `reference_date`. Блок C шага 6 | FR |
| FR-1.e | «*Резерв* — резерв целей (бюджет накоплений) + подушка» | FR-1 | `reserve_configured(D) = cushion_threshold + goals_part(D)`, где `cushion_threshold` — **порог** подушки (п. 1), `goals_part(D) = max(0, budget − consumed(D) − committed(D))`. Фактический `reserve(D)` — результат каскада `_split_day` (п. 3б). Численная трассировка на **12 кейсах**; блок A шага 6. **Два допущения объявлены явно** в докстринге `_goals_part_by_day`: «бюджет не менялся внутри месяца» (перерасход обрезается без признака в UI — решение владельца п. 3в) и «фактическая дата операции совпадает с датой, по которой её видит баланс» (три случая с направлениями ошибки) | FR |
| FR-1.f | «Сумма трёх слоёв на день D равна прогнозному остатку на D (согласована с балансом кассового календаря)» | FR-1 | Конструктивно: `free` выводится вычитанием из `calculate_daily_balances`, `_split_day` сохраняет сумму. Блок B шага 6. **Оговорка:** инвариант по построению слеп к раскладке слоёв и потому НЕ считается главной защитой корректности (см. FR-1.e и блок A). Именно эта слепота скрывает случай 3 перенесённого exception — ограничение зафиксировано, а не спрятано | FR |
| FR-1.g | «Модель — единый источник для шапки, графика и (в куске 2) карточек щитка» | FR-1 | Один вызов `get_money_layers()` в `_load_dashboard_components()` кормит `build_free_header()` и `build_layers_chart()`. Оговорка: контракт куска 1 не претендует на стабильность до куска 2 | FR |
| FR-2.a | «Вверху дашборда: "Свободно сегодня: N ₽" (N — срез модели FR-1 на сегодня)» | FR-2 | `build_free_header()`: метка «Свободно сегодня» + `format_rub(data['today']['free'])`; тест `today['free'] == days[0]['free']` и `days[0]['date'] == reference_date` | FR |
| FR-2.b | «цветовой вердикт состояния (порядок / впереди просадка / проблема)» | FR-2 | **ТРЕБОВАНИЕ СНЯТО РЕШЕНИЕМ ВЛАДЕЛЬЦА 2026-08-24** (п. 3а). Не реализуется: нет уровней ok/dip/problem, порогов, чипов, сигнальной шины. Из контракта не создаются `VerdictLevel`, `VERDICT_TEXTS`, `VERDICT_COLORS`, `DIP_RATIO`, `DIP_FLOOR`, поля `level`/`text`/`dip_threshold`. Причина владельца: любой порог произволен, проблемные дни видны на графике. **Осознанное отступление от буквы спеки, а не покрытие.** Что осталось: `min_free`/`min_free_date` — исключительно как данные для маркера FR-3.e | FR |
| FR-2.c | «краткий разбор "баланс − платежи − резерв"» | FR-2 | `pnl-breakdown`: «баланс {balance} − платежи {payments} − резерв {reserve}» из `TodaySlice` через `format_rub`. При `degraded=True` — нейтральная сноска | FR |
| FR-2.d | «Справа — аватар пользователя и служебная иконка настроек» | FR-2 | `get_avatar_emoji(profile['avatar_id'])` + `profile['name']` в `pnl-avatar`; шестерёнка `id="dashboard-settings-cog"` → **новый Input в `profile_modal.py`** (решение владельца п. 5). Состав воспроизводит эскиз буквально (`v3.html:415-418`). `profile` — единственный источник имени/аватара, второго чтения профиля нет | FR |
| FR-2.e | «Шапка не является дверью-переходом» | FR-2 | На `pnl-breaker` нет `dcc.Link`, `n_clicks`, `cursor:pointer`; кликабельны только «Сверка» и шестерёнка | FR |
| FR-2.f | «Шапка-вердикт **заменяет текущий ряд 4 KPI-карточек** (два "главных числа" рядом недопустимы)» | FR-2 | Удаляются `build_overview_cards()`, `_build_kpi_card()`, `build_statistics_card()`; `dashboard-overview-cards` и `dashboard-statistics-card` уходят из layout; на их место — `dashboard-free-header`. Элемент `dashboard-greeting` тоже уходит (см. отдельную строку) | FR |
| **Приветствие** | «Привет, {имя}» / `dashboard-greeting` — **не требование спеки**, а унаследованный элемент текущего дашборда (`dashboard.py:108-112`, протоколы 0024/0026) | — (спека приветствия не требует; FR-2.d просит только аватар и иконку) | **СНЯТО РЕШЕНИЕМ ВЛАДЕЛЬЦА 2026-08-24 (п. 3г).** Приветствие с дашборда убирается: «главное место отдано цифре, не вежливости». Это **не отступление от спеки** — спека приветствия не требовала; это снятие унаследованного элемента, и оно согласовано с принятым эскизом, где приветствия нет вовсе (`v3.html:415-418` — только 🦊 + «Иван» + шестерёнка). Следствия исполнены: элемент и Output удаляются; **хелпер `_build_greeting_text()` удаляется как мёртвый код** (вызывающих ровно два, оба снимаются — grep); `TestBuildGreetingText` и импорт `:20` удаляются; «пустой» для loguru `exc_info=True` (`:90`) исчезает вместе с телом функции (critique-v3, №4); второе чтение профиля за рендер снято (critique-v3, №3). Защита протокола 0026 не ослаблена: `Input("profile-updated", "data")` сохранён у обоих callback'ов, тесты `:50`/`:57` не трогаются | Решение владельца |
| FR-3.a | «Текущий график (grouped bars + линия баланса, протокол 0022) заменяется полностью» | FR-3 | Удаляются `_build_daily_cashflow_chart()`, `_build_yearly_cashflow_chart()`, `build_cashflow_chart()`; `dashboard-cashflow-chart` → `dashboard-layers-chart` | FR |
| FR-3.b | «стопка полос Свободно (зелёный) / Платежи (оранжевый) / Резерв (синий) по дням» | FR-3 | `barmode="stack"`, три `go.Bar` по датам; `LAYER_COLORS`: `#2ecc71` / `#f0b775` / `#3498db`; порядок снизу вверх free → payments → reserve | FR |
| FR-3.c | «вехи целей на оси времени» | FR-3 | `GoalMilestone` + аннотации Plotly; ≤`MAX_MILESTONES_IN_WINDOW = 3` в окне + одна `beyond_window` стрелкой. При окне 45 дней и валидации `create_goal` (`target_date >= today + 7`) вехи попадают в кадр регулярно | FR |
| FR-3.d | «вертикальная линия "сегодня"» | FR-3 | `fig.add_shape` (`yref="paper"`) на `reference_date`, `dash="dash"`, подпись «сегодня» | FR |
| FR-3.e | «маркер минимума остатка» | FR-3 | Маркер-кружок на `data['min_free_date']` + аннотация `format_rub(data['min_free'])` со сдвигом (`yshift`/`ay`). Минимум по всем 45 дням. **Единственный потребитель `min_free`** — оценочного вывода нет (см. FR-2.b) | FR |
| FR-3.f | «График и шапка — единый визуальный блок» | FR-3 | Одна модель на оба блока; тест `today['free'] == days[0]['free']`; визуально `pnl-meter` примыкает к `pnl-breaker` | FR |
| FR-4.a | «У легенды графика — пояснение с конкретикой: для "Платежей" — список предстоящих платежей с датами» | FR-4 | `_build_payments_tooltip()`: `dbc.Tooltip` на элементе легенды «Платежи», строки «{описание} · {дата} · {сумма}» из `upcoming_payments`, до 8 + «и ещё N». Только текстовые компоненты | FR |
| FR-4.b | «для остальных слоёв — что входит в слой» | FR-4 | «Свободно»: «Остаток минус платежи до конца месяца и резерв». «Резерв целей и подушки»: **честная подпись по факту дня** (п. 3б) — «Порог подушки {cushion_threshold} + бюджет целей {goals_reserve_today}», при сжатой полосе «В этот день на резерв остаётся {reserve} из {reserve_configured} — вы залезаете в подушку». **Признака «обещано сверх бюджета» в тултипе НЕТ** — решение владельца п. 3в (промолчать) | FR |
| FR-5.a | «Вход в "Сверку" с дашборда сохраняется» | FR-5 | Кнопка «Сверка» в правом блоке шапки, id `open-recon-from-dashboard-header-btn`, тот же clientside → `open-recon-trigger`. Баннерная кнопка не трогается | FR |
| FR-5.b | «Судьба показателя "Доходы за месяц" решается проектированием явно» | FR-5 | **Решение: убрать с дашборда осознанно.** Основание: не отвечает ни на один вопрос иерархии внимания design.md; его проекция — «цифра месяца» карточки «Аналитика» (кусок 2). Данные сохранны: `CalendarService.get_month_summary`, `DashboardService.get_overview_metrics`, раздел `/analytics`. Запись в осадок | FR |
| FR-6.a | «При нулевых данных шапка и график показывают спроектированное пустое состояние» | FR-6 | `is_empty` через `_is_empty()` — **без отдельного запроса**. `_build_header_empty_state()` + `_build_chart_empty_state()`. Отдельно `window_is_flat` — график рисуется, а не подменяется | FR |
| FR-6.b | «без осей −1..1, склеек подписей и прочих артефактов деградации» | FR-6 | При `is_empty` Plotly не вызывается (`html.Div` вместо `dcc.Graph`). Для непустых: `yaxis=dict(rangemode="tozero", tickformat=",.0f", separatethousands=True)`; `xaxis=dict(type="date", tickmode="array", tickvals=_axis_tickvals(...), tickformat="%-d %b", tickangle=0)` — **не более `MAX_X_TICKS = 11` подписей** (для 45 дней — 10), явные даты вместо `dtick` в спорных единицах | FR |
| NFR-1 | «Загрузка дашборда с новой моделью и графиком — не медленнее текущего дашборда; ориентир < 2 секунд» | NFR-1 | **Бюджет вызовов на рендер дашборда (пересмотрен под п. 3г):** 1 `calculate_daily_balances(ref, ref+44)`; **1** `get_all_transactions_for_period(month_start(ref), window_end)` — до 75 дней, единственный сбор; 1 `BudgetReservationService.get_settings`; 1 `CushionService.get_threshold_amount` (**без** обхода баланса); 1 `GoalService.get_all_by_user`; ≤1 `RecurringService.get_templates_for_user`; **1 `OnboardingService.get_profile`** (для аватара и имени шапки). **Ушли относительно v3:** второе чтение профиля через `_build_greeting_text()` — хелпер открывал собственный `get_db_session()` (`dashboard.py:82-91`) и удаляется вместе с приветствием (critique-v3, №3, решение владельца п. 3г). **Ушли относительно v2:** `get_budget_progress` (с вложенным `get_settings`, `:190`), `_get_reserve_sum_for_month`, `count(transactions)`. **Честная оговорка:** ещё один полный обход recurring-истории остаётся вне модели — в `_build_cushion_card_readonly` (`dashboard.py:395-398`), который C-1 запрещает трогать. Диапазон сбора ≤75 дней — цена источника данных за границей месяца. Замер на шаге 14 | NFR |
| NFR-2 | «Сбои расчёта модели логируются через loguru с трейсбеком (`logger.opt(exception=True)` — идиома проекта, протокол 0027), не молча» | NFR-2 | `logger.opt(exception=True).warning(...)` в fail-open ветках (бюджет целей, цели, неожиданный сбой порога) + флаг `degraded`; `logger.opt(exception=True).error(...)` в `load_dashboard_data` / `refresh_dashboard_after_crud` вместо `logger.error(f"...{e}")` (`:1389`, `:1451`). **Третий «пустой» для loguru `exc_info=True` (`_build_greeting_text`, `:90`) не остаётся оговоркой, а исчезает физически** — хелпер удаляется по решению владельца п. 3г (critique-v3, замечание №4 закрывается без ссылки на п.10 аудита). Штатное «нет пользователя / подушка не настроена» — тихий дефолт без трейсбека | NFR |
| C-1 | «Остальные разделы и сайдбар в этом куске не трогаются. Таблицы операций, wishlist-виджет и карточка подушки на дашборде остаются как есть» | C-1 | Правки в `dashboard.py`, `profile_modal.py` (решение владельца п. 5), `cushion_service.py` (добавление метода), `custom.css`, новых файлах. `sidebar.py`, `calendar.py`, `goals.py`, `transactions.py`, `analytics.py` не меняются. `dashboard-recent-transactions`, `dashboard-upcoming-transactions`, `build_wishlist_widget()`, `dashboard-cushion-card` остаются в layout и в tuple | C |
| C-2 | «Decimal для денег, session-контракт flush()/commit(), сервисы не знают о Dash» | C-2 | Все денежные поля TypedDict — `Decimal`; `MoneyLayersService` read-only; `get_threshold_amount` read-only; импортов `dash`/`plotly` в сервисах и схеме нет | C |
| C-3 | «Существующее поведение сервисов не меняется — модель FR-1 строится надстройкой/композицией; полный прогон тестов (565 на 2026-08-21) остаётся зелёным» | C-3 | Ни один существующий метод `CalendarService`/`DashboardService`/`CushionService`/`BudgetReservationService`/`GoalService`/`RecurringService`/`TransactionService` не редактируется. **Одно явно зафиксированное отступление:** в `CushionService` **добавляется** новый метод `get_threshold_amount()` — C-3 запрещает менять поведение, а не расширять API. Зависимости от приватного `_get_reserve_sum_for_month` нет. `tests/test_dashboard_service.py`, `test_calendar_service.py`, `test_budget_reservation_service.py`, `test_goal_service.py` не правятся; правятся только `test_dashboard_callbacks.py` (контракт callback'а + удаление тестов удалённого хелпера) и дополняется `test_cushion_service.py`. **Число тестов в прогоне меняется:** 565 − 2 (`TestBuildGreetingText`) + новые — это следствие решения владельца п. 3г, а не регрессия; фиксируется на шаге 14 | C |
| C-4 | «Схема БД не меняется» | C-4 | Проверено: `users.starting_balance/cushion_target/cushion_threshold_percent/monthly_savings_budget/avatar_id/name`, `transactions.*`, `goals.*` — всё есть. Колонки «ручная сумма порога подушки» в схеме нет (только `cushion_threshold_manual` — булев, `database.py:107`). Месячной истории бюджета целей нет (`monthly_savings_budget` — одна настройка, `:99`), поэтому `budget(D) == monthly_budget` для любого D — **зафиксировано в докстринге `_goals_part_by_day` вместе с последствиями расхождения настройки и истории** (решение владельца п. 3в). Поля `reservation_mode`/`reservation_day` моделью не читаются. Миграций нет | C |
| C-5.a | «Горизонт слоя "Платежи" — до конца календарного месяца» | C-5 | `payments_end = date(y, m, monthrange(y, m)[1])`; `_payments_tail_by_day` не смотрит за `payments_end`. `payments_end` — чисто арифметический фильтр, а не граница сбора; сбор идёт до `window_end`. C-5 соблюдён буквально: в слой «Платежи» ни одна операция следующего месяца не попадает. **Уточнение v4:** `committed(D)` в формуле резерва — **не** слой «Платежи» и `payments_end` не ограничен (он ограничен `month_end(D)` и может захватывать даты за `window_end` — 🟡№2); это разные величины, и различие прописано в докстрингах | C |
| C-5.b | «Механику "основного дохода" не реализовывать» | C-5 | Нет ни поля, ни ветвления по «основному доходу» | C |
| AC-1 | «Наполненная база → видна шапка "Свободно сегодня: N ₽" с цветовым вердиктом и разбором, и N совпадает со значением слоя "Свободно" модели на сегодняшнюю дату» | AC-1 | Покрыто **частично, с явным отступлением:** шапка, число N и разбор реализованы (`build_free_header`, тест `today['free'] == days[0]['free']`, ручная проверка шага 14). Часть «**с цветовым вердиктом**» — **СНЯТА решением владельца п. 3а** (см. FR-2.b). При приёмке этот фрагмент не проверяется: он не проваленный критерий, но и не выполненный | AC |
| AC-2 | «Отображается график стопки трёх полос с легендой, вехами целей, линией "сегодня" и маркером минимума; старый график и ряд 4 KPI-карточек отсутствуют» | AC-2 | `build_layers_chart()` + `_build_layer_legend()`; физическое удаление `_build_daily_cashflow_chart`, `_build_yearly_cashflow_chart`, `build_cashflow_chart`, `build_overview_cards`, `_build_kpi_card`, `build_statistics_card` (шаг 12) + grep-проверка | AC |
| AC-3 | «Для любого дня D горизонта сумма трёх слоёв модели равна прогнозному остатку на D из кассового календаря — проверено unit-тестом» | AC-3 | Блок B шага 6: для всех 45 дней `free + payments + reserve == forecast_balance`. **Явная оговорка:** тест по построению зелёный при любой раскладке, поэтому корректность держит блок A. Именно эта слепота маскирует случай 3 перенесённого exception — ограничение названо в докстринге, а не оставлено на тест | AC |
| AC-4 | «Наведение/клик на пояснение легенды "Платежи" показывает список конкретных предстоящих платежей с датами до конца месяца» | AC-4 | `dbc.Tooltip(target="pnl-legend-payments", trigger="hover focus")` со строками из `upcoming_payments`; элемент с `tabIndex=0`. Тултип объясняет и пустой случай | AC |
| AC-5 | «Чистая база → шапка и график показывают осмысленное пустое состояние без артефактов» | AC-5 | Ветка `is_empty` (Plotly не вызывается) + тесты блока G, включая «онбординг пропущен (`skip()` → `first_launch=False`, `starting_balance=0`) → `is_empty=True`» и «в `_is_empty` нет обращений к БД». Ручная проверка (шаг 14) | AC |
| AC-6 | «Вход в сверку с дашборда работает» | AC-6 | `open-recon-from-dashboard-header-btn` → тот же clientside → `open-recon-trigger` → существующий `create_reconciliation_modal()` в `main.py`; баннерный вход сохранён; потребитель в `calendar.py:1262-1309` не затронут | AC |
| AC-7 | «Новая модель покрыта unit-тестами (включая границу месяца и "таяние" платежей); полный прогон pytest зелёный; black + flake8 без новых замечаний» | AC-7 | `tests/test_money_layers_service.py` — ~37 тестов в 10 блоках (шаг 6), включая блок A «таблица ожидаемых слоёв» (с двумя новыми параметрами смены бюджета) и блок F (с новым тестом перенесённого exception); блоки C и F — явно про таяние и границы месяцев; дополнения в `test_cushion_service.py`; шаг 14 — `pytest -q`, `black`, `flake8` | AC |
| Эскиз | «легенду графика вынести из поля» (заметка vision-критика) | memory/spec-context | `showlegend=False` в Plotly; HTML-легенда `_build_layer_legend()` под заголовком блока графика | Заметка |
| Эскиз | «ярлык минимума ("9 800 ₽") не ставить вплотную к тику даты» | memory/spec-context | Аннотация минимума со сдвигом (`yshift`/`ay`) + плашка «Минимум свободного» в свободной зоне поля | Заметка |
| Эскиз | «выровнять вертикальный ритм карточки "Цели"» | memory/spec-context | Не применимо к куску 1 (карточки-двери — кусок 2). Заметка остаётся в осадке | Заметка |
| Эскиз | Ось «~45 дней» (`v3.html` aria-label: «с 22 августа по 5 октября 2026») | .visual + осадок | `WINDOW_DAYS = 45`; `_axis_tickvals` → ≤`MAX_X_TICKS = 11` подписей (для 45 дней 10). **Расхождение с эскизом объявлено:** в эскизе 11 подписей с неравномерным шагом (семантические даты, `v3.html:575-596`), равномерная сетка их не воспроизводит; воспроизводится плотность, ограниченная сверху | Эскиз |
| Эскиз | Вердикт-чип «Всё в порядке» зелёной плашкой (brief.md эскиза, п. 1) | .visual + осадок | **НЕ РЕАЛИЗУЕТСЯ — решение владельца п. 3а.** Отступление от принятого эскиза зафиксировано явно; композиция шапки сохраняется, место чипа занимает разбор | Эскиз |
| Эскиз | Правый блок шапки: аватар-эмодзи + имя + шестерёнка, **без приветствия** (`v3.html:415-418`) | .visual + осадок | **Соответствие полное** после решения владельца п. 3г: приветствие с дашборда снято, шапка воспроизводит эскиз буквально. До п. 3г v3 добавлял приветствие, которого в эскизе нет | Эскиз |
| Эскиз | «Свободно сегодня: 32 000 ₽» при разборе «84 500 − 37 500 − 15 000» | .visual + осадок | **Числовое расхождение зафиксировано явно:** на реальных данных recurring-резерв целей входит в список операций и сидит в слое «Платежи»; корректный разбор — `84 500 − 37 500 − 30 000 = 17 000`. Композиция и метафора эскиза не меняются; расхождение — в осадок | Эскиз |

## Blast Radius

### Прямые изменения

- `app/schema/money_layers.py` — **НОВЫЙ**: `DayLayers`, `UpcomingPayment`, `GoalMilestone`, `TodaySlice`, `MoneyLayersData`, `Horizons`; `LayerKey`; `WINDOW_DAYS`, `MAX_MILESTONES_IN_WINDOW`, **`MAX_X_TICKS`** (переименована из `TARGET_X_TICKS`), `LAYER_COLORS`, `LAYER_LABELS`. **Не создаются** (п. 3а): `VerdictLevel`, `VERDICT_TEXTS`, `VERDICT_COLORS`, `DIP_RATIO`, `DIP_FLOOR`.
- `app/services/money_layers_service.py` — **НОВЫЙ**: `MoneyLayersService.get_money_layers()` + `_horizons`, `_forecast_balances`, `_collect_operations` (**без фильтра `savings_by_date` по окну**), `_payments_tail_by_day`, `_goals_part_by_day` (**`committed(D)` до `month_end(D)`, не обрезая по `window_end`**), `_split_day`, `_today_slice`, `_window_min_free`, `_goal_milestones`, `_is_empty`.
- `app/assets/panel.css` — **НОВЫЙ**: `pnl-*` (шапка, блок графика, HTML-легенда). Без классов сигнальной шины, чипа вердикта и приветствия.
- `app/services/cushion_service.py` — **ДОБАВЛЕНИЕ** `get_threshold_amount()`; существующие методы не тронуты.
- `app/components/dashboard.py` — крупнейший blast: удаление 4 KPI-карточек, `build_statistics_card`, обоих старых графиков, мёртвого кода **и `_build_greeting_text()` (`:82-91`, решение владельца п. 3г)**; добавление `build_free_header`, `build_layers_chart`, `_build_layer_legend`, `_build_payments_tooltip`, `_build_reserve_tooltip`, `_build_header_empty_state`, `_build_chart_empty_state`, `_axis_tickvals`; перекройка `create_dashboard_layout` (снятие `period-switcher` :118-128, **`dashboard-greeting` :108-112**, `dashboard-overview-cards` :129-133, `dashboard-statistics-card` :170), `_load_dashboard_components` (**сигнатура `(period_state)`**, 5 значений, один `get_profile`), `load_dashboard_data` (5 Output'ов, снятие `Input("period-switcher","value")` и **Output `dashboard-greeting` :1348**, `logger.opt`), `refresh_dashboard_after_crud` (5 Output'ов, `logger.opt`), `open_create_from_chart` (Input → `dashboard-layers-chart-graph`, ISO-дата), clientside «Сверка» (новый id); **удаление** callback'а `update_period_state` (:1397-1408). Проверить, что импорты `OnboardingService` / `get_db_session` в модуле остаются нужны (они нужны — `_load_dashboard_components` читает профиль).
- `app/components/profile_modal.py` — **прямые изменения** (решение владельца п. 5): второй `Input("dashboard-settings-cog", "n_clicks")` и ветка `triggered_id in ("sidebar-profile-container", "dashboard-settings-cog")`.
- `app/schema/__init__.py` — реэкспорт новых типов и констант (+ `__all__`).
- `app/services/__init__.py` — реэкспорт `MoneyLayersService` и типов модели (+ `__all__`).
- `app/assets/custom.css` — удаление `#dashboard-overview-cards .row`, `.db-period-switcher`, `.kpi-*` (:195-268) — grep проведён; `.an-period-switcher` в analytics — отдельный класс; правка `.db-page` / `.db-left-col` под новую сетку.
- `tests/test_money_layers_service.py` — **НОВЫЙ**: FR-1 / AC-3 / AC-7, 10 блоков (см. шаг 6), включая два параметра смены бюджета и тест перенесённого exception.
- `tests/test_dashboard_callbacks.py` — **четыре позиции** (пересмотрено под п. 3г): **удаление класса `TestBuildGreetingText` (`:73-102`) и импорта `_build_greeting_text` (`:20`)**; `test_load_dashboard_data_decorator_declares_greeting_output` (`:62-70`) → на `dashboard-free-header`; `test_returns_seven_values_with_greeting_last` (`:186-210`) → 5 значений, ассерт приветствия снят, добавлен ассерт имени профиля в шапке; `test_wrong_pathname_prevents_update` (`:212-222`) → снять `period_value=`; докстринг модуля (`:1-12`). Тесты `test_load_dashboard_data_decorator_declares_profile_updated_input` (`:50`) и `test_toggle_balance_toast_decorator_declares_profile_updated_input` (`:57`) **не трогаются** — подписка на `profile-updated` сохраняется.
- `tests/test_cushion_service.py` — тесты `get_threshold_amount`.

### Связанные файлы

- `app/main.py` — `suppress_callback_exceptions=True` (:41) и глобальные Store'ы (`open-recon-trigger` :95, `profile-updated` :91, `balance-toast-dismissed` :93), `create_reconciliation_modal()`, `create_profile_modal()`. Проверить, что снятые `period-switcher` и `dashboard-greeting` не ломают старт.
- `app/components/calendar.py` — второй потребитель `open-recon-trigger` (:1262-1309): контракт триггера менять нельзя.
- `app/components/sidebar.py` — `sidebar-profile-container` остаётся первым Input'ом модала; C-1 запрещает правки; визуальный дубль аватара — осознанная цена до куска 3.
- `app/config/avatars.py` — `get_avatar_emoji()`, `AVATARS`, `DEFAULT_AVATAR_ID` для шапки.
- `app/services/onboarding_service.py` — **НЕ меняется**; `get_profile` (`:150-166`) остаётся единственным источником имени/аватара шапки. Бросает `ValueError` при отсутствии пользователя — обрабатывается в `_load_dashboard_components` (пустое состояние / дефолтный профиль), как и раньше делал удаляемый хелпер.
- `app/components/wishlist.py` — `build_wishlist_widget()` вызывается прямо из `create_dashboard_layout` (:167): при перекройке layout нельзя потерять вызов (C-1).
- `app/components/transaction_modals.py` — `create-modal`, `preselected-date`, `modal-source`: Output'ы `open_create_from_chart`, парсинг клика меняется (`int(point["x"])` → ISO-дата). Отдельно: `process_recurring_edit_scope` (`:1163`) — точка, где создаётся exception с совпадающими датами; **не меняется**, но это первый шаг пути, дающего расхождение `transaction_date`/`original_date` (🟡№2).
- `app/services/transaction_service.py` — **НЕ меняется**; `update_transaction` (`:236-243`) присваивает `transaction_date` и не трогает `original_date` — второй шаг того же пути. Правка вне scope (C-3).
- `app/services/dashboard_service.py` — **НЕ меняется** (C-3), но `get_overview_metrics`, `get_daily_cashflow`, `get_yearly_cashflow`, `get_cashflow_data` теряют вызывающего на дашборде: остаются в публичном API и под тестами, удалять нельзя.
- `app/services/calendar_service.py` — **НЕ меняется**; латентный дефект `_calculate_recurring_before_date` (`:396-406` учитывает только income/expense, тогда как `_get_recurring_daily_changes` `:426-437` учитывает и `savings_*`) подтверждён и остаётся вне scope. **Является причиной ограничения «перенесённый exception внутри месяца»** — записывается в осадок одним пунктом со следствием.
- `app/services/budget_reservation_service.py` — **НЕ меняется**; `get_budget_progress` и `_get_reserve_sum_for_month` моделью **не вызываются**. `sync_template_amount` (`:808-839`) — источник допущения «бюджет не менялся внутри месяца»: обновляет только `template.amount`.
- `app/services/recurring_service.py` — **НЕ меняется**; `get_templates_for_user` (:114-137) используется как есть для `is_empty`; `get_instances_with_exceptions` (:666-721) — единая выборка и для нашего сбора, и для баланса; параметр `create_exception(new_date=...)` (:405) — **API без вызывающих**, кандидат на удаление отдельным протоколом (запись в осадок).
- `app/assets/clientside_triggers.js` — namespace `triggers`, `timestamp_trigger` / `open_create_modal`: переиспользуются новыми id, файл не меняется.
- `tests/test_dashboard_service.py`, `tests/test_calendar_service.py`, `tests/test_budget_reservation_service.py`, `tests/test_goal_service.py`, `tests/test_purchase_recommendation.py` — не должны требовать правок; если потребовали — признак нарушения C-3.
- `tests/test_bootstrap.py`, `tests/test_serializers.py` — smoke-тесты layout/сериализации: могут поймать несериализуемые объекты или отсутствующие id.
- `.obsidian-docs/knowledge-bank/modules/services.md`, `modules/schema.md`, `modules/ui-components.md`, `patterns/plotly-charts.md`, `architecture.md` — обновление KB после реализации (Dual-Y-Axis паттерн перестаёт применяться на дашборде; появляется паттерн stacked-decomposition).
- `memory/spec-context/epic-11.md` — записать: судьба «Доходов за месяц» (убрать), достаточность схемы БД, **снятие приветствия и удаление `_build_greeting_text` + `TestBuildGreetingText`**, единая формула резерва без режимного ветвления, **допущение «бюджет не менялся внутри месяца» и решение промолчать при перерасходе (п. 3в)**, **ограничение «перенесённый exception внутри месяца завышает Свободно» вместе с латентным дефектом `_calculate_recurring_before_date`, чьим следствием является**, **`create_exception(new_date=...)` — API без вызывающих**, числовое расхождение с моковой арифметикой эскиза (17 000 против 32 000), отступление от эскиза в части вердикт-чипа, расхождение по числу тиков оси (10 против 11 неравномерных), добавление `get_threshold_amount` как отступление от буквы C-3, удаление аргумента `period`.

### Проверить после реализации

- [ ] `pytest -q` — прежние зелёные (565 − 2 удалённых `TestBuildGreetingText`) + новые; в `test_dashboard_service.py`, `test_calendar_service.py`, `test_budget_reservation_service.py`, `test_goal_service.py` ни одной правки (доказательство C-3).
- [ ] `grep -rn "period_value" app tests` — пусто.
- [ ] `grep -rn "_build_greeting_text\|dashboard-greeting" app tests` — **пусто** (хелпер, элемент, Output и тесты удалены; п. 3г).
- [ ] `grep -rn "TARGET_X_TICKS" app tests` — пусто (переименована в `MAX_X_TICKS`).
- [ ] `grep -rn "build_overview_cards\|_build_kpi_card\|_build_daily_cashflow_chart\|_build_yearly_cashflow_chart\|build_cashflow_chart\|build_statistics_card\|dashboard-overview-cards\|dashboard-statistics-card\|period-switcher\|update_period_state\|kpi-" app tests` — по дашборду пусто (остаётся `an-period-switcher` в analytics).
- [ ] `grep -rn "VERDICT_\|dip_threshold\|DIP_RATIO\|DIP_FLOOR\|VerdictLevel" app tests` — пусто (вердикт снят, п. 3а).
- [ ] `grep -rn "_get_reserve_sum_for_month\|get_budget_progress" app/services/money_layers_service.py` — пусто.
- [ ] `grep -rn "exc_info" app/components/dashboard.py` — пусто (единственное вхождение было в удалённом хелпере; NFR-2, критика №4).
- [ ] Открыть `/` и `/dashboard`: нет ошибок в консоли про nonexistent object `period-switcher`, `dashboard-overview-cards`, `dashboard-statistics-card`, `dashboard-greeting`, `daily-cashflow-chart`.
- [ ] AC-1: число в шапке == высота зелёной полосы «сегодня» (hover) == `days[0]['free']`; разбор арифметически сходится.
- [ ] **п. 3г вручную:** в шапке нет приветствия; справа аватар-эмодзи и имя; после правки имени/аватара в модале профиля шапка обновляется без перезагрузки страницы (подписка `profile-updated` жива); в логах — **один** запрос профиля за рендер, не два.
- [ ] AC-3 вручную: на наполненной базе для 3 произвольных дней (один до, один после границы месяца) сумма слоёв из hover == остаток того же дня в `/calendar`.
- [ ] **Формула, частичный взнос:** `fixed_date`, бюджет 15 000, резерв 25-го, взнос **5 000** — синяя полоса сегодня содержит ровно 5 000 бюджета целей поверх порога подушки; не 0 и не 15 000.
- [ ] **Формула, симметрия:** `from_balance`, бюджет 15 000, взнос 5 000 с датой **в будущем** этого месяца — синяя полоса содержит 10 000 бюджета целей, взнос виден в оранжевом слое.
- [ ] **Формула, граница месяца:** `fixed_date`, резерв 25-го, взносов нет — синяя полоса на последнем дне месяца, на 1-м числе следующего и на дне после резерва следующего месяца равна порогу подушки, **не растёт** к правому краю окна.
- [ ] **🟡№1 / п. 3в вручную (бюджет уменьшен):** бюджет 15 000 → взнос 5 000 → бюджет снижен до 8 000. Синяя полоса = порог подушки (бюджет целей 0); в тултипе слоя «Резерв» **нет** признака перерасхода (промолчать — решение владельца); числа разбора сходятся с суммой слоёв.
- [ ] **🟡№1 / п. 3в вручную (бюджет увеличен):** бюджет 8 000 → полный взнос 8 000 → бюджет поднят до 20 000. Синяя полоса = порог + 12 000; «Свободно» занижено на 12 000 (безопасная сторона), инвариант AC-3 держится.
- [ ] **🟡№2 вручную (перенесённый exception):** создать exception инстанса резерва следующего месяца, затем перенести его дату **за правый край окна** (в пределах того же месяца, что и правый край). На правом крае окна синяя полоса **не** держит бюджет этого месяца — операция учтена в `committed`; «Свободно» не завышено.
- [ ] **п. 3б:** день с остатком ниже порога подушки — синяя полоса упирается в остаток, тултип называет ФАКТ дня и настройку рядом; цифра тултипа == высота полосы.
- [ ] AC-4: hover и Tab-фокус на легенде «Платежи» → список с датами; проверить месяц без платежей (тултип объясняющий, не пустой).
- [ ] AC-5: чистая база — шапка и график в пустом состоянии, в DOM нет `dcc.Graph` от графика слоёв.
- [ ] Отдельно: база с историей и пустым окном → **график рисуется** (плоская стопка).
- [ ] AC-6: кнопка в шапке и кнопка в баннере обе открывают модал сверки; сверка применяется; вход с `/calendar` не сломан.
- [ ] Шестерёнка в шапке открывает модал профиля; клик по аватару в сайдбаре — тоже (обе ветки живы).
- [ ] **🟢№5:** подписей на оси не больше 11 (для 45 дней — 10); первая подпись == `reference_date`, последняя == `window_end`; склеек нет.
- [ ] Границы: `reference_date` = последний день месяца (`payments == 0` всюду, `consumed` считается от 1-го числа); `reference_date` = 1-е число; февраль; переход через год.
- [ ] NFR-1: замер времени рендера на наполненной базе — < 2 сек и не хуже прежнего; в логах ровно один `calculate_daily_balances`, ровно один `get_all_transactions_for_period` и ровно **один** `get_profile` от дашборда.
- [ ] NFR-2: monkeypatch-падение чтения `monthly_budget` → трейсбек через `logger.opt(exception=True)`, `degraded=True`, в шапке видна сноска, дашборд рендерится. Отдельно: чистая база **не** генерирует варнинг-с-трейсбеком.
- [ ] `black --check app tests` и `flake8 app tests` — без новых замечаний.
- [ ] Wishlist-виджет, таблицы недавних/предстоящих операций и карточка подушки на месте и живые (C-1).

## Учтённые замечания из критики

| Замечание из critique v3 | Как решено |
|---|---|
| 🟡 №1. Изменение бюджета в середине месяца рассинхронизирует формулу с живущим exception — `goals_part` врёт в обе стороны; `max(0,…)` молча съедает перерасход; вход отсутствует и в 9 кейсах, и в блоке A | **Формула не меняется — допущение объявлено, поведение зафиксировано решением владельца (п. 3в: промолчать).** (1) Докстринг `_goals_part_by_day` получил раздел «ДОПУЩЕНИЕ "БЮДЖЕТ НЕ МЕНЯЛСЯ ВНУТРИ МЕСЯЦА"» с доказательством по коду (`sync_template_amount` `:808-839` обновляет только `template.amount`; `recalculate_current_month_exception` вызывается из путей взноса и содержит guard `:263-265`) и **обоими направлениями ошибки**: при уменьшении бюджета числа корректны, теряется только информация о превышении; при увеличении «Свободно» занижается — безопасная сторона. (2) В блок A шага 6 добавлены **два параметра** с числами по трём слоям: **кейс 10** (бюджет 15 000 → взнос 5 000 → бюджет 8 000: `goals_part == 0`, `reserve_configured == 30 000`) и **кейс 11** (бюджет 8 000 → полный взнос → бюджет 20 000: `goals_part == 12 000`, `reserve_configured == 42 000`); оба вошли в «Численную трассировку» как кейсы 10–11. (3) Третий пункт рекомендации критика («нужно ли различать "бюджет исчерпан" и "обещано больше бюджета"») закрыт **решением владельца п. 3в: не различать, признака в UI не вводить** — цифры корректны, теряется только информация о превышении; пометка в тултипе отброшена как лишняя сущность, вопрос отнесён к открытому №9 ROADMAP (жизненный цикл целей / превышение). Ассерт «признака перерасхода в контракте нет» включён в кейс 10 блока A и в ручной чек-лист — решение «промолчать» защищено тестом, а не подразумевается. Оценка шага 6: 9 → 9.5 ч |
| 🟡 №2. Exception с перенесённой датой (`new_date`) выпадает из `savings_by_date`: `committed` недосчитывается, «Свободно» завышается; направление ошибки неопределённо | **Механика проверена самостоятельно, результат точнее исходного, и все четыре пункта рекомендации исполнены.** Проверка дала три уточнения к диагнозу: (а) параметр `create_exception(new_date=...)` (`recurring_service.py:405`) **не имеет ни одного вызывающего** — grep по `new_date` даёт только сам модуль и не связанную локальную переменную в `calendar.py:816-822`; все три call-site (`budget_reservation_service.py:294`, `:916`, `transaction_modals.py:1163`) передают только `original_date`. Расхождение достижимо **двухшаговым** путём UI (создать exception → изменить дату в модале правки: `TransactionService.update_transaction` `:236-243` присваивает `transaction_date` и `original_date` не трогает). (б) **Правила отбора у нашего сбора и у расчёта баланса ОДИНАКОВЫ** — обе стороны идут через `get_instances_with_exceptions` (отбор по `original_date` `:691-695`, раскладка по `transaction_date` — `calendar_service.py:845` у нас, `:353-357` у баланса). Значит «обратный случай» критика (`original_date` вне диапазона, дата внутри) расхождения между слоями и балансом **не даёт**: баланс её тоже не видит, потому что `_calculate_recurring_before_date` (`:396-406`) считает только income/expense и savings игнорирует — это уже названный латентный дефект, а не новый. (в) Реально расходящихся случаев два, оба разобраны с направлением. Исполнено: **(1)** докстринг `_collect_operations` фиксирует ключевание по **фактической** дате операции, отсутствие фильтра по границам окна и механику расхождения дат со ссылками на код; **(2)** savings-операции с датой за `window_end` **не отбрасываются** — `committed(D)` суммирует до `month_end(D)` включительно (один дополнительный `if` при построении суффиксных сумм, шаг 4), направление правки консервативно («Свободно» не завышается); **(3)** в блок F шага 6 добавлен тест «exception перенесён в другой месяц» с числами по трём слоям для двух дней (кейс 12: D = 30 сент → `goals_part == 15 000`; D = 5 окт → `goals_part == 0`, тогда как v3 дал бы 15 000) + assert наличия ключа за `window_end` в `savings_by_date`; **(4)** остающийся случай (перенос внутри текущего месяца с даты до `reference_date`) назван **ограничением с направлением ошибки** — «Свободно» **завышается**, инвариант AC-3 слеп; ограничение привязано к латентному дефекту `_calculate_recurring_before_date`, который C-3 не даёт править, и записано в осадок одним пунктом со своей причиной. Ответ на `[факт]`-вопрос дан явно в разделе «Ответы на вопросы критика» |
| 🟢 №3. `build_free_header(data, profile)` принимает профиль и одновременно вызывает `_build_greeting_text()`, открывающий вторую сессию; бюджет вызовов NFR-1 короче реальности на один запрос | **Закрыто решением владельца п. 3г — развилка снята вместе с приветствием.** Приветствие с дашборда **убирается**, `_build_greeting_text()` из шапки не вызывается и вообще удаляется (см. 🟢№4). Профиль читается **один раз** в `_load_dashboard_components` и передаётся аргументом; параметр `profile` осмыслен — он единственный источник имени и аватара в правом блоке шапки, что буквально воспроизводит эскиз (`v3.html:415-418`: 🦊 + «Иван» + шестерёнка, приветствия в эскизе нет вовсе). **Строка бюджета вызовов NFR-1 поправлена:** добавлен явный пункт «1 `OnboardingService.get_profile`» и явно указано, что второе чтение профиля через хелпер **ушло** относительно v3. Шаг 8 подешевел (2.5 → 2 ч) — состав шапки на один элемент короче. Пункт «в логах ровно один `get_profile`» добавлен в NFR-1-проверку чек-листа |
| 🟢 №4. `exc_info=True` в сохраняемом `_build_greeting_text` остаётся «пустым» для loguru — стоит назвать это явно в NFR-2 как п.10 аудита вне scope | **Замечание уходит физически, а не оговоркой.** Проверено по коду: у хелпера ровно **два** вызывающих — `dashboard.py:111` (элемент layout `dashboard-greeting`) и `:1386` (7-й Output `load_dashboard_data`), и **оба снимаются этим куском** по решению владельца п. 3г. Третьего вызывающего нет (`grep -rn "_build_greeting_text" app/ tests/`). Следовательно хелпер — мёртвый код, и он **удаляется** на шаге 12 вместе с прочим мёртвым кодом дашборда; `logger.warning(..., exc_info=True)` (`:90`) исчезает вместе с телом функции. Ссылка на п.10 аудита не нужна: правка полна, а не частична. Сопутствующее: `TestBuildGreetingText` (`tests/test_dashboard_callbacks.py:73-102`) и импорт `:20` удаляются — тесты удалённой функции не оставляем; в чек-лист добавлены `grep -rn "_build_greeting_text\|dashboard-greeting"` и `grep -rn "exc_info" app/components/dashboard.py` — оба должны быть пусты. Состав правок теста пересмотрен с трёх позиций до четырёх, оценка шага 13: 1.5 → 2 ч. Регрессионная защита протокола 0026 не ослаблена: `Input("profile-updated","data")` сохранён у обоих callback'ов, тесты `:50`/`:57` не трогаются |
| 🟢 №5. `TARGET_X_TICKS = 11` при фактических 12 подписях — имя обещает результат, которого функция не даёт | **Исполнены оба варианта критика сразу: переименование + формула, не превышающая потолок.** Константа переименована в **`MAX_X_TICKS`** (семантика «потолок», не «цель»), формула `_axis_tickvals` меняет `round` на `ceil`: `k = max(1, ceil(len / MAX_X_TICKS))` — для 45 дней `k = 5` → индексы 0, 5 … 40 (9 подписей) + принудительно `window_end` = **10 подписей**, что `<= MAX_X_TICKS` **по построению**, а не по совпадению. Заодно объявлено, почему потолок честнее цели: проверено по эскизу — там ровно 11 подписей, но с **неравномерным** шагом (22/25/28 авг, 1/5/10/15/20/25/30 сент, 5 окт — `v3.html:575-596`), то есть семантически значимые даты; равномерная сетка эскиз не воспроизводит в принципе, воспроизводима только плотность. Расхождение с эскизом по числу тиков (10 против 11) зафиксировано строкой RTM и записью в осадок; в чек-лист добавлены пункты «подписей не больше 11», «первая == `reference_date`, последняя == `window_end`» и `grep -rn "TARGET_X_TICKS"` → пусто |

## Ответы на вопросы критика

**[факт] Фильтруется ли `savings_by_date` по границам окна, или в него попадают все savings-операции собранного диапазона независимо от даты? От ответа зависит, выпадает ли перенесённый через `new_date` exception из `committed(D)`.**

**В v3 поведение действительно не было определено — критик прав, что два утверждения решения («по ВСЕМУ диапазону сбора» в `_collect_operations` и `window_dates` на входе `_goals_part_by_day`) не задают ответ для даты за `window_end`. В v4 ответ дан явно: `savings_by_date` НЕ фильтруется по границам окна, ключуется по фактической дате операции, а `committed(D)` суммирует до `month_end(D)` включительно, даже если `month_end(D) > window_end`.**

Доказательство механики по коду, включая три уточнения к диагнозу критика:

1. **Как операция может получить дату вне запрошенного диапазона.** `get_all_transactions_for_period(u, S, E)` для recurring-части вызывает `RecurringService.get_instances_with_exceptions(u, S, E)` (`calendar_service.py:820-822`). Внутри: exceptions отбираются `get_exceptions_for_template(template.id, S, E)` по **`original_date`** (`recurring_service.py:390-393`), кладутся в словарь по ключу `(template.id, exc.original_date)` (`:695`), и подставляются вместо виртуального инстанса, если ключ совпал с `instance_date` (`:704-710`). Вызывающий раскладывает возвращённый exception по **`transaction_date`** (`calendar_service.py:845`). У exception с расхождением дат `transaction_date` может лежать вне `[S, E]` — значит `savings_by_date` физически может содержать такой ключ, и решение обязано сказать, что с ним делать.

2. **Уточнение первое: `new_date` — API без вызывающих.** `grep -rn "new_date" app/` даёт только `app/services/recurring_service.py` (`:405` сигнатура, `:415` докстринг, `:464-465` ветка обновления, `:484` создание) и **не связанную** локальную переменную в `app/components/calendar.py:816-822` (навигация по месяцам). Все три реальных вызова `create_exception` — `budget_reservation_service.py:294`, `:916` и `transaction_modals.py:1163` — передают только `original_date` (+ сумма/описание), то есть создают exception с **совпадающими** датами. Через `new_date` вход недостижим вовсе.

   **Он достижим двухшаговым путём.** `process_recurring_edit_scope` создаёт exception для виртуального инстанса с `transaction_date == original_date == instance_date` (`transaction_modals.py:1159-1166`), возвращает его `id` в модал правки, и дальше пользователь может изменить дату: `TransactionService.update_transaction` присваивает `transaction.transaction_date = transaction_date` (`transaction_service.py:236-243`) и **`original_date` не трогает нигде**. Вход реален, но узок — требует ручного переноса конкретного экземпляра регулярной savings-операции.

3. **Уточнение второе (главное): правила отбора у нас и у баланса одинаковы, поэтому «обратный случай» расхождения между слоями и балансом не даёт.** Критик предполагал разные правила у двух сторон. По коду — одно: `calculate_daily_balances` → `_get_recurring_daily_changes(u, S', E')` → `_get_recurring_instances_for_period` → **тот же** `get_instances_with_exceptions(u, S', E')`, и раскладка тоже по `instance.transaction_date` (`calendar_service.py:353-357`). Разница только в **диапазонах** вызова. Отсюда три случая:

   | Случай | `original_date` | `transaction_date` | Наш сбор `[collect_start, window_end]` | Баланс окна `(ref, window_end)` | Расхождение слоёв и баланса |
   |---|---|---|---|---|---|
   | Сдвиг вправо | в диапазоне | `> window_end` | **видит** (ключ за окном) | не видит | **было в v3** → исправлено правкой (+1 `if`) |
   | Сдвиг влево за `collect_start` | `< collect_start` | в окне | не видит | не видит (тот же отбор) | **нет.** Баланс её тоже теряет, потому что `_calculate_recurring_before_date` (`:396-406`) считает только income/expense и savings игнорирует — это уже названный латентный дефект, а не новый |
   | Сдвиг внутри месяца | в `[collect_start, ref−1]` | в окне | **видит** | не видит (`original_date < ref`) | **есть**, направление: «Свободно» **завышается** |

4. **Что сделано.** Случай «сдвиг вправо» **исправлен**: фильтр по `window_end` снят, `committed(D)` учитывает операцию, если её фактическая дата `<= month_end(D)`. Это ровно один дополнительный `if`, как и предлагал критик, и он консервативен по направлению (учёт уменьшает `goals_part` → «Свободно» не завышается). Кейс 12 «Численной трассировки» показывает числа: при резерве 25 сент, перенесённом на 8 окт, D = 5 окт даёт `goals_part = 0` (v3 дал бы 15 000). Тест — в блоке F шага 6, с числами по трём слоям для двух дней.

   Случай «сдвиг внутри месяца» **назван ограничением с направлением ошибки** (докстринг `_goals_part_by_day`, риск в таблице, запись в осадок): «Свободно» завышается на сумму операции, инвариант AC-3 этого не поймает. Исправление требует правки `_calculate_recurring_before_date`, что запрещено C-3, — поэтому ограничение записано **одним пунктом с латентным дефектом, чьим следствием оно является**, а не как отдельный дефект модели. Молчания, которое «читается как проверено», больше нет.

**[решение] Что должна показывать модель, когда `consumed(D) + committed(D) > monthly_budget` (бюджет снижен после того, как операции месяца зафиксированы при большем)? Приемлемо ли молчаливое `max(0, …)`, или случай «обещано целям больше текущего бюджета» заслуживает признака в тултипе слоя «Резерв»?**

**Закрыто решением владельца** (`memory/spec-context/epic-11.md`, п. 3в, 2026-08-24): **промолчать**. Когда целям обещано больше текущего бюджета, `goals_part` обрезается до нуля **без признака в UI**. Дословное основание владельца: «цифры остаются корректными, теряется только информация "обещано сверх бюджета"». Вариант (б) критика — пометка в тултипе слоя «Резерв» — **отброшен** как лишняя сущность: жизненный цикл целей и превышение цели держатся отдельным открытым вопросом ROADMAP №9 (пп. 5/7 аудита), и вводить для них половинчатый признак в куске 1 значит закреплять решение раньше, чем оно принято.

Обоснование корректности «цифр» проверяемо: в сценарии кейса 10 (бюджет 15 000 → взнос 5 000 → бюджет снижен до 8 000) exception 25 авг = 10 000 остаётся в силе, эти 10 000 физически лежат в остатке и видны в **оранжевом** слое, откуда уйдут 25-го. Синий слой их не держит — и правильно, что не держит: держать значило бы вычесть дважды. Инвариант AC-3 не нарушен, разбор в шапке сходится. Утрачивается ровно один бит: «обещано на 2 000 больше, чем настроено».

**Требование к проектированию, которое владелец сохранил, исполнено полностью:**
- допущение «бюджет не менялся внутри месяца» объявлено **явно** в докстринге `_goals_part_by_day` — с доказательством по коду (`sync_template_amount` `:808-839` обновляет только `template.amount`; guard `if reserve_date < date.today(): return` в `recalculate_current_month_exception` `:263-265`) и с **обоими** направлениями ошибки;
- **два параметра** добавлены в блок A шага 6 и в «Численную трассировку» как кейсы 10–11: бюджет уменьшен после частичного взноса (`goals_part == 0`, `reserve_configured == 30 000`) и бюджет увеличен после полного (`goals_part == 12 000`, `reserve_configured == 42 000`), оба — числами по всем трём слоям;
- решение «промолчать» **защищено тестом**, а не подразумевается: кейс 10 блока A содержит ассерт отсутствия признака перерасхода в контракте, и тот же пункт есть в ручном чек-листе. Это важно, потому что «промолчать» — такое же решение, как «показать», и без ассерта его легко потерять при следующей правке.

Различие «`goals_part` = 0, потому что бюджет исчерпан» и «= 0, потому что обещано больше бюджета» модель **сознательно не различает** — это прямой ответ на третий пункт рекомендации критика, сказанный явно, а не оставленный на догадку.

**[решение] Приветствие в шапке строится из переданного `profile` или через сохраняемый `_build_greeting_text()`, который открывает собственную сессию?**

**Развилка снята целиком: приветствия в шапке нет.** Решение владельца (`memory/spec-context/epic-11.md`, п. 3г, 2026-08-24): **приветствие «Привет, {имя}» с дашборда убирается**; в шапке остаются только аватарка и имя справа, «главное место отдано цифре, не вежливости». Оба варианта критика оказались вариантами одного вопроса, которого больше нет.

Решение согласовано с двумя независимыми источниками, и это стоит зафиксировать, потому что снятие элемента легко принять за потерю: (1) **спека приветствия не требует** — FR-2.d просит «справа — аватар пользователя и служебная иконка настроек», и приветствие было унаследованным элементом текущего дашборда (`dashboard.py:108-112`, протоколы 0024/0026), а не требованием эпика; (2) **в принятом эскизе приветствия нет вовсе** — правый блок шапки это `🦊` + «Иван» + шестерёнка (`v3.html:415-418`), и v3 добавлял приветствие сверх эскиза. Поэтому в RTM это зафиксировано отдельной строкой как **снятие унаследованного элемента решением владельца**, а не как отступление от спеки.

**Судьба хелпера и его тестов решена — удаление, и это проверено, а не предположено.** `grep -rn "_build_greeting_text" app/ tests/` даёт ровно: `dashboard.py:82` (определение), `:111` (элемент layout), `:1386` (7-й Output callback'а), `tests/test_dashboard_callbacks.py:20` (импорт), `:90`, `:100` (вызовы в тестах). Оба продуктовых вызывающих снимаются этим куском — `:111` вместе с элементом `dashboard-greeting`, `:1386` вместе с Output'ом. Третьего вызывающего нет, значит хелпер становится мёртвым кодом и удаляется на шаге 12 (вместе с `build_overview_cards`, старыми графиками и прочим), а `TestBuildGreetingText` (`:73-102`) и импорт `:20` удаляются как тесты удалённой функции.

Три следствия исполнены:
- **лишний запрос профиля снят по построению** (замечание №3): хелпер открывал собственный `get_db_session()` (`:82-91`) при уже переданном `profile`; теперь профиль читается один раз в `_load_dashboard_components`, а `profile` осмыслен как единственный источник имени и аватара. Строка бюджета вызовов NFR-1 поправлена: добавлен пункт «1 `OnboardingService.get_profile`» и указано, что второе чтение ушло;
- **«пустой» для loguru `exc_info=True`** (`:90`, замечание №4) исчезает вместе с телом функции — оговорка «п.10 аудита вне scope» не нужна, правка полна. В чек-лист добавлен `grep -rn "exc_info" app/components/dashboard.py` → пусто;
- **дух протоколов 0024/0026 соблюдён строже, чем в v3**: отдельного Output/callback'а на приветствие не появляется, потому что нет приветствия; регрессионная защита подписки на `profile-updated` не ослаблена — `Input("profile-updated","data")` остаётся у `load_dashboard_data` и `toggle_balance_toast`, оба соответствующих теста (`:50`, `:57`) не трогаются, и имя с аватаром в шапке обновляются тем же Input'ом через первый Output шапки.

Состав правок `tests/test_dashboard_callbacks.py` пересмотрен с трёх позиций до четырёх, оценка шага 13: 1.5 → 2 ч (удаление класса тестов + переориентация ассерта приветствия на имя профиля в шапке + докстринг модуля `:1-12`, где «7-й Output» заменяется на «приветствие снято решением владельца п. 3г; имя и аватар обновляются первым Output'ом шапки»).
