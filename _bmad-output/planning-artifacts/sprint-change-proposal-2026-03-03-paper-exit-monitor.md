# Sprint Change Proposal — Paper Mode Exit Monitor Fix

**Date:** 2026-03-03
**Triggered by:** Operational testing during Epic 6.5 (Paper Trading Validation)
**Scope classification:** Minor — Direct implementation by dev team
**Status:** Approved

## Section 1: Issue Summary

### Problem Statement

Orders in paper mode are never being sold by the exit monitor, completely blocking the ability to test position lifecycle in paper trading mode.

**Root cause:** `ExitMonitorService.evaluatePositions()` calls `findByStatusWithOrders('OPEN')` which defaults `isPaper` to `false`. Paper positions (created with `isPaper: true`) are never queried, so they accumulate as perpetually open positions that never trigger exit thresholds.

**Secondary effect:** Because paper positions never close, the `paperActivePairIds` dedup cache in `RiskManagerService` is never cleared for those pairs, preventing re-execution of the same opportunity even if market conditions return. This cleanup is already handled by `closePosition()` — it just never gets called because the exit flow never runs for paper positions.

### Discovery Context

Observed during Epic 6.5 paper trading validation. The exit monitor was explicitly left as live-only with a TODO comment in Story 5.5.2. This fix is prerequisite for Story 6.5.5 (Paper Execution Validation) which requires observing complete position lifecycles.

### Evidence

- `exit-monitor.service.ts:62` — `findByStatusWithOrders('OPEN')` defaults `isPaper=false`
- `position.repository.ts:44` — `isPaper: boolean = false` default parameter
- Code comments: *"Exit monitor only processes live positions (isPaper=false filter from Story 5.5.2). Hardcoding false/false — update if paper position exit handling is added."*

### Cache Persistence (Non-Issue)

The `paperActivePairIds` Set is already restored from the database on startup via `loadPaperActivePairs()` (queries all non-CLOSED paper positions from Prisma). Persistence across restarts is already handled — the real issue is that positions never reach CLOSED status because the exit monitor doesn't evaluate them.

## Section 2: Impact Analysis

### Epic Impact

- **Epic 6.5 (Paper Trading Validation) — in-progress:** No new stories needed. This is a bug fix to existing exit-management module. Directly unblocks Story 6.5.5 (Paper Execution Validation, backlog).
- **All other epics:** No impact.

### Artifact Conflicts

- **PRD:** None — paper trading exit is within existing requirements.
- **Architecture:** None — all extension points already exist (repository `isPaper` parameter, event `isPaper`/`mixedMode` fields, connector health `mode`).
- **UI/UX:** None — dashboard already displays positions regardless of paper status.

### Technical Impact

- **Single file changed:** `src/modules/exit-management/exit-monitor.service.ts`
- **Four methods touched:** `evaluatePositions`, `evaluatePosition`, `executeExit`, `handlePartialExit`
- **Pattern:** Mirrors existing `ExecutionService` approach for determining `isPaper`/`mixedMode` from connector health
- **No schema changes, no new modules, no new dependencies**

## Section 3: Recommended Approach

**Selected path:** Direct Adjustment — bug fix in exit-management module

**Rationale:**
- Code was explicitly designed with this extension point in mind (TODO comments, parameters already exist)
- Single-file change with no ripple effects
- Mirrors the exact pattern already used in `ExecutionService` (lines 131-137)
- Low effort, low risk, directly unblocks paper trading validation gate

**Effort estimate:** Low
**Risk level:** Low
**Timeline impact:** None — unblocks rather than delays

## Section 4: Detailed Change Proposals

All changes in `pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts`:

### Change 1: `evaluatePositions()` — Mode-aware position query

Derive `isPaper` and `mixedMode` from connector health (same pattern as `ExecutionService`), pass `isPaper` to repository query:

```typescript
// OLD:
positions = await this.positionRepository.findByStatusWithOrders('OPEN');

// NEW:
const kalshiHealth = this.kalshiConnector.getHealth();
const polymarketHealth = this.polymarketConnector.getHealth();
const isPaper = kalshiHealth.mode === 'paper' || polymarketHealth.mode === 'paper';
const mixedMode = (kalshiHealth.mode === 'paper') !== (polymarketHealth.mode === 'paper');

positions = await this.positionRepository.findByStatusWithOrders('OPEN', isPaper);
```

Note: health check for disconnected connectors happens later per-position in `evaluatePosition()` — this early health read is only for mode detection.

### Change 2: `evaluatePosition()` — Thread isPaper/mixedMode

Add `isPaper: boolean, mixedMode: boolean` parameters. Forward to `executeExit()`.

### Change 3: `executeExit()` — Tag exit orders and events

- Add `isPaper: boolean, mixedMode: boolean` parameters
- Add `isPaper` to both exit order `create()` calls
- Replace hardcoded `false, false` in `ExitTriggeredEvent` with `isPaper, mixedMode`
- Forward `isPaper, mixedMode` to both `handlePartialExit()` call sites

### Change 4: `handlePartialExit()` — Tag partial exit events

- Add `isPaper: boolean, mixedMode: boolean` parameters
- Replace hardcoded `false, false` in `SingleLegExposureEvent` with `isPaper, mixedMode`

### No Change Needed: Cache cleanup

`RiskManagerService.closePosition()` already calls `this.paperActivePairIds.delete(pairId)` when `pairId` is provided. Once paper positions flow through the exit path, the dedup cache clears automatically, allowing re-execution of the same pair.

## Section 5: Implementation Handoff

### Scope Classification: Minor

Direct implementation by development team. No backlog reorganization needed.

### Deliverable

Bug fix to `exit-monitor.service.ts` — can be implemented as part of Story 6-5-5e or as a pre-requisite patch before Story 6-5-5 (Paper Execution Validation).

### Files to Modify

| File | Change |
|------|--------|
| `src/modules/exit-management/exit-monitor.service.ts` | Mode-aware position query, isPaper/mixedMode threading through evaluatePosition → executeExit → handlePartialExit, exit order isPaper tagging, event flag correction |
| `src/modules/exit-management/exit-monitor.service.spec.ts` | New tests: paper mode position query, isPaper on exit orders, isPaper/mixedMode on exit events, paper cache cleanup on successful exit |

### Success Criteria

1. Paper mode: open paper positions are evaluated for exit thresholds each cycle
2. Live mode: behavior unchanged — only live positions evaluated (zero behavioral change)
3. Exit orders created for paper positions carry `isPaper: true`
4. `ExitTriggeredEvent` and `SingleLegExposureEvent` emit correct `isPaper`/`mixedMode` flags
5. `paperActivePairIds` is cleared when a paper position exits successfully (enabling re-execution)
6. Complete position lifecycle observable in paper mode: open → monitor → exit → closed
7. All existing tests pass, new tests cover paper mode exit behavior
8. `pnpm lint` reports zero errors
