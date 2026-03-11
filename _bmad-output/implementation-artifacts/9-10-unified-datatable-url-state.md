# Story 9.10: Unified DataTable & URL State Persistence

Status: done

## Story

As an operator,
I want all dashboard tables to use a shared DataTable component and persist sorting/pagination/filter state in URL query parameters,
So that I can bookmark, share, and navigate back to specific views without losing my table configuration.

## Acceptance Criteria

1. **Given** the PositionsPage renders a table of positions **When** the page loads **Then** it uses the shared `DataTable` component (not the custom `PositionsTable.tsx` implementation) **And** `PositionsTable.tsx` is deleted [Source: sprint-change-proposal-2026-03-13-dashboard-ux.md#Story-9-10, item 1]

2. **Given** the PerformancePage renders a weekly performance table **When** the page loads **Then** it uses the shared `DataTable` with column defs and client-side sorting enabled **And** `weeks` and `mode` filter selections sync to URL query parameters (`/performance?weeks=8&mode=all`) [Source: sprint-change-proposal-2026-03-13-dashboard-ux.md#Story-9-10, items 2+6]

3. **Given** the StressTestPage renders 3 tables (P&L percentiles, synthetic scenarios, contract volatilities) **When** the page loads **Then** the synthetic scenarios and contract volatilities tables use `DataTable` inside the existing collapsible wrappers **And** the P&L percentiles table (single data row, dynamic columns) is exempt from DataTable migration and remains a raw `<Table>` as it is a data visualization, not a data table [Source: sprint-change-proposal-2026-03-13-dashboard-ux.md#Story-9-10, item 3; exemption per review — single-row display table]

4. **Given** the PositionDetailPage renders an order history table **When** the page loads **Then** it uses the shared `DataTable` [Source: sprint-change-proposal-2026-03-13-dashboard-ux.md#Story-9-10, item 4]

5. **Given** any page uses DataTable with a `urlStateKey` prop **When** the operator changes sorting, pagination, or filters **Then** the state is persisted in URL query parameters via `useSearchParams()` **And** refreshing the page restores the exact table state **And** browser back/forward navigates between page changes (pagination uses `push`); sort/filter changes use `replace` to avoid polluting history [Source: sprint-change-proposal-2026-03-13-dashboard-ux.md#Story-9-10, item 5]

6. **Given** a page URL contains query parameters (e.g. `/positions?sort=expectedEdge&order=desc&mode=paper&status=open&page=2`) **When** the page loads **Then** the DataTable initializes with the URL-specified state [Source: sprint-change-proposal-2026-03-13-dashboard-ux.md, query param format examples]

7. **Given** the MatchesPage already uses DataTable **When** the `urlStateKey` enhancement is added **Then** MatchesPage adopts URL state persistence for its existing sorting, pagination, tab, and cluster filter [Source: sprint-change-proposal-2026-03-13-dashboard-ux.md#Story-9-10, item 6]

8. **Given** the positions API endpoint `GET /dashboard/positions` **When** `sortBy` and `order` query params are provided **Then** the backend sorts results by the specified DB column before pagination **And** the response order matches the requested sort **And** only DB-mapped columns are server-sortable: `createdAt`, `updatedAt`, `expectedEdge`, `status`, `isPaper` **And** an invalid `sortBy` value returns 400 Bad Request via class-validator [Source: user confirmation — backend sorting required for positions]

9. **Given** custom cell renderers exist in `PositionsTable.tsx` (PnlCell, StatusBadge, ExitTypeBadge, RiskRewardCell) **When** they are needed across multiple pages **Then** they live in a shared `src/components/cells/` directory and are imported by all consuming pages [Source: sprint-change-proposal-2026-03-13-dashboard-ux.md#Story-9-10, item 1]

10. **Given** all tables are migrated **Then** zero instances of raw `<Table>/<TableBody>/<TableRow>` remain in page files, except the StressTestPage P&L percentiles table (exempted per AC #3) [Derived from: AC #1-4 — complete migration]

11. **Given** a page URL contains an invalid `sortBy` value (e.g. user manually edits URL) **When** the frontend reads URL params on mount **Then** invalid sort params are silently dropped and defaults are applied **And** the URL is replaced (not pushed) with corrected params [Derived from: review feedback — invalid URL param handling]

12. **Given** PositionsPage uses server-side sorting (`manualSorting=true`) **When** a column is computed post-fetch (unrealizedPnl, currentEdge, timeToResolution, pairName) **Then** that column has `enableSorting: false` and shows no sort indicator **And** only DB-mapped columns (expectedEdge, status, isPaper, createdAt, updatedAt) show sort indicators [Derived from: AC #8 — server-sort-only columns]

## Tasks / Subtasks

### Backend: Positions Sorting Support

- [x] **Task 1: Add `PositionSortField` enum and update DTOs** (AC: #8)
  - [x] Create `PositionSortField` enum in `dashboard/dto/` with sortable DB columns: `createdAt`, `updatedAt`, `expectedEdge`, `status`, `isPaper`
  - [x] Move `SortOrder` enum from `match-approval.dto.ts` to a shared `dashboard/dto/common-query.dto.ts` (reuse across both DTOs)
  - [x] Add `sortBy?: PositionSortField` and `order?: SortOrder` query params to positions controller with `@ApiQuery` decorators
  - [x] Add class-validator decorators (`@IsOptional`, `@IsEnum`) on new DTO fields

- [x] **Task 2: Update `PositionRepository.findManyWithFilters()` for sorting** (AC: #8)
  - [x] Add `sortBy?: string` and `order?: 'asc' | 'desc'` parameters
  - [x] Map `sortBy` values to Prisma `orderBy` clause (default: `{ updatedAt: 'desc' }`)
  - [x] Validate `sortBy` against allowed column names to prevent injection

- [x] **Task 3: Wire sorting through `DashboardService.getPositions()` → controller** (AC: #8)
  - [x] Pass `sortBy` and `order` from controller to service to repository
  - [x] Default behavior unchanged when params are omitted (`updatedAt desc`)

- [x] **Task 4: Backend unit tests** (AC: #8)
  - [x] Test `PositionRepository.findManyWithFilters` with each sort field
  - [x] Test controller passes sort params correctly
  - [x] Test default sort when params omitted
  - [x] Test invalid sort field is rejected by DTO validation

### Frontend: Shared Cell Renderers

- [x] **Task 5: Extract shared cell renderer components** (AC: #9)
  - [x] Create `src/components/cells/PnlCell.tsx` — extracted from `PositionsTable.tsx:30-38`
  - [x] Create `src/components/cells/StatusBadge.tsx` — unified from PositionsTable (:41-47), PositionDetailPage (:10-17), MatchesPage (:15-19)
  - [x] Create `src/components/cells/ExitTypeBadge.tsx` — extracted from `PositionsTable.tsx:50-68`, also duplicated in PositionDetailPage (:140-154)
  - [x] Create `src/components/cells/RiskRewardCell.tsx` — extracted from `PositionsTable.tsx:70-85`
  - [x] Create `src/components/cells/index.ts` barrel export
  - [x] Extract `formatDecimal` utility from `PositionsTable.tsx:23-28` to `lib/utils.ts` (alongside existing `formatUsd`)
  - [x] Update all consuming pages to import from `@/components/cells/` and `@/lib/utils`

### Frontend: `useUrlTableState` Hook

- [x] **Task 6: Create `src/hooks/useUrlTableState.ts`** (AC: #5, #6, #11)
  - [x] Accept a typed config: `{ defaults: Record<string, string | undefined>, filterKeys?: string[] }`
  - [x] `filterKeys` lists param names that trigger page reset on change (e.g. `['status', 'mode', 'tab', 'cluster', 'sort', 'order']`)
  - [x] Wrap `useSearchParams()` from `react-router-dom`
  - [x] Return `{ params, setParam, setParams, getParam }` with typed getters for sort/order/page/filters
  - [x] Read initial state from URL on mount; apply defaults for missing params
  - [x] On mount, validate URL params against `defaults` keys; silently drop unknown sort/order values and `replace` URL with corrected params (AC #11)
  - [x] On `setParam`/`setParams` for filter/sort changes, call `setSearchParams` with `replace: true` (avoid polluting history per toggle)
  - [x] On page changes, call `setSearchParams` with default `push` behavior (so back button navigates between pages)
  - [x] When any `filterKeys` param changes, auto-reset `page` to `'1'`
  - [x] This hook manages ALL URL params for the page (both table state AND page-level filters like mode/status/weeks). One hook instance per page — no competing URL managers

### Frontend: DataTable Enhancement

- [x] **Task 7: Add optional URL state integration to DataTable** (AC: #5, #6)
  - [x] Add optional `urlStateKey` prop (string). When provided, DataTable reads/writes sorting state to/from URL via `useUrlTableState`
  - [x] Ensure backward compatibility: DataTable without `urlStateKey` works exactly as before (local state)
  - [x] Pagination `onPageChange` also syncs to URL when `urlStateKey` is set

### Frontend: Table Migrations

- [x] **Task 8: Migrate PositionsPage to DataTable** (AC: #1, #10)
  - [x] Define column defs using `createColumnHelper<PositionSummaryDto>()` — reuse shared cell renderers from Task 5
  - [x] Use `DataTable` with `manualSorting` + `urlStateKey="positions"` (server-side sort)
  - [x] Sync mode and status filters to URL via `useUrlTableState`
  - [x] Update `useDashboardPositions` hook to accept `sortBy`, `order` params and pass to API
  - [x] Wire pagination to URL (page param)
  - [x] Delete `src/components/PositionsTable.tsx`
  - [x] Preserve `ClosePositionDialog` and close button behavior in actions column
  - [x] Preserve row click → `/positions/:id` navigation

- [x] **Task 9: Migrate MatchesPage to use URL state** (AC: #7)
  - [x] Replace `useState` for tab/page/clusterId/sorting with `useUrlTableState`
  - [x] URL format: `/matches?tab=pending&sort=confidenceScore&order=desc&page=1&cluster=<id>`
  - [x] Existing `DataTable` usage stays; add `urlStateKey="matches"`

- [x] **Task 10: Migrate PerformancePage table to DataTable** (AC: #2, #10)
  - [x] Define column defs for 8 columns (Week, Trades, Closed, P&L, Hit Rate, Slippage, Opps, AR)
  - [x] Use `DataTable` with client-side sorting (`manualSorting=false`)
  - [x] Sync mode and weeks filters to URL: `/performance?weeks=8&mode=all`
  - [x] Preserve existing TrendsSummary component above the table

- [x] **Task 11: Migrate PositionDetailPage order history to DataTable** (AC: #4, #10)
  - [x] Define column defs for 8 columns (Timestamp, Platform, Side, Req. Price, Fill Price, Fill Size, Slippage, Status)
  - [x] Use `DataTable` with client-side sorting, no pagination (small dataset)
  - [x] Keep inside existing `DashboardPanel title="Order History"` wrapper

- [x] **Task 12: Migrate StressTestPage 2 tables to DataTable** (AC: #3, #10)
  - [x] P&L percentiles table — EXEMPT from migration (single data row, dynamic columns; keep as raw `<Table>`)
  - [x] Synthetic scenarios table → DataTable (2 columns, client-side sorting on P&L)
  - [x] Contract volatilities table → DataTable (4 columns, client-side sorting on Vol)
  - [x] Keep inside existing collapsible wrappers (`syntheticOpen`, `volOpen`)

### Verification

- [x] **Task 13: Regenerate API client** (AC: #8) — **Must run after Tasks 1-4 (backend complete), before Task 8 (frontend needs types)**
  - [x] Run `swagger-typescript-api` to pick up new `sortBy`/`order` query params on positions endpoint
  - [x] Verify generated client types match new DTO

- [x] **Task 14: Lint & test** (AC: #1-10)
  - [x] `pnpm lint` passes in both repos
  - [x] `pnpm test` passes in engine (all existing tests + new sorting tests)
  - [x] No raw `<Table>` usage remains in any page file (grep verification)
  - [x] Manual smoke: navigate to each page, verify table renders, sort, paginate, refresh preserves state

## Dev Notes

### Architecture Compliance

- **Module boundary**: Backend changes are confined to `dashboard/` module (controller, service, repository). No new module imports needed. [Source: CLAUDE.md#Module-Dependency-Rules]
- **DTO validation**: Use `class-validator` decorators matching the pattern in `MatchListQueryDto` (`match-approval.dto.ts:69-122`). [Source: codebase — verified pattern]
- **Error hierarchy**: No new error types needed. Existing `SystemHealthError` covers DB failures. [Source: CLAUDE.md#Error-Handling]

### Backend: Positions Sorting Implementation

**Pattern to follow:** `MatchListQueryDto` + `MatchApprovalService.listMatches()` already implement sort + paginate. Mirror this pattern.

**`PositionSortField` enum — allowed values:**

```typescript
export enum PositionSortField {
  CREATED_AT = 'createdAt',
  UPDATED_AT = 'updatedAt',
  EXPECTED_EDGE = 'expectedEdge',
  STATUS = 'status',
  IS_PAPER = 'isPaper',
}
```

Only DB-column sorts are supported. Computed fields (`unrealizedPnl`, `currentEdge`) cannot be sorted server-side because they are calculated post-fetch by `PositionEnrichmentService`. The frontend should disable sort indicators on computed columns.

**`SortOrder` enum** is currently defined in `match-approval.dto.ts:65-68`. Move it to a shared location (`dashboard/dto/common-query.dto.ts` or similar) so both `MatchListQueryDto` and the new positions query DTO can import it.

**Repository change** (`position.repository.ts:105-135`):

```typescript
async findManyWithFilters(
  statuses?: string[],
  isPaper?: boolean,
  page?: number,
  limit?: number,
  sortBy?: string,   // NEW
  order?: 'asc' | 'desc',  // NEW
) {
  // Map sortBy to Prisma orderBy, default: { updatedAt: 'desc' }
  const orderBy = sortBy
    ? { [sortBy]: order ?? 'desc' }
    : { updatedAt: 'desc' as const };
  // ... existing where clause ...
  // pass orderBy to findMany
}
```

Validate `sortBy` against allowed enum values in the controller/DTO layer (class-validator `@IsEnum`) — the repository trusts its callers.

### Frontend: `useUrlTableState` Hook Design

This hook is the **single owner** of URL params for a page. One instance per page. It manages both page-level filters (mode, status, weeks) and table state (sort, order, page).

```typescript
// src/hooks/useUrlTableState.ts
import { useSearchParams } from 'react-router-dom';

interface UrlTableStateConfig {
  defaults: Record<string, string | undefined>;
  filterKeys?: string[]; // params that trigger page reset
}

export function useUrlTableState(config: UrlTableStateConfig) {
  const [searchParams, setSearchParams] = useSearchParams();

  // getParam(key) → reads from URL, falls back to config.defaults[key]
  // setParam(key, value, opts?) → updates URL
  //   - opts.push: true for page changes (default: false = replace)
  //   - if key is in filterKeys, auto-resets page to '1'
  // setParams(record) → batch-update multiple params at once
}
```

**Usage example (PositionsPage):**

```typescript
const urlState = useUrlTableState({
  defaults: { status: 'open', mode: 'all', sort: 'updatedAt', order: 'desc', page: '1' },
  filterKeys: ['status', 'mode', 'sort', 'order'],
});

// Read: urlState.getParam('mode') // 'all' or from URL
// Write filter: urlState.setParam('mode', 'paper') // replace, resets page
// Write page: urlState.setParam('page', '2', { push: true }) // push (back button works)
```

**Key design decisions:**

- Sort/filter changes use `replace: true` (don't pollute history per toggle)
- Page changes use `push` (so back button goes to previous page)
- Params not in `defaults` are preserved (future-proof for other consumers)
- On mount, invalid sort/order values (not matching allowed enums) are silently dropped and URL is `replace`d with defaults
- Parse `page` as number, all others as strings

**Frontend → Backend sort field mapping** (PositionsPage):

```typescript
// Column accessor → API sortBy mapping
const POSITION_SORT_MAP: Record<string, string> = {
  initialEdge: 'expectedEdge', // accessor 'initialEdge' maps to DB column 'expectedEdge'
  // createdAt, updatedAt, status, isPaper → 1:1 mapping
};
```

**Filter param naming convention:**
| UI Control | URL Param | Values | Page |
|------------|-----------|--------|------|
| Status tab | `status` | `open` (default), `all` | PositionsPage |
| Mode toggle | `mode` | `all` (default), `live`, `paper` | PositionsPage, MatchesPage, PerformancePage |
| Tab filter | `tab` | `pending` (default), `approved`, `all` | MatchesPage |
| Cluster filter | `cluster` | UUID or omitted | MatchesPage |
| Weeks picker | `weeks` | `8` (default), `4`, `12`, `26`, `52` | PerformancePage |
| Sort field | `sort` | column accessor name | All pages with sorting |
| Sort direction | `order` | `asc`, `desc` | All pages with sorting |
| Page number | `page` | 1-indexed integer | Pages with pagination |

Each page uses different params. No collision risk because each page has its own route. The `mode` param name is reused across pages but they're on different routes (`/positions`, `/matches`, `/performance`).

### Frontend: DataTable Enhancement

Current `DataTable` (`components/DataTable.tsx:20-31`) accepts:

```typescript
interface DataTableProps<TData> {
  columns: ColumnDef<TData, any>[];
  data: TData[];
  isLoading: boolean;
  emptyMessage?: string;
  onRowClick?: (row: TData) => void;
  pagination?: PaginationProps;
  initialSorting?: SortingState;
  manualSorting?: boolean;
  onSortingChange?: (sorting: SortingState) => void;
}
```

The `urlStateKey` prop is an **alternative** to `initialSorting`/`onSortingChange`/`pagination.onPageChange`. When `urlStateKey` is set, DataTable internally uses `useUrlTableState` to manage sorting/pagination state. The existing callback-based API remains for backward compatibility (pages that don't want URL sync).

**Precedence when both are provided:** If `urlStateKey` is set, it takes precedence over `initialSorting` and `onSortingChange`. Do not provide both — the dev should use one pattern or the other per page. DataTable should log a console warning in development if both are provided.

### Frontend: PositionsTable Migration

**Current:** `PositionsTable.tsx` (316 lines) — custom `useReactTable`, 12-13 columns, `ClosePositionDialog` integration, `useNavigate` for row clicks.

**Migration plan:**

1. Extract cell renderers to `components/cells/` (PnlCell, StatusBadge, ExitTypeBadge, RiskRewardCell already identified)
2. Move column defs to `PositionsPage.tsx` using `createColumnHelper<PositionSummaryDto>()`
3. Replace `PositionsTable` with `DataTable` in `PositionsPage.tsx`
4. `ClosePositionDialog` state management moves to `PositionsPage.tsx`
5. Delete `PositionsTable.tsx`

**Column mappings (PositionsTable → DataTable column defs):**
| Column | Accessor | Sortable | Server-sort? | Cell Renderer |
|--------|----------|----------|--------------|---------------|
| Pair | `pairName` | Yes | No (derived) | Truncated text |
| Entry | `entryPrices` | No | — | K/P price stack |
| Current | `currentPrices` | No | — | K/P price stack |
| Init Edge | `initialEdge` | Yes | Yes (`expectedEdge`) | `formatDecimal()` |
| Curr Edge | `currentEdge` | Yes | No (computed) | `formatDecimal()` |
| P&L | display | Yes | No (computed) | `PnlCell` |
| Risk/Reward | display | No | — | `RiskRewardCell` |
| Resolution | `timeToResolution` | Yes | No (computed) | Text |
| Exit Proximity | `exitProximity` | No | — | `ExitProximityIndicator` |
| Status | `status` | Yes | Yes | `StatusBadge` |
| Exit Type | display (conditional) | No | — | `ExitTypeBadge` |
| Mode | `isPaper` | Yes | Yes | Badge |
| Actions | display | No | — | Close button |

Columns marked "Server-sort: No (computed)" should use `enableSorting: false` when `manualSorting=true`. The alternative is client-side sort within the fetched page, which is misleading with pagination. Better to disable.

### Frontend: PerformancePage Migration

Current raw `<Table>` with 8 static columns. No backend sorting support. Use DataTable with `manualSorting=false` (client-side sort via `getSortedRowModel()`). No pagination needed (typically 4-52 rows).

URL state: `/performance?weeks=8&mode=all` — sync `weeks` and `mode` filter selections.

### Frontend: StressTestPage Migration

Three collapsible tables, two migrated:

1. **P&L Percentiles** — EXEMPT. Single data row with dynamic columns (p1, p5, ..., p99). This is a data visualization, not a sortable/pageable data table. Keep as raw `<Table>`. DataTable's row-based model is a poor fit for a single-row wide table.
2. **Synthetic Scenarios** — 2 columns (Scenario, Portfolio P&L). Migrate to DataTable with client-side sorting on P&L column.
3. **Contract Volatilities** — 4 columns (Contract, Platform, Vol, Source). Migrate to DataTable with client-side sorting on Vol column.

Keep existing collapsible toggle buttons above each table. No URL state for StressTestPage tables (small static data, no pagination).

### Frontend: PositionDetailPage Migration

Order history table: 8 columns, typically 2-4 rows. Convert to DataTable with client-side sorting, no pagination. Stays inside `DashboardPanel title="Order History"` wrapper.

Audit trail section is a `<div>` list (not a table) — leave as-is, not in scope.

### Shared Component Deduplication

| Component        | Current Locations                                        | Shared Location                                       |
| ---------------- | -------------------------------------------------------- | ----------------------------------------------------- |
| `PnlCell`        | PositionsTable:30                                        | `components/cells/PnlCell.tsx`                        |
| `PnlValue`       | PositionDetailPage:19                                    | Merge into `PnlCell.tsx` (same logic, different name) |
| `StatusBadge`    | PositionsTable:41, PositionDetailPage:10, MatchesPage:15 | `components/cells/StatusBadge.tsx`                    |
| `ExitTypeBadge`  | PositionsTable:50, PositionDetailPage:140                | `components/cells/ExitTypeBadge.tsx`                  |
| `RiskRewardCell` | PositionsTable:70                                        | `components/cells/RiskRewardCell.tsx`                 |
| `formatDecimal`  | PositionsTable:23                                        | `lib/utils.ts` (alongside existing `formatUsd`)       |

### API Client Regeneration

After backend changes, regenerate the swagger-typescript-api client so the new `sortBy`/`order` query params on positions are typed. The generated client uses `baseURL` (axios convention) — see `pm-arbitrage-dashboard/src/api/client.ts`. [Source: MEMORY.md — Generated API client config]

### Existing Patterns to Preserve

- `'use no memo'` directive in DataTable (React 19 compiler opt-out) [Source: DataTable.tsx:44]
- `eslint-disable-next-line react-hooks/incompatible-library` on `useReactTable` call [Source: DataTable.tsx:53]
- `keepPreviousData` placeholder in `useDashboardMatches` for pagination UX [Source: useDashboard.ts:65]
- `ExitProximityIndicator` component stays separate (imported into column defs, not a "cell" component) [Source: components/ExitProximityIndicator.tsx]
- `ClosePositionDialog` / `CloseAllDialog` integration on PositionsPage [Source: PositionsPage.tsx:96-106]

### Project Structure Notes

**Files to create (frontend):**

- `pm-arbitrage-dashboard/src/components/cells/PnlCell.tsx`
- `pm-arbitrage-dashboard/src/components/cells/StatusBadge.tsx`
- `pm-arbitrage-dashboard/src/components/cells/ExitTypeBadge.tsx`
- `pm-arbitrage-dashboard/src/components/cells/RiskRewardCell.tsx`
- `pm-arbitrage-dashboard/src/components/cells/index.ts`
- `pm-arbitrage-dashboard/src/hooks/useUrlTableState.ts`

**Files to create (backend):**

- `pm-arbitrage-engine/src/dashboard/dto/common-query.dto.ts` (shared `SortOrder` enum + `PositionSortField` enum)

**Files to modify (frontend):**

- `pm-arbitrage-dashboard/src/components/DataTable.tsx` — add `urlStateKey` prop
- `pm-arbitrage-dashboard/src/pages/PositionsPage.tsx` — full rewrite to use DataTable + URL state
- `pm-arbitrage-dashboard/src/pages/MatchesPage.tsx` — adopt URL state
- `pm-arbitrage-dashboard/src/pages/PerformancePage.tsx` — migrate to DataTable + URL state
- `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx` — migrate order history to DataTable
- `pm-arbitrage-dashboard/src/pages/StressTestPage.tsx` — migrate 3 tables to DataTable
- `pm-arbitrage-dashboard/src/hooks/useDashboard.ts` — add sortBy/order to `useDashboardPositions`
- `pm-arbitrage-dashboard/src/lib/utils.ts` — add `formatDecimal` utility

**Files to modify (backend):**

- `pm-arbitrage-engine/src/dashboard/dashboard.controller.ts` — add sortBy/order query params
- `pm-arbitrage-engine/src/dashboard/dashboard.service.ts` — pass sort params through
- `pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts` — remove `SortOrder` (moved to shared)
- `pm-arbitrage-engine/src/persistence/repositories/position.repository.ts` — add orderBy support

**Files to delete:**

- `pm-arbitrage-dashboard/src/components/PositionsTable.tsx`

**Test files to create/modify (backend):**

- `pm-arbitrage-engine/src/persistence/repositories/position.repository.spec.ts` — add sorting tests
- `pm-arbitrage-engine/src/dashboard/dashboard.controller.spec.ts` — add sort param tests
- `pm-arbitrage-engine/src/dashboard/dashboard.service.spec.ts` — add sort passthrough tests

### Dependencies & Versions

| Package               | Version  | Role                                         |
| --------------------- | -------- | -------------------------------------------- |
| react-router-dom      | ^7.13.1  | `useSearchParams` hook for URL state         |
| @tanstack/react-table | ^8.21.3  | `ColumnDef`, `SortingState`, `useReactTable` |
| @tanstack/react-query | ^5.90.21 | `useQuery` with `keepPreviousData`           |
| class-validator       | (engine) | `@IsEnum`, `@IsOptional` for new DTO fields  |

No new dependencies required. All capabilities come from already-installed packages.

### References

- [Source: sprint-change-proposal-2026-03-13-dashboard-ux.md] — Full proposal with all 5 stories, URL format examples, dependency chain
- [Source: CLAUDE.md#Architecture] — Module dependency rules, error handling, naming conventions
- [Source: pm-arbitrage-dashboard/src/components/DataTable.tsx] — Current DataTable implementation (142 lines)
- [Source: pm-arbitrage-dashboard/src/components/PositionsTable.tsx] — Custom table to delete (316 lines)
- [Source: pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts:51-68] — MatchSortField + SortOrder enum pattern to mirror
- [Source: pm-arbitrage-engine/src/persistence/repositories/position.repository.ts:105-135] — findManyWithFilters to extend
- [Source: pm-arbitrage-engine/src/dashboard/dashboard.controller.ts:49-101] — Positions controller to add sort params
- [Source: react-router-dom v7.13.1 docs] — `useSearchParams` returns `[URLSearchParams, setSearchParams]` tuple, stable reference, supports `replace` option

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
N/A

### Completion Notes List
- Backend: Created `PositionSortField` enum + shared `SortOrder` in `common-query.dto.ts`, updated `match-approval.dto.ts` to import from shared location
- Backend: Extended `PositionRepository.findManyWithFilters()` with `sortBy`/`order` params mapped to Prisma `orderBy`
- Backend: Wired sort params through `DashboardController` → `DashboardService` → `PositionRepository` with `@ApiQuery` decorators
- Backend: +8 new unit tests (4 repository sorting, 2 controller sort passthrough, 1 service sort passthrough, 1 default sort verification). Updated 10 existing tests to expect 6-arg calls
- Frontend: Extracted 4 shared cell renderers (PnlCell, StatusBadge, ExitTypeBadge, RiskRewardCell) to `components/cells/`
- Frontend: Added `formatDecimal` utility to `lib/utils.ts`
- Frontend: Created `useUrlTableState` hook for URL query param state management with `filterKeys` auto-page-reset
- Frontend: Enhanced `DataTable` with `urlStateKey` prop via internal `DataTableWithUrl` component (backward compatible)
- Frontend: Migrated PositionsPage to DataTable with server-side sorting + URL state, deleted `PositionsTable.tsx`
- Frontend: Migrated MatchesPage to URL state (tab, page, cluster, sort, order in URL)
- Frontend: Migrated PerformancePage to DataTable with client-side sorting + URL state (mode, weeks)
- Frontend: Migrated PositionDetailPage order history to DataTable
- Frontend: Migrated StressTestPage synthetic scenarios + contract volatilities to DataTable. P&L percentiles exempt (single-row dynamic columns)
- Regenerated swagger-typescript-api client with new `sortBy`/`order` position params
- **Code review fix**: Replaced raw `@Query()` params with `PositionsQueryDto` + `@UsePipes(ValidationPipe)` for runtime enum validation (AC #8). Removed manual `parseInt` + `Math.max` parsing — DTO `@Type(() => Number)` + `@IsInt()` + `@Min(1)` + `@Max(200)` handles this declaratively
- Test count: 2007 → 2015 (+8 backend tests)
- All page files verified: zero raw `<Table>` usage except StressTestPage P&L percentiles (exempt per AC #3)
- **Code review #2 fix (2026-03-14)**: Fixed 3 MEDIUM + 3 LOW issues:
  - MEDIUM: AC #11 — Added `allowedValues` validation to `useUrlTableState` hook; invalid URL sort params now silently dropped and defaults applied, URL replaced on mount
  - MEDIUM: `dashboard.service.spec.ts` — Added missing `EventEmitter2` mock (5th constructor param was missing, `this.eventEmitter` was `undefined` in tests)
  - MEDIUM: `RiskRewardCell.tsx` — Added `isNaN()` guard after `parseFloat()` to prevent rendering "SL: -$NaN"
  - LOW: `PerformancePage.tsx` — Replaced `type WeekData = any` with proper `WeeklySummaryDto` type from generated API client
  - LOW: Extracted inline URL state config objects to module-level constants in PositionsPage, MatchesPage, PerformancePage (fixes memoization defeat from new objects per render)
  - LOW: Added `allowedValues` for mode/status/tab params across all 3 pages for comprehensive URL validation

### File List

**Backend (pm-arbitrage-engine/):**
- `src/dashboard/dto/common-query.dto.ts` — NEW: shared SortOrder + PositionSortField enums
- `src/dashboard/dto/match-approval.dto.ts` — MODIFIED: import SortOrder from common-query.dto
- `src/dashboard/dto/index.ts` — MODIFIED: added common-query.dto export
- `src/dashboard/dashboard.controller.ts` — MODIFIED: added sortBy/order @ApiQuery params
- `src/dashboard/dashboard.service.ts` — MODIFIED: pass sortBy/order to repository
- `src/dashboard/match-approval.service.ts` — MODIFIED: import SortOrder from common-query.dto
- `src/persistence/repositories/position.repository.ts` — MODIFIED: added sortBy/order to findManyWithFilters
- `src/persistence/repositories/position.repository.spec.ts` — MODIFIED: +4 sorting tests
- `src/dashboard/dashboard.controller.spec.ts` — MODIFIED: +2 sort tests, updated 3 existing tests
- `src/dashboard/dashboard.service.spec.ts` — MODIFIED: +1 sort test, updated 7 existing tests
- `src/dashboard/match-approval.controller.spec.ts` — MODIFIED: import SortOrder from common-query.dto

**Frontend (pm-arbitrage-dashboard/):**
- `src/components/cells/PnlCell.tsx` — NEW
- `src/components/cells/StatusBadge.tsx` — NEW
- `src/components/cells/ExitTypeBadge.tsx` — NEW
- `src/components/cells/RiskRewardCell.tsx` — NEW
- `src/components/cells/index.ts` — NEW
- `src/hooks/useUrlTableState.ts` — NEW
- `src/components/DataTable.tsx` — MODIFIED: added urlStateKey prop + DataTableWithUrl/DataTableLayout
- `src/hooks/useDashboard.ts` — MODIFIED: added sortBy/order to useDashboardPositions
- `src/lib/utils.ts` — MODIFIED: added formatDecimal
- `src/pages/PositionsPage.tsx` — REWRITTEN: DataTable + URL state + server-side sorting
- `src/pages/MatchesPage.tsx` — REWRITTEN: useUrlTableState for all state
- `src/pages/PerformancePage.tsx` — REWRITTEN: DataTable + URL state
- `src/pages/PositionDetailPage.tsx` — MODIFIED: order history uses DataTable, shared cells
- `src/pages/StressTestPage.tsx` — MODIFIED: synthetic+vol tables use DataTable
- `src/api/generated/Api.ts` — REGENERATED
- `src/components/PositionsTable.tsx` — DELETED
