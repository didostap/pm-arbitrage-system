# Story 5.3: Single-Leg Resolution & Operator Actions

Status: done

## Story

As an operator,
I want to retry the failed leg at a worse price or close the filled leg to cut losses,
So that I can resolve single-leg exposure within acceptable loss parameters.

## Out of Scope

- **Automatic single-leg management** (auto-close/hedge) — FR-EX-07, Phase 1 (Epic 10, Story 10.3). This story is manual operator-initiated only.
- **Exit monitoring** — Story 5.4. This story does NOT monitor `OPEN` positions for exit thresholds.
- **Startup reconciliation** — Story 5.5. Pending orders from timeout scenarios are Story 5.5's domain.
- **Telegram alert integration** — Epic 6, Story 6.1. The recurring alert emits domain events; Telegram consumption is a future subscriber.
- **Dashboard UI** — Epic 7. Endpoints are REST API only; no frontend in this story.
- **cancelOrder() implementation** — Both connectors currently throw "not implemented" for `cancelOrder()`. This story does NOT implement `cancelOrder()`. Close-leg uses `submitOrder()` with an opposing trade, not cancellation.

## Acceptance Criteria

1. **Given** a position is in `SINGLE_LEG_EXPOSED` state
   **When** the operator sends `POST /api/positions/:id/retry-leg` with `{ price: number }` body
   **Then** the system identifies which leg failed (the one without an order FK on the position)
   **And** submits an order to the failed platform via `IPlatformConnector.submitOrder()` at the specified price
   **And** if the order returns `filled`, the position transitions to `OPEN` with the new order linked
   **And** if the order returns `partial`, the position still transitions to `OPEN` (a partial fill is real exposure on both platforms — consistent with Story 5.1 which treats `partial` the same as `filled`). The partially filled size is recorded in the order record (`fillSize` < `size`). The size mismatch between legs is a known trade-off accepted at MVP — full size reconciliation is deferred to Phase 1.
   **And** the retry is logged with original price, retry price, resulting edge, and a `SingleLegResolvedEvent` is emitted
   **And** risk budget reservation is preserved (capital was already committed on the partial fill)

2. **Given** a position is in `SINGLE_LEG_EXPOSED` state
   **When** the operator sends `POST /api/positions/:id/close-leg` with optional `{ rationale?: string }` body
   **Then** the filled leg is closed by submitting an opposing trade on the same platform (buy→sell, sell→buy) at current market price (best bid for sell, best ask for buy)
   **And** the position transitions to `CLOSED` with realized P&L calculated
   **And** the close is logged with loss amount and operator rationale
   **And** a `SingleLegResolvedEvent` is emitted with resolution type `closed`
   **And** `closePosition()` is called on `IRiskManager` to decrement position count, return capital to pool, and update daily P&L

3. **Given** no operator action is taken on a single-leg exposure
   **When** the position remains in `SINGLE_LEG_EXPOSED` state
   **Then** the system re-emits a `SingleLegExposureEvent` every 60 seconds with updated P&L scenarios (fresh order book prices)
   **And** re-emission continues until the position status changes away from `SINGLE_LEG_EXPOSED`

4. **Given** a retry-leg attempt fails (order rejected, pending, or depth insufficient)
   **When** the `submitOrder()` returns a non-fill status
   **Then** the position remains in `SINGLE_LEG_EXPOSED` state (no status change)
   **And** the failure is logged with reason code and the response includes the updated P&L scenarios
   **And** the operator can retry again with different parameters

5. **Given** a position is NOT in `SINGLE_LEG_EXPOSED` state
   **When** the operator sends retry-leg or close-leg
   **Then** the request is rejected with HTTP 409 Conflict and error message "Position is not in single-leg exposed state"

## Tasks / Subtasks

- [x] Task 1: Create `SingleLegResolvedEvent` class (AC: 1, 2)
  - [x] 1.1 Add `SingleLegResolvedEvent` to `common/events/execution.events.ts` extending `BaseEvent`
  - [x] 1.2 Payload: positionId, pairId, resolutionType (`retried` | `closed`), resolvedOrder (OrderResult), realizedPnl (Decimal string, for close only), retryPrice (for retry only), originalEdge, newEdge (for retry only)
  - [x] 1.3 Add `SINGLE_LEG_RESOLVED` to `EVENT_NAMES` in `event-catalog.ts` as `'execution.single_leg.resolved'`
  - [x] 1.4 Add `SINGLE_LEG_EXPOSURE_REMINDER` to `EVENT_NAMES` in `event-catalog.ts` as `'execution.single_leg.exposure_reminder'`

- [x] Task 2: Create `SingleLegResolutionService` (AC: 1, 2, 4, 5)
  - [x] 2.1 Create `single-leg-resolution.service.ts` in `src/modules/execution/`
  - [x] 2.2 Inject: `PositionRepository`, `OrderRepository`, `PrismaService` (for ContractMatch access via include), Kalshi and Polymarket connectors (via `KALSHI_CONNECTOR_TOKEN` / `POLYMARKET_CONNECTOR_TOKEN`), `EventEmitter2`, `IRiskManager` (via `RISK_MANAGER_TOKEN`)
  - [x] 2.3 Implement `retryLeg(positionId: string, retryPrice: number): Promise<RetryLegResult>`
    - Fetch position via `PositionRepository.findById()`
    - Validate status is `SINGLE_LEG_EXPOSED` — throw `ExecutionError(2005)` if not
    - Determine failed leg: the platform whose order FK is null (`kalshiOrderId` or `polymarketOrderId`)
    - Get failed leg's contract ID from `ContractMatch` (position's `pairId`)
    - Determine side from position's `kalshiSide` / `polymarketSide`
    - Determine size from position's `sizes` JSON
    - Call `connector.submitOrder({ contractId, side, quantity, price: retryPrice, type: 'limit' })`
    - On `filled`/`partial`: persist new order, link to position, update position status to `OPEN`, emit `SingleLegResolvedEvent`
    - On failure: return failure result with updated P&L scenarios (re-fetch books, re-calculate)
  - [x] 2.4 Implement `closeLeg(positionId: string, rationale?: string): Promise<CloseLegResult>`
    - Fetch position, validate `SINGLE_LEG_EXPOSED`
    - Determine filled leg: the platform whose order FK is NOT null
    - Get current order book on filled platform for the contract
    - Submit opposing trade: if original was `buy`, submit `sell` at best bid; if `sell`, submit `buy` at best ask
    - Calculate realized P&L using the **linked order record's `fillPrice`** (NOT `position.entryPrices` — those may be incomplete on single-leg positions since only one leg filled). Fetch the filled order via `position.kalshiOrderId` or `position.polymarketOrderId` → `OrderRepository.findById()` → use `order.fillPrice` as entry price. Formula: For buy→sell: P&L = (closePrice - entryFillPrice) × fillSize; For sell→buy: P&L = (entryFillPrice - closePrice) × fillSize. Subtract taker fee on the close trade.
    - Persist close order, update position status to `CLOSED`
    - Emit `SingleLegResolvedEvent` with `resolutionType: 'closed'` and `realizedPnl`
    - Call `riskManager.closePosition(capitalReturned, pnlDelta)` to return capital and update P&L
  - [x] 2.5 Helper: `getContractMatch(pairId)` — query ContractMatch for contract IDs

- [x] Task 3: Create `SingleLegResolutionController` (AC: 1, 2, 4, 5)
  - [x] 3.1 Create `single-leg-resolution.controller.ts` in `src/modules/execution/`
  - [x] 3.2 `@Controller('api/positions')` with `@UseGuards(AuthTokenGuard)`
  - [x] 3.3 `POST :id/retry-leg` — accepts `RetryLegDto { price: number }`, validated with `class-validator`
  - [x] 3.4 `POST :id/close-leg` — accepts `CloseLegDto { rationale?: string }`, validated with `class-validator`
  - [x] 3.5 Standardized response wrapper: `{ data: result, timestamp }` for success, `{ error: { code, message, severity }, timestamp }` for errors
  - [x] 3.6 HTTP status codes: 200 for success, 409 for wrong position state, 422 for empty order book / cannot determine close price (market condition, not platform failure), 502 for platform connector submission failure (API error / timeout)

- [x] Task 4: Create `ExposureAlertScheduler` — recurring 60-second re-emission (AC: 3)
  - [x] 4.1 Create `exposure-alert-scheduler.service.ts` in `src/modules/execution/`
  - [x] 4.2 Use `@nestjs/schedule`'s `@Interval(60000)` or `setInterval` to poll every 60 seconds
  - [x] 4.3 On each tick: query `PositionRepository.findByStatus('SINGLE_LEG_EXPOSED')` for all exposed positions
  - [x] 4.4 For each exposed position: fetch current order books from both connectors, re-calculate P&L scenarios, emit `SingleLegExposureEvent` via `EVENT_NAMES.SINGLE_LEG_EXPOSURE_REMINDER` (NOT `SINGLE_LEG_EXPOSURE`) — this prevents `ExposureTrackerService` from counting re-emissions as distinct incidents toward the monthly/weekly thresholds
  - [x] 4.5 Wrap each position's re-emission in try/catch — one failing position must not prevent others from being re-emitted
  - [x] 4.6 Log each re-emission at `debug` level (avoid log spam at higher levels)
  - [x] 4.7 Skip re-emission if connector health is `disconnected` — stale data is worse than no alert (the initial alert from Story 5.2 already fired)

- [x] Task 5: Add `closePosition()` to `IRiskManager` and `RiskManagerService` (AC: 2)
  - [x] 5.1 Add `closePosition(capitalReturned: Decimal, pnlDelta: Decimal): Promise<void>` to `IRiskManager` interface
  - [x] 5.2 Implement in `RiskManagerService`: decrement `openPositionCount`, subtract `capitalReturned` from `totalCapitalDeployed`, call `updateDailyPnl(pnlDelta)`, emit `BUDGET_RELEASED`, persist state
  - [x] 5.3 **CRITICAL:** Update ALL existing `IRiskManager` mocks across the codebase to include `closePosition`. Search for `RISK_MANAGER_TOKEN` in test files — at minimum `execution-queue.service.spec.ts` and `execution.service.spec.ts` mock `IRiskManager` and will fail TypeScript compilation if `closePosition` is missing. Add `closePosition: vi.fn().mockResolvedValue(undefined)` to each mock.
  - [x] 5.4 Unit tests: position count decrements, capital returns, P&L updated, event emitted

- [x] Task 6: Update Prisma and repositories (AC: 1, 2)
  - [x] 6.1 Add `PositionRepository.findByIdWithPair(positionId)` — uses Prisma `include: { pair: true }` to return position with its `ContractMatch` (kalshiContractId, polymarketContractId, primaryLeg). Add JSDoc: `/** Fetches position with its associated ContractMatch for contract ID resolution. */`
  - [x] 6.2 Add `PositionRepository.updateWithOrder(positionId, data)` — update status AND link new order FK in one transaction
  - [x] 6.3 No new migration needed — existing schema supports all fields (status transitions, nullable order FKs)

- [x] Task 7: Register providers in `ExecutionModule` (AC: all)
  - [x] 7.1 Add `SingleLegResolutionService`, `SingleLegResolutionController`, `ExposureAlertScheduler` to `ExecutionModule`
  - [x] 7.2 `ScheduleModule` from `@nestjs/schedule` is already installed (`^6.1.1`). Import `ScheduleModule.forRoot()` in `AppModule` if not already imported.
  - [x] 7.3 Ensure `PersistenceModule` is imported for repository access

- [x] Task 8: DTO validation classes (AC: 1, 2)
  - [x] 8.1 Create `retry-leg.dto.ts` with `price: number` (required, `@IsNumber()`, `@IsPositive()`, `@Max(1)` — internal prices are decimal probability 0.00–1.00; rejects operator typos like `65` instead of `0.65`)
  - [x] 8.2 Create `close-leg.dto.ts` with `rationale?: string` (optional, `@IsString()`, `@IsOptional()`, `@MaxLength(500)`)

- [x] Task 9: Tests (all ACs)
  - [x] 9.1 Unit tests for `SingleLegResolutionService.retryLeg()`: happy path (fills, position→OPEN), fill failure (status unchanged), wrong position state (409)
  - [x] 9.2 Unit tests for `SingleLegResolutionService.closeLeg()`: happy path (close, position→CLOSED, P&L calculated), platform failure, wrong state
  - [x] 9.3 Unit tests for `SingleLegResolutionController`: request validation, response format, error mapping
  - [x] 9.4 Unit tests for `ExposureAlertScheduler`: re-emission with fresh P&L, skip on disconnected connector, error isolation between positions
  - [x] 9.5 Unit tests for `SingleLegResolvedEvent` construction
  - [x] 9.6 Unit tests for `closePosition()` on `RiskManagerService`
  - [x] 9.7 All existing tests continue to pass (612 total, up from 572+ baseline in Story 5.2)

## Dev Notes

### Architecture Constraints

- **This story introduces REST endpoints in the execution module.** Follow the pattern established by `RiskOverrideController` in `risk-management/`: `@Controller('api/...')` + `@UseGuards(AuthTokenGuard)` + `ValidationPipe` + standardized response wrapper.
- **Module dependency rules:**
  - `modules/execution/` → `connectors/` (submit retry/close orders) + `modules/risk-management/` (release reservation on close) — ALLOWED
  - `connectors/` NEVER imports from `modules/` — FORBIDDEN
  - Cross-module access through interfaces in `common/interfaces/`
- **Fan-out is async:** `SingleLegResolvedEvent` emission is on the EventEmitter2 async path. Future consumers (Telegram, dashboard) subscribe. Event emission must NEVER delay the HTTP response.
- **Do NOT create `leg-manager.service.ts` yet.** Story 5.2 explicitly noted this was deferred. The resolution logic lives in `SingleLegResolutionService` — a focused service for the two operator actions. `leg-manager.service.ts` may be introduced in Epic 10 when automatic management is added.

### Retry-Leg Flow

```
Operator → POST /api/positions/:id/retry-leg { price: 0.65 }
    ↓
Controller validates DTO, calls SingleLegResolutionService.retryLeg()
    ↓
Service fetches position (PositionRepository.findByIdWithPair())
    ↓
Validate: position.status === 'SINGLE_LEG_EXPOSED'
    ↓
Determine failed leg:
  - If kalshiOrderId is null → failed leg is Kalshi
  - If polymarketOrderId is null → failed leg is Polymarket
    ↓
Get contractId from ContractMatch (via pair relation):
  - Kalshi: pair.kalshiContractId
  - Polymarket: pair.polymarketContractId
    ↓
Get side and size from position:
  - Side: position.kalshiSide or position.polymarketSide
  - Size: JSON.parse(position.sizes).kalshi or .polymarket
    ↓
connector.submitOrder({ contractId, side, quantity: size, price: retryPrice, type: 'limit' })
    ↓
If filled/partial:
  1. Persist order to `orders` table
  2. Update position: status → OPEN, link new order FK
  3. Emit SingleLegResolvedEvent + OrderFilledEvent
  4. Return { success: true, newEdge, orderId }
    ↓
If rejected/pending:
  1. Fetch current books, recalculate P&L scenarios
  2. Return { success: false, reason, pnlScenarios }
```

### Close-Leg Flow

```
Operator → POST /api/positions/:id/close-leg { rationale: "Cut losses" }
    ↓
Controller validates DTO, calls SingleLegResolutionService.closeLeg()
    ↓
Service fetches position (findByIdWithPair())
    ↓
Validate: position.status === 'SINGLE_LEG_EXPOSED'
    ↓
Determine filled leg:
  - If kalshiOrderId is NOT null → filled leg is Kalshi
  - If polymarketOrderId is NOT null → filled leg is Polymarket
    ↓
Get current order book on the filled platform
    ↓
Submit opposing trade:
  - Original was buy → submit sell at bestBid (taking liquidity)
  - Original was sell → submit buy at bestAsk (taking liquidity)
  - Use fillSize as quantity (unwind entire position)
    ↓
Fetch filled order record via position's non-null order FK
    ↓
Calculate realized P&L:
  - closePrice = closeOrder.filledPrice
  - entryFillPrice = Decimal(filledOrderRecord.fillPrice)  // from the ORDER record, NOT position.entryPrices
  - For buy→sell: P&L = (closePrice - entryFillPrice) × fillSize
  - For sell→buy: P&L = (entryFillPrice - closePrice) × fillSize
  - Subtract taker fee on close trade
    ↓
Persist close order, update position status → CLOSED
    ↓
Release budget via riskManager.closePosition(capitalReturned, pnlDelta)
    ↓
Emit SingleLegResolvedEvent with realizedPnl
    ↓
Return { success: true, realizedPnl, closeOrderId }
```

### Budget Accounting on Close — CRITICAL

**IMPORTANT:** `releaseReservation()` on `IRiskManager` CANNOT be used for close-leg. Here's why:

When a single-leg position is created, `commitReservation()` is called by `ExecutionQueueService` (Story 5.1: `partialFill: true` triggers commit, not release). `commitReservation()` **deletes** the reservation from the in-memory `reservations` Map and permanently increments `openPositionCount` + `totalCapitalDeployed`. The reservation ID no longer exists.

**Therefore, this story MUST add a new method** to `IRiskManager` and `RiskManagerService`:

```typescript
// Add to IRiskManager interface:
/**
 * Close a committed position — return capital to pool, decrement position count.
 * Called when a position transitions to CLOSED.
 * @param capitalReturned - Decimal amount of capital being returned to the pool
 * @param pnlDelta - Realized P&L (positive = profit, negative = loss)
 */
closePosition(capitalReturned: Decimal, pnlDelta: Decimal): Promise<void>;
```

**Implementation in `RiskManagerService`:**
- Decrement `openPositionCount` by 1
- Subtract `capitalReturned` from `totalCapitalDeployed` (capital returns to available pool)
- Call `updateDailyPnl(pnlDelta)` to track the realized loss/gain
- Emit `BUDGET_RELEASED` event with close context
- Call `persistState()`

**For retry-leg (position→OPEN):** No budget change needed. The capital was already committed. The position just transitions from single-leg to fully hedged.

**No `contract-match.repository.ts` exists.** Access `ContractMatch` data through Prisma's `include: { pair: true }` on position queries — use `PositionRepository.findByIdWithPair()`.

### Recurring Alert Design

The `ExposureAlertScheduler` is a **separate service** from `ExposureTrackerService` (Story 5.2). They have different responsibilities:

- **ExposureTrackerService** (Story 5.2): Counts **distinct** exposure incidents monthly/weekly for threshold warnings. Subscribes to `SINGLE_LEG_EXPOSURE` event only.
- **ExposureAlertScheduler** (this story): Re-emits alerts every 60 seconds for unresolved positions. Polls DB for `SINGLE_LEG_EXPOSED` positions.

**CRITICAL — Use a separate event name for re-emissions:** The scheduler MUST emit via `EVENT_NAMES.SINGLE_LEG_EXPOSURE_REMINDER` (NOT `SINGLE_LEG_EXPOSURE`). The Story 5.2 thresholds (>5/month, >1/week for 3 weeks) were designed to count distinct incidents. A single unresolved exposure left for 5 minutes would generate 5 re-emissions — counting those toward the monthly threshold of 5 would trigger a false warning from what is essentially one incident. The `ExposureTrackerService` subscribes only to `SINGLE_LEG_EXPOSURE`, so it naturally ignores reminders. Future consumers (Telegram alerts in Epic 6) will subscribe to BOTH event names.

**The `SingleLegExposureEvent` class is reused** for both event names — the payload is identical. Only the event name differs.

**Debounce via in-memory map:** Maintain a `Map<string, number>` of `positionId → lastEmittedAtMs` within the scheduler. Skip re-emission if `Date.now() - lastEmittedAt < 55000` (slightly under 60s to account for interval drift). This prevents double-emission at position creation. Do NOT rely on `position.createdAt` or `updatedAt` — those don't represent emission times.

### Error Codes

Add new execution error codes for resolution actions:

```typescript
// In execution-error.ts or a constants file
EXECUTION_ERROR_CODES = {
  ...existing,
  INVALID_POSITION_STATE: 2005,   // Position not in expected state for operation
  RETRY_FAILED: 2006,             // Retry leg submission failed
  CLOSE_FAILED: 2007,             // Close leg submission failed
}
```

### Existing Code to Build On

**ExecutionService (execution.service.ts):**
- `handleSingleLeg()` — creates position with `SINGLE_LEG_EXPOSED`, emits initial `SingleLegExposureEvent`. Resolution service reads positions created by this method.
- `resolveConnectors(primaryLeg)` — returns primary/secondary connectors. Resolution service needs similar connector resolution based on platform.

**PositionRepository (position.repository.ts):**
- `findById(positionId)` — basic find, returns OpenPosition
- `findByStatus(status)` — used by ExposureTrackerService for rebuild, also needed by scheduler
- `updateStatus(positionId, status)` — simple status update, but retry-leg also needs to set the order FK

**OrderRepository (order.repository.ts):**
- `create(data)` — persist new orders (retry and close orders)

**Connectors:**
- `submitOrder()` — fully implemented on both Kalshi and Polymarket (Story 5.1)
- `cancelOrder()` — NOT implemented (throws). Not needed for this story.
- `getOrderBook()` — fully implemented, returns `NormalizedOrderBook`
- `getFeeSchedule()` — returns `FeeSchedule` with `takerFeePercent` (0-100 scale)

**P&L Calculator (single-leg-pnl.util.ts):**
- `calculateSingleLegPnlScenarios()` — reuse for updated P&L in retry failure responses and recurring alerts
- `buildRecommendedActions()` — reuse for recommended actions in recurring alerts

**RiskOverrideController (risk-override.controller.ts):**
- Pattern to follow for controller structure: `@Controller`, `@UseGuards(AuthTokenGuard)`, `@Body(new ValidationPipe({ whitelist: true }))`, standardized error response format

### ContractMatch Access

The resolution service needs contract IDs (kalshiContractId, polymarketContractId) from the `ContractMatch` table. The position has `pairId` which references `ContractMatch.matchId`. Options:

Use `PositionRepository.findByIdWithPair()` which includes the `pair` relation via Prisma's `include: { pair: true }`. This returns the position with its associated `ContractMatch` in one query. **Note:** There is NO `ContractMatchRepository` — do not create one. Access ContractMatch exclusively through the position's relation.

### Price for Close-Leg

When closing the filled leg, the price should be the **current best available price** on that platform:
- If the filled side was `buy`: close by selling → use `bestBid` from current order book
- If the filled side was `sell`: close by buying → use `bestAsk` from current order book

If the order book is empty or the connector is disconnected, return HTTP 422 with error code 2007 — do NOT submit blind market orders. The operator should retry when the market is available.

### Fee Handling

- Taker fee from `getFeeSchedule()` uses 0-100 percentage scale. Convert to decimal: `takerFeePercent / 100`
- Close trade fee reduces realized P&L
- Retry trade fee affects the new edge calculation
- Use `Decimal` (decimal.js) for all financial math

### DoD Gates (from Epic 4.5 Retro Action Items)

1. **Test isolation** — all new tests must mock platform API calls, no live HTTP
2. **Interface preservation** — do not rename existing interface methods; add new ones alongside if needed
3. **Normalization ownership** — order books from `getOrderBook()` are already normalized (decimal probability 0.00–1.00)

### Project Structure Notes

- New files go in `src/modules/execution/` (resolution service, controller, scheduler, DTOs)
- Event class added to existing `src/common/events/execution.events.ts`
- New error codes in existing `src/common/errors/execution-error.ts`
- Co-located tests next to source files
- No new Prisma migration needed
- DTO files: `retry-leg.dto.ts`, `close-leg.dto.ts` in `src/modules/execution/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5, Story 5.3]
- [Source: _bmad-output/planning-artifacts/prd.md#FR-EX-06]
- [Source: _bmad-output/planning-artifacts/architecture.md#Execution Module]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error Handling]
- [Source: _bmad-output/planning-artifacts/architecture.md#Event Emission]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Decision-Ready Crisis Context]
- [Source: _bmad-output/implementation-artifacts/5-1-order-submission-position-tracking.md#Dev Notes]
- [Source: _bmad-output/implementation-artifacts/5-2-single-leg-exposure-detection-alerting.md#Dev Notes]
- [Source: CLAUDE.md#Architecture, #Error Handling, #Event Emission, #API Response Format, #Domain Rules]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

### Completion Notes List

- All 9 tasks and subtasks implemented per story specification
- 613 tests pass across 48 test files (up from 572+ baseline in Story 5.2)
- Lint clean — ESLint auto-fixed `import type` for interfaces, definite assignment in DTO, non-null assertions on array access
- `ExposureAlertScheduler` uses `SINGLE_LEG_EXPOSURE_REMINDER` event name (not `SINGLE_LEG_EXPOSURE`) to avoid inflating ExposureTrackerService incident counts
- Controller error mapping: 2005→409, 2007+warning→422, platform errors→502, unknown→500
- `closePosition()` added to IRiskManager and all existing mocks updated (execution-queue.service.spec.ts)
- P&L calculation uses linked order record's fillPrice (not position.entryPrices) per story spec
- No new Prisma migration needed

### Code Review Fixes Applied
- **[M4] Eliminated P&L scenario duplication:** Refactored `ExposureAlertScheduler` to delegate P&L scenario building to `SingleLegResolutionService.buildPnlScenarios()` instead of duplicating ~100 lines of logic
- **[L2] Fixed N+1 query:** Added `PositionRepository.findByStatusWithPair()` — scheduler now loads positions with pair relation in a single query instead of calling `findByIdWithPair()` per position
- **[M1] File list corrected:** Added missing `single-leg-pnl.util.ts` entry

### File List

**Created:**
- `src/modules/execution/single-leg-resolution.service.ts` — Core retryLeg() and closeLeg() logic
- `src/modules/execution/single-leg-resolution.service.spec.ts` — 14 unit tests
- `src/modules/execution/single-leg-resolution.controller.ts` — REST endpoints POST :id/retry-leg, POST :id/close-leg
- `src/modules/execution/single-leg-resolution.controller.spec.ts` — 9 unit tests
- `src/modules/execution/exposure-alert-scheduler.service.ts` — 60s recurring re-emission scheduler
- `src/modules/execution/exposure-alert-scheduler.service.spec.ts` — 7 unit tests
- `src/modules/execution/retry-leg.dto.ts` — RetryLegDto with price validation
- `src/modules/execution/close-leg.dto.ts` — CloseLegDto with optional rationale

**Modified:**
- `src/common/events/execution.events.ts` — Added SingleLegResolvedEvent class
- `src/common/events/event-catalog.ts` — Added SINGLE_LEG_RESOLVED, SINGLE_LEG_EXPOSURE_REMINDER
- `src/common/events/execution.events.spec.ts` — Added SingleLegResolvedEvent tests
- `src/common/errors/execution-error.ts` — Added error codes 2005, 2006, 2007
- `src/common/interfaces/risk-manager.interface.ts` — Added closePosition() method
- `src/modules/risk-management/risk-manager.service.ts` — Implemented closePosition()
- `src/modules/risk-management/risk-manager.service.spec.ts` — Added 5 closePosition() tests
- `src/persistence/repositories/position.repository.ts` — Added findByIdWithPair(), updateWithOrder(), findByStatusWithPair()
- `src/modules/execution/execution.module.ts` — Registered new providers and controller
- `src/modules/execution/execution-queue.service.spec.ts` — Added closePosition to IRiskManager mock
- `src/modules/execution/single-leg-pnl.util.ts` — Fixed unused parameter lint warning (_filledSide)
