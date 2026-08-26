# Solution v2: `PanelData` за одну сессию + карточки-двери на `dcc.Link`, «вчера» отдельным полем

## Обзор решения

Версия 2 сохраняет удачный скелет v1 (единый композитор, `dcc.Link` вместо серверных колбэков, поблочная деградация) и меняет четыре вещи по критике и решениям владельца:

1. **«Вчера» — новое поле, а не новое окно (Подход A критика, решение владельца).** `MoneyLayersData.days` сохраняет форму и смысл куска 1: ровно `WINDOW_DAYS` дней от `reference_date`. Добавляется единственное новое поле `yesterday: DayLayers | None`, посчитанное **тем же** `_split_day` из баланса за `ref-1`, полученного **тем же** вызовом `_forecast_balances` с расширенной ЛЕВОЙ границей. `window_days()`-хелпер выброшен целиком. График, `_axis_tickvals`, `min_free`/`min_free_date`, `_today_slice`, `_is_empty`, 47 тестов визуального слоя — не трогаются вообще; C-7 держится тривиально, шаг «адаптация 47 тестов» из плана исчезает.

2. **Владение `url.search` — контракт по pathname.** Расширенный `handle_panel_query_params` чистит `search` **только** для путей, чьи параметры разобрал сам (`/calendar`, `/goals`). На `/transactions` он бросает `PreventUpdate` — `search` остаётся разделу, `apply_url_date_filter` (протокол 0023) работает как сегодня. Контракт зафиксирован в докстринге, в RTM и в списке ручных проверок.

3. **Каждая карточка честна сама за себя (решение владельца).** Единственный источник правды отрисовки карточки — её собственный `CardStatus`. Поле `is_new_user` из `PanelData` **убрано** — двух источников правды больше нет. Тест на смешанный случай (`layers['is_empty'] == True` + непустой блок Цели → карточка Цели показывает цифры) входит в обязательный набор.

4. **Стратегия загрузки пересчитана по фактическим вызовам, дубли названы и один из них устранён.** Карточка «Цели» **не вызывает** `CushionService.get_settings` (самый дорогой вызов из четырёх блоков: `_get_user` + `_get_current_balance` → `CalendarService.get_balance_on_date`, полный обход recurring-истории). Прогресс подушки считается из уже посчитанных `layers['cushion_threshold']`, `layers['today']['balance']` и одного дешёвого чтения `User.cushion_target` — второй расчёт баланса ради процента подушки был бы ровно тем дублем, от которого лечит FR-6. Дубль `GoalService.get_all_by_user` остаётся осознанно (identity map, C-3) и назван. В замер добавляется счётчик SQL-запросов, не только время.

Плюс исправления: `Input("open-wishlist-modal-btn")` удаляется вместе с элементом; `DIP_STRONG_THRESHOLD` убрана; один механизм скрытия колонки сайдбара; контракт материализации ORM в докстринге + тест после закрытия сессии; `highlight_active_sidebar` переводится на условный рендер вместо guard'а.

## Архитектура

### Компоненты

**Сервисный слой (новое)**

| Компонент | Файл | Роль |
|---|---|---|
| `DashboardPanelService` | `app/services/panel_service.py` (новый, ~340 строк) | Read-only композитор: одна сессия, один `PanelData`. Знает `MoneyLayersService`, `GoalService`, `AllocationService`, `DashboardService`, `AnalyticsService`, `WishlistService`. **Не знает** `CushionService` — прогресс подушки выводится из `layers` (см. «Стратегия загрузки»). О Dash не знает (C-2). |
| схемы карточек | `app/schema/panel.py` (новый, ~200 строк) | `PanelData`, `CalendarCardData`, `GoalsCardData`, `OperationsCardData`, `AnalyticsCardData`, `WishlistCardData`, `CardStatus`. Без `is_new_user`, без `DIP_STRONG_THRESHOLD`. |
| расширение модели слоёв | `app/schema/money_layers.py`, `app/services/money_layers_service.py` | ОДНО новое поле `yesterday: DayLayers \| None`. `days`, `today`, `min_free`, `is_empty`, `window_is_flat` — без изменений. |

**Презентационный слой** — как в v1, кроме `sidebar.py`:

| Компонент | Файл | Роль |
|---|---|---|
| ряд дверей + build-функции | `app/components/panel_cards.py` (новый, ~620 строк) | `build_cards_row(PanelData)` + чистые `build_*_card(...)`. Без БД, тестируются словарями. |
| щиток | `app/components/dashboard.py` | Layout без split-таблиц/подушки/wishlist-виджета; `_load_dashboard_components` → 3 Output'а; один новый clientside-триггер. |
| каркас | `app/main.py` | Сайдбар рендерится колбэком по `pathname`; расширенный разбор query params с контрактом владения `search`; два новых Store'а. |
| приёмники контекста | `app/components/calendar.py`, `app/components/goals.py` | Минимальные Input'ы на новые Store'ы (C-1). |
| стили | `app/assets/panel.css`, `custom.css`, `sidebar.css`, `calendar.css` | Секции `.pnl-slots`/`.pnl-door*`/`.pnl-wish*`; снятие `.db-*` раскладки 8/4. |

### Диаграмма взаимодействия

```
Открытие /dashboard
  url.pathname ──► load_dashboard_data (dashboard.py)
                     │
                     └─ _load_dashboard_components()
                          with get_db_session() as session:      ← ОДНА сессия
                            DashboardPanelService(session).get_panel_data(uid)
                              ├─ MoneyLayersService.get_money_layers()   (сбой НЕ глотаем)
                              │    └─ внутри: _forecast_balances(ref-1 .. window_end)
                              │       days = [ref .. ref+44]   ← ФОРМА НЕ МЕНЯЕТСЯ
                              │       yesterday = _split_day(balances[ref-1], …)  ← НОВОЕ
                              ├─ try: _goals_block()      GoalService + Allocation + layers
                              ├─ try: _operations_block()  DashboardService (recent/upcoming)
                              ├─ try: _analytics_block()   AnalyticsService.get_expenses_by_category
                              └─ try: _wishlist_block()    WishlistService.get_focus + to_data
                          → PanelData: ТОЛЬКО Decimal/date/str/bool/int
                            (ORM за пределы блока не выходит — контракт материализации)
                     │
                     ├─► build_free_header(data["layers"], profile)  (кусок 1, 0 правок)
                     ├─► build_layers_chart(data["layers"])          (кусок 1, 0 правок,
                     │                                                читает data["days"])
                     └─► build_cards_row(data)  →  5 × <дверь>

Клик по элементу двери
  «вчера»/«сегодня»/«завтра» ─ dcc.Link href="/calendar?focus_date=<ISO>"
  маркер просадки            ─ dcc.Link href="/calendar?focus_date=<dip ISO>"
  цель                       ─ dcc.Link href="/goals?goal=7"
  группа операций            ─ dcc.Link href="/transactions?start=…&end=…"
  «Аналитика»                ─ dcc.Link href="/analytics"
  тело/заголовок Wishlist    ─ clientside → Store open-wishlist-trigger → wishlist.py
  конкретная хотелка         ─ dcc.Link href="/calendar?wishlist_item=3"  (механизм 0023)

Приёмники (main.py handle_panel_query_params) — ВЛАДЕНИЕ url.search ПО PATHNAME
  /calendar  : разбирает open_recon | wishlist_item | focus_date → ЧИСТИТ search
  /goals     : разбирает goal                                    → ЧИСТИТ search
  /transactions : PreventUpdate — search принадлежит разделу (apply_url_date_filter, 0023)
  прочее     : PreventUpdate
```

## Файловая структура

```
app/
  schema/
    panel.py                    NEW  — TypedDict-контракты карточек
    money_layers.py             MOD  — ОДНО поле yesterday (форма days не меняется)
    __init__.py                 MOD  — реэкспорт схем панели
  services/
    panel_service.py            NEW  — DashboardPanelService
    money_layers_service.py     MOD  — левая граница _forecast_balances/_horizons + yesterday
    __init__.py                 MOD  — экспорт DashboardPanelService
  components/
    panel_cards.py              NEW  — build_*_card, build_cards_row
    dashboard.py                MOD  — layout/колбэки/один clientside-триггер
    sidebar.py                  MOD  — clientside-триггер профиля; highlight_active_sidebar
                                       переносится внутрь create_sidebar (см. Q2)
    calendar.py                 MOD  — приёмник calendar-focus-date
    goals.py                    MOD  — приёмник goals-focus-goal + anchor-id карточек
    wishlist.py                 MOD  — build_wishlist_widget удаляется ВМЕСТЕ с его Input'ом
    profile_modal.py            MOD  — единственный вход открытия — Store
    __init__.py                 MOD  — экспорты (снятие build_wishlist_widget)
  main.py                       MOD  — сайдбар колбэком, query params, Store'ы
  assets/
    panel.css                   MOD  — .pnl-slots / .pnl-door* / .pnl-wish*
    custom.css                  MOD  — снятие .db-* раскладки 8/4
    sidebar.css                 MOD  — ОДИН механизм скрытия колонки (см. №9)
    calendar.css                MOD  — .calendar-day-focused
tests/
  test_panel_cards_ui.py        NEW  — визуальный слой карточек (стиль 0029)
  test_panel_service.py         NEW  — сборка PanelData, деградация, материализация,
                                       смешанный случай пустоты, счётчик запросов
  test_money_layers_service.py  MOD  — ТОЛЬКО добавление: yesterday != 0 на истории,
                                       yesterday на 1-м числе, days НЕ изменились
  test_dashboard_callbacks.py   MOD  — 5 Output'ов → 3
  test_profile_modal_callbacks.py MOD — вход через Store
  test_dashboard_panel_ui.py    БЕЗ ПРАВОК ← отличие v2 от v1
```

## Ключевые интерфейсы

### Сервис-композитор

```python
# app/services/panel_service.py
class DashboardPanelService:
    """Read-only композитор данных щитка (EPIC-11, кусок 2, FR-6).

    Собирает ВСЕ данные дашборда за один вызов и одну сессию:
    модель слоёв + четыре блока карточек. Ни один существующий
    сервис не меняется — только композиция (C-3). В БД не пишет,
    о Dash не знает (C-2).

    КОНТРАКТ МАТЕРИАЛИЗАЦИИ (критика v1, №5 — обязателен к соблюдению):
        Каждый блок обязан вернуть ТОЛЬКО примитивы —
        Decimal / date / str / bool / int / их списки и словари.
        Обращение к ORM-атрибутам (включая вычисляемые property
        вроде Goal.progress_percentage и связи вроде
        WishlistItem.category_rel) выполняется ВНУТРИ открытой
        сессии, внутри тела блока. ORM-объект за пределы блока
        НЕ ВЫХОДИТ никогда.
        Почему это правило, а не пожелание: GoalService.get_all_by_user
        возвращает list[Goal], WishlistService.get_focus —
        list[WishlistItem]; WishlistService.to_data внутри читает
        item.category_rel (wishlist_service.py:308-312), то есть
        безопасен только внутри сессии и при не-eager загрузке даёт
        по запросу на элемент. PanelData живёт ДОЛЬШЕ сессии
        (build_*_card вызываются после выхода из with), поэтому
        любая утечка ORM даёт DetachedInstanceError в проде,
        невидимый в тестах карточек (они кормятся словарями).
        Проверяется тестом, который читает ВСЕ поля PanelData
        после закрытия сессии (test_panel_service.py).

    СТРАТЕГИЯ ЗАГРУЗКИ (FR-6, NFR-1) — посчитана по фактическим вызовам,
    а не по прикидке (критика v1, №6):

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
          _goals_block     — GoalService.get_all_by_user(ACTIVE)  [ДУБЛЬ п.5,
                             из identity map, см. ниже]
                           + GoalService.get_savings_budget  (session.get(User),
                             identity map)
                           + GoalService.get_savings_mode    (то же)
                           + AllocationService.calculate_allocation (0 запросов,
                             чистый расчёт)
                           + подушка БЕЗ запросов баланса, см. ниже
          _operations_block— 2 запроса с LIMIT
          _analytics_block — 1 GROUP BY по текущему месяцу
          _wishlist_block  — 1 запрос с LIMIT 5 + to_data на элемент
                             (category_rel; при отсутствии eager-загрузки —
                             до 5 коротких SELECT Category, все из одной сессии)

        Итого куском 2 добавляется: 4-9 коротких запросов (не «~7»),
        ноль дополнительных расчётов баланса, ноль вызовов Plotly.
        Сессий за рендер: 1 (было 4 — слои+профиль, подушка readonly,
        wishlist-виджет, каждый со своим get_db_session).

    ДУБЛИ С МОДЕЛЬЮ СЛОЁВ — названы и решены осознанно:
        * GoalService.get_all_by_user(ACTIVE) вызывается и в
          _goal_milestones модели (money_layers_service.py:723), и в
          _goals_block. Дубль ОСТАВЛЕН: milestones содержат только
          goal_id/name/target_date/target_amount/progress_percent,
          отфильтрованы условием target_date >= ref и обрезаны до
          MAX_MILESTONES_IN_WINDOW + 1 — карточке нужны current_amount,
          полный список активных целей и порядок по priority, чего в
          milestones нет. Второй вызов идёт в ту же сессию: объекты
          Goal берутся из identity map, повторного SELECT по идентичности
          может и не быть, но даже полный повтор — один короткий запрос.
          Читать milestones вместо целей = молча сузить карточку
          до целей с будущей датой; это дороже одного SELECT.
        * CushionService.get_settings НЕ вызывается вовсе (в v1 вызывался).
          Это самый дорогой вызов из всех четырёх блоков: помимо
          _get_user он делает _get_current_balance →
          CalendarService.get_balance_on_date(user, today), а тот
          обходит всю recurring-историю от самого раннего шаблона
          (задокументировано в докстринге get_threshold_amount,
          cushion_service.py:94-101). Второй расчёт баланса ради
          процента подушки — ровно тот дубль, от которого лечит FR-6.
          Вместо него _goals_block берёт:
            target    — одно чтение User.cushion_target (identity map);
            threshold — layers["cushion_threshold"] (уже посчитан
                        моделью, money_layers_service.py:153);
            current   — layers["today"]["balance"] (остаток сегодня,
                        уже посчитан тем же CalendarService).
          Побочный выигрыш: цифра подушки в карточке приходит из того
          же источника, что шапка и график, — расхождение невозможно
          по построению (FR-6), а get_settings давал ВТОРОЙ источник
          остатка. Расхождение семантики названо честно: get_settings
          считает current как balance_on_date(today) через
          _calculate_balance_before_date, модель — через
          calculate_daily_balances; оба идут в CalendarService и на
          «сегодня» совпадают, тест сравнивает их на фикстуре.

    КЕША НЕТ намеренно: единственный источник инвалидации —
    global-transaction-trigger, а он уже перерисовывает щиток
    целиком. Кеш добавил бы риск показать устаревшие цифры
    (P1-боль «цифры противоречат друг другу») без выигрыша
    в бюджете NFR-1.
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

    # --- блоки; каждый (кроме календарного) под своим try/except ---
    def _calendar_block(self, layers: MoneyLayersData) -> CalendarCardData: ...
    def _goals_block(self, user_id: int, layers: MoneyLayersData) -> GoalsCardData: ...
    def _operations_block(self, user_id: int, ref: date) -> OperationsCardData: ...
    def _analytics_block(self, user_id: int, ref: date) -> AnalyticsCardData: ...
    def _wishlist_block(self, user_id: int) -> WishlistCardData: ...
```

`_calendar_block` — чистая функция от уже посчитанной `MoneyLayersData`, **без единого запроса**: это и есть механическая гарантия AC-3. `_goals_block` принимает `layers` именно для того, чтобы не звать `CushionService`.

### Расширение модели слоёв (C-5) — аккуратный вариант

Полный, исчерпывающий перечень правок в `money_layers_service.py` / `money_layers.py`. Всё, чего в перечне нет, **не трогается**.

```python
# app/schema/money_layers.py
WINDOW_LOOKBACK_DAYS = 1
"""Сколько дней ДО reference_date модель считает ДОПОЛНИТЕЛЬНО к окну.

ВАЖНО: это НЕ расширение окна. days остаётся ровно WINDOW_DAYS дней
от reference_date — форма и смысл контракта куска 1 не меняются
(решение владельца 2026-08-25, «аккуратный вариант»). Константа
управляет ТОЛЬКО левой границей расчёта балансов и сбора операций,
из которой считается отдельное поле yesterday.

Почему так, а не сдвигом окна: days читают график
(dashboard.py:502/510/513), фикстуры и 47 тестов визуального слоя
щитка (протокол 0029). Смена смысла days задела бы _axis_tickvals
(только что чинённый от пробития MAX_X_TICKS), min_free, _today_slice
и _is_empty. Добавление поля не читает никто, кроме нового кода
куска 2 — blast radius куска 1 равен нулю (C-7).
"""

class MoneyLayersData(TypedDict):
    days: list[DayLayers]        # БЕЗ ИЗМЕНЕНИЙ: [ref .. ref+44], len == WINDOW_DAYS
    yesterday: DayLayers | None  # NEW и единственное новое поле
    # ... все остальные поля БЕЗ ИЗМЕНЕНИЙ
```

Докстринг нового поля:

```python
        yesterday: Слои за reference_date - WINDOW_LOOKBACK_DAYS, посчитанные
            ТЕМ ЖЕ _split_day из ТОГО ЖЕ вызова расчёта балансов —
            нужны карточке «Календарь» (FR-1.a: вчера/сегодня/завтра).
            None, если день не попал в расчёт балансов (не должно
            случаться при корректных границах — см. _horizons; None
            рисуется в карточке прочерком, а не нулём: числовой
            артефакт «Вчера — 0 ₽» на наполненной базе противоречил
            бы AC-3/AC-5).
            В days НЕ входит и на ось графика НЕ попадает.
```

**Явный перечень границ (критика v1, №3 — самый опасный пункт):**

| Место | Было | Стало | Зачем |
|---|---|---|---|
| `_horizons.collect_start` (`:266`) | `_month_start(ref)` | `min(_month_start(ref), ref - WINDOW_LOOKBACK_DAYS)` | 1-го числа «вчера» = последний день прошлого месяца; иначе его операции не собраны |
| `_forecast_balances(...)` (вызов `:138`) | `(user_id, ref, window_end)` | `(user_id, ref - WINDOW_LOOKBACK_DAYS, window_end)` | **без этого `balances.get(ref-1)` вернёт дефолт `Decimal("0")` — «Вчера — 0 ₽» на наполненной базе; инварианты при этом держатся (0 = 0+0+0), тесты не краснеют, дефект ловится только целевым тестом** |
| `_horizons.window_end` | `ref + WINDOW_DAYS - 1` | **без изменений** | правая граница оси не меняется |
| `_horizons.payments_end` | `_month_end(ref)` | **без изменений** | горизонт платежей — решение куска 1 (C-5) |
| `window_dates` (`:135`) | `[ref + d for d in range(WINDOW_DAYS)]` | **без изменений** | форма `days` — контракт куска 1 |
| `_payments_tail_by_day` / `_goals_part_by_day` | `window_dates` | **без изменений** | для `yesterday` считаются точечно, см. ниже |
| `_today_slice` (`:664`) | `days[0]` | **без изменений** | `days[0] == ref` по-прежнему верно |
| `_window_min_free` / `min_free`, `min_free_date` | по всему `days` | **без изменений** | «вчера» в `days` не попадает, маркер графика не может уехать (R3 v1 снят конструктивно) |
| `_is_empty` (`:810`) | `all(day["forecast_balance"] == 0 for day in days)` | **без изменений** | `days` не изменился → семантика пустоты не переворачивается (критика №3, п.3 снят конструктивно) |
| `window_is_flat` | от `payments`/`savings_by_date` | **без изменений** | `payments` фильтруется `day >= reference_date` (`:402`) — «вчера» в него не попадает; `savings_by_date` по всему собранному материалу уже сегодня включает прошедшие дни месяца, поэтому расширение `collect_start` на 1 день (только на стыке месяцев) не меняет ни `window_is_flat`, ни формулу резерва: `_goals_part_by_day` фильтрует по `[month_start(D), month_end(D)]` внутри себя |
| `window_days()`-хелпер v1 | планировался | **не создаётся** | не нужен (решение владельца) |

Расчёт `yesterday` — три строки того же каскада, точечно:

```python
# app/services/money_layers_service.py
    def _yesterday_slice(
        self,
        balances: dict[date, Decimal],
        payments: list[UpcomingPayment],
        savings_by_date: dict[date, Decimal],
        monthly_budget: Decimal,
        cushion_threshold: Decimal,
        ref: date,
        payments_end: date,
    ) -> DayLayers | None:
        """Слои за ref - WINDOW_LOOKBACK_DAYS — вне цикла по days.

        Считается ТЕМ ЖЕ _split_day и ТЕМИ ЖЕ формулами, что дни окна:
        расхождение способа счёта между «вчера» и «сегодня» было бы
        новым источником противоречащих цифр (FR-6, P1-боль аудита).

        Почему вне цикла: days сохраняет форму контракта куска 1
        (решение владельца, «аккуратный вариант»). Цена — одно
        точечное применение каскада; выигрыш — нулевой blast radius
        куска 1 (C-7).

        Returns:
            DayLayers | None: None, если balances не содержит дня
                (границы расчёта нарушены) — карточка нарисует
                прочерк, а не 0 ₽.
        """
        yday = ref - WINDOW_LOOKBACK_DAYS_TD
        if yday not in balances:
            logger.warning(
                f"Баланс за {yday} отсутствует в расчёте (user-facing «вчера» "
                "будет прочерком) — проверить левую границу _forecast_balances"
            )
            return None

        day_payments = self._payments_tail_by_day([yday], payments, payments_end)  # точечно
        goals_part = self._goals_part_by_day(savings_by_date, [yday], monthly_budget)
        reserve_configured = cushion_threshold + goals_part.get(yday, Decimal("0"))
        free, fact_payments, fact_reserve = self._split_day(
            balances[yday], day_payments.get(yday, Decimal("0")), reserve_configured
        )
        return DayLayers(
            date=yday, free=free, payments=fact_payments, reserve=fact_reserve,
            reserve_configured=reserve_configured, forecast_balance=balances[yday],
        )
```

Обе вспомогательные функции (`_payments_tail_by_day`, `_goals_part_by_day`) уже принимают `window_dates: list[date]` — передача списка из одного дня их не меняет вообще (C-3 для внутренних хелперов соблюдён без правок их тел). Инвариант «сумма слоёв == остаток» для `yesterday` держится по построению: `_split_day` не меняется и сохраняет сумму во всех ветках; тест проверяет инвариант отдельно для `yesterday`.

### Владение `url.search` (блокер №1)

```python
# app/main.py
# Пути, чьи query params разбирает ЭТОТ колбэк и, следовательно,
# чей url.search он имеет право очистить.
_OWNED_SEARCH_PATHS = frozenset({"/calendar", "/goals"})
"""КОНТРАКТ ВЛАДЕНИЯ url.search (критика v1, блокер №1).

url.search — Input не только у этого колбэка. Второй читатель —
apply_url_date_filter (transactions.py:1470-1520): он читает
?start=&end= для /transactions, в search НЕ пишет и работает
с протокола 0023. Если бы этот колбэк чистил search на
/transactions, фильтр периода в разделе перестал бы применяться
(или применялся недетерминированно — гонка двух Output'ов на один
Input), то есть сломалась бы уже работающая дверь Операций.

Правило: чистим search ТОЛЬКО для путей, чьи параметры разобрали
сами. Для /transactions — PreventUpdate: search остаётся разделу.
Идемпотентность там обеспечена самим разделом — повторное
применение того же периода после F5 не наблюдаемо.
"""

@callback(
    [
        Output("open-recon-trigger", "data"),
        Output("wishlist-active-item", "data"),
        Output("calendar-focus-date", "data"),   # NEW
        Output("goals-focus-goal", "data"),      # NEW
        Output("url", "search"),
    ],
    Input("url", "search"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def handle_panel_query_params(url_search: str | None, pathname: str | None):
    """Разбирает query params дверей щитка и раскладывает по Store'ам.

    Расширение механизма протоколов 0023/0028, а не новый механизм
    (свидетельство поиска — memory/spec-context/epic-11.md):

      РАЗБИРАЕТ САМ и очищает search (_OWNED_SEARCH_PATHS):
        /calendar?open_recon=1      → open-recon-trigger    (было)
        /calendar?wishlist_item=ID  → wishlist-active-item  (было)
        /calendar?focus_date=ISO    → calendar-focus-date   (НОВОЕ, FR-3)
        /goals?goal=ID              → goals-focus-goal      (НОВОЕ, FR-3)

      НЕ ТРОГАЕТ (PreventUpdate, search принадлежит разделу):
        /transactions?start=&end=   → apply_url_date_filter (0023) — см.
                                      _OWNED_SEARCH_PATHS, блокер №1
        /analytics                  → params не нужны вовсе: раздел
                                      уже открывается на текущем месяце
                                      (analytics-period-store = "month")

    Значения-триггеры timestamp-обёрнуты: два клика подряд по «завтра»
    должны сработать дважды, а Store сравнивается по значению.
    Битые значения (?focus_date=abc, ?goal=x) игнорируются молча —
    не повод падать; если после разбора ни один параметр не распознан,
    PreventUpdate, и search сохраняется.
    """
    if not url_search or pathname not in _OWNED_SEARCH_PATHS:
        raise PreventUpdate
    # ... разбор; если ничего не распознали — PreventUpdate (search цел)
    return recon_trigger, wishlist_item, focus_date, focus_goal, ""
```

### Двери-переходы

Каркас и build-функции — как в v1 (`_door_shell`, `build_calendar_card`, `build_goals_card`, `build_operations_card`, `build_analytics_card`, `build_wishlist_card`, `build_cards_row`), с двумя правками докстрингов:

```python
def build_calendar_card(data: CalendarCardData) -> html.Div:
    """Карточка «Календарь»: вчера / сегодня / завтра + маркер просадки.

    Каждое окошко дня — dcc.Link на /calendar?focus_date=<ISO> (FR-3,
    AC-2). Маркер просадки показывается ВСЕГДА (день минимума слоя
    «Свободно» в окне модели), при dip_free <= 0 получает класс
    pnl-flagline-strong (AC-7): усиление привязано к факту знака
    числа — порога-вердикта нет и константы-порога тоже нет
    (решение владельца 2026-08-25; критика v1, №8).

    День без данных (yesterday is None) рисуется ПРОЧЕРКОМ, не нулём:
    «Вчера — 0 ₽» на наполненной базе — числовой артефакт, который
    неотличим от корректной работы (AC-3/AC-5).
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
    модели слоёв (starting_balance == 0 И нет шаблонов И нет операций
    И нулевые балансы окна), и пользователь с заведёнными целями
    при is_empty=True обязан видеть их прогресс, а не «щиток в режиме
    первого запуска» (риск: человек решит, что данные потерялись).
    """
```

### Store-триггеры и приёмники (C-6)

```python
# app/main.py — глобальные Store'ы (живут на ВСЕХ страницах)
dcc.Store(id="open-wishlist-trigger", data=None),   # NEW: дверь Wishlist, уровень 1
dcc.Store(id="calendar-focus-date", data=None),     # NEW: ?focus_date=
dcc.Store(id="goals-focus-goal", data=None),        # NEW: ?goal=
```

```python
# app/components/wishlist.py — ЕДИНСТВЕННЫЙ вход в модал (блокер №2)
@callback(
    [Output("wishlist-modal", "is_open", allow_duplicate=True),
     Output("wishlist-items-container", "children"),
     Output("wishlist-add-category", "options")],
    Input("open-wishlist-trigger", "data"),   # ЕДИНСТВЕННЫЙ Input открытия
    prevent_initial_call=True,
)
def open_wishlist_modal(door_trigger: float | None):
    """Открывает модал управления wishlist (AC-8, уровень 1 двери).

    ПРАВИЛО (критика v1, блокер №2 — обратная сторона C-6):
    УДАЛЯЕШЬ ЭЛЕМЕНТ — УДАЛЯЙ ЕГО INPUT. Прежний вход
    Input("open-wishlist-modal-btn", "n_clicks") УДАЛЁН вместе
    с build_wishlist_widget: элемент рождался только внутри виджета
    (wishlist.py:65), а виджет снят с дашборда карточкой Wishlist.
    Оставить Input «на будущее» нельзя: клиентский рендерер Dash
    молча не отправляет колбэк ЦЕЛИКОМ, если Input-элемента нет
    в DOM (patterns/callbacks.md) — а после удаления виджета его нет
    НИ НА ОДНОЙ странице, то есть колбэк был бы мёртв безусловно
    и модал стал бы недостижим вообще (второй его вход,
    wishlist-plan-btn, живёт внутри самого модала).

    Guard на пустой Store обязателен: Store — состояние, а не
    событие (layout Dash не пересоздаётся между страницами), иначе
    модал переоткрывался бы при каждой загрузке страницы после
    первого клика.

    Если виджет когда-нибудь вернётся — он подключится к тому же
    Store clientside-триггером, как шестерёнка щитка.
    """
    if not door_trigger:
        raise PreventUpdate
    ...
```

```python
# app/components/dashboard.py — единственный новый clientside-триггер
# Дверь Wishlist (заголовок/тело карточки) → модал управления (AC-8).
# Элемент рождается динамически внутри dashboard-cards-row и вне
# /dashboard в DOM отсутствует → прямой Input запрещён (C-6).
clientside_callback(
    ClientsideFunction("triggers", "timestamp_trigger"),
    Output("open-wishlist-trigger", "data", allow_duplicate=True),
    Input("panel-wishlist-door", "n_clicks"),
    prevent_initial_call=True,
)
```

### Сайдбар: снятие с дашборда (FR-2, AC-1, AC-9) + судьба `highlight_active_sidebar` (№10)

```python
# app/main.py
html.Div(id="sidebar-slot", className="sidebar-column"),

@callback(
    Output("sidebar-slot", "children"),
    Input("url", "pathname"),
)
def render_sidebar_slot(pathname: str | None):
    """Сайдбар есть на всех страницах, КРОМЕ дашборда (FR-2, AC-1).

    Возвращает [] на дашборде. Колонка скрывается ОДНИМ механизмом —
    CSS-правилом .sidebar-column:empty { display: none } (критика v1,
    №9: в v1 механизмов было два — className "d-none" и :empty; при
    двух правилах CSS обрастает дублями, чего Epic-10 как раз лечит).
    Поэтому className НЕ переключается и Output'а на него нет.

    ВАЖНО, класс регрессий C-6 «наоборот»: убирая сайдбар с дашборда,
    мы удаляем из DOM sidebar-profile-container — прямой Input
    колбэка handle_profile_modal (profile_modal.py:96). На /dashboard
    колбэк перестал бы отправляться ЦЕЛИКОМ, включая вход через
    шестерёнку → AC-9 красный. Поэтому вход через аватар сайдбара
    тоже переводится на Store open-profile-trigger, и
    handle_profile_modal не имеет ни одного Input на условно
    присутствующий элемент.

    Симметрично, по правилу «удаляешь элемент — удаляй его Input»
    (блокер №2), проверены ВСЕ колбэки, ссылающиеся на элементы
    сайдбара: highlight_active_sidebar (Output sidebar-nav) и
    update_sidebar_profile (Output sidebar-profile-name/avatar) —
    их судьба решена в sidebar.py.
    """
    is_dashboard = pathname in (None, "/", "/dashboard")
    return [] if is_dashboard else create_sidebar()
```

```python
# app/components/sidebar.py
def create_sidebar(pathname: str | None = None) -> dbc.Card:
    """Сайдбар. Активный пункт подсвечивается ПРИ ПОСТРОЕНИИ.

    Изменение куска 2 (критика v1, №10): колбэк
    highlight_active_sidebar УДАЛЁН, подсветка переехала в аргумент.

    Почему: раньше сайдбар был статическим узлом глобального layout
    (main.py:59) и жил на всех страницах, поэтому колбэк
    Output("sidebar-nav","children") ← Input("url","pathname") был
    корректен. После FR-2 сайдбар рендерится колбэком
    render_sidebar_slot по тому же Input("url","pathname"), и
    sidebar-nav на /dashboard в DOM отсутствует. Два колбэка на один
    Input, один из которых пишет в узел, который второй в этот же
    момент создаёт или удаляет, — гонка, а не «шум в логах» (в v1
    это было названо шумом и лечилось guard'ом; критика v1, №10
    справедливо это оспорила).
    Решение убирает гонку целиком: пункт «активен» вычисляется
    там же, где рождается сайдбар, одним колбэком по одному Input.
    Побочный выигрыш: минус один колбэк и минус один Output
    на условно присутствующий элемент.

    Args:
        pathname: Текущий путь для подсветки активного пункта;
            None → "/dashboard" (сохраняет прежнее поведение).
    """

# update_sidebar_profile ОСТАЁТСЯ, но его Output'ы тоже условно
# присутствуют → значение подставляется при построении (create_sidebar
# уже читает профиль), а колбэк оставляется ТОЛЬКО ради
# Input("profile-updated","data") с guard'ом на dashboard-pathname.
```

```python
# app/components/profile_modal.py — оба входа через Store (AC-9)
@callback(
    [...],
    [Input("open-profile-trigger", "data"),   # ЕДИНСТВЕННЫЙ вход открытия
     Input("profile-save-btn", "n_clicks"),
     Input("profile-cancel-btn", "n_clicks")],
    [...],
    prevent_initial_call=True,
)
def handle_profile_modal(profile_trigger, save_clicks, cancel_clicks, ...):
    """...
    Прямого Input на sidebar-profile-container БОЛЬШЕ НЕТ (правило
    «удаляешь элемент — удаляй его Input», блокер №2 критики v1):
    после снятия сайдбара с дашборда элемент отсутствует в DOM на
    /dashboard, и прямой Input отключил бы колбэк там целиком —
    включая вход через шестерёнку (AC-9). Оба входа (аватар сайдбара
    и шестерёнка щитка) пишут в один Store open-profile-trigger.
    """
```

## Модель данных

Изменения относительно v1 — три: убрано `is_new_user`, убрана `DIP_STRONG_THRESHOLD`, добавлено `yesterday` в модель слоёв. Остальное сохраняется.

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

# Константы DIP_STRONG_THRESHOLD НЕТ (критика v1, №8): имя содержало
# «THRESHOLD», а решение владельца прямо говорит, что порога здесь нет.
# Константа со значением 0, названная порогом, — приглашение следующему
# разработчику её «настроить». В коде — прямое `dip_free <= 0`
# с комментарием, что это факт знака числа, как красное «Свободно»
# в шапке куска 1.


class CardStatus(str, Enum):
    """Состояние блока карточки — ЕДИНСТВЕННЫЙ источник правды её отрисовки.

    OK      — данные есть, показываем цифры.
    EMPTY   — в ЭТОМ разделе данных нет: пустое состояние БЕЗ числовых
              артефактов, карточка остаётся (FR-2, FR-5, AC-5).
              Определяется ТОЛЬКО по данным собственного блока —
              «каждая карточка честна сама за себя» (решение владельца
              2026-08-25). Общего признака пустоты в PanelData нет.
    FAILED  — сбор блока упал; сбой залогирован
              logger.opt(exception=True), карточка деградирует
              с индикацией, дашборд жив (NFR-2).
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
            ['yesterday'], для «сегодня»/«завтра» — из days.
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
            layers['min_free_date']; маркер показывается ВСЕГДА
            (решение владельца «оба»).
        dip_free: Значение минимума (layers['min_free']).
        dip_is_strong: dip_free <= 0 — маркер визуально усилен (AC-7).
            Факт знака числа, не порог.
        dip_href: /calendar?focus_date=<dip_date ISO>.
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
    layers['cushion_threshold'], layers['today']['balance'] и одного
    чтения User.cushion_target (см. «Стратегия загрузки»): второй
    расчёт баланса ради процента был бы дублем, от которого лечит FR-6.

    Attributes:
        status, top_goal_id, top_goal_name, top_goal_progress,
        top_goal_current, top_goal_target, top_goal_target_date,
        top_goal_href, others_count, others_behind_count,
        others_summary («по плану» / «1 отстаёт», источник —
        AllocationResult['shortfall'] > 0),
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
    """Строка операции в карточке «Операции» (FR-1.c)."""
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
    в неё НЕ попадают: DashboardService.get_recent/get_upcoming
    их не отдаёт, а менять поведение сервиса запрещает C-3. Эскиз v3
    рисовал «Аренда 🔁» — этого не будет.
    Где регулярные видны: в календаре, в графике полос щитка и
    в тултипе легенды слоя «Платежи» (кусок 1). Флаг is_recurring
    остаётся: материализованные recurring-операции маркер получают.
    Ограничение зафиксировано здесь, в докстринге _operations_block
    и в документации (modules/ui-components.md), чтобы не выглядело
    недоделкой.

    Attributes:
        status, recent, upcoming (до OPERATIONS_PER_GROUP строк),
        recent_href / upcoming_href — те же диапазоны, по которым
        DashboardService отбирал строки (FR-6).
    """
    status: CardStatus
    recent: list[OperationRow]
    upcoming: list[OperationRow]
    recent_href: str
    upcoming_href: str


class AnalyticsCategorySlice(TypedDict):
    """Доля категории в мини-структуре карточки «Аналитика»."""
    name: str
    total: Decimal
    share: float
    color: str


class AnalyticsCardData(TypedDict):
    """Карточка «Аналитика» (FR-1.d): ТОЛЬКО расходы.

    Показателя «Доходы за месяц» здесь нет и не появится ни в каком
    виде — решение владельца 2026-08-25.
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
    безопасен ПОСЛЕ закрытия сессии (контракт материализации
    DashboardPanelService), проверяется целевым тестом.

    Поля is_new_user НЕТ (критика v1, №7; решение владельца
    2026-08-25): общего признака пустоты, влияющего на отрисовку
    карточек, в контракте не существует — иначе получались бы два
    источника правды для AC-5 и достижимое расхождение «пустой щиток
    с непустыми карточками». Каждая карточка честна сама за себя:
    единственный источник — <slot>["status"].

    Attributes:
        layers: Модель слоёв — источник шапки, графика И карточки
            «Календарь». Один вызов на рендер: расхождение цифр
            между шапкой, графиком и карточкой физически невозможно
            (AC-3, лечение P1-боли аудита).
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

## Обработка ошибок

| Уровень | Поведение | Идиома |
|---|---|---|
| `MoneyLayersService` (базовая модель остатка) | Исключение НЕ глотается — пробрасывается наружу, `load_dashboard_data` показывает единый alert. Без остатка щитка нет (правило куска 1). | существующее |
| Части модели слоёв (порог подушки, бюджет, вехи) | fail-open, `degraded=True`, оговорка в шапке — как в куске 1. | `logger.opt(exception=True).warning(...)` |
| `yesterday` не посчитан (нет дня в `balances`) | Не исключение: `yesterday = None`, `logger.warning` с указанием проверить левую границу. Карточка рисует прочерк, **не 0 ₽** — числовой артефакт неотличим от корректной работы (критика №3). | `logger.warning` |
| Блок карточки (`_goals_block`, `_operations_block`, `_analytics_block`, `_wishlist_block`) | `try/except Exception` вокруг каждого; `CardStatus.FAILED` + пустые поля. Карточка рисуется с текстом «Не удалось загрузить раздел», ссылка-дверь остаётся рабочей (находимость раздела не теряется — FR-2). Остальные четыре живы (NFR-2). | `logger.opt(exception=True).warning(f"Не удалось собрать блок «{name}» для user_id={uid} (карточка деградирует)")` |
| `_calendar_block` | Без try/except: чистая функция от уже валидной `MoneyLayersData`. Отсутствие дня — `has_data=False`, не ошибка. | — |
| ORM-детач (`DetachedInstanceError`) | Предотвращается контрактом, а не ловится: блок обязан вернуть примитивы. Проверяется тестом «читаем все поля `PanelData` после закрытия сессии». | — |
| `load_dashboard_data` целиком | Существующий `except Exception` → alert; число Output'ов 5 → 3. | `logger.opt(exception=True).error` |
| Разбор query params | `try/except (ValueError, IndexError)` на каждом параметре; битый `?focus_date=abc` игнорируется молча; `PreventUpdate` если не распознан ни один параметр (тогда `search` не затирается). | существующее |
| `exc_info=True` | Запрещён: loguru его молча игнорирует. В правимых файлах (`sidebar.py:184`, `profile_modal.py:143,159,163`) заменяется на `logger.opt(exception=True)` — попутный долг протокола 0027. | — |

## План реализации

Нумерация пересобрана: шаг 2 старого плана (адаптация 47 тестов визуального слоя под новую форму `days`) **исчез** — в аккуратном варианте `days` не меняется.

**Шаг 1. Модель слоёв: одно поле «вчера» (C-5) — фундамент AC-3.**
`app/schema/money_layers.py`: `WINDOW_LOOKBACK_DAYS` + поле `yesterday: DayLayers | None` с докстрингом «в `days` не входит, на ось не попадает». `money_layers_service.py`: левая граница `_forecast_balances(user_id, ref - WINDOW_LOOKBACK_DAYS, window_end)`; `_horizons.collect_start = min(_month_start(ref), ref - WINDOW_LOOKBACK_DAYS)`; новый `_yesterday_slice`. Больше в файле не меняется НИЧЕГО: `window_dates`, `days`, `_today_slice`, `_window_min_free`, `_is_empty`, `window_is_flat`, `_payments_tail_by_day`, `_goals_part_by_day`, `_split_day` — без правок (перечень границ выше — исчерпывающий).
Тесты (`test_money_layers_service.py`, только добавление):
1. `data["yesterday"]["forecast_balance"] != 0` на фикстуре с историей (**целевой тест на дефект «Вчера — 0 ₽»** — без него он неотличим от корректной работы);
2. инвариант `free + payments + reserve == forecast_balance` для `yesterday`;
3. `len(data["days"]) == WINDOW_DAYS` и `data["days"][0]["date"] == ref` — **регрессионный тест формы `days`**: если кто-то позже решит сдвинуть окно, тест покраснеет первым;
4. `min_free_date` не совпадает с `ref-1` даже когда «вчера» — глобальный минимум (маркер графика не может уехать);
5. `is_empty` на чистой базе остаётся `True` (семантика пустоты не тронута);
6. фикстура «сегодня = 1-е число месяца» через относительные даты: «вчера» видит операции прошлого месяца (`collect_start`).

**Шаг 2 (был 3). Контракты карточек.** `app/schema/panel.py` целиком + реэкспорт в `app/schema/__init__.py`. Контракт первым, чтобы тесты шага 4 писались от него. `is_new_user` и `DIP_STRONG_THRESHOLD` не создаются.

**Шаг 3 (был 4). `DashboardPanelService`.** `app/services/panel_service.py` + экспорт. Блоки:
- `_calendar_block(layers)` — чистая функция; «вчера» из `layers["yesterday"]` (или `has_data=False`), «сегодня»/«завтра» из `layers["days"][0]`/`[1]`;
- `_goals_block(user_id, layers)` — `GoalService.get_all_by_user(ACTIVE)` + `get_savings_budget` + `get_savings_mode` → `AllocationService.calculate_allocation` (без БД); подушка из `layers["cushion_threshold"]` + `layers["today"]["balance"]` + `User.cushion_target`, **без `CushionService.get_settings`**;
- `_operations_block` — `get_recent_transactions(limit=3)` + `get_upcoming_transactions(limit=3)`; докстринг с ограничением по регулярным операциям;
- `_analytics_block` — `AnalyticsService.get_expenses_by_category(user_id, month_start, month_end)` (одна агрегация; `month_total` = сумма её `total`);
- `_wishlist_block` — `WishlistService.get_focus(limit=5)` + `to_data` внутри сессии.
Докстринг класса содержит контракт материализации и пересчитанную стратегию загрузки с названными дублями.

**Шаг 4 (был 5). Тесты сервиса.** `tests/test_panel_service.py`:
- AC-3: `panel["calendar"]["days"][1]["balance"] == panel["layers"]["today"]["balance"] == panel["layers"]["days"][0]["forecast_balance"]`;
- «вчера»: `panel["calendar"]["days"][0]["balance"] == panel["layers"]["yesterday"]["forecast_balance"]`, `has_data=True`, значение != 0 на истории;
- **материализация**: собрать `PanelData` внутри `with`, выйти из сессии, затем прочитать ВСЕ поля всех пяти срезов, включая `goals`/`wishlist` — ловит `DetachedInstanceError`, которого не видит ни один тест внутри сессии и ни один тест карточек;
- деградация: `patch` падающего сервиса → один блок `FAILED`, остальные `OK`, дашборд собран;
- пустая база → все блоки `EMPTY`;
- **смешанный случай (критика №7)**: фикстура `layers["is_empty"] == True` + заведённая цель без взносов → `panel["goals"]["status"] == OK` с цифрами, `panel["operations"]["status"] == EMPTY`; и обратный: операции есть, целей нет;
- согласованность подушки: `cushion_progress`, посчитанный из `layers`, совпадает с `CushionService.get_settings(...)["progress"]` на той же фикстуре (доказывает, что отказ от дорогого вызова не изменил цифру);
- **счётчик запросов** (`sqlalchemy.event` на `before_cursor_execute`) + счётчик `get_money_layers` == 1: фиксирует потолок стратегии загрузки числом, а не временем (локальный SQLite время дублей скрывает, число — нет).

**Шаг 5 (был 6). Карточки-двери.** `app/components/panel_cards.py` + секции CSS в `panel.css` (`.pnl-slots` grid 4 + `.pnl-wish` полосой, `.pnl-door`, `.pnl-door-head`, `.pnl-days`, `.pnl-day`, `.pnl-day-today`, `.pnl-flagline`, `.pnl-flagline-strong`, `.pnl-bar`, `.pnl-bar-thin`, `.pnl-grp`, `.pnl-big-sum`, `.pnl-mini-slot`, `.pnl-wish*`). Вертикальный ритм карточки «Цели» выравнивается (`margin-top:auto` у строки подушки) — заметка vision-критика эскиза v3.

**Шаг 6 (был 7). Перестройка щитка.** `dashboard.py`: layout → шапка + график + `html.Div(id="dashboard-cards-row")`; удаляются `_build_transactions_split_table`, `_build_cushion_card_readonly`, `_build_empty_state`, импорты `build_wishlist_widget`/`CushionService`/`DashboardService`/`RecentTransaction`, четыре clientside-триггера пустых состояний таблиц; `_load_dashboard_components` → 3 значения через `DashboardPanelService`; оба колбэка → 3 Output'а; добавляется один clientside-триггер двери Wishlist. `custom.css`: снимаются `.db-left-col`, `.db-right-col`, `.db-main-row`, `.dashboard-split-table`. **`build_layers_chart` и `_axis_tickvals` не правятся** — читают `data["days"]`, форма которого не изменилась.

**Шаг 7 (был 7/8, разделён). Удаление wishlist-виджета вместе с его Input'ом (блокер №2).** `wishlist.py`: `build_wishlist_widget` и `_build_widget_item` удаляются; `open_wishlist_modal` получает **единственный** `Input("open-wishlist-trigger", "data")` + guard; `Input("open-wishlist-modal-btn", "n_clicks")` удаляется. `components/__init__.py`: снятие экспорта. Правило «удаляешь элемент — удаляй его Input» фиксируется в докстринге и идёт в `patterns/callbacks.md`.

**Шаг 8. Снятие сайдбара с дашборда + защита AC-9 + судьба колбэков сайдбара.** `main.py`: `sidebar-slot` + `render_sidebar_slot` (без Output'а на className). `profile_modal.py`: единственный вход открытия — `open-profile-trigger`. `sidebar.py`: `create_sidebar(pathname)`, колбэк `highlight_active_sidebar` **удаляется** (подсветка при построении), `update_sidebar_profile` — clientside-триггер профиля + guard на dashboard-pathname; `exc_info=True` → `logger.opt(exception=True)`. `sidebar.css`: **один** механизм — `.sidebar-column:empty { display: none }` (второй, `d-none`, не вводится).

**Шаг 9. Приёмники контекста (FR-3) с контрактом владения `url.search`.** `main.py`: `handle_panel_query_params` + `_OWNED_SEARCH_PATHS` + два Store'а. `calendar.py`: `Input("calendar-focus-date")` в существующий `load_and_navigate_calendar`, ключ `focus_date` в `calendar-state`, класс `calendar-day-focused` в `_build_day_cell`, стиль в `calendar.css`. `goals.py`: якорные id в `_build_goal_card`, узел `goals-focus-anchor`, колбэк `apply_goal_focus`. `transactions.py` и `analytics.py` — **без правок**: `apply_url_date_filter` (0023) и дефолт `analytics-period-store` уже покрывают AC-2, и колбэк `main.py` теперь их не трогает.

**Шаг 10. Тесты UI карточек.** `tests/test_panel_cards_ui.py` в стиле `test_dashboard_panel_ui.py` (хелперы `iter_tree`/`joined_text`/`find_by_id`, фикстуры-словари, относительные даты, БД нет): все пять карточек при любом статусе (FR-2/AC-5); пустые состояния без `₽`/`%`/нулей; AC-7 в двух фикстурах (минимум > 0 → нет `pnl-flagline-strong`; ≤ 0 → есть); «вчера» с `has_data=False` рисует прочерк, а не «0 ₽»; href'ы всех дверей (AC-2, AC-8); отсутствие слова «Доход» в дереве карточки Аналитика; отсутствие карточки подушки в ряду и наличие строки подушки внутри карточки Цели (AC-4); **смешанный случай пустоты на уровне UI**: `calendar=EMPTY` + `goals=OK` → пустое состояние только в календарной карточке.

**Шаг 11. Адаптация существующих тестов.** `test_dashboard_callbacks.py` — 5 Output'ов → 3, контракт декоратора; `test_profile_modal_callbacks.py` — вход через Store вместо `sidebar-profile-container`; тест на `handle_panel_query_params`: **`pathname="/transactions"` → `PreventUpdate`** (контрактная фиксация блокера №1), `/calendar` и `/goals` → Store'ы заполнены и `search == ""`. `tests/test_dashboard_panel_ui.py` — **правок не требует** (проверяется прогоном, не адаптацией).

**Шаг 12. Замер NFR-1 (время + запросы) и статика.** Замер как в куске 1 (`time.perf_counter` вокруг `_load_dashboard_components` на наполненной локальной базе) **плюс счётчик SQL-запросов через `sqlalchemy.event`**; и то, и другое в протокол, со сверкой с 13 мс куска 1. `black`, `flake8`, полный `pytest`.

**Шаг 13. Ручная проверка регрессий C-6 и владения `url.search`** (юнит-тестом не ловится, KB это прямо фиксирует): навигация дашборд → каждый раздел → обратно; профиль открывается шестерёнкой на дашборде и аватаром в каждом разделе; подсветка активного пункта сайдбара корректна во всех разделах (после удаления `highlight_active_sidebar`); модал wishlist открывается дверью; клик «вчера»/«сегодня»/«завтра»/маркер просадки/цель/группа операций/аналитика/хотелка; **«переход в Операции с периодом → фильтр применён; F5 → фильтр остался/переприменён без ошибки»**.

Порядок жёсткий: 1 → 3 (сервис читает `yesterday`), 2 → 3 → 4, 5 → 6, 6 → 7 → 8 (снятие сайдбара безопасно только после перестройки layout и удаления виджета), 9 после 8 (Store'ы объявляются той же правкой `main.py`), 10–13 замыкают.

## Зависимости

- Новых пакетов нет; версии не меняются (Dash 2.17.1, SQLAlchemy 2.0.23).
- Внутренние: `panel_service` → `MoneyLayersService`, `GoalService`, `AllocationService`, `DashboardService`, `AnalyticsService`, `WishlistService`. `CushionService` из зависимостей композитора **исключён** (порог берётся из модели слоёв). Все существуют, ни один не меняется (C-3).
- Схема БД не меняется, миграций нет (C-4).
- Тестовая инфраструктура: `sqlalchemy.event` для счётчика запросов (входит в SQLAlchemy, новой зависимости нет).

## Риски и mitigation

| # | Риск | Вероятность | Mitigation |
|---|---|---|---|
| R1 | **Снятие сайдбара ломает модал профиля на дашборде** (`sidebar-profile-container` — прямой Input, элемента больше нет в DOM) → AC-9 красный. Класс регрессий C-6 «наоборот». | Высокая, если не заметить | Шаг 8: оба входа на `open-profile-trigger`, ни одного Input на условно присутствующий элемент. Ручная проверка — шаг 13. |
| R2 | **Модал wishlist становится недостижим**: Input на удалённый `open-wishlist-modal-btn` убивает колбэк на всех страницах. | Высокая, если оставить Input «на будущее» | Шаг 7: Input удаляется вместе с элементом; единственный вход — Store. Правило записывается в `patterns/callbacks.md`. |
| R3 | **«Вчера» = 0 ₽ на наполненной базе**: левая граница `_forecast_balances` не покрывает `ref-1`, `balances.get` отдаёт дефолт `Decimal("0")`. Инварианты держатся (0=0+0+0), тесты зелёные, UI правдоподобен. | Средняя — **самый опасный тихий дефект** | Явный перечень границ (таблица выше) + целевой тест «`yesterday["forecast_balance"] != 0` на истории» + `None` вместо нуля при отсутствии дня (прочерк в UI виден сразу) + `logger.warning`. |
| R4 | **«Вчера» 1-го числа не видит операций прошлого месяца** (`collect_start = _month_start(ref)`). | Средняя (1 день в месяц) | `collect_start = min(_month_start(ref), ref - WINDOW_LOOKBACK_DAYS)`; тест на фикстуре «сегодня = 1-е число» через относительные даты. |
| R5 | **Регрессия куска 1 при правке модели слоёв** (C-7). | **Низкая в v2** (была средней в v1) | Форма `days` не меняется вообще → график, `_axis_tickvals`, `min_free`, `_today_slice`, `_is_empty`, `window_is_flat` и 47 тестов не затронуты. Плюс регрессионный тест формы `days` (шаг 1, п. 3). |
| R6 | **Гонка за `url.search`** ломает уже работающую дверь Операций (протокол 0023). | Высокая, если чистить search для всех путей | `_OWNED_SEARCH_PATHS = {"/calendar", "/goals"}`; на `/transactions` — `PreventUpdate`. Контрактный тест (шаг 11) + ручная проверка «период + F5» (шаг 13). |
| R7 | **Деградация NFR-1.** По фактическим вызовам кусок 2 добавляет 4-9 коротких запросов (см. стратегию загрузки), ноль дополнительных расчётов баланса, ноль вызовов Plotly. Ожидание: с 13 мс до ~25-40 мс против бюджета 2 с. | Низкая | Замер шага 12 **со счётчиком запросов**; тест-счётчик `get_money_layers == 1`; отказ от `CushionService.get_settings` убирает самый дорогой вызов (полный обход recurring-истории). |
| R8 | **Кеш кажется нужным** и вносится «на всякий случай» → устаревшие цифры карточек против свежей шапки (та самая P1-боль). | Средняя | Решение зафиксировано в докстринге сервиса: кеша нет, инвалидация только через `global-transaction-trigger`. |
| R9 | **Дубль `GoalService.get_all_by_user`** между моделью слоёв и `_goals_block`. | Осознанно оставлен | Назван в докстринге стратегии загрузки с обоснованием (milestones не покрывают потребности карточки: нет `current_amount`, отфильтрованы по `target_date >= ref`, обрезаны до 4). Второй вызов идёт в ту же сессию → identity map. Счётчик запросов шага 12 делает цену видимой. |
| R10 | **`?focus_date` применяется повторно после F5** (Store хранит состояние). | Средняя | `url.search` очищается для владеемых путей; значение timestamp-обёрнуто; guard на пустой Store в приёмнике. Для `/transactions` идемпотентность обеспечивает сам раздел (повторное применение того же периода не наблюдаемо). |
| R11 | **`DetachedInstanceError` в проде на `_goals_block`/`_wishlist_block`**, невидимый в тестах (карточки кормятся словарями, сессия фикстуры живёт дольше прода). | Средняя | Контракт материализации в докстринге сервиса + тест, читающий все поля `PanelData` **после** закрытия сессии (шаг 4). Плюс: `to_data` вызывается внутри сессии — его обращение к `category_rel` (`wishlist_service.py:310-312`) безопасно. |
| R12 | **Удаление `highlight_active_sidebar` теряет подсветку активного пункта** в разделах. | Низкая | Подсветка переезжает в `create_sidebar(pathname)` — тот же `_build_nav_links(pathname)`, вызываемый на построении; `render_sidebar_slot` уже слушает `url.pathname`. Ручная проверка подсветки во всех четырёх разделах — шаг 13. |
| R13 | **Фокус цели требует переписать раздел** (карточки не имеют id) → нарушение C-1. | Низкая | Правка минимальна: якорный id в `_build_goal_card` + один невидимый узел + один колбэк; логика allocation/приоритетов не трогается. |
| R14 | **Ряд из 5 карточек не влезает в grid эскиза (4 колонки)**. | Средняя | Раскладка эскиза v3 воспроизводится буквально: 4 двери в `.pnl-slots`, Wishlist — `.pnl-wish` полосой под ними (FR-2 требует представительство, не равный размер). |
| R15 | **Расхождение семантики подушки** после отказа от `get_settings`: `current` берётся из модели слоёв, а не из `get_balance_on_date`. | Низкая | Оба значения идут в `CalendarService` и на «сегодня» должны совпадать; тест шага 4 сравнивает `cushion_progress` с `CushionService.get_settings(...)["progress"]` на фикстуре. Расхождение, если бы оно нашлось, — дефект `CalendarService`, а не карточки, и должно быть поймано, а не замаскировано вторым источником. |

## Requirements Traceability Matrix (RTM)

Строки #1-#78 сохраняются из v1 с правками, отмеченными **(v2)**; #79-#86 — новые (в том числе четыре, требуемые заданием: владение `url.search`, признак пустоты, контракт материализации, ограничение по регулярным операциям).

| # | Requirement (дословно) | Секция spec | Реализация в solution | Тип |
|---|---|---|---|---|
| 1 | «под шапкой и графиком видны карточки пяти предметных разделов» | AC-1, FR-1 | `build_cards_row(PanelData)` → 4 двери в `.pnl-slots` + `.pnl-wish`; `dashboard-cards-row` в layout | Visual |
| 2 | *Календарь*: «вчера / сегодня / завтра (остатки дней)» | FR-1 | **(v2)** `CalendarCardData.days` — 3 `CalendarDaySlice`; «вчера» из нового поля `layers["yesterday"]`, «сегодня»/«завтра» из `layers["days"][0]/[1]` | Visual |
| 3 | «маркер просадки — день минимума слоя «Свободно» окна модели» | FR-1 | `dip_date`/`dip_free` из `layers["min_free_date"]`/`["min_free"]` (не тронуты); `.pnl-flagline` всегда | Visual |
| 4 | «при минимуме ≤ 0 маркер визуально усиливается (факт знака числа, не порог-вердикт)» | FR-1, AC-7 | **(v2)** `dip_is_strong = dip_free <= 0` прямым сравнением, константы-«порога» нет (№8) | Edge |
| 5 | Календарь-дверь: «календарь на кликнутом дне» | FR-1, FR-3, AC-2 | `href=/calendar?focus_date=<ISO>` → `calendar-focus-date` → `load_and_navigate_calendar` + класс `calendar-day-focused` | Integration |
| 6 | *Цели*: «топ-цель с прогрессом» | FR-1, AC-4 | `top_goal_*`; `.pnl-bar`; материализовано внутри сессии | Visual |
| 7 | «сводка остальных (вида «по плану / 1 отстаёт»)» | FR-1, AC-4 | `others_count`, `others_behind_count`, `others_summary`; источник — `AllocationResult["shortfall"] > 0` | Visual |
| 8 | «статус подушки одной строкой + подушка живёт внутри этой карточки» | FR-1, AC-4 | **(v2)** `cushion_*` из `layers["cushion_threshold"]` + `layers["today"]["balance"]` + `User.cushion_target`, **без `get_settings`**; `_build_cushion_card_readonly` удалён | Visual |
| 9 | Цели-дверь: «цели с фокусом на кликнутой» | FR-1, FR-3, AC-2 | `top_goal_href=/goals?goal=<id>` → `goals-focus-goal` → `apply_goal_focus` + якорные id | Integration |
| 10 | *Операции*: «2-3 недавние + 2-3 предстоящие» | FR-1 | `OPERATIONS_PER_GROUP = 3`; `get_recent/upcoming_transactions(limit=3)` | Visual |
| 11 | Операции-дверь: «список операций с фильтром периода» | FR-1, FR-3, AC-2 | `recent_href`/`upcoming_href`; приёмник `apply_url_date_filter` (0023) **не ломается** — см. #79 | Integration |
| 12 | *Аналитика*: «цифра месяца — топ-категория расходов + мини-структура» | FR-1 | `month_total`, `top_category_*`, `structure`; `.pnl-big-sum`, `.pnl-mini-slot` | Visual |
| 13 | «Показатель «Доходы за месяц» НЕ возвращается» | FR-1, out of scope | `AnalyticsCardData` без поля доходов; только `get_expenses_by_category`; тест «слова «Доход» нет в дереве» | UX |
| 14 | Аналитика-дверь: «аналитика текущего месяца» | FR-1, AC-2 | `href="/analytics"`; дефолт `analytics-period-store`; раздел не правится (C-1) | Integration |
| 15 | *Wishlist*: «компактный виджет (представительство сохраняется)» | FR-1 | `.pnl-wish` полосой; в `MAIN_NAV_ITEMS` пункта нет | Visual |
| 16 | «Дверь двухуровневая: заголовок/тело → модал управления wishlist» | FR-1, AC-8 | **(v2)** `panel-wishlist-door` → clientside `timestamp_trigger` → `open-wishlist-trigger` → `open_wishlist_modal` с **единственным** Input'ом (блокер №2) | Integration |
| 17 | «клик по конкретной хотелке → календарь в режиме покупок с фокусом» | FR-1, AC-8 | `WishlistCardRow.href=/calendar?wishlist_item=<id>` → `wishlist-active-item` | Integration |
| 18 | *Настройки*: «служебная иконка, не карточка» | FR-1 | `_build_settings_cog` куска 1 не меняется | Visual |
| 19 | **FR-2** «Каждый предметный пункт меню имеет карточку» | FR-2 | Пять карточек ↔ `MAIN_NAV_ITEMS` + Wishlist | UX |
| 20 | «на дашборде меню нет — сайдбар убирается» | FR-2, AC-1 | **(v2)** `render_sidebar_slot` → `[]`; скрытие колонки одним CSS-правилом `:empty` (№9) | Visual |
| 21 | «На остальных страницах сайдбар остаётся» | FR-2, AC-1 | **(v2)** `create_sidebar(pathname)` для четырёх разделов; тест по pathname | Integration |
| 22 | **FR-3** «Клик открывает раздел в состоянии, соответствующем клику» | FR-3 | Двери — `dcc.Link` с контекстом в query params; `handle_panel_query_params` раскладывает по Store'ам | Integration |
| 23 | «завтра» → календарь с завтрашним днём | FR-3, AC-2 | `days[2].href=/calendar?focus_date=<ref+1>` | Integration |
| 24 | «Дух важнее буквы»: позиционная привязка — не требование | FR-3 | Раскладка эскиза v3; зафиксировано в докстринге `build_cards_row` | UX |
| 25 | **FR-4** «Онбординг-тост сохраняет поведение» | FR-4, AC-6 | `_build_balance_banner` + `toggle_balance_toast` + `persist_toast_dismissal` не трогаются; баннер — первый узел layout | Integration |
| 26 | «Прочие сироты закрыты ранее» | FR-4 | Сверка — кнопки шапки куска 1; «Доходы» — см. #13 | UX |
| 27 | **FR-5** «каждая карточка показывает спроектированное пустое состояние» | FR-5, AC-5 | **(v2)** `CardStatus.EMPTY` **по собственным данным блока**; текст-смысл раздела в `build_*_card` | Visual |
| 28 | «без числовых артефактов» | FR-5, AC-5 | Ветка `EMPTY` не рендерит ни `format_rub`, ни проценты; тест «нет «₽» и «%»»; **плюс** `has_data=False` → прочерк, не «0 ₽» | Edge |
| 29 | «карточки не исчезают (конституция FR-2)» | FR-5, AC-5 | `build_cards_row` строит пять карточек безусловно; тест на смешанных статусах | Visual |
| 30 | **FR-6** «карточка «Календарь» — той же моделью слоёв куска 1» | FR-6, AC-3 | `_calendar_block(layers)` — чистая функция, ноль запросов | Integration |
| 31 | «цифры карточек не противоречат шапке/графику» | FR-6, AC-3 | **(v2)** один `get_money_layers` за сборку (тест-счётчик); подушка тоже из `layers` (не из второго расчёта баланса); `recent/upcoming_href` — те же диапазоны, что выборка строк | Perf/Integration |
| 32 | «стратегия загрузки проектируется явно» | FR-6 | **(v2)** докстринг `DashboardPanelService`: 1 сессия (было 4), 1 модель слоёв, 4-9 коротких запросов по фактическим вызовам, дубли названы, `get_settings` исключён, кеша нет намеренно, ленивости нет | Perf |
| 33 | **NFR-1** «< 2 секунд» | NFR-1, AC-10 | **(v2)** замер шага 12 — время **и число запросов**; оценка ~25-40 мс | Perf |
| 34 | «в куске 1 рендер был 13 мс, деградация должна быть объяснима» | задача | R7: покомпонентная оценка запросов; сессий 4 → 1; минус дорогой `get_settings` | Perf |
| 35 | **NFR-2** «сбой одной карточки не обрушивает дашборд» | NFR-2 | `try/except` на блок → `FAILED` → «Не удалось загрузить раздел» при живой двери | Edge |
| 36 | «сбой логируется с трейсбеком (`logger.opt(exception=True)`)» | NFR-2 | Идиома во всех новых except; попутно два `exc_info=True` заменяются | Edge |
| 37 | «Сбой расчёта базовой модели не глотается» | NFR-2 | `get_money_layers` вызывается ВНЕ try/except | Edge |
| 38 | **C-1** «только минимальные приёмники контекста» | C-1 | `calendar.py`: +1 Input, +1 ключ Store, +1 CSS-класс; `goals.py`: +якорные id, +1 узел, +1 колбэк; `transactions.py`, `analytics.py` — 0 правок | Integration |
| 39 | **C-2** «Decimal, session-контракт, сервисы не знают о Dash» | C-2 | `PanelData` — только примитивы; сервис read-only, без `flush`/`commit`; импортов Dash нет | Integration |
| 40 | **C-3** «поведение сервисов не меняется; 693 теста зелёные» | C-3, AC-10 | Кроме `MoneyLayersService` (разрешён C-5) ни один сервис не правится; `_payments_tail_by_day`/`_goals_part_by_day` вызываются со списком из одного дня — их тела не меняются | Integration |
| 41 | **C-4** «Схема БД не меняется» | C-4 | Миграций нет; `app/models/database.py` вне blast radius | Integration |
| 42 | **C-5** «контракт МОЖНО менять, но шапка и график работают, инвариант сохраняется» | C-5 | **(v2)** одно добавленное поле `yesterday`; форма `days` неизменна; инвариант `_split_day` держится по построению, тест инварианта для `yesterday` | Integration |
| 43 | **C-6** «новые элементы дашборда не ломают колбэки на других страницах» | C-6, AC-9 | Двери — `dcc.Link` (Input'ов нет); дверь Wishlist — clientside → Store; вход профиля через сайдбар на Store; **плюс обратная сторона: удалённые элементы удаляются вместе с Input'ами** (#80) | Integration |
| 44 | **C-7** «шапка и график не регрессируют; 47 тестов зелёные или осознанно адаптированы» | C-7, AC-10 | **(v2)** `days` не меняется → `test_dashboard_panel_ui.py` правок **не требует**, тесты остаются зелёными без адаптации; проверяется прогоном (шаг 12) | Visual |
| 45 | «нет вердикта-светофора, нет приветствия, шапка не дверь» | C-7 | `build_free_header` не правится; `TestFreeHeader` остаётся | Visual |
| 46 | **AC-1** «сайдбара/меню на дашборде нет» | AC-1 | см. #20 | Visual |
| 47 | **AC-2** полный набор четырёх переходов | AC-2 | см. #5, #9, #11, #14 | Integration |
| 48 | **AC-3** «остаток «сегодня» равен значению модели слоёв — unit-тест» | AC-3 | Тест шага 4: `calendar.days[1].balance == layers.today.balance == layers.days[0].forecast_balance` | Integration |
| 49 | **AC-4** «readonly-карточка подушки снята» | AC-4 | `_build_cushion_card_readonly`, `dashboard-cushion-card`, `.db-right-col` удалены | Visual |
| 50 | «split-таблицы заменены карточкой Операции» | AC-4 | `_build_transactions_split_table` и связанные id/CSS удалены | Visual |
| 51 | **AC-5** «чистая база → все пять карточек с пустыми состояниями» | AC-5 | см. #27-#29; тест `PanelData` на пустой базе | Edge |
| 52 | **AC-6** «онбординг-тост ведёт себя как до перестройки» | AC-6 | см. #25; `TestToggleBalanceToastProfileUpdated` зелёный без правок | Integration |
| 53 | **AC-7** «минимум > 0 → без усиления; ≤ 0 → усилен — unit-тесты» | AC-7 | Две фикстуры в `test_panel_cards_ui.py`; ассерт на `pnl-flagline-strong` | Edge |
| 54 | **AC-8** оба уровня двери Wishlist | AC-8 | см. #16, #17 | Integration |
| 55 | **AC-9** «модал профиля со всех страниц обоими входами» | AC-9 | Шаг 8: единственный Input открытия — `open-profile-trigger` | Integration |
| 56 | **AC-10** «unit-тесты, полный pytest, black+flake8, рендер в NFR-1» | AC-10 | Шаги 4, 10, 11, 12 | Perf |
| 57 | design.md: «иерархия определяет размер и позицию, но не факт присутствия» | design.md | Wishlist — полоса; все пять присутствуют | UX |
| 58 | design.md: «служебные экраны — иконки, не карточки» | design.md | см. #18 | UX |
| 59 | Эскиз v3: `.door` + `.door-head` + `.door-body` | эскиз | `_door_shell` → `.pnl-door*`; цветная шина гнезда 3px через `--pnl-slot` | Visual |
| 60 | Эскиз v3: цвета гнёзд Календарь/Цели/Операции/Аналитика | эскиз | CSS-переменные на `.pnl-door-<slot>`; зелёный/синий из `--pnl-free`/`--pnl-reserve` | Visual |
| 61 | Эскиз v3: три окошка `.day`, у сегодняшнего фон и класс `.today` | эскиз | `.pnl-day`, `.pnl-day-today`; `CalendarDaySlice.is_today` | Visual |
| 62 | Эскиз v3: подпись окошка «2 операции» / «план» | эскиз | **(v2)** `operations_note` считается из `layers["upcoming_payments"]` (без запроса) для «сегодня»/«завтра»; у «вчера» подпись пустая — как в эскизе (`d-note` там `&nbsp;`), потому что `payments` фильтруется `day >= reference_date` и данных о вчерашних операциях в модели нет | Visual |
| 63 | Эскиз v3: `.flagline` «Ближайшая просадка: 4 сент, остаток 9 800 ₽» | эскиз | `.pnl-flagline` + `format_date_human(dip_date)` + `format_rub(dip_free)`; усиление — `.pnl-flagline-strong` | Visual |
| 64 | Эскиз v3: «102 000 из 150 000 ₽ · к 15 окт» | эскиз | `top_goal_current/target/target_date` + форматтеры | Visual |
| 65 | Эскиз v3: «Ещё 2 цели — по плану»; подушка мелким кеглем `.bar.thin` | эскиз | `others_summary`, `.pnl-pillow`, `.pnl-bar-thin` | Visual |
| 66 | Эскиз v3: заметка vision-критика «выровнять вертикальный ритм карточки Цели» | осадок | `margin-top:auto` у блока подушки (шаг 5) | Visual |
| 67 | Эскиз v3: группы «НЕДАВНИЕ»/«ПРЕДСТОЯЩИЕ», маркер 🔁 | эскиз | `.pnl-grp`; `OperationRow.is_recurring` — **только для материализованных**, см. #82 | Visual |
| 68 | Эскиз v3: «78 400 ₽» `.big-sum` + «расходы августа» | эскиз | `month_total` + `month_label` (родительный падеж) | Visual |
| 69 | Эскиз v3: «Продукты — 24 300 ₽ · 31%» + «крупнейшая категория месяца» | эскиз | `top_category_*`; `.pnl-top-cat` | Visual |
| 70 | Эскиз v3: мини-структура 3 категории + «Прочее» + «из 78 400 ₽» | эскиз | `structure`; CSS-полоска, без Plotly | Visual |
| 71 | Эскиз v3: `.wish` — полоса с левым зелёным бордером, тег «WISHLIST» | эскиз | `.pnl-wish*` | Visual |
| 72 | Эскиз v3: `:focus-visible` outline, `tabindex` на дверях | эскиз | `dcc.Link` фокусируем нативно; `.pnl-door:focus-within` outline | UX |
| 73 | Эскиз v3: адаптив 1180px → 2 колонки, 680px → 1 | эскиз | Те же брейкпоинты в `panel.css` (полная адаптация — Epic-08) | Visual |
| 74 | Эскиз v3: `prefers-reduced-motion` | эскиз | Секция «ДОСТУПНОСТЬ» `panel.css` расширяется на `.pnl-door` | UX |
| 75 | Out of scope: «выбор произвольного месяца в аналитике» | out of scope | `href="/analytics"` без params; `analytics.py` не правится | UX |
| 76 | Out of scope: «/settings — заглушка остаётся» | out of scope | `/settings` не добавляется; шестерёнка ведёт в модал профиля | UX |
| 77 | Out of scope: «полоска-меню вместо сайдбара» | out of scope | `create_sidebar` не переписывается — только условно рендерится и получает аргумент `pathname` | UX |
| 78 | Out of scope: «анимация переходов дашборд↔раздел» | out of scope | Переходы — обычные `dcc.Link` | UX |
| 79 | **НОВОЕ (v2). Владение `url.search`**: очистка search не должна ломать `apply_url_date_filter` (`/transactions?start=&end=`, работает с протокола 0023) | AC-2, C-1, C-3 (регрессия за пределами scope) | `_OWNED_SEARCH_PATHS = {"/calendar", "/goals"}`; на `/transactions` — `PreventUpdate`; контракт в докстринге `handle_panel_query_params`; контрактный тест (шаг 11) + ручная проверка «период + F5» (шаг 13) | Integration |
| 80 | **НОВОЕ (v2). Обратная сторона C-6**: «удаляешь элемент — удаляй его Input» | C-6, AC-8 | `Input("open-wishlist-modal-btn")` удаляется вместе с `build_wishlist_widget`; правило в докстринге `open_wishlist_modal` и в `patterns/callbacks.md`; аналогично проверены все Output'ы на элементы сайдбара (#83) | Integration |
| 81 | **НОВОЕ (v2). Один источник правды пустоты**: отрисовкой карточки управляет только её `CardStatus` | FR-5, AC-5 | `is_new_user` из `PanelData` **убрано**; правило в докстринге `build_cards_row` и `CardStatus`; тесты на смешанный случай в сервисе (шаг 4) и в UI (шаг 10) | Edge |
| 82 | **НОВОЕ (v2). Ограничение по регулярным операциям**: карточка «Операции» показывает только материализованные операции | FR-1.c, C-3 | Ограничение в докстринге `OperationsCardData` и `_operations_block`; в списке документации на обновление (`modules/ui-components.md`); решение владельца 2026-08-25 | Edge |
| 83 | **НОВОЕ (v2). Output на условно присутствующий элемент**: `sidebar-nav` исчезает с `/dashboard` | C-6, AC-1 | Колбэк `highlight_active_sidebar` **удаляется**, подсветка переезжает в `create_sidebar(pathname)`; гонка двух колбэков за один Input снята, а не заглушена guard'ом | Integration |
| 84 | **НОВОЕ (v2). Контракт материализации ORM**: `PanelData` безопасен после закрытия сессии | C-2, NFR-2 | Требование в докстринге `DashboardPanelService`; тест, читающий все поля `PanelData` после выхода из `with` (шаг 4); `to_data` вызывается внутри сессии (его обращение к `category_rel` — `wishlist_service.py:310-312`) | Edge |
| 85 | **НОВОЕ (v2). Явные границы расчёта «вчера»** | FR-1.a, AC-3, FR-6 | Таблица границ: `_forecast_balances(ref - WINDOW_LOOKBACK_DAYS, …)`, `collect_start = min(_month_start(ref), ref - 1)`; целевой тест «`yesterday` != 0 на истории»; `None` → прочерк вместо «0 ₽» | Edge |
| 86 | **НОВОЕ (v2). Форма `days` — контракт куска 1** | C-5, C-7 | `days` не меняется; регрессионный тест `len(days) == WINDOW_DAYS and days[0].date == ref`; `window_days()`-хелпер не создаётся | Integration |

## Blast Radius

### Прямые изменения

**Новые файлы (4)**
- `app/schema/panel.py` — контракты карточек
- `app/services/panel_service.py` — `DashboardPanelService`
- `app/components/panel_cards.py` — build-функции карточек
- `tests/test_panel_service.py`, `tests/test_panel_cards_ui.py`

**Изменяемые файлы (14)**

| Файл | Что меняется | Почему связано |
|---|---|---|
| `app/components/dashboard.py` | Layout → шапка+график+`dashboard-cards-row`; удаляются `_build_transactions_split_table`, `_build_cushion_card_readonly`, `_build_empty_state`; `_load_dashboard_components` 5→3; оба колбэка 5→3 Output'а; 4 clientside-триггера пустых состояний удаляются, 1 (дверь Wishlist) добавляется; импорты вычищаются. **`build_layers_chart`/`_axis_tickvals` НЕ ПРАВЯТСЯ (v2)** | ядро задачи |
| `app/main.py` | `sidebar-slot` + `render_sidebar_slot`; `handle_calendar_query_params` → `handle_panel_query_params` (+2 Output'а, `_OWNED_SEARCH_PATHS`); 3 новых `dcc.Store` | FR-2, FR-3, блокер №1 |
| `app/components/sidebar.py` | **(v2)** `create_sidebar(pathname)`; колбэк `highlight_active_sidebar` **удаляется**; clientside-триггер на `sidebar-profile-container`; guard в `update_sidebar_profile`; `exc_info=True` → `logger.opt` | сайдбар стал условным; №10 |
| `app/components/profile_modal.py` | `Input("sidebar-profile-container")` убирается — единственный вход `open-profile-trigger`; `exc_info` → `logger.opt` | AC-9 / C-6, R1 |
| `app/components/wishlist.py` | **(v2)** `build_wishlist_widget`/`_build_widget_item` удаляются; `open_wishlist_modal` — **единственный** Input `open-wishlist-trigger` + guard; `Input("open-wishlist-modal-btn")` **удаляется** | AC-8, C-6, блокер №2 |
| `app/components/calendar.py` | `Input("calendar-focus-date")`; ключ `focus_date` в `calendar-state`; класс `calendar-day-focused` | FR-3, AC-2 |
| `app/components/goals.py` | якорные id в `_build_goal_card`; узел `goals-focus-anchor`; колбэк `apply_goal_focus` | FR-3, AC-2 |
| `app/components/__init__.py` | снятие `build_wishlist_widget` из импортов и `__all__` | удаление функции |
| `app/services/money_layers_service.py` | **(v2, объём резко меньше)** только: левая граница `_forecast_balances`, `collect_start`, новый `_yesterday_slice`, заполнение поля в `MoneyLayersData`. `window_dates`, `days`, `_today_slice`, `_window_min_free`, `_is_empty`, `window_is_flat`, `_split_day`, `_payments_tail_by_day`, `_goals_part_by_day` — **без правок** | C-5, AC-3 |
| `app/schema/money_layers.py` | **(v2)** `WINDOW_LOOKBACK_DAYS` + **одно** поле `yesterday`. Полей `tomorrow`/`window_start` из v1 нет: «завтра» — это `days[1]`, а `window_start == reference_date` | C-5 |
| `app/schema/__init__.py`, `app/services/__init__.py` | реэкспорт новых схем и сервиса | конвенция проекта |
| `app/assets/panel.css` | секции дверей и wishlist-полосы, адаптив, `prefers-reduced-motion` | эскиз v3 |
| `app/assets/custom.css` | удаление `.db-left-col`, `.db-right-col`, `.db-main-row`, `.dashboard-split-table`; правка `.db-page` | старая раскладка 8/4 |
| `app/assets/sidebar.css`, `app/assets/calendar.css` | **(v2)** **один** механизм скрытия: `.sidebar-column:empty { display:none }` (правила `d-none` не вводится); `.calendar-day-focused` | №9, FR-3 |

### Связанные файлы

**Тесты, требующие адаптации**
- `tests/test_dashboard_callbacks.py` — `load_dashboard_data`/`refresh_dashboard_after_crud` 5→3 Output'а, контракт декоратора
- `tests/test_profile_modal_callbacks.py` — вход через Store вместо `sidebar-profile-container`
- `tests/test_money_layers_service.py` — **только добавление** новых тестов (`yesterday`, форма `days`, 1-е число); существующие утверждения не меняются

**Ушло из Blast Radius по сравнению с v1 (аккуратный вариант «вчера»)**
- `tests/test_dashboard_panel_ui.py` (47 тестов) — **правок не требует**: фикстура `make_layers_data` строит `days` как `range(WINDOW_DAYS)` от `ref` (`:113`), и это остаётся верным; утверждения про ось, `MAX_X_TICKS`, «первая подпись == reference_date», плоское окно (`:465`) не затрагиваются. Требуется только добавить ключ `yesterday` в словарь фикстуры, если `build_free_header`/`build_layers_chart` его читают — **они не читают** (`data["days"]` — единственный доступ, `dashboard.py:502/510/513`), поэтому даже этого не требуется до появления TypedDict-total-проверок
- `app/components/dashboard.py::build_layers_chart` и `_axis_tickvals` — вне правок (в v1 переводились на `window_days()`)
- Хелпер `window_days()` — не создаётся
- Mutation-проверка на `window_days()` (рекомендация критика №4) — не нужна, проверяемого хелпера нет; её роль играет регрессионный тест формы `days` (#86)
- `MoneyLayersData.tomorrow`, `MoneyLayersData.window_start` — не добавляются
- `CushionService` из зависимостей композитора — исключён (`get_settings` не вызывается)

**Добавилось в Blast Radius по сравнению с v1**
- `app/components/sidebar.py` — удаление колбэка `highlight_active_sidebar` и подпись `create_sidebar(pathname)` (в v1 был только guard); поэтому в зону риска попадает поведение подсветки активного пункта во всех четырёх разделах
- `main.py::_OWNED_SEARCH_PATHS` — новая явная константа-контракт; в зону контрактного риска входит `transactions.py::apply_url_date_filter`
- Тест-инфраструктура счётчика SQL-запросов (`sqlalchemy.event`) в `tests/test_panel_service.py`

**Файлы БЕЗ правок, но в зоне контрактного риска (проверить прогоном/вручную)**
- `app/components/transactions.py` — `apply_url_date_filter` остаётся единственным владельцем `search` на `/transactions` (блокер №1)
- `app/components/analytics.py` — дефолт `analytics-period-store` становится приёмником двери Аналитики
- `app/components/calendar_wishlist.py` — `wishlist-active-item` становится приёмником второго уровня двери Wishlist
- `app/components/transaction_modals.py` — `refresh_dashboard_after_crud` меняет арность Output'ов
- `app/components/onboarding_wizard.py` — `profile-updated` → `load_dashboard_data`, `update_sidebar_profile`
- `app/services/dashboard_service.py`, `analytics_service.py`, `goal_service.py`, `allocation_service.py`, `wishlist_service.py`, `cushion_service.py` — только вызываются (C-3); `cushion_service` теперь **не вызывается** композитором вовсе

**Общие component ID / Store'ы, затронутые семантически**
- новые: `sidebar-slot`, `dashboard-cards-row`, `panel-wishlist-door`, `open-wishlist-trigger`, `calendar-focus-date`, `goals-focus-goal`, `goals-focus-anchor`
- удаляемые: `dashboard-recent-transactions`, `dashboard-upcoming-transactions`, `dashboard-cushion-card`, `empty-recent-add-btn`, `empty-upcoming-add-btn`, `open-wishlist-modal-btn` (**вместе со своим Input'ом**)
- меняющие роль: `open-profile-trigger` (был вторым входом — стал единственным), `open-wishlist-trigger` (единственный вход в модал wishlist), `wishlist-active-item` (был только из календаря — стал и из карточки), `sidebar-nav` (перестаёт быть Output'ом колбэка — заполняется при построении), `dashboard-period` (остаётся guard'ом клика по графику)

**Документация (после реализации)**
- `.obsidian-docs/knowledge-bank/modules/ui-components.md` — секции Dashboard-щиток, Sidebar; новая секция Panel Cards; **ограничение карточки «Операции» по регулярным операциям** (решение владельца, чтобы не выглядело недоделкой)
- `.obsidian-docs/knowledge-bank/modules/services.md` — `DashboardPanelService` (контракт материализации + стратегия загрузки с названными дублями), эволюция `MoneyLayersService` (поле `yesterday`, форма `days` неизменна)
- `.obsidian-docs/knowledge-bank/modules/schema.md` — `app/schema/panel.py`, `yesterday` в `money_layers.py`
- `.obsidian-docs/knowledge-bank/modules/routing.md` — `?focus_date=`, `?goal=` **и контракт владения `url.search` по pathname**
- `.obsidian-docs/knowledge-bank/patterns/callbacks.md` — правило «удаляешь элемент — удаляй его Input» (обратная сторона C-6) + кейс «Output на условно присутствующий элемент лечится условным рендером, а не guard'ом»
- `memory/spec-context/epic-11.md` — удалить применённые записи с тегом `for: design-loop`

### Проверить после реализации

1. **AC-9 вручную**: профиль открывается шестерёнкой на `/dashboard` И аватаром на каждом из `/calendar`, `/goals`, `/transactions`, `/analytics` (R1, юнит-тестом не ловится).
2. **AC-8 вручную**: клик по телу/заголовку карточки Wishlist открывает модал (проверяет блокер №2 — единственный вход через Store); клик по хотелке ведёт в режим покупок календаря с фокусом.
3. **Блокер №1 вручную**: клик по группе «Недавние»/«Предстоящие» → `/transactions?start=&end=` → **фильтр периода применён**; F5 на этом URL → фильтр остался/переприменён без ошибки; переход на `/calendar?focus_date=…` → `search` очищен, F5 контекст не переприменяет.
4. **AC-1 вручную**: сайдбара на дашборде нет и он не оставляет пустой колонки (одно правило `:empty`); на четырёх разделах сайдбар на месте **с корректной подсветкой активного пункта** (R12 — после удаления `highlight_active_sidebar`).
5. **AC-2 вручную**: все переходы, включая маркер просадки; повторный клик по тому же элементу срабатывает (timestamp-обёртка).
6. **C-7**: `pytest tests/test_dashboard_panel_ui.py` — **47 тестов зелёные БЕЗ правок**; график полос визуально идентичен куску 1 (первая подпись оси = сегодня, маркер минимума на том же дне).
7. **«Вчера» (R3)**: `pytest tests/test_money_layers_service.py` — `yesterday` != 0 на истории; инвариант для `yesterday`; форма `days` неизменна; фикстура «сегодня = 1-е число».
8. **Материализация (R11)**: тест, читающий все поля `PanelData` после закрытия сессии, — зелёный; попутно вручную открыть дашборд на наполненной базе и убедиться, что в логах нет `DetachedInstanceError`.
9. **Пустота (№7)**: тесты смешанного случая (`is_empty=True` + непустые цели) зелёные в сервисе и в UI.
10. **NFR-1**: замер `_load_dashboard_components` на наполненной локальной базе — **время И число SQL-запросов**, запись в протокол, сверка с 13 мс куска 1; счётчик `get_money_layers == 1`.
11. **AC-3/AC-7**: `pytest tests/test_panel_service.py tests/test_panel_cards_ui.py`.
12. **AC-10**: полный `pytest` (693 + новые), `black --check`, `flake8`.
13. **NFR-2**: `patch`-тест падающего блока — дашборд рендерится, одна карточка деградирована, в логах трейсбек.

## Учтённые замечания из критики

| # | Замечание критики v1 | Решение в v2 |
|---|---|---|
| 🔴 1 | Очистка `url.search` ломает дверь Операций — гонка двух колбэков за один Input (`handle_panel_query_params` vs `apply_url_date_filter`, работает с протокола 0023) | Введён явный **контракт владения `url.search` по pathname**: константа `_OWNED_SEARCH_PATHS = {"/calendar", "/goals"}`; колбэк чистит `search` только для путей, чьи параметры разобрал сам, а на `/transactions` бросает `PreventUpdate` — `search` остаётся разделу, как сегодня. Контракт в докстринге, в RTM (#79), контрактный тест (шаг 11: `pathname="/transactions"` → `PreventUpdate`) и ручная проверка «переход в Операции с периодом → фильтр применён; F5 → без ошибки» (шаг 13, п. 3). Идемпотентность на `/transactions` обеспечена самим разделом (повторное применение того же периода не наблюдаемо) |
| 🔴 2 | `Input("open-wishlist-modal-btn")` оставлен после удаления элемента → колбэк модала wishlist мёртв безусловно, AC-8 красный | Input **удалён вместе с элементом**. `open_wishlist_modal` имеет **единственный** `Input("open-wishlist-trigger", "data")` (Store из глобального layout) + guard на пустой Store. Мотивировка «на случай возврата виджета в кусок 3» снята — её нет в требованиях. Правило «**удаляешь элемент — удаляй его Input**» (обратная сторона C-6) зафиксировано в докстринге, в RTM (#80) и идёт в `patterns/callbacks.md`. По этому же правилу проверены все колбэки, ссылающиеся на элементы сайдбара (см. №10) |
| 🟡 3 | Неполный перечень мест, зависящих от формы/границ `days`: `_forecast_balances` (левая граница — «вчера» = 0 ₽), `_is_empty`, `_today_slice` | Выбран **аккуратный вариант** (решение владельца = Подход A критика): форма `days` не меняется, поэтому `_is_empty`, `_today_slice`, `min_free`, `window_is_flat` перестают быть затронутыми **конструктивно**, а не обещанием. Границы даны **явной исчерпывающей таблицей** (секция «Расширение модели слоёв»): `_forecast_balances(user_id, ref - WINDOW_LOOKBACK_DAYS, window_end)` и `collect_start = min(_month_start(ref), ref - WINDOW_LOOKBACK_DAYS)` — единственные две правки границ. Самый опасный пункт закрыт тремя способами: целевой тест «`yesterday["forecast_balance"] != 0` на фикстуре с историей», `None` вместо нуля при отсутствии дня (в UI прочерк, а не «0 ₽»), `logger.warning` с указанием проверить границу |
| 🟡 4 | Объём адаптации 47 тестов визуального слоя недооценён (фикстуры, `_axis_tickvals`, длина окна 45→46 в зоне свежего фикса 0029) | **Шаг исчез из плана целиком.** `days` сохраняет длину `WINDOW_DAYS` и начало `reference_date`, `build_layers_chart`/`_axis_tickvals` не правятся, `window_days()` не создаётся → `tests/test_dashboard_panel_ui.py` правок **не требует** (проверено: единственные консьюмеры `days` — `dashboard.py:502/510/513` и фикстура `:113`/`:465`). Заход в зону `MAX_X_TICKS` не происходит: длина срезов не меняется. Вместо mutation-проверки на `window_days()` вводится **регрессионный тест формы `days`** (`len == WINDOW_DAYS`, `days[0].date == ref`), который покраснеет первым при любой будущей попытке сдвинуть окно |
| 🟡 5 | Контракт материализации ORM не назван: `_goals_block` и `_wishlist_block` строятся на `list[Goal]` / `list[WishlistItem]`; `to_data` принят на веру | Контракт записан **явно** в докстринг `DashboardPanelService` («блок возвращает только `Decimal`/`date`/`str`/`bool`/`int`; обращение к ORM-атрибутам — внутри `with`; ORM за пределы блока не выходит»), в шаг 3 плана и в RTM (#84). Проверено по диску и отражено: `to_data` возвращает примитивы, но внутри читает `item.category_rel` (`wishlist_service.py:310-312`) → безопасен только внутри сессии и при не-eager загрузке даёт по запросу на элемент (учтено в стратегии загрузки как «до 5 коротких SELECT»); `get_focus` (`:108-127`) возвращает сырые ORM. Добавлен **тест, читающий все поля `PanelData` после закрытия сессии** — единственный тест, который ловит detached (R11) |
| 🟡 6 | Оценка «~7 коротких запросов» не сходится; дубли с `MoneyLayersService` (`get_all_by_user`, настройки подушки) не названы; цена `get_settings` не измерена | Стратегия загрузки **пересчитана по фактическим вызовам** (докстринг сервиса): перечислены 6 запросов модели слоёв и 4-9 запросов блоков, вместо «~7». Дубли названы и решены осознанно: `GoalService.get_all_by_user` **оставлен** с обоснованием (milestones не содержат `current_amount`, отфильтрованы `target_date >= ref`, обрезаны до 4; второй вызов — в ту же сессию, identity map); `CushionService.get_settings` **исключён вовсе** как самый дорогой вызов (`_get_current_balance` → `get_balance_on_date` обходит всю recurring-историю) — прогресс подушки считается из `layers["cushion_threshold"]`, `layers["today"]["balance"]` и одного чтения `User.cushion_target`. Побочный выигрыш: цифра подушки приходит из того же источника, что шапка (FR-6), а не из второго расчёта баланса. В замер шага 12 добавлен **счётчик SQL-запросов** (`sqlalchemy.event`), не только время |
| 🟡 7 | `is_new_user` дублирует `CardStatus` → два источника правды для AC-5, достижимо «пустой щиток с непустыми карточками» | Поле `is_new_user` **убрано из `PanelData`** (решение владельца: «каждая карточка честна сама за себя»). Единственный источник правды отрисовки — `<slot>["status"]`; правило зафиксировано в докстринге `CardStatus` и `build_cards_row` с объяснением, почему общего признака нет (`is_empty` — узкий критерий модели слоёв; человек с заведёнными целями обязан видеть прогресс). Добавлены **тесты на смешанный случай** в обе стороны: сервисный (`is_empty=True` + цель без взносов → `goals=OK` с цифрами, `operations=EMPTY`) и UI (`calendar=EMPTY` + `goals=OK` → пустое состояние только в календарной карточке) |
| 🟢 8 | `DIP_STRONG_THRESHOLD = Decimal("0")` — константа, имя которой отрицает решение владельца («порога нет») | Константа **не создаётся**. В коде — прямое `dip_free <= 0` с комментарием «факт знака числа, как красное „Свободно“ в шапке куска 1», в `app/schema/panel.py` — явная заметка, почему константы здесь нет (чтобы следующий разработчик не «настроил порог») |
| 🟢 9 | Два несогласованных механизма скрытия колонки сайдбара (`className="sidebar-column d-none"` и `.sidebar-column:empty`) | Оставлен **один**: CSS-правило `.sidebar-column:empty { display: none }`. `render_sidebar_slot` возвращает только `children` (Output'а на `className` больше нет — колбэк стал одноголовым), правило `d-none` не вводится |
| 🟢 10 | Guard в `highlight_active_sidebar` описан как защита от «шума в логах»; поведение колбэка с Output на отсутствующий элемент не проверено | Проблема **устранена, а не заглушена**: колбэк `highlight_active_sidebar` **удаляется**, подсветка активного пункта переезжает в `create_sidebar(pathname)` — вычисляется там же, где рождается сайдбар, тем же `_build_nav_links(pathname)`. Обоснование в докстринге: после FR-2 сайдбар рендерится колбэком по тому же `Input("url","pathname")`, и два колбэка на один Input, один из которых пишет в узел, который второй в этот же момент создаёт/удаляет, — гонка, а не шум. Побочно: минус один колбэк и минус один Output на условно присутствующий элемент. Фактическая сторона вопроса — в ответе на вопрос 2 |

## Ответы на вопросы критика

**1. `[факт]` Кто после правки владеет `url.search` и для каких `pathname` он очищается?**

Проверено по диску. Сегодня `url.search` имеет **двух** читателей: `handle_calendar_query_params` (`main.py:106-146`) — единственный, кто **пишет** `Output("url","search") = ""`, причём разбирает параметры только под guard'ом `if pathname == "/calendar"` (`:133`) и при пустом `url_search` бросает `PreventUpdate`; и `apply_url_date_filter` (`transactions.py:1470-1520`) — только **читает**, под guard'ом `if pathname != "/transactions": PreventUpdate`, в `search` не пишет, параметры остаются в URL, и это работающее с протокола 0023 поведение. Блокер подтверждён: расширение первого колбэка на несколько путей с сохранением `Output("url","search")` создало бы гонку.

Контракт в v2: константа `_OWNED_SEARCH_PATHS = frozenset({"/calendar", "/goals"})`. Колбэк разбирает параметры и чистит `search` **только** для этих двух путей; на `/transactions` и на всём остальном — `PreventUpdate` первой же строкой (`if not url_search or pathname not in _OWNED_SEARCH_PATHS`). Дополнительно: если для владеемого пути ни один параметр не распознан, тоже `PreventUpdate` — `search` не затирается на битом вводе. `/analytics` в контракт не входит вовсе: дверь Аналитики не несёт параметров (раздел уже открывается на текущем месяце через дефолт `analytics-period-store`). Контракт отражён в докстринге `handle_panel_query_params`, в RTM (#79), в контрактном тесте шага 11 и в ручной проверке шага 13 п. 3 («переход в Операции с периодом → фильтр применён; F5 → без ошибки»).

**2. `[факт]` Что происходит с колбэком, у которого Output указывает на отсутствующий в DOM элемент?**

Критик исходил из неверной посылки, и это важно зафиксировать. Элемент `sidebar-nav` рождается в `create_sidebar()` (`sidebar.py:103-113`), а `create_sidebar()` вызывается **статически** в глобальном layout (`main.py:59`) — то есть сегодня присутствует на всех страницах, и колбэк `highlight_active_sidebar` (`sidebar.py:152-160`) корректен. Задокументированный проектом класс регрессий (`patterns/callbacks.md`) касается **именно Input'ов**: клиентский рендерер не отправляет колбэк, если Input-элемента нет в DOM; про Output такого правила в KB нет, и Dash действительно терпит Output в отсутствующий элемент при `suppress_callback_exceptions=True`.

Но после снятия сайдбара с дашборда возникает **другая** проблема, и v2 решает именно её: `render_sidebar_slot` и `highlight_active_sidebar` будут иметь **один и тот же** `Input("url","pathname")`, причём второй пишет `children` в узел, который первый в этот же момент создаёт или удаляет. Порядок применения Output'ов Dash не гарантирует — это гонка, а формулировка v1 «шум в логах» её преуменьшала. Поэтому v2 не ставит guard, а **убирает колбэк**: подсветка вычисляется при построении, `create_sidebar(pathname)` вызывает тот же `_build_nav_links(pathname)`, а `render_sidebar_slot` уже слушает `url.pathname`. Один колбэк, один Input, ни одного Output на условно присутствующий элемент. По тому же принципу проверен `update_sidebar_profile`: его значения подставляются при построении, а сам колбэк остаётся только ради `Input("profile-updated","data")` с guard'ом на dashboard-pathname. Ручная проверка подсветки во всех четырёх разделах — шаг 13, п. 4 (R12).

**3. `[факт]` `WishlistService.to_data(item)` материализует все поля, нужные `WishlistCardRow`?**

Проверено по диску. `to_data` (`wishlist_service.py:299-325`) возвращает **чистый словарь примитивов** — `id`, `name`, `amount` (уже отформатированный `format_amount`), `category_id/name/icon`, `priority`, `status`, `planned_date` (ISO-строка или `None`), `planned_transaction_id` (int). То есть все поля, нужные `WishlistCardRow`, включая `planned_transaction_id`, в нём есть и после закрытия сессии читаются безопасно. **Но** сам `to_data` внутри обращается к ORM-связи `item.category_rel` (`:310-312` — `.name`, `.icon`), а `get_focus` (`:108-127`) возвращает сырые `list[WishlistItem]`. Следствия, отражённые в v2: (а) `to_data` обязан вызываться **внутри** сессии — это часть контракта материализации в докстринге сервиса; (б) при не-eager загрузке каждый элемент даёт дополнительный короткий SELECT Category (N+1 на `limit=5`) — учтено в стратегии загрузки честно, как «до 5 коротких SELECT из одной сессии», а не спрятано; (в) добавлен тест, читающий все поля `PanelData` после закрытия сессии (только он ловит detached — тесты карточек кормятся словарями, а тест внутри сессии проблему не видит).

**4. `[факт]` Во что превращается `CushionService.get_settings` по числу запросов — чего стоит `_get_current_balance`?**

Проверено по диску. `get_settings` (`cushion_service.py:126-166`) = `_get_user` (1 запрос) + `_get_current_balance` (`:75-89`) → `CalendarService.get_balance_on_date(user_id, today)` (`calendar_service.py:668-694`), а тот складывает `_get_starting_balance` + `_calculate_balance_before_date` + `_calculate_recurring_before_date`, то есть **не константа, а расчёт со сканом recurring-шаблонов и exceptions и суммированием в памяти** — что зафиксировано и в самом проекте, в докстринге `get_threshold_amount` (`:94-101`: «обходит recurring-историю от самого раннего шаблона»). Это самый дорогой из четырёх блочных вызовов v1.

Решение v2: **`get_settings` не вызывается вовсе.** `MoneyLayersService` уже зовёт дешёвый `get_threshold_amount` (`money_layers_service.py:150-162`: 1 SELECT User + формула, без `_get_current_balance`), и его результат лежит готовым полем `cushion_threshold` в `MoneyLayersData` (`money_layers.py:220-221`). Остаток «сегодня» модель тоже уже знает — `layers["today"]["balance"]`. Значит `_goals_block` берёт `threshold` и `current` из модели, а `target` — одним чтением `User.cushion_target` (identity map: `User` уже загружен и `_user_data_markers`, и `BudgetReservationService.get_settings`), и считает `progress` той же формулой `min(current/target*100, 100)`. Второй расчёт баланса ради процента подушки был бы ровно тем дублем, от которого лечит FR-6, и вторым источником остатка — тем, от чего лечит кусок 1. Дубль `GoalService.get_all_by_user` (модель зовёт его в `_goal_milestones`, `:723`) оставлен осознанно и назван: `milestones` не содержат `current_amount`, отфильтрованы `target_date >= ref` и обрезаны до `MAX_MILESTONES_IN_WINDOW + 1`, а карточке нужен полный список активных целей в порядке `priority`. В замер добавлен счётчик запросов, потому что на локальном SQLite время дубли скрывает, а число — нет.

**5. `[решение]` При расхождении `is_new_user` и `CardStatus` блока — что главнее?**

Решение владельца (осадок `memory/spec-context/epic-11.md`, 2026-08-25): «Пустые состояния карточек: **каждая карточка честна сама за себя**. Общий признак „база пуста“ не управляет отрисовкой карточек; карточка показывает пустое состояние только если пусто именно в её разделе. Пользователь с заведёнными целями видит их прогресс, даже если операций ещё нет. Отброшено: „щиток целиком в режиме первого запуска“ — риск, что человек с заведёнными целями решит, будто данные потерялись».

Реализация: поле `is_new_user` **убрано** из `PanelData` (вариант «явно переопределить как не влияющую подсказку» отброшен — неиспользуемое поле в контракте рано или поздно кто-то использует). Единственный источник правды — `<slot>["status"]`, что зафиксировано в докстрингах `CardStatus` и `build_cards_row`. Тест на смешанный случай — обязательный, в двух направлениях (замечание №7).

**6. `[решение]` Оставляем расширение окна модели или переходим на «вчера отдельным полем»?**

Решение владельца (осадок, 2026-08-25): «„Вчера“ в карточке „Календарь“ — **аккуратный вариант**: окно расчёта модели слоёв НЕ сдвигается назад, добавляется одно новое значение „остаток за вчера“, посчитанное тем же способом. Главный график, подписи оси, поиск дня просадки, признак пустой базы и 47 тестов визуального слоя куска 1 не трогаются вовсе — риск регрессии почти нулевой. Отброшено: сдвиг всего окна на день назад (единая форма данных на будущее, но меняет основу, на которую опирается кусок 1; критик нашёл три недоучтённых места, в одном „вчера“ молча показало бы 0 ₽). Если позже понадобится „позавчера“/неделя назад — это отдельный осознанный шаг, а не побочный эффект».

Реализация в v2: `MoneyLayersData.days` сохраняет форму и смысл (`WINDOW_DAYS` дней от `reference_date`); добавлено единственное поле `yesterday: DayLayers | None`, посчитанное тем же `_split_day` из того же вызова расчёта балансов с расширенной левой границей; `window_days()` не создаётся; шаг «адаптация 47 тестов» из плана исчез; замечания №3 и №4 сняты конструктивно. Границы, обязанные покрывать `ref-1`, перечислены явной таблицей — `_forecast_balances(user_id, ref - WINDOW_LOOKBACK_DAYS, window_end)` и `collect_start = min(_month_start(ref), ref - WINDOW_LOOKBACK_DAYS)`; без первой «вчера» молча показало бы 0 ₽ (самый опасный пункт критики), поэтому к ней приложены целевой тест, `None`-вместо-нуля и `logger.warning`.

**7. `[решение]` R7 (карточка Операции не покажет виртуальные recurring-инстансы) — осознанное ограничение или исключение из C-3?**

Решение владельца (осадок, 2026-08-25): «Карточка „Операции“ показывает только фактически сохранённые операции; регулярные платежи, которые ещё не материализованы в базе, в неё не попадают (эскиз рисовал „Аренда 🔁“ — этого не будет). Владелец принял ограничение: регулярные видны в календаре и в графике щитка, а правка общего сервиса операций запрещена ограничением C-3 спеки. Ограничение фиксируется в докстринге блока и в документации, чтобы не выглядело недоделкой».

Реализация: ограничение зафиксировано в трёх местах — докстринг `OperationsCardData` (`app/schema/panel.py`), докстринг `_operations_block` (`panel_service.py`) и список документации на обновление (`modules/ui-components.md`, секция Panel Cards). В RTM это строка #82. Флаг `is_recurring` в `OperationRow` остаётся: материализованные регулярные операции маркер 🔁 получают. Где регулярные видны пользователю, названо прямо: календарь, график полос щитка и тултип легенды слоя «Платежи» (кусок 1). Исключения из C-3 не запрашивается, `DashboardService` не правится.
