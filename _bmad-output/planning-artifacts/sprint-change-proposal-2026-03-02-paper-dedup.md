# Sprint Change Proposal — Paper Mode Duplicate Opportunity Prevention

**Date:** 2026-03-02
**Author:** Bob (Scrum Master Agent)
**Triggered by:** Pre-validation discovery during Epic 6.5 preparation
**Scope Classification:** Minor
**Status:** Approved

---

## Section 1: Issue Summary

### Problem Statement

In paper trading mode, a single arbitrage opportunity can be re-triggered repeatedly across consecutive detection cycles because simulated paper fills do not consume liquidity from the cached order books. This produces inflated trade counts, distorted P&L, and unreliable validation metrics — defeating the purpose of paper trading validation (Epic 6.5).

### Discovery Context

Identified during preparation for Story 6-5-5 (Paper Execution Validation). Code analysis confirmed that no per-pair deduplication guard exists anywhere in the detection → risk → execution pipeline. In live mode, real fills naturally shift order book prices and eliminate the stale dislocation. In paper mode, the order book never changes after a simulated fill.

### Evidence

- `TradingEngineService.executeCycle()` generates a unique `opportunityId` per cycle via `Date.now()` suffix — no natural deduplication key
- `RiskManagerService.validatePosition()` checks halt status, max pairs, and capital — never checks whether a position already exists on the same pair
- `RiskManagerService.reserveBudget()` similarly has no pair-level check
- Paper connectors intercept `submitOrder()` but do not modify in-memory order book state
- Result: identical dislocation re-detected → re-approved → re-executed every polling cycle

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| Epic 6.5 (Paper Trading Validation) | **Direct** | Fix is a prerequisite for Story 6-5-5 to produce trustworthy validation data |
| Epic 7 (Dashboard) | None | Dashboard consumes events, doesn't affect detection/execution |
| Epics 8-12 | None | Downstream or parallel concerns |

No new epics needed. No epic reordering or priority changes.

### Story Impact

- **Story 6-5-5 (Paper Execution Validation):** Add deduplication as acceptance criterion, or insert a small preceding story (6-5-5c)
- No other stories affected

### Artifact Conflicts

| Artifact | Conflict | Details |
|----------|----------|---------|
| PRD | None | PRD states paper trading should provide accurate validation — fix supports intent |
| Architecture | None | Fix lives within existing module boundaries and dependency rules |
| UI/UX Spec | None | No user-facing changes |

### Technical Impact

- **Scope:** `RiskManagerService` (primary), `ReservationRequest` type, `BudgetReservation` type, `TradingEngineService` (pass-through flag)
- **Module boundaries:** Respected — risk management already owns execution gating
- **Connectors:** Untouched
- **Detection layer:** Untouched
- **Database:** No schema changes (in-memory tracking, restored from existing `is_paper` + position status on startup)

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment

**Rationale:** This is a focused correctness fix within existing architecture. The risk validation layer already gates execution — adding per-pair tracking scoped exclusively to paper mode is a natural extension. Zero architectural disruption, zero live-mode behavioral change.

**Effort:** Low (estimated 1 story point)
**Risk:** Low — additive guard, paper-mode-only, no live execution behavior change
**Timeline Impact:** None — fits within current Epic 6.5 sprint

### Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| Detection-layer filtering | Detection's job is "does a dislocation exist?" (market data question), not "should we act on it?" (risk question). Wrong responsibility layer. |
| Both layers (belt-and-suspenders) | Over-engineering for a paper-mode-only issue. Single guard at risk layer is sufficient and testable. |
| Modifying paper connectors to update order books | Would require paper connectors to maintain fake liquidity state — adds significant complexity and couples the fix to connector internals. |
| Applying guard to live mode too | In live mode, real fills naturally consume order book liquidity, so the problem is self-correcting. There could also be legitimate reasons to scale into the same pair across cycles in live. |

---

## Section 4: Detailed Change Proposals

### Change A: `ReservationRequest` interface

**File:** `pm-arbitrage-engine/src/common/types/risk.type.ts`

```
OLD:
export interface ReservationRequest {
  opportunityId: string;
  recommendedPositionSizeUsd: Decimal;
  pairId: string;
}

NEW:
export interface ReservationRequest {
  opportunityId: string;
  recommendedPositionSizeUsd: Decimal;
  pairId: string;
  isPaper: boolean;
}
```

**Rationale:** Explicit signal — the risk manager doesn't need to know about connector internals, it just gets told "this is a paper execution."

### Change B: `BudgetReservation` interface

**File:** `pm-arbitrage-engine/src/common/types/risk.type.ts`

```
OLD:
export interface BudgetReservation {
  reservationId: string;
  opportunityId: string;
  reservedPositionSlots: number;
  reservedCapitalUsd: Decimal;
  correlationExposure: Decimal;
  createdAt: Date;
}

NEW:
export interface BudgetReservation {
  reservationId: string;
  opportunityId: string;
  pairId: string;
  isPaper: boolean;
  reservedPositionSlots: number;
  reservedCapitalUsd: Decimal;
  correlationExposure: Decimal;
  createdAt: Date;
}
```

**Rationale:** Carries `pairId` and `isPaper` through the reservation lifecycle so `releaseReservation()` can clean up `paperActivePairIds` without needing the original request.

### Change C: `TradingEngineService.executeCycle()`

**File:** `pm-arbitrage-engine/src/core/trading-engine.service.ts` (~line 196)

```
OLD:
reservationRequest: {
  opportunityId: `${opportunity.dislocation.pairConfig.polymarketContractId}:${opportunity.dislocation.pairConfig.kalshiContractId}:${Date.now()}`,
  recommendedPositionSizeUsd: new FinancialDecimal(decision.maxPositionSizeUsd),
  pairId: matchId,
},

NEW:
reservationRequest: {
  opportunityId: `${opportunity.dislocation.pairConfig.polymarketContractId}:${opportunity.dislocation.pairConfig.kalshiContractId}:${Date.now()}`,
  recommendedPositionSizeUsd: new FinancialDecimal(decision.maxPositionSizeUsd),
  pairId: matchId,
  isPaper:
    this.kalshiConnector.getHealth().mode === 'paper' ||
    this.polymarketConnector.getHealth().mode === 'paper',
},
```

**Rationale:** If either connector is in paper mode, the execution involves simulated fills that won't update order books. Mixed mode (one live, one paper) still triggers the guard because the paper leg won't consume real liquidity.

### Change D: `RiskManagerService`

**File:** `pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts`

| Method | Change |
|--------|--------|
| **Class field** | Add `private paperActivePairIds = new Set<string>()` |
| **`reserveBudget()`** | After halt check: if `request.isPaper && this.paperActivePairIds.has(request.pairId)` → throw `RiskLimitError` with code `BUDGET_RESERVATION_FAILED`, message `"Budget reservation failed: paper position already open or reserved for pair ${request.pairId}"`, severity `warning` |
| **`reserveBudget()`** | After creating reservation object: copy `pairId` and `isPaper` from request onto reservation. If `request.isPaper` → `this.paperActivePairIds.add(request.pairId)` |
| **`releaseReservation()`** | Before deleting reservation: if `reservation.isPaper` → `this.paperActivePairIds.delete(reservation.pairId)` |
| **`closePosition()`** | Accept optional `pairId?: string` parameter. If provided → `this.paperActivePairIds.delete(pairId)` |
| **`loadState()` / startup** | Populate `paperActivePairIds` from open positions in DB where `is_paper = true` and status is not `CLOSED` |

**Key behavior summary:**

- **Paper mode:** Pair blocked from re-execution until position closes or reservation releases
- **Live mode:** Zero change — `isPaper` is `false`, the `paperActivePairIds` check is never triggered
- **Mixed mode:** Treated as paper (conservative — correct since paper leg won't update books)

### Files NOT Changed

- `IRiskManager` interface — `reserveBudget` takes `ReservationRequest`, adding a field is non-breaking
- Detection layer — stays purely about market data
- Execution service — passes `ReservationRequest` through unchanged
- Connectors — untouched
- Prisma schema — no migration needed (in-memory set, restored from existing DB fields on startup)

---

## Section 5: Implementation Handoff

### Change Scope: Minor

Direct implementation by development team. No backlog reorganization or architectural review needed.

### Handoff Plan

| Step | Owner | Action |
|------|-------|--------|
| 1 | Scrum Master | Create story file 6-5-5c or add acceptance criteria to 6-5-5 |
| 2 | Dev Agent | Implement via TDD workflow |
| 3 | Dev Agent | After fix verified, proceed to 6-5-5 (paper execution validation) |

### Success Criteria

1. In paper mode, executing an opportunity for pair X prevents re-execution of pair X until the position is closed or the reservation is released
2. In live mode, no behavioral change — duplicate pair executions remain allowed
3. On startup, `paperActivePairIds` is correctly restored from DB open positions with `is_paper = true`
4. All existing tests pass; new tests cover: paper dedup reject, paper dedup allow after close, paper dedup allow after release, live mode unaffected, startup restore, mixed mode treated as paper
5. `pnpm lint` and `pnpm test` pass
