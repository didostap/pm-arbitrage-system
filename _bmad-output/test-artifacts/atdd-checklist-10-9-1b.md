---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-26'
workflowType: 'testarch-atdd'
inputDocuments:
  - '_bmad-output/implementation-artifacts/10-9-1b-depth-data-third-party-ingestion.md'
  - '_bmad/tea/testarch/knowledge/data-factories.md'
  - '_bmad/tea/testarch/knowledge/test-quality.md'
  - '_bmad/tea/testarch/knowledge/test-levels-framework.md'
  - '_bmad/tea/testarch/knowledge/test-priorities-matrix.md'
  - '_bmad/tea/testarch/knowledge/test-healing-patterns.md'
---

# ATDD Checklist - Epic 10-9, Story 10-9.1b: Depth Data & Third-Party Ingestion

**Date:** 2026-03-26
**Author:** Arbi
**Primary Test Level:** Unit + Integration (backend)

---

## Story Summary

The system ingests historical orderbook depth from PMXT Archive and supplementary OHLCV from OddsPipe, so that backtesting can model VWAP-based fill pricing and slippage.

**As an** operator
**I want** the system to ingest historical orderbook depth from PMXT Archive and supplementary OHLCV from OddsPipe
**So that** backtesting can model VWAP-based fill pricing and slippage

---

## Acceptance Criteria

1. PMXT Archive Parquet ingestion — download, parse, filter by target token IDs, sample per UTC hour, persist to `historical_depths`
2. OddsPipe OHLCV ingestion — resolve market IDs, fetch candlesticks, persist to `historical_prices` with source `ODDSPIPE`
3. Data normalization — all bid/ask prices to Decimal 0.00–1.00, sizes in USD, timestamps UTC, source provenance
4. Idempotent re-ingestion — unique constraints + `skipDuplicates: true`, DataCatalog checksum skip
5. Coverage gap & quality detection — depth gaps >2h, wide spreads >5%, empty/imbalanced books, OddsPipe price deviations
6. Freshness tracking — last available timestamp per contract per source, stale source flagging (>48h)
7. Observability — structured logs, `BacktestDataIngestedEvent` per source/contract, `BacktestDataQualityWarningEvent` for depth issues

---

## Failing Tests Created (RED Phase)

### PmxtArchiveService Tests (18 tests)

**File:** `src/modules/backtesting/ingestion/pmxt-archive.service.spec.ts` (NEW, ~280 lines)

- ↓ **Test:** [P1] should parse HTML directory listing for matching Parquet filenames within date range
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #1 — file discovery from PMXT Archive directory
- ↓ **Test:** [P1] should return empty array when no files match the date range
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #1 — edge case: no matching files
- ↓ **Test:** [P1] should upsert DataCatalog with PENDING -> PROCESSING -> COMPLETE status transitions
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #1 — DataCatalog lifecycle tracking
- ↓ **Test:** [P1] should compute SHA-256 checksum during download stream
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #1, #4 — incremental checksum for integrity
- ↓ **Test:** [P1] should skip download if DataCatalog row already COMPLETE with matching checksum
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #4 — idempotent download
- ↓ **Test:** [P1] should use 5-minute timeout for large file downloads
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #1 — 150-600MB file handling
- ↓ **Test:** [P1] should retry failed downloads with exponential backoff (3 attempts)
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #1 — transient error resilience
- ↓ **Test:** [P1] should throw SystemHealthError code 4208 after all retries exhausted
  - **Status:** RED — PmxtArchiveService class does not exist, error code 4208 not defined
  - **Verifies:** AC #1 — error handling
- ↓ **Test:** [P0] should filter rows by target token IDs from Set\<string\>
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #1 — CRITICAL: avoid ingesting millions of irrelevant records
- ↓ **Test:** [P0] should only process book_snapshot rows, skipping price_change
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #1 — Parquet row type filtering
- ↓ **Test:** [P0] should normalize bid/ask prices to Decimal in 0.00-1.00 range
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #3 — price normalization
- ↓ **Test:** [P0] should normalize sizes to Decimal in USD
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #3 — size normalization
- ↓ **Test:** [P1] should throw SystemHealthError code 4201 on Parquet parse failure
  - **Status:** RED — PmxtArchiveService class does not exist, error code 4201 not defined
  - **Verifies:** AC #1 — parse error handling
- ↓ **Test:** [P0] should sample first book_snapshot per UTC hour
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #1 — hourly sampling strategy
- ↓ **Test:** [P0] should batch persist via createMany({ skipDuplicates: true }), 500/batch
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #1, #4 — batch persistence + idempotency
- ↓ **Test:** [P0] should not create duplicates on re-ingestion (idempotency)
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #4 — re-ingestion safety
- ↓ **Test:** [P1] should update DataCatalog status on completion
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #1 — DataCatalog state management
- ↓ **Test:** [P1] should return IngestionMetadata with correct source and counts
  - **Status:** RED — PmxtArchiveService class does not exist
  - **Verifies:** AC #7 — metadata return contract

### OddsPipeService Tests (12 tests)

**File:** `src/modules/backtesting/ingestion/oddspipe.service.spec.ts` (NEW, ~220 lines)

- ↓ **Test:** [P1] should resolve OddsPipe market ID via title search from ContractMatch description
  - **Status:** RED — OddsPipeService class does not exist
  - **Verifies:** AC #2 — market ID resolution via `/v1/markets/search`
- ↓ **Test:** [P1] should cache market ID mapping in Map to avoid repeated lookups
  - **Status:** RED — OddsPipeService class does not exist
  - **Verifies:** AC #2 — caching strategy
- ↓ **Test:** [P1] should return null when no matching market found and log warning
  - **Status:** RED — OddsPipeService class does not exist
  - **Verifies:** AC #2 — graceful no-match handling
- ↓ **Test:** [P1] should clear market ID cache on service destroy (onModuleDestroy)
  - **Status:** RED — OddsPipeService class does not exist
  - **Verifies:** Collection cleanup requirement
- ↓ **Test:** [P0] should fetch OHLCV candlesticks and normalize to NormalizedPrice with Decimal
  - **Status:** RED — OddsPipeService class does not exist
  - **Verifies:** AC #2, #3 — OHLCV fetch + normalization
- ↓ **Test:** [P0] should persist prices with source ODDSPIPE, 500/batch, skipDuplicates
  - **Status:** RED — OddsPipeService class does not exist
  - **Verifies:** AC #2, #4 — persistence + idempotency
- ↓ **Test:** [P0] should not create duplicates on re-ingestion (idempotency)
  - **Status:** RED — OddsPipeService class does not exist
  - **Verifies:** AC #4 — re-ingestion safety
- ↓ **Test:** [P1] should enforce 857ms minimum interval between requests (70 req/min)
  - **Status:** RED — OddsPipeService class does not exist
  - **Verifies:** AC #2 — rate limiting (70% of 100 req/min)
- ↓ **Test:** [P1] should include X-API-Key header from ConfigService in all requests
  - **Status:** RED — OddsPipeService class does not exist
  - **Verifies:** AC #2 — authentication
- ↓ **Test:** [P1] should clamp date ranges exceeding 30 days to most recent 30 days
  - **Status:** RED — OddsPipeService class does not exist
  - **Verifies:** AC #2 — free tier history limit handling
- ↓ **Test:** [P1] should throw SystemHealthError code 4209 on OddsPipe API failure
  - **Status:** RED — OddsPipeService class does not exist, error code 4209 not defined
  - **Verifies:** AC #2 — error handling
- ↓ **Test:** [P1] should retry with exponential backoff (3 attempts) on transient errors
  - **Status:** RED — OddsPipeService class does not exist
  - **Verifies:** AC #2 — retry strategy

### DataQualityService Extension Tests (8 tests)

**File:** `src/modules/backtesting/ingestion/data-quality.service.spec.ts` (EXTENDED, +~120 lines)

- ↓ **Test:** [P1] should detect depth gaps >2 hours between PMXT snapshots
  - **Status:** RED — assessDepthQuality() method does not exist
  - **Verifies:** AC #5 — depth gap detection
- ↓ **Test:** [P1] should detect wide spreads (>5% bid-ask spread on 0-1 scale)
  - **Status:** RED — assessDepthQuality() method does not exist
  - **Verifies:** AC #5 — wide spread detection
- ↓ **Test:** [P1] should detect empty orderbooks (0 bid or 0 ask levels)
  - **Status:** RED — assessDepthQuality() method does not exist
  - **Verifies:** AC #5 — empty book detection
- ↓ **Test:** [P1] should detect imbalanced books (bid size <10% of ask size)
  - **Status:** RED — assessDepthQuality() method does not exist
  - **Verifies:** AC #5 — book imbalance detection
- ↓ **Test:** [P1] should return no flags for clean depth data
  - **Status:** RED — assessDepthQuality() method does not exist
  - **Verifies:** AC #5 — clean data baseline
- ↓ **Test:** [P1] should sort unsorted depth snapshots by timestamp before analysis
  - **Status:** RED — assessDepthQuality() method does not exist
  - **Verifies:** AC #5 — robustness
- ↓ **Test:** [P1] should return last available timestamp per contract per source
  - **Status:** RED — assessFreshness() method does not exist
  - **Verifies:** AC #6 — freshness tracking
- ↓ **Test:** [P1] should flag sources with data older than 48 hours as stale
  - **Status:** RED — assessFreshness() method does not exist
  - **Verifies:** AC #6 — stale source detection

### Orchestrator Extension Tests (8 tests)

**File:** `src/modules/backtesting/ingestion/ingestion-orchestrator.service.spec.ts` (EXTENDED, +~120 lines)

- ↓ **Test:** [P1] should call PmxtArchiveService.ingestDepth for Polymarket contracts
  - **Status:** RED — orchestrator does not inject PmxtArchiveService
  - **Verifies:** AC #1, #7 — new source wiring
- ↓ **Test:** [P1] should call OddsPipeService for Polymarket contracts only
  - **Status:** RED — orchestrator does not inject OddsPipeService
  - **Verifies:** AC #2, #7 — new source wiring
- ↓ **Test:** [P1] should emit BacktestDataIngestedEvent with source PMXT_ARCHIVE
  - **Status:** RED — orchestrator does not call PMXT source
  - **Verifies:** AC #7 — event emission
- ↓ **Test:** [P1] should emit BacktestDataIngestedEvent with source ODDSPIPE
  - **Status:** RED — orchestrator does not call OddsPipe source
  - **Verifies:** AC #7 — event emission
- ↓ **Test:** [P1] should skip OddsPipe ingestion when resolveMarketId returns null
  - **Status:** RED — orchestrator does not call OddsPipe source
  - **Verifies:** AC #2 — graceful skip
- ↓ **Test:** [P1] should run depth quality assessment for PMXT ingested data
  - **Status:** RED — orchestrator does not run depth quality assessment
  - **Verifies:** AC #5 — quality assessment wiring
- ↓ **Test:** [P1] should continue ingestion when PMXT source fails for a contract
  - **Status:** RED — orchestrator does not call PMXT source
  - **Verifies:** AC #7 — error resilience per source
- ↓ **Test:** [P1] should call assessFreshness at end of run and log summary
  - **Status:** RED — assessFreshness() does not exist
  - **Verifies:** AC #6 — freshness tracking wiring

### Error Code Tests (3 tests)

**File:** `src/common/errors/system-health-error.spec.ts` (EXTENDED, +~40 lines)

- ↓ **Test:** [P1] should define BACKTEST_PARQUET_PARSE_ERROR with code 4201
  - **Status:** RED — error code 4201 not defined in SYSTEM_HEALTH_ERROR_CODES
  - **Verifies:** AC #1 — PMXT Parquet parse error classification
- ↓ **Test:** [P1] should define BACKTEST_DEPTH_INGESTION_FAILURE with code 4208
  - **Status:** RED — error code 4208 not defined
  - **Verifies:** AC #1 — PMXT download failure error classification
- ↓ **Test:** [P1] should define BACKTEST_ODDSPIPE_API_ERROR with code 4209
  - **Status:** RED — error code 4209 not defined
  - **Verifies:** AC #2 — OddsPipe API error classification

### Type Tests (4 tests)

**File:** `src/modules/backtesting/types/normalized-historical.types.spec.ts` (NEW, ~90 lines)

- ↓ **Test:** [P1] should construct NormalizedHistoricalDepth with Decimal bids/asks arrays
  - **Status:** RED — NormalizedHistoricalDepth type does not exist
  - **Verifies:** AC #3 — depth type definition matching NormalizedOrderBook structure
- ↓ **Test:** [P1] should support null updateType for sources without update classification
  - **Status:** RED — NormalizedHistoricalDepth type does not exist
  - **Verifies:** AC #3 — updateType nullability
- ↓ **Test:** [P1] should include hasWideSpreads boolean field in DataQualityFlags
  - **Status:** RED — hasWideSpreads field not defined on DataQualityFlags
  - **Verifies:** AC #5 — depth quality flag extension
- ↓ **Test:** [P1] should be backward-compatible (depth fields optional)
  - **Status:** RED — DataQualityFlags extension does not exist
  - **Verifies:** AC #5 — backward compatibility

### Controller & Module Wiring Tests (4 tests)

**File:** `src/modules/backtesting/controllers/historical-data.controller.spec.ts` (EXTENDED, +~100 lines)

- ↓ **Test:** [P2] should include depth source coverage (PMXT_ARCHIVE, ODDSPIPE) in GET /coverage
  - **Status:** RED — controller does not query historicalDepth
  - **Verifies:** AC #6 — coverage endpoint extension
- ↓ **Test:** [P2] should include per-source freshness timestamps in GET /coverage/:contractId
  - **Status:** RED — controller does not return freshness data
  - **Verifies:** AC #6 — freshness endpoint
- ↓ **Test:** [P2] should handle empty depth data gracefully
  - **Status:** RED — controller does not query historicalDepth
  - **Verifies:** AC #6 — edge case
- ↓ **Test:** [P1] should resolve PmxtArchiveService and OddsPipeService from IngestionModule
  - **Status:** RED — providers not registered in ingestion.module.ts
  - **Verifies:** Module wiring — DI resolution

---

## Data Factories Created

### NormalizedHistoricalDepth Factory

**File:** `src/modules/backtesting/ingestion/data-quality.service.spec.ts` (inline)

**Exports:**
- `createNormalizedDepth(overrides?)` — Creates a depth record with Decimal bids/asks arrays

### PMXT Directory Listing Factory

**File:** `src/modules/backtesting/ingestion/pmxt-archive.service.spec.ts` (inline)

**Exports:**
- `createDirectoryListingHtml(filenames)` — Creates mock HTML directory listing for PMXT Archive
- `createExpectedDepth(overrides?)` — Creates expected depth record for assertions

### OddsPipe Response Factories

**File:** `src/modules/backtesting/ingestion/oddspipe.service.spec.ts` (inline)

**Exports:**
- `createMarketSearchResponse(markets)` — Creates mock OddsPipe market search response
- `createCandlestickResponse(candles)` — Creates mock OddsPipe candlestick response

---

## Mock Requirements

### PMXT Archive HTTP Mock

**Endpoint:** `GET https://archive.pmxt.dev/data/`

**Success Response:**
```html
<html><body><pre>
<a href="polymarket_orderbook_2025-06-01T00.parquet">polymarket_orderbook_2025-06-01T00.parquet</a>
<a href="polymarket_orderbook_2025-06-01T01.parquet">polymarket_orderbook_2025-06-01T01.parquet</a>
</pre></body></html>
```

### OddsPipe Market Search Mock

**Endpoint:** `GET https://oddspipe.com/v1/markets/search?q={title}`

**Success Response:**
```json
[
  { "id": 42, "title": "Will Bitcoin exceed $100k by December 2025?" }
]
```

### OddsPipe Candlestick Mock

**Endpoint:** `GET https://oddspipe.com/v1/markets/{id}/candlesticks?interval=1h`

**Success Response:**
```json
[
  { "timestamp": 1717200000, "open": 0.55, "high": 0.60, "low": 0.50, "close": 0.58, "volume": 15000 }
]
```

### hyparquet Parquet Mock

**Module:** `hyparquet` + `hyparquet-compressors` (ESM dynamic import)

**Mock pattern:** `vi.mock('hyparquet', ...)` with simulated `onChunk` callback returning filtered rows

**Notes:** All external APIs mocked via `vi.stubGlobal('fetch', mockFetch)`. Parquet library mocked via `vi.mock()`. No real HTTP calls or file I/O.

---

## Implementation Checklist

### Test: Error Codes (4201, 4208, 4209)

**File:** `src/common/errors/system-health-error.spec.ts`

**Tasks to make these tests pass:**

- [ ] Add `BACKTEST_PARQUET_PARSE_ERROR: 4201` to `SYSTEM_HEALTH_ERROR_CODES`
- [ ] Add `BACKTEST_DEPTH_INGESTION_FAILURE: 4208` to `SYSTEM_HEALTH_ERROR_CODES`
- [ ] Add `BACKTEST_ODDSPIPE_API_ERROR: 4209` to `SYSTEM_HEALTH_ERROR_CODES`
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/common/errors/system-health-error.spec.ts`
- [ ] 6 tests pass (green phase)

### Test: NormalizedHistoricalDepth Type & DataQualityFlags Extension

**File:** `src/modules/backtesting/types/normalized-historical.types.spec.ts`

**Tasks to make these tests pass:**

- [ ] Add `NormalizedHistoricalDepth` interface to `src/modules/backtesting/types/normalized-historical.types.ts`
- [ ] Extend `DataQualityFlags` in `src/common/types/historical-data.types.ts` with optional `hasWideSpreads?: boolean` and `spreadDetails?: Array<{timestamp: Date; spreadBps: number}>`
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/types/normalized-historical.types.spec.ts`
- [ ] 4 tests pass (green phase)

### Test: Prisma Schema — HistoricalDepth & DataCatalog

**Tasks (no dedicated test file — verified via service tests):**

- [ ] Add `HistoricalDepth` model to `prisma/schema.prisma` with unique constraint on `(platform, contractId, source, timestamp)`
- [ ] Add `DataCatalog` model with unique constraint on `(source, filePath)`
- [ ] Add `DataCatalogStatus` enum: `PENDING`, `PROCESSING`, `COMPLETE`, `FAILED`
- [ ] Run `pnpm prisma migrate dev --name add-historical-depth-data-catalog && pnpm prisma generate`
- [ ] Verify baseline tests still pass

### Test: PmxtArchiveService

**File:** `src/modules/backtesting/ingestion/pmxt-archive.service.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/modules/backtesting/ingestion/pmxt-archive.service.ts` (PrismaService, EventEmitter2 — 2 deps, leaf)
- [ ] Implement `discoverFiles(dateRange)`: HTTP GET to PMXT directory listing, parse HTML for matching Parquet filenames
- [ ] Implement `downloadAndCatalog(fileInfo)`: stream to disk, SHA-256 checksum, DataCatalog upsert, 5-min timeout, 3 retries
- [ ] Implement `parseParquetDepth(filePath, targetTokenIds)`: `hyparquet` dynamic import, `onChunk`, filter by token IDs and `book_snapshot` type, normalize to Decimal
- [ ] Implement `ingestDepth(contractId, dateRange)`: orchestrate discover → download → parse → sample (1 per UTC hour) → batch persist (500/batch, skipDuplicates)
- [ ] Add `pnpm add hyparquet hyparquet-compressors`
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/ingestion/pmxt-archive.service.spec.ts`
- [ ] 18 tests pass (green phase)

### Test: OddsPipeService

**File:** `src/modules/backtesting/ingestion/oddspipe.service.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/modules/backtesting/ingestion/oddspipe.service.ts` (PrismaService, ConfigService, EventEmitter2 — 3 deps, leaf)
- [ ] Implement `resolveMarketId(polymarketTokenId)`: look up contract title, search OddsPipe, cache in Map
- [ ] Implement `ingestPrices(oddsPipeMarketId, contractId, dateRange)`: fetch OHLCV, normalize, persist with source `ODDSPIPE`
- [ ] Implement rate limiting (857ms interval), auth (X-API-Key), 30-day clamping, retry with backoff
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/ingestion/oddspipe.service.spec.ts`
- [ ] 12 tests pass (green phase)

### Test: DataQualityService Extensions

**File:** `src/modules/backtesting/ingestion/data-quality.service.spec.ts`

**Tasks to make these tests pass:**

- [ ] Add `assessDepthQuality(depths)` method: detect gaps >2h, wide spreads >5%, empty books, imbalanced books
- [ ] Add `assessFreshness(contractId, sources)` method: query latest record per source, flag stale (>48h)
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/ingestion/data-quality.service.spec.ts`
- [ ] 23 tests pass (green phase — 15 existing + 8 new)

### Test: IngestionOrchestratorService Extensions

**File:** `src/modules/backtesting/ingestion/ingestion-orchestrator.service.spec.ts`

**Tasks to make these tests pass:**

- [ ] Add `PmxtArchiveService` and `OddsPipeService` to constructor (now 7 deps — facade, <=8 limit)
- [ ] In `runIngestion()`, after existing 4 source calls, add PMXT depth ingestion + OddsPipe OHLCV for Polymarket contracts
- [ ] In `runQualityAssessment()`, add depth quality assessment
- [ ] Add freshness assessment at end of run
- [ ] Emit events for new sources
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/ingestion/ingestion-orchestrator.service.spec.ts`
- [ ] 17 tests pass (green phase — 9 existing + 8 new)

### Test: Controller & Module Wiring

**File:** `src/modules/backtesting/controllers/historical-data.controller.spec.ts`

**Tasks to make these tests pass:**

- [ ] Extend `GET /api/backtesting/coverage` to include `historicalDepth` groupBy results
- [ ] Extend `GET /api/backtesting/coverage/:contractId` to include depth counts and freshness timestamps
- [ ] Add `PmxtArchiveService` and `OddsPipeService` to `ingestion.module.ts` providers
- [ ] Add env vars to `.env.example`: `ODDSPIPE_API_KEY`, `PMXT_ARCHIVE_BASE_URL`, `PMXT_ARCHIVE_LOCAL_DIR`
- [ ] Add `data/pmxt-archive/` to `.gitignore`
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/controllers/historical-data.controller.spec.ts`
- [ ] 10 tests pass (green phase — 6 existing + 4 new)

---

## Running Tests

```bash
# Run all failing tests for this story (all new should be skipped)
cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/ingestion/pmxt-archive.service.spec.ts src/modules/backtesting/ingestion/oddspipe.service.spec.ts src/modules/backtesting/types/normalized-historical.types.spec.ts src/common/errors/system-health-error.spec.ts src/modules/backtesting/ingestion/data-quality.service.spec.ts src/modules/backtesting/ingestion/ingestion-orchestrator.service.spec.ts src/modules/backtesting/controllers/historical-data.controller.spec.ts

# Run specific test file
cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/ingestion/pmxt-archive.service.spec.ts

# Run tests in watch mode
cd pm-arbitrage-engine && pnpm vitest src/modules/backtesting/

# Run tests with coverage
cd pm-arbitrage-engine && pnpm test:cov
```

---

## Red-Green-Refactor Workflow

### RED Phase (Complete)

**TEA Agent Responsibilities:**

- All 57 tests written and skipped (TDD red phase)
- Factory helpers created inline for test data
- Mock requirements documented (fetch, Prisma, hyparquet, ConfigService, EventEmitter2)
- Implementation checklist created per service
- No placeholder assertions (`expect(true).toBe(true)` removed)

**Verification:**

```
Test Files  4 passed | 3 skipped (7)
     Tests  33 passed | 57 skipped (90)
  Duration  793ms
```

All 57 new tests registered as skipped. 33 existing tests still passing. No failures, no errors.

---

### GREEN Phase (DEV Team - Next Steps)

**DEV Agent Responsibilities:**

1. **Pick one failing test group** from implementation checklist (start with error codes/types)
2. **Read the test** to understand expected behavior
3. **Implement minimal code** to make that specific test pass
4. **Remove `it.skip()`** → change to `it()`
5. **Run the test** to verify it passes (green)
6. **Check off the task** in implementation checklist
7. **Move to next test** and repeat

**Recommended implementation order:**
1. Prisma schema + migration (models needed by all services)
2. Error codes 4201, 4208, 4209 (shared infrastructure)
3. NormalizedHistoricalDepth type + DataQualityFlags extension
4. DataQualityService extensions (assessDepthQuality, assessFreshness)
5. PmxtArchiveService (download, parse, ingest)
6. OddsPipeService (resolve, fetch, persist)
7. IngestionOrchestratorService extensions
8. Controller extensions + module wiring + config

---

## Priority Coverage Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0       | 10    | Token ID filtering, normalization, batch persistence, idempotency, sampling |
| P1       | 44    | File discovery, download, error handling, rate limiting, caching, quality, freshness, orchestration, events, DI |
| P2       | 3     | Coverage endpoints, freshness endpoints |
| **Total** | **57** | |

## Acceptance Criteria Coverage

| AC | Description | Tests | Coverage |
|----|-------------|-------|----------|
| #1 | PMXT Archive Parquet ingestion | 18 | Full (discover, download, parse, filter, sample, persist, catalog, errors) |
| #2 | OddsPipe OHLCV ingestion | 12 | Full (resolve, fetch, normalize, persist, rate limit, auth, 30-day, errors) |
| #3 | Data normalization | 6 | Full (Decimal 0-1 prices, USD sizes, type construction, backward compat) |
| #4 | Idempotent re-ingestion | 4 | Full (skipDuplicates on depth/prices, checksum skip, re-ingestion test) |
| #5 | Coverage gap & quality detection | 8 | Full (depth gaps, wide spreads, empty books, imbalance, clean baseline, sort) |
| #6 | Freshness tracking | 5 | Full (per-source timestamps, stale flagging, coverage endpoints, edge case) |
| #7 | Observability | 6 | Full (PMXT event, OddsPipe event, quality assessment, resilience, freshness, metadata) |

---

## Knowledge Base References Applied

- **data-factories.md** — Factory patterns for NormalizedHistoricalDepth with Decimal overrides, PMXT directory listing HTML, OddsPipe API responses
- **test-quality.md** — Deterministic tests, explicit assertions, no placeholder assertions, parallel-safe
- **test-levels-framework.md** — Unit for pure logic (parsing, normalization), integration for service+DI tests
- **test-priorities-matrix.md** — P0 for data integrity/normalization/filtering, P1 for operational (errors, caching, rate limits), P2 for coverage endpoints
- **test-healing-patterns.md** — Mock patterns for fetch() via vi.stubGlobal, vi.mock() for ESM dynamic imports (hyparquet)

---

## Test Execution Evidence

### Initial Test Run (RED Phase Verification)

**Command:** `cd pm-arbitrage-engine && pnpm vitest run [7 spec files]`

**Results:**

```
Test Files  4 passed | 3 skipped (7)
     Tests  33 passed | 57 skipped (90)
  Duration  793ms
```

**Summary:**

- Total new tests: 57
- Passing: 0 new (expected — all skipped for TDD red phase)
- Failing: 0 (no errors)
- Skipped: 57 (TDD red phase)
- Existing tests: 33 still passing (no regressions)
- Status: RED phase verified

---

## Notes

- All tests use `it.skip()` (Vitest convention) for TDD red phase
- No E2E/browser tests — this is a pure backend story
- `vi.stubGlobal('fetch', mockFetch)` used for HTTP mocking (matches existing codebase pattern)
- `vi.mock('hyparquet', ...)` needed for ESM dynamic import mocking of Parquet library
- PMXT Parquet schema is undocumented — tests use known column assumptions from design doc section 1.4
- Paper/Live mode not applicable — historical data ingestion has no mode distinction
- Factory helpers are inline in spec files — consistent with 10-9-1a pattern
- OddsPipe market search returns integer IDs, not Polymarket token IDs — mapping handled by resolveMarketId()

---

**Generated by BMad TEA Agent** — 2026-03-26
