# Story 6.5.5i: Exit Threshold Calibration Fix

Status: done

## Story

As an operator,
I want exit thresholds calibrated against the realistic mark-to-market baseline at entry,
so that stop-loss doesn't trigger on the natural entry cost of opening a position.

## Background / Root Cause

The exit monitor's threshold calibration mixes two incompatible reference frames. `ThresholdEvaluatorService.evaluate()` takes `initialEdge` — a resolution-frame metric computed at detection time (gross edge minus entry fees and gas) — and applies it as a stop-loss/take-profit bound against `currentPnl` — a mark-to-market metric computed from live close prices plus exit fees. Both thresholds use zero as their baseline.

In reality, every position starts with a mark-to-market deficit equal to the bid-ask spread cost plus exit fees because:

- Detection evaluates the **favorable** side of each order book (best bid for sell legs, best ask for buy legs)
- P&L evaluates the **unfavorable** side (best ask for sell legs to buy back, best bid for buy legs to sell)
- Exit fees are subtracted from the P&L but not accounted for in the threshold baseline

**Evidence from paper trading (2026-03-04):**

| Metric | Value |
|--------|-------|
| Position size | 141 contracts |
| Gross edge (resolution) | $0.04/contract ($5.64 total) |
| Net edge (after entry fees) | $0.025/contract ($3.52 total) |
| Immediate MtM P&L | -$5.63 |
| — Spread cost component | -$4.28 |
| — Exit fee component | -$1.35 |
| Stop-loss threshold (current) | -$7.04 |
| Room to stop-loss at entry | $1.41 |
| SL proximity at entry | ~80% |

**Core problem:** Neither the detection subsystem nor the exit monitor is independently wrong. Detection correctly optimizes for resolution profit. The exit monitor correctly tracks mark-to-market. The bug is the interface between them — the threshold calibration applies resolution-frame inputs as bounds in the mark-to-market frame without any translation. Positions are designed to stop themselves out of profitable trades.

## Acceptance Criteria

### AC1: Schema — Entry Close Price Fields

**Given** the Prisma schema for `OpenPosition`
**When** this story is complete
**Then** two new nullable Decimal fields exist: `entryClosePriceKalshi` and `entryClosePricePolymarket`
**And** two new nullable Decimal fields exist: `entryKalshiFeeRate` and `entryPolymarketFeeRate` (fee rate as decimal fraction at entry close prices, persisted so downstream consumers don't need connector access)
**And** a migration is created for the schema change
**And** existing positions (with null values) continue to function without error

### AC2: Execution — Close-Side Price Capture

**Given** the execution service has just filled both legs
**When** the order books for both legs are fetched for close-side price extraction
**Then** the close-side top-of-book price is captured per leg:
- For a **buy** leg: the best **bid** price (what you'd sell at to close)
- For a **sell** leg: the best **ask** price (what you'd buy at to close)

**And** both close-side prices are persisted on the `OpenPosition` record alongside existing entry data

### AC3: Execution — Empty Close-Side Book

**Given** the execution service has just filled both legs
**When** the close side of the order book is empty (no bids after a buy fill, or no asks after a sell fill)
**Then** the entry close price for that leg is set to the fill price (conservative zero-spread assumption)
**And** the threshold evaluator treats this as zero spread for that leg (exit fees still apply)

### AC4: Threshold Evaluator — Entry Cost Baseline

**Given** a position has `entryClosePriceKalshi` and `entryClosePricePolymarket` populated
**When** `ThresholdEvaluatorService.evaluate()` runs
**Then** the entry cost baseline is computed as:

```
// Spread cost (direction-aware, clamped to >= 0)
kalshiSpread:
  if kalshiSide === 'buy':  max(0, kalshiEntryFillPrice - entryClosePriceKalshi)
  if kalshiSide === 'sell': max(0, entryClosePriceKalshi - kalshiEntryFillPrice)

polymarketSpread:
  if polymarketSide === 'buy':  max(0, polymarketEntryFillPrice - entryClosePricePolymarket)
  if polymarketSide === 'sell': max(0, entryClosePricePolymarket - polymarketEntryFillPrice)

spreadCost = (kalshiSpread * kalshiSize) + (polymarketSpread * polymarketSize)

// Exit fees at close-side prices, using persisted entry fee rates
// (Persisted at execution time via FinancialMath.calculateTakerFeeRate —
//  no fee schedule access needed at evaluation time)
entryExitFees = (entryClosePriceKalshi * kalshiSize * entryKalshiFeeRate)
              + (entryClosePricePolymarket * polymarketSize * entryPolymarketFeeRate)

entryCostBaseline = -(spreadCost + entryExitFees)

// Offset thresholds
stopLossThreshold  = entryCostBaseline + (initialEdge * legSize * -2)
takeProfitThreshold = entryCostBaseline + (initialEdge * legSize * 0.80)
```

**And** spread values are clamped to zero minimum (if market moved favorably between fill and close-side capture, don't inflate thresholds with negative spread)

### AC5: Legacy Position Fallback

**Given** a position was opened before this fix (entry close prices are null)
**When** the threshold evaluator evaluates it
**Then** `entryCostBaseline` defaults to `0` (current behavior preserved)
**And** no error is thrown, no NaN produced

### AC6: Position Enrichment — Exit Proximity

**Given** `PositionEnrichmentService.enrich()` computes exit proximity for the dashboard
**When** entry close prices are available on the position
**Then** the same baseline-offset thresholds are used for SL/TP proximity calculation
**And** when entry close prices are null, proximity uses baseline = 0 (current behavior)

### AC7: Tests

**Given** the test suites for threshold evaluator, execution, and position enrichment
**When** tests run
**Then** scenarios cover:
- Position with realistic spread + fees: SL proximity at entry is well below 50%
- Position with zero spread (close prices equal fill prices): only exit fees offset thresholds
- Negative spread (market moved favorably): clamped to zero, no threshold inflation
- Legacy position (null entry close prices): baseline = 0, current behavior preserved
- Empty close-side book: fill price used as fallback, zero spread for that leg
- All existing tests continue to pass
**And** `pnpm lint` reports zero errors

## Tasks / Subtasks

- [x] Task 1: Prisma schema migration (AC: #1)
  - [x] 1.1 Add `entryClosePriceKalshi Decimal? @db.Decimal(20, 8) @map("entry_close_price_kalshi")` to `OpenPosition` model in `prisma/schema.prisma` (after `isPaper` field, ~line 175)
  - [x] 1.2 Add `entryClosePricePolymarket Decimal? @db.Decimal(20, 8) @map("entry_close_price_polymarket")` to `OpenPosition` model
  - [x] 1.3 Add `entryKalshiFeeRate Decimal? @db.Decimal(20, 8) @map("entry_kalshi_fee_rate")` to `OpenPosition` model — fee rate as decimal fraction (e.g., 0.02 = 2%) computed at entry close price via `FinancialMath.calculateTakerFeeRate()` at execution time
  - [x] 1.4 Add `entryPolymarketFeeRate Decimal? @db.Decimal(20, 8) @map("entry_polymarket_fee_rate")` to `OpenPosition` model
  - [x] 1.5 Run `pnpm prisma migrate dev --name add-entry-close-prices-and-fee-rates`
  - [x] 1.6 Run `pnpm prisma generate` to regenerate client

- [x] Task 2: Close-side price capture in execution service (AC: #2, #3)
  - [x] 2.1 In `execution.service.ts`, after both legs fill and before position creation (after secondary order persistence at ~line 639, before the `const kalshiOrderId` block at ~line 643), add close-side price capture using the same pattern as `ExitMonitorService.getClosePrice()` (line 634-648):
    - `getOrderBook(contractId)` is on the `IPlatformConnector` interface (line 30 of `platform-connector.interface.ts`) — both connectors expose it directly. This is the same method the exit monitor's `getClosePrice()` already calls.
    - Fetch both order books via `primaryConnector.getOrderBook(primaryContractId)` and `secondaryConnector.getOrderBook(secondaryContractId)` in parallel via `Promise.all()`
    - For **buy** legs: extract best **bid** price (`book.bids[0]?.price`)
    - For **sell** legs: extract best **ask** price (`book.asks[0]?.price`)
    - Wrap in try/catch — on fetch failure, fall back to fill price (zero-spread conservative assumption)
  - [x] 2.2 **Empty book fallback:** If close side is empty (no bids for buy leg, no asks for sell leg), use the fill price as entry close price (zero-spread assumption). This is the same logic as AC#3. Log a `logger.warn` with contractId, side, and fill price when fallback is used — enables operators to identify positions with approximate baselines.
  - [x] 2.3 **Fetch failure fallback:** If `getOrderBook()` throws (network error, rate limit), fall back to fill price. Log `logger.warn` with error context. Close-side price capture must NEVER block or fail position creation — it's supplementary data.
  - [x] 2.4 Map captured prices to Kalshi/Polymarket using the existing `primaryLeg` variable (same mapping pattern as `kalshiOrderId`/`polymarketOrderId` at ~line 643):
    ```
    const kalshiEntryClosePrice = primaryLeg === 'kalshi' ? primaryClosePrice : secondaryClosePrice;
    const polymarketEntryClosePrice = primaryLeg === 'kalshi' ? secondaryClosePrice : primaryClosePrice;
    ```
  - [x] 2.5 Compute and persist entry fee rates alongside close prices using `FinancialMath.calculateTakerFeeRate()`:
    ```
    const kalshiFeeSchedule = (primaryLeg === 'kalshi' ? primaryConnector : secondaryConnector).getFeeSchedule();
    const polymarketFeeSchedule = (primaryLeg === 'kalshi' ? secondaryConnector : primaryConnector).getFeeSchedule();
    const entryKalshiFeeRate = FinancialMath.calculateTakerFeeRate(kalshiEntryClosePrice, kalshiFeeSchedule);
    const entryPolymarketFeeRate = FinancialMath.calculateTakerFeeRate(polymarketEntryClosePrice, polymarketFeeSchedule);
    ```
    This eliminates the need for fee schedule access in the threshold evaluator and enrichment service — they use the persisted rates directly.
  - [x] 2.6 Add all four fields to `positionRepository.create()` call (the position creation at ~line 651):
    ```
    entryClosePriceKalshi: kalshiEntryClosePrice.toNumber(),
    entryClosePricePolymarket: polymarketEntryClosePrice.toNumber(),
    entryKalshiFeeRate: entryKalshiFeeRate.toNumber(),
    entryPolymarketFeeRate: entryPolymarketFeeRate.toNumber(),
    ```
  - [x] 2.7 Write tests: close-side prices captured from order book; empty book fallback to fill price; fetch failure fallback to fill price; fee rates computed at close prices not fill prices; all four fields persisted

- [x] Task 3: Threshold evaluator — entry cost baseline (AC: #4, #5)
  - [x] 3.1 Extend `ThresholdEvalInput` interface (lines 4-20 of `threshold-evaluator.service.ts`) with four new optional fields:
    ```typescript
    entryClosePriceKalshi?: Decimal | null;
    entryClosePricePolymarket?: Decimal | null;
    entryKalshiFeeRate?: Decimal | null;
    entryPolymarketFeeRate?: Decimal | null;
    ```
    Fee rates are persisted on the position at execution time (Task 2.5) — no fee schedule access needed here.
  - [x] 3.2 In `evaluate()` method (starts at line 34), after extracting `kalshiPnl`/`polymarketPnl` (line ~74) and before the threshold checks (line ~96), add entry cost baseline computation:
    - **Check nulls:** If ANY of the four entry fields is null/undefined, set `entryCostBaseline = new Decimal(0)` (legacy fallback — AC#5). Both close prices and both fee rates are written atomically at execution time, so partial nulls indicate a legacy position or data corruption — log a warning if partially populated.
    - **Spread cost:** Compute per-leg spread direction-aware, clamp each to `Decimal.max(new Decimal(0), spread)`:
      - Buy side: `max(0, kalshiEntryFillPrice - entryClosePriceKalshi)`
      - Sell side: `max(0, entryClosePriceKalshi - kalshiEntryFillPrice)`
    - **Entry exit fees:** Use persisted `entryKalshiFeeRate` and `entryPolymarketFeeRate` directly:
      `entryExitFees = (entryClosePriceKalshi * kalshiSize * entryKalshiFeeRate) + (entryClosePricePolymarket * polymarketSize * entryPolymarketFeeRate)`
    - **Baseline:** `entryCostBaseline = -(spreadCost + entryExitFees)` (always <= 0)
  - [x] 3.3 Modify threshold calculations to offset from baseline:
    - Stop-loss: `const stopLossThreshold = entryCostBaseline.plus(scaledInitialEdge.mul(-2))`
    - Take-profit: `const takeProfitThreshold = entryCostBaseline.plus(scaledInitialEdge.mul(new Decimal('0.80')))`
  - [x] 3.4 Write tests: all scenarios from AC#7 — realistic spread, zero spread, negative spread clamping, legacy null fallback, partially populated entry fields (warn + baseline=0), Kalshi dynamic fee at different entry price tier, decimal precision

- [x] Task 4: Position enrichment — mirror baseline offset (AC: #6)
  - [x] 4.1 In `position-enrichment.service.ts` `enrich()` method (~line 33), extract all four entry fields from the position record: `entryClosePriceKalshi`, `entryClosePricePolymarket`, `entryKalshiFeeRate`, `entryPolymarketFeeRate`. The position object from `findByStatusWithOrders()` will now include these fields.
  - [x] 4.2 Replace the exit proximity calculation (lines ~170-190) to use baseline-offset thresholds:
    - If any of the four entry fields is null, keep `entryCostBaseline = 0` (current behavior)
    - If all available, compute same spread + exit fee baseline as threshold evaluator using persisted fee rates (no connector/fee schedule access needed — this is why fee rates are persisted on the position)
  - [x] 4.3 **Fix `minLegSize` usage (6.5.5h oversight):** The enrichment service currently uses `minLegSize = Decimal.min(kalshiSize, polymarketSize)` (line ~163) — this should be `legSize = kalshiSize` to match the threshold evaluator (Story 6.5.5h guaranteed equal sizes). Add the same debug assertion as the threshold evaluator. **Note:** This is a Story 6.5.5h oversight being picked up here — 6.5.5h fixed `minLegSize` in the threshold evaluator but did not touch `position-enrichment.service.ts` (which was added later in Story 7.1). Including it in this story is pragmatic since we're already modifying the enrichment proximity logic for the baseline offset. For traceability: the `minLegSize → legSize` fix originates from 6.5.5h; the baseline offset is 6.5.5i.
  - [x] 4.4 Write tests: enrichment returns correct exit proximity with baseline offset; null fallback returns current behavior

- [x] Task 5: Exit monitor — pass entry close prices to evaluator (AC: #4)
  - [x] 5.1 In `exit-monitor.service.ts` `evaluatePosition()` method (line ~207), extract all four entry fields from the position record and add to the `ThresholdEvalInput` construction:
    ```typescript
    entryClosePriceKalshi: position.entryClosePriceKalshi
      ? new Decimal(position.entryClosePriceKalshi.toString())
      : null,
    entryClosePricePolymarket: position.entryClosePricePolymarket
      ? new Decimal(position.entryClosePricePolymarket.toString())
      : null,
    entryKalshiFeeRate: position.entryKalshiFeeRate
      ? new Decimal(position.entryKalshiFeeRate.toString())
      : null,
    entryPolymarketFeeRate: position.entryPolymarketFeeRate
      ? new Decimal(position.entryPolymarketFeeRate.toString())
      : null,
    ```
    Note: Prisma Decimal → decimal.js conversion requires `.toString()` intermediary.
  - [x] 5.2 Write tests: all four entry fields forwarded to evaluator; null values forwarded correctly

- [x] Task 6: Run full test suite and lint (AC: #7)
  - [x] 6.1 `pnpm test` — all tests pass (baseline: 1,374 → 1,393 tests, +19 new)
  - [x] 6.2 `pnpm lint` — zero errors

## Dev Notes

### Architecture Compliance

- **Module boundaries preserved.** Changes span:
  - `modules/execution/` — close-side price capture during position creation (allowed: execution → connectors)
  - `modules/exit-management/` — threshold evaluator baseline offset (internal module change)
  - `dashboard/` — position enrichment mirroring (dashboard reads from persistence, allowed)
  - `persistence/` — schema migration (infrastructure change)
- **No forbidden imports.** No new cross-module dependencies. Execution still only talks to connectors and risk-management. Exit management still only talks to connectors and risk-management.
- **Financial math:** ALL spread, fee, and baseline calculations MUST use `decimal.js`. Use `.mul()`, `.plus()`, `.minus()`, `.div()`. Convert Prisma Decimal via `new Decimal(value.toString())`.
- **Error hierarchy:** No new error types needed. Execution fetch failures fall back to fill price gracefully.
- **Events:** No new events required. Existing threshold evaluation emits same events.

### Key Design Decisions

1. **Fetch order books after fills, not reuse from depth checking.** `getAvailableDepth()` fetches the order book internally but only returns accumulated depth as a number — the book objects are NOT retained. Rather than refactoring `getAvailableDepth()` to also return book data (breaking its clean single-responsibility), fetch fresh books after both legs fill. This also captures post-fill market state, which is more accurate for close-side prices. Time between fills and position creation is negligible.

2. **Entry close prices on position record, not computed on the fly.** Persisting close prices at execution time provides an exact, auditable record. Computing them later from order book snapshots would require replaying historical data and wouldn't account for real-time book state at entry.

3. **Nullable fields for backward compatibility.** Existing positions have null entry close prices. The threshold evaluator and enrichment service use baseline = 0 for null values, preserving current behavior exactly. No data migration needed.

4. **Spread clamped to zero minimum.** If the market moved favorably between execution and close-price capture (close-side price better than fill price), this would produce a negative spread. Clamping prevents inflating thresholds with a "bonus" that may not persist.

5. **Persisted fee rates eliminate downstream access problem.** Entry fee rates are computed via `FinancialMath.calculateTakerFeeRate(entryClosePrice, feeSchedule)` at execution time and persisted on the position record. This is critical because `PositionEnrichmentService` (in `dashboard/`) does not inject connectors and cannot call `getFeeSchedule()`. Persisting the rates at execution time means both the threshold evaluator and the enrichment service can compute the entry cost baseline using only position data — no connector access needed. For Kalshi's dynamic price-dependent fees, this captures the exact fee tier at the entry close price. **Known limitation:** The entry exit fee rate is frozen at execution time. If the fee schedule itself changes (Kalshi updates fee tiers), the persisted rate won't reflect the update. This is acceptable — the baseline represents historical entry conditions, not current fee schedules.

### Design Note — Take-Profit via Early Exit

For positions where the combined bid-ask spread exceeds the net edge (as in the evidence position: 3-cent spread vs 2.5-cent net edge), the take-profit threshold remains negative after offset (e.g., -$2.81). This means MtM P&L would need to improve from the entry baseline but would still be nominally negative at TP trigger. This is expected and correct — such positions are not designed for profitable early exit. Their profit path is resolution (binary payout), not spread convergence. The TP threshold serves as a "best achievable early exit" rather than a profit target. The stop-loss, the critical threshold, is properly calibrated with full headroom.

> **Superseded by Story 6.5.5j** — The design note above incorrectly concluded that negative TP thresholds are "expected and correct." Story 6.5.5j replaces the formula with a journey-based calculation floored at zero. Positions whose profit path is resolution now correctly avoid premature TP exits at a loss. See 6-5-5j-take-profit-negative-threshold-fix.md for the corrected analysis.

### Expected Impact on Evidence Position

- Entry cost baseline: ~-$5.63 (spread $4.28 + fees $1.35)
- New SL threshold: -$5.63 + (-$7.04) = **-$12.67** → **$7.04 of room from entry**
- New TP threshold: -$5.63 + $2.82 = **-$2.81** → **$2.82 of movement needed for TP from entry**
- SL proximity at entry: ~0% (properly calibrated vs current ~80%)

### Current Code — Exact Locations to Modify

**`prisma/schema.prisma` — OpenPosition model (~line 155-181):**

| Change | Details |
|--------|---------|
| Add field | `entryClosePriceKalshi Decimal? @db.Decimal(20, 8) @map("entry_close_price_kalshi")` |
| Add field | `entryClosePricePolymarket Decimal? @db.Decimal(20, 8) @map("entry_close_price_polymarket")` |
| Add field | `entryKalshiFeeRate Decimal? @db.Decimal(20, 8) @map("entry_kalshi_fee_rate")` |
| Add field | `entryPolymarketFeeRate Decimal? @db.Decimal(20, 8) @map("entry_polymarket_fee_rate")` |

**`src/modules/execution/execution.service.ts` (735 lines):**

| Location | Current | Change |
|----------|---------|--------|
| After ~line 639 (after secondary order persist) | No close-side capture | Add `Promise.all()` order book fetch for both legs, extract close-side top-of-book prices, map to kalshi/polymarket |
| ~Line 651 (`positionRepository.create()`) | No close price fields | Add `entryClosePriceKalshi` and `entryClosePricePolymarket` to create input |

**`src/modules/exit-management/threshold-evaluator.service.ts` (162 lines):**

| Location | Current | Change |
|----------|---------|--------|
| Lines 4-20 (`ThresholdEvalInput`) | No entry close prices | Add optional `entryClosePriceKalshi`, `entryClosePricePolymarket` (and optionally fee schedules) |
| Lines 63-94 (P&L computation) | Thresholds anchored at 0 | Add entry cost baseline computation (spread + exit fees at entry close prices) |
| Lines 96-113 (stop-loss) | `scaledInitialEdge.mul(-2)` | `entryCostBaseline.plus(scaledInitialEdge.mul(-2))` |
| Lines 115-125 (take-profit) | `scaledInitialEdge.mul(0.80)` | `entryCostBaseline.plus(scaledInitialEdge.mul(new Decimal('0.80')))` |

**`src/modules/exit-management/exit-monitor.service.ts` (648 lines):**

| Location | Current | Change |
|----------|---------|--------|
| Lines 207-231 (`ThresholdEvalInput` construction) | No entry close prices | Add `entryClosePriceKalshi`/`entryClosePricePolymarket` from position record (Prisma Decimal → decimal.js via `.toString()`) |

**`src/dashboard/position-enrichment.service.ts` (205 lines):**

| Location | Current | Change |
|----------|---------|--------|
| Line ~163 | `minLegSize = Decimal.min(kalshiSize, polymarketSize)` | Replace with `legSize = kalshiSize` + debug assertion (mirror 6.5.5h fix) |
| Lines 170-190 (exit proximity) | `stopLossThreshold = scaledInitialEdge.mul(-2)` | Add entry cost baseline offset, same formula as threshold evaluator |

### Sequencing & Dependencies

- **Depends on:** Stories 6.5.5a through 6.5.5h (all done). Specifically:
  - 6.5.5h (Equal Leg Sizing) — sizes guaranteed equal, `legSize = kalshiSize` pattern
  - 6.5.5g (Kalshi Dynamic Fees) — `FinancialMath.calculateTakerFeeRate()` for price-dependent fees
  - 6.5.5f (Gross Edge Formula) — edge = `sellPrice - buyPrice` (signed)
  - 6.5.5e (Paper Mode Exit Monitor) — paper positions flow through exit monitoring
- **Gates:** Story 6.5.5 (Paper Execution Validation) and Story 6.5.6 (Validation Report)
- **Schema migration:** Four nullable columns on `open_positions` (2 close prices + 2 fee rates) — backward compatible
- **No new module dependencies.** No connector changes. No detection changes.

### Previous Story Intelligence

**Story 6.5.5h (Execution Equal Leg Sizing) — most recent, 1,374 tests baseline:**
- `legSize = kalshiSize` pattern established in threshold evaluator (sizes guaranteed equal)
- Execution flow restructured: both depth checks BEFORE either order submission
- Collateral-aware sizing: buy = `budget/price`, sell = `budget/(1-price)`
- Position creation persists equal sizes in `sizes` JSONB
- Runtime invariant: `targetSize === secondarySize` before submission

**Story 6.5.5g (Kalshi Dynamic Fee Correction):**
- `FinancialMath.calculateTakerFeeRate(price, feeSchedule)` centralized helper
- `FeeSchedule.takerFeeForPrice` callback for Kalshi's price-dependent fees
- Fee rate is a decimal fraction (0.02 = 2%), NOT percentage

**Story 6.5.5e (Paper Mode Exit Monitor Fix):**
- Exit monitor mode-aware: `isPaper`/`mixedMode` threaded through all methods
- Paper positions evaluated, exit orders tagged, events carry correct flags

**Story 6.5.5f (Detection Gross Edge Formula Fix):**
- Edge = `sellPrice - buyPrice` (signed, directional)
- Edge re-validation in execution uses same formula

### Git Intelligence

Recent engine commits (on `main`):

```
dcde66a Merge remote-tracking branch 'origin/main' into epic-7
11168d9 feat: add LEG_SIZE_MISMATCH error code and enhance execution service with collateral-aware sizing
a1f18c8 feat: add performance tracking
09f5b96 feat: implement match approval/rejection
9a37f3b feat: add position enrichment service
78da8f6 feat: implement dynamic taker fee calculation for Kalshi
00ed663 refactor: update financial math for new gross edge formula
```

Most relevant: `11168d9` (equal leg sizing, current execution flow) and `78da8f6` (dynamic fee helper).

### File Structure — Files to Modify

| File | Change |
|------|--------|
| `prisma/schema.prisma` | Add 4 nullable Decimal fields to OpenPosition model (2 close prices + 2 fee rates) |
| `prisma/migrations/*/migration.sql` | Auto-generated by `prisma migrate dev` |
| `src/modules/execution/execution.service.ts` | Close-side price capture after both fills, persist on position |
| `src/modules/execution/execution.service.spec.ts` | Tests: close-side price capture, empty book fallback, fetch failure fallback |
| `src/modules/exit-management/threshold-evaluator.service.ts` | Extend input interface, entry cost baseline computation, offset thresholds |
| `src/modules/exit-management/threshold-evaluator.service.spec.ts` | Tests: realistic spread, zero spread, negative clamping, legacy null, all existing pass |
| `src/modules/exit-management/exit-monitor.service.ts` | Pass entry close prices from position to evaluator input |
| `src/modules/exit-management/exit-monitor.service.spec.ts` | Tests: entry close prices forwarded, null forwarding |
| `src/dashboard/position-enrichment.service.ts` | Mirror baseline offset in exit proximity, fix minLegSize → legSize |
| `src/dashboard/position-enrichment.service.spec.ts` | Tests: enrichment proximity with baseline, null fallback |

### Scope Guard

This story is strictly scoped to:

1. Schema: four nullable Decimal columns on OpenPosition (2 close prices + 2 fee rates)
2. Execution: close-side price capture after fills
3. Threshold evaluator: entry cost baseline offset on SL/TP thresholds
4. Position enrichment: mirror baseline offset for dashboard proximity
5. Exit monitor: pass entry close prices to evaluator
6. Tests for all above

Do NOT:

- Modify detection service logic (edge formula already correct from 6.5.5f)
- Change execution sizing logic (collateral-aware equalization correct from 6.5.5h)
- Add configurable SL/TP multipliers (deferred to future, keep 2x/-0.80 defaults)
- Modify connectors (order book API already supports this)
- Change the FeeSchedule interface or FinancialMath helpers (already correct from 6.5.5g)
- Add new events or error codes
- Modify risk management module
- Change monitoring or Telegram alerting

### Project Structure Notes

- All source changes within `pm-arbitrage-engine/` — separate git repo, separate commit required
- Schema migration creates a new migration file in `prisma/migrations/`
- Files follow existing kebab-case naming convention
- Tests co-located with source (`.spec.ts` suffix)
- This is a **dual-repo** project — engine changes require separate commit from story file updates

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-05-threshold-calibration.md] — Approved sprint change proposal with full evidence, impact analysis, and detailed acceptance criteria
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts:4-20] — `ThresholdEvalInput` interface (extend with entry close prices)
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts:34-148] — `evaluate()` method (add baseline computation, offset thresholds)
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts:150-162] — `calculateLegPnl()` helper (reuse for spread calculation)
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts:207-231] — `ThresholdEvalInput` construction in `evaluatePosition()` (add entry close prices)
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts:634-648] — `getClosePrice()` helper (pattern for close-side price extraction)
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts:639-668] — Position creation block (add close-side price capture before, add fields to create input)
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts:738-782] — `getAvailableDepth()` — fetches order book internally but does NOT retain book object (hence refetch needed)
- [Source: pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts:33-205] — `enrich()` method (mirror baseline offset, fix minLegSize)
- [Source: pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts:163] — `minLegSize = Decimal.min(...)` to fix (should be `legSize = kalshiSize`)
- [Source: pm-arbitrage-engine/prisma/schema.prisma:155-181] — OpenPosition model (add entry close price fields)
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.ts:114-124] — `FinancialMath.calculateTakerFeeRate()` (use for entry exit fees at close prices)
- [Source: pm-arbitrage-engine/src/common/types/platform.type.ts:64-83] — `FeeSchedule` interface with `takerFeeForPrice` callback
- [Source: _bmad-output/implementation-artifacts/6-5-5h-execution-equal-leg-sizing.md] — Previous story (equal leg sizing, 1,374 tests baseline)
- [Source: _bmad-output/implementation-artifacts/6-5-5e-paper-mode-exit-monitor-fix.md] — Paper mode exit monitor (isPaper threading pattern)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

Session transcript: `5d70e1c2-1399-488a-bc8e-98962f0885bc.jsonl` (continued across context boundary)

### Completion Notes List

- All 6 tasks completed using strict TDD (red-green) workflow
- All 7 Acceptance Criteria verified as PASS
- Test count: 1,374 (baseline) → 1,393 (+19 new tests across 4 spec files)
- Lint: 0 errors after implementation
- Fixed 6.5.5h oversight in position-enrichment.service.ts (`minLegSize` → `legSize = kalshiSize`)
- Lad MCP design review attempted but timed out (both reviewers) — proceeded without blocking
- Code reviews via Lad MCP timed out — manual verification used instead
- Key implementation detail: fee rates persisted at execution time so downstream consumers (threshold evaluator, enrichment) don't need connector/fee schedule access

### Code Review Fixes (AI)

Adversarial code review performed by Claude Opus 4.6. 4 issues fixed (1 HIGH, 3 MEDIUM):

1. **[H1] Fee rate computation try-catch** (`execution.service.ts:749-775`): Wrapped `getFeeSchedule()` + `calculateTakerFeeRate()` in try-catch with flat 2% fallback. Previously, a throw here would orphan both filled orders without creating a position record.
2. **[M1] Missing debug assertion in enrichment** (`position-enrichment.service.ts`): Added Logger + `if (!kalshiSize.eq(polymarketSize))` assertion matching threshold evaluator. Task 4.3 claimed this was done but it was missing.
3. **[M2] Extracted shared baseline computation** (`financial-math.ts`): Created `FinancialMath.computeEntryCostBaseline()` static method. Both `threshold-evaluator.service.ts` and `position-enrichment.service.ts` now call the shared helper instead of duplicating ~50 lines.
4. **[M3] Tightened test assertion** (`position-enrichment.service.spec.ts:380`): Replaced range assertion `(0.5, 0.8)` with `toBeCloseTo(0.7095, 2)` for SL proximity baseline offset test.

2 LOW issues not fixed (acceptable):
- L1: Duplicated close-side price extraction blocks in execution service (cosmetic, single-use code)
- L2: No test for partially populated entry fields in enrichment service (covered at utility level)

Test count after review: 1,393 → 1,398 (+5 for `computeEntryCostBaseline` utility tests)

### File List

| File | Change |
|------|--------|
| `prisma/schema.prisma` | Added 4 nullable Decimal fields to OpenPosition: `entryClosePriceKalshi`, `entryClosePricePolymarket`, `entryKalshiFeeRate`, `entryPolymarketFeeRate` |
| `prisma/migrations/20260305090624_add_entry_close_prices_and_fee_rates/migration.sql` | Auto-generated migration adding 4 columns to `open_positions` |
| `src/common/utils/financial-math.ts` | Added `computeEntryCostBaseline()` static method (review fix M2) |
| `src/common/utils/financial-math.spec.ts` | +5 tests: baseline computation — realistic spread, null fields, partial fields, negative clamping, zero spread (review fix M2) |
| `src/modules/execution/execution.service.ts` | Close-side price capture after both legs fill; fee rate computation wrapped in try-catch (review fix H1) |
| `src/modules/execution/execution.service.spec.ts` | +6 tests: close-side price capture, empty book fallback, fetch failure fallback, dynamic fee rates, field persistence |
| `src/modules/exit-management/threshold-evaluator.service.ts` | Extended ThresholdEvalInput; delegates baseline to `FinancialMath.computeEntryCostBaseline()` (review fix M2) |
| `src/modules/exit-management/threshold-evaluator.service.spec.ts` | +8 tests: realistic spread, zero spread, negative clamping, legacy null, undefined, partial fields, dynamic fee, differentiating SL test |
| `src/modules/exit-management/exit-monitor.service.ts` | Forward 4 entry close price fields from position to ThresholdEvalInput |
| `src/modules/exit-management/exit-monitor.service.spec.ts` | +2 tests: Decimal field forwarding, null field forwarding |
| `src/dashboard/position-enrichment.service.ts` | Added Logger + debug assertion (review fix M1); delegates baseline to `FinancialMath.computeEntryCostBaseline()` (review fix M2); fix `minLegSize` → `legSize = kalshiSize` |
| `src/dashboard/position-enrichment.service.spec.ts` | +3 tests: legSize fix, baseline offset proximity (tightened assertion — review fix M3), null fallback |
