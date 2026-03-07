# Sprint Change Proposal: Exit Path Depth Verification & Partial Fill Handling

**Date:** 2026-03-06
**Triggered by:** Code review — entry vs exit path comparison
**Scope classification:** Minor — direct implementation by dev team
**Target epic:** Epic 6.5 (Paper Trading Validation)
**Proposed story:** 6-5-5k

---

## Section 1: Issue Summary

### Problem Statement

The exit management module (`ExitMonitorService`) submits exit orders for the full entry position size without verifying order book depth. This creates four compounding gaps:

1. **No pre-exit depth check** — Entry path has `getAvailableDepth()` with size capping and minimum fill ratio enforcement. Exit path has nothing — goes straight to `submitOrder()` with the full `fillSize` from entry.
2. **Top-of-book-only close pricing** — `getClosePrice()` reads `bids[0].price` or `asks[0].price`. For large positions, the actual executable price (VWAP across levels) may be significantly worse.
3. **P&L calculated on entry sizes, not exit fill sizes** — When `submitOrder` returns `status: 'partial'`, P&L computation uses `kalshiFillSize`/`polymarketFillSize` (entry) instead of `primaryResult.filledQuantity`/`secondaryResult.filledQuantity` (exit). This corrupts `dailyPnl` and `totalCapitalDeployed` in `RiskState`.
4. **Premature CLOSED on partial fills** — Positions are marked `CLOSED` even when some contracts weren't exited. Unfilled contracts remain on the platform with zero tracking, accumulating invisible exposure.

### Discovery Context

Identified during code review comparing `ExecutionService.execute()` (robust depth-aware sizing, edge re-validation, cross-leg equalization) against `ExitMonitorService.executeExit()` (no depth checks, no partial fill awareness). The Kalshi connector can return `status: 'partial'` when `order.remaining_count > 0`, confirming this is a reachable production scenario.

### Evidence

- **Entry depth check:** `execution.service.ts:260-370` — `getAvailableDepth()`, `min(idealSize, depth)`, `minFillRatio` gate, edge re-validation after sizing
- **Exit no depth check:** `exit-monitor.service.ts:288-291` — Uses `kalshiOrder.fillSize` directly as order quantity
- **P&L uses wrong sizes:** `exit-monitor.service.ts:460-491` — Multiplies by entry `kalshiFillSize`/`polymarketFillSize`
- **Premature CLOSED:** `exit-monitor.service.ts:502` — `updateStatus(positionId, 'CLOSED')` regardless of partial fill
- **PRD mandate:** FR-EX-03 requires depth verification "before placing any order" — applies to exit orders but was only implemented for entry
- **Kalshi partial path:** `kalshi.connector.ts:309` — `status = order.remaining_count > 0 ? 'partial' : 'filled'`

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| Epic 6.5 (Paper Trading Validation) | Direct — add story | New story `6-5-5k` in the existing bug-fix series |
| Epic 7 (Dashboard) | None | Dashboard reads position data; no schema changes |
| Epic 10 (Model-Driven Exits) | Beneficial | VWAP infrastructure reusable for FR-EM-03 criterion #5 (liquidity deterioration) |
| Epics 8, 9, 11, 12 | None | Unaffected |

No new epics needed. No epic removal or resequencing required.

### Artifact Impact

| Artifact | Impact | Action |
|----------|--------|--------|
| PRD | None | FR-EX-03 already mandates this; fix restores compliance |
| Architecture doc | Minor update | Add depth verification note to exit-management hot path description |
| Epics doc | Minor update | Add story 6-5-5k to Epic 6.5 |
| Sprint status | Minor update | Add `6-5-5k` entry |
| UI/UX spec | None | Backend-only change |
| Schema/migrations | None | `EXIT_PARTIAL` already in `PositionStatus` enum |
| CI/CD | None | No pipeline changes |

### Technical Impact

- **Files modified:** `exit-monitor.service.ts`, `exit-monitor.service.spec.ts`, `architecture.md`
- **No new modules, no schema changes, no new dependencies**
- **Existing infrastructure reused:** `EXIT_PARTIAL` status, `SingleLegExposureEvent`, `retry-leg`/`close-leg` endpoints, `NormalizedOrderBook` type

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment

**Rationale:** All four gaps are isolated to a single service (`ExitMonitorService.executeExit()` and `getClosePrice()`). The entry path already has proven depth-checking infrastructure. The fix adapts existing patterns to the exit path with no cross-module rewiring.

- **Effort:** Low-Medium (1 story, single service + tests)
- **Risk:** Low — no schema changes, no new modules, no interface changes
- **Timeline impact:** None — slots into Epic 6.5's existing bug-fix series

### Alternatives Considered

| Option | Verdict | Reason |
|--------|---------|--------|
| Rollback | Not viable | No work to roll back; this is a missing safety guard |
| MVP scope reduction | Not viable | Not a scope question; it's a bug in existing functionality |

---

## Section 4: Detailed Change Proposals

### Proposal 1 (P0): Fix P&L Calculation — Use Exit Fill Sizes

**File:** `exit-monitor.service.ts` — `executeExit()` method

**Change:** Replace entry fill sizes (`kalshiFillSize`/`polymarketFillSize`) with exit fill sizes (`primaryResult.filledQuantity`/`secondaryResult.filledQuantity`) in:
- Per-leg P&L calculation (price delta multiplied by size)
- Exit fee calculation (fee rate applied to actual traded notional)
- Capital returned calculation (rename `totalEntryCapital` to `exitedEntryCapital`)

**Rationale:** Active state corruption. A partial fill (300 of 400 contracts) currently computes P&L as if all 400 exited, corrupting `dailyPnl` and `totalCapitalDeployed` in `RiskState`.

**Connector contract verified:** `OrderResult.filledQuantity` is always populated (typed as `number`, not optional). Kalshi sets it from `order.taker_fill_count`, Polymarket from `params.quantity` or polled `filledSize`, paper from `params.quantity`. No null/undefined risk.

### Proposal 2 (P0): Partial Fills Transition to EXIT_PARTIAL

**File:** `exit-monitor.service.ts` — `executeExit()` method

**Change:** After both legs return `'filled'` or `'partial'`, compare exit fill sizes against entry fill sizes:
- If both legs fully exited: existing CLOSED path (with corrected P&L from Proposal 1)
- If either leg partially filled: transition to `EXIT_PARTIAL`, log remainder details, emit `SingleLegExposureEvent` with operator action recommendations

**Design decisions:**
- No partial capital release — capital stays reserved until operator fully resolves (conservative: prevents risk budget drift while contracts remain live)
- No auto-retry of remainder — operator decides via existing `retry-leg`/`close-leg` endpoints
- No sub-position splitting — deferred; would require schema changes beyond this fix's scope

**Re-evaluation loop safety verified:** Exit monitor queries only `'OPEN'` positions (`findByStatusWithOrders('OPEN', isPaper)`). Positions in `EXIT_PARTIAL` are not picked up by the polling cycle — no double-exit risk.

### Proposal 3 (P1): Pre-Exit Depth Check with Graceful Deferral

**File:** `exit-monitor.service.ts` — `executeExit()` method + new `getAvailableExitDepth()` method

**Change:** Before submitting exit orders:
1. Fetch fresh order books for both legs (intentional second fetch — book may have changed since evaluation)
2. Calculate available depth at close price or better via new `getAvailableExitDepth()` method
3. If zero depth on either side: defer exit to next cycle (return without submitting)
4. Cap exit sizes to available depth
5. Equalize across legs: `exitSize = Decimal.min(primaryExitSize, secondaryExitSize)`
6. If `exitSize < entryFillSize`: partial exit flows into Proposal 2's EXIT_PARTIAL path

**Design decisions:**
- No minimum fill ratio for exits (unlike entry's 25%). At exit time, reducing any exposure is better than staying fully exposed.
- No edge re-validation. Exit decision already made by threshold evaluator; depth check is about execution feasibility.
- Cross-leg equalization prevents creating directional exposure from asymmetric partial fills.
- Double order book fetch is intentional freshness, not redundancy — must be commented in code.

### Proposal 4 (P1): VWAP-Aware Close Price for Threshold Evaluation

**File:** `exit-monitor.service.ts` — `getClosePrice()` method + `evaluatePosition()` caller

**Change:** Extend `getClosePrice()` with optional `positionSize` parameter:
- Without size: returns top-of-book price (backward compatible)
- With size: computes VWAP across enough levels to fill the position
- If book can't fill full position: VWAP of available depth (pessimistic signal)

`evaluatePosition()` passes each leg's fill size to `getClosePrice()`.

**Rationale:** Prevents the threshold evaluator from triggering exits based on misleadingly optimistic top-of-book prices. For a 400-contract position with thin depth, the VWAP reflects the true cost of exiting, making take-profit/stop-loss decisions more realistic.

**Epic 10 connection:** VWAP infrastructure directly reusable for FR-EM-03 criterion #5 (liquidity deterioration). Comparing `getClosePrice(connector, id, side)` vs `getClosePrice(connector, id, side, size)` yields a built-in spread metric.

### Proposal 5 (P2): Architecture Doc Update

**File:** `_bmad-output/planning-artifacts/architecture.md` — hot path diagram (line 627)

**Change:** Update exit-management description from:
```
modules/exit-management/ (monitor positions, evaluate thresholds, trigger exits)
```
To:
```
modules/exit-management/ (monitor positions, VWAP-aware threshold evaluation, depth-verified exit sizing)
    ↓                  ↑ exit orders depth-checked and capped to available liquidity (FR-EX-03)
    ↓                  ↑ partial fills transition to EXIT_PARTIAL for operator resolution
```

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

Direct implementation by the dev agent. No backlog reorganization or architectural replan needed.

### Story Definition

**Story ID:** 6-5-5k
**Title:** Exit Path Depth Verification & Partial Fill Handling
**Epic:** 6.5 (Paper Trading Validation)
**Sequencing:** After 6-5-5j (take-profit negative threshold fix), before 6-5-5 (paper execution validation)

### Implementation Order (within the story)

1. **Proposal 1** — Fix P&L to use exit fill sizes (P0, prerequisite for everything else)
2. **Proposal 2** — Partial fills transition to EXIT_PARTIAL (P0, depends on correct P&L)
3. **Proposal 3** — Pre-exit depth check + deferral (P1, builds on partial fill handling)
4. **Proposal 4** — VWAP-aware close pricing (P1, independent but logically follows)
5. **Proposal 5** — Architecture doc update (P2, last)

### DoD Gates

- All existing tests pass (`pnpm test`)
- `pnpm lint` reports zero errors
- New test cases cover: partial fill P&L calculation, EXIT_PARTIAL transition, depth deferral, VWAP calculation, cross-leg equalization
- No `decimal.js` violations introduced
- Architecture doc updated

### Success Criteria

- A partial fill on either exit leg transitions to `EXIT_PARTIAL` (not `CLOSED`)
- Realized P&L reflects actual exit quantities, not entry quantities
- Exit orders are depth-checked and capped before submission
- Zero-depth exits are deferred to next cycle
- Threshold evaluator uses position-size-aware VWAP, not top-of-book

---

**Approved by:** Pending
**Handoff to:** Dev agent (via create-story workflow)
