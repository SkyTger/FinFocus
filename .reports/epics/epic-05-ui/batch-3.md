# Батч 3: Layout — операции + правая колонна + sidebar

**Epic**: Epic-05-UI (Dashboard UI Redesign)
**Дата старта**: TBD (после батча 2)
**Статус**: 🔄 Планирование
**Протокол**: 0023-dashboard-layout

---

## 🎯 Цель батча

Завершить Dashboard UI redesign — реализовать полный layout по спецификации:
1. Split таблицы операций на 2 колонки 50/50: "Недавние" (1..сегодня) и "Предстоящие" (сегодня..конец месяца)
2. Метод `DashboardService.get_upcoming_transactions()` для предстоящих операций
3. Формат таблиц по спецификации (без "Completed" бейджей, категория/тип во вторую строку)
4. Ссылки "Все операции" → /transactions с фильтром дат
5. Правая колонна: перенести Wishlist + Safety Cushion с /goals
6. Sidebar как card-контейнер (обернуть в dbc.Card, зелёный акцент на активном пункте)
7. Модал "Сверка" доступен с Dashboard (кнопка на Total Balance KPI)
8. Пустые состояния: иконка + текст + CTA "Добавить"

**Приоритет**: Must Have — финальный батч Epic-05, завершает Dashboard UI redesign.

---

## ✅ Задачи (детальный checklist)

### Задача 1: Метод `get_upcoming_transactions()`
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1 (Нижняя часть Dashboard)`

**Сигнатура**:
```python
def get_upcoming_transactions(
    self,
    user_id: int,
    limit: int = 5
) -> list[TransactionData]:
    """
    Возвращает предстоящие операции (сегодня → конец месяца).

    Логика:
    1. Определить диапазон: today → конец текущего месяца
    2. Получить операции из TransactionService
    3. Сортировка: дата ASC (ближайшие первыми)
    4. Limit: максимум N операций

    Returns:
        list[TransactionData] (максимум limit элементов)
    """
```

**Детали реализации**:
- [ ] Вычислить диапазон:
  - start_date = datetime.date.today()
  - end_date = последнее число текущего месяца (calendar.monthrange())
- [ ] Получить операции:
  - `TransactionService.get_by_date_range(user_id, start_date, end_date)`
- [ ] Фильтрация:
  - Исключить TRANSFER? (или включить, по спецификации не ясно)
  - Включить recurring операции (если они попадают в диапазон)
- [ ] Сортировка: по date ASC
- [ ] Limit: `[:limit]`
- [ ] Преобразовать в TransactionData (уже есть в TransactionService)

**Файлы**: `app/services/dashboard_service.py`

---

### Задача 2: Метод `get_recent_transactions()` (расширить существующий?)
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1 (Нижняя часть Dashboard)`

**Проверка**: Уже есть `DashboardService.get_recent_transactions()`?
- [ ] Если есть — расширить для диапазона "1 число..сегодня":
  - start_date = первое число текущего месяца
  - end_date = datetime.date.today()
  - Сортировка: по date DESC (последние первыми)
  - Limit: 5
- [ ] Если нет — создать аналогично `get_upcoming_transactions()`

**Файлы**: `app/services/dashboard_service.py`

---

### Задача 3: UI таблицы операций (2 колонки 50/50)
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1 (Нижняя часть Dashboard), секция 4 (Список операций)**

**Действия**:
- [ ] Создать функцию `_build_transactions_table()` в `app/components/dashboard.py`:
  - Параметры: `transactions: list[TransactionData]`, `title: str`, `empty_message: str`, `link_text: str`, `link_href: str`
  - Возвращает: dbc.Card с таблицей
- [ ] Структура карточки:
  ```python
  dbc.Card([
      dbc.CardHeader(title),  # "Недавние операции" или "Предстоящие операции"
      dbc.CardBody([
          # Если transactions пустой → empty state
          # Иначе → таблица
      ]),
      dbc.CardFooter([
          html.A(link_text, href=link_href, className="link-show-all")
      ])
  ])
  ```
- [ ] Таблица (если есть операции):
  - Столбцы: Дата | Описание/категория | Сумма
  - Формат:
    - **Дата**: `5 февраля` (не `2026-02-05`, человеческий формат)
    - **Описание**:
      - Строка 1: transaction.description + иконка (если recurring → ⟳)
      - Строка 2: category.name (серый, 13px) или "Без категории"
    - **Сумма**: `format_rub()`, выравнивание RIGHT
      - Доход: зелёный (`#27ae60`), с `+` знаком
      - Расход: красный (`#e74c3c`), с `−` знаком
  - Высота строки: 48-56px (две строки текста)
  - Separator: `1px solid #ecf0f1`
  - Hover: `rgba(0,0,0,0.02)` фон
- [ ] Пустое состояние (если transactions пустой):
  ```python
  html.Div([
      html.I(className="bi bi-inbox", style={"fontSize": "48px", "color": "#95a5a6"}),
      html.P(empty_message, className="text-muted"),
      dbc.Button("Добавить", color="primary", size="sm", id="add-transaction-from-empty")
  ], className="empty-state")
  ```

**Файлы**: `app/components/dashboard.py`

---

### Задача 4: Layout 2 колонки операций
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1 (Нижняя часть Dashboard)`

- [ ] Обновить основной layout Dashboard в `app/components/dashboard.py`:
  ```python
  dbc.Row([
      dbc.Col([
          _build_transactions_table(
              recent_transactions,
              title="Недавние операции",
              empty_message="Нет операций в этом месяце",
              link_text=f"Все операции: с 1 {month_name} по {today.day} {month_name}",
              link_href=f"/transactions?start={start_date}&end={today}"
          )
      ], width=6),
      dbc.Col([
          _build_transactions_table(
              upcoming_transactions,
              title="Предстоящие операции",
              empty_message="Нет запланированных операций",
              link_text=f"Все операции: с {today.day} {month_name} по {end_of_month.day} {month_name}",
              link_href=f"/transactions?start={today}&end={end_date}"
          )
      ], width=6),
  ])
  ```
- [ ] Responsive: на 768px → single-column (col-12), на 576px → tabs вместо 2 колонок (опционально, если не усложняет)

**Файлы**: `app/components/dashboard.py`

---

### Задача 5: Ссылки "Все операции" с фильтром дат
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 4 (Ссылка "Показать все")**

**Действия**:
- [ ] Ссылки в CardFooter таблиц:
  - href: `/transactions?start=YYYY-MM-DD&end=YYYY-MM-DD`
  - Текст явный: "Все операции: с 1 по сегодня" или "Все операции: сегодня → конец месяца"
- [ ] Обновить `/transactions` страницу (`app/components/transactions.py`):
  - [ ] Обработать query params `?start=` и `?end=` при загрузке
  - [ ] Автоматически применить фильтр дат (предзаполнить date pickers)
  - [ ] Callback `apply_date_filter_from_url()`:
    - Input: `dcc.Location` pathname + search
    - Outputs: date-filter-start, date-filter-end Stores
  - [ ] Интеграция с существующими фильтрами (если есть)

**Файлы**: `app/components/dashboard.py`, `app/components/transactions.py`

---

### Задача 6: Правая колонна — Wishlist + Safety Cushion
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1 (Правая колонна)**

**Действия**:
- [ ] Перенести компоненты с /goals на Dashboard:
  - `build_wishlist_widget()` из `app/components/wishlist.py`
  - `_build_cushion_card()` из `app/components/goals.py` (или создать отдельный компонент)
- [ ] Обновить layout Dashboard:
  ```python
  dbc.Row([
      dbc.Col([
          # 4 KPI-карточки
          # График
          # 2 колонки операций
      ], width=9),  # Центральный контент
      dbc.Col([
          build_wishlist_widget(user_id),
          html.Br(),
          _build_cushion_card(user_id),
      ], width=3),  # Правая колонна
  ])
  ```
- [ ] Стили:
  - Одинаковая ширина карточек
  - Одинаковые бордеры/тени
  - Margin между карточками: 24px
- [ ] Callbacks:
  - Wishlist callbacks уже есть в `wishlist.py` — переиспользуем
  - Cushion callbacks уже есть в `goals.py` — переиспользуем
  - Убедиться что Stores/Modals доступны глобально (уже в `main.py`)

**Файлы**: `app/components/dashboard.py`, `app/components/wishlist.py`, `app/components/goals.py`

---

### Задача 7: Sidebar как card-контейнер
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1 (Левый сайдбар), решение из обсуждения #5**

**Действия**:
- [ ] Обновить `app/components/sidebar.py`:
  - Обернуть содержимое в `dbc.Card`:
    ```python
    dbc.Card([
        dbc.CardBody([
            # Существующий список пунктов меню
        ])
    ], className="sidebar-card")
    ```
  - Фон карточки: `#ffffff` (белый)
  - Бордер: `1px solid #bdc3c7` или тень `0 2px 8px rgba(0,0,0,0.08)`
  - Радиус: 8-10px
  - Padding: 20px
- [ ] Активный пункт меню:
  - Логика: определить текущий pathname (`dcc.Location`)
  - Если pathname = "/dashboard" → пункт "Личные финансы" активен
  - Активный стиль:
    - Зелёный бордер слева 4px (`border-left: 4px solid #2ecc71`)
    - Или зелёная иконка
    - Вес текста: 600 (semibold)
- [ ] Callback `highlight_active_menu_item()`:
  - Input: `Input("url", "pathname")`
  - Outputs: стили пунктов меню (active/inactive)
  - Логика: match pathname → highlight соответствующий пункт

**Файлы**: `app/components/sidebar.py`, `app/assets/sidebar.css`

---

### Задача 8: Модал "Сверка" доступен с Dashboard
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 5 (Модал корректировки баланса)**

**Действия**:
- [ ] Кнопка "Сверка" на Total Balance KPI (уже добавлена в батче 1):
  - id: `"open-reconciliation-from-dashboard"`
- [ ] Callback `open_reconciliation_modal_from_dashboard()`:
  - Input: `Input("open-reconciliation-from-dashboard", "n_clicks")`
  - Output: `Output("reconciliation-modal", "is_open", allow_duplicate=True)`
  - Логика: открыть модал сверки (тот же модал что на Calendar)
  - ADR-003 guard clause: проверить `n_clicks is None`
- [ ] Модал сверки:
  - Уже реализован в `app/components/calendar.py` (протокол 0010)
  - Переиспользуем: убедиться что модал доступен глобально (в `main.py`)
  - Структура модала:
    - Заголовок: "Сверка баланса"
    - Текущий остаток: read-only, серый (из DashboardService)
    - Поле ввода: "Фактический баланс" (обязательное, число)
    - Preview: разница = фактический − текущий (создаётся ADJUSTMENT)
    - Кнопки: "Подтвердить" (зелёный), "Отмена" (серый)
  - После подтверждения: Dashboard обновляется (Refresh Trigger)

**Файлы**: `app/components/dashboard.py`, `app/components/calendar.py` (переиспользуем модал)

---

### Задача 9: Пустые состояния для таблиц
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 6 (Пустое состояние)**

**Действия**:
- [ ] Компонент empty state (уже создан в задаче 3):
  ```python
  html.Div([
      html.I(className="bi bi-inbox", style={"fontSize": "48px", "color": "#95a5a6"}),
      html.P(message, className="text-muted"),
      dbc.Button("Добавить", color="primary", size="sm", id=button_id)
  ], className="empty-state", style={"textAlign": "center", "padding": "40px"})
  ```
- [ ] Callback `open_create_from_empty_state()`:
  - Inputs:
    - `Input("add-transaction-from-empty-recent", "n_clicks")`
    - `Input("add-transaction-from-empty-upcoming", "n_clicks")`
  - Output: `Output("create-transaction-modal", "is_open", allow_duplicate=True)`
  - Логика: открыть модал создания операции
  - ADR-003 guard clauses
- [ ] CSS стили `.empty-state`:
  ```css
  .empty-state {
      text-align: center;
      padding: 40px;
  }
  .empty-state i {
      font-size: 48px;
      color: #95a5a6;
      margin-bottom: 16px;
  }
  .empty-state p {
      color: #7f8c8d;
      margin-bottom: 16px;
  }
  ```

**Файлы**: `app/components/dashboard.py`, `app/assets/style.css`

---

### Задача 10: Unit тесты для `get_upcoming_transactions()`
**Действия**:
- [ ] Обновить `tests/test_dashboard_service.py`:
  - `test_get_upcoming_transactions_basic()` — несколько операций в диапазоне
  - `test_get_upcoming_transactions_empty()` — нет операций
  - `test_get_upcoming_transactions_limit()` — больше операций чем limit
  - `test_get_upcoming_transactions_sorting()` — сортировка по date ASC
  - `test_get_upcoming_transactions_edge_of_month()` — последний день месяца
  - `test_get_recent_transactions_basic()` — аналогично для недавних
  - `test_get_recent_transactions_sorting()` — сортировка по date DESC
- [ ] Запустить pytest — все тесты должны проходить (≥ 508 тестов, было 501 + 7 новых)

**Файлы**: `tests/test_dashboard_service.py`

---

### Задача 11: Финализация
- [ ] Black: переформатировать изменённые файлы
- [ ] Flake8: исправить E501, F401 (если есть)
- [ ] Pytest: запустить полный набор тестов (≥ 508)
- [ ] Проверить Dashboard в браузере:
  - 2 колонки операций (Недавние 50% / Предстоящие 50%)
  - Таблицы без "Completed" бейджей, категория во вторую строку
  - Ссылки "Все операции" ведут на /transactions с фильтром дат
  - Правая колонна: Wishlist + Safety Cushion (одинаковая ширина)
  - Sidebar как card-контейнер, активный пункт подсвечен зелёным
  - Кнопка "Сверка" на Total Balance открывает модал
  - Пустые состояния с иконкой + текст + CTA "Добавить"
- [ ] Обновить `feature_progress.md` — добавить батч 17
- [ ] Обновить `ROADMAP.md` — завершить Epic-05-UI

---

## 📊 Затронутые файлы с описанием изменений

### Новые файлы
- `app/assets/sidebar.css` — стили для sidebar card-контейнера и активного пункта (~50 строк)

### Модифицированные файлы

| Файл | Изменения | Строк (примерно) |
|------|-----------|------------------|
| `app/services/dashboard_service.py` | `get_upcoming_transactions()`, расширение `get_recent_transactions()` | +80 строк |
| `app/components/dashboard.py` | `_build_transactions_table()`, layout 2 колонки, правая колонна, callbacks | +250 строк |
| `app/components/transactions.py` | Обработка query params `?start=&end=`, автоприменение фильтра | +50 строк |
| `app/components/sidebar.py` | Обернуть в dbc.Card, callback highlight active | +40 строк |
| `app/components/calendar.py` | Интеграция модала сверки (переиспользование, минимальные изменения) | +10 строк |
| `app/assets/custom.css` | `.empty-state` стили | +20 строк |
| `app/assets/sidebar.css` | Новый файл — стили sidebar card | +50 строк |
| `tests/test_dashboard_service.py` | +7 unit тестов для get_upcoming/recent | +100 строк |

**Всего**: 8 файлов, ~600 строк изменено/добавлено

---

## ✅ Acceptance Criteria

### Visual
- [ ] 2 колонки операций 50/50: "Недавние" (1..сегодня) и "Предстоящие" (сегодня..конец)
- [ ] Формат таблиц:
  - Дата человеческий формат (`5 февраля`)
  - Описание + иконка recurring (⟳)
  - Категория во вторую строку (серый, 13px) или "Без категории"
  - Сумма RIGHT, формат ₽, цвет доход/расход
  - Без "Completed" бейджей
- [ ] Правая колонна: Wishlist + Safety Cushion (одинаковая ширина, бордеры/тени)
- [ ] Sidebar как card-контейнер (белый фон, бордер/тень)
- [ ] Активный пункт меню подсвечен зелёным (бордер слева 4px или иконка)
- [ ] Пустые состояния: иконка inbox + текст + CTA "Добавить"

### UX
- [ ] Ссылки "Все операции" ведут на /transactions с явным диапазоном дат
- [ ] Клик на "Добавить" в empty state → модал создания операции
- [ ] Кнопка "Сверка" на Total Balance → модал сверки баланса
- [ ] После сверки Dashboard обновляется сразу (Refresh Trigger)
- [ ] После создания операции таблицы обновляются автоматически

### Functional
- [ ] `get_upcoming_transactions()` возвращает операции сегодня..конец месяца, сортировка ASC, limit 5
- [ ] `get_recent_transactions()` возвращает операции 1..сегодня, сортировка DESC, limit 5
- [ ] Query params `?start=&end=` на /transactions автоматически применяют фильтр дат
- [ ] Модал сверки переиспользуется с Calendar (ReconciliationService)

### Technical
- [ ] Все тесты проходят (pytest ≥ 508)
- [ ] Black + Flake8 OK (0 ошибок)
- [ ] Производительность Dashboard не ухудшилась (< 2 сек загрузка)
- [ ] Нет регрессий на других страницах (Calendar, Goals, Transactions)

---

## 🔗 Зависимости и риски

### Зависимости
- **Блокируется**: Батч 1 (формат ₽), Батч 2 (Refresh Trigger, график)
- **Блокирует**: Нет (финальный батч Epic-05)

### Риски

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| Конфликт Wishlist/Cushion компонентов при переносе | Средняя | Среднее | Проверить что Stores/Modals доступны глобально в main.py |
| Query params на /transactions не работают | Низкая | Среднее | Использовать `dcc.Location` search parsing, тесты для query params |
| Sidebar активный пункт не подсвечивается | Низкая | Низкое | Callback highlight с match pathname, fallback на CSS class |
| Responsive 2 колонки на mobile | Средняя | Низкое | Базовые breakpoints: 768px → single-column, не критично для MVP |

---

## 📝 Примечания

### Формат даты "5 февраля"
- **Реализация**: Python `datetime.strftime("%d %B")` → "05 февраля" (лидирующий 0)
- **Альтернатива**: `datetime.strftime("%-d %B")` (Unix) или `datetime.strftime("%#d %B")` (Windows) → "5 февраля"
- **Локализация**: `locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')` перед форматированием

### Переиспользование модала сверки
- **Модал**: Уже реализован в `app/components/calendar.py` (протокол 0010)
- **Интеграция**:
  1. Модал доступен глобально в `main.py` (добавлен в layout)
  2. Callback `open_reconciliation_from_dashboard()` триггерит тот же модал
  3. ReconciliationService.create_adjustment() создаёт ADJUSTMENT операцию
  4. После подтверждения → Refresh Trigger → Dashboard обновляется

### Wishlist + Cushion на Dashboard
- **Компоненты уже есть**:
  - `build_wishlist_widget()` — `app/components/wishlist.py`
  - `_build_cushion_card()` — `app/components/goals.py`
- **Callbacks**: Уже реализованы, Stores/Modals в `main.py`
- **Изменения**: Только layout (перенести на Dashboard), стили одинаковые

### Sidebar активный пункт
- **Логика**: Match `dcc.Location` pathname с пунктами меню
  - `/dashboard` → "Личные финансы"
  - `/calendar` → "Кассовый календарь"
  - `/goals` → "Цели"
  - `/transactions` → "Операции"
- **Стиль**:
  - Активный: `border-left: 4px solid #2ecc71`, `font-weight: 600`
  - Неактивный: `border-left: 4px solid transparent`, `font-weight: 400`

### Responsive (опционально)
- **Desktop-first**: 1440px+ полный layout
- **768px**: Правая колонна под графиком, 2 колонки операций → 60/40 или single-column
- **576px**: Sidebar → hamburger menu, KPI horizontal scroll, 2 колонки → tabs
- **Приоритет**: Низкий для MVP (desktop-first достаточно)

---

**Статус**: ✅ Scope батча 3 финализирован, готов к протоколу 0023
