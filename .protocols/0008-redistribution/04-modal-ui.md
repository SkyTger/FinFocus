# Шаг 4: Redistribution Modal UI

## Briefing
- **Цель:** Создать модальное окно перераспределения с congratulation section, preview таблицей сравнения распределений и action buttons.
- **Ключевые файлы:**
  - `app/components/goals.py` (модифицировать — добавить модал и helper функции)
  - `app/assets/goals.css` (модифицировать — добавить стили)
- **Additional info:**
  - Модал должен показывать: название достигнутой цели, освободившийся бюджет, preview нового распределения
  - Кнопки: "Перераспределить" (confirm) и "Закрыть" (decline)
  - Spinner toggle для кнопки confirm во время обработки
  - CSS transition для плавного появления модала (fadeIn animation)
  - dcc.Store компоненты для хранения preview данных и состояния кнопки

## Sub-tasks

1. **Добавить dcc.Store компоненты в `create_goals_layout()`:**
   ```python
   dcc.Store(id="redistribution-preview-store", data=None),
   dcc.Store(id="redistribution-btn-disabled-store", data=False),
   ```

2. **Создать helper функцию `_build_redistribution_modal()`:**
   - Структура модала:
     ```
     Modal(id="redistribution-modal")
     ├── ModalHeader: "Цель достигнута!"
     ├── ModalBody
     │   ├── Congratulation section (название цели, сумма)
     │   ├── Freed budget display
     │   ├── Preview section (если есть remaining goals)
     │   │   └── Comparison table (old vs new allocation)
     │   └── Info message (если нет remaining goals)
     └── ModalFooter
         ├── Button "Перераспределить" (id="confirm-redistribution-btn")
         │   ├── Spinner (id="confirm-redistribution-spinner")
         │   └── Text (id="confirm-redistribution-text")
         └── Button "Закрыть" (id="decline-redistribution-btn")
     ```

3. **Создать helper функцию `_build_preview_section(preview_data)`:**
   - Таблица сравнения:
     | Цель | Было | Станет | Изменение |
   - Цветовая индикация: зеленый для увеличения
   - Итоговая строка: Total allocated
   - Обработка edge cases: no remaining goals, budget not set

4. **Добавить модал в `create_goals_layout()`:**
   - Вызвать `_build_redistribution_modal()`
   - Разместить после других модалов

5. **Добавить CSS стили в `app/assets/goals.css`:**
   ```css
   /* Redistribution Modal */
   .redistribution-modal .modal-content {
       animation: fadeIn 0.2s ease-in-out;
   }
   @keyframes fadeIn {
       from { opacity: 0; transform: translateY(-10px); }
       to { opacity: 1; transform: translateY(0); }
   }
   .redistribution-modal .congratulation-section { ... }
   .redistribution-modal .freed-budget { ... }
   .redistribution-modal .preview-table { ... }
   .redistribution-modal .spinner-border {
       margin-right: 8px;
       display: none; /* Hidden by default */
   }
   .redistribution-modal .change-positive { color: var(--bs-success); }
   ```

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи.

2. **Базовая проверка:**
   ```bash
   python -m py_compile app/components/goals.py
   ```

3. **Фиксация:**
   - **Добавь запись в `log.md`**: Описание UI компонентов модала.
   - **Обнови `context.md`**: Current Step = 5, Next Action для callbacks.
   - Проверь ветку main.

4. **Сделай коммит:**
   ```bash
   git add . && git commit -m "feat(goals): add redistribution modal UI [protocol-0008/04]"
   ```
   Сделай пуш.

5. **Отчет пользователю.**
