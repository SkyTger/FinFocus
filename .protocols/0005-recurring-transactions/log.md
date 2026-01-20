# Work Log: 0005 — Повторяющиеся операции (Recurring Transactions)

Этот раздел является **журналом**. Записи только добавляются, старые не изменяются.

---

**Restore context**: protocol-0005#ctx-5

## Шаг 7: Финализация

**Дата**: 2026-01-20

**Действия**:
- Запущены тесты с coverage: 75/75 passed
  - recurring_service: 89% coverage
  - calendar_service: 99% coverage
- Создан `docs/adr/ADR-004-recurring-transactions.md`
  - Описана гибридная архитектура с Anchored-алгоритмом
  - Документированы ключевые решения и trade-offs
- Обновлён `ROADMAP.md`:
  - Батч 2 помечен как "В ПРОЦЕССЕ"
  - Recurring transactions отмечены как завершённые
- Обновлён `.reports/notes/feature_progress.md`:
  - Добавлен Батч 8: Recurring Transactions
  - Обновлён статус на Epic-02-EnhancedPlanning
- Обновлён `.memory-bank/modules/services.md`:
  - Добавлена документация RecurringService
- PR #5 переведён в Ready for Review

**Файлы**:
- `docs/adr/ADR-004-recurring-transactions.md` (новый)
- `ROADMAP.md` (обновлён)
- `.reports/notes/feature_progress.md` (обновлён)
- `.memory-bank/modules/services.md` (обновлён)

**Тесты**: 75/75 passed

---

## Шаг 6: UI — визуализация и редактирование recurring

**Дата**: 2026-01-20

**Действия**:
- Обновлён `app/components/calendar.py`:
  - `build_day_cell()` расширен для отображения иконок `is_skipped`, `is_exception`
  - Добавлен класс `has-virtual` для ячеек с виртуальными транзакциями
  - Интеграция с `get_all_transactions_for_period(include_recurring=True)`
- Обновлён `app/components/transactions.py`:
  - Модифицирован `open_edit_modal()` — проверка `is_recurring` и открытие scope modal
  - Добавлен модал `recurring-edit-scope-modal` с выбором "экземпляр vs серия"
  - Добавлен callback `cancel_recurring_edit_scope()` — отмена scope диалога
  - Добавлен callback `process_recurring_edit_scope()` — обработка выбора scope
  - Добавлена кнопка "Пропустить" в edit modal (скрыта для обычных операций)
  - Добавлен callback `skip_recurring_instance()` — пропуск экземпляра recurring
  - Импорт `RecurringService` для работы с пропусками
- Обновлён `app/assets/calendar.css`:
  - `.recurring-indicator` — зеленая иконка повторяющейся операции
  - `.recurring-indicator.skipped` — полупрозрачная иконка пропущенной операции
  - `.exception-indicator` — оранжевая иконка изменённого экземпляра
  - `.calendar-day.has-virtual` — левая зеленая граница для ячеек с recurring

**Файлы**:
- `app/components/calendar.py` — иконки recurring в ячейках (+~25 строк)
- `app/components/transactions.py` — scope wizard + skip functionality (+~130 строк)
- `app/assets/calendar.css` — стили recurring (+~24 строки)

**Тесты**: 75/75 passed

---

## Шаг 5: UI форма создания recurring

**Дата**: 2026-01-20

**Действия**:
- Добавлены UI элементы в create modal `app/components/transactions.py`:
  - `dbc.Checkbox` "Повторяющаяся операция" (`create-is-recurring`)
  - `dbc.Select` период повторения (`create-recurring-period`)
  - `dbc.Input` дата окончания (`create-recurring-end-date`)
  - Секция `create-recurring-section` скрыта по умолчанию
- Добавлен callback `toggle_recurring_section()` — показ/скрытие секции при изменении checkbox
- Расширен callback `create_transaction()`:
  - Добавлены State для 3 новых полей
  - Поддержка создания recurring шаблонов
  - Reset формы при успешном создании
- Расширен `TransactionService.create_transaction()`:
  - Новые параметры: `is_recurring`, `recurring_period`, `recurring_end_date`
  - Валидация recurring полей (период обязателен, допустимые значения)
- Добавлена индикация recurring в таблице (иконка `bi-arrow-repeat`)
- Создан файл `app/assets/transactions.css` с CSS стилями

**Файлы**:
- `app/components/transactions.py` — UI + callbacks (+~170 строк)
- `app/services/transaction_service.py` — валидация recurring (+~40 строк)
- `app/assets/transactions.css` — новый файл (~38 строк)

**Проверки**:
- black: ✅ All done
- flake8: ✅ No errors
- pytest: ✅ 75 passed

---

**Restore context: protocol-0005#ctx-4** (2026-01-20)
- Восстановлен контекст после прерывания
- Обнаружены незакоммиченные изменения (Сценарий B): Шаг 5 почти завершен предыдущей сессией
- Добавлены noqa комментарии для длинных строк в options
- Готов к завершению Шага 5 (коммит + обновление context.md)

---

**Restore context: protocol-0005#ctx-3** (2026-01-20)
- Восстановлен контекст после прерывания
- Обнаружены незакоммиченные изменения (Сценарий B): Шаг 4 уже выполнен предыдущей сессией
- Проверены изменения, запущены quality checks (black ✅, flake8 ✅, pytest 75/75 ✅)
- Готов к завершению Шага 4 (коммит + обновление context.md)

---

**Restore context: protocol-0005#ctx-2** (2026-01-20)
- Восстановлен контекст после прерывания
- Обнаружены незакоммиченные изменения (Сценарий B): все CRUD методы уже добавлены предыдущей сессией
- Проверены изменения, запущены quality checks
- Исправлены deprecation warnings (Query.get() → Session.get())
- Завершено выполнение Шага 3

---

## Шаг 4: Интеграция с CalendarService

**Дата**: 2026-01-20

**Действия**:
- Добавлены фильтры recurring в 5 методов `app/services/calendar_service.py`:
  - `_calculate_balance_before_date()` — `is_recurring == False`, `recurring_parent_id == None`
  - `_get_daily_changes()` — `is_recurring == False`, `recurring_parent_id == None`
  - `get_transactions_by_date()` — `is_recurring == False` (exceptions нужны для UI)
  - `get_month_summary()` — `is_recurring == False`, `recurring_parent_id == None`
  - `get_year_summary()` — `is_recurring == False`, `recurring_parent_id == None`
- Расширен TypedDict `TransactionInfo` для поддержки recurring:
  - Добавлены поля: `template_id`, `date`, `is_virtual`, `is_recurring`, `is_exception`
  - Изменено: `id` теперь `int | None` (для виртуальных)
- Добавлен новый метод `get_all_transactions_for_period()`:
  - Объединяет обычные транзакции + recurring instances
  - Поддерживает параметр `include_recurring`
- Создан файл `tests/test_calendar_recurring.py` с 8 unit тестами

**Файлы**:
- `app/services/calendar_service.py` — изменения + новый метод (+~120 строк)
- `tests/test_calendar_recurring.py` — новый файл (~305 строк)

**Проверки**:
- black: ✅ All done
- flake8: ✅ No errors
- pytest: ✅ 75 passed (было 67, добавлено 8)

---

## Шаг 3: RecurringService — CRUD для exceptions

**Дата**: 2026-01-20

**Действия**:
- Добавлены 7 методов CRUD в `app/services/recurring_service.py`:
  - `get_exceptions_for_template()` — получение exceptions шаблона
  - `create_exception()` — создание/обновление exception
  - `skip_instance()` — пропуск экземпляра (is_skipped=True)
  - `stop_template()` — soft delete (recurring_end_date)
  - `delete_template()` — hard delete с CASCADE
  - `update_template_period()` — изменение периода с savepoint
  - `get_instances_with_exceptions()` — объединение виртуальных + exceptions
- Добавлены импорты: `Decimal`, `ValidationError`
- Исправлены deprecation warnings: `Query.get()` → `Session.get()` (5 мест)
- Добавлены 10 unit тестов в `tests/test_recurring_service.py`

**Файлы**:
- `app/services/recurring_service.py` — расширение (+348 строк)
- `tests/test_recurring_service.py` — расширение (+367 строк)

**Проверки**:
- black: ✅ All done
- flake8: ✅ No errors
- pytest: ✅ 67 passed (было 57, добавлено 10)

---

**Restore context: protocol-0005#ctx-1** (2026-01-20)
- Восстановлен контекст после прерывания
- Обнаружены незакоммиченные изменения в `context.md` (обновление статуса Шаг 0 → Шаг 1)
- Изменений в коде приложения не обнаружено
- Готов к выполнению Шага 1

---

## Шаг 1: Расширение модели Transaction

**Дата**: 2026-01-20

**Действия**:
- Добавлены новые поля в модель Transaction:
  - `recurring_end_date` — дата окончания серии (None = бессрочно)
  - `recurring_parent_id` — FK на шаблон для exceptions (self-referential)
  - `original_date` — исходная дата экземпляра
  - `is_skipped` — флаг пропущенного экземпляра
- Добавлен self-referential relationship: `recurring_parent` ↔ `recurring_exceptions`
- Добавлены индексы: `ix_transaction_recurring_parent`, `ix_transaction_is_recurring`
- Добавлен UniqueConstraint: `uq_recurring_exception_date` (parent_id + original_date)
- Добавлены computed properties: `anchor_day` (с guard clause), `is_exception`
- Создан файл `tests/test_models.py` с 7 unit тестами

**Файлы**:
- `app/models/database.py` — расширение модели Transaction
- `tests/test_models.py` — новый файл с тестами

**Проверки**:
- black: ✅ All done
- flake8: ✅ No errors
- pytest: ✅ 44 passed (было 37, добавлено 7)

---

## Шаг 2: RecurringService — генерация экземпляров

**Дата**: 2026-01-20

**Действия**:
- Создан `app/services/recurring_service.py` (~270 строк):
  - Константы защиты: MAX_INSTANCES_PER_CALL=1000, MAX_FORECAST_DAYS=366
  - TypedDict VirtualTransaction для JSON-сериализации (dcc.Store)
  - RecurringService с методами:
    - `get_templates_for_user()` — получение шаблонов пользователя
    - `_get_anchored_date()` — Anchored-алгоритм (31 янв → 28 фев → 31 мар)
    - `_generate_dates()` — генерация дат по периодам (weekly/biweekly/monthly/quarterly)
    - `generate_instances()` — генерация виртуальных экземпляров с guard clauses
- Обновлен `app/services/__init__.py` — экспорт новых компонентов
- Создан `tests/test_recurring_service.py` с 13 unit тестами

**Anchored-алгоритм**:
- monthly/quarterly сохраняют anchor_day (день шаблона)
- При коротких месяцах: min(anchor_day, last_day_of_month)
- weekly/biweekly используют простой timedelta

**Файлы**:
- `app/services/recurring_service.py` — новый файл
- `app/services/__init__.py` — обновление экспортов
- `tests/test_recurring_service.py` — новый файл с тестами

**Проверки**:
- black: ✅ All done
- flake8: ✅ No errors
- pytest: ✅ 57 passed (было 44, добавлено 13)

---

## Шаг 0: Подготовка и фиксация плана

**Дата**: 2026-01-20

**Действия**:
- Проверено состояние Git: main синхронизирован с origin/main
- Незафиксированные изменения в `.design/` оставлены как есть (по решению пользователя)
- Создан worktree: `../worktrees/0005-recurring-transactions`
- Создана ветка: `0005-recurring-transactions`
- Создана структура протокола в `.protocols/0005-recurring-transactions/`

**Решения**:
- Номер протокола: 0005 (следующий после существующих 0001-0004)
- Структура шагов основана на Solution v3: 7 шагов + setup

**Проверки перед началом**:
- black: ✅ All done
- flake8: ⚠️ 1 warning (E501 в dashboard.py) — не критично
- pytest: ✅ 37 passed

---
