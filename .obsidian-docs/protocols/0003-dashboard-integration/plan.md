# 0003 — Dashboard Data Integration

## ADR-style Summary:

- **Context**: Дашборд (`app/components/dashboard.py`) использует hardcoded данные для всех метрик (Total Balance, Income, Expense, Savings) и графиков. Фаза 3 (Кассовый календарь) завершена, CalendarService содержит логику расчета балансов. Требуется интеграция дашборда с реальными данными из SQLite.

- **Problem Statement**: Как подключить дашборд к реальным данным, обеспечив переключение периода (месяц/год), без дублирования логики расчета баланса и с соблюдением паттернов из calendar.py (guard clauses, ADR-003)?

- **Decision**: Создать `DashboardService` как агрегатор, использующий публичные методы CalendarService и GoalService. Расширить CalendarService методами `get_balance_on_date()` и `get_year_summary()`. Рефакторить dashboard.py с добавлением callbacks по паттерну из calendar.py.

- **Alternatives**:
  1. Прямые SQL-запросы в dashboard callbacks — отвергнуто (дублирование логики, нарушение separation of concerns)
  2. Расширение CalendarService всей dashboard-логикой — отвергнуто (нарушение SRP, CalendarService станет слишком большим)

- **Consequences**:
  - (+) Переиспользование проверенной логики CalendarService
  - (+) Единообразие паттернов с calendar.py
  - (+) Тестируемость через DashboardService
  - (-) Дополнительный сервисный слой (+200 строк)

---

## High-Level Plan:

Этот раздел является **контрактом**, не меняй его при реализации.

- **[Шаг 0: Подготовка и фиксация плана](./00-setup.md)**: Создание и фиксация артефактов этого протокола.
- **[Шаг 1: Расширение CalendarService](./01-calendar-service.md)**: Добавить публичные методы `get_balance_on_date()`, `get_year_summary()` и TypedDict `YearSummary`.
- **[Шаг 2: Создание DashboardService](./02-dashboard-service.md)**: Создать новый сервис с методами `get_overview_metrics()`, `get_cashflow_data()`, `get_recent_transactions()`.
- **[Шаг 3: Обновление exports](./03-services-init.md)**: Обновить `app/services/__init__.py` для экспорта новых компонентов.
- **[Шаг 4: Рефакторинг Dashboard UI](./04-dashboard-ui.md)**: Добавить dcc.Store, callbacks, переписать функции build_* для приема данных.
- **[Шаг 5: Unit тесты](./05-tests.md)**: Создать тесты для DashboardService и новых методов CalendarService.
- **[Шаг 6: Финализация](./06-finalize.md)**: Интеграционное тестирование, перевод PR в Ready, завершение работы.

---

## Protocol Workflow (Инструкция по выполнению):

**Твоя задача — выполнять шаги из `High-Level Plan`, строго следуя этому рабочему циклу для каждого шага.**

- **Папка проекта (PROJECT_ROOT)**: `/home/skytiger/PycharmProjects/FinFocus`
- **Папка worktree (CWD)**: `/home/skytiger/PycharmProjects/worktrees/0003-dashboard-integration`
- **Папка протокола**: `/home/skytiger/PycharmProjects/worktrees/0003-dashboard-integration/.protocols/0003-dashboard-integration`

**Вся работа ведется из папки worktree (CWD).**

### A. Перед началом нового шага (Восстановление контекста)
1.  Определи текущий шаг, прочитав `Current Step` из файла `context.md` в папке протокола.
2.  **Открой и изучи файл этого шага** (например, `01-calendar-service.md`). Он содержит полный набор инструкций.
3.  Убедись, что все предыдущие изменения закоммичены.

### B. Во время выполнения шага (Исполнение)
1.  Выполняй подзадачи, описанные в файле текущего шага.
2.  **Не изменяй файлы планов** (`plan.md`, `XX-*.md`). Они являются контрактом.
3.  Следуй общим принципам, изложенным ниже.

### C. Сразу после завершения шага (Верификация и Фиксация)
1.  Выполни проверки: `black`, `flake8`, `pytest`. Исправляй проблемы, пока все проверки не пройдут.
2.  **Добавь запись в `log.md`**: Опиши, что было сделано, и **почему** были приняты неочевидные решения. Сошлись на ID коммита.
3.  **Полностью перезапиши `context.md`** новым состоянием для следующего шага.
4.  Проверь ветку main чтобы не было случайно добавленных наших файлов из нашей ветки. **Сделай коммит** с сообщением по формату `type(scope): subject [protocol-0003/YY]`. Сделай пуш.
5.  Сообщи пользователю о завершении шага в установленном формате.

---

## Generic Principles (MUST follow):

1. **Баланс и простота**: Избегай оверинжиниринга. Не вводи лишних абстракций. Решения — самые простые из возможных, но функциональные и надежные.

2. **Никакого легаси**: Удаляй устаревший код. Обратная совместимость не требуется.

3. **Стандарты кода**:
   - Python 3.12+ с type annotations
   - Docstrings на русском языке
   - black (88 chars) + flake8
   - Guard clauses в начале функций

4. **Паттерны из calendar.py (ADR-003)**:
   - `prevent_initial_call=True` для Pattern-Matching callbacks
   - Проверка `ctx.triggered[0].get("value") is None` для фильтрации автовызовов
   - try/except с logger.error() и graceful degradation
   - dcc.Store с serialize/deserialize для Decimal

5. **Session Management**:
   - Сервисы используют `flush()`, caller делает `commit()`
   - Context manager `with get_db_session() as session:`

6. **Тесты**: Покрытие ключевых сценариев (минимум 9 тестов для DashboardService).

---

## Reference Materials

- **Brief**: `.design/brief.md` — функциональные требования FR-01..FR-08, NFR-01
- **Solution**: `.design/solution-v2.md` — архитектура решения
- **Calendar паттерн**: `app/components/calendar.py` — референс для callbacks
- **CalendarService**: `app/services/calendar_service.py` — методы для переиспользования
- **ADR-003**: `docs/adr/ADR-003-pattern-matching-callbacks-issue.md` — guard clauses
