# Solution v3: Финансовая подушка безопасности (финальная версия)

## Обзор изменений v2 -> v3

1. **NewType Percent для type safety** - Добавлен `Percent = NewType("Percent", int)` с range 0-100 и функция валидации `_validate_percent()`
2. **Комментарий DEFAULT_THRESHOLD_PERCENT** - 3-строчный комментарий объясняющий выбор значения 30%
3. **Документация threshold_manual поведения** - Обновлён docstring callback #3 с явным объяснением: manual=True при любом изменении input

---

## Изменение #1: NewType Percent для type safety

### app/schema/cushion.py (полный файл)

```python
"""TypedDicts для финансовой подушки безопасности."""

from decimal import Decimal
from typing import NewType, TypedDict


# NewType для процентов (0-100) - type safety на уровне IDE/type checker
Percent = NewType("Percent", int)


class CushionSettings(TypedDict):
    """Настройки подушки из User.

    Все поля обязательны (total=True по умолчанию).

    Attributes:
        target: Целевая сумма подушки (cushion_target из User).
        threshold_percent: Порог в процентах 0-100 (cushion_threshold_percent).
            Используется Percent NewType для type safety.
        threshold_amount: Вычисляемое: target * threshold_percent / 100.
        threshold_manual: True если порог изменён вручную.
        current_amount: Текущий баланс (из CalendarService).
        progress: Процент выполнения 0-100 (capped).
        is_configured: target > 0.
    """

    target: Decimal
    threshold_percent: Percent  # 0-100, NewType для type safety
    threshold_amount: Decimal  # computed: target * percent / 100
    threshold_manual: bool
    current_amount: Decimal
    progress: float  # 0-100
    is_configured: bool


class CushionScenario(TypedDict):
    """Сценарий для калькулятора (не сохраняется в БД).

    Attributes:
        name: Название сценария (не пустое).
        min_amount: Минимальная сумма >= 0.
        max_amount: Максимальная сумма >= min_amount.
    """

    name: str
    min_amount: Decimal
    max_amount: Decimal
```

### app/services/cushion_service.py (изменённые части)

**Импорты (обновлённые):**

```python
from decimal import Decimal
from loguru import logger
from sqlalchemy.orm import Session

from app.core import ValidationError
from app.schema.cushion import CushionSettings, CushionScenario, Percent
```

**Константа с комментарием (изменение #2 включено):**

```python
# Допустимые режимы расчёта
VALID_CALC_MODES = {"sum", "max_scenario"}

# 30% от цели — типичный рекомендуемый минимальный остаток.
# При достижении этого порога баланс считается "в зоне риска".
# Источник: стандартная практика финансового планирования.
DEFAULT_THRESHOLD_PERCENT: Percent = Percent(30)
```

**Функция валидации (новая):**

```python
def _validate_percent(value: int) -> Percent:
    """Валидирует и преобразует int в Percent (0-100).

    Args:
        value: Значение в процентах для проверки.

    Returns:
        Percent: Валидированное значение как NewType Percent.

    Raises:
        ValidationError: Если value не в диапазоне 0-100.
    """
    if not 0 <= value <= 100:
        raise ValidationError(
            "Порог должен быть в диапазоне 0-100%",
            field="threshold_percent"
        )
    return Percent(value)
```

**Метод get_settings (обновлённый):**

```python
def get_settings(self, user_id: int) -> CushionSettings:
    """Получить настройки подушки с вычисленными полями.

    Args:
        user_id: ID пользователя.

    Returns:
        CushionSettings: Полные настройки включая вычисляемые поля.

    Raises:
        ValidationError: Если пользователь не найден.
    """
    user = self._get_user(user_id)
    current = self._get_current_balance(user_id)

    target = user.cushion_target or Decimal("0")
    # Используем Percent для type safety
    threshold_percent = Percent(user.cushion_threshold_percent or 0)

    # Вычисляем threshold_amount
    threshold_amount = (
        target * threshold_percent / 100 if target > 0 else Decimal("0")
    )

    # Вычисляем progress
    progress = 0.0
    if target > 0:
        if current < 0:
            progress = 0.0
        else:
            progress = min(float(current / target * 100), 100.0)

    return CushionSettings(
        target=target,
        threshold_percent=threshold_percent,
        threshold_amount=threshold_amount,
        threshold_manual=user.cushion_threshold_manual,
        current_amount=current,
        progress=progress,
        is_configured=target > 0,
    )
```

**Метод update_settings (обновлённый):**

```python
def update_settings(
    self,
    user_id: int,
    target: Decimal,
    threshold_percent: int,
    threshold_manual: bool,
) -> None:
    """Обновить настройки подушки.

    Args:
        user_id: ID пользователя.
        target: Целевая сумма (>= 0).
        threshold_percent: Порог в процентах (0-100).
        threshold_manual: True если порог изменён вручную.

    Raises:
        ValidationError: Если target < 0 или threshold_percent не в 0-100.
    """
    # Валидация target
    if target < 0:
        raise ValidationError("Цель должна быть >= 0", field="target")

    # Валидация threshold с использованием _validate_percent
    validated_percent = _validate_percent(threshold_percent)

    user = self._get_user(user_id)
    user.cushion_target = target
    user.cushion_threshold_percent = validated_percent
    user.cushion_threshold_manual = threshold_manual
    self.session.flush()

    logger.info(
        f"Обновлены настройки подушки для user {user_id}: "
        f"target={target}, threshold={validated_percent}%"
    )
```

**Метод reset_settings (обновлённый):**

```python
def reset_settings(self, user_id: int) -> None:
    """Сбросить настройки подушки.

    При сбросе:
    - target = 0
    - threshold_percent = DEFAULT_THRESHOLD_PERCENT (30%)
    - threshold_manual = False

    Args:
        user_id: ID пользователя.
    """
    user = self._get_user(user_id)
    user.cushion_target = Decimal("0")
    user.cushion_threshold_percent = DEFAULT_THRESHOLD_PERCENT  # Percent(30)
    user.cushion_threshold_manual = False
    self.session.flush()

    logger.info(f"Сброшены настройки подушки для user {user_id}")
```

---

## Изменение #2: Комментарий DEFAULT_THRESHOLD_PERCENT

```python
# 30% от цели — типичный рекомендуемый минимальный остаток.
# При достижении этого порога баланс считается "в зоне риска".
# Источник: стандартная практика финансового планирования.
DEFAULT_THRESHOLD_PERCENT: Percent = Percent(30)
```

---

## Изменение #3: Документация threshold_manual поведения

### Callback #3: mark_threshold_manual (обновлённый docstring)

```python
@callback(
    Output("cushion-threshold-manual-flag", "data"),
    Input("cushion-threshold-input", "value"),
    prevent_initial_call=True,
)
def mark_threshold_manual(value):
    """Устанавливает флаг manual=True при ручном вводе порога.

    ВАЖНО: Любое взаимодействие с полем threshold устанавливает manual=True,
    даже если введённое значение совпадает с default (30%).

    Обоснование:
    - Проще и предсказуемее: пользователь явно взаимодействовал с полем
    - Избегаем edge cases: "пользователь ввёл 31%, потом исправил на 30% —
      это manual или auto?" — всегда manual
    - При reset_settings() флаг сбрасывается в False

    Args:
        value: Новое значение порога (0-100).

    Returns:
        bool: True (manual flag).

    Raises:
        PreventUpdate: Если value is None.
    """
    # Guard: None value
    if value is None:
        raise PreventUpdate

    # Любое изменение = manual
    return True
```

---

## Учтённые замечания из критики v2

| Замечание | Как решено |
|-----------|------------|
| 🟢 #1: Type safety threshold_percent | NewType `Percent` + функция `_validate_percent()` |
| 🟢 #2: Комментарий DEFAULT_THRESHOLD_PERCENT | 3-строчный комментарий с обоснованием выбора 30% |
| 🟢 #3: threshold_manual при вводе 30% | Документировано в docstring: manual=True при любом взаимодействии с полем |

---

## Файловая структура (без изменений от v2)

```
app/
├── models/
│   └── database.py          # +3 поля в User (MODIFY)
├── schema/
│   ├── __init__.py          # +exports Percent, CushionSettings, CushionScenario (MODIFY)
│   └── cushion.py           # NEW: Percent NewType, CushionSettings, CushionScenario
├── services/
│   ├── __init__.py          # +CushionService export (MODIFY)
│   └── cushion_service.py   # NEW: CushionService, _validate_percent
├── components/
│   └── goals.py             # +cushion card, modal, callbacks (MODIFY)
└── assets/
    └── goals.css            # +.cushion-* styles (MODIFY)

tests/
└── test_cushion_service.py  # NEW: 15+ unit tests
```

---

## План реализации (без изменений от v2)

**Общее время: ~6 часов**

| Шаг | Задача | Оценка |
|-----|--------|--------|
| 1 | Schema + миграция (User model) | 15 мин |
| 2 | TypedDicts (cushion.py с Percent NewType) | 10 мин |
| 3 | CushionService + _validate_percent() | 30 мин |
| 4 | Карточка подушки (goals.py) | 45 мин |
| 5 | Модал настройки (goals.py) | 60 мин |
| 6 | Callbacks (9 штук) | 90 мин |
| 7 | CSS стили (goals.css) | 30 мин |
| 8 | Unit тесты (15+ тестов) | 45 мин |
| 9 | Финализация (Black, Flake8, pytest) | 20 мин |

---

## Дополнительные unit тесты для v3

К существующим 12 тестам из v2 добавляются:

```python
# tests/test_cushion_service.py

def test_validate_percent_valid():
    """_validate_percent возвращает Percent для валидных значений."""
    assert _validate_percent(0) == Percent(0)
    assert _validate_percent(30) == Percent(30)
    assert _validate_percent(100) == Percent(100)


def test_validate_percent_invalid_negative():
    """_validate_percent выбрасывает ValidationError для отрицательных."""
    with pytest.raises(ValidationError) as exc_info:
        _validate_percent(-1)
    assert "0-100" in str(exc_info.value)


def test_validate_percent_invalid_over_100():
    """_validate_percent выбрасывает ValidationError для > 100."""
    with pytest.raises(ValidationError) as exc_info:
        _validate_percent(101)
    assert "0-100" in str(exc_info.value)


def test_get_settings_returns_percent_newtype():
    """get_settings возвращает threshold_percent как Percent."""
    # ... setup ...
    settings = service.get_settings(user_id)
    # Type check (runtime verification)
    assert isinstance(settings["threshold_percent"], int)
    # Value check
    assert 0 <= settings["threshold_percent"] <= 100
```

**Итого тестов: 15+**

---

## Полное содержимое из solution-v2

Все остальные секции (Архитектура, Callback Signatures, CSS стили, Риски и mitigation) остаются без изменений из solution-v2.md.

Ключевые элементы:
- **9 callbacks** с детальной таблицей Input/Output
- **Refresh механизм** через cushion-refresh-trigger Store
- **ADR-003 guard clauses** во всех callbacks
- **CSS стили** с prefix `.cushion-*`
