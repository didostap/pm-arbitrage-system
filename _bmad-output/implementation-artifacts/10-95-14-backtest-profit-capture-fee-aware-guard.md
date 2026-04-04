# Story 10-95.14: PROFIT_CAPTURE Fee-Aware P&L Guard

Status: done

## Story

As an operator,
I want the backtest PROFIT_CAPTURE exit to verify post-fee profitability before triggering,
so that positions with small edge but large fees are not exited as "profit captures" when they would actually realize a loss.

## Context

In backtest run `2d2f84ac`, 81 of 413 PROFIT_CAPTURE exits (20%) realized a net loss despite the P&L guard checking `mtmPnl > 0`. The guard at `exit-evaluator.service.ts:120-133` uses raw `calculateLegPnl()` (price movement only), but `closePosition()` at `backtest-portfolio.service.ts:243-277` deducts entry fees, exit fees, and gas. When raw P&L is positive but smaller than total fees, the guard approves exit but the actual result is negative.

Evidence from the run:
- Losing PROFIT_CAPTURE avg: entry_edge 4.1%, raw P&L ~$8.40, fees ~$9.80, realized -$1.99
- Winning PROFIT_CAPTURE avg: entry_edge 8.8%, raw P&L ~$19.50, fees ~$7.46, realized +$12.06
- Win rate by entry edge: <5% = 61%, 5-6% = 84%, 6-8% = 95%, 8%+ = 100%

Story 10-95-11 already raised the default `edgeThresholdPct` from 0.03 to 0.05, which prevents many low-edge entries. The fee-aware guard is defense-in-depth for positions that enter near the threshold.

## Acceptance Criteria

1. **Given** PROFIT_CAPTURE exit evaluation **when** `capturedRatio >= exitProfitCapturePct` **then** the P&L guard estimates total fees (entry fees from position + estimated exit fees using `FinancialMath.calculateTakerFeeRate()`) and checks `rawMtmPnl - estimatedTotalFees > 0`. If post-fee P&L <= 0, the condition returns false (falls through to other exit triggers).

2. **Given** estimated exit fees in the P&L guard **then** uses the same fee estimation pattern as `calculateUnrealizedPnl()` in `backtest-portfolio.service.ts:27-66` (both platform exit fees + entry fees + gas cost).

3. **Given** a position where raw mark-to-market P&L is positive but smaller than estimated total fees **when** PROFIT_CAPTURE is evaluated **then** it returns false and the position falls through to EDGE_EVAPORATION, TIME_DECAY, or STOP_LOSS as appropriate.

4. **Given** existing tests **when** all run **then** all pass. New tests cover: fee-aware guard rejects exit when raw P&L < total fees; fee-aware guard approves when raw P&L > total fees; guard correctly estimates exit fees using platform fee schedules; edge cases (zero fees, very small positions, fees exactly equal to P&L).

## Tasks / Subtasks

- [x] Task 1: Add fee estimation imports to `exit-evaluator.service.ts` (AC: #1, #2)
  - [x] 1.1 In `src/modules/backtesting/engine/exit-evaluator.service.ts`, update the import from `financial-math` (line 4) to include `FinancialMath`:
    ```typescript
    import { calculateLegPnl, FinancialMath } from '../../../common/utils/financial-math';
    ```
  - [x] 1.2 Add fee schedule imports (new import statement):
    ```typescript
    import {
      DEFAULT_KALSHI_FEE_SCHEDULE,
      DEFAULT_POLYMARKET_FEE_SCHEDULE,
    } from '../utils/fee-schedules';
    ```
    These are the same imports used by `backtest-portfolio.service.ts` (line 10-11).

- [x] Task 2: Make `isProfitCaptureTriggered()` fee-aware (AC: #1, #2, #3)
  - [x] 2.1 In `isProfitCaptureTriggered()` (line 114-134), replace the raw PnL guard (lines 120-133) with a fee-aware guard. The current code:
    ```typescript
    // PnL guard: only trigger if mark-to-market PnL is positive
    const kalshiPnl = calculateLegPnl(
      params.position.kalshiSide.toLowerCase(),
      params.position.kalshiEntryPrice,
      params.kalshiCurrentPrice,
      params.positionSizeUsd,
    );
    const polyPnl = calculateLegPnl(
      params.position.polymarketSide.toLowerCase(),
      params.position.polymarketEntryPrice,
      params.polymarketCurrentPrice,
      params.positionSizeUsd,
    );
    return kalshiPnl.plus(polyPnl).gt(0);
    ```
    Replace with:
    ```typescript
    // Fee-aware PnL guard: only trigger if post-fee PnL is positive (10-95-14)
    const kalshiPnl = calculateLegPnl(
      params.position.kalshiSide.toLowerCase(),
      params.position.kalshiEntryPrice,
      params.kalshiCurrentPrice,
      params.positionSizeUsd,
    );
    const polyPnl = calculateLegPnl(
      params.position.polymarketSide.toLowerCase(),
      params.position.polymarketEntryPrice,
      params.polymarketCurrentPrice,
      params.positionSizeUsd,
    );
    const rawMtmPnl = kalshiPnl.plus(polyPnl);

    // Estimate exit fees (same pattern as calculateUnrealizedPnl)
    const kalshiExitFeeRate = FinancialMath.calculateTakerFeeRate(
      params.kalshiCurrentPrice,
      DEFAULT_KALSHI_FEE_SCHEDULE,
    );
    const polyExitFeeRate = FinancialMath.calculateTakerFeeRate(
      params.polymarketCurrentPrice,
      DEFAULT_POLYMARKET_FEE_SCHEDULE,
    );
    const estimatedExitFees = params.kalshiCurrentPrice
      .mul(params.positionSizeUsd)
      .mul(kalshiExitFeeRate)
      .plus(
        params.polymarketCurrentPrice.mul(params.positionSizeUsd).mul(polyExitFeeRate),
      );

    const postFeePnl = rawMtmPnl
      .minus(estimatedExitFees)
      .minus(params.position.entryFees)
      .minus(params.position.gasCost);

    return postFeePnl.gt(0);
    ```
  - [x] 2.2 **No changes to `ExitEvaluationParams` interface needed.** The `position` field is already `SimulatedPosition`, which carries `entryFees: Decimal` and `gasCost: Decimal` (added in story 10-95-9). The fee-aware guard accesses them via `params.position.entryFees` and `params.position.gasCost`.
  - [x] 2.3 **No changes to the `evaluateExits()` call site in `backtest-engine.service.ts` (line 572-588).** The `position` object already includes entry fees and gas cost.

- [x] Task 3: Update existing PROFIT_CAPTURE tests for fee-aware guard (AC: #4)
  - [x] 3.1 In `src/modules/backtesting/engine/exit-evaluator.service.spec.ts`, the existing `makePosition()` helper (line 10-28) creates positions via `createSimulatedPosition()` which defaults `entryFees` and `gasCost` to `new Decimal(0)`. Existing tests that trigger PROFIT_CAPTURE with zero fees will continue to pass — raw PnL > 0 still means post-fee PnL > 0 when fees are zero.
  - [x] 3.2 Verify the following existing tests still pass unchanged:
    - `[P0] should trigger PROFIT_CAPTURE when edge recovery >= exitProfitCapturePct of entry edge` (line 95) — zero fees, positive raw PnL → still triggers.
    - `[P0] should NOT trigger PROFIT_CAPTURE when capturedRatio >= 0.8 but mtm PnL <= 0` (line 208) — raw PnL <= 0 → still blocked.
    - `[P0] should trigger PROFIT_CAPTURE when capturedRatio >= 0.8 AND mtm PnL > 0` (line 248) — zero fees, positive raw PnL → still triggers.
    - Priority tests (`INSUFFICIENT_DEPTH over PROFIT_CAPTURE`, `PROFIT_CAPTURE over EDGE_EVAPORATION`) — unchanged logic.

- [x] Task 4: Add fee-aware guard tests (AC: #1, #3, #4)
  - [x] 4.1 In `exit-evaluator.service.spec.ts`, after the existing PROFIT_CAPTURE PnL guard tests (after line 278), add a new describe block:
    ```
    // ============================================================
    // PROFIT_CAPTURE fee-aware PnL guard (10-95-14) — 5 tests
    // ============================================================
    ```
  - [x] 4.2 Tests to add:
    ```
    [P0] should NOT trigger PROFIT_CAPTURE when raw PnL positive but less than estimated fees
      — Position: entryFees=new Decimal('5'), gasCost=new Decimal('2'), positionSizeUsd=300
      — Prices producing small positive raw PnL (~$6): kalshiEntry=0.45, polyEntry=0.52,
        kalshiCurrent=0.46, polyCurrent=0.51 (BUY kalshi gains $3, SELL poly gains $3, total ~$6 raw).
        Exit fees (~$8+) + entry $5 + gas $2 >> $6 raw PnL. entryEdge=0.015, currentNetEdge=0.001
        (capturedRatio=0.933 >= 0.80).
      — Assert result is NOT null (another exit reason triggers instead of PROFIT_CAPTURE)
      — Assert result.reason !== 'PROFIT_CAPTURE'
      — NOTE: Exact prices should be tuned to ensure raw PnL > 0 but post-fee PnL <= 0.
        Use calculateLegPnl + FinancialMath.calculateTakerFeeRate to verify math in test setup.

    [P0] should trigger PROFIT_CAPTURE when raw PnL exceeds estimated fees
      — Position: entryFees=new Decimal('5'), gasCost=new Decimal('2')
      — Prices producing large positive raw PnL (~$25): kalshiEntry=0.45, polyEntry=0.52,
        kalshiCurrent=0.50, polyCurrent=0.48 (standard profitable convergence).
        entryEdge=0.015, currentNetEdge=0.002 (capturedRatio=0.867 >= 0.80).
      — Assert result.reason === 'PROFIT_CAPTURE'

    [P1] should trigger PROFIT_CAPTURE with zero entry fees and zero gas (backward compat)
      — Position: entryFees=new Decimal('0'), gasCost=new Decimal('0')
      — Same profitable prices as existing PROFIT_CAPTURE test. Confirms the fee-aware guard
        degrades gracefully to the original behavior when fees are zero.
      — Assert result.reason === 'PROFIT_CAPTURE'

    [P1] should NOT trigger PROFIT_CAPTURE when fees exactly equal raw PnL (boundary)
      — Construct position with entryFees + gasCost + estimated exit fees == raw PnL (to Decimal precision).
      — postFeePnl == 0, which is NOT > 0, so guard rejects.
      — Assert result.reason !== 'PROFIT_CAPTURE'

    [P1] should NOT trigger PROFIT_CAPTURE when raw PnL is negative regardless of fees
      — Position: entryFees=new Decimal('0'), gasCost=new Decimal('0')
      — Prices producing negative raw PnL (same as existing test at line 208).
      — Confirms fee-aware guard still rejects when raw PnL itself is negative.
      — Assert result.reason !== 'PROFIT_CAPTURE'
    ```
  - [x] 4.3 **Test price calculation guidance:** To construct reliable test cases, compute the expected raw PnL in the test setup:
    ```typescript
    // Verify test math: calculate what isProfitCaptureTriggered will compute
    const expectedKalshiPnl = calculateLegPnl('buy', kalshiEntry, kalshiCurrent, positionSize);
    const expectedPolyPnl = calculateLegPnl('sell', polyEntry, polyCurrent, positionSize);
    const expectedRawPnl = expectedKalshiPnl.plus(expectedPolyPnl);
    // Then compute exit fees and verify postFeePnl sign matches test assertion
    ```

- [x] Task 5: Lint + test (post-edit)
  - [x] 5.1 Run `pnpm lint` — fix any issues.
  - [x] 5.2 Run `pnpm test` — verify baseline + new tests pass. 23/23 exit-evaluator tests pass (+5 new). Full suite: 3783+ unit tests pass, all failures are pre-existing e2e/integration (database/network).

## Dev Notes

**Line numbers are approximate** — always search by function/method name rather than relying on exact line numbers, as prior edits may have shifted them.

### Critical Implementation Details

**The fix is entirely within `isProfitCaptureTriggered()`.** No interface changes, no new parameters, no call site changes. The `SimulatedPosition` already carries `entryFees` and `gasCost` (added in story 10-95-9), and these are accessible via `params.position.entryFees` and `params.position.gasCost`.

**Reuse the `calculateUnrealizedPnl()` pattern, not the function.** The fee estimation logic is identical to `calculateUnrealizedPnl()` in `backtest-portfolio.service.ts:27-66`, but we inline it in the exit evaluator rather than calling the function. Reason: `calculateUnrealizedPnl()` takes a `SimulatedPosition` and returns a single Decimal; we already have the raw leg PnL values computed and need intermediate values. Inlining avoids double calculation.

**New imports needed in `exit-evaluator.service.ts`.** Currently it only imports `calculateLegPnl` from `financial-math`. Add `FinancialMath` to the same import, and add `DEFAULT_KALSHI_FEE_SCHEDULE` / `DEFAULT_POLYMARKET_FEE_SCHEDULE` from `../utils/fee-schedules`. These are the same fee schedules used throughout the backtesting module.

**`ExitEvaluationParams` does NOT change.** The position object (type `SimulatedPosition`) already carries the needed fee data. No new fields on the params interface, no changes to the call site in `backtest-engine.service.ts:572-588`.

**Existing tests pass without modification.** The `createSimulatedPosition()` factory defaults `entryFees` and `gasCost` to `Decimal(0)`. With zero fees, the fee-aware guard behaves identically to the old raw-PnL guard: `postFeePnl = rawMtmPnl - 0 - 0 - 0 = rawMtmPnl`. All existing PROFIT_CAPTURE tests use zero-fee positions.

**`closePosition()` already deducts fees identically.** The fee-aware guard mirrors the exact fee calculation from `closePosition()` at `backtest-portfolio.service.ts:257-277`: estimated exit fees via `FinancialMath.calculateTakerFeeRate()` + entry fees + gas cost. This ensures the guard's prediction matches the actual realized PnL.

**Exit fee estimation uses current market prices (mark-to-market).** The guard estimates exit fees using `kalshiCurrentPrice` / `polymarketCurrentPrice`, matching the `calculateUnrealizedPnl()` approach. Actual realized fees in `closePosition()` will use the final exit prices. Since the guard runs at the same timestep as `closePosition()`, the prices are identical — the estimate is exact.

### File Impact Map

**Modify (1 file):**
| File | Current Lines | Change |
|------|---------------|--------|
| `src/modules/backtesting/engine/exit-evaluator.service.ts` | ~170 | Add 2 imports (~5 lines), expand `isProfitCaptureTriggered()` PnL guard from 14 to ~28 lines (+14 lines) |

**Modify (1 test file):**
| File | Change |
|------|--------|
| `src/modules/backtesting/engine/exit-evaluator.service.spec.ts` | ~5 new tests in fee-aware guard section. Add imports for test math verification: `import { FinancialMath } from '../../../common/utils/financial-math';` and `import { DEFAULT_KALSHI_FEE_SCHEDULE, DEFAULT_POLYMARKET_FEE_SCHEDULE } from '../utils/fee-schedules';` |

### Previous Story Intelligence (10-95-13)

- **Pattern:** Story 10-95-13 added entry-time filters in `detectOpportunities()`. This story adds an exit-time filter in `isProfitCaptureTriggered()`. Different scope, but same philosophy: prevent unprofitable operations before they happen.
- **Test patterns:** 10-95-13 used `expect(result!.reason).not.toBe(...)` for rejection assertions and verified counter accumulation. For this story, the rejection assertion pattern applies (verify PROFIT_CAPTURE does NOT fire), but no counters are needed — the guard is a boolean check, not a tracked metric.
- **No `detectOpportunities()` parameter count increase.** Unlike 10-95-13 which added 3 new parameters to `detectOpportunities()`, this story has zero signature changes anywhere.

### What NOT To Do

- **Do NOT create a `calculatePostFeePnl()` utility.** The calculation is 6 lines, used once. Extracting it would be premature abstraction.
- **Do NOT add fee-awareness to `isStopLossTriggered()`.** Stop-loss checks raw PnL against a threshold — it's explicitly meant to catch adverse price movement, not fee impact. A separate story would be needed if that behavior changes.
- **Do NOT add new fields to `IBacktestConfig` or `BacktestConfigDto`.** There's no configuration needed — the guard unconditionally uses actual fee schedules. A "disable fee-aware guard" toggle would be scope creep.

### References

- [Source: exit-evaluator.service.ts — `isProfitCaptureTriggered()` lines 114-134]
- [Source: backtest-portfolio.service.ts — `calculateUnrealizedPnl()` lines 27-66]
- [Source: backtest-portfolio.service.ts — `closePosition()` fee deduction lines 243-277]
- [Source: simulation.types.ts — `SimulatedPosition.entryFees`, `SimulatedPosition.gasCost` lines 26-27]
- [Source: fee-schedules.ts — `DEFAULT_KALSHI_FEE_SCHEDULE`, `DEFAULT_POLYMARKET_FEE_SCHEDULE`]
- [Source: financial-math.ts — `FinancialMath.calculateTakerFeeRate()`]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
- RED phase: 2 of 5 new tests failed as expected (fee-rejection + boundary). 3 passed (approve, backward-compat, negative-raw).
- Boundary test fix: original used `exitEdgeEvaporationPct=0.002 == currentNetEdge=0.002` so no fallback exit triggered → result was null. Fixed by setting `exitEdgeEvaporationPct=0.003` to ensure EDGE_EVAPORATION fires as fallback.
- GREEN phase: All 23 exit-evaluator tests pass after implementing fee-aware guard.

### Completion Notes List
- ✅ Task 1: Added `FinancialMath` import and `DEFAULT_KALSHI_FEE_SCHEDULE`/`DEFAULT_POLYMARKET_FEE_SCHEDULE` imports to `exit-evaluator.service.ts`
- ✅ Task 2: Replaced raw PnL guard in `isProfitCaptureTriggered()` with fee-aware guard: estimates exit fees via `FinancialMath.calculateTakerFeeRate()`, deducts entry fees + gas cost, checks `postFeePnl.gt(0)`
- ✅ Task 3: Verified all 18 existing tests pass unchanged (zero-fee positions degrade gracefully)
- ✅ Task 4: Added 5 new fee-aware guard tests covering: reject when raw PnL < fees, approve when raw PnL > fees, backward compat (zero fees), boundary (fees == PnL), negative raw PnL
- ✅ Task 5: Lint passes, 23/23 exit-evaluator tests pass, no regressions in full suite

### Change Log
- 2026-04-12: Implemented fee-aware PROFIT_CAPTURE P&L guard (10-95-14). 2 files modified, 5 tests added.

### File List
- `src/modules/backtesting/engine/exit-evaluator.service.ts` — Modified: added FinancialMath + fee schedule imports, replaced raw PnL guard with fee-aware guard in `isProfitCaptureTriggered()`
- `src/modules/backtesting/engine/exit-evaluator.service.spec.ts` — Modified: added test imports (calculateLegPnl, FinancialMath, fee schedules), added 5 new fee-aware guard tests
