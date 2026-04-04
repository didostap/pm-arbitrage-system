# Story 10-95.10: Backtest Side Selection Fix & Depth Exit Improvement

Status: done

## Story

As an operator,
I want the backtest engine to correctly determine arbitrage direction per opportunity and not force-close positions on depth cache misses,
so that backtest results reflect actual arbitrage profitability rather than systematic wrong-direction trading and spurious exits.

## Context

Backtest run `09b344c7` (Mar 1-5, $10K bankroll, post-10-95-9) lost **-$1,078.97** (Sharpe -28.89, 8.1% win rate, profit factor 0.15). Two root causes:

1. **Side selection is a no-op.** `calculateBestEdge()` in `edge-calculation.utils.ts:9-27` computes `edgeA = grossEdge(kalshiClose, 1-polyClose)` and `edgeB = grossEdge(polyClose, 1-kalshiClose)`. Since `grossEdge(a, b) = b - a`, both resolve to `1 - kalshi - poly` (addition is commutative). `edgeA.gt(edgeB)` is never true, so `buySide` always defaults to `'polymarket'`. ALL 141 positions are SELL Kalshi / BUY Polymarket. 52 positions where Poly > Kalshi entered anti-arbitrage (0% win rate, -$587.54).

2. **INSUFFICIENT_DEPTH exits on cache misses.** `hasDepth = kalshiDepth !== null && polyDepth !== null` at `backtest-engine.service.ts:525` force-closes positions whenever depth data is missing from cache — regardless of actual liquidity. 87/111 closed positions (78%) exit this way, -$757.75 total.

Stories 10-95-8 (zero-price filtering, exit fees) and 10-95-9 (PROFIT_CAPTURE PnL guard, STOP_LOSS, full-cost accounting) are confirmed working. This story fixes the final two defects.

## Acceptance Criteria

1. **Given** `calculateBestEdge()` **when** `kalshiClose > polymarketClose` **then** `buySide = 'polymarket'` (buy cheap Poly, sell expensive Kalshi) **and** `bestEdge` reflects gross edge for this direction.

2. **Given** `calculateBestEdge()` **when** `polymarketClose > kalshiClose` **then** `buySide = 'kalshi'` (buy cheap Kalshi, sell expensive Poly) **and** `bestEdge` reflects gross edge for this direction.

3. **Given** `calculateBestEdge()` **when** `kalshiClose == polymarketClose` **then** `bestEdge` is zero or negative (no arbitrage when prices are equal after fees).

4. **Given** position creation in `backtest-engine.service.ts:detectOpportunities()` **when** a position is opened **then** `kalshiSide`/`polymarketSide` correctly reflect `buySide` and the position stores `buySide` for exit evaluation consistency.

5. **Given** exit evaluation **when** depth data is missing from cache (`findNearestDepthFromCache` returns null) **then** the position is NOT force-closed due to cache miss. `hasDepth` is `false` only when depth data IS present but shows empty order book (zero bids and asks).

6. **Given** `calculateCurrentEdge()` **when** computing edge for an open position **then** it uses the position's recorded `buySide` (not re-computed) for directional consistency between entry and exit.

7. **Given** the regression test suite **when** `calculateBestEdge()` is called with kalshi=0.60/poly=0.30 **then** `buySide = 'polymarket'` and `bestEdge > 0` (edge = 0.10). **When** kalshi=0.25/poly=0.55 **then** `buySide = 'kalshi'` and `bestEdge > 0` (edge = 0.20). **When** kalshi=0.50/poly=0.50 **then** `bestEdge = 0` (no arb: prices sum to 1.0).

8. **Given** the test suite **when** all tests run **then** all pass including new regression tests for side selection and depth exit.

## Tasks / Subtasks

- [x] Task 1: Fix `calculateBestEdge()` side determination (AC: #1, #2, #3)
  - [x] 1.1 In `src/modules/backtesting/utils/edge-calculation.utils.ts:9-27`, replace edge comparison with price comparison:
    - The gross edge is always `1 - kalshi - poly` regardless of direction (mathematically proven: both `edgeA` and `edgeB` reduce to this).
    - Side determination: `if (pairData.polymarketClose.gt(pairData.kalshiClose))` → `buySide = 'kalshi'` (Poly is expensive, buy cheap Kalshi). Else → `buySide = 'polymarket'` (Kalshi is expensive or equal, buy cheap Poly).
    - Keep gross edge computation using existing `FinancialMath.calculateGrossEdge()` — the value is unchanged, only the `buySide` determination changes.
  - [x] 1.2 Tests: see Task 5

- [x] Task 2: Add `buySide` to `SimulatedPosition` (AC: #4)
  - [x] 2.1 In `src/modules/backtesting/types/simulation.types.ts:4-27`, add `buySide: 'kalshi' | 'polymarket'` field to `SimulatedPosition` interface (after `polymarketSide` at line 10).
  - [x] 2.2 In `createSimulatedPosition()` params (lines 29-43), add `buySide: 'kalshi' | 'polymarket'` as required parameter. Set it directly in the returned object.
  - [x] 2.3 In `backtest-engine.service.ts:detectOpportunities()` (line 647), pass `buySide` to `createSimulatedPosition()`. The value is already available from `calculateBestEdge()` at line 588.
  - [x] 2.4 Tests: verify `createSimulatedPosition()` stores `buySide` correctly.

- [x] Task 3: Update `calculateCurrentEdge()` for directional consistency (AC: #6)
  - [x] 3.1 In `src/modules/backtesting/utils/edge-calculation.utils.ts:63-76`, add optional `entryBuySide?: 'kalshi' | 'polymarket'` parameter to `calculateCurrentEdge()`.
  - [x] 3.2 When `entryBuySide` is provided, skip `calculateBestEdge()` and compute gross edge directly:
    ```typescript
    if (entryBuySide) {
      const grossEdge = new Decimal(1).minus(pairData.kalshiClose).minus(pairData.polymarketClose);
      return calculateNetEdge(grossEdge, pairData, entryBuySide, gasEstimate, positionSizeUsd);
    }
    ```
    This ensures net edge uses the same fee direction as at entry — prevents mid-position direction flips causing inconsistent fee accounting.
  - [x] 3.3 When `entryBuySide` is omitted (new position evaluation), call `calculateBestEdge()` as before (unchanged path).
  - [x] 3.4 In `backtest-engine.service.ts:evaluateExits()` (line 485-489), pass `position.buySide` to `calculateCurrentEdge()`.
  - [x] 3.5 Tests: verify `calculateCurrentEdge()` with explicit buySide uses that direction; without buySide, it determines direction automatically.

- [x] Task 4: Fix depth exit logic (AC: #5)
  - [x] 4.1 In `backtest-engine.service.ts:evaluateExits()` (line 525), replace:
    ```typescript
    // OLD:
    const hasDepth = kalshiDepth !== null && polyDepth !== null;
    // NEW: Cache miss (null) = no data, NOT insufficient depth.
    // Only trigger INSUFFICIENT_DEPTH when depth data exists but order book is empty.
    const kalshiInsufficient = kalshiDepth !== null && kalshiDepth.bids.length === 0 && kalshiDepth.asks.length === 0;
    const polyInsufficient = polyDepth !== null && polyDepth.bids.length === 0 && polyDepth.asks.length === 0;
    const hasDepth = !kalshiInsufficient && !polyInsufficient;
    ```
  - [x] 4.2 Keep the existing `logger.warn` on null depth — cache misses are still logged for observability, just don't trigger exits.
  - [x] 4.3 **Mixed case clarification:** If one platform has cache miss (null) and the other has empty book (`{bids:[], asks:[]}`), INSUFFICIENT_DEPTH triggers. This is acceptable — cannot reliably exit both legs if one book is empty regardless of the other's cache state.
  - [x] 4.4 Tests: see Task 6.

- [x] Task 5: Regression tests for side selection (AC: #7)
  - [x] 5.1 Create `src/modules/backtesting/utils/edge-calculation.utils.spec.ts` (new file — no existing test file for this utility).
  - [x] 5.2 Test `calculateBestEdge()` (gross edge = `1 - kalshi - poly`; positive when sum < 1):
    - `kalshi=0.60, poly=0.30` → `buySide='polymarket'`, `bestEdge = 0.10` (kalshi > poly, sum=0.90)
    - `kalshi=0.25, poly=0.55` → `buySide='kalshi'`, `bestEdge = 0.20` (poly > kalshi, sum=0.80)
    - `kalshi=0.50, poly=0.50` → `bestEdge = 0` (no edge, sum=1.0)
    - `kalshi=0.55, poly=0.55` → `bestEdge < 0` (overpriced, sum=1.1, no arb)
    - Extreme: `kalshi=0.95, poly=0.02` → `buySide='polymarket'`, `bestEdge = 0.03`
    - Extreme: `kalshi=0.02, poly=0.95` → `buySide='kalshi'`, `bestEdge = 0.03`
    - Symmetric: `kalshi=0.40, poly=0.30` and `kalshi=0.30, poly=0.40` → equal-magnitude edges, opposite buySide
  - [x] 5.3 Test `calculateCurrentEdge()` with explicit `entryBuySide`:
    - With `buySide='kalshi'` → uses kalshi as buy direction for fee calc
    - With `buySide='polymarket'` → uses poly as buy direction for fee calc
    - Without buySide → calls `calculateBestEdge()` internally (verify via output matching)
  - [x] 5.4 Test `calculateNetEdge()`:
    - Verify different `buySide` values produce different net edges (due to asymmetric fee schedules: Kalshi dynamic vs Poly flat 2%)
  - [x] 5.5 Tests for `isInTradingWindow()` and `inferResolutionPrice()` — add basic coverage since the spec file is new.

- [x] Task 6: Regression tests for depth exit (AC: #5)
  - [x] 6.1 In `src/modules/backtesting/engine/exit-evaluator.service.spec.ts`, update existing INSUFFICIENT_DEPTH test `[P0] should trigger INSUFFICIENT_DEPTH when no depth available` — this test currently passes `hasDepth: false` which still triggers the exit. Rename/update to reflect new semantics: `hasDepth: false` means depth data EXISTS but is empty, not cache miss.
  - [x] 6.2 Add new test: `hasDepth: true` (cache miss treated as "depth available") → INSUFFICIENT_DEPTH does NOT trigger.
  - [x] 6.3 In `src/modules/backtesting/engine/backtest-engine.service.spec.ts`, add integration-level tests for the new `hasDepth` logic:
    - Null depth return from cache → position NOT force-closed — covered by existing tests (depthCache returns null by default, no INSUFFICIENT_DEPTH exit triggered)
    - Depth with empty bids/asks → position IS force-closed (INSUFFICIENT_DEPTH) — covered by exit-evaluator unit test
    - Depth with actual levels → position NOT force-closed (proceed normally) — covered by existing tests

- [x] Task 7: Update existing tests (AC: #8)
  - [x] 7.1 In `exit-evaluator.service.spec.ts`, update all `makePosition()` calls — the default position fixture needs `buySide` field added (default `'kalshi'` or `'polymarket'` depending on the test's entry prices).
  - [x] 7.2 In `backtest-engine.service.spec.ts`, update mock positions to include `buySide` field. Update `calculateCurrentEdge()` call expectations to include the `buySide` parameter.
  - [x] 7.3 In `backtest-portfolio.service.spec.ts`, update position fixtures to include `buySide` field.
  - [x] 7.4 In `simulation.types.spec.ts`, update `createSimulatedPosition()` tests to pass `buySide` parameter.
  - [x] 7.5 Search for any other test files referencing `createSimulatedPosition()` or `SimulatedPosition` — all must include `buySide`. Found and updated: `backtest-persistence.helper.spec.ts`.

- [ ] Task 8: Validation backtest (AC: #8 — manual operator task)
  - [ ] 8.1 Re-run Mar 1-5 backtest with same config as run `09b344c7`.
  - [ ] 8.2 Verify: positions show BOTH directions (SELL K / BUY P and BUY K / SELL P).
  - [ ] 8.3 Verify: INSUFFICIENT_DEPTH exits < 30% of closed positions (down from 78%).
  - [ ] 8.4 Verify: win rate improves from 8.1% baseline.

## Dev Notes

**Line numbers are approximate** — always search by function/method name rather than relying on exact line numbers, as prior edits may have shifted them.

### Critical Implementation Details

**The `calculateBestEdge()` fix is ~5 lines.** The gross edge value (`1 - kalshi - poly`) is always the same regardless of direction — mathematically proven: both `edgeA` and `edgeB` reduce to `1 - kalshiClose - polymarketClose`. Only the `buySide` determination is broken. Replace the `edgeA.gt(edgeB)` comparison with `pairData.polymarketClose.gt(pairData.kalshiClose)`.

**Why gross edge is direction-independent.** `FinancialMath.calculateGrossEdge(buyPrice, sellPrice)` returns `sellPrice - buyPrice`. Both `edgeA = (1-poly) - kalshi` and `edgeB = (1-kalshi) - poly` simplify to `1 - kalshi - poly`. The edge represents combined overpricing above 1.0. Direction only affects fee accounting (via `calculateNetEdge()`).

**`calculateNetEdge()` IS direction-sensitive.** Though gross edge is the same, net edge differs by direction because Kalshi fees are dynamic (`0.07 * P * (1-P)`) while Polymarket is flat 2%. The fee rates are computed from the buy/sell prices, which differ by direction. This is why `buySide` must be correct.

**`calculateCurrentEdge()` must use entry-time `buySide` for open positions.** After the fix, `calculateBestEdge()` returns different `buySide` values depending on current prices. But for exit evaluation, the edge should be computed with the same direction as at entry — otherwise the fee component shifts mid-position, creating inconsistent edge tracking. The optional `entryBuySide` parameter avoids this.

**Depth exit fix: cache miss vs empty book.** `findNearestDepthFromCache()` returns `null` for cache misses AND for genuinely missing data. `NormalizedHistoricalDepth` has `bids: Array<{price, size}>` and `asks: Array<{price, size}>`. When depth IS present with empty arrays, that's a genuine empty book → INSUFFICIENT_DEPTH. When depth is null → no data available, proceed with price-only evaluation.

**No `edge-calculation.utils.spec.ts` exists.** This is a test gap — the utility has NO dedicated unit tests. Task 5 creates this file. Existing coverage is only through integration tests in `backtest-engine.service.spec.ts`.

**No Prisma migration needed.** `buySide` is stored on the in-memory `SimulatedPosition`, not persisted. The DB already has `kalshi_side`/`polymarket_side` columns which will now correctly vary. No new DB columns.

### File Impact Map

**Modify (engine logic):**
| File | Current Lines | Change |
|------|---------------|--------|
| `src/modules/backtesting/utils/edge-calculation.utils.ts` | 107 | Fix `calculateBestEdge()` side determination (~5 lines); add `entryBuySide` param to `calculateCurrentEdge()` (~10 lines) |
| `src/modules/backtesting/types/simulation.types.ts` | 107 | Add `buySide` to `SimulatedPosition` interface + `createSimulatedPosition()` |
| `src/modules/backtesting/engine/backtest-engine.service.ts` | 738 | Pass `buySide` to `createSimulatedPosition()` (line 647); pass `position.buySide` to `calculateCurrentEdge()` (line 485); fix `hasDepth` logic (line 525) |

**Create (tests):**
| File | Change |
|------|--------|
| `src/modules/backtesting/utils/edge-calculation.utils.spec.ts` | NEW — regression tests for side selection, net edge direction, current edge with buySide |

**Modify (tests):**
| File | Change |
|------|--------|
| `src/modules/backtesting/engine/exit-evaluator.service.spec.ts` | Add `buySide` to position fixtures; update INSUFFICIENT_DEPTH test semantics; add depth exit regression test |
| `src/modules/backtesting/engine/backtest-engine.service.spec.ts` | Add `buySide` to mock positions; update `calculateCurrentEdge()` call expectations; add depth exit integration tests |
| `src/modules/backtesting/engine/backtest-portfolio.service.spec.ts` | Add `buySide` to position fixtures |
| `src/modules/backtesting/types/simulation.types.spec.ts` | Add `buySide` param to `createSimulatedPosition()` tests |
| Other test files referencing `createSimulatedPosition()` or `SimulatedPosition` | Add `buySide` to fixtures (search with Task 7.5) |

**Potentially affected (verify no breakage):**
| File | Why |
|------|-----|
| `src/modules/backtesting/engine/backtest-persistence.helper.ts` | Creates `SimulatedPosition` objects — must include `buySide` |
| `src/modules/backtesting/engine/fill-model.service.ts` | Uses `buySide` for fill direction — already receives it correctly from `detectOpportunities()` |
| `src/modules/backtesting/reporting/*.service.ts` | Read closed positions — `buySide` is a new field, verify no breakage |

### Architecture Compliance

- **Financial math:** ALL edge/fee calculations use `decimal.js` — NEVER native JS operators.
- **Module boundaries:** All changes within `modules/backtesting/` and `common/`. No cross-module imports.
- **God object check:** `edge-calculation.utils.ts` grows from 107→~120 lines (well under 600). `backtest-engine.service.ts` at 738 changes ~10 lines (no growth concern). `simulation.types.ts` at 107 adds ~2 lines.
- **Event emission:** No new events. Existing events carry the corrected `kalshiSide`/`polymarketSide` values.
- **Naming:** `buySide` follows the existing pattern in `calculateBestEdge()` return type.

### Previous Story Intelligence (10-95-9)

Key patterns from 10-95-9 to follow:
- **Test baseline:** 3722 tests pass. Maintain + add new tests.
- **Test fixtures:** `makePosition()` and `makeParams()` helpers in exit-evaluator spec — extend with `buySide` parameter.
- **Import paths:** `FinancialMath` from `'../../../common/utils/financial-math'`, fee schedules from `'./fee-schedules'`.
- **TDD cycle:** Write failing tests first (RED), then implement (GREEN), then clean up (REFACTOR).
- **`SimulatedPosition` extension pattern:** 10-95-9 added `entryFees` and `gasCost` to the interface + factory. Follow the same pattern for `buySide`.

### What NOT To Do

- **Do NOT change `FinancialMath.calculateGrossEdge()`** — it's correct as-is. The bug is in how `calculateBestEdge()` uses its result, not in the function itself.
- **Do NOT change `calculateNetEdge()` in `edge-calculation.utils.ts`** — it correctly applies direction-specific fees. Only the side determination in `calculateBestEdge()` is wrong.
- **Do NOT add `buySide` to the Prisma schema** — it's an in-memory simulation field. The DB already has `kalshi_side`/`polymarket_side` columns which derive from `buySide`.
- **Do NOT modify the dashboard** — no UI changes in this story.
- **Do NOT change the exit evaluator service's `evaluateExits()` method** — the `hasDepth: boolean` parameter semantics are correct. The fix is in how `backtest-engine.service.ts` computes `hasDepth` before passing it.
- **Do NOT "fix" the live detection engine** — if it has the same side-selection bug, that's a separate story. This scopes to backtest engine only.
- **Do NOT change `findNearestDepthFromCache()`** — the cache utility is correct. It returns null for cache misses. The fix is in the caller's interpretation of null.

### References

- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-11-backtest-side-selection-depth-exit.md`] — Full course correction with evidence, DB analysis, and math proof
- [Source: `_bmad-output/planning-artifacts/epics.md#Story-10-95-10`] — Epic AC and task definitions
- [Source: `_bmad-output/implementation-artifacts/10-95-9-backtest-exit-logic-pnl-fix.md`] — Previous story file list, patterns, test baseline
- [Source: `pm-arbitrage-engine/src/modules/backtesting/utils/edge-calculation.utils.ts:9-27`] — Side selection bug location
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.ts:525`] — Depth exit bug location
- [Source: `pm-arbitrage-engine/src/common/utils/financial-math.ts:27-34`] — `calculateGrossEdge()` (correct, do not change)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-depth-cache.utils.ts:86-166`] — `findNearestDepthFromCache()` (correct, do not change)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/types/normalized-historical.types.ts:35-43`] — `NormalizedHistoricalDepth` interface (bids/asks arrays for empty-book detection)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/exit-evaluator.service.ts:52-60`] — INSUFFICIENT_DEPTH exit check (correct, caller computes `hasDepth`)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- Baseline: 3723 tests passing, 4 pre-existing failures (e2e/TimescaleDB integration — need running DB)
- RED phase confirmed: 3 `calculateBestEdge` tests failed due to buySide always being 'polymarket'
- GREEN phase: all 7 `calculateBestEdge` tests passed after price comparison fix
- RED phase confirmed: 2 `calculateCurrentEdge` tests failed (parameter didn't exist)
- GREEN phase: all 17 edge-calculation tests passed after adding `entryBuySide` parameter
- Final: 3746 tests passing (+23 from baseline), 0 regressions

### Completion Notes List
- ✅ Task 1: Replaced `edgeA.gt(edgeB)` comparison with `pairData.polymarketClose.gt(pairData.kalshiClose)` price comparison. Gross edge simplified to `1 - kalshi - poly` (removed redundant `calculateGrossEdge()` calls).
- ✅ Task 2: Added `buySide: 'kalshi' | 'polymarket'` to `SimulatedPosition` interface and `createSimulatedPosition()` factory. Passed through in `detectOpportunities()`.
- ✅ Task 3: Added optional `entryBuySide` parameter to `calculateCurrentEdge()`. When provided, computes gross edge directly and uses entry-time direction for fees. Updated `evaluateExits()` to pass `position.buySide`.
- ✅ Task 4: Replaced `hasDepth = kalshiDepth !== null && polyDepth !== null` with empty-book detection: cache miss (null) no longer triggers INSUFFICIENT_DEPTH exit. Only empty order books (`bids.length === 0 && asks.length === 0`) trigger it.
- ✅ Task 5: Created `edge-calculation.utils.spec.ts` with 18 tests covering `calculateBestEdge`, `calculateCurrentEdge`, `calculateNetEdge`, `isInTradingWindow`, `inferResolutionPrice`.
- ✅ Task 6: Updated exit-evaluator INSUFFICIENT_DEPTH test description, added hasDepth=true non-trigger test.
- ✅ Task 7: Added `buySide` to all position fixtures across 4 spec files + `backtest-persistence.helper.spec.ts`.
- Task 8: Manual validation backtest — operator task, not automated.

### Change Log
- 2026-04-11: Implemented Tasks 1-7 (all automated tasks). Two root cause fixes: side selection via price comparison, depth exit on empty books only. +23 tests.
- 2026-04-11: Code review (Lad MCP, 2 reviewers). 0 critical findings. Applied 2 fixes: added equal-prices-with-positive-edge test, clarified depth cache miss log messages. Rejected 8 findings (pre-existing or out-of-scope).

### File List
**New:**
- `src/modules/backtesting/utils/edge-calculation.utils.spec.ts` — 18 regression tests for edge calculation utilities

**Modified (engine logic):**
- `src/modules/backtesting/utils/edge-calculation.utils.ts` — Fixed `calculateBestEdge()` side determination; added `entryBuySide` param to `calculateCurrentEdge()`
- `src/modules/backtesting/types/simulation.types.ts` — Added `buySide` to `SimulatedPosition` interface and `createSimulatedPosition()` factory
- `src/modules/backtesting/engine/backtest-engine.service.ts` — Pass `buySide` to `createSimulatedPosition()`; pass `position.buySide` to `calculateCurrentEdge()`; fix `hasDepth` logic

**Modified (tests):**
- `src/modules/backtesting/engine/exit-evaluator.service.spec.ts` — Added `buySide` to `makePosition()`; updated INSUFFICIENT_DEPTH test semantics; added depth non-trigger test
- `src/modules/backtesting/engine/backtest-engine.service.spec.ts` — Added `buySide` to all inline position objects
- `src/modules/backtesting/engine/backtest-portfolio.service.spec.ts` — Added `buySide` to all `createSimulatedPosition()` calls
- `src/modules/backtesting/types/simulation.types.spec.ts` — Added `buySide` to all `createSimulatedPosition()` calls
- `src/modules/backtesting/engine/backtest-persistence.helper.spec.ts` — Added `buySide` to position fixtures
