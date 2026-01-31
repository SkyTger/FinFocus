# Протоколы разработки

## Суть
История выполненных протоколов — детализированных технических задач с пошаговой реализацией.

## Формат протокола
Каждый протокол — изолированная задача в worktree с детальным планом (6 шагов), логом работы и commit-trail.

## Завершенные протоколы

### Протокол 0014: Onboarding Wizard (2026-01-31)
**Статус**: ✅ MERGED (PR #14)
**Батч**: Epic-04-Advanced Features (Batch 4, Onboarding)
**Worktree**: `/worktrees/0014-onboarding-wizard`

**Контекст**:
- FinFocus требует корректной настройки starting_balance для точных расчетов кассового календаря
- Новые пользователи часто пропускают этот критичный шаг
- Как обеспечить настройку starting_balance при первом входе без блокировки опытных пользователей?

**Решения**:
- Blocking modal-wizard при first_launch=True
- Toast на Dashboard для пользователей с balance=0 (мягкое напоминание)
- Calendar query param ?open_recon=1 для автооткрытия модала сверки
- Fail-closed DB strategy (wizard скрывается при ошибке, не блокирует приложение)
- Flush/commit contract в сервисе (docstring)

**Реализация** (11 шагов):
1. **Schema + Model** (commit 0659dfc)
   - User.first_launch: Boolean, default=True, nullable=False
   - OnboardingStatus TypedDict (first_launch, starting_balance, needs_balance_alert)
   - Exported in app/schema/__init__.py

2. **Migration Script** (commit e048e7a)
   - scripts/migrate_003_first_launch.py
   - Logic: starting_balance != 0 → first_launch = False
   - Idempotent: проверяет PRAGMA table_info перед ALTER

3. **OnboardingService** (commit f70e66e)
   - get_status(user_id) → OnboardingStatus
   - complete_with_balance(user_id, starting_balance) — flush(), caller commit()
   - skip(user_id) — first_launch=False, balance остается 0
   - Flush/commit contract documented в class docstring
   - Exported in app/services/__init__.py

4. **Unit Tests** (commit e666816)
   - tests/test_onboarding_service.py: 8 тестов
   - TestGetStatus (3), TestCompleteWithBalance (3), TestSkip (2)
   - Added email field to User fixtures (model requirement)

5. **Wizard UI** (commit ae8824d)
   - app/components/onboarding_wizard.py
   - Blocking modal: backdrop="static", keyboard=False, no close button
   - InputGroup с ruble sign, warning div для negative balance
   - Buttons: "Пропустить" (secondary), "Продолжить" (success, disabled by default)

6. **Wizard Callbacks** (commit 3bab87f)
   - check_onboarding_and_validate: checks first_launch on URL change, validates input
   - handle_onboarding_action: submit or skip с ADR-003 guard clauses
   - DB failure strategy: fail-closed (hide wizard on error)

7. **Main Integration** (commit c5cd192)
   - Exported create_onboarding_wizard в app/components/__init__.py
   - Added wizard to main.py layout после transaction_modals
   - Added dcc.Store("balance-toast-dismissed") для toast session state

8. **Dashboard Toast** (commit 59eb24b)
   - _build_balance_toast() function для zero-balance warning
   - Toast shows если starting_balance == 0 и not dismissed
   - CTA button links to /calendar?open_recon=1
   - 2 callbacks: toggle_balance_toast, persist_toast_dismissal

9. **Calendar Query Param** (commit d4a0f92)
   - Extended toggle_reconciliation_modal для обработки ?open_recon=1
   - Added Input("url", "search") и State("url", "pathname")
   - Query cleanup strategy: full (returns "" to clear query string)
   - All return statements updated с 6th element для url.search

10. **CSS Styles** (commit cd891f1)
    - app/assets/onboarding.css (~80 lines)
    - Стили .onboarding-modal (green gradient header, border-radius)
    - Стили .balance-toast (warning colors)
    - Responsive adjustments для mobile

11. **Финализация** (commit 3b72b95)
    - Black: 2 files reformatted
    - Flake8: fixed 2 E501 line too long errors
    - Pytest: 300 tests PASSED (было 292, +8 для OnboardingService)
    - PR #14 marked as Ready

**Результат**:
- +~500 строк (onboarding_wizard.py, dashboard toast, calendar query param)
- +~80 строк OnboardingService
- +8 unit тестов (300 всего)
- Migration script для существующих пользователей
- Fail-closed DB strategy для production safety

**Критичные детали**:
- User.first_launch — Boolean флаг (не Nullable, default=True)
- Flush/commit contract — сервис flush(), caller commit() (documented в docstring)
- Fail-closed DB strategy — wizard скрывается при ошибке БД, не блокирует UI
- Query param full cleanup — url.search = "" (не оставляем артефактов в URL)
- ADR-003 guard clauses — n_clicks проверки для предотвращения автовызовов
- Toast dismissal в session Store (не в БД) — сброс при новой сессии

**Референсы**:
- План: `.protocols/0014-onboarding-wizard/plan.md`
- Лог: `.protocols/0014-onboarding-wizard/log.md`
- Brief: `.design/brief.md`
- Solution v3: `.design/solution-v3.md`

---

### Протокол 0013: Safety Cushion (2026-01-30)
**Статус**: ✅ READY FOR REVIEW (PR #13)
**Батч**: Epic-04-Advanced Features (Batch 4, Safety Cushion)
**Worktree**: `/worktrees/0013-safety-cushion`

**Контекст**:
- В MVP планировщика бюджета отсутствует функционал финансовой подушки безопасности
- Резервный фонд для непредвиденных расходов — критичная часть финансового планирования
- Подушка НЕ является Goal (не участвует в распределении бюджета накоплений)

**Решения**:
- Подушка как 3 поля в User (не отдельная таблица) — простота для single-user MVP
- CushionService отдельный сервис с CRUD методами
- Percent NewType для type safety порогов
- Калькулятор сценариев для рекомендации размера подушки

**Реализация** (8 шагов):
1. **Schema + Model** (commit 12ed5a4)
   - TypedDicts: CushionSettings, CushionScenario (app/schema/cushion.py)
   - Percent NewType = int (0-100 range validation)
   - User модель: +cushion_target, +cushion_threshold_percent, +cushion_threshold_manual

2. **CushionService** (commit 560da11)
   - get_settings() — возвращает CushionSettings с вычисляемыми полями
   - update_settings() — обновление с валидацией
   - reset_settings() — сброс к default (target=0, threshold=30%)
   - calculate_recommendation() — расчет по сценариям (sum/max_scenario)
   - Константы: DEFAULT_THRESHOLD_PERCENT = 30, VALID_CALC_MODES

3. **Unit Tests** (commit 38a1817)
   - tests/test_cushion_service.py: 20 тестов
   - TestValidatePercent (5), TestGetSettings (7), TestUpdateSettings (3)
   - TestResetSettings (1), TestCalculateRecommendation (4)

4. **Card UI** (commit f36e0bb)
   - _build_cushion_card() — карточка на /goals (~180 строк)
   - Состояния: "Не настроена" / "Настроена"
   - Прогресс-бар с маркером порога риска
   - 4 цветовых статуса: danger/warning/info/success
   - dcc.Store: cushion-settings-store, cushion-refresh-trigger

5. **Modal UI** (commit 6a152ee)
   - _build_cushion_modal() — модал настройки (~175 строк)
   - Поля: cushion-target-input, cushion-threshold-input
   - Collapsible калькулятор сценариев
   - RadioItems режима расчёта (sum/max_scenario)
   - dcc.Store: cushion-scenarios-store, cushion-threshold-manual-flag

6. **Callbacks** (commit a31154c)
   - 12 callbacks (~450 строк):
     1. render_cushion_card — рендер из store
     2. load_cushion_settings — загрузка из БД
     3. open_cushion_modal, 4. close_cushion_modal
     5. populate_cushion_modal — заполнение при открытии
     6. mark_threshold_manual — флаг manual=True
     7. toggle_calculator — collapsible
     8. add_scenario — Pattern-Matching
     9. remove_scenario — Pattern-Matching
     10. calculate_recommendation — расчет
     11. apply_recommendation — применение к полю
     12. save_cushion_settings, 13. reset_cushion_settings
   - Все с ADR-003 guard clauses

7. **CSS** (commit 76c8f96)
   - Стили .cushion-* (~200 строк)
   - Варианты: .cushion-danger/warning/info/success
   - Прогресс: .cushion-progress-container, .cushion-threshold-marker
   - Responsive: breakpoints 768px, 576px

8. **Финализация** (commit fd5326f)
   - Black: OK
   - Flake8: 5 E501 исправлено
   - Pytest: 292 passed (было 272, +20 для CushionService)

**Результат**:
- +~1000 строк в goals.py (карточка + модал + callbacks)
- +~180 строк CushionService
- +20 unit тестов (292 всего)
- Percent NewType для type safety
- Калькулятор сценариев для рекомендации

**Критичные детали**:
- Percent NewType — type safety для порогов (0-100 validation)
- cushion_threshold_manual — фиксированная сумма порога (альтернатива процентам)
- Калькулятор сценариев: sum (сумма всех) vs max_scenario (максимальный)
- Прогресс = User.current_balance / cushion_target (требует актуализации баланса)
- Подушка НЕ Goal — не участвует в AllocationService распределении

**Следующие шаги** (протокол 0014):
- Календарная визуализация подушки (график пополнения)
- Умное распределение неосвоенного бюджета накоплений

**Референсы**:
- План: `.protocols/0013-safety-cushion/plan.md`
- Лог: `.protocols/0013-safety-cushion/log.md`
- Brief: `.design/brief.md`
- Solution v3: `.design/solution-v3.md`

---

### Протокол 0012: Quick-Add Chips (2026-01-25)
**Статус**: ✅ READY FOR REVIEW (PR #12)
**Батч**: Epic-04-Advanced Features (Batch 4, Quick-Add Chips)
**Worktree**: `/worktrees/0012-quick-add-chips`

**Контекст**:
- После Батча 3 создание операций требует 6 шагов
- Quick-add chips позволяют сократить процесс до 3-4 шагов
- Протокол A (hardcoded chips) как фундамент для Протокола B (кастомные шаблоны)

**Реализация** (8 шагов):
1. **Schema и константы** (commit ffb88d3)
   - TypedDict QuickAddChipData (category_id, name, icon, type)
   - DEFAULT_QUICK_ADD_CHIP_NAMES — 7 названий (5 expense + 2 income)
   - _get_quick_add_chips() — lookup по имени с warning

2. **UI секция Quick-add** (commit 76be290)
   - _build_quick_add_chip() — вертикальный layout (иконка + название)
   - _build_quick_add_section() — группировка expense/income + кнопки "Ещё"
   - Интеграция в transactions layout между header и фильтрами

3. **Модал "Ещё..."** (commit 2fdcaec)
   - _build_category_more_modal() — dbc.Modal с Tabs
   - load_more_modal_categories() callback — динамическая загрузка
   - Pattern-Matching ID: {"type": "qa-more-category", ...}

4. **Preselection механизм** (commit b500451)
   - dcc.Store: preselected-category, preselected-type
   - set_preselection_on_modal_open() — применение при открытии
   - create_transaction обновлен — reset preselection после создания

5. **Callbacks Quick-add** (commit 69f7837)
   - open_create_from_quick_add() — chip → modal с preselection
   - open_more_modal() — "Ещё..." → modal категорий
   - select_from_more_modal() — выбор → закрытие + открытие create
   - ADR-003 guard clauses во всех 3 callbacks

6. **CSS стили** (commit 0f1b945)
   - Стили .qa-* (~100 строк)
   - Вертикальный layout, hover transform, ellipsis
   - Responsive: horizontal scroll на 768px

7. **Unit тесты** (commit b325864)
   - test_quick_add_chips.py — 13 тестов
   - Покрытие: TypedDict, _get_quick_add_chips(), UI функции

8. **Финализация** (commit 55b334c)
   - Black: 1 файл OK
   - Flake8: 3 unused imports исправлены
   - Pytest: 272 passed

**Результат**:
- +~600 строк в transactions.py/transaction_modals.py
- +13 unit тестов (272 всего)
- Сокращение шагов создания операции: 6 → 3-4
- 7 hardcoded chips готовы к использованию

**Критичные детали**:
- Lookup по имени защищает от ID mismatch между dev/prod окружениями
- Preselection Store Pattern — чистая передача состояния между модалами
- Вертикальный layout чипов экономит горизонтальное пространство
- Pattern-Matching IDs масштабируются для будущих кастомных чипов

**Следующие шаги** (Протокол B):
- Кастомизация chips пользователем
- Частые операции → автоматические шаблоны
- Редактирование/удаление шаблонов

**Референсы**:
- План: `.protocols/0012-quick-add-chips/plan.md`
- Лог: `.protocols/0012-quick-add-chips/log.md`
- Спецификация: `.reports/epics/epic-04-advanced/spec-quick-add-chips.md`
- Design doc: `.design/solution-v3.md`

---

### Протокол 0011: Chips + Bulk + Export UI (2026-01-24)
**Статус**: ✅ MERGED (commit ac25b5d, PR #11)
**Батч**: Epic-03-Analytics (Batch 3.2)
**Worktree**: `/worktrees/0011-chips-bulk-export`

**Контекст**:
- Батч 3.2 был завершен ранее, но UI компоненты потеряны при merge
- Backend методы готовы: `bulk_update_category`, `export_to_csv`, `get_frequent_for_type`
- Требовалось восстановить Chips UI, Bulk actions, CSV export

**Реализация** (6 шагов):
1. **Layout + Helpers** (commit 1b2e3f5)
   - dcc.Store: selected-transactions, frequent-categories
   - dcc.Download: export-download
   - Helper: `_pluralize_operations()` — склонение "операция/операции/операций"
   - Helper: `_build_bulk_panel()` — sticky panel с dropdown

2. **Table + Chips** (commit ef16193)
   - Helper: `_build_chips_cell()` с guard для TRANSFER/ADJUSTMENT
   - Chips из frequent_categories[:5] + overflow dropdown
   - Checkboxes в таблице (select-all + individual)

3. **Chips Callbacks** (commit 1931a48)
   - `load_frequent_categories()` — кеширование через CategoryService
   - `chip_assign_category()` — Pattern-Matching с 3-уровневыми guard clauses (ADR-003)
   - `chip_dropdown_assign_category()` — аналогично для overflow dropdown

4. **Bulk Callbacks** (commit b89c954)
   - `update_selection_state()` — обработка Select All и checkboxes
   - `clear_selection_on_filter_change()` — WYSIWYG поведение
   - `toggle_bulk_panel()` — показ/скрытие с prevent_initial_call=True
   - `bulk_assign_category()` — ValidationError handling, emit trigger

5. **Export + Tests** (commit 240ca5e)
   - `export_transactions()` — filename pattern, UTF-8 BOM
   - tests/test_transactions_callbacks.py: 13 тестов для _pluralize_operations

6. **Финализация** (commit ea62f55)
   - Black: 65 файлов OK
   - Flake8: 0 ошибок
   - Pytest: 259 passed

**Результат**:
- +636 строк в transactions.py
- +81 строка в tests
- 13 новых unit тестов (все PASS)
- Полное восстановление UX функциональности Батча 3.2

**Критичные детали**:
- Pattern-Matching guard clauses (ADR-003) обязательны для chips и bulk callbacks
- TRANSFER/ADJUSTMENT не могут иметь категорию (guard в `_build_chips_cell`)
- Max 100 транзакций для bulk операций (лимит в TransactionService)
- UTF-8 BOM критичен для Excel совместимости экспорта

**Референсы**:
- План: `.protocols/0011-chips-bulk-export/plan.md`
- Лог: `.protocols/0011-chips-bulk-export/log.md`
- Design doc: `.design/solution-v2.md`

---

### Протокол 0010: Analytics & UX Improvements (2026-01-23)
**Статус**: ✅ MERGED (commit ed0fc44, PR #10)
**Батч**: Epic-03-Analytics (Batch 3.2)

**Реализация**:
- AnalyticsService (~290 строк)
- TransactionService: bulk_update_category, export_to_csv
- CategoryService: get_frequent_for_type
- Страница /analytics с donut/bar charts
- UI компоненты (потеряны при merge, восстановлены в протоколе 0011)

**Результат**:
- 246 unit тестов (было 213)
- Memory Bank обновлен

---

### Протокол 0009: Categories + Reconciliation (2026-01-23)
**Статус**: ✅ MERGED (commit merge PR #9)
**Батч**: Epic-03-Analytics (Batch 3.1)

**Реализация**:
- Category модель, TransactionType.ADJUSTMENT
- CategoryService, ReconciliationService
- Сверка баланса через модал
- 16 предустановленных категорий (seed idempotent)

**Результат**:
- 213 unit и integration тестов

---

### Протокол 0008: Redistribution (2026-01-22)
**Статус**: ✅ MERGED (PR #8)
**Батч**: Epic-02-EnhancedPlanning (Batch 2)

**Реализация**:
- RedistributionService с Temporary Status Pattern
- TypedDicts и Serializers для preview/event
- Redistribution Modal UI с анимациями

**Результат**: 23 новых теста

---

### Протокол 0007: Savings Modes (2026-01-22)
**Статус**: ✅ MERGED (PR #7)
**Батч**: Epic-02-EnhancedPlanning (Batch 2)

**Реализация**:
- User.savings_mode (free/medium/strict)
- Множители к monthly_contribution (1.0 / 1.15 / 1.5)
- UI селектор режимов

---

### Протокол 0006: Multiple Goals (2026-01-21)
**Статус**: ✅ MERGED (PR #6)
**Батч**: Epic-02-EnhancedPlanning (Batch 2)

**Реализация**:
- User.monthly_savings_budget
- AllocationService с жадным алгоритмом
- TypedDicts модуль (app/types/)
- Goals UI рефакторинг (~600 строк)

**Результат**: 98 unit и integration тестов

---

### Протокол 0005: Recurring Transactions (2026-01-20)
**Статус**: ✅ MERGED (PR #5)
**Батч**: Epic-02-EnhancedPlanning (Batch 2)

**Реализация**:
- RecurringService (~550 строк)
- Anchored-алгоритм генерации дат
- Wizard UI "экземпляр vs серия"

**Результат**: 75 unit тестов, ADR-004 создан

---

### Протокол 0004: Goals UI (2026-01-19)
**Статус**: ✅ MERGED (PR #4)
**Батч**: Epic-01-CoreMVP (Фаза 5)

**Реализация**:
- Utils модуль (app/utils/formatters.py)
- Goals UI (~1040 строк)
- 10 callbacks для CRUD

**Результат**: 37 unit тестов

---

### Протокол 0003: Dashboard Integration (2026-01-19)
**Статус**: ✅ MERGED (PR #3)
**Батч**: Epic-01-CoreMVP (Фаза 4)

**Реализация**:
- DashboardService (~290 строк)
- CalendarService расширен (get_balance_on_date, get_year_summary)
- Dashboard UI переписан (~685 строк)

**Результат**: 16 новых unit тестов (33 всего)

---

### Протокол 0002: Cash Calendar (2026-01-19)
**Статус**: ✅ MERGED (PR #2)
**Батч**: Epic-01-CoreMVP (Фаза 3)

**Реализация**:
- CalendarService (~310 строк)
- Calendar UI (~700 строк)
- 3 callbacks с guard clauses (ADR-003)

**Результат**: 15 unit тестов

---

## Паттерны протоколов

### Структура протокола
```
.protocols/NNNN-название/
├── plan.md          # High-level план (6 шагов)
├── log.md           # Журнал работы (append-only)
├── context.md       # Restore context записи
├── NN-название.md   # Детальный план каждого шага
└── ...
```

### Commit Convention
```
type(scope): description [protocol-NNNN/NN]

Примеры:
feat(transactions): add chips callbacks [protocol-0011/03]
chore(review): complete review steps 1-3 [protocol-0011/3-m]
docs(protocol): finalize 0011-chips-bulk-export [protocol-0011/06]
```

### Workflow
1. Создание worktree и ветки
2. Пошаговая реализация (6 шагов)
3. Code quality checks (black, flake8, pytest)
4. Finalize документации
5. PR создание и review
6. Merge в main

---

Детали: см. `CLAUDE.md` (Protocol Workflow section), `.protocols/_core/workflow.md`
