# Шаг 4: Plotly Charts + Dashboard Integration

## Briefing

- **Цель:** Plotly chart builders для Month и Year mode, helper для устранения дублирования callbacks, click→create callback, transaction_modals handler.
- **Ключевые файлы:**
  - `app/components/dashboard.py` — MOD (+350 строк)
  - `app/components/transaction_modals.py` — MOD (+10 строк)
- **Доп. информация:** Единый Graph ID "daily-cashflow-chart" для обоих режимов. Hover через customdata + format_rub(). MONTH_NAMES_RU_SHORT импортировать из dashboard_service.py.

## Sub-tasks

1. **Добавить `STATUS_COLORS` dict:**
   - `{"ok": "#27ae60", "attention": "#f39c12", "risk": "#c0152f"}`

2. **Добавить `_build_daily_cashflow_chart(data: MonthlyCashflowData) -> dbc.Card`:**
   - go.Bar x2 (income #27ae60, expense #e74c3c, barmode="group")
   - go.Scatter balance line (lines+markers, width=2.5, цвет по STATUS_COLORS[min_status])
   - go.Scatter min marker (diamond, text "Мин: день, сумма")
   - Today vertical dashed line (shapes, #3498db)
   - tickvals [1,8,15,22,29]
   - Hover: customdata + format_rub() + hovertemplate
   - hovermode="x unified"
   - yaxis2 для balance (dual Y-axis)
   - Horizontal gridlines rgba(0,0,0,0.1), no vertical grid

3. **Добавить `_build_yearly_cashflow_chart(data: YearlyCashflowData) -> dbc.Card`:**
   - Аналогичная структура, X-ось: месяцы (Янв..Дек)
   - Current month: rect shape с fillcolor rgba(52,152,219,0.08)
   - Title: "Кассовый календарь — {year}"

4. **Добавить `_load_dashboard_components(period, period_state) -> tuple`:**
   - Единая точка для load_dashboard_data и refresh_dashboard_after_crud
   - if period=="month" → get_daily_cashflow → _build_daily_cashflow_chart
   - else → get_yearly_cashflow → _build_yearly_cashflow_chart
   - year/month из period_state.get() с fallback на today

5. **Обновить `load_dashboard_data` callback:**
   - Добавить State("dashboard-period", "data") как period_state
   - Тело → try: _load_dashboard_components(period, period_state) except: error_alert

6. **Обновить `refresh_dashboard_after_crud` callback:**
   - Аналогично: State + _load_dashboard_components

7. **Обновить `update_period_state` callback:**
   - Расширить Store: `{"period": value, "year": today.year, "month": today.month}`

8. **Добавить `open_create_from_chart` callback:**
   - Input: daily-cashflow-chart clickData
   - State: dashboard-period data
   - Output: create-modal.is_open, preselected-date.data, modal-source.data
   - Guard: click_data is None → PreventUpdate
   - Guard: period != "month" → PreventUpdate
   - day = int(point["x"]), year/month из Store
   - Return: True, clicked_date.isoformat(), "chart"

9. **Обновить `transaction_modals.py`:**
   - В `set_preselection_on_modal_open()` добавить: if modal_source == "chart" → set date_value

10. **Импорты:**
    - `from app.services.dashboard_service import MONTH_NAMES_RU_SHORT`
    - `from app.schema.dashboard import MonthlyCashflowData, YearlyCashflowData`
    - `import plotly.graph_objects as go` (если ещё нет)

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/dashboard.py app/components/transaction_modals.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 5, Next Action: Шаг 5 — Финализация
5. Коммит: `git add . && git commit -m "feat(dashboard-ui): add cashflow charts and click-to-create [protocol-0022/04]"`
6. Push
