# Story 9.19: VWAP-Aware Dashboard Pricing & Position Calculation Consolidation

Status: done

<!-- Validation: Run validate-create-story for quality check before dev-story. -->

## Story

As a **system operator**,
I want **the dashboard to display VWAP-based close prices, P&L, and exit proximity that match the engine's actual threshold evaluation logic**,
so that **I can trust dashboard figures during morning scans and not be misled by top-of-book prices that diverge from the engine's depth-aware VWAP calculations**.

## Acceptance Criteria

### Backend — Shared Pure Functions

1. **`calculateVwapClosePrice(orderBook, closeSide, positionSize)`** exists in `common/utils/financial-math.ts` as an exported pure function. It accepts a `NormalizedOrderBook`, a close side (`'buy' | 'sell'`), and a `Decimal` position size. It returns `Decimal | null` — null when the relevant side has zero depth OR positionSize is zero/negative (invalid input guard). It walks price levels in **liquidity priority order** (bids highest-to-lowest for sell-to-close, asks lowest-to-highest for buy-to-close), accumulating quantity until `positionSize` is filled, returning `totalCost / filledQty`. `PriceLevel.price` and `.quantity` are `number` — convert to `FinancialDecimal` internally for calculation precision. If total available depth < positionSize, it returns the VWAP across all available depth (partial fill scenario — still more accurate than top-of-book; caller determines `depthSufficient`). Uses `FinancialDecimal` (the precision-configured clone in `financial-math.ts`) for all internal arithmetic. [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md#Story-9-19, ExitMonitorService.getClosePrice() lines 966-997]

2. **`calculateLegPnl(side, entryPrice, closePrice, size)`** exists in `common/utils/financial-math.ts` as an exported pure function. Buy side: `(closePrice - entryPrice) × size`. Sell side: `(entryPrice - closePrice) × size`. All params and return are `Decimal`. [Source: ThresholdEvaluatorService.calculateLegPnl() lines 202-214, PositionEnrichmentService.calculateLegPnl() lines 310-319 — verified identical]

3. **`calculateExitProximity(currentPnl, baseline, target)`** exists in `common/constants/exit-thresholds.ts` as an exported pure function (alongside existing `computeTakeProfitThreshold`). Formula: `clamp(0, 1, (currentPnl - baseline) / (target - baseline))`. Returns `Decimal`. Handles `target === baseline` (zero denominator) by returning `Decimal(0)`. Works for both SL (target < baseline → proximity rises as PnL drops) and TP (target > baseline → proximity rises as PnL rises). [Source: PositionEnrichmentService lines 270-290 — extracted and unified]

### Backend — IPriceFeedService Interface Extension

4. A new method **`getVwapClosePrice(platform, contractId, side, positionSize)`** is added to `IPriceFeedService` in `common/interfaces/price-feed-service.interface.ts`. Returns `Promise<{ price: Decimal; depthSufficient: boolean } | null>`. Null = no order book data at all. `depthSufficient: false` = partial depth, fell back to VWAP across available levels (or top-of-book if only one level). The existing `getCurrentClosePrice()` method is unchanged — it remains available for non-position contexts like match indicative pricing. [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md#Story-9-19 interface design decision]

5. **`PriceFeedService`** in `modules/data-ingestion/price-feed.service.ts` implements `getVwapClosePrice()` by fetching the order book from the connector and delegating to the shared `calculateVwapClosePrice()` pure function. It sets `depthSufficient: true` when total available depth >= positionSize, `false` otherwise. [Source: PriceFeedService.getCurrentClosePrice() lines 23-51 — extended]

### Backend — Service Refactoring

6. **`ExitMonitorService.getClosePrice()`** delegates its VWAP calculation body to the shared `calculateVwapClosePrice()` from `financial-math.ts`. The method signature and behavior remain identical. It does NOT call `PriceFeedService` — it continues to use the connector's order book directly (no cross-module dependency created). [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md "What NOT To Do" — ExitMonitorService calls pure function directly]

7. **`ThresholdEvaluatorService.calculateLegPnl()`** delegates to the shared `calculateLegPnl()` from `financial-math.ts`. The private method stays as a thin wrapper for test stability. [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md#Story-9-19]

8. **`PositionEnrichmentService`** is refactored:
   - Calls `priceFeed.getVwapClosePrice()` instead of `priceFeed.getCurrentClosePrice()`, passing the position's fill sizes.
   - Delegates per-leg P&L to shared `calculateLegPnl()`.
   - Delegates SL/TP proximity to shared `calculateExitProximity()`.
   - Propagates `depthSufficient` flags per-platform through to the response DTO.
   - When `getVwapClosePrice()` returns null (no order book data), existing behavior is preserved: enrichment returns `currentPrices: null`.
   [Source: PositionEnrichmentService lines 93-98 (current top-of-book calls), lines 155-167 (duplicate calculateLegPnl), lines 270-290 (inline proximity)]

### Backend — DTO Changes

9. **`CurrentPricesDto`** in `dashboard/dto/position-summary.dto.ts` gains two new optional boolean fields: `kalshiDepthSufficient` and `polymarketDepthSufficient`. Default `true` when VWAP is fully backed, `false` when depth was insufficient and the price is an estimate. Swagger documentation includes the business meaning. [Derived from: disambiguation decision #1 — confirmed by operator]

10. **`PositionFullDetailDto`** in `dashboard/dto/position-detail.dto.ts` gains the same depth-sufficiency fields within its `currentPrices` inline type. **Note:** This DTO uses an inline `{ kalshi: string | null; polymarket: string | null }` type (NOT `CurrentPricesDto`), so the depth fields must be added independently and kept in sync with AC #9. [Derived from: AC #9 consistency, verified at position-detail.dto.ts line 151]

### Frontend — Depth-Insufficient Visual Treatment

11. When `depthSufficient === false` for either platform, the dashboard visually distinguishes estimated values using three stacked signals that require **no hover** to interpret:
    - **Tilde prefix (`~`):** The price/PnL value is prefixed with `~` (e.g., `~0.150`, `~$6.42`). Universal "approximate" convention in quantitative contexts.
    - **Desaturated text:** The value renders at `opacity-60` on its existing color class (prices become muted, PnL green/red becomes washed out). Peripheral vision catches the contrast difference during scanning.
    - **Dashed amber underline:** `border-b border-dashed border-amber-400/50` on the value span. The dashed pattern evokes "projected/estimated" (solid = actual, dashed = estimated — a culturally ingrained data visualization convention).
    - **Tooltip (supplementary):** On hover, explains "Estimated — thin order book depth. Using best available price." Tooltip is additive, not the primary indicator.
    [Derived from: operator feedback on disambiguation #1 — "must be obvious at a glance during morning scan, no hover required"]

12. The depth-insufficient treatment applies to: **price cells** (per-platform close prices), **PnL cell** (if either platform's depth is insufficient, PnL is estimated), and **exit proximity indicators** (SL/TP proximity values derived from estimated prices). On the **detail page**, the same treatment applies with an additional inline micro-label "Est." in muted amber next to estimated prices. [Derived from: AC #11 extension to all dependent values]

13. When **both** platforms have sufficient depth, no visual indicators appear — values render exactly as they do today. No regression in the confident-value display path. [Derived from: implicit — visual treatment is additive only]

### Frontend — API Client Regeneration

14. The dashboard SPA's generated API client (`swagger-typescript-api`) is regenerated to pick up the new `kalshiDepthSufficient` and `polymarketDepthSufficient` fields on `CurrentPricesDto`. [Source: pm-arbitrage-dashboard architecture — generated client pattern]

### Testing

15. `calculateVwapClosePrice()` has dedicated unit tests in `financial-math.spec.ts` covering: single-level book (returns that level's price), multi-level book (correct weighted average), partial depth (VWAP across all available levels when depth < positionSize), zero-depth side (returns null), empty order book (returns null), zero position size (returns null), position size exactly matching available depth (edge case), correct level traversal order (bids highest-first, asks lowest-first). All tests use `Decimal` values. Note: `depthSufficient` is determined by the caller (`PriceFeedService`), not the pure function — pure function tests verify only the VWAP math and null returns. [Source: ExitMonitorService.getClosePrice() spec — existing VWAP tests as reference patterns]

16. `calculateLegPnl()` has dedicated unit tests in `financial-math.spec.ts` covering: buy-side profit, buy-side loss, sell-side profit, sell-side loss, zero-size position (returns 0). [Source: ThresholdEvaluatorService spec — existing leg P&L test patterns]

17. `calculateExitProximity()` has dedicated unit tests in `exit-thresholds.spec.ts` covering: mid-range value, at-threshold (returns 1), at-baseline (returns 0), beyond-threshold (clamped to 1), beyond-baseline (clamped to 0), zero denominator (returns 0). Both SL direction (target < baseline) and TP direction (target > baseline). [Source: PositionEnrichmentService lines 270-290 — extracted logic]

18. `PriceFeedService.getVwapClosePrice()` has unit tests verifying: delegates to `calculateVwapClosePrice`, sets `depthSufficient` correctly based on available vs requested depth, returns null when connector returns no order book. [Derived from: AC #5]

19. `PositionEnrichmentService` existing tests are updated: mocks switch from `getCurrentClosePrice` to `getVwapClosePrice` returning `{ price, depthSufficient }`. New test cases verify: depthSufficient flags propagate to DTO output, estimated prices produce correct tilde/muted rendering data. [Source: position-enrichment.service.spec.ts — 30+ existing mock calls to update]

20. `ExitMonitorService.getClosePrice()` existing VWAP tests continue to pass — the delegation to the shared pure function doesn't change behavior. [Source: exit-monitor.service.spec.ts lines 474-519, 1437-1519]

21. `ThresholdEvaluatorService` existing tests continue to pass — the delegation wrapper preserves the same interface. [Source: threshold-evaluator.service.spec.ts]

## Tasks / Subtasks

### Phase 1: Shared Pure Functions (AC: #1, #2, #3)

- [x] **Task 1:** Extract `calculateVwapClosePrice()` to `common/utils/financial-math.ts` (AC: #1)
  - [x] 1.1: Copy VWAP logic from `ExitMonitorService.getClosePrice()` lines 982-996 into a standalone exported function
  - [x] 1.2: Adapt to accept `NormalizedOrderBook` + close side + position size (pure function, no connector dependency). Ensure bids are consumed highest-to-lowest, asks lowest-to-highest. Convert `PriceLevel.price`/`.quantity` from `number` to `FinancialDecimal` internally.
  - [x] 1.3: Handle edge cases: null/empty book, empty side array, zero/negative position size (return null)
  - [x] 1.4: Write unit tests in `financial-math.spec.ts` (AC: #15)

- [x] **Task 2:** Extract `calculateLegPnl()` to `common/utils/financial-math.ts` (AC: #2)
  - [x] 2.1: Create exported function matching the existing private method signature
  - [x] 2.2: Write unit tests in `financial-math.spec.ts` (AC: #16)

- [x] **Task 3:** Extract `calculateExitProximity()` to `common/constants/exit-thresholds.ts` (AC: #3)
  - [x] 3.1: Implement `clamp(0, 1, (currentPnl - baseline) / (target - baseline))` with zero-denom guard
  - [x] 3.2: Write unit tests in `exit-thresholds.spec.ts` (AC: #17)

### Phase 2: Interface & PriceFeedService (AC: #4, #5)

- [x] **Task 4:** Extend `IPriceFeedService` with `getVwapClosePrice()` (AC: #4)
  - [x] 4.1: Add method signature to `common/interfaces/price-feed-service.interface.ts`
  - [x] 4.2: Define return type `{ price: Decimal; depthSufficient: boolean } | null`

- [x] **Task 5:** Implement `getVwapClosePrice()` in `PriceFeedService` (AC: #5)
  - [x] 5.1: Fetch order book from connector (reuse existing connector resolution logic)
  - [x] 5.2: Delegate to `calculateVwapClosePrice()` pure function
  - [x] 5.3: Determine `depthSufficient` by comparing available depth to requested position size
  - [x] 5.4: Write unit tests (AC: #18)

### Phase 3: Service Refactoring (AC: #6, #7, #8)

- [x] **Task 6:** Refactor `ExitMonitorService.getClosePrice()` to delegate to shared function (AC: #6)
  - [x] 6.1: Replace inline VWAP loop with call to `calculateVwapClosePrice()`
  - [x] 6.2: Verify all existing tests pass without modification (AC: #20)

- [x] **Task 7:** Refactor `ThresholdEvaluatorService.calculateLegPnl()` to delegate (AC: #7)
  - [x] 7.1: Replace method body with call to shared `calculateLegPnl()`
  - [x] 7.2: Keep private method wrapper for test stability
  - [x] 7.3: Verify all existing tests pass without modification (AC: #21)

- [x] **Task 8:** Refactor `PositionEnrichmentService` (AC: #8)
  - [x] 8.1: Replace `getCurrentClosePrice()` calls with `getVwapClosePrice()`, passing position fill sizes
  - [x] 8.2: Replace private `calculateLegPnl()` with shared function call
  - [x] 8.3: Replace inline SL/TP proximity formulas with `calculateExitProximity()` calls
  - [x] 8.4: Propagate `depthSufficient` flags to enrichment result. Note: `PositionEnrichmentService` returns an `EnrichedPosition` internal type that maps to DTOs in `DashboardService` — add depth flags to the enrichment result type so they flow through to DTO mapping.
  - [x] 8.5: Update existing test mocks from `getCurrentClosePrice` → `getVwapClosePrice` (AC: #19)

### Phase 4: DTO Changes (AC: #9, #10)

- [x] **Task 9:** Add depth-sufficiency fields to DTOs (AC: #9, #10)
  - [x] 9.1: Add `kalshiDepthSufficient` and `polymarketDepthSufficient` to `CurrentPricesDto`
  - [x] 9.2: Add same fields to `PositionFullDetailDto.currentPrices` inline type (this DTO does NOT reuse `CurrentPricesDto` — fields must be added independently and kept in sync)
  - [x] 9.3: Add Swagger `@ApiPropertyOptional` decorators with clear descriptions
  - [x] 9.4: Wire enrichment result through `DashboardService` to DTO mapping (automatic — EnrichedPosition.currentPrices flows through directly)

### Phase 5: Dashboard SPA (AC: #11, #12, #13, #14)

- [x] **Task 10:** Regenerate API client (AC: #14)
  - [x] 10.1: Run `swagger-typescript-api` against updated backend Swagger spec
  - [x] 10.2: Verify new fields appear in generated `CurrentPricesDto` type

- [x] **Task 11:** Implement depth-insufficient visual treatment (AC: #11, #12, #13)
  - [x] 11.1: Extend `PnlCell` shared renderer to accept an `isEstimated` boolean prop (computed by the page: `true` if either platform's `depthSufficient === false`) — apply tilde prefix, `opacity-60`, dashed amber underline when true
  - [x] 11.2: Create or extend price cell component with same treatment (inline in PositionsPage + PositionDetailPage)
  - [x] 11.3: Extend `ExitProximityIndicator` to accept and propagate depth sufficiency — apply tilde + muted treatment to proximity values
  - [x] 11.4: Wire depth-sufficiency flags through `PositionsPage.tsx` table columns
  - [x] 11.5: Wire through `PositionDetailPage.tsx` — add inline "Est." micro-label in muted amber next to estimated prices
  - [x] 11.6: Verify confident-value path has zero visual regression (AC: #13)

### Phase 6: Operational (no code change)

- [x] **Task 12:** Document Telegram deployment message in completion notes (AC: operator communication)
  - [x] 12.1: Draft suggested message text already in story Dev Notes section

## Dev Notes

### Architecture Compliance

**Module dependency rules — verified compliant:**
- Shared pure functions in `common/utils/` and `common/constants/` — importable by all modules per architecture rules [Source: CLAUDE.md#Module-Dependency-Rules]
- `ExitMonitorService` calls `calculateVwapClosePrice()` from `common/utils/` with the order book it already fetches from the connector — no new cross-module dependency [Source: sprint-change-proposal "What NOT To Do"]
- `PositionEnrichmentService` calls `PriceFeedService` (injected via `IPriceFeedService`) — existing dependency, no new import path
- `PriceFeedService` fetches order books from connectors — existing `data-ingestion → connectors` dependency [Source: CLAUDE.md#Module-Dependency-Rules allowed imports]
- **No forbidden imports created**

### Consolidation Pattern (established by Story 9-18)

Story 9-18 set the precedent: extract duplicated financial logic into shared pure functions in `common/`, then have both `ThresholdEvaluatorService` and `PositionEnrichmentService` delegate to them. That story extracted `computeTakeProfitThreshold()` into `common/constants/exit-thresholds.ts`. This story follows the identical pattern for:
- VWAP close price calculation → `common/utils/financial-math.ts`
- Leg P&L calculation → `common/utils/financial-math.ts`
- Exit proximity calculation → `common/constants/exit-thresholds.ts`
[Source: 9-18-take-profit-threshold-formula-fix.md — completion notes, file list]

### Key Implementation Details

**VWAP calculation (source of truth: `ExitMonitorService.getClosePrice()` lines 966-997):**
- Close side determination: buy position → sell to close (walk bids), sell position → buy to close (walk asks)
- Walk price levels: accumulate `level.quantity` until `positionSize` is filled
- Formula: `VWAP = Σ(price × min(quantity, remaining)) / Σ(min(quantity, remaining))`
- If total depth < positionSize: compute VWAP across all available depth (partial fill), signal `depthSufficient: false` at call site
- If zero levels on relevant side: return `null`
- All arithmetic uses `Decimal` (decimal.js) — never native JS operators [Source: CLAUDE.md#Domain-Rules]

**NormalizedOrderBook type (verified stable):**
```typescript
interface NormalizedOrderBook {
  platformId: PlatformId;
  contractId: ContractId;
  bids: PriceLevel[];  // { price: number; quantity: number }
  asks: PriceLevel[];
  timestamp: Date;
  sequenceNumber?: number;
  platformHealth?: 'healthy' | 'degraded' | 'offline';
}
```
Note: `PriceLevel.price` and `.quantity` are `number` (not Decimal). The VWAP function must convert to `Decimal` internally for calculation precision. [Source: common/types/normalized-order-book.type.ts lines 9-17]

**Exit proximity baseline definition:**
`baseline` = `entryCostBaseline` — the MtM (mark-to-market) deficit at entry, typically ≤ 0 (computed by `FinancialMath.computeEntryCostBaseline()`, story 9-18). `target` = stop-loss threshold (negative, below baseline) or take-profit threshold (positive, above baseline). The unified formula `(currentPnl - baseline) / (target - baseline)` works for both directions because when target < baseline (SL), both numerator and denominator are negative as PnL drops, producing a positive proximity rising toward 1. [Source: ThresholdEvaluatorService lines 109-130, PositionEnrichmentService lines 259-268]

**FinancialDecimal usage:**
`financial-math.ts` defines `FinancialDecimal = Decimal.clone({ precision: 20 })` (line 7). All new pure functions in this file (`calculateVwapClosePrice`, `calculateLegPnl`) MUST use `FinancialDecimal` (not plain `Decimal`) to match the existing pattern and avoid global precision contamination. Functions in `exit-thresholds.ts` (`calculateExitProximity`) should use plain `Decimal` — consistent with existing `computeTakeProfitThreshold()` in that file. [Source: financial-math.ts line 7]

**Combined P&L pattern (stays inline — not extracted):**
Both services compute: `kalshiPnl.plus(polymarketPnl).minus(totalExitFees)`. This is a 3-term sum that doesn't warrant a separate function. Exit fees are computed per-leg as `closePrice.mul(size).mul(feeRate)`. [Source: ThresholdEvaluatorService lines 90-98, PositionEnrichmentService lines 170-179]

**Depth-insufficient visual treatment (dashboard SPA):**
Three stacked signals, no hover required:
1. Tilde prefix: `~0.150` / `~$6.42`
2. Desaturation: `opacity-60` on existing color class
3. Dashed amber underline: `border-b border-dashed border-amber-400/50`
4. Tooltip (supplementary): "Estimated — thin order book depth. Using best available price."

Detail page additionally shows inline "Est." micro-label in muted amber (`text-amber-500 text-xs font-medium`).

All treatment is additive — confident values render identically to current behavior.

### Files Modified

| File | Change Type | Description |
|---|---|---|
| `src/common/utils/financial-math.ts` | Modify | Add `calculateVwapClosePrice()`, `calculateLegPnl()` exported functions |
| `src/common/utils/financial-math.spec.ts` | Modify | Add VWAP + leg P&L unit tests |
| `src/common/constants/exit-thresholds.ts` | Modify | Add `calculateExitProximity()` exported function |
| `src/common/constants/exit-thresholds.spec.ts` | Modify | Add proximity unit tests |
| `src/common/interfaces/price-feed-service.interface.ts` | Modify | Add `getVwapClosePrice()` method |
| `src/modules/data-ingestion/price-feed.service.ts` | Modify | Implement `getVwapClosePrice()` |
| `src/modules/data-ingestion/price-feed.service.spec.ts` | Modify | Add `getVwapClosePrice()` tests |
| `src/modules/exit-management/exit-monitor.service.ts` | Modify | Delegate `getClosePrice()` VWAP body to shared function |
| `src/modules/exit-management/threshold-evaluator.service.ts` | Modify | Delegate `calculateLegPnl()` to shared function |
| `src/dashboard/position-enrichment.service.ts` | Modify | Switch to `getVwapClosePrice()`, delegate P&L + proximity to shared functions, propagate depth flags |
| `src/dashboard/position-enrichment.service.spec.ts` | Modify | Update mocks (`getCurrentClosePrice` → `getVwapClosePrice`), add depth-sufficiency tests |
| `src/dashboard/dto/position-summary.dto.ts` | Modify | Add `kalshiDepthSufficient`, `polymarketDepthSufficient` to `CurrentPricesDto` |
| `src/dashboard/dto/position-detail.dto.ts` | Modify | Add depth-sufficiency fields to `currentPrices` |

### Dashboard SPA Files Modified

| File | Change Type | Description |
|---|---|---|
| `pm-arbitrage-dashboard/src/api/generated/Api.ts` | Regenerate | Updated `CurrentPricesDto` with depth fields |
| `pm-arbitrage-dashboard/src/components/PnlCell.tsx` | Modify | Accept `depthSufficient` prop, render tilde + opacity + underline |
| `pm-arbitrage-dashboard/src/components/ExitProximityIndicator.tsx` | Modify | Accept depth sufficiency, apply muted treatment |
| `pm-arbitrage-dashboard/src/pages/PositionsPage.tsx` | Modify | Wire depth flags through table columns |
| `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx` | Modify | Wire depth flags, add "Est." micro-label |

### What NOT To Do

- **Do NOT import `PriceFeedService` from `exit-management`** — ExitMonitorService continues using the connector's order book directly. The shared pure function is in `common/utils/`, which all modules may import. [Source: sprint-change-proposal "What NOT To Do"]
- **Do NOT remove `ThresholdEvaluatorService.calculateLegPnl()` or `ExitMonitorService.getClosePrice()` as methods** — they should delegate to shared functions while retaining their method signatures for test stability. [Source: sprint-change-proposal "What NOT To Do"]
- **Do NOT change `getCurrentClosePrice()` signature or behavior** — it remains for non-position contexts like match indicative pricing.
- **Do NOT use native JS arithmetic operators on monetary values** — all calculations via `Decimal` methods [Source: CLAUDE.md#Domain-Rules]
- **Do NOT add client-side P&L or VWAP calculations in the dashboard SPA** — the SPA consumes pre-computed values from the backend API.
- **Do NOT forget to update BOTH DTOs** when changing depth-sufficiency field names/types — `CurrentPricesDto` (position-summary.dto.ts) and `PositionFullDetailDto.currentPrices` (position-detail.dto.ts) define these fields independently (no shared type).

### Project Structure Notes

- All shared pure functions follow existing patterns: `financial-math.ts` for calculation utilities, `exit-thresholds.ts` for threshold-related constants and functions
- Test co-location: specs next to source files
- DTO changes are additive (new optional fields) — backward compatible with any older dashboard client

### References

- [Source: sprint-change-proposal-2026-03-14-vwap-consolidation.md] — Root cause analysis, design decisions, artifact changes table
- [Source: 9-18-take-profit-threshold-formula-fix.md] — Shared function extraction pattern (computeTakeProfitThreshold precedent)
- [Source: CLAUDE.md#Module-Dependency-Rules] — Allowed/forbidden imports
- [Source: CLAUDE.md#Domain-Rules] — Decimal.js mandate, price normalization
- [Source: ExitMonitorService.getClosePrice() lines 966-997] — Existing VWAP implementation (source of truth)
- [Source: ThresholdEvaluatorService.calculateLegPnl() lines 202-214] — Existing leg P&L (duplication target)
- [Source: PositionEnrichmentService lines 93-98, 155-167, 270-290, 310-319] — Dashboard enrichment (refactoring target)
- [Source: IPriceFeedService lines 9-28] — Current interface (extension target)
- [Source: position-summary.dto.ts CurrentPricesDto lines 31-47] — DTO extension target

### Suggested Telegram Deployment Message

> Dashboard pricing update: Position close prices, P&L, and exit proximity now use VWAP (volume-weighted average price) across order book depth, matching the engine's actual evaluation logic. Previously, the dashboard used top-of-book prices which could diverge significantly from the engine's calculations — especially for positions with large size relative to available liquidity. Exit proximity values may appear more conservative than before. This is the accurate number. Positions where order book depth is insufficient for full VWAP will show estimated values with a `~` prefix and muted styling.

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
N/A

### Completion Notes List

- **Test count:** 2081 → 2112 (+31 tests). All passing.
- **Lad MCP code review completed:** Primary reviewer (moonshotai/kimi-k2.5) returned findings. Secondary reviewer timed out. Fixed 1 finding (FinancialDecimal.min consistency). Remaining findings were false positives or by-design decisions — documented inline.
- **Code review #2 completed 2026-03-15:** Fixed 3 MEDIUM (PositionDetailPage missing tooltip on estimated prices, `calculateLegPnl` not using FinancialDecimal, missing EXIT_PARTIAL VWAP size test), 3 LOW noted (per-call Decimal(1) allocation in calculateExitProximity, calculateLegPnl side typed as string, ExitMonitorService getClosePrice return type inconsistency).
- **Key design decisions:**
  - `calculateVwapClosePrice` parameter named `closeSide` follows existing codebase convention where 'buy' means "the position was a buy → walk bids to sell-to-close". This is consistent with `getCurrentClosePrice`, `ExitMonitorService.getClosePrice()`, and `PositionEnrichmentService` call patterns.
  - `depthSufficient` defaults to `true` when VWAP returns null (price unavailable). Rationale: prices are null in that case, so enrichment exits early as 'failed'/'partial'. Defaulting to true prevents false estimation indicators on error paths.
  - Price cell depth-insufficient treatment implemented inline in PositionsPage/PositionDetailPage rather than creating a separate reusable component. Per-cell Tooltip wrapping requires direct inline implementation for the price values.
  - DashboardService DTO mapping requires no changes — `EnrichedPosition.currentPrices` flows through directly since `DashboardService` assigns `enrichment.data.currentPrices` directly to the DTO, and the new depth fields pass through the spread.
- **No deviations** from Dev Notes guidance.
- **Dashboard SPA:** TypeScript passes (`tsc --noEmit`), Vite build succeeds.

### File List

**Engine (pm-arbitrage-engine/)**
| File | Change |
|---|---|
| `src/common/utils/financial-math.ts` | Added `calculateVwapClosePrice()`, `calculateLegPnl()` |
| `src/common/utils/financial-math.spec.ts` | Added 14 tests (9 VWAP + 5 leg P&L) |
| `src/common/utils/index.ts` | Exported new functions |
| `src/common/constants/exit-thresholds.ts` | Added `calculateExitProximity()` |
| `src/common/constants/exit-thresholds.spec.ts` | Added 8 proximity tests |
| `src/common/interfaces/price-feed-service.interface.ts` | Added `getVwapClosePrice()` method |
| `src/modules/data-ingestion/price-feed.service.ts` | Implemented `getVwapClosePrice()` |
| `src/modules/data-ingestion/price-feed.service.spec.ts` | Added 4 VWAP tests |
| `src/modules/exit-management/exit-monitor.service.ts` | Delegated VWAP body to shared function |
| `src/modules/exit-management/threshold-evaluator.service.ts` | Delegated `calculateLegPnl` to shared function |
| `src/dashboard/position-enrichment.service.ts` | Refactored: VWAP, shared P&L, shared proximity, depth flags |
| `src/dashboard/position-enrichment.service.spec.ts` | Rewrote mocks (getCurrentClosePrice→getVwapClosePrice), +4 depth tests |
| `src/dashboard/dto/position-summary.dto.ts` | Added `kalshiDepthSufficient`, `polymarketDepthSufficient` |
| `src/dashboard/dto/position-detail.dto.ts` | Added depth fields to inline `currentPrices` type |

**Dashboard SPA (pm-arbitrage-dashboard/)**
| File | Change |
|---|---|
| `src/api/generated/Api.ts` | Regenerated — depth fields in `CurrentPricesDto` + `PositionFullDetailDto` |
| `src/components/cells/PnlCell.tsx` | Added `isEstimated` prop with tilde/opacity/underline/tooltip treatment |
| `src/components/ExitProximityIndicator.tsx` | Added `isEstimated` prop with muted/tilde treatment |
| `src/pages/PositionsPage.tsx` | Wired depth flags through price, P&L, and exit proximity columns |
| `src/pages/PositionDetailPage.tsx` | Wired depth flags + "Est." micro-label on detail page |
