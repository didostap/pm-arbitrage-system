# Story 9.21: Dashboard UX Clarity Audit

Status: done

## Story

As a **system operator**,
I want **tooltips, calculation explanations, and contextual help on every dashboard page**,
so that **I can understand every number, indicator, and status on the dashboard without referencing external documentation or source code**.

## Acceptance Criteria

### Phase 1: Audit (must complete before any code changes)

1. **Page-by-page review**: Systematically audit all 7 dashboard views: Dashboard (overview), Positions (Open/All), Position Detail, Matches (Approved/Pending/Rejected), Match Detail, Performance, Stress Test. For each page, inspect every metric, label, status indicator, color-coded element, and interactive control. There is no "Settings" page — bankroll editing is a dialog on the Dashboard page and must be covered there. [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md#Story-9-21 — "Systematic page-by-page review"]

2. **Structured findings document**: Produce `_bmad-output/implementation-artifacts/9-21-ux-audit-findings.md` with a table per page. Columns: `Element` | `Current State` | `Recommended Change` | `Priority (P0/P1/P2)`. Each row describes one discrete UX gap. The document is the implementation checklist — every P0/P1 row becomes a task. [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md#Story-9-21 — "structured findings document"]

3. **Priority classification**: Apply these definitions consistently:
   - **P0 — Misleading without explanation**: The element actively confuses the operator or could lead to incorrect decisions (e.g., a metric whose meaning isn't what the label implies, a color whose threshold is invisible, an "estimated" indicator without context).
   - **P1 — Unclear but not misleading**: The element is correct but requires operator knowledge or source code reading to understand (e.g., unexplained abbreviations, unlabeled calculation methodology, missing units).
   - **P2 — Nice-to-have polish**: The element is understandable but could be improved (e.g., additional drill-down context, inline sparklines, expected-vs-actual comparisons, dynamic threshold values from the backend).
   [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md#Story-9-21 — "Prioritize findings"]

### Implementation Gate (between Phase 1 and Phase 2)

4. **Operator review**: After producing the findings document, PAUSE and present a summary to the operator (Arbi): total finding count by priority, notable P0 items, and the top-level structure. Wait for approval before implementing. If running autonomously (dev-story), present findings in the conversation and ask for confirmation. [Derived from: Story 9-20 investigation gate pattern, sprint-change-proposal "artifact for Arbi's review before implementation begins"]

### Phase 2: Implementation (P0 + P1 items only)

5. **P0 items implemented**: Every P0 finding from the audit has a corresponding tooltip, label change, or contextual help addition. Each implementation follows the established tooltip pattern (see Dev Notes). [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md — "Implement P0 and P1 items"]

6. **P1 items implemented**: Every P1 finding from the audit has a corresponding tooltip, label change, or contextual help addition. [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md — "Implement P0 and P1 items"]

7. **P2 items documented**: P2 findings remain in the findings document as a backlog for future stories. No implementation required. [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md — "Document P2 items for future sprints"]

8. **Consistent tooltip pattern**: All new info tooltips use the same visual treatment: shadcn/ui `Tooltip` component with `Info` icon (lucide-react) trigger, `className="max-w-xs"` for readability. No inline `title` attributes. No custom tooltip implementations. Do NOT add info tooltips to elements that already have value-level tooltips (PnlCell estimated indicator, ExitProximityIndicator bars) — avoid duplicate tooltip triggers in close proximity. [Derived from: standardization of existing ad-hoc tooltip patterns in PnlCell.tsx, RiskRewardCell.tsx, ExitProximityIndicator.tsx]

### Phase 3: Verification

9. **Operator comprehension test**: After implementation, the operator can look at any page and understand every visible metric, status, and indicator without needing to open source code. This is the success criteria from the sprint change proposal. [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md — "Operator can understand every number on the dashboard without referencing documentation"]

10. **No visual regressions**: Tooltips do not break existing layout, overflow containers, or interfere with interactive elements (sort headers, action buttons, navigation). Verified by visual inspection of all 7 pages. [Derived from: dashboard UX continuity]

11. **Lint clean**: `cd pm-arbitrage-dashboard && pnpm lint` passes. [Source: pm-arbitrage-dashboard/package.json — `"lint": "eslint ."`]

12. **No new dependencies**: Verify `package.json` has no new entries. Implementation uses only libraries already installed (`radix-ui`, `lucide-react`, `tailwindcss`, shadcn/ui components). [Derived from: Low effort scope classification]

## Tasks / Subtasks

### Phase 1: Audit (AC: #1, #2, #3)

- [x] **Task 1:** Audit Dashboard (overview) page (AC: #1, #2, #3)
  - [x] 1.1: Review all MetricDisplay cards: "Trailing 7d P&L", "Execution Quality", "Open Positions", "Active Alerts" — check if meaning/calculation is self-evident
  - [x] 1.2: Review Capital Overview section: "Total Bankroll", "Deployed", "Available", "Reserved" — check if allocation logic is explained
  - [x] 1.3: Review HealthComposite: platform health dots, "healthy"/"degraded"/"disconnected"/"initializing" statuses, "dataFresh" vs "stale data" label, mode badges (LIVE/PAPER)
  - [x] 1.4: Review EditBankrollDialog: does it explain what changing bankroll affects?
  - [x] 1.5: Review ConnectionStatus (WebSocket indicator): does "connected"/"disconnected" explain what it means for data freshness?
  - [x] 1.6: Record findings in table format

- [x] **Task 2:** Audit Positions pages (Open/All tabs) (AC: #1, #2, #3)
  - [x] 2.1: Review column headers: Pair, Entry Prices (K/P), Current Prices (K/P), Init Edge, Current Edge, P&L, Risk/Reward (SL/TP), Time to Resolution, Exit Proximity (SL/TP), Status, Mode
  - [x] 2.2: Review existing tooltip implementations: PnlCell estimated indicator, RiskRewardCell SL/TP projection, ExitProximityIndicator bars — are they sufficient?
  - [x] 2.3: Review estimated price treatment (tilde + amber dashed underline from Story 9-19) — is the "thin order book depth" tooltip adequate?
  - [x] 2.4: Review status badges (OPEN, SINGLE_LEG_EXPOSED, EXIT_PARTIAL, CLOSED, RECONCILIATION_REQUIRED) — are meanings clear? Also review exit type badges (STOP_LOSS, TAKE_PROFIT, TIME_BASED, MANUAL) in ExitTypeBadge.tsx.
  - [x] 2.5: Review mode filter (All/Live/Paper) and paper position styling (amber border, [PAPER] tag)
  - [x] 2.6: Review sort indicators and pagination — any UX confusion?
  - [x] 2.7: Record findings

- [x] **Task 3:** Audit Position Detail page (AC: #1, #2, #3)
  - [x] 3.1: Review entry prices breakdown, capital per platform, fees
  - [x] 3.2: Review current state section: current edge, P&L, prices (with estimated indicator)
  - [x] 3.3: Review exit state: SL/TP triggered prices, exit thresholds
  - [x] 3.4: Review order history table: leg, quantity, filled price, fees
  - [x] 3.5: Review audit log / events timeline
  - [x] 3.6: Record findings

- [x] **Task 4:** Audit Matches pages (Approved/Pending/Rejected tabs) (AC: #1, #2, #3)
  - [x] 4.1: Review column headers: Status, Contract descriptions, Confidence Score, Est. APR, Cluster, Resolution Date, Primary Leg, Position Count
  - [x] 4.2: Review confidence score — is the calculation methodology explained? (What does 97% mean?)
  - [x] 4.3: Review "Est. APR" — is the annualized return calculation explained?
  - [x] 4.4: Review "Cluster" — is the correlation cluster concept explained?
  - [x] 4.5: Review "Primary Leg" — is it clear which platform trades first and why?
  - [x] 4.6: Review approve/reject actions — is it clear what approval means operationally?
  - [x] 4.7: Record findings

- [x] **Task 5:** Audit Match Detail page (AC: #1, #2, #3)
  - [x] 5.1: Review match metadata section
  - [x] 5.2: Review associated positions sub-table
  - [x] 5.3: Record findings

- [x] **Task 6:** Audit Performance page (AC: #1, #2, #3)
  - [x] 6.1: Review weekly metrics: Trades, Closed, P&L, Hit Rate, Slippage, Opps (D/F/E), Autonomy Ratio. Note: "AR" column already has a tooltip ("Autonomy Ratio") — verify it's sufficient. There is NO Sharpe Ratio or ROI column.
  - [x] 6.2: Review trends summary: Edge Trend, Opportunity Frequency, Opportunity Baseline, Avg Slippage
  - [x] 6.3: Review lookback selector (4/8/12/26/52 weeks)
  - [x] 6.4: Review "data insufficiency" alert — when is it shown and is it clear?
  - [x] 6.5: Record findings

- [x] **Task 7:** Audit Stress Test page (AC: #1, #2, #3)
  - [x] 7.1: Review stress test results: worst-case drawdown, max recovery time, VaR metrics
  - [x] 7.2: Review scenario descriptions — are they self-explanatory?
  - [x] 7.3: Review "Run Stress Test" action — is it clear what it does and how long it takes?
  - [x] 7.4: Record findings

- [x] **Task 8:** Compile findings document (AC: #2, #3)
  - [x] 8.1: Create `_bmad-output/implementation-artifacts/9-21-ux-audit-findings.md`
  - [x] 8.2: Organize findings by page with per-page tables
  - [x] 8.3: Add summary counts: total P0, total P1, total P2
  - [x] 8.4: Verify every finding has a concrete recommended change (not vague "add tooltip")

### Implementation Gate (AC: #4)

- [x] **Task 9:** PAUSE — Present audit findings to operator and await approval before Phase 2.

### Phase 2: Implementation (AC: #5, #6, #7, #8)

- [x] **Task 10:** Create shared tooltip helper (AC: #8)
  - [x] 10.1: Create `src/components/InfoTooltip.tsx` — reusable component wrapping shadcn Tooltip + lucide `Info` icon with consistent sizing, color, and sideOffset
  - [x] 10.2: Ensure InfoTooltip accepts `content: ReactNode` for rich tooltip text (multi-line, bold terms, etc.)
  - [x] 10.3: Ensure InfoTooltip accepts optional `iconSize` (default 14) and `className` for layout flexibility

- [x] **Task 11:** Implement P0 findings (AC: #5)
  - [x] 11.1: D1 — Execution Quality metric tooltip (DashboardPage)
  - [x] 11.2: D2 — Platform health status meanings tooltip (HealthComposite)
  - [x] 11.3: D3 — "Stale data" inline tooltip (HealthComposite)
  - [x] 11.4: P1 — Init Edge column header tooltip (PositionsPage)
  - [x] 11.5: P2 — Curr Edge column header tooltip (PositionsPage)
  - [x] 11.6: P3 — StatusBadge per-status tooltips (StatusBadge component)
  - [x] 11.7: PD1 — Current Edge label tooltip (PositionDetailPage)
  - [x] 11.8: PD2 — Initial Edge label tooltip (PositionDetailPage)
  - [x] 11.9: M1 — Confidence column header tooltip (MatchesPage)
  - [x] 11.10: M2 — Est. APR column header tooltip (MatchesPage)
  - [x] 11.11: PE1 — Opps (D/F/E) column header tooltip (PerformancePage)
  - [x] 11.12: ST1 — VaR (95%) metric tooltip (StressTestPage)
  - [x] 11.13: ST2 — VaR (99%) metric tooltip (StressTestPage)

- [x] **Task 12:** Implement P1 findings (AC: #6)
  - [x] 12.1: D4 — Trailing 7d P&L tooltip (DashboardPage)
  - [x] 12.2: D5 — Active Alerts tooltip (DashboardPage)
  - [x] 12.3: D6 — Total Bankroll tooltip (DashboardPage)
  - [x] 12.4: D7 — Deployed tooltip (DashboardPage)
  - [x] 12.5: D8 — Available tooltip with color thresholds (DashboardPage)
  - [x] 12.6: D9 — Reserved tooltip (DashboardPage)
  - [x] 12.7: D10 — Mode badge explanation added to health tooltip (HealthComposite)
  - [x] 12.8: D11 — "API disconnected" inline tooltip (HealthComposite)
  - [x] 12.9: D12 — ConnectionStatus WebSocket tooltip (ConnectionStatus)
  - [x] 12.10: P4 — Entry column tooltip (PositionsPage)
  - [x] 12.11: P5 — Current column tooltip (PositionsPage)
  - [x] 12.12: P6 — P&L column header tooltip (PositionsPage)
  - [x] 12.13: P7 — Resolution column tooltip (PositionsPage)
  - [x] 12.14: P8 — ExitTypeBadge per-type tooltips (ExitTypeBadge component)
  - [x] 12.15: PD3 — Unrealized P&L tooltip (PositionDetailPage)
  - [x] 12.16: PD4 — Gross P&L tooltip (PositionDetailPage)
  - [x] 12.17: PD5 — Net P&L tooltip (PositionDetailPage)
  - [x] 12.18: PD6 — Slippage column tooltip (PositionDetailPage)
  - [x] 12.19: PD7 — Renamed "Req. Price" to "Requested" (PositionDetailPage)
  - [x] 12.20: M3 — Cluster column tooltip (MatchesPage)
  - [x] 12.21: M4 — Primary Leg column tooltip (MatchesPage)
  - [x] 12.22: M5 — Positions column tooltip (MatchesPage)
  - [x] 12.23: MD1 — Criteria Hash tooltip (MatchDetailPage)
  - [x] 12.24: MD2 — Diverged tooltip (MatchDetailPage)
  - [x] 12.25: MD3 — Total Cycles Traded tooltip (MatchDetailPage)
  - [x] 12.26: MD4 — Freshness tooltip (MatchDetailPage)
  - [x] 12.27: MD5 — Net Edge tooltip (MatchDetailPage)
  - [x] 12.28: PE2 — Trades column tooltip (PerformancePage)
  - [x] 12.29: PE3 — Hit Rate column tooltip (PerformancePage)
  - [x] 12.30: PE4 — Slippage column tooltip (PerformancePage)
  - [x] 12.31: PE5 — Enhanced AR tooltip text (PerformancePage)
  - [x] 12.32: PE6 — Opportunities/wk metric tooltip (TrendsSummary)
  - [x] 12.33: PE7 — Edge/wk metric tooltip (TrendsSummary)
  - [x] 12.34: PE8 — Avg Slippage metric tooltip (TrendsSummary)
  - [x] 12.35: PE9 — Edge Trend tooltip (TrendsSummary)
  - [x] 12.36: PE10 — Opp Baseline tooltip (TrendsSummary)
  - [x] 12.37: ST3 — Worst-Case Loss tooltip (StressTestPage)
  - [x] 12.38: ST4 — Drawdown Probabilities section tooltip (StressTestPage)
  - [x] 12.39: ST5 — P&L Distribution section tooltip (StressTestPage)
  - [x] 12.40: ST6 — Synthetic Scenarios section tooltip (StressTestPage)
  - [x] 12.41: ST7 — Enhanced Vol tooltip text (StressTestPage)
  - [x] 12.42: ST8 — Run Stress Test button tooltip (StressTestPage)

- [x] **Task 13:** Mark P2 items as documented (AC: #7)
  - [x] 13.1: Verify all P2 items remain in findings doc with "P2 — future" notation

### Phase 3: Verification (AC: #9, #10, #11, #12)

- [ ] **Task 14:** Visual verification (AC: #9, #10)
  - [ ] 14.1: Navigate every page, hover every tooltip, verify content accuracy
  - [ ] 14.2: Check no layout breakage on any page
  - [ ] 14.3: Verify tooltips don't block interactive elements (sort headers, buttons)
  - [ ] 14.4: Verify all P0/P1 implementations use InfoTooltip component (not ad-hoc Tooltip usage)

- [x] **Task 15:** Lint and dependency verification (AC: #11, #12)
  - [x] 15.1: Run `pnpm lint` on dashboard SPA — clean
  - [x] 15.2: Verify no new packages in `package.json` (diff against pre-implementation state)

## Dev Notes

### Scope: Frontend Only (`pm-arbitrage-dashboard/`)

This story modifies ONLY the dashboard SPA. No backend (pm-arbitrage-engine) changes. Tooltip content uses static text referencing system constants (e.g., "3% of bankroll per pair", "60s staleness threshold") rather than dynamic values from the API. Dynamic threshold display is a P2 item for a future story.
[Source: disambiguation #3 — confirmed frontend-only]

### Existing Tooltip Infrastructure (REUSE, do not reinvent)

**Already installed and configured:**
- `TooltipProvider` wraps entire app in `App.tsx` with `delayDuration={0}` (instant open — shadcn default overrides Radix's 700ms). This means tooltips appear immediately on hover, which is appropriate for a data-dense dashboard. Do NOT change this.
- shadcn/ui `Tooltip`, `TooltipContent`, `TooltipTrigger` in `src/components/ui/tooltip.tsx`
- shadcn's `TooltipContent` defaults: `sideOffset={0}`, includes `<TooltipPrimitive.Arrow>` automatically
- `lucide-react` provides `Info`, `HelpCircle`, `CircleHelp` icons (use `Info` for consistency)
- Radix Tooltip is fully WCAG-accessible: keyboard navigable (Tab/Escape), ARIA attributes automatic
- Note: `TooltipProvider` is at app root — no need to add another one in child components
[Source: pm-arbitrage-dashboard/src/components/ui/tooltip.tsx lines 6-7, App.tsx line 50, radix-ui.com/primitives/docs/components/tooltip]

**Existing usage patterns (5 locations) — match these exactly:**

1. `PnlCell.tsx` (lines 26-39) — Estimated P&L: tilde prefix + `opacity-60` + dashed amber underline + tooltip "Estimated — thin order book depth"
2. `RiskRewardCell.tsx` (lines 11-19) — SL/TP values: tooltip "Projected P&L at stop-loss / take-profit thresholds"
3. `ExitProximityIndicator.tsx` (lines 36-82) — SL/TP bars: color meaning tooltips
4. `AppSidebar.tsx` (lines 18-21) — Collapsed sidebar nav labels
5. `PerformancePage.tsx` (lines 117-122) — "AR" column header: tooltip "Autonomy Ratio"

**Pattern for NEW info tooltips (not estimated-value tooltips):**
```tsx
import { Info } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

// Note: Requires TooltipProvider at app root (already configured in App.tsx)
// Inline next to a label or column header
<span className="flex items-center gap-1">
  Label Text
  <Tooltip>
    <TooltipTrigger asChild>
      <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
    </TooltipTrigger>
    <TooltipContent side="top" className="max-w-xs">
      <p>Explanation of what this metric means.</p>
    </TooltipContent>
  </Tooltip>
</span>
```

The `InfoTooltip` wrapper component (Task 10) encapsulates this pattern to avoid repetition across 15+ locations.

### Dashboard Pages — Complete Inventory

| Route | Page Component | Data Hook | Key Metrics |
|---|---|---|---|
| `/` | `DashboardPage.tsx` | `useDashboardOverview()`, `useDashboardHealth()`, `useBankrollConfig()` | Trailing 7d P&L, Execution Quality %, Open Positions, Active Alerts, Capital Breakdown, Platform Health |
| `/positions/open` | `PositionsPage.tsx` | `useDashboardPositions()` | Entry/Current Prices, Init/Current Edge, P&L, SL/TP Risk/Reward, Exit Proximity, Status |
| `/positions/:id` | `PositionDetailPage.tsx` | `usePositionDetails()` | Entry breakdown, fees, current state, exit state, order history, audit events |
| `/matches/approved` | `MatchesPage.tsx` | `useDashboardMatches()` | Confidence Score, Est. APR, Cluster, Primary Leg, Resolution Date, Position Count |
| `/matches/:id` | `MatchDetailPage.tsx` | `useMatchDetail()` | Match metadata + position history sub-table |
| `/performance` | `PerformancePage.tsx` | `useDashboardPerformance()`, `useDashboardTrends()` | Trades, Closed, P&L, Hit Rate, Slippage, Opps (D/F/E), Autonomy Ratio, TrendsSummary |
| `/stress-test` | `StressTestPage.tsx` | `useStressTestLatest()`, `useRunStressTest()` | Drawdown, Recovery Time, VaR, Scenario Results |

[Source: codebase investigation — `pm-arbitrage-dashboard/src/pages/`, `App.tsx` routes]

### Shadcn/UI Components Available

Already installed: `Tooltip`, `Alert`, `Badge`, `Button`, `Card`, `Dialog`, `Input`, `Textarea`, `Separator`, `Sheet`, `Sidebar`, `Skeleton`, `Table`, `Tabs` (unused). No new shadcn components needed.
[Source: codebase investigation — `pm-arbitrage-dashboard/src/components/ui/`]

### Cell/Table Components

Column renderers in `src/components/cells/`:
- `PnlCell.tsx` — P&L with estimated indicator (has tooltip)
- `RiskRewardCell.tsx` — SL/TP values (has tooltip)
- `StatusBadge.tsx` — Position status badge (NO tooltip)
- `ExitTypeBadge.tsx` — Exit type badge (NO tooltip)

Table wrapper: `DataTable.tsx` — generic sortable/paginated table. Column definitions are inline in page components (not in DataTable).
[Source: codebase investigation — `pm-arbitrage-dashboard/src/components/cells/`]

### UX Specification Requirements (guide audit priorities)

The UX spec establishes these principles that inform what P0/P1 means:

- **Transparency layer**: Every automated decision surfaces reasoning on-demand. "Why did the system do X?" must be answerable from the dashboard. [Source: ux-design-specification.md#transparency-layer]
- **Metric context**: Every metric shown has context (target line, acceptable range, comparison to model). The absence of context makes a metric misleading. [Source: ux-design-specification.md#metric-display-standard]
- **Terminology consistency**: Fixed naming that never changes between sessions. If the dashboard uses a term, the tooltip must match the same term the code and docs use. [Source: ux-design-specification.md#terminology-consistency]
- **2-minute scan target**: Dashboard overview should answer "is intervention needed?" in 10 seconds if healthy. Tooltips should not slow this down — they supplement, not replace, the visual hierarchy. [Source: ux-design-specification.md#morning-scan-dashboard]

### No Centralized Label System Exists

Labels are currently inline in components — no constants file or i18n setup. The story should NOT create a centralized label system (that's over-engineering for tooltips). Tooltip text goes directly in the component where it's displayed.
[Source: codebase investigation — no label constants found]

### Testing Requirements

The dashboard SPA has NO existing test infrastructure (no `*.spec.tsx` or `*.test.tsx` files). No new tests required for tooltip additions. If the `InfoTooltip` wrapper component contains any conditional logic beyond simple prop forwarding, add a co-located test file.
[Source: disambiguation #4 — confirmed no test requirement for pure tooltip work]

### Previous Story Intelligence

**Story 9-19 (VWAP Dashboard Pricing)**: Established the "estimated" indicator pattern: tilde prefix + `opacity-60` + dashed amber underline + tooltip. Created `PnlCell.tsx` estimated prop, `ExitProximityIndicator.tsx` estimated prop. The dev agent should NOT alter or conflict with these existing indicators — new tooltips are additive (info icons next to labels), not replacements for the estimation indicators.
[Source: 9-19-vwap-dashboard-pricing-position-calculation-consolidation.md — completion notes]

**Story 9-20 (Staleness Investigation)**: Fixed the 70% stale rate. Health indicators now show stale only for genuine platform issues. The audit should verify that the health status meanings are clear post-fix (healthy/degraded/initializing).
[Source: 9-20-platform-staleness-investigation-remediation.md — completion notes]

**Story 9-13 (Left Sidebar Navigation)**: Established sidebar layout with TopBar for health status. Platform health dots moved from header to TopBar. Mode badges (LIVE/PAPER) added per platform.
[Source: sprint-status.yaml — Story 9-13 completion notes]

### Key Financial Concepts for Tooltip Content

These concepts need clear, concise explanations in tooltips. The dev agent should use these definitions — they are verified against the actual codebase formulas:

- **Init Edge**: The net spread at position entry after fees and gas. Formula: `|Price_A - Price_B| - fees - gas`. Must exceed 0.8% minimum threshold. [Source: CLAUDE.md#Domain-Rules, edge-calculator.service.ts]
- **Current Edge**: The current net spread using VWAP close prices for the actual position size. May differ from Init Edge due to order book depth changes. [Source: position-enrichment.service.ts]
- **Exit Proximity (SL/TP)**: 0-100% scale showing how close the position's P&L is to the stop-loss or take-profit threshold. Formula: `clamp(0, 1, (currentPnl - baseline) / (target - baseline))`. 100% = threshold reached, exit triggered. [Source: common/constants/exit-thresholds.ts — `calculateExitProximity()`]
- **Estimated Price (~)**: When the order book doesn't have sufficient depth to VWAP-price the full position, the best available price is used instead. Shown with tilde (~) prefix and amber dashed underline. Already has tooltip from Story 9-19 — do NOT duplicate. [Source: PnlCell.tsx, position-enrichment.service.ts]
- **Confidence Score**: LLM-generated 0-100 assessment of whether two contracts (Polymarket vs Kalshi) refer to the same real-world event. The LLM evaluates outcome identity, event identity, and settlement alignment. Scores ≥85 are auto-approved; below 85 requires operator review. NOT a statistical probability — it's a subjective match quality rating. [Source: confidence-scorer.service.ts lines 109-148, llm-scoring.strategy.ts lines 40-85]
- **Est. APR**: Annualized return estimate. Formula: `netEdge × (365 / daysToResolution)`. Example: 1.2% net edge with 30 days to resolution = 14.6% APR. Minimum threshold: 15% (`MIN_ANNUALIZED_RETURN`). [Source: edge-calculator.service.ts lines 361-363]
- **Cluster**: Correlation group. Positions in the same cluster are correlated — if one loses, others likely lose too. Max 15% of bankroll per cluster. [Source: CLAUDE.md#Domain-Rules]
- **Primary Leg**: The platform where the first leg of the arbitrage trade executes. The second leg follows on the other platform. [Source: execution.service.ts]
- **Execution Quality**: Ratio of successfully filled orders to total attempted orders. Formula: `filledOrders / totalOrders`. This is a **lifetime aggregate** (all-time, not windowed). [Source: dashboard.service.ts lines 95-101]
- **Hit Rate**: Percentage of closed positions that were profitable. Shown as percentage in the Performance table. [Source: PerformancePage.tsx — `hitRate` column]
- **Autonomy Ratio (AR)**: Ratio of automated decisions to operator interventions. Higher = more autonomous operation. Already has a tooltip on the Performance page header ("Autonomy Ratio"). [Source: PerformancePage.tsx lines 117-122]
- **Opps (D/F/E)**: Opportunities Detected / Filtered / Executed. Shows the funnel from detection through filtering to execution in a single compact column. [Source: PerformancePage.tsx lines 103-115]
- **VaR (Value at Risk)**: Maximum expected loss at a given confidence level, computed via Monte Carlo simulation (1000+ scenarios). VaR95 = 95% confidence losses won't exceed this amount (5th percentile). VaR99 = 99% confidence (1st percentile). [Source: stress-test.service.ts lines 156-161]

### Health Status Definitions (for audit reference)

These are the platform health states displayed in HealthComposite. Use these for tooltip content:

- **healthy**: API connected AND data fresh (last update within 60s staleness threshold). Green indicator.
- **degraded**: API connected BUT data stale (>60s since last update) OR latency p95 exceeds threshold. Yellow indicator. Operator action: check platform API status.
- **disconnected**: API not connected. Red indicator. Operator action: check network/credentials.
- **initializing**: Platform connector startup state (transient, typically <30s after engine boot). Falls through to "healthy" in composite health calculation. No operator action needed.
- **dataFresh**: Boolean derived from health status. `true` when status is `'healthy'`, `false` otherwise. Drives the "Stale data" label in the UI.
[Source: platform-health.service.ts lines 312-385, dashboard.service.ts lines 171-207, HealthComposite.tsx]

### Position Status Definitions (for audit reference)

- **OPEN**: Both legs executed successfully. Position actively monitored for exit triggers.
- **SINGLE_LEG_EXPOSED**: One leg executed, the other failed. Critical alert — requires operator decision (retry or close).
- **EXIT_PARTIAL**: Exit triggered but only one leg closed. Intermediate state during exit execution.
- **CLOSED**: Both legs closed (or position resolved). Terminal state.
- **RECONCILIATION_REQUIRED**: Position state inconsistent with platform state after restart reconciliation.

### Exit Type Definitions (for audit reference)

- **STOP_LOSS**: Position exited because P&L reached the stop-loss threshold (negative exit).
- **TAKE_PROFIT**: Position exited because P&L reached the take-profit threshold (positive exit).
- **TIME_BASED**: Position exited because resolution date approached (time-based trigger).
- **MANUAL**: Position closed by operator action.

[Source: Prisma schema enums, exit-monitor.service.ts, threshold-evaluator.service.ts]

### What NOT To Do

- **Do NOT modify backend code** — frontend-only story
- **Do NOT create a centralized label/i18n system** — over-engineering for this scope
- **Do NOT alter existing estimated-value tooltips** (PnlCell, ExitProximityIndicator) — they are correct post-9-19
- **Do NOT add component tests for static tooltip text** — no test infra exists, visual verification sufficient
- **Do NOT install new packages** — everything needed is already in package.json
- **Do NOT change the `TooltipProvider` delay settings** in App.tsx — `delayDuration={0}` (instant) is the shadcn default and appropriate for expert-user dashboards
- **Do NOT add info tooltips to elements that already have value-level tooltips** (PnlCell estimated, ExitProximityIndicator bars, AR column header) — avoid duplicate triggers
- **Do NOT add tooltips to sort column headers** — clicking sorts, not info. Put info tooltips next to the label text instead
- **Do NOT expose backend config values via new API endpoints** — use static text referencing known constants

### Project Structure Notes

All changes in `pm-arbitrage-dashboard/src/`:
```
src/
├── components/
│   ├── InfoTooltip.tsx              # NEW — reusable info tooltip wrapper
│   ├── MetricDisplay.tsx            # Modify — add optional tooltip prop
│   ├── HealthComposite.tsx          # Modify — add status explanation tooltips
│   ├── DashboardPanel.tsx           # Possibly modify — add optional header tooltip
│   ├── cells/
│   │   ├── StatusBadge.tsx          # Modify — add status meaning tooltip
│   │   └── ExitTypeBadge.tsx        # Modify — add exit type explanation
│   └── ... (other components as audit determines)
├── pages/
│   ├── DashboardPage.tsx            # Modify — add metric tooltips
│   ├── PositionsPage.tsx            # Modify — add column header tooltips
│   ├── PositionDetailPage.tsx       # Modify — add section tooltips
│   ├── MatchesPage.tsx              # Modify — add column header tooltips
│   ├── MatchDetailPage.tsx          # Modify — add field tooltips
│   ├── PerformancePage.tsx          # Modify — add metric tooltips
│   └── StressTestPage.tsx           # Modify — add metric tooltips
└── ... (exact file list determined by audit findings)
```

Note: The exact modification list will be refined after Phase 1 audit. Files listed above are the expected targets based on codebase investigation.
[Source: codebase investigation — pm-arbitrage-dashboard/src/]

### References

- [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md#Story-9-21] — Problem statement, scope, approach, deliverable format, success criteria
- [Source: ux-design-specification.md] — Transparency layer, metric context, terminology consistency, 2-minute scan target, information hierarchy
- [Source: CLAUDE.md#Domain-Rules] — Financial math definitions (edge, fees, position sizing, correlation limits)
- [Source: 9-19-vwap-dashboard-pricing-position-calculation-consolidation.md] — VWAP enrichment, estimated indicator pattern, depth-sufficient flags, PnlCell/ExitProximityIndicator changes
- [Source: 9-20-platform-staleness-investigation-remediation.md] — Health staleness fix, transition logging, post-ingestion health check
- [Source: radix-ui.com/primitives/docs/components/tooltip] — Tooltip API, accessibility (keyboard: Tab/Escape), TooltipProvider config (delayDuration, skipDelayDuration)
- [Source: pm-arbitrage-dashboard/src/App.tsx] — TooltipProvider wrapping, route structure
- [Source: pm-arbitrage-dashboard/src/components/ui/tooltip.tsx] — shadcn/ui Tooltip component (Radix wrapper)
- [Source: pm-arbitrage-dashboard/src/components/cells/PnlCell.tsx] — Existing estimated P&L tooltip pattern
- [Source: pm-arbitrage-dashboard/src/components/cells/RiskRewardCell.tsx] — Existing SL/TP tooltip pattern
- [Source: pm-arbitrage-dashboard/src/components/ExitProximityIndicator.tsx] — Existing proximity bar tooltip pattern

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Phase 1 audit: read all 7 page components + 12 shared components, produced 59 findings (13 P0, 42 P1, 4 P2)
- Findings document: `_bmad-output/implementation-artifacts/9-21-ux-audit-findings.md`
- Operator approved findings before Phase 2
- Created `InfoTooltip` component with `aria-label`, `tabIndex={0}` for accessibility, `sideOffset={4}` for positioning
- Added `titleTooltip` prop to `DashboardPanel`, `tooltip` prop to `MetricDisplay` — minimal API surface
- `StatusBadge` and `ExitTypeBadge` use value-level tooltips (badge as trigger) rather than InfoTooltip pattern — consistent with existing PnlCell/RiskRewardCell approach
- AR column (PerformancePage) and Vol column (StressTestPage) — enhanced existing tooltip text only, no InfoTooltip added per AC #8 constraint
- Renamed "Req. Price" to "Requested" in order history table for clarity
- Code review (Lad MCP): primary reviewer found 3 actionable items — fixed sideOffset and aria-label; AR column pattern intentionally kept per AC #8
- No new dependencies added, lint clean
- Code review #2 (adversarial, 2026-03-15): fixed 3 MEDIUM (findings doc summary counts 11→13 P0 + 33→42 P1, InfoTooltip generic aria-label→optional `label` prop, MatchesPage HTML entities→Unicode), 2 LOW noted (Entry Net P&L missing tooltip, StatusBadge wording softened from reference)

### File List

**Created:**
- `pm-arbitrage-dashboard/src/components/InfoTooltip.tsx`
- `_bmad-output/implementation-artifacts/9-21-ux-audit-findings.md`

**Modified:**
- `pm-arbitrage-dashboard/src/components/DashboardPanel.tsx` — added `titleTooltip` prop
- `pm-arbitrage-dashboard/src/components/MetricDisplay.tsx` — added `tooltip` prop
- `pm-arbitrage-dashboard/src/components/HealthComposite.tsx` — health status tooltip, stale data tooltip, API disconnected tooltip, mode explanation
- `pm-arbitrage-dashboard/src/components/ConnectionStatus.tsx` — WebSocket tooltip
- `pm-arbitrage-dashboard/src/components/TrendsSummary.tsx` — metric tooltips, edge trend tooltip, opp baseline tooltip
- `pm-arbitrage-dashboard/src/components/cells/StatusBadge.tsx` — per-status tooltips (5 statuses)
- `pm-arbitrage-dashboard/src/components/cells/ExitTypeBadge.tsx` — per-type tooltips (4 types)
- `pm-arbitrage-dashboard/src/pages/DashboardPage.tsx` — metric tooltips, capital overview tooltips
- `pm-arbitrage-dashboard/src/pages/PositionsPage.tsx` — column header tooltips (Entry, Current, Init Edge, Curr Edge, P&L, Resolution)
- `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx` — label tooltips (Current Edge, Initial Edge, Unrealized P&L, Gross P&L, Net P&L, Slippage), renamed Req. Price → Requested
- `pm-arbitrage-dashboard/src/pages/MatchesPage.tsx` — column header tooltips (Confidence, Est. APR, Cluster, Primary Leg, Positions)
- `pm-arbitrage-dashboard/src/pages/MatchDetailPage.tsx` — label tooltips (Criteria Hash, Diverged, Total Cycles Traded, Freshness, Net Edge)
- `pm-arbitrage-dashboard/src/pages/PerformancePage.tsx` — column header tooltips (Trades, Hit Rate, Slippage, Opps D/F/E), enhanced AR tooltip text
- `pm-arbitrage-dashboard/src/pages/StressTestPage.tsx` — metric tooltips (VaR 95%, VaR 99%, Worst-Case Loss), section tooltips (Drawdown, P&L Distribution, Synthetic), enhanced Vol tooltip, Run button tooltip
