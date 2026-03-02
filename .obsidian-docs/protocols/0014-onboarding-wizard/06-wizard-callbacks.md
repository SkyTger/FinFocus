# Шаг 6: Wizard Callbacks

## Briefing

- **Цель:** Реализовать callbacks для проверки first_launch, валидации и сохранения
- **Ключевые файлы:**
  - `app/components/onboarding_wizard.py` — добавить callbacks
- **Доп. информация:**
  - DB failure strategy: fail-closed (при ошибке скрыть wizard)
  - ADR-003 guard clauses для Pattern-Matching

## Sub-tasks

1. **Добавить imports и константы**:
   ```python
   from dash import callback, Output, Input, State, ctx, no_update
   from dash.exceptions import PreventUpdate
   from decimal import Decimal
   import logging

   from app.core.database import get_db_session
   from app.services.onboarding_service import OnboardingService

   logger = logging.getLogger(__name__)
   DEFAULT_USER_ID = 1
   ```

2. **Callback: check_onboarding_and_validate**:
   ```python
   @callback(
       [
           Output("onboarding-modal", "is_open"),
           Output("onboarding-submit-btn", "disabled"),
           Output("onboarding-balance-warning", "style"),
       ],
       [
           Input("url", "pathname"),
           Input("onboarding-balance-input", "value"),
       ],
       prevent_initial_call=False,
   )
   def check_onboarding_and_validate(
       pathname: str | None,
       balance_value: float | None,
   ) -> tuple[bool, bool, dict]:
       """Проверяет first_launch и валидирует ввод.

       DB Failure Strategy: Fail-closed.
       При ошибке чтения first_launch wizard скрывается, позволяя
       пользователю работать. Повторная попытка при следующей загрузке.
       """
       triggered_id = ctx.triggered_id

       # При первой загрузке или navigation — проверяем first_launch
       if triggered_id == "url" or triggered_id is None:
           try:
               with get_db_session() as session:
                   service = OnboardingService(session)
                   status = service.get_status(DEFAULT_USER_ID)

               if status["first_launch"]:
                   return True, True, {"display": "none"}
               else:
                   return False, True, {"display": "none"}

           except Exception as e:
               # FAIL-CLOSED: скрыть wizard при ошибке
               logger.error(f"Ошибка проверки онбординга (fail-closed): {e}")
               return False, True, {"display": "none"}

       # При вводе значения — валидация
       if triggered_id == "onboarding-balance-input":
           if balance_value is None or balance_value == "":
               return no_update, True, {"display": "none"}

           try:
               value = float(balance_value)
               is_negative = value < 0
               return (
                   no_update,
                   False,  # Enable submit
                   {"display": "block"} if is_negative else {"display": "none"},
               )
           except (ValueError, TypeError):
               return no_update, True, {"display": "none"}

       raise PreventUpdate
   ```

3. **Callback: handle_onboarding_action**:
   ```python
   @callback(
       Output("onboarding-modal", "is_open", allow_duplicate=True),
       [
           Input("onboarding-submit-btn", "n_clicks"),
           Input("onboarding-skip-btn", "n_clicks"),
       ],
       State("onboarding-balance-input", "value"),
       prevent_initial_call=True,
   )
   def handle_onboarding_action(
       submit_clicks: int | None,
       skip_clicks: int | None,
       balance_value: float | None,
   ) -> bool:
       """Обрабатывает submit или skip действия."""
       # Guard: проверяем что был реальный клик
       if not ctx.triggered:
           raise PreventUpdate

       triggered_id = ctx.triggered_id

       # Guard: проверяем что значение не None (автовызов)
       trigger_value = ctx.triggered[0].get("value")
       if trigger_value is None:
           raise PreventUpdate

       try:
           with get_db_session() as session:
               service = OnboardingService(session)

               if triggered_id == "onboarding-submit-btn":
                   balance = Decimal(str(balance_value)) if balance_value else Decimal("0")
                   service.complete_with_balance(DEFAULT_USER_ID, balance)
               elif triggered_id == "onboarding-skip-btn":
                   service.skip(DEFAULT_USER_ID)

               session.commit()

           return False  # Close modal

       except Exception as e:
           logger.error(f"Ошибка сохранения онбординга: {e}")
           return False  # Close modal anyway
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/onboarding_wizard.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 7, Next Action: Шаг 7
5. Коммит: `git add . && git commit -m "feat(callbacks): add onboarding wizard callbacks [protocol-0014/06]"`
6. Push
7. Отчёт по формату
