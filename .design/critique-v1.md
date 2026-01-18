# Critique - Solution v1
Date: 2026-01-18
Reviewer: AI Critic (Claude)

---

## 🎯 Общая оценка

**Рейтинг:** ⭐⭐⭐⭐ (4/5)

**Вердикт:**
- [ ] ✅ Отлично, можно кодировать как есть
- [x] 🟢 Хорошо, с минорными улучшениями
- [ ] 🟡 Требуются значительные изменения
- [ ] 🔴 Не рекомендуется, нужен другой подход

**Краткая суммаризация:**
Решение хорошо структурировано, соответствует существующим паттернам проекта и покрывает все основные функциональные требования. Однако есть несколько технических недочетов в дизайне Pattern-Matching Callbacks и сериализации Decimal в dcc.Store, которые необходимо устранить до реализации.

---

## ✅ Сильные стороны

1. **Соответствие архитектурным паттернам проекта**
   - CalendarService следует установленному Service Layer Pattern с session injection
   - Использование flush() вместо commit() для атомарности соответствует D010
   - TypedDict для MonthSummary обеспечивает type safety

2. **Четкое разделение ответственностей**
   - Backend (CalendarService) отделен от UI (calendar.py)
   - Callbacks изолированы от бизнес-логики
   - CSS вынесен в отдельный файл assets/calendar.css

3. **Хорошее покрытие требований Brief**
   - Все функциональные требования учтены (визуализация, операции, остатки, навигация)
   - Нефункциональные требования (производительность, адаптивность) рассмотрены
   - Ограничения scope явно соблюдены (no recurring, user_id=1)

4. **Продуманная оптимизация производительности**
   - SQL агрегация через GROUP BY вместо Python циклов
   - Использование существующего индекса ix_transactions_user_date
   - Кэширование данных в dcc.Store для быстрого переключения месяцев

5. **Реалистичный план реализации**
   - 6 четких шагов с конкретными критериями готовности
   - Общая оценка 11 часов выглядит адекватной
   - Зависимости между шагами логичны

---

## 🔴 Критичные проблемы (Blockers)

### BLOCKER-1: Сериализация Decimal в dcc.Store невозможна

**Файл**: solution-v1.md, секция "State Management"

**Проблема**: В дизайне указано кэширование балансов в dcc.Store:
```python
{
    "balances": {date_str: float},  # Кэш балансов
    "transactions": {date_str: [tx_dict]}  # Кэш операций
}
```

Однако:
1. dcc.Store сериализует данные в JSON
2. Decimal НЕ сериализуется в JSON нативно
3. При конвертации Decimal -> float -> Decimal возникают погрешности округления

Это противоречит требованию Brief:
> "Точность до копеек (2 знака после запятой). Отсутствие погрешностей округления при большом количестве операций."

**Решение**:
- Вариант A: Хранить балансы как строки `str(decimal)` и парсить при использовании `Decimal(balance_str)`
- Вариант B: Не кэшировать балансы в Store, всегда пересчитывать через CalendarService
- Вариант C: Хранить как integer в копейках (balance_kopecks) и конвертировать при отображении

**Рекомендация**: Вариант A наиболее чистый - добавить утилиты `serialize_balances()` и `deserialize_balances()` для конвертации dict[date, Decimal] <-> dict[str, str].

---

## 🟡 Важные проблемы (Should Fix)

### IMPORTANT-1: Pattern-Matching Callback для клика по дню может вызвать регрессию

**Файл**: solution-v1.md, callback `open_create_modal_from_calendar()`

**Проблема**: Callback использует Pattern-Matching с ALL:
```python
@callback(
    [...],
    Input({"type": "calendar-day", "date": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_create_modal_from_calendar(n_clicks_list):
    ...
```

Проект имеет задокументированную историю проблем с Pattern-Matching Callbacks (ADR-003, D011). Согласно architecture.md:
> "Критично: Pattern-Matching Callbacks с ALL: Проверять ctx.triggered[0].get('value') is None для фильтрации автовызовов"

В solution-v1.md НЕ показана эта проверка в интерфейсе callback'а.

**Решение**: Добавить в дизайн callback'а явную проверку:
```python
def open_create_modal_from_calendar(n_clicks_list):
    triggered_id = ctx.triggered_id

    # Guard: фильтрация автовызовов при обновлении DOM
    if not triggered_id:
        raise PreventUpdate

    if not isinstance(triggered_id, dict) or triggered_id.get("type") != "calendar-day":
        raise PreventUpdate

    # Guard: проверка реального клика (не автовызов)
    if not ctx.triggered or ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    selected_date = triggered_id.get("date")
    # ... остальная логика
```

### IMPORTANT-2: Отсутствует callback для обновления календаря после CRUD операций

**Файл**: solution-v1.md, секция "Dash Callbacks"

**Проблема**: Указан callback `refresh_calendar_after_transaction()`, но не показана его сигнатура и логика. Это критичная часть интеграции с transactions.py.

Brief требует:
> "После добавления/изменения операции календарь автоматически обновляется"
> "Удаление операции обновляет календарь и пересчитывает остатки"

**Вопросы без ответа**:
- Как callback узнает, что операция создана/изменена/удалена?
- Как избежать дублирования Output (calendar-grid уже выводится в load_and_navigate_calendar)?
- Нужен ли allow_duplicate=True?

**Решение**: Добавить полную сигнатуру callback'а:
```python
@callback(
    [
        Output("calendar-grid", "children", allow_duplicate=True),
        Output("calendar-stats", "children", allow_duplicate=True),
    ],
    [
        Input("create-submit-btn", "n_clicks"),
        Input("edit-submit-btn", "n_clicks"),
        Input({"type": "delete-btn", "index": ALL}, "n_clicks"),
    ],
    [State("calendar-state", "data")],
    prevent_initial_call=True,
)
def refresh_calendar_after_transaction(create_clicks, edit_clicks, delete_clicks_list, state):
    # Guard clauses + logic
    ...
```

### IMPORTANT-3: Нет обработки пользователя с отсутствующим starting_balance

**Файл**: solution-v1.md, CalendarService.calculate_daily_balances()

**Проблема**: Метод получает starting_balance пользователя, но не указано поведение при:
- User.starting_balance = None (маловероятно, default=0)
- User не найден в БД

Brief требует:
> "Формула: остаток(date) = starting_balance + SUM(доходы до date) - SUM(расходы до date)"

Если starting_balance не установлен, формула будет ошибочной.

**Решение**: Добавить явную обработку:
```python
user = self.session.get(User, user_id)
if not user:
    raise ValueError(f"Пользователь {user_id} не найден")

starting_balance = user.starting_balance or Decimal('0')  # Fallback
```

### IMPORTANT-4: Нет учета типа TRANSFER в расчетах

**Файл**: solution-v1.md, CalendarService

**Проблема**: Модель Transaction имеет три типа:
```python
class TransactionType(PyEnum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"  # Перевод
```

В solution не указано, как обрабатывать TRANSFER при расчете остатков. По бизнес-логике трансфер может быть:
- Внутренний (между счетами) - не влияет на общий баланс
- Внешний (перевод другому) - как расход

**Решение**: Уточнить в CalendarService:
```python
# В calculate_daily_balances():
# TRANSFER исключается из расчета (внутренние переводы)
# или учитывается как EXPENSE (если поддерживаются внешние переводы)
income_sum = self.session.query(func.sum(Transaction.amount)).filter(
    Transaction.user_id == user_id,
    Transaction.transaction_type == TransactionType.INCOME,
    Transaction.transaction_date <= current_date
).scalar() or Decimal('0')
```

---

## 🟢 Незначительные замечания (Optional)

### MINOR-1: Нет локализации месяцев в заголовке календаря

**Файл**: solution-v1.md, _build_calendar_header()

**Проблема**: Brief требует "Заголовок показывает текущий месяц и год (например, 'Январь 2026')". Python calendar модуль по умолчанию использует английские названия.

**Решение**: Добавить словарь локализации:
```python
MONTH_NAMES_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}
```

### MINOR-2: Не указан threshold для желтого предупреждения остатка

**Файл**: solution-v1.md, _format_balance()

**Проблема**: Указано ".balance-warning (желтый, < 10% от starting_balance)", но Brief не определяет конкретный threshold. 10% может быть слишком/мало в зависимости от суммы.

**Решение**: Сделать threshold конфигурируемым или использовать абсолютное значение (например, < 5000 рублей).

### MINOR-3: Отсутствует валидация периода +-12 месяцев

**Файл**: solution-v1.md, change_month() callback

**Проблема**: Brief указывает:
> "Период отображения: текущий месяц ± 12 месяцев (валидация в API)"

В solution не показана эта валидация.

**Решение**: Добавить проверку в change_month():
```python
from datetime import date
from dateutil.relativedelta import relativedelta

today = date.today()
min_date = today - relativedelta(months=12)
max_date = today + relativedelta(months=12)

if new_month < min_date.month or new_year < min_date.year:
    raise PreventUpdate  # Не переключать назад > 12 месяцев
```

### MINOR-4: Дублирование ID модалов между transactions.py и calendar.py

**Файл**: solution-v1.md, callback open_create_modal_from_calendar()

**Проблема**: Callback выводит в Output("create-modal", "is_open"). Это тот же ID, что в transactions.py. При одновременном рендере обоих компонентов могут возникнуть конфликты.

**Решение**: Использовать общий модал из transactions.py или создать уникальные ID (calendar-create-modal).

---

## 📊 Детальный анализ по аспектам

### Соответствие требованиям Brief

| Требование | Статус | Комментарий |
|------------|--------|-------------|
| Сетка 7x5 с датами | ✅ | Покрыто _build_calendar_grid() |
| Выходные визуально отличаются | ✅ | CSS класс .calendar-day-weekend |
| Текущий день выделяется | ✅ | CSS класс .calendar-day-today |
| Дни соседних месяцев затемнены | ✅ | Упомянуто в дизайне |
| Иконки доходов/расходов | ✅ | Указаны зеленые/красные стрелки |
| Группировка +N | ✅ | Описано в Brief compliance |
| Tooltip со списком операций | ✅ | Покрыто в _build_day_cell() |
| Клик по дате → модал | ⚠️ | Есть, но Pattern-Matching требует guard clauses |
| Расчет остатков | ⚠️ | Формула верная, но TRANSFER не учтен |
| Цветовая индикация остатков | ✅ | 3 CSS класса (positive/negative/warning) |
| Навигация < > Сегодня | ✅ | 3 кнопки в callback |
| Загрузка < 2 сек | ✅ | SQL агрегация + индексы |
| Переключение < 500ms | ✅ | Кэширование в dcc.Store |
| Decimal точность | ⚠️ | Нарушена при сериализации в Store |

**Итого**: 11/14 требований полностью покрыты, 3 требуют доработки

### Архитектурное качество

**Соответствие паттернам проекта**:
- Service Layer Pattern: ✅ CalendarService аналогичен TransactionService
- Session Management (D010): ✅ flush() упомянут в сервисе
- Guard Clauses (D008): ⚠️ Частично - нужны дополнительные проверки в callbacks
- Separation of Concerns: ✅ UI/Business/Data разделены

**SOLID принципы**:
- SRP: ✅ CalendarService отвечает только за расчет балансов
- OCP: ✅ Можно расширить MonthSummary без изменения калькулятора
- LSP: N/A (нет наследования)
- ISP: ✅ Три конкретных метода вместо одного "do everything"
- DIP: ✅ Сервис зависит от Session абстракции

### Технические риски

| Риск | Оценка в solution | Моя оценка | Комментарий |
|------|-------------------|------------|-------------|
| SQL производительность | Средняя | Низкая | Индекс существует, оптимизации правильные |
| Pattern-Matching | Средняя | Высокая | История проблем ADR-003, требует внимания |
| Decimal округление | Низкая | Средняя | Не учтена сериализация в JSON |
| UX понятность | Низкая | Низкая | Дизайн интуитивный |
| Регрессия transactions | Низкая | Низкая | Минимальные изменения |

### Интеграция

**С transactions.py**:
- Необходимо добавить callback для refresh после CRUD
- Модалы могут конфликтовать по ID - требуется проверка

**С main.py**:
- Изменение простое: заменить stub на create_calendar_layout()
- Нет рисков регрессии

**С services/__init__.py**:
- Нужно добавить export CalendarService
- Стандартная процедура

### План реализации

| Шаг | Время | Реалистичность | Комментарий |
|-----|-------|----------------|-------------|
| CalendarService | 2 часа | ✅ | Адекватно для 3 методов + тесты |
| Calendar UI | 3 часа | ⚠️ | Может занять 4 часа с CSS |
| Dash Callbacks | 2 часа | ⚠️ | +1 час на Pattern-Matching guard clauses |
| Интеграция | 1 час | ✅ | Минимальные изменения |
| Тестирование | 2 часа | ✅ | Достаточно для функционального QA |
| Документация | 1 час | ✅ | Стандартный процесс |

**Общая оценка**: 11 часов → 13-14 часов с учетом дополнительной работы над Pattern-Matching и сериализацией Decimal.

---

## 🔄 Альтернативные подходы

### Альтернатива для Pattern-Matching Callbacks

Вместо `Input({"type": "calendar-day", "date": ALL}, "n_clicks")` можно использовать:

**Вариант B: Один callback с dcc.Store для выбранной даты**
```python
# Каждая ячейка дня устанавливает значение в Store при клике
@callback(
    Output("selected-date-store", "data"),
    Input({"type": "calendar-day", "date": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def select_date(n_clicks_list):
    # Стандартная логика + guard clauses
    ...

# Отдельный callback открывает модал при изменении Store
@callback(
    Output("create-modal", "is_open"),
    Input("selected-date-store", "data"),
    prevent_initial_call=True,
)
def open_modal_on_date_select(selected_date):
    if not selected_date:
        raise PreventUpdate
    return True
```

**Преимущество**: Разделение логики выбора даты и открытия модала, проще отлаживать.

**Недостаток**: Дополнительный Store, два callback вместо одного.

**Рекомендация**: Выбранный подход оптимален при правильной реализации guard clauses.

---

## ❓ Вопросы для архитектора

1. **TRANSFER транзакции**: Как обрабатывать тип TRANSFER при расчете остатков? Исключать полностью или учитывать как расход?

2. **Конфликт модалов**: Планируется ли использовать общий create-modal из transactions.py или создать отдельный calendar-create-modal?

3. **Мобильная версия**: Brief упоминает "На мобильных (<768px) показывается список дней вместо сетки". Это входит в scope Фазы 3 или откладывается на Batch 3?

4. **Предзаполнение формы**: При клике по дню с существующими операциями - открывать модал создания или показывать список операций дня с возможностью добавить новую?

---

## 📋 Рекомендации для следующей итерации

### Обязательно:
1. **Решить проблему сериализации Decimal в dcc.Store** - использовать строковое представление или хранить в копейках
2. **Добавить полные guard clauses в open_create_modal_from_calendar()** - согласно паттерну из transactions.py
3. **Определить поведение для TRANSFER транзакций** - добавить в CalendarService явную фильтрацию
4. **Добавить сигнатуру refresh_calendar_after_transaction()** - критично для интеграции

### Желательно:
1. Добавить локализацию месяцев на русский язык
2. Добавить валидацию диапазона +-12 месяцев в навигации
3. Уточнить threshold для желтого предупреждения остатка
4. Рассмотреть уникальные ID для модалов календаря

### Опционально:
1. Добавить animated transitions при переключении месяцев (CSS)
2. Рассмотреть lazy loading для tooltips с операциями
3. Добавить keyboard navigation (arrow keys для навигации по дням)

---

## 🔄 Изменения с предыдущей итерации
(N/A - первая итерация)
