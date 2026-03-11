# Story 9-4a: Stress Test Dashboard Page

Status: done

## Story

As an operator,
I want a dedicated dashboard page to visualize stress test results, trigger manual runs, and review parameter suggestions,
So that I can validate my risk parameters at a glance without making raw API calls.

## Acceptance Criteria

1. **Given** a stress test has been run previously, **When** the operator navigates to `/stress-test`, **Then** the page displays the latest stress test results with: VaR at 95% and 99%, worst-case loss, bankroll, drawdown probabilities (>15%, >20%, >25%) with color-coded thresholds, and run metadata (run timestamp, scenario count, position count). [Source: Story 9-4 StressTestResultDto, sprint-change-proposal §UX Design]

2. **Given** the latest stress test emitted an alert (`alertEmitted: true`), **When** the page loads, **Then** a prominent alert banner displays all parameter tightening suggestions from the `suggestions[]` array. [Source: Story 9-4 AC#2, StressTestResultDto.suggestions field]

3. **Given** the operator clicks "Run Stress Test", **When** the simulation completes, **Then** the page updates immediately with fresh results and shows a success toast. **And** the button shows a loading state while the simulation runs. **And** errors display a toast with failure context. [Source: Story 9-4 POST /api/risk/stress-test endpoint]

4. **Given** no stress test has ever been run, **When** the operator navigates to `/stress-test`, **Then** a friendly empty state prompts: "No stress test results yet" with a prominent "Run Stress Test" button. [Source: StressTestController GET /latest returns 404 with error code 4008]

5. **Given** stress test results contain scenario details, **When** the operator wants to drill deeper, **Then** collapsible panels show: P&L distribution percentiles, synthetic scenario results, and per-contract volatilities. [Source: StressTestResultDto.scenarioDetails nested object]

## Tasks / Subtasks

- [x] **Task 0: Backend — add `runTimestamp` to stress test DTO** (AC: #1)
  - [x] Add `runTimestamp!: string` field with `@ApiProperty({ description: 'Timestamp of the stress test run (ISO 8601)', type: String })` to `StressTestResultDto` in `pm-arbitrage-engine/src/modules/risk-management/dto/stress-test.dto.ts`
  - [x] In `stress-test.controller.ts` GET /latest handler: map `runTimestamp: latest.timestamp.toISOString()`
  - [x] In `stress-test.controller.ts` POST handler: map `runTimestamp: new Date().toISOString()`
  - [x] Update `stress-test.controller.spec.ts` to assert `runTimestamp` presence in responses
  - [x] Run `pnpm lint` and `pnpm test` in pm-arbitrage-engine/

- [x] **Task 1: Regenerate API client** (AC: #1, #3)
  - [x] Start the engine (`pnpm start:dev` in pm-arbitrage-engine/) so Swagger spec is served at `/api/docs-json`
  - [x] Run `pnpm generate-api` in pm-arbitrage-dashboard/ to regenerate `src/api/generated/Api.ts`
  - [x] Verify `StressTestResultDto`, `StressTestResponseDto`, `StressTestTriggerResponseDto` types appear in generated code with the new `runTimestamp` field
  - [x] Note the actual generated method names for the stress test controller (see Hook Design section below)

- [x] **Task 2: Add stress test hooks** (AC: #1, #3, #4)
  - [x] `useStressTestLatest()` — `GET /api/risk/stress-test/latest`, staleTime 60s, no auto-refetch interval. 404 → empty state (not error).
  - [x] `useRunStressTest()` — `useMutation` wrapping `POST /api/risk/stress-test`. On success: set query data directly from response (instant update), toast "Stress test completed". On error: toast with context.

- [x] **Task 3: Create `StressTestPage` component** (AC: #1–#5)
  - [x] Local `StressMetricCard` helper (DashboardPanel + value + optional subtitle) — do NOT use MetricDisplay directly
  - [x] Header section: title, run metadata subtitle (timestamp + scenario/position counts), "Run Stress Test" button (right-aligned)
  - [x] Key metrics row: 4-column grid of `StressMetricCard` (VaR 95%, VaR 99%, Worst-Case Loss, Bankroll) with % of bankroll subtitles and threshold coloring
  - [x] Drawdown probabilities panel: 3 rows with label, percentage value, visual bar, color coding per thresholds
  - [x] Alert/suggestions panel: conditional render when `alertEmitted === true`, amber Alert component listing each suggestion
  - [x] P&L distribution panel: collapsible (default open), horizontal table of percentile values with red/green coloring
  - [x] Synthetic scenarios panel: collapsible (default open), two-column table (humanized name + P&L)
  - [x] Contract volatilities panel: collapsed by default, expandable table (contract, platform, vol, source)
  - [x] Empty state: centered message + prominent Run button when GET /latest returns 404
  - [x] Loading state: skeleton cards matching existing dashboard pattern
  - [x] Zero positions state: normal layout with $0.00 / 0.0% values, header subtitle "0 positions — empty portfolio"
  - [x] Scenario name humanization: `humanizeScenarioName(name: string)` local helper — kebab-case to title case, `cluster-blowup-{id}` → "Cluster Blowup — {id}" with em-dash
  - [x] Error state: red banner matching `PerformancePage` error pattern

- [x] **Task 4: Add route and navigation** (AC: #1)
  - [x] Add `<Route path="/stress-test" element={<StressTestPage />} />` to `App.tsx`
  - [x] Add `{ to: '/stress-test', label: 'Stress Test' }` to `navItems` array in `Navigation.tsx` (5th item, after Performance)

- [x] **Task 5: Formatting utilities** (AC: #1)
  - [x] Add `formatUsd(value: string): string` to `src/lib/utils.ts`
    - Handles: comma separators, 2 decimal places, `$` prefix, negative values as `-$123.45`
    - Defensive: return `$0.00` for empty/null/NaN inputs
  - [x] Add `formatPercent(value: string): string` to `src/lib/utils.ts`
    - Multiply decimal string by 100, format to 1 decimal place, append `%`
    - Example: `"0.123000"` → `"12.3%"`, `"0.008000"` → `"0.8%"`

## Dev Notes

### Architecture Context

This story is **primarily frontend** (dashboard SPA) with a **small backend addition** (exposing `runTimestamp` in the stress test DTO). The backend endpoints (`POST /api/risk/stress-test`, `GET /api/risk/stress-test/latest`) were delivered in Story 9-4 and are already functional. [Source: pm-arbitrage-engine/src/modules/risk-management/stress-test.controller.ts]

The page follows the same patterns established in the 6 existing dashboard pages: TanStack Query hooks in `useDashboard.ts`, generated API client via `swagger-typescript-api`, `DashboardPanel` components, shadcn/ui primitives. [Source: pm-arbitrage-dashboard/src/]

### Backend Change: `runTimestamp`

The `StressTestResultDto` currently lacks the run timestamp. The Prisma `StressTestRun` model stores a `timestamp` field (DateTime @db.Timestamptz) but the controller doesn't expose it in the response. [Source: pm-arbitrage-engine/src/modules/risk-management/stress-test.controller.ts, dto/stress-test.dto.ts, prisma/schema.prisma StressTestRun model]

Add `runTimestamp: string` (ISO 8601) to `StressTestResultDto`. Controller mapping:
- **GET /latest:** `runTimestamp: latest.timestamp.toISOString()` — uses the persisted run timestamp
- **POST /trigger:** `runTimestamp: new Date().toISOString()` — trigger time approximates run time

**Backend files to modify:**
- `src/modules/risk-management/dto/stress-test.dto.ts` — add field to `StressTestResultDto`
- `src/modules/risk-management/stress-test.controller.ts` — map field in both `getLatestResult()` and `triggerStressTest()` methods
- `src/modules/risk-management/stress-test.controller.spec.ts` — update response assertions

**Run `pnpm lint` and `pnpm test` in pm-arbitrage-engine/ after backend changes.**

### Page Layout Design

The page answers one primary question: **"Are my risk parameters calibrated correctly?"**

Information hierarchy follows progressive disclosure (2s glance → 10s review → 2min deep dive):

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER                                                      │
│ Stress Testing                              [Run Stress Test]│
│ Last run: Mar 13, 2026 00:00 UTC · 1003 scenarios          │
├─────────────────────────────────────────────────────────────┤
│ KEY METRICS (4-column grid of StressMetricCard)             │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐ │
│ │ VaR (95%)  │ │ VaR (99%)  │ │ Worst Case │ │ Bankroll  │ │
│ │  $142.50   │ │  $287.30   │ │  $412.80   │ │$10,000.00 │ │
│ │  1.4% bank │ │  2.9% bank │ │  4.1% bank │ │           │ │
│ └────────────┘ └────────────┘ └────────────┘ └───────────┘ │
├─────────────────────────────────────────────────────────────┤
│ DRAWDOWN PROBABILITIES (DashboardPanel)                     │
│                                                             │
│  >15% drawdown   12.3%  ████████████░░░░░░░░  amber        │
│  >20% drawdown    3.2%  ███░░░░░░░░░░░░░░░░░  green        │
│  >25% drawdown    0.8%  █░░░░░░░░░░░░░░░░░░░  green        │
│                                                             │
│  ── 5% alert threshold (dashed line visual reference) ──    │
├─────────────────────────────────────────────────────────────┤
│ ALERT BANNER (conditional — only when alertEmitted=true)    │
│ ⚠ Risk Alert — Parameter Suggestions                       │
│ • Cluster 'Elections' at 12% exposure — reduce correlated   │
│   positions to lower tail risk                              │
│ • Reduce RISK_MAX_POSITION_PCT from 3% to 2% — large       │
│   positions drive tail losses                               │
├─────────────────────────────────────────────────────────────┤
│ P&L DISTRIBUTION (collapsible, default open)                │
│ ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────┐ │
│ │  p5  │ p10  │ p25  │ p50  │ p75  │ p90  │ p95  │  p99   │ │
│ │-$287 │-$195 │ -$82 │ +$15 │ +$98 │+$185 │+$241 │ +$320  │ │
│ └──────┴──────┴──────┴──────┴──────┴──────┴──────┴────────┘ │
├─────────────────────────────────────────────────────────────┤
│ SYNTHETIC SCENARIOS (collapsible, default open)             │
│ ┌────────────────────────────────┬─────────────────────────┐ │
│ │ Scenario                       │ Portfolio P&L           │ │
│ │ Correlation-1 Stress           │ -$412.80                │ │
│ │ Cluster Blowup — Elections     │ -$287.30                │ │
│ │ Liquidity Gap                  │ -$198.50                │ │
│ └────────────────────────────────┴─────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ CONTRACT VOLATILITIES (collapsed by default)                │
│ ▸ Show volatility details (N contracts)                     │
│   ┌───────────────┬────────────┬────────┬─────────────────┐ │
│   │ Contract       │ Platform   │ Vol    │ Source          │ │
│   │ abc-123        │ Kalshi     │ 0.028  │ Historical      │ │
│   │ def-456        │ Polymarket │ 0.030  │ Default (0.03)  │ │
│   └───────────────┴────────────┴────────┴─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### StressMetricCard (local component)

`MetricDisplay` only supports `{ label, value, className }` — no subtitle prop. [Source: pm-arbitrage-dashboard/src/components/MetricDisplay.tsx] Create a local `StressMetricCard` inside `StressTestPage.tsx` that wraps `DashboardPanel` with a large value and an optional subtitle line:

```tsx
function StressMetricCard({ label, value, subtitle, className }: {
  label: string;
  value: string;
  subtitle?: string;
  className?: string;
}) {
  return (
    <DashboardPanel title={label} className={className}>
      <p className="font-mono text-2xl tabular-nums font-semibold">{value}</p>
      {subtitle && (
        <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
      )}
    </DashboardPanel>
  );
}
```

This follows the same local-helper pattern as `BalanceMetric` in `DashboardPage.tsx`. [Source: pm-arbitrage-dashboard/src/pages/DashboardPage.tsx]

### Color Coding Thresholds

**Drawdown probabilities:**
- Green (`text-green-500`): probability < 2%
- Amber (`text-amber-500`): 2% ≤ probability < 5%
- Red (`text-red-500`): probability ≥ 5%

The >20% row is the alert threshold — when red, the system has emitted a `STRESS_TEST_ALERT` event. Note: alert fires at `> 0.05` (strict) while Red starts at `>= 5%` — at exactly 5.0%, the row is Red but `alertEmitted` is false. This edge case is acceptable. [Source: Story 9-4 alert logic, stress-test.service.ts checks `drawdown20PctProbability > 0.05`]

**VaR / Worst-Case Loss (subtitle shows % of bankroll):**
- Green: < 5% of bankroll
- Amber: 5–10% of bankroll
- Red: ≥ 10% of bankroll

### States

| State | Behavior |
|-------|----------|
| **Empty** | GET /latest returns 404 (error code 4008, body: `{ error: { code: 4008, message: "No stress test runs found", severity: "info" }, timestamp }`). Show centered empty state: "No stress test results yet. Run your first stress test to validate portfolio tail risk." + prominent Run button. [Source: stress-test.controller.ts getLatestResult()] |
| **Loading** | Skeleton cards (3 rows of pulsing rectangles, matching existing dashboard pattern with `animate-pulse`). [Source: DashboardPage.tsx loading pattern] |
| **Data** | Full page layout as designed above. |
| **Running** | Button shows spinner + "Running..." text, disabled. On completion: toast "Stress test completed", page updates with fresh data. |
| **Zero positions** | Normal layout but metrics show $0.00 / 0.0%. Header subtitle: "0 positions — empty portfolio". |
| **Error** | Red error banner: "Failed to load stress test data. Check backend connectivity." [Source: PerformancePage.tsx error pattern] |

### API Response Shape (from `StressTestResultDto`)

```typescript
{
  runTimestamp: string;              // ISO 8601 — NEW (Task 0), e.g. "2026-03-13T00:00:00.000Z"
  numScenarios: number;
  numPositions: number;
  bankrollUsd: string;               // Decimal as string, e.g. "10000.00000000"
  var95: string;                     // USD as string
  var99: string;                     // USD as string
  worstCaseLoss: string;             // USD as string
  drawdown15PctProbability: string;  // 0.000000–1.000000
  drawdown20PctProbability: string;
  drawdown25PctProbability: string;
  alertEmitted: boolean;
  suggestions: string[];
  scenarioDetails: {
    percentiles: Record<string, string>;  // Dynamic keys, e.g. { p1: "...", p5: "-287.30", p10: "...", ..., p99: "..." }
    syntheticResults: { name: string; portfolioPnl: string }[];
    volatilities: { contractId: string; platform: string; vol: string; source: string }[];
  };
}
```

Wrapped in standard response: `{ data: StressTestResultDto, timestamp: string }`. [Source: pm-arbitrage-engine/src/modules/risk-management/dto/stress-test.dto.ts, stress-test.controller.ts]

GET /latest returns 404 when no runs exist. The 404 body is a structured error (not empty). The hook's `retry` function returns `false` for 404, so TanStack Query immediately enters error state. The page component differentiates 404 (empty state) from other errors (error state). [Source: stress-test.controller.ts getLatestResult()]

### Monetary Value Formatting

All values from the DTO arrive as strings (Decimal serialized). Format for display:
- Dollar values: `$1,234.56` (2 decimal places, comma separators, `$` prefix)
- Negative: `-$123.45`
- Probabilities: `12.3%` (multiply by 100, 1 decimal place)
- Volatilities: `0.028` (3 decimal places, no conversion)

### Synthetic Scenario Name Humanization

Transform raw scenario names for display:
- `correlation-1-stress` → "Correlation-1 Stress"
- `cluster-blowup-{id}` → "Cluster Blowup — {id}"
- `liquidity-gap` → "Liquidity Gap"

Simple kebab-case to title-case transform, with cluster ID separated by em-dash. [Source: Story 9-4 StressTestService synthetic scenario naming]

### Collapsible Panel Pattern

Use a simple `useState<boolean>` toggle with a clickable header. No accordion library needed:

```tsx
const [open, setOpen] = useState(true); // or false for collapsed-by-default
<DashboardPanel title={...}>
  <button onClick={() => setOpen(!open)} className="flex items-center gap-1 text-sm text-muted-foreground mb-2">
    {open ? '▾' : '▸'} {open ? 'Hide' : 'Show'} details ({items.length})
  </button>
  {open && <Table>...</Table>}
</DashboardPanel>
```

P&L Distribution and Synthetic Scenarios default **open**. Contract Volatilities defaults **closed**. [Source: sprint-change-proposal §Progressive Disclosure]

### Drawdown Bar Visualization

CSS-based bars using Tailwind. Each bar is a div with width proportional to probability:

```tsx
<div
  className={cn('h-5 rounded', colorClass)}
  style={{ width: `${Math.min(prob * 100 / 25, 100)}%` }}
/>
```

Scale: 25% probability = full width. This ensures even small probabilities (0.8%) produce a visible bar. The 5% alert threshold can be marked with a dashed vertical line positioned at 20% of the bar track width (5/25 = 20%).

### Existing Components to Reuse

| Component | Usage | Source |
|-----------|-------|--------|
| `DashboardPanel` | Wraps each section (drawdown, percentiles, scenarios, volatilities) | `src/components/DashboardPanel.tsx` — props: `{ title, children, className }` |
| `Table` / `TableRow` / `TableHead` / `TableCell` | Percentile table, scenarios table, volatilities table | `src/components/ui/table.tsx` |
| `Alert` / `AlertDescription` | Risk alert banner with parameter suggestions | `src/components/ui/alert.tsx` |
| `Badge` | Run metadata tags (position count) | `src/components/ui/badge.tsx` |
| `Button` | "Run Stress Test" trigger button | `src/components/ui/button.tsx` |
| `Tooltip` / `TooltipTrigger` / `TooltipContent` | Abbreviation explanations (e.g., "VaR" → "Value at Risk") | `src/components/ui/tooltip.tsx` |
| `cn()` utility | Conditional class merging | `src/lib/utils.ts` |

**Do NOT use `MetricDisplay` directly** — it lacks subtitle support. Use the local `StressMetricCard` helper instead. [Source: src/components/MetricDisplay.tsx — props: `{ label, value, className }` only]

### Navigation Placement

"Stress Test" is added as the 5th top-level nav item after "Performance". Full nav:

`Dashboard | Positions | Matches | Performance | Stress Test`

Current `navItems` array has 4 entries. Append at index 4. No `showPendingBadge` needed. [Source: pm-arbitrage-dashboard/src/components/Navigation.tsx lines 7-12]

### Hook Design

```typescript
// In useDashboard.ts — add these two hooks
// Imports needed: useQuery, useMutation, useQueryClient from '@tanstack/react-query'
// Already imported in file: isAxiosError from 'axios', toast from 'sonner', api from '@/api/client'

export function useStressTestLatest() {
  return useQuery({
    queryKey: ['stress-test', 'latest'],
    queryFn: () => api.stressTestControllerGetLatestResult(), // ← use actual generated name from Task 1
    select: (res) => res.data,
    staleTime: 60_000,
    retry: (failureCount, error) => {
      // Don't retry 404s — that's just "no data yet"
      if (isAxiosError(error) && error.response?.status === 404) return false;
      return failureCount < 2;
    },
  });
}

export function useRunStressTest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.stressTestControllerTriggerStressTest(), // ← use actual generated name from Task 1
    onSuccess: (data) => {
      queryClient.setQueryData(['stress-test', 'latest'], data);
      toast.success('Stress test completed');
    },
    onError: (error) => {
      if (isAxiosError(error)) {
        toast.error('Stress test failed — check engine logs');
      } else {
        toast.error('Connection failed');
      }
    },
  });
}
```

**IMPORTANT:** The API method names above are illustrative. After Task 1 (regenerate API client), check `src/api/generated/Api.ts` for the actual generated method names. `swagger-typescript-api` derives names from `@ApiTags` + controller class + method names. The controller is `StressTestController` with methods `triggerStressTest()` and `getLatestResult()`. [Source: pm-arbitrage-engine/src/modules/risk-management/stress-test.controller.ts]

**404 handling in page component:**
```typescript
if (query.isLoading) return <LoadingSkeleton />;
if (query.isError) {
  if (isAxiosError(query.error) && query.error.response?.status === 404) {
    return <EmptyState onRun={...} />;
  }
  return <ErrorBanner />;
}
// query.data is StressTestResultDto — render full page
```

[Source: useDashboard.ts existing patterns — `isAxiosError` from 'axios', `toast` from 'sonner']

### Dependency Versions (verified)

| Dependency | Version | Relevant APIs |
|-----------|---------|---------------|
| React | 19.2.0 | `useState`, `ReactNode` |
| TanStack Query | 5.90.21 | `useQuery`, `useMutation`, `useQueryClient` |
| React Router | 7.13.1 | `<Route>`, `<NavLink>` |
| Sonner | 2.0.7 | `toast.success()`, `toast.error()` |
| Tailwind | 4.2.1 | Utility classes, `animate-pulse` |
| Axios | 1.13.6 | `isAxiosError()` |
| TypeScript | 5.9.3 | Strict mode |

[Source: pm-arbitrage-dashboard/package.json]

### Project Structure

**Backend (pm-arbitrage-engine/) — Task 0 only:**
- `src/modules/risk-management/dto/stress-test.dto.ts` — modify (add `runTimestamp` field)
- `src/modules/risk-management/stress-test.controller.ts` — modify (map field in both endpoints)
- `src/modules/risk-management/stress-test.controller.spec.ts` — modify (update response assertions)

**Frontend (pm-arbitrage-dashboard/) — Tasks 1–5:**

New files:
- `src/pages/StressTestPage.tsx` — main page component (~250-400 lines)

Modified files:
- `src/App.tsx` — add route + import [Source: current 6 routes at lines 27-33]
- `src/components/Navigation.tsx` — add nav item to `navItems` array [Source: 4 items at lines 7-12]
- `src/hooks/useDashboard.ts` — add `useStressTestLatest()` + `useRunStressTest()` hooks [Source: existing ~15 hooks]
- `src/api/generated/Api.ts` — regenerated from engine Swagger spec (adds stress test endpoint methods)
- `src/lib/utils.ts` — add `formatUsd()` utility [Source: currently only has `cn()` utility]

### Testing

The dashboard repo has **no test infrastructure** — no test framework, no test scripts, no spec files. Quality is ensured via TypeScript strict mode + ESLint. [Source: pm-arbitrage-dashboard/package.json — scripts: dev, build, lint, preview, generate-api only]

**Verification:** After all frontend changes, run `pnpm build` and `pnpm lint` in pm-arbitrage-dashboard/ to ensure clean compilation.

**Backend tests:** After Task 0, run `pnpm test` and `pnpm lint` in pm-arbitrage-engine/ to verify no regressions.

### Post-Edit Workflow

1. Backend changes (Task 0) in pm-arbitrage-engine/:
   - Make DTO + controller changes
   - `pnpm lint` → `pnpm test` → verify green
2. Start engine: `pnpm start:dev` in pm-arbitrage-engine/
3. Regenerate API client (Task 1) in pm-arbitrage-dashboard/:
   - `pnpm generate-api`
   - Verify generated types include `runTimestamp`
4. Frontend changes (Tasks 2–5) in pm-arbitrage-dashboard/:
   - `pnpm lint` → `pnpm build` → verify clean
5. Manual smoke test: navigate to `/stress-test`, verify empty state, trigger run, verify data display

### References

- [Source: Story 9-4] — Backend implementation, StressTestResultDto, API endpoints, alert logic
- [Source: pm-arbitrage-engine/src/modules/risk-management/stress-test.controller.ts] — Controller with POST/GET endpoints, 404 handling (code 4008), response mapping
- [Source: pm-arbitrage-engine/src/modules/risk-management/dto/stress-test.dto.ts] — DTO definitions: StressTestResultDto, StressTestResponseDto, StressTestTriggerResponseDto
- [Source: pm-arbitrage-engine/src/modules/risk-management/stress-test.service.ts] — Service with runSimulation('cron'|'operator'), weekly cron, event emission
- [Source: pm-arbitrage-engine/prisma/schema.prisma] — StressTestRun model with timestamp field (DateTime @db.Timestamptz)
- [Source: pm-arbitrage-dashboard/src/hooks/useDashboard.ts] — Hook patterns (useQuery, useMutation, toast, setQueryData, isAxiosError, select unwrapping)
- [Source: pm-arbitrage-dashboard/src/components/MetricDisplay.tsx] — Props: `{ label, value, className }` only — no subtitle
- [Source: pm-arbitrage-dashboard/src/components/DashboardPanel.tsx] — Props: `{ title, children, className }`
- [Source: pm-arbitrage-dashboard/src/pages/DashboardPage.tsx] — BalanceMetric local helper pattern, loading/error states
- [Source: pm-arbitrage-dashboard/src/pages/PerformancePage.tsx] — Error state pattern, DashboardPanel usage, table formatting
- [Source: pm-arbitrage-dashboard/src/components/Navigation.tsx] — navItems array (4 items: Dashboard, Positions, Matches, Performance)
- [Source: pm-arbitrage-dashboard/src/App.tsx] — Route definitions (6 routes currently)
- [Source: pm-arbitrage-dashboard/src/lib/utils.ts] — Only `cn()` utility present, no formatUsd
- [Source: pm-arbitrage-dashboard/package.json] — Dependency versions
- [Source: sprint-change-proposal-2026-03-13-stress-test-dashboard.md] — UX design spec, progressive disclosure hierarchy

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
- Engine tests: 5/5 stress-test controller spec passing after runTimestamp addition
- Dashboard: clean build (0 TS errors), lint clean (only pre-existing tabs.tsx warning)
- Generated API method names match story: `stressTestControllerGetLatestResult`, `stressTestControllerTriggerStressTest`

### Completion Notes List
- Task order adjusted: Task 5 (formatUsd/formatPercent) done before Tasks 2-3 since page depends on utils
- `formatPercent` was defined in utils but never imported — removed during code review (dead code).
- Generated `scenarioDetails.percentiles` typed as `object` (not `Record<string, string>`), cast in page component
- Generated `syntheticResults`/`volatilities` are optional arrays in generated types, handled with `?? []` fallback
- Drawdown bar width formula: `Math.min(prob * 400, 100)%` — 25% probability = full width (fixed during code review: original formula allowed >100% overflow)
- 5% alert threshold shown as dashed vertical line at 20% of bar track (5/25 = 20%)
- Pre-existing test failures (22 in candidate-discovery, 1 in data-ingestion e2e) unrelated to this story
- **Code Review (Lad MCP):** Primary reviewer (kimi-k2.5) found 1 HIGH (false positive — cache shapes match correctly with `--unwrap-response-data`), 2 MEDIUM (pre-existing, out of scope), 3 LOW. Fixed LOW #4: added numeric sort for percentile keys in P&L distribution table. Secondary reviewer (glm-5) timed out.

### File List
**Backend (pm-arbitrage-engine/):**
- `src/modules/risk-management/dto/stress-test.dto.ts` — added `runTimestamp` field
- `src/modules/risk-management/stress-test.controller.ts` — mapped `runTimestamp` in both endpoints
- `src/modules/risk-management/stress-test.controller.spec.ts` — added `runTimestamp` assertions

**Frontend (pm-arbitrage-dashboard/):**
- `src/api/generated/Api.ts` — regenerated with stress test types + runTimestamp
- `src/lib/utils.ts` — added `formatUsd()` utility (formatPercent removed during code review — dead code)
- `src/hooks/useDashboard.ts` — added `useStressTestLatest()` and `useRunStressTest()` hooks
- `src/pages/StressTestPage.tsx` — NEW: full stress test dashboard page (~280 lines)
- `src/App.tsx` — added `/stress-test` route
- `src/components/Navigation.tsx` — added "Stress Test" nav item (5th position)

### Senior Developer Review (AI) — 2026-03-13

**Reviewer:** Claude Opus 4.6 (adversarial code review)
**Verdict:** Approved after fixes

**Fixed (3 MEDIUM):**
1. **Drawdown bar width overflow** (`StressTestPage.tsx:198`) — `Math.min((dd.prob * 100) / 25, 100) * 100` → `Math.min(dd.prob * 400, 100)`. Original formula applied `* 100` outside the clamp, producing >100% CSS width for probabilities > 25%.
2. **Wrong type annotation** (`useDashboard.ts:212`) — `StressTestResponseDto` → `StressTestTriggerResponseDto` in `useRunStressTest` `onSuccess` handler. Mutation returns trigger response type, not GET response type.
3. **Dead `formatPercent` utility** (`utils.ts:17-22`) — Removed. Defined but never imported anywhere; probabilities formatted inline in StressTestPage.

**Noted (3 LOW, not fixed):**
1. Weak `runTimestamp` assertion in POST test — `toBeDefined()` vs ISO format validation
2. Pre-existing: raw `HttpException` in controller instead of `SystemError` hierarchy (from story 9-4)
3. Pre-existing: ESLint error in `tabs.tsx` (not introduced by this story)
