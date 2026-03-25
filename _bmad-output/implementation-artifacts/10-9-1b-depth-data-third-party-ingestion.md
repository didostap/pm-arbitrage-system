# Story 10-9.1b: Depth Data & Third-Party Ingestion

Status: done

## Story

As an operator,
I want the system to ingest historical orderbook depth from PMXT Archive and supplementary OHLCV from OddsPipe,
So that backtesting can model VWAP-based fill pricing and slippage.

## Acceptance Criteria

1. **Given** PMXT Archive provides hourly Polymarket L2 orderbook snapshots in Parquet format
   **When** a depth data ingestion job is triggered
   **Then** PMXT Archive Parquet files are downloaded and parsed into `HistoricalDepth` records (bids/asks as JSON arrays of `{price, size}` objects — same structure as `NormalizedOrderBook` from `normalized-order-book.type.ts`, enabling direct use with `calculateVwapWithFillInfo()`)
   **And** raw Parquet files are stored in `data/pmxt-archive/` directory, indexed by a `DataCatalog` table
   **And** sampled depth snapshots are persisted to `historical_depths` table

2. **Given** OddsPipe provides OHLCV candlesticks at 1m/5m/1h/1d intervals
   **When** a data ingestion job is triggered
   **Then** OddsPipe OHLCV data is fetched for matched pairs as supplementary price data
   **And** data is persisted to `historical_prices` with source `ODDSPIPE`
   **And** OddsPipe market ID mapping is resolved via `/v1/markets/search`

3. **Given** data arrives from heterogeneous sources (PMXT Parquet columns, OddsPipe OHLCV JSON)
   **When** data is persisted
   **Then** all bid/ask prices are normalized to `Decimal` in 0.00-1.00 probability range
   **And** all sizes are normalized to `Decimal` in USD
   **And** all timestamps are UTC `Date`
   **And** source provenance is recorded via `HistoricalDataSource` enum

4. **Given** ingestion targets a date range
   **When** records already exist for that range
   **Then** re-ingestion does not create duplicates (unique constraints + `skipDuplicates: true`)

5. **Given** PMXT Archive has intermittent availability and irregular `book_snapshot` periodicity
   **When** coverage gap detection runs
   **Then** time ranges with missing depth data (gaps >2 hours between PMXT snapshots) are flagged
   **And** OddsPipe price deviations >10% from our Polymarket CLOB price data (same contract, same timestamp window) are flagged as quality warnings

6. **Given** multiple depth/price sources exist
   **When** freshness tracking runs
   **Then** last available snapshot timestamp per contract per source is recorded
   **And** freshness data is queryable via coverage endpoints

7. **Given** ingestion is running
   **When** progress changes
   **Then** structured logs report per-contract/per-source progress
   **And** `BacktestDataIngestedEvent` is emitted on completion per source/contract
   **And** `BacktestDataQualityWarningEvent` is emitted when quality issues are detected

## Tasks / Subtasks

- [x] Task 1: Prisma Schema -- HistoricalDepth & DataCatalog Models + Migration (AC: #1, #3, #4)
  - [x] 1.1 Add `HistoricalDepth` model with fields: `platform`, `contractId`, `source`, `bids` (Json), `asks` (Json), `timestamp`, `updateType`, `ingestionTs`, `qualityFlags`, `createdAt`. Unique constraint on `(platform, contractId, source, timestamp)`. Indexes on `(platform, contractId, timestamp)`, `(source, timestamp)`, `(timestamp)`
  - [x] 1.2 Add `DataCatalog` model with fields: `id` (autoincrement), `source` (HistoricalDataSource), `filePath`, `fileSize` (BigInt), `timeRangeStart`, `timeRangeEnd`, `recordCount`, `status` (enum: PENDING, PROCESSING, COMPLETE, FAILED), `checksum` (String?), `metadata` (Json?), `createdAt`, `updatedAt`. Unique constraint on `(source, filePath)`
  - [x] 1.3 Add `DataCatalogStatus` enum: `PENDING`, `PROCESSING`, `COMPLETE`, `FAILED`
  - [x] 1.4 Run migration and generate
  - [x] 1.5 Tests: migration verified, baseline tests pass

- [x] Task 2: NormalizedHistoricalDepth Type & Depth Quality Flags (AC: #3, #5)
  - [x] 2.1 Add `NormalizedHistoricalDepth` interface to `src/modules/backtesting/types/normalized-historical.types.ts`: `platform`, `contractId`, `source`, `bids: Array<{ price: Decimal; size: Decimal }>`, `asks: Array<{ price: Decimal; size: Decimal }>`, `timestamp`, `updateType: 'snapshot' | 'price_change' | null`, `qualityFlags`
  - [x] 2.2 Extend `DataQualityFlags` in `src/common/types/historical-data.types.ts` with `hasWideSpreads?: boolean` and `spreadDetails?: Array<{ timestamp: Date; spreadBps: number }>` (optional fields, backward-compatible)
  - [x] 2.3 Tests: type tests verifying depth-specific quality flag construction

- [x] Task 3: Error Codes for Depth/Third-Party Sources (AC: #1, #2)
  - [x] 3.1 Add error codes to `system-health-error.ts` (after existing 4200/4206/4207): `4201` (`BACKTEST_PARQUET_PARSE_ERROR`), `4208` (`BACKTEST_DEPTH_INGESTION_FAILURE`), `4209` (`BACKTEST_ODDSPIPE_API_ERROR`). Codes 4202-4205 are reserved for later stories per design doc section 8.5
  - [x] 3.2 Tests: error construction specs

- [x] Task 4: PmxtArchiveService -- Download, Parse, Persist Depth (AC: #1, #3, #4, #7)
  - [x] 4.1 Create `pmxt-archive.service.ts` (PrismaService, EventEmitter2 -- 2 deps, leaf)
  - [x] 4.2 Implement `discoverFiles(dateRange)`: HTTP GET to `https://archive.pmxt.dev/data/` directory listing, parse HTML for matching Parquet filenames within date range, return list of `{ url, filename, hourTimestamp }`
  - [x] 4.3 Implement `downloadAndCatalog(fileInfo)`: download Parquet file to `data/pmxt-archive/` (stream to disk, do NOT buffer in memory for 150-600MB files). Compute SHA-256 checksum via `crypto.createHash('sha256')` during stream. Upsert `DataCatalog` row (status PENDING -> PROCESSING -> COMPLETE/FAILED). Skip download if DataCatalog row already COMPLETE with matching checksum. Use 5-minute timeout for large file downloads (not the standard 30s)
  - [x] 4.4 Implement `parseParquetDepth(filePath, targetTokenIds: Set<string>)`: use `hyparquet` + `hyparquet-compressors` (dynamic import for ESM). Stream via `onChunk` callback. Filter rows where asset ID matches target contract token IDs (the Set comes from orchestrator's `buildTargetList()` → `target.polymarketTokenId` values). Only process `book_snapshot` rows (skip `price_change`). Extract bids/asks arrays, normalize prices to Decimal 0-1, sizes to Decimal USD. Return `NormalizedHistoricalDepth[]`
  - [x] 4.5 Implement `ingestDepth(contractId, dateRange)`: orchestrate discover -> download -> parse -> persist flow. Sample: select the first `book_snapshot` per UTC hour (floor timestamp to hour, take earliest snapshot within that hour). Persist sampled snapshots to `historical_depths` via `createMany({ skipDuplicates: true })`, 500/batch. Update `DataCatalog` status. Return `IngestionMetadata`
  - [x] 4.6 Error handling: `SystemHealthError` code 4201 for Parquet parse failures, 4208 for download failures. 3 retries with exponential backoff for downloads. 30s HTTP timeout via `fetchWithTimeout` pattern
  - [x] 4.7 Tests: 10+ tests -- file discovery, download+catalog, Parquet parsing with mock data, depth normalization, batch persistence, idempotency, error handling, timeout

- [x] Task 5: OddsPipeService -- Fetch OHLCV Candlesticks (AC: #2, #3, #4, #7)
  - [x] 5.1 Create `oddspipe.service.ts` (PrismaService, ConfigService, EventEmitter2 -- 3 deps, leaf)
  - [x] 5.2 Implement `resolveMarketId(polymarketTokenId)`: look up `ContractMatch.polymarketDescription` for the contract title, then call `GET /v1/markets/search?q={encodeURIComponent(title)}` to find the OddsPipe market ID. Select the first result whose title contains key words from the description. Cache mapping in `Map<polymarketClobTokenId, oddsPipeMarketId>` /\*_ Cleanup: .clear() on service destroy, entries invalidated on re-ingestion _/. Return `oddsPipeMarketId | null` (null if no match found — skip silently with log warning)
  - [x] 5.3 Implement `ingestPrices(oddsPipeMarketId, contractId, dateRange)`: fetch `GET /v1/markets/{id}/candlesticks?interval=1h`. Normalize OHLCV to `NormalizedPrice`. Persist to `historical_prices` with source `ODDSPIPE`. 500/batch, `skipDuplicates`
  - [x] 5.4 Rate limiting: 100 req/min free tier -> effective 70 req/min (70% safety). `minIntervalMs = 857` (1000 \* 60 / 70). Simple lastRequestTs pattern
  - [x] 5.5 Auth: `X-API-Key` header from `ConfigService` (`ODDSPIPE_API_KEY` env var)
  - [x] 5.6 Handle 30-day history limit: if requested range exceeds 30 days, clamp to last 30 days, log warning
  - [x] 5.7 Error handling: `SystemHealthError` code 4209. Retry with backoff (3 attempts). 30s timeout
  - [x] 5.8 Tests: 9+ tests -- market ID resolution, OHLCV fetch+normalize, rate limiting, 30-day clamping, auth header, persistence, idempotency, error handling

- [x] Task 6: Extend DataQualityService for Depth Assessment (AC: #5, #6)
  - [x] 6.1 Add `assessDepthQuality(depths: NormalizedHistoricalDepth[])`: detect gaps >2 hours between snapshots, wide spreads (>5% bid-ask spread), empty orderbooks (0 levels), imbalanced books. Sort by timestamp before analysis. Return `DataQualityFlags`
  - [x] 6.2 Add `assessFreshness(contractId, sources)`: query latest record per source for a contract, return map of `{ source -> lastTimestamp }`. Flag sources with data older than 48 hours as stale
  - [x] 6.3 Tests: 6+ tests -- gap detection, spread detection, empty books, imbalance, freshness stale/fresh, mixed sources

- [x] Task 7: Extend IngestionOrchestratorService for New Sources (AC: #1, #2, #5, #6, #7)
  - [x] 7.1 Add `PmxtArchiveService` and `OddsPipeService` to constructor (now 7 deps -- facade, within <=8 limit)
  - [x] 7.2 In `runIngestion()` loop (after line ~216 in `ingestion-orchestrator.service.ts`), after existing 4 source calls, add: PMXT depth ingestion for `target.polymarketTokenId` (Polymarket only — PMXT has no Kalshi data), OddsPipe OHLCV for Polymarket contracts only (OddsPipe uses its own market IDs, Kalshi mapping unavailable). Emit `BacktestDataIngestedEvent` per source with correct `source` enum value
  - [x] 7.3 In `runQualityAssessment()`, add depth quality assessment: query `historical_depths`, run `assessDepthQuality()`, persist flags, emit warnings
  - [x] 7.4 Add freshness assessment at end of run: call `assessFreshness()` per contract, log freshness summary
  - [x] 7.5 Tests: 5+ tests -- new source calls wired, depth quality assessed, freshness tracked, event emission, error resilience per source

- [x] Task 8: Controller Updates & Coverage Freshness Endpoints (AC: #6, #7)
  - [x] 8.1 Extend `GET /api/backtesting/coverage` response to include depth source coverage (PMXT, OddsPipe) alongside existing price/trade coverage
  - [x] 8.2 Extend `GET /api/backtesting/coverage/:contractId` to include per-source freshness timestamps
  - [x] 8.3 Tests: 3+ tests -- coverage includes depth sources, freshness data returned, empty data handled

- [x] Task 9: Module Wiring & Configuration (AC: all)
  - [x] 9.1 Add `PmxtArchiveService` and `OddsPipeService` to `ingestion.module.ts` providers (now 6 providers -- within limit)
  - [x] 9.2 Add env vars to `.env.example` and config: `ODDSPIPE_API_KEY`, `PMXT_ARCHIVE_BASE_URL` (default `https://archive.pmxt.dev/data/`), `PMXT_ARCHIVE_LOCAL_DIR` (default `data/pmxt-archive`)
  - [x] 9.3 Add `data/pmxt-archive/` to `.gitignore`
  - [x] 9.4 Add `hyparquet` and `hyparquet-compressors` as dependencies: `pnpm add hyparquet hyparquet-compressors`
  - [x] 9.5 Tests: module compilation, provider injection verified

## Dev Notes

### Design Document Reference

**Authoritative source:** `_bmad-output/implementation-artifacts/10-9-0-design-doc.md` -- ALL technical decisions for this story are defined there. When in doubt, the design doc overrides this story file.

Key sections:

- Section 1.4 (PMXT Archive): file naming, sizes, gotchas M1-M5, no schema docs (must inspect)
- Section 1.5 (OddsPipe): endpoints, 30-day limit, no Node.js SDK, gotchas O1-O5
- Section 2.1-2.4 (Persistence): HistoricalDepth model, indexes, batch insert, raw SQL fallback
- Section 2.5 (Hybrid Storage): raw Parquet + sampled PostgreSQL decision
- Section 2.7 (Ingestion Scope): target list = ContractMatch union
- Section 3.3 (Normalized Depth Schema): bids/asks structure matching NormalizedOrderBook

### Critical Implementation Notes

**Parquet Library -- `hyparquet` (MANDATORY):**

- Zero dependencies, pure JS, built-in TypeScript declarations
- **ESM-only module** -- use dynamic `import()` in NestJS:
  ```typescript
  const { asyncBufferFromFile, parquetRead } = await import('hyparquet');
  const { compressors } = await import('hyparquet-compressors');
  ```
- Use `onChunk` callback for streaming 150-600MB files -- NEVER load entire file into memory
- Use `asyncBufferFromFile` for local files (lazy I/O via `slice()`, not upfront load)
- Column filtering: read only needed columns (`asset_id`, `timestamp`, `update_type`, bid/ask data)
- **DO NOT** add `parquetjs`, `parquetjs-lite`, `@dsnp/parquetjs`, or `parquet-wasm`

**PMXT Archive File Naming:** `polymarket_orderbook_YYYY-MM-DDTHH.parquet` (hourly UTC). File sizes 150-605MB. Hosted at `https://archive.pmxt.dev/data/`. No auth required.

**PMXT Schema is UNDOCUMENTED:** The exact Parquet columns must be inspected at runtime. Use `parquetMetadataAsync()` from `hyparquet` to read schema before parsing. The data contains `update_type` field with values `price_change` (level updates) and `book_snapshot` (full L2 snapshots). Use `book_snapshot` rows for sampled depth; `price_change` rows can be skipped for MVP.

**PMXT Token ID Filtering (CRITICAL):** The Parquet files contain ALL Polymarket markets. You MUST filter rows where the asset ID matches one of our target contract token IDs (`ContractMatch.polymarketClobTokenId`). Build a `Set<string>` of target token IDs and filter during parsing. Without filtering, you'd be ingesting millions of irrelevant records.

**Hybrid Storage Strategy (from design doc section 2.5):**

- **Raw Parquet files**: store in `data/pmxt-archive/` directory on disk
- **PostgreSQL `historical_depths`**: store sampled snapshots (1 per hour per contract). This is what the backtest engine queries
- **DataCatalog table**: tracks which files are downloaded, their status, time range, and size
- Do NOT load the entire Parquet into PostgreSQL -- sample only `book_snapshot` rows for our target contracts

**OddsPipe 30-Day History Limit:** Free tier limits history to 30 days. Pro tier ($99/mo) not available. This makes OddsPipe supplementary only. If requested date range exceeds 30 days, clamp to the most recent 30 days and log a structured warning. Do NOT throw an error.

**OddsPipe Market ID Mapping:** OddsPipe uses its own integer market IDs, not Polymarket condition_id/token_id or Kalshi tickers. Use `GET /v1/markets/search?q={title}` to find the OddsPipe market ID for our contracts. Cache the mapping to avoid repeated lookups. The market search may return multiple results -- implement basic title matching to select the best match.

**OddsPipe Base URL:** `https://oddspipe.com/v1`. Auth: `X-API-Key` header. Key stored in `ODDSPIPE_API_KEY` env var. No SDK exists for Node.js -- use native `fetch()`.

**OddsPipe Rate Limit:** Free tier 100 req/min. Apply 70% safety buffer -> effective 70 req/min. `minIntervalMs = ceil(60000 / 70) = 857ms`. Use same `lastRequestTs + minIntervalMs` pattern as existing services.

**HTTP Client:** Use native `fetch()` for all HTTP calls. Follow existing codebase pattern (see `src/connectors/polymarket/polymarket-catalog-provider.ts:60`). Use `fetchWithTimeout` (AbortController + 30s timeout) pattern from `polymarket-historical.service.ts`.

**Batch Sizing:** 500 records per `createMany` transaction. Use `skipDuplicates: true` for idempotency. For high-volume PMXT depth data, consider raw SQL `INSERT ... ON CONFLICT DO NOTHING` via `$executeRaw` if `createMany` proves too slow (see design doc section 2.4).

**Depth Data Quality Thresholds:**

- Gap detection: flag gaps >2 hours between consecutive PMXT snapshots (AC says >2 hours)
- Wide spread: flag bid-ask spread >5% (500 bps; on 0-1 probability scale, spread = `asks[0].price - bids[0].price > 0.05`)
- Empty books: flag snapshots with 0 bid or 0 ask levels
- Imbalance: total bid size < 10% of total ask size (or vice versa)

### Paper/Live Mode Boundary

Not applicable for this story. Historical depth/price ingestion operates on historical data only -- no paper/live mode distinction. The `HistoricalDepth` table does NOT have an `is_paper` column.

### File Size Constraints

All services in this story are leaf services with focused responsibilities:

- `PmxtArchiveService`: ~250 lines (5 methods: discover, download, catalog, parse, ingestDepth)
- `OddsPipeService`: ~200 lines (3 methods: resolveMarketId, ingestPrices, rate limiting)
- `DataQualityService` additions: ~60 lines (2 new methods: assessDepthQuality, assessFreshness)
- Orchestrator additions: ~80 lines (new source calls + depth quality assessment)

All within 300-line service / 400-logical-line file limits.

### Existing Code to Reuse -- DO NOT REIMPLEMENT

| What                              | Where                                                                 | Usage                                                                                          |
| --------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `PlatformId` enum                 | `src/common/types/platform.type.ts`                                   | Platform identification                                                                        |
| `BaseEvent` class                 | `src/common/events/base.event.ts`                                     | Event base class with correlationId                                                            |
| `SystemHealthError` class         | `src/common/errors/system-health-error.ts`                            | Error base for codes 4200+                                                                     |
| `SYSTEM_HEALTH_ERROR_CODES`       | same file                                                             | Add new codes 4201, 4208, 4209 here                                                            |
| `EVENT_NAMES` catalog             | `src/common/events/event-catalog.ts`                                  | Existing `BACKTEST_DATA_INGESTED` and `BACKTEST_DATA_QUALITY_WARNING` -- reuse for new sources |
| `BacktestDataIngestedEvent`       | `src/common/events/backtesting.events.ts`                             | Reuse with `source: 'PMXT_ARCHIVE'` / `'ODDSPIPE'`                                             |
| `BacktestDataQualityWarningEvent` | same file                                                             | Reuse for depth quality warnings                                                               |
| `PrismaService`                   | `src/common/prisma.service.ts`                                        | Database access                                                                                |
| `ContractMatch` model             | `prisma/schema.prisma`                                                | Target list source                                                                             |
| `expectEventHandled()`            | `src/common/testing/expect-event-handled.ts`                          | Event wiring verification                                                                      |
| `DataQualityFlags` type           | `src/common/types/historical-data.types.ts`                           | Quality flag structure (extend, don't replace)                                                 |
| `IngestionMetadata` type          | same file                                                             | Return type for ingestion methods                                                              |
| `NormalizedPrice` type            | `src/modules/backtesting/types/normalized-historical.types.ts`        | OddsPipe OHLCV normalization target                                                            |
| `IngestionOrchestratorService`    | `src/modules/backtesting/ingestion/ingestion-orchestrator.service.ts` | Extend with new sources                                                                        |
| `DataQualityService`              | `src/modules/backtesting/ingestion/data-quality.service.ts`           | Extend with depth quality methods                                                              |
| `IngestionModule`                 | `src/modules/backtesting/ingestion/ingestion.module.ts`               | Add new providers                                                                              |
| `HistoricalDataController`        | `src/modules/backtesting/controllers/historical-data.controller.ts`   | Extend coverage endpoints                                                                      |
| native `fetch()`                  | Node.js built-in                                                      | HTTP client for PMXT downloads + OddsPipe API                                                  |
| `HistoricalDataSource` enum       | `prisma/schema.prisma` (lines ~455-463)                               | Values `PMXT_ARCHIVE` and `ODDSPIPE` already defined                                           |

### Patterns from Story 10-9-1a -- Follow Exactly

| Pattern                | Implementation Reference                                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Rate limiting**      | `lastRequestTs + minIntervalMs` (kalshi-historical.service.ts:302-313)                                                               |
| **Batch persistence**  | `createMany({ skipDuplicates: true })`, 500/batch, flush per page (polymarket-historical.service.ts:268)                             |
| **Error handling**     | `fetchWithRetry()` -- 3 max retries, exponential backoff + jitter, throws `SystemHealthError` (kalshi-historical.service.ts:315-354) |
| **Timeout protection** | `fetchWithTimeout()` -- AbortController + 30s (polymarket-historical.service.ts:445-459)                                             |
| **Event emission**     | Orchestrator emits `BacktestDataIngestedEvent` per source/contract (ingestion-orchestrator.service.ts:137-147)                       |
| **Decimal precision**  | `new Decimal(String(value))` to avoid IEEE 754 noise (polymarket-historical.service.ts P12)                                          |
| **Progress tracking**  | `progressMap` with cleanup comment (ingestion-orchestrator.service.ts:30)                                                            |
| **Concurrency guard**  | `_isRunning` flag with try/finally (ingestion-orchestrator.service.ts:33-37)                                                         |
| **Structured logging** | correlationId, matchId, per-source milestones (ingestion-orchestrator.service.ts:90-97)                                              |

### What This Story Does NOT Include

- **Predexon data ingestion** (prices/trades/orderbooks) -- Use for story 10-9-2 matching validation or a separate depth story if needed
- **BacktestRun / BacktestPosition models** -- Story 10-9-3a
- **Backtest engine integration** -- Story 10-9-3a/3b uses depth data this story ingests
- **Monthly partitioning DDL** -- Deferred; Prisma creates unpartitioned tables
- **Dashboard UI for coverage/freshness** -- Story 10-9-5
- **Incremental/cron-based updates** -- Story 10-9-6
- **Error codes 4202-4205, 4210+** -- Later stories
- **Parquet schema auto-detection** -- Inspect manually first; hardcode column mapping for MVP. Auto-detection can be added later
- **PMXT Kalshi data** (`/data/Kalshi/` directory) -- Only Polymarket L2 depth in this story

### Constructor Dependency Summary

| Service                                   | Dependencies                                                                                             | Count | Type   |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------- | ----- | ------ |
| `PmxtArchiveService`                      | PrismaService, EventEmitter2                                                                             | 2     | Leaf   |
| `OddsPipeService`                         | PrismaService, ConfigService, EventEmitter2                                                              | 3     | Leaf   |
| `DataQualityService` (extended)           | EventEmitter2                                                                                            | 1     | Leaf   |
| `IngestionOrchestratorService` (extended) | PrismaService, KalshiHistorical, PolymarketHistorical, PmxtArchive, OddsPipe, DataQuality, EventEmitter2 | 7     | Facade |

All within limits (leaf <=5, facade <=8).

### Module Provider Summary

| Module            | Providers                                                                                         | Count | Status           |
| ----------------- | ------------------------------------------------------------------------------------------------- | ----- | ---------------- |
| `IngestionModule` | KalshiHistorical, PolymarketHistorical, PmxtArchive, OddsPipe, DataQuality, IngestionOrchestrator | 6     | Within <=8 limit |

### Project Structure Notes

```
pm-arbitrage-engine/
├── prisma/schema.prisma                              # MODIFY: Add HistoricalDepth model, DataCatalog model, DataCatalogStatus enum
├── data/pmxt-archive/                                # NEW: Raw PMXT Parquet file storage (gitignored)
├── src/
│   ├── common/
│   │   ├── errors/system-health-error.ts             # MODIFY: add codes 4201, 4208, 4209
│   │   └── types/historical-data.types.ts            # MODIFY: extend DataQualityFlags with depth fields
│   ├── modules/backtesting/
│   │   ├── types/
│   │   │   └── normalized-historical.types.ts        # MODIFY: add NormalizedHistoricalDepth
│   │   ├── ingestion/
│   │   │   ├── ingestion.module.ts                   # MODIFY: add PmxtArchiveService, OddsPipeService
│   │   │   ├── pmxt-archive.service.ts               # NEW
│   │   │   ├── pmxt-archive.service.spec.ts          # NEW
│   │   │   ├── oddspipe.service.ts                   # NEW
│   │   │   ├── oddspipe.service.spec.ts              # NEW
│   │   │   ├── ingestion-orchestrator.service.ts     # MODIFY: add PMXT + OddsPipe calls, depth quality
│   │   │   ├── ingestion-orchestrator.service.spec.ts# MODIFY: test new source calls
│   │   │   ├── data-quality.service.ts               # MODIFY: add assessDepthQuality(), assessFreshness()
│   │   │   └── data-quality.service.spec.ts          # MODIFY: test depth quality + freshness
│   │   └── controllers/
│   │       ├── historical-data.controller.ts         # MODIFY: extend coverage response
│   │       └── historical-data.controller.spec.ts    # MODIFY: test depth coverage
├── .env.example                                       # MODIFY: add ODDSPIPE_API_KEY, PMXT vars
└── .gitignore                                         # MODIFY: add data/pmxt-archive/
```

### Reviewer Context Template (for Lad MCP code_review)

```
## Module: Backtesting & Calibration -- Story 10-9-1b (Depth Data & Third-Party Ingestion)

### Architecture
- Extends ingestion sub-module: src/modules/backtesting/ingestion/
- 2 new services: PmxtArchiveService (Parquet download+parse), OddsPipeService (OHLCV fetch)
- 1 new Prisma model: HistoricalDepth (L2 orderbook snapshots)
- 1 new Prisma model: DataCatalog (PMXT file tracking)
- Extended: DataQualityService (depth quality), IngestionOrchestratorService (new sources)

### Hard Constraints
- ALL prices normalized to Decimal in 0.00-1.00 probability range (decimal.js)
- Parquet library: hyparquet only (zero deps, ESM dynamic import)
- PMXT files 150-600MB -- MUST stream via onChunk, NEVER load into memory
- PMXT token ID filtering: filter parsed rows by target contract Set<string>
- Hybrid storage: raw Parquet on disk + sampled depth in PostgreSQL
- OddsPipe: 30-day free tier limit, clamp date range, log warning
- ALL errors extend SystemHealthError (codes 4201, 4208, 4209)
- Rate limits: OddsPipe 70 req/min effective
- Batch inserts: createMany({ skipDuplicates: true }), 500/batch
- HTTP: native fetch() only

### Testing Requirements
- Co-located specs, Vitest
- Assertion depth: verify payloads with expect.objectContaining
- Event wiring: reuse existing BacktestDataIngestedEvent with new source values
- Collection cleanup: every Map/Set documents cleanup strategy + test
- Mock fetch() via vi.stubGlobal
- Mock hyparquet via vi.mock with dynamic import handling

### Acceptance Criteria
[SEE STORY ACs #1-#7 ABOVE]
```

### References

- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md] -- Authoritative design document
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md#Section 1.4] -- PMXT Archive API, gotchas M1-M5
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md#Section 1.5] -- OddsPipe API, gotchas O1-O5
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md#Section 2.1-2.4] -- HistoricalDepth model, batch insert strategy
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md#Section 2.5] -- Hybrid storage decision (raw Parquet + sampled PostgreSQL)
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md#Section 3.3] -- NormalizedHistoricalDepth schema
- [Source: _bmad-output/implementation-artifacts/10-9-1a-platform-api-price-trade-ingestion.md] -- Previous story patterns and code review fixes
- [Source: _bmad-output/planning-artifacts/epics.md#Story 10-9-1b, line 3533] -- Epic definition and ACs
- [Source: pm-arbitrage-engine/src/modules/backtesting/ingestion/ingestion-orchestrator.service.ts] -- Orchestrator to extend
- [Source: pm-arbitrage-engine/src/modules/backtesting/ingestion/data-quality.service.ts] -- Quality service to extend
- [Source: pm-arbitrage-engine/src/modules/backtesting/ingestion/ingestion.module.ts] -- Module wiring (currently 4 providers)
- [Source: pm-arbitrage-engine/prisma/schema.prisma] -- Existing schema (PMXT_ARCHIVE, ODDSPIPE enums already defined)
- [Source: pm-arbitrage-engine/src/common/errors/system-health-error.ts] -- Error codes 4200, 4206, 4207 taken; 4201, 4208-4209 available
- [Source: pm-arbitrage-engine/src/common/events/backtesting.events.ts] -- Existing events to reuse
- [Source: pm-arbitrage-engine/src/common/types/historical-data.types.ts] -- DataQualityFlags, IngestionMetadata
- [Source: pm-arbitrage-engine/src/modules/backtesting/types/normalized-historical.types.ts] -- NormalizedPrice, NormalizedTrade

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- All 57 ATDD tests GREEN (from 3037 baseline → 3094 total)
- Prisma migration `add_historical_depth_data_catalog` applied successfully
- `hyparquet` + `hyparquet-compressors` installed (ESM dynamic import pattern)
- Lad MCP code review attempted 2x — both reviewers returned empty/errored; proceeding per CLAUDE.md retry policy
- `data/pmxt-archive/` already covered by existing `data/` gitignore entry
- Orchestrator constructor dep count: 7 (facade, within <=8 limit)
- DataQualityService constructor dep count: 2 (EventEmitter2 + PrismaService, leaf <=5)
- IngestionModule providers: 6 (within <=8 limit)
- All services within 300-line / 400-logical-line limits

#### Post-implementation TSC fixes (12 errors resolved)

- **Removed unused `EventEmitter2`** from PmxtArchiveService and OddsPipeService constructors — events are emitted by the orchestrator, not leaf services. Constructor dep counts: PmxtArchiveService 2→1, OddsPipeService 3→2
- **Fixed `RetryStrategy` fields** — used correct interface fields (`maxRetries`, `initialDelayMs`, `maxDelayMs`, `backoffMultiplier`) instead of non-existent `type`/`baseDelayMs`
- **Switched hyparquet from `onChunk` to `onComplete`** with `rowFormat: 'object'` — `onChunk` receives column-oriented `ColumnData`, not row objects. `onComplete` with object row format gives `Record<string, any>[]` which is the correct API for row-oriented access. `asyncBufferFromFile` still provides lazy I/O on the raw Parquet file
- **Defined `OddsPipeCandlestick` interface** — typed `fetchWithRetry` return as `OddsPipeCandlestick[]` instead of `unknown[]` so `.map()` callback can narrow to the candlestick shape
- **Used `Platform.POLYMARKET` enum** — imported `Platform` from `@prisma/client` instead of string literal `'POLYMARKET'` to satisfy Prisma's `createMany` input type
- **Created `flagsToJson()` helper** — serializes `DataQualityFlags` (which contains `Date` objects in `gapDetails`/`spreadDetails`) to JSON-safe `Prisma.InputJsonValue` via `JSON.parse(JSON.stringify())`. Replaced unsafe `as unknown as Prisma.JsonValue` cast
- **Created `toDepthUpdateType()` helper** — runtime validation narrowing `string | null` (Prisma's `String?`) to `'snapshot' | 'price_change' | null` union type
- **Created `parseJsonDepthLevels()` helper** — validates Prisma `JsonValue` structure (which can be `null`, `string`, `boolean`, etc.) into typed `{ price: string; size: string }[]` with proper type narrowing
- **Injected `PrismaService` into `DataQualityService`** — replaced incompatible `FreshnessDb` interface (used `string[]` for `by` param, Prisma requires `HistoricalDepthScalarFieldEnum[]`). `assessFreshness()` now uses `this.prisma` directly. Dep count 1→2, still leaf <=5

### File List

**New files:**

- `pm-arbitrage-engine/src/modules/backtesting/ingestion/pmxt-archive.service.ts`
- `pm-arbitrage-engine/src/modules/backtesting/ingestion/pmxt-archive.service.spec.ts`
- `pm-arbitrage-engine/src/modules/backtesting/ingestion/oddspipe.service.ts`
- `pm-arbitrage-engine/src/modules/backtesting/ingestion/oddspipe.service.spec.ts`
- `pm-arbitrage-engine/prisma/migrations/20260326223858_add_historical_depth_data_catalog/migration.sql`

**Modified files:**

- `pm-arbitrage-engine/prisma/schema.prisma` — HistoricalDepth, DataCatalog, DataCatalogStatus
- `pm-arbitrage-engine/src/common/errors/system-health-error.ts` — codes 4201, 4208, 4209
- `pm-arbitrage-engine/src/common/errors/system-health-error.spec.ts` — unskipped 3 tests
- `pm-arbitrage-engine/src/common/types/historical-data.types.ts` — hasWideSpreads, spreadDetails
- `pm-arbitrage-engine/src/modules/backtesting/types/normalized-historical.types.ts` — NormalizedHistoricalDepth
- `pm-arbitrage-engine/src/modules/backtesting/types/normalized-historical.types.spec.ts` — unskipped 4 tests
- `pm-arbitrage-engine/src/modules/backtesting/ingestion/data-quality.service.ts` — assessDepthQuality, assessFreshness
- `pm-arbitrage-engine/src/modules/backtesting/ingestion/data-quality.service.spec.ts` — unskipped 8 tests
- `pm-arbitrage-engine/src/modules/backtesting/ingestion/ingestion-orchestrator.service.ts` — PMXT+OddsPipe calls, depth quality, freshness
- `pm-arbitrage-engine/src/modules/backtesting/ingestion/ingestion-orchestrator.service.spec.ts` — unskipped 8 tests, updated event count
- `pm-arbitrage-engine/src/modules/backtesting/controllers/historical-data.controller.ts` — depth coverage, freshness endpoints
- `pm-arbitrage-engine/src/modules/backtesting/controllers/historical-data.controller.spec.ts` — unskipped 4 tests
- `pm-arbitrage-engine/src/modules/backtesting/ingestion/ingestion.module.ts` — PmxtArchiveService, OddsPipeService
- `pm-arbitrage-engine/.env.example` — ODDSPIPE_API_KEY, PMXT vars
- `pm-arbitrage-engine/package.json` — hyparquet, hyparquet-compressors
