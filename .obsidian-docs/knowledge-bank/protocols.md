---
name: protocols
description: История протоколов разработки FinFocus (0002-0031) — контекст, решения, реализация каждого; включая незапротоколированную packaging-работу
type: reference
originSessionId: -
---

# Протоколы разработки

## Суть
История выполненных протоколов — детализированных технических задач с пошаговой реализацией.

## Формат протокола
Каждый протокол — изолированная задача в worktree с детальным планом (6 шагов), логом работы и commit-trail.

## Завершенные протоколы

### Протокол 0031: Nav Rail (2026-08-30)
**Статус**: 🔄 PR #31 на ревью
**Батч**: Epic-11 «щиток», кусок 3 из 3 (полоска-меню)

**Контекст**: куски 1 и 2 смержены — дашборд стал щитком с шапкой,
графиком полос и пятью карточками-дверями, навигация с него снята.
Но на остальных четырёх экранах по-прежнему стоял широкий сайдбар
(228px), дублирующий двери щитка и отъедающий ширину у содержимого.
Кусок 3 заменяет его полоской иконок 60px.

**Что сделано**:
- `app/components/nav_rail.py` — полоска: знак-домик на дашборд,
  четыре раздела иконками, аватар входом в профиль, подписи язычком
  при наведении. Чистая функция: ни БД, ни колбэков (унаследовано
  от Подхода B куска 2)
- `app/assets/nav_rail.css` — геометрия по утверждённому эскизу;
  у кожуха намеренно НЕТ `overflow: hidden` (язычки выходят за край)
- Разворот при входе с дашборда: CSS-анимация на монтировании узла,
  без единой строки JS. Не переигрывается при переходах
  раздел→раздел — React патчит узел, а не пересоздаёт
- `app/version.py` — единственный источник версии, устойчивый к
  PyInstaller-бандлу; версия показывается в окне профиля
- `app/components/sidebar.py` усох до надгробия с константой
  `ADDITIONAL_NAV_ITEMS`; `sidebar.css` и `test_sidebar.py` удалены

**Закрыты находки UX-аудита 2026-08-20**: P1 «Настройки → 404»
(пункт убран до появления маршрута) и P3 «зашитая v1.0.0 в сайдбаре»
(версия из `app/version.py`, сверяется с git-тегом тестом).

**Ключевые решения и грабли**:
- **Гипотеза реконсиляции проверена ПЕРЕД реализацией** (шаг 1):
  живая проба на приложении в двух режимах (с `id` и без) показала,
  что React переиспользует узел слота при переходах. Без этого вся
  затея с анимацией на монтировании была бы догадкой
- **Носитель идентичности — `id`, а не `key`**: ключ обёртки в
  dash-renderer 2.17.1 = `stringifyId(props.id)`; `dcc.Link` проп
  `key` вообще не принимает (TypeError на построении)
- **`dcc.Link` не принимает `aria-*`** — закрытый список пропсов.
  Доступное имя даётся через `title`; замена на `html.A` отвергнута
  (полная перезагрузка ломает переиспользование узла). Цена:
  активный раздел не помечен `aria-current`
- **`animation-fill-mode: backwards`, а не `both`**: `both` оставил
  бы `clip-path: inset(0)` навсегда и срезал бы язычки
- Анимируется содержимое, а не плашка — отступление от раскадровки
  эскиза, решение владельца Р5 (2026-08-28): подписи важнее
  буквального роста плашки
- Файл `sidebar.py` сохранён, а не удалён — решение владельца Р2:
  прецедент «решение владельца можно обойти удачной трактовкой»
  дороже почти пустого файла

**Тесты**: 808 (было 766). `tests/test_nav_rail.py` (43) — новый
регрессионный якорь навигации; `tests/test_version.py` (7).
Визуальный слой и сам разворот тестами не покрыты принципиально —
проверены живьём (AC-5/AC-6 в браузере, счётчик `animationstart`
и сравнение ссылки на DOM-узел).

**Попутно**: починен протухший тест тултипа платежей — падал в
последние дни месяца (фикстура кладёт платежи на «сегодня + 2/+4»,
тултип отсекает по концу месяца). Тот же класс, что открытый
вопрос №6 ROADMAP, но в форме падения, а не тихого skip.

### Протокол 0030: Panel Doors (2026-08-26)
**Статус**: ✅ СМЕРЖЕНО (2026-08-26, `33c8a11`, PR #30)
**Батч**: Epic-11 «щиток», кусок 2 из 3 (карточки-двери)

**Контекст**: кусок 1 (протокол 0028) и его долги (протокол 0029)
смержены — 693 теста, модель «свободно/платежи/резерв» + шапка +
график полос. Кусок 2 по концепции design.md делает дашборд
единственной навигацией: пять карточек-дверей заменяют сайдбар как
основной вход в разделы. Решение спроектировано `/design-loop`
(4 итерации, финал `solution-v4.md`, ⭐4/5, покрытие спеки 25/25 PASS).

**Решение владельца перед стартом (2026-08-26)**: окошко «вчера» в
карточке «Календарь» убрано из FR-1.a — карточка показывает только
сегодня и завтра. Причина: расчёт «вчера» три итерации проектирования
подряд порождал тихие дефекты (граница расчёта → сумма платежей →
резерв 1-го числа). Следствие: `MoneyLayersService` протоколом 0030
**не затрагивается вообще** — контракт `MoneyLayersData` не меняется,
47 тестов визуального слоя щитка (протокол 0029) не правятся.

**Реализация**:
- `app/schema/panel.py` (новый) — TypedDict-контракты пяти карточек-дверей,
  `CardStatus`, `TRANSACTION_KIND_MAP`, `_empty_*` для каждой карточки
- `app/services/panel_service.py` (новый, ~640 строк) —
  `DashboardPanelService.get_panel_data()`: ОДИН сбор `PanelData` за
  ОДНУ сессию БД (было 3 отдельные сессии на пути сборки прежнего
  layout), пять блоков (calendar/goals/operations/analytics/wishlist)
  в поблочных `try/except` с деградацией — сбой одного блока не роняет
  остальные; `get_money_layers` вызывается вне try/except (модель не
  деградирует)
- `app/components/panel_cards.py` (новый, ~560 строк) — чистые
  build-функции пяти карточек, `_door_shell`, `build_cards_row`; ни
  одного нового серверного Input — переходы делает `dcc.Link` (класс
  регрессий C-6 не создаётся конструктивно)
- `app/components/dashboard.py` — layout щитка = шапка + график +
  `dashboard-cards-row`; удалены раскладка 8/4, split-таблицы
  «Недавние»/«Предстоящие», readonly-карточка подушки, wishlist-виджет
  (~270 строк); `_load_dashboard_components` → 3 Output'а вместо 5
- `app/components/sidebar.py` — снят с дашборда, переведён на Подход B:
  `create_sidebar(pathname, profile)` — чистая функция без БД и
  колбэков; рендерится одним колбэком `render_sidebar_slot(pathname,
  profile_updated)` в `main.py` (`html.Div(id="sidebar-slot")`); ОБА
  прежних колбэка сайдбара (`highlight_active_sidebar`,
  `update_sidebar_profile`) удалены — их Output'ы стали бы условно
  присутствующими при снятии сайдбара с дашборда
- Переходы с контекстом: контракт владения `url.search` —
  `_OWNED_SEARCH_PATHS = frozenset({"/calendar", "/goals"})`
  (`/transactions` со своим владением с протокола 0023 не трогается);
  `handle_panel_query_params` разбирает `focus_date`/`wishlist_item`/
  `open_recon` на `/calendar` и `goal` на `/goals`; два новых Store
  (`calendar-focus-date`, `goals-focus-goal`) с двойным guard'ом
  идемпотентности (triggered_id == Store И новый timestamp)
- 72 новых теста: `tests/test_panel_service.py` (19, композитор),
  `tests/test_panel_cards_ui.py` (26, дерево без БД), `tests/test_sidebar.py`
  (11, регрессионный якорь «в sidebar.py нет ни одного `@callback`»),
  `tests/test_panel_query_params.py` (14, контракт владения `url.search`)

**Отклонённая альтернатива**: guard'ы вместо удаления колбэков
сайдбара — отброшена, маскирует гонку рендера, а не снимает её. Кеш
данных карточек — отброшен: единственный источник инвалидации уже
перерисовывает щиток целиком, кеш дал бы риск устаревших цифр без
выигрыша.

**Дефекты, найденные и исправленные до PR (все три — самопроверкой
шагов, не ревью)**:
1. Шаг 7 — нераспознанные query-параметры возвращали `None` в Store, а
   запись `None` в Store всё равно триггерит подписчиков: клик
   «завтра» → фокус дня применялся и тут же сбрасывался вторым
   рендером по соседнему Store `wishlist-active-item`. Исправлено:
   нераспознанные → `no_update`
2. Шаг 9 — цифра карточки «Аналитика» не совпадала с разделом
   (33 560 ₽ vs 3 560 ₽): карточка брала период до конца месяца,
   раздел — до сегодня (завтрашний расход входил в карточку). Границы
   карточки приведены к границам раздела, добавлен регрессионный тест
3. Шаг 4 (самопроверка) — `_calendar_block` был по ошибке обёрнут в
   `try/except` вопреки решению «чистая функция без побочных эффектов
   и без try/except» — убран

**Найдено на ревью (fidelity-гейт 3.5-m) и исправлено до мержа**:
**AC-8, двухуровневая дверь Wishlist**. Верификатор предсказал по коду
смешение уровней; подтверждено вживую (agent-browser): клик по
хотелке уводил в /calendar И одновременно открывал модал управления
поверх него. Причина — id уровня 1 (`panel-wishlist-door`) висел на
КОНТЕЙНЕРЕ полосы, ссылки-хотелки были его детьми; React-события
всплывают от вложенной ссылки к родителю, `dcc.Link` делает
`preventDefault`, но не `stopPropagation`. Фикс (3.5-m-fix) — слой-
подложка вместо вложенности: id снят с контейнера и заведён на пустой
`position:absolute` слой `.pnl-wish-hitbox` первым ребёнком полосы,
ссылки-хотелки стали его соседями с `z-index:1` выше слоя. Буква AC-8
сохранена целиком (тело полосы → модал, хотелка → календарь). Добавлен
целевой тест `test_wishlist_links_not_inside_door_node` (узел двери
пуст — ссылок внутри нет), mutation-проверен (возврат id на контейнер
красит оба теста). Правило общего вида записано в
`modules/ui-components.md`: **кликабельный контейнер со ссылками
внутри — всегда баг всплытия**, уровни разводить слоями, а не
вложенностью.

**Итог**: 9 шагов, **766 тестов** (693 + 72 по протоколу + 1 на
ревью 3.5-m-fix), ~20 мс рендер щитка (21 SQL-запрос на весь экран:
шапка + график + 5 карточек), CI зелёный (Python 3.10 и 3.12), bandit —
0 findings по 10 изменённым файлам, независимое code review (субагент
вне контекста реализации) — критичных находок нет, 3 минорных
замечания приняты в долг (слабый хелпер теста материализации,
экзотический URL с двумя одновременными query-параметрами, отсутствие
явной константы UI-лимита хотелок в полосе).

**Референсы**:
- План: `.obsidian-docs/protocols/0030-panel-doors/plan.md`
- Лог: `.obsidian-docs/protocols/0030-panel-doors/log.md`
- Ревью: `.obsidian-docs/protocols/0030-panel-doors/review-log.md`
- Решение (источник правды): `.obsidian-docs/design/epic-11-panel-batch-2/solution-v4.md`

---

### Протокол 0029: Panel Debts (2026-08-25)
**Статус**: ✅ СМЕРЖЕН (2026-08-25, merge-коммит 0b3cec5, PR #29; ветка и worktree удалены)
**Батч**: Epic-11 «щиток», долги куска 1 (два независимых хвоста протокола 0028)

**Контекст**: протокол 0028 смержен с двумя зафиксированными хвостами —
латентный дефект расчёта базы остатка календаря (запрещено было чинить
ограничением C-3) и полное отсутствие тестов визуального слоя щитка
(три критерия приёмки проверялись только вручную). Оба записаны в
ROADMAP как долг перед началом куска 2.

**Шаг 1 — багфикс `CalendarService`**:
- Дефект оказался двухслойным, не только «savings игнорируются»:
  (а) `_calculate_recurring_before_date` суммировал только income/expense
  (не вычитал savings-типы); (б) выборка recurring-инстансов шла по
  `original_date` шаблона, а раскладка — по фактической дате, поэтому
  exception, перенесённый через границу окна расчёта, терялся из баланса
  целиком — в обе стороны переноса и для ЛЮБОГО типа операции, не
  только savings
- Фикс: оба метода (`_calculate_recurring_before_date`,
  `_get_recurring_daily_changes`) фильтруют по ФАКТИЧЕСКОЙ дате инстанса;
  первый вычитает savings-типы симметрично соседям и расширяет выборку
  вправо на `RECURRING_LOOKAHEAD_DAYS` (= `RecurringService.MAX_FORECAST_DAYS`,
  привязано импортом); второй расширяет выборку влево до самого раннего
  шаблона
- Минимальный фикс «только добавить savings в total» отвергнут расчётом:
  на кейсе переноса давал двойной счёт со слоем «Платежи» и занижение
  «Свободно» на днях до фактической даты
- Остаточное ограничение (в докстринге): exception с `original_date`
  дальше 366 дней от границы расчёта не подхватывается — вне scope
- 7 регрессионных тестов (6 в `test_calendar_service.py`, 1 E2E в
  `test_money_layers_service.py`), написаны ДО фикса на относительных
  датах. Mutation-проверка: 3 порчи — все пойманы адресными тестами
- Снято «известное ограничение куска 1» из докстрингов `MoneyLayersService`
  и ROADMAP (Epic-11)

**Шаг 2 — тесты визуального слоя щитка**:
- Новый `tests/test_dashboard_panel_ui.py`: 47 тестов в 4 классах, без
  БД (фикстуры-словари `MoneyLayersData` на относительных датах),
  формализуют три ручных критерия приёмки 0028 (AC-1/AC-4/AC-5) и
  инварианты решений владельца (нет вердикта/приветствия, шапка не дверь,
  degraded-сноска, `is_empty`/`window_is_flat` поведение)
- Побочная находка (исправлена): `_axis_tickvals` пробивал собственный
  потолок `MAX_X_TICKS` при длине окна, кратной ему (латентно в проде —
  окно всегда 45); правый край теперь ЗАМЕНЯЕТ последнюю подпись сетки
  вместо добавления сверх нее
- Mutation-проверка: 3 порчи UI-инвариантов — все пойманы

**Итог**: 693 теста (639 + 7 регрессионных + 47 щитка), независимое
code review (субагент чистыми глазами) — критичных проблем нет,
fidelity-гейт пропущен по канону (ad-hoc протокол без спеки батча).

**Референсы**:
- План: `.obsidian-docs/protocols/0029-panel-debts/plan.md`
- Лог: `.obsidian-docs/protocols/0029-panel-debts/log.md`
- Ревью: `.obsidian-docs/protocols/0029-panel-debts/review-log.md`

---

### Протокол 0028: Money Layers Panel (2026-08-24 — 2026-08-25)
**Статус**: ✅ СМЕРЖЕНО (PR #28, 2026-08-25, merge-коммит `a6e566a`)
**Батч**: Epic-11 «щиток», кусок 1 из 3 (модель данных + шапка + график полос)

**Контекст**:
- Дашборд — самый слабый раздел по UX-аудиту 2026-08-20: не отвечает ни
  на один вопрос за 5 секунд, цифры соседних карточек расходятся на
  глаз. Концепция «щиток» (дашборд как навигация по метафоре
  электрощитка) принята владельцем 2026-08-23, эскиз утверждён
  через `/visual`. Кусок 1 из 3 — единственный кусок с новой моделью
  данных; куски 2 (карточки-двери, протокол 0030) и 3 (полоска-меню,
  протокол 0031) выполнены следом
- Проектирование прошло 4 итерации `/design-loop`, финал ⭐5 READY,
  Spec Validator PASS (24/24)

**Решения и реализация**:
- `app/services/money_layers_service.py` (новый, ~838 строк) —
  `MoneyLayersService`, read-only композиция над CalendarService /
  BudgetReservationService / CushionService / GoalService. Раскладывает
  прогнозный остаток каждого дня на три слоя (Свободно/Платежи/Резерв)
  ЕДИНОЙ формулой от даты D, без ветвления по режиму резервирования —
  режимное ветвление (отброшенная альтернатива итерации 3) давало
  двойной счёт при частичном взносе. Инвариант «сумма слоёв == остаток»
  обеспечен конструктивно, а не проверкой
- `app/schema/money_layers.py` (новый, ~225 строк) — TypedDict-контракт
  (`MoneyLayersData`, `DayLayers`, `UpcomingPayment`, `GoalMilestone`,
  `TodaySlice`) + константы (`WINDOW_DAYS=45`, `LAYER_COLORS`, `LAYER_LABELS`)
- `CushionService.get_threshold_amount()` — добавлен аддитивно,
  единственное разрешённое отступление от ограничения C-3 («существующие
  сервисы не менять»); CalendarService/DashboardService/BudgetReservationService/
  GoalService/RecurringService/TransactionService не тронуты
- `app/components/dashboard.py` — полная переделка: шапка-вердикт
  «Свободно сегодня» + график полос (Plotly, `barmode="stack"`, линия
  «сегодня», вехи целей, HTML-легенда с тултипами) ВМЕСТО ряда 4
  KPI-карточек и графика доходы/расходы+баланс (протоколы 0021-0023).
  Удалены приветствие, переключатель Месяц/Год, AI Assistant/Exchange
  карточки и весь связанный мёртвый код
- `app/assets/panel.css` (новый, ~286 строк); `custom.css` почищен
  572 → 419 строк
- **Правка на ревью (регрессия, устранена до мержа)**: первая версия
  подключила шестерёнку щитка к модалу профиля прямым `Input` — сломала
  вход через аватар сайдбара на всех страницах, кроме `/dashboard`
  (клиентский рендерер Dash молча не отправляет callback с недостающим
  в DOM Input'ом; `suppress_callback_exceptions` эту проблему НЕ решает —
  подавляет только серверную валидацию layout). Исправлено переводом на
  Store-триггер + `clientside_callback`, тот же паттерн, что уже
  использовался для кнопок «Сверка». Найден и задокументирован новый
  паттерн: `patterns/callbacks.md` → «Store-триггер для динамически
  рендеренных элементов»
- Тестов: 639 (565 базовых − 2 удалённых `TestBuildGreetingText` + 76
  новых, включая 65 в `test_money_layers_service.py` с mutation-проверкой
  формулы резерва и 7 в `test_profile_modal_callbacks.py`)

**Известное ограничение, не устранённое сознательно**: savings-exception,
перенесённый внутри месяца с даты до сегодня на дату внутри окна,
завышает «Свободно» — латентный дефект `_calculate_recurring_before_date`
(игнорирует savings-типы), исправление которого запрещено C-3.
Кандидат №1 в отдельный протокол до начала куска 2.
**СНЯТО протоколом 0029** (см. запись выше) — правка `CalendarService`
устраняет завышение, докстринги `MoneyLayersService` актуализированы.

**Референсы**:
- План: `.obsidian-docs/protocols/0028-money-layers-panel/plan.md`
- Лог: `.obsidian-docs/protocols/0028-money-layers-panel/log.md`
- Ревью: `.obsidian-docs/protocols/0028-money-layers-panel/review-log.md`
- Решение (источник правды): `.obsidian-docs/design/epic-11-panel-batch-1/solution-v4.md`

---

### Протокол 0027: Audit Quick Wins (2026-08-22)
**Статус**: ✅ MERGED (`c6c5529`, ветка `0027-audit-quick-wins`)
**Батч**: Quick wins из двойного аудита 2026-08-20 (UX + код)

**Контекст**:
- Двойной аудит проекта (2026-08-20) выявил несколько мелких, но
  реальных проблем в существующем коде — не архитектурные, устранимые
  точечно без нового батча

**Решения и реализация**:
- `app/services/purchase_recommendation_service.py`: fail-open стратегия —
  при сбое чтения настроек подушки безопасности рекомендации покупок не
  падают целиком, а логируют сбой с трейсбеком и продолжают без подушки
- `app/services/analytics_service.py`: удалён мёртвый блок `end_of_month`
- Обе точки логирования сбоев переведены на `logger.opt(exception=True)`
  (см. `loguru-exc-info.md` в автопамяти — `exc_info=True` у loguru не
  даёт трейсбек)
- Тесты: `tests/test_analytics_service.py`, `tests/test_purchase_recommendation.py`

**Референсы**:
- План: `.obsidian-docs/protocols/0027-audit-quick-wins/plan.md`
- Лог: `.obsidian-docs/protocols/0027-audit-quick-wins/log.md`

---

### Протокол 0026: Onboarding Refresh (2026-08-21)
**Статус**: ✅ MERGED (`b209721`, ветка `0026-onboarding-refresh`)
**Батч**: Epic-06 (User Profile), исправление UX-дефекта

**Контекст**:
- После редактирования профиля (имя, аватар) приветствие на дашборде
  не обновлялось без перезагрузки страницы — дашборд не был подписан
  на событие изменения профиля

**Решения и реализация**:
- `app/components/dashboard.py`: дашборд подписан на `dcc.Store("profile-updated")`
  (event bus, введённый в протоколе 0024); приветствие — 7-й Output
  в существующем `load_dashboard_data`, а не отдельный callback
  (правка `cc68c18` в ревью — избежать дублирующего callback на одни
  и те же данные)
- `tests/test_dashboard_callbacks.py`: контракт подписок колбэка
  зафиксирован через `inspect.getsource` (+10 тестов, 563 passed)

**Референсы**:
- План: `.obsidian-docs/protocols/0026-onboarding-refresh/plan.md`
- Лог: `.obsidian-docs/protocols/0026-onboarding-refresh/log.md`

---

### Packaging: PyInstaller-сборка (2026-08, незапротоколировано)
**Статус**: ✅ реализовано и работает в CI, но НЕ прошло через процесс
протокола — нет plan.md/log.md, нет записи в ROADMAP/feature_progress на
момент внедрения (см. открытый вопрос №1 ROADMAP)

**Коммиты**: `92fffc7`..`3b6a8e0`, в т.ч. `d9e93c6` (feat(packaging): add
PyInstaller support for standalone Windows build), `3b6a8e0`
(feat(packaging): add macOS build to CI workflow)

**Что сделано**:
- `finfocus.spec` — конфиг PyInstaller, режим `onedir`, исключает
  `alembic`/`tkinter`/`unittest`/`pytest`/`test`, собирает hidden imports
  для Dash/Plotly/dbc
- `.github/workflows/build.yml` — сборка на Windows и macOS runners,
  триггер: push тега `v*` или ручной запуск; готовый ZIP прикладывается
  к GitHub Release

**ВАЖНО — расхождение с протоколом 0025**: 0025 явно отверг PyInstaller
как альтернативу («сложная сборка Dash на 3 платформах») в пользу
setup-скриптов. Эта запись решением протокола 0025 не отменяется
автоматически — PyInstaller появился позже как второй, параллельный
способ доставки, а не замена. **Какой способ доставки основной — открытый
вопрос №1 ROADMAP, решение владельцем не принято.** Не выбирать сторону
в документации; см. также врезку в `deployment.md` и раздел «Сборка
standalone-бандла» в `tech-stack.md`.

---

### Протокол 0025: Beta Delivery & Setup (2026-03-03)
**Статус**: ЗАВЕРШЕН
**Батч**: Epic-09 (Delivery & Setup for Beta Testers)
**Worktree**: `/worktrees/0025-beta-delivery`

**Контекст**:
- Нетехнические бета-тестеры не знают terminal/pip/venv
- Нужен способ запустить Dash web app (localhost:8050) без технических знаний
- Решение: два платформенных скрипта (start.sh + start.bat) с автонастройкой окружения

**Решения**:
- `start.sh` (Linux/macOS) + `start.bat` (Windows) — автоматически создают venv, устанавливают зависимости, запускают браузер
- Маркер `.venv/.deps_installed` для идемпотентных установок (не переустанавливать при каждом запуске)
- Проверка Python 3.10+ с понятными сообщениями об ошибке
- Проверка занятости порта 8050 перед запуском
- `BETA_README.md` — инструкция для тестеров (3 шага установки + 6 FAQ)
- `docs/RELEASE_GUIDE.md` — процесс релиза для команды
- Разделение зависимостей: `requirements.txt` (runtime) + `requirements-dev.txt` (dev/test)

**Реализация** (3 шага):
1. **Скрипты запуска + разделение requirements** (start.sh 168 строк, start.bat 148 строк)
   - start.sh: ss/lsof/netstat fallback chain для проверки порта, xdg-open/open для браузера, trap handler, цветной вывод
   - start.bat: py -3 launcher приоритет, python fallback, xcopy /D /L для timestamp comparison маркера
   - requirements.txt очищен от dev-зависимостей; requirements-dev.txt создан с pytest/black/flake8

2. **Документация** (BETA_README.md 86 строк, docs/RELEASE_GUIDE.md 82 строки)
   - BETA_README.md: 3-шаговая установка (скачать → запустить → открыть браузер), 6 FAQ с типичными проблемами
   - RELEASE_GUIDE.md: формат тега v0.9.0-beta.N, команда git archive для ZIP, шаблон Release Notes, чеклист

3. **QA финализация**
   - black OK, flake8 6 E501 pre-existing, pytest 546 passed / 7 failed (все pre-existing)

**Результат**:
- Бета-тестер запускает приложение двойным кликом на start.sh/start.bat
- Приложение открывается в браузере автоматически
- Повторные запуски: зависимости не переустанавливаются (маркер)

**Критичные детали**:
- **Python 3.10+ (не 3.12)** — намеренно для широкой совместимости у тестеров
- **Маркер `.venv/.deps_installed`** — проверяется по timestamp; touch при успешной установке
- **start.bat xcopy /D /L** — имитирует timestamp-сравнение (xcopy dry-run проверяет newer)
- **Порт 8050** — check через ss/lsof/netstat (fallback chain) на Linux; netstat на Windows
- **git archive для ZIP** — исключает .git, .venv, data/ автоматически через .gitattributes
- **requirements-dev.txt** — pytest, black, flake8, coverage; не нужны пользователям

**Альтернативы** (отвергнуты на момент протокола):
- Python-launcher — проблема "курица и яйцо" (нужен Python для запуска Python)
- Docker — слишком сложен для нетехнических пользователей
- PyInstaller — сложная сборка Dash на 3 платформах (в Backlog post-beta)

**⚠️ Решение по PyInstaller пересмотрено фактом**: несмотря на отказ
здесь, PyInstaller позже реализован и работает в CI (см. запись
«Packaging: PyInstaller-сборка» выше) — как второй способ доставки,
не как замена setup-скриптов. Какой способ основной — открытый
вопрос №1 ROADMAP, не решено.

**Референсы**:
- Рабочая директория: `/worktrees/0025-beta-delivery`
- RELEASE_GUIDE: `docs/RELEASE_GUIDE.md`
- Инструкция для тестеров: `BETA_README.md`

---

### Протокол 0020: Postponed Purchases (Wishlist) (2026-02-04)
**Статус**: ✅ ЗАВЕРШЕН (в процессе финализации)
**Батч**: Epic-04-Advanced Features (Batch 4, Postponed Purchases)
**Worktree**: `/worktrees/0020-postponed-purchases`

**Контекст**:
- Пользователю нужен инструмент для управления списком желаемых покупок (wishlist) с подбором безопасной даты на основе кассового календаря
- Проблема: пользователь не знает "когда безопасно купить", чтобы не опускать баланс ниже порога подушки безопасности
- Решение: виджет на Dashboard + модал управления + календарь с overlay для выбора даты + JS hover для каскадного пересчета остатков

**Решения**:
- WishlistItem ORM модель (7 полей: name, amount, category_id, priority, status, planned_date, planned_transaction_id)
- WishlistService для CRUD + planning workflow (mark_as_planned, reset_planned, check_orphaned_planned)
- PurchaseRecommendationService для расчета safe dates и предрассчета hover data
- Dashboard виджет с фокусными покупками (priority=1, до 5)
- Wishlist модал с CRUD + кнопками "Запланировать"
- Calendar wishlist mode через query param ?wishlist_item=ID
- Overlay-баннер с легендой, счетчиком дней, кнопкой "Отмена"
- JS hover (wishlist_hover.js) для каскадного пересчета балансов без server calls
- Preselection Store Pattern для передачи данных в create-modal
- Orphan detection callback для сброса статуса при удалении транзакции

**Реализация** (11 шагов):
1. **Schema + Model + Migration** (commit: 80d1ad2, 8b28dd4)
   - WishlistItemData, SafeDateInfo, HoverBalances TypedDicts
   - WishlistItem ORM: FK user_id, category_id, planned_transaction_id (ON DELETE SET NULL)
   - scripts/migrate_006_wishlist.py (idempotent)

2. **WishlistService** (commit: a6f0b84)
   - CRUD: create_item, get_all, get_focus, get_by_id, update_item, delete_item
   - Planning: mark_as_planned, reset_planned
   - Utility: check_orphaned_planned, to_data
   - Валидация: name (1-100), amount > 0, priority in {1, 2}
   - Planned guard: status="planned" → только name, priority

3. **PurchaseRecommendationService** (commit: ab7f32d)
   - get_safe_dates_map() — карта безопасности дней (cushion + negative_balance)
   - precalculate_hover_data() — предрассчет ~960 балансов для JS hover
   - Зависимости: CalendarService.calculate_daily_balances(), CushionService.get_settings()
   - Формула: min(balance[d:end] - amount) для проверки safe

4. **Unit тесты сервисов** (commit: a17c82f)
   - tests/test_wishlist_service.py: 31 тест
   - tests/test_purchase_recommendation.py: 11 тестов
   - Всего: 483 теста (было 441, +42)

5. **Wishlist UI (виджет + модал)** (commit: ae3e15c)
   - build_wishlist_widget() — Dashboard карточка с 5 фокусными
   - create_wishlist_modal() — модал с inline-формой, секции Focus/Later
   - _build_replan_confirm_modal() — confirm dialog перепланирования
   - 9 callbacks: open/add/delete/edit/replan flow/plan navigate
   - ADR-003 guard clauses

6. **Dashboard + Main интеграция** (commit: 8f1e4d7)
   - Виджет в dashboard.py правая колонка
   - create_wishlist_modal() в main.py layout
   - dcc.Store wishlist-active-item
   - handle_calendar_query_params() для ?wishlist_item=ID

7. **Calendar wishlist module** (commit: 3a5d4b2)
   - calendar_wishlist.py (~280 строк)
   - build_wishlist_overlay_banner() — название, сумма, легенда, счетчик
   - build_wishlist_day_cell() — safe/unsafe маркеры, data-date, reasons tooltip
   - build_wishlist_calendar_grid() — полная сетка с .wishlist-mode CSS
   - cancel_wishlist_mode callback

8. **Calendar.py расширение** (commit: 236228e)
   - data-date атрибут на .calendar-day-balance
   - dcc.Stores: wishlist-safe-dates, wishlist-hover-data
   - wishlist-overlay div в layout
   - load_and_navigate_calendar расширен: +Input wishlist-active-item, +3 Outputs
   - Wishlist mode: PurchaseRecommendationService + wishlist grid
   - wishlist.css: +55 строк (overlay, markers, safe/unsafe, hover, past-day)

9. **JS hover asset** (commit: e7a0f3c)
   - wishlist_hover.js (~145 строк)
   - IIFE pattern, 'use strict'
   - rubleFormatter: Intl.NumberFormat('ru-RU')
   - getHoverData(), applyHoverBalances(), restoreBaseBalances()
   - attachHoverListeners() — mouseenter/mouseleave, data-hover-attached guard
   - observeContainer() — MutationObserver для .wishlist-mode
   - init() с DOMContentLoaded / readyState check

10. **Preselection + mark_planned** (commit: f9c8a41)
    - transaction_modals.py: +4 Stores (amount, date, description, risk-warning)
    - set_preselection_on_modal_open() расширен для source="wishlist" (7 outputs)
    - create_transaction: +wishlist_item_id State, +4 reset stores (19 outputs)
    - calendar_wishlist.py: open_create_from_wishlist_day() с ADR-003 guards
    - wishlist.py: mark_wishlist_planned_after_create(), detect_orphaned_wishlist()

11. **Финализация** (commit: TBD)
    - Black: 8 файлов
    - Flake8: 5 F401 + 3 E501
    - Pytest: 483 tests passed

**Результат**:
- +~1700 строк кода (services + UI + JS)
- +~280 строк tests
- +42 unit тестов (483 всего)
- Полноценный wishlist workflow: add → plan → calendar mode → hover → select → create transaction → mark planned
- JS hover без server calls (< 1ms vs ~200ms предрассчет)
- Orphan detection для data integrity

**Критичные детали**:
- **Каскадный hover**: пересчет балансов от выбранного дня до конца месяца (не только день покупки)
- **Статическая карта safe/unsafe**: pre-calculated, не меняются при hover (UX clarity)
- **Orphan detection**: ON DELETE SET NULL + callback detect_orphaned_wishlist()
- **Planned guard**: статус "planned" блокирует изменение amount, category_id
- **JS MutationObserver**: обнаружение .wishlist-mode для подключения hover listeners
- **Preselection 4 Stores**: amount, date, description, risk_warning (7 outputs в set_preselection)
- **data-hover-attached**: guard против повторного подключения listeners

**Альтернативы** (отвергнуты):
- Dash clientside_callback для hover — проблемы с _dashprivate_setProps, выбран нативный JS
- Tooltip + hover одновременно — конфликт, Known Limitation для MVP
- Отдельная страница /wishlist — модал достаточен для 5-15 хотелок

**Референсы**:
- План: `.protocols/0020-postponed-purchases/plan.md`
- Лог: `.protocols/0020-postponed-purchases/log.md`
- Спецификация: `.reports/epics/epic-04-advanced/postponed-purchases-spec.md`
- Design brief: `.design/brief.md`
- Solution v3: `.design/solution-v3.md`

---

### Протокол 0019: Contribution Edit/Delete (2026-02-04)
**Статус**: ✅ MERGED (PR #19, merge commit 8e48858)
**Батч**: Epic-04-Advanced Features (Batch 4, Contribution Edit/Delete)

**Контекст**:
- В Goals UI можно добавлять взносы, но нельзя редактировать или удалять их
- Нужна полноценная CRUD для GoalContribution с каскадной синхронизацией
- Требуется блокировка SAVINGS_CONTRIBUTION в calendar tooltip (как SAVINGS_RESERVE)

**Решения**:
- update_contribution() в GoalService с каскадной синхронизацией (Contribution → Transaction → current_amount → Exception)
- Переписан delete_contribution() по Варианту A (прямое удаление без delete_contribution_transaction())
- Calendar Guard #6: блокировка SAVINGS_CONTRIBUTION в tooltip
- Goals UI: таблица взносов с кнопками Edit/Delete

**Реализация** (6 шагов):
1. Schema + Helpers: ContributionInfo, ContributionUpdateResult TypedDicts, _get_budget_service()
2. Service Methods: update_contribution(), переписан delete_contribution()
3. Calendar Guard #6: блокировка SAVINGS_CONTRIBUTION в tooltip
4. Goals UI: таблица взносов, модалы edit/delete, 4 callbacks
5. Unit Tests: 23 новых (441 всего)
6. Финализация: Black, Flake8, pytest OK

**Результат**: +~300 строк, +23 теста, полный CRUD для GoalContribution

---

### Протокол 0018: Budget Reservation Bugfix (2026-02-02)
**Статус**: ✅ MERGED (PR #18, merge commit TBD)
**Батч**: Epic-04-Advanced Features (Batch 4, Budget-Calendar Integration bugfix)
**Worktree**: `/worktrees/0018-budget-reservation-bugfix`

**Контекст**:
- Протоколы 0016-0017 реализовали интеграцию бюджета с календарём, но выявлены критические баги:
  - При переключении режима fixed_date → from_balance → fixed_date ранее внесённые суммы "забывались"
  - Exception сбрасывался при переключении режимов — досрочный взнос терялся
- Корневая причина: создание нового шаблона при каждом переключении → exceptions становились orphan (привязаны к старому template_id)

**Решения**:
- Переиспользовать существующий шаблон при совпадении дня
- Добавить recalculate_current_month_exception() для пересчёта при изменениях
- GoalService.delete_contribution() с lazy import для избежания circular dependency
- _cleanup_orphan_exceptions() с логированием

**Реализация** (10 шагов):
1. **Helper методы** (commit 644bef6)
   - _find_any_reserve_template() — поиск любого шаблона (включая остановленный)
   - _get_template_day() — извлечение дня из шаблона (EOM → 31)
   - _get_reserve_date_for_month() — дата резерва с учётом коротких месяцев
   - _delete_exception_for_date() — удаление exception для даты

2. **recalculate метод** (commit b5a1204)
   - recalculate_current_month_exception(user_id, reference_date)
   - Расширен _get_contributions_sum_for_month параметром before_date
   - Логика: нет взносов → удалить exception, есть → создать/обновить
   - Lazy import RecurringService (как в adjust_reserve_for_contribution)

3. **cleanup + logging** (commit 408308a)
   - _cleanup_orphan_exceptions(template_id) — удаляет exceptions остановленного шаблона
   - logger.info() при удалении, logger.debug() если нечего удалять

4. **set_mode модификация** (commit 88f044b)
   - Логика переиспользования шаблонов:
     - Тот же день → реактивируем (recurring_end_date = None, exceptions сохраняются)
     - Другой день → stop + cleanup + create new
     - from_balance → stop (exceptions НЕ чистим — пригодятся при возврате)

5. **get_budget_progress** (commit b68e2d0)
   - Унифицирован расчёт used_budget — взносы для обоих режимов
   - mode_text = "Внесено" для обоих режимов

6. **GoalService** (commit 5f4cf36)
   - delete_contribution() в GoalService
   - Lazy import BudgetReservationService (избежание circular dependency)
   - Удаление транзакции если есть → пересчёт exception

7. **Callbacks интеграция** (commit 16975a5)
   - goals.py: save_budget — добавлен recalculate_current_month_exception после set_mode
   - budget_reservation_service.py: update_contribution_transaction — добавлен recalculate

8. **Unit тесты** (commit afbe1dc)
   - 13 новых тестов для protocol-0018 (всего 45 в test_budget_reservation_service.py)
   - Исправлен test_progress_fixed_date_mode (mode_text → "Внесено")

9. **Integration тесты** (commit 4a572a7)
   - test_budget_calendar_integration.py с 3 E2E тестами
   - pytest.skip() для дат >= reserve_day (тесты требуют today < reserve_day)

10. **Финализация** (commit 18d6a1c)
    - Black: 2 files reformatted
    - Flake8: E501 fix в docstring
    - Pytest: 418 passed (было 402, +16)

**Результат**:
- +~250 строк в BudgetReservationService
- +13 unit тестов, +3 integration тестов (418 всего)
- Решены оба критических бага
- Exceptions сохраняются при переключении режимов

**Критичные детали**:
- **Template reuse logic**: тот же день → reactivate, разный → stop + cleanup + new
- **recalculate_current_month_exception**: вызывается при delete/update contribution, изменении бюджета
- **Lazy import pattern**: используется в delete_contribution для избежания circular import
- **Orphan cleanup**: удаляет exceptions только для остановленных шаблонов с recurring_end_date < today
- **reference_date parameter**: переименован из month для консистентности с get_budget_progress()

**Альтернативы** (отвергнуты):
- Event-driven пересчёт через signals — overcomplicated для MVP
- Обновление шаблона вместо Exception — проблема с расчётом следующего месяца

**Референсы**:
- План: `.protocols/0018-budget-reservation-bugfix/plan.md`
- Лог: `.protocols/0018-budget-reservation-bugfix/log.md`
- Спецификация: `.reports/epics/epic-04-advanced/spec-budget-reservation-bugfix.md`
- Solution v3: `.design/solution-v3.md`

---

### Протокол 0017: Budget UI Improvements (2026-02-02)
**Статус**: ✅ MERGED (PR #17, merge commit TBD)
**Батч**: Epic-04-Advanced Features (Batch 4, Budget-Calendar Integration improvements)
**Worktree**: `/worktrees/0017-budget-ui-improvements`

**Контекст**:
- Протокол 0016 реализовал интеграцию бюджета с календарём, но выявлены UX проблемы:
  - Непонятный текст "Резерв на цели" → что это значит?
  - Дублирование UI: карточка прогресса бюджета + сводка целей
  - Взносы до даты резерва (fixed_date) не уменьшают сумму резервирования
- Как улучшить UX бюджета накоплений и реализовать корректное поведение при досрочных взносах?

**Решения**:
- Изменить текст на "Резервирование бюджета" (ясность назначения)
- Удалить верхнюю карточку, объединить информацию в "Сводку по целям"
- При взносе до даты резерва — создавать Exception для recurring с уменьшенной суммой
- Формат сводки: "Бюджет накоплений (месяц): X / Y ₽" + "Сумма активных целей: Z ₽"

**Реализация** (6 шагов):
1. **UI Description** (commit c4ae7ad)
   - RESERVE_DESCRIPTION: "Резерв на цели" → "Резервирование бюджета"
   - "(авто)" суффикс подтвержден в calendar.py

2. **Remove Budget Card** (commit 6ba5570)
   - Удалена _build_budget_progress_card() (~70 строк)
   - Удалён container budget-progress-card-container
   - Удалён Store budget-progress-refresh-trigger
   - Удалён callback load_budget_progress_card() (~55 строк)
   - Итого удалено: ~130 строк кода

3. **Update Summary** (commit fa13a27)
   - Параметр budget_progress: BudgetProgress в _build_summary_section()
   - Секция "Бюджет накоплений": формат "used / total" с подписью "В текущем месяце"
   - Вызов BudgetReservationService.get_budget_progress() в _recalculate_and_render()

4. **Fixed Date Mechanism** (commit 5d5074d)
   - adjust_reserve_for_contribution() метод в BudgetReservationService (~70 строк)
   - Логика: взнос ДО даты резерва → Exception с уменьшенной суммой
   - Если взносы ≥ бюджета → description "(внесено досрочно)"
   - Использует RecurringService.create_exception()

5. **Integration Tests** (commit 2c7e834)
   - Интеграция adjust_reserve_for_contribution() в GoalService.add_contribution()
   - 6 unit тестов для TestAdjustReserveForContribution
   - Исправлен вызов RecurringService.create_exception() (правильные аргументы)
   - Все 402 теста PASSED

6. **Финализация** (commit 962349e)
   - Black: 1 файл переформатирован (goals.py)
   - Flake8: OK
   - Pytest: 402 теста PASSED
   - PR #17 Ready for Review

**Результат**:
- +~70 строк adjust_reserve_for_contribution() метод
- -~130 строк удалённая карточка прогресса
- +6 unit тестов (402 всего)
- Улучшенный UX без дублирования интерфейса
- Корректное поведение при досрочных взносах

**Критичные детали**:
- **adjust_reserve_for_contribution** — создаёт Exception для recurring при взносе до reserve_date
- **Exception суммы** — original_amount - SUM(contributions_before_reserve_date)
- **"(внесено досрочно)"** — description когда взносы полностью покрыли бюджет
- **from_balance guard** — метод ничего не делает в режиме from_balance
- **Сводка целей** — единая секция объединяет бюджет и сумму активных целей

**Альтернативы** (отвергнуты):
- Обновление шаблона вместо Exception — проблема с расчётом следующего месяца
- Виртуальный расчёт при рендере — проблемы с производительностью

**Референсы**:
- План: `.protocols/0017-budget-ui-improvements/plan.md`
- Лог: `.protocols/0017-budget-ui-improvements/log.md`
- Спецификация: `.reports/epics/epic-04-advanced/spec-budget-ui-improvements.md`

---

### Протокол 0016: Budget-Calendar Integration (2026-02-02)
**Статус**: ✅ MERGED (PR #16, merge commit fdea488)
**Батч**: Epic-04-Advanced Features (Batch 4, Budget-Calendar Integration)
**Worktree**: `/worktrees/0016-budget-calendar`

**Контекст**:
- FinFocus MVP имеет систему накопительных целей с monthly_savings_budget, но бюджет не отражается в кассовом календаре
- Пользователь не видит, как накопления влияют на остатки по дням
- Как связать бюджет накоплений с календарём, чтобы пользователь видел влияние резервирования на остаток?

**Решения**:
- Два режима резервирования:
  - **fixed_date** — recurring операция "Резервирование бюджета" в календаре на указанную дату (1-28 число)
  - **from_balance** — операции "Взнос: цель" при каждом взносе
- Новый BudgetReservationService для управления резервированием
- Два новых TransactionType: SAVINGS_RESERVE, SAVINGS_CONTRIBUTION
- FK связь GoalContribution → Transaction для целостности данных
- Динамический бюджет: remaining = total - SUM(contributions_this_month)

**Реализация** (8 шагов):
1. **Schema + Migration** (commit 66a0a6f)
   - TransactionType: +SAVINGS_RESERVE, +SAVINGS_CONTRIBUTION
   - User: +reservation_mode (default "from_balance"), +reservation_day (nullable, 1-28)
   - GoalContribution: +transaction_id FK (SET NULL), +ix_contribution_date index
   - Migration: scripts/migrate_005_reservation.py (idempotent)
   - Unit tests: 15 passed (8 новых тестов)

2. **BudgetReservationService Core** (commit 20fe4c3)
   - TypedDicts: ReservationMode, BudgetReservationSettings, BudgetProgress, ContributionRecord
   - BudgetReservationService: get_settings(), set_mode(), get_budget_progress()
   - Private helpers: _get_reserve_template(), _create_reserve_template(), _stop_reserve_template()
   - Экспорт в schema/__init__.py и services/__init__.py
   - Unit tests: 17 passed

3. **BudgetReservationService CRUD** (commit 19c1bef)
   - create_contribution_transaction() — создаёт SAVINGS_CONTRIBUTION в режиме from_balance
   - update_contribution_transaction() — синхронизирует Transaction ↔ GoalContribution ↔ Goal
   - delete_contribution_transaction() — каскадное удаление с обновлением цели
   - sync_template_amount() — синхронизация суммы шаблона с бюджетом
   - Unit tests: 26 passed (+9 новых)

4. **CalendarService Integration** (commit ade680f)
   - _calculate_balance_before_date() — добавлены SAVINGS_RESERVE, SAVINGS_CONTRIBUTION
   - _get_daily_changes() — добавлены новые типы (уменьшают баланс как EXPENSE)
   - _get_recurring_daily_changes() — обработка savings_reserve, savings_contribution
   - _get_recurring_totals_for_period() — аналогично
   - Unit tests: 34 passed (+4 новых)

5. **GoalService Integration** (commit d17dab7)
   - add_contribution() — создаёт SAVINGS_CONTRIBUTION транзакцию (from_balance режим)
   - add_contribution() — guard clause для COMPLETED целей
   - add_contribution() — warning logging при budget=0
   - update_savings_budget() — sync_template_amount для fixed_date
   - Unit tests: 8 passed (+4 новых)

6. **Goals UI** (commit 1ef4503)
   - _build_budget_progress_card() — карточка прогресса бюджета (цвета по статусу)
   - budget-progress-card-container — контейнер в layout
   - load_budget_progress_card callback — загрузка при переходе на /goals
   - CSS стили .budget-progress-card с gradient header
   - _build_mode_selector_modal() — модал выбора режима резервирования
   - toggle_mode_selector, handle_mode_change callbacks — интерактивность
   - BudgetReservationSettings TypedDict с mode/day

7. **Calendar UI** (commit f1ff0df)
   - ICON_TO_EMOJI: добавлены savings_reserve (💼), savings_contribution (🎯)
   - _build_tooltip_transaction_row(): специальная обработка SAVINGS типов
     - SAVINGS_RESERVE: readonly, id=-1, "(авто)" суффикс, без 🔁 иконки
     - SAVINGS_CONTRIBUTION: кликабельно → edit modal
   - CSS: .tooltip-txn-amount.savings (purple), .tooltip-txn-row.readonly
   - open_edit_from_tooltip(): +txn_type в Pattern-Matching ID, guard для savings_reserve
   - Unit tests: 14 новых тестов для SAVINGS визуализации (395 passed)

8. **Финализация** (commit fdea488)
   - Black: OK
   - Flake8: OK (E501 pre-existing)
   - Pytest: 396 тестов passed (было 343, +53)
   - PR #16 merged в main

**Результат**:
- +~280 строк BudgetReservationService
- +~300 строк UI (goals + calendar)
- +53 unit и integration тестов (396 всего)
- FK связь GoalContribution → Transaction (SET NULL)
- Визуализация SAVINGS операций в календаре
- Карточка прогресса бюджета на /goals

**Критичные детали**:
- **Два режима**: fixed_date (recurring) vs from_balance (per contribution)
- **FK связь**: GoalContribution.transaction_id → Transaction.id (SET NULL ondelete)
- **Динамический бюджет**: remaining = total - SUM(contributions_this_month)
- **SAVINGS_RESERVE readonly**: нельзя редактировать напрямую (only через mode settings)
- **Sync template**: sync_template_amount() синхронизирует recurring шаблон с budget
- **SAVINGS операции**: уменьшают баланс в календаре, но не считаются расходами для целей
- **Migration 005**: idempotent script для добавления reservation_mode, reservation_day

**Референсы**:
- План: `.protocols/0016-budget-calendar/plan.md`
- Лог: `.protocols/0016-budget-calendar/log.md`
- Brief: `.design/brief.md`
- Solution v2: `.design/solution-v2.md`
- Спецификация: `.reports/epics/epic-04-advanced/spec-budget-calendar-integration.md`

---

### Протокол 0015: Calendar Tooltip (2026-02-01)
**Статус**: ✅ MERGED (PR #15, merge commit c9f7110)
**Батч**: Epic-04-Advanced Features (Batch 4, Calendar Tooltip)
**Worktree**: `/worktrees/0015-calendar-tooltip`

**Контекст**:
- В кассовом календаре пользователь видит только иконки операций и баланс, но не детали
- Нужен быстрый способ просмотра списка операций дня без открытия модала
- Как показать детальную информацию о дне при наведении без конфликта с существующим кликом?

**Решения**:
- CSS-only hover tooltip как sibling элемент к кликабельной области
- Expand/collapse через CSS checkbox hack (max 5 visible операций)
- Glassmorphism стиль с backdrop-filter blur
- Pattern-Matching callback для клика по операции в tooltip
- На mobile (< 768px) tooltip отключен

**Реализация** (7 шагов):
1. **Extend TransactionInfo** (commit 77db700)
   - Добавлены поля is_skipped: bool, category_icon: str | None в TransactionInfo
   - Добавлены поля is_skipped: bool, category_icon: str | None в VirtualTransaction
   - CalendarService: заполнение новых полей в get_all_transactions_for_period()
   - RecurringService: заполнение category_icon в generate_instances()

2. **CSS Styles** (commit a50a7f3)
   - Glassmorphism tooltip: backdrop-filter blur, rgba background, transitions
   - Edge detection для правых 2 колонок (nth-child)
   - CSS checkbox hack для expand/collapse
   - Mobile: display:none на 768px

3. **DOM Restructure** (commit c28f455)
   - Константа MAX_VISIBLE_TRANSACTIONS = 5
   - Sibling structure: clickable_content + tooltip в wrapper

4. **Tooltip Builders** (commit 68998f6)
   - _build_tooltip_balance() — header с балансом
   - _build_tooltip_transaction_row() — строка операции с emoji, суммой
   - _build_day_tooltip() — полный tooltip с expand/collapse
   - Pattern-Matching ID для tooltip-txn

5. **Edit Callback** (commit 2318c57)
   - open_edit_from_tooltip() — Pattern-Matching callback
   - 4 ADR-003 guard clauses
   - is_virtual → scope modal, иначе → edit modal

6. **Unit Tests** (commit 90e595c)
   - tests/test_calendar_tooltip.py: 20 тестов
   - Fix: Dash PM ID не поддерживает None → placeholder -1 для template_id

7. **Финализация** (commit c9f7110)
   - Black: 2 файла OK
   - Flake8: 1 unused import исправлен
   - Pytest: 343 тестов passed (было 300, +43)

**Результат**:
- +~200 строк в calendar.py (tooltip builders + callback)
- +~200 строк CSS стилей
- +43 unit тестов (343 всего)
- CSS-only tooltip (zero server calls)
- Glassmorphism стиль

**Критичные детали**:
- CSS-only tooltip — zero server calls, instant response
- Sibling structure — clickable_content + tooltip как siblings в wrapper
- Checkbox hack — expand/collapse без JavaScript
- Pattern-Matching ID: {"type": "tooltip-txn", "date": ..., "id": ..., "is_virtual": bool, "template_id": int | -1}
- Placeholder -1 для template_id (Dash не поддерживает None в PM IDs)
- Mobile disabled — tooltip не показывается на < 768px

**Референсы**:
- План: `.protocols/0015-calendar-tooltip/plan.md`
- Лог: `.protocols/0015-calendar-tooltip/log.md`
- Solution v3: `.design/solution-v3.md`

---

### Протокол 0014: Onboarding Wizard (2026-01-31)
**Статус**: ✅ MERGED (PR #14)
**Батч**: Epic-04-Advanced Features (Batch 4, Onboarding)
**Worktree**: `/worktrees/0014-onboarding-wizard`

**Контекст**:
- FinFocus требует корректной настройки starting_balance для точных расчетов кассового календаря
- Новые пользователи часто пропускают этот критичный шаг
- Как обеспечить настройку starting_balance при первом входе без блокировки опытных пользователей?

**Решения**:
- Blocking modal-wizard при first_launch=True
- Toast на Dashboard для пользователей с balance=0 (мягкое напоминание)
- Calendar query param ?open_recon=1 для автооткрытия модала сверки
- Fail-closed DB strategy (wizard скрывается при ошибке, не блокирует приложение)
- Flush/commit contract в сервисе (docstring)

**Реализация** (11 шагов):
1. **Schema + Model** (commit 0659dfc)
   - User.first_launch: Boolean, default=True, nullable=False
   - OnboardingStatus TypedDict (first_launch, starting_balance, needs_balance_alert)
   - Exported in app/schema/__init__.py

2. **Migration Script** (commit e048e7a)
   - scripts/migrate_003_first_launch.py
   - Logic: starting_balance != 0 → first_launch = False
   - Idempotent: проверяет PRAGMA table_info перед ALTER

3. **OnboardingService** (commit f70e66e)
   - get_status(user_id) → OnboardingStatus
   - complete_with_balance(user_id, starting_balance) — flush(), caller commit()
   - skip(user_id) — first_launch=False, balance остается 0
   - Flush/commit contract documented в class docstring
   - Exported in app/services/__init__.py

4. **Unit Tests** (commit e666816)
   - tests/test_onboarding_service.py: 8 тестов
   - TestGetStatus (3), TestCompleteWithBalance (3), TestSkip (2)
   - Added email field to User fixtures (model requirement)

5. **Wizard UI** (commit ae8824d)
   - app/components/onboarding_wizard.py
   - Blocking modal: backdrop="static", keyboard=False, no close button
   - InputGroup с ruble sign, warning div для negative balance
   - Buttons: "Пропустить" (secondary), "Продолжить" (success, disabled by default)

6. **Wizard Callbacks** (commit 3bab87f)
   - check_onboarding_and_validate: checks first_launch on URL change, validates input
   - handle_onboarding_action: submit or skip с ADR-003 guard clauses
   - DB failure strategy: fail-closed (hide wizard on error)

7. **Main Integration** (commit c5cd192)
   - Exported create_onboarding_wizard в app/components/__init__.py
   - Added wizard to main.py layout после transaction_modals
   - Added dcc.Store("balance-toast-dismissed") для toast session state

8. **Dashboard Toast** (commit 59eb24b)
   - _build_balance_toast() function для zero-balance warning
   - Toast shows если starting_balance == 0 и not dismissed
   - CTA button links to /calendar?open_recon=1
   - 2 callbacks: toggle_balance_toast, persist_toast_dismissal

9. **Calendar Query Param** (commit d4a0f92)
   - Extended toggle_reconciliation_modal для обработки ?open_recon=1
   - Added Input("url", "search") и State("url", "pathname")
   - Query cleanup strategy: full (returns "" to clear query string)
   - All return statements updated с 6th element для url.search

10. **CSS Styles** (commit cd891f1)
    - app/assets/onboarding.css (~80 lines)
    - Стили .onboarding-modal (green gradient header, border-radius)
    - Стили .balance-toast (warning colors)
    - Responsive adjustments для mobile

11. **Финализация** (commit 3b72b95)
    - Black: 2 files reformatted
    - Flake8: fixed 2 E501 line too long errors
    - Pytest: 300 tests PASSED (было 292, +8 для OnboardingService)
    - PR #14 marked as Ready

**Результат**:
- +~500 строк (onboarding_wizard.py, dashboard toast, calendar query param)
- +~80 строк OnboardingService
- +8 unit тестов (300 всего)
- Migration script для существующих пользователей
- Fail-closed DB strategy для production safety

**Критичные детали**:
- User.first_launch — Boolean флаг (не Nullable, default=True)
- Flush/commit contract — сервис flush(), caller commit() (documented в docstring)
- Fail-closed DB strategy — wizard скрывается при ошибке БД, не блокирует UI
- Query param full cleanup — url.search = "" (не оставляем артефактов в URL)
- ADR-003 guard clauses — n_clicks проверки для предотвращения автовызовов
- Toast dismissal в session Store (не в БД) — сброс при новой сессии

**Референсы**:
- План: `.protocols/0014-onboarding-wizard/plan.md`
- Лог: `.protocols/0014-onboarding-wizard/log.md`
- Brief: `.design/brief.md`
- Solution v3: `.design/solution-v3.md`

---

### Протокол 0013: Safety Cushion (2026-01-30)
**Статус**: ✅ READY FOR REVIEW (PR #13)
**Батч**: Epic-04-Advanced Features (Batch 4, Safety Cushion)
**Worktree**: `/worktrees/0013-safety-cushion`

**Контекст**:
- В MVP планировщика бюджета отсутствует функционал финансовой подушки безопасности
- Резервный фонд для непредвиденных расходов — критичная часть финансового планирования
- Подушка НЕ является Goal (не участвует в распределении бюджета накоплений)

**Решения**:
- Подушка как 3 поля в User (не отдельная таблица) — простота для single-user MVP
- CushionService отдельный сервис с CRUD методами
- Percent NewType для type safety порогов
- Калькулятор сценариев для рекомендации размера подушки

**Реализация** (8 шагов):
1. **Schema + Model** (commit 12ed5a4)
   - TypedDicts: CushionSettings, CushionScenario (app/schema/cushion.py)
   - Percent NewType = int (0-100 range validation)
   - User модель: +cushion_target, +cushion_threshold_percent, +cushion_threshold_manual

2. **CushionService** (commit 560da11)
   - get_settings() — возвращает CushionSettings с вычисляемыми полями
   - update_settings() — обновление с валидацией
   - reset_settings() — сброс к default (target=0, threshold=30%)
   - calculate_recommendation() — расчет по сценариям (sum/max_scenario)
   - Константы: DEFAULT_THRESHOLD_PERCENT = 30, VALID_CALC_MODES

3. **Unit Tests** (commit 38a1817)
   - tests/test_cushion_service.py: 20 тестов
   - TestValidatePercent (5), TestGetSettings (7), TestUpdateSettings (3)
   - TestResetSettings (1), TestCalculateRecommendation (4)

4. **Card UI** (commit f36e0bb)
   - _build_cushion_card() — карточка на /goals (~180 строк)
   - Состояния: "Не настроена" / "Настроена"
   - Прогресс-бар с маркером порога риска
   - 4 цветовых статуса: danger/warning/info/success
   - dcc.Store: cushion-settings-store, cushion-refresh-trigger

5. **Modal UI** (commit 6a152ee)
   - _build_cushion_modal() — модал настройки (~175 строк)
   - Поля: cushion-target-input, cushion-threshold-input
   - Collapsible калькулятор сценариев
   - RadioItems режима расчёта (sum/max_scenario)
   - dcc.Store: cushion-scenarios-store, cushion-threshold-manual-flag

6. **Callbacks** (commit a31154c)
   - 12 callbacks (~450 строк):
     1. render_cushion_card — рендер из store
     2. load_cushion_settings — загрузка из БД
     3. open_cushion_modal, 4. close_cushion_modal
     5. populate_cushion_modal — заполнение при открытии
     6. mark_threshold_manual — флаг manual=True
     7. toggle_calculator — collapsible
     8. add_scenario — Pattern-Matching
     9. remove_scenario — Pattern-Matching
     10. calculate_recommendation — расчет
     11. apply_recommendation — применение к полю
     12. save_cushion_settings, 13. reset_cushion_settings
   - Все с ADR-003 guard clauses

7. **CSS** (commit 76c8f96)
   - Стили .cushion-* (~200 строк)
   - Варианты: .cushion-danger/warning/info/success
   - Прогресс: .cushion-progress-container, .cushion-threshold-marker
   - Responsive: breakpoints 768px, 576px

8. **Финализация** (commit fd5326f)
   - Black: OK
   - Flake8: 5 E501 исправлено
   - Pytest: 292 passed (было 272, +20 для CushionService)

**Результат**:
- +~1000 строк в goals.py (карточка + модал + callbacks)
- +~180 строк CushionService
- +20 unit тестов (292 всего)
- Percent NewType для type safety
- Калькулятор сценариев для рекомендации

**Критичные детали**:
- Percent NewType — type safety для порогов (0-100 validation)
- cushion_threshold_manual — фиксированная сумма порога (альтернатива процентам)
- Калькулятор сценариев: sum (сумма всех) vs max_scenario (максимальный)
- Прогресс = User.current_balance / cushion_target (требует актуализации баланса)
- Подушка НЕ Goal — не участвует в AllocationService распределении

**Следующие шаги** (протокол 0014):
- Календарная визуализация подушки (график пополнения)
- Умное распределение неосвоенного бюджета накоплений

**Референсы**:
- План: `.protocols/0013-safety-cushion/plan.md`
- Лог: `.protocols/0013-safety-cushion/log.md`
- Brief: `.design/brief.md`
- Solution v3: `.design/solution-v3.md`

---

### Протокол 0012: Quick-Add Chips (2026-01-25)
**Статус**: ✅ READY FOR REVIEW (PR #12)
**Батч**: Epic-04-Advanced Features (Batch 4, Quick-Add Chips)
**Worktree**: `/worktrees/0012-quick-add-chips`

**Контекст**:
- После Батча 3 создание операций требует 6 шагов
- Quick-add chips позволяют сократить процесс до 3-4 шагов
- Протокол A (hardcoded chips) как фундамент для Протокола B (кастомные шаблоны)

**Реализация** (8 шагов):
1. **Schema и константы** (commit ffb88d3)
   - TypedDict QuickAddChipData (category_id, name, icon, type)
   - DEFAULT_QUICK_ADD_CHIP_NAMES — 7 названий (5 expense + 2 income)
   - _get_quick_add_chips() — lookup по имени с warning

2. **UI секция Quick-add** (commit 76be290)
   - _build_quick_add_chip() — вертикальный layout (иконка + название)
   - _build_quick_add_section() — группировка expense/income + кнопки "Ещё"
   - Интеграция в transactions layout между header и фильтрами

3. **Модал "Ещё..."** (commit 2fdcaec)
   - _build_category_more_modal() — dbc.Modal с Tabs
   - load_more_modal_categories() callback — динамическая загрузка
   - Pattern-Matching ID: {"type": "qa-more-category", ...}

4. **Preselection механизм** (commit b500451)
   - dcc.Store: preselected-category, preselected-type
   - set_preselection_on_modal_open() — применение при открытии
   - create_transaction обновлен — reset preselection после создания

5. **Callbacks Quick-add** (commit 69f7837)
   - open_create_from_quick_add() — chip → modal с preselection
   - open_more_modal() — "Ещё..." → modal категорий
   - select_from_more_modal() — выбор → закрытие + открытие create
   - ADR-003 guard clauses во всех 3 callbacks

6. **CSS стили** (commit 0f1b945)
   - Стили .qa-* (~100 строк)
   - Вертикальный layout, hover transform, ellipsis
   - Responsive: horizontal scroll на 768px

7. **Unit тесты** (commit b325864)
   - test_quick_add_chips.py — 13 тестов
   - Покрытие: TypedDict, _get_quick_add_chips(), UI функции

8. **Финализация** (commit 55b334c)
   - Black: 1 файл OK
   - Flake8: 3 unused imports исправлены
   - Pytest: 272 passed

**Результат**:
- +~600 строк в transactions.py/transaction_modals.py
- +13 unit тестов (272 всего)
- Сокращение шагов создания операции: 6 → 3-4
- 7 hardcoded chips готовы к использованию

**Критичные детали**:
- Lookup по имени защищает от ID mismatch между dev/prod окружениями
- Preselection Store Pattern — чистая передача состояния между модалами
- Вертикальный layout чипов экономит горизонтальное пространство
- Pattern-Matching IDs масштабируются для будущих кастомных чипов

**Следующие шаги** (Протокол B):
- Кастомизация chips пользователем
- Частые операции → автоматические шаблоны
- Редактирование/удаление шаблонов

**Референсы**:
- План: `.protocols/0012-quick-add-chips/plan.md`
- Лог: `.protocols/0012-quick-add-chips/log.md`
- Спецификация: `.reports/epics/epic-04-advanced/spec-quick-add-chips.md`
- Design doc: `.design/solution-v3.md`

---

### Протокол 0011: Chips + Bulk + Export UI (2026-01-24)
**Статус**: ✅ MERGED (commit ac25b5d, PR #11)
**Батч**: Epic-03-Analytics (Batch 3.2)
**Worktree**: `/worktrees/0011-chips-bulk-export`

**Контекст**:
- Батч 3.2 был завершен ранее, но UI компоненты потеряны при merge
- Backend методы готовы: `bulk_update_category`, `export_to_csv`, `get_frequent_for_type`
- Требовалось восстановить Chips UI, Bulk actions, CSV export

**Реализация** (6 шагов):
1. **Layout + Helpers** (commit 1b2e3f5)
   - dcc.Store: selected-transactions, frequent-categories
   - dcc.Download: export-download
   - Helper: `_pluralize_operations()` — склонение "операция/операции/операций"
   - Helper: `_build_bulk_panel()` — sticky panel с dropdown

2. **Table + Chips** (commit ef16193)
   - Helper: `_build_chips_cell()` с guard для TRANSFER/ADJUSTMENT
   - Chips из frequent_categories[:5] + overflow dropdown
   - Checkboxes в таблице (select-all + individual)

3. **Chips Callbacks** (commit 1931a48)
   - `load_frequent_categories()` — кеширование через CategoryService
   - `chip_assign_category()` — Pattern-Matching с 3-уровневыми guard clauses (ADR-003)
   - `chip_dropdown_assign_category()` — аналогично для overflow dropdown

4. **Bulk Callbacks** (commit b89c954)
   - `update_selection_state()` — обработка Select All и checkboxes
   - `clear_selection_on_filter_change()` — WYSIWYG поведение
   - `toggle_bulk_panel()` — показ/скрытие с prevent_initial_call=True
   - `bulk_assign_category()` — ValidationError handling, emit trigger

5. **Export + Tests** (commit 240ca5e)
   - `export_transactions()` — filename pattern, UTF-8 BOM
   - tests/test_transactions_callbacks.py: 13 тестов для _pluralize_operations

6. **Финализация** (commit ea62f55)
   - Black: 65 файлов OK
   - Flake8: 0 ошибок
   - Pytest: 259 passed

**Результат**:
- +636 строк в transactions.py
- +81 строка в tests
- 13 новых unit тестов (все PASS)
- Полное восстановление UX функциональности Батча 3.2

**Критичные детали**:
- Pattern-Matching guard clauses (ADR-003) обязательны для chips и bulk callbacks
- TRANSFER/ADJUSTMENT не могут иметь категорию (guard в `_build_chips_cell`)
- Max 100 транзакций для bulk операций (лимит в TransactionService)
- UTF-8 BOM критичен для Excel совместимости экспорта

**Референсы**:
- План: `.protocols/0011-chips-bulk-export/plan.md`
- Лог: `.protocols/0011-chips-bulk-export/log.md`
- Design doc: `.design/solution-v2.md`

---

### Протокол 0010: Analytics & UX Improvements (2026-01-23)
**Статус**: ✅ MERGED (commit ed0fc44, PR #10)
**Батч**: Epic-03-Analytics (Batch 3.2)

**Реализация**:
- AnalyticsService (~290 строк)
- TransactionService: bulk_update_category, export_to_csv
- CategoryService: get_frequent_for_type
- Страница /analytics с donut/bar charts
- UI компоненты (потеряны при merge, восстановлены в протоколе 0011)

**Результат**:
- 246 unit тестов (было 213)
- Memory Bank обновлен

---

### Протокол 0009: Categories + Reconciliation (2026-01-23)
**Статус**: ✅ MERGED (commit merge PR #9)
**Батч**: Epic-03-Analytics (Batch 3.1)

**Реализация**:
- Category модель, TransactionType.ADJUSTMENT
- CategoryService, ReconciliationService
- Сверка баланса через модал
- 16 предустановленных категорий (seed idempotent)

**Результат**:
- 213 unit и integration тестов

---

### Протокол 0008: Redistribution (2026-01-22)
**Статус**: ✅ MERGED (PR #8)
**Батч**: Epic-02-EnhancedPlanning (Batch 2)

**Реализация**:
- RedistributionService с Temporary Status Pattern
- TypedDicts и Serializers для preview/event
- Redistribution Modal UI с анимациями

**Результат**: 23 новых теста

---

### Протокол 0007: Savings Modes (2026-01-22)
**Статус**: ✅ MERGED (PR #7)
**Батч**: Epic-02-EnhancedPlanning (Batch 2)

**Реализация**:
- User.savings_mode (free/medium/strict)
- Множители к monthly_contribution (1.0 / 1.15 / 1.5)
- UI селектор режимов

---

### Протокол 0006: Multiple Goals (2026-01-21)
**Статус**: ✅ MERGED (PR #6)
**Батч**: Epic-02-EnhancedPlanning (Batch 2)

**Реализация**:
- User.monthly_savings_budget
- AllocationService с жадным алгоритмом
- TypedDicts модуль (app/types/)
- Goals UI рефакторинг (~600 строк)

**Результат**: 98 unit и integration тестов

---

### Протокол 0005: Recurring Transactions (2026-01-20)
**Статус**: ✅ MERGED (PR #5)
**Батч**: Epic-02-EnhancedPlanning (Batch 2)

**Реализация**:
- RecurringService (~550 строк)
- Anchored-алгоритм генерации дат
- Wizard UI "экземпляр vs серия"

**Результат**: 75 unit тестов, ADR-004 создан

---

### Протокол 0004: Goals UI (2026-01-19)
**Статус**: ✅ MERGED (PR #4)
**Батч**: Epic-01-CoreMVP (Фаза 5)

**Реализация**:
- Utils модуль (app/utils/formatters.py)
- Goals UI (~1040 строк)
- 10 callbacks для CRUD

**Результат**: 37 unit тестов

---

### Протокол 0003: Dashboard Integration (2026-01-19)
**Статус**: ✅ MERGED (PR #3)
**Батч**: Epic-01-CoreMVP (Фаза 4)

**Реализация**:
- DashboardService (~290 строк)
- CalendarService расширен (get_balance_on_date, get_year_summary)
- Dashboard UI переписан (~685 строк)

**Результат**: 16 новых unit тестов (33 всего)

---

### Протокол 0002: Cash Calendar (2026-01-19)
**Статус**: ✅ MERGED (PR #2)
**Батч**: Epic-01-CoreMVP (Фаза 3)

**Реализация**:
- CalendarService (~310 строк)
- Calendar UI (~700 строк)
- 3 callbacks с guard clauses (ADR-003)

**Результат**: 15 unit тестов

---

## Паттерны протоколов

### Структура протокола
```
.protocols/NNNN-название/
├── plan.md          # High-level план (6 шагов)
├── log.md           # Журнал работы (append-only)
├── context.md       # Restore context записи
├── NN-название.md   # Детальный план каждого шага
└── ...
```

### Commit Convention
```
type(scope): description [protocol-NNNN/NN]

Примеры:
feat(transactions): add chips callbacks [protocol-0011/03]
chore(review): complete review steps 1-3 [protocol-0011/3-m]
docs(protocol): finalize 0011-chips-bulk-export [protocol-0011/06]
```

### Workflow
1. Создание worktree и ветки
2. Пошаговая реализация (6 шагов)
3. Code quality checks (black, flake8, pytest)
4. Finalize документации
5. PR создание и review
6. Merge в main

---

Детали: см. `CLAUDE.md` (Protocol Workflow section), `.protocols/_core/workflow.md`
