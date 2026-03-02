# Шаг 4: Goals UI — таблица, модалы, callbacks

## Briefing

- **Цель:** Добавить кнопки Edit/Delete в таблицу взносов, создать модал редактирования с inline alert, модал подтверждения удаления с суммой/датой, и callbacks для всех операций
- **Ключевые файлы:**
  - `app/components/goals.py` — _build_contributions_table(), новые модалы, новые callbacks
  - `app/assets/` — CSS стили если нужны
- **Доп. информация:** См. `.design/solution-v4.md` секции "Delete confirmation modal", "Изменение 4: Detached state"

## Sub-tasks

1. **Расширить `_build_contributions_table()`:**
   - Добавить колонку "Действия"
   - Кнопки Edit (bi-pencil) и Delete (bi-trash) с Pattern-Matching IDs:
     ```python
     {"type": "contribution-edit-btn", "contribution_id": contrib.id}
     {"type": "contribution-delete-btn", "contribution_id": contrib.id}
     ```

2. **Создать `_build_edit_contribution_modal()`:**
   - dcc.Store("edit-contribution-id") для хранения ID
   - Поля: amount (InputGroup с ₽), date (DatePickerSingle), description (Input)
   - Inline dbc.Alert для ошибок валидации (модал остается открытым при ошибке)
   - Кнопки: Отмена, Сохранить

3. **Создать `_build_delete_contribution_confirm_modal()`:**
   - dcc.Store("delete-contribution-id") для хранения ID
   - dcc.Store("delete-contribution-info") для хранения суммы/даты
   - Динамический текст: "Удалить взнос {amount} ₽ от {date}?"
   - Подпись: "Это действие нельзя отменить."
   - Кнопки: Отмена, Удалить (danger)

4. **Интегрировать модалы в layout:**
   - Добавить оба модала в goals layout

5. **Callbacks (ADR-003 guard clauses во всех):**

   a. `open_edit_contribution_modal()`:
      - Input: Pattern-Matching clicks от contribution-edit-btn
      - Загрузить данные через GoalService.get_contribution_by_id()
      - Prefill поля формы
      - Output: modal is_open, поля формы, edit-contribution-id

   b. `submit_edit_contribution()`:
      - Input: клик Сохранить, значения полей, edit-contribution-id
      - Вызов GoalService.update_contribution()
      - При ошибке: показать inline alert, модал остается открытым
      - При успехе: закрыть модал, обновить таблицу
      - При status_changed: показать toast
      - **ВАЖНО detached state**: сохранить goal_name = result["goal"].name ВНУТРИ `with get_db_session()`

   c. `open_delete_contribution_modal()`:
      - Input: Pattern-Matching clicks от contribution-delete-btn
      - Заполнить message: "Удалить взнос {amount} ₽ от {date}?"
      - Сохранить contribution_id в Store

   d. `confirm_delete_contribution()`:
      - Input: клик Удалить, delete-contribution-id
      - Вызов GoalService.delete_contribution()
      - Закрыть модал, обновить таблицу
      - При status_changed: показать toast "Цель «{goal_name}» снова активна"
      - **ВАЖНО detached state**: goal_name из result["contribution_info"]["goal_name"]

6. **Toast для status change:**
   - Добавить dbc.Toast или использовать существующий механизм
   - Текст при откате: 'Цель "{goal_name}" снова активна'
   - Текст при completion: 'Цель "{goal_name}" достигнута!'

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/goals.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 5, Next Action: Шаг 5
5. Коммит: `git add . && git commit -m "feat(goals): add contribution edit/delete UI with modals and callbacks [protocol-0019/04]"`
6. Push
7. Отчёт
