# Story 10-95.9: Backtest Exit Logic Fix & Full-Cost PnL Accounting

Status: complete

## Story

As an operator,
I want the backtest PROFIT_CAPTURE exit to verify actual position profitability before triggering, and realized P&L to include all trading costs (entry fees + gas),
so that backtest exit classifications are accurate and P&L reflects true economics.

## Context

Backtest run `e90b5698` (Mar 1–5, $10K bankroll) lost **-$937.90** (Sharpe -18.24, 10.5% win rate, profit factor 0.238) after Story 10-95-8 fixed zero-price contamination and added exit fees. Two remaining defects exposed by clean data:

1. **PROFIT_CAPTURE is direction-blind** — `exit-evaluator.service.ts:98-106` fires when `(entryEdge - currentEdge) / entryEdge >= 0.8`, but doesn't check which direction prices moved. ALL 39 PROFIT_CAPTURE exits were losers (avg -$9.23). In 84.6% of cases, Kalshi rose (adverse for short leg) while Polymarket barely moved. Edge convergence ≠ profitable convergence.

2. **Entry fees + gas omitted from PnL** — `backtest-portfolio.service.ts:240` computes `realizedPnl = kalshiPnl + polyPnl - exitFees`. Entry fees (~$4.5-5.5/position) and gas ($0.50/position) are never deducted. ~$800 of costs invisible.

This is the final story in Epic 10.95. After this fix, re-run Mar 1-5 backtest to validate the entire quality pipeline.

## Acceptance Criteria

1. **PROFIT_CAPTURE PnL guard** — `isProfitCaptureTriggered()` returns `true` ONLY when `capturedRatio >= exitProfitCapturePct` AND mark-to-market PnL > 0. MtM PnL computed via `calculateLegPnl()` for both legs. If `mtmPnl <= 0`, returns false (falls through to EDGE_EVAPORATION or other triggers).

2. **ExitEvaluationParams expansion** — Params include `kalshiCurrentPrice`, `polymarketCurrentPrice`, and `positionSizeUsd` (entry prices + sides already available via `params.position`). Uses existing `calculateLegPnl` from `common/utils/financial-math.ts`.

3. **Entry fee + gas tracking on openPosition()** — Computes entry fees for both legs using `FinancialMath.calculateTakerFeeRate()` with `DEFAULT_KALSHI_FEE_SCHEDULE` and `DEFAULT_POLYMARKET_FEE_SCHEDULE`. Stores `entryFees: Decimal` (sum of both legs) and `gasCost: Decimal` on `SimulatedPosition`.

4. **Full-cost PnL in closePosition()** — `realizedPnl = kalshiPnl + polyPnl - exitFees - entryFees - gasCost`. `fees` field = `entryFees + exitFees`. Capital tracking uses fully-net PnL: `availableCapital += positionSizeUsd + realizedPnl`.

5. **Minimum edge floor** — `edgeThresholdPct` default raised from 0.008 to 0.03. Config validation rejects values below 0.02 with descriptive error. Existing `maxEdgeThresholdPct` (15%) unchanged.

6. **STOP_LOSS exit condition** — Triggers when mark-to-market PnL drops below `-exitStopLossPct * positionSizeUsd` (default 15%). Priority between INSUFFICIENT_DEPTH (2) and PROFIT_CAPTURE (3). New `BacktestExitReason.STOP_LOSS` enum value via Prisma migration. Configurable via `exitStopLossPct` in `BacktestConfig` (default 0.15).

7. **Unrealized PnL update** — `calculateUnrealizedPnl()` includes entry fees + gas: `unrealizedPnl = kalshiMtmPnl + polyMtmPnl - estimatedExitFees - entryFees - gasCost`.

8. **Tests** — All existing tests pass (update assertions where entry fees/gas now affect PnL). New tests: PROFIT_CAPTURE positive/negative PnL paths, entry fee storage, full-cost PnL, STOP_LOSS trigger/non-trigger, edge threshold validation, unrealized PnL cost components.

## Tasks / Subtasks

- [x] Task 1: Add `entryFees` and `gasCost` fields to `SimulatedPosition` and `createSimulatedPosition()` (AC: #3)
  - [x] 1.1 Add `entryFees: Decimal` and `gasCost: Decimal` to `SimulatedPosition` interface in `simulation.types.ts:4-25`
  - [x] 1.2 Add `entryFees` and `gasCost` params to `createSimulatedPosition()` factory (lines 27-52), initialize from params
  - [x] 1.3 Tests: verify `createSimulatedPosition()` stores entry fees and gas cost

- [x] Task 2: Compute and store entry fees + gas on position open (AC: #3)
  - [x] 2.1 In `backtest-engine.service.ts:detectOpportunities()` (around line 623), BEFORE calling `createSimulatedPosition()`, compute entry fees:
    - `kalshiEntryFee = kalshiEntryPrice × positionSizeUsd × calculateTakerFeeRate(kalshiEntryPrice, DEFAULT_KALSHI_FEE_SCHEDULE)` (dynamic: `0.07 × (1 - price)`)
    - `polyEntryFee = polymarketEntryPrice × positionSizeUsd × calculateTakerFeeRate(polymarketEntryPrice, DEFAULT_POLYMARKET_FEE_SCHEDULE)` (flat 2%)
    - `entryFees = kalshiEntryFee + polyEntryFee`
  - [x] 2.2 Pass computed `entryFees` (Decimal) and `gasCost: gasEstimate` (already a Decimal in `detectOpportunities()`) to `createSimulatedPosition()`
  - [x] 2.3 Import `FinancialMath` and fee schedule constants in `backtest-engine.service.ts` (same imports used by `backtest-portfolio.service.ts`)
  - [x] 2.4 Tests: verify entry fees match manual calculation for known prices; verify gas cost stored correctly

- [x] Task 3: Full-cost PnL in `closePosition()` (AC: #4)
  - [x] 3.1 In `backtest-portfolio.service.ts:closePosition()` (line 240), change: `realizedPnl = kalshiPnl.plus(polyPnl).minus(totalFees).minus(position.entryFees).minus(position.gasCost)`
  - [x] 3.2 Update `fees` field on closed position: `fees = totalFees.plus(position.entryFees)` (exit + entry fees, gas separate)
  - [x] 3.3 Tests: verify `realizedPnl` is net of entry fees + exit fees + gas; verify `fees` includes both entry and exit

- [x] Task 4: PROFIT_CAPTURE PnL guard (AC: #1, #2)
  - [x] 4.1 Expand `ExitEvaluationParams` in `exit-evaluator.service.ts:9-19` with: `kalshiCurrentPrice: Decimal`, `polymarketCurrentPrice: Decimal`, `positionSizeUsd: Decimal`
  - [x] 4.2 In `isProfitCaptureTriggered()` (lines 98-106), after capturedRatio check, compute mtm PnL:
    ```
    const kalshiPnl = calculateLegPnl(params.position.kalshiSide.toLowerCase(), params.position.kalshiEntryPrice, params.kalshiCurrentPrice, params.positionSizeUsd)
    const polyPnl = calculateLegPnl(params.position.polymarketSide.toLowerCase(), params.position.polymarketEntryPrice, params.polymarketCurrentPrice, params.positionSizeUsd)
    return capturedRatio.gte(params.exitProfitCapturePct) && kalshiPnl.plus(polyPnl).gt(0)
    ```
  - [x] 4.3 Import `calculateLegPnl` from `../../../common/utils/financial-math`
  - [x] 4.4 Update caller in `backtest-engine.service.ts:evaluateExits()` (lines 523-535) to pass new params: `kalshiCurrentPrice: pairData.kalshiClose`, `polymarketCurrentPrice: pairData.polymarketClose`, `positionSizeUsd: position.positionSizeUsd`
  - [x] 4.5 Tests: PROFIT_CAPTURE fires when `capturedRatio >= 0.8` AND `mtmPnl > 0`; does NOT fire when `capturedRatio >= 0.8` but `mtmPnl <= 0` (adverse movement)

- [x] Task 5: STOP_LOSS exit condition (AC: #6)
  - [x] 5.1 Add `STOP_LOSS` to `BacktestExitReason` enum in `prisma/schema.prisma:641-648`. Run `pnpm prisma migrate dev --name add_stop_loss_exit_reason`
  - [x] 5.2 Add `exitStopLossPct` to `IBacktestConfig` in `common/interfaces/backtest-engine.interface.ts:3-23` (optional, default 0.15)
  - [x] 5.3 Add `exitStopLossPct` to `BacktestConfigDto` in `dto/backtest-config.dto.ts` with `@IsNumber() @Min(0.01) @Max(1)` validators, default 0.15
  - [x] 5.4 Renumber `EXIT_PRIORITY` map: RESOLUTION_FORCE_CLOSE=1, INSUFFICIENT_DEPTH=2, STOP_LOSS=3, PROFIT_CAPTURE=4, EDGE_EVAPORATION=5, TIME_DECAY=6, SIMULATION_END=7
  - [x] 5.5 Add `exitStopLossPct: Decimal` to `ExitEvaluationParams`
  - [x] 5.6 Add `isStopLossTriggered()` method: compute mtm PnL same as PROFIT_CAPTURE guard, return `true` if `mtmPnl <= -exitStopLossPct * positionSizeUsd`
  - [x] 5.7 Wire into `evaluateExits()` between INSUFFICIENT_DEPTH and PROFIT_CAPTURE checks
  - [x] 5.8 Update caller in `backtest-engine.service.ts:evaluateExits()` to pass `exitStopLossPct: new Decimal(config.exitStopLossPct ?? 0.15)`
  - [x] 5.9 Tests: STOP_LOSS triggers at threshold; does NOT trigger above threshold; priority ordering correct (INSUFFICIENT_DEPTH > STOP_LOSS > PROFIT_CAPTURE)

- [x] Task 6: Minimum edge threshold floor (AC: #5)
  - [x] 6.1 Change `edgeThresholdPct` default from `0.008` to `0.03` in `BacktestConfigDto` (line 24)
  - [x] 6.2 Change `@Min(0.001)` to `@Min(0.02)` on `edgeThresholdPct` validator
  - [x] 6.3 Tests: config validation rejects `edgeThresholdPct: 0.01` with descriptive error; accepts `0.02` and `0.03`

- [x] Task 7: Unrealized PnL update (AC: #7)
  - [x] 7.1 Update `calculateUnrealizedPnl()` in `backtest-portfolio.service.ts:27-45` — the function already receives the `SimulatedPosition` (which now has `entryFees` and `gasCost` fields). Add estimated exit fee calculation (same pattern as `closePosition()`), then: `unrealizedPnl = kalshiPnl + polyPnl - estimatedExitFees - position.entryFees - position.gasCost`. Need two additional params: `lastKalshiPrice` and `lastPolymarketPrice` are already passed — use them for exit fee estimation.
  - [x] 7.2 Callers pass the updated `SimulatedPosition` object which now includes `entryFees`/`gasCost` — no caller signature changes needed. Verify: `updateEquity()` in `backtest-engine.service.ts` and `backtest-persistence.helper.ts`
  - [x] 7.3 Tests: unrealized PnL includes all cost components

- [x] Task 8: Update existing tests (AC: #8)
  - [x] 8.1 Update `exit-evaluator.service.spec.ts` — all test fixtures must include new `ExitEvaluationParams` fields (`kalshiCurrentPrice`, `polymarketCurrentPrice`, `positionSizeUsd`, `exitStopLossPct`)
  - [x] 8.2 Update `backtest-portfolio.service.spec.ts` — assertions for `realizedPnl`, `fees`, and `unrealizedPnl` must account for entry fees + gas
  - [x] 8.3 Update `backtest-engine.service.spec.ts` — mocks/call expectations for `evaluateExits()` and `openPosition()` must include new params
  - [x] 8.4 Update `backtest-config.dto.spec.ts` — existing edge threshold tests may need adjustment for new min (0.02)
  - [x] 8.5 Update all `__fixtures__/scenarios/*.fixture.json` files — any with `edgeThresholdPct: 0.008` must be raised to `0.03` (or at minimum `0.02`) to pass validation with new floor
  - [x] 8.6 Update test fixture factories in `backtest-portfolio.service.spec.ts` and `exit-evaluator.service.spec.ts` to include default `entryFees: new Decimal(0)` and `gasCost: new Decimal(0)` on all `SimulatedPosition` objects

## Dev Notes

**Line numbers are approximate** — always search by function/method name rather than relying on exact line numbers, as prior edits may have shifted them.

### Critical Implementation Details

**PROFIT_CAPTURE fix is ~5 lines.** The existing `isProfitCaptureTriggered()` at `exit-evaluator.service.ts:98-106` just needs a PnL guard after the capturedRatio check. `calculateLegPnl()` already exists in `common/utils/financial-math.ts:302-315` — import and use it, do NOT duplicate.

**Entry fee pattern mirrors 10-95-8's exit fee.** Story 10-95-8 added exit fee deduction using `FinancialMath.calculateTakerFeeRate()` with platform fee schedules. Entry fees use the identical pattern with entry prices instead of exit prices. The fee schedules:
- `DEFAULT_KALSHI_FEE_SCHEDULE` at `src/modules/backtesting/utils/fee-schedules.ts:7-16` — Dynamic: `0.07 × (1 - P)`
- `DEFAULT_POLYMARKET_FEE_SCHEDULE` at `src/modules/backtesting/utils/fee-schedules.ts:18-23` — Flat 2%

**10-95-8 explicitly deferred entry fees.** Previous change proposal stated: *"Entry fees are already captured in calculateNetEdge()."* This conflates two concerns — edge governs entry decisions, PnL must reflect actual costs. They serve different purposes.

**EXIT_PRIORITY renumbering.** The existing map at `exit-evaluator.service.ts:22-29` uses integers 1-6. Renumber to insert STOP_LOSS: RESOLUTION_FORCE_CLOSE=1, INSUFFICIENT_DEPTH=2, STOP_LOSS=3, PROFIT_CAPTURE=4, EDGE_EVAPORATION=5, TIME_DECAY=6, SIMULATION_END=7. Tests referencing priority numbers must be updated accordingly.

**openPosition() needs gasEstimateUsd.** Currently `openPosition()` in `backtest-portfolio.service.ts` doesn't receive gas config. The value comes from `config.gasEstimateUsd` (string, default "0.50"). Convert to Decimal and pass through. The calling code in `detectOpportunities()` at `backtest-engine.service.ts:559-639` already has `gasEstimate: Decimal` available.

**calculateUnrealizedPnl() is a standalone exported function** (not a service method) at `backtest-portfolio.service.ts:27-45`. It currently takes `(position, lastKalshiPrice, lastPolymarketPrice)` and returns raw leg PnL without fees. Add estimated exit fees (matching `closePosition()` pattern) plus entry fees + gas from the position object.

**Prisma migration is additive-only.** Adding `STOP_LOSS` to `BacktestExitReason` enum. No column changes needed — `exit_reason` column already accepts nullable enum. Run: `cd pm-arbitrage-engine && pnpm prisma migrate dev --name add_stop_loss_exit_reason`. Then `pnpm prisma generate`.

### File Impact Map

**Modify (engine logic):**
| File | Lines | Change |
|------|-------|--------|
| `src/modules/backtesting/types/simulation.types.ts` | 101 | Add `entryFees`, `gasCost` to `SimulatedPosition` + `createSimulatedPosition()` |
| `src/modules/backtesting/engine/exit-evaluator.service.ts` | 120 | Expand `ExitEvaluationParams`, PnL guard on PROFIT_CAPTURE, add STOP_LOSS, import `calculateLegPnl` |
| `src/modules/backtesting/engine/backtest-portfolio.service.ts` | 552 | Entry fee calc in `openPosition()`, full-cost PnL in `closePosition()`, unrealized PnL update |
| `src/modules/backtesting/engine/backtest-engine.service.ts` | 712 | Pass new params to `evaluateExits()`, pass gas to `openPosition()` |
| `src/modules/backtesting/dto/backtest-config.dto.ts` | 105 | Add `exitStopLossPct`, change `edgeThresholdPct` default + min |
| `src/common/interfaces/backtest-engine.interface.ts` | 23 | Add `exitStopLossPct` to `IBacktestConfig` |

**Modify (Prisma):**
| File | Change |
|------|--------|
| `prisma/schema.prisma` (line 641-648) | Add `STOP_LOSS` to `BacktestExitReason` enum |
| New migration file | Additive enum ALTER TYPE |

**Modify (tests):**
| File | Lines | Change |
|------|-------|--------|
| `src/modules/backtesting/engine/exit-evaluator.service.spec.ts` | 284 | New params in fixtures, PROFIT_CAPTURE PnL guard tests, STOP_LOSS tests |
| `src/modules/backtesting/engine/backtest-portfolio.service.spec.ts` | 903 | Entry fee tests, full-cost PnL assertions, unrealized PnL tests |
| `src/modules/backtesting/engine/backtest-engine.service.spec.ts` | ~700 | Updated mock calls for new params |
| `src/modules/backtesting/dto/backtest-config.dto.spec.ts` | ~60 | Edge threshold min validation, stopLossPct validation |

**Potentially affected (callers to verify):**
| File | Why |
|------|-----|
| `src/modules/backtesting/engine/backtest-persistence.helper.ts` | Calls `calculateUnrealizedPnl()` for open position reporting |
| `src/modules/backtesting/engine/chunked-data-loading.service.ts` | Orchestrates chunks; verify no direct exit/PnL coupling |
| `src/modules/backtesting/engine/walk-forward-routing.service.ts` | Delegates to engine; verify no direct exit/PnL coupling |

### Architecture Compliance

- **Financial math:** ALL fee/PnL calculations use `decimal.js` — NEVER native JS operators. Convert Prisma Decimal via `new Decimal(value.toString())`.
- **Error hierarchy:** Config validation errors use class-validator decorators (existing pattern). Any runtime errors extend SystemError.
- **Module boundaries:** All changes are within `modules/backtesting/` and `common/`. No cross-module imports added.
- **God object check:** `exit-evaluator.service.ts` grows from 120→~160 lines (well under 300 limit). `backtest-portfolio.service.ts` at 552 grows by ~20 lines (under 600 trigger). `backtest-engine.service.ts` at 712 grows by ~5 lines (existing facade justification from 10-95-4).
- **Event emission:** No new events required. Existing `BacktestPositionClosedEvent` carries the updated `realizedPnl` and `fees` values.
- **Naming:** `exitStopLossPct` follows existing pattern: `exitEdgeEvaporationPct`, `exitTimeLimitHours`, `exitProfitCapturePct`.

### Previous Story Intelligence (10-95-8)

Key patterns established in 10-95-8 to follow:
- **Fee formula:** `exitPrice × positionSizeUsd × takerFeeRate(price, schedule)` — same formula for entry fees, just swap exit→entry prices
- **Import paths:** `FinancialMath` from `'../../../common/utils/financial-math'`, fee schedules from `'../utils/fee-schedules'`
- **Defense-in-depth:** SQL-level filter + TypeScript guard pattern (applicable: validate `entryFees.gte(0)` after computation)
- **Config validation:** `@IsNumber() @Min() @Max()` pattern with `@IsOptional()` for backward compat
- **Test count baseline:** 3706 tests pass. This story should maintain that + new tests

### What NOT To Do

- **Do NOT add entry fees in `calculateNetEdge()`** — entry fees are already subtracted there for threshold decisions. PnL accounting is a separate concern.
- **Do NOT modify the dashboard** — no new UI elements in this story. The existing position detail view and metrics panels display whatever PnL/fee values the engine stores.
- **Do NOT modify `BacktestPosition` Prisma model columns** — the existing `fees Decimal?` and `realized_pnl Decimal?` columns are sufficient. Entry fees are included in `fees` total; gas is absorbed into `realizedPnl`.
- **Do NOT change the `calculateLegPnl()` function** — it's correct as-is. Use it as-is for the PnL guard.
- **Do NOT add `entryFees`/`gasCost` columns to Prisma** — these are simulation-time fields on the in-memory `SimulatedPosition` interface. The persisted `BacktestPosition` stores the final `fees` total and `realizedPnl` which already includes these costs.

### References

- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-10-backtest-exit-logic-pnl-fix.md`] — Full course correction with evidence table and trade-off analysis
- [Source: `_bmad-output/planning-artifacts/epics.md#Epic-10.95`, Story 10-95-9] — AC and task definitions
- [Source: `_bmad-output/implementation-artifacts/10-95-8-backtest-zero-price-fee-fix.md`] — Previous story with fee pattern, file list, learnings
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/exit-evaluator.service.ts:98-106`] — PROFIT_CAPTURE bug location
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-portfolio.service.ts:240`] — PnL calculation bug location
- [Source: `pm-arbitrage-engine/src/common/utils/financial-math.ts:302-315`] — `calculateLegPnl()` to reuse
- [Source: `pm-arbitrage-engine/src/modules/backtesting/utils/fee-schedules.ts`] — Fee schedule constants

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
N/A — no debugging issues encountered.

### Completion Notes List
- TDD approach: all tests written RED first, then production code for GREEN
- Baseline: 3707 tests passing → Final: 3722 tests passing (+15 new tests)
- Pre-existing e2e failures (4) unchanged — DB-dependent, not related to this story
- Prisma migration `add_stop_loss_exit_reason` created (additive enum only)
- `edgeThresholdPct` raised from 0.008→0.03 required updating test data in backtest-engine.service.spec.ts (`setupDataWithEdge` prices widened from K=0.40/P=0.55 to K=0.35/P=0.58) to ensure net edge exceeds new 3% threshold
- `calculateUnrealizedPnl` now includes estimated exit fees, entry fees, and gas — all existing unrealized PnL test assertions updated accordingly
- EXIT_PRIORITY renumbered: STOP_LOSS=3 inserted, PROFIT_CAPTURE→4, EDGE_EVAPORATION→5, TIME_DECAY→6, SIMULATION_END→7

### File List
**Modified (engine logic):**
- `src/modules/backtesting/types/simulation.types.ts` — Added `entryFees`, `gasCost` to `SimulatedPosition` interface and `createSimulatedPosition()` factory
- `src/modules/backtesting/engine/exit-evaluator.service.ts` — Expanded `ExitEvaluationParams`, PnL guard on PROFIT_CAPTURE, added STOP_LOSS, renumbered EXIT_PRIORITY
- `src/modules/backtesting/engine/backtest-portfolio.service.ts` — Full-cost PnL in `closePosition()`, updated `calculateUnrealizedPnl()` with estimated exit fees + entry fees + gas
- `src/modules/backtesting/engine/backtest-engine.service.ts` — Entry fee computation in `detectOpportunities()`, pass new params to `evaluateExits()`
- `src/modules/backtesting/dto/backtest-config.dto.ts` — Added `exitStopLossPct`, changed `edgeThresholdPct` default (0.008→0.03) and min (0.001→0.02)
- `src/common/interfaces/backtest-engine.interface.ts` — Added `exitStopLossPct` to `IBacktestConfig`

**Modified (Prisma):**
- `prisma/schema.prisma` — Added `STOP_LOSS` to `BacktestExitReason` enum
- `prisma/migrations/*_add_stop_loss_exit_reason/migration.sql` — Additive enum ALTER TYPE

**Modified (tests):**
- `src/modules/backtesting/types/simulation.types.spec.ts` — 2 new tests for entryFees/gasCost
- `src/modules/backtesting/engine/exit-evaluator.service.spec.ts` — Refactored with `makeParams` helper, 5 new tests (PROFIT_CAPTURE PnL guard, STOP_LOSS trigger/non-trigger/priority)
- `src/modules/backtesting/engine/backtest-portfolio.service.spec.ts` — 3 new tests (full-cost PnL, entry fees in fees total, unrealized PnL with costs), updated existing assertions
- `src/modules/backtesting/engine/backtest-engine.service.spec.ts` — Updated mockConfig, setupDataWithEdge prices, mock position fixtures, unrealized PnL assertions
- `src/modules/backtesting/dto/backtest-config.dto.spec.ts` — 6 new tests (edge threshold floor, exitStopLossPct validation)
- `src/modules/backtesting/__fixtures__/scenarios/*.fixture.json` (6 files) — Updated `edgeThresholdPct` 0.008→0.03

**Modified (other test files — edgeThresholdPct update):**
- `src/common/events/backtesting.events.spec.ts`
- `src/modules/backtesting/reporting/sensitivity-analysis.service.spec.ts`
- `src/modules/backtesting/engine/chunked-data-loading.service.spec.ts`
- `src/modules/backtesting/reporting/calibration-report.integration.spec.ts`
- `src/modules/backtesting/engine/walk-forward-routing.service.spec.ts`
- `src/modules/backtesting/engine/backtest-state-machine.service.spec.ts`
