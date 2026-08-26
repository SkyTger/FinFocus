# Solution v1: Единый сбор `PanelData` + карточки-двери на Store-триггерах

## Обзор решения

Пять решений образуют скелет:

1. **Один сбор данных на весь щиток — `DashboardPanelService`.** Новый read-only сервис-композитор в `app/services/panel_service.py` за **одну** сессию БД собирает `PanelData` — TypedDict со срезами всех пяти карточек плюс уже существующая `MoneyLayersData`. Ни одна build-функция карточки не открывает сессию сама (сегодня `_build_cushion_card_readonly` и `build_wishlist_widget` открывают свои — это уходит). Число сессий за рендер дашборда: **1** (было 4). Число обращений к БД-сервисам: модель слоёв (как в куске 1) + 4 дешёвых блока карточек.

2. **Окно модели слоёв расширяется на один день назад** (C-5, разрешено спекой): `MoneyLayersData` получает поле `yesterday: DayLayers | None` и `days` начинает с `reference_date - 1`. Это делает «вчера» карточки Календарь **тем же числом**, что и модель шапки/графика, без второго запроса баланса. График рисует окно с сегодня (срез `days[1:]`), минимум ищется по тому же срезу — визуально и поведенчески кусок 1 не меняется (C-7).

3. **Карточки — `<a>`-двери и Store-триггеры, не прямые Input'ы.** Навигационные клики реализуются `dcc.Link` (переход через `url.pathname/search`, серверных колбэков не требует вообще — самый дешёвый способ не нарваться на C-6). Клики, которым нужен не переход, а модал/режим (дверь Wishlist), идут через `clientside_callback` → глобальный `dcc.Store` → существующий серверный приёмник, с guard'ом на пустой Store.

4. **Приёмники контекста — расширение единого callback query params в `app/main.py`.** Добавляются `?focus_date=YYYY-MM-DD` (календарь), `?goal=ID` (цели) и переиспользуется `?wishlist_item=ID`. `main.py` разбирает params и пишет в глобальные Store'ы (`calendar-focus-date`, `goals-focus-goal`), разделы читают Store — приёмники минимальны (C-1).

5. **Деградация — на уровне блока карточки.** `DashboardPanelService` собирает каждый блок в своём `try/except` с `logger.opt(exception=True)` и выставляет `CardBlock.failed`; UI рисует «Не удалось загрузить» вместо карточки, остальные четыре живы. Сбой `MoneyLayersService` (базовая модель) не глотается — правило куска 1.

## Архитектура

### Компоненты

**Сервисный слой (новое)**

| Компонент | Файл | Роль |
|---|---|---|
| `DashboardPanelService` | `app/services/panel_service.py` (новый, ~330 строк) | Read-only композитор: одна сессия, один `PanelData`. Знает `MoneyLayersService`, `GoalService`, `AllocationService`, `CushionService`, `DashboardService`, `AnalyticsService`, `WishlistService`. О Dash не знает (C-2). |
| схемы карточек | `app/schema/panel.py` (новый, ~200 строк) | `PanelData`, `CalendarCardData`, `GoalsCardData`, `OperationsCardData`, `AnalyticsCardData`, `WishlistCardData`, `CardStatus`. |
| расширение модели слоёв | `app/schema/money_layers.py`, `app/services/money_layers_service.py` | `yesterday`, `days` от `ref-1`, `WINDOW_LOOKBACK_DAYS = 1`. |

**Презентационный слой**

| Компонент | Файл | Роль |
|---|---|---|
| ряд дверей + build-функции | `app/components/panel_cards.py` (новый, ~620 строк) | `build_cards_row(PanelData)` и по одной чистой `build_*_card(...)` на карточку. Чистые функции без БД — тестируются словарями (AC-10). |
| щиток | `app/components/dashboard.py` | Layout без split-таблиц/подушки/wishlist-виджета; `_load_dashboard_components` → 3 Output'а; clientside-триггеры новых элементов. |
| каркас | `app/main.py` | Сайдбар рендерится колбэком по `pathname` (на дашборде — пусто); расширенный разбор query params; два новых Store'а. |
| приёмники контекста | `app/components/calendar.py`, `app/components/goals.py` | Минимальные Input'ы на новые Store'ы. |
| стили | `app/assets/panel.css` | Секции `.pnl-slots`, `.pnl-door*` по эскизу v3; `app/assets/custom.css` — снятие `.db-left-col/.db-right-col/.db-main-row/.dashboard-split-table`. |

### Диаграмма взаимодействия

```
Открытие /dashboard
  url.pathname ──► load_dashboard_data (dashboard.py)
                     │
                     └─ _load_dashboard_components()
                          with get_db_session() as session:      ← ОДНА сессия
                            DashboardPanelService(session).get_panel_data(uid)
                              ├─ MoneyLayersService.get_money_layers()   (не глотаем сбой)
                              ├─ try: _goals_block()      GoalService+AllocationService+CushionService
                              ├─ try: _operations_block()  DashboardService (recent/upcoming)
                              ├─ try: _analytics_block()   AnalyticsService.get_expenses_by_category
                              └─ try: _wishlist_block()    WishlistService.get_focus
                          → PanelData (всё материализовано, безопасно вне сессии)
                     │
                     ├─► build_free_header(data.layers, profile)   (кусок 1, без изменений)
                     ├─► build_layers_chart(data.layers)           (кусок 1, срез days[1:])
                     └─► build_cards_row(data)  →  5 × <дверь>

Клик по элементу двери
  «завтра»            ─ dcc.Link href="/calendar?focus_date=2026-08-26"
  цель                ─ dcc.Link href="/goals?goal=7"
  «Операции»          ─ dcc.Link href="/transactions?start=…&end=…"
  «Аналитика»         ─ dcc.Link href="/analytics"
  тело Wishlist       ─ clientside → Store open-wishlist-trigger → wishlist.py
  хотелка             ─ dcc.Link href="/calendar?wishlist_item=3"   (механизм 0023)

Приёмники (main.py handle_panel_query_params)
  url.search ──► open-recon-trigger | wishlist-active-item
             ──► calendar-focus-date  ──► calendar.py load_and_navigate_calendar
             ──► goals-focus-goal     ──► goals.py apply_goal_focus
```

## Файловая структура

```
app/
  schema/
    panel.py                    NEW  — TypedDict-контракты карточек
    money_layers.py             MOD  — yesterday, WINDOW_LOOKBACK_DAYS
    __init__.py                 MOD  — реэкспорт схем панели
  services/
    panel_service.py            NEW  — DashboardPanelService
    money_layers_service.py     MOD  — окно от ref-1, срез today/yesterday
    __init__.py                 MOD  — экспорт DashboardPanelService
  components/
    panel_cards.py              NEW  — build_*_card, build_cards_row
    dashboard.py                MOD  — layout/колбэки/clientside-триггеры
    sidebar.py                  MOD  — is_dashboard-guard колбэка подсветки
    calendar.py                 MOD  — приёмник calendar-focus-date
    goals.py                    MOD  — приёмник goals-focus-goal + anchor-id карточек
    wishlist.py                 MOD  — второй вход в модал через Store
    __init__.py                 MOD  — экспорты (снятие build_wishlist_widget)
  main.py                       MOD  — сайдбар колбэком, query params, Store'ы
  assets/
    panel.css                   MOD  — .pnl-slots / .pnl-door* / .pnl-wish*
    custom.css                  MOD  — снятие .db-* раскладки 8/4
    clientside_triggers.js      MOD  — (переиспользуется timestamp_trigger)
tests/
  test_panel_cards_ui.py        NEW  — визуальный слой карточек (стиль 0029)
  test_panel_service.py         NEW  — сборка PanelData, деградация, согласованность
  test_dashboard_panel_ui.py    MOD  — адаптация под срез days[1:] (C-7)
  test_money_layers_service.py  MOD  — yesterday, инвариант на расширенном окне
  test_dashboard_callbacks.py   MOD  — 5 Output'ов → 3
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

    Стратегия загрузки (FR-6, NFR-1):
        * одна сессия на рендер (было четыре: слои+профиль, подушка,
          wishlist-виджет — каждый со своим get_db_session);
        * модель слоёв вызывается РОВНО ОДИН раз и переиспользуется
          карточкой «Календарь» — второго расчёта баланса нет;
        * блоки целей / операций / аналитики / wishlist — короткие
          агрегирующие запросы на текущий месяц, не окно;
        * кеша нет намеренно: единственный источник инвалидации —
          global-transaction-trigger, а он уже перерисовывает щиток;
          кеш добавил бы риск показать устаревшие цифры (P1-боль
          «цифры противоречат друг другу») без выигрыша в бюджете.
    """

    def __init__(self, session: Session) -> None: ...

    def get_panel_data(
        self,
        user_id: int,
        reference_date: date | None = None,
    ) -> PanelData:
        """Собирает PanelData целиком.

        Raises:
            Любое исключение MoneyLayersService — базовая модель
            остатка НЕ деградирует (правило куска 1, NFR-2).
            Сбои остальных блоков ловятся поблочно и превращаются
            в CardStatus.FAILED с логом logger.opt(exception=True).
        """

    # --- блоки; каждый вызывается под своим try/except ---
    def _calendar_block(self, layers: MoneyLayersData) -> CalendarCardData: ...
    def _goals_block(self, user_id: int) -> GoalsCardData: ...
    def _operations_block(self, user_id: int, ref: date) -> OperationsCardData: ...
    def _analytics_block(self, user_id: int, ref: date) -> AnalyticsCardData: ...
    def _wishlist_block(self, user_id: int) -> WishlistCardData: ...
```

`_calendar_block` — чистая функция от уже посчитанной `MoneyLayersData`, **без единого запроса**: это и есть механическая гарантия AC-3.

### Расширение модели слоёв (C-5)

```python
# app/schema/money_layers.py
WINDOW_LOOKBACK_DAYS = 1
"""Сколько дней ДО reference_date входит в окно модели.

Нужен карточке «Календарь» (FR-1.a: вчера/сегодня/завтра). Один
день назад вместо отдельного запроса баланса: «вчера» обязано быть
тем же числом, что и модель шапки (FR-6, AC-3), а второй источник
остатка — ровно тот способ разойтись, от которого лечит кусок 1.

График куска 1 показывает окно ОТ СЕГОДНЯ (C-7): build_layers_chart
рисует срез window_days(data), минимум ищется по нему же.
"""

class MoneyLayersData(TypedDict):
    days: list[DayLayers]          # [ref-1 .. ref+44], len == WINDOW_DAYS + 1
    yesterday: DayLayers | None    # NEW: срез ref-1; None при сбое расчёта
    today: TodaySlice
    tomorrow: DayLayers | None     # NEW: срез ref+1
    window_start: date             # NEW: ref - WINDOW_LOOKBACK_DAYS
    # ... остальные поля без изменений
```

```python
# app/services/money_layers_service.py — хелпер для куска 1
def window_days(data: MoneyLayersData) -> list[DayLayers]:
    """Дни окна ОСИ ГРАФИКА — от reference_date, без дней lookback.

    Кусок 1 (шапка, график, маркер минимума) работает ровно с этим
    срезом: расширение окна назад сделано для карточки «Календарь»
    и не должно менять картинку графика (C-7).
    """
    return [day for day in data["days"] if day["date"] >= data["reference_date"]]
```

`min_free` / `min_free_date` считаются по `window_days(...)`, а не по всему `days` — иначе «вчера» могло бы стать минимумом окна и сдвинуть маркер на графике (регрессия C-7).

### Двери-переходы

```python
# app/components/panel_cards.py
def _door_shell(
    *,
    slot_key: str,          # "calendar" | "goals" | "operations" | "analytics" | "wishlist"
    icon: str,              # bootstrap-icon класс
    title: str,
    href: str | None,       # None → тело двери не ссылка (Wishlist: модал)
    body: list,
    element_id: str | None = None,
    n_clicks: int | None = None,
) -> html.Div:
    """Каркас карточки-двери по эскизу v3 (.door / .door-head / .door-body).

    Заголовок обёрнут в dcc.Link, если href задан: переход выполняет
    сам dcc.Link через url, серверный колбэк НЕ нужен — самый дешёвый
    способ не создать регрессию класса C-6 (нет Input на элемент,
    живущий только на дашборде).
    """

def build_calendar_card(data: CalendarCardData) -> html.Div:
    """Карточка «Календарь»: вчера / сегодня / завтра + маркер просадки.

    Каждое окошко дня — dcc.Link на /calendar?focus_date=<ISO> (FR-3,
    AC-2). Маркер просадки показывается ВСЕГДА (день минимума слоя
    «Свободно» в окне), при min_free <= 0 получает класс
    pnl-flagline-strong (AC-7): усиление привязано к факту знака числа,
    порога-вердикта нет (решение владельца 2026-08-25).
    """

def build_goals_card(data: GoalsCardData) -> html.Div:
    """Карточка «Цели»: топ-цель + сводка остальных + строка подушки.

    Топ-цель — dcc.Link на /goals?goal=<id> (AC-2); сводка и подушка —
    dcc.Link на /goals. Отдельной карточки подушки нет (AC-4).
    """

def build_operations_card(data: OperationsCardData) -> html.Div:
    """Карточка «Операции»: до OPERATIONS_PER_GROUP недавних и предстоящих.

    Обе группы — ссылки на /transactions?start=&end= с периодом группы
    (механизм протокола 0023, apply_url_date_filter уже существует).
    """

def build_analytics_card(data: AnalyticsCardData) -> html.Div:
    """Карточка «Аналитика»: расходы месяца, топ-категория, мини-структура.

    Доходов НЕТ ни в каком виде (решение владельца 2026-08-25).
    Мини-структура — html.Div с процентными долями, БЕЗ Plotly:
    инлайновая полоска на CSS-ширинах (эскиз v3 рисовал её SVG),
    пятый вызов Plotly на рендер дашборда не нужен (NFR-1).
    """

def build_wishlist_card(data: WishlistCardData) -> html.Div:
    """Карточка «Wishlist» — двухуровневая дверь (решение владельца 2026-08-25).

    Уровень 1: заголовок/тело (id="panel-wishlist-door", n_clicks=0) →
        clientside-триггер → Store open-wishlist-trigger → модал.
    Уровень 2: каждая хотелка — dcc.Link на
        /calendar?wishlist_item=<id> → режим покупок с фокусом на ней
        (существующий механизм, wishlist-active-item, AC-8).
    """

def build_cards_row(data: PanelData) -> html.Div:
    """Ряд карточек-дверей (FR-1, FR-2).

    Все пять карточек присутствуют ВСЕГДА — конституция щитка (FR-2):
    даже при пустых данных (FR-5) и даже при сбое блока (NFR-2)
    карточка остаётся на месте, меняется только её содержимое.
    """
```

### Store-триггеры и приёмники (C-6)

```python
# app/main.py — глобальные Store'ы (живут на ВСЕХ страницах)
dcc.Store(id="open-wishlist-trigger", data=None),   # NEW: тело двери Wishlist
dcc.Store(id="calendar-focus-date", data=None),     # NEW: ?focus_date=
dcc.Store(id="goals-focus-goal", data=None),        # NEW: ?goal=
```

```python
# app/components/dashboard.py — единственный новый clientside-триггер
# Дверь Wishlist (тело карточки) → модал управления wishlist (AC-8).
# Элемент рождается динамически внутри dashboard-cards-row и вне
# /dashboard в DOM отсутствует. Прямой Input сломал бы open_wishlist_modal
# целиком (класс регрессий C-6, протоколы 0026 и 0028/3.5-m-fix).
clientside_callback(
    ClientsideFunction("triggers", "timestamp_trigger"),
    Output("open-wishlist-trigger", "data", allow_duplicate=True),
    Input("panel-wishlist-door", "n_clicks"),
    prevent_initial_call=True,
)
```

```python
# app/components/wishlist.py — приёмник получает ВТОРОЙ вход через Store
@callback(
    [Output("wishlist-modal", "is_open", allow_duplicate=True),
     Output("wishlist-items-container", "children"),
     Output("wishlist-add-category", "options")],
    [Input("open-wishlist-modal-btn", "n_clicks"),   # старый вход (может исчезнуть)
     Input("open-wishlist-trigger", "data")],        # новый вход через Store
    prevent_initial_call=True,
)
def open_wishlist_modal(n_clicks: int | None, door_trigger: float | None):
    """Открывает модал wishlist. Два входа (AC-8).

    ВНИМАНИЕ, класс регрессий C-6: open-wishlist-modal-btn существует
    только на дашборде. Пока это был ЕДИНСТВЕННЫЙ Input, колбэк работал;
    добавление второго прямого Input на другой dashboard-only элемент
    отключило бы колбэк везде. Второй вход подключён Store'ом.

    Guard на пустой Store обязателен: Store — состояние, не событие
    (layout Dash не пересоздаётся между страницами), иначе модал
    переоткрывался бы при каждой загрузке страницы после первого клика.
    """
    triggered_id = ctx.triggered_id
    if triggered_id == "open-wishlist-trigger" and not door_trigger:
        raise PreventUpdate
    if triggered_id == "open-wishlist-modal-btn" and not n_clicks:
        raise PreventUpdate
    ...
```

```python
# app/main.py — расширение ЕДИНОГО callback query params (FR-3)
@callback(
    [Output("open-recon-trigger", "data"),
     Output("wishlist-active-item", "data"),
     Output("calendar-focus-date", "data"),
     Output("goals-focus-goal", "data"),
     Output("url", "search")],
    Input("url", "search"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def handle_panel_query_params(url_search: str | None, pathname: str | None):
    """Разбирает query params дверей и раскладывает по Store'ам.

    Расширение механизма протоколов 0023/0028, а не новый механизм
    (свидетельство поиска — memory/spec-context/epic-11.md):
      /calendar?open_recon=1        → open-recon-trigger   (было)
      /calendar?wishlist_item=ID    → wishlist-active-item (было)
      /calendar?focus_date=ISO      → calendar-focus-date  (НОВОЕ, FR-3)
      /goals?goal=ID                → goals-focus-goal     (НОВОЕ, FR-3)
      /transactions?start=&end=     → обрабатывает сам раздел (было, 0023)
      /analytics                    → params не нужны: раздел уже
                                      открывается на текущем месяце
                                      (analytics-period-store = "month")
    Значения-триггеры timestamp-обёрнуты: клик по «завтра» дважды
    подряд должен сработать дважды, а Store сравнивается по значению.
    Search очищается после разбора — иначе перезагрузка страницы
    повторно применит контекст.
    """
```

```python
# app/components/calendar.py — приёмник фокус-даты (минимальный, C-1)
@callback(
    [...те же 7 Output'ов существующего load_and_navigate_calendar...],
    [Input("url", "pathname"),
     Input("prev-month-btn", "n_clicks"),
     Input("next-month-btn", "n_clicks"),
     Input("today-btn", "n_clicks"),
     Input("wishlist-active-item", "data"),
     Input("calendar-focus-date", "data")],   # NEW
    [State("calendar-state", "data")],
)
def load_and_navigate_calendar(..., focus_date: dict | None, state: dict | None):
    """...

    Приёмник focus_date (FR-3, AC-2): месяц календаря переставляется
    на месяц кликнутого дня, сам день получает класс
    calendar-day-focused. Новый Output'ов нет — фокус едет через
    уже существующий calendar-state (ключ "focus_date"), поэтому
    логика раздела не переписывается (C-1).
    """
```

```python
# app/components/goals.py — приёмник фокуса цели (минимальный, C-1)
@callback(
    Output("goals-focus-anchor", "children"),   # NEW: единственный новый узел
    Input("goals-focus-goal", "data"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def apply_goal_focus(focus: dict | None, pathname: str | None):
    """Подсвечивает и прокручивает к кликнутой цели (FR-3, AC-2).

    Раздел «Цели» не переписывается (C-1): карточки уже строятся
    списком, им добавлен якорный id={"type": "goal-anchor", "index": id};
    колбэк отдаёт невидимый html.A(href=f"#goal-{id}") + Store для
    clientside-скролла. Порядок целей, allocation и любые расчёты
    раздела не затрагиваются.
    """
```

### Сайдбар: снятие с дашборда (FR-2, AC-1, AC-9)

```python
# app/main.py — колонка сайдбара становится динамической
html.Div(id="sidebar-slot", className="sidebar-column"),

@callback(
    [Output("sidebar-slot", "children"), Output("sidebar-slot", "className")],
    Input("url", "pathname"),
)
def render_sidebar_slot(pathname: str | None):
    """Сайдбар есть на всех страницах, КРОМЕ дашборда (FR-2, AC-1).

    Возвращается ПУСТОЙ контейнер, а не None: className меняется на
    "sidebar-column d-none", чтобы .app-layout не оставлял 288px+gap
    пустого места, но сама позиция в DOM сохраняется.

    ВАЖНО, класс регрессий C-6 наоборот: убирая сайдбар с дашборда,
    мы удаляем из DOM sidebar-profile-container — прямой Input
    колбэка handle_profile_modal (profile_modal.py). На /dashboard
    этот колбэк ЦЕЛИКОМ перестанет отправляться, включая вход через
    шестерёнку (open-profile-trigger) → AC-9 сломается. Поэтому
    вход через сайдбар тоже переводится на Store-триггер
    (open-profile-trigger), и handle_profile_modal больше НЕ имеет
    ни одного Input на элемент, отсутствующий на части страниц.
    """
    is_dashboard = pathname in (None, "/", "/dashboard")
    if is_dashboard:
        return [], "sidebar-column d-none"
    return create_sidebar(), "sidebar-column"
```

```python
# app/components/sidebar.py — clientside-триггер вместо прямого Input
# Аватар сайдбара живёт не на всех страницах (на дашборде сайдбара нет),
# поэтому его клик тоже идёт через Store (симметрично шестерёнке).
clientside_callback(
    ClientsideFunction("triggers", "timestamp_trigger"),
    Output("open-profile-trigger", "data", allow_duplicate=True),
    Input("sidebar-profile-container", "n_clicks"),
    prevent_initial_call=True,
)

@callback(
    Output("sidebar-nav", "children"),
    Input("url", "pathname"),
)
def highlight_active_sidebar(pathname: str | None):
    """...

    Guard: на дашборде сайдбара нет — sidebar-nav отсутствует в DOM.
    Колбэк остаётся объявленным (sidebar-nav рождается динамически
    вместе с сайдбаром), но на дашборде PreventUpdate: попытка
    отдать children в отсутствующий элемент — шум в логах.
    """
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
    Прямого Input на sidebar-profile-container БОЛЬШЕ НЕТ: после снятия
    сайдбара с дашборда этот элемент отсутствует в DOM на /dashboard,
    и прямой Input отключил бы колбэк там целиком — включая вход через
    шестерёнку (AC-9). Оба входа (аватар сайдбара, шестерёнка щитка)
    пишут в один Store open-profile-trigger.
    """
```

## Модель данных

```python
# app/schema/panel.py
"""Контракты данных карточек-дверей щитка (EPIC-11, кусок 2)."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal, TypedDict

from app.schema.money_layers import MoneyLayersData

OPERATIONS_PER_GROUP = 3
"""Сколько операций в каждой группе карточки «Операции» (FR-1.c: «2-3»).

Три, не пять: карточка — фрагмент, а не таблица. Прежние split-таблицы
брали limit=5 — их место заняла эта карточка (AC-4).
"""

MINI_STRUCTURE_CATEGORIES = 3
"""Категорий в мини-структуре карточки «Аналитика» (эскиз v3: 3 + «из N ₽»)."""

DIP_STRONG_THRESHOLD = Decimal("0")
"""Граница усиления маркера просадки (AC-7).

Это НЕ порог-вердикт: усиление привязано к факту знака числа —
ровно как красное «Свободно» в шапке куска 1 (решение владельца
2026-08-25, альтернативы «только день нуля» и «только минимум»
отброшены).
"""


class CardStatus(str, Enum):
    """Состояние блока карточки (FR-5, NFR-2).

    OK      — данные есть, показываем цифры.
    EMPTY   — данных нет вовсе (новый пользователь): пустое состояние
              БЕЗ числовых артефактов, карточка остаётся (FR-2, AC-5).
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
        is_today: True для сегодняшнего окошка (класс .today эскиза).
        balance: Прогнозный остаток дня — DayLayers['forecast_balance'].
            Тот же язык, что у раздела «Календарь» (он показывает
            остаток дня), и то же число, что в модели шапки (AC-3).
        free: Слой «Свободно» дня — для подписи под остатком.
        operations_note: «2 операции» / «план» / None — подпись эскиза.
        href: /calendar?focus_date=<ISO> — дверь дня (FR-3, AC-2).
    """

    date: date
    label: str
    is_today: bool
    balance: Decimal
    free: Decimal
    operations_note: str | None
    href: str


class CalendarCardData(TypedDict):
    """Карточка «Календарь» (FR-1.a). Считается ИЗ MoneyLayersData, без запросов.

    Attributes:
        status: OK / EMPTY / FAILED.
        days: Ровно три окошка: вчера, сегодня, завтра (в этом порядке).
            При отсутствии дня в окне — окошко с status-нейтральным
            прочерком, но окошко есть (ритм карточки не ломается).
        dip_date: День минимума слоя «Свободно» в окне оси — маркер
            просадки, показывается ВСЕГДА (решение «оба»).
        dip_free: Значение минимума на dip_date.
        dip_is_strong: dip_free <= DIP_STRONG_THRESHOLD — маркер
            визуально усилен (AC-7).
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

    Attributes:
        status: OK / EMPTY / FAILED.
        top_goal_id: ID топ-цели (priority=1 среди активных) или None.
        top_goal_name: Название топ-цели.
        top_goal_progress: Прогресс 0..100 (Goal.progress_percentage).
        top_goal_current / top_goal_target: Суммы для подписи
            «102 000 из 150 000 ₽» (эскиз v3).
        top_goal_target_date: «к 15 окт» (эскиз v3).
        top_goal_href: /goals?goal=<id> — дверь с фокусом (AC-2).
        others_count: Сколько ещё целей кроме топовой.
        others_behind_count: Сколько из них с дефицитом бюджета
            (AllocationResult['shortfall'] > 0).
        others_summary: Готовая фраза «по плану» / «1 отстаёт»
            (формулировки design.md; склонение — в build-функции).
        cushion_is_configured: Подушка настроена.
        cushion_progress: Прогресс подушки 0..100 (CushionSettings).
        cushion_label: «78%» либо «не настроена».
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

    Attributes:
        date: Дата операции.
        title: Описание или название категории («Продукты · сегодня»).
        amount: Сумма со знаком по типу (расход — отрицательная).
        kind: "income" | "expense" | "other" — для класса цвета.
        is_recurring: Маркер 🔁 (эскиз v3).
    """

    date: date
    title: str
    amount: Decimal
    kind: Literal["income", "expense", "other"]
    is_recurring: bool


class OperationsCardData(TypedDict):
    """Карточка «Операции» (FR-1.c): 2-3 недавние + 2-3 предстоящие.

    Attributes:
        status: OK / EMPTY / FAILED.
        recent / upcoming: До OPERATIONS_PER_GROUP строк каждая.
        recent_href: /transactions?start=<1-е число>&end=<сегодня>.
        upcoming_href: /transactions?start=<сегодня>&end=<конец месяца>.
            Диапазоны ровно те, по которым DashboardService отбирал
            строки — цифры карточки и раздела совпадают (FR-6).
    """

    status: CardStatus
    recent: list[OperationRow]
    upcoming: list[OperationRow]
    recent_href: str
    upcoming_href: str


class AnalyticsCategorySlice(TypedDict):
    """Доля категории в мини-структуре карточки «Аналитика».

    Attributes:
        name: Название категории.
        total: Сумма расходов.
        share: Доля 0..100 — ширина сегмента полоски.
        color: Цвет сегмента (палитра щитка, не случайная).
    """

    name: str
    total: Decimal
    share: float
    color: str


class AnalyticsCardData(TypedDict):
    """Карточка «Аналитика» (FR-1.d): ТОЛЬКО расходы.

    Показателя «Доходы за месяц» здесь нет и не появится ни в каком
    виде — решение владельца 2026-08-25 (альтернатива «вернуть строку
    мелко» отброшена). Доходы видны в разделе аналитики и в графике
    щитка.

    Attributes:
        status: OK / EMPTY / FAILED.
        month_label: «расходы августа» (родительный падеж, эскиз v3).
        month_total: Расходы месяца — «цифра месяца».
        top_category_name / top_category_total / top_category_share:
            Крупнейшая категория месяца.
        structure: До MINI_STRUCTURE_CATEGORIES долей + «Прочее».
        href: "/analytics" — раздел уже открывается на текущем месяце
            (analytics-period-store = {"type": "month"}), отдельный
            query param не нужен (C-1, AC-2).
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

    Attributes:
        item_id: ID хотелки.
        name: Название.
        amount_label: Готовая строка суммы (WishlistItemData['amount']).
        is_planned: Уже запланирована.
        planned_date_label: Подпись даты плана или None.
        href: /calendar?wishlist_item=<id> — календарь в режиме
            покупок с фокусом на ней (механизм протокола 0023).
    """

    item_id: int
    name: str
    amount_label: str
    is_planned: bool
    planned_date_label: str | None
    href: str


class WishlistCardData(TypedDict):
    """Карточка «Wishlist» (FR-1.e) — двухуровневая дверь.

    Attributes:
        status: OK / EMPTY / FAILED.
        items: Фокусные хотелки (WishlistService.get_focus).
        total_count: Всего хотелок — для подписи «и ещё N».
    """

    status: CardStatus
    items: list[WishlistCardRow]
    total_count: int


class PanelData(TypedDict):
    """Полный набор данных щитка за один сбор (FR-6).

    Attributes:
        layers: Модель слоёв — источник шапки, графика И карточки
            «Календарь». Один вызов на рендер: расхождение цифр
            между шапкой, графиком и карточкой физически невозможно
            (AC-3, лечение P1-боли аудита).
        calendar / goals / operations / analytics / wishlist:
            Срезы карточек.
        reference_date: Дата отсчёта сборки.
        is_new_user: Данных нет вообще (layers['is_empty']) —
            все карточки в пустых состояниях (FR-5, AC-5).
    """

    layers: MoneyLayersData
    calendar: CalendarCardData
    goals: GoalsCardData
    operations: OperationsCardData
    analytics: AnalyticsCardData
    wishlist: WishlistCardData
    reference_date: date
    is_new_user: bool
```

## Обработка ошибок

| Уровень | Поведение | Идиома |
|---|---|---|
| `MoneyLayersService` (базовая модель остатка) | Исключение НЕ глотается — пробрасывается наружу, `load_dashboard_data` показывает единый alert. Без остатка щитка нет (правило куска 1). | существующее |
| Части модели слоёв (порог подушки, бюджет, вехи) | fail-open, `degraded=True`, оговорка в шапке — как в куске 1. | `logger.opt(exception=True).warning(...)` |
| Блок карточки (`_goals_block`, `_operations_block`, `_analytics_block`, `_wishlist_block`) | `try/except Exception` вокруг каждого; `CardStatus.FAILED` + пустые поля. Карточка рисуется с текстом «Не удалось загрузить раздел», ссылка-дверь остаётся рабочей (находимость раздела не теряется — конституция FR-2). Остальные четыре карточки живы (NFR-2). | `logger.opt(exception=True).warning(f"Не удалось собрать блок «{name}» карточки для user_id={uid} (карточка деградирует)")` |
| `_calendar_block` | Нет try/except: чистая функция от уже валидной `MoneyLayersData`, падать нечем. Отсутствие дня в окне — не ошибка, а `None`-слайс. | — |
| `load_dashboard_data` целиком | Существующий `except Exception` → alert, число Output'ов меняется с 5 на 3. | `logger.opt(exception=True).error` |
| Разбор query params | `try/except (ValueError, IndexError)` на каждом параметре; битый `?focus_date=abc` игнорируется молча (не повод падать), `PreventUpdate` если не распознан ни один. | существующее |
| `exc_info=True` | Запрещён: loguru его молча игнорирует. При правке `sidebar.py` / `profile_modal.py` два существующих `exc_info=True` заменяются на `logger.opt(exception=True)` (попутный долг протокола 0027, файлы всё равно правятся). | — |

## План реализации

**Шаг 1. Расширение модели слоёв (C-5) — фундамент AC-3.**
`app/schema/money_layers.py`: `WINDOW_LOOKBACK_DAYS`, поля `yesterday`, `tomorrow`, `window_start`. `money_layers_service.py`: `window_dates` от `ref - 1`; `_horizons.collect_start = min(_month_start(ref), ref - 1)` (иначе «вчера» 1-го числа не соберёт операций); `min_free`/`min_free_date`/`window_is_flat` — по `window_days(...)`; `_today_slice` ищет `ref`, а не `days[0]`. Хелпер `window_days()`. Тесты `test_money_layers_service.py`: инвариант суммы слоёв на расширенном окне, `yesterday` есть/None, минимум НЕ уезжает на «вчера».

**Шаг 2. Кусок 1 не регрессирует (C-7).**
`build_layers_chart` и `_axis_tickvals` работают с `window_days(data)`. Прогон `tests/test_dashboard_panel_ui.py` — фикстуры-строители в нём собирают `days` от `reference_date`; адаптируются фикстуры (добавляется день lookback), утверждения о графике («первая подпись оси == reference_date», «len(days) == WINDOW_DAYS») остаются в силе. Это единственная осознанная адаптация 47 тестов.

**Шаг 3. Контракты карточек.** `app/schema/panel.py` целиком, реэкспорт в `app/schema/__init__.py`. Кода-исполнителя ещё нет — контракт первым, чтобы тесты шага 5 писались от него.

**Шаг 4. `DashboardPanelService`.** `app/services/panel_service.py`, экспорт в `app/services/__init__.py`. Блоки:
- `_calendar_block` — чистая функция от `MoneyLayersData`;
- `_goals_block` — `GoalService.get_all_by_user(ACTIVE)` + `get_savings_budget` + `get_savings_mode` → `AllocationService.calculate_allocation` (без БД) + `CushionService.get_settings`;
- `_operations_block` — `DashboardService.get_recent_transactions(limit=3)` + `get_upcoming_transactions(limit=3)`;
- `_analytics_block` — `AnalyticsService.get_expenses_by_category(user_id, month_start, month_end)` (одна SQL-агрегация; `month_total` = сумма её `total`, второго запроса нет);
- `_wishlist_block` — `WishlistService.get_focus(limit=5)` + `to_data`.

**Шаг 5. Тесты сервиса.** `tests/test_panel_service.py`: `PanelData` на наполненной in-memory базе; AC-3 формализуется утверждением `panel["calendar"]["days"][1]["balance"] == panel["layers"]["today"]["balance"]` **и** `... == panel["layers"]["days"][i]["forecast_balance"]` для `i` дня `reference_date`; деградация блока — через `patch` падающего сервиса, проверяется `FAILED` у одного блока и `OK` у остальных; пустая база → все блоки `EMPTY`; счётчик вызовов `get_money_layers` == 1 за сборку (NFR-1, защита от повторного расчёта модели).

**Шаг 6. Карточки-двери.** `app/components/panel_cards.py` + секции CSS в `panel.css` (`.pnl-slots` grid 4+1 по эскизу, `.pnl-door`, `.pnl-door-head`, `.pnl-days`, `.pnl-day`, `.pnl-flagline`, `.pnl-flagline-strong`, `.pnl-bar`, `.pnl-bar-thin`, `.pnl-grp`, `.pnl-big-sum`, `.pnl-mini-slot`, `.pnl-wish`). Вертикальный ритм карточки «Цели» выравнивается (`margin-top:auto` у строки подушки) — заметка vision-критика эскиза.

**Шаг 7. Перестройка щитка.** `dashboard.py`: layout → шапка + график + `html.Div(id="dashboard-cards-row")`; удаляются `_build_transactions_split_table`, `_build_cushion_card_readonly`, `_build_empty_state`, импорты `build_wishlist_widget`/`CushionService`/`RecentTransaction`, четыре clientside-триггера пустых состояний таблиц; `_load_dashboard_components` → 3 значения через `DashboardPanelService`; оба колбэка (`load_dashboard_data`, `refresh_dashboard_after_crud`) → 3 Output'а; новый clientside-триггер двери Wishlist. `custom.css`: снимаются `.db-left-col`, `.db-right-col`, `.db-main-row`, `.dashboard-split-table`, правило `.db-right-col > div:last-child`.

**Шаг 8. Снятие сайдбара с дашборда + защита AC-9.** `main.py`: `sidebar-slot` + `render_sidebar_slot`. `profile_modal.py`: единственный вход открытия — `open-profile-trigger`. `sidebar.py`: clientside-триггер на `sidebar-profile-container`, guard в `highlight_active_sidebar`, guard в `update_sidebar_profile`. `sidebar.css`: `.sidebar-column.d-none` не должен оставлять gap — `.app-layout { gap }` заменяется на `margin-left` у `.main-content` либо `.sidebar-column:empty { display:none }`.

**Шаг 9. Приёмники контекста (FR-3).** `main.py`: `handle_panel_query_params` + два Store'а. `calendar.py`: `Input("calendar-focus-date")` в существующий `load_and_navigate_calendar`, ключ `focus_date` в `calendar-state`, класс `calendar-day-focused` в `_build_day_cell`, стиль в `calendar.css`. `goals.py`: якорные id карточек в `_build_goal_card`, узел `goals-focus-anchor` в layout, колбэк `apply_goal_focus`, clientside-скролл. `transactions.py` и `analytics.py` — **без правок**: `apply_url_date_filter` и дефолт `analytics-period-store` уже покрывают AC-2.

**Шаг 10. Тесты UI карточек.** `tests/test_panel_cards_ui.py` в стиле `test_dashboard_panel_ui.py` (хелперы `iter_tree`/`joined_text`/`find_by_id`, фикстуры-словари, относительные даты, БД нет): все пять карточек присутствуют при любом статусе (FR-2/AC-5); пустые состояния без числовых артефактов (нет `₽`, нет `0%`); AC-7 в двух вариантах фикстуры (минимум > 0 → нет класса `pnl-flagline-strong`; минимум ≤ 0 → класс есть); href'ы дверей (AC-2, AC-8); отсутствие слова «Доход» в дереве карточки Аналитика; отсутствие карточки подушки в ряду и наличие строки подушки внутри карточки Цели (AC-4).

**Шаг 11. Адаптация существующих тестов.** `test_dashboard_callbacks.py` — 5 Output'ов → 3, контракт декоратора; `test_profile_modal_callbacks.py` — вход через Store вместо `sidebar-profile-container`.

**Шаг 12. Замер NFR-1 и статика.** Замер как в куске 1 (наполненная локальная база, `time.perf_counter` вокруг `_load_dashboard_components`), запись в протокол. `black`, `flake8`, полный `pytest`.

**Шаг 13. Ручная проверка регрессий C-6** (юнит-тестом не ловится, KB прямо это фиксирует): навигация дашборд → каждый раздел → обратно; профиль открывается шестерёнкой на дашборде и аватаром в каждом разделе; модал wishlist открывается дверью; клик «завтра» / цель / операции / аналитика / хотелка.

## Зависимости

- Новых пакетов нет; версии не меняются (Dash 2.17.1, SQLAlchemy 2.0.23).
- Внутренние: `panel_service` → `MoneyLayersService`, `GoalService`, `AllocationService`, `CushionService`, `DashboardService`, `AnalyticsService`, `WishlistService`. Все существуют, ни один не меняется (C-3).
- Схема БД не меняется, миграций нет (C-4).
- Порядок шагов жёсткий: 1 → 2 (иначе кусок 1 красный), 3 → 4 → 5, 6 → 7, 7 → 8 (снятие сайдбара безопасно только после перестройки layout), 9 после 8 (Store'ы объявляются в том же правке `main.py`).

## Риски и mitigation

| # | Риск | Вероятность | Mitigation |
|---|---|---|---|
| R1 | **Снятие сайдбара ломает модал профиля на дашборде** (`sidebar-profile-container` — прямой Input, элемента больше нет в DOM) → AC-9 красный. Это тот же класс регрессий C-6, только «наоборот»: не добавили элемент, а убрали. | Высокая, если не заметить | Шаг 8 переводит ОБА входа на `open-profile-trigger`; в `handle_profile_modal` не остаётся ни одного Input на условно-присутствующий элемент. Ручная проверка — шаг 13. |
| R2 | **Второй вход в модал wishlist отключает колбэк** (`open-wishlist-modal-btn` уже сегодня dashboard-only и работает лишь потому, что он единственный Input). | Высокая, если делать прямым Input'ом | Дверь Wishlist подключена Store-триггером `open-wishlist-trigger`; старый `open-wishlist-modal-btn` исчезает вместе с виджетом, но Input оставлен с guard'ом на случай возврата виджета в кусок 3. |
| R3 | **Расширение окна модели сдвигает маркер минимума на графике** — «вчера» может оказаться минимумом → визуальная регрессия C-7. | Средняя | `min_free`/`min_free_date` считаются по `window_days(...)`; отдельный тест «минимум не уезжает на день lookback». |
| R4 | **Сбор операций 1-го числа месяца** — `collect_start = _month_start(ref)` не покрывает `ref-1` (последний день прошлого месяца), «вчера» посчитается без операций. | Средняя (1 день в месяц) | `collect_start = min(_month_start(ref), ref - WINDOW_LOOKBACK_DAYS)`; тест на фикстуре «сегодня = 1-е число» через относительные даты. |
| R5 | **Деградация NFR-1**: 4 дополнительных блока данных на рендер. Оценка: `_goals_block` ~3 запроса + чистый расчёт, `_operations_block` 2 запроса с `LIMIT 3`, `_analytics_block` 1 GROUP BY по месяцу, `_wishlist_block` 1 запрос с `LIMIT 5` → ~7 коротких запросов поверх модели слоёв, все на одной открытой сессии. Ожидаемая деградация с 13 мс до ~25–40 мс — два порядка от бюджета 2 с. | Низкая | Замер шага 12; тест-счётчик «`get_money_layers` вызван один раз»; Plotly в карточках не используется (мини-структура — CSS-полоска), пятый график не появляется. |
| R6 | **Кеш кажется нужным** и вносится «на всякий случай» → устаревшие цифры карточек против свежей шапки (та самая P1-боль). | Средняя | Решение зафиксировано в докстринге сервиса: кеша НЕТ, инвалидация только через `global-transaction-trigger`, который и так перерисовывает щиток целиком. |
| R7 | **`get_recent_transactions` не отдаёт виртуальные recurring-инстансы** (только материализованные) — эскиз показывает «Аренда 🔁». Карточка может выглядеть беднее эскиза. | Средняя | Осознанное ограничение: менять `DashboardService` запрещено (C-3), а карточка — фрагмент, не таблица. Ограничение фиксируется в докстринге `_operations_block`; предстоящие регулярные видны в тултипе легенды графика и в календаре. Если владелец сочтёт критичным — отдельное решение, не молча. |
| R8 | **`?focus_date` применяется повторно** после F5 (Store хранит состояние). | Средняя | `url.search` очищается в `handle_panel_query_params`; значение Store timestamp-обёрнуто; guard на пустой Store в приёмнике. |
| R9 | **Фокус цели требует переписать раздел** (карточки не имеют id) → нарушение C-1. | Низкая | Правка минимальна: якорный `id` в `_build_goal_card` + один невидимый узел + один колбэк. Логика allocation/приоритетов не трогается. |
| R10 | **Ряд из 5 карточек не влезает в grid эскиза (4 колонки)** — эскиз держал Wishlist отдельной полосой снизу. | Средняя | Раскладка эскиза воспроизводится буквально: `.pnl-slots` — 4 двери в grid, Wishlist — `.pnl-wish` полосой под ними. Все пять присутствуют (FR-2 требует представительство, не равный размер: «иерархия ответов определяет размер и позицию, но не факт присутствия»). |
| R11 | **`.app-layout { gap: 24px }` оставляет пустое место** при скрытом сайдбаре. | Низкая | Правило `.sidebar-column:empty { display: none }` + проверка на дашборде вручную. |

## Requirements Traceability Matrix (RTM)

| # | Requirement (дословно) | Секция spec | Реализация в solution | Тип |
|---|---|---|---|---|
| 1 | «под шапкой и графиком видны карточки пяти предметных разделов (Календарь, Цели, Операции, Аналитика, Wishlist)» | AC-1, FR-1 | `build_cards_row(PanelData)` → 4 двери в `.pnl-slots` + `.pnl-wish`; `dashboard-cards-row` в layout | Visual |
| 2 | *Календарь*: «вчера / сегодня / завтра (остатки дней)» | FR-1 | `CalendarCardData.days` — ровно 3 `CalendarDaySlice` с `balance = DayLayers['forecast_balance']`; поле `yesterday` модели | Visual |
| 3 | «маркер просадки — день минимума слоя «Свободно» окна модели» | FR-1 | `dip_date`/`dip_free` из `layers['min_free_date']`/`min_free`; `.pnl-flagline` показывается всегда | Visual |
| 4 | «при минимуме ≤ 0 маркер визуально усиливается (факт знака числа, не порог-вердикт)» | FR-1, AC-7 | `dip_is_strong = dip_free <= DIP_STRONG_THRESHOLD (Decimal("0"))` → класс `pnl-flagline-strong` | Edge |
| 5 | Календарь-дверь: «календарь на кликнутом дне» | FR-1, FR-3, AC-2 | `href = /calendar?focus_date=<ISO>` → `calendar-focus-date` Store → `load_and_navigate_calendar` переставляет месяц + класс `calendar-day-focused` | Integration |
| 6 | *Цели*: «топ-цель с прогрессом» | FR-1, AC-4 | `top_goal_name/progress/current/target/target_date`; `.pnl-bar` | Visual |
| 7 | «сводка остальных (вида «по плану / 1 отстаёт»)» | FR-1, AC-4 | `others_count`, `others_behind_count`, `others_summary`; источник — `AllocationResult['shortfall'] > 0` | Visual |
| 8 | «статус подушки одной строкой + подушка живёт внутри этой карточки и отдельной не имеет» | FR-1, AC-4 | `cushion_is_configured/progress/label` + `.pnl-bar-thin`; `_build_cushion_card_readonly` и `dashboard-cushion-card` удалены | Visual |
| 9 | Цели-дверь: «цели с фокусом на кликнутой» | FR-1, FR-3, AC-2 | `top_goal_href = /goals?goal=<id>` → `goals-focus-goal` Store → `apply_goal_focus` + якорные id карточек | Integration |
| 10 | *Операции*: «2-3 недавние + 2-3 предстоящие» | FR-1 | `OPERATIONS_PER_GROUP = 3`; `get_recent_transactions(limit=3)`, `get_upcoming_transactions(limit=3)` | Visual |
| 11 | Операции-дверь: «список операций с фильтром периода» | FR-1, FR-3, AC-2 | `recent_href = /transactions?start=<1-е>&end=<сегодня>`, `upcoming_href = ?start=<сегодня>&end=<конец месяца>`; приёмник `apply_url_date_filter` уже существует (0023) | Integration |
| 12 | *Аналитика*: «цифра месяца — топ-категория расходов + мини-структура» | FR-1 | `month_total`, `top_category_*`, `structure` (`MINI_STRUCTURE_CATEGORIES = 3` + «Прочее»); `.pnl-big-sum`, `.pnl-mini-slot` | Visual |
| 13 | «Показатель «Доходы за месяц» НЕ возвращается (решение владельца 2026-08-25)» | FR-1, out of scope | `AnalyticsCardData` не содержит поля доходов; `_analytics_block` вызывает только `get_expenses_by_category`; тест «слова «Доход» нет в дереве карточки» | UX |
| 14 | Аналитика-дверь: «аналитика текущего месяца» | FR-1, AC-2 | `href = "/analytics"`; `analytics-period-store` дефолт `{"type": "month"}` — раздел не правится (C-1) | Integration |
| 15 | *Wishlist*: «компактный виджет (не пункт меню — представительство сохраняется)» | FR-1 | `.pnl-wish` — полоса под рядом дверей (раскладка эскиза v3); в `MAIN_NAV_ITEMS` пункта нет и не появляется | Visual |
| 16 | «Дверь двухуровневая: заголовок/тело карточки → модал управления wishlist» | FR-1, AC-8 | `panel-wishlist-door` (n_clicks) → clientside `timestamp_trigger` → `open-wishlist-trigger` Store → `open_wishlist_modal` | Integration |
| 17 | «клик по конкретной хотелке → календарь в режиме покупок с фокусом на ней» | FR-1, AC-8 | `WishlistCardRow.href = /calendar?wishlist_item=<id>` → `wishlist-active-item` → существующий wishlist-mode календаря | Integration |
| 18 | *Настройки*: «служебная иконка (шестерёнка шапки, есть с куска 1), не карточка» | FR-1 | `_build_settings_cog` куска 1 не меняется; карточки «Настройки» нет | Visual |
| 19 | **FR-2** «Каждый предметный пункт меню имеет карточку» | FR-2 | Пять карточек ↔ `MAIN_NAV_ITEMS` (Календарь, Операции, Аналитика, Цели) + Wishlist | UX |
| 20 | «на дашборде меню нет — сайдбар с дашборда убирается, карточки и есть навигация» | FR-2, AC-1 | `render_sidebar_slot`: на `/`, `/dashboard` → `[]` + `sidebar-column d-none` | Visual |
| 21 | «На остальных страницах сайдбар остаётся» | FR-2, AC-1 | `render_sidebar_slot` → `create_sidebar()` для `/calendar`, `/goals`, `/transactions`, `/analytics`; тест на возвращаемое значение по pathname | Integration |
| 22 | **FR-3** «Клик по элементу карточки открывает раздел в состоянии, соответствующем клику» | FR-3 | Все двери — `dcc.Link` с контекстом в query params; `handle_panel_query_params` раскладывает по Store'ам | Integration |
| 23 | «завтра» → календарь с завтрашним днём | FR-3, AC-2 | `days[2].href = /calendar?focus_date=<ref+1>` | Integration |
| 24 | «Дух важнее буквы»: позиционная привязка фрагмента — не требование | FR-3 | Раскладка эскиза v3 (ряд дверей), а не копия позиций разделов; фиксируется в докстринге `build_cards_row` | UX |
| 25 | **FR-4** «Онбординг-тост нулевого баланса сохраняет своё поведение» | FR-4, AC-6 | `_build_balance_banner` + `toggle_balance_toast` + `persist_toast_dismissal` не трогаются; баннер остаётся первым узлом layout дашборда | Integration |
| 26 | «Прочие сироты инвентаризации закрыты ранее» | FR-4 | Вход в «Сверку» — кнопки шапки куска 1 (не трогаются); «Доходы за месяц» — см. #13 | UX |
| 27 | **FR-5** «У нового пользователя (0 операций, 0 целей, пустой wishlist) каждая карточка показывает спроектированное пустое состояние» | FR-5, AC-5 | `CardStatus.EMPTY` на каждый блок; текст-смысл раздела в `build_*_card` | Visual |
| 28 | «без числовых артефактов» | FR-5, AC-5 | Ветка `EMPTY` не рендерит ни `format_rub`, ни проценты; тест «нет «₽» и нет «%» в дереве пустой карточки» | Edge |
| 29 | «карточки не исчезают (конституция FR-2)» | FR-5, AC-5 | `build_cards_row` строит пять карточек безусловно; тест «5 карточек при `is_new_user=True`» | Visual |
| 30 | **FR-6** «Карточки питаются данными, согласованными с шапкой и графиком: там, где применимо (карточка «Календарь»), — той же моделью слоёв куска 1» | FR-6, AC-3 | `_calendar_block(layers)` — чистая функция от той же `MoneyLayersData`, ноль запросов | Integration |
| 31 | «цифры карточек не противоречат шапке/графику» | FR-6, AC-3 | Один `get_money_layers` за сборку (тест-счётчик); `recent/upcoming_href` — те же диапазоны, что у выборки строк | Perf/Integration |
| 32 | «Открытие дашборда тянет фрагменты всех разделов — стратегия загрузки (сколько вызовов, кеширование/ленивая подгрузка) проектируется явно» | FR-6 | Секция «Обзор решения» п.1 + докстринг `DashboardPanelService`: 1 сессия (было 4), 1 модель слоёв, ~7 коротких запросов, кеша нет намеренно, ленивости нет (ряд карточек — первый экран) | Perf |
| 33 | **NFR-1** «не медленнее ориентира куска 1: < 2 секунд» | NFR-1, AC-10 | Замер шага 12 как в куске 1; оценка ~25–40 мс; Plotly в карточках не используется | Perf |
| 34 | «в куске 1 рендер был 13 мс на 120 операциях, деградация должна быть объяснима» | задача | R5: покомпонентная оценка запросов, число сессий уменьшается с 4 до 1 | Perf |
| 35 | **NFR-2** «Сбой сборки данных одной карточки не обрушивает дашборд целиком: карточка деградирует с индикацией» | NFR-2 | `try/except` на каждый блок → `CardStatus.FAILED` → текст «Не удалось загрузить раздел» при живой двери | Edge |
| 36 | «сбой логируется с трейсбеком (`logger.opt(exception=True)`)» | NFR-2 | Идиома во всех новых except-ветках; попутно заменяются два `exc_info=True` в правимых файлах | Edge |
| 37 | «Сбой расчёта базовой модели остатка не глотается» | NFR-2 | `get_money_layers` вызывается ВНЕ try/except в `get_panel_data` | Edge |
| 38 | **C-1** «Разделы содержательно не пересматриваются; допустимы только минимальные приёмники контекста» | C-1 | `calendar.py`: +1 Input, +1 ключ в существующем Store, +1 CSS-класс; `goals.py`: +якорные id, +1 узел, +1 колбэк; `transactions.py`, `analytics.py` — 0 правок | Integration |
| 39 | **C-2** «Decimal для денег, session-контракт flush()/commit(), сервисы не знают о Dash» | C-2 | `PanelData` — только `Decimal`/`date`/`str`; `DashboardPanelService` read-only, ни `flush`, ни `commit`; импортов Dash в сервисе нет | Integration |
| 40 | **C-3** «Существующее поведение сервисов не меняется; полный прогон тестов остаётся зелёным» | C-3, AC-10 | Кроме `MoneyLayersService` (разрешён C-5) ни один сервис не правится — только вызывается; шаг 12 | Integration |
| 41 | **C-4** «Схема БД не меняется» | C-4 | Миграций нет; `app/models/database.py` не в blast radius | Integration |
| 42 | **C-5** «Контракт MoneyLayersService/MoneyLayersData МОЖНО менять, но шапка и график продолжают работать, а инвариант «сумма слоёв == остаток» сохраняется» | C-5 | Шаг 1 (+`yesterday`/`tomorrow`/`window_start`) и шаг 2 (`window_days()` для графика); инвариант держится по построению — `_split_day` не меняется; тест инварианта на расширенном окне | Integration |
| 43 | **C-6** «Новые интерактивные элементы дашборда не ломают колбэки на других страницах» | C-6, AC-9 | Двери-переходы — `dcc.Link` (Input'ов нет вовсе); дверь Wishlist — clientside → Store; вход профиля через сайдбар тоже переведён на Store (R1); ручная проверка шаг 13 | Integration |
| 44 | **C-7** «Шапка и график куска 1 визуально и поведенчески не регрессируют… 47 тестов остаются зелёными или осознанно адаптируются» | C-7, AC-10 | `window_days()` изолирует расширение окна; адаптация — только фикстуры `test_dashboard_panel_ui.py` (шаг 2), причина документируется | Visual |
| 45 | «нет вердикта-светофора, нет приветствия, шапка не дверь — остаются в силе» | C-7 | `build_free_header` не правится; тесты `TestFreeHeader` остаются | Visual |
| 46 | **AC-1** «сайдбара/меню на дашборде нет» | AC-1 | см. #20 | Visual |
| 47 | **AC-2** полный набор четырёх переходов | AC-2 | см. #5, #9, #11, #14 | Integration |
| 48 | **AC-3** «остаток «сегодня» в карточке Календарь равен значению модели слоёв на сегодня (тому же, из которого построена шапка) — проверено unit-тестом» | AC-3 | Тест шага 5: `panel["calendar"]["days"][1]["balance"] == panel["layers"]["today"]["balance"]` и `== forecast_balance` дня `reference_date` | Perf/Integration |
| 49 | **AC-4** «readonly-карточка подушки старой раскладки снята» | AC-4 | `_build_cushion_card_readonly`, `dashboard-cushion-card`, `.db-right-col` удалены | Visual |
| 50 | «split-таблицы операций старой раскладки заменены карточкой Операции» | AC-4 | `_build_transactions_split_table`, `dashboard-recent-transactions`, `dashboard-upcoming-transactions`, `empty-recent-add-btn`, `empty-upcoming-add-btn`, `.dashboard-split-table` удалены | Visual |
| 51 | **AC-5** «Дано: чистая база (онбординг пропущен)… все пять карточек на месте и показывают спроектированные пустые состояния» | AC-5 | см. #27–#29; тест на `PanelData` с пустой базой | Edge |
| 52 | **AC-6** «Онбординг-тост появляется и ведёт себя так же, как до перестройки» | AC-6 | см. #25; `test_dashboard_callbacks.py::TestToggleBalanceToastProfileUpdated` остаётся зелёным без правок | Integration |
| 53 | **AC-7** «на фикстуре с минимумом > 0 — без усиления; ≤ 0 — усилен — проверено unit-тестами» | AC-7 | Две фикстуры-словаря в `test_panel_cards_ui.py`; ассерт на наличие/отсутствие `pnl-flagline-strong` | Edge |
| 54 | **AC-8** оба уровня двери Wishlist | AC-8 | см. #16, #17 | Integration |
| 55 | **AC-9** «Модал профиля открывается со всех страниц обоими входами (аватар сайдбара на не-дашборд страницах, шестерёнка шапки на дашборде)» | AC-9 | Шаг 8: единственный Input открытия — `open-profile-trigger`, оба источника пишут в него | Integration |
| 56 | **AC-10** «Новые данные и UI покрыты unit-тестами; полный прогон pytest зелёный; black + flake8 без новых замечаний; рендер в NFR-1» | AC-10 | Шаги 5, 10, 11, 12 | Perf |
| 57 | design.md: «Иерархия ответов определяет размер и позицию карточки, но не факт присутствия» | design.md | Wishlist — полоса, не равная дверь; все пять присутствуют | UX |
| 58 | design.md: «Служебные экраны без предметного содержания (настройки, справка) — иконки, не карточки» | design.md | см. #18 | UX |
| 59 | Эскиз v3: `.door` + `.door-head` (иконка 26px, h3 15px/700, шеврон «→») + `.door-body` | эскиз | `_door_shell` → `.pnl-door`, `.pnl-door-head`, `.pnl-door-body`; цветная шина гнезда 3px через `--pnl-slot` | Visual |
| 60 | Эскиз v3: цвета гнёзд — Календарь `#2ecc71`, Цели `#3498db`, Операции `#c3ccd4`, Аналитика `#f39c12` | эскиз | CSS-переменные `--pnl-slot`/`--pnl-slot-soft` на `.pnl-door-<slot>`; зелёный/синий берутся из существующих `--pnl-free`/`--pnl-reserve` (единый источник правды палитры) | Visual |
| 61 | Эскиз v3: три окошка `.day`, у сегодняшнего фон `#eafaf1` / бордер `#c6ebd6` и класс `.today` | эскиз | `.pnl-day`, `.pnl-day-today`; `CalendarDaySlice.is_today` | Visual |
| 62 | Эскиз v3: подпись окошка «2 операции» / «план» | эскиз | `CalendarDaySlice.operations_note` — считается по операциям дня из `layers` (без запроса) | Visual |
| 63 | Эскиз v3: `.flagline` — жёлтая полоса «Ближайшая просадка: **4 сент**, остаток **9 800 ₽**» | эскиз | `.pnl-flagline` + `format_date_human(dip_date)` + `format_rub(dip_free)`; усиление — `.pnl-flagline-strong` | Visual |
| 64 | Эскиз v3: «102 000 из 150 000 ₽ · к 15 окт» под баром топ-цели | эскиз | `top_goal_current/target/target_date` + `format_rub`/`format_date_human` | Visual |
| 65 | Эскиз v3: «Ещё 2 цели — по плану»; подушка мелким кеглем с `.bar.thin` (52% ширины, 4px) | эскиз | `others_summary`, `.pnl-pillow`, `.pnl-bar-thin` | Visual |
| 66 | Эскиз v3: заметка vision-критика «выровнять вертикальный ритм карточки Цели» | осадок, design.md | `margin-top:auto` у блока подушки внутри `.pnl-door-body` (шаг 6) | Visual |
| 67 | Эскиз v3: группы `.grp` «НЕДАВНИЕ» / «ПРЕДСТОЯЩИЕ», маркер 🔁 у регулярных | эскиз | `.pnl-grp`; `OperationRow.is_recurring` | Visual |
| 68 | Эскиз v3: «78 400 ₽» `.big-sum` + подпись «расходы августа» | эскиз | `month_total` + `month_label` (родительный падеж через `MONTH_NAMES_RU_GENITIVE`) | Visual |
| 69 | Эскиз v3: «Продукты — 24 300 ₽ · 31%» + «крупнейшая категория месяца» | эскиз | `top_category_name/total/share`; `.pnl-top-cat` | Visual |
| 70 | Эскиз v3: мини-структура — 3 категории + «Прочее» + «из 78 400 ₽» | эскиз | `structure` (`MINI_STRUCTURE_CATEGORIES = 3`, остаток в «Прочее»); CSS-полоска, без Plotly (R5) | Visual |
| 71 | Эскиз v3: `.wish` — полоса с левым зелёным бордером 3px, тег «WISHLIST», название + цена | эскиз | `.pnl-wish`, `.pnl-wish-tag`, `.pnl-wish-item`, `.pnl-wish-price` | Visual |
| 72 | Эскиз v3: `.door:focus-visible { outline: 2px solid var(--reserve) }`, `tabindex` на дверях | эскиз | `dcc.Link` фокусируем нативно; `.pnl-door:focus-within` outline в `panel.css` | UX |
| 73 | Эскиз v3: адаптив `@media (max-width:1180px)` → 2 колонки, `680px` → 1 колонка | эскиз | Те же брейкпоинты в `panel.css` (полная мобильная адаптация — Epic-08) | Visual |
| 74 | Эскиз v3: `@media (prefers-reduced-motion: reduce) { *{transition:none} }` | эскиз | Секция «ДОСТУПНОСТЬ» `panel.css` расширяется на `.pnl-door` | UX |
| 75 | Out of scope: «выбор произвольного месяца в аналитике — дверь ведёт на текущий месяц» | out of scope | `href = "/analytics"` без params; `analytics.py` не правится | UX |
| 76 | Out of scope: «Раздел «Настройки» — заглушка остаётся» | out of scope | `/settings` не добавляется в роутинг; шестерёнка ведёт в модал профиля | UX |
| 77 | Out of scope: «Полоска-меню вместо сайдбара на остальных страницах» | out of scope | `create_sidebar()` не переписывается — только условно рендерится | UX |
| 78 | Out of scope: «Анимация переходов дашборд↔раздел» | out of scope | Переходы — обычные `dcc.Link`, без CSS-анимаций входа | UX |
| 79 | Edge (не в спеке, найден при проектировании): вчера = последний день прошлого месяца при `ref` = 1-е число | R4 | `collect_start = min(_month_start(ref), ref - WINDOW_LOOKBACK_DAYS)` + тест | Edge |
| 80 | Edge: `get_recent_transactions` не отдаёт виртуальные recurring-инстансы, эскиз показывает 🔁 | R7 | Ограничение зафиксировано в докстринге `_operations_block`; C-3 запрещает менять `DashboardService` | Edge |

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
| `app/components/dashboard.py` | Layout → шапка+график+`dashboard-cards-row`; удаляются `_build_transactions_split_table`, `_build_cushion_card_readonly`, `_build_empty_state`; `_load_dashboard_components` 5→3 значения; оба колбэка 5→3 Output'а; 4 clientside-триггера пустых состояний удаляются, 1 (дверь Wishlist) добавляется; импорты `build_wishlist_widget`, `CushionService`, `DashboardService`, `RecentTransaction`, `Decimal` вычищаются | ядро задачи |
| `app/main.py` | `sidebar-slot` + `render_sidebar_slot`; `handle_calendar_query_params` → `handle_panel_query_params` (+2 Output'а); 3 новых `dcc.Store` | FR-2, FR-3 |
| `app/components/sidebar.py` | clientside-триггер на `sidebar-profile-container`; guard в `highlight_active_sidebar` и `update_sidebar_profile`; `exc_info=True` → `logger.opt(exception=True)` | сайдбар стал условным |
| `app/components/profile_modal.py` | `Input("sidebar-profile-container")` убирается — единственный вход открытия `open-profile-trigger`; `exc_info` → `logger.opt` | **AC-9 / C-6, R1** |
| `app/components/wishlist.py` | `build_wishlist_widget` удаляется (место заняла карточка); `open_wishlist_modal` получает второй вход через Store + guard'ы | AC-8, C-6 |
| `app/components/calendar.py` | `Input("calendar-focus-date")` в `load_and_navigate_calendar`; ключ `focus_date` в `calendar-state`; класс `calendar-day-focused` в `_build_day_cell` | FR-3, AC-2 |
| `app/components/goals.py` | якорные id в `_build_goal_card`; узел `goals-focus-anchor`; колбэк `apply_goal_focus` | FR-3, AC-2 |
| `app/components/__init__.py` | снятие `build_wishlist_widget` из импортов и `__all__` | удаление функции |
| `app/services/money_layers_service.py` | окно от `ref-1`; `collect_start` учитывает lookback; `min_free` по `window_days`; `yesterday`/`tomorrow`/`window_start`; хелпер `window_days` | C-5, AC-3 |
| `app/schema/money_layers.py` | `WINDOW_LOOKBACK_DAYS`, 3 новых поля `MoneyLayersData` | C-5 |
| `app/schema/__init__.py`, `app/services/__init__.py` | реэкспорт новых схем и сервиса | конвенция проекта |
| `app/assets/panel.css` | секции 3 (двери) и 4 (wishlist-полоса), правки адаптива и `prefers-reduced-motion` | эскиз v3 |
| `app/assets/custom.css` | удаление `.db-left-col`, `.db-right-col`, `.db-main-row`, `.dashboard-split-table`; правка `.db-page` | старая раскладка 8/4 |
| `app/assets/sidebar.css`, `app/assets/calendar.css` | `.sidebar-column:empty { display:none }`; `.calendar-day-focused` | R11, FR-3 |

### Связанные файлы

**Тесты, требующие адаптации**
- `tests/test_dashboard_panel_ui.py` (47 тестов, C-7) — фикстуры `days` расширяются днём lookback; ассерты про ось/минимум сохраняются
- `tests/test_money_layers_service.py` — длина окна, инвариант, минимум, `yesterday`
- `tests/test_dashboard_callbacks.py` — `load_dashboard_data` 5→3 Output'а, контракт декоратора
- `tests/test_profile_modal_callbacks.py` — вход через Store вместо `sidebar-profile-container`

**Файлы БЕЗ правок, но в зоне контрактного риска (проверить прогоном)**
- `app/components/transactions.py` — `apply_url_date_filter` становится приёмником двери Операций
- `app/components/analytics.py` — дефолт `analytics-period-store` становится приёмником двери Аналитики
- `app/components/calendar_wishlist.py` — `wishlist-active-item` становится приёмником второго уровня двери Wishlist
- `app/components/transaction_modals.py` — `global-transaction-trigger`, `modal-source`, `create-modal`: `refresh_dashboard_after_crud` меняет арность Output'ов
- `app/components/onboarding_wizard.py` — `profile-updated` → `load_dashboard_data`
- `app/services/dashboard_service.py`, `analytics_service.py`, `goal_service.py`, `allocation_service.py`, `cushion_service.py`, `wishlist_service.py` — только вызываются (C-3)

**Общие component ID / Store'ы, затронутые семантически**
- новые: `sidebar-slot`, `dashboard-cards-row`, `panel-wishlist-door`, `open-wishlist-trigger`, `calendar-focus-date`, `goals-focus-goal`, `goals-focus-anchor`
- удаляемые: `dashboard-recent-transactions`, `dashboard-upcoming-transactions`, `dashboard-cushion-card`, `empty-recent-add-btn`, `empty-upcoming-add-btn`, `open-wishlist-modal-btn` (вместе с виджетом)
- меняющие роль: `open-profile-trigger` (был вторым входом — стал единственным), `wishlist-active-item` (был только из calendar — стал и из карточки), `dashboard-period` (остаётся guard'ом клика по графику)

**Документация (после реализации)**
- `.obsidian-docs/knowledge-bank/modules/ui-components.md` — секции Dashboard-щиток, Sidebar; новая секция Panel Cards
- `.obsidian-docs/knowledge-bank/modules/services.md` — `DashboardPanelService`, эволюция `MoneyLayersService`
- `.obsidian-docs/knowledge-bank/modules/schema.md` — `app/schema/panel.py`
- `.obsidian-docs/knowledge-bank/modules/routing.md` — `?focus_date=`, `?goal=`
- `.obsidian-docs/knowledge-bank/patterns/callbacks.md` — кейс «удаление элемента ломает колбэк» (обратная сторона C-6)
- `memory/spec-context/epic-11.md` — удалить применённые записи с тегом `for: design-loop`

### Проверить после реализации

1. **AC-9 вручную**: профиль открывается шестерёнкой на `/dashboard` И аватаром на каждом из `/calendar`, `/goals`, `/transactions`, `/analytics` — после снятия сайдбара с дашборда (R1, юнит-тестом не ловится).
2. **AC-8 вручную**: клик по телу карточки Wishlist открывает модал; клик по хотелке ведёт в режим покупок календаря с фокусом.
3. **AC-1 вручную**: сайдбара на дашборде нет и он не оставляет пустой колонки; на четырёх разделах сайдбар на месте с корректной подсветкой активного пункта.
4. **AC-2 вручную**: все четыре перехода; повторный клик по тому же элементу срабатывает (timestamp-обёртка); F5 после перехода не применяет контекст заново (R8).
5. **C-7**: график полос визуально идентичен куску 1 — первая подпись оси = сегодня, маркер минимума на том же дне (R3).
6. **NFR-1**: замер `_load_dashboard_components` на наполненной локальной базе, запись в протокол; сверка с 13 мс куска 1.
7. **AC-3/AC-7**: `pytest tests/test_panel_service.py tests/test_panel_cards_ui.py`.
8. **AC-10**: полный `pytest` (693 + новые), `black --check`, `flake8`.
9. **Edge 1-го числа** (R4): фикстура «сегодня = 1-е число месяца» — «вчера» показывает остаток с учётом операций прошлого месяца.
10. **NFR-2**: `patch`-тест падающего блока — дашборд рендерится, одна карточка деградирована, в логах трейсбек.
