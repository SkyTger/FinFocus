# Шаг 8: Dashboard Toast

## Briefing

- **Цель:** Добавить Toast предупреждение на Dashboard для пользователей с balance=0
- **Ключевые файлы:**
  - `app/components/dashboard.py` — добавить Toast UI и callbacks
- **Доп. информация:**
  - Toast показывается если starting_balance == 0 И not dismissed
  - CTA "Сверить баланс" → /calendar?open_recon=1
  - Крестик закрывает до перезагрузки (без localStorage)

## Sub-tasks

1. **Добавить imports**:
   ```python
   from app.services.onboarding_service import OnboardingService
   ```

2. **Создать Toast компонент** (функция _build_balance_toast):
   ```python
   def _build_balance_toast() -> dbc.Toast:
       """Создает Toast для предупреждения о нулевом балансе."""
       return dbc.Toast(
           id="balance-alert-toast",
           header="Настройте начальный баланс",
           icon="warning",
           is_open=False,
           dismissable=True,
           duration=None,  # Не закрывается автоматически
           className="balance-toast",
           style={"position": "fixed", "top": 80, "right": 20, "width": 350},
           children=[
               html.P(
                   "Для точных расчётов укажите текущий остаток на счетах.",
                   className="mb-2"
               ),
               dcc.Link(
                   dbc.Button(
                       "Сверить баланс",
                       color="warning",
                       size="sm",
                   ),
                   href="/calendar?open_recon=1",
               ),
           ],
       )
   ```

3. **Добавить Toast в layout** (в create_dashboard):
   ```python
   # В конце layout добавить:
   _build_balance_toast(),
   ```

4. **Callback: toggle_balance_toast**:
   ```python
   @callback(
       Output("balance-alert-toast", "is_open"),
       [
           Input("url", "pathname"),
           Input("balance-alert-toast", "is_open"),
       ],
       State("balance-toast-dismissed", "data"),
       prevent_initial_call=False,
   )
   def toggle_balance_toast(
       pathname: str | None,
       is_open: bool,
       is_dismissed: bool,
   ) -> bool:
       """Показывает Toast если balance=0 и не dismissed."""
       triggered_id = ctx.triggered_id

       # При закрытии через крестик
       if triggered_id == "balance-alert-toast" and not is_open:
           return False

       # При загрузке Dashboard
       if pathname == "/dashboard" or pathname == "/":
           if is_dismissed:
               return False

           try:
               with get_db_session() as session:
                   service = OnboardingService(session)
                   status = service.get_status(DEFAULT_USER_ID)

               return status["needs_balance_alert"]

           except Exception:
               return False

       return no_update
   ```

5. **Callback: persist_toast_dismissal**:
   ```python
   @callback(
       Output("balance-toast-dismissed", "data"),
       Input("balance-alert-toast", "is_open"),
       State("balance-toast-dismissed", "data"),
       prevent_initial_call=True,
   )
   def persist_toast_dismissal(is_open: bool, current: bool) -> bool:
       """Запоминает закрытие Toast до перезагрузки."""
       if not is_open and not current:
           return True
       return no_update
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/dashboard.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 9, Next Action: Шаг 9
5. Коммит: `git add . && git commit -m "feat(dashboard): add balance alert toast [protocol-0014/08]"`
6. Push
7. Отчёт по формату
