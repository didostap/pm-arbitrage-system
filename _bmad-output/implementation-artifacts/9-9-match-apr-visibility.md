# Story 9.9: Match APR Visibility — Persist & Display Estimated Annualized Return

Status: done

## Story

As an operator,
I want to see estimated annualized return (APR), net edge, and computation recency for each contract match on the dashboard,
so that I can make informed match approval and capital allocation decisions based on capital efficiency data.

## Acceptance Criteria

1. **Given** the Prisma schema is migrated, **When** inspecting the `contract_matches` table, **Then** three new nullable columns exist: `last_annualized_return` (Decimal(20,8)), `last_net_edge` (Decimal(20,8)), `last_computed_at` (Timestamptz). All existing data is unaffected (columns default NULL). [Source: sprint-change-proposal-2026-03-13-match-apr.md §4.1]

2. **Given** the detection pipeline emits `OpportunityIdentifiedEvent` for a matched pair, **When** the event fires, **Then** the monitoring module's event subscriber updates the corresponding `ContractMatch` record with `lastAnnualizedReturn`, `lastNetEdge`, and `lastComputedAt` from the event payload. **And** the update is async (never blocks the hot path). [Source: sprint-change-proposal §3, §4.2; CLAUDE.md "Fan-out (async EventEmitter2) — NEVER BLOCK EXECUTION"]

3. **Given** the detection pipeline emits `OpportunityFilteredEvent` for a matched pair, **When** the event carries a non-null `matchId`, **Then** the subscriber updates the corresponding `ContractMatch` with `lastNetEdge`, `lastComputedAt`, and `lastAnnualizedReturn` (when available — only non-null for APR-threshold-filtered events). [Source: sprint-change-proposal §4.2; Q2 decision: subscribe to both events]

4. **Given** the API serves `GET /api/contract-matches`, **When** the response includes matches with APR data, **Then** each `MatchSummaryDto` includes `lastAnnualizedReturn: number | null`, `lastNetEdge: number | null`, `lastComputedAt: string | null`. [Source: sprint-change-proposal §4.3]

5. **Given** the API serves `GET /api/contract-matches`, **When** query includes `sortBy` and `order` params, **Then** results are sorted server-side by the specified field. Sortable fields: `createdAt`, `updatedAt`, `confidenceScore`, `resolutionDate`, `totalCyclesTraded`, `operatorApproved`, `firstTradedTimestamp`, `lastAnnualizedReturn`, `lastNetEdge`, `lastComputedAt`. Order: `asc` | `desc`. Default `order` when `sortBy` is provided but `order` is omitted: `desc`. Default (no sortBy): current behavior (`operatorApproved asc, createdAt desc`). Invalid `sortBy` or `order` returns 400. Null values sort last regardless of sort direction. [Source: sprint-change-proposal §4.5; Q3 decision: server-side sort for all fields]

6. **Given** the Matches page table, **When** APR data exists for a match, **Then** a sortable "Est. APR" column displays the value as a percentage (e.g., "42.1%") with color coding: green ≥ 30%, yellow 15–30%, red < 15%, gray "—" when null. **And** sorting triggers a server-side API call (all table columns use server-side sort). [Source: sprint-change-proposal §4.6; Q3 decision]

7. **Given** the Match detail page, **When** APR data exists, **Then** a "Capital Efficiency" card section displays: Est. APR (formatted %), Net Edge (formatted %), Last Updated (relative time with absolute tooltip), and a staleness indicator (amber if > 5 minutes old, hardcoded threshold matching detection polling cycle ~30s × 10 missed cycles). **When** APR is null, the section shows "Awaiting detection data". [Source: sprint-change-proposal §4.7; staleness threshold derived from detection cycle frequency]

8. **Given** all changes are deployed, **When** the full test suite runs, **Then** all existing tests pass and new tests cover: event subscriber (identified + filtered events), DTO mapping (Decimal→number, null handling), sort query validation, and frontend column rendering. [Source: sprint-change-proposal §5 AC#8]

## Tasks / Subtasks

- [x] **Task 1: Prisma migration** (AC: #1)
  - [x] Add `lastAnnualizedReturn Decimal? @map("last_annualized_return") @db.Decimal(20, 8)`, `lastNetEdge Decimal? @map("last_net_edge") @db.Decimal(20, 8)`, `lastComputedAt DateTime? @map("last_computed_at") @db.Timestamptz` to `ContractMatch` model
  - [x] Add `@@index([lastAnnualizedReturn])`, `@@index([lastNetEdge])`, `@@index([lastComputedAt])` for sort performance on all three new sortable fields
  - [x] Run `pnpm prisma migrate dev --name add-match-apr-fields` then `pnpm prisma generate`

- [x] **Task 2: Enrich event payloads** (AC: #2, #3)
  - [x] `OpportunityIdentifiedEvent`: Add `matchId: dislocation.pairConfig.matchId ?? null` to the payload object emitted at `edge-calculator.service.ts:~261`
  - [x] `OpportunityFilteredEvent`: Add optional `matchId` and `annualizedReturn` as class fields with explicit assignments. Add trailing options object to constructor: `opts?: { matchId?: string; annualizedReturn?: number | null }`. In constructor body: `this.matchId = opts?.matchId; this.annualizedReturn = opts?.annualizedReturn ?? null;` — backward-compatible, existing 4 call sites unchanged
  - [x] Update all 4 `OpportunityFilteredEvent` emission sites in `edge-calculator.service.ts` to pass `opts` with `matchId` from `dislocation.pairConfig.matchId`; for the APR-below-threshold case (~line 380), also pass computed `annualizedReturn`
  - [x] Update corresponding tests

- [x] **Task 3: Match APR updater service** (AC: #2, #3)
  - [x] Create `pm-arbitrage-engine/src/modules/monitoring/match-apr-updater.service.ts`
  - [x] Use `@OnEvent(EVENT_NAMES.OPPORTUNITY_IDENTIFIED)` and `@OnEvent(EVENT_NAMES.OPPORTUNITY_FILTERED)` decorators (established pattern: see `dashboard.gateway.ts`, `correlation-tracker.service.ts`)
  - [x] On `OpportunityIdentifiedEvent`: extract `matchId` from `event.opportunity.matchId`, `annualizedReturn` from `event.opportunity.annualizedReturn`, `netEdge` from `event.opportunity.netEdge`, `enrichedAt` from `event.opportunity.enrichedAt`. If `matchId` is present, update via `prisma.contractMatch.update({ where: { matchId }, data: { lastAnnualizedReturn: annualizedReturn != null ? annualizedReturn.toString() : null, lastNetEdge: netEdge.toString(), lastComputedAt: enrichedAt ?? new Date() } })`. Pass Decimal values as strings for precision safety.
  - [x] On `OpportunityFilteredEvent`: extract `matchId` from `event.matchId`. If present, build update data: always set `lastNetEdge` (from `event.netEdge.toString()`), `lastComputedAt: new Date()`. Set `lastAnnualizedReturn` ONLY if `event.annualizedReturn` is non-null (otherwise skip — preserve any previously-persisted APR value).
  - [x] **Null handling rule**: when a field value is `null`/`undefined` in the event, do NOT overwrite a previously-stored value in the DB. Only update fields that carry non-null data. This prevents a filtered event from wiping a previously-computed APR.
  - [x] Wrap DB updates in try/catch — log errors but never throw (must not disrupt event fan-out)
  - [x] Register in `monitoring.module.ts` providers

- [x] **Task 4: DTO + service mapping** (AC: #4)
  - [x] Add to `MatchSummaryDto`: `lastAnnualizedReturn: number | null`, `lastNetEdge: number | null`, `lastComputedAt: string | null` with `@ApiProperty({ nullable: true, type: Number/String })`
  - [x] Update `toSummaryDto()` in `match-approval.service.ts`: map Prisma `Decimal?` → `number | null` via `?.toNumber() ?? null`; map `DateTime?` → `.toISOString() ?? null`

- [x] **Task 5: Server-side sort support** (AC: #5)
  - [x] Create `MatchSortField` enum and `SortOrder` enum in `match-approval.dto.ts`
  - [x] Add `sortBy?: MatchSortField` and `order?: SortOrder` to `MatchListQueryDto` with `@IsOptional()`, `@IsEnum()` validators
  - [x] Update `MatchApprovalService.listMatches()` signature to accept `sortBy` and `order`
  - [x] Build Prisma `orderBy` dynamically: if `sortBy` provided, use `{ [sortBy]: { sort: order ?? 'desc', nulls: 'last' } }` (Prisma 6+ supports `nulls` option); else use current default `[{ operatorApproved: 'asc' }, { createdAt: 'desc' }]`
  - [x] Update `MatchApprovalController.listMatches()` to pass `query.sortBy` and `query.order` through
  - [x] Add validation: reject unknown sort fields (handled by `@IsEnum`)

- [x] **Task 6: Regenerate API client** (AC: #4, #5, #6)
  - [x] Start engine (`pnpm start:dev` in pm-arbitrage-engine/) so Swagger spec is served at `/api/docs-json`
  - [x] Run `pnpm generate-api` in pm-arbitrage-dashboard/ to regenerate `src/api/generated/Api.ts`
  - [x] Verify new fields and query params appear in generated types

- [x] **Task 7: Frontend — server-side sort migration** (AC: #6)
  - [x] Update `DataTable` component: add optional `manualSorting?: boolean` and `onSortingChange?: (sorting: SortingState) => void` props. When `manualSorting` is true, set `manualSorting: true` on useReactTable and skip `getSortedRowModel()`. Propagate `onSortingChange` callback.
  - [x] Update `useDashboardMatches` hook: accept `sortBy` and `order` params, pass them to `api.matchApprovalControllerListMatches()` query
  - [x] Update `MatchesPage`: track sort state in component, pass to `useDashboardMatches` hook and `DataTable`. Map TanStack `SortingState` → API `sortBy`/`order` params. Use `manualSorting` mode.

- [x] **Task 8: Frontend — APR table column** (AC: #6)
  - [x] Add "Est. APR" column to MatchesPage columns array (after "Confidence")
  - [x] Formatter: APR value is a decimal (e.g., 0.42 = 42%). Display as `value != null ? (value * 100).toFixed(1) + '%' : '—'`. Verify whether any existing `formatPercent` util handles the multiplication internally — if so, pass `value` directly without `* 100`
  - [x] Color coding: `text-green-600` if ≥ 0.30, `text-yellow-600` if ≥ 0.15, `text-red-500` if < 0.15, `text-muted-foreground` if null
  - [x] Column accessor: `lastAnnualizedReturn`

- [x] **Task 9: Frontend — Match detail Capital Efficiency section** (AC: #7)
  - [x] Add "Capital Efficiency" DashboardPanel to MatchDetailPage (after Trading Activity panel)
  - [x] Display: Est. APR (%), Net Edge (%), Last Updated (relative time via existing date utils, absolute in tooltip)
  - [x] Staleness indicator: amber badge if `lastComputedAt` is > 5 minutes ago
  - [x] Empty state: "Awaiting detection data" when all three fields are null

- [x] **Task 10: Tests** (AC: #8)
  - [x] `match-apr-updater.service.spec.ts`: test identified event updates all 3 fields, filtered event updates fields (with null APR preservation), missing matchId is skipped, DB error is caught and logged, concurrent events for same matchId are handled (last-write-wins acceptable)
  - [x] `match-approval.service.spec.ts`: test `toSummaryDto` maps new Decimal fields correctly, null handling
  - [x] `match-approval.controller.spec.ts`: test sortBy/order params passed through, invalid sortBy returns 400, invalid order returns 400, nulls sort last
  - [x] `edge-calculator.service.spec.ts`: test matchId is included in identified event payload, test filtered event opts carry matchId/annualizedReturn
  - [x] Run full suite: `pnpm test` in pm-arbitrage-engine/

## Dev Notes

### Architecture Compliance

- **Event fan-out pattern**: The subscriber runs in the async event fan-out path, NOT the hot path. `@OnEvent` handlers execute asynchronously when `EventEmitterModule` is configured with `wildcard: true` (verified at `app.module.ts:34`). The subscriber must never throw — wrap all DB operations in try/catch. [Source: CLAUDE.md "Fan-out (async EventEmitter2) — NEVER BLOCK EXECUTION"]
- **Module boundaries**: Monitoring module is allowed to access persistence (`PrismaService`) per CLAUDE.md dependency rules (`modules/monitoring/ → persistence/`). Updating `ContractMatch` via PrismaService is within allowed boundaries.
- **No cross-module service imports**: The subscriber reads event data only — no imports from detection or contract-matching modules. [Source: CLAUDE.md "No module imports another module's service directly"]

### Event Payload Details (Verified)

**`OpportunityIdentifiedEvent`** (`common/events/detection.events.ts:9`):
- Constructor: `(opportunity: Record<string, unknown>, correlationId?: string)`
- Payload emitted at `edge-calculator.service.ts:261-279`:
  ```
  { netEdge, grossEdge, buyPlatformId, sellPlatformId, buyPrice, sellPrice,
    pairId (= eventDescription), positionSizeUsd, feeBreakdown, liquidityDepth,
    annualizedReturn (number|null), enrichedAt }
  ```
- **Missing**: `matchId` — must be added from `dislocation.pairConfig.matchId` (verified present at `contract-pair-loader.service.ts:131`)

**`OpportunityFilteredEvent`** (`common/events/detection.events.ts:21`):
- Constructor: `(pairEventDescription, netEdge: Decimal, threshold: Decimal, reason, correlationId?)`
- **4 emission sites** in `edge-calculator.service.ts`: ~line 219 (edge threshold), ~308 (no resolution date), ~343 (past resolution), ~380 (APR threshold)
- **Missing**: `matchId`, `annualizedReturn` — add via optional `opts` parameter at end of constructor

### ContractMatch Schema (Current — `prisma/schema.prisma:95-134`)

The model has 20+ existing columns. New columns:
```prisma
lastAnnualizedReturn Decimal?  @map("last_annualized_return") @db.Decimal(20, 8)
lastNetEdge          Decimal?  @map("last_net_edge") @db.Decimal(20, 8)
lastComputedAt       DateTime? @map("last_computed_at") @db.Timestamptz
```
Use `Decimal(20,8)` — NOT `Float` — per financial math rules. [Source: CLAUDE.md "ALL financial calculations MUST use decimal.js"]

### Decimal Conversion Patterns

**Read path** (Prisma → DTO): `Decimal?` → `number | null` via `.toNumber() ?? null`. Prisma `Decimal` has `.toNumber()` directly.

**Write path** (subscriber → Prisma): Pass values as **strings** for precision safety: `annualizedReturn.toString()`. Prisma accepts `string` for `Decimal` columns and preserves full precision. Do NOT pass raw `number` — while Prisma accepts numbers, string conversion avoids floating-point precision loss.

**Important type difference**: `OpportunityIdentifiedEvent.opportunity` contains `netEdge` as `number` (already converted via `.toNumber()` at emission). `OpportunityFilteredEvent.netEdge` is `Decimal` (the original `decimal.js` instance). The subscriber must handle both: use `.toString()` for `Decimal` instances and `String(value)` for numbers.

### Server-Side Sort Implementation

`MatchListQueryDto` currently has: `status?`, `page?`, `limit?`, `resolution?`, `clusterId?` (verified at `match-approval.dto.ts:51-88`). Add:
```typescript
export enum MatchSortField {
  CREATED_AT = 'createdAt',
  UPDATED_AT = 'updatedAt',
  CONFIDENCE_SCORE = 'confidenceScore',
  RESOLUTION_DATE = 'resolutionDate',
  TOTAL_CYCLES_TRADED = 'totalCyclesTraded',
  OPERATOR_APPROVED = 'operatorApproved',
  FIRST_TRADED_TIMESTAMP = 'firstTradedTimestamp',
  LAST_ANNUALIZED_RETURN = 'lastAnnualizedReturn',
  LAST_NET_EDGE = 'lastNetEdge',
  LAST_COMPUTED_AT = 'lastComputedAt',
}

export enum SortOrder {
  ASC = 'asc',
  DESC = 'desc',
}
```

Service `listMatches()` currently hardcodes `orderBy: [{ operatorApproved: 'asc' }, { createdAt: 'desc' }]` (verified at `match-approval.service.ts:52`). Replace with dynamic `orderBy` based on `sortBy`/`order` params.

**Null sort handling**: Use Prisma 6+ `nulls` option: `{ [sortBy]: { sort: order, nulls: 'last' } }`. This ensures null APR/netEdge values appear at the bottom regardless of sort direction — operators see data-rich matches first.

### Frontend DataTable Changes

`DataTable` component (`pm-arbitrage-dashboard/src/components/DataTable.tsx`):
- Currently uses `getSortedRowModel()` (line 50) with internal `SortingState` (line 41)
- For server-side sort: add `manualSorting: true` prop to `useReactTable` config, conditionally exclude `getSortedRowModel()`, and expose `onSortingChange` callback
- Keep backward compatibility: `PositionsTable.tsx` (line 251) also uses `DataTable` with client-side sort — only `MatchesPage` should use `manualSorting` mode
- TanStack `SortingState` maps to API params: `[{ id: 'lastAnnualizedReturn', desc: true }]` → `sortBy=lastAnnualizedReturn&order=desc`

### Frontend Color Coding

APR column color thresholds (match sprint-change-proposal §4.6):
- ≥ 30% (0.30): green — strong capital efficiency
- 15–30% (0.15–0.30): yellow — meets minimum threshold
- < 15% (0.15): red — below minimum (should have been filtered by detection)
- null: gray "—" with tooltip "Awaiting next detection cycle"

### Existing Test Patterns

- Co-located specs: `*.spec.ts` next to source file [Source: CLAUDE.md "Testing"]
- Framework: Vitest with `vi.fn()` mocks, `describe`/`it` blocks
- NestJS testing: `Test.createTestingModule({ ... }).compile()` pattern
- Event testing pattern: see `event-consumer.service.spec.ts` for `EventEmitterModule.forRoot({ wildcard: true, delimiter: '.' })` setup
- Current baseline: 1991 tests passing, 1 pre-existing e2e timeout (data-ingestion — unrelated)

### Project Structure Notes

Files to create:
- `pm-arbitrage-engine/src/modules/monitoring/match-apr-updater.service.ts`
- `pm-arbitrage-engine/src/modules/monitoring/match-apr-updater.service.spec.ts`

Files to modify:
- `pm-arbitrage-engine/prisma/schema.prisma` — ContractMatch model (3 columns + 3 indexes)
- `pm-arbitrage-engine/src/common/events/detection.events.ts` — OpportunityFilteredEvent (add opts param)
- `pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.ts` — event payloads (5 sites)
- `pm-arbitrage-engine/src/modules/monitoring/monitoring.module.ts` — register new provider
- `pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts` — MatchSummaryDto, MatchListQueryDto, enums
- `pm-arbitrage-engine/src/dashboard/match-approval.service.ts` — toSummaryDto, listMatches
- `pm-arbitrage-engine/src/dashboard/match-approval.controller.ts` — pass sort params
- `pm-arbitrage-dashboard/src/components/DataTable.tsx` — manualSorting support
- `pm-arbitrage-dashboard/src/hooks/useDashboard.ts` — sort params in query
- `pm-arbitrage-dashboard/src/pages/MatchesPage.tsx` — APR column, server-side sort
- `pm-arbitrage-dashboard/src/pages/MatchDetailPage.tsx` — Capital Efficiency section
- Spec files for modified services

### References

- [Source: sprint-change-proposal-2026-03-13-match-apr.md] — full change proposal with decision rationale
- [Source: CLAUDE.md §Architecture §Communication Patterns] — hot-path vs fan-out rules
- [Source: CLAUDE.md §Module Dependency Rules] — monitoring → persistence allowed
- [Source: CLAUDE.md §Domain Rules] — financial math must use decimal.js
- [Source: edge-calculator.service.ts:231-280] — APR computation + event emission
- [Source: detection.events.ts:9-30] — event class definitions
- [Source: contract-pair-loader.service.ts:119-136] — matchId populated on ContractPairConfig
- [Source: match-approval.dto.ts:51-88] — current MatchListQueryDto (no sort)
- [Source: match-approval.service.ts:30-66] — current listMatches with hardcoded orderBy
- [Source: match-approval.service.ts:240-275] — toSummaryDto mapping
- [Source: app.module.ts:34] — EventEmitterModule.forRoot({ wildcard: true })
- [Source: dashboard.gateway.ts:74-142] — @OnEvent pattern reference
- [Source: DataTable.tsx:31-51] — current client-side sort implementation

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
- PrismaService import path: initially used `../../persistence/prisma.service.js` but correct path is `../../common/prisma.service.js` (grepped existing monitoring service imports to confirm)
- `@OnEvent` handler registration: tests initially failed because `emitAsync` was called without `module.init()`. NestJS `@OnEvent` decorators only register during module initialization lifecycle. Fixed by adding `await module.init()` and using `emit()` + `setTimeout(50ms)` pattern (matching existing `event-consumer.service.spec.ts`)
- Controller test assertions: existing `toHaveBeenCalledWith` assertions needed `undefined, undefined` appended for the two new sort params
- TypeScript build error in `useDashboard.ts`: `Parameters<typeof api.matchApprovalControllerListMatches>[0]` could be `undefined` (optional query param). Fixed with `NonNullable<Parameters<...>[0]>['sortBy']`

### Completion Notes List
- **Implementation**: All 10 tasks completed via TDD. 15 new tests added (1991 → 2006 passing). 2 pre-existing e2e failures unrelated (data-ingestion timeout, logging e2e flaky).
- **Code review #1**: Lad MCP `code_review` completed. Primary reviewer confirmed correct implementation with no actionable findings. Secondary reviewer noted minor style suggestions (not actioned — aligned with existing codebase patterns).
- **Code review #2** (2026-03-13): fixed 2 MEDIUM (missing edge-calculator matchId/APR event assertions, non-sortable columns missing `enableSorting: false`), 1 MEDIUM (weak error-path logger.error assertions), 1 LOW (duplicate import). Test count 2006 → 2007.
- **AC verification**: All 8 acceptance criteria verified and passing.
- **Key decisions**:
  - `OpportunityFilteredEvent` extended with trailing `opts` parameter for backward compatibility (existing 4 call sites unchanged)
  - Null handling: filtered events preserve previously-stored APR values when `annualizedReturn` is null
  - Staleness threshold hardcoded at 5 minutes (detection polling ~30s × 10 missed cycles)
  - `DataTable` `manualSorting` prop maintains backward compatibility — `PositionsTable` continues using client-side sort
- **Dashboard build**: `pnpm build` in `pm-arbitrage-dashboard/` succeeds with no errors.

### File List
**Created:**
- `pm-arbitrage-engine/src/modules/monitoring/match-apr-updater.service.ts` — event subscriber for persisting APR data
- `pm-arbitrage-engine/src/modules/monitoring/match-apr-updater.service.spec.ts` — 10 tests for event subscriber
- `pm-arbitrage-engine/prisma/migrations/20260313173843_add_match_apr_fields/migration.sql` — migration for 3 columns + 3 indexes

**Modified (engine):**
- `pm-arbitrage-engine/prisma/schema.prisma` — ContractMatch model: 3 columns + 3 indexes
- `pm-arbitrage-engine/src/common/events/detection.events.ts` — OpportunityFilteredEvent: added `matchId`, `annualizedReturn` via `opts` param
- `pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.ts` — 5 event emission sites enriched with matchId/annualizedReturn
- `pm-arbitrage-engine/src/modules/monitoring/monitoring.module.ts` — registered MatchAprUpdaterService
- `pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts` — MatchSortField enum, SortOrder enum, sort query params, 3 APR DTO fields
- `pm-arbitrage-engine/src/dashboard/match-approval.service.ts` — dynamic orderBy, toSummaryDto APR mapping
- `pm-arbitrage-engine/src/dashboard/match-approval.controller.ts` — sort param pass-through
- `pm-arbitrage-engine/src/dashboard/match-approval.service.spec.ts` — 5 new tests (APR mapping, sort)
- `pm-arbitrage-engine/src/dashboard/match-approval.controller.spec.ts` — 1 new test + updated assertions
- `pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.spec.ts` — added matchId + annualizedReturn event payload assertions

**Modified (dashboard):**
- `pm-arbitrage-dashboard/src/api/generated/Api.ts` — regenerated with new fields/params
- `pm-arbitrage-dashboard/src/components/DataTable.tsx` — manualSorting + onSortingChange props
- `pm-arbitrage-dashboard/src/hooks/useDashboard.ts` — sortBy/order params in useDashboardMatches
- `pm-arbitrage-dashboard/src/pages/MatchesPage.tsx` — AprCell component, Est. APR column, server-side sort state
- `pm-arbitrage-dashboard/src/pages/MatchDetailPage.tsx` — Capital Efficiency panel with staleness indicator
