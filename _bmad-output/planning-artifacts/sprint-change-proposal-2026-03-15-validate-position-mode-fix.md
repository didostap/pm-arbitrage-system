# Sprint Change Proposal — 2026-03-15 — validatePosition Mode-Awareness Fix

## Section 1: Issue Summary

**Problem Statement:** `RiskManagerService.validatePosition()` always checks `this.liveState` regardless of trading mode. When the live mode risk state is halted (e.g., `reconciliation_discrepancy`), all new entries are blocked — including paper mode trades. This caused a 1770% APR / 31.79% net edge opportunity to be silently rejected, along with every other opportunity since March 14, 20:08 UTC.

**Discovery Context:** Operator noticed a high-APR contract match (UFC Fight Night: Sutherland vs. Pericic, match `85b96578`) was never traded despite being APPROVED with 100% confidence. Investigation traced the flow: detection identified the opportunity repeatedly (`detection.opportunity.identified` audit events), but zero execution events followed. The `validatePosition()` halt check returned `approved: false` before any downstream processing.

**Root Cause Chain:**
1. Story 9-16 (risk-state-paper-trade-reconciliation) introduced dual risk state rows (live/paper) and made `reserveBudget`, `commitReservation`, `closePosition` mode-aware
2. The code review flagged that `validatePosition`, `getCurrentExposure`, and `isTradingHalted` should also be mode-aware — this was **explicitly dismissed as "out of scope, these methods correctly operate on live state by design"**
3. On March 14, paper positions were reconciled against live platform APIs (pre-fix), triggering `order_not_found` discrepancies → `haltTrading('reconciliation_discrepancy')` set on live state
4. Story 9-16 fixed the reconciliation boundary (reverted to live-only) and manually fixed position statuses via SQL — but never cleared the stale halt reason from the live risk state
5. `isTradingHalted()` always returns `this.liveState.activeHaltReasons.size > 0` → returns `true`
6. `validatePosition()` calls `isTradingHalted()` as the FIRST check → rejects ALL opportunities for ALL modes

**Evidence:**
- DB: Live risk state `trading_halted: true`, `halt_reason: ["reconciliation_discrepancy"]`
- DB: Paper risk state `trading_halted: false` — correctly not halted
- DB: Zero new position entries after March 14, 20:08 UTC — only exits (which bypass `validatePosition`)
- DB: Multiple `detection.opportunity.identified` audit events for match `85b96578` with no corresponding execution events
- Code: `reserveBudget()` line 1215 already has `!request.isPaper && this.isTradingHalted()` — but `validatePosition()` line 493 does not
- Code: `onApplicationBootstrap()` calls `haltTrading('reconciliation_discrepancy')` but never calls `resumeTrading('reconciliation_discrepancy')` when reconciliation succeeds on subsequent restart

## Section 2: Impact Analysis

### Epic Impact
- **Epic 10** (in-progress): No structural impact. This is a targeted fix within existing risk-management module
- **No future epics affected**
- **No epic resequencing needed**

### Story Impact
- **Story 9-16 completion notes**: Must be updated to revise the "validatePosition live-only by design" statement (document the course correction, don't delete history)
- **New story required**: 10-0-2a (course correction, sequenced after 10-0-1)

### Artifact Conflicts
- **PRD**: No conflict — fix fulfills the paper/live isolation requirement
- **Architecture**: No conflict — uses existing `getState(isPaper)` pattern from Story 9-16
- **UI/UX**: No impact

### Technical Impact
- **Interface change**: `IRiskManager.validatePosition`, `isTradingHalted`, `getCurrentExposure` signatures gain `isPaper?: boolean`
- **Caller updates**: `TradingEngineService.executeCycle()` (1 production caller of `validatePosition`), `StressTestService.runSimulation()` (1 caller of `getCurrentExposure`), `processOverride()` (internal caller of `isTradingHalted`)
- **Test updates**: ~30 test cases reference `isTradingHalted()`, ~25 reference `validatePosition()`, ~12 reference `getCurrentExposure()` — all need optional `isPaper` parameter handling
- **Startup recovery**: `onApplicationBootstrap()` needs `resumeTrading('reconciliation_discrepancy')` after clean reconciliation

## Section 3: Recommended Approach

**Selected: Direct Adjustment** — one new course correction story in Epic 10

**Rationale:**
- The fix follows the **exact same `getState(isPaper)` pattern** already established in Story 9-16
- `reserveBudget()` already demonstrates the correct approach at line 1215: `!request.isPaper && this.isTradingHalted()`
- The trading engine already computes `isPaper` from connector health mode — no new data needed
- Effort: **Low** (5-6 method signatures, same refactoring pattern)
- Risk: **Low** (pattern proven, tests comprehensive)

**Why not a PRD/Architecture change:** The architecture already mandates paper/live isolation. The code just doesn't implement it fully at the `validatePosition` level.

## Section 4: Detailed Change Proposals

### Story 10-0-2a: validatePosition Mode-Awareness & Stale Halt Recovery

See full story spec in the implementation artifacts directory.

### Story 9-16 Completion Notes Update

```
OLD:
- `validatePosition` and `getCurrentExposure` remain live-only by design — mode
  separation occurs at `reserveBudget`/`commitReservation` level.

NEW:
- `validatePosition` and `getCurrentExposure` were initially left live-only (mode
  separation at `reserveBudget`/`commitReservation` level). This was revised in
  Story 10-0-2a (course correction 2026-03-15): `validatePosition` runs BEFORE
  `reserveBudget` and its halt check blocked all paper trades when live mode was
  halted. The code review had flagged this but it was dismissed as "by design".
  See sprint-change-proposal-2026-03-15-validate-position-mode-fix.md for full
  analysis.
```

## Section 5: Implementation Handoff

**Scope Classification: Minor** — direct implementation by development team

**Handoff:**
- Development agent implements Story 10-0-2a
- Story sequenced after 10-0-1 in Epic 10
- Sprint status updated: `10-0-2a-validate-position-mode-awareness: ready-for-dev`

**Success Criteria:**
1. Paper trades execute when live mode is halted
2. Live trades are still correctly blocked when live mode is halted
3. Stale `reconciliation_discrepancy` halt auto-clears on clean startup reconciliation
4. All existing tests pass + new mode-aware tests added
5. The 1770% APR opportunity (or similar) can be entered by the paper trading engine
