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

*Решения нумеруются последовательно: D001, D002, D003...*
*Новые решения добавляются в хронологическом порядке*