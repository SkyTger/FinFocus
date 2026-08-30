# modules/routing.md

## Суть
URL-based routing через Dash Location component и display_page callback

## Ключевые файлы
- `app/main.py:317-355` — `display_page()` callback и route mapping
- `app/main.py:129-189` — `render_nav_rail_slot()` — слот полоски-меню
- `app/main.py:224-315` — `handle_panel_query_params()` — переходы с контекстом
- `app/main.py:198-203` — clientside-триггер аватара → Store `open-profile-trigger`

## Роутинг

**Маршруты**:
- `/` или `/dashboard` → Дашборд-«щиток» (шапка, график полос, карточки-двери)
- `/calendar` → Кассовый календарь
- `/goals` → Цели накопления и финансовая подушка
- `/transactions` → Список операций
- `/analytics` → Аналитика по категориям
- `other` → 404 page

Маршрута `/settings` НЕ существует — пункт «Настройки» убран из
навигации протоколом 0031 (P1 UX-аудита: вёл на 404). Константа
`ADDITIONAL_NAV_ITEMS` ждёт появления реального маршрута в
файле-надгробии `app/components/sidebar.py`.

**Callback**:
```python
@callback(
    [Output("page-content", "children"),
     Output("page-header", "children")],
    [Input("url", "pathname")]
)
def display_page(pathname):
    if pathname == "/transactions":
        return (
            create_transactions_layout(),
            create_page_header("Операции", "Управление доходами и расходами")
        )
    # ... другие маршруты
```

## Layout Structure

**Главный layout** (`app/main.py:66-123`):
```
Container (fluid, .app-container)
  └── Div (.app-layout)
       ├── Div#nav-rail-slot (.nav-rail-column, 60px)
       │    └── наполняется render_nav_rail_slot;
       │       на дашборде ПУСТ — колонку скрывает
       │       CSS-правило .nav-rail-column:empty
       └── Div (.main-content)
            ├── page-header (заголовок страницы)
            └── page-content (динамический контент)
  + глобальные модалы и Store'ы
```

**URL Component**:
```python
dcc.Location(id="url", refresh=False)  # SPA режим, без перезагрузки
```

## Навигация

**Ссылки полоски-меню** (`dcc.Link`) → изменяют URL → `display_page()`
callback → рендер нового контента. Полоска перерисовывается своим
слот-колбэком по тому же `Input("url", "pathname")`.

На дашборде навигации сбоку нет вовсе — её роль играют карточки-двери
щитка (Epic-11, кусок 2). Переходы с контекстом (`?focus_date=`,
`?goal=`, `?wishlist_item=`, `?open_recon=1`) обслуживает
`handle_panel_query_params`.

**Пример flow**:
```
User clicks "Transactions" link (href="/transactions")
  ↓
dcc.Location updates pathname
  ↓
display_page(pathname="/transactions") triggered
  ↓
Returns create_transactions_layout() + page header
  ↓
page-content updated with Transactions component
```

## Переходы с контекстом и владение url.search (Протокол 0030)

`handle_panel_query_params` (app/main.py) разбирает query params дверей
щитка и раскладывает по Store'ам, очищая search:
- `/calendar?open_recon=1` → open-recon-trigger (было, 0028)
- `/calendar?wishlist_item=ID` → wishlist-active-item (было, 0023)
- `/calendar?focus_date=ISO` → calendar-focus-date (0030)
- `/goals?goal=ID` → goals-focus-goal (0030)

**Контракт владения** `_OWNED_SEARCH_PATHS = {"/calendar", "/goals"}`:
`/transactions?start=&end=` принадлежит `apply_url_date_filter`
(transactions.py, протокол 0023) — на нём PreventUpdate, иначе гонка двух
Output'ов на url.search сломала бы фильтр периода. Нераспознанные Store'ы
получают `no_update`, НЕ None: запись в Store (даже того же значения)
триггерит подписчиков — None в wishlist-active-item перерисовывал бы
календарь второй раз, уже без фокуса.

**Механика идемпотентности Store-фокусов** (одна на оба приёмника):
payload `{"value": ..., "ts": мс}`; приёмник реагирует ТОЛЬКО если
(1) `ctx.triggered_id` — сам Store И (2) `ts != state["focus_applied_ts"]`.
Применённый ts хранится: календарь — в `calendar-state`; цели — в узле
`goals-focus-anchor`. Приёмник целей — clientside (`apply_goal_focus` в
clientside_triggers.js): скролл к якорю `goal-card-<id>` + класс
`goal-card-focused`; серверный колбэк скроллить не умеет. Ветка except
календаря намеренно НЕ пишет ts: после сбоя загрузки повторный клик
должен сработать.

## Важное

**Multi-page architecture**:
- `suppress_callback_exceptions=True` в `Dash()` - для динамических компонентов
- Компоненты создаются только при рендере страницы (lazy initialization)

**Page Header Helper**:
```python
def create_page_header(title: str, subtitle: str = ""):
    return html.Div([
        html.H1(title, className="h2 mb-0"),
        html.P(subtitle, className="text-muted"),
        html.Hr()
    ])
```

## Планируемые изменения

Прежний список («активировать `/calendar`», «активировать `/goals`»,
«query parameters через `dcc.Location`») выполнен целиком: все пять
маршрутов работают, переходы с контекстом через query params —
протоколы 0023/0028/0030, см. раздел выше.

Открыто:
- **`/settings`** — маршрута нет, пункт убран из навигации протоколом
  0031 (P1 UX-аудита). Появится маршрут — вернуть пункт из
  `ADDITIONAL_NAV_ITEMS` (`app/components/sidebar.py`, файл-надгробие).
- **`/help`** — там же, справки пока нет.

---

Детали: `architecture.md` (Routing Flow), Dash Multi-Page Apps: https://dash.plotly.com/urls
