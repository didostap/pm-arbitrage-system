# Sprint Change Proposal: Execution Equal Leg Sizing & Threshold Accuracy

**Date:** 2026-03-04
**Triggered by:** Story 6.5.5 (Paper Execution Validation)
**Scope:** Minor — direct implementation by dev team
**Status:** Pending approval

---

## 1. Issue Summary

During Story 6.5.5 (Paper Execution Validation), a paper position on "Will Republicans lose the H..." was opened with Polymarket BUY 457.14 shares @ 0.17 and Kalshi SELL 108 contracts @ 0.21. Despite a 2.5% initial edge (0.02498), the position immediately hit -$13.02 P&L and triggered the stop-loss at 100%.

**Root cause:** The execution service (`execution.service.ts`) sizes each leg independently using `floor(reservedCapitalUsd / targetPrice)`, producing wildly different contract counts per leg. For binary options arbitrage, both legs must have equal contract counts to create a proper hedge. The 4.2x size mismatch (457 vs 108) created directional exposure instead of a hedged position.

**Three cascading bugs identified:**

1. **Sizing formula produces unequal contract counts** — `budget/price` gives different quantities when prices differ (0.17 vs 0.21). For binary options arbitrage, equal contract counts guarantee profit regardless of outcome.
2. **No cross-leg size equalization after depth capping** — when one leg is depth-limited, the other leg is not reduced to match, amplifying the mismatch.
3. **Sell-side sizing ignores collateral cost** — selling at price `p` requires `(1-p)` collateral per contract, but the formula divides by `p`, overestimating affordable contracts.

**Evidence:**
- Database position `cc945929`: Poly BUY 457.14 @ 0.17, Kalshi SELL 108 @ 0.21
- Math proof: with equal sizes (108 each), both YES and NO outcomes yield +$4.32. With 457 vs 108, NO outcome yields -$55.01 — not an arbitrage.
- Stop-loss threshold was -$5.40 (2 x 0.025 x 108), instantly exceeded because the 457-share Poly leg dominated P&L.

---

## 2. Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| **Epic 6.5** (Paper Trading Validation) | **Direct** | New fix story 6.5.5h required before 6.5.5 can resume. 5-day validation clock resets. |
| **Epic 7** (Dashboard) | None | Dashboard reads engine-calculated data; fix corrects the source. |
| **Epic 9** (Advanced Risk) | Low | Story 9.3 (Confidence-Adjusted Sizing) will build on corrected formula. No blocking impact. |
| **Epic 10** (Model-Driven Exits) | Low | Story 10.2 (Five-Criteria Exits) builds on threshold evaluator. Base P&L is corrected first. |
| All other epics | None | — |

### Story Impact

| Story | Status | Change |
|-------|--------|--------|
| 6.5.5h (new) | backlog | New story: fix equal leg sizing, collateral-aware formula, runtime invariant, threshold evaluator cleanup |
| 6.5.5 (Paper Execution Validation) | backlog | Blocked until 6.5.5h deploys. 5-day clock restarts. |
| 6.5.5b (Depth-Aware Position Sizing) | done | Origin of the flawed `budget/price` formula. No rollback — fix corrects forward. |

### Artifact Conflicts

| Artifact | Conflict | Action |
|----------|----------|--------|
| PRD | None — requirements are correct, implementation deviated | No changes |
| Architecture | None — module boundaries and patterns intact | No changes |
| UX Design | None — dashboard displays engine data correctly | No changes |
| Epics doc | Story 6.5.5h must be added to Epic 6.5 | Add story |
| Sprint status | New entry for 6.5.5h | Add entry |
| Test coverage | Missing assertions for equal contract counts and bilateral P&L | New tests in fix story |

### Technical Impact

- **Files modified:** `execution.service.ts` (sizing logic), `threshold-evaluator.service.ts` (P&L normalization)
- **Schema changes:** None. `open_positions.sizes` JSONB will now contain equal values.
- **Deployment:** Standard `pm2 restart` on VPS after fix.

---

## 3. Recommended Approach

**Selected path:** Direct Adjustment — new Story 6.5.5h within Epic 6.5.

**Rationale:**
- Bugs are well-localized to 2 source files, ~3 methods
- Fix is conceptually clear: equal contract counts for proper arbitrage hedging
- Follows the established 6.5.5x bug-fix naming pattern (a through g already exist)
- Low effort (~1 day), low risk, no architectural changes
- Paper validation framework worked exactly as designed — it caught a critical bug before production

**Alternatives considered and rejected:**
- **Rollback of 6.5.5b:** Destructive — would lose valid depth-awareness and require re-implementing it correctly anyway. High risk.
- **MVP scope reduction:** Unnecessary — MVP completed at Epic 6. This is a validation-phase fix.

**Effort estimate:** Low (1 day for implementation + testing)
**Risk level:** Low (contained changes, no module boundary or schema modifications)
**Timeline impact:** ~6 days added to Epic 6.5 (1 day fix + 5 day validation restart)

---

## 4. Detailed Change Proposals

### 4.1 Story Addition: Epic 6.5

**Add Story 6.5.5h: Execution Equal Leg Sizing & Threshold Accuracy**

As an operator,
I want arbitrage positions to have equal contract counts on both legs and exit thresholds calibrated to actual exposure,
So that positions are properly hedged (guaranteed profit regardless of outcome) and stop-loss triggers reflect real risk.

**Acceptance Criteria:**

**Given** an arbitrage opportunity passes risk validation with a reserved capital budget
**When** the execution service calculates leg sizes
**Then** ideal sizes use collateral-aware formulas: `floor(budget / price)` for buy legs, `floor(budget / (1 - price))` for sell legs
**And** each leg's ideal size is independently capped by available order book depth
**And** after depth capping, both legs are equalized to the smaller: `finalSize = min(primaryCapped, secondaryCapped)`
**And** edge is re-validated at the equalized size before proceeding

**Given** both legs are equalized to the same contract count
**When** the execution service submits orders
**Then** a runtime invariant asserts `primarySize === secondarySize` before order submission
**And** if the invariant fails, execution is aborted with an `ExecutionError` (code 2xxx) and the violation is logged at error level
**And** no orders are submitted to either platform

**Given** a position is opened with equal leg sizes
**When** the threshold evaluator calculates current P&L and exit proximity
**Then** the evaluator uses the single shared leg size directly (removing the `minLegSize = Decimal.min(kalshiSize, polymarketSize)` workaround)
**And** `currentEdge = currentPnl / legSize` uses the shared size
**And** stop-loss and take-profit thresholds use the shared size

**Given** the stop-loss threshold is defined as `-(2 x initialEdge x legSize)`
**When** the threshold is evaluated against real market conditions
**Then** the story implementation includes a documented analysis of whether `2 x initialEdge` is an appropriate risk bound — specifically: with a typical 2-3 cent edge and 100+ contract positions, this threshold triggers on a ~2.5-cent adverse move per side, which may be too tight for normal market volatility
**And** the analysis recommends keeping, adjusting, or making configurable the stop-loss multiplier, with the decision recorded in the implementation artifact

**Given** the fix changes position sizing semantics
**When** regression tests are written
**Then** tests assert both legs in a position have equal contract counts
**And** tests verify guaranteed profit under both YES and NO outcomes for a correctly sized position
**And** tests verify stop-loss threshold accurately bounds actual loss exposure at the equalized size
**And** existing depth-aware sizing tests are updated to reflect the equal-size constraint

**Technical Notes:**
- Primary file: `src/modules/execution/execution.service.ts` — `execute()` method, lines ~220 (primary sizing) and ~330 (secondary sizing)
- Secondary file: `src/modules/exit-management/threshold-evaluator.service.ts` — `evaluate()` method
- Collateral-aware formula: buy side = `budget / price`, sell side = `budget / (1 - price)`
- Sizing flow: calculate each leg's ideal size independently -> apply depth caps per leg -> equalize once: `finalSize = min(primaryCapped, secondaryCapped)` -> re-validate edge at final size. The initial ideal sizes will differ (different prices/collateral), but the pre-depth-cap min() is unnecessary — depth capping + one equalization is sufficient.
- Runtime invariant: add a guard `if (primarySize !== secondarySize)` after equalization and before order submission. This is a cheap O(1) check that prevents any future regression from reaching the order book.
- The `open_positions.sizes` JSONB will now contain equal values for both legs (e.g., `{ kalshi: "108", polymarket: "108" }`)
- Edge re-validation after equalization must use the same fee-inclusive calculation as initial opportunity detection (platform-specific fee schedules, gas estimate). Kalshi and Polymarket have different fee models — re-validating on raw prices would approve positions where fees eat the edge at the reduced size.
- Threshold evaluator cleanup: replace `Decimal.min(kalshiSize, polymarketSize)` with direct use of either size (they're equal). This removes a band-aid that masked the sizing bug.

**Sequencing:** After 6.5.5g (done), before 6.5.5 (Paper Execution Validation). Must complete and deploy before 5-day validation clock restarts.

**Previous Story Intelligence:**
- Story 6.5.5b (Depth-Aware Position Sizing) introduced the independent `budget/price` formula — this story corrects its core assumption
- Story 5.4 (Exit Monitoring) defined the threshold evaluator — the `minLegSize` normalization was a workaround for the unequal sizing, not an intentional design choice
- Story 5.1 (Order Submission) defined the position persistence schema — `sizes` JSONB field, no schema change needed
- Stop-loss multiplier (2x) was set in Story 5.4 without calibration against real market tick sizes — this story flags it for review

### 4.2 Sprint Status Update

```yaml
# Add after 6-5-5g-kalshi-dynamic-fee-correction: done
6-5-5h-execution-equal-leg-sizing: backlog
```

---

## 5. Implementation Handoff

**Change scope classification:** Minor — direct implementation by development team.

| Recipient | Responsibility |
|-----------|---------------|
| **Dev Agent** | Implement Story 6.5.5h: fix execution sizing, add runtime invariant, clean up threshold evaluator, write regression tests, analyze stop-loss multiplier, run lint/test, deploy to VPS |
| **SM (Bob)** | Update sprint-status.yaml, add story to epics doc |
| **Arbi (Operator)** | Approve this proposal, verify fix on VPS, restart 5-day validation window for Story 6.5.5 |

**Success criteria:**
- All existing tests pass + new regression tests for equal leg sizing
- Runtime invariant prevents any future unequal-size execution
- Paper position opened on VPS shows equal contract counts on both legs
- Stop-loss multiplier analysis documented in implementation artifact
- `pnpm lint` clean, `pnpm test` green

**Next steps after approval:**
1. SM updates epics doc and sprint-status.yaml
2. Dev agent implements Story 6.5.5h
3. Deploy fix to VPS
4. Restart Story 6.5.5 (Paper Execution Validation) with fresh 5-day window
