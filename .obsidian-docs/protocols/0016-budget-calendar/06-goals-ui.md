# Шаг 6: Goals UI

## Briefing

- **Цель:** Добавить карточку бюджета и расширить модал настройки режима
- **Ключевые файлы:**
  - `app/components/goals.py` — UI компоненты и callbacks
  - `app/assets/goals.css` — стили карточки бюджета
- **Доп. информация:** Цветовая индикация: 0-70% green, 70-90% yellow, 90-100% orange, >100% red

## Sub-tasks

1. **_build_budget_progress_card()** — новая функция:
   ```python
   def _build_budget_progress_card(progress: BudgetProgress, month_label: str) -> dbc.Card:
       # Карточка "Бюджет накоплений (Февраль 2026)"
       # Прогресс-бар с цветом по status
       # Текст: "Внесено 5 000 из 15 000 ₽" или "Распределено..."
   ```

2. **Расширить _build_budget_modal()** — добавить:
   - RadioButtons: "Фиксированная дата" / "Из остатка"
   - Dropdown: день месяца (1-31), показывать только для fixed_date
   - Tooltip с описанием режимов

3. **Callback: load_budget_modal_data** — загрузка settings при открытии:
   ```python
   @callback(
       Output("budget-mode-radio", "value"),
       Output("budget-day-dropdown", "value"),
       Output("budget-day-container", "style"),
       Input("budget-modal", "is_open"),
       State("budget-modal", "is_open"),
   )
   ```

4. **Callback: toggle_day_dropdown** — показать/скрыть dropdown:
   ```python
   @callback(
       Output("budget-day-container", "style"),
       Input("budget-mode-radio", "value"),
   )
   ```

5. **Callback: save_budget_settings** — сохранение режима:
   ```python
   @callback(
       Output("budget-modal", "is_open"),
       Output("goals-refresh-trigger", "data"),
       Input("budget-save-btn", "n_clicks"),
       State("budget-amount-input", "value"),
       State("budget-mode-radio", "value"),
       State("budget-day-dropdown", "value"),
   )
   ```

6. **Callback: refresh_budget_card** — обновление карточки:
   ```python
   @callback(
       Output("budget-progress-card", "children"),
       Input("goals-refresh-trigger", "data"),
   )
   ```

7. **CSS стили** в `goals.css`:
   - `.budget-progress-card`
   - Цветовые классы для progress bar

## Workflow

1. Выполни Sub-tasks
2. Проверка: `python -m py_compile app/components/goals.py`
3. Визуальное тестирование: запустить app, проверить UI
4. Обнови `log.md`
5. Обнови `context.md` — Current Step: 7
6. Коммит: `git add . && git commit -m "feat(ui): add budget progress card and mode selector [protocol-0016/06]"`
7. Push
