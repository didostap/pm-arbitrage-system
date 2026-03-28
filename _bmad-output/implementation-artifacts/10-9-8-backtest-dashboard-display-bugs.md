# Story 10-9.8: Backtest Dashboard Display Bugs

Status: done

## Story

As an operator,
I want the backtest dashboard to correctly display P&L values and position details,
so that I can evaluate backtesting results accurately without misleading $0 values or missing trade data.

## Acceptance Criteria

1. **Given** a completed backtest run with `summaryMetrics.netPnl = "-7950.0000000000"`, **When** I view the Summary tab, **Then** the Net P&L metric displays `-$7,950.00` (red) instead of `$0.00`.

2. **Given** a completed backtest run with positive P&L, **When** I view the Summary tab, **Then** the Net P&L metric displays the correct positive value in green.

3. **Given** a completed backtest run with 2,049 positions, **When** I click the Positions tab, **Then** I see a DataTable with paginated position records (not a placeholder text).

4. **Given** the Positions DataTable, **Then** each row displays: Pair ID, Kalshi/Polymarket sides, entry/exit timestamps, entry/exit prices (both platforms), position size (USD), entry/exit edge, realized P&L (color-coded green/red), fees, exit reason, and holding hours.

5. **Given** more than 100 positions in a run, **When** I view the Positions tab, **Then** pagination controls allow navigating through all positions (100 per page).

6. **Given** the Positions DataTable, **When** I click a column header, **Then** the table sorts the current page by that column (client-side sort within page — the API returns pre-ordered positions by `entryTimestamp` ASC, but per-page re-sorting by any column is supported).

7. **Given** all changes are complete, **Then** existing SummaryMetricsPanel and BacktestDetailPage tests are updated and pass, and new tests cover the Positions DataTable rendering and P&L fix.

## Tasks / Subtasks

- [x] **Task 1: Fix P&L field name mismatch in SummaryMetricsPanel** (AC: #1, #2)
  - [x] 1.1 In `pm-arbitrage-dashboard/src/components/backtest/SummaryMetricsPanel.tsx`: rename `totalPnl` to `netPnl` in the type assertion (line 25), the `pnlNum` calculation (line 47), and the `formatUsd` call (line 64)
  - [x] 1.2 Update `SummaryMetricsPanel.spec.tsx`: change `mockReport.summaryMetrics.totalPnl` to `netPnl` in all mock data, add negative P&L test with `netPnl: "-7950.0000000000"` verifying `-$7,950.00` rendered in red
  - [x] 1.3 Update `BacktestDetailPage.spec.tsx`: change `mockReport.data.summaryMetrics.totalPnl` to `netPnl`

- [x] **Task 2: Create BacktestPositionsTable component** (AC: #3, #4, #6)
  - [x] 2.1 Create `pm-arbitrage-dashboard/src/components/backtest/BacktestPositionsTable.tsx`
  - [x] 2.2 Define columns using `createColumnHelper` (follow `PositionsPage.tsx` pattern):
    - Pair ID (`pairId`, text)
    - Kalshi Side / Polymarket Side (two cells or combined)
    - Entry Timestamp (`entryTimestamp`, formatted date)
    - Exit Timestamp (`exitTimestamp`, formatted date or "—")
    - Entry Prices: K/P dual display (`kalshiEntryPrice`/`polymarketEntryPrice`, `formatDecimal(value, 4)`)
    - Exit Prices: K/P dual display (`kalshiExitPrice`/`polymarketExitPrice`, or "—")
    - Position Size (`positionSizeUsd`, `formatUsd`)
    - Entry Edge (`entryEdge`, `formatDecimal(value, 4)`)
    - Exit Edge (`exitEdge`, `formatDecimal(value, 4)` or "—")
    - Realized P&L (`realizedPnl`, color-coded green/red using `PnlCell` from `src/components/cells/`)
    - Fees (`fees`, `formatUsd`)
    - Exit Reason (`exitReason`, Badge — map `EDGE_EVAPORATION`, `TIME_DECAY`, `PROFIT_CAPTURE`, `RESOLUTION_FORCE_CLOSE`, `INSUFFICIENT_DEPTH`, `SIMULATION_END`)
    - Holding Hours (`holdingHours`, format as `Xh` or `X.Xh`)
  - [x] 2.3 Use `DataTable` component with client-side sorting (not manual), pagination props. Add `data-testid="backtest-positions-table"` to wrapper div.
  - [x] 2.4 Props: `positions: BacktestPosition[]`, `positionCount: number`, `page: number`, `onPageChange: (page: number) => void`, `isLoading: boolean`

- [x] **Task 3: Integrate BacktestPositionsTable into BacktestDetailPage** (AC: #3, #5)
  - [x] 3.1 In `BacktestDetailPage.tsx`, replace the positions tab placeholder (lines 138-144) with `BacktestPositionsTable`
  - [x] 3.2 Add position pagination state: `const [positionPage, setPositionPage] = useState(1)`
  - [x] 3.3 Pass `positionLimit: 100, positionOffset: (positionPage - 1) * 100` to `useBacktestRun` (currently hardcoded to `positionLimit: 100, positionOffset: 0`)
  - [x] 3.4 Modify `useBacktestRun` in `useBacktest.ts` to accept an options object: `useBacktestRun(id: string, options?: { positionLimit?: number; positionOffset?: number })` (add to query key for proper cache isolation per page). Verify all existing callers (only `BacktestDetailPage.tsx`) — default params ensure backward compatibility.
  - [x] 3.5 Wire pagination: `BacktestPositionsTable` receives `page={positionPage}`, `onPageChange={setPositionPage}`, `positionCount={run.positionCount}`, `positions={run.positions}`

- [x] **Task 4: Write tests for BacktestPositionsTable** (AC: #7)
  - [x] 4.1 Create `pm-arbitrage-dashboard/src/components/backtest/BacktestPositionsTable.spec.tsx`
  - [x] 4.2 Tests:
    - `[P0]` renders DataTable with position data (all columns present)
    - `[P0]` displays realized P&L with green/red color coding
    - `[P0]` renders pagination when positionCount > 100
    - `[P1]` displays exit reason badges
    - `[P1]` formats timestamps, prices, and monetary values correctly
    - `[P1]` shows "—" for null exit fields (open positions at simulation end)
    - `[P1]` shows loading state when `isLoading=true`
    - `[P1]` pagination click triggers `onPageChange` callback
    - `[P2]` empty state when no positions

- [x] **Task 5: Update BacktestDetailPage tests for positions integration** (AC: #7)
  - [x] 5.1 Update `BacktestDetailPage.spec.tsx` to add mock positions data in `mockRun`
  - [x] 5.2 Add test: `[P0] should render BacktestPositionsTable on Positions tab` (click Positions tab, verify DataTable appears)
  - [x] 5.3 Verify all existing tests still pass after mock data field name changes

- [x] **Task 6: Run lint and verify** (AC: #7)
  - [x] 6.1 Run `cd pm-arbitrage-dashboard && pnpm lint`
  - [x] 6.2 Run `cd pm-arbitrage-dashboard && pnpm test`
  - [x] 6.3 Fix any failures

## Dev Notes

### Scope & Risk

**Frontend-only fix.** Zero backend changes. The API already returns all required data correctly:
- `CalibrationReport.summaryMetrics` uses `netPnl` (not `totalPnl`)
- `GET /backtesting/runs/:id` returns paginated `positions[]` with `positionCount`

**Root causes are definitively identified:**
1. SummaryMetricsPanel type assertion uses `totalPnl` but API sends `netPnl` — results in `undefined -> 0 -> $0.00`
2. Positions tab has placeholder text where DataTable should be

### Bug 1: Exact Changes Required

**File:** `pm-arbitrage-dashboard/src/components/backtest/SummaryMetricsPanel.tsx`

3 occurrences of `totalPnl` must become `netPnl`:
- **Line 25** (type assertion): `totalPnl?: string;` -> `netPnl?: string;`
- **Line 47** (value parse): `metrics.totalPnl` -> `metrics.netPnl`
- **Line 64** (display): `formatUsd(metrics.totalPnl)` -> `formatUsd(metrics.netPnl)`

### Bug 2: Positions Table Pattern

Follow `PositionsPage.tsx` column definition pattern. Key differences for backtest positions:
- **Simpler schema:** Backtest positions have flat fields (no nested objects like `entryPrices`, `currentPrices`)
- **All closed:** Every backtest position has `realizedPnl` (no unrealized P&L concept)
- **Exit reasons are enums:** `EDGE_EVAPORATION`, `TIME_DECAY`, `PROFIT_CAPTURE`, `RESOLUTION_FORCE_CLOSE`, `INSUFFICIENT_DEPTH`, `SIMULATION_END`
- **Client-side sorting:** Positions are loaded per-page from the API, sort within the page (API doesn't support position-level sort params — pagination is offset-based only)
- **Reuse `PnlCell`** from `src/components/cells/PnlCell.tsx` for realized P&L (never estimated for backtest positions)
- **Reuse `formatUsd`** from `src/lib/utils.ts` for monetary values
- **Reuse `formatDecimal`** from `src/lib/utils.ts` for edge values

### Backtest Position API Shape

Positions come embedded in the run response from `useBacktestRun`:
```typescript
// From GET /backtesting/runs/:id?positionLimit=100&positionOffset=0
run.positions: Array<{
  id: number;
  runId: string;
  pairId: string;
  kalshiContractId: string;
  polymarketContractId: string;
  kalshiSide: string;          // "YES" | "NO"
  polymarketSide: string;      // "YES" | "NO"
  entryTimestamp: string;       // ISO 8601
  exitTimestamp: string | null;
  kalshiEntryPrice: string;     // Decimal string
  polymarketEntryPrice: string;
  kalshiExitPrice: string | null;
  polymarketExitPrice: string | null;
  positionSizeUsd: string;      // Decimal string
  entryEdge: string;            // Decimal string
  exitEdge: string | null;
  realizedPnl: string | null;   // Decimal string
  fees: string | null;          // Decimal string
  exitReason: string | null;    // BacktestExitReason enum
  holdingHours: string | null;  // Decimal string
  createdAt: string;            // ISO 8601
}>
run.positionCount: number;      // Total count for pagination
```

### useBacktestRun Pagination Modification

Current hook (line 52-59 of `src/hooks/useBacktest.ts`):
```typescript
export function useBacktestRun(id: string) {
  return useQuery({
    queryKey: ['backtesting', 'run', id],
    queryFn: () => api.backtestControllerGetRun(id, { positionLimit: 100, positionOffset: 0 }),
    // ...
  });
}
```

Change to accept an options object:
```typescript
export function useBacktestRun(id: string, options?: { positionLimit?: number; positionOffset?: number }) {
  const { positionLimit = 100, positionOffset = 0 } = options ?? {};
  return useQuery({
    queryKey: ['backtesting', 'run', id, positionLimit, positionOffset],
    queryFn: () => api.backtestControllerGetRun(id, { positionLimit, positionOffset }),
    // ...
  });
}
```

**Important:** Adding pagination params to `queryKey` ensures each page is cached independently. Existing callers pass no options and get defaults, so no breaking changes. Only `BacktestDetailPage.tsx` imports this hook — verify with a search before modifying.

**Cache invalidation safety:** TanStack Query's `invalidateQueries({ queryKey: ['backtesting', 'run', runId] })` uses prefix matching — it will match `['backtesting', 'run', runId, 100, 0]`, `['backtesting', 'run', runId, 100, 100]`, etc. The WebSocket handlers in `WebSocketProvider.tsx` that invalidate on `backtesting.run.completed` / `backtesting.run.failed` will continue to work correctly.

### Test Mock Data Update

Both test files use `totalPnl` in mock report data that must become `netPnl`:
- `SummaryMetricsPanel.spec.tsx` line 7: `totalPnl: '1234.56'` -> `netPnl: '1234.56'`
- `BacktestDetailPage.spec.tsx` line 28: `totalPnl: '1234.56'` -> `netPnl: '1234.56'`

### Existing Test Patterns to Follow

- **Vitest + React Testing Library** (not Jest)
- **Mock hooks with `vi.mock()`** for dependencies (see `BacktestDetailPage.spec.tsx` lines 9-13)
- **Test IDs for assertions:** `data-testid="summary-metrics-panel"`, `data-testid="backtest-detail-header"`, etc.
- **Priority tags:** `[P0]` critical, `[P1]` important, `[P2]` nice-to-have
- **JSX via `React.createElement`** (existing convention in these test files — not required but follow for consistency)
- **MemoryRouter + Routes** for page-level tests

### Exit Reason Badge Mapping

Use `Badge` component from `@/components/ui/badge`:

| Exit Reason | Label | Variant |
|---|---|---|
| `EDGE_EVAPORATION` | Edge Evap | `secondary` |
| `TIME_DECAY` | Time Decay | `secondary` |
| `PROFIT_CAPTURE` | Profit Capture | `default` (green-ish) |
| `RESOLUTION_FORCE_CLOSE` | Resolution | `outline` |
| `INSUFFICIENT_DEPTH` | Insuf. Depth | `destructive` |
| `SIMULATION_END` | Sim End | `outline` |

**Authoritative source:** `pm-arbitrage-engine/prisma/schema.prisma` — `enum BacktestExitReason`. If any unmapped value is encountered at runtime, render a fallback `outline` badge with the raw value.

### Project Structure Notes

All changes in `pm-arbitrage-dashboard/` (separate git repo — commit separately from engine):

```
src/components/backtest/
  SummaryMetricsPanel.tsx         # MODIFY — fix netPnl field name (3 lines)
  SummaryMetricsPanel.spec.tsx    # MODIFY — update mock data, add negative P&L test
  BacktestPositionsTable.tsx      # NEW — DataTable with position columns
  BacktestPositionsTable.spec.tsx # NEW — unit tests
src/pages/
  BacktestDetailPage.tsx          # MODIFY — replace placeholder with BacktestPositionsTable
  BacktestDetailPage.spec.tsx     # MODIFY — update mock data, add positions tab test
src/hooks/
  useBacktest.ts                  # MODIFY — add pagination params to useBacktestRun
```

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-02-backtest-dashboard-bugs.md — Full bug analysis with evidence]
- [Source: _bmad-output/implementation-artifacts/10-9-5-backtest-dashboard-page.md — Original dashboard story, all patterns and conventions]
- [Source: pm-arbitrage-dashboard/src/components/backtest/SummaryMetricsPanel.tsx — Bug 1 location (totalPnl field)]
- [Source: pm-arbitrage-dashboard/src/pages/BacktestDetailPage.tsx — Bug 2 location (placeholder at lines 138-144)]
- [Source: pm-arbitrage-dashboard/src/pages/PositionsPage.tsx — Reference pattern for DataTable + column definitions]
- [Source: pm-arbitrage-dashboard/src/components/DataTable.tsx — DataTable props API]
- [Source: pm-arbitrage-dashboard/src/components/cells/PnlCell.tsx — Reusable P&L cell component]
- [Source: pm-arbitrage-dashboard/src/hooks/useBacktest.ts — useBacktestRun hook to modify for pagination]
- [Source: pm-arbitrage-dashboard/src/lib/utils.ts — formatUsd, formatDecimal utilities]
- [Source: pm-arbitrage-engine/src/modules/backtesting/types/calibration-report.types.ts — SummaryMetrics.netPnl (authoritative field name)]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None.

### Completion Notes List

- Bug 1 (P&L $0): Renamed `totalPnl` → `netPnl` in 3 locations in SummaryMetricsPanel.tsx. Root cause confirmed: type assertion used wrong field name, causing `undefined → 0 → $0.00`.
- Bug 2 (Positions placeholder): Created BacktestPositionsTable component with 13 columns, exit reason badge mapping (6 reasons + fallback), PnlCell color coding, client-side sorting via DataTable.
- `useBacktestRun` modified to accept `{ positionLimit, positionOffset }` options with cache-isolated queryKey per page.
- Exported `BACKTEST_POSITIONS_PAGE_SIZE` constant shared between BacktestPositionsTable and BacktestDetailPage to prevent drift.
- Added `isFetching` prop pass-through for pagination loading indicator (review fix).
- Added render-time position page reset on `id` change using React "previous value" state pattern (lint-compliant, no useEffect/useRef during render).
- Code review completed (Lad MCP, 2 reviewers): 12 findings total. Fixed 3 actionable (isFetching loading, page reset on run switch, shared PAGE_SIZE constant). Rejected 9 pre-existing/out-of-scope (PnlCell format inconsistency, useEffect deps, error handling, win rate falsy, color inconsistency — all pre-existing code not in story scope).
- 3-layer adversarial code review (Blind Hunter + Edge Case Hunter + Acceptance Auditor): 11 raw findings triaged to 1 intent-gap + 0 bad-spec + 4 patch + 2 defer + 4 reject. All 5 actionable items fixed: IG-1 chunk progress refactored (reactive useQuery subscription replacing non-reactive getQueryData, split useEffect into timer + cache cleanup, derived showChunkFallback state replacing setState-in-effect, totalChunks>0 guard, chunk progress test added — also fixed pre-existing set-state-in-effect lint error), P-1 null fees guard (formatUsd→'—'), P-2 all 5 display columns converted to accessor columns for AC#6 sorting + sorting test, P-3 keepPreviousData added to useBacktestRun (prevents page-change loading flash), P-4 already covered by existing test. 2 deferred (pre-existing): PnlCell $-12.30 vs formatUsd -$12.30 format, PnlCell emerald-600 vs SummaryMetricsPanel green-600 color. 152 dashboard tests pass.

### File List

**Modified:**
- `pm-arbitrage-dashboard/src/components/backtest/SummaryMetricsPanel.tsx` — `totalPnl` → `netPnl` (3 occurrences)
- `pm-arbitrage-dashboard/src/components/backtest/SummaryMetricsPanel.spec.tsx` — mock data field rename + new negative P&L test
- `pm-arbitrage-dashboard/src/pages/BacktestDetailPage.tsx` — replaced positions placeholder with BacktestPositionsTable, pagination state, isFetching, page reset
- `pm-arbitrage-dashboard/src/pages/BacktestDetailPage.spec.tsx` — mock positions data, positions tab test, field name fix
- `pm-arbitrage-dashboard/src/hooks/useBacktest.ts` — `useBacktestRun` accepts pagination options

**Created:**
- `pm-arbitrage-dashboard/src/components/backtest/BacktestPositionsTable.tsx` — DataTable with 13 columns, exit reason badges, pagination
- `pm-arbitrage-dashboard/src/components/backtest/BacktestPositionsTable.spec.tsx` — 10 tests (3 P0, 5 P1, 1 P2 + 1 P0 negative P&L in SummaryMetricsPanel)
