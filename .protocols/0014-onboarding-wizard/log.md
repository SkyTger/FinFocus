# Work Log: 0014-onboarding-wizard — Onboarding Wizard

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0014#ctx-N -->

- Restore context: protocol-0014#ctx-1

---

## Step Log

### Step 00 — Setup (commit: 067ffd4)
- Protocol artifacts created from solution-v3.md
- 11-step plan based on approved design (5/5 stars)
- Key decisions from design:
  - DB failure strategy: fail-closed
  - Query param cleanup: full (url.search = "")
  - flush/commit contract documented in service docstring

### Step 01 — Schema + Model (commit: 0659dfc)
- Added User.first_launch: Boolean, default=True, nullable=False
- Created OnboardingStatus TypedDict (first_launch, starting_balance, needs_balance_alert)
- Exported in app/schema/__init__.py

### Step 02 — Migration Script (commit: e048e7a)
- Created scripts/migrate_003_first_launch.py (следуя паттерну migrate_NNN_name.py)
- Logic: starting_balance != 0 → first_launch = False
- Idempotent: проверяет PRAGMA table_info перед ALTER

### Step 03 — OnboardingService (commit: f70e66e)
- Created OnboardingService with get_status, complete_with_balance, skip methods
- flush/commit contract documented in class docstring
- Exported in app/services/__init__.py

### Step 04 — Unit Tests (commit: e666816)
- Created tests/test_onboarding_service.py with 8 tests
- Coverage: get_status (3), complete_with_balance (3), skip (2)
- Added email field to User fixtures (email is required in model)

### Step 05 — Wizard UI (commit: pending)
- Created app/components/onboarding_wizard.py
- Blocking modal: backdrop="static", keyboard=False, no close button
- InputGroup with ruble sign, warning div for negative balance
- Buttons: "Пропустить" (secondary), "Продолжить" (success, disabled by default)
