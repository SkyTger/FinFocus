# Шаг 4: Стили и интеграция

## Briefing
- **Цель:** Создать CSS стили для Goals UI и интегрировать компонент в роутинг main.py.
- **Ключевые файлы:**
  - `app/assets/goals.css` (создать)
  - `app/main.py` (модифицировать)
- **Additional info:**
  - Использовать паттерны из calendar.css
  - Адаптивность для mobile (768px, 576px breakpoints)
  - Порядок импортов в main.py не критичен (goals.py не зависит от других callbacks)

## Sub-tasks

### 4.1 Создать CSS стили

1. **Создать `app/assets/goals.css` (~120-150 строк):**

```css
/* ============================================
   GOALS UI STYLES
   ============================================ */

/* === GOAL CARD === */
.goal-card {
    border: none;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    border-radius: 12px;
}

.goal-card .card-header {
    background: linear-gradient(135deg, #198754 0%, #157347 100%);
    color: white;
    border-radius: 12px 12px 0 0;
    padding: 1.25rem;
}

.goal-card .card-header h4 {
    color: white;
}

.goal-card .card-header small {
    color: rgba(255, 255, 255, 0.85);
}

.goal-card .card-body {
    padding: 1.5rem;
}

/* === PROGRESS BAR === */
.goal-progress-container {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
}

.goal-progress {
    border-radius: 12px;
    background-color: #e9ecef;
}

.goal-progress .progress-bar {
    border-radius: 12px;
    font-weight: 600;
    font-size: 0.875rem;
}

/* === METRICS CARDS === */
.goal-metric-card {
    border: none;
    background: #f8f9fa;
    border-radius: 8px;
    text-align: center;
}

.goal-metric-card .card-body {
    padding: 1rem;
}

.goal-metric-card h5 {
    font-size: 1.1rem;
}

/* === EMPTY STATE === */
.goal-empty-state {
    border: 2px dashed #dee2e6;
    border-radius: 12px;
    background: #f8f9fa;
}

.goal-empty-state .card-body {
    padding: 3rem 1.5rem;
}

.goal-empty-icon {
    color: #6c757d;
    font-size: 4rem;
}

/* === CONTRIBUTIONS TABLE === */
.contributions-table {
    margin-bottom: 0;
}

.contributions-table th {
    background: #f8f9fa;
    font-weight: 600;
    color: #495057;
    border-bottom: 2px solid #dee2e6;
}

.contributions-table td {
    vertical-align: middle;
    padding: 0.75rem;
}

/* === BUTTON GROUPS === */
.goals-container .btn-group .btn {
    border-radius: 6px !important;
    margin-left: 4px;
}

.goals-container .btn-group .btn:first-child {
    margin-left: 0;
}

/* === MODALS === */
.goals-container .modal-content {
    border-radius: 12px;
    border: none;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
}

.goals-container .modal-header {
    border-bottom: 1px solid #e9ecef;
    padding: 1.25rem 1.5rem;
}

.goals-container .modal-body {
    padding: 1.5rem;
}

.goals-container .modal-footer {
    border-top: 1px solid #e9ecef;
    padding: 1rem 1.5rem;
}

/* Date Picker Styling */
.goals-container .DateInput_input {
    border: 1px solid #ced4da;
    border-radius: 0.375rem;
    padding: 0.375rem 0.75rem;
    font-size: 1rem;
}

.goals-container .DateInput_input:focus {
    border-color: #86b7fe;
    outline: 0;
    box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
}

/* === ALERTS === */
.goals-container .alert {
    border-radius: 8px;
    border: none;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* === RESPONSIVE === */
@media (max-width: 768px) {
    .goal-card .card-header {
        padding: 1rem;
    }

    .goal-card .card-body {
        padding: 1rem;
    }

    .goal-metric-card .card-body {
        padding: 0.75rem;
    }

    .goal-metric-card h5 {
        font-size: 0.95rem;
    }

    .goals-container .btn-group {
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .goals-container .btn-group .btn {
        margin-left: 0;
    }
}

@media (max-width: 576px) {
    .goal-empty-state .card-body {
        padding: 2rem 1rem;
    }

    .goal-progress-container {
        padding: 0.75rem;
    }

    .goal-progress {
        height: 20px !important;
    }

    .contributions-table {
        font-size: 0.875rem;
    }
}
```

### 4.2 Интегрировать в main.py

2. **Модифицировать `app/main.py`:**

**Добавить импорт (после строки 15):**
```python
from app.components.goals import create_goals_layout  # После calendar
```

**Заменить заглушку в роутинге (строки 91-95):**

Было:
```python
elif pathname == "/goals":
    # Накопительные цели (пока заглушка)
    return html.Div(
        [html.H2("Накопительные цели"), html.P("Здесь будут цели накоплений")]
    ), create_page_header("Цели", "Накопительные цели")
```

Стало:
```python
elif pathname == "/goals":
    # Накопительные цели
    return create_goals_layout(), create_page_header(
        "Цели", "Накопительные цели"
    )
```

### 4.3 Ручное тестирование

3. **Запустить приложение и проверить:**

```bash
cd /home/skytiger/PycharmProjects/worktrees/0004-goals-ui
python run.py
```

**Проверить в браузере (http://localhost:8050/goals):**

- [ ] Страница загружается без ошибок
- [ ] Empty state отображается корректно (если нет целей)
- [ ] Кнопка "Создать цель" видна
- [ ] Модал создания открывается/закрывается
- [ ] Стили применяются корректно
- [ ] Адаптивность работает (изменить размер окна)

**Если есть цель в БД:**
- [ ] Карточка цели отображается
- [ ] Прогресс-бар работает
- [ ] Метрики показываются
- [ ] Кнопки действий активны

## Workflow (Порядок работы)

1.  **Выполнение:** Выполни подзадачи 4.1-4.3.
2.  **Верификация:**
    - `black app/main.py`
    - `flake8 app/main.py app/assets/`
    - Запуск приложения и ручная проверка UI
3.  **Фиксация:**
    - **Добавь запись в `log.md`**
    - **Обнови `context.md`**: `Current Step` = 5
4.  **Сделай коммит:** `git commit -m "feat(goals): add styles and integrate routing [protocol-0004/04]"`. Push.
5.  **Отчет пользователю.**
