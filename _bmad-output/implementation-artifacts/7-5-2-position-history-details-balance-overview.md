# Story 7.5.2: Position History, Details Page & Balance Overview

Status: DONE

## Story

As an operator,
I want to see my full position history, drill into detailed breakdowns of any position, see my available vs. blocked capital at a glance, and assess risk/reward via projected SL/TP P&L,
so that I can understand how the system has been performing over time and make informed decisions about open positions.

## Acceptance Criteria

1. **Position status tabs**: Positions page has "Open Positions" (OPEN, SINGLE_LEG_EXPOSED, EXIT_PARTIAL — current behavior) and "All Positions" (all statuses including CLOSED, RECONCILIATION_REQUIRED) toggle. Closed positions show: pair name, entry/exit prices, realized P&L, exit type (stop_loss / take_profit / time_based / manual), open/close timestamps, mode. Sorted by most recently updated, with pagination. [Source: epics.md#Epic-7.5, Story 7.5.2, AC: Position History]

2. **Position history backend**: `GET /dashboard/positions` accepts optional `status` query param (comma-separated status filter, e.g. `?status=OPEN,EXIT_PARTIAL`). When no status param provided and viewing "Open Positions", backend uses current default (`OPEN`, `SINGLE_LEG_EXPOSED`, `EXIT_PARTIAL`). When viewing "All Positions", frontend omits the status param and backend returns all statuses. Closed positions include associated orders in the response. Realized P&L for closed positions computed from order fill records (`fillSize * fillPrice`), not from `expectedEdge`. [Source: epics.md#Epic-7.5, Story 7.5.2, AC: Position History; P&L source-of-truth from Story 6.5.5k]

3. **Position detail page**: Clicking any position row navigates to `/positions/:id` showing a comprehensive breakdown: **Entry section** — per-leg contract counts, requested vs fill prices, entry slippage (fill - requested), capital invested (sum of both legs: fillSize x fillPrice + fees), entry timestamps. **Current state section** (open positions only) — current prices on both platforms, current edge, unrealized P&L, time held. **Exit section** (closed/partially exited) — exit prices (requested vs fill), exit timestamps, exit type and trigger reason, exit slippage, realized P&L breakdown (gross P&L - Kalshi fees - Polymarket fees). **Order history** — chronological list of all orders associated with this position (entry, exit attempts, partial fills, retry attempts) with status, timestamps, and fill details. **Audit trail** — key events from audit_logs filtered by this position's pair_id (opportunity identified, risk reserved, orders filled, exit triggered, single-leg events). [Source: epics.md#Epic-7.5, Story 7.5.2, AC: Position Details Page]

4. **Position detail backend**: `GET /dashboard/positions/:id/details` returns: position record, all associated orders (entry + exit + retries), entry reasoning from the `risk.budget.reserved` audit event details, and capital breakdown. Audit trail events fetched from audit_logs filtered by pairId with relevant event types only (not orderbook.updated or detection spam). [Source: epics.md#Epic-7.5, Story 7.5.2, AC: Position Details Backend]

5. **Audit trail index (mandatory)**: Prisma migration creates functional btree index: `CREATE INDEX idx_audit_logs_pair_id ON audit_logs USING btree ((details->>'pairId'))`. Detail page audit trail query uses this index for performant filtering. [Source: epics.md#Epic-7.5, Story 7.5.2, AC: Audit Trail Index]

6. **Balance overview display**: Dashboard overview section shows: total bankroll, deployed capital (blocked), available capital (bankroll - deployed - reserved), reserved capital (pending reservations not yet committed), and open position count. Values sourced from API — bankroll NEVER hardcoded in frontend. [Source: epics.md#Epic-7.5, Story 7.5.2, AC: Balance Overview]

7. **Balance overview backend**: `GET /dashboard/overview` response extended with: `totalBankroll` (from ConfigService `BANKROLL_USD` env var), `deployedCapital` (from `risk_states.totalCapitalDeployed`), `reservedCapital` (from `risk_states.reservedCapital`), `availableCapital` (computed: bankroll - deployed - reserved). Bankroll is the single source of truth from engine config. [Source: epics.md#Epic-7.5, Story 7.5.2, AC: Balance Overview — ADAPTED: extend existing `GET /dashboard/overview` instead of epic's non-existent `GET /api/risk/state`; confirmed during story creation disambiguation]

8. **SL/TP projected P&L display**: Each position row in the positions table displays projected P&L at stop-loss and take-profit thresholds. Format: "SL: -$2.14 / TP: +$1.87". For EXIT_PARTIAL positions, projections use residual sizes via `getResidualSize()`. [Source: epics.md#Epic-7.5, Story 7.5.2, AC: SL/TP Projected P&L]

9. **SL/TP projected P&L backend**: Enrichment service computes `projectedSlPnl` and `projectedTpPnl` as decimal string values in the enriched DTO. The SL/TP thresholds ARE P&L values directly (not close prices) — computed from `entryCostBaseline` and `scaledInitialEdge` using the same formulas as `ThresholdEvaluatorService`. For EXIT_PARTIAL, recompute with residual sizes via `getResidualSize()`. Lives in enrichment service — not the threshold evaluator — to keep the trading hot path clean. [Source: epics.md#Epic-7.5, Story 7.5.2, AC: SL/TP Projected P&L Backend]

## Tasks / Subtasks

### Backend (Engine — pm-arbitrage-engine/)

- [x] T1: Extend position repository with filtered query (AC: #2)
  - [x] T1.1: Add `findManyWithFilters(statuses?: PositionStatus[], isPaper?: boolean, page: number, limit: number)` to `PositionRepository`
  - [x] T1.2: When `statuses` is undefined/empty, return ALL statuses (for "All Positions" tab)
  - [x] T1.3: Include related orders via `pair: { include: { orders: true } }` for realized P&L computation
  - [x] T1.4: Unit tests for status filtering, pagination, mode filtering

- [x] T2: Extend `DashboardService.getPositions()` with status filter and realized P&L (AC: #2)
  - [x] T2.1: Accept optional `status` query param, parse comma-separated values
  - [x] T2.2: When status param absent, use current default open statuses (backward compatible)
  - [x] T2.3: Compute realized P&L for CLOSED positions from order fill records: entry cost vs exit proceeds per leg, minus platform fees
  - [x] T2.4: Add `realizedPnl` (string | null) and `exitType` (string | null) fields to `PositionSummaryDto`
  - [x] T2.5: Update Swagger query param decorators
  - [x] T2.6: Unit tests for realized P&L computation, status filter propagation, backward compat

- [x] T3: Create position detail DTOs (AC: #4)
  - [x] T3.1: `PositionFullDetailDto` in `src/dashboard/dto/position-detail.dto.ts` — wraps: position summary, orders array, audit events array, capital breakdown
  - [x] T3.2: `OrderDetailDto` — orderId, platform, side, requestedPrice (price), fillPrice, fillSize, slippage (computed), status, createdAt, updatedAt
  - [x] T3.3: `AuditEventDto` — id, eventType, timestamp, summary (human-readable extracted from details JSON)
  - [x] T3.4: `CapitalBreakdownDto` — entryCapitalPerLeg, totalFeesPerPlatform, grossPnl, netPnl
  - [x] T3.5: All fields with Swagger decorators (`@ApiProperty`)

- [x] T4: Implement `DashboardService.getPositionDetails(id)` (AC: #4)
  - [x] T4.1: Fetch position via `findByIdWithOrders()` (exists from 7.5.1)
  - [x] T4.2: Fetch ALL orders for the pairId bounded by position lifecycle: `createdAt >= position.createdAt`; for CLOSED: also `createdAt <= position.updatedAt`
  - [x] T4.3: Fetch audit_logs: `WHERE details->>'pairId' = :pairId AND eventType IN (:whitelist)` — uses new btree index
  - [x] T4.4: Compute capital breakdown: entry capital = `sum(fillSize * fillPrice + fees)` per leg using `decimal.js`
  - [x] T4.5: Extract entry reasoning from `BUDGET_RESERVED` event's details JSON
  - [x] T4.6: Enrich with current prices/P&L for open positions (reuse enrichment service)
  - [x] T4.7: Unit tests for full detail assembly, missing position (null), order temporal bounding

- [x] T5: Add `GET /dashboard/positions/:id/details` endpoint (AC: #4)
  - [x] T5.1: New method in `DashboardController` with Swagger decorators
  - [x] T5.2: Return `{ data: PositionFullDetailDto, timestamp: string }` wrapper
  - [x] T5.3: 404 via `NotFoundException` if position not found
  - [x] T5.4: Controller unit test

- [x] T6: Create Prisma migration for audit trail index (AC: #5)
  - [x] T6.1: Run `pnpm prisma migrate dev --create-only --name add-audit-logs-pair-id-index`
  - [x] T6.2: Edit generated `migration.sql` to contain: `CREATE INDEX idx_audit_logs_pair_id ON audit_logs USING btree ((details->>'pairId'));`
  - [x] T6.3: Run `pnpm prisma migrate dev` to apply
  - [x] T6.4: Prisma does NOT support functional JSONB indexes in `schema.prisma` — raw SQL in migration file is the correct approach

- [x] T7: Extend `DashboardOverviewDto` with balance fields (AC: #7)
  - [x] T7.1: Add fields: `totalBankroll: string`, `deployedCapital: string`, `availableCapital: string`, `reservedCapital: string`
  - [x] T7.2: All as `@ApiProperty({ type: String, description: '...' })` — decimal strings

- [x] T8: Extend `DashboardService.getOverview()` with balance computation (AC: #7)
  - [x] T8.1: Inject `ConfigService`, read `BANKROLL_USD` env var (already in `.env.*` files)
  - [x] T8.2: Query `risk_states` singleton for `totalCapitalDeployed` and `reservedCapital`
  - [x] T8.3: Compute: `availableCapital = new Decimal(bankroll).minus(deployed).minus(reserved)` — all `decimal.js`
  - [x] T8.4: Handle edge cases: no risk state row (defaults to zero deployed/reserved), zero bankroll
  - [x] T8.5: Unit tests for balance computation and edge cases

- [x] T9: Add SL/TP projected P&L to `PositionEnrichmentService` (AC: #9)
  - [x] T9.1: Extract threshold constants to `src/common/constants/exit-thresholds.ts`: `SL_MULTIPLIER = -2`, `TP_RATIO = 0.80` — then import in BOTH ThresholdEvaluatorService and PositionEnrichmentService (avoids module boundary violation and value duplication)
  - [x] T9.2: Compute thresholds as P&L values directly (NOT close prices): `projectedSlPnl = entryCostBaseline + scaledInitialEdge * SL_MULTIPLIER`; `projectedTpPnl = max(0, entryCostBaseline + TP_RATIO * (scaledInitialEdge - entryCostBaseline))` — reuse `FinancialMath.computeEntryCostBaseline()` (already imported by enrichment service)
  - [x] T9.3: For EXIT_PARTIAL: use `getResidualSize(position, allPairOrders)` from `src/common/utils/residual-size.ts` to get residual leg sizes, then recompute `scaledInitialEdge = initialEdge * residualLegSize` and `entryCostBaseline` with residual sizes
  - [x] T9.4: Add `projectedSlPnl: string | null` and `projectedTpPnl: string | null` to `PositionSummaryDto`
  - [x] T9.5: Return null for both when entry close prices unavailable (enrichment returns `partial` status)
  - [x] T9.6: Unit tests: OPEN projections, EXIT_PARTIAL with residual sizes, null when prices unavailable, zero-size edge case

- [x] T10: Swagger spec and API client (AC: all)
  - [x] T10.1: Verify all new/modified DTOs and endpoints have complete Swagger decorators
  - [x] T10.2: `pnpm build` to confirm zero TS errors
  - [x] T10.3: Start engine briefly to export swagger JSON, or use build output

### Frontend (Dashboard — pm-arbitrage-dashboard/)

- [x] T11: Regenerate API client (AC: all frontend)
  - [x] T11.1: Run `swagger-typescript-api` against updated swagger spec (picks up 7.5.1 close endpoint + all 7.5.2 changes)
  - [x] T11.2: Verify new types (`PositionFullDetailDto`, updated `DashboardOverviewDto`, etc.) and methods are generated

- [x] T12: Add position status tabs to PositionsPage (AC: #1)
  - [x] T12.1: Add "Open" / "All" toggle buttons above existing mode filter (Live/Paper/All)
  - [x] T12.2: "Open" = default, passes open statuses to hook; "All" = omits status filter
  - [x] T12.3: Update position count header to reflect filtered results
  - [x] T12.4: Closed positions in table: show realized P&L instead of unrealized, show exit type badge, dim current prices

- [x] T13: Update `useDashboardPositions` hook (AC: #1, #2)
  - [x] T13.1: Accept optional `statusFilter?: string` param
  - [x] T13.2: Pass `status` query param to API call when provided
  - [x] T13.3: Keep existing `mode` param working alongside new `status`

- [x] T14: Create PositionDetailPage (AC: #3)
  - [x] T14.1: Header: pair name, status badge, mode badge (Live/Paper), open date, close date (if applicable)
  - [x] T14.2: Entry section: DashboardPanel with per-leg cards — platform, side, requested price, fill price, slippage, fill size, timestamp, capital invested
  - [x] T14.3: Current state section (OPEN/EXIT_PARTIAL only): current prices per platform, current edge, unrealized P&L, time held since entry
  - [x] T14.4: Exit section (CLOSED/EXIT_PARTIAL): exit prices per leg, exit type, trigger reason, realized P&L breakdown (gross - Kalshi fees - Polymarket fees = net)
  - [x] T14.5: Order history: Table with columns — timestamp, platform, side, type (entry/exit/retry), requested price, fill price, fill size, status
  - [x] T14.6: Audit trail: Timeline list — timestamp, event type badge, summary text
  - [x] T14.7: Back button navigating to `/positions`

- [x] T15: Add route and row click navigation (AC: #3)
  - [x] T15.1: Add `<Route path="/positions/:id" element={<PositionDetailPage />} />` in App.tsx
  - [x] T15.2: Make PositionsTable rows clickable — `onClick` navigates to `/positions/${row.original.id}`
  - [x] T15.3: Visual hover effect on rows (`cursor-pointer hover:bg-muted/50`)

- [x] T16: Create `usePositionDetails(id)` query hook (AC: #3)
  - [x] T16.1: `useQuery({ queryKey: ['dashboard', 'position-details', id], queryFn, staleTime: 10_000 })`
  - [x] T16.2: Select unwraps `res.data`

- [x] T17: Add balance card to DashboardPage (AC: #6)
  - [x] T17.1: New "Capital Overview" DashboardPanel in the overview grid section
  - [x] T17.2: Display 4 values: Total Bankroll, Deployed, Available, Reserved — each as MetricDisplay or inline metric
  - [x] T17.3: `font-mono tabular-nums` for dollar amounts, color-code available capital (green >50%, yellow 20-50%, red <20% of bankroll)
  - [x] T17.4: Data from existing `useDashboardOverview()` — no new hook needed

- [x] T18: Add SL/TP projected P&L column to PositionsTable (AC: #8)
  - [x] T18.1: New column "Risk/Reward" showing "SL: -$X.XX / TP: +$X.XX"
  - [x] T18.2: SL value in red, TP value in green
  - [x] T18.3: Show only for OPEN and EXIT_PARTIAL (null/dash for CLOSED)
  - [x] T18.4: Tooltip on hover showing "Projected P&L at stop-loss / take-profit thresholds"

## Dev Notes

### Critical Architecture Constraints

**Module boundaries** [Source: CLAUDE.md#Architecture, Module Dependency Rules]:
- Dashboard controller = REST gateway for ALL read queries — position detail endpoint goes here
- `PositionManagementController` (`api/positions/`) handles WRITE operations only (close from 7.5.1)
- Enrichment service computes ALL derived display data — SL/TP projections belong here, NOT in exit-management module's ThresholdEvaluatorService

**Financial math** [Source: CLAUDE.md#Domain Rules]:
- ALL P&L computations MUST use `decimal.js` — `new Decimal(value.toString())` for Prisma Decimal conversion
- NEVER use native JS `*`, `+`, `-`, `/` on monetary values
- Realized P&L per leg: `(exitFillPrice - entryFillPrice) * fillSize` adjusted for side direction, minus fees
- Available capital: `new Decimal(bankroll).minus(deployed).minus(reserved)`

**API response format** [Source: CLAUDE.md#API Response Format]:
- Single: `{ data: T, timestamp: string }`
- List: `{ data: T[], count: number, timestamp: string }`
- Null for absent optionals — never `undefined`, never omitted

### Implementation Drift — Verified Against Codebase

1. **No `GET /api/risk/state` endpoint exists** — epic referenced extending this; resolved by extending `GET /dashboard/overview` [Verified: grep @Controller/@Get across all engine controllers]
2. **`GET /dashboard/positions` hardcodes open statuses** — `DashboardService.getPositions()` filters to `['OPEN', 'SINGLE_LEG_EXPOSED', 'EXIT_PARTIAL']` only [Verified: `src/dashboard/dashboard.service.ts`]
3. **`GET /dashboard/positions/:id` returns basic `PositionSummaryDto`** — no orders or audit trail; new `/details` sub-route needed [Verified: `src/dashboard/dashboard.controller.ts:94`]
4. **`useClosePosition()` calls wrong endpoint** — currently calls `singleLegResolutionControllerCloseLeg`; Story 7.5.3 will fix this — do NOT change in 7.5.2 [Verified: `pm-arbitrage-dashboard/src/hooks/useDashboard.ts`]
5. **Overview DTO lacks balance fields** — currently: systemHealth, trailingPnl7d, executionQualityRatio, openPositionCount, activeAlertCount [Verified: `src/dashboard/dto/dashboard-overview.dto.ts`]

### Existing Patterns to Reuse

**Backend DTOs** [Source: `src/dashboard/dto/`]:
- All DTOs use `@ApiProperty({ description, example, type })` — decimal values as `type: String`
- Response wrappers applied at controller level: `{ data, timestamp }` or `{ data, count, timestamp }`
- Null for absent optionals, never undefined [Source: CLAUDE.md#API Response Format]

**Position enrichment** [Source: `src/dashboard/position-enrichment.service.ts`]:
- Enriches in batches of 10 via `Promise.allSettled`
- Returns `{ status: 'enriched' | 'partial' | 'failed', data, errors? }`
- Already has access to: close prices (via `IPriceFeedService`), fee rates (`entryKalshiFeeRate`, `entryPolymarketFeeRate`), position data
- SL/TP projection is a natural extension of the same enrichment pass

**Frontend hooks** [Source: `pm-arbitrage-dashboard/src/hooks/useDashboard.ts`]:
```typescript
// Query pattern
useQuery({ queryKey: ['dashboard', 'resource'], queryFn: () => api.method(), select: res => res.data })
// Mutation pattern
useMutation({ mutationFn, onSuccess: () => queryClient.invalidateQueries({ queryKey: [...] }) })
```

**Frontend components** [Source: `pm-arbitrage-dashboard/src/components/`]:
- `DashboardPanel` for card sections with title
- `MetricDisplay` for large single-value metrics (monospace)
- TanStack React Table v8 with `useReactTable`, sortable columns
- Status badges with color variants, P&L color-coded (green/red)
- `font-mono tabular-nums` for ALL numeric displays
- `sonner` toast for error/success notifications

### Key Files to Modify

**Engine (pm-arbitrage-engine/):**

| File | Action | Notes |
|------|--------|-------|
| `src/dashboard/dashboard.controller.ts` | Modify | Add `GET positions/:id/details`, extend `positions` query params |
| `src/dashboard/dashboard.service.ts` | Modify | Add `getPositionDetails()`, extend `getPositions()` status filter, extend `getOverview()` balance |
| `src/dashboard/position-enrichment.service.ts` | Modify | Add SL/TP projected P&L computation |
| `src/dashboard/dto/position-summary.dto.ts` | Modify | Add `projectedSlPnl`, `projectedTpPnl`, `realizedPnl`, `exitType` |
| `src/dashboard/dto/dashboard-overview.dto.ts` | Modify | Add `totalBankroll`, `deployedCapital`, `availableCapital`, `reservedCapital` |
| `src/dashboard/dto/position-detail.dto.ts` | **Create** | `PositionFullDetailDto`, `OrderDetailDto`, `AuditEventDto`, `CapitalBreakdownDto` |
| `src/persistence/repositories/position.repository.ts` | Modify | Add `findManyWithFilters()` with status array + pagination |
| `prisma/migrations/…_add_audit_logs_pair_id_index/migration.sql` | **Create** | Raw SQL functional index (see Prisma notes below) |
| `src/dashboard/dashboard.module.ts` | Modify | If new providers needed |

**Dashboard (pm-arbitrage-dashboard/):**

| File | Action | Notes |
|------|--------|-------|
| `src/api/generated/Api.ts` | **Regenerate** | After engine Swagger spec updates |
| `src/pages/PositionsPage.tsx` | Modify | Add Open/All status tabs |
| `src/pages/PositionDetailPage.tsx` | **Create** | Full position breakdown page |
| `src/pages/DashboardPage.tsx` | Modify | Add balance card to overview grid |
| `src/components/PositionsTable.tsx` | Modify | Clickable rows, SL/TP column, closed position rendering |
| `src/hooks/useDashboard.ts` | Modify | `usePositionDetails()`, update `useDashboardPositions()` |
| `src/App.tsx` | Modify | Add `/positions/:id` route |

### Prior Story Intelligence (7.5.1)

[Source: `_bmad-output/implementation-artifacts/7-5-1-exit-partial-re-evaluation-dual-platform-close.md`]

**Key deliverables available from 7.5.1:**
- `getResidualSize()` at `src/common/utils/residual-size.ts` — pure function, computes residual contract sizes for EXIT_PARTIAL. Use for SL/TP projections.
- `PositionManagementController` at `src/dashboard/position-management.controller.ts` — `@Controller('api/positions')`, only write operations
- `findByIdWithOrders()` in position repository — fetches position with entry orders via FK relations
- `IPositionCloseService` and token injection pattern — follows `IPriceFeedService` pattern from Story 7.2
- `SingleLegExposureEvent` now has optional `origin` field — audit trail should display this context

**Patterns from 7.5.1 to follow:**
- DTO structure with Swagger decorators for all fields
- Error routing: 422 for business rule violations, NotFoundException for missing records
- Race condition handling via `ExecutionLockService` — NOT needed for read-only detail queries

### Audit Trail Event Type Whitelist

[Source: `src/common/events/event-catalog.ts`]

Include in detail page audit trail:
- `detection.opportunity.identified` — when the arbitrage opportunity was spotted
- `risk.budget.reserved` — capital reservation (contains entry reasoning in details)
- `risk.budget.committed` — reservation committed post-execution
- `execution.order.filled` — individual order fills
- `execution.order.failed` — failed order attempts
- `execution.exit.triggered` — exit threshold hit
- `execution.single_leg.exposure` — single-leg exposure detected

Exclude: `orderbook.updated`, detection cycle events, health events — these are high-volume and not position-specific.

**pairId in event details:** Verified — all execution events (`OrderFilledEvent`, `ExecutionFailedEvent`, `SingleLegExposureEvent`, `ExitTriggeredEvent`) include `pairId` as a constructor parameter, which gets serialized into `audit_logs.details` JSON. [Verified: `src/common/events/execution.events.ts` — pairId on lines 39, 79, 101, 131]

**Audit trail limit:** Apply `LIMIT 100` to the audit trail query to prevent oversized responses for long-lived positions. 100 events provides sufficient history context; the operator can always query the full audit trail via the export endpoint if needed.

### Prisma Migration: Functional JSONB Index

Prisma 6 does not support functional indexes on JSONB fields in `schema.prisma`. Use raw SQL migration:

```bash
pnpm prisma migrate dev --create-only --name add-audit-logs-pair-id-index
```

Edit the generated `migration.sql`:
```sql
CREATE INDEX idx_audit_logs_pair_id ON audit_logs USING btree ((details->>'pairId'));
```

Apply: `pnpm prisma migrate dev`

Do NOT add `@@index` to `schema.prisma` for this — it would fail on `(details->>'pairId')` syntax.

### exitType Data Source

[Verified: `exitType` / `exit_type` NOT in OpenPosition Prisma schema]

The `exitType` (stop_loss / take_profit / time_based / manual) is NOT stored on the OpenPosition model. It exists only in the `EXIT_TRIGGERED` audit event's details and in the `ThresholdEvalResult.type` field (runtime only).

**Solution: Derive from audit log for the positions list.**
For each closed position in the list response, query the most recent `execution.exit.triggered` audit event for the position's `pairId` and extract `type` from the event details JSON. For positions closed via manual endpoint (7.5.1), check for an `execution.order.filled` event with `origin: 'manual_close'` context — if present, `exitType = 'manual'`.

**Optimization for list queries:** Batch-fetch EXIT_TRIGGERED audit events for all positions' pairIds in a single query, then join in memory. This avoids N+1 queries:
```typescript
const pairIds = closedPositions.map(p => p.pairId);
const exitEvents = await prisma.auditLog.findMany({
  where: {
    eventType: 'execution.exit.triggered',
    // Use raw query with idx_audit_logs_pair_id index:
    // details->>'pairId' IN (:pairIds)
  },
  orderBy: { createdAt: 'desc' },
});
// Group by pairId, take most recent per pairId
```

**Alternative (future improvement):** Add `exitType` column to `open_positions` table and set it when the exit monitor or manual close updates the position status. This would eliminate the audit log query entirely. Not required for this story — the audit-based approach is correct and the new index makes it performant.

### Realized P&L Computation

[Source: Story 6.5.5k P&L source-of-truth; `ThresholdEvaluatorService.calculateLegPnl()` pattern]

**For closed positions in the list view:**
```typescript
// 1. Identify entry orders (direct FK on position)
const entryKalshi = position.kalshiOrder;   // { fillPrice, fillSize, side }
const entryPoly = position.polymarketOrder; // { fillPrice, fillSize, side }

// 2. Identify exit orders (all non-entry orders for this pair, within lifecycle)
const exitOrders = allPairOrders.filter(o => !entryOrderIds.has(o.orderId));

// 3. Compute entry cost per leg
// Buy leg: entryFillPrice * entryFillSize (capital spent)
// Sell leg: entryFillPrice * entryFillSize (capital received)

// 4. Per-leg P&L (same pattern as ThresholdEvaluatorService.calculateLegPnl):
// Buy side: (exitFillPrice - entryFillPrice) * fillSize
// Sell side: (entryFillPrice - exitFillPrice) * fillSize

// 5. Exit fees per platform:
// kalshiFee = sum(exitFillPrice * exitFillSize * kalshiFeeRate) for Kalshi exit orders
// polyFee = sum(exitFillPrice * exitFillSize * polyFeeRate) for Polymarket exit orders
// Fee rates: use position.entryKalshiFeeRate / entryPolymarketFeeRate (fee rates are
// per-platform constants, same at entry and exit for MVP — Kalshi uses dynamic fees
// corrected in 6.5.5g, stored on position at entry time)

// 6. Realized P&L = sum(legPnls) - sum(exitFees)
// ALL using decimal.js
```

**For multiple partial exits (EXIT_PARTIAL → CLOSED):** Sum across all exit orders. The `getResidualSize()` utility from 7.5.1 already handles this aggregation pattern — entry fills minus sum of exit fills.

### Order History Query Strategy

Orders are linked to positions indirectly via `pairId` (FK to ContractMatch). Entry orders have direct FK on OpenPosition (`polymarketOrderId`, `kalshiOrderId`). Exit/retry orders share `pairId` but have no direct position FK.

To get all orders for a specific position's lifecycle:
```typescript
// Entry orders: direct FK
const entryOrders = [position.polymarketOrder, position.kalshiOrder];

// All orders for pair within position lifecycle
const allOrders = await prisma.order.findMany({
  where: {
    pairId: position.pairId,
    createdAt: { gte: position.createdAt },
    // For CLOSED positions, also bound: lte: position.updatedAt
  },
  orderBy: { createdAt: 'asc' },
});
```

**Why temporal bounding is safe:** The system enforces at most one active position per pair at any time (via risk budget reservation in Story 4.4). Entry orders are always fetched via direct FK (never missed). Exit/retry orders are created ONLY while the position is active — the exit monitor and manual close both check position status before submitting orders. For CLOSED positions, `position.updatedAt` marks the close timestamp, providing an upper bound.

**Edge case:** Entry orders may have `createdAt` slightly before `position.createdAt` (order creation → position creation is non-atomic). Fetching entry orders via direct FK (`position.polymarketOrder`, `position.kalshiOrder`) avoids this — they don't need temporal bounding.

### Balance Computation

[Verified: `risk_states.reservedCapital` Decimal(20,8) and `risk_states.totalCapitalDeployed` Decimal(20,8) confirmed in `prisma/schema.prisma`]

- `totalBankroll`: `ConfigService.get('BANKROLL_USD')` — single source of truth [Source: epics.md#Epic-7.5]
- `deployedCapital`: `risk_states.totalCapitalDeployed` — updated on every position open/close [Source: `src/modules/risk-management/`]
- `reservedCapital`: `risk_states.reservedCapital` — tracked during execution lock phase [Source: `src/modules/risk-management/`]
- `availableCapital`: `new Decimal(bankroll).minus(deployed).minus(reserved)`

**Error handling:**
- If `BANKROLL_USD` env var is not set: log a warning and return `null` for all balance fields (do NOT throw — overview endpoint should still return health/P&L/counts)
- If `deployed + reserved > bankroll`: return `availableCapital = '0'` (floor at zero), log warning — this indicates configuration drift or race condition, not a crash-worthy error
- If risk_states row doesn't exist (first boot): default deployed = 0, reserved = 0

### SL/TP Projection Computation

[Source: `src/modules/exit-management/threshold-evaluator.service.ts` — verified implementation]

**Key insight: The SL/TP thresholds ARE P&L values directly.** They are not close prices — they are the `currentPnl` levels at which exit triggers fire. The enrichment service computes the same thresholds to show projected P&L.

**Formulas (from ThresholdEvaluatorService, lines 155-170):**
```typescript
const scaledInitialEdge = initialEdge.mul(legSize);
const entryCostBaseline = FinancialMath.computeEntryCostBaseline({...}); // already used by enrichment

// Stop-loss: P&L at which SL fires
const projectedSlPnl = entryCostBaseline.plus(scaledInitialEdge.mul(-2));

// Take-profit: P&L at which TP fires (floored at zero per 6.5.5j)
const projectedTpPnl = Decimal.max(
  new Decimal(0),
  entryCostBaseline.plus(scaledInitialEdge.minus(entryCostBaseline).mul(new Decimal('0.80')))
);
```

**For EXIT_PARTIAL positions:**
1. Get residual sizes: `const { kalshi, polymarket } = getResidualSize(position, allPairOrders)`
2. Use `min(kalshi, polymarket)` as `residualLegSize` (ThresholdEvaluator uses equal leg assumption)
3. Recompute: `scaledInitialEdge = initialEdge * residualLegSize`
4. Recompute `entryCostBaseline` with residual sizes
5. Apply same SL/TP formulas

**Example:** Position with `initialEdge = 0.02`, `legSize = 50`, `entryCostBaseline = -0.15`:
- `scaledInitialEdge = 0.02 * 50 = 1.00`
- `projectedSlPnl = -0.15 + (1.00 * -2) = -2.15` (operator loses ~$2.15 at SL)
- `projectedTpPnl = max(0, -0.15 + 0.80 * (1.00 - (-0.15))) = max(0, -0.15 + 0.92) = 0.77` (operator gains ~$0.77 at TP)

**Threshold constants:** Currently inline in ThresholdEvaluatorService (`-2` and `0.80`). Extract to `src/common/constants/exit-thresholds.ts` and import in both services to avoid duplication AND avoid cross-module import from exit-management (which would violate module boundaries). [Source: CLAUDE.md#Architecture, Module Dependency Rules]

### Testing Strategy

[Source: CLAUDE.md#Testing — Vitest, co-located spec files]

- Baseline: 83 test files, 1473 tests (all green, verified)
- Co-located: `dashboard.service.spec.ts`, `position-enrichment.service.spec.ts`, etc.
- Mock patterns: `vi.fn()` for service mocks, factory functions for test data
- Vitest + `unplugin-swc` for decorator metadata

**Required new test coverage:**
- Position repository: status array filtering, pagination, mode filtering
- Dashboard service: realized P&L from fill records, status filter propagation, backward compat (no status = open default)
- Position detail: DTO assembly with orders + audit events, temporal bounding of orders, missing position (404)
- Balance: bankroll - deployed - reserved computation, zero/missing risk state edge cases
- SL/TP projection: OPEN positions, EXIT_PARTIAL with residual sizes, null when prices unavailable
- Controller: new endpoint routing, 404 handling

### DoD Gates

- All existing 1473 tests pass (`pnpm test`), `pnpm lint` reports zero errors
- New test cases cover ALL acceptance criteria listed above
- No `decimal.js` violations introduced — all financial math uses Decimal methods
- Generated API client regenerated after engine Swagger spec changes
- Frontend builds without errors (`pnpm build` in dashboard repo)

### Dependency Note

[Source: epics.md#Epic-7.5, Dependency Note]

The bulk of this story (position history, detail page, balance overview, audit trail index) has NO dependency on Story 7.5.1. Only SL/TP projected P&L for EXIT_PARTIAL positions depends on `getResidualSize()` — which is already delivered at `src/common/utils/residual-size.ts`.

### Project Structure Notes

- Backend changes within `src/dashboard/` and `src/persistence/` — consistent with dashboard module ownership of read-only API [Source: CLAUDE.md#Module Structure]
- New `PositionDetailPage.tsx` in `pm-arbitrage-dashboard/src/pages/` — matches existing page organization
- No new modules, no new NestJS providers needed beyond what's already wired in `DashboardModule`
- Route `/positions/:id` follows React Router v7 dynamic segment pattern already used in App.tsx

### References

- [Source: epics.md#Epic-7.5] — All acceptance criteria and implementation notes
- [Source: CLAUDE.md#Architecture] — Module boundaries, error handling, API patterns, response format
- [Source: CLAUDE.md#Domain Rules] — Financial math (`decimal.js`), price normalization
- [Source: CLAUDE.md#Testing] — Vitest, co-located spec files
- [Source: 7-5-1-exit-partial-re-evaluation-dual-platform-close.md] — Prior story deliverables, getResidualSize, patterns
- [Source: src/dashboard/dashboard.service.ts] — Current getPositions/getOverview implementation
- [Source: src/dashboard/position-enrichment.service.ts] — Enrichment service patterns, batch processing
- [Source: src/dashboard/dto/position-summary.dto.ts] — Current DTO structure
- [Source: src/dashboard/dto/dashboard-overview.dto.ts] — Current overview DTO
- [Source: src/common/events/event-catalog.ts] — Event type constants for audit trail whitelist
- [Source: src/common/utils/residual-size.ts] — getResidualSize utility from 7.5.1
- [Source: src/modules/exit-management/threshold-evaluator.service.ts] — SL/TP threshold formulas
- [Source: pm-arbitrage-dashboard/src/hooks/useDashboard.ts] — Frontend query hook patterns
- [Source: pm-arbitrage-dashboard/src/components/PositionsTable.tsx] — Existing table component
- [Source: pm-arbitrage-dashboard/src/pages/DashboardPage.tsx] — Overview page layout
- [Source: pm-arbitrage-dashboard/src/App.tsx] — Router configuration
- [Source: pm-arbitrage-dashboard/src/api/generated/Api.ts] — Generated API client structure

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 via Claude Code CLI

### Completion Notes List

- All 18 tasks (T1-T18) implemented, verified, and CR fixes applied
- Backend: 1499 tests pass (83 spec files), lint clean, build clean
- Frontend: TypeScript clean, Vite build successful
- T6 migration applied successfully — `idx_audit_logs_pair_id` functional btree index on `audit_logs` for `details->>'pairId'`
- Shared exit threshold constants (`SL_MULTIPLIER`, `TP_RATIO`) extracted to `common/constants/exit-thresholds.ts` to avoid cross-module boundary violation between exit-management and dashboard modules
- Position detail page uses `createdAt`/`updatedAt` (Prisma model fields) instead of hypothetical `openedAt`/`closedAt` since the schema doesn't have dedicated timestamp columns for open/close
- Balance card on DashboardPage conditionally renders only when `totalBankroll` is available from the API (not null)
- Available capital color-coded: green >50%, yellow 20-50%, red <20% of bankroll
- PositionsTable rows are clickable with `cursor-pointer hover:bg-muted/50` for navigation to detail page; Close button uses `e.stopPropagation()` to prevent row click
- Pre-existing lint warnings in dashboard (MatchApprovalDialog setState-in-effect, useReactTable React Compiler compat) not addressed — out of scope

### Key Design Decisions

1. **Return type of `findManyWithFilters`**: Removed explicit `Promise<{data: Awaited<ReturnType<typeof this.prisma.openPosition.findMany>>; count: number}>` annotation because `typeof this` in return type position triggers TS2683 in strict mode. TypeScript infers the return type correctly from the method body.
2. **Exit orders null filtering**: The `exitOrdersByPairId` Map values include nullable entries (`kalshiOrder | null`). Added `.filter((o): o is NonNullable<typeof o> => o !== null)` before passing to `computeRealizedPnl()`.
3. **Column type casting in PositionsTable**: Used `ColumnDef<PositionSummaryDto, any>[]` explicit type for the `cols` array since `push()` with mixed accessor/display column defs caused type narrowing errors from TanStack Table's union types.
4. **Broken migration recovery**: `20260307021134_add_knowledge_base_resolution_fields` had an empty directory (no migration.sql). Recreated the SQL based on DB introspection and updated the checksum in `_prisma_migrations` to unblock new migration creation.

### Code Review Findings & Fixes

**Review performed by:** Claude Opus 4.6 (BMAD adversarial CR workflow)

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| C1 | Critical | EXIT_PARTIAL SL/TP thresholds used full entry size instead of residual sizes | Added `getResidualSize()` integration in `position-enrichment.service.ts` with `allPairOrders` param |
| C2 | Critical | No test coverage for EXIT_PARTIAL residual threshold computation | Added 2 tests in `position-enrichment.service.spec.ts` |
| H1 | High | `computeCapitalBreakdown` always returned null `grossPnl`/`netPnl` | Fixed per-leg P&L computation from exit orders using side-aware formula |
| H2 | High | Position detail page had skeletal exit section, no exit type display | Added `exitType` to DTO, computed from audit events, enhanced frontend `ExitSection` |
| H3 | High | `PositionRepository.findManyWithFilters()` was dead code | Wired into `DashboardService` constructor & `getPositions()`, added to module providers |
| M1 | Medium | SL/TP dollar formatting showed `$-2.40` instead of `-$2.40` | Fixed with `Math.abs()` in `RiskRewardCell` |
| M2 | Medium | Prisma JSON filter may not leverage btree index for audit pairId | Documented as acceptable — small table, Postgres may still use index on `details->>'pairId'` |

**Post-fix verification:** 1499 tests pass (83 spec files), lint clean, TypeScript clean (both repos).

### File List

**Backend (pm-arbitrage-engine/):**
| File | Action |
|------|--------|
| `src/persistence/repositories/position.repository.ts` | Modified — added `findManyWithFilters()` |
| `src/persistence/repositories/position.repository.spec.ts` | Modified — added 6 tests for `findManyWithFilters` |
| `src/dashboard/dashboard.service.ts` | Modified — extended `getPositions()` with status filter + realized P&L, added `getPositionDetails()`, extended `getOverview()` with balance |
| `src/dashboard/dashboard.service.spec.ts` | Modified — added tests for status filter, realized P&L, detail assembly, balance |
| `src/dashboard/dashboard.controller.ts` | Modified — added `status` query param, `GET positions/:id/details` endpoint |
| `src/dashboard/dashboard.controller.spec.ts` | Modified — added tests for status passthrough, detail endpoint, 404 |
| `src/dashboard/dto/position-summary.dto.ts` | Modified — added `realizedPnl`, `exitType`, `projectedSlPnl`, `projectedTpPnl` |
| `src/dashboard/dto/dashboard-overview.dto.ts` | Modified — added `totalBankroll`, `deployedCapital`, `availableCapital`, `reservedCapital` |
| `src/dashboard/dto/position-detail.dto.ts` | **Created** — `PositionFullDetailDto`, `OrderDetailDto`, `AuditEventDto`, `CapitalBreakdownDto` |
| `src/dashboard/dto/response-wrappers.dto.ts` | Modified — added `PositionFullDetailResponseDto` |
| `src/dashboard/dto/index.ts` | Modified — added export for position-detail.dto |
| `src/dashboard/position-enrichment.service.ts` | Modified — added `projectedSlPnl`/`projectedTpPnl`, EXIT_PARTIAL residual size support (CR C1) |
| `src/dashboard/position-enrichment.service.spec.ts` | Modified — added 3 tests for SL/TP projections + 2 EXIT_PARTIAL residual tests (CR C2) |
| `src/dashboard/dashboard.module.ts` | Modified — added `PositionRepository` provider (CR H3) |
| `src/common/constants/exit-thresholds.ts` | **Created** — `SL_MULTIPLIER`, `TP_RATIO` shared constants |
| `src/modules/exit-management/threshold-evaluator.service.ts` | Modified — import shared constants instead of inline values |
| `prisma/migrations/20260309004718_add_audit_logs_pair_id_index/migration.sql` | **Created** — functional btree index on `audit_logs` |
| `prisma/migrations/20260307021134_.../migration.sql` | **Recreated** — recovered from empty directory |

**Frontend (pm-arbitrage-dashboard/):**
| File | Action |
|------|--------|
| `src/api/generated/Api.ts` | Regenerated — includes all new types and endpoints |
| `src/hooks/useDashboard.ts` | Modified — added `status` param to `useDashboardPositions`, added `usePositionDetails` hook |
| `src/pages/PositionsPage.tsx` | Modified — added Open/All status tabs, status filter state |
| `src/pages/PositionDetailPage.tsx` | **Created** — full position detail page with entry/current/exit/orders/audit sections |
| `src/pages/DashboardPage.tsx` | Modified — added Capital Overview panel with balance metrics |
| `src/components/PositionsTable.tsx` | Modified — row click navigation, P&L column for realized/unrealized, Risk/Reward column, exit type column, hover effects |
| `src/App.tsx` | Modified — added `/positions/:id` route |
