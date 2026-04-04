# Sprint Change Proposal: Backtest Side Selection Fix & Depth Exit Improvement

**Date:** 2026-04-11
**Triggered by:** Analysis of backtest run `09b344c7-9a02-4701-85ba-649a66f9f763` (Mar 1-5, $10K bankroll) — second validation run after Stories 10-95-8 and 10-95-9 shipped
**Scope Classification:** Minor — 1 new story in existing Epic 10.95, no Prisma migration, no architectural changes
**Status:** APPROVED (2026-04-11)

---

## Section 1: Issue Summary

### Problem Statement

Backtest run `09b344c7` lost **-$1,078.97 (Sharpe -28.89, 8.1% win rate, profit factor 0.15)** after Story 10-95-9 successfully fixed PROFIT_CAPTURE PnL guards, added full-cost accounting, and introduced STOP_LOSS exits. Those fixes are confirmed working (PROFIT_CAPTURE exits are now profitable, STOP_LOSS fires, fees include entry costs). However, two deeper defects remain — one was incorrectly dismissed in the prior course correction (2026-04-10), the other was not investigated.

### Two Root Causes

**1. Side selection is a no-op — `calculateBestEdge()` always returns `buySide = 'polymarket'` (`edge-calculation.utils.ts:9-27`)**

The function computes:
```
edgeA = grossEdge(kalshiClose, 1 - polymarketClose) = (1 - poly) - kalshi
edgeB = grossEdge(polymarketClose, 1 - kalshiClose) = (1 - kalshi) - poly
```

Since `1 - poly - kalshi === 1 - kalshi - poly` (addition is commutative), `edgeA` always equals `edgeB`. The comparison `edgeA.gt(edgeB)` is never true, so `buySide` always falls through to `'polymarket'`. Every position is created as SELL Kalshi / BUY Polymarket, regardless of which platform has the higher price.

When `polymarketPrice > kalshiPrice`, this is anti-arbitrage: selling cheap and buying expensive.

**2. INSUFFICIENT_DEPTH exits triggered by depth cache misses, not actual liquidity problems (`backtest-engine.service.ts:525`)**

`hasDepth = kalshiDepth !== null && polyDepth !== null` — positions are force-closed whenever depth data is missing from the cache for either platform at the current timestamp. This is a data sparsity issue, not a liquidity issue. 87/111 closed positions (78%) exit this way.

### Prior Course Correction Misdiagnosis

The 2026-04-10 course correction explicitly evaluated and dismissed the unidirectional bias:

> *"Also fixing unidirectional bias: Not a bug. If Kalshi consistently prices higher for the same events, SELL K / BUY P is the correct arb direction. The detection engine is working as designed."*

This assessment was incorrect. The DB evidence is unambiguous:

| Price Relationship | Positions | Winners | Losers | Total PnL |
|---|---|---|---|---|
| Kalshi > Poly (correct direction) | 59 | 9 | 50 | -$491.43 |
| **Poly > Kalshi (wrong direction)** | **52** | **0** | **52** | **-$587.54** |

47% of positions have Poly priced higher than Kalshi. 100% of those are losers. The code confirms the mathematical identity — this is definitively a bug, not a feature.

### Discovery Context

Post-10-95-9 validation backtest. Story 10-95-9 successfully fixed PROFIT_CAPTURE guards (7 exits, all profitable at avg +$2.42), added STOP_LOSS (1 triggered), and included full-cost PnL. With those fixes in place, the side-selection and depth exit bugs became the dominant loss drivers.

### Evidence Summary

| Evidence | Detail |
|---|---|
| `calculateBestEdge()` math proof | `edgeA = (1-poly) - kalshi = edgeB = (1-kalshi) - poly` — always equal |
| `calculateGrossEdge()` confirmed | `sellPrice.minus(buyPrice)` at `financial-math.ts:27-34` |
| DB: All positions | 141/141 have `kalshi_side='SELL', polymarket_side='BUY'` |
| DB: POLY_HIGHER group | 52 positions, 0 winners, -$587.54 (54.5% of total loss) |
| DB: KALSHI_HIGHER group | 59 positions, 9 winners, 50 losers, -$491.43 |
| INSUFFICIENT_DEPTH exits | 87/111 closed (78%), -$757.75 total |
| INSUFFICIENT_DEPTH on correct-direction | 40/59 KALSHI_HIGHER positions, -$262.00 |
| Total fees | $1,041.57 on $1,078.97 total loss |
| Exit reason breakdown | INSUF_DEPTH: 87, EDGE_EVAP: 13, PROFIT_CAP: 7, TIME_DECAY: 3, STOP_LOSS: 1 |
| Pair concentration | Top pair (KXLOSEPRIMARYSENATER): 16 trades, -$270.26 |
| Open positions | 30 still open, -$283.26 unrealized PnL |

---

## Section 2: Impact Analysis

### Checklist Results

| # | Item | Status |
|---|------|--------|
| 1.1 | Triggering story identified | [x] Done — Post-Story 10-95-9 backtest validation run `09b344c7` |
| 1.2 | Core problem defined | [x] Done — 2 bugs: side selection no-op + depth cache miss force-close |
| 1.3 | Evidence gathered | [x] Done — DB analysis (141 positions), code proof (commutative identity) |
| 2.1 | Current epic (10.95) impact | [x] Done — 1 new story before retro |
| 2.2 | Epic-level changes needed | [x] Done — Add story 10-95-10 |
| 2.3 | Remaining epics reviewed | [x] Done — Epic 11, 12 unaffected |
| 2.4 | New epics needed | [x] Done — No |
| 2.5 | Epic ordering | [x] Done — No resequencing |
| 3.1 | PRD conflicts | [x] Done — FR-AD-02 clarification added (side selection determinism) |
| 3.2 | Architecture conflicts | [x] Done — Side selection and depth exit invariants added |
| 3.3 | UI/UX conflicts | [N/A] — No dashboard changes |
| 3.4 | Other artifacts | [x] Done — Test gap in edge-calculation.utils.spec.ts to close |
| 4.1 | Direct Adjustment viable | [x] Viable — Effort: Low, Risk: Low |
| 4.2 | Rollback viable | [N/A] — Original defect, not regression |
| 4.3 | MVP Review needed | [N/A] — MVP complete |
| 4.4 | Recommended path | [x] Done — Direct Adjustment (1 new story in 10.95) |

### Epic Impact

**Epic 10.95 (in-progress):** Add story 10-95-10 after 10-95-9. Epic scope ("TimescaleDB Migration & Backtesting Quality") covers this. Story 10-95-10 becomes the final story before retro.

**Epic 11, 12 (backlog):** No changes needed.

### Artifact Changes Applied

| Artifact | Change | Status |
|---|---|---|
| `prd.md` (FR-AD-02) | Added "Clarification CC 2026-04-11 — Side Selection Determinism" | Applied |
| `architecture.md` (Backtesting module) | Added side selection invariant and depth exit invariant (CC 2026-04-11) | Applied |
| `epics.md` (Epic 10.95) | Added Story 10-95-10 definition | Applied |
| `sprint-status.yaml` | Added `10-95-10-backtest-side-selection-depth-exit-fix: backlog` | Applied |

---

## Section 3: Recommended Approach

### Selected: Direct Adjustment — 1 New Story in Epic 10.95

**Rationale:**
- **Low effort.** The side-selection fix is ~5-10 lines (replace edge comparison with price comparison). The depth exit change is a semantic adjustment to `hasDepth` logic.
- **Low risk.** No module boundary crossings. No Prisma migrations. No new DB fields (buySide is in-memory only; `kalshi_side`/`polymarket_side` DB columns already exist and will now vary correctly).
- **Critical for backtest trustworthiness.** Until side selection is fixed, 47% of positions enter anti-arbitrage. Until depth exits are fixed, 78% of positions are force-closed spuriously. Backtest results are meaningless with either bug present.
- **Validates full 10.95 quality pipeline.** A clean backtest after this fix validates the entire chain: 10-95-8 (zero-price filtering, exit fees) → 10-95-9 (PROFIT_CAPTURE PnL guard, full-cost accounting, STOP_LOSS) → 10-95-10 (side selection, depth exits).

**Trade-offs considered:**
- *Splitting into two stories (side selection + depth exit):* Each is undersized at ~3-4 tasks. Combined (~8 tasks) is right-sized and shares the validation backtest.
- *Also adding fee optimization (larger positions, higher edge floor):* Deferred. Fee impact may look different after wrong-direction trades and spurious exits are eliminated. Re-evaluate after validation re-run.
- *Fixing the live detection engine too:* The live detection engine uses a different code path. If it has the same bug, that's a separate story. This story scopes to the backtest engine only.

---

## Section 4: Detailed Change Proposals

### Story 10-95-10: Backtest Side Selection Fix & Depth Exit Improvement

*(Full story definition written to `epics.md` — see artifact changes above)*

**Summary of 8 tasks:**
1. Fix `calculateBestEdge()` — price comparison instead of edge comparison
2. Fix depth exit logic — cache miss ≠ insufficient depth
3. Add `buySide` to `SimulatedPosition`
4. Update `calculateCurrentEdge()` for directional consistency
5. Regression tests for side selection
6. Regression tests for depth exit
7. Update existing tests
8. Validation backtest

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

Focused correctness fix within an existing epic. No schema migrations. No cross-module refactoring.

### Handoff Recipients

| Role | Responsibility |
|---|---|
| **Scrum Master (Bob)** | Update artifacts (done). Sprint status updated. |
| **Dev Agent** | Implement story 10-95-10 following TDD workflow. |
| **Operator (Arbi)** | Re-run Mar 1-5 backtest after fix. Compare metrics against `09b344c7`. |

### Sequencing

```
Epic 10.95 (in-progress):
  10-95-1 through 10-95-8: DONE
  10-95-9: ready-for-dev (exit logic + full-cost PnL)
  |
  NEW → 10-95-10: backlog (side selection + depth exit)
  |
  epic-10-95-retrospective
  |
  Epic 11: Platform Extensibility & Security Hardening
```

### Success Criteria

1. `calculateBestEdge()` returns different `buySide` values depending on which platform has the higher price
2. Backtest positions show BOTH `SELL K / BUY P` and `BUY K / SELL P` directions
3. INSUFFICIENT_DEPTH exits < 30% of closed positions (down from 78%)
4. Zero wrong-direction positions (0 positions where buySide contradicts price relationship)
5. Win rate improves significantly from the 8.1% baseline
6. All existing tests pass; new regression tests cover side selection and depth exit
7. Re-run of Mar 1-5 backtest produces trustworthy, bidirectional results

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Fix reveals additional issues masked by wrong-direction trades | Low | Expected — these would be genuine findings, not regressions |
| `calculateCurrentEdge()` direction flip during holding period | Low | Task 3-4 stores buySide on position for consistency |
| Depth cache miss fallback to mid-price overestimates fill quality | Low | Mid-price is a reasonable approximation; better than force-close |
| Live detection engine has same side-selection bug | Medium | Out of scope for this story; investigate separately after backtest fix ships |

---

## Checklist Completion Summary

| Section | Status |
|---------|--------|
| 1. Trigger & Context | [x] Complete |
| 2. Epic Impact | [x] Complete |
| 3. Artifact Conflicts | [x] Complete — PRD, Architecture updated |
| 4. Path Forward | [x] Complete — Direct Adjustment selected |
| 5. Proposal Components | [x] Complete — 1 story defined |
| 6. Final Review | [x] Complete — Approved 2026-04-11 |
