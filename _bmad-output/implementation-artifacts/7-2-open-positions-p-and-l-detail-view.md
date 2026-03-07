# Story 7.2: Open Positions & P&L Detail View

Status: done

## Story

As an operator,
I want to see all open positions with current edge, P&L, and exit proximity,
so that I can quickly assess portfolio state and identify positions needing attention.

## Acceptance Criteria

### AC1 — Position Display

- **Given** the operator navigates to the positions view
- **When** positions load
- **Then** each position shows:
  - Contract pair names (Kalshi + Polymarket descriptions)
  - Entry prices per platform
  - Current prices per platform (live from order books)
  - Initial edge (at entry)
  - Current edge (recalculated with live prices and fees)
  - Unrealized P&L in USD
  - Time to resolution (if resolution date known)
  - Exit threshold proximity: `% to take-profit`, `% to stop-loss`
  - Paper/Live badge
  - Position status

### AC2 — Real-Time Updates

- **Given** a position's status changes (filled, exit triggered, single-leg exposed)
- **When** the WebSocket pushes `position.update` event
- **Then** the positions view updates in real-time without page refresh (<2 seconds, NFR-P4)

### AC3 — Manual Position Closure

- **Given** the operator wants to manually close a position
- **When** they click a close button on a position row
- **Then** a confirmation dialog shows estimated P&L and asks for rationale (text input, max 500 chars)
- **And** on confirmation, `POST /api/positions/:id/close-leg` is called with `{ rationale: string }` (reusing Epic 5 endpoint)
- **And** toast notification confirms success/failure
- **And** the position row updates in real-time via WebSocket `position.update`

## Tasks / Subtasks

### Backend Tasks

- [x] **Task 1: Enhance `GET /dashboard/positions` with live P&L data** (AC: #1, #2)
  - [x] 1.1 Create `IPriceFeedService` interface in `src/common/interfaces/price-feed-service.interface.ts`:
    - Method: `getCurrentClosePrice(platform: string, contractId: string, side: 'buy' | 'sell'): Promise<Decimal | null>`
    - Method: `getTakerFeeRate(platform: string, price: Decimal): Decimal`
    - This preserves module boundaries — Dashboard never imports connectors directly
  - [x] 1.2 Create `PriceFeedService` implementation in `src/modules/data-ingestion/price-feed.service.ts`:
    - Implements `IPriceFeedService`
    - Injects platform connectors
    - For close price: buy side → best **bid** (selling to close); sell side → best **ask** (buying to close)
    - For fees: Kalshi uses `takerFeeForPrice` callback; Polymarket uses flat config rate
    - Register in `DataIngestionModule` and export
  - [x] 1.3 Create `PositionEnrichmentService` in `src/dashboard/` that:
    - Injects `IPriceFeedService` (via interface token, NOT connector imports)
    - Accepts an `OpenPosition` (with pair + orders)
    - Computes per-leg P&L, total P&L, current edge, exit proximity using same formulas as `ThresholdEvaluatorService`
    - Returns typed result: `{ status: 'enriched' | 'partial' | 'failed'; data: EnrichedPosition; errors?: string[] }`
    - `partial` = some prices unavailable (one connector down); `failed` = both connectors down
  - [x] 1.4 Update `DashboardService.getPositions()` to:
    - Use `findByStatusWithOrders()` (includes pair + kalshiOrder + polymarketOrder) instead of just `include: { pair: true }`
    - Call `PositionEnrichmentService` for each position
    - Populate `currentPrices`, `currentEdge`, `unrealizedPnl`, `exitProximity` fields (currently all `null`)
    - Handle enrichment failures gracefully: `partial` → populate available fields, null for missing; `failed` → all null, log warning
  - [x] 1.5 Add `resolutionDate` and `timeToResolution` fields to `PositionSummaryDto`:
    - `resolutionDate`: ISO 8601 string | null — sourced from `ContractMatch.resolutionDate` (accessed via `pos.pair.resolutionDate`)
    - `timeToResolution`: string | null — human-readable duration (e.g., "2d 5h", "< 48h") computed server-side; null if `resolutionDate` unknown
  - [x] 1.6 Add pagination support: accept `page` and `limit` query params (default: page=1, limit=50, max=200). Return `{ data: T[], count: number, page: number, limit: number, timestamp: string }`
  - [x] 1.7 Write co-located unit tests for `PositionEnrichmentService` covering: normal calculation, missing prices (connector down → partial result), zero-size edge case (division-by-zero protection), paper vs live mode, negative P&L with correct exit proximity
  - [x] 1.8 Write co-located unit tests for `PriceFeedService` covering: buy→bid / sell→ask mapping, Kalshi dynamic fee, Polymarket flat fee, connector errors
  - [x] 1.9 Update `DashboardService` tests for enriched positions flow + pagination

- [x] **Task 2: Add individual position detail endpoint** (AC: #1)
  - [x] 2.1 Add `GET /dashboard/positions/:id` to `DashboardController` returning a single enriched `PositionSummaryDto`
  - [x] 2.2 Add Swagger decorators (`@ApiParam`, `@ApiOperation`, `@ApiResponse`)
  - [x] 2.3 Write controller test

- [x] **Task 3: WebSocket position events — lightweight push, frontend enriches** (AC: #2)
  - [x] 3.1 Keep `WsPositionUpdatePayload` lightweight: `{ positionId, status, timestamp }` — do NOT enrich with P&L in the event mapper (price fetching would block the async fan-out path and violate NFR-P4)
  - [x] 3.2 `DashboardEventMapperService` maps `ExitTriggeredEvent` → `position.update` with basic fields only (id + new status). No connector calls in event handlers.
  - [x] 3.3 Frontend handles enrichment: on receiving `position.update`, invalidate `['dashboard', 'positions']` to trigger a fresh `GET /dashboard/positions` which performs server-side enrichment
  - [x] 3.4 Write mapper tests confirming lightweight payloads (no price/P&L fields)

### Frontend Tasks

- [x] **Task 4: Create Positions page with data table** (AC: #1)
  - [x] 4.1 Install `@tanstack/react-table` (shadcn data table pattern)
  - [x] 4.2 Create `src/pages/PositionsPage.tsx` — uses `useDashboardPositions()` hook
  - [x] 4.3 Create `src/components/PositionsTable.tsx` — TanStack Table with shadcn `<Table>` components
    - Columns: Pair Name, Platforms, Entry Prices, Current Prices, Initial Edge, Current Edge, Unrealized P&L, Time to Resolution, Exit Proximity, Status, Paper/Live, Actions
    - Color-code P&L: green (positive), red (negative)
    - Color-code exit proximity: yellow (approaching), red (near threshold)
    - Sortable columns (at minimum: P&L, edge, status)
  - [x] 4.4 Create `src/components/ExitProximityIndicator.tsx` — visual bar/progress showing % to stop-loss and % to take-profit
  - [x] 4.5 Add mode filter toggle (Live / Paper / All) using existing query param support

- [x] **Task 5: Real-time position updates** (AC: #2)
  - [x] 5.1 Update `WebSocketProvider` `position.update` handler: use `invalidateQueries(['dashboard', 'positions'])` exclusively (NOT `setQueryData`) — the REST endpoint performs server-side enrichment so a refetch gives complete data. This avoids race conditions between partial WS payloads and full REST responses.
  - [x] 5.2 Also invalidate `['dashboard', 'overview']` on position updates (open count / P&L may change)
  - [x] 5.3 Add `staleTime: 5_000` to position queries — prevents duplicate refetches if multiple WS events arrive within 5 seconds

- [x] **Task 6: Manual position closure dialog** (AC: #3)
  - [x] 6.1 Create `src/components/ClosePositionDialog.tsx` — shadcn `<AlertDialog>` or `<Dialog>` with:
    - Position summary (pair name, current P&L)
    - Rationale text area (max 500 chars)
    - Confirm / Cancel buttons
  - [x] 6.2 Create `useClosePosition` mutation hook using TanStack Query `useMutation`:
    - Calls `api.singleLegResolutionControllerCloseLeg(id, { rationale })`
    - On success: invalidate `['dashboard', 'positions']` + `['dashboard', 'overview']` + show success toast with position ID and final status
    - On error: show specific error toasts:
      - 409 → "Position is not in a closeable state (current status: X)"
      - 422 → "Cannot determine close price — order book may be empty"
      - Network error → "Connection failed — check if engine is running"
    - Disable close button while mutation is `isPending` (prevents double-submit)
  - [x] 6.3 Add close button to each position row (only for positions with status `OPEN` or `SINGLE_LEG_EXPOSED`)
  - [x] 6.4 Add shadcn toast component: `npx shadcn@latest add toast` (uses `@radix-ui/react-toast` already in lockfile). Add `<Toaster />` to App.tsx. Use `useToast()` hook for notifications.

- [x] **Task 7: Navigation and routing** (AC: #1)
  - [x] 7.1 Install `react-router-dom` (not yet installed — confirmed missing from dashboard)
  - [x] 7.2 Add `/positions` route to app router
  - [x] 7.3 Add navigation link from dashboard overview to positions page (the open positions count card should link to `/positions`)

- [x] **Task 8: Regenerate API client** (AC: all)
  - [x] 8.1 Run `pnpm generate-api` in dashboard to pick up new/updated endpoints and DTOs
  - [x] 8.2 Verify generated types include enriched `PositionSummaryDto` fields and new position detail endpoint

## Dev Notes

### Critical Architecture Rules

- **Financial Math:** ALL P&L calculations MUST use `decimal.js` (`Decimal`). NEVER native JS operators. Use `.mul()`, `.plus()`, `.minus()`, `.div()`.
- **Prisma Decimal:** Convert via `new Decimal(value.toString())` — Prisma.Decimal ≠ decimal.js Decimal.
- **DTO Decimal Fields:** Serialize as `string` in JSON (never `number`). Frontend receives strings.
- **Error Hierarchy:** All new errors extend `SystemError`. Never throw raw `Error`.
- **Module Boundaries:** Dashboard module reads data via `PrismaService` + `IPriceFeedService` (from `common/interfaces/`). NEVER import connector services or module services directly.
- **Fan-out:** Dashboard event handlers are async subscribers. NEVER block the hot path (detection → risk → execution). NEVER fetch prices inside event handlers.
- **DTO Consistency:** `exitProximity` in `PositionSummaryDto` is currently typed `number | null`. Change it to an object: `{ stopLoss: string; takeProfit: string } | null` — both as decimal strings (0-1 range). This follows the "DTO Decimal Fields as strings" rule and gives the frontend both proximity values.

### P&L Calculation — MUST Match ThresholdEvaluatorService

The `PositionEnrichmentService` MUST use the **exact same formulas** as `ThresholdEvaluatorService.evaluate()`:

```typescript
// === CLOSE PRICE SELECTION ===
// The "current price" is the price at which the leg COULD BE CLOSED right now:
//   Buy side → close by selling → use best BID from order book
//   Sell side → close by buying → use best ASK from order book
// IPriceFeedService.getCurrentClosePrice() encapsulates this logic.

// === PER-LEG P&L ===
// Buy side: profit when price goes up; sell side: profit when price goes down
legPnl = side === 'buy' ? closePrice.minus(entryPrice).mul(size) : entryPrice.minus(closePrice).mul(size);

// === EXIT FEES (taker fee at current close price) ===
exitFee = closePrice.mul(size).mul(feeDecimal);

// === TOTALS ===
currentPnl = kalshiPnl.plus(polymarketPnl).minus(totalExitFees);
minLegSize = Decimal.min(kalshiSize, polymarketSize);
currentEdge = currentPnl.div(minLegSize.isZero() ? new Decimal(1) : minLegSize);
scaledInitialEdge = initialEdge.mul(minLegSize);
capturedEdgePercent = scaledInitialEdge.isZero() ? new Decimal(0) : currentPnl.div(scaledInitialEdge).mul(100);

// === EXIT PROXIMITY (0→1 range, 1 = at threshold) ===
// Stop-loss: threshold is NEGATIVE (e.g., -0.024), currentPnl approaches it from above
// Use abs() to get a 0→1 proximity that increases as loss deepens
stopLossThreshold = scaledInitialEdge.mul(-2); // negative number
takeProfitThreshold = scaledInitialEdge.mul(new Decimal('0.80')); // positive number

// Clamp to [0, 1] — values >1 mean threshold already breached
stopLossProximity = Decimal.min(new Decimal(1), Decimal.max(new Decimal(0), currentPnl.div(stopLossThreshold).abs()));
takeProfitProximity = Decimal.min(new Decimal(1), Decimal.max(new Decimal(0), currentPnl.div(takeProfitThreshold)));
```

ALL of these computations use `Decimal` — never native operators.

### Existing Endpoint Reuse

**`POST /api/positions/:id/close-leg`** already exists at:

- `src/modules/execution/single-leg-resolution.controller.ts` → `closeLeg()` method
- Route: `POST /positions/:id/close-leg` (under `/api` prefix)
- Body: `CloseLegDto { rationale?: string }` (max 500 chars)
- Response: `CloseLegResponseDto { data: { positionId, status, closedLeg, closePrice }, timestamp }`
- Auth: `AuthTokenGuard` (Bearer token)
- Errors: 409 (invalid position state), 422 (cannot determine close price)

**Do NOT create a new endpoint.** The generated API client already has `singleLegResolutionControllerCloseLeg()`.

### Current Dashboard Service Gap

`DashboardService.getPositions()` currently returns `null` for:

- `currentPrices` — needs live order book fetch from connectors
- `currentEdge` — needs recalculation with current prices
- `unrealizedPnl` — needs P&L calculation
- `exitProximity` — needs threshold distance calculation

The query also only includes `pair` relation — needs `kalshiOrder` and `polymarketOrder` to extract entry prices, sides, and sizes from Order records (not just `entryPrices` JSON).

### Order Model Reference

The `Order` model contains:

- `side` ('buy' | 'sell')
- `price` (Decimal — fill price)
- `filledSize` (Decimal — actual filled contracts)
- `platform` ('kalshi' | 'polymarket')
- `status` (OrderStatus enum)

---

## Dev Agent Record

**Completed:** 2026-03-04

### Implementation Summary

**Backend (Tasks 1-3):**

- Created `IPriceFeedService` interface + `PriceFeedService` implementation with buy→bid/sell→ask close price mapping and platform-specific fee rates
- Created `PositionEnrichmentService` with P&L, current edge, exit proximity calculations matching `ThresholdEvaluatorService` formulas
- Updated `DashboardService` to enrich positions with live data, handle partial/failed enrichment gracefully
- Added `resolutionDate` and `timeToResolution` to `PositionSummaryDto`; extracted nested DTOs (`PlatformPairDto`, `EntryPricesDto`, `CurrentPricesDto`, `ExitProximityDto`) for proper Swagger schema generation
- Added `GET /dashboard/positions/:id` endpoint with `PositionDetailResponseDto`
- Pagination support (page/limit query params, clamped to max 200)
- WebSocket `position.update` kept lightweight (no price fetching in event handlers)
- 1296+ tests passing (1 pre-existing kalshi-price.util failure unrelated)

**Frontend (Tasks 4-8):**

- `PositionsPage` with mode filter (All/Live/Paper)
- `PositionsTable` using TanStack React Table with sortable columns, color-coded P&L, status badges
- `ExitProximityIndicator` with visual progress bars (green/yellow/red thresholds)
- `ClosePositionDialog` with rationale textarea, P&L display, error-specific toasts (409/422/network)
- `useClosePosition` mutation hook with query invalidation
- react-router-dom routing (`/` and `/positions`)
- sonner toast notifications (shadcn)
- `staleTime: 5_000` prevents duplicate WS-triggered refetches
- Regenerated `Api.ts` from engine Swagger — all DTO types correctly typed

Entry prices for P&L are taken from `Order.price` (fill price), NOT from `OpenPosition.entryPrices` JSON (which stores the same data redundantly). Prefer the Order record as single source of truth.

### WebSocket Event Flow

```
Position status change → Domain event (e.g., ExitTriggeredEvent)
  → EventEmitter2 (async fan-out — NEVER blocks hot path)
  → DashboardEventMapperService.mapExitTriggeredEvent()
  → DashboardGateway.broadcast('position.update', { positionId, status, timestamp })
  → Frontend WebSocketProvider.onMessage()
  → queryClient.invalidateQueries(['dashboard', 'positions'])
  → React Query refetches GET /dashboard/positions (with server-side P&L enrichment)
  → PositionsTable re-renders with fresh data
```

**Design rationale:** WS events carry only lightweight status changes (no price fetching in event handlers). The REST endpoint handles enrichment, ensuring P&L is always computed server-side with fresh order book data. This avoids blocking the async fan-out path and prevents stale P&L in WS payloads.

### Frontend Patterns (from Story 7.1)

- **API Client:** `src/api/client.ts` exports `api` (axios instance with auth). Generated client at `src/api/generated/Api.ts`.
- **Hooks:** `src/hooks/useDashboard.ts` — add new hooks here.
- **Query Keys:** `['dashboard', 'positions', mode]` — already established.
- **WebSocket Cache Updates:** `WebSocketProvider` already handles `position.update` → `invalidateQueries(['dashboard', 'positions'])`. Keep this pattern (server-side enrichment on refetch). Add `staleTime: 5_000` to prevent rapid duplicate refetches.
- **UI Components:** Use shadcn/ui `<Table>`, `<Badge>`, `<Button>`, `<Dialog>`, `<AlertDialog>`, `<Tooltip>`. All already installed except `@tanstack/react-table`.
- **Env Config:** `src/lib/env.ts` provides `API_URL`, `WS_URL`, `OPERATOR_TOKEN`.
- **Styling:** Tailwind CSS 4 via `@tailwindcss/vite`. Use `cn()` utility from `src/lib/utils.ts`.

### Price & Fee Access — IPriceFeedService Interface

`PositionEnrichmentService` MUST NOT import connectors directly. Instead, it uses `IPriceFeedService` (new interface in `common/interfaces/`):

```typescript
// common/interfaces/price-feed-service.interface.ts
export interface IPriceFeedService {
  // Returns the close price for a position leg:
  //   buy side → best BID (selling to close)
  //   sell side → best ASK (buying to close)
  // Returns null if order book unavailable or empty
  getCurrentClosePrice(platform: string, contractId: string, side: 'buy' | 'sell'): Promise<Decimal | null>;

  // Returns the taker fee rate as a decimal (e.g., 0.02 = 2%)
  // Kalshi: dynamic based on fee schedule tier + price
  // Polymarket: flat rate from config
  getTakerFeeRate(platform: string, price: Decimal): Decimal;
}
```

**Implementation** lives in `src/modules/data-ingestion/price-feed.service.ts` — this module already imports connectors. Register the provider with `IPriceFeedService` injection token and export from `DataIngestionModule`. Dashboard module imports `DataIngestionModule` to get the interface binding.

This mirrors how `ExitMonitorService` accesses connector data — same source of truth for prices and fees.

### Project Structure Notes

**New backend files:**

- `src/common/interfaces/price-feed-service.interface.ts` — IPriceFeedService interface
- `src/modules/data-ingestion/price-feed.service.ts` — IPriceFeedService implementation (wraps connectors)
- `src/modules/data-ingestion/price-feed.service.spec.ts` — co-located test
- `src/dashboard/position-enrichment.service.ts` — P&L enrichment logic
- `src/dashboard/position-enrichment.service.spec.ts` — co-located test

**Modified backend files:**

- `src/modules/data-ingestion/data-ingestion.module.ts` — register + export PriceFeedService
- `src/dashboard/dashboard.module.ts` — import DataIngestionModule, register PositionEnrichmentService
- `src/dashboard/dashboard.service.ts` — inject PositionEnrichmentService, update getPositions() + add pagination
- `src/dashboard/dashboard.service.spec.ts` — update tests
- `src/dashboard/dashboard.controller.ts` — add GET /positions/:id + pagination params
- `src/dashboard/dashboard.controller.spec.ts` — update tests
- `src/dashboard/dto/position-summary.dto.ts` — add resolutionDate, timeToResolution, change exitProximity type to `{ stopLoss: string; takeProfit: string } | null`
- `src/dashboard/dto/ws-events.dto.ts` — keep WsPositionUpdatePayload lightweight (id + status only)
- `src/dashboard/dashboard-event-mapper.service.ts` — lightweight position event mapping (no enrichment)
- `src/dashboard/dashboard-event-mapper.service.spec.ts` — update tests

**New frontend files:**

- `src/pages/PositionsPage.tsx`
- `src/components/PositionsTable.tsx`
- `src/components/ExitProximityIndicator.tsx`
- `src/components/ClosePositionDialog.tsx`

**Modified frontend files:**

- `src/hooks/useDashboard.ts` — add `useClosePosition` mutation, add `staleTime` to position queries
- `src/providers/WebSocketProvider.tsx` — ensure `position.update` uses `invalidateQueries` (already does, verify no `setQueryData` conflict)
- `src/App.tsx` — add route
- `src/pages/DashboardPage.tsx` — link to positions page
- `src/api/generated/Api.ts` — regenerated

### References

- [Source: pm-arbitrage-engine/src/dashboard/dashboard.service.ts#getPositions] — current implementation returning null P&L fields
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts#evaluate] — canonical P&L formulas
- [Source: pm-arbitrage-engine/src/modules/execution/single-leg-resolution.controller.ts#closeLeg] — existing close-leg endpoint
- [Source: pm-arbitrage-engine/src/modules/execution/close-leg.dto.ts] — CloseLegDto with optional rationale
- [Source: pm-arbitrage-engine/src/dashboard/dto/position-summary.dto.ts] — current PositionSummaryDto
- [Source: pm-arbitrage-engine/src/dashboard/dto/ws-events.dto.ts] — WebSocket event payloads
- [Source: pm-arbitrage-engine/src/persistence/repositories/position.repository.ts] — position queries (findByStatusWithOrders)
- [Source: pm-arbitrage-engine/prisma/schema.prisma#OpenPosition] — Prisma model
- [Source: pm-arbitrage-dashboard/src/hooks/useDashboard.ts] — existing query hooks
- [Source: pm-arbitrage-dashboard/src/providers/WebSocketProvider.tsx] — WebSocket cache management
- [Source: _bmad-output/planning-artifacts/architecture.md] — dashboard architecture, API patterns, response format
- [Source: _bmad-output/planning-artifacts/epics.md#Epic7] — acceptance criteria, story requirements

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

**New backend files:**
- `src/common/interfaces/price-feed-service.interface.ts` — IPriceFeedService interface + token
- `src/modules/data-ingestion/price-feed.service.ts` — IPriceFeedService implementation (wraps connectors)
- `src/modules/data-ingestion/price-feed.service.spec.ts` — co-located test (8 tests)
- `src/dashboard/position-enrichment.service.ts` — P&L enrichment logic
- `src/dashboard/position-enrichment.service.spec.ts` — co-located test (9 tests)

**Modified backend files:**
- `src/common/interfaces/index.ts` — export IPriceFeedService + token
- `src/common/errors/system-health-error.ts` — added NOT_FOUND error code (4007)
- `src/modules/data-ingestion/data-ingestion.module.ts` — register + export PriceFeedService via token
- `src/dashboard/dashboard.module.ts` — import DataIngestionModule, register PositionEnrichmentService
- `src/dashboard/dashboard.service.ts` — inject PositionEnrichmentService, batched enrichment, pagination
- `src/dashboard/dashboard.service.spec.ts` — updated tests for enrichment + pagination
- `src/dashboard/dashboard.controller.ts` — GET /positions/:id, pagination params, clamped values, SystemHealthError
- `src/dashboard/dashboard.controller.spec.ts` — updated tests (SystemHealthError, position detail)
- `src/dashboard/dto/position-summary.dto.ts` — nested DTOs (PlatformPairDto, EntryPricesDto, CurrentPricesDto, ExitProximityDto), resolutionDate, timeToResolution
- `src/dashboard/dto/response-wrappers.dto.ts` — PositionDetailResponseDto, PositionListResponseDto (page/limit)
- `src/dashboard/dto/ws-events.dto.ts` — WsPositionUpdatePayload (lightweight)
- `src/dashboard/dashboard-event-mapper.service.ts` — mapPositionUpdate (lightweight)
- `src/dashboard/dashboard-event-mapper.service.spec.ts` — added beforeEach import, position update tests

**New frontend files (pm-arbitrage-dashboard/):**
- `src/pages/PositionsPage.tsx` — positions view with mode filter
- `src/components/PositionsTable.tsx` — TanStack React Table with sortable columns
- `src/components/ExitProximityIndicator.tsx` — visual SL/TP progress bars
- `src/components/ClosePositionDialog.tsx` — close dialog with rationale + error toasts
- `src/components/ui/button.tsx` — shadcn button component
- `src/components/ui/dialog.tsx` — shadcn dialog component
- `src/components/ui/sonner.tsx` — sonner toast wrapper
- `src/components/ui/table.tsx` — shadcn table component
- `src/components/ui/textarea.tsx` — shadcn textarea component

**Modified frontend files (pm-arbitrage-dashboard/):**
- `package.json` + `pnpm-lock.yaml` — added @tanstack/react-table, react-router-dom, sonner
- `src/App.tsx` — BrowserRouter, routes, Toaster
- `src/api/generated/Api.ts` — regenerated from engine Swagger
- `src/hooks/useDashboard.ts` — useClosePosition mutation, staleTime: 5_000
- `src/pages/DashboardPage.tsx` — link to /positions from open positions card
- `src/types/ws-events.ts` — WsPositionUpdatePayload type sync
