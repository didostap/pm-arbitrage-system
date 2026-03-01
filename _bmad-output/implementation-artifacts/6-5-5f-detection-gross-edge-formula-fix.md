# Story 6.5.5f: Detection Gross Edge Formula Fix

Status: done

## Story

As an operator,
I want the arbitrage detection engine to use a correct gross edge formula that rejects guaranteed-loss trades,
so that paper trading validation produces only genuine arbitrage opportunities and I can trust the system before going live.

## Background / Root Cause

**Critical blocker for Stories 6-5-5 (Paper Execution Validation) and 6-5-6 (Validation Report).**

The detection engine's `calculateGrossEdge()` formula produces false-positive arbitrage opportunities. The formula `|buyPrice - (1 - sellPrice)|` uses complement math with `abs()` that inflates guaranteed-loss trades into apparent high-edge opportunities when both platforms price an event similarly (both YES prices low, or both high).

**Evidence from paper trading:**

- DB record: Polymarket buy at 0.16, Kalshi sell at 0.01, expected_edge = 0.83
- P&L analysis: -$0.15 per contract pair in ALL outcomes (guaranteed loss)
- Size asymmetry: 4362 Kalshi contracts vs 32 Polymarket (caused by `idealSize = capital / 0.01`)
- Code trace: `financial-math.ts:29` formula and `detection.service.ts:163` direction check both rely on flawed complement logic
- Formula: `|0.16 - (1 - 0.01)| = |0.16 - 0.99| = 0.83` — abs() hides that this is a losing trade

**Correct formula:** For cross-platform YES arbitrage: `sellBid - buyAsk`. Sign encodes direction — positive means profitable, negative means guaranteed loss. No `abs()`.

## Acceptance Criteria

1. **Given** two prices where sell > buy (valid arb: buy YES at 0.40, sell YES at 0.55)
   **When** `calculateGrossEdge(0.40, 0.55)` is called
   **Then** the result is 0.15 (positive — profitable trade)

2. **Given** two prices where both are low (false positive: buy at 0.16, sell at 0.01)
   **When** `calculateGrossEdge(0.16, 0.01)` is called
   **Then** the result is -0.15 (negative — guaranteed loss, rejected by detection)

3. **Given** two prices where both are high (false positive: buy at 0.92, sell at 0.88)
   **When** `calculateGrossEdge(0.92, 0.88)` is called
   **Then** the result is -0.04 (negative — guaranteed loss, rejected by detection)

4. **Given** equal prices (buy at 0.50, sell at 0.50)
   **When** `calculateGrossEdge(0.50, 0.50)` is called
   **Then** the result is 0 (zero edge — no arb)

5. **Given** the detection service evaluates a pair where both platforms agree on probability direction
   **When** `detectDislocations()` runs
   **Then** no dislocation is created (the `grossEdge > 0` check filters it out since grossEdge is now signed)

6. **Given** the detection service finds a genuine arb (sell bid > buy ask)
   **When** `detectDislocations()` runs
   **Then** a dislocation is created with correct prices and positive grossEdge
   **And** the redundant `impliedSellPrice` direction check has been removed

7. **Given** all existing tests (1,251) pass before the change
   **When** the changes are implemented
   **Then** all tests pass with updated expectations
   **And** new false-positive regression tests are added
   **And** `pnpm lint` reports zero errors

## Tasks / Subtasks

- [x] Task 1: Fix `FinancialMath.calculateGrossEdge()` formula (AC: #1, #2, #3, #4)
  - [x] 1.1 In `financial-math.ts`, replace `return buyPrice.minus(new FinancialDecimal(1).minus(sellPrice)).abs()` with `return sellPrice.minus(buyPrice)`
  - [x] 1.2 Update the comment to explain: "Cross-platform arb: buy YES at ask on platform A, sell YES at bid on platform B. Profit per contract = sellBid - buyAsk. Negative means no arb."

- [x] Task 2: Update `financial-math.spec.ts` gross edge test expectations (AC: #1, #2, #3, #4)
  - [x] 2.1 The CSV file `edge-calculation-scenarios.csv` uses the OLD formula to compute `expected_gross_edge`. Update the CSV header comment to reflect the new formula: `grossEdge = sellPrice - buyPrice`
  - [x] 2.2 Recalculate ALL `expected_gross_edge` values in the CSV using `sell_price - buy_price` (no abs, no complement)
  - [x] 2.3 Recalculate ALL `expected_net_edge` values that depend on `expected_gross_edge` — netEdge formula: `grossEdge - buyFeeCost - sellFeeCost - gasFraction`
  - [x] 2.4 Recalculate `expected_passes_filter` for any scenario where net edge sign or threshold crossing changes
  - [x] 2.5 Add new CSV regression rows: "both_low_false_positive" (buy=0.16, sell=0.01, grossEdge=-0.15), "both_high_false_positive" (buy=0.92, sell=0.88, grossEdge=-0.04), "valid_arb_sell_gt_buy" (buy=0.40, sell=0.55, grossEdge=0.15)
  - [x] 2.6 Verify NaN/Infinity guard tests still pass (they test input validation, not the formula)

- [x] Task 3: Update `financial-math.property.spec.ts` property tests (AC: #7)
  - [x] 3.1 Remove or update the "complementary pricing symmetry" property test — the new formula does NOT have `grossEdge(buy, sell) === grossEdge(1-sell, 1-buy)` symmetry
  - [x] 3.2 Update "result <= 1" property — result can now be negative (range is [-1, 1]), so update to `result >= -1 && result <= 1`
  - [x] 3.3 Update "boundary: grossEdge(0.5, 0.5) yields 0" — this still holds, keep as-is
  - [x] 3.4 Add new property: "grossEdge is antisymmetric: grossEdge(a, b) === -grossEdge(b, a)" — verifying `sellPrice - buyPrice === -(buyPrice - sellPrice)`
  - [x] 3.5 Update the composition chain test: "if grossEdge is computed, netEdge <= grossEdge" — this property still holds since fees/gas only subtract; but grossEdge can now be negative, so the assertion may need revisiting if it assumes grossEdge >= 0
  - [x] 3.6 Add new property: "grossEdge > 0 iff sellPrice > buyPrice" — the sign correctly encodes trade direction

- [x] Task 4: Remove redundant direction checks in `DetectionService.detectDislocations()` (AC: #5, #6)
  - [x] 4.1 In Scenario A (~lines 152-165): Remove `const impliedSellPrice = new FinancialDecimal(1).minus(kalshiSellPrice)` and the inner `if (polyBuyPrice.lessThan(impliedSellPrice))` check. The `if (grossEdgeA.greaterThan(0))` alone is now sufficient since grossEdge is signed
  - [x] 4.2 In Scenario B (~lines 180-193): Same removal — remove `impliedSellPrice` computation and inner `if` check
  - [x] 4.3 Result: each scenario becomes `if (grossEdge.greaterThan(0)) { dislocations.push(...) }`

- [x] Task 5: Update `detection.service.spec.ts` tests (AC: #5, #6)
  - [x] 5.1 Remove any tests that assert `impliedSellPrice` behavior (search found: none exist as named tests, but check inline assertions)
  - [x] 5.2 Add test: "rejects pair when both platforms agree unlikely" — set both asks high, both bids low → grossEdge negative → no dislocation
  - [x] 5.3 Add test: "rejects pair when both platforms agree likely" — set both asks low, both bids high, but sellBid < buyAsk → grossEdge negative → no dislocation
  - [x] 5.4 Update any existing test expectations where grossEdge values are asserted with the old formula's output

- [x] Task 6: Update `edge-calculator.service.spec.ts` `makeDislocation` helper (AC: #7)
  - [x] 6.1 Current defaults: `buyPrice: 0.52, sellPrice: 0.45, grossEdge: 0.03`. With the new formula: `grossEdge = 0.45 - 0.52 = -0.07` (negative → invalid arb). Update defaults to valid arb prices where `sellPrice > buyPrice`, e.g. `buyPrice: 0.45, sellPrice: 0.52, grossEdge: 0.07`
  - [x] 6.2 Scan ALL `makeDislocation()` overrides in the file for any that use `sellPrice < buyPrice` with positive `grossEdge` — fix to consistent values
  - [x] 6.3 Verify all edge calculator tests still pass with updated defaults

- [x] Task 7: Run full test suite and lint (AC: #7)
  - [x] 7.1 `pnpm test` — all tests pass (updated + new)
  - [x] 7.2 `pnpm lint` — zero errors

## Dev Notes

### Architecture Compliance

- **Module boundaries:** Changes span `common/utils/` (formula fix) and `modules/arbitrage-detection/` (direction check removal). No forbidden imports introduced.
- **Connectors untouched.** Risk management untouched. Execution untouched. Monitoring untouched. Exit management untouched.
- **No new modules, no new files, no schema changes, no new dependencies.**
- **Financial math:** Formula change is pure `decimal.js` — `sellPrice.minus(buyPrice)` replaces `buyPrice.minus(new FinancialDecimal(1).minus(sellPrice)).abs()`. Still uses `Decimal` throughout.
- **Error hierarchy:** No new error types needed.
- **Event system:** No event changes. Detection emits same events with corrected edge values.

### Key Design Decisions

1. **Signed edge, no abs().** The PRD states `|Price_A - Price_B|` but that was ambiguous about what Price_A and Price_B represent. The correct cross-platform arb formula is `sellBid - buyAsk` where sign encodes profitability. Positive = arb exists. Negative = guaranteed loss.

2. **`impliedSellPrice` removal.** The complement-based direction check (`buyPrice < 1 - sellPrice`) was a guard against the old formula's abs() masking direction. With signed grossEdge, `grossEdge > 0` is the sole necessary check. Removing the redundant guard simplifies code and eliminates a semantic mismatch.

3. **No execution service changes needed.** Verified: `ExecutionService` uses `dislocation.buyPrice` and `dislocation.sellPrice` directly. With correct detection inputs (sellPrice > buyPrice when grossEdge > 0), execution records will always show sell > buy entry prices.

4. **CSV recalculation required.** The entire `edge-calculation-scenarios.csv` was built around the old complement formula. Every `expected_gross_edge` and downstream `expected_net_edge` must be recalculated. Some scenarios that were "passing" may now correctly fail, and vice versa.

### File Structure — Exact Files to Modify

| File | Change |
|------|--------|
| `src/common/utils/financial-math.ts` | Replace `calculateGrossEdge` formula: `sellPrice.minus(buyPrice)` instead of complement+abs |
| `src/common/utils/financial-math.spec.ts` | Tests driven by CSV — CSV update propagates |
| `src/common/utils/financial-math.property.spec.ts` | Update/remove complementary symmetry property, update range property, add antisymmetry + sign-direction properties |
| `src/modules/arbitrage-detection/__tests__/edge-calculation-scenarios.csv` | Recalculate all grossEdge/netEdge values with new formula, add false-positive regression rows |
| `src/modules/arbitrage-detection/detection.service.ts` | Remove `impliedSellPrice` computation and inner `if` block in both Scenario A and Scenario B |
| `src/modules/arbitrage-detection/detection.service.spec.ts` | Add false-positive regression tests, update any grossEdge assertions |
| `src/modules/arbitrage-detection/edge-calculator.service.spec.ts` | Update `makeDislocation` defaults to valid arb prices (sellPrice > buyPrice) |

**No new files. No schema changes. No new dependencies. No migration needed.**

### Current Formula (BEFORE — WRONG)

```typescript
// financial-math.ts:25-30
static calculateGrossEdge(buyPrice: Decimal, sellPrice: Decimal): Decimal {
    FinancialMath.validateDecimalInput(buyPrice, 'buyPrice');
    FinancialMath.validateDecimalInput(sellPrice, 'sellPrice');
    return buyPrice.minus(new FinancialDecimal(1).minus(sellPrice)).abs();
}
```

### Target Formula (AFTER — CORRECT)

```typescript
static calculateGrossEdge(buyPrice: Decimal, sellPrice: Decimal): Decimal {
    FinancialMath.validateDecimalInput(buyPrice, 'buyPrice');
    FinancialMath.validateDecimalInput(sellPrice, 'sellPrice');
    // Cross-platform arb: buy YES at ask on platform A, sell YES at bid on platform B.
    // Profit per contract = sellBid - buyAsk. Negative means no arb.
    return sellPrice.minus(buyPrice);
}
```

### Detection Service Direction Check (BEFORE — REDUNDANT)

```typescript
// detection.service.ts — Scenario A (~lines 152-165)
if (grossEdgeA.greaterThan(0)) {
    const impliedSellPrice = new FinancialDecimal(1).minus(kalshiSellPrice);
    if (polyBuyPrice.lessThan(impliedSellPrice)) {
        dislocations.push(/* ... */);
    }
}
```

### Detection Service Direction Check (AFTER — CLEAN)

```typescript
if (grossEdgeA.greaterThan(0)) {
    dislocations.push(/* ... */);
}
```

### CSV Recalculation Guide

New formula: `grossEdge = sell_price - buy_price`

| Scenario | buy_price | sell_price | OLD grossEdge | NEW grossEdge | Notes |
|----------|-----------|------------|---------------|---------------|-------|
| exact_threshold_boundary | 0.52 | 0.45 | 0.03 | -0.07 | Was "passing" — now negative (no arb). Swap or replace. |
| zero_edge | 0.50 | 0.50 | 0 | 0 | Unchanged |
| large_spread | 0.70 | 0.20 | 0.1 | -0.50 | Was valid — now negative (correctly: selling at 0.20 < buying at 0.70 = loss) |

**CRITICAL:** Most existing scenarios have `sellPrice < buyPrice` which made sense under the old complement formula but are LOSING trades under the correct formula. The dev MUST either:
- Swap buy/sell prices to make sellPrice > buyPrice for scenarios that should represent valid arbs
- OR keep original prices but update expected values to negative (for "should be filtered" scenarios)

### Edge Calculator Service — `makeDislocation` Fix

```typescript
// BEFORE (defaults represent losing trade under new formula)
function makeDislocation(overrides?: Partial<RawDislocation>): RawDislocation {
  return {
    buyPrice: new FinancialDecimal(0.52),   // buy at 0.52
    sellPrice: new FinancialDecimal(0.45),  // sell at 0.45 → LOSS
    grossEdge: new FinancialDecimal(0.03),  // old formula said positive
    ...
  };
}

// AFTER (defaults represent valid arb)
function makeDislocation(overrides?: Partial<RawDislocation>): RawDislocation {
  return {
    buyPrice: new FinancialDecimal(0.45),   // buy at 0.45
    sellPrice: new FinancialDecimal(0.52),  // sell at 0.52 → PROFIT
    grossEdge: new FinancialDecimal(0.07),  // 0.52 - 0.45 = 0.07
    ...
  };
}
```

### Previous Story Intelligence

**Story 6-5-5e (Paper Mode Exit Monitor Fix) — DONE:**
- 1,251 tests passing (baseline for this story)
- Exit monitor now mode-aware — paper positions flow through complete lifecycle
- No financial math changes — purely mode threading

**Story 6-5-5d (Telegram Batching & Paper Dedup) — DONE:**
- Event consumer dedup logic reads `pairId` from events — unaffected by edge formula change
- 1,239 → 1,251 tests after 6-5-5e

### Git Intelligence

Recent engine commits (on `epic-7` branch):
```
122e0df Merge remote-tracking branch 'origin/main' into epic-7
ff3d8cd feat: paper mode support in exit monitor (Story 6-5-5e)
c655939 refactor: telegram batching + paper dedup (Story 6-5-5d)
```

### Operational Note

After the fix is deployed, Arbi should review and close any phantom paper positions in the DB that were created by the false-positive formula. This is a prerequisite for the validation report (6-5-6) but is NOT part of this dev story — it's an operator action.

### Scope Guard

This story is strictly scoped to:

1. Fix `calculateGrossEdge()` formula in `financial-math.ts`
2. Remove redundant `impliedSellPrice` checks in `detection.service.ts`
3. Update all test files with corrected expectations
4. Add false-positive regression tests

Do NOT:

- Modify execution layer
- Modify risk management
- Modify exit management
- Modify monitoring/alerting
- Modify connectors
- Add database columns or tables
- Add new error types
- Create new events
- Add configuration flags
- Clean up phantom DB records (operator task)

### Project Structure Notes

- All source changes within `pm-arbitrage-engine/src/` — no root repo changes
- Files follow existing kebab-case naming convention
- Tests co-located with source (`.spec.ts` suffix)
- CSV test data in `modules/arbitrage-detection/__tests__/`

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-03-gross-edge-formula.md] — Approved sprint change proposal with full problem analysis, exact code changes, and P&L proof
- [Source: _bmad-output/planning-artifacts/prd.md] — PRD formula `|Price_A - Price_B|` — ambiguous but closer to correct intent
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.ts, lines 25-30] — Current `calculateGrossEdge` implementation (complement + abs)
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/detection.service.ts, lines 140-193] — Scenario A & B with `impliedSellPrice` direction checks
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.spec.ts, lines 81-93] — CSV-driven gross edge tests
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.property.spec.ts, lines 56-101] — Property-based tests for calculateGrossEdge
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/__tests__/edge-calculation-scenarios.csv] — All 15+ test scenarios with hand-verified values (needs full recalculation)
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.spec.ts, lines 61-84] — `makeDislocation` helper with current defaults
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/detection.service.spec.ts] — Detection service tests (no `impliedSellPrice` named tests found)
- [Source: _bmad-output/implementation-artifacts/6-5-5e-paper-mode-exit-monitor-fix.md] — Previous story context (1,251 tests baseline)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None.

### Completion Notes List

- Formula changed from `|buyPrice - (1 - sellPrice)|` to `sellPrice - buyPrice` — signed result eliminates false positives
- JSDoc comment updated to match new formula (caught by Lad code review)
- `impliedSellPrice` direction checks removed from both Scenario A and B in detection service — `grossEdge > 0` is the sole profitability check
- All 16 existing CSV rows recalculated; most scenarios now correctly show negative grossEdge (losing trades under old formula's complement math)
- Only `inverse_complementary` (buy=0.40, sell=0.52) and new `valid_arb_sell_gt_buy` (buy=0.40, sell=0.55) pass filter as valid arbs
- Property tests: complementary symmetry replaced with antisymmetry and sign-direction properties; range updated to [-1, 1]
- Composition chain property `netEdge <= grossEdge` still holds — fees/gas only subtract, regardless of grossEdge sign
- Edge calculator `makeDislocation` defaults updated: buy=0.45, sell=0.52, edge=0.07 (consistent with new formula)
- Tests using defaults that expected filtering needed grossEdge overrides (0.03) to remain below threshold
- 1263 tests passing (baseline 1251, +12 net new), 0 lint errors

### File List

| File | Change |
|------|--------|
| `src/common/utils/financial-math.ts` | Formula fix: `sellPrice.minus(buyPrice)` + JSDoc update |
| `src/common/utils/financial-math.property.spec.ts` | Replaced complementary symmetry with antisymmetry; updated range [-1,1]; added sign-direction property |
| `src/modules/arbitrage-detection/__tests__/edge-calculation-scenarios.csv` | Recalculated all 16 rows + 3 new regression rows (19 total) |
| `src/modules/arbitrage-detection/detection.service.ts` | Removed `impliedSellPrice` checks in Scenario A and B |
| `src/modules/arbitrage-detection/detection.service.spec.ts` | Updated arb test prices (sell > buy); added 2 false-positive regression tests |
| `src/modules/arbitrage-detection/edge-calculator.service.spec.ts` | Updated `makeDislocation` defaults + overrides for consistent sell > buy prices |
