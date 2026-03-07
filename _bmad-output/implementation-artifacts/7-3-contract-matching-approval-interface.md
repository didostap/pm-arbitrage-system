# Story 7.3: Contract Matching Approval Interface

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want to review pending contract matches with side-by-side resolution criteria comparison,
so that I can make informed approval decisions quickly.

## Acceptance Criteria

### AC1 — Pending Match Display

- **Given** pending matches exist (confidence <85% in Phase 1, or new manual pairs)
- **When** the operator opens the matches view
- **Then** each pending match displays:
  - Both contract descriptions side-by-side (Polymarket + Kalshi)
  - Resolution criteria from both platforms (MVP: `polymarketDescription` and `kalshiDescription` fields ARE the resolution criteria — no separate field exists. Epic 8 will add structured resolution criteria parsing.)
  - Confidence score (if available — null until Epic 8 adds scoring)
  - Similar historical matches from knowledge base (empty until Epic 8 — show placeholder)
  - Match status (pending / approved / rejected)
  - Creation timestamp
- **And** matches are sorted with pending items first, then by creation date descending (FR-MA-05)

### AC2 — Approve Match

- **Given** the operator reviews a match
- **When** they approve with rationale text
- **Then** `POST /api/matches/:id/approve` is called with the rationale
- **And** the match is logged with `operator_rationale` and `operator_approval_timestamp` (FR-MA-06)
- **And** the match disappears from the pending queue (moves to approved section)
- **And** a toast notification confirms the approval

### AC3 — Reject Match

- **Given** the operator rejects a match
- **When** they click reject with rationale
- **Then** `POST /api/matches/:id/reject` is called
- **And** the rejection is logged for audit trail (`operatorApproved` stays `false`, rationale + timestamp recorded). Active detection not affected in MVP — exclusion from detection implemented in Epic 8 semantic matching.
- **And** the match disappears from the pending queue
- **And** a toast notification confirms the rejection

### AC4 — Real-Time Updates

- **Given** a contract match status changes (new pending match, approved, rejected)
- **When** the WebSocket pushes `match.pending` event
- **Then** the matches view updates in real-time without page refresh

## Tasks / Subtasks

### Backend Tasks

- [x] **Task 1: Create `MatchApprovalController` with approve/reject endpoints** (AC: #2, #3)
  - [x] 1.1 Create `src/dashboard/match-approval.controller.ts` — `@Controller('matches')`, `@UseGuards(AuthTokenGuard)`, `@ApiTags('Contract Matches')`, `@ApiBearerAuth()`:
    - `GET /api/matches` — list all matches with optional `?status=pending|approved|rejected|all` filter (default: `all`). Returns matches sorted: pending first, then by `createdAt` descending. Include pagination (`page`, `limit` query params, max 100).
    - `GET /api/matches/:id` — single match detail by `matchId`
    - `POST /api/matches/:id/approve` — approve match with `{ rationale: string }` body. Sets `operatorApproved = true`, `operatorApprovalTimestamp = now()`, `operatorRationale = rationale`. Emits domain event.
    - `POST /api/matches/:id/reject` — reject match with `{ rationale: string }` body. Sets `operatorApproved = false`, `operatorRationale = rationale`, `operatorApprovalTimestamp = now()`. Emits domain event.
  - [x] 1.2 Create request/query DTOs:
    - `ApproveMatchDto` / `RejectMatchDto` — `{ rationale: string }` with `@IsString()`, `@IsNotEmpty()`, `@MaxLength(1000)` validators. Use `class-validator` decorators + `@ApiProperty()`. **Validation:** Apply `@Body(new ValidationPipe({ whitelist: true }))` on each POST handler — NO global ValidationPipe exists; each controller does it inline (same pattern as `RiskOverrideController`, `SingleLegResolutionController`).
    - `MatchListQueryDto` — `{ status?: 'pending' | 'approved' | 'rejected' | 'all'; page?: number; limit?: number }` with `@IsOptional()`, `@IsEnum()`, `@IsInt()`, `@Min(1)`, `@Max(100)`, `@Type(() => Number)` (for query param transform). Apply `@UsePipes(new ValidationPipe({ whitelist: true, transform: true }))` on the GET list handler (same pattern as `TradeExportController`).
  - [x] 1.3 Create response DTOs:
    - `MatchSummaryDto` — `matchId`, `polymarketContractId`, `kalshiContractId`, `polymarketDescription`, `kalshiDescription`, `operatorApproved`, `operatorApprovalTimestamp`, `operatorRationale`, `confidenceScore` (null for MVP), `createdAt`, `updatedAt`
    - `MatchListResponseDto` — `{ data: MatchSummaryDto[], count: number, page: number, limit: number, timestamp: string }`
    - `MatchDetailResponseDto` — `{ data: MatchSummaryDto, timestamp: string }`
    - `MatchActionResponseDto` — `{ data: { matchId: string, status: string, operatorRationale: string, timestamp: string }, timestamp: string }`
  - [x] 1.4 Register `MatchApprovalController` AND `MatchApprovalService` in `DashboardModule` (controller in `controllers`, service in `providers`)
  - [x] 1.5 Write `match-approval.controller.spec.ts` — tests:
    - List matches with status filter (all, pending, approved, rejected)
    - Invalid status filter → 400
    - Pagination (page, limit, clamping to max 100, page=0/limit=-1/limit=101 → 400)
    - Get single match (found, not found → 404)
    - Approve match (success, not found → 404, already approved → 409)
    - Reject match (success, not found → 404)
    - Re-reject with new rationale (idempotent — overwrites)
    - Empty rationale → 400, rationale > 1000 chars → 400
    - Auth guard applied
    - Swagger decorators present (return type inference via CLI plugin)

- [x] **Task 2: Create `MatchApprovalService`** (AC: #2, #3, #4)
  - [x] 2.1 Create `src/dashboard/match-approval.service.ts`:
    - `listMatches(status: 'pending' | 'approved' | 'rejected' | 'all', page: number, limit: number)` — query `ContractMatch` with optional `where` filter. Status mapping:
      - `pending` = `operatorApproved === false AND operatorRationale IS NULL` (never reviewed)
      - `approved` = `operatorApproved === true`
      - `rejected` = `operatorApproved === false AND operatorRationale IS NOT NULL` (explicitly rejected)
      - `all` = no filter
      - Sort: pending first (operatorApproved ASC), then `createdAt DESC`.
    - `getMatchById(matchId: string)` — find unique, throw `SystemHealthError` (code 4007 NOT_FOUND) if missing
    - `approveMatch(matchId: string, rationale: string)` — atomically update record, emit `MatchApprovedEvent` via EventEmitter2. **`confidenceScore` is NOT a DB column** — hardcode `null` in DTO construction, do NOT attempt to read it from Prisma result.
    - `rejectMatch(matchId: string, rationale: string)` — atomically update record (keep `operatorApproved = false`, set rationale + timestamp), emit `MatchRejectedEvent` via EventEmitter2
  - [x] 2.2 Inject `PrismaService` and `EventEmitter2`
  - [x] 2.3 Validation and atomicity:
    - **Approve:** Use atomic `updateMany` with `WHERE matchId = :id AND operatorApproved = false` to prevent race conditions. If `result.count === 0`, fetch the match — if it exists and is already approved → throw `SystemHealthError` 4008 (409 Conflict). If match doesn't exist → throw 4007 (404).
    - **Reject:** Idempotent — allow re-reject with updated rationale (overwrites previous). Only block: reject-after-approved requires operator to explicitly re-approve first. Use same atomic pattern.
    - **Re-approve after reject:** Allowed — operator can change their mind on a rejected match.
  - [x] 2.4 Write `match-approval.service.spec.ts` — tests:
    - List with status filter
    - Approve flow (updates DB fields, emits event)
    - Approve already-approved match → 409 (SystemHealthError 4008)
    - Reject flow (updates DB, emits event)
    - Re-reject with new rationale (overwrites previous)
    - Match not found → SystemHealthError 4007
    - Atomic update race condition (concurrent approve → only one succeeds)
    - Pagination math

- [x] **Task 3: Create domain events for match state changes** (AC: #4)
  - [x] 3.1 Create `MatchApprovedEvent` and `MatchRejectedEvent` in `src/common/events/`:
    - `MatchApprovedEvent` — `{ matchId, polymarketContractId, kalshiContractId, operatorRationale, timestamp }`
    - `MatchRejectedEvent` — `{ matchId, polymarketContractId, kalshiContractId, operatorRationale, timestamp }`
  - [x] 3.2 Add event names to `EVENT_NAMES` in `event-catalog.ts`:
    - `MATCH_APPROVED: 'contract.match.approved'`
    - `MATCH_REJECTED: 'contract.match.rejected'`
  - [x] 3.3 Update `DashboardEventMapperService` — add `@OnEvent()` handlers for `MATCH_APPROVED` and `MATCH_REJECTED`. Pattern (matches existing mapper methods):
    ```typescript
    @OnEvent(EVENT_NAMES.MATCH_APPROVED)
    handleMatchApproved(event: MatchApprovedEvent): void {
      const payload: WsMatchPendingPayload = {
        matchId: event.matchId,
        status: 'approved',
        confidenceScore: null, // Epic 8
      };
      this.gateway.broadcast(DASHBOARD_EVENTS.MATCH_PENDING, payload);
    }
    ```
    Same pattern for `MATCH_REJECTED` with `status: 'rejected'`.
  - [x] 3.4 Write mapper tests for new match events

- [x] **Task 4: Add Swagger decorators and register** (AC: all)
  - [x] 4.1 All controller methods have return type annotations for CLI plugin schema inference
  - [x] 4.2 `@ApiParam`, `@ApiOperation`, `@ApiResponse` (error codes only — 401, 404, 409) on all endpoints
  - [x] 4.3 DTOs have `@ApiProperty` / `@ApiPropertyOptional`
  - [x] 4.4 Verify `/api/docs` renders match endpoints correctly

### Frontend Tasks

- [x] **Task 5: Create Matches page with side-by-side comparison** (AC: #1)
  - [x] 5.1 Create `src/pages/MatchesPage.tsx` — uses `useDashboardMatches()` hook, displays match cards
  - [x] 5.2 Create `src/components/MatchCard.tsx` — side-by-side contract comparison card:
    - Left panel: Polymarket contract ID + description
    - Right panel: Kalshi contract ID + description
    - Bottom: confidence score (if available, else "N/A — manual pair"), creation date, status badge (pending/approved/rejected)
    - Action buttons: Approve / Reject (only for pending matches)
  - [x] 5.3 Add status filter toggle (Pending / Approved / All) — defaults to Pending
  - [x] 5.4 Empty state: "No pending matches. All contract pairs are approved." with explanation that matches come from YAML config in MVP.
  - [x] 5.5 Use `DashboardPanel` container (existing component) for consistent styling
  - [x] 5.6 Historical matches placeholder: "Knowledge base not available — coming in Epic 8" (shown per match card)

- [x] **Task 6: Approve/Reject dialogs** (AC: #2, #3)
  - [x] 6.1 Create `src/components/MatchApprovalDialog.tsx` — shadcn `<Dialog>` with:
    - Match summary (both contract IDs + descriptions)
    - Action type indicator (Approve / Reject)
    - Rationale text area (`@MaxLength(1000)`, required)
    - Confirm / Cancel buttons
  - [x] 6.2 Create `useApproveMatch` mutation hook in `useDashboard.ts`:
    - Calls `api.matchApprovalControllerApproveMatch(id, { rationale })`
    - On success: invalidate `['dashboard', 'matches']` + show success toast
    - On error: 409 → "Match is already approved"; 404 → "Match not found"; network → "Connection failed"
    - Disable button while `isPending`
  - [x] 6.3 Create `useRejectMatch` mutation hook in `useDashboard.ts`:
    - Calls `api.matchApprovalControllerRejectMatch(id, { rationale })`
    - On success: invalidate `['dashboard', 'matches']` + show success toast
    - On error: 404 → "Match not found"; network → "Connection failed"
    - Disable button while `isPending`

- [x] **Task 7: Real-time match updates via WebSocket** (AC: #4)
  - [x] 7.1 Update `WebSocketProvider.tsx` — replace the `MATCH_PENDING` no-op with:
    ```typescript
    case WS_EVENTS.MATCH_PENDING:
      void queryClient.invalidateQueries({ queryKey: ['dashboard', 'matches'] });
      break;
    ```
    **Note:** `invalidateQueries` uses prefix matching by default — `['dashboard', 'matches']` will invalidate `['dashboard', 'matches', 'pending']`, `['dashboard', 'matches', 'approved']`, etc. This is the desired behavior.
  - [x] 7.2 Add `staleTime: 5_000` to match queries (same pattern as positions — prevents rapid duplicate refetches)

- [x] **Task 8: Navigation and routing** (AC: #1)
  - [x] 8.1 Add `/matches` route to `App.tsx` → `MatchesPage`
  - [x] 8.2 Add navigation header/sidebar with links: Dashboard, Positions, Matches (currently no nav — just route links in cards)
  - [x] 8.3 Add pending match count badge to nav link. Derive from `useDashboardMatches('pending')` query — use `.data?.count` for the badge number. No separate count endpoint needed since the full list is small in MVP.

- [x] **Task 9: Regenerate API client** (AC: all)
  - [x] 9.1 Run `pnpm generate-api` in dashboard to pick up new match endpoints and DTOs
  - [x] 9.2 Verify generated types include `MatchSummaryDto`, approve/reject endpoints

- [x] **Task 10: Add `useDashboardMatches` query hook** (AC: #1)
  - [x] 10.1 Add to `src/hooks/useDashboard.ts`:
    ```typescript
    export function useDashboardMatches(status: 'pending' | 'approved' | 'all' = 'all') {
      return useQuery({
        queryKey: ['dashboard', 'matches', status],
        queryFn: () => api.matchApprovalControllerListMatches({ status }),
        staleTime: 5_000,
      });
    }
    ```

## Dev Notes

### Architecture Compliance

- **Module boundaries:** `MatchApprovalController` and `MatchApprovalService` live in `src/dashboard/` — they are dashboard-facing features, NOT part of `modules/contract-matching/`. The match approval service directly uses `PrismaService` for DB access (same pattern as `DashboardService`). It does NOT import from `modules/contract-matching/`.
- **Why not in `modules/contract-matching/`?** The contract-matching module handles pair loading from YAML config and sync. Approval is an operator-facing workflow belonging to the dashboard domain. Keeping them separate follows the existing pattern where `DashboardService` queries positions/risk without importing module services.
- **Event fan-out:** Match approval/rejection emits domain events → `DashboardEventMapperService` maps to WS event → frontend updates. Same async pattern as all other dashboard events.
- **Error hierarchy:** 404 → `SystemHealthError` (code 4007 NOT_FOUND, severity Info). 409 → `SystemHealthError` (code 4008 MATCH_ALREADY_APPROVED, severity Warning). Add code 4008 to `system-health-error.ts`.
- **Response format:** All endpoints use standard wrapper: `{ data: T, timestamp: string }` / `{ data: T[], count: number, timestamp: string }`.

### Existing Backend Infrastructure (DO NOT recreate)

- **`ContractMatch` Prisma model** — Already has all needed fields: `operatorApproved`, `operatorApprovalTimestamp`, `operatorRationale`, `polymarketDescription`, `kalshiDescription`. No schema migration needed.
- **`AuthTokenGuard`** — Reuse on controller (`src/common/guards/auth-token.guard.ts`)
- **`DashboardModule`** — Register new controller and service here
- **`DashboardEventMapperService`** — Add match event handlers (currently has NO match mapping)
- **`WsMatchPendingPayload`** — Already defined in `src/dashboard/dto/ws-events.dto.ts`: `{ matchId: string; status: string; confidenceScore: number | null; }`
- **`DASHBOARD_EVENTS.MATCH_PENDING`** — Already defined as `'match.pending'`
- **Frontend `MATCH_PENDING` handler** — Currently a no-op in `WebSocketProvider.tsx` line 112-114 with comment "No-op: contract match UI not implemented until Story 7.3"

### Current Contract Match State

In MVP, ALL contract matches come from YAML config (`contract-pairs.yaml`) and are synced to the database with `operatorApproved: true` by `ContractMatchSyncService.syncPairsToDatabase()`. This means:

- There are currently NO pending matches in the database
- The matches view will show all approved matches initially
- The pending queue will become useful when Epic 8 adds semantic matching with confidence scoring (auto-approve >=85%, flag <85% for review)
- For now, this story builds the complete approval infrastructure so it's ready when needed

**Do NOT change the `ContractMatchSyncService` behavior** — YAML-sourced pairs should continue to be auto-approved. The approval UI is for future semantic matches.

### Pending vs Rejected State Discrimination

The `ContractMatch` model has NO explicit `status` enum — only `operatorApproved: boolean` + `operatorRationale: string | null`. The tri-state is derived:

| `operatorApproved` | `operatorRationale` | Derived Status |
|---|---|---|
| `false` | `null` | **pending** (never reviewed) |
| `true` | any | **approved** |
| `false` | not null | **rejected** (explicitly rejected with reason) |

This discrimination is critical for the list endpoint filter and UI display.

### Detection Does NOT Check `operatorApproved` from DB

The arbitrage detection hot path uses **in-memory pairs** from `ContractPairLoaderService` (loaded from YAML on startup). It does NOT query the `ContractMatch` table for `operatorApproved` status. Therefore:

- Rejecting a match in the dashboard does NOT remove it from active detection in the current cycle
- The rejection is recorded in the DB for audit trail and future reference
- In Epic 8, when semantic matching adds pairs dynamically, rejection will prevent them from entering the active pair set
- For MVP, rejection is primarily a record-keeping action (FR-MA-06 audit logging)

### No `confidenceScore` Column Yet

The `ContractMatch` model does NOT have a `confidenceScore` column — that's added in Epic 8 Story 8.1. The `MatchSummaryDto` should include `confidenceScore: null` for all matches. The UI shows "N/A" when null.

### WebSocket Match Event Flow

```
Operator approves/rejects match via REST
  → MatchApprovalService updates DB
  → Emits MatchApprovedEvent / MatchRejectedEvent via EventEmitter2
  → DashboardEventMapperService.mapMatchApprovedEvent() / mapMatchRejectedEvent()
  → DashboardGateway.broadcast('match.pending', { matchId, status, confidenceScore: null })
  → Frontend WebSocketProvider.onMessage()
  → queryClient.invalidateQueries(['dashboard', 'matches'])
  → React Query refetches GET /api/matches
```

### Frontend Patterns (from Stories 7.1 + 7.2)

- **API Client:** `src/api/client.ts` exports `api`. Generated client at `src/api/generated/Api.ts`.
- **Hooks:** All query/mutation hooks in `src/hooks/useDashboard.ts`.
- **Query Keys:** Follow pattern `['dashboard', '<resource>', ...params]`.
- **Mutations:** Use `useMutation` with `onSuccess` → `invalidateQueries` + toast. `onError` → error-specific toasts.
- **Components:** Use shadcn/ui components. All UI components already installed: `card`, `badge`, `button`, `dialog`, `textarea`, `table`, `tooltip`, `alert`, `sonner` (toasts).
- **Styling:** Tailwind CSS 4, `cn()` utility, no gradients/shadows, flat terminal aesthetic.
- **Routing:** `react-router-dom` with `<Routes>` in `App.tsx`. Currently: `/` (dashboard), `/positions`.

### UX Design for Match Comparison Card

```
┌─────────────────────────────────────────────────────┐
│ [PENDING]  Match #abc123                 2026-03-01  │
│                                                      │
│  ┌────────────────────┐  ┌────────────────────────┐ │
│  │ POLYMARKET          │  │ KALSHI                  │ │
│  │                     │  │                         │ │
│  │ Contract ID:        │  │ Contract ID:            │ │
│  │ 0x1234...5678       │  │ FEDRATE-25MAR-T4.50    │ │
│  │                     │  │                         │ │
│  │ Description:        │  │ Description:            │ │
│  │ Will the Fed cut    │  │ Will the Fed cut        │ │
│  │ rates in March?     │  │ rates in March 2026?    │ │
│  └────────────────────┘  └────────────────────────┘ │
│                                                      │
│  Confidence: N/A (manual pair)                       │
│  Knowledge Base: Coming in Epic 8                    │
│                                                      │
│  [✓ Approve]  [✗ Reject]                            │
└─────────────────────────────────────────────────────┘
```

- Pending matches: amber left-border accent (matching paper position pattern)
- Approved matches: green-500 left-border
- Rejected matches: red-500 left-border, dimmed text
- Status badge colors: pending → yellow, approved → green, rejected → red

### Navigation Design

Currently the dashboard has NO shared navigation — each page is accessed via route links in cards. This story should add a simple top nav bar:

```
┌──────────────────────────────────────────────────────┐
│  PM Arbitrage   Dashboard  Positions  Matches(2)     │
│                                          ↑ badge     │
│                                  (pending count)     │
└──────────────────────────────────────────────────────┘
```

Create `src/components/Navigation.tsx` — shared across all pages. Use `NavLink` from react-router-dom for active state styling.

### Project Structure Notes

**New backend files:**

- `src/dashboard/match-approval.controller.ts` — REST endpoints
- `src/dashboard/match-approval.controller.spec.ts` — controller tests
- `src/dashboard/match-approval.service.ts` — business logic
- `src/dashboard/match-approval.service.spec.ts` — service tests
- `src/dashboard/dto/match-summary.dto.ts` — response DTOs
- `src/common/events/match-approved.event.ts` — domain event
- `src/common/events/match-rejected.event.ts` — domain event

**Modified backend files:**

- `src/dashboard/dashboard.module.ts` — register new controller + service
- `src/dashboard/dashboard-event-mapper.service.ts` — add match event handlers
- `src/dashboard/dashboard-event-mapper.service.spec.ts` — add match event tests
- `src/common/events/event-catalog.ts` — add MATCH_APPROVED, MATCH_REJECTED to EVENT_NAMES
- `src/common/events/index.ts` — export new event classes

**New frontend files (pm-arbitrage-dashboard/):**

- `src/pages/MatchesPage.tsx` — matches view with status filter
- `src/components/MatchCard.tsx` — side-by-side contract comparison
- `src/components/MatchApprovalDialog.tsx` — approve/reject dialog with rationale
- `src/components/Navigation.tsx` — shared top navigation bar

**Modified frontend files (pm-arbitrage-dashboard/):**

- `src/App.tsx` — add `/matches` route, add `Navigation` component
- `src/hooks/useDashboard.ts` — add `useDashboardMatches`, `useApproveMatch`, `useRejectMatch`
- `src/providers/WebSocketProvider.tsx` — replace `MATCH_PENDING` no-op with cache invalidation
- `src/api/generated/Api.ts` — regenerated from engine Swagger
- `src/types/ws-events.ts` — no changes needed (types already defined)

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 7, Story 7.3 lines 1864-1886]
- [Source: _bmad-output/planning-artifacts/prd.md — FR-MA-05, FR-MA-06]
- [Source: pm-arbitrage-engine/prisma/schema.prisma — ContractMatch model lines 66-88]
- [Source: pm-arbitrage-engine/src/modules/contract-matching/contract-match-sync.service.ts — sync behavior]
- [Source: pm-arbitrage-engine/src/dashboard/dto/ws-events.dto.ts — WsMatchPendingPayload, DASHBOARD_EVENTS]
- [Source: pm-arbitrage-engine/src/dashboard/dashboard-event-mapper.service.ts — no match mapping yet]
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts — EVENT_NAMES, no match events yet]
- [Source: pm-arbitrage-engine/src/common/errors/system-health-error.ts — 4007 NOT_FOUND code]
- [Source: pm-arbitrage-dashboard/src/providers/WebSocketProvider.tsx — MATCH_PENDING no-op line 112]
- [Source: pm-arbitrage-dashboard/src/App.tsx — current routes]
- [Source: pm-arbitrage-dashboard/src/hooks/useDashboard.ts — existing hooks pattern]
- [Source: 7-1-dashboard-project-setup-system-health-view.md — architecture compliance patterns, event mapper patterns]
- [Source: 7-2-open-positions-p-and-l-detail-view.md — P&L enrichment pattern, frontend patterns, mutation hooks]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A

### Completion Notes List

- All 10 tasks (4 backend + 6 frontend) implemented with TDD
- 1326 backend tests passing (78 test files), 0 regressions
- Frontend TypeScript clean, build successful
- Lad MCP code review completed — two findings addressed: (1) added 409 handling to `useRejectMatch`, (2) fixed `'info' as 'warning'` severity casts in match-approval.service.ts
- Story deviation: `@OnEvent` handlers placed on `DashboardGateway` (not `DashboardEventMapperService`) to match existing codebase pattern
- Story deviation: Used `WS_EVENTS` constant (not `DASHBOARD_EVENTS` as story referenced)
- DTOs consolidated into single `match-approval.dto.ts` file (story suggested separate `match-summary.dto.ts`)
- All 4 Acceptance Criteria verified
- **Code Review (Opus 4.6):** 4 MEDIUM + 2 LOW findings, all fixed:
  - M1: Story File List updated — 6 undocumented frontend files added
  - M2: MatchApprovalDialog now resets rationale on reopen via `useEffect`
  - M3: Removed non-null assertion `updated!` in approveMatch — explicit null check added
  - M4: Controller HTTP responses now use error's actual severity (was hardcoded)
  - L1: Extracted `MatchActionDataDto` class with `@ApiProperty()` for proper Swagger schema
  - L2: Removed unnecessary `?? dto.rationale` fallback in controller responses

### File List

**New backend files:**
- `src/common/events/match-approved.event.ts`
- `src/common/events/match-rejected.event.ts`
- `src/dashboard/dto/match-approval.dto.ts`
- `src/dashboard/match-approval.service.ts`
- `src/dashboard/match-approval.service.spec.ts`
- `src/dashboard/match-approval.controller.ts`
- `src/dashboard/match-approval.controller.spec.ts`

**Modified backend files:**
- `src/common/events/event-catalog.ts` — added MATCH_APPROVED, MATCH_REJECTED
- `src/common/events/index.ts` — added exports
- `src/common/errors/system-health-error.ts` — added 4008 MATCH_ALREADY_APPROVED
- `src/dashboard/dashboard-event-mapper.service.ts` — added match event mappers
- `src/dashboard/dashboard-event-mapper.service.spec.ts` — added mapper tests
- `src/dashboard/dashboard.gateway.ts` — added @OnEvent handlers
- `src/dashboard/dashboard.module.ts` — registered controller + service
- `src/dashboard/dto/index.ts` — added export

**New frontend files (pm-arbitrage-dashboard/):**
- `src/pages/MatchesPage.tsx`
- `src/components/MatchCard.tsx`
- `src/components/MatchApprovalDialog.tsx`
- `src/components/Navigation.tsx`

**Modified frontend files (pm-arbitrage-dashboard/):**
- `src/App.tsx` — added Navigation, /matches route
- `src/hooks/useDashboard.ts` — added match hooks
- `src/providers/WebSocketProvider.tsx` — MATCH_PENDING cache invalidation, extracted context to separate file
- `src/pages/DashboardPage.tsx` — removed header (now in shared Navigation)
- `src/pages/PositionsPage.tsx` — removed header (now in shared Navigation)
- `src/api/generated/Api.ts` — regenerated from Swagger
- `src/providers/WebSocketContext.ts` — extracted WebSocket context (new file)
- `src/hooks/useWebSocket.ts` — extracted useWebSocket hook (new file)
- `src/components/ConnectionStatus.tsx` — updated to use extracted useWebSocket hook
- `src/components/PositionsTable.tsx` — minor updates
- `src/components/ui/badge.tsx` — updated
- `src/components/ui/button.tsx` — updated
