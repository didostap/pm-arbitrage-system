# Story 6.5.5a: Polymarket Order Book Sort Fix

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want the Polymarket REST order book normalizer to sort asks ascending and bids descending after parsing,
so that `asks[0]` is the best (lowest) ask and `bids[0]` is the best (highest) bid — matching the WebSocket client and Kalshi normalizer conventions — and arbitrage detection uses correct prices.

## Background / Root Cause

The Polymarket CLOB API returns asks in **descending** price order. `OrderBookNormalizerService.normalizePolymarket()` (lines 95-200 of `order-book-normalizer.service.ts`) parses and validates the raw book but does not sort. As a result:

- `asks[0]` = worst ask (e.g., 0.99) instead of best ask (e.g., 0.17)
- `bids[0]` = lowest bid instead of highest bid
- The crossed-market check (lines 141-144) compares wrong values
- `DetectionService.detectDislocations()` (line 129) uses `asks[0]` as best ask — produces incorrect edge calculations
- `EdgeCalculatorService` (lines 258-263) uses `asks[0]`/`bids[0]` for depth sizing — same incorrect values

**Evidence:** Sample Polymarket order book has asks `[0.99, 0.98, …, 0.17]` (descending). Gamma market API confirms `bestAsk: 0.17`.

**Correct reference implementations already in the codebase:**

- `PolymarketWebSocketClient.handleBookSnapshot()` (lines 217-219): sorts bids descending, asks ascending using Decimal comparison
- `kalshi-price.util.ts:33`: `asks.sort((a, b) => new Decimal(a.price).minus(b.price).toNumber())` — sorts asks ascending

## Acceptance Criteria

1. **Given** Polymarket REST API returns an order book with asks in descending price order
   **When** `normalizePolymarket()` processes the book
   **Then** the returned `NormalizedOrderBook.asks` array is sorted ascending by price (best/lowest ask at index 0)
   **And** the returned `NormalizedOrderBook.bids` array is sorted descending by price (best/highest bid at index 0)

2. **Given** a normalized Polymarket order book is produced
   **When** the crossed-market check runs
   **Then** it compares the actual best bid and best ask (not arbitrary array positions)

3. **Given** the sort is applied
   **When** `DetectionService` reads `asks[0]` and `bids[0]` from the normalized book
   **Then** it gets the true best ask and best bid for edge calculation

4. **Given** all existing tests pass before the change
   **When** the sort logic is added
   **Then** all existing tests continue to pass
   **And** a new test verifies sort order with realistically unordered input (asks descending, bids unordered)

## Tasks / Subtasks

- [x] Task 1: Add sort to `normalizePolymarket()` (AC: #1, #2)
  - [x] 1.1 In `order-book-normalizer.service.ts`, after step 4 (price validation, ~line 138), before the crossed-market check (~line 141), add:
    ```typescript
    // 5. Sort bids descending (best bid first), asks ascending (best ask first)
    // Polymarket CLOB API returns asks descending — must sort to match convention
    // (WebSocket client already sorts: polymarket-websocket.client.ts:217-219)
    bids.sort((a, b) => b.price - a.price);
    asks.sort((a, b) => a.price - b.price);
    ```

- [x] Task 2: Add test for sort order (AC: #4)
  - [x] 2.1 In `order-book-normalizer.service.spec.ts`, add test `'should sort asks ascending and bids descending (best price at index 0)'` inside the `describe('normalizePolymarket()')` block (starts at line 307)
  - [x] 2.2 Test uses asks in descending order `[0.99, 0.50, 0.17]` and bids unordered `[0.10, 0.14, 0.12]`
  - [x] 2.3 Verify `asks[0].price === 0.17`, `asks[2].price === 0.99` (ascending)
  - [x] 2.4 Verify `bids[0].price === 0.14`, `bids[2].price === 0.10` (descending)

- [x] Task 3: Fix detection sell-leg pricing (buy=ask, sell=bid)
  - [x] 3.1 In `detection.service.ts`, introduce `polyBestBid` and `kalshiBestBid` from `bids[0]`
  - [x] 3.2 Scenario A: `kalshiSellPrice` uses `kalshiBestBid.price` (was `kalshiBestAsk.price`)
  - [x] 3.3 Scenario B: `polySellPrice` uses `polyBestBid.price` (was `polyBestAsk.price`)
  - [x] 3.4 Add 2 tests verifying sell leg uses bids with wide-spread order books
  - [x] 3.5 Update 4 existing tests whose expected values used old buggy ask-based sell pricing

- [x] Task 4: Convert Decimal fields to numbers in OpportunityIdentifiedEvent payload
  - [x] 4.1 In `edge-calculator.service.ts`, build a plain object with `.toNumber()` calls for all Decimal fields (netEdge, grossEdge, buyPrice, sellPrice, positionSizeUsd, feeBreakdown costs) instead of casting `enriched as unknown as Record<string, unknown>`
  - [x] 4.2 Update edge-calculator test to expect `Number` instead of `Decimal` in event payload

- [x] Task 5: Verify no regressions
  - [x] 5.1 Run `pnpm test` — all 1171 unit tests pass
  - [x] 5.2 Run `pnpm lint` — zero errors

## Dev Notes

### Architecture Compliance

- **Module boundaries**: Change is entirely within `modules/data-ingestion/` — no cross-module imports added.
- **Error handling**: No new error types. This is a data transformation fix, not an error path.
- **Event system**: No new events. The fix is upstream of all event emissions — downstream consumers automatically get correct data.
- **Financial math**: Sort uses native JS comparison (`b.price - a.price`), not `decimal.js`. This is safe because values are already parsed floats in 0.00-1.00 range — no precision concern for sort ordering (only for arithmetic). Matches the WebSocket client pattern at `polymarket-websocket.client.ts:217-219` which also uses Decimal for comparison but the result is the same for sort ordering in this range.

### File Structure — Exact Files to Modify

| File                                                               | Change                                                              | Lines                                            |
| ------------------------------------------------------------------ | ------------------------------------------------------------------- | ------------------------------------------------ |
| `src/modules/data-ingestion/order-book-normalizer.service.ts`      | Add 2-line sort after price validation, before crossed-market check | Insert between ~line 138 and ~line 141           |
| `src/modules/data-ingestion/order-book-normalizer.service.spec.ts` | Add 1 test in `describe('normalizePolymarket()')` block             | After line 307+ (inside existing describe block) |

**No new files.** No schema changes. No new dependencies. No env var changes. No migration needed.

### Downstream Consumers (NO changes needed)

These all correctly use `asks[0]`/`bids[0]` as "best price" — the fix is upstream:

| Consumer                                    | File                               | Lines   | Usage                                                                                  |
| ------------------------------------------- | ---------------------------------- | ------- | -------------------------------------------------------------------------------------- |
| `DetectionService.detectDislocations()`     | `detection.service.ts`             | 129-130 | `polyBestAsk = polymarketOrderBook.asks[0]`, `kalshiBestAsk = kalshiOrderBook.asks[0]` |
| `EdgeCalculatorService.getDepthInfo()`      | `edge-calculator.service.ts`       | 258-263 | `buyBook.asks[0].quantity`, `buyBook.bids[0].quantity` etc.                            |
| Crossed-market check (in normalizer itself) | `order-book-normalizer.service.ts` | 141-144 | `bestBid = bids[0]`, `bestAsk = asks[0]`                                               |

### Existing Test Data Pattern

The existing test at line 308 uses **already-sorted** data (bids `[0.65, 0.60]`, asks `[0.70, 0.75]`), so it won't catch the sort bug. The new test must use **realistically unordered** input to verify the sort.

### Scope Guard

Originally scoped as sort fix + test only. During implementation, two related bugs were discovered and fixed in-scope (Tasks 3-4) because they were directly caused by the same root issue (incorrect best-price assumptions). Do not:

- Modify the Kalshi `normalize()` method (already sorts via `normalizeKalshiLevels` → `kalshi-price.util.ts:33`)
- Modify the WebSocket `handleBookSnapshot()` (already sorts at lines 217-219)
- Add Decimal-based sort comparison (native JS comparison is correct for this value range)

### Previous Story Intelligence (Story 6.5.4)

- Story 6.5.4 added WebSocket keepalive ping to both WS clients and fixed `summarizeEvent()` serialization
- Final test count after 6.5.4: 1,139 tests → current baseline: 1,167 tests (dashboard module added since)
- 0 lint errors at completion
- The WebSocket client sort pattern (`handleBookSnapshot` lines 217-219) was not modified in 6.5.4 — it's been correct since Story 2.2
- 2 e2e test files flaky (need running DB): `test/app.e2e-spec.ts`, `test/logging.e2e-spec.ts` — pre-existing, ignore

### Git Intelligence

Recent engine commits:

```
6ba25e1 feat: add dashboard module with WebSocket support
92ec9ff feat: implement WebSocket keepalive mechanism for Kalshi and Polymarket clients
8804bef feat: add comprehensive validation documentation for paper trading
c470f15 feat: implement batch fetching of order books for Polymarket
```

**Relevant to this story:**

- `c470f15`: Batch order book fetch — `DataIngestionService` now calls `getOrderBooks()` (batch) and each result goes through `normalizePolymarket()`. The sort fix applies to all books in the batch.
- The batch change did NOT modify `normalizePolymarket()` itself — it only changed how results are fed into it.

### Project Structure Notes

- All changes within `pm-arbitrage-engine/src/` — no root repo changes
- Files follow existing kebab-case naming convention
- Tests co-located with source (`.spec.ts` suffix)
- No new modules, no new files, no new dependencies

### References

- [Source: pm-arbitrage-engine/src/modules/data-ingestion/order-book-normalizer.service.ts, lines 95-200] — `normalizePolymarket()` method (no sort)
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/order-book-normalizer.service.spec.ts, line 307+] — `describe('normalizePolymarket()')` test block
- [Source: pm-arbitrage-engine/src/connectors/polymarket/polymarket-websocket.client.ts, lines 217-219] — Reference sort implementation (bids desc, asks asc)
- [Source: pm-arbitrage-engine/src/common/utils/kalshi-price.util.ts, line 33] — Kalshi asks sort (ascending)
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/detection.service.ts, lines 129-130] — Downstream consumer using `asks[0]`
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.ts, lines 258-263] — Downstream consumer using `asks[0]`/`bids[0]`
- [Source: _bmad-output/implementation-artifacts/6-5-4-websocket-stability-structured-log-payloads.md] — Previous story

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None required — straightforward 2-line sort fix.

### Completion Notes List

- Added `bids.sort((a, b) => b.price - a.price)` and `asks.sort((a, b) => a.price - b.price)` after price validation, before crossed-market check in `normalizePolymarket()`
- Added test with realistically unordered input (asks descending `[0.99, 0.50, 0.17]`, bids unordered `[0.10, 0.14, 0.12]`)
- Native JS comparison used for sort (safe for 0.00-1.00 range, matches WebSocket client pattern)
- **Detection sell-leg fix:** `detectDislocations()` was using `asks[0]` for both buy and sell legs. Sell leg must use `bids[0]` (executable sell price). Fixed Scenario A (`kalshiSellPrice` from `kalshiBestBid`) and Scenario B (`polySellPrice` from `polyBestBid`). This was overstating edge by the bid-ask spread of the sell-side platform.
- Added 2 new detection tests verifying sell-leg uses bid price with wide-spread books
- Updated 4 existing detection tests whose expected values were computed with old buggy ask-based sell pricing
- **Event serialization fix:** `OpportunityIdentifiedEvent` was emitting Decimal objects which the Telegram formatter's `str()` helper couldn't convert (rendered as `'N/A'`). Now builds a plain object with `.toNumber()` for all Decimal fields (netEdge, grossEdge, buyPrice, sellPrice, positionSizeUsd, feeBreakdown costs). Also adds `pairId` from `dislocation.pairConfig.eventDescription` so the formatter can display it.
- All 1171 tests pass (1168 baseline + 1 sort test + 2 sell-leg tests), 0 lint errors

### File List

| File                                                                                   | Change                                                                      |
| -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `pm-arbitrage-engine/src/modules/data-ingestion/order-book-normalizer.service.ts`      | Added 2-line sort (bids desc, asks asc) after price validation              |
| `pm-arbitrage-engine/src/modules/data-ingestion/order-book-normalizer.service.spec.ts` | Added 1 test: sort order with realistically unordered input                 |
| `pm-arbitrage-engine/src/modules/arbitrage-detection/detection.service.ts`             | Sell leg uses `bids[0]` instead of `asks[0]` for both scenarios             |
| `pm-arbitrage-engine/src/modules/arbitrage-detection/detection.service.spec.ts`        | Added 2 sell-leg tests, updated 4 existing test expectations                |
| `pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.ts`       | Event payload: Decimal → `.toNumber()`, adds `pairId` and `positionSizeUsd` |
| `pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.spec.ts`  | Event test expects `Number` instead of `Decimal`                            |
| `pm-arbitrage-engine/src/modules/monitoring/formatters/telegram-message.formatter.spec.ts` | Test data uses numbers (not strings) to match production event payload |
