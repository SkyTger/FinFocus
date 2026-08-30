---
name: ui-components
description: Dash UI компоненты FinFocus — дашборд-щиток (шапка+график полос), Nav Rail, Transactions, Calendar, модалы
type: reference
originSessionId: -
---

# modules/ui-components.md

## Суть
Dash компоненты для UI: Dashboard-щиток, Nav Rail, Transactions с Bootstrap styling

## Ключевые файлы
- `app/components/dashboard.py` - главная страница: шапка «Свободно сегодня» + график полос (протокол 0028)
- `app/components/nav_rail.py` — навигация (полоска-меню 60px)
- `app/components/transactions.py` - управление операциями (CRUD),
  маркировка и защита служебных операций (протокол 0032)

См. секцию «Dashboard Component» ниже (актуальная версия, протокол 0028)
— первая версия этого раздела (статические metric-карточки без БД)
описывала состояние Батча 0, давно неактуальна.

## Nav Rail Component (Протокол 0031 — полоска-меню 60px)

**Файл**: `app/components/nav_rail.py`, стили — `app/assets/nav_rail.css`

> **История**: широкий сайдбар (228px) заменён узкой полоской иконок
> (60px) куском 3 Epic-11. До этого кусок 2 (протокол 0030) уже снял
> навигацию с дашборда и удалил оба её колбэка — `highlight_active_sidebar`
> (подсветка) и `update_sidebar_profile` (имя/аватар из БД): их Output'ы
> стали бы условно присутствующими, а запись children в узлы, которые
> слот-колбэк одновременно создаёт/удаляет, — гонка (порядок применения
> Output'ов Dash не гарантирует). Полоска унаследовала это устройство.
>
> Прежний `app/components/sidebar.py` сохранён как **файл-надгробие**
> с одной константой `ADDITIONAL_NAV_ITEMS` (решение владельца Р2,
> 2026-08-27); `sidebar.css` и `test_sidebar.py` удалены.

**Состав**: знак-домик наверху (ведёт на `/dashboard`), разделитель,
четыре раздела иконками (Календарь, Операции, Аналитика, Цели),
распорка, аватар внизу (открывает профиль). Подписи — язычком при
наведении. Активный раздел подсвечен пилюлей.

**Чего в полоске нет осознанно**:
- «Настройки» — маршрута `/settings` не существует, пункт вёл на 404
  (P1 UX-аудита 2026-08-20, FR-4). Ждёт маршрута в надгробии
- версия — переехала в окно профиля, берётся из `app/version.py`
  (P3 UX-аудита: в сайдбаре была зашита «v1.0.0» при релизе
  v0.9.0-beta.1)
- имя пользователя — в 60px не помещается, компенсируется окном профиля

**Устройство**:
- `create_nav_rail(pathname, profile)` — ЧИСТАЯ функция: ни БД, ни
  колбэков, ни литералов профиля. Подсветка и аватар вычисляются на
  построении из аргументов. Тотальна: любой pathname допустим
- Рендерится колбэком `render_nav_rail_slot(pathname, profile_updated)`
  в `app/main.py`: два Input'а на всегда присутствующие `url` и
  `profile-updated`; на `/dashboard` возвращает `[]` ДО открытия
  сессии; fail-open чтения профиля (заглушка + лог — находимость
  разделов важнее аватара)
- Колонку скрывает ОДНО CSS-правило `.nav-rail-column:empty
  { display: none }` — второй механизм не вводить
- Клик по аватару → clientside `timestamp_trigger` (main.py) → Store
  `open-profile-trigger` — единственный вход открытия модала профиля
  (второй вход — шестерёнка щитка — пишет в тот же Store)

**Разворот при входе с дашборда** (`@keyframes nav-rail-unfold`):
анимация играет только на МОНТИРОВАНИИ узла. При переходах
раздел→раздел React патчит существующий узел вместо пересоздания —
ключ обёртки берётся из `id="nav-rail"`, позиция стабильна (слот
отдаёт ровно один компонент, не список). На дашборде слот пуст, узел
уничтожается, при возврате монтируется заново — разворот играет снова.
Подтверждено живой пробой (шаг 1 протокола) и живой приёмкой (шаг 8).
Детали и грабли — `patterns/callbacks.md`, «Анимация на монтировании
условно присутствующего элемента».

Анимируется `.nav-rail-inner`, а не кожух: в эскизе схлопывалась сама
плашка, но это требует обрезки по её краю и срезало бы язычки
(решение владельца Р5, 2026-08-28). У кожуха намеренно нет
`overflow: hidden` — язычки выходят за правый край.

**Доступность**: имена ссылок даются через `title`, а не `aria-label` —
`dcc.Link` в dash 2.17.1 имеет закрытый список пропсов и на любой
`aria-*` бросает TypeError при построении. Замена на `html.A` отвергнута:
он делает полную перезагрузку и ломает переиспользование узла. Цена
компромисса: активный раздел не помечен `aria-current` для скринридера.
У аватара (`html.Div`) полноценные `aria-label` и `role="button"`.

**Регрессионный якорь**: `tests/test_nav_rail.py` (60 — на ревью
протокола 0031 параметризованы по всем разделам, было 43) — контракт
входов слот-колбэка, «в модуле nav_rail нет ни одного @callback»,
чистота построения, fail-open, предпосылки реконсиляции, доступность.
Визуальный слой и сам разворот тестами НЕ покрыты — только живьём.

## Transactions Component (КРИТИЧНО, Протокол 0023 — расширен, Протокол 0032 — служебные операции)

**Layout**:
- Header с кнопками "Добавить операцию" и "Экспорт CSV"
- Date Range Filter (dcc.DatePickerRange) — фильтр по диапазону дат
- Transactions table с:
  - Multi-select checkboxes (select-all в header)
  - Quick chips для категоризации некатегоризированных операций
  - Edit/Delete кнопки для каждой операции
- Bulk Actions Panel (sticky bottom):
  - Счетчик выбранных операций с склонением
  - Dropdown категорий для массового назначения
  - Кнопка "Применить категорию"
- Модалы:
  - Create modal с формой создания
  - Edit modal с формой редактирования
- dcc.Store:
  - selected-transactions - список ID выбранных операций
  - frequent-categories - кеш частых категорий
- dcc.Download для CSV экспорта

**Callbacks** (Pattern-Matching):
- `toggle_create_modal()` - открытие/закрытие модала создания
- `create_transaction()` - создание операции через TransactionService
- `open_edit_modal()` - открытие модала редактирования (pattern-matching)
- `update_transaction()` - обновление операции
- `delete_transaction()` - удаление операции (pattern-matching)
- `refresh_transactions_table()` - обновление таблицы после изменений

**Категоризация Callbacks** (Протокол 0011):
- `load_frequent_categories()` - кеширование частых категорий через CategoryService.get_frequent_for_type()
- `chip_assign_category()` - быстрое назначение через chip (Pattern-Matching с guard clauses)
- `chip_dropdown_assign_category()` - назначение через overflow dropdown

**Bulk Actions Callbacks** (Протокол 0011):
- `update_selection_state()` - обработка Select All и individual checkboxes
- `clear_selection_on_filter_change()` - сброс selection при смене фильтра (WYSIWYG)
- `toggle_bulk_panel()` - показ/скрытие panel с prevent_initial_call=True
- `bulk_assign_category()` - массовое назначение категории (max 100, ValidationError handling)

**Export Callback** (Протокол 0011):
- `export_transactions()` - CSV экспорт с UTF-8 BOM, учет filter-no-category

**URL Query Params Callback** (Протокол 0023 — NEW):
- `apply_url_date_filter()` - парсинг ?start=&end= query params в date filter
  - Input: url.search
  - Output: filter-date-range.dates (start, end tuple)
  - Logic: parse_qs() + date.fromisoformat() с try/except для невалидных дат
  - Применение: прямые ссылки с предзаполненным фильтром

**Pattern-Matching Callbacks** (КРИТИЧНО):
```python
# Edit buttons
Input({"type": "edit-btn", "index": ALL}, "n_clicks")

# КРИТИЧНО: проверка автовызова
if ctx.triggered[0].get('value') is None:
    raise PreventUpdate

# Используем triggered_id напрямую
transaction_id = ctx.triggered_id["index"]
```

**Quick Chips UI** (Протокол 0011):
```python
# Pattern-Matching ID для chip кнопок
{"type": "category-chip", "tx_id": transaction_id, "cat_id": category_id}

# Helper функция
def _build_chips_cell(tx, frequent_categories, all_categories):
    # Guard: TRANSFER/ADJUSTMENT → "—"
    if tx.type in [TransactionType.TRANSFER, TransactionType.ADJUSTMENT]:
        return "—"

    # Chips из frequent_categories[:5]
    chips = [dbc.Badge(cat.name, ...) for cat in frequent_categories[:5]]

    # Overflow dropdown с полным списком
    overflow = dcc.Dropdown(options=all_categories, ...)
```

**Ключевые особенности**:
- Chips показываются ТОЛЬКО для транзакций без категории
- TRANSFER и ADJUSTMENT типы не могут иметь категорию (guard clause)
- Chips загружаются из CategoryService.get_frequent_for_type() (кеш в Store)
- Max 5 chips + overflow dropdown "..." с полным списком
- 3-уровневые guard clauses в callbacks (ADR-003)

**Bulk Actions Panel** (Протокол 0011):
```python
# Helper для склонения
def _pluralize_operations(count: int) -> str:
    """Склонение слова 'операция' по падежам."""
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} операция"
    elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
        return f"{count} операции"
    else:
        return f"{count} операций"

# Bulk panel visibility
def toggle_bulk_panel(selection):
    if not selection or len(selection) == 0:
        return {"display": "none"}, ""

    counter = _pluralize_operations(len(selection))
    return {"display": "block"}, f"Выбрано {counter}"
```

**Ключевые особенности**:
- Multi-select с checkboxes в таблице (select-all в header)
- Sticky bottom panel появляется только при выборе
- Max 100 транзакций (лимит в TransactionService.bulk_update_category)
- Сброс selection при смене фильтров (WYSIWYG behavior)
- ValidationError handling с alert notification

**CSV Export** (Протокол 0011):
```python
# Filename pattern
filename = f"finfocus_transactions_{datetime.now().strftime('%Y-%m-%d')}.csv"

# UTF-8 BOM для Excel совместимости
content = TransactionService.export_to_csv(session, user_id, include_uncategorized)
```

**Ключевые особенности**:
- Учитывает filter-no-category
- UTF-8 BOM для корректного отображения кириллицы в Excel
- Timestamp в имени файла

## Служебные операции — маркировка и защита (Протокол 0032)

Список операций выбирает ВСЕ шесть типов транзакций
(`get_all_by_user` без фильтра типа), но до протокола 0032 рендер
различал только INCOME/EXPENSE — служебные `SAVINGS_RESERVE`,
`SAVINGS_CONTRIBUTION` показывались как обычный «Расход» с активными
кнопками редактирования/удаления. Прямое удаление минует каскад
`GoalService` (Contribution → Transaction → Goal) и рассинхронизирует
накопленную сумму цели. Календарь эту проблему уже решал (readonly-
строка, `calendar.py:437-500`) — список приведён к тому же принципу.

**Единственный источник правды «служебности»** — предикат в
`transactions.py`:
```python
SYSTEM_TRANSACTION_TYPES: frozenset[TransactionType] = frozenset(
    {TransactionType.SAVINGS_RESERVE, TransactionType.SAVINGS_CONTRIBUTION}
)

def _is_system_transaction(tx) -> bool:
    return tx.transaction_type in SYSTEM_TRANSACTION_TYPES
```
Импортируется в `transaction_modals.py` для delete-guard'а — второго
независимого предиката нет.

**Двухуровневая защита** (не подменяют друг друга — оба уровня нужны):
1. **UI не рендерит контролы** для служебных строк: нет чекбокса, нет
   кнопок edit/delete, нет chips категоризации. Вместо кнопок —
   значок замка́ с `title`-пояснением («управляется через Цели» /
   «через настройку резервирования»), описание получает суффикс
   «(авто)», строка целиком — класс `.tx-system-row` (opacity 0.75,
   `transactions.css`, по образцу `.readonly` календаря).
2. **Серверные guard'ы в callbacks** — страховка от устаревшего DOM
   или второй открытой вкладки: `open_edit_modal` и
   `handle_delete_click` (в `transaction_modals.py`) проверяют
   `_is_system_transaction(tx)` СРАЗУ после загрузки транзакции из БД
   и делают `PreventUpdate`, если тип служебный.

**Критичный порядок в `open_edit_modal`**: guard «служебная ли
операция» стоит ДО ветвления на recurring/обычная операция — шаблон
резервирования бюджета реально бывает повторяющейся операцией
(`is_recurring=True`), и если бы guard стоял после ветвления на
scope-modal, служебная recurring-операция открыла бы диалог выбора
scope раньше проверки. Порядок проверок здесь не второстепенная
деталь реализации.

**Bulk-операции** — двойная страховка:
- `TransactionService.bulk_update_category` фильтрует кандидатов по
  `CATEGORIZABLE_TRANSACTION_TYPES = {INCOME, EXPENSE}` ПОСЛЕ проверки
  ownership (существующий тест ownership не сломан) — некатегоризируемые
  типы молча исключаются, счётчик обновлённых — честный (не включает
  исключённые), пустой остаток после фильтрации → `0`, не ошибка.
- `_drop_system_ids()` в `transactions.py` — страховка на уровне
  формирования bulk-выборки: один SQL-запрос по факту id из БД (не по
  тому, что нарисовано в DOM), фильтрует служебные, порядок id
  сохраняется. Вызывается из `update_selection_state`.
- Chips-callbacks (`chip_assign_category`, `chip_dropdown_assign_category`)
  загружают транзакцию до записи и делают `PreventUpdate`, если
  `_is_system_transaction(target_tx)` — тот же принцип «проверка после
  чтения из БД, не по data-атрибутам DOM».

**Единый источник подписей типов** — `TYPE_LABELS` в
`transaction_service.py` (модульная константа, не метод): используется
и бейджами списка операций, и CSV-экспортом (`export_to_csv`) — раньше
экспорт держал свой отдельный `type_labels` dict, теперь один словарь
на двоих. Savings-типы получили общую подпись «Накопления» (раньше
CSV показывал сырой `str(enum)`).

**Знак и цвет суммы по типу** (не только INCOME/EXPENSE как раньше):
INCOME — зелёный `+`; EXPENSE — красный `-`; ADJUSTMENT — по значению
суммы (как в сверке календаря, может быть и `+`, и `-`); savings-типы —
приглушённый `-` (уменьшают баланс); TRANSFER — приглушённый, без
знака (баланс не меняет).

**Решение Р1 (ADJUSTMENT)**: dropdown типов edit-модала умеет только
INCOME/EXPENSE — у ADJUSTMENT кнопка редактирования скрыта, delete
оставлен (откат корректировки сверки — законное действие
пользователя). TRANSFER той же болезнью страдает (тот же dropdown),
но по решению протокола не тронут — полноценная пользовательская
операция, ограничение модала вне scope.

**Принятый техдолг** (зафиксирован на ревью, не блокер): существуют
ДВА независимых списка «что нельзя категоризировать/что служебное» —
`SYSTEM_TRANSACTION_TYPES` в `transactions.py` (UI-слой, 2 типа) и
`CATEGORIZABLE_TRANSACTION_TYPES` в `transaction_service.py`
(сервисный слой, инвертированный список — что МОЖНО, 2 типа из 6).
При добавлении седьмого `TransactionType` оба списка нужно обновлять
руками — есть риск молчаливого расхождения, автоматической сверки
между ними нет.

**Тесты**: `tests/test_transactions_system_ops.py` (51 тест) — рендер
(бейджи, скрытие контролов, знак суммы, «(авто)»), guard'ы callbacks
(edit/delete/chips/selection) без БД, где возможно (Transaction в
памяти, относительные даты); `tests/test_transaction_service.py`
(+2: смешанный список bulk — обновлён только EXPENSE; список из одних
служебных — счётчик `0` без исключения). Mutation smoke: предикат
`_is_system_transaction` → `return False` ловится 14 тестами;
delete-guard → `if False` ловится 2 тестами.

**Form Validation**:
- amount > 0 (frontend: type="number", min=0)
- transaction_type required (frontend: dropdown)
- transaction_date required (frontend: DatePickerSingle)
- Backend validation через TransactionService

## Важное

**Dash Bootstrap Components**:
- `dbc.Modal` - модальные окна
- `dbc.Table` - таблицы с striped/hover
- `dbc.Card` - карточки для метрик
- `dbc.Button` - кнопки с цветами (primary/danger/success)

**Plotly Charts**:
```python
fig = go.Figure(data=[
    go.Bar(x=dates, y=amounts, name="Income", marker_color="green")
])
fig.update_layout(template="plotly_white", showlegend=True)
```

**Component IDs** (kebab-case):
- `transaction-table` - таблица операций
- `create-modal` - модал создания
- `edit-modal` - модал редактирования
- `export-download` - dcc.Download для CSV экспорта
- `selected-transactions` - dcc.Store для списка ID выбранных операций
- `frequent-categories` - dcc.Store для кеша частых категорий
- `select-all-checkbox` - checkbox в header таблицы
- `bulk-actions-panel` - sticky panel для bulk операций
- `bulk-category-dropdown` - dropdown категорий для bulk назначения
- `{"type": "edit-btn", "index": transaction_id}` - pattern-matching ID
- `{"type": "tx-checkbox", "index": transaction_id}` - checkbox для multi-select
- `{"type": "category-chip", "tx_id": tx_id, "cat_id": cat_id}` - chip кнопка категории
- `{"type": "chip-dropdown", "index": transaction_id}` - overflow dropdown категорий

## Transaction Modals Component (Глобальные модалы CRUD)

**Файл**: `app/components/transaction_modals.py` (~800 строк)

**Layout**:
- create-modal — форма создания транзакции с recurring секцией
- edit-modal — форма редактирования транзакции
- recurring-scope-modal — выбор scope при редактировании recurring операций

**dcc.Stores**:
- modal-source — источник открытия модала (calendar/transactions/dashboard)
- global-transaction-trigger — эмиттер обновления страниц после CRUD
- edit-transaction-id — ID редактируемой транзакции
- recurring-edit-context — контекст для recurring operations

**Submit Callbacks** (3):
1. **create_transaction** — создание новой операции
   - TransactionService.create_transaction()
   - RecurringService.create_recurring() для recurring операций
   - emit global-transaction-trigger для refresh страниц

2. **update_transaction** — обновление существующей операции
   - TransactionService.update_transaction()
   - Обработка recurring edit через RecurringService

3. **skip_recurring_instance** — пропуск экземпляра recurring операции
   - RecurringService.skip_instance()
   - emit global-transaction-trigger

**Recurring Edit Scope Callback** (КРИТИЧНО):
- **process_recurring_edit_scope()** — обработка выбора scope редактирования (2026/02/02)
  - Inputs: scope-ok-button.n_clicks, scope-radio.value, recurring-edit-context.data
  - Outputs: edit-modal, transaction fields, category dropdown
  - Logic:
    - scope="all" → редактирование шаблона (template_id)
    - scope="instance" + transaction_id → редактирование существующего exception
    - scope="instance" + VIRTUAL op (transaction_id=None) → **AUTO-CREATE EXCEPTION** (commit cae3575)
  - **Критичный bugfix (cae3575)**:
    - RecurringService.create_exception() для виртуальных операций перед редактированием
    - Предотвращает "fully NULL primary key identity" ошибку
    - Error handling с transaction_error_alert
  - **Context обновление**: updated_context для кнопки "Пропустить"

**Category Dropdown Callbacks**:
- load_create_category_options / update_edit_category_options — dynamic dropdown с ICON_TO_EMOJI
- Guard clause: allow_duplicate=True для update_edit

**Close Callbacks**:
- close_create_modal / close_edit_modal — глобальные close для Cancel buttons

**Ключевые паттерны**:
- **Refresh Trigger Pattern** — global-transaction-trigger emit/listen
- **modal-source Store** — источник открытия для Selective Refresh
- **Auto-create exception** — виртуальные recurring ops → exception перед edit (cae3575)
- **Error handling** — try/catch в callbacks с transaction-error-alert UI

**Важно**:
- Модалы глобальные — доступны с любой страницы
- RecurringService.create_exception() — idempotent (возвращает существующий exception)
- Flush/commit contract: сервис flush(), callback commit()

## Критичные проблемы и решения

**ADR-003**: Pattern-Matching Callbacks auto-trigger issue
- **Проблема**: Callbacks срабатывают автоматически при обновлении DOM
- **Решение**: Проверка `ctx.triggered[0].get('value') is None` для фильтрации автовызовов
- **Статус**: Исправлено в Батче 4 (2025-12-22)

**BUG-001**: Auto-deletion после создания операции
- **Проблема**: Delete callback срабатывал автоматически после create
- **Решение**: Проверка `ctx.triggered[0].get('value') is None`
- **Статус**: Исправлено

**BUG-002**: Edit virtual recurring operations error (2026/02/02)
- **Проблема**: Клик по виртуальной recurring операции в tooltip → выбор "только этот экземпляр" → SQLAlchemy ошибка "fully NULL primary key identity"
- **Root Cause**: callback пытался загрузить transaction_id=None для виртуальных операций
- **Решение**: process_recurring_edit_scope() создаёт exception через RecurringService.create_exception() перед редактированием
- **Статус**: Исправлено (commit cae3575)

**Упрощение логики**:
- Использование `ctx.triggered_id["index"]` напрямую вместо поиска в списках
- Удаление избыточной проверки `n_clicks is None` (не нужна с `prevent_initial_call=True`)

## Calendar Component (Фаза 3 + Протокол 0015, 0023 — ЗАВЕРШЕНА)

**Файлы**:
- `app/components/calendar.py` — UI + callbacks (~820 строк после протокола 0023)
- `app/assets/calendar.css` — стили (~390 строк после протокола 0015)

**Layout**:
- Header с навигацией (prev/today/next кнопки)
- Stats cards (Доходы/Расходы/Баланс за месяц)
- Calendar grid — сетка дней с балансами
- Hover tooltips на каждой ячейке дня (Протокол 0015)
- Интеграция с create-modal из transactions.py
- **NEW (Протокол 0023)**: Reconciliation modal перенесён в main.py (глобализация)

**Основные функции**:
- `create_calendar_layout()` — главный layout страницы
- `build_calendar_header()` — навигация по месяцам
- `build_stats_cards()` — карточки статистики (dbc.Row)
- `build_calendar_grid()` — сетка дней
- `build_day_cell()` — ячейка одного дня (sibling structure для tooltip)

**Tooltip Builder Functions** (Протокол 0015):
- `_build_day_tooltip(day_date, balance, transactions)` — полный tooltip с expand/collapse
  - Glassmorphism стиль с backdrop-filter
  - CSS checkbox hack для expand (max 5 visible, кнопка "Показать ещё")
  - Pattern-Matching IDs для клика по операциям
  - ARIA атрибуты: role="tooltip", aria-label
- `_build_tooltip_balance(balance)` — header с балансом (positive/negative классы)
- `_build_tooltip_transaction_row(tx)` — строка операции с emoji, описанием, суммой
  - category_icon из TransactionInfo → ICON_TO_EMOJI mapping
  - Strikethrough для is_skipped=True
  - Цветовая индикация: зеленый (income), красный (expense)

**Callbacks**:
- `load_and_navigate_calendar()` — загрузка данных и навигация ±12 месяцев
- `open_create_modal_from_calendar()` — открытие модала при клике на день
- `refresh_calendar_after_transaction()` — обновление после CRUD операций **(Протокол 0023: удален calendar-refresh-trigger, использует global-transaction-trigger)**
- `open_edit_from_tooltip()` — Pattern-Matching callback для клика по операции в tooltip (Протокол 0015)
  - Inputs: {"type": "tooltip-txn", "date": ALL, "id": ALL, "is_virtual": ALL, "template_id": ALL}
  - Outputs: recurring-scope-modal is_open, recurring-edit-context data, edit-modal is_open, edit-transaction-id data
  - 4 ADR-003 guard clauses: triggered_id exists, type="tooltip-txn", n_clicks not None, n_clicks > 0
  - Logic: is_virtual=True → scope modal, else → edit modal
  - Placeholder -1 для template_id вместо None (Dash PM ID limitation)
- `apply_reconciliation()` — применение сверки баланса **(Протокол 0023: Output global-transaction-trigger вместо calendar-refresh-trigger)**
  - allow_duplicate=True для множественных Outputs на trigger
  - return data: {"timestamp": ..., "source": "calendar", "action": "reconciliation"}
- `toggle_reconciliation_modal()` — открытие/закрытие модала сверки (query param ?open_recon=1)

**Утилиты**:
- `serialize_balances()` / `deserialize_balances()` — Decimal ↔ JSON для dcc.Store
- `format_balance()` — форматирование суммы с разделителями
- `format_month_header()` — локализованный заголовок (MONTH_NAMES_RU)

**Pattern-Matching IDs**:
```python
# Ячейка дня
{"type": "calendar-day", "date": "2026-01-19"}

# Tooltip операция (Протокол 0015)
{"type": "tooltip-txn", "date": "2026-01-19", "id": 123, "is_virtual": False, "template_id": -1}
# ВАЖНО: template_id=-1 placeholder вместо None (Dash limitation)

# КРИТИЧНО: проверка автовызова (ADR-003)
if ctx.triggered[0].get('value') is None:
    raise PreventUpdate
```

**Стили** (calendar.css):
- `.calendar-grid` — flexbox контейнер
- `.calendar-day` — ячейка дня
- `.calendar-day-balance.positive` — зеленый баланс
- `.calendar-day-balance.negative` — красный баланс
- `.calendar-day-balance.warning` — желтый (< 5000₽)
- `.calendar-day.today` — подсветка сегодня
- `.calendar-day.weekend` — выходные дни

**Tooltip Styles** (Протокол 0015, ~200 строк):
- `.calendar-day-content` — wrapper для tooltip sibling structure
- `.day-tooltip` — glassmorphism стиль с backdrop-filter blur
  - Transitions: opacity 0.3s, visibility с delay 0.5s
  - Edge detection: `:nth-child(6n), :nth-child(7n)` → tooltip слева
  - Mobile: `display: none` на 768px (нет hover на мобильных)
- `.tooltip-balance.positive` / `.tooltip-balance.negative` — цветовая индикация баланса
- `.tooltip-txn-row` — строка операции (hover highlight)
- `.tooltip-txn-row.skipped` — strikethrough для пропущенных
- `.tooltip-expand-checkbox` — CSS checkbox hack для expand/collapse
- `.tooltip-hidden-container` — скрытые операции (display: none до expand)

**Константы**:
- `WARNING_BALANCE_THRESHOLD = Decimal("5000")` — порог предупреждения
- `MAX_MONTHS_OFFSET = 12` — ограничение навигации
- `MAX_VISIBLE_TRANSACTIONS = 5` — лимит видимых операций в tooltip (Протокол 0015)

**Критичные детали Tooltip** (Протокол 0015):
- **CSS-only approach** — zero server calls, instant response
- **Sibling structure** — clickable_content (n_clicks) + tooltip как siblings в wrapper (CSS классы на wrapper)
- **Checkbox hack** — dcc.Checklist для expand без JavaScript callbacks
- **Edge detection** — tooltip справа для колонок 1-5, слева для колонок 6-7
- **Mobile disabled** — tooltip скрыт на < 768px (нет hover)
- **Placeholder -1** — template_id=-1 вместо None для Dash Pattern-Matching (None не поддерживается)

## Dashboard Component — щиток (Протокол 0028 — Epic-11, кусок 1 из 3)

> **История**: до протокола 0028 дашборд состоял из ряда 4 KPI-карточек
> (Баланс/Доходы/Расходы/Накопления) + переключаемого графика
> доходы-расходы+баланс (Month/Year, dual Y-axis) — реализация протоколов
> 0021-0023. Протокол 0028 заменил этот layout целиком на «щиток»:
> шапка-вердикт «Свободно сегодня» + график полос
> Свободно/Платежи/Резерв. Приветствие и переключатель периода убраны,
> AI Assistant/Exchange остаются скрытыми. Раздел ниже описывает ТЕКУЩЕЕ
> состояние; секции про KPI-карточки и dual-axis график ниже больше не
> актуальны для дашборда (dual Y-axis остаётся общим Plotly-паттерном,
> см. `patterns/plotly-charts.md`).

**Файлы**:
- `app/components/dashboard.py` — UI + callbacks (922 строки)
- `app/assets/panel.css` — стили щитка (841 строка — секции 1-6 куска 1
  + секции 7-10 карточек-дверей куска 2)
- `app/assets/custom.css` — общие стили, почищен от `.kpi-*` и
  `.db-period-switcher` (346 строк)

> Размеры файлов меняются с каждым протоколом — приведены как ориентир
> на момент актуализации 2026-08-30, не как инвариант; при расхождении
> сверяться с `wc -l`, а не с этой цифрой.

**Layout**:
- **Шапка `dashboard-free-header`** — «Свободно сегодня: N ₽» + разбор
  «баланс − платежи − резерв», справа аватар-эмодзи с именем, кнопка
  «Сверка», шестерёнка (→ модал профиля). Приветствия и вердикта НЕТ
  (решения владельца, см. ниже). Не дверь-переход: без `dcc.Link`,
  `n_clicks`, `cursor:pointer`
- **`dashboard-layers-chart`** — график полос (Plotly) на 45 дней:
  Свободно/Платежи/Резерв в `barmode="stack"`, линия «сегодня», маркер
  минимума слоя «Свободно», вехи целей аннотациями, HTML-легенда
  с тултипами вместо легенды Plotly
- **`html.Div(id="dashboard-cards-row")`** — ряд из пяти карточек-дверей
  (протокол 0030, см. секцию «Panel Cards» ниже). **Заменяет** прежнюю
  раскладку 8/4: split-таблицы «Недавние»/«Предстоящие», wishlist-виджет
  и readonly-карточку подушки — все три удалены целиком, вместе с
  функциями `_build_transactions_split_table`, `_build_cushion_card_readonly`,
  `build_wishlist_widget`, `_build_widget_item` (их больше нет в коде)
- Переключателя Месяц/Год **больше нет** — `dcc.Store(id="dashboard-period")`
  остался в layout только как guard для клика по графику (писателя нет)
- AI Assistant и Exchange — по-прежнему скрыты (TODO Epic-08)

**Единственный источник данных**: `MoneyLayersService.get_money_layers()`
(см. `services.md`) — шапка и график строятся из ОДНОГО вызова за
рендер, расхождение цифр между ними физически невозможно.

**Решения владельца, зафиксированные в UI** (`.obsidian-docs/design/epic-11-panel-batch-1/spec.md`):
- Вердикта/светофора в шапке НЕТ — любой порог просадки произволен,
  проблемные дни видны на самом графике (единственное исключение:
  отрицательное «Свободно» красным — факт знака числа, не оценка)
- Приветствия НЕТ — главное место отдано цифре
- Признака перерасхода бюджета целей в тултипе НЕТ (см. ограничение
  формулы резерва в `services.md` → MoneyLayersService)

**Callbacks**:
- `load_dashboard_data()` — 3 Output'а (шапка, график, ряд карточек);
  Inputs: `url.pathname`, `profile-updated`. Приветствия-Output нет —
  имя/аватар обновляются вместе с шапкой через тот же Output.
  **Изменено протоколом 0030**: было 5 Output'ов (шапка, график,
  recent, upcoming, подушка) — три последних снялись вместе со
  split-таблицами/подушкой/wishlist-виджетом, их место заняла
  единая карточка-ряд
- `refresh_dashboard_after_crud()` — те же 3 Output'а, после CRUD
- `open_create_from_chart()` — клик по столбцу графика → create-modal;
  дата берётся из ISO-строки `point["x"]` (ось графика — `type="date"`),
  а не из года/месяца Store — окно щитка пересекает границы месяцев
- `toggle_balance_toast()` — без изменений логики, тот же баннер
  нулевого баланса

**Build Functions**:
- `_load_dashboard_components(period_state)` — единая точка загрузки:
  **протокол 0030** — один сбор через `DashboardPanelService.get_panel_data()`
  (профиль + `MoneyLayersData` + `PanelData` за одну сессию БД), дальше
  сборка шапки/графика/ряда карточек. Параметр `period_state` сохранён
  для совместимости сигнатуры вызова, на состав щитка не влияет
- `build_free_header(data, profile)` — шапка; `_build_header_who`,
  `_build_header_empty_state`, `_build_recon_button`,
  `_build_settings_cog` — хелперы шапки
- `build_layers_chart(data)` — график полос; `_axis_tickvals`
  (потолок подписей `MAX_X_TICKS`, не цель — см. `schema.md`),
  `_build_layer_legend`, `_build_payments_tooltip`,
  `_build_reserve_tooltip`, `_build_chart_empty_state`
- `build_cards_row(panel_data)` (`panel_cards.py`) — ряд пяти
  карточек-дверей, см. секцию «Panel Cards» ниже

**Багфикс протокола 0029** — `_axis_tickvals` пробивал собственный
потолок `MAX_X_TICKS`: при длине окна, кратной `MAX_X_TICKS` (например
44), равномерная сетка уже давала ровно 11 подписей, и `append` правого
края поверх неё делал 12 — вопреки докстрингу «НИКОГДА не превышает».
В проде дефект был латентным (окно всегда `WINDOW_DAYS`=45 → 10
подписей). Фикс: при упоре в потолок правый край ЗАМЕНЯЕТ последнюю
подпись сетки, а не добавляется сверх неё. Найдено и исправлено при
написании тестов визуального слоя (см. «Unit тесты» ниже).

**Удалено протоколом 0028** (мёртвый код): `_build_greeting_text`,
`build_overview_cards`, `_build_kpi_card`, `build_statistics_card`,
`build_cashflow_chart`, `_build_daily_cashflow_chart`,
`_build_yearly_cashflow_chart`, `create_ai_assistant_card`,
`create_exchange_card`, `build_recent_transactions_card`,
`update_period_state()` callback, `update_dashboard_greeting()`
callback, элемент `dashboard-greeting`, Store `dashboard-period-store`
(заменён на `dashboard-period` — не писателя).

**Удалено протоколом 0030** (мёртвый код и раскладка 8/4, вытеснены
рядом карточек-дверей): `_build_transactions_split_table`,
`_build_cushion_card_readonly` (вместе с её сессией БД),
`_build_empty_state`; в `wishlist.py` — `build_wishlist_widget`,
`_build_widget_item` (вместе с сессией виджета из layout);
в `custom.css` — `.db-main-row`, `.db-left-col`, `.db-right-col`,
`.dashboard-split-table`.

**Пустые состояния (FR-6)**:
- Чистая база → `dcc.Graph` в дереве ОТСУТСТВУЕТ вовсе (Plotly не
  вызывается — выродившиеся оси −1..1 физически невозможны)
- История есть, но окно пустое (`window_is_flat=True`) → график
  рисуется плоской стопкой, пустое состояние НЕ подменяет его
- `data["degraded"]` → нейтральная сноска в шапке «Часть данных
  недоступна, показано без бюджета целей» + тултип резерва честно
  не утверждает состав

**Второй вход в модал профиля — шестерёнка щитка**: см.
`patterns/callbacks.md` → «Store-триггер для динамически рендеренных
элементов (протокол 0028)» — прямой `Input` на элемент
`dashboard-settings-cog` ломал бы модал профиля на всех страницах,
кроме `/dashboard`.

**Unit тесты**: UI-слой закрыт протоколом 0029 — 47 тестов в новом
`tests/test_dashboard_panel_ui.py` (4 класса: `TestFreeHeader` 10,
`TestAxisTickvals` 5×параметризация, `TestLayersChart` 8,
`TestLegendAndTooltips` 7). БД не используется — фикстуры-словари
`MoneyLayersData` на относительных датах, локальный хелпер `iter_tree`
для обхода дерева Dash-компонентов. Формализуют три ручных критерия
приёмки протокола 0028 (AC-1 цифра шапки, AC-4 тултип «Платежи»,
AC-5 пустые состояния без числовых артефактов) и инварианты решений
владельца из секции выше (нет вердикта/приветствия, шапка не дверь,
`degraded` → сноска, `is_empty` → `dcc.Graph` отсутствует,
`window_is_flat` → график всё равно рисуется). Mutation-проверка:
3 намеренные порчи (вернуть приветствие; подменить график пустым
состоянием при `window_is_flat`; тултип резерва всегда утверждает
настройку) — каждая поймана адресным тестом. Колбэки по-прежнему
покрыты отдельно в `test_dashboard_callbacks.py`.

## Panel Cards — карточки-двери щитка (Протокол 0030 — Epic-11, кусок 2 из 3)

**Файлы**:
- `app/components/panel_cards.py` — чистые build-функции пяти карточек
- `app/assets/panel.css` — секции 7-10 (двери, wishlist-полоса, адаптив
  1180/680, prefers-reduced-motion)

**Состав**: `_door_shell` (каркас: цветная шина гнезда 3px, заголовок-
dcc.Link, тело) + `build_calendar_card` / `build_goals_card` /
`build_operations_card` / `build_analytics_card` / `build_wishlist_card`
+ `build_cards_row`. Данные приходят срезами `PanelData`
(DashboardPanelService), сами функции о БД не знают.

**Конституция щитка (FR-2)**: все пять карточек присутствуют ВСЕГДА —
при пустых данных и при сбое блока меняется только содержимое.
Единственный источник правды отрисовки — `<slot>["status"]`
(CardStatus): общего признака пустоты в PanelData нет.

**Ни одного серверного Input**: переходы делает dcc.Link; единственный
интерактивный не-ссылочный элемент — слой-подложка двери Wishlist
(`panel-wishlist-door`) → clientside timestamp_trigger → Store
`open-wishlist-trigger` → `open_wishlist_modal` (wishlist.py,
единственный Input + guard на пустой Store).

**Двухуровневая дверь = слой-подложка, а не вложенность** (найдено на
ревью 0030): пока кликабельный узел уровня 1 был КОНТЕЙНЕРОМ полосы,
а ссылки-хотелки — его детьми, клик по хотелке всплывал в родителя и
открывал модал ПОВЕРХ календаря (уровни смешивались). React-события
всплывают от вложенной ссылки к родителю; `dcc.Link` делает
`preventDefault`, но НЕ `stopPropagation`. Решение: уровень 1 —
пустой absolute-слой `.pnl-wish-hitbox` внутри полосы, ссылки —
его соседи, поднятые `z-index`. Правило общее: **кликабельный
контейнер со ссылками внутри — всегда баг всплытия**; разводить
уровни слоями, а не вложенностью.

**Карточка «Календарь»**: ДВА окошка (сегодня/завтра, «вчера» убрано
решением владельца 2026-08-26), каждое — dcc.Link на
`/calendar?focus_date=<ISO>`; маркер просадки только при status == OK
(оговорка #91: на пустом окне min_free = (0, today) — без оговорки
чистая база дала бы числовой артефакт); усиление
`pnl-flagline-strong` — факт знака `dip_free <= 0`, порога нет.

**Ограничение карточки «Операции»** (решение владельца 2026-08-25):
только материализованные операции — виртуальные инстансы регулярных
платежей не показываются (источник их не отдаёт, C-3); регулярные
видны в календаре и графике полос. Маркер 🔁 — у материализованных
recurring-инстансов.

**Объявленное расхождение карточки «Аналитика»**: цифра месяца
считается `AnalyticsService.get_expenses_by_category` (EXPENSE и
is_recurring=False) — с разделом совпадает по построению, но с
месячным слоем «Платежи» графика НЕ сопоставима (слой включает
виртуальные регулярные и savings_*). Объявлено подписью «расходы
{месяца} · без регулярных и взносов в цели», в докстринге
AnalyticsCardData и в RTM #87. Показателя «Доходы» в карточке нет.

**AC-4**: подушка — строка внутри карточки «Цели» (`margin-top:auto`,
вертикальный ритм), отдельной карточки в ряду нет.

**Тесты**: `tests/test_panel_cards_ui.py` (26, дерево без БД),
`tests/test_panel_service.py` (19, композитор), `tests/test_nav_rail.py`
(60, см. секцию Nav Rail выше), `tests/test_panel_query_params.py` (14).

## Onboarding Wizard Component (Протокол 0014 — ЗАВЕРШЕН)

**Файлы**:
- `app/components/onboarding_wizard.py` — Wizard UI + callbacks (~200 строк)
- `app/assets/onboarding.css` — стили (~80 строк)

**Layout**:
- Blocking modal (dbc.Modal):
  - backdrop="static" — нельзя закрыть кликом вне модала
  - keyboard=False — нельзя закрыть ESC
  - is_open управляется из check_onboarding_and_validate callback
- Header с зеленым градиентом
- Body:
  - Welcome text с объяснением важности starting_balance
  - InputGroup с полем ввода + ruble sign (₽)
  - Warning div для negative balance (display: none по умолчанию)
- Footer:
  - "Пропустить" button (secondary) — для опытных пользователей
  - "Продолжить" button (success, disabled по умолчанию) — активируется при valid input

**Callbacks** (2):
1. **check_onboarding_and_validate** (triggered on URL change + input change)
   - Inputs: url.pathname, starting-balance-input.value
   - Outputs: modal is_open, continue-button disabled, continue-button n_clicks, warning visibility
   - Logic:
     - Check first_launch через OnboardingService.get_status()
     - Show modal если first_launch=True
     - Validate input: empty → disabled, negative → warning + disabled, positive → enabled
     - DB failure strategy: fail-closed (hide wizard on error)

2. **handle_onboarding_action** (triggered on button clicks)
   - Inputs: continue-btn.n_clicks, skip-btn.n_clicks, starting-balance-input.value
   - Outputs: modal is_open, dashboard-refresh-trigger
   - Logic:
     - ADR-003 guard clauses для n_clicks (prevent auto-triggers)
     - Continue → OnboardingService.complete_with_balance()
     - Skip → OnboardingService.skip()
     - Emit dashboard-refresh-trigger для обновления UI
     - Close modal

**Dashboard Toast Integration** (Протокол 0014):
- Toast UI в dashboard.py:
  - _build_balance_toast() — warning toast с CTA кнопкой
  - Показывается если starting_balance=0 (в коде БЕЗ условия first_launch — onboarding_service.py:80; уточнено при ревью 0026)
  - Dismissable через close button (состояние в session Store)
  - CTA кнопка "Настроить" → redirect на /calendar?open_recon=1
- 2 callbacks:
  - toggle_balance_toast — показ/скрытие на основе OnboardingStatus
  - persist_toast_dismissal — сохранение dismissal state в Store

**Calendar Query Param Handler** (Протокол 0014):
- Extended toggle_reconciliation_modal в calendar.py:
  - Added Input("url", "search") и State("url", "pathname")
  - Logic: если ?open_recon=1 → auto-open reconciliation modal
  - Query cleanup strategy: full (return "" для url.search Output)
  - All return statements updated с 6th element для url.search Output

**State Management**:
- `dcc.Store(id="balance-toast-dismissed")` — session state для toast dismissal (в main.py)

**Ключевые паттерны**:
- **Fail-closed DB strategy**: wizard скрывается при ошибке БД, не блокирует приложение (critical для UX)
- **Query param full cleanup**: url.search = "" после обработки (не оставляем артефактов в URL)
- **Flush/commit contract**: OnboardingService.flush(), callback context manager commit()
- **ADR-003 guard clauses**: n_clicks проверки в handle_onboarding_action

**Стили** (onboarding.css):
- `.onboarding-modal .modal-header` — green gradient (linear-gradient #1a7431 → #228b3b)
- `.onboarding-modal .modal-body` — padding, line-height
- `.balance-toast` — warning colors (#856404 bg, #fff3cd text)
- Responsive: max-width 90% на mobile

**Критичные детали**:
- Modal НЕЛЬЗЯ закрыть без действия (backdrop=static, keyboard=False, no X button)
- Negative balance → warning div показывается, button disabled
- Toast dismissal в session Store (не в БД) — reset при новой сессии
- Query param ?open_recon=1 обрабатывается ОДИН РАЗ (full cleanup после)

**Unit тесты**: 8 тестов OnboardingService покрывают бизнес-логику

---

## Goals Component (Фаза 5 — ЗАВЕРШЕНА, Протокол 0006 — РЕФАКТОРИНГ)

**Файлы**:
- `app/components/goals.py` — UI + callbacks (~1500 строк после протокола 0006)
- `app/assets/goals.css` — стили (~270 строк после протокола 0006)

**Layout** (после протокола 0006):
- Empty state для новых пользователей
- Summary section:
  - Общий прогресс по всем целям
  - Статус распределения бюджета (Budget Alert если не настроен)
  - Кнопка "Настроить бюджет"
- Список карточек целей (вместо одной карточки):
  - Priority badge (#1, #2, #3...)
  - Кнопки ↑↓ для изменения приоритета
  - Прогресс-бар
  - Allocation badge (Полностью/Частично/Не профинансирована/Пропущена)
- Модалы:
  - Создание цели
  - Редактирование цели
  - Добавление взноса
  - Настройка бюджета накоплений
  - Выбор режима накоплений (free/medium/strict) — Протокол 0007
- dcc.ConfirmDialog для удаления

**Callbacks** (10+ callbacks):
- CRUD операции (create, edit, delete, add_contribution)
- Смена статуса (pause, resume)
- Управление приоритетами (move_up, move_down) — Pattern-Matching
- Настройка бюджета (update_budget)
- Смена режима накоплений (update_savings_mode) — Протокол 0007
- `_recalculate_and_render()` — helper для пересчета allocation и рендера

**State Management**:
- `dcc.Store(id="goals-store")` — ID активной цели (для модалов)
- `dcc.Store(id="goals-budget-store")` — текущий бюджет
- `dcc.Store(id="goals-allocation-store")` — результаты AllocationService
- `dcc.Store(id="goals-savings-mode-store")` — режим накоплений (free/medium/strict)

**Интеграция**:
- GoalService для CRUD
- AllocationService для распределения бюджета
- Утилиты форматирования (app/utils/formatters.py)

**Ключевые уроки**:
- Simple IDs > Pattern-Matching для Goals UI (простота callbacks)
- dcc.Store для синхронизации состояния между callbacks
- allow_duplicate=True для множественных Outputs на один компонент
- Helper функции (_recalculate_and_render) для DRY

---

Детали: `architecture.md` (Presentation Layer), `code-style.md` (Dash Callbacks Pattern), `schema.md` (TypedDicts)
