# Sprint Change Proposal — Gross Edge Formula False-Positive Fix

**Date:** 2026-03-03
**Triggered by:** Paper trading observation (Epic 6.5)
**Scope:** Minor — Direct implementation by dev agent
**Status:** Approved

---

## Section 1: Issue Summary

**Problem Statement:** The detection engine's `calculateGrossEdge()` formula produces false-positive arbitrage opportunities. The formula `|buyPrice - (1 - sellPrice)|` uses complement math with `abs()` that inflates guaranteed-loss trades into apparent high-edge opportunities when both platforms price an event similarly (both YES prices low, or both high).

**Discovery Context:** Found during Epic 6.5 (Paper Trading Validation) by examining an `OpenPosition` record in the database. The entry prices `{"kalshi": "0.01", "polymarket": "0.16"}` with expected edge 0.83 were immediately suspicious — both prices low, sell side lower than buy side, yet an enormous reported edge.

**Evidence:**

- DB record: Polymarket buy at 0.16, Kalshi sell at 0.01, expected_edge = 0.83
- P&L analysis: -$0.15 per contract pair in ALL outcomes (guaranteed loss)
- Size asymmetry: 4362 Kalshi contracts vs 32 Polymarket (caused by `idealSize = capital / 0.01`)
- Code trace: `financial-math.ts:29` formula and `detection.service.ts:163` direction check both rely on flawed complement logic
- Formula: `|0.16 - (1 - 0.01)| = |0.16 - 0.99| = 0.83` — abs() hides that this is a losing trade

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Status | Impact |
|------|--------|--------|
| Epic 3 (Arbitrage Detection) | done | Origin of bug (stories 3-2, 3-3). No re-opening; fix is hotfix in current sprint. |
| Epic 6.5 (Paper Validation) | in-progress | **Blocked** — stories `6-5-5` and `6-5-6` cannot proceed until fix deployed. |
| Epic 7 (Dashboard) | in-progress | Indirect — displays whatever engine produces. No code changes needed. |
| Epic 10 (Model-Driven Exits) | backlog | Story 10-1 (continuous edge recalculation) will consume `calculateGrossEdge`. Fix ensures correct values downstream. |
| All other epics | — | No impact. |

### Story Impact

No existing stories require modification. One new hotfix story inserted into Epic 6.5.

### Artifact Conflicts

- **PRD:** No conflict. PRD's stated formula `|Price_A - Price_B|` is closer to correct. Fix aligns implementation to PRD intent.
- **Architecture:** No conflict. Fix is within existing `FinancialMath` utility and `DetectionService`.
- **Testing:** Existing tests built around complement formula need updating. New false-positive regression tests required.

### Technical Impact

- 2 source files modified (`financial-math.ts`, `detection.service.ts`)
- 3 test files updated (`financial-math.spec.ts`, `detection.service.spec.ts`, `edge-calculator.service.spec.ts`)
- 1 operational DB cleanup step
- Zero infrastructure, deployment, or dependency changes

---

## Section 3: Recommended Approach

**Selected Path: Direct Adjustment**

Insert a single hotfix story `6-5-5f-detection-gross-edge-formula-fix` into Epic 6.5 before `6-5-5-paper-execution-validation`.

**Rationale:**

- Minimal disruption — one story, ~4-8 hours, no architectural changes
- Low risk — formula is mathematically verifiable, well-isolated module
- Unblocks Epic 6.5 validation immediately
- Aligns code back to PRD's stated intent

**Alternatives considered:**

- **Rollback (Option 2):** Rejected — would destroy months of working detection infrastructure to fix a one-line formula
- **MVP Review (Option 3):** Rejected — not needed, MVP scope and thesis are valid, this is an implementation bug

---

## Section 4: Detailed Change Proposals

### Code Changes

#### Change 1: Fix `FinancialMath.calculateGrossEdge()`

**File:** `pm-arbitrage-engine/src/common/utils/financial-math.ts`

**OLD:**
```typescript
static calculateGrossEdge(buyPrice: Decimal, sellPrice: Decimal): Decimal {
    FinancialMath.validateDecimalInput(buyPrice, 'buyPrice');
    FinancialMath.validateDecimalInput(sellPrice, 'sellPrice');

    return buyPrice.minus(new FinancialDecimal(1).minus(sellPrice)).abs();
}
```

**NEW:**
```typescript
static calculateGrossEdge(buyPrice: Decimal, sellPrice: Decimal): Decimal {
    FinancialMath.validateDecimalInput(buyPrice, 'buyPrice');
    FinancialMath.validateDecimalInput(sellPrice, 'sellPrice');

    // Cross-platform arb: buy YES at ask on platform A, sell YES at bid on platform B.
    // Profit per contract = sellBid - buyAsk. Negative means no arb.
    return sellPrice.minus(buyPrice);
}
```

**Rationale:** The original formula uses a complement that conflates "selling YES at bid" with "buying NO at complement cost". The `abs()` hides direction, allowing guaranteed-loss trades to appear as high-edge opportunities. The correct formula for same-event cross-platform YES arbitrage is `sellBid - buyAsk`. Sign encodes direction.

#### Change 2: Remove redundant direction checks in `DetectionService`

**File:** `pm-arbitrage-engine/src/modules/arbitrage-detection/detection.service.ts`

Remove the `impliedSellPrice` computation and nested `if` block in both Scenario A (~lines 163-165) and Scenario B (~lines 185-187).

**OLD (both scenarios):**
```typescript
if (grossEdgeA.greaterThan(0)) {
    const impliedSellPrice = new FinancialDecimal(1).minus(kalshiSellPrice);
    if (polyBuyPrice.lessThan(impliedSellPrice)) {
        dislocations.push(/* ... */);
    }
}
```

**NEW (both scenarios):**
```typescript
if (grossEdgeA.greaterThan(0)) {
    dislocations.push(/* ... */);
}
```

**Rationale:** `grossEdge > 0` now correctly encodes `sellBid > buyAsk`. The complement-based direction check is redundant and semantically wrong against the new formula.

#### Change 3: No change to `ExecutionService`

Verified: execution correctly uses `dislocation.buyPrice` for buy orders and `dislocation.sellPrice` for sell orders. Entry prices record the limit order prices submitted. With correct detection inputs, entry prices will always show sell > buy.

### Test Changes

| File | Change |
|------|--------|
| `financial-math.spec.ts` | Update `calculateGrossEdge` expectations to signed result. Add regression: "both low" (0.16, 0.01) → -0.15, "both high" (0.92, 0.88) → -0.04, "valid arb" (0.40, 0.55) → 0.15, "equal" (0.50, 0.50) → 0. |
| `detection.service.spec.ts` | Remove `impliedSellPrice` assertion tests. Add: "both platforms agree unlikely" → no dislocation. "Both agree likely" → no dislocation. |
| `edge-calculator.service.spec.ts` | Update `makeDislocation` helpers to use valid arb prices (sellPrice > buyPrice). Verify net edge calculations with corrected gross edge. |

### Operational

| Action | Rationale |
|--------|-----------|
| Review and close phantom paper positions in DB | Clean data prerequisite for validation report (6-5-6) |

---

## Section 5: Implementation Handoff

**New Story:** `6-5-5f-detection-gross-edge-formula-fix`
**Inserted into:** Epic 6.5, before `6-5-5-paper-execution-validation`
**Scope:** Minor — direct dev implementation via TDD

**Handoff Responsibilities:**

| Role | Responsibility |
|------|---------------|
| Dev agent | Implement formula fix, update tests, verify all existing tests pass |
| Operator (Arbi) | Review phantom paper positions, clean DB, verify fix with fresh paper execution cycle |

**Success Criteria:**

- `calculateGrossEdge(0.16, 0.01)` returns -0.15 (negative → rejected by detection)
- `calculateGrossEdge(0.40, 0.55)` returns 0.15 (positive → valid arb)
- Zero false-positive dislocations when both platforms agree on event probability direction
- All existing tests pass (with updated expectations)
- Paper execution produces positions where sell-side entry price > buy-side entry price

**Unblocks:** `6-5-5-paper-execution-validation` and `6-5-6-validation-report-epic-7-readiness`
