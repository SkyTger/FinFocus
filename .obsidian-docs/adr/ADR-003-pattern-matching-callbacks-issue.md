# ADR-003: Проблема Pattern-Matching Callbacks в Dash

**Дата**: 2025-11-03
**Статус**: 🔍 Исследуется
**Контекст**: Фаза 2 - Формы управления операциями (Epic-01-CoreMVP)
**Приоритет**: P1 (критичный)

## Проблема

При использовании Dash Pattern-Matching Callbacks с `Input({"type": "...", "index": ALL}, "n_clicks")`:
- Callbacks срабатывают при обновлении таблицы (добавление новых кнопок)
- Невозможно надёжно отличить "обновление компонента" от "реального клика пользователя"
- Простые проверки `n_clicks` приводят к регрессиям или не решают проблему

### Симптомы

1. **Исходная проблема** (начало сессии):
   - Автоудаление операций сразу после создания
   - Автооткрытие модала редактирования при добавлении операции

2. **После исправлений** (текущее состояние):
   - ✅ Создание операций работает корректно
   - ✅ Автооткрытие модала устранено
   - ❌ Кнопка Edit (карандаш) не открывает модал редактирования
   - ❌ Кнопка Delete (корзина) не удаляет операции

### Affected Files

- `app/components/transactions.py:463-514` - callback `open_edit_modal`
- `app/components/transactions.py:642-755` - callback `delete_transaction`

## Попытки решения

### Попытка #1: Проверка triggered_id

```python
triggered_id = ctx.triggered_id
if not triggered_id:
    raise PreventUpdate
```

**Результат**: ❌ Не помогла
**Причина**: `triggered_id` имеет значение даже для новых кнопок при инициализации

---

### Попытка #2: Проверка n_clicks с == 0

```python
# Найти индекс кликнутой кнопки
clicked_idx = next(
    (i for i, inp in enumerate(ctx.inputs_list[0]) if inp["id"] == triggered_id),
    None,
)

# Проверка на None ИЛИ 0
if clicked_idx is None or n_clicks_list[clicked_idx] is None or n_clicks_list[clicked_idx] == 0:
    raise PreventUpdate
```

**Результат**: ⚠️ Устранила автоудаление, но создала регрессию
**Причина**: Проверка `== 0` блокирует первый реальный клик пользователя
**Побочный эффект**: Кнопки Edit/Delete перестали работать

**Вывод QA engineer** (оказался ошибочным):
> "Dash НИКОГДА не инициализирует кнопки с `n_clicks=0`. Проверка `n_clicks is None` достаточна."

---

### Попытка #3: Удаление проверки == 0

```python
# Удалена проверка на 0, оставлена только проверка на None
if clicked_idx is None or n_clicks_list[clicked_idx] is None:
    raise PreventUpdate
```

**Результат**: ❌ Регрессия осталась
**Причина**: Проблема глубже, чем предполагалось
**Вывод**: Простое удаление `== 0` не решило регрессию - кнопки по-прежнему не реагируют

## Гипотезы корневой причины

### Гипотеза #1: Логика поиска clicked_idx неверна ⚠️ ВЫСОКАЯ ВЕРОЯТНОСТЬ

Метод поиска индекса в `ctx.inputs_list` может не работать корректно:

```python
clicked_idx = next(
    (i for i, inp in enumerate(ctx.inputs_list[0]) if inp["id"] == triggered_id),
    None,
)
```

**Потенциальные проблемы**:
- Структура `ctx.inputs_list[0]` может отличаться от ожидаемой
- `inp["id"]` может иметь другой формат или структуру
- Порядок элементов в `inputs_list` может не совпадать с порядком кнопок в UI
- `triggered_id` может иметь сложную структуру (словарь), которую нельзя напрямую сравнивать

**Метод проверки**:
```python
# Runtime debugging
print("triggered_id:", ctx.triggered_id)
print("inputs_list[0]:", ctx.inputs_list[0])
print("clicked_idx:", clicked_idx)
print("n_clicks_list:", n_clicks_list)
```

---

### Гипотеза #2: Формат triggered_id отличается от ожидаемого ⚠️ СРЕДНЯЯ ВЕРОЯТНОСТЬ

Структура `triggered_id` может быть другой в runtime:

**Ожидается** (словарь):
```python
{"type": "edit-btn", "index": 1}
```

**Может быть** (строка JSON или другой формат):
```python
'{"type":"edit-btn","index":1}'
# ИЛИ
EditBtn(type='edit-btn', index=1)
```

**Метод проверки**:
```python
print("type(triggered_id):", type(ctx.triggered_id))
print("triggered_id repr:", repr(ctx.triggered_id))
```

---

### Гипотеза #3: n_clicks блокируется для всех случаев ⚠️ НИЗКАЯ ВЕРОЯТНОСТЬ

Проверка `n_clicks_list[clicked_idx] is None` может срабатывать даже для реальных кликов:

**Возможные причины**:
- `n_clicks` сбрасывается в `None` при обновлении таблицы
- Индекс `clicked_idx` указывает на неправильный элемент
- Порядок элементов в `n_clicks_list` не соответствует порядку кнопок

**Метод проверки**:
```python
print("n_clicks_list before check:", n_clicks_list)
print("n_clicks_list[clicked_idx]:", n_clicks_list[clicked_idx] if clicked_idx is not None else "clicked_idx is None")
```

---

### Гипотеза #4: Порядок элементов в inputs_list ⚠️ СРЕДНЯЯ ВЕРОЯТНОСТЬ

Индексы кнопок в `ctx.inputs_list[0]` могут не совпадать с индексами в `n_clicks_list`:

**Проблема**: Если Dash изменяет порядок элементов при обновлении компонентов, поиск индекса может вернуть неправильное значение.

**Метод проверки**:
```python
for i, inp in enumerate(ctx.inputs_list[0]):
    print(f"Index {i}: id={inp['id']}, n_clicks={n_clicks_list[i]}")
```

## Следующие шаги (Приоритеты)

### 🔴 P0 - Критично (немедленно)

1. **Runtime debugging с print()** - добавить детальный вывод:
   ```python
   print("=== DEBUG START ===")
   print("ctx.triggered_id:", ctx.triggered_id)
   print("type(triggered_id):", type(ctx.triggered_id))
   print("ctx.inputs_list[0]:", ctx.inputs_list[0])
   print("n_clicks_list:", n_clicks_list)
   print("clicked_idx:", clicked_idx)
   if clicked_idx is not None:
       print("n_clicks_list[clicked_idx]:", n_clicks_list[clicked_idx])
   print("=== DEBUG END ===")
   ```

2. **Проверить структуру данных** - убедиться в корректности форматов и типов

### 🟡 P1 - Высокий приоритет (сегодня/завтра)

3. **Изучить Dash документацию**:
   - Официальные примеры с Pattern-Matching Callbacks и `ALL`
   - Поведение `n_clicks` в динамических списках компонентов
   - Особенности `ctx.triggered_id` для MATCH/ALL/ALLSMALLER

4. **Проверить ctx.triggered_prop_ids**:
   ```python
   print("ctx.triggered:", ctx.triggered)
   print("ctx.triggered_prop_ids:", ctx.triggered_prop_ids)
   ```

### 🟢 P2 - Средний приоритет (на неделе)

5. **Рассмотреть альтернативные подходы**:
   - **Вариант A**: Использовать `ctx.triggered_prop_ids` вместо `triggered_id`
   - **Вариант B**: Проверять изменение `n_clicks` между вызовами (state management с dcc.Store)
   - **Вариант C**: Использовать отдельные callbacks для каждой кнопки (без `ALL`) - более надёжно, но менее масштабируемо

6. **Изучить community решения**:
   - Поиск похожих проблем на Dash Community Forum
   - GitHub issues в репозитории plotly/dash
   - Stack Overflow вопросы о Pattern-Matching Callbacks

## Референсы

### Документация Dash
- **Pattern-Matching Callbacks**: https://dash.plotly.com/pattern-matching-callbacks
- **Callback Context**: https://dash.plotly.com/advanced-callbacks#determining-which-input-has-fired

### Related Issues
- GitHub issue #??? (если найдётся)
- Dash Community Forum thread #??? (если найдётся)

### Affected Commits
- Commit ??? - Попытка #1: Добавлена проверка `if not triggered_id`
- Commit ??? - Попытка #2: Добавлена проверка `n_clicks == 0`
- Commit ??? - Попытка #3: Удалена проверка `== 0`

## Решение

> **Статус**: 🔍 В процессе исследования
> **Дата обновления**: 2025-11-03
> **Ответственный**: TBD

Решение будет задокументировано после успешной отладки и устранения регрессии.

### Критерии успеха
- [ ] Кнопки Edit открывают модал редактирования
- [ ] Кнопки Delete удаляют операции
- [ ] Создание операций работает без автоудаления
- [ ] Модал редактирования не открывается автоматически
- [ ] Добавлены unit/integration тесты для предотвращения регрессий

---

## Уроки для будущего

1. **Runtime debugging критичен** - без точных значений переменных невозможно определить корневую причину Pattern-Matching Callbacks
2. **Dash документация может быть неполной** - поведение `n_clicks` в `ALL`-callbacks требует эмпирического изучения
3. **QA рекомендации требуют валидации** - даже опытные QA engineer могут ошибаться в сложных случаях
4. **Простые проверки недостаточны** - Pattern-Matching Callbacks требуют глубокого понимания механизма Dash
5. **Альтернативные подходы всегда полезны** - иметь запасной план (отдельные callbacks без `ALL`)

---

*ADR создан doc-manager на основе .protocol.md*
*Последнее обновление: 2025-11-03*