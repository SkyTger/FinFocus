# Review Log: 0021-dashboard-foundation

> Записи только добавляются.

---

## Step 1-m: CI/CD
- No CI checks configured on this repo — not a blocker
- PR #21 is OPEN (not draft), head branch: 0021-dashboard-foundation

## Step 2-m: Local Verification
- **Black**: OK — 83 files clean
- **Flake8**: 5 pre-existing E501 + 2 new E501 in calendar.py (introduced by format_rub calls)
- **Fix**: extracted `adj_fmt` variable in calendar.py lines 1527-1533 → committed as `68eb161`
- **Pytest**: 492 passed, 1 pre-existing failure (test_budget_change_updates_allocation — Decimal precision)
- **Verdict**: PASS (all new code clean, pre-existing issues not introduced by this PR)

---
