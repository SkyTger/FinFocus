# ADR-004: Архитектура повторяющихся операций

## Статус
Принято (2026-01-20)

## Контекст
Пользователи регулярно вводят одни и те же операции (зарплата, аренда, подписки).
Необходима автоматизация с возможностью редактирования отдельных экземпляров.

## Рассмотренные варианты

### Вариант A: Pre-generation (создание заранее)
Создавать все экземпляры recurring операции заранее в БД.

**Плюсы**: Простой код, стандартные запросы
**Минусы**: Раздувание БД, сложное изменение серии, проблема бесконечных серий

### Вариант B: Pure virtual (полностью виртуальные)
Хранить только шаблоны, генерировать все экземпляры динамически.

**Плюсы**: Минимальное хранилище
**Минусы**: Невозможно редактировать отдельные экземпляры

### Вариант C: Гибридный (выбранный)
Шаблоны + exceptions + виртуальная генерация.

**Плюсы**: Минимальное хранилище, гибкое редактирование
**Минусы**: Сложность генерации, фильтрация в запросах

## Решение
Гибридная архитектура с Anchored-алгоритмом:

### Структура данных

1. **Шаблоны** — Transaction с `is_recurring=True`
   - `recurring_period`: weekly, biweekly, monthly, quarterly
   - `recurring_end_date`: дата окончания (None = бессрочно)

2. **Exceptions** — Transaction с `recurring_parent_id`
   - `original_date`: исходная дата экземпляра
   - `is_skipped`: пропущен ли экземпляр
   - UniqueConstraint(recurring_parent_id, original_date)

3. **Виртуальные экземпляры** — VirtualTransaction (TypedDict)
   - Генерируются динамически
   - JSON-совместимы для dcc.Store

### Anchored-алгоритм
Сохраняет исходный день месяца при переходе между месяцами.

```
Пример: шаблон 31 января
- Февраль: 28 (или 29)
- Март: 31
- Апрель: 30
- Май: 31
```

Алгоритм: `min(anchor_day, last_day_of_month)`

### Ключевые решения

1. **VirtualTransaction как TypedDict** — JSON-совместимость для dcc.Store
2. **MAX_INSTANCES_PER_CALL = 1000** — защита от DoS при бессрочных шаблонах
3. **MAX_FORECAST_DAYS = 366** — ограничение горизонта прогноза
4. **CASCADE delete** — удаление шаблона удаляет все exceptions
5. **Фильтрация шаблонов** — во всех balance-расчетах (`is_recurring=False OR recurring_parent_id IS NOT NULL`)

### Потоки данных

```
Создание recurring:
UI → TransactionService → save Template to DB

Отображение в календаре:
CalendarService.get_all_transactions_for_period()
  → get regular transactions (excluding templates)
  → RecurringService.generate_instances() for each template
  → merge and replace virtuals with exceptions
  → return combined list

Редактирование экземпляра:
UI (scope modal) → "instance" selected
  → RecurringService.create_exception()
  → save Exception to DB

Пропуск экземпляра:
UI → RecurringService.skip_instance()
  → create/update Exception with is_skipped=True
```

## Последствия

### Позитивные
- Минимальное хранилище (только шаблоны + exceptions)
- Простое редактирование серий (изменить шаблон)
- Гибкое редактирование экземпляров (exceptions)
- Понятная логика для пользователей

### Негативные
- Сложность генерации виртуальных экземпляров
- Фильтрация шаблонов во всех запросах балансов
- Дополнительная нагрузка при расчете календаря

### Риски
- Performance при большом количестве шаблонов (митигация: MAX_INSTANCES)
- IntegrityError при concurrent exceptions (митигация: UniqueConstraint)

## Связанные документы
- Protocol: `.protocols/0005-recurring-transactions/`
- RecurringService: `app/services/recurring_service.py`
- CalendarService integration: `app/services/calendar_service.py`
- Model extension: `app/models/database.py`
