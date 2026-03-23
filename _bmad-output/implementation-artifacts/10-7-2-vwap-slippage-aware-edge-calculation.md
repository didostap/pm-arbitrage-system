# Story 10.7.2: VWAP Slippage-Aware Opportunity Edge Calculation

Status: done

## Story

As an operator,
I want the system to calculate expected edge using VWAP fill prices at target position size,
so that the displayed edge accurately reflects what execution would actually achieve.

## Context

Analysis of 202 paper trading positions revealed 0% profitability. Expected edge at entry averaged +3.4% but collapsed to -17.5% on recalculation — a -20.83% average decay. Root cause: detection uses best-level prices (best bid/ask at `[0]`); execution fills across multiple levels at worse prices. The `calculateVwapClosePrice()` utility in `financial-math.ts` already walks the book to compute volume-weighted average prices — it just needs to be called at the detection stage.

**Depends on:** 10-7-1 (completed — shares depth-fetching pattern, dual-leg gate already in place).

## Acceptance Criteria

1. **AC-1: VWAP-based edge replaces best-bid/ask edge**
   - **Given** an opportunity is detected with a cross-platform price gap
   - **When** the edge calculator computes net edge
   - **Then** it uses `calculateVwapClosePrice()` to estimate fill prices for BOTH legs at the target contract count
   - **And** the VWAP-estimated prices replace `dislocation.buyPrice` / `dislocation.sellPrice` in the `FinancialMath.calculateNetEdge()` call
   - **And** the edge includes estimated fees and gas at the VWAP-estimated prices
   - **And** `grossEdge` is recalculated as `vwapSellPrice - vwapBuyPrice` (not the best-level grossEdge from RawDislocation)

2. **AC-2: Partial fill handling**
   - **Given** order book depth is insufficient to VWAP-price the full target contract count
   - **When** `calculateVwapClosePrice()` fills partially (remaining qty > 0)
   - **Then** the edge is calculated at the partial fill VWAP (the function already returns correct VWAP for partial fills)
   - **And** if the fillable quantity on either leg is below `DETECTION_MIN_FILL_RATIO` × target contracts, the opportunity is filtered with reason `"insufficient_vwap_depth"` before the edge threshold check

3. **AC-3: VWAP-adjusted edge threshold filtering**
   - **Given** a computed VWAP-based net edge
   - **When** it falls below the minimum edge threshold (existing `DETECTION_MIN_EDGE_THRESHOLD` × degradation multiplier)
   - **Then** the opportunity is filtered with reason `"below_threshold"` (unchanged reason — the threshold check just uses VWAP edge now)
   - **And** both the best-level edge and VWAP-adjusted edge are logged for comparison

4. **AC-4: Best-level vs VWAP edge comparison logging**
   - **Given** an opportunity is processed (whether filtered or passed)
   - **When** edge calculation completes
   - **Then** the `OpportunityIdentifiedEvent` payload includes both `bestLevelNetEdge` and `netEdge` (VWAP-based)
   - **And** the `OpportunityFilteredEvent` carries the VWAP-based `netEdge`
   - **And** `FilteredDislocation` includes a `bestLevelNetEdge` field for comparison logging

5. **AC-5: Configurable detection fill ratio**
   - **Given** the VWAP depth gate for detection
   - **When** the engine starts
   - **Then** `DETECTION_MIN_FILL_RATIO` is loaded from EngineConfig DB (default: 0.25)
   - **And** the setting appears in the dashboard Settings page under "Detection & Edge" group
   - **And** hot-reload works via the CONFIG_SETTINGS_UPDATED event

## Design Decisions

### VWAP Side Mapping for Entry

`calculateVwapClosePrice()` uses a `closeSide` parameter that determines which side of the book to walk:

- `closeSide='buy'` → walks **bids** (descending, highest first)
- `closeSide='sell'` → walks **asks** (ascending, lowest first)

For **entry** into an arbitrage position:

- **Buy leg** (buying contracts at ask): walk asks → `closeSide='sell'` → `calculateVwapClosePrice(buyOrderBook, 'sell', targetContracts)`
- **Sell leg** (selling contracts at bid): walk bids → `closeSide='buy'` → `calculateVwapClosePrice(sellOrderBook, 'buy', targetContracts)`

This is counterintuitive — document in a code comment.

### Target Contract Count Conversion

`positionSizeUsd` is in USD; `calculateVwapClosePrice()` needs contract count. Convert using best-level prices (not VWAP — avoids chicken-and-egg):

```
buyTargetContracts = positionSizeUsd / dislocation.buyPrice  (best ask)
sellTargetContracts = positionSizeUsd / dislocation.sellPrice (best bid)
```

Use `Decimal.ceil()` to round up (conservative — ensures we don't understate the VWAP impact). This approximation is acceptable: detection sizing is indicative, execution does precise sizing.

### Separate `DETECTION_MIN_FILL_RATIO` (Not Shared with Execution)

`EXECUTION_MIN_FILL_RATIO` exists in the execution module (default 0.25). Detection needs its own because: (a) different pipeline stage, different semantics — detection filters early to avoid wasting risk validation cycles; (b) operator may want different thresholds for detection vs execution; (c) module dependency rules forbid detection importing from execution.

### No Changes to RawDislocation

`RawDislocation.buyPrice` and `sellPrice` remain best-level prices. They are still needed for: (a) target contract count conversion, (b) best-level edge comparison logging. VWAP prices are computed within `processSingleDislocation()` only.

### grossEdge Recalculation

The existing `grossEdge` in `RawDislocation` is `sellPrice - buyPrice` (best-level). After VWAP, gross edge must be recomputed as `vwapSellPrice - vwapBuyPrice`. Do NOT pass the old `grossEdge` to `calculateNetEdge()` — pass the VWAP-based gross edge.

## Tasks / Subtasks

- [x] **Task 1: Add `DETECTION_MIN_FILL_RATIO` config setting** (AC: #5)
  - [x] 1.1 Add `DETECTION_MIN_FILL_RATIO` to `src/common/config/env.schema.ts` — use `decimalString('0.25')` validator
  - [x] 1.2 Add `detectionMinFillRatio` to `src/common/config/config-defaults.ts` — `{ envKey: 'DETECTION_MIN_FILL_RATIO', defaultValue: '0.25' }`
  - [x] 1.3 Add `detectionMinFillRatio` to `src/common/config/settings-metadata.ts` — group: `SettingsGroup.DetectionEdge`, type: `'decimal'`, label: `'Min VWAP Fill Ratio'`, description: `'Minimum ratio of fillable depth to target contracts for VWAP edge calculation. Opportunities below this are filtered as insufficient depth.'`
  - [x] 1.4 Add `detectionMinFillRatio` to `src/dashboard/dto/update-settings.dto.ts` — `@IsOptional() @IsString() @Matches(DECIMAL_REGEX)`
  - [x] 1.5 Add `detectionMinFillRatio` column to Prisma `EngineConfig` model — `Decimal? @map("detection_min_fill_ratio") @db.Decimal(20, 8)` in the Edge Detection section
  - [x] 1.6 Create Prisma migration: `pnpm prisma migrate dev --name add-detection-min-fill-ratio`
  - [x] 1.7 Add `detectionMinFillRatio` to `src/common/config/effective-config.types.ts` — `detectionMinFillRatio: string;`
  - [x] 1.8 Add `detectionMinFillRatio` to `src/persistence/repositories/engine-config.repository.ts` resolve chain
  - [x] 1.9 Add `detectionMinFillRatio` to `SERVICE_RELOAD_MAP` in `src/dashboard/settings.service.ts` — route to `'detection'`
  - [x] 1.10 Wire reload handler for detection in `settings.service.ts` — pass `detectionMinFillRatio` to the detection edge calculator

- [x] **Task 2: Add reload support to EdgeCalculatorService** (AC: #5)
  - [x] 2.1 Add `private detectionMinFillRatio: Decimal` field, initialized from config in constructor: `new FinancialDecimal(this.configService.get<number>('DETECTION_MIN_FILL_RATIO', 0.25))`
  - [x] 2.2 Add startup validation in `onModuleInit()` — `DETECTION_MIN_FILL_RATIO` must be > 0 and ≤ 1.0, same pattern as existing `validateConfig()`
  - [x] 2.3 Add `reloadConfig(settings: { detectionMinFillRatio?: string }): void` method following the `ExecutionService.reloadConfig()` pattern — validate with `Number()` + range check, store as `Decimal`
  - [x] 2.4 Register handler in `settings.service.ts`: used `EdgeCalculatorService` class directly (no token needed) — `this.tryRegisterHandler('detection', EdgeCalculatorService, (svc, cfg) => svc.reloadConfig({ detectionMinFillRatio: cfg.detectionMinFillRatio }))`

- [x] **Task 3: Implement VWAP edge calculation in processSingleDislocation** (AC: #1, #2, #3)
  - [x] 3.1 At the top of `processSingleDislocation()`, after fee schedules and gas estimate are obtained, compute target contract counts. Guard against zero prices (possible in degenerate order books — filter and return if either price is zero):
    ```typescript
    if (dislocation.buyPrice.isZero() || dislocation.sellPrice.isZero()) {
      // Filter: zero price means empty book side — cannot compute VWAP
      filtered.push({ pairEventDescription, netEdge: '0', threshold: 'N/A', reason: 'insufficient_vwap_depth' });
      return;
    }
    const buyTargetContracts = this.positionSizeUsd.div(dislocation.buyPrice).ceil();
    const sellTargetContracts = this.positionSizeUsd.div(dislocation.sellPrice).ceil();
    ```
  - [x] 3.2 Compute VWAP prices for both legs:
    ```typescript
    // Buy leg: buying at ask side → closeSide='sell' walks asks
    const vwapBuyPrice = calculateVwapClosePrice(dislocation.buyOrderBook, 'sell', buyTargetContracts);
    // Sell leg: selling at bid side → closeSide='buy' walks bids
    const vwapSellPrice = calculateVwapClosePrice(dislocation.sellOrderBook, 'buy', sellTargetContracts);
    ```
  - [x] 3.3 Handle null VWAP (empty book side): if either returns `null`, filter with reason `"insufficient_vwap_depth"` — emit `OpportunityFilteredEvent`, push to `filtered[]`, return
  - [x] 3.4 Compute fillable quantities and check fill ratio:
    - Track `filledQty` from each leg (need to compute this — `calculateVwapClosePrice` doesn't return it)
    - **Option A (recommended):** Extract a helper `calculateVwapWithFillInfo()` that returns `{ vwap: Decimal, filledQty: Decimal }` — reuses the same loop logic as `calculateVwapClosePrice()` but also returns the filled quantity. Place in `financial-math.ts` next to the existing function.
    - **Option B:** Compute fill ratio by walking the book a second time (wasteful). Avoid.
    - If `filledQty.div(targetContracts).lt(this.detectionMinFillRatio)` on either leg → filter with reason `"insufficient_vwap_depth"` including fill details (use Decimal comparison, not native JS division)
  - [x] 3.5 Compute best-level net edge (for comparison logging):
    ```typescript
    const bestLevelNetEdge = FinancialMath.calculateNetEdge(
      dislocation.grossEdge,
      dislocation.buyPrice,
      dislocation.sellPrice,
      buyFeeSchedule,
      sellFeeSchedule,
      gasEstimate,
      this.positionSizeUsd,
    );
    ```
  - [x] 3.6 Compute VWAP-based gross edge and net edge:
    ```typescript
    const vwapGrossEdge = vwapSellPrice.minus(vwapBuyPrice);
    const vwapNetEdge = FinancialMath.calculateNetEdge(
      vwapGrossEdge,
      vwapBuyPrice,
      vwapSellPrice,
      buyFeeSchedule,
      sellFeeSchedule,
      gasEstimate,
      this.positionSizeUsd,
    );
    ```
  - [x] 3.7 Replace the existing `netEdge` variable with `vwapNetEdge` for threshold comparison, `EnrichedOpportunity` population, and event emission
  - [x] 3.8 Log both edges for comparison:
    ```typescript
    this.logger.debug({
      message: `Edge comparison: ${pairEventDescription}`,
      data: {
        bestLevelNetEdge: bestLevelNetEdge.toString(),
        vwapNetEdge: vwapNetEdge.toString(),
        edgeDelta: bestLevelNetEdge.minus(vwapNetEdge).toString(),
      },
    });
    ```

- [x] **Task 4: Create `calculateVwapWithFillInfo()` helper** (AC: #2)
  - [x] 4.1 Add to `src/common/utils/financial-math.ts`, adjacent to `calculateVwapClosePrice()`:
    ```typescript
    export interface VwapFillResult {
      vwap: Decimal;
      filledQty: Decimal;
      totalQtyAvailable: Decimal;
    }
    export function calculateVwapWithFillInfo(
      orderBook: NormalizedOrderBook,
      closeSide: 'buy' | 'sell',
      positionSize: Decimal,
    ): VwapFillResult | null;
    ```
  - [x] 4.2 Logic is identical to `calculateVwapClosePrice()` but returns the struct with `filledQty` and `totalQtyAvailable` (sum of all level quantities on the relevant side)
  - [x] 4.3 Return `null` when `positionSize ≤ 0`, side is empty, or `filledQty = 0`
  - [x] 4.4 Refactor `calculateVwapClosePrice()` to delegate to `calculateVwapWithFillInfo()` — avoids duplicated book-walking logic:
    ```typescript
    export function calculateVwapClosePrice(...): Decimal | null {
      const result = calculateVwapWithFillInfo(orderBook, closeSide, positionSize);
      return result?.vwap ?? null;
    }
    ```
  - [x] 4.5 Update Task 3 to use `calculateVwapWithFillInfo()` instead of `calculateVwapClosePrice()` for the VWAP computation in edge calculator

- [x] **Task 5: Update types for VWAP edge data** (AC: #4)
  - [x] 5.1 Add to `EnrichedOpportunity` interface in `enriched-opportunity.type.ts`
  - [x] 5.2 Add to `FilteredDislocation` interface in `edge-calculation-result.type.ts`
  - [x] 5.3 Add to `LiquidityDepth` interface: `buyTotalDepth`, `sellTotalDepth`
  - [x] 5.4 Update `buildLiquidityDepth()` to populate the new depth fields
  - [x] 5.5 Update the `EnrichedOpportunity` construction in `processSingleDislocation()` to include all new fields
  - [x] 5.6 Update `OpportunityIdentifiedEvent` payload to include `bestLevelNetEdge`, `vwapBuyPrice`, `vwapSellPrice`, `buyFillRatio`, `sellFillRatio`
  - [x] 5.7 Update existing tests that construct `EnrichedOpportunity` or assert on its shape — add the new fields to test factories/assertions

- [x] **Task 6: Update `OpportunityFilteredEvent` emission for depth filtering** (AC: #2, #4)
  - [x] 6.1 Emit `OpportunityFilteredEvent` with `"insufficient_vwap_depth"` reason, matchId, for all depth filter paths
  - [x] 6.2 EventConsumerService handles new reason string — `reason` is free-form string

- [x] **Task 7: Write unit tests** (AC: #1, #2, #3, #4, #5)
  - [x] 7.1–7.15: All 18 ATDD edge-calculator tests activated and passing

- [x] **Task 8: Write unit tests for `calculateVwapWithFillInfo`** (AC: #2)
  - [x] 8.1–8.6: All 6 ATDD financial-math tests activated and passing

- [x] **Task 9: Update existing edge calculator tests** (AC: #1)
  - [x] 9.1 Updated `makeDislocation()` factory to auto-build consistent order books from buyPrice/sellPrice. Default quantity 10000 for sufficient fill ratio
  - [x] 9.2 Tests overriding `grossEdge` now use book-consistent prices (VWAP recomputes grossEdge)
  - [x] 9.3 Updated `liquidityDepth` assertions to match new default quantity (10000)
  - [x] 9.4 Event payload assertions updated in ATDD tests (skipped, activated in Task 7)
  - [x] 9.5 Updated settings count test in `settings.service.spec.ts` (72→73)

- [x] **Task 10: Event wiring verification** (AC: #4)
  - [x] 10.1 No new `@OnEvent` handlers added → no `expectEventHandled()` test needed
  - [x] 10.2 Verified `MatchAprUpdaterService.handleOpportunityFiltered` handles new reason — `reason` is free-form, `matchId` is populated

## Dev Notes

### Architecture Compliance

- **Module dependency rules:** EdgeCalculatorService already imports from `common/utils/financial-math.ts` — adding `calculateVwapWithFillInfo()` to the same file introduces no new imports
- **Error hierarchy:** No new errors thrown. Filtering uses existing event emission patterns. If VWAP computation throws unexpectedly, it's caught by the existing try/catch in `processDislocations()` (line 141-155)
- **Financial math:** VWAP prices are `Decimal` (returned by `calculateVwapClosePrice`). Gross edge recalculation uses `.minus()`. Net edge passes through `FinancialMath.calculateNetEdge()`. All `decimal.js` — no native JS operators
- **Hot path:** Edge calculation is in the detection → risk → execution hot path. VWAP adds a book walk per leg (~O(n) where n is price levels, typically <20) — negligible vs API latency

### Source Tree — Files to Modify

| File                                                                    | Change                                                                                                                                                                   |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/common/utils/financial-math.ts`                                    | Add `calculateVwapWithFillInfo()` + `VwapFillResult` interface                                                                                                           |
| `src/common/utils/financial-math.spec.ts`                               | Tests for `calculateVwapWithFillInfo()`                                                                                                                                  |
| `src/common/config/env.schema.ts`                                       | Add `DETECTION_MIN_FILL_RATIO`                                                                                                                                           |
| `src/common/config/config-defaults.ts`                                  | Add `detectionMinFillRatio` entry                                                                                                                                        |
| `src/common/config/settings-metadata.ts`                                | Add metadata under DetectionEdge group                                                                                                                                   |
| `src/common/config/effective-config.types.ts`                           | Add `detectionMinFillRatio` field                                                                                                                                        |
| `src/dashboard/dto/update-settings.dto.ts`                              | Add DTO field                                                                                                                                                            |
| `src/dashboard/settings.service.ts`                                     | Add to SERVICE_RELOAD_MAP + handler                                                                                                                                      |
| `src/dashboard/settings.service.spec.ts`                                | Update settings count (72→73)                                                                                                                                            |
| `src/persistence/repositories/engine-config.repository.ts`              | Add to resolve chain                                                                                                                                                     |
| `prisma/schema.prisma`                                                  | Add column to EngineConfig                                                                                                                                               |
| `src/modules/arbitrage-detection/types/enriched-opportunity.type.ts`    | Add `bestLevelNetEdge`, `vwapBuyPrice`, `vwapSellPrice`, `buyFillRatio`, `sellFillRatio` to EnrichedOpportunity; add `buyTotalDepth`, `sellTotalDepth` to LiquidityDepth |
| `src/modules/arbitrage-detection/types/edge-calculation-result.type.ts` | Add `bestLevelNetEdge?` to FilteredDislocation                                                                                                                           |
| `src/modules/arbitrage-detection/edge-calculator.service.ts`            | Core: VWAP edge calc in `processSingleDislocation()`, `reloadConfig()`, config field, startup validation, updated `buildLiquidityDepth()`                                |
| `src/modules/arbitrage-detection/edge-calculator.service.spec.ts`       | Updated and new test cases                                                                                                                                               |

### Source Tree — Files to Read (Reference Only)

| File                                                   | Why                                                                   |
| ------------------------------------------------------ | --------------------------------------------------------------------- |
| `src/common/events/detection.events.ts`                | `OpportunityFilteredEvent`, `OpportunityIdentifiedEvent` constructors |
| `src/common/events/event-catalog.ts`                   | Event name constants                                                  |
| `src/common/types/normalized-order-book.type.ts`       | `NormalizedOrderBook`, `PriceLevel` types                             |
| `src/modules/execution/execution.service.ts`           | Reference for `reloadConfig()` pattern (10-7-1)                       |
| `src/modules/arbitrage-detection/detection.service.ts` | How `RawDislocation` is built — `buyPrice`/`sellPrice` are best-level |

### Key Code Patterns to Follow

**Config getter pattern (edge-calculator.service.ts, line 107):**

```typescript
private get positionSizeUsd(): Decimal {
  return new FinancialDecimal(
    this.configService.get<number>('DETECTION_POSITION_SIZE_USD', 300),
  );
}
```

Follow same pattern for `detectionMinFillRatio` as a `Decimal` getter (unlike execution's `Number` — this is used in Decimal comparisons with filledQty).

**Startup validation pattern (edge-calculator.service.ts, line 47):**

```typescript
private validateConfig(envKey: string, defaultValue: number): void {
  const val = this.configService.get<number>(envKey, defaultValue);
  if (val < 0) {
    throw new SystemHealthError(
      `Config ${envKey} = ${val}: must not be negative`,
      ...
    );
  }
}
```

**Test factory pattern (edge-calculator.service.spec.ts):**
Tests use inline dislocation construction. When updating, ensure order books have multiple levels for VWAP tests. For backward-compatible tests (single level), VWAP = best level = identical results.

**Settings count test (settings.service.spec.ts):**
There's a test asserting total settings count. Increment by 1 for `detectionMinFillRatio`.

### Insertion Point in processSingleDislocation()

The VWAP computation should be inserted AFTER:

- Fee schedule retrieval (lines 169-174)
- Gas estimate computation (line 176)

And BEFORE:

- The current `FinancialMath.calculateNetEdge()` call (line 178)

The new flow is:

1. Get fee schedules + gas estimate (existing)
2. **NEW:** Compute target contract counts from `positionSizeUsd` / best-level prices
3. **NEW:** Compute VWAP prices via `calculateVwapWithFillInfo()` for both legs
4. **NEW:** Check fill ratios → filter if below `detectionMinFillRatio`
5. **NEW:** Compute best-level net edge (for comparison)
6. **MODIFIED:** Compute VWAP net edge (replaces current `netEdge` calculation)
7. Apply threshold filter (existing — now uses VWAP edge)
8. Capital efficiency gate (existing — now uses VWAP edge)
9. Build enriched opportunity (existing — extended with new fields)

### What NOT To Do

- Do NOT modify `RawDislocation` — keep `buyPrice`/`sellPrice` as best-level prices. VWAP is computed inside `processSingleDislocation()` only
- Do NOT modify `calculateVwapClosePrice()` — keep it unchanged. Create a new `calculateVwapWithFillInfo()` companion that returns fill info
- Do NOT pass best-level `grossEdge` to `calculateNetEdge()` when using VWAP prices — recompute as `vwapSellPrice - vwapBuyPrice`
- Do NOT use `Number()` for `detectionMinFillRatio` — use `Decimal` (it's compared against `Decimal` filledQty/targetContracts)
- Do NOT import from `modules/execution/` — use separate config for detection fill ratio
- Do NOT remove existing edge calculator tests — update them to work with VWAP (single-level books produce identical results)

### Previous Story Intelligence (10-7-1)

From 10-7-1 implementation:

- **Config pipeline pattern** is well-established: env.schema → config-defaults → settings-metadata → DTO → Prisma → effective-config → repository → settings.service reload map + handler. Follow exactly
- **Settings count test** needs incrementing (currently 72, updated from 71 in 10-7-1)
- **Event payload assertion** uses `expect.objectContaining({...})` — follow this for all new event assertions
- **Lad MCP code review** should be run after implementation with `paths` pointing to modified files
- **ATDD test approach** worked well — activate from skip if ATDD checklist is provided

### Testing Standards

- Co-located tests: `edge-calculator.service.spec.ts` (same directory)
- Framework: Vitest (NOT Jest) — use `vi.fn()`, `vi.spyOn()`, `describe`, `it`, `expect`
- Assertion depth: verify event payloads with `expect.objectContaining({...})` — bare `toHaveBeenCalled()` insufficient
- Financial math tests: use `toBeCloseTo()` or exact `Decimal` comparison for VWAP values
- Event wiring: no new `@OnEvent` handlers → no `expectEventHandled()` tests needed
- Paper/live boundary: detection module has no `isPaper` branching → no boundary tests needed

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 10-7-2] — Acceptance criteria
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-23-paper-profitability.md] — Root cause: +3.4% expected edge collapsed to -17.5% recalculated, -20.83% avg decay
- [Source: pm-arbitrage-engine/src/common/utils/financial-math.ts#calculateVwapClosePrice] — Existing VWAP utility (lines 231-256)
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.ts#processSingleDislocation] — Current edge calc (lines 164-283)
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/types/enriched-opportunity.type.ts] — EnrichedOpportunity, LiquidityDepth, FeeBreakdown
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/types/raw-dislocation.type.ts] — RawDislocation includes full order books
- [Source: CLAUDE.md#Architecture] — Module dependency rules, error handling, financial math
- [Source: CLAUDE.md#Testing] — Assertion depth, event wiring, co-located tests
- [Source: _bmad-output/implementation-artifacts/10-7-1-pre-trade-dual-leg-liquidity-gate.md] — Config pipeline pattern, event payload patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — no debugging issues encountered.

### Completion Notes List

- **Task 1:** Full config pipeline: env.schema → config-defaults → settings-metadata → DTO → Prisma migration → effective-config → repository → settings.service. Settings count 72→73.
- **Task 2:** `reloadConfig()` + startup validation (>0, ≤1.0) + `detectionMinFillRatio` field on EdgeCalculatorService.
- **Task 3:** Core VWAP implementation in `processSingleDislocation()`: zero-price guard → target contract conversion → `calculateVwapWithFillInfo()` for both legs → null/fill-ratio checks → bestLevelNetEdge + vwapNetEdge computation → threshold filtering → capital efficiency → enriched opportunity with all new fields → event emission with VWAP data.
- **Task 4:** `calculateVwapWithFillInfo()` returning `VwapFillResult { vwap, filledQty, totalQtyAvailable }`. Refactored `calculateVwapClosePrice()` to delegate. `totalQtyAvailable` sums all levels (not just filled).
- **Task 5:** `EnrichedOpportunity` + `FilteredDislocation` + `LiquidityDepth` type updates. `buildLiquidityDepth()` populates `buyTotalDepth`/`sellTotalDepth`.
- **Task 6:** `OpportunityFilteredEvent` emitted for all three depth filter paths (zero price, null VWAP, low fill ratio) with `insufficient_vwap_depth` reason and matchId.
- **Tasks 7-8:** All 24 ATDD tests activated (18 edge-calculator + 6 financial-math). Green.
- **Task 9:** Updated `makeDislocation()` factory to auto-build consistent order books from buyPrice/sellPrice (VWAP recomputes grossEdge). Default quantity 10000. Fixed all existing tests that independently overrode `grossEdge`.
- **Task 10:** No new `@OnEvent` handlers. `MatchAprUpdaterService` handles new reason string transparently.

### File List

**Modified:**
- `src/common/config/env.schema.ts` — Added `DETECTION_MIN_FILL_RATIO`
- `src/common/config/config-defaults.ts` — Added `detectionMinFillRatio` entry
- `src/common/config/settings-metadata.ts` — Added metadata (DetectionEdge group, count 72→73)
- `src/common/config/effective-config.types.ts` — Added `detectionMinFillRatio: string`
- `src/dashboard/dto/update-settings.dto.ts` — Added DTO field
- `src/dashboard/settings.service.ts` — Added to SERVICE_RELOAD_MAP + handler import + registration
- `src/dashboard/settings.service.spec.ts` — Updated settings count (72→73)
- `src/persistence/repositories/engine-config.repository.ts` — Added to resolve chain
- `prisma/schema.prisma` — Added `detectionMinFillRatio` column to EngineConfig
- `src/common/utils/financial-math.ts` — Added `calculateVwapWithFillInfo()` + `VwapFillResult`, refactored `calculateVwapClosePrice()` to delegate
- `src/common/utils/financial-math.spec.ts` — Activated 6 ATDD tests, real import
- `src/common/utils/index.ts` — Exported `calculateVwapWithFillInfo` + `VwapFillResult`
- `src/modules/arbitrage-detection/edge-calculator.service.ts` — Core VWAP implementation, `reloadConfig()`, startup validation, `buildLiquidityDepth()` update
- `src/modules/arbitrage-detection/edge-calculator.service.spec.ts` — Activated 18 ATDD tests, updated factories + existing tests for VWAP compatibility
- `src/modules/arbitrage-detection/types/enriched-opportunity.type.ts` — Added `bestLevelNetEdge`, `vwapBuyPrice`, `vwapSellPrice`, `buyFillRatio`, `sellFillRatio`, `buyTotalDepth`, `sellTotalDepth`
- `src/modules/arbitrage-detection/types/edge-calculation-result.type.ts` — Added `bestLevelNetEdge?` to FilteredDislocation

**Created:**
- `prisma/migrations/20260323192526_add_detection_min_fill_ratio/migration.sql`
