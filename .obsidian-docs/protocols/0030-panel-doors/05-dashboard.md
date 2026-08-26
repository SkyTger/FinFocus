# Шаг 5: Перестройка щитка

## Briefing

- **Цель:** layout дашборда = шапка + график + ряд карточек; снять старую раскладку 8/4.
- **Ключевые файлы:**
  - `app/components/dashboard.py` — layout, `_load_dashboard_components`, оба колбэка
  - `app/components/wishlist.py` — удаление виджета вместе с его Input
  - `app/components/__init__.py` — экспорты
  - `app/assets/custom.css` — снятие `.db-*` раскладки
- **Доп. информация:** solution-v4.md, план шаги 6-7. `build_layers_chart` и `_axis_tickvals` **не правятся** (форма `days` не меняется).

## Sub-tasks

- [ ] Layout: шапка (кусок 1, без правок) + график (без правок) + `html.Div(id="dashboard-cards-row")`
- [ ] Удалить: `_build_transactions_split_table`, `_build_cushion_card_readonly` (сессия `:871`), `_build_empty_state`, вызов `build_wishlist_widget()` из layout (`:687`), четыре clientside-триггера пустых состояний
- [ ] `_load_dashboard_components` → 3 значения через `DashboardPanelService`; оба колбэка (`load_dashboard_data`, `refresh_dashboard_after_crud`) → 3 Output'а
- [ ] Добавить **один** clientside-триггер: дверь Wishlist → Store `open-wishlist-trigger`
- [ ] Вычистить импорты: `build_wishlist_widget`, `CushionService`, `DashboardService`, `RecentTransaction`
- [ ] `wishlist.py`: удалить `build_wishlist_widget` и `_build_widget_item`; `open_wishlist_modal` — **единственный** Input `open-wishlist-trigger` + guard на пустой Store; **удалить `Input("open-wishlist-modal-btn")`** вместе с элементом (правило «удаляешь элемент — удаляй его Input»)
- [ ] `custom.css`: снять `.db-left-col`, `.db-right-col`, `.db-main-row`, `.dashboard-split-table`
- [ ] **Онбординг-тост не трогать** (FR-4): `_build_balance_banner`, `toggle_balance_toast`, `persist_toast_dismissal` остаются как есть

## Workflow

1. Выполни Sub-tasks последовательно
2. Проверка: `python -m py_compile app/components/dashboard.py app/components/wishlist.py` + `pytest tests/test_dashboard_panel_ui.py` (47 тестов куска 1 обязаны остаться зелёными **без правок**)
3. Обнови `log.md`, `context.md`
4. Проверь `main` на случайные файлы
5. Коммит: `git add . && git commit -m "feat(ui): щиток — карточки вместо split-таблиц и readonly-подушки [protocol-0030/05]"`
6. Push
7. Отчёт
