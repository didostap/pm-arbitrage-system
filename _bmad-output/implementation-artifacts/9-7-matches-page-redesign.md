# Story 9.7: Matches Page Redesign & Data Alignment

Status: done

## Story

As an operator,
I want the dashboard matches page redesigned as a proper table with all contract match fields visible, separate status views, cluster filtering, and a match detail page,
So that I can efficiently review, filter, and inspect contract matches with full operational context including cluster assignments, resolution dates, and trading activity.

## Acceptance Criteria

1. **Given** the `contract_matches` table has 22+ fields including cluster, resolution date, categories, primary leg, and trading activity, **when** the operator views the matches page, **then** all fields are accessible — key columns in the table view, full record on the detail page, **and** the card-based layout is replaced with a structured table. [Source: epics.md#Story-9.7, sprint-change-proposal-2026-03-13b.md#Section-1]

2. **Given** the operator wants to view matches by approval status, **when** they navigate the matches page, **then** Pending, Approved, and All are presented as separate tabbed views (not a single consolidated list). [Source: epics.md#Story-9.7, sprint-change-proposal-2026-03-13b.md#Section-4.4]

3. **Given** the operator wants to filter by correlation cluster, **when** they select a cluster from the filter dropdown, **then** the table shows only matches belonging to that cluster, **and** the filter works across all status tabs. [Source: epics.md#Story-9.7, sprint-change-proposal-2026-03-13b.md#Section-4.4]

4. **Given** the operator clicks on a match row in the table, **when** the detail page loads at `/matches/:id`, **then** the full record is displayed with all fields organized in sections: contract pair details, resolution data, trading activity, operator review status. [Source: epics.md#Story-9.7, sprint-change-proposal-2026-03-13b.md#Section-4.5]

5. **Given** Epic 8 (semantic matching) is complete, **when** the matches page renders, **then** no dead code references Epic 8 as future work (e.g., `"Knowledge Base: Coming in Epic 8"` in MatchCard.tsx:67, `"Epic 8 adds semantic matching"` in MatchesPage.tsx:79), **and** the deleted `MatchCard` component is replaced by table rows. [Source: epics.md#Story-9.7]

6. **Given** the backend DTO is updated, **when** the API returns match data, **then** `MatchSummaryDto` includes all 8 previously missing fields: `polymarketRawCategory`, `kalshiRawCategory`, `firstTradedTimestamp`, `totalCyclesTraded`, `primaryLeg`, `resolutionDate`, `resolutionCriteriaHash`, and resolved `cluster` object (`{ id, name, slug } | null`), **and** the generated API client is regenerated to reflect the updated types. [Source: epics.md#Story-9.7, sprint-change-proposal-2026-03-13b.md#Section-4.1]

7. **Given** the backend clusters endpoint exists, **when** the frontend requests `GET /matches/clusters`, **then** all `CorrelationCluster` records are returned as `{ id, name, slug }[]` to populate the cluster filter dropdown. [Source: sprint-change-proposal-2026-03-13b.md#Section-4.3, user disambiguation Q3→option (b)]

8. **Given** the dashboard needs multiple tabular data views (positions, matches, future pages), **when** the `DataTable` component is used, **then** it provides a generic, reusable wrapper around `@tanstack/react-table` v8 with built-in sorting indicators, pagination controls, loading/empty states, and clickable row navigation. [Source: user disambiguation Q2→option (a)]

## Tasks / Subtasks

### Backend (pm-arbitrage-engine)

- [x] **Task 1: Extend `MatchSummaryDto` with 8 missing fields** (AC: #6)
  - [x]Add `ClusterSummaryDto` class (`id`, `name`, `slug`) with Swagger decorators
  - [x]Add 8 fields to `MatchSummaryDto`: `polymarketRawCategory` (string|null), `kalshiRawCategory` (string|null), `firstTradedTimestamp` (string|null, ISO 8601), `totalCyclesTraded` (number), `primaryLeg` (string|null), `resolutionDate` (string|null, ISO 8601), `resolutionCriteriaHash` (string|null), `cluster` (ClusterSummaryDto|null)
  - [x]Update `toSummaryDto()` in `match-approval.service.ts` to map all 8 new fields
  - [x]Add `include: { cluster: true }` to ALL Prisma queries in the service — specifically: `listMatches()` `findMany`, `getMatchById()` `findUnique`, `approveMatch()` `updateMany`+`findUnique`, `rejectMatch()` `findUnique`+`update`
  - [x]Write/update spec tests for the new DTO mapping in `match-approval.service.spec.ts`

- [x] **Task 2: Add `clusterId` query parameter to list endpoint** (AC: #3)
  - [x]Add optional `clusterId` field (string, `@IsUUID()`) to `MatchListQueryDto`
  - [x]Extend `listMatches()` service method signature to accept `clusterId`
  - [x]Add Prisma WHERE clause: `clusterId: clusterId ?? undefined`
  - [x]Pass `query.clusterId` from controller to service
  - [x]Write spec test for cluster filtering

- [x] **Task 3: Add `GET /matches/clusters` endpoint** (AC: #7)
  - [x]Add `ClusterListResponseDto` (`data: ClusterSummaryDto[]`, `count`, `timestamp`)
  - [x]Add `listClusters()` method to `MatchApprovalService`: `prisma.correlationCluster.findMany({ orderBy: { name: 'asc' } })`
  - [x]Add `@Get('clusters')` endpoint to `MatchApprovalController` — **must be declared BEFORE the `@Get(':id')` route** to avoid NestJS treating "clusters" as an `:id` param
  - [x]Write spec tests for the clusters endpoint

### Frontend (pm-arbitrage-dashboard)

- [x] **Task 4: Install shadcn tabs component** (AC: #2)
  - [x]Run `npx shadcn@latest add tabs`
  - [x]Verify `src/components/ui/tabs.tsx` is created

- [x] **Task 5: Create generic reusable `DataTable` component** (AC: #8)
  - [x]Create `src/components/DataTable.tsx` wrapping `@tanstack/react-table` v8
  - [x]Props: `columns: ColumnDef<TData, TValue>[]`, `data: TData[]`, `isLoading: boolean`, `emptyMessage?: string`, `onRowClick?: (row: TData) => void`, `pagination?: { page, totalPages, onPageChange }`, `sorting` state (optional, externally controlled or internal)
  - [x]Render: shadcn `<Table>` components, sort direction indicators (↑/↓) on sortable column headers, loading skeleton row, empty state row, pagination controls (Previous/Page X of Y/Next)
  - [x]Pattern reference: extract from existing `PositionsTable.tsx` (lines 237-316) — the header/body/sorting/loading/empty/row-click rendering is nearly identical boilerplate

- [x] **Task 6: Rewrite `MatchesPage.tsx` with tabbed table views** (AC: #1, #2, #3)
  - [x]Replace Button-toggle filters with shadcn `<Tabs>` component (Pending/Approved/All)
  - [x]Add cluster filter `<select>` dropdown above the table, populated from `useMatchClusters()` hook
  - [x]Use `DataTable` component with match-specific column definitions
  - [x]Table columns: Status badge, Polymarket description (truncated), Kalshi description (truncated), Confidence %, Cluster name, Resolution Date, Primary Leg, Created date, Actions (Approve/Reject for pending)
  - [x]Clickable rows navigate to `/matches/:id`
  - [x]Retain pagination (server-side, page/limit via hook)
  - [x]Reset page to 1 on tab or cluster filter change

- [x] **Task 7: Create `MatchDetailPage.tsx`** (AC: #4)
  - [x]Create `src/pages/MatchDetailPage.tsx`
  - [x]Use `useParams<{ id: string }>()` + `useMatchDetail(id)` hook
  - [x]Sections: Header (status badge, match ID, confidence, cluster badge), Contract Pair (side-by-side Polymarket/Kalshi with descriptions, contract IDs, CLOB token ID, raw categories), Resolution (resolution date, criteria hash, per-platform outcomes, divergence status/notes, timestamp), Trading Activity (first traded, total cycles, primary leg), Operator Review (approval status, timestamp, rationale), Actions (Approve/Reject buttons if pending — reuse `MatchApprovalDialog`)
  - [x]Back button navigating to `/matches`
  - [x]Follow `PositionDetailPage.tsx` layout patterns: loading spinner, 404/error message with back link, `DashboardPanel` sections

- [x] **Task 8: Add hooks and update routing** (AC: #1, #3, #4, #7)
  - [x]Add `useMatchClusters()` hook: query key `['matches', 'clusters']`, calls `matchApprovalControllerListClusters()`, staleTime 60s
  - [x]Add `useMatchDetail(id)` hook: query key `['matches', 'detail', id]`, calls `matchApprovalControllerGetMatchById(id)`, staleTime 10s
  - [x]Update `useDashboardMatches` to accept optional `clusterId` parameter
  - [x]Add `<Route path="/matches/:id" element={<MatchDetailPage />} />` to `App.tsx` — `/matches/:id` and `/matches` are distinct route patterns in React Router v7, order doesn't matter

- [x] **Task 9: Delete `MatchCard.tsx` and clean up dead code** (AC: #5)
  - [x]Delete `src/components/MatchCard.tsx`
  - [x]Remove all imports of `MatchCard` (only in `MatchesPage.tsx`)
  - [x]Remove dead Epic 8 references in MatchesPage empty state text. Replace pending empty state with: `"No pending contract matches."` and general empty state with: `"No contract matches found."`

- [x] **Task 10: Regenerate API client** (AC: #6)
  - [x]Start the engine (`pnpm start:dev` in pm-arbitrage-engine)
  - [x]Run `cd pm-arbitrage-dashboard && pnpm generate-api`
  - [x]Verify the generated `Api.ts` includes: updated `MatchSummaryDto` (25 fields), `ClusterSummaryDto`, `ClusterListResponseDto`, `clusterId` query param on list endpoint, `listClusters` method
  - [x]**NOTE:** The current generated client is also missing 5 resolution fields (`polymarketResolution`, `kalshiResolution`, `resolutionTimestamp`, `resolutionDiverged`, `divergenceNotes`) that already exist in the backend DTO — regeneration will pick these up too

- [x] **Task 11: Update `MatchApprovalDialog.tsx` with new context fields** (AC: #4)
  - [x]Show cluster badge (from `match.cluster?.name`, colored via slug), confidence score, and resolution date in the dialog between the contract pair display and the rationale textarea
  - [x]Minor enhancement — the dialog already works, just surface more context for the operator's decision. Use `Badge` for cluster, format confidence as `"85%"`, format resolution date with `toLocaleDateString()`

## Dev Notes

### Architecture Compliance

**Module boundaries — hard constraints:**
- Backend changes are contained to `src/dashboard/` (controller, service, DTOs). No cross-module imports needed. [Source: CLAUDE.md#Module-Dependency-Rules]
- The `CorrelationCluster` Prisma model is accessed via `PrismaService` in the dashboard service — this is the established pattern (dashboard bypasses repository layer, uses PrismaService directly). [Source: Serena memory `dashboard/module_deep_dive` §11]
- Frontend changes are contained to `pm-arbitrage-dashboard/` — separate git repo, separate commits required. [Source: CLAUDE.md#Repository-Structure]

**API response format — must follow:**
```typescript
// List: { data: T[], count: number, page?: number, limit?: number, timestamp: string }
// Detail: { data: T, timestamp: string }
```
[Source: CLAUDE.md#API-Response-Format]

### Backend Implementation Details

**MatchSummaryDto — full field list after this story (25 fields):**
```
matchId, polymarketContractId, polymarketClobTokenId, kalshiContractId,
polymarketDescription, kalshiDescription, operatorApproved, operatorApprovalTimestamp,
operatorRationale, confidenceScore, polymarketResolution, kalshiResolution,
resolutionTimestamp, resolutionDiverged, divergenceNotes, createdAt, updatedAt,
+ polymarketRawCategory, kalshiRawCategory, firstTradedTimestamp, totalCyclesTraded,
  primaryLeg, resolutionDate, resolutionCriteriaHash, cluster
```

**Prisma `include` for cluster relation:**
```typescript
// ContractMatch has: clusterId String? + cluster CorrelationCluster? @relation(...)
// CorrelationCluster has: id, name, slug, description, createdAt, updatedAt
// Map to: { id: string; name: string; slug: string } | null
```
[Source: prisma/schema.prisma lines 66-78, 108-131]

**CRITICAL — `GET /matches/clusters` route ordering:**
NestJS evaluates routes top-to-bottom. `@Get('clusters')` MUST be declared before `@Get(':id')` in the controller, otherwise `"clusters"` will be parsed as a match ID and return 404. The current controller has `@Get()` first then `@Get(':id')` — insert the new route between them.
[Source: match-approval.controller.ts lines 44-84]

**`toSummaryDto()` mapping for new fields:**
```typescript
// DateTime? → string | null: field?.toISOString() ?? null
// String? → string | null: field ?? null
// Int with @default(0) → number: field (already a number)
// Relation → nested object | null: match.cluster ? { id, name, slug } : null
```
Current mapping pattern at `match-approval.service.ts:221-242`.

**Note on `dto/index.ts`:** `src/dashboard/dto/index.ts` already has `export * from './match-approval.dto'` — `ClusterSummaryDto` and `ClusterListResponseDto` will be auto-exported. No manual export needed.

### Frontend Implementation Details

**Generic `DataTable<TData>` component design:**

Extract the rendering boilerplate from `PositionsTable.tsx` (lines 254-314) into a generic component. The existing pattern is:
1. `useReactTable()` with `getCoreRowModel`, `getSortedRowModel`, sorting state
2. Render header groups with sort indicators
3. Loading row, empty row, data rows
4. Clickable rows with `cursor-pointer` class + `onClick` handler

The `DataTable` should accept:
- `columns` + `data` + `isLoading` (required)
- `emptyMessage` (default: "No data")
- `onRowClick` (optional — enables cursor-pointer and click handler)
- `pagination` object (optional — renders Previous/Page X of Y/Next controls)
- Initial sorting state (optional)

After creating `DataTable`, the `PositionsTable` can optionally be refactored to use it — but that is **out of scope** for this story. Don't refactor PositionsTable. Just create DataTable and use it for the matches page.

**`@tanstack/react-table` v8 pattern (already installed, version 8.21.3):**
```typescript
import { useReactTable, getCoreRowModel, getSortedRowModel, flexRender, createColumnHelper } from '@tanstack/react-table';
```
See `PositionsTable.tsx` for the exact import pattern and usage. [Source: pm-arbitrage-dashboard/src/components/PositionsTable.tsx]

**shadcn Tabs component:**
```bash
npx shadcn@latest add tabs
```
This creates `src/components/ui/tabs.tsx` with `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`. Use `onValueChange` to sync tab state with the query params.

**Routing — React Router v7:**
The app uses `<BrowserRouter>` with `<Routes>/<Route>`. The detail page pattern is established by `PositionDetailPage`:
```tsx
<Route path="/matches/:id" element={<MatchDetailPage />} />
```
Use `useParams<{ id: string }>()` + `useNavigate()`.
In React Router v7 with path-based matching, `/matches/:id` will NOT conflict with `/matches` — they are distinct routes. Place the detail route alongside the list route (order doesn't matter for distinct path patterns in RR v7).
[Source: pm-arbitrage-dashboard/src/App.tsx lines 31-35]

**API client regeneration command:**
```bash
cd pm-arbitrage-dashboard && pnpm generate-api
```
Requires the engine running at `http://127.0.0.1:8080`. [Source: pm-arbitrage-dashboard/package.json "generate-api" script]

**Generated client is currently stale:**
The generated `Api.ts` `MatchSummaryDto` has only 12 fields — it's missing 5 resolution fields that already exist in the backend DTO (`polymarketResolution`, `kalshiResolution`, `resolutionTimestamp`, `resolutionDiverged`, `divergenceNotes`). Regeneration will pick up all 13 missing fields (5 existing + 8 new).
[Source: pm-arbitrage-dashboard/src/api/generated/Api.ts lines 258-273 vs pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts lines 87-123]

**Cluster filter dropdown — populate from dedicated endpoint:**
Use the `useMatchClusters()` hook to fetch all clusters. Show a `<select>` (or use the shadcn `select` component if installed — check first, otherwise a plain `<select>` styled with Tailwind is fine). Include an "All Clusters" default option with value `""` (empty string). In the hook, convert empty string to `undefined` so no `clusterId` query param is sent to the API.

### File Manifest

**Engine (pm-arbitrage-engine) — Modify:**
| File | Change |
|---|---|
| `src/dashboard/dto/match-approval.dto.ts` | Add `ClusterSummaryDto`, add 8 fields to `MatchSummaryDto`, add `clusterId` to `MatchListQueryDto`, add `ClusterListResponseDto` |
| `src/dashboard/match-approval.service.ts` | Extend `toSummaryDto()`, add `include: { cluster: true }`, accept `clusterId` in `listMatches()`, add `listClusters()` |
| `src/dashboard/match-approval.controller.ts` | Add `@Get('clusters')` endpoint (before `@Get(':id')`), pass `clusterId` to service |
| `src/dashboard/match-approval.service.spec.ts` | Add tests for new DTO fields, cluster filtering, clusters endpoint |
| `src/dashboard/match-approval.controller.spec.ts` | Add test for clusters endpoint routing |

**Dashboard (pm-arbitrage-dashboard) — Modify:**
| File | Change |
|---|---|
| `src/components/ui/tabs.tsx` | NEW — shadcn tabs component (auto-generated) |
| `src/components/DataTable.tsx` | NEW — generic reusable table component |
| `src/pages/MatchesPage.tsx` | REWRITE — tabs + cluster filter + DataTable |
| `src/pages/MatchDetailPage.tsx` | NEW — full match detail view |
| `src/components/MatchApprovalDialog.tsx` | MINOR UPDATE — show cluster/confidence/resolution in header |
| `src/hooks/useDashboard.ts` | ADD hooks: `useMatchClusters`, `useMatchDetail`; UPDATE `useDashboardMatches` with `clusterId` param |
| `src/App.tsx` | ADD `/matches/:id` route + import |
| `src/api/generated/Api.ts` | REGENERATE — 13 new fields + cluster types + clusters endpoint |

**Dashboard (pm-arbitrage-dashboard) — Delete:**
| File | Reason |
|---|---|
| `src/components/MatchCard.tsx` | Replaced by table rows in redesigned MatchesPage |

### Testing Strategy

**Backend (Vitest, co-located specs):**
- `match-approval.service.spec.ts`: Test `toSummaryDto()` maps all 25 fields correctly (including cluster relation → nested object, null cluster → null, DateTime → ISO string). Test `listMatches()` with `clusterId` filter. Test `listClusters()` returns all clusters sorted by name.
- `match-approval.controller.spec.ts`: Test `GET /matches/clusters` returns correct response shape. Test that the clusters route resolves before `:id` route.
- Run `pnpm test` — baseline is 1937 tests. All must pass after changes.

**Frontend:** No unit test framework is configured for the dashboard SPA. Manual verification via browser.

**Integration verification:**
1. Start engine, regenerate API client, verify types compile
2. Navigate to `/matches` — verify tabbed views, cluster filter, table rendering
3. Click a row — verify `/matches/:id` detail page loads
4. Approve/reject from detail page — verify dialog works
5. Filter by cluster — verify server-side filtering

### Project Structure Notes

- Engine and dashboard are separate git repos — commit changes separately [Source: CLAUDE.md#Repository-Structure]
- Engine changes go first (backend DTO + endpoints), then regenerate client, then frontend changes
- All engine financial math uses `decimal.js` — but this story has no financial calculations, so not applicable

### References

- [Source: epics.md#Story-9.7] — Epic acceptance criteria
- [Source: sprint-change-proposal-2026-03-13b.md] — Full change analysis and field inventory
- [Source: CLAUDE.md#Module-Dependency-Rules] — Import constraints
- [Source: CLAUDE.md#API-Response-Format] — Response wrapper standard
- [Source: prisma/schema.prisma#ContractMatch] — 22-field data model (lines 97-131)
- [Source: prisma/schema.prisma#CorrelationCluster] — Cluster model (lines 66-78)
- [Source: pm-arbitrage-engine/src/dashboard/match-approval.dto.ts] — Current DTO (16 fields, needs 8 more)
- [Source: pm-arbitrage-engine/src/dashboard/match-approval.service.ts#toSummaryDto] — Current mapping (lines 221-242)
- [Source: pm-arbitrage-engine/src/dashboard/match-approval.controller.ts] — Current routes (lines 44-84)
- [Source: pm-arbitrage-dashboard/src/components/PositionsTable.tsx] — Existing @tanstack/react-table pattern to extract into DataTable
- [Source: pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx] — Detail page pattern (useParams, DashboardPanel, loading/error states)
- [Source: pm-arbitrage-dashboard/src/hooks/useDashboard.ts] — Hook patterns (query keys, staleTime, mutations)
- [Source: pm-arbitrage-dashboard/src/api/generated/Api.ts#MatchSummaryDto] — Generated client is stale (12 of 25 fields)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
N/A — no blockers encountered.

### Completion Notes List
- **Backend (Tasks 1-3):** Extended `MatchSummaryDto` with 8 new fields (polymarketRawCategory, kalshiRawCategory, firstTradedTimestamp, totalCyclesTraded, primaryLeg, resolutionDate, resolutionCriteriaHash, cluster). Added `ClusterSummaryDto`, `ClusterListResponseDto`. Added `include: { cluster: true }` to all Prisma queries in the service. Added `clusterId` query parameter to list endpoint. Added `GET /matches/clusters` endpoint (declared BEFORE `@Get(':id')` to avoid route conflict). Tests: 39 passing (29 service + 10 controller), up from 31 baseline.
- **Frontend (Tasks 4-11):** Installed shadcn tabs. Created generic `DataTable<TData>` component wrapping @tanstack/react-table v8 with sorting, pagination, loading/empty states, and clickable rows. Rewrote `MatchesPage` with tabbed views (Pending/Approved/All), cluster filter dropdown, and DataTable. Created `MatchDetailPage` at `/matches/:id` with 4 organized sections (Contract Pair, Resolution, Trading Activity, Operator Review). Updated `MatchApprovalDialog` to show cluster badge, confidence score, and resolution date. Added `useMatchClusters()`, `useMatchDetail()` hooks and updated `useDashboardMatches` with `clusterId` param. Added detail view query invalidation on approve/reject mutations. Deleted `MatchCard.tsx`. Removed all dead Epic 8 references. Regenerated API client (25 fields in MatchSummaryDto + cluster types + clusters endpoint).
- **Code Review (Lad MCP):** Primary reviewer (kimi-k2.5) identified 18 findings. Fixed 2 legitimate issues: (1) memoized column definitions in MatchesPage, (2) added detail view query invalidation. Remaining findings were either pre-existing code, out of scope, or followed established patterns (e.g., `any` in ColumnDef matches PositionsTable, native `<select>` per story guidance when shadcn Select not installed).
- **Test counts:** Engine 1944 passing (baseline 1936, +8 new). Dashboard builds with zero TS errors.
- **Code Review #2 (Claude Opus 4.6, 2026-03-13):** Found 2 MEDIUM, 3 LOW issues. Fixed 2 MEDIUM (controller spec `buildMatchDto` missing 8 new DTO fields; `deriveStatus()`/`statusConfig` duplicated between MatchesPage and MatchDetailPage — extracted to `src/lib/match-status.ts`), 2 LOW (missing `aria-label` on cluster filter `<select>`; no test for combined status+clusterId filter). 1 LOW noted as design consideration (client-side sorting on server-paginated data — pre-existing pattern). Engine tests: 1945 passing (+1 combined filter test). Dashboard: zero TS errors.

### File List

**Engine (pm-arbitrage-engine) — Modified:**
| File | Change |
|---|---|
| `src/dashboard/dto/match-approval.dto.ts` | Added `ClusterSummaryDto`, 8 fields to `MatchSummaryDto`, `clusterId` to `MatchListQueryDto`, `ClusterListResponseDto` |
| `src/dashboard/match-approval.service.ts` | Extended `toSummaryDto()` with 8 fields, added `include: { cluster: true }` to all queries, added `clusterId` filter, added `listClusters()` |
| `src/dashboard/match-approval.controller.ts` | Added `@Get('clusters')` endpoint before `@Get(':id')`, passed `clusterId` to service |
| `src/dashboard/match-approval.service.spec.ts` | Added 7 tests: new field mapping (2), cluster filtering (2), listClusters (2), combined status+clusterId (1) |
| `src/dashboard/match-approval.controller.spec.ts` | Added 1 test for clusters endpoint, updated listMatches call expectations, added 8 missing fields to buildMatchDto |

**Dashboard (pm-arbitrage-dashboard) — Modified:**
| File | Change |
|---|---|
| `src/components/ui/tabs.tsx` | NEW — shadcn tabs component |
| `src/components/DataTable.tsx` | NEW — generic reusable table component |
| `src/lib/match-status.ts` | NEW — shared `deriveStatus()`, `statusConfig`, `DerivedStatus` type (extracted from MatchesPage/MatchDetailPage) |
| `src/pages/MatchesPage.tsx` | REWRITE — tabs + cluster filter + DataTable + aria-label on select |
| `src/pages/MatchDetailPage.tsx` | NEW — full match detail view (uses shared match-status) |
| `src/components/MatchApprovalDialog.tsx` | Added cluster/confidence/resolution context |
| `src/hooks/useDashboard.ts` | Added `useMatchClusters`, `useMatchDetail`; updated `useDashboardMatches` with clusterId; added detail view invalidation |
| `src/App.tsx` | Added `/matches/:id` route + import |
| `src/api/generated/Api.ts` | REGENERATED — 25-field MatchSummaryDto + cluster types + clusters endpoint |

**Dashboard (pm-arbitrage-dashboard) — Deleted:**
| File | Reason |
|---|---|
| `src/components/MatchCard.tsx` | Replaced by table rows in redesigned MatchesPage |
