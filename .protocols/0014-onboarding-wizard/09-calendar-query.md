# Шаг 9: Calendar Query Param Handler

## Briefing

- **Цель:** Реализовать auto-open Reconciliation modal через query parameter
- **Ключевые файлы:**
  - `app/components/calendar.py` — расширить toggle_reconciliation_modal
- **Доп. информация:**
  - Query parameter: ?open_recon=1
  - Query cleanup strategy: full (url.search = "")
  - Добавить Output url.search в callback

## Sub-tasks

1. **Расширить toggle_reconciliation_modal callback**:

   Добавить:
   - `Input("url", "search")` — для отслеживания query params
   - `Output("url", "search", allow_duplicate=True)` — для очистки

   ```python
   @callback(
       [
           Output("reconciliation-modal", "is_open"),
           Output("reconciliation-expected", "value"),
           Output("reconciliation-actual", "value"),
           Output("reconciliation-preview", "children"),
           Output("reconciliation-message", "children"),
           Output("url", "search", allow_duplicate=True),  # NEW: для очистки
       ],
       [
           Input("open-reconciliation-btn", "n_clicks"),
           Input("cancel-reconciliation-btn", "n_clicks"),
           Input("reconciliation-date", "date"),
           Input("url", "search"),  # NEW: query param trigger
       ],
       [
           State("reconciliation-modal", "is_open"),
           State("url", "pathname"),
       ],
       prevent_initial_call=True,
   )
   def toggle_reconciliation_modal(
       open_clicks: int | None,
       cancel_clicks: int | None,
       selected_date: str | None,
       url_search: str | None,  # NEW
       is_open: bool,
       pathname: str | None,
   ) -> tuple[bool, str, float | None, str, str, str]:
       """Открывает/закрывает модал сверки.

       Query Parameter Cleanup: Full.
       При обработке ?open_recon=1 весь search string очищается пустой строкой.
       """
       triggered_id = ctx.triggered_id

       # NEW: Auto-open from query parameter
       if triggered_id == "url":
           # Guard: только на странице календаря
           if pathname != "/calendar":
               raise PreventUpdate

           if url_search and "open_recon=1" in url_search:
               target_date = date.today()

               try:
                   with get_db_session() as session:
                       service = ReconciliationService(session)
                       expected = service.get_expected_balance(
                           user_id=DEFAULT_USER_ID, target_date=target_date
                       )
                   # FULL CLEANUP: возвращаем пустую строку
                   return True, f"{expected:,.2f} ₽", None, "", "", ""

               except Exception as e:
                   logger.error(f"Ошибка auto-open reconciliation: {e}")
                   return True, "Ошибка", None, "", "", ""

           raise PreventUpdate

       # Остальная логика без изменений, но добавить no_update для url.search
       # ... existing code, добавить no_update в return tuple
   ```

2. **Обновить существующие return statements**:

   Каждый return должен включать 6-й элемент для url.search:
   - При открытии/закрытии кнопками: `no_update`
   - При auto-open: `""` (пустая строка для очистки)

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/calendar.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 10, Next Action: Шаг 10
5. Коммит: `git add . && git commit -m "feat(calendar): add query param auto-open for reconciliation [protocol-0014/09]"`
6. Push
7. Отчёт по формату
