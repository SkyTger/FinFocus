# FinFocus - Архив прогресса разработки

Старые батчи, перенесённые из `feature_progress.md` по правилу Rolling Window
(в основном файле хранятся только последние 5 батчей).

---

## ✅ Батч 29: Заплатки-параллель — пять простых находок (2026-09-05)

**Режим**: без протокола, пять правок пятью субагентами в worktree, смержены
прямо в main (de5bb44, 66f65b1, 2118abc, b43c11d, 7235bf2)
**Статус**: ✅ Смержено в main

### 🎯 Цель:
Снять находки UX-аудита и живого использования, не требующие продуктового
обсуждения, — чтобы шаг 3 «сшивки» начинался с чистого списка мелочей.

### ✅ Сделано:
1. Единое имя кнопки «Сверка» (заголовок окна — «Сверка баланса»)
2. Сегодняшние операции — только в «Недавних» карточки «Операции»
   («Предстоящие» с завтра, дверь с тем же диапазоном)
3. 404-страница в стиле щитка (panel.css, кнопка «На главную»), 16 тестов
4. Годовой период повторения вместо квартального (29 февраля → 28-е);
   миграция не нужна
5. Тултип дня календаря не обрезается: причина — два `overflow: hidden`
   у сетки и тултип пятницы вправо; обрезки сняты, пятница — налево

### 📊 Результат:
- ✅ **928 тестов** (было 898, +30), black чист, flake8 — 3 pre-existing E501
- ⚠️ Живая проверка в браузере не делалась (404, тултипы Пт/Сб/Вс/Пн)
- ✅ Долг документации закрыт 2026/09/10 прогоном /kb-update

Файлы: `app/components/{dashboard,transaction_modals}.py`,
`app/services/{dashboard_service,panel_service,recurring_service}.py`,
`app/schema/panel.py`, `app/main.py`, `app/assets/calendar.css`,
`tests/test_{dashboard_service,panel_service,recurring_service,dashboard_panel_ui,display_page_404,calendar_tooltip_visual}.py`

→ ROADMAP.md: UX-аудит P2 «тултип», P2 «пустые состояния» (устарел),
P3 «Сверка», P3 «404» — закрыты; п.10: «годовое повторение», «дубли
сегодняшних операций» — закрыты. Детали — в архиве.

---

---

## ✅ Батч 28: Защита служебных операций в списке (2026-08-30)

**Протокол**: 0032-system-ops-guard (план «сшивка», шаг 2)
**PR**: https://github.com/SkyTger/FinFocus/pull/32 — смержено (2026/08/30, 62ac1df)

### 🎯 Цель:
Служебные операции (резерв на цели, взносы в цели, корректировки сверки)
в списке операций не должны выглядеть и вести себя как пользовательские
записи (удаление взноса ломает синхронизацию суммы цели).

### ✅ Сделано:
1. У служебных строк нет кнопок редактирования/удаления, чекбокса
   массового выделения и быстрых категорий; бейдж и подпись «(авто)»
2. Корректировки сверки: редактирование скрыто, удаление оставлено
   (откат — право пользователя)
3. Те же проверки продублированы на сервере (обработчики и сервисный слой)

### 📊 Результат:
- ✅ **898 тестов** (было 845, +53), независимое ревью без критичных находок
- 💡 Техдолг: список «некатегоризируемых» типов продублирован в двух местах кода

Файлы: `app/components/{transactions,transaction_modals}.py`,
`app/services/transaction_service.py`, `tests/test_transactions_system_ops.py`,
`tests/test_transaction_service.py`

→ ROADMAP.md: «сшивка» шаг 2 — закрыт; UX-аудит P2 «служебные операции
смешаны с пользовательскими» — закрыт

---

## ✅ Батч 27: Тесты визуального слоя полоски — долг куска 3 (2026-08-30)

Закрыта тестовая часть долга протокола 0031: 20 якорных тестов по
тексту `nav_rail.css` (`tests/test_nav_rail_visual.py`) — геометрия и
цепочка CSS-переменных, единственность правила видимости `:empty`
(включая AST-проверку, что видимостью не управляет Python), язычки и
отсутствие обрезки у кожуха, разворот (fill-mode backwards,
reduced-motion снимает анимацию целиком), существование всех
заимствованных токенов. Сам факт проигрывания анимации по-прежнему
подтверждается только живой приёмкой — браузерных зависимостей в
проекте нет осознанно. 845 тестов (было 825).
Файлы: `tests/test_nav_rail_visual.py`, `tests/test_nav_rail.py` (докстринг)
→ Ветка test/0031-nav-rail-visual-debt; ROADMAP: долг куска 3 (тесты) — закрыт,
заведён план «сшивка разделов со щитком» (5 шагов)

---

## ✅ Батч 26: Щиток — полоска-меню вместо сайдбара (2026-08-30)

**Дата**: 2026/08/30
**Протокол**: 0031-nav-rail (Epic-11, кусок 3 из 3)
**PR**: https://github.com/SkyTger/FinFocus/pull/31 — смержено
**Статус**: ✅ Смержено (2026/08/30, f504fa8)

### 🎯 Цель батча:
Третий и последний кусок редизайна «щиток»: широкий сайдбар (228px)
на четырёх экранах заменяется узкой полоской иконок (60px).
Содержимому возвращается 228px ширины, а дублирование дверей щитка
уходит.

### ✅ Выполненные задачи:
1. **Гипотеза проверена ДО реализации**: живая проба на приложении
   в двух режимах показала, что браузер переиспользует узел меню при
   переходах между разделами. На этом стоит вся анимация разворота —
   без пробы это была бы догадка
2. **Единый источник версии** (`app/version.py`): константа в модуле
   кода — единственный способ, переживающий сборку в самостоятельный
   исполняемый файл. Версия показывается в окне профиля и сверяется
   с git-тегом тестом
3. **Полоска-меню** (`nav_rail.py` + `nav_rail.css`): знак-домик на
   дашборд, четыре раздела иконками, аватар входом в профиль, подписи
   язычком при наведении. Ноль колбэков, ноль обращений к базе —
   устройство унаследовано от куска 2
4. **Разворот при входе с дашборда**: чистая CSS-анимация на
   появлении элемента, без единой строки JS. Не переигрывается при
   переходах между разделами — проверено живьём счётчиком
5. **Прежний сайдбар свёрнут**: файл сохранён как «надгробие» с одной
   константой под будущие маршруты (решение владельца), стили и его
   тесты удалены

### 📊 Результат:
- ✅ **825 тестов** (было 766): +43 новый регрессионный якорь
  навигации, +7 источник версии, +5 по итогам живой приёмки,
  −8 удалённых вместе с сайдбаром, +13 добавлено на ревью
- ✅ Живая приёмка всех критериев в браузере + **запуск собранного
  бандла**: версия во frozen-режиме читается верно
- ✅ flake8 без новых замечаний, black чист

### 💡 Ключевые решения:
1. **Носитель идентичности элемента — его имя, а не служебный проп
   `key`**: в этой версии Dash ключ берётся именно из имени, а `key`
   до сопоставления вообще не доходит
2. **Доступное имя ссылок через `title`**: компонент ссылки Dash не
   принимает aria-атрибуты (падает при построении), а замена на
   обычную ссылку сломала бы переиспользование узла. Цена компромисса
   названа явно
3. **Анимируется содержимое, а не плашка** — отступление от
   раскадровки эскиза, решение владельца: подписи важнее буквального
   роста плашки

### 🔍 Найдено живым чек-листом и исправлено:
- **Иконка раздела «Цели» не существовала** в наборе Bootstrap Icons —
  глиф не отрисовывался, слот выглядел пустым кружком. Имя досталось
  по наследству от сайдбара, где дефект скрывала подпись рядом (это и
  есть пункт аудита «у пункта Цели нет иконки»). Заменено, добавлен
  тест-якорь на известные несуществующие имена
- **Аватар выпадал из обхода по клавише Tab**: это не ссылка и не
  кнопка, поэтому без явного указания в обход не попадал — в окно
  профиля нельзя было попасть с клавиатуры вообще. Исправлено,
  Enter и Space теперь работают

### ⚠️ Попутно (вне scope):
Починен тест тултипа платежей, падавший в последние дни месяца:
фикстура кладёт платежи на «сегодня + 2/+4», а тултип отсекает по
концу месяца. Тот же класс, что открытый вопрос №6 ROADMAP, но в
форме падения, а не тихого пропуска.

Файлы: `app/version.py`, `app/__init__.py`, `app/components/nav_rail.py`,
`app/components/sidebar.py`, `app/components/profile_modal.py`,
`app/main.py`, `app/assets/{nav_rail.css,nav_rail_keyboard.js,custom.css,calendar.css,clientside_triggers.js}`,
`tests/test_nav_rail.py`, `tests/test_version.py`,
`tests/test_profile_modal_callbacks.py`, `tests/test_dashboard_panel_ui.py`

### 🔍 Итоги ревью (2026-08-30):

Независимое code review субагентом вне контекста реализации —
**критичных и важных находок нет**: все четыре унаследованных правила
устройства навигации соблюдены и закреплены тестами, а не только
комментариями. Проверка осмысленности тестов намеренной порчей кода —
5 из 5 порч пойманы адресными тестами.

**Сверка итога с замыслом** (независимый верификатор, смотревший на
код, но не на отчёт исполнителя): из 26 требований спецификации
**ни одного невыполненного**; пять расхождений «сделано иначе», из них
четыре — заранее принятые решения владельца или обход ограничений
библиотеки, задокументированные прямо в коде.

**Найдено и исправлено на ревью**: проверка входа в окно профиля с
аватара выполнялась только на одном разделе, тогда как критерий
приёмки прямо требует проверки на каждом — при том что соседние
проверки в том же файле уже шли по всем разделам. Похоже на
недосмотр: если бы аватар пропал на одном конкретном разделе, тесты
этого не заметили бы. Исправлено, осмысленность подтверждена порчей.

**Зафиксирован долг куска 3** (не блокер мержа): визуальный слой
полоски — сам разворот, язычки подписей, геометрия — тестами не
покрыт и проверялся только вживую. Это тот же вид долга, который в
куске 1 пришлось закрывать отдельным протоколом; здесь он создан
осознанно. Туда же: производительность отрисовки не замерена (в куске
2 замеряли), и для незрячих пользователей активный раздел неотличим
от остальных — следствие ограничения библиотеки, обойти которое можно
только сломав навигацию.

→ ROADMAP.md, Epic-11: кусок 3 — выполнен; P1 «Настройки → 404» и
P3 «зашитая v1.0.0», «у пункта Цели нет иконки» — закрыты

---

## ✅ Батч 25: Щиток — карточки-двери (2026-08-26)

**Дата**: 2026/08/26
**Протокол**: 0030-panel-doors (Epic-11, кусок 2 из 3)
**PR**: https://github.com/SkyTger/FinFocus/pull/30 — смержено
**Статус**: ✅ Смержено (2026/08/26, 33c8a11)

### 🎯 Цель батча:
Второй кусок редизайна «щиток»: дашборд становится навигацией —
под шапкой и графиком куска 1 появляются пять карточек-дверей
(Календарь, Цели, Операции, Аналитика, Wishlist-полоса), сайдбар
снимается с дашборда, все двери ведут в разделы с контекстом.

### ✅ Выполненные задачи:
1. **Контракты** (`app/schema/panel.py`): CardStatus (OK/EMPTY/FAILED —
   единственный источник правды отрисовки), срезы пяти карточек,
   PanelData без общего признака пустоты, TRANSACTION_KIND_MAP
   (6 типов → 3 kind)
2. **Композитор** (`DashboardPanelService`): один сбор PanelData за
   одну сессию (на пути сборки щитка было 3), поблочная деградация с
   `logger.opt(exception=True)`, контракт материализации ORM, контракт
   `_empty_*` (нейтральные значения без текстов и нулей)
3. **Карточки-двери** (`panel_cards.py` + panel.css секции 7-10):
   чистые build-функции, ни одного серверного Input (двери — dcc.Link,
   Wishlist — clientside → Store); Календарь — ДВА окошка + маркер
   просадки (усиление — факт знака, без порога); подушка — строкой в
   Целях (AC-4); Аналитика — только расходы + объявленное расхождение
   с графиком; Операции — только материализованные (решение владельца)
4. **Сайдбар — Подход B**: снят с дашборда (`render_sidebar_slot` в
   main.py, `[]` без сессии), оба колбэка сайдбара удалены,
   `create_sidebar(pathname, profile)` — чистая функция; вход профиля —
   ТОЛЬКО Store open-profile-trigger (шестерёнка + аватар через
   clientside); колонку скрывает одно CSS-правило `:empty`
5. **Переходы с контекстом** (FR-3): `handle_panel_query_params` +
   `_OWNED_SEARCH_PATHS` (владение url.search; /transactions не
   трогаем — фильтр 0023); приёмники `?focus_date=` (календарь,
   подсветка дня) и `?goal=` (цели, скролл к карточке) с единой
   идемпотентностью {"value","ts"}
6. **Снято**: split-таблицы, readonly-подушка, wishlist-виджет,
   `_build_empty_state`, раскладка 8/4 (custom.css), 2 clientside-
   триггера удалённых кнопок

### 📊 Результат:
- ✅ **766 тестов** (было 693: +19 композитор, +51 UI/сайдбар/params,
  +1 адаптация, +1 добавлен на ревью), mutation smoke 5/5 пойманы
  после усиления фикстуры
- ✅ Замер NFR-1: композитор ~20 мс / 21 SQL (бюджет 2 с);
  get_money_layers — 1 вызов на рендер; сайдбар на переходе ~1 мс
- ✅ Ручная проверка в живом браузере: оба входа профиля со всех
  страниц, все двери с контекстом, F5 сохраняет фильтр периода,
  фокус не переприменяется при возврате по меню
- ✅ 47 тестов куска 1 зелёные без правок; black чист; flake8 — новых
  замечаний нет (замечаний стало 4 вместо 6: две E501-строки ушли
  вместе с удалёнными split-таблицами)

### 💡 Ключевые решения:
1. **Окошко «вчера» убрано** (владелец, 2026-08-26) — отступление от
   FR-1.a спеки: расчёт «вчера» три итерации проектирования порождал
   тихие дефекты; `MoneyLayersService` куском 2 не тронут вообще
2. **Дефект, пойманный ручной проверкой**: нераспознанные параметры
   писали None в Store'ы → второй рендер календаря гасил фокус;
   исправлено на no_update, зафиксировано тестом и в patterns
3. **Уроки в knowledge-bank** (`patterns/services.md`): два вопроса к
   оконному хелперу; проверка `__init__` перед передачей сессии

### 🔍 Итоги ревью (2026-08-26):
Code review независимым субагентом (вне контекста реализации) —
критичных и важных находок нет: правило проекта про динамические
элементы не нарушено ни одним новым колбэком, чтение данных из базы
после закрытия сессии организовано аккуратно, цифры карточек питаются
общей моделью слоёв куска 1, инъекций нет, слои приложения не смешаны,
мёртвый код убран полностью. Три минорных замечания приняты как есть —
в долг куска 2, не блокеры: (а) вспомогательный приём в одном из тестов
проверяет чтение данных слабее, чем заявлено в его описании, хотя
реальное поведение корректно; (б) один экзотический вручную собранный
адрес перехода с двумя параметрами фокуса сразу может применить только
один из них — обычные двери такой адрес не формируют; (в) для лимита
показа покупок в полосе на дашборде нет отдельно вынесенной именованной
константы.

**Найдено на ревью и исправлено**: карточка «Отложенные покупки» —
двухуровневая дверь (клик по всей полосе открывает окно управления
списком, клик по конкретной покупке ведёт в календарь с фокусом на
ней). Кликабельной была вся полоса целиком, а ссылки покупок лежали
внутри неё — из-за этого клик по покупке срабатывал одновременно на
обоих уровнях: уводил в календарь и одновременно открывал окно
управления поверх него, нарушая один из критериев приёмки. Дефект
предсказан по коду при сверке итога со спекой и подтверждён вживую в
браузере. Исправлено разделением на слои: кликабельная зона полосы
стала отдельным невидимым слоем-подложкой, а ссылки покупок подняты
над ним — клику по покупке больше некуда всплывать на уровень полосы.
Проверено настоящими кликами мыши: клик по покупке — только календарь,
клик по пустому месту полосы — только окно управления. Добавлен
целевой тест (766-й), осмысленность подтверждена порчей кода. Правило
записано в knowledge-bank.

Файлы: `app/schema/panel.py`, `app/services/panel_service.py`,
`app/components/panel_cards.py`, `app/components/dashboard.py`,
`app/components/sidebar.py`, `app/components/wishlist.py`,
`app/components/profile_modal.py`, `app/components/calendar.py`,
`app/components/goals.py`, `app/main.py`, `app/assets/{panel,sidebar,custom,calendar,goals}.css`,
`app/assets/clientside_triggers.js`, `tests/test_panel_*.py`,
`tests/test_sidebar.py`

→ ROADMAP.md, Epic-11: кусок 2 — выполнен (с зафиксированным
отступлением от FR-1.a)

---

## ✅ Батч 24: Долги куска 1 — savings в базе календаря + тесты щитка (2026-08-25)

**Дата**: 2026/08/25
**Протокол**: 0029-panel-debts (Epic-11, долги куска 1)
**PR**: https://github.com/SkyTger/FinFocus/pull/29 — смержено (2026-08-25, 0b3cec5)
**Статус**: ✅ Смержено

### 🎯 Цель батча:
Закрыть два хвоста, зафиксированных при мерже протокола 0028, до начала
куска 2 (карточки-двери): (1) багфикс кассового календаря, снимающий
«Известное ограничение куска 1» Epic-11 (кандидат №1 в ROADMAP);
(2) тестовый долг визуального слоя щитка (шапка, график, легенда,
тултипы, ось), покрытый только вручную.

### ✅ Выполненные задачи:
1. **Багфикс savings в базе остатка календаря** — дефект оказался
   двухслойным: `_calculate_recurring_before_date` суммировал только
   income/expense (игнорировал savings-типы), а выборка recurring-
   инстансов шла по `original_date`, тогда как раскладка — по
   фактической дате, из-за чего exception, перенесённый через границу
   окна расчёта, терялся из баланса целиком (в обе стороны переноса,
   для любого типа операции). Оба метода (`_calculate_recurring_before_date`,
   `_get_recurring_daily_changes`) переведены на фильтрацию по
   фактической дате инстанса, выборки расширены (366 дней вправо/влево)
2. **Снято известное ограничение куска 1**: savings-операция,
   перенесённая с прошедшей даты, больше не завышает «Свободно
   сегодня». Докстринги MoneyLayersService актуализированы
3. **47 unit-тестов визуального слоя щитка** (`tests/test_dashboard_panel_ui.py`,
   4 класса) — без БД, на фикстурах-словарях и относительных датах.
   Формализованы три ручных критерия приёмки протокола 0028: AC-1
   (цифра шапки == free среза «сегодня»), AC-4 (тултип «Платежи» —
   конкретные операции с датами), AC-5 (пустые состояния без числовых
   артефактов)
4. **Побочная находка и фикс**: `_axis_tickvals` пробивал собственный
   потолок MAX_X_TICKS на окне длиной, кратной 11 (в проде латентно —
   окно щитка всегда 45 дней); правый край подписей теперь заменяет
   последнюю подпись сетки вместо добавления сверх потолка

### 📊 Результат:
- ✅ **693 теста** (было 639: +7 регрессионных календаря, +47 щитка)
- ✅ Mutation-проверки: 3 порчи фикса календаря + 3 порчи build-функций
  щитка — все пойманы адресными тестами
- ✅ flake8 без новых замечаний (те же 6 pre-existing E501); bandit —
  0 findings по трём изменённым файлам
- ✅ Независимое code review (субагент вне контекста реализации) —
  критичных проблем нет

### 💡 Ключевые решения:
1. **Минимальный фикс отвергнут расчётом**: «только добавить savings
   в total» на кейсе переноса давал двойной счёт со слоем «Платежи»
   и занижение «Свободно» на днях до фактической даты — понадобилась
   фильтрация по фактической дате в обоих методах, а не точечная правка
2. **Остаточное ограничение оставлено осознанно**: exception с
   `original_date` дальше 366 дней от границы расчёта невидим —
   чинится только правкой выборки exceptions в RecurringService
   (по двум датам), вне scope протокола
3. **`_get_recurring_totals_for_period` (сводки месяца/года)** от
   переносов через границы всё ещё страдает — это отображение сводки,
   не баланс щитка; вне scope, кандидат в пул заплаток

Файлы: `app/services/calendar_service.py`, `app/services/money_layers_service.py`,
`app/components/dashboard.py`, `tests/test_calendar_service.py`,
`tests/test_money_layers_service.py`, `tests/test_dashboard_panel_ui.py`

→ ROADMAP.md, Epic-11: «Известное ограничение куска 1» и «Долг куска 1» — закрыты

---

## ✅ Батч 23: Щиток — модель слоёв, шапка и график полос (2026-08-24)

**Дата**: 2026/08/24
**Протокол**: 0028-money-layers-panel (Epic-11, кусок 1 из 3)
**PR**: https://github.com/SkyTger/FinFocus/pull/28 — смержено
**Статус**: ✅ Смержено (2026/08/25, a6e566a)

### 🎯 Цель батча:
Первый кусок редизайна «щиток»: дать дашборду единую модель денег
и заменить ей ряд KPI-карточек с графиком доходы/расходы. Главный
дефект, который чинится, — цифры соседних карточек противоречили
друг другу на глаз (UX-аудит 2026-08-20), потому что каждая считала
своё своим способом.

### ✅ Выполненные задачи:
1. **Модель «свободно / платежи / резерв»** — новый сервис-надстройка
   раскладывает прогнозный остаток каждого дня на три слоя единой
   формулой от даты. Сумма слоёв равна остатку кассового календаря
   по построению, поэтому шапка и график разойтись не могут
2. **Формула резерва без ветвления по режиму** — самая тонкая часть.
   Две предыдущие версии решения здесь ошибались, причём инвариант
   суммы дефект не ловил. Проверена вручную на всех 12 кейсах
   численной трассировки решения
3. **Шапка «Свободно сегодня»** с разбором «баланс − платежи − резерв»,
   аватаром, кнопкой сверки и шестерёнкой (второй вход в профиль)
4. **График полос** на 45 дней: стопка трёх слоёв, вехи целей, линия
   «сегодня», маркер минимума, HTML-легенда с тултипами-пояснениями
5. **Снято**: ряд из 4 KPI-карточек, график доходы/расходы + баланс,
   переключатель Месяц/Год, приветствие, карточка статистики,
   10 функций мёртвого кода, 153 строки осиротевшего CSS

### 📊 Результат:
- ✅ **639 тестов** (632 по протоколу + 7 добавленных на ревью), flake8 без
  новых замечаний
- ✅ Тесты проверяют раскладку по слоям, а не только сумму: прогон
  5 намеренных порч формулы и каскада — все пойманы
- ✅ Рендер щитка на 120 операциях — 13 мс при пороге 2 секунды;
  один расчёт балансов и один сбор операций за рендер

### 💡 Ключевые решения:
1. **Вердикта нет** (решение владельца): ни чипа «всё в порядке»,
   ни окраски суммы по уровню — любой порог просадки произволен,
   проблемные дни видны на самом графике
2. **Тултип резерва говорит факт дня, а не настройку**: если остатка
   меньше, чем настроено, он так и пишет — «остаётся 18 000 из 30 000,
   вы залезаете в подушку»
3. **Подушка входит в резерв порогом, а не полной целью** — иначе
   «Свободно» залипало бы на нуле у всех, кто ещё не накопил

### ⚠️ Остающееся ограничение:
Снято протоколом 0029 (см. Батч 24). На момент завершения этого
батча: операция взноса, перенесённая внутри текущего месяца с
прошедшей даты, завышала «Свободно» — давний дефект расчёта остатка
до начала периода в кассовом календаре, не в scope протокола 0028.

### 🔍 Найдено и исправлено на ревью (шаг 3.5-m-fix):
**Регрессия за пределами scope протокола**: шестерёнка щитка была
подключена к окну профиля напрямую. Элемент существует только на
дашборде, а браузерная часть Dash при отсутствии одного из источников
молча перестаёт отправлять запрос целиком — из-за этого перестал
работать и второй вход, аватар в сайдбаре, на всех остальных
страницах. Ошибки в консоли при этом нет, кнопка просто мёртвая.

Подтверждено сравнением с main: там тот же клик уходит на сервер и
открывает окно, на ветке протокола — ноль запросов. Переведено на
паттерн проекта для динамических элементов (Store-триггер +
clientside), который в этом же файле уже применён к соседней кнопке
«Сверка». Попутно закрыт побочный дефект: Store сохраняет значение
между переходами, из-за чего окно профиля стало всплывать при каждой
загрузке страницы — добавлена защита от пустого триггера.

Покрыто 7 тестами (контракт входов + поведение защиты), осмысленность
подтверждена порчей кода. Урок записан в knowledge-bank
(`patterns/callbacks.md`) — это повторение случая, который проект уже
чинил протоколом 0026.

Файлы: `app/schema/money_layers.py`, `app/services/money_layers_service.py`,
`app/components/dashboard.py`, `app/assets/panel.css`,
`app/components/profile_modal.py`, `app/services/cushion_service.py`,
`app/main.py`, `tests/test_money_layers_service.py`,
`tests/test_profile_modal_callbacks.py`

---

## ✅ Epic-05-UI: Dashboard UI Redesign — COMPLETED

**Дата старта**: 2026/02/05
**Дата завершения**: 2026/02/06
**Спецификация**: `.reports/epics/epic-05-ui/dashboard_ui_spec.md`
**План**: `.reports/epics/epic-05-ui/plan.md`

### Цель:
Переделка Dashboard по новой UI/UX спецификации — дневной график кассового календаря, обновлённые KPI-карточки, формат денег ₽, split таблиц операций.

### Батчи:
- ✅ Батч 5.1: Фундамент (цвета + формат ₽ + KPI) — завершён 2026/02/06, PR #21
- ✅ Батч 5.2: Дневной график (ядро) — завершён 2026/02/06, PR #22
- ✅ Батч 5.3: Layout (операции + правая колонна + sidebar) — завершён 2026/02/06, PR #23

### Ключевые решения:
1. Тёмная тема — откладывается (Epic-06)
2. Формат денег — глобальная замена $ → ₽ (DONE)
3. Дневной график — отдельный метод (не через CalendarService)
4. AI Assistant/Exchange — скрыты (TODO Epic-08)
5. Сайдбар — обернуть в dbc.Card (без рефакторинга main.py)
6. Адаптивность — desktop-first

---

## ✅ Батч 16: Dashboard UI Foundation (2026-02-06) — MERGED

**Дата**: 2026/02/06
**Протокол**: 0021-dashboard-foundation
**PR**: https://github.com/SkyTger/FinFocus/pull/21
**Статус**: ✅ Merged в main

### 🎯 Цель батча:
Обновить цветовую схему, глобальный форматтер денег ($ → ₽), переделать KPI-карточки без градиентов, скрыть AI/Exchange — фундамент для Epic-05-UI Dashboard Redesign.

### ✅ Выполненные задачи:

1. **format_rub() в formatters.py** (Step 01)
   - Глобальный форматтер: Decimal/float/int/None → "X XXX ₽"
   - show_sign: True → "+X XXX ₽" / "−X XXX ₽"
   - MINUS_SIGN константа: U+2212 (типографский минус)
   - .00 копейки скрываются (15000 → "15 000 ₽")
   - format_amount() переопределён как alias → 28 callsites покрыты
   - 10 unit тестов

2. **CSS-переменные + типографика** (Step 02)
   - 15 новых CSS-переменных (палитра #2ecc71, текст, фон, границы)
   - Deprecated aliases --primary-green, --light-green для обратной совместимости
   - 9 типографических классов (kpi-number/title/subtitle, table-amount, link-show-all)
   - custom.css: 7 замен hardcoded цветов
   - calendar.css: 6 замен (#28a745 → var(--color-primary/-dark))
   - transactions.css: 2 замены
   - onboarding.css: 3 замены

3. **Dashboard.py переработка** (Step 03)
   - create_metric_card() → _build_kpi_card() (белый фон, border, kpi-* классы)
   - 12 inline замен на format_rub() (KPI values, cashflow text, transaction amounts)
   - Кнопка "Сверка" на Total Balance → /calendar?open_recon=1
   - Русские label: Overview→Обзор, Income→Доходы, Expense→Расходы
   - AI Assistant и Exchange скрыты (TODO Epic-08)
   - table-amount.positive/.negative классы для транзакций

4. **Calendar.py обновления** (Step 04)
   - format_balance() рефакторинг: внутри format_rub(), возвращает с символом ₽
   - 4 callsite обновлены (убран ручной "₽")
   - Stats cards: income show_sign=True, expense → format_rub(-amount)
   - Tooltip balance + 5 amount строк → format_rub()
   - Reconciliation: 2 expected, 1 diff, 2 adjustment → format_rub()
   - 2 теста обновлены: "-3 000" → "−" + "3 000" (типографский минус)

5. **Analytics.py обновления** (Step 05)
   - 2 inline замены: donut center annotation + total H4 → format_rub()

6. **Финализация** (Step 06)
   - Black: 0 changes (all clean)
   - Flake8: 0 errors
   - Pytest: 492 passed (было 483, +10 новых, +1 updated)
   - 1 pre-existing failure: test_budget_change_updates_allocation (precision)

### 📊 Результат:
- ✅ 492 unit и integration тестов (было 483, +10 новых для format_rub)
- ✅ Глобальный формат денег X XXX ₽ (28 callsites format_amount + 12 dashboard + 11 calendar + 2 analytics)
- ✅ 15 CSS-переменных палитры #2ecc71
- ✅ 9 типографических классов
- ✅ KPI-карточки без градиентов (белый фон, border)
- ✅ AI/Exchange скрыты (TODO Epic-08)
- ✅ Black + Flake8 OK
- ✅ PR #21 Merged

### 💡 Ключевые решения:

1. **format_amount() как alias** — 28 существующих callsites покрыты без изменений (обратная совместимость)
2. **MINUS_SIGN константа** — U+2212 (типографский минус) вместо ASCII "-" (0x2D)
3. **Deprecated CSS aliases** — --primary-green, --light-green для legacy code (warnings)
4. **format_balance() внутри format_rub()** — календарь теперь единообразный (4 callsites обновлены)
5. **AI/Exchange скрыты, не удалены** — код сохранён для Epic-08

### 🔧 Технические детали:

**Модифицированные файлы:**
- `app/utils/formatters.py` — format_rub() + MINUS_SIGN
- `app/assets/custom.css` — 15 CSS-переменных + 9 типографических классов
- `app/assets/calendar.css` — 6 замен цветов
- `app/assets/transactions.css` — 2 замены
- `app/assets/onboarding.css` — 3 замены
- `app/components/dashboard.py` — _build_kpi_card(), 12 format_rub(), AI/Exchange скрыты
- `app/components/calendar.py` — format_balance() рефакторинг, 11 format_rub()
- `app/components/analytics.py` — 2 inline замены
- `tests/test_formatters.py` — 10 unit тестов
- `tests/test_calendar_service.py` — 2 теста обновлены (типографский минус)

### 🚀 Следующие шаги:

**Батч 5.2: Дневной график (ядро)**:
- DashboardService.get_daily_cashflow() — дневные данные
- Plotly: grouped bars + линия баланса + маркер минимума
- Hover tooltip, клик → модал, переключатель Month/Year

---

## ✅ Батч 17: Daily & Yearly Cashflow Chart (2026-02-06) — MERGED

**Дата**: 2026/02/06
**Протокол**: 0022-daily-cashflow-chart
**PR**: https://github.com/SkyTger/FinFocus/pull/22
**Статус**: ✅ Merged в main (commit 0ca4227)

### 🎯 Цель батча:
Реализовать дневной и годовой график кассового календаря на Dashboard с grouped bars (доход/расход), линией баланса, маркером минимума, интерактивными hover tooltip и клик-to-create для операций.

### ✅ Выполненные задачи:

1. **Schema + CalendarService** (commit e9ce06d)
   - 8 TypedDicts: BalanceStatus, DailyCashflow, DailyBalancePoint, MonthlyCashflowData, MonthlyCashflow, YearlyCashflowData
   - 4 константы: BALANCE_RISK/ATTENTION_THRESHOLD (0, 5000), STATUS_COLORS (ok/attention/risk)
   - CalendarService.get_recurring_income_expense_by_day() — публичный API для recurring интеграции
   - Экспорты в schema/__init__.py и services/__init__.py

2. **DashboardService расширение** (commit 2c75a77)
   - get_daily_cashflow() — merge regular + recurring, running balance, min marker → MonthlyCashflowData
   - get_yearly_cashflow() — оптимизация: один calculate_daily_balances(Jan 1, Dec 31) вместо 12x
   - _classify_balance_status() helper — ok/attention/risk по порогам
   - _get_daily_income_expense() — SQL CASE для INCOME/EXPENSE/SAVINGS/ADJUSTMENT, GROUP BY date
   - _get_monthly_income_expense() — переиспользует _get_daily_income_expense()
   - ADJUSTMENT handling: amount > 0 → income, amount < 0 → expense

3. **Unit тесты** (commit 69a7d51)
   - 16 новых тестов (12 daily + 4 yearly)
   - Покрытие: basic, no_txn, risk/attention/ok, min_position, cumulative, ADJUSTMENT +/-, TRANSFER, SAVINGS types
   - Всего: 508 тестов (было 492, +16)

4. **Charts + Callbacks** (commit 2c75a77)
   - _build_daily_cashflow_chart() — grouped bars (income/expense) + balance line (yaxis2) + diamond marker + today dashed line
   - _build_yearly_cashflow_chart() — end-of-month balances + current month highlight rect
   - _load_dashboard_components() helper — единая точка загрузки для обоих режимов (устраняет дублирование)
   - open_create_from_chart callback — клик на bar → create-modal с preselected-date (month mode only)
   - Dual Y-axis pattern для bars vs balance line (разные масштабы)
   - hovermode="x unified" с format_rub() в customdata
   - transaction_modals.py: source="chart" → set preselected-date

5. **Финализация** (commit ba0e448)
   - Black: 3 файла переформатированы
   - Flake8: 2 ошибки исправлены (F841, F401)
   - Pytest: 508 passed (1 deselected pre-existing precision issue)
   - Code review: PASS (no blockers, 16 unit tests, all planned items implemented)
   - Knowledge Bank update: 5 файлов обновлены, 2 новых (plotly-charts, callbacks patterns)

### 📊 Результат:
- ✅ 508 unit и integration тестов (было 492, +16 для daily/yearly cashflow)
- ✅ Дневной график с grouped bars + balance line + diamond min marker + today line
- ✅ Годовой график с end-of-month balances + current month highlight
- ✅ Клик на bar → create-modal с preselected date (Month mode)
- ✅ Dual Y-axis pattern для разных масштабов
- ✅ Unified hover tooltip с format_rub()
- ✅ _load_dashboard_components() helper (устраняет 80% дублирования)
- ✅ CalendarService.get_recurring_income_expense_by_day() публичный API
- ✅ Black + Flake8 OK
- ✅ PR #22 Merged

### 💡 Ключевые решения:

1. **Дневной vs годовой режим** — единый Chart ID, переключение через store {period, year, month}
2. **Year mode оптимизация** — один calculate_daily_balances() для всех 365 дней вместо 12x месячных
3. **Recurring через публичный API** — CalendarService.get_recurring_income_expense_by_day() вместо прямого вызова protected метода
4. **Dual Y-axis** — bars на первой оси, balance line на второй (разные масштабы)
5. **ADJUSTMENT классификация** — positive → income, negative → expense(abs) (осознанное решение)
6. **Protect method access** — _get_recurring_totals_for_period в Year mode (допустимо, тот же слой сервисов)

### 🔧 Технические детали:

**Новые файлы:**
- `app/schema/dashboard.py` — 8 TypedDicts (~104 строк)
- `tests/test_dashboard_service.py` — 16 unit тестов (~347 строк)

**Модифицированные файлы:**
- `app/components/dashboard.py` — +520 строк (chart builders, callbacks, helper)
- `app/services/dashboard_service.py` — +320 строк (get_daily/yearly_cashflow, helpers)
- `app/services/calendar_service.py` — +42 строк (get_recurring_income_expense_by_day)
- `app/components/transaction_modals.py` — +12 строк (source="chart" preselection)
- `app/schema/__init__.py`, `app/services/__init__.py` — экспорты

### 🚀 Следующие шаги:

**Epic-06: Dark Theme**:
- Тёмная тема по спецификации dashboard_ui_spec.md секция 2

**Epic-07: Mobile Responsive**:
- Полная адаптивность < 576px

---

## ✅ Батч 18: Dashboard Layout Redesign (2026-02-06) — MERGED

**Дата**: 2026/02/06
**Протокол**: 0023-dashboard-layout
**PR**: https://github.com/SkyTger/FinFocus/pull/23
**Статус**: ✅ Merged в main (commit a0ece8c + b4e6000)

### 🎯 Цель батча:
Финальная перестройка Dashboard layout: split таблиц операций 50/50, правая колонна с Wishlist + Cushion, sidebar в card, глобализация reconciliation modal, пустые состояния.

### ✅ Выполненные задачи:

1. **Formatters + DashboardService** (Step 01)
   - format_date_human() — "5 февраля" для операций
   - MONTH_NAMES_RU_GENITIVE константа
   - is_recurring_instance: bool в RecentTransaction TypedDict
   - get_recent_transactions() рефакторинг: reference_date параметр, month range filter (1-го числа..reference_date)
   - get_upcoming_transactions() NEW: операции после reference_date, ASC sort
   - _map_transactions() helper для устранения дублирования
   - 12 unit тестов: 3 formatter + 3 recent refactor + 6 upcoming
   - 57 тестов DashboardService (13 старых + 44 новых)

2. **Reconciliation глобализация** (Step 02)
   - calendar.py: удалён calendar-refresh-trigger, удалён create_reconciliation_modal() из layout
   - calendar.py: apply_reconciliation() Output global-transaction-trigger (allow_duplicate), return data с source/action
   - main.py: create_reconciliation_modal() перенесён в app.layout после wishlist modal
   - dashboard.py: KPI recon_button dcc.Link→dbc.Button(id="open-recon-from-dashboard-btn")
   - dashboard.py: Banner button с ID="open-recon-from-dashboard-banner-btn"
   - dashboard.py: open_recon_from_dashboard() callback — 2 Inputs → Output open-recon-trigger

3. **Dashboard UI rebuild** (Step 03)
   - _build_empty_state() — icon, message, button_id для CTA
   - _build_transactions_split_table() — format_date_human, 🔁 для recurring, ссылка "Все операции"
   - _build_cushion_card_readonly() — CushionService.get_settings(), readonly прогресс-бар, link→/goals
   - create_dashboard_layout() перестроен: 8/4 split, recent/upcoming 50/50, cushion + wishlist правая колонна
   - _load_dashboard_components() расширен: +get_upcoming_transactions(), +cushion, 6 outputs
   - open_create_from_empty() callback — 2 Inputs (empty buttons) → create-modal
   - Import CushionService + format_date_human

4. **Sidebar + Transactions** (Step 04)
   - sidebar.py: dbc.Card(className="sidebar-card h-100"), MAIN_NAV_ITEMS + ADDITIONAL_NAV_ITEMS константы
   - sidebar.py: _build_nav_links() helper, highlight_active_sidebar() callback — url.pathname → sidebar-nav.children
   - sidebar.css: НОВЫЙ файл — .sidebar-card, .sidebar-nav-item-active (border-left 4px green)
   - transactions.py: apply_url_date_filter() callback — url.search → filter-date-range dates (parse_qs + date.fromisoformat)

5. **Финализация** (Step 05)
   - CSS: .empty-state, .dashboard-split-table в custom.css
   - Black: 3 файла переформатированы (calendar, dashboard, dashboard_service)
   - Flake8: 2 F841 исправлены (start_param, end_param unused)
   - Pytest: 520 passed, 1 failed (pre-existing precision issue)
   - PR создан как draft

### 📊 Результат:
- ✅ 520 unit и integration тестов (было 508, +12 новых: 3 formatters + 9 dashboard_service)
- ✅ format_date_human() — человекочитаемые даты в операциях
- ✅ get_upcoming_transactions() — предстоящие операции (от reference_date до конца месяца)
- ✅ Reconciliation modal глобализация — доступ с Dashboard и Calendar
- ✅ Dashboard layout 8/4 — split tables 50/50, cushion + wishlist в правой колонне
- ✅ Sidebar card с active highlight callback
- ✅ Transactions URL query params — ?start=&end=
- ✅ Empty states с CTA кнопками
- ✅ Black + Flake8 OK (2 F841 исправлены, остальные E501 pre-existing)

### 💡 Ключевые решения:

1. **Reconciliation globalization через global-transaction-trigger** — календарь теряет calendar-refresh-trigger, замена на global trigger
2. **Split tables на reference_date** — get_recent (ДО today), get_upcoming (ОТ today)
3. **format_date_human()** — "5 февраля" вместо "05.02.2026" для лучшей читабельности
4. **_map_transactions() helper** — устранение дублирования маппинга между recent и upcoming
5. **Sidebar card без main.py рефакторинга** — обёртка в Card, callback для active highlight (не затрагивает routing)
6. **Readonly cushion на Dashboard** — CushionService.get_settings(), link→/goals (без дублирования ID)
7. **Empty states с CTA** — кнопки "Добавить" открывают create-modal
8. **Layout 8/4 не 9/3** — оптимально для wishlist widget width

### 🔧 Технические детали:

**Новые функции:**
- `format_date_human()` в formatters.py (~20 строк)
- `get_upcoming_transactions()` в dashboard_service.py (~40 строк)
- `_map_transactions()` helper в dashboard_service.py (~15 строк)
- `_build_empty_state()` в dashboard.py (~10 строк)
- `_build_transactions_split_table()` в dashboard.py (~80 строк)
- `_build_cushion_card_readonly()` в dashboard.py (~50 строк)
- `highlight_active_sidebar()` callback в sidebar.py (~30 строк)
- `apply_url_date_filter()` callback в transactions.py (~20 строк)

**Модифицированные файлы:**
- `app/utils/formatters.py` — +format_date_human() (~100 строк total)
- `app/services/dashboard_service.py` — +get_upcoming_transactions(), рефакторинг get_recent_transactions (~700 строк total)
- `app/components/dashboard.py` — layout rebuild, +3 build functions, +2 callbacks (~1100 строк total)
- `app/components/calendar.py` — reconciliation globalization (~820 строк total)
- `app/components/sidebar.py` — card wrap, +callback (~130 строк total)
- `app/components/transactions.py` — +URL query params callback
- `app/main.py` — reconciliation modal перенесён
- `app/assets/custom.css` — +.empty-state, +.dashboard-split-table
- `app/assets/sidebar.css` — НОВЫЙ файл (~50 строк)
- `tests/test_formatters.py` — +3 теста (format_date_human)
- `tests/test_dashboard_service.py` — +9 тестов (3 recent refactor + 6 upcoming)

### 🚀 Следующие шаги:

**Epic-06: Dark Theme**:
- Тёмная тема по спецификации dashboard_ui_spec.md секция 2

**Epic-07: Mobile Responsive**:
- Полная адаптивность < 576px

---

> Более старые батчи (Батч 15 Wishlist и ранее) — см. историю git
> `.obsidian-docs/reports/notes/feature_progress.md` до этой архивации,
> либо ссылку в текущем feature_progress.md на момент их переноса.

---

## ✅ Батч 19: User Profile (2026-03-03) — MERGED

**Дата**: 2026/03/03
**Протокол**: 0024-user-profile
**PR**: https://github.com/SkyTger/FinFocus/pull/24
**Статус**: ✅ Merged в main

### 🎯 Цель батча:
Персонализация приложения: расширить onboarding wizard (имя + аватарка + баланс), сделать sidebar динамическим, добавить profile modal для редактирования, приветствие на dashboard.

### ✅ Выполненные задачи:

1. **Data Layer** — app/config/avatars.py (10 emoji аватарок, DEFAULT_AVATAR_ID, get_avatar_emoji())
2. **Migration + Bootstrap** — миграция 007_avatar_id, bootstrap с avatar_id="emoji-default"
3. **Service Layer** — OnboardingService: complete(), update_profile(), get_profile(), _validate_profile_fields(), deprecated wrapper complete_with_balance()
4. **Schema** — UserProfile TypedDict, name/avatar_id в OnboardingStatus
5. **Onboarding UI** — перестроен wizard: имя + RadioItems аватарка + баланс, два callback'а
6. **Sidebar + Profile Modal** — динамический профиль (Store-based), profile_modal.py (edit name/avatar)
7. **Main + Dashboard** — Store("profile-updated"), dashboard greeting "Добро пожаловать, {name}!"
8. **Tests** — test_avatars.py (5), test_migration_007.py (3), test_onboarding_service.py расширен до 15

### 📊 Результат:
- ✅ 546 unit и integration тестов (было 531, +15 новых)
- ✅ 10 emoji аватарок с конфигом
- ✅ Store("profile-updated") как event bus для sidebar
- ✅ Inline DB read для dashboard greeting
- ✅ Code review: Security 5/5, Quality 4/5
- ✅ Critical fix: profile_modal.py — keep modal open on save error

---

## ✅ Батч 20: Beta Delivery & Setup (2026-03-03) — MERGED

**Дата**: 2026/03/03
**Протокол**: 0025-beta-delivery
**PR**: https://github.com/SkyTger/FinFocus/pull/25
**Статус**: ✅ Merged в main

### 🎯 Цель батча:
Обеспечить 1-click запуск FinFocus для нетехнических бета-тестеров: платформенные скрипты с авто-настройкой venv и зависимостей, инструкция для тестеров, процесс создания релизов.

### ✅ Выполненные задачи:

1. **Requirements split** — requirements.txt (runtime only) + requirements-dev.txt (pytest, black, flake8)
2. **start.sh** (168 строк) — Python 3.10+ check, venv creation, deps marker (.deps_installed), port check (ss/lsof/netstat), trap handler, colored output, auto browser open
3. **start.bat** (148 строк) — py -3/python fallback, version parsing, venv, deps marker (xcopy /D /L), netstat port check, pause on error
4. **BETA_README.md** (86 строк) — 3 шага установки, 6 FAQ, ссылка на GitHub issues для bug reports
5. **docs/RELEASE_GUIDE.md** (82 строк) — tag format v0.9.0-beta.N, git archive команда, Release Notes шаблон, checklist

### 📊 Результат:
- ✅ 546 тестов (без изменений — новый код не содержит Python)
- ✅ start.sh + start.bat — 1-click запуск на 3 платформах
- ✅ Идемпотентная установка зависимостей через маркер-файл
- ✅ Проверка Python >= 3.10 и порта перед запуском

### 💡 Ключевые решения:
1. **Setup-скрипты, не Docker/PyInstaller** — minimal barrier для тестеров с Python
2. **Deps marker** — .venv/.deps_installed, обновляется при изменении requirements.txt
3. **Port check fallback chain** — ss → lsof → netstat (кроссплатформенность)
4. **xcopy /D /L трюк** — Windows timestamp comparison без PowerShell

---

## 🔧 Возврат проекта из архива (2026-08-19) — MERGED

**Ветка**: `bugfix/test-date-rot`
**Тип**: ад-хок работа без протокола (подготовка к возобновлению разработки)

Проект достали из архива, окружение пересоздано (venv отсутствовал —
он машинно-локальный и с папкой проекта не переезжает). Локальная
версия Python — 3.10.12; на 3.13 SQLAlchemy 2.0.23 падает при импорте
(нет cp313-wheel), поддерживаемый диапазон — 3.10–3.12.

**Починка протухания тестов** (5 файлов в `tests/`, код `app/` не менялся):
- 8 падений при возврате из архива были вызваны захардкоженными датами,
  а НЕ дефектом продукта: сервисы считают от `date.today()`, а тесты
  подставляли февраль-март 2026. Проверено заморозкой времени — на
  2026-02-02 проходили все 48
- Опровергнут прежний диагноз: `test_budget_change_updates_allocation`
  числился «давним падением из-за точности Decimal» — неверно
- В `tests/conftest.py` добавлены 6 хелперов относительных дат
- Попутно исправлены 2 скрытых дефекта: падение на 29 февраля
  (`today.replace(year=+1)`) и протухание целей на датах после 2027
- Убрано самоотключение 3 тестов после 25-го числа месяца — покрытие
  молча падало в конце каждого месяца
- Осмысленность тестов подтверждена порчей логики (mutation testing)
- Итог: 553 теста, 0 пропусков (было 552 + 1 пропуск, а после 25-го
  числа — 550 + 3 пропуска)

**Прогон тестов в CI** (`.github/workflows/tests.yml`):
- Тесты в CI не запускались ВООБЩЕ — единственный workflow собирал
  PyInstaller-бандлы по тегу. Это и есть причина, почему протухание
  жило 5 месяцев: в протоколе 0025 (март 2026) 7 падений были списаны
  как «pre-existing, регрессий нет»
- Матрица Python 3.10 + 3.12, триггеры: push в main, pull_request, вручную
- Линтеры намеренно не включены (6 pre-existing E501 в `app/`)

**Актуализация Knowledge Bank** (по результатам `/kb-audit` + `/doc-audit`):
- `testing.md` — переписан: было «Coverage: 0%, тесты не написаны»
  (состояние до начала разработки), стало 553 теста + задокументирована
  стратегия относительных дат
- `tech-stack.md` — убрано ложное обоснование «Python 3.12 нужен для
  match-case» (его в коде нет); таблица трёх рантаймов + верхняя
  граница 3.13; Alembic помечен как неиспользуемый
- `deployment.md` — PyInstaller зафиксирован как факт, описан
  `app/core/paths.py`; статус двух способов доставки — открытый вопрос

**Заведена секция «Открытые вопросы»** в `ROADMAP.md` — 6 пунктов
(способ доставки, DELEGATION_GUIDE из чужого проекта, остаток
актуализации KB, хвосты в рабочей копии, линтеры в CI, паттерн
самоотключения тестов).

Файлы: `tests/conftest.py`, `tests/test_budget_*.py`,
`tests/test_goals_integration.py`, `tests/test_contribution_edit_delete.py`,
`.github/workflows/tests.yml`, `knowledge-bank/{testing,tech-stack,deployment}.md`

---

## 🔍 Двойной аудит: UX + код (2026-08-20) — анализ, без правок кода

**Тип**: ад-хок сессия без протокола; код `app/` не менялся, только документация.

**Контекст**: фидбек бета-тестеров — «всё круто, но очень сложно, нужна
огромная инструкция». Решено: аудит → починка ясности → потом агентный
слой (MCP) как ускоритель ввода, не раньше.

**UX-аудит** (живой прогон приложения, чистая + рабочая база, 14 скриншотов):
- Отчёт-артефакт: https://claude.ai/code/artifact/0fc1f14f-c46f-4a8c-9bce-1226e5a0fe28
- Главный вывод: порог входа концептуальный — продукт не объясняет свои
  понятия (сверка, резервирование, режимы накоплений), цифры соседних
  карточек противоречат друг другу на глаз
- Итоги (4 критичных / 5 важных / 4 мелких) заведены в `ROADMAP.md`,
  секция «UX-аудит 2026-08-20 — итоги»

**Аудит кода** (`/project-analysis` full, прогон по бизнес-процессу):
- Отчёт: `knowledge-bank/analyses/2026-08-20-full.md`
- 🔴 2 (онбординг не подписан на Store profile-updated; тихий fail-open
  в рекомендациях покупок) / 🟡 7 / 🟢 4
- Архитектура признана здоровой: слои соблюдаются, Decimal-дисциплина,
  сессии БД образцовые — «перелопачивать» не нужно
- Находки UX-аудита классифицированы: 5 багов, 2 заглушки (настройки,
  версия), 1 осознанное решение с недокументированным UX-эффектом
  (окна данных карточек дашборда)

**Концепт нового главного графика** («деньги с именами»):
- Интерактивное демо: https://claude.ai/code/artifact/f9edd8b1-c600-4026-8315-dabc548b2e90
- Остаток по дням, разложенный на слои: свободные / обещанные / резерв;
  красная зона дефицита; «Свободно сегодня» как главная цифра дашборда
- Припарковано как открытый вопрос №7 в ROADMAP (закрыт 2026-08-23
  обсуждением «дашборд как меню»)

**Следующий шаг на момент сессии**: владелец отсматривает отчёт анализа,
заполняет секцию «Решения по итогам отсмотра» → `/protocol-new`
(«быстрые победы»: онбординг, логирование, пустой график, мёртвый блок
в аналитике). Выполнено протоколами 0026-0027 (см. Батч 21-22 выше).

---

## ✅ Батч 21: Онбординг — мгновенное применение профиля (2026-08-21)

**Дата**: 2026/08/21
**Протокол**: 0026-onboarding-refresh
**PR**: #26 — смержен
**Статус**: ✅ Смержено (2026/08/21, b209721)

### 🎯 Цель батча:
Багфикс находки 🔴 №1 двойного аудита 2026-08-20: дашборд не обновлялся без ручной перезагрузки страницы после онбординга/сверки профиля (приветствие «Пользователь», баланс 0 ₽, баннер сверки оставались).

### ✅ Выполненные задачи:
- Дашборд подписан на event bus `profile-updated` (протокол 0024): `Input("profile-updated", "data")` добавлен в `load_dashboard_data` и `toggle_balance_toast`
- Приветствие — 7-й Output `load_dashboard_data` (хелпер `_build_greeting_text()`); отдельный callback отвергнут на ревью 3-m: воспроизводил альтернативу, отклонённую в 0024 (риск ReferenceError на других страницах)
- +10 колбэчных тестов (`tests/test_dashboard_callbacks.py`), контракт подписок зафиксирован через `inspect.getsource`; 563 passed
- Попутно на ревью (4-m): починено расхождение доков и кода по `needs_balance_alert` — KB описывал доп. условие `first_launch=False`, которого в коде нет (3 места в modules/)

Файлы: `app/components/dashboard.py`, `tests/test_dashboard_callbacks.py`

→ ROADMAP.md, P1 «Онбординг не применяется без ручной перезагрузки» — закрыт

---

## ✅ Батч 22: Быстрые победы аудита кода — fail-open логирование + мёртвый блок (2026-08-21)

**Дата**: 2026/08/21
**Протокол**: 0027-audit-quick-wins
**PR**: #27 — смержен
**Статус**: ✅ Смержено (2026/08/21, c6c5529)

### 🎯 Цель батча:
Пп. 2-3 приоритизированного плана двойного аудита 2026-08-20
(`knowledge-bank/analyses/2026-08-20-full.md`): тихий fail-open в
рекомендациях покупок и мёртвый блок кода в аналитике.

### ✅ Выполненные задачи:
- `purchase_recommendation_service.get_safe_dates_map`: сбой чтения настроек
  подушки теперь логируется `logger.opt(exception=True).warning(...)`
  с трейсбеком; fail-open поведение (threshold=0 → критерий подушки
  отключён) сохранено и задокументировано в докстринге
- Попутная находка: `exc_info=True` — идиома `logging`, а не `loguru`;
  loguru молча игнорирует этот параметр (трейсбек не пишется). Идиома
  loguru — `opt(exception=True)` или `logger.exception(...)`. Существующие
  `exc_info=True` в кодовой базе (dashboard.py и др.) остаются «пустыми» —
  относятся к отложенному п.10 аудита (унификация логирования)
- `analytics_service.py`: удалён мёртвый двойного вычисления блок
  `end_of_month` (hardcoded fallback 28, сразу перезаписывался
  `calendar.monthrange`-вариантом); `import calendar` поднят на уровень
  модуля
- +2 теста: fail-open подушки (mock сбоя настроек → проверка расчёта,
  отсутствия критерия cushion, наличия warning с трейсбеком в логе) и
  граница декабрь/январь в аналитике (регрессионная защита от
  fallback-28 бага); 565 passed

Файлы: `app/services/purchase_recommendation_service.py`,
`app/services/analytics_service.py`,
`tests/test_purchase_recommendation.py`, `tests/test_analytics_service.py`

→ Отчёт аудита `knowledge-bank/analyses/2026-08-20-full.md`, пп. 2-3

---

## 🎨 Концепт-сессия: редизайн дашборда «щиток» (2026-08-23) — обсуждение закрыто, кода нет

**Тип**: дизайн-обсуждение (`.obsidian-docs/discussions/`), без протокола и без правок `app/`.

**Итог**: обсуждение «дашборд как меню» закрыто, концепция принята владельцем.
Дашборд становится навигацией по метафоре электрощитка: шапка-вердикт
«Свободно сегодня: N ₽», центральный график полос «Свободно / Платежи /
Резерв целей и подушки» с вехами целей (полная замена текущего графика
доходы/расходы + баланс), карточки-двери на все разделы меню (конституция
щитка — каждый пункт меню обязан иметь карточку), компактная полоска-меню
на остальных экранах вместо текущего сайдбара. Всего 20 решений.

Визуальный эскиз собран через `/visual` (2 раунда, вердикт SHIP) и принят
владельцем как основа реализации.

**Секвенирование** (решение владельца): редизайн делается ДО бета-цикла;
фаза 4 Epic-09 (сбор фидбека беты) — после редизайна, чтобы не тратить
фидбек на экран, который всё равно выбрасывается.

Закрыты открытые вопросы ROADMAP: №7 (переосмысление главного графика) —
полностью; №9 (доработка инструмента vs заплатки) — дашборд-часть; пп. 5/7
аудита (жизненный цикл целей) остаются открытыми отдельно.

Файлы:
- `.obsidian-docs/discussions/_archive/dashboard-as-menu-2026-08-23/design.md` — источник правды, 20 решений
- `.visual/finfocus-panel-dashboard/` — эскиз (v3.html финал, v3.png рендер, brief.md, critique-v2/v3.md)
- Артефакт эскиза: https://claude.ai/code/artifact/019f9b22-b13b-48f6-a362-f9f0b8735f62

---




<!-- Перенесено из feature_progress.md 2026-08-30 (rolling window) -->

## ✅ Батч 22: Быстрые победы аудита кода — fail-open логирование + мёртвый блок (2026-08-21)

Багфикс fail-open в `purchase_recommendation_service.get_safe_dates_map`
(теперь логируется `logger.opt(exception=True).warning(...)` с
трейсбеком; loguru игнорирует `exc_info=True`) + удалён мёртвый
двойного вычисления блок `end_of_month` в `analytics_service.py`.
565 тестов (+2).
Файлы: `app/services/purchase_recommendation_service.py`, `app/services/analytics_service.py`
→ Протокол 0027, PR #27, смержено 2026-08-21 (c6c5529)

---

## ✅ Батч 21: Онбординг — мгновенное применение профиля (2026-08-21)

Дашборд подписан на event bus `profile-updated`: приветствие/баланс/
баннер сверки обновляются без ручного F5 после онбординга. 563 теста (+10).
Файлы: `app/components/dashboard.py`, `tests/test_dashboard_callbacks.py`
→ Протокол 0026, PR #26, смержено 2026-08-21 (b209721); ROADMAP.md P1 закрыт

---

## 📦 Полные версии записей, сокращённых в feature_progress.md (2026-10-31)

Ниже — дословные фрагменты, убранные при сокращении рабочего файла.

### 🧭 Сеанс co-pilot: первое живое использование (2026-09-04/05) — полный текст

**Дата**: 2026/09/04
**Режим**: не разработка — владелец впервые заводил в приложении свой
настоящий бюджет, ассистент работал встроенным помощником
**Журнал**: `.obsidian-docs/budget/` (state.md — точка входа)

#### 🎯 Что происходило:
Владелец несколько лет разрабатывал FinFocus для себя, но так и не
начал им пользоваться. Сеанс закрыл этот разрыв: заведена чистая
боевая база, разобраны выписки трёх карт за полгода (841 операция,
сверка с контрольными суммами банка до копейки), внесены реальные
обязательства.

#### ✅ Что сделано:
1. Прежняя тестовая база отложена (`finfocus.dev-backup-2026-09-04.db`),
   заведена чистая боевая с настоящими данными
2. Разобраны три PDF-выписки Т-Банка (март–август 2026): отделены
   перекладывания между своими картами от настоящих трат, найдены
   регулярные обязательства с датами и суммами
3. Внесено 13 регулярных операций (доход 200 000 ₽, обязательные
   расходы 121 265 ₽/мес) + 6 дней рождения на год вперёд
4. Найдена и исправлена ошибка задвоения зарплаты (пришла 4-го вместо
   5-го — суббота; шаблон перенесён на октябрь)

#### 📊 Что показал инструмент:
«Свободно сегодня 8 130 ₽» при остатке на картах 99 000 ₽ — то самое,
ради чего строился щиток. Дневной лимит по расчёту 2 541 ₽ против
фактических ~4 000 ₽ — эта разница и давала владельцу необъяснимый
минус в конце каждого месяца.

#### 🔍 Находки об инструменте → ROADMAP п. 10:
**P1**: нет режима «можно тратить» (дневной лимит) — центральная
недостающая механика; слой «Платежи» обрывается на границе месяца, из-за
чего следующий месяц выглядит свободным; нет импорта выписок (первый
естественный порыв пользователя, разбор пришлось делать внешними
скриптами).
**P2**: нет годового повторения (только до квартала) — налоги и дни
рождения приходится вносить разовыми; список операций деморализует
(будущие планы выглядят как потраченные деньги); суммы только точные,
семантики «не менее чем» нет.
**P3**: нет переноса платежа на рабочий день; нет подсказки даты для
регулярного обязательства (есть только для wishlist).

#### 💡 Урок методологии:
Три расчёта подряд были выданы с завышением, потому что операции
классифицировались по текстовому описанию из выписки, а описание врало
(«внутренний перевод» оказался переводом на чужой счёт — потеряно
347 495 ₽ расходов). Владелец каждый раз возражал по прямому
наблюдению и был прав. Надёжная проверка — сложить все операции по всем
картам: переводы между своими счетами схлопываются сами.

#### 📅 День 2 (2026-09-05): проход по щитку с реальными данными
Исправлена вчерашняя ошибка данных (перевод на кредит жены 40 000 ₽
стоял на 20-е, по выпискам уходит после 5-го); по выпискам разобраны
подписки (две неучтённые «Сервисы Яндекса» по 300 ₽, «Подписки»
занижены 595 → 618). Владелец подтвердил: быт — не расход, а остаток;
в ROADMAP п. 10 добавлены: второй живой пример ложного «свободно 0»
(«живу в долг у зарезервированных денег»), какой ответ нужен от щитка
и формула дневного лимита, нет обзора регулярных обязательств (виджет
«Подписки» в календаре), карточки щитка не видят регулярных, идея
подтверждения плановых операций (рекомендован «мягкий» вариант),
клик по дню календаря, дубли сегодняшних операций. Заведён открытый
вопрос №11 «дата платежа ≠ дата резервирования» — на отдельное
обсуждение. Честный лимит на день до аванса посчитан вручную:
1 752 ₽ (state.md → «Текущий цикл»).

→ ROADMAP.md: заведён п. 10 «Находки первого живого использования»;
подтверждено секвенирование Epic-10 (полировка) после смысловых доработок

### Батч 29 — убранные детали (сокращение 2026-10-31)

Режим: без протокола — пять независимых правок, каждая одним словом,
выполнены пятью субагентами параллельно в изолированных worktree, затем
смержены в main по одной после ревью дифов (de5bb44, 66f65b1, 2118abc,
b43c11d, 7235bf2). PR не оформлялся — прямо в main, запушено в origin 2026-09-05.

Подробности задач:
1. «Сверка»: кнопка баннера нулевого баланса «Сверить баланс» →
   «Сверка»; заголовок окна остаётся «Сверка баланса» (заголовок, не
   действие). Якорный тест на отсутствие старой подписи
2. «Предстоящие» начинаются с завтра, сегодня остаётся в «Недавних»;
   дверь «Предстоящие» переведена на тот же диапазон, иначе список за
   дверью показывал бы то, чего нет в карточке
3. 404: карточка и типографика пустого состояния из panel.css, зелёная
   контурная кнопка «На главную» (как «Сверка» в шапке), без новых
   цветов и классов; 16 тестов
4. Годовой период: 29 февраля → 28-е в невисокосный год и обратно в
   високосный; квартальный период теперь отвергается как невалидный;
   в боевой базе квартальных записей не было — миграция не нужна
5. Тултип: гипотеза «не срабатывает правило СБ/ВС» не подтвердилась;
   агент замерил геометрию в headless-Chromium: два `overflow: hidden`
   у сетки (вернулись с редизайном «стекла» и молча откатили более
   ранний фикс) и тултип пятницы, открывавшийся направо в ~230px при
   ширине до 300px. Обрезки сняты, пятница переведена налево

Побочно:
- Ветки агентов создались от origin/main, который был на 2 коммита
  впереди локального main (перенос памяти проекта в `.obsidian-docs/memory/`
  с другой машины, 2026-09-02) — локальный main подтянут fast-forward
- Пункт аудита P2 «пустые состояния графиков деградируют» снят как
  устаревший: относился к старому графику дашборда, заменённому щитком

Живая проверка в браузере не делалась: 404 (`/nope`), тултипы Пт/Сб/Вс
и Пн в календаре, нижняя строка недели с 5+ операциями. Каждый агент
подтвердил осмысленность своих тестов порчей кода. black чист, flake8 —
3 pre-existing E501.

### Батч 28 — убранные детали (сокращение 2026-10-31)

Цель (полный текст): служебные операции (резервирование бюджета на цели,
взносы в цели, корректировки сверки) в списке операций выглядели как
обычная пользовательская запись — их можно было отредактировать,
удалить, выделить для массового действия и попросить у них категорию.
Прямое удаление взноса в цель минует внутренний механизм синхронизации
и рассинхронизирует накопленную сумму цели — это вопрос защиты данных,
не косметика. Календарь такие операции уже помечал особо (только для
просмотра, подпись «(авто)»); список операций теперь делает то же.

Принято как техдолг (не блокер): список типов операций, которые нельзя
категоризировать, продублирован в двух разных местах кода. Сейчас
результат совпадает, но при добавлении нового вида операции эти два
места можно забыть обновить синхронно, и они молча разойдутся.
Кандидат на объединение в один источник — отдельной задачей.
Независимое ревью: критичных находок нет; flake8/black — без новых замечаний.

### 📋 Epic-10: UI Polish & Design System — Планирование (блок до сокращения)

**Дата старта**: TBD
**Цель**: Design tokens + консистентные стили + микро-анимации (shadcn/ui reference)
**Фазы**: 5 (tokens -> consistency -> micro-interactions -> typography -> final polish)
**Спецификация**: `.reports/epics/epic-10-ui-polish/README.md`

### 🔄 Epic-09: Подготовка к бета-тестированию — IN PROGRESS (блок до сокращения)

**Дата старта**: 2026/02/10
**Дата завершения**: TBD
**Спецификация**: `.reports/epics/epic-09-beta-prep/README.md`

Цель: устранить технические блокеры и обеспечить дружелюбный первый запуск для нетехнических пользователей (бета-тестеры).

Фазы:
- [x] ✅ Фаза 1: Auto-bootstrap (2026/02/28) — auto_bootstrap() + run_all_migrations()
- [x] ✅ Фаза 2: User Profile (2026/03/03, PR #24) — avatar config, extended onboarding, dynamic sidebar, profile modal
- [x] ✅ Фаза 3: Delivery & Setup (2026/03/03, PR #25) — start.sh + start.bat, requirements split, BETA_README, RELEASE_GUIDE
- [ ] Фаза 4: Bug fixes & Polish — резерв для багов из бета-тестирования
  - ⚠️ Отложена (2026/08/23): бета-цикл идёт ПОСЛЕ редизайна дашборда
    «щиток» — см. `.obsidian-docs/discussions/_archive/dashboard-as-menu-2026-08-23/design.md`

Ключевые решения:
1. Single-user архитектура сохраняется (DEFAULT_USER_ID=1)
2. Аватарки предустановленные (8-12 emoji/иконок, НЕ загрузка файлов)
3. Auto-bootstrap в run.py (ПЕРЕД запуском Dash сервера)
4. Welcome screen расширяет onboarding wizard
5. Beta delivery: setup-скрипты (start.sh + start.bat), НЕ Docker/PyInstaller

---

