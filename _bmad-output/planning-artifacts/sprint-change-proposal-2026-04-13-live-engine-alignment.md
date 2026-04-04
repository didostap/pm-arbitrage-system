# Sprint Change Proposal: Live Trading Engine Alignment & Configuration Calibration

**Date:** 2026-04-13
**Triggered by:** Backtest profitability analysis (stories 10-95-8 through 10-95-14)
**Scope Classification:** Moderate
**Status:** Approved

---

## 1. Issue Summary

The backtest engine has turned profitable after six critical algorithmic fixes (stories 10-95-8 through 10-95-14), validated across 5 runs with the best showing **+$2,026 P&L, 12.26 Sharpe, 1.67 profit factor** over March–April 2026. These fixes exist only in the backtest engine — the live trading engine lacks all of them. The live engine is currently disabled (early `return;` on line 65 of `trading-engine.service.ts`) and must not be re-enabled without these fixes.

**Evidence:**
- Pre-fix backtest: -$3,406 P&L, -48.20 Sharpe, 7.6% win rate
- Post-fix backtest: +$2,026 P&L, 12.26 Sharpe, 56.1% win rate
- Fee-aware PROFIT_CAPTURE guard eliminated 81 losers (100% win rate post-fix)
- STOP_LOSS prevented -$168 in catastrophic losses (2 triggers)
- Entry liquidity filters eliminated -$736 STOP_LOSS and -$1,338 diverged TIME_DECAY losses
- TIME_DECAY cooldown prevents re-entry churning (-$9.10 avg loss per TIME_DECAY exit)

**Recalibrations during analysis** (live engine differs from backtest structurally):
- Side selection bug (10-95-10): NOT present in live — live evaluates both directions independently. **Removed from scope.**
- Edge formula (10-95-11): Live uses signed `sellPrice - buyPrice` with dual-scenario evaluation. Functionally correct. **No fix needed.**
- Exit fee deduction: Live C6 already deducts exit fees. **Only entry fee deduction needed.**

---

## 2. Impact Analysis

### Epic Impact
- **New epic required:** Epic 10.96 — Live Trading Engine Alignment & Configuration Calibration
- **Sequencing:** 10.95 (complete) → **10.96 (new)** → 11 (backlog)
- **Hard sequencing requirement:** Live engine must not be re-enabled without 10.96 fixes
- **No impact on Epic 11 or 12**

### Artifact Conflicts
- **PRD:** No conflicts. Fixes align with or enhance PRD requirements (FR-AD-03 edge threshold, FR-RM-01 position sizing, FR-EM-01 exit thresholds)
- **Architecture:** No changes. All fixes are algorithmic within existing module boundaries
- **UI/UX:** No changes. Settings page renders dynamically from backend
- **Schema:** No migration needed. Entry fee data already exists on OpenPosition (`entryKalshiFeeRate`, `entryPolymarketFeeRate`, `entryClosePriceKalshi`, `entryClosePricePolymarket`)

### Technical Impact
- **threshold-evaluator.service.ts** (625 lines) — entry fee deduction + stop-loss
- **edge-calculator.service.ts** (546 lines) — max edge cap
- **trading-engine.service.ts** or edge calculator — entry price/gap filters
- **pair-concentration-filter.service.ts** — TIME_DECAY-specific cooldown
- **exit-monitor.service.ts** — pass entry fee data + exit reason context
- **config-defaults.ts** — 3 new settings + 5 default value updates

---

## 3. Recommended Approach

**Direct Adjustment** — new epic 10.96 with 4 stories.

**Rationale:**
- Fixes are already implemented and tested in the backtest engine — porting is adaptation, not invention
- Live engine is disabled (`return;` on line 65), providing a safe implementation window
- No architectural or scope changes needed
- Each fix has backtest validation data proving P&L impact
- Effort: Medium. Risk: Low. Timeline: 4 stories, each 5-8 tasks.

**Alternatives considered and rejected:**
- Rollback: Nothing to roll back — backtest fixes are correct and live has no recent changes
- PRD MVP Review: MVP scope not affected — these strengthen the system

---

## 4. Detailed Change Proposals

### Story 10-96-1: Entry-Fee-Aware Exit PnL & Percentage Stop-Loss

**Scope:** Two tightly coupled fixes in the live exit evaluation pipeline:

1. **Entry fee deduction in exit PnL** — `threshold-evaluator.service.ts` currently computes `currentPnl = kalshiPnl + polymarketPnl - exitFees`. Missing: `- entryFees - gasCost`. Entry fee data already exists on position (`entryKalshiFeeRate`, `entryPolymarketFeeRate`, `entryClosePriceKalshi`, `entryClosePricePolymarket`). Compute entry fee dollar cost from rates x sizes x entry-close-prices.

2. **Percentage-based stop-loss** — Add `exitStopLossPct` config setting (default 0.20). When `currentPnl <= -exitStopLossPct x positionSizeUsd`, trigger exit. This replaces/augments the current breakeven-based SL (multiplier -1.0) in fixed mode.

**Impacted files:**
- `src/modules/exit-management/threshold-evaluator.service.ts` — entry fee deduction + stop-loss logic
- `src/common/config/config-defaults.ts` — new `exitStopLossPct` setting
- `src/modules/exit-management/exit-monitor.service.ts` — pass entry fee data to evaluator

**Backtest evidence:** 10-95-9 showed entry fees + gas = ~$800 invisible costs. 10-95-14 showed fee-unaware PROFIT_CAPTURE produced 81 losers. Two STOP_LOSS triggers prevented -$168 in catastrophic losses.

---

### Story 10-96-2: Max Edge Cap & Entry Liquidity Filters

**Scope:** Three entry-side guards in the live detection pipeline:

1. **Max edge cap (phantom signal guard)** — Add `maxEdgeThresholdPct` config setting (default 0.35). Reject any opportunity where `netEdge > maxEdgeThresholdPct`. The live engine's existing `maxDynamicEdgeThreshold` (0.05) caps dynamic threshold scaling, NOT actual net edge. A 50%+ "edge" from a data anomaly would currently trade.

2. **Minimum entry price filter** — Add `minEntryPricePct` config setting (default 0.08). Reject opportunities where either platform's price < threshold. Prices below 8% are typically illiquid/stale.

3. **Maximum entry price gap filter** — Add `maxEntryPriceGapPct` config setting (default 0.20). Reject opportunities where `|kalshiPrice - polymarketPrice| > threshold`. Large price gaps correlate with stale one-sided pricing.

**Impacted files:**
- `src/modules/arbitrage-detection/edge-calculator.service.ts` — max edge cap after net edge calculation
- `src/core/trading-engine.service.ts` — entry price + gap filters in detection-risk pipeline
- `src/common/config/config-defaults.ts` — three new settings

**Backtest evidence:** 10-95-8: phantom signals at 40%+ edge. 10-95-13: liquidity filters eliminated -$736 STOP_LOSS and -$1,338 diverged TIME_DECAY.

---

### Story 10-96-3: Post-TIME_DECAY Re-Entry Cooldown

**Scope:** Prevent the live engine from re-entering a pair immediately after a TIME_DECAY exit.

Add `timeDecayCooldownHours` config setting (default 24). The pair concentration filter checks exit reason and applies the longer cooldown only for TIME_DECAY exits. Non-TIME_DECAY exits (PROFIT_CAPTURE, EDGE_EVAPORATION) use the existing generic `pairCooldownMinutes` (shorter).

**Impacted files:**
- `src/common/interfaces/pair-concentration-filter.interface.ts` — extend to accept exit reason context
- `src/modules/risk-management/pair-concentration-filter.service.ts` — TIME_DECAY-specific cooldown logic
- `src/modules/exit-management/exit-monitor.service.ts` — pass exit reason to concentration filter on position close
- `src/common/config/config-defaults.ts` — new `timeDecayCooldownHours` setting

**Backtest evidence:** 10-95-12: TIME_DECAY exits average -$9.10 P&L and 93h hold. Without cooldown, engine re-enters same toxic pair immediately.

---

### Story 10-96-4: Configuration Defaults Calibration

**Scope:** Update default values in `config-defaults.ts` to backtest-validated settings.

| Setting | Key | Current | New | Line | Rationale |
|---------|-----|---------|-----|------|-----------|
| Min edge threshold | `detectionMinEdgeThreshold` | `'0.008'` | `'0.05'` | 35-38 | Below 5%, fee drag makes entries negative EV |
| Gas estimate | `detectionGasEstimateUsd` | `'0.30'` | `'0.50'` | 39-42 | Conservative estimate validated by backtest |
| Max open pairs | `riskMaxOpenPairs` | `10` | `25` | 90 | Phase 1 PRD spec (FR-RM-02) |
| Profit capture ratio | `exitProfitCaptureRatio` | `0.5` | `0.8` | 307-310 | 80% threshold validated — 100% PROFIT_CAPTURE win rate |
| Pair cooldown | `pairCooldownMinutes` | `30` | `60` | 313-316 | Modest increase for generic cooldown |

**Impacted files:**
- `src/common/config/config-defaults.ts` — value changes only
- DTO validation decorators if `@Min`/`@Max` bounds need adjustment

**Backtest evidence:** Current defaults set during MVP before any backtest validation. Backtest profitable only after parameter tuning.

---

## 5. Implementation Handoff

**Change Scope:** Moderate — requires backlog update and SM coordination for sprint planning.

**Handoff Recipients:**
- **SM (Bob):** Update sprint-status.yaml with Epic 10.96 and stories. Run sprint planning to generate story files.
- **Dev agent:** Implement stories 10-96-1 through 10-96-4 following TDD workflow.
- **Operator:** After implementation, run full backtest with new live defaults to validate before removing the `return;` gate in `trading-engine.service.ts`.

**Success Criteria:**
1. All four stories implemented with passing tests
2. Backtest run with live-equivalent settings produces comparable profitability (P&L > $0, profit factor > 1.2)
3. Live engine `return;` gate removed only after validation
4. All existing 3793+ tests continue to pass

**Dependencies:**
- 10-96-1 before 10-96-4 (stop-loss setting must exist before calibrating its default)
- 10-96-2 before 10-96-4 (entry filter settings must exist before calibrating their defaults)
- 10-96-3 before 10-96-4 (cooldown setting must exist before calibrating)
- 10-96-4 is the final story (calibrates all new + existing defaults)

**Sequencing:** 10-96-1 → 10-96-2 → 10-96-3 → 10-96-4 (sequential due to config dependencies)
