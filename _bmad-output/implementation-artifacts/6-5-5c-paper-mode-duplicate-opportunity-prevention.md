# Story 6.5.5c: Paper Mode Duplicate Opportunity Prevention

Status: done

## Story

As an operator,
I want the risk management layer to prevent re-execution of the same contract pair in paper trading mode while a position is already open or reserved,
so that paper trading validation (Story 6-5-5) produces realistic trade counts and P&L instead of inflated results from the same opportunity firing every polling cycle.

## Background / Root Cause

In paper trading mode, simulated fills do NOT consume liquidity from the cached order books. A profitable dislocation detected in cycle N remains visible in cycle N+1, N+2, etc. because the order book never changes after a simulated fill. This causes the same opportunity to be re-detected, re-validated, and re-executed every polling cycle — producing inflated trade counts, distorted P&L, and unreliable validation metrics.

**Evidence from code analysis:**

- `TradingEngineService.executeCycle()` generates a unique `opportunityId` per cycle via `Date.now()` suffix — no natural deduplication key
- `RiskManagerService.reserveBudget()` validates: halt status, max open pairs, available capital — never checks whether a position/reservation already exists on the same pair
- Paper connectors intercept `submitOrder()` but do not modify in-memory order book state
- Result: identical dislocation → re-detected → re-approved → re-executed every cycle

**Why this doesn't happen in live mode:** Real fills naturally shift order book prices and eliminate the stale dislocation. The problem is self-correcting with real executions.

## Acceptance Criteria

1. **Given** the engine is running in paper mode (either or both platforms configured as paper)
   **When** an arbitrage opportunity is detected for pair X and a budget reservation or open position already exists for pair X
   **Then** `reserveBudget()` throws `RiskLimitError` with code `BUDGET_RESERVATION_FAILED` and message containing `"paper position already open or reserved for pair"`
   **And** the opportunity is logged as filtered (not silently dropped)

2. **Given** the engine is running in paper mode
   **When** a position for pair X is closed (via `closePosition()`)
   **Then** pair X is removed from the paper active set
   **And** subsequent opportunities for pair X can execute normally

3. **Given** the engine is running in paper mode
   **When** a reservation for pair X is released (execution failed, via `releaseReservation()`)
   **Then** pair X is removed from the paper active set
   **And** subsequent opportunities for pair X can reserve budget normally

4. **Given** the engine is running in live mode (`isPaper: false`)
   **When** multiple opportunities for the same pair X are detected across cycles
   **Then** no deduplication guard applies — all pass through `reserveBudget()` as before (zero behavioral change in live mode)

5. **Given** mixed mode (one platform paper, one live)
   **When** an opportunity is presented with `isPaper: true`
   **Then** the paper deduplication guard applies (conservative — the paper leg won't consume real order book liquidity)

6. **Given** the engine restarts while paper positions are open
   **When** `initializeStateFromDb()` runs during startup
   **Then** `paperActivePairIds` is populated from the database: all open positions where `is_paper = true` and status is NOT `CLOSED`
   **And** those pairs are blocked from re-execution until positions close

7. **Given** the `ReservationRequest` and `BudgetReservation` types need to carry paper mode context
   **When** the types are updated
   **Then** `ReservationRequest` gains `isPaper: boolean` (required field)
   **And** `BudgetReservation` gains `pairId: string` and `isPaper: boolean` (required fields)
   **And** all production callers compile without errors
   **And** test mocks/helpers that construct `ReservationRequest` or `BudgetReservation` are updated to include the new fields (see "Breaking Type Changes" note below)

8. **Given** all existing tests pass before the change
   **When** paper deduplication is implemented
   **Then** all existing 1,202+ passing tests continue to pass
   **And** new tests cover: paper dedup reject, paper dedup allow after close, paper dedup allow after release, live mode unaffected, startup restore, mixed mode treated as paper
   **And** `pnpm lint` reports zero errors

## Tasks / Subtasks

- [x] Task 1: Extend `ReservationRequest` and `BudgetReservation` types (AC: #7)
  - [x] 1.1 Add `isPaper: boolean` to `ReservationRequest` in `src/common/types/risk.type.ts`
  - [x] 1.2 Add `pairId: string` and `isPaper: boolean` to `BudgetReservation` in `src/common/types/risk.type.ts`
  - [x] 1.3 Verify all existing callers of `reserveBudget()` compile — the only caller constructing `ReservationRequest` is `TradingEngineService.executeCycle()` (must add `isPaper` field)

- [x] Task 2: Add `isPaper` to `TradingEngineService.executeCycle()` reservation request (AC: #5)
  - [x] 2.1 In `src/core/trading-engine.service.ts` (~line 196), add `isPaper` field to `reservationRequest`:
    ```typescript
    isPaper:
      this.kalshiConnector.getHealth().mode === 'paper' ||
      this.polymarketConnector.getHealth().mode === 'paper',
    ```
  - [x] 2.2 Write test: verify `isPaper` is `true` when either connector is in paper mode, `false` when both are live
  - [x] 2.3 Write test: verify `isPaper` is `true` in mixed mode (one paper, one live)

- [x] Task 3: Implement paper deduplication guard in `RiskManagerService` (AC: #1, #2, #3, #4, #6)
  - [x] 3.1 Add private field `private paperActivePairIds = new Set<string>()` to `RiskManagerService`
  - [x] 3.2 In `reserveBudget()`, after the halt check (first validation): if `request.isPaper && this.paperActivePairIds.has(request.pairId)` → emit a structured warning log (`this.logger.warn({ message: 'Paper mode duplicate opportunity blocked', module: 'risk-management', data: { pairId: request.pairId, opportunityId: request.opportunityId, reason: 'paper_position_already_active' } })`) then throw `RiskLimitError(RISK_ERROR_CODES.BUDGET_RESERVATION_FAILED, "Budget reservation failed: paper position already open or reserved for pair ${request.pairId}", 'warning', 'budget_reservation', 0, 0)`
  - [x] 3.3 In `reserveBudget()`, when creating the reservation object: copy `pairId` and `isPaper` from request onto the reservation. After storing in Map: if `request.isPaper` → `this.paperActivePairIds.add(request.pairId)`
  - [x] 3.4 In `releaseReservation()`, before deleting from Map: if `reservation.isPaper` → `this.paperActivePairIds.delete(reservation.pairId)`
  - [x] 3.5 In `closePosition()`, accept an optional `pairId?: string` parameter. If provided → `this.paperActivePairIds.delete(pairId)`. If `pairId` is NOT provided AND `this.paperActivePairIds.size > 0`, emit a defensive warning: `this.logger.warn({ message: 'closePosition called without pairId while paper pairs are tracked — potential Set leak if closing a paper position', module: 'risk-management', data: { trackedPairCount: this.paperActivePairIds.size } })`. **Important:** This is additive — the existing `closePosition(capitalReturned, pnlDelta)` signature gains a third optional parameter
  - [x] 3.6 In `initializeStateFromDb()`, after restoring `openPositionCount`/`totalCapitalDeployed`: query DB for open positions where `is_paper = true` and status NOT `CLOSED`, extract their `pairId` values, populate `this.paperActivePairIds`
  - [x] 3.7 Write tests (see Testing Requirements section below)

- [x] Task 4: Update `IRiskManager` interface and mocks (AC: #7)
  - [x] 4.1 Update `closePosition` signature in `IRiskManager` interface to accept optional `pairId?: string` third parameter: `closePosition(capitalReturned: unknown, pnlDelta: unknown, pairId?: string): Promise<void>`
  - [x] 4.2 Update `closePosition` mock in `src/test/mock-factories.ts` to accept 3 parameters (no behavior change needed — mock already accepts any args)
  - [x] 4.3 Verify all callers of `closePosition()` — identify where `pairId` should be passed (likely `ExitMonitorService` or `ExecutionQueueService` when closing positions)

- [x] Task 5: Pass `pairId` at all `closePosition()` call sites (AC: #2) — **CRITICAL: all 3 callers have `position.pairId` available**
  - [x] 5.1 `ExitMonitorService` (`src/modules/exit-management/exit-monitor.service.ts`, line 443): `position` is in scope → pass `position.pairId` as third arg
  - [x] 5.2 `SingleLegResolutionService` (`src/modules/execution/single-leg-resolution.service.ts`, line 394): `position` is in scope → pass `position.pairId` as third arg
  - [x] 5.3 `StartupReconciliationService` (`src/reconciliation/startup-reconciliation.service.ts`, line 494): `position` loaded at line 455 → pass `position.pairId` as third arg
  - [x] 5.4 Write test: verify `paperActivePairIds` is cleaned up when a position closes with a `pairId`

- [x] Task 6: Verify no regressions (AC: #8)
  - [x] 6.1 Run `pnpm test` — all existing 1,202+ passing tests still pass
  - [x] 6.2 Run `pnpm lint` — zero errors

## Dev Notes

### Architecture Compliance

- **Module boundaries:** All changes within `modules/risk-management/` (primary), `core/` (pass-through `isPaper` flag), and `common/types/` (type extensions). No forbidden imports introduced.
- **Interface changes:** `IRiskManager.closePosition()` gains optional third parameter — backward-compatible. `ReservationRequest` and `BudgetReservation` gain new required fields — production code has a single construction site for each, but test mocks need updating (see below).
- **Error handling:** Uses existing `RiskLimitError` with `BUDGET_RESERVATION_FAILED` code — no new error types needed.
- **Event system:** No new events. The `BUDGET_RESERVED`/`BUDGET_RELEASED` events are already emitted by `reserveBudget`/`releaseReservation`.
- **Financial math:** No monetary calculations affected. The dedup guard is a simple Set lookup, no Decimal math.
- **Database:** No schema changes. The `paperActivePairIds` Set is in-memory, populated on startup from existing `open_position` table fields (`is_paper`, `status`). Prisma schema confirmed: `OpenPosition` has `isPaper Boolean @default(false)` and `pairId String`.

### Breaking Type Changes (IMPORTANT)

Adding **required** fields to `ReservationRequest` (`isPaper: boolean`) and `BudgetReservation` (`pairId: string`, `isPaper: boolean`) is a compile-breaking change for any code constructing these types. Impact:

- **Production code:** Only `TradingEngineService.executeCycle()` constructs `ReservationRequest`, and only `RiskManagerService.reserveBudget()` constructs `BudgetReservation` — 2 sites total, both updated by this story.
- **Test code:** Any test mock or helper that constructs `ReservationRequest` or `BudgetReservation` inline will break at compile time. Key files to update:
  - `src/modules/risk-management/risk-manager.service.spec.ts` — `reserveBudget()` tests construct `ReservationRequest` directly
  - `src/modules/execution/execution-queue.service.spec.ts` — may construct `BudgetReservation` for mocking `reserveBudget` return values
  - `src/modules/execution/execution.service.spec.ts` — receives `BudgetReservation` as parameter to `execute()`
  - `src/core/trading-engine.service.spec.ts` — may construct `ReservationRequest`
  - `src/test/mock-factories.ts` — check if `makeReservation()` or similar helper exists

**Strategy:** Search for all `ReservationRequest` and `BudgetReservation` usages in test files and add `isPaper: false` (default for existing tests — live mode behavior unchanged) and `pairId: 'test-pair-id'` where needed. This is mechanical but must be thorough — a single missed site will fail compilation.

### File Structure — Exact Files to Modify

| File                                                       | Change                                                                                                                                                        |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/common/types/risk.type.ts`                            | Add `isPaper: boolean` to `ReservationRequest`; add `pairId: string` and `isPaper: boolean` to `BudgetReservation`                                            |
| `src/core/trading-engine.service.ts`                       | Add `isPaper` field to `reservationRequest` construction (~line 196)                                                                                          |
| `src/core/trading-engine.service.spec.ts`                  | Tests for `isPaper` flag construction                                                                                                                         |
| `src/modules/risk-management/risk-manager.service.ts`      | Add `paperActivePairIds` Set, dedup guard in `reserveBudget()`, cleanup in `releaseReservation()` and `closePosition()`, restore in `initializeStateFromDb()` |
| `src/modules/risk-management/risk-manager.service.spec.ts` | New tests for paper dedup: reject, allow after close, allow after release, live unaffected, startup restore, mixed mode                                       |
| `src/common/interfaces/risk-manager.interface.ts`          | Update `closePosition` signature with optional `pairId` param                                                                                                 |
| `src/test/mock-factories.ts`                               | Check if `makeReservation()` helper exists — add `isPaper`/`pairId` fields if so                                                                              |
| `src/modules/exit-management/exit-monitor.service.ts`      | Pass `position.pairId` as third arg to `closePosition()` (line 443)                                                                                           |
| `src/modules/execution/single-leg-resolution.service.ts`   | Pass `position.pairId` as third arg to `closePosition()` (line 394)                                                                                           |
| `src/reconciliation/startup-reconciliation.service.ts`     | Pass `position.pairId` as third arg to `closePosition()` (line 494)                                                                                           |

**Test files requiring `isPaper`/`pairId` additions to mock data:**

- `src/modules/risk-management/risk-manager.service.spec.ts`
- `src/modules/execution/execution-queue.service.spec.ts`
- `src/modules/execution/execution.service.spec.ts`
- `src/core/trading-engine.service.spec.ts`

**No new files.** No schema changes. No new dependencies. No migration needed.

### Key Design Decisions

1. **Guard lives in risk layer, NOT detection layer.** Detection's job is "does a dislocation exist?" (market data question). Risk's job is "should we act on it?" (execution gating). The dedup guard is a risk-layer concern.

2. **Paper-mode-only guard.** In live mode, real fills naturally consume liquidity. Additionally, there could be legitimate reasons to scale into the same pair across cycles in live mode. The guard only applies when `isPaper: true`.

3. **Mixed mode = paper.** If either connector is paper, the paper leg won't consume real liquidity. Conservative approach: treat mixed mode as paper.

4. **In-memory Set, restored from DB.** No new database columns or tables. The `paperActivePairIds` Set is populated on startup from existing `open_position` records where `is_paper = true` and status is active. Stale reservations are already cleared on startup by `clearStaleReservations()`, so only open positions need restoration.

5. **`closePosition` gains optional `pairId`.** This is the cleanest way to clean up the Set when a position closes. The parameter is optional for backward compatibility, but **all 3 production callers MUST pass `pairId`** — `ExitMonitorService` (line 443), `SingleLegResolutionService` (line 394), `StartupReconciliationService` (line 494). All have `position.pairId` in scope. If `pairId` is omitted when the Set is non-empty, a defensive warning log is emitted to catch future regressions — without `pairId`, a paper position's pair would remain in the Set indefinitely (until restart), permanently blocking that pair from paper re-execution.

### Current State of `reserveBudget()` Validations

Current validation order in `reserveBudget()`:

1. Halt check → throws if trading halted
2. Cap amount → `min(requested, maxPositionSizeUsd)`
3. Max open pairs → throws if `openPositionCount + reservedSlots >= maxOpenPairs`
4. Available capital → throws if insufficient bankroll

**New validation (insert after step 1):**

- Paper dedup check → throws if `request.isPaper && paperActivePairIds.has(request.pairId)`

### Current `ReservationRequest` and `BudgetReservation` Types

```typescript
// CURRENT
export interface ReservationRequest {
  opportunityId: string;
  recommendedPositionSizeUsd: Decimal;
  pairId: string;
}

export interface BudgetReservation {
  reservationId: string;
  opportunityId: string;
  reservedPositionSlots: number;
  reservedCapitalUsd: Decimal;
  correlationExposure: Decimal;
  createdAt: Date;
}
```

```typescript
// AFTER
export interface ReservationRequest {
  opportunityId: string;
  recommendedPositionSizeUsd: Decimal;
  pairId: string;
  isPaper: boolean;
}

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

### Current `closePosition()` Signature

```typescript
// CURRENT (risk-manager.service.ts)
async closePosition(capitalReturned: unknown, pnlDelta: unknown): Promise<void>

// AFTER
async closePosition(capitalReturned: unknown, pnlDelta: unknown, pairId?: string): Promise<void>
```

### How `isPaper` is Determined

`TradingEngineService.executeCycle()` already reads connector health modes at line 86-93:

```typescript
kalshiMode: this.kalshiConnector.getHealth().mode === 'paper' ? 'paper' : 'live',
polymarketMode: this.polymarketConnector.getHealth().mode === 'paper' ? 'paper' : 'live',
```

The `PlatformHealth.mode` field is `'paper' | 'live' | undefined` (optional, undefined = live by convention). For `isPaper`, check if either connector's mode is `'paper'`.

### Startup Restoration Logic

In `initializeStateFromDb()` (called by `onModuleInit()`), after existing state restoration, add:

```typescript
// Restore paper active pair IDs from open positions
// PositionStatus enum: OPEN | SINGLE_LEG_EXPOSED | EXIT_PARTIAL | CLOSED | RECONCILIATION_REQUIRED
const openPaperPositions = await this.prisma.openPosition.findMany({
  where: {
    isPaper: true,
    status: { not: 'CLOSED' }, // Prisma PositionStatus enum — string literal matches enum value
  },
  select: { pairId: true },
});

this.paperActivePairIds = new Set(openPaperPositions.map(p => p.pairId));

if (this.paperActivePairIds.size > 0) {
  this.logger.log({
    message: `Restored ${this.paperActivePairIds.size} paper active pair(s) from DB`,
    module: 'risk-management',
    data: { pairIds: [...this.paperActivePairIds] },
  });
}
```

**Note:** `clearStaleReservations()` already clears all in-memory reservations on startup. So the Set only needs open positions, not stale reservations.

**Startup crash-between-reserve-and-commit:** If the system crashes after `reserveBudget()` adds pairId to the Set but before `commitReservation()` persists a position, the reservation is lost on restart (stale reservations are cleared). The pair becomes available again. This is **correct behavior** — a failed/incomplete reservation should not permanently block a pair.

### Testing Requirements

New tests for `RiskManagerService`:

| Test                                              | Description                                                                                                                     |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Paper dedup: rejects duplicate pair               | `isPaper: true`, reserve pair X, second reserve for pair X throws `BUDGET_RESERVATION_FAILED`                                   |
| Paper dedup: allows after release                 | Reserve pair X, release reservation, second reserve for pair X succeeds                                                         |
| Paper dedup: allows after close                   | Reserve pair X, commit, close position with pairId, next reserve for pair X succeeds                                            |
| Paper dedup: live mode unaffected                 | `isPaper: false`, reserve pair X twice — both succeed (no dedup applied)                                                        |
| Paper dedup: mixed mode treated as paper          | `isPaper: true` (derived from mixed connectors), reserve pair X, second reserve for pair X throws                               |
| Paper dedup: different pairs allowed              | `isPaper: true`, reserve pair X, reserve pair Y succeeds (different pair)                                                       |
| Paper dedup: startup restore                      | Mock DB returns open paper positions for pairs X, Y → `reserveBudget` for X throws, for Z succeeds                              |
| Paper dedup: startup restore ignores closed       | Mock DB returns closed paper positions → `reserveBudget` for those pairs succeeds                                               |
| Paper dedup: closePosition without pairId warns   | Call `closePosition` without `pairId` while Set has entries → warning log emitted, Set entry NOT removed                        |
| Paper dedup: closePosition with pairId cleans Set | Call `closePosition` with `pairId` → Set entry removed, no warning                                                              |
| Paper dedup: logs when blocking                   | `isPaper: true`, reserve pair X, second reserve for pair X → warning log emitted with `pairId` and `opportunityId` before throw |

New tests for `TradingEngineService`:

| Test                       | Description                                                              |
| -------------------------- | ------------------------------------------------------------------------ |
| `isPaper` flag: both paper | Both connectors `mode: 'paper'` → `isPaper: true` in reservation request |
| `isPaper` flag: both live  | Both connectors `mode: 'live'` or `undefined` → `isPaper: false`         |
| `isPaper` flag: mixed mode | One paper, one live → `isPaper: true`                                    |

### Previous Story Intelligence (Story 6.5.5b)

- Story 6.5.5b added `adjustReservation()` to `IRiskManager` interface (CR fix H1) — the interface is now extended with this method. Any new interface changes must be additive.
- `reservations` Map keys are `reservationId` (UUID), not `pairId` — cannot use Map key for dedup. Separate Set is needed.
- `clearStaleReservations()` zeroes in-memory reservations on startup — Set doesn't need to track stale reservations, only open positions.
- Test count after 6.5.5b: 1,204 tests (some tests have since changed — current baseline: 1,202 passing, 2 known failures).
- `ExecutionResult.actualCapitalUsed` is the new optional field — unrelated to this story but shows pattern for optional type additions.

### Git Intelligence

Recent engine commits:

```
4a8edf3 feat: introduce depth-aware reservation adjustment
612d195 feat: update detection service to use best bid for sell leg
6ba25e1 feat: add dashboard module with WebSocket support
```

**Relevant to this story:**

- `4a8edf3`: Depth-aware sizing — `adjustReservation()` added to `IRiskManager` interface, `actualCapitalUsed` on `ExecutionResult`. Shows the pattern for non-breaking interface additions.
- `6ba25e1`: Dashboard module — no impact on risk management.

### Scope Guard

This story is strictly scoped to:

1. Prevent duplicate pair execution in paper mode via `paperActivePairIds` Set
2. Carry `isPaper` flag through `ReservationRequest` → `BudgetReservation`
3. Clean up Set on `releaseReservation()` and `closePosition()`
4. Restore Set from DB on startup

Do NOT:

- Modify detection layer (detection stays purely about market data)
- Add dedup guard for live mode
- Modify paper trading connectors (they remain unchanged)
- Add new database columns or tables (in-memory Set, restored from existing fields)
- Create new error types (use existing `RiskLimitError`)
- Add configuration for the dedup behavior (it's always on in paper mode — no toggle needed)

### Project Structure Notes

- All changes within `pm-arbitrage-engine/src/` — no root repo changes
- Files follow existing kebab-case naming convention
- Tests co-located with source (`.spec.ts` suffix)
- No new modules, no new files, no new dependencies

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-02-paper-dedup.md] — Sprint change proposal with full problem analysis and recommended approach
- [Source: pm-arbitrage-engine/src/common/types/risk.type.ts] — `ReservationRequest` and `BudgetReservation` types
- [Source: pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts, lines 673-760] — `reserveBudget()` current validations
- [Source: pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts, lines 806-840] — `releaseReservation()` cleanup
- [Source: pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts, lines 876-912] — `closePosition()` current implementation
- [Source: pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts, lines 152-254] — `initializeStateFromDb()` startup restoration
- [Source: pm-arbitrage-engine/src/core/trading-engine.service.ts, lines 192-203] — `reservationRequest` construction in `executeCycle()`
- [Source: pm-arbitrage-engine/src/common/interfaces/risk-manager.interface.ts] — `IRiskManager` interface
- [Source: _bmad-output/implementation-artifacts/6-5-5b-depth-aware-position-sizing.md] — Previous story (1,204 tests baseline, `adjustReservation` pattern)
- [Source: _bmad-output/implementation-artifacts/6-5-5-paper-execution-validation.md] — Blocked story that requires this fix

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None — clean implementation, no debugging required.

### Completion Notes List

- All 8 ACs verified and passing
- 15 new tests added (12 risk manager + 3 trading engine), total 1219 passing
- Zero lint errors
- All type changes are compile-safe — updated 7 test files with new required fields
- `openPosition.findMany` mock added to 3 test setups (risk-manager spec, financial-math property spec, e2e spec)
- No new files, no schema changes, no new dependencies

### Code Review Fixes Applied

- **[M1]** Fixed pre-existing logging bug in `reserveBudget()`: log was reporting `maxPositionSizeUsd` instead of actual `reservation.reservedCapitalUsd`
- **[M2]** Added integration test: startup restore → `reserveBudget` rejection for restored paper pairs (verifies AC#6 end-to-end)

### File List

**Production code modified:**

- `src/common/types/risk.type.ts` — `isPaper` on `ReservationRequest`, `pairId`+`isPaper` on `BudgetReservation`
- `src/common/interfaces/risk-manager.interface.ts` — `closePosition` optional `pairId` param
- `src/modules/risk-management/risk-manager.service.ts` — `paperActivePairIds` Set, dedup guard, cleanup, startup restore
- `src/core/trading-engine.service.ts` — `isPaper` flag on reservation request
- `src/modules/exit-management/exit-monitor.service.ts` — pass `position.pairId` to `closePosition`
- `src/modules/execution/single-leg-resolution.service.ts` — pass `position.pairId` to `closePosition`
- `src/reconciliation/startup-reconciliation.service.ts` — pass `position.pairId` to `closePosition`

**Test code modified:**

- `src/modules/risk-management/risk-manager.service.spec.ts` — 12 new paper dedup tests, `openPosition` mock, updated `mockPrisma` type
- `src/core/trading-engine.service.spec.ts` — 3 new `isPaper` flag tests
- `src/modules/execution/execution.service.spec.ts` — `pairId`+`isPaper` on `makeReservation`
- `src/modules/execution/execution-queue.service.spec.ts` — `pairId`+`isPaper` on mock reservations
- `src/common/utils/financial-math.property.spec.ts` — `isPaper` on request, `openPosition` mock
- `src/reconciliation/startup-reconciliation.service.spec.ts` — updated `closePosition` assertion with `pairId`
- `test/core-lifecycle.e2e-spec.ts` — `openPosition` mock in both Prisma mock instances
