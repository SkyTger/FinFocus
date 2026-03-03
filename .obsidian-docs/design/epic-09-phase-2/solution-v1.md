# Solution v1: User Profile с emoji-аватарками

## Обзор решения
Расширяем модель User полем `avatar_id`, перестраиваем Onboarding Wizard в единый экран (имя + аватарка + баланс), делаем sidebar динамическим через callback с чтением из БД, добавляем глобальный модал редактирования профиля в `main.py`. Dashboard greeting становится динамическим через тот же механизм Store-based обновления.

## Архитектура

### Компоненты

1. **Data Layer**: `User.avatar_id` + миграция 007 + конфиг `app/config/avatars.py`
2. **Service Layer**: `OnboardingService.complete()` (расширенный) + `OnboardingService.update_profile()`
3. **UI -- Onboarding**: Перестроенный wizard с тремя полями в одном экране
4. **UI -- Sidebar**: Динамический profile-блок с callback на `dcc.Store("profile-updated")`
5. **UI -- Profile Modal**: `app/components/profile_modal.py` -- глобальный модал в `main.py`
6. **UI -- Dashboard**: Greeting "Добро пожаловать, {имя}!" через callback

### Диаграмма взаимодействия
```
[Onboarding Wizard]                    [Profile Modal]
        |                                     |
        | complete(name, avatar, balance)      | update_profile(name, avatar)
        v                                     v
  [OnboardingService] ----session----> [User model (DB)]
        |                                     |
        | -> Store("profile-updated")         | -> Store("profile-updated")
        v                                     v
  [Sidebar callback] <-- reads User --> [Dashboard callback]
        |                                     |
        v                                     v
  sidebar-profile-name                 dashboard-greeting
  sidebar-profile-avatar
```

**Механизм обновления sidebar/dashboard после сохранения:**
```
Onboarding submit / Profile save
  -> callback записывает в dcc.Store("profile-updated", data=timestamp)
  -> sidebar callback Input("profile-updated") -> reads User from DB -> updates profile block
  -> dashboard callback Input("profile-updated") -> reads User.name -> updates greeting H4
```

## Файловая структура
```
app/config/__init__.py              — CREATE: пустой __init__
app/config/avatars.py               — CREATE: AVATARS dict, DEFAULT_AVATAR_ID, get_avatar_emoji()
app/models/database.py              — EDIT: +avatar_id в User
app/core/migrations.py              — EDIT: +миграция 007_avatar_id
app/core/bootstrap.py               — EDIT: +avatar_id="emoji-default" в default User
app/schema/onboarding.py            — EDIT: +name, +avatar_id в OnboardingStatus
app/services/onboarding_service.py  — EDIT: complete() расширен, +update_profile(), +get_profile()
app/components/onboarding_wizard.py — EDIT: перестройка UI (имя + аватарка + баланс)
app/components/sidebar.py           — EDIT: динамический профиль, callback
app/components/profile_modal.py     — CREATE: модал редактирования
app/components/dashboard.py         — EDIT: динамический greeting
app/main.py                         — EDIT: +profile modal, +dcc.Store("profile-updated")
app/assets/onboarding.css           — EDIT: +avatar grid стили
app/assets/sidebar.css              — EDIT: +profile clickable стили
tests/test_onboarding_service.py    — EDIT: +тесты complete(), update_profile()
tests/test_avatars.py               — CREATE: тесты конфига аватарок
tests/test_migration_007.py         — CREATE: тест миграции avatar_id
```

## Ключевые интерфейсы

```python
# app/config/avatars.py
AVATARS: dict[str, dict[str, str]] = {
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
DEFAULT_AVATAR_ID: str = "emoji-default"

def get_avatar_emoji(avatar_id: str) -> str:
    """Возвращает emoji по avatar_id. Fallback на default."""
    return AVATARS.get(avatar_id, AVATARS[DEFAULT_AVATAR_ID])["emoji"]
```

```python
# app/services/onboarding_service.py — расширение
class OnboardingService:
    def complete(
        self,
        user_id: int,
        name: str,
        avatar_id: str,
        starting_balance: Decimal,
    ) -> None:
        """Завершить онбординг с именем, аватаркой и балансом."""
        ...

    def update_profile(
        self,
        user_id: int,
        name: str,
        avatar_id: str,
    ) -> None:
        """Обновить профиль пользователя (имя + аватарка)."""
        ...

    def get_profile(self, user_id: int) -> dict[str, str]:
        """Получить name и avatar_id для отображения в UI."""
        ...
```

```python
# app/components/profile_modal.py
def create_profile_modal() -> dbc.Modal:
    """Создает глобальный модал редактирования профиля."""
    ...

# Callbacks:
# 1. open modal: Input("sidebar-profile-edit-btn", "n_clicks") -> Output("profile-modal", "is_open")
#    + загрузка текущих данных из БД
# 2. save: Input("profile-save-btn", "n_clicks") -> update DB, close modal,
#    -> Output("profile-updated", "data") = timestamp
```

```python
# app/components/sidebar.py — расширение
# Новый callback:
@callback(
    Output("sidebar-profile-container", "children"),
    [Input("url", "pathname"), Input("profile-updated", "data")],
)
def update_sidebar_profile(pathname, profile_updated):
    """Обновляет профиль в sidebar при загрузке и после редактирования."""
    ...
```

```python
# app/components/dashboard.py — расширение
# Greeting H4 получает id="dashboard-greeting"
# Новый callback:
@callback(
    Output("dashboard-greeting", "children"),
    [Input("url", "pathname"), Input("profile-updated", "data")],
    prevent_initial_call=False,
)
def update_dashboard_greeting(pathname, profile_updated):
    """Обновляет приветствие на dashboard."""
    ...
```

## Модель данных

### User (расширение)
```python
# Добавить в User модель:
avatar_id = Column(String(20), default="emoji-default", nullable=False)
```

### Миграция 007
```python
# В run_all_migrations():
if not _column_exists(cursor, "users", "avatar_id"):
    cursor.execute(
        "ALTER TABLE users "
        "ADD COLUMN avatar_id VARCHAR(20) DEFAULT 'emoji-default' NOT NULL"
    )
    applied.append("007_avatar_id")
```

### OnboardingStatus (расширение)
```python
class OnboardingStatus(TypedDict):
    first_launch: bool
    starting_balance: Decimal
    needs_balance_alert: bool
    name: str          # NEW
    avatar_id: str     # NEW
```

## Обработка ошибок

1. **Onboarding submit**: Валидация имени (1-50 chars, strip) на клиенте (disabled кнопка) и на сервере (guard в `complete()`). При ошибке БД -- закрыть модал (fail-closed, как сейчас).
2. **Profile modal save**: Аналогичная валидация. При невалидном `avatar_id` -- использовать `DEFAULT_AVATAR_ID` (fallback в `get_avatar_emoji()`).
3. **Sidebar read**: Fail-closed. При ошибке чтения User -- показать defaults ("Пользователь" + "😊"). Не блокировать навигацию.
4. **Dashboard greeting**: При ошибке -- "Добро пожаловать!" без имени (graceful degradation).
5. **Миграция 007**: Идемпотентна через `_column_exists()` check.

## План реализации

**Батч 1: Data Layer (3 файла)**
1. `app/config/__init__.py` -- CREATE пустой `__init__`
2. `app/config/avatars.py` -- CREATE конфиг аватарок
3. `app/models/database.py` -- EDIT: `+avatar_id` в User

**Батч 2: Migration + Bootstrap + Schema (3 файла)**
4. `app/core/migrations.py` -- EDIT: `+007_avatar_id`
5. `app/core/bootstrap.py` -- EDIT: `+avatar_id` в default User
6. `app/schema/onboarding.py` -- EDIT: `+name, +avatar_id`

**Батч 3: Service Layer (1 файл)**
7. `app/services/onboarding_service.py` -- EDIT: `complete()`, `update_profile()`, `get_profile()`

**Батч 4: Onboarding Wizard UI (2 файла)**
8. `app/components/onboarding_wizard.py` -- EDIT: перестройка формы
9. `app/assets/onboarding.css` -- EDIT: `+avatar grid` стили

**Батч 5: Sidebar + Profile Modal (3 файла)**
10. `app/components/sidebar.py` -- EDIT: динамический профиль + callback
11. `app/components/profile_modal.py` -- CREATE: модал редактирования
12. `app/assets/sidebar.css` -- EDIT: `+profile clickable` стили

**Батч 6: Main + Dashboard integration (2 файла)**
13. `app/main.py` -- EDIT: `+profile_modal`, `+dcc.Store("profile-updated")`
14. `app/components/dashboard.py` -- EDIT: динамический greeting

**Батч 7: Tests (3 файла)**
15. `tests/test_avatars.py` -- CREATE
16. `tests/test_onboarding_service.py` -- EDIT: `+complete()`, `+update_profile()`
17. `tests/test_migration_007.py` -- CREATE

## Зависимости

- `app/config/avatars.py` -- нет внешних зависимостей (чистый Python dict)
- `User.avatar_id` -- зависит от конфига аватарок (import для валидации)
- `OnboardingService.complete()` -- зависит от `User.avatar_id` в модели
- `onboarding_wizard.py` -- зависит от `avatars.py` (для рендера сетки) и обновленного `OnboardingService`
- `sidebar.py` -- зависит от `avatars.py` (для `get_avatar_emoji()`) и `OnboardingService.get_profile()`
- `profile_modal.py` -- зависит от `avatars.py`, `OnboardingService.update_profile()`
- `main.py` -- зависит от `profile_modal.py` (import `create_profile_modal`)
- `dashboard.py` -- зависит от `OnboardingService.get_profile()` или прямой read User.name

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Callback circular dependency: profile-updated Store triggers multiple callbacks | Средняя | Каждый callback использует `no_update` для неизменных Output. `profile-updated` -- чистый timestamp, не зацикливается. |
| Sidebar profile callback на `Input("url", "pathname")` -- двойной вызов при навигации | Средняя | Дедупликация через `ctx.triggered_id`: если `url` -- читаем из БД, если `profile-updated` -- тоже читаем (свежие данные после save). Оба случая безопасны. |
| Dashboard greeting -- ReferenceError при clientside_callback для динамического элемента | Высокая | Использовать серверный callback с `prevent_initial_call=False`. Элемент `dashboard-greeting` всегда присутствует в layout dashboard (не динамический). Но dashboard рендерится через `display_page()`, поэтому элемент появляется только на `/dashboard`. Решение: использовать `suppress_callback_exceptions=True` (уже включено) + server-side callback. При pathname != "/dashboard" -- `no_update` / `PreventUpdate`. |
| Onboarding wizard -- имя обрезается или содержит только пробелы | Низкая | Server-side валидация в `complete()`: `name = name.strip()`, проверка `len(name) >= 1`. Client-side: disabled кнопка пока input пустой. |
| Существующие пользователи без avatar_id после миграции | Низкая | Миграция 007 добавляет DEFAULT "emoji-default". `get_avatar_emoji()` имеет fallback. |

## Requirements Traceability Matrix (RTM)

| # | Requirement (дословно из спецификации) | Секция spec | Реализация в solution | Тип |
|---|----------------------------------------|-------------|----------------------|-----|
| R1 | `avatar_id = Column(String(20), default="emoji-default", nullable=False)` в User, миграция 007 | R1 | `app/models/database.py` + `app/core/migrations.py` (007) | Data |
| R2 | Файл `app/config/avatars.py`, 10 вариантов emoji | R2 | `app/config/avatars.py` -- AVATARS dict + `get_avatar_emoji()` | Config |
| R3 | Onboarding wizard: имя (обяз.) + аватарка (сетка 10) + баланс (опц.) | R3 | `app/components/onboarding_wizard.py` -- перестройка + `app/assets/onboarding.css` | UI |
| R3.1 | Кнопка "Продолжить" disabled пока имя пустое | R3 | Callback валидации в `onboarding_wizard.py` | UI |
| R3.2 | Выбранная аватарка подсвечена зелёным border + glow | R3 | CSS `.avatar-option.selected` в `onboarding.css` | UI |
| R3.3 | "Пропустить": name="Пользователь", avatar_id=default, balance=0 | R3 | `handle_onboarding_action()` -- branch skip | Logic |
| R4 | `complete(user_id, name, avatar_id, starting_balance)` | R4 | `OnboardingService.complete()` | Service |
| R4.1 | `update_profile(user_id, name, avatar_id)` | R6 (implied) | `OnboardingService.update_profile()` | Service |
| R5 | Sidebar читает User из БД, отображает name + avatar_id | R5 | `sidebar.py` callback + `get_avatar_emoji()` | UI |
| R5.1 | Клик по профилю -> открыть модал редактирования | R5 | `sidebar-profile-edit-btn` -> `profile-modal.is_open` | UI |
| R5.2 | Sidebar обновляется после сохранения профиля | R5 | `Input("profile-updated", "data")` trigger | Callback |
| R6 | Глобальный модал в main.py: имя + аватарка (без баланса) | R6 | `profile_modal.py` + `main.py` integration | UI |
| R6.1 | При открытии подгрузить текущие данные из БД | R6 | Callback open -> read User -> populate fields | Callback |
| R7 | Unit тесты: complete(), конфиг, миграция 007 | R7 | `tests/test_onboarding_service.py`, `tests/test_avatars.py`, `tests/test_migration_007.py` | Test |

## Blast Radius

### Прямые изменения (новые + редактируемые файлы)
- `app/config/__init__.py` -- CREATE
- `app/config/avatars.py` -- CREATE
- `app/components/profile_modal.py` -- CREATE
- `tests/test_avatars.py` -- CREATE
- `tests/test_migration_007.py` -- CREATE
- `app/models/database.py` -- EDIT (User +avatar_id)
- `app/core/migrations.py` -- EDIT (+007)
- `app/core/bootstrap.py` -- EDIT (+avatar_id)
- `app/schema/onboarding.py` -- EDIT (+name, +avatar_id)
- `app/services/onboarding_service.py` -- EDIT (complete, update_profile, get_profile)
- `app/components/onboarding_wizard.py` -- EDIT (полная перестройка формы + callbacks)
- `app/components/sidebar.py` -- EDIT (динамический профиль + callback)
- `app/components/dashboard.py` -- EDIT (динамический greeting)
- `app/main.py` -- EDIT (+profile modal, +Store)
- `app/assets/onboarding.css` -- EDIT (+avatar grid)
- `app/assets/sidebar.css` -- EDIT (+profile clickable)
- `tests/test_onboarding_service.py` -- EDIT (+тесты)

### Связанные файлы (проверить на совместимость, но не редактировать)
- `app/core/database.py` -- `get_db_session()` используется в новых callbacks (read-only)
- `app/schema/__init__.py` -- если расширяем OnboardingStatus, re-export остается прежним
- `app/assets/custom.css` -- CSS переменные `--color-primary`, `--color-primary-glow` используются для аватар-подсветки
- `tests/conftest.py` -- fixture `db_session` используется в новых тестах

### Проверить после реализации
- [ ] `pytest -k "not test_budget_change_updates_allocation"` -- все тесты зеленые
- [ ] `black app/` -- код отформатирован
- [ ] `flake8 app/` -- нет ошибок F/E категории
- [ ] Onboarding wizard открывается при `first_launch=True`, все три поля работают
- [ ] Sidebar показывает реальное имя и аватарку после onboarding
- [ ] Dashboard greeting показывает "Добро пожаловать, {имя}!"
- [ ] Профиль редактируется через модал, sidebar обновляется
- [ ] Миграция 007 идемпотентна (повторный запуск безопасен)
- [ ] Auto-bootstrap создает пользователя с `avatar_id="emoji-default"`
- [ ] "Пропустить" в onboarding сохраняет defaults
- [ ] Не сломан существующий reconciliation modal и onboarding flow
