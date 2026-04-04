# Sprint Change Proposal: Backtest Exit Logic Fix & Full-Cost PnL Accounting

**Date:** 2026-04-10
**Triggered by:** Analysis of backtest run `e90b5698-de93-4647-bd94-7f7ca3c07e5b` (Mar 1–5, $10K bankroll) — first run after Story 10-95-8 shipped
**Scope Classification:** Minor — 1 new story in existing Epic 10.95, 1 additive Prisma enum migration, no architectural changes
**Status:** APPROVED (2026-04-10)

---

## Section 1: Issue Summary

### Problem Statement

Backtest run `e90b5698` lost **-$937.90 (Sharpe -18.24, 10.5% win rate, profit factor 0.238)** despite Story 10-95-8 successfully fixing zero-price contamination and adding exit fee deduction. The data now has realistic entry edges (avg 8.4% vs prior 67.3%) and non-null fees — confirming 10-95-8 worked. However, stripping away the zero-price noise exposed a **second layer of defects**: a fundamentally broken profit-capture exit condition and incomplete cost accounting.

### Two Critical Defects

**1. PROFIT_CAPTURE exit condition triggers on edge convergence, not position profitability (`exit-evaluator.service.ts:98-106`)**

The formula `capturedRatio = (entryEdge - currentNetEdge) / entryEdge` fires when 80%+ of the edge has evaporated. But edge evaporation is **direction-agnostic** — it cannot distinguish between:

- **Favorable convergence** (K drops, P rises → position profits)
- **Adverse one-sided movement** (K rises sharply, P barely moves → position loses)

Both reduce the edge equally. The condition is satisfied either way.

**2. Entry fees and gas omitted from realized PnL (`backtest-portfolio.service.ts:240`)**

`realizedPnl = kalshiPnl + polyPnl - exitFees`. Entry fees (~$4.5–5.5/position) and gas ($0.50/position) are never deducted. The previous change proposal (2026-04-08) explicitly deferred this: *"Entry fees are already captured in calculateNetEdge()."* This reasoning conflates two separate concerns — the edge metric governs entry **decisions**, while PnL must reflect actual **costs**. They serve different purposes.

### Discovery Context

Post-10-95-8 validation backtest. Story 10-95-8 successfully eliminated zero-price contamination (entry edges now 8.4% avg vs prior 67.3%) and added exit fee deduction (fees now populated vs prior NULL). With clean data, the exit logic and cost accounting defects became visible.

### Evidence Summary

| Evidence | Detail |
|---|---|
| PROFIT_CAPTURE exits | ALL 39 are losers (avg -$9.23, total -$360.14) |
| Direction analysis | 33/39 (84.6%) PROFIT_CAPTURE exits had Kalshi rising (adverse for short leg) |
| Worst PROFIT_CAPTURE | K 0.64→0.95, P 0.325→0.33. CapturedRatio 3,060%. Realized PnL: **-$62.99** |
| INSUFFICIENT_DEPTH exits | 97/171 (57%), total -$545.05 |
| Entry fee gap | Recorded fees match exit-only calculation exactly. Missing ~$770–850 in entry fees + gas |
| Edge buckets | ALL 7 buckets (< 2% through 12%+) are net negative |
| Direction bias | 100% SELL Kalshi / BUY Polymarket — zero reverse trades |
| Win rate | 18/171 = 10.5% |
| Total fees recorded | $814.60 (exit-only) |
| Run metrics | Sharpe -18.24, profit factor 0.238, max drawdown 10.3% |

---

## Section 2: Impact Analysis

### Checklist Results

| # | Item | Status |
|---|------|--------|
| 1.1 | Triggering story identified | [x] Done — Post-Story 10-95-8 backtest validation run |
| 1.2 | Core problem defined | [x] Done — 2 bugs: PROFIT_CAPTURE direction-blind + missing entry fees/gas in PnL |
| 1.3 | Evidence gathered | [x] Done — DB analysis of 171 positions, code review of exit-evaluator + portfolio services |
| 2.1 | Current epic (10.95) impact | [x] Done — 1 new story after completed 10-95-8 |
| 2.2 | Epic-level changes needed | [x] Done — 1 new story in Epic 10.95 |
| 2.3 | Remaining epics reviewed | [x] Done — Epic 11, 12 unaffected |
| 2.4 | New epics needed | [x] Done — No, fits within 10.95 |
| 2.5 | Epic ordering | [x] Done — No resequencing; 10-95-9 slots after 10-95-8 |
| 3.1 | PRD conflicts | [!] Action-needed — FR-EM-01 says "take profit at 80% of initial edge captured" but doesn't specify PnL guard. Add clarification. |
| 3.2 | Architecture conflicts | [!] Action-needed — Document mark-to-market validation requirement for backtest exit evaluator |
| 3.3 | UI/UX conflicts | [N/A] — No new dashboard features |
| 3.4 | Other artifacts | [N/A] — No deployment changes |
| 4.1 | Direct Adjustment viable | [x] Viable — Effort: Low, Risk: Low |
| 4.2 | Rollback viable | [N/A] — Nothing to roll back (original gap, not regression) |
| 4.3 | MVP Review needed | [N/A] — MVP complete |
| 4.4 | Recommended path | [x] Done — Direct Adjustment (1 new story in 10.95) |

### Epic Impact

**Epic 10.95 (in-progress):** Add story 10-95-9 after completed 10-95-8. Epic scope ("TimescaleDB Migration & Backtesting Quality") covers this. Final story before retro.

**Epic 11, 12 (backlog):** No changes needed.

### Artifact Changes Required

**PRD** (`prd.md`, FR-EM-01):
- Clarify that "take profit at 80% of initial edge captured" requires mark-to-market PnL to be positive before triggering.

**Architecture** (`architecture.md`, Backtesting module section):
- Document that BacktestEngine exit evaluator must validate mark-to-market PnL direction before classifying an exit as PROFIT_CAPTURE. Entry cost accounting (entry fees + gas) must be included in realized PnL.

**Epics** (`epics.md`, Epic 10.95):
- Add story 10-95-9 definition.

**Sprint Status** (`sprint-status.yaml`):
- Add `10-95-9-backtest-exit-logic-pnl-fix: backlog` entry under `epic-10-95`.

---

## Section 3: Recommended Approach

### Selected: Direct Adjustment — 1 New Story in Epic 10.95

**Rationale:**
- **Low effort.** PROFIT_CAPTURE fix is ~5 lines (add PnL guard). Entry fee deduction mirrors the exit fee pattern already implemented in 10-95-8. Stop-loss is a new exit condition using existing evaluator framework.
- **Low risk.** No schema migrations beyond additive enum value. No module boundary crossings. Exit evaluator has clean test coverage.
- **Critical for backtest trustworthiness.** Until PROFIT_CAPTURE is fixed, every backtest run produces misleading exit classifications. Until entry fees are in PnL, every position's reported profitability is wrong.
- **Validates 10-95-8.** A clean backtest result after this fix validates the entire 10.95 quality pipeline.

**Trade-offs considered:**
- *Splitting into two stories (exit logic + PnL accounting):* Each undersized at ~3-4 tasks. Combined (~8 tasks) is right-sized and they share the "backtest result accuracy" concern.
- *Also adding liquidity pre-qualification filters:* Deferred. The INSUFFICIENT_DEPTH issue may look different after the PROFIT_CAPTURE fix — some positions forced out by depth may have correctly profit-captured earlier if the exit logic wasn't broken. Re-evaluate after re-run.
- *Also fixing unidirectional bias:* Not a bug. If Kalshi consistently prices higher for the same events, SELL K / BUY P is the correct arb direction. The detection engine is working as designed.

---

## Section 4: Detailed Change Proposals

### Story 10-95-9: Backtest Exit Logic Fix & Full-Cost PnL Accounting (Added by Course Correction 2026-04-10)

As an operator,
I want the backtest PROFIT_CAPTURE exit to verify actual position profitability before triggering, and realized P&L to include all trading costs (entry fees + gas),
So that backtest exit classifications are accurate and P&L reflects true economics.

**Context:** Backtest run `e90b5698` (Mar 1-5, $10K bankroll) lost $937.90 after Story 10-95-8 fixed zero-price contamination and added exit fees. Two remaining defects:

1. **PROFIT_CAPTURE is direction-blind:** `exit-evaluator.service.ts:104` fires when `(entryEdge - currentEdge) / entryEdge >= 0.8`, but doesn't check which direction prices moved. ALL 39 PROFIT_CAPTURE exits were losers (avg -$9.23). In 84.6% of cases, the Kalshi short leg was destroyed by rising prices while Polymarket barely moved.

2. **Entry fees + gas missing from PnL:** `backtest-portfolio.service.ts:240` computes `realizedPnl = kalshiPnl + polyPnl - exitFees`. Entry fees (~$4.5-5.5/position) and gas ($0.50/position) are never subtracted. ~$800 of costs are invisible.

**Acceptance Criteria:**

1. **Given** the PROFIT_CAPTURE exit condition in `exit-evaluator.service.ts`
   **When** the captured ratio threshold is met (`capturedRatio >= exitProfitCapturePct`)
   **Then** the exit is ONLY classified as PROFIT_CAPTURE if the mark-to-market PnL is positive
   **And** mark-to-market PnL is computed as: `calculateLegPnl(kalshiSide, kalshiEntry, kalshiCurrent, size) + calculateLegPnl(polySide, polyEntry, polyCurrent, size)`
   **And** if `capturedRatio >= threshold` but `mtmPnl <= 0`, the condition returns false (falls through to EDGE_EVAPORATION or other triggers)

2. **Given** `ExitEvaluationParams` passed to the exit evaluator
   **When** PROFIT_CAPTURE is evaluated
   **Then** the params include position entry prices and current prices for both platforms (required for PnL calculation)
   **And** the `calculateLegPnl` function from `common/utils/financial-math.ts` is used (no duplication)

3. **Given** a position is opened in `backtest-portfolio.service.ts:openPosition()`
   **When** the position is created
   **Then** entry fees are computed for both legs using `FinancialMath.calculateTakerFeeRate()` with platform fee schedules:
   - `kalshiEntryFee = kalshiEntryPrice × positionSizeUsd × takerFeeRate(kalshiEntryPrice)` using `DEFAULT_KALSHI_FEE_SCHEDULE`
   - `polyEntryFee = polymarketEntryPrice × positionSizeUsd × takerFeeRate(polymarketEntryPrice)` using `DEFAULT_POLYMARKET_FEE_SCHEDULE`
   **And** entry fees are stored on the `SimulatedPosition` (new field: `entryFees: Decimal`)
   **And** gas cost (`gasEstimateUsd` from config) is stored on the position (new field: `gasCost: Decimal`)

4. **Given** a position is closed in `backtest-portfolio.service.ts:closePosition()`
   **When** realized PnL is calculated
   **Then** `realizedPnl = kalshiPnl + polyPnl - exitFees - entryFees - gasCost`
   **And** `fees` field stored on the closed position includes both entry and exit fees: `fees = entryFees + exitFees`
   **And** capital tracking adjusts: `availableCapital += positionSizeUsd + realizedPnl` (realizedPnl now fully net)

5. **Given** the backtest engine configuration
   **When** `edgeThresholdPct` is evaluated for entry
   **Then** the minimum default value is raised from `0.008` (0.8%) to `0.03` (3%)
   **And** the config validation rejects values below `0.02` (2%) with a descriptive error message
   **And** existing `maxEdgeThresholdPct` (15%) upper bound from 10-95-8 remains

6. **Given** a new exit condition: mark-to-market stop-loss
   **When** an open position's mark-to-market PnL drops below a configurable threshold (default: -15% of `positionSizeUsd`)
   **Then** the exit evaluator triggers a `STOP_LOSS` exit with priority between INSUFFICIENT_DEPTH (2) and PROFIT_CAPTURE (3)
   **And** the new `BacktestExitReason` enum value `STOP_LOSS` is added to the Prisma schema
   **And** stop-loss percentage is configurable via `exitStopLossPct` in `BacktestConfig` (default: `0.15`)

7. **Given** the unrealized PnL calculation in `calculateUnrealizedPnl()` (used for open position reporting)
   **When** unrealized PnL is computed for the dashboard
   **Then** it includes estimated exit fees (already present from 10-95-6) AND entry fees + gas (newly included)
   **And** the formula is: `unrealizedPnl = kalshiMtmPnl + polyMtmPnl - estimatedExitFees - entryFees - gasCost`

8. **Given** existing backtest tests and the new changes
   **When** all changes are applied
   **Then** all existing tests pass (update assertions where entry fees and gas now affect PnL values)
   **And** new tests verify:
   - (a) PROFIT_CAPTURE only fires when `mtmPnl > 0` (positive convergence)
   - (b) PROFIT_CAPTURE does NOT fire when `capturedRatio >= 0.8` but `mtmPnl <= 0` (adverse movement)
   - (c) Entry fees + gas are stored on `SimulatedPosition` at open time
   - (d) `realizedPnl` is net of entry fees + exit fees + gas
   - (e) `STOP_LOSS` triggers at configurable threshold and has correct priority
   - (f) `STOP_LOSS` does NOT trigger when PnL is above threshold
   - (g) Minimum edge threshold validation rejects < 2%
   - (h) Unrealized PnL includes all cost components

**Tasks:**

1. **PROFIT_CAPTURE PnL guard** — In `exit-evaluator.service.ts:isProfitCaptureTriggered()`, after the `capturedRatio` check, compute mark-to-market PnL using `calculateLegPnl()` for both legs. Return `true` only if `capturedRatio >= threshold AND mtmPnl > 0`. Add required position price fields to `ExitEvaluationParams`.

2. **Entry fee + gas tracking on position open** — In `backtest-portfolio.service.ts:openPosition()`, compute entry fees for both legs using `FinancialMath.calculateTakerFeeRate()`. Store as `entryFees` and `gasCost` on `SimulatedPosition`. Add fields to simulation types.

3. **Full-cost PnL in closePosition()** — Modify `realizedPnl` calculation to subtract `entryFees + gasCost` in addition to exit fees. Update `fees` field to include entry + exit. Ensure capital tracking uses the fully-net PnL.

4. **STOP_LOSS exit condition** — Add `STOP_LOSS` to `BacktestExitReason` enum (Prisma schema + migration). Add `isStopLossTriggered()` to `ExitEvaluatorService` with priority 2.5 (between INSUFFICIENT_DEPTH and PROFIT_CAPTURE). Add `exitStopLossPct` to `BacktestConfig` with default 0.15.

5. **Minimum edge threshold floor** — Change `edgeThresholdPct` default from 0.008 to 0.03. Add config validation rejecting values < 0.02 with descriptive error.

6. **Unrealized PnL update** — Update `calculateUnrealizedPnl()` to subtract `entryFees + gasCost` from mark-to-market calculation.

7. **Update existing tests** — Fix assertions in `exit-evaluator.service.spec.ts` and `backtest-portfolio.service.spec.ts` for new PnL values, new params, and new exit reason.

8. **New tests** — Per AC #8: PROFIT_CAPTURE positive/negative PnL paths, entry fee storage, full-cost PnL, STOP_LOSS trigger/non-trigger, edge threshold validation, unrealized PnL cost components.

**Technical Notes:**
- The `calculateLegPnl()` function already exists in `common/utils/financial-math.ts` — reuse it in the exit evaluator. Import path: `from '@common/utils/financial-math'`.
- The Prisma enum change (`STOP_LOSS` addition) requires a migration. This is additive-only and backward compatible.
- `ExitEvaluationParams` needs expansion: add `kalshiEntryPrice`, `polymarketEntryPrice`, `kalshiCurrentPrice`, `polymarketCurrentPrice`, `kalshiSide`, `polymarketSide`, `positionSizeUsd`. The calling code in `backtest-engine.service.ts` already has all these values available.
- The stop-loss priority (2.5) means: if both INSUFFICIENT_DEPTH and STOP_LOSS trigger simultaneously, INSUFFICIENT_DEPTH wins (market condition). If STOP_LOSS and PROFIT_CAPTURE both trigger, STOP_LOSS wins (protective exit takes precedence).
- After this story ships, re-run the same Mar 1-5 backtest to validate. Expected: PROFIT_CAPTURE exits should be profitable, total PnL closer to breakeven.

**Dependencies:** None (10-95-1 through 10-95-8 all complete). Final story before Epic 10.95 retrospective.

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

Focused correctness fix within an existing epic. One additive Prisma enum migration. No cross-module refactoring, no strategic pivot.

### Handoff Recipients

| Role | Responsibility |
|---|---|
| **Scrum Master (Bob)** | Update `sprint-status.yaml` with story 10-95-9. Update `epics.md`. Apply PRD/Architecture clarifications. |
| **Dev Agent** | Implement story 10-95-9 following TDD workflow. |
| **Operator (Arbi)** | Re-run Mar 1-5 backtest after fix. Compare metrics against `e90b5698`. If INSUFFICIENT_DEPTH remains dominant, file follow-up course correction for liquidity pre-qualification filters. |

### Sequencing

```
Epic 10.95 (in-progress):
  10-95-1 through 10-95-8: DONE
  |
  NEW → 10-95-9: backlog (exit logic fix + full-cost PnL)
  |
  epic-10-95-retrospective
  |
  Epic 11: Platform Extensibility & Security Hardening
```

### Success Criteria

1. Zero PROFIT_CAPTURE exits with negative realized PnL on re-run
2. All positions include entry fees + gas in `realized_pnl` and `fees` columns
3. `fees` column = entry fees + exit fees (both components)
4. STOP_LOSS exits observed for positions exceeding -15% position size loss
5. No entries with edge < 2% (config validation enforced)
6. All existing tests pass, new tests cover all fix paths
7. Re-run of Mar 1-5 backtest produces trustworthy metrics

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| PROFIT_CAPTURE PnL guard filters too aggressively | Low | Positions still exit via EDGE_EVAPORATION, STOP_LOSS, or TIME_DECAY |
| STOP_LOSS triggers too frequently at 15% | Low | Configurable threshold; can be relaxed |
| Entry fee calculation diverges from live pipeline | Low | Same FinancialMath + fee schedules; tests verify |
| Raising min edge to 3% reduces opportunity count | Low | Most profitable trades have >5% edge; configurable |

---

## Checklist Completion Summary

| Section | Status |
|---------|--------|
| 1. Trigger & Context | [x] Complete |
| 2. Epic Impact | [x] Complete |
| 3. Artifact Conflicts | [x] Complete — PRD FR-EM-01 and Architecture need minor clarifications |
| 4. Path Forward | [x] Complete — Direct Adjustment selected |
| 5. Proposal Components | [x] Complete — 1 story defined |
| 6. Final Review | [x] Complete — Approved 2026-04-10 |
