# Шаг 1: Контракты карточек

## Briefing

- **Цель:** создать `app/schema/panel.py` — TypedDict-контракты данных пяти карточек-дверей. Контракт первым, чтобы тесты шага 3 писались от него.
- **Ключевые файлы:**
  - `app/schema/panel.py` — НОВЫЙ
  - `app/schema/__init__.py` — реэкспорт
  - `app/schema/money_layers.py` — **только читать**, не менять (решение владельца про «вчера»)
- **Доп. информация:** solution-v4.md, секция «Модель данных» — контракты приведены полностью с докстрингами. Читать оттуда, не изобретать.

## Sub-tasks

- [ ] `CardStatus` (Enum: OK / EMPTY / FAILED) с докстрингом: единственный источник правды отрисовки карточки; «нет пользователя» — это EMPTY, а не сбой
- [ ] `CalendarDaySlice`, `CalendarCardData` — **два окошка** (сегодня, завтра), не три: «вчера» убрано решением владельца 2026-08-26. Поля `has_data` и механизм прочерка **не нужны** (оба дня всегда в окне) — упростить относительно solution-v4
- [ ] `GoalsCardData` — топ-цель + сводка + подушка одной строкой
- [ ] `OperationRow`, `OperationsCardData` — с докстрингом ограничения: только материализованные операции (решение владельца 2026-08-25)
- [ ] `AnalyticsCategorySlice`, `AnalyticsCardData` — с докстрингом объявленного расхождения с месячным слоем «Платежи» графика (две причины по телу `get_expenses_by_category`)
- [ ] `WishlistCardRow`, `WishlistCardData`
- [ ] `PanelData` — **без** `is_new_user` (два источника правды не заводим)
- [ ] Константы: `OPERATIONS_PER_GROUP = 3`, `MINI_STRUCTURE_CATEGORIES = 3`, `TRANSACTION_KIND_MAP` (шесть значений enum → три `kind`). Константы `DIP_STRONG_THRESHOLD` **не создавать** — прямое `dip_free <= 0` в коде
- [ ] Сверить `TRANSACTION_KIND_MAP` с фактическим `TransactionType` (`app/models/database.py`): ровно шесть значений, имена совпадают
- [ ] Реэкспорт в `app/schema/__init__.py`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/schema/panel.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 2, Next Action
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(schema): контракты карточек-дверей щитка [protocol-0030/01]"`
7. Push
8. Отчёт по формату
