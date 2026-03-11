# Sprint Change Proposal: Dashboard UX Overhaul — Unified Tables, Routed Tabs, Cross-Entity Navigation, Sidebar Layout & Bankroll Persistence

**Date:** 2026-03-13
**Triggered by:** Accumulated dashboard UX tech debt across Epics 7–9. Tables use 3 different patterns, no URL state persistence, no cross-entity navigation, header nav doesn't scale, bankroll hardcoded in `.env`
**Scope Classification:** Moderate — 5 course correction stories added to Epic 9
**Proposed Stories:** `9-10`, `9-11`, `9-12`, `9-13`, `9-14`

---

## Section 1: Issue Summary

The dashboard was scaffolded in Epic 7 (Stories 7-1 through 7-4) and enriched through Epic 7.5 and Epic 9 course corrections (9-7, 9-4a, 9-9). During rapid feature delivery, implementation patterns diverged:

- **Tables:** `PositionsTable.tsx` (316 lines) implements its own `useReactTable` bypassing the shared `DataTable` component. `PerformancePage` and `StressTestPage` use raw shadcn `<Table>` with no sorting or pagination. `PositionDetailPage` order history is also raw `<Table>`.
- **State persistence:** Zero pages persist filter/sort/pagination state in URL query params. All state is `useState` — lost on navigation or refresh.
- **Tabs:** `MatchesPage` and `PositionsPage` manage tabs via component state, not routes. Browser back/forward doesn't work across tabs. Deep-linking to a specific tab is impossible.
- **Cross-entity navigation:** No links between positions and their contract matches. The operator must manually cross-reference.
- **Navigation:** Horizontal header nav with 5 items. Future pages (calibration, settings, logs) will overflow.
- **Bankroll:** `RISK_BANKROLL_USD=10000` in `.env` files only. Not in database. Restart loses any runtime concept of capital changes. Editing requires SSH + file edit + restart.

**Evidence:**
- `PositionsTable.tsx` duplicates DataTable functionality with 316 lines of custom code
- `PerformancePage` table has zero interactivity (no sorting, no click)
- `StressTestPage` has 3 separate raw tables
- `useDashboardPositions`, `useDashboardMatches` hooks read from component `useState`, not URL
- `OpenPosition.pairId → ContractMatch.matchId` FK exists in schema but is never surfaced as a navigable link
- `RISK_BANKROLL_USD` is consumed by 4 services: `RiskManagerService`, `DashboardService`, `StressTestService`, `CorrelationTrackerService` — all read from `ConfigService.get()` (env var)

---

## Section 2: Impact Analysis

### Epic Impact

**Contained to Epic 9.** All 5 stories are course corrections added to Epic 9, following the established pattern (9-1a, 9-1b, 9-5, 9-6, 9-7, 9-8, 9-9, 9-4a, 9-9). No other epics affected.

### Story Impact

No existing stories require modification. All 5 are net-new stories. Story 9-7 (matches page redesign) introduced the `DataTable` component that 9-10 builds upon.

### Artifact Conflicts

- **PRD:** No conflicts. FR-MA-04 (web dashboard) reinforced.
- **Architecture:** Bankroll persistence (9-14) requires adding a `SystemMetadata` row or new model field. Minor schema change. All other stories are frontend-only.
- **UX Spec:** Spec mentions "persistent header component showing composite health status" (can move to TopBar above main content). Spec emphasizes layout stability — this is a one-time improvement before production use. Sidebar aligns with spec's Grafana-inspired panel architecture reference.
- **Epics doc:** No changes needed. Stories are course corrections within Epic 9.

### Technical Impact

- **Frontend:** 5 pages modified, 1 component deleted (`PositionsTable.tsx`), 2 new components (`Sidebar.tsx`, `TopBar.tsx`), DataTable enhanced with URL state support
- **Backend:** 1 new query param on existing endpoint (`GET /api/positions?matchId=`), 2 new endpoints (`GET/PUT /api/config/bankroll`), 1 new event (`config.bankroll.updated`), `RiskManagerService` constructor reads from DB instead of env
- **Database:** 1 new `SystemMetadata` row for `BANKROLL_USD` (no migration needed if using existing key-value model)
- **No breaking changes** to any existing endpoint or data model

---

## Section 3: Recommended Approach

**Selected: Direct Adjustment** — Add 5 course correction stories to Epic 9.

**Rationale:**
- All changes are additive or refactoring — no existing behavior removed
- Risk is low — no core trading logic affected, purely UX/operational improvements
- Epic 9 already has the established pattern of course correction stories
- Dependency chain is simple: 9-10 first (foundational), then 9-11 through 9-14 in any order

**Effort:** Medium (5 stories, frontend-heavy with one backend change)
**Risk:** Low
**Timeline impact:** None — Epic 9 main stories are complete, these extend the epic before retrospective

---

## Section 4: Detailed Change Proposals

### Story 9-10: Unified DataTable & URL State Persistence

**Scope:** Frontend refactor

**Changes:**
1. Migrate `PositionsTable.tsx` (custom `useReactTable`) to use shared `DataTable` component. Move custom cell renderers (PnlCell, RiskRewardCell, ExitProximityIndicator) to standalone components reusable as column def cell renderers. Delete `PositionsTable.tsx`
2. Migrate `PerformancePage` raw `<Table>` to `DataTable` with column defs. Gain sorting for free
3. Migrate `StressTestPage` 3× raw `<Table>` to `DataTable` inside existing collapsible wrappers
4. Migrate `PositionDetailPage` order history raw `<Table>` to `DataTable`
5. Enhance `DataTable` with optional `urlStateKey` prop. When provided, sorting/pagination/filter state syncs to URL query params via `useSearchParams()`. Query params become single source of truth
6. Update `useDashboardPositions`, `useDashboardMatches`, `useDashboardPerformance` hooks to accept params from URL when applicable

**Query param format examples:**
```
/positions?status=open&mode=all&sort=pnl&order=desc&page=1
/matches?sort=apr&order=desc&page=1&cluster=politics
/performance?weeks=8&mode=all
```

**Dependency:** None (foundational — other stories build on this)

---

### Story 9-11: Tab-Based Routing & Default Tab Order

**Scope:** Frontend routing

**Changes:**
1. MatchesPage tabs become route segments:
   - `/matches/approved` (default), `/matches/pending`, `/matches/rejected`
   - `/matches` redirects to `/matches/approved`
   - **New default order: Approved → Pending → Rejected** (replaces Pending → Approved → All)
   - "All" tab removed — replaced by dedicated "Rejected" tab
2. PositionsPage status becomes route segment:
   - `/positions/open` (default), `/positions/all`
   - `/positions` redirects to `/positions/open`
   - Mode filter (all/live/paper) stays as query param `?mode=live`
3. PerformancePage: query params only (from 9-10), no route segments needed
4. StressTestPage: no changes (collapsible sections, not tabs)
5. shadcn `<Tabs>` `value` reads from route param, `onValueChange` calls `navigate()`
6. Combined with 9-10's query params: `/matches/approved?sort=apr&order=desc&page=2`
7. Update `App.tsx` router with new route structure, redirects

**Dependency:** 9-10 (for query param infrastructure)

---

### Story 9-12: Cross-Entity Navigation & Match Position History

**Scope:** Backend + Frontend

**Backend changes:**
1. Add optional `matchId` query param to `GET /api/positions`. `DashboardService.getPositions()` adds `pairId` filter to repository query. FK and index already exist (`OpenPosition.pairId → ContractMatch.matchId`)
2. Enrich `GET /api/matches/:id` response with `positionCount` and `activePositionCount` (cheap count query)

**Frontend changes:**
1. MatchDetailPage: New "Position History" section after Trading Activity. Uses `useDashboardPositions({ matchId })`. Renders DataTable with columns: Status, Entry Prices, P&L, Mode, Opened, Closed. Row click → `/positions/:id`
2. PositionDetailPage: Pair name in header becomes clickable link to `/matches/:pairId`
3. PositionsPage table: Pair name column becomes link to `/matches/:pairId` (with `stopPropagation` to preserve row click → position detail)
4. MatchesPage table: Optional position count column, links to match detail

**Dependency:** 9-10 (DataTable for match detail positions table)

---

### Story 9-13: Left Sidebar Navigation

**Scope:** Frontend layout

**Changes:**
1. New `Sidebar.tsx` component: fixed ~220px left sidebar with vertical nav items (Dashboard, Positions, Matches with pending badge, Performance, Stress Test). Bottom section: version, ConnectionStatus
2. New `TopBar.tsx` component (optional): thin bar with platform health composite dots + connection indicator. Preserves UX spec requirement for persistent health status visibility
3. Update `App.tsx` layout: `flex h-screen` with Sidebar + main content area
4. Delete `Navigation.tsx` after migration
5. All NavLink active state patterns preserved (vertical highlight instead of horizontal underline)

**Dependency:** None (can run parallel with 9-11/9-12/9-14)

---

### Story 9-14: Bankroll Database Persistence & UI Management

**Scope:** Backend + Frontend

**Backend changes:**
1. `RiskManagerService` constructor reads bankroll from `SystemMetadata` DB table instead of `ConfigService.get('RISK_BANKROLL_USD')`. Fallback: if no DB row exists, seed from env var (migration path)
2. New `RiskManagerService.reloadBankroll()` method: re-reads from DB, recalculates derived limits (maxPositionSize, dailyLossLimit, availableCapital). Hot-reload without restart
3. New endpoints: `GET /api/config/bankroll` (current value + updatedAt), `PUT /api/config/bankroll` (validates positive decimal, updates DB, calls reloadBankroll)
4. Bankroll change emits `config.bankroll.updated` event → audit log + Telegram alert
5. Startup: reads DB → if missing, seeds from env var → writes to DB. Env var becomes seed default only

**Frontend changes:**
1. DashboardPage Capital Overview card: edit icon next to bankroll value
2. Click opens inline edit or dialog: current value, input field (validated positive decimal), confirm/cancel
3. Confirmation dialog if change >20% from current value
4. On confirm: `PUT /api/config/bankroll` → invalidate overview query → UI updates
5. Last updated timestamp displayed below bankroll value

**Env var `RISK_BANKROLL_USD` kept** as seed default for fresh installs. Not removed.

**Dependency:** None (can run parallel with 9-11/9-12/9-13)

---

## Section 5: Implementation Handoff

**Change Scope Classification:** Moderate — backlog reorganization within Epic 9

**Handoff: Development team** for direct implementation

**Sequencing:**
1. **9-10** first (foundational DataTable + URL state infrastructure)
2. **9-11 through 9-14** in any order after 9-10

**Sprint status updates required:**
- Add 5 new story entries to `sprint-status.yaml` under Epic 9
- Update summary statistics (story count)

**Success criteria:**
- All tables across the dashboard use the shared `DataTable` component
- Sorting, pagination, and filter state persists in URL query params on all applicable pages
- Tabs route to distinct URLs; browser back/forward works across tabs
- Operator can navigate from any position to its contract match and vice versa
- Match detail page shows full position history for that match
- Navigation is in a left sidebar with room for future pages
- Bankroll is stored in DB, editable from dashboard, survives restarts
- Default matches page lands on Approved tab
- All existing tests pass, linting clean
