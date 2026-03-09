# Story 7.5.3: Close All Positions & Updated Close UX

Status: done

## Story

As an operator,
I want a "Close All Positions" bulk action and the existing per-position close button updated to use the new dual-platform close endpoint,
so that I can quickly exit all positions in an emergency and the close button actually works for OPEN positions.

## Acceptance Criteria

### Updated Per-Position Close Button

1. **Given** the operator clicks "Close" on a position in `OPEN` or `EXIT_PARTIAL` status
   **When** the confirmation dialog appears
   **Then** it shows: pair name, current P&L, projected close P&L at current market prices (the existing `currentPnl` from enrichment), and a rationale text field
   **And** on confirmation, the frontend calls `POST /api/positions/:id/close` (the dual-platform endpoint from Story 7.5.1) instead of `POST /api/positions/:id/close-leg`
   **And** on success, the position row updates in real-time via WebSocket to reflect CLOSED status
   **And** on failure (single-leg exposure), the position row updates to `SINGLE_LEG_EXPOSED` and the operator sees the error context in a toast notification with a link to the position detail page
   [Source: epics.md#Story-7.5.3, AC: Updated Per-Position Close Button]

### Close All — Frontend

2. **Given** the operator has one or more positions in `OPEN` or `EXIT_PARTIAL` status
   **When** they click "Close All Positions"
   **Then** a confirmation dialog shows: total number of positions to close, aggregate current P&L across all closeable positions, and a warning that this will attempt to close all positions at current market prices
   **And** the dialog requires the operator to type "CLOSE ALL" to prevent accidental triggering
   **And** on confirmation, the frontend calls `POST /api/positions/close-all` with optional `{ rationale: string }`
   [Source: epics.md#Story-7.5.3, AC: Close All Bulk Action]

### Close All — Backend

3. **Given** the backend receives `POST /api/positions/close-all`
   **When** the endpoint processes the request
   **Then** it returns immediately with `202 Accepted` and a `{ batchId: string }`
   **And** positions are closed sequentially in the background (not parallel — respect rate limits and sequential execution locking from Story 4.4)
   **And** each position's close attempt uses the existing `IPositionCloseService.closePosition()` method
   **And** each position's close result is classified as `success`, `failure`, or `rate_limited`
   **And** if a PlatformApiError with a rate-limit code is encountered, the position is classified as `rate_limited` and the batch continues to the next position
   **And** on all positions processed, a `batch.complete` WebSocket event is emitted containing: `batchId`, per-position results (positionId, pairName, status, realizedPnl or error)
   [Source: epics.md#Story-7.5.3, AC: Close All Backend; Derived from: sprint-change-proposal-2026-03-08.md#Section-4]

### WebSocket Event Registration

4. **Given** a new `batch.complete` event type is introduced
   **When** Story 7.5.3 is implemented
   **Then** `DashboardEventMapperService` is updated with the new event mapping
   **And** `DASHBOARD_EVENTS` constant includes the new event type
   **And** `WsEventEnvelope` types are extended to include the batch complete payload
   [Source: epics.md#Story-7.5.3, AC: WebSocket Event Registration]

### Close All — Empty Case

5. **Given** there are no positions in `OPEN` or `EXIT_PARTIAL` status
   **When** the backend processes `POST /api/positions/close-all`
   **Then** it returns `202 Accepted` with a `batchId`
   **And** the `batch.complete` event is emitted immediately with an empty results array
   [Derived from: epics.md#Story-7.5.3, defensive edge case]

## Tasks / Subtasks

### Backend (Engine — pm-arbitrage-engine/)

- [x] T1: Extend `IPositionCloseService` interface and result types (AC: #3)
  - [x] T1.1: Add `'RATE_LIMITED'` to `PositionCloseResult.errorCode` union type in `src/common/interfaces/position-close-service.interface.ts`
  - [x] T1.2: Add `closeAllPositions(rationale?: string): Promise<{ batchId: string }>` method to `IPositionCloseService`
  - [x] T1.3: Define `BatchPositionResult` type: `{ positionId: string; pairName: string; status: 'success' | 'failure' | 'rate_limited'; realizedPnl?: string; error?: string }`
  - [x] T1.4: Export new types from `src/common/interfaces/index.ts`

- [x] T2: Create `BatchCompleteEvent` and register in event catalog (AC: #4)
  - [x] T2.1: Create `src/common/events/batch.events.ts` with `BatchCompleteEvent extends BaseEvent` — constructor: `batchId: string`, `results: BatchPositionResult[]`, `correlationId?: string`
  - [x] T2.2: Add `BATCH_COMPLETE: 'execution.batch.complete'` to `EVENT_NAMES` in `src/common/events/event-catalog.ts`
  - [x] T2.3: Export from `src/common/events/index.ts` (if barrel exists) or direct import
  - [x] T2.4: Unit test in `src/common/events/batch.events.spec.ts`

- [x] T3: Implement `closeAllPositions()` in `PositionCloseService` (AC: #3, #5)
  - [x] T3.1: Inject `PositionRepository` (already available via module)
  - [x] T3.2: Generate `batchId` via `randomUUID()` (Node.js `crypto`)
  - [x] T3.3: Query all positions with status `{ in: ['OPEN', 'EXIT_PARTIAL'] }` using `positionRepository.findByStatus()` or equivalent
  - [x] T3.4: Fire-and-forget background processing via `void this.processCloseAllBatch(batchId, positions, rationale)` — do NOT await
  - [x] T3.5: Return `{ batchId }` immediately
  - [x] T3.6: In `processCloseAllBatch()`: iterate positions sequentially with `for...of`, call `this.closePosition(position.id, rationale)` for each
  - [x] T3.7: Classify each result: if `result.success` → `'success'`; if `result.errorCode === 'RATE_LIMITED'` → `'rate_limited'`; otherwise → `'failure'`
  - [x] T3.8: Build `BatchPositionResult` per position with `positionId`, `pairName` (from pair relation), `status`, `realizedPnl`, `error`
  - [x] T3.9: After all positions processed, emit `BatchCompleteEvent` via `eventEmitter.emit(EVENT_NAMES.BATCH_COMPLETE, new BatchCompleteEvent(batchId, results))`
  - [x] T3.10: Wrap entire `processCloseAllBatch()` in try/catch — log any unexpected error, still emit batch.complete with what we have
  - [x] T3.11: Add `'RATE_LIMITED'` classification in the existing `closePosition()` method: when catching `PlatformApiError`, check if error code is in the rate-limit range (1003-1005); if so, return `{ success: false, errorCode: 'RATE_LIMITED', error: message }`
  - [x] T3.12: Unit tests in `position-close.service.spec.ts` for batch: happy path, mixed results, empty positions, rate-limited classification

- [x] T4: Add `POST /api/positions/close-all` endpoint (AC: #3, #5)
  - [x] T4.1: Create `src/dashboard/dto/close-all-positions.dto.ts` with `CloseAllPositionsDto { rationale?: string }` and Swagger decorators
  - [x] T4.2: Add `@Post('close-all')` `@HttpCode(HttpStatus.ACCEPTED)` method in `PositionManagementController`
  - [x] T4.3: Call `closeService.closeAllPositions(dto.rationale)`, return `{ data: { batchId }, timestamp: ISO string }`
  - [x] T4.4: Swagger: `@ApiResponse({ status: 202, description: 'Batch close initiated' })`
  - [x] T4.5: Guard with `AuthTokenGuard` (existing on controller)
  - [x] T4.6: Unit test in `position-management.controller.spec.ts`

- [x] T5: Wire `batch.complete` into WebSocket pipeline (AC: #4)
  - [x] T5.1: Add `BATCH_COMPLETE: 'batch.complete'` to `WS_EVENTS` in `src/dashboard/dto/ws-events.dto.ts`
  - [x] T5.2: Add `BatchCompleteWsPayload` interface: `{ batchId: string; results: Array<{ positionId: string; pairName: string; status: string; realizedPnl?: string; error?: string }> }`
  - [x] T5.3: Add `mapBatchComplete(event: BatchCompleteEvent)` method to `DashboardEventMapperService` — maps to `WsEventEnvelope<BatchCompleteWsPayload>`
  - [x] T5.4: Add `@OnEvent(EVENT_NAMES.BATCH_COMPLETE)` handler in `DashboardGateway` that calls mapper then `broadcast()`
  - [x] T5.5: Unit tests for mapper and gateway handler

### Frontend (Dashboard — pm-arbitrage-dashboard/)

- [x] T6: Fix close mutation to call correct endpoint (AC: #1)
  - [x] T6.1: In `src/hooks/useDashboard.ts`, change `useClosePosition()` mutation from `api.singleLegResolutionControllerCloseLeg(id, { rationale })` to `api.positionManagementControllerClosePosition(id, { rationale })`
  - [x] T6.2: Verify response shape — `positionManagementControllerClosePosition` returns `{ data: PositionCloseResult, timestamp }` with `success`, `realizedPnl?`, `error?`, `errorCode?`
  - [x] T6.3: Update error handling in mutation/dialog if response shape differs from current `CloseLegResponseDto`

- [x] T7: Update close button visibility (AC: #1)
  - [x] T7.1: In `src/components/PositionsTable.tsx`, change close button condition from `status === 'OPEN' || status === 'SINGLE_LEG_EXPOSED'` to `status === 'OPEN' || status === 'EXIT_PARTIAL'`
  - [x] T7.2: `SINGLE_LEG_EXPOSED` positions have dedicated retry-leg and close-leg buttons (from Story 5.3) that call `SingleLegResolutionController` — these remain UNCHANGED. Do NOT remove or modify those buttons. The "Close" button (dual-platform close via 7.5.1) is a different action that only applies to OPEN and EXIT_PARTIAL.

- [x] T8: Add projected close P&L to ClosePositionDialog (AC: #1)
  - [x] T8.1: In `src/components/ClosePositionDialog.tsx`, display the `currentPnl` field from the position prop (already available from enriched position data in the table)
  - [x] T8.2: Format as "Projected P&L at close: -$X.XX" with red/green color coding
  - [x] T8.3: Show null/dash if `currentPnl` is unavailable (enrichment partial/failed)

- [x] T9: Add failure toast with detail page link (AC: #1)
  - [x] T9.1: On close failure in `ClosePositionDialog`, show toast with error message and a clickable link to `/positions/:id` (the detail page from Story 7.5.2)
  - [x] T9.2: Single-leg exposure failure (errorCode `EXECUTION_FAILED`) gets specific messaging: "Close resulted in single-leg exposure — view position details"

- [x] T10: Create CloseAllDialog component (AC: #2)
  - [x] T10.1: Create `src/components/CloseAllDialog.tsx` using same Dialog/Button/Textarea patterns as ClosePositionDialog
  - [x] T10.2: Props: `open`, `onOpenChange`, `positions` (array of closeable positions from table data)
  - [x] T10.3: Display: position count, aggregate current P&L (sum `currentPnl` across positions using simple JS — frontend display, not financial math), warning text: "This will attempt to close all open positions at current market prices"
  - [x] T10.4: Text input with placeholder "Type CLOSE ALL to confirm" — submit button disabled until input matches "CLOSE ALL" (case-sensitive)
  - [x] T10.5: Optional rationale textarea (same as per-position dialog)
  - [x] T10.6: On confirm: call `useCloseAllPositions()` mutation, show toast "Batch close initiated — watch for WebSocket updates", close dialog

- [x] T11: Create `useCloseAllPositions()` hook (AC: #2)
  - [x] T11.1: In `src/hooks/useDashboard.ts`, add `useCloseAllPositions()` mutation
  - [x] T11.2: Calls `api.positionManagementControllerCloseAll({ rationale })` (method name will be in regenerated client)
  - [x] T11.3: On success: invalidate positions and overview queries, show success toast with batchId
  - [x] T11.4: On error: show error toast

- [x] T12: Add "Close All Positions" button to PositionsPage (AC: #2)
  - [x] T12.1: In `src/pages/PositionsPage.tsx`, add "Close All Positions" button in the header area (near existing mode filter)
  - [x] T12.2: Button uses `variant='destructive'` styling
  - [x] T12.3: Disabled when no closeable positions exist (filter OPEN + EXIT_PARTIAL from current table data)
  - [x] T12.4: Only visible on "Open" tab (not "All" tab — closed positions can't be re-closed)
  - [x] T12.5: On click: open CloseAllDialog

- [x] T13: Handle `batch.complete` WebSocket event on frontend (AC: #3, #4)
  - [x] T13.1: Add `'batch.complete'` to WebSocket event type definitions in `src/types/ws-events.ts` (or wherever WS event types are defined in the dashboard)
  - [x] T13.2: In `WebSocketProvider.tsx`, add a handler for `batch.complete` event that shows a summary toast: "Batch close complete: X succeeded, Y failed, Z rate-limited"
  - [x] T13.3: On `batch.complete`, invalidate positions and overview queries to refresh table state

- [x] T14: Regenerate API client (AC: all)
  - [x] T14.1: After engine endpoint is complete, manually updated `src/api/generated/Api.ts` with `CloseAllPositionsDto` and `positionManagementControllerCloseAll()` method (full regeneration requires running server)
  - [x] T14.2: Verify `positionManagementControllerCloseAll()` method is generated with correct request/response types

### Verification

- [x] T15: Lint, test, verify (all ACs)
  - [x] T15.1: `pnpm lint` in engine — zero errors
  - [x] T15.2: `pnpm test` in engine — 84 files, 1514 tests passed
  - [x] T15.3: `pnpm build` in dashboard — zero TS errors
  - [x] T15.4: No `decimal.js` violations in engine (no native JS arithmetic on monetary values)

## Dev Notes

### Critical: Close Button Endpoint Migration

The most impactful change is fixing the close button to call the correct endpoint. Currently:

```
useDashboard.ts:140 → api.singleLegResolutionControllerCloseLeg(id, { rationale })
```

Must become:

```
useDashboard.ts:140 → api.positionManagementControllerClosePosition(id, { rationale })
```

The response shape differs:
- **Old** (`CloseLegResponseDto`): `{ success, realizedPnl?, closeOrderId?, reason? }`
- **New** (`PositionCloseResult`): `{ success, realizedPnl?, error?, errorCode? }`

The `ClosePositionDialog` error handling (lines 38-51) uses HTTP status codes (409, 422) — these are set by `PositionManagementController` (NOT_CLOSEABLE → 409, NOT_FOUND → 404, EXECUTION_FAILED → 422). Verify the dialog handles these correctly after the endpoint switch.
[Source: `pm-arbitrage-dashboard/src/components/ClosePositionDialog.tsx:38-51`, `pm-arbitrage-engine/src/dashboard/position-management.controller.ts:51-77`]

### Close Button Visibility Change

**Before (current):** Close button shows for `OPEN` and `SINGLE_LEG_EXPOSED`
**After:** Close button shows for `OPEN` and `EXIT_PARTIAL`

`SINGLE_LEG_EXPOSED` positions continue to use the existing retry-leg/close-leg flow from Story 5.3 via `SingleLegResolutionController`. Do NOT change that flow.
[Source: `pm-arbitrage-dashboard/src/components/PositionsTable.tsx:209`, `pm-arbitrage-engine/src/modules/execution/single-leg-resolution.controller.ts`]

### Batch Close Architecture

The `closeAllPositions()` method uses fire-and-forget pattern:

```typescript
async closeAllPositions(rationale?: string): Promise<{ batchId: string }> {
  const batchId = randomUUID();
  const positions = await this.positionRepository.findByStatus(
    { in: ['OPEN', 'EXIT_PARTIAL'] },
  );
  // Fire-and-forget — controller returns 202 immediately
  void this.processCloseAllBatch(batchId, positions, rationale);
  return { batchId };
}
```

The `processCloseAllBatch()` loop calls `this.closePosition(positionId, rationale)` per position. Each call independently acquires and releases the `ExecutionLockService` mutex — this is correct because the lock is designed for serializing individual execution operations. Sequential iteration means at most one lock acquisition at a time, so no deadlock risk.

**Correlation ID propagation:** The fire-and-forget call runs outside the original request's AsyncLocalStorage context. Capture the correlation ID before spawning the background task and pass it explicitly:
```typescript
const correlationId = this.correlationContext?.getId();
void this.processCloseAllBatch(batchId, positions, rationale, correlationId);
```
[Source: `pm-arbitrage-engine/src/modules/execution/execution-lock.service.ts:11-23`, `pm-arbitrage-engine/src/modules/execution/position-close.service.ts:60-62`, `pm-arbitrage-engine/src/common/services/correlation-context.ts`]

### Rate Limit Classification

The `position-close.service.ts` currently catches all errors from connector calls and returns `{ success: false, errorCode: 'EXECUTION_FAILED' }`. For rate limit detection, add a check when catching `PlatformApiError`:

```typescript
if (error instanceof PlatformApiError && this.isRateLimitError(error)) {
  return { success: false, error: error.message, errorCode: 'RATE_LIMITED' };
}
```

Check the error code range: `PlatformApiError` codes 1003-1005 correspond to rate limit errors.
[Source: `pm-arbitrage-engine/src/common/errors/platform-api-error.ts`, `pm-arbitrage-engine/src/common/utils/rate-limiter.ts:71-77`]

### WebSocket Event Wiring Pattern

Follow the exact pattern from `ExitTriggeredEvent` → `DashboardGateway`:

1. **Event class** (`batch.events.ts`): extends `BaseEvent`, carries `batchId` + `results[]`
2. **Event catalog** (`event-catalog.ts`): `BATCH_COMPLETE: 'execution.batch.complete'`
3. **Mapper** (`dashboard-event-mapper.service.ts`): `mapBatchComplete(event)` → `WsEventEnvelope<BatchCompleteWsPayload>`
4. **Gateway** (`dashboard.gateway.ts`): `@OnEvent(EVENT_NAMES.BATCH_COMPLETE)` → `this.broadcast(mapped)`
5. **WS types** (`ws-events.dto.ts`): `WS_EVENTS.BATCH_COMPLETE = 'batch.complete'`, payload type

Existing pattern reference: `handleExitTriggered()` at `dashboard.gateway.ts:109-113`

**Event name namespaces:** `EVENT_NAMES` uses internal NestJS event names with module prefix (`execution.batch.complete`), while `WS_EVENTS` uses client-facing event names without prefix (`batch.complete`). This is consistent with all existing events (e.g., `EVENT_NAMES.EXIT_TRIGGERED = 'execution.exit.triggered'` → `WS_EVENTS.POSITION_UPDATE = 'position.update'`).
[Source: `pm-arbitrage-engine/src/dashboard/dashboard.gateway.ts:109-113`, `pm-arbitrage-engine/src/dashboard/dashboard-event-mapper.service.ts:25-169`]

### "CLOSE ALL" Typed Confirmation — New UX Pattern

No existing phrase-confirmation pattern exists in the codebase. The risk override from Story 4.3 uses a 10-character minimum rationale, not a typed phrase. This is a new pattern:

```tsx
const [confirmText, setConfirmText] = useState('');
const isConfirmed = confirmText === 'CLOSE ALL';

<Input
  placeholder="Type CLOSE ALL to confirm"
  value={confirmText}
  onChange={(e) => setConfirmText(e.target.value)}
/>
<Button disabled={!isConfirmed || mutation.isPending} variant="destructive">
  Close All Positions
</Button>
```

Use the same Dialog/Button from `@/components/ui/` as `ClosePositionDialog`. Import `Input` from shadcn/ui (already installed via `@/components/ui/input`).
[Source: `pm-arbitrage-dashboard/src/components/ClosePositionDialog.tsx`, `pm-arbitrage-dashboard/src/components/ui/`]

### Projected Close P&L in Dialog

The `currentPnl` field is already computed by `PositionEnrichmentService` and available on every enriched position in the table. The `ClosePositionDialog` receives the full position object as a prop — just read `position.currentPnl` and display it.

No new computation is needed. Format with `font-mono tabular-nums` and red/green color coding (same pattern as PositionsTable P&L column).
[Source: `pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts`, `pm-arbitrage-dashboard/src/components/PositionsTable.tsx` P&L column formatting]

### Single-Leg Failure Toast with Detail Page Link

On close failure with single-leg exposure, show a toast with a link to the position detail page:

```tsx
toast.error(
  <span>
    Close resulted in single-leg exposure —{' '}
    <a href={`/positions/${positionId}`} className="underline">view details</a>
  </span>
);
```

The position detail page is at `/positions/:id` (delivered in Story 7.5.2).
[Source: `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx`, `pm-arbitrage-dashboard/src/App.tsx` route config]

### Aggregate P&L for Close All Dialog

The dialog sums `currentPnl` across all closeable positions for display. This is a **frontend display calculation** using simple JS `Number()` addition — NOT a financial math operation. The actual P&L computation per position is done server-side with `decimal.js`. The aggregate in the dialog is informational only (it tells the operator "approximately this much P&L will be realized").

```tsx
const aggregatePnl = positions
  .filter(p => p.currentPnl != null)
  .reduce((sum, p) => sum + Number(p.currentPnl), 0);
```

[Source: CLAUDE.md#Domain Rules — decimal.js required for financial math; frontend display aggregation is acceptable with native JS]

### Concurrency: Batch Close vs Exit Monitor

The exit monitor runs every 30s and evaluates OPEN + EXIT_PARTIAL positions. During a batch close:
- Each position close acquires `ExecutionLockService` before submitting orders
- The exit monitor does NOT acquire the lock (by design — see Story 7.5.1 dev notes)
- If the exit monitor closes a position while the batch is processing, the batch's `closePosition()` call will detect the status change after acquiring the lock (re-reads position from DB) and return gracefully without double-submitting
- This race condition is already handled by the existing `PositionCloseService` implementation

No additional concurrency protection needed for the batch.
[Source: `pm-arbitrage-engine/src/modules/execution/position-close.service.ts:65-75` (re-read after lock), Story 7.5.1 dev notes on race conditions]

### Error Handling in Batch Processing

The `processCloseAllBatch()` method must be resilient — a failure in one position should NOT halt the batch:

```typescript
for (const position of positions) {
  try {
    const result = await this.closePosition(position.id, rationale);
    results.push(this.classifyResult(position, result));
  } catch (error) {
    // Unexpected error (closePosition normally returns result, doesn't throw)
    this.logger.error(`Batch close unexpected error for ${position.id}`, error);
    results.push({
      positionId: position.id,
      pairName: this.getPairName(position),
      status: 'failure',
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
}
```

Wrap the entire method in try/catch too — if the loop itself fails (e.g., DB connection lost), emit batch.complete with partial results.
[Source: Existing error handling pattern in `position-close.service.ts:537-543`]

### Key Files to Modify

**Engine (pm-arbitrage-engine/):**

| File | Action | Notes |
|------|--------|-------|
| `src/common/interfaces/position-close-service.interface.ts` | Modify | Add `closeAllPositions()`, `RATE_LIMITED` errorCode, `BatchPositionResult` |
| `src/common/interfaces/index.ts` | Modify | Export new types |
| `src/common/events/event-catalog.ts` | Modify | Add `BATCH_COMPLETE` |
| `src/common/events/batch.events.ts` | **Create** | `BatchCompleteEvent` class |
| `src/common/events/batch.events.spec.ts` | **Create** | Event tests |
| `src/modules/execution/position-close.service.ts` | Modify | Add `closeAllPositions()`, `processCloseAllBatch()`, rate limit classification |
| `src/modules/execution/position-close.service.spec.ts` | Modify | Add batch close tests |
| `src/dashboard/position-management.controller.ts` | Modify | Add `POST close-all` endpoint |
| `src/dashboard/position-management.controller.spec.ts` | Modify | Add close-all test |
| `src/dashboard/dto/close-all-positions.dto.ts` | **Create** | `CloseAllPositionsDto` |
| `src/dashboard/dto/ws-events.dto.ts` | Modify | Add `BATCH_COMPLETE`, payload type |
| `src/dashboard/dashboard-event-mapper.service.ts` | Modify | Add `mapBatchComplete()` |
| `src/dashboard/dashboard-event-mapper.service.spec.ts` | Modify | Add batch.complete test |
| `src/dashboard/dashboard.gateway.ts` | Modify | Add `@OnEvent(BATCH_COMPLETE)` handler |

**Dashboard (pm-arbitrage-dashboard/):**

| File | Action | Notes |
|------|--------|-------|
| `src/api/generated/Api.ts` | Regenerate | After engine Swagger updates |
| `src/hooks/useDashboard.ts` | Modify | Fix `useClosePosition()`, add `useCloseAllPositions()` |
| `src/components/PositionsTable.tsx` | Modify | Close button visibility: OPEN + EXIT_PARTIAL |
| `src/components/ClosePositionDialog.tsx` | Modify | Add projected close P&L display, failure toast with detail page link |
| `src/components/CloseAllDialog.tsx` | **Create** | Close All confirmation dialog with typed phrase |
| `src/pages/PositionsPage.tsx` | Modify | Add Close All button |

### Testing Strategy

**Framework:** Vitest with `vi.fn()` mocks. Co-located spec files. Follow existing patterns from `position-close.service.spec.ts`.
[Source: CLAUDE.md#Testing]

**Baseline:** 83 test files, 1499 tests (all green, verified before story creation).

**Required new test cases (from DoD Gates):**

| Test | AC | Location |
|------|----|----------|
| Close-all async batch execution — 3 positions, all succeed | #3 | `position-close.service.spec.ts` |
| Close-all with mixed success/failure/rate-limited results | #3 | `position-close.service.spec.ts` |
| Close-all with no closeable positions (empty result + batch.complete) | #5 | `position-close.service.spec.ts` |
| Per-position execution lock during batch (no deadlock) | #3 | `position-close.service.spec.ts` |
| Rate limit error classified as RATE_LIMITED errorCode | #3 | `position-close.service.spec.ts` |
| Updated close button calls correct endpoint (response shape) | #1 | Manual verification or integration test |
| Confirmation dialog shows projected P&L (currentPnl) | #1 | Visual verification |
| "CLOSE ALL" typed confirmation validation | #2 | Visual verification |
| `batch.complete` event emission with correct payload | #4 | `batch.events.spec.ts` |
| `batch.complete` event mapping in DashboardEventMapperService | #4 | `dashboard-event-mapper.service.spec.ts` |
| `batch.complete` gateway handler broadcasts to clients | #4 | `dashboard.gateway.spec.ts` |
| POST /api/positions/close-all returns 202 with batchId | #3 | `position-management.controller.spec.ts` |
| Race: exit monitor closes position during batch — batch skips gracefully | #3 | `position-close.service.spec.ts` |
| Frontend: batch.complete WS event triggers summary toast + query invalidation | #4 | Visual verification |

### Dependencies

- **Story 7.5.1** (done): `POST /api/positions/:id/close`, `IPositionCloseService`, `PositionCloseService`, `PositionManagementController`, `ClosePositionDto`
- **Story 7.5.2** (done): Position enrichment with `currentPnl`, position detail page at `/positions/:id`, generated API client with all endpoints
- No new npm packages required — all dependencies already installed
- No Prisma schema changes required
[Source: sprint-status.yaml lines 143-144 (both done)]

### DoD Gates

- All existing 1499 tests pass (`pnpm test`), `pnpm lint` reports zero errors
- New test cases cover all items in the testing strategy table above
- No `decimal.js` violations introduced — all financial math uses Decimal methods (batch P&L aggregation is server-side via existing `closePosition()`)
- Generated API client regenerated after new endpoint
- Frontend builds without errors (`pnpm build` in dashboard repo)

### Project Structure Notes

- Backend changes span `common/events/`, `common/interfaces/`, `modules/execution/`, and `dashboard/` — consistent with existing module boundaries [Source: CLAUDE.md#Module Dependency Rules]
- `PositionCloseService` orchestrates batch close — it already has all necessary injections (connectors, risk manager, event emitter, repositories, execution lock) [Source: `position-close.service.ts` constructor]
- New `CloseAllDialog.tsx` in `pm-arbitrage-dashboard/src/components/` follows existing component organization [Source: `pm-arbitrage-dashboard/src/components/`]
- No module dependency rule violations — `modules/execution/` already imports from `common/` and `connectors/`

### References

- [Source: epics.md#Epic-7.5, Story-7.5.3] — Full acceptance criteria and implementation notes
- [Source: sprint-change-proposal-2026-03-08.md#Section-4] — Discovery context, story 7.5.3 scope
- [Source: 7-5-1-exit-partial-re-evaluation-dual-platform-close.md] — Prior story deliverables: IPositionCloseService, PositionCloseService, PositionManagementController, execution lock patterns, race condition handling
- [Source: 7-5-2-position-history-details-balance-overview.md] — Prior story deliverables: position enrichment with currentPnl/projectedSlPnl/projectedTpPnl, position detail page, generated API client
- [Source: pm-arbitrage-engine/src/modules/execution/position-close.service.ts] — Existing close service (656 lines): dual-platform close, lock acquisition, residual size, P&L, error handling
- [Source: pm-arbitrage-engine/src/dashboard/position-management.controller.ts] — POST /api/positions/:id/close route, error routing (404/409/422)
- [Source: pm-arbitrage-engine/src/common/interfaces/position-close-service.interface.ts] — IPositionCloseService, PositionCloseResult, POSITION_CLOSE_SERVICE_TOKEN
- [Source: pm-arbitrage-engine/src/dashboard/dashboard-event-mapper.service.ts:25-169] — Event mapping patterns (9 existing mappings)
- [Source: pm-arbitrage-engine/src/dashboard/dashboard.gateway.ts:109-113] — @OnEvent handler + broadcast pattern
- [Source: pm-arbitrage-engine/src/dashboard/dto/ws-events.dto.ts:52-58] — WS_EVENTS constant, WsEventEnvelope interface
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts] — EVENT_NAMES constant (30 event types)
- [Source: pm-arbitrage-engine/src/modules/execution/execution-lock.service.ts:11-23] — Lock acquisition pattern (Promise-based, 30s timeout)
- [Source: pm-arbitrage-engine/src/common/utils/rate-limiter.ts:71-77] — getUtilization() for rate limit budget
- [Source: pm-arbitrage-engine/src/common/errors/platform-api-error.ts] — Rate limit error codes (1003-1005)
- [Source: pm-arbitrage-dashboard/src/hooks/useDashboard.ts:135-146] — useClosePosition() hook (currently calls wrong endpoint)
- [Source: pm-arbitrage-dashboard/src/components/ClosePositionDialog.tsx] — Existing close dialog (114 lines)
- [Source: pm-arbitrage-dashboard/src/components/PositionsTable.tsx:208-224] — Close button visibility and actions column
- [Source: pm-arbitrage-dashboard/src/pages/PositionsPage.tsx] — Page layout for Close All button placement
- [Source: CLAUDE.md#Architecture] — Module boundaries, error handling, API response format
- [Source: CLAUDE.md#Domain Rules] — decimal.js requirement, financial math
- [Source: CLAUDE.md#Testing] — Vitest, co-located spec files

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — no unexpected errors requiring debug investigation.

### Completion Notes List

- **Rate limit codes deviation from story:** Story T3.11 specifies codes 1003-1005, but actual codebase rate limit codes are 1002 (`KALSHI_ERROR_CODES.RATE_LIMIT_EXCEEDED`) and 1009 (`POLYMARKET_ERROR_CODES.RATE_LIMIT`). Used correct codes from codebase.
- **Field name deviation:** Story says `currentPnl` but the DTO exposes `unrealizedPnl` (enrichment service computes `currentPnl` internally, maps to `unrealizedPnl` on the DTO). Frontend uses `unrealizedPnl`.
- **API client manually updated:** Full regeneration via `swagger-typescript-api` requires a running server. Manually added `CloseAllPositionsDto` interface and `positionManagementControllerCloseAll()` method to `Api.ts`.
- **Position query uses `findByStatusWithPair`:** Called twice (live + paper mode) to get all closeable positions regardless of execution mode, matching the pattern established by exit-management.
- **Dashboard Input component:** `@/components/ui/input` did not exist. Created standard shadcn/ui Input component.
- **`useCloseAllPositions` return type:** The `--unwrap-response-data` config means the generated API returns `void` for 202 responses. Simplified `onSuccess` to not attempt batchId extraction from the response.

### Test Results

- **Engine:** 84 test files, 1514 tests passed, 0 lint errors
- **Dashboard:** `pnpm build` clean (0 TS errors)
- **New tests added:** 12 tests across 5 files (batch.events.spec.ts: 3, position-close.service.spec.ts: 6, position-management.controller.spec.ts: 2, dashboard-event-mapper.service.spec.ts: 2 (in existing file, extended), dashboard.gateway.spec.ts: 1 (in existing file, extended))

### File List

**Engine — New files:**
- `src/common/events/batch.events.ts` — BatchCompleteEvent class
- `src/common/events/batch.events.spec.ts` — Unit tests for BatchCompleteEvent
- `src/dashboard/dto/close-all-positions.dto.ts` — CloseAllPositionsDto with validation

**Engine — Modified files:**
- `src/common/interfaces/position-close-service.interface.ts` — Added RATE_LIMITED, BatchPositionResult, closeAllPositions()
- `src/common/interfaces/index.ts` — Added BatchPositionResult export
- `src/common/events/event-catalog.ts` — Added BATCH_COMPLETE event name
- `src/common/events/index.ts` — Added batch.events barrel export
- `src/modules/execution/position-close.service.ts` — Added closeAllPositions(), processCloseAllBatch(), isRateLimitError(), rate limit classification in closePosition()
- `src/modules/execution/position-close.service.spec.ts` — Added batch close and rate limit tests
- `src/dashboard/position-management.controller.ts` — Added POST close-all endpoint (202 Accepted)
- `src/dashboard/position-management.controller.spec.ts` — Added close-all controller tests
- `src/dashboard/dto/ws-events.dto.ts` — Added BATCH_COMPLETE, WsBatchCompletePayload
- `src/dashboard/dashboard-event-mapper.service.ts` — Added mapBatchComplete()
- `src/dashboard/dashboard-event-mapper.service.spec.ts` — Added batch.complete mapping test
- `src/dashboard/dashboard.gateway.ts` — Added @OnEvent(BATCH_COMPLETE) handler
- `src/dashboard/dashboard.gateway.spec.ts` — Added batch.complete gateway test

**Dashboard — New files:**
- `src/components/CloseAllDialog.tsx` — Close All confirmation dialog with typed phrase
- `src/components/ui/input.tsx` — shadcn/ui Input component

**Dashboard — Modified files:**
- `src/hooks/useDashboard.ts` — Fixed useClosePosition() endpoint, added useCloseAllPositions()
- `src/components/PositionsTable.tsx` — Close button visibility: OPEN + EXIT_PARTIAL
- `src/components/ClosePositionDialog.tsx` — Added projected P&L display, single-leg exposure toast with detail link
- `src/pages/PositionsPage.tsx` — Added Close All button + CloseAllDialog
- `src/types/ws-events.ts` — Added BATCH_COMPLETE, WsBatchCompletePayload
- `src/providers/WebSocketProvider.tsx` — Added batch.complete WS handler with summary toast
- `src/api/generated/Api.ts` — Added CloseAllPositionsDto, positionManagementControllerCloseAll()
