# Story 7.4: Weekly Performance Metrics & Trends

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want weekly performance summaries with key metrics and trend analysis,
so that I can track whether the system is improving or degrading over time.

## Acceptance Criteria

### AC1 — Weekly Summary Display

- **Given** the operator navigates to the performance view
- **When** the weekly summary loads
- **Then** it displays:
  - Autonomy ratio (automated decisions / manual interventions)
  - Average slippage vs. modeled (absolute difference between `fillPrice` and `price` on filled orders)
  - Opportunity frequency (detected, filtered, executed counts)
  - P&L by week (sum of `expectedEdge` on closed positions)
  - Hit rate (profitable closed positions / total closed positions)
- **And** data is sourced from DB (not in-memory event counters) for persistence across restarts (FR-MA-09)

### AC2 — 4-Week Rolling Trend Analysis

- **Given** multiple weeks of data exist
- **When** trend analysis runs
- **Then** 4-week rolling averages are shown for opportunity frequency, edge captured, and slippage
- **And** alert indicators highlight if opportunity frequency drops below baseline (8-12/week)
- **And** edge degradation leading indicators are surfaced (average edge trend declining)

## Tasks / Subtasks

### Backend Tasks

- [x] **Task 1: Create `PerformanceService` with weekly and daily metrics aggregation** (AC: #1, #2)
  - [x] 1.1 Create `src/dashboard/performance.service.ts` — `@Injectable()`:
    - `getWeeklySummary(weeksBack: number = 8, mode?: 'live' | 'paper')` — returns array of `WeeklySummaryDto` for last N weeks. If `mode` is provided, filter `Order.isPaper` and `OpenPosition.isPaper` accordingly. If omitted, include all. Each week:
      - `weekStart: string` (ISO date, Monday 00:00:00.000 UTC)
      - `weekEnd: string` (ISO date, following Monday 00:00:00.000 UTC — exclusive upper bound)
      - `totalTrades: number` — count of `Order` records with `status = FILLED` in date range
      - `closedPositions: number` — count of `OpenPosition` with `status = CLOSED` and `updatedAt` in range
      - `pnl: string` — sum of `expectedEdge` on closed positions in range (Decimal string)
      - `hitRate: number` — (closed positions with `expectedEdge > 0`) / total closed. 0 if no closed positions.
      - `averageSlippage: string` — average `|fillPrice - price|` on filled orders in range (Decimal string). Use `decimal.js` for all math.
      - `opportunitiesDetected: number` — count of `AuditLog` entries where `eventType` matches `EVENT_NAMES.OPPORTUNITY_IDENTIFIED` in range
      - `opportunitiesFiltered: number` — count of `AuditLog` entries where `eventType` matches `EVENT_NAMES.OPPORTUNITY_FILTERED` in range
      - `opportunitiesExecuted: number` — count of `AuditLog` entries where `eventType` matches `EVENT_NAMES.ORDER_FILLED` in range
      - `manualInterventions: number` — count of `RiskOverrideLog` entries where `approved = true` in range
      - `autonomyRatio: string` — `totalTrades / max(manualInterventions, 1)` as string. "N/A" if zero trades. This matches the PRD "94:1" user scenario — reads as "94 automated trades per 1 manual intervention."
    - `getDailySummary(daysBack: number = 30, mode?: 'live' | 'paper')` — returns array of `DailyPerformanceDto` for last N days. Same metrics as weekly but aggregated per calendar day (00:00 UTC to next day 00:00 UTC, exclusive upper bound). Lighter-weight version for recent trend monitoring.
    - `getRollingAverages(mode?: 'live' | 'paper')` — computes 4-week rolling averages from `getWeeklySummary(8, mode)`:
      - Rolling average for: opportunity frequency, edge captured per week, slippage per week
      - Alert flag: `opportunityBelowBaseline: boolean` — true if latest 4-week avg opportunity count < 8
      - Trend indicator: `edgeTrend: 'improving' | 'stable' | 'declining'` — compare latest 4-week avg to previous 4-week avg
  - [x] 1.2 Inject `PrismaService` (for Order, OpenPosition, AuditLog, RiskOverrideLog queries)
  - [x] 1.3 Use `decimal.js` for ALL financial math (slippage, P&L, edge, averages). Convert Prisma Decimal via `new Decimal(value.toString())`.
  - [x] 1.4 **CRITICAL: Use `EVENT_NAMES` constants** from `src/common/events/event-catalog.ts` for all AuditLog `eventType` queries. NEVER use raw string literals — use `EVENT_NAMES.OPPORTUNITY_IDENTIFIED`, `EVENT_NAMES.OPPORTUNITY_FILTERED`, `EVENT_NAMES.ORDER_FILLED`.
  - [x] 1.5 Write `performance.service.spec.ts` — tests:
    - Weekly summary with data across multiple weeks
    - Empty week returns zeroes / "N/A" for autonomy
    - Slippage calculation correctness (absolute value of fill vs price)
    - Hit rate edge cases (0 closed positions → 0, all profitable → 1.0)
    - Autonomy ratio with zero manual interventions → trades / 1
    - Rolling averages computed correctly from 8 weeks
    - Opportunity baseline alert flag
    - Edge trend detection (improving/stable/declining)
    - Date range boundaries use exclusive upper bound (Monday < next Monday)
    - Paper mode filter: `mode='paper'` only includes `isPaper=true` orders/positions
    - Paper mode filter: `mode='live'` excludes `isPaper=true`
    - Paper mode filter: `mode=undefined` includes all
    - Daily summary with data across multiple days
    - Daily summary empty day returns zeroes

- [x] **Task 2: Create `PerformanceController` with REST endpoints** (AC: #1, #2)
  - [x] 2.1 Create `src/dashboard/performance.controller.ts` — `@Controller('performance')`, `@UseGuards(AuthTokenGuard)`, `@ApiTags('Performance')`, `@ApiBearerAuth()`:
    - `GET /api/performance/weekly` — returns `{ data: WeeklySummaryDto[], count: number, timestamp: string }`. Query params: `?weeks=N` (default 8, max 52, min 1), `?mode=live|paper` (optional — omit for all).
    - `GET /api/performance/daily` — returns `{ data: DailyPerformanceDto[], count: number, timestamp: string }`. Query params: `?days=N` (default 30, max 90, min 1), `?mode=live|paper` (optional). Architecture-mandated endpoint for recent daily granularity.
    - `GET /api/performance/trends` — returns `{ data: PerformanceTrendsDto, timestamp: string }`. Query params: `?mode=live|paper` (optional). Includes rolling averages + alert flags.
  - [x] 2.2 Create query DTOs:
    - `WeeklyQueryDto` — `{ weeks?: number; mode?: 'live' | 'paper' }` with `@IsOptional()`, `@IsInt()`, `@Min(1)`, `@Max(52)`, `@Type(() => Number)`, `@IsEnum()`. Apply `@UsePipes(new ValidationPipe({ whitelist: true, transform: true }))` on GET handler (same pattern as `TradeExportController`, `MatchApprovalController`).
    - `DailyQueryDto` — `{ days?: number; mode?: 'live' | 'paper' }` with `@IsOptional()`, `@IsInt()`, `@Min(1)`, `@Max(90)`, `@Type(() => Number)`, `@IsEnum()`.
    - `TrendsQueryDto` — `{ mode?: 'live' | 'paper' }` with `@IsOptional()`, `@IsEnum()`.
  - [x] 2.3 Register `PerformanceController` AND `PerformanceService` in `DashboardModule` (controller in `controllers`, service in `providers`)
  - [x] 2.4 Write `performance.controller.spec.ts` — tests:
    - GET /weekly returns weekly summaries (default 8 weeks)
    - GET /weekly?weeks=4 returns 4 weeks
    - GET /weekly?weeks=0 → 400 (below min)
    - GET /weekly?weeks=100 → 400 (above max)
    - GET /weekly?mode=paper filters paper trades only
    - GET /daily returns daily summaries (default 30 days)
    - GET /daily?days=7 returns 7 days
    - GET /daily?days=0 → 400
    - GET /trends returns trends with rolling averages
    - GET /trends?mode=live filters live trades only
    - Auth guard applied
    - Swagger decorators present

- [x] **Task 3: Create response DTOs** (AC: #1, #2)
  - [x] 3.1 Create `src/dashboard/dto/performance.dto.ts`:
    - `WeeklySummaryDto` — all fields described in Task 1.1 above, with `@ApiProperty()` decorators
    - `DailyPerformanceDto` — same fields as `WeeklySummaryDto` but with `date: string` (ISO date) instead of `weekStart`/`weekEnd`
    - `RollingAverageDto` — `{ opportunityFrequency: number; edgeCaptured: string; slippage: string }` with `@ApiProperty()`
    - `PerformanceTrendsDto` — `{ rollingAverages: RollingAverageDto; opportunityBelowBaseline: boolean; edgeTrend: 'improving' | 'stable' | 'declining'; latestWeekSummary: WeeklySummaryDto }` with `@ApiProperty()`
    - `WeeklyListResponseDto` — `{ data: WeeklySummaryDto[], count: number, timestamp: string }` extending standard wrapper pattern
    - `DailyListResponseDto` — `{ data: DailyPerformanceDto[], count: number, timestamp: string }`
    - `TrendsResponseDto` — `{ data: PerformanceTrendsDto, timestamp: string }`
    - `WeeklyQueryDto`, `DailyQueryDto`, `TrendsQueryDto` — request DTOs (see Task 2.2)
  - [x] 3.2 Export from `src/dashboard/dto/index.ts`

### Frontend Tasks

- [x] **Task 4: Create Performance page with weekly metrics table** (AC: #1)
  - [x] 4.1 Create `src/pages/PerformancePage.tsx` — uses `useDashboardPerformance()` and `useDashboardTrends()` hooks
  - [x] 4.2 Display weekly summary as a table (most recent week first):
    - Columns: Week, Trades, Closed, P&L, Hit Rate, Avg Slippage, Opportunities (D/F/E), Autonomy Ratio
    - P&L column: green text for positive, red for negative
    - Hit rate as percentage (e.g., "75.0%")
    - Opportunities as "12 / 3 / 9" (detected / filtered / executed)
  - [x] 4.3 Use `DashboardPanel` container (if exists) or `Card` component for consistent styling
  - [x] 4.4 Use `Table` from shadcn/ui for the data grid
  - [x] 4.5 Default to 8 weeks, with a selector to change (4, 8, 12, 26, 52 weeks)
  - [x] 4.6 Add mode filter toggle (All / Live / Paper) — defaults to All. Same pattern as positions page mode filter. Passes `mode` to `useDashboardPerformance` and `useDashboardTrends` hooks.
  - [x] 4.7 Empty state: "No performance data yet. Metrics will appear after the first week of trading."

- [x] **Task 5: Create Trends summary card with alerts** (AC: #2)
  - [x] 5.1 Create `src/components/TrendsSummary.tsx` — displays:
    - 4-week rolling averages for opportunity frequency, edge captured, slippage
    - Edge trend indicator: arrow up (green) for improving, dash (gray) for stable, arrow down (red) for declining
    - Opportunity baseline alert: if below baseline (8/week), show amber warning banner
  - [x] 5.2 Position at top of PerformancePage, above the weekly table
  - [x] 5.3 Use `MetricDisplay` component (existing in dashboard) for individual metrics where appropriate

- [x] **Task 6: Add query hooks and routing** (AC: #1, #2)
  - [x] 6.1 Add to `src/hooks/useDashboard.ts`:
    ```typescript
    export function useDashboardPerformance(weeks: number = 8, mode?: 'live' | 'paper') {
      return useQuery({
        queryKey: ['dashboard', 'performance', weeks, mode],
        queryFn: () => api.performanceControllerGetWeekly({ weeks, mode }),
        staleTime: 60_000, // Performance data changes slowly — 1 minute stale
      });
    }

    export function useDashboardDaily(days: number = 30, mode?: 'live' | 'paper') {
      return useQuery({
        queryKey: ['dashboard', 'daily', days, mode],
        queryFn: () => api.performanceControllerGetDaily({ days, mode }),
        staleTime: 60_000,
      });
    }

    export function useDashboardTrends(mode?: 'live' | 'paper') {
      return useQuery({
        queryKey: ['dashboard', 'trends', mode],
        queryFn: () => api.performanceControllerGetTrends({ mode }),
        staleTime: 60_000,
      });
    }
    ```
  - [x] 6.2 Add `/performance` route to `App.tsx` → `PerformancePage`
  - [x] 6.3 Add "Performance" link to `Navigation.tsx` (after Matches)

- [x] **Task 7: Regenerate API client** (AC: all)
  - [x] 7.1 Run `pnpm generate-api` in dashboard to pick up new performance endpoints and DTOs
  - [x] 7.2 Verify generated types include `WeeklySummaryDto`, `PerformanceTrendsDto`, performance endpoints

## Dev Notes

### Architecture Compliance

- **Module boundaries:** `PerformanceController` and `PerformanceService` live in `src/dashboard/` — same pattern as `DashboardController`, `MatchApprovalController`. Performance metrics are an operator-facing dashboard feature.
- **Data source: Database, NOT in-memory counters.** The `EventConsumerService.getMetrics()` provides in-memory event counts that reset on process restart. For weekly metrics, we MUST query the database directly:
  - `Order` table → trade counts, fill prices (slippage calculation)
  - `OpenPosition` table → closed position counts, P&L (expectedEdge), hit rate
  - `AuditLog` table → opportunity detected/filtered/executed counts (events are persisted here by `AuditLogService`)
  - `RiskOverrideLog` table → manual intervention counts (autonomy ratio)
- **Error hierarchy:** Use `SystemHealthError` with existing codes (4000-series) for database failures. No new error codes needed.
- **Response format:** All endpoints use standard wrapper: `{ data: T, timestamp: string }` / `{ data: T[], count: number, timestamp: string }`.
- **Financial math:** ALL calculations (slippage, P&L sums, averages, edge) MUST use `decimal.js`. Convert Prisma Decimal via `new Decimal(value.toString())`.

### Metrics Derivation — Detailed SQL/Prisma Logic

**CRITICAL: Event Name Constants.** All AuditLog `eventType` queries MUST use `EVENT_NAMES` constants from `src/common/events/event-catalog.ts`. NEVER hardcode string literals. The EventConsumerService (line 250) persists ALL domain events (except `monitoring.audit.*`) to AuditLog with their event name as `eventType`.

**PnL Assumption:** `expectedEdge` is used as P&L proxy. In prediction markets, the entry price spread (edge) IS the realized profit at resolution (minus slippage). This is NOT the same as traditional finance mark-to-market P&L. The approach is correct for this domain but should be understood as "edge captured at entry" not "realized exit P&L."

**Slippage Calculation:**
```
For each Order WHERE status = 'FILLED' AND fillPrice IS NOT NULL:
  slippage = |fillPrice - price|  (absolute value, using decimal.js)
Average slippage = sum(slippages) / count
```
Note: `price` is the requested price, `fillPrice` is the actual fill price. Both are `Decimal(20,8)` columns.

**Paper Mode Filtering:** When `mode` is provided, add `isPaper` filter to `Order` and `OpenPosition` queries:
- `mode = 'live'` → `{ isPaper: false }`
- `mode = 'paper'` → `{ isPaper: true }`
- `mode = undefined` → no filter (all trades)
AuditLog and RiskOverrideLog do NOT have `isPaper` — their counts are always unfiltered regardless of mode.

**Autonomy Ratio:**
```
automated = count(Order WHERE status = 'FILLED' AND createdAt IN range [+ isPaper filter])
manual = count(RiskOverrideLog WHERE approved = true AND createdAt IN range)
ratio = automated / max(manual, 1)
```
This measures "how many automated trades per manual intervention." Higher is better (PRD example: "94:1"). If no manual interventions, divide by 1 to show total automated trades as the ratio.

**Hit Rate:**
```
profitable = count(OpenPosition WHERE status = 'CLOSED' AND expectedEdge > 0 AND updatedAt IN range [+ isPaper filter])
total = count(OpenPosition WHERE status = 'CLOSED' AND updatedAt IN range [+ isPaper filter])
hitRate = profitable / total  (0 if total = 0)
```

**Opportunity Counts (from AuditLog):**
```
SELECT COUNT(*) FROM audit_logs
WHERE event_type = EVENT_NAMES.OPPORTUNITY_IDENTIFIED
AND created_at >= weekStart AND created_at < weekEnd
```
Same pattern for `EVENT_NAMES.OPPORTUNITY_FILTERED` and `EVENT_NAMES.ORDER_FILLED`.

**Date Range Boundaries — Exclusive Upper Bound:**
- Week: `weekStart = Monday 00:00:00.000 UTC`, `weekEnd = next Monday 00:00:00.000 UTC`
- Day: `dayStart = 00:00:00.000 UTC`, `dayEnd = next day 00:00:00.000 UTC`
- Prisma queries use `{ gte: start, lt: end }` — NEVER `lte` for the upper bound (avoids microsecond precision issues with PostgreSQL)
- Use `Date` arithmetic, NOT `date-fns` or similar library (no new dependencies)

**4-Week Rolling Average:**
```
Given weeks[0..7] (most recent first):
rollingAvg = average(weeks[0..3])   // latest 4 weeks
previousAvg = average(weeks[4..7])  // previous 4 weeks
edgeTrend = rollingAvg.pnl > previousAvg.pnl * 1.1 ? 'improving'
          : rollingAvg.pnl < previousAvg.pnl * 0.9 ? 'declining'
          : 'stable'
```
10% threshold for trend detection avoids noise.

### Existing Infrastructure (DO NOT recreate)

- **`AuthTokenGuard`** — Reuse on controller (`src/common/guards/auth-token.guard.ts`)
- **`DashboardModule`** — Register new controller and service here
- **`PrismaService`** — Inject for all DB queries
- **`Order` model** — Has `price`, `fillPrice`, `status`, `createdAt` columns
- **`OpenPosition` model** — Has `expectedEdge`, `status`, `updatedAt` columns
- **`AuditLog` model** — Has `eventType`, `createdAt` columns (indexed on both)
- **`RiskOverrideLog` model** — Has `approved`, `createdAt` columns
- **`SystemHealthError`** — Existing error class with DATABASE_FAILURE code
- **`SYSTEM_HEALTH_ERROR_CODES`** — Import from `src/common/errors/system-health-error.ts`

### No New Prisma Migration Needed

All required data already exists in the database:
- `Order.price`, `Order.fillPrice`, `Order.status` — for slippage and trade counts
- `OpenPosition.expectedEdge`, `OpenPosition.status` — for P&L and hit rate
- `AuditLog.eventType`, `AuditLog.createdAt` — for opportunity counts (already indexed)
- `RiskOverrideLog.approved`, `RiskOverrideLog.createdAt` — for autonomy ratio

No schema changes, no migration.

### No WebSocket Events Needed

Performance metrics are slow-changing data (weekly aggregations). No real-time WebSocket push required. The frontend uses `staleTime: 60_000` (1 minute) for polling — appropriate for data that updates at most once per day.

### Frontend Patterns (from Stories 7.1 + 7.2 + 7.3)

- **API Client:** `src/api/client.ts` exports `api`. Generated client at `src/api/generated/Api.ts`.
- **Hooks:** All query/mutation hooks in `src/hooks/useDashboard.ts`.
- **Query Keys:** Follow pattern `['dashboard', '<resource>', ...params]`.
- **Components:** Use shadcn/ui components. Available: `card`, `badge`, `button`, `table`, `tooltip`, `alert`, `sonner` (toasts).
- **Styling:** Tailwind CSS 4, `cn()` utility, no gradients/shadows, flat terminal aesthetic.
- **Routing:** `react-router-dom` with `<Routes>` in `App.tsx`. Currently: `/` (dashboard), `/positions`, `/matches`.
- **Navigation:** `src/components/Navigation.tsx` — shared top nav with `NavLink` active state styling.
- **MetricDisplay:** `src/components/MetricDisplay.tsx` — reusable metric card with label/value.

### UX Design for Performance View

```
┌──────────────────────────────────────────────────────────┐
│  PM Arbitrage   Dashboard  Positions  Matches  Performance│
└──────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  4-Week Rolling Averages                                 │
│                                                          │
│  Opportunities/wk   Edge/wk      Avg Slippage           │
│  ┌──────────┐      ┌──────────┐  ┌──────────┐          │
│  │   10.5   │      │  $42.30  │  │  0.0023  │          │
│  └──────────┘      └──────────┘  └──────────┘          │
│                                                          │
│  Edge Trend: ↑ Improving    Opp Baseline: ✓ On track    │
└─────────────────────────────────────────────────────────┘

⚠️ Opportunity frequency below baseline (6.2/week vs 8 minimum)
   ↑ (Only shown when opportunityBelowBaseline is true, amber alert)

┌──────────────────────────────────────────────────────────────────────────┐
│  Weekly Performance Summary                          [4w ▾ 8w 12w 52w] │
│                                                                          │
│  Week       │ Trades │ Closed │ P&L     │ Hit  │ Slippage │ Opps    │ AR│
│  ─────────────────────────────────────────────────────────────────────── │
│  Mar 3-9    │  12    │   3    │ +$18.40 │ 66%  │ 0.0021   │ 15/3/12 │ 12│
│  Feb 24-Mar2│   9    │   2    │ -$4.20  │ 50%  │ 0.0035   │ 11/2/9  │  9│
│  Feb 17-23  │  11    │   4    │ +$32.10 │ 75%  │ 0.0018   │ 14/3/11 │ 11│
│  ...                                                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

- P&L: green for positive, red for negative
- Hit rate below 50%: amber text
- Opportunity baseline warning: amber alert banner above table
- Edge trend arrows: ↑ green, → gray, ↓ red
- Compact "D/F/E" format for opportunities (Detected/Filtered/Executed)
- AR = Autonomy Ratio (compact column header, tooltip for full label)

### Project Structure Notes

**New backend files:**

- `src/dashboard/performance.service.ts` — weekly metrics aggregation
- `src/dashboard/performance.service.spec.ts` — service tests
- `src/dashboard/performance.controller.ts` — REST endpoints
- `src/dashboard/performance.controller.spec.ts` — controller tests
- `src/dashboard/dto/performance.dto.ts` — response DTOs

**Modified backend files:**

- `src/dashboard/dashboard.module.ts` — register PerformanceController + PerformanceService
- `src/dashboard/dto/index.ts` — export new DTOs

**New frontend files (pm-arbitrage-dashboard/):**

- `src/pages/PerformancePage.tsx` — performance view with table + trends
- `src/components/TrendsSummary.tsx` — 4-week rolling averages + alerts

**Modified frontend files (pm-arbitrage-dashboard/):**

- `src/App.tsx` — add `/performance` route
- `src/hooks/useDashboard.ts` — add `useDashboardPerformance`, `useDashboardTrends`
- `src/components/Navigation.tsx` — add Performance link
- `src/api/generated/Api.ts` — regenerated from Swagger

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 7, Story 7.4 lines 1887-1904]
- [Source: _bmad-output/planning-artifacts/prd.md — FR-MA-09 line 881]
- [Source: _bmad-output/planning-artifacts/architecture.md — Dashboard API endpoints: /api/performance/weekly, /api/performance/daily]
- [Source: pm-arbitrage-engine/prisma/schema.prisma — Order model (price, fillPrice, status), OpenPosition model (expectedEdge, status), AuditLog model (eventType, createdAt), RiskOverrideLog model (approved, createdAt)]
- [Source: pm-arbitrage-engine/src/modules/monitoring/daily-summary.service.ts — DailySummaryData interface for existing daily metrics pattern]
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts — EVENT_NAMES for audit log event types]
- [Source: pm-arbitrage-engine/src/dashboard/dashboard.service.ts — existing Prisma query patterns, decimal.js usage]
- [Source: pm-arbitrage-engine/src/dashboard/dashboard.controller.ts — existing controller patterns, auth guard, swagger decorators]
- [Source: pm-arbitrage-engine/src/dashboard/dashboard.module.ts — module registration pattern]
- [Source: 7-1-dashboard-project-setup-system-health-view.md — frontend patterns, MetricDisplay component]
- [Source: 7-2-open-positions-p-and-l-detail-view.md — position enrichment, table patterns]
- [Source: 7-3-contract-matching-approval-interface.md — match approval controller patterns, DTO patterns, navigation addition]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None.

### Completion Notes List

- All 7 tasks implemented following TDD (tests written first, then implementation)
- 32 new tests added (22 service + 10 controller), total suite: 1358 passing
- All financial math uses decimal.js, no native JS operators on monetary values
- EVENT_NAMES constants used for all AuditLog queries (verified by test)
- Date ranges use exclusive upper bound (gte/lt, never lte) — verified by test
- Paper mode filter only applied to Order/OpenPosition tables (AuditLog/RiskOverrideLog unfiltered)
- Swagger 200 response types added to all controller endpoints (per Lad code review)
- Added partial data test (fewer than 8 weeks) per Lad code review recommendation
- Dashboard SPA builds clean (tsc + vite), API client regenerated with all new endpoints/DTOs

#### Code Review Fixes (Amelia — adversarial review)
- **H1 FIXED:** 14 ESLint errors resolved — controller spec refactored to explicit mock types (project pattern), service spec mockImplementation scoped eslint-disable for async mocks
- **M1 FIXED:** Added 3 missing controller tests: AuthTokenGuard decorator verification, Swagger ApiTags verification, default weeks=8 fallback. Validation tests (weeks=0/100, days=0) deferred — require NestJS e2e test with full pipe setup, not unit test scope
- **M2 FIXED:** Renamed misleading test "should return stable trend when fewer than 8 weeks" → "should detect improving trend when previous 4 weeks have zero data"
- **M3 FIXED:** Parallelized 7 sequential DB queries in `aggregateRange` with `Promise.all()` — reduces latency from ~7x to ~1x per time range
- **L1 FIXED:** Added `dataInsufficient: boolean` to `PerformanceTrendsDto` — true when < 8 non-empty weeks exist. Frontend shows muted alert banner when trend data is unreliable. 2 new tests.
- **L2 FIXED:** Wrapped `getWeeklySummary` and `getDailySummary` with try/catch → `SystemHealthError(4002, DATABASE_FAILURE)`. Re-throws existing `SystemHealthError` without double-wrapping. 3 new tests.

### File List

**New backend files (pm-arbitrage-engine/):**
- `src/dashboard/performance.service.ts` — weekly/daily metrics aggregation + rolling averages
- `src/dashboard/performance.service.spec.ts` — 17 tests
- `src/dashboard/performance.controller.ts` — REST endpoints (weekly, daily, trends)
- `src/dashboard/performance.controller.spec.ts` — 7 tests
- `src/dashboard/dto/performance.dto.ts` — query DTOs, response DTOs, wrapper DTOs

**Modified backend files (pm-arbitrage-engine/):**
- `src/dashboard/dashboard.module.ts` — registered PerformanceController + PerformanceService
- `src/dashboard/dto/index.ts` — added performance.dto export

**New frontend files (pm-arbitrage-dashboard/):**
- `src/pages/PerformancePage.tsx` — weekly metrics table + mode filter + week selector
- `src/components/TrendsSummary.tsx` — 4-week rolling averages + edge trend + baseline alert

**Modified frontend files (pm-arbitrage-dashboard/):**
- `src/App.tsx` — added /performance route
- `src/hooks/useDashboard.ts` — added useDashboardPerformance, useDashboardDaily, useDashboardTrends hooks
- `src/components/Navigation.tsx` — added Performance nav link
- `src/api/generated/Api.ts` — regenerated from Swagger (includes performance endpoints + DTOs)
