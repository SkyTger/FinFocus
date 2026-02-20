# Solution v3: Dashboard Layout Redesign (Batch 5.3)

## Обзор решения

Финальная перестройка Dashboard layout: split Recent/Upcoming операций 50/50, правая колонна с Wishlist + readonly Cushion card, sidebar в dbc.Card, модал сверки глобализирован через замену `calendar-refresh-trigger` на `global-transaction-trigger`, пустые состояния с CTA. Все 11 замечаний из critique v1 решены с конкретными code-level изменениями. 4 замечания из critique v2 учтены.

## Архитектура

### Слой 1: DashboardService (данные)
- **`get_recent_transactions()`** -- рефакторинг: добавить `reference_date` параметр, фильтрация first_of_month..reference_date. Включить recurring instances (`recurring_parent_id IS NOT NULL`). Исключить только шаблоны (`is_recurring=True AND recurring_parent_id IS NULL`).
- **`get_upcoming_transactions()`** -- новый метод: reference_date..end_of_month ASC. Аналогичная логика фильтрации (recurring instances включены, шаблоны исключены).
- **`RecentTransaction`** TypedDict: добавить поле `is_recurring_instance: bool`.

### Слой 2: Formatters (утилиты)
- **`format_date_human()`** -- новая функция "5 февраля" (генитив).
- **`MONTH_NAMES_RU_GENITIVE`** -- словарь русских месяцев в родительном падеже.

### Слой 3: Dashboard UI (компоненты)
- **`_build_transactions_split_table()`** -- новая функция для одной колонки (recent или upcoming).
- **`_build_empty_state()`** -- новая функция пустого состояния с CTA.
- **`_build_cushion_card_readonly()`** -- новая read-only карточка cushion (без кнопок, с ссылкой на /goals). Определяется в dashboard.py, а НЕ в goals.py, чтобы исключить конфликт ID.
- Перестройка `create_dashboard_layout()` -- 8/4 split сохранен, добавлен upcoming output.
- Новый callback `open_recon_from_dashboard()` -- кнопки "Сверка" (KPI card + banner) пишут timestamp в `open-recon-trigger` Store. Один callback с двумя Inputs.
- Новый callback `open_create_from_empty()` -- CTA "Добавить" из empty state открывает create-modal.

### Слой 4: Calendar.py (reconciliation refactoring)
- **`apply_reconciliation()`** -- заменить Output `calendar-refresh-trigger` на `global-transaction-trigger`. Удалить `calendar-refresh-trigger` Store из layout. Удалить `refresh_calendar_after_reconciliation()` callback (он дублирует `refresh_calendar_after_transaction()` который уже слушает `global-transaction-trigger`).
- `create_reconciliation_modal()` вызов перемещается из `create_calendar_layout()` в `main.py`.

### Слой 5: Sidebar (навигация)
- Обертка в `dbc.Card`, `dbc.Nav` получает `id="sidebar-nav"`.
- Callback `highlight_active_sidebar()` перестраивает children `dbc.Nav` при смене URL (5 items, negligible cost).

### Слой 6: Transactions (query params)
- Новый callback `apply_url_date_filter()` -- парсит `url.search` (?start=&end=), устанавливает `filter-date-range` start_date/end_date.

### Диаграмма взаимодействия

```
User clicks "Сверка" on Dashboard KPI card
  → open_recon_from_dashboard() fires (Input: open-recon-from-dashboard-btn)
  → writes timestamp to open-recon-trigger Store
  → toggle_reconciliation_modal() fires (Input: open-recon-trigger)
  → Modal opens, user enters data, clicks "Применить"
  → apply_reconciliation() creates ADJUSTMENT, writes to global-transaction-trigger
  → refresh_dashboard_after_crud() fires → KPI + tables refresh
  → refresh_calendar_after_transaction() fires (if on /calendar) → calendar refreshes

User clicks "Сверить баланс" on Dashboard balance banner
  → open_recon_from_dashboard() fires (Input: open-recon-from-dashboard-banner-btn)
  → same flow as above (same callback, second Input)

User clicks "Добавить" in empty state
  → open_create_from_empty() writes to create-modal.is_open + modal-source
  → Transaction create flow (existing)
  → global-transaction-trigger fires → Dashboard refreshes

Dashboard navigated to → create_dashboard_layout()
  → _load_dashboard_components() fetches recent + upcoming + cushion
  → _build_cushion_card_readonly() renders read-only card (no button IDs)
  → Layout renders with 8/4 split (chart+tables | wishlist+cushion)
```

## Файловая структура

```
app/
  services/
    dashboard_service.py       # +get_upcoming_transactions(), refactor get_recent_transactions(), +is_recurring_instance in TypedDict
  utils/
    formatters.py              # +format_date_human(), +MONTH_NAMES_RU_GENITIVE
  components/
    dashboard.py               # Перестройка layout, +_build_transactions_split_table, +_build_empty_state, +_build_cushion_card_readonly, +2 callbacks, обновление _load_dashboard_components (6 outputs)
    sidebar.py                 # dbc.Card обертка, id="sidebar-nav", callback highlight_active_sidebar
    calendar.py                # Удалить calendar-refresh-trigger Store, удалить refresh_calendar_after_reconciliation callback, переделать apply_reconciliation Output на global-transaction-trigger, удалить create_reconciliation_modal() из layout
    transactions.py            # +apply_url_date_filter callback
  assets/
    custom.css                 # +.empty-state, +.dashboard-split-table styles
    sidebar.css                # НОВЫЙ: .sidebar-card, .sidebar-nav-item.active
  main.py                      # +create_reconciliation_modal() в глобальный layout
tests/
  test_dashboard_service.py    # +9 тестов (upcoming + recent refactor)
  test_formatters.py           # +3 теста для format_date_human
```

## Ключевые интерфейсы

```python
# === formatters.py ===

MONTH_NAMES_RU_GENITIVE: dict[int, str] = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

def format_date_human(date_obj: date) -> str:
    """Форматирует дату в человекочитаемый формат.

    Args:
        date_obj: Объект даты

    Returns:
        str: Дата в формате "5 февраля"
    """
    return f"{date_obj.day} {MONTH_NAMES_RU_GENITIVE[date_obj.month]}"


# === dashboard_service.py ===

class RecentTransaction(TypedDict):
    """Данные транзакции для списка на дашборде."""
    id: int
    description: str | None
    category_name: str | None
    category_icon: str | None
    date: str
    amount: Decimal
    transaction_type: str
    is_recurring_instance: bool  # True если recurring_parent_id != None


def get_recent_transactions(
    self,
    user_id: int,
    limit: int = 5,
    reference_date: date | None = None,
) -> list[RecentTransaction]:
    """Получает недавние операции (1 число текущего месяца..reference_date включительно).

    INTENTIONAL SEMANTIC CHANGE: предыдущая версия возвращала последние N
    транзакций за все время. Новая версия фильтрует по текущему месяцу
    (first_of_month..reference_date). При отсутствии данных за месяц — пустой список
    (обрабатывается empty state на UI).

    Фильтрация:
    - Исключает recurring шаблоны (is_recurring=True AND recurring_parent_id IS NULL)
    - Включает recurring instances (recurring_parent_id IS NOT NULL)
    - Включает обычные транзакции (is_recurring=False)

    Args:
        user_id: ID пользователя
        limit: Максимальное количество (по умолчанию 5)
        reference_date: Дата отсчета (по умолчанию сегодня)

    Returns:
        list[RecentTransaction]: транзакции, сортировка date DESC, id DESC
    """
    ...


def get_upcoming_transactions(
    self,
    user_id: int,
    limit: int = 5,
    reference_date: date | None = None,
) -> list[RecentTransaction]:
    """Получает предстоящие операции (reference_date..конец месяца включительно).

    Фильтрация идентична get_recent_transactions():
    - Исключает recurring шаблоны (is_recurring=True AND recurring_parent_id IS NULL)
    - Включает recurring instances (recurring_parent_id IS NOT NULL)

    Args:
        user_id: ID пользователя
        limit: Максимальное количество (по умолчанию 5)
        reference_date: Дата отсчета (по умолчанию сегодня)

    Returns:
        list[RecentTransaction]: предстоящие операции, сортировка date ASC, id ASC
    """
    ...


# === dashboard.py (new build functions) ===

def _build_transactions_split_table(
    transactions: list[RecentTransaction],
    title: str,
    empty_message: str,
    link_text: str,
    link_href: str,
    empty_btn_id: str,
) -> dbc.Card:
    """Создает карточку с таблицей операций для split layout.

    Args:
        transactions: Список транзакций
        title: Заголовок ("Недавние операции" / "Предстоящие операции")
        empty_message: Текст пустого состояния
        link_text: Текст ссылки внизу карточки
        link_href: URL с фильтром дат (/transactions?start=...&end=...)
        empty_btn_id: ID кнопки "Добавить" для пустого состояния
    """
    ...


def _build_empty_state(
    icon: str,
    message: str,
    button_id: str,
) -> html.Div:
    """Создает пустое состояние с иконкой, текстом и CTA.

    Args:
        icon: Bootstrap icon class (например "bi-inbox")
        message: Текст сообщения
        button_id: ID кнопки "Добавить"

    Returns:
        html.Div с пустым состоянием
    """
    ...


def _build_cushion_card_readonly(user_id: int) -> dbc.Card:
    """Создает read-only карточку подушки безопасности для Dashboard.

    Отличия от _build_cushion_card() в goals.py:
    - НЕ содержит кнопок с id="cushion-open-modal-btn" (избежание duplicate ID)
    - Вместо кнопки "Настроить"/"Изменить" — dcc.Link("Настройки", href="/goals")
    - Не зависит от cushion-settings-store и cushion-refresh-trigger (goals-local Stores)
    - Рендерится at layout-build time, обновляется при навигации на Dashboard

    Args:
        user_id: ID пользователя

    Returns:
        dbc.Card: Read-only cushion card
    """
    ...


# === dashboard.py (_build_balance_banner refactored) ===

def _build_balance_banner() -> dbc.Alert:
    """Создает баннер для предупреждения о нулевом балансе.

    Кнопка "Сверить баланс" реализована как dbc.Button с
    id="open-recon-from-dashboard-banner-btn" (НЕ как dcc.Link на /calendar).
    Клик обрабатывается callback open_recon_from_dashboard() совместно
    с KPI кнопкой "Сверка".
    """
    return dbc.Alert(
        id="balance-alert-toast",
        is_open=False,
        dismissable=True,
        className="balance-banner mb-3",
        children=[
            html.Div(
                [
                    html.I(className="bi bi-exclamation-triangle-fill me-2"),
                    html.Span(
                        "Для точных расчётов укажите текущий остаток на счетах.",
                        className="me-3",
                    ),
                    dbc.Button(
                        "Сверить баланс",
                        id="open-recon-from-dashboard-banner-btn",
                        color="dark",
                        size="sm",
                        outline=True,
                    ),
                ],
                className="d-flex align-items-center justify-content-center flex-wrap",
            ),
        ],
    )


# === dashboard.py (build_overview_cards refactored recon_button) ===

# В build_overview_cards() (строки 310-318 текущего кода):
# БЫЛО:
#   recon_button = dcc.Link(
#       dbc.Button([html.I(...), "Сверка"], ...),
#       href="/calendar?open_recon=1",
#   )
# СТАЛО:
recon_button = dbc.Button(
    [html.I(className="bi bi-check2-square me-1"), "Сверка"],
    id="open-recon-from-dashboard-btn",
    size="sm",
    color="success",
    outline=True,
)


# === dashboard.py (open_recon_from_dashboard callback — unified for both buttons) ===

@callback(
    Output("open-recon-trigger", "data", allow_duplicate=True),
    [
        Input("open-recon-from-dashboard-btn", "n_clicks"),
        Input("open-recon-from-dashboard-banner-btn", "n_clicks"),
    ],
    prevent_initial_call=True,
)
def open_recon_from_dashboard(kpi_clicks, banner_clicks):
    """Открывает модал сверки с Dashboard (KPI card или banner).

    Пишет timestamp в open-recon-trigger Store. Один callback
    обслуживает обе кнопки: "Сверка" на KPI-карточке баланса и
    "Сверить баланс" на toast-баннере.

    Args:
        kpi_clicks: Клики на кнопку "Сверка" в KPI-карточке
        banner_clicks: Клики на кнопку "Сверить баланс" в баннере

    Returns:
        int: Timestamp для trigger
    """
    if kpi_clicks is None and banner_clicks is None:
        raise PreventUpdate
    return int(time.time() * 1000)


# === calendar.py (apply_reconciliation refactored) ===

@callback(
    [
        Output("reconciliation-message", "children", allow_duplicate=True),
        Output("reconciliation-modal", "is_open", allow_duplicate=True),
        Output("global-transaction-trigger", "data", allow_duplicate=True),
        # REMOVED: Output("calendar-refresh-trigger", "data")
    ],
    [Input("apply-reconciliation-btn", "n_clicks")],
    [
        State("reconciliation-date", "date"),
        State("reconciliation-actual", "value"),
    ],
    prevent_initial_call=True,
)
def apply_reconciliation(
    n_clicks: int | None,
    selected_date: str | None,
    actual_value: float | None,
):
    """Применяет сверку и создает корректировку.

    Пишет в global-transaction-trigger (НЕ calendar-refresh-trigger) чтобы
    обновить и Dashboard, и Calendar, и Transactions.
    """
    ...
    # On success:
    return (
        success_alert,
        False,  # close modal
        {
            "source": "reconciliation",
            "action": "create",
            "timestamp": datetime.now().isoformat(),
        },
    )


# === sidebar.py ===

# Diff для dbc.Nav — добавление id="sidebar-nav":
# БЫЛО (строка 82):
#   dbc.Nav(nav_links, vertical=True, className="mb-4")
# СТАЛО:
#   dbc.Nav(nav_links, vertical=True, className="mb-4", id="sidebar-nav")

@callback(
    Output("sidebar-nav", "children"),
    Input("url", "pathname"),
)
def highlight_active_sidebar(pathname: str) -> list:
    """Подсвечивает активный пункт меню в sidebar.

    Перестраивает NavLink children с правильным active и className.
    5 items, negligible cost.
    """
    ...


# === transactions.py (new callback) ===

@callback(
    [
        Output("filter-date-range", "start_date", allow_duplicate=True),
        Output("filter-date-range", "end_date", allow_duplicate=True),
    ],
    Input("url", "search"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def apply_url_date_filter(
    url_search: str | None,
    pathname: str | None,
) -> tuple[str | None, str | None]:
    """Парсит query params ?start=YYYY-MM-DD&end=YYYY-MM-DD и устанавливает фильтры.

    Работает только на /transactions. Невалидные даты игнорируются (fallback None).
    """
    ...
```

## Модель данных

Модель данных не изменяется. Расширяется TypedDict `RecentTransaction`:

```python
class RecentTransaction(TypedDict):
    id: int
    description: str | None
    category_name: str | None
    category_icon: str | None
    date: str
    amount: Decimal
    transaction_type: str
    is_recurring_instance: bool  # NEW: True if recurring_parent_id is not None
```

Фильтрация в SQL для обоих методов (recent + upcoming):
```python
# Исключаем ТОЛЬКО шаблоны recurring: is_recurring=True AND parent_id IS NULL
# Включаем recurring instances: parent_id IS NOT NULL (is_recurring=False)
# Включаем обычные: is_recurring=False AND parent_id IS NULL
.filter(
    ~(
        (Transaction.is_recurring == True)
        & (Transaction.recurring_parent_id == None)
    )
)
```

## Обработка ошибок

1. **Service layer**: try/except с logger.error, возврат пустого списка (fail-safe, существующий паттерн в `get_recent_transactions()`).
2. **Callbacks**: try/except с logger.error и `raise PreventUpdate` (существующий паттерн).
3. **`_build_cushion_card_readonly()`**: try/except при загрузке CushionService.get_settings(); fallback -- карточка "не настроена" с ссылкой на /goals.
4. **`apply_url_date_filter()`**: невалидные даты (parse error) -> return (None, None) (ignore query params).
5. **Empty state CTA**: guard clauses по ADR-003 (`n_clicks is None -> raise PreventUpdate`).
6. **`toggle_reconciliation_modal()` with missing `open-reconciliation-btn`**: `suppress_callback_exceptions=True` позволяет Dash подставить None для отсутствующего Input. Existing guard `if open_clicks is None or open_clicks == 0: raise PreventUpdate` корректно обрабатывает этот случай.

## План реализации

### Step 1: Formatters -- format_date_human() (~10 min)
- Добавить `MONTH_NAMES_RU_GENITIVE` dict в `formatters.py`.
- Добавить `format_date_human(date_obj) -> str`.
- 3 unit теста в `tests/test_formatters.py`: day 1, day 15, day 31 (разные месяцы).

### Step 2: DashboardService -- расширение (~30 min)
- Добавить `is_recurring_instance: bool` в `RecentTransaction` TypedDict.
- Рефакторинг `get_recent_transactions()`: добавить `reference_date` параметр, фильтры first_of_month..reference_date, новая логика exclude recurring templates (NOT include instances).
- Новый `get_upcoming_transactions()`: reference_date..end_of_month, ASC sort.
- Маппинг: `is_recurring_instance=t.recurring_parent_id is not None`.

### Step 3: Unit тесты для service (~30 min)
- 9 тестов в `tests/test_dashboard_service.py`:
  - `test_get_upcoming_basic` -- базовый кейс
  - `test_get_upcoming_empty` -- нет операций
  - `test_get_upcoming_limit` -- ограничение количества
  - `test_get_upcoming_sorting_asc` -- сортировка ASC
  - `test_get_upcoming_excludes_templates` -- шаблоны исключены
  - `test_get_upcoming_includes_recurring_instances` -- instances включены
  - `test_get_recent_month_range` -- фильтрация по месяцу
  - `test_get_recent_sorting_desc` -- сортировка DESC
  - `test_get_recent_includes_recurring_instances` -- instances включены

### Step 4: Reconciliation modal глобализация (~30 min)
4a. В `calendar.py`:
  - Удалить `dcc.Store(id="calendar-refresh-trigger", data=None)` из `create_calendar_layout()` (строка 228).
  - Удалить вызов `create_reconciliation_modal()` из `create_calendar_layout()` (строка 256).
  - Удалить callback `refresh_calendar_after_reconciliation()` целиком (строки 1548-1620) -- дублирует `refresh_calendar_after_transaction()` (строка 1201) который уже слушает `global-transaction-trigger`.
  - Рефакторинг `apply_reconciliation()` (строка 1468): заменить `Output("calendar-refresh-trigger", "data")` на `Output("global-transaction-trigger", "data", allow_duplicate=True)`. Возвращать `{"source": "reconciliation", "action": "create", "timestamp": ...}` вместо `{"timestamp": ...}`.
4b. В `main.py`:
  - Добавить `from app.components.calendar import create_reconciliation_modal`.
  - Добавить `create_reconciliation_modal()` в app.layout после `create_wishlist_modal()`.

### Step 5: Dashboard кнопки "Сверка" -> Store trigger (~20 min)
- В `build_overview_cards()` (строки 310-318): заменить `dcc.Link(href="/calendar?open_recon=1")` на `dbc.Button(id="open-recon-from-dashboard-btn")`.
- В `_build_balance_banner()` (строки 55-63): заменить `dcc.Link(dbc.Button("Сверить баланс", ...), href="/calendar?open_recon=1")` на `dbc.Button("Сверить баланс", id="open-recon-from-dashboard-banner-btn", color="dark", size="sm", outline=True)`. Обертка dcc.Link полностью удаляется.
- Новый callback `open_recon_from_dashboard()` в `dashboard.py` с двумя Inputs:
  ```python
  @callback(
      Output("open-recon-trigger", "data", allow_duplicate=True),
      [
          Input("open-recon-from-dashboard-btn", "n_clicks"),
          Input("open-recon-from-dashboard-banner-btn", "n_clicks"),
      ],
      prevent_initial_call=True,
  )
  def open_recon_from_dashboard(kpi_clicks, banner_clicks):
      if kpi_clicks is None and banner_clicks is None:
          raise PreventUpdate
      return int(time.time() * 1000)
  ```

### Step 6: Cushion card readonly на Dashboard (~25 min)
- Новая функция `_build_cushion_card_readonly(user_id: int) -> dbc.Card` в `dashboard.py`:
  - Вызывает `CushionService.get_settings(user_id)` с try/except.
  - Рендерит упрощенную карточку: заголовок, статус, суммы, прогресс-бар.
  - Вместо `id="cushion-open-modal-btn"` -- `dcc.Link("Настройки", href="/goals")`.
  - Fallback при ошибке: карточка "Подушка не настроена" с ссылкой на /goals.
- В `_load_dashboard_components()`: вызвать `_build_cushion_card_readonly()` и вернуть как 6-й элемент.

### Step 7: Dashboard layout перестройка (~40 min)
- Удалить `build_recent_transactions_card()` (заменена на `_build_transactions_split_table()`).
- Добавить `html.Div(id="dashboard-upcoming-transactions")` в layout.
- Перестроить `create_dashboard_layout()`:
  ```
  dbc.Row([
      dbc.Col([  # width=8 (center content)
          KPI cards  (id="dashboard-overview-cards")
          Chart      (id="dashboard-cashflow-chart")
          dbc.Row([  # 2 колонки операций 50/50
              dbc.Col([id="dashboard-recent-transactions"], width=6),
              dbc.Col([id="dashboard-upcoming-transactions"], width=6),
          ])
      ], width=8),
      dbc.Col([  # width=4 (right column)
          wishlist_widget
          html.Div(id="dashboard-cushion-card")
          statistics_card  (id="dashboard-statistics-card")
      ], width=4),
  ])
  ```
- Обновить `_load_dashboard_components()`: возвращать 6 outputs (cards, chart, stats, recent, upcoming, cushion).
- Обновить `load_dashboard_data()` callback: 6 Outputs.
- Обновить `refresh_dashboard_after_crud()` callback: 6 Outputs.
- Формат таблиц: format_date_human() для дат, category во вторую строку, no "Completed" badge, amount RIGHT-aligned.
- Ссылки "Все операции" внизу каждой таблицы:
  - Recent: `/transactions?start=YYYY-MM-01&end=YYYY-MM-DD` (1-е..сегодня)
  - Upcoming: `/transactions?start=YYYY-MM-DD&end=YYYY-MM-LD` (сегодня..last_day)
- Recurring icon: если `is_recurring_instance`, показывать "🔁" перед описанием.

### Step 8: Sidebar card-контейнер (~25 min)
- Обернуть sidebar content в `dbc.Card(className="sidebar-card h-100")`.
- Убрать static `active=True` из nav_items (строка 59 sidebar.py: удалить `"active": True`).
- Добавить `id="sidebar-nav"` на `dbc.Nav` (строка 82 sidebar.py: `dbc.Nav(nav_links, vertical=True, className="mb-4")` -> `dbc.Nav(nav_links, vertical=True, className="mb-4", id="sidebar-nav")`).
- Callback `highlight_active_sidebar()`: Input("url", "pathname"), Output("sidebar-nav", "children"). Rebuilds 5 NavLink elements with `active=True` for matching pathname и `className` with `sidebar-nav-item-active`.
- CSS `sidebar.css`: `.sidebar-card`, `.sidebar-nav-item-active` (border-left 4px solid var(--color-primary)).

### Step 9: Transactions query params (~20 min)
- Новый callback `apply_url_date_filter()` в `transactions.py`:
  - Input: `url.search`, State: `url.pathname`
  - Guard: pathname != "/transactions" -> PreventUpdate
  - Parse `?start=YYYY-MM-DD&end=YYYY-MM-DD` using `urllib.parse.parse_qs`
  - Validate dates with `date.fromisoformat()` in try/except (invalid -> None)
  - Output: `filter-date-range.start_date`, `filter-date-range.end_date`
  - `load_transactions()` already reacts to filter-date-range changes -> automatic refresh.

### Step 10: Empty state CTA callback (~15 min)
- Callback `open_create_from_empty()` in `dashboard.py`:
  ```python
  @callback(
      [
          Output("create-modal", "is_open", allow_duplicate=True),
          Output("modal-source", "data", allow_duplicate=True),
      ],
      [
          Input("empty-recent-add-btn", "n_clicks"),
          Input("empty-upcoming-add-btn", "n_clicks"),
      ],
      prevent_initial_call=True,
  )
  def open_create_from_empty(recent_clicks, upcoming_clicks):
      if not ctx.triggered_id:
          raise PreventUpdate
      if recent_clicks is None and upcoming_clicks is None:
          raise PreventUpdate
      return True, "dashboard-empty"
  ```

### Step 11: CSS стили (~15 min)
- `.empty-state` в `custom.css`: text-align center, padding 40px, icon size 2.5rem.
- `.dashboard-split-table` -- row hover, consistent padding.
- `sidebar.css` (new file ~50 lines): `.sidebar-card`, active nav item border.

### Step 12: Финализация (~15 min)
- Black formatting.
- Flake8 check.
- Pytest (target >= 520 tests: 508 existing + 9 service + 3 formatter).
- Manual browser verification.

## Зависимости

- **Внутренние**: Batch 5.1 (format_rub, CSS variables) -- DONE.
- **Внутренние**: Batch 5.2 (daily cashflow chart, _load_dashboard_components) -- DONE.
- **Библиотечные**: dash, dash-bootstrap-components, plotly, sqlalchemy -- уже установлены.
- **Нет новых внешних зависимостей.**

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| `toggle_reconciliation_modal` не срабатывает с Dashboard (missing `open-reconciliation-btn` Input) | Низкая | `suppress_callback_exceptions=True` подставляет None; existing guard `open_clicks is None` корректно предотвращает ложное срабатывание. Тестировать вручную: Calendar recon button + Dashboard recon button (KPI) + Dashboard recon button (banner) |
| Удаление `calendar-refresh-trigger` ломает Calendar refresh после сверки | Низкая | `refresh_calendar_after_transaction()` уже слушает `global-transaction-trigger` и обновляет calendar grid/stats/state. apply_reconciliation теперь пишет в global-transaction-trigger => Calendar обновится через существующий callback (line 1201) |
| `get_recent_transactions()` пустой список в начале месяца | Средняя | **Intentional semantic change** per spec. Empty state UI с CTA "Добавить" обрабатывает этот кейс. Документировано в docstring |
| Duplicate Output конфликт: `apply_reconciliation` Output `global-transaction-trigger` vs `create_transaction` | Низкая | Все используют `allow_duplicate=True`. Dash корректно обрабатывает multiple callbacks writing to same Output с этим флагом |
| Layout ломается при resize | Средняя | 8/4 split с Bootstrap responsive col-lg-8/col-lg-4. На < 768px падает в single column. Desktop-first approach |
| Sidebar callback может конфликтовать с NavLink.active prop | Низкая | Убрать static `active=True`, управлять исключительно через callback children rebuild. 5 элементов -- negligible cost при каждой навигации |

## Requirements Traceability Matrix (RTM)

| # | Requirement (из спецификации) | Секция spec | Реализация в solution | Тип |
|---|------|------|------|------|
| 1 | FR-1: DashboardService.get_upcoming_transactions() | brief FR-1 | Step 2: новый метод | Service |
| 2 | FR-2: get_recent_transactions() для диапазона 1-е..сегодня | brief FR-2 | Step 2: рефакторинг с reference_date | Service |
| 3 | FR-3: Две колонки 50/50 Recent + Upcoming | brief FR-3, spec секция 1 | Step 7: dbc.Row с width=6 + width=6 | Layout |
| 4 | FR-4: Формат таблиц (дата "5 февраля", категория 2-я строка, нет "Completed", amount RIGHT) | brief FR-4, spec секция 1 | Step 1: format_date_human(), Step 7: _build_transactions_split_table() | UI |
| 5 | FR-5: Ссылки "Все операции" с query params дат | brief FR-5 | Step 7: link_href с ?start=&end= | Routing |
| 6 | FR-6: /transactions обрабатывает ?start=&end= | brief FR-6 | Step 9: apply_url_date_filter() callback | Callback |
| 7 | FR-7: Правая колонна Wishlist + Safety Cushion | brief FR-7, spec секция 1 | Step 6: _build_cushion_card_readonly(), Step 7: Col width=4 | Layout |
| 8 | FR-8: Sidebar в dbc.Card с зеленым акцентом | brief FR-8, spec секция 1 | Step 8: dbc.Card wrapper + callback + CSS | UI+Callback |
| 9 | FR-9: Модал "Сверка" с Dashboard | brief FR-9, spec секция 1 | Steps 4-5: глобализация modal + Store trigger | Callback |
| 10 | FR-10: Пустые состояния с иконкой + текст + CTA | brief FR-10, spec секция 1 | Step 7: _build_empty_state(), Step 10: callback | UI+Callback |
| 11 | FR-11: CTA "Добавить" открывает create-modal | brief FR-11 | Step 10: open_create_from_empty() | Callback |
| 12 | Recurring icon в таблицах | spec секция 1 | Step 2: is_recurring_instance, Step 7: emoji rendering | Data+UI |
| 13 | Unit тесты >= 520 | brief NFR | Steps 1, 3: +12 тестов (508+12=520) | Test |

## Blast Radius

### Прямые изменения (файлы которые будут изменены)

1. **`app/services/dashboard_service.py`** -- +get_upcoming_transactions(), рефакторинг get_recent_transactions() (reference_date, recurring filter), +is_recurring_instance в RecentTransaction, ~+80 строк
2. **`app/utils/formatters.py`** -- +MONTH_NAMES_RU_GENITIVE dict, +format_date_human(), ~+15 строк
3. **`app/components/dashboard.py`** -- перестройка layout, +_build_transactions_split_table(), +_build_empty_state(), +_build_cushion_card_readonly(), обновление _load_dashboard_components (6 outputs), +2 callbacks (open_recon с 2 Inputs, open_empty), замена recon_button на dbc.Button в build_overview_cards(), замена dcc.Link на dbc.Button в _build_balance_banner(), ~+350 строк / -80 строк переработки
4. **`app/components/sidebar.py`** -- dbc.Card обертка, id="sidebar-nav" на dbc.Nav, callback highlight_active_sidebar(), ~+50 строк
5. **`app/components/calendar.py`** -- удалить calendar-refresh-trigger Store (-1 line), удалить create_reconciliation_modal() из layout (-1 line), удалить refresh_calendar_after_reconciliation callback (~-80 lines), рефакторинг apply_reconciliation Output (~5 lines changed)
6. **`app/components/transactions.py`** -- +apply_url_date_filter callback (~25 строк)
7. **`app/main.py`** -- +import create_reconciliation_modal, +вызов в layout (~3 строки)
8. **`app/assets/custom.css`** -- +.empty-state, +.dashboard-split-table (~30 строк)
9. **`app/assets/sidebar.css`** -- НОВЫЙ файл (~50 строк)
10. **`tests/test_dashboard_service.py`** -- +9 unit тестов (~180 строк)
11. **`tests/test_formatters.py`** -- +3 unit теста (~25 строк)

### Связанные файлы (могут быть затронуты)

- `app/components/wishlist.py` -- `build_wishlist_widget()` используется в dashboard layout, не меняется
- `app/components/transaction_modals.py` -- глобальный create-modal, используется CTA из empty state, не меняется
- `app/services/reconciliation_service.py` -- используется модалом сверки, не меняется
- `app/services/cushion_service.py` -- используется _build_cushion_card_readonly(), не меняется
- `app/components/goals.py` -- cushion callbacks остаются локальными в goals, не меняются
- `app/schema/dashboard.py` -- RecentTransaction TypedDict в dashboard_service.py, не в schema (не меняется)
- `app/services/__init__.py` -- может понадобиться экспорт get_upcoming_transactions type

### Проверить после реализации

- [ ] Dashboard загружается < 2 сек (3 новых SQL запроса: recent, upcoming, cushion)
- [ ] Calendar reconciliation modal работает после глобализации (open-reconciliation-btn on Calendar)
- [ ] Dashboard reconciliation modal работает с KPI кнопки (open-recon-from-dashboard-btn)
- [ ] Dashboard reconciliation modal работает с banner кнопки (open-recon-from-dashboard-banner-btn)
- [ ] После сверки с Dashboard -- KPI, таблицы и chart обновляются сразу
- [ ] После сверки с Calendar -- calendar grid и stats обновляются сразу (через global-transaction-trigger -> refresh_calendar_after_transaction)
- [ ] Goals cushion card и modal работают как раньше (нет конфликта ID)
- [ ] Dashboard cushion card readonly показывает актуальные данные при навигации
- [ ] Transactions page работает с query params (?start=&end=) и без них
- [ ] Sidebar active highlight работает на всех 5 страницах
- [ ] Global transaction trigger обновляет обе таблицы операций на Dashboard
- [ ] Wishlist widget на Dashboard работает (модал, callbacks)
- [ ] Пустые состояния отображаются корректно при отсутствии данных
- [ ] CTA "Добавить" в пустом состоянии открывает create-modal
- [ ] Нет duplicate ID ошибок в browser console
- [ ] Recurring instances отображаются в таблицах с иконкой 🔁
- [ ] Формат дат "5 февраля" корректен для всех месяцев

## Учтённые замечания из критики v1

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🔴 1. `apply_reconciliation` callback writes to `calendar-refresh-trigger` -- not available on Dashboard | **РЕШЕНО**: Заменяем Output `calendar-refresh-trigger` на `global-transaction-trigger` (с `allow_duplicate=True`). Удаляем `calendar-refresh-trigger` Store и callback `refresh_calendar_after_reconciliation()`. |
| 🔴 2. `handle_calendar_query_params` blocks Dashboard reconciliation via query param | **РЕШЕНО**: Dashboard кнопки заменены с `dcc.Link(href="/calendar?open_recon=1")` на `dbc.Button` с прямой записью в `open-recon-trigger` Store. Оба места: KPI card + banner. |
| 🔴 3. Cushion Stores/callbacks local to goals -- duplicate IDs | **РЕШЕНО**: `_build_cushion_card_readonly()` в `dashboard.py`, НЕ вызывает `_build_cushion_card()`, без кнопок с совпадающими ID. |
| 🟡 4. `get_recent_transactions()` breaking change | **РЕШЕНО**: Intentional semantic change, единственный callsite подтвержден, empty state UI обрабатывает пустой список. |
| 🟡 5. Sidebar callback pattern -- dbc.Nav conflict | **РЕШЕНО**: `dbc.Nav` получает `id="sidebar-nav"`, static `active=True` убран, callback rebuilds children. |
| 🟡 6. Reconciliation `open-reconciliation-btn` Input Calendar-specific | **РЕШЕНО**: `suppress_callback_exceptions=True` подставляет None, existing guard обрабатывает. |
| 🟡 7. No Dashboard refresh after reconciliation | **РЕШЕНО**: `apply_reconciliation()` пишет в `global-transaction-trigger`, Dashboard слушает его. |
| 🟡 8. Transactions query params -- no test coverage | **РЕШЕНО**: callback с edge case handling, manual checks в checklist. |
| 🟢 9. Recurring instances excluded | **РЕШЕНО**: Новый SQL фильтр, поле `is_recurring_instance`, иконка 🔁. |
| 🟢 10. Layout 8/4 vs 9/3 | **РЕШЕНО**: Оставлен 8/4 split. |
| 🟢 11. format_date_human() unit tests | **РЕШЕНО**: 3 теста в Step 1. |

## Учтённые замечания из критики v2

| Замечание из critique v2 | Как решено |
|--------------------------|------------|
| 🟡 1. _build_balance_banner() содержит dcc.Link на /calendar?open_recon=1 | **РЕШЕНО**: В Step 5 уточнено: `_build_balance_banner()` (строки 55-63 dashboard.py) -- dcc.Link заменяется на `dbc.Button("Сверить баланс", id="open-recon-from-dashboard-banner-btn", color="dark", size="sm", outline=True)`. Обертка dcc.Link удаляется. Кнопка обрабатывается callback `open_recon_from_dashboard()` как второй Input. Полный код приведен в секции "Ключевые интерфейсы". |
| 🟢 2. Sidebar dbc.Nav id diff | **РЕШЕНО**: В Step 8 добавлен явный diff: строка 82 sidebar.py `dbc.Nav(nav_links, vertical=True, className="mb-4")` -> `dbc.Nav(nav_links, vertical=True, className="mb-4", id="sidebar-nav")`. Также строка 59: удалить `"active": True`. |
| 🟢 3. Test count projection | **Информационное**: Solution проецирует >= 520 тестов (508 + 9 service + 3 formatter), что выше brief target >= 515. |
| 🟢 4. Banner кнопка может потребовать третий Input | **РЕШЕНО**: По решению пользователя, banner кнопка добавляется как второй Input в callback `open_recon_from_dashboard()`. ID: `open-recon-from-dashboard-banner-btn`. Callback имеет 2 Inputs (KPI btn + banner btn). |

## Ответы на вопросы критика v1

1. **Вопрос:** Recurring transactions in Recent/Upcoming tables?
   **Ответ:** Да, включить recurring instances. Шаблоны исключаются. SQL фильтр: `NOT (is_recurring=True AND recurring_parent_id IS NULL)`.

2. **Вопрос:** Dashboard cushion refresh?
   **Ответ:** Re-render при навигации через `_load_dashboard_components()`. Также через `refresh_dashboard_after_crud` при global-transaction-trigger.

3. **Вопрос:** Layout change 8/4 vs 9/3?
   **Ответ:** Оставить 8/4 split. Wishlist уже рассчитан на width=4.

## Ответы на вопросы критика v2

1. **Вопрос:** Banner кнопка ID и отдельный callback vs второй Input?
   **Ответ:** По решению пользователя -- второй Input в единый callback `open_recon_from_dashboard()`. ID: `open-recon-from-dashboard-banner-btn`. Один callback, два Inputs, один Output (`open-recon-trigger`).
