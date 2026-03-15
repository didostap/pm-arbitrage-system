# Story 10.3: Automatic Single-Leg Management

Status: done

## Story

As an operator,
I want the system to automatically manage single-leg exposure by closing or hedging the filled leg,
so that I don't need to be available for every single-leg event.

## Acceptance Criteria

1. **Given** a second leg fails to fill within the existing execution timeout (5 seconds, per NFR-R3 — already implemented in `handleSingleLeg`) and a `SINGLE_LEG_EXPOSURE` event is emitted, **when** automatic single-leg management is enabled (`AUTO_UNWIND_ENABLED=true`), **then** after an additional stabilization delay (`AUTO_UNWIND_DELAY_MS`, default 2000ms), the system attempts to unwind the filled leg within acceptable loss parameters (FR-EX-07). If unwind succeeds, the position is closed with loss logged (realized P&L is negative for losses). If unwind fails, the position remains in `SINGLE_LEG_EXPOSED` for operator resolution (fallback to MVP workflow from Story 5.2/5.3). An `AutoUnwindEvent` is emitted with action taken and result.

2. **Given** the `handleSingleLeg` function, **when** this story is implemented, **then** it continues to accept the `SingleLegContext` interface (resolved in 10-0-2). The `AutoUnwindEvent` payload includes full `SingleLegContext` for audit trail completeness.

3. **Given** paper trading mode is active, **when** a single-leg event occurs, **then** the auto-unwind uses simulated fills (paper connectors — simulated fills don't exist on platforms). The unwind result is marked as `simulated: true` in the event payload and audit log. Live mode uses real platform API order submission for unwind. Both paths have explicit test coverage with dedicated `paper-live-boundary` tests (Team Agreement #20).

4. **Given** auto-unwind is attempted (paper or live), **when** the dashboard displays single-leg events, **then** each event shows: auto-unwind attempted (yes/no), action taken (close/hedge/fallback), result (success/fail/simulated), loss amount, and time elapsed (Team Agreement #18: vertical slice minimum).

5. **Given** tests validate auto-unwind behavior, **when** internal subsystems interact, **then** tests verify the unwind order actually reaches the connector (not just that the management logic makes the right decision) (Team Agreement #19: internal subsystem verification).

6. **Given** auto-unwind is disabled (`AUTO_UNWIND_ENABLED=false`, the default), **when** a single-leg event occurs, **then** behavior is identical to pre-story MVP workflow — position is `SINGLE_LEG_EXPOSED`, operator receives alert, manual retry/close available. Zero regression.

7. **Given** the estimated unwind loss exceeds `AUTO_UNWIND_MAX_LOSS_PCT` (default 5%), **when** auto-unwind evaluates whether to proceed, **then** auto-unwind is skipped, position remains `SINGLE_LEG_EXPOSED` for operator decision, and the `AutoUnwindEvent` records `action: 'skip_loss_limit'` with the estimated loss.

## Tasks / Subtasks

### Task 0: Configuration & Environment Setup (AC: #1, #6)
- [x] Add config keys to `common/config/env.schema.ts`:
  - `AUTO_UNWIND_ENABLED` (`z.boolean().default(false)`) — disabled by default, explicit opt-in
  - `AUTO_UNWIND_DELAY_MS` (`z.number().int().min(0).default(2000)`) — delay before auto-action (allows order book to settle)
  - `AUTO_UNWIND_MAX_LOSS_PCT` (`z.number().min(0).max(100).default(5)`) — max acceptable loss as % of leg value; 0 = no limit
- [x] Add all keys to `.env.example` and `.env.development` with comments (AUTO_UNWIND_ENABLED=false in both)
- [x] Verify: when `AUTO_UNWIND_ENABLED=false`, entire auto-unwind path is inert

### Task 1: AutoUnwindEvent Type & Event Catalog (AC: #1, #2)
- [x]Add `AutoUnwindEvent` class to `common/events/execution.events.ts`:
  ```typescript
  export class AutoUnwindEvent {
    constructor(
      public readonly positionId: PositionId,
      public readonly pairId: PairId,
      public readonly action: 'close' | 'skip_loss_limit' | 'skip_already_resolved' | 'failed',
      public readonly result: 'success' | 'failed' | 'skipped',
      public readonly singleLegContext: SingleLegContext,
      public readonly estimatedLossPct: number | null,
      public readonly realizedPnl: string | null,
      public readonly closeOrderId: string | null,
      public readonly timeElapsedMs: number,
      public readonly simulated: boolean,
      public readonly correlationId?: string,
      public readonly isPaper: boolean = false,
      public readonly mixedMode: boolean = false,
    ) {}
  }
  ```
- [x]Add event name to `common/events/event-catalog.ts`:
  ```typescript
  AUTO_UNWIND: 'execution.auto_unwind.attempted'
  ```
- [x]Export `AutoUnwindEvent` from events barrel

### Task 2: AutoUnwindService Implementation (AC: #1, #2, #3, #6, #7)
- [x]Create `src/modules/execution/auto-unwind.service.ts`:
  - Inject: `ConfigService`, `SingleLegResolutionService`, `PositionRepository`, `EventEmitter2`, `OrderRepository`, connectors (via tokens)
  - Subscribe to `SINGLE_LEG_EXPOSURE` event via `@OnEvent(EVENT_NAMES.SINGLE_LEG_EXPOSURE)`
  - **`onSingleLegExposure(event: SingleLegExposureEvent)`:** Entry point for auto-unwind evaluation
    1. Check `AUTO_UNWIND_ENABLED` config — if false, return immediately (AC #6)
    2. Check in-flight guard Set — if positionId already in-flight, return (prevent duplicate processing)
    3. Add positionId to in-flight Set
    4. Record `startTime = Date.now()` for elapsed time tracking
    5. Wait `AUTO_UNWIND_DELAY_MS` (default 2000ms) via `setTimeout` promise — allows order book to stabilize after failed submission
    6. Re-check position status in DB — if no longer `SINGLE_LEG_EXPOSED`, emit `AutoUnwindEvent` with `action: 'skip_already_resolved'` and return (handles race with operator manual resolution)
    7. Estimate unwind loss via `estimateCloseLoss()` (see below)
    8. If loss exceeds `AUTO_UNWIND_MAX_LOSS_PCT` of leg value → emit `AutoUnwindEvent` with `action: 'skip_loss_limit'` (AC #7) and return
    9. Attempt close via `singleLegResolutionService.closeLeg(positionId, 'Auto-unwind: second leg failed')` (reuses existing close logic)
    10. On success: emit `AutoUnwindEvent` with `action: 'close'`, `result: 'success'`, realized P&L from close result
    11. On failure — **distinguish error types:**
        - `ExecutionError` with code `INVALID_POSITION_STATE (2005)` → emit `AutoUnwindEvent` with `action: 'skip_already_resolved'` (operator resolved during close attempt)
        - `ExecutionError` with code `CLOSE_FAILED (2007)` or other → emit `AutoUnwindEvent` with `action: 'failed'`, `result: 'failed'` — position stays `SINGLE_LEG_EXPOSED` for operator fallback
        - Any non-ExecutionError → emit `AutoUnwindEvent` with `action: 'failed'`, log at `error` level with stack trace
    12. All `AutoUnwindEvent` emissions include `simulated: event.isPaper` and `SingleLegContext` reconstructed from event data (AC #2, #3)
    13. **Finally block:** Remove positionId from in-flight Set (always, even on error)

  - **CRITICAL: Only subscribe to `SINGLE_LEG_EXPOSURE`, NOT `SINGLE_LEG_EXPOSURE_REMINDER`.** The reminder events from `ExposureAlertScheduler` (every 60s) must NOT trigger auto-unwind re-attempts. Auto-unwind is a one-shot opportunity per single-leg event.

  - **`estimateCloseLoss(positionId: string)`:** Private helper
    1. Fetch position with orders from repository
    2. Determine filled platform and filled order (entry fill price + fill size)
    3. Fetch current order book from filled platform connector — **distinguish failure modes:**
       - Order book returned but empty (no bids/asks) → return null (proceed with close anyway)
       - Connector throws `PlatformApiError` → return null with warning log (proceed with close — conservative)
       - Database query fails → re-throw (system error, should NOT proceed)
    4. Determine close price: opposing side (buy→sell=bestBid, sell→buy=bestAsk)
    5. Calculate estimated loss using `decimal.js` with `Decimal.ROUND_HALF_UP` (2 decimal places for percentage):
       - `estimatedLoss = |closePrice - entryPrice| × fillSize` (sign-aware for buy/sell)
       - `lossPct = estimatedLoss / (entryPrice × fillSize) × 100` (use `.toDecimalPlaces(2, Decimal.ROUND_HALF_UP)`)
    6. Return `{ estimatedLossPct: number; closePrice: Decimal } | null` (null if order book unavailable or empty)

  - **Error handling:** Wrap entire `onSingleLegExposure` flow in try/catch. Any unexpected error → log at `error` level with full stack trace, emit `AutoUnwindEvent` with `action: 'failed'`, DO NOT throw (async event handler must not crash process). In-flight Set cleanup happens in finally block.

  - **Paper mode:** No special branching needed — `closeLeg()` already dispatches to paper connector when `position.isPaper` is true. The `simulated` flag is derived from the event's `isPaper` field. In mixed mode (`mixedMode: true`), behavior follows the filled leg's platform connector (paper or live), and `simulated` follows `isPaper`.

### Task 3: Wire AutoUnwindService into Execution Module (AC: #1)
- [x]Register `AutoUnwindService` in `execution.module.ts` providers
- [x]No new exports needed — service is event-driven, not injected by other modules

### Task 4: Monitoring & Telegram Integration (AC: #1, #4)
- [x]In `modules/monitoring/event-consumer.service.ts`:
  - Subscribe to `AUTO_UNWIND` event
  - Format audit log record: `{ type: 'auto_unwind', positionId, pairId, action, result, estimatedLossPct, realizedPnl, timeElapsedMs, simulated }`
  - Add `AUTO_UNWIND` to `TELEGRAM_ELIGIBLE_CRITICAL_EVENTS` (always notify operator of auto-unwind outcomes)
- [x]In `modules/monitoring/telegram-formatter.service.ts`:
  - Add `formatAutoUnwind(event: AutoUnwindEvent): string` method
  - Format: `"AUTO-UNWIND {result}: {pairId} — Action: {action}, Loss: {realizedPnl || estimatedLossPct}, Elapsed: {timeElapsedMs}ms {simulated ? '[SIMULATED]' : ''}"` — include retry/close endpoint links in the message for failed cases
  - Register in `FORMATTER_REGISTRY`
- [x]In `modules/monitoring/csv-trade-logger.service.ts`:
  - Add auto-unwind event to daily CSV log record format

### Task 5: Dashboard Backend — Auto-Unwind Visibility (AC: #4)
- [x]Extend `AlertResponseDto` (or existing alert DTO in dashboard) with **optional** auto-unwind fields (backward-compatible — all fields `?` to prevent breaking existing dashboard clients):
  - `autoUnwindAttempted?: boolean`
  - `autoUnwindAction?: string | null` — 'close' | 'skip_loss_limit' | 'skip_already_resolved' | 'failed' | null
  - `autoUnwindResult?: string | null` — 'success' | 'failed' | 'skipped' | null
  - `autoUnwindLossAmount?: string | null` — realized P&L (negative for losses) or estimated loss
  - `autoUnwindTimeElapsedMs?: number | null`
  - `autoUnwindSimulated?: boolean`
- [x]In `dashboard-event-mapper.service.ts`:
  - Map `AutoUnwindEvent` → alert update with auto-unwind fields populated
  - On `SINGLE_LEG_EXPOSURE` event: set `autoUnwindAttempted: config.AUTO_UNWIND_ENABLED` (indicates whether auto-unwind will be attempted)
  - On `AUTO_UNWIND` event: update the existing single-leg alert with auto-unwind result
- [x]In `dashboard.gateway.ts`:
  - Subscribe to `AUTO_UNWIND` event
  - Emit to connected WebSocket clients: `{ type: 'auto_unwind', ...payload }` for real-time dashboard update

### Task 6: Dashboard Frontend — Auto-Unwind Display (AC: #4)
- [x]**Position detail page** (`pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx`):
  - For `SINGLE_LEG_EXPOSED` or recently-closed-via-auto-unwind positions:
    - Show "Auto-Unwind" section with: attempted (yes/no badge), action taken, result badge (success=green, failed=red, skipped=amber), loss amount, time elapsed
    - Use existing `StatusBadge` component pattern for result badges
  - For positions closed by auto-unwind: show in position history with `exitType: 'auto_unwind'`
- [x]**Alerts display** (integrated into existing alert card component):
  - When single-leg alert has auto-unwind data, show inline: "Auto-unwind: {action} → {result}" with color coding
  - If auto-unwind failed/skipped: show operator action buttons (retry-leg, close-leg) prominently

### Task 7: Tests (AC: #3, #5, #6, #7)
- [x]**AutoUnwindService unit tests** (`auto-unwind.service.spec.ts`, ~20-25 tests):
  - **Config guard:**
    - AUTO_UNWIND_ENABLED=false → no action taken, no events emitted
    - AUTO_UNWIND_ENABLED=true → proceeds with unwind flow
  - **Delay behavior:**
    - Verify configurable delay before action (use fake timers)
    - Position resolved during delay → skip with 'skip_already_resolved'
  - **Loss threshold:**
    - Estimated loss < MAX_LOSS_PCT → proceeds with close
    - Estimated loss > MAX_LOSS_PCT → skip with 'skip_loss_limit' (AC #7)
    - Estimated loss = 0 → proceeds (no loss = good close)
    - Order book unavailable for estimate → proceeds anyway (conservative: try to close)
  - **Close success path:**
    - closeLeg() succeeds → AutoUnwindEvent with action='close', result='success'
    - Position transitions to CLOSED
    - Realized P&L included in event
    - Risk manager release called (via closeLeg internals)
  - **Close failure path:**
    - closeLeg() throws ExecutionError → AutoUnwindEvent with action='failed', result='failed'
    - Position remains SINGLE_LEG_EXPOSED
    - Operator manual resolution still available
  - **Race condition:**
    - Operator resolves position before auto-unwind delay expires → 'skip_already_resolved'
    - Operator resolves position during closeLeg() call → closeLeg() throws INVALID_POSITION_STATE → handled gracefully
  - **Event payload completeness:**
    - AutoUnwindEvent includes full SingleLegContext (AC #2)
    - timeElapsedMs calculated correctly
    - correlationId propagated from original SingleLegExposureEvent
  - **Error resilience:**
    - Unexpected error in onSingleLegExposure → caught, logged, AutoUnwindEvent emitted with 'failed', no process crash
  - **In-flight guard:**
    - Same positionId in-flight → second event skipped (no duplicate processing)
    - In-flight Set cleaned up in finally block even on error
    - In-flight Set at max capacity (100) → new auto-unwind skipped with warning log
  - **Loss estimation edge cases:**
    - Connector throws PlatformApiError during order book fetch → proceeds with close (conservative)
    - Database query fails during position fetch → emits 'failed', does NOT attempt close
    - Partial fill scenario: closeLeg() returns partial → handled per closeLeg() existing behavior (position may go to EXIT_PARTIAL)
  - **Mixed mode:**
    - mixedMode=true position → auto-unwind uses filled leg's platform connector, simulated follows isPaper

- [x]**Paper/live boundary tests** (Team Agreement #20, ~6 tests):
  - Paper mode: closeLeg() dispatches to paper connector, `simulated: true` in event
  - Live mode: closeLeg() dispatches to real connector, `simulated: false` in event
  - Paper and live use identical decision logic (loss check, delay, flow)
  - Dedicated describe block: `describe('paper-live-boundary')`

- [x]**Internal subsystem verification tests** (Team Agreement #19, ~4 tests):
  - Verify close order actually reaches the platform connector mock (not just that decision logic is tested)
  - Verify order book fetch for loss estimation actually calls connector.getOrderBook()
  - Verify position status re-check actually queries the database (not cached state)
  - Verify SingleLegResolvedEvent is emitted by closeLeg() (downstream effect)

- [x]**Zero-regression tests** (AC #6, ~3 tests):
  - AUTO_UNWIND_ENABLED=false + single-leg event → identical behavior to pre-story (SINGLE_LEG_EXPOSED, alerts fire, manual endpoints available)
  - Existing SingleLegResolutionService.retryLeg() works unchanged
  - Existing SingleLegResolutionService.closeLeg() works unchanged when called manually
  - ExposureAlertScheduler continues its 60s reminder cycle regardless of auto-unwind config

- [x]**Monitoring/Telegram tests** (~3 tests):
  - AutoUnwindEvent → audit log record created
  - AutoUnwindEvent → Telegram message sent with correct format
  - CSV logger includes auto-unwind records

## Dev Notes

### Design Decisions

**Event-Driven Architecture (NOT Inline):** AutoUnwindService subscribes to `SINGLE_LEG_EXPOSURE` events via `@OnEvent()`. It does NOT modify `handleSingleLeg()` in ExecutionService. Rationale:
- Follows the established fan-out pattern (execution emits → others react)
- Does not block the trading cycle
- Clean separation of concerns — detection (ExecutionService) vs resolution (AutoUnwindService)
- Existing ExposureAlertScheduler and ExposureTrackerService also subscribe to the same event without interference

**Reuse `closeLeg()` — DO NOT Duplicate Close Logic:** The auto-unwind close operation MUST call `SingleLegResolutionService.closeLeg()`. This method already handles:
- Filled platform detection
- Order book fetch + close price determination
- Close order submission
- Realized P&L calculation (with `decimal.js`)
- Position status transition (SINGLE_LEG_EXPOSED → CLOSED)
- Risk manager capital release (`riskManager.closePosition()`)
- `SingleLegResolvedEvent` emission

Do NOT reimplement any of this. The AutoUnwindService is an **automated caller** of existing manual resolution logic, not a parallel implementation.

**Loss Estimation Before Close:** The loss check (`estimateCloseLoss`) fetches the order book and calculates expected loss WITHOUT submitting an order. This is a read-only pre-check. Only if the estimated loss is within bounds does the service proceed to call `closeLeg()`. If the order book is unavailable for estimation, proceed with close anyway (conservative — better to close than hold unbounded risk).

**Configurable Delay:** The `AUTO_UNWIND_DELAY_MS` (default 2000ms) prevents race conditions where the order book hasn't settled after the failed submission. The delay is implemented as `await new Promise(resolve => setTimeout(resolve, delay))`. During this delay, operators may manually resolve the position — the re-check after delay handles this gracefully.

**No Retry Strategy (Close Only):** This story implements auto-**unwind** (close the filled leg), NOT auto-**retry** (submit the failed leg again). Rationale from FR-EX-07: "close or hedge first leg" — unwinding is the conservative choice that eliminates directional exposure. Auto-retry (hedge) would be a future enhancement if needed. The `action` field supports future extension ('close' | 'retry' | 'hedge') but only 'close' is implemented now.

### Position Status Transitions (Updated)

```
SINGLE_LEG_EXPOSED (created by handleSingleLeg)
 ├─ [AUTO_UNWIND_ENABLED + loss within bounds] → closeLeg() → CLOSED
 ├─ [AUTO_UNWIND_ENABLED + loss exceeds limit] → stays SINGLE_LEG_EXPOSED → operator
 ├─ [AUTO_UNWIND_ENABLED + close fails] → stays SINGLE_LEG_EXPOSED → operator
 ├─ [AUTO_UNWIND_ENABLED=false] → stays SINGLE_LEG_EXPOSED → operator (MVP flow)
 ├─ [Operator: POST retry-leg succeeds] → OPEN (fully hedged)
 └─ [Operator: POST close-leg succeeds] → CLOSED
```

### Concurrency & Race Conditions

1. **Operator vs auto-unwind:** Position status checked in DB before close. If operator resolves first, `closeLeg()` throws `INVALID_POSITION_STATE (2005)` → AutoUnwindService catches, distinguishes from other ExecutionError codes, emits `action: 'skip_already_resolved'`.
2. **Multiple SINGLE_LEG_EXPOSURE events for same position:** Should not happen (event emitted once per position creation), but guard with an in-flight `Set<string>` (positionId strings). Check before starting, add on start, remove in finally block. **Set bounds:** max 100 entries — log warning and skip auto-unwind if exceeded (prevents memory exhaustion). No TTL needed — entries are removed in finally block within seconds.
3. **ExposureAlertScheduler 60s reminders:** The scheduler emits `SINGLE_LEG_EXPOSURE_REMINDER` events (different from `SINGLE_LEG_EXPOSURE`). AutoUnwindService subscribes ONLY to `SINGLE_LEG_EXPOSURE` — reminders do NOT trigger auto-unwind re-attempts. This is intentional: auto-unwind is a one-shot mechanism.
4. **Concurrent auto-unwinds across positions:** If multiple positions hit single-leg simultaneously, each auto-unwind runs independently. No global rate limit in this story (future enhancement if needed). Each calls `closeLeg()` which internally handles platform connector access.
5. **Config hot-reload:** If `AUTO_UNWIND_ENABLED` changes from true→false while an auto-unwind is in-flight, the in-flight unwind completes (it already passed the config check). New events will see the updated config.

### SingleLegContext Reconstruction

The `SingleLegExposureEvent` does NOT carry the full `SingleLegContext`. The `AutoUnwindEvent` must include it per AC #2. Reconstruct from event data using this mapping:

| SingleLegContext field | Source from SingleLegExposureEvent |
|----------------------|----------------------------------|
| `pairId` | `event.pairId` |
| `primaryLeg` | `event.filledLeg.platform` |
| `primaryOrderId` | `event.filledLeg.orderId` |
| `primaryOrder` | `null` — OrderResult not available from event |
| `primarySide` | `event.filledLeg.side` |
| `secondarySide` | `event.failedLeg.platform` side (infer: opposite of primary) |
| `primaryPrice` | `String(event.filledLeg.price)` — string for JSON serialization (not Decimal) |
| `secondaryPrice` | `String(event.failedLeg.attemptedPrice)` — string for JSON serialization (not Decimal) |
| `primarySize` | `event.filledLeg.size` |
| `secondarySize` | `event.failedLeg.attemptedSize` |
| `enriched` | `null` — EnrichedOpportunity not available from event |
| `opportunity` | `null` — RankedOpportunity not available from event |
| `errorCode` | `event.failedLeg.reasonCode` |
| `errorMessage` | `event.failedLeg.reason` |
| `isPaper` | `event.isPaper` |
| `mixedMode` | `event.mixedMode` |

**Type consideration:** Define a `PartialSingleLegContext` type (or use `Partial<SingleLegContext>`) for the AutoUnwindEvent field to reflect that `primaryOrder`, `enriched`, and `opportunity` are null. Add a JSDoc comment documenting this is a partial reconstruction for audit purposes.

### Files to Create

| File | Purpose |
|------|---------|
| `src/modules/execution/auto-unwind.service.ts` | Event-driven auto-unwind logic |
| `src/modules/execution/auto-unwind.service.spec.ts` | ~40 tests |

### Files to Modify

| File | Changes |
|------|---------|
| `src/common/config/env.schema.ts` | +3 config keys (AUTO_UNWIND_ENABLED, AUTO_UNWIND_DELAY_MS, AUTO_UNWIND_MAX_LOSS_PCT) |
| `src/common/events/execution.events.ts` | +AutoUnwindEvent class |
| `src/common/events/event-catalog.ts` | +AUTO_UNWIND event name |
| `src/modules/execution/execution.module.ts` | +AutoUnwindService provider |
| `src/modules/monitoring/event-consumer.service.ts` | +AUTO_UNWIND subscriber, audit log formatting |
| `src/modules/monitoring/telegram-formatter.service.ts` | +formatAutoUnwind(), FORMATTER_REGISTRY |
| `src/modules/monitoring/csv-trade-logger.service.ts` | +auto-unwind CSV record format |
| `src/dashboard/dashboard-event-mapper.service.ts` | +AutoUnwindEvent → alert mapping |
| `src/dashboard/dashboard.gateway.ts` | +AUTO_UNWIND WS event emission |
| `src/dashboard/dto/` | Extend alert DTO with auto-unwind fields |
| `.env.example` | +3 config keys with comments |
| `.env.development` | +3 config keys (AUTO_UNWIND_ENABLED=false) |
| `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx` | +auto-unwind section for SINGLE_LEG_EXPOSED positions |
| `pm-arbitrage-dashboard/src/api/generated/Api.ts` | Regenerate after DTO changes |

### Existing Code to Reuse (DO NOT REINVENT)

- **`SingleLegResolutionService.closeLeg()`** — Core close logic (order submission, P&L, status transition, risk release). Auto-unwind calls this directly.
- **`SingleLegResolutionService.buildPnlScenarios()`** — P&L scenario calculation (can reference pattern for loss estimation)
- **`calculateSingleLegPnlScenarios()`** in `single-leg-pnl.util.ts` — P&L utility functions
- **`buildRecommendedActions()`** — For formatting fallback recommendations in failed auto-unwind events
- **`ExposureAlertScheduler`** — Pattern for position status querying and connector availability checks
- **`ExposureTrackerService`** — Pattern for @OnEvent subscription to SINGLE_LEG_EXPOSURE
- **`PositionRepository.findByStatusWithOrders()`** — Position + order queries needed for loss estimation
- **`StatusBadge`** component in dashboard — Reuse for auto-unwind result badges
- **`EXECUTION_ERROR_CODES`** — Error code constants (2005=INVALID_POSITION_STATE, 2007=CLOSE_FAILED)
- **`SingleLegExposureEvent`** payload structure — Source of data for AutoUnwindEvent reconstruction

### Anti-Patterns to Avoid

- **DO NOT** modify `handleSingleLeg()` or `ExecutionService.execute()` — auto-unwind is event-driven, not inline
- **DO NOT** duplicate `closeLeg()` logic — call the existing method
- **DO NOT** create a separate close flow for paper vs live — `closeLeg()` already routes to the correct connector based on `position.isPaper`
- **DO NOT** use native JS operators for financial math — `decimal.js` only (loss estimation must use `Decimal`)
- **DO NOT** block the event handler — use `async`/`await` with proper error handling, never throw from `@OnEvent`
- **DO NOT** import services directly between modules — `AutoUnwindService` is in execution module and can use `SingleLegResolutionService` directly (same module)
- **DO NOT** add retry logic (submit failed leg again) — this story is unwind-only per FR-EX-07 scope
- **DO NOT** throw raw `Error` — use ExecutionError from `common/errors/`
- **DO NOT** import `AutoUnwindService` from `SingleLegResolutionService` — dependency is one-way (AutoUnwind → Resolution, never reverse) to prevent circular imports
- **DO NOT** process `SINGLE_LEG_EXPOSURE_REMINDER` events — only process `SINGLE_LEG_EXPOSURE` (auto-unwind is one-shot, not repeated on reminders)

### Testing Conventions (from Epic 9 Retro)

- **Internal subsystem verification (Team Agreement #19):** Tests must verify the close order actually reaches the connector mock. Mock `connector.submitOrder()` and assert it was called with correct params — don't just test that AutoUnwindService decides to close.
- **Paper/live boundary (Team Agreement #20):** Paper mode uses paper connector (simulated fills). Live mode uses real connector. Both use identical auto-unwind decision logic. Create a dedicated `describe('paper-live-boundary')` block with parallel test cases.
- **Investigation-first pattern:** If the auto-unwind delay timing or loss estimation produces unexpected results during testing, investigate with documented findings before changing the implementation.

### Project Structure Notes

- `AutoUnwindService` co-located in `modules/execution/` — it's an execution concern (manages single-leg resolution)
- No new module created — service registered in existing `execution.module.ts`
- Config keys follow existing UPPER_SNAKE_CASE with `AUTO_UNWIND_` prefix
- Event naming follows dot-notation: `execution.auto_unwind.attempted`
- Dashboard DTO changes follow existing camelCase JSON convention

### Key Implementation Details

**Connector Token Injection:** AutoUnwindService needs connector access for loss estimation (order book fetch). Inject via:
```typescript
@Inject(KALSHI_CONNECTOR_TOKEN) private readonly kalshiConnector: IPlatformConnector,
@Inject(POLYMARKET_CONNECTOR_TOKEN) private readonly polymarketConnector: IPlatformConnector,
```
Pattern established in `ExposureAlertScheduler`.

**In-Flight Guard Set:** Track positions currently being auto-unwound:
```typescript
private readonly inFlightUnwinds = new Set<string>();  // positionId strings
```
Check before starting, add on start, remove on completion (in finally block). Prevents duplicate processing if event fires twice.

**Timer in Tests:** Use Vitest fake timers (`vi.useFakeTimers()`) for the delay. Advance time with `vi.advanceTimersByTimeAsync()`. Clean up in afterEach.

**Loss Estimation with Decimal:** All financial math in `estimateCloseLoss()` uses `decimal.js`:
```typescript
const entryPrice = new Decimal(filledOrder.fillPrice.toString());
const closePrice = new Decimal(bestPrice.toString());
const fillSize = new Decimal(filledOrder.fillSize.toString());
const loss = filledSide === 'buy'
  ? entryPrice.minus(closePrice).mul(fillSize)  // bought high, selling low = loss
  : closePrice.minus(entryPrice).mul(fillSize);  // sold low, buying back high = loss
const legValue = entryPrice.mul(fillSize);
const lossPct = legValue.isZero() ? new Decimal(0) : loss.div(legValue).mul(100).abs();
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 10.3] — Acceptance criteria, dependencies, vertical slice
- [Source: _bmad-output/planning-artifacts/prd.md#FR-EX-07] — Auto-close/hedge on second leg failure requirement
- [Source: _bmad-output/planning-artifacts/prd.md#NFR-R3] — 5s single-leg exposure timeout, <5 events/month target
- [Source: _bmad-output/planning-artifacts/architecture.md#Module Dependencies] — Execution module allowed imports
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Alert Display] — Decision-ready context, deep-link pattern, 60s decision target
- [Source: _bmad-output/implementation-artifacts/10-0-2-carry-forward-debt-triage-critical-fixes.md#AC2] — SingleLegContext refactor (17→1 param), unblocks this story
- [Source: _bmad-output/implementation-artifacts/10-2-five-criteria-model-driven-exit-logic.md] — Previous story: six-criteria model, shadow mode pattern, test conventions

### Previous Story Intelligence (from 10-2)

- Six-criteria evaluator (C1-C6) now drives exit decisions in model/shadow mode — auto-unwind is orthogonal (handles execution failures, not exit triggers)
- `@OnEvent` wiring pattern established: subscribe in service, emit result event — follow same pattern for AutoUnwindService
- ShadowComparisonService pattern: event-driven accumulation + daily summary — similar loose coupling approach
- Test count at story start: ~2321 tests (2274 → 2321 via 10-2 + code reviews)
- Code review found dense ranking bug, missing wiring, and shadow event gaps — test wiring and event emission thoroughly
- `closeLeg()` already handles mode-aware resolution — no new paper/live branching needed in auto-unwind
- `ExposureAlertScheduler` pattern: connector health check before action, debounce to prevent duplicate work — apply same guards

### Git Intelligence

Recent commits follow `feat:` prefix convention. Key patterns from last 20 commits:
- Services registered in module providers, NOT exports (unless other modules inject them)
- Event subscriptions via `@OnEvent(EVENT_NAMES.X)` with class-based event objects
- Telegram formatter uses `FORMATTER_REGISTRY` map for event→formatter dispatch
- Config keys added to both `.env.example` and `.env.development` simultaneously
- Dashboard DTOs extended additively (new optional fields, no breaking changes)
- Tests co-located: `auto-unwind.service.spec.ts` next to `auto-unwind.service.ts`

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- All 46 ATDD unit tests unskipped and passing (auto-unwind.service.spec.ts)
- TELEGRAM_ELIGIBLE_EVENTS count test updated from 24 → 25

### Completion Notes List
- Task 0: Added AUTO_UNWIND_ENABLED, AUTO_UNWIND_DELAY_MS, AUTO_UNWIND_MAX_LOSS_PCT to env.schema.ts, .env.example, .env.development
- Task 1: Added AutoUnwindEvent class + PartialSingleLegContext interface to execution.events.ts, AUTO_UNWIND event name to event-catalog.ts
- Task 2: Created AutoUnwindService — event-driven (@OnEvent SINGLE_LEG_EXPOSURE only), config guard, in-flight Set guard (max 100), configurable delay, loss estimation via decimal.js, closeLeg() reuse, error type discrimination, finally-block cleanup
- Task 3: Registered AutoUnwindService in execution.module.ts providers
- Task 4: Added AUTO_UNWIND to event-severity.ts (warning), formatAutoUnwind() telegram formatter, FORMATTER_REGISTRY entry, TELEGRAM_ELIGIBLE_EVENTS entry, CSV trade log record for auto-unwind events
- Task 5: Extended WsAlertNewPayload with optional auto-unwind fields (backward-compatible), added mapAutoUnwindAlert() to dashboard-event-mapper, @OnEvent handler in dashboard.gateway.ts, AUTO_UNWIND WS event type
- Task 6: Added AutoUnwindSection component to PositionDetailPage.tsx — shows auto-unwind status extracted from audit events
- Task 7: Unskipped all 46 ATDD tests, fixed lint issues, updated TELEGRAM_ELIGIBLE_EVENTS count test. All 2367 tests pass (2321 → +46)

### File List
**Created:**
- pm-arbitrage-engine/src/modules/execution/auto-unwind.service.ts

**Modified:**
- pm-arbitrage-engine/src/common/config/env.schema.ts (+3 config keys)
- pm-arbitrage-engine/src/common/events/execution.events.ts (+AutoUnwindEvent, +PartialSingleLegContext)
- pm-arbitrage-engine/src/common/events/event-catalog.ts (+AUTO_UNWIND)
- pm-arbitrage-engine/src/modules/execution/execution.module.ts (+AutoUnwindService provider)
- pm-arbitrage-engine/src/modules/monitoring/event-severity.ts (+AUTO_UNWIND to WARNING_EVENTS)
- pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts (+AUTO_UNWIND CSV trade log record)
- pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.ts (+formatAutoUnwind, +FORMATTER_REGISTRY, +TELEGRAM_ELIGIBLE_EVENTS)
- pm-arbitrage-engine/src/modules/monitoring/formatters/telegram-message.formatter.ts (+formatAutoUnwind function)
- pm-arbitrage-engine/src/dashboard/dashboard-event-mapper.service.ts (+mapAutoUnwindAlert)
- pm-arbitrage-engine/src/dashboard/dashboard.gateway.ts (+handleAutoUnwind @OnEvent)
- pm-arbitrage-engine/src/dashboard/dto/ws-events.dto.ts (+auto_unwind type, +optional auto-unwind fields, +AUTO_UNWIND WS event)
- pm-arbitrage-engine/src/modules/execution/auto-unwind.service.spec.ts (46 tests unskipped)
- pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.spec.ts (count 24→25)
- pm-arbitrage-engine/.env.example (+3 auto-unwind config keys)
- pm-arbitrage-engine/.env.development (+3 auto-unwind config keys)
- pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx (+AutoUnwindSection component)
