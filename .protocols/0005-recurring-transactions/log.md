# Work Log: 0005 — Повторяющиеся операции (Recurring Transactions)

Этот раздел является **журналом**. Записи только добавляются, старые не изменяются.

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
