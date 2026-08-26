# Шаг 8: Тесты UI и адаптация

## Briefing

- **Цель:** покрыть визуальный слой карточек и сайдбар; адаптировать существующие тесты под новую арность колбэков.
- **Ключевые файлы:**
  - `tests/test_panel_cards_ui.py` — НОВЫЙ
  - `tests/test_sidebar.py` — НОВЫЙ (сайдбар не покрыт **ничем** — именно поэтому дефект профиля не был бы поймал)
  - `tests/test_dashboard_callbacks.py`, `tests/test_profile_modal_callbacks.py` — адаптация
  - `tests/test_dashboard_panel_ui.py` — **правок не требует**, проверяется прогоном
- **Доп. информация:** solution-v4.md, план шаги 10-11. Стиль — как `test_dashboard_panel_ui.py`: хелперы `iter_tree`/`joined_text`/`find_by_id`, фикстуры-словари, относительные даты, без БД.

## Sub-tasks

- [ ] `test_panel_cards_ui.py`: пять карточек присутствуют при любом статусе (FR-2/AC-5); пустые состояния без `₽`/`%`/нулей; **AC-7** в двух фикстурах (минимум > 0 → нет `pnl-flagline-strong`; ≤ 0 → есть); **`status=EMPTY` при непустых `dip_*` → маркера в дереве нет**; href'ы всех дверей; отсутствие слова «Доход» в карточке Аналитика; **наличие подписи объявленного расхождения**; отсутствие карточки подушки в ряду и наличие строки подушки внутри карточки Цели (AC-4); смешанный случай пустоты
- [ ] **Карточка «Календарь» — два окошка**, не три: ассерт на состав (решение владельца)
- [ ] `test_sidebar.py`: контракт входов `render_sidebar_slot` через `inspect.getsource` — два Input'а, оба на `url`/`profile-updated`, **ни одного** на элемент сайдбара; имя и эмодзи из профиля в дереве `create_sidebar("/calendar", profile)`; класс `sidebar-nav-item-active` у активного пункта; `render_sidebar_slot("/dashboard", None) == []`; **«в модуле sidebar нет ни одного `@callback`»** (регрессионный якорь); `patch` падающего `get_profile` → пять пунктов меню на месте
- [ ] `test_dashboard_callbacks.py`: 5 Output'ов → 3, контракт декоратора
- [ ] `test_profile_modal_callbacks.py`: вход через Store вместо `sidebar-profile-container`
- [ ] Тест на `handle_panel_query_params`: `pathname="/transactions"` → `PreventUpdate` (контрактная фиксация); `/calendar` и `/goals` → Store'ы заполнены и `search == ""`
- [ ] Прогон `pytest tests/test_dashboard_panel_ui.py` — 47 тестов зелёные **без правок**

## Workflow

1. Выполни Sub-tasks последовательно
2. Проверка: `pytest tests/ -q`
3. Обнови `log.md`, `context.md`
4. Проверь `main` на случайные файлы
5. Коммит: `git add . && git commit -m "test(ui): тесты карточек-дверей и сайдбара [protocol-0030/08]"`
6. Push
7. Отчёт
