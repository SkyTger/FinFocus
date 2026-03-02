# Спецификация: Quick-add Chips

**Версия**: 1.0
**Дата**: 2026-01-25
**Статус**: Утверждено
**Эпик**: Epic-04 Advanced Features

---

## 1. Бизнес-контекст

### Проблема
После Батча 3 (Analytics & UX) пользователи могут быстро категоризировать операции через chips, но создание новых операций всё ещё требует:
1. Открыть модал создания
2. Выбрать тип (доход/расход)
3. Выбрать категорию из dropdown
4. Ввести сумму
5. Ввести описание
6. Кликнуть "Создать"

**Итого: 6 шагов** для частых операций типа "Кофе — 150₽" или "Продукты — 2500₽".

### Решение
Добавить **Quick-add chips** на страницу Transactions:
- **Фаза A (Протокол A)**: Чипы категорий — клик открывает модал с предвыбранной категорией (3-4 шага)
- **Фаза B (Протокол B)**: Шаблоны операций — 1-клик создание с toast "Отменить" (1-2 шага)

### Бизнес-метрики
- Время добавления частой операции: **< 5 секунд** (сейчас ~20-30 сек)
- Retention rate: **+15%** (снижение friction при ежедневном использовании)
- Adoption: **70%** пользователей используют chips вместо полной формы

---

## 2. Два понятия: Чипы категорий vs Шаблоны операций

### 2.1 Чипы категорий (Протокол A)

**Что это**: Кнопки быстрого доступа к частым категориям

**Как работает**:
1. Пользователь кликает "Продукты"
2. Открывается модал создания операции
3. Категория предвыбрана: "Еда и продукты"
4. Пользователь вводит сумму и описание
5. Кликает "Создать"

**Итого: 4 шага** (вместо 6)

**Дефолтные чипы**:
- **Расход (5)**: Продукты, Дом/Жильё, Транспорт/Авто, Связь/Коммуналка, Развлечения/Кафе
- **Доход (2)**: Зарплата, Аванс/Подработка

**Хранение**: Hardcoded в UI (Протокол A), позже PinnedCategory модель (Протокол B)

### 2.2 Шаблоны операций (Протокол B)

**Что это**: Сохраненные операции с предзаполненными полями (amount, description, category)

**Как работает**:
1. Пользователь кликает "Кофе — 150₽"
2. Операция создается мгновенно (без модала!)
3. Toast notification: "Кофе — 150₽ добавлено [Отменить]" (3 сек)
4. Если клик "Отменить" → операция удаляется
5. Если timeout → операция сохраняется

**Итого: 1-2 шага** (идеально для ежедневного ввода)

**Примеры шаблонов**:
- "Кофе — 150₽" (категория: Еда)
- "Обед в офисе — 350₽" (категория: Еда)
- "Метро — 70₽" (категория: Транспорт)
- "Зарплата Январь" (категория: Зарплата, amount: None → требует ввода)

**Хранение**: Template модель (user_id, category_id, amount, description, name, sort_order, is_archived)

---

## 3. Scope разбивки

### Протокол A: Чипы категорий (~6-8 дней)

**Входит в scope**:
- [x] UI: плитки с иконками (7 дефолтных чипов)
- [x] Группировка: "Расход" (5 чипов) и "Доход" (2 чипа)
- [x] Клик на chip → модал создания с предвыбранной категорией
- [x] Кнопка "Ещё..." для полного списка категорий
- [x] Расположение: страница Transactions, под "Экспорт" и "Добавить"
- [x] CSS стили: плитки крупнее чем chips категоризации из Батча 3.2
- [x] Адаптивность: 2 ряда на desktop, 1 ряд + scroll на mobile

**НЕ входит в Протокол A**:
- ❌ PinnedCategory модель (появится в Протоколе B)
- ❌ Кастомизация списка чипов (появится в Протоколе B)
- ❌ Шаблоны операций (появится в Протоколе B)

### Протокол B: Шаблоны операций (~6-8 дней)

**Входит в scope**:
- [x] Template модель (миграция БД)
- [x] PinnedCategory модель (миграция БД)
- [x] TemplateService и PinnedCategoryService (CRUD)
- [x] UI: создание шаблона ("⋯" меню → "Сохранить как шаблон")
- [x] UI: 1-клик создание операции из шаблона
- [x] Toast notification с кнопкой "Отменить" (3 сек)
- [x] Управление шаблонами: редактирование/архивирование/порядок
- [x] Кнопки ↑↓ для изменения порядка (или "В начало")
- [x] Модал "Архив шаблонов" (восстановление архивированных)
- [x] Миграция дефолтных чипов → PinnedCategory (seed script)

**НЕ входит в Протокол B**:
- ❌ Drag-and-drop для порядка (сложность высокая, оставляем кнопки ↑↓)
- ❌ Автоматическое создание шаблонов (ML на основе повторяющихся операций)
- ❌ Экспорт/импорт шаблонов (post-MVP)

---

## 4. UI Концепция

### 4.1 Расположение на странице Transactions

```
┌──────────────────────────────────────────────────────────────┐
│ Операции                                  [Экспорт] [Добавить]│
├──────────────────────────────────────────────────────────────┤
│ Быстрое создание                                             │
│                                                              │
│ [Расход]                                                     │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────┐ │
│ │ [🛒]        │ │ [🏠]        │ │ [🚗]        │ │        │ │
│ │ Продукты    │ │ Дом         │ │ Транспорт   │ │ Ещё... │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └────────┘ │
│ ┌─────────────┐ ┌─────────────┐                             │
│ │ [📱]        │ │ [☕]         │                             │
│ │ Связь       │ │ Развлечения │                             │
│ └─────────────┘ └─────────────┘                             │
│                                                              │
│ [Доход]                                                      │
│ ┌─────────────┐ ┌─────────────┐ ┌────────┐                  │
│ │ [💼]        │ │ [💵]        │ │        │                  │
│ │ Зарплата    │ │ Подработка  │ │ Ещё... │                  │
│ └─────────────┘ └─────────────┘ └────────┘                  │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ История операций                                             │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 25.01  Расход  -1 500₽  Кофейня на углу  [Еда]        │   │
│ └────────────────────────────────────────────────────────┘   │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 24.01  Расход  -3 200₽  Яндекс.Такси   [Транспорт]    │   │
│ └────────────────────────────────────────────────────────┘   │
```

### 4.2 Визуальный дизайн чипа

**Протокол A (чипы категорий)**:
```
┌─────────────────┐
│   [🛒]          │  ← Иконка категории (Bootstrap Icon)
│                 │
│   Продукты      │  ← Название категории
└─────────────────┘
    100-120px
```

**Протокол B (шаблоны операций)**:
```
┌─────────────────┐
│ [☕] [⋯]        │  ← Иконка категории + меню управления (hover)
│                 │
│ Кофе            │  ← Название шаблона
│ 150₽            │  ← Сумма (если задана)
└─────────────────┘
    100-120px
```

### 4.3 Модал "Ещё..." (полный список категорий)

```
┌───────────────────────────────────────────────────┐
│ Выберите категорию                      [×]       │
├───────────────────────────────────────────────────┤
│ Расход                                            │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│ │ 🛒 Еда   │ │ 🚗 Авто  │ │ 🏠 Жильё │  ...      │
│ └──────────┘ └──────────┘ └──────────┘           │
│ ┌──────────┐ ┌──────────┐                        │
│ │ 💊 Здоров│ │ 🎓 Образ │  ...                   │
│ └──────────┘ └──────────┘                        │
│                                                   │
│ Доход                                             │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│ │ 💼 Зарп  │ │ 💵 Подра │ │ 📈 Инвес │  ...      │
│ └──────────┘ └──────────┘ └──────────┘           │
└───────────────────────────────────────────────────┘
```

### 4.4 Меню управления шаблоном (Протокол B)

Hover на чип шаблона → появляется "⋯" в правом верхнем углу

Клик на "⋯" → dropdown меню:
```
┌─────────────────────┐
│ ✏️ Изменить         │
│ 📌 В начало         │
│ ↑  Переместить вверх│
│ ↓  Переместить вниз │
│ 🗄️ Архивировать     │
└─────────────────────┘
```

### 4.5 Toast notification (Протокол B)

После 1-клик создания операции из шаблона:

```
┌──────────────────────────────────────────┐
│ ✓ Кофе — 150₽ добавлено    [Отменить]   │
└──────────────────────────────────────────┘
        ↑ появляется на 3 секунды
```

Если клик "Отменить" → операция удаляется

---

## 5. Модели данных

### 5.1 PinnedCategory (Протокол B)

```python
# app/models/database.py

class PinnedCategory(Base):
    __tablename__ = 'pinned_categories'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship('User', back_populates='pinned_categories')
    category = relationship('Category')

    # Unique constraint: пользователь не может закрепить одну категорию дважды
    __table_args__ = (
        UniqueConstraint('user_id', 'category_id', name='unique_user_category'),
    )
```

### 5.2 Template (Протокол B)

```python
# app/models/database.py

class Template(Base):
    __tablename__ = 'templates'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    amount = Column(Numeric(10, 2), nullable=True)  # None = требует ввода при использовании
    description = Column(String(500), nullable=True)
    name = Column(String(100), nullable=False)  # "Кофе", "Обед в офисе", "Метро"
    sort_order = Column(Integer, nullable=False, default=0)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship('User', back_populates='templates')
    category = relationship('Category')

    # Index для быстрого поиска активных шаблонов пользователя
    __table_args__ = (
        Index('idx_user_archived', 'user_id', 'is_archived'),
    )
```

### 5.3 Изменения в User модели

```python
# app/models/database.py

class User(Base):
    # Существующие поля...

    # Новые relationships
    pinned_categories = relationship('PinnedCategory', back_populates='user', cascade='all, delete-orphan')
    templates = relationship('Template', back_populates='user', cascade='all, delete-orphan')
```

---

## 6. Сервисы

### 6.1 PinnedCategoryService (Протокол B)

```python
# app/services/pinned_category_service.py

class PinnedCategoryService:
    def __init__(self, session):
        self.session = session

    def get_all_by_user(self, user_id: int) -> list[PinnedCategory]:
        """Получить все закрепленные категории пользователя (сортировка по sort_order)."""

    def create_pinned_category(self, user_id: int, category_id: int) -> PinnedCategory:
        """Закрепить категорию для пользователя."""

    def delete_pinned_category(self, user_id: int, category_id: int) -> None:
        """Открепить категорию."""

    def reorder(self, user_id: int, category_id: int, new_sort_order: int) -> None:
        """Изменить порядок отображения закрепленной категории."""

    def move_to_top(self, user_id: int, category_id: int) -> None:
        """Переместить категорию в начало (sort_order=1, остальные +1)."""
```

### 6.2 TemplateService (Протокол B)

```python
# app/services/template_service.py

class TemplateService:
    def __init__(self, session):
        self.session = session

    def get_all_by_user(self, user_id: int, include_archived: bool = False) -> list[Template]:
        """Получить шаблоны пользователя (сортировка по sort_order)."""

    def get_by_id(self, template_id: int) -> Template | None:
        """Получить шаблон по ID."""

    def create_template(
        self,
        user_id: int,
        name: str,
        category_id: int | None = None,
        amount: Decimal | None = None,
        description: str | None = None
    ) -> Template:
        """Создать шаблон операции."""

    def update_template(
        self,
        template_id: int,
        name: str | None = None,
        category_id: int | None = None,
        amount: Decimal | None = None,
        description: str | None = None
    ) -> Template:
        """Обновить шаблон."""

    def archive_template(self, template_id: int) -> None:
        """Архивировать шаблон (soft delete)."""

    def restore_template(self, template_id: int) -> None:
        """Восстановить шаблон из архива."""

    def reorder(self, user_id: int, template_id: int, new_sort_order: int) -> None:
        """Изменить порядок отображения шаблона."""

    def create_transaction_from_template(
        self,
        template_id: int,
        transaction_date: date | None = None,
        amount_override: Decimal | None = None
    ) -> Transaction:
        """
        Создать операцию из шаблона.

        - transaction_date: дата операции (default: today)
        - amount_override: переопределить сумму (если template.amount=None)
        """
```

---

## 7. TypedDicts

```python
# app/schema/templates.py

class PinnedCategoryDisplay(TypedDict):
    category_id: int
    category_name: str
    category_icon: str
    category_type: str  # "income" / "expense"
    sort_order: int

class TemplateDisplay(TypedDict):
    template_id: int
    name: str
    amount: Decimal | None
    description: str | None
    category_id: int | None
    category_name: str | None
    category_icon: str | None
    sort_order: int
```

---

## 8. UI Компоненты

### 8.1 Изменения в transactions.py (Протокол A)

**Добавить**:
- Секция Quick-add chips (hardcoded 7 дефолтных чипов)
- Группировка: "Расход" (5 чипов) и "Доход" (2 чипа)
- Callback: клик на chip → открыть модал создания с предвыбранной категорией
- Модал "Ещё..." со всеми категориями из CategoryService

**CSS**:
- Плитки 100-120px (крупнее чем chips категоризации)
- Grid layout: 2 ряда на desktop, 1 ряд + horizontal scroll на mobile
- Hover эффект: легкое затемнение
- Иконки: Bootstrap Icons 24px

### 8.2 Изменения в transactions.py (Протокол B)

**Добавить**:
- Интеграция с PinnedCategoryService и TemplateService
- Callback: 1-клик создание операции из шаблона
- Toast notification с кнопкой "Отменить"
- Меню "⋯" на каждом чипе (hover)
- Модал "Создать шаблон" (вызов из формы создания операции)
- Модал "Редактировать шаблон"
- Модал "Архив шаблонов"

**Логика**:
- При клике на chip категории → модал создания с предвыбранной категорией (Протокол A)
- При клике на chip шаблона → мгновенное создание операции + toast (Протокол B)
- Защита от даблтапа: 0.5-1 сек debounce на кнопках шаблонов

---

## 9. Файлы для изменения/создания

### Протокол A: Чипы категорий

**Модели** (изменений НЕТ):
- Используем существующую Category модель

**Сервисы** (изменений НЕТ):
- Используем существующий CategoryService

**UI**:
- `app/components/transactions.py` — добавить Quick-add chips section
- `app/assets/transactions.css` — стили для chips (плитки)

**TypedDicts** (опционально):
- `app/schema/categories.py` — если нужны дополнительные TypedDicts для UI

### Протокол B: Шаблоны операций

**Миграции**:
- `scripts/migrate_002_quick_add_chips.py` — создание таблиц PinnedCategory и Template

**Модели**:
- `app/models/database.py` — добавить PinnedCategory и Template

**Сервисы**:
- `app/services/pinned_category_service.py` — НОВЫЙ
- `app/services/template_service.py` — НОВЫЙ
- `app/services/__init__.py` — экспорт новых сервисов

**Schema**:
- `app/schema/templates.py` — НОВЫЙ (PinnedCategoryDisplay, TemplateDisplay)

**UI**:
- `app/components/transactions.py` — интеграция с TemplateService, toast, меню "⋯"
- `app/assets/transactions.css` — дополнительные стили для шаблонов

**Тесты**:
- `tests/test_pinned_category_service.py` — НОВЫЙ
- `tests/test_template_service.py` — НОВЫЙ

**Seed**:
- `scripts/seed_default_pinned_categories.py` — миграция дефолтных чипов → PinnedCategory

---

## 10. Acceptance Criteria

### Протокол A: Чипы категорий

- [ ] Отображается 7 дефолтных чипов (5 расход + 2 доход)
- [ ] Чипы сгруппированы по типам "Расход" и "Доход"
- [ ] Клик на chip открывает модал создания операции с предвыбранной категорией
- [ ] Кнопка "Ещё..." открывает модал со всеми категориями
- [ ] Плитки крупнее чем chips категоризации (100-120px vs 60-80px)
- [ ] Адаптивность: 2 ряда на desktop, 1 ряд + scroll на mobile
- [ ] Hover эффект на чипах

### Протокол B: Шаблоны операций

- [ ] Создание шаблона через форму создания операции
- [ ] 1-клик создание операции из шаблона
- [ ] Toast notification "Операция добавлена [Отменить]" (3 сек)
- [ ] Кнопка "Отменить" удаляет операцию
- [ ] Меню "⋯" на каждом чипе шаблона (hover)
- [ ] Редактирование шаблона через "⋯" → "Изменить"
- [ ] Архивирование шаблона через "⋯" → "Архивировать"
- [ ] Изменение порядка через кнопки ↑↓ или "В начало"
- [ ] Модал "Архив шаблонов" для восстановления
- [ ] Защита от даблтапа (0.5-1 сек debounce)
- [ ] Дефолтные чипы мигрированы в PinnedCategory

---

## 11. Что НЕ делаем (из scope)

### НЕ входит в Quick-add chips

- ❌ **Drag-and-drop для порядка** — слишком сложно для MVP, используем кнопки ↑↓
- ❌ **Автоматическое создание шаблонов** — ML на основе повторяющихся операций (post-MVP)
- ❌ **Экспорт/импорт шаблонов** — не критично для MVP
- ❌ **Сложный конструктор шаблонов** — только базовые поля (name, amount, description, category)
- ❌ **Авто-перезапись шаблонов** — не обновляем шаблон при редактировании операции созданной из него
- ❌ **Scheduled templates** — повторяющиеся шаблоны с датами (уже есть recurring transactions)
- ❌ **Условные шаблоны** — "если сумма > X, то категория Y" (post-MVP AI features)

---

## 12. Оценка сложности

| Компонент | Сложность | Дни |
|-----------|-----------|-----|
| **Протокол A: Чипы категорий** | | **6-8** |
| UI chips (hardcoded дефолтные) | Низкая | 2 |
| Callback клик → модал | Низкая | 1 |
| Модал "Ещё..." (все категории) | Средняя | 2 |
| CSS стили (плитки, адаптивность) | Низкая | 1-2 |
| Тестирование UI | Низкая | 1 |
| **Протокол B: Шаблоны операций** | | **6-8** |
| Миграция БД (PinnedCategory, Template) | Низкая | 1 |
| PinnedCategoryService | Низкая | 1 |
| TemplateService | Средняя | 2 |
| UI: 1-клик создание + toast | Средняя | 2 |
| UI: меню "⋯" + модалы управления | Средняя | 2 |
| Seed дефолтных чипов → PinnedCategory | Низкая | 1 |
| Тесты (PinnedCategoryService, TemplateService) | Низкая | 1-2 |

**Итого**: 12-16 дней

---

## 13. Зависимости

### Протокол A зависит от:
- Батч 3.2 (Analytics & UX) — Category модель, CategoryService

### Протокол B зависит от:
- Протокол A завершен (чипы категорий работают)
- Transaction модель (для создания операций из шаблонов)
- TransactionService (для CRUD операций)

---

## 14. Риски и митигация

### Риски

1. **Средний**: Toast notification UX может быть неочевидным для пользователей
   - **Митигация**: Добавить hint "Совет: кликните 'Отменить' чтобы отменить" при первом использовании

2. **Низкий**: Даблтап может создать дублирующие операции
   - **Митигация**: Debounce 0.5-1 сек на кнопках шаблонов

3. **Низкий**: Пользователи могут создать слишком много шаблонов → UI переполнен
   - **Митигация**: Лимит 2 ряда (7-8 видимых чипов), остальные в "Ещё..."

### Предположения

- Пользователи понимают концепцию "шаблонов" (похоже на "Избранное" в банковских приложениях)
- Toast notification с "Отменить" — знакомый паттерн (Gmail, Slack)
- Архивирование вместо hard delete — привычно для опытных пользователей

---

**Готово для передачи в Протокол A** (после завершения Батча 3.2)
