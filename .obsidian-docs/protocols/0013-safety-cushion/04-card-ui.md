# Шаг 4: Карточка UI

## Briefing

- **Цель:** Реализовать карточку подушки на странице /goals (два состояния)
- **Ключевые файлы:**
  - `app/components/goals.py` — MODIFY
- **Доп. информация:** Карточка над блоком бюджета, состояния: "Не настроена" и "Настроена"

## Sub-tasks

1. **Добавить функцию `_build_cushion_card()`:**
   ```python
   def _build_cushion_card(settings: CushionSettings | None) -> dbc.Card:
       """Карточка финансовой подушки.

       Два состояния:
       - Не настроена (target=0): приглашение + кнопка "Настроить"
       - Настроена (target>0): цель, текущая сумма, прогресс-бар с маркером порога
       """
       if not settings or not settings.get("is_configured"):
           # Состояние "Не настроена"
           return dbc.Card([
               dbc.CardBody([
                   html.H5("Финансовая подушка", className="cushion-title"),
                   html.P("Создайте резервный фонд для непредвиденных расходов"),
                   dbc.Button("Настроить", id="cushion-setup-btn", color="primary")
               ])
           ], className="cushion-card cushion-not-configured")
       else:
           # Состояние "Настроена"
           # Прогресс-бар с маркером порога
           ...
   ```

2. **Добавить dcc.Store для состояния:**
   ```python
   dcc.Store(id="cushion-settings-store", data=None)
   dcc.Store(id="cushion-refresh-trigger", data=0)
   ```

3. **Интегрировать в layout goals:**
   - Карточка вверху страницы, над блоком бюджета
   - Добавить кнопки "Настроить" / "Изменить" с ID

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка: `python -m py_compile app/components/goals.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 5
5. Коммит: `git add . && git commit -m "feat(ui): add cushion card to goals page [protocol-0013/04]"`
6. Push
7. Отчёт
