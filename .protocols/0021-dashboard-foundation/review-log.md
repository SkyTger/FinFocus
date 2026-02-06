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

## Step 2.5-m: Security Audit
- **Bandit**: PASS — no findings
- **pip-audit**: not installed (skip)
- **safety**: not installed (skip)
- **Verdict**: PASS

## Step 3-m: Code Review
- **Diff**: 21 files changed, +794/-172 lines (10 protocol docs + 11 code/test/css files)
- **Plan compliance**: All 6 steps completed (format_rub, CSS vars, dashboard, calendar, analytics, finalize)
- **format_rub()**: Correct implementation — handles Decimal/float/int/None, show_sign, U+2212, .00 hidden
- **CSS variables**: 15 new vars + deprecated aliases for backward compat
- **Dashboard**: _build_kpi_card() replaces create_metric_card(), 12 format_rub() callsites, AI/Exchange hidden (TODO Epic-08)
- **Calendar**: format_balance() refactored, 4 callsites + stats + tooltip + reconciliation updated
- **Analytics**: 2 inline replacements, Plotly hovertemplate intentionally unchanged
- **Tests**: 10 new test_formatters.py, 2 calendar tests updated for typographic minus
- **Security**: No findings (no eval/exec/secrets/injection)
- **Minor non-blocking**: Exchange card has hardcoded $100.00 — card is hidden, Epic-08 will rewrite
- **Verdict**: PASS — approved for merge

---
