# Critique - Solution v1
Date: 2026-02-01
Reviewer: AI Critic (Claude Opus 4.5)

---

## 🎯 Общая оценка

**Рейтинг:** ⭐⭐⭐ (3/5)

**Вердикт:**
- [ ] Отлично, можно кодировать как есть
- [ ] Хорошо, с минорными улучшениями
- [x] Требуются значительные изменения
- [ ] Не рекомендуется, нужен другой подход

**Краткая суммаризация:**
Решение демонстрирует грамотный CSS-only подход для hover-функциональности, однако содержит одну критичную проблему с конфликтом click-событий и несколько важных архитектурных упущений. После исправления критичной проблемы решение будет готово к реализации.

---

## ✅ Сильные стороны

1. **CSS-only hover подход**
   - Правильно выбран подход без server round-trip при hover
   - Обеспечивает мгновенный отклик UI без мерцания
   - Совместим с существующими callbacks

2. **Glassmorphism реализация**
   - Грамотное использование backdrop-filter с @supports fallback
   - Правильное позиционирование absolute внутри relative
   - Edge detection через CSS nth-child для правой границы

3. **Использование существующей архитектуры**
   - TransactionInfo TypedDict уже содержит все необходимые поля
   - Интеграция с существующими Stores (edit-transaction-id, recurring-edit-context)
   - Соблюдение ADR-003 guard clauses pattern

4. **Обработка ошибок**
   - Предусмотрены fallback для отсутствующих категорий
   - `_build_day_tooltip()` возвращает None для пустых дней
   - Guard clauses в callbacks защищают от автовызовов

5. **Продуманный план реализации**
   - Четкая декомпозиция на 7 шагов
   - Адекватные временные оценки (около 3.5 часов)
   - Включены unit-тесты

---

## 🔴 Критичные проблемы (Blockers)

### 1. Конфликт click handlers между tooltip и day cell

**Где:**
- Секция "Решение конфликта click handlers" в solution-v1.md
- `app/components/calendar.py`, функция `build_day_cell()`, строка 492

**Проблема:**
Предложенное решение конфликта недостаточно. CSS `pointer-events: auto` на tooltip НЕ предотвращает event bubbling в JavaScript/Dash. Клик на элемент внутри tooltip все равно сначала триггерит callback для tooltip-txn, но затем событие bubbling достигает родительского calendar-day и триггерит его callback тоже.

В Dash Pattern-Matching callbacks оба callback будут вызваны последовательно, что приведет к:
1. Сначала откроется edit-modal (через tooltip-txn callback)
2. Затем откроется create-modal (через calendar-day callback)

**Почему критично:**
- Полностью ломает основной use case: клик по операции в tooltip должен открывать ТОЛЬКО edit-modal
- Пользователь получит конфликтующее UX-поведение
- Нет возможности исправить через CSS — требуется архитектурное решение

**Пример сценария:**
```
User hovers day cell -> Tooltip appears
User clicks on transaction row in tooltip
-> tooltip-txn callback fires -> edit-modal opens
-> calendar-day callback fires -> create-modal opens (BUG!)
```

**Рекомендация:**
Реструктурировать build_day_cell() так, чтобы tooltip был "сестринским" элементом к кликабельной области дня, а не вложенным:

```python
def build_day_cell(...) -> html.Div:
    clickable_area = html.Div(
        [day_number, icons, balance],
        id={"type": "calendar-day", "date": day_date.isoformat()},
        n_clicks=0,
        className="calendar-day-content",
    )

    tooltip = _build_day_tooltip(...) if transactions else None

    # Tooltip и clickable area на одном уровне, не вложенные
    return html.Div(
        [clickable_area, tooltip],
        className=" ".join(css_classes),
    )
```

CSS:
```css
.calendar-day {
    position: relative;
}

.calendar-day-content {
    cursor: pointer;
    /* ... existing styles ... */
}

.calendar-day-tooltip {
    position: absolute;
    /* pointer-events работает т.к. tooltip не внутри clickable area */
}
```

**Альтернативный подход:**
Использовать единый callback для обоих типов кликов с ctx.triggered_id проверкой:

```python
@callback(
    [...outputs...],
    [
        Input({"type": "calendar-day", "date": ALL}, "n_clicks"),
        Input({"type": "tooltip-txn", "date": ALL, ...}, "n_clicks"),
    ],
)
def handle_calendar_clicks(day_clicks, txn_clicks):
    triggered_id = ctx.triggered_id

    if triggered_id.get("type") == "tooltip-txn":
        # Открыть edit-modal, НЕ вызывать calendar-day логику
        return ...
    elif triggered_id.get("type") == "calendar-day":
        # Открыть create-modal
        return ...
```

---

## 🟡 Важные проблемы (Should Fix)

### 2. dcc.Store для expand state не масштабируется

**Где:**
- Секция "Callbacks (calendar.py)" в solution-v1.md
- План реализации, Шаг 4

**Проблема:**
Предлагается создать dcc.Store "tooltip-expanded-{date}" для каждой даты. При отображении месяца это ~35 Store компонентов. При навигации между месяцами:
- Старые Stores остаются в DOM
- Новые создаются
- Memory leak в долгой сессии

**Почему важно:**
- Performance degradation при продолжительном использовании
- Увеличивает размер callback context
- Противоречит best practices Dash

**Рекомендация:**
Вариант A (рекомендуемый): CSS-only expand через hidden checkbox hack:
```html
<input type="checkbox" id="expand-{date}" class="tooltip-expand-checkbox">
<label for="expand-{date}" class="tooltip-expand-btn">ещё 5...</label>
<div class="tooltip-hidden-txns">...</div>
```
```css
.tooltip-expand-checkbox { display: none; }
.tooltip-expand-checkbox:checked ~ .tooltip-hidden-txns { display: block; }
.tooltip-expand-checkbox:checked ~ .tooltip-expand-btn { display: none; }
```

Вариант B: Один глобальный Store с expanded date:
```python
dcc.Store(id="tooltip-expanded-date", data=None)  # Хранит одну дату
```

### 3. Отсутствует обработка `is_skipped` транзакций в tooltip

**Где:**
- `_build_day_tooltip()` function signature
- TransactionInfo TypedDict

**Проблема:**
В существующем TransactionInfo нет поля `is_skipped`, но оно используется в `build_day_cell()` для визуализации пропущенных операций. Tooltip должен отображать пропущенные операции отлично от активных (зачеркнутый текст, другой цвет).

Brief (FR3) требует: "иконку категории/типа, описание/название, сумму с цветом". Пропущенные операции должны иметь явную визуальную индикацию.

**Почему важно:**
- Пользователь не поймет почему операция "в календаре" но не влияет на баланс
- Несоответствие между визуализацией в ячейке и в tooltip

**Рекомендация:**
Добавить `is_skipped` в TransactionInfo (уже есть в Transaction model) и соответствующую визуализацию:
```css
.tooltip-txn-row.skipped {
    opacity: 0.5;
    text-decoration: line-through;
}
```

### 4. Нет delay на hide tooltip при уходе мыши

**Где:**
- CSS стили `.calendar-day-tooltip`
- Секция "Риски и mitigation"

**Проблема:**
В рисках указано "Клик по tooltip закрывает его (mouse leave)" с mitigation "Увеличить padding; добавить delay на hide". Однако в CSS реализации delay отсутствует.

При перемещении мыши от ячейки к tooltip (если есть gap) tooltip исчезнет до того, как пользователь успеет кликнуть.

**Почему важно:**
- UX friction при попытке кликнуть на операцию
- Особенно заметно на мобильных с touch events

**Рекомендация:**
Добавить transition-delay на hide:
```css
.calendar-day-tooltip {
    transition: opacity 0.2s ease 0.15s, transform 0.2s ease 0.15s;
    /* 0.15s delay перед hide */
}

.calendar-day:hover .calendar-day-tooltip {
    transition-delay: 0s; /* Мгновенное появление */
    opacity: 1;
}
```

### 5. TooltipTransactionItem дублирует TransactionInfo

**Где:**
- `app/schema/calendar_tooltip.py` (предлагаемый)
- Существующий `calendar_service.py`, TransactionInfo

**Проблема:**
Решение предлагает создать новый TypedDict `TooltipTransactionItem` с полями, которые уже есть в TransactionInfo. Это нарушает DRY и создает дополнительную maintenance burden.

В solution сказано "(опционально, можно работать напрямую с TransactionInfo)" — рекомендую выбрать именно этот путь.

**Рекомендация:**
Использовать TransactionInfo напрямую. Для форматирования суммы создать helper function:
```python
def format_amount_for_tooltip(txn: TransactionInfo) -> tuple[str, str]:
    """Returns (formatted_amount, css_class)."""
    amount = Decimal(txn["amount"])
    if txn["transaction_type"] == "income":
        return f"+{amount:,.0f}".replace(",", " "), "income"
    else:
        return f"-{amount:,.0f}".replace(",", " "), "expense"
```

---

## 🟢 Незначительные замечания (Optional)

### 6. Edge detection через nth-child не учитывает padding days

**Где:**
- CSS правила `.calendar-day:nth-child(6)`, `.calendar-day:nth-child(7)`

**Проблема:**
nth-child считает все дни в неделе, включая дни предыдущего/следующего месяца. Для крайних правых дней edge detection работает корректно. Однако семантически это не совсем точно — лучше использовать nth-child(7n-1) и nth-child(7n).

**Рекомендация:**
```css
.calendar-day:nth-child(7n-1) .calendar-day-tooltip,
.calendar-day:nth-child(7n) .calendar-day-tooltip {
    left: auto;
    right: 0;
}
```

### 7. Константа MAX_VISIBLE_TRANSACTIONS не определена

**Где:**
- `_build_day_tooltip()` упоминает MAX_VISIBLE_TRANSACTIONS (5)
- Нет в констант

**Рекомендация:**
Добавить в начало calendar.py:
```python
MAX_VISIBLE_TRANSACTIONS = 5
```

### 8. Нет aria-атрибутов для accessibility

**Где:**
- Tooltip HTML structure

**Рекомендация:**
Добавить ARIA для screen readers:
```python
html.Div(
    [tooltip_content],
    role="tooltip",
    aria_label=f"Операции на {day_date.strftime('%d.%m.%Y')}",
    className="calendar-day-tooltip",
)
```

---

## 📊 Детальный анализ по аспектам

### Аспект 1: Соответствие требованиям

**Статус:** Частично

**Детали:**
- FR1 (tooltip только для дней с операциями): Покрыт (возврат None)
- FR2 (содержимое: баланс + до 5 операций): Покрыт
- FR3 (отображение операции): Частично (is_skipped не учтен)
- FR4 (кнопка "ещё N..."): Покрыт в дизайне
- FR5 (раскрытие в том же tooltip): Покрыт, но архитектура Store проблемная
- FR6 (клик открывает edit-modal): КРИТИЧНО - bubbling проблема
- FR7 (recurring открывает scope-modal): Покрыт в дизайне
- NFR1-NFR5: В основном покрыты

**Комментарий:**
Большинство требований учтено, но критичная проблема с click handlers блокирует FR6/FR7.

### Аспект 2: Архитектурное качество

**Статус:** Хорошо

**Детали:**
- SOLID: SRP соблюдается (отдельные функции для tooltip, row)
- Coupling: Низкий, использует существующие интерфейсы
- Cohesion: Высокая, логика tooltip сгруппирована
- Совместимость с архитектурой: Да (ADR-003, Pattern-Matching)

**Проблемы:**
- DRY violation с TooltipTransactionItem (важно)
- Store per date не масштабируется (важно)

### Аспект 3: Производительность

**Статус:** Хорошо

**Детали:**
- Сложность алгоритмов: O(n) где n = количество транзакций дня
- Bottlenecks: Нет server round-trip на hover
- Масштабируемость: Store-per-date проблема при долгих сессиях

### Аспект 4: Обработка ошибок и edge cases

**Статус:** Хорошо

**Детали:**
- Покрытие ошибок: 80%
- Edge cases: Пустой tooltip, >5 операций, виртуальные — покрыты
- Fallback стратегии: fallback emoji, None return

**Пропущено:**
- is_skipped транзакции
- Очень длинные description (text-overflow есть, но не протестировано)

### Аспект 5: Безопасность

**Статус:** Нет проблем

**Детали:**
- Input validation: Не применимо (readonly tooltip)
- XSS: Dash экранирует по умолчанию
- Secrets: Не применимо

### Аспект 6: Сложность реализации

**Статус:** Адекватно

**Детали:**
- Реалистичность оценки: 3.5 часа — реалистично при отсутствии критичной проблемы
- Скрытая сложность: Click handler conflict потребует рефакторинга build_day_cell
- Зависимости: Не требуются новые

### Аспект 7: Альтернативные подходы

**Статус:** Частично

**Детали:**
- Рассмотрены CSS-only vs callback-based: Да
- Обоснование выбора: Да (нет server round-trip)
- Альтернатива для expand: Упомянута но не детализирована

---

## 🔄 Альтернативные подходы

### Подход A: dcc.Tooltip компонент

**Идея:**
Использовать dash-bootstrap-components dbc.Tooltip вместо кастомного CSS:
```python
dbc.Tooltip(
    _build_tooltip_content(...),
    target={"type": "calendar-day", "date": day_date.isoformat()},
    placement="bottom",
)
```

**Плюсы:**
- Автоматическое позиционирование
- Решает проблему edge detection
- Меньше CSS кода

**Минусы:**
- Требует server callback для content (не CSS-only)
- Менее кастомизируемый glassmorphism
- Pattern-Matching targets могут не работать с dbc.Tooltip

**Рекомендация:**
Не рекомендуется — текущий CSS-only подход лучше для UX.

### Подход B: Tooltip как отдельный overlay вне calendar grid

**Идея:**
Один глобальный tooltip div, позиционируемый через JavaScript при hover:
```python
html.Div(id="global-calendar-tooltip", className="calendar-tooltip-overlay")
```

**Плюсы:**
- Нет проблем с bubbling (tooltip вне calendar-day)
- Один Store для всех данных
- Проще z-index management

**Минусы:**
- Требует clientside_callback для позиционирования
- Сложнее синхронизация с hover state
- Менее "Dash-native"

**Рекомендация:**
Не рекомендуется — добавляет сложность без существенных преимуществ.

---

## ❓ Вопросы для архитектора

1. **Click handler priority**: Предусмотрен ли в Dash механизм stopPropagation для Pattern-Matching callbacks? Или единственное решение — restructuring DOM?

2. **Store cleanup**: Планируется ли очистка Stores при навигации между месяцами? Если да — какой механизм?

3. **Mobile UX**: Brief говорит "Tooltip появляется ТОЛЬКО при наведении" — на мобильных нет hover. Планируется ли fallback (tap → tooltip) или tooltip отключен на mobile (как в CSS)?

4. **Edit recurring flow**: При клике на виртуальную recurring операцию должен открываться recurring-edit-scope-modal. Но в tooltip нет визуального отличия recurring от обычных. Нужна ли индикация?

---

## 📋 Рекомендации для следующей итерации

### Обязательно:
1. **Исправить click handler conflict** — реструктурировать DOM так, чтобы tooltip не был вложен в кликабельную область дня, или использовать единый callback с ctx.triggered_id routing

### Желательно:
2. **Заменить Store-per-date на CSS-only expand** — использовать checkbox hack или один глобальный Store
3. **Добавить is_skipped визуализацию** — транзакции is_skipped должны отображаться зачеркнутыми
4. **Добавить transition-delay на hide** — улучшит UX при перемещении мыши к tooltip

### Опционально:
5. **Использовать TransactionInfo напрямую** — убрать TooltipTransactionItem
6. **Исправить nth-child селекторы** — использовать 7n-1, 7n для корректности
7. **Добавить ARIA атрибуты** — улучшит accessibility

---

## 🔄 Изменения с предыдущей итерации
(N/A - это первая итерация)