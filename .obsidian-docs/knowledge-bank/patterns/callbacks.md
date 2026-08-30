---
name: callbacks
description: Паттерны Dash callbacks FinFocus — helper-функции, ADR-003 guards, Store-триггеры для динамических элементов, selective refresh
type: reference
originSessionId: -
---

# patterns/callbacks.md

## Суть
Паттерны организации Dash callbacks для устранения дублирования и безопасности

## Ключевые паттерны

### Store-триггер для динамически рендеренных элементов (Протокол 0028)

Расширяет известный проекту урок про `suppress_callback_exceptions`
(см. `MEMORY.md`) конкретным подтверждённым кейсом: флаг подавляет
только СЕРВЕРНУЮ валидацию layout, а не клиентский рендерер. Прямой
`Input` на элемент, который рендерится динамически и отсутствует в
DOM на части страниц, заставляет `dash-renderer.js` молча не
отправлять callback ВООБЩЕ — без ошибки в консоли — на всех
страницах, где элемента нет.

**Кейс (протокол 0028, зафиксирован как регрессия на ревью)**: шестерёнка
щитка (`dashboard-settings-cog`) рендерится только внутри
`dashboard-free-header`, то есть только на `/dashboard`. Первая попытка
подключить её к модалу профиля — прямой `Input("dashboard-settings-cog",
"n_clicks")` в обычном серверном callback `handle_profile_modal` —
сломала ВТОРОЙ, уже существующий вход (клик по аватару в сайдбаре) на
всех страницах, кроме дашборда: клиентский рендерер не резолвил callback
целиком, потому что один из его Input'ов отсутствовал в DOM.

**Решение**: тот же приём, что уже применялся для кнопок «Сверка» на
дашборде (протоколы 0021-0023) — clientside-триггер пишет timestamp
в глобальный `dcc.Store`, а серверный callback слушает Store, а не
элемент напрямую.

Пример ниже — состояние на момент протокола 0028 (два Input'а: прямой
на аватар сайдбара + Store на шестерёнку). Кусок 3 (протокол 0031,
после переезда навигации в `nav_rail.py`) свёл ОБА входа на один и тот
же Store — аватар полоски-меню тоже рендерится динамически (сайдбар
живёт в слоте и на части страниц отсутствует), поэтому прямой Input на
него страдал бы той же болезнью. Актуальный код (`profile_modal.py`):

```python
# main.py — Store в глобальном layout (существует на всех страницах)
dcc.Store(id="open-profile-trigger", data=None)

# nav_rail.py / dashboard.py — оба clientside-триггера пишут в один Store
clientside_callback(
    ClientsideFunction("triggers", "timestamp_trigger"),
    Output("open-profile-trigger", "data", allow_duplicate=True),
    Input("dashboard-settings-cog", "n_clicks"),  # шестерёнка щитка
    prevent_initial_call=True,
)
# аналогичный clientside-триггер для аватара nav_rail пишет в тот же Store

# profile_modal.py — ЕДИНСТВЕННЫЙ серверный вход, слушает Store, не элемент
@callback(
    ...,
    Input("open-profile-trigger", "data"),
)
def handle_profile_modal(cog_trigger, ...):
    triggered_id = ctx.triggered_id
    if not triggered_id:
        raise PreventUpdate
    # ВАЖНО: guard на пустой триггер — Store хранит значение между
    # переходами по разделам (layout Dash не пересоздаётся), без
    # guard'а модал переоткрывался бы при КАЖДОЙ загрузке любой
    # страницы после первого клика
    ...
```

**Второй побочный дефект того же паттерна — guard на пустой Store**:
Store — не событие, а состояние: Dash не пересоздаёт layout при
переходах между страницами (`url.pathname` меняется, но `dcc.Store`
в корневом `app.layout` живёт всю сессию браузера). Значит после
первого клика Store навсегда хранит непустое значение, и любой
callback, слушающий его через `Input`, сработает заново при следующей
загрузке страницы — если не проверить явно, что значение изменилось
именно СЕЙЧАС. Образец guard'а — `toggle_reconciliation_modal`
в `calendar.py:1309-1311`.

**Когда применять**: любой второй (третий, …) вход в существующий
callback через элемент, которого нет в начальном layout на части
страниц — карточки-двери куска 2 Epic-11, скорее всего, дадут ещё
несколько таких кейсов.

**Критичные детали**:
- `suppress_callback_exceptions=True` НЕ решает эту проблему — это
  доказанный экспериментом факт (0 запросов `_dash-update-component`,
  консоль браузера пуста, никакой ошибки не брошено), не переигрывать
- Проверять эффект нужно вручную в браузере на реальной навигации между
  страницами — юнит-тестом на колбэк-контракт (какие Input'ы объявлены)
  эту регрессию не поймать, только её ОТСУТСТВИЕ повторной поломки
- Docstring/комментарий, объясняющий выбор паттерна, обязателен —
  иначе следующий разработчик повторит прямой Input

---

### Helper Function for Component Loading (Протокол 0022)

Устранение дублирования между load и refresh callbacks через helper функцию.

**Проблема**: load_dashboard_data и refresh_dashboard_after_crud содержали ~80% идентичного кода — риск десинхронизации при изменениях.

**Решение**: Централизованная функция _load_dashboard_components()

```python
def _load_dashboard_components(user_id: int, period: str, year: int, month: int) -> tuple:
    """
    Загружает все компоненты dashboard.

    ВАЖНО: Единая точка загрузки для устранения дублирования.
    Используется в:
    - load_dashboard_data (initial load)
    - refresh_dashboard_after_crud (refresh после CRUD)

    Returns:
        tuple: (kpi_cards, chart_figure, transactions_table)
    """
    with get_db_session() as session:
        service = DashboardService(session)

        # KPI metrics
        metrics = service.get_overview_metrics(user_id, period, reference_date)
        kpi_cards = _build_kpi_cards(metrics)

        # Chart
        if period == "month":
            data = service.get_daily_cashflow(user_id, year, month)
            chart = _build_daily_cashflow_chart(data)
        else:
            data = service.get_yearly_cashflow(user_id, year)
            chart = _build_yearly_cashflow_chart(data)

        # Recent transactions
        transactions = service.get_recent_transactions(user_id, limit=5)
        table = build_recent_transactions(transactions)

    return kpi_cards, chart, table


@app.callback(
    Output("dashboard-content", "children"),
    Input("url", "pathname"),
    State("dashboard-period-store", "data")
)
def load_dashboard_data(pathname, period_store):
    if pathname != "/dashboard":
        raise PreventUpdate

    user_id = 1
    period = period_store.get("period", "month")
    year = period_store.get("year", date.today().year)
    month = period_store.get("month", date.today().month)

    kpi, chart, table = _load_dashboard_components(user_id, period, year, month)
    return [kpi, chart, table]


@app.callback(
    Output("dashboard-content", "children"),
    Input("global-transaction-trigger", "data"),
    State("dashboard-period-store", "data"),
    prevent_initial_call=True
)
def refresh_dashboard_after_crud(trigger, period_store):
    # ADR-003 Guard Clause
    if trigger is None:
        raise PreventUpdate

    user_id = 1
    period = period_store.get("period", "month")
    year = period_store.get("year", date.today().year)
    month = period_store.get("month", date.today().month)

    kpi, chart, table = _load_dashboard_components(user_id, period, year, month)
    return [kpi, chart, table]
```

**Преимущества**:
- Single Source of Truth для логики загрузки
- Изменения в одном месте → применяются ко всем callbacks
- Проще тестировать (один метод вместо двух callbacks)
- Меньше риск copy-paste ошибок

**Критичные детали**:
- Helper функция module-level (не в классе) — доступна всем callbacks
- Возвращает tuple компонентов (не Dash layout) — flexibility
- Обработка БД в helper, не в callback — separation of concerns
- Docstring ВАЖНО — какие callbacks используют этот helper

---

### ADR-003 Guard Clauses Pattern

4-уровневая система защиты от автовызовов Pattern-Matching callbacks.

**Проблема**: Dash Pattern-Matching callbacks срабатывают автоматически при обновлении DOM (n_clicks=0 при mount).

**Решение**: Цепочка guard clauses для фильтрации

```python
@app.callback(
    Output("create-modal", "is_open"),
    Output("preselected-date", "data"),
    Input({"type": "cashflow-bar", "date": ALL}, "n_clicks"),
    State("dashboard-period-store", "data"),
    prevent_initial_call=True
)
def open_create_from_chart(n_clicks_list, period_store):
    # GUARD CLAUSE #1: triggered_id exists
    if not ctx.triggered_id:
        raise PreventUpdate

    # GUARD CLAUSE #2: correct type
    if ctx.triggered_id.get("type") != "cashflow-bar":
        raise PreventUpdate

    # GUARD CLAUSE #3: n_clicks not None
    triggered = ctx.triggered[0]
    if triggered.get("value") is None:
        raise PreventUpdate

    # GUARD CLAUSE #4: n_clicks > 0 (user click, not mount)
    if triggered.get("value", 0) <= 0:
        raise PreventUpdate

    # GUARD CLAUSE #5 (опционально): business logic guard
    period = period_store.get("period", "month")
    if period != "month":  # Только Month mode поддерживает клик
        raise PreventUpdate

    # Основная логика
    date_str = ctx.triggered_id["date"]
    return True, date_str
```

**Уровни защиты**:
1. **triggered_id exists** — callback был вызван через конкретный Input
2. **correct type** — тип соответствует ожидаемому (для множественных Pattern-Matching)
3. **n_clicks not None** — есть данные (защита от corrupted state)
4. **n_clicks > 0** — реальный клик пользователя, не mount
5. **business logic guard** (опционально) — дополнительная валидация контекста

**Применение**:
- Обязательно для Pattern-Matching callbacks с Input ALL
- Обязательно для callbacks с n_clicks Input
- Опционально для State-only callbacks (но рекомендуется Guard #1)

**Критичные детали**:
- `ctx.triggered_id` — dict для Pattern-Matching, None для обычных callbacks
- `ctx.triggered[0].get("value")` — значение Input, None при mount
- `raise PreventUpdate` — прерывает callback, не обновляет Outputs
- Порядок важен: дешевые проверки (exists/type) перед дорогими (DB queries)

---

### Period Store Pattern (Протокол 0022)

> **Статус (протокол 0028)**: конкретное применение на дашборде
> (`dashboard-period-store`, переключатель Month/Year) СНЯТО вместе
> со старым графиком — щиток показывает единое 45-дневное окно без
> переключения периода. Паттерн Store-с-расширенной-структурой
> остаётся общим приёмом, пример ниже сохранён как референс структуры,
> но на дашборде больше не действует.

State management через dcc.Store для сохранения контекста (period, year, month).

**Проблема**: Переключение month/year сбрасывало текущий месяц — пользователь терял контекст.

**Решение**: Store с расширенной структурой данных

```python
# В layout
dcc.Store(id="dashboard-period-store", data={
    "period": "month",
    "year": date.today().year,
    "month": date.today().month
})

@app.callback(
    Output("dashboard-period-store", "data"),
    Input("period-switcher", "value"),
    State("dashboard-period-store", "data")
)
def update_period_state(new_period, current_store):
    # ADR-003 Guard Clause
    if new_period is None:
        raise PreventUpdate

    # Сохраняем year/month из текущего Store
    return {
        "period": new_period,
        "year": current_store.get("year", date.today().year),
        "month": current_store.get("month", date.today().month)
    }

@app.callback(
    Output("dashboard-content", "children"),
    Input("dashboard-period-store", "data")
)
def load_dashboard_data(period_store):
    user_id = 1
    period = period_store.get("period", "month")
    year = period_store.get("year", date.today().year)
    month = period_store.get("month", date.today().month)

    kpi, chart, table = _load_dashboard_components(user_id, period, year, month)
    return [kpi, chart, table]
```

**Преимущества**:
- Контекст сохраняется между переключениями period
- Централизованный state для множества callbacks
- Легко расширить (добавить новые поля в dict)
- Сохраняется в сессии браузера (не теряется при refresh страницы)

**Критичные детали**:
- Store data всегда dict (не scalar) — flexibility для расширения
- `.get("key", default)` — защита от missing keys
- State в update callback — merge old и new данных
- Store Output только в одном callback — avoid conflicts

---

### Preselection Store Pattern (Протокол 0020-0022)

Передача данных из источника в create-modal через dcc.Store.

**Проблема**: Клик по bar/wishlist → create-modal должен получить дату/сумму/описание — как передать?

**Решение**: 4 специализированных Stores для preselection

```python
# В transaction_modals.py layout
dcc.Store(id="preselected-date", data=None),
dcc.Store(id="preselected-amount", data=None),
dcc.Store(id="preselected-description", data=None),
dcc.Store(id="preselected-risk-warning", data=None)

# В calendar_wishlist.py (источник)
@app.callback(
    Output("create-modal", "is_open"),
    Output("preselected-date", "data"),
    Output("preselected-amount", "data"),
    Output("preselected-description", "data"),
    Output("preselected-risk-warning", "data"),
    Input({"type": "wishlist-day-cell", "date": ALL}, "n_clicks"),
    State("wishlist-active-item", "data"),
    State("wishlist-safe-dates", "data"),
    prevent_initial_call=True
)
def open_create_from_wishlist_day(n_clicks_list, active_item, safe_dates):
    # ADR-003 guards...

    date_str = ctx.triggered_id["date"]
    item = deserialize_wishlist_item(active_item)

    # Preselection данные
    amount_str = str(item["amount"])
    description = f"Покупка: {item['name']}"

    # Risk warning из safe_dates
    safe_info = safe_dates.get(date_str, {})
    risk_warning = None
    if not safe_info.get("safe"):
        reasons = safe_info.get("reasons", [])
        if "cushion" in reasons:
            risk_warning = "⚠️ Покупка нарушит финансовую подушку"
        elif "negative_balance" in reasons:
            risk_warning = "🚨 Покупка приведёт к отрицательному балансу"

    return True, date_str, amount_str, description, risk_warning

# В transaction_modals.py (приёмник)
@app.callback(
    Output("create-date-picker", "date"),
    Output("create-amount-input", "value"),
    Output("create-description-input", "value"),
    Output("create-risk-warning", "children"),
    Output("create-risk-warning", "style"),
    Input("create-modal", "is_open"),
    State("preselected-date", "data"),
    State("preselected-amount", "data"),
    State("preselected-description", "data"),
    State("preselected-risk-warning", "data"),
    State("modal-source", "data")
)
def set_preselection_on_modal_open(is_open, date, amount, desc, warning, source):
    if not is_open:
        raise PreventUpdate

    # Применяем preselection
    if source == "wishlist" and date:
        warning_style = {"display": "block"} if warning else {"display": "none"}
        return date, amount or "", desc or "", warning or "", warning_style

    # Default values
    return None, "", "", "", {"display": "none"}
```

**Преимущества**:
- Разделение concerns: источник → Stores → приёмник
- Множественные источники (calendar, dashboard, wishlist) → единый приёмник
- Расширяемо (добавить новые Stores для других полей)
- Type safety через TypedDicts в источниках

**Критичные детали**:
- 4 отдельных Stores (не один dict) — flexibility для опциональных полей
- Reset Stores после create → callback create_transaction возвращает None для всех 4 Stores
- modal-source Store — для определения источника открытия (conditional logic)
- State в set_preselection callback — не trigger при изменении Store (только при is_open)

---

### Selective Refresh Pattern (Протокол 0015)

Обновление только страниц, которые открыты, через global trigger + source tracking.

**Проблема**: Создание транзакции → нужно обновить Calendar, Dashboard, Transactions — но все 3 callbacks срабатывают даже если страницы не открыты.

**Решение**: global-transaction-trigger + modal-source Store

```python
# В transaction_modals.py
dcc.Store(id="modal-source", data=None),  # "calendar" | "dashboard" | "transactions"
dcc.Store(id="global-transaction-trigger", data=None)  # Эмиттер

@app.callback(
    Output("create-modal", "is_open"),
    Output("global-transaction-trigger", "data"),
    Input("create-submit-btn", "n_clicks"),
    State("modal-source", "data")
)
def create_transaction(n_clicks, source):
    # ... создание транзакции ...

    # Emit trigger для refresh
    trigger_data = {
        "timestamp": datetime.now().isoformat(),
        "source": source,  # Откуда был открыт модал
        "action": "create"
    }

    return False, trigger_data  # Close modal, emit trigger

# В calendar.py
@app.callback(
    Output("calendar-grid", "children"),
    Input("global-transaction-trigger", "data"),
    State("url", "pathname"),
    prevent_initial_call=True
)
def refresh_calendar_after_transaction(trigger, pathname):
    # Guard: только если мы на странице календаря
    if pathname != "/calendar":
        raise PreventUpdate

    # Guard: trigger не пустой
    if trigger is None:
        raise PreventUpdate

    # Refresh logic...
    return updated_calendar_grid

# В dashboard.py (аналогично)
@app.callback(
    Output("dashboard-content", "children"),
    Input("global-transaction-trigger", "data"),
    State("url", "pathname"),
    prevent_initial_call=True
)
def refresh_dashboard_after_crud(trigger, pathname):
    if pathname != "/dashboard":
        raise PreventUpdate

    if trigger is None:
        raise PreventUpdate

    # Refresh logic...
    return updated_dashboard
```

**Преимущества**:
- Не срабатывает callback если страница не открыта → экономия ресурсов
- Единый trigger для множества страниц → consistency
- Source tracking для аналитики/debugging
- Расширяемо (добавить action type: create/update/delete)

**Критичные детали**:
- `prevent_initial_call=True` — не срабатывает при mount
- pathname guard в НАЧАЛЕ callback — дешевая проверка до DB queries
- trigger dict с timestamp — уникальность для каждого emit (Dash сравнивает по value)
- modal-source устанавливается при открытии модала из разных источников

---

## Правила условно присутствующих элементов (Протокол 0030)

**«Удаляешь элемент — удаляй его Input»** (RTM #80). Кнопка
`open-wishlist-modal-btn` ушла вместе с wishlist-виджетом — вместе с ней
удалён и её Input в `open_wishlist_modal`, вход переведён на Store
`open-wishlist-trigger`. Осиротевший Input на несуществующий элемент
молча отключает колбэк ЦЕЛИКОМ на страницах без элемента (класс
регрессий C-6, дважды пойманный проектом: 0026, 0028/3.5-m-fix).

**«Output на условно присутствующий элемент лечится переносом данных в
построение, а не guard'ом»** (Подход B, протокол 0030). Сайдбар после
снятия с дашборда рендерится колбэком render_sidebar_slot — его прежние
колбэки (подсветка, профиль) писали бы children в узлы, которые слот в
тот же момент создаёт/удаляет: это гонка, guard по pathname её маскирует,
а не снимает (и возвращал бы литералы-заглушки после каждого перехода).
Решение: обязанности колбэков переехали в аргументы чистой функции
create_sidebar(pathname, profile) — куском 3 переименована в
create_nav_rail; чтение профиля — в колбэк слота.
У навигации не осталось ни одного колбэка кроме слот-колбэка.
Регрессионный якорь — `tests/test_nav_rail.py` (протокол 0031;
`test_sidebar.py` удалён вместе с сайдбаром).

**«Нераспознанные Output-Store'ы → no_update, не None»** (протокол 0030,
дефект найден живой проверкой). Запись в Store — даже того же значения —
триггерит его подписчиков: None в wishlist-active-item из
handle_panel_query_params перерисовывал календарь второй раз, гася
только что применённый фокус дня.

### Анимация на монтировании условно присутствующего элемента (Протокол 0031)

Полоска-меню «разворачивается» при входе с дашборда и НЕ переигрывает
разворот при переходах раздел→раздел. Четыре решения, каждое из
которых легко сделать неправильно:

**`@keyframes`, а не `transition`.** Transition анимирует ПЕРЕХОД между
двумя значениями, а на монтировании стартового значения не существует:
узла секунду назад не было. Задать «начальное» состояние и через кадр
снять его — это уже JS с requestAnimationFrame и вторым источником
правды о том, played/not played. Keyframes-анимация играет на
монтировании сама, без единой строки JS.

**Различитель «пришёл с дашборда» — пустой слот, а не хранимый
предыдущий pathname.** Соблазн держать в Store прошлый путь и сравнивать
велик, но это второй источник правды: он разъезжается с реальностью при
F5, при переходе по внешней ссылке, при восстановлении Store между
страницами. Пустой слот на дашборде (`render_nav_rail_slot` возвращает
`[]`) — уже существующий факт, из которого монтирование следует само:
узла не было → появился → анимация сыграла.

**Носитель идентичности узла — `id`, а НЕ `key`.** В dash-renderer
2.17.1 ключ обёртки вычисляется как `stringifyId(component.props.id)`
(`createContainer`, ~строка 3972 в `dash_renderer.dev.js`); проп `key`
в этом выражении не участвует и до реконсиляции обёртки не доходит
вообще. Более того, `dcc.Link` его не принимает — `TypeError` прямо на
построении layout. Ставить `key` бессмысленно и вредно: создаёт
впечатление, что идентичность обеспечена, тогда как обеспечивает её
`id`.

Второе условие переиспользования узла — **стабильная позиция**: слот
обязан возвращать РОВНО ОДИН компонент, не список. Обёртка возврата в
список ломает анимацию молча: визуально всё на месте, разворот начинает
играть на каждом переходе.

**`id` — не приглашение вешать колбэк.** Output на узел, который слот
создаёт и удаляет, — гонка (порядок применения Output'ов Dash не
гарантирует), Input — класс регрессий C-6. Вход в профиль с аватара
полоски идёт clientside-триггером в Store, как и у шестерёнки щитка.

**`animation-fill-mode: backwards`, а не `both`.** `both` оставляет
`to`-кадр на узле навсегда; если в нём `clip-path: inset(0)` — он
режет по border-box и срезает всё, что выходит за границы элемента
(в нашем случае — язычки подписей). `backwards` при нулевой задержке
собственного эффекта не имеет и берётся ровно ради отсутствия
остаточного состояния.

**`prefers-reduced-motion` обнуляет `animation` целиком**, не только
`animation-duration`: при нулевой длительности первый кадр всё равно
применяется и залипает.

Проверяется только живьём: счётчик `animationstart` с фильтром по
`animationName` + сравнение ссылки на DOM-узел до и после перехода.
Тестами фиксируются лишь ПРЕДПОСЫЛКИ (стабильный `id`, единственность
ребёнка слота, отсутствие серверных колбэков) — зелёный прогон не
означает, что анимация ведёт себя правильно.

### Порядок guard'ов: бизнес-проверка ДО ветвления на подтипы (Протокол 0032)

Guard «эта запись служебная/защищённая» обязан стоять ПЕРВЫМ среди
проверок после загрузки записи из БД — раньше любого ветвления на
подтипы поведения (recurring/обычная, scope-modal/обычный edit).
Порядок «сначала определить подтип, потом решить, можно ли вообще
редактировать» кажется естественным (сначала классифицировать, потом
защитить), но ломается на записях, которые принадлежат сразу двум
классификациям одновременно.

**Кейс (протокол 0032, `open_edit_modal` в `transactions.py`)**:
служебная транзакция `SAVINGS_RESERVE` (шаблон резервирования
бюджета) реально бывает recurring-операцией (`is_recurring=True`).
Guard «служебная → PreventUpdate» стоит ДО проверки
`is_recurring_tx` — если бы порядок был обратным, служебная recurring-
операция сначала открыла бы диалог выбора scope («экземпляр vs
серия»), и только защита следующего шага (которой там нет) успела бы
её остановить. Два независимых измерения одной записи (что это за
операция / какая у неё периодичность) нельзя проверять по очереди,
предполагая, что более специфичная проверка идёт первой автоматически.

**Правило**: при добавлении guard'а к callback'у, который уже ветвится
по подтипу записи, новый guard — с самой широкой областью действия
(«вообще нельзя трогать») — вставляется перед существующим
ветвлением, не после него и не «где нашлось место».

---

### Технический долг: дублирующиеся списки типов (Протокол 0032)

Защита служебных операций опирается на два независимых перечня
`TransactionType`, живущих в разных слоях:
`SYSTEM_TRANSACTION_TYPES` (UI-слой, `transactions.py`, «что нельзя
трогать» — 2 типа) и `CATEGORIZABLE_TRANSACTION_TYPES` (сервисный
слой, `transaction_service.py`, «что можно категоризировать» —
инвертированный список, тоже 2 из 6 типов). Автоматической сверки
между ними нет. При добавлении седьмого `TransactionType` оба списка
редактируются руками — риск молчаливого расхождения (новый тип
окажется «служебным» в одном слое и «обычным» в другом) принят
осознанно как техдолг, не устранён протоколом.

**Когда возвращаться**: следующий раз, когда в проекте появится новый
`TransactionType` — свериться с обоими списками явно, не полагаться
на память о том, что они должны совпадать.

---

## Критичные решения

**Helper Functions**: Устранение дублирования > copy-paste (maintainability)

**ADR-003 Guards**: 4-уровневая защита обязательна для Pattern-Matching с n_clicks

**Period Store**: Dict с расширенной структурой > scalar для flexibility

**Preselection Stores**: Отдельные Stores > один dict для optional fields

**Selective Refresh**: pathname guard > всегда refresh (performance)

---

Детали: `ui-components.md` (Dashboard-щиток, Calendar, Transactions), `code-style.md` (ADR-003), `architecture.md` (Presentation Layer), `services.md` (MoneyLayersService)
