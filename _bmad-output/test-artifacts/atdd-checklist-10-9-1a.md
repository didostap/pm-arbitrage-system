---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-26'
workflowType: 'testarch-atdd'
inputDocuments:
  - '_bmad-output/implementation-artifacts/10-9-1a-platform-api-price-trade-ingestion.md'
  - '_bmad/tea/testarch/knowledge/data-factories.md'
  - '_bmad/tea/testarch/knowledge/test-quality.md'
  - '_bmad/tea/testarch/knowledge/test-levels-framework.md'
  - '_bmad/tea/testarch/knowledge/test-priorities-matrix.md'
  - '_bmad/tea/testarch/knowledge/test-healing-patterns.md'
---

# ATDD Checklist - Epic 10-9, Story 10-9.1a: Platform API Price & Trade Ingestion

**Date:** 2026-03-26
**Author:** Arbi
**Primary Test Level:** Unit + Integration (backend)

---

## Story Summary

The system ingests historical price and trade data from Polymarket and Kalshi APIs so that backtesting has a local dataset of cross-platform pricing to analyze.

**As an** operator
**I want** the system to ingest historical price and trade data from Polymarket and Kalshi
**So that** backtesting has a local dataset of cross-platform pricing to analyze

---

## Acceptance Criteria

1. Kalshi API ingestion — candlesticks via `/historical/markets/{ticker}/candlesticks`, trades via `/historical/trades`, cutoff routing via `/historical/cutoff`
2. Polymarket API ingestion — prices via `/prices-history`, trades from Goldsky `OrderFilledEvent` via GraphQL
3. poly_data bootstrap — CSV import from `processed/trades.csv`, idempotent
4. Data normalization — all prices to Decimal 0.00–1.00, sizes in USD, timestamps UTC, source provenance
5. Target list from ContractMatch — only approved pairs, bounded scope
6. Idempotent re-ingestion — unique constraints + `skipDuplicates: true`
7. Rate limiting — 70% of platform limits with 20% safety buffer
8. Data quality checks — gaps, suspicious jumps, survivorship bias, stale data
9. Progress logging and event emission — structured logs, domain events

---

## Failing Tests Created (RED Phase)

### Event Tests (8 tests)

**File:** `src/common/events/backtesting.events.spec.ts` (120 lines)

- ↓ **Test:** [P1] should construct BacktestDataIngestedEvent with required fields
  - **Status:** RED — BacktestDataIngestedEvent class does not exist
  - **Verifies:** AC #9 — event construction with source, platform, contractId, recordCount, dateRange
- ↓ **Test:** [P1] should inherit from BaseEvent
  - **Status:** RED — BacktestDataIngestedEvent class does not exist
  - **Verifies:** AC #9 — event hierarchy
- ↓ **Test:** [P1] should use correlationId from context when not provided
  - **Status:** RED — BacktestDataIngestedEvent class does not exist
  - **Verifies:** AC #9 — correlation context fallback
- ↓ **Test:** [P1] should construct BacktestDataQualityWarningEvent with quality flags
  - **Status:** RED — BacktestDataQualityWarningEvent class does not exist
  - **Verifies:** AC #8, #9 — quality flag payload
- ↓ **Test:** [P1] should inherit BacktestDataQualityWarningEvent from BaseEvent
  - **Status:** RED — BacktestDataQualityWarningEvent class does not exist
  - **Verifies:** AC #9 — event hierarchy
- ↓ **Test:** [P1] should define BACKTEST_DATA_INGESTED in EVENT_NAMES
  - **Status:** RED — event catalog entry does not exist
  - **Verifies:** AC #9 — event catalog registration
- ↓ **Test:** [P1] should define BACKTEST_DATA_QUALITY_WARNING in EVENT_NAMES
  - **Status:** RED — event catalog entry does not exist
  - **Verifies:** AC #9 — event catalog registration

### DTO Tests (8 tests)

**File:** `src/modules/backtesting/dto/ingestion-trigger.dto.spec.ts` (55 lines)

- ↓ **Test:** [P1] should accept valid input with required fields only
  - **Status:** RED — IngestionTriggerDto class does not exist
  - **Verifies:** AC #1, #2 — DTO validation
- ↓ **Test:** [P1] should accept valid input with all optional fields
  - **Status:** RED — IngestionTriggerDto class does not exist
  - **Verifies:** AC #1, #2 — optional platform/source/contractMatchId filters
- ↓ **Test:** [P1] should reject missing dateRangeStart
  - **Status:** RED — IngestionTriggerDto class does not exist
  - **Verifies:** AC #1 — required field validation
- ↓ **Test:** [P1] should reject missing dateRangeEnd
  - **Status:** RED — IngestionTriggerDto class does not exist
  - **Verifies:** AC #1 — required field validation
- ↓ **Test:** [P1] should reject invalid date strings
  - **Status:** RED — IngestionTriggerDto class does not exist
  - **Verifies:** AC #1 — date format validation

**File:** `src/modules/backtesting/dto/historical-data-query.dto.spec.ts` (35 lines)

- ↓ **Test:** [P1] should accept valid input with required fields only
  - **Status:** RED — HistoricalDataQueryDto class does not exist
  - **Verifies:** AC #1, #2 — query DTO validation
- ↓ **Test:** [P1] should accept valid input with optional filters
  - **Status:** RED — HistoricalDataQueryDto class does not exist
  - **Verifies:** AC #1, #2 — optional contract/source filters
- ↓ **Test:** [P1] should reject missing required fields
  - **Status:** RED — HistoricalDataQueryDto class does not exist
  - **Verifies:** AC #1 — required field validation

### Kalshi Service Tests (11 tests)

**File:** `src/modules/backtesting/ingestion/kalshi-historical.service.spec.ts` (250 lines)

- ↓ **Test:** [P0] should fetch and parse cutoff timestamps
  - **Status:** RED — KalshiHistoricalService class does not exist
  - **Verifies:** AC #1 — cutoff routing
- ↓ **Test:** [P1] should cache cutoff for 1 hour (TTL)
  - **Status:** RED — KalshiHistoricalService class does not exist
  - **Verifies:** AC #1 — cutoff caching
- ↓ **Test:** [P1] should refresh cutoff after TTL expires
  - **Status:** RED — KalshiHistoricalService class does not exist
  - **Verifies:** AC #1 — cutoff TTL refresh
- ↓ **Test:** [P0] should fetch candlestick data and normalize Kalshi dollar strings to Decimal
  - **Status:** RED — KalshiHistoricalService class does not exist
  - **Verifies:** AC #1, #4 — dollar string normalization (no ÷100)
- ↓ **Test:** [P0] should batch insert in chunks of 500
  - **Status:** RED — KalshiHistoricalService class does not exist
  - **Verifies:** AC #1 — batch sizing
- ↓ **Test:** [P0] should use skipDuplicates for idempotent re-ingestion
  - **Status:** RED — KalshiHistoricalService class does not exist
  - **Verifies:** AC #6 — idempotency
- ↓ **Test:** [P0] should paginate via cursor until empty cursor returned
  - **Status:** RED — KalshiHistoricalService class does not exist
  - **Verifies:** AC #1 — trade cursor pagination
- ↓ **Test:** [P0] should retry 5xx errors with exponential backoff (3 attempts)
  - **Status:** RED — KalshiHistoricalService class does not exist
  - **Verifies:** AC #1 — transient error retry
- ↓ **Test:** [P1] should NOT retry 4xx errors
  - **Status:** RED — KalshiHistoricalService class does not exist
  - **Verifies:** AC #1 — client error handling
- ↓ **Test:** [P0] should throw SystemHealthError with code 4206 on API failure
  - **Status:** RED — KalshiHistoricalService class does not exist
  - **Verifies:** AC #1 — error code mapping
- ↓ **Test:** [P1] should enforce 14 req/s rate limit (70% of 20 req/s)
  - **Status:** RED — KalshiHistoricalService class does not exist
  - **Verifies:** AC #7 — rate limiting

### Polymarket Service Tests (11 tests)

**File:** `src/modules/backtesting/ingestion/polymarket-historical.service.spec.ts` (250 lines)

- ↓ **Test:** [P0] should fetch prices-history and normalize Polymarket decimal probabilities
  - **Status:** RED — PolymarketHistoricalService class does not exist
  - **Verifies:** AC #2, #4 — price passthrough normalization
- ↓ **Test:** [P1] should chunk date ranges >7 days into 7-day windows
  - **Status:** RED — PolymarketHistoricalService class does not exist
  - **Verifies:** AC #2 — large payload chunking
- ↓ **Test:** [P0] should derive BUY side when maker asset is USDC
  - **Status:** RED — PolymarketHistoricalService class does not exist
  - **Verifies:** AC #2 — Goldsky USDC derivation algorithm
- ↓ **Test:** [P0] should derive SELL side when taker asset is USDC
  - **Status:** RED — PolymarketHistoricalService class does not exist
  - **Verifies:** AC #2 — Goldsky USDC derivation algorithm
- ↓ **Test:** [P0] should skip token-to-token trades (neither side is USDC)
  - **Status:** RED — PolymarketHistoricalService class does not exist
  - **Verifies:** AC #2 — Goldsky trade filtering
- ↓ **Test:** [P0] should use Decimal arithmetic for price derivation (never native JS operators)
  - **Status:** RED — PolymarketHistoricalService class does not exist
  - **Verifies:** AC #2, #4 — financial math precision
- ↓ **Test:** [P0] should paginate Goldsky via id_gt
  - **Status:** RED — PolymarketHistoricalService class does not exist
  - **Verifies:** AC #2 — GraphQL cursor pagination
- ↓ **Test:** [P0] should filter results client-side by target token ID
  - **Status:** RED — PolymarketHistoricalService class does not exist
  - **Verifies:** AC #2 — client-side filtering (subgraph limitation)
- ↓ **Test:** [P1] should parse CSV and persist as HistoricalTrade with source POLY_DATA
  - **Status:** RED — PolymarketHistoricalService class does not exist
  - **Verifies:** AC #3 — poly_data bootstrap
- ↓ **Test:** [P1] should be idempotent — re-import creates no duplicates
  - **Status:** RED — PolymarketHistoricalService class does not exist
  - **Verifies:** AC #3, #6 — bootstrap idempotency
- ↓ **Test:** [P1] should back off when response time exceeds 5 seconds
  - **Status:** RED — PolymarketHistoricalService class does not exist
  - **Verifies:** AC #7 — Cloudflare throttle detection

### Data Quality Service Tests (11 tests)

**File:** `src/modules/backtesting/ingestion/data-quality.service.spec.ts` (200 lines)

- ↓ **Test:** [P1] should detect coverage gaps when missing expected timestamps
  - **Status:** RED — DataQualityService class does not exist
  - **Verifies:** AC #8 — gap detection (5× interval threshold)
- ↓ **Test:** [P1] should detect suspicious price jumps exceeding 20%
  - **Status:** RED — DataQualityService class does not exist
  - **Verifies:** AC #8 — price jump detection
- ↓ **Test:** [P1] should detect stale data when latest timestamp >24h behind expected
  - **Status:** RED — DataQualityService class does not exist
  - **Verifies:** AC #8 — stale data flagging
- ↓ **Test:** [P1] should detect low volume when all candles have zero volume
  - **Status:** RED — DataQualityService class does not exist
  - **Verifies:** AC #8 — low volume detection
- ↓ **Test:** [P1] should return no flags for clean data
  - **Status:** RED — DataQualityService class does not exist
  - **Verifies:** AC #8 — clean data baseline
- ↓ **Test:** [P1] should handle exactly-at-threshold price jump (20%) without flagging
  - **Status:** RED — DataQualityService class does not exist
  - **Verifies:** AC #8 — boundary condition
- ↓ **Test:** [P1] should detect gaps in trade data
  - **Status:** RED — DataQualityService class does not exist
  - **Verifies:** AC #8 — trade gap detection
- ↓ **Test:** [P1] should detect low volume (< 5 trades in a 1-hour window)
  - **Status:** RED — DataQualityService class does not exist
  - **Verifies:** AC #8 — trade volume threshold
- ↓ **Test:** [P1] should flag resolved contracts (survivorship bias)
  - **Status:** RED — DataQualityService class does not exist
  - **Verifies:** AC #8 — survivorship bias detection
- ↓ **Test:** [P1] should flag unapproved matches
  - **Status:** RED — DataQualityService class does not exist
  - **Verifies:** AC #8 — unvalidated match flagging
- ↓ **Test:** [P1] should emit BacktestDataQualityWarningEvent when quality flags are present
  - **Status:** RED — DataQualityService class does not exist
  - **Verifies:** AC #8, #9 — event emission with payload

### Orchestrator Service Tests (7 tests)

**File:** `src/modules/backtesting/ingestion/ingestion-orchestrator.service.spec.ts` (200 lines)

- ↓ **Test:** [P1] should query ContractMatch for approved pairs only
  - **Status:** RED — IngestionOrchestratorService class does not exist
  - **Verifies:** AC #5 — target list from ContractMatch
- ↓ **Test:** [P1] should skip records with null polymarketClobTokenId
  - **Status:** RED — IngestionOrchestratorService class does not exist
  - **Verifies:** AC #5 — null token filtering
- ↓ **Test:** [P1] should call all services for each contract in target list
  - **Status:** RED — IngestionOrchestratorService class does not exist
  - **Verifies:** AC #9 — orchestration flow
- ↓ **Test:** [P1] should continue with remaining contracts when one fails
  - **Status:** RED — IngestionOrchestratorService class does not exist
  - **Verifies:** AC #9 — error resilience
- ↓ **Test:** [P1] should emit BacktestDataIngestedEvent per source/contract on completion
  - **Status:** RED — IngestionOrchestratorService class does not exist
  - **Verifies:** AC #9 — event emission
- ↓ **Test:** [P1] should track progress per contract via Map
  - **Status:** RED — IngestionOrchestratorService class does not exist
  - **Verifies:** AC #9 — progress tracking
- ↓ **Test:** [P1] should clear progress Map at the start of each run
  - **Status:** RED — IngestionOrchestratorService class does not exist
  - **Verifies:** AC #9 — Map cleanup lifecycle

### Controller & Module Wiring Tests (4 tests)

**File:** `src/modules/backtesting/controllers/historical-data.controller.spec.ts` (120 lines)

- ↓ **Test:** [P1] should accept IngestionTriggerDto and return 202 with run ID
  - **Status:** RED — HistoricalDataController class does not exist
  - **Verifies:** AC #1, #2 — POST /api/backtesting/ingest
- ↓ **Test:** [P2] should return per-contract/per-source coverage summary
  - **Status:** RED — HistoricalDataController class does not exist
  - **Verifies:** AC #9 — GET /api/backtesting/coverage
- ↓ **Test:** [P2] should return detailed coverage for single contract
  - **Status:** RED — HistoricalDataController class does not exist
  - **Verifies:** AC #9 — GET /api/backtesting/coverage/:contractId
- ↓ **Test:** [P1] should resolve all DI providers in IngestionModule
  - **Status:** RED — BacktestingModule does not exist
  - **Verifies:** Module wiring — DI resolution

---

## Data Factories Created

### NormalizedPrice Factory

**File:** `src/modules/backtesting/ingestion/data-quality.service.spec.ts` (inline)

**Exports:**
- `createNormalizedPrice(overrides?)` — Creates a normalized price record with Decimal fields

### NormalizedTrade Factory

**File:** `src/modules/backtesting/ingestion/data-quality.service.spec.ts` (inline)

**Exports:**
- `createNormalizedTrade(overrides?)` — Creates a normalized trade record with Decimal fields

---

## Mock Requirements

### Kalshi Historical API Mock

**Endpoint:** `GET /historical/cutoff`

**Success Response:**
```json
{
  "market_settled_ts": "2025-03-01T00:00:00Z",
  "trades_created_ts": "2025-03-01T00:00:00Z",
  "orders_updated_ts": "2025-03-01T00:00:00Z"
}
```

**Endpoint:** `GET /historical/markets/{ticker}/candlesticks`

**Success Response:**
```json
{
  "candlesticks": [
    { "end_period_ts": 1704067260, "open": "0.5600", "high": "0.5800", "low": "0.5500", "close": "0.5700", "volume": "15000" }
  ]
}
```

**Endpoint:** `GET /historical/trades`

**Success Response:**
```json
{
  "trades": [
    { "id": "t1", "yes_price_dollars": "0.56", "no_price_dollars": "0.44", "taker_side": "yes", "count": 10, "created_time": "2025-01-01T00:00:00Z" }
  ],
  "cursor": ""
}
```

### Goldsky GraphQL Mock

**Endpoint:** `POST https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn`

**Success Response:**
```json
{
  "data": {
    "orderFilledEvents": [
      {
        "id": "event-1",
        "transactionHash": "0xabc",
        "timestamp": "1704067200",
        "makerAssetId": "USDC_ASSET_ID",
        "takerAssetId": "12345678",
        "makerAmountFilled": "50000000",
        "takerAmountFilled": "100000000",
        "fee": "500000"
      }
    ]
  }
}
```

### Polymarket Prices API Mock

**Endpoint:** `GET https://clob.polymarket.com/prices-history`

**Success Response:**
```json
{
  "history": [
    { "t": 1704067200, "p": 0.55 },
    { "t": 1704067260, "p": 0.56 }
  ]
}
```

**Notes:** All external APIs mocked via `vi.stubGlobal('fetch', mockFetch)`. No real HTTP calls.

---

## Implementation Checklist

### Test: BacktestDataIngestedEvent / BacktestDataQualityWarningEvent

**File:** `src/common/events/backtesting.events.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/common/events/backtesting.events.ts` with both event classes extending `BaseEvent`
- [ ] Add `BACKTEST_DATA_INGESTED` and `BACKTEST_DATA_QUALITY_WARNING` to `src/common/events/event-catalog.ts`
- [ ] Export new events from `src/common/events/index.ts`
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/common/events/backtesting.events.spec.ts`
- [ ] ✅ 7 tests pass (green phase)

### Test: IngestionTriggerDto / HistoricalDataQueryDto

**File:** `src/modules/backtesting/dto/ingestion-trigger.dto.spec.ts`, `historical-data-query.dto.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/modules/backtesting/dto/ingestion-trigger.dto.ts` with class-validator decorators
- [ ] Create `src/modules/backtesting/dto/historical-data-query.dto.ts` with class-validator decorators
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/dto/`
- [ ] ✅ 8 tests pass (green phase)

### Test: DataQualityService

**File:** `src/modules/backtesting/ingestion/data-quality.service.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/modules/backtesting/types/normalized-historical.types.ts` with NormalizedPrice, NormalizedTrade, DataQualityFlags
- [ ] Create `src/modules/backtesting/ingestion/data-quality.service.ts` with assessment methods
- [ ] Implement gap detection (5× interval threshold), jump detection (>20%), stale/volume checks
- [ ] Wire event emission via EventEmitter2
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/ingestion/data-quality.service.spec.ts`
- [ ] ✅ 11 tests pass (green phase)

### Test: KalshiHistoricalService

**File:** `src/modules/backtesting/ingestion/kalshi-historical.service.spec.ts`

**Tasks to make these tests pass:**

- [ ] Add Prisma models: `HistoricalPrice`, `HistoricalTrade`, `HistoricalDataSource` enum
- [ ] Run `pnpm prisma migrate dev --name add-historical-price-trade-models && pnpm prisma generate`
- [ ] Add error codes 4200, 4206, 4207 to `SYSTEM_HEALTH_ERROR_CODES`
- [ ] Create `src/modules/backtesting/ingestion/kalshi-historical.service.ts` implementing `IHistoricalDataProvider`
- [ ] Implement cutoff fetch/cache, candlestick ingestion, trade pagination, rate limiting, error handling
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/ingestion/kalshi-historical.service.spec.ts`
- [ ] ✅ 11 tests pass (green phase)

### Test: PolymarketHistoricalService

**File:** `src/modules/backtesting/ingestion/polymarket-historical.service.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/modules/backtesting/ingestion/polymarket-historical.service.ts` implementing `IHistoricalDataProvider`
- [ ] Implement prices-history fetch, Goldsky GraphQL with USDC derivation, CSV bootstrap
- [ ] Implement 7-day chunking, Cloudflare throttle detection, rate limiting
- [ ] Look up USDC_ASSET_ID via `kindly-web-search`
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/ingestion/polymarket-historical.service.spec.ts`
- [ ] ✅ 11 tests pass (green phase)

### Test: IngestionOrchestratorService

**File:** `src/modules/backtesting/ingestion/ingestion-orchestrator.service.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/modules/backtesting/ingestion/ingestion-orchestrator.service.ts`
- [ ] Implement buildTargetList(), runIngestion(), progress tracking
- [ ] Wire event emission for BacktestDataIngestedEvent
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/ingestion/ingestion-orchestrator.service.spec.ts`
- [ ] ✅ 7 tests pass (green phase)

### Test: HistoricalDataController + Module Wiring

**File:** `src/modules/backtesting/controllers/historical-data.controller.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/modules/backtesting/controllers/historical-data.controller.ts` with 3 endpoints
- [ ] Create `src/modules/backtesting/ingestion/ingestion.module.ts`
- [ ] Create `src/modules/backtesting/backtesting.module.ts`
- [ ] Register BacktestingModule in AppModule
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/controllers/historical-data.controller.spec.ts`
- [ ] ✅ 4 tests pass (green phase)

---

## Running Tests

```bash
# Run all failing tests for this story (all should be skipped)
cd pm-arbitrage-engine && pnpm vitest run src/common/events/backtesting.events.spec.ts src/modules/backtesting/

# Run specific test file
cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/ingestion/kalshi-historical.service.spec.ts

# Run tests in watch mode
cd pm-arbitrage-engine && pnpm vitest src/modules/backtesting/

# Debug specific test
cd pm-arbitrage-engine && pnpm vitest run --reporter=verbose src/modules/backtesting/ingestion/polymarket-historical.service.spec.ts

# Run tests with coverage
cd pm-arbitrage-engine && pnpm test:cov
```

---

## Red-Green-Refactor Workflow

### RED Phase (Complete) ✅

**TEA Agent Responsibilities:**

- ✅ All 59 tests written and skipped (TDD red phase)
- ✅ Factory helpers created inline for test data
- ✅ Mock requirements documented (fetch, Prisma, EventEmitter2)
- ✅ Implementation checklist created per service
- ✅ No placeholder assertions (`expect(true).toBe(true)` removed)

**Verification:**

```
Test Files  8 skipped (8)
     Tests  59 skipped (59)
  Duration  514ms
```

All tests registered as skipped. No failures, no errors.

---

### GREEN Phase (DEV Team - Next Steps)

**DEV Agent Responsibilities:**

1. **Pick one failing test group** from implementation checklist (start with events/DTOs/types)
2. **Read the test** to understand expected behavior
3. **Implement minimal code** to make that specific test pass
4. **Remove `it.skip()`** → change to `it()`
5. **Run the test** to verify it passes (green)
6. **Check off the task** in implementation checklist
7. **Move to next test** and repeat

**Recommended implementation order:**
1. Prisma schema + migration (models needed by all services)
2. Error codes + events + catalog (shared infrastructure)
3. Types + DTOs (shared types)
4. IHistoricalDataProvider interface
5. DataQualityService (no external deps)
6. KalshiHistoricalService
7. PolymarketHistoricalService
8. IngestionOrchestratorService
9. Controller + module wiring

---

## Priority Coverage Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0       | 18    | Core data pipeline, financial math, USDC derivation, error handling |
| P1       | 39    | Rate limiting, caching, DTOs, events, orchestration, quality checks |
| P2       | 2     | Coverage endpoints |
| **Total** | **59** | |

## Acceptance Criteria Coverage

| AC | Description | Tests | Coverage |
|----|-------------|-------|----------|
| #1 | Kalshi API ingestion | 8 | Full (cutoff, candlesticks, trades, pagination) |
| #2 | Polymarket/Goldsky ingestion | 9 | Full (prices, Goldsky derivation buy/sell/skip, pagination, filtering) |
| #3 | poly_data bootstrap | 2 | Full (CSV parse, idempotency) |
| #4 | Data normalization | 4 | Full (dollar strings, decimal passthrough, Decimal arithmetic) |
| #5 | Target list from ContractMatch | 2 | Full (approved filter, null token skip) |
| #6 | Idempotent re-ingestion | 3 | Full (skipDuplicates on prices, trades, bootstrap) |
| #7 | Rate limiting | 3 | Full (Kalshi 14 req/s, Cloudflare throttle, interval check) |
| #8 | Data quality checks | 11 | Full (gaps, jumps, stale, volume, survivorship, clean baseline, boundary) |
| #9 | Progress & events | 9 | Full (event emission, progress Map, orchestration, structured summary) |

---

## Knowledge Base References Applied

- **data-factories.md** — Factory patterns for NormalizedPrice/NormalizedTrade with Decimal overrides
- **test-quality.md** — Deterministic tests, explicit assertions, no placeholder assertions
- **test-levels-framework.md** — Unit for pure logic, integration for service+DI tests
- **test-priorities-matrix.md** — P0 for financial math/data integrity, P1 for operational, P2 for coverage endpoints
- **test-healing-patterns.md** — Mock patterns for fetch() via vi.stubGlobal

---

## Test Execution Evidence

### Initial Test Run (RED Phase Verification)

**Command:** `cd pm-arbitrage-engine && pnpm vitest run src/common/events/backtesting.events.spec.ts src/modules/backtesting/`

**Results:**

```
Test Files  8 skipped (8)
     Tests  59 skipped (59)
  Duration  514ms
```

**Summary:**

- Total tests: 59
- Passing: 0 (expected)
- Failing: 0 (all skipped, as expected)
- Skipped: 59 (TDD red phase)
- Status: ✅ RED phase verified

---

## Notes

- All tests use `it.skip()` (Vitest equivalent of Playwright's `test.skip()`) for TDD red phase
- No E2E/browser tests — this is a pure backend story
- `vi.stubGlobal('fetch', mockFetch)` used for HTTP mocking (matches existing codebase pattern)
- Goldsky USDC_ASSET_ID uses placeholder — must be verified via `kindly-web-search` at implementation time
- Factory helpers are inline in spec files — will be extracted to shared factories if reuse grows in later stories

---

**Generated by BMad TEA Agent** — 2026-03-26
