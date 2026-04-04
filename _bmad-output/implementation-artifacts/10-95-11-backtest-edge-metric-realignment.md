# Story 10-95.11: Backtest Edge Metric Realignment

Status: done

## Story

As an operator,
I want the backtest engine to use the same edge formula as the PRD and live detection engine (`|K-P|` price discrepancy instead of `1-K-P` overround gap),
so that backtest entry/exit decisions predict actual profitability and results can be compared to live performance.

## Context

Backtest run `9bab5cf5` (Mar 1-5, $10K bankroll, post-10-95-10) lost **-$3,406 on 436 positions** (7.1% win rate). Three prior bug-fix stories (10-95-8/9/10) addressed real issues and are confirmed working. The remaining dominant loss driver is a fundamental formula mismatch:

**Bug #1 (CRITICAL) — Edge formula divergence:** `calculateBestEdge()` in `edge-calculation.utils.ts:17-20` computes `grossEdge = 1 - K - P` (overround gap). The PRD (FR-AD-02) specifies `Gross Edge = sellPrice - buyPrice = |K - P|` (price discrepancy). The live detection engine (`detection.service.ts:187-217`) correctly uses `FinancialMath.calculateGrossEdge(buyPrice, sellPrice)` = `sellPrice - buyPrice`. The two metrics differ by `|1 - 2 * sellSidePrice|` — 70% of positions (304/436) have coded edge exceeding actual `|K-P|` gap.

**Bug #2 (HIGH) — Complement prices in fee deduction:** `calculateNetEdge()` at `edge-calculation.utils.ts:49-52` computes `sellPrice = 1 - otherPlatformClose` instead of using the actual platform price. The PRD example: "Sell fee cost (Kalshi at 0.62): 0.62 x 0.0266" — uses actual price, not complement. For Polymarket's flat 2% fee, this creates systematic error of `0.02 * (1-2P)` per unit.

**Bug #3 (MEDIUM) — Exit edge tracks wrong metric:** `calculateCurrentEdge()` at `edge-calculation.utils.ts:80-82` uses the same `1-K-P` formula. EDGE_EVAPORATION and PROFIT_CAPTURE triggers don't track actual PnL convergence, causing 87% of positions to fall through to TIME_DECAY.

## Acceptance Criteria

1. **Given** `calculateBestEdge()` **when** computing gross edge **then** returns `|K - P|` (absolute price difference) instead of `1 - K - P`. Specifically: `Decimal.max(kalshiClose, polymarketClose).minus(Decimal.min(kalshiClose, polymarketClose))` or equivalently `kalshiClose.minus(polymarketClose).abs()`. This matches `FinancialMath.calculateGrossEdge(buyPrice, sellPrice)` = `sellPrice - buyPrice` as used by the live detection engine.

2. **Given** `calculateNetEdge()` **when** computing fee deductions **then** uses actual trade prices for both buy and sell sides: `buyPrice = buySide === 'kalshi' ? kalshiClose : polymarketClose` (unchanged), `sellPrice = buySide === 'kalshi' ? polymarketClose : kalshiClose` (was: `1 - otherClose`). The PRD example confirms: "Buy fee cost (Polymarket at 0.58): 0.58 x 0.02 = 0.0116; Sell fee cost (Kalshi at 0.62): 0.62 x 0.0266 = 0.01649" — both use actual YES prices.

3. **Given** `calculateCurrentEdge()` **when** evaluating open position edge **then** uses `|K - P|` for gross edge (same formula as entry), preserving the `entryBuySide` parameter for directional fee consistency (from 10-95-10).

4. **Given** `edgeThresholdPct` configuration **when** validated **then** default raised from 0.03 to 0.05. With `|K-P|` as the edge metric, the threshold must exceed roundtrip fees per unit: for $200 positions with ~$10 roundtrip fees, minimum ~5%. `@Min()` raised from 0.02 to 0.03.

5. **Given** `maxEdgeThresholdPct` configuration **when** filtering phantom signals **then** default raised from 0.15 to 0.40. With `|K-P|` representing actual price gap (can exceed 0.50 for divergent markets), the old 15% cap filtered legitimate large-gap opportunities.

6. **Given** the PRD edge formula example (K=0.62, P=0.58, buySide=polymarket) **when** `calculateBestEdge()` and `calculateNetEdge()` run **then** `grossEdge = 0.04`, `netEdge ≈ 0.01024` (PRD shows 0.01021 with rounded intermediates; decimal.js exact: `0.04 - 0.0116 - 0.016492 - 0.001667 = 0.010241`).

7. **Given** existing tests **when** all tests run **then** all pass. Update `edge-calculation.utils.spec.ts` assertions for new formula values. Update `backtest-config.dto.spec.ts` for new defaults/minimums. Update `backtest-engine.service.spec.ts` for new threshold defaults. Verify fixture-based integration tests still produce correct entry/exit behavior.

## Tasks / Subtasks

- [x] Task 1: Fix `calculateBestEdge()` gross edge formula (AC: #1)
  - [x] 1.1 In `src/modules/backtesting/utils/edge-calculation.utils.ts:17-20`, replace:
    ```typescript
    // OLD: 1 - K - P (overround gap)
    const bestEdge = new Decimal(1).minus(pairData.kalshiClose).minus(pairData.polymarketClose);
    // NEW: |K - P| (price discrepancy, matches PRD FR-AD-02 and live detection.service.ts)
    const bestEdge = pairData.kalshiClose.minus(pairData.polymarketClose).abs();
    ```
  - [x] 1.2 Side determination at lines 22-27 is UNCHANGED — `buySide` logic using price comparison is correct (fixed in 10-95-10).
  - [x] 1.3 Replace comment: `// Gross edge = 1 - kalshi - poly (direction-independent, mathematically proven)` → `// Gross edge = |kalshi - polymarket| (price discrepancy, matches PRD FR-AD-02 and live detection.service.ts)`

- [x] Task 2: Fix `calculateNetEdge()` sell price computation (AC: #2)
  - [x] 2.1 In `src/modules/backtesting/utils/edge-calculation.utils.ts:49-52`, replace:
    ```typescript
    // OLD: complement prices (1 - other platform's close)
    const sellPrice =
      buySide === 'kalshi'
        ? new Decimal(1).minus(pairData.polymarketClose)
        : new Decimal(1).minus(pairData.kalshiClose);
    // NEW: actual trade prices (other platform's close)
    const sellPrice = buySide === 'kalshi' ? pairData.polymarketClose : pairData.kalshiClose;
    ```
  - [x] 2.2 `buyPrice` at lines 47-48 is UNCHANGED — already uses actual prices (`kalshiClose` / `polymarketClose`).
  - [x] 2.3 Fee schedule assignment at lines 54-61 is UNCHANGED — Kalshi/Poly fee schedule mapping is correct.

- [x] Task 3: Fix `calculateCurrentEdge()` gross edge formula (AC: #3)
  - [x] 3.1 In `src/modules/backtesting/utils/edge-calculation.utils.ts:80-82`, replace:
    ```typescript
    // OLD: 1 - K - P
    const grossEdge = new Decimal(1).minus(pairData.kalshiClose).minus(pairData.polymarketClose);
    // NEW: |K - P|
    const grossEdge = pairData.kalshiClose.minus(pairData.polymarketClose).abs();
    ```
  - [x] 3.2 `entryBuySide` parameter and delegation to `calculateNetEdge()` — UNCHANGED.

- [x] Task 4: Recalibrate config defaults (AC: #4, #5)
  - [x] 4.1 In `src/modules/backtesting/dto/backtest-config.dto.ts:22-24`:
    - Change `@Min(0.02)` to `@Min(0.03)`
    - Change default `0.03` to `0.05`
  - [x] 4.2 In `src/modules/backtesting/dto/backtest-config.dto.ts:101-103`:
    - Change default `0.15` to `0.40`
  - [x] 4.3 In `src/modules/backtesting/engine/backtest-engine.service.ts:430`, update fallback default:
    ```typescript
    // OLD:
    const maxEdgeThreshold = new Decimal(config.maxEdgeThresholdPct ?? 0.15);
    // NEW:
    const maxEdgeThreshold = new Decimal(config.maxEdgeThresholdPct ?? 0.4);
    ```

- [x] Task 5: Update `edge-calculation.utils.spec.ts` assertions (AC: #6, #7)
  - [x] 5.1 Update `calculateBestEdge` test assertions — gross edge values change with `|K-P|`:
        | Inputs (K, P) | Old `1-K-P` | New `\|K-P\|` | buySide (unchanged) |
        |---|---|---|---|
        | 0.60, 0.30 | 0.10 | **0.30** | polymarket |
        | 0.25, 0.55 | 0.20 | **0.30** | kalshi |
        | 0.50, 0.50 | 0 | 0 | polymarket (default) |
        | 0.55, 0.55 | -0.10 | **0** (was negative, now zero — no arb either way) |
        | 0.95, 0.02 | 0.03 | **0.93** | polymarket |
        | 0.02, 0.95 | 0.03 | **0.93** | kalshi |
        | 0.30, 0.30 | 0.40 | **0** (equal prices = no arb) | polymarket |
        | 0.40/0.30 vs 0.30/0.40 | both 0.30 | **both 0.10** | poly / kalshi |
  - [x] 5.2 Update the `0.55, 0.55` test: old assertion was `bestEdge.lt(0)` (negative). New: `bestEdge.equals(0)` (zero — no price discrepancy).
  - [x] 5.3 Update the `0.30, 0.30` test: old assertion was `bestEdge.equals(0.40)` (positive edge from overround gap). New: `bestEdge.equals(0)` (zero — no price discrepancy, no arb opportunity).
  - [x] 5.4 Add PRD regression test (AC #6): K=0.62, P=0.58, buySide='polymarket' (poly < kalshi → buy cheap poly, sell expensive kalshi).
    - `calculateBestEdge(makePair('0.62', '0.58'))` → `grossEdge = 0.04`, `buySide = 'polymarket'`
    - `calculateNetEdge(grossEdge=0.04, pair, 'polymarket', gas=0.50, positionSize=300)`:
      - buyPrice = 0.58 (poly), sellPrice = 0.62 (kalshi) — both actual YES prices
      - polyBuyFeeRate = 0.02 (flat), buyFeeCost = 0.58 \* 0.02 = 0.0116
      - kalshiSellFeeRate = 0.07 _ (1-0.62) = 0.0266, sellFeeCost = 0.62 _ 0.0266 = 0.016492
      - gasFraction = 0.50 / 300 = 0.001667
      - netEdge = 0.04 - 0.0116 - 0.016492 - 0.001667 = **0.010241**
    - Assert `netEdge.toFixed(5)` equals `'0.01024'` (decimal.js precision; PRD shows 0.01021 with rounded intermediates).
  - [x] 5.5 Update `calculateNetEdge` test: grossEdge value changes for pair (0.40, 0.30) from 0.30 to 0.10. Verify both buySide values still produce different net edges (asymmetric fee schedules).
  - [x] 5.6 Update `calculateCurrentEdge` tests: the underlying gross edge changes, so expected net edge values change. Verify that different `entryBuySide` still produces different net edges.

- [x] Task 6: Update `backtest-config.dto.spec.ts` assertions (AC: #4, #5, #7)
  - [x] 6.1 Line 21: `expect(dto.edgeThresholdPct).toBe(0.03)` → `toBe(0.05)`
  - [x] 6.2 Line 316: `expect(dto.maxEdgeThresholdPct).toBe(0.15)` → `toBe(0.40)`
  - [x] 6.3 Lines 349-356: Update `edgeThresholdPct rejects below 0.02` → change test value and description to `rejects below 0.03`. Test with value `0.02` (now rejected).
  - [x] 6.4 Lines 359-366: Update `edgeThresholdPct accepts 0.02 (minimum floor)` → change to `accepts 0.03 (minimum floor)`. Test with value `0.03`.
  - [x] 6.5 Lines 369-376: Update `edgeThresholdPct accepts 0.03 (new default)` → change to `accepts 0.05 (new default)`. Test with value `0.05`.
  - [x] 6.6 Update IBacktestConfig interface conformance tests (lines 409, 434): `edgeThresholdPct: 0.03` → `0.05` in the interface literal.

- [x] Task 7: Update `backtest-engine.service.spec.ts` edge threshold assertions (AC: #7)
  - [x] 7.1 In `DEFAULT_TEST_CONFIG` (line 48): `edgeThresholdPct: 0.03` → `0.05`. (Or adjust test-specific overrides to still test threshold behavior correctly.)
  - [x] 7.2 Line 404: `maxEdgeThresholdPct: 0.15` → `0.40` (or verify test override still works).
  - [x] 7.3 Line 443: Same — update `maxEdgeThresholdPct` in test override.
  - [x] 7.4 Lines 452-455: `default maxEdgeThresholdPct should be 0.15` → `0.40`. Update assertion and test description.
  - [x] 7.5 Review all `edgeThresholdPct`-dependent tests: the mock data may produce different net edges under the new formula, potentially changing which opportunities pass the threshold. Adjust mock prices or thresholds to preserve test intent.

- [x] Task 8: Update fixture JSON files and other test config references (AC: #7)
  - [x] 8.1 All 6 fixture files in `src/modules/backtesting/__fixtures__/scenarios/` have `edgeThresholdPct: 0.03`. Gross edge changes per fixture:
        | Fixture | Prices (K, P) | Old `1-K-P` | New `\|K-P\|` | Entry impact |
        |---------|--------------|-------------|--------------|-------------|
        | `profitable-2leg-arb` | 0.45, 0.52 | 0.03 | **0.07** | Still enters (larger edge) |
        | `unprofitable-fees-exceed` | 0.495, 0.500 | 0.005 | **0.005** | No change (sum ≈ 1.0) |
        | `breakeven` | 0.44, 0.54 | 0.02 | **0.10** | Edge 5x larger — verify EDGE_EVAPORATION exit still triggers with convergence prices K=0.48/P=0.50 (new exit edge = \|0.48-0.50\| = 0.02, old = 0.02) |
        | `coverage-gap` | 0.40, 0.55 | 0.05 | **0.15** | 3x larger — still enters, held through gap |
        | `insufficient-depth` | 0.40, 0.55 | 0.05 | **0.15** | 3x larger — but `depthAvailable: false` prevents entry regardless |
        | `resolution-force-close` | 0.40, 0.55 | 0.05 | **0.15** | 3x larger — still enters, resolution force-close at K=0.98/P=0.01 |
        For each fixture: verify the test assertions and expected outcomes still hold. Pay attention to `breakeven` — with 5x higher entry edge but same convergence prices, the EDGE_EVAPORATION exit might trigger at a different point or the "approximately zero P&L" expectation may shift.
  - [x] 8.2 If any fixture's expected outcome changes, update the fixture's `expected` block AND the test assertions in `backtest-engine.service.spec.ts` that reference it.
  - [x] 8.3 Update remaining spec files with hardcoded config: `walk-forward-routing.service.spec.ts:20`, `backtest-state-machine.service.spec.ts:17`, `chunked-data-loading.service.spec.ts:57`, `calibration-report.integration.spec.ts:25`, `sensitivity-analysis.service.spec.ts:48`.

- [x] Task 9: Validation backtest (manual operator task)
  - [x] 9.1 Re-run Mar 1-5 backtest with same config as run `9bab5cf5` (except new defaults: edgeThresholdPct=0.05, maxEdgeThresholdPct=0.40).
  - [x] 9.2 Verify: coded entry edge matches `|K-P|` for sampled positions.
  - [x] 9.3 Verify: fewer entries overall (higher threshold filters more noise).
  - [x] 9.4 Compare total PnL, win rate, Sharpe to baseline run `9bab5cf5`.

## Dev Notes

**Line numbers are approximate** — always search by function/method name rather than relying on exact line numbers, as prior edits may have shifted them.

### Critical Implementation Details

**The formula change in `calculateBestEdge()` is ~3 lines.** Replace `new Decimal(1).minus(K).minus(P)` with `K.minus(P).abs()`. The `buySide` determination (price comparison) is unchanged from 10-95-10.

**Why `|K-P|` is correct.** Cross-platform arbitrage profit = `sellPrice - buyPrice` = `max(K,P) - min(K,P)` = `|K-P|`. This is the maximum per-contract profit available from the price discrepancy, regardless of overround. When K+P > 1 (overround market), `1-K-P < 0` but `|K-P|` can still be positive — there's still directional profit from the price gap even if the combined market is overpriced. The PRD example confirms: K=0.62, P=0.58, gross edge = 0.62-0.58 = 0.04 = |K-P|.

**Why complement `sellPrice` was wrong.** `calculateNetEdge()` passes `buyPrice` and `sellPrice` to `FinancialMath.calculateNetEdge()`, which computes `sellFeeCost = sellPrice * takerFeeRate(sellPrice)`. For Kalshi's dynamic fee `0.07 * (1-P)`, using the complement `1-P` instead of `P` produces the same absolute fee cost (algebraically: `P * 0.07 * (1-P) = (1-P) * 0.07 * P`). But for Polymarket's flat 2%, using `1-K` instead of `K` changes the fee: `(1-K) * 0.02 != K * 0.02`. When K=0.62: wrong fee = 0.38 _ 0.02 = 0.0076, correct fee = 0.62 _ 0.02 = 0.0124.

**Gross edge is still direction-independent under `|K-P|`.** `abs(K-P)` is the same regardless of which side you buy. Only the net edge differs by direction (due to asymmetric fee schedules). The `buySide` determination and directional fee routing are unaffected.

**Test assertion values change significantly.** The old `1-K-P` and new `|K-P|` formulas produce identical output only when `K+P = 1` (no arb). For all other cases, see the table in Task 5.1. Key behavioral changes:

- `K=0.55, P=0.55`: old produces negative edge (rejected), new produces zero edge (also rejected, but for different reason — zero means no discrepancy, not overpriced)
- `K=0.30, P=0.30`: old produces 0.40 edge (enters), new produces 0 (rejects — no price discrepancy even though sum < 1)
- Extreme prices (0.95/0.02): old produces 0.03 edge, new produces 0.93 edge (massive)

**The `0.30, 0.30` behavioral change is CORRECT.** If both platforms price YES at 0.30, there's no cross-platform arbitrage (buy at 0.30, sell at 0.30 = zero profit). The old formula's 0.40 "edge" was the overround gap — it indicated underpricing across both markets, not a cross-platform opportunity.

**Extreme price discrepancies are filtered by `maxEdgeThresholdPct`.** With the new formula, K=0.95/P=0.02 produces `|K-P| = 0.93` gross edge. After fees, net edge is still very high. The `maxEdgeThresholdPct = 0.40` cap filters these as phantom signals. Existing tests for extreme prices (Task 5.1) should verify this cap works: the extreme-price `calculateBestEdge()` test returns 0.93 gross edge, but when used in the simulation loop, the net edge exceeds `maxEdgeThresholdPct` and is skipped.

**Entry fee calculation in `detectOpportunities()` is UNCHANGED.** Lines 642-655 of `backtest-engine.service.ts` already use actual prices (`pairData.kalshiClose`, `pairData.polymarketClose`) for entry fee computation (fixed in 10-95-9). The `calculateNetEdge()` fix brings the threshold check into alignment with this existing fee calculation.

**PnL accounting in `backtest-portfolio.service.ts` is INDEPENDENT.** PnL is computed from actual position entry/exit prices, not from the edge metric. The edge metric only affects which positions are entered and when they exit. PnL accounting (fixed in 10-95-8/9) is unaffected.

### File Impact Map

**Modify (engine logic):**
| File | Current Lines | Change |
|------|---------------|--------|
| `src/modules/backtesting/utils/edge-calculation.utils.ts` | 121 | Fix `calculateBestEdge()` formula (~3 lines), fix `calculateNetEdge()` sell price (~4 lines), fix `calculateCurrentEdge()` formula (~3 lines) |
| `src/modules/backtesting/dto/backtest-config.dto.ts` | 110 | Change `edgeThresholdPct` default 0.03→0.05, `@Min` 0.02→0.03. Change `maxEdgeThresholdPct` default 0.15→0.40 |
| `src/modules/backtesting/engine/backtest-engine.service.ts` | ~740 | Update `maxEdgeThresholdPct` fallback 0.15→0.40 (~1 line) |

**Modify (tests — assertions only):**
| File | Change |
|------|--------|
| `src/modules/backtesting/utils/edge-calculation.utils.spec.ts` | Update ALL `calculateBestEdge` assertions (8 tests), `calculateNetEdge` grossEdge value (1 test), `calculateCurrentEdge` (2 tests). Add PRD regression test. |
| `src/modules/backtesting/dto/backtest-config.dto.spec.ts` | Update default assertions (edgeThresholdPct 0.03→0.05, maxEdgeThresholdPct 0.15→0.40), min floor tests (0.02→0.03), IBacktestConfig literals |
| `src/modules/backtesting/engine/backtest-engine.service.spec.ts` | Update `DEFAULT_TEST_CONFIG`, maxEdgeThresholdPct default test, threshold override tests |
| `src/modules/backtesting/__fixtures__/scenarios/*.fixture.json` | Verify (and update if needed) expected outcomes under new formula. All have `edgeThresholdPct: 0.03` — may need adjustment if edge changes alter entry behavior. |
| `src/modules/backtesting/engine/walk-forward-routing.service.spec.ts` | Config `edgeThresholdPct: 0.03` — verify still valid or update |
| `src/modules/backtesting/engine/backtest-state-machine.service.spec.ts` | Config `edgeThresholdPct: 0.03` — verify still valid or update |
| `src/modules/backtesting/engine/chunked-data-loading.service.spec.ts` | Config `edgeThresholdPct: 0.03` — verify still valid or update |
| `src/modules/backtesting/reporting/calibration-report.integration.spec.ts` | Config `edgeThresholdPct: 0.03` — verify still valid or update |
| `src/modules/backtesting/reporting/sensitivity-analysis.service.spec.ts` | Config `edgeThresholdPct: 0.03` — verify still valid or update |

**What NOT to change:**
| File | Why |
|------|-----|
| `src/common/utils/financial-math.ts` | `calculateGrossEdge()` and `calculateNetEdge()` already correct — the backtest wraps them incorrectly |
| `src/modules/arbitrage-detection/detection.service.ts` | Live engine already uses correct formula (fixed March 3 SCP) |
| `src/modules/backtesting/engine/backtest-portfolio.service.ts` | PnL accounting is independent of edge metric (fixed 10-95-9) |
| `src/modules/backtesting/engine/exit-evaluator.service.ts` | Exit evaluator receives edge values — its logic is formula-agnostic |
| `src/modules/backtesting/utils/fee-schedules.ts` | Fee schedule definitions unchanged |
| `src/modules/backtesting/types/simulation.types.ts` | No structural changes to SimulatedPosition |
| `src/common/interfaces/backtest-engine.interface.ts` | `IBacktestConfig` interface unchanged (defaults are in DTO, not interface) |

### Architecture Compliance

- **Financial math:** ALL edge/fee calculations use `decimal.js` (`Decimal.abs()`, `.minus()`). No native JS operators on monetary values.
- **Module boundaries:** All changes within `modules/backtesting/` and `common/`. No cross-module imports added.
- **God object check:** `edge-calculation.utils.ts` stays at ~121 lines. `backtest-config.dto.ts` at ~110. `backtest-engine.service.ts` at ~740 (1 line change). All well under limits.
- **Event emission:** No new events. Existing events carry edge values that will now reflect the correct metric.
- **Naming:** No naming changes. `bestEdge`, `grossEdge`, `netEdge`, `buySide` all remain.

### Previous Story Intelligence (10-95-10)

Key patterns to follow:

- **Test baseline:** 3747 tests pass. Maintain + update assertions.
- **TDD cycle:** Write failing tests first (RED), then implement (GREEN), then clean up (REFACTOR). However, for this story the change is a formula fix where existing tests will FAIL after the production code change — so the approach is: update test assertions AFTER changing the formula, then verify all pass.
- **Actually, preferred TDD approach:** Add the PRD regression test FIRST (Task 5.4) — it will FAIL with the old formula. Then fix the formula (Tasks 1-3). Then update existing test assertions (Tasks 5-8). This preserves the RED-GREEN-REFACTOR cycle.
- **Import paths:** `FinancialMath` from `'../../../common/utils/financial-math'`, fee schedules from `'./fee-schedules'`.
- **`Decimal.abs()` is available.** `decimal.js` supports `.abs()` natively — confirmed in Decimal.js API.

### References

- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-12-backtest-edge-metric-reentry.md`] — Full course correction with evidence, DB analysis, math proof
- [Source: `_bmad-output/planning-artifacts/prd.md:1213-1234`] — FR-AD-02 Edge Calculation Formula with worked example
- [Source: `_bmad-output/planning-artifacts/epics.md:3316-3490`] — Epic 10.95 context
- [Source: `_bmad-output/implementation-artifacts/10-95-10-backtest-side-selection-depth-exit-fix.md`] — Previous story patterns, test baseline (3747 tests)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/utils/edge-calculation.utils.ts:13-90`] — All three functions to fix
- [Source: `pm-arbitrage-engine/src/modules/backtesting/utils/edge-calculation.utils.spec.ts`] — 18 existing tests needing assertion updates
- [Source: `pm-arbitrage-engine/src/modules/backtesting/dto/backtest-config.dto.ts:22-24,101-103`] — Default values to recalibrate
- [Source: `pm-arbitrage-engine/src/common/utils/financial-math.ts:27-96`] — `calculateGrossEdge()` and `calculateNetEdge()` (correct, do not change)
- [Source: `pm-arbitrage-engine/src/modules/arbitrage-detection/detection.service.ts:187-217`] — Live engine using correct formula (reference implementation)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None required.

### Completion Notes List

- Tasks 1-3: Formula fixes in `edge-calculation.utils.ts` — replaced `1-K-P` with `|K-P|` in all three functions (`calculateBestEdge`, `calculateNetEdge` sellPrice, `calculateCurrentEdge`). ~10 lines changed.
- Task 4: Config defaults recalibrated — `edgeThresholdPct` 0.03→0.05 (`@Min` 0.02→0.03), `maxEdgeThresholdPct` 0.15→0.40. Fallback in `backtest-engine.service.ts` updated.
- Task 5: Edge calculation spec updated — all 8 `calculateBestEdge` assertions updated for `|K-P|`. 2 PRD regression tests added (gross edge + net edge). Key finding: with actual prices (not complements), `calculateNetEdge` and `calculateCurrentEdge` produce **identical** net edges for both buySide directions because total fee cost is commutative (`K*feeK + P*feeP` is direction-invariant). Tests updated to assert equality instead of inequality.
- Task 6: DTO spec updated — default assertions, min floor tests (0.02→0.03), IBacktestConfig literal conformance tests.
- Task 7: Engine spec updated — `mockConfig.edgeThresholdPct` 0.03→0.05, phantom signal test prices changed from K=0.01/P=0.01 (produces 0 edge with `|K-P|`) to K=0.95/P=0.05 (produces 0.90 edge), maxEdgeThresholdPct default assertion 0.15→0.40.
- Task 8: All 6 fixture JSONs updated `edgeThresholdPct` 0.03→0.05. 5 other spec files with hardcoded config updated. All fixture outcomes verified unchanged under new formula.
- Baseline: 3725 passing unit tests (4 pre-existing e2e failures). Final: 3727 passing (+2 PRD regression tests).

### File List

**Modified (production):**

- `src/modules/backtesting/utils/edge-calculation.utils.ts`
- `src/modules/backtesting/dto/backtest-config.dto.ts`
- `src/modules/backtesting/engine/backtest-engine.service.ts`

**Modified (tests):**

- `src/modules/backtesting/utils/edge-calculation.utils.spec.ts`
- `src/modules/backtesting/dto/backtest-config.dto.spec.ts`
- `src/modules/backtesting/engine/backtest-engine.service.spec.ts`
- `src/modules/backtesting/engine/walk-forward-routing.service.spec.ts`
- `src/modules/backtesting/engine/backtest-state-machine.service.spec.ts`
- `src/modules/backtesting/engine/chunked-data-loading.service.spec.ts`
- `src/modules/backtesting/reporting/calibration-report.integration.spec.ts`
- `src/modules/backtesting/reporting/sensitivity-analysis.service.spec.ts`

**Modified (fixtures):**

- `src/modules/backtesting/__fixtures__/scenarios/profitable-2leg-arb.fixture.json`
- `src/modules/backtesting/__fixtures__/scenarios/unprofitable-fees-exceed.fixture.json`
- `src/modules/backtesting/__fixtures__/scenarios/breakeven.fixture.json`
- `src/modules/backtesting/__fixtures__/scenarios/coverage-gap.fixture.json`
- `src/modules/backtesting/__fixtures__/scenarios/insufficient-depth.fixture.json`
- `src/modules/backtesting/__fixtures__/scenarios/resolution-force-close.fixture.json`
