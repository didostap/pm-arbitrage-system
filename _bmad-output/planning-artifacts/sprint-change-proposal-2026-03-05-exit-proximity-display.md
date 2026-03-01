# Sprint Change Proposal — Exit Proximity Display Formula Fix

**Date:** 2026-03-05
**Triggered by:** Operator dashboard showing TP=100%, SL=63% on a just-opened position
**Scope:** Minor — Direct implementation by development team
**Status:** Approved

---

## 1. Issue Summary

The exit proximity formulas in `position-enrichment.service.ts:214-231` produce incorrect TP/SL percentages for the operator dashboard. The formulas measure "how far is P&L from zero relative to the threshold" but after Story 6.5.5i offset both thresholds by `entryCostBaseline`, the correct measurement is "how far has P&L moved from the baseline toward the threshold."

This is a **display-only bug** — the actual exit trigger logic in `threshold-evaluator.service.ts` works correctly (it compares `currentPnl` against shifted thresholds directly). Exits fire at the correct P&L levels.

**However, it is operationally significant:** the operator uses proximity percentages to triage which positions need attention. Every just-opened position currently appears to be at take-profit (100%), which is misleading.

**Evidence from live paper position (2026-03-05):**

| Metric | Value |
|--------|-------|
| Position | "Will Republicans lose the H..." (66 contracts) |
| Entry prices | K: 0.21 (sell), P: 0.17 (buy) |
| Current prices | K: 0.26, P: 0.15 |
| entryCostBaseline | -5.707 |
| takeProfitThreshold | -4.389 (negative because baseline overwhelms TP offset) |
| stopLossThreshold | -9.003 |
| currentPnl | -5.71 |
| **TP displayed** | **100%** (should be ~0%) |
| **SL displayed** | **63%** (should be ~0%) |

**Root cause trace:**

```
TP proximity = clamp(currentPnl / takeProfitThreshold, 0, 1)
             = clamp(-5.71 / -4.389, 0, 1)       // two negatives = positive
             = clamp(1.30, 0, 1) = 1.0            // clamped to 100%

SL proximity = clamp(|currentPnl / stopLossThreshold|, 0, 1)
             = clamp(|-5.71 / -9.003|, 0, 1)      // measures from zero, not baseline
             = clamp(0.634, 0, 1) = 0.634          // 63% instead of ~0%
```

**Correct formulas (baseline-relative):**

```
TP proximity = clamp((currentPnl - baseline) / (tpThreshold - baseline), 0, 1)
             = clamp((-5.71 - (-5.71)) / (-4.39 - (-5.71)), 0, 1)
             = clamp(0 / 1.32, 0, 1) = 0.0        // 0% -- correct for just-opened

SL proximity = clamp((baseline - currentPnl) / (baseline - slThreshold), 0, 1)
             = clamp((-5.71 - (-5.71)) / (-5.71 - (-9.00)), 0, 1)
             = clamp(0 / 3.30, 0, 1) = 0.0        // 0% -- correct for just-opened
```

---

## 2. Impact Analysis

### Epic Impact

| Epic | Status | Impact |
|------|--------|--------|
| **7** (Dashboard) | in-progress | **Direct** — New story 7.5 patches proximity formulas in `position-enrichment.service.ts` |
| **6.5** (Paper Validation) | in-progress | None — threshold evaluator is correct, exits fire properly |
| **10** (Model-Driven Exits) | backlog | None — replaces fixed thresholds entirely |
| All others | -- | None |

### Artifact Impact

| Artifact | Change Needed |
|----------|--------------|
| **Sprint status YAML** | New story entry `7-5-exit-proximity-display-fix` in Epic 7 |
| **Epics document** | New Story 7.5 definition |
| **position-enrichment.service.ts** | Fix proximity formulas (lines 214-231) |
| **position-enrichment.service.spec.ts** | Update test assertions for baseline-relative formulas |
| PRD | None |
| Architecture | None |
| UI/UX | None — frontend renders whatever backend sends |

### Technical Impact

- **No schema changes** — all required data already available (`entryCostBaseline` is computed in the same function)
- **No new dependencies** — fix is within the existing `enrich()` method
- **No API contract changes** — `ExitProximityDto` shape unchanged (still `{ stopLoss: string, takeProfit: string }`)
- **No frontend changes** — `ExitProximityIndicator` renders the decimal values as-is
- **Exit triggers unaffected** — `threshold-evaluator.service.ts` compares P&L against thresholds directly

---

## 3. Recommended Approach

**Direct Adjustment** — single story (7.5) within Epic 7.

### What the fix does

Replace the two proximity ratio formulas in `position-enrichment.service.ts:214-231` to measure progress from `entryCostBaseline` toward the threshold, instead of from zero toward the threshold.

### Why this approach

- The `entryCostBaseline` variable is already computed on line 186 of the same function — no new data needed
- Two-line formula change + division-by-zero guard
- The threshold evaluator (actual exit logic) is not touched
- Forward-compatible with Epic 10

---

## 4. Detailed Change Proposals

### 4.1 New Story: 7.5 — Exit Proximity Display Fix

**As an operator,**
I want exit proximity percentages to accurately reflect how close a position is to triggering TP/SL,
so that I can reliably triage positions from the dashboard.

**Acceptance Criteria:**

**AC1: Baseline-Relative Proximity**

**Given** a position with `entryCostBaseline` computed from entry close prices and fees
**When** `PositionEnrichmentService.enrich()` calculates exit proximity
**Then** stop-loss proximity = `clamp((baseline - currentPnl) / (baseline - slThreshold), 0, 1)`
**And** take-profit proximity = `clamp((currentPnl - baseline) / (tpThreshold - baseline), 0, 1)`
**And** a just-opened position (where currentPnl ~ baseline) shows both TP and SL near 0%

**AC2: Division-by-Zero Guard**

**Given** a degenerate case where `entryCostBaseline == threshold` (zero-edge position)
**When** proximity is calculated
**Then** the result is 0 (not NaN or Infinity)

**AC3: Legacy Position Behavior**

**Given** a position with null entry close prices (pre-6.5.5i)
**When** `entryCostBaseline` defaults to 0
**Then** proximity formulas still produce correct results

**Implementation note:** When `entryCostBaseline = 0`, the corrected formulas algebraically reduce to the original ratios:
- SL: `(0 - currentPnl) / (0 - slThreshold)` = `currentPnl / slThreshold` (same sign behavior as original `.abs()` variant since both are negative)
- TP: `(currentPnl - 0) / (tpThreshold - 0)` = `currentPnl / tpThreshold` (identical to original)

This means pre-6.5.5i positions produce exactly the same proximity values as before. The dev agent should verify this equivalence in tests, not just that "it works."

**AC4: Tests**

**Given** the position enrichment test suite
**When** tests run
**Then** scenarios cover:
- Just-opened position: both SL and TP proximity near 0%
- Position with P&L halfway to SL: SL proximity ~50%, TP ~0%
- Position with P&L at TP threshold: TP proximity = 100%
- Legacy position (null entry close prices, baseline = 0): correct ratios
- Division-by-zero edge case: proximity = 0
- All existing tests continue to pass
**And** `pnpm lint` reports zero errors

**Tasks / Subtasks:**

- [ ] Task 1: Fix proximity formulas in `position-enrichment.service.ts` (AC: #1, #2)
  - [ ] 1.1 Replace SL proximity formula (lines 214-222) with baseline-relative version
  - [ ] 1.2 Replace TP proximity formula (lines 223-231) with baseline-relative version
  - [ ] 1.3 Add division-by-zero guard: if `threshold == baseline`, proximity = 0

- [ ] Task 2: Update tests in `position-enrichment.service.spec.ts` (AC: #3, #4)
  - [ ] 2.1 Add test: just-opened position with current prices === entry close prices → both proximities exactly 0.0 (not "near 0" — use identical prices to make it mathematically exact)
  - [ ] 2.2 Add test: just-opened position with small price movement between entry and first enrichment → both proximities small but nonzero (validates formula works with realistic drift, avoids brittle assertions)
  - [ ] 2.3 Add test: P&L halfway to SL → SL ~50%, TP ~0%
  - [ ] 2.4 Add test: P&L at TP threshold → TP = 100%
  - [ ] 2.5 Update existing proximity test assertions to match new formula
  - [ ] 2.6 Verify legacy position (baseline = 0) produces identical values to the original formula — explicitly assert algebraic equivalence, not just "it works"

- [ ] Task 3: Run full test suite and lint (AC: #4)
  - [ ] 3.1 `pnpm test` — all tests pass
  - [ ] 3.2 `pnpm lint` — zero errors

**Sequencing:** After 7.4. No dependencies on other in-progress stories. Does not gate anything.

**Scope Guard:**

This story is strictly scoped to:
1. Fix two proximity formulas in `position-enrichment.service.ts`
2. Update tests

Do NOT:
- Modify `threshold-evaluator.service.ts` (exit triggers are correct)
- Modify `financial-math.ts` (baseline computation is correct)
- Modify any frontend code (renders backend values as-is)
- Modify the Prisma schema
- Change the API response shape
- Add new events or error codes

---

### 4.2 Sprint Status Update

Add to Epic 7 section:
```yaml
7-5-exit-proximity-display-fix: backlog
```

---

## 5. Implementation Handoff

**Scope classification:** Minor — direct implementation by development agent.

| Role | Action |
|------|--------|
| **SM** | Finalize this proposal, update sprint status and epics doc upon approval |
| **Dev agent** | Implement Story 7.5 (formula fix + tests) |
| **Operator** | Verify paper positions show ~0% proximity at entry on the dashboard |

**Success criteria:**
- Just-opened paper positions show both SL and TP proximity near 0%
- Positions with actual P&L movement show proportional proximity values
- All tests pass, lint clean
- No changes to exit trigger behavior
