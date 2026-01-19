# Шаг 4: Интеграция и функциональное тестирование

## Briefing
- **Цель:** Интегрировать календарь с main.py (роутинг), провести функциональное тестирование всех сценариев.
- **Ключевые файлы:**
  - `app/main.py` (модифицировать — добавить роутинг /calendar)
  - `app/components/__init__.py` (модифицировать — добавить export)
- **Additional info:**
  - Порядок импортов критичен: сначала transactions, потом calendar
  - Тестирование включает: навигацию, создание операций, обновление после CRUD

## Sub-tasks

### 1. Обновить `app/components/__init__.py`

Добавить export:
```python
from app.components.calendar import create_calendar_layout
```

### 2. Обновить `app/main.py` — роутинг

Найти функцию `display_page()` и добавить обработку `/calendar`:

```python
from app.components.calendar import create_calendar_layout

@callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def display_page(pathname):
    """Роутинг страниц приложения."""
    if pathname == "/" or pathname == "/dashboard":
        return create_dashboard_layout()
    elif pathname == "/transactions":
        return create_transactions_layout()
    elif pathname == "/calendar":
        return create_calendar_layout()
    elif pathname == "/goals":
        return html.Div("Goals page - Coming soon")
    else:
        return html.Div("404 - Page not found")
```

### 3. Проверить порядок импортов

В `app/main.py` убедиться что imports идут в правильном порядке:
```python
# Components (порядок важен для регистрации callbacks!)
from app.components.sidebar import create_sidebar
from app.components.dashboard import create_dashboard_layout
from app.components.transactions import create_transactions_layout  # Сначала
from app.components.calendar import create_calendar_layout          # Потом
```

### 4. Обновить sidebar (опционально)

Если sidebar содержит ссылки на страницы, проверить что `/calendar` активируется корректно.

### 5. Функциональное тестирование

Запустить приложение и протестировать вручную:

```bash
cd /home/skytiger/PycharmProjects/worktrees/0002-cash-calendar
python run.py
```

**Тест-кейсы:**

#### TC-01: Загрузка календаря
1. Открыть http://localhost:8050/calendar
2. **Ожидание:** Календарь отображается с текущим месяцем
3. **Проверить:** Заголовок (месяц на русском), карточки статистики, сетка дней

#### TC-02: Навигация по месяцам
1. Нажать кнопку `<`
2. **Ожидание:** Отображается предыдущий месяц
3. Нажать кнопку `>`
4. **Ожидание:** Отображается следующий месяц
5. Нажать "Сегодня"
6. **Ожидание:** Возврат к текущему месяцу

#### TC-03: Ограничение +-12 месяцев
1. Навигировать на 12 месяцев назад
2. **Ожидание:** Кнопка `<` становится disabled
3. Навигировать на 12 месяцев вперед
4. **Ожидание:** Кнопка `>` становится disabled

#### TC-04: Клик по дню — открытие модала
1. Кликнуть на любой день текущего месяца
2. **Ожидание:** Открывается модал создания операции
3. **Проверить:** Дата предзаполнена выбранным днем

#### TC-05: Создание операции — обновление календаря
1. Открыть модал через клик по дню
2. Заполнить форму (сумма, тип, описание)
3. Нажать "Создать"
4. **Ожидание:** Модал закрывается, календарь обновляется
5. **Проверить:** Баланс на выбранный день изменился

#### TC-06: Отображение транзакций
1. Навести на день с транзакциями
2. **Ожидание:** Иконки (↓ доход, ↑ расход) отображаются
3. **Проверить:** Tooltip показывает детали

#### TC-07: Цвета балансов
1. Найти день с балансом > 5000
2. **Ожидание:** Баланс зеленый
3. Найти день с балансом < 5000 и > 0
4. **Ожидание:** Баланс желтый (warning)
5. Найти день с отрицательным балансом
6. **Ожидание:** Баланс красный

#### TC-08: Дни другого месяца
1. Посмотреть на дни в начале/конце сетки от соседних месяцев
2. **Ожидание:** Они отображаются с уменьшенной прозрачностью

### 6. Исправить найденные проблемы

Если тесты выявили проблемы — исправить и перетестировать.

## Workflow (Порядок работы)

1. **Выполнение:**
   - Обнови `app/components/__init__.py`
   - Обнови `app/main.py` — роутинг
   - Проведи функциональное тестирование

2. **Верификация:**
   ```bash
   black app/main.py app/components/__init__.py
   flake8 app/main.py app/components/__init__.py
   pytest tests/ -v  # Убедиться что ничего не сломали
   ```

3. **Фиксация:**
   - Добавь запись в `log.md` с результатами тестирования
   - Обнови `context.md`: `Current Step` → `5`

4. **Коммит:**
   ```bash
   git add .
   git commit -m "feat(calendar): integrate with main.py routing [protocol-0002/04]"
   git push
   ```

5. **Отчет пользователю.**

<формат_отчёта_о_шаге>
(Протокол 0002, шаг 4):

**Сделано**: интеграция с main.py, функциональное тестирование.

**Проверки**: black, flake8, pytest, функциональные тест-кейсы TC-01..TC-08.

**Git**: PR, ветка, коммит, main чистая.

**Рабочая папка**: /home/skytiger/PycharmProjects/worktrees/0002-cash-calendar

**Статус протокола**: Шаг 4 завершен, следующий — Шаг 5 (Финализация).
</формат_отчёта_о_шаге>
