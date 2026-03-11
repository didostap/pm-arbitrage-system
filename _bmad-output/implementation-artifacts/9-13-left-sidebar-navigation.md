# Story 9.13: Left Sidebar Navigation

Status: done

## Story

As an **operator**,
I want **the dashboard navigation in a collapsible left sidebar with a persistent top bar showing platform health status**,
so that **navigation scales to future pages without overflow and system health is always visible regardless of which page I'm on**.

## Acceptance Criteria

1. **shadcn/ui Sidebar installed**: `pnpm dlx shadcn@latest add sidebar` run in `pm-arbitrage-dashboard/`. All dependencies (Sheet, Separator, etc.) auto-installed. `src/components/ui/sidebar.tsx` present and functional. [Source: sprint-change-proposal-2026-03-13-dashboard-ux.md#Story-9-13, shadcn/ui Sidebar docs]

2. **AppSidebar component**: New `src/components/AppSidebar.tsx` renders a `<Sidebar collapsible="icon">` with `SidebarHeader` (app name "PM Arbitrage"), `SidebarContent` (nav group), and `SidebarFooter` (version + ConnectionStatus). [Source: sprint-change-proposal#Story-9-13 change 1]

3. **Five nav items with icons**: `SidebarMenu` renders items using `SidebarMenuButton asChild` wrapping React Router `<Link>`. Icons from `lucide-react`: `LayoutDashboard` (/), `Briefcase` (/positions), `GitCompareArrows` (/matches), `ChartLine` (/performance), `Activity` (/stress-test). [Source: sprint-change-proposal#Story-9-13 change 1, confirmed icon mapping]

4. **Pending badge on Matches**: `SidebarMenuBadge` displays pending match count (from `useDashboardMatches('pending')` — `count` field is total count from API, not page size). Badge hidden when count is 0. In expanded state: badge renders inline via `SidebarMenuBadge`. In collapsed state: override default `group-data-[collapsible=icon]:hidden` on the badge — show a small absolute-positioned indicator dot (e.g., `h-2 w-2 rounded-full bg-amber-500`) near the icon to signal pending items exist. [Source: Navigation.tsx existing pattern, sprint-change-proposal#Story-9-13 change 1]

5. **Active state preserved**: `SidebarMenuButton` `isActive` prop computed from `useLocation()` — exact match for `/`, `startsWith` for all others. Visual: sidebar-accent background on active item (shadcn/ui default theming). [Source: sprint-change-proposal#Story-9-13 change 5]

6. **Collapse to icons**: `collapsible="icon"` mode. `SidebarRail` rendered for hover-to-toggle. Keyboard shortcut `Cmd+B` / `Ctrl+B` toggles sidebar (shadcn/ui built-in). [Confirmed: user requirement for collapsible state]

7. **Collapse state persisted**: Override shadcn/ui's default cookie persistence with `localStorage` (`sidebar_open` key) since this is a Vite SPA, not SSR. Read on mount via `defaultOpen` prop on `SidebarProvider`. Store `open` state directly (not inverted). [Source: user requirement, shadcn/ui docs — "The code is yours"]

8. **TopBar component**: New `src/components/TopBar.tsx` renders a thin bar (~48px) above the main content area (to the right of sidebar). Contains: `SidebarTrigger` (left), platform health status dots (center-left), `ConnectionStatus` (right). [Source: sprint-change-proposal#Story-9-13 change 2, UX spec line 635: "Persistent header component showing composite health status"]

9. **TopBar health dots**: Simplified health indicator — colored dots (green/yellow/red using `--color-status-healthy/warning/critical`) with platform name + mode badge (LIVE/PAPER). Data from `useDashboardHealth()` hook. NOT the full `HealthComposite` card — that stays on DashboardPage. [Source: UX spec line 635-639, HealthComposite.tsx existing pattern]

10. **App.tsx restructured**: `SidebarProvider` placed inside `BrowserRouter` (AppSidebar needs router context). Remove `<div className="min-h-screen bg-panel">` wrapper — `SidebarInset` handles full-height layout. Layout: `<BrowserRouter> <SidebarProvider> <AppSidebar /> <SidebarInset> <TopBar /> <Routes>...</Routes> </SidebarInset> </SidebarProvider> </BrowserRouter>`. Remove `<Navigation />` import. [Source: sprint-change-proposal#Story-9-13 change 3, shadcn/ui docs]

11. **Navigation.tsx deleted**: Old header navigation component removed after all functionality migrated to AppSidebar + TopBar. [Source: sprint-change-proposal#Story-9-13 change 4]

12. **Mobile responsive**: On screens below `md` breakpoint, sidebar renders as a `Sheet` overlay (shadcn/ui built-in). `SidebarTrigger` in TopBar opens/closes it. Desktop: sidebar is fixed, content area adjusts width. [Source: UX spec responsive strategy, shadcn/ui Sidebar mobile behavior]

13. **Version display**: Sidebar footer shows app version. Use Vite `define` in `vite.config.ts`: `define: { __APP_VERSION__: JSON.stringify(process.env.npm_package_version) }`, then reference `declare const __APP_VERSION__: string` in the component. Displayed as `v{version}` in muted text. Alternative: `import pkg from '../../../package.json'` (Vite supports JSON imports by default). [Source: sprint-change-proposal#Story-9-13 change 1 — "version"]

14. **Page layout compatibility**: All existing pages continue to render correctly. Pages use `p-6 max-w-7xl mx-auto` (or `max-w-[1400px]`). The `SidebarInset` component handles content width adjustment automatically. No page-level layout changes required. [Source: codebase verification — DashboardPage.tsx, PositionsLayout.tsx, MatchesLayout.tsx]

15. **UX spec updated**: Update `ux-design-specification.md` line 635 to reflect the sidebar + TopBar pattern replacing the header nav. Update lines 637-639 (platform mode badges description) to reference TopBar instead of "header health bar". [Source: user instruction "Consider to update ux spec"]

16. **Build clean, tests pass**: `pnpm build` succeeds in dashboard. `pnpm test` in engine passes at baseline (2027 passed, 1 pre-existing e2e failure from DB connectivity). `pnpm lint` clean in dashboard. [Source: CLAUDE.md post-edit workflow]

## Tasks / Subtasks

- [x] **Task 1: Install shadcn/ui Sidebar component** (AC: #1)
  - [x] Run `pnpm dlx shadcn@latest add sidebar` in `pm-arbitrage-dashboard/`
  - [x] Verify `src/components/ui/sidebar.tsx` installed with all sub-components
  - [x] Verify Sheet, Separator, and other dependencies auto-installed
  - [x] Confirm `SIDEBAR_WIDTH` defaults and adjust to `"13.75rem"` (~220px) if desired

- [x] **Task 2: Create AppSidebar component** (AC: #2, #3, #4, #5, #6, #7, #13)
  - [x] Create `src/components/AppSidebar.tsx`
  - [x] Define nav items array: `{ to, label, icon, showPendingBadge? }`
  - [x] Render `<Sidebar collapsible="icon">` with `SidebarRail`
  - [x] `SidebarHeader`: app name "PM Arbitrage" (hidden when collapsed via `group-data-[collapsible=icon]:hidden`)
  - [x] `SidebarContent` → `SidebarGroup` → `SidebarMenu` with `SidebarMenuItem` for each nav item
  - [x] `SidebarMenuButton asChild` wrapping `<Link to={item.to}>` with `<item.icon />` + `<span>{label}</span>`
  - [x] Compute `isActive` per item using `useLocation()` — exact match for `/`, `pathname.startsWith()` for others
  - [x] `SidebarMenuBadge` for Matches item when `pendingCount > 0` (reuse `useDashboardMatches('pending')` — `count` field is total, not page size)
  - [x] Override `SidebarMenuBadge` collapsed visibility: remove `group-data-[collapsible=icon]:hidden` from badge, or add a separate collapsed indicator (small amber dot near icon) when `pendingCount > 0`
  - [x] `SidebarFooter`: version display (`v{version}`) + `<ConnectionStatus />` (full version with Alert in footer — footer has room)
  - [x] Keyboard accessibility: verify Tab navigation works through menu items in both expanded and collapsed states

- [x] **Task 3: Create TopBar component** (AC: #8, #9)
  - [x] Create `src/components/TopBar.tsx`
  - [x] Render thin bar: `sticky top-0 z-10 flex items-center h-12 border-b bg-surface px-4 gap-4`
  - [x] Left: `<SidebarTrigger />` (from shadcn/ui sidebar)
  - [x] Center-left: Platform health dots — map `useDashboardHealth()` data to colored dots with platform name + mode badge
  - [x] Right: `<ConnectionStatus />` — render **dot + label only** in TopBar context (suppress the disconnected Alert which would overflow `h-12`). Either: (a) pass a `compact` prop to ConnectionStatus, or (b) create a simplified inline version for TopBar
  - [x] Health dot styles: reuse `--color-status-healthy/warning/critical` CSS variables
  - [x] Mode badge: small `<Badge variant="outline">` showing `LIVE` or `PAPER` per platform
  - [x] Handle loading state: show skeleton dots while `health.isLoading`
  - [x] Handle error state: hide health section or show `?` indicator when `health.isError`

- [x] **Task 4: Restructure App.tsx layout** (AC: #10, #12)
  - [x] Import `SidebarProvider`, `SidebarInset` from `@/components/ui/sidebar`
  - [x] Import `AppSidebar` and `TopBar`
  - [x] Remove `Navigation` import
  - [x] Remove `<div className="min-h-screen bg-panel">` wrapper — `SidebarInset` handles full-height layout
  - [x] Add localStorage persistence state (`open`/`handleOpenChange` from dev notes pattern)
  - [x] New layout structure — full provider nesting order:
    ```tsx
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WebSocketProvider>
          <BrowserRouter>
            <SidebarProvider open={open} onOpenChange={handleOpenChange}>
              <AppSidebar />
              <SidebarInset>
                <TopBar />
                <Routes>...</Routes>
              </SidebarInset>
            </SidebarProvider>
          </BrowserRouter>
          <Toaster />
        </WebSocketProvider>
      </TooltipProvider>
    </QueryClientProvider>
    ```
  - [x] Verify `Toaster` position doesn't overlap with TopBar (Sonner defaults to bottom-right — should be fine)
  - [x] Verify mobile Sheet behavior works with existing routing
  - [x] Verify Dialog components (CloseAllDialog, MatchApprovalDialog) z-index doesn't conflict with Sheet overlay

- [x] **Task 5: Delete Navigation.tsx** (AC: #11)
  - [x] Remove `src/components/Navigation.tsx`
  - [x] Remove all imports of `Navigation` across codebase (only `App.tsx`)
  - [x] Verify no other component references `Navigation`

- [x] **Task 6: Verify page layout compatibility** (AC: #14, #16)
  - [x] Navigate all routes: `/`, `/positions/open`, `/positions/all`, `/positions/:id`, `/matches/approved`, `/matches/pending`, `/matches/rejected`, `/matches/:id`, `/performance`, `/stress-test`
  - [x] Verify: no horizontal scrollbar on main content area
  - [x] Verify: content area width adjusts dynamically when sidebar toggles between expanded/collapsed
  - [x] Verify: page headings and DataTable columns don't get cut off
  - [x] Verify: tab-based routing (MatchesLayout, PositionsLayout) still works — tabs render inside main content, not sidebar
  - [x] Verify: URL query params persist after sidebar toggle (e.g., `?mode=live&sort=pnl&page=2` survives expand/collapse)
  - [x] Verify: cross-entity navigation links (from story 9-12) still work — position pair name links to match detail
  - [x] Verify: mobile Sheet overlay slides in from left, closes on route change
  - [x] Run `pnpm build` — verify clean build
  - [x] Run `pnpm lint` — fix any issues

- [x] **Task 7: Update UX spec** (AC: #15)
  - [x] In `_bmad-output/planning-artifacts/ux-design-specification.md`:
    - Update line 635: "Persistent header component" → "Persistent TopBar component above main content (to the right of the left sidebar)" showing composite health status
    - Update lines 637-639: "header health bar" → "TopBar health indicator"
    - Add note: "Navigation moved to collapsible left sidebar (shadcn/ui Sidebar component) — scales to future pages"

## Dev Notes

### Design Direction

**Aesthetic: Industrial-utilitarian with refined precision.** This is a trading dashboard — the operator needs stability, predictability, and information density. No decorative elements.

- **Sidebar background**: Uses existing `--sidebar` theme token (light: near-white `oklch(0.985 0 0)`, dark: dark gray `oklch(0.205 0 0)`)
- **Active state**: `sidebar-accent` background — shadcn/ui's built-in styling. Clean, subtle highlight.
- **Typography**: `text-sm` Inter. No custom fonts for nav items.
- **Icons**: 18px lucide-react icons. Muted color when inactive, foreground when active (shadcn handles this).
- **Hover**: `sidebar-accent` background on hover (shadcn default, ~150ms transition).
- **Collapsed state**: Icons centered, labels hidden, tooltips on hover (shadcn built-in behavior with Tooltip component — already installed).
- **TopBar**: Minimal. `bg-surface` (white), thin `border-b`, only status indicators. No branding or decorative elements.
- **Color discipline**: Only `--color-status-healthy/warning/critical` for health dots. Everything else grayscale. [Source: UX spec lines 917-919: "Semantic only: Green/yellow/red reserved for health status, never decorative"]

### Architecture Decisions

**Why shadcn/ui Sidebar (not custom):**
- Composable component architecture with `SidebarProvider` context
- Built-in `collapsible="icon"` mode with smooth transitions
- Built-in mobile Sheet drawer — no custom responsive logic needed
- `SidebarMenuBadge` for the pending count badge
- `SidebarRail` for edge-hover toggle
- Keyboard shortcut `Cmd+B` / `Ctrl+B` out of the box
- Theming via existing `--sidebar-*` CSS variables (already defined in `index.css`)
- [Source: shadcn/ui docs — "The code is yours. Use sidebar.tsx as a starting point"]

**Why localStorage over cookies for collapse state:**
- Vite SPA, not SSR/Next.js — no server-side cookie reading
- Simpler: `localStorage.getItem('sidebar_open')` on mount
- Implementation: Use controlled `SidebarProvider` with `open`/`onOpenChange` that read/write `localStorage`
- Key name `sidebar_open` stores boolean directly — no inverted semantics

**TopBar is separate from sidebar (not SidebarHeader):**
- TopBar sits above the MAIN CONTENT area, not inside the sidebar
- Health status must remain visible when sidebar is collapsed
- `SidebarTrigger` in TopBar is the primary toggle for mobile
- [Source: UX spec line 635, sprint-change-proposal change 2]

### Key Integration Points

**React Router + SidebarMenuButton:**
```tsx
// Pattern for each nav item
const location = useLocation();
const isActive = item.to === '/'
  ? location.pathname === '/'
  : location.pathname.startsWith(item.to);

<SidebarMenuButton asChild isActive={isActive}>
  <Link to={item.to}>
    <item.icon />
    <span>{item.label}</span>
  </Link>
</SidebarMenuButton>
```
Do NOT use `NavLink` — `SidebarMenuButton` manages its own active styles via the `isActive` prop. Using `NavLink`'s className function would conflict with shadcn's `data-active` attribute styling.

**Pending badge pattern:**
```tsx
// Reuse exact hook from deleted Navigation.tsx
const pendingMatches = useDashboardMatches('pending');
const pendingCount = pendingMatches.data?.count ?? 0;

// In Matches SidebarMenuItem:
{pendingCount > 0 && <SidebarMenuBadge>{pendingCount}</SidebarMenuBadge>}
```

**TopBar health dots pattern:**
```tsx
// Simplified from HealthComposite — dots only, no DashboardPanel wrapper
const health = useDashboardHealth();
{health.data?.map(p => (
  <div key={p.platformId} className="flex items-center gap-1.5">
    <span className={`h-2 w-2 rounded-full ${STATUS_DOT[p.status]}`} />
    <span className="text-xs text-muted-foreground capitalize">{p.platformId}</span>
    <Badge variant="outline" className="text-[10px] px-1 py-0">{p.mode.toUpperCase()}</Badge>
  </div>
))}
```

**localStorage persistence pattern:**
```tsx
const STORAGE_KEY = 'sidebar_open';

function getInitialOpen(): boolean {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === null ? true : stored === 'true'; // default open on first visit
}

// In App.tsx:
const [open, setOpen] = useState(getInitialOpen);
const handleOpenChange = (value: boolean) => {
  setOpen(value);
  localStorage.setItem(STORAGE_KEY, String(value)); // store open state directly
};

<SidebarProvider open={open} onOpenChange={handleOpenChange}>
```

### Existing Files Reference

**Files to DELETE:**
- `pm-arbitrage-dashboard/src/components/Navigation.tsx` — replaced by AppSidebar + TopBar

**Files to CREATE:**
- `pm-arbitrage-dashboard/src/components/AppSidebar.tsx` — main sidebar component
- `pm-arbitrage-dashboard/src/components/TopBar.tsx` — persistent health status bar
- `pm-arbitrage-dashboard/src/components/ui/sidebar.tsx` — installed by shadcn CLI
- `pm-arbitrage-dashboard/src/components/ui/sheet.tsx` — auto-installed as sidebar dependency
- `pm-arbitrage-dashboard/src/components/ui/separator.tsx` — auto-installed if needed

**Files to MODIFY:**
- `pm-arbitrage-dashboard/src/App.tsx` — layout restructure (SidebarProvider wrapper, remove Navigation import)
- `_bmad-output/planning-artifacts/ux-design-specification.md` — update navigation/health references (lines 635, 637-639)

**Files to VERIFY (no changes expected):**
- `pm-arbitrage-dashboard/src/index.css` — sidebar CSS variables already defined, should work as-is
- `pm-arbitrage-dashboard/src/pages/DashboardPage.tsx` — HealthComposite stays, verify layout
- `pm-arbitrage-dashboard/src/pages/PositionsLayout.tsx` — verify tab routing
- `pm-arbitrage-dashboard/src/pages/MatchesLayout.tsx` — verify tab routing
- `pm-arbitrage-dashboard/src/components/ConnectionStatus.tsx` — reused in TopBar and SidebarFooter
- `pm-arbitrage-dashboard/src/hooks/useDashboard.ts` — existing hooks reused, no changes

### Prior Story Patterns (from 9-11, 9-12)

- **Layout components as separate files**: MatchesLayout.tsx, PositionsLayout.tsx — follow same pattern for AppSidebar.tsx
- **NavLink with ARIA roles**: 9-11 added `role="tablist"`, `role="tab"`, `aria-selected`. Sidebar gets ARIA automatically from shadcn/ui components.
- **URL state preservation**: Query params (sort, order, page, cluster) must survive sidebar toggle and navigation. Verify after integration.
- **Cross-entity navigation links**: Position → Match links (from 9-12) must still work within the new layout.

### Dependency Versions (verified from package.json)

| Package | Version | Relevant |
|---------|---------|----------|
| react | ^19.2.0 | SidebarProvider context |
| react-router-dom | ^7.13.1 | Link, useLocation for active state |
| lucide-react | ^0.575.0 | Nav icons (LayoutDashboard, Briefcase, GitCompareArrows, ChartLine, Activity) |
| radix-ui | ^1.4.3 | Sidebar primitives (Sheet, Tooltip) |
| tailwindcss | ^4.2.1 | Theme tokens, responsive classes |
| shadcn (dev) | ^3.8.5 | CLI for component installation |

### Test Baseline

- **Engine tests**: 2027 passed, 1 failed (pre-existing e2e DB connectivity), 2 todo (115 files)
- **Dashboard build**: Clean (`pnpm build` succeeds, 572KB JS bundle)
- **This story is frontend-only**: No backend changes. No new backend tests needed. Verify dashboard `pnpm build` and `pnpm lint` only.

### What NOT To Do

- Do NOT create a custom sidebar from scratch — use shadcn/ui Sidebar component
- Do NOT use `NavLink` with `className` function — use `Link` with `SidebarMenuButton isActive` prop instead
- Do NOT move `HealthComposite` out of `DashboardPage` — TopBar shows a simplified dot indicator, the full card stays on the dashboard
- Do NOT change page-level padding/max-width — `SidebarInset` handles layout width automatically
- Do NOT add dark mode toggle to sidebar — not in scope, system already has dark mode CSS vars defined for future use
- Do NOT use shadcn's cookie persistence — this is a Vite SPA, use `localStorage`

### References

- [Source: sprint-change-proposal-2026-03-13-dashboard-ux.md#Story-9-13] — Original story definition (lines 140-152)
- [Source: ux-design-specification.md#line-635] — "Persistent header component showing composite health status"
- [Source: ux-design-specification.md#lines-637-639] — Platform mode badges in health bar
- [Source: ux-design-specification.md#lines-917-919] — "Semantic only: Green/yellow/red reserved for health status"
- [Source: ux-design-specification.md#line-576] — "Nothing moves unless you move it: Interface stability"
- [Source: shadcn/ui Sidebar docs] — Component API, collapsible modes, theming, SidebarMenuBadge, SidebarRail
- [Source: Navigation.tsx] — Current nav items array, pending badge pattern, ConnectionStatus placement
- [Source: App.tsx] — Current layout structure (min-h-screen bg-panel wrapper)
- [Source: index.css] — Existing `--sidebar-*` CSS variables in oklch format
- [Source: HealthComposite.tsx] — STATUS_STYLES mapping, PlatformHealthDto type

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
None — clean implementation, no debugging sessions needed.

### Completion Notes List
- Installed shadcn/ui Sidebar via `pnpm dlx shadcn@latest add sidebar --overwrite` — installed sidebar.tsx, sheet.tsx, separator.tsx, skeleton.tsx, use-mobile.ts; updated button.tsx, tooltip.tsx, input.tsx
- Fixed shadcn-generated lint issues: `Math.random()` in SidebarMenuSkeleton replaced with deterministic width; `react-refresh/only-export-components` suppressed on `useSidebar` and `buttonVariants` exports (standard shadcn patterns)
- Created AppSidebar.tsx: 5 nav items with lucide icons, active state via `useLocation()`, pending badge on Matches (SidebarMenuBadge in expanded, amber dot near icon in collapsed), version display via Vite `define`, ConnectionStatus in footer
- Created TopBar.tsx: SidebarTrigger + separator, health dots (colored by status with platform name + mode badge), compact ConnectionStatus (no Alert overflow)
- Added `compact` prop to ConnectionStatus.tsx — suppresses the disconnected Alert in TopBar context
- Added `__APP_VERSION__` define to vite.config.ts
- Restructured App.tsx: SidebarProvider with localStorage persistence (`sidebar_open` key, `open`/`onOpenChange` controlled mode), AppSidebar + SidebarInset + TopBar layout, removed Navigation import and `min-h-screen bg-panel` wrapper
- Deleted Navigation.tsx
- Updated ux-design-specification.md line 635 + 637 to reference sidebar + TopBar pattern
- Build clean (tsc + vite), lint clean
- **Code review #2 fix**: Added `SidebarTrigger` + `Separator` to TopBar.tsx (was missing — broke mobile navigation). Reverted max-width removal from 7 page files (violated AC #14 "no page-level layout changes required"). Documented `overflow-auto` wrapper in App.tsx.

### File List
**Created:**
- `pm-arbitrage-dashboard/src/components/AppSidebar.tsx`
- `pm-arbitrage-dashboard/src/components/TopBar.tsx`
- `pm-arbitrage-dashboard/src/components/ui/sidebar.tsx` (shadcn install)
- `pm-arbitrage-dashboard/src/components/ui/sheet.tsx` (shadcn install)
- `pm-arbitrage-dashboard/src/components/ui/separator.tsx` (shadcn install)
- `pm-arbitrage-dashboard/src/components/ui/skeleton.tsx` (shadcn install)
- `pm-arbitrage-dashboard/src/hooks/use-mobile.ts` (shadcn install)

**Modified:**
- `pm-arbitrage-dashboard/src/App.tsx` — layout restructure
- `pm-arbitrage-dashboard/src/components/ConnectionStatus.tsx` — added `compact` prop
- `pm-arbitrage-dashboard/src/components/ui/button.tsx` — shadcn update + lint suppress
- `pm-arbitrage-dashboard/src/components/ui/tooltip.tsx` — shadcn update
- `pm-arbitrage-dashboard/src/components/ui/input.tsx` — shadcn update
- `pm-arbitrage-dashboard/vite.config.ts` — added `__APP_VERSION__` define
- `_bmad-output/planning-artifacts/ux-design-specification.md` — sidebar + TopBar references

**Deleted:**
- `pm-arbitrage-dashboard/src/components/Navigation.tsx`
