# Story 10-96.1: Entry-Fee-Aware Exit PnL & Percentage Stop-Loss

Status: review

## Story

As an operator,
I want the live exit evaluation to account for entry fees and gas in PnL calculations, and to enforce a percentage-based stop-loss,
so that PROFIT_CAPTURE exits are profitable after all costs and catastrophic positions are exited early.

## Context

The backtest engine turned profitable after six critical algorithmic fixes (stories 10-95-8 through 10-95-14), validated across 5 runs with **+$2,026 P&L, 12.26 Sharpe, 1.67 profit factor**. Two of those fixes address the live exit evaluation pipeline:

1. **Entry fees + gas invisible in PnL** (10-95-9): `threshold-evaluator.service.ts` computes `currentPnl = kalshiPnl + polymarketPnl - exitFees`. Entry trading fees (~$4.5-5.5/position) and gas ($0.30-0.50/position) are never deducted. ~$800 of costs invisible across a backtest run.

2. **Fee-unaware PROFIT_CAPTURE** (10-95-14): Without fee awareness, 81 of 413 PROFIT_CAPTURE exits realized net losses — raw PnL was positive but smaller than total fees.

3. **No percentage stop-loss**: The current edge-relative SL (`SL_MULTIPLIER = -2`) scales with detected edge. Positions with miscalculated edge or slow bleed have no position-size-relative circuit breaker. In backtest, two STOP_LOSS triggers at 15% prevented -$168 in catastrophic losses.

The live engine is disabled (`return;` on line 65 of `trading-engine.service.ts`). All changes are safe to implement without live trading risk.

**Recalibration notes** (from sprint change proposal):

- The live threshold evaluator already deducts exit fees from `currentPnl` (correct)
- Entry fee data already exists on `OpenPosition` schema and flows through to `ThresholdEvalInput` (`entryKalshiFeeRate`, `entryPolymarketFeeRate`, `entryClosePriceKalshi`, `entryClosePricePolymarket`)
- These fields are currently consumed ONLY by `computeEntryCostBaseline()` (for SL/TP threshold shifts), NOT deducted from `currentPnl`

## Acceptance Criteria

1. **Given** an open position with entry fee data (`entryKalshiFeeRate`, `entryPolymarketFeeRate`, `entryClosePriceKalshi`, `entryClosePricePolymarket` all non-null)
   **When** `computeCommon()` computes `currentPnl`
   **Then** `currentPnl = kalshiPnl + polymarketPnl - exitFees - entryFees - gasCost`
   **And** `entryFees = (entryClosePriceKalshi * kalshiSize * entryKalshiFeeRate) + (entryClosePricePolymarket * polymarketSize * entryPolymarketFeeRate)`

2. **Given** a legacy position where any entry fee field is null
   **When** `computeCommon()` computes `currentPnl`
   **Then** `entryFees = 0` (graceful degradation, same behavior as `computeEntryCostBaseline`)
   **And** `currentPnl = kalshiPnl + polymarketPnl - exitFees - gasCost`

3. **Given** `exitStopLossPct` config setting (default 0.20) and a position in fixed exit mode
   **When** `currentPnl <= -(exitStopLossPct * legSize)`
   **Then** a `stop_loss` exit is triggered (highest priority in fixed mode, before edge-relative SL)

4. **Given** model or shadow exit mode
   **When** exit criteria are evaluated
   **Then** the corrected `currentPnl` (with entry fees + gas) flows through to all six criteria evaluations
   **And** no separate percentage stop-loss criterion is added (edge_evaporation handles the equivalent function)

5. **Given** `EXIT_STOP_LOSS_PCT` added to env schema, config-defaults, and EffectiveConfig
   **When** the exit-monitor reads config
   **Then** `exitStopLossPct` is passed through `ThresholdEvalInput` to the evaluator
   **And** `gasCost` is read from `DETECTION_GAS_ESTIMATE_USD` and passed through as `Decimal`

6. **Given** all existing tests
   **When** the test suite runs
   **Then** all tests pass (updating assertions where entry fees now affect PnL values)
   **And** new tests cover: entry fee deduction (with/without data), gas deduction, percentage SL trigger/non-trigger, legacy position graceful degradation

## Tasks / Subtasks

- [x] Task 1: Add `EXIT_STOP_LOSS_PCT` config infrastructure (AC: #3, #5)
  - [x] 1.1 In `src/common/config/env.schema.ts` (~line 281, after `EXIT_PROFIT_CAPTURE_RATIO`), add: `EXIT_STOP_LOSS_PCT: z.coerce.number().min(0.01).max(1).default(0.20),`
  - [x] 1.2 In `src/common/config/config-defaults.ts` (exit section ~line 310, after `exitProfitCaptureRatio`), add: `exitStopLossPct: { envKey: 'EXIT_STOP_LOSS_PCT', defaultValue: 0.20 },`
  - [x] 1.3 In `src/common/config/effective-config.types.ts` (~line 160, after `exitProfitCaptureRatio`), add: `exitStopLossPct: number;`
  - [x] 1.4 Tests: validate `EXIT_STOP_LOSS_PCT` Zod parsing (accepts 0.01-1, rejects 0 and >1, default 0.20). If a DTO test exists for exit config validation, add there; otherwise add to env schema tests.

- [x] Task 2: Expand `ThresholdEvalInput` interface (AC: #1, #3, #5)
  - [x] 2.1 In `src/modules/exit-management/threshold-evaluator.service.ts`, add to `ThresholdEvalInput` interface (~line 82, after existing optional fields):
    ```typescript
    /** Gas cost estimate in USD for the entry transaction (from DETECTION_GAS_ESTIMATE_USD) */
    gasCost?: Decimal;
    /** Percentage of position size for stop-loss circuit breaker (default 0.20 = 20%). Fixed mode only. */
    exitStopLossPct?: number;
    ```
  - [x] 2.2 Both fields are optional (`?`) for backward compatibility with any other callers of `evaluate()`

- [x] Task 3: Entry fee + gas deduction in `computeCommon()` (AC: #1, #2, #4)
  - [x] 3.1 In `computeCommon()` (~line 562, after `const currentPnl = kalshiPnl.plus(polymarketPnl).minus(totalExitFees)`), compute entry fees:
    ```typescript
    let totalEntryFees = new Decimal(0);
    if (
      params.entryClosePriceKalshi != null &&
      params.entryClosePricePolymarket != null &&
      params.entryKalshiFeeRate != null &&
      params.entryPolymarketFeeRate != null
    ) {
      const kalshiEntryFee = params.entryClosePriceKalshi.mul(kalshiSize).mul(params.entryKalshiFeeRate);
      const polyEntryFee = params.entryClosePricePolymarket.mul(polymarketSize).mul(params.entryPolymarketFeeRate);
      totalEntryFees = kalshiEntryFee.plus(polyEntryFee);
    }
    const gasCost = params.gasCost ?? new Decimal(0);
    ```
  - [x] 3.2 Update the `currentPnl` assignment: `const currentPnl = kalshiPnl.plus(polymarketPnl).minus(totalExitFees).minus(totalEntryFees).minus(gasCost);`
  - [x] 3.3 The null-check pattern (all four fields non-null or skip) matches `computeEntryCostBaseline()` behavior — legacy positions with null fields get `entryFees = 0`
  - [x] 3.4 Tests: (a) `currentPnl` deducts entry fees when all four fields present; (b) `currentPnl` skips entry fee deduction when any field is null; (c) `currentPnl` deducts `gasCost` when provided; (d) `currentPnl` uses `gasCost = 0` when not provided; (e) `currentPnl` deducts all three cost types simultaneously (exit + entry + gas)

- [x] Task 4: Percentage-based stop-loss in `evaluateFixed()` (AC: #3)
  - [x] 4.1 In `evaluateFixed()` (~line 209, BEFORE the existing edge-relative stop-loss check at line 211), add percentage-based circuit breaker. Use the same destructured variable names as the existing SL code (the method destructures `EvalCommon` fields — match the pattern: `currentPnl`, `currentEdge`, `capturedEdgePercent`, `legSize`, `scaledInitialEdge`, `entryCostBaseline` from `common`):
    ```typescript
    // Percentage-based stop-loss circuit breaker (10-96-1)
    const stopLossPct = new Decimal(params.exitStopLossPct ?? 0.2);
    const pctStopLossThreshold = legSize.mul(stopLossPct).neg();
    if (currentPnl.lte(pctStopLossThreshold)) {
      return {
        triggered: true,
        type: 'stop_loss',
        currentPnl,
        currentEdge,
        capturedEdgePercent,
      };
    }
    ```
  - [x] 4.2 This check runs BEFORE the existing edge-relative SL (`entryCostBaseline + scaledInitialEdge * SL_MULTIPLIER`). Both use the same `type: 'stop_loss'` return — the percentage SL is a wider circuit breaker for catastrophic losses. The edge-relative SL handles normal position management.
  - [x] 4.3 Tests: (a) percentage SL triggers when `currentPnl <= -(exitStopLossPct * legSize)`; (b) percentage SL does NOT trigger when `currentPnl > -(exitStopLossPct * legSize)`; (c) percentage SL takes priority over edge-relative SL — construct a case where both would trigger: e.g., `legSize=$100`, `exitStopLossPct=0.20`, `initialEdge=0.05`, `entryCostBaseline=Decimal(0)`, `scaledEdge=$5`, edge-relative threshold=`0 + 5*-2 = -$10`. Set `currentPnl = -$25`. Both trigger (`-25 <= -20` pct SL, `-25 <= -10` edge SL), but percentage fires first because it runs before; (d) with default 0.20 and $300 leg: triggers at currentPnl <= -$60; (e) boundary: exactly at threshold (`lte` is correct — triggers on equality)

- [x] Task 5: Wire new fields through `exit-monitor.service.ts` (AC: #5)
  - [x] 5.1 Add instance field: `private exitStopLossPct: number;` (~line 90, after other exit config fields)
  - [x] 5.2 In constructor (~line 97, after other exit config reads), read using `getConfigNumber` (MUST use `getConfigNumber` from `typed-config.helpers.ts` — NOT `configService.get<number>()` — to avoid incrementing the structural guard baseline count from story 10-96-0):
    ```typescript
    this.exitStopLossPct = getConfigNumber(this.configService, 'EXIT_STOP_LOSS_PCT', 0.2);
    ```
  - [x] 5.3 Add gas estimate field + read in constructor:
    ```typescript
    private gasEstimateUsd: Decimal;
    // In constructor:
    const gasRaw = this.configService.get<string>('DETECTION_GAS_ESTIMATE_USD') ?? '0.30';
    this.gasEstimateUsd = new Decimal(gasRaw);
    ```
  - [x] 5.4 In `reloadConfig()` (~line 140, after other field updates): first update the method's inline parameter type to include `exitStopLossPct?: number;` alongside the existing fields. Then add:
    ```typescript
    if (settings.exitStopLossPct !== undefined) {
      this.exitStopLossPct = settings.exitStopLossPct;
    }
    ```
  - [x] 5.5 In `buildCriteriaInputs()` (~line 748, after `profitCaptureRatio`), add to the returned `ThresholdEvalInput` object:
    ```typescript
    exitStopLossPct: this.exitStopLossPct,
    gasCost: this.gasEstimateUsd,
    ```
  - [x] 5.6 Import `getConfigNumber` from `../../common/config/typed-config.helpers`
  - [x] 5.7 Tests: (a) `buildCriteriaInputs` includes `exitStopLossPct` and `gasCost` in returned object; (b) `reloadConfig` updates `exitStopLossPct` when provided; (c) constructor reads correct defaults

- [x] Task 6: Update existing test fixtures (AC: #6)
  - [x] 6.1 In `threshold-evaluator.service.spec.ts`: update all test input fixtures to include `gasCost: new Decimal(0)` and `exitStopLossPct: 0.20` (or leave undefined — both fields are optional with defaults). Existing assertions for `currentPnl` must be updated ONLY for tests that provide non-null entry fee fields, since `currentPnl` now deducts entry fees.
  - [x] 6.2 In `exit-monitor.service.spec.ts`: update mock config/constructor to include `exitStopLossPct` and gas estimate. Update `buildCriteriaInputs` call expectations. Note: test files for exit-monitor are split across multiple spec files (`exit-monitor-core.spec.ts`, `exit-monitor-criteria.integration.spec.ts`, `exit-monitor-data-source.spec.ts`, `exit-monitor-shadow-emission.spec.ts`) — check all for fixtures that need updating.
  - [x] 6.3 Verify all existing tests pass after updates — entry fee deduction only affects tests with non-null entry fee fields. Tests with null entry fee fields are unaffected.
  - [x] 6.4 Add one model-mode verification test in `five-criteria-evaluator.spec.ts` or `threshold-evaluator.service.spec.ts`: confirm that `evaluateEdgeEvaporation` (C1) triggers sooner when entry fees are deducted (construct two inputs: identical except one has non-null entry fee fields, verify the one with entry fees has lower `currentPnl` and higher proximity to edge_evaporation threshold).

- [x] Task 7: Run lint + full test suite (AC: #6)
  - [x] 7.1 `cd pm-arbitrage-engine && pnpm lint` — fix any issues
  - [x] 7.2 `cd pm-arbitrage-engine && pnpm test` — all tests pass
  - [x] 7.3 Verify test count is baseline + new tests (baseline: 3825 from story 10-96-0)

## Dev Notes

**Line numbers are approximate** — always search by function/method name or string literal rather than relying on exact line numbers, as prior edits may have shifted them.

### Critical Implementation Details

**Entry fee formula uses EXISTING `ThresholdEvalInput` fields — no new input fields needed for entry fees.** The four entry fee fields (`entryClosePriceKalshi`, `entryClosePricePolymarket`, `entryKalshiFeeRate`, `entryPolymarketFeeRate`) are already on `ThresholdEvalInput` (lines 35-41), already populated by `exit-monitor.service.ts:buildCriteriaInputs()` (lines 718-729), and already converted from Prisma Decimal to decimal.js. They're currently consumed only by `FinancialMath.computeEntryCostBaseline()` (line 573). This story adds a second consumption point in `computeCommon()` for PnL deduction.

**No double-counting with `entryCostBaseline`.** `computeEntryCostBaseline` computes the MtM deficit at entry time (spread cost + what it would cost to exit at entry-time prices). The new entry fee deduction computes the actual trading fees paid to the platform when opening the position. These are conceptually different costs that happen to use similar input data. Both are real costs:

- `entryCostBaseline` shifts SL/TP thresholds down (your "zero" starts in a hole)
- Entry fee deduction makes `currentPnl` reflect actual costs (your P&L includes all trading costs)
  The combined effect correctly makes positions start with a larger unrealized loss, reflecting true economics.

**`entryKalshiFeeRate` is a close-side approximation, not the fill-side fee rate.** It was stored as `calculateTakerFeeRate(entryClosePriceKalshi)` for `computeEntryCostBaseline`. Using it for entry fee deduction gives `entryClosePrice * size * feeRate(closePrice)` instead of the ideal `entryFillPrice * size * feeRate(fillPrice)`. For Kalshi's formula (`0.07 * (1 - price)`), the difference between fill side and close side is typically 1-3 basis points — acceptable for PnL estimation.

**Percentage SL vs. edge-relative SL — different roles.** The existing edge-relative SL (`currentPnl <= entryCostBaseline + scaledInitialEdge * -2`) scales with detected edge. For a 5% edge on $300 leg, it triggers at approximately -$30 to -$39 depending on baseline. The new percentage SL at 20% triggers at -$60 for the same $300 leg. The percentage SL is a WIDER circuit breaker that catches catastrophic losses when edge was miscalculated or the edge-relative SL is too tight. Both can coexist — the percentage SL runs first and catches the worst cases.

**Gas cost uses `DETECTION_GAS_ESTIMATE_USD` (shared config).** The same gas cost applies to both entry evaluation (detection) and exit PnL accounting. No need for a separate `EXIT_GAS_ESTIMATE_USD` — the Polymarket on-chain gas cost is a system constant. Currently defaults to `'0.30'`, will be updated to `'0.50'` in story 10-96-4.

**`getConfigNumber` is MANDATORY for the new `EXIT_STOP_LOSS_PCT` read.** Story 10-96-0 added a structural guard test (`typed-config.guard.spec.ts`) that baseline-counts `configService.get<number>()` usages at 58. Adding a new `configService.get<number>()` call would increment to 59 and fail the guard. Use `getConfigNumber(this.configService, 'EXIT_STOP_LOSS_PCT', 0.20)` from `src/common/config/typed-config.helpers.ts` instead.

**`legSize` serves as `positionSizeUsd`.** `OpenPosition` does not have a `positionSizeUsd` field. Position sizes are in `ThresholdEvalInput` as `kalshiSize` and `polymarketSize`. `computeCommon()` already computes `legSize = params.kalshiSize` with an invariant check that both sides are equal. Use `legSize` for the percentage SL calculation.

**Model mode automatically benefits from corrected PnL.** Both `evaluateEdgeEvaporation()` (C1) and `evaluateProfitCapture()` (C6) use `common.currentPnl` from `computeCommon()`. With entry fees included, C1 becomes more conservative (triggers sooner) and C6 requires larger raw gains to fire (must overcome fees). This is correct behavior — no criterion-specific changes needed in model mode.

### File Impact Map

**Modify (config — 3 files):**

| File                                          | Lines | Change                                       |
| --------------------------------------------- | ----- | -------------------------------------------- |
| `src/common/config/env.schema.ts`             | ~285  | Add `EXIT_STOP_LOSS_PCT` with Zod validation |
| `src/common/config/config-defaults.ts`        | ~312  | Add `exitStopLossPct` entry                  |
| `src/common/config/effective-config.types.ts` | ~162  | Add `exitStopLossPct: number` field          |

**Modify (exit-management — 2 files):**

| File                                                         | Current Lines | Change                                                                                                                                              |
| ------------------------------------------------------------ | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/modules/exit-management/threshold-evaluator.service.ts` | 625           | Add 2 fields to `ThresholdEvalInput`, ~15 lines in `computeCommon()` for entry fee + gas deduction, ~8 lines in `evaluateFixed()` for percentage SL |
| `src/modules/exit-management/exit-monitor.service.ts`        | 914           | Add `exitStopLossPct` + `gasEstimateUsd` instance fields, constructor reads, `reloadConfig` handler, 2 fields in `buildCriteriaInputs` return       |

**Modify (tests — 2 files):**

| File                                                              | Change                                                                                                                                       |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/modules/exit-management/threshold-evaluator.service.spec.ts` | New tests for entry fee deduction (5), gas deduction (2), percentage SL (5). Update existing fixtures if they use non-null entry fee fields. |
| `src/modules/exit-management/exit-monitor.service.spec.ts`        | Update mock config, verify new fields passed, reloadConfig updates                                                                           |

### Architecture Compliance

- **Financial math:** ALL fee/PnL calculations use `decimal.js`. Entry fee formula: `entryClosePriceKalshi.mul(kalshiSize).mul(entryKalshiFeeRate)` — no native JS operators.
- **Error hierarchy:** Config validation uses Zod (env.schema.ts). No new runtime errors. If entry fee fields are null, graceful degradation (not an error).
- **Module boundaries:** All changes within `exit-management/` and `common/config/`. No new cross-module imports.
- **God object check:** `threshold-evaluator.service.ts` grows from 625 to ~648 lines (above 600 review trigger but below 800; the file is inherently complex — 6 criteria + fixed mode + shared computation). `exit-monitor.service.ts` grows from 914 to ~920 lines (already flagged; no decomposition in this story's scope).
- **Constructor injection:** No new DI dependencies. `exit-monitor.service.ts` already injects `ConfigService`. No new service injections in `threshold-evaluator.service.ts`.
- **Event emission:** No new events. Existing `ExitTriggeredEvent` carries the `type: 'stop_loss'` from the percentage SL — same as the existing edge-relative SL.
- **Paper/live mode:** The percentage SL and entry fee deduction apply identically to both paper and live positions. `exit-monitor.service.ts` already handles mode separation via `isPaper` parameter to `findByStatusWithOrders`. No mode-specific branching needed in this story.

### Previous Story Intelligence (10-96-0)

Key patterns established:

- **`getConfigNumber` usage:** Import from `../../common/config/typed-config.helpers`. Signature: `getConfigNumber(configService, key, defaultValue)`. Throws `SystemHealthError(4006)` if key is present but non-parseable.
- **Structural guard baseline:** `configService.get<number>` count is baselined at 58. Do NOT add new `configService.get<number>()` calls — use `getConfigNumber` instead.
- **Env schema completeness guard:** Any new env var used at runtime MUST be added to `env.schema.ts` or added to the allowlist with a TODO comment. Since we're adding `EXIT_STOP_LOSS_PCT` to env.schema.ts, no allowlist change needed.
- **Test count baseline:** 3825 tests pass (from 10-96-0 completion). This story should maintain that + new tests.

### What NOT To Do

- **Do NOT deduct entry fees from actual `realizedPnl` in `exit-execution.service.ts` or `position-close.service.ts`.** This story fixes the exit EVALUATION (threshold evaluator). Actual realized PnL recording is a separate concern. The live position close paths (`computeChunkPnl` in exit-execution, PnL formula in position-close) currently compute `realizedPnl = legPnl - exitFees` without entry fees — that's a known gap but outside this story's scope.
- **Do NOT add a percentage stop-loss criterion to model mode.** The sprint change proposal specifies fixed mode. Model mode's `edge_evaporation` criterion already handles the breakeven check and benefits from the corrected `currentPnl`.
- **Do NOT modify `computeEntryCostBaseline()` or `FinancialMath`.** The entry cost baseline is correct as-is. The entry fee deduction is a separate, additive correction to `currentPnl`.
- **Do NOT store `gasCost` per-position on `OpenPosition`.** Gas is a config-driven system estimate, not a per-position tracked value. Read from `DETECTION_GAS_ESTIMATE_USD` and pass through.
- **Do NOT add entry fee data to `ThresholdEvalResult`.** The result's `currentPnl` field will naturally reflect the corrected PnL. Dashboard and monitoring code consumes `currentPnl` directly — they'll see more accurate values without code changes.
- **Do NOT add `exitStopLossPct` to the Prisma `EngineConfig` model.** DB-configurable settings require ConfigAccessor integration. For now, env-var-only is sufficient. Dashboard settings page can be extended later if needed.
- **Do NOT migrate existing `configService.get<number>()` calls in `exit-monitor.service.ts` to `getConfigNumber`.** That's a separate debt item. Only use `getConfigNumber` for the NEW `EXIT_STOP_LOSS_PCT` read.

### Testing Standards

- **Co-located tests:** Changes to `threshold-evaluator.service.ts` tested in `threshold-evaluator.service.spec.ts` (same directory). Changes to `exit-monitor.service.ts` tested in `exit-monitor.service.spec.ts`.
- **Assertion depth:** Verify exact `currentPnl` values using `expect.objectContaining({ currentPnl: expect.any(Decimal) })` and then `expect(result.currentPnl.toNumber()).toBeCloseTo(expectedValue, 4)` or equivalent decimal comparison.
- **TDD cycle:** Write failing test first (entry fee deduction changes `currentPnl`), then implement, then refactor.
- **Financial math:** All test fixtures with monetary values use `new Decimal('...')` — NEVER native JS numbers for financial assertions.
- **Entry fee field fixtures:** Use realistic values: `entryClosePriceKalshi: new Decimal('0.44')`, `entryKalshiFeeRate: new Decimal('0.0392')`, `entryClosePricePolymarket: new Decimal('0.53')`, `entryPolymarketFeeRate: new Decimal('0.02')`.

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-13-live-engine-alignment.md — Story 10-96-1 scope, evidence, recalibrations]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-10-96-1 — AC and user story]
- [Source: _bmad-output/implementation-artifacts/10-95-9-backtest-exit-logic-pnl-fix.md — Backtest entry fee + stop-loss implementation]
- [Source: _bmad-output/implementation-artifacts/10-95-14-backtest-profit-capture-fee-aware-guard.md — Backtest fee-aware PROFIT_CAPTURE guard]
- [Source: _bmad-output/implementation-artifacts/10-96-0-structural-guards-configservice-route-prefix.md — getConfigNumber pattern, structural guard baselines]
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts:513-615 — computeCommon() PnL formula]
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts:199-268 — evaluateFixed() SL/TP/time checks]
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts:18-82 — ThresholdEvalInput interface]
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts:625-749 — buildCriteriaInputs() data flow]
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts:63-97 — Constructor config reads]
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts:101-149 — reloadConfig() method]
- [Source: pm-arbitrage-engine/src/common/config/env.schema.ts:269-281 — Exit env var definitions]
- [Source: pm-arbitrage-engine/src/common/config/config-defaults.ts:277-310 — Exit config defaults section]
- [Source: pm-arbitrage-engine/src/common/config/effective-config.types.ts:148-161 — Exit fields in EffectiveConfig]
- [Source: pm-arbitrage-engine/src/common/config/typed-config.helpers.ts — getConfigBoolean/getConfigNumber helpers]
- [Source: pm-arbitrage-engine/src/common/constants/exit-thresholds.ts:12 — SL_MULTIPLIER = -2]
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.ts:302-315 — calculateLegPnl()]
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.ts:115-125 — calculateTakerFeeRate()]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None.

### Completion Notes List

- All 7 tasks completed via TDD (Red-Green-Refactor cycle)
- 3838 tests pass (+13 from 3825 baseline). All failures are pre-existing e2e/integration (TimescaleDB, data-ingestion, app controller, logging — DB/network dependent)
- Structural guard tests pass: `configService.get<number>` baseline at 58 preserved (used `getConfigNumber` for new EXIT_STOP_LOSS_PCT read), env schema completeness guard satisfied
- Code review (Lad MCP, 3-layer): 1 finding deferred (gasEstimateUsd hot-reload — env-only value, not DB-configurable, consistent with existing architecture), 1 suggestion applied (clarifying comment on legSize semantics)
- Entry fee + gas deduction is additive with entryCostBaseline (no double-counting): baseline shifts SL/TP thresholds, entry fee deduction corrects currentPnl. Both are real costs.
- Percentage SL at 20% is a WIDER circuit breaker than edge-relative SL. Catches catastrophic losses when large baseline shifts edge-relative SL too far negative. Differentiating test proves this.

### File List

**Modified (config — 3 files):**

- `src/common/config/env.schema.ts` — Added `EXIT_STOP_LOSS_PCT` Zod validation
- `src/common/config/config-defaults.ts` — Added `exitStopLossPct` entry
- `src/common/config/effective-config.types.ts` — Added `exitStopLossPct: number` field

**Modified (exit-management — 2 files):**

- `src/modules/exit-management/threshold-evaluator.service.ts` — Added `gasCost`/`exitStopLossPct` to ThresholdEvalInput, entry fee + gas deduction in computeCommon(), percentage SL in evaluateFixed()
- `src/modules/exit-management/exit-monitor.service.ts` — Added `exitStopLossPct`/`gasEstimateUsd` instance fields, constructor reads (getConfigNumber + configService.get), reloadConfig handler, buildCriteriaInputs wiring

**Modified (tests — 3 files):**

- `src/common/config/env.schema.spec.ts` — +3 tests for EXIT_STOP_LOSS_PCT Zod validation
- `src/modules/exit-management/threshold-evaluator.service.spec.ts` — +11 tests (5 entry fee/gas, 6 percentage SL)
- `src/modules/exit-management/five-criteria-evaluator.spec.ts` — +1 model-mode entry fee impact test
- `src/modules/exit-management/exit-monitor-criteria.integration.spec.ts` — +2 wiring tests (exitStopLossPct/gasCost passthrough, reloadConfig)
