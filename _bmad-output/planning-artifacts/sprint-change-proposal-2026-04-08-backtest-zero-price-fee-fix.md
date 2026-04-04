# Sprint Change Proposal: Backtest Zero-Price Data Filtering & Exit Fee Accounting

**Date:** 2026-04-08
**Triggered by:** Analysis of backtest run `fd98b78e-ee46-4cda-a8db-f6e65ac8bb1b` (Mar 1-5 2026, $10K bankroll)
**Scope Classification:** Minor — 1 new story in existing epic, no schema migrations, no architectural changes
**Status:** APPROVED (2026-04-08)

---

## Section 1: Issue Summary

### Problem Statement

Backtest run `fd98b78e` lost **$2,929.70 (-29.3% of bankroll)** due to two compounding data correctness failures in the backtest engine:

1. **Zero-price candle contamination:** The backtest data loader (`backtest-data-loader.service.ts:130-134`) joins Kalshi `historical_prices` rows without filtering `close = 0`. Kalshi's candlestick API returns all-zero OHLCV bars for minutes with no trading activity — these are not real prices. **95.2% of Kalshi rows** (668,386 / 701,856) in the test period are zeros. The engine treats them as real, computing phantom edges averaging **67.3%** (vs realistic 1-3%). Result: 164/174 positions entered with `kalshi_entry_price = 0`, all one-directional (SELL Kalshi / BUY Polymarket).

2. **Missing exit fee deduction:** `backtest-portfolio.service.ts:208` computes `realizedPnl = kalshiPnl.plus(polyPnl)` with no fee subtraction. Line 227 stores `fees: null`. Fee schedules exist (`fee-schedules.ts`), `FinancialMath.calculateTakerFeeRate()` is available, and the live pipeline's `position-close.service.ts:456-479` correctly deducts exit fees — the backtest engine never wired this in.

### Discovery Context

Observed after completing Epic 10.95 stories 10-95-1 through 10-95-7 (TimescaleDB migration + backtest quality improvements). The first production backtest run revealed catastrophic losses, triggering deep DB analysis of positions and historical price data.

### Evidence Summary

| Evidence | Detail |
|---|---|
| Zero-price rows | 668,386 / 701,856 Kalshi rows = 95.2% zeros in Mar 1-5 period |
| Zero-price contracts | 766 contracts with *only* zero prices; 1,116 mixed; 14 all-nonzero |
| Affected positions | 164/174 positions entered with `kalshi_entry_price = 0` |
| Direction bias | All 174 positions: SELL Kalshi / BUY Polymarket (phantom one-directional signal) |
| Avg entry edge | 67.3% (5%+ bucket: 138 positions, -$2,743.60 total PnL) |
| PROFIT_CAPTURE exits | 17 positions, -$2,332.50 total (avg -$137.21 — paradoxically the biggest losers) |
| Run metrics | Sharpe -20.27, profit factor 0.083, max drawdown 30.4% |
| Bootstrap CI | Sharpe 95% CI: [-25.76, -12.03] — systematic, not noise |
| Fee column | NULL for all 174 positions |

---

## Section 2: Impact Analysis

### Checklist Results

| # | Item | Status |
|---|------|--------|
| 1.1 | Triggering story identified | [x] Done — Post-Epic 10.95 backtest run analysis |
| 1.2 | Core problem defined | [x] Done — 2 issues: zero-price contamination + missing fee deduction |
| 1.3 | Evidence gathered | [x] Done — DB analysis, code investigation, web research on Kalshi API behavior |
| 2.1 | Current epic (10.95) impact | [x] Done — 1 new story slots after completed 10-95-7 |
| 2.2 | Epic-level changes needed | [x] Done — 1 new story in Epic 10.95 |
| 2.3 | Remaining epics reviewed | [x] Done — Epic 11, 12 unaffected |
| 2.4 | New epics needed | [x] Done — No, fits within 10.95 |
| 2.5 | Epic ordering | [x] Done — No resequencing; 10-95-8 is the only remaining story |
| 3.1 | PRD conflicts | [!] Action-needed — Minor addition: historical price validity rule in Price Normalization section |
| 3.2 | Architecture conflicts | [!] Action-needed — Addition: document data quality boundary filtering for backtest data loader |
| 3.3 | UI/UX conflicts | [!] Action-needed — Addition: data quality card in backtest Summary tab |
| 3.4 | Other artifacts | [N/A] — No schema migrations, no deployment changes |
| 4.1 | Direct Adjustment viable | [x] Viable — Effort: Low, Risk: Low |
| 4.2 | Rollback viable | [N/A] — Nothing to roll back (original gap, not regression) |
| 4.3 | MVP Review needed | [N/A] — MVP complete |
| 4.4 | Recommended path | [x] Done — Direct Adjustment (1 new story in 10.95) |

### Epic Impact

**Epic 10.95 (in-progress):** Add story 10-95-8 after completed 10-95-7. This is the only remaining story before the epic retrospective. Epic scope ("TimescaleDB Migration & Backtesting Quality") already covers this.

**Epic 11, 12 (backlog):** No changes needed.

### Artifact Changes Required

**PRD** (`prd.md`, Price Normalization section after line 1218):
- Add historical price validity rule: zero-price candles must be filtered before edge calculation in backtesting/calibration consumers.

**Architecture** (`architecture.md`, Backtesting module section):
- Document data quality boundary filtering pattern: zero-price exclusion in `loadAlignedPricesForChunk`, defense-in-depth TypeScript guard, data quality metrics in report.

**UX Specification** (`ux-design-specification.md`, Backtest Results page):
- Add "Data Quality" card specification for backtest Summary tab: exclusion counts, percentages, per-platform breakdown, warning banner.

**Epics** (`epics.md`, Epic 10.95):
- Add story 10-95-8 definition.

**Sprint Status** (`sprint-status.yaml`):
- Add `10-95-8-backtest-zero-price-fee-fix: backlog` entry under `epic-10-95`.
- Update backlog count.

---

## Section 3: Recommended Approach

### Selected: Direct Adjustment — 1 New Story in Epic 10.95

**Rationale:**
- **Low effort.** SQL filter is a one-line WHERE clause. Fee deduction is ~15 lines mirroring proven live code. Edge cap is a config guard. All infrastructure exists.
- **Low risk.** No schema migrations. No module boundary crossings. Additive logic only.
- **Zero momentum impact.** Stories 10-95-1 through 10-95-7 are all done. This is the only remaining work.
- **Backtesting is unusable without this.** Every result is contaminated by phantom edges. All other backtest improvements (performance, open position reporting, detail view) operate on garbage data until this ships.
- **Establishes a reusable pattern.** Data quality boundary filtering protects against future data source issues beyond the current Kalshi zero-price problem.

**Trade-offs considered:**
- *Splitting into two stories (data quality + fees):* Each undersized at ~3-4 tasks. Combined (~8 tasks) is right-sized and they share the "backtest result accuracy" concern.
- *Forward-filling zero-volume candles instead of filtering:* Deferred. Forward-fill is data enrichment, not correctness. Filter first, enrich later.
- *Adding entry fee deduction too:* Entry fees are already captured in `calculateNetEdge()` which subtracts buy/sell fee costs from gross edge. Only exit fees are missing from realized PnL.

---

## Section 4: Detailed Change Proposals

### Story 10-95-8: Backtest Zero-Price Filtering & Exit Fee Accounting

As an operator,
I want the backtest engine to reject zero-price historical candles and deduct realistic exit fees from realized P&L,
So that backtest results reflect actual tradeable opportunities and accurate profit/loss accounting.

**Context:** Backtest run `fd98b78e` (Mar 1-5, $10K bankroll) lost $2,929.70 due to two compounding data correctness failures:

1. **Zero-price candle contamination:** `backtest-data-loader.service.ts:130-134` joins Kalshi `historical_prices` rows without filtering `close = 0`. Kalshi's candlestick API returns all-zero OHLCV bars for minutes with no trading activity. 95.2% of Kalshi rows (668,386/701,856) in the test period are zeros. The engine treats these as real prices, computing phantom edges averaging 67.3% (vs realistic 1-3%). Result: 164/174 positions entered with `kalshi_entry_price = 0`, all one-directional (SELL Kalshi / BUY Polymarket).

2. **Missing fee deduction:** `backtest-portfolio.service.ts:208` computes `realizedPnl = kalshiPnl.plus(polyPnl)` with no fee subtraction. Line 227 stores `fees: null`. Fee schedules exist in `fee-schedules.ts` (Kalshi dynamic: `0.07 * P * (1-P)`; Polymarket flat 2%). `FinancialMath.calculateTakerFeeRate()` is available. The live pipeline's `position-close.service.ts:456-479` correctly deducts exit fees -- the backtest engine simply never wired this in.

**Acceptance Criteria:**

1. **Given** the data loader SQL query in `loadAlignedPricesForChunk`
   **When** Kalshi historical prices are joined
   **Then** rows where `k.close = 0` are excluded from the result set
   **And** rows where `p.close = 0` (Polymarket lateral join) are also excluded
   **And** the SQL comment `-- MODE-FILTERED` is not required (not a mode-sensitive table)

2. **Given** aligned price data passes the SQL filter
   **When** the TypeScript grouping loop processes rows (`backtest-data-loader.service.ts:152-163`)
   **Then** an additional guard rejects any row where `kalshiClose` or `polymarketClose` equals zero after `Decimal` conversion (defense-in-depth against future data source changes)
   **And** rejected rows are counted per chunk and included in chunk progress events

3. **Given** a backtest run over a date range with sparse Kalshi data
   **When** the run completes
   **Then** the backtest report's `dataQuality` section includes:
   - `zeroRowsExcluded`: total rows filtered by the zero-price clause
   - `zeroRowsExcludedPct`: percentage of potential rows excluded
   - `perPlatformExclusion`: `{ kalshi: number, polymarket: number }`

4. **Given** a position is closed in `backtest-portfolio.service.ts:closePosition()`
   **When** realized P&L is calculated (line 208)
   **Then** exit fees are computed for both legs using `FinancialMath.calculateTakerFeeRate()` with the platform's fee schedule from `fee-schedules.ts`:
   - `kalshiExitFee = exitPrice * positionSizeUsd * takerFeeRate(exitPrice)` using `DEFAULT_KALSHI_FEE_SCHEDULE`
   - `polyExitFee = exitPrice * positionSizeUsd * takerFeeRate(exitPrice)` using `DEFAULT_POLYMARKET_FEE_SCHEDULE`
   **And** `realizedPnl = kalshiPnl + polyPnl - kalshiExitFee - polyExitFee`
   **And** `fees = kalshiExitFee + polyExitFee` (stored on the position, replacing `null`)

5. **Given** the capital tracking in `closePosition()` (lines 232-238)
   **When** capital is released after position close
   **Then** `availableCapital` adjustment accounts for fees: `availableCapital += positionSizeUsd + realizedPnl` (realizedPnl already net of fees from AC 4)
   **And** `realizedPnl` state accumulator reflects fee-deducted PnL

6. **Given** a backtest entry edge exceeds a configurable maximum threshold
   **When** the detection logic evaluates the opportunity
   **Then** the opportunity is rejected as a phantom signal
   **And** the default maximum edge threshold is 15% (configurable via `BacktestConfig`)
   **And** rejection is logged at DEBUG level with pair ID, computed edge, and threshold

7. **Given** the backtest dashboard Summary tab
   **When** the run has data quality metrics
   **Then** a "Data Quality" card displays:
   - Total aligned rows loaded
   - Rows excluded by zero-price filter (count + percentage)
   - Per-platform breakdown
   - Warning banner if exclusion rate > 20% for either platform

8. **Given** existing backtest tests
   **When** these changes are applied
   **Then** all existing tests pass (update assertions where `fees: null` becomes a calculated value)
   **And** new tests verify: (a) zero-price rows excluded from SQL results, (b) TypeScript guard rejects zero after Decimal conversion, (c) exit fees calculated correctly for both platforms, (d) realizedPnl is net of fees, (e) edge cap rejects phantom opportunities, (f) data quality metrics populated

**Tasks:**

1. **SQL filter** -- Add `AND k.close > 0` to the Kalshi join in `loadAlignedPricesForChunk` (line 134). Add `AND hp.close > 0` to the Polymarket lateral subquery (line 140). Verify the SQL comment is `-- MODE-FILTERED` exempt.

2. **TypeScript defense-in-depth guard** -- After line 158 in the grouping loop, add: `if (kalshiClose.isZero() || polymarketClose.isZero()) { excludedCount++; continue; }`. Add `excludedCount` to chunk progress event payload.

3. **Exit fee calculation in closePosition()** -- After line 207 in `backtest-portfolio.service.ts`, compute exit fees using `FinancialMath.calculateTakerFeeRate()` with `DEFAULT_KALSHI_FEE_SCHEDULE` and `DEFAULT_POLYMARKET_FEE_SCHEDULE`. Subtract from `realizedPnl`. Store in `fees` field (line 227). Mirror the pattern from live `position-close.service.ts:456-479`.

4. **Edge cap guard** -- In the detection/opportunity evaluation path (where `calculateNetEdge` result is checked against `edgeThresholdPct`), add an upper-bound check: `if (netEdge.gt(maxEdgeThreshold)) reject`. Add `maxEdgeThresholdPct` to `BacktestConfig` with default `0.15`.

5. **Data quality metrics** -- Add `zeroRowsExcluded`, `zeroRowsExcludedPct`, `perPlatformExclusion` to the backtest report's `dataQuality` section. Accumulate counts across chunks in the engine.

6. **Dashboard data quality card** -- Add a "Data Quality" panel to the backtest Summary tab. Show exclusion counts, percentages, per-platform breakdown. Render warning banner if >20%.

7. **Update existing tests** -- Fix assertions in `backtest-portfolio.service.spec.ts` where `fees: null` expectations must become calculated values. Update any fixture-based tests that rely on zero-price entry data.

8. **New tests** -- (a) Data loader: verify zero-close rows excluded from SQL + TS guard. (b) Portfolio: verify fee calculation matches expected values for both fee schedules. (c) Portfolio: verify `realizedPnl` is leg PnL minus fees. (d) Engine: verify edge cap rejects opportunities above threshold. (e) Report: verify data quality metrics populated.

**Technical Notes:**
- The Kalshi dynamic fee formula `0.07 * P * (1-P)` is already implemented in `fee-schedules.ts:12-15` via `takerFeeForPrice`. For `P = 0` or `P = 1`, fee = 0 -- handles resolution-price exits gracefully.
- Entry fees are already accounted for in `calculateNetEdge()` (via `FinancialMath.calculateNetEdge` which subtracts buy/sell fee costs from gross edge). Only *exit* fees are missing from realized PnL.
- The `calculateUnrealizedPnl` function (line 20-37) should also eventually account for estimated exit fees, but that's a refinement -- keep this story focused on realized PnL correctness.
- Story 10-95-4 decomposed the engine into `ChunkedDataLoadingService` -- the data loader changes target that extracted service.

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

This is a focused data correctness fix within an existing epic. No schema migrations, no cross-module refactoring, no strategic pivot. Direct implementation by the dev agent.

### Handoff Recipients

| Role | Responsibility |
|---|---|
| **Scrum Master (Bob)** | Update `sprint-status.yaml` with story 10-95-8. Update `epics.md`. Apply PRD/Architecture/UX additions. |
| **Dev Agent** | Implement story 10-95-8 following TDD workflow. |
| **Operator (Arbi)** | Re-run backtest over same date range (Mar 1-5) after fix to validate results are now reasonable. |

### Sequencing

```
Epic 10.95 (in-progress):
  10-95-1 through 10-95-7: DONE
  |
  NEW -> 10-95-8: backlog (zero-price filtering + fee accounting)
  |
  epic-10-95-retrospective
  |
  Epic 11: Platform Extensibility & Security Hardening
```

No dependencies on other stories. No blocking relationships. This is the final story before the epic retro.

### Success Criteria

1. Zero positions entered with `kalshi_entry_price = 0` or `polymarket_entry_price = 0` on re-run
2. No entry edges above 15% (configurable cap)
3. All positions have non-null `fees` field with realistic fee values
4. `realizedPnl` reflects leg PnL minus exit fees
5. Data quality card visible in dashboard showing exclusion statistics
6. All existing tests pass, new tests cover all fix paths
7. Re-run of Mar 1-5 backtest produces plausible results (positive or mildly negative Sharpe, not -20)

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Filtering removes too much data, leaving insufficient coverage | Low | Data quality metrics report exclusion rate; operator sees coverage gaps |
| Edge cap of 15% may filter legitimate high-edge opportunities | Very Low | 15% is still 15x higher than typical edges (1-3%); configurable if needed |
| Fee calculation differs subtly from live pipeline | Low | Same `FinancialMath.calculateTakerFeeRate()` + same fee schedules used; tests verify |

---

## Checklist Completion Summary

| Section | Status |
|---------|--------|
| 1. Trigger & Context | [x] Complete |
| 2. Epic Impact | [x] Complete |
| 3. Artifact Conflicts | [x] Complete -- PRD, Architecture, UX need minor additions |
| 4. Path Forward | [x] Complete -- Direct Adjustment selected |
| 5. Proposal Components | [x] Complete -- 1 story defined |
| 6. Final Review | [x] Complete -- Approved 2026-04-08 |
