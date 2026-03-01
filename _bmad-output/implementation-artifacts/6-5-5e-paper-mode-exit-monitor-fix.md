# Story 6.5.5e: Paper Mode Exit Monitor Fix

Status: done

## Story

As an operator,
I want paper mode positions to flow through the complete position lifecycle including exit monitoring,
so that I can observe and validate position opening → monitoring → exit → close during paper trading validation.

## Background / Root Cause

**Critical blocker for Story 6.5.5 (Paper Execution Validation):**

Orders in paper mode are never exited by the exit monitor, completely blocking the ability to test position lifecycle in paper trading mode.

**Root cause:** `ExitMonitorService.evaluatePositions()` calls `findByStatusWithOrders('OPEN')` which defaults `isPaper` to `false`. Paper positions (created with `isPaper: true`) are never queried, so they accumulate as perpetually open positions that never trigger exit thresholds.

**Secondary effect:** Because paper positions never close, the `paperActivePairIds` dedup cache in `RiskManagerService` (from Story 6-5-5c) is never cleared for those pairs, preventing re-execution of the same opportunity even if market conditions return. This cleanup is already handled by `closePosition()` — it just never gets called because the exit flow never runs for paper positions.

**Discovery context:** Observed during Epic 6.5 paper trading validation. The exit monitor was explicitly left as live-only with a TODO comment in Story 5.5.2. Code comments confirm intent:

- `exit-monitor.service.ts:460` — `"Exit monitor only processes live positions (isPaper=false filter from Story 5.5.2). Hardcoding false/false — update if paper position exit handling is added."`
- `exit-monitor.service.ts:571` — Same comment on `handlePartialExit` event emission
- `position.repository.ts:44` — `isPaper: boolean = false` default parameter

## Acceptance Criteria

1. **Given** the engine is running in paper mode (either platform in paper mode)
   **When** `ExitMonitorService.evaluatePositions()` runs its polling cycle
   **Then** it derives `isPaper` and `mixedMode` from connector health
   **And** passes `isPaper` to `positionRepository.findByStatusWithOrders('OPEN', isPaper)`
   **And** paper positions are returned and evaluated for exit thresholds

2. **Given** the engine is running in live mode (both platforms live)
   **When** `evaluatePositions()` runs
   **Then** behavior is unchanged — only live positions evaluated (`isPaper=false`)
   **And** zero behavioral change in live mode

3. **Given** a paper position triggers an exit threshold
   **When** exit orders are created via `orderRepository.create()`
   **Then** both primary and secondary exit orders carry `isPaper: true`

4. **Given** a paper position exits successfully (both legs filled)
   **When** `ExitTriggeredEvent` is emitted
   **Then** the event carries correct `isPaper` and `mixedMode` flags (not hardcoded `false, false`)

5. **Given** a paper position exit has a partial failure (one leg fills, other fails)
   **When** `SingleLegExposureEvent` is emitted from `handlePartialExit()`
   **Then** the event carries correct `isPaper` and `mixedMode` flags (not hardcoded `false, false`)

6. **Given** a paper position exits successfully
   **When** `riskManager.closePosition()` is called with `position.pairId`
   **Then** `paperActivePairIds` is cleared for that pair (enabling re-execution of same pair — AC#2 from Story 6-5-5c)

7. **Given** all existing tests pass before the change (1,239 tests)
   **When** the changes are implemented
   **Then** all existing tests continue to pass
   **And** new tests cover: paper mode position query, `isPaper` on exit orders, `isPaper`/`mixedMode` on exit events, paper cache cleanup on successful exit, live mode unaffected
   **And** `pnpm lint` reports zero errors

## Tasks / Subtasks

- [x] Task 1: Mode-aware position query in `evaluatePositions()` (AC: #1, #2)
  - [x] 1.1 Read `kalshiConnector.getHealth()` and `polymarketConnector.getHealth()` at the start of `evaluatePositions()`
  - [x] 1.2 Derive `isPaper` and `mixedMode` using the established pattern: `isPaper = kalshiHealth.mode === 'paper' || polymarketHealth.mode === 'paper'`; `mixedMode = (kalshiHealth.mode === 'paper') !== (polymarketHealth.mode === 'paper')`
  - [x] 1.3 Pass `isPaper` to `this.positionRepository.findByStatusWithOrders('OPEN', isPaper)` — the repository method already accepts this parameter with a default of `false`
  - [x] 1.4 Thread `isPaper, mixedMode` to `this.evaluatePosition(position, isPaper, mixedMode)` call
  - [x] 1.5 Add `isPaper`/`mixedMode` to key log statements for operational debugging (e.g., the "Evaluating N positions" log and the "Position exited successfully" log in `executeExit`)
  - [x] 1.6 Write tests: paper mode passes `true` to repository, live mode passes `false`

- [x] Task 2: Thread `isPaper`/`mixedMode` through `evaluatePosition()` (AC: #1)
  - [x] 2.1 Add `isPaper: boolean, mixedMode: boolean` parameters to `evaluatePosition()` signature (after `position`)
  - [x] 2.2 Forward `isPaper, mixedMode` to `this.executeExit()` call (line ~220)

- [x] Task 3: Tag exit orders and events in `executeExit()` (AC: #3, #4)
  - [x] 3.1 Add `isPaper: boolean, mixedMode: boolean` parameters to `executeExit()` signature
  - [x] 3.2 Add `isPaper` to primary exit order `create()` call — `isPaper` field on `Prisma.OrderCreateInput` (schema already has `isPaper Boolean @default(false)` on `Order` model)
  - [x] 3.3 Add `isPaper` to secondary exit order `create()` call
  - [x] 3.4 Replace hardcoded `false, false` in `ExitTriggeredEvent` constructor (line ~460) with `isPaper, mixedMode`
  - [x] 3.5 Forward `isPaper, mixedMode` to both `handlePartialExit()` call sites
  - [x] 3.6 Remove the TODO comments about hardcoded `false/false`
  - [x] 3.7 Write tests: exit orders carry `isPaper: true` when paper mode, `ExitTriggeredEvent` emitted with correct flags

- [x] Task 4: Tag partial exit events in `handlePartialExit()` (AC: #5)
  - [x] 4.1 Add `isPaper: boolean, mixedMode: boolean` parameters to `handlePartialExit()` signature
  - [x] 4.2 Replace hardcoded `false, false` in `SingleLegExposureEvent` constructor (line ~571) with `isPaper, mixedMode`
  - [x] 4.3 Remove the TODO comment about hardcoded `false/false`
  - [x] 4.4 Write test: `SingleLegExposureEvent` emitted with correct `isPaper`/`mixedMode` in paper mode

- [x] Task 5: Verify cache cleanup works end-to-end (AC: #6)
  - [x] 5.1 Verify existing `closePosition()` call at line ~457 already passes `position.pairId` (confirmed from Story 6-5-5c)
  - [x] 5.2 Write integration-style test: paper position goes through exit → `closePosition` called with pairId → verify the flow

- [x] Task 6: Verify no regressions (AC: #7)
  - [x] 6.1 `pnpm test` — all 1,250 tests pass (1,239 original + 11 new)
  - [x] 6.2 `pnpm lint` — zero errors

## Dev Notes

### Architecture Compliance

- **Module boundaries:** All changes within `src/modules/exit-management/exit-monitor.service.ts` — no forbidden imports introduced.
- **Connectors untouched.** Detection untouched. Risk management untouched. Monitoring untouched.
- **No new modules, no new files, no schema changes, no new dependencies.**
- **No financial math affected** — the mode detection is a simple string comparison, no Decimal math.
- **Error hierarchy:** No new error types needed. Existing error handling in `evaluatePositions` and `executeExit` remains unchanged.
- **Event system:** No new events. Existing `ExitTriggeredEvent` and `SingleLegExposureEvent` already accept `isPaper`/`mixedMode` parameters — they were just hardcoded to `false`.

### Key Design Decisions

1. **Health read location: `evaluatePositions()`, NOT `evaluatePosition()`.** The mode is a system-level setting that doesn't change per-position within a cycle. Reading once at the top and threading down is cleaner and avoids redundant `getHealth()` calls per position. Note: `evaluatePosition()` already reads `getHealth()` for disconnection checks — the mode read here is purely for `isPaper`/`mixedMode` derivation, not duplicating the disconnection check.

2. **Pattern mirrors existing code.** The `isPaper`/`mixedMode` derivation pattern is identical to `SingleLegResolutionService` (lines 100-103), `ExposureAlertSchedulerService` (lines 133-136), and `ExecutionService`. This ensures consistency across the codebase.

3. **`isPaper` on exit orders via Prisma `OrderCreateInput`.** The `Order` model already has `isPaper Boolean @default(false)` (schema line 138). The `OrderRepository.create()` accepts `Prisma.OrderCreateInput` which includes optional `isPaper`. Adding `isPaper: true` to exit order creation is a one-field addition per `create()` call.

4. **Cache cleanup is already handled.** `RiskManagerService.closePosition()` already calls `this.paperActivePairIds.delete(pairId)` when `pairId` is provided (added in Story 6-5-5c). The `executeExit()` method already passes `position.pairId` to `closePosition()` (line ~457). Once paper positions flow through the exit path, the dedup cache clears automatically — no additional code needed.

5. **No `isPaper` on `submitOrder()` calls.** The connector already knows its own mode — the paper connector intercepts `submitOrder()` internally. Adding `isPaper` to the submit call is unnecessary.

### File Structure — Exact Files to Modify

| File | Change |
|------|--------|
| `src/modules/exit-management/exit-monitor.service.ts` | Mode-aware position query in `evaluatePositions()`, `isPaper`/`mixedMode` threading through `evaluatePosition` → `executeExit` → `handlePartialExit`, `isPaper` on exit order `create()` calls, event flag correction (replace hardcoded `false, false`), remove TODO comments |
| `src/modules/exit-management/exit-monitor.service.spec.ts` | New tests: paper mode position query, `isPaper` on exit orders, `isPaper`/`mixedMode` on exit events, partial exit events, live mode unaffected |

**No new files.** No schema changes. No new dependencies. No migration needed.

### Current Method Signatures (BEFORE)

```typescript
// evaluatePositions() — line 49
@Interval(EXIT_POLL_INTERVAL_MS)
async evaluatePositions(): Promise<void> {
  // ...
  positions = await this.positionRepository.findByStatusWithOrders('OPEN');
  // ...
  await this.evaluatePosition(position);
}

// evaluatePosition() — line 108
private async evaluatePosition(
    position: Awaited<ReturnType<PositionRepository['findByStatusWithOrders']>>[0],
): Promise<void> {
  // ...
  await this.executeExit(position, evalResult, kalshiClosePrice, polymarketClosePrice);
}

// executeExit() — line 225
private async executeExit(
    position: ...,
    evalResult: ThresholdEvalResult,
    kalshiClosePrice: Decimal,
    polymarketClosePrice: Decimal,
): Promise<void> {
  // Line ~340: primaryExitOrder = await this.orderRepository.create({ ... }); // NO isPaper
  // Line ~383: secondaryExitOrder = await this.orderRepository.create({ ... }); // NO isPaper
  // Line ~460: new ExitTriggeredEvent(..., false, false)  // HARDCODED
  // Line ~388-394: await this.handlePartialExit(...); // No isPaper/mixedMode
}

// handlePartialExit() — line 488
private async handlePartialExit(
    position: ...,
    filledExitOrderId: string,
    filledIsPrimaryKalshi: boolean,
    error: unknown,
    failedAttemptedPrice: Decimal,
    failedAttemptedSize: Decimal,
): Promise<void> {
  // Line ~571: new SingleLegExposureEvent(..., false, false)  // HARDCODED
}
```

### Target Method Signatures (AFTER)

```typescript
// evaluatePositions() — add mode derivation before query
@Interval(EXIT_POLL_INTERVAL_MS)
async evaluatePositions(): Promise<void> {
  // ...
  const kalshiHealth = this.kalshiConnector.getHealth();
  const polymarketHealth = this.polymarketConnector.getHealth();
  const isPaper = kalshiHealth.mode === 'paper' || polymarketHealth.mode === 'paper';
  const mixedMode = (kalshiHealth.mode === 'paper') !== (polymarketHealth.mode === 'paper');

  positions = await this.positionRepository.findByStatusWithOrders('OPEN', isPaper);
  // ...
  await this.evaluatePosition(position, isPaper, mixedMode);
}

// evaluatePosition() — add isPaper/mixedMode params, forward to executeExit
private async evaluatePosition(
    position: ...,
    isPaper: boolean,
    mixedMode: boolean,
): Promise<void> {
  // ...
  await this.executeExit(position, evalResult, kalshiClosePrice, polymarketClosePrice, isPaper, mixedMode);
}

// executeExit() — add isPaper/mixedMode, tag orders, fix events
private async executeExit(
    position: ...,
    evalResult: ThresholdEvalResult,
    kalshiClosePrice: Decimal,
    polymarketClosePrice: Decimal,
    isPaper: boolean,
    mixedMode: boolean,
): Promise<void> {
  // Add isPaper to both order.create() calls
  // Replace false, false → isPaper, mixedMode in ExitTriggeredEvent
  // Forward isPaper, mixedMode to handlePartialExit calls
}

// handlePartialExit() — add isPaper/mixedMode, fix event
private async handlePartialExit(
    position: ...,
    filledExitOrderId: string,
    filledIsPrimaryKalshi: boolean,
    error: unknown,
    failedAttemptedPrice: Decimal,
    failedAttemptedSize: Decimal,
    isPaper: boolean,
    mixedMode: boolean,
): Promise<void> {
  // Replace false, false → isPaper, mixedMode in SingleLegExposureEvent
}
```

### How `isPaper`/`mixedMode` Are Determined (Established Pattern)

From `SingleLegResolutionService` (lines 96-103) and `ExposureAlertSchedulerService` (lines 129-136):

```typescript
const kalshiHealth = this.kalshiConnector.getHealth();
const polymarketHealth = this.polymarketConnector.getHealth();
const isPaper = kalshiHealth.mode === 'paper' || polymarketHealth.mode === 'paper';
const mixedMode = (kalshiHealth.mode === 'paper') !== (polymarketHealth.mode === 'paper');
```

`PlatformHealth.mode` is `'paper' | 'live' | undefined` (undefined = live by convention).

### Existing Test Structure (`exit-monitor.service.spec.ts`)

Test file uses a `createMockPosition()` factory function. Existing `describe` blocks:

- `describe('evaluatePositions')` — mock `positionRepository.findByStatusWithOrders` return value
- `describe('happy path exit')` — full exit flow with both legs filled
- `describe('first leg failure')` — primary leg fails, position stays OPEN
- `describe('partial exit')` — secondary leg fails after primary fills
- `describe('circuit breaker')` — consecutive failure handling
- `describe('error isolation')` — per-position error isolation
- `describe('getClosePrice')` — close price from order book

**Existing connector health mocks** (from `beforeEach`):

```typescript
mockKalshiConnector = {
  getHealth: vi.fn().mockReturnValue({ status: 'connected', mode: 'live', ... }),
  submitOrder: vi.fn().mockResolvedValue({ status: 'filled', filledPrice: 0.55, filledQuantity: 100 }),
  getFeeSchedule: vi.fn().mockReturnValue({ takerFeePercent: 2, ... }),
  getOrderBook: vi.fn().mockResolvedValue({ ... }),
};
```

The `mode: 'live'` in existing mock health means existing tests already default to `isPaper = false`. New tests need `mode: 'paper'` override.

### Testing Requirements

**New tests for `ExitMonitorService`:**

| Test | Description |
|------|-------------|
| Paper mode: queries paper positions | Set connector `mode: 'paper'` → `findByStatusWithOrders` called with `('OPEN', true)` |
| Live mode: queries live positions | Both connectors `mode: 'live'` → `findByStatusWithOrders` called with `('OPEN', false)` (backward-compatible) |
| Paper mode: exit orders carry isPaper | Paper mode + full exit → both `orderRepository.create()` calls include `isPaper: true` |
| Paper mode: ExitTriggeredEvent has correct flags | Paper mode + full exit → event emitted with `isPaper: true, mixedMode: false` (or `true` if mixed) |
| Mixed mode: correct flags | One connector paper, one live → event emitted with `isPaper: true, mixedMode: true` |
| Paper mode: SingleLegExposureEvent has correct flags | Paper mode + partial exit → `SingleLegExposureEvent` emitted with `isPaper: true` |
| Paper mode: pairId passed to closePosition | Paper exit → `closePosition` called with 3 args including `position.pairId` (already tested, but verify flow) |
| Live mode: exit behavior unchanged | Live mode full exit → identical to existing happy path test (regression guard) |

### Previous Story Intelligence

**Story 6-5-5c (Paper Mode Duplicate Opportunity Prevention) — DONE:**
- Added `paperActivePairIds` Set in `RiskManagerService`
- `closePosition()` already accepts optional `pairId` and deletes from Set
- `ExitMonitorService.executeExit()` already passes `position.pairId` to `closePosition()` (line ~457)
- Test count after: 1,219 passing

**Story 6-5-5d (Telegram Batching & Paper Dedup) — DONE:**
- Paper notification dedup in `EventConsumerService`
- `notifiedOpportunityPairs` cleared on `EXIT_TRIGGERED` and `SINGLE_LEG_RESOLVED` events
- Event pair clearing uses `pairId` field from events — these events will now carry correct `isPaper`/`mixedMode`, which doesn't affect the clearing logic (it only reads `pairId`)
- Test count after: 1,239 passing

### Git Intelligence

Recent engine commits:

```
2f7ad96 Merge remote-tracking branch 'origin/main' into epic-7
c655939 refactor: update EventConsumerService and TelegramAlertService (Story 6-5-5d)
8d6a8de Merge remote-tracking branch 'origin/main' into epic-7
711fa31 feat: enhance risk management by adding isPaper flag (Story 6-5-5c)
4a8edf3 feat: introduce depth-aware reservation adjustment (Story 6-5-5b)
612d195 feat: update detection service to use best bid for sell leg (Story 6-5-5a)
```

### Scope Guard

This story is strictly scoped to:

1. Mode-aware position query in `evaluatePositions()` (pass `isPaper` to repository)
2. Threading `isPaper`/`mixedMode` through `evaluatePosition` → `executeExit` → `handlePartialExit`
3. Tagging exit orders with `isPaper: true` when in paper mode
4. Replacing hardcoded `false, false` with actual `isPaper, mixedMode` on event emissions

Do NOT:

- Modify detection layer
- Modify risk management (6-5-5c already handles cache cleanup)
- Modify monitoring layer (6-5-5d already handles notification dedup)
- Modify connectors
- Add database columns or tables
- Add new error types
- Create new events
- Add configuration flags (mode is derived from connector health at runtime)

### Project Structure Notes

- All changes within `pm-arbitrage-engine/src/modules/exit-management/` — no root repo changes
- Files follow existing kebab-case naming convention
- Tests co-located with source (`.spec.ts` suffix)
- No new modules, no new files, no new dependencies

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-03-paper-exit-monitor.md] — Approved sprint change proposal with full problem analysis
- [Source: _bmad-output/implementation-artifacts/6-5-5c-paper-mode-duplicate-opportunity-prevention.md] — Paper dedup at risk layer (cache cleanup via `closePosition`)
- [Source: _bmad-output/implementation-artifacts/6-5-5d-telegram-batching-paper-dedup.md] — Paper notification dedup (clears on EXIT_TRIGGERED events)
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts, lines 49-106] — `evaluatePositions()` current implementation
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts, lines 108-223] — `evaluatePosition()` with connector health check
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts, lines 225-486] — `executeExit()` with hardcoded `false, false` on ExitTriggeredEvent
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts, lines 488-582] — `handlePartialExit()` with hardcoded `false, false` on SingleLegExposureEvent
- [Source: pm-arbitrage-engine/src/persistence/repositories/position.repository.ts, lines 42-50] — `findByStatusWithOrders(status, isPaper = false)` already supports `isPaper` parameter
- [Source: pm-arbitrage-engine/src/common/events/execution.events.ts, lines 74-90] — `ExitTriggeredEvent` constructor with `isPaper`/`mixedMode` params
- [Source: pm-arbitrage-engine/src/common/events/execution.events.ts, lines 35-72] — `SingleLegExposureEvent` constructor with `isPaper`/`mixedMode` params
- [Source: pm-arbitrage-engine/src/modules/execution/single-leg-resolution.service.ts, lines 96-103] — Established `isPaper`/`mixedMode` derivation pattern
- [Source: pm-arbitrage-engine/prisma/schema.prisma, lines 138, 170] — `isPaper Boolean` on Order and OpenPosition models

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

N/A — no debug issues encountered.

### Completion Notes List

- All 4 methods updated: `evaluatePositions()`, `evaluatePosition()`, `executeExit()`, `handlePartialExit()`
- Mode derivation pattern matches `SingleLegResolutionService` and `ExposureAlertSchedulerService`
- Both TODO comments about hardcoded `false/false` removed
- `isPaper` added to both primary and secondary exit order `create()` calls
- `isPaper`/`mixedMode` added to log statements in `evaluatePositions()` and `executeExit()`
- 11 new tests: 3 query tests (paper/live/mixed), 2 order tests (paper/live), 3 ExitTriggeredEvent tests (paper/mixed/live), 2 SingleLegExposureEvent tests (paper/mixed), 1 cache cleanup test
- All 1,250 tests pass (1,239 original + 11 new), lint clean

### Code Review Fixes (AI)

- **M1:** Eliminated redundant `getHealth()` calls in `evaluatePosition()` — health objects now passed from `evaluatePositions()` via parameters instead of re-reading per position
- **M2:** Added test for secondary-leg-non-fill-status path (returns 'rejected') in paper mode — previously only the `submitOrder` rejection path was covered
- **M3:** Added `isPaper`/`mixedMode` to `handlePartialExit()` error log for operational debugging parity with success log
- **L1:** Extracted `setupOrderCreateMock()` helper to eliminate 5x duplicated orderCounter pattern in tests
- All 1,251 tests pass (1,250 + 1 new from M2), lint clean

### File List

| File | Change |
|------|--------|
| `pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts` | Mode-aware position query, `isPaper`/`mixedMode` threading through 4 methods, exit order tagging, event flag correction, TODO comment removal, log enrichment. Review fix: pass health objects to `evaluatePosition()` to avoid redundant `getHealth()` calls; add `isPaper`/`mixedMode` to `handlePartialExit` error log |
| `pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.spec.ts` | 12 tests in `paper mode support` describe block covering all ACs. Review fix: extracted `setupOrderCreateMock()` helper; added secondary-leg-non-fill-status test for paper mode |
