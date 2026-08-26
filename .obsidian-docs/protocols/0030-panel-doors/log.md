# Журнал протокола 0030-panel-doors

## Шаг 0: Подготовка (2026-08-26)

Создан worktree `0030-panel-doors` от `origin/main` (d56b17c), артефакты
протокола: plan.md, context.md, log.md, 00-setup.md, 9 файлов шагов.

**Вход протокола** — цикл `/design-loop` (4 итерации, финал solution-v4,
⭐4/5, блокеров нет, покрытие спеки 25/25 PASS). Артефакты
проектирования закоммичены в main перед созданием ветки (d56b17c).

**Отступление от спеки, зафиксированное осознанно:** FR-1.a требует
«вчера / сегодня / завтра» в карточке «Календарь». Решением владельца
от 2026-08-26 окошко «вчера» **убрано** — карточка показывает сегодня и
завтра. Причина: расчёт «вчера» три итерации проектирования подряд
порождал тихие дефекты (граница расчёта → сумма платежей → резерв 1-го
числа), каждый правдоподобный и не ловимый прежними проверками.
Следствие: `MoneyLayersService` куском 2 **не затрагивается вообще**,
C-5 не используется, 47 тестов визуального слоя щитка не правятся.

**Pre-existing состояние**: flake8 — 6 замечаний E501 (открытый вопрос
№5 ROADMAP, не трогаем), black чист, 693 теста зелёные.

Restore context: protocol-0030#ctx-1

## Шаг 1: Контракты карточек (2026-08-26)

Создан `app/schema/panel.py` — контракты пяти карточек-дверей из
solution-v4 («Модель данных»), реэкспорт в `app/schema/__init__.py`.

**Адаптации относительно solution-v4** (решение владельца 2026-08-26,
«вчера» убрано):
- `CalendarDaySlice` — без поля `has_data` (оба дня всегда в окне
  модели, прочерк рисовать не из чего); label — «Сегодня»/«Завтра»
- `CalendarCardData.days` — ровно ДВА окошка (сегодня, завтра)
- `app/schema/money_layers.py` НЕ тронут: поле `yesterday`,
  описанное в solution-v4, не заводится
- Ссылки на номера строк чужих файлов в докстрингах сведены к именам
  файлов/функций (номера из solution-v4 протухнут при первой правке)

**Сверки**:
- `TRANSACTION_KIND_MAP` сверен с фактическим `TransactionType`
  (database.py) программно: шесть значений, имена совпадают
- `is_new_user` в `PanelData` отсутствует, `DIP_STRONG_THRESHOLD`
  не создан — по плану шага

Проверки: py_compile OK, импорт из `app.schema` OK, black чист,
flake8 без замечаний.

## Шаг 2: Композитор данных (2026-08-26)

Создан `app/services/panel_service.py` (~640 строк) —
`DashboardPanelService.get_panel_data()`: один сбор PanelData за одну
сессию, `get_money_layers` вне try/except (модель не деградирует),
пять блоков — четыре в поблочных try/except с
`logger.opt(exception=True)`. Экспорт в `app/services/__init__.py`.

**По плану шага**: `_calendar_block` — чистая функция от layers
(0 запросов, дни из days[0]/[1]); `_goals_block` — одно
`session.get(User)` вместо трёх сервисных вызовов, `AllocationService()`
без аргументов, подушка из layers без `CushionService.get_settings`;
`_operations_block` — явные преобразования (ISO→date, kind по
`TRANSACTION_KIND_MAP`, переименование is_recurring_instance, title с
фолбэком); `_analytics_block` — month_label из reference_date;
`_wishlist_block` — to_data внутри сессии; пять `_empty_*` по
контракту (Optional→None, числа→0, строки→"", href как обычно).

**Интерпретации, не расписанные в solution дословно** (задокументированы
в докстрингах):
- `operations_note`: «сегодня» — счётчик платежей дня из
  `layers["upcoming_payments"]` со склонением («2 операции»),
  «завтра» — «план» при наличии платежей, иначе None (RTM #62,
  сведённый к двум окошкам)
- EMPTY-критерий карточки «Календарь» — `layers["is_empty"]`
  (собственные данные карточки и есть модель слоёв; иначе чистая база
  дала бы «Сегодня — 0 ₽» — артефакт AC-5)
- `cushion_label` = «N% из <format_rub(target)>»; формула progress
  повторяет `CushionService.get_settings` (current<0 → 0, cap 100)
- FAILED-срезы = `_empty_*` + подмена status (хелпер `_failed`)
- Цвета мини-структуры — локальная копия первых цветов
  CATEGORY_COLORS: services не импортирует components (C-2)
- `total_count` wishlist = len(get_all)

**Смоук** (in-memory SQLite): пустая база без User — все пять EMPTY;
база с User/целями/операциями/wishlist — все пять OK, чтение всех
полей после закрытия сессии без DetachedInstanceError.

Проверки: py_compile OK, black чист, flake8 без замечаний.
