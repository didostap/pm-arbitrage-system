# Sprint Change Proposal: Backtest Edge Metric Realignment & Re-Entry Prevention

**Date:** 2026-04-12
**Triggered by:** Deep investigation of backtest run `9bab5cf5-dd56-4bc2-b3da-8cdc20895a23` (Mar 1-5, $10K bankroll) — third post-fix validation after Stories 10-95-8, 10-95-9, 10-95-10
**Scope Classification:** Moderate — 2 new stories in existing Epic 10.95, no Prisma migration, no architectural changes, but calibration report invalidation requires re-generation
**Status:** APPROVED (2026-04-12)

---

## Section 1: Issue Summary

### Problem Statement

Despite three successful bug-fix stories (10-95-8: zero-price filtering + exit fees, 10-95-9: PROFIT_CAPTURE PnL guard + STOP_LOSS + full-cost accounting, 10-95-10: side selection + depth exit), backtest run `9bab5cf5` loses **-$3,406 on 436 positions** (Sharpe deeply negative, 7.1% win rate). The three prior fixes addressed real bugs and are confirmed working. However, they were incremental patches on an engine whose **core edge calculation formula diverges from both the PRD specification and the live detection engine**.

### Root Causes (4 bugs, 2 design flaws)

**Bug #1 (CRITICAL) — Edge metric mismatch:**
`calculateBestEdge()` in `edge-calculation.utils.ts:19-23` computes `grossEdge = 1 - K - P` (the "overround gap"). The PRD (Section FR-AD-02, Edge Calculation Formula) explicitly specifies `Gross Edge = sellPrice - buyPrice = |K - P|` (the price discrepancy). The live detection engine (`detection.service.ts:190-217`) correctly uses `calculateGrossEdge(buyPrice, sellPrice)` with actual order book prices — fixed in the March 3 sprint change proposal. The backtest engine, built later in Epic 10.9, independently re-implemented the wrong formula.

These metrics differ by `|1 - 2 * sellSidePrice|`, averaging 6-22 cents. **70% of positions (304/436)** have the coded net edge exceeding the raw `|K-P|` gap — meaning the engine enters trades where even the maximum possible profit (before fees) cannot cover what the edge predicted.

| Metric | Value |
|--------|-------|
| Avg coded entry edge | 9.6% |
| Avg actual `\|K-P\|` gap | 18.6% |
| Avg `1-K-P` overround | 12.1% |
| Actual gross PnL per unit | **0.97%** |
| Fees per unit | **4.91%** |

**Bug #2 (HIGH) — `sellPrice` complement in `calculateNetEdge()`:**
`edge-calculation.utils.ts:43-47` uses `sellPrice = 1 - polymarketClose` (the complement) instead of the actual trade price `polymarketClose`. The PRD example shows fees computed on actual prices: "Sell fee cost (Kalshi at 0.62): 0.62 x 0.0266 = 0.01649". The Polymarket flat 2% fee creates a systematic error of `0.02 * (1-2P)` per unit — underestimating fees when the sell price > 0.5.

**Bug #3 (HIGH) — No pair re-entry cooldown:**
`detectOpportunities()` in `backtest-engine.service.ts:588-675` re-enters the same pair immediately after TIME_DECAY exit because the persistent "edge" (the wrong metric) still exceeds the threshold. Top pair entered **76 times** at 1.24h intervals, losing $761. Top 3 pairs account for **42% of total loss** ($1,421) from fee churning alone.

**Bug #4 (MEDIUM) — Exit criteria track wrong metric:**
`evaluateExits()` calls `calculateCurrentEdge()` which also uses `1-K-P`. EDGE_EVAPORATION and PROFIT_CAPTURE triggers don't track actual PnL convergence, causing 87% of positions to fall through to TIME_DECAY.

### Discovery Context

Post-10-95-10 validation backtest. The three prior fixes eliminated noise (zero prices), corrected accounting (fees, PnL), fixed side selection, and improved depth exits. With those fixes in place, the structural edge metric divergence and re-entry churning became the dominant loss drivers.

### Evidence Summary

| Evidence | Detail |
|---|---|
| PRD Edge Formula | `Net Edge = \|Polymarket Price - Kalshi Price\| - Total Fees - Gas` (FR-AD-02) |
| Live engine formula | `calculateGrossEdge(buyPrice, sellPrice)` = `sellPrice - buyPrice` (detection.service.ts:190-217) |
| Backtest formula | `1 - kalshiClose - polymarketClose` (edge-calculation.utils.ts:19-23) |
| March 3 SCP | Fixed live engine from complement math to `\|K-P\|` — backtest never aligned |
| DB: Edge overestimation | 304/436 positions (70%) have coded net edge > raw `\|K-P\|` gap |
| DB: Fee dominance | Avg fees $9.83 vs avg gross PnL $1.94 (5:1 ratio) |
| DB: No convergence | SELL K group: 0.13 cents convergence on 5.68 cent gap. BUY K group: 0.16 cents on 34.27 cent gap |
| DB: Re-entry churning | Top pair: 76 entries, $761 loss. Top 3 pairs: 42% of total loss |
| DB: TIME_DECAY dominance | 354/406 closed positions (87%) exit via TIME_DECAY |

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Status | Impact |
|------|--------|--------|
| Epic 10.95 (TimescaleDB + Backtest Quality) | in-progress | **Directly affected.** Add 2 new stories (10-95-11, 10-95-12). 8 of 10 existing stories are done and unaffected. |
| Epic 10.9 (Backtesting Phase 1) | done | **Indirectly affected.** Calibration reports generated using the wrong edge metric are invalid. Re-generation needed after fix, but no code changes in 10.9 stories. |
| All other epics | — | No impact. |

### Story Impact

**Current stories (no changes needed):**
- Stories 10-95-1 through 10-95-10: All completed and correct. The three recent bug fixes (8, 9, 10) addressed real issues and are working as designed.

**New stories:**
- **Story 10-95-11:** Backtest edge metric realignment — fix `calculateBestEdge()`, `calculateNetEdge()`, `calculateCurrentEdge()` to match PRD formula and live engine
- **Story 10-95-12:** Backtest pair re-entry cooldown — prevent immediate re-entry into same pair after TIME_DECAY exit

### Artifact Conflicts

| Artifact | Conflict? | Detail |
|----------|-----------|--------|
| PRD | **YES — implementation diverges from spec** | PRD specifies `\|K-P\|` formula. Backtest uses `1-K-P`. Fix aligns implementation to PRD. |
| Architecture | No | All changes within `modules/backtesting/`. Module boundaries respected. |
| UI/UX | No | Dashboard displays engine output. No UI changes. |
| Calibration Reports | **YES — invalid data** | Reports from Epic 10.9 calibration runs used wrong edge metric. Re-run needed after fix. |

### Technical Impact

| Area | Impact |
|------|--------|
| Source files modified | 2-3 files: `edge-calculation.utils.ts`, `backtest-engine.service.ts`, possibly `backtest-portfolio.service.ts` |
| Test files modified | 3-4 files: `edge-calculation.utils.spec.ts`, `backtest-engine.service.spec.ts`, related spec files |
| Database | No schema changes. Existing backtest runs remain (historical comparison). |
| Infrastructure | No changes. |
| Dependencies | No changes. |

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment

Two focused stories within existing Epic 10.95. No rollback needed — prior fixes are correct. No MVP scope change — MVP is complete; backtesting is Phase 1.

### Rationale

1. **Clear PRD specification exists** — the fix aligns backtest to the documented, tested, and deployed formula
2. **Live engine already correct** — the March 3 SCP fixed the same bug in the live engine; this extends that fix to backtest
3. **Surgical scope** — 2-3 source files, no architectural changes, no migrations
4. **Prior fixes are preserved** — Stories 10-95-8/9/10 addressed real issues; this builds on them
5. **Immediate validation possible** — re-run same Mar 1-5 backtest to measure improvement

### Effort Estimate

| Story | Effort | Risk |
|-------|--------|------|
| 10-95-11 (Edge metric fix) | Medium (1 session) | Low — formula is well-defined in PRD with examples |
| 10-95-12 (Re-entry cooldown) | Low (1 session) | Low — straightforward state tracking in simulation loop |

### Risk Assessment

- **Regression risk:** Low. The edge metric change only affects entry/exit decisions. PnL accounting (fixed in 10-95-8/9) is independent.
- **Test coverage:** Existing `edge-calculation.utils.spec.ts` (18 tests) covers side selection and net edge — assertions will need updating for new formula. New tests needed for re-entry cooldown.
- **Overcorrection risk:** Low. The new formula is not a guess — it's the PRD-specified, live-engine-verified formula.

---

## Section 4: Detailed Change Proposals

### Story 10-95-11: Backtest Edge Metric Realignment

**As an operator,** I want the backtest engine to use the same edge formula as the PRD and live detection engine (`|K-P|` price discrepancy instead of `1-K-P` overround gap), **so that** backtest entry/exit decisions predict actual profitability and results can be compared to live performance.

**Acceptance Criteria:**

1. **Given** `calculateBestEdge()` **when** computing gross edge **then** returns `max(K,P) - min(K,P)` (= `|K-P|`) instead of `1-K-P`. This matches `FinancialMath.calculateGrossEdge(buyPrice, sellPrice)` = `sellPrice - buyPrice` as used by the live detection engine.

2. **Given** `calculateNetEdge()` **when** computing fee deductions **then** uses actual trade prices (`kalshiClose` and `polymarketClose`) instead of complement prices (`1-polymarketClose`, `1-kalshiClose`). The PRD example: "Buy fee cost (Polymarket at 0.58): 0.58 x 0.02 = 0.0116; Sell fee cost (Kalshi at 0.62): 0.62 x 0.0266 = 0.01649" — both use actual prices.

3. **Given** `calculateCurrentEdge()` **when** evaluating open position edge **then** uses the same `|K-P|` metric with actual prices for fee deduction, preserving the `entryBuySide` parameter for directional consistency (from 10-95-10).

4. **Given** `edgeThresholdPct` configuration **when** validated **then** the minimum floor is recalibrated to account for the new metric. With `|K-P|` as the edge, the threshold must exceed roundtrip fees per unit: `(entryFees + exitFees + gas) / positionSize`. For $200 positions with ~$10 roundtrip: minimum ~5%. Default raised from 0.03 to 0.05.

5. **Given** `maxEdgeThresholdPct` configuration **when** filtering phantom signals **then** recalibrated for the new metric. With `|K-P|` representing actual price gap (can be >0.50 for divergent markets), the cap should be higher than 15%. Raise default to 0.40 (40% price gap maximum).

6. **Given** existing tests **when** all tests run **then** all pass. Update `edge-calculation.utils.spec.ts` assertions for new formula. Add regression tests comparing backtest edge output to PRD examples.

**Files to modify:**
- `src/modules/backtesting/utils/edge-calculation.utils.ts` — `calculateBestEdge()`, `calculateNetEdge()`, `calculateCurrentEdge()`
- `src/modules/backtesting/utils/edge-calculation.utils.spec.ts` — update all edge value assertions
- `src/modules/backtesting/dto/backtest-config.dto.ts` — recalibrate `edgeThresholdPct` default + min, `maxEdgeThresholdPct` default
- `src/modules/backtesting/engine/backtest-engine.service.spec.ts` — update edge expectations
- Fixture files with `edgeThresholdPct` values

**What NOT to change:**
- `FinancialMath.calculateGrossEdge()` in `common/utils/financial-math.ts` — already correct
- `FinancialMath.calculateNetEdge()` in `common/utils/financial-math.ts` — already correct
- Live detection engine (`detection.service.ts`) — already uses correct formula
- PnL accounting in `backtest-portfolio.service.ts` — independent of edge metric, already correct from 10-95-9
- Fee calculation in `backtest-engine.service.ts:detectOpportunities()` entry fees — already uses actual prices (correct from 10-95-9)

### Story 10-95-12: Backtest Pair Re-Entry Cooldown

**As an operator,** I want the backtest engine to enforce a cooldown period before re-entering the same pair after a TIME_DECAY exit, **so that** the simulation doesn't churn through persistent non-converging edges, accumulating fees without new information.

**Acceptance Criteria:**

1. **Given** a position exits via TIME_DECAY **when** the same pair appears as a candidate in subsequent timesteps **then** the pair is skipped until `cooldownHours` have elapsed since the exit timestamp.

2. **Given** a position exits via EDGE_EVAPORATION, PROFIT_CAPTURE, STOP_LOSS, or RESOLUTION_FORCE_CLOSE **when** the same pair reappears **then** no cooldown is enforced (these exits indicate changed market conditions).

3. **Given** `cooldownHours` configuration **when** set in `BacktestConfig` **then** defaults to `exitTimeLimitHours` value (matching the hold period). Configurable via `IBacktestConfig` with `@IsNumber() @Min(0) @IsOptional()` validation.

4. **Given** cooldown tracking **when** simulation runs **then** cooldown state is tracked per-pair in the simulation loop via a `Map<pairId, lastTimeDecayExit>`. Cleanup: map entries are removed when cooldown expires or simulation ends. `/** Cleanup: entries expire after cooldownHours, map cleared at simulation end */`

5. **Given** headless simulations (walk-forward, sensitivity) **when** running sub-simulations **then** cooldown state is independent per simulation run (no cross-contamination via the `tempRunId` scoping).

6. **Given** existing tests **when** all tests run **then** all pass. New tests verify: cooldown blocks re-entry within period, cooldown does not block after period expires, cooldown does not apply to non-TIME_DECAY exits, cooldown map cleanup works.

**Files to modify:**
- `src/modules/backtesting/engine/backtest-engine.service.ts` — add cooldown tracking in `runSimulationLoop()` and `detectOpportunities()`
- `src/modules/backtesting/engine/backtest-engine.service.spec.ts` — new cooldown tests
- `src/common/interfaces/backtest-engine.interface.ts` — add `cooldownHours` to `IBacktestConfig`
- `src/modules/backtesting/dto/backtest-config.dto.ts` — add `cooldownHours` with validation

**What NOT to change:**
- Exit evaluator logic — cooldown is an entry filter, not an exit condition
- Portfolio service — no PnL impact
- Existing exit reasons — no new enum values

---

## Section 5: Implementation Handoff

### Change Scope: Moderate

While the code changes are surgically scoped (2-3 source files per story), the impact on calibration reports and backtest interpretation requires SM coordination.

### Handoff Plan

| Recipient | Responsibility |
|-----------|---------------|
| **Dev Agent** | Implement Stories 10-95-11 and 10-95-12 (TDD, standard post-edit workflow) |
| **SM (Bob)** | Update sprint-status.yaml with new stories. Schedule validation backtest. |
| **Operator (Arbi)** | Re-run Mar 1-5 backtest after both stories ship. Compare results to run `9bab5cf5`. |

### Success Criteria

1. **Edge metric alignment:** `calculateBestEdge()` output matches `FinancialMath.calculateGrossEdge(buyPrice, sellPrice)` for all test cases
2. **Fee consistency:** Net edge fee deductions use same prices as PnL fee deductions
3. **Re-entry reduction:** Top pair entries < 10 (down from 76)
4. **Validation backtest:** Win rate > 30% (up from 7.1%), total PnL improved significantly from -$3,406
5. **All tests pass:** Baseline maintained + new tests

### Implementation Order

1. **Story 10-95-11 first** (edge metric) — this changes what positions are entered, affecting all downstream metrics
2. **Story 10-95-12 second** (cooldown) — this is an additional filter on top of the corrected entry logic
3. **Validation backtest** — re-run after both stories, compare to `9bab5cf5`

### Epics File Update

Add to Epic 10.95 story list:

```
Story 10-95-11: Backtest Edge Metric Realignment
Story 10-95-12: Backtest Pair Re-Entry Cooldown
```

---

## Appendix: Prior Fix Chain Assessment

| Story | Fix | Working? | Regression? |
|-------|-----|----------|-------------|
| 10-95-8 | Zero-price SQL filter, TS guard, exit fee deduction, edge cap, data quality metrics | YES | No |
| 10-95-9 | PROFIT_CAPTURE PnL guard, STOP_LOSS exit, full-cost PnL (entry fees + gas), edge threshold floor | YES | No |
| 10-95-10 | Side selection via price comparison, depth exit on empty books only, buySide on position, calculateCurrentEdge with entryBuySide | YES | No |

All three fixes addressed real bugs. This proposal builds on them — it does not undo any prior work. The remaining issue (edge metric) was out of scope for those stories, which focused on fee accounting, side selection, and depth exits.

## Appendix: Mathematical Proof — Why `1-K-P` != `|K-P|`

For `buySide = 'kalshi'` (K < P, buy cheap K, sell expensive P):
```
Coded edge:  1 - K - P
Actual arb:  P - K
Difference:  (1-K-P) - (P-K) = 1 - 2P
```

- When P > 0.5 (sell side expensive): code **underestimates** edge → misses good trades
- When P < 0.5 (sell side cheap): code **overestimates** edge → enters bad trades
- When P = 0.5: metrics are equal (coincidentally correct)

**DB Verification (run `9bab5cf5`):**
- 304/436 positions (70%): coded entry_edge > actual `|K-P|` = edge overestimated
- 132/436 positions (30%): coded entry_edge < actual `|K-P|` = edge underestimated
- 1/436 position: approximately equal (P near 0.5)
