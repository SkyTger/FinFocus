# Solution v3: User Profile с emoji-аватарками (финальная)

## Обзор решения

Расширяем модель User полем `avatar_id`, перестраиваем Onboarding Wizard в единый экран (имя + аватарка + баланс), делаем sidebar динамическим через callback с чтением из БД, добавляем глобальный модал редактирования профиля в `main.py`. Dashboard greeting читается inline при вызове `create_dashboard_layout()`. Все замечания critique-v2 учтены: session management в profile modal, DRY-валидация через приватный метод, логирование в except-блоках.

## Архитектура

### Компоненты

1. **Data Layer**: `User.avatar_id` + миграция 007 + конфиг `app/config/avatars.py`
2. **Service Layer**: `OnboardingService.complete()` (новая сигнатура) + `update_profile()` + `get_profile()` + приватный `_validate_profile_fields()`
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

**Dashboard greeting (обновляется только при навигации -- документировано):**
```
display_page("/dashboard")
  -> create_dashboard_layout()
  -> inline: session.get(User, 1).name -> H4("Добро пожаловать, {name}!")
  -> При изменении имени на dashboard -- обновится после перехода на другую страницу.
     Это приемлемо для single-user приложения.
```

## Файловая структура

```
app/config/__init__.py              — CREATE: пустой __init__
app/config/avatars.py               — CREATE: AVATARS dict, DEFAULT_AVATAR_ID, get_avatar_emoji()
app/models/database.py              — EDIT: +avatar_id в User
app/core/migrations.py              — EDIT: +миграция 007_avatar_id
app/core/bootstrap.py               — EDIT: +avatar_id="emoji-default" в default User
app/schema/onboarding.py            — EDIT: +name, +avatar_id в OnboardingStatus, +UserProfile TypedDict
app/services/onboarding_service.py  — EDIT: complete() расширен, +_validate_profile_fields(), +update_profile(), +get_profile(), deprecated wrapper
app/components/onboarding_wizard.py — EDIT: перестройка UI (имя + RadioItems аватарка + баланс)
app/components/sidebar.py           — EDIT: динамический профиль, clickable container, callback
app/components/profile_modal.py     — CREATE: модал редактирования (один callback с session management)
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
from typing import TypedDict

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

### 3. Сервисный слой (с DRY-валидацией и module-level imports)

```python
# app/services/onboarding_service.py — расширение
from app.config.avatars import AVATARS, DEFAULT_AVATAR_ID  # module-level import
from app.schema.onboarding import OnboardingStatus, UserProfile


class OnboardingService:

    def _validate_profile_fields(self, name: str, avatar_id: str) -> tuple[str, str]:
        """Валидирует и нормализует имя и avatar_id.

        Args:
            name: Имя пользователя (raw input).
            avatar_id: ID аватарки.

        Returns:
            Кортеж (clean_name, valid_avatar_id).

        Raises:
            ValueError: Если имя пустое или длиннее 50 символов.

        Note:
            Валидация имени ограничена 50 символами (UX-лимит),
            при том что User.name модель допускает до 100 символов (запас в БД).
        """
        clean_name = name.strip()
        if not clean_name or len(clean_name) > 50:
            raise ValueError("Name must be 1-50 characters")
        if avatar_id not in AVATARS:
            avatar_id = DEFAULT_AVATAR_ID
        return clean_name, avatar_id

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

        clean_name, valid_avatar_id = self._validate_profile_fields(name, avatar_id)

        user.name = clean_name
        user.avatar_id = valid_avatar_id
        user.starting_balance = starting_balance
        user.first_launch = False
        self.session.flush()

    # Обратная совместимость (deprecated wrapper)
    def complete_with_balance(self, user_id: int, starting_balance: Decimal) -> None:
        """Deprecated. Используйте complete()."""
        self.complete(
            user_id=user_id,
            name="Пользователь",
            avatar_id=DEFAULT_AVATAR_ID,
            starting_balance=starting_balance,
        )

    def update_profile(self, user_id: int, name: str, avatar_id: str) -> None:
        """Обновить профиль пользователя (имя + аватарка)."""
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        clean_name, valid_avatar_id = self._validate_profile_fields(name, avatar_id)

        user.name = clean_name
        user.avatar_id = valid_avatar_id
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
                dbc.Input(id="onboarding-name-input", type="text", placeholder="Как вас зовут?", maxLength=50, className="mb-3"),

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

**Callback flow (с ctx.triggered_id оптимизацией):**

```python
# Callback 1: check_onboarding_and_validate
#   Inputs: url.pathname, onboarding-name-input.value, onboarding-balance-input.value
#   Outputs: onboarding-modal.is_open, onboarding-submit-btn.disabled, onboarding-balance-warning.style
#   Логика по ctx.triggered_id:
#     "url" / None -> check first_launch from DB (only DB call here)
#     "onboarding-name-input" -> has_name = bool(name.strip()) -> disabled = not has_name (NO DB call)
#     "onboarding-balance-input" -> warning for negative (NO DB call)

# Callback 2: handle_onboarding_action
#   Inputs: onboarding-submit-btn.n_clicks, onboarding-skip-btn.n_clicks
#   States: onboarding-name-input.value, onboarding-avatar-selector.value, onboarding-balance-input.value
#   Outputs: onboarding-modal.is_open (allow_duplicate=True), profile-updated.data
#   Логика:
#     submit -> complete(name, avatar, balance) + session.commit() + timestamp
#     skip -> skip() + session.commit() + timestamp
```

### 5. Sidebar (динамический профиль с логированием)

```python
# app/components/sidebar.py
from loguru import logger  # project standard

def create_sidebar():
    profile = html.Div(
        id="sidebar-profile-container",
        n_clicks=0,
        children=[
            html.Div(id="sidebar-profile-avatar", children="😊",
                className="d-flex align-items-center justify-content-center",
                style={
                    "width": "48px", "height": "48px", "borderRadius": "50%",
                    "background": "rgba(46, 204, 113, 0.15)",
                    "border": "1px solid rgba(255,255,255,0.4)",
                    "fontSize": "1.5rem",
                },
            ),
            html.Div([
                html.Div(id="sidebar-profile-name", children="Пользователь",
                    className="fw-bold", style={"fontSize": "14px", "lineHeight": "1.2"}),
                html.Div("Профиль ✏️", className="text-muted", style={"fontSize": "12px"}),
            ]),
        ],
        className="d-flex align-items-center gap-3 px-4 pt-4 pb-2 sidebar-profile-clickable",
        style={"cursor": "pointer"},
    )
    # ... rest unchanged

# Callback: обновление профиля с логированием
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
        logger.warning("Failed to load user profile for sidebar, using defaults", exc_info=True)
        return "Пользователь", "😊"
```

### 6. Profile Modal (с полным session management)

```python
# app/components/profile_modal.py
import time
from loguru import logger

import dash_bootstrap_components as dbc
from dash import callback, ctx, html, no_update, Input, Output, State

from app.config.avatars import AVATARS, DEFAULT_AVATAR_ID, get_avatar_emoji
from app.core.database import get_db_session
from app.services.onboarding_service import OnboardingService

DEFAULT_USER_ID = 1


def create_profile_modal() -> dbc.Modal:
    """Создает глобальный модал редактирования профиля (имя + аватарка)."""
    from app.config.avatars import AVATARS, DEFAULT_AVATAR_ID

    avatar_options = [
        {
            "label": html.Span(v["emoji"], className="avatar-option-label", title=v["label"]),
            "value": k,
        }
        for k, v in AVATARS.items()
    ]

    return dbc.Modal(
        id="profile-modal",
        is_open=False,
        centered=True,
        className="profile-modal",
        children=[
            dbc.ModalHeader(dbc.ModalTitle("Редактировать профиль"), close_button=True),
            dbc.ModalBody([
                html.Label("Имя", className="fw-semibold mb-2"),
                dbc.Input(id="profile-name-input", type="text", placeholder="Введите имя", maxLength=50, className="mb-3"),

                html.Label("Аватарка", className="fw-semibold mb-2"),
                dbc.RadioItems(
                    id="profile-avatar-selector",
                    options=avatar_options,
                    value=DEFAULT_AVATAR_ID,
                    inline=True,
                    className="avatar-grid mb-3",
                    inputClassName="avatar-radio-hidden",
                    labelClassName="avatar-option",
                    labelCheckedClassName="avatar-option-selected",
                ),
            ]),
            dbc.ModalFooter([
                dbc.Button("Отмена", id="profile-cancel-btn", color="secondary", outline=True, className="me-2"),
                dbc.Button("Сохранить", id="profile-save-btn", color="success"),
            ]),
        ],
    )


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
def handle_profile_modal(
    open_clicks: int | None,
    save_clicks: int | None,
    cancel_clicks: int | None,
    name_value: str | None,
    avatar_value: str | None,
) -> tuple:
    """Open: load from DB. Save: write to DB + trigger sidebar. Cancel: close."""
    triggered_id = ctx.triggered_id

    if triggered_id == "sidebar-profile-container":
        try:
            with get_db_session() as session:
                profile = OnboardingService(session).get_profile(DEFAULT_USER_ID)
            return True, profile["name"], profile["avatar_id"], no_update
        except Exception:
            logger.warning("Failed to load profile for modal, using defaults", exc_info=True)
            return True, "Пользователь", DEFAULT_AVATAR_ID, no_update

    elif triggered_id == "profile-save-btn":
        try:
            with get_db_session() as session:
                OnboardingService(session).update_profile(
                    DEFAULT_USER_ID, name_value or "", avatar_value or DEFAULT_AVATAR_ID
                )
                session.commit()
            return False, no_update, no_update, int(time.time() * 1000)
        except ValueError as e:
            logger.warning(f"Profile validation failed: {e}")
            # Не закрываем модал при ошибке валидации
            return no_update, no_update, no_update, no_update
        except Exception:
            logger.error("Failed to save profile", exc_info=True)
            return False, no_update, no_update, no_update

    elif triggered_id == "profile-cancel-btn":
        return False, no_update, no_update, no_update

    raise PreventUpdate
```

### 7. Dashboard greeting (inline read с логированием)

```python
# app/components/dashboard.py — в create_dashboard_layout()
# Inline read имени для greeting.
# NOTE: Greeting обновляется только при навигации на /dashboard.
# При изменении имени через profile modal на этой же странице,
# обновление произойдет после перехода. Приемлемо для single-user.
greeting_name = "Пользователь"
try:
    with get_db_session() as session:
        profile = OnboardingService(session).get_profile(DEFAULT_USER_ID)
        greeting_name = profile["name"]
except Exception:
    logger.warning("Failed to load user name for dashboard greeting, using default", exc_info=True)

# В layout:
# html.H4(f"Добро пожаловать, {greeting_name}!", className="mb-0 fw-semibold")
```

### 8. main.py (интеграция)

```python
# Добавить:
from app.components.profile_modal import create_profile_modal

# В layout (после onboarding wizard):
create_profile_modal(),                       # NEW
dcc.Store(id="profile-updated", data=None),   # NEW
```

## CSS стили

### Avatar Grid (onboarding.css)

```css
/* === Avatar Grid === */
.avatar-grid { display: flex; flex-wrap: wrap; gap: 10px; }
.avatar-radio-hidden { display: none !important; }
.avatar-option {
    display: flex; align-items: center; justify-content: center;
    width: 56px; height: 56px; border-radius: 50%;
    background: rgba(255, 255, 255, 0.5);
    border: 2px solid rgba(0, 0, 0, 0.1);
    cursor: pointer; transition: all 0.2s ease;
    font-size: 1.8rem; padding: 0;
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
/* === Sidebar Profile Clickable === */
.sidebar-profile-clickable {
    cursor: pointer; border-radius: 12px; transition: background 0.2s ease;
}
.sidebar-profile-clickable:hover {
    background: rgba(46, 204, 113, 0.08);
}
```

### Profile Modal (onboarding.css -- reuse avatar-grid styles)

```css
/* Profile modal reuses .avatar-grid, .avatar-option, .avatar-option-selected */
.profile-modal .modal-content {
    border-radius: 12px;
    border: none;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}
```

## Модель данных

### User (расширение)
```python
# app/models/database.py — добавить поле в класс User
avatar_id = Column(String(20), default="emoji-default", nullable=False)
```

### Миграция 007
```python
# app/core/migrations.py — в run_all_migrations(), после 006
if not _column_exists(cursor, "users", "avatar_id"):
    cursor.execute(
        "ALTER TABLE users ADD COLUMN avatar_id VARCHAR(20) DEFAULT 'emoji-default' NOT NULL"
    )
    applied.append("007_avatar_id")
```

## Обработка ошибок

1. **Onboarding submit**: strip + length check через `_validate_profile_fields()` (server-side). Client-side: disabled button пока имя пустое.
2. **Profile modal save**: Аналогичная валидация через `_validate_profile_fields()`. При `ValueError` -- модал не закрывается, пользователь видит текущие данные. При unexpected error -- модал закрывается, логируется.
3. **Sidebar read**: `except Exception` c `logger.warning(..., exc_info=True)`, fallback defaults.
4. **Dashboard greeting**: `except Exception` с `logger.warning(..., exc_info=True)`, fallback "Пользователь".
5. **Миграция 007**: Идемпотентна через `_column_exists()`.
6. **skip()**: Только `first_launch=False`, defaults из bootstrap.

## План реализации

1. **Батч 1: Data Layer** -- `app/config/__init__.py`, `app/config/avatars.py`, `app/models/database.py` (добавить avatar_id в User)
2. **Батч 2: Migration + Bootstrap + Schema** -- `app/core/migrations.py` (миграция 007), `app/core/bootstrap.py` (avatar_id в default User), `app/schema/onboarding.py` (+UserProfile, +name/avatar_id в OnboardingStatus)
3. **Батч 3: Service Layer** -- `app/services/onboarding_service.py` (complete, _validate_profile_fields, update_profile, get_profile, deprecated wrapper), `app/schema/__init__.py` (re-export UserProfile)
4. **Батч 4: Onboarding UI** -- `app/components/onboarding_wizard.py` (перестройка), `app/assets/onboarding.css` (+avatar grid + profile modal styles)
5. **Батч 5: Sidebar + Profile Modal** -- `app/components/sidebar.py` (динамический профиль), `app/components/profile_modal.py` (CREATE), `app/assets/sidebar.css` (+profile clickable)
6. **Батч 6: Main + Dashboard** -- `app/main.py` (+profile modal, +Store), `app/components/dashboard.py` (inline greeting)
7. **Батч 7: Tests** -- `tests/test_avatars.py`, `tests/test_onboarding_service.py` (+тесты), `tests/test_migration_007.py`

## Зависимости

Новых внешних библиотек не требуется. Все компоненты (Dash, dbc, SQLAlchemy, loguru) уже в проекте.

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Store allow_duplicate: оба writer (onboarding + profile modal) | Средняя | allow_duplicate=True на profile modal output |
| Sidebar двойной вызов (url + profile-updated) | Низкая | Идемпотентный read, безвредно |
| Inline DB read в create_dashboard_layout() | Низкая | Single-user SQLite, ~1ms. Логирование ошибок. |
| RadioItems value не обновляется | Низкая | Нативный механизм dbc.RadioItems |
| Onboarding callback 1: лишние DB calls при вводе имени | Низкая | ctx.triggered_id check -- DB only на "url" trigger |
| OnboardingStatus потребители при расширении полей | Низкая | Единственный consumer -- get_status(). Проверить при реализации. |

## Requirements Traceability Matrix (RTM)

| # | Requirement (дословно из спецификации) | Секция spec | Реализация в solution | Тип |
|---|----------------------------------------|-------------|----------------------|-----|
| R1 | avatar_id (String(20), default="emoji-default") в модель User + миграция 007 | brief R1 | database.py +avatar_id, migrations.py 007 | Data |
| R2 | config/avatars.py с 10 emoji-вариантами | brief R2 | app/config/avatars.py (AVATARS dict, 10 entries) | Config |
| R3 | Onboarding Wizard -- единый экран: имя + аватарка + баланс | brief R3 | onboarding_wizard.py (RadioItems + name input + balance) | UI |
| R3.1 | Кнопка "Продолжить" disabled пока имя пустое | brief criteria | Callback 1: disabled = not bool(name.strip()) | UI |
| R3.2 | "Пропустить" сохраняет defaults | brief criteria | skip() -> first_launch=False, defaults из bootstrap | Logic |
| R4 | OnboardingService: complete(user_id, name, avatar_id, starting_balance) | brief R4 | OnboardingService.complete() | Service |
| R4.1 | update_profile(user_id, name, avatar_id) | brief R4 | OnboardingService.update_profile() | Service |
| R5 | Sidebar -- динамический профиль из БД | brief R5 | sidebar.py callback + profile-updated Store | UI |
| R5.1 | Клик по профилю -> модал | brief criteria | sidebar-profile-container n_clicks | UI |
| R6 | Модал редактирования профиля (глобальный в main.py) | brief R6 | profile_modal.py + main.py layout | UI |
| R7 | Dashboard greeting "Добро пожаловать, {имя}!" | brief R7 | Inline read в create_dashboard_layout() | UI |
| R8 | Bootstrap auto_bootstrap создает User с avatar_id | brief criteria | bootstrap.py +avatar_id="emoji-default" | Data |
| R9 | Unit тесты: complete(), config, миграция | brief criteria | test_avatars.py, test_onboarding_service.py, test_migration_007.py | Test |

## Blast Radius

### Прямые изменения (файлы которые будут изменены)
- `app/config/__init__.py` -- CREATE: пустой `__init__` для пакета
- `app/config/avatars.py` -- CREATE: конфиг 10 emoji-аватарок
- `app/components/profile_modal.py` -- CREATE: модал редактирования профиля
- `tests/test_avatars.py` -- CREATE: тесты конфига аватарок
- `tests/test_migration_007.py` -- CREATE: тест миграции avatar_id
- `app/models/database.py` -- EDIT: +avatar_id в User (строка ~109, рядом с first_launch)
- `app/core/migrations.py` -- EDIT: +007_avatar_id (после блока 006)
- `app/core/bootstrap.py` -- EDIT: +avatar_id="emoji-default" в default User creation
- `app/schema/onboarding.py` -- EDIT: +UserProfile TypedDict, +name/avatar_id в OnboardingStatus
- `app/schema/__init__.py` -- EDIT: +re-export UserProfile
- `app/services/onboarding_service.py` -- EDIT: +complete(), +_validate_profile_fields(), +update_profile(), +get_profile(), deprecated wrapper, module-level imports
- `app/components/onboarding_wizard.py` -- EDIT: полная перестройка UI (имя + RadioItems аватарка + баланс), callback flow с ctx.triggered_id
- `app/components/sidebar.py` -- EDIT: динамический профиль, clickable container, callback + loguru logging
- `app/components/dashboard.py` -- EDIT: inline greeting read с loguru logging
- `app/main.py` -- EDIT: +profile modal, +dcc.Store("profile-updated")
- `app/assets/onboarding.css` -- EDIT: +avatar grid styles, +profile modal styles
- `app/assets/sidebar.css` -- EDIT: +profile clickable styles
- `tests/test_onboarding_service.py` -- EDIT: +тесты complete(), update_profile(), get_profile(), _validate_profile_fields()

### Связанные файлы (могут быть затронуты)
- `app/core/database.py` -- get_db_session() используется в новых callbacks (read-only dependency)
- `app/assets/custom.css` -- CSS переменные --color-primary, --color-primary-glow (read-only dependency)
- `tests/conftest.py` -- fixture db_session может потребовать проверки при добавлении avatar_id в User

### Проверить после реализации
- [ ] `pytest -k "not test_budget_change_updates_allocation"` -- все тесты зелёные
- [ ] `black app/` + `flake8 app/` -- code quality
- [ ] Onboarding: три поля отображаются, "Продолжить" disabled пока имя пустое
- [ ] "Пропустить" -> defaults (name="Пользователь", avatar_id="emoji-default", balance=0)
- [ ] Sidebar: имя + аватарка из БД, обновляется после onboarding/profile save
- [ ] Клик по профилю в sidebar открывает модал с текущими данными
- [ ] Модал: сохранение обновляет sidebar, валидация пустого имени
- [ ] Dashboard: "Добро пожаловать, {имя}!" с актуальным именем
- [ ] Миграция 007 идемпотентна (повторный запуск безопасен)
- [ ] `complete_with_balance()` deprecated wrapper продолжает работать
- [ ] Bootstrap создает User с avatar_id="emoji-default"

## Учтённые замечания из критики

| Замечание из critique v2 | Как решено |
|------------------------------|------------|
| 🟡 #1: Profile modal callback: отсутствует DB session management (session откуда? нет commit! несоответствие имен параметров) | Полный pseudocode с `with get_db_session() as session:`, явный `session.commit()` в save-ветке, параметры `name_value`/`avatar_value` используются напрямую. Добавлена обработка ValueError (модал не закрывается) и unexpected Exception (модал закрывается + логирование). |
| 🟡 #2: Дублирование валидационной логики в complete() и update_profile() | Извлечен приватный метод `_validate_profile_fields(self, name, avatar_id) -> tuple[str, str]`. Оба метода вызывают его. Import `AVATARS`/`DEFAULT_AVATAR_ID` перенесен на уровень модуля. |
| 🟡 #3: Sidebar callback: except Exception с fallback без логирования | Добавлен `logger.warning("Failed to load user profile for sidebar, using defaults", exc_info=True)`. Аналогично для dashboard greeting inline try/except. Используется loguru (стандарт проекта, не stdlib logging). |
| 🟢 #4: OnboardingStatus TypedDict расширение -- проверить потребителей | Единственное место создания OnboardingStatus -- метод `get_status()`, который обновлен. Потребители (onboarding_wizard callbacks) используют only known keys, не ломаются. Отмечено в Рисках. |
| 🟢 #5: Onboarding Callback 1 -- три разных Input триггера, DB call при каждом keystroke | Callback 1 явно проверяет `ctx.triggered_id`: DB call ТОЛЬКО на "url"/None trigger, валидация имени/баланса -- без DB call. Документировано в callback flow. |
| 🟢 #6: User.name column max length 100 vs валидация 50 | Добавлен комментарий в `_validate_profile_fields()` docstring: "Валидация имени ограничена 50 символами (UX-лимит), при том что User.name модель допускает до 100 символов (запас в БД)". Решение пользователя: оставить 50 в валидации, задокументировать. |

## Ответы на вопросы критика

1. **Вопрос:** User.name max length: В модели `String(100)`, в валидации `len() > 50`. Какой лимит правильный? Стоит ли согласовать?
   **Ответ:** Решение пользователя: оставить 50 в валидации (модель String(100) -- запас в БД, UX-wise 50 достаточно для имени). Добавлен комментарий в docstring `_validate_profile_fields()` о намеренном расхождении.

2. **Вопрос:** Dashboard greeting при изменении имени на dashboard: greeting обновится только после перехода на другую страницу и обратно. Это приемлемо?
   **Ответ:** Решение пользователя: обновление только при навигации приемлемо для single-user приложения. Поведение задокументировано комментарием в `create_dashboard_layout()` рядом с inline read.
