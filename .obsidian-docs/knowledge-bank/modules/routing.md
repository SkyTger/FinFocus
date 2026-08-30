---
name: routing
description: URL-роутинг FinFocus — display_page() elif-цепочка на 5 маршрутов, переходы с контекстом через query params (протокол 0030)
type: reference
originSessionId: a7066508-1d51-418c-a40d-a34902bde2ab
---

# modules/routing.md

## Суть
URL-based routing через Dash Location component и display_page callback

## Ключевые файлы
- `app/main.py:311-340` - `display_page()` callback и route mapping

## Роутинг

**Маршруты**:
- `/` или `/dashboard` → Dashboard-щиток
- `/calendar` → Кассовый календарь
- `/goals` → Накопительные цели
- `/transactions` → Управление операциями (CRUD)
- `/analytics` → Аналитика по категориям
- `other` → 404 page

**Callback** (реальная elif-цепочка, заголовок страницы встроен в
glass-header каждого layout — второй Output почти всегда пустой div):
```python
@callback(
    [Output("page-content", "children"), Output("page-header", "children")],
    [Input("url", "pathname")],
)
def display_page(pathname):
    if pathname is None or pathname == "/" or pathname == "/dashboard":
        return create_dashboard_layout(), html.Div(style={"display": "none"})
    elif pathname == "/calendar":
        return create_calendar_layout(), html.Div(style={"display": "none"})
    elif pathname == "/goals":
        return create_goals_layout(), html.Div(style={"display": "none"})
    elif pathname == "/transactions":
        return create_transactions_layout(), html.Div(style={"display": "none"})
    elif pathname == "/analytics":
        return create_analytics_layout(), html.Div(style={"display": "none"})
    else:
        return ...  # 404 страница
```

## Layout Structure

**Главный layout** (`app/main.py:66-123`, обновлено протоколом 0030 —
Подход B, сайдбар снят с дашборда):
```
Container (fluid, className="p-0 app-container")
  ├── dcc.Location(id="url")
  ├── Div (className="app-layout")
  │    ├── Div (id="sidebar-slot") — наполняется render_sidebar_slot();
  │    │    на дашборде остаётся пустым ([]), колонку скрывает CSS :empty
  │    └── Div (className="main-content")
  │         ├── page-header (почти всегда пустой div — заголовок встроен
  │         │    в glass-header каждого layout)
  │         └── page-content (динамический контент, display_page())
  ├── глобальные модалы (transaction, wishlist, reconciliation,
  │    onboarding, profile) — доступны с любой страницы
  └── глобальные dcc.Store (profile-updated, open-*-trigger,
       calendar-focus-date, goals-focus-goal и др.)
```

`sidebar-slot` заполняется отдельным callback'ом `render_sidebar_slot(pathname, profile_updated)`
(`app/main.py:129-134`), не жёстко зашит в layout — см. `modules/ui-components.md` (Sidebar).

**URL Component**:
```python
dcc.Location(id="url", refresh=False)  # SPA режим, без перезагрузки
```

## Навигация

**Sidebar links / карточки-двери дашборда** → изменяют URL →
`display_page()` callback → рендер нового контента

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

Все 5 маршрутов активны, query-параметры для фильтров реализованы
(см. секцию выше про переходы с контекстом, протокол 0030, и
`/transactions?start=&end=`, протокол 0023). Следующее изменение
роутинга ожидается в куске 3 Epic-11 (полоска-меню вместо сайдбара) —
без изменения набора маршрутов.

---

Детали: `architecture.md` (Routing Flow), Dash Multi-Page Apps: https://dash.plotly.com/urls
