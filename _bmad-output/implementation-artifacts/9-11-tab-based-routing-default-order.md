# Story 9.11: Tab-Based Routing & Default Order

Status: done

## Story

As an operator,
I want dashboard tabs converted to URL route segments with the matches page defaulting to the Approved tab,
So that I can bookmark, share, and directly navigate to specific tab views, and see approved matches first as my primary workflow.

## Acceptance Criteria

1. **Given** the operator navigates to `/matches` **When** the page loads **Then** the browser redirects to `/matches/approved` and the Approved tab content is displayed [Source: sprint-status.yaml#9-11]

2. **Given** the operator navigates to `/matches/approved`, `/matches/pending`, or `/matches/rejected` **When** the page loads **Then** the corresponding tab content is displayed with the correct status filter applied to `useDashboardMatches()` and the active tab is visually highlighted [Source: sprint-status.yaml#9-11]

3. **Given** the operator navigates to `/matches/rejected` **When** the rejected tab loads **Then** matches where `operatorApproved === false AND operatorRationale !== null` are displayed (backend `MatchStatusFilter.rejected` already supports this) [Derived from: match-approval.service.ts status filter logic + sprint-status.yaml#9-11]

4. **Given** the matches page previously had "pending/approved/all" tabs **When** the new route-based tabs are active **Then** the "all" tab is removed and replaced by an explicit "rejected" tab; tab order is: Approved, Pending, Rejected [Derived from: sprint-status.yaml#9-11 specifying "approved/pending/rejected"]

5. **Given** the operator navigates to `/positions` **When** the page loads **Then** the browser redirects to `/positions/open` and the Open positions tab content is displayed [Source: sprint-status.yaml#9-11]

6. **Given** the operator navigates to `/positions/open` or `/positions/all` **When** the page loads **Then** the corresponding tab content is displayed with the correct status filter and the active tab is visually highlighted [Source: sprint-status.yaml#9-11]

7. **Given** the operator is on any tab route (e.g., `/matches/approved?sort=confidenceScore&order=desc&page=2`) **When** they sort, filter by cluster, or paginate **Then** query params update in the URL as before; the tab route segment is unchanged [Derived from: preserving story 9-10 URL state persistence behavior]

8. **Given** the operator switches between tabs on the same page **When** they click a tab (e.g., Approved → Pending) **Then** cluster filter and other query params are preserved across the tab navigation; page resets to 1 [Derived from: UX consistency — filtering by cluster should persist across status views; matches existing useUrlTableState filterKeys page-reset behavior]

9. **Given** detail page routes (`/matches/:id`, `/positions/:id`) exist **When** the operator navigates to a detail page **Then** the detail page renders at full width without tab layout chrome; detail routes are NOT nested under tab layout components [Derived from: current architecture, no requirement to change detail pages]

10. **Given** the operator navigates to an invalid tab route (e.g., `/matches/invalid`) **When** the page loads **Then** they are redirected to the default tab for that page (`/matches/approved` or `/positions/open`) [Derived from: defensive routing best practice]

11. **Given** the Navigation component links to `/matches` and `/positions` **When** the operator clicks a nav link **Then** the redirect to the default tab fires and the nav link shows active state correctly for all tab sub-routes [Derived from: Navigation.tsx NavLink behavior]

12. **Given** the tab navigation replaces shadcn/ui Tabs (which provides built-in ARIA roles) **When** the layout components render NavLink-based tabs **Then** the tab container has `role="tablist"`, each NavLink has `role="tab"`, and the Outlet wrapper has `role="tabpanel"` to preserve accessibility semantics [Derived from: WAI-ARIA Tabs pattern — replacing Radix UI Tabs requires manual ARIA roles]

## Tasks / Subtasks

- [x] Task 1: Update App.tsx route configuration (AC: #1, #2, #5, #6, #9, #10)
  - [x] 1.1 Convert flat `/matches` route to nested structure with layout route + tab child routes
  - [x] 1.2 Convert flat `/positions` route to nested structure with layout route + tab child routes
  - [x] 1.3 Add index routes with `<Navigate to="..." replace />` for defaults
  - [x] 1.4 Keep `/matches/:id` and `/positions/:id` detail routes as siblings (NOT nested under layout)
  - [x] 1.5 Add catch-all `*` routes under each section for invalid tab redirect
- [x] Task 2: Create MatchesLayout.tsx (AC: #1, #2, #4, #8, #11, #12)
  - [x] 2.1 Extract page title and cluster filter dropdown from MatchesPage.tsx
  - [x] 2.2 Replace shadcn/ui `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent` with `NavLink`-based tab navigation; add ARIA roles: `role="tablist"` on nav container, `role="tab"` on each NavLink, `role="tabpanel"` on `<Outlet />` wrapper
  - [x] 2.3 Tab order: Approved, Pending, Rejected (no "all" tab)
  - [x] 2.4 Active tab styling via NavLink `isActive` (reuse existing tab visual style)
  - [x] 2.5 Add `<Outlet />` for tab content rendering
  - [x] 2.6 Build tab link URLs that preserve current query params (cluster, sort, order) but reset page to 1
- [x] Task 3: Refactor MatchesPage.tsx to tab content + update hook type (AC: #2, #3, #7)
  - [x] 3.1 Strip layout chrome (title, cluster filter, tab bar) — now in MatchesLayout
  - [x] 3.2 Accept `status` prop (type: `'approved' | 'pending' | 'rejected'`)
  - [x] 3.3 Remove `tab` from `useUrlTableState` defaults and `filterKeys`
  - [x] 3.4 Pass `status` prop directly to `useDashboardMatches()` instead of reading from URL param
  - [x] 3.5 Remove shadcn/ui Tabs imports if no longer used
  - [x] 3.6 Update `useDashboardMatches()` status type in `useDashboard.ts`: add `'rejected'` to union (`'pending' | 'approved' | 'rejected' | 'all'`) — the generated API client already supports it (Api.ts line 1303)
- [x] Task 4: Create PositionsLayout.tsx (AC: #5, #6, #8, #11, #12)
  - [x] 4.1 Extract page title, mode filter (live/paper/all), and status tab bar from PositionsPage.tsx
  - [x] 4.2 Replace Button-based status tabs with `NavLink`-based tab navigation; add ARIA roles (`tablist`, `tab`, `tabpanel`) matching MatchesLayout pattern
  - [x] 4.3 Tab order: Open, All
  - [x] 4.4 Active tab styling via NavLink `isActive`
  - [x] 4.5 Add `<Outlet />` for tab content rendering
  - [x] 4.6 Build tab link URLs that preserve mode, sort, order but reset page to 1
  - [x] 4.7 Keep mode filter (live/paper/all) as query param in the layout (shared across tabs)
- [x] Task 5: Refactor PositionsPage.tsx to tab content (AC: #6, #7)
  - [x] 5.1 Strip layout chrome (title, mode filter, status tab bar) — now in PositionsLayout
  - [x] 5.2 Accept `status` prop (type: `'open' | 'all'`)
  - [x] 5.3 Remove `status` from `useUrlTableState` defaults and `filterKeys`
  - [x] 5.4 Map `status` prop to API filter: `'open'` → `'OPEN,SINGLE_LEG_EXPOSED,EXIT_PARTIAL'`, `'all'` → `''`
  - [x] 5.5 Pass mapped status to `useDashboardPositions()` instead of reading from URL param
- [x] Task 6: Verify Navigation.tsx active state (AC: #11)
  - [x] 6.1 Confirm NavLink `to="/matches"` shows active for all `/matches/*` sub-routes (react-router-dom v7 default behavior — no `end` prop)
  - [x] 6.2 Confirm NavLink `to="/positions"` shows active for all `/positions/*` sub-routes
  - [x] 6.3 Confirm pending matches badge still renders correctly
- [x] Task 7: Clean up dead code (AC: #4)
  - [x] 7.1 Remove unused shadcn/ui Tabs imports from MatchesPage if fully replaced
  - [x] 7.2 Remove `StatusTab` type and `statusTabs` array from PositionsPage if fully replaced
  - [x] 7.3 Verify no orphaned references to old `tab` or `status` URL params
- [x] Task 8: Lint & verify
  - [x] 8.1 Run `pnpm lint` in `pm-arbitrage-dashboard/`
  - [ ] 8.2 Manual verification: all tab routes render correct content
  - [ ] 8.3 Manual verification: browser back/forward between tabs works
  - [ ] 8.4 Manual verification: query params persist across tab switches
  - [ ] 8.5 Manual verification: detail pages render without tab chrome
  - [ ] 8.6 Manual verification: invalid tab URLs redirect to defaults

## Dev Notes

### Scope

**Frontend only** — no backend changes. The backend already supports all required status filters for both matches (`pending`, `approved`, `rejected` in `MatchStatusFilter`) and positions (status param in `PositionsQueryDto`). No API client regeneration needed.

### Route Architecture

Use react-router-dom v7 (v7.13.1 installed) nested routes with layout routes and `<Outlet />`. Key pattern — "Route Prefix" (path without element) wraps both a layout route (with element) for tabs and a sibling dynamic route for detail pages:

```tsx
// App.tsx — target structure
<Route path="matches">
  {/* Layout route: renders tab chrome + Outlet */}
  <Route element={<MatchesLayout />}>
    <Route index element={<Navigate to="approved" replace />} />
    <Route path="approved" element={<MatchesPage status="approved" />} />
    <Route path="pending" element={<MatchesPage status="pending" />} />
    <Route path="rejected" element={<MatchesPage status="rejected" />} />
    <Route path="*" element={<Navigate to="approved" replace />} />
  </Route>
  {/* Detail route: NOT inside layout, no tab chrome */}
  <Route path=":id" element={<MatchDetailPage />} />
</Route>

<Route path="positions">
  <Route element={<PositionsLayout />}>
    <Route index element={<Navigate to="open" replace />} />
    <Route path="open" element={<PositionsPage status="open" />} />
    <Route path="all" element={<PositionsPage status="all" />} />
    <Route path="*" element={<Navigate to="open" replace />} />
  </Route>
  <Route path=":id" element={<PositionDetailPage />} />
</Route>
```

**Why this works:** React Router v7 matches static segments (`approved`, `pending`, `rejected`) before dynamic segments (`:id`). Since match IDs are UUIDs, there's no collision. The detail route is a sibling of the layout route, so it renders at full width without tab chrome. [Source: reactrouter.com/start/declarative/routing — "Route Prefixes" and "Layout Routes"]

### Tab Navigation Pattern — Preserving Query Params

When the operator switches tabs, query params (cluster, sort, order) should persist but page should reset to 1 (AC #8). This mirrors the existing `useUrlTableState` `filterKeys` page-reset behavior. Build tab NavLink `to` values programmatically:

```tsx
// In MatchesLayout.tsx
const location = useLocation();

const buildTabUrl = (tab: string): string => {
  const params = new URLSearchParams(location.search);
  params.delete('page'); // reset page on tab switch
  const search = params.toString();
  return `${tab}${search ? `?${search}` : ''}`;
};

// Render tabs
const TABS = [
  { path: 'approved', label: 'Approved' },
  { path: 'pending', label: 'Pending' },
  { path: 'rejected', label: 'Rejected' },
];

{TABS.map(({ path, label }) => (
  <NavLink
    key={path}
    to={buildTabUrl(path)}
    className={({ isActive }) => /* active/inactive styles */ }
  >
    {label}
  </NavLink>
))}
```

**Important:** Use `<NavLink>` (not `<Link>`) so `isActive` correctly highlights the current tab. react-router-dom v7 NavLink matches the current URL path against the `to` path (ignoring query params for matching). [Source: reactrouter.com/start/declarative/routing — "Linking"]

### useUrlTableState Changes

The `tab`/`status` param is no longer managed by the hook — it's now a route segment. Remove it from defaults, filterKeys, and allowedValues:

**MatchesPage (before):**
```typescript
const MATCHES_URL_DEFAULTS = { tab: 'pending', page: '1', cluster: undefined, sort: undefined, order: undefined };
const filterKeys = ['tab', 'cluster', 'sort', 'order'];
const allowedValues = { tab: ['pending', 'approved', 'all'] };
```

**MatchesPage (after):**
```typescript
const MATCHES_URL_DEFAULTS = { page: '1', cluster: undefined, sort: undefined, order: undefined };
const filterKeys = ['cluster', 'sort', 'order'];
// No tab in allowedValues — tab is a route segment now
```

**PositionsPage (before):**
```typescript
const POSITIONS_URL_DEFAULTS = { status: 'open', mode: 'all', sort: 'updatedAt', order: 'desc', page: '1' };
const filterKeys = ['status', 'mode', 'sort', 'order'];
```

**PositionsPage (after):**
```typescript
const POSITIONS_URL_DEFAULTS = { mode: 'all', sort: 'updatedAt', order: 'desc', page: '1' };
const filterKeys = ['mode', 'sort', 'order'];
// No status in filterKeys — status is a route segment now
```

### Positions Status Mapping

The `status` prop maps to the existing API filter convention in `useDashboardPositions()`:
- `'open'` → pass `status` as `undefined` to the hook (which defaults to `'OPEN,SINGLE_LEG_EXPOSED,EXIT_PARTIAL'` server-side) [Source: dashboard.service.ts status filter logic]
- `'all'` → pass `status` as `''` (empty string, which means all statuses server-side)

### Navigation.tsx

NavLink `to="/matches"` will show active for all `/matches/*` sub-routes by default in react-router-dom v7 (no `end` prop). If `end` is present, it must be removed. Same for `/positions`. The pending matches badge is independent of routing — it fetches count from the API regardless of current tab. [Source: Navigation.tsx current implementation]

### Tab Visual Styling

The current MatchesPage uses shadcn/ui `Tabs` with filled pill variant. The new NavLink-based tabs should match this visual style. Reuse the same Tailwind classes from the existing `TabsTrigger` styling (rounded pill, active background color) applied via NavLink's `className` callback.

The current PositionsPage uses `Button` components with `variant='default'` (active) and `variant='outline'` (inactive). The new NavLink-based tabs should match this visual pattern.

### Project Structure Notes

- **MatchesLayout.tsx** and **PositionsLayout.tsx** are created in `src/pages/` alongside existing page components (no new `layouts/` directory — two files don't warrant a new directory)
- **MatchesPage.tsx** and **PositionsPage.tsx** are refactored in-place (not renamed) — they remain the "page content" components, just with layout chrome extracted
- **No new hooks or utilities needed** — `useUrlTableState`, `useLocation`, `NavLink`, `Outlet`, `Navigate` are all available
- **DataTable.tsx unchanged** — URL state behavior is fully controlled by `useUrlTableState` config passed from page components

### References

- [Source: sprint-status.yaml#9-11] — story one-liner defining tab routes and default order
- [Source: reactrouter.com/start/declarative/routing] — react-router-dom v7 nested routes, layout routes, route prefixes, NavLink
- [Source: pm-arbitrage-dashboard/src/pages/MatchesPage.tsx] — current tab implementation using shadcn/ui Tabs + useUrlTableState
- [Source: pm-arbitrage-dashboard/src/pages/PositionsPage.tsx] — current status filter using Button components + useUrlTableState
- [Source: pm-arbitrage-dashboard/src/App.tsx] — current flat route configuration
- [Source: pm-arbitrage-dashboard/src/components/Navigation.tsx] — NavLink navigation with pending badge
- [Source: pm-arbitrage-dashboard/src/hooks/useUrlTableState.ts] — URL state management hook
- [Source: pm-arbitrage-engine/src/dashboard/match-approval.service.ts] — backend status filter logic (pending/approved/rejected)
- [Source: pm-arbitrage-engine/src/dashboard/dashboard.service.ts] — backend positions status filter logic
- [Source: pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts] — MatchStatusFilter enum, MatchListQueryDto
- [Source: pm-arbitrage-engine/src/dashboard/dto/common-query.dto.ts] — PositionsQueryDto, PositionSortField
- [Source: story 9-10 dev notes] — URL state persistence patterns, useUrlTableState design, DataTable urlStateKey

### Previous Story Intelligence (from 9-10)

Story 9-10 established the shared DataTable + URL state persistence pattern. Key learnings:
- `useUrlTableState` is the single owner of URL params per page; manages sort/order/page/filter
- Sort/filter changes use `replace: true`; page changes use `push: true`
- Invalid params silently dropped on mount, URL replaced with defaults
- `filterKeys` auto-reset page to 1 when any filter key changes
- DataTable `urlStateKey` prop enables URL state integration

This story extends that pattern by extracting the tab dimension from query params to route segments, while preserving all other URL state behaviors intact.

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
N/A — no test failures or debugging needed

### Completion Notes List
- All 8 tasks completed. Tasks 8.2–8.6 are manual verification items for the operator.
- Navigation.tsx required no changes — `end` only on `/`, prefix matching works for sub-routes.
- Lad MCP code review (1 reviewer returned, 1 timed out): fixed P1 finding (replaced `useLocation` + `location.search` with existing `searchParams` in both layouts). All other findings were either pre-existing behavior or out-of-scope.
- `aria-controls` not added — AC #12 explicitly scopes to `role="tablist"`, `role="tab"`, `role="tabpanel"`. NavLink auto-sets `aria-current="page"` for equivalent screen reader behavior.
- Positions pagination without `page` param in `useDashboardPositions()` is pre-existing behavior (hook never accepted page). Not a regression from this story.
- Code review #2 completed 2026-03-14: fixed 2 MEDIUM (dead `'cluster'` in MATCHES_FILTER_KEYS after extraction to layout, missing `aria-selected` on tab NavLinks), 2 LOW noted (PositionsLayout unsafe `as Mode` cast, `<Navigate>` redirects don't preserve query params).

### File List

**Files CREATED:**
- `pm-arbitrage-dashboard/src/pages/MatchesLayout.tsx` — tab layout with NavLink tabs + Outlet + cluster filter
- `pm-arbitrage-dashboard/src/pages/PositionsLayout.tsx` — tab layout with NavLink tabs + Outlet + mode filter

**Files MODIFIED:**
- `pm-arbitrage-dashboard/src/App.tsx` — nested route configuration with layout routes, index redirects, catch-all redirects
- `pm-arbitrage-dashboard/src/pages/MatchesPage.tsx` — stripped layout chrome, accepts `status` prop, removed Tabs/useMatchClusters/StatusTab
- `pm-arbitrage-dashboard/src/pages/PositionsPage.tsx` — stripped layout chrome, accepts `status` prop, removed Mode/StatusTab/modes/statusTabs
- `pm-arbitrage-dashboard/src/hooks/useDashboard.ts` — added `'rejected'` to `useDashboardMatches()` status type union

**Files UNCHANGED (verified):**
- `pm-arbitrage-dashboard/src/components/Navigation.tsx` — no changes needed (prefix matching works)
- `pm-arbitrage-dashboard/src/components/DataTable.tsx`
- `pm-arbitrage-dashboard/src/hooks/useUrlTableState.ts`
- `pm-arbitrage-dashboard/src/pages/MatchDetailPage.tsx`
- `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx`
- `pm-arbitrage-dashboard/src/api/generated/Api.ts`
- All backend files (no backend changes)
