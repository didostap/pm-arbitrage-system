---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-27'
workflowType: 'testarch-atdd'
inputDocuments:
  - '_bmad-output/implementation-artifacts/10-9-5-backtest-dashboard-page.md'
  - '_bmad-output/implementation-artifacts/10-9-0-design-doc.md'
  - '_bmad-output/implementation-artifacts/10-9-4-calibration-report-sensitivity-analysis.md'
  - '_bmad/tea/testarch/knowledge/data-factories.md'
  - '_bmad/tea/testarch/knowledge/component-tdd.md'
  - '_bmad/tea/testarch/knowledge/test-quality.md'
  - '_bmad/tea/testarch/knowledge/selector-resilience.md'
  - '_bmad/tea/testarch/knowledge/timing-debugging.md'
  - '_bmad/tea/testarch/knowledge/test-healing-patterns.md'
---

# ATDD Checklist — Story 10-9.5: Backtest Dashboard Page

**Date:** 2026-03-27
**Author:** Arbi
**Primary Test Level:** Component (Vitest + Testing Library) + Integration (engine WS gateway) + E2E (Playwright)
**Repos:** `pm-arbitrage-dashboard/` (primary), `pm-arbitrage-engine/` (minor), `e2e/` (E2E)

---

## Story Summary

**As an** operator
**I want** a dashboard page to configure, trigger, and review backtests with interactive sensitivity charts and run comparison
**So that** I can run calibration analysis, evaluate parameter sensitivity, and detect overfitting without CLI access

---

## Acceptance Criteria

1. History list: DataTable with status badge, date range, key metrics, created timestamp
2. New Backtest config dialog: date range, parameters, bankroll, fee model, walk-forward toggle
3. Run progress: real-time status transitions (CONFIGURING → LOADING_DATA → SIMULATING → GENERATING_REPORT → COMPLETE)
4. Calibration report: summary metrics, bootstrap 95% CI, data quality summary
5. Sensitivity charts: interactive line charts with degradation boundaries and recommended values
6. Walk-forward panel: in-sample vs out-of-sample with overfit warnings (>30% degradation)
7. Trigger sensitivity: POST /runs/:id/sensitivity with progress indication
8. Run comparison: side-by-side with config diff and metric deltas
9. Known limitations: collapsible section listing all 10 items from API
10. Dashboard patterns: DataTable URL state, sidebar nav, DashboardPanel layout

---

## Test Strategy

| Level | Scope | Framework | Location |
|-------|-------|-----------|----------|
| Component | UI rendering, form validation, data transformation, user interactions | Vitest + @testing-library/react | `pm-arbitrage-dashboard/src/**/*.spec.tsx` |
| Hook | TanStack Query hooks, mutation callbacks, cache invalidation | Vitest | `pm-arbitrage-dashboard/src/hooks/useBacktest.spec.ts` |
| Integration | WebSocket gateway event handlers | Vitest + @nestjs/testing | `pm-arbitrage-engine/src/dashboard/dashboard.gateway.spec.ts` |
| E2E | Critical user journeys across pages | Playwright | `e2e/tests/ui/backtest*.spec.ts` |

---

## Failing Tests Created (RED Phase)

### Task 1: Install shadcn/ui Chart + Recharts (0 tests)

No tests — infrastructure task. Verified transitively by Task 9 chart rendering tests.

---

### Task 2: Regenerate API Client (0 tests)

No tests — code generation task. Verified transitively by hook and component tests importing generated types.

---

### Task 3: Backtest TanStack Query Hooks (18 tests)

**File:** `pm-arbitrage-dashboard/src/hooks/useBacktest.spec.ts` (NEW, ~350 lines)

**Query hooks — 8 tests:**

- [ ] **Test:** [P0] useBacktestRuns should fetch paginated runs with status/sort/order/page/limit params and return data
  - **Status:** RED — useBacktestRuns hook does not exist
  - **Verifies:** AC #1 — history list data fetching
- [ ] **Test:** [P0] useBacktestRun should fetch single run by id with staleTime 5s
  - **Status:** RED — useBacktestRun hook does not exist
  - **Verifies:** AC #4 — single run fetch
- [ ] **Test:** [P1] useBacktestReport should fetch calibration report with staleTime 60s (immutable once generated)
  - **Status:** RED — useBacktestReport hook does not exist
  - **Verifies:** AC #4 — report data fetching
- [ ] **Test:** [P1] useBacktestSensitivity should fetch sensitivity results with staleTime 10s
  - **Status:** RED — useBacktestSensitivity hook does not exist
  - **Verifies:** AC #5 — sensitivity data fetching
- [ ] **Test:** [P1] useBacktestWalkForward should fetch walk-forward results with staleTime 60s
  - **Status:** RED — useBacktestWalkForward hook does not exist
  - **Verifies:** AC #6 — walk-forward data fetching
- [ ] **Test:** [P1] useBacktestRuns should use query key ['backtesting', 'runs'] with filter params
  - **Status:** RED — hook does not exist
  - **Verifies:** AC #1 — query key convention for cache invalidation
- [ ] **Test:** [P1] useBacktestReport should use query key ['backtesting', 'report', id]
  - **Status:** RED — hook does not exist
  - **Verifies:** AC #4 — query key convention
- [ ] **Test:** [P1] useBacktestSensitivity should use query key ['backtesting', 'sensitivity', id]
  - **Status:** RED — hook does not exist
  - **Verifies:** AC #5, #7 — query key for WS invalidation

**Mutation hooks — 6 tests:**

- [ ] **Test:** [P0] useCreateBacktest should POST config and invalidate runs list on success
  - **Status:** RED — useCreateBacktest hook does not exist
  - **Verifies:** AC #2, #3 — create run mutation
- [ ] **Test:** [P1] useCreateBacktest should show error toast on failure (isAxiosError check)
  - **Status:** RED — useCreateBacktest hook does not exist
  - **Verifies:** AC #2 — error handling
- [ ] **Test:** [P1] useCancelBacktest should invalidate run and runs list on success
  - **Status:** RED — useCancelBacktest hook does not exist
  - **Verifies:** AC #3 — cancel mutation cache invalidation
- [ ] **Test:** [P0] useTriggerSensitivity should POST to /runs/:id/sensitivity and invalidate sensitivity query
  - **Status:** RED — useTriggerSensitivity hook does not exist
  - **Verifies:** AC #7 — trigger sensitivity mutation
- [ ] **Test:** [P1] useTriggerSensitivity should show success toast on completion
  - **Status:** RED — useTriggerSensitivity hook does not exist
  - **Verifies:** AC #7 — user feedback
- [ ] **Test:** [P1] useCreateBacktest should show success toast and return run data for navigation
  - **Status:** RED — useCreateBacktest hook does not exist
  - **Verifies:** AC #2 — post-create navigation

**Error handling — 4 tests:**

- [ ] **Test:** [P1] query hooks should retry 2 times on failure (except 404)
  - **Status:** RED — hooks do not exist
  - **Verifies:** Cross-cutting — retry policy
- [ ] **Test:** [P1] query hooks should not retry on 404 responses
  - **Status:** RED — hooks do not exist
  - **Verifies:** Cross-cutting — skip retry for not-found
- [ ] **Test:** [P2] useBacktestRuns should use placeholderData: keepPreviousData for smooth pagination
  - **Status:** RED — hook does not exist
  - **Verifies:** AC #1 — UX during page transitions
- [ ] **Test:** [P2] useBacktestRuns should accept optional status filter parameter
  - **Status:** RED — hook does not exist
  - **Verifies:** AC #10 — filter tabs support

---

### Task 4: WebSocket Event Handlers (10 tests)

**File:** `pm-arbitrage-dashboard/src/providers/WebSocketProvider.spec.tsx` (NEW or EXTEND, ~150 lines)

- [ ] **Test:** [P0] should invalidate ['backtesting', 'runs'] + ['backtesting', 'run', runId] + ['backtesting', 'report', runId] on backtesting.run.completed event
  - **Status:** RED — backtest WS event handlers not wired
  - **Verifies:** AC #3 — run completion cache refresh
- [ ] **Test:** [P1] should show success toast on backtesting.run.completed event
  - **Status:** RED — handler does not exist
  - **Verifies:** AC #3 — user notification
- [ ] **Test:** [P0] should invalidate ['backtesting', 'runs'] + ['backtesting', 'run', runId] on backtesting.run.failed event
  - **Status:** RED — handler does not exist
  - **Verifies:** AC #3 — failure cache refresh
- [ ] **Test:** [P1] should show error toast with message on backtesting.run.failed event
  - **Status:** RED — handler does not exist
  - **Verifies:** AC #3 — failure notification
- [ ] **Test:** [P1] should invalidate ['backtesting', 'run', runId] on backtesting.engine.state-changed event
  - **Status:** RED — handler does not exist
  - **Verifies:** AC #3 — status transition refresh
- [ ] **Test:** [P0] should invalidate ['backtesting', 'sensitivity', runId] on backtesting.sensitivity.completed event
  - **Status:** RED — handler does not exist
  - **Verifies:** AC #7 — sensitivity results appear after completion
- [ ] **Test:** [P1] should show toast on backtesting.sensitivity.completed event
  - **Status:** RED — handler does not exist
  - **Verifies:** AC #7 — user notification

**File:** `pm-arbitrage-engine/src/dashboard/dashboard.gateway.spec.ts` (EXTEND existing, ~60 lines)

- [ ] **Test:** [P0] should have @OnEvent('backtesting.run.completed') handler that emits to WS clients
  - **Status:** RED — handler not wired in gateway
  - **Verifies:** AC #3 — backend event → WS push
- [ ] **Test:** [P0] should have @OnEvent('backtesting.sensitivity.completed') handler that emits to WS clients
  - **Status:** RED — handler not wired in gateway
  - **Verifies:** AC #7 — sensitivity completion push
- [ ] **Test:** [P1] should have @OnEvent handlers for backtesting.run.failed, backtesting.engine.state-changed, backtesting.sensitivity.progress
  - **Status:** RED — handlers not wired
  - **Verifies:** AC #3, #7 — all 5 backtest event handlers present

---

### Task 5: Backtest History List Page (12 tests)

**File:** `pm-arbitrage-dashboard/src/pages/BacktestPage.spec.tsx` (NEW, ~250 lines)

- [ ] **Test:** [P0] should render DataTable with columns: Status, Date Range, Profit Factor, Sharpe, Net P&L, Win Rate, Created At
  - **Status:** RED — BacktestPage does not exist
  - **Verifies:** AC #1 — history list columns
- [ ] **Test:** [P0] should display status badges with correct colors (COMPLETE=green, FAILED=red, SIMULATING=yellow, CONFIGURING=blue)
  - **Status:** RED — BacktestPage does not exist
  - **Verifies:** AC #1 — status badge rendering
- [ ] **Test:** [P1] should render filter tabs: All / Running / Complete / Failed
  - **Status:** RED — BacktestPage does not exist
  - **Verifies:** AC #10 — status filter tabs
- [ ] **Test:** [P1] should pass urlStateKey="backtest" to DataTable for URL state sync
  - **Status:** RED — BacktestPage does not exist
  - **Verifies:** AC #10 — URL state management
- [ ] **Test:** [P1] should call onRowClick handler when a row is clicked (for navigation)
  - **Status:** RED — BacktestPage does not exist
  - **Verifies:** AC #1 — row click navigates to detail
- [ ] **Test:** [P0] should render "New Backtest" button
  - **Status:** RED — BacktestPage does not exist
  - **Verifies:** AC #2 — config dialog trigger
- [ ] **Test:** [P1] should show loading skeleton while data is loading
  - **Status:** RED — BacktestPage does not exist
  - **Verifies:** AC #10 — loading state
- [ ] **Test:** [P1] should show empty state when no runs exist
  - **Status:** RED — BacktestPage does not exist
  - **Verifies:** AC #10 — empty state
- [ ] **Test:** [P1] should format Net P&L as currency with color (green positive, red negative)
  - **Status:** RED — BacktestPage does not exist
  - **Verifies:** AC #1 — decimal display formatting
- [ ] **Test:** [P1] should format profit factor and Sharpe with 2 decimal places
  - **Status:** RED — BacktestPage does not exist
  - **Verifies:** AC #1 — metric formatting
- [ ] **Test:** [P2] should render pagination controls from DataTable
  - **Status:** RED — BacktestPage does not exist
  - **Verifies:** AC #10 — pagination
- [ ] **Test:** [P2] should enable comparison checkboxes and "Compare Selected" button when 2 rows selected
  - **Status:** RED — BacktestPage does not exist
  - **Verifies:** AC #8 — comparison selection UI

---

### Task 6: Backtest Configuration Dialog (14 tests)

**File:** `pm-arbitrage-dashboard/src/components/backtest/NewBacktestDialog.spec.tsx` (NEW, ~300 lines)

**Field rendering — 5 tests:**

- [ ] **Test:** [P0] should render all config fields: date range pickers, edge threshold, position size, max concurrent pairs, bankroll, trading window, gas estimate, exit params, walk-forward toggle
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2 — config form completeness
- [ ] **Test:** [P1] should show default values: edge threshold 0.8%, position size 3%, max pairs 10, bankroll "10000", trading window 14-23, gas "0.50", timeout 300
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2 — sensible defaults
- [ ] **Test:** [P1] should show walk-forward split ratio slider only when walk-forward toggle is enabled
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2 — conditional field visibility
- [ ] **Test:** [P1] should set walk-forward split slider default to 70%
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2 — walk-forward default
- [ ] **Test:** [P2] should follow dialog patterns from ClosePositionDialog (Dialog + DialogContent + DialogHeader structure)
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #10 — consistent dialog pattern

**Validation — 5 tests:**

- [ ] **Test:** [P0] should require start and end date (disable submit when missing)
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2 — date validation
- [ ] **Test:** [P1] should validate edge threshold range 0.1%-100%
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2 — parameter bounds
- [ ] **Test:** [P1] should validate max concurrent pairs range 1-100
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2 — parameter bounds
- [ ] **Test:** [P1] should validate timeout range 60-3600
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2 — timeout bounds
- [ ] **Test:** [P1] should validate walk-forward split slider range 10%-90%
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2 — slider bounds

**Submission — 4 tests:**

- [ ] **Test:** [P0] should call useCreateBacktest mutation with correct payload on submit (edge threshold as decimal: 0.8% → 0.008)
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2 — correct value conversion
- [ ] **Test:** [P1] should disable submit button while mutation is pending
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2 — prevent double submit
- [ ] **Test:** [P1] should close dialog on successful submission
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2, #3 — post-submit behavior
- [ ] **Test:** [P1] should show error toast on submission failure
  - **Status:** RED — NewBacktestDialog does not exist
  - **Verifies:** AC #2 — error feedback

---

### Task 7: Backtest Detail Page (10 tests)

**File:** `pm-arbitrage-dashboard/src/pages/BacktestDetailPage.spec.tsx` (NEW, ~200 lines)

- [ ] **Test:** [P0] should render header with run ID, status badge, date range, and config summary
  - **Status:** RED — BacktestDetailPage does not exist
  - **Verifies:** AC #4 — detail page header
- [ ] **Test:** [P0] should render tab navigation: Summary | Sensitivity | Walk-Forward | Positions
  - **Status:** RED — BacktestDetailPage does not exist
  - **Verifies:** AC #4, #5, #6 — tabbed layout
- [ ] **Test:** [P1] should render cancel button when run status is SIMULATING or LOADING_DATA
  - **Status:** RED — BacktestDetailPage does not exist
  - **Verifies:** AC #3 — cancel running runs
- [ ] **Test:** [P1] should not render cancel button when run status is COMPLETE or FAILED
  - **Status:** RED — BacktestDetailPage does not exist
  - **Verifies:** AC #3 — no cancel for terminal states
- [ ] **Test:** [P0] should render SummaryMetricsPanel on Summary tab
  - **Status:** RED — BacktestDetailPage does not exist
  - **Verifies:** AC #4 — summary tab content
- [ ] **Test:** [P1] should render SensitivityCharts on Sensitivity tab
  - **Status:** RED — BacktestDetailPage does not exist
  - **Verifies:** AC #5 — sensitivity tab content
- [ ] **Test:** [P1] should render WalkForwardPanel on Walk-Forward tab
  - **Status:** RED — BacktestDetailPage does not exist
  - **Verifies:** AC #6 — walk-forward tab content
- [ ] **Test:** [P0] should render KnownLimitationsCollapsible on Summary tab
  - **Status:** RED — BacktestDetailPage does not exist
  - **Verifies:** AC #9 — limitations visible from report view
- [ ] **Test:** [P1] should show loading skeleton while run data loads
  - **Status:** RED — BacktestDetailPage does not exist
  - **Verifies:** AC #10 — loading state
- [ ] **Test:** [P1] should use DashboardPanel wrappers for each section
  - **Status:** RED — BacktestDetailPage does not exist
  - **Verifies:** AC #10 — consistent layout

---

### Task 8: Summary Metrics Panel (8 tests)

**File:** `pm-arbitrage-dashboard/src/components/backtest/SummaryMetricsPanel.spec.tsx` (NEW, ~180 lines)

- [ ] **Test:** [P0] should render 6 metrics: Total Trades, Profit Factor, Net P&L, Max Drawdown, Sharpe Ratio, Win Rate
  - **Status:** RED — SummaryMetricsPanel does not exist
  - **Verifies:** AC #4 — summary metrics display
- [ ] **Test:** [P0] should display bootstrap 95% CI below Profit Factor as "[lower – upper]" format
  - **Status:** RED — SummaryMetricsPanel does not exist
  - **Verifies:** AC #4 — CI display for profit factor
- [ ] **Test:** [P0] should display bootstrap 95% CI below Sharpe Ratio as "[lower – upper]" format
  - **Status:** RED — SummaryMetricsPanel does not exist
  - **Verifies:** AC #4 — CI display for Sharpe
- [ ] **Test:** [P1] should color Net P&L green when positive, red when negative
  - **Status:** RED — SummaryMetricsPanel does not exist
  - **Verifies:** AC #4 — visual P&L indicator
- [ ] **Test:** [P1] should format Net P&L as USD currency (e.g., "$1,234.56")
  - **Status:** RED — SummaryMetricsPanel does not exist
  - **Verifies:** AC #4 — decimal display formatting
- [ ] **Test:** [P1] should render DataQualityPanel with pair count, total data points, coverage gaps, excluded periods
  - **Status:** RED — SummaryMetricsPanel does not exist
  - **Verifies:** AC #4 — data quality summary
- [ ] **Test:** [P2] should handle null CI gracefully (display "N/A" or omit CI range)
  - **Status:** RED — SummaryMetricsPanel does not exist
  - **Verifies:** AC #4 — edge case: insufficient data for CI
- [ ] **Test:** [P2] should use MetricDisplay component pattern from DashboardPage
  - **Status:** RED — SummaryMetricsPanel does not exist
  - **Verifies:** AC #10 — consistent component reuse

---

### Task 9: Sensitivity Analysis Charts (14 tests)

**File:** `pm-arbitrage-dashboard/src/components/backtest/SensitivityCharts.spec.tsx` (NEW, ~350 lines)

**Data transformation — 4 tests:**

- [ ] **Test:** [P0] should transform sweep data from API shape (parallel arrays of string decimals) into Recharts data points array
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #5 — data transformation for chart rendering
- [ ] **Test:** [P0] should parse string decimal values to numbers (e.g., "1.45" → 1.45) for chart rendering
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #5 — string-to-number conversion
- [ ] **Test:** [P1] should handle null sharpeRatio values in sweep data (skip nulls in line, don't break chart)
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #5 — null handling in chart data
- [ ] **Test:** [P1] should transform each sweep into a separate chart (one per parameter)
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #5 — per-parameter chart rendering

**Chart rendering — 6 tests:**

- [ ] **Test:** [P0] should render a LineChart for each parameter sweep with x-axis (parameter values) and y-axis (metric values)
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #5 — interactive line charts
- [ ] **Test:** [P0] should render degradation boundary as vertical ReferenceLine at breakEvenValue with description label
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #5 — degradation boundary visualization
- [ ] **Test:** [P0] should render horizontal ReferenceLine at profitFactor = 1.0 labeled "Breakeven"
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #5 — breakeven reference line
- [ ] **Test:** [P1] should render recommended value as vertical ReferenceLine with label
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #5 — recommended values callout
- [ ] **Test:** [P1] should provide metric toggle (buttons/tabs) to switch y-axis between Profit Factor / Sharpe / Max Drawdown / Net P&L
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #5 — metric toggle UI
- [ ] **Test:** [P1] should render recommended parameters table below charts (best by profit factor and Sharpe)
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #5 — recommended parameters section

**Trigger & progress — 3 tests:**

- [ ] **Test:** [P0] should render "Run Sensitivity Analysis" button when no sensitivity results exist
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #7 — trigger button when empty
- [ ] **Test:** [P1] should render progress bar ("Completed X / Y sweeps") when sweep is in progress
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #7 — progress indication
- [ ] **Test:** [P1] should display warning banner when partial=true: "Sensitivity analysis timed out — showing {completed}/{total} sweeps"
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #5 — partial results handling

**Edge case — 1 test:**

- [ ] **Test:** [P2] should use ChartContainer + ChartConfig + ChartTooltip from shadcn Chart component
  - **Status:** RED — SensitivityCharts does not exist
  - **Verifies:** AC #10 — shadcn chart integration

---

### Task 10: Walk-Forward Analysis Panel (10 tests)

**File:** `pm-arbitrage-dashboard/src/components/backtest/WalkForwardPanel.spec.tsx` (NEW, ~220 lines)

- [ ] **Test:** [P0] should render two-column layout: "In-Sample (Train)" panel left, "Out-of-Sample (Test)" panel right
  - **Status:** RED — WalkForwardPanel does not exist
  - **Verifies:** AC #6 — train/test visual distinction
- [ ] **Test:** [P0] should display metrics in each panel: total positions, profit factor, Sharpe, net P&L, max drawdown, capital utilization
  - **Status:** RED — WalkForwardPanel does not exist
  - **Verifies:** AC #6 — panel content
- [ ] **Test:** [P0] should display degradation row between panels with % degradation per metric
  - **Status:** RED — WalkForwardPanel does not exist
  - **Verifies:** AC #6 — degradation display
- [ ] **Test:** [P0] should color-code degradation: green < 15%, yellow 15-30%, red > 30%
  - **Status:** RED — WalkForwardPanel does not exist
  - **Verifies:** AC #6 — visual degradation severity
- [ ] **Test:** [P0] should render destructive Alert banner when overfitFlags array is non-empty: "Potential overfitting detected: {metrics} show >30% degradation"
  - **Status:** RED — WalkForwardPanel does not exist
  - **Verifies:** AC #6 — overfit warning alert
- [ ] **Test:** [P1] should not render overfit alert when overfitFlags array is empty
  - **Status:** RED — WalkForwardPanel does not exist
  - **Verifies:** AC #6 — no false positives
- [ ] **Test:** [P1] should display train/test date ranges with train%/test% split labels
  - **Status:** RED — WalkForwardPanel does not exist
  - **Verifies:** AC #6 — date range context
- [ ] **Test:** [P1] should format degradation values as percentages (API 0.0-1.0 → display as %)
  - **Status:** RED — WalkForwardPanel does not exist
  - **Verifies:** AC #6 — degradation formatting
- [ ] **Test:** [P2] should handle null degradation values (display "N/A")
  - **Status:** RED — WalkForwardPanel does not exist
  - **Verifies:** AC #6 — edge case: null metrics
- [ ] **Test:** [P2] should render negative degradation (improvement) in green without flag
  - **Status:** RED — WalkForwardPanel does not exist
  - **Verifies:** AC #6 — improvement direction

---

### Task 11: Run Comparison View (10 tests)

**File:** `pm-arbitrage-dashboard/src/components/backtest/RunComparisonView.spec.tsx` (NEW, ~220 lines)

- [ ] **Test:** [P0] should render side-by-side layout: Run A | Delta | Run B
  - **Status:** RED — RunComparisonView does not exist
  - **Verifies:** AC #8 — comparison layout
- [ ] **Test:** [P0] should display summary metrics for both runs with delta values
  - **Status:** RED — RunComparisonView does not exist
  - **Verifies:** AC #8 — metric comparison
- [ ] **Test:** [P0] should color delta values green for improvement (higher P&L, profit factor, Sharpe) and red for degradation
  - **Status:** RED — RunComparisonView does not exist
  - **Verifies:** AC #8 — delta color coding
- [ ] **Test:** [P0] should highlight config differences between the two runs
  - **Status:** RED — RunComparisonView does not exist
  - **Verifies:** AC #8 — config diff display
- [ ] **Test:** [P1] should compute delta as Run B - Run A (first run = baseline)
  - **Status:** RED — RunComparisonView does not exist
  - **Verifies:** AC #8 — delta calculation direction
- [ ] **Test:** [P1] should fetch both runs and reports in parallel using useQueries
  - **Status:** RED — RunComparisonView does not exist
  - **Verifies:** AC #8 — efficient data fetching
- [ ] **Test:** [P1] should read run IDs from URL query param ?compare=uuid1,uuid2
  - **Status:** RED — RunComparisonView does not exist
  - **Verifies:** AC #8 — URL state for shareability
- [ ] **Test:** [P1] should show loading state while either run is loading
  - **Status:** RED — RunComparisonView does not exist
  - **Verifies:** AC #8 — loading UX
- [ ] **Test:** [P2] should show error if fewer than 2 run IDs in URL
  - **Status:** RED — RunComparisonView does not exist
  - **Verifies:** AC #8 — invalid URL handling
- [ ] **Test:** [P2] should only highlight config fields that differ (not all fields)
  - **Status:** RED — RunComparisonView does not exist
  - **Verifies:** AC #8 — minimal config diff

---

### Task 12: Routing and Navigation (6 tests)

**File:** `pm-arbitrage-dashboard/src/components/backtest/KnownLimitationsSection.spec.tsx` (NEW, ~60 lines)

- [ ] **Test:** [P1] should render collapsible section with title "Known Limitations"
  - **Status:** RED — KnownLimitationsSection does not exist
  - **Verifies:** AC #9 — collapsible limitations
- [ ] **Test:** [P1] should be collapsed by default
  - **Status:** RED — KnownLimitationsSection does not exist
  - **Verifies:** AC #9 — default collapsed state
- [ ] **Test:** [P1] should render all limitation items from API data (not hardcoded)
  - **Status:** RED — KnownLimitationsSection does not exist
  - **Verifies:** AC #9 — dynamic from API response
- [ ] **Test:** [P1] should expand/collapse on click
  - **Status:** RED — KnownLimitationsSection does not exist
  - **Verifies:** AC #9 — toggle behavior

**File:** `pm-arbitrage-dashboard/src/App.spec.tsx` (NEW or EXTEND, ~40 lines)

- [ ] **Test:** [P1] should render BacktestPage at /backtesting route
  - **Status:** RED — route not configured
  - **Verifies:** AC #10 — routing
- [ ] **Test:** [P1] should render "Backtesting" entry in sidebar navigation
  - **Status:** RED — sidebar entry not added
  - **Verifies:** AC #10 — navigation integration

---

### E2E Tests: Critical User Journeys (8 tests)

**File:** `e2e/tests/ui/backtest-page.spec.ts` (NEW, ~200 lines)

- [ ] **Test:** [P0] E2E: should navigate to /backtesting and display backtest history table with runs
  - **Status:** RED — page does not exist
  - **Verifies:** AC #1, #10 — end-to-end history list
- [ ] **Test:** [P0] E2E: should open New Backtest dialog, fill config form, submit, and see new run in list
  - **Status:** RED — page does not exist
  - **Verifies:** AC #2, #3 — end-to-end create flow
- [ ] **Test:** [P0] E2E: should click a completed run row, navigate to detail page, and see Summary tab with metrics and CI
  - **Status:** RED — page does not exist
  - **Verifies:** AC #1, #4 — end-to-end report viewing
- [ ] **Test:** [P1] E2E: should switch to Sensitivity tab and see charts with reference lines (or trigger button if no results)
  - **Status:** RED — page does not exist
  - **Verifies:** AC #5, #7 — end-to-end sensitivity viewing
- [ ] **Test:** [P1] E2E: should switch to Walk-Forward tab and see train/test panels with degradation colors
  - **Status:** RED — page does not exist
  - **Verifies:** AC #6 — end-to-end walk-forward viewing
- [ ] **Test:** [P1] E2E: should select two runs and navigate to comparison view with side-by-side metrics
  - **Status:** RED — page does not exist
  - **Verifies:** AC #8 — end-to-end comparison flow
- [ ] **Test:** [P1] E2E: should persist sort/filter/page in URL and restore on reload
  - **Status:** RED — page does not exist
  - **Verifies:** AC #10 — URL state persistence
- [ ] **Test:** [P2] E2E: should display Known Limitations section collapsed by default, expand on click
  - **Status:** RED — page does not exist
  - **Verifies:** AC #9 — end-to-end limitations section

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **Total tests** | **120** |
| Component tests | 84 |
| Hook tests | 18 |
| Integration tests (engine gateway) | 3 |
| WS provider tests | 7 |
| E2E tests | 8 |
| P0 (critical) | 38 |
| P1 (high) | 62 |
| P2 (medium) | 20 |

## Acceptance Criteria Coverage Matrix

| AC | Component | Hook | Integration | E2E | Coverage |
|----|-----------|------|-------------|-----|----------|
| #1 History list | 10 tests | 3 tests | — | 2 tests | Full |
| #2 Config dialog | 14 tests | 3 tests | — | 1 test | Full |
| #3 Run progress | 4 tests | 1 test | 3 tests + 4 WS | 1 test | Full |
| #4 Calibration report | 8 tests | 2 tests | — | 1 test | Full |
| #5 Sensitivity charts | 11 tests | 1 test | — | 1 test | Full |
| #6 Walk-forward panel | 10 tests | 1 test | — | 1 test | Full |
| #7 Trigger sensitivity | 3 tests | 2 tests | 1 test + 1 WS | 1 test | Full |
| #8 Run comparison | 10 tests | — | — | 1 test | Full |
| #9 Known limitations | 4 tests | — | — | 1 test | Full |
| #10 Dashboard patterns | 10 tests | 2 tests | — | 1 test | Full |

## TDD Red Phase Status

All 120 tests are in RED phase (will fail until feature implemented).

**Next steps for dev agent:**
1. Load this checklist at story start
2. Implement in TDD Red-Green-Refactor cycles
3. Trace each implementation test back to a checklist item
4. Mark items as covered during implementation
5. All items must have passing tests before story completion

## Implementation Guidance

**New files to create:**
- `pm-arbitrage-dashboard/src/hooks/useBacktest.ts`
- `pm-arbitrage-dashboard/src/pages/BacktestPage.tsx`
- `pm-arbitrage-dashboard/src/pages/BacktestDetailPage.tsx`
- `pm-arbitrage-dashboard/src/components/backtest/NewBacktestDialog.tsx`
- `pm-arbitrage-dashboard/src/components/backtest/SummaryMetricsPanel.tsx`
- `pm-arbitrage-dashboard/src/components/backtest/SensitivityCharts.tsx`
- `pm-arbitrage-dashboard/src/components/backtest/WalkForwardPanel.tsx`
- `pm-arbitrage-dashboard/src/components/backtest/RunComparisonView.tsx`
- `pm-arbitrage-dashboard/src/components/backtest/KnownLimitationsSection.tsx`
- `pm-arbitrage-dashboard/src/components/backtest/BacktestStatusBadge.tsx`

**Existing files to modify:**
- `pm-arbitrage-dashboard/src/providers/WebSocketProvider.tsx` — add backtest event handlers
- `pm-arbitrage-dashboard/src/types/ws-events.ts` — add backtest WS event types
- `pm-arbitrage-dashboard/src/App.tsx` — add /backtesting routes
- `pm-arbitrage-dashboard/src/components/AppSidebar.tsx` — add "Backtesting" nav entry
- `pm-arbitrage-engine/src/dashboard/dashboard.gateway.ts` — add @OnEvent handlers (~20 lines)

**Critical patterns to follow:**
- Query hooks: follow `useDashboard.ts` patterns (queryKey, staleTime, select, error handling)
- WebSocket: follow `WebSocketProvider.tsx` switch/case pattern for event → invalidation
- DataTable: use `urlStateKey` prop for URL state sync
- Dialogs: follow `ClosePositionDialog.tsx` structure
- Charts: use shadcn `ChartContainer` + Recharts `LineChart` + `ReferenceLine`
