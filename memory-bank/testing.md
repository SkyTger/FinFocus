# Стратегия тестирования FinFocus

## Текущий статус
**Coverage**: 0% (тесты не написаны)
**Цель для Core MVP**: 80% покрытие критических компонентов

## Testing Stack

**pytest 7.4.3** - основной testing framework
- Fixtures для session management
- Параметризация тестов
- Test discovery (`tests/test_*.py`)

**pytest-cov 4.1.0** - code coverage
- Coverage reports (terminal + HTML)
- Coverage thresholds для CI/CD

## Testing Pyramid (приоритеты)

### 1. Unit Tests (70% от всех тестов)
**Scope**: Отдельные функции и классы

**Приоритет 1** (КРИТИЧНО):
- **TransactionService** - CRUD методы, валидация
- **GoalService** - CRUD, add_contribution, валидация
- **Goal.monthly_contribution** - guard clauses, формула расчета
- **Goal.progress_percentage** - cap на 100%, edge cases

**Приоритет 2**:
- **User model** - relationships, starting_balance
- **Transaction model** - enum validation
- **ValidationError** - custom exceptions

**Пример теста**:
```python
# tests/test_services/test_transaction_service.py
import pytest
from decimal import Decimal
from app.services.transaction_service import TransactionService, ValidationError

def test_create_transaction_success(db_session, test_user):
    service = TransactionService()
    data = {
        'amount': Decimal('1500.00'),
        'transaction_type': 'income',
        'transaction_date': date.today(),
        'description': 'Зарплата'
    }

    transaction = service.create_transaction(db_session, test_user.id, data)
    assert transaction.id is not None
    assert transaction.amount == Decimal('1500.00')

def test_create_transaction_negative_amount(db_session, test_user):
    service = TransactionService()
    data = {'amount': Decimal('-100.00'), ...}

    with pytest.raises(ValidationError, match="положительной"):
        service.create_transaction(db_session, test_user.id, data)
```

### 2. Integration Tests (20% от всех тестов)
**Scope**: Взаимодействие компонентов

**Приоритеты**:
- **Service + ORM**: создание операции → сохранение в БД → retrieval
- **GoalService.add_contribution**: обновление current_amount → изменение статуса
- **Session management**: flush → commit → rollback flow

**Пример теста**:
```python
def test_add_contribution_updates_goal(db_session, test_goal):
    service = GoalService()
    initial_amount = test_goal.current_amount

    service.add_contribution(
        db_session,
        test_goal.id,
        amount=Decimal('5000.00'),
        contribution_date=date.today()
    )
    db_session.commit()

    updated_goal = service.get_goal(db_session, test_goal.id)
    assert updated_goal.current_amount == initial_amount + Decimal('5000.00')
```

### 3. E2E Tests (10% от всех тестов)
**Scope**: Полные пользовательские сценарии

**Приоритеты** (для Батча 1):
- **Create Transaction flow**: Open modal → Fill form → Submit → Table updates
- **Edit Transaction flow**: Click Edit → Modal opens → Update → Table refreshes
- **Delete Transaction flow**: Click Delete → Confirm → Table updates

**Инструмент**: Dash Testing (`dash.testing`) или Selenium

**Пример теста**:
```python
def test_create_transaction_e2e(dash_duo):
    app = create_app()
    dash_duo.start_server(app)

    # Navigate to Transactions
    dash_duo.wait_for_element("#transaction-table")

    # Open modal
    dash_duo.find_element("#create-transaction-btn").click()
    dash_duo.wait_for_element("#create-modal")

    # Fill form
    dash_duo.find_element("#amount-input").send_keys("1500")
    dash_duo.find_element("#type-dropdown").click()
    # ...

    # Submit
    dash_duo.find_element("#submit-btn").click()

    # Verify table updated
    table_rows = dash_duo.find_elements("tbody tr")
    assert len(table_rows) > 0
```

## Test Fixtures (pytest)

**Database fixtures**:
```python
# tests/conftest.py
import pytest
from app.models.database import create_database_engine, get_session, Base

@pytest.fixture(scope="function")
def db_engine():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(db_engine):
    session = get_session(db_engine)
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def test_user(db_session):
    user = User(email="test@test.com", name="Test User")
    db_session.add(user)
    db_session.commit()
    return user
```

## Quality Gates (QA workflow)

**Pre-commit checks** (локально):
```bash
black app/               # Format
flake8 app/              # Lint
pytest                   # Run tests
```

**CI/CD pipeline** (GitHub Actions - planned):
```yaml
- name: Run tests
  run: |
    pytest --cov=app --cov-report=xml
    coverage report --fail-under=80  # Fail if < 80%
```

**QA тестирование** (manual):
- Функциональное тестирование основных сценариев
- Bug reporting с приоритетами (P1-P4)
- Regression testing после багфиксов

## Testing Priorities (Roadmap)

**Фаза 1** (Database Integration) ✅:
- QA тестирование выполнено (PASS 95/100)
- Unit тесты для сервисов - **TODO**

**Фаза 2** (Формы управления) ✅:
- E2E тесты для CRUD операций - **TODO**

**Фаза 3** (Кассовый календарь):
- Unit тесты для расчета остатков
- Integration тесты с Transaction

**Батч 1 завершение**:
- Покрытие >= 80% для критических компонентов
- CI/CD настроен с автотестами

## Edge Cases для тестирования

**Goal.monthly_contribution**:
- target_date в прошлом → return 0
- target_date == сегодня → return 0
- current_amount >= target_amount → return 0
- months_remaining < 1 → использовать 1 месяц

**GoalService.add_contribution**:
- Сумма взноса > остаток до цели → статус COMPLETED
- Отрицательный взнос → ValidationError
- Дата взноса в будущем → ValidationError

**Pattern-Matching Callbacks**:
- Auto-trigger при DOM update → PreventUpdate
- Multiple clicks на одну кнопку → idempotency
- Одновременные clicks на разные кнопки → race condition handling

## Metrics для мониторинга

**Code Coverage**:
- Цель: 80% для Core MVP
- Критичные компоненты: 90%+ (services, models)

**Test Execution Time**:
- Unit tests: < 5 секунд
- Integration tests: < 30 секунд
- E2E tests: < 2 минуты

**Bug Metrics**:
- P1 bugs: 0 (блокеры)
- P2 bugs: < 3 (критичные)
- Regression bugs: < 10% от исправленных

---

Референсы:
- pytest docs: https://docs.pytest.org/
- Dash Testing: https://dash.plotly.com/testing
- QA Report: `.reports/notes/feature_progress.md` (Фаза 1)
