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
