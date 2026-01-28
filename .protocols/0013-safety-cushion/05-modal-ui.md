# Шаг 5: Модал UI

## Briefing

- **Цель:** Реализовать модал настройки подушки с калькулятором сценариев
- **Ключевые файлы:**
  - `app/components/goals.py` — MODIFY
- **Доп. информация:** Поля цели и порога, collapsible калькулятор, кнопки "Сохранить"/"Сбросить"

## Sub-tasks

1. **Добавить функцию `_build_cushion_modal()`:**
   ```python
   def _build_cushion_modal() -> dbc.Modal:
       """Модал настройки подушки.

       Содержит:
       - Поле "Цель подушки" (число >= 0)
       - Поле "Минимальный остаток" (порог, по умолчанию 30% от цели)
       - Collapsible секция "Рассчитать по сценариям"
       - Кнопки: Сохранить, Сбросить, Отмена
       """
       return dbc.Modal([
           dbc.ModalHeader("Настройка финансовой подушки"),
           dbc.ModalBody([
               # Поле цели
               dbc.Label("Цель подушки"),
               dbc.Input(id="cushion-target-input", type="number", min=0, step=1000),

               # Поле порога
               dbc.Label("Минимальный остаток (порог)"),
               dbc.InputGroup([
                   dbc.Input(id="cushion-threshold-input", type="number", min=0, max=100),
                   dbc.InputGroupText("%")
               ]),
               html.Small("При достижении этого порога баланс считается в зоне риска"),

               # Collapsible калькулятор
               dbc.Collapse([
                   html.H6("Сценарии"),
                   dcc.Store(id="cushion-scenarios-store", data=[]),
                   html.Div(id="cushion-scenarios-list"),
                   dbc.Button("+ Добавить сценарий", id="cushion-add-scenario-btn", size="sm"),
                   dbc.RadioItems(
                       id="cushion-calc-mode",
                       options=[
                           {"label": "Сумма всех", "value": "sum"},
                           {"label": "По самому дорогому", "value": "max_scenario"}
                       ],
                       value="sum"
                   ),
                   html.Div(id="cushion-recommendation"),
                   dbc.Button("Применить", id="cushion-apply-recommendation-btn", size="sm")
               ], id="cushion-calculator-collapse", is_open=False),
               dbc.Button("Рассчитать по сценариям", id="cushion-toggle-calculator-btn", outline=True)
           ]),
           dbc.ModalFooter([
               dbc.Button("Сбросить", id="cushion-reset-btn", color="danger", outline=True),
               dbc.Button("Отмена", id="cushion-cancel-btn"),
               dbc.Button("Сохранить", id="cushion-save-btn", color="primary")
           ])
       ], id="cushion-modal", is_open=False, size="lg")
   ```

2. **Добавить dcc.Store для manual flag:**
   ```python
   dcc.Store(id="cushion-threshold-manual-flag", data=False)
   ```

3. **Интегрировать модал в layout goals**

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка: `python -m py_compile app/components/goals.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 6
5. Коммит: `git add . && git commit -m "feat(ui): add cushion settings modal [protocol-0013/05]"`
6. Push
7. Отчёт
