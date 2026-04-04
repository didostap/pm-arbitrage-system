# Story 10-95.6: Replace Simulation-End Force-Close with Open Position Reporting

Status: done

## Story

As an operator,
I want backtests to leave open positions unclosed at simulation end and instead report blocked capital separately,
so that backtest statistics accurately reflect realized trading performance without artificial losses from force-closed positions.

## Context

`closeRemainingPositions()` (backtest-engine.service.ts:615-636) force-closes all open positions at simulation end with `exitReason: 'SIMULATION_END'` and `exitEdge: 0`, inflating loss count and depressing total P&L, profit factor, win rate, and Sharpe ratio. In live trading these positions would remain open. The fix: skip force-close, persist open positions with null exit fields + calculated `unrealizedPnl`, and add aggregate blocked capital metrics to `BacktestRun`.

**Why metrics are automatically correct after removal:** The portfolio service accumulators (`totalPositions`, `winCount`, `lossCount`, `totalPnl`, etc.) are incremented inside `closePosition()` (backtest-portfolio.service.ts:217-232). By removing the `closeRemainingPositions()` call, accumulators naturally reflect only naturally closed positions. No accumulator reset or filtering needed.

**Walk-forward sub-runs:** Walk-forward headless runs have their own portfolios for bounded train/test windows. Force-close in sub-runs is a design decision outside this story's scope — the main run's metrics and positions are the focus. Walk-forward sub-run behavior should remain unchanged for now.

## Acceptance Criteria

1. **Given** a backtest completes with N open positions remaining
   **When** the simulation ends
   **Then** those positions are **not** closed (no `closeRemainingPositions` call)

2. **Given** open positions exist at simulation end
   **When** results are persisted
   **Then** each open position is stored with null exit fields (`exitTimestamp`, `kalshiExitPrice`, `polymarketExitPrice`, `exitEdge`, `realizedPnl`, `fees`, `exitReason`, `holdingHours`) + calculated `unrealizedPnl`
   **And** `BacktestRun` stores `openPositionCount`, `blockedCapitalUsd`, `unrealizedPnlUsd`

3. **Given** aggregate metrics are calculated
   **When** open positions exist
   **Then** `totalPositions`, `winCount`, `lossCount`, `totalPnl`, `profitFactor`, `sharpeRatio`, `avgHoldingHours` reflect **only** naturally closed positions
   **And** `capitalUtilization` correctly reflects capital still deployed at simulation end

4. **Given** the backtest detail page
   **When** the run has open positions
   **Then** a "Blocked Capital" section shows: open position count, total capital blocked, estimated unrealized P&L, percentage of initial capital blocked
   **And** the Positions tab distinguishes open vs closed positions visually

## Tasks / Subtasks

- [x] Task 0: Baseline verification (AC: all)
  - [x] 0.1 `cd pm-arbitrage-engine && pnpm test` — confirm green baseline, record test count (3671 expected)
  - [x] 0.2 `pnpm lint` — confirm baseline

- [x] Task 1: Prisma migration — new fields (AC: #2)
  - [x] 1.1 Add `unrealizedPnl Decimal(20,10)?` to `BacktestPosition` model in `prisma/schema.prisma` (after `realizedPnl` field, line ~698). Map: `@map("unrealized_pnl")`
  - [x] 1.2 Add three fields to `BacktestRun` model (after `capitalUtilization`, line ~675):
    - `openPositionCount Int? @map("open_position_count")`
    - `blockedCapitalUsd Decimal(20,6)? @map("blocked_capital_usd") @db.Decimal(20, 6)`
    - `unrealizedPnlUsd Decimal(20,10)? @map("unrealized_pnl_usd") @db.Decimal(20, 10)`
  - [x] 1.3 Run `pnpm prisma migrate dev --name add-open-position-reporting-fields`
  - [x] 1.4 Run `pnpm prisma generate` and verify TS compilation

- [x] Task 2: Add unrealized PnL calculation utility (AC: #2)
  - [x] 2.1 Add `unrealizedPnl?: Decimal` optional field to `SimulatedPosition` interface in `src/modules/backtesting/types/simulation.types.ts` (after `realizedPnl`, line ~19)
  - [x] 2.2 Create `calculateUnrealizedPnl()` function in `backtest-portfolio.service.ts` (or a nearby utils file if portfolio service is near line limits). Signature: `(position: SimulatedPosition, lastKalshiPrice: Decimal, lastPolymarketPrice: Decimal) => Decimal`. Logic must mirror the realized PnL calculation in `closePosition()` (lines 195-215) but without modifying the position. Use `decimal.js` for all math.
  - [x] 2.3 Write unit tests for `calculateUnrealizedPnl()`: (a) long Kalshi / short Polymarket with profit, (b) loss scenario, (c) uses last available prices correctly, (d) matches `closePosition()` P&L calculation for equivalent inputs

- [x] Task 3: Remove force-close, calculate unrealized PnL for open positions (AC: #1, #2, #3)
  - [x] 3.1 In `backtest-engine.service.ts`, remove the `closeRemainingPositions(runId, lastTimeSteps)` call at line ~316. Do NOT delete the method yet (walk-forward sub-runs at line ~332 may still use it — see Dev Notes).
  - [x] 3.2 After the chunk loop (where `closeRemainingPositions` was), add logic to calculate unrealized PnL for each open position:
    - Get open positions from `portfolioService.getState(runId).openPositions`
    - For each position, find last available prices from `lastTimeSteps` (same pattern as `closeRemainingPositions` used: `lastStep?.pairs.find(p => p.pairId === position.pairId)`)
    - Call `calculateUnrealizedPnl(position, lastKalshiPrice, lastPolymarketPrice)`
    - Set `position.unrealizedPnl = calculated value`
  - [x] 3.3 Update tests in `backtest-engine.service.spec.ts`:
    - Remove/update tests that verify `closeRemainingPositions` is called on main run
    - Add test: when simulation ends with open positions, they remain open (portfolioService.closePosition NOT called for them)
    - Add test: unrealizedPnl is calculated for each open position using last available prices
    - Add test: aggregate metrics (`getAggregateMetrics`) only reflect naturally closed positions
    - Add test: when no price data for a pair in lastTimeSteps, unrealizedPnl = Decimal(0)
    - Add test: walk-forward callback still passes `closeRemainingPositions` to `finalizeResults`
    - Add test: all positions remain open (no natural exits) — metrics all zero, openPositionCount = N

- [x] Task 4: Persist open positions and blocked capital metrics (AC: #2, #3)
  - [x] 4.1 In `backtest-persistence.helper.ts`, modify `persistBacktestResults()`:
    - After getting `aggregateMetrics`, also get open positions: `portfolioService.getState(runId).openPositions`
    - Calculate aggregates: `openPositionCount = openPositions.size`, `blockedCapitalUsd = sum of positionSizeUsd`, `unrealizedPnlUsd = sum of unrealizedPnl`
    - Add these three fields to the `prisma.backtestRun.update()` call
  - [x] 4.2 Modify `batchWritePositions()` to handle open positions:
    - Open positions have `unrealizedPnl` set, exit fields null
    - Add `unrealizedPnl` to the field mapping: `unrealizedPnl: p.unrealizedPnl?.toFixed(10) ?? null`
    - Ensure null exit fields are handled correctly (already nullable in Prisma schema, but verify the mapping doesn't crash on null)
  - [x] 4.3 Write the open positions to DB: after flushing closed positions, call `batchWritePositions()` with the open positions (convert `openPositions` Map values to array)
  - [x] 4.4 Write tests:
    - Test: open positions are persisted with null exit fields + unrealizedPnl
    - Test: BacktestRun is updated with openPositionCount, blockedCapitalUsd, unrealizedPnlUsd
    - Test: blocked capital calculation is correct (sum of positionSizeUsd of open positions)
    - Test: run with zero open positions has `openPositionCount: 0`, `blockedCapitalUsd: 0`, `unrealizedPnlUsd: 0` (not null — 0 is meaningful)

- [x] Task 5: Update DTOs and event (AC: #2, #4)
  - [x] 5.1 In `backtest-result.dto.ts`, add to `BacktestRunResponseDto`:
    - `openPositionCount: number | null`
    - `blockedCapitalUsd: string | null`
    - `unrealizedPnlUsd: string | null`
  - [x] 5.2 In `backtest-result.dto.ts`, add to `BacktestPositionResponseDto`:
    - `unrealizedPnl: string | null`
  - [x] 5.3 In `backtesting.events.ts`, add to `BacktestRunCompletedEvent` metrics:
    - `openPositionCount`, `blockedCapitalUsd`, `unrealizedPnlUsd`
  - [x] 5.4 Update the controller's response mapping (`backtest.controller.ts`) to include new fields in serialization
  - [x] 5.5 Update `DashboardGateway` if it maps `BacktestRunCompletedEvent` fields explicitly

- [x] Task 6: Fix report generation to exclude open positions (AC: #3)
  - [x] 6.1 **CRITICAL FIX:** In `calibration-report.service.ts`, `buildSummaryMetrics()` (line ~224) sets `totalTrades = positions.length`. After this story, the DB contains both open AND closed positions. This will miscount. Fix: filter before counting: `const closedPositions = positions.filter(p => p.exitTimestamp != null); const totalTrades = closedPositions.length;` — use `closedPositions` for ALL metrics (winCount loop, edge capture, etc.)
  - [x] 6.2 **Prisma query filter:** In `generateReport()` (line ~55), the Prisma query loads ALL positions: `findMany({ where: { runId } })`. Either: (a) add filter `exitTimestamp: { not: null }` to load only closed positions, OR (b) load all and split into closed/open arrays for different uses. Option (b) is better if the report needs to include open position summary.
  - [x] 6.3 Add `openPositionCount`, `blockedCapitalUsd`, `unrealizedPnlUsd` to `SummaryMetrics` interface in `calibration-report.types.ts` (lines 27-35). Populate from the BacktestRun record fields (already persisted in Task 4).
  - [x] 6.4 The `toBootstrapPositions()` helper (line ~285) already filters `p.exitTimestamp != null` — verify this still works correctly
  - [x] 6.5 Write tests: (a) `summaryMetrics.totalTrades` equals count of closed positions only, (b) open positions are excluded from winRate/profitFactor/edge capture calculations, (c) report includes blocked capital fields

- [x] Task 7: Dashboard — Blocked Capital section (AC: #4)
  - [x] 7.1 Create `BlockedCapitalSection.tsx` in `pm-arbitrage-dashboard/src/components/backtest/`. Display:
    - Open Position Count
    - Total Capital Blocked (USD formatted)
    - Estimated Unrealized P&L (USD, colored green/red)
    - % of Initial Capital Blocked (calculate: `blockedCapitalUsd / config.bankroll * 100`)
  - [x] 7.2 Conditionally render in `BacktestDetailPage.tsx` Summary tab (after `SummaryMetricsPanel`, before `KnownLimitationsSection`) — only show when `openPositionCount != null && openPositionCount > 0` (handles both pre-migration null and zero cases)
  - [x] 7.3 Use existing UI primitives (`Card`, `CardHeader`, `CardContent` from shadcn/ui) consistent with `SummaryMetricsPanel`

- [x] Task 8: Dashboard — Position table open/closed distinction (AC: #4)
  - [x] 8.1 In `BacktestPositionsTable.tsx`, handle null `exitReason`:
    - Add to `EXIT_REASON_MAP`: handle null/undefined → `{ label: 'Open', variant: 'default' }` with a distinct visual (e.g., blue badge or similar)
    - For open positions: show "—" for exitTimestamp, exitEdge, holdingHours
    - For open positions: show `unrealizedPnl` in the P&L column instead of `realizedPnl` (with "Unrealized" label)
  - [x] 8.2 Update `BacktestPosition` interface in the component to include `unrealizedPnl: string | null`
  - [x] 8.3 Add sorting/grouping: open positions should appear at the top of the positions list (or provide a filter toggle). Implementation choice: sort by exitReason with nulls first.

- [x] Task 9: Regenerate API client (AC: #4)
  - [x] 9.1 Regenerate the swagger-typescript-api client in `pm-arbitrage-dashboard/` to pick up new DTO fields
  - [x] 9.2 Verify TypeScript compilation in the dashboard project

- [x] Task 10: Full verification (AC: all)
  - [x] 10.1 `cd pm-arbitrage-engine && pnpm test` — all tests pass, count >= baseline (3671)
  - [x] 10.2 `pnpm lint` — zero new errors
  - [x] 10.3 Verify backward compatibility: existing backtest positions with `SIMULATION_END` exitReason still display correctly in the dashboard
  - [x] 10.4 Verify the `SIMULATION_END` enum value remains in Prisma schema (do NOT remove — backward compat for historical data)

- [x] Task 11: Post-implementation review (AC: all)
  - [x] 11.1 Lad MCP `code_review` on all created/modified files with context: "Remove simulation-end force-close, persist open positions with unrealizedPnl, add blocked capital metrics to BacktestRun, dashboard blocked capital section"
  - [x] 11.2 Address genuine bugs, security issues, or AC violations
  - [x] 11.3 Re-run tests after any review-driven changes

## Dev Notes

### Core Design: Why Metrics Are Automatically Correct

The portfolio service accumulators (`totalPositions`, `winCount`, `lossCount`, `totalPnl`, `grossWin`, `grossLoss`) are incremented ONLY inside `closePosition()` (backtest-portfolio.service.ts:217-232). By removing the `closeRemainingPositions()` call, open positions never hit `closePosition()`, so accumulators naturally exclude them. No accumulator filtering needed.

However, verify that `buildSummaryMetrics()` in `calibration-report.service.ts` doesn't independently count from the positions array loaded from DB. If it does, it must filter to `WHERE exit_reason IS NOT NULL`.

### Unrealized PnL Calculation

Mirror the realized PnL logic in `closePosition()` (backtest-portfolio.service.ts:195-215). The formula per position:

```typescript
// For each leg, directional P&L:
// BUY side: (lastPrice - entryPrice) * quantity
// SELL side: (entryPrice - lastPrice) * quantity
// where quantity = positionSizeUsd / entryPrice (per leg allocation)
// Total unrealizedPnl = kalshiLegPnl + polymarketLegPnl
// NOTE: Do NOT subtract fees — open positions have not incurred exit fees yet.
// The fees field on SimulatedPosition is null for open positions (set only on close).
```

Use `decimal.js` for ALL math. Use the last available close prices from `lastTimeSteps` (same data source `closeRemainingPositions` used). If no price data available for a pair (e.g., `lastStep?.pairs.find()` returns undefined), use entry prices as fallback — unrealizedPnl = `Decimal(0)` (no paper gain/loss).

### Walk-Forward Sub-Runs

`closeRemainingPositions` is referenced at TWO locations:
1. **Line ~316** (main run) — REMOVE this direct call
2. **Line ~332** (walk-forward routing) — This is a **callback passed** to `walkForwardRouting.finalizeResults()`: `(closeRunId, steps) => this.closeRemainingPositions(closeRunId, steps)`. KEEP this callback — walk-forward sub-runs need it.

Walk-forward sub-runs use bounded train/test windows where force-close at window end is semantically different (window boundaries are artificial). Changing walk-forward behavior is out of scope. The dev should verify the walk-forward callback still works correctly and add a `// TODO: evaluate removing force-close for walk-forward sub-runs` comment. Add a test confirming walk-forward sub-runs still call `closeRemainingPositions` via the callback.

### Open Position Persistence Flow

After removing `closeRemainingPositions()`, the new flow at simulation end:

```
Chunk loop completes
  ↓
Calculate unrealizedPnl for each open position (using last time step prices)
  ↓
Push final capital snapshot (open positions still deployed — correct for utilization)
  ↓
Walk-forward finalization (if enabled, unchanged)
  ↓
persistBacktestResults():
  1. Get aggregateMetrics (accumulators — only closed positions)
  2. Get open positions from portfolio state
  3. Calculate: openPositionCount, blockedCapitalUsd, unrealizedPnlUsd
  4. Update BacktestRun record with all metrics
  5. Batch write remaining closed positions
  6. Batch write open positions (null exit fields, unrealizedPnl set)
  ↓
Generate calibration report (uses DB data — must filter open positions from trade count)
  ↓
Emit BacktestRunCompletedEvent (includes new blocked capital fields)
```

### Prisma Schema Backward Compatibility

- Keep `SIMULATION_END` in `BacktestExitReason` enum — historical data uses it
- All new fields on `BacktestRun` and `BacktestPosition` are nullable — backward compat with existing data
- Old backtest runs (pre-migration) will have null for new fields — dashboard should show "N/A" or hide the Blocked Capital section when `openPositionCount` is null

### Zero vs Null Semantics for New Fields

**Post-migration runs** (this story and later): Fields are ALWAYS set to 0+ values. `openPositionCount = 0`, `blockedCapitalUsd = 0.000000`, `unrealizedPnlUsd = 0.0000000000`. Use explicit `?? new Decimal(0)` / `?? 0` in the persistence code to guarantee this.

**Pre-migration historical runs**: Fields are `null` (migration adds nullable columns). Dashboard must handle both: `null` means pre-migration (hide section), `0` means no open positions (hide section), `> 0` means show Blocked Capital section.

**Dashboard condition**: `openPositionCount != null && openPositionCount > 0` (covers both null and zero cases).

### Dashboard Position Table: Open vs Closed

For open positions in `BacktestPositionsTable`:
- `exitReason` is null → show "Open" badge (distinct color, e.g., blue)
- `exitTimestamp`, `exitEdge`, `holdingHours` are null → show "—"
- P&L column: show `unrealizedPnl` with "(unrealized)" label, or use distinct color
- Keep `SIMULATION_END` in `EXIT_REASON_MAP` for backward compat with old runs
- Sort: open positions first (nulls-first on exitTimestamp) or add a filter toggle

### Capital Utilization Impact

Without force-close, the final capital snapshot correctly reflects deployed capital at simulation end. Previously, `closeRemainingPositions()` released all deployed capital back to available before the final snapshot, showing 0 deployed. Now the final snapshot shows actual deployed capital — a significant and more accurate change to the capital utilization curve. In live trading, that capital IS still deployed.

### Collection Cleanup

No new Maps/Sets introduced. Open positions are read from `portfolioService.getState(runId).openPositions` (existing Map) and converted to array for persistence. The existing Map cleanup via `portfolioService.reset(runId)` in the finally block handles lifecycle.

### File Size Monitoring

- `backtest-engine.service.ts`: Currently 636 lines (deferred from 10-95-5 review). This story REMOVES ~22 lines (`closeRemainingPositions` method) and adds ~15 lines (unrealized PnL loop). Net change minimal.
- `backtest-persistence.helper.ts`: Currently ~74 lines. Adding open position handling adds ~30 lines. Still well under limits.

### Previous Story Intelligence (10-95-5)

Key patterns to preserve:
- `SharedDepthCache` passes through the pipeline — not relevant to this story but don't break
- `depthCacheHitRate` and `depthQueriesExecuted` in chunk events — leave unchanged
- `BacktestDepthLoaderService` injected in `ChunkedDataLoadingService` — leave unchanged
- Walk-forward compatibility: `WalkForwardRoutingService` doesn't interact with open position reporting

### Project Structure Notes

**New files:**
- `pm-arbitrage-dashboard/src/components/backtest/BlockedCapitalSection.tsx` — Blocked capital display component
- `prisma/migrations/YYYYMMDDHHMMSS_add_open_position_reporting_fields/migration.sql` — Auto-generated

**Modified files (engine):**
- `prisma/schema.prisma` — New fields on BacktestRun + BacktestPosition
- `src/modules/backtesting/types/simulation.types.ts` — Add `unrealizedPnl` to SimulatedPosition
- `src/modules/backtesting/engine/backtest-engine.service.ts` — Remove force-close, add unrealized PnL calculation
- `src/modules/backtesting/engine/backtest-engine.service.spec.ts` — Updated tests
- `src/modules/backtesting/engine/backtest-persistence.helper.ts` — Persist open positions + blocked capital
- `src/modules/backtesting/engine/backtest-portfolio.service.ts` — Add `calculateUnrealizedPnl()` utility (if here, or in a utils file)
- `src/modules/backtesting/dto/backtest-result.dto.ts` — New fields on response DTOs
- `src/modules/backtesting/reporting/calibration-report.service.ts` — Filter open positions from metrics
- `src/modules/backtesting/types/calibration-report.types.ts` — New fields on SummaryMetrics
- `src/common/events/backtesting.events.ts` — New fields on BacktestRunCompletedEvent
- `src/modules/backtesting/controllers/backtest.controller.ts` — Serialize new fields
- `src/dashboard/dashboard.gateway.ts` — Forward new event fields

**Modified files (dashboard):**
- `pm-arbitrage-dashboard/src/components/backtest/BacktestPositionsTable.tsx` — Open/closed distinction
- `pm-arbitrage-dashboard/src/pages/BacktestDetailPage.tsx` — Add BlockedCapitalSection
- `pm-arbitrage-dashboard/src/components/backtest/SummaryMetricsPanel.tsx` — May need open position count addition to summary

### References

- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.ts:615-636`] — `closeRemainingPositions()` to remove
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.ts:315-316`] — Main run force-close call site
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.ts:332`] — Walk-forward force-close callback passed to `finalizeResults` (keep)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-persistence.helper.ts:9-38`] — `persistBacktestResults()` to modify
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-persistence.helper.ts:43-74`] — `batchWritePositions()` to extend
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-portfolio.service.ts:162-250`] — `closePosition()` P&L calculation to mirror for unrealized PnL
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-portfolio.service.ts:307-344`] — `getAggregateMetrics()` (accumulators only — automatically correct)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/reporting/calibration-report.service.ts:217-279`] — `buildSummaryMetrics()` to verify/fix
- [Source: `pm-arbitrage-engine/src/modules/backtesting/types/simulation.types.ts:4-24`] — SimulatedPosition type to extend
- [Source: `pm-arbitrage-engine/src/modules/backtesting/types/calibration-report.types.ts:27-35`] — SummaryMetrics interface to extend
- [Source: `pm-arbitrage-engine/src/modules/backtesting/dto/backtest-result.dto.ts`] — Response DTOs to extend
- [Source: `pm-arbitrage-engine/src/common/events/backtesting.events.ts:96-109`] — BacktestRunCompletedEvent to extend
- [Source: `pm-arbitrage-engine/prisma/schema.prisma:651-709`] — BacktestRun + BacktestPosition models
- [Source: `pm-arbitrage-dashboard/src/pages/BacktestDetailPage.tsx`] — Detail page to add Blocked Capital section
- [Source: `pm-arbitrage-dashboard/src/components/backtest/BacktestPositionsTable.tsx:39-46`] — EXIT_REASON_MAP to extend
- [Source: `pm-arbitrage-dashboard/src/components/backtest/SummaryMetricsPanel.tsx`] — Summary panel (reference for UI patterns)
- [Source: `_bmad-output/implementation-artifacts/10-95-5-backtest-performance-optimization.md`] — Previous story patterns to preserve
- [Source: `_bmad-output/planning-artifacts/epics.md:3492-3520`] — Epic story definition

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Removed `closeRemainingPositions()` call on main run; walk-forward callback preserved
- Added `calculateUnrealizedPnl()` as standalone exported function mirroring `closePosition()` P&L logic
- Added `calculateOpenPositionUnrealizedPnl()` private method to engine service — sets `unrealizedPnl` on each open position using last available prices (falls back to entry prices if no data)
- Prisma migration adds 4 nullable fields (3 on BacktestRun, 1 on BacktestPosition) — backward compat with historical data
- Persistence helper now writes open positions to DB and calculates blocked capital aggregates
- Calibration report filters to closed positions for all trade metrics; includes blocked capital fields from BacktestRun
- Dashboard BlockedCapitalSection: conditionally rendered when `openPositionCount > 0`
- Positions table: blue "Open" badge, unrealized PnL display, nulls-first sort order
- Code review fix: explicitly set `unrealizedPnl: null` in `closePosition()` to prevent stale values
- API client regeneration deferred (requires running server); response types use manual interfaces
- Unit baseline: 3631 → 3648 (+17 tests). All green. Lint delta: +3 (spec file `unsafe-*` suppressions)

### Change Log

- 2026-04-07: Story 10-95-6 implemented. Removed simulation-end force-close, added open position reporting with unrealized PnL, blocked capital metrics, dashboard section. Code review: 15 findings triaged to 1 patch (explicit `unrealizedPnl: null` on close), 14 rejected (intentional design, pre-existing, false positive).

### File List

**Engine (pm-arbitrage-engine/):**
- `prisma/schema.prisma` — Added `unrealizedPnl` to BacktestPosition, `openPositionCount`/`blockedCapitalUsd`/`unrealizedPnlUsd` to BacktestRun
- `prisma/migrations/20260406235723_add_open_position_reporting_fields/migration.sql` — Auto-generated migration
- `src/modules/backtesting/types/simulation.types.ts` — Added `unrealizedPnl` to SimulatedPosition + createSimulatedPosition
- `src/modules/backtesting/engine/backtest-portfolio.service.ts` — Added `calculateUnrealizedPnl()` function, explicit `unrealizedPnl: null` in closePosition
- `src/modules/backtesting/engine/backtest-portfolio.service.spec.ts` — Added 4 tests for calculateUnrealizedPnl
- `src/modules/backtesting/engine/backtest-engine.service.ts` — Removed main-run closeRemainingPositions call, added calculateOpenPositionUnrealizedPnl method, updated event emission with blocked capital fields
- `src/modules/backtesting/engine/backtest-engine.service.spec.ts` — Replaced force-close test with 6 new tests for open position behavior
- `src/modules/backtesting/engine/backtest-persistence.helper.ts` — Added open position persistence, blocked capital aggregate calculation, unrealizedPnl field mapping
- `src/modules/backtesting/engine/backtest-persistence.helper.spec.ts` — NEW: 6 tests for persistence helper
- `src/modules/backtesting/dto/backtest-result.dto.ts` — Added new fields to BacktestRunResponseDto and BacktestPositionResponseDto
- `src/modules/backtesting/types/calibration-report.types.ts` — Added openPositionCount/blockedCapitalUsd/unrealizedPnlUsd to SummaryMetrics
- `src/modules/backtesting/reporting/calibration-report.service.ts` — Filter to closed positions for metrics, add blocked capital fields to report
- `src/modules/backtesting/reporting/calibration-report.service.spec.ts` — Added 3 tests for open position exclusion
- `src/modules/backtesting/controllers/backtest.controller.ts` — Updated position sort: nulls-first on exitReason

**Dashboard (pm-arbitrage-dashboard/):**
- `src/components/backtest/BlockedCapitalSection.tsx` — NEW: Blocked capital display component
- `src/components/backtest/BacktestPositionsTable.tsx` — Added unrealizedPnl to interface, blue "Open" badge, unrealized PnL in P&L column
- `src/pages/BacktestDetailPage.tsx` — Integrated BlockedCapitalSection conditionally
