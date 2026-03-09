# Story 7.5.1: EXIT_PARTIAL Re-evaluation & Dual-Platform Close Endpoint

Status: done

## Story

As an operator,
I want partially exited positions to be automatically re-evaluated for exit by the exit monitor, and I want a new endpoint to manually close any open position across both platforms,
So that positions never stall permanently and I always have a manual override for the full position lifecycle.

## Acceptance Criteria

### EXIT_PARTIAL Re-evaluation

1. **Given** a position is in `EXIT_PARTIAL` status with unfilled remainder contracts
   **When** the exit monitor's polling cycle runs
   **Then** the position is included in the evaluation query alongside `OPEN` positions
   **And** the residual contract size is computed as `entryFillSize - alreadyExitedFillSize` per leg
   **And** `alreadyExitedFillSize` per leg is the sum of `order.fillSize` (Prisma Decimal field) across all exit orders for that leg's platform
   **And** a shared `getResidualSize(position, orders)` utility computes this, reusable by both the exit monitor and the close endpoint
   **And** all downstream logic (threshold evaluation, depth checks, VWAP close pricing, cross-leg equalization) operates on the residual sizes, not the original entry sizes
   [Source: epics.md#Story-7.5.1, sprint-change-proposal-2026-03-08.md#Section-4]

2. **Given** an EXIT_PARTIAL position's residual contracts meet an exit threshold (SL, TP, or time-based)
   **When** exit orders are submitted for the remainder
   **Then** exit sizes are `min(residualPrimaryDepth, residualSecondaryDepth, residualEntryFillSize)`
   **And** if both legs fill for the full remainder, the position transitions to `CLOSED` with aggregate P&L (sum of all partial exit P&Ls + remainder exit P&L)
   **And** if the remainder only partially fills again, the position stays `EXIT_PARTIAL` with an updated residual
   [Source: epics.md#Story-7.5.1]

3. **Given** an EXIT_PARTIAL position has zero depth on either side
   **When** the exit monitor evaluates it
   **Then** the exit is deferred to the next cycle (same pattern as OPEN positions with no depth)
   [Source: epics.md#Story-7.5.1]

### Dual-Platform Close Endpoint

4. **Given** a position is in `OPEN` or `EXIT_PARTIAL` status
   **When** the operator calls `POST /api/positions/:id/close` with optional `{ rationale: string }`
   **Then** the system fetches fresh order books for both platforms
   **And** submits opposing trades on both legs simultaneously using best available prices
   **And** for EXIT_PARTIAL positions, the close operates on the residual contract sizes (via `getResidualSize()`)
   **And** on success, the position transitions to `CLOSED` with realized P&L
   **And** risk budget is fully released via `IRiskManager.closePosition()`
   [Source: epics.md#Story-7.5.1]

5. **Given** one leg of the manual close fills but the other fails
   **When** a single-leg exposure occurs during manual close
   **Then** the position transitions to `SINGLE_LEG_EXPOSED` (not EXIT_PARTIAL)
   **And** a `SingleLegExposureEvent` is emitted with `origin: 'manual_close'` context
   **And** the operator can resolve via existing retry-leg/close-leg endpoints (Story 5.3)
   [Source: epics.md#Story-7.5.1]

6. **Given** the position is in any status other than `OPEN` or `EXIT_PARTIAL`
   **When** the operator calls `POST /api/positions/:id/close`
   **Then** the endpoint returns 422 with error "Position is not in a closeable state"
   [Source: epics.md#Story-7.5.1]

## Tasks / Subtasks

### Task 1: `getResidualSize` utility (AC: #1)

- [x] 1.1 Create `src/common/utils/residual-size.ts` with a pure function `getResidualSize(position, allPairOrders): { kalshi: Decimal, polymarket: Decimal }`
- [x] 1.2 Logic: filter `allPairOrders` to exclude entry orders (`position.kalshiOrderId`, `position.polymarketOrderId`), group remaining by platform, sum `fillSize` per platform, compute `entryFillSize - sumExitFillSize` per leg
- [x] 1.3 For OPEN positions (no exit orders), return entry fill sizes unchanged
- [x] 1.4 Unit tests in `src/common/utils/residual-size.spec.ts`

### Task 2: Exit monitor query broadening (AC: #1, #3)

- [x] 2.1 In `ExitMonitorService.evaluatePositions()`, change `findByStatusWithOrders('OPEN', isPaper)` to `findByStatusWithOrders({ in: ['OPEN', 'EXIT_PARTIAL'] }, isPaper)` — no signature change needed, Prisma type already supports this
- [x] 2.2 Update log message to reflect both statuses

### Task 3: Exit monitor residual integration (AC: #1, #2, #3)

- [x] 3.1 In `evaluatePosition()`: when `position.status === 'EXIT_PARTIAL'`, fetch all orders via `orderRepository.findByPairId(position.pairId)` and call `getResidualSize()` to get residual sizes per leg
- [x] 3.2 Pass residual sizes (instead of entry `fillSize`) to `getClosePrice()` for VWAP computation
- [x] 3.3 Pass residual sizes to threshold evaluator input (`kalshiSize`, `polymarketSize`)
- [x] 3.4 In `executeExit()`: when position is EXIT_PARTIAL, use residual sizes for `exitSize` cap calculation: `min(primaryDepth, secondaryDepth, residualPrimaryFillSize)` instead of `primaryEntryFillSize`
- [x] 3.5 In `executeExit()`: update the `isFullExit` check to compare exit fills against residual sizes (not entry sizes) for EXIT_PARTIAL positions
- [x] 3.6 For aggregate P&L on full exit of EXIT_PARTIAL: the `closePosition()` call handles only the REMAINING capital and this exit's P&L. Prior partial exits already called `releasePartialCapital()` which decremented `totalCapitalDeployed` and updated `dailyPnl` for those portions. The risk state implicitly tracks aggregate P&L across all exits — no manual aggregation needed. `closePosition()` also decrements `openPositionCount` and removes `pairId` from active tracking (which `releasePartialCapital` deliberately does not do)
- [x] 3.7 Update existing exit monitor tests for EXIT_PARTIAL scenarios

### Task 3.5b: Add `origin` field to `SingleLegExposureEvent` (AC: #5)

- [x] 3.5b.1 Add optional `origin?: string` parameter to `SingleLegExposureEvent` constructor (after `correlationId`, before `isPaper`) in `src/common/events/execution.events.ts`
- [x] 3.5b.2 Store as `public readonly origin?: string`
- [x] 3.5b.3 Update existing call sites to pass `undefined` for backward compatibility (exit monitor's `handlePartialExit` and `executeExit` partial paths)
- [x] 3.5b.4 Update event spec if it validates constructor parameters

### Task 4: `IPositionCloseService` interface (AC: #4, #5, #6)

- [x] 4.1 Create `src/common/interfaces/position-close-service.interface.ts` with `IPositionCloseService` interface and `POSITION_CLOSE_SERVICE_TOKEN` constant
- [x] 4.2 Interface method: `closePosition(positionId: string, rationale?: string): Promise<PositionCloseResult>`
- [x] 4.3 Define `PositionCloseResult` type: `{ success: boolean, realizedPnl?: string, error?: string }`
- [x] 4.4 Export from `src/common/interfaces/index.ts`

### Task 5: `PositionCloseService` implementation (AC: #4, #5, #6)

- [x] 5.1 Create `src/modules/execution/position-close.service.ts` implementing `IPositionCloseService`
- [x] 5.2 Inject: `PositionRepository`, `OrderRepository`, connectors (via tokens), `IRiskManager` (via `RISK_MANAGER_TOKEN`), `EventEmitter2`, `ExecutionLockService`
- [x] 5.3 Acquire `ExecutionLockService` before any DB reads or order submissions (release in `finally` block). After acquiring, re-read position from DB — if status has changed (e.g., exit monitor closed it while waiting for lock), return early with a "position already transitioning" result instead of throwing
- [x] 5.4 Validate position status is `OPEN` or `EXIT_PARTIAL` — throw `ExecutionError` (code 2005) otherwise
- [x] 5.5 For EXIT_PARTIAL: call `getResidualSize()` with orders from `orderRepository.findByPairId()`
- [x] 5.6 Fetch fresh order books, determine close sides, compute VWAP close prices on residual/entry sizes
- [x] 5.7 Submit primary leg → persist order → submit secondary leg → persist order
- [x] 5.8 On both success: `CLOSED` + `closePosition()` on risk manager + emit `ExitTriggeredEvent` with `exitType: 'manual'`
- [x] 5.9 On single-leg failure: `SINGLE_LEG_EXPOSED` + emit `SingleLegExposureEvent` with `origin: 'manual_close'` (using the new `origin` constructor parameter from Task 3.5b)
- [x] 5.10 Unit tests in `src/modules/execution/position-close.service.spec.ts`

### Task 6: `PositionManagementController` (AC: #4, #6)

- [x] 6.1 Create `src/dashboard/position-management.controller.ts` with `POST /api/positions/:id/close`
- [x] 6.2 Inject `IPositionCloseService` via `POSITION_CLOSE_SERVICE_TOKEN`
- [x] 6.3 DTO: `ClosePositionDto` with optional `rationale: string`
- [x] 6.4 Return standardized response: `{ data: PositionCloseResult, timestamp: string }` on success, `{ error: { code, message, severity }, timestamp: string }` on failure
- [x] 6.5 Guard with `AuthTokenGuard`
- [x] 6.6 Unit tests in `src/dashboard/position-management.controller.spec.ts`

### Task 7: Module wiring (AC: #4)

- [x] 7.1 In `ExecutionModule`: register `PositionCloseService` as provider with `{ provide: POSITION_CLOSE_SERVICE_TOKEN, useClass: PositionCloseService }`, add to exports
- [x] 7.2 In `DashboardModule`: import `ExecutionModule`, register `PositionManagementController`
- [x] 7.3 Verify DI resolution with integration test or manual check

### Task 8: Lint, test, verify (all ACs)

- [x] 8.1 `pnpm lint` — zero errors
- [x] 8.2 `pnpm test` — all existing + new tests pass
- [x] 8.3 Verify no `decimal.js` violations (no native JS arithmetic on monetary values)

## Dev Notes

### Critical: Exit Monitor is Hot Path

The exit monitor runs every 30s (`EXIT_POLL_INTERVAL_MS`) and evaluates all open positions. Changes here must be surgical:

- The `evaluatePositions` query change is a one-line edit — `{ in: ['OPEN', 'EXIT_PARTIAL'] }` instead of `'OPEN'` [Source: `exit-monitor.service.ts:72`]
- Residual size branching in `evaluatePosition` only activates for EXIT_PARTIAL positions — OPEN positions follow the unchanged code path
- The `orderRepository.findByPairId()` call adds one DB query per EXIT_PARTIAL position per cycle — acceptable since EXIT_PARTIAL positions are rare (typically 0-2 at a time based on production data)
[Source: sprint-change-proposal-2026-03-08.md#Section-2]

### `getResidualSize` Design

Pure function signature:
```typescript
function getResidualSize(
  position: { kalshiOrderId: string | null; polymarketOrderId: string | null; kalshiOrder: { fillSize: Prisma.Decimal | null } | null; polymarketOrder: { fillSize: Prisma.Decimal | null } | null },
  allPairOrders: Array<{ orderId: string; platform: string; fillSize: Prisma.Decimal | null }>,
): { kalshi: Decimal; polymarket: Decimal }
```

Logic:
1. Entry order IDs = `position.kalshiOrderId`, `position.polymarketOrderId`
2. Exit orders = `allPairOrders.filter(o => o.orderId !== kalshiEntryId && o.orderId !== polyEntryId)`
3. Per platform: `sumExitFillSize = exitOrders.filter(o => o.platform === platform).reduce(sum of fillSize)`
4. Residual = `new Decimal(entryOrder.fillSize.toString()).minus(sumExitFillSize)`
5. Floor at zero (defensive)

All math uses `decimal.js`. Convert Prisma Decimals via `.toString()`.
[Source: epics.md#Story-7.5.1, CLAUDE.md#Domain-Rules]

### `PositionCloseService` Pattern

Follow the exact pattern from `IPriceFeedService` / `PriceFeedService`:
- Interface + token in `src/common/interfaces/position-close-service.interface.ts` [Source: `price-feed-service.interface.ts`]
- Implementation in `src/modules/execution/position-close.service.ts` — co-located with execution logic since it coordinates dual-platform order submission [Source: epics.md#Story-7.5.1 Implementation Notes]
- Token-based injection in `DashboardModule` → `PositionManagementController` [Source: `dashboard.module.ts` imports `DataIngestionModule` for `PRICE_FEED_SERVICE_TOKEN`; similarly will import `ExecutionModule` for `POSITION_CLOSE_SERVICE_TOKEN`]

The close flow mirrors `executeExit()` in the exit monitor but is operator-initiated:
1. Validate status (OPEN or EXIT_PARTIAL)
2. Determine residual sizes (if EXIT_PARTIAL, call `getResidualSize`; if OPEN, use entry fill sizes)
3. Fetch order books, compute VWAP close prices on residual/entry sizes
4. Submit primary leg → persist → submit secondary → persist
5. Both succeed → CLOSED + `closePosition()` + `ExitTriggeredEvent`
6. One fails → SINGLE_LEG_EXPOSED + `SingleLegExposureEvent` with origin context
[Source: `exit-monitor.service.ts:270-708` for the pattern, epics.md#Story-7.5.1 for requirements]

### `PositionManagementController` Pattern

Follows existing dashboard controller conventions:
- Route prefix: `/api/positions` (shares prefix with `DashboardController` which has `GET /api/positions` — ensure no route collision by using `@Controller('api/positions')` with specific `@Post(':id/close')`)
- Guard: `AuthTokenGuard` (same as `RiskOverrideController`, `SingleLegResolutionController`)
- Response wrapper: `{ data: T, timestamp: string }` / `{ error: { code, message, severity }, timestamp: string }`
[Source: `dashboard.controller.ts`, `risk-override.controller.ts`, CLAUDE.md#API-Response-Format]

### Single-Leg Failure During Manual Close

When one leg fills and the other fails during a manual close:
- Transition to `SINGLE_LEG_EXPOSED` (NOT `EXIT_PARTIAL` — this is a fresh execution attempt with single-leg semantics, per epics.md explicit requirement)
- Emit `SingleLegExposureEvent` with `origin: 'manual_close'` via the new optional `origin` constructor parameter (Task 3.5b)
- Operator resolves via existing `POST /api/positions/:id/retry-leg` or `POST /api/positions/:id/close-leg` endpoints from Story 5.3
[Source: epics.md#Story-7.5.1, `single-leg-resolution.service.ts` for existing resolution flow]

### Race Condition: Exit Monitor vs Manual Close

`ExecutionLockService` is a global mutex (promise-based, 30s timeout) currently used only by `ExecutionQueueService` for the entry path. The exit monitor does NOT acquire it. This creates a race window where both the exit monitor and a manual close could operate on the same EXIT_PARTIAL position simultaneously, potentially double-submitting exit orders.

**Solution:** `PositionCloseService` must acquire `ExecutionLockService` before any DB reads or order submissions. After acquiring, it re-reads the position from DB — if the status has changed (exit monitor closed it while the manual close was waiting), it returns early with a graceful "position already transitioning" result. The lock is released in a `finally` block to prevent deadlocks.

The exit monitor itself does NOT need to acquire the lock — it runs on a 30s interval, processes positions sequentially, and the worst case is it reads a stale status for one cycle and skips the position next cycle when it sees CLOSED. The manual close path is the one that needs protection because it's operator-initiated and concurrent with the exit monitor's interval.

Test: verify that when `PositionCloseService` acquires the lock and the position status has changed to CLOSED during the wait, the service returns a non-error result without submitting any orders.
[Source: `execution-lock.service.ts:2-41`, `execution-queue.service.ts:18` for existing lock usage]

### Existing Code That Remains Untouched

- `POST /api/positions/:id/close-leg` (single-leg resolution for SINGLE_LEG_EXPOSED) — different purpose, different endpoint
- `SingleLegResolutionService.closeLeg()` / `retryLeg()` — continue to serve SINGLE_LEG_EXPOSED resolution
- `ThresholdEvaluatorService.evaluate()` — interface unchanged, just receives residual sizes in the input
- `IRiskManager` interface — `closePosition()` and `releasePartialCapital()` already exist
[Source: `single-leg-resolution.service.ts`, `threshold-evaluator.service.ts`, `risk-manager.interface.ts`]

### Error Codes

- Position not in closeable state: `EXECUTION_ERROR_CODES.INVALID_POSITION_STATE` (2005) [Source: `execution-error.ts:22`]
- Close leg failure: `EXECUTION_ERROR_CODES.CLOSE_FAILED` (2007) [Source: `execution-error.ts:23`]
- Partial exit failure: `EXECUTION_ERROR_CODES.PARTIAL_EXIT_FAILURE` (2008) [Source: `execution-error.ts:24`]

### Project Structure Notes

All new files follow existing conventions:
- `src/common/utils/residual-size.ts` + `.spec.ts` — co-located tests [Source: CLAUDE.md#Testing]
- `src/common/interfaces/position-close-service.interface.ts` — mirrors `price-feed-service.interface.ts` [Source: `common/interfaces/`]
- `src/modules/execution/position-close.service.ts` + `.spec.ts` — execution module [Source: `execution/` directory]
- `src/dashboard/position-management.controller.ts` + `.spec.ts` — dashboard module [Source: `dashboard/` directory]
- `src/dashboard/dto/close-position.dto.ts` — follows existing DTO pattern [Source: `dashboard/dto/`]

No conflicts with existing file paths. No naming convention violations.

### Testing Strategy

Framework: Vitest with `vi.fn()` mocks. Co-located spec files. Follow patterns from `exit-monitor.service.spec.ts`:
- Mock factories: `createMockPlatformConnector()`, `createMockRiskManager()` from `src/test/mock-factories.ts` [Source: `exit-monitor.service.spec.ts:20`]
- DI: `Test.createTestingModule()` with `{ provide: TOKEN, useValue: mock }` [Source: `exit-monitor.service.spec.ts`]
- `vi.mock('../../common/services/correlation-context', ...)` for correlation ID [Source: `exit-monitor.service.spec.ts:22-24`]

Required test cases per DoD:
1. EXIT_PARTIAL re-evaluation with residual sizes — verify VWAP and threshold use residual, not entry
2. Depth deferral on residual — zero depth defers EXIT_PARTIAL to next cycle
3. Aggregate P&L across multiple partial exits — full exit after prior partial correctly calls `closePosition()`
4. Dual-platform close for OPEN — happy path, both legs fill
5. Dual-platform close for EXIT_PARTIAL residual — uses `getResidualSize`
6. Single-leg failure during manual close — transitions to SINGLE_LEG_EXPOSED with origin context
7. Status guard — reject non-closeable statuses (CLOSED, SINGLE_LEG_EXPOSED, RECONCILIATION_REQUIRED) with 422
8. Zero residual edge case — `getResidualSize` returns zero when exit orders sum to entry size (defensive floor, log warning for potential data integrity issue)
9. `getResidualSize` for OPEN position with no exit orders — returns entry fill sizes unchanged
10. Concurrent exit monitor + manual close race condition — `PositionCloseService` acquires `ExecutionLockService` before operating; if another path (exit monitor or second manual close) finds the position already CLOSED or transitioning after lock acquisition, it exits gracefully without double-submitting orders
[Source: epics.md#Story-7.5.1 DoD Gates, execution-lock.service.ts]

### Dependencies

- `decimal.js` — already installed (used throughout codebase) [Source: `package.json`]
- `@nestjs/common`, `@nestjs/event-emitter`, `@nestjs/swagger` — already installed [Source: `package.json`]
- No new npm packages required
- No Prisma schema changes required (existing `Order` and `OpenPosition` models suffice)
- No new event classes required — `ExitTriggeredEvent` and `SingleLegExposureEvent` already exist. `SingleLegExposureEvent` gets an additive `origin?: string` parameter (Task 3.5b) [Source: `common/events/execution.events.ts:35-72`]

### References

- [Source: epics.md#Epic-7.5, Story-7.5.1] — Full acceptance criteria and implementation notes
- [Source: sprint-change-proposal-2026-03-08.md] — Discovery context, impact analysis, risk assessment
- [Source: exit-monitor.service.ts:50-129] — `evaluatePositions()` current implementation (query to change)
- [Source: exit-monitor.service.ts:131-268] — `evaluatePosition()` (residual integration points)
- [Source: exit-monitor.service.ts:270-708] — `executeExit()` (exit size cap + isFullExit check)
- [Source: exit-monitor.service.ts:740-837] — `handlePartialExit()` (existing EXIT_PARTIAL handler)
- [Source: exit-monitor.service.ts:839-870] — `getClosePrice()` (VWAP with size parameter)
- [Source: position.repository.ts:42-50] — `findByStatusWithOrders()` (Prisma type already supports `{ in: [...] }`)
- [Source: order.repository.ts:16-18] — `findByPairId()` (returns all orders for a pair)
- [Source: risk-manager.interface.ts:81-98] — `closePosition()`, `releasePartialCapital()` already exist
- [Source: price-feed-service.interface.ts] — Token injection pattern template
- [Source: dashboard.module.ts:12-28] — Module registration pattern
- [Source: execution.module.ts:20-49] — Execution module provider/export pattern
- [Source: execution-error.ts:15-28] — Error codes (2005, 2007, 2008)
- [Source: exit-monitor.service.spec.ts:1-80] — Test setup patterns, mock factories

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
N/A

### Completion Notes List

- **Baseline**: 80 test files, 1432 tests passing before implementation
- **Final**: 83 test files, 1473 tests passing (41 new tests added)
- **Lad MCP review (round 1)**: Applied fixes for 2 critical bugs found by reviewer:
  1. Secondary leg quantity now uses cross-leg equalized `exitSize = min(kalshiEffective, polymarketEffective)` instead of only primary effective size
  2. Added `isFullExit` check in `PositionCloseService` — partial fills transition to `EXIT_PARTIAL` with `releasePartialCapital()`, not unconditionally to `CLOSED`
  3. Lock release safety — tracks `lockAcquired` flag to avoid releasing lock that was never acquired
- **Lad MCP review (round 2 — story review)**: Addressed all 8 findings (4 critical, 4 moderate):
  1. **Data integrity alerting for negative residuals**: `getResidualSize()` now returns `floored: boolean` flag; callers (exit monitor + position close) log `DATA INTEGRITY` error when exit orders exceed entry fill size
  2. **Race condition: exit monitor write-after-read**: Added `findByIdWithOrders` status re-check at the top of `executeExit()` — skips exit if position status changed to non-closeable during evaluation (guards against concurrent manual close)
  3. **Primary leg failure clarity**: Added comment explaining why primary failure returns error without state transition (no exposure created — no orders were placed)
  4. **Zero residual EXIT_PARTIAL handling**: Both exit monitor and position close service detect zero residual on both legs → transition directly to `CLOSED` with `closePosition(0, 0, pairId)`, no orders submitted
  5. **VWAP staleness for secondary leg**: `PositionCloseService` re-fetches secondary order book after primary leg fills, recomputes VWAP; falls back to original price if re-fetch fails
  6-8. Paper mode, origin backward compat, error code mapping — confirmed correct, no changes needed
- **Added `ExitTriggeredEvent.exitType` union**: Added `'manual'` to the existing `'take_profit' | 'stop_loss' | 'time_based'` union type (backward compatible)
- **Added `PositionRepository.findByIdWithOrders()`**: New method including pair + both entry orders for the close service
- **Review items not addressed** (out of scope): DB transaction boundaries (existing pattern doesn't use them), `.toNumber()` precision (connector interface requires numbers), UUID validation (no existing controller uses `ParseUUIDPipe`), mixed mode detection for manual close events
- **Code review (Dev Agent — adversarial)**: Fixed 4 issues (1 HIGH, 3 MEDIUM):
  1. **(H) Exit monitor exit size cap missing secondary effective size**: `executeExit()` only included primary effective size in `min(primaryDepth, secondaryDepth, primaryEntryFillSize)`. For asymmetric EXIT_PARTIAL residuals (e.g., kalshi=70, poly=30), exit monitor could submit 70 contracts to secondary when only 30 remain. Fixed: renamed to `primaryEffectiveSize`/`secondaryEffectiveSize`, exit size now `min(primaryDepth, secondaryDepth, primaryEffective, secondaryEffective)`. Added test.
  2. **(M) ExitTriggeredEvent test stale**: Test "should accept all three exit types" only tested `['take_profit', 'stop_loss', 'time_based']` — updated to include `'manual'` and fixed description to "all four".
  3. **(M) Controller fragile string matching**: `PositionManagementController` used `result.error?.includes('not found')` for 404 routing — fragile if error messages change. Added `errorCode` field (`'NOT_FOUND' | 'NOT_CLOSEABLE' | 'EXECUTION_FAILED'`) to `PositionCloseResult`, set on all error returns, controller now uses `result.errorCode === 'NOT_FOUND'`.
  4. **(M) Single-zero residual edge case**: Neither exit monitor nor PositionCloseService handled EXIT_PARTIAL with one leg at zero residual (fully exited) and the other non-zero. Would attempt to submit zero-quantity orders. Added explicit check in both: exit monitor skips evaluation with DATA INTEGRITY error log; close service returns structured error suggesting close-leg endpoint. Added tests for both.
- All financial math uses `decimal.js` — verified no native JS operators on monetary values

### File List

**New files:**
- `src/common/utils/residual-size.ts` — Pure function computing residual contract sizes per leg (returns `floored` flag for data integrity alerting)
- `src/common/utils/residual-size.spec.ts` — 10 unit tests (added `floored` flag assertions)
- `src/common/interfaces/position-close-service.interface.ts` — IPositionCloseService + token + result type (with `errorCode` field)
- `src/modules/execution/position-close.service.ts` — Dual-platform manual close with lock, residual, P&L, secondary order book re-fetch, zero residual handling
- `src/modules/execution/position-close.service.spec.ts` — 14 unit tests (added zero residual + secondary re-fetch + single-zero residual tests)
- `src/dashboard/position-management.controller.ts` — POST /api/positions/:id/close
- `src/dashboard/position-management.controller.spec.ts` — 4 unit tests
- `src/dashboard/dto/close-position.dto.ts` — ClosePositionDto with optional rationale

**Modified files:**
- `src/common/utils/index.ts` — Export `getResidualSize`
- `src/common/interfaces/index.ts` — Export `IPositionCloseService`, `PositionCloseResult`, `POSITION_CLOSE_SERVICE_TOKEN`
- `src/common/events/execution.events.ts` — Added `origin?: string` to `SingleLegExposureEvent`, added `'manual'` to `ExitTriggeredEvent.exitType`
- `src/common/events/execution.events.spec.ts` — Updated call sites for `origin` parameter, added origin test
- `src/modules/exit-management/exit-monitor.service.ts` — Query broadening to include EXIT_PARTIAL, residual size integration, effective size passthrough to `executeExit()`, status re-check before order submission, zero residual → CLOSED handling, data integrity alerting for negative residuals, secondary effective size in exit cap, single-zero residual guard
- `src/modules/exit-management/exit-monitor.service.spec.ts` — Updated 3 existing assertions, added 12 EXIT_PARTIAL tests (including race condition guard, zero residual, single-zero residual, asymmetric residual cap)
- `src/modules/execution/execution.module.ts` — Register `PositionCloseService` + token, add to exports
- `src/modules/execution/execution.service.ts` — Updated `SingleLegExposureEvent` call site for `origin` parameter
- `src/modules/execution/exposure-alert-scheduler.service.ts` — Updated `SingleLegExposureEvent` call site for `origin` parameter
- `src/modules/execution/exposure-tracker.service.spec.ts` — Updated `SingleLegExposureEvent` call site for `origin` parameter
- `src/dashboard/dashboard.module.ts` — Import `ExecutionModule`, register `PositionManagementController`
- `src/dashboard/dashboard-event-mapper.service.spec.ts` — Updated `SingleLegExposureEvent` call site for `origin` parameter
- `src/persistence/repositories/position.repository.ts` — Added `findByIdWithOrders()` method
