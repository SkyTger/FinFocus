# Шаг 6: График полос + HTML-легенда с тултипами

## Briefing

- **Цель:** Собрать stacked-график на 45 дней с вехами целей, линией «сегодня» и маркером минимума; вынести легенду из поля графика и снабдить тултипами-пояснениями.
- **Ключевые файлы:**
  - `app/components/dashboard.py` — `build_layers_chart()`, `_build_layer_legend()`, `_build_payments_tooltip()`, `_build_reserve_tooltip()`, `_build_chart_empty_state()`, `_axis_tickvals()`
  - Эскиз: `.visual/finfocus-panel-dashboard/v3.html` (полосы, вехи, плашка минимума)
  - KB: `knowledge-bank/patterns/plotly-charts.md`
- **Источник правды:** solution-v4.md — докстринги `build_layers_chart`, `_axis_tickvals`; FR-3, FR-4, FR-6 в RTM.
- **Соответствует шагу 9 плана решения** (оценка 4 ч).

## Sub-tasks

1. **`build_layers_chart(data) -> dbc.Card`:**
   - Три `go.Bar` в `barmode="stack"`, порядок снизу вверх: free → payments → reserve
   - Цвета из `LAYER_COLORS`: `#2ecc71` / `#f0b775` / `#3498db`
   - Ось X — даты (`type="date"`), `tickmode="array"`, `tickvals=_axis_tickvals(...)`, `tickformat="%-d %b"`, `tickangle=0`
   - Ось Y: `rangemode="tozero"`, `tickformat=",.0f"`, `separatethousands=True` (против «50.001k»)
   - Вертикальная линия «сегодня»: `fig.add_shape` с `yref="paper"`, `dash="dash"`, подпись
   - Маркер минимума на `data['min_free_date']` + аннотация `format_rub(data['min_free'])` **со сдвигом** (`yshift`/`ay`) — не вплотную к тику даты (заметка vision-критика)
   - Вехи целей: аннотации по `data['milestones']`, ≤3 в окне + одна `beyond_window` стрелкой у правого края
   - `showlegend=False` — легенда Plotly отключена, вынесена в HTML
   - `id="dashboard-layers-chart-graph"`

2. **`_axis_tickvals(window_dates) -> list[date]`:**
   - `k = max(1, ceil(len(window_dates) / MAX_X_TICKS))`; для 45 дней `k = 5` → 9 подписей
   - Плюс принудительно `window_end`, **если он не попал в сетку** (замечание критики v4 №1: на коротком окне `k = 1`, и последняя дата уже в сетке — иначе дубль подписи)
   - Итог для 45 дней: 10 подписей, `<= MAX_X_TICKS` по построению
   - Первая подпись — `reference_date`, последняя — `window_end`

3. **`_build_layer_legend(data)`** — HTML-легенда **вне поля графика**: три элемента (цветной квадрат + подпись из `LAYER_LABELS`), каждый с `tabIndex=0` и `dbc.Tooltip(trigger="hover focus")`.

4. **`_build_payments_tooltip(data)`** — список конкретных платежей: «{описание} · {дата} · {сумма}» из `data['upcoming_payments']`, до 8 строк + «и ещё N». Пустой случай — объясняющий текст («до конца месяца платежей больше нет»), не пустой тултип.

5. **`_build_reserve_tooltip(data)`** — **честная подпись по факту дня** (решение владельца п. 3б):
   - Полоса не сжата (`today['reserve'] == reserve_configured_today`): «Порог подушки {cushion_threshold} + бюджет целей {goals_reserve_today}»
   - Полоса сжата: «В этот день на резерв остаётся {reserve} из {reserve_configured} — вы залезаете в подушку»
   - Цифра тултипа **всегда** равна высоте полосы
   - При `degraded` — не утверждать состав слоя

6. **Тултип «Свободно»**: «Остаток минус платежи до конца месяца и резерв».

7. **`_build_chart_empty_state()`** — при `data['is_empty']` отдавать `html.Div` **вместо `dcc.Graph`**: Plotly не вызывается вовсе → оси −1..1 физически невозможны (AC-5).

8. **Безопасность:** пользовательский `description` в тултипе — только через `html.Div`/`html.Span`. `dangerously_allow_html` и `dcc.Markdown` в новых путях **запрещены**.

## Проверки шага

- `python -m py_compile app/components/dashboard.py`
- Визуально на наполненной базе: три полосы видны, все ненулевые; линия «сегодня» у левого края; маркер минимума не липнет к тику; вехи целей в кадре
- **Подписей на оси не больше 11** (для 45 дней — 10); первая == сегодня, последняя == правый край; склеек нет; дубля последней подписи нет
- Hover и **Tab-фокус** на легенде «Платежи» → список платежей с датами; на «Резерв» → состав по факту дня
- Чистая база: в DOM **нет** `dcc.Graph` от графика слоёв
- База с историей и пустым окном → **график рисуется** (плоская стопка), пустое состояние его не подменяет
- `.venv/bin/pytest -q` — прежние зелёные
- `.venv/bin/black` + `.venv/bin/flake8 --select=F` — чисто

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile {FILES}`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 7, Next Action: Шаг 7
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(dashboard): график полос свободно/платежи/резерв + легенда с тултипами [protocol-0028/06]"`
7. Push
8. Отчёт
