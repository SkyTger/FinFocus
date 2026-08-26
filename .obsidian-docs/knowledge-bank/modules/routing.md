# modules/routing.md

## Суть
URL-based routing через Dash Location component и display_page callback

## Ключевые файлы
- `app/main.py:70-109` - `display_page()` callback и route mapping

## Роутинг

**Маршруты**:
- `/` или `/dashboard` → Dashboard overview
- `/calendar` → Cash calendar (stub)
- `/goals` → Savings goals (stub)
- `/transactions` → Transaction management (CRUD)
- `other` → 404 page

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

**Главный layout** (`app/main.py:41-67`):
```
Container (fluid)
  └── Row
       ├── Col (width=3, fixed sidebar)
       │    └── Sidebar component
       └── Col (width=9, margin-left=25%)
            ├── page-header (заголовок страницы)
            └── page-content (динамический контент)
```

**URL Component**:
```python
dcc.Location(id="url", refresh=False)  # SPA режим, без перезагрузки
```

## Навигация

**Sidebar links** → изменяют URL → `display_page()` callback → рендер нового контента

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

**Фаза 3** (Кассовый календарь):
- Активировать `/calendar` маршрут
- Создать `create_calendar_layout()` в `app/components/calendar.py`

**Фаза 5** (Накопительные цели):
- Активировать `/goals` маршрут
- Создать `create_goals_layout()` в `app/components/goals.py`

**Батч 3** (Analytics):
- Добавить подстраницы для фильтров (e.g., `/transactions?month=2025-01`)
- Query parameters через `dcc.Location` search property

---

Детали: `architecture.md` (Routing Flow), Dash Multi-Page Apps: https://dash.plotly.com/urls
