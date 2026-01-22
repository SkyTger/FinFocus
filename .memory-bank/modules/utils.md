# modules/utils.md

## Суть
Утилиты для форматирования, сериализации и обработки данных в UI компонентах

## Ключевые файлы
- `app/utils/formatters.py` - форматирование для отображения (~75 строк)
- `app/utils/serializers.py` - сериализация TypedDicts для dcc.Store (~65 строк)

## Форматирование для отображения

**Создан в**: Протокол 0004 (Goals UI)

**Причина**: Избежать дублирования кода форматирования между transactions.py и goals.py

### format_amount(amount: Decimal) → str
Форматирует сумму для отображения.

```python
format_amount(Decimal('15000.00'))
# → "15 000.00 ₽"
```

**Детали**:
- Разделитель тысяч: пробел
- 2 знака после запятой
- Символ рубля в конце

### format_date(date_obj: date) → str
Форматирует дату для отображения.

```python
format_date(date(2026, 1, 21))
# → "21.01.2026"
```

**Формат**: DD.MM.YYYY

### format_days_remaining(days: int) → str
Форматирует оставшиеся дни с правильным склонением для русского языка.

```python
format_days_remaining(1)   # → "1 день"
format_days_remaining(2)   # → "2 дня"
format_days_remaining(5)   # → "5 дней"
format_days_remaining(21)  # → "21 день"
format_days_remaining(0)   # → "Срок истёк"
```

**Правила склонения**:
- 1, 21, 31... → "день"
- 2-4, 22-24... → "дня"
- 5-20, 25-30... → "дней"
- 11-14 → "дней" (исключение)

### parse_date_safe(date_str: str | None) → date | None
Безопасно парсит строку даты с обработкой ошибок.

```python
parse_date_safe("2026-01-21")  # → date(2026, 1, 21)
parse_date_safe(None)          # → None
parse_date_safe("invalid")     # → None (с логом ошибки)
```

**Формат входа**: YYYY-MM-DD (ISO)

**Обработка ошибок**: logger.error() + возврат None

## Сериализация для dcc.Store

### RedistributionPreview сериализация (Протокол 0008)

**Файл**: `app/utils/serializers.py`

**Создан в**: Протокол 0008 (Redistribution)

**Причина**: Decimal и вложенные AllocationSummary несовместимы с JSON (dcc.Store)

#### serialize_redistribution_preview(preview: RedistributionPreview) → dict
Конвертирует RedistributionPreview в JSON-совместимый формат.

```python
preview = {
    "completed_goal_id": 1,
    "freed_budget": Decimal("5000.00"),
    "old_allocation": {"total_budget": Decimal("15000.00"), ...},
    ...
}

serialized = serialize_redistribution_preview(preview)
# → {"completed_goal_id": 1, "freed_budget": "5000.00", "old_allocation": {"total_budget": "15000.00", ...}, ...}
```

**Детали**:
- Рекурсивная конвертация Decimal → str через `_convert_decimal_to_str()`
- Поддерживает вложенные AllocationSummary
- None значения сохраняются

#### deserialize_redistribution_preview(serialized: dict) → RedistributionPreview
Обратная конвертация из JSON.

```python
preview = deserialize_redistribution_preview(serialized)
# → {"completed_goal_id": 1, "freed_budget": Decimal("5000.00"), ...}
```

**Детали**:
- Рекурсивная конвертация str → Decimal через `_convert_str_to_decimal()`
- Использует набор `_DECIMAL_KEYS` для идентификации полей с Decimal
- Сохраняет точность при roundtrip (5000.00 → "5000.00" → 5000.00)

**Helper функции** (внутренние):
- `_convert_decimal_to_str(obj)` - рекурсивная конвертация Decimal → str
- `_convert_str_to_decimal(obj, decimal_keys)` - рекурсивная конвертация str → Decimal

### Calendar сериализация (Legacy)

**Примечание**: Для сериализации Decimal в Calendar Component используются отдельные функции:

#### serialize_balances(balances: dict[date, Decimal]) → dict[str, str]
Конвертирует словарь балансов в JSON-совместимый формат.

**Где**: `app/components/calendar.py`

#### deserialize_balances(serialized: dict[str, str]) → dict[date, Decimal]
Обратная конвертация из JSON.

**Где**: `app/components/calendar.py`

## Важное

**DRY принцип**: Одна функция форматирования переиспользуется во всех UI компонентах

**Русская локализация**: Склонения учитывают правила русского языка (11-14 исключение)

**Безопасность**: parse_date_safe никогда не бросает exception, всегда возвращает None при ошибке

## Где используются

**format_amount**:
- `app/components/transactions.py` - таблица транзакций
- `app/components/goals.py` - карточки целей, прогресс
- `app/components/calendar.py` - балансы в ячейках

**format_date**:
- `app/components/transactions.py` - даты операций
- `app/components/goals.py` - целевые даты

**format_days_remaining**:
- `app/components/goals.py` - срок до достижения цели

**parse_date_safe**:
- `app/components/transactions.py` - парсинг дат из форм
- `app/components/goals.py` - парсинг дат из форм

**serialize_redistribution_preview / deserialize_redistribution_preview**:
- `app/components/goals.py` - redistribution-preview-store (dcc.Store)

## Критичные решения

**Протокол 0004**: Вынесение общих formatters из transactions.py в отдельный модуль

**Обновление transactions.py**: Импорты изменены с локальных функций на `from app.utils.formatters import ...`

**Протокол 0008**: Добавлен модуль serializers.py для сериализации RedistributionPreview в dcc.Store

**Decimal сериализация**: str (не float) для сохранения точности при roundtrip

---

Детали: `ui-components.md` (где используются), `code-style.md` (DRY принцип)
