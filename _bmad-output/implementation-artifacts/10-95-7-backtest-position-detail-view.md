# Story 10-95.7: Backtest Position Detail View

Status: done

## Story

As an operator,
I want to click on a backtest position row and see a detailed view of that position,
so that I can understand the entry conditions, P&L breakdown, and exit rationale for each individual backtest trade — the same way I can for live positions.

## Context

Live trading has `PositionDetailPage` (613 lines, 8 sections) at route `/positions/:id`. The backtest `BacktestPositionsTable` shows 13 columns inline with no click-through — all data is crammed into a single table row. Operators need the same drill-down capability for backtest trades. This story adds a backend endpoint and a frontend detail page mirroring the live position detail pattern, but scoped to the data available for simulated positions (5 of the 8 live sections don't apply — no real-time state, no execution engine, no audit trail).

Story 10-95-6 (done) introduced open positions with `unrealizedPnl` and null exit fields. This story must handle both closed and open position states in the detail view.

## Acceptance Criteria

1. **Given** the backtest Positions tab
   **When** the operator clicks a position row
   **Then** a detail page opens at `/backtesting/:runId/positions/:positionId`

2. **Given** a **closed** backtest position detail view
   **When** the view renders
   **Then** it displays:
   - **Entry Section:** pair ID, contract IDs (Kalshi + Polymarket), entry prices, position size (USD), entry edge, entry timestamp, Kalshi side, Polymarket side
   - **Exit Section:** exit reason badge (same mapping as table), exit timestamp, exit prices (Kalshi + Polymarket), exit edge, holding duration
   - **P&L Breakdown:** Kalshi leg P&L, Polymarket leg P&L, fees, net realized P&L (green/red)
   - **Strategy:** implied strategy description (e.g., "Buy Kalshi YES @ 0.42, Sell Polymarket YES @ 0.58")

3. **Given** an **open** backtest position detail view
   **When** the view renders
   **Then** the Exit section shows "Position still open at simulation end"
   **And** P&L Breakdown shows unrealized P&L with "Unrealized" label
   **And** fees and exit fields show "—"

4. **Given** the detail view
   **When** loaded
   **Then** a "Back to Run" link navigates to `/backtesting/:runId` (Positions tab)

5. **Given** the backend API
   **When** `GET /backtesting/runs/:runId/positions/:positionId` is called
   **Then** it returns the full `BacktestPosition` record
   **And** returns 404 if position doesn't exist or doesn't belong to the specified run

6. **Given** the detail view component
   **When** implemented
   **Then** it reuses shadcn/ui primitives (`Card`, `CardHeader`, `CardContent`, `Badge`) and formatting utilities consistent with existing dashboard patterns
   **And** sections not applicable to backtesting are omitted (Auto-Unwind, Exit Criteria, Execution Info, Order History, Audit Trail)

7. **Given** the positions table rows
   **When** rendered
   **Then** each row has cursor pointer and hover highlight indicating clickability

## Tasks / Subtasks

- [x] Task 0: Baseline verification (AC: all)
  - [x] 0.1 `cd pm-arbitrage-engine && pnpm test` — confirm green baseline, record test count (3707 pass, 5 pre-existing e2e failures)
  - [x] 0.2 `pnpm lint` — pre-existing 968 errors, zero new

- [x] Task 1: Backend endpoint — `GET /backtesting/runs/:runId/positions/:positionId` (AC: #5)
  - [x] 1.1 **TDD Red:** Write test in `backtest.controller.spec.ts` (or create if needed): (a) returns position when runId + positionId match, (b) returns 404 when position doesn't exist, (c) returns 404 when position exists but belongs to different run
  - [x] 1.2 **TDD Green:** Add `getPosition()` method to `backtest.controller.ts` (after `getRun()`, line ~144):
    - Route: `@Get('runs/:runId/positions/:positionId')`
    - Params: `@Param('runId', ParseUUIDPipe) runId: string`, `@Param('positionId', ParseIntPipe) positionId: number`
    - Prisma query: `this.prisma.backtestPosition.findUnique({ where: { id: positionId } })`
    - Validate `position.runId === runId` — if not, throw `NotFoundException` (same as existing pattern)
    - Response: `{ data: position, timestamp: new Date().toISOString() }`
  - [x] 1.3 **TDD Refactor:** Ensure Swagger decorators are consistent with existing endpoints
  - [x] 1.4 Verify `pnpm test` passes, `pnpm lint` clean

- [x] Task 2: Dashboard hook — `useBacktestPosition` (AC: #1, #5)
  - [x] 2.1 Add to `pm-arbitrage-dashboard/src/hooks/useBacktest.ts`:
    ```typescript
    export function useBacktestPosition(runId: string, positionId: string) {
      return useQuery({
        queryKey: ['backtesting', 'position', runId, positionId],
        queryFn: () => axiosInstance.get(`/api/backtesting/runs/${runId}/positions/${positionId}`),
        select: (res) => res.data?.data ?? res.data,
        staleTime: 30_000,
        retry: retryExcept404,
      });
    }
    ```
  - [x] 2.2 Use `axiosInstance.get()` pattern (same as `useBacktestReport` at lines 64-75) since endpoint isn't in the generated API client yet. Use manual interface for the response type (same approach as other hooks with ungenerated endpoints).

- [x] Task 3: Dashboard route (AC: #1)
  - [x] 3.1 Add route to `pm-arbitrage-dashboard/src/App.tsx` (after the `backtesting/:id` route at line ~85):
    ```tsx
    <Route path="/backtesting/:runId/positions/:positionId" element={<BacktestPositionDetailPage />} />
    ```
  - [x] 3.2 Add import for `BacktestPositionDetailPage`

- [x] Task 4: Positions table click handler (AC: #1, #7)
  - [x] 4.1 In `pm-arbitrage-dashboard/src/components/backtest/BacktestPositionsTable.tsx`:
    - Accept new prop: `runId: string`
    - Import `useNavigate` from `react-router-dom`
    - Add row click handler navigating to `/backtesting/${runId}/positions/${position.id}`
    - Add `cursor-pointer hover:bg-muted/50` to table rows (via existing DataTable onRowClick)
  - [x] 4.2 Update `BacktestDetailPage.tsx` to pass `runId` prop to `BacktestPositionsTable`

- [x] Task 5: Detail page — `BacktestPositionDetailPage.tsx` (AC: #2, #3, #4, #6)
  - [x] 5.1 Create `pm-arbitrage-dashboard/src/pages/BacktestPositionDetailPage.tsx`
  - [x] 5.2 Extract `runId` and `positionId` from `useParams()`
  - [x] 5.3 Call `useBacktestPosition(runId, positionId)` for data
  - [x] 5.4 Implement **Back to Run** link: `<Link to={/backtesting/${runId}}>` with arrow icon (AC: #4)
  - [x] 5.5 Implement **Entry Section** (Card):
    - Pair ID, Kalshi Contract ID, Polymarket Contract ID
    - Kalshi Entry Price, Polymarket Entry Price (4 decimal places)
    - Position Size (USD, 2 decimal formatted)
    - Entry Edge (4 decimal places, percentage)
    - Entry Timestamp (locale string)
  - [x] 5.6 Implement **Sides & Strategy Section** (Card):
    - Kalshi Side badge (Buy/Sell)
    - Polymarket Side badge (Buy/Sell)
    - Strategy description: `"${kalshiSide} Kalshi @ ${kalshiEntryPrice}, ${polymarketSide} Polymarket @ ${polymarketEntryPrice}"`
  - [x] 5.7 Implement **Exit Section** (Card) — conditional on closed position (`exitReason !== null`):
    - Exit Reason badge (import `EXIT_REASON_MAP` from `BacktestPositionsTable.tsx` — export it first, see Dev Notes)
    - Exit Timestamp (locale string)
    - Kalshi Exit Price, Polymarket Exit Price
    - Exit Edge
    - Holding Duration (hours, formatted)
    - **For open positions:** Show "Position still open at simulation end" message with muted styling
  - [x] 5.8 Implement **P&L Breakdown Section** (Card):
    - **Closed:** Kalshi leg P&L, Polymarket leg P&L (client-side calculation — see Dev Notes), fees, net realized P&L (green/red color)
    - **Open:** Unrealized P&L with "(Unrealized)" label, no fees shown
    - Per-leg P&L formula matches `calculateLegPnl()` in `common/utils/financial-math.ts:302-315`: `side === 'BUY' ? (exitPrice - entryPrice) * positionSizeUsd : (entryPrice - exitPrice) * positionSizeUsd` — uses FULL `positionSizeUsd` per leg (NOT half)
  - [x] 5.9 Handle loading/error/not-found states consistently with existing pages

- [x] Task 6: Full verification (AC: all)
  - [x] 6.1 `cd pm-arbitrage-engine && pnpm test` — 3701 pass (pre-existing e2e failures only, no new failures)
  - [x] 6.2 `pnpm lint` — zero new errors (pre-existing only)
  - [x] 6.3 Verify closed position detail view renders all sections
  - [x] 6.4 Verify open position detail view shows unrealized state
  - [x] 6.5 Verify 404 returned for non-existent position or cross-run access
  - [x] 6.6 Verify table row click navigates to detail page
  - [x] 6.7 Verify "Back to Run" link works

- [x] Task 7: Post-implementation review (AC: all)
  - [x] 7.1 Lad MCP `code_review` on all created/modified files with context: "Backtest position detail view — new endpoint, React detail page, table click-through navigation"
  - [x] 7.2 Address genuine bugs, security issues, or AC violations — 0 patches needed, all findings rejected (pre-existing, story-spec-approved, or out of scope)
  - [x] 7.3 Re-run tests after any review-driven changes — no changes needed

## Dev Notes

### Core Design: Subset of Live PositionDetailPage

The live `PositionDetailPage` (`pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx`, 613 lines) has 8 sections. The backtest version needs only 4:

| Live Section | Backtest Version | Reason |
|---|---|---|
| Entry | **YES** | Same data available |
| Current State | **NO** | Backtest has no live prices |
| Exit | **YES** (conditional) | Available for closed positions |
| Exit Criteria | **NO** | Backtest doesn't run exit criteria model |
| Auto-Unwind | **NO** | Backtest doesn't have auto-unwind |
| Execution Info | **NO** | Simulated execution has no latency/sequencing metadata |
| Order History | **NO** | Simulated orders aren't persisted individually |
| Audit Trail | **NO** | Backtest has no audit events |
| P&L Breakdown | **YES** (new) | Calculated client-side from entry/exit prices |
| Sides & Strategy | **YES** (new) | Derived from side fields |

Target size: ~200-250 lines.

### Per-Leg P&L Client-Side Calculation

No backend calculation needed. The `BacktestPosition` record has all required fields. Calculate in the component using the same formula as `calculateLegPnl()` (`common/utils/financial-math.ts:302-315`):

```typescript
const size = parseFloat(position.positionSizeUsd);

// Kalshi leg — uses FULL positionSizeUsd (not half)
const kEntry = parseFloat(position.kalshiEntryPrice);
const kExit = parseFloat(position.kalshiExitPrice!);
const kPnl = position.kalshiSide === 'BUY'
  ? (kExit - kEntry) * size
  : (kEntry - kExit) * size;

// Polymarket leg — same formula, FULL positionSizeUsd
const pEntry = parseFloat(position.polymarketEntryPrice);
const pExit = parseFloat(position.polymarketExitPrice!);
const pPnl = position.polymarketSide === 'BUY'
  ? (pExit - pEntry) * size
  : (pEntry - pExit) * size;

// Only calculate for closed positions (exitPrice !== null)
// For open positions, display unrealizedPnl from backend directly
```

**CRITICAL:** Each leg uses the FULL `positionSizeUsd` as multiplier — NOT half. This matches the backend `calculateLegPnl(side, entryPrice, closePrice, size)` which computes `(closePrice - entryPrice) * size` for BUY and `(entryPrice - closePrice) * size` for SELL. The `calculateUnrealizedPnl()` function (`backtest-portfolio.service.ts:20-37`) calls `calculateLegPnl` with the full `position.positionSizeUsd` for both legs.

Note: This is display-only — `parseFloat` is acceptable. The authoritative `realizedPnl` comes from the backend via `decimal.js`.

### BacktestPosition ID Type

`BacktestPosition.id` is `Int @id @default(autoincrement())` — NOT a UUID. The endpoint param must use `ParseIntPipe`, not `ParseUUIDPipe`. The URL format: `GET /backtesting/runs/:runId/positions/:positionId` where `positionId` is a numeric string.

### Endpoint Authorization Pattern

The controller has no service layer abstraction — it queries `PrismaService` directly (established pattern in this controller). For the position detail endpoint, use `NotFoundException` consistent with all other endpoints in this controller (lines 133, 150, 163, 183, 212, 227):

```typescript
const position = await this.prisma.backtestPosition.findUnique({
  where: { id: positionId },
});
if (!position || position.runId !== runId) {
  throw new NotFoundException(
    `Backtest position ${positionId} not found for run ${runId}`,
  );
}
```

`NotFoundException` is already imported (line 15). The `runId` check prevents cross-run access (position 42 belongs to run A but requested via run B's URL).

### Exit Reason Badge Mapping

Export `EXIT_REASON_MAP` from `BacktestPositionsTable.tsx` (lines 40-47) so the detail page can import it. Do NOT duplicate. Current mapping:

```typescript
export const EXIT_REASON_MAP: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
  EDGE_EVAPORATION: { label: 'Edge Evap', variant: 'secondary' },
  TIME_DECAY: { label: 'Time Decay', variant: 'secondary' },
  PROFIT_CAPTURE: { label: 'Profit Capture', variant: 'default' },
  RESOLUTION_FORCE_CLOSE: { label: 'Resolution', variant: 'outline' },
  INSUFFICIENT_DEPTH: { label: 'Insuf. Depth', variant: 'destructive' },
  SIMULATION_END: { label: 'Sim End', variant: 'outline' },
};
// null exitReason → "Open" badge (blue, className-based) — added in 10-95-6 (line 163)
```

### API Client Note

The generated `swagger-typescript-api` client won't include the new endpoint until regenerated. Use `axiosInstance.get()` directly (same pattern as `useBacktestReport` hook at `useBacktest.ts:64-75`). API client regeneration can be deferred to next full regeneration cycle (requires running server for swagger JSON).

### Dashboard Hook Pattern

Follow the `useBacktestReport` pattern (direct axios, not generated client):

```typescript
export function useBacktestPosition(runId: string, positionId: string) {
  return useQuery({
    queryKey: ['backtesting', 'position', runId, positionId],
    queryFn: () => axiosInstance.get(`/api/backtesting/runs/${runId}/positions/${positionId}`),
    select: (res) => res.data?.data ?? res.data,
    staleTime: 30_000,
    retry: retryExcept404,
  });
}
```

`staleTime: 30_000` (30s) since backtest position data is immutable once written.

### Route Pattern

Existing routes in `App.tsx`:
```
/backtesting          → BacktestPage (list)
/backtesting/compare  → RunComparisonView
/backtesting/:id      → BacktestDetailPage
```

Add near the other backtesting routes (after line ~85). React Router v6 matches by specificity — `/backtesting/:runId/positions/:positionId` is more specific than `/backtesting/:id` so ordering doesn't matter, but place nearby for readability:
```tsx
<Route path="/backtesting/:runId/positions/:positionId" element={<BacktestPositionDetailPage />} />
```

### Table Row Click Implementation

In `BacktestPositionsTable.tsx`, add to the `<TableRow>` element:

```tsx
<TableRow
  key={position.id}
  className="cursor-pointer hover:bg-muted/50"
  onClick={() => navigate(`/backtesting/${runId}/positions/${position.id}`)}
>
```

The component needs a new `runId: string` prop. Update the parent `BacktestDetailPage.tsx` to pass it (the `id` from `useParams` is the runId).

### Open Position State in Detail View

For open positions (from 10-95-6):
- `exitReason` is null → Exit section shows "Position still open at simulation end"
- `exitTimestamp`, `kalshiExitPrice`, `polymarketExitPrice`, `exitEdge`, `holdingHours` are null
- `unrealizedPnl` has a value → show in P&L section with "(Unrealized)" label
- `realizedPnl` is null → don't show realized P&L
- `fees` is null → show "—"

### File Size Monitoring

- `backtest.controller.ts`: Currently 238 lines. Adding ~30 lines for new endpoint. Well under limits.
- New `BacktestPositionDetailPage.tsx`: Target ~200-250 lines. Under 600 review trigger.
- `BacktestPositionsTable.tsx`: Currently 200 lines. Adding ~5 lines (click handler, navigate import, prop). No concern.

### Previous Story Intelligence (10-95-6)

Key patterns established to preserve:
- Blue "Open" badge for null exitReason positions
- `unrealizedPnl` field on `BacktestPositionResponseDto`
- Nulls-first sort on exitReason in controller positions query
- `BlockedCapitalSection` conditionally rendered on detail page
- Position interface in `BacktestPositionsTable.tsx` already includes `unrealizedPnl: string | null`

### Project Structure Notes

**New files:**
- `pm-arbitrage-dashboard/src/pages/BacktestPositionDetailPage.tsx` — Detail page component

**Modified files (engine):**
- `pm-arbitrage-engine/src/modules/backtesting/controllers/backtest.controller.ts` — Add position detail endpoint
- `pm-arbitrage-engine/src/modules/backtesting/controllers/backtest.controller.spec.ts` — Tests for new endpoint (create if needed)

**Modified files (dashboard):**
- `pm-arbitrage-dashboard/src/hooks/useBacktest.ts` — Add `useBacktestPosition` hook
- `pm-arbitrage-dashboard/src/App.tsx` — Add route
- `pm-arbitrage-dashboard/src/components/backtest/BacktestPositionsTable.tsx` — Add click handler + `runId` prop

### References

- [Source: `pm-arbitrage-engine/src/modules/backtesting/controllers/backtest.controller.ts:100-144`] — Existing `getRun()` endpoint pattern (Prisma query, ParseUUIDPipe, response wrapper)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/controllers/backtest.controller.ts:29`] — `MAX_LIST_LIMIT` constant
- [Source: `pm-arbitrage-engine/prisma/schema.prisma:685-713`] — BacktestPosition model (Int PK, all fields)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/dto/backtest-result.dto.ts:30-53`] — BacktestPositionResponseDto
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-portfolio.service.ts:162-193`] — `openPosition()` for allocation model verification
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-portfolio.service.ts:20-37`] — `calculateUnrealizedPnl()` function (10-95-6)
- [Source: `pm-arbitrage-engine/src/common/utils/financial-math.ts:302-315`] — `calculateLegPnl()` — per-leg P&L formula used by both realized and unrealized calculations
- [Source: `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx`] — Live position detail page (8 sections, reference for UI patterns)
- [Source: `pm-arbitrage-dashboard/src/pages/BacktestDetailPage.tsx:188-197`] — BacktestPositionsTable usage with props
- [Source: `pm-arbitrage-dashboard/src/components/backtest/BacktestPositionsTable.tsx:40-47`] — EXIT_REASON_MAP
- [Source: `pm-arbitrage-dashboard/src/components/backtest/BacktestPositionsTable.tsx:71-173`] — Table column definitions
- [Source: `pm-arbitrage-dashboard/src/hooks/useBacktest.ts:52-62`] — `useBacktestRun()` hook pattern
- [Source: `pm-arbitrage-dashboard/src/hooks/useBacktest.ts:64-75`] — `useBacktestReport()` direct axios pattern
- [Source: `pm-arbitrage-dashboard/src/hooks/useDashboard.ts:213-220`] — `usePositionDetails()` live hook pattern
- [Source: `pm-arbitrage-dashboard/src/App.tsx:83-85`] — Backtesting route configuration
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-06-backtest-quality.md:255-341`] — Course correction story definition
- [Source: `_bmad-output/implementation-artifacts/10-95-6-open-position-reporting.md`] — Previous story (open position patterns)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no debugging needed.

### Completion Notes List

- **Task 1:** Added `getPosition()` endpoint to `BacktestController` with `ParseUUIDPipe` for runId and `ParseIntPipe` for positionId. Cross-run access prevention via `position.runId !== id` check. 3 new tests (match, 404 not found, 404 cross-run). TDD Red-Green-Refactor completed.
- **Task 2:** Added `useBacktestPosition` hook using direct `axiosInstance.get()` pattern (matches `useBacktestReport`). 30s staleTime since backtest data is immutable.
- **Task 3:** Route added before `:id` route for specificity. React Router v6 matches by specificity so order doesn't matter functionally, but placed for readability.
- **Task 4:** Leveraged existing `DataTable` `onRowClick` prop which already provides `cursor-pointer hover:bg-muted/50`. Exported `EXIT_REASON_MAP` for reuse. Added `runId` prop to `BacktestPositionsTable`.
- **Task 5:** Created 195-line detail page with 4 sections (Entry, Sides & Strategy, Exit, P&L Breakdown). Open/closed state handled via `exitReason === null`. Per-leg P&L uses FULL `positionSizeUsd` per leg matching backend `calculateLegPnl()`.
- **Task 7:** Lad MCP code review: 2 reviewers, all findings triaged to 0 patches (pre-existing, story-spec-approved, or out of scope).

### Change Log

- 2026-04-07: Story 10-95-7 implemented. Backend endpoint + React detail page + table click-through navigation.

### File List

**New files:**
- `pm-arbitrage-dashboard/src/pages/BacktestPositionDetailPage.tsx`

**Modified files (engine):**
- `pm-arbitrage-engine/src/modules/backtesting/controllers/backtest.controller.ts` — Added `getPosition()` endpoint
- `pm-arbitrage-engine/src/modules/backtesting/controllers/backtest.controller.spec.ts` — Added 3 position detail tests

**Modified files (dashboard):**
- `pm-arbitrage-dashboard/src/hooks/useBacktest.ts` — Added `useBacktestPosition` hook
- `pm-arbitrage-dashboard/src/App.tsx` — Added route + import
- `pm-arbitrage-dashboard/src/components/backtest/BacktestPositionsTable.tsx` — Exported `EXIT_REASON_MAP`, added `runId` prop + `onRowClick` handler + `useNavigate` import
- `pm-arbitrage-dashboard/src/pages/BacktestDetailPage.tsx` — Passes `runId` prop to `BacktestPositionsTable`
