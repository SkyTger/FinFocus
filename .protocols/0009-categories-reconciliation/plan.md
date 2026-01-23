# 0009 — Категоризация и Сверка

## ADR-style Summary:

- **Context**: FinFocus — приложение для планирования бюджета с кассовым календарём и накопительными целями. Батч 2 (Enhanced Planning) завершён на 100%. Следующий этап — добавление категоризации операций и механизма сверки остатков для подготовки к аналитике (Батч 3.1).

- **Problem Statement**: Пользователи не могут классифицировать свои операции по категориям (еда, транспорт, зарплата и т.д.), что блокирует будущую аналитику расходов. Также отсутствует механизм корректировки расхождений между расчётным и фактическим балансом.

- **Decision**: Реализовать:
  1. Модель Category как справочник с предзаполненными категориями
  2. Nullable category_id в Transaction (ленивая категоризация)
  3. TransactionType.ADJUSTMENT для корректирующих операций сверки
  4. CategoryService и ReconciliationService
  5. UI: выбор категории в формах, модал сверки на календаре

- **Alternatives**:
  - Пользовательские кастомные категории → отложено, усложняет MVP
  - Account модель (несколько кошельков) → отложено, один баланс пока достаточен
  - Bulk-операции с категориями (chips) → отложено в Батч 3.2

- **Consequences**:
  - (+) Фундамент для аналитики по категориям
  - (+) Ленивый подход — категория опциональна, не блокирует workflow
  - (+) Механизм сверки позволяет корректировать расхождения
  - (-) Категории только системные, без кастомизации пользователем

---

## High-Level Plan:

Этот раздел является **контрактом**, не меняй его при реализации.

- **[Шаг 0: Подготовка и фиксация плана](./00-setup.md)**: Создание и фиксация артефактов этого протокола.
- **[Шаг 1: Модель данных](./01-data-model.md)**: Category модель, TransactionType.ADJUSTMENT, Transaction.category_id FK, seed категорий.
- **[Шаг 2: TypedDicts](./02-typeddicts.md)**: Создание app/schema/categories.py с CategoryOption и ReconciliationPreview.
- **[Шаг 3: CategoryService](./03-category-service.md)**: Сервис для работы с категориями (get_all, get_for_dropdown, seed_default).
- **[Шаг 4: ReconciliationService](./04-reconciliation-service.md)**: Сервис для сверки (get_expected_balance, create_adjustment, get_preview).
- **[Шаг 5: CalendarService](./05-calendar-service.md)**: Обработка ADJUSTMENT в расчётах баланса, расширение TransactionInfo.
- **[Шаг 6: TransactionService](./06-transaction-service.md)**: Замена category на category_id, валидация ADJUSTMENT + recurring.
- **[Шаг 7: RecurringService](./07-recurring-service.md)**: Добавление category_id в VirtualTransaction и наследование в exceptions.
- **[Шаг 8: DashboardService](./08-dashboard-service.md)**: Обновление RecentTransaction с category_name и category_icon.
- **[Шаг 9: UI Transactions](./09-ui-transactions.md)**: Dropdown категорий, колонка с иконкой, фильтр "Без категории".
- **[Шаг 10: UI Calendar](./10-ui-calendar.md)**: Кнопка и модал сверки на странице календаря.
- **[Шаг 11: Финализация](./11-finalize.md)**: Полная верификация (black, flake8, pytest), перевод PR в Ready.

---

## Protocol Workflow (Инструкция по выполнению):

**Твоя задача — выполнять шаги из `High-Level Plan`, строго следуя этому рабочему циклу для каждого шага.**

- **Папка проекта (PROJECT_ROOT)**: `/home/skytiger/PycharmProjects/FinFocus`
- **Папка worktree (CWD)**: `/home/skytiger/PycharmProjects/worktrees/0009-categories-reconciliation`
- **Папка протокола**: `/home/skytiger/PycharmProjects/worktrees/0009-categories-reconciliation/.protocols/0009-categories-reconciliation`

**Вся работа ведется из папки worktree (CWD).**

### A. Перед началом нового шага (Восстановление контекста)
1.  Определи текущий шаг, прочитав `Current Step` из файла `context.md` в папке протокола.
2.  **Открой и изучи файл этого шага** (например, `01-data-model.md`). Он содержит полный набор инструкций.
3.  Убедись, что все предыдущие изменения закоммичены.

### B. Во время выполнения шага (Исполнение)
1.  Выполняй подзадачи, описанные в файле текущего шага.
2.  **Не изменяй файлы планов** (`plan.md`, `XX-*.md`). Они являются контрактом.
3.  Следуй общим принципам, изложенным ниже.
4.  **Важно:** На промежуточных шагах проводится только базовая проверка синтаксиса. Полная верификация (black, flake8, pytest) выполняется ТОЛЬКО на финальном шаге для экономии токенов и контекста.

### C. Сразу после завершения шага (Верификация и Фиксация)
1.  Выполни базовую проверку: убедись что код синтаксически корректен (python -m py_compile для измененных Python файлов).
2.  **Добавь запись в `log.md`**: Опиши, что было сделано, и **почему** были приняты неочевидные решения. Сошлись на ID коммита.
3.  **Полностью перезапиши `context.md`** новым состоянием для следующего шага.
4.  Проверь ветку main чтобы не было случайно добавленных наших файлов из нашей ветки. **Сделай коммит** с сообщением по формату `type(scope): subject [protocol-0009/YY]`. Сделай пуш.
5.  Сообщи пользователю о завершении шага в установленном формате.

---

## Generic Principles (MUST follow):

1. **Баланс и простота**: Избегай оверинжиниринга. Решения должны быть самыми простыми из возможных, но функциональными и надежными.

2. **Никакого легаси**: Удаляй устаревший код. Обратная совместимость не требуется. Все решения — для новой кодовой базы.

3. **Стандарты кодирования проекта**:
   - Python 3.12 с type annotations
   - Docstrings на русском языке
   - Black (88 chars) + flake8
   - Абсолютные импорты (`from app.services import ...`)

4. **Паттерны проекта**:
   - Guard clauses в начале функций
   - Session management: сервисы используют flush(), caller делает commit
   - Pattern-Matching Callbacks: проверка `ctx.triggered[0].get('value') is None`
   - TypedDicts в app/schema/ для типизации

5. **Качественные тесты**: Покрытие сбалансировано. Использовать существующие фикстуры из conftest.py. Минимум 15 unit тестов для новой функциональности.

6. **Memory Bank**: После завершения протокола обновить документацию в .memory-bank/ если изменились ключевые концепции.

---

## Reference Materials

- **Solution**: `.design/solution-v3.md` — финальная архитектура
- **Brief**: `.design/brief.md` — функциональные требования
- **Existing patterns**:
  - `app/schema/goals.py` — пример TypedDicts
  - `app/services/goal_service.py` — пример сервиса
  - `app/components/transactions.py` — пример UI компонента
- **ADR-003**: Pattern-Matching Callbacks guard clauses
