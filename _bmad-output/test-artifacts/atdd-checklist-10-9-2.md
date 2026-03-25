---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-27'
workflowType: 'testarch-atdd'
inputDocuments:
  - '_bmad-output/implementation-artifacts/10-9-2-cross-platform-pair-matching-validation.md'
  - '_bmad/tea/testarch/knowledge/data-factories.md'
  - '_bmad/tea/testarch/knowledge/test-quality.md'
  - '_bmad/tea/testarch/knowledge/test-levels-framework.md'
  - '_bmad/tea/testarch/knowledge/test-priorities-matrix.md'
  - '_bmad/tea/testarch/knowledge/test-healing-patterns.md'
---

# ATDD Checklist - Epic 10-9, Story 10-9.2: Cross-Platform Pair Matching Validation

**Date:** 2026-03-27
**Author:** Arbi
**Primary Test Level:** Unit + Integration (backend)

---

## Story Summary

The system cross-references our ContractMatch records against OddsPipe and Predexon matched pairs, so that the operator can validate matching accuracy and identify pairs we may have missed.

**As an** operator
**I want** to cross-reference our contract matching against OddsPipe and Predexon matched pairs
**So that** I can validate matching accuracy and identify pairs we may have missed

---

## Acceptance Criteria

1. OddsPipe matched pairs fetched via `GET /v1/spreads` with pagination, normalized to common comparison structure
2. Predexon matched pairs fetched via `GET /v2/matching-markets/pairs` with offset pagination, normalized to common structure, `similarity` preserved (may be `null`)
3. Our ContractMatch records compared against both external sources using contract identifiers (primary) with fuzzy title fallback for OddsPipe
4. Validation report categorizes every pair into exactly one bucket: Confirmed, Our-only, External-only, Conflict
5. External-only entries include source metadata and are flagged as knowledge base candidates
6. Conflict entries include all sources' match details and specific disagreement description
7. `MatchValidationReport` persisted and queryable via REST API (`GET /reports`, `GET /reports/:id`)
8. `BacktestValidationCompletedEvent` on completion, `BacktestDataQualityWarningEvent` if conflicts > 0

---

## Failing Tests Created (RED Phase)

### Types & DTO Tests (10 tests)

**File:** `src/modules/backtesting/types/match-validation.types.spec.ts` (NEW, ~80 lines)

- ↓ **Test:** [P1] should construct ExternalMatchedPair with OddsPipe source and spread data
  - **Status:** RED — ExternalMatchedPair type does not exist
  - **Verifies:** AC #1 — type definition for normalized external pairs
- ↓ **Test:** [P1] should construct ExternalMatchedPair with Predexon source and null similarity
  - **Status:** RED — ExternalMatchedPair type does not exist
  - **Verifies:** AC #2 — null similarity for pre-Jan-2025 matches
- ↓ **Test:** [P1] should construct ValidationReportEntry with all 4 category values
  - **Status:** RED — ValidationReportEntry type does not exist
  - **Verifies:** AC #4 — report entry type definition
- ↓ **Test:** [P1] should require conflictDescription for conflict category entries
  - **Status:** RED — ValidationReportEntry type does not exist
  - **Verifies:** AC #6 — conflict description required
- ↓ **Test:** [P1] should construct ValidationReportSummary with per-source counts
  - **Status:** RED — ValidationReportSummary type does not exist
  - **Verifies:** AC #4 — summary counts type definition

**File:** `src/modules/backtesting/dto/match-validation.dto.spec.ts` (NEW, ~70 lines)

- ↓ **Test:** [P1] should accept valid TriggerValidationDto with includeSources array
  - **Status:** RED — TriggerValidationDto class does not exist
  - **Verifies:** AC #1, #2 — source selection DTO
- ↓ **Test:** [P1] should default to both sources when includeSources omitted or empty
  - **Status:** RED — TriggerValidationDto class does not exist
  - **Verifies:** AC #1, #2 — default source behavior
- ↓ **Test:** [P1] should reject unknown source names with 400
  - **Status:** RED — TriggerValidationDto class does not exist
  - **Verifies:** AC #1, #2 — input validation

### Error Code Tests (2 tests)

**File:** `src/common/errors/system-health-error.spec.ts` (EXTENDED, +~30 lines)

- ↓ **Test:** [P1] should define BACKTEST_PREDEXON_API_ERROR with code 4202
  - **Status:** RED — error code 4202 not defined in SYSTEM_HEALTH_ERROR_CODES
  - **Verifies:** AC #2 — Predexon API error classification
- ↓ **Test:** [P1] should define BACKTEST_VALIDATION_FAILURE with code 4203
  - **Status:** RED — error code 4203 not defined
  - **Verifies:** AC #4 — validation engine error classification

### Event Tests (2 tests)

**File:** `src/common/events/backtesting.events.spec.ts` (EXTENDED, +~40 lines)

- ↓ **Test:** [P1] should construct BacktestValidationCompletedEvent with summary counts and reportId
  - **Status:** RED — BacktestValidationCompletedEvent class does not exist
  - **Verifies:** AC #8 — event construction with payload
- ↓ **Test:** [P1] should register BACKTEST_VALIDATION_COMPLETED in event catalog
  - **Status:** RED — event name not in EVENT_NAMES catalog
  - **Verifies:** AC #8 — event catalog entry

### PredexonMatchingService Tests (9 tests)

**File:** `src/modules/backtesting/validation/predexon-matching.service.spec.ts` (NEW, ~250 lines)

- ↓ **Test:** [P0] should fetch matched pairs from GET /v2/matching-markets/pairs and normalize to ExternalMatchedPair
  - **Status:** RED — PredexonMatchingService class does not exist
  - **Verifies:** AC #2 — core pair fetching + normalization
- ↓ **Test:** [P1] should paginate with offset until has_more === false
  - **Status:** RED — PredexonMatchingService class does not exist
  - **Verifies:** AC #2 — offset-based pagination loop
- ↓ **Test:** [P1] should include lowercase x-api-key header from PREDEXON_API_KEY config
  - **Status:** RED — PredexonMatchingService class does not exist
  - **Verifies:** AC #2 — authentication (lowercase header differs from OddsPipe)
- ↓ **Test:** [P1] should enforce 72ms minimum interval between requests (14 req/s effective)
  - **Status:** RED — PredexonMatchingService class does not exist
  - **Verifies:** AC #2 — rate limiting (70% of Dev tier 20 req/s)
- ↓ **Test:** [P1] should preserve null similarity for pre-Jan-2025 matches
  - **Status:** RED — PredexonMatchingService class does not exist
  - **Verifies:** AC #2 — null similarity handling
- ↓ **Test:** [P1] should abort after 30s via fetchWithTimeout
  - **Status:** RED — PredexonMatchingService class does not exist
  - **Verifies:** AC #2 — timeout protection
- ↓ **Test:** [P1] should retry with exponential backoff (3 attempts) on transient errors
  - **Status:** RED — PredexonMatchingService class does not exist
  - **Verifies:** AC #2 — retry strategy
- ↓ **Test:** [P1] should throw SystemHealthError code 4202 after all retries exhausted
  - **Status:** RED — PredexonMatchingService class does not exist, error code 4202 not defined
  - **Verifies:** AC #2 — error handling
- ↓ **Test:** [P0] should return empty array on 403 (free tier) with warn-level log, not throw
  - **Status:** RED — PredexonMatchingService class does not exist
  - **Verifies:** AC #2 — graceful degradation on expired/missing Dev tier

### OddsPipeService Extension Tests (5 tests)

**File:** `src/modules/backtesting/ingestion/oddspipe.service.spec.ts` (EXTENDED, +~120 lines)

- ↓ **Test:** [P0] should fetch matched pairs from GET /v1/spreads and normalize to ExternalMatchedPair
  - **Status:** RED — fetchMatchedPairs() method does not exist on OddsPipeService
  - **Verifies:** AC #1 — core spreads fetching + normalization
- ↓ **Test:** [P1] should preserve spread metadata (yes_diff, polyYesPrice, kalshiYesPrice)
  - **Status:** RED — fetchMatchedPairs() method does not exist
  - **Verifies:** AC #1 — spread data preservation for report
- ↓ **Test:** [P1] should extract Polymarket and Kalshi identifiers from spread response objects
  - **Status:** RED — fetchMatchedPairs() method does not exist
  - **Verifies:** AC #1, #3 — identifier extraction for matching
- ↓ **Test:** [P1] should reuse existing X-API-Key auth and rate limiting from fetchWithRateLimit
  - **Status:** RED — fetchMatchedPairs() method does not exist
  - **Verifies:** AC #1 — auth and rate-limit reuse
- ↓ **Test:** [P1] should handle error responses with existing error handling patterns
  - **Status:** RED — fetchMatchedPairs() method does not exist
  - **Verifies:** AC #1 — error resilience

### MatchValidationService Tests (22 tests)

**File:** `src/modules/backtesting/validation/match-validation.service.spec.ts` (NEW, ~450 lines)

#### loadOurMatches

- ↓ **Test:** [P0] should load all ContractMatch records and build polymarket/kalshi/composite lookup maps
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #3 — lookup map construction for efficient matching

#### matchExternalPair (ID-based + fuzzy fallback)

- ↓ **Test:** [P0] should match Predexon pair by polymarketContractId and kalshiContractId (ID-based)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #3 — ID-based matching (primary strategy)
- ↓ **Test:** [P0] should fall back to fuzzy title matching when OddsPipe pair lacks platform IDs
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #3 — fuzzy title fallback for OddsPipe
- ↓ **Test:** [P1] should use stop-word removal and bidirectional substring containment for fuzzy matching
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #3 — matching algorithm (reuse PreFilterService stop-word pattern)
- ↓ **Test:** [P1] should accept fuzzy match when >=60% of significant tokens overlap (default threshold)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #3 — configurable threshold (VALIDATION_TITLE_MATCH_THRESHOLD)

#### Conflict Detection Decision Table (AC#4 — 10 rows)

- ↓ **Test:** [P0] should categorize as Confirmed when all 3 sources agree (A↔B, A↔B, A↔B)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #4 — decision table row 1
- ↓ **Test:** [P0] should categorize as Confirmed when ours + OddsPipe agree (A↔B, A↔B, —)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #4 — decision table row 2
- ↓ **Test:** [P0] should categorize as Confirmed when ours + Predexon agree (A↔B, —, A↔B)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #4 — decision table row 3
- ↓ **Test:** [P1] should categorize as Our-only when no external source has the pair (A↔B, —, —)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #4 — decision table row 4
- ↓ **Test:** [P1] should categorize as External-only when both externals agree but we don't have it (—, A↔B, A↔B)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #4, #5 — decision table row 5
- ↓ **Test:** [P1] should categorize as External-only when only OddsPipe has the pair (—, A↔B, —)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #4, #5 — decision table row 6
- ↓ **Test:** [P1] should categorize as External-only when only Predexon has the pair (—, —, A↔B)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #4, #5 — decision table row 7
- ↓ **Test:** [P0] should categorize as Conflict when OddsPipe disagrees on Kalshi side (A↔B, A↔C, A↔B)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #4, #6 — decision table row 8
- ↓ **Test:** [P0] should categorize as Conflict when Predexon disagrees on Kalshi side (A↔B, A↔B, A↔C)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #4, #6 — decision table row 9
- ↓ **Test:** [P1] should categorize as Conflict when externals disagree and we have no opinion (—, A↔B, A↔C)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #4, #6 — decision table row 10 (variant: no our match)

#### Report Entry Content (AC#5, #6)

- ↓ **Test:** [P1] should set isKnowledgeBaseCandidate=true for all external-only entries with full metadata
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #5 — external-only entries include source(s), titles, IDs, similarity, spread data
- ↓ **Test:** [P1] should include conflictDescription naming sources and identifiers for conflict entries
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #6 — conflict description format (e.g., "Our ContractMatch pairs PM-xxx with K-yyy, but Predexon pairs PM-xxx with K-zzz")

#### Orchestration & Guards

- ↓ **Test:** [P1] should return 409 when validation is already running (concurrency guard)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** Task 5.6 — _isRunning flag with try/finally
- ↓ **Test:** [P1] should reset _isRunning after 10-minute timeout
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** Task 5.6 — safety timeout (600,000ms)

#### Event Emission (AC#8)

- ↓ **Test:** [P1] should emit BacktestValidationCompletedEvent with summary counts and reportId on success
  - **Status:** RED — MatchValidationService class does not exist, BacktestValidationCompletedEvent not defined
  - **Verifies:** AC #8 — completion event with payload verification
- ↓ **Test:** [P1] should emit BacktestDataQualityWarningEvent when conflict count > 0
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #8 — conditional quality warning event
- ↓ **Test:** [P1] should NOT emit events on validation failure
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #8 — events only after successful DB commit

#### Persistence (AC#7)

- ↓ **Test:** [P0] should persist MatchValidationReport with summary counts and full reportData JSON
  - **Status:** RED — MatchValidationService class does not exist, MatchValidationReport model not in schema
  - **Verifies:** AC #7 — report persistence

#### Edge Cases

- ↓ **Test:** [P1] should handle empty external responses gracefully (both sources return 0 pairs)
  - **Status:** RED — MatchValidationService class does not exist
  - **Verifies:** AC #4 — all our matches become our-only when no external data

### Controller & Module Wiring Tests (5 tests)

**File:** `src/modules/backtesting/controllers/match-validation.controller.spec.ts` (NEW, ~130 lines)

- ↓ **Test:** [P1] POST /api/backtesting/validation/run should return 202 with correlationId
  - **Status:** RED — MatchValidationController class does not exist
  - **Verifies:** AC #7 — trigger endpoint returns async 202
- ↓ **Test:** [P1] GET /api/backtesting/validation/reports should return paginated list ordered by runTimestamp desc
  - **Status:** RED — MatchValidationController class does not exist
  - **Verifies:** AC #7 — report listing endpoint
- ↓ **Test:** [P1] GET /api/backtesting/validation/reports/:id should return full report with reportData
  - **Status:** RED — MatchValidationController class does not exist
  - **Verifies:** AC #7 — single report endpoint
- ↓ **Test:** [P1] POST /api/backtesting/validation/run should return 409 when already running
  - **Status:** RED — MatchValidationController class does not exist
  - **Verifies:** Task 5.6 — concurrency guard surfaced via controller
- ↓ **Test:** [P1] ValidationModule should compile with PredexonMatchingService, MatchValidationService, and OddsPipeService
  - **Status:** RED — ValidationModule does not exist
  - **Verifies:** Task 6.2, 6.3 — module wiring, OddsPipeService export from IngestionModule

---

## Data Factories Created

### ExternalMatchedPair Factory

**File:** `src/modules/backtesting/validation/match-validation.service.spec.ts` (inline)

**Exports:**
- `createExternalPair(overrides?)` — Creates an ExternalMatchedPair with OddsPipe or Predexon source

### ContractMatch Factory

**File:** `src/modules/backtesting/validation/match-validation.service.spec.ts` (inline)

**Exports:**
- `createContractMatch(overrides?)` — Creates a ContractMatch record with polymarketContractId, kalshiContractId, descriptions

### Predexon API Response Factory

**File:** `src/modules/backtesting/validation/predexon-matching.service.spec.ts` (inline)

**Exports:**
- `createPredexonPairResponse(pairs, pagination?)` — Creates mock Predexon API paginated response
- `createPredexonPair(overrides?)` — Creates a single Predexon pair with condition_id, kalshi identifier, similarity

### OddsPipe Spreads Response Factory

**File:** `src/modules/backtesting/ingestion/oddspipe.service.spec.ts` (inline)

**Exports:**
- `createSpreadsResponse(items)` — Creates mock OddsPipe /v1/spreads response with items array
- `createSpreadItem(overrides?)` — Creates a single spread item with polymarket/kalshi objects and spread data

---

## Mock Requirements

### Predexon API Mock

**Endpoint:** `GET https://api.predexon.com/v2/matching-markets/pairs?limit=100&offset=0`

**Auth Header:** `x-api-key: test-predexon-key` (lowercase)

**Success Response:**
```json
{
  "data": [
    {
      "polymarket_condition_id": "0xabc123",
      "kalshi_ticker": "KXBTC-24DEC31",
      "polymarket_title": "Will Bitcoin exceed $100k?",
      "kalshi_title": "Bitcoin above $100,000",
      "similarity": 0.97
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 100,
    "offset": 0,
    "has_more": true
  }
}
```

**403 Response (free tier):**
```json
{ "error": "Forbidden", "message": "Dev tier subscription required" }
```

### OddsPipe Spreads Mock

**Endpoint:** `GET https://oddspipe.com/v1/spreads`

**Auth Header:** `X-API-Key: test-oddspipe-key` (uppercase)

**Success Response:**
```json
{
  "items": [
    {
      "polymarket": {
        "title": "Will Bitcoin exceed $100k?",
        "yes_price": 0.65
      },
      "kalshi": {
        "title": "Bitcoin above $100,000",
        "yes_price": 0.62
      },
      "spread": {
        "yes_diff": 0.03
      }
    }
  ]
}
```

### Prisma Mock

**Models mocked:**
- `contractMatch.findMany()` — returns array of ContractMatch records
- `matchValidationReport.create()` — persists report record
- `matchValidationReport.findMany()` — paginated report listing
- `matchValidationReport.findUnique()` — single report by ID

**Notes:** All external APIs mocked via `vi.stubGlobal('fetch', mockFetch)`. Prisma mocked via `vi.fn()` per existing patterns. ConfigService mocked for API keys and thresholds. EventEmitter2 spied for event emission verification.

---

## Implementation Checklist

### Test: Prisma Schema — MatchValidationReport Model

**Tasks (no dedicated test file — verified via service tests):**

- [ ] Add `MatchValidationReport` model to `prisma/schema.prisma`: `id` (autoincrement), `correlationId`, `runTimestamp`, `totalOurMatches`, `totalOddsPipePairs`, `totalPredexonPairs`, `confirmedCount`, `ourOnlyCount`, `externalOnlyCount`, `conflictCount`, `reportData` (Json), `durationMs`, `createdAt`. Table name `match_validation_reports`, all columns `@map` to snake_case
- [ ] Run `pnpm prisma migrate dev --name add-match-validation-report && pnpm prisma generate`
- [ ] Verify baseline tests still pass (~3101)

### Test: Error Codes (4202, 4203)

**File:** `src/common/errors/system-health-error.spec.ts`

**Tasks to make these tests pass:**

- [ ] Add `BACKTEST_PREDEXON_API_ERROR: 4202` to `SYSTEM_HEALTH_ERROR_CODES`
- [ ] Add `BACKTEST_VALIDATION_FAILURE: 4203` to `SYSTEM_HEALTH_ERROR_CODES`
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/common/errors/system-health-error.spec.ts`
- [ ] New error code tests pass (green phase)

### Test: Types — ExternalMatchedPair, ValidationReportEntry, ValidationReportSummary

**File:** `src/modules/backtesting/types/match-validation.types.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/modules/backtesting/types/match-validation.types.ts` with `ExternalMatchedPair`, `ValidationReportEntry`, `ValidationReportSummary` types per story spec
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/types/match-validation.types.spec.ts`
- [ ] 5 tests pass (green phase)

### Test: DTOs — TriggerValidationDto, ValidationReportResponseDto

**File:** `src/modules/backtesting/dto/match-validation.dto.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/modules/backtesting/dto/match-validation.dto.ts` with `TriggerValidationDto` (optional `includeSources` with `@IsIn` validation), `ValidationReportResponseDto`
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/dto/match-validation.dto.spec.ts`
- [ ] 3 tests pass (green phase)

### Test: Events — BacktestValidationCompletedEvent + Catalog

**File:** `src/common/events/backtesting.events.spec.ts`

**Tasks to make these tests pass:**

- [ ] Add `BacktestValidationCompletedEvent` class extending `BaseEvent` to `src/common/events/backtesting.events.ts` with payload: `reportId`, `confirmedCount`, `ourOnlyCount`, `externalOnlyCount`, `conflictCount`
- [ ] Add `BACKTEST_VALIDATION_COMPLETED: 'backtesting.validation.completed'` to `EVENT_NAMES` in `event-catalog.ts`
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/common/events/backtesting.events.spec.ts`
- [ ] New event tests pass (green phase)

### Test: PredexonMatchingService

**File:** `src/modules/backtesting/validation/predexon-matching.service.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/modules/backtesting/validation/predexon-matching.service.ts` (ConfigService, EventEmitter2 — 2 deps, leaf)
- [ ] Implement `fetchMatchedPairs()`: GET `/v2/matching-markets/pairs`, offset pagination (`limit=100`), lowercase `x-api-key` header, normalize to `ExternalMatchedPair`
- [ ] Implement rate limiting: 72ms minimum interval (14 req/s effective)
- [ ] Implement fetchWithRetry: 3 retries, exponential backoff + jitter, 30s timeout via AbortController
- [ ] Implement 403 graceful degradation: return empty array, log warning, don't throw
- [ ] Implement error handling: `SystemHealthError` code 4202 after retries exhausted
- [ ] Preserve `similarity` as-is (may be `null`)
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/validation/predexon-matching.service.spec.ts`
- [ ] 9 tests pass (green phase)

### Test: OddsPipeService Extension — fetchMatchedPairs

**File:** `src/modules/backtesting/ingestion/oddspipe.service.spec.ts`

**Tasks to make these tests pass:**

- [ ] Add `fetchMatchedPairs(minSpread?: number)` method to existing `oddspipe.service.ts`
- [ ] Call `GET /v1/spreads` with optional `min_spread` param, reuse `fetchWithRateLimit` for auth + rate limiting
- [ ] Normalize spread items to `ExternalMatchedPair`: extract Polymarket/Kalshi identifiers and titles, preserve spread data
- [ ] **CRITICAL**: Verify exact response field names at implementation time via `kindly-web-search` or test API call (OddsPipe docs are Swagger-only)
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/ingestion/oddspipe.service.spec.ts`
- [ ] 5 new + existing tests pass (green phase)

### Test: MatchValidationService

**File:** `src/modules/backtesting/validation/match-validation.service.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/modules/backtesting/validation/match-validation.service.ts` (PrismaService, OddsPipeService, PredexonMatchingService, EventEmitter2 — 4 deps, leaf)
- [ ] Implement `loadOurMatches()`: query `ContractMatch`, build `Map<polymarketContractId>`, `Map<kalshiContractId>`, `Map<compositeKey>` lookups
- [ ] Implement `matchExternalPair(pair, ourMaps)`: ID-based primary, fuzzy title fallback for OddsPipe. Fuzzy matching: lowercase + stop-word removal (reuse PreFilterService STOP_WORDS approach) + bidirectional substring containment with >=60% token overlap threshold (configurable via `VALIDATION_TITLE_MATCH_THRESHOLD`)
- [ ] Implement `runValidation(dto)`: orchestrate load → fetch sources → match → categorize → persist → emit events
- [ ] Implement conflict detection per decision table (10 rows)
- [ ] Implement concurrency guard: `_isRunning` + `try/finally` + 10-min timeout
- [ ] Persist `MatchValidationReport` with summary counts + full `reportData` JSON
- [ ] Emit `BacktestValidationCompletedEvent` on success, `BacktestDataQualityWarningEvent` if conflicts > 0
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/validation/match-validation.service.spec.ts`
- [ ] 22 tests pass (green phase)

### Test: Controller & Module Wiring

**File:** `src/modules/backtesting/controllers/match-validation.controller.spec.ts`

**Tasks to make these tests pass:**

- [ ] Create `src/modules/backtesting/controllers/match-validation.controller.ts`: `POST /api/backtesting/validation/run` (202 + correlationId), `GET /api/backtesting/validation/reports` (paginated list desc), `GET /api/backtesting/validation/reports/:id` (full report)
- [ ] Create `src/modules/backtesting/validation/validation.module.ts` (2 providers: PredexonMatchingService, MatchValidationService; 1 controller: MatchValidationController; imports: IngestionModule)
- [ ] Modify `ingestion.module.ts`: add `OddsPipeService` to `exports` array
- [ ] Modify `backtesting.module.ts`: import `ValidationModule`
- [ ] Add `PREDEXON_API_KEY` to `.env.example` and config
- [ ] Run test: `cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/controllers/match-validation.controller.spec.ts`
- [ ] 5 tests pass (green phase)

---

## Running Tests

```bash
# Run all failing tests for this story (all new should be skipped)
cd pm-arbitrage-engine && pnpm vitest run \
  src/modules/backtesting/types/match-validation.types.spec.ts \
  src/modules/backtesting/dto/match-validation.dto.spec.ts \
  src/common/errors/system-health-error.spec.ts \
  src/common/events/backtesting.events.spec.ts \
  src/modules/backtesting/validation/predexon-matching.service.spec.ts \
  src/modules/backtesting/ingestion/oddspipe.service.spec.ts \
  src/modules/backtesting/validation/match-validation.service.spec.ts \
  src/modules/backtesting/controllers/match-validation.controller.spec.ts

# Run specific test file
cd pm-arbitrage-engine && pnpm vitest run src/modules/backtesting/validation/match-validation.service.spec.ts

# Run tests in watch mode
cd pm-arbitrage-engine && pnpm vitest src/modules/backtesting/

# Run tests with coverage
cd pm-arbitrage-engine && pnpm test:cov
```

---

## Red-Green-Refactor Workflow

### RED Phase (Current)

**TEA Agent Responsibilities:**

- All 55 tests documented and planned for TDD red phase
- Factory helpers defined inline for test data
- Mock requirements documented (fetch, Prisma, ConfigService, EventEmitter2)
- Implementation checklist created per service
- No placeholder assertions

### GREEN Phase (DEV Team — Next Steps)

**DEV Agent Responsibilities:**

1. **Pick one failing test group** from implementation checklist (start with Prisma schema / error codes / types)
2. **Read the test** to understand expected behavior
3. **Implement minimal code** to make that specific test pass
4. **Remove `it.skip()`** → change to `it()`
5. **Run the test** to verify it passes (green)
6. **Check off the task** in implementation checklist
7. **Move to next test** and repeat

**Recommended implementation order:**
1. Prisma schema + migration (MatchValidationReport model needed by service tests)
2. Error codes 4202, 4203 (shared infrastructure)
3. Types: ExternalMatchedPair, ValidationReportEntry, ValidationReportSummary
4. DTOs: TriggerValidationDto, ValidationReportResponseDto
5. Events: BacktestValidationCompletedEvent + catalog entry
6. PredexonMatchingService (new service — API fetching + pagination + auth)
7. OddsPipeService extension (fetchMatchedPairs for /v1/spreads)
8. MatchValidationService (comparison engine — depends on 6 & 7)
9. Controller + module wiring + config

---

## Priority Coverage Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0       | 10    | Core fetching, normalization, ID-based matching, conflict detection (all 4 conflict rows), 403 degradation, report persistence, lookup maps |
| P1       | 45    | Pagination, auth, rate limiting, timeout, retries, error codes, types, DTOs, events, fuzzy matching, all categories, metadata, concurrency, controller, module wiring |
| **Total** | **55** | |

## Acceptance Criteria Coverage

| AC | Description | Tests | Coverage |
|----|-------------|-------|----------|
| #1 | OddsPipe /v1/spreads fetching | 5 | Full (fetch, normalize, identifiers, auth reuse, errors) |
| #2 | Predexon /v2/matching-markets/pairs fetching | 9 | Full (fetch, pagination, auth, rate limit, null similarity, timeout, retry, error, 403 degradation) |
| #3 | Comparison engine (ID-based + fuzzy) | 4 | Full (lookup maps, ID matching, fuzzy fallback, threshold) |
| #4 | Categorization into 4 buckets | 11 | Full (all 10 decision table rows + empty externals edge case) |
| #5 | External-only metadata + KB candidate | 1 | Full (isKnowledgeBaseCandidate=true, all metadata fields) |
| #6 | Conflict disagreement description | 1 | Full (conflictDescription format) |
| #7 | Report persistence + REST API | 6 | Full (persist, POST 202, GET list, GET :id, 409 concurrency, module) |
| #8 | Event emission | 3 | Full (completion event, quality warning on conflicts, no emit on failure) |

---

## Knowledge Base References Applied

- **data-factories.md** — Factory patterns for ExternalMatchedPair, ContractMatch, Predexon/OddsPipe API responses with overrides
- **test-quality.md** — Deterministic tests, explicit assertions with `expect.objectContaining()`, no placeholder assertions, parallel-safe
- **test-levels-framework.md** — Unit for pure logic (type construction, DTO validation, normalization), integration for service+DI tests (API mocking, Prisma, EventEmitter2)
- **test-priorities-matrix.md** — P0 for core matching accuracy/conflict detection/data integrity, P1 for operational concerns (auth, rate limits, pagination, concurrency)
- **test-healing-patterns.md** — Mock patterns for fetch() via vi.stubGlobal, event wiring via expectEventHandled()

---

## Notes

- All tests use `it.skip()` (Vitest convention) for TDD red phase
- No E2E/browser tests — this is a pure backend story
- `vi.stubGlobal('fetch', mockFetch)` used for HTTP mocking (matches existing codebase pattern from stories 10-9-1a/1b)
- `BacktestDataQualityWarningEvent` already exists and is reused for conflict warnings — no new class needed
- Paper/Live mode not applicable — matching validation operates on contract metadata, not trading data
- Factory helpers are inline in spec files — consistent with existing pattern
- OddsPipe response schema must be verified at implementation time (Swagger-only docs — GOTCHA O3)
- Predexon `x-api-key` is **lowercase** — differs from OddsPipe's `X-API-Key` (GOTCHA documented in story)
- PreFilterService STOP_WORDS and matching approach are reused conceptually, not imported — the validation service implements its own simplified version
- Conflict detection tests cover all 10 rows of the decision table from the story, ensuring exhaustive category assignment

---

**Generated by BMad TEA Agent** — 2026-03-27
