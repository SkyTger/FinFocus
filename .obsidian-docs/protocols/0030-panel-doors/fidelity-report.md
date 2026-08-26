# Fidelity-отчёт: спека epic-11-panel-batch-2 ↔ ветка 0030-panel-doors

> Составлен независимым верификатором на шаге 3.5-m ревью (2026-08-26).
> Верификатору переданы только spec.md, worktree и имена веток — без
> plan.md/log.md/выводов основного ревью. Проверки (pytest, black,
> flake8, замер рендера) выполнены им самостоятельно.

Метод: спека прочитана целиком (6 FR с подпунктами, 2 NFR, 7 C, 10 AC); код проверен по diff `origin/main...HEAD` и чтением файлов; полный pytest, black, flake8 и замер рендера выполнены независимо. План реализации и отчёты исполнителя не читались.

## Сводка

| Вердикт | Кол-во |
|---|---|
| ПОКРЫТО | 23 |
| СДЕЛАНО ИНАЧЕ | 2 (FR-1.a «вчера»; AC-8 — риск дефекта всплытия клика) |
| НЕ ПОКРЫТО | 0 |

## Таблица требований

| ID | Вердикт | Доказательство / комментарий |
|---|---|---|
| FR-1.a Календарь | **СДЕЛАНО ИНАЧЕ** | Окошек **два** (сегодня/завтра), «вчера» нет — `app/services/panel_service.py:349-382`, `app/schema/panel.py:82-108`. Маркер просадки: `dip_is_strong = dip_free <= 0` (факт знака, без порога) — `panel_service.py:391`; усиление классом `pnl-flagline-strong` — `app/components/panel_cards.py:158-185`. Дверь на кликнутый день: `?focus_date=<ISO>` — `panel_service.py:371,380,392`. Детали ниже |
| FR-1.b Цели | ПОКРЫТО | Топ-цель с прогрессом + «по плану / N отстаёт» + подушка строкой внутри карточки: `panel_service.py:395-500`, `panel_cards.py:190-303`. Дверь `/goals?goal=<id>` — `panel_service.py:461` |
| FR-1.c Операции | ПОКРЫТО | 3+3 (`OPERATIONS_PER_GROUP=3`, в норме «2-3») — `app/schema/panel.py:18`, `panel_service.py:502-564`; дверь `/transactions?start=&end=` теми же диапазонами, что выборка — `panel_service.py:178-187`. Только материализованные операции — задокументированное решение владельца 2026-08-25 (`schema/panel.py:216-230`), букве спеки не противоречит |
| FR-1.d Аналитика | ПОКРЫТО | Топ-категория + мини-структура (CSS-полоска, 3 категории) — `panel_service.py:566-615`, `panel_cards.py:372-480`. «Доходы за месяц» отсутствуют — тест `test_no_income_word_in_tree`. Дверь `/analytics` (раздел сам открывается на текущем месяце) |
| FR-1.e Wishlist | ПОКРЫТО | Компактная полоса, не пункт меню — `panel_cards.py:483-551`. Уровень 1: тело `#panel-wishlist-door` → Store `open-wishlist-trigger` → модал (`dashboard.py`, хвост; `wishlist.py:322-340`). Уровень 2: хотелка → `/calendar?wishlist_item=<id>` — `panel_service.py:645`. Но см. риск в AC-8 |
| FR-1.f Настройки | ПОКРЫТО | Шестерёнка шапки осталась (кусок 1, тест `test_who_block_has_avatar_recon_and_cog`); карточки настроек нет |
| FR-2 Конституция | ПОКРЫТО | Все 5 карточек присутствуют всегда (`build_cards_row`, `panel_cards.py:554-581`; тесты `TestCardsConstitution` — OK/EMPTY/FAILED). Сайдбар с дашборда снят: `render_sidebar_slot` возвращает `[]` на `/`, `/dashboard` (`app/main.py`), колонка скрыта `.sidebar-column:empty` (`sidebar.css:18`); на остальных страницах сайдбар строится |
| FR-3 Переходы с контекстом | ПОКРЫТО | Расширен единый обработчик query params: `?focus_date` → Store `calendar-focus-date` (приёмник с двойным guard в `calendar.py:844-857`, подсветка `.calendar-day-focused`), `?goal` → Store `goals-focus-goal` (clientside `apply_goal_focus` — скролл+подсветка, `clientside_triggers.js`, `goals.py`), операции → диапазоны периодов, аналитика → текущий месяц |
| FR-4 Механики-сироты | ПОКРЫТО | Онбординг-тост нулевого баланса не тронут: `toggle_balance_toast` и `persist_toast_dismissal` без изменений (`dashboard.py:816-871`), тост в layout (`dashboard.py:58`) |
| FR-5 Пустые состояния | ПОКРЫТО | `CardStatus.EMPTY` на каждый блок + спроектированные тексты в build-функциях (`panel_cards.py:94-103` и по карточкам); тесты `test_no_currency_or_percent_in_empty_tree`, `TestEmptyBase` (с пользователем и без). Карточки не исчезают |
| FR-6 Единая модель / стратегия загрузки | ПОКРЫТО | `DashboardPanelService.get_panel_data` — один сбор, одна сессия, один вызов `get_money_layers`; карточка «Календарь» — чистая функция от той же модели, что шапка/график (`panel_service.py:325-344`). Стратегия описана явно (докстринг класса: дубли названы и решены, кеша нет осознанно) и защищена тестами (`test_get_money_layers_called_once`, потолок ≤12 запросов) |
| NFR-1 Производительность | ПОКРЫТО | Замер верификатора: `_load_dashboard_components` на локальной базе — **74 мс** (< 2 с). Плюс тест-потолок числа запросов, сессий на рендер — одна (было 3) |
| NFR-2 Наблюдаемость/деградация | ПОКРЫТО | Поблочные `try/except` → `CardStatus.FAILED` + `logger.opt(exception=True)` (`panel_service.py:283-313`); сбой модели слоёв НЕ глотается — вызов вне try (`panel_service.py:277-278`). UI FAILED — индикация без чисел, дверь работает (`panel_cards.py:76-91`). Тесты `TestDegradation` |
| C-1 Разделы не пересматриваются | ПОКРЫТО | В `calendar.py` — только приёмник фокуса (параметр + CSS-класс + guard); в `goals.py` — якорный id + clientside-скролл. Логика разделов не тронута |
| C-2 Дисциплина слоёв | ПОКРЫТО | `panel_service.py` — Decimal, read-only, Dash не импортирует; палитра скопирована, а не импортирована из components (комментарий `panel_service.py:46-52`) |
| C-3 Сервисы не меняются | ПОКРЫТО | Diff по `app/services/` — только новый `panel_service.py` + экспорт в `__init__`. 765 passed (включая прежние 693) |
| C-4 Схема БД | ПОКРЫТО | `app/models/` в diff отсутствует, миграций нет |
| C-5 Контракт MoneyLayers | ПОКРЫТО (тривиально) | `money_layers_service.py`/`schema/money_layers.py` не изменены вовсе; шапка и график живы (тесты куска 1 зелёные) |
| C-6 Колбэки на условные элементы | ПОКРЫТО | Все новые интерактивы — dcc.Link либо Store-триггер (`panel_cards.py` докстринг модуля; wishlist-дверь и аватар сайдбара — clientside timestamp). Прямой Input на аватар удалён из `handle_profile_modal`. Тесты-контракты: `test_no_inputs_on_sidebar_elements`, `test_sidebar_avatar_is_not_a_direct_input` |
| C-7 Шапка/график не регрессируют | ПОКРЫТО | `tests/test_dashboard_panel_ui.py` (47 тестов протокола 0029) в diff не тронут, проходит; «нет вердикта/приветствия/шапка не дверь» — тесты остались |
| AC-1 | ПОКРЫТО | Карточки под шапкой и графиком (`dashboard.py`, layout: `dashboard-cards-row`); сайдбара на дашборде нет, на остальных есть (см. FR-2) |
| AC-2 | ПОКРЫТО | «Завтра» → `?focus_date` (месяц/год берутся из даты фокуса, ячейка подсвечивается); цель → `?goal` + скролл; операции → диапазоны; аналитика → текущий месяц. Продюсер покрыт тестами (`TestCalendarParams`, `TestGoalsParams`); приёмник в календаре — тестами НЕ покрыт (см. раздел тестов) |
| AC-3 | ПОКРЫТО | `test_today_balance_matches_layers`, `test_tomorrow_balance_matches_layers` — сравнение с той же MoneyLayersData |
| AC-4 | ПОКРЫТО | Карточка Цели: топ-цель+сводка+подушка (тест `test_cushion_row_inside_goals_card`); readonly-карточка подушки удалена; split-таблицы удалены |
| AC-5 | ПОКРЫТО | `TestEmptyBase` (сервис, чистая база с пользователем/без), `TestEmptyStates` (UI: нет ₽/% в дереве), включая оговорку про dip на пустой базе (`test_empty_status_ignores_nonempty_dip_fields`) |
| AC-6 | ПОКРЫТО | Код тоста не менялся; прежние тесты `TestToggleBalanceToastProfileUpdated` зелёные |
| AC-7 | ПОКРЫТО | `TestDipMarker`: `test_positive_min_no_strong_class`, `test_zero_or_negative_min_strong_class` — ровно фикстуры спеки |
| AC-8 | **СДЕЛАНО ИНАЧЕ (риск дефекта)** | Оба уровня двери реализованы, но см. детально ниже: клик по хотелке, вероятно, ТАКЖЕ открывает модал управления |
| AC-9 | ПОКРЫТО | Единственный вход открытия — Store `open-profile-trigger`; оба источника (шестерёнка на дашборде, аватар в сайдбаре) пишут в него clientside-триггерами. Тесты: `test_clientside_trigger_registered_for_sidebar_avatar` / `_for_cog`, guard пустого триггера |
| AC-10 | ПОКРЫТО | Прогон верификатора: **765 passed**; `black --check` — чисто; `flake8` — 4 замечания E501, все из pre-existing списка ROADMAP, **новых нет**; рендер 74 мс |

## СДЕЛАНО ИНАЧЕ — детально

**1. FR-1.a: окошка «вчера» нет — карточка «Календарь» показывает сегодня и завтра.**
Спека требует «вчера / сегодня / завтра». В коде — два окошка (`panel_service.py:361-382`), и это НЕ молчаливое отступление: решение владельца 2026-08-26 зафиксировано в `memory/spec-context/epic-11.md` и в докстринге `app/schema/panel.py:3-8`. Причина — расчёт «вчера» три итерации проектирования подряд порождал тихие дефекты. Побочное следствие в плюс: `MoneyLayersService` куском 2 не тронут вовсе (C-5 не потребовался, C-7 тривиален). Формально спека под решение не переиздана — расхождение буквы остаётся.

**2. AC-8: двухуровневая дверь Wishlist — вероятный дефект всплытия клика.**
Найдено чтением кода (в рантайме верификатором не подтверждалось):
- тело полосы `#panel-wishlist-door` имеет `n_clicks`-триггер (clientside → Store → модал), а хотелки — `dcc.Link` **внутри** этого же div (`panel_cards.py:514-535, 545-551`);
- клик в браузере всплывает: React-обработчик родительского div сработает и при клике по дочерней ссылке; `dcc.Link` в Dash 2.17 делает `preventDefault`, но **не** `stopPropagation` (проверено в бандле `dash/dcc/dash_core_components.js` — вхождений `stopPropagation` ноль);
- модал wishlist — в глобальном layout (`app/main.py:97`), `open_wishlist_modal` не имеет guard'а по странице.
Итог: клик по конкретной хотелке, скорее всего, одновременно уводит на `/calendar?wishlist_item=<id>` (как требует AC-8) И открывает модал управления поверх календаря (чего AC-8 не предполагает — уровни двери смешиваются). Тесты это не ловят: они проверяют наличие узла, href'ы и подключение триггера по отдельности, не взаимодействие. Рекомендация: ручной смоук клика по хотелке; фикс — stopPropagation на ссылках-хотелках или guard в `open_wishlist_modal`.

## НЕ ПОКРЫТО — детально

Не найдено требований без реализации.

## Вне спеки

Существенных самовольных изменений нет; заметные попутные:
1. **`app/components/profile_modal.py`** — три `exc_info=True` заменены на `logger.opt(exception=True)` (идиома проекта, п.10 аудита) — спека куска 2 этого не требовала, но правки в русле протокола 0027.
2. **Рефакторинг `sidebar.py` в чистую функцию** с удалением обоих его колбэков и переносом чтения профиля в `render_sidebar_slot` (`main.py`) — крупнее «минимальных приёмников», но это прямое следствие FR-2 и C-6; защищено тестами `TestNoCallbacksInSidebarModule`.
3. **Контракт владения `url.search`** (`_OWNED_SEARCH_PATHS`, `main.py`) — новая инфраструктурная дисциплина, защищающая уже работавший фильтр `/transactions` (дверь FR-3 от неё зависит).
4. Удалены вместе со старой раскладкой: виджет wishlist, кнопки «Добавить» пустых split-таблиц и их два clientside-колбэка, 48 строк `custom.css` — всё следствия AC-4/FR-1.e.

## Тестовое покрытие AC

| AC | Тестами покрыт? | Где |
|---|---|---|
| AC-1 | Да (по частям) | `TestCardsConstitution`, `test_dashboard_returns_empty_before_session`, `TestCreateSidebarPure`/`TestFailOpenProfile` |
| AC-2 | **Частично** | Продюсер параметров — `tests/test_panel_query_params.py`; href'ы окошек и диапазоны — есть. **Приёмник в `load_and_navigate_calendar` (двойной guard, смена месяца по фокусу) юнит-тестами не покрыт**; clientside `apply_goal_focus` — JS, не тестируется по определению |
| AC-3 | Да, unit-тестом как требует спека | `test_today_balance_matches_layers` |
| AC-4 | Да | `test_cushion_row_inside_goals_card`, `test_no_cushion_card_in_row`, `test_groups_and_recurring_marker` |
| AC-5 | Да | `TestEmptyBase`, `TestEmptyStates`, `TestMixedEmptiness` |
| AC-6 | Да (унаследовано) | прежние тесты тоста в `test_dashboard_callbacks.py`, код не менялся |
| AC-7 | Да, unit-тестами как требует спека | `TestDipMarker` — обе фикстуры |
| AC-8 | **Частично** | наличие узла двери, подключение Store-триггера, href'ы хотелок; взаимодействие уровней (всплытие клика) не покрыто — именно там найден риск |
| AC-9 | Да (контрактно) | `tests/test_profile_modal_callbacks.py` |
| AC-10 | Да, проверено прогоном | 765 passed / black чисто / flake8 без новых / рендер 74 мс |

**Итоговая оценка верификатора**: соответствие спеке высокое — 23/25 требований реализованы по букве, оба отступления задокументированы или объяснимы. Требует действия до мержа: ручная проверка клика по хотелке в полосе Wishlist (вероятное смешение двух уровней двери, AC-8); по желанию — дотест приёмника фокуса календаря (AC-2).
