# Sprint Change Proposal: Take-Profit Negative Threshold Fix

**Date:** 2026-03-05
**Triggered by:** Live paper trading observation — TP triggering with negative P&L
**Scope classification:** Minor (direct implementation by dev team)
**Approved by:** Arbi

---

## Section 1: Issue Summary

### Problem Statement

The Take Profit (TP) threshold formula introduced in Story 6.5.5i produces **negative thresholds** for positions where entry costs (bid-ask spread + exit fees) exceed 80% of the scaled initial edge. This causes the system to close positions at a realized loss, labeled as "take_profit."

### Discovery Context

Observed during Epic 6.5 paper trading validation with live market data. A paper position on the KXLOSEMAJORITY-27JAN01 contract pair exhibited a TP threshold of -$4.41 against an entry cost baseline of -$5.73. The position's convergence profit is +$1.65 — triggering TP at -$4.41 would destroy $6.06 of potential profit.

### Evidence

Live paper position `8e0c3a7d` (2026-03-05):

| Metric | Value |
|--------|-------|
| Entry cost baseline | -$5.73 |
| Scaled initial edge | $1.65 |
| TP threshold (current formula) | **-$4.41** |
| SL threshold | -$9.03 |
| Convergence P&L | +$1.65 |
| Potential profit destroyed by premature TP | **up to $6.06** (assumes full convergence) |

Spread data (real order books via paper trading connector):
- Kalshi: filled sell at 0.2099, close-side ask at 0.26 (5-cent spread)
- Polymarket: filled buy at 0.1703, close-side bid at 0.15 (2-cent spread)
- Total spread cost: $4.64 vs scaled edge: $1.65 (2.8:1 ratio)

### Root Cause

The TP formula uses a convergence-based edge metric (`scaledInitialEdge`) as the improvement target from an early-exit baseline (`entryCostBaseline`). These two operands live in different frames of reference:

- `entryCostBaseline` reflects early-exit reality (spreads + fees to close now)
- `scaledInitialEdge` reflects convergence/resolution profit (no exit spread)

The formula `entryCostBaseline + 0.80 x scaledInitialEdge` measures "80% of the convergence edge above baseline" but should measure "80% of the total achievable improvement from entry MtM to convergence."

### Prior Design Decision (Superseded)

Story 6.5.5i's Dev Notes (line 245-247) explicitly acknowledged negative TP thresholds and declared them "expected and correct," reasoning that wide-spread positions "are not designed for profitable early exit" and TP serves as a "best achievable early exit." This reasoning is flawed: if a position's profit path is resolution, triggering TP at a loss actively prevents that resolution profit. The correct behavior is for TP to not trigger at all, letting the position reach convergence.

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact |
|------|--------|
| Epic 6.5 (Paper Trading Validation) | Add story 6-5-5j to 6.5.5x series. No scope change. |
| Epic 7 (Dashboard) | Story 7.5's proximity display fix remains correct. Enrichment service mirrors the formula change. |
| Epic 10 (Model-Driven Exits) | Story 10.2 will replace fixed thresholds entirely. No conflict. |
| All other epics | No impact. |

### Story Impact

- **6-5-5j (new):** Take-Profit Negative Threshold Fix — the fix story
- **6-5-5 (backlog):** Paper Execution Validation — should run after this fix lands
- **6-5-6 (backlog):** Validation Report — should run after this fix lands

### Artifact Conflicts

- **PRD:** No conflict. FR-EM-01 specifies "80% edge take-profit" — the journey formula better implements this than the current formula.
- **Architecture:** No changes. Fix is internal to `ThresholdEvaluatorService.evaluate()`.
- **Epics:** No structural changes. Story addition to existing series.
- **Story 6.5.5i Dev Notes:** The "Design Note — Take-Profit via Early Exit" is superseded by this proposal's analysis. The new story will document the corrected reasoning.
- **Story 7.5:** Its claim that "exit trigger logic works correctly" is invalidated, but its actual code changes (proximity formulas) remain correct.

### Technical Impact

Two files modified, identical formula change in both:
- `src/modules/exit-management/threshold-evaluator.service.ts` (exit trigger)
- `src/dashboard/position-enrichment.service.ts` (dashboard display)

No schema changes, no new events, no new error codes, no module boundary changes.

---

## Section 3: Recommended Approach

**Path:** Direct Adjustment — add story 6-5-5j to the existing 6.5.5x bugfix series.

### The Fix

Replace the TP threshold formula from:

```
takeProfitThreshold = entryCostBaseline + 0.80 x scaledInitialEdge
```

To journey-based with floor:

```
takeProfitThreshold = max(0, entryCostBaseline + 0.80 x (scaledInitialEdge - entryCostBaseline))
```

Which simplifies to: `max(0, 0.20 x entryCostBaseline + 0.80 x scaledInitialEdge)`

### Behavior Change

| Scenario | Baseline | Edge | Current | Journey + Floor |
|----------|----------|------|---------|-----------------|
| Legacy (no baseline) | $0 | $3.00 | $2.40 | $2.40 (identical) |
| Moderate spread | -$1.00 | $3.00 | $1.40 | $2.20 |
| Real position | -$5.73 | $1.65 | **-$4.41** | **+$0.17** |
| Extreme spread | -$20 | $1.00 | -$19.20 | **$0.00** (floor) |

- **Legacy positions (baseline = 0):** Zero change. No regression risk.
- **Normal positions:** TP threshold moves higher (e.g., $1.40 -> $2.20 in the moderate-spread example). **This is a behavioral change for positions that were not exhibiting the negative-threshold bug.** It is acceptable because 6.5.5i inadvertently lowered TP thresholds as a side effect of adding the baseline offset — the journey formula restores them closer to the pre-6.5.5i values ($2.40 legacy vs $2.20 journey). These positions will hold slightly longer and capture more profit before exit.
- **Wide-spread positions:** TP produces a meaningful positive target instead of a negative one.
- **Extreme positions:** Floor catches degenerate cases where even the journey formula goes negative.

### SL Unchanged

The stop-loss threshold formula is not affected. SL's "2x edge below baseline" is semantically correct and properly calibrated per 6.5.5i. The frame mismatch is TP-specific.

### Rationale

- Minimal change (two files, identical formula)
- Zero legacy regression (baseline = 0 produces identical results)
- Consistent with 6.5.5x series pattern (nine prior stories)
- Additive constraint — no existing correct behavior is removed
- Formula fix produces meaningful targets; floor is belt-and-suspenders

### Risk Assessment

- **Effort:** Low (< 1 story point)
- **Risk:** Low (additive constraint, zero regression for legacy positions)
- **Timeline impact:** None (fits in current sprint)

---

## Section 4: Detailed Change Proposals

### Change 1: `threshold-evaluator.service.ts` (Core Fix)

**Location:** `evaluate()` method, lines 152-161

**OLD:**
```typescript
// Priority 2: Take-profit — currentPnl >= entryCostBaseline + 0.80 * initialEdge * legSize
const takeProfitThreshold = entryCostBaseline.plus(
  scaledInitialEdge.mul(new Decimal('0.80')),
);
if (currentPnl.gte(takeProfitThreshold)) {
```

**NEW:**
```typescript
// Priority 2: Take-profit — 80% of total journey from entry MtM to convergence, floored at zero
const takeProfitThreshold = Decimal.max(
  new Decimal(0),
  entryCostBaseline.plus(
    scaledInitialEdge.minus(entryCostBaseline).mul(new Decimal('0.80')),
  ),
);
if (currentPnl.gte(takeProfitThreshold)) {
```

### Change 2: `position-enrichment.service.ts` (Mirror)

**Location:** `enrich()` method, lines 219-224

**OLD:**
```typescript
const takeProfitThreshold = entryCostBaseline.plus(
  scaledInitialEdge.mul(new Decimal('0.80')),
);
```

**NEW:**
```typescript
const takeProfitThreshold = Decimal.max(
  new Decimal(0),
  entryCostBaseline.plus(
    scaledInitialEdge.minus(entryCostBaseline).mul(new Decimal('0.80')),
  ),
);
```

### Change 3: `sprint-status.yaml`

**Location:** Epic 6.5 block, after line 125

Add entry: `6-5-5j-take-profit-negative-threshold-fix: backlog`

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

Direct implementation by development team (dev agent).

### Handoff

- **Dev agent:** Implement story 6-5-5j via the Create Story (CS) workflow, then TDD implementation
- **SM (Bob):** Create the story file via CS workflow with this proposal as input
- **Tests required:** Targeted scenarios for negative threshold (journey formula produces positive target), floor activation (extreme spreads), legacy regression (baseline = 0 unchanged), and normal position behavior change (threshold moves higher)

### 6.5.5i Artifact Supersession

The new story (6-5-5j) must append a supersession note to `_bmad-output/implementation-artifacts/6-5-5i-exit-threshold-calibration-fix.md` at the "Design Note -- Take-Profit via Early Exit" section (line 245), pointing to 6-5-5j's corrected analysis. Without this, anyone reading 6.5.5i in isolation would still believe negative TP thresholds are by design.

### Follow-up Tech Debt (Not in this story)

Extract TP/SL threshold computation into shared `FinancialMath` utility functions (`computeTakeProfitThreshold`, `computeStopLossThreshold`) to eliminate formula duplication between `threshold-evaluator.service.ts` and `position-enrichment.service.ts`. Same pattern as `computeEntryCostBaseline` extraction in 6.5.5i code review fix M2.

### Success Criteria

1. No position triggers TP with negative P&L
2. Legacy positions (null entry close prices, baseline = 0) produce identical thresholds
3. Given entryCostBaseline = -$5.73 and scaledInitialEdge = $1.65, the formula produces +$0.17 (not -$4.41)
4. All existing tests pass + new tests for journey formula and floor
5. `pnpm lint` reports zero errors

---

## References

- [Source: _bmad-output/implementation-artifacts/6-5-5i-exit-threshold-calibration-fix.md] — Story that introduced entryCostBaseline and the flawed TP design note
- [Source: _bmad-output/implementation-artifacts/7-5-exit-proximity-display-fix.md] — Story that fixed display but asserted trigger logic was correct
- [Source: _bmad-output/implementation-artifacts/5-4-exit-monitoring-fixed-threshold-exits.md] — Original exit monitoring story with threshold evaluator
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts:152-161] — TP threshold formula to fix
- [Source: pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts:219-224] — Mirror formula to fix
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.ts:130-201] — computeEntryCostBaseline utility
