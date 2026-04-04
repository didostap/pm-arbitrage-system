# Sprint Change Proposal: Backtest Engine Quality — Performance, Statistics Accuracy & Position Detail View

**Date:** 2026-04-06
**Triggered by:** Post-TimescaleDB migration observation during Epic 10.95
**Scope Classification:** Moderate — 3 new stories in existing epic, Prisma schema changes, dashboard additions
**Status:** APPROVED (2026-04-06)

---

## Section 1: Issue Summary

### Problem Statement

Following the TimescaleDB migration (Epic 10.95), backtesting performance improved for short date ranges but remains unacceptably slow for monthly+ ranges. Additionally, two quality issues were identified: (1) the backtest engine force-closes all open positions at simulation end, distorting P&L statistics, and (2) the backtest positions table lacks a detail view that exists for live positions.

### Discovery Context

Observed during production use of the backtesting system after Epic 10.95 stories 10-95-1 and 10-95-2 completed (TimescaleDB hypertable conversion). The TimescaleDB chunk exclusion improved short-range queries, but the engine's data loading and caching architecture remains the bottleneck for longer ranges. The statistics distortion and missing detail view were identified during backtest result analysis.

### Evidence Summary

**Performance:**
- `backtest-data-loader.service.ts` loads depths per-chunk (30 separate cycles for a monthly backtest)
- LRU cache: 2,000 entries. Monthly backtest with 50 pairs x 2 platforms x 44K minute-steps = ~4.4M unique keys — cache hit rate collapses
- Lazy fallback triggers N+1 `prisma.historicalDepth.findFirst()` per cache miss
- Sequential per-position depth lookups in `evaluateExits()` and `detectOpportunities()` (engine lines 651-674)

**Statistics Distortion:**
- `backtest-engine.service.ts:854-875` — `closeRemainingPositions()` force-closes all open positions at last market price with `exitReason: 'SIMULATION_END'` and `exitEdge: 0`
- Closed positions with negative P&L inflate loss count and depress total P&L, profit factor, win rate, and Sharpe ratio
- In live trading, these positions would remain open — their P&L is unrealized

**Missing Detail View:**
- `BacktestPositionsTable.tsx` shows 13 columns inline with no click handler
- Live positions have `PositionDetailPage.tsx` (613 lines) at `/positions/:id` with 8 comprehensive sections
- No equivalent exists for backtest positions

---

## Section 2: Impact Analysis

### Checklist Results

| # | Item | Status |
|---|------|--------|
| 1.1 | Triggering story identified | [x] Done — Post-Epic 10.95 TimescaleDB migration |
| 1.2 | Core problem defined | [x] Done — 3 issues: performance, statistics accuracy, missing UI |
| 1.3 | Evidence gathered | [x] Done — Code-level investigation with file paths and line numbers |
| 2.1 | Current epic (10.95) impact | [x] Done — Stories slot after 10-95-4 |
| 2.2 | Epic-level changes needed | [x] Done — 3 new stories in Epic 10.95 |
| 2.3 | Remaining epics reviewed | [x] Done — Epic 11, 12 unaffected |
| 2.4 | New epics needed | [x] Done — No, fits within 10.95 |
| 2.5 | Epic ordering | [x] Done — No resequencing needed |
| 3.1 | PRD conflicts | [N/A] — MVP complete; Phase 1 improvements |
| 3.2 | Architecture conflicts | [N/A] — No pattern violations |
| 3.3 | UI/UX conflicts | [!] Action-needed — UX spec should document backtest position detail view |
| 3.4 | Other artifacts | [N/A] — No deployment/CI changes |
| 4.1 | Direct Adjustment viable | [x] Viable — Effort: Medium, Risk: Low |
| 4.2 | Rollback viable | [N/A] — No rollback needed |
| 4.3 | MVP Review needed | [N/A] — MVP complete |
| 4.4 | Recommended path | [x] Done — Direct Adjustment (3 new stories in 10.95) |

### Epic Impact

**Epic 10.95 (in-progress):** Add 3 stories after 10-95-4. Epic scope expands from "TimescaleDB Migration" to "TimescaleDB Migration & Backtesting Quality." No impact on stories 10-95-1 through 10-95-4.

**Epic 11 (backlog):** No changes needed. Benefits from improved backtest tooling.

**Epic 12 (backlog):** No changes needed.

### Artifact Changes Required

**Epics Document** (`_bmad-output/planning-artifacts/epics.md`):
- Add stories 10-95-5, 10-95-6, 10-95-7 under Epic 10.95
- Update Epic 10.95 description to include backtesting quality improvements

**Sprint Status** (`_bmad-output/implementation-artifacts/sprint-status.yaml`):
- Add 3 new story entries under `epic-10-95`
- Update summary statistics

**Prisma Schema** (`pm-arbitrage-engine/prisma/schema.prisma`):
- `BacktestRun`: Add `openPositionCount`, `blockedCapitalUsd`, `unrealizedPnlUsd` fields
- `BacktestPosition`: Add nullable `unrealizedPnl` field; make `exitReason` nullable

**UX Specification** (`_bmad-output/planning-artifacts/ux-design-specification.md`):
- Add backtest position detail view specification

---

## Section 3: Recommended Approach

### Selected: Direct Adjustment — 3 New Stories in Epic 10.95

**Rationale:**
- All three issues are well-scoped with clear implementation paths
- The codebase has proven patterns to follow (live `PositionDetailPage`, existing depth loading architecture, `decimal.js` conventions)
- Performance optimization stays within `backtest-data-loader.service.ts` and `backtest-engine.service.ts` — no cross-module changes
- Statistics fix is behavioral (remove force-close, add reporting) — no architectural change
- Detail view mirrors existing live position pattern — clear template, shared UI primitives
- No impact on in-flight work (10-95-3 in review, 10-95-4 in backlog)

**Effort:** Medium (3 stories, ~3-4 sessions)
**Risk:** Low (all changes are additive or behavioral; no infrastructure changes)
**Timeline Impact:** Adds 3 stories to Epic 10.95 after 10-95-4. Minimal delay to Epic 11 start.

**Trade-offs considered:**
- *Deferring to Epic 11:* Possible but illogical — these are backtesting infrastructure improvements that belong with the backtesting epic.
- *Performance only, defer others:* The statistics fix is critical for backtest validity — unreliable results undermine the entire calibration purpose. Deferring the detail view is possible but the effort is low and the value is immediate.

---

## Section 4: Detailed Change Proposals

### Story 10-95-5: Backtest Engine Performance Optimization for Extended Date Ranges

As an operator,
I want monthly+ backtests to complete in reasonable time (minutes, not tens of minutes),
So that I can run calibration sweeps over meaningful historical periods without waiting excessively.

**Context:** Post-TimescaleDB migration, short-range backtests (1-5 days) improved noticeably due to chunk exclusion and compressed reads. However, monthly ranges remain slow. Deep investigation identified three compounding bottlenecks in `backtest-data-loader.service.ts` and `backtest-engine.service.ts`:

1. **Per-chunk depth re-loading** (data-loader lines 112-196): Each 1-day chunk triggers a fresh eager cache build or lazy LRU setup. A 30-day backtest = 30 separate depth loading cycles, each with batch SQL queries across all contract IDs.
2. **LRU cache undersized** (data-loader line 200): 2,000 entries. A monthly backtest with 50 pairs x 2 platforms x 44K minute-steps = ~4.4M unique keys. Cache hit rate collapses, falling back to N+1 `findFirst()` per miss.
3. **Sequential per-position depth lookups** (engine lines 651-674): `evaluateExits()` and `detectOpportunities()` call `findNearestDepth()` per position per time step. Without cache hit, each triggers an individual `findFirst()` query.

**Acceptance Criteria:**

1. **Given** a 30-day backtest with 50+ active pairs
   **When** the backtest runs end-to-end
   **Then** total wall-clock time is at least 3x faster than current baseline (measure before/after with same dataset and config)

2. **Given** the depth data loader
   **When** loading depths for a chunk
   **Then** a single batch query fetches depths for all contracts in the chunk (no per-contract `findFirst()` fallback within a loaded chunk)
   **And** the batch query leverages TimescaleDB chunk exclusion via time-range predicates

3. **Given** the depth caching strategy
   **When** a backtest spans multiple chunks
   **Then** depth cache is shared across chunk boundaries using a sliding window or range-based pre-load (not rebuilt per chunk)
   **And** the cache size is dynamically bounded by available memory (configurable max, default 512MB RSS budget for depth cache)

4. **Given** a time step with N open positions
   **When** `evaluateExits()` needs depth data for those positions
   **Then** all N depth lookups are resolved from the pre-loaded cache (zero individual DB queries during simulation loop)
   **And** cache misses are logged at WARN level with contract ID and timestamp for debugging

5. **Given** the simulation loop processes time steps
   **When** depth data is needed for both detection and exit evaluation in the same step
   **Then** a single cache lookup serves both (no duplicate lookups for the same contract+timestamp)

6. **Given** existing backtest tests
   **When** the optimization is applied
   **Then** all existing tests pass without modification (simulation logic unchanged)
   **And** backtest results (positions, P&L, metrics) are identical to pre-optimization output for the same input data

7. **Given** the backtest engine emits progress events
   **When** a chunk completes
   **Then** the event includes `depthCacheHitRate` and `depthQueriesExecuted` for observability

**Tasks:**
1. Benchmark current 30-day backtest wall-clock time (baseline measurement)
2. Refactor `backtest-data-loader.service.ts`: Replace per-chunk eager/lazy dual cache with range-based pre-load — single batch query per chunk covering all contracts, results stored in a shared cross-chunk Map with TTL eviction
3. Eliminate `findFirst()` fallback path during simulation — all depth data must be pre-loaded before simulation loop begins for each chunk
4. Add batch depth query using TimescaleDB `time_bucket` or range scan with `ORDER BY timestamp DESC LIMIT 1` per contract (lateral join pattern already proven in `loadAlignedPricesForChunk`)
5. Add `depthCacheHitRate` to chunk progress events
6. Add WARN-level logging for any cache miss during simulation (indicates pre-load gap)
7. Re-benchmark 30-day backtest, verify >=3x improvement
8. Verify all existing backtest tests pass with identical results

**Technical Notes:**
- The aligned price loading (`loadAlignedPricesForChunk`, line 302) already uses efficient raw SQL with LATERAL join. Apply the same pattern to depth loading.
- TimescaleDB hypertables on `historical_depths` enable chunk exclusion — time-range predicates will skip irrelevant chunks automatically.
- The `MAX_DEPTH_RECORDS_PER_CHUNK` threshold (100K) that triggers lazy mode should be revisited — with TimescaleDB compression, decompression happens transparently and the bottleneck shifts from I/O to decompression CPU.
- Story 10-95-4 (engine decomposition) extracts `ChunkedDataLoadingService` — coordinate with that decomposition if both are in-flight.

---

### Story 10-95-6: Replace Simulation-End Force-Close with Open Position Reporting

As an operator,
I want backtests to leave open positions unclosed at simulation end and instead report blocked capital separately,
So that backtest statistics accurately reflect realized trading performance without artificial losses from force-closed positions.

**Context:** `backtest-engine.service.ts:854-875` — `closeRemainingPositions()` iterates all open positions at simulation end, closing them at last market price (or entry price fallback) with `exitReason: 'SIMULATION_END'` and `exitEdge: 0`. This inflates loss count and depresses total P&L, profit factor, win rate, and Sharpe ratio. In live trading, these positions would remain open — their P&L is unrealized and shouldn't be counted as realized losses.

**Acceptance Criteria:**

1. **Given** a backtest completes with N open positions remaining
   **When** the simulation ends
   **Then** those positions are **not** closed (no `closePosition()` call)
   **And** `closeRemainingPositions()` is removed or bypassed

2. **Given** open positions exist at simulation end
   **When** results are persisted
   **Then** each open position is stored in `BacktestPosition` with:
   - `exitTimestamp: NULL`
   - `exitReason: NULL`
   - `kalshiExitPrice: NULL`, `polymarketExitPrice: NULL`
   - `realizedPnl: NULL`
   - `holdingHours: NULL` (still open)
   **And** a new field `unrealizedPnl` is calculated using last available market prices (same lookup as current force-close uses)
   **And** a new field `blockedCapital` stores the `positionSizeUsd` sum

3. **Given** aggregate metrics are calculated (`getAggregateMetrics`)
   **When** open positions exist
   **Then** `totalPositions`, `winCount`, `lossCount`, `totalPnl`, `profitFactor`, `sharpeRatio`, and `avgHoldingHours` reflect **only naturally closed positions** (positions with a non-null `exitReason` that is NOT `SIMULATION_END`)
   **And** existing `SIMULATION_END` positions from prior runs are excluded from metrics if re-calculated

4. **Given** the `BacktestRun` model
   **When** results are persisted
   **Then** new fields are stored:
   - `openPositionCount: Int` — number of positions still open
   - `blockedCapitalUsd: Decimal` — total USD locked in open positions
   - `unrealizedPnlUsd: Decimal` — estimated unrealized P&L of open positions at last known prices

5. **Given** the backtest detail page in the dashboard
   **When** the run has open positions
   **Then** a **"Blocked Capital"** section is displayed in the Summary tab showing:
   - Number of open positions
   - Total capital blocked (USD)
   - Estimated unrealized P&L (with caveat label: "estimated at last available prices")
   - Percentage of initial capital blocked
   **And** the Positions tab distinguishes open vs closed positions (e.g., status badge or row styling)

6. **Given** the Positions tab table
   **When** a position has `exitTimestamp: NULL`
   **Then** it displays "Open" status badge (distinct from exit reason badges)
   **And** P&L column shows unrealized P&L with "unrealized" label
   **And** Exit columns show dash

7. **Given** existing backtest tests
   **When** this change is applied
   **Then** tests that assert on `SIMULATION_END` positions are updated to reflect the new behavior
   **And** new tests verify: (a) open positions are not closed, (b) aggregate metrics exclude open positions, (c) blocked capital fields are correctly calculated

**Tasks:**
1. Add `openPositionCount`, `blockedCapitalUsd`, `unrealizedPnlUsd` fields to `BacktestRun` Prisma model + migration
2. Add nullable `unrealizedPnl` field to `BacktestPosition` Prisma model + migration
3. Modify `backtest-engine.service.ts`: Replace `closeRemainingPositions()` with `captureOpenPositionState()` that calculates unrealized P&L and blocked capital without closing
4. Modify `backtest-portfolio.service.ts` `getAggregateMetrics()`: Exclude open positions from all aggregate calculations
5. Modify `persistResults()`: Write open positions to `BacktestPosition` with null exit fields + unrealized P&L, write blocked capital fields to `BacktestRun`
6. Backend: Update `GET /backtesting/runs/:id` response to include new fields
7. Dashboard: Add "Blocked Capital" section to backtest Summary tab
8. Dashboard: Add "Open" status badge and unrealized P&L display in Positions tab
9. Update existing tests, add new tests for open position handling

**Technical Notes:**
- Unrealized P&L calculation reuses the same price lookup logic currently in `closeRemainingPositions()` (last step's pair prices or entry price fallback). Extract this into a shared helper.
- Walk-forward mode: Train/test splits should independently track their own open positions. Verify `closeRemainingPositions` is called separately for train and test — both need this fix.
- The `BacktestPosition` table currently has `exitReason` as a non-null field — the migration must make it nullable.
- Financial math: All new calculations use `decimal.js` per project convention.

---

### Story 10-95-7: Backtest Position Detail View (Mirroring Live Position Detail)

As an operator,
I want to click on a backtest position row and see a detailed view of that position,
So that I can understand the rationale, P&L breakdown, and conditions for each individual backtest trade — the same way I can for live positions.

**Context:** The live trading dashboard has a comprehensive `PositionDetailPage` (`pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx`, 613 lines) at route `/positions/:id` with 8 sections: entry pricing, current state, exit info, auto-unwind, exit criteria, execution info, order history, and audit trail. The backtest positions table (`BacktestPositionsTable.tsx`) shows 13 columns inline with no click-through — all data is crammed into the table row. Operators need the same drill-down capability to analyze individual backtest trades.

**Acceptance Criteria:**

1. **Given** the backtest Positions tab
   **When** the operator clicks a position row
   **Then** a detail view opens for that position (either a slide-over sheet or a dedicated page at `/backtesting/runs/:runId/positions/:positionId`)

2. **Given** the backtest position detail view for a **closed** position
   **When** the view renders
   **Then** it displays the following sections (mirroring live where data is available):

   **Entry Section:**
   - Pair ID and contract IDs (Kalshi + Polymarket)
   - Kalshi/Polymarket entry prices
   - Position size (USD)
   - Entry edge
   - Entry timestamp

   **Exit Section:**
   - Exit reason (badge, same mapping as table: Edge Evap, Time Decay, Profit Capture, Resolution, Insuf. Depth)
   - Exit timestamp
   - Kalshi/Polymarket exit prices
   - Exit edge
   - Holding duration (hours)

   **P&L Breakdown:**
   - Kalshi leg P&L (calculated: side x (exit - entry) x size)
   - Polymarket leg P&L (calculated: side x (exit - entry) x size)
   - Fees
   - Net realized P&L (color-coded green/red)

   **Sides & Strategy:**
   - Kalshi side (Buy/Sell)
   - Polymarket side (Buy/Sell)
   - Implied strategy description (e.g., "Buy Kalshi YES @ 0.42, Sell Polymarket YES @ 0.58")

3. **Given** the backtest position detail view for an **open** position (from Story 10-95-6)
   **When** the view renders
   **Then** the Exit section shows "Position still open at simulation end"
   **And** P&L Breakdown shows unrealized P&L (with "unrealized" label)
   **And** blocked capital amount is displayed

4. **Given** the backtest position detail view
   **When** the position data loads
   **Then** a "Back to Run" navigation link returns to the backtest detail page at the Positions tab

5. **Given** the backend API
   **When** `GET /backtesting/runs/:runId/positions/:positionId` is called
   **Then** it returns the full `BacktestPosition` record for that run
   **And** returns 404 if position doesn't belong to the specified run

6. **Given** the detail view component
   **When** implemented
   **Then** it reuses existing UI primitives from the live `PositionDetailPage` where applicable (`DashboardPanel`, `Badge`, formatting utilities, color-coding logic)
   **And** sections not applicable to backtesting are omitted (Auto-Unwind, Exit Criteria proximity bars, Execution Info, Order History, Audit Trail — backtest positions don't have this data)

7. **Given** the positions table
   **When** rows are rendered
   **Then** each row has a visual click affordance (cursor pointer, hover highlight) indicating it's interactive

**Tasks:**
1. Backend: Add `GET /backtesting/runs/:runId/positions/:positionId` endpoint to `backtest.controller.ts`
2. Backend: Validate position belongs to run (prevent cross-run access)
3. Dashboard: Create `BacktestPositionDetailPage.tsx` (or `BacktestPositionSheet.tsx` if using slide-over pattern)
4. Dashboard: Add route `/backtesting/runs/:runId/positions/:positionId` to router
5. Dashboard: Implement Entry section (prices, size, edge, timestamp, sides)
6. Dashboard: Implement Exit section (reason, prices, edge, duration) — conditional on closed status
7. Dashboard: Implement P&L Breakdown section (per-leg calculation, fees, net)
8. Dashboard: Implement open position state (unrealized P&L, blocked capital) — conditional on open status
9. Dashboard: Add row click handler to `BacktestPositionsTable.tsx` with navigation
10. Dashboard: Add "Back to Run" navigation
11. Dashboard: Add hook `useBacktestPosition(runId, positionId)` in `useBacktest.ts`
12. Reuse existing UI primitives (`DashboardPanel`, `Badge`, `formatCurrency`, `formatPrice`, P&L color logic)

**Technical Notes:**
- The live `PositionDetailPage` is 613 lines covering 8 sections. The backtest version will be significantly smaller (~200-250 lines) since 5 of the 8 sections don't apply (no real-time data, no execution engine, no audit trail).
- Per-leg P&L can be calculated client-side from entry/exit prices and side — no backend calculation needed. Use `decimal.js` via the existing `Decimal` import in the dashboard.
- The generated API client (`swagger-typescript-api`) will need regeneration after adding the new endpoint.
- Consider a slide-over sheet (`Sheet` from shadcn/ui) instead of a full page — keeps the positions table visible for quick comparison. Either approach is acceptable; match whichever feels more natural with existing dashboard patterns.

---

## Section 5: Implementation Handoff

### Scope Classification: Moderate

This change requires backlog updates (3 new stories) and Prisma schema changes, but no strategic pivot or fundamental replan.

### Handoff Recipients

| Role | Responsibility |
|------|---------------|
| **Scrum Master (Bob)** | Update `sprint-status.yaml` with new stories 10-95-5, 10-95-6, 10-95-7. Update `epics.md`. |
| **Dev Agent** | Implement stories following TDD workflow. Coordinate 10-95-5 with 10-95-4 (engine decomposition) if both in-flight. |
| **Operator (Arbi)** | Provide baseline benchmark data for 10-95-5. Validate backtest statistics accuracy after 10-95-6. |

### Sequencing

```
Current: Epic 10.95 in-progress
  10-95-3: review (compression policies)
  10-95-4: backlog (engine decomposition)
    |
NEW -> 10-95-5: backlog (performance optimization) — can start after 10-95-4 or in parallel
NEW -> 10-95-6: backlog (open position reporting) — independent, can start anytime after 10-95-4
NEW -> 10-95-7: backlog (position detail view) — depends on 10-95-6 (open position UI)
    |
Epic 11: Platform Extensibility & Security Hardening
```

**Dependencies:**
- 10-95-5 benefits from 10-95-4 (decomposition creates `ChunkedDataLoadingService` — cleaner refactoring target)
- 10-95-7 depends on 10-95-6 (needs open position fields and UI patterns from blocked capital story)
- 10-95-5 and 10-95-6 are independent of each other

### Success Criteria

1. 30-day backtest runs at least 3x faster than pre-optimization baseline
2. Zero individual `findFirst()` depth queries during simulation loop
3. Backtest statistics reflect only naturally closed positions
4. Open positions reported with blocked capital and unrealized P&L
5. Backtest position detail view accessible via row click with entry/exit/P&L sections
6. All existing tests pass (no regressions)
7. New tests cover: depth cache behavior, open position handling, detail endpoint

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Depth pre-load memory pressure for large date ranges | Medium | Configurable RSS budget (default 512MB), sliding window eviction |
| Unrealized P&L estimates misleading if last prices are stale | Low | Caveat label in UI: "estimated at last available prices" |
| `exitReason` nullable migration on existing data | Low | Existing rows retain their values; only new open positions use NULL |
| Story 10-95-4 and 10-95-5 touching same files | Low | Sequence 10-95-4 first; 10-95-5 refactors the extracted service |

---

## Checklist Completion Summary

| Section | Status |
|---------|--------|
| 1. Trigger & Context | [x] Complete |
| 2. Epic Impact | [x] Complete |
| 3. Artifact Conflicts | [x] Complete — Prisma schema, UX spec need updates |
| 4. Path Forward | [x] Complete — Direct Adjustment selected |
| 5. Proposal Components | [x] Complete — 3 stories defined and approved |
| 6. Final Review | [x] Complete — Approved 2026-04-06 |
