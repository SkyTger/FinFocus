===CRITIQUE_START===
# Critique - Solution v1
Date: 2026-02-06
Reviewer: AI Critic (Claude Opus 4.6)

---

## General Assessment

**Rating:** 4/5

**Verdict:**
- [ ] Excellent, can start coding as-is
- [x] Good, with minor improvements
- [ ] Requires significant changes
- [ ] Not recommended, needs a different approach

**Summary:**
The solution demonstrates strong analytical work on the codebase, with a well-reasoned alias strategy for `format_amount()` and a pragmatic approach to the reconciliation modal (redirect vs. duplication). However, several inaccuracies in inline formatting counts, one missed CSS file with hardcoded colors, an under-specified `format_balance()` refactoring strategy, and a subtle behavioral change risk (`.00` truncation) need to be addressed before coding begins.

---

## Strong Points

1. **Alias strategy for `format_amount()` is excellent**
   - Retaining `format_amount()` as a thin wrapper around `format_rub()` eliminates the need to modify ~34 call sites across 7 files, reducing blast radius dramatically.
   - This is a textbook application of the Strangler Fig pattern for incremental migration.

2. **Reconciliation modal via `/calendar?open_recon=1` redirect**
   - Correctly identifies the Dash limitation (no duplicate component IDs across pages) and reuses the existing mechanism from protocol 0014.
   - Avoids risky refactoring of `calendar.py` modal extraction into `main.py`.

3. **Comprehensive RTM with 20 requirements tracked**
   - Each requirement from `batch-1.md` is traced to a specific implementation step.
   - RTM covers Must/Info types with correct section references.

4. **Thorough inline formatting audit**
   - Identified multiple distinct formatting patterns (6+ types) across dashboard, calendar, and analytics.
   - Correctly noted that Plotly hovertemplates cannot use Python formatters.

5. **Risk table with mitigations**
   - Proactively identified CSS cascade risk with Bootstrap `.btn-success`.
   - Identified the `.00` truncation behavioral change.

---

## Critical Problems (Blockers)

### 1. Inaccurate inline formatting count in `calendar.py` -- understated complexity

**Where:**
- File: `/home/skytiger/PycharmProjects/FinFocus/app/components/calendar.py`
- Solution section: "Inline-formatirovaniya (6 patternov)" table and Step 4

**Problem:**
The solution claims "5 mest" for `f"{balance:,.0f}".replace(",", " ")` in calendar.py. Actual count from grep is **6 distinct occurrences** (lines 95, 419, 465, 471, 475, 478). Additionally, `f"{amount:+,.0f}".replace(",", " ")` at line 468 (adjustment type) is a separate pattern not listed in the table. The solution also claims "2 mesta" for `adjustment.amount:+,.2f` but the actual code shows 2 occurrences at lines 1525 and 1530 plus the `diff:+,.2f` at line 1452 -- totaling **3** inline formatting spots in the reconciliation callback, not 3 as labeled across two different rows.

More importantly, the solution's Step 4 describes updating `format_balance()`, `_build_tooltip_balance()`, `_build_tooltip_transaction_row()`, `build_stats_cards()`, and `build_day_cell()` -- but does not explicitly address the `adjustment.amount:+,.2f` formatting at lines 1525 and 1530 of `apply_reconciliation()`. These are logger.info and Alert messages that also display money to users.

**Why critical:**
If the implementer follows the solution's step-by-step plan literally, they will miss 2-3 inline formatting spots, leading to inconsistent currency display (some amounts in old format, others in new). This directly violates the acceptance criterion "All numbers in the application display in format X XXX rub."

**Recommendation:**
Create a definitive, line-by-line map of ALL inline formatting locations in calendar.py. My audit found these:
- Line 95: `format_balance()` -- `f"{balance:,.0f}".replace(",", " ")` (no ruble sign)
- Line 419: `_build_tooltip_balance()` -- `f"{balance:,.0f}".replace(",", " ") + " rub"`
- Line 465: `_build_tooltip_transaction_row()` -- `f"+{amount:,.0f}".replace(",", " ")`
- Line 468: `_build_tooltip_transaction_row()` -- `f"{amount:+,.0f}".replace(",", " ")` (adjustment)
- Line 471: `_build_tooltip_transaction_row()` -- `f"{amount:,.0f}".replace(",", " ")` (transfer)
- Line 475-478: `_build_tooltip_transaction_row()` -- `f"-{amount:,.0f}".replace(",", " ")` (savings + expense)
- Line 1347, 1385: `toggle_reconciliation_modal()` -- `f"{expected:,.2f} rub"`
- Line 1452: `update_reconciliation_preview()` -- `f"Raznitsa: {diff:+,.2f} rub"`
- Line 1525: `apply_reconciliation()` -- logger: `f"{adjustment.amount:+,.2f} rub"`
- Line 1530: `apply_reconciliation()` -- Alert: `f"{adjustment.amount:+,.2f} rub"`

Total: **12 distinct formatting spots** in calendar.py (not "10 mest" as claimed).

---

## Important Problems (Should Fix)

### 2. `format_balance()` refactoring plan is under-specified and risky

**Where:**
- File: `/home/skytiger/PycharmProjects/FinFocus/app/components/calendar.py`, line 86-102
- Solution: Step 4.7 and Risk table row about `format_balance()`

**Problem:**
The solution acknowledges the need to coordinate `format_balance()` with `format_rub()` but the plan is vague: "format_balance() ostaetsya dlya CSS-klassa, no stroku formiruem cherez format_rub()." This is contradictory -- `format_balance()` currently returns a formatted string WITHOUT the ruble sign (line 95), and callers add the ruble sign themselves in 3+ places (lines 294, 309, 324, 681). The solution proposes making `format_balance()` return `(format_rub(balance), css_class)` which INCLUDES the ruble sign, but then callers like line 681 (`f"{balance_text} rub"`) would produce double ruble signs: "15 000 rub rub".

**Why important:**
Without a clear refactoring strategy, the implementer will either (a) get double ruble signs, or (b) have to independently figure out the correct approach, which defeats the purpose of the architectural solution.

**Recommendation:**
Explicitly define: `format_balance()` should return `(format_rub(balance), css_class)` where `format_rub` already includes the ruble sign. Then update ALL 4 callsites that currently append ruble signs:
- Line 294: `f"+{income_formatted} rub"` -> `f"+{income_formatted}"` or use `format_rub(total_income, show_sign=True)`
- Line 309: `f"-{expense_formatted} rub"` -> similar
- Line 324: `f"{balance_formatted} rub"` -> just `balance_formatted`
- Line 681: `f"{balance_text} rub"` -> just `balance_text`

Or alternatively: keep `format_balance()` returning WITHOUT ruble sign (as now) and only update the internal formatting to use spaces. The solution must pick one and document all callsite changes.

### 3. Missing CSS file: `goals.css` not in blast radius, but `rgba(40, 167, 69)` in `custom.css` not fully catalogued

**Where:**
- File: `/home/skytiger/PycharmProjects/FinFocus/app/assets/custom.css`, lines 28 and 187
- Solution section: "Blast Radius" and Step 2.2

**Problem:**
The solution's Step 2.2 mentions updating `rgba(40,167,69)` references in custom.css but only refers to it vaguely ("rgba(40,167,69) -> rgba(46,204,113)"). The actual custom.css has **3 occurrences** of `rgba(40, 167, 69, ...)`:
- Line 28: sidebar hover (`rgba(40, 167, 69, 0.1)`)
- Line 187: focus ring (`rgba(40, 167, 69, 0.25)`)
- (onboarding.css line 35 also has one)

Additionally, the solution's blast radius lists `custom.css` as having "6 hardcoded #28a745, #1e7e34 etc." but the actual counts are:
- `#28a745`: 1 occurrence (line 5, the variable definition itself)
- `#1e7e34`: 2 occurrences (lines 100, 166)
- `#1c7430`: 1 occurrence (line 101)
- `rgba(40,167,69,...)`: 2 occurrences (lines 28, 187)

The solution overstates "6 hardcoded" in Python dashboard.py (actually 7: lines 147, 212, 369, 378, 433, 471, 489, counting #28a745 + #17a2b8 + #20c997 separately).

**Why important:**
Inaccurate counts lead to missed replacements. If even one `rgba(40,167,69)` is left while the variable changes to `#2ecc71` (which is `rgba(46,204,113)`), the colors will be inconsistent between elements using var() and those with hardcoded rgba.

**Recommendation:**
Provide an exact line-by-line map for each CSS file. Here is the verified data:

**custom.css** (5 changes needed):
- Line 5: `--primary-green: #28a745` -> `--color-primary: #2ecc71`
- Line 28: `rgba(40, 167, 69, 0.1)` -> `rgba(46, 204, 113, 0.1)` or `var(--color-primary)` with opacity
- Line 100: `#1e7e34` -> `var(--color-primary-dark)` or `#27ae60`
- Line 101: `#1c7430` -> related dark shade
- Line 166: `#1e7e34` -> `var(--color-primary-dark)`
- Line 187: `rgba(40, 167, 69, 0.25)` -> `rgba(46, 204, 113, 0.25)`

**calendar.css** (5 lines with `#28a745`, 1 with `#17a2b8`):
- Lines 144, 198, 216, 330, 373: `#28a745`
- Line 385: `#17a2b8`

**onboarding.css** (3 changes):
- Line 12: `#28a745` and `#20c997` in gradient
- Line 34: `#28a745`
- Line 35: `rgba(40, 167, 69, 0.25)`

### 4. Behavioral change risk: `.00` truncation affects string comparison in service layer

**Where:**
- File: `/home/skytiger/PycharmProjects/FinFocus/app/services/wishlist_service.py`, line 317
- Solution: Step 1.2

**Problem:**
The solution correctly identifies that `format_amount(Decimal("15000"))` currently returns `"15 000.00 rub"` and will change to `"15 000 rub"`. It asserts this only affects UI display. However, `wishlist_service.py` calls `format_amount()` inside `to_data()` at line 317, which populates `WishlistItemData` TypedDict's `amount` field. This TypedDict is then serialized to JSON and stored in `dcc.Store`. If any callback or JS code does string matching or comparison on this value, the format change could break it.

While I found no direct string comparison in the current code, this is a data contract change that should be explicitly documented and verified.

**Why important:**
Silent data format changes in serialized data structures can cause subtle bugs that are hard to trace, especially across Python-JS boundaries (the wishlist hover JS reads data from stores).

**Recommendation:**
1. Grep for any string matching/comparison on formatted amount values across Python and JS
2. Verify that `wishlist_hover.js` does not depend on the `.00` format
3. Add this to the test plan: verify wishlist widget + hover still works after format change
4. Document in the solution that `to_data()` output format changes from `"15 000.00 rub"` to `"15 000 rub"`

### 5. Solution lists `dashboard.py` with "9 mest inline $" but actual count is 10

**Where:**
- File: `/home/skytiger/PycharmProjects/FinFocus/app/components/dashboard.py`
- Solution: Inline formatting table

**Problem:**
The solution claims 9 inline `$` formatting spots in dashboard.py. The actual grep shows **10 distinct occurrences**:
1. Line 290: `f"${metrics['total_balance']:,.2f}"`
2. Line 291: `f"${metrics['period_income']:,.2f}"`
3. Line 292: `f"${metrics['period_expense']:,.2f}"`
4. Line 295: `f"${metrics['savings_current']:,.2f}"`
5. Line 298: `f"${metrics['savings_target']:,.2f}"`
6. Line 301: `"$0.00"` (hardcoded string for "No goals" case)
7. Line 476: `f"${metrics['period_income']:,.0f}"`
8. Line 494: `f"${metrics['period_expense']:,.0f}"`
9. Line 552: `f"+${tx['amount']:,.2f}"`
10. Line 555: `f"-${tx['amount']:,.2f}"`
11. Line 558: `f"${tx['amount']:,.2f}"`

That is actually **11** spots (including `"$0.00"` at line 301). The solution also does not mention `"$0.00"` (line 301) which is a hardcoded fallback string that needs updating to `"0 rub"`.

**Why important:**
Missing even one `$` sign in the UI breaks the visual consistency requirement and is immediately noticeable to users.

**Recommendation:**
Add line 301 (`savings_value = "$0.00"`) to the replacement list. Update the count to 11 (or 10 if the `$0.00` is counted separately).

### 6. `batch-1.md` Zadacha 3 lists 8 component files for format_rub migration, but solution only addresses 3

**Where:**
- File: `/home/skytiger/PycharmProjects/FinFocus/.reports/epics/epic-05-ui/batch-1.md`, lines 77-108 (Zadacha 3)
- Solution: Steps 3-5 and Blast Radius section

**Problem:**
`batch-1.md` Zadacha 3 explicitly lists 8 components that need `format_rub()` migration:
1. Dashboard -- addressed (Step 3)
2. Calendar -- addressed (Step 4)
3. Goals -- addressed via alias (Step 1.2)
4. Transactions -- addressed via alias (Step 1.2)
5. Transaction Modals -- mentioned in blast radius as "no format calls"
6. Wishlist -- addressed via alias
7. Onboarding Wizard -- mentioned as "no inline formatting"
8. Analytics -- addressed (Step 5)

The solution correctly handles this through the alias strategy, but the `batch-1.md` spec says "Zadat' 3: Obnovit' vse UI-komponenty na format_rub()" which implies direct replacement, not aliasing. There is a **scope discrepancy**: the spec expects editing 8 files, the solution only edits 3 (dashboard, calendar, analytics) and relies on the alias for the other 5.

**Why important:**
If the acceptance review compares the spec's file list against actual changes, the alias approach might be questioned. The solution should explicitly address this discrepancy and justify why aliasing is sufficient for goals/transactions/wishlist.

**Recommendation:**
Add a paragraph explicitly stating: "Zadacha 3 lists 8 components, but only 3 require direct changes because goals.py, transactions.py, calendar_wishlist.py, wishlist_service.py, and onboarding_wizard.py all call `format_amount()` which is aliased to `format_rub()`. The behavioral change (`.00` truncation) propagates automatically through the alias."

---

## Minor Issues (Optional)

### 7. RTM row #16: `.kpi-title` font-size discrepancy (12px in solution vs 16px in spec)

The solution's Step 2.3 defines `.kpi-title` as `font-size: 12px` but the spec (`dashboard_ui_spec.md` section 3, line 139) says "Zagolovok kartochki: 16px, medium". The solution's RTM row #16 notes this discrepancy parenthetically but does not resolve it. The `batch-1.md` says "16px zagolovok" in Zadacha 6.

**Recommendation:** Use 16px for `.kpi-title` as the spec states. The 12px applies to `.kpi-subtitle`.

### 8. Missing `--color-separator: #ecf0f1` usage in CSS

The solution adds `--color-separator` as a CSS variable but no CSS rule uses it. While this is technically just declaring a variable for future use, it adds dead code.

**Recommendation:** Either use it in `.table td` border or document it as "available for batch 5.3".

### 9. English labels still in solution for consistency check

The solution correctly proposes Russian labels ("Balans", "Dokhody", "Raskhody", "Nakopleniya") in Step 3.3, but Step 3.4 uses mixed Russian/English: "Russkie label: 'Dokhody' / 'Raskhody' vmesto 'Income' / 'Expense'". The Period Switcher labels ("Month"/"Year" in `period-switcher` RadioItems at dashboard.py line 78-79) are not mentioned in the solution.

**Recommendation:** Add Step 3.8 or extend Step 3.3 to update the `period-switcher` labels from "Month"/"Year" to "Mesyats"/"God" if the localization scope includes the switcher.

### 10. `create_metric_card()` not explicitly marked for deprecation or removal

The solution proposes creating `_build_kpi_card()` but doesn't say what happens to the existing `create_metric_card()` function (lines 134-198 of dashboard.py). If `_build_kpi_card()` replaces it, `create_metric_card()` should be removed or deprecated.

**Recommendation:** Explicitly state: "Remove `create_metric_card()` after replacing all calls with `_build_kpi_card()` in `build_overview_cards()`."

---

## Detailed Analysis by Aspect

### Aspect 1: Requirements Compliance

**Status:** Partially compliant

**Details:**
- FR-1 (format_rub): Fully covered (Step 1)
- FR-2 (replace all inline): Partially covered -- counts are inaccurate, some spots may be missed
- FR-3 (KPI cards redesign): Covered (Step 3)
- FR-4 (Reconciliation button): Covered (redirect strategy)
- FR-5 (Hide AI/Exchange): Covered (Step 3.7)
- FR-6 (CSS variables): Covered but counts inaccurate (Step 2)
- FR-7 (Typography classes): Covered but .kpi-title size discrepancy (Step 2.3)

**RTM Check:**
- RTM exists with 20 rows -- good coverage
- Types are specified (Must, Info)
- Visual requirements reference CSS properties
- UX text references missing for Russian label translations
- Row #16 has internal inconsistency (12px vs 16px)

### Aspect 2: Architectural Quality

**Status:** Good

**Details:**
- SRP: `format_rub()` has single responsibility (formatting). Good.
- OCP: Alias pattern allows extension without modification. Good.
- LSP: `format_amount()` as alias preserves the contract (same return type). Good.
- ISP: Not applicable (no interfaces).
- DIP: `format_rub()` is a pure function with no dependencies. Excellent.
- Coupling: Low -- the alias strategy minimizes coupling between the change and existing code.
- Cohesion: High -- all formatting logic stays in `formatters.py`.

**Issues:**
- `format_balance()` in calendar.py creates a coupling issue: it duplicates formatting logic that should delegate to `format_rub()`. The refactoring plan is unclear.

### Aspect 3: Performance

**Status:** Good

**Details:**
- `format_rub()` is O(n) where n is digit count -- negligible overhead.
- No new database queries, no new API calls.
- No N+1 issues.
- The redirect to `/calendar?open_recon=1` causes a page navigation, which is slightly slower than opening a modal in-place, but acceptable for this use case.

### Aspect 4: Error Handling

**Status:** Good

**Details:**
- `format_rub()` accepts Decimal/float/int with type union -- covers main input types.
- Solution mentions adding a guard for None/invalid inputs returning "0 rub" -- good defensive approach.
- No new callbacks that could fail silently.

**Issues:**
- The solution does not specify what happens if `format_rub()` receives a string (e.g., from broken serialization). Should it raise TypeError or return "0 rub"?

### Aspect 5: Security

**Status:** Good (N/A for most checks)

**Details:**
- No user input handling changes.
- No SQL queries modified.
- No secrets management changes.
- The `format_rub()` function processes numeric data only -- no injection risk.

### Aspect 6: Implementation Complexity

**Status:** Good

**Details:**
- Realistic scope: 8 files modified + 1 new test file.
- No new dependencies required.
- Step ordering is correct (format_rub first, then CSS, then components).
- Estimated ~300 lines changed -- reasonable for a UI foundation batch.

**Issues:**
- The `format_balance()` refactoring in calendar.py is the highest-risk part and needs clearer specification.
- Total of 12 inline spots in calendar.py (not 10 as claimed) increases implementation effort slightly.

### Aspect 7: Alternative Approaches

**Status:** Good

**Details:**
- The alias approach was correctly chosen over full replacement.
- The redirect approach for reconciliation was correctly chosen over modal extraction.
- Alternative `always_cents` parameter was considered and rejected with justification.

**Not considered:**
- Using Python `locale` module for formatting (would provide automatic grouping but harder to control exact output format).
- Using a `Formatter` class instead of a function (overkill for this use case).

---

## Questions for the Architect

1. **`format_balance()` in calendar.py**: Should it return `format_rub(balance)` (WITH ruble sign) or continue returning WITHOUT ruble sign? This affects 4+ callsites and the double-ruble-sign risk needs explicit resolution.

2. **Period Switcher labels**: Should "Month"/"Year" be translated to Russian ("Mesyats"/"God") in this batch, or is that deferred to batch 5.3?

3. **`.kpi-title` font-size**: The spec says 16px but the solution implements 12px. Which is correct?

4. **Plotly tooltip format**: The solution defers Plotly hovertemplate formatting (which still uses comma separators). Is this acceptable for MVP, or should we use `customdata` + custom hovertemplate to show space-separated thousands?

5. **`$0.00` hardcoded fallback** at dashboard.py line 301: Should this become `"0 rub"` or the more descriptive text like "Net tselei"?

---

## Recommendations for Next Iteration

### Required (for 5/5):
1. **Fix inline formatting counts**: Provide exact line-by-line maps for calendar.py (12 spots, not 10) and dashboard.py (11 spots, not 9). Include `$0.00` fallback and `adjustment.amount` in reconciliation callbacks.
2. **Resolve `format_balance()` refactoring strategy**: Explicitly define whether it returns with or without ruble sign, and list all 4 callsite changes needed.
3. **Resolve `.kpi-title` font-size**: Pick 16px per spec or 12px per solution, and document the decision.

### Desirable:
4. **Add explicit scope discrepancy note** for batch-1.md Zadacha 3 (8 files listed, 3 edited, 5 via alias).
5. **Document `to_data()` format change** in wishlist_service.py and verify JS hover compatibility.
6. **Add exact rgba replacement map** for custom.css and onboarding.css.

### Optional:
7. **Consider adding `always_cents: bool` parameter** to `format_rub()` for future use cases where precision matters (e.g., CSV export, financial reports).
8. **Address Period Switcher Russian labels** if in scope.
===CRITIQUE_END===

===METADATA===
RATING: 4
VERDICT: MINOR_FIXES
BLOCKERS: 1
IMPORTANT: 5
MINOR: 4
===END_METADATA===
