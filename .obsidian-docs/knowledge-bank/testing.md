---
name: testing
description: Стратегия тестирования FinFocus — 825 тестов, стратегия относительных дат против календарного протухания, CI на pytest
type: reference
---

# Стратегия тестирования FinFocus

## Текущий статус

**825 тестов, все проходят** (протокол 0031, смержен 2026-08-30 —
`825 passed`, 0 xfailed = 766 на main + 67 новых (60
`test_nav_rail.py` + 7 `test_version.py`) + 4 про версию в окне
профиля − 8 удалённых вместе с `test_sidebar.py` − 4 переехавших
из него в `test_nav_rail.py`. Отдельно: на main один из 766 тестов
падает в последние дни месяца — протухание фикстуры, починено этим
же протоколом. До 0031 было 766
(протокол 0030: карточки-двери щитка), до 0030 — 693 (протокол 0029:
639 + 7 регрессионных `CalendarService` + 47 визуального слоя щитка),
до 0028 — 565 базовых, проверено 2026-08-21, Python 3.10.12).
Тестов в `tests/`: 44 файла (`test_*.py`, без подкаталогов), включая
`test_panel_service.py` (19), `test_panel_cards_ui.py` (26),
`test_nav_rail.py` (43), `test_version.py` (7),
`test_panel_query_params.py` (14).

Запуск:
```bash
pytest -q          # быстрый прогон
pytest --cov        # с coverage-отчётом
```

## Testing Stack

**pytest 7.4.3** - основной testing framework
- Fixtures для session management
- Параметризация тестов
- Test discovery (`tests/test_*.py`)

**pytest-cov 4.1.0** - code coverage
- Coverage reports (terminal + HTML)

## КРИТИЧНО: стратегия дат — избегаем календарного протухания

Ключевые сервисы считают **от `date.today()`**, а не от фиксированной точки:
- `BudgetReservationService` строит recurring-шаблон резерва от текущей даты
- `Goal.monthly_contribution` (`app/models/database.py:289-317`) делит остаток
  до цели на `(target_date - today).days / 30` — размер взноса зависит от
  того, сколько дней осталось "сегодня"

Следствие: **захардкоженная дата в тесте протухает**. Тест, зелёный в
феврале, может упасть в августе — не из-за регрессии в коде, а потому что
относительно новой даты изменилось количество месяцев/дней в расчёте.

**Историческая заметка** (чтобы не повторить ошибку диагностики): в марте
2026 (протокол 0025) 7 таких падений были на скорую руку списаны как
"pre-existing failure, precision issue в `test_budget_change_updates_allocation`,
регрессий нет". Диагноз был **неверным** — падения не имели отношения к
точности `Decimal`, это было обычное календарное протухание захардкоженных
дат. Расследовано и исправлено 2026-08-19 (коммит `fix(tests): устранить
протухание тестов из-за захардкоженных дат`). Не воспроизводить
формулировку "precision issue" в будущих отчётах — источник падения другой.

### Хелперы относительных дат (`tests/conftest.py`)

| Хелпер | Сигнатура | Назначение |
|--------|-----------|------------|
| `reserve_period_start` | `(day_of_month: int, today: date \| None = None) -> date` | Дата резерва, которую построит `BudgetReservationService` — повторяет anchored-логику переноса на следующий месяц, если день уже прошёл |
| `days_before` | `(reference: date, days: int = 1) -> date` | `reference - N дней` |
| `days_after` | `(reference: date, days: int = 1) -> date` | `reference + N дней` |
| `far_future_date` | `(years: int = 1) -> date` | 31 декабря через `years` лет — гарантированно в будущем для `target_date` |
| `months_ahead` | `(months: int) -> date` | `today + 30*months` дней — для тестов, зависящих от размера `monthly_contribution` |
| `upcoming_reserve_day` | `(min_gap_days: int = 2) -> int` | Подбирает день месяца резерва, который ещё не прошёл — замена `pytest.skip()` |

### Антипаттерны (не делать)

- ❌ Хардкодить конкретные даты (`date(2026, 3, 15)`) в тестах, завязанных
  на "дни до сегодня"
- ❌ `today.replace(year=today.year + 1)` — падает 29 февраля, такой даты
  нет в невисокосном году следующего года
- ❌ `pytest.skip()` как обход календарной зависимости. Так уже было в
  `test_budget_calendar_integration.py`: 3 теста молча отключались после
  25-го числа месяца, покрытие падало незаметно (тесты формально
  "проходили", просто не выполнялись). Исправлено переходом на
  `upcoming_reserve_day()`.
- ✅ Вместо `pytest.skip()` — вычислить дату относительно `date.today()`
  через хелперы conftest, чтобы сценарий воспроизводился в любой день

### Проверка устойчивости к календарю

Для новых тестов, зависящих от даты, желательно проверять поведение через
заморозку времени (`freezegun`) на нескольких контрольных датах: конец
месяца, конец года, 29 февраля. **На момент 2026-08-19 `freezegun` в
зависимостях и тестах проекта не используется** — это рекомендация на
будущее, не текущая практика.

**Важное ограничение**: заморозка времени ломает тесты, измеряющие
реальное время выполнения — например `calculation_time_ms` в
`redistribution_service.py:136` (используется в `test_serializers.py`).
Такие тесты нужно исключать из прогона с `freeze_time`.

## Testing Pyramid (структура, актуально)

### 1. Unit Tests
**Scope**: Отдельные функции и классы — сервисы (`TransactionService`,
`GoalService`, `BudgetReservationService`), модели (`Goal.monthly_contribution`,
`Goal.progress_percentage`), кастомные исключения.

### 2. Integration Tests
**Scope**: Взаимодействие компонентов — Service + ORM, `GoalService.add_contribution`
(обновление `current_amount` → изменение статуса), календарная интеграция
резервов (`test_budget_calendar_integration.py`).

### 3. E2E / manual QA
Dash-специфичные сценарии (модалки, callbacks) на текущем этапе проверяются
вручную; автоматизация через `dash.testing`/Selenium в проекте не внедрена.

## Test Fixtures (`tests/conftest.py`)

**Database fixtures**:
```python
@pytest.fixture(scope="function")
def db_engine():
    """Создаёт in-memory SQLite engine для тестов."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(db_engine):
    """Создаёт session для тестов с автоматическим rollback."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
```

**User fixtures**: `test_user`, `test_user_zero_balance` — готовые
пользователи для сценариев с ненулевым/нулевым стартовым балансом.

**Date fixtures**: см. таблицу хелперов выше — они не pytest-фикстуры в
строгом смысле (обычные функции), но живут в том же `conftest.py` и
выполняют ту же роль переиспользуемой инфраструктуры тестов.

## Quality Gates (QA workflow)

**Pre-commit checks** (локально):
```bash
black app/               # Format
flake8 app/              # Lint
pytest -q                # Run tests
```

**CI** (`.github/workflows/tests.yml`, реально существует):
- Триггеры: `push` в `main`, `pull_request`, ручной запуск (`workflow_dispatch`)
- Матрица: Python 3.10 и 3.12 (`fail-fast: false` — падение на одной версии
  не отменяет прогон на другой)
- Устанавливает `requirements-dev.txt`, запускает `pytest -q`
- **Линтеры (`black --check`, `flake8`) в CI намеренно не включены** — в
  `app/` есть unresolved pre-existing E501 (превышение длины строки),
  включение линта заблокировало бы CI без реальной пользы

**QA тестирование** (manual):
- Функциональное тестирование основных сценариев
- Bug reporting с приоритетами (P1-P4)
- Regression testing после багфиксов

## Edge Cases для тестирования

**Goal.monthly_contribution**:
- `target_date` в прошлом или сегодня → return 0
- `current_amount >= target_amount` → return 0
- `days_remaining < 30` → `months_remaining` берётся с минимумом 1

**GoalService.add_contribution**:
- Сумма взноса > остаток до цели → статус COMPLETED
- Отрицательный взнос → ValidationError
- Дата взноса в будущем → ValidationError

**Pattern-Matching Callbacks**:
- Auto-trigger при DOM update → PreventUpdate
- Multiple clicks на одну кнопку → idempotency

## Metrics

**Test Execution Time**: полный прогон 825 тестов — около 7 секунд
локально (`pytest -q`, Python 3.10.12, in-memory SQLite).

## Mutation-проверка формул (практика протокола 0028)

Для тестов на инвариант, который остаётся верным при неправильной
раскладке результата (например «сумма частей равна целому» — верно
и для правильного, и для сломанного разбиения), сам инвариант не
защита корректности. Практика, применённая для `MoneyLayersService`
(таблица ожидаемых слоёв, `test_money_layers_service.py`): вручную
портить ключевые строки формулы (убрать слагаемое, снять границу,
перевернуть порядок операций) и проверять, что порча роняет тесты.

На протоколе 0028 mutation-проверка поймала случай, когда одна и та
же порча (снятие верхней границы месяца в формуле резерва) была
не видна тесту с нулевым ожидаемым значением — обе версии формулы,
верная и испорченная, обрезались `max(0, …)` до нуля в выбранном
сценарии. Тест добавлен с ненулевым ожиданием именно для того, чтобы
различие стало видимым. Вывод: для инвариантов такого рода мутационная
проверка — не разовая формальность, а инструмент подбора самих
тестовых сценариев.

---

Референсы:
- pytest docs: https://docs.pytest.org/
- `.github/workflows/tests.yml` — CI-конфигурация
- Историческая заметка про протухание дат: `tests-calendar-rot.md`
  (автопамять проекта, `~/.claude/projects/-home-skytiger-Projects-FinFocus/memory/`)

---

**Последнее обновление**: 2026-08-30 (протокол 0031, смержен, f504fa8 —
счётчик 766 → 825 тестов: +60 `test_nav_rail.py` (полоска-меню;
заменил удалённый `test_sidebar.py` как регрессионный якорь
навигации; из них 13 добавлены на ревью — тесты аватара
параметризованы по всем разделам, AC-7), +7 `test_version.py`
(источник версии, сверка с git-тегом), +4 в
`test_profile_modal_callbacks.py` (версия в окне профиля),
−8 удалённых вместе с сайдбаром, +1 активированный из xfail. Попутно починен протухавший в конце месяца
`test_payments_tooltip_lists_operations`).
Предыдущее: 2026-08-26 (протокол 0030, смержен — счётчик
693 → 766 теста: +19 `test_panel_service.py` (композитор
`DashboardPanelService`, включая регрессионный тест границ карточки
«Аналитика»), +26 `test_panel_cards_ui.py` (дерево карточек без БД),
+11 `test_sidebar.py` (сайдбар без колбэков), +14
`test_panel_query_params.py` (владение `url.search`), +1 адаптационный
и +1 на ревью 3.5-m-fix (регрессия двухуровневой двери Wishlist,
`test_wishlist_links_not_inside_door_node`)).
Предыдущее: 2026-08-25 (протокол 0029, смержен — счётчик 639 → 693
теста: +7 регрессионных для багфикса `CalendarService`, +47 для
визуального слоя дашборда-щитка, новый файл `test_dashboard_panel_ui.py`).
До этого: 2026-08-25 (протокол 0028, смержено — счётчик 565 → 639
тестов, добавлена практика mutation-проверки формул). Ранее:
2026-08-19 (аудит KB: заменено устаревшее "0% coverage" на факт;
задокументирована стратегия относительных дат
и хелперы conftest; описан реальный CI)
