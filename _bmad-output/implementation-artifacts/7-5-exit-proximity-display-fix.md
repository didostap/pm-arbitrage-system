# Story 7.5: Exit Proximity Display Fix

Status: done

## Story

As an operator,
I want exit proximity percentages to accurately reflect how close a position is to triggering TP/SL,
so that I can reliably triage positions from the dashboard.

## Acceptance Criteria

### AC1 — Baseline-Relative Proximity

- **Given** a position with `entryCostBaseline` computed from entry close prices and fees
- **When** `PositionEnrichmentService.enrich()` calculates exit proximity
- **Then** stop-loss proximity = `clamp((baseline - currentPnl) / (baseline - slThreshold), 0, 1)`
- **And** take-profit proximity = `clamp((currentPnl - baseline) / (tpThreshold - baseline), 0, 1)`
- **And** a just-opened position (where currentPnl ~ baseline) shows both TP and SL near 0%

### AC2 — Division-by-Zero Guard

- **Given** a degenerate case where `entryCostBaseline == threshold` (zero-edge position)
- **When** proximity is calculated
- **Then** the result is 0 (not NaN or Infinity)

### AC3 — Legacy Position Behavior

- **Given** a position with null entry close prices (pre-6.5.5i)
- **When** `entryCostBaseline` defaults to 0
- **Then** proximity formulas still produce correct results
- **And** the corrected formulas algebraically reduce to the original ratios:
  - SL: `(0 - currentPnl) / (0 - slThreshold)` = `currentPnl / slThreshold` (same sign behavior as original `.abs()` variant since both are negative)
  - TP: `(currentPnl - 0) / (tpThreshold - 0)` = `currentPnl / tpThreshold` (identical to original)

### AC4 — Tests

- **Given** the position enrichment test suite
- **When** tests run
- **Then** scenarios cover:
  - Just-opened position: both SL and TP proximity exactly 0 (identical current and entry prices)
  - Just-opened with small price drift: both proximities small but nonzero
  - Position with P&L halfway to SL: SL proximity ~50%, TP ~0%
  - Position with P&L at TP threshold (non-zero baseline): TP proximity = 100%
  - Legacy position (null entry close prices, baseline = 0): correct ratios matching original formula
  - Division-by-zero edge case (zero initial edge): both proximities = 0
  - Clamping: P&L beyond threshold clamps to 1.0, P&L opposite direction clamps to 0.0
- **And** all existing tests continue to pass
- **And** `pnpm lint` reports zero errors

## Tasks / Subtasks

- [x] Task 1: Fix proximity formulas in `position-enrichment.service.ts` (AC: #1, #2)
  - [x] 1.1 Replace SL proximity formula (lines 215-223) with baseline-relative version: `clamp((entryCostBaseline - currentPnl) / (entryCostBaseline - stopLossThreshold), 0, 1)`
  - [x] 1.2 Replace TP proximity formula (lines 224-232) with baseline-relative version: `clamp((currentPnl - entryCostBaseline) / (takeProfitThreshold - entryCostBaseline), 0, 1)`
  - [x] 1.3 Add division-by-zero guard: if denominator is zero (threshold == baseline), proximity = 0

- [x] Task 2: Update tests in `position-enrichment.service.spec.ts` (AC: #3, #4)
  - [x] 2.1 Add test: just-opened position with current prices === entry close prices — both proximities exactly 0.0
  - [x] 2.2 Add test: just-opened position with small price movement — both proximities small but nonzero
  - [x] 2.3 Add test: P&L halfway to SL — SL ~50%, TP ~0%
  - [x] 2.4 Add test: P&L at TP threshold with non-zero baseline — TP = 100%. Must use a position with offset `entryCostBaseline` (not zero) to verify TP proximity works correctly with the baseline-relative formula, not just the legacy case.
  - [x] 2.5 Update existing proximity test assertions to match new baseline-relative formula
  - [x] 2.6 Verify legacy position (baseline = 0) produces identical values to the original formula — explicitly assert algebraic equivalence by computing expected values using both old formula (`currentPnl.div(threshold)`) and new formula (`currentPnl.minus(new Decimal(0)).div(threshold.minus(new Decimal(0)))`) and asserting they're equal. The equivalence proof must be in the test code, not just an implicit side effect of outputs matching.
  - [x] 2.7 Add test: zero `scaledInitialEdge` (zero-edge position) — both denominators become 0, verify both SL and TP proximity return exactly 0 (not NaN or Infinity). This is the concrete test for AC2.
  - [x] 2.8 Add test: explicit clamping — verify that when `currentPnl` exceeds the threshold (beyond trigger), proximity clamps to 1.0, and when P&L moves opposite to the threshold direction (better than baseline for SL, worse than baseline for TP), proximity clamps to 0.0.

- [x] Task 3: Run full test suite and lint (AC: #4)
  - [x] 3.1 `pnpm test` — all tests pass (1404 tests, 80 files)
  - [x] 3.2 `pnpm lint` — zero errors

## Dev Notes

### Bug Summary

The exit proximity formulas in `position-enrichment.service.ts:215-232` measure "how far is P&L from zero relative to the threshold" but after Story 6.5.5i offset both thresholds by `entryCostBaseline`, the correct measurement is "how far has P&L moved from the baseline toward the threshold."

**This is display-only** — the actual exit trigger logic in `threshold-evaluator.service.ts` works correctly (it compares `currentPnl` against shifted thresholds directly). Exits fire at the correct P&L levels.

**Evidence from live paper position (2026-03-05):**

| Metric | Value |
|--------|-------|
| entryCostBaseline | -5.707 |
| takeProfitThreshold | -4.389 |
| stopLossThreshold | -9.003 |
| currentPnl | -5.71 |
| TP displayed | 100% (should be ~0%) |
| SL displayed | 63% (should be ~0%) |

### Current Buggy Formulas (lines 215-232)

```typescript
// BUGGY — measures from zero, not from baseline
const stopLossProximity = Decimal.min(
  new Decimal(1),
  Decimal.max(
    new Decimal(0),
    stopLossThreshold.isZero()
      ? new Decimal(0)
      : currentPnl.div(stopLossThreshold).abs(),
  ),
);
const takeProfitProximity = Decimal.min(
  new Decimal(1),
  Decimal.max(
    new Decimal(0),
    takeProfitThreshold.isZero()
      ? new Decimal(0)
      : currentPnl.div(takeProfitThreshold),
  ),
);
```

### Correct Formulas (baseline-relative)

```typescript
// CORRECT — measures from baseline toward threshold
const slDenom = entryCostBaseline.minus(stopLossThreshold);
const stopLossProximity = slDenom.isZero()
  ? new Decimal(0)
  : Decimal.min(
      new Decimal(1),
      Decimal.max(
        new Decimal(0),
        entryCostBaseline.minus(currentPnl).div(slDenom),
      ),
    );

const tpDenom = takeProfitThreshold.minus(entryCostBaseline);
const takeProfitProximity = tpDenom.isZero()
  ? new Decimal(0)
  : Decimal.min(
      new Decimal(1),
      Decimal.max(
        new Decimal(0),
        currentPnl.minus(entryCostBaseline).div(tpDenom),
      ),
    );
```

**Why this works:**
- SL proximity: numerator = `baseline - currentPnl` (how far P&L has dropped below baseline). Denominator = `baseline - slThreshold` (total distance from baseline to SL). Both are positive when P&L is between baseline and SL.
- TP proximity: numerator = `currentPnl - baseline` (how far P&L has risen above baseline). Denominator = `tpThreshold - baseline` (total distance from baseline to TP). Both are positive when P&L is between baseline and TP.
- Division-by-zero guard: if denominator is 0, threshold equals baseline (zero-edge), proximity = 0.

### Existing Test Patterns

The test file (`position-enrichment.service.spec.ts`, 420 lines, 12 tests) uses:
- `createMockPriceFeed()` — returns `{ getClosePrice: vi.fn() }` for price feed mocking
- `createMockPosition()` — returns a realistic `OpenPosition` with pair and both orders, all Decimal fields as Prisma Decimal objects
- Each test calls `service.enrich(position, mockPriceFeed)` and asserts on the `EnrichedPosition` result
- Proximity assertions use `toEqual(expect.any(String))` or specific string comparisons

Tests to update:
- **"computes exit proximity correctly"** (line 246): Currently asserts proximity is in [0,1] — update expected values for baseline-relative formula
- **"offsets exit proximity with entry cost baseline (6.5.5i)"** (line 352): Currently asserts SL proximity ≈ 0.7095 — this value will change with the new formula
- **"uses baseline=0 when entry close prices are null (legacy fallback)"** (line 395): Should continue to work — verify algebraic equivalence

### Architecture Compliance

- **Module boundaries:** Change is entirely within `src/dashboard/position-enrichment.service.ts` — stays in dashboard module
- **Financial math:** All calculations use `decimal.js` — no native JS operators
- **Error hierarchy:** No new errors needed — this is a formula fix
- **Events:** No new events — this is a display calculation
- **API contract:** `ExitProximityDto` shape is unchanged (`{ stopLoss: string, takeProfit: string }`)
- **Frontend:** No changes — `ExitProximityIndicator` renders backend values as-is

### Scope Guard

This story is strictly scoped to:
1. Fix two proximity formulas in `position-enrichment.service.ts`
2. Update tests in `position-enrichment.service.spec.ts`

Do NOT:
- Modify `threshold-evaluator.service.ts` (exit triggers are correct)
- Modify `financial-math.ts` (baseline computation is correct)
- Modify any frontend code (renders backend values as-is)
- Modify the Prisma schema
- Change the API response shape
- Add new events or error codes

### Project Structure Notes

**Modified files (pm-arbitrage-engine/):**
- `src/dashboard/position-enrichment.service.ts` — fix proximity formulas (lines 215-232)
- `src/dashboard/position-enrichment.service.spec.ts` — update/add test assertions

No new files. No deleted files.

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-05-exit-proximity-display.md — full root cause analysis and formula derivation]
- [Source: pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts:186-232 — entryCostBaseline computation + buggy proximity formulas]
- [Source: pm-arbitrage-engine/src/dashboard/position-enrichment.service.spec.ts:246-417 — existing proximity tests]
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts:1-50 — confirms exit logic is separate and correct]
- [Source: _bmad-output/implementation-artifacts/7-4-weekly-performance-metrics-trends.md — previous story patterns]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None required — straightforward formula replacement.

### Completion Notes List

- Replaced zero-relative proximity formulas with baseline-relative versions in `position-enrichment.service.ts:215-232`
- SL formula: `(entryCostBaseline - currentPnl) / (entryCostBaseline - stopLossThreshold)` with clamp [0,1]
- TP formula: `(currentPnl - entryCostBaseline) / (takeProfitThreshold - entryCostBaseline)` with clamp [0,1]
- Division-by-zero guard: denominator == 0 (zero-edge position) returns proximity 0
- Updated 2 existing test assertions to match new formula outputs
- Added 6 new test cases: just-opened (0%), small drift, halfway to SL (~42%), TP at threshold (100%), zero-edge div-by-zero, clamping behavior
- Legacy algebraic equivalence verified with explicit old-vs-new formula computation in test code
- All 1404 tests pass, zero lint errors

### File List

- `pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts` — fixed SL/TP proximity formulas (lines 215-232)
- `pm-arbitrage-engine/src/dashboard/position-enrichment.service.spec.ts` — updated 2 existing tests, added 6 new tests
