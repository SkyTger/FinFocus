# Solution v2: User Profile с emoji-аватарками (исправленная)

## Обзор решения

Расширяем модель User полем `avatar_id`, перестраиваем Onboarding Wizard в единый экран (имя + аватарка + баланс), делаем sidebar динамическим через callback с чтением из БД, добавляем глобальный модал редактирования профиля в `main.py`. Dashboard greeting читается inline при вызове `create_dashboard_layout()` (без отдельного callback).

**Ключевые отличия от v1:**
- Dashboard greeting: inline read в `create_dashboard_layout()` вместо callback (устраняет ReferenceError)
- Avatar selection: `dbc.RadioItems` со скрытыми native radio + CSS labels
- Profile modal: один callback с разветвлением по `ctx.triggered_id`
- Sidebar profile: весь контейнер clickable (`id="sidebar-profile-container"`, `n_clicks`)
- `skip()` полагается на bootstrap defaults, только ставит `first_launch=False`
- Добавлен TypedDict `UserProfile` для return type `get_profile()`
- `complete_with_balance()` переименован в `complete()` (breaking change с обратной совместимостью)

## Архитектура

### Компоненты

1. **Data Layer**: `User.avatar_id` + миграция 007 + конфиг `app/config/avatars.py`
2. **Service Layer**: `OnboardingService.complete()` (новая сигнатура) + `update_profile()` + `get_profile()`
3. **UI -- Onboarding**: Перестроенный wizard с тремя полями в одном экране, avatar через RadioItems
4. **UI -- Sidebar**: Динамический profile-блок с callback на `dcc.Store("profile-updated")`
5. **UI -- Profile Modal**: `app/components/profile_modal.py` -- глобальный модал в `main.py`, один callback
6. **UI -- Dashboard**: Greeting "Добро пожаловать, {имя}!" через inline read в `create_dashboard_layout()`

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
  [Sidebar callback] <-- reads User --> [Dashboard: обновляется при навигации]
        |                                     |
        v                                     v
  sidebar-profile-name               H4 text (inline read при каждом display_page)
  sidebar-profile-avatar
```

**Механизм обновления sidebar после сохранения:**
```
Onboarding submit / Profile save
  -> callback записывает в dcc.Store("profile-updated", data=timestamp)
  -> sidebar callback Input("profile-updated") -> reads User from DB -> updates profile block
```

**Dashboard greeting:**
```
display_page("/dashboard")
  -> create_dashboard_layout()
  -> inline: session.get(User, 1).name -> H4("Добро пожаловать, {name}!")
  -> greeting обновляется при каждой навигации на dashboard (достаточно)
```

## Файловая структура

```
app/config/__init__.py              — CREATE: пустой __init__
app/config/avatars.py               — CREATE: AVATARS dict, DEFAULT_AVATAR_ID, get_avatar_emoji()
app/models/database.py              — EDIT: +avatar_id в User
app/core/migrations.py              — EDIT: +миграция 007_avatar_id
app/core/bootstrap.py               — EDIT: +avatar_id="emoji-default" в default User
app/schema/onboarding.py            — EDIT: +name, +avatar_id в OnboardingStatus, +UserProfile TypedDict
app/services/onboarding_service.py  — EDIT: complete() расширен, +update_profile(), +get_profile()
app/components/onboarding_wizard.py — EDIT: перестройка UI (имя + RadioItems аватарка + баланс)
app/components/sidebar.py           — EDIT: динамический профиль, clickable container, callback
app/components/profile_modal.py     — CREATE: модал редактирования (один callback)
app/components/dashboard.py         — EDIT: inline greeting (read User.name)
app/main.py                         — EDIT: +profile modal, +dcc.Store("profile-updated")
app/assets/onboarding.css           — EDIT: +avatar grid стили
app/assets/sidebar.css              — EDIT: +profile clickable стили
tests/test_onboarding_service.py    — EDIT: +тесты complete(), update_profile(), get_profile()
tests/test_avatars.py               — CREATE: тесты конфига аватарок
tests/test_migration_007.py         — CREATE: тест миграции avatar_id
```

## Ключевые интерфейсы

### 1. Конфиг аватарок

```python
# app/config/avatars.py
"""Конфигурация предустановленных emoji-аватарок."""

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

### 2. TypedDict для UserProfile

```python
# app/schema/onboarding.py — добавление
class UserProfile(TypedDict):
    """Данные профиля пользователя для UI."""
    name: str
    avatar_id: str

class OnboardingStatus(TypedDict):
    """Статус онбординга пользователя."""
    first_launch: bool
    starting_balance: Decimal
    needs_balance_alert: bool
    name: str          # NEW
    avatar_id: str     # NEW
```

### 3. Сервисный слой

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
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        clean_name = name.strip()
        if not clean_name or len(clean_name) > 50:
            raise ValueError("Name must be 1-50 characters")

        from app.config.avatars import AVATARS, DEFAULT_AVATAR_ID
        if avatar_id not in AVATARS:
            avatar_id = DEFAULT_AVATAR_ID

        user.name = clean_name
        user.avatar_id = avatar_id
        user.starting_balance = starting_balance
        user.first_launch = False
        self.session.flush()

    # Обратная совместимость (deprecated wrapper)
    def complete_with_balance(self, user_id: int, starting_balance: Decimal) -> None:
        """Deprecated. Используйте complete()."""
        self.complete(
            user_id=user_id,
            name="Пользователь",
            avatar_id="emoji-default",
            starting_balance=starting_balance,
        )

    def update_profile(self, user_id: int, name: str, avatar_id: str) -> None:
        """Обновить профиль пользователя (имя + аватарка)."""
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        clean_name = name.strip()
        if not clean_name or len(clean_name) > 50:
            raise ValueError("Name must be 1-50 characters")

        from app.config.avatars import AVATARS, DEFAULT_AVATAR_ID
        if avatar_id not in AVATARS:
            avatar_id = DEFAULT_AVATAR_ID

        user.name = clean_name
        user.avatar_id = avatar_id
        self.session.flush()

    def get_profile(self, user_id: int) -> UserProfile:
        """Получить name и avatar_id для отображения в UI."""
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return UserProfile(name=user.name, avatar_id=user.avatar_id)

    def get_status(self, user_id: int) -> OnboardingStatus:
        """Получить статус онбординга (расширенный)."""
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return OnboardingStatus(
            first_launch=user.first_launch,
            starting_balance=user.starting_balance,
            needs_balance_alert=user.starting_balance == Decimal("0"),
            name=user.name,
            avatar_id=user.avatar_id,
        )
```

### 4. Onboarding Wizard (перестроенный)

```python
# app/components/onboarding_wizard.py — полная перестройка

def create_onboarding_wizard() -> dbc.Modal:
    """Единый экран: имя (обязательно) + аватарка (RadioItems) + баланс (опционально)."""
    from app.config.avatars import AVATARS, DEFAULT_AVATAR_ID

    avatar_options = [
        {
            "label": html.Span(v["emoji"], className="avatar-option-label", title=v["label"]),
            "value": k,
        }
        for k, v in AVATARS.items()
    ]

    return dbc.Modal(
        id="onboarding-modal",
        is_open=False,
        backdrop="static",
        keyboard=False,
        centered=True,
        className="onboarding-modal",
        children=[
            dbc.ModalHeader(dbc.ModalTitle("Добро пожаловать в FinFocus!"), close_button=False),
            dbc.ModalBody([
                html.Label("Ваше имя", className="fw-semibold mb-2"),
                dbc.Input(id="onboarding-name-input", type="text", placeholder="Введите имя", maxLength=50, className="mb-3"),

                html.Label("Выберите аватарку", className="fw-semibold mb-2"),
                dbc.RadioItems(
                    id="onboarding-avatar-selector",
                    options=avatar_options,
                    value=DEFAULT_AVATAR_ID,
                    inline=True,
                    className="avatar-grid mb-3",
                    inputClassName="avatar-radio-hidden",
                    labelClassName="avatar-option",
                    labelCheckedClassName="avatar-option-selected",
                ),

                html.Label("Текущий остаток на счетах", className="fw-semibold mb-2"),
                dbc.InputGroup([
                    dbc.Input(id="onboarding-balance-input", type="number", placeholder="0.00", step="0.01", className="onboarding-balance-input"),
                    dbc.InputGroupText("₽"),
                ], className="mb-2"),
                html.Div(id="onboarding-balance-warning", className="onboarding-warning text-warning", style={"display": "none"}, children="Отрицательный баланс — вы уверены?"),
                html.Small("Вы сможете изменить баланс позже через Сверку.", className="text-muted"),
            ]),
            dbc.ModalFooter([
                dbc.Button("Пропустить", id="onboarding-skip-btn", color="secondary", outline=True, className="me-2"),
                dbc.Button("Продолжить", id="onboarding-submit-btn", color="success", disabled=True),
            ], className="justify-content-end"),
        ],
    )
```

**Callback flow:**

```python
# Callback 1: check_onboarding_and_validate
#   Inputs: url.pathname, onboarding-name-input.value, onboarding-balance-input.value
#   Outputs: onboarding-modal.is_open, onboarding-submit-btn.disabled, onboarding-balance-warning.style
#   Логика:
#     url trigger -> check first_launch from DB
#     name trigger -> has_name = bool(name.strip()) -> disabled = not has_name
#     balance trigger -> warning for negative

# Callback 2: handle_onboarding_action
#   Inputs: onboarding-submit-btn.n_clicks, onboarding-skip-btn.n_clicks
#   States: onboarding-name-input.value, onboarding-avatar-selector.value, onboarding-balance-input.value
#   Outputs: onboarding-modal.is_open (allow_duplicate=True), profile-updated.data
#   Логика:
#     submit -> complete(name, avatar, balance) + timestamp
#     skip -> skip() + timestamp
```

### 5. Sidebar (динамический профиль)

```python
# app/components/sidebar.py

def create_sidebar():
    profile = html.Div(
        id="sidebar-profile-container",
        n_clicks=0,
        children=[
            html.Div(id="sidebar-profile-avatar", children="😊", ...),  # Default
            html.Div([
                html.Div(id="sidebar-profile-name", children="Пользователь", ...),
                html.Div("Профиль ✏️", className="text-muted", style={"fontSize": "12px"}),
            ]),
        ],
        className="d-flex align-items-center gap-3 px-4 pt-4 pb-2 sidebar-profile-clickable",
        style={"cursor": "pointer"},
    )
    # ... rest unchanged

# Callback: обновление профиля
@callback(
    [Output("sidebar-profile-name", "children"), Output("sidebar-profile-avatar", "children")],
    [Input("url", "pathname"), Input("profile-updated", "data")],
    prevent_initial_call=False,
)
def update_sidebar_profile(pathname, profile_updated):
    """Обновляет имя и аватарку в sidebar из БД. Fallback: defaults."""
    try:
        with get_db_session() as session:
            profile = OnboardingService(session).get_profile(DEFAULT_USER_ID)
        return profile["name"], get_avatar_emoji(profile["avatar_id"])
    except Exception:
        return "Пользователь", "😊"
```

### 6. Profile Modal (один callback)

```python
# app/components/profile_modal.py

# Единственный callback: open / save / cancel
@callback(
    [
        Output("profile-modal", "is_open"),
        Output("profile-name-input", "value"),
        Output("profile-avatar-selector", "value"),
        Output("profile-updated", "data", allow_duplicate=True),
    ],
    [
        Input("sidebar-profile-container", "n_clicks"),
        Input("profile-save-btn", "n_clicks"),
        Input("profile-cancel-btn", "n_clicks"),
    ],
    [
        State("profile-name-input", "value"),
        State("profile-avatar-selector", "value"),
    ],
    prevent_initial_call=True,
)
def handle_profile_modal(open_clicks, save_clicks, cancel_clicks, name_value, avatar_value):
    """Open: load from DB. Save: write to DB + trigger sidebar. Cancel: close."""
    triggered_id = ctx.triggered_id
    if triggered_id == "sidebar-profile-container":
        profile = OnboardingService(session).get_profile(DEFAULT_USER_ID)
        return True, profile["name"], profile["avatar_id"], no_update
    elif triggered_id == "profile-save-btn":
        OnboardingService(session).update_profile(DEFAULT_USER_ID, name, avatar)
        return False, no_update, no_update, int(time.time() * 1000)
    elif triggered_id == "profile-cancel-btn":
        return False, no_update, no_update, no_update
```

### 7. Dashboard greeting (inline read)

```python
# app/components/dashboard.py — в create_dashboard_layout()
greeting_name = "Пользователь"
try:
    with get_db_session() as session:
        profile = OnboardingService(session).get_profile(DEFAULT_USER_ID)
        greeting_name = profile["name"]
except Exception:
    pass
# H4(f"Добро пожаловать, {greeting_name}!", ...)
```

### 8. main.py (интеграция)

```python
# Добавить:
from app.components.profile_modal import create_profile_modal

# В layout:
create_profile_modal(),                       # NEW
dcc.Store(id="profile-updated", data=None),   # NEW
```

## CSS стили

### Avatar Grid (onboarding.css)

```css
.avatar-grid { display: flex; flex-wrap: wrap; gap: 10px; }
.avatar-radio-hidden { display: none !important; }
.avatar-option {
    display: flex; align-items: center; justify-content: center;
    width: 56px; height: 56px; border-radius: 50%;
    background: rgba(255, 255, 255, 0.5);
    border: 2px solid rgba(0, 0, 0, 0.1);
    cursor: pointer; transition: all 0.2s ease;
    font-size: 1.75rem; padding: 0;
}
.avatar-option:hover {
    border-color: var(--color-primary);
    background: rgba(46, 204, 113, 0.08);
    transform: scale(1.05);
}
.avatar-option-selected {
    border-color: var(--color-primary) !important;
    background: rgba(46, 204, 113, 0.15) !important;
    box-shadow: 0 0 12px var(--color-primary-glow);
    transform: scale(1.1);
}
```

### Sidebar Profile (sidebar.css)

```css
.sidebar-profile-clickable {
    cursor: pointer; border-radius: 12px; transition: background 0.2s ease;
}
.sidebar-profile-clickable:hover {
    background: rgba(46, 204, 113, 0.08);
}
```

## Модель данных

### User (расширение)
```python
avatar_id = Column(String(20), default="emoji-default", nullable=False)
```

### Миграция 007
```python
if not _column_exists(cursor, "users", "avatar_id"):
    cursor.execute(
        "ALTER TABLE users ADD COLUMN avatar_id VARCHAR(20) DEFAULT 'emoji-default' NOT NULL"
    )
    applied.append("007_avatar_id")
```

## Обработка ошибок

1. **Onboarding submit**: strip + length check (client + server). Fail-closed.
2. **Profile modal save**: Аналогичная валидация. Fallback avatar_id.
3. **Sidebar read**: Fail-closed, defaults.
4. **Dashboard greeting**: Graceful degradation (inline try/except).
5. **Миграция 007**: Идемпотентна.
6. **skip()**: Только `first_launch=False`, defaults из bootstrap.

## План реализации

**Батч 1: Data Layer** — `config/__init__.py`, `config/avatars.py`, `models/database.py`
**Батч 2: Migration + Bootstrap + Schema** — `core/migrations.py`, `core/bootstrap.py`, `schema/onboarding.py`
**Батч 3: Service Layer** — `services/onboarding_service.py`
**Батч 4: Onboarding UI** — `components/onboarding_wizard.py`, `assets/onboarding.css`
**Батч 5: Sidebar + Profile Modal** — `components/sidebar.py`, `components/profile_modal.py`, `assets/sidebar.css`
**Батч 6: Main + Dashboard** — `main.py`, `components/dashboard.py`
**Батч 7: Tests** — `test_avatars.py`, `test_onboarding_service.py`, `test_migration_007.py`

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Store allow_duplicate: оба writer'а (onboarding + profile modal) | Средняя | allow_duplicate=True на profile modal output |
| Sidebar двойной вызов (url + profile-updated) | Низкая | Идемпотентный read, безвредно |
| Inline DB read в create_dashboard_layout() | Низкая | Single-user SQLite, ~1ms |
| RadioItems value не обновляется | Низкая | Нативный механизм dbc.RadioItems |

## Requirements Traceability Matrix (RTM)

| # | Requirement | Реализация | Тип |
|---|------------|-----------|-----|
| R1 | avatar_id в User + миграция 007 | database.py + migrations.py | Data |
| R2 | config/avatars.py, 10 emoji | avatars.py | Config |
| R3 | Onboarding: имя + аватарка + баланс | onboarding_wizard.py (RadioItems) | UI |
| R3.1 | "Продолжить" disabled пока имя пустое | check_onboarding_and_validate callback | UI |
| R3.2 | Аватарка подсвечена зелёным + glow | CSS .avatar-option-selected | UI |
| R3.3 | "Пропустить": defaults из bootstrap | skip() -> first_launch=False | Logic |
| R4 | complete(name, avatar_id, balance) | OnboardingService.complete() | Service |
| R4.1 | update_profile(name, avatar_id) | OnboardingService.update_profile() | Service |
| R4.2 | get_profile() -> UserProfile | OnboardingService.get_profile() | Service |
| R5 | Sidebar: name + avatar из БД | sidebar.py callback | UI |
| R5.1 | Клик по профилю -> модал | sidebar-profile-container n_clicks | UI |
| R5.2 | Sidebar обновляется после save | Input("profile-updated") | Callback |
| R6 | Глобальный модал: имя + аватарка | profile_modal.py + main.py | UI |
| R6.1 | При открытии подгрузить данные | handle_profile_modal open branch | Callback |
| R7 | Dashboard greeting с именем | Inline read в create_dashboard_layout() | UI |
| R8 | Bootstrap с avatar_id | bootstrap.py | Data |
| R9 | Unit тесты | test_avatars.py, test_onboarding_service.py, test_migration_007.py | Test |

## Blast Radius

### Прямые изменения
- `app/config/__init__.py` — CREATE
- `app/config/avatars.py` — CREATE
- `app/components/profile_modal.py` — CREATE
- `tests/test_avatars.py` — CREATE
- `tests/test_migration_007.py` — CREATE
- `app/models/database.py` — EDIT (+avatar_id)
- `app/core/migrations.py` — EDIT (+007)
- `app/core/bootstrap.py` — EDIT (+avatar_id)
- `app/schema/onboarding.py` — EDIT (+UserProfile, +name/avatar_id)
- `app/services/onboarding_service.py` — EDIT (complete, deprecated wrapper, update_profile, get_profile)
- `app/components/onboarding_wizard.py` — EDIT (полная перестройка)
- `app/components/sidebar.py` — EDIT (динамический профиль)
- `app/components/dashboard.py` — EDIT (inline greeting)
- `app/main.py` — EDIT (+profile modal, +Store)
- `app/assets/onboarding.css` — EDIT (+avatar grid)
- `app/assets/sidebar.css` — EDIT (+profile clickable)
- `tests/test_onboarding_service.py` — EDIT (+тесты)

### Связанные файлы
- `app/core/database.py` — get_db_session() (read-only)
- `app/schema/__init__.py` — re-export UserProfile
- `app/assets/custom.css` — CSS переменные
- `tests/conftest.py` — fixture db_session

### Проверить после реализации
- [ ] pytest -k "not test_budget_change_updates_allocation" — все тесты
- [ ] black app/ + flake8 app/
- [ ] Onboarding: три поля, disabled пока имя пустое
- [ ] "Пропустить" → defaults
- [ ] Sidebar: имя + аватарка из БД
- [ ] Dashboard: "Добро пожаловать, {имя}!"
- [ ] Профиль редактируется, sidebar обновляется
- [ ] Миграция 007 идемпотентна
- [ ] complete_with_balance() deprecated wrapper работает

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|-----|-----|
| 🔴 #1: Dashboard greeting ReferenceError | Inline read в create_dashboard_layout(), без callback |
| 🟡 #2: Avatar selection не описан | dbc.RadioItems + inputClassName="avatar-radio-hidden" + CSS labels |
| 🟡 #3: Onboarding callback flow не описан | Явный flow: 2 callback, Inputs/Outputs/States описаны |
| 🟡 #4: Sidebar profile container id | id="sidebar-profile-container", n_clicks=0, clickable div |
| 🟡 #5: Profile modal dual output | Один callback handle_profile_modal(), allow_duplicate на profile-updated |
| 🟢 #6: TypedDict для get_profile() | UserProfile TypedDict в schema/onboarding.py |
| 🟢 #7: skip() defaults | skip() только first_launch=False, defaults из bootstrap |
| 🟢 #8: Breaking change complete_with_balance() | Deprecated wrapper сохранён |

## Ответы на вопросы критика

1. **Avatar selection**: dbc.RadioItems, нативный single-selection
2. **Dashboard greeting real-time**: Не нужен, inline read при навигации
3. **Sidebar click target**: Весь container, n_clicks
4. **Profile modal callback**: Один callback, разветвление по ctx.triggered_id
5. **skip() defaults**: Полагается на bootstrap
