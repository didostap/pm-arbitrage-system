# Sprint Change Proposal — Exit Threshold Calibration Fix

**Date:** 2026-03-05
**Triggered by:** Epic 6.5 Paper Trading Validation
**Scope:** Minor — Direct implementation by development team
**Status:** Pending approval

---

## 1. Issue Summary

The exit monitor's threshold calibration mixes two incompatible reference frames. `ThresholdEvaluatorService.evaluate()` takes `initialEdge` — a resolution-frame metric computed at detection time (gross edge minus entry fees and gas) — and applies it as a stop-loss/take-profit bound against `currentPnl` — a mark-to-market metric computed from live close prices plus exit fees. The baseline for both thresholds is zero.

In reality, every position starts with a mark-to-market deficit equal to the bid-ask spread cost plus exit fees. This is because:

- Detection evaluates the **favorable** side of each order book (best bid for sell legs, best ask for buy legs)
- P&L evaluates the **unfavorable** side (best ask for sell legs to buy back, best bid for buy legs to sell)
- Exit fees are subtracted from the P&L but not accounted for in the threshold baseline

**Evidence from paper trading (2026-03-04):**

| Metric | Value |
|--------|-------|
| Position size | 141 contracts |
| Gross edge (resolution) | $0.04/contract ($5.64 total) |
| Net edge (after entry fees) | $0.025/contract ($3.52 total) |
| Immediate MtM P&L | -$5.63 |
| — Spread cost component | -$4.28 |
| — Exit fee component | -$1.35 |
| Stop-loss threshold | -$7.04 |
| Room to stop-loss at entry | $1.41 |
| Take-profit threshold | +$2.82 |
| Movement needed for TP from entry | $8.45 |
| SL proximity at entry | ~80% (displayed 91% after minor adverse movement) |

**Core problem:** Neither the detection subsystem nor the exit monitor is independently wrong. Detection correctly optimizes for resolution profit. The exit monitor correctly tracks mark-to-market. The bug is the interface between them — the threshold calibration applies resolution-frame inputs as bounds in the mark-to-market frame without any translation. Positions are designed to stop themselves out of profitable trades.

---

## 2. Impact Analysis

### Epic Impact

| Epic | Status | Impact | Change |
|------|--------|--------|--------|
| **6.5** (Paper Validation) | in-progress | **Direct** | Insert fix story (6.5.5i) before 6.5.5 and 6.5.6 |
| **5** (Execution & Exits) | done | Retroactive context | Story 5.4 implemented FR-EM-01 with the broken interface. No rollback — fix is forward-compatible |
| **7** (Dashboard) | in-progress | None | P&L display already correct; exit proximity bars auto-correct when thresholds change |
| **10** (Model-Driven Exits) | backlog | Positive downstream | Inherits correct baseline; five-criteria exits replace fixed thresholds entirely |
| All others | — | None | — |

### Artifact Impact

| Artifact | Change Needed |
|----------|--------------|
| **PRD (FR-EM-01)** | Clarify that fixed thresholds account for mark-to-market entry cost baseline |
| **Epics document** | New story 6.5.5i definition; clarifying note on Story 5.4 |
| **Sprint status YAML** | New story entry `6-5-5i-exit-threshold-calibration-fix` |
| **Architecture doc** | Brief note on exit threshold ↔ entry cost relationship in exit management section |
| **Prisma schema** | Two new nullable Decimal columns on `open_positions` |
| **Test suites** | Updated threshold evaluator, position enrichment, and exit monitor specs |

### Technical Impact

- **Schema migration:** Two columns added to `open_positions` (nullable for backward compat)
- **No new module dependencies:** Fix is contained within existing modules
- **No API contract changes:** Dashboard response shape unchanged
- **No connector changes:** Order book data already available during execution

---

## 3. Recommended Approach

**Direct Adjustment** — single story within Epic 6.5.

### What the fix does

At execution time, the order book is already in hand. Capture the close-side top-of-book price for each leg and persist it on the position record. The threshold evaluator then uses these observed prices to compute the exact mark-to-market entry cost, and offsets SL/TP thresholds from that baseline instead of from zero.

### Why this approach

- All required data is already available during execution — no new fetches, no estimation
- The fix is exact, not heuristic — it computes what MtM P&L would have been at t=0
- Forward-compatible with Epic 10 (model-driven exits replace fixed thresholds entirely)
- No rollback of existing work, no architectural changes, no new module dependencies

### Alternatives rejected

| Alternative | Reason |
|------------|--------|
| Exit fee offset only (no spread) | Solves 25% of the problem — positions still start at ~60% SL proximity |
| Rollback Story 5.4 | Destroys working infrastructure for no benefit |
| Defer to Epic 10 | Paper validation (6.5.5, 6.5.6) cannot pass with broken thresholds |

---

## 4. Detailed Change Proposals

### 4.1 New Story: 6.5.5i — Exit Threshold Calibration Fix

**As an operator,**
I want exit thresholds calibrated against the realistic mark-to-market baseline at entry,
So that stop-loss doesn't trigger on the natural entry cost of opening a position.

**Acceptance Criteria:**

**Schema:**

**Given** the Prisma schema for `OpenPosition`
**When** this story is complete
**Then** two new nullable Decimal fields exist: `entry_close_price_kalshi` and `entry_close_price_polymarket`
**And** a migration is created for the schema change
**And** existing positions (with null values) continue to function without error

**Execution — Close-Side Price Capture:**

**Given** the execution service has just filled a leg
**When** the order book for that leg's platform is available (already fetched for depth-aware sizing)
**Then** the close-side top-of-book price is captured:
- For a **buy** leg: the best **bid** price (what you'd sell at to close)
- For a **sell** leg: the best **ask** price (what you'd buy at to close)

**And** both close-side prices are persisted on the `OpenPosition` record alongside the existing entry data

**Execution — Empty Close-Side Book:**

**Given** the execution service has just filled a leg
**When** the close side of the order book is empty (no bids after a buy fill, or no asks after a sell fill)
**Then** the entry close price for that leg is set to the fill price (conservative zero-spread assumption)
**And** the threshold evaluator treats this as zero spread for that leg (exit fees still apply)

**Threshold Evaluator — Entry Cost Baseline:**

**Given** a position has `entryClosePriceKalshi` and `entryClosePricePolymarket` populated
**When** `ThresholdEvaluatorService.evaluate()` runs
**Then** the entry cost baseline is computed as:

```
// Spread cost (direction-aware, clamped to >= 0)
kalshiSpread:
  if kalshiSide === 'buy':  max(0, kalshiEntryFillPrice - entryClosePriceKalshi)
  if kalshiSide === 'sell': max(0, entryClosePriceKalshi - kalshiEntryFillPrice)

polymarketSpread:
  if polymarketSide === 'buy':  max(0, polymarketEntryFillPrice - entryClosePricePolymarket)
  if polymarketSide === 'sell': max(0, entryClosePricePolymarket - polymarketEntryFillPrice)

spreadCost = (kalshiSpread × kalshiSize) + (polymarketSpread × polymarketSize)

// Exit fees at close-side prices, using the same fee calculation as the live P&L formula.
// Use FinancialMath.calculateTakerFeeRate(price, feeSchedule) for each platform —
// this handles Kalshi's dynamic price-dependent fees and Polymarket's static fee model.
kalshiExitFeeRate    = FinancialMath.calculateTakerFeeRate(entryClosePriceKalshi, kalshiFeeSchedule)
polymarketExitFeeRate = FinancialMath.calculateTakerFeeRate(entryClosePricePolymarket, polymarketFeeSchedule)
entryExitFees = (entryClosePriceKalshi × kalshiSize × kalshiExitFeeRate)
              + (entryClosePricePolymarket × polymarketSize × polymarketExitFeeRate)

entryCostBaseline = -(spreadCost + entryExitFees)

// Offset thresholds
stopLossThreshold  = entryCostBaseline + (initialEdge × legSize × -2)
takeProfitThreshold = entryCostBaseline + (initialEdge × legSize × 0.80)
```

**And** spread values are clamped to zero minimum (if market moved favorably between fill and close-side capture, don't inflate thresholds with negative spread)

**Legacy Position Fallback:**

**Given** a position was opened before this fix (entry close prices are null)
**When** the threshold evaluator evaluates it
**Then** `entryCostBaseline` defaults to `0` (current behavior preserved)
**And** no error is thrown, no NaN produced

**Position Enrichment — Exit Proximity:**

**Given** `PositionEnrichmentService.enrich()` computes exit proximity for the dashboard
**When** entry close prices are available on the position
**Then** the same baseline-offset thresholds are used for SL/TP proximity calculation
**And** when entry close prices are null, proximity uses baseline = 0 (current behavior)

**Tests:**

**Given** the threshold evaluator test suite
**When** tests run
**Then** scenarios cover:
- Position with realistic spread + fees: SL proximity at entry is well below 50%
- Position with zero spread (close prices equal fill prices): only exit fees offset thresholds
- Negative spread (market moved favorably): clamped to zero, no threshold inflation
- Legacy position (null entry close prices): baseline = 0, current behavior preserved
- Empty close-side book: fill price used as fallback, zero spread for that leg
- All existing tests continue to pass

**And** `pnpm lint` reports zero errors

**Sequencing:** After 6.5.5h. Gates 6.5.5 (paper execution validation) and 6.5.6 (validation report).

**Design Note — Take-Profit via Early Exit:**

For positions where the combined bid-ask spread exceeds the net edge (as in the evidence position: 3-cent spread vs 2.5-cent net edge), the take-profit threshold remains negative after offset (e.g., -$2.81). This means MtM P&L would need to improve from the entry baseline but would still be nominally negative at TP trigger. This is expected and correct — such positions are not designed for profitable early exit. Their profit path is resolution (binary payout), not spread convergence. The TP threshold in these cases serves as a "best achievable early exit" rather than a profit target. The stop-loss, which is the critical threshold, is properly calibrated with full headroom.

### 4.2 PRD Update — FR-EM-01

**OLD:**
```
FR-EM-01 [MVP]: System shall monitor open positions continuously and trigger
exits based on fixed thresholds: take profit at 80% of initial edge captured,
stop loss at 2× initial edge, time-based exit 48 hours before contract resolution.
```

**NEW:**
```
FR-EM-01 [MVP]: System shall monitor open positions continuously and trigger
exits based on fixed thresholds: take profit at 80% of initial edge captured,
stop loss at 2× initial edge, time-based exit 48 hours before contract resolution.
Thresholds are offset from the mark-to-market entry cost baseline (bid-ask spread
cost + exit fees observed at execution time) so that the natural cost of opening
a position does not consume stop-loss headroom.
```

**Rationale:** The original FR was ambiguous about the threshold reference frame. The clarification makes explicit that thresholds account for the MtM entry cost, preventing the resolution-frame / MtM-frame mismatch.

### 4.3 Sprint Status Update

Add to Epic 6.5 section:
```yaml
6-5-5i-exit-threshold-calibration-fix: backlog
```

### 4.4 Epics Document — Story 5.4 Clarifying Note

Add note after Story 5.4 acceptance criteria:

```
> **Implementation Note (Epic 6.5 Retro):** The original threshold implementation
> anchored SL/TP at zero, not accounting for the mark-to-market entry cost
> (bid-ask spread + exit fees). Fixed in Story 6.5.5i — thresholds are now offset
> from the observed entry cost baseline. See sprint-change-proposal-2026-03-05.
```

---

## 5. Implementation Handoff

**Scope classification:** Minor — direct implementation by development agent.

| Role | Action |
|------|--------|
| **SM** | Finalize this proposal, update sprint status and epics doc upon approval |
| **Dev agent** | Implement Story 6.5.5i (schema, execution capture, threshold fix, enrichment mirror, tests) |
| **Operator** | Validate paper trading results post-fix — positions should start at <30% SL proximity |

**Success criteria:**
- Paper positions open with SL proximity well below 50% at entry
- No existing position evaluation breaks (null fallback verified)
- All tests pass, lint clean
- Paper validation (6.5.5) and report (6.5.6) can proceed

**Estimated impact on position from evidence:**
- Entry cost baseline: ~-$5.63 (spread $4.28 + fees $1.35)
- New SL threshold: -$5.63 + (-$7.04) = **-$12.67** → **$7.04 of room from entry**
- New TP threshold: -$5.63 + $2.82 = **-$2.81** → **$2.82 of movement needed for TP from entry**
- SL proximity at entry: ~0% (thresholds properly calibrated)
