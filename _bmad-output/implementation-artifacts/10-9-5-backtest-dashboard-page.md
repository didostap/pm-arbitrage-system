# Story 10-9.5: Backtest Dashboard Page

Status: done

## Story

As an operator,
I want a dashboard page to configure, trigger, and review backtests with interactive sensitivity charts and run comparison,
so that I can run calibration analysis, evaluate parameter sensitivity, and detect overfitting without CLI access.

## Acceptance Criteria

1. **Given** the backtesting module is operational, **When** I navigate to the Backtest page, **Then** I see a backtest history list with: status badge, date range, key metrics (profit factor, Sharpe, net P&L, win rate), and created timestamp.

2. **Given** I am on the Backtest page, **When** I click "New Backtest", **Then** I can configure: date range (start/end pickers), parameter values (edge threshold, position size, max concurrent pairs, trading window hours), bankroll, gas estimate (platform fees are determined by the engine's fee schedule constants), and validation mode toggle (full-range vs walk-forward with split ratio slider).

3. **Given** I have configured a backtest, **When** I trigger the run, **Then** I see real-time progress indication (status transitions: CONFIGURING -> LOADING_DATA -> SIMULATING -> GENERATING_REPORT -> COMPLETE) and the run appears in the history list.

4. **Given** a backtest run is COMPLETE, **When** I view it, **Then** I see the calibration report with: summary metrics panel (total trades, profit factor, net P&L, max drawdown, Sharpe ratio, win rate), bootstrap 95% confidence intervals for profit factor and Sharpe, and a data quality summary.

5. **Given** a completed run with sensitivity results, **When** I view the sensitivity tab, **Then** interactive line charts display parameter sweeps (parameter value on x-axis, metric on y-axis) with degradation boundary lines highlighted where profit factor crosses 1.0, and recommended parameter values are called out.

6. **Given** a completed run with walk-forward results, **When** I view the walk-forward tab, **Then** in-sample vs out-of-sample metrics are displayed in separate panels with clear visual distinction, and overfitting warnings (>30% degradation) are prominently displayed with an alert banner.

7. **Given** a completed run has no sensitivity results yet, **When** I click "Run Sensitivity Analysis", **Then** a sweep is triggered (POST /runs/:id/sensitivity) and progress indication shows completed/total sweeps until results appear.

8. **Given** two completed backtest runs, **When** I select them for comparison, **Then** I see a side-by-side view with summary metrics, config differences highlighted, and delta values (improvement/degradation) for each metric.

9. **Given** any report view, **When** I look for known limitations, **Then** a collapsible section lists all 10 known modeling limitations.

10. **Given** the Backtest page, **Then** it follows existing dashboard patterns: DataTable with URL state (sorting, pagination, filtering by status), sidebar navigation entry, and consistent DashboardPanel layout.

## Tasks / Subtasks

- [x] **Task 1: Install shadcn/ui Chart component and Recharts v3** (AC: #5, #6)
  - [x] 1.1 Run `pnpm dlx shadcn@latest add chart` in `pm-arbitrage-dashboard/`
  - [x] 1.2 Add `--chart-1` through `--chart-5` CSS variables to globals.css if not present
  - [x] 1.3 Verify Recharts v3 imports work with React 19 (known compatibility — check shadcn docs note)

- [x] **Task 2: Regenerate API client with backtest endpoints** (AC: #1-#9)
  - [x] 2.1 Run `pnpm generate-api` (or equivalent swagger-typescript-api command) against the engine's `/api/docs-json`
  - [x] 2.2 Verify generated client includes: `POST/GET /backtesting/runs`, `GET/DELETE /backtesting/runs/:id`, `GET /backtesting/runs/:id/report`, `POST/GET /backtesting/runs/:id/sensitivity`, `GET /backtesting/runs/:id/walk-forward`
  - [x] 2.3 If generation script doesn't exist, create one that points to the engine Swagger endpoint

- [x] **Task 3: Create backtest TanStack Query hooks** (AC: #1-#9)
  - [x] 3.1 Create `src/hooks/useBacktest.ts` following the pattern in `useDashboard.ts`
  - [x] 3.2 Implement hooks:
    - `useBacktestRuns(status?, sortBy?, order?, page?, limit?)` — list runs, `staleTime: 10s`, `placeholderData: keepPreviousData`
    - `useBacktestRun(id)` — single run with positions, `staleTime: 5s`
    - `useBacktestReport(id)` — calibration report, `staleTime: 60s` (immutable once generated)
    - `useBacktestSensitivity(id)` — sensitivity results, `staleTime: 10s` (poll while pending)
    - `useBacktestWalkForward(id)` — walk-forward results, `staleTime: 60s`
    - `useCreateBacktest()` — mutation, invalidates runs list on success
    - `useCancelBacktest()` — mutation, invalidates run + runs list
    - `useTriggerSensitivity(id)` — mutation, invalidates sensitivity query on success
  - [x] 3.3 Query keys: `['backtesting', 'runs']`, `['backtesting', 'run', id]`, `['backtesting', 'report', id]`, `['backtesting', 'sensitivity', id]`, `['backtesting', 'walkforward', id]`
  - [x] 3.4 Error handling: `isAxiosError` checks with sonner toasts, retry: 2 (skip 404s)

- [x] **Task 4: Add WebSocket event handlers for backtest events** (AC: #3, #7)
  - [x] 4.1 Add backtest WS event types to `src/types/ws-events.ts` (names match the WebSocket Push Event column in Dev Notes table): `backtesting.run.completed`, `backtesting.run.failed`, `backtesting.engine.state-changed`, `backtesting.sensitivity.progress`, `backtesting.sensitivity.completed`
  - [x] 4.2 In `WebSocketProvider.tsx`, add event handlers (follow existing `handlePositionUpdate` pattern):
    - `backtesting.run.completed` → invalidate `['backtesting', 'runs']` + `['backtesting', 'run', runId]` + `['backtesting', 'report', runId]` + success toast
    - `backtesting.run.failed` → invalidate `['backtesting', 'runs']` + `['backtesting', 'run', runId]` + error toast with message
    - `backtesting.engine.state-changed` → invalidate `['backtesting', 'run', runId]`
    - `backtesting.sensitivity.completed` → invalidate `['backtesting', 'sensitivity', runId]` + toast
    - `backtesting.sensitivity.progress` → update progress state (optional: React Query `setQueryData` or local state)

- [x] **Task 5: Backtest history list page (BacktestPage)** (AC: #1, #10)
  - [x] 5.1 Create `src/pages/BacktestPage.tsx`
  - [x] 5.2 Use `DataTable` with `urlStateKey="backtest"` for URL state sync (status filter, pagination, sorting)
  - [x] 5.3 Columns: Status (badge), Date Range, Profit Factor, Sharpe, Net P&L, Win Rate, Created At
  - [x] 5.4 Status filter tabs: All / Running / Complete / Failed (use `useUrlTableState` pattern from PositionsPage)
  - [x] 5.5 Row click navigates to `/backtesting/:id`
  - [x] 5.6 "New Backtest" button opens config dialog

- [x] **Task 6: Backtest configuration dialog** (AC: #2, #3)
  - [x] 6.1 Create `src/components/NewBacktestDialog.tsx`
  - [x] 6.2 Form fields with validation (mirror `BacktestConfigDto` constraints):
    - Date range: start/end date pickers (required)
    - Edge threshold: number input, 0.1%-100%, default 0.8% (display as %, submit as decimal 0.008)
    - Position size: number input, 1%-100%, default 3%
    - Max concurrent pairs: number input, 1-100, default 10
    - Bankroll: string input, default "10000"
    - Trading window: start hour (0-23, default 14) / end hour (0-23, default 23)
    - Gas estimate: string input, default "0.50"
    - Exit edge evaporation: number input, default 0.2%
    - Exit time limit: number input, default 72 hours
    - Exit profit capture: number input, default 80%
    - Walk-forward toggle: Switch, default off
    - Walk-forward train %: Slider (10%-90%, default 70%), visible only when walk-forward enabled
    - Timeout: number input, 60-3600s, default 300
  - [x] 6.3 Submit calls `useCreateBacktest()`, toast on success, navigate to run detail
  - [x] 6.4 Follow dialog patterns from `ClosePositionDialog.tsx` / `MatchApprovalDialog.tsx`

- [x] **Task 7: Backtest run detail page (BacktestDetailPage)** (AC: #4, #9)
  - [x] 7.1 Create `src/pages/BacktestDetailPage.tsx`
  - [x] 7.2 Header: Run ID, status badge, date range, config summary, cancel button (if running)
  - [x] 7.3 Tab navigation: Summary | Sensitivity | Walk-Forward | Positions
  - [x] 7.4 Summary tab: `SummaryMetricsPanel` + `ConfidenceIntervalsPanel` + `DataQualityPanel` + `KnownLimitationsCollapsible`
  - [x] 7.5 Use DashboardPanel wrappers for each section (consistent with existing pages)
  - [x] 7.6 Known limitations: Collapsible component with 10 items, collapsed by default

- [x] **Task 8: Summary metrics panel** (AC: #4)
  - [x] 8.1 Create `src/components/backtest/SummaryMetricsPanel.tsx`
  - [x] 8.2 Grid layout (2x3 or responsive): Total Trades, Profit Factor (with 95% CI range), Net P&L (colored), Max Drawdown, Sharpe Ratio (with 95% CI range), Win Rate
  - [x] 8.3 Use `MetricDisplay` component pattern from DashboardPage
  - [x] 8.4 CI display: "1.45 [1.12 – 1.78]" format below main value

- [x] **Task 9: Sensitivity analysis charts** (AC: #5, #7)
  - [x] 9.1 Create `src/components/backtest/SensitivityCharts.tsx`
  - [x] 9.2 For each parameter sweep, render a `LineChart` (Recharts via shadcn Chart):
    - X-axis: parameter values (edge threshold %, position size %, etc.)
    - Y-axis: metric value (profit factor primary, with Sharpe and max drawdown as toggleable series)
    - Degradation boundary: `ReferenceLine` at profitFactor = 1.0 with label "Breakeven"
    - Breakeven crossing point: annotated dot with interpolated parameter value
    - Recommended value: vertical `ReferenceLine` with label
  - [x] 9.3 Chart config using `ChartContainer` + `ChartConfig` + `ChartTooltip` from shadcn
  - [x] 9.4 Metric toggle: buttons/tabs to switch y-axis between Profit Factor / Sharpe / Max Drawdown / Net P&L
  - [x] 9.5 "Run Sensitivity Analysis" button when no results exist, with `useTriggerSensitivity` mutation
  - [x] 9.6 Progress indicator when sweep in progress: "Completed X / Y sweeps" bar
  - [x] 9.7 Partial results display: when `partial: true`, show completed sweeps with a warning banner: "Sensitivity analysis timed out — showing {completedSweeps}/{totalPlannedSweeps} sweeps. Re-run with a higher timeout to complete."
  - [x] 9.8 Recommended parameters section below charts: table of best values by profit factor and Sharpe
  - [x] 9.9 Degradation boundary annotations: `breakEvenValue` and `direction` come from the API (`degradationBoundaries` array) — no frontend interpolation needed. Render as a vertical `ReferenceLine` with the boundary description as label.

- [x] **Task 10: Walk-forward analysis panel** (AC: #6)
  - [x] 10.1 Create `src/components/backtest/WalkForwardPanel.tsx`
  - [x] 10.2 Two-column layout: "In-Sample (Train)" panel left, "Out-of-Sample (Test)" panel right
  - [x] 10.3 Each panel shows: total positions, profit factor, Sharpe, net P&L, max drawdown, capital utilization
  - [x] 10.4 Delta row between panels: % degradation per metric, color-coded (green < 15%, yellow 15-30%, red > 30%)
  - [x] 10.5 Overfit alert: if any `overfitFlags` exist, show Alert component (destructive variant) at top: "Potential overfitting detected: {metrics} show >30% degradation between in-sample and out-of-sample"
  - [x] 10.6 Date range labels: show train/test date ranges with train% / test% split

- [x] **Task 11: Run comparison view** (AC: #8)
  - [x] 11.1 Create `src/components/backtest/RunComparisonView.tsx`
  - [x] 11.2 Selection UI: checkboxes on BacktestPage DataTable rows, "Compare Selected" button (enabled when exactly 2 selected)
  - [x] 11.3 Side-by-side layout: Run A | Delta | Run B
  - [x] 11.4 Config diff: highlight changed parameters between the two runs
  - [x] 11.5 Metrics comparison: all summary metrics with delta values (green for improvement, red for degradation)
  - [x] 11.6 URL state: `?compare=id1,id2` for shareability

- [x] **Task 12: Routing and navigation integration** (AC: #10)
  - [x] 12.1 Add routes in `App.tsx`:
    - `/backtesting` → `BacktestPage` (history list)
    - `/backtesting/:id` → `BacktestDetailPage`
    - `/backtesting/compare` → `RunComparisonView` (reads `?compare=id1,id2`)
  - [x] 12.2 Add "Backtesting" entry to `AppSidebar.tsx` (under existing nav items, use `FlaskConical` or `TestTubeDiagonal` Lucide icon)
  - [x] 12.3 Add backtest layout if needed for consistent tab structure

## Dev Notes

### Dual-Repository Context

This story spans TWO separate git repos:
- **Frontend**: `pm-arbitrage-dashboard/` — React SPA (separate git repo)
- **Backend**: `pm-arbitrage-engine/` — NestJS API (separate git repo)

All implementation work for this story is in `pm-arbitrage-dashboard/`. The backend endpoints already exist from Stories 10-9-3 and 10-9-4. The only backend change needed is wiring backtest events to the WebSocket gateway (see Task 4 notes below).

### Backend WebSocket Gateway Gap (REQUIRES ENGINE REPO COMMIT)

The existing `DashboardGateway` (`pm-arbitrage-engine/src/dashboard/dashboard.gateway.ts`) subscribes to EventEmitter2 events and pushes them to WebSocket clients. **Backtest events are NOT yet wired to the gateway.** The dev agent needs to add `@OnEvent` handlers in the gateway following the existing pattern (see `handlePositionUpdate`, `handleHealthChange` methods for reference). Add handlers for:

| EventEmitter2 Event (backend `@OnEvent`) | WebSocket Push Event (frontend subscribes to) |
|---|---|
| `backtesting.run.completed` | `backtesting.run.completed` |
| `backtesting.run.failed` | `backtesting.run.failed` |
| `backtesting.engine.state-changed` | `backtesting.engine.state-changed` |
| `backtesting.sensitivity.completed` | `backtesting.sensitivity.completed` |
| `backtesting.sensitivity.progress` | `backtesting.sensitivity.progress` |

**Use the same event names on both sides** (consistent with existing gateway pattern where `position.update` EventEmitter2 event pushes as `position.update` WebSocket event). This is ~20 lines in the engine repo.

The frontend in Task 4 subscribes to these exact WebSocket event names. Keep them in sync.

### Chart Library: shadcn/ui Chart (Recharts v3)

shadcn/ui has an official `Chart` component built on Recharts v3. Install via `pnpm dlx shadcn@latest add chart`. This provides:
- `ChartContainer` — responsive wrapper with theme support
- `ChartTooltip` / `ChartTooltipContent` — themed tooltips
- `ChartLegend` / `ChartLegendContent` — themed legends
- Uses Recharts components directly (no wrapping abstraction): `LineChart`, `Line`, `XAxis`, `YAxis`, `CartesianGrid`, `ReferenceLine`, `ResponsiveContainer`
- Theming via CSS vars: `--chart-1` through `--chart-5`, referenced as `var(--color-KEY)` in components
- **Recharts v3 note**: Use `var(--chart-1)` directly (not `hsl(var(--chart-1))`). Keep `min-h-*` on `ChartContainer`.

### API Client Generation

The dashboard uses `swagger-typescript-api` to generate an Axios-based client from the engine's OpenAPI spec. Check `pm-arbitrage-dashboard/package.json` for the generation script. If no script exists, run:
```bash
npx swagger-typescript-api -p http://localhost:3000/api/docs-json -o src/api/generated -n Api.ts --unwrap-response-data
```
The generated client uses `baseURL` (axios convention). Methods follow controller naming: `backtestControllerCreateRun()`, `backtestControllerGetRuns()`, etc.

### Existing Patterns to Follow

| Pattern | Source File | What to Reuse |
|---------|-------------|---------------|
| Page layout | `StressTestPage.tsx` | Closest analog — collapsible sections, metric grids, tabbed content |
| Data table + URL state | `PositionsPage.tsx` + `useUrlTableState.ts` | DataTable with urlStateKey, filter tabs, pagination |
| Query hooks | `useDashboard.ts` | TanStack Query patterns, error handling, toast integration |
| Dialogs | `ClosePositionDialog.tsx` | Dialog with form, mutation, validation |
| Status badges | `StatusBadge.tsx` | Colored status indicators |
| Metric display | `MetricDisplay.tsx` | Single metric card with label/value |
| Dashboard panels | `DashboardPanel.tsx` | Card wrapper with title + tooltip |
| WebSocket events | `WebSocketProvider.tsx` + `ws-events.ts` | Event type → query invalidation pattern |
| Settings form | `SettingField.tsx` | Field-level validation pattern |

### Backtest Status Badges

Map `BacktestRunStatus` to badge variants:
| Status | Color | Variant |
|--------|-------|---------|
| CONFIGURING | blue | `info` |
| LOADING_DATA | blue | `info` |
| SIMULATING | yellow | `warning` |
| GENERATING_REPORT | yellow | `warning` |
| COMPLETE | green | `success` |
| FAILED | red | `destructive` |
| CANCELLED | gray | `secondary` |

### Decimal Display Formatting

All monetary values from the API are serialized as strings (Decimal precision). **For display-only rendering (charts, tables, badges), parsing to `number` via `parseFloat()` is acceptable.** No `decimal.js` needed in the frontend — all financial math is server-side. Format for display:
- P&L: `$1,234.56` (2 decimal places, comma-separated, colored green/red)
- Percentages (profit factor, Sharpe, win rate): 2-4 decimal places
- CI ranges: `[1.12 – 1.78]` format
- Edge threshold: display as `0.8%` (value from API is `0.008`)
- Walk-forward degradation values: come pre-computed from the API (0.0-1.0 scale), display as percentage

### Sensitivity Chart Data Shape

The sensitivity API returns sweep data in this shape:
```typescript
{
  sweeps: [{
    parameterName: "edgeThresholdPct",
    baseValue: 0.008,
    values: [0.005, 0.006, ...0.05],      // x-axis data points
    profitFactor: ["1.45", "1.42", ...],   // string decimals
    maxDrawdown: ["0.08", "0.09", ...],
    sharpeRatio: ["0.92", null, ...],      // null when incalculable
    totalPnl: ["1234.56", "1100.00", ...]
  }],
  degradationBoundaries: [{
    parameterName: "edgeThresholdPct",
    breakEvenValue: 0.028,
    direction: "below",
    description: "Below 2.8% edge threshold, system is unprofitable"
  }],
  recommendedParameters: {
    byProfitFactor: [{ parameterName, value, profitFactor }],
    bySharpe: [{ parameterName, value, sharpeRatio }]
  },
  partial: false,
  completedSweeps: 66,
  totalPlannedSweeps: 66
}
```

Transform for Recharts: each sweep → array of `{ value: number, profitFactor: number, sharpeRatio: number | null, maxDrawdown: number, totalPnl: number }`. Parse string decimals to numbers for chart rendering (display-only, no financial math needed).

### Walk-Forward Data Shape

```typescript
{
  trainPct: 0.7,
  testPct: 0.3,
  trainDateRange: { start: "2025-01-01T...", end: "2025-09-30T..." },
  testDateRange: { start: "2025-10-01T...", end: "2025-12-31T..." },
  trainMetrics: { totalPositions, winCount, lossCount, totalPnl, maxDrawdown, sharpeRatio, profitFactor, avgHoldingHours, capitalUtilization },
  testMetrics: { /* same shape */ },
  degradation: { profitFactor: 0.15, sharpeRatio: 0.22, totalPnl: 0.18 },
  overfitFlags: []  // or ["profitFactor", "sharpeRatio"] when >30%
}
```

### Run Comparison URL State

When comparing, store in URL: `/backtesting/compare?compare=uuid1,uuid2` (matches Task 11.6). Fetch both runs and their reports in parallel using `useQueries` from TanStack Query. The first run in the pair is the baseline (Run A); delta = Run B - Run A (positive = improvement for P&L/profit factor/Sharpe, negative = degradation).

### Known Limitations

Known limitations come from the API response (`CalibrationReport.knownLimitations: string[]`). Display them from the API data, do NOT hardcode in the frontend. The backend constant `KNOWN_LIMITATIONS` in `src/modules/backtesting/types/calibration-report.types.ts` currently contains these 10 items:

```
1. No single-leg risk modeling — assumes atomic dual-leg fills
2. No market impact — ignores price movement from our orders
3. No queue position modeling — taker-only assumptions
4. Depth interpolation — hourly PMXT snapshots use nearest-neighbor between hours
5. No correlation modeling — independent position evaluation
6. No funding/holding costs — ignores capital opportunity cost
7. Execution latency not modeled — assumes instant fills
8. Historical data biases — survivorship bias, lookback bias
9. Cross-platform clock skew — Kalshi vs Polymarket time (minutes)
10. Non-binary resolution excluded — void/refunded/fractional resolution not modeled
```

### Project Structure Notes

New files in `pm-arbitrage-dashboard/src/`:
```
pages/
  BacktestPage.tsx              # History list with DataTable
  BacktestDetailPage.tsx        # Tabbed detail view
components/
  backtest/
    SummaryMetricsPanel.tsx     # Metric grid with CIs
    SensitivityCharts.tsx       # Recharts line charts per sweep
    WalkForwardPanel.tsx        # Train vs test comparison
    RunComparisonView.tsx       # Side-by-side two-run diff
    NewBacktestDialog.tsx       # Config form dialog
    BacktestStatusBadge.tsx     # Status → color mapping
    KnownLimitationsSection.tsx # Collapsible limitations list
hooks/
  useBacktest.ts                # All backtest TanStack Query hooks
```

Backend changes in `pm-arbitrage-engine/src/`:
```
dashboard/
  dashboard.gateway.ts          # Add @OnEvent handlers for backtest events (~20 lines)
```

### Testing Notes

- Frontend tests use Vitest + Testing Library (see existing specs in `pm-arbitrage-dashboard/`)
- Priority test targets: `useBacktest.ts` hooks (mock API responses), `SensitivityCharts.tsx` (data transformation), `BacktestPage.tsx` (DataTable rendering)
- Follow existing test patterns in `SettingsPage.spec.tsx`, `SettingField.spec.tsx`

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 10-9, Story 10-9-5]
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md — Section 8.6 API endpoints, Section 4.3 BacktestConfigDto, Section 4.8 CalibrationReport]
- [Source: _bmad-output/implementation-artifacts/10-9-4-calibration-report-sensitivity-analysis.md — Calibration report types, sensitivity sweep format, walk-forward results]
- [Source: _bmad-output/planning-artifacts/architecture.md — Dashboard module, REST patterns, WebSocket gateway, response format]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Panel-based architecture, health indicators, scannable design]
- [Source: pm-arbitrage-dashboard/src/hooks/useDashboard.ts — TanStack Query hook patterns]
- [Source: pm-arbitrage-dashboard/src/hooks/useUrlTableState.ts — URL state management]
- [Source: pm-arbitrage-dashboard/src/components/DataTable.tsx — DataTable with URL sync]
- [Source: pm-arbitrage-dashboard/src/pages/StressTestPage.tsx — Closest page analog]
- [Source: pm-arbitrage-dashboard/src/providers/WebSocketProvider.tsx — Event → query invalidation]
- [Source: ui.shadcn.com/docs/components/chart — shadcn Chart component (Recharts v3)]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
None — clean implementation.

### Completion Notes List
- Task 1: Installed shadcn/ui Chart + Recharts v3.8.0. CSS vars `--chart-1` through `--chart-5` already present.
- Task 2: Regenerated API client via `pnpm generate-api`. Added `axiosInstance` export for sub-route endpoints missing from Swagger spec.
- Task 3: Created `useBacktest.ts` with 8 hooks (5 query, 3 mutation). Uses `axiosInstance` for report/sensitivity/walk-forward sub-routes not in generated client. 18 tests pass.
- Task 4: Added 5 backtest `@OnEvent` handlers to `DashboardGateway`. Added 5 WS event types to both repos. 7 WS provider tests + 3 engine gateway tests pass.
- Task 5: Created `BacktestPage.tsx` with DataTable, `BacktestStatusBadge`, filter tabs, comparison checkboxes. 12 tests pass.
- Task 6: Created `NewBacktestDialog.tsx` with all config fields, validation, walk-forward toggle. 13 tests pass.
- Task 7: Created `BacktestDetailPage.tsx` with tabs (Summary/Sensitivity/Walk-Forward/Positions), cancel button, loading states. 8 tests pass.
- Task 8: Created `SummaryMetricsPanel.tsx` with 6 metrics, bootstrap CIs, data quality panel. 8 tests pass.
- Task 9: Created `SensitivityCharts.tsx` with Recharts LineChart per sweep, metric toggle, reference lines, partial warning, trigger button. 10 tests pass.
- Task 10: Created `WalkForwardPanel.tsx` with train/test comparison, degradation colors, overfit alert. 7 tests pass.
- Task 11: Created `RunComparisonView.tsx` with side-by-side layout, config diff, metric deltas, URL state. 8 tests pass.
- Task 12: Added routes in `App.tsx`, sidebar entry with `FlaskConical` icon, `KnownLimitationsSection` component. 4 tests pass.

### File List

**pm-arbitrage-dashboard/ (NEW files):**
- `src/hooks/useBacktest.ts` — TanStack Query hooks for all backtest endpoints
- `src/hooks/useBacktest.spec.ts` — 18 tests
- `src/pages/BacktestPage.tsx` — History list with DataTable
- `src/pages/BacktestPage.spec.tsx` — 12 tests
- `src/pages/BacktestDetailPage.tsx` — Tabbed detail view
- `src/pages/BacktestDetailPage.spec.tsx` — 8 tests
- `src/components/backtest/BacktestStatusBadge.tsx` — Status badge with colors
- `src/components/backtest/NewBacktestDialog.tsx` — Config form dialog
- `src/components/backtest/NewBacktestDialog.spec.tsx` — 13 tests
- `src/components/backtest/SummaryMetricsPanel.tsx` — Metric grid with CIs
- `src/components/backtest/SummaryMetricsPanel.spec.tsx` — 8 tests
- `src/components/backtest/SensitivityCharts.tsx` — Recharts line charts
- `src/components/backtest/SensitivityCharts.spec.tsx` — 10 tests
- `src/components/backtest/WalkForwardPanel.tsx` — Train vs test comparison
- `src/components/backtest/WalkForwardPanel.spec.tsx` — 7 tests
- `src/components/backtest/RunComparisonView.tsx` — Side-by-side run diff
- `src/components/backtest/RunComparisonView.spec.tsx` — 8 tests
- `src/components/backtest/KnownLimitationsSection.tsx` — Collapsible limitations
- `src/components/backtest/KnownLimitationsSection.spec.tsx` — 4 tests
- `src/providers/WebSocketProvider.spec.tsx` — 7 WS event handler tests

**pm-arbitrage-dashboard/ (MODIFIED files):**
- `src/api/client.ts` — Added `axiosInstance` export
- `src/api/generated/Api.ts` — Regenerated with backtest endpoints
- `src/types/ws-events.ts` — Added 5 backtest WS event types
- `src/providers/WebSocketProvider.tsx` — Added 5 backtest event handlers
- `src/App.tsx` — Added 3 backtesting routes
- `src/components/AppSidebar.tsx` — Added "Backtesting" nav entry
- `src/components/ui/chart.tsx` — NEW (shadcn/ui Chart component)
- `src/components/ui/card.tsx` — Updated by shadcn installer

**pm-arbitrage-engine/ (MODIFIED files):**
- `src/dashboard/dashboard.gateway.ts` — Added 5 backtest `@OnEvent` handlers
- `src/dashboard/dashboard.gateway.spec.ts` — Added 3 handler tests
- `src/dashboard/dto/ws-events.dto.ts` — Added 5 backtest WS event names

### Change Log
- 2026-03-28: Story 10-9-5 implemented. 12 tasks complete. 130 dashboard tests pass (95 new). 16 engine gateway tests pass (3 new). All ACs covered.
- 2026-03-28: Code review completed. 3-layer adversarial (Blind Hunter + Edge Case Hunter + Acceptance Auditor), 40 raw findings triaged to 1 intent-gap + 1 bad-spec + 15 patch + 5 defer + 13 reject. All 17 actionable items fixed: IG-1 BacktestPage URL state sync via useUrlTableState, BS-1 AC#2 fee fields amended; P-1 status filter backend+frontend, P-2 running filter all 4 states, P-3 transformSweepData null-safe for "0" strings, P-4 dialog form reset via component remount, P-5 WalkForwardPanel null guard, P-6 RunComparisonView error handling, P-7 numeric field validation, P-8 date ordering validation, P-9 WS toast fallback, P-10 Invalid Date guard, P-11 connectNulls removed, P-12 selection reset on filter change, P-13 bankroll/gas numeric inputs, P-14 NaN delta guard, P-15 progress bar test added. 131 dashboard tests pass. 3426 engine tests pass.
