# Story 6.5.5h: Execution Equal Leg Sizing & Threshold Accuracy

Status: done

## Story

As an operator,
I want arbitrage positions to have equal contract counts on both legs and exit thresholds calibrated to actual exposure,
so that positions are properly hedged (guaranteed profit regardless of outcome) and stop-loss triggers reflect real risk.

## Background / Root Cause

A paper position on "Will Republicans lose the H..." was opened with Polymarket BUY 457.14 shares @ 0.17 and Kalshi SELL 108 contracts @ 0.21. Despite a 2.5% initial edge (0.02498), the position immediately hit -$13.02 P&L and triggered stop-loss at 100%.

**Three cascading bugs:**

1. **Sizing formula produces unequal contract counts** — `budget/price` gives different quantities when prices differ (0.17 vs 0.21). For binary options arbitrage, equal contract counts guarantee profit regardless of outcome.
2. **No cross-leg size equalization after depth capping** — when one leg is depth-limited, the other leg is not reduced to match, amplifying the mismatch.
3. **Sell-side sizing ignores collateral cost** — selling at price `p` requires `(1-p)` collateral per contract, but the formula divides by `p`, overestimating affordable contracts.

**Math proof:** With equal sizes (108 each), both YES and NO outcomes yield +$4.32. With 457 vs 108, NO outcome yields -$55.01 — not an arbitrage.

## Acceptance Criteria

1. **Given** an arbitrage opportunity passes risk validation with a reserved capital budget
   **When** the execution service calculates leg sizes
   **Then** ideal sizes use collateral-aware formulas: `floor(budget / price)` for buy legs, `floor(budget / (1 - price))` for sell legs
   **And** each leg's ideal size is independently capped by available order book depth
   **And** after depth capping, both legs are equalized to the smaller: `finalSize = min(primaryCapped, secondaryCapped)`
   **And** edge is re-validated at the equalized size before proceeding

2. **Given** both legs are equalized to the same contract count
   **When** the execution service submits orders
   **Then** a runtime invariant asserts `primarySize === secondarySize` before order submission
   **And** if the invariant fails, execution is aborted with an `ExecutionError` (code 2xxx) and the violation is logged at error level
   **And** no orders are submitted to either platform

3. **Given** a position is opened with equal leg sizes
   **When** the threshold evaluator calculates current P&L and exit proximity
   **Then** the evaluator uses the single shared leg size directly (removing the `minLegSize = Decimal.min(kalshiSize, polymarketSize)` workaround)
   **And** `currentEdge = currentPnl / legSize` uses the shared size
   **And** stop-loss and take-profit thresholds use the shared size

4. **Given** the stop-loss threshold is defined as `-(2 x initialEdge x legSize)`
   **When** the threshold is evaluated against real market conditions
   **Then** the implementation includes a documented analysis of whether `2 x initialEdge` is an appropriate risk bound
   **And** the analysis recommends keeping, adjusting, or making configurable the stop-loss multiplier, with the decision recorded in this artifact

5. **Given** the fix changes position sizing semantics
   **When** regression tests are written
   **Then** tests assert both legs in a position have equal contract counts
   **And** tests verify guaranteed profit under both YES and NO outcomes for a correctly sized position
   **And** tests verify stop-loss threshold accurately bounds actual loss exposure at the equalized size
   **And** existing depth-aware sizing tests are updated to reflect the equal-size constraint

6. **Given** the equalized size may be smaller than either leg's ideal size
   **When** the execution service re-validates the edge at the equalized size
   **Then** the same fee-inclusive calculation as initial opportunity detection is used (platform-specific fee schedules, gas estimate)
   **And** if the re-validated edge falls below `DETECTION_MIN_EDGE_THRESHOLD` (default 0.008), execution is rejected with `EDGE_ERODED_BY_SIZE` and triggers single-leg handling

## Tasks / Subtasks

- [x] Task 1: Fix primary leg sizing with collateral-aware formula (AC: #1)
  - [x] 1.1 In `execution.service.ts` `execute()` method (~line 220), change primary ideal size calculation: if `primarySide === 'buy'` use `floor(reservedCapitalUsd / targetPrice)` (unchanged), if `primarySide === 'sell'` use `floor(reservedCapitalUsd / (1 - targetPrice))` — selling at price `p` requires `(1-p)` collateral per contract
  - [x] 1.2 Write tests: buy-side sizing unchanged from current behavior; sell-side sizing uses `(1-price)` denominator (e.g., sell @ 0.21 → `floor(100 / 0.79) = 126` not `floor(100 / 0.21) = 476`)

- [x] Task 2: Fix secondary leg sizing with collateral-aware formula (AC: #1)
  - [x] 2.1 In `execute()` (~line 330), change secondary ideal size: if `secondarySide === 'buy'` use `floor(reservedCapitalUsd / secondaryTargetPrice)`, if `secondarySide === 'sell'` use `floor(reservedCapitalUsd / (1 - secondaryTargetPrice))`
  - [x] 2.2 Write tests: secondary leg uses collateral-aware formula independently

- [x] Task 3: Add cross-leg equalization after depth capping (AC: #1, #6)
  - [x] 3.1 After both legs are independently depth-capped (primary `targetSize`, secondary `secondarySize`), add equalization: `const equalizedSize = Math.min(targetSize, secondarySize)`
  - [x] 3.2 Apply `equalizedSize` to BOTH legs — set `targetSize = equalizedSize` and `secondarySize = equalizedSize`
  - [x] 3.3 **Skip separate minFillRatio check on equalized size.** The `minFillRatio` threshold was designed for single-leg depth scenarios (Story 6.5.5b) — each leg already passed its own `minFillRatio` check before equalization. The equalized size is guaranteed to be at least as large as the smaller capped size, which already passed. The meaningful post-equalization check is edge re-validation (Task 3.4), which determines if the trade is profitable at the reduced size. Do NOT add a redundant threshold check here — it could reject valid trades where equalization reduces size below `minFillRatio` of the larger leg's ideal but the trade is still profitable
  - [x] 3.4 Re-validate edge at equalized size using existing edge re-validation logic (recalculate gas fraction at reduced position size). If edge < `minEdgeThreshold` → `EDGE_ERODED_BY_SIZE` → clean rejection (pre-submission, not single-leg)
  - [x] 3.5 Update `actualCapitalUsed` calculation: for buy legs `equalizedSize * price`, for sell legs `equalizedSize * (1 - price)` (collateral-aware)
  - [x] 3.6 Write tests: asymmetric depth (200 vs 150) → both equalized to 150; both above ideal → both at min(idealPrimary, idealSecondary); edge re-validation at equalized size passes/fails

- [x] Task 4: Add runtime invariant before order submission (AC: #2)
  - [x] 4.1 Add guard immediately before primary order submission: `if (targetSize !== secondarySize) { return { success: false, partialFill: false, error: ExecutionError(EXECUTION_ERROR_CODES.LEG_SIZE_MISMATCH, ...) } }` — added new error code `LEG_SIZE_MISMATCH: 2011` to `EXECUTION_ERROR_CODES`
  - [x] 4.2 Log at error level with both sizes, pair ID, and both platform identifiers
  - [x] 4.3 Return early with `{ success: false, partialFill: false, error }` — no orders submitted
  - [x] 4.4 Write tests: invariant passes when sizes equal (implicitly verified by every successful execution test). NOTE: fail-path test for LEG_SIZE_MISMATCH is unreachable by construction — equalization sets `targetSize = secondarySize = equalizedSize` 3 lines above the invariant check. The invariant is a regression safety net, not reachable business logic.

- [x] Task 5: Clean up threshold evaluator (AC: #3)
  - [x] 5.1 In `threshold-evaluator.service.ts` `evaluate()` method, replaced `const minLegSize = Decimal.min(kalshiSize, polymarketSize)` with `const legSize = kalshiSize`. Added NestJS Logger with debug assertion: `if (!kalshiSize.eq(polymarketSize)) this.logger.error(...)`
  - [x] 5.2 Replaced all downstream references from `minLegSize` to `legSize`
  - [x] 5.3 Updated tests to pass equal sizes for both legs
  - [x] 5.4 Written tests: equal sizes → correct P&L with legSize; assertion fires when sizes differ (logger.error spy verification)

- [x] Task 6: Analyze stop-loss multiplier (AC: #4)
  - [x] 6.1 Documented analysis in code comment: 2x multiplier is conservative default for binary options arbitrage — small initial edges (0.8%-5%), bounded prices [0,1], consistent with mean-reversion stop-loss practice (2-3x entry signal)
  - [x] 6.2 Recommendation: keep current 2x default, add TODO for `EXIT_STOP_LOSS_MULTIPLIER` env var for future tuning during paper trading validation
  - [x] 6.3 Added rationale comment + TODO in threshold-evaluator.service.ts

- [x] Task 7: Update position persistence for equal sizes (AC: #5)
  - [x] 7.1 In `execute()` position creation, `sizes` JSONB stores `equalizedSize.toString()` for both legs
  - [x] 7.2 Written tests: persisted position has equal `kalshi` and `polymarket` sizes

- [x] Task 8: Update existing depth-aware sizing tests (AC: #5)
  - [x] 8.1 Updated all 10 existing depth-aware tests from Story 6.5.5b to reflect equalization + collateral-aware behavior
  - [x] 8.2 Existing happy-path tests: collateral-aware formula for symmetric prices (buy @ 0.45, sell @ 0.55) produces equal ideal sizes (222 each), so no behavioral change
  - [x] 8.3 Written guaranteed profit tests: YES outcome and NO outcome both yield positive P&L with equal sizes
  - [x] 8.4 Written explicit no-op equalization test: symmetric case produces identical sizes, equalization is a no-op

- [x] Task 9: Run full test suite and lint (AC: #5)
  - [x] 9.1 `pnpm test` — 1,372 tests pass (80 test files), up from 1,358 baseline (+14 net new tests)
  - [x] 9.2 `pnpm lint` — zero errors

## Dev Notes

### Architecture Compliance

- **Module boundaries preserved.** Changes span only: `modules/execution/` (sizing logic) and `modules/exit-management/` (threshold evaluator). Both in the allowed hot path (`execution → risk-management` is allowed; exit-management → connectors is allowed).
- **No forbidden imports.** No new cross-module dependencies.
- **No new modules, no schema changes, no new dependencies, no migration needed.**
- **Financial math:** All sizing and collateral calculations MUST use `decimal.js`. `Math.min()` is only used on integer contract counts (already converted from Decimal to number) — this is safe.
- **Error hierarchy:** New `LEG_SIZE_MISMATCH` error code extends `EXECUTION_ERROR_CODES` (2xxx range). Uses existing `ExecutionError` class.
- **Events:** No new events required. Existing `ExecutionFailedEvent` covers the invariant-failure path.

### Key Design Decisions

1. **Collateral-aware sizing formula.** For binary options: buying at price `p` costs `p` per contract. Selling at price `p` requires posting `(1-p)` collateral per contract. The current formula `budget/price` is only correct for buy legs. Sell legs must use `budget/(1-price)`.

2. **Equalization AFTER depth capping, not before.** Each leg's ideal size is calculated independently (may differ due to different prices/collateral). Each is depth-capped independently. THEN both are equalized to `min(primaryCapped, secondaryCapped)`. This maximizes the common size given available liquidity.

3. **Runtime invariant is a safety net, not business logic.** After equalization, sizes ARE equal by construction. The invariant (`primarySize === secondarySize`) guards against future regressions — it's an O(1) check before order submission. If it fires, something broke the equalization logic.

4. **Threshold evaluator cleanup, not rewrite.** The `Decimal.min()` call becomes a no-op since sizes are guaranteed equal. Replace with direct use of either size. Add a debug assertion to catch callers that somehow pass unequal sizes (defensive).

5. **Edge re-validation uses the existing mechanism** from Story 6.5.5b — recalculate gas fraction at reduced position size. The equalized size may be smaller than either ideal size, so gas per contract is higher. Same `EDGE_ERODED_BY_SIZE` error code.

### Collateral-Aware Sizing — Formula Reference

```
Buy leg:  idealSize = floor(reservedCapitalUsd / buyPrice)
Sell leg: idealSize = floor(reservedCapitalUsd / (1 - sellPrice))

After depth capping:
  primaryCapped  = min(primaryIdealSize, primaryAvailableDepth)
  secondaryCapped = min(secondaryIdealSize, secondaryAvailableDepth)

Equalization:
  finalSize = min(primaryCapped, secondaryCapped)

Capital used:
  Buy leg capital  = finalSize × buyPrice
  Sell leg capital = finalSize × (1 - sellPrice)
  totalCapitalUsed = buyLegCapital + sellLegCapital
```

**Example (from the bug):**

- Budget: $100, Buy @ 0.17, Sell @ 0.21
- Buy ideal: `floor(100/0.17)` = 588
- Sell ideal: `floor(100/0.79)` = 126 (collateral = 1-0.21 = 0.79)
- Equalized (no depth cap): `min(588, 126)` = 126
- Capital: buy = 126 × 0.17 = $21.42, sell = 126 × 0.79 = $99.54
- Both YES and NO outcomes: +$5.04 each (true arbitrage)

### Current Code — Exact Locations to Modify

**`execution.service.ts` (693 lines total):**

| Location                    | Current Code                                                                                                          | Change                                                                                                                                    |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| ~Line 220                   | `const idealSize = new Decimal(reservation.reservedCapitalUsd).div(targetPrice).floor().toNumber()`                   | Add collateral-awareness: if sell side, divide by `(1 - targetPrice)`                                                                     |
| ~Line 236                   | `const targetSize = Math.min(idealSize, primaryAvailableDepth)`                                                       | Keep (depth capping unchanged)                                                                                                            |
| ~Line 330                   | `const secondaryIdealSize = new Decimal(reservation.reservedCapitalUsd).div(secondaryTargetPrice).floor().toNumber()` | Add collateral-awareness: if sell side, divide by `(1 - secondaryTargetPrice)`                                                            |
| ~Line 346                   | `const secondarySize = Math.min(secondaryIdealSize, secondaryAvailableDepth)`                                         | Keep (depth capping unchanged)                                                                                                            |
| NEW after ~346              | (none)                                                                                                                | Add equalization: `const equalizedSize = Math.min(targetSize, secondarySize); targetSize = equalizedSize; secondarySize = equalizedSize;` |
| NEW before order submission | (none)                                                                                                                | Add runtime invariant: `if (targetSize !== secondarySize) throw ExecutionError(LEG_SIZE_MISMATCH)`                                        |
| ~Line 370-430               | Edge re-validation using `smallerLegSize`                                                                             | Now `smallerLegSize === equalizedSize` — logic unchanged but operates on equalized value                                                  |
| ~Line 560                   | `sizes: { kalshi: kalshiSize.toString(), polymarket: polymarketSize.toString() }`                                     | Both use `equalizedSize`                                                                                                                  |

**`threshold-evaluator.service.ts` (138 lines total):**

| Location    | Current Code                                                 | Change                                                                |
| ----------- | ------------------------------------------------------------ | --------------------------------------------------------------------- |
| ~Line 70    | `const minLegSize = Decimal.min(kalshiSize, polymarketSize)` | Replace with `const legSize = kalshiSize` + debug assertion           |
| ~Line 71    | `const scaledInitialEdge = initialEdge.mul(minLegSize)`      | Use `legSize`                                                         |
| ~Line 72-74 | `currentPnl.div(minLegSize.isZero() ? ...)`                  | Use `legSize`                                                         |
| ~Line 75-76 | `capturedEdgePercent` uses `scaledInitialEdge`               | Already uses `scaledInitialEdge` which now uses `legSize` — no change |

**`error-codes.ts`:**

| Change                  | Details                                                |
| ----------------------- | ------------------------------------------------------ |
| Add `LEG_SIZE_MISMATCH` | New error code in `EXECUTION_ERROR_CODES` (2xxx range) |

### Sequencing & Dependencies

- **Depends on:** Stories 6.5.5a through 6.5.5g (all done)
- **Blocks:** Story 6.5.5 (Paper Execution Validation) — cannot restart 5-day clock until this deploys
- **No schema changes** — `open_positions.sizes` JSONB will now contain equal values but the column type is unchanged

### IMPORTANT: Execution Flow & Order of Operations

The current execution flow submits primary BEFORE checking secondary depth (architectural constraint from Story 5.1). Story 6.5.5h changes this:

**Current flow:**

1. Calculate primary ideal size → depth cap → submit primary order
2. Calculate secondary ideal size → depth cap → submit secondary order
3. Record position with potentially unequal sizes

**New flow (this story):**

1. Calculate primary ideal size (collateral-aware) → depth cap primary
2. Calculate secondary ideal size (collateral-aware) → depth cap secondary
3. Equalize: `finalSize = min(primaryCapped, secondaryCapped)`
4. Re-validate edge at equalized size
5. Runtime invariant: assert both sizes equal
6. Submit primary order at `finalSize`
7. Submit secondary order at `finalSize`
8. Record position with equal sizes

**Critical change:** Both depth queries happen BEFORE either order is submitted. This is a departure from the previous "submit primary first, then check secondary depth" pattern. This is necessary because equalization requires knowing both depths. Correctness beats speed for this fix.

**Safety analysis of moving secondary depth query earlier:**

- `getAvailableDepth()` is a read-only order book query — no side effects
- Moving it earlier does not change any state
- The order book may change between query and submission (inherent to any DEX interaction and already accepted)

**Race window tradeoff:** By querying both depths upfront, the time window between primary depth query and primary order submission widens slightly. On thin books, someone else might fill those levels in the gap. This is not a blocker — the same race exists today and is inherent to non-atomic cross-platform execution. However, if partial fills increase after deployment, this wider window is a likely contributor. Future Story 10-4 (pre-flight dual-depth architecture) can address this with tighter atomic-like patterns.

### Previous Story Intelligence

**Story 6.5.5b (Depth-Aware Position Sizing) — origin of the bug:**

- Introduced independent `budget/price` formula for each leg
- Explicitly deferred equal-size execution to Story 10-4 (pre-flight dual-depth check)
- However, this story (6.5.5h) provides a simpler fix: query both depths first, equalize, then submit. True pre-flight architecture (Story 10-4) adds additional sophistication (adaptive retry, partial fills).
- `getAvailableDepth()` method already extracted and tested — reuse as-is
- `minFillRatio` config already exists (default 0.25) — reuse
- `EDGE_ERODED_BY_SIZE` error code already exists — reuse
- `adjustReservation()` already exists on `IRiskManager` — reuse for adjusted capital
- Test data: `makeReservation()` → $100, prices 0.45/0.55, order books qty 500

**Story 6.5.5g (Kalshi Dynamic Fee Correction) — most recent:**

- 1,270 tests passing (current baseline)
- `FinancialMath.calculateTakerFeeRate()` centralized helper — use for edge re-validation
- `takerFeeForPrice` callback on `FeeSchedule` — dynamic fees are price-dependent, must use at equalized size's price point

**Story 6.5.5e (Paper Mode Exit Monitor Fix):**

- Exit monitor now mode-aware — paper positions flow through complete lifecycle
- Threshold evaluator changes in this story affect exit monitoring for all positions

**Story 6.5.5f (Detection Gross Edge Formula Fix):**

- Edge formula: `sellPrice - buyPrice` (signed, not absolute value)
- Edge re-validation in execution must use same formula

### Git Intelligence

Recent engine commits (on `main` branch, merges from `epic-7`):

```
a1f18c8 feat: add performance tracking
09f5b96 feat: implement match approval/rejection
9a37f3b feat: add position enrichment service
78da8f6 feat: implement dynamic taker fee calculation for Kalshi
00ed663 refactor: update financial math for new gross edge formula
ff3d8cd feat: enhance Kalshi connector and exit monitor with paper mode
```

Most relevant: `78da8f6` (dynamic Kalshi fees) and `00ed663` (gross edge formula). Both feed into edge re-validation at equalized size.

### File Structure — Files to Modify

| File                                                              | Change                                                                                                 |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `src/modules/execution/execution.service.ts`                      | Collateral-aware sizing, equalization after depth capping, runtime invariant, updated capital tracking |
| `src/modules/execution/execution.service.spec.ts`                 | New tests for collateral-aware sizing, equalization, invariant, profit verification                    |
| `src/modules/exit-management/threshold-evaluator.service.ts`      | Replace `minLegSize` with `legSize`, add debug assertion                                               |
| `src/modules/exit-management/threshold-evaluator.service.spec.ts` | Update to pass equal sizes, add assertion test                                                         |
| `src/common/constants/error-codes.ts`                             | Add `LEG_SIZE_MISMATCH` to `EXECUTION_ERROR_CODES`                                                     |

**No new files. No schema changes. No new dependencies. No migration needed.**

### Scope Guard

This story is strictly scoped to:

1. Collateral-aware sizing formula for sell legs
2. Cross-leg equalization after depth capping
3. Runtime invariant before order submission
4. Threshold evaluator cleanup (remove `minLegSize` workaround)
5. Stop-loss multiplier analysis (document only, possibly make configurable)
6. Regression tests for equal leg sizing and guaranteed profit

Do NOT:

- Implement pre-flight dual-depth architecture with adaptive retry (Story 10-4)
- Modify `IRiskManager` interface (already has `adjustReservation`)
- Add partial fill order types (Epic 10)
- Change position sizing limits in `RiskManagerService.reserveBudget()` (stays at 3% bankroll)
- Add confidence-adjusted sizing (Story 9-3)
- Modify detection service logic (already fixed in 6.5.5f)
- Change the `FeeSchedule` interface or `FinancialMath` helpers (already correct from 6.5.5g)
- Clean up phantom DB records (operator task)

### Project Structure Notes

- All source changes within `pm-arbitrage-engine/src/` — no root repo changes needed (except this story file)
- Files follow existing kebab-case naming convention
- Tests co-located with source (`.spec.ts` suffix)
- This is a **dual-repo** project — engine changes require separate commit from story file updates

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-04-equal-leg-sizing.md] — Approved sprint change proposal with full root cause analysis, math proofs, and detailed acceptance criteria
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts:220] — Primary leg sizing formula (current: `reservedCapitalUsd / targetPrice`)
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts:330] — Secondary leg sizing formula (current: `reservedCapitalUsd / secondaryTargetPrice`)
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts:210-215] — Side determination logic (`primarySide`, `secondarySide`, `targetPrice`, `secondaryTargetPrice`)
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts:695-739] — `getAvailableDepth()` method (reuse as-is)
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts:370-430] — Edge re-validation after depth capping (reuse pattern)
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts:560] — Position persistence with `sizes` JSONB
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts:70-76] — `minLegSize` workaround to replace
- [Source: pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts:126-138] — `calculateLegPnl()` (unchanged)
- [Source: _bmad-output/implementation-artifacts/6-5-5b-depth-aware-position-sizing.md] — Story that introduced the bug (independent sizing per leg)
- [Source: _bmad-output/implementation-artifacts/6-5-5g-kalshi-dynamic-fee-correction.md] — Previous story (1,270 tests baseline, dynamic fee helper)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

N/A

### Completion Notes List

- All 9 tasks completed. 13 new tests added, 10 existing tests updated. Total: 1,372 tests passing.
- Flow restructured: both depth queries BEFORE either order submission. Pre-submission failures now return clean rejection (partialFill: false) instead of single-leg exposure.
- Lad design review feedback addressed: documented division-by-zero risk for sell price >= 1.0, added JSDoc invariant on ThresholdEvalInput interface.
- Stop-loss multiplier analysis: 2x default is appropriate, documented rationale + TODO for future configurability.
- AC #6 note: story text says "triggers single-leg handling" for edge re-validation failure, but since this now happens pre-submission, it's a clean rejection — correct behavior since no orders have been submitted yet.
- **Code Review Fixes (Reviewer: Claude Opus 4.6):**
  - [H1] Added explicit guard for non-positive collateral divisor (sell price >= 1.0) on both primary and secondary legs — prevents Infinity cascading through sizing logic
  - [M1] Updated Task 4.4 to document LEG_SIZE_MISMATCH fail-path as unreachable by construction (regression safety net only)
  - [M2] Made edge re-validation `conservativePositionSizeUsd` collateral-aware — reuses `primaryDivisor`/`secondaryDivisor` for consistency with `actualCapitalUsed`
  - 2 new tests for divisor guard (secondary sell@1.0, primary sell@1.0). Total: 1,374 tests passing.

### File List

| File                                                              | Change                                                                                                                                                                                                   |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/common/errors/execution-error.ts`                            | Added `LEG_SIZE_MISMATCH: 2011` to `EXECUTION_ERROR_CODES`                                                                                                                                               |
| `src/modules/execution/execution.service.ts`                      | Major restructure of `execute()`: collateral-aware sizing, both depth checks before submission, cross-leg equalization, runtime invariant, collateral-aware capital tracking, equal position persistence. **Review fix:** divisor guards for sell price >= 1.0, collateral-aware `conservativePositionSizeUsd` |
| `src/modules/execution/execution.service.spec.ts`                 | 15 new tests in "equal leg sizing" describe block + 10 existing tests updated. **Review fix:** +2 divisor guard tests, LEG_SIZE_MISMATCH untestability documented                                                                                                                            |
| `src/modules/exit-management/threshold-evaluator.service.ts`      | Added NestJS Logger, replaced `minLegSize` with `legSize = kalshiSize`, debug assertion for unequal sizes, stop-loss multiplier rationale comment, JSDoc on interface                                    |
| `src/modules/exit-management/threshold-evaluator.service.spec.ts` | Replaced "unequal leg sizes" test with assertion verification test, added legSize test, logger spy setup                                                                                                 |
