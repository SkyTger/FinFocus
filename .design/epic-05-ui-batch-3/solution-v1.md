# Solution v1: Dashboard Layout Redesign

## Обзор решения

Реализация финального layout Dashboard требует изменений в 5 слоях: service (новый метод), UI-строитель (новые функции), layout (перекомпоновка), callbacks (новые/расширенные), CSS (стили). Ключевое архитектурное решение -- модал сверки и cushion-card перемещаются в глобальный scope (main.py) для доступности с Dashboard.

## Архитектура

### Слой 1: DashboardService (данные)
Расширение существующего сервиса двумя методами:
- `get_upcoming_transactions()` -- новый метод
- `get_recent_transactions()` -- рефакторинг существующего для диапазона дат

### Слой 2: Formatters (утилиты)
Новая функция `format_date_human()` для формата "5 февраля" (генитив русских месяцев).

### Слой 3: Dashboard UI (компоненты)
- `_build_transactions_table()` -- новая функция построения таблицы по спецификации
- `_build_empty_state()` -- новая функция пустого состояния
- `build_cushion_card_dashboard()` -- обертка для cushion на Dashboard
- Перестройка `create_dashboard_layout()` -- 3-колоночный layout (sidebar | content | right column)

### Слой 4: Sidebar (навигация)
- Обертка в `dbc.Card`
- Callback для активного пункта меню

### Слой 5: Reconciliation modal (глобализация)
- Извлечение `create_reconciliation_modal()` из calendar.py в main.py
- Callback для открытия с Dashboard

## Файловая структура

```
app/
  services/
    dashboard_service.py       # +get_upcoming_transactions(), рефакторинг get_recent_transactions()
  utils/
    formatters.py              # +format_date_human(), +MONTH_NAMES_RU_GENITIVE
  components/
    dashboard.py               # Перестройка layout, новые build-функции, новые callbacks
    sidebar.py                 # dbc.Card обертка, callback active item
    calendar.py                # Извлечение reconciliation modal в отдельную функцию
    goals.py                   # Публичный build_cushion_card_standalone()
    transactions.py            # Обработка query params ?start=&end=
  assets/
    custom.css                 # +.empty-state, +.transactions-split-table
    sidebar.css                # Новый файл: sidebar card стили
  main.py                      # +reconciliation modal в глобальный layout, +cushion Stores
tests/
  test_dashboard_service.py    # +7 тестов для get_upcoming/recent_transactions
```

## Ключевые интерфейсы

### 1. DashboardService.get_upcoming_transactions()

```python
def get_upcoming_transactions(
    self,
    user_id: int,
    limit: int = 5,
    reference_date: date | None = None,
) -> list[RecentTransaction]:
    """Получает предстоящие операции (сегодня..конец месяца).

    Args:
        user_id: ID пользователя
        limit: Максимальное количество (по умолчанию 5)
        reference_date: Дата отсчета (по умолчанию сегодня)

    Returns:
        list[RecentTransaction]: предстоящие операции, сортировка по date ASC

    Note:
        - Исключает recurring шаблоны (is_recurring=True без parent)
        - Включает today (>= reference_date)
        - Сортировка: transaction_date ASC, id ASC
    """
    if reference_date is None:
        reference_date = date.today()

    _, last_day_num = monthrange(reference_date.year, reference_date.month)
    end_of_month = date(reference_date.year, reference_date.month, last_day_num)

    transactions = (
        self.session.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .filter(Transaction.is_recurring == False)
        .filter(Transaction.recurring_parent_id == None)
        .filter(Transaction.transaction_date >= reference_date)
        .filter(Transaction.transaction_date <= end_of_month)
        .order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
        .limit(limit)
        .all()
    )

    return [
        RecentTransaction(
            id=t.id,
            description=t.description,
            category_name=t.category_rel.name if t.category_rel else None,
            category_icon=t.category_rel.icon if t.category_rel else None,
            date=t.transaction_date.isoformat(),
            amount=t.amount,
            transaction_type=t.transaction_type.value,
        )
        for t in transactions
    ]
```

### 2. DashboardService.get_recent_transactions() (рефакторинг)

```python
def get_recent_transactions(
    self,
    user_id: int,
    limit: int = 5,
    reference_date: date | None = None,
) -> list[RecentTransaction]:
    """Получает недавние операции (1 число..сегодня включительно).

    Args:
        user_id: ID пользователя
        limit: Максимальное количество (по умолчанию 5)
        reference_date: Дата отсчета (по умолчанию сегодня)

    Returns:
        list[RecentTransaction]: недавние операции, сортировка по date DESC
    """
    if reference_date is None:
        reference_date = date.today()

    first_of_month = reference_date.replace(day=1)

    transactions = (
        self.session.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .filter(Transaction.is_recurring == False)
        .filter(Transaction.recurring_parent_id == None)
        .filter(Transaction.transaction_date >= first_of_month)
        .filter(Transaction.transaction_date <= reference_date)
        .order_by(desc(Transaction.transaction_date), desc(Transaction.id))
        .limit(limit)
        .all()
    )
    # ... same mapping
```

### 3. format_date_human()

```python
MONTH_NAMES_RU_GENITIVE = {
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
```

### 4. _build_transactions_table() (dashboard.py)

```python
def _build_transactions_table(
    transactions: list[RecentTransaction],
    title: str,
    empty_message: str,
    link_text: str,
    link_href: str,
    empty_btn_id: str,
) -> dbc.Card:
    """Создает карточку с таблицей операций.

    Args:
        transactions: Список транзакций
        title: Заголовок ("Недавние операции" / "Предстоящие операции")
        empty_message: Текст пустого состояния
        link_text: Текст ссылки "Все операции: ..."
        link_href: URL с фильтром дат
        empty_btn_id: ID кнопки "Добавить" для пустого состояния
    """
```

### 5. Sidebar callback

```python
@callback(
    Output("sidebar-nav-links", "children"),
    Input("url", "pathname"),
)
def highlight_active_sidebar(pathname: str) -> list:
    """Подсвечивает активный пункт меню в sidebar."""
```

## Модель данных

Модель данных не изменяется. `RecentTransaction` TypedDict уже содержит все нужные поля:
- `id`, `description`, `category_name`, `category_icon`, `date`, `amount`, `transaction_type`

Для поля `is_recurring` можно расширить `RecentTransaction`:

```python
class RecentTransaction(TypedDict):
    id: int
    description: str | None
    category_name: str | None
    category_icon: str | None
    date: str
    amount: Decimal
    transaction_type: str
    is_recurring: bool  # Новое поле для иконки ⟳
```

## Обработка ошибок

1. **Service layer**: try/except с logger.error, возврат пустого списка (fail-safe, аналогично существующему `get_recent_transactions()`)
2. **Callbacks**: try/except с logger.error и raise PreventUpdate (как в существующих callbacks)
3. **Reconciliation modal на Dashboard**: если не удается загрузить баланс -- показываем "Ошибка" (как в calendar.py toggle_reconciliation_modal)
4. **Cushion card на Dashboard**: если не удается загрузить settings -- показываем "не настроена" (fail-safe)
5. **Empty state CTA**: guard clauses по ADR-003 (n_clicks is None -> raise PreventUpdate)

## План реализации

### Step 1: Расширение formatters.py (~15 min)
- Добавить `MONTH_NAMES_RU_GENITIVE` dict
- Добавить `format_date_human(date_obj) -> str`
- Не ломает существующий `format_date()` (DD.MM.YYYY)

### Step 2: Расширение DashboardService (~30 min)
- Добавить параметр `reference_date` в `get_recent_transactions()` с date-range фильтрами (1-е число..сегодня)
- Добавить поле `is_recurring` в `RecentTransaction` TypedDict
- Добавить `get_upcoming_transactions()` (сегодня..конец месяца, ASC)
- **ВАЖНО**: Обратная совместимость -- `reference_date=None` дает today, `get_recent_transactions()` без reference_date работает как раньше (хотя семантика меняется: вместо глобального DESC без даты -- теперь за текущий месяц)

### Step 3: Unit тесты для новых методов (~30 min)
- 7 тестов в `tests/test_dashboard_service.py`:
  - `test_get_upcoming_basic`, `test_get_upcoming_empty`, `test_get_upcoming_limit`
  - `test_get_upcoming_sorting_asc`, `test_get_upcoming_edge_of_month`
  - `test_get_recent_transactions_month_range`, `test_get_recent_transactions_sorting_desc`

### Step 4: Reconciliation modal -- глобализация (~30 min)
- В `calendar.py`: `create_reconciliation_modal()` уже является отдельной функцией, но рендерится внутри `create_calendar_layout()`. **Решение**: переместить вызов `create_reconciliation_modal()` в `main.py` (после `create_transaction_modals()`)
- Удалить вызов `create_reconciliation_modal()` из `create_calendar_layout()`
- Callbacks сверки (`toggle_reconciliation_modal`, `update_reconciliation_preview`, `apply_reconciliation`) останутся в `calendar.py` -- они уже работают через глобальные IDs
- **Риск**: callback `toggle_reconciliation_modal` имеет Input `"open-reconciliation-btn"` (кнопка на Calendar) -- нужно добавить альтернативный Input для Dashboard. Решение: использовать `open-recon-trigger` Store (уже глобальный в main.py), расширить его для Dashboard trigger.

### Step 5: Dashboard кнопка "Сверка" -> reconciliation modal (~20 min)
- В `build_overview_cards()`: изменить `recon_button` с `dcc.Link(href="/calendar?open_recon=1")` на кнопку с ID, которая триггерит `open-recon-trigger` Store напрямую
- Новый callback `open_recon_from_dashboard()`: клик на кнопку -> устанавливает timestamp в `open-recon-trigger`
- Callback `toggle_reconciliation_modal` (в calendar.py) уже реагирует на `Input("open-recon-trigger", "data")` -- будет работать.
- **ВАЖНО**: Нужно убрать guard `if pathname == "/calendar"` из `handle_calendar_query_params` в main.py -- или лучше: Dashboard кнопка не использует query params, а напрямую пишет в Store. Для этого нужен отдельный callback:
  ```python
  @callback(
      Output("open-recon-trigger", "data", allow_duplicate=True),
      Input("open-recon-from-dashboard-btn", "n_clicks"),
      prevent_initial_call=True,
  )
  def open_recon_from_dashboard(n_clicks):
      if n_clicks is None:
          raise PreventUpdate
      return int(time.time() * 1000)
  ```

### Step 6: Cushion card на Dashboard (~30 min)
- В `goals.py`: создать публичную функцию `build_cushion_card_standalone(user_id: int) -> dbc.Card` которая:
  1. Загружает `CushionService.get_settings(user_id)`
  2. Вызывает `_build_cushion_card(settings)`
  3. Обрабатывает ошибки (fallback "не настроена")
- В `dashboard.py`: импортировать `build_cushion_card_standalone` и использовать в правой колонне
- **Проблема**: Cushion modal и callbacks (`cushion-open-modal-btn`, `cushion-modal`, etc.) живут в goals.py и рендерятся только в goals layout. Кнопка "Настроить"/"Изменить" в карточке cushion имеет `id="cushion-open-modal-btn"` -- если этот ID дублируется на Dashboard, будет конфликт. **Решение**: на Dashboard карточка cushion показывается в read-only режиме (без кнопок "Настроить"/"Изменить"), вместо этого -- ссылка "Перейти к настройке" -> /goals. Это избегает конфликта ID и необходимости перемещать сложный cushion modal в глобальный scope.

### Step 7: Dashboard layout перестройка (~45 min)
- Убрать старую `build_recent_transactions_card()` и заменить на `_build_transactions_table()` x2
- Перестроить `create_dashboard_layout()`:
  ```
  dbc.Row([
      dbc.Col([  # width=9 (центральный контент)
          KPI cards (4 в ряд)
          Chart (daily/yearly)
          dbc.Row([  # 2 колонки операций 50/50
              dbc.Col([recent_table], width=6),
              dbc.Col([upcoming_table], width=6),
          ])
      ], width=9),
      dbc.Col([  # width=3 (правая колонна)
          wishlist_widget
          cushion_card_standalone
      ], width=3),
  ])
  ```
- Обновить `_load_dashboard_components()`: загрузить и recent, и upcoming transactions
- Добавить Output для upcoming transactions в callbacks

### Step 8: Sidebar card-контейнер (~30 min)
- Обернуть sidebar content в `dbc.Card`
- Заменить static `active=True` на callback `highlight_active_sidebar(pathname)`
- Стили: border-left 4px solid #2ecc71 для активного пункта, белый фон для карточки
- Новый файл `sidebar.css`

### Step 9: Transactions query params (~20 min)
- В `load_transactions()` callback: добавить Input для `url.search`
- Парсить `?start=YYYY-MM-DD&end=YYYY-MM-DD`
- Предзаполнить `filter-date-range` start_date/end_date
- Альтернативный подход (проще): callback `apply_url_date_filter` реагирует на pathname + search, устанавливает start/end в DatePickerRange, а `load_transactions` уже реагирует на изменения DatePickerRange

### Step 10: CSS стили (~15 min)
- `.empty-state` в `custom.css`: text-align center, padding 40px, стили иконки и текста
- `.transactions-split-table` -- hover на строках, separator
- `sidebar.css`: `.sidebar-card`, `.sidebar-nav-item.active`

### Step 11: Callbacks для пустых состояний и refresh (~20 min)
- Callback `open_create_from_empty_state()` -- клик на CTA "Добавить" -> открывает create-modal
- Обновить `_load_dashboard_components()` для возврата 5 outputs (cards, chart, stats, recent, upcoming)
- Обновить `load_dashboard_data` и `refresh_dashboard_after_crud` -- добавить Output для upcoming

### Step 12: Финализация (~15 min)
- Black formatting
- Flake8 check
- Pytest (>= 515 tests)
- Manual verification in browser

## Зависимости

- **Внутренние**: Batch 5.1 (format_rub, CSS-переменные, KPI cards) -- DONE
- **Внутренние**: Batch 5.2 (daily cashflow chart, _load_dashboard_components) -- DONE
- **Библиотечные**: dash, dash-bootstrap-components, plotly, sqlalchemy -- уже установлены
- **Нет новых зависимостей**

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Reconciliation modal callbacks конфликтуют при глобализации (duplicate Output IDs) | Средняя | Callbacks уже используют unique IDs (reconciliation-*); тестировать что open-recon-trigger работает и с Calendar, и с Dashboard |
| Cushion modal ID конфликт при дублировании на Dashboard | Высокая | **Решено**: cushion на Dashboard в read-only режиме (ссылка на /goals вместо модала). Избегаем duplicate ID |
| get_recent_transactions() семантика меняется (теперь по месяцу вместо глобального) | Средняя | Добавить reference_date параметр; старое поведение (без reference_date) = новое (текущий месяц). Проверить что другие callsites не ломаются |
| Sidebar callback конфликтует с existing NavLink.active | Низкая | Убрать static active=True из nav_items, управлять через callback className |
| Transactions query params не парсятся корректно | Низкая | Unit-тесты для URL parsing; использовать urllib.parse.parse_qs |
| Layout responsive ломается при 3-column layout | Средняя | Desktop-first, тестировать на 1440px+; 768px breakpoint через Bootstrap col-lg-9/col-lg-3 |

## Requirements Traceability Matrix (RTM)

| # | Requirement (дословно из спецификации) | Секция spec | Реализация в solution | Тип |
|---|----------------------------------------|-------------|----------------------|-----|
| 1 | Split таблицы операций на 2 колонки 50/50: "Недавние" (1..сегодня) и "Предстоящие" (сегодня..конец месяца) | batch-3.md:Задача 3-4, dashboard_ui_spec.md:секция 1 (Нижняя часть) | Step 7: перестройка create_dashboard_layout() с dbc.Row 50/50 | Layout |
| 2 | Метод DashboardService.get_upcoming_transactions() для предстоящих операций | batch-3.md:Задача 1 | Step 2: новый метод в dashboard_service.py | Service |
| 3 | Формат таблиц по спецификации (без "Completed" бейджей, категория/тип во вторую строку) | batch-3.md:Задача 3, dashboard_ui_spec.md:секция 4 | Step 7: _build_transactions_table() убирает Badge, добавляет вторую строку | UI |
| 4 | Ссылки "Все операции" -> /transactions с фильтром дат | batch-3.md:Задача 5 | Step 7: CardFooter с link_href, Step 9: transactions.py query params | UI+Routing |
| 5 | Правая колонна: перенести Wishlist + Safety Cushion с /goals | batch-3.md:Задача 6, dashboard_ui_spec.md:секция 1 (Правая колонна) | Step 6: cushion standalone, Step 7: layout Col width=3 | Layout |
| 6 | Sidebar как card-контейнер (обернуть в dbc.Card, зелёный акцент на активном пункте) | batch-3.md:Задача 7, dashboard_ui_spec.md:секция 1 (Левый сайдбар) | Step 8: sidebar.py refactor + callback + sidebar.css | UI+Callback |
| 7 | Модал "Сверка" доступен с Dashboard (кнопка на Total Balance KPI) | batch-3.md:Задача 8, dashboard_ui_spec.md:секция 5 | Step 4: глобализация modal, Step 5: Dashboard button + callback | Callback |
| 8 | Пустые состояния: иконка + текст + CTA "Добавить" | batch-3.md:Задача 9, dashboard_ui_spec.md:секция 6 | Step 7: _build_empty_state(), Step 11: callback open_create_from_empty | UI+Callback |
| 9 | Дата человеческий формат ("5 февраля") | batch-3.md:Задача 3 (Формат: Дата) | Step 1: format_date_human() в formatters.py | Utility |
| 10 | Иконка recurring (⟳) | batch-3.md:Задача 3 (Описание строка 1) | Step 2: is_recurring в RecentTransaction, Step 7: отображение ⟳ | Data+UI |
| 11 | Unit тесты для get_upcoming_transactions() | batch-3.md:Задача 10 | Step 3: 7 тестов в test_dashboard_service.py | Test |
| 12 | Responsive: на 768px single-column | batch-3.md:Задача 4, dashboard_ui_spec.md:секция 7 | CSS @media breakpoints, Bootstrap responsive classes | CSS |

## Blast Radius

### Прямые изменения (файлы, которые будут модифицированы)

1. **`app/services/dashboard_service.py`** -- +get_upcoming_transactions(), рефакторинг get_recent_transactions() (добавление reference_date, is_recurring), ~+100 строк
2. **`app/utils/formatters.py`** -- +MONTH_NAMES_RU_GENITIVE, +format_date_human(), ~+20 строк
3. **`app/components/dashboard.py`** -- основная перестройка: новый layout, _build_transactions_table(), _build_empty_state(), обновление callbacks (5 outputs вместо 4), обновление _load_dashboard_components(), новый callback open_recon_from_dashboard, ~+300 строк / -100 строк переработки
4. **`app/components/sidebar.py`** -- обертка в dbc.Card, callback highlight_active_sidebar(), ~+40 строк
5. **`app/components/calendar.py`** -- удалить вызов create_reconciliation_modal() из create_calendar_layout(), ~-1 строка
6. **`app/components/goals.py`** -- публичная функция build_cushion_card_standalone(), ~+25 строк
7. **`app/components/transactions.py`** -- обработка query params ?start=&end= в load_transactions() или новый callback, ~+30 строк
8. **`app/main.py`** -- +create_reconciliation_modal() в глобальный layout, ~+5 строк
9. **`app/assets/custom.css`** -- +.empty-state, +.dashboard-transactions-table стили, ~+40 строк
10. **`app/assets/sidebar.css`** -- НОВЫЙ файл: .sidebar-card, .sidebar-nav-item.active, ~50 строк
11. **`tests/test_dashboard_service.py`** -- +7 unit тестов, ~+120 строк

### Связанные файлы (не меняются, но влияют/зависят)

- `app/components/wishlist.py` -- `build_wishlist_widget()` уже используется в dashboard.py, не меняется
- `app/components/transaction_modals.py` -- глобальный create-modal, используется CTA из пустых состояний
- `app/services/reconciliation_service.py` -- используется модалом сверки, не меняется
- `app/services/cushion_service.py` -- используется для cushion card, не меняется
- `app/schema/dashboard.py` -- TypedDicts, не меняется
- `app/services/__init__.py` -- может понадобиться экспорт новых типов
- `app/components/__init__.py` -- может понадобиться экспорт build_cushion_card_standalone

### Проверить после реализации
- [ ] Dashboard загружается < 2 сек (2 новых SQL запроса)
- [ ] Calendar reconciliation modal работает как раньше (после глобализации)
- [ ] Goals cushion card и modal работают как раньше (не ломается при появлении Dashboard cushion)
- [ ] Transactions page работает с query params (?start=&end=) и без них
- [ ] Sidebar active highlight работает на всех страницах (/dashboard, /calendar, /goals, /transactions, /analytics)
- [ ] Global transaction trigger обновляет обе таблицы операций на Dashboard
- [ ] Wishlist widget на Dashboard работает (модал открывается, callbacks функционируют)
- [ ] "Сверка" с Dashboard создает ADJUSTMENT и обновляет KPI/таблицы сразу
- [ ] Пустые состояния отображаются корректно при отсутствии данных
- [ ] Нет duplicate ID ошибок в browser console
