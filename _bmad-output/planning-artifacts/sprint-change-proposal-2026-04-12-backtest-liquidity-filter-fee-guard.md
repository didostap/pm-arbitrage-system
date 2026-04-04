# Sprint Change Proposal: Backtest Entry Liquidity Filter & Fee-Aware Profit Capture

**Date:** 2026-04-12
**Triggered by:** Deep analysis of backtest run `2d2f84ac-b62b-497b-a811-6f6170b4d8dc` (Mar 1 – Apr 30, $10K bankroll, post-10-95-12 validation)
**Scope Classification:** Moderate — 2 new stories in existing Epic 10.95, no Prisma migration, no architectural changes
**Status:** APPROVED (2026-04-12)

---

## Section 1: Issue Summary

### Problem Statement

Backtest run `2d2f84ac` is profitable (+$2,026, 56% win rate on 770 positions), but **$2,235 in avoidable losses** across three categories are suppressing returns. Two root causes identified: (A) liquidity asymmetry at entry time causing STOP_LOSS and diverged TIME_DECAY losses, (B) a bug in PROFIT_CAPTURE's P&L guard that ignores fees.

### Evidence Summary

| Issue | Exit Reason | Count | P&L Impact | Root Cause |
|-------|-------------|-------|------------|------------|
| Liquidity asymmetry | STOP_LOSS | 8 | -$736 | Stale/illiquid pricing on one platform |
| Liquidity asymmetry | TIME_DECAY (diverged) | 106 | -$1,338 | Same — enters, never converges, bleeds to time limit |
| Fee-blind P&L guard | PROFIT_CAPTURE (losers) | 81 | -$161 | Pre-fee P&L check passes, post-fee P&L is negative |
| **Total recoverable** | | **195** | **~$2,235** | |

### Discovery Context

Post-10-95-12 validation run. All prior fixes (10-95-8 through 10-95-12) confirmed working — PROFIT_CAPTURE winners average +$12.06/position, overall system is profitable. These are second-order quality issues emerging now that first-order bugs are resolved.

---

## Section 2: Impact Analysis

### Epic Impact

**Epic 10.95 (TimescaleDB Migration & Backtesting Quality)** — absorbs 2 additional stories. This is the 6th course correction in this epic (established pattern: 10-95-8 through 10-95-12 are all course corrections). Epic scope extends but remains focused on backtesting quality.

No impact on Epic 11 (Platform Extensibility) or subsequent epics.

### Story Impact

No existing stories require modification. Two new stories added:

- **10-95-13:** Backtest Entry Liquidity Filter & Stop-Loss Recalibration
- **10-95-14:** PROFIT_CAPTURE Fee-Aware P&L Guard

### Artifact Conflicts

- **PRD:** No conflict. FR-AD-02 (edge calculation) already aligned. Exit criteria in PRD don't specify fee handling in guards — the fix is additive.
- **Architecture:** No change. Both fixes are within `modules/backtesting/engine/` module boundary. No new dependencies or interfaces.
- **UI/UX:** No change. Purely engine-internal logic.

### Technical Impact

- **Files modified:** `exit-evaluator.service.ts`, `backtest-engine.service.ts` (or `backtest-portfolio.service.ts`), `backtest-config.dto.ts`
- **New config parameters:** `minEntryPricePct` (minimum price threshold), `maxEntryPriceGapPct` (maximum cross-platform price gap)
- **Schema:** No Prisma migration required
- **Calibration report:** Should accumulate liquidity-filtered entry counts for operator visibility

---

## Section 3: Recommended Approach

**Selected: Direct Adjustment (Option 1)**

Add 2 new stories within Epic 10.95, following the established course correction pattern.

**Rationale:**
- Proven pattern — 5 prior course corrections in this sprint all succeeded
- No architectural changes — confined to backtest engine module
- Low risk — additive filtering logic with configurable thresholds
- High value — estimated ~$2,235 recoverable P&L (roughly doubling profitability)
- Both fixes are independent and can be implemented in parallel

**Effort estimate:** Low-Medium (each story ~1 session)
**Risk level:** Low
**Timeline impact:** Minimal — no blocking dependencies

### TIME_DECAY Threshold Recommendation

The TIME_DECAY time limit (24h in this run) does **not** need to change. Here's why:

- **Converged** TIME_DECAY (161 positions): marginally profitable (+$119). These are legitimate trades that partially converged but ran out of time. The 24h limit is working correctly for them.
- **Diverged** TIME_DECAY (106 positions): -$1,338. But 58% of these (62 positions) have one platform completely flat — the **entry liquidity filter in Story 13 will prevent these entries entirely**.
- The remaining 44 "both-moved-but-diverged" positions are genuine market risk that the stop-loss recalibration (30% → 15%) will catch earlier.

**Net recommendation:** Don't adjust `exitTimeLimitHours`. Instead:
1. Entry filter (Story 13) eliminates 58%+ of diverged TIME_DECAY entries
2. Stop-loss recalibration from 0.30 → 0.15 catches remaining divergers faster (-$30 max loss vs current -$55)
3. Combined effect: TIME_DECAY losses should drop from -$1,338 to roughly -$200–300

---

## Section 4: Detailed Change Proposals

### Story 10-95-13: Backtest Entry Liquidity Filter & Stop-Loss Recalibration (Course Correction 2026-04-12)

As an operator,
I want the backtest engine to reject entry into positions where one platform shows stale or illiquid pricing, and I want a tighter stop-loss default,
So that the simulation avoids illusory edges from liquidity asymmetry and cuts losses faster on diverging positions.

**Context:** In backtest run `2d2f84ac`, 8 STOP_LOSS exits (-$736) and 106 diverged TIME_DECAY exits (-$1,338) share the same root cause: one platform's price is stale/flat while the other moves dramatically. All 8 stop-loss pairs verified against `contract_matches` — descriptions and CLOB token IDs match correctly. These are NOT contract matching errors. The apparent "edge" is illusory because one platform has no real market activity (e.g., Polymarket at $0.002 with zero price movement).

Pattern observed across all 8 STOP_LOSS positions:
- One platform moves 30-63 cents, the other moves 0-0.5 cents
- Exit edge EXCEEDS entry edge (divergence, not convergence)
- Average price gap at entry: $0.12 (vs $0.11 for profitable trades)

62 of 106 diverged TIME_DECAY positions show identical one-sided movement. 51 have Polymarket flat, 11 have Kalshi flat.

**Acceptance Criteria:**

1. **Given** a candidate entry opportunity **when** either platform's price is below `minEntryPricePct` (default 0.05) **then** the entry is skipped and a counter is incremented in the calibration report.

2. **Given** a candidate entry opportunity **when** the absolute price gap between platforms (`|kalshiPrice - polymarketPrice|`) exceeds `maxEntryPriceGapPct` (default 0.25) **then** the entry is skipped and a counter is incremented.

3. **Given** `exitStopLossPct` configuration **when** no explicit value is provided **then** the default is `0.15` (was `0.30`). `@Min(0.05) @Max(0.50)` validation range.

4. **Given** filtered entries **when** the calibration report is generated **then** a new "Liquidity Filters" section shows: total candidates evaluated, entries rejected by min-price filter (with per-platform breakdown), entries rejected by price-gap filter, and the configured thresholds.

5. **Given** existing tests **when** all run **then** all pass. New tests: min-price filter rejects below threshold, allows above; price-gap filter rejects above threshold, allows below; stop-loss triggers at 15% default; filter counters accumulate correctly in report; all three filters are configurable and independently disablable (min 0 disables).

**Tasks:**

1. **Add config parameters** — `minEntryPricePct` and `maxEntryPriceGapPct` to `IBacktestConfig` and `BacktestConfigDto` with `@IsNumber() @Min(0) @IsOptional()` validation. Update `exitStopLossPct` default from 0.30 to 0.15.

2. **Add entry filtering in opportunity detection** — In `detectOpportunities()` (or equivalent entry evaluation), add pre-entry checks for min price and price gap. Skip and count filtered entries.

3. **Accumulate filter metrics** — Track per-run counts of filtered entries by reason. Include in calibration report generation.

4. **Tests** — Verify: min-price blocks entry below threshold; price-gap blocks entry above threshold; stop-loss triggers at new default; filters configurable; counters accumulate; existing tests pass.

**Dependencies:** 10-95-12 complete (all prior fixes in place).

---

### Story 10-95-14: PROFIT_CAPTURE Fee-Aware P&L Guard (Course Correction 2026-04-12)

As an operator,
I want the backtest PROFIT_CAPTURE exit to verify post-fee profitability before triggering,
So that positions with small edge but large fees are not exited as "profit captures" when they would actually realize a loss.

**Context:** In backtest run `2d2f84ac`, 81 of 413 PROFIT_CAPTURE exits (20%) realized a net loss despite the P&L guard at `exit-evaluator.service.ts:120-133` checking `mtmPnl > 0`. The guard uses raw `calculateLegPnl()` (price movement only), but `closePosition()` at `backtest-portfolio.service.ts:262-266` deducts entry fees, exit fees, and gas. When raw P&L is positive but smaller than total fees, the guard approves exit but the actual result is negative.

Evidence:
- Losing PROFIT_CAPTURE avg: entry_edge 4.1%, raw P&L ~$8.40, fees ~$9.80, realized -$1.99
- Winning PROFIT_CAPTURE avg: entry_edge 8.8%, raw P&L ~$19.50, fees ~$7.46, realized +$12.06
- Win rate by entry edge: <5% = 61%, 5-6% = 84%, 6-8% = 95%, 8%+ = 100%

**Note:** Story 10-95-11 already raised the default `edgeThresholdPct` from 0.03 to 0.05, which would prevent many of these entries. This run used the old 0.03 value. The fee-aware guard is still needed as defense-in-depth for positions that enter near the threshold.

**Acceptance Criteria:**

1. **Given** PROFIT_CAPTURE exit evaluation **when** `capturedRatio >= exitProfitCapturePct` **then** the P&L guard estimates total fees (entry fees from position + estimated exit fees using `FinancialMath.calculateTakerFeeRate()`) and checks `rawMtmPnl - estimatedTotalFees > 0`. If post-fee P&L <= 0, condition returns false (falls through to other exit triggers).

2. **Given** estimated exit fees in the P&L guard **then** uses the same fee estimation pattern as `calculateUnrealizedPnl()` in `backtest-portfolio.service.ts:46-55` (existing implementation that already includes exit fee calculation).

3. **Given** a position where raw mark-to-market P&L is positive but smaller than estimated total fees **when** PROFIT_CAPTURE is evaluated **then** it returns false and the position falls through to EDGE_EVAPORATION, TIME_DECAY, or STOP_LOSS as appropriate.

4. **Given** `ExitEvaluationParams` **then** includes `entryFees` and `gasCost` from the position record (already available on `SimulatedPosition`).

5. **Given** existing tests **when** all run **then** all pass. New tests: fee-aware guard rejects exit when raw P&L < total fees; fee-aware guard approves when raw P&L > total fees; guard correctly estimates exit fees using platform fee schedules; edge cases: zero fees, very small positions.

**Tasks:**

1. **Extend `ExitEvaluationParams`** — Add `entryFees: Decimal` and `gasCost: Decimal` (sourced from `SimulatedPosition`).

2. **Make P&L guard fee-aware** — In `isProfitCaptureTriggered()`, after computing raw `mtmPnl`, estimate exit fees using `FinancialMath.calculateTakerFeeRate()` for both platforms (same pattern as `calculateUnrealizedPnl`). Check `mtmPnl - exitFees - entryFees - gasCost > 0`.

3. **Pass position cost data to exit evaluator** — Ensure `evaluateExits()` call site passes entry fees and gas cost from the position.

4. **Tests** — Verify: guard rejects when raw P&L positive but < fees; guard accepts when raw P&L > fees; fee estimation matches `calculateUnrealizedPnl` pattern; parametric tests across fee schedule ranges.

**Dependencies:** 10-95-12 complete. Independent of 10-95-13 (can be implemented in parallel).

---

## Section 5: Implementation Handoff

### Scope Classification: Moderate

Two independent stories, both confined to backtest engine module.

### Handoff Plan

| Role | Responsibility |
|------|---------------|
| **Scrum Master (Bob)** | Update sprint-status.yaml, update epics.md with new stories |
| **Dev Agent** | Implement stories 10-95-13 and 10-95-14 (can be parallel) |
| **Operator (Arbi)** | Re-run backtest with updated engine to validate P&L improvement |

### Success Criteria

1. Backtest run with same config (but new defaults) shows: zero STOP_LOSS exits from liquidity-flat pairs, PROFIT_CAPTURE losers reduced to <5% of total PROFIT_CAPTURE exits, overall P&L > +$3,500 (vs current +$2,026)
2. All existing tests pass + new tests for each story
3. Calibration report includes liquidity filter metrics

### Post-Implementation Validation

Re-run backtest `2d2f84ac` configuration with updated engine. Compare:
- STOP_LOSS exit count and P&L
- PROFIT_CAPTURE loser count and P&L
- Diverged TIME_DECAY count and P&L
- Overall P&L, win rate, Sharpe ratio
