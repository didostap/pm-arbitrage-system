# Story 10-95.13: Backtest Entry Liquidity Filter & Stop-Loss Recalibration

Status: done

## Story

As an operator,
I want the backtest engine to reject entry into positions where one platform shows stale or illiquid pricing, and I want a tighter stop-loss validation range,
so that the simulation avoids illusory edges from liquidity asymmetry and cuts losses faster on diverging positions.

## Context

In backtest run `2d2f84ac` (Mar 1 – Apr 30, $10K bankroll, post-10-95-12 validation), 8 STOP_LOSS exits (-$736) and 106 diverged TIME_DECAY exits (-$1,338) share the same root cause: one platform's price is stale/flat while the other moves dramatically. All 8 stop-loss pairs verified against `contract_matches` — descriptions and CLOB token IDs match correctly. These are NOT contract matching errors. The apparent "edge" is illusory because one platform has no real market activity (e.g., Polymarket at $0.002 with zero price movement).

Pattern observed across all 8 STOP_LOSS positions:
- One platform moves 30-63 cents, the other moves 0-0.5 cents
- Exit edge EXCEEDS entry edge (divergence, not convergence)
- Average price gap at entry: $0.12 (vs $0.11 for profitable trades)

62 of 106 diverged TIME_DECAY positions show identical one-sided flat-price movement (51 Polymarket flat, 11 Kalshi flat).

Combined recoverable P&L: ~$2,074 from these two categories. Entry liquidity filters plus tighter stop-loss are estimated to reduce TIME_DECAY losses from -$1,338 to ~$200-300.

## Acceptance Criteria

1. **Given** a candidate entry opportunity **when** either platform's price is below `minEntryPricePct` (default 0.05) **then** the entry is skipped and a counter is incremented in the calibration report.

2. **Given** a candidate entry opportunity **when** the absolute price gap between platforms (`|kalshiPrice - polymarketPrice|`) exceeds `maxEntryPriceGapPct` (default 0.25) **then** the entry is skipped and a counter is incremented.

3. **Given** `exitStopLossPct` configuration **when** validation is applied **then** the range is `@Min(0.05) @Max(0.50)` (was `@Min(0.01) @Max(1)`). Default remains `0.15` (already set by story 10-95-9).

4. **Given** filtered entries **when** the calibration report is generated **then** a new "Liquidity Filters" section in `DataQualitySummary` shows: total candidates evaluated, entries rejected by min-price filter (with per-platform breakdown), entries rejected by price-gap filter, and the configured thresholds.

5. **Given** existing tests **when** all run **then** all pass. New tests: min-price filter rejects below threshold, allows above; price-gap filter rejects above threshold, allows below; stop-loss validation at new range; filter counters accumulate correctly across chunks; all filters are configurable and independently disablable (value 0 disables).

## Tasks / Subtasks

- [x] Task 1: Add `minEntryPricePct` and `maxEntryPriceGapPct` to `IBacktestConfig` and `BacktestConfigDto` (AC: #1, #2, #3)
  - [x] 1.1 In `src/common/interfaces/backtest-engine.interface.ts:24`, after `cooldownHours?: number;`, add:
    ```typescript
    minEntryPricePct?: number;
    maxEntryPriceGapPct?: number;
    ```
  - [x] 1.2 In `src/modules/backtesting/dto/backtest-config.dto.ts`, after the `cooldownHours` field (line 114), add:
    ```typescript
    @IsOptional()
    @IsNumber()
    @Min(0)
    minEntryPricePct: number = 0.05;

    @IsOptional()
    @IsNumber()
    @Min(0)
    @Max(1)
    maxEntryPriceGapPct: number = 0.25;
    ```
  - [x] 1.3 In the same file, update `exitStopLossPct` validation (line 107-108): change `@Min(0.01)` to `@Min(0.05)` and `@Max(1)` to `@Max(0.50)`.
  - [x] 1.4 **Test impact:** The existing test `[P1] exitStopLossPct rejects value below 0.01` (line 386) tests `0.005` which will still be rejected by `@Min(0.05)`, but the test description is now misleading. Update the test title and add a test for the new boundary (e.g., `0.04` rejected, `0.05` accepted). Similarly add a test for the new `@Max(0.50)` boundary.

- [x] Task 2: Add DTO + interface tests for new config params (AC: #1, #2, #5)
  - [x] 2.1 In `src/modules/backtesting/dto/backtest-config.dto.spec.ts`, after the `cooldownHours` tests (around line 440), add:
    ```
    // 10-95-13: minEntryPricePct
    [P0] minEntryPricePct defaults to 0.05 — plainToInstance, verify dto.minEntryPricePct === 0.05
    [P1] minEntryPricePct accepts 0 (disabled) — set 0, no validation error
    [P1] minEntryPricePct accepts custom value — set 0.10, no validation error
    [P1] minEntryPricePct rejects negative — set -0.01, expect validation error

    // 10-95-13: maxEntryPriceGapPct
    [P0] maxEntryPriceGapPct defaults to 0.25 — plainToInstance, verify dto.maxEntryPriceGapPct === 0.25
    [P1] maxEntryPriceGapPct accepts 0 (disabled) — set 0, no validation error
    [P1] maxEntryPriceGapPct accepts custom value — set 0.50, no validation error
    [P1] maxEntryPriceGapPct rejects negative — set -0.01, expect validation error
    [P1] maxEntryPriceGapPct rejects value above 1.0 — set 1.01, expect validation error

    // 10-95-13: exitStopLossPct validation range tightened
    [P1] exitStopLossPct rejects value below 0.05 — set 0.04, expect validation error
    [P1] exitStopLossPct accepts 0.05 (new minimum) — set 0.05, no validation error
    [P1] exitStopLossPct rejects value above 0.50 — set 0.51, expect validation error
    [P1] exitStopLossPct accepts 0.50 (new maximum) — set 0.50, no validation error
    ```
  - [x] 2.2 Add IBacktestConfig conformance tests (follow the `depthCacheBudgetMb` / `cooldownHours` pattern at lines 493-516 / 442-465):
    ```
    [P0] IBacktestConfig includes optional minEntryPricePct: number — create literal with minEntryPricePct: 0.10, assert === 0.10
    [P0] IBacktestConfig includes optional maxEntryPriceGapPct: number — create literal with maxEntryPriceGapPct: 0.30, assert === 0.30
    ```
  - [x] 2.3 Update existing test `[P1] exitStopLossPct rejects value below 0.01` (line 386) — change title to `rejects value below 0.05` and test value to `0.04` (aligns with new `@Min(0.05)`).

- [x] Task 3: Add liquidity filter counters to `RunningAccumulators` (AC: #4)
  - [x] 3.1 In `src/modules/backtesting/engine/backtest-portfolio.service.ts`, extend `RunningAccumulators` interface (after `polyZeroCount: number;` at line 106):
    ```typescript
    /** Liquidity filter metrics — accumulated per chunk from detectOpportunities */
    liquidityFilterTotalCandidates: number;
    liquidityFilterMinPriceRejected: number;
    liquidityFilterMinPriceKalshi: number;
    liquidityFilterMinPricePoly: number;
    liquidityFilterPriceGapRejected: number;
    ```
  - [x] 3.2 Initialize all five counters to `0` in `initialize()` (after `polyZeroCount: 0,` at line 184) and in `reset()` (after `polyZeroCount: 0,` at line 507).
  - [x] 3.3 Add accumulation method after `getZeroExclusionCounts()` (after line 479):
    ```typescript
    addLiquidityFilterCounts(
      runId: string,
      totalCandidates: number,
      minPriceRejected: number,
      minPriceKalshi: number,
      minPricePoly: number,
      priceGapRejected: number,
    ): void {
      const ctx = this.getRunContext(runId);
      ctx.accumulators.liquidityFilterTotalCandidates += totalCandidates;
      ctx.accumulators.liquidityFilterMinPriceRejected += minPriceRejected;
      ctx.accumulators.liquidityFilterMinPriceKalshi += minPriceKalshi;
      ctx.accumulators.liquidityFilterMinPricePoly += minPricePoly;
      ctx.accumulators.liquidityFilterPriceGapRejected += priceGapRejected;
    }
    ```
  - [x] 3.4 Add retrieval method:
    ```typescript
    getLiquidityFilterCounts(runId: string): {
      totalCandidates: number;
      minPriceRejected: number;
      minPriceKalshi: number;
      minPricePoly: number;
      priceGapRejected: number;
    } {
      const ctx = this.getRunContext(runId);
      return {
        totalCandidates: ctx.accumulators.liquidityFilterTotalCandidates,
        minPriceRejected: ctx.accumulators.liquidityFilterMinPriceRejected,
        minPriceKalshi: ctx.accumulators.liquidityFilterMinPriceKalshi,
        minPricePoly: ctx.accumulators.liquidityFilterMinPricePoly,
        priceGapRejected: ctx.accumulators.liquidityFilterPriceGapRejected,
      };
    }
    ```

- [x] Task 4: Add portfolio service accumulator tests (AC: #4, #5)
  - [x] 4.1 In `src/modules/backtesting/engine/backtest-portfolio.service.spec.ts`, after the `addZeroExclusionCounts()` describe block (around line 370), add:
    ```
    describe('addLiquidityFilterCounts()')
      [P0] accumulates liquidity filter counts across multiple calls — call twice with different values, verify totals via getLiquidityFilterCounts()
      [P0] reset() clears liquidity filter counters — add counts, reset, verify all zero
      [P1] getLiquidityFilterCounts() returns zero for fresh run — initialize, get counts, verify all zero
    ```
  - [x] 4.2 Follow the exact pattern of the `addZeroExclusionCounts` tests at lines 353-370.

- [x] Task 5: Implement entry filtering in `detectOpportunities()` (AC: #1, #2)
  - [x] 5.1 In `src/modules/backtesting/engine/backtest-engine.service.ts`, in `runSimulationLoop()` after `cooldownMap` initialization (line 435), add:
    ```typescript
    const minEntryPrice = new Decimal(config.minEntryPricePct ?? 0.05);
    const maxEntryPriceGap = new Decimal(config.maxEntryPriceGapPct ?? 0.25);
    const liquidityFilterCounts = {
      totalCandidates: 0,
      minPriceRejected: 0,
      minPriceKalshi: 0,
      minPricePoly: 0,
      priceGapRejected: 0,
    };
    ```
  - [x] 5.2 Pass `minEntryPrice`, `maxEntryPriceGap`, and `liquidityFilterCounts` to `detectOpportunities()`. Update the call site (line 459-471) and method signature (line 588-599) to add three new parameters:
    ```typescript
    minEntryPrice: Decimal,
    maxEntryPriceGap: Decimal,
    liquidityFilterCounts: { totalCandidates: number; minPriceRejected: number; minPriceKalshi: number; minPricePoly: number; priceGapRejected: number },
    ```
  - [x] 5.3 In `detectOpportunities()`, after the cooldown check block (line 624) and before position size calculation (line 626), add:
    ```typescript
    // Entry liquidity filters — reject stale/illiquid pricing (10-95-13)
    liquidityFilterCounts.totalCandidates++;

    if (minEntryPrice.gt(0)) {
      const kalshiBelowMin = pairData.kalshiClose.lt(minEntryPrice);
      const polyBelowMin = pairData.polymarketClose.lt(minEntryPrice);
      if (kalshiBelowMin || polyBelowMin) {
        liquidityFilterCounts.minPriceRejected++;
        if (kalshiBelowMin) liquidityFilterCounts.minPriceKalshi++;
        if (polyBelowMin) liquidityFilterCounts.minPricePoly++;
        continue;
      }
    }

    if (maxEntryPriceGap.gt(0)) {
      const priceGap = pairData.kalshiClose.minus(pairData.polymarketClose).abs();
      if (priceGap.gt(maxEntryPriceGap)) {
        liquidityFilterCounts.priceGapRejected++;
        continue;
      }
    }
    ```
  - [x] 5.4 After the simulation loop in `runSimulationLoop()` (after line 475, before `}`), accumulate the counters:
    ```typescript
    this.portfolioService.addLiquidityFilterCounts(
      runId,
      liquidityFilterCounts.totalCandidates,
      liquidityFilterCounts.minPriceRejected,
      liquidityFilterCounts.minPriceKalshi,
      liquidityFilterCounts.minPricePoly,
      liquidityFilterCounts.priceGapRejected,
    );
    ```

- [x] Task 6: Extend calibration report pipeline with liquidity filter metrics (AC: #4)
  - [x] 6.1 In `src/modules/backtesting/types/calibration-report.types.ts`, extend `DataQualitySummary` (after `perPlatformExclusion?` at line 55):
    ```typescript
    liquidityFilter?: {
      totalCandidates: number;
      minPriceRejected: number;
      minPriceKalshi: number;
      minPricePoly: number;
      priceGapRejected: number;
      configuredMinPrice: number;
      configuredMaxGap: number;
    };
    ```
  - [x] 6.2 In `src/modules/backtesting/reporting/calibration-report.service.ts`, extend `generateReport()` signature (line 43) to accept an optional `liquidityFilter` parameter after `zeroExclusion`:
    ```typescript
    async generateReport(
      runId: string,
      zeroExclusion?: { ... },
      liquidityFilter?: {
        totalCandidates: number;
        minPriceRejected: number;
        minPriceKalshi: number;
        minPricePoly: number;
        priceGapRejected: number;
        configuredMinPrice: number;
        configuredMaxGap: number;
      },
    ): Promise<CalibrationReport>
    ```
  - [x] 6.3 Pass `liquidityFilter` through to `buildDataQualitySummary()`. In that method (line 325), add after the zero exclusion block (line 383):
    ```typescript
    if (liquidityFilter && liquidityFilter.totalCandidates > 0) {
      summary.liquidityFilter = liquidityFilter;
    }
    ```
  - [x] 6.4 In `src/modules/backtesting/engine/walk-forward-routing.service.ts`, extend `generateCalibrationReport()` (line 267) to accept and pass through the `liquidityFilter` parameter:
    ```typescript
    async generateCalibrationReport(
      runId: string,
      zeroExclusion?: { ... },
      liquidityFilter?: { ... },
    ): Promise<void> {
      // ...
      await this.calibrationReportService.generateReport(runId, zeroExclusion, liquidityFilter);
    }
    ```
  - [x] 6.5 In `src/modules/backtesting/engine/backtest-engine.service.ts`, at the report generation call (line 368-372), retrieve and pass liquidity filter counts:
    ```typescript
    const zeroExclusion = this.portfolioService.getZeroExclusionCounts(runId);
    const liquidityFilterCounts = this.portfolioService.getLiquidityFilterCounts(runId);
    await this.walkForwardRouting.generateCalibrationReport(
      runId,
      zeroExclusion,
      {
        ...liquidityFilterCounts,
        configuredMinPrice: config.minEntryPricePct ?? 0.05,
        configuredMaxGap: config.maxEntryPriceGapPct ?? 0.25,
      },
    );
    ```

- [x] Task 7: Add engine entry filter tests (AC: #1, #2, #5)
  - [x] 7.1 In `src/modules/backtesting/engine/backtest-engine.service.spec.ts`, add `describe('Entry liquidity filters')` block. Add `minEntryPricePct` and `maxEntryPriceGapPct` mocks to `createMockPortfolio()`: add `addLiquidityFilterCounts: vi.fn()` and `getLiquidityFilterCounts: vi.fn().mockReturnValue({ totalCandidates: 0, minPriceRejected: 0, minPriceKalshi: 0, minPricePoly: 0, priceGapRejected: 0 })`.
  - [x] 7.2 Tests (use existing test fixtures with prices adapted for filter scenarios):
    ```
    [P0] should skip entry when Kalshi price below minEntryPricePct
      — Config: minEntryPricePct: 0.05. Pair: kalshiClose=0.03, polyClose=0.40. Assert openPosition NOT called. Assert addLiquidityFilterCounts called with minPriceRejected >= 1.
    [P0] should skip entry when Polymarket price below minEntryPricePct
      — Config: minEntryPricePct: 0.05. Pair: kalshiClose=0.40, polyClose=0.02. Assert openPosition NOT called.
    [P0] should allow entry when both prices above minEntryPricePct
      — Config: minEntryPricePct: 0.05. Pair: kalshiClose=0.40, polyClose=0.55 (standard edge-producing prices). Assert openPosition called.
    [P0] should skip entry when price gap exceeds maxEntryPriceGapPct
      — Config: maxEntryPriceGapPct: 0.25. Pair: kalshiClose=0.10, polyClose=0.80 (gap=0.70). Assert openPosition NOT called.
    [P0] should allow entry when price gap within maxEntryPriceGapPct
      — Config: maxEntryPriceGapPct: 0.25. Pair: kalshiClose=0.40, polyClose=0.55 (gap=0.15). Assert openPosition called.
    [P1] should disable min-price filter when minEntryPricePct=0
      — Config: minEntryPricePct: 0. Pair: kalshiClose=0.001, polyClose=0.55 (below any threshold). Assert openPosition called (filter disabled).
    [P1] should disable price-gap filter when maxEntryPriceGapPct=0
      — Config: maxEntryPriceGapPct: 0. Pair: kalshiClose=0.10, polyClose=0.90 (huge gap). Assert openPosition called (filter disabled).
    [P1] should apply both filters independently — min-price passes but price-gap fails
      — Config: minEntryPricePct: 0.05, maxEntryPriceGapPct: 0.10. Pair: kalshiClose=0.20, polyClose=0.55 (both above min, but gap=0.35 > 0.10). Assert openPosition NOT called.
    [P1] should count per-platform min-price rejections correctly
      — Two pairs: one with kalshi below min (kalshiClose=0.02, polyClose=0.40), one with poly below min (kalshiClose=0.40, polyClose=0.01). Verify addLiquidityFilterCounts call has minPriceKalshi=1, minPricePoly=1, minPriceRejected=2.
    [P1] should count both platforms when both below min in same pair
      — Config: minEntryPricePct: 0.05. Pair: kalshiClose=0.02, polyClose=0.03 (both below 0.05). Assert minPriceRejected=1, minPriceKalshi=1, minPricePoly=1 (pair rejected once, both platform counters incremented).
    [P1] filter counters accumulate across timesteps
      — Two timesteps, each with a pair that triggers min-price filter. Verify addLiquidityFilterCounts receives accumulated totals.
    ```
  - [x] 7.3 **Test price values:** For "allow entry" tests, use K=0.40, P=0.55 (produces `|K-P|=0.15` gross edge, above `edgeThresholdPct: 0.05`). These are the same prices used across existing test fixtures. For "reject entry" tests, use prices that trigger the specific filter while keeping other values normal.
  - [x] 7.4 **Mock setup:** Extend `mockConfig` for filter tests: `{ ...mockConfig, minEntryPricePct: 0.05, maxEntryPriceGapPct: 0.25 }`. For "disable" tests, override to `0`.

- [x] Task 8: Verify no regressions (AC: #5)
  - [x] 8.1 Verify `mockConfig` in `backtest-engine.service.spec.ts` (line 45) does NOT include `minEntryPricePct` or `maxEntryPriceGapPct` — they are optional with defaults in the DTO. The engine uses `config.minEntryPricePct ?? 0.05` fallback. Existing tests should pass unchanged because existing test prices (K=0.40, P=0.55) are above the 0.05 min-price default and the gap (0.15) is below the 0.25 max-gap default.
  - [x] 8.2 Verify existing `exitStopLossPct` tests — the default (0.15) is within the new [0.05, 0.50] range, so no existing test should break. The test at line 386 (`exitStopLossPct: 0.005`) will still be rejected by `@Min(0.05)` but the test title needs updating (Task 2.3).
  - [x] 8.3 Check other spec files that call `runSimulationLoop` indirectly (walk-forward-routing, chunked-data-loading, sensitivity-analysis) — these pass configs that don't include the new fields. The `?? 0.05` / `?? 0.25` fallbacks in the engine and DTO defaults ensure they run unchanged.

- [x] Task 9: Lint + test (post-edit)
  - [x] 9.1 Run `pnpm lint` — fix any issues.
  - [x] 9.2 Run `pnpm test` — verify baseline + new tests pass. Expected: ~3763 + ~25 new = ~3788 tests passing.

## Dev Notes

**Line numbers are approximate** — always search by function/method name rather than relying on exact line numbers, as prior edits may have shifted them.

### Critical Implementation Details

**Entry filters go BEFORE edge calculation.** Insert after the cooldown check (line 624) and before `positionSizeUsd` calculation (line 626) in `detectOpportunities()`. This avoids wasted `calculateBestEdge()` / `calculateNetEdge()` / `modelFill()` calls for pairs that will be filtered anyway. The price data (`pairData.kalshiClose`, `pairData.polymarketClose`) is already available as Decimal values on the `BacktestTimeStepPair`.

**Value 0 disables each filter independently.** The `gt(0)` guard around each filter means:
- `minEntryPricePct: 0` → min-price filter skipped entirely
- `maxEntryPriceGapPct: 0` → price-gap filter skipped entirely
This matches the AC: "all three filters are configurable and independently disablable (min 0 disables)."

**Counter accumulation follows the `addZeroExclusionCounts` pattern.** A mutable counter object is passed from `runSimulationLoop()` to `detectOpportunities()` (like `cooldownMap`). At the end of `runSimulationLoop()`, the counters are flushed to the portfolio service's `RunningAccumulators`. This pattern:
- Avoids per-rejection method calls on the portfolio service
- Survives chunk boundaries (portfolio accumulators persist across chunks)
- Is automatically cleaned up on `destroyRun()` / `reset()`

**`exitStopLossPct` default is already 0.15.** Story 10-95-9 changed it from 0.30 to 0.15. This story only tightens the validation range from `@Min(0.01) @Max(1)` to `@Min(0.05) @Max(0.50)`. The engine fallback at line 559 (`config.exitStopLossPct ?? 0.15`) remains correct.

**Parameter count: `detectOpportunities()` goes from 11 to 14.** Adding `minEntryPrice: Decimal`, `maxEntryPriceGap: Decimal`, and `liquidityFilterCounts` object. These are private methods called from one place (`runSimulationLoop`). The high parameter count reflects pre-computed Decimal values passed to avoid redundant `new Decimal()` in the hot loop. A future refactoring could bundle simulation parameters into a context object, but that's out of scope (consistent with 10-95-12 dev notes).

**`totalCandidates` counts pairs reaching the liquidity filter checkpoint.** This is pairs that passed has-position and cooldown checks but have not yet been evaluated for edge. It does NOT count pairs blocked by max concurrent pairs or existing position — those aren't true entry candidates.

**Per-platform min-price tracking.** A single pair can trigger both `minPriceKalshi` and `minPricePoly` if both platforms are below the threshold. However, `minPriceRejected` increments only once per pair (it counts rejected pairs, not rejected legs). The per-platform counters provide diagnostic value about which platform has stale pricing.

### File Impact Map

**Modify (engine logic):**
| File | Current Lines | Change |
|------|---------------|--------|
| `src/common/interfaces/backtest-engine.interface.ts` | 41 | Add 2 optional fields to `IBacktestConfig` (~2 lines) |
| `src/modules/backtesting/dto/backtest-config.dto.ts` | 115 | Add 2 new fields, tighten `exitStopLossPct` range (~10 lines) |
| `src/modules/backtesting/engine/backtest-engine.service.ts` | 777 | Add filter logic in `detectOpportunities()`, pre-compute in `runSimulationLoop()`, accumulate at loop end, pass to report (~30 lines) |
| `src/modules/backtesting/engine/backtest-portfolio.service.ts` | 577 | Add 5 counter fields, 2 methods, initialize/reset entries (~35 lines) |
| `src/modules/backtesting/types/calibration-report.types.ts` | 145 | Add `liquidityFilter` to `DataQualitySummary` (~10 lines) |
| `src/modules/backtesting/reporting/calibration-report.service.ts` | 432 | Accept + include liquidity filter in report (~10 lines) |
| `src/modules/backtesting/engine/walk-forward-routing.service.ts` | ~285 | Extend `generateCalibrationReport()` param (~3 lines) |

**Modify (tests):**
| File | Change |
|------|--------|
| `src/modules/backtesting/dto/backtest-config.dto.spec.ts` | ~14 new tests (8 new field validation + 4 range tightening + 2 interface conformance) |
| `src/modules/backtesting/engine/backtest-engine.service.spec.ts` | ~10 new tests in `describe('Entry liquidity filters')`, update `createMockPortfolio()` |
| `src/modules/backtesting/engine/backtest-portfolio.service.spec.ts` | ~3 new tests in `describe('addLiquidityFilterCounts()')` |

**What NOT to change:**
| File | Why |
|------|-----|
| `src/modules/backtesting/engine/exit-evaluator.service.ts` | Liquidity filters are entry checks, not exit conditions |
| `src/modules/backtesting/engine/backtest-portfolio.service.ts` — `closePosition()` | No changes to exit/P&L logic |
| `src/modules/backtesting/utils/edge-calculation.utils.ts` | Edge calculation unaffected by entry filtering |
| `src/modules/backtesting/types/simulation.types.ts` | No new types needed |
| `src/modules/backtesting/__fixtures__/scenarios/*.fixture.json` | Fixtures don't include new params (optional with defaults) |
| Walk-forward, chunked-data-loading, sensitivity spec files | Don't test entry filtering, new fields default silently |

### Architecture Compliance

- **Financial math:** Price comparisons use `Decimal.lt()`, `Decimal.gt()`, `Decimal.abs()`, `Decimal.minus()`. No native JS operators on monetary values.
- **Module boundaries:** All changes within `modules/backtesting/`, `common/interfaces/`, and `common/types/`. No cross-module imports added.
- **God object check:** `backtest-engine.service.ts` goes from 777→~807 lines (above 600 review trigger, but logical lines remain under 400). Constructor deps unchanged at 8. `backtest-portfolio.service.ts` goes from 577→~612 lines (under 600 threshold).
- **Collection lifecycle:** Filter counters are primitive numbers in `RunningAccumulators` — no Map/Set cleanup needed.
- **Event emission:** No new events. Liquidity filtering is an internal simulation filter. Results are observable via the calibration report.
- **Paper/live mode:** Not applicable — backtesting is its own execution mode.
- **Naming:** `minEntryPricePct`, `maxEntryPriceGapPct` follow the existing `exitStopLossPct`, `edgeThresholdPct` naming convention (camelCase with Pct suffix for decimal percentage values).

### Previous Story Intelligence (10-95-12)

Key patterns to follow:
- **Test baseline:** 3763 tests pass. Maintain + add new.
- **TDD cycle:** RED → GREEN → REFACTOR. Write failing filter test first, implement filter, verify pass, add next test.
- **Import paths:** `IBacktestConfig` from `'../../../common/interfaces/backtest-engine.interface'`. `Decimal` from `'decimal.js'`.
- **Mutable pass-by-reference pattern:** `cooldownMap` proves that passing a mutable object from `runSimulationLoop()` to `detectOpportunities()` is the established pattern for cross-timestep accumulation.
- **DTO validation test pattern:** `plainToInstance(BacktestConfigDto, { ...validInput, newField: value })` → `validate(dto)` → check `errors.some(e => e.property === 'newField')`.
- **Mock portfolio setup:** `createMockPortfolio()` at line 101 needs two new mock methods. Follow the `addZeroExclusionCounts` / `getZeroExclusionCounts` mock pattern at lines 132-138.
- **Edge direction-invariance:** Post-10-95-11, `calculateBestEdge()` uses `|K-P|`. The liquidity filter checks raw prices, not edges, so direction is irrelevant.

### Project Structure Notes

- All changes conform to the `modules/backtesting/` bounded context
- No new files created — all changes modify existing files
- Types extended in their existing homes (`calibration-report.types.ts`, `backtest-engine.interface.ts`)
- Accumulator pattern extension follows the exact blueprint of `addZeroExclusionCounts` (introduced in 10-95-8)

### References

- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-12-backtest-liquidity-filter-fee-guard.md`#Section 4, Story 10-95-13] — Full course correction with evidence, liquidity asymmetry data
- [Source: `_bmad-output/planning-artifacts/epics.md:3769-3804`] — Epic 10.95 story 13 definition
- [Source: `_bmad-output/implementation-artifacts/10-95-12-backtest-pair-reentry-cooldown.md`] — Previous story (cooldown, test baseline 3763)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.ts:421-476`] — `runSimulationLoop()` config unpacking and loop structure
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.ts:588-705`] — `detectOpportunities()` full implementation, insertion point after line 624
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.ts:368-372`] — Report generation call with zeroExclusion passthrough
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.spec.ts:45-63`] — `mockConfig` object
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.spec.ts:101-140`] — `createMockPortfolio()` mock setup
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-portfolio.service.ts:93-116`] — `RunningAccumulators` interface and `RunContext`
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-portfolio.service.ts:452-479`] — `addZeroExclusionCounts` / `getZeroExclusionCounts` pattern to follow
- [Source: `pm-arbitrage-engine/src/modules/backtesting/dto/backtest-config.dto.ts:105-114`] — `exitStopLossPct` and `cooldownHours` fields (range to update)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/dto/backtest-config.dto.spec.ts:380-466`] — DTO validation and interface conformance test patterns
- [Source: `pm-arbitrage-engine/src/common/interfaces/backtest-engine.interface.ts:3-25`] — `IBacktestConfig` interface
- [Source: `pm-arbitrage-engine/src/modules/backtesting/types/calibration-report.types.ts:47-56`] — `DataQualitySummary` interface to extend
- [Source: `pm-arbitrage-engine/src/modules/backtesting/reporting/calibration-report.service.ts:43-51`] — `generateReport()` signature with zeroExclusion pattern
- [Source: `pm-arbitrage-engine/src/modules/backtesting/reporting/calibration-report.service.ts:325-386`] — `buildDataQualitySummary()` with zero exclusion inclusion pattern
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/walk-forward-routing.service.ts:267-277`] — `generateCalibrationReport()` delegation

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Existing takerFeeForPrice test (K=0.30, P=0.60) had gap=0.30 > default maxEntryPriceGapPct=0.25 — added `maxEntryPriceGapPct: 0.50` override to that test.
- "Disable filter" tests produced edges > maxEdgeThresholdPct=0.40 — added `maxEdgeThresholdPct: 1` override.
- walk-forward-routing.service.spec.ts delegation test expected 2 args, updated to 3 for new liquidityFilter param.

### Completion Notes List

- AC#1: minEntryPricePct filter implemented in detectOpportunities(), default 0.05, value 0 disables. 5 tests verify behavior.
- AC#2: maxEntryPriceGapPct filter implemented, default 0.25, value 0 disables. 4 tests verify behavior.
- AC#3: exitStopLossPct range tightened to @Min(0.05) @Max(0.50). 4 DTO validation tests added.
- AC#4: DataQualitySummary.liquidityFilter section in calibration report with totalCandidates, per-platform breakdowns, configured thresholds. Full pipeline: accumulators → portfolio → engine → walk-forward → calibration report service.
- AC#5: 28 new tests total (14 DTO + 3 portfolio + 11 engine). All 3792 tests pass (was 3764). 2 pre-existing e2e failures unchanged.

### Change Log

- 2026-04-12: Implemented entry liquidity filters, stop-loss recalibration, calibration report metrics. +28 tests.
- 2026-04-12: Regenerated dashboard API client (pnpm generate-api). Added Min Entry Price and Max Entry Price Gap inputs to NewBacktestDialog. Updated Exit Stop Loss input range to 5-50%.

### File List

**Modified (engine logic):**
- `pm-arbitrage-engine/src/common/interfaces/backtest-engine.interface.ts` — added minEntryPricePct, maxEntryPriceGapPct to IBacktestConfig
- `pm-arbitrage-engine/src/modules/backtesting/dto/backtest-config.dto.ts` — added 2 new DTO fields, tightened exitStopLossPct to @Min(0.05) @Max(0.50)
- `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.ts` — entry filters in detectOpportunities(), pre-compute in runSimulationLoop(), accumulate counters, pass to report
- `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-portfolio.service.ts` — 5 accumulator fields, addLiquidityFilterCounts(), getLiquidityFilterCounts(), initialize/reset
- `pm-arbitrage-engine/src/modules/backtesting/types/calibration-report.types.ts` — liquidityFilter in DataQualitySummary
- `pm-arbitrage-engine/src/modules/backtesting/reporting/calibration-report.service.ts` — generateReport + buildDataQualitySummary accept/include liquidityFilter
- `pm-arbitrage-engine/src/modules/backtesting/engine/walk-forward-routing.service.ts` — generateCalibrationReport passthrough

**Modified (engine tests):**
- `pm-arbitrage-engine/src/modules/backtesting/dto/backtest-config.dto.spec.ts` — +14 tests (8 new fields + 4 range tightening + 2 interface conformance)
- `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.spec.ts` — +11 tests, updated createMockPortfolio(), fixed takerFeeForPrice config, updated calibration report assertion
- `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-portfolio.service.spec.ts` — +3 tests for addLiquidityFilterCounts
- `pm-arbitrage-engine/src/modules/backtesting/engine/walk-forward-routing.service.spec.ts` — updated delegation test for 3rd param

**Modified (dashboard):**
- `pm-arbitrage-dashboard/src/api/generated/Api.ts` — regenerated from Swagger (includes minEntryPricePct, maxEntryPriceGapPct)
- `pm-arbitrage-dashboard/src/components/backtest/NewBacktestDialog.tsx` — added Min Entry Price (%) and Max Entry Price Gap (%) inputs, updated Exit Stop Loss min/max to 5-50%
