# Sprint Change Proposal — Kalshi Dynamic Fee Correction

**Date:** 2026-03-04
**Triggered by:** Code review during Epic 6.5 Paper Trading Validation
**Author:** Bob (SM) with Arbi
**Status:** Approved
**Scope:** Minor — direct implementation by dev agent

---

## Section 1: Issue Summary

**Problem:** The Kalshi connector's `getFeeSchedule()` returns `takerFeePercent: 0` and `makerFeePercent: 0`, and the PRD documents Kalshi's fee as a flat 1.5%. Both are wrong. Kalshi charges a **dynamic, price-dependent taker fee**: `roundUp(0.07 × P × (1-P))` per contract, peaking at 1.75% at P=0.50.

**Discovery:** Manual code review of `kalshi.connector.ts:479-486` cross-referenced against Kalshi's published fee schedule (Feb 5, 2026 PDF). Web research confirmed the formula.

**Impact:** With 0% Kalshi fees, every edge calculation is overstated by up to 1.75%. The system could execute **negative-edge trades** that appear profitable. Exit monitoring and single-leg PnL scenarios are also miscalculated, potentially triggering exits too late or recommending unprofitable retry actions. Paper trading validation (story 6-5-5) would produce meaningless results.

---

## Section 2: Impact Analysis

**Epic Impact:** Epic 6.5 (in-progress) — must fix before story 6-5-5 paper execution validation. No other epic scope changes.

**Story Impact:** New story 6-5-5g added to Epic 6.5.

**Artifact Conflicts:**

- PRD lines 1223-1254: Fee normalization section states flat 1.5% Kalshi fee — must be corrected
- Architecture: `FeeSchedule` interface needs optional `takerFeeForPrice` callback
- Code: 6 source files + 1 mock factory + ~8 spec files affected

**Technical Impact:** No infrastructure, deployment, or schema changes. Pure code + doc fix.

---

## Section 3: Recommended Approach

**Selected: Direct Adjustment** (Option 1)

**Rationale:** Well-scoped bug fix within existing sprint. No architectural redesign — extends `FeeSchedule` with an optional callback, backward-compatible. Low risk, medium effort.

- **Effort:** Medium (~9 source files, ~8 spec files, comprehensive new tests, PRD update)
- **Risk:** Low — interface extension is additive, all existing code paths have fallback to flat rate
- **Timeline impact:** 1 story added to Epic 6.5, must complete before 6-5-5

### LAD Design Review Findings (incorporated)

1. **Serialization safety:** `takerFeeForPrice` callback is stripped by `JSON.stringify()`. Verified that event payloads serialize computed fee *costs* (numbers), not raw `FeeSchedule` objects. Added verification checklist item.
2. **Centralized fee helper:** Instead of duplicating the callback-or-fallback pattern in 6 locations, add `FinancialMath.calculateTakerFeeRate(price, feeSchedule)` static method.
3. **Rounding precision confirmed:** Kalshi's "round up" means **round up to the next cent** (ceiling to 2 decimal places in dollar terms). The rounding applies to the **total fee for the batch** (`0.07 × C × P × (1-P)`), not per-contract. Since our callback returns a *rate* (fee fraction per unit price), the rounding must be applied after multiplying by quantity at the consumption site, not inside the callback itself.
4. **Scale mismatch prevention:** The centralized helper from finding #2 encapsulates the scale conversion (`takerFeePercent / 100` vs callback returning decimal directly), eliminating risk of consumer-level confusion.

---

## Section 4: Detailed Change Proposals

### 4.1 Interface Change — FeeSchedule

**File:** `pm-arbitrage-engine/src/common/types/platform.type.ts`

Add optional `takerFeeForPrice` callback to `FeeSchedule` interface:

```typescript
export interface FeeSchedule {
  platformId: PlatformId;
  makerFeePercent: number; // Percentage: 0-100 scale (e.g., 2.0 = 2% fee)
  takerFeePercent: number; // Percentage: 0-100 scale. For dynamic fees, worst-case (max) fee.
  description: string;
  gasEstimateUsd?: number; // Dynamic gas estimate in USD (Polymarket only)
  /**
   * Optional: compute the exact taker fee for a given contract price.
   * Price is in internal decimal format (0.00-1.00).
   * Returns the fee as a decimal fraction (e.g., 0.0175 for 1.75%).
   * When absent, consumers use takerFeePercent / 100 as a flat rate.
   */
  takerFeeForPrice?: (price: number) => number;
}
```

### 4.2 Connector Fix — KalshiConnector.getFeeSchedule()

**File:** `pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts`

```typescript
/**
 * Kalshi fee formula (effective Feb 2026):
 *   fee per contract = roundUp(0.07 × P × (1 - P))
 * where P = contract price in dollars (0.00-1.00).
 * Peak fee at P=0.50 → 1.75¢/contract (1.75%).
 * Maker fee: 0% for most markets.
 */
getFeeSchedule(): FeeSchedule {
  return {
    platformId: PlatformId.KALSHI,
    makerFeePercent: 0,
    takerFeePercent: 1.75, // Worst-case (at P=0.50) for pre-screening
    description:
      'Kalshi: dynamic taker fee = 0.07 × P × (1-P), max 1.75% at 50¢. 0% maker fee.',
    takerFeeForPrice: (price: number): number => {
      // Fee per contract (dollars) = 0.07 × P × (1-P)
      // As fraction of contract price: 0.07 × (1-P)
      // Returns decimal fraction (e.g., 0.035 at P=0.50)
      if (price <= 0 || price >= 1) return 0;
      return new Decimal(0.07)
        .mul(new Decimal(1).minus(price))
        .toNumber();
    },
  };
}
```

### 4.3 Centralized Fee Helper (NEW — from LAD review)

**File:** `pm-arbitrage-engine/src/common/utils/financial-math.ts`

Add a static method to `FinancialMath` that encapsulates the callback-or-fallback pattern:

```typescript
/**
 * Returns the taker fee rate as a decimal fraction for a given price.
 * Uses takerFeeForPrice callback when available (dynamic fees like Kalshi),
 * falls back to takerFeePercent / 100 (flat fees like Polymarket).
 *
 * @param price - Contract price in internal decimal format (0.00-1.00)
 * @param feeSchedule - Platform fee schedule
 * @returns Fee rate as decimal fraction (e.g., 0.035 for 3.5%)
 */
static calculateTakerFeeRate(price: Decimal, feeSchedule: FeeSchedule): Decimal {
  if (feeSchedule.takerFeeForPrice) {
    return new FinancialDecimal(feeSchedule.takerFeeForPrice(price.toNumber()));
  }
  return new FinancialDecimal(feeSchedule.takerFeePercent).div(100);
}
```

All 6 consumer locations use this helper instead of inline logic:

```typescript
// Before (duplicated 6 times):
const feeRate = feeSchedule.takerFeeForPrice
  ? new FinancialDecimal(feeSchedule.takerFeeForPrice(price.toNumber()))
  : new FinancialDecimal(feeSchedule.takerFeePercent).div(100);

// After (single helper call):
const feeRate = FinancialMath.calculateTakerFeeRate(price, feeSchedule);
```

### 4.4 Consumer Updates (6 locations)

All consumers call `FinancialMath.calculateTakerFeeRate(price, feeSchedule)`:

1. **`FinancialMath.calculateNetEdge()`** — `common/utils/financial-math.ts` (buy + sell fee computation)
2. **`EdgeCalculatorService.buildFeeBreakdown()`** — `modules/arbitrage-detection/edge-calculator.service.ts` (buy + sell fee breakdown)
3. **`ExitMonitorService.evaluatePosition()`** — `modules/exit-management/exit-monitor.service.ts` lines ~207-223 (threshold eval fees at current exit price)
4. **`ExitMonitorService` realized PnL** — `modules/exit-management/exit-monitor.service.ts` lines ~455-462 (exit fees at actual fill price)
5. **`SingleLegResolutionService`** — `modules/execution/single-leg-resolution.service.ts` lines 374-376 (close fee at close fill price)
6. **`single-leg-pnl.util.ts`** — `calcCloseNow` and `calcRetry` functions (accept optional `takerFeeForPrice` callbacks, compute per-price)

### 4.5 Rounding Behavior (confirmed via research)

Kalshi's "round up" means **ceiling to the next cent** on the **total batch fee**:
- Formula: `totalFee = ceil_to_cent(0.07 × C × P × (1-P))`
- The `takerFeeForPrice` callback returns the **rate** (fee fraction per unit price), NOT the rounded dollar amount
- Rounding is applied at consumption sites after multiplying rate × price × quantity, using `Decimal.ROUND_UP` to 2 decimal places
- This matches Kalshi's semantics: rounding applies to the total fee invoice, not per-contract

### 4.6 Call Site Updates (2 locations)

Both call sites for `calculateSingleLegPnlScenarios` must pass through `takerFeeForPrice` callbacks from FeeSchedule:

1. **`execution.service.ts`** lines ~873-901
2. **`single-leg-resolution.service.ts`** lines ~558-584

Changes: resolve `FeeSchedule` per platform, pass `takerFeeForPrice` and `secondaryTakerFeeForPrice` to the PnL utility.

`SingleLegPnlInput` interface extended with:
```typescript
takerFeeForPrice?: (price: number) => number;
secondaryTakerFeeForPrice?: (price: number) => number;
```

### 4.7 Test Updates

**Mock factory** (`test/mock-factories.ts`):
- Kalshi `takerFeePercent: 0 → 1.75`
- Add `takerFeeForPrice` callback for Kalshi mocks

**Assertion fixes:**
- `kalshi.connector.spec.ts`: `toBe(0)` → `toBe(1.75)` + dynamic fee formula tests
- `mock-factories.spec.ts`: `toBe(0)` → `toBe(1.75)`

**Inline mock updates** (~6 spec files with explicit Kalshi fee mocks):
- Add `takerFeeForPrice` lambda to each Kalshi mock

**New comprehensive tests:**
- `financial-math.spec.ts`: 5 new test cases covering dynamic fee path, fallback, edge prices, midpoint, both-sides dynamic
- `edge-calculator.service.spec.ts`: tests for `buildFeeBreakdown` with dynamic Kalshi fees
- `kalshi.connector.spec.ts`: formula correctness tests across price range + boundary tests

### 4.8 Serialization Safety Verification (from LAD review)

Verify that no event payload or audit log serializes raw `FeeSchedule` objects (the `takerFeeForPrice` callback would be stripped by `JSON.stringify()`). Event payloads must only carry computed fee costs as numbers. Files to verify:
- `common/events/execution.events.ts` — `OpportunityIdentifiedEvent`, `SingleLegExposureEvent`
- `common/events/detection.events.ts` — `OpportunityFilteredEvent`
- `modules/monitoring/` event consumers

### 4.9 PRD Update

**File:** `_bmad-output/planning-artifacts/prd.md`

**Fee Normalization section** (lines 1249-1254):
- Replace "Kalshi: 1.5% taker fee → 0.015 multiplier" with dynamic formula documentation
- Document `takerFeeForPrice` callback pattern

**Edge Calculation example** (lines 1223-1228):
- Update Kalshi fee from flat 1.5% to dynamic formula at P=0.62
- Recalculate net edge result

---

## Section 5: Implementation Handoff

**Scope classification:** Minor — direct implementation by dev agent

**New story:** `6-5-5g-kalshi-dynamic-fee-correction`

**Sequencing:** Must complete before story 6-5-5 (paper execution validation)

**Success criteria:**

- [ ] `FeeSchedule` interface has optional `takerFeeForPrice` field
- [ ] `KalshiConnector.getFeeSchedule()` returns `takerFeePercent: 1.75` + `takerFeeForPrice` callback
- [ ] `FinancialMath.calculateTakerFeeRate()` centralized helper added with tests
- [ ] All 6 consumer locations use the centralized helper (no inline callback-or-fallback logic)
- [ ] Rounding: total batch fee rounded up to next cent (`ROUND_UP` to 2 dp) at consumption sites
- [ ] Serialization verified: no event payload carries raw `FeeSchedule` objects (callback would be stripped)
- [ ] All existing tests pass with updated mocks
- [ ] New tests cover: formula correctness, fallback path, price edge cases, helper method, integration through calculateNetEdge and buildFeeBreakdown
- [ ] PRD fee normalization section corrected
- [ ] `pnpm lint` and `pnpm test` pass clean
