# Story 9.18: Take-Profit Threshold Formula Fix — Edge-Relative TP When Baseline Exceeds Edge

Status: done

## Story

As an **operator**,
I want **the take-profit threshold to produce a meaningful profit target even when entry costs (spread + fees) dominate the expected edge**,
so that **positions are not exited at breakeven ($0.00 TP) when they have positive expected profit**.

## Acceptance Criteria

1. **TP never $0.00 when position has positive expected edge**: When `entryCostBaseline` is large enough to make the journey formula negative, a fallback produces `max(0, scaledInitialEdge × TP_RATIO)` — a real profit target. [Source: sprint-change-proposal-2026-03-14.md#Story-D AC1]

2. **Journey formula used when positive**: Existing positions where the journey formula yields a positive value see zero behavior change. [Source: sprint-change-proposal-2026-03-14.md#Story-D AC2]

3. **Fallback activates only when `journeyTp ≤ 0`**: The edge-relative formula is strictly a fallback — it never overrides a healthy journey TP. [Source: sprint-change-proposal-2026-03-14.md#Story-D AC3]

4. **TP never below $0**: `max(0, ...)` guard remains as final safety net on the fallback path. [Source: sprint-change-proposal-2026-03-14.md#Story-D AC4]

5. **TP proximity in [0, 1]**: No NaN, negative, or division by zero in `takeProfitProximity`. [Source: sprint-change-proposal-2026-03-14.md#Story-D AC5]

6. **SL formula and proximity unaffected**: Stop-loss threshold and its proximity calculation are not modified. [Source: sprint-change-proposal-2026-03-14.md#Story-D AC6]

7. **Shared formula**: Both `ThresholdEvaluatorService` (hot path) and `PositionEnrichmentService` (dashboard) call the same `computeTakeProfitThreshold()` function — no duplicate logic. [Source: codebase investigation — formula duplicated at threshold-evaluator.service.ts:164-173 and position-enrichment.service.ts:264-272; user confirmation 2026-03-14]

8. **`exit-thresholds.ts` comment updated**: JSDoc documents the fallback behavior for high-fee/small-size positions. [Source: sprint-change-proposal-2026-03-14.md#Story-D AC7]

9. **Tests**: Normal journey case (no behavior change), high-fee fallback (the bug case), boundary (`|baseline| = 4 × edge`, journeyTp exactly 0), very small edge, legacy positions (baseline = 0), SL unchanged. Shared function has its own unit tests. All existing tests pass. `pnpm lint` clean. [Source: sprint-change-proposal-2026-03-14.md#Story-D AC8; baseline: 2069 passed, 2 todo]

## Tasks / Subtasks

**Execution order: 1 → 2 → 3 → 4 → 5**

- [x] **Task 1: Add shared `computeTakeProfitThreshold()` to `exit-thresholds.ts`** (AC: #1, #2, #3, #4, #7, #8)
  - [x] 1.1 Add a pure function `computeTakeProfitThreshold(entryCostBaseline: Decimal, scaledInitialEdge: Decimal): Decimal` to `src/common/constants/exit-thresholds.ts`:
    ```typescript
    import Decimal from 'decimal.js';

    /**
     * Compute the take-profit threshold with edge-relative fallback.
     * @param entryCostBaseline MtM deficit at entry (≤ 0). May be recomputed for
     *   residual size in EXIT_PARTIAL (callers pass as `thresholdBaseline`).
     * @param scaledInitialEdge initialEdge × legSize (> 0 for real positions).
     */
    export function computeTakeProfitThreshold(
      entryCostBaseline: Decimal,
      scaledInitialEdge: Decimal,
    ): Decimal {
      // Journey-based TP (6.5.5j): 80% of the path from baseline to convergence
      const journeyTp = entryCostBaseline.plus(
        scaledInitialEdge
          .minus(entryCostBaseline)
          .mul(new Decimal(TP_RATIO.toString())),
      );

      if (journeyTp.gt(0)) {
        return journeyTp;
      }

      // Fallback (9-18): edge-relative TP when baseline dominates edge
      return Decimal.max(new Decimal(0), scaledInitialEdge.mul(new Decimal(TP_RATIO.toString())));
    }
    ```
  - [x] 1.2 Update the `TP_RATIO` JSDoc (line 12) to document the fallback:
    ```typescript
    /**
     * Take-profit ratio (80% of journey or edge).
     *
     * Normal case: TP = entryCostBaseline + (scaledInitialEdge - entryCostBaseline) × TP_RATIO
     * Fallback (when journey TP ≤ 0, i.e. |baseline| > 4 × edge): TP = max(0, scaledInitialEdge × TP_RATIO)
     */
    export const TP_RATIO = 0.8;
    ```

- [x] **Task 2: Replace inline formula in both services** (AC: #7)
  - [x] 2.1 In `src/modules/exit-management/threshold-evaluator.service.ts` (lines 164-173), replace the inline `Decimal.max(...)` block with:
    ```typescript
    // Priority 2: Take-profit — journey-based with edge-relative fallback (6.5.5j, 9-18)
    const takeProfitThreshold = computeTakeProfitThreshold(
      entryCostBaseline,
      scaledInitialEdge,
    );
    ```
    Update the import from `exit-thresholds` to include `computeTakeProfitThreshold`. (Note: this file uses bare imports without `.js` extension.)
  - [x] 2.2 In `src/dashboard/position-enrichment.service.ts` (lines 264-272), replace the inline `Decimal.max(...)` block with:
    ```typescript
    // Journey-based TP with edge-relative fallback (6.5.5j, 9-18)
    const takeProfitThreshold = computeTakeProfitThreshold(
      thresholdBaseline,
      scaledInitialEdge,
    );
    ```
    Update the import from `exit-thresholds.js` to include `computeTakeProfitThreshold`. (Note: this file uses `.js` extension in imports.)

- [x] **Task 3: Unit test the shared function** (AC: #1, #2, #3, #4, #9)
  - [x] 3.1 Create `src/common/constants/exit-thresholds.spec.ts` with tests for `computeTakeProfitThreshold()`:
    - **Normal journey (AC #2):** `baseline = 0, edge = $3.00` → returns `$2.40` (0.80 × $3.00). Journey formula, no fallback.
    - **High-fee fallback — the bug case (AC #1, #3):** `baseline = -$8.05, edge = $1.13` → journeyTp = -$0.706 ≤ 0 → fallback `$1.13 × 0.80 = $0.904`. NOT $0.00.
    - **Extreme spread floor (AC #1, #4):** `baseline = -$20, edge = $1.00` → journeyTp = -$3.20 ≤ 0 → fallback `$1.00 × 0.80 = $0.80`.
    - **Boundary — journey exactly 0 (AC #3):** `baseline = -4 × edge`. E.g. `baseline = -$4, edge = $1` → `journeyTp = -4 + (1+4) × 0.80 = -4 + 4 = 0 ≤ 0` → fallback `$0.80`.
    - **Moderate spread — journey positive (AC #2):** `baseline = -$1, edge = $3` → `journeyTp = -1 + (3+1) × 0.80 = -1 + 3.20 = $2.20 > 0` → returns $2.20. No fallback.
    - **Very small edge (AC #4):** `baseline = -$0.50, edge = $0.01` → journeyTp ≤ 0 → fallback `$0.01 × 0.80 = $0.008`.
    - **Zero edge (AC #4):** `baseline = -$5, edge = $0` → journeyTp = -$5 ≤ 0 → fallback `max(0, 0) = $0.00`. Correct — no expected profit.
    - **Legacy position (AC #2):** `baseline = $0, edge = $2` → `journeyTp = 0 + (2-0) × 0.80 = $1.60 > 0`. No change from pre-fix behavior.
    - **Extreme ratio (AC #4):** `baseline = -$1000, edge = $1` → journeyTp ≤ 0 → fallback `$1 × 0.80 = $0.80`. Verifies no precision loss at extreme baseline/edge ratios.

- [x] **Task 4: Update service spec files** (AC: #5, #6, #9)
  - [x] 4.1 In `src/modules/exit-management/threshold-evaluator.service.spec.ts`, add a test: **`'should use edge-relative TP fallback when baseline dominates edge'`** — reproduce the actual bug case (`baseline = -$8.05, edge = $1.13`). Verify TP does NOT fire at currentPnl = $0.00 but DOES fire at currentPnl ≥ $0.904.
  - [x] 4.2 In `src/modules/exit-management/threshold-evaluator.service.spec.ts`, verify existing TP tests still pass unchanged (AC #2, #6). The 6-5-5j tests (AC4-AC6 at lines 387-593) should be green with no modifications.
  - [x] 4.3 In `src/dashboard/position-enrichment.service.spec.ts`, add a test: **`'should produce positive TP and valid proximity when baseline dominates edge'`** — same bug case. Verify `projectedTpPnl > "0"`. Explicitly assert proximity bounds: `parseFloat(takeProfitProximity) >= 0`, `parseFloat(takeProfitProximity) <= 1`, and `!isNaN(parseFloat(takeProfitProximity))`.

- [x] **Task 5: Final validation** (AC: #9)
  - [x] 5.1 Run `pnpm test` — 2081 passed (2069 + 12 new), 2 todo
  - [x] 5.2 Run `pnpm lint` — clean
  - [x] 5.3 Run `pnpm build` — no type errors

## Dev Notes

### Root Cause Analysis

The journey-based TP formula (introduced in Story 6-5-5j) computes:

```
takeProfitThreshold = max(0, entryCostBaseline + (scaledInitialEdge - entryCostBaseline) × 0.80)
```

Expanding: `max(0, 0.20 × entryCostBaseline + 0.80 × scaledInitialEdge)`.

The inner expression goes negative when `|entryCostBaseline| > 4 × scaledInitialEdge` (solving `0.20 × baseline + 0.80 × edge = 0`). The `max(0, ...)` clamps the result to $0.00, which means TP fires at breakeven — not at any actual profit. This happens with high-spread, small-position trades.

**Observed on a real position:**
- `thresholdBaseline = -$8.05` (spread $7.13 + exit fees $0.93)
- `scaledInitialEdge = $1.13` (edge 0.02536 × size 44.55)
- `journeyTp = -8.05 + (1.13 + 8.05) × 0.80 = -8.05 + 7.344 = -0.706`
- Old result: `max(0, -0.706) = $0.00` — TP fires at breakeven
- New result: fallback `max(0, 1.13 × 0.80) = $0.904` — TP fires at ~80% of expected profit

[Source: sprint-change-proposal-2026-03-14.md#Story-D; threshold-evaluator.service.ts:164-173; position-enrichment.service.ts:264-272]

### Fix Design

**Shared function** in `exit-thresholds.ts`:
1. Compute `journeyTp` using existing formula (no `max(0, ...)` wrapper yet)
2. If `journeyTp > 0`: return it — normal behavior, no change for any existing position
3. If `journeyTp ≤ 0`: return `max(0, scaledInitialEdge × TP_RATIO)` — edge-relative fallback

The fallback expresses TP as "capture 80% of the expected edge profit", independent of the MtM baseline. This is safe because:
- P&L at TP already accounts for exit fees (MtM basis)
- `scaledInitialEdge > 0` for all real positions (we only enter with positive expected edge)
- `max(0, ...)` protects against degenerate cases (zero/negative edge)

[Source: sprint-change-proposal-2026-03-14.md#Story-D lines 229-240]

### TP Proximity Impact

In `position-enrichment.service.ts` (lines 285-294):

```typescript
const tpDenom = takeProfitThreshold.minus(thresholdBaseline);
```

After fix: `tpDenom = 0.904 - (-8.05) = 8.954` — positive. The `isZero()` guard handles the degenerate case where `scaledInitialEdge ≤ 0` produces `TP = 0` and `tpDenom = 0 - baseline` which is positive when baseline < 0 (or zero when baseline = 0, caught by guard). No division issues.

[Source: sprint-change-proposal-2026-03-14.md#Story-D lines 242-245; position-enrichment.service.ts:285-294]

### Behavior Change Matrix

| Scenario | Baseline | Edge | Old TP | New TP | Change |
|----------|----------|------|--------|--------|--------|
| Legacy (no baseline) | $0 | $3.00 | $2.40 | $2.40 | None |
| Moderate spread | -$1.00 | $3.00 | $2.20 | $2.20 | None (journey > 0) |
| Real position (bug) | -$8.05 | $1.13 | $0.00 | $0.90 | FIXED |
| Extreme spread | -$20 | $1.00 | $0.00 | $0.80 | FIXED |
| Boundary (|b|=4×e) | -$4.00 | $1.00 | $0.00 | $0.80 | FIXED |

[Source: sprint-change-proposal-2026-03-14.md#Story-D; Story 6-5-5j behavior change matrix]

### Scope Boundaries

- **No schema changes**: No new DB columns, no migration
- **No new events**: No event class changes, no new event types
- **No interface changes**: `ThresholdEvalInput`, `ThresholdEvalResult`, `EnrichmentResult` unchanged
- **No dashboard frontend changes**: Dashboard displays `projectedTpPnl` from the enrichment service — it will automatically show the corrected TP value
- **SL formula untouched**: Stop-loss threshold (`entryCostBaseline + scaledInitialEdge × SL_MULTIPLIER`) is not modified

### Project Structure Notes

**Modified files** (3):
- `src/common/constants/exit-thresholds.ts` — add `computeTakeProfitThreshold()`, update JSDoc [Source: AC #1, #7, #8]
- `src/modules/exit-management/threshold-evaluator.service.ts` — replace inline TP formula with shared function call [Source: AC #7]
- `src/dashboard/position-enrichment.service.ts` — replace inline TP formula with shared function call [Source: AC #7]

**New files** (1):
- `src/common/constants/exit-thresholds.spec.ts` — unit tests for `computeTakeProfitThreshold()` [Source: AC #9]

**Modified test files** (2):
- `src/modules/exit-management/threshold-evaluator.service.spec.ts` — add fallback integration test [Source: AC #9]
- `src/dashboard/position-enrichment.service.spec.ts` — add fallback + proximity test [Source: AC #9]

**Verified (no changes):**
- `src/common/utils/financial-math.ts` — `computeEntryCostBaseline()` unchanged [Source: codebase investigation]
- Existing 6-5-5j test cases — must pass without modification [Source: AC #2]

### References

- [Source: sprint-change-proposal-2026-03-14.md#Story-D] — Primary requirements, math verification, acceptance criteria
- [Source: CLAUDE.md] — Post-edit workflow, naming conventions, financial math rules (decimal.js)
- [Source: exit-thresholds.ts:9-13] — `SL_MULTIPLIER`, `TP_RATIO` constants
- [Source: threshold-evaluator.service.ts:164-173] — Current inline TP formula (hot path)
- [Source: position-enrichment.service.ts:264-272] — Current inline TP formula (dashboard)
- [Source: position-enrichment.service.ts:285-294] — TP proximity calculation
- [Source: financial-math.ts:131-202] — `computeEntryCostBaseline()` — feeds into TP calculation
- [Source: threshold-evaluator.service.spec.ts:387-593] — Existing 6-5-5j TP test cases
- [Source: Story 6-5-5j] — Introduced journey-based TP formula with `max(0, ...)` floor
- [Source: Story 6-5-5i] — Introduced `entryCostBaseline` and entry close price fields

### Previous Story Intelligence

**From Story 9-17** (stale-apr-display-fix):
- Test count baseline: 2069 passed, 2 todo.
- Pattern: when fixing a consistency issue, audit all write sites (applied here: both services share one function now).
- Code review found duplicate test and inconsistent string conversion — watch for these.

**From Story 6-5-5j** (take-profit-negative-threshold-fix):
- This story introduced the journey-based formula we are now extending with a fallback.
- The `Decimal.max(0, ...)` floor was the original mitigation — it prevented negative TP but created $0.00 TP for high-spread scenarios.
- The story has 6 dedicated TP test cases (lines 387-593 in the evaluator spec). All must remain green.
- Files modified: `threshold-evaluator.service.ts`, `position-enrichment.service.ts`, and both their specs.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no blockers encountered.

### Completion Notes List

- Implemented shared `computeTakeProfitThreshold()` in `exit-thresholds.ts` with journey-based formula + edge-relative fallback when `journeyTp ≤ 0`.
- Replaced inline TP formula in both `ThresholdEvaluatorService` and `PositionEnrichmentService` with shared function call.
- Two existing enrichment service tests required expected-value updates (6.5.5j AC5 extreme spread, 6.5.5i proximity) because the old floor at `$0.00` is now replaced with a positive fallback — this is the intended behavior change.
- All 6 existing 6.5.5j tests in `threshold-evaluator.service.spec.ts` (lines 387-593) pass without modification — the evaluator tests that used the floor happened to be testing for `triggered: false` or scenarios where journey TP was positive, so the behavior didn't change.
- Test count: 2069 → 2081 (+12 new tests: 9 shared function + 2 evaluator integration + 1 enrichment integration).
- Lad MCP code review: both reviewers APPROVED. No code changes required.
- Code review (Amelia, 2026-03-14): fixed 1 MEDIUM (hoisted `new Decimal(TP_RATIO.toString())` and `new Decimal(0)` to module-level constants `TP_RATIO_DECIMAL`/`DECIMAL_ZERO` to avoid repeated hot-path allocations). 2 LOW noted (dead `TP_RATIO` export, no negative-edge defensive test).

### File List

**Modified (3):**
- `src/common/constants/exit-thresholds.ts` — added `computeTakeProfitThreshold()`, updated `TP_RATIO` JSDoc, added `decimal.js` import
- `src/modules/exit-management/threshold-evaluator.service.ts` — replaced inline TP formula with shared function call, updated import
- `src/dashboard/position-enrichment.service.ts` — replaced inline TP formula with shared function call, updated import

**Created (1):**
- `src/common/constants/exit-thresholds.spec.ts` — 9 unit tests for `computeTakeProfitThreshold()`

**Modified test files (2):**
- `src/modules/exit-management/threshold-evaluator.service.spec.ts` — +2 tests (fallback no-trigger at breakeven, fallback trigger above threshold)
- `src/dashboard/position-enrichment.service.spec.ts` — +1 test (positive TP + valid proximity when baseline dominates edge), updated 2 existing tests (extreme spread proximity values)
