# Decisions - Epic 01: Core MVP

История принятых решений для эпика Core MVP (только критичные архитектурные решения).

---

## D001: SQLAlchemy ORM для доменной модели (2025-01-27)

Выбрана ORM SQLAlchemy для моделирования бизнес-доменов вместо прямого SQL.

**КРИТИЧНО**:
- **Модели**: User, Transaction, Goal, GoalContribution
- **Типы транзакций**: INCOME (доход), EXPENSE (расход), TRANSFER (перевод)
- **Статусы целей**: ACTIVE (активная), COMPLETED (достигнута), PAUSED (приостановлена)
- **Терминология**:
  - Transaction (операция) → финансовая операция любого типа
  - Goal (цель) → накопительная цель с target_amount
  - GoalContribution (взнос) → добавление средств в цель
- **Precision**: Decimal(10, 2) для всех денежных полей (точность до копеек)
- **Relationships**: Cascade delete для зависимых сущностей (transactions, goals, contributions)

Файлы: `app/models/database.py`

---

## D002: SQLite для разработки, PostgreSQL для production (2025-01-27)

База данных SQLite выбрана для локальной разработки с миграцией на PostgreSQL для production.

**КРИТИЧНО**:
- **Database URL**: `sqlite:///data/finfocus.db` (локация по умолчанию)
- **Автоматическая инициализация**: `init_database()` создает таблицы при старте
- **Migration path**: Готовность к переходу на PostgreSQL без изменения кода
- **Session management**: sessionmaker для транзакционности операций

Файлы: `app/models/database.py`, `run.py`

---

## D003: Dash + Plotly для frontend стека (2025-01-27)

Dash выбран как фреймворк для построения интерактивного веб-приложения с Python.

**КРИТИЧНО - Технологический стек**:
- **Frontend**: Dash 2.17.1 (React-based Python framework)
- **UI Components**: Dash Bootstrap Components 1.5.0 (dbc)
- **Visualization**: Plotly 5.17.0 (интерактивные графики)
- **Styling**: Bootstrap Grid + кастомные CSS стили
- **Theme**: Зелено-белая палитра (#28a745 primary color)
- **Routing**: URL-based routing в `app/main.py` (callback на `dcc.Location`)
- **Architecture**: Multi-page application с модульными компонентами

**Преимущества**:
- Нативная интеграция Python + визуализация данных
- Быстрая разработка UI без JavaScript фреймворков
- Мощные интерактивные графики Plotly из коробки

Файлы: `app/main.py`, `requirements.txt`, `app/assets/custom.css`

---

## D004: Модульная архитектура приложения (2025-01-27)

Принята модульная структура проекта с разделением по ответственности.

**КРИТИЧНО - Структура проекта**:
```
app/
├── main.py              # Dash app, routing, layout orchestration
├── models/              # SQLAlchemy ORM models
│   └── database.py      # User, Transaction, Goal, GoalContribution
├── components/          # Reusable UI components
│   ├── dashboard.py     # Dashboard с карточками и графиками
│   └── sidebar.py       # Навигация
├── services/            # Business logic (будущее)
└── assets/              # Static files (CSS, images)
    └── custom.css       # Кастомные стили
```

**Принципы**:
- **Separation of Concerns**: UI компоненты отделены от бизнес-логики
- **Reusability**: Компоненты переиспользуются между страницами
- **Scalability**: Готовность к добавлению новых модулей без рефакторинга

Файлы: структура `app/`

---

## D005: Calculated properties для Goal модели (2025-01-27)

Прогресс цели рассчитывается через @property вместо хранения в БД.

**КРИТИЧНО - Формулы расчета**:
- **progress_percentage**: `(current_amount / target_amount) × 100`
- **is_completed**: `current_amount >= target_amount` (boolean)
- **monthly_contribution**: Рассчитывается на основе:
  - Остаток: `target_amount - current_amount`
  - Месяцев до цели: `(target_date - today).months`
  - Формула: `остаток / количество_месяцев`

**Преимущества**:
- Всегда актуальные данные без риска рассинхронизации
- Упрощение обновления при изменении current_amount
- Возможность изменить логику расчета без миграции БД

Файлы: `app/models/database.py:105-118`

---

## D006: Dash Bootstrap для UI компонентов (2025-01-27)

Bootstrap Grid и компоненты dbc выбраны для быстрой разработки адаптивного UI.

**КРИТИЧНО - UI паттерны**:
- **Layout**: `dbc.Container` > `dbc.Row` > `dbc.Col` (responsive grid)
- **Cards**: `dbc.Card` для карточек показателей и блоков контента
- **Navigation**: `dbc.Nav` + `dbc.NavLink` для sidebar
- **Icons**: Bootstrap Icons (CDN в `app/main.py`)
- **Breakpoints**: xs/sm/md/lg/xl для адаптивности
- **Styling**: Кастомные классы поверх Bootstrap базы

**Advantage**:
- Готовая адаптивность из коробки
- Консистентный дизайн
- Быстрая разработка UI без глубокого CSS

Файлы: `app/components/dashboard.py`, `app/components/sidebar.py`, `app/assets/custom.css`

---

## D007: Роутинг через URL pathname callbacks (2025-01-27)

Навигация реализована через Dash callbacks на изменение URL pathname.

**КРИТИЧНО - Routing паттерн**:
```python
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/' or pathname == '/dashboard':
        return dashboard_layout()
    elif pathname == '/calendar':
        return calendar_layout()
    # ...
```

**URL структура**:
- `/` или `/dashboard` → Dashboard overview
- `/calendar` → Кассовый календарь
- `/goals` → Управление целями
- `/transactions` → Список операций

**Преимущества**:
- Clean URLs для пользователей
- Поддержка browser history (назад/вперед)
- Возможность прямых ссылок на страницы

Файлы: `app/main.py:50-70`

---

## D008: Guard Clauses в Goal.monthly_contribution

**Дата**: 2025/01/27
**Контекст**: QA-review обнаружил риск division by zero в расчёте ежемесячного взноса
**Решение**: Реализовать defensive programming с guard clauses

**Реализация**:
- Вернуть 0 если target_date в прошлом или сегодня
- Вернуть 0 если цель уже достигнута (current >= target)
- Использовать max(days_remaining / 30, 1) для предотвращения деления на 0

**Обоснование**:
- Предотвращает runtime errors
- Даёт понятное поведение для edge cases
- Соответствует принципу fail-safe

**Альтернативы**:
- Выбрасывать исключение → Отклонено (слишком агрессивно для @property)
- Вернуть None → Отклонено (Decimal('0') более явный для денежных расчётов)

**Статус**: ✅ Реализовано (Commit 8cc98e2)

---

## D009: Ограничение одной активной цели в MVP

**Дата**: 2025/01/27
**Контекст**: Необходимо упростить MVP, отложив множественные цели на Batch 2
**Решение**: GoalService.create_goal() проверяет наличие активной цели у пользователя

**Реализация**:
```python
active_goals_count = session.query(Goal).filter_by(
    user_id=user_id,
    status=GoalStatus.ACTIVE
).count()

if active_goals_count >= 1:
    raise ValidationError(
        "В MVP версии можно иметь только одну активную цель. "
        "Завершите или удалите текущую цель перед созданием новой."
    )
```

**Обоснование**:
- Упрощает логику кассового календаря для MVP
- Снижает complexity Фазы 2-3
- Пользователи могут паузить/завершить цель для создания новой

**КРИТИЧНО**: Это временное ограничение MVP! В Batch 2 добавим:
- Множественные цели с приоритетами
- Перераспределение средств между целями
- Стратегии накопления (свободный/средний/строгий режимы)

**Статус**: ✅ Реализовано (Commit 8cc98e2)
**Снять в**: Batch 2 (Enhanced Planning)

---

## D010: Session Management Pattern в Сервисном слое

**Дата**: 2025/01/27
**Контекст**: Необходимо определить, кто управляет транзакциями БД
**Решение**: Сервисы используют session.flush(), caller управляет commit/rollback

**Реализация**:
- TransactionService и GoalService принимают session через __init__
- Методы используют session.flush() вместо commit
- Caller (UI/API) ответственен за commit/rollback
- Позволяет объединять несколько операций в одну транзакцию

**Пример**:
```python
# UI layer
session = get_session(engine)
try:
    transaction_service = TransactionService(session)
    goal_service = GoalService(session)

    # Создаём транзакцию и добавляем взнос в одной транзакции
    transaction = transaction_service.create_transaction(...)
    goal_service.add_contribution(...)

    session.commit()  # Caller управляет коммитом
except Exception:
    session.rollback()
    raise
finally:
    session.close()
```

**Обоснование**:
- Больше гибкости для сложных бизнес-операций
- Соответствует Unit of Work pattern
- Упрощает тестирование (можно роллбэчить после теста)

**Trade-offs**:
- Caller должен помнить про commit/rollback
- Риск забыть закрыть сессию → Требует finally блоков

**Статус**: ✅ Реализовано (Commit 1211796)

---

## D011: Корневая причина регрессии Edit/Delete кнопок (2025-11-03)

Code review выявил критические ошибки в логике Pattern-Matching Callbacks после исправления автоудаления операций.

**КРИТИЧНО - Найденные проблемы**:
1. **Неправильный поиск индекса**: Код ищет `clicked_idx` в `ctx.inputs_list[0]` по `index`, но использует найденный индекс для доступа к `n_clicks_list` - порядок элементов может не совпадать (вероятность 95%)
2. **Избыточная проверка n_clicks**: При `prevent_initial_call=True` и валидном `triggered_id` проверка `is None` не нужна - Dash гарантирует срабатывание только при реальных событиях
3. **Неизвестная структура данных**: Реальная структура `ctx.inputs_list[0]` может отличаться от предполагаемой - требуется runtime debugging

**План решения**:
- Фаза 1: Runtime debugging для проверки структуры `ctx.triggered_id` и `ctx.inputs_list`
- Фаза 2: Упростить логику - использовать только `triggered_id["index"]` без поиска в списках, убрать проверку `n_clicks is None`
- Фаза 3: Тестирование всех операций (создание, редактирование, удаление)

**Статус**: 🔍 Диагностика завершена, требуется runtime debugging для валидации

Файлы: `app/components/transactions.py:463-514`, `app/components/transactions.py:642-755`

---

*Решения нумеруются последовательно: D001, D002, D003...*
*Новые решения добавляются в хронологическом порядке*