# Story 10-9.2: Cross-Platform Pair Matching Validation

Status: done

## Story

As an operator,
I want to cross-reference our contract matching against OddsPipe and Predexon matched pairs,
So that I can validate matching accuracy and identify pairs we may have missed.

## Acceptance Criteria

1. **Given** OddsPipe provides 2,500+ auto-matched Polymarket-Kalshi pairs via `GET /v1/spreads`
   **When** a matching validation job runs
   **Then** OddsPipe matched pairs are fetched with pagination
   **And** each pair is normalized to a common comparison structure (Polymarket identifier + Kalshi identifier + source metadata)

2. **Given** Predexon provides cross-platform matching with 99%+ claimed accuracy via `GET /v2/matching-markets/pairs` (Dev tier, $49/mo)
   **When** a matching validation job runs
   **Then** Predexon matched pairs are fetched with offset-based pagination
   **And** each pair is normalized to the same common comparison structure
   **And** `similarity` field is preserved when non-null (may be `null` for pre-Jan-2025 matches)

3. **Given** our `ContractMatch` records exist in the database
   **When** the comparison engine runs
   **Then** our records are compared against OddsPipe matched pairs
   **And** our records are compared against Predexon matched pairs
   **And** matching uses contract identifiers (Polymarket `condition_id`/`token_id`, Kalshi ticker) as primary keys with fuzzy title fallback for OddsPipe

4. **Given** the comparison is complete
   **When** the validation report is generated
   **Then** it categorizes every pair into exactly one bucket:
   - **Confirmed**: our match AND at least one external source agree on the same pair
   - **Our-only**: we matched but neither external source has the pair
   - **External-only**: at least one external source has the pair but we don't — flagged as knowledge base candidates
   - **Conflict**: sources disagree on which contracts pair together (e.g., our Polymarket A pairs with Kalshi B, but Predexon says Polymarket A pairs with Kalshi C)

5. **Given** external-only matches exist
   **When** the report is generated
   **Then** each external-only entry includes: source(s), Polymarket title/ID, Kalshi title/ID, similarity score (Predexon), spread data (OddsPipe)
   **And** entries are flagged as "candidate for knowledge base" for operator review

6. **Given** conflicts exist
   **When** the report is generated
   **Then** each conflict entry includes: all sources' match details, specific disagreement description, Polymarket and Kalshi identifiers from each source

7. **Given** a validation job completes
   **When** the report is persisted
   **Then** a `MatchValidationReport` record is created with summary counts and full report data as JSON
   **And** the report is queryable via REST API (`GET /api/backtesting/validation/reports`, `GET /api/backtesting/validation/reports/:id`)

8. **Given** validation is running or complete
   **When** events are emitted
   **Then** `BacktestValidationCompletedEvent` fires on completion with summary counts
   **And** `BacktestDataQualityWarningEvent` fires if conflict count > 0

## Tasks / Subtasks

- [x] Task 1: Prisma Schema — MatchValidationReport Model + Migration (AC: #7)
  - [x] 1.1 Add `MatchValidationReport` model: `id` (autoincrement), `correlationId` (String), `runTimestamp` (DateTime), `totalOurMatches` (Int), `totalOddsPipePairs` (Int), `totalPredexonPairs` (Int), `confirmedCount` (Int), `ourOnlyCount` (Int), `externalOnlyCount` (Int), `conflictCount` (Int), `reportData` (Json — array of `ValidationReportEntry`), `durationMs` (Int), `createdAt` (DateTime). Table name `match_validation_reports`. All columns `@map` to snake_case
  - [x] 1.2 Run migration and generate
  - [x] 1.3 Tests: migration verified, baseline tests pass (~3101)

- [x] Task 2: Types, DTOs & Events (AC: #4, #5, #6, #8)
  - [x] 2.1 Create `src/modules/backtesting/types/match-validation.types.ts`:
    - `ExternalMatchedPair`: `polymarketId` (string|null), `kalshiId` (string|null), `polymarketTitle` (string), `kalshiTitle` (string), `source` ('oddspipe'|'predexon'), `similarity` (number|null — preserve null for pre-Jan-2025 Predexon), `spreadData` ({yesDiff: number, polyYesPrice: number, kalshiYesPrice: number}|null)
    - `ValidationReportEntry`: `category` ('confirmed'|'our-only'|'external-only'|'conflict'), `isKnowledgeBaseCandidate` (boolean — true for all external-only entries), `ourMatch?` ({matchId, polymarketContractId, kalshiContractId, polymarketDescription?, kalshiDescription?, confidenceScore?, operatorApproved}), `oddsPipeMatch?` ({polymarketTitle, kalshiTitle, yesDiff?, polyYesPrice?, kalshiYesPrice?}), `predexonMatch?` ({polymarketConditionId, kalshiId, polymarketTitle, kalshiTitle, similarity?}), `conflictDescription?` (string — human-readable disagreement, required for 'conflict' category per AC#6), `notes` (string)
    - `ValidationReportSummary`: counts per category, totals per source, sources queried
  - [x] 2.2 Create `src/modules/backtesting/dto/match-validation.dto.ts`: `TriggerValidationDto` (optional: `includeSources: ('oddspipe' | 'predexon')[]` — default `['oddspipe', 'predexon']` when omitted or empty; validate array values with `@IsIn` decorator, reject unknown source names with 400), `ValidationReportResponseDto` (summary + entries, `reportId` for reference)
  - [x] 2.3 Add error codes to `system-health-error.ts`: `4202` (`BACKTEST_PREDEXON_API_ERROR`), `4203` (`BACKTEST_VALIDATION_FAILURE`)
  - [x] 2.4 Add `BacktestValidationCompletedEvent` to `src/common/events/backtesting.events.ts` (extends BaseEvent, payload: summary counts + reportId). Add event name to `event-catalog.ts`
  - [x] 2.5 Tests: type construction, DTO validation, error construction, event construction

- [x] Task 3: PredexonMatchingService — Fetch Pairs from Predexon API (AC: #2)
  - [x] 3.1 Create `src/modules/backtesting/validation/predexon-matching.service.ts` (ConfigService, EventEmitter2 — 2 deps, leaf)
  - [x] 3.2 Implement `fetchMatchedPairs()`: call `GET /v2/matching-markets/pairs` with offset pagination (`limit=100`). Auth: `x-api-key` header (lowercase) from `PREDEXON_API_KEY` env var. Normalize each pair to `ExternalMatchedPair` structure. Polymarket `condition_id` maps to our `polymarketContractId`. Kalshi identifier maps to our `kalshiContractId`
  - [x] 3.3 Rate limiting: Dev tier 20 req/sec → effective 14 req/sec (70% safety). `minIntervalMs = ceil(1000 / 14) = 72ms`. Same `lastRequestTs + minIntervalMs` pattern
  - [x] 3.4 Handle pagination: loop until `has_more === false` or `pagination.total` reached. Collect all pairs
  - [x] 3.5 Handle `similarity` field: preserve as-is (may be `null` for pre-Jan-2025 matches per Predexon docs)
  - [x] 3.6 Error handling: `SystemHealthError` code 4202. 3 retries with exponential backoff. 30s timeout via `fetchWithTimeout`. **Graceful degradation on 403:** If Predexon returns 403 (free tier / expired key), log warning at `warn` level ("Predexon Dev tier not active — skipping Predexon source"), return empty array (not an error), and continue validation with available sources only. Do NOT throw — a missing Predexon source degrades the report but doesn't block it
  - [x] 3.7 Tests: 8+ tests — pair fetching, pagination, normalization, rate limiting, auth header (lowercase `x-api-key`), timeout, error handling, null similarity

- [x] Task 4: Extend OddsPipeService — Fetch Matched Pairs via Spreads (AC: #1)
  - [x] 4.1 Add `fetchMatchedPairs(minSpread?: number)` method to existing `oddspipe.service.ts`: call `GET /v1/spreads` (with optional `min_spread` param, default 0 to get all pairs). Paginate if API supports it (check response for pagination fields)
  - [x] 4.2 Normalize each spread item to `ExternalMatchedPair`: extract Polymarket and Kalshi identifiers from response objects. Preserve spread data (`yes_diff`, prices) as metadata
  - [x] 4.3 **CRITICAL — Verify response schema at implementation time**: OddsPipe docs are Swagger UI (not statically extractable). Used `kindly-web-search` — confirmed from Reddit post and SDK example: `item["polymarket"]["title"]`, `item["kalshi"]["title"]`, `item["spread"]["yes_diff"]`, `item["polymarket"]["yes_price"]`, `item["kalshi"]["yes_price"]`. OddsPipe does NOT return platform-specific IDs (condition_id, ticker) — fuzzy title matching required
  - [x] 4.4 Reuse existing rate limiting, auth, error handling patterns from `OddsPipeService`
  - [x] 4.5 Tests: 5+ tests — spreads fetching, normalization, pagination, reuse of auth/rate-limit, error handling

- [x] Task 5: MatchValidationService — Core Comparison Engine (AC: #3, #4, #5, #6)
  - [x] 5.1 Create `src/modules/backtesting/validation/match-validation.service.ts` (PrismaService, OddsPipeService, PredexonMatchingService, EventEmitter2 — 4 deps, leaf)
  - [x] 5.2 Implement `loadOurMatches()`: query all `ContractMatch` records. Build lookup maps: `Map<polymarketContractId, ContractMatch>`, `Map<kalshiContractId, ContractMatch>`, `Map<compositeKey, ContractMatch>` where compositeKey = `${polymarketContractId}::${kalshiContractId}`
  - [x] 5.3 Implement `matchExternalPair(pair: ExternalMatchedPair, ourMaps)`: try ID-based matching first (Polymarket condition_id → our `polymarketContractId`, Kalshi ticker → our `kalshiContractId`). For OddsPipe pairs where IDs may not be available: fall back to fuzzy title matching. **Fuzzy matching algorithm** (reuse `PreFilterService` pattern from `src/modules/contract-matching/pre-filter.service.ts`): (1) lowercase both strings, (2) remove stop words using the same STOP_WORDS set from PreFilterService, (3) check bidirectional substring containment — if normalized external title contains normalized our description OR vice versa, consider it a match. Threshold: accept if >=60% of our description's significant tokens appear in the external title. Configurable via `VALIDATION_TITLE_MATCH_THRESHOLD` env var (default 0.6)
  - [x] 5.4 Implement `runValidation(dto: TriggerValidationDto)`: orchestrate full comparison
  - [x] 5.5 Implement conflict detection using the decision table (all 10 rows + OddsPipe title-based conflict detection)
  - [x] 5.6 Concurrency guard: `_isRunning` flag with `try/finally` reset. Return 409 if already running. Add 10-minute timeout (`setTimeout` → set `_isRunning = false` and log error if validation hasn't completed within 600,000ms). Clear timeout on normal completion
  - [x] 5.7 Tests: 24 tests — full comparison with all categories, ID-based matching, fuzzy title fallback, conflict detection (OddsPipe title mismatch + Predexon ID mismatch + external disagree), confirmed with both/single external, our-only, external-only from each source, empty external responses, concurrency guard, event emission with payload verification, no events on failure, persistence

- [x] Task 6: Controller & Module Wiring (AC: #7, #8)
  - [x] 6.1 Create `src/modules/backtesting/controllers/match-validation.controller.ts`: `POST /api/backtesting/validation/run` (triggers validation, returns 202 with correlationId), `GET /api/backtesting/validation/reports` (list reports, ordered by runTimestamp desc, paginated), `GET /api/backtesting/validation/reports/:id` (single report with full data)
  - [x] 6.2 Create `src/modules/backtesting/validation/validation.module.ts` (2 providers: PredexonMatchingService, MatchValidationService; 1 controller: MatchValidationController). Import IngestionModule (to access OddsPipeService — must be exported from IngestionModule)
  - [x] 6.3 Modify `ingestion.module.ts`: add `OddsPipeService` to `exports` array so ValidationModule can inject it
  - [x] 6.4 Modify `backtesting.module.ts`: import ValidationModule
  - [x] 6.5 Add `PREDEXON_API_KEY` and `PREDEXON_BASE_URL` to `.env.example`
  - [x] 6.6 Tests: 5 tests — trigger returns 202, reports list returns paginated results, single report returns full data, 409 when already running, module DI compiles with all services

## Dev Notes

### Design Document Reference

**Authoritative source:** `_bmad-output/implementation-artifacts/10-9-0-design-doc.md` — ALL technical decisions for this story are defined there. When in doubt, the design doc overrides this story file.

Key sections:

- Section 1.5 (OddsPipe): endpoints, rate limits, gotchas O1-O5 — 30-day history limit, very new service, fuzzy matching accuracy
- Section 1.6 (Predexon): endpoints, Dev tier requirement ($49/mo), rate limits, gotchas D1-D5 — LLM-based matching, timestamp inconsistency
- Section 2.7 (Ingestion Scope): target list = ContractMatch union, third-party pair merging concept
- Section 6.5 (Story Sizing): 6 tasks, 2 integration boundaries — within limits
- Section 7.2 (Deferral Assessment): elevated importance — third-party pair accuracy affects ingestion targeting
- Section 8.5 (Error Codes): 4202-4205 reserved for this and later stories

### Critical Implementation Notes

**Predexon API — `GET /v2/matching-markets/pairs` (MANDATORY: Dev tier $49/mo):**

- Base URL: `https://api.predexon.com`
- Auth: `x-api-key` header (**lowercase** — differs from OddsPipe's `X-API-Key`)
- Response: paginated list of exact-matched pairs (similarity >= 95). Each pair includes Polymarket `condition_id` and Kalshi market identifiers
- Rate limit: Dev tier 20 req/sec, 1M req/month
- `match_type` parameter removed in v2 — all pairs are exact matches
- `similarity` field may be `null` for matches created before January 4, 2025 (Predexon docs)
- Pagination: offset-based (`limit`, `offset`, `pagination.total`, `pagination.has_more`)
- **GOTCHA (D1):** Timestamp inconsistency — candlesticks use seconds, orderbooks use milliseconds. For the matching endpoint this is not relevant but be aware when parsing any timestamps in the response
- **GOTCHA (D5):** LLM-based matching means a small % may be incorrect. This is EXPECTED — the whole point of this story is to detect such discrepancies

**Predexon Changelog (as of 2026-03-27):**

- v2 launched 2026-02-04 with 14 new endpoints
- March 15, 2026: Kalshi orderbook data gap (March 12-14 UTC) due to upstream format change
- `token_id` removed from `/v2/polymarket/markets` in v2 — use `condition_id` instead
- Matching endpoints are gated (Dev+, $49/mo). Free tier returns 403

**OddsPipe API — `GET /v1/spreads` (Free tier):**

- Base URL: `https://oddspipe.com/v1`
- Auth: `X-API-Key` header (uppercase `X-API-Key`)
- Response: `{ "items": [{ "polymarket": { "title", "yes_price", ... }, "kalshi": { "title", "yes_price", ... }, "spread": { "yes_diff" } }] }`
- Optional params: `min_spread` (decimal, e.g., 0.03 for 3%), `min_match` (match quality cutoff %)
- Rate limit: Free tier 100 req/min → effective 70 req/min (70% safety)
- 2,500+ auto-matched pairs using fuzzy title matching with post-validation rules
- **CRITICAL — Verify exact response schema**: OddsPipe Swagger docs at `oddspipe.com/docs` need direct inspection. The Python SDK example shows the structure above, but exact field names for platform identifiers (market ID, slug, condition_id, token_id, ticker) must be verified at implementation time via `kindly-web-search` against the Swagger spec or by making a test call. If OddsPipe does NOT return platform-specific IDs (only titles), use fuzzy title matching against our `ContractMatch` descriptions
- **GOTCHA (O3):** OddsPipe is very new (~3 weeks since Reddit launch). Light integration — don't build critical dependencies
- **GOTCHA (O5):** Fuzzy matching accuracy unverified at scale. Cross-validate against Predexon and our data (that's what this story does)

**Matching Strategy:**

1. **Predexon → our ContractMatch (ID-based):**
   - Match on `pair.polymarket_condition_id === contractMatch.polymarketContractId`
   - AND verify Kalshi identifier matches `contractMatch.kalshiContractId`
   - Direct, reliable — Predexon returns typed IDs

2. **OddsPipe → our ContractMatch (ID-based with title fallback):**
   - First attempt: match by platform IDs if OddsPipe provides them
   - Fallback: normalized title matching — lowercase + stop-word removal, check if OddsPipe title contains or is contained by our description. Threshold: 0.6 substring similarity
   - Log unmatched OddsPipe pairs at `warn` level for operator visibility

3. **Cross-source conflict detection:**
   - Key each pair by Polymarket contract ID (the more unique identifier)
   - If two sources map the same Polymarket contract to different Kalshi contracts → conflict
   - If two sources map the same Kalshi contract to different Polymarket contracts → conflict

**CorrelationId:** Generate via `crypto.randomUUID()` at job start. Pass through to all events, log entries, and persist in `MatchValidationReport.correlationId`. Controller returns it in the 202 response.

**Event Emission:** Emit `BacktestValidationCompletedEvent` and `BacktestDataQualityWarningEvent` (if conflicts > 0) ONLY after successful DB commit. Do NOT emit on failure — the orchestrator's `try/finally` ensures events fire only in the success path.

**Knowledge Base Candidate Flagging:** ALL external-only entries have `isKnowledgeBaseCandidate = true`. This is a simple rule — no additional criteria. The operator reviews and decides whether to add to ContractMatch.

**Report Retention:** No cleanup policy for MVP. Validation reports are low-volume (operator-triggered, not cron). Add retention policy in Story 10-9-6 if needed.

**HTTP Client:** Use native `fetch()`. Follow existing patterns from `oddspipe.service.ts` and `kalshi-historical.service.ts`. Use `fetchWithTimeout` (AbortController + 30s timeout).

**Batch Sizing / Rate Limiting:** Predexon pagination: `limit=100` per page. OddsPipe: check if `/v1/spreads` supports pagination — if not, a single call may return all 2,500+ pairs (acceptable for free tier).

### Paper/Live Mode Boundary

Not applicable. Matching validation operates on contract metadata, not on trading data. The `MatchValidationReport` table does NOT have an `is_paper` column.

### File Size Constraints

All services have focused responsibilities:

- `PredexonMatchingService`: ~150 lines (2 methods: fetchMatchedPairs, fetchWithRetry)
- `OddsPipeService` additions: ~60 lines (1 new method: fetchMatchedPairs)
- `MatchValidationService`: ~250 lines (5 methods: loadOurMatches, matchExternalPair, runValidation, detectConflicts, buildReport)
- `MatchValidationController`: ~80 lines (3 endpoints)

All within 300-line service / 400-logical-line file limits.

### Existing Code to Reuse — DO NOT REIMPLEMENT

| What                              | Where                                                                 | Usage                                                    |
| --------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------- |
| `OddsPipeService`                 | `src/modules/backtesting/ingestion/oddspipe.service.ts`               | Extend with `fetchMatchedPairs()`. Reuse auth, rate-limit, error handling |
| `PlatformId` enum                 | `src/common/types/platform.type.ts`                                   | Platform identification                                  |
| `BaseEvent` class                 | `src/common/events/base.event.ts`                                     | Event base class with correlationId                      |
| `SystemHealthError` class         | `src/common/errors/system-health-error.ts`                            | Error base for codes 4202, 4203                          |
| `SYSTEM_HEALTH_ERROR_CODES`       | same file                                                             | Add new codes here                                       |
| `EVENT_NAMES` catalog             | `src/common/events/event-catalog.ts`                                  | Add `BACKTEST_VALIDATION_COMPLETED` event name           |
| `BacktestDataQualityWarningEvent` | `src/common/events/backtesting.events.ts`                             | Reuse for conflict warnings                              |
| `PrismaService`                   | `src/persistence/prisma.service.ts`                                   | Database access                                          |
| `ContractMatch` model             | `prisma/schema.prisma`                                                | Our matching data (polymarketContractId, kalshiContractId, descriptions, operatorApproved) |
| `MatchId` branded type            | `src/common/types/branded.type.ts`                                    | Type-safe match IDs                                      |
| `expectEventHandled()`            | `src/common/testing/expect-event-handled.ts`                          | Event wiring verification                                |
| native `fetch()`                  | Node.js built-in                                                      | HTTP client for both APIs                                |
| `fetchWithTimeout` pattern        | `src/modules/backtesting/ingestion/polymarket-historical.service.ts`  | AbortController + 30s timeout                            |
| `fetchWithRetry` pattern          | `src/modules/backtesting/ingestion/kalshi-historical.service.ts`      | 3 retries with exponential backoff + jitter              |

### Patterns from Stories 10-9-1a/1b — Follow Exactly

| Pattern                | Implementation Reference                                                                                             |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Rate limiting**      | `lastRequestTs + minIntervalMs` (oddspipe.service.ts, kalshi-historical.service.ts)                                  |
| **Error handling**     | `fetchWithRetry()` — 3 max retries, exponential backoff + jitter, throws `SystemHealthError`                         |
| **Timeout protection** | `fetchWithTimeout()` — AbortController + 30s                                                                         |
| **Event emission**     | Orchestrator emits domain events per story patterns (ingestion-orchestrator.service.ts)                              |
| **Concurrency guard**  | `_isRunning` flag with `try/finally` (ingestion-orchestrator.service.ts:33-37)                                       |
| **Structured logging** | correlationId, per-source milestones                                                                                 |
| **Controller 202**     | Trigger returns 202 with correlationId, runs async (historical-data.controller.ts)                                   |

### What This Story Does NOT Include

- **Auto-importing external pairs into ContractMatch** — flagging only; operator review is manual
- **Predexon free endpoint data ingestion** (candlesticks, trades, orderbooks) — future story or extend 10-9-1a
- **OddsPipe OHLCV ingestion** — already done in story 10-9-1b
- **Dashboard UI for validation reports** — Story 10-9-5
- **Scheduled/cron-based validation** — Story 10-9-6 or future work
- **Fuzzy title matching library** — use simple normalized substring matching, NOT NLP. The contract-matching module's `PreFilterService` uses stop-word removal + substring matching — reuse that approach
- **Error codes 4204-4205** — reserved for later stories
- **Monthly partitioning** — not applicable (validation reports are low-volume, not time-series)

### Constructor Dependency Summary

| Service                     | Dependencies                                                       | Count | Type |
| --------------------------- | ------------------------------------------------------------------ | ----- | ---- |
| `PredexonMatchingService`   | ConfigService, EventEmitter2                                       | 2     | Leaf |
| `OddsPipeService` (existing)| PrismaService, ConfigService, EventEmitter2                        | 3     | Leaf |
| `MatchValidationService`    | PrismaService, OddsPipeService, PredexonMatchingService, EventEmitter2 | 4 | Leaf |
| `MatchValidationController` | MatchValidationService                                             | 1     | —    |

All within limits (leaf <=5).

### Module Provider Summary

| Module             | Providers                                               | Count | Status           |
| ------------------ | ------------------------------------------------------- | ----- | ---------------- |
| `ValidationModule` | PredexonMatchingService, MatchValidationService         | 2     | Within <=8 limit |
| `IngestionModule`  | (unchanged: 6 providers, now exports OddsPipeService)   | 6     | Within <=8 limit |

### Project Structure Notes

```
pm-arbitrage-engine/
├── prisma/schema.prisma                                    # MODIFY: Add MatchValidationReport model
├── src/
│   ├── common/
│   │   ├── errors/system-health-error.ts                   # MODIFY: add codes 4202, 4203
│   │   ├── errors/system-health-error.spec.ts              # MODIFY: unskip new error tests
│   │   └── events/
│   │       ├── backtesting.events.ts                       # MODIFY: add BacktestValidationCompletedEvent
│   │       ├── backtesting.events.spec.ts                  # MODIFY: add event construction tests
│   │       └── event-catalog.ts                            # MODIFY: add validation event names
│   ├── modules/backtesting/
│   │   ├── types/
│   │   │   └── match-validation.types.ts                   # NEW: ExternalMatchedPair, ValidationReportEntry, ValidationReportSummary
│   │   ├── dto/
│   │   │   └── match-validation.dto.ts                     # NEW: TriggerValidationDto, ValidationReportResponseDto
│   │   ├── validation/
│   │   │   ├── validation.module.ts                        # NEW: ValidationModule
│   │   │   ├── predexon-matching.service.ts                # NEW
│   │   │   ├── predexon-matching.service.spec.ts           # NEW
│   │   │   ├── match-validation.service.ts                 # NEW
│   │   │   └── match-validation.service.spec.ts            # NEW
│   │   ├── ingestion/
│   │   │   ├── oddspipe.service.ts                         # MODIFY: add fetchMatchedPairs()
│   │   │   ├── oddspipe.service.spec.ts                    # MODIFY: add matched pairs tests
│   │   │   └── ingestion.module.ts                         # MODIFY: export OddsPipeService
│   │   ├── controllers/
│   │   │   ├── match-validation.controller.ts              # NEW
│   │   │   └── match-validation.controller.spec.ts         # NEW
│   │   └── backtesting.module.ts                           # MODIFY: import ValidationModule
├── .env.example                                             # MODIFY: add PREDEXON_API_KEY
```

### Reviewer Context Template (for Lad MCP code_review)

```
## Module: Backtesting & Calibration — Story 10-9-2 (Cross-Platform Pair Matching Validation)

### Architecture
- New sub-module: src/modules/backtesting/validation/
- 2 new services: PredexonMatchingService (Predexon API), MatchValidationService (comparison engine)
- 1 extended service: OddsPipeService (add fetchMatchedPairs for /v1/spreads)
- 1 new controller: MatchValidationController (POST /run, GET /reports, GET /reports/:id)
- 1 new Prisma model: MatchValidationReport
- Imports OddsPipeService from IngestionModule via module exports

### Hard Constraints
- Predexon auth: lowercase `x-api-key` header (NOT `X-API-Key`)
- OddsPipe auth: `X-API-Key` header (uppercase)
- ALL errors extend SystemHealthError (codes 4202, 4203)
- Rate limits: Predexon 14 req/s effective, OddsPipe 70 req/min effective
- HTTP: native fetch() only — no axios/got
- Matching: ID-based primary, fuzzy title fallback for OddsPipe only
- Concurrency: _isRunning guard on validation service

### Testing Requirements
- Co-located specs, Vitest
- Assertion depth: verify payloads with expect.objectContaining
- Event wiring: expectEventHandled() for @OnEvent handlers
- Mock fetch() via vi.stubGlobal
- Test all 4 report categories with realistic data

### Acceptance Criteria
[SEE STORY ACs #1-#8 ABOVE]
```

### References

- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md] — Authoritative design document
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md#Section 1.5] — OddsPipe API, gotchas O1-O5
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md#Section 1.6] — Predexon API, gotchas D1-D5
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md#Section 2.7] — Ingestion scope, third-party pair merging
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md#Section 6.5] — Story sizing: 6 tasks, 2 integration boundaries
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md#Section 7.2] — Deferral assessment: elevated importance
- [Source: _bmad-output/implementation-artifacts/10-9-0-design-doc.md#Section 8.5] — Error codes 4202-4205 reserved
- [Source: _bmad-output/planning-artifacts/epics.md#Story 10-9-2] — Epic definition and ACs
- [Source: _bmad-output/implementation-artifacts/10-9-1a-platform-api-price-trade-ingestion.md] — Previous story patterns, code review fixes
- [Source: _bmad-output/implementation-artifacts/10-9-1b-depth-data-third-party-ingestion.md] — Previous story patterns, OddsPipe service implementation
- [Source: pm-arbitrage-engine/src/modules/backtesting/ingestion/oddspipe.service.ts] — Existing OddsPipe service to extend
- [Source: pm-arbitrage-engine/src/modules/contract-matching/] — Contract matching module (ContractMatch model, descriptions, confidence scores)
- [Source: pm-arbitrage-engine/prisma/schema.prisma] — ContractMatch model, HistoricalDataSource enum (PREDEXON already reserved)
- [Source: pm-arbitrage-engine/src/common/errors/system-health-error.ts] — Error codes 4200-4201, 4206-4209 taken; 4202-4203 available
- [Source: pm-arbitrage-engine/src/common/events/backtesting.events.ts] — Existing backtesting events
- [Source: pm-arbitrage-engine/src/modules/contract-matching/pre-filter.service.ts] — Stop-word removal + substring matching pattern (reuse approach for fuzzy title matching)
- [Source: https://docs.predexon.com/concepts/matching] — Predexon cross-platform matching docs: similarity scores, match types, endpoint descriptions
- [Source: https://docs.predexon.com/api-reference/introduction] — Predexon API reference: rate limits, pagination, auth, response format
- [Source: https://docs.predexon.com/changelog] — Predexon changelog: v2 breaking changes (match_type removed, cursor pagination)
- [Source: https://www.reddit.com/r/Kalshi/comments/1rnu6oe/] — OddsPipe launch post: spreads endpoint, 2500+ pairs, fuzzy matching description

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Task 1: Prisma schema — MatchValidationReport model added, migration created, 3101 baseline tests pass
- Task 2: Types (ExternalMatchedPair, ValidationReportEntry, ValidationReportSummary), DTOs (TriggerValidationDto with @IsIn validation), error codes (4202, 4203), event (BacktestValidationCompletedEvent + catalog entry) — 25 tests
- Task 3: PredexonMatchingService — offset pagination, lowercase x-api-key auth, 72ms rate limiting, 403 graceful degradation, null similarity preservation — 9 tests
- Task 4: OddsPipeService extension — fetchMatchedPairs() for /v1/spreads endpoint. Verified via kindly-web-search: OddsPipe does NOT return platform IDs (condition_id, ticker), only titles. Normalized to ExternalMatchedPair with polymarketId/kalshiId = null — 5 new tests (17 total)
- Task 5: MatchValidationService — core comparison engine with ID-based + fuzzy title matching, all 10 decision table rows, concurrency guard with 10-min safety timeout, event emission (completion + quality warning), report persistence — 24 tests
- Task 6: Controller (POST /run 202, GET /reports, GET /reports/:id), ValidationModule, IngestionModule OddsPipeService export, BacktestingModule import, .env.example PREDEXON vars — 5 tests
- Final: 3156 tests pass (55 new), 200 test files, zero regressions, lint clean for new files
- Code Review (3-layer adversarial): Blind Hunter + Edge Case Hunter + Acceptance Auditor. 69 raw findings → 44 unique after dedup → 0 intent-gap, 1 bad-spec (spec table OddsPipeService deps count), 20 patch, 10 defer, 13 rejected. All 20 patch items fixed:
  - **P0 fixes (4):** Controller correlationId now passed to service (was generating separate IDs); cross-external conflict detection implemented (decision table row 10 — title-only and ID-based cross-source comparison); ValidationReportResponseDto added; `getEffectiveSources()` extracted as standalone function (class method would crash at runtime without `transform:true`)
  - **P1 fixes (9):** `fetchWithRetry` refactored to generic `fetchJsonWithRetry<T>` (type-safe); `getReports()` now paginated with `take`/`skip`; `VALIDATION_TITLE_MATCH_THRESHOLD` env var support via ConfigService; warn-level logging for unmatched OddsPipe pairs; `ConflictException`/`NotFoundException` replaced with SystemHealthError hierarchy; duplicate ContractMatch ID warnings in `buildLookupMaps`; Predexon MAX_PAGES (100) pagination guard + empty data break; Predexon response shape validation (data array + pagination object); OddsPipe /spreads response shape validation (items array + sub-object checks)
  - **P2 fixes (7):** ParseIntPipe on `:id` param; safety timeout test with `vi.useFakeTimers` + `advanceTimersByTimeAsync(600_001)`; "yes"/"no" removed from stop words (semantically meaningful in prediction markets); null byte key separator (prevents `::` collision); external-only entry metadata verified with `expect.objectContaining` per AC#5; conflict description verified to contain specific identifiers per AC#6; 404 path tested for `getReport`
- Post-review: 3167 tests pass (11 new from review fixes), 200 test files, zero regressions

### File List

**New files:**
- `prisma/migrations/20260327023301_add_match_validation_report/migration.sql`
- `src/modules/backtesting/types/match-validation.types.ts`
- `src/modules/backtesting/types/match-validation.types.spec.ts`
- `src/modules/backtesting/dto/match-validation.dto.ts`
- `src/modules/backtesting/dto/match-validation.dto.spec.ts`
- `src/modules/backtesting/validation/predexon-matching.service.ts`
- `src/modules/backtesting/validation/predexon-matching.service.spec.ts`
- `src/modules/backtesting/validation/match-validation.service.ts`
- `src/modules/backtesting/validation/match-validation.service.spec.ts`
- `src/modules/backtesting/validation/validation.module.ts`
- `src/modules/backtesting/controllers/match-validation.controller.ts`
- `src/modules/backtesting/controllers/match-validation.controller.spec.ts`

**Modified files:**
- `prisma/schema.prisma` — Added MatchValidationReport model
- `src/common/errors/system-health-error.ts` — Added codes 4202, 4203
- `src/common/errors/system-health-error.spec.ts` — Added 2 error code tests
- `src/common/events/backtesting.events.ts` — Added BacktestValidationCompletedEvent
- `src/common/events/backtesting.events.spec.ts` — Added event construction + catalog tests
- `src/common/events/event-catalog.ts` — Added BACKTEST_VALIDATION_COMPLETED
- `src/modules/backtesting/ingestion/oddspipe.service.ts` — Added fetchMatchedPairs() method
- `src/modules/backtesting/ingestion/oddspipe.service.spec.ts` — Added 5 fetchMatchedPairs tests
- `src/modules/backtesting/ingestion/ingestion.module.ts` — Exported OddsPipeService
- `src/modules/backtesting/backtesting.module.ts` — Imported ValidationModule
- `.env.example` — Added PREDEXON_API_KEY, PREDEXON_BASE_URL
