# Solution v3: `PanelData` за одну сессию, «вчера» из расширенного списка дат хелперов, сайдбар без Output-колбэков

## Обзор решения

v3 сохраняет скелет v2 (единый композитор `DashboardPanelService`, `dcc.Link` вместо серверных колбэков, поблочная деградация, контракт владения `url.search`) и меняет ровно то, что поймала критика v2 — при этом **каждое утверждение о существующем коде в этой версии выведено из прочитанного тела функции**, а не из подписи или докстринга.

Пять содержательных изменений относительно v2:

1. **«Вчера» считается одним вызовом хелперов на расширенном списке дат (Подход A критика).** Критик прав: `_payments_tail_by_day` (`money_layers_service.py:423-462`) — **оконная**, а не точечная функция. Прочитано тело: `by_day` собирается по всему списку `payments`, но затем `result` наполняется проходом `for day in reversed(window_dates)`, и `tail` накапливается **из того же списка**. На `window_dates=[yday]` цикл делает одну итерацию, `tail` ещё `Decimal("0")`, `yday < payments_end` → `result[yday] = Decimal("0")`. Плюс подпись действительно `(payments, window_dates, payments_end)` — в v2 аргументы были переставлены. v3 передаёт **`calc_dates = [yday] + window_dates`** одним вызовом и берёт из результата и `yday`, и дни окна; `days` строится по-прежнему только из `window_dates`.
2. **`_goals_part_by_day` от состава списка НЕ зависит — перепроверено по телу.** Прочитано (`:579-599`): внешний цикл `for day in window_dates`, внутри — полный обход `savings_by_date.items()` с фильтром `month_start(day) <= op_date <= day` / `day < op_date <= month_end(day)`. Результат для ключа `yday` не зависит от того, какие ещё даты в списке. Значит `calc_dates` для него безвреден, и передавать его туда же — правильно (один список для обоих хелперов, а не два разных).
3. **Сайдбар: чтение профиля переезжает в построение, оба колбэка удаляются (Подход B критика, решение владельца).** Прочитано `create_sidebar()` (`sidebar.py:57-146`): **аргументов нет, сессия не открывается**, в `sidebar-profile-avatar` литерал `"\U0001f60a"` (`:65`), в `sidebar-profile-name` литерал `"Пользователь"` (`:82`), `_build_nav_links("/dashboard")` захардкожен (`:106`). Утверждение v2 «`create_sidebar` уже читает профиль» было ложным. v3: `create_sidebar(pathname, profile)` — чистая функция; `render_sidebar_slot(pathname, profile_updated)` — один колбэк, два Input'а на всегда присутствующие элементы, одна сессия внутри; `highlight_active_sidebar` **и** `update_sidebar_profile` удаляются **оба**.
4. **`_goals_block` читает `User` напрямую — отсутствие пользователя = `EMPTY`, не `FAILED`.** Прочитаны тела: `get_savings_budget` (`goal_service.py:458-476`) = `session.get(User, uid)` → `raise ValidationError` если нет → `return user.monthly_savings_budget`; `get_savings_mode` (`:512-529`) = тот же `session.get(User, uid)` → `raise ValidationError` → `return user.savings_mode`. Поля те же, что и нужны, и тот же `User`, который блоку и так нужен для `cushion_target`. v3 читает `session.get(User, uid)` один раз и берёт три поля; `user is None` → `EMPTY` (симметрично `_user_data_markers`, `money_layers_service.py:812-830`, где «чистая база штатна»).
5. **`OperationRow` приводится к типам явно.** Прочитано `_map_transactions` (`dashboard_service.py:456-472`): `date=t.transaction_date.isoformat()` — **строка**; `transaction_type=t.transaction_type.value` — строка из шести значений enum; поле называется `is_recurring_instance`, не `is_recurring`. Прочитан `format_date_human` (`formatters.py:119-128`): `date_obj.day` — на строке даст `AttributeError`, то есть блок ушёл бы в `FAILED` на нормальных данных. v3 задаёт явное преобразование и таблицу сведения шести значений `transaction_type` в три `kind`.

Плюс: расхождение цифры «Аналитика» с месячным слоем «Платежи» объявлено (решение владельца), единая механика идемпотентности Store-фокусов, `_is_empty` через `savings_by_date` признан зависимым от `collect_start`, «было 3 сессии», одна константа lookback, `dip_*` игнорируется при `EMPTY`.

## Архитектура

### Компоненты

**Сервисный слой (новое)**

| Компонент | Файл | Роль |
|---|---|---|
| `DashboardPanelService` | `app/services/panel_service.py` (новый, ~360 строк) | Read-only композитор: одна сессия, один `PanelData`. Знает `MoneyLayersService`, `GoalService`, `AllocationService`, `DashboardService`, `AnalyticsService`, `WishlistService` + прямое чтение `User`. **Не знает** `CushionService`. О Dash не знает (C-2). |
| схемы карточек | `app/schema/panel.py` (новый, ~215 строк) | `PanelData`, `CalendarCardData`, `GoalsCardData`, `OperationsCardData`, `AnalyticsCardData`, `WishlistCardData`, `CardStatus`, таблица `kind`. Без `is_new_user`, без `DIP_STRONG_THRESHOLD`. |
| расширение модели слоёв | `app/schema/money_layers.py`, `app/services/money_layers_service.py` | ОДНО новое поле `yesterday: DayLayers \| None` + локальный `calc_dates` в `get_money_layers`. `days`, `today`, `min_free`, `is_empty`, `window_is_flat` — форма не меняется. |

**Презентационный слой**

| Компонент | Файл | Роль |
|---|---|---|
| ряд дверей + build-функции | `app/components/panel_cards.py` (новый, ~620 строк) | `build_cards_row(PanelData)` + чистые `build_*_card(...)`. Без БД, тестируются словарями. |
| щиток | `app/components/dashboard.py` | Layout без split-таблиц/подушки/wishlist-виджета; `_load_dashboard_components` → 3 Output'а; один новый clientside-триггер. |
| каркас | `app/main.py` | `sidebar-slot` + `render_sidebar_slot` (**единственный** колбэк сайдбара); расширенный разбор query params с контрактом владения `search`; три новых Store'а. |
| сайдбар | `app/components/sidebar.py` | `create_sidebar(pathname, profile)` — **чистая функция без БД и без колбэков**. Оба колбэка файла удаляются. |
| приёмники контекста | `app/components/calendar.py`, `app/components/goals.py` | Минимальные Input'ы на новые Store'ы + единая механика идемпотентности (C-1). |
| стили | `app/assets/panel.css`, `custom.css`, `sidebar.css`, `calendar.css` | Секции `.pnl-slots`/`.pnl-door*`/`.pnl-wish*`; снятие `.db-*` раскладки 8/4. |

### Диаграмма взаимодействия

```
Открытие /dashboard
  url.pathname ──► load_dashboard_data (dashboard.py)
  │                  └─ _load_dashboard_components()
  │                       with get_db_session() as session:      ← ОДНА сессия
  │                         DashboardPanelService(session).get_panel_data(uid)
  │                           ├─ MoneyLayersService.get_money_layers()  (сбой НЕ глотаем)
  │                           │    calc_dates = [ref-1] + window_dates   ← НОВОЕ
  │                           │    payments_tail = _payments_tail_by_day(payments,
  │                           │                        calc_dates, payments_end)
  │                           │    goals_part    = _goals_part_by_day(savings_by_date,
  │                           │                        calc_dates, monthly_budget)
  │                           │    days      = [_split_day(d) for d in window_dates]
  │                           │    yesterday = _split_day(...[ref-1]...)  ← из ТЕХ ЖЕ dict
  │                           ├─ try: _goals_block()      session.get(User) + Goal + Allocation
  │                           ├─ try: _operations_block()  DashboardService (recent/upcoming)
  │                           ├─ try: _analytics_block()   AnalyticsService.get_expenses_by_category
  │                           └─ try: _wishlist_block()    WishlistService.get_focus + to_data
  │                       → PanelData: ТОЛЬКО Decimal/date/str/bool/int
  │                  ├─► build_free_header(data["layers"], profile)  (кусок 1, 0 правок)
  │                  ├─► build_layers_chart(data["layers"])          (кусок 1, 0 правок)
  │                  └─► build_cards_row(data)  →  5 × <дверь>
  │
  └──► render_sidebar_slot(pathname="/dashboard", …) → []   ← сессии НЕТ на дашборде

Переход на /calendar (или любой раздел)
  url.pathname ─┐
  profile-updated ─┴─► render_sidebar_slot   ← ЕДИНСТВЕННЫЙ колбэк сайдбара
                        with get_db_session():  ← ОДНА сессия (цена Подхода B)
                          profile = OnboardingService.get_profile(uid)
                        return create_sidebar(pathname, profile)  ← чистая функция

Клик по элементу двери
  «вчера»/«сегодня»/«завтра» ─ dcc.Link href="/calendar?focus_date=<ISO>"
  маркер просадки            ─ dcc.Link href="/calendar?focus_date=<dip ISO>"
  цель                       ─ dcc.Link href="/goals?goal=7"
  группа операций            ─ dcc.Link href="/transactions?start=…&end=…"
  «Аналитика»                ─ dcc.Link href="/analytics"
  тело/заголовок Wishlist    ─ clientside → Store open-wishlist-trigger → wishlist.py
  конкретная хотелка         ─ dcc.Link href="/calendar?wishlist_item=3"  (механизм 0023)

Приёмники (main.py handle_panel_query_params) — ВЛАДЕНИЕ url.search ПО PATHNAME
  /calendar  : open_recon | wishlist_item | focus_date → ЧИСТИТ search
  /goals     : goal                                    → ЧИСТИТ search
  /transactions : PreventUpdate — search принадлежит разделу (apply_url_date_filter, 0023)
  прочее     : PreventUpdate

Идемпотентность фокусов (замечание №7) — ОДНА механика на оба Store'а
  приёмник реагирует ТОЛЬКО если ctx.triggered_id == сам Store
  И payload["ts"] != state.get("focus_applied_ts")   ← сравнение с calendar-state
```

## Файловая структура

```
app/
  schema/
    panel.py                    NEW  — TypedDict-контракты карточек + таблица kind
    money_layers.py             MOD  — ОДНА константа lookback + поле yesterday
    __init__.py                 MOD  — реэкспорт схем панели
  services/
    panel_service.py            NEW  — DashboardPanelService
    money_layers_service.py     MOD  — calc_dates + левая граница + _yesterday_slice
    __init__.py                 MOD  — экспорт DashboardPanelService
  components/
    panel_cards.py              NEW  — build_*_card, build_cards_row
    dashboard.py                MOD  — layout/колбэки/один clientside-триггер
    sidebar.py                  MOD  — create_sidebar(pathname, profile); ОБА колбэка удалены
    calendar.py                 MOD  — приёмник calendar-focus-date + focus_applied_ts
    goals.py                    MOD  — приёмник goals-focus-goal + anchor-id карточек
    wishlist.py                 MOD  — build_wishlist_widget удаляется ВМЕСТЕ с его Input'ом
    profile_modal.py            MOD  — единственный вход открытия — Store
    __init__.py                 MOD  — экспорты (снятие build_wishlist_widget)
  main.py                       MOD  — render_sidebar_slot (2 Input), query params, Store'ы
  assets/
    panel.css                   MOD  — .pnl-slots / .pnl-door* / .pnl-wish*
    custom.css                  MOD  — снятие .db-* раскладки 8/4
    sidebar.css                 MOD  — ОДИН механизм скрытия колонки
    calendar.css                MOD  — .calendar-day-focused
tests/
  test_panel_cards_ui.py        NEW  — визуальный слой карточек (стиль 0029)
  test_panel_service.py         NEW  — сборка PanelData, деградация, материализация,
                                       типы OperationRow, EMPTY без пользователя,
                                       смешанный случай, счётчик запросов
  test_money_layers_service.py  MOD  — ТОЛЬКО добавление: значение yesterday["payments"],
                                       инвариант, форма days, 1-е число, is_empty
  test_sidebar.py               NEW  — контракт входов render_sidebar_slot + профиль
  test_dashboard_callbacks.py   MOD  — 5 Output'ов → 3
  test_profile_modal_callbacks.py MOD — вход через Store
  test_dashboard_panel_ui.py    БЕЗ ПРАВОК (сохраняется из v2)
```

## Ключевые интерфейсы

### Расчёт «вчера»: один вызов хелперов на расширенном списке (блокер №1)

**Почему Подход A, а не «хвост `ref` + платежи дня `ref`».** Вторая формула для одного понятия — ровно та болезнь, от которой лечит весь кусок (FR-6). Расширенный список даёт верную семантику **по построению**: расхождение между `yesterday` и `days[0]` становится невозможным, а не «проверенным тестом».

```python
# app/services/money_layers_service.py :: get_money_layers
    ref = reference_date or date.today()
    horizons = self._horizons(ref)
    window_dates = [ref + timedelta(days=offset) for offset in range(WINDOW_DAYS)]

    # Служебный список дат ДЛЯ ХЕЛПЕРОВ — НЕ окно модели (critique-v2, блокер №1).
    # days строится ТОЛЬКО из window_dates; calc_dates нужен потому, что
    # _payments_tail_by_day — ОКОННАЯ функция: она накапливает суффиксную
    # сумму проходом по ПЕРЕДАННОМУ списку (:455-461), и на одноэлементном
    # списке вернула бы Decimal("0") для любого дня.
    yday = ref - LOOKBACK
    calc_dates = [yday] + window_dates          # строго возрастающий список

    balances = self._forecast_balances(user_id, yday, horizons.window_end)
    payments, savings_by_date = self._collect_operations(
        user_id, horizons.collect_start, horizons.window_end, ref
    )
    payments_tail = self._payments_tail_by_day(          # подпись:
        payments, calc_dates, horizons.payments_end      # (payments, window_dates, payments_end)
    )
    ...
    goals_part = self._goals_part_by_day(savings_by_date, calc_dates, monthly_budget)

    days: list[DayLayers] = []
    for day in window_dates:                    # ← ФОРМА days НЕ МЕНЯЕТСЯ
        ...                                     # тело цикла куска 1 без правок

    yesterday = self._yesterday_slice(
        balances, payments_tail, goals_part, cushion_threshold, yday
    )
```

**Что именно проверено в телах хелперов (не допущено):**

| Хелпер | Прочитанное тело | Следствие для `calc_dates` |
|---|---|---|
| `_payments_tail_by_day` (`:423-462`) | `by_day` собирается по всему `payments`; затем `for day in reversed(window_dates)`: `result[day] = 0 if day >= payments_end else tail`, потом `tail += by_day.get(day, 0)` | **Зависит от состава списка.** На `calc_dates` результат для `yday` = Σ платежей в `(yday, payments_end]` = `result[ref] + by_day.get(ref, 0)` — то есть хвост «сегодня» плюс платежи дня `ref`. Для дней окна значения **не меняются**: `yday` — самый левый элемент, а проход идёт справа налево, поэтому добавление элемента слева не влияет ни на один правый ключ. |
| `_goals_part_by_day` (`:462-599`) | `for day in window_dates:` → внутри полный обход `savings_by_date.items()` с фильтром `month_start(day) <= op_date <= day` (consumed) / `day < op_date <= month_end(day)` (committed); `result[day] = max(0, monthly_budget − consumed − committed)` | **Не зависит от состава списка** — критик прав, перепроверено. Значение каждого ключа функция от `day` и `savings_by_date`. Добавление `yday` даёт один лишний ключ и не меняет остальные. Передаём тот же `calc_dates`, чтобы список был **один** (два разных списка для двух хелперов — новая возможность разойтись). |
| `_split_day` (`:598-643`) | Три ветки: `balance < 0` → `(balance, 0, 0)`; `free >= 0` → как есть; иначе гашение `reserve`, затем `payments`. Сумма == `balance` во всех трёх | Применяется к `yesterday` **без правок**. Инвариант держится по построению — и **именно поэтому** тест инварианта блокер №1 не поймал бы (см. ниже). |
| `_window_min_free` (`:669-697`) | `if not days: return Decimal("0"), date.today()` — при пустом `days` возвращает **сегодня, не None**; иначе линейный поиск минимума по `days` | `yday` в `days` не входит → маркер не может уехать. Но на пустом окне `min_free_date` = `date.today()` и `min_free` = 0 — значит `dip_*` обязан игнорироваться при `EMPTY` (замечание №10). |
| `_is_empty` (`:751-810`) | `starting_balance != 0 → False`; `has_recurring_templates → False`; **`if payments or savings_by_date: return False`**; иначе `all(day["forecast_balance"] == 0 for day in days)` | `payments` защищён фильтром `day >= reference_date` (`:404`) — «вчера» в него не попадает. **`savings_by_date` — нет**: `_collect_operations` наполняет его без фильтра по датам (`:415-418`), по всему диапазону от `collect_start`. Критик прав (замечание №3). |
| `_horizons` (`:244-272`) | `collect_start=_month_start(ref)`, `window_end=ref+WINDOW_DAYS-1`, `payments_end=_month_end(ref)` | `collect_start` расширяется до `min(_month_start(ref), yday)` — иначе 1-го числа операций «вчера» нет в сборе. |
| `calculate_daily_balances` (`calendar_service.py:120-177`) | `current_balance = starting + before_period + recurring_before`, затем кумулятивный проход от `start_date`; `start_date > end_date` → `ValueError` | Сдвиг левой границы на день **не меняет** `balances[ref]`: значение на любом дне = стартовое + все изменения до него включительно, независимо от того, где начался проход. Заявление v2 подтверждено критиком и перепроверено по телу. |

```python
# app/schema/money_layers.py — ОДНА константа (замечание №9)
LOOKBACK = timedelta(days=1)
"""На сколько модель считает НАЗАД от reference_date — сверх окна.

Единственная константа этого понятия (critique-v2, №9: в v2 их было
две — WINDOW_LOOKBACK_DAYS и WINDOW_LOOKBACK_DAYS_TD). Тип timedelta,
а не int, потому что все три места использования — арифметика с date
(ref - LOOKBACK); int требовал бы timedelta(days=…) в каждом месте.

ВАЖНО: это НЕ расширение окна. days остаётся ровно WINDOW_DAYS дней
от reference_date — форма и смысл контракта куска 1 не меняются
(решение владельца 2026-08-25, «аккуратный вариант»). Константа
управляет ТОЛЬКО левой границей расчёта балансов, левой границей
сбора операций и служебным списком calc_dates, из которых считается
отдельное поле yesterday.
"""
```

```python
    def _yesterday_slice(
        self,
        balances: dict[date, Decimal],
        payments_tail: dict[date, Decimal],
        goals_part: dict[date, Decimal],
        cushion_threshold: Decimal,
        yday: date,
    ) -> DayLayers | None:
        """Слои за reference_date - LOOKBACK — вне цикла по days.

        Принимает УЖЕ ПОСЧИТАННЫЕ payments_tail и goals_part (оба
        считались один раз на calc_dates = [yday] + window_dates),
        а не вызывает хелперы повторно.

        ПОЧЕМУ ТАК, А НЕ ТОЧЕЧНЫМ ВЫЗОВОМ (critique-v2, блокер №1):
        _payments_tail_by_day — ОКОННАЯ функция. Её тело (:455-461)
        накапливает tail проходом по ПЕРЕДАННОМУ списку дат, поэтому
        на списке [yday] она вернула бы Decimal("0"): платежи дней
        ref…payments_end в by_day есть, но их дат в списке нет.
        Результат был бы правдоподобным (не ноль, не отрицательное),
        инвариант суммы сошёлся бы (_split_day сохраняет сумму при
        любом входе), и «Вчера» показало бы «Свободно» завышенным
        на всю сумму остатка платежей месяца.

        Считается ТЕМ ЖЕ _split_day и ИЗ ТЕХ ЖЕ словарей, что дни
        окна: расхождение способа счёта между «вчера» и «сегодня»
        было бы новым источником противоречащих цифр (FR-6).

        Returns:
            DayLayers | None: None, если balances не содержит дня
                (границы расчёта нарушены) — карточка нарисует
                прочерк, а не 0 ₽.
        """
        if yday not in balances:
            logger.warning(
                f"Баланс за {yday} отсутствует в расчёте (user-facing «вчера» "
                "будет прочерком) — проверить левую границу _forecast_balances"
            )
            return None

        reserve_configured = cushion_threshold + goals_part.get(yday, Decimal("0"))
        free, fact_payments, fact_reserve = self._split_day(
            balances[yday], payments_tail.get(yday, Decimal("0")), reserve_configured
        )
        return DayLayers(
            date=yday, free=free, payments=fact_payments, reserve=fact_reserve,
            reserve_configured=reserve_configured,
            forecast_balance=balances[yday],
        )
```

**Исправленный перечень границ.** Всё, чего в перечне нет, не трогается.

| Место | Было | Стало | Зачем |
|---|---|---|---|
| `_horizons.collect_start` (`:266`) | `_month_start(ref)` | `min(_month_start(ref), ref - LOOKBACK)` | 1-го числа «вчера» = последний день прошлого месяца; иначе его операции не собраны |
| `_forecast_balances(...)` (вызов `:138`) | `(user_id, ref, window_end)` | `(user_id, ref - LOOKBACK, window_end)` | без этого `balances.get(yday)` вернёт дефолт `Decimal("0")` — «Вчера — 0 ₽» на наполненной базе; инварианты держатся (0=0+0+0) |
| `window_dates` (`:135`) | `[ref + d for d in range(WINDOW_DAYS)]` | **без изменений** | форма `days` — контракт куска 1 |
| `calc_dates` | — | **НОВЫЙ** локальный `[yday] + window_dates` | вход хелперов; **не** окно модели |
| `_payments_tail_by_day` (вызов) | `(payments, window_dates, payments_end)` | `(payments, calc_dates, payments_end)` | **блокер №1**: функция оконная, точечный вызов даёт 0. Тело функции НЕ правится (C-3) |
| `_goals_part_by_day` (вызов) | `(savings_by_date, window_dates, monthly_budget)` | `(savings_by_date, calc_dates, monthly_budget)` | ключ для `yday`; значения дней окна не меняются (тело от состава списка не зависит) |
| `_horizons.window_end`, `payments_end` | — | **без изменений** | правая граница оси и горизонт платежей — решения куска 1 (C-5) |
| `_today_slice` (`:645-668`) | `days[0]` | **без изменений** | `days[0] == ref` по-прежнему верно |
| `_window_min_free` / `min_free`, `min_free_date` | по всему `days` | **без изменений** | `yday` в `days` не входит. **Но**: при пустом `days` возвращает `(Decimal("0"), date.today())`, а не `None` (`:690-691`) → `dip_*` игнорируется при `EMPTY`, см. №10 |
| `_is_empty` (`:751-810`) | 4 условия | **тело без изменений, но зависимость есть** | Третье условие `if payments or savings_by_date` смотрит на `savings_by_date`, который `_collect_operations` наполняет **без фильтра по датам** от `collect_start` (`:415-418`). Расширение `collect_start` на 1 день (только когда `ref` = 1-е число) может перевернуть `is_empty` с `True` на `False`. **Решение: принять** (см. ниже) |
| `window_is_flat` | `not is_empty and not payments and not savings_by_date` | **без изменений** | зависит от `savings_by_date` так же, как `_is_empty`, и в том же направлении: на 1-м числе с savings-операцией 31-го станет `False` вместо `True`. Направление безопасное — вместо «плоской стопки» рисуется обычный график с ненулевым синим слоем, что для такого пользователя честнее |
| `_split_day`, `_goal_milestones`, `_user_data_markers` | — | **без изменений** | не зависят от границ |
| `window_days()`-хелпер v1 | планировался | **не создаётся** | решение владельца |

**Решение по `_is_empty` (замечание №3): принять зависимость, задокументировать.** Фильтровать `savings_by_date` по `>= _month_start(ref)` при передаче в `_is_empty` — значит завести **второй** отфильтрованный словарь и второй смысл у одного имени; при этом достижимость сценария узкая (`ref` = 1-е число **и** `starting_balance == 0` **и** нет recurring-шаблонов **и** одна savings-операция в конце прошлого месяца **и** все балансы окна нулевые), а направление безопасное: вместо пустого состояния пользователь видит плоский график, то есть **больше** информации, а не меньше. Строка в докстринге `_is_empty`:

```python
        Note:
            ЗАВИСИМОСТЬ ОТ ГРАНИЦ СБОРА (кусок 2, critique-v2 №3).
            Условие «нет savings-операций» смотрит на savings_by_date,
            который _collect_operations наполняет ВЕСЬ собранный
            диапазон без фильтра по датам (:415-418). С куска 2
            collect_start = min(_month_start(ref), ref - LOOKBACK),
            поэтому 1-го числа месяца в диапазон попадает последний
            день предыдущего месяца. Savings-операция на этом дне
            даст is_empty=False у пользователя, который иначе получил
            бы True. Принято осознанно: сценарий узкий, направление
            безопасное (плоский график вместо «Добавьте первую
            операцию»), а фильтрация словаря завела бы второй его
            смысл. Покрыто тестом «1-е число + savings 31-го».
```

### Сайдбар: Подход B — ноль Output'ов на условно присутствующие элементы (блокер №2)

Решение владельца: одна сессия на построение сайдбара при переходе между разделами — приемлемая цена. На дашборде сессии нет вовсе (возвращается `[]`), бюджет NFR-1 (2 с против десятков мс) не задет, взамен у сайдбара не остаётся ни одного Output на условно присутствующий элемент.

```python
# app/main.py
html.Div(id="sidebar-slot", className="sidebar-column"),

@callback(
    Output("sidebar-slot", "children"),
    Input("url", "pathname"),
    Input("profile-updated", "data"),
)
def render_sidebar_slot(pathname: str | None, profile_updated: float | None):
    """Сайдбар есть на всех страницах, КРОМЕ дашборда (FR-2, AC-1).

    ЕДИНСТВЕННЫЙ колбэк сайдбара. Оба прежних — highlight_active_sidebar
    (Output sidebar-nav) и update_sidebar_profile (Output
    sidebar-profile-name/-avatar) — УДАЛЕНЫ (critique-v2, блокер №2;
    Подход B критика, принят владельцем).

    ПОЧЕМУ ОБА, А НЕ ОДИН (факт, проверенный по телу create_sidebar,
    sidebar.py:57-146): create_sidebar() НЕ открывала сессию и НЕ
    читала профиль — в sidebar-profile-avatar стоял литерал 😊 (:65),
    в sidebar-profile-name — литерал «Пользователь» (:82), а
    _build_nav_links получал захардкоженный "/dashboard" (:106).
    Реальные имя и аватар приходили ТОЛЬКО из update_sidebar_profile
    (:163-185). После снятия сайдбара с дашборда оба его Output'а
    становятся условно присутствующими, а один из Input'ов — тот же
    url.pathname, что здесь: это та же гонка, из-за которой удалён
    highlight_active_sidebar. Оставить колбэк с guard'ом = вернуться
    к «Пользователь» + 😊 после каждого перехода (регрессия Epic-09
    фазы 2). Поэтому чтение профиля переехало СЮДА, а create_sidebar
    стала чистой функцией от (pathname, profile).

    Оба Input'а — на элементы, присутствующие ВСЕГДА: dcc.Location
    "url" и dcc.Store "profile-updated" живут в глобальном layout
    (main.py:52, :90). Правило C-6 соблюдено с обеих сторон:
    ни Input, ни Output не смотрит на условно присутствующий узел.

    profile-updated как Input, а не State: правка профиля обязана
    перерисовать сайдбар (тот же Store уже слушает load_dashboard_data).
    Guard'а на пустой Store здесь НЕ нужно — колбэк идемпотентен:
    он не открывает модалов и не меняет навигацию, а перерисовка
    сайдбара тем же содержимым не наблюдаема.

    ЦЕНА (в «Стратегию загрузки» внесено явно): одна сессия и одно
    чтение профиля на каждый переход между разделами. На /dashboard
    сессии НЕТ — возвращается [] до открытия сессии. Сбой чтения
    профиля НЕ обрушивает сайдбар: except → literal-профиль
    («Пользователь», DEFAULT_AVATAR_ID) + logger.opt(exception=True),
    навигация остаётся рабочей (находимость разделов важнее имени).

    Колонка скрывается ОДНИМ механизмом — CSS-правилом
    .sidebar-column:empty { display: none } (critique-v1, №9).
    Поэтому className НЕ переключается и Output'а на него нет.

    ВАЖНО, класс регрессий C-6 «наоборот»: убирая сайдбар с дашборда,
    мы удаляем из DOM sidebar-profile-container — прямой Input
    handle_profile_modal (profile_modal.py:96). На /dashboard колбэк
    перестал бы отправляться ЦЕЛИКОМ, включая вход через шестерёнку
    → AC-9 красный. Поэтому вход через аватар тоже переводится на
    Store open-profile-trigger.
    """
    if pathname in (None, "/", "/dashboard"):
        return []                      # ← сессия НЕ открывается

    try:
        with get_db_session() as session:
            profile = OnboardingService(session).get_profile(DEFAULT_USER_ID)
    except Exception:
        logger.opt(exception=True).warning(
            "Не удалось прочитать профиль для сайдбара — "
            "рисуем сайдбар с профилем-заглушкой (навигация не теряется)"
        )
        profile = UserProfile(name="Пользователь", avatar_id=DEFAULT_AVATAR_ID)

    return create_sidebar(pathname, profile)
```

```python
# app/components/sidebar.py
def create_sidebar(pathname: str | None, profile: UserProfile) -> dbc.Card:
    """Сайдбар — ЧИСТАЯ функция: ни БД, ни колбэков, ни литералов профиля.

    Изменение куска 2 (critique-v2, блокер №2): оба колбэка файла
    удалены, обе их обязанности переехали в построение.

      * подсветка активного пункта: было
        highlight_active_sidebar (Output "sidebar-nav") ← Input url.pathname;
        стало _build_nav_links(pathname) на построении. Прежде
        _build_nav_links получал захардкоженный "/dashboard" (:106),
        и без колбэка подсветка была бы всегда на «Дашборде».
      * имя и аватар: было update_sidebar_profile (Output
        "sidebar-profile-name"/"-avatar") ← Input url.pathname
        + profile-updated; стало — аргумент profile.

    Почему не guard, а удаление: после FR-2 сайдбар рендерится
    колбэком render_sidebar_slot по тому же Input("url","pathname"),
    и оба прежних колбэка писали бы children в узлы, которые
    render_sidebar_slot в этот же момент создаёт или удаляет. Порядок
    применения Output'ов Dash не гарантирует — это гонка, а не шум
    в логах. Guard на pathname её не снимает, а лишь маскирует
    (и во втором случае давал бы «Пользователь» + 😊 после каждого
    перехода — регрессия Epic-09 фазы 2).
    Результат: у сайдбара НЕТ ни одного Output-колбэка и ни одного
    Input на его элементы; условно присутствующих узлов в колбэках
    проекта по сайдбару не осталось.

    exc_info=True в этом файле (:184) уходит вместе с колбэком;
    в render_sidebar_slot используется logger.opt(exception=True)
    (loguru молча игнорирует exc_info — попутный долг протокола 0027).

    Args:
        pathname: Текущий путь для подсветки; None → "/dashboard"
            (сохраняет прежнее поведение _build_nav_links).
        profile: Имя и avatar_id пользователя. Аватар-эмодзи получается
            get_avatar_emoji(profile["avatar_id"]) — как в удалённом
            колбэке (:181).
    """
```

### Владение `url.search` (сохраняется из v2, проверено критиком по диску)

```python
# app/main.py
_OWNED_SEARCH_PATHS = frozenset({"/calendar", "/goals"})
"""КОНТРАКТ ВЛАДЕНИЯ url.search (critique-v1, блокер №1).

url.search — Input не только у этого колбэка. Второй читатель —
apply_url_date_filter (transactions.py:1470-1520): читает ?start=&end=
для /transactions, в search НЕ пишет, работает с протокола 0023. Если
бы этот колбэк чистил search на /transactions, фильтр периода перестал
бы применяться (или применялся недетерминированно — гонка двух
Output'ов на один Input), то есть сломалась бы уже работающая дверь
Операций.

Правило: чистим search ТОЛЬКО для путей, чьи параметры разобрали сами.
Для /transactions — PreventUpdate. Идемпотентность там обеспечена самим
разделом: повторное применение того же периода не наблюдаемо.
"""

@callback(
    [Output("open-recon-trigger", "data"),
     Output("wishlist-active-item", "data"),
     Output("calendar-focus-date", "data"),   # NEW
     Output("goals-focus-goal", "data"),      # NEW
     Output("url", "search")],
    Input("url", "search"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def handle_panel_query_params(url_search: str | None, pathname: str | None):
    """Разбирает query params дверей щитка и раскладывает по Store'ам.

    Расширение механизма протоколов 0023/0028 (свидетельство поиска —
    memory/spec-context/epic-11.md), а не новый механизм:

      РАЗБИРАЕТ САМ и очищает search (_OWNED_SEARCH_PATHS):
        /calendar?open_recon=1      → open-recon-trigger    (было)
        /calendar?wishlist_item=ID  → wishlist-active-item  (было)
        /calendar?focus_date=ISO    → calendar-focus-date   (НОВОЕ, FR-3)
        /goals?goal=ID              → goals-focus-goal      (НОВОЕ, FR-3)

      НЕ ТРОГАЕТ (PreventUpdate, search принадлежит разделу):
        /transactions?start=&end=   → apply_url_date_filter (0023)
        /analytics                  → params не нужны: раздел уже
                                      открывается на текущем месяце

    ФОРМАТ ЗНАЧЕНИЯ новых Store'ов — dict, не скаляр (замечание №7):
        {"value": <date ISO | goal_id>, "ts": <int мс>}
    ts обязателен: два клика подряд по «завтра» должны сработать
    дважды, а Store сравнивается по значению. Он же — ключ
    идемпотентности приёмника (см. ниже).

    Битые значения (?focus_date=abc, ?goal=x) игнорируются молча —
    не повод падать; если ни один параметр не распознан, PreventUpdate,
    и search сохраняется.
    """
    if not url_search or pathname not in _OWNED_SEARCH_PATHS:
        raise PreventUpdate
    # ... разбор; если ничего не распознали — PreventUpdate (search цел)
    return recon_trigger, wishlist_item, focus_date, focus_goal, ""
```

### Идемпотентность Store-фокусов — ОДНА механика на оба (замечание №7)

Прочитано `load_and_navigate_calendar` (`calendar.py:758-947`): пять Input'ов (`url.pathname`, `prev/next/today-month-btn`, `wishlist-active-item`), `State("calendar-state")`; первой строкой guard `if pathname != "/calendar": raise PreventUpdate`; `triggered_id = ctx.triggered_id` уже используется для выбора ветки навигации (`:815-825`); возвращаемый `new_state` = `{"current_month", "current_year", "balances"}` (`:926-930`). То есть словарь состояния уже есть и уже возвращается — добавить в него ключ можно без новой инфраструктуры.

```python
# app/components/calendar.py :: load_and_navigate_calendar
#   +Input("calendar-focus-date", "data")  → 6-й Input
#
# ЕДИНАЯ МЕХАНИКА ИДЕМПОТЕНТНОСТИ (critique-v2, №7) — та же для
# goals-focus-goal:
#
#   1. Реагируем ТОЛЬКО если ctx.triggered_id == "calendar-focus-date".
#      Колбэк срабатывает и на url.pathname (возврат в раздел по меню),
#      и на кнопках навигации, и на wishlist-active-item. Store хранит
#      значение до перезагрузки страницы, layout между переходами не
#      пересоздаётся — без этой проверки «ушёл в Операции, вернулся
#      в Календарь по меню» молча прыгало бы на прошлый фокус.
#   2. И ТОЛЬКО если payload["ts"] != state.get("focus_applied_ts").
#      Защита от повторного применения того же события (F5, повторная
#      отправка колбэка). Применив фокус, кладём ts в calendar-state
#      рядом с current_month/current_year/balances — там уже есть
#      словарь состояния, новых Store'ов не нужно.
#   3. Применение = current_month/current_year из focus-даты
#      + класс .calendar-day-focused у ячейки этого дня
#      (build_day_cell, :574-660: css_classes собирается списком,
#      добавление ещё одного класса — одна строка).
#
# Тот же абзац буквально — для goals-focus-goal в apply_goal_focus;
# у него роль calendar-state играет собственный Store состояния фокуса.
```

### Сервис-композитор

```python
# app/services/panel_service.py
class DashboardPanelService:
    """Read-only композитор данных щитка (EPIC-11, кусок 2, FR-6).

    Собирает ВСЕ данные дашборда за один вызов и одну сессию:
    модель слоёв + четыре блока карточек. Ни один существующий сервис
    не меняется — только композиция (C-3). В БД не пишет, о Dash
    не знает (C-2).

    КОНТРАКТ МАТЕРИАЛИЗАЦИИ (обязателен к соблюдению):
        Каждый блок обязан вернуть ТОЛЬКО примитивы — Decimal / date /
        str / bool / int / их списки и словари. Обращение к
        ORM-атрибутам (включая вычисляемые property вроде
        Goal.progress_percentage и связи вроде WishlistItem.category_rel)
        выполняется ВНУТРИ открытой сессии, внутри тела блока.
        ORM-объект за пределы блока НЕ ВЫХОДИТ никогда.
        Почему правило, а не пожелание: GoalService.get_all_by_user
        возвращает list[Goal], WishlistService.get_focus —
        list[WishlistItem]; WishlistService.to_data внутри читает
        item.category_rel (wishlist_service.py:308-312), то есть
        безопасен только внутри сессии и при не-eager загрузке даёт
        по запросу на элемент. PanelData живёт ДОЛЬШЕ сессии
        (build_*_card вызываются после выхода из with), поэтому любая
        утечка ORM даёт DetachedInstanceError в проде, невидимый
        в тестах карточек (они кормятся словарями).
        Проверяется тестом, читающим ВСЕ поля PanelData после
        закрытия сессии.

    ЯВНЫЕ ПРЕОБРАЗОВАНИЯ ТИПОВ (critique-v2, №4): контракт карточки
        не равен контракту источника. Список — в докстринге
        _operations_block; проверяется тестом на isinstance.

    СТРАТЕГИЯ ЗАГРУЗКИ (FR-6, NFR-1) — по фактическим вызовам:

        Сессий за рендер дашборда: 1 (было 3, critique-v2 №8).
          Прежние три: dashboard.py:1002 (_load_dashboard_components:
          профиль + слои + recent + upcoming — все в ОДНОЙ сессии),
          dashboard.py:871 (_build_cushion_card_readonly),
          wishlist.py:33 (build_wishlist_widget — вызывается ИЗ LAYOUT,
          dashboard.py:687, а не из колбэка). Четвёртой не было.
          Побочный выигрыш от переноса wishlist в карточку: виджет
          сегодня НЕ обновляется по global-transaction-trigger — его
          контейнер не является Output'ом ни одного колбэка, он
          строится один раз в layout. Карточка Wishlist это исправляет:
          она приходит из PanelData, который перерисовывается CRUD-
          триггером вместе со всем щитком.

        Сессия сайдбара (Подход B, блокер №2) — учтена явно:
          на /dashboard — 0 (render_sidebar_slot возвращает [] до
          открытия сессии);
          на /calendar, /goals, /transactions, /analytics — 1 сессия
          и 1 SELECT User на переход (OnboardingService.get_profile =
          session.get(User, uid), onboarding_service.py:150-166),
          плюс та же сессия при каждой правке профиля (Input
          profile-updated). Против бюджета NFR-1 (2 с) при 13 мс
          куска 1 — не значимо; взамен у сайдбара ноль Output'ов
          на условно присутствующие элементы.

        Модель слоёв (get_money_layers, один вызов на рендер):
          1. CalendarService.calculate_daily_balances(ref-1 .. window_end)
          2. CalendarService.get_all_transactions_for_period(collect_start .. window_end)
          3. CushionService.get_threshold_amount   → 1 SELECT User (баланс НЕ считает)
          4. BudgetReservationService.get_settings → session.get(User) [identity map]
                                                     + _get_reserve_template
          5. GoalService.get_all_by_user(ACTIVE)   → 1 SELECT (вехи)
          6. _user_data_markers                    → session.get(User) [identity map]
                                                     + get_templates_for_user

        Блоки карточек, добавляемые куском 2:
          _calendar_block  — 0 запросов (чистая функция от MoneyLayersData)
          _goals_block     — session.get(User, uid) [identity map: User уже
                             загружен пп. 3/4/6] → cushion_target,
                             monthly_savings_budget, savings_mode ОДНИМ
                             чтением вместо трёх вызовов (critique-v2, №6)
                           + GoalService.get_all_by_user(ACTIVE) [ДУБЛЬ п.5]
                           + AllocationService.calculate_allocation (0 запросов)
                           + подушка БЕЗ запросов баланса
          _operations_block— 2 запроса с LIMIT
          _analytics_block — 1 GROUP BY по текущему месяцу
          _wishlist_block  — 1 запрос с LIMIT 5 + to_data на элемент
                             (category_rel; без eager-загрузки — до 5
                             коротких SELECT Category из одной сессии)

        Итого куском 2 добавляется: 4-9 коротких запросов, ноль
        дополнительных расчётов баланса, ноль вызовов Plotly.

    ДУБЛИ С МОДЕЛЬЮ СЛОЁВ — названы и решены осознанно:
        * GoalService.get_all_by_user(ACTIVE) вызывается и в
          _goal_milestones модели (money_layers_service.py:723), и в
          _goals_block. Дубль ОСТАВЛЕН: milestones содержат только
          goal_id/name/target_date/target_amount/progress_percent,
          отфильтрованы условием target_date >= ref (:735) и обрезаны
          до MAX_MILESTONES_IN_WINDOW + 1 (:750) — карточке нужны
          current_amount, полный список активных целей и порядок по
          priority, чего в milestones нет. Второй вызов идёт в ту же
          сессию (identity map). Читать milestones вместо целей =
          молча сузить карточку до целей с будущей датой.
        * CushionService.get_settings НЕ вызывается вовсе. Это самый
          дорогой вызов из блоков: помимо _get_user он делает
          _get_current_balance → CalendarService.get_balance_on_date,
          а тот обходит всю recurring-историю от самого раннего
          шаблона (задокументировано в get_threshold_amount,
          cushion_service.py:94-101). Второй расчёт баланса ради
          процента подушки — ровно тот дубль, от которого лечит FR-6.
          Вместо него _goals_block берёт:
            target    — User.cushion_target (то же чтение User);
            threshold — layers["cushion_threshold"] (посчитан моделью);
            current   — layers["today"]["balance"].
          Побочный выигрыш: цифра подушки приходит из того же
          источника, что шапка и график — расхождение невозможно
          по построению (FR-6).
        * GoalService.get_savings_budget / get_savings_mode НЕ
          вызываются (critique-v2, №6). Проверено по телам
          (goal_service.py:458-476 и :512-529): каждый —
          session.get(User, uid) + raise ValidationError если нет +
          return одного поля (monthly_savings_budget / savings_mode).
          Те же поля того же User, который блоку и так нужен для
          cushion_target, значит три чтения сводятся к одному,
          а «пользователя нет» перестаёт быть исключением.

    КЕША НЕТ намеренно: единственный источник инвалидации —
    global-transaction-trigger, а он уже перерисовывает щиток целиком.
    Кеш добавил бы риск показать устаревшие цифры (P1-боль «цифры
    противоречат друг другу») без выигрыша в бюджете NFR-1.
    """

    def __init__(self, session: Session) -> None: ...

    def get_panel_data(
        self, user_id: int, reference_date: date | None = None
    ) -> PanelData:
        """Собирает PanelData целиком.

        Raises:
            Любое исключение MoneyLayersService — базовая модель
            остатка НЕ деградирует (правило куска 1, NFR-2).
            Сбои остальных блоков ловятся поблочно и превращаются
            в CardStatus.FAILED с логом logger.opt(exception=True).
        """

    def _calendar_block(self, layers: MoneyLayersData) -> CalendarCardData: ...
    def _goals_block(self, user_id: int, layers: MoneyLayersData) -> GoalsCardData: ...
    def _operations_block(self, user_id: int, ref: date) -> OperationsCardData: ...
    def _analytics_block(self, user_id: int, ref: date) -> AnalyticsCardData: ...
    def _wishlist_block(self, user_id: int) -> WishlistCardData: ...
```

```python
    def _goals_block(self, user_id: int, layers: MoneyLayersData) -> GoalsCardData:
        """Топ-цель + сводка + подушка одной строкой (FR-1.b, AC-4).

        ОТСУТСТВИЕ ПОЛЬЗОВАТЕЛЯ — ЭТО EMPTY, НЕ FAILED (critique-v2, №6).
        Читаем User напрямую вместо GoalService.get_savings_budget /
        get_savings_mode: оба (goal_service.py:458-476, :512-529)
        делают session.get(User, uid) и бросают ValidationError, если
        пользователя нет. На чистой базе бутстрап создаёт User(id=1)
        (Epic-09 фаза 1), но фикстура «пустая база» его создавать
        не обязана — и тогда AC-5 получил бы goals=FAILED и был бы
        либо красным, либо подкручен под FAILED. «Нет пользователя» —
        это пустота, а не сбой: MoneyLayersService для того же случая
        специально не бросает (_user_data_markers: «на отсутствующем
        пользователе — (0, False): чистая база штатна»).

        Одно чтение User даёт все три нужных поля и убирает два вызова
        из стратегии загрузки.
        """
        user = self.session.get(User, user_id)
        if user is None:
            return _empty_goals()          # CardStatus.EMPTY, без цифр

        monthly_budget = user.monthly_savings_budget
        savings_mode = user.savings_mode
        cushion_target = user.cushion_target

        goals = GoalService(self.session).get_all_by_user(user_id, status=ACTIVE)
        if not goals and not cushion_target:
            return _empty_goals()

        allocation = AllocationService(self.session).calculate_allocation(
            goals, monthly_budget, savings_mode
        )
        # ORM Goal материализуется ЗДЕСЬ, внутри сессии.
        # others_behind_count — из allocation["results"] по shortfall > 0
        # каждой цели; сводное поле называется total_shortfall
        # (app/schema/goals.py:52), а не shortfall — v2 писала неверно.
        ...
```

```python
    def _operations_block(self, user_id: int, ref: date) -> OperationsCardData:
        """2-3 недавние + 2-3 предстоящие (FR-1.c).

        ЯВНЫЕ ПРЕОБРАЗОВАНИЯ (critique-v2, №4). Источник —
        DashboardService.get_recent_transactions / get_upcoming_transactions
        (limit=OPERATIONS_PER_GROUP), которые отдают RecentTransaction
        (dashboard_service.py:81-91). Проверено по телу _map_transactions
        (:456-472) — контракт источника НЕ совпадает с OperationRow:

          RecentTransaction["date"]: str  ← t.transaction_date.isoformat()
            → OperationRow["date"]: date = date.fromisoformat(row["date"])
            Обязательно: карточка отдаёт это поле в format_date_human
            (formatters.py:119-128 → date_obj.day), и на строке был бы
            AttributeError внутри try/except блока, то есть карточка
            деградировала бы в FAILED на НОРМАЛЬНЫХ данных. Тестами
            карточек это не ловится: они кормятся словарями с date.

          RecentTransaction["transaction_type"]: str  ← enum .value,
            шесть возможных значений (database.py:31-39)
            → OperationRow["kind"]: Literal["income","expense","other"]
            по таблице сведения (см. app/schema/panel.py).

          RecentTransaction["is_recurring_instance"]: bool
            → OperationRow["is_recurring"]  ← ПЕРЕИМЕНОВАНИЕ поля,
            в источнике поля is_recurring НЕТ.

          RecentTransaction["description"]: str | None
            → OperationRow["title"]: str  ← description or
            category_name or «Без описания» (в UI пустая строка
            выглядела бы дефектом вёрстки).

        ОГРАНИЧЕНИЕ (решение владельца 2026-08-25): только
        материализованные операции — см. докстринг OperationsCardData.

        Диапазоны href'ов — ТЕ ЖЕ, по которым источник отбирал строки
        (FR-6), проверено по телам: get_recent_transactions
        (:362-408) фильтрует [reference_date.replace(day=1),
        reference_date]; get_upcoming_transactions (:411-455) —
        [reference_date, последний день месяца].
        """
```

```python
    def _analytics_block(self, user_id: int, ref: date) -> AnalyticsCardData:
        """Только расходы месяца (FR-1.d).

        Один вызов AnalyticsService.get_expenses_by_category(user_id,
        month_start, month_end); month_total = Σ row["total"].
        Тот же сервис, что питает раздел «Аналитика» — цифра карточки
        и цифра раздела совпадают по построению, и это правильно
        (решение владельца по вопросу 5 критика v2).

        ОБЪЯВЛЕННОЕ РАСХОЖДЕНИЕ С ГРАФИКОМ ЩИТКА — см. докстринг
        AnalyticsCardData. AnalyticsService не правится (C-3).
        """
```

### Двери-переходы

Каркас и build-функции — как в v2 (`_door_shell`, `build_calendar_card`, `build_goals_card`, `build_operations_card`, `build_analytics_card`, `build_wishlist_card`, `build_cards_row`), с уточнениями докстрингов:

```python
def build_calendar_card(data: CalendarCardData) -> html.Div:
    """Карточка «Календарь»: вчера / сегодня / завтра + маркер просадки.

    Каждое окошко дня — dcc.Link на /calendar?focus_date=<ISO> (FR-3, AC-2).

    Маркер просадки (AC-7) рисуется ТОЛЬКО при status == OK
    (critique-v2, №10). Причина — в теле источника: _window_min_free
    (money_layers_service.py:669-697) при пустом days возвращает
    (Decimal("0"), date.today()), а НЕ (0, None). Без этой оговорки
    на чистой базе появилось бы «Ближайшая просадка: сегодня,
    остаток 0 ₽» — числовой артефакт, прямо запрещённый AC-5.
    При status EMPTY/FAILED поля dip_* игнорируются целиком, даже
    если непустые.

    При dip_free <= 0 маркер получает класс pnl-flagline-strong:
    усиление привязано к факту знака числа — порога-вердикта нет
    и константы-порога тоже нет (решение владельца 2026-08-25).

    День без данных (has_data=False) рисуется ПРОЧЕРКОМ, не нулём:
    «Вчера — 0 ₽» на наполненной базе — числовой артефакт,
    неотличимый от корректной работы (AC-3/AC-5).
    """

def build_analytics_card(data: AnalyticsCardData) -> html.Div:
    """Карточка «Аналитика»: цифра месяца + топ-категория + мини-структура.

    Подпись под цифрой — не просто «расходы августа», а
    «расходы августа · без регулярных и взносов в цели» (мелким
    кеглем, .pnl-note). Это ОБЪЯВЛЕНИЕ расхождения с месячным слоем
    «Платежи» графика над карточкой, а не извинение — оформлено
    симметрично ограничению карточки «Операции» (решение владельца
    2026-08-25). См. докстринг AnalyticsCardData.
    """

def build_cards_row(data: PanelData) -> html.Div:
    """Ряд карточек-дверей (FR-1, FR-2).

    Все пять карточек присутствуют ВСЕГДА — конституция щитка (FR-2):
    и при пустых данных (FR-5), и при сбое блока (NFR-2) карточка
    остаётся на месте, меняется только содержимое.

    ЕДИНСТВЕННЫЙ ИСТОЧНИК ПРАВДЫ отрисовки карточки — её собственный
    data[<slot>]["status"] (решение владельца 2026-08-25: «каждая
    карточка честна сама за себя»). Общего признака пустоты в
    PanelData НЕТ и не будет: layers["is_empty"] — узкий критерий
    модели слоёв, и пользователь с заведёнными целями при is_empty=True
    обязан видеть их прогресс, а не «щиток в режиме первого запуска».
    """
```

## Модель данных

```python
# app/schema/panel.py
"""Контракты данных карточек-дверей щитка (EPIC-11, кусок 2)."""

OPERATIONS_PER_GROUP = 3
"""Сколько операций в каждой группе карточки «Операции» (FR-1.c: «2-3»).

Три, не пять: карточка — фрагмент, а не таблица. Прежние split-таблицы
брали limit=5 — их место заняла эта карточка (AC-4).
"""

MINI_STRUCTURE_CATEGORIES = 3
"""Категорий в мини-структуре карточки «Аналитика» (эскиз v3: 3 + «из N ₽»)."""

# Константы DIP_STRONG_THRESHOLD НЕТ (critique-v1, №8): имя содержало
# «THRESHOLD», а решение владельца прямо говорит, что порога здесь нет.
# В коде — прямое `dip_free <= 0` с комментарием, что это факт знака
# числа, как красное «Свободно» в шапке куска 1.

TRANSACTION_KIND_MAP: dict[str, Literal["income", "expense", "other"]] = {
    "income": "income",                 # доход
    "expense": "expense",               # расход
    "savings_reserve": "expense",       # деньги уходят из остатка
    "savings_contribution": "expense",  # деньги уходят из остатка
    "transfer": "other",                # знак не определён семантикой типа
    "adjustment": "other",              # знак определяется суммой, не типом
}
"""Сведение шести значений TransactionType к трём kind (critique-v2, №4).

Источник — RecentTransaction["transaction_type"]: строка
t.transaction_type.value (dashboard_service.py:466), то есть одно из
шести значений TransactionType (database.py:31-39). В карточке kind
управляет ЦВЕТОМ суммы, поэтому правило нужно явное, а не «по знаку».

Логика: income/expense — прямо; savings_* — expense, потому что деньги
физически уходят из остатка (та же трактовка, что у слоя «Платежи»
модели: _PAYMENT_TYPES, money_layers_service.py:397-402); transfer и
adjustment — other (нейтральный цвет), потому что их направление
определяется не типом, а знаком суммы, а карточка-фрагмент не место
для разбора знака: в разделе «Операции» он виден полностью.

Неизвестное значение (если enum расширят) → "other" через .get(..., "other"):
карточка не падает, максимум теряет цвет. Покрыто тестом на все шесть
значений enum — тест покраснеет при добавлении седьмого.
"""


class CardStatus(str, Enum):
    """Состояние блока карточки — ЕДИНСТВЕННЫЙ источник правды её отрисовки.

    OK      — данные есть, показываем цифры.
    EMPTY   — в ЭТОМ разделе данных нет: пустое состояние БЕЗ числовых
              артефактов, карточка остаётся (FR-2, FR-5, AC-5).
              Определяется ТОЛЬКО по данным собственного блока —
              «каждая карточка честна сама за себя» (решение владельца
              2026-08-25). Сюда же относится «пользователя нет в БД»
              для карточки Цели: это пустота, а не сбой (critique-v2, №6).
    FAILED  — сбор блока упал; сбой залогирован logger.opt(exception=True),
              карточка деградирует с индикацией, дашборд жив (NFR-2).
    """

    OK = "ok"
    EMPTY = "empty"
    FAILED = "failed"


class CalendarDaySlice(TypedDict):
    """Одно окошко дня карточки «Календарь» (FR-1.a).

    Attributes:
        date: Дата дня.
        label: «Вчера» / «Сегодня» / «Завтра».
        is_today: True для сегодняшнего окошка (класс .pnl-day-today).
        balance: Прогнозный остаток дня — DayLayers['forecast_balance'].
            Тот же язык, что у раздела «Календарь», и то же число, что
            в модели шапки (AC-3). Для «вчера» — из MoneyLayersData
            ['yesterday'], для «сегодня»/«завтра» — из days[0]/[1].
        free: Слой «Свободно» дня — для подписи под остатком.
        has_data: False — день не посчитан (yesterday is None): окошко
            рисуется ПРОЧЕРКОМ, а не нулём (числовой артефакт).
        operations_note: «2 операции» / «план» / None — подпись эскиза.
        href: /calendar?focus_date=<ISO> — дверь дня (FR-3, AC-2).
    """
    date: date
    label: str
    is_today: bool
    balance: Decimal
    free: Decimal
    has_data: bool
    operations_note: str | None
    href: str


class CalendarCardData(TypedDict):
    """Карточка «Календарь» (FR-1.a). Считается ИЗ MoneyLayersData, без запросов.

    Attributes:
        status: OK / EMPTY / FAILED — только по собственным данным.
        days: Ровно три окошка: вчера, сегодня, завтра (в этом порядке).
        dip_date: День минимума слоя «Свободно» в окне модели —
            layers['min_free_date']; маркер показывается ВСЕГДА при
            status == OK (решение владельца «оба»).
        dip_free: Значение минимума (layers['min_free']).
        dip_is_strong: dip_free <= 0 — маркер визуально усилен (AC-7).
            Факт знака числа, не порог.
        dip_href: /calendar?focus_date=<dip_date ISO>.

    ВАЖНО (critique-v2, №10): при status != OK поля dip_* НЕ рисуются,
    даже если непустые. _window_min_free при пустом days возвращает
    (Decimal("0"), date.today()) — проверено по телу
    (money_layers_service.py:690-691), а не None. Без этой оговорки
    чистая база дала бы «Ближайшая просадка: сегодня, 0 ₽» — числовой
    артефакт, запрещённый AC-5.
    """
    status: CardStatus
    days: list[CalendarDaySlice]
    dip_date: date | None
    dip_free: Decimal | None
    dip_is_strong: bool
    dip_href: str | None


class GoalsCardData(TypedDict):
    """Карточка «Цели» (FR-1.b): топ-цель + сводка + подушка одной строкой.

    Все поля материализованы ВНУТРИ сессии из ORM Goal (контракт
    материализации DashboardPanelService): progress_percentage —
    вычисляемое property, обращение к нему после закрытия сессии даёт
    DetachedInstanceError.

    Подушка считается БЕЗ CushionService.get_settings — из
    layers['cushion_threshold'], layers['today']['balance'] и
    User.cushion_target (см. «Стратегия загрузки»): второй расчёт
    баланса ради процента был бы дублем, от которого лечит FR-6.

    Бюджет и режим накоплений читаются из того же User одним
    session.get, а не через GoalService.get_savings_budget /
    get_savings_mode: те бросают ValidationError при отсутствии
    пользователя, а «нет пользователя» здесь — EMPTY (critique-v2, №6).

    Attributes:
        status, top_goal_id, top_goal_name, top_goal_progress,
        top_goal_current, top_goal_target, top_goal_target_date,
        top_goal_href, others_count, others_behind_count,
        others_summary («по плану» / «1 отстаёт»; источник — цели
        с shortfall > 0 в AllocationSummary['results'], сводное поле
        сервиса называется total_shortfall, app/schema/goals.py:52),
        cushion_is_configured, cushion_progress, cushion_label.
    """
    status: CardStatus
    top_goal_id: int | None
    top_goal_name: str | None
    top_goal_progress: float
    top_goal_current: Decimal
    top_goal_target: Decimal
    top_goal_target_date: date | None
    top_goal_href: str | None
    others_count: int
    others_behind_count: int
    others_summary: str
    cushion_is_configured: bool
    cushion_progress: float
    cushion_label: str


class OperationRow(TypedDict):
    """Строка операции в карточке «Операции» (FR-1.c).

    КОНТРАКТ НЕ РАВЕН КОНТРАКТУ ИСТОЧНИКА (critique-v2, №4).
    Источник — RecentTransaction (dashboard_service.py:81-91),
    заполняемый _map_transactions (:456-472). Различия и
    преобразования — в докстринге _operations_block; здесь важно:
      * date — ЭТО date, а не ISO-строка источника: поле уходит в
        format_date_human (formatters.py:119-128 → date_obj.day),
        и строка дала бы AttributeError внутри try/except блока,
        то есть FAILED на нормальных данных;
      * kind — три значения, сведённые из шести по TRANSACTION_KIND_MAP;
      * is_recurring — переименование is_recurring_instance источника.
    Тип поля date проверяется тестом сервиса на isinstance: тесты
    карточек его не поймают, они кормятся словарями с уже верным типом.
    """
    date: date
    title: str
    amount: Decimal
    kind: Literal["income", "expense", "other"]
    is_recurring: bool


class OperationsCardData(TypedDict):
    """Карточка «Операции» (FR-1.c): 2-3 недавние + 2-3 предстоящие.

    ОГРАНИЧЕНИЕ (решение владельца 2026-08-25, принято осознанно):
    карточка показывает ТОЛЬКО материализованные операции — те, что
    физически лежат в таблице transactions. Виртуальные инстансы
    регулярных платежей (RecurringService), ещё не сохранённые в базу,
    в неё НЕ попадают: get_recent/get_upcoming исключают шаблоны
    условием ~(is_recurring == True & recurring_parent_id IS NULL)
    (dashboard_service.py:399-402) и не знают о виртуальных инстансах
    вовсе, а менять поведение сервиса запрещает C-3. Эскиз v3 рисовал
    «Аренда 🔁» — этого не будет.
    Где регулярные видны: в календаре, в графике полос щитка и в
    тултипе легенды слоя «Платежи» (кусок 1). Флаг is_recurring
    остаётся: материализованные recurring-инстансы маркер получают
    (источник — recurring_parent_id is not None).
    Ограничение зафиксировано здесь, в докстринге _operations_block
    и в документации (modules/ui-components.md).

    Attributes:
        status, recent, upcoming (до OPERATIONS_PER_GROUP строк),
        recent_href / upcoming_href — те же диапазоны, по которым
        источник отбирал строки (FR-6): recent — [1-е число, ref],
        upcoming — [ref, конец месяца].
    """
    status: CardStatus
    recent: list[OperationRow]
    upcoming: list[OperationRow]
    recent_href: str
    upcoming_href: str


class AnalyticsCategorySlice(TypedDict):
    """Доля категории в мини-структуре карточки «Аналитика».

    Источник — CategorySummary (app/schema/analytics.py:36-56):
    name ← category_name, total ← total, share ← percentage.
    """
    name: str
    total: Decimal
    share: float
    color: str


class AnalyticsCardData(TypedDict):
    """Карточка «Аналитика» (FR-1.d): ТОЛЬКО расходы.

    Показателя «Доходы за месяц» здесь нет и не появится ни в каком
    виде — решение владельца 2026-08-25.

    ОБЪЯВЛЕННОЕ РАСХОЖДЕНИЕ С ГРАФИКОМ ЩИТКА (critique-v2, №5;
    решение владельца по вопросу 5). month_total считается тем же
    AnalyticsService.get_expenses_by_category, что питает раздел
    «Аналитика», — с разделом цифра совпадает по построению, и это
    правильное поведение. Но с МЕСЯЧНЫМ СЛОЕМ «ПЛАТЕЖИ» графика,
    стоящего прямо над карточкой, она НЕ сопоставима, и это названо
    прямо, а не оставлено пользователю на догадки.

    Проверено по телу get_expenses_by_category (analytics_service.py:
    85-100): фильтр transaction_type == EXPENSE И is_recurring == False.
    Следствия:
      * виртуальные инстансы регулярных платежей в цифру НЕ входят,
        а в слой «Платежи» входят (модель считает их через
        CalendarService);
      * savings_reserve / savings_contribution и отрицательные
        adjustment в цифру НЕ входят, а в слой «Платежи» входят
        (_PAYMENT_TYPES + ветка adjustment, money_layers_service.py:
        397-402).
    Поэтому «расходы августа» будут заметно меньше месячного слоя
    платежей на графике. Обе цифры корректны в своей семантике;
    необъявленное расхождение и было болезнью (P1-боль аудита, FR-6),
    поэтому семантика объявляется в трёх местах: здесь, в подписи
    карточки («расходы августа · без регулярных и взносов в цели»)
    и в RTM (#87) — симметрично оформлению ограничения карточки
    «Операции». AnalyticsService НЕ правится (C-3); отдельный
    протокол по семантике «расходов месяца» в этом куске
    не заводится (решение владельца).
    """
    status: CardStatus
    month_label: str
    month_total: Decimal
    top_category_name: str | None
    top_category_total: Decimal
    top_category_share: float
    structure: list[AnalyticsCategorySlice]
    href: str


class WishlistCardRow(TypedDict):
    """Одна хотелка в карточке Wishlist — второй уровень двери (AC-8).

    Материализована из WishlistItemData ВНУТРИ сессии: to_data
    (wishlist_service.py:299-325) возвращает словарь примитивов, но
    внутри читает связь item.category_rel (:310-312) — то есть сам
    безопасен только внутри сессии.
    """
    item_id: int
    name: str
    amount_label: str
    is_planned: bool
    planned_date_label: str | None
    href: str


class WishlistCardData(TypedDict):
    """Карточка «Wishlist» (FR-1.e) — двухуровневая дверь."""
    status: CardStatus
    items: list[WishlistCardRow]
    total_count: int


class PanelData(TypedDict):
    """Полный набор данных щитка за один сбор (FR-6).

    Все значения — примитивы (Decimal/date/str/bool/int): PanelData
    безопасен ПОСЛЕ закрытия сессии (контракт материализации),
    проверяется целевым тестом.

    Поля is_new_user НЕТ (critique-v1, №7; решение владельца
    2026-08-25): общего признака пустоты, влияющего на отрисовку
    карточек, в контракте не существует — иначе получались бы два
    источника правды для AC-5 и достижимое расхождение «пустой щиток
    с непустыми карточками». Каждая карточка честна сама за себя:
    единственный источник — <slot>["status"].

    Attributes:
        layers: Модель слоёв — источник шапки, графика И карточки
            «Календарь». Один вызов на рендер: расхождение цифр между
            шапкой, графиком и карточкой физически невозможно (AC-3).
        calendar / goals / operations / analytics / wishlist: срезы карточек.
        reference_date: Дата отсчёта сборки.
    """
    layers: MoneyLayersData
    calendar: CalendarCardData
    goals: GoalsCardData
    operations: OperationsCardData
    analytics: AnalyticsCardData
    wishlist: WishlistCardData
    reference_date: date
```

```python
# app/schema/money_layers.py — новое поле
class MoneyLayersData(TypedDict):
    days: list[DayLayers]        # БЕЗ ИЗМЕНЕНИЙ: [ref .. ref+44], len == WINDOW_DAYS
    yesterday: DayLayers | None  # NEW и единственное новое поле
    # ... все остальные поля БЕЗ ИЗМЕНЕНИЙ
```

```
        yesterday: Слои за reference_date - LOOKBACK, посчитанные ТЕМ ЖЕ
            _split_day из ТЕХ ЖЕ словарей payments_tail/goals_part,
            что дни окна — нужны карточке «Календарь» (FR-1.a:
            вчера/сегодня/завтра).
            Хелперы вызываются ОДИН раз на служебном списке
            calc_dates = [ref-LOOKBACK] + window_dates: точечный вызов
            _payments_tail_by_day на одноэлементном списке вернул бы
            Decimal("0") по построению — функция накапливает суффиксную
            сумму проходом по переданному списку (critique-v2, блокер №1).
            None, если день не попал в расчёт балансов (не должно
            случаться при корректных границах — см. _horizons; None
            рисуется в карточке прочерком, а не нулём: числовой
            артефакт «Вчера — 0 ₽» на наполненной базе противоречил
            бы AC-3/AC-5).
            В days НЕ входит и на ось графика НЕ попадает.
```

## Обработка ошибок

| Уровень | Поведение | Идиома |
|---|---|---|
| `MoneyLayersService` (базовая модель остатка) | Исключение НЕ глотается — пробрасывается наружу, `load_dashboard_data` показывает единый alert. Без остатка щитка нет (правило куска 1). | существующее |
| Части модели слоёв (порог подушки, бюджет, вехи) | fail-open, `degraded=True`, оговорка в шапке — как в куске 1. | `logger.opt(exception=True).warning(...)` |
| `yesterday` не посчитан (нет дня в `balances`) | Не исключение: `yesterday = None`, `logger.warning` с указанием проверить левую границу. Карточка рисует прочерк, **не 0 ₽**. | `logger.warning` |
| **Пользователь отсутствует в БД (`_goals_block`)** | **`CardStatus.EMPTY`, а не `FAILED`** (critique-v2, №6): `session.get(User, uid)` → `None` → `_empty_goals()`. Это пустота, а не сбой — та же трактовка, что у `_user_data_markers`. Исключений `ValidationError` в этом пути больше нет, потому что `get_savings_budget`/`get_savings_mode` не вызываются. | без лога (штатный путь) |
| Блок карточки (`_goals_block`, `_operations_block`, `_analytics_block`, `_wishlist_block`) | `try/except Exception` вокруг каждого; `CardStatus.FAILED` + пустые поля. Карточка рисуется с текстом «Не удалось загрузить раздел», ссылка-дверь остаётся рабочей (находимость раздела не теряется — FR-2). Остальные четыре живы (NFR-2). | `logger.opt(exception=True).warning(f"Не удалось собрать блок «{name}» для user_id={uid} (карточка деградирует)")` |
| `_calendar_block` | Без try/except: чистая функция от уже валидной `MoneyLayersData`. Отсутствие дня — `has_data=False`, не ошибка. | — |
| **Чтение профиля в `render_sidebar_slot`** | **fail-open**: `except Exception` → профиль-заглушка (`"Пользователь"`, `DEFAULT_AVATAR_ID`) + лог; **сайдбар рисуется** с рабочей навигацией. Сбой чтения имени не имеет права лишать пользователя меню (FR-2 «находимость разделов»). `get_profile` бросает `ValueError` при отсутствии пользователя (`onboarding_service.py:162-164`) — это одна из ловимых ветвей. | `logger.opt(exception=True).warning` |
| ORM-детач (`DetachedInstanceError`) | Предотвращается контрактом, а не ловится: блок обязан вернуть примитивы. Проверяется тестом «читаем все поля `PanelData` после закрытия сессии». | — |
| Преобразование типов `OperationRow` | `date.fromisoformat` на строке источника; `TRANSACTION_KIND_MAP.get(value, "other")` — неизвестный тип не роняет блок. Битую дату источник дать не может (`isoformat()` от `date`), поэтому отдельной ветви нет; если бы дал — сработал бы общий `except` блока. | — |
| `load_dashboard_data` целиком | Существующий `except Exception` → alert; число Output'ов 5 → 3. | `logger.opt(exception=True).error` |
| Разбор query params | `try/except (ValueError, IndexError)` на каждом параметре; битый `?focus_date=abc` игнорируется молча; `PreventUpdate` если не распознан ни один параметр (тогда `search` не затирается). | существующее |
| `exc_info=True` | Запрещён: loguru его молча игнорирует. `sidebar.py:184` уходит вместе с удаляемым колбэком; в `profile_modal.py:143,159,163` заменяется на `logger.opt(exception=True)` — попутный долг протокола 0027. | — |

## План реализации

**Шаг 1. Модель слоёв: `calc_dates` + поле «вчера» (C-5) — фундамент AC-3.**
`app/schema/money_layers.py`: **одна** константа `LOOKBACK = timedelta(days=1)` (замечание №9) + поле `yesterday: DayLayers | None` с докстрингом. `money_layers_service.py`:
- `yday = ref - LOOKBACK`; `calc_dates = [yday] + window_dates`;
- `_forecast_balances(user_id, yday, horizons.window_end)`;
- `_horizons.collect_start = min(_month_start(ref), ref - LOOKBACK)`;
- `_payments_tail_by_day(payments, calc_dates, horizons.payments_end)` — **правильный порядок аргументов** (`payments` первым, подпись `:423-428`);
- `_goals_part_by_day(savings_by_date, calc_dates, monthly_budget)`;
- новый `_yesterday_slice(balances, payments_tail, goals_part, cushion_threshold, yday)`;
- строка `Note` в докстринге `_is_empty` про зависимость от `savings_by_date`.

**Тела `_payments_tail_by_day`, `_goals_part_by_day`, `_split_day`, `_today_slice`, `_window_min_free`, `_is_empty`, `_user_data_markers`, `_goal_milestones` не правятся** (C-3), меняются только точки вызова первых двух. Форма `days` не меняется.

Тесты (`test_money_layers_service.py`, только добавление):
1. **`yesterday["payments"]` НА ЗНАЧЕНИЕ** (главный тест блокера №1): на фикстуре с платежами внутри месяца `data["yesterday"]["payments"] == data["days"][0]["payments"] + Σ amount платежей с датой ровно `ref``. **Плюс mutation-проверка**: локально заменить `calc_dates` на `window_dates` в вызове `_payments_tail_by_day` — тест обязан покраснеть; если не краснеет, тест написан не туда;
2. **прямо в плане фиксируется**: тест инварианта `free + payments + reserve == forecast_balance` этот класс дефектов **НЕ ЛОВИТ ПРИНЦИПИАЛЬНО**. `_split_day` (`:598-643`) сохраняет сумму при **любом** входе, поэтому при `payments=0` инвариант сходится (`free` просто больше на ту же величину). Так же не ловят: тест «`yesterday["forecast_balance"] != 0`» (баланс считается верно), любой тест формы `days`, любой тест «не ноль/не отрицательное». Ловит **только** ассерт на само значение `payments`. Эту строку писать в план, чтобы следующая итерация не положилась на инвариант снова;
3. инвариант для `yesterday` — всё равно нужен (ловит другой класс: правку `_split_day`);
4. `len(data["days"]) == WINDOW_DAYS` и `data["days"][0]["date"] == ref` — регрессионный тест формы `days`;
5. **`payments_tail` дней окна не изменились от добавления `yday`**: значения `days[i]["payments"]` совпадают с эталоном, посчитанным до правки (фиксируется числами фикстуры). Ловит гипотетическую ошибку «список не отсортирован»;
6. `min_free_date` не совпадает с `yday` даже когда «вчера» — глобальный минимум;
7. `data["yesterday"]["forecast_balance"] != 0` на фикстуре с историей (целевой тест дефекта «Вчера — 0 ₽», левая граница `_forecast_balances`);
8. фикстура «сегодня = 1-е число месяца» через относительные даты: «вчера» видит операции прошлого месяца (`collect_start`);
9. **фикстура «1-е число + savings-операция в конце прошлого месяца» с ассертом на `is_empty`** (замечание №3): фиксирует принятое поведение `is_empty == False` в этом сценарии — если кто-то позже отфильтрует `savings_by_date`, тест покраснеет и решение будет пересмотрено осознанно;
10. `is_empty` на чистой базе остаётся `True`.

**Шаг 2. Контракты карточек.** `app/schema/panel.py` целиком (включая `TRANSACTION_KIND_MAP`) + реэкспорт в `app/schema/__init__.py`. Контракт первым, чтобы тесты шага 4 писались от него. `is_new_user` и `DIP_STRONG_THRESHOLD` не создаются.

**Шаг 3. `DashboardPanelService`.** `app/services/panel_service.py` + экспорт. Блоки:
- `_calendar_block(layers)` — чистая функция; «вчера» из `layers["yesterday"]` (или `has_data=False`), «сегодня»/«завтра» из `layers["days"][0]`/`[1]`; `dip_*` заполняются, но помечены «игнорируются при `status != OK`» (замечание №10);
- `_goals_block(user_id, layers)` — **`session.get(User, uid)` → `None` = `EMPTY`**; три поля (`cushion_target`, `monthly_savings_budget`, `savings_mode`) одним чтением; `GoalService.get_all_by_user(ACTIVE)` → `AllocationService.calculate_allocation(goals, monthly_budget, savings_mode)` (подпись `allocation_service.py:25-30`); `others_behind_count` из `allocation["results"]`; подушка из `layers["cushion_threshold"]` + `layers["today"]["balance"]` + `User.cushion_target`, **без `CushionService.get_settings`**;
- `_operations_block` — `get_recent_transactions(limit=OPERATIONS_PER_GROUP)` + `get_upcoming_transactions(...)`; **явные преобразования** `date.fromisoformat`, `TRANSACTION_KIND_MAP`, `is_recurring_instance → is_recurring`, `title` из `description or category_name or "Без описания"`; докстринг с ограничением по регулярным;
- `_analytics_block` — `get_expenses_by_category(user_id, month_start, month_end)`; `month_total` = Σ `total`; докстринг с объявленным расхождением;
- `_wishlist_block` — `get_focus(limit=5)` + `to_data` внутри сессии.
Докстринг класса содержит контракт материализации, список преобразований и стратегию загрузки с сессией сайдбара и «было 3 сессии».

**Шаг 4. Тесты сервиса.** `tests/test_panel_service.py`:
- AC-3: `panel["calendar"]["days"][1]["balance"] == panel["layers"]["today"]["balance"] == panel["layers"]["days"][0]["forecast_balance"]`;
- «вчера»: `panel["calendar"]["days"][0]["balance"] == panel["layers"]["yesterday"]["forecast_balance"]`, `has_data=True`, значение != 0 на истории;
- **типы `OperationRow`** (замечание №4): `isinstance(panel["operations"]["recent"][0]["date"], date)`; `kind` ∈ трёх значений для фикстуры со **всеми шестью** `transaction_type`; `is_recurring` True у материализованного recurring-инстанса;
- **AC-5 в ДВУХ вариантах фикстуры пустой базы** (замечание №6): (а) пустая база **с** `User(id=1)` → все пять блоков `EMPTY`; (б) пустая база **без** пользователя → все пять блоков `EMPTY` (а не `FAILED`), в логах нет трейсбека по `goals`. Второй вариант — целевой тест замечания №6;
- **материализация**: собрать `PanelData` внутри `with`, выйти из сессии, прочитать ВСЕ поля всех пяти срезов — ловит `DetachedInstanceError`;
- деградация: `patch` падающего сервиса → один блок `FAILED`, остальные `OK`, дашборд собран;
- смешанный случай: `layers["is_empty"] == True` + заведённая цель без взносов → `goals=OK` с цифрами, `operations=EMPTY`; и обратный;
- согласованность подушки: `cushion_progress` из `layers` совпадает с `CushionService.get_settings(...)["progress"]` на той же фикстуре;
- **счётчик запросов** (`sqlalchemy.event` на `before_cursor_execute`) + счётчик `get_money_layers == 1`.

**Шаг 5. Карточки-двери.** `app/components/panel_cards.py` + секции CSS в `panel.css` (`.pnl-slots` grid 4 + `.pnl-wish` полосой, `.pnl-door`, `.pnl-door-head`, `.pnl-days`, `.pnl-day`, `.pnl-day-today`, `.pnl-flagline`, `.pnl-flagline-strong`, `.pnl-bar`, `.pnl-bar-thin`, `.pnl-grp`, `.pnl-big-sum`, `.pnl-note`, `.pnl-mini-slot`, `.pnl-wish*`). Вертикальный ритм карточки «Цели» выравнивается (`margin-top:auto` у строки подушки). В карточке Аналитика — подпись объявленного расхождения.

**Шаг 6. Перестройка щитка.** `dashboard.py`: layout → шапка + график + `html.Div(id="dashboard-cards-row")`; удаляются `_build_transactions_split_table`, `_build_cushion_card_readonly` (сессия `:871`), `_build_empty_state`, импорты `build_wishlist_widget`/`CushionService`/`DashboardService`/`RecentTransaction`, вызов `build_wishlist_widget()` из layout (`:687`, сессия `wishlist.py:33`), четыре clientside-триггера пустых состояний; `_load_dashboard_components` → 3 значения через `DashboardPanelService`; оба колбэка → 3 Output'а; добавляется один clientside-триггер двери Wishlist. `custom.css`: снимаются `.db-left-col`, `.db-right-col`, `.db-main-row`, `.dashboard-split-table`. **`build_layers_chart` и `_axis_tickvals` не правятся.**

**Шаг 7. Удаление wishlist-виджета вместе с его Input'ом.** `wishlist.py`: `build_wishlist_widget` (`:25-80`) и `_build_widget_item` удаляются; `open_wishlist_modal` получает **единственный** `Input("open-wishlist-trigger", "data")` + guard; `Input("open-wishlist-modal-btn", "n_clicks")` (`:423`) удаляется вместе с элементом (`:65`). `components/__init__.py`: снятие экспорта. Правило «удаляешь элемент — удаляй его Input» → `patterns/callbacks.md`.

**Шаг 8. Сайдбар: Подход B (блокер №2) + снятие с дашборда + защита AC-9.**
- `main.py`: `sidebar-slot` + `render_sidebar_slot(pathname, profile_updated)` — **два Input'а** на всегда присутствующие `url` и `profile-updated`; чтение профиля внутри с fail-open; `[]` на дашборде до открытия сессии; статический `create_sidebar()` из layout (`:59`) снимается;
- `sidebar.py`: `create_sidebar(pathname, profile)` — чистая функция, литералы `"Пользователь"` (`:82`) и `😊` (`:65`) заменяются на `profile["name"]` и `get_avatar_emoji(profile["avatar_id"])`, `_build_nav_links("/dashboard")` (`:106`) → `_build_nav_links(pathname or "/dashboard")`; **колбэк `highlight_active_sidebar` (`:152-160`) УДАЛЯЕТСЯ; колбэк `update_sidebar_profile` (`:163-185`) УДАЛЯЕТСЯ**; импорты `callback/Input/Output`, `get_db_session`, `OnboardingService` из файла уходят (переезжают в `main.py`);
- `profile_modal.py`: `Input("sidebar-profile-container")` (`:96`) убирается — единственный вход открытия `open-profile-trigger`; guard на пустой Store сохраняется; `exc_info=True` → `logger.opt(exception=True)`;
- `sidebar.css`: **один** механизм — `.sidebar-column:empty { display: none }`;
- **новый `tests/test_sidebar.py`**: контракт входов `render_sidebar_slot` через `inspect.getsource` (как в `test_dashboard_callbacks.py`) — два Input'а, оба на `url`/`profile-updated`, ни одного на элемент сайдбара; `create_sidebar("/calendar", profile)` содержит имя и эмодзи из профиля и класс `sidebar-nav-item-active` у пункта «Календарь»; `render_sidebar_slot("/dashboard", None) == []`; **в модуле `sidebar` нет ни одного `@callback`** (регрессионный тест против возврата колбэка).

**Шаг 9. Приёмники контекста (FR-3) с владением `url.search` и единой идемпотентностью.** `main.py`: `handle_panel_query_params` + `_OWNED_SEARCH_PATHS` + три Store'а (`open-wishlist-trigger`, `calendar-focus-date`, `goals-focus-goal`); payload новых Store'ов — `{"value":…, "ts":…}`. `calendar.py`: `Input("calendar-focus-date")` шестым Input'ом в `load_and_navigate_calendar`; **двойной guard идемпотентности** (`ctx.triggered_id` == сам Store **И** `ts != state.get("focus_applied_ts")`); ключи `focus_date`/`focus_applied_ts` в `calendar-state` (словарь уже возвращается, `:926-930`); класс `calendar-day-focused` в `build_day_cell` (`css_classes` — список, `:596`); стиль в `calendar.css`. `goals.py`: якорные id в `_build_goal_card` (`:618`), узел `goals-focus-anchor`, колбэк `apply_goal_focus` с **той же** механикой. `transactions.py` и `analytics.py` — без правок.

**Шаг 10. Тесты UI карточек.** `tests/test_panel_cards_ui.py` в стиле `test_dashboard_panel_ui.py` (хелперы `iter_tree`/`joined_text`/`find_by_id`, фикстуры-словари, относительные даты, БД нет): все пять карточек при любом статусе (FR-2/AC-5); пустые состояния без `₽`/`%`/нулей; AC-7 в двух фикстурах (минимум > 0 → нет `pnl-flagline-strong`; ≤ 0 → есть); **`status=EMPTY` при непустых `dip_date`/`dip_free` → маркера в дереве НЕТ** (замечание №10, целевой тест); «вчера» с `has_data=False` рисует прочерк, а не «0 ₽»; href'ы всех дверей; отсутствие слова «Доход» в дереве карточки Аналитика; **наличие подписи объявленного расхождения** в карточке Аналитика (замечание №5); отсутствие карточки подушки в ряду и наличие строки подушки внутри карточки Цели (AC-4); смешанный случай пустоты на уровне UI.

**Шаг 11. Адаптация существующих тестов.** `test_dashboard_callbacks.py` — 5 Output'ов → 3, контракт декоратора; `test_profile_modal_callbacks.py` — вход через Store вместо `sidebar-profile-container`; тест на `handle_panel_query_params`: `pathname="/transactions"` → `PreventUpdate`, `/calendar` и `/goals` → Store'ы заполнены и `search == ""`. Проверить существующие тесты, ссылающиеся на удаляемые колбэки сайдбара (`grep highlight_active_sidebar|update_sidebar_profile tests/`) — если есть, они удаляются вместе с колбэками, а их роль берёт `test_sidebar.py`. `tests/test_dashboard_panel_ui.py` — правок не требует (проверяется прогоном).

**Шаг 12. Замер NFR-1 (время + запросы) и статика.** Замер как в куске 1 (`time.perf_counter` вокруг `_load_dashboard_components`) **плюс счётчик SQL-запросов**; **плюс отдельный замер `render_sidebar_slot("/calendar", None)`** — цена Подхода B в числах, в протокол. `black`, `flake8`, полный `pytest`.

**Шаг 13. Ручная проверка регрессий C-6, владения `url.search` и идемпотентности** (юнит-тестом не ловится): навигация дашборд → каждый раздел → обратно; **имя и аватар в сайдбаре корректны на всех четырёх разделах и после правки профиля** (блокер №2, целевая проверка); профиль открывается шестерёнкой на дашборде и аватаром в каждом разделе; подсветка активного пункта корректна во всех разделах; модал wishlist открывается дверью; клик «вчера»/«сегодня»/«завтра»/маркер просадки/цель/группа операций/аналитика/хотелка; «переход в Операции с периодом → фильтр применён; F5 → фильтр остался/переприменён без ошибки»; **«ушёл из раздела и вернулся по меню — фокус НЕ переприменяется»** (замечание №7): дашборд → клик «завтра» → календарь на завтра → пролистать на октябрь → уйти в Операции → вернуться в Календарь по меню → **октябрь остался, прыжка на август нет**; то же для фокуса цели.

Порядок жёсткий: 1 → 3 (сервис читает `yesterday`), 2 → 3 → 4, 5 → 6, 6 → 7 → 8 (снятие сайдбара безопасно только после перестройки layout и удаления виджета), 9 после 8 (Store'ы объявляются той же правкой `main.py`), 10–13 замыкают.

## Зависимости

- Новых пакетов нет; версии не меняются (Dash 2.17.1, SQLAlchemy 2.0.23).
- Внутренние: `panel_service` → `MoneyLayersService`, `GoalService`, `AllocationService`, `DashboardService`, `AnalyticsService`, `WishlistService` + прямое чтение `User` (`app.models.database`). `CushionService` из зависимостей композитора **исключён**; `GoalService.get_savings_budget`/`get_savings_mode` **не вызываются**. Все существуют, ни один не меняется (C-3).
- `main.py` получает новые импорты `get_db_session`, `OnboardingService`, `get_avatar_emoji`/`UserProfile` — те, что уходят из `sidebar.py`. Циклов не возникает: `main.py` уже импортирует `create_sidebar`.
- Схема БД не меняется, миграций нет (C-4).
- Тестовая инфраструктура: `sqlalchemy.event` для счётчика запросов (входит в SQLAlchemy).

## Риски и mitigation

| # | Риск | Вероятность | Mitigation |
|---|---|---|---|
| R1 | **Снятие сайдбара ломает модал профиля на дашборде** (`sidebar-profile-container` — прямой Input, элемента больше нет в DOM) → AC-9 красный. Класс C-6 «наоборот». | Высокая, если не заметить | Шаг 8: оба входа на `open-profile-trigger`. Ручная проверка — шаг 13. |
| R2 | **Модал wishlist недостижим**: Input на удалённый `open-wishlist-modal-btn` убивает колбэк на всех страницах. | Высокая, если оставить Input | Шаг 7: Input удаляется вместе с элементом; единственный вход — Store; правило в `patterns/callbacks.md`. |
| R3 | **«Вчера» = 0 ₽**: левая граница `_forecast_balances` не покрывает `yday`. Инварианты держатся (0=0+0+0). | Средняя | Таблица границ + целевой тест «`yesterday["forecast_balance"] != 0`» + `None` вместо нуля + `logger.warning`. |
| **R3b** | **«Вчера» `payments = 0` и завышенное «Свободно»** — оконный хелпер вызван точечно (блокер №1 v2). Профиль дефекта хуже R3: значение правдоподобно, инвариант суммы **держится**, UI не показывает ничего подозрительного. | **Была высокая в v2 (дефект был в решении); в v3 закрыта конструктивно** | Один вызов `_payments_tail_by_day` на `calc_dates` — верно **по построению**, а не по тесту. Плюс: тест **на значение** `yesterday["payments"] == days[0]["payments"] + Σ payments(date == ref)`; **mutation-проверка** (замена `calc_dates` → `window_dates` красит тест); тест «значения дней окна не изменились»; в плане записано, что тест инварианта этот класс НЕ ловит. |
| R4 | **«Вчера» 1-го числа не видит операций прошлого месяца.** | Средняя (1 день в месяц) | `collect_start = min(_month_start(ref), ref - LOOKBACK)`; тест на фикстуре «1-е число». |
| R5 | **Регрессия куска 1 при правке модели слоёв** (C-7). | Низкая | Форма `days` не меняется → график, `_axis_tickvals`, `min_free`, `_today_slice` не затронуты; 47 тестов зелёные без правок; регрессионный тест формы `days`. |
| **R5b** | **`is_empty`/`window_is_flat` переворачиваются 1-го числа** из-за `savings_by_date` от расширенного `collect_start` (замечание №3). | Низкая (узкий сценарий), направление безопасное | Зависимость **названа** в таблице границ и в докстринге `_is_empty`; принята осознанно; тест «1-е число + savings 31-го» фиксирует поведение с ассертом на `is_empty`. |
| R6 | **Гонка за `url.search`** ломает дверь Операций (0023). | Высокая, если чистить search для всех путей | `_OWNED_SEARCH_PATHS = {"/calendar","/goals"}`; на `/transactions` — `PreventUpdate`; контрактный тест + ручная проверка «период + F5». |
| R7 | **Деградация NFR-1.** Кусок 2 добавляет 4-9 коротких запросов, ноль расчётов баланса, ноль вызовов Plotly. Ожидание: 13 мс → ~25-40 мс против бюджета 2 с. Плюс 1 SELECT User на построение сайдбара при переходе между разделами. | Низкая | Замер шага 12 со счётчиком запросов + отдельный замер `render_sidebar_slot`; тест-счётчик `get_money_layers == 1`; отказ от `get_settings` и от двух вызовов `GoalService` убирает больше, чем добавляет сайдбар. |
| R8 | **Кеш кажется нужным** → устаревшие цифры против свежей шапки. | Средняя | Решение в докстринге: кеша нет, инвалидация только через `global-transaction-trigger`. |
| R9 | **Дубль `GoalService.get_all_by_user`** между моделью слоёв и `_goals_block`. | Осознанно оставлен | Назван в стратегии загрузки с обоснованием по телу `_goal_milestones` (нет `current_amount`, фильтр `target_date >= ref`, обрезка до 4). Identity map. Счётчик запросов делает цену видимой. |
| R10 | **Фокус переприменяется**: Store — состояние, а не событие. Два подслучая: F5 на URL с параметром и **возврат в раздел по меню** (колбэк срабатывает по `url.pathname`, Store всё ещё полон). | **Средняя; второй подслучай в v2 не был закрыт** | Единая механика (шаг 9): `ctx.triggered_id` == сам Store **И** `ts != state["focus_applied_ts"]`; `url.search` чистится для владеемых путей; ручной пункт «ушёл и вернулся» (шаг 13). |
| R11 | **`DetachedInstanceError` в проде**, невидимый в тестах карточек. | Средняя | Контракт материализации + тест на все поля после закрытия сессии. `to_data` вызывается внутри сессии. |
| R12 | **Удаление колбэков сайдбара теряет подсветку активного пункта.** | Низкая | Подсветка в `create_sidebar(pathname, profile)` тем же `_build_nav_links(pathname)`; `test_sidebar.py` проверяет класс `sidebar-nav-item-active`; ручная проверка во всех разделах. |
| **R12b** | **Удаление `update_sidebar_profile` теряет имя и аватар** — сайдбар возвращается к литералам «Пользователь» + 😊 (регрессия Epic-09 фазы 2). Именно этот дефект внесла v2. | **Была высокая в v2; в v3 закрыта конструктивно** | Профиль читается в `render_sidebar_slot` и передаётся аргументом; `create_sidebar` литералов профиля больше не содержит; `test_sidebar.py` ассертит имя и эмодзи в дереве; **ручной пункт шага 13** «имя и аватар на всех четырёх разделах и после правки профиля». |
| **R12c** | **Сбой чтения профиля обрушивает сайдбар целиком** — новый риск Подхода B: сессия теперь на пути построения навигации. | Низкая | fail-open в `render_sidebar_slot`: `except` → профиль-заглушка + `logger.opt(exception=True)`, **сайдбар рисуется** с рабочей навигацией. Тест: `patch` падающего `get_profile` → в дереве есть все пять пунктов меню. |
| R13 | **Фокус цели требует переписать раздел** → нарушение C-1. | Низкая | Якорный id в `_build_goal_card` + один узел + один колбэк; логика allocation/приоритетов не трогается. |
| R14 | **Ряд из 5 карточек не влезает в grid эскиза (4 колонки)**. | Средняя | Раскладка эскиза v3: 4 двери в `.pnl-slots`, Wishlist — `.pnl-wish` полосой. |
| R15 | **Расхождение семантики подушки** после отказа от `get_settings`. | Низкая | Оба значения идут в `CalendarService`; тест сравнивает `cushion_progress` с `get_settings(...)["progress"]`. Расхождение, если найдётся, — дефект `CalendarService`, и должно быть поймано, а не замаскировано вторым источником. |
| **R16** | **Цифра «Аналитика» противоречит графику на глаз** — та самая P1-боль, но с корректными числами по обе стороны. | Средняя (наблюдаема на любой базе с регулярными) | **Объявление, а не правка** (решение владельца): докстринг `AnalyticsCardData` со списком двух причин расхождения, подпись в карточке, строка RTM #87, тест на наличие подписи. `AnalyticsService` не правится (C-3); отдельный протокол в этом куске не заводится. |
| **R17** | **`FAILED` вместо `EMPTY` на базе без пользователя** → AC-5 ложнозелёный или подкручен под `FAILED`. | **Была средняя в v2** | `session.get(User)` → `None` → `EMPTY`; `get_savings_budget`/`get_savings_mode` не вызываются вовсе, поэтому `ValidationError` в этом пути неоткуда взяться; **тест AC-5 в двух вариантах фикстуры** (с пользователем и без). |
| **R18** | **`OperationRow["date"]` — ISO-строка вместо `date`** → `format_date_human` → `AttributeError` → карточка `FAILED` на нормальных данных, **невидимо для тестов карточек** (они кормятся словарями с `date`). | **Была средняя в v2** | Явное `date.fromisoformat` в `_operations_block`; таблица `TRANSACTION_KIND_MAP`; тест сервиса на `isinstance(..., date)` и на все шесть значений enum. |
| **R19** | **Третий случай «оконный хелпер вызван точечно»** в куске 3 или при карточках на других страницах. | Средняя (файл будет открыт снова) | Урок в `knowledge-bank/patterns/`: **хелперы `MoneyLayersService`, принимающие `window_dates`, определены только для непрерывного окна и точечно не переиспользуются**; в докстринги `_payments_tail_by_day` и `_goals_part_by_day` — по строке о том, зависит ли результат от состава списка (для первого — да, для второго — нет). Ловить третий такой случай на ревью реализации дороже, чем записать правило. |

## Requirements Traceability Matrix (RTM)

Строки #1-#86 сохраняются из v2 с правками, отмеченными **(v3)**; #87-#92 — новые.

| # | Requirement (дословно) | Секция spec | Реализация в solution | Тип |
|---|---|---|---|---|
| 1 | «под шапкой и графиком видны карточки пяти предметных разделов» | AC-1, FR-1 | `build_cards_row(PanelData)` → 4 двери в `.pnl-slots` + `.pnl-wish`; `dashboard-cards-row` в layout | Visual |
| 2 | *Календарь*: «вчера / сегодня / завтра (остатки дней)» | FR-1 | **(v3)** `CalendarCardData.days` — 3 `CalendarDaySlice`; «вчера» из `layers["yesterday"]`, посчитанного из `calc_dates`; «сегодня»/«завтра» из `layers["days"][0]/[1]` | Visual |
| 3 | «маркер просадки — день минимума слоя «Свободно» окна модели» | FR-1 | `dip_date`/`dip_free` из `layers["min_free_date"]`/`["min_free"]`; `.pnl-flagline` при `status == OK` | Visual |
| 4 | «при минимуме ≤ 0 маркер визуально усиливается (факт знака, не порог-вердикт)» | FR-1, AC-7 | `dip_is_strong = dip_free <= 0` прямым сравнением, константы-«порога» нет | Edge |
| 5 | Календарь-дверь: «календарь на кликнутом дне» | FR-1, FR-3, AC-2 | `href=/calendar?focus_date=<ISO>` → `calendar-focus-date` → `load_and_navigate_calendar` + класс `calendar-day-focused`; идемпотентность — #90 | Integration |
| 6 | *Цели*: «топ-цель с прогрессом» | FR-1, AC-4 | `top_goal_*`; `.pnl-bar`; материализовано внутри сессии | Visual |
| 7 | «сводка остальных (вида «по плану / 1 отстаёт»)» | FR-1, AC-4 | **(v3)** `others_count`, `others_behind_count`, `others_summary`; источник — цели с `shortfall > 0` в `AllocationSummary["results"]` (сводное поле сервиса — `total_shortfall`, `app/schema/goals.py:52`) | Visual |
| 8 | «статус подушки одной строкой + подушка живёт внутри этой карточки» | FR-1, AC-4 | **(v3)** `cushion_*` из `layers["cushion_threshold"]` + `layers["today"]["balance"]` + `User.cushion_target` (то же чтение `User`, что бюджет и режим), **без `get_settings`**; `_build_cushion_card_readonly` удалён | Visual |
| 9 | Цели-дверь: «цели с фокусом на кликнутой» | FR-1, FR-3, AC-2 | `top_goal_href=/goals?goal=<id>` → `goals-focus-goal` → `apply_goal_focus` + якорные id; идемпотентность — #90 | Integration |
| 10 | *Операции*: «2-3 недавние + 2-3 предстоящие» | FR-1 | `OPERATIONS_PER_GROUP = 3`; `get_recent/upcoming_transactions(limit=3)` | Visual |
| 11 | Операции-дверь: «список операций с фильтром периода» | FR-1, FR-3, AC-2 | **(v3)** `recent_href`/`upcoming_href` — те же диапазоны, что в телах источника (`[1-е, ref]` и `[ref, конец месяца]`); приёмник `apply_url_date_filter` не ломается — см. #79 | Integration |
| 12 | *Аналитика*: «цифра месяца — топ-категория расходов + мини-структура» | FR-1 | `month_total`, `top_category_*`, `structure`; `.pnl-big-sum`, `.pnl-mini-slot`; семантика цифры — #87 | Visual |
| 13 | «Показатель «Доходы за месяц» НЕ возвращается» | FR-1, out of scope | `AnalyticsCardData` без поля доходов; только `get_expenses_by_category`; тест «слова «Доход» нет в дереве» | UX |
| 14 | Аналитика-дверь: «аналитика текущего месяца» | FR-1, AC-2 | `href="/analytics"`; дефолт `analytics-period-store`; раздел не правится (C-1) | Integration |
| 15 | *Wishlist*: «компактный виджет (представительство сохраняется)» | FR-1 | `.pnl-wish` полосой; в `MAIN_NAV_ITEMS` пункта нет | Visual |
| 16 | «Дверь двухуровневая: заголовок/тело → модал управления wishlist» | FR-1, AC-8 | `panel-wishlist-door` → clientside `timestamp_trigger` → `open-wishlist-trigger` → `open_wishlist_modal` с единственным Input'ом | Integration |
| 17 | «клик по конкретной хотелке → календарь в режиме покупок с фокусом» | FR-1, AC-8 | `WishlistCardRow.href=/calendar?wishlist_item=<id>` → `wishlist-active-item` | Integration |
| 18 | *Настройки*: «служебная иконка, не карточка» | FR-1 | `_build_settings_cog` куска 1 не меняется | Visual |
| 19 | **FR-2** «Каждый предметный пункт меню имеет карточку» | FR-2 | Пять карточек ↔ `MAIN_NAV_ITEMS` + Wishlist | UX |
| 20 | «на дашборде меню нет — сайдбар убирается» | FR-2, AC-1 | **(v3)** `render_sidebar_slot` → `[]` **до открытия сессии**; скрытие колонки одним CSS `:empty` | Visual |
| 21 | «На остальных страницах сайдбар остаётся» | FR-2, AC-1 | **(v3)** `create_sidebar(pathname, profile)` для четырёх разделов; `test_sidebar.py` по pathname | Integration |
| 22 | **FR-3** «Клик открывает раздел в состоянии, соответствующем клику» | FR-3 | Двери — `dcc.Link` с контекстом в query params; `handle_panel_query_params` раскладывает по Store'ам | Integration |
| 23 | «завтра» → календарь с завтрашним днём | FR-3, AC-2 | `days[2].href=/calendar?focus_date=<ref+1>` | Integration |
| 24 | «Дух важнее буквы»: позиционная привязка — не требование | FR-3 | Раскладка эскиза v3; зафиксировано в докстринге `build_cards_row` | UX |
| 25 | **FR-4** «Онбординг-тост сохраняет поведение» | FR-4, AC-6 | `_build_balance_banner` + `toggle_balance_toast` + `persist_toast_dismissal` не трогаются; баннер — первый узел layout | Integration |
| 26 | «Прочие сироты закрыты ранее» | FR-4 | Сверка — кнопки шапки куска 1; «Доходы» — см. #13 | UX |
| 27 | **FR-5** «каждая карточка показывает спроектированное пустое состояние» | FR-5, AC-5 | `CardStatus.EMPTY` по собственным данным блока; текст-смысл раздела в `build_*_card` | Visual |
| 28 | «без числовых артефактов» | FR-5, AC-5 | **(v3)** Ветка `EMPTY` не рендерит ни `format_rub`, ни проценты, **ни `dip_*`** (#91); тест «нет «₽» и «%»»; `has_data=False` → прочерк | Edge |
| 29 | «карточки не исчезают (конституция FR-2)» | FR-5, AC-5 | `build_cards_row` строит пять карточек безусловно; тест на смешанных статусах | Visual |
| 30 | **FR-6** «карточка «Календарь» — той же моделью слоёв куска 1» | FR-6, AC-3 | `_calendar_block(layers)` — чистая функция, ноль запросов | Integration |
| 31 | «цифры карточек не противоречат шапке/графику» | FR-6, AC-3 | **(v3)** один `get_money_layers` за сборку (тест-счётчик); подушка тоже из `layers`; **«вчера» и «сегодня» считаются одним каскадом из одних словарей** (#89); объявленное исключение — #87 | Perf/Integration |
| 32 | «стратегия загрузки проектируется явно» | FR-6 | **(v3)** докстринг `DashboardPanelService`: 1 сессия (**было 3**, не 4), сессия сайдбара учтена явно, 1 модель слоёв, 4-9 коротких запросов, дубли названы, `get_settings` и два вызова `GoalService` исключены, кеша нет намеренно | Perf |
| 33 | **NFR-1** «< 2 секунд» | NFR-1, AC-10 | Замер шага 12 — время и число запросов (щиток **и** сайдбар); оценка ~25-40 мс | Perf |
| 34 | «в куске 1 рендер был 13 мс, деградация должна быть объяснима» | задача | R7: покомпонентная оценка; сессий 3 → 1 на дашборде, +1 на переход между разделами; минус `get_settings` | Perf |
| 35 | **NFR-2** «сбой одной карточки не обрушивает дашборд» | NFR-2 | `try/except` на блок → `FAILED` → «Не удалось загрузить раздел» при живой двери | Edge |
| 36 | «сбой логируется с трейсбеком (`logger.opt(exception=True)`)» | NFR-2 | Идиома во всех новых except; `sidebar.py:184` уходит с колбэком, `profile_modal.py:143,159,163` заменяются | Edge |
| 37 | «Сбой расчёта базовой модели не глотается» | NFR-2 | `get_money_layers` вызывается ВНЕ try/except | Edge |
| 38 | **C-1** «только минимальные приёмники контекста» | C-1 | `calendar.py`: +1 Input, +2 ключа Store, +1 CSS-класс; `goals.py`: +якорные id, +1 узел, +1 колбэк; `transactions.py`, `analytics.py` — 0 правок | Integration |
| 39 | **C-2** «Decimal, session-контракт, сервисы не знают о Dash» | C-2 | `PanelData` — только примитивы; сервис read-only, без `flush`/`commit`; импортов Dash нет | Integration |
| 40 | **C-3** «поведение сервисов не меняется; 693 теста зелёные» | C-3, AC-10 | **(v3)** Кроме `MoneyLayersService` (разрешён C-5) ни один сервис не правится. **Тела `_payments_tail_by_day` и `_goals_part_by_day` НЕ меняются — меняются только точки вызова** (`calc_dates` вместо `window_dates`); режим вызова соответствует контракту функций: непрерывный возрастающий список дат | Integration |
| 41 | **C-4** «Схема БД не меняется» | C-4 | Миграций нет; `app/models/database.py` только читается | Integration |
| 42 | **C-5** «контракт МОЖНО менять, но шапка и график работают, инвариант сохраняется» | C-5 | **(v3)** одно добавленное поле `yesterday`; форма `days` неизменна; инвариант `_split_day` держится по построению, тест инварианта для `yesterday` — **плюс тест на значение `payments`, потому что инвариант этот класс не ловит** (#89) | Integration |
| 43 | **C-6** «новые элементы дашборда не ломают колбэки на других страницах» | C-6, AC-9 | Двери — `dcc.Link`; дверь Wishlist — clientside → Store; вход профиля на Store; обратная сторона (#80); **и Output-сторона закрыта полностью** (#88) | Integration |
| 44 | **C-7** «шапка и график не регрессируют; 47 тестов зелёные» | C-7, AC-10 | `days` не меняется → `test_dashboard_panel_ui.py` правок не требует; проверяется прогоном (шаг 12) | Visual |
| 45 | «нет вердикта-светофора, нет приветствия, шапка не дверь» | C-7 | `build_free_header` не правится; `TestFreeHeader` остаётся | Visual |
| 46 | **AC-1** «сайдбара/меню на дашборде нет» | AC-1 | см. #20 | Visual |
| 47 | **AC-2** полный набор четырёх переходов | AC-2 | см. #5, #9, #11, #14 | Integration |
| 48 | **AC-3** «остаток «сегодня» равен значению модели слоёв — unit-тест» | AC-3 | Тест шага 4: `calendar.days[1].balance == layers.today.balance == layers.days[0].forecast_balance` | Integration |
| 49 | **AC-4** «readonly-карточка подушки снята» | AC-4 | `_build_cushion_card_readonly` (сессия `dashboard.py:871`), `dashboard-cushion-card`, `.db-right-col` удалены | Visual |
| 50 | «split-таблицы заменены карточкой Операции» | AC-4 | `_build_transactions_split_table` и связанные id/CSS удалены | Visual |
| 51 | **AC-5** «чистая база → все пять карточек с пустыми состояниями» | AC-5 | **(v3)** см. #27-#29; тест `PanelData` на пустой базе **в двух вариантах фикстуры** — с пользователем и без (#92) | Edge |
| 52 | **AC-6** «онбординг-тост ведёт себя как до перестройки» | AC-6 | см. #25; `TestToggleBalanceToastProfileUpdated` зелёный без правок | Integration |
| 53 | **AC-7** «минимум > 0 → без усиления; ≤ 0 → усилен — unit-тесты» | AC-7 | Две фикстуры в `test_panel_cards_ui.py`; ассерт на `pnl-flagline-strong`; плюс #91 | Edge |
| 54 | **AC-8** оба уровня двери Wishlist | AC-8 | см. #16, #17 | Integration |
| 55 | **AC-9** «модал профиля со всех страниц обоими входами» | AC-9 | Шаг 8: единственный Input открытия — `open-profile-trigger` | Integration |
| 56 | **AC-10** «unit-тесты, полный pytest, black+flake8, рендер в NFR-1» | AC-10 | Шаги 4, 8, 10, 11, 12 | Perf |
| 57 | design.md: «иерархия определяет размер и позицию, но не факт присутствия» | design.md | Wishlist — полоса; все пять присутствуют | UX |
| 58 | design.md: «служебные экраны — иконки, не карточки» | design.md | см. #18 | UX |
| 59 | Эскиз v3: `.door` + `.door-head` + `.door-body` | эскиз | `_door_shell` → `.pnl-door*`; цветная шина гнезда 3px через `--pnl-slot` | Visual |
| 60 | Эскиз v3: цвета гнёзд четырёх дверей | эскиз | CSS-переменные на `.pnl-door-<slot>`; зелёный/синий из `--pnl-free`/`--pnl-reserve` | Visual |
| 61 | Эскиз v3: три окошка `.day`, у сегодняшнего фон и класс `.today` | эскиз | `.pnl-day`, `.pnl-day-today`; `CalendarDaySlice.is_today` | Visual |
| 62 | Эскиз v3: подпись окошка «2 операции» / «план» | эскиз | `operations_note` из `layers["upcoming_payments"]` (без запроса) для «сегодня»/«завтра»; у «вчера» подпись пустая — как в эскизе (`d-note` там `&nbsp;`), потому что `payments` фильтруется `day >= reference_date` (`:404`) и вчерашних операций в модели нет | Visual |
| 63 | Эскиз v3: `.flagline` «Ближайшая просадка: 4 сент, остаток 9 800 ₽» | эскиз | `.pnl-flagline` + `format_date_human(dip_date)` + `format_rub(dip_free)`; усиление — `.pnl-flagline-strong`; при `status != OK` не рисуется (#91) | Visual |
| 64 | Эскиз v3: «102 000 из 150 000 ₽ · к 15 окт» | эскиз | `top_goal_current/target/target_date` + форматтеры | Visual |
| 65 | Эскиз v3: «Ещё 2 цели — по плану»; подушка мелким кеглем `.bar.thin` | эскиз | `others_summary`, `.pnl-pillow`, `.pnl-bar-thin` | Visual |
| 66 | Эскиз v3: заметка vision-критика «выровнять вертикальный ритм карточки Цели» | осадок | `margin-top:auto` у блока подушки (шаг 5) | Visual |
| 67 | Эскиз v3: группы «НЕДАВНИЕ»/«ПРЕДСТОЯЩИЕ», маркер 🔁 | эскиз | `.pnl-grp`; `OperationRow.is_recurring` ← `is_recurring_instance` источника, **только для материализованных**, см. #82 | Visual |
| 68 | Эскиз v3: «78 400 ₽» `.big-sum` + «расходы августа» | эскиз | **(v3)** `month_total` + `month_label` (родительный падеж) + **подпись расхождения** (#87) | Visual |
| 69 | Эскиз v3: «Продукты — 24 300 ₽ · 31%» + «крупнейшая категория месяца» | эскиз | `top_category_*` из `CategorySummary["category_name"]`/`total`/`percentage`; `.pnl-top-cat` | Visual |
| 70 | Эскиз v3: мини-структура 3 категории + «Прочее» + «из 78 400 ₽» | эскиз | `structure` (`MINI_STRUCTURE_CATEGORIES`); CSS-полоска, без Plotly | Visual |
| 71 | Эскиз v3: `.wish` — полоса с левым зелёным бордером, тег «WISHLIST» | эскиз | `.pnl-wish*` | Visual |
| 72 | Эскиз v3: `:focus-visible` outline, `tabindex` на дверях | эскиз | `dcc.Link` фокусируем нативно; `.pnl-door:focus-within` outline | UX |
| 73 | Эскиз v3: адаптив 1180px → 2 колонки, 680px → 1 | эскиз | Те же брейкпоинты в `panel.css` (полная адаптация — Epic-08) | Visual |
| 74 | Эскиз v3: `prefers-reduced-motion` | эскиз | Секция «ДОСТУПНОСТЬ» `panel.css` расширяется на `.pnl-door` | UX |
| 75 | Out of scope: «выбор произвольного месяца в аналитике» | out of scope | `href="/analytics"` без params; `analytics.py` не правится | UX |
| 76 | Out of scope: «/settings — заглушка остаётся» | out of scope | `/settings` не добавляется; шестерёнка ведёт в модал профиля | UX |
| 77 | Out of scope: «полоска-меню вместо сайдбара» | out of scope | **(v3)** `create_sidebar` не переписывается — только становится чистой функцией от `(pathname, profile)` и условно рендерится | UX |
| 78 | Out of scope: «анимация переходов дашборд↔раздел» | out of scope | Переходы — обычные `dcc.Link` | UX |
| 79 | **Владение `url.search`**: очистка не должна ломать `apply_url_date_filter` (0023) | AC-2, C-1, C-3 | `_OWNED_SEARCH_PATHS = {"/calendar","/goals"}`; на `/transactions` — `PreventUpdate`; контракт в докстринге; контрактный тест (шаг 11) + ручная проверка (шаг 13) | Integration |
| 80 | **Обратная сторона C-6**: «удаляешь элемент — удаляй его Input» | C-6, AC-8 | `Input("open-wishlist-modal-btn")` (`wishlist.py:423`) удаляется вместе с элементом (`:65`); правило в докстринге и в `patterns/callbacks.md` | Integration |
| 81 | **Один источник правды пустоты**: отрисовкой карточки управляет только её `CardStatus` | FR-5, AC-5 | `is_new_user` из `PanelData` убрано; правило в докстрингах `CardStatus` и `build_cards_row`; тесты смешанного случая в сервисе и в UI | Edge |
| 82 | **Ограничение по регулярным операциям**: карточка «Операции» показывает только материализованные | FR-1.c, C-3 | Ограничение в докстрингах `OperationsCardData` и `_operations_block` (с указанием фильтра-источника `dashboard_service.py:399-402`); в документации; решение владельца 2026-08-25 | Edge |
| 83 | **(v3, переписана) Output на условно присутствующие элементы сайдбара** — `sidebar-nav` **и** `sidebar-profile-name`/`-avatar` исчезают с `/dashboard` | C-6, AC-1, AC-9 | **Оба** колбэка сайдбара (`highlight_active_sidebar`, `update_sidebar_profile`) удаляются; подсветка и профиль вычисляются при построении; у сайдбара не остаётся ни одного Output-колбэка. См. #88 | Integration |
| 84 | **Контракт материализации ORM**: `PanelData` безопасен после закрытия сессии | C-2, NFR-2 | Требование в докстринге сервиса; тест на все поля после выхода из `with`; `to_data` внутри сессии (`category_rel`, `wishlist_service.py:310-312`) | Edge |
| 85 | **(v3, дополнена) Явные границы расчёта «вчера»** | FR-1.a, AC-3, FR-6 | Таблица границ: `_forecast_balances(ref-LOOKBACK, …)`, `collect_start = min(_month_start(ref), ref-LOOKBACK)`, **`calc_dates` как вход обоих хелперов**; `None` → прочерк вместо «0 ₽»; строка про `_is_empty`/`savings_by_date` (#89, R5b) | Edge |
| 86 | **Форма `days` — контракт куска 1** | C-5, C-7 | `days` строится только из `window_dates`; регрессионный тест `len(days) == WINDOW_DAYS and days[0].date == ref`; `calc_dates` — служебный локальный список, в контракт не попадает | Integration |
| 87 | **НОВОЕ (v3). Объявленное расхождение цифры «Аналитика» с месячным слоем «Платежи» графика** | FR-6, FR-1.d, C-3 | Причины названы по телу `get_expenses_by_category` (`analytics_service.py:85-100`: `EXPENSE` И `is_recurring == False` → нет виртуальных recurring, нет `savings_*`/`adjustment`); объявлено в трёх местах: докстринг `AnalyticsCardData`, подпись карточки «расходы августа · без регулярных и взносов в цели», эта строка RTM; тест на наличие подписи. `AnalyticsService` НЕ правится; протокол по семантике «расходов месяца» в куске не заводится (решение владельца) | UX/Edge |
| 88 | **НОВОЕ (v3). Сайдбар без Output-колбэков** (Подход B, решение владельца) | C-6, FR-2, AC-1, AC-9 | `render_sidebar_slot(pathname, profile_updated)` — один колбэк, два Input'а на всегда присутствующие `url`/`profile-updated`, одна сессия внутри, `[]` на дашборде до её открытия; `create_sidebar(pathname, profile)` — чистая функция (было: без аргументов, литералы 😊 `:65` и «Пользователь» `:82`, `_build_nav_links("/dashboard")` `:106`); **оба** прежних колбэка удалены; `test_sidebar.py` (контракт входов + профиль в дереве + «в модуле нет `@callback`»); ручной пункт «имя и аватар на четырёх разделах и после правки профиля»; сессия внесена в стратегию загрузки | Integration |
| 89 | **НОВОЕ (v3). «Вчера» считается тем же оконным каскадом, что окно** | FR-1.a, FR-6, C-3, C-5 | `calc_dates = [ref-LOOKBACK] + window_dates` → один вызов `_payments_tail_by_day(payments, calc_dates, payments_end)` (**правильный порядок аргументов**, подпись `:423-428`) и один `_goals_part_by_day(savings_by_date, calc_dates, monthly_budget)`; **тест на значение** `yesterday["payments"] == days[0]["payments"] + Σ payments(date == ref)` + **mutation-проверка**; в плане записано, что **тест инварианта суммы этот класс дефектов не ловит** (`_split_day` сохраняет сумму при любом входе) | Edge |
| 90 | **НОВОЕ (v3). Единая механика идемпотентности Store-фокусов** | FR-3, C-1, AC-2 | Для `calendar-focus-date` и `goals-focus-goal` одинаково: payload `{"value","ts"}`; приёмник реагирует только если `ctx.triggered_id` — сам Store **И** `ts != state["focus_applied_ts"]`; применённый `ts` хранится в существующем `calendar-state` (словарь уже возвращается, `calendar.py:926-930`); ручной пункт «ушёл из раздела и вернулся по меню — фокус не переприменяется» | Integration |
| 91 | **НОВОЕ (v3). `dip_*` игнорируется при `status != OK`** | AC-5, AC-7, FR-5 | Причина в теле: `_window_min_free` при пустом `days` возвращает `(Decimal("0"), date.today())`, а не `None` (`:690-691`) → без оговорки чистая база дала бы «Ближайшая просадка: сегодня, 0 ₽». Зафиксировано в докстрингах `CalendarCardData` и `build_calendar_card`; целевой тест UI «`EMPTY` при непустых `dip_*` → маркера в дереве нет» | Edge |
| 92 | **НОВОЕ (v3). Отсутствие пользователя = `EMPTY`, не `FAILED`** | AC-5, FR-5, NFR-2 | `_goals_block` читает `session.get(User, uid)` (одно чтение → `cushion_target`, `monthly_savings_budget`, `savings_mode`) вместо `get_savings_budget`/`get_savings_mode`, которые бросают `ValidationError` при отсутствии пользователя (`goal_service.py:458-476`, `:512-529`); `None` → `EMPTY`, как `_user_data_markers` («чистая база штатна»); **тест AC-5 в двух вариантах фикстуры**; побочно минус два вызова из стратегии загрузки | Edge |

## Blast Radius

### Прямые изменения

**Новые файлы (6)**
- `app/schema/panel.py` — контракты карточек + `TRANSACTION_KIND_MAP`
- `app/services/panel_service.py` — `DashboardPanelService`
- `app/components/panel_cards.py` — build-функции карточек
- `tests/test_panel_service.py`, `tests/test_panel_cards_ui.py`
- `tests/test_sidebar.py` — **новый (v3)**: контракт входов `render_sidebar_slot`, профиль в дереве, отсутствие `@callback` в модуле

**Изменяемые файлы (14)**

| Файл | Что меняется | Почему связано |
|---|---|---|
| `app/components/dashboard.py` | Layout → шапка+график+`dashboard-cards-row`; удаляются `_build_transactions_split_table`, `_build_cushion_card_readonly` (**сессия `:871`**), `_build_empty_state`, вызов `build_wishlist_widget()` (`:687`, **сессия `wishlist.py:33`**); `_load_dashboard_components` 5→3; оба колбэка 5→3 Output'а; 4 clientside-триггера пустых состояний удаляются, 1 (дверь Wishlist) добавляется; импорты вычищаются. **`build_layers_chart`/`_axis_tickvals` НЕ ПРАВЯТСЯ** | ядро задачи |
| `app/main.py` | **(v3)** `sidebar-slot` + `render_sidebar_slot` с **двумя** Input'ами и **чтением профиля** (переезд из `sidebar.py`); статический `create_sidebar()` (`:59`) снимается; `handle_calendar_query_params` → `handle_panel_query_params` (+2 Output'а, `_OWNED_SEARCH_PATHS`); 3 новых `dcc.Store`; новые импорты `get_db_session`/`OnboardingService`/`get_avatar_emoji` | FR-2, FR-3, блокер №2 |
| `app/components/sidebar.py` | **(v3, объём больше, чем в v2)** `create_sidebar(pathname, profile)` — чистая функция; литералы `😊` (`:65`) и «Пользователь» (`:82`) заменяются аргументом; `_build_nav_links("/dashboard")` (`:106`) → `_build_nav_links(pathname or "/dashboard")`; **удаляются ОБА колбэка**: `highlight_active_sidebar` (`:152-160`) и `update_sidebar_profile` (`:163-185`); уходят импорты `callback/Input/Output`, `get_db_session`, `OnboardingService`, `logger`, `exc_info=True` (`:184`) | блокер №2, Подход B |
| `app/components/profile_modal.py` | `Input("sidebar-profile-container")` (`:96`) убирается — единственный вход `open-profile-trigger`; guard на пустой Store сохраняется; `exc_info` (`:143,159,163`) → `logger.opt` | AC-9 / C-6, R1 |
| `app/components/wishlist.py` | `build_wishlist_widget` (`:25-80`)/`_build_widget_item` удаляются; `open_wishlist_modal` — **единственный** Input `open-wishlist-trigger` + guard; `Input("open-wishlist-modal-btn")` (`:423`) удаляется | AC-8, C-6 |
| `app/components/calendar.py` | **(v3)** `Input("calendar-focus-date")` шестым Input'ом; **двойной guard идемпотентности** (`ctx.triggered_id` + `focus_applied_ts`); ключи `focus_date`/`focus_applied_ts` в возвращаемом `new_state` (`:926-930`); класс `calendar-day-focused` в `build_day_cell` (`css_classes`, `:596`) | FR-3, AC-2, №7 |
| `app/components/goals.py` | якорные id в `_build_goal_card` (`:618`); узел `goals-focus-anchor`; колбэк `apply_goal_focus` **с той же механикой идемпотентности** | FR-3, AC-2, №7 |
| `app/components/__init__.py` | снятие `build_wishlist_widget` из импортов и `__all__` | удаление функции |
| `app/services/money_layers_service.py` | **(v3)** только: `calc_dates` в `get_money_layers`, левая граница `_forecast_balances`, `collect_start` в `_horizons`, **точки вызова** `_payments_tail_by_day`/`_goals_part_by_day`, новый `_yesterday_slice`, заполнение поля, `Note` в докстринге `_is_empty`. **Тела** `_payments_tail_by_day`, `_goals_part_by_day`, `_split_day`, `_today_slice`, `_window_min_free`, `_is_empty`, `_user_data_markers`, `_goal_milestones`, `window_dates`, `days` — **без правок** | C-5, AC-3, блокер №1 |
| `app/schema/money_layers.py` | **(v3)** **ОДНА** константа `LOOKBACK: timedelta` (замечание №9) + **одно** поле `yesterday`. Полей `tomorrow`/`window_start` нет: «завтра» — `days[1]`, `window_start == reference_date` | C-5 |
| `app/schema/__init__.py`, `app/services/__init__.py` | реэкспорт новых схем и сервиса | конвенция проекта |
| `app/assets/panel.css` | секции дверей, wishlist-полосы, `.pnl-note` (подпись расхождения), адаптив, `prefers-reduced-motion` | эскиз v3, №5 |
| `app/assets/custom.css` | удаление `.db-left-col`, `.db-right-col`, `.db-main-row`, `.dashboard-split-table`; правка `.db-page` | старая раскладка 8/4 |
| `app/assets/sidebar.css`, `app/assets/calendar.css` | **один** механизм скрытия: `.sidebar-column:empty { display:none }`; `.calendar-day-focused` | №9, FR-3 |

### Связанные файлы

**Тесты, требующие адаптации**
- `tests/test_dashboard_callbacks.py` — `load_dashboard_data`/`refresh_dashboard_after_crud` 5→3 Output'а, контракт декоратора
- `tests/test_profile_modal_callbacks.py` — вход через Store вместо `sidebar-profile-container`
- `tests/test_money_layers_service.py` — **только добавление** (`yesterday["payments"]` на значение + mutation, инвариант, форма `days`, неизменность дней окна, 1-е число, `is_empty` с savings прошлого месяца)
- **любые тесты, ссылающиеся на `highlight_active_sidebar`/`update_sidebar_profile`** — проверить `grep` перед шагом 8; удаляются вместе с колбэками, их роль переходит к `tests/test_sidebar.py` **(v3)**

**Ушло из Blast Radius по сравнению с v1 (аккуратный вариант «вчера»)**
- `tests/test_dashboard_panel_ui.py` (47 тестов) — правок не требует: фикстура `make_layers_data` строит `days` как `range(WINDOW_DAYS)` от `ref` (`:113`), и это остаётся верным; `data.update(overrides)` делает добавление ключа необязательным; единственные консьюмеры `days` — `dashboard.py:502/510/513`, поле `yesterday` они не читают
- `build_layers_chart` и `_axis_tickvals` — вне правок
- Хелпер `window_days()` — не создаётся; `MoneyLayersData.tomorrow`/`window_start` — не добавляются
- `CushionService` из зависимостей композитора — исключён

**Добавилось в Blast Radius по сравнению с v2**
- `app/main.py` — **чтение профиля и сессия** внутри `render_sidebar_slot` (в v2 сессии там не было): в зону риска входит поведение имени/аватара на четырёх разделах и после правки профиля
- `app/components/sidebar.py` — удаляется **второй** колбэк (`update_sidebar_profile`), файл становится без колбэков вовсе
- `tests/test_sidebar.py` — новый файл (в v2 сайдбар тестами не был покрыт вовсе, что и позволило блокеру №2 остаться незамеченным)
- `app/schema/panel.py` — `TRANSACTION_KIND_MAP` как публичная часть контракта
- Точки вызова двух хелперов `money_layers_service.py` (в v2 планировался отдельный точечный вызов)

**Файлы БЕЗ правок, но в зоне контрактного риска (проверить прогоном/вручную)**
- `app/components/transactions.py` — `apply_url_date_filter` остаётся единственным владельцем `search` на `/transactions`
- `app/components/analytics.py` — дефолт `analytics-period-store` становится приёмником двери Аналитики
- `app/components/calendar_wishlist.py` — `wishlist-active-item` становится приёмником второго уровня двери Wishlist
- `app/components/transaction_modals.py` — `refresh_dashboard_after_crud` меняет арность Output'ов
- `app/components/onboarding_wizard.py` — **(v3)** пишет `profile-updated`, который теперь слушает `render_sidebar_slot` вместо удалённого `update_sidebar_profile`; проверить, что сайдбар перерисовывается после онбординга
- `app/services/dashboard_service.py`, `analytics_service.py`, `goal_service.py`, `allocation_service.py`, `wishlist_service.py`, `cushion_service.py`, `onboarding_service.py` — только вызываются (C-3); `cushion_service` композитором **не вызывается** вовсе; `goal_service.get_savings_budget`/`get_savings_mode` композитором **не вызываются** (остаются для раздела «Цели»)

**Общие component ID / Store'ы, затронутые семантически**
- новые: `sidebar-slot`, `dashboard-cards-row`, `panel-wishlist-door`, `open-wishlist-trigger`, `calendar-focus-date`, `goals-focus-goal`, `goals-focus-anchor`
- удаляемые: `dashboard-recent-transactions`, `dashboard-upcoming-transactions`, `dashboard-cushion-card`, `empty-recent-add-btn`, `empty-upcoming-add-btn`, `open-wishlist-modal-btn` (вместе со своим Input'ом)
- меняющие роль: `open-profile-trigger` (был вторым входом — стал единственным), `open-wishlist-trigger` (единственный вход в модал wishlist), `wishlist-active-item` (был только из календаря — стал и из карточки), **`sidebar-nav`, `sidebar-profile-name`, `sidebar-profile-avatar` (перестают быть Output'ами колбэков — заполняются при построении)**, `profile-updated` (**становится Input'ом `render_sidebar_slot` вместо удалённого `update_sidebar_profile`**), `calendar-state` (получает ключи `focus_date`, `focus_applied_ts`), `dashboard-period` (остаётся guard'ом клика по графику)

**Документация (после реализации)**
- `.obsidian-docs/knowledge-bank/modules/ui-components.md` — секции Dashboard-щиток, **Sidebar (ноль колбэков, профиль аргументом)**, новая секция Panel Cards; ограничение карточки «Операции»; **объявленное расхождение цифры «Аналитика»**
- `.obsidian-docs/knowledge-bank/modules/services.md` — `DashboardPanelService` (контракт материализации, преобразования типов, стратегия загрузки с сессией сайдбара и «было 3 сессии»); эволюция `MoneyLayersService` (поле `yesterday`, `calc_dates`, форма `days` неизменна)
- `.obsidian-docs/knowledge-bank/modules/schema.md` — `app/schema/panel.py` (включая `TRANSACTION_KIND_MAP`), `yesterday` и `LOOKBACK` в `money_layers.py`
- `.obsidian-docs/knowledge-bank/modules/routing.md` — `?focus_date=`, `?goal=`, контракт владения `url.search` по pathname, **механика идемпотентности Store-фокусов**
- `.obsidian-docs/knowledge-bank/patterns/callbacks.md` — правило «удаляешь элемент — удаляй его Input»; кейс «Output на условно присутствующий элемент лечится условным рендером и переносом данных в построение, а не guard'ом» (**оба** Output'а сайдбара как пример)
- **`.obsidian-docs/knowledge-bank/patterns/` — НОВЫЙ урок (заметка критика на будущее):** «хелперы `MoneyLayersService`, принимающие `window_dates`, определены только для непрерывного окна и точечно не переиспользуются». Два случая уже были (`_forecast_balances` в критике v1, `_payments_tail_by_day` в критике v2), кусок 3 и карточки других страниц зайдут в этот файл снова; ловить третий случай на ревью реализации дороже, чем записать правило. В тот же урок — приём проверки: **прежде чем утверждать поведение приватного хелпера, открыть его тело**, а не подпись и не докстринг
- `memory/spec-context/epic-11.md` — удалить применённые записи с тегом `for: design-loop`

### Проверить после реализации

1. **AC-9 вручную**: профиль открывается шестерёнкой на `/dashboard` И аватаром на каждом из четырёх разделов (R1).
2. **Блокер №2 вручную (v3, целевая проверка)**: **имя и аватар в сайдбаре корректны на `/calendar`, `/goals`, `/transactions`, `/analytics`; после правки профиля обновляются без перезагрузки; после перехода в другой раздел не сбрасываются на «Пользователь» + 😊** (R12b). Плюс подсветка активного пункта во всех четырёх разделах (R12). Плюс `patch` падающего `get_profile` → сайдбар с пятью пунктами меню и заглушкой имени (R12c).
3. **AC-8 вручную**: клик по телу/заголовку карточки Wishlist открывает модал; клик по хотелке ведёт в режим покупок календаря с фокусом.
4. **Владение `search` вручную**: клик по группе «Недавние»/«Предстоящие» → `/transactions?start=&end=` → фильтр применён; F5 → фильтр остался без ошибки; переход на `/calendar?focus_date=…` → `search` очищен, F5 контекст не переприменяет.
5. **Идемпотентность вручную (v3, замечание №7)**: дашборд → «завтра» → календарь на завтра → пролистать на октябрь → уйти в «Операции» → **вернуться в «Календарь» по меню → октябрь остался, прыжка нет**; то же для фокуса цели; повторный клик по тому же элементу двери срабатывает (timestamp).
6. **AC-1 вручную**: сайдбара на дашборде нет и он не оставляет пустой колонки (одно правило `:empty`).
7. **C-7**: `pytest tests/test_dashboard_panel_ui.py` — 47 тестов зелёные **без правок**; график полос визуально идентичен куску 1.
8. **«Вчера» (R3, R3b)**: `pytest tests/test_money_layers_service.py` — **тест на значение `yesterday["payments"]` зелёный, а при замене `calc_dates` на `window_dates` КРАСНЕЕТ** (mutation-проверка обязательна: без неё нельзя утверждать, что тест смотрит туда, куда нужно); `yesterday != 0` на истории; инвариант; форма `days`; неизменность `payments` дней окна; фикстура «1-е число»; фикстура «1-е число + savings прошлого месяца» → `is_empty is False` (R5b).
9. **Материализация (R11)**: тест на все поля `PanelData` после закрытия сессии зелёный; вручную открыть дашборд на наполненной базе — в логах нет `DetachedInstanceError`.
10. **Типы (R18)**: тест `isinstance(panel["operations"]["recent"][0]["date"], date)`; тест `kind` на всех шести значениях `TransactionType`; вручную — подпись даты в карточке Операции читается как «5 февраля», а не мусор, и карточка не в `FAILED`.
11. **AC-5 (R17)**: тесты пустой базы **в двух вариантах** — с `User(id=1)` и без него; в обоих все пять блоков `EMPTY`, `goals` не `FAILED`, в логах нет трейсбека по `goals`.
12. **AC-7 / №10**: `pytest tests/test_panel_cards_ui.py` — усиление маркера в двух фикстурах; **`status=EMPTY` при непустых `dip_*` → маркера в дереве нет**; вручную на чистой базе — строки «Ближайшая просадка: сегодня, 0 ₽» нет.
13. **№5**: вручную — под цифрой карточки Аналитика читается подпись «расходы августа · без регулярных и взносов в цели»; цифра совпадает с разделом «Аналитика» за тот же месяц.
14. **NFR-1**: замер `_load_dashboard_components` (время И число SQL-запросов) + **отдельный замер `render_sidebar_slot("/calendar", None)`**, запись в протокол, сверка с 13 мс куска 1; счётчик `get_money_layers == 1`.
15. **AC-3**: `pytest tests/test_panel_service.py tests/test_sidebar.py`.
16. **AC-10**: полный `pytest` (693 + новые), `black --check`, `flake8`.
17. **NFR-2**: `patch`-тест падающего блока — дашборд рендерится, одна карточка деградирована, в логах трейсбек.

## Учтённые замечания из критики

| # | Замечание критики v2 | Решение в v3 |
|---|---|---|
| 🔴 1 | `_payments_tail_by_day([yday], payments, payments_end)` вернёт ноль по построению — «вчера» получит `payments = 0` и завышенное `free`; плюс порядок аргументов перепутан | **Подход A критика.** Прочитано тело (`:423-462`): `by_day` собирается по всему `payments`, но `result` наполняется проходом `for day in reversed(window_dates)` с накоплением `tail` **из того же списка** — на `[yday]` одна итерация, `tail == 0`, `yday < payments_end` → `Decimal("0")`. Введён служебный локальный `calc_dates = [yday] + window_dates`, **один** вызов `_payments_tail_by_day(payments, calc_dates, payments_end)` — **правильный порядок аргументов** по фактической подписи; из результата берутся и `yday`, и дни окна; `days` строится по-прежнему **только** из `window_dates` (форма контракта куска 1 не меняется). Имя `calc_dates` выбрано, чтобы читатель не решил, что окно сдвинуто; в докстринге поля `yesterday` и в `_yesterday_slice` сказано, зачем список расширен. Почему Подход A, а не «хвост `ref` + платежи дня `ref`»: вторая формула для одного понятия — та болезнь, от которой лечит весь кусок. **Тела хелперов не правятся** — меняются только точки вызова (C-3). Обязательные тесты: **на значение** `yesterday["payments"] == days[0]["payments"] + Σ payments(date == ref)` + **mutation-проверка** (замена `calc_dates` → `window_dates` красит тест) + «значения `payments` дней окна не изменились». **В план прямо записано: тест инварианта суммы этот класс дефектов НЕ ловит принципиально** — `_split_day` (`:598-643`) сохраняет сумму при любом входе, поэтому при `payments=0` инвариант сходится, а `free` просто больше на ту же величину; не ловят и тесты «`forecast_balance != 0`», формы `days`, «не ноль/не отрицательное». `_goals_part_by_day` **перепроверен по телу** (`:579-599`): внешний цикл по `window_dates`, внутри полный обход `savings_by_date` с фильтром по месяцу дня `D` — от состава списка **не зависит** (критик прав); тот же `calc_dates` передаётся ему для единственности списка, а не по необходимости |
| 🔴 2 | Удаление `highlight_active_sidebar` оставляет `update_sidebar_profile` с условно присутствующими Output'ами — имя и аватар ломаются; утверждение «`create_sidebar` уже читает профиль» неверно | **Подход B критика, принят владельцем.** Прочитано `create_sidebar()` (`sidebar.py:57-146`): **аргументов нет, сессия не открывается**, литерал `"\U0001f60a"` в `sidebar-profile-avatar` (`:65`), литерал `"Пользователь"` в `sidebar-profile-name` (`:82`), `_build_nav_links("/dashboard")` захардкожен (`:106`) — утверждение v2 было ложным, реальные имя и аватар приходили только из `update_sidebar_profile` (`:163-185`). v3: `render_sidebar_slot(pathname, profile_updated)` — **один** колбэк, **два** Input'а на всегда присутствующие `url` (`main.py:52`) и Store `profile-updated` (`:90`), внутри **одно** чтение профиля (`OnboardingService.get_profile` = `session.get(User, uid)`, `onboarding_service.py:150-166`) с fail-open, `[]` на дашборде **до** открытия сессии; `create_sidebar(pathname, profile)` — **чистая функция**. Колбэки `highlight_active_sidebar` **и** `update_sidebar_profile` удаляются **ОБА** — у сайдбара не остаётся ни одного Output-колбэка и ни одного Input на его элементы. Цена (одна сессия и один SELECT User на переход между разделами; на дашборде — ноль) внесена в «Стратегию загрузки» **явно**, отдельным абзацем, и в замер шага 12 отдельной цифрой. Новое покрытие: `tests/test_sidebar.py` — контракт входов через `inspect.getsource`, имя и эмодзи из профиля в дереве, класс `sidebar-nav-item-active` у активного пункта, `render_sidebar_slot("/dashboard", None) == []`, **«в модуле `sidebar` нет ни одного `@callback`»**; fail-open при падении `get_profile`. Ручной пункт шага 13: «имя и аватар корректны на всех четырёх разделах и после правки профиля». Новый риск R12c (сессия на пути навигации) закрыт fail-open: сбой чтения имени не лишает пользователя меню |
| 🟡 3 | Перечень границ объявлен исчерпывающим, но `_is_empty` через `savings_by_date` от расширения `collect_start` зависит | Строка таблицы границ **исправлена**: `_is_empty` — «тело без изменений, **но зависимость есть**», с указанием механизма: третье условие `if payments or savings_by_date` (`:807`) смотрит на словарь, который `_collect_operations` наполняет **без фильтра по датам** от `collect_start` (`:415-418`); `payments` защищён фильтром `day >= reference_date` (`:404`), а `savings_by_date` — нет. Добавлена строка и про `window_is_flat` (тот же словарь, то же направление). **Решено явно: принять** (рекомендация критика) — сценарий узкий (`ref` = 1-е число И `starting_balance == 0` И нет шаблонов И savings-операция в конце прошлого месяца И нулевые балансы окна), направление безопасное (плоский график вместо пустого состояния — больше информации, а не меньше), а фильтрация словаря завела бы его второй смысл. Одна строка `Note` в докстринге `_is_empty` (текст приведён). Фикстура **«1-е число + savings-операция 31-го прошлого месяца» с ассертом `is_empty is False`** — тест шага 1 п. 9; если кто-то позже решит фильтровать, тест покраснеет и решение будет пересмотрено осознанно. Риск вынесен отдельной строкой R5b |
| 🟡 4 | `OperationRow.date: date` против `RecentTransaction["date"]: str` — контракт карточки не сходится с источником; правило сведения `transaction_type` → `kind` не задано | Прочитано `_map_transactions` (`dashboard_service.py:456-472`) и `RecentTransaction` (`:81-91`): `date=t.transaction_date.isoformat()` — **строка**; `transaction_type=t.transaction_type.value` — одна из **шести** строк `TransactionType` (`database.py:31-39`); поле называется **`is_recurring_instance`**, не `is_recurring`; `description` может быть `None`. Прочитан `format_date_human` (`formatters.py:119-128`): `date_obj.day` — на строке `AttributeError`, то есть блок ушёл бы в `FAILED` **на нормальных данных**, и тесты карточек этого не увидели бы (кормятся словарями с `date`). В шаге 3 и в докстринге `_operations_block` записаны **все четыре** преобразования: `date.fromisoformat(row["date"])`, `TRANSACTION_KIND_MAP.get(value, "other")`, `is_recurring_instance → is_recurring`, `title = description or category_name or "Без описания"`. **Таблица сведения** — публичная константа `TRANSACTION_KIND_MAP` в `app/schema/panel.py`: `income→income`; `expense→expense`; `savings_reserve`, `savings_contribution`→`expense` (деньги уходят из остатка — та же трактовка, что `_PAYMENT_TYPES` модели); `transfer`, `adjustment`→`other` (направление определяется знаком суммы, не типом). Тесты: `isinstance(panel["operations"]["recent"][0]["date"], date)` и `kind` на фикстуре со **всеми шестью** значениями enum (покраснеет при добавлении седьмого). Риск R18 |
| 🟡 5 | Карточка «Аналитика»: `month_total` от `get_expenses_by_category` не сопоставим с расходами графика — FR-6 требует это назвать | **Решение владельца: объявить расхождение, сервис не менять.** Цифра карточки считается тем же `AnalyticsService`, что и раздел «Аналитика» — это правильно и сохраняется. Прочитано тело `get_expenses_by_category` (`analytics_service.py:85-100`): фильтр `transaction_type == EXPENSE` **И** `is_recurring == False`, отсюда две названные причины расхождения с месячным слоем «Платежи»: (а) виртуальные инстансы регулярных платежей в цифру не входят, а в слой входят (модель считает их через `CalendarService`); (б) `savings_reserve`/`savings_contribution`/отрицательные `adjustment` в цифру не входят, а в слой входят (`_PAYMENT_TYPES` + ветка `adjustment`, `money_layers_service.py:397-402`). Объявлено **в трёх местах, симметрично уже принятому ограничению карточки «Операции»**: докстринг `AnalyticsCardData` (с обеими причинами и ссылками на тела), подпись в карточке «расходы августа · без регулярных и взносов в цели» (`.pnl-note`, мелкий кегль), строка RTM #87. Тест на наличие подписи в дереве (шаг 10) + ручная сверка с разделом (проверка 13). Правка `AnalyticsService` запрещена C-3; **отдельный протокол по семантике «расходов месяца» в этом куске не заводится** (решение владельца). Риск R16 |
| 🟡 6 | `_goals_block` на чистой базе без пользователя даст `FAILED`, а не `EMPTY` — AC-5 под вопросом | Прочитаны тела `get_savings_budget` (`goal_service.py:458-476`) и `get_savings_mode` (`:512-529`): **каждый** = `session.get(User, uid)` → `raise ValidationError` если нет → `return` **одного поля** (`user.monthly_savings_budget` / `user.savings_mode`). Поля те же и `User` тот же, который блоку и так нужен для `cushion_target` — значит рекомендация критика применима буквально: `_goals_block` делает **одно** `session.get(User, user_id)` и берёт три поля; `user is None` → **`EMPTY`** (симметрично `_user_data_markers`, `:812-830`: «на отсутствующем пользователе — `(0, False)`: чистая база штатна»). Побочно **из стратегии загрузки уходят два вызова**, а `ValidationError` в этом пути неоткуда взяться вовсе. Строка в таблице обработки ошибок: «Пользователь отсутствует → `EMPTY`, не `FAILED`, без лога — штатный путь». **Тест AC-5 в двух вариантах фикстуры** (шаг 4): пустая база **с** `User(id=1)` и **без** пользователя — в обоих все пять блоков `EMPTY`, и отдельный ассерт «в логах нет трейсбека по `goals`» (иначе тест можно подкрутить под `FAILED` незаметно). Риск R17 |
| 🟡 7 | `calendar-focus-date` — Store как состояние: приёмник переприменит фокус при возврате на календарь | **Единая механика для обоих новых Store'ов**, описанная одним абзацем и применённая дважды. Прочитан `load_and_navigate_calendar` (`calendar.py:758-947`): пять Input'ов (`url.pathname`, три кнопки навигации, `wishlist-active-item`), `State("calendar-state")`, `ctx.triggered_id` уже используется для ветвления (`:815-825`), возвращаемый `new_state` = `{"current_month","current_year","balances"}` (`:926-930`) — словарь состояния уже есть. Механика: (1) реагируем **только** если `ctx.triggered_id` — это **сам Store** (иначе «вернулся в раздел по меню» переприменяло бы прошлый фокус, потому что колбэк срабатывает по `url.pathname`, а Store хранит значение до перезагрузки страницы); (2) **и только** если `payload["ts"] != state.get("focus_applied_ts")` — сравнение применённого timestamp с сохранённым в существующем `calendar-state`, куда `focus_applied_ts` кладётся рядом с `focus_date`; (3) применение = месяц/год из даты + класс `.calendar-day-focused` в `build_day_cell` (`css_classes` — список, `:596`). Payload новых Store'ов сделан словарём `{"value","ts"}`, а не скаляром, чтобы `ts` был доступен приёмнику. Тот же абзац буквально — для `goals-focus-goal` в `apply_goal_focus`. **Пункт ручного чек-листа шага 13**: «ушёл из раздела и вернулся по меню — фокус не переприменяется» (с полным сценарием: клик «завтра» → пролистать на октябрь → уйти в Операции → вернуться по меню → октябрь остался). Риск R10 переформулирован в два подслучая |
| 🟢 8 | «Сессий за рендер: 1 (было 4)» — фактически было 3 | Исправлено на **3** с перечислением по диску: `dashboard.py:1002` (`_load_dashboard_components` — профиль **и** слои **и** recent **и** upcoming в **одной** сессии, поэтому четвёртой нет), `dashboard.py:871` (`_build_cushion_card_readonly`), `wishlist.py:33` (`build_wishlist_widget`, вызывается **из layout** `dashboard.py:687`, а не из колбэка). **Побочный выигрыш назван**: контейнер виджета wishlist не является Output'ом ни одного колбэка (проверено `grep` по `wishlist-widget`) — виджет строится один раз в layout и **сегодня не обновляется по `global-transaction-trigger`**; карточка Wishlist это исправляет, потому что приходит из `PanelData`, перерисовываемого CRUD-триггером вместе со всем щитком. Цифра поправлена в докстринге сервиса, в RTM #32/#34 и в Blast Radius, чтобы не поехала в knowledge-bank как факт |
| 🟢 9 | `WINDOW_LOOKBACK_DAYS` и `WINDOW_LOOKBACK_DAYS_TD` — две константы на одно понятие | Оставлена **ОДНА**: `LOOKBACK = timedelta(days=1)` в `app/schema/money_layers.py`. Тип `timedelta`, а не `int`, потому что все три места использования — арифметика с `date` (`ref - LOOKBACK` в `_forecast_balances`, в `collect_start`, в `calc_dates`); при `int` каждое место требовало бы `timedelta(days=…)`, то есть три возможности разойтись. Обоснование выбора типа — в докстринге константы, там же прежнее предупреждение «это НЕ расширение окна» |
| 🟢 10 | `dip_href` при пустом окне: `min_free_date` возвращает `date.today()`, а не `None` | Прочитано `_window_min_free` (`:669-697`): `if not days: return Decimal("0"), date.today()` — критик прав, **не `None`**. Зафиксировано **одной строкой намерения в трёх местах**: докстринг `CalendarCardData` («при `status != OK` поля `dip_*` НЕ рисуются, даже если непустые»), докстринг `build_calendar_card` (с причиной и ссылкой на `:690-691`), таблица границ. Иначе на чистой базе появилось бы «Ближайшая просадка: сегодня, остаток 0 ₽» — числовой артефакт, прямо запрещённый AC-5. Плюс **целевой тест UI** (шаг 10): фикстура `status=EMPTY` с **непустыми** `dip_date`/`dip_free` → маркера в дереве нет (общий тест «нет `₽`/`%`» это тоже поймал бы, но не объяснил бы, что именно проверяется), и ручная проверка 12 |

## Ответы на вопросы критика

**1. `[факт]` Какой именно набор дат передаётся в `_payments_tail_by_day` и `_goals_part_by_day` при расчёте «вчера», и чему равен `yesterday["payments"]` на фикстуре с платежами внутри месяца?**

Передаётся **один** список на оба хелпера: `calc_dates = [ref - LOOKBACK] + window_dates` — строго возрастающий, непрерывный, `WINDOW_DAYS + 1` элементов. Каждый хелпер вызывается **один раз**, точечных вызовов нет.

Формула, выведенная из тела `_payments_tail_by_day` (`money_layers_service.py:423-462`), а не из подписи. Тело: `by_day` наполняется по всему списку `payments` с фильтром `payment["date"] <= payments_end`; затем

```python
tail = Decimal("0")
for day in reversed(window_dates):
    if day >= payments_end:  result[day] = Decimal("0")
    else:                    result[day] = tail
    tail += by_day.get(day, Decimal("0"))
```

Проход идёт **справа налево**, `yday` — самый левый элемент `calc_dates`, значит:

```
yesterday["payments"] (до каскада) = result[yday]
                                   = result[ref] + by_day.get(ref, 0)
                                   = хвост «сегодня» + Σ платежей с датой ровно ref
```

и **ни одно значение для дней окна не меняется** (добавление элемента слева не влияет на уже накопленные правые ключи). Граничный случай `yday >= payments_end` (то есть `ref` — 1-е число, а `payments_end` — конец **этого** месяца; `yday` тогда в прошлом месяце и `yday < payments_end` всегда) невозможен по построению `_horizons`, но ветка `day >= payments_end` в теле есть и даёт `0` — корректно.

После `_split_day` (`:598-643`) значение может быть сжато: при `balance < 0` → `payments = 0`; при дефиците — гашение сначала `reserve`, потом `payments`. Тест поэтому ставится на фикстуре с положительным балансом и достаточным остатком, где каскад не срабатывает, а инвариант проверяется отдельным тестом.

`_goals_part_by_day` (`:462-599`): **перепроверено по телу** — критик прав, от состава списка **не зависит**. Внешний цикл `for day in window_dates`, внутри полный обход `savings_by_date.items()` с фильтрами `month_start(day) <= op_date <= day` и `day < op_date <= month_end(day)`; значение каждого ключа — функция только от `day` и `savings_by_date`. Ему `calc_dates` передаётся не по необходимости, а чтобы список был **один**: два разных списка для двух хелперов — новая возможность разойтись.

Тесты **на само значение**, а не на инвариант: (а) `yesterday["payments"] == days[0]["payments"] + Σ amount платежей с датой == ref` на фикстуре с платежами внутри месяца; (б) **mutation-проверка** — заменить `calc_dates` на `window_dates` в вызове, тест обязан покраснеть; (в) значения `payments` дней окна не изменились от расширения списка. **В плане прямо записано, почему инварианта недостаточно**: `_split_day` сохраняет сумму при любом входе, поэтому при `payments=0` инвариант сходится, а `free` завышен на ту же величину — весь набор страховок v2 (инвариант + «`forecast_balance != 0`» + правдоподобность значения) проходил мимо дефекта.

**2. `[факт]` Откуда карточка профиля сайдбара берёт имя и аватар после удаления `highlight_active_sidebar` и снятия сайдбара с дашборда?**

Из **аргумента**, который передаёт `render_sidebar_slot`. Критик прав по факту, и утверждение v2 было ложным — проверено по телу `create_sidebar()` (`sidebar.py:57-146`): функция **не принимает аргументов**, **не открывает сессию**, подставляет литерал `"\U0001f60a"` в `sidebar-profile-avatar` (`:65`), литерал `"Пользователь"` в `sidebar-profile-name` (`:82`) и захардкоженный `_build_nav_links("/dashboard")` (`:106`). Реальные имя и аватар приходили **только** из `update_sidebar_profile` (`:163-185`), который читает `OnboardingService.get_profile` и висит на `url.pathname` + `profile-updated`; подсветка активного пункта — только из `highlight_active_sidebar` (`:152-160`).

Реализация — **Подход B критика** (решение владельца: «одна сессия на построение сайдбара — приемлемая цена»):

```
render_sidebar_slot(pathname, profile_updated)   ← ЕДИНСТВЕННЫЙ колбэк сайдбара
  Input("url","pathname")        ← элемент есть ВСЕГДА (main.py:52)
  Input("profile-updated","data") ← Store глобального layout, есть ВСЕГДА (main.py:90)
  Output("sidebar-slot","children") ← контейнер статичен, есть ВСЕГДА
  дашборд → [] (сессия НЕ открывается)
  иначе  → одна сессия → get_profile → create_sidebar(pathname, profile)
```

`create_sidebar(pathname, profile)` становится **чистой функцией**. Колбэки `highlight_active_sidebar` и `update_sidebar_profile` удаляются **оба**; у сайдбара не остаётся ни одного Output на условно присутствующий элемент и ни одного Input на его элементы — правило, которое v2 вывела и применила наполовину, применяется до конца.

Почему не guard на pathname (вариант, к которому подталкивала v2): при Input'е `url.pathname` это та же гонка, что у `highlight_active_sidebar` — второй колбэк пишет `children` в узлы, которые первый в этот же момент создаёт или удаляет, а порядок применения Output'ов Dash не гарантирует. Без Input'а `url.pathname` — регрессия функциональности Epic-09 фазы 2: после каждого перехода сайдбар возвращался бы к «Пользователь» + 😊, потому что `profile-updated` не менялся.

Цена внесена в «Стратегию загрузки» **явно** (её там не было ни в одном варианте v2): на `/dashboard` — 0 сессий; на четырёх разделах — 1 сессия и 1 SELECT User на переход (`get_profile` = `session.get(User, uid)`, `onboarding_service.py:150-166`), плюс та же сессия при каждой правке профиля. Против бюджета NFR-1 (2 с при 13 мс куска 1) не значимо; в замер шага 12 добавлена отдельная цифра. Сбой чтения профиля **не обрушивает** сайдбар: fail-open — `except` → профиль-заглушка (`"Пользователь"`, `DEFAULT_AVATAR_ID`) + `logger.opt(exception=True)`, сайдбар рисуется с рабочей навигацией; сбой чтения имени не имеет права лишать пользователя меню (FR-2 «находимость разделов»). Это новый риск Подхода B (R12c), закрытый конструктивно.

Новое покрытие, которого в v2 не было вовсе (и именно поэтому блокер №2 остался незамеченным): `tests/test_sidebar.py` — контракт входов `render_sidebar_slot` через `inspect.getsource` (два Input'а, оба на `url`/`profile-updated`, ни одного на элемент сайдбара); имя и эмодзи из профиля присутствуют в дереве `create_sidebar("/calendar", profile)`; класс `sidebar-nav-item-active` у пункта «Календарь»; `render_sidebar_slot("/dashboard", None) == []`; **в модуле `sidebar` нет ни одного `@callback`** (регрессионный тест против возврата колбэка); `patch` падающего `get_profile` → пять пунктов меню на месте. Ручной пункт шага 13, п. 2: «имя и аватар корректны на всех четырёх разделах и после правки профиля».

**3. `[факт]` Что возвращает `_goals_block` на базе без пользователя — `EMPTY` или `FAILED`?**

В v2 — `FAILED` (дефект). В v3 — **`EMPTY`**, и путь к `ValidationError` устранён вовсе, а не обёрнут в `except`.

Проверено по телам, а не по докстрингам. `GoalService.get_savings_budget` (`goal_service.py:458-476`):

```python
user = self.session.get(User, user_id)
if not user:
    raise ValidationError(f"Пользователь с ID {user_id} не найден")
return user.monthly_savings_budget
```

`GoalService.get_savings_mode` (`:512-529`) — **тот же** `session.get(User, user_id)`, тот же `raise`, `return user.savings_mode`. То есть оба вызова — это одно чтение `User` плюс одно поле, и это **тот же** `User`, который блоку и так нужен для `cushion_target`. Рекомендация критика применима буквально:

```python
user = self.session.get(User, user_id)
if user is None:
    return _empty_goals()          # CardStatus.EMPTY, ни одной цифры
monthly_budget  = user.monthly_savings_budget
savings_mode    = user.savings_mode
cushion_target  = user.cushion_target
```

Три следствия: (а) «нет пользователя» — пустота, а не сбой, симметрично `_user_data_markers` (`money_layers_service.py:812-830`, докстринг: «на отсутствующем пользователе — `(0, False)`: чистая база штатна»); (б) из стратегии загрузки уходят **два** вызова (`get_savings_budget`, `get_savings_mode`) — побочный выигрыш, названный критиком; (в) `ValidationError` в этом пути неоткуда взяться, поэтому отдельной ветви `except ValidationError` перед общим `except` не нужно — общий `except` остаётся ловить реальные сбои (`GoalService.get_all_by_user`, `AllocationService`).

Что проверит тест AC-5, чтобы не оказаться подкрученным: **две фикстуры** пустой базы — с `User(id=1)` (как в проде после бутстрапа Epic-09 фазы 1) и **без** пользователя (самый естественный способ написать «пустая база»). В обоих ожидается пять `EMPTY`. Плюс отдельный ассерт «в логах нет трейсбека по блоку `goals`» — без него тест можно было бы подкрутить под `FAILED` незаметно.

**4. `[факт]` Как приёмник `calendar-focus-date` отличает «пришёл новый фокус» от «Store сохранил прошлое значение, а колбэк сработал по другому Input'у»?**

Двумя условиями, оба обязательны. Прочитан `load_and_navigate_calendar` (`calendar.py:758-947`): Input'ов пять — `url.pathname`, `prev-month-btn`, `next-month-btn`, `today-btn`, `wishlist-active-item`; `State("calendar-state")`; первой строкой guard `if pathname != "/calendar": raise PreventUpdate` (`:800`); `triggered_id = ctx.triggered_id` **уже используется** для выбора ветки навигации (`:815-825`); возвращаемый `new_state` = `{"current_month", "current_year", "balances"}` (`:926-930`).

1. **`ctx.triggered_id == "calendar-focus-date"`.** Без этого «ушёл в Операции, вернулся в Календарь по меню» переприменяло бы прошлый фокус: колбэк срабатывает по `url.pathname`, а Store хранит значение до перезагрузки страницы (layout между переходами не пересоздаётся). Тот же эффект давало бы любое нажатие «вперёд/назад/сегодня».
2. **`payload["ts"] != state.get("focus_applied_ts")`.** Защита от повторного применения того же события (F5, повторная отправка колбэка). Применив фокус, кладём `ts` в `calendar-state` рядом с `current_month`/`current_year`/`balances` — словарь состояния уже есть и уже возвращается, новых Store'ов не нужно; ключ `focus_date` v2 туда и так добавляла.

Поэтому payload новых Store'ов — **словарь** `{"value": <ISO | goal_id>, "ts": <int мс>}`, а не скаляр: `ts` нужен и для «два клика подряд по «завтра» срабатывают дважды», и как ключ идемпотентности. Механика описана **одним абзацем и применена дважды** — тот же текст для `goals-focus-goal` в `apply_goal_focus`, где роль `calendar-state` играет собственный Store состояния фокуса. Юнит-тестом «ушёл и вернулся» не ловится (нужен реальный порядок срабатываний), поэтому добавлен ручной пункт шага 13 с полным сценарием: дашборд → «завтра» → пролистать на октябрь → уйти в «Операции» → вернуться по меню → **октябрь остался**.

**5. `[решение]` Цифра карточки «Аналитика» заметно меньше месячного слоя «Платежи» — объявляем расхождение или заводим отдельный протокол?**

Принятое решение (обсуждению не подлежит): **объявить расхождение, сервис не менять.** Цитата решения владельца: цифра карточки считается тем же сервисом, что и раздел «Аналитика» — это правильно и сохраняется; расхождение с месячным слоем «Платежи» графика объявляется явно — докстринг `AnalyticsCardData`, подпись/пояснение в карточке, строка в RTM; оформить симметрично уже принятому ограничению карточки «Операции» (решение владельца 2026-08-25); правка `AnalyticsService` запрещена C-3, **отдельный протокол по семантике «расходов месяца» в этом куске не заводится**.

Реализация. Причины расхождения выведены из тела `get_expenses_by_category` (`analytics_service.py:85-100`), где фильтр — `transaction_type == TransactionType.EXPENSE` **и** `is_recurring == False`: (а) виртуальные инстансы регулярных платежей в цифру не входят, а в слой «Платежи» входят (модель считает их через `CalendarService`); (б) `savings_reserve` / `savings_contribution` / отрицательные `adjustment` в цифру не входят, а в слой входят (`_PAYMENT_TYPES` + ветка `adjustment`, `money_layers_service.py:397-402`). Обе цифры корректны в своей семантике; болезнью было именно **необъявленное** расхождение (FR-6, P1-боль аудита).

Три места объявления, симметрично карточке «Операции»: докстринг `AnalyticsCardData` (обе причины со ссылками на тела), подпись под цифрой в карточке — «расходы августа · без регулярных и взносов в цели» (`.pnl-note`, мелкий кегль), строка RTM #87. Тест на наличие подписи в дереве (шаг 10) + ручная сверка с разделом «Аналитика» за тот же месяц (проверка 13). Риск R16.

**6. `[решение]` Сессия на построение сайдбара при каждом переходе — приемлемая цена или предпочтительнее иной способ доставки профиля?**

Принятое решение (обсуждению не подлежит): **приемлемая цена, Подход B критика.** Цитата: одна сессия на построение сайдбара при переходе между разделами приемлема — на дашборде её нет вовсе, бюджет NFR-1 (2 с против десятков мс) не задет, а взамен у сайдбара не остаётся ни одного Output на условно присутствующий элемент. Реализовать `render_sidebar_slot(pathname, profile_updated)` — один колбэк, два Input'а на всегда присутствующие элементы (`url` + Store `profile-updated`), внутри одно чтение профиля, `create_sidebar(pathname, profile)` — чистая функция. Колбэки `highlight_active_sidebar` **и** `update_sidebar_profile` удаляются **ОБА**. Сессию сайдбара внести в «Стратегию загрузки» явно.

Реализация — см. ответ на вопрос 2 и шаг 8 плана. Что сделано по последнему требованию буквально: в докстринге `DashboardPanelService` появился **отдельный абзац** «Сессия сайдбара (Подход B, блокер №2) — учтена явно» с разбивкой по страницам (0 на `/dashboard`; 1 сессия + 1 SELECT User на переход между четырьмя разделами; та же сессия при правке профиля), а в шаге 12 — **отдельный замер** `render_sidebar_slot("/calendar", None)` в протокол, рядом со замером щитка. Итог по числу колбэков: минус два (`highlight_active_sidebar`, `update_sidebar_profile`), плюс один (`render_sidebar_slot`) — на один колбэк меньше, чем сегодня, и на два условно присутствующих Output'а меньше, чем в v2.
