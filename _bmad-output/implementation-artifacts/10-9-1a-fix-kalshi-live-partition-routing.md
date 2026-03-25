# Story 10-9.1a-fix: Kalshi Live Endpoint Dual-Partition Routing

Status: done

## Story

As an operator,
I want Kalshi price and trade ingestion to fetch data from BOTH the historical and live API partitions,
So that backtesting has complete Kalshi coverage across the full date range (not just pre-cutoff).

## Context

**Why this exists:** `KalshiHistoricalService` (Story 10-9-1a) only queries historical partition endpoints. Kalshi's live/historical data partition places a cutoff at ~2025-12-27 (`GET /historical/cutoff`). Data after this date is only available through live endpoints with different URL structures and (for candlesticks) different response field names. The service currently clamps `effectiveEnd` to the cutoff and returns 0 records for any post-cutoff range — making ~3 months of Kalshi price data invisible to backtesting.

**Scope:** Changes isolated to `KalshiHistoricalService` and its spec file. No module boundary changes, no new dependencies, no new Prisma models.

**Ref:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-28-kalshi-live-partition.md`

## Acceptance Criteria

1. **Given** a date range spanning the cutoff boundary **When** `ingestPrices()` runs **Then** data before cutoff is fetched from `GET /historical/markets/{ticker}/candlesticks` **And** data after cutoff is fetched from `GET /markets/candlesticks` (batch endpoint) **And** both datasets are normalized to the same `NormalizedPrice` schema and persisted.

2. **Given** the live candlestick endpoint returns `_dollars` suffix fields **When** the response is parsed **Then** `price.open_dollars`/`high_dollars`/`low_dollars`/`close_dollars` map to the same Decimal columns as historical `price.open`/`high`/`low`/`close` **And** `volume_fp` maps to `volume`, `open_interest_fp` to `openInterest`.

3. **Given** a date range entirely after the cutoff **When** `ingestPrices()` runs **Then** only the live endpoint is queried (no historical call) **And** records are persisted normally (not 0 records).

4. **Given** a date range entirely before the cutoff **When** `ingestPrices()` runs **Then** behavior is unchanged (historical endpoint only).

5. **Given** `ingestTrades()` has the same cutoff clamping **When** a date range spans the cutoff **Then** trades before cutoff use `GET /historical/trades` **And** trades after cutoff use `GET /markets/trades` (with `ticker` filter).

6. **Given** a date range entirely after the cutoff **When** `ingestTrades()` runs **Then** only the live trades endpoint is queried **And** records are persisted normally.

7. **Given** live and historical fetches share the same rate limit budget (14 req/s effective) **When** dual-partition routing issues requests to both endpoints **Then** all requests go through the existing `fetchWithRateLimit()` — no separate rate limiter.

8. **Given** the live batch candlestick endpoint caps at 10,000 candlesticks per request **When** fetching post-cutoff prices **Then** date ranges are chunked using 6-day windows (`LIVE_CHUNK_MS`) to stay safely under the 10K limit (6 days of 1-min candles = 8,640).

9. **Given** the `IngestionMetadata` return type is unchanged **When** dual-partition routing fetches from both endpoints **Then** `recordCount` reflects the total from both partitions combined.

## Tasks / Subtasks

- [x] **Task 1: Add live candlestick types and batch response parser** (AC: #2)
  - [x] 1.1 Define `KalshiLiveCandlestick` interface in the service (mirrors existing `KalshiCandlestick` but with `_dollars`/`_fp` field names)
  - [x] 1.2 Define `KalshiLiveCandlestickBatchResponse` type: `{ markets: Array<{ market_ticker: string; candlesticks: KalshiLiveCandlestick[] }> }`
  - [x] 1.3 Write `parseLiveCandlestick()` private method — maps `price.open_dollars` → Decimal, `volume_fp` → Decimal, etc. Returns inline Prisma `HistoricalPriceCreateManyInput` objects (matching existing `ingestPrices()` `.map()` pattern at lines 147-160, NOT `NormalizedPrice` type which is not used by this service). Keep `parseLiveCandlestick` as a standalone method (do NOT add an `isLive` flag to the existing inline mapper).
  - [x] 1.4 TDD: Red/green tests for parser — verify `open_dollars` maps to `open`, `volume_fp` to `volume`, `open_interest_fp` to `openInterest`, null/undefined `volume_fp`/`open_interest_fp` handling (map to `null` matching existing nullable pattern), string-to-Decimal conversion

- [x] **Task 2: Extract `fetchLiveCandlesticks()` private method** (AC: #3, #8)
  - [x] 2.1 Implement `fetchLiveCandlesticks(contractId, dateRange): Promise<Prisma.HistoricalPriceCreateManyInput[]>` using `GET /markets/candlesticks?market_tickers={contractId}&start_ts={unix_s}&end_ts={unix_s}&period_interval=1`
  - [x] 2.2 Apply `LIVE_CHUNK_MS` (6 days) chunking for live endpoint — 6 days of 1-min candles = 8,640, safely under the 10K candlestick limit
  - [x] 2.3 Parse response: extract `response.markets[0].candlesticks`, apply `parseLiveCandlestick()` to each
  - [x] 2.4 Route through existing `fetchWithRateLimit()` for rate limiting
  - [x] 2.5 TDD: Test chunking, rate limiting, empty response handling, market not found in response

- [x] **Task 3: Implement dual-partition routing in `ingestPrices()`** (AC: #1, #3, #4, #8, #9)
  - [x] 3.1 Replace the early-return-0 block (lines ~106-118) with partition routing logic. Also update the warning log (lines ~99-103) which currently says "data beyond cutoff not available" — replace with a **debug**-level log noting partition routing: `Routing prices: historical=${hasHistorical}, live=${hasLive}` (log only when spanning cutoff to avoid noise):
    - Range entirely pre-cutoff → historical only (existing path, unchanged)
    - Range entirely post-cutoff → `fetchLiveCandlesticks()` only
    - Range spans cutoff → fetch historical up to `cutoff.market_settled_ts`, fetch live from cutoff onward, merge arrays
  - [x] 3.2 Combined `recordCount` in `IngestionMetadata` = historical records + live records
  - [x] 3.3 Batch persist live records using existing `createMany({ skipDuplicates: true })` with `BATCH_SIZE` (500)
  - [x] 3.4 TDD: Three routing scenarios (pre-only, post-only, spanning), verify correct endpoints called, verify merged record count, verify persistence

- [x] **Task 4: Extract `fetchLiveTrades()` private method** (AC: #5, #6)
  - [x] 4.1 Implement `fetchLiveTrades(contractId, dateRange): Promise<Prisma.HistoricalTradeCreateManyInput[]>` using `GET /markets/trades?ticker={contractId}&min_ts={unix_s}&max_ts={unix_s}&limit=1000` with cursor pagination
  - [x] 4.2 Response format is IDENTICAL to historical trades — reuse existing `KalshiTrade` type and trade parsing logic (no new parser needed)
  - [x] 4.3 Route through existing `fetchWithRateLimit()`
  - [x] 4.4 TDD: Test pagination, rate limiting, empty response, identical normalization to historical path

- [x] **Task 5: Implement dual-partition routing in `ingestTrades()`** (AC: #5, #6, #7, #9)
  - [x] 5.1 Replace the early-return-0 block (lines 199-211) with partition routing logic (same pattern as prices)
  - [x] 5.2 Combined `recordCount` in `IngestionMetadata`
  - [x] 5.3 Batch persist live trade records
  - [x] 5.4 TDD: Three routing scenarios, verify correct endpoints called, verify merged record count

- [x] **Task 6: Update existing tests and edge cases** (AC: #4, #7)
  - [x] 6.1 Update test "returns 0 records when entirely beyond cutoff" — this test should now verify live endpoint is called instead of returning 0
  - [x] 6.2 Add edge case: cutoff timestamp exactly equals range start/end boundary
  - [x] 6.3 Add edge case: live endpoint returns empty array (no data for that market post-cutoff)
  - [x] 6.4 Add edge case: live endpoint 5xx triggers retry (same retry logic as historical)
  - [x] 6.5 Verify all pre-cutoff-only tests still pass unchanged
  - [x] 6.6 Add edge case: live batch endpoint returns `markets: []` (market not found) — verify empty array returned and warning logged
  - [x] 6.7 Verify Decimal precision maintained when parsing `_dollars` strings (same precision as historical)

## Dev Notes

### Target Files

| Action | File | Notes |
|--------|------|-------|
| MODIFY | `src/modules/backtesting/ingestion/kalshi-historical.service.ts` | Add live types, parsers, dual routing |
| MODIFY | `src/modules/backtesting/ingestion/kalshi-historical.service.spec.ts` | Update + new tests |
| NO CHANGE | All other files | No module boundary changes |

### Current Service Structure (356 lines)

```
Lines 20-46:   KalshiCandlestick, KalshiTrade, KalshiCutoff types
Lines 47-54:   Constants (CUTOFF_TTL_MS, BATCH_SIZE, EFFECTIVE_RATE, etc.)
Lines 56-65:   Constructor (ConfigService, PrismaService, Logger — 3 deps, well under leaf limit)
Lines 67-87:   fetchCutoff() — cached with 1hr TTL
Lines 89-181:  ingestPrices() — MODIFY (routing logic at 106-118)
Lines 183-276: ingestTrades() — MODIFY (routing logic at 199-211)
Lines 278-290: getSupportedSources() — DO NOT MODIFY
Lines 292-303: fetchWithRateLimit() — reuse for live calls
Lines 305-354: fetchWithRetry() + retry logic — reuse for live calls
```

**Line budget:** Service is 356 lines. Adding ~100-150 for live types + 2 fetch methods + 1 parser + routing changes → ~456-506 lines. Under the 600-line review trigger. Monitor during implementation.

### API Endpoint Details (verified via Kalshi docs 2026-03-28)

#### Live Candlesticks — `GET /markets/candlesticks` (batch, no `series_ticker` needed)

```
Query params:
  market_tickers: string (comma-separated, max 100) — use single contractId
  start_ts:       int64  (Unix seconds)
  end_ts:         int64  (Unix seconds)
  period_interval: int32 (1 = 1 min, 60 = 1 hour, 1440 = 1 day)

Response 200:
{
  "markets": [{
    "market_ticker": "TICKER",
    "candlesticks": [{
      "end_period_ts": 1234567890,          // Unix seconds
      "yes_bid":  { "open_dollars": "0.56", "high_dollars": "0.58", "low_dollars": "0.54", "close_dollars": "0.57" },
      "yes_ask":  { "open_dollars": "0.58", "high_dollars": "0.60", "low_dollars": "0.56", "close_dollars": "0.59" },
      "price":    { "open_dollars": "0.56", "high_dollars": "0.58", "low_dollars": "0.54", "close_dollars": "0.57",
                    "mean_dollars": "0.565", "previous_dollars": "0.55", "min_dollars": "0.54", "max_dollars": "0.58" },
      "volume_fp": "10.00",
      "open_interest_fp": "25.00"
    }]
  }]
}

Auth: NONE (public endpoint)
Rate limit: 20 req/s (Basic tier) — shared with historical calls
Max: 100 tickers, 10,000 candlesticks total per request
```

#### Live Trades — `GET /markets/trades`

```
Query params:
  ticker:  string (filter by market)
  min_ts:  int64  (Unix seconds, optional)
  max_ts:  int64  (Unix seconds, optional)
  limit:   int64  (1-1000, default 100)
  cursor:  string (pagination)

Response 200:
{
  "trades": [{
    "trade_id":          "uuid-string",
    "ticker":            "TICKER",
    "count_fp":          "10.00",        // same field name as historical
    "yes_price_dollars": "0.5600",       // same field name as historical
    "no_price_dollars":  "0.4400",       // same field name as historical
    "taker_side":        "yes",          // same field name as historical
    "created_time":      "2026-01-15T10:30:00Z"
  }],
  "cursor": "next-page-cursor"
}

Auth: NONE (public endpoint)
Rate limit: 20 req/s (Basic tier)
Pagination: cursor-based, empty cursor = done
```

### Field Mapping Reference

**Candlesticks — format DIFFERS between live and historical:**

| NormalizedPrice field | Historical field path | Live field path |
|-----------------------|----------------------|-----------------|
| `open` | `candlestick.price.open` | `candlestick.price.open_dollars` |
| `high` | `candlestick.price.high` | `candlestick.price.high_dollars` |
| `low` | `candlestick.price.low` | `candlestick.price.low_dollars` |
| `close` | `candlestick.price.close` | `candlestick.price.close_dollars` |
| `volume` | `candlestick.volume` | `candlestick.volume_fp` |
| `openInterest` | `candlestick.open_interest` | `candlestick.open_interest_fp` |
| `timestamp` | `candlestick.end_period_ts` | `candlestick.end_period_ts` |

All values are dollar-denomination strings (e.g., `"0.5600"`). Convert via `new Decimal(value)`. Do NOT divide by 100 — the existing historical parser already handles dollar strings correctly.

**Note:** Live response also contains `yes_bid` and `yes_ask` objects — intentionally ignored. Only `price` OHLC is needed for backtesting. `yes_bid`/`yes_ask` may be useful for spread analysis later (out of scope).

**Trades — format IDENTICAL between live and historical.** Reuse existing `KalshiTrade` type and parsing logic. Only the endpoint URL changes.

### Routing Logic Pseudocode

```typescript
// ingestPrices() — replace lines 106-118 routing logic
// NOTE: Historical candlestick fetching is currently INLINE in ingestPrices() (lines 120-171).
// There is NO existing fetchHistoricalCandlesticks() method. Keep the existing inline code for
// the historical path and add the live path alongside it.
const cutoff = await this.fetchCutoff();
const cutoffTs = cutoff.market_settled_ts;

let historicalCount = 0;
let liveCount = 0;

if (dateRange.start < cutoffTs) {
  // Historical partition — existing inline fetch logic (lines 120-171), clamp end to cutoff
  const effectiveEnd = new Date(Math.min(dateRange.end.getTime(), cutoffTs.getTime()));
  // ... existing chunked fetch + batch insert code, using effectiveEnd ...
  historicalCount = /* records from existing logic */;
}

if (dateRange.end > cutoffTs) {
  // Live partition — NEW fetchLiveCandlesticks() method
  const liveStart = new Date(Math.max(dateRange.start.getTime(), cutoffTs.getTime()));
  const liveRecords = await this.fetchLiveCandlesticks(contractId, { start: liveStart, end: dateRange.end });
  // Batch persist liveRecords using same createMany({ skipDuplicates: true }) pattern
  liveCount = liveRecords.length;
}

// Return IngestionMetadata with recordCount = historicalCount + liveCount
```

Same pattern for `ingestTrades()` using `cutoff.trades_created_ts`:

```typescript
// ingestTrades() — replace lines 199-211 routing logic
// NOTE: Historical trade fetching is currently INLINE (lines ~213-270).
const cutoff = await this.fetchCutoff();
const cutoffTs = cutoff.trades_created_ts; // NOT market_settled_ts — trades have their own cutoff

let historicalCount = 0;
let liveCount = 0;

if (dateRange.start < cutoffTs) {
  const effectiveEnd = new Date(Math.min(dateRange.end.getTime(), cutoffTs.getTime()));
  // ... existing cursor-paginated fetch + batch insert, using effectiveEnd ...
  historicalCount = /* records from existing logic */;
}

if (dateRange.end > cutoffTs) {
  const liveStart = new Date(Math.max(dateRange.start.getTime(), cutoffTs.getTime()));
  const liveRecords = await this.fetchLiveTrades(contractId, { start: liveStart, end: dateRange.end });
  // Batch persist liveRecords
  liveCount = liveRecords.length;
}
```

### Cutoff Boundary Convention

Records at exactly `cutoffTs` belong to the **live** partition:
- Historical partition fetches `[dateRange.start, cutoffTs)` — exclusive of cutoff
- Live partition fetches `[cutoffTs, dateRange.end]` — inclusive of cutoff
- This matches the current code's `effectiveEnd = min(end, cutoff)` which excludes the cutoff from historical
- When `dateRange.start === cutoffTs`: only live executes (historical condition `start < cutoffTs` is false)
- When `dateRange.end === cutoffTs`: only historical executes (live condition `end > cutoffTs` is false) — cutoff candle itself comes from historical in this edge case, which is acceptable

### Critical Implementation Notes

**Line ranges are approximate** — verify against actual source during implementation. They reflect the file at story creation time and may shift by a few lines after formatting or prior edits.

1. **Timestamps are Unix SECONDS** for live endpoints (not milliseconds). The existing historical endpoint also uses seconds. Verify consistency.

2. **Batch endpoint response is wrapped in `markets` array.** Extract `response.markets[0]?.candlesticks ?? []`. Handle case where market ticker isn't found in response (return empty array, log warning).

3. **`end_period_ts` in live response is a number (Unix seconds)**, same as historical. Convert with `new Date(end_period_ts * 1000)`.

4. **Live trades `min_ts`/`max_ts` are Unix seconds.** Historical trades use `min_ts`/`max_ts` too. Both are cursor-paginated.

5. **Idempotency preserved** — both live and historical records go through `createMany({ skipDuplicates: true })` with the same unique constraint: `[platform, contractId, source, intervalMinutes, timestamp]` for prices, `[platform, contractId, source, externalTradeId]` for trades.

6. **`HistoricalDataSource` enum** — live records should still use `KALSHI_API` as the source (same data source, different endpoint). This preserves the unique constraint semantics.

7. **Do NOT change the `IHistoricalDataProvider` interface or `IngestionMetadata` return type.** The orchestrator and all downstream consumers must continue to work unchanged.

8. **Retry logic applies to live calls too.** Route live fetches through the same `fetchWithRateLimit()` and retry wrapper.

9. **Chunking for live candlesticks:** The live batch endpoint explicitly documents a 10K candlestick cap. For 1-min intervals: 7 days = 10,080 (over). **Use 6-day chunks for live** (`LIVE_CHUNK_MS = 6 * 24 * 60 * 60 * 1000` = 8,640 candles, safe margin). Historical keeps `SEVEN_DAYS_MS` — its 10K limit is undocumented but 7-day chunks have worked empirically.

10. **Live trades `trade_id` field** — use this as `externalTradeId` (unlike historical where it may be missing and requires synthetic ID generation). Check if the field is always present.

### Previous Story Intelligence

**From 10-9-1a (original implementation):**
- Dollar string normalization pattern: `new Decimal(candlestick.price.open)` — no division
- Rate limiting: 70% of Kalshi limit (14 req/s effective)
- Chunking: 7-day windows due to Kalshi server-side 10K candle limit
- Idempotency via `skipDuplicates: true` on batch inserts
- Synthetic trade IDs: `kalshi-${contractId}-${t.created_time}-${t.yes_price_dollars}` when `trade_id` missing
- Error codes: `4206` for Kalshi API failures (`SystemHealthError`)

**From 10-9-0 design doc gotchas:**
- **K1 (Field naming divergence):** Historical uses `open`/`volume`, live uses `open_dollars`/`volume_fp`. Mitigation: separate parsers per endpoint with normalization layer mapping both to common schema. **This is exactly what this story implements.**
- **K3 (Data removed from live endpoints):** Since March 6, 2026, historical data is only in `/historical/*`. Always route via cutoff. **The cutoff routing in the original story is correct; this story extends it to also fetch from live when data is post-cutoff.**

### Git Intelligence

Recent commits show Epic 10.9 implementation pattern:
- Services implement `IHistoricalDataProvider` interface
- Tests use Vitest with `vi.fn()` mocks for HTTP calls
- Prisma operations mocked via `mockPrismaService`
- Rate limiting tested with real timers in dedicated describe block

### Testing Standards

- **Co-located:** spec file in same directory as service
- **TDD cycle:** Red → Green → Refactor per unit of behavior
- **Assertion depth:** Verify payloads with `expect.objectContaining({})`, not just `toHaveBeenCalled()`
- **Event wiring:** Not applicable (no new events in this story)
- **Paper/live mode:** Not applicable (backtesting module is offline-only)
- **Collection cleanup:** Not applicable (no new Maps/Sets expected)

### Project Structure Notes

- All changes in `pm-arbitrage-engine/src/modules/backtesting/ingestion/`
- No new files — modifying existing service and spec only
- No module boundary violations — `KalshiHistoricalService` stays in `ingestion/` submodule
- No new dependencies — uses existing `ConfigService`, `PrismaService`, `Logger`

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-28-kalshi-live-partition.md] — Full change proposal with impact analysis
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md#1.1] — Kalshi API endpoints, gotchas K1/K3
- [Source: _bmad-output/implementation-artifacts/10-9-1a-platform-api-price-trade-ingestion.md] — Original implementation story
- [Source: pm-arbitrage-engine/src/modules/backtesting/ingestion/kalshi-historical.service.ts] — Current implementation (356 lines)
- [Source: pm-arbitrage-engine/prisma/schema.prisma] — HistoricalPrice, HistoricalTrade models

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
None — clean implementation, no debugging needed.

### Completion Notes List
- **Task 1:** Added `KalshiLiveCandlestick`, `KalshiLiveCandlestickBatchResponse` types and `parseLiveCandlestick()` method. 3 tests: field mapping, null handling, precision.
- **Task 2:** Added `fetchLiveCandlesticks()` with 6-day chunking (`LIVE_CHUNK_MS`), `chunkDateRange()` updated to accept configurable chunk size. 4 tests: URL params, chunking, empty markets, market not found.
- **Task 3:** Replaced `ingestPrices()` early-return-0 block with dual-partition routing (historical < cutoff, live > cutoff). Debug log on span. 3 tests: post-only, spanning, combined count.
- **Task 4:** Added `fetchLiveTrades()` with cursor pagination, reusing `KalshiTrade` type. 3 tests: pagination, empty response, parsing.
- **Task 5:** Replaced `ingestTrades()` early-return-0 block with dual-partition routing using `trades_created_ts`. 3 tests: post-only, spanning, trades_created_ts vs market_settled_ts.
- **Task 6:** Replaced old "returns 0" test, added 7 edge case tests: pre-only behavior, cutoff=start, cutoff=end, empty live, 5xx retry on live, Decimal precision, empty live trades.
- **Total:** 22 new tests (37 total in spec file, up from 15). Full suite: 3448 pass (+22 from baseline 3426). No regressions.
- **Line count:** Service went from 356 → 464 lines (+108). Under 600-line review trigger.

### Change Log
- 2026-03-28: Implemented dual-partition routing for Kalshi historical/live API endpoints (prices + trades). 22 new tests.

### File List
- `pm-arbitrage-engine/src/modules/backtesting/ingestion/kalshi-historical.service.ts` — MODIFIED (added live types, parsers, fetchLiveCandlesticks, fetchLiveTrades, dual-partition routing in ingestPrices/ingestTrades)
- `pm-arbitrage-engine/src/modules/backtesting/ingestion/kalshi-historical.service.spec.ts` — MODIFIED (22 new tests for live endpoint parsing, fetching, routing, edge cases)
