# Шаг 5: Wizard UI

## Briefing

- **Цель:** Создать modal wizard с backdrop="static" для ввода starting_balance
- **Ключевые файлы:**
  - `app/components/onboarding_wizard.py` — NEW: modal + layout
- **Доп. информация:**
  - backdrop="static", keyboard=False — blocking modal
  - Предупреждение при отрицательном значении (желтый текст)
  - Кнопки: "Продолжить" (disabled если пусто), "Пропустить"

## Sub-tasks

1. **Создать UI компонент** (`app/components/onboarding_wizard.py`):
   ```python
   """Onboarding Wizard — modal для первоначальной настройки."""
   import dash_bootstrap_components as dbc
   from dash import html, dcc


   def create_onboarding_wizard() -> dbc.Modal:
       """Создает blocking modal для онбординга.

       Returns:
           dbc.Modal: Модальное окно с формой ввода starting_balance.
       """
       return dbc.Modal(
           id="onboarding-modal",
           is_open=False,
           backdrop="static",  # Клик вне modal не закрывает
           keyboard=False,     # Escape не закрывает
           centered=True,
           className="onboarding-modal",
           children=[
               dbc.ModalHeader(
                   dbc.ModalTitle("Добро пожаловать в FinFocus!"),
                   close_button=False,  # Без крестика
               ),
               dbc.ModalBody([
                   html.P(
                       "Для точных расчётов кассового календаря укажите "
                       "текущий остаток на всех ваших счетах:",
                       className="mb-3"
                   ),
                   dbc.InputGroup([
                       dbc.Input(
                           id="onboarding-balance-input",
                           type="number",
                           placeholder="0.00",
                           step="0.01",
                           className="onboarding-balance-input",
                       ),
                       dbc.InputGroupText("₽"),
                   ], className="mb-2"),
                   html.Div(
                       id="onboarding-balance-warning",
                       className="onboarding-warning text-warning",
                       style={"display": "none"},
                       children="Отрицательный баланс — вы уверены?",
                   ),
                   html.Small(
                       "Вы сможете изменить это значение позже через Сверку баланса.",
                       className="text-muted"
                   ),
               ]),
               dbc.ModalFooter([
                   dbc.Button(
                       "Пропустить",
                       id="onboarding-skip-btn",
                       color="secondary",
                       outline=True,
                       className="me-2",
                   ),
                   dbc.Button(
                       "Продолжить",
                       id="onboarding-submit-btn",
                       color="success",
                       disabled=True,  # Disabled по умолчанию
                   ),
               ], className="justify-content-end"),
           ],
       )
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/onboarding_wizard.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 6, Next Action: Шаг 6
5. Коммит: `git add . && git commit -m "feat(ui): add onboarding wizard modal [protocol-0014/05]"`
6. Push
7. Отчёт по формату
