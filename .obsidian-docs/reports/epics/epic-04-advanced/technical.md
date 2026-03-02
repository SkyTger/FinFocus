# Technical Details - Epic-04: Advanced Features

## 🏗️ Архитектура

Epic-04 расширяет сервисный слой для автоматизации частых действий:

```
┌─────────────────────────────────────────────────────────────┐
│                      UI Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Transactions │  │  Dashboard   │  │   Calendar   │      │
│  │   (Chips)    │  │              │  │              │      │
│  └──────┬───────┘  └──────────────┘  └──────────────┘      │
└─────────┼───────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────┐
│         │            Service Layer                          │
│  ┌──────▼───────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Template   │  │   Pinned     │  │  Transaction │      │
│  │   Service    │  │   Category   │  │   Service    │      │
│  └──────┬───────┘  │   Service    │  └──────────────┘      │
│         │          └──────────────┘                         │
└─────────┼───────────────────────────────────────────────────┘
          │
┌─────────┼───────────────────────────────────────────────────┐
│         │            Data Layer                             │
│  ┌──────▼───────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Template   │  │  Pinned      │  │  Category    │      │
│  │    Model     │  │  Category    │  │    Model     │      │
│  └──────────────┘  │    Model     │  └──────────────┘      │
│                    └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

**Новые модели**:
- `PinnedCategory` — закрепленные категории для быстрого доступа
- `Template` — шаблоны операций с предзаполненными полями

**Новые сервисы**:
- `PinnedCategoryService` — управление закрепленными категориями
- `TemplateService` — управление шаблонами + создание операций из шаблонов

---

## 📦 Модули и функции

### PinnedCategoryService (`app/services/pinned_category_service.py`)

#### `get_all_by_user(user_id: int) -> list[PinnedCategory]`
Получает все закрепленные категории пользователя с сортировкой по `sort_order`.

**Входные данные:**
- `user_id` — ID пользователя

**Выходные данные:**
- Список моделей `PinnedCategory`
- Сортировка: `ORDER BY sort_order ASC`

**Пример использования:**
```python
pinned_service = PinnedCategoryService(session)
pinned_categories = pinned_service.get_all_by_user(user_id=1)

for pc in pinned_categories:
    print(f"{pc.category.name} (order: {pc.sort_order})")
```

---

#### `create_pinned_category(user_id: int, category_id: int) -> PinnedCategory`
Закрепляет категорию для пользователя.

**Входные данные:**
- `user_id` — ID пользователя
- `category_id` — ID категории из справочника `Category`

**Выходные данные:**
- Созданная модель `PinnedCategory`

**Валидация:**
- Проверка уникальности `(user_id, category_id)` — нельзя закрепить одну категорию дважды
- `ValidationError` если категория уже закреплена

**Пример использования:**
```python
pinned_service = PinnedCategoryService(session)
pinned = pinned_service.create_pinned_category(user_id=1, category_id=3)

session.commit()
```

---

#### `delete_pinned_category(user_id: int, category_id: int) -> None`
Открепляет категорию.

**Входные данные:**
- `user_id` — ID пользователя
- `category_id` — ID категории

**Побочный эффект:**
- Удаляет запись из `pinned_categories` (hard delete)

**Пример использования:**
```python
pinned_service = PinnedCategoryService(session)
pinned_service.delete_pinned_category(user_id=1, category_id=3)

session.commit()
```

---

#### `move_to_top(user_id: int, category_id: int) -> None`
Перемещает категорию в начало списка.

**Входные данные:**
- `user_id` — ID пользователя
- `category_id` — ID категории

**Логика:**
- Устанавливает `sort_order=1` для целевой категории
- Увеличивает `sort_order` остальных на +1 (shift-down алгоритм)

**Пример использования:**
```python
pinned_service = PinnedCategoryService(session)
pinned_service.move_to_top(user_id=1, category_id=5)

session.commit()
```

---

### TemplateService (`app/services/template_service.py`)

#### `get_all_by_user(user_id: int, include_archived: bool = False) -> list[Template]`
Получает шаблоны пользователя.

**Входные данные:**
- `user_id` — ID пользователя
- `include_archived` — включать архивированные (default: `False`)

**Выходные данные:**
- Список моделей `Template`
- Фильтр: `is_archived=False` если `include_archived=False`
- Сортировка: `ORDER BY sort_order ASC`

**Пример использования:**
```python
template_service = TemplateService(session)
active_templates = template_service.get_all_by_user(user_id=1)

for tpl in active_templates:
    print(f"{tpl.name} — {tpl.amount}₽ ({tpl.category.name})")
```

---

#### `create_template(user_id, name, category_id, amount, description) -> Template`
Создает шаблон операции.

**Входные данные:**
- `user_id` — ID пользователя
- `name` — название шаблона ("Кофе", "Обед в офисе")
- `category_id` — ID категории (nullable)
- `amount` — сумма операции (nullable, если требуется ввод при использовании)
- `description` — описание операции (nullable)

**Выходные данные:**
- Созданная модель `Template`

**Валидация:**
- `name` обязателен (min 1 символ)
- `ValidationError` если name пустой

**Пример использования:**
```python
template_service = TemplateService(session)
template = template_service.create_template(
    user_id=1,
    name="Кофе",
    category_id=1,  # "Еда и продукты"
    amount=Decimal("150.00"),
    description="Кофе в офисе"
)

session.commit()
```

---

#### `update_template(template_id, name, category_id, amount, description) -> Template`
Обновляет шаблон.

**Входные данные:**
- `template_id` — ID шаблона
- `name` — новое название (optional)
- `category_id` — новая категория (optional)
- `amount` — новая сумма (optional)
- `description` — новое описание (optional)

**Выходные данные:**
- Обновленная модель `Template`

**Логика:**
- Обновляются только переданные параметры (partial update)

**Пример использования:**
```python
template_service = TemplateService(session)
template = template_service.update_template(
    template_id=5,
    amount=Decimal("180.00")  # Поднимаем цену кофе
)

session.commit()
```

---

#### `archive_template(template_id: int) -> None`
Архивирует шаблон (soft delete).

**Входные данные:**
- `template_id` — ID шаблона

**Побочный эффект:**
- Устанавливает `is_archived=True`

**Пример использования:**
```python
template_service = TemplateService(session)
template_service.archive_template(template_id=5)

session.commit()
```

---

#### `create_transaction_from_template(template_id, transaction_date, amount_override) -> Transaction`
Создает операцию из шаблона (1-клик).

**Входные данные:**
- `template_id` — ID шаблона
- `transaction_date` — дата операции (default: `date.today()`)
- `amount_override` — переопределить сумму (optional, если template.amount=None)

**Выходные данные:**
- Созданная модель `Transaction` через `TransactionService`

**Логика:**
1. Загружает шаблон из БД
2. Если `template.amount=None` и `amount_override=None` → `ValidationError`
3. Создает операцию через `TransactionService.create_transaction()`
4. Копирует: `category_id`, `amount`, `description` из шаблона

**Валидация:**
- `ValidationError` если шаблон архивирован (`is_archived=True`)
- `ValidationError` если сумма не задана (template.amount=None и amount_override=None)

**Пример использования:**
```python
template_service = TemplateService(session)
transaction = template_service.create_transaction_from_template(
    template_id=5,
    transaction_date=date.today()
)

session.commit()

# Операция создана, можно показать toast "Кофе — 150₽ добавлено [Отменить]"
```

---

## 🗄️ База данных

### Schema Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     User        │       │    Category     │       │  Transaction    │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ username        │       │ name            │       │ user_id (FK)    │
│ ...             │       │ icon            │       │ category_id (FK)│
└────────┬────────┘       │ type            │       │ type            │
         │                │ is_system       │       │ amount          │
         │                └────────┬────────┘       │ date            │
         │                         │                │ description     │
         │                         │                └─────────────────┘
         │                         │
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│ PinnedCategory  │       │    Template     │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ user_id (FK)    │       │ user_id (FK)    │
│ category_id (FK)│       │ category_id (FK)│
│ sort_order      │       │ name            │
│ created_at      │       │ amount          │
└─────────────────┘       │ description     │
  Unique (user, cat)      │ sort_order      │
                          │ is_archived     │
                          │ created_at      │
                          └─────────────────┘
```

### Миграция

**Файл**: `scripts/migrate_002_quick_add_chips.py`

**Создаваемые таблицы**:
1. `pinned_categories`
2. `templates`

**Индексы**:
- `idx_user_archived` на `templates(user_id, is_archived)` — быстрый поиск активных шаблонов

**Constraints**:
- `unique_user_category` на `pinned_categories(user_id, category_id)` — нельзя закрепить категорию дважды

**Идемпотентность**:
- Проверка `IF NOT EXISTS` перед созданием таблиц

---

## 🔄 Инварианты

### PinnedCategory
- ✅ **Уникальность**: Пользователь не может закрепить одну категорию дважды
- ✅ **Cascade delete**: При удалении пользователя → удаляются все pinned_categories
- ✅ **Cascade delete**: При удалении категории → удаляются все pinned_categories (защита целостности)

### Template
- ✅ **Soft delete**: Архивирование вместо hard delete (is_archived=True)
- ✅ **Cascade delete**: При удалении пользователя → удаляются все templates
- ✅ **SET NULL**: При удалении категории → `template.category_id=NULL` (шаблон сохраняется)
- ✅ **Amount nullable**: Сумма может быть None (требуется ввод при использовании)

### Transaction creation from template
- ✅ **Дата**: Операция создается на `date.today()` если `transaction_date=None`
- ✅ **Amount validation**: Если `template.amount=None` и `amount_override=None` → `ValidationError`
- ✅ **Archived check**: Нельзя создать операцию из архивированного шаблона

---

## ⚡ Производительность

### Запросы к БД

**get_all_by_user (PinnedCategory)**:
- 1 SELECT с JOIN Category: ~5ms для 10 записей
- Index: `pinned_categories(user_id)` (FK автоматически создает индекс)

**get_all_by_user (Template)**:
- 1 SELECT с JOIN Category: ~5ms для 20 записей
- Index: `idx_user_archived` ускоряет фильтрацию активных шаблонов

**create_transaction_from_template**:
- 2 SELECT: загрузка template + user (через TransactionService)
- 1 INSERT: создание transaction
- Итого: ~10ms

### Лимиты

- **PinnedCategory**: Рекомендуется < 20 закрепленных категорий на пользователя
- **Template**: Рекомендуется < 50 активных шаблонов на пользователя (UI показывает 7-8, остальные в "Ещё...")

### Оптимизации

**N+1 query prevention**:
- В `get_all_by_user` используется `.options(joinedload(PinnedCategory.category))` для загрузки категорий за 1 запрос

**Sort order management**:
- Shift-down алгоритм для `move_to_top` выполняет 1 UPDATE с `WHERE sort_order >= new_order`

---

## 🎨 UI Patterns

### Quick-add chips визуальная иерархия

```css
/* Плитки Quick-add (крупные) */
.quick-add-chip {
    width: 100-120px;
    height: 80-100px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.quick-add-chip:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    transform: translateY(-2px);
}

/* Chips категоризации (мелкие, из Батча 3.2) */
.category-chip {
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 14px;
    display: inline-block;
}
```

### Toast notification UX

**Позиционирование**: Bottom-right (как Gmail)

**Автозакрытие**: 3 секунды

**Кнопка "Отменить"**: Видна всё время показа toast

**Z-index**: Поверх модалов (z-index: 1060)

---

## 🧪 Тестирование

### Unit тесты

**PinnedCategoryService** (~8-10 тестов):
- `test_create_pinned_category` — создание закрепленной категории
- `test_create_duplicate_raises_error` — нельзя закрепить дважды
- `test_delete_pinned_category` — открепление
- `test_move_to_top` — изменение порядка
- `test_get_all_by_user_sorted` — проверка sort_order

**TemplateService** (~12-15 тестов):
- `test_create_template` — создание шаблона
- `test_create_template_with_null_amount` — сумма может быть None
- `test_update_template` — обновление полей
- `test_archive_template` — soft delete
- `test_restore_template` — восстановление из архива
- `test_create_transaction_from_template` — создание операции
- `test_create_from_archived_raises_error` — нельзя использовать архивный шаблон
- `test_create_without_amount_raises_error` — валидация суммы

### Integration тесты

**E2E Quick-add flow** (~3-5 тестов):
- `test_click_chip_opens_modal_with_category` — Протокол A
- `test_click_template_creates_transaction` — Протокол B
- `test_undo_toast_deletes_transaction` — кнопка "Отменить"
- `test_manage_template_menu` — редактирование шаблона

---

## 🔧 Конфигурация

### Environment Variables

*Нет новых переменных окружения для Epic-04*

### Feature Flags (будущее)

Если потребуется A/B тестирование:
```python
# .env
ENABLE_QUICK_ADD_CHIPS=true
ENABLE_TEMPLATE_ONE_CLICK=true
```

---

## 📚 Референсы

### Похожие реализации

**Gmail "Отменить отправку"** — Toast notification с кнопкой отмены (3-5 сек таймер)

**Slack "Shortcuts"** — Частые действия через `/` команды и кнопки

**Banking apps "Favorites"** — Закрепленные шаблоны платежей (Сбербанк, Тинькофф)

### Dash UI Components

**dcc.Store** — хранение `undo_transaction_id` для toast "Отменить"

**dbc.Toast** — notification component для "Операция добавлена [Отменить]"

**Pattern-Matching Callbacks** — обработка кликов на динамические chips

---

**Дата создания**: 2026-01-25
**Последнее обновление**: 2026-01-25
