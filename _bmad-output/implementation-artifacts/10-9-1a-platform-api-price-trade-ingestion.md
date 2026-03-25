# Story 10-9.1a: Platform API Price & Trade Ingestion

Status: done

## Story

As an operator,
I want the system to ingest historical price and trade data from Polymarket and Kalshi,
So that backtesting has a local dataset of cross-platform pricing to analyze.

## Acceptance Criteria

1. **Given** the system has API access to Kalshi
   **When** a data ingestion job is triggered (POST `/api/backtesting/ingest`)
   **Then** historical OHLCV candlestick data is fetched via `GET /historical/markets/{ticker}/candlesticks` (1-min interval)
   **And** historical trades are fetched via `GET /historical/trades` (cursor-paginated, max 1000 per page)
   **And** ingestion handles Kalshi's live/historical partition via `GET /historical/cutoff` before routing queries

2. **Given** the system has access to Polymarket CLOB API and Goldsky subgraph
   **When** a data ingestion job is triggered
   **Then** historical price data is fetched via `GET /prices-history` (1-min fidelity, `market` = token ID)
   **And** historical trades are fetched from Goldsky `OrderFilledEvent` entities (GraphQL, cursor-paginated via `id_gt`)
   **And** price/side are derived from Goldsky amounts using the USDC asset ID derivation algorithm

3. **Given** poly_data pre-built snapshot CSV files are available
   **When** a bootstrap import is triggered
   **Then** Polymarket trade data from `processed/trades.csv` is parsed and persisted as `HistoricalTrade` records
   **And** bootstrap is idempotent (re-import does not create duplicates)

4. **Given** data arrives from heterogeneous sources (Kalshi dollar strings, Polymarket decimal probability, Goldsky raw amounts)
   **When** data is persisted
   **Then** all prices are normalized to `Decimal` in 0.00–1.00 probability range
   **And** all sizes are normalized to `Decimal` in USD
   **And** all timestamps are UTC `Date`
   **And** source provenance is recorded via `HistoricalDataSource` enum

5. **Given** the target contract list is built from `ContractMatch` records
   **When** ingestion runs
   **Then** only contracts in active `ContractMatch` pairs are ingested (bounded scope)
   **And** `kalshiContractId` maps to Kalshi ticker, `polymarketClobTokenId` maps to Polymarket `market` param

6. **Given** ingestion targets a date range
   **When** records already exist for that range
   **Then** re-ingestion does not create duplicates (unique constraints + `skipDuplicates: true`)

7. **Given** rate limits exist (Kalshi 20 req/s Basic, Polymarket 1K req/10s, Goldsky 100 req/s)
   **When** ingestion runs
   **Then** request rates stay at 70% of platform limits with 20% safety buffer (effective: Kalshi 14 req/s, Goldsky 70 req/s)
   **And** Polymarket Cloudflare throttling is handled via HTTP timeout (30s) and slow-response detection

8. **Given** ingested data may have quality issues
   **When** data quality checks run
   **Then** coverage gaps (missing time periods) are flagged
   **And** suspicious price jumps (>20% between consecutive candles) are flagged
   **And** survivorship bias indicators (resolved/delisted contracts) are flagged
   **And** quality flags are stored as `qualityFlags` JSON on each record

9. **Given** ingestion is running
   **When** progress changes
   **Then** structured logs report per-contract/per-source progress
   **And** `BacktestDataIngestedEvent` is emitted on completion per source/contract
   **And** `BacktestDataQualityWarningEvent` is emitted when quality issues are detected

## Tasks / Subtasks

- [x] Task 1: Prisma Schema — New Models & Migration (AC: #4, #6)
  - [x] 1.1 Add `HistoricalDataSource` enum
  - [x] 1.2 Add `HistoricalPrice` model
  - [x] 1.3 Add `HistoricalTrade` model
  - [x] 1.4 Run migration and generate
  - [x] 1.5 Tests: migration verified, 2964 baseline tests pass

- [x] Task 2: Common Schema Types, DTOs & Infrastructure (AC: #4, #8, #9)
  - [x] 2.1 Create normalized-historical.types.ts
  - [x] 2.2 Create historical-data-query.dto.ts
  - [x] 2.3 Create ingestion-trigger.dto.ts
  - [x] 2.4 Create ingestion-progress.dto.ts
  - [x] 2.5 Tests: 8 DTO validation tests pass

- [x] Task 3: Error Codes & Domain Events (AC: #9)
  - [x] 3.1 Add error codes 4200, 4206, 4207
  - [x] 3.2 Create backtesting.events.ts
  - [x] 3.3 Add event catalog entries
  - [x] 3.4 Export from index.ts
  - [x] 3.5 Tests: 7 event tests pass

- [x] Task 4: IHistoricalDataProvider Interface (AC: #1, #2)
  - [x] 4.1 Create historical-data-provider.interface.ts
  - [x] 4.2 Export from interfaces/index.ts

- [x] Task 5: KalshiHistoricalService (AC: #1, #6, #7)
  - [x] 5.1 Create kalshi-historical.service.ts (PrismaService, EventEmitter2 — 2 deps)
  - [x] 5.2 Implement fetchCutoff() with 1hr TTL cache
  - [x] 5.3 Implement ingestPrices() with dollar string normalization, 500/batch
  - [x] 5.4 Implement ingestTrades() with cursor pagination, taker_side mapping
  - [x] 5.5 Rate limiting: 14 req/s via lastRequestTs + minIntervalMs
  - [x] 5.6 Error handling: SystemHealthError 4206, 3 retries with backoff for 5xx, no retry 4xx
  - [x] 5.7 Tests: 11 tests pass

- [x] Task 6: PolymarketHistoricalService (AC: #2, #3, #6, #7)
  - [x] 6.1 Create polymarket-historical.service.ts (PrismaService, EventEmitter2 — 2 deps)
  - [x] 6.2 Implement ingestPrices() with 7-day chunking, decimal passthrough
  - [x] 6.3 Implement Goldsky trade ingestion with GraphQL, id_gt pagination, client-side token filtering
  - [x] 6.4 USDC derivation: USDC_ASSET_ID = 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174 (verified from Polymarket docs). All Decimal arithmetic.
  - [x] 6.5 Implement importPolyDataBootstrap() for CSV import
  - [x] 6.6 Rate limiting: Cloudflare throttle detection (>5s), 30s HTTP timeout, Goldsky 70 req/s
  - [x] 6.7 Tests: 11 tests pass

- [x] Task 7: DataQualityService (AC: #8)
  - [x] 7.1 Create data-quality.service.ts (EventEmitter2 — 1 dep)
  - [x] 7.2 Implement assessPriceQuality(): gaps (5x interval), jumps (>20% strict), stale (>24h), low volume
  - [x] 7.3 Implement assessTradeQuality(): gaps (>1h), low volume (<5 trades per hour window)
  - [x] 7.4 Implement assessSurvivorshipBias(): resolved contracts, unapproved matches
  - [x] 7.5 Emit BacktestDataQualityWarningEvent via emitQualityWarning()
  - [x] 7.6 Tests: 11 tests pass

- [x] Task 8: IngestionOrchestratorService (AC: #5, #9)
  - [x] 8.1 Create ingestion-orchestrator.service.ts (5 deps — facade/orchestrator)
  - [x] 8.2 Implement buildTargetList() from ContractMatch, skip null polymarketClobTokenId
  - [x] 8.3 Implement runIngestion() with correlationId, sequential per contract, error resilience
  - [x] 8.4 Progress tracking with Map cleanup strategy comments
  - [x] 8.5 Emit BacktestDataIngestedEvent per source/contract
  - [x] 8.6 Tests: 7 tests pass

- [x] Task 9: HistoricalDataController & IngestionModule Wiring (AC: #1, #2, #9)
  - [x] 9.1 Create ingestion.module.ts (4 providers)
  - [x] 9.2 Create historical-data.controller.ts (POST /ingest 202, GET /coverage, GET /coverage/:contractId)
  - [x] 9.3 Create backtesting.module.ts importing IngestionModule
  - [x] 9.4 Register BacktestingModule in AppModule
  - [x] 9.5 Tests: 4 controller + wiring tests pass

## Dev Notes

### Design Document Reference

**Authoritative source:** `_bmad-output/implementation-artifacts/10-9-0-design-doc.md` — ALL technical decisions for this story are defined there. When in doubt, the design doc overrides this story file.

Key sections:

- Section 1.1 (Kalshi API): endpoints, auth, rate limits, dollar string normalization, gotchas K1-K5
- Section 1.2 (Polymarket API): `/prices-history` params, token ID confusion (P1), Cloudflare throttling (P2)
- Section 1.3 (Goldsky): `OrderFilledEvent` schema, USDC derivation algorithm, gotchas G1-G5
- Section 1.7 (poly_data): bootstrap snapshot, CSV format
- Section 2.1-2.4 (Persistence): Prisma models, indexes, batch insert strategy
- Section 2.7 (Ingestion Scope): target list = ContractMatch union (third-party pairs added in later stories)
- Section 3 (Common Schema): normalized types, normalization rules per source

### Critical Implementation Notes

**Platform Enum Naming:** Prisma schema defines `enum Platform { KALSHI; POLYMARKET }`. TypeScript code uses `PlatformId` enum from `src/common/types/platform.type.ts` with values `'kalshi'`/`'polymarket'`. In Prisma models, use `Platform` (the Prisma enum). In service/DTO code, use `PlatformId` (the TypeScript enum). They represent the same concept but are different types.

**HTTP Client:** Use native `fetch()` — the existing codebase uses it (see `src/connectors/polymarket/polymarket-catalog-provider.ts:60`). Do NOT add axios, got, node-fetch, or @nestjs/axios.

**GraphQL without library:** Goldsky queries use raw `fetch()` with `POST`, `Content-Type: application/json`, and a JSON body containing `query` and `variables`. Do NOT add `graphql-request` or `@apollo/client`.

**Kalshi Historical Endpoints are PUBLIC:** No RSA-PSS auth required for `/historical/cutoff`, `/historical/markets/{ticker}/candlesticks`, `/historical/trades`. Auth headers are only needed for user-scoped endpoints.

**Kalshi Dollar Strings:** Response prices like `"0.5600"` are already in 0.00–1.00 range. Normalize via `new Decimal(value)` directly — no division by 100.

**Kalshi Field Naming Divergence (Gotcha K1):** Historical endpoints use field names `open`/`volume`, live endpoints use `open_dollars`/`volume_fp`. This story only uses historical endpoints, but name parsers to avoid future confusion.

**Polymarket `market` Param (CRITICAL — Gotcha P1):** The `/prices-history` `market` parameter takes the **token ID** (large decimal number), NOT condition_id, NOT slug. Map from `ContractMatch.polymarketClobTokenId`. Each binary market has TWO token IDs (Yes/No) — use the one stored in ContractMatch.

**Goldsky Derivation (CRITICAL — No price/side fields):** The `OrderFilledEvent` entity has NO `price`, `side`, or `blockNumber` fields. You MUST derive them from `makerAssetId`/`takerAssetId` and amounts. See design doc section 1.3 for the exact algorithm. ALL division uses `Decimal.div()` — NEVER native `/`.

**Goldsky USDC Asset ID:** The USDC collateral token ID for Polymarket CTF Exchange must be looked up from Polymarket documentation or hardcoded as a constant. This is NOT the same as a market token ID.

**poly_data Bootstrap:** This is a one-time import from Python-generated CSV files. The developer runs `poly_data` externally (Python/UV), then the system imports the `processed/trades.csv` output. Not a runtime dependency. CSV columns: `timestamp` (Unix seconds), `price` (decimal 0-1), `usd_amount` (USD), `side` ('buy'/'sell'). Verify column names at implementation time via `kindly-web-search` against the poly_data repository README.

**Batch Sizing:** 500 records per `createMany` transaction (design doc section 2.4). Use `skipDuplicates: true` for idempotency.

**Rate Limiting Strategy:** Simple token-bucket / last-request-timestamp approach per service instance. Do NOT add a rate-limiting library. Calculate `minIntervalMs = 1000 / effectiveRate` and `await sleep(remaining)` before each request. Add jitter (±10%) to backoff delays to avoid thundering herd. Note: rate limiting is per-process, not cluster-aware — acceptable for single-instance backtesting workload.

### Kalshi Cutoff Routing Logic

```
1. Call GET /historical/cutoff → { market_settled_ts, trades_created_ts, orders_updated_ts }
2. For candlestick queries:
   - If requested end_ts <= cutoff.market_settled_ts → use /historical/markets/{ticker}/candlesticks
   - Else → data not yet in historical partition (use live endpoint or wait)
3. For trade queries:
   - If requested max_ts <= cutoff.trades_created_ts → use /historical/trades
   - Else → data not yet in historical partition
4. Cache cutoff for 1 hour (TTL)
```

### Goldsky GraphQL Query Template

```graphql
query OrderFilledEvents($timestamp_gte: BigInt!, $timestamp_lte: BigInt!, $first: Int!, $id_gt: ID) {
  orderFilledEvents(
    where: { timestamp_gte: $timestamp_gte, timestamp_lte: $timestamp_lte, id_gt: $id_gt }
    first: $first
    orderBy: id
    orderDirection: asc
  ) {
    id
    transactionHash
    timestamp
    maker
    taker
    makerAssetId
    takerAssetId
    makerAmountFilled
    takerAmountFilled
    fee
  }
}
```

Paginate via `id_gt` = last result's `id`. First page: omit `id_gt`. `first` = 1000 (max page size).

**Token ID filtering:** After fetching, filter results where `makerAssetId` or `takerAssetId` matches the target contract's token ID. The subgraph does NOT support filtering by arbitrary asset IDs in the `where` clause — filter client-side.

### Paper/Live Mode Boundary

Not applicable for this story. Historical data ingestion operates on historical data only — no paper/live mode distinction. The `HistoricalPrice` and `HistoricalTrade` tables do NOT have an `is_paper` column.

### File Size Constraints

All services in this story are leaf services with focused responsibilities:

- `KalshiHistoricalService`: ~200 lines (3 methods: cutoff, prices, trades)
- `PolymarketHistoricalService`: ~250 lines (4 methods: prices, goldsky trades, poly_data import, USDC derivation helper)
- `DataQualityService`: ~150 lines (3 assessment methods + event emission)
- `IngestionOrchestratorService`: ~200 lines (3 methods: target list, run, progress)
- `HistoricalDataController`: ~100 lines (3 endpoints)

All within 300-line service / 400-logical-line file limits.

### Existing Code to Reuse — DO NOT REIMPLEMENT

| What                        | Where                                        | Usage                               |
| --------------------------- | -------------------------------------------- | ----------------------------------- |
| `PlatformId` enum           | `src/common/types/platform.type.ts`          | Platform identification             |
| `BaseEvent` class           | `src/common/events/base.event.ts`            | Event base class with correlationId |
| `SystemHealthError` class   | `src/common/errors/system-health-error.ts`   | Error base for codes 4200+          |
| `SYSTEM_HEALTH_ERROR_CODES` | same file                                    | Add new codes here                  |
| `EVENT_NAMES` catalog       | `src/common/events/event-catalog.ts`         | Add new event names here            |
| `PrismaService`             | `src/persistence/prisma.service.ts`          | Database access                     |
| `ContractMatch` model       | `prisma/schema.prisma:221`                   | Target list source                  |
| `expectEventHandled()`      | `src/common/testing/expect-event-handled.ts` | Event wiring verification           |
| native `fetch()`            | Node.js built-in (used in connectors/)       | HTTP client                         |

### What This Story Does NOT Include

- **PMXT Archive / Predexon / OddsPipe ingestion** → Story 10-9-1b
- **HistoricalDepth model** → Story 10-9-1b (only HistoricalPrice + HistoricalTrade in this story)
- **BacktestRun / BacktestPosition models** → Story 10-9-3a
- **DataCatalog model** → Story 10-9-1b (for PMXT Parquet file tracking)
- **Third-party pair merging in target list** (Predexon/OddsPipe) → Story 10-9-2 extends the orchestrator
- **Monthly partitioning DDL** → Deferred; Prisma creates unpartitioned tables. Partitioning applied via manual migration when data volume warrants it
- **Dashboard UI for backtests** → Story 10-9-5
- **Error codes 4201-4205** → Later stories in the epic

### Constructor Dependency Summary

| Service                        | Dependencies                                                                              | Count | Type   |
| ------------------------------ | ----------------------------------------------------------------------------------------- | ----- | ------ |
| `KalshiHistoricalService`      | PrismaService, EventEmitter2, Logger                                                      | 3     | Leaf   |
| `PolymarketHistoricalService`  | PrismaService, EventEmitter2, Logger                                                      | 3     | Leaf   |
| `DataQualityService`           | EventEmitter2, Logger                                                                     | 2     | Leaf   |
| `IngestionOrchestratorService` | PrismaService, KalshiHistorical, PolymarketHistorical, DataQuality, EventEmitter2, Logger | 6     | Facade |

All within limits (leaf <=5, facade <=8).

### Project Structure Notes

```
pm-arbitrage-engine/
├── prisma/schema.prisma                              # ADD: HistoricalDataSource enum, HistoricalPrice, HistoricalTrade
├── src/
│   ├── common/
│   │   ├── errors/system-health-error.ts             # MODIFY: add 4200, 4206, 4207 codes
│   │   ├── events/
│   │   │   ├── backtesting.events.ts                 # NEW: BacktestDataIngestedEvent, BacktestDataQualityWarningEvent
│   │   │   ├── backtesting.events.spec.ts            # NEW: event construction specs
│   │   │   ├── event-catalog.ts                      # MODIFY: add backtesting event names
│   │   │   └── index.ts                              # MODIFY: export new events
│   │   └── interfaces/
│   │       ├── historical-data-provider.interface.ts  # NEW: IHistoricalDataProvider + token
│   │       └── index.ts                              # MODIFY: export new interface + token
│   ├── modules/backtesting/
│   │   ├── backtesting.module.ts                     # NEW: root module importing IngestionModule
│   │   ├── types/
│   │   │   └── normalized-historical.types.ts        # NEW: NormalizedPrice, NormalizedTrade, DataQualityFlags
│   │   ├── dto/
│   │   │   ├── historical-data-query.dto.ts          # NEW
│   │   │   ├── ingestion-trigger.dto.ts              # NEW
│   │   │   └── ingestion-progress.dto.ts             # NEW
│   │   ├── ingestion/
│   │   │   ├── ingestion.module.ts                   # NEW: sub-module
│   │   │   ├── kalshi-historical.service.ts          # NEW
│   │   │   ├── kalshi-historical.service.spec.ts     # NEW
│   │   │   ├── polymarket-historical.service.ts      # NEW
│   │   │   ├── polymarket-historical.service.spec.ts # NEW
│   │   │   ├── data-quality.service.ts               # NEW
│   │   │   ├── data-quality.service.spec.ts          # NEW
│   │   │   ├── ingestion-orchestrator.service.ts     # NEW
│   │   │   └── ingestion-orchestrator.service.spec.ts# NEW
│   │   └── controllers/
│   │       ├── historical-data.controller.ts         # NEW
│   │       └── historical-data.controller.spec.ts    # NEW
│   └── app.module.ts                                 # MODIFY: import BacktestingModule
```

### Reviewer Context Template (for Lad MCP code_review)

```
## Module: Backtesting & Calibration — Story 10-9-1a (Platform API Price & Trade Ingestion)

### Architecture
- Sub-module: src/modules/backtesting/ingestion/ — fetches historical data from Kalshi API, Polymarket API, Goldsky subgraph
- 4 services: KalshiHistorical, PolymarketHistorical, DataQuality, IngestionOrchestrator
- 1 controller: HistoricalDataController (POST /ingest, GET /coverage)
- 2 new Prisma models: HistoricalPrice, HistoricalTrade

### Hard Constraints
- ALL prices normalized to Decimal in 0.00–1.00 probability range (decimal.js)
- Kalshi dollar strings ("0.5600") → new Decimal(value) directly (already 0–1)
- Goldsky: derive price/side from amounts — NO price/side fields on entity
- Polymarket market param = token ID (NOT condition_id)
- ALL errors extend SystemHealthError (codes 4200, 4206, 4207)
- Rate limits: Kalshi 14 req/s effective, Goldsky 70 req/s, Polymarket 30s timeout
- Batch inserts: createMany({ skipDuplicates: true }), 500/batch
- HTTP: native fetch() only — no axios/got/graphql-request

### Testing Requirements
- Co-located specs, Vitest
- Assertion depth: verify payloads with expect.objectContaining
- Event wiring: expectEventHandled() for @OnEvent handlers
- Collection cleanup: every Map/Set documents cleanup strategy + test
- Mock fetch() via vi.stubGlobal

### Acceptance Criteria
[SEE STORY ACs #1-#9 ABOVE]
```

### References

- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md] — Authoritative design document
- [Source: _bmad-output/implementation-artifacts/10-9-0-backtesting-design-spike.md] — Design spike with API verification research
- [Source: _bmad-output/planning-artifacts/epics.md#Story 10-9-1a, lines 3513-3531] — Epic definition and ACs
- [Source: _bmad-output/implementation-artifacts/sprint-status.yaml, line 261] — Sprint tracking
- [Source: pm-arbitrage-engine/prisma/schema.prisma:221-268] — ContractMatch model (target list source)
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts] — Existing event names
- [Source: pm-arbitrage-engine/src/common/errors/system-health-error.ts] — Error code registry (4001-4010, 4500 taken)
- [Source: pm-arbitrage-engine/src/common/errors/llm-scoring-error.ts] — LLM codes (4100-4103 taken)
- [Source: pm-arbitrage-engine/src/common/events/base.event.ts] — BaseEvent pattern
- [Source: pm-arbitrage-engine/src/common/interfaces/index.ts] — Interface export pattern
- [Source: pm-arbitrage-engine/src/common/types/platform.type.ts] — PlatformId enum
- [Source: pm-arbitrage-engine/src/connectors/polymarket/polymarket-catalog-provider.ts:60] — native fetch() pattern

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no debugging sessions required.

### Completion Notes List

- All 9 tasks completed with 73 tests passing (59 original + 14 added during code review)
- Baseline: 2964 tests → Post-implementation: 3023 tests → Post-review: 3037 tests, 0 regressions
- USDC_ASSET_ID verified from Polymarket official docs: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`
- All financial math uses Decimal.js — no native JS operators on monetary values
- All errors extend SystemHealthError (codes 4200, 4206, 4207)
- Rate limiting: simple lastRequestTs + minIntervalMs (no library dependency)
- Batch inserts: createMany with skipDuplicates, 500/batch
- HTTP: native fetch() only — no additional dependencies
- Map cleanup strategy comments on all Map fields
- Production files lint clean; test files have expected unsafe-any warnings

### Change Log

- 2026-03-26: Implemented story 10-9-1a — all 9 tasks, 59 tests, 0 regressions
- 2026-03-26: Post-implementation 3-layer adversarial code review (Blind Hunter + Edge Case Hunter + Acceptance Auditor). Fixed 25 patches + 2 intent gaps. 14 new tests added. Final: 3037 tests, 0 regressions. Details below.

### Code Review Fixes (2026-03-26)

**25 patches applied, 2 intent gaps resolved, 2 deferred, 4 rejected as noise.**

#### Critical/High (P1–P7)

- **P1:** Architecture boundary — moved `DataQualityFlags` + `IngestionMetadata` from `modules/backtesting/types/` to `common/types/historical-data.types.ts`. `common/` no longer imports from `modules/`.
- **P2:** Cutoff routing — `ingestPrices`/`ingestTrades` now compare date range against cutoff timestamps. Data clamped to historical partition boundary; returns 0 records if range entirely beyond cutoff.
- **P3:** Data quality assessment fully wired — `assessPriceQuality`/`assessTradeQuality` called on real DB data (query back up to 10K records per source). `assessSurvivorshipBias` uses actual `ContractMatch.operatorApproved`/`resolutionTimestamp` from DB. Quality flags persisted to records via `updateMany`.
- **P4:** `BacktestDataIngestedEvent` now emitted 4 times per contract (Kalshi prices, Kalshi trades, Polymarket prices, Goldsky trades) with correct source/platform values, instead of single `source: 'all'` event.
- **P5:** `externalTradeId` no longer nullable — synthetic ID generated (`kalshi-{contractId}-{timestamp}-{price}`) when Kalshi API response lacks `trade_id`/`id`, preventing duplicate null-key rows.
- **P6:** Concurrency guard — `isRunning` flag on orchestrator, `try/finally` reset. Controller returns 409 Conflict if ingestion already running.
- **P7:** Controller outer `.catch()` now logs errors via `Logger.error` instead of swallowing silently.

#### Medium (P8–P19)

- **P8:** Removed dead DTO fields (`platforms`, `sources`, `contractMatchIds`) from `IngestionTriggerDto`. Removed corresponding test.
- **P9:** Controller validates `dateRangeStart < dateRangeEnd`, throws `BadRequestException` on inverted range.
- **P10:** Goldsky GraphQL requests now use `fetchWithTimeout` (AbortController + 30s timeout) instead of bare `fetch`.
- **P11:** Cloudflare throttle detection triggers 10s backoff on next chunk; `_isThrottled` flag reset after backoff.
- **P12:** Polymarket prices: `new Decimal(String(point.p))` instead of `new Decimal(point.p)` to avoid IEEE 754 floating-point noise.
- **P13:** CSV import validates field count (≥4), numeric fields (`isNaN` check), side enum (`buy`/`sell` only). Malformed lines skipped with logger warning.
- **P14:** `assessPriceQuality` and `assessTradeQuality` now sort input by timestamp ascending before analysis, preventing false gaps/jumps from unsorted data.
- **P15:** Price jump detection uses `Decimal.minus().abs().div()` instead of `.toNumber()` + native JS operators.
- **P16:** Structured progress logs at run start (`correlationId`, date range), per-contract/per-source milestones, and run completion.
- **P17:** Removed Kalshi service URL fallback — `ConfigService.get()` with `env.schema.ts` default is the single source of truth.
- **P18:** Trade ingestion flushes per page, price per chunk — no unbounded in-memory accumulation.
- **P19:** Removed unused `runId` from 202 response (was generated but never tracked).

#### Low (P20–P23)

- **P20:** `fetchCutoff` routed through `fetchWithRetry` for proper error handling on non-2xx responses.
- **P21:** Trade quality window loop uses strict `<` instead of `<=` to prevent ghost window at boundary.
- **P22:** Rate-limit real-timer test isolated in dedicated `describe` block with own `beforeEach`/`afterEach`.
- **P23:** Controller test verifies `runIngestion` call arguments with `expect.objectContaining({ dateRangeStart, dateRangeEnd })`.

#### Intent Gaps (IG-1, IG-2) — Resolved via research

- **IG-1:** Kalshi `ingestPrices` now chunks date ranges into 7-day windows. Research confirmed: Kalshi batch endpoint caps at 10K candles; single-market endpoint has undocumented `maxAggregateCandidates` limit with silent truncation.
- **IG-2:** Goldsky `id_gt` pagination documented as known limitation. The Graph docs state entity IDs sort alphanumerically, NOT by creation time. Comment added with TODO for timestamp-based pagination in follow-up story.

#### Deferred (D1–D2)

- **D1:** Rate limiter `lastRequestTs` TOCTOU race — acceptable for single-instance sequential ingestion.
- **D2:** `IHistoricalDataProvider` interface unused — forward-looking per Task 4 spec, may be used in later stories.

### File List

**New files:**

- `prisma/migrations/20260326171706_add_historical_price_trade_models/migration.sql`
- `src/common/types/historical-data.types.ts` — `DataQualityFlags`, `IngestionMetadata` (moved from modules for P1)
- `src/modules/backtesting/types/normalized-historical.types.ts` — `NormalizedPrice`, `NormalizedTrade` (re-exports moved types)
- `src/modules/backtesting/dto/ingestion-trigger.dto.ts`
- `src/modules/backtesting/dto/historical-data-query.dto.ts`
- `src/modules/backtesting/dto/ingestion-progress.dto.ts`
- `src/modules/backtesting/ingestion/kalshi-historical.service.ts`
- `src/modules/backtesting/ingestion/kalshi-historical.service.spec.ts`
- `src/modules/backtesting/ingestion/polymarket-historical.service.ts`
- `src/modules/backtesting/ingestion/polymarket-historical.service.spec.ts`
- `src/modules/backtesting/ingestion/data-quality.service.ts`
- `src/modules/backtesting/ingestion/data-quality.service.spec.ts`
- `src/modules/backtesting/ingestion/ingestion-orchestrator.service.ts`
- `src/modules/backtesting/ingestion/ingestion-orchestrator.service.spec.ts`
- `src/modules/backtesting/ingestion/ingestion.module.ts`
- `src/modules/backtesting/controllers/historical-data.controller.ts`
- `src/modules/backtesting/controllers/historical-data.controller.spec.ts`
- `src/modules/backtesting/backtesting.module.ts`
- `src/common/events/backtesting.events.ts`
- `src/common/events/backtesting.events.spec.ts`
- `src/common/interfaces/historical-data-provider.interface.ts`

**Modified files:**

- `prisma/schema.prisma` — Added HistoricalDataSource enum, HistoricalPrice, HistoricalTrade models
- `src/common/errors/system-health-error.ts` — Added codes 4200, 4206, 4207
- `src/common/events/event-catalog.ts` — Added backtesting event names
- `src/common/events/index.ts` — Export backtesting events
- `src/common/interfaces/index.ts` — Export IHistoricalDataProvider + token
- `src/app.module.ts` — Import BacktestingModule
- `src/modules/backtesting/dto/ingestion-trigger.dto.spec.ts` — ATDD tests (removed dead optional-fields test for P8)
- `src/modules/backtesting/dto/historical-data-query.dto.spec.ts` — Enabled ATDD tests
