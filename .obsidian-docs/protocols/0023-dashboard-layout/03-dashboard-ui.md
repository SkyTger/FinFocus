# Шаг 3: Dashboard UI rebuild

## Briefing

- **Цель:** Перестроить Dashboard layout: split таблиц 50/50, cushion readonly card, пустые состояния, обновить callbacks (6 outputs)
- **Ключевые файлы:**
  - `app/components/dashboard.py` — основная перестройка
- **Доп. информация:** Solution v3 Steps 6-7, 10. Layout 8/4 сохранен. format_date_human() для дат. Recurring icon 🔁 для instances. _build_cushion_card_readonly() вызывает CushionService напрямую (не goals.py).

## Sub-tasks

1. **_build_empty_state()** — новая функция:
   - icon (bi-inbox), message, button_id
   - Возвращает html.Div с центрированным содержимым

2. **_build_transactions_split_table()** — новая функция:
   - Принимает transactions, title, empty_message, link_text, link_href, empty_btn_id
   - Формат строки: format_date_human() для даты, описание + категория во 2-ю строку, amount RIGHT, 🔁 для recurring
   - Без "Completed" бейджей
   - Ссылка "Все операции" внизу карточки

3. **_build_cushion_card_readonly()** — новая функция:
   - Вызывает CushionService.get_settings(user_id) с try/except
   - Рендерит упрощенную карточку: заголовок, статус, суммы, прогресс-бар
   - dcc.Link("Настройки", href="/goals") вместо кнопки
   - Fallback: "Подушка не настроена"

4. **create_dashboard_layout()** перестройка:
   - dbc.Row: Col width=8 (KPI + Chart + split tables), Col width=4 (wishlist + cushion + stats)
   - Добавить html.Div(id="dashboard-upcoming-transactions")
   - Добавить html.Div(id="dashboard-cushion-card")

5. **_load_dashboard_components()** расширение:
   - Загрузить upcoming transactions через get_upcoming_transactions()
   - Загрузить cushion card через _build_cushion_card_readonly()
   - Возвращать 6 outputs: cards, chart, stats, recent, upcoming, cushion
   - Ссылки "Все операции" с ?start=&end= query params

6. **load_dashboard_data** и **refresh_dashboard_after_crud** — обновить:
   - 6 Outputs вместо текущих (добавить upcoming + cushion)

7. **open_create_from_empty()** — новый callback:
   - 2 Inputs: empty-recent-add-btn, empty-upcoming-add-btn
   - Output: create-modal.is_open + modal-source

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/dashboard.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 4, Next Action: Шаг 4
5. Коммит: `git add . && git commit -m "feat(dashboard): rebuild layout with split tables and cushion card [protocol-0023/03]"`
6. Push
7. Отчёт
