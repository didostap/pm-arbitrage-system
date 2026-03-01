# Story 6.5.5k: Exit Path Depth Verification & Partial Fill Handling

Status: done

## Story

As an **operator**,
I want exit orders to be depth-verified and partial fills handled correctly,
so that the system never orphans untracked contracts, never corrupts risk state with incorrect P&L, and exits are sized to what the order book can actually fill.

## Acceptance Criteria

### AC1: P&L Uses Exit Fill Sizes (P0)

**Given** an exit order returns `status: 'partial'` (e.g., 300 of 400 contracts filled)
**When** realized P&L is calculated
**Then** P&L uses the actual exit fill sizes (`filledQuantity`) from both legs, not the entry fill sizes
**And** exit fees are calculated on the actual traded notional (exit fill size x exit fill price)
**And** capital returned to the risk manager reflects only the exited portion
[Source: sprint-change-proposal-2026-03-06-exit-depth-partial-fill.md#Proposal-1]

### AC2: Partial Fills Transition to EXIT_PARTIAL with Proportional Capital Release (P0)

**Given** an exit completes and either leg's actual exit fill size is less than the entry fill size
**When** the exit result is processed
**Then** the position transitions to `EXIT_PARTIAL` (not `CLOSED`)
**And** realized P&L is calculated on the actual exit fill sizes (AC1)
**And** `riskManager.releasePartialCapital(exitedEntryCapital.plus(realizedPnl), realizedPnl, pairId)` is called — releasing capital for exited contracts while keeping the remaining contracts' capital reserved
**And** a `SingleLegExposureEvent` is emitted with remainder details and operator action recommendations
**And** the exit monitor's next polling cycle does NOT re-evaluate this position (confirmed: queries only `OPEN` status)
[Source: sprint-change-proposal-2026-03-06-exit-depth-partial-fill.md#Proposal-2, user correction re: proportional capital release]

### AC3: IRiskManager — releasePartialCapital Method

**Given** the `IRiskManager` interface and `RiskManagerService` implementation
**When** this story is complete
**Then** a new `releasePartialCapital(capitalReleased, realizedPnl, pairId?)` method exists
**And** it reduces `totalCapitalDeployed` by `capitalReleased`
**And** it updates `dailyPnl` with `realizedPnl`
**And** it does NOT decrement `openPositionCount` (position is still EXIT_PARTIAL)
**And** it does NOT delete from `paperActivePairIds` (position is still active)
**And** it emits a `BUDGET_RELEASED` event with reason `'partial-exit'`
**And** it persists state
[Derived from: risk-manager.service.ts:926-974 — closePosition does all three wrong things for partial exits]

### AC4: Pre-Exit Depth Check with Graceful Deferral (P1)

**Given** an exit threshold is triggered and `executeExit()` is called
**When** exit orders are about to be submitted
**Then** fresh order books are fetched for both legs (intentional second fetch — book may have changed since evaluation)
**And** available depth is calculated at the close price or better on each side
**And** if either side has zero depth, the exit is deferred to the next cycle (position stays `OPEN`)
**And** if the order book fetch throws (network error, rate limit), fall back to entry fill size (attempt full exit rather than deferring — at exit time, prolonging exposure is worse than risking a partial fill)
**And** exit sizes are capped to available depth and equalized: `exitSize = Decimal.min(primaryDepth, secondaryDepth, entryFillSize)`
**And** if `exitSize < entryFillSize`, partial exit flows into the EXIT_PARTIAL path (AC2)
[Source: sprint-change-proposal-2026-03-06-exit-depth-partial-fill.md#Proposal-3]

### AC5: VWAP-Aware Close Price for Threshold Evaluation (P1)

**Given** the threshold evaluator is computing close prices for a position
**When** `getClosePrice()` is called with a position size
**Then** the returned price is a VWAP (volume-weighted average price) across order book levels needed to fill the position size
**And** if the book cannot fill the full position, the VWAP covers available depth (pessimistic signal)
**And** if `getClosePrice()` is called without a position size, it returns top-of-book price (backward compatible)
[Source: sprint-change-proposal-2026-03-06-exit-depth-partial-fill.md#Proposal-4]

### AC6: Architecture Doc Update (P2)

**Given** the architecture document describes the exit-management hot path at line 627
**When** this story is complete
**Then** the description is updated to note depth-verified exit sizing and partial fill handling
[Source: sprint-change-proposal-2026-03-06-exit-depth-partial-fill.md#Proposal-5]

### AC7: Tests

**Given** the test suites for exit-monitor, risk-manager, and threshold evaluator
**When** tests run
**Then** new test cases cover:
- Partial fill P&L uses exit fill sizes, not entry fill sizes (AC: #1)
- EXIT_PARTIAL transition on partial fills with proportional capital release (AC: #2)
- `releasePartialCapital` reduces capital without decrementing position count (AC: #3)
- Zero-depth exit deferred to next cycle (AC: #4)
- Depth-capped exit sizes equalized across legs (AC: #4)
- Depth-capped full fill still triggers EXIT_PARTIAL when `exitSize < entryFillSize` (AC: #4)
- VWAP calculation across multiple order book levels (AC: #5)
- VWAP with partial book depth (AC: #5)
- VWAP backward compatibility (no size param = top-of-book) (AC: #5)
- All existing tests continue to pass
**And** `pnpm lint` reports zero errors

## Tasks / Subtasks

- [x] Task 1: Add `releasePartialCapital` to IRiskManager and RiskManagerService (AC: #3)
  - [x] 1.1 Add method signature to `IRiskManager` interface (`common/interfaces/risk-manager.interface.ts:81`):
    ```typescript
    releasePartialCapital(
      capitalReleased: unknown,
      realizedPnl: unknown,
      pairId?: string,
    ): Promise<void>;
    ```
  - [x] 1.2 Implement in `RiskManagerService` (`modules/risk-management/risk-manager.service.ts`):
    - Reduce `totalCapitalDeployed` by `capitalReleased` (clamp to 0)
    - Call `updateDailyPnl(realizedPnl)` — same as `closePosition`
    - Emit `BUDGET_RELEASED` event with reason `'partial-exit'`
    - Call `persistState()`
    - Do NOT decrement `openPositionCount`
    - Do NOT delete from `paperActivePairIds`
  - [x] 1.3 Write tests: capital reduced correctly; position count unchanged; paperActivePairIds unchanged; dailyPnl updated; event emitted; state persisted
  - [x] 1.4 Add `releasePartialCapital` to `createMockRiskManager` factory (`test/mock-factories.ts`)

- [x] Task 2: Fix P&L to use exit fill sizes (AC: #1)
  - [x] 2.1 In `executeExit()` (`exit-monitor.service.ts:268-544`), after both legs return `'filled'` or `'partial'`, replace entry fill sizes with exit fill sizes in P&L calculation:
    - Current (lines 466-491): `kalshiFillSize` / `polymarketFillSize` (entry sizes from `kalshiOrder.fillSize`)
    - New: map `primaryResult.filledQuantity` / `secondaryResult.filledQuantity` to kalshi/polymarket using `isPrimaryKalshi`:
      ```typescript
      const kalshiExitFillSize = isPrimaryKalshi
        ? new Decimal(primaryResult.filledQuantity)
        : new Decimal(secondaryResult.filledQuantity);
      const polymarketExitFillSize = isPrimaryKalshi
        ? new Decimal(secondaryResult.filledQuantity)
        : new Decimal(primaryResult.filledQuantity);
      ```
    - Replace `kalshiFillSize` with `kalshiExitFillSize` in per-leg P&L (lines 470-484)
    - Replace `kalshiFillSize` with `kalshiExitFillSize` in exit fee calculation (lines 488-499)
    - Replace `kalshiFillSize`/`polymarketFillSize` in `totalEntryCapital` → rename to `exitedEntryCapital` and compute: `kalshiEntryPrice.mul(kalshiExitFillSize).plus(polymarketEntryPrice.mul(polymarketExitFillSize))`
  - [x] 2.2 Write tests: partial fill P&L uses exit quantities; full fill produces same result as before; exit fees on actual traded notional; capital returned reflects exited portion

- [x] Task 3: Partial fills transition to EXIT_PARTIAL with proportional release (AC: #2)
  - [x] 3.1 After both exit legs return, compare actual exit fill sizes to entry fill sizes. Determine `isFullExit`:
    ```typescript
    // Round to integer contract units for comparison (filledQuantity is integer contracts)
    const isFullExit = kalshiExitFillSize.round().gte(kalshiFillSize.round())
      && polymarketExitFillSize.round().gte(polymarketFillSize.round());
    ```
  - [x] 3.2 **Full exit path** (isFullExit = true): existing CLOSED logic with corrected P&L from Task 2. Call `riskManager.closePosition(capitalReturned, realizedPnl, pairId)`.
  - [x] 3.3 **Partial exit path** (isFullExit = false):
    - Transition to `EXIT_PARTIAL` via `positionRepository.updateStatus(positionId, 'EXIT_PARTIAL')`
    - Call `riskManager.releasePartialCapital(exitedEntryCapital.plus(realizedPnl), realizedPnl, pairId)` — releases capital for exited contracts only
    - Emit `SingleLegExposureEvent` with (note: overloaded use — this is a partial-exit remainder, not a true execution failure; add code comment: `// Overloaded: partial exit remainder, not single-leg failure`):
      - filledLeg: the exit order with the larger fill (or primary if equal)
      - failedLeg: reason = `'Partial exit — remainder contracts unexited'`, reasonCode = `EXECUTION_ERROR_CODES.PARTIAL_EXIT_FAILURE` (2008)
      - recommendedActions: `['Retry exit via POST /api/positions/:id/retry-leg', 'Close remaining via POST /api/positions/:id/close-leg']`
      - isPaper/mixedMode flags
    - Log remainder details: position ID, entry sizes, exit fill sizes, unfilled quantities
  - [x] 3.4 Write tests: partial primary triggers EXIT_PARTIAL; partial secondary triggers EXIT_PARTIAL; both partial triggers EXIT_PARTIAL; full exit still triggers CLOSED; proportional capital release called with correct amounts; SingleLegExposureEvent emitted with correct data

- [x] Task 4: Pre-exit depth check with deferral (AC: #4)
  - [x] 4.1 Add `getAvailableExitDepth()` private method to `ExitMonitorService`:
    ```typescript
    private async getAvailableExitDepth(
      connector: IPlatformConnector,
      contractId: string,
      closeSide: 'buy' | 'sell',
      closePrice: Decimal,
    ): Promise<{ depth: Decimal; book: NormalizedOrderBook }>
    ```
    Pattern: iterate price levels on the close side at `closePrice` or better (buy: asks <= closePrice; sell: bids >= closePrice). Accumulate quantity. Return both depth and book (book needed for VWAP in Task 5).
  - [x] 4.2 At the top of `executeExit()`, BEFORE submitting any orders:
    - Wrap depth fetches in try-catch:
      ```typescript
      let primaryDepthResult, secondaryDepthResult;
      try {
        [primaryDepthResult, secondaryDepthResult] = await Promise.all([
          this.getAvailableExitDepth(primaryConnector, primaryContractId, primaryCloseSide, primaryClosePrice),
          this.getAvailableExitDepth(secondaryConnector, secondaryContractId, secondaryCloseSide, secondaryClosePrice),
        ]);
      } catch (error) {
        // Fetch failure: fall back to entry fill size — attempt full exit rather than deferring
        this.logger.warn({ message: 'Exit depth fetch failed — using entry fill size', data: { ... } });
        // Skip depth capping, proceed with original primaryFillSize/secondaryFillSize
      }
      ```
    - Comment: `// Intentional second fetch — book may have changed since threshold evaluation`
    - If either side has zero depth (not fetch failure): log warning, return (position stays OPEN, deferred to next cycle)
    - Cap exit sizes: `exitSize = Decimal.min(primaryDepth, secondaryDepth, entryFillSize)`
    - If `exitSize.isZero()`: return (deferred)
    - Replace `primaryFillSize`/`secondaryFillSize` with `exitSize` in the `submitOrder` calls
  - [x] 4.3 Cross-leg equalization: both legs submit the same `exitSize` to prevent directional exposure from asymmetric fills
  - [x] 4.4 Write tests: zero depth on primary defers exit; zero depth on secondary defers exit; sizes capped to smaller depth; sizes equalized across legs; depth-capped full fill produces EXIT_PARTIAL when exitSize < entryFillSize; fetch failure falls back to entry fill size (conservative: attempt full exit)

- [x] Task 5: VWAP-aware close pricing (AC: #5)
  - [x] 5.1 Extend `getClosePrice()` signature (`exit-monitor.service.ts:645-659`) with optional `positionSize` parameter:
    ```typescript
    async getClosePrice(
      connector: IPlatformConnector,
      contractId: string,
      originalSide: string,
      positionSize?: Decimal,
    ): Promise<Decimal | null>
    ```
  - [x] 5.2 Without `positionSize`: existing behavior (top-of-book price, backward compatible)
  - [x] 5.3 With `positionSize`: compute VWAP across levels:
    ```typescript
    let remainingQty = positionSize;
    let totalCost = new Decimal(0);
    for (const level of levels) {
      const fillAtLevel = Decimal.min(remainingQty, new Decimal(level.quantity));
      totalCost = totalCost.plus(fillAtLevel.mul(new Decimal(level.price)));
      remainingQty = remainingQty.minus(fillAtLevel);
      if (remainingQty.lte(0)) break;
    }
    const filledQty = positionSize.minus(remainingQty);
    if (filledQty.isZero()) return null;
    return totalCost.div(filledQty);
    ```
    If book can't fill full position: VWAP of available depth (pessimistic — signals larger impact)
  - [x] 5.4 Update `evaluatePosition()` (line ~193-199) to pass position size to `getClosePrice()`:
    ```typescript
    const kalshiClosePrice = await this.getClosePrice(
      this.kalshiConnector,
      position.pair.kalshiContractId,
      position.kalshiSide,
      new Decimal(kalshiOrder.fillSize.toString()),
    );
    ```
    Same for polymarket close price.
  - [x] 5.5 Write tests: single-level book returns same as top-of-book; multi-level VWAP correct; book can't fill full position returns VWAP of available; empty book returns null; no positionSize returns top-of-book (backward compat)

- [x] Task 6: Architecture doc update (AC: #6)
  - [x] 6.1 Update `_bmad-output/planning-artifacts/architecture.md` line 627 from:
    ```
    modules/exit-management/ (monitor positions, evaluate thresholds, trigger exits)
    ```
    To:
    ```
    modules/exit-management/ (monitor positions, VWAP-aware threshold evaluation, depth-verified exit sizing)
        ↓                  ↑ exit orders depth-checked and capped to available liquidity (FR-EX-03)
        ↓                  ↑ partial fills transition to EXIT_PARTIAL for operator resolution
    ```

- [x] Task 7: Run full test suite and lint (AC: #7)
  - [x] 7.1 `pnpm test` — all tests pass
  - [x] 7.2 `pnpm lint` — zero errors

## Dev Notes

### Architecture Compliance

- **Module boundaries preserved.** Changes span:
  - `common/interfaces/` — new method on `IRiskManager` interface (common → all modules, allowed)
  - `modules/risk-management/` — new `releasePartialCapital` method (internal to module)
  - `modules/exit-management/` — depth checks, VWAP, partial fill handling (exit-management → connectors, risk-management — allowed)
  - `_bmad-output/planning-artifacts/` — architecture doc update (non-code)
- **No forbidden imports introduced.** Exit management already imports connectors and risk-management. No new cross-module dependencies.
- **Financial math:** ALL depth, VWAP, P&L, and capital calculations MUST use `decimal.js`. Use `.mul()`, `.plus()`, `.minus()`, `.div()`. Convert Prisma Decimal via `new Decimal(value.toString())`.
- **Error hierarchy:** No new error types. Reuse `EXECUTION_ERROR_CODES.PARTIAL_EXIT_FAILURE` (2008) — already exists.
- **Events:** No new event classes. Reuse `SingleLegExposureEvent` and `BudgetReleasedEvent`.

### Key Design Decisions

1. **Proportional capital release on partial exits.** When 300 of 400 contracts exit, release capital for those 300 (entry capital + realized P&L). The remaining 100 contracts' capital stays reserved. This keeps the risk budget accurate — no over-release (the original bug where full capital was released on CLOSED) and no under-release (the proposal's original approach of holding all capital). New `releasePartialCapital()` method does NOT touch `openPositionCount` or `paperActivePairIds` because the position remains active as EXIT_PARTIAL. [Source: user correction to sprint-change-proposal-2026-03-06-exit-depth-partial-fill.md#Proposal-2]

2. **`closePosition()` is wrong for partial exits because it:** (a) decrements `openPositionCount` — position is still open, (b) deletes from `paperActivePairIds` — pair is still active, (c) releases full capital — only exited portion should be released. Hence the need for `releasePartialCapital()`. [Source: risk-manager.service.ts:926-974]

3. **No minimum fill ratio for exits.** Unlike entry's 25% minimum fill ratio, exits accept any fill. At exit time, reducing any exposure is better than staying fully exposed. [Source: epics.md#Story-6.5.5k design decisions]

4. **No edge re-validation at exit.** The exit decision was already made by the threshold evaluator. The depth check is about execution feasibility, not opportunity quality. [Source: epics.md#Story-6.5.5k design decisions]

5. **Cross-leg equalization.** Both exit legs submit the same `exitSize = Decimal.min(primaryDepth, secondaryDepth, entryFillSize)`. This prevents creating directional exposure from asymmetric fills. Same principle as entry equalization from Story 6.5.5h. [Source: sprint-change-proposal-2026-03-06-exit-depth-partial-fill.md#Proposal-3]

6. **Double order book fetch is intentional freshness.** `evaluatePosition()` fetches books for threshold evaluation. `executeExit()` fetches again for depth checking. The book may have changed between evaluation and execution — this is NOT redundancy. Must be commented in code. [Source: sprint-change-proposal-2026-03-06-exit-depth-partial-fill.md#Proposal-3]

7. **VWAP backward compatibility.** `getClosePrice()` without `positionSize` returns top-of-book (existing behavior). With `positionSize`, it returns VWAP. This is backward compatible — no existing callers break. The threshold evaluator is updated to pass position size. [Source: sprint-change-proposal-2026-03-06-exit-depth-partial-fill.md#Proposal-4]

8. **VWAP reusable for Epic 10.** The `getClosePrice(connector, id, side)` vs `getClosePrice(connector, id, side, size)` comparison yields a built-in spread metric, directly reusable for FR-EM-03 criterion #5 (liquidity deterioration). [Source: epics.md#Story-10.2]

9. **BudgetReleasedEvent reuse.** `BudgetReleasedEvent(reservationId, opportunityId, releasedCapitalUsd)` — for partial exit, use `'partial-exit'` for both `reservationId` and `opportunityId` (same pattern as `closePosition` which uses `'position-close'`). No event class changes needed.

10. **Reconciliation on restart.** EXIT_PARTIAL positions with unfilled remainders must be verified against platform order status on system restart. The existing `StartupReconciliationService` (Story 5.5) already queries active positions — EXIT_PARTIAL positions will be included since they're not CLOSED. If exit orders filled while the system was down, reconciliation should detect the discrepancy and update status.

12. **No sub-position splitting.** When a partial exit leaves unfilled contracts, we don't create a sub-position or split the record. The position stays as EXIT_PARTIAL with the full original entry data. The operator resolves via existing retry-leg/close-leg endpoints. Splitting would require schema changes beyond this fix's scope. [Source: sprint-change-proposal-2026-03-06-exit-depth-partial-fill.md#Proposal-2]

13. **Depth fetch failure fallback.** If `getAvailableExitDepth()` throws (network error, rate limit), fall back to entry fill size — attempt the full exit rather than deferring. This is different from zero-depth (book exists but empty, which defers), and from entry path behavior (where depth failure returns 0 and blocks execution). Rationale: for exits, the operator has already decided to close; blocking repeatedly on depth failures prolongs exposure.

### Existing Infrastructure Reused

- `EXIT_PARTIAL` already in `PositionStatus` enum — no schema change needed
- `EXECUTION_ERROR_CODES.PARTIAL_EXIT_FAILURE` (2008) already exists
- `SingleLegExposureEvent` class reused for partial exit notification
- `BudgetReleasedEvent` class reused for partial capital release
- `handlePartialExit()` method already handles secondary-leg-total-failure → EXIT_PARTIAL (this story adds partial-fill handling as a separate code path)
- Exit monitor queries only `'OPEN'` positions — `EXIT_PARTIAL` positions are NOT re-evaluated (no double-exit risk)
- Operator resolves via existing `retry-leg` / `close-leg` endpoints from Story 5.3

### Current Code — Exact Bugs Being Fixed

**Bug 1 — P&L uses entry sizes** (`exit-monitor.service.ts:466-501`):
```typescript
// CURRENT (broken): uses kalshiFillSize from entry order
kalshiPnl = kalshiCloseFilledPrice.minus(kalshiEntryPrice).mul(kalshiFillSize);
// FIX: use kalshiExitFillSize from exit result
kalshiPnl = kalshiCloseFilledPrice.minus(kalshiEntryPrice).mul(kalshiExitFillSize);
```
Same pattern for polymarketPnl, exit fees, and capital calculation.

**Bug 2 — CLOSED on partial fills** (`exit-monitor.service.ts:502`):
Currently, after both legs return `'filled'` or `'partial'`, the code unconditionally runs `updateStatus(positionId, 'CLOSED')`. A partial fill leaves unfilled contracts on the platform with zero tracking.

**Bug 3 — No depth check** (`exit-monitor.service.ts:268-544`):
`executeExit()` uses `primaryFillSize` (entry fill size) directly as order quantity. No `getAvailableDepth()` or equivalent. Entry path has robust depth checking (execution.service.ts:867-911).

**Bug 4 — Top-of-book pricing** (`exit-monitor.service.ts:645-659`):
`getClosePrice()` reads `bids[0].price` / `asks[0].price`. For large positions, the actual executable price (VWAP across levels) may be significantly worse, causing misleading threshold evaluations.

### handlePartialExit vs New Partial Fill Path

The existing `handlePartialExit()` method (lines 546-643) handles a specific scenario: the secondary exit leg **entirely fails** (throws or returns rejected/pending status). It transitions to EXIT_PARTIAL and emits SingleLegExposureEvent.

The NEW partial fill path (Task 3) handles a different scenario: both legs return `'filled'` or `'partial'`, but one or both have `filledQuantity < entry fillSize`. This path:
1. Calculates corrected P&L on actual fills (Task 2)
2. Calls `releasePartialCapital` for proportional release (Task 1)
3. Transitions to EXIT_PARTIAL
4. Emits SingleLegExposureEvent with remainder details

Both paths lead to EXIT_PARTIAL but with different context. The existing `handlePartialExit` is NOT modified — it continues to handle total secondary failure.

### Interaction: Depth Cap + Actual Partial Fill

Example: entry = 400 contracts, depth check caps to 200, both legs submit 200.
- Scenario A: both fill 200 → `isFullExit = false` (200 < 400) → EXIT_PARTIAL, P&L on 200
- Scenario B: primary fills 200, secondary fills 150 → `isFullExit = false` → EXIT_PARTIAL, P&L on min(200, 150) per leg
- Scenario C: depth cap = 400 (sufficient), both fill 400 → `isFullExit = true` → CLOSED

Note for Scenario B: P&L is calculated independently per leg (kalshiExitFillSize, polymarketExitFillSize), not capped to the minimum. Each leg's P&L reflects its actual fills. The cross-leg imbalance (50 extra contracts exited on primary) means the position has asymmetric exposure in EXIT_PARTIAL — the operator must resolve this.

### Implementation Order (within the story)

1. **Task 1** — `releasePartialCapital` on IRiskManager + RiskManagerService (prerequisite for Task 3)
2. **Task 2** — Fix P&L to use exit fill sizes (P0, prerequisite for Task 3)
3. **Task 3** — Partial fills transition to EXIT_PARTIAL with proportional release (P0, depends on Tasks 1+2)
4. **Task 4** — Pre-exit depth check + deferral (P1, builds on partial fill handling)
5. **Task 5** — VWAP-aware close pricing (P1, independent but logically follows)
6. **Task 6** — Architecture doc update (P2, last)
7. **Task 7** — Full test suite + lint

### Sequencing & Dependencies

- **Depends on:** Stories 6.5.5a through 6.5.5j (all done). Specifically:
  - 6.5.5h (Equal Leg Sizing) — sizes guaranteed equal, `legSize = kalshiSize` pattern
  - 6.5.5i (Exit Threshold Calibration) — entry close prices, entry cost baseline, `FinancialMath.computeEntryCostBaseline()`
  - 6.5.5j (Take-Profit Negative Threshold) — journey-based TP formula with floor
  - 6.5.5e (Paper Mode Exit Monitor) — paper positions flow through exit monitoring, isPaper threading
  - 5.3 (Single-Leg Resolution) — retry-leg/close-leg endpoints for operator resolution of EXIT_PARTIAL
- **Gates:** Story 6.5.5 (Paper Execution Validation) and Story 6.5.6 (Validation Report)
- **No schema changes.** `EXIT_PARTIAL` already in PositionStatus enum. `PARTIAL_EXIT_FAILURE` (2008) already in error codes.

### Previous Story Intelligence

**Story 6.5.5j (Take-Profit Negative Threshold Fix) — most recent, 1,410 tests baseline:**
- Journey-based TP formula: `max(0, 0.20 * entryCostBaseline + 0.80 * scaledInitialEdge)`
- Strict TDD throughout — follow same pattern
- `computeEntryCostBaseline()` in `financial-math.ts` handles nullable fields

**Story 6.5.5i (Exit Threshold Calibration Fix) — 1,398 tests:**
- Entry close prices stored on OpenPosition (4 nullable Decimal fields)
- `FinancialMath.calculateTakerFeeRate(price, feeSchedule)` for dynamic fees
- Close-side price capture pattern in execution service (after fills, before position creation)
- Adversarial code review found missing try-catch on fee computation — apply same defensive pattern here

**Story 6.5.5h (Execution Equal Leg Sizing) — 1,374 tests:**
- `legSize = kalshiSize` convention (sizes guaranteed equal)
- Cross-leg equalization in execution: both legs submit same size
- Apply same equalization principle to exit sizing

**Story 6.5.5b (Depth-Aware Position Sizing):**
- `getAvailableDepth()` pattern in ExecutionService (lines 867-911) — adapt for exit path
- Iterates price levels, accumulates quantity at target price or better

### Testing Patterns (from exit-monitor.service.spec.ts)

- NestJS `TestingModule` with mocked dependencies
- `createMockPosition(overrides)` factory — accepts `Record<string, unknown>` overrides
- `createMockPlatformConnector()` and `createMockRiskManager()` from `test/mock-factories.ts`
- `setupOrderCreateMock()` — generates sequential `exit-order-N` IDs
- `vi.mock('../../common/services/correlation-context')` — must be at top of file
- Mock connectors: `submitOrder.mockResolvedValue(...)`, `getOrderBook.mockResolvedValue(...)`, `getHealth.mockReturnValue(...)`, `getFeeSchedule.mockReturnValue(...)`
- Existing `'partial exit'` describe block covers secondary-leg-total-failure scenario — new tests should be in a new describe block for partial-fill scenarios

### Project Structure Notes

- All source changes within `pm-arbitrage-engine/` — separate git repo, separate commit required
- No new files created — only modifications to existing files + architecture doc
- Tests co-located with source (`.spec.ts` suffix)
- `NormalizedOrderBook` type imported from `common/types/normalized-order-book.type.ts` — needed for `getAvailableExitDepth()` return type

### File Structure — Files to Modify

| File | Change |
|------|--------|
| `src/common/interfaces/risk-manager.interface.ts` | Add `releasePartialCapital()` method to interface |
| `src/modules/risk-management/risk-manager.service.ts` | Implement `releasePartialCapital()` |
| `src/modules/risk-management/risk-manager.service.spec.ts` | Tests for `releasePartialCapital()` |
| `src/test/mock-factories.ts` | Add `releasePartialCapital` to mock risk manager |
| `src/modules/exit-management/exit-monitor.service.ts` | Fix P&L sizes, partial fill → EXIT_PARTIAL, depth check, VWAP |
| `src/modules/exit-management/exit-monitor.service.spec.ts` | Tests for all new behaviors |
| `_bmad-output/planning-artifacts/architecture.md` | Update hot path diagram (line 627) |

### Scope Guard

This story is strictly scoped to:

1. New `releasePartialCapital()` on IRiskManager + RiskManagerService
2. Fix P&L to use exit fill sizes
3. Partial fills → EXIT_PARTIAL with proportional capital release
4. Pre-exit depth check with deferral and cross-leg equalization
5. VWAP-aware `getClosePrice()` with backward-compatible optional param
6. Architecture doc hot path update
7. Tests for all above

Do NOT:

- Modify detection service logic
- Change execution entry sizing logic (correct from 6.5.5h)
- Add configurable SL/TP multipliers
- Modify connectors (order book API and `OrderResult.filledQuantity` already support this)
- Create new event classes (reuse `SingleLegExposureEvent`, `BudgetReleasedEvent`)
- Add new error codes (reuse `PARTIAL_EXIT_FAILURE` 2008)
- Implement sub-position splitting (deferred — would require schema changes)
- Modify threshold evaluator formulas (correct from 6.5.5i/6.5.5j — only the price input changes to VWAP)
- Add auto-retry of unfilled remainder (operator decides via existing endpoints)
- Modify `handlePartialExit()` (continues handling secondary-leg-total-failure, unchanged)

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-06-exit-depth-partial-fill.md] — Sprint change proposal with full evidence, impact analysis, proposals 1-5
- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.5.5k] — Epic story definition with AC, design decisions, sequencing
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts:268-544] — `executeExit()` method (P&L bug at 466-501, CLOSED bug at 502, no depth check)
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts:645-659] — `getClosePrice()` (top-of-book only, extend with VWAP)
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts:546-643] — `handlePartialExit()` (NOT modified, handles secondary-leg-total-failure)
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts:50-129] — `evaluatePositions()` queries only `'OPEN'` — EXIT_PARTIAL not re-evaluated
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts:131-266] — `evaluatePosition()` fetches close prices (update to pass size for VWAP)
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts:867-911] — `getAvailableDepth()` pattern to adapt for exit path
- [Source: pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts:926-974] — `closePosition()` — decrements position count, deletes from paper pairs, releases full capital (all wrong for partial)
- [Source: pm-arbitrage-engine/src/common/interfaces/risk-manager.interface.ts:81-85] — `IRiskManager.closePosition` signature (add `releasePartialCapital` near it)
- [Source: pm-arbitrage-engine/src/common/errors/execution-error.ts:24] — `PARTIAL_EXIT_FAILURE: 2008` (reuse)
- [Source: pm-arbitrage-engine/src/common/events/execution.events.ts:35-72] — `SingleLegExposureEvent` class (reuse for partial exit notification)
- [Source: pm-arbitrage-engine/src/common/types/platform.type.ts:22-29] — `OrderResult` interface (`filledQuantity: number` — always populated, not optional)
- [Source: pm-arbitrage-engine/src/common/types/normalized-order-book.type.ts:2-15] — `PriceLevel` and `NormalizedOrderBook` types (needed for VWAP and depth check)
- [Source: _bmad-output/implementation-artifacts/6-5-5i-exit-threshold-calibration-fix.md] — Previous story: entry close prices, fee rates, baseline computation
- [Source: _bmad-output/implementation-artifacts/6-5-5j-take-profit-negative-threshold-fix.md] — Previous story: journey-based TP formula, 1,410 test baseline
- [Source: _bmad-output/planning-artifacts/architecture.md:627] — Hot path diagram line to update

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — implementation was clean with no debugging needed.

### Completion Notes List

- **Baseline:** 1,410 tests (80 files) before changes
- **Final:** 1,432 tests (80 files) — 22 new tests added (7 risk-manager + 15 exit-monitor)
- **Lint:** Zero errors
- **TDD:** All tests written before implementation (RED → GREEN → REFACTOR)
- **Lad MCP review completed.** Both reviewers' findings were evaluated against story AC and Dev Notes — all were either pre-existing patterns, intentional design decisions (documented in Dev Notes #9, #12, #13), or out of scope per the Scope Guard. No code changes needed from review.
- **BMAD adversarial code review (Amelia):** 3 issues fixed:
  - **H1 FIXED:** `filledLeg.price` in `SingleLegExposureEvent` was set to `exitSize` (a quantity) instead of the close price. Fixed to use `primaryClosePrice`/`secondaryClosePrice` based on `filledLegIsPrimary`.
  - **M1 FIXED:** Strengthened `SingleLegExposureEvent` test to validate `filledLeg` fields (`price`, `fillPrice`, `fillSize`) and assert `filledLeg.price` is a valid probability (0-1). Would have caught H1.
  - **M2 FIXED:** Added early termination (`break`) in `getAvailableExitDepth()` level iteration — sorted book optimization.
  - **L1 NOTED:** VWAP integration with threshold evaluation not explicitly tested (no fix needed).
  - **L2 NOTED:** Pre-existing: `handlePartialExit` doesn't release capital for filled primary leg (out of scope per Scope Guard).
- **Key decisions:**
  - `releasePartialCapital` follows same `unknown` param typing as `closePosition` (consistency)
  - `BudgetReleasedEvent` uses `'partial-exit'` placeholder IDs (same pattern as `'position-close'`)
  - `handlePartialExit` (secondary-leg-total-failure) intentionally NOT modified per Scope Guard
  - `getAvailableExitDepth` adapted from execution's `getAvailableDepth` pattern but returns Decimal (not number) and throws on fetch failure (caller handles)

### File List

| File | Change |
|------|--------|
| `src/common/interfaces/risk-manager.interface.ts` | Added `releasePartialCapital()` method signature |
| `src/modules/risk-management/risk-manager.service.ts` | Implemented `releasePartialCapital()` — reduces capital, updates P&L, emits event, persists; does NOT decrement position count or delete paper pairs |
| `src/modules/risk-management/risk-manager.service.spec.ts` | +7 tests for `releasePartialCapital` |
| `src/test/mock-factories.ts` | Added `releasePartialCapital` to `createMockRiskManager` |
| `src/modules/exit-management/exit-monitor.service.ts` | (1) P&L uses `kalshiExitFillSize`/`polymarketExitFillSize` from `filledQuantity`. (2) `isFullExit` check branches to CLOSED or EXIT_PARTIAL with proportional capital release. (3) `getAvailableExitDepth()` private method + pre-exit depth check with deferral/fallback. (4) `getClosePrice()` extended with optional `positionSize` for VWAP. (5) `evaluatePosition()` passes position size to VWAP. |
| `src/modules/exit-management/exit-monitor.service.spec.ts` | +15 tests: partial fill P&L, EXIT_PARTIAL transitions, releasePartialCapital vs closePosition, SingleLegExposureEvent, full exit still CLOSED, depth deferral (zero/fetch fail), depth capping/equalization, VWAP (multi-level, partial book, backward compat, sell side) |
| `_bmad-output/planning-artifacts/architecture.md` | Updated hot path diagram line 627: VWAP-aware threshold evaluation, depth-verified exit sizing, partial fills → EXIT_PARTIAL |
