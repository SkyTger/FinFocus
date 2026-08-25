---
name: plotly-charts
description: Паттерны Plotly-графиков FinFocus — dual Y-axis, unified hover, stacked bars щитка, clickable bars, вехи-аннотации
type: reference
originSessionId: -
---

# patterns/plotly-charts.md

## Суть
Паттерны построения интерактивных Plotly графиков с Dash интеграцией

## Ключевые паттерны

### Stacked Layers Bar Pattern (Протокол 0028 — Dashboard-щиток)

График полос «Свободно/Платежи/Резерв» — три `go.Bar` в
`barmode="stack"`, легенда Plotly отключена и вынесена в HTML (нужны
развёрнутые пояснения-тултипы и доступность с клавиатуры, чего
встроенная легенда Plotly не даёт).

```python
fig = go.Figure()

# Порядок трасс снизу вверх осмыслен: свободно → платежи → резерв
for key in ("free", "payments", "reserve"):
    fig.add_trace(
        go.Bar(
            x=dates,
            y=[float(day[key]) for day in data["days"]],
            name=LAYER_LABELS[key],
            marker_color=LAYER_COLORS[key],
            customdata=[format_rub(day[key]) for day in data["days"]],
            hovertemplate=f"{LAYER_LABELS[key]}: %{{customdata}}<extra></extra>",
        )
    )

fig.update_layout(
    barmode="stack",
    showlegend=False,  # легенда — HTML вне поля графика, см. ui-components.md
    xaxis=dict(
        type="date",
        tickmode="array",
        tickvals=_axis_tickvals(dates),  # см. ниже — потолок числа подписей
    ),
    yaxis=dict(
        rangemode="tozero",
        tickformat=",.0f",
        separatethousands=True,  # против "50.001k" — P2 UX-аудита
    ),
)
```

**Явные tickvals вместо dtick** (`_axis_tickvals`, `dashboard.py`):
спорные единицы `dtick` (день/неделя/месяц) на неравномерном 45-дневном
окне дают либо слишком частую, либо слишком редкую сетку. Явный список
дат с потолком (не целью!) числа подписей:

```python
def _axis_tickvals(window_dates: list[date]) -> list[date]:
    step = max(1, ceil(len(window_dates) / MAX_X_TICKS))
    ticks = window_dates[::step]
    if window_dates[-1] not in ticks:  # правый край окна обязан быть подписан
        ticks.append(window_dates[-1])
    return ticks
```

**Пустое состояние без вызова Plotly**: на чистой базе функция
построения графика возвращает `html.Div` вместо `dcc.Graph` —
Plotly вообще не вызывается, поэтому выродившиеся оси −1..1 и
подписи вида «50.001k» физически невозможны (не «скрыты стилями», а
не могут возникнуть). Критерий пустоты — `MoneyLayersData["is_empty"]`,
НЕ «данные есть, но окно без операций» (`window_is_flat`) — в этом
случае график всё равно рисуется, просто плоской стопкой.

**Безопасность тултипов**: пользовательские описания операций
(название платежа, категория) вставляются ТОЛЬКО текстом внутри
`html.Div`. `dangerously_allow_html` и `dcc.Markdown` в этом пути
запрещены — источник текста пользовательский.

**Критичные детали**:
- Порядок трасс в стеке — продуктовое решение, не косметика (снизу
  «то, что точно ваше», сверху «то, что уже не ваше»)
- `MAX_X_TICKS` — имя-потолок, не имя-цель: предыдущее имя
  `TARGET_X_TICKS` обещало результат, которого простой `round()` не
  давал (см. `schema.md` → MoneyLayersData для истории переименования)
- Легенда и тултипы — см. `ui-components.md` → Dashboard-щиток

---

### Dual Y-Axis Pattern (Протокол 0022)

> **Статус (протокол 0028)**: график доходы/расходы+баланс, для
> которого писался этот паттерн, УДАЛЁН с дашборда вместе с
> `_build_daily_cashflow_chart`/`_build_yearly_cashflow_chart` — заменён
> графиком полос выше. Сам паттерн dual-axis остаётся общим приёмом
> Plotly и может понадобиться где-то ещё; пример ниже не переписан,
> но на дашборде больше не действует.

Две оси Y для отображения данных разного масштаба (bars vs line).

**Проблема**: Income/Expense bars имеют диапазон 0-50K, balance line 100K-150K — без dual-axis линия баланса "прилипает" к верху графика.

**Решение**: yaxis для bars (левая), yaxis2 для balance line (правая)

```python
fig = go.Figure()

# Bars на yaxis (левая)
fig.add_trace(go.Bar(
    x=dates,
    y=income_values,
    name="Доходы",
    yaxis="y",
    marker_color="#2ecc71"
))

# Line на yaxis2 (правая)
fig.add_trace(go.Scatter(
    x=dates,
    y=balance_values,
    name="Баланс",
    yaxis="y2",
    mode="lines+markers",
    line=dict(color="#3498db", width=2)
))

# Layout
fig.update_layout(
    yaxis=dict(
        title="Доходы/Расходы (₽)",
        side="left",
        showgrid=True
    ),
    yaxis2=dict(
        title="Баланс (₽)",
        side="right",
        overlaying="y",  # КРИТИЧНО: overlay над yaxis
        showgrid=False    # Избегаем наложения grid lines
    )
)
```

**Критичные детали**:
- `overlaying="y"` — ось yaxis2 накладывается на область yaxis
- `showgrid=False` для yaxis2 — избегаем visual clutter
- Разные цвета для различения
- Оба title отображаются (слева и справа)

---

### Unified Hover Pattern (Протокол 0022)

Единый tooltip для всех traces по вертикали (X-axis aligned).

**Проблема**: По умолчанию hover показывает только одну trace при наведении — нужно точно попасть на линию/bar.

**Решение**: `hovermode="x unified"` + customdata для форматирования

```python
# Customdata подготовка
customdata = [
    [
        date.isoformat(),
        format_rub(income),
        format_rub(expense),
        format_rub(balance),
        status  # "ok" | "attention" | "risk"
    ]
    for date, income, expense, balance, status in zip(...)
]

# Hover template
fig.update_traces(
    customdata=customdata,
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "Доходы: %{customdata[1]}<br>"
        "Расходы: %{customdata[2]}<br>"
        "Баланс: %{customdata[3]}<br>"
        "<extra></extra>"  # Убирает trace name из hover
    )
)

fig.update_layout(hovermode="x unified")
```

**Критичные детали**:
- `customdata` — массив данных для каждой точки (не только Y)
- `%{customdata[N]}` — доступ к элементам в hovertemplate
- `<extra></extra>` — убирает trace name из правого края hover box
- `hovermode="x unified"` — объединяет все traces по вертикали

---

### Marker Highlighting Pattern (Протокол 0022)

Специальный маркер для важной точки данных (минимум, максимум, текущее значение).

**Кейс**: Diamond маркер минимального баланса на графике.

```python
# Найти минимум
min_balance = min(balance_values)
min_date = dates[balance_values.index(min_balance)]

# Добавить marker trace
fig.add_trace(go.Scatter(
    x=[min_date],
    y=[min_balance],
    mode="markers",
    marker=dict(
        size=12,
        color="#e74c3c",  # Красный для критичной точки
        symbol="diamond",  # Форма маркера
        line=dict(color="white", width=2)  # Белая обводка для контраста
    ),
    name="Минимум",
    yaxis="y2",  # На той же оси, что и balance line
    showlegend=True,
    hovertemplate=f"<b>Минимальный баланс</b><br>%{{x}}: {format_rub(min_balance)}<extra></extra>"
))
```

**Критичные детали**:
- `mode="markers"` — только маркер, без линии
- `symbol` — форма: "circle", "square", "diamond", "cross", "x", "triangle-up", etc.
- `line=dict(...)` — обводка маркера для контраста
- `yaxis` — та же ось, что и данные для правильного позиционирования
- `showlegend=True` — показывать в legend для пояснения

---

### Vertical Line Annotation Pattern (Протокол 0022)

Вертикальная линия для маркировки "сегодня" или другого события.

```python
from datetime import date

today = date.today()

# Вертикальная линия через Scatter trace
fig.add_trace(go.Scatter(
    x=[today, today],
    y=[0, max_y_value],  # От нижней до верхней границы
    mode="lines",
    line=dict(color="#95a5a6", width=1, dash="dash"),  # Пунктирная линия
    name="Сегодня",
    showlegend=True,
    hoverinfo="skip"  # Не показывать hover для линии
))

# Альтернатива: через add_vline (не в legend)
fig.add_vline(
    x=today,
    line_dash="dash",
    line_color="#95a5a6",
    annotation_text="Сегодня",
    annotation_position="top"
)
```

**Выбор метода**:
- `add_trace(go.Scatter)` — если нужно в legend
- `add_vline()` — если линия декоративная (не в legend)

**Критичные детали**:
- `hoverinfo="skip"` — убирает hover для вертикальной линии
- `dash="dash"` — стиль линии (solid/dash/dot/dashdot)
- `y=[0, max_y]` — нужно указать полный диапазон для Scatter method

---

### Highlight Region Pattern (Протокол 0022)

Выделение региона графика цветом (current month, выходные, праздники).

**Кейс**: Highlight текущего месяца на Year mode.

```python
from datetime import date

current_month = date.today().month

# Highlight через Scatter fill
fig.add_trace(go.Scatter(
    x=[current_month - 0.5, current_month + 0.5, current_month + 0.5, current_month - 0.5],
    y=[0, 0, max_y_value, max_y_value],
    fill="toself",
    fillcolor="rgba(46, 204, 113, 0.1)",  # Зеленый с прозрачностью
    mode="none",  # Без линии/маркеров
    showlegend=False,
    hoverinfo="skip"
))
```

**Альтернатива через vrect**:
```python
fig.add_vrect(
    x0=current_month - 0.5,
    x1=current_month + 0.5,
    fillcolor="rgba(46, 204, 113, 0.1)",
    layer="below",  # Под traces
    line_width=0
)
```

**Критичные детали**:
- `fillcolor` — RGBA с прозрачностью (alpha 0.05-0.2 для subtle highlight)
- `layer="below"` — rect под traces, не перекрывает данные
- `hoverinfo="skip"` — не мешает hover основных данных
- `mode="none"` — для Scatter метода (нет линии/маркеров)

---

### Pattern-Matching Clickable Bars (Протокол 0022)

> **Статус (протокол 0028)**: на графике полос щитка клик реализован
> ПРОЩЕ — через обычный `dcc.Graph.clickData` (Input на сам граф, не
> Pattern-Matching ID), потому что ось теперь `type="date"` и
> `point["x"]` приходит готовой ISO-строкой; Pattern-Matching ID по
> дате был нужен старому графику с числовыми/категориальными осями.
> Guard "только Month mode" тоже снят — щитка нет режимов. Пример ниже
> — исторический, для графиков, где ось НЕ дата или нужен ID сложнее
> одной даты.

Клик по bar для открытия модала с предзаполненной датой.

**Проблема**: Plotly clickData возвращает индекс точки, а не custom ID — неудобно для обработки.

**Решение**: Pattern-Matching IDs в customdata + Dash callback

```python
# При построении chart
customdata = [
    [date.isoformat(), income, expense, balance, status]
    for date, income, expense, balance, status in zip(...)
]

ids = [{"type": "cashflow-bar", "date": date.isoformat()} for date in dates]

fig.add_trace(go.Bar(
    x=dates,
    y=income_values,
    customdata=customdata,
    ids=ids  # Pattern-Matching IDs
))

# В layout Graph component
dcc.Graph(id="daily-cashflow-chart", figure=fig)
```

```python
# Callback
@app.callback(
    Output("create-modal", "is_open"),
    Output("preselected-date", "data"),
    Input({"type": "cashflow-bar", "date": ALL}, "n_clicks"),
    State("dashboard-period-store", "data"),
    prevent_initial_call=True
)
def open_create_from_chart(n_clicks_list, period_store):
    # ADR-003 Guard Clause #1: triggered_id exists
    if not ctx.triggered_id:
        raise PreventUpdate

    # Guard #2: type check
    if ctx.triggered_id.get("type") != "cashflow-bar":
        raise PreventUpdate

    # Guard #3: n_clicks not None
    triggered = ctx.triggered[0]
    if triggered.get("value") is None:
        raise PreventUpdate

    # Guard #4: только Month mode
    period = period_store.get("period", "month")
    if period != "month":
        raise PreventUpdate

    # Извлечь дату из triggered_id
    date_str = ctx.triggered_id["date"]

    return True, date_str
```

**Критичные детали**:
- `ids` parameter в go.Bar для Pattern-Matching
- **4 guard clauses** (ADR-003) для предотвращения автовызовов
- `ctx.triggered_id["date"]` — прямой доступ к дате из ID
- Year mode guard — clickable только в Month mode (разные use cases)

---

### Color Status Mapping Pattern (Протокол 0022)

Цветовая индикация статуса (ok/attention/risk) для balance line.

```python
# Константы цветов
STATUS_COLORS = {
    "ok": "#2ecc71",       # Зеленый (≥ 15000₽)
    "attention": "#f39c12", # Оранжевый (5000-15000₽)
    "risk": "#e74c3c"      # Красный (< 5000₽)
}

# Классификация статуса в сервисе
def _classify_balance_status(balance: Decimal) -> BalanceStatus:
    if balance < BALANCE_RISK_THRESHOLD:  # 5000
        return "risk"
    elif balance < BALANCE_ATTENTION_THRESHOLD:  # 15000
        return "attention"
    else:
        return "ok"

# Применение цвета в chart
status = _classify_balance_status(balance)
color = STATUS_COLORS[status]

fig.add_trace(go.Scatter(
    x=dates,
    y=balance_values,
    line=dict(color=color, width=2)
))
```

**Альтернатива**: Segment coloring для линии (не поддерживается напрямую в Plotly Python — нужен workaround через несколько traces)

**Критичные детали**:
- Константы STATUS_COLORS в начале модуля (single source of truth)
- Классификация в сервисе, не в UI (separation of concerns)
- TypedDict BalanceStatus = Literal["ok", "attention", "risk"] для type safety

---

## Критичные решения

**Stacked Layers (протокол 0028)**: `showlegend=False` + HTML-легенда с тултипами вместо встроенной Plotly-легенды — нужны развёрнутые пояснения и клавиатурная доступность

**Явные tickvals с потолком, не dtick**: на неравномерных многодневных окнах спорные единицы dtick дают то частую, то редкую сетку

**Dual Y-Axis**: Обязателен при разном масштабе данных (50K bars vs 150K line)

**hovermode="x unified"**: Улучшает UX — не нужно точно попадать на trace

**customdata**: Позволяет передавать любые данные в hover (не только Y values)

**Pattern-Matching IDs**: Лучше чем clickData индексы — явные ID для обработки

**4 guard clauses** (ADR-003): Предотвращают auto-trigger callbacks в Dash Pattern-Matching

**STATUS_COLORS константы**: Single source of truth для цветовой индикации

---

Детали: `ui-components.md` (Dashboard-щиток), `services.md` (MoneyLayersService, DashboardService), `code-style.md` (ADR-003 Guard Clauses)
