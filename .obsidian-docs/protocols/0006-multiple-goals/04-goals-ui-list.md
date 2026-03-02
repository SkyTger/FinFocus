# Шаг 4: Goals UI — список целей

## Briefing
- **Цель:** Рефакторинг Goals UI для отображения списка карточек целей вместо одной карточки. Добавить сводную секцию и info-alert для budget_not_set.
- **Ключевые файлы:**
  - `app/components/goals.py` (изменить)
  - `app/assets/goals.css` (изменить)
- **Additional info:**
  - Текущий UI показывает одну карточку или empty state
  - Нужно: список карточек с сортировкой по priority
  - Каждая карточка: название, прогресс-бар, allocated_amount, дедлайн, кнопки ↑↓
  - Сводная секция вверху: общий прогресс, общий бюджет, статус распределения
  - Info-alert если monthly_savings_budget = 0
  - В этом шаге ТОЛЬКО layout, без callbacks для кнопок приоритетов

## Sub-tasks

1. **Изучить текущий UI** в `app/components/goals.py`:
   - Понять структуру `create_goals_layout()`
   - Понять `_build_goal_card()` и `_build_empty_state()`

2. **Создать функцию `_build_summary_section()`**:
   ```python
   def _build_summary_section(
       goals_summary: GoalsSummary,
       allocation_summary: AllocationSummary,
   ) -> dbc.Card:
       """Строит сводную секцию с общим прогрессом и статусом распределения."""
   ```
   Содержимое:
   - Общий прогресс: `{total_current} / {total_target} ({progress}%)`
   - Бюджет накоплений: `{monthly_budget}` (или "Не настроен")
   - Статус распределения: "Все цели профинансированы" или "Недостаток: {shortfall}"
   - Кнопка "Настроить бюджет" (id="open-budget-modal-btn")

3. **Создать функцию `_build_budget_alert()`**:
   ```python
   def _build_budget_alert() -> dbc.Alert:
       """Строит info-alert с призывом настроить бюджет."""
   ```
   Текст: "Бюджет накоплений не настроен. Настройте его для получения рекомендаций по взносам."
   Color: "info", dismissable: True

4. **Переписать `_build_goal_card()`** для поддержки списка:
   - Добавить отображение `allocated_amount` (если есть)
   - Добавить allocation_status badge ("Полностью", "Частично", "Не профинансирована")
   - Добавить кнопки ↑ и ↓ для приоритетов (id pattern: `{"type": "priority-up-btn", "index": goal_id}`)
   - Добавить отображение номера приоритета

5. **Переписать `_build_goals_list()`** (новая функция):
   ```python
   def _build_goals_list(goals: list[Goal], allocation_results: dict[int, AllocationResult]) -> html.Div:
       """Строит список карточек целей."""
   ```
   - Сортировка по priority
   - Вызов `_build_goal_card()` для каждой цели
   - Передача allocation_result в каждую карточку

6. **Обновить `create_goals_layout()`**:
   - Загрузка всех целей (не только первой)
   - Загрузка бюджета через `GoalService.get_savings_budget()`
   - Расчет allocation через `AllocationService.calculate_allocation()`
   - Построение layout:
     1. Summary section (если есть цели)
     2. Budget alert (если budget_not_set)
     3. Goals list или Empty state
     4. Create button
     5. Модалы (существующие)

7. **Обновить стили** в `app/assets/goals.css`:
   - `.goals-list` — контейнер для списка карточек
   - `.goal-card-priority` — badge с номером приоритета
   - `.goal-card-allocation` — секция с allocated_amount
   - `.priority-btn` — стили кнопок ↑↓
   - `.summary-section` — стили сводной секции
   - `.budget-alert` — стили info-alert

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-7.

2. **Верификация:**
   ```bash
   black app/components/goals.py
   flake8 app/components/goals.py
   # Визуальная проверка: запустить приложение и открыть /goals
   python run.py
   pytest tests/ -v
   ```

3. **Фиксация:**
   - Добавь запись в `log.md`
   - Обнови `context.md`: `Current Step` = 5
   - Проверь ветку main

4. **Коммит:**
   ```bash
   git add .
   git commit -m "feat(ui): refactor Goals UI for multiple goals list [protocol-0006/04]"
   git push
   ```

5. **Отчет пользователю.**
