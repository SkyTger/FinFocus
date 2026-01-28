# Шаг 6: Callbacks

## Briefing

- **Цель:** Реализовать 9 callbacks для модала и карточки подушки
- **Ключевые файлы:**
  - `app/components/goals.py` — MODIFY
- **Доп. информация:** ADR-003 guard clauses обязательны во всех callbacks

## Sub-tasks

1. **Callback #1: load_cushion_settings** — загрузка при открытии страницы
   ```python
   @callback(
       Output("cushion-settings-store", "data"),
       Input("cushion-refresh-trigger", "data"),
       prevent_initial_call=False
   )
   def load_cushion_settings(trigger):
       """Загружает настройки подушки из БД."""
       ...
   ```

2. **Callback #2: auto_recalc_threshold** — автопересчет порога при изменении цели
   ```python
   @callback(
       Output("cushion-threshold-input", "value"),
       Input("cushion-target-input", "value"),
       State("cushion-threshold-manual-flag", "data"),
       prevent_initial_call=True
   )
   def auto_recalc_threshold(target, is_manual):
       """Пересчитывает порог если manual=False."""
       if is_manual:
           raise PreventUpdate
       ...
   ```

3. **Callback #3: mark_threshold_manual** — установка manual=True при ручном вводе
   ```python
   @callback(
       Output("cushion-threshold-manual-flag", "data"),
       Input("cushion-threshold-input", "value"),
       prevent_initial_call=True
   )
   def mark_threshold_manual(value):
       """Любое изменение threshold = manual=True."""
       if value is None:
           raise PreventUpdate
       return True
   ```

4. **Callback #4: toggle_calculator** — открытие/закрытие калькулятора

5. **Callback #5: add_scenario** — добавление сценария в список

6. **Callback #6: remove_scenario** — удаление сценария (Pattern-Matching)

7. **Callback #7: calculate_recommendation** — расчет рекомендации

8. **Callback #8: apply_recommendation** — применение рекомендации к цели

9. **Callback #9: save_cushion_settings** — сохранение в БД
   ```python
   @callback(
       [Output("cushion-modal", "is_open"),
        Output("cushion-refresh-trigger", "data")],
       Input("cushion-save-btn", "n_clicks"),
       [State("cushion-target-input", "value"),
        State("cushion-threshold-input", "value"),
        State("cushion-threshold-manual-flag", "data")],
       prevent_initial_call=True
   )
   def save_cushion_settings(n_clicks, target, threshold, manual):
       ...
   ```

10. **Callback #10: reset_cushion_settings** — сброс настроек

11. **Callback #11: open_cushion_modal** — открытие модала

12. **Callback #12: close_cushion_modal** — закрытие модала

## Workflow

1. Реализуй все callbacks с ADR-003 guard clauses
2. Базовая проверка: `python -m py_compile app/components/goals.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 7
5. Коммит: `git add . && git commit -m "feat(callbacks): add cushion modal callbacks [protocol-0013/06]"`
6. Push
7. Отчёт
