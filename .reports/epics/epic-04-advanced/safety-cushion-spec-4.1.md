# Epic-04.1: Финансовая подушка — Backend + Goals UI

**Статус:** Ready for Implementation
**Протокол:** 4.1 (первый из двух)
**Дата:** 2026-01-28
**Зависимости:** Нет
**Следующий:** safety-cushion-spec-4.2.md (Calendar Integration)

---

## Цель протокола

Реализовать backend-логику и UI карточки/модала подушки на странице `/goals`. После этого протокола пользователь сможет настроить подушку, но визуализация в календаре будет в протоколе 4.2.

---

## Scope протокола 4.1

### Включено
- Schema: 3 новых поля в User
- TypedDicts: CushionSettings, CushionScenario
- SafetyCushionService: CRUD + калькулятор рекомендаций
- Goals UI: карточка подушки (два состояния)
- Goals UI: модал настройки (цель, порог, сценарии)
- Unit тесты для сервиса

### Исключено (протокол 4.2)
- CalendarService расширение
- Calendar UI подсветка
- Calendar CSS
- KPI в шапке календаря

---

## Архитектурные решения (из основной спеки)

### D001: Хранение в User, а не как Goal

Настройки подушки хранятся в полях User:
```python
cushion_target: Decimal = 0           # Целевая сумма (0 = не настроена)
cushion_threshold: Decimal = 0        # Минимальный порог для календаря
cushion_threshold_manual: bool = False  # True если порог изменён вручную
```

### D002: Расположение — карточка на /goals

Карточка вверху страницы, над блоком бюджета:
```
┌─────────────────────────────────────┐
│ 🛡️ Финансовая подушка              │  ← Этот протокол
├─────────────────────────────────────┤
│ 💰 Бюджет накоплений                │
├─────────────────────────────────────┤
│ 🎯 Цели                             │
└─────────────────────────────────────┘
```

### D003-D006

- Подушка всегда существует (target=0 → "Настроить")
- current_amount = текущий баланс (CalendarService)
- Сценарии без БД (UI калькулятор)
- Нельзя удалить, только сбросить

---

## Структура данных

### User (новые поля)

**Файл:** `app/models/database.py`

```python
class User(Base):
    # ... существующие поля ...

    # Финансовая подушка
    cushion_target = Column(Numeric(10, 2), default=0, nullable=False)
    cushion_threshold = Column(Numeric(10, 2), default=0, nullable=False)
    cushion_threshold_manual = Column(Boolean, default=False, nullable=False)
```

**Миграция:** Пересоздать БД (dev stage).

### TypedDicts

**Файл:** `app/schema/cushion.py` (новый)

```python
from decimal import Decimal
from typing import TypedDict


class CushionSettings(TypedDict):
    """Настройки подушки из User."""
    target: Decimal           # cushion_target
    threshold: Decimal        # cushion_threshold
    threshold_manual: bool    # cushion_threshold_manual
    current_amount: Decimal   # вычисляется (текущий баланс)
    progress: float           # вычисляется (current / target * 100)
    is_configured: bool       # target > 0


class CushionScenario(TypedDict):
    """Сценарий для калькулятора (не сохраняется в БД)."""
    name: str
    min_amount: Decimal
    max_amount: Decimal
```

### Edge Cases

| Случай | Поведение |
|--------|-----------|
| `current_amount < 0` | progress = 0% |
| `current_amount > target` | progress = 100% (cap) |
| `target = 0` | Показать "Настроить" |
| `threshold > target` | Разрешить |

---

## SafetyCushionService

**Файл:** `app/services/cushion_service.py` (новый)

```python
from decimal import Decimal
from app.schema.cushion import CushionSettings, CushionScenario


class SafetyCushionService:
    """Сервис для работы с финансовой подушкой."""

    def __init__(self, session):
        self.session = session

    def get_settings(self, user_id: int) -> CushionSettings:
        """Получить настройки подушки с вычисленными полями."""
        user = self._get_user(user_id)
        current = self._get_current_balance(user_id)

        target = user.cushion_target or Decimal(0)
        progress = 0.0
        if target > 0:
            progress = min(float(current / target * 100), 100.0)
            if current < 0:
                progress = 0.0

        return CushionSettings(
            target=target,
            threshold=user.cushion_threshold or Decimal(0),
            threshold_manual=user.cushion_threshold_manual,
            current_amount=current,
            progress=progress,
            is_configured=target > 0,
        )

    def update_settings(
        self,
        user_id: int,
        target: Decimal,
        threshold: Decimal,
        threshold_manual: bool,
    ) -> None:
        """Обновить настройки подушки."""
        user = self._get_user(user_id)
        user.cushion_target = target
        user.cushion_threshold = threshold
        user.cushion_threshold_manual = threshold_manual
        self.session.flush()

    def reset_settings(self, user_id: int) -> None:
        """Сбросить настройки подушки."""
        self.update_settings(user_id, Decimal(0), Decimal(0), False)

    def calculate_recommendation(
        self,
        scenarios: list[CushionScenario],
        mode: str,  # "sum" | "max_scenario"
    ) -> Decimal:
        """Рассчитать рекомендуемую цель по сценариям."""
        if not scenarios:
            return Decimal(0)

        if mode == "sum":
            return sum(s["max_amount"] for s in scenarios)
        else:  # max_scenario
            return max(s["max_amount"] for s in scenarios)

    def _get_current_balance(self, user_id: int) -> Decimal:
        """Получить текущий баланс через CalendarService."""
        from app.services.calendar_service import CalendarService
        from datetime import date

        calendar_service = CalendarService(self.session)
        return calendar_service.get_balance_on_date(user_id, date.today())

    def _get_user(self, user_id: int):
        from app.models.database import User
        return self.session.query(User).filter_by(id=user_id).one()
```

---

## Goals UI — Карточка подушки

**Файл:** `app/components/goals.py`

### Состояние "Не настроена"

```
┌─────────────────────────────────────┐
│ 🛡️ Финансовая подушка              │
│                                     │
│ Создайте финансовую подушку для     │
│ защиты от непредвиденных расходов   │
│                                     │
│         [Настроить]                 │
└─────────────────────────────────────┘
```

### Состояние "Настроена"

```
┌─────────────────────────────────────┐
│ 🛡️ Финансовая подушка              │
│                                     │
│ Цель: 150 000 ₽                     │
│ Сейчас: 95 000 ₽                    │
│                                     │
│ [━━━━━━━━━░░░░░░░] 63%             │
│      ↑ порог (30%)                  │
│                                     │
│ [Настроить]                         │
└─────────────────────────────────────┘
```

### Функция

```python
def build_cushion_card(settings: CushionSettings) -> dbc.Card:
    """Построить карточку подушки безопасности."""
    if not settings["is_configured"]:
        return _build_cushion_card_unconfigured()
    return _build_cushion_card_configured(settings)
```

### Прогресс-бар

- Заливка: зелёная при >= threshold, оранжевая при < threshold
- Маркер порога: вертикальная полоска на `threshold / target * 100%`

---

## Goals UI — Модал настройки

**Файл:** `app/components/goals.py` или `app/components/cushion_modal.py`

### Макет

```
┌─────────────────────────────────────────────┐
│ Настройка финансовой подушки            [×] │
├─────────────────────────────────────────────┤
│                                             │
│ Цель подушки                                │
│ ┌─────────────────────────────────────────┐ │
│ │ 150 000                               ₽ │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Минимальный остаток на счёте                │
│ ┌─────────────────────────────────────────┐ │
│ │ 45 000                                ₽ │ │
│ └─────────────────────────────────────────┘ │
│ (по умолчанию 30% от цели)                  │
│                                             │
│ ▼ Рассчитать по сценариям                   │
│ ┌─────────────────────────────────────────┐ │
│ │ Сценарий 1: Медицина                    │ │
│ │ от [10 000] до [50 000] ₽          [×]  │ │
│ │                                         │ │
│ │ [+ Добавить сценарий]                   │ │
│ │                                         │ │
│ │ Режим расчёта:                          │ │
│ │ (○) Сумма всех сценариев                │ │
│ │ (●) По самому дорогому                  │ │
│ │                                         │ │
│ │ Рекомендованная цель: 80 000 ₽          │ │
│ │ [Применить]                             │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ ┌─────────────┐  ┌─────────────────────┐    │
│ │ Сбросить    │  │ Сохранить           │    │
│ └─────────────┘  └─────────────────────┘    │
└─────────────────────────────────────────────┘
```

### Поведение

1. **Цель подушки** — число ≥ 0, при изменении пересчитать порог на 30% (если не manual)
2. **Минимальный остаток** — при ручном изменении установить threshold_manual = True
3. **Сценарии** — collapsible, max 5, не сохраняются в БД
4. **Режим расчёта** — "sum" или "max_scenario"
5. **Применить** — копирует рекомендацию в поле цели
6. **Сбросить** — обнуляет все поля
7. **Сохранить** — записывает в User, закрывает модал

### Валидация

| Поле | Правило | Ошибка |
|------|---------|--------|
| Цель | число ≥ 0 | "Введите положительное число" |
| Порог | число ≥ 0 | "Введите положительное число" |
| Сценарий: название | не пустое | "Введите название" |
| Сценарий: max | ≥ min | "Максимум ≥ минимума" |

### dcc.Store (временные данные модала)

```python
dcc.Store(id="cushion-scenarios-store", data=[])      # list[CushionScenario]
dcc.Store(id="cushion-calc-mode", data="max_scenario")  # "sum" | "max_scenario"
dcc.Store(id="cushion-modal-trigger", data=0)         # для refresh карточки
```

### Callbacks

1. `open_cushion_modal()` — открытие модала, загрузка текущих настроек
2. `update_threshold_on_target_change()` — автопересчёт порога
3. `add_scenario()` / `remove_scenario()` — управление списком сценариев
4. `calculate_recommendation()` — расчёт по сценариям
5. `apply_recommendation()` — копирование в поле цели
6. `save_cushion_settings()` — сохранение в БД
7. `reset_cushion_settings()` — сброс настроек

### Refresh после сохранения

1. **Модал → Карточка**: callback `refresh_cushion_card()` слушает `cushion-modal-trigger`
2. **Карточка → Календарь**: при переходе на /calendar данные загрузятся свежие
3. **Глобальный trigger не нужен** — подушка не влияет на транзакции

### User ID

В текущей системе используется `user_id = 1` (hardcoded в UI callbacks).
Сервис принимает `user_id` как параметр для будущей multi-user поддержки.

---

## Технический план

### Шаг 1: Schema + миграция

**Файл:** `app/models/database.py`
- Добавить 3 поля в User
- Пересоздать БД

### Шаг 2: TypedDicts

**Файл:** `app/schema/cushion.py` (новый)
- CushionSettings
- CushionScenario
- Обновить `app/schema/__init__.py`

### Шаг 3: SafetyCushionService

**Файл:** `app/services/cushion_service.py` (новый)
- get_settings(), update_settings(), reset_settings()
- calculate_recommendation()
- Обновить `app/services/__init__.py`

### Шаг 4: Карточка подушки

**Файл:** `app/components/goals.py`
- build_cushion_card()
- _build_cushion_card_unconfigured()
- _build_cushion_card_configured()
- Интеграция в create_goals_layout()

### Шаг 5: Модал настройки

**Файл:** `app/components/goals.py` или `cushion_modal.py`
- build_cushion_modal()
- dcc.Store компоненты
- 7 callbacks

### Шаг 6: CSS стили

**Файл:** `app/assets/goals.css`
- .cushion-card, .cushion-progress-bar, .cushion-threshold-marker

### Шаг 7: Unit тесты

**Файл:** `tests/test_cushion_service.py`
- test_get_settings_unconfigured()
- test_get_settings_configured()
- test_update_settings()
- test_reset_settings()
- test_calculate_recommendation_sum()
- test_calculate_recommendation_max()
- test_progress_edge_cases()

---

## Acceptance Criteria (протокол 4.1)

### Карточка на /goals
- [ ] Карточка подушки **всегда** отображается вверху
- [ ] Если target = 0 → "Настроить подушку"
- [ ] Если target > 0 → прогресс (current = текущий баланс)
- [ ] Прогресс-бар с маркером порога
- [ ] Клик → модал настройки

### Модал настройки
- [ ] Поле "Цель" — число ≥ 0
- [ ] Поле "Порог" — по умолчанию 30% от цели
- [ ] Автопересчёт порога при изменении цели
- [ ] threshold_manual = True при ручном изменении
- [ ] Сценарии: добавление/удаление (max 5)
- [ ] Режим расчёта: сумма / максимум
- [ ] Кнопка "Применить" → в поле цели
- [ ] Кнопка "Сбросить" → обнуление
- [ ] Кнопка "Сохранить" → в БД

### Backend
- [ ] User.cushion_target, cushion_threshold, cushion_threshold_manual
- [ ] SafetyCushionService работает
- [ ] Unit тесты проходят

---

## Результат протокола

После завершения:
- Пользователь может настроить подушку на /goals
- Видит прогресс (текущий баланс vs цель)
- Может использовать калькулятор сценариев
- **Визуализация в календаре — в протоколе 4.2**

---

## Ссылки

- Основная спека: `safety-cushion-spec.md`
- Протокол 4.2: `safety-cushion-spec-4.2.md`
- ROADMAP.md: Epic-04 (Advanced Features)
