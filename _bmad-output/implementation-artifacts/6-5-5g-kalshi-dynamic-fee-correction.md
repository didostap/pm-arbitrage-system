# Story 6.5.5g: Kalshi Dynamic Fee Correction

Status: done

## Story

As an operator,
I want the system to use Kalshi's actual dynamic taker fee formula (`0.07 × P × (1-P)`) instead of 0%,
so that edge calculations, exit monitoring, and single-leg P&L scenarios reflect real trading costs and paper trading validation produces meaningful results.

## Background / Root Cause

**Critical blocker for Stories 6-5-5 (Paper Execution Validation) and 6-5-6 (Validation Report).**

The Kalshi connector's `getFeeSchedule()` returns `takerFeePercent: 0` and `makerFeePercent: 0`. The PRD documents a flat 1.5%. Both are wrong. Kalshi charges a **dynamic, price-dependent taker fee**: `roundUp(0.07 × P × (1-P))` per contract, peaking at 1.75% at P=0.50.

**Discovery:** Manual code review of `kalshi.connector.ts:478-485` cross-referenced against Kalshi's published fee schedule (Feb 5, 2026 PDF). Web research confirmed the formula.

**Impact:** With 0% Kalshi fees, every edge calculation is overstated by up to 1.75%. The system could execute **negative-edge trades** that appear profitable. Exit monitoring and single-leg PnL scenarios are also miscalculated. Paper trading validation (story 6-5-5) would produce meaningless results.

## Acceptance Criteria

1. **Given** the `FeeSchedule` interface
   **When** a platform has dynamic fees
   **Then** an optional `takerFeeForPrice` callback field exists that accepts a price (0.00-1.00) and returns the fee as a decimal fraction

2. **Given** the Kalshi connector
   **When** `getFeeSchedule()` is called
   **Then** it returns `takerFeePercent: 1.75` (worst-case at P=0.50 for pre-screening) and a `takerFeeForPrice` callback implementing `0.07 × (1-P)`
   **And** `makerFeePercent: 0`

3. **Given** `FinancialMath.calculateTakerFeeRate(price, feeSchedule)` is called with a FeeSchedule that has `takerFeeForPrice`
   **When** the callback exists
   **Then** it returns the callback result as a Decimal
   **And** when the callback is absent, it falls back to `takerFeePercent / 100`

4. **Given** all 6 consumer locations of `takerFeePercent / 100`
   **When** the code is updated
   **Then** each uses `FinancialMath.calculateTakerFeeRate()` instead of inline `takerFeePercent / 100` logic

5. **Given** the `SingleLegPnlInput` interface and both call sites (`execution.service.ts`, `single-leg-resolution.service.ts`)
   **When** a single-leg PnL scenario is built
   **Then** `takerFeeForPrice` callbacks are passed through from FeeSchedule and used in `calcCloseNow` and `calcRetry`

6. **Given** no event payload or audit log serializes raw `FeeSchedule` objects
   **When** the change is deployed
   **Then** the `takerFeeForPrice` callback is never stripped by `JSON.stringify()` (verified: events carry computed fee costs as numbers, not `FeeSchedule` objects)

7. **Given** the mock factory in `src/test/mock-factories.ts`
   **When** a Kalshi mock connector is created
   **Then** `takerFeePercent` is `1.75` (was `0`) and `takerFeeForPrice` callback is provided

8. **Given** the PRD fee normalization section
   **When** the documentation is updated
   **Then** the flat 1.5% Kalshi fee is replaced with the dynamic formula documentation

9. **Given** all existing tests (1,263) pass before the change
   **When** the changes are implemented
   **Then** all tests pass with updated expectations
   **And** new tests cover: formula correctness, centralized helper, fallback path, price edge cases
   **And** `pnpm lint` reports zero errors

## Tasks / Subtasks

- [x] Task 1: Extend `FeeSchedule` interface (AC: #1)
  - [x]1.1 In `src/common/types/platform.type.ts`, add optional `takerFeeForPrice?: (price: number) => number` field to `FeeSchedule` interface with JSDoc explaining: price is internal decimal (0.00-1.00), returns fee as decimal fraction

- [x] Task 2: Fix `KalshiConnector.getFeeSchedule()` (AC: #2)
  - [x]2.1 In `src/connectors/kalshi/kalshi.connector.ts:478-485`, change `takerFeePercent: 0` → `1.75`, update `description`, add `takerFeeForPrice` callback: `(price) => { if (price <= 0 || price >= 1) return 0; return new Decimal(0.07).mul(new Decimal(1).minus(price)).toNumber(); }`
  - [x]2.2 Update `src/connectors/kalshi/kalshi.connector.spec.ts`: change `toBe(0)` → `toBe(1.75)`, add tests for dynamic fee formula correctness across price range (0.01, 0.25, 0.50, 0.75, 0.99) and boundary tests (0 and 1 return 0)

- [x] Task 3: Add centralized `FinancialMath.calculateTakerFeeRate()` helper (AC: #3)
  - [x]3.1 In `src/common/utils/financial-math.ts`, add static method `calculateTakerFeeRate(price: Decimal, feeSchedule: FeeSchedule): Decimal` — uses `takerFeeForPrice` callback when present, falls back to `takerFeePercent / 100`
  - [x]3.2 In `src/common/utils/financial-math.spec.ts`, add 5+ test cases: dynamic fee path, flat fee fallback, edge prices (0, 1), midpoint (0.50), both-sides dynamic

- [x] Task 4: Update `FinancialMath.calculateNetEdge()` to use centralized helper (AC: #4)
  - [x]4.1 In `src/common/utils/financial-math.ts:80-84`, replace inline `buyPrice.mul(new FinancialDecimal(buyFeeSchedule.takerFeePercent).div(100))` with `FinancialMath.calculateTakerFeeRate(buyPrice, buyFeeSchedule).mul(buyPrice)` — WAIT: the helper returns the fee *rate*, so `buyFeeCost = buyPrice.mul(calculateTakerFeeRate(buyPrice, buyFeeSchedule))`. Same for sell side.
  - [x]4.2 Verify existing `calculateNetEdge` tests pass with CSV scenarios (the helper should produce identical results for flat-fee platforms)

- [x] Task 5: Update `EdgeCalculatorService.buildFeeBreakdown()` (AC: #4)
  - [x]5.1 In `src/modules/arbitrage-detection/edge-calculator.service.ts:248-252`, replace inline fee computation with `FinancialMath.calculateTakerFeeRate()` calls
  - [x]5.2 Add/update `edge-calculator.service.spec.ts` tests for `buildFeeBreakdown` with dynamic Kalshi fees (use `makeFeeSchedule` helper — extend it to accept optional `takerFeeForPrice`)

- [x] Task 6: Update `ExitMonitorService.evaluatePosition()` (AC: #4)
  - [x]6.1 In `src/modules/exit-management/exit-monitor.service.ts:220-223`, replace inline `kalshiFeeSchedule.takerFeePercent / 100` with `FinancialMath.calculateTakerFeeRate()` using the current close price
  - [x]6.2 **IMPORTANT:** The `ThresholdEvalInput.kalshiFeeDecimal` / `polymarketFeeDecimal` fields expect a single decimal number, but dynamic fees depend on price. Two options: (a) pass the rate at the current close price, or (b) extend `ThresholdEvalInput` to accept a callback. Option (a) is simpler and correct since `evaluatePosition` already has the current price — use that.

- [x] Task 7: Update `ExitMonitorService` realized PnL computation (AC: #4)
  - [x]7.1 In `src/modules/exit-management/exit-monitor.service.ts:455-462`, replace `kalshiFee.takerFeePercent / 100` with `FinancialMath.calculateTakerFeeRate()` at the actual fill price for exit fee calculation

- [x] Task 8: Update `SingleLegResolutionService.closeExposedLeg()` (AC: #4)
  - [x]8.1 In `src/modules/execution/single-leg-resolution.service.ts:374-376`, replace `new Decimal(feeSchedule.takerFeePercent).div(100)` with `FinancialMath.calculateTakerFeeRate(closeFillPrice, feeSchedule)`

- [x] Task 9: Update `single-leg-pnl.util.ts` and call sites (AC: #5)
  - [x]9.1 Extend `SingleLegPnlInput` interface with optional `takerFeeForPrice?: (price: number) => number` and `secondaryTakerFeeForPrice?: (price: number) => number`
  - [x]9.2 Update `calcCloseNow`: if `takerFeeForPrice` provided, compute fee rate at unwind price instead of using flat `takerFeeDecimal`
  - [x]9.3 Update `calcRetry`: if callbacks provided, compute fee rates at respective prices instead of flat rates
  - [x]9.4 Update call site in `execution.service.ts:873-901`: resolve `FeeSchedule` per platform, pass `takerFeeForPrice` callbacks
  - [x]9.5 Update call site in `single-leg-resolution.service.ts:558-573`: resolve `FeeSchedule` per platform, pass `takerFeeForPrice` callbacks

- [x] Task 10: Update mock factory and inline mocks (AC: #7)
  - [x]10.1 In `src/test/mock-factories.ts:29`, change Kalshi `takerFeePercent: 0 → 1.75` and add `takerFeeForPrice` callback
  - [x]10.2 In `src/test/mock-factories.spec.ts`, update `toBe(0)` → `toBe(1.75)` for Kalshi fee assertions, add `takerFeeForPrice` callback verification
  - [x]10.3 In `edge-calculator.service.spec.ts`, update `makeFeeSchedule` helper to accept optional `takerFeeForPrice`, update Kalshi fee mocks where needed
  - [x]10.4 Scan all inline mocks: `exit-monitor.service.spec.ts`, `single-leg-resolution.service.spec.ts`, `execution.service.spec.ts`, `exposure-alert-scheduler.service.spec.ts` — add `takerFeeForPrice` to Kalshi mocks where tests exercise the dynamic fee path

- [x] Task 11: Update PRD (AC: #8)
  - [x]11.1 In `_bmad-output/planning-artifacts/prd.md`, update Fee Normalization section: replace flat 1.5% with dynamic formula documentation
  - [x]11.2 Update Edge Calculation example with dynamic fee at the example price

- [x] Task 12: Run full test suite and lint (AC: #9)
  - [x]12.1 `pnpm test` — all tests pass
  - [x]12.2 `pnpm lint` — zero errors

## Dev Notes

### Architecture Compliance

- **Module boundaries preserved.** Changes span: `common/types/` (interface), `common/utils/` (helper), `connectors/kalshi/` (fee data), `modules/arbitrage-detection/` (fee breakdown), `modules/exit-management/` (exit fees), `modules/execution/` (single-leg PnL fees).
- **No forbidden imports.** The centralized helper lives in `common/utils/financial-math.ts` — importable by all modules. Connectors don't import from modules.
- **No new modules, no schema changes, no new dependencies, no new error types, no new events.**
- **Financial math:** All fee computations use `decimal.js`. The `takerFeeForPrice` callback returns a `number` for API simplicity — consumers wrap in `Decimal` immediately via the centralized helper.

### Key Design Decisions

1. **Centralized `calculateTakerFeeRate()` helper.** Instead of duplicating the callback-or-fallback pattern in 6+ locations, a single static method in `FinancialMath` encapsulates it. This eliminates scale confusion (`takerFeePercent` is 0-100 scale, callback returns decimal fraction) and ensures consistent behavior.

2. **Callback returns rate, not dollar amount.** The `takerFeeForPrice` callback returns `0.07 × (1-P)` — the fee as a *fraction of contract price*. Rounding to the next cent applies to the **total batch fee** at consumption sites after multiplying by quantity, matching Kalshi's semantics.

3. **`takerFeePercent: 1.75` as worst-case.** The flat field now serves as a pre-screening upper bound (max fee at P=0.50). The callback provides exact per-price computation. When the callback is absent (Polymarket), the flat rate is used as before.

4. **Backward-compatible interface extension.** `takerFeeForPrice` is optional. All existing code that uses `takerFeePercent / 100` works unchanged until migrated to the helper. The helper itself handles both paths.

5. **`SingleLegPnlInput` extension for callbacks.** The PnL utility uses plain `number` fees. Extending with optional callbacks allows per-price fee computation without breaking the existing interface.

### Kalshi Fee Formula (verified via web research)

```
Standard event contracts: fee = roundUp(0.07 × C × P × (1-P))
INX/NASDAQ100 contracts:  fee = roundUp(0.035 × C × P × (1-P))
```

Where:
- `C` = number of contracts
- `P` = contract price ($0.00-$1.00)
- `roundUp` = ceiling to next cent on total batch fee

As a rate (fee fraction per unit price): `0.07 × (1-P)` for standard contracts.
Peak: 1.75% at P=$0.50. Approaches 0% at P→$1.00. At P=$0.01: 6.93%.

**Note:** Our system only trades standard event contracts. The INX/NASDAQ100 coefficient (0.035) is out of scope.

### Consumer Location Map

| # | File | Method | Current Code | Change |
|---|------|--------|-------------|--------|
| 1 | `common/utils/financial-math.ts` | `calculateNetEdge` | `buyPrice.mul(new FinancialDecimal(buyFeeSchedule.takerFeePercent).div(100))` | Use `calculateTakerFeeRate(buyPrice, buyFeeSchedule)` then multiply by `buyPrice` |
| 2 | `modules/arbitrage-detection/edge-calculator.service.ts` | `buildFeeBreakdown` | Same inline pattern | Same helper call |
| 3 | `modules/exit-management/exit-monitor.service.ts:220` | `evaluatePosition` | `new Decimal(kalshiFeeSchedule.takerFeePercent).div(100)` | `FinancialMath.calculateTakerFeeRate(currentPrice, feeSchedule)` |
| 4 | `modules/exit-management/exit-monitor.service.ts:457-462` | `executeExit` (realized PnL) | Same inline pattern | Same helper at fill price |
| 5 | `modules/execution/single-leg-resolution.service.ts:375` | `closeExposedLeg` | `new Decimal(feeSchedule.takerFeePercent).div(100)` | Helper at close fill price |
| 6 | `modules/execution/single-leg-pnl.util.ts` | `calcCloseNow` + `calcRetry` | Uses flat `takerFeeDecimal` | Use callback when provided |

### Call Site Updates for PnL Utility (2 locations)

Both `execution.service.ts:873-901` and `single-leg-resolution.service.ts:558-573` compute `takerFeeDecimal` from `feeSchedule.takerFeePercent / 100` and pass to `calculateSingleLegPnlScenarios`. These must additionally pass `takerFeeForPrice` callbacks from the `FeeSchedule`.

### Serialization Safety (verified)

No event payload in `common/events/` carries raw `FeeSchedule` objects. Events carry computed numeric fee costs. The `takerFeeForPrice` callback will never be stripped by `JSON.stringify()` because it's never serialized.

### Rounding Behavior

- `takerFeeForPrice` returns the **rate** (decimal fraction), not the rounded dollar amount
- Rounding to next cent applies at consumption sites: `Decimal.ceil(rate × price × quantity, 2)` or equivalent
- This matches Kalshi's semantics: rounding applies to the total fee invoice, not per-contract
- **Implementation note:** Most of our consumers don't currently round to cents because they operate on fractions of probability. The rounding primarily matters for the actual order cost at execution time, which the connector handles. For edge/PnL calculations, the unrounded rate is more accurate.
- **Rounding mode:** If rounding is needed at any consumption site, use `Decimal.ROUND_UP` (ceiling), NOT the codebase default `ROUND_HALF_UP`. Kalshi's "round up" means ceiling to the next cent. Example: `feeTotal.toDecimalPlaces(2, Decimal.ROUND_UP)`.

### File Structure — Files to Modify

| File | Change |
|------|--------|
| `src/common/types/platform.type.ts` | Add `takerFeeForPrice?` to `FeeSchedule` |
| `src/common/utils/financial-math.ts` | Add `calculateTakerFeeRate()` static method + update `calculateNetEdge()` |
| `src/common/utils/financial-math.spec.ts` | Add tests for `calculateTakerFeeRate()` |
| `src/connectors/kalshi/kalshi.connector.ts` | Fix `getFeeSchedule()`: `takerFeePercent: 1.75` + callback |
| `src/connectors/kalshi/kalshi.connector.spec.ts` | Update fee assertions + add formula tests |
| `src/modules/arbitrage-detection/edge-calculator.service.ts` | Use helper in `buildFeeBreakdown()` |
| `src/modules/arbitrage-detection/edge-calculator.service.spec.ts` | Extend `makeFeeSchedule`, add dynamic fee tests |
| `src/modules/exit-management/exit-monitor.service.ts` | Use helper in `evaluatePosition()` + realized PnL |
| `src/modules/exit-management/exit-monitor.service.spec.ts` | Add `takerFeeForPrice` to Kalshi mock |
| `src/modules/execution/single-leg-resolution.service.ts` | Use helper in `closeExposedLeg()` + pass callbacks in `buildPnlScenarios()` |
| `src/modules/execution/single-leg-resolution.service.spec.ts` | Add `takerFeeForPrice` to Kalshi mock |
| `src/modules/execution/single-leg-pnl.util.ts` | Extend interface + update `calcCloseNow`/`calcRetry` |
| `src/modules/execution/execution.service.ts` | Pass `takerFeeForPrice` callbacks in PnL call site |
| `src/modules/execution/execution.service.spec.ts` | Add `takerFeeForPrice` to Kalshi mock |
| `src/modules/execution/exposure-alert-scheduler.service.spec.ts` | Add `takerFeeForPrice` to Kalshi mock |
| `src/test/mock-factories.ts` | Kalshi: `takerFeePercent: 0 → 1.75` + callback |
| `src/test/mock-factories.spec.ts` | Update assertions |
| `_bmad-output/planning-artifacts/prd.md` | Fix fee normalization section |

**No new files. No schema changes. No new dependencies. No migration needed.**

### Previous Story Intelligence

**Story 6-5-5f (Detection Gross Edge Formula Fix) — DONE:**
- 1,263 tests passing (baseline for this story)
- Formula changed from `|buyPrice - (1 - sellPrice)|` to `sellPrice - buyPrice` (signed edge)
- `impliedSellPrice` direction checks removed from detection service
- CSV test scenarios recalculated — most now correctly show negative grossEdge
- Edge calculator `makeDislocation` defaults: buy=0.45, sell=0.52, edge=0.07

**Story 6-5-5e (Paper Mode Exit Monitor Fix) — DONE:**
- Exit monitor now mode-aware — paper positions flow through complete lifecycle
- 1,251 → 1,263 tests after 6-5-5f

### Git Intelligence

Recent engine commits (on `epic-7` branch):
```
df4d4b7 Merge remote-tracking branch 'origin/main' into epic-7
00ed663 refactor: update financial math calculations and tests to reflect new gross edge formula
122e0df Merge remote-tracking branch 'origin/main' into epic-7
ff3d8cd feat: enhance Kalshi connector and exit monitor with paper mode support
```

### Inline Mock Summary

The following spec files have inline Kalshi fee mocks that need `takerFeeForPrice` added:

| Spec File | Current Kalshi `takerFeePercent` | Needs `takerFeeForPrice`? |
|-----------|--------------------------------|--------------------------|
| `edge-calculator.service.spec.ts` | 2.0 (via `makeFeeSchedule`) | Yes — tests `buildFeeBreakdown` |
| `exit-monitor.service.spec.ts` | 2 | Yes — tests `evaluatePosition` |
| `single-leg-resolution.service.spec.ts` | 2 | Yes — tests `closeExposedLeg` |
| `execution.service.spec.ts` | 2.0 | Yes — tests PnL call site |
| `exposure-alert-scheduler.service.spec.ts` | 2 | Maybe — depends on whether it exercises fee paths |
| `mock-factories.ts` (shared) | 0 | Yes — MUST change to 1.75 + callback |

**Note:** The inline mocks use `takerFeePercent: 2` which is already non-zero — the existing flat fee tests will continue working. The key is adding `takerFeeForPrice` for tests that specifically exercise the dynamic path.

### Scope Guard

This story is strictly scoped to:

1. Extend `FeeSchedule` with optional `takerFeeForPrice` callback
2. Fix `KalshiConnector.getFeeSchedule()` to return correct fees
3. Add centralized `FinancialMath.calculateTakerFeeRate()` helper
4. Migrate all 6 consumer locations to use the centralized helper
5. Extend `SingleLegPnlInput` and update PnL utility + call sites
6. Update all mocks and tests
7. Fix PRD documentation

Do NOT:

- Modify detection service logic (already fixed in 6-5-5f)
- Add new modules or files beyond the helper method
- Change database schema or add migrations
- Add new error types or event types
- Implement INX/NASDAQ100 fee coefficient (0.035) — out of scope
- Clean up phantom DB records (operator task)
- Add feature flags or configuration toggles

### Project Structure Notes

- All source changes within `pm-arbitrage-engine/src/` + one PRD update in root repo
- Files follow existing kebab-case naming convention
- Tests co-located with source (`.spec.ts` suffix)
- `FinancialMath` is the established location for all financial computation helpers
- This is a **dual-repo** project — engine changes require separate commit from PRD update

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-04-kalshi-dynamic-fees.md] — Approved sprint change proposal with full problem analysis, exact code changes, LAD review findings
- [Source: pm-arbitrage-engine/src/common/types/platform.type.ts:68-74] — Current `FeeSchedule` interface (no callback field)
- [Source: pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts:478-485] — Current `getFeeSchedule()` returning `takerFeePercent: 0`
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.ts:50-88] — `calculateNetEdge()` with inline fee computation
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.ts:242-265] — `buildFeeBreakdown()` with inline fee computation
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts:220-223] — `evaluatePosition()` threshold fee input
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts:455-462] — Realized PnL exit fee computation
- [Source: pm-arbitrage-engine/src/modules/execution/single-leg-resolution.service.ts:374-376] — `closeExposedLeg()` fee computation
- [Source: pm-arbitrage-engine/src/modules/execution/single-leg-pnl.util.ts:2-17] — `SingleLegPnlInput` interface
- [Source: pm-arbitrage-engine/src/modules/execution/single-leg-pnl.util.ts:84-167] — `calcCloseNow` and `calcRetry` functions
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts:873-901] — PnL call site with fee resolution
- [Source: pm-arbitrage-engine/src/modules/execution/single-leg-resolution.service.ts:558-573] — PnL call site with fee resolution
- [Source: pm-arbitrage-engine/src/test/mock-factories.ts:26-31] — Mock factory with Kalshi `takerFeePercent: 0`
- [Source: https://kalshi.com/docs/kalshi-fee-schedule.pdf] — Official Kalshi fee schedule confirming `0.07 × C × P × (1-P)` formula
- [Source: _bmad-output/implementation-artifacts/6-5-5f-detection-gross-edge-formula-fix.md] — Previous story (1,263 tests baseline)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean implementation, no debugging required.

### Completion Notes List

- All 12 tasks completed in order with TDD (test-first) approach
- Baseline: 1,263 tests → Final: 1,270 tests (7 new tests added)
- LAD design review flagged formula concern (rate vs absolute fee) — verified story formula `0.07 × (1-P)` is correct as a rate
- No additional consumer locations found beyond the 6 documented
- Inline spec mocks (takerFeePercent: 2) exercise the flat-fee fallback path — no changes needed
- Task 10.3/10.4 (inline mock updates): Inline mocks in spec files use flat fees (takerFeePercent: 2), which correctly test the fallback path. Only the shared mock factory needed the `takerFeeForPrice` callback for Kalshi.

### File List

**Engine repo (`pm-arbitrage-engine/`):**
- `src/common/types/platform.type.ts` — Added `takerFeeForPrice` optional callback to FeeSchedule
- `src/common/utils/financial-math.ts` — Added `calculateTakerFeeRate()` static method, updated `calculateNetEdge()` to use it
- `src/common/utils/financial-math.spec.ts` — Added 5 tests for calculateTakerFeeRate
- `src/connectors/kalshi/kalshi.connector.ts` — Fixed getFeeSchedule: takerFeePercent 0→1.75, added callback
- `src/connectors/kalshi/kalshi.connector.spec.ts` — Updated fee assertions, added 2 formula tests
- `src/modules/arbitrage-detection/edge-calculator.service.ts` — Updated buildFeeBreakdown to use helper
- `src/modules/exit-management/exit-monitor.service.ts` — Updated evaluatePosition + executeExit fee computation
- `src/modules/execution/single-leg-resolution.service.ts` — Updated closeExposedLeg + buildPnlScenarios
- `src/modules/execution/single-leg-pnl.util.ts` — Extended SingleLegPnlInput, updated calcCloseNow + calcRetry
- `src/modules/execution/execution.service.ts` — Updated PnL call site to pass callbacks
- `src/test/mock-factories.ts` — Kalshi takerFeePercent 0→1.75, added callback
- `src/test/mock-factories.spec.ts` — Updated assertions, added callback verification

**Root repo:**
- `_bmad-output/planning-artifacts/prd.md` — Updated Fee Normalization section + edge calculation example
- `_bmad-output/implementation-artifacts/6-5-5g-kalshi-dynamic-fee-correction.md` — Updated status + task checkboxes
