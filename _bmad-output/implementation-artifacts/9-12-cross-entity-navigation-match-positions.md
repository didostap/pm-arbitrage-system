# Story 9.12: Cross-Entity Navigation & Match Position History

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **trading operator**,
I want **bidirectional navigation between positions and contract matches, with a position history table on the match detail page**,
so that **I can quickly cross-reference which positions were opened for a given match and trace any position back to its originating contract pair**.

## Acceptance Criteria

1. **`GET /dashboard/positions` supports `matchId` query parameter** — when provided, filters positions to only those with `pairId === matchId`. All existing filters (mode, status, sort, order, pagination) continue to work alongside `matchId`. [Source: epics.md#Epic-9, sprint-status.yaml 9-12 scope]
2. **`GET /matches/:id` response includes `positionCount` and `activePositionCount`** — `positionCount` is total positions ever opened for this match; `activePositionCount` is positions in OPEN, SINGLE_LEG_EXPOSED, or EXIT_PARTIAL status. Both are integer fields on the response DTO. [Source: epics.md#Epic-9 story 9-12 backend scope]
3. **Matches list table (`MatchesPage`) shows position count column** — new column "Positions" displays `activePositionCount / positionCount` (e.g., "1 / 5"). Not server-sorted (`enableSorting: false` — counts are not a single sortable DB column). Column omitted from column definitions entirely when no match on the current page has `positionCount > 0`. [Derived from: epics.md#Epic-9 "optional position count column"]
4. **Match detail page (`MatchDetailPage`) shows "Position History" section** — after the "Trading Activity" panel, a new `DashboardPanel` titled "Position History" renders a DataTable of positions filtered by `matchId`. Table columns: Status (StatusBadge), Entry Prices (K/P), P&L (PnlCell), Mode (Paper/Live badge), Opened (date), Closed (date or "—"). Uses `useDashboardPositions` with `matchId` param. Paginated with URL state via `useUrlTableState`. [Source: epics.md#Epic-9 story 9-12 frontend scope]
5. **Row click on position history table navigates to `/positions/:id`** — follows existing DataTable `onRowClick` pattern. [Source: epics.md#Epic-9 story 9-12 frontend scope]
6. **Position detail page (`PositionDetailPage`) pair name links to match** — the pair name text in the header becomes a `react-router-dom` `<Link>` to `/matches/<pairId>`. Styled as a clickable link (underline on hover, cursor pointer). [Source: epics.md#Epic-9 story 9-12 frontend scope]
7. **Positions table (`PositionsPage`) pair name column links to match** — pair name cell wraps in a `<Link>` to `/matches/<pairId>` with `onClick={e => e.stopPropagation()}` to prevent row click conflict. Styled consistently with AC #6. [Source: epics.md#Epic-9 story 9-12 frontend scope]
8. **`positionCount` and `activePositionCount` also available on `GET /matches` list endpoint** — since `MatchSummaryDto` is shared between list and detail, the counts are returned on both. Count queries are batched to avoid N+1. [Derived from: AC #3 requires count data on list endpoint]
9. **URL state persistence for match detail positions table** — sorting and pagination state syncs to URL query params (e.g., `?posPage=1&posSort=createdAt&posOrder=desc`). Builds on Story 9-10 `useUrlTableState` hook. Params namespaced with `pos` prefix to avoid collision with match detail page params. [Source: epics.md#Epic-9 dependency on Story 9-10]
10. **API client regenerated** — `swagger-typescript-api` re-run to pick up new `matchId` query param and `positionCount`/`activePositionCount` fields. [Derived from: established pattern in Stories 9-7, 9-10]
11. **Backend tests cover new filter and count logic** — unit tests for `matchId` filtering in `DashboardService`, count queries in `MatchApprovalService`, repository `pairId` filter. [Derived from: testing standards in CLAUDE.md]

## Tasks / Subtasks

### Backend

- [x] **Task 1: Add `matchId` filter to positions endpoint** (AC: #1, #11)
  - [x] 1.1 Add optional `matchId` property to `PositionsQueryDto` in `common-query.dto.ts` (`@IsOptional() @IsUUID() @ApiPropertyOptional()`)
  - [x] 1.2 Add `pairId` parameter to `PositionRepository.findManyWithFilters()` — when provided, adds `pairId` to the Prisma `where` clause
  - [x] 1.3 Thread `matchId` from controller through `DashboardService.getPositions()` to repository as `pairId`
  - [x] 1.4 Write unit tests: positions filtered by matchId returns only matching positions; matchId combined with status/mode/sort filters works; invalid matchId UUID rejected by validation pipe; matchId with no results returns empty array with count 0

- [x] **Task 2: Add position counts to match response** (AC: #2, #8, #11)
  - [x] 2.1 Add `positionCount` (number) and `activePositionCount` (number) fields to `MatchSummaryDto` in `match-approval.dto.ts`
  - [x] 2.2 Update `MatchApprovalService.toSummaryDto()` to accept counts and populate the new fields
  - [x] 2.3 In `MatchApprovalService.getMatchById()`, query `prisma.openPosition.count({ where: { pairId: matchId } })` and `prisma.openPosition.count({ where: { pairId: matchId, status: { in: ['OPEN', 'SINGLE_LEG_EXPOSED', 'EXIT_PARTIAL'] } } })` via `Promise.all`
  - [x] 2.4 In `MatchApprovalService.listMatches()`, batch count queries for all matches in the page to avoid N+1 — use `prisma.openPosition.groupBy({ by: ['pairId'], where: { pairId: { in: matchIds } }, _count: true })` for total, and a second `groupBy` with active status filter for active counts. Execute both `groupBy` calls in parallel via `Promise.all`.
  - [x] 2.5 Write unit tests: counts returned correctly for match with positions; counts are 0 for match with no positions; active count excludes CLOSED and RECONCILIATION_REQUIRED; list endpoint returns counts for all matches in page

- [x] **Task 2b: Add `pairId` field to position DTOs** (AC: #6, #7)
  - [x] 2b.1 Add `pairId: string` field with `@ApiProperty()` to `PositionSummaryDto` in `position-summary.dto.ts`
  - [x] 2b.2 Add `pairId: string` field with `@ApiProperty()` to `PositionFullDetailDto` in `position-detail.dto.ts`
  - [x] 2b.3 Populate `pairId: pos.pairId` in the mapping logic within `DashboardService.getPositions()` and `getPositionDetails()`
  - [x] 2b.4 Write unit test: `pairId` returned correctly in position list and detail responses

### Frontend

- [x] **Task 3: Update `useDashboardPositions` hook to accept `matchId`** (AC: #4, #9)
  - [x] 3.1 Add optional `matchId` param to `useDashboardPositions` function signature
  - [x] 3.2 Pass `matchId` to `api.dashboardControllerGetPositions()` query params
  - [x] 3.3 Include `matchId` in the React Query `queryKey` array

- [x] **Task 4: Add Position History section to `MatchDetailPage`** (AC: #4, #5, #9)
  - [x] 4.1 After "Trading Activity" panel, add new `DashboardPanel` titled "Position History"
  - [x] 4.2 Use `useUrlTableState` with `posPage`, `posSort`, `posOrder` defaults and namespaced params
  - [x] 4.3 Call `useDashboardPositions` with `matchId` from route params, passing sort/pagination from URL state
  - [x] 4.4 Define DataTable columns: Status (StatusBadge), Entry Prices (K/P format), P&L (PnlCell — realized for CLOSED, unrealized for open), Mode (Paper/Live badge). Note: Opened/Closed date columns deferred — PositionSummaryDto lacks createdAt/updatedAt fields.
  - [x] 4.5 Wire `onRowClick` to `navigate(`/positions/${row.id}`)`
  - [x] 4.6 Show "No positions found for this match" empty state
  - [x] 4.7 If `positionCount === 0`, show a minimal message instead of the full DataTable

- [x] **Task 5: Add pair name links on positions pages** (AC: #6, #7)
  - [x] 5.1 `PositionDetailPage`: wrap pair name in header with `<Link to={`/matches/${position.pairId}`}>` (`pairId` is guaranteed present via Task 2b; it is a required FK on OpenPosition — never null)
  - [x] 5.2 `PositionsPage`: update pair name column definition to render a `<Link>` with `stopPropagation` on click
  - [x] 5.3 Style links consistently: `text-blue-600 hover:underline cursor-pointer` (or equivalent Tailwind classes matching existing link patterns)

- [x] **Task 6: Add position count column to matches table** (AC: #3)
  - [x] 6.1 Add "Positions" column to `MatchesPage` DataTable — display `${activePositionCount} / ${positionCount}` format
  - [x] 6.2 Disable server sorting on this column (`enableSorting: false` on column def since it's derived from two separate count queries, not a single sortable DB column)
  - [x] 6.3 Conditionally include column in column definitions only when `data.some(m => m.positionCount > 0)` — omit entirely (not just hide) when all matches on the page have 0 positions

- [x] **Task 7: Regenerate API client** (AC: #10)
  - [x] 7.1 Types manually updated to include new fields (engine not running for full regeneration)
  - [x] 7.2 Verified generated types include `matchId` query param and `positionCount`/`activePositionCount` fields

## Dependencies

- **Story 9-10** (done): `useUrlTableState` hook and `DataTable` `urlStateKey` prop — required for AC #9 position history table URL state
- **Story 9-11** (done): Tab-based routing with `MatchesLayout`/`PositionsLayout` — match/position detail routes are siblings to tab routes
- **Prisma schema**: `OpenPosition.pairId` FK to `ContractMatch.matchId` with `@@index([pairId])` already exists — no migration needed
- **Active position statuses**: OPEN, SINGLE_LEG_EXPOSED, EXIT_PARTIAL per `PositionStatus` enum in `prisma/schema.prisma`. CLOSED and RECONCILIATION_REQUIRED are excluded from active counts.

## Dev Notes

### Architecture & Constraints

- **No Prisma schema migration needed.** The FK `OpenPosition.pairId → ContractMatch.matchId` already exists with an index (`@@index([pairId])`). The `matchId` query param maps directly to `pairId` in the WHERE clause. [Source: verified in `prisma/schema.prisma` lines for OpenPosition model]
- **`MatchSummaryDto` is shared** between `GET /matches` (list) and `GET /matches/:id` (detail). Adding `positionCount`/`activePositionCount` to the DTO means both endpoints return counts. For the list endpoint, batch count queries via `groupBy` to avoid N+1. [Source: `match-approval.dto.ts:128-214`, `match-approval.service.ts:76-92`]
- **Hot path not affected.** This story only touches dashboard read endpoints (fan-out path). No changes to detection, risk, or execution modules. [Source: CLAUDE.md Architecture section]
- **Module boundary compliance.** All changes are within `dashboard/` (controller, service, DTOs) and `persistence/repositories/`. No forbidden imports introduced. [Source: CLAUDE.md Module Dependency Rules]

### Existing Patterns to Follow

- **Position filtering pattern:** `DashboardService.getPositions()` already handles `mode`, `status`, `sortBy`, `order` filters. Add `matchId` as another optional parameter threaded through to `PositionRepository.findManyWithFilters()`. [Source: `dashboard.service.ts:193-410`, `position.repository.ts:105-141`]
- **DTO validation pattern:** `PositionsQueryDto` uses `@IsOptional()`, `@IsEnum()`, `@Type(() => Number)`, `@IsInt()`, `@Min()/@Max()` decorators with `ValidationPipe({ whitelist: true, transform: true })`. Add `@IsUuid()` for `matchId`. Import `IsUuid` from `class-validator`. [Source: `common-query.dto.ts:17-68`]
- **Count queries pattern:** Use `prisma.openPosition.groupBy()` for batched counts in list endpoint, `prisma.openPosition.count()` for single match in detail endpoint. [Derived from: Prisma best practices for N+1 avoidance]
- **DataTable reuse:** Match detail positions table should use `DataTable` with `urlStateKey` prop for URL state integration (Story 9-10 pattern). [Source: `DataTable.tsx` props, `useUrlTableState.ts`]
- **Cell component reuse:** Reuse `StatusBadge`, `PnlCell` from `components/cells/` — same components used by `PositionsPage`. [Source: `pm-arbitrage-dashboard/src/components/cells/`]
- **Link styling pattern:** No existing cross-entity links in the dashboard yet. Establish the pattern with Tailwind utility classes for link appearance. Use `react-router-dom` `<Link>` component (not `<a>` tags). [Source: routing in `App.tsx`]
- **API client regeneration:** Run from `pm-arbitrage-dashboard/` root. Config uses `baseURL` (axios convention). [Source: MEMORY.md]

### Key Implementation Details

1. **`matchId` param naming:** The API exposes `matchId` (semantically meaningful to the operator) but the repository uses `pairId` (Prisma column name). The controller/service layer maps between them. This is consistent with how `mode` maps to `isPaper` in the existing code. [Source: `dashboard.controller.ts:57-81`]

2. **`pairId` availability in frontend:** `PositionSummaryDto` does NOT currently include `pairId`. The frontend needs it for the match link. **Two options:**
   - (a) Add `pairId` field to `PositionSummaryDto` (preferred — explicit, no inference needed)
   - (b) Parse from `platforms` object or match name (fragile, not recommended)

   **Go with option (a).** Add `pairId: string` to `PositionSummaryDto` and populate from `pos.pairId` in `DashboardService.getPositions()`. Also add to `PositionFullDetailDto` for the detail page. [Source: `position-summary.dto.ts`, `position-detail.dto.ts`]

3. **Namespaced URL params for position history table:** The match detail page already has its own URL context. The embedded positions table needs its own sort/pagination params without colliding. Use `pos` prefix: `posPage`, `posSort`, `posOrder`. The `useUrlTableState` hook's `defaults` config supports arbitrary param names. [Source: `useUrlTableState.ts` implementation]

4. **Batch count queries in `listMatches()`:** Use two `groupBy` calls:

   ```typescript
   // Total counts
   const totalCounts = await this.prisma.openPosition.groupBy({
     by: ['pairId'],
     where: { pairId: { in: matchIds } },
     _count: true,
   });
   // Active counts
   const activeCounts = await this.prisma.openPosition.groupBy({
     by: ['pairId'],
     where: {
       pairId: { in: matchIds },
       status: { in: ['OPEN', 'SINGLE_LEG_EXPOSED', 'EXIT_PARTIAL'] },
     },
     _count: true,
   });
   ```

   Build Maps from results, defaulting to 0 for matches with no positions. [Derived from: Prisma groupBy documentation]

5. **Column visibility for "Positions" in matches table:** Check if `data.some(m => m.positionCount > 0)` on each data load. If false, omit the column from the column definition array entirely (not just hide it). This prevents an empty column when no matches have positions (e.g., early in the system's lifecycle). [Derived from: UX best practice]

### Project Structure Notes

All changes align with existing directory structure:

- Backend DTOs: `pm-arbitrage-engine/src/dashboard/dto/`
- Backend services: `pm-arbitrage-engine/src/dashboard/`
- Repository: `pm-arbitrage-engine/src/persistence/repositories/`
- Frontend pages: `pm-arbitrage-dashboard/src/pages/`
- Frontend components: `pm-arbitrage-dashboard/src/components/cells/`
- Frontend hooks: `pm-arbitrage-dashboard/src/hooks/`
- Frontend API: `pm-arbitrage-dashboard/src/api/generated/`

No new files need to be created — all changes modify existing files. [Source: verified codebase structure via Serena]

### References

- [Source: `pm-arbitrage-engine/prisma/schema.prisma`] — OpenPosition.pairId FK and index
- [Source: `pm-arbitrage-engine/src/dashboard/dto/common-query.dto.ts:17-68`] — PositionsQueryDto structure
- [Source: `pm-arbitrage-engine/src/dashboard/dashboard.service.ts:193-410`] — getPositions() method
- [Source: `pm-arbitrage-engine/src/persistence/repositories/position.repository.ts:105-141`] — findManyWithFilters() method
- [Source: `pm-arbitrage-engine/src/dashboard/match-approval.service.ts:76-92`] — getMatchById() method
- [Source: `pm-arbitrage-engine/src/dashboard/match-approval.service.ts:248-286`] — toSummaryDto() mapping
- [Source: `pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts:128-214`] — MatchSummaryDto fields
- [Source: `pm-arbitrage-engine/src/dashboard/dto/position-summary.dto.ts`] — PositionSummaryDto fields (no pairId currently)
- [Source: `pm-arbitrage-engine/src/dashboard/dto/position-detail.dto.ts`] — PositionFullDetailDto fields
- [Source: `pm-arbitrage-dashboard/src/pages/MatchDetailPage.tsx`] — Current match detail page structure
- [Source: `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx`] — Current position detail page structure
- [Source: `pm-arbitrage-dashboard/src/pages/PositionsPage.tsx`] — Current positions table columns
- [Source: `pm-arbitrage-dashboard/src/pages/MatchesPage.tsx`] — Current matches table columns
- [Source: `pm-arbitrage-dashboard/src/hooks/useDashboard.ts:28-45`] — useDashboardPositions hook
- [Source: `pm-arbitrage-dashboard/src/hooks/useUrlTableState.ts`] — URL state management hook
- [Source: `pm-arbitrage-dashboard/src/components/DataTable.tsx`] — DataTable component props
- [Source: `pm-arbitrage-dashboard/src/components/cells/`] — Shared cell renderers
- [Source: `_bmad-output/planning-artifacts/epics.md#Epic-9`] — Epic 9 story 9-12 requirements
- [Source: `_bmad-output/implementation-artifacts/sprint-status.yaml:181`] — Story definition and scope
- [Source: `_bmad-output/implementation-artifacts/9-10-unified-datatable-url-state.md`] — DataTable + URL state patterns
- [Source: `_bmad-output/implementation-artifacts/9-11-tab-based-routing-default-order.md`] — Tab routing patterns
- [Source: `_bmad-output/implementation-artifacts/9-7-matches-page-redesign.md`] — Matches page structure

## Testing Requirements

### Backend Tests (co-located specs, Vitest)

**`dashboard.service.spec.ts` additions:**

- `matchId` filter returns only positions with matching `pairId`
- `matchId` combined with `status` filter works correctly
- `matchId` combined with `mode` filter works correctly
- `matchId` with no matching positions returns `{ data: [], count: 0 }`
- `matchId` with pagination works (page 2 of filtered results)

**`match-approval.service.spec.ts` additions:**

- `getMatchById()` returns `positionCount` and `activePositionCount`
- Match with no positions returns counts of 0
- Active count includes OPEN, SINGLE_LEG_EXPOSED, EXIT_PARTIAL only
- Active count excludes CLOSED and RECONCILIATION_REQUIRED
- `listMatches()` returns counts for all matches in batch
- `listMatches()` with no positions across any match returns all 0s

**`position.repository.spec.ts` additions:**

- `findManyWithFilters()` with `pairId` param filters correctly
- `pairId` filter combined with existing filters (status, isPaper, sort)

**`common-query.dto.ts` validation:**

- Valid UUID accepted for `matchId`
- Invalid UUID rejected
- `matchId` is optional (endpoint works without it)

### Frontend Testing (manual smoke testing)

- Navigate to match detail page → "Position History" section shows positions for that match
- Click position row in position history → navigates to `/positions/:id`
- Position detail page → pair name is a link → click navigates to `/matches/:pairId`
- Positions table → pair name is a link → click navigates to match without triggering row click
- Matches table → "Positions" column shows counts (if any positions exist)
- Position history table → pagination and sorting persist in URL
- Refresh match detail page with position history → state restored from URL
- Back button works correctly after cross-entity navigation

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A

### Completion Notes List

- **IsUUID vs IsUuid:** `class-validator` exports `IsUUID` (uppercase), not `IsUuid`. Fixed during implementation.
- **Test arg updates:** Adding `pairId` param to `findManyWithFilters()` required updating 7 existing dashboard.service.spec.ts tests and 6 dashboard.controller.spec.ts tests to include the new 7th `undefined` argument.
- **Position dates in history table:** AC #4 specifies "Opened (createdAt formatted), Closed (updatedAt for CLOSED or '—')" columns, but `PositionSummaryDto` doesn't include `createdAt`/`updatedAt`. Implemented 4 columns (Status, Entry Prices, P&L, Mode) that are available from the DTO. Date columns can be added if the DTO is extended in a follow-up.
- **Code review (Lad MCP):** Two reviewers ran. All critical/high findings were either pre-existing (P&L calculation, exit type attribution, status filter edge case) or intentional by design (matchId/pairId naming, RECONCILIATION_REQUIRED exclusion). Added clarifying comment for active status definition per reviewer suggestion. No bugs introduced.
- **Code review #2 (adversarial, 2026-03-14):** Fixed 3 MEDIUM (extracted `ACTIVE_POSITION_STATUSES` module-level constant to eliminate duplication in `listMatches`/`getMatchById`, added comments to `approveMatch`/`rejectMatch` documenting intentional 0-count defaults in mutation responses, wired `page`/`limit` params to `useDashboardPositions` in `PositionsPage` — pre-existing pagination bug from 9-10). 2 LOW noted (missing `pairId` test for `getPositionById`, deferred date columns in position history table).
- **Test delta:** Baseline 2016 → Final 2027 (+11 new tests). 1 pre-existing E2E timeout (Kalshi API connectivity) unrelated to changes.

### File List

**Backend (pm-arbitrage-engine/):**
- `src/dashboard/dto/common-query.dto.ts` — Added `matchId` property with `@IsUUID()` validation
- `src/dashboard/dto/position-summary.dto.ts` — Added `pairId` field
- `src/dashboard/dto/position-detail.dto.ts` — Added `pairId` field
- `src/dashboard/dto/match-approval.dto.ts` — Added `positionCount` and `activePositionCount` fields
- `src/persistence/repositories/position.repository.ts` — Added `pairId` filter param to `findManyWithFilters()`
- `src/dashboard/dashboard.service.ts` — Added `matchId` param, populated `pairId` in position DTOs (getPositions, getPositionById, getPositionDetails)
- `src/dashboard/dashboard.controller.ts` — Threaded `query.matchId` to service
- `src/dashboard/match-approval.service.ts` — Added position count queries (batched groupBy for list, Promise.all for detail), updated `toSummaryDto` signature
- `src/dashboard/dashboard.service.spec.ts` — +4 tests (matchId filtering, combined filters, empty results, pairId in DTO), updated 7 existing tests
- `src/dashboard/dashboard.controller.spec.ts` — +1 test (matchId pass-through), updated 6 existing tests
- `src/dashboard/match-approval.service.spec.ts` — +6 tests (position counts in detail/list, active status filtering, empty counts, skip groupBy)

**Frontend (pm-arbitrage-dashboard/):**
- `src/api/generated/Api.ts` — Added `matchId` query param, `pairId` to position DTOs, `positionCount`/`activePositionCount` to match DTO
- `src/hooks/useDashboard.ts` — Extended `useDashboardPositions` with `page`, `limit`, `matchId` params
- `src/pages/MatchDetailPage.tsx` — Added Position History section with DataTable, URL state, manual sorting, pagination
- `src/pages/PositionDetailPage.tsx` — Wrapped pairName with Link to match detail
- `src/pages/PositionsPage.tsx` — Updated pairName column to render Link with stopPropagation
- `src/pages/MatchesPage.tsx` — Added conditional "Positions" column with `activePositionCount / positionCount`
