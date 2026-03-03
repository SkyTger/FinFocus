# Spec: Epic-09 Phase 2 — User Profile

## Цель
Персонализация приложения: при первом запуске пользователь вводит имя, выбирает аватарку и указывает баланс. Sidebar отображает профиль. Профиль можно редактировать.

## Контекст

### Текущее состояние
- **User модель**: `name`, `email`, `first_launch`, `starting_balance` — НЕТ `avatar_id`
- **Onboarding wizard** (`onboarding_wizard.py`): blocking modal, спрашивает ТОЛЬКО `starting_balance`, кнопки "Продолжить"/"Пропустить"
- **OnboardingService**: `get_status()`, `complete_with_balance()`, `skip()`
- **Sidebar** (`sidebar.py`): ХАРДКОД "🦊" + "Иван Иванов" + "FinFocus"
- **Auto-bootstrap** (`app/core/bootstrap.py`): создаёт `User(name="Пользователь")`
- **Миграции**: 001-006 в `app/core/migrations.py` (inline, идемпотентные)
- **Дизайн**: Glassmorphism Light Theme — glass-card, мятный градиент фон, pill nav, `border-radius: 24px`

### Ключевые ограничения
- Single-user (DEFAULT_USER_ID=1)
- Аватарки ТОЛЬКО предустановленные (НЕ загрузка файлов)
- Onboarding wizard перестраивается: имя + аватарка + баланс в ОДНОМ модале (вариант B)

## Требования

### R1: User.avatar_id
- Добавить `avatar_id = Column(String(20), default="emoji-default", nullable=False)` в User модель
- Миграция 007 в `app/core/migrations.py`: `ALTER TABLE users ADD COLUMN avatar_id VARCHAR(20) DEFAULT 'emoji-default' NOT NULL`

### R2: Конфиг аватарок
- Файл `app/config/avatars.py`
- 10 вариантов: emoji-стиль (Unicode символы)
- Формат:
```python
AVATARS: dict[str, dict] = {
    "emoji-default": {"emoji": "😊", "label": "Улыбка"},
    "emoji-rocket": {"emoji": "🚀", "label": "Ракета"},
    "emoji-fox": {"emoji": "🦊", "label": "Лиса"},
    "emoji-cat": {"emoji": "🐱", "label": "Котик"},
    "emoji-coffee": {"emoji": "☕", "label": "Кофе"},
    "emoji-star": {"emoji": "⭐", "label": "Звезда"},
    "emoji-fire": {"emoji": "🔥", "label": "Огонь"},
    "emoji-crystal": {"emoji": "💎", "label": "Кристалл"},
    "emoji-leaf": {"emoji": "🍃", "label": "Листок"},
    "emoji-target": {"emoji": "🎯", "label": "Цель"},
}
DEFAULT_AVATAR_ID = "emoji-default"
```

### R3: Перестройка Onboarding Wizard (вариант B — один экран)
Заменить текущий onboarding modal на единую форму:
1. **Заголовок**: "Добро пожаловать в FinFocus!"
2. **Имя** (обязательно): `dbc.Input(type="text", maxLength=50, placeholder="Как вас зовут?")`
   - Валидация: 1-50 символов, strip пробелов
   - Кнопка "Продолжить" disabled пока имя пустое
3. **Аватарка** (опционально): Сетка из 10 кликабельных круглых элементов
   - По умолчанию выбрана первая (emoji-default)
   - Выбранная подсвечена зелёным border + glow (как calendar-day-today)
   - Размер: 56x56px, font-size 1.8rem
4. **Баланс** (опционально): Текущий InputGroup с ₽ (как сейчас)
   - Warning для отрицательного баланса (как сейчас)
5. **Кнопки**: "Пропустить" (secondary) + "Продолжить" (success)
   - "Пропустить": сохраняет name="Пользователь", avatar_id=default, balance=0
   - "Продолжить": сохраняет введённые значения

**Стиль модала**: текущий onboarding-modal CSS (зелёный gradient header, border-radius 12px)

### R4: OnboardingService — расширение
- `complete_with_balance()` → `complete(user_id, name, avatar_id, starting_balance)`
  - Устанавливает `user.name`, `user.avatar_id`, `user.starting_balance`, `user.first_launch = False`
- `skip()` → устанавливает `user.first_launch = False` (как сейчас, без изменения name/avatar)

### R5: Sidebar — динамический профиль из БД
- При загрузке sidebar читать User из БД: `name`, `avatar_id`
- Отображать реальные данные вместо хардкода "🦊 Иван Иванов"
- Клик по профильному блоку → открыть модал редактирования
- Sidebar profile обновляется после сохранения профиля (через callback)

### R6: Модал редактирования профиля
- Глобальный модал в `main.py` (как reconciliation modal)
- Поля: имя + аватарка (БЕЗ баланса — баланс меняется через Сверку)
- Кнопки: "Отмена" + "Сохранить"
- При открытии: подгрузить текущие данные из БД
- При сохранении: обновить User, закрыть модал, обновить sidebar

### R7: Тесты
- Unit тесты OnboardingService: `complete()` с именем и аватаркой
- Unit тесты конфига аватарок: валидация структуры, DEFAULT_AVATAR_ID существует
- Unit тесты миграции 007: column exists, default value

## Файлы для изменения

| Файл | Действие | Описание |
|------|----------|----------|
| `app/models/database.py` | EDIT | +avatar_id колонка в User |
| `app/config/avatars.py` | CREATE | Конфиг предустановленных аватарок |
| `app/config/__init__.py` | CREATE | Пустой __init__ |
| `app/core/migrations.py` | EDIT | +миграция 007_avatar_id |
| `app/services/onboarding_service.py` | EDIT | Расширить complete(), добавить update_profile() |
| `app/components/onboarding_wizard.py` | EDIT | Перестройка: имя + аватарка + баланс |
| `app/components/sidebar.py` | EDIT | Динамический профиль из БД + клик → модал |
| `app/components/profile_modal.py` | CREATE | Модал редактирования профиля |
| `app/main.py` | EDIT | +profile modal в глобальный layout |
| `app/assets/onboarding.css` | EDIT | +стили для аватарки grid |
| `app/core/bootstrap.py` | EDIT | +avatar_id в default User |
| `tests/test_onboarding_service.py` | EDIT | +тесты complete() с name/avatar |
| `tests/test_avatars.py` | CREATE | Тесты конфига аватарок |
| `tests/test_migrations.py` | EDIT | +тест 007_avatar_id |

## НЕ входит в scope
- Загрузка пользовательских аватарок (фото/файлы)
- Страница /settings или /profile (только модал)
- Многопользовательская архитектура
- Изменение баланса через модал профиля (для этого есть Сверка)
