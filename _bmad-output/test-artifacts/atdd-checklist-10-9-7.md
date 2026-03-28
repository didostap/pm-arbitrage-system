---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-28'
workflowType: 'testarch-atdd'
inputDocuments:
  - '_bmad-output/implementation-artifacts/10-9-7-external-pair-candidate-ingestion.md'
  - '_bmad/tea/testarch/knowledge/data-factories.md'
  - '_bmad/tea/testarch/knowledge/test-quality.md'
  - '_bmad/tea/testarch/knowledge/test-levels-framework.md'
  - '_bmad/tea/testarch/knowledge/test-priorities-matrix.md'
  - '_bmad/tea/testarch/knowledge/test-healing-patterns.md'
---

# ATDD Checklist — Story 10-9.7: External Pair Candidate Ingestion

**Date:** 2026-03-28
**Author:** Arbi
**Primary Test Level:** Unit (Vitest) + Integration (event wiring) + Component (React Testing Library)
**Repos:** `pm-arbitrage-engine/` (primary), `pm-arbitrage-dashboard/` (frontend)

---

## Story Summary

**As an** operator
**I want** the discovery pipeline to proactively import matched pairs from OddsPipe and Predexon as LLM scoring candidates
**So that** the system discovers arbitrage opportunities beyond what catalog brute-force finds, substantially expanding the tradeable pair universe

---

## Acceptance Criteria

1. `IExternalPairProvider` interface defined in `common/interfaces/` with `fetchPairs()` and `getSourceId()`, DI tokens exported
2. `OddsPipeService` implements `IExternalPairProvider`, delegates to existing `fetchMatchedPairs()`
3. `PredexonMatchingService` implements `IExternalPairProvider`, delegates to existing `fetchMatchedPairs()`
4. External pairs checked for duplicates against existing `ContractMatch` records before scoring
5. Predexon dedup uses deterministic composite key matching (exact match only)
6. OddsPipe dedup uses composite key first, falls back to fuzzy title matching with conservative threshold
7. Novel pairs scored through `ConfidenceScorerService` via `IScoringStrategy` interface
8. Scored pairs persisted as `ContractMatch` with `origin` field set to `PREDEXON` or `ODDSPIPE`
9. Auto-approve/review/reject events emitted following existing patterns
10. Configurable cron schedule with concurrency guard (no overlap with self or `CandidateDiscoveryService`)
11. Dashboard origin badge and filter on matches table
12. Graceful degradation — single provider outage does not fail entire run
13. Same auto-approve/review/reject thresholds as existing discovery pipeline
14. Direction validation skipped for external pairs (lack outcome metadata), `divergenceNotes` records skip reason
15. Per-source stats emitted via `ExternalPairIngestionRunCompletedEvent`
16. No behavior changes in existing `CandidateDiscoveryService`

---

## Test Strategy

| Level | Scope | Framework | Location |
|-------|-------|-----------|----------|
| Unit | Service logic, config, DTOs, event classes, dedup algorithms, scoring delegation | Vitest + vi.fn() mocks | `pm-arbitrage-engine/src/**/*.spec.ts` |
| Integration | Event wiring (@OnEvent → handler), module registration | Vitest + expectEventHandled() | `pm-arbitrage-engine/src/common/testing/event-wiring-audit.spec.ts` |
| Component | Frontend origin badge rendering, filter behavior | Vitest + @testing-library/react | `pm-arbitrage-dashboard/src/**/*.spec.tsx` |

**Priority rationale:**
- P0: Data integrity (deduplication correctness, scoring delegation, origin persistence, concurrency guards, event emission)
- P1: Operational visibility (dashboard origin, event payloads, config wiring, error isolation)
- P2: Edge cases (ID-less pairs, P2002 race condition, cluster classification failure, all-providers-failed)
- P3: Low-risk cosmetic (frontend loading/error states)

---

## Failing Tests Created (RED Phase)

### Task 1: IExternalPairProvider Interface + MatchOrigin Schema Migration (8 tests)

**File:** `pm-arbitrage-engine/src/common/interfaces/external-pair-provider.interface.spec.ts` (NEW, ~50 lines)
**File:** `pm-arbitrage-engine/src/modules/contract-matching/contract-match-sync.service.spec.ts` (MODIFIED, +2 tests)

**Interface + DI tokens — 3 tests:**

- [ ] **Test:** [P0] `IExternalPairProvider` interface should define `fetchPairs(): Promise<ExternalMatchedPair[]>` and `getSourceId(): string` (type-level verification via mock implementation)
  - **Status:** RED — interface does not exist in `common/interfaces/`
  - **Verifies:** AC #1
  - **Assert:** mock object satisfying interface compiles and has both methods

- [ ] **Test:** [P0] `ODDSPIPE_PAIR_PROVIDER_TOKEN` and `PREDEXON_PAIR_PROVIDER_TOKEN` should be exported from `common/interfaces/index.ts`
  - **Status:** RED — tokens not defined
  - **Verifies:** AC #1
  - **Assert:** import resolves, tokens are unique Symbol/string values

- [ ] **Test:** [P1] DI tokens should follow `IContractCatalogProvider` multi-token pattern (string token format)
  - **Status:** RED — tokens not defined
  - **Verifies:** AC #1 — consistency with existing token pattern
  - **Assert:** tokens are strings matching `'ODDSPIPE_PAIR_PROVIDER'` / `'PREDEXON_PAIR_PROVIDER'`

**MatchOrigin enum + origin field — 3 tests:**

- [ ] **Test:** [P0] `MatchOrigin` enum should contain `DISCOVERY`, `PREDEXON`, `ODDSPIPE`, `MANUAL` values
  - **Status:** RED — enum not defined in Prisma schema
  - **Verifies:** AC #8
  - **Assert:** after `prisma generate`, enum values accessible from Prisma client

- [ ] **Test:** [P0] `ContractMatch.origin` field should default to `DISCOVERY`
  - **Status:** RED — field not in schema
  - **Verifies:** AC #8 — existing records retain DISCOVERY origin
  - **Assert:** Prisma mock shape includes `origin` with default `DISCOVERY`

- [ ] **Test:** [P1] `ContractMatch` should have `@@index([origin])` for dashboard filtering performance
  - **Status:** RED — index not defined
  - **Verifies:** AC #11 — index supports filtered queries

**ContractMatchSyncService origin update — 2 tests:**

- [ ] **Test:** [P0] `syncPairsToDatabase()` should set `origin: MatchOrigin.MANUAL` on upsert for YAML-sourced pairs
  - **Status:** RED — origin field not set in sync service
  - **Verifies:** AC #8 — YAML pairs tagged as MANUAL going forward
  - **Assert:** `prisma.contractMatch.upsert` called with `expect.objectContaining({ create: expect.objectContaining({ origin: 'MANUAL' }), update: expect.objectContaining({ origin: 'MANUAL' }) })`

- [ ] **Test:** [P1] Backfill: existing records with `operatorApproved = true AND operatorRationale IS NULL` should be updated to `origin: MANUAL`
  - **Status:** RED — backfill migration not created
  - **Verifies:** AC #8 — correct historical data

---

### Task 2: Config — Cron Expression + Enabled Flag + Dedup Threshold (8 tests)

**File:** `pm-arbitrage-engine/src/common/config/env.schema.spec.ts` (MODIFIED, +4 tests)
**File:** `pm-arbitrage-engine/src/common/config/config-defaults.spec.ts` (MODIFIED, +4 tests)

**env.schema.ts — 4 tests:**

- [ ] **Test:** [P1] `EXTERNAL_PAIR_INGESTION_CRON_EXPRESSION` defaults to `'0 0 6,18 * * *'`
  - **Status:** RED — env var not defined in env.schema.ts
  - **Verifies:** AC #10 — configurable cron schedule, default twice daily

- [ ] **Test:** [P1] `EXTERNAL_PAIR_INGESTION_ENABLED` defaults to `true`
  - **Status:** RED — env var not defined
  - **Verifies:** AC #10 — enabled by default

- [ ] **Test:** [P1] `EXTERNAL_PAIR_DEDUP_TITLE_THRESHOLD` defaults to `0.45`
  - **Status:** RED — env var not defined
  - **Verifies:** AC #6 — conservative fuzzy match threshold for OddsPipe dedup

- [ ] **Test:** [P1] `EXTERNAL_PAIR_LLM_CONCURRENCY` defaults to `5`
  - **Status:** RED — env var not defined
  - **Verifies:** AC #7 — lower concurrency than discovery (pre-vetted, smaller batches)

**config-defaults.ts — 4 tests:**

- [ ] **Test:** [P1] config-defaults maps `externalPairIngestionCronExpression` to `EXTERNAL_PAIR_INGESTION_CRON_EXPRESSION`
  - **Status:** RED — config entry not defined
  - **Verifies:** AC #10

- [ ] **Test:** [P1] config-defaults maps `externalPairIngestionEnabled` to `EXTERNAL_PAIR_INGESTION_ENABLED`
  - **Status:** RED — config entry not defined
  - **Verifies:** AC #10

- [ ] **Test:** [P1] config-defaults maps `externalPairDedupTitleThreshold` to `EXTERNAL_PAIR_DEDUP_TITLE_THRESHOLD`
  - **Status:** RED — config entry not defined
  - **Verifies:** AC #6

- [ ] **Test:** [P1] config-defaults maps `externalPairLlmConcurrency` to `EXTERNAL_PAIR_LLM_CONCURRENCY`
  - **Status:** RED — config entry not defined
  - **Verifies:** AC #7

---

### Task 3: OddsPipe + Predexon Implement IExternalPairProvider (6 tests)

**File:** `pm-arbitrage-engine/src/modules/backtesting/ingestion/oddspipe.service.spec.ts` (MODIFIED, +3 tests)
**File:** `pm-arbitrage-engine/src/modules/backtesting/validation/predexon-matching.service.spec.ts` (MODIFIED, +3 tests)

**PredexonMatchingService adapter — 3 tests:**

- [ ] **Test:** [P0] `fetchPairs()` should delegate to existing `fetchMatchedPairs()` and return `ExternalMatchedPair[]`
  - **Status:** RED — `fetchPairs()` method does not exist on PredexonMatchingService
  - **Verifies:** AC #3
  - **Assert:** `fetchPairs()` calls `fetchMatchedPairs()` exactly once, returns same array

- [ ] **Test:** [P0] `getSourceId()` should return `'predexon'`
  - **Status:** RED — `getSourceId()` method does not exist
  - **Verifies:** AC #3
  - **Assert:** `service.getSourceId()` === `'predexon'`

- [ ] **Test:** [P1] `fetchPairs()` should propagate errors from `fetchMatchedPairs()` without adding retry layer
  - **Status:** RED — method does not exist
  - **Verifies:** AC #12 — existing retry logic in fetchMatchedPairs() handles retries; no second layer
  - **Assert:** when `fetchMatchedPairs()` rejects, `fetchPairs()` rejects with same error

**OddsPipeService adapter — 3 tests:**

- [ ] **Test:** [P0] `fetchPairs()` should delegate to existing `fetchMatchedPairs()` and return `ExternalMatchedPair[]`
  - **Status:** RED — `fetchPairs()` method does not exist on OddsPipeService
  - **Verifies:** AC #2
  - **Assert:** `fetchPairs()` calls `fetchMatchedPairs()` exactly once, returns same array

- [ ] **Test:** [P0] `getSourceId()` should return `'oddspipe'`
  - **Status:** RED — `getSourceId()` method does not exist
  - **Verifies:** AC #2
  - **Assert:** `service.getSourceId()` === `'oddspipe'`

- [ ] **Test:** [P1] `fetchPairs()` should propagate errors from `fetchMatchedPairs()` without adding retry layer
  - **Status:** RED — method does not exist
  - **Verifies:** AC #12 — no double-retry
  - **Assert:** when `fetchMatchedPairs()` rejects, `fetchPairs()` rejects with same error

---

### Task 4: ExternalPairIngestionService — Coordinator + Scheduling (11 tests)

**File:** `pm-arbitrage-engine/src/modules/contract-matching/external-pair-ingestion.service.spec.ts` (NEW, ~300 lines)

**Cron + enabled flag — 3 tests:**

- [ ] **Test:** [P0] `handleCron()` should return immediately when `EXTERNAL_PAIR_INGESTION_ENABLED` is not `true` (use `enabled !== true` pattern)
  - **Status:** RED — ExternalPairIngestionService does not exist
  - **Verifies:** AC #10 — configurable enabled flag
  - **Assert:** `runExternalPairIngestion` NOT called, no events emitted

- [ ] **Test:** [P0] `handleCron()` should call `runExternalPairIngestion()` when enabled and no concurrency conflict
  - **Status:** RED — service does not exist
  - **Verifies:** AC #10 — cron triggers ingestion run
  - **Assert:** `runExternalPairIngestion` called once

- [ ] **Test:** [P1] cron registered via `SchedulerRegistry` in `onModuleInit()` with configurable expression from config
  - **Status:** RED — service does not exist
  - **Verifies:** AC #10 — follows CandidateDiscoveryService pattern with runtime reload support
  - **Assert:** `schedulerRegistry.addCronJob` called with cron expression from config

**Concurrency guard — 3 tests:**

- [ ] **Test:** [P0] `handleCron()` should skip when own `_isRunning` flag is true
  - **Status:** RED — service does not exist
  - **Verifies:** AC #10 — no concurrent external pair ingestion runs
  - **Assert:** `runExternalPairIngestion` NOT called, debug-level log emitted

- [ ] **Test:** [P0] `handleCron()` should skip when `CandidateDiscoveryService.isRunning` is true
  - **Status:** RED — service does not exist, `isRunning` getter not public on CandidateDiscoveryService
  - **Verifies:** AC #10, #16 — no overlap with catalog discovery (prevents rate limit contention)
  - **Assert:** `runExternalPairIngestion` NOT called

- [ ] **Test:** [P1] `_isRunning` flag should be reset to false after `runExternalPairIngestion()` completes (even on error)
  - **Status:** RED — service does not exist
  - **Verifies:** AC #10 — flag cleanup prevents permanent lockout
  - **Assert:** after `ExternalPairProcessorService.processAllProviders()` throws, flag is false

**Run completion + stats — 3 tests:**

- [ ] **Test:** [P0] `runExternalPairIngestion()` should emit `ExternalPairIngestionRunCompletedEvent` with per-source stats and `durationMs`
  - **Status:** RED — service does not exist
  - **Verifies:** AC #15
  - **Assert:** `emitter.emit` called with `EVENT_NAMES.EXTERNAL_PAIR_INGESTION_RUN_COMPLETED` and payload containing `expect.objectContaining({ sources: expect.arrayContaining([expect.objectContaining({ source: expect.any(String), fetched: expect.any(Number), deduplicated: expect.any(Number), scored: expect.any(Number), autoApproved: expect.any(Number) })]), durationMs: expect.any(Number) })`

- [ ] **Test:** [P2] when all providers fail, should emit `SystemHealthError(4220, ...)` warning
  - **Status:** RED — service does not exist
  - **Verifies:** AC #12 — all-providers-failed is a health concern
  - **Assert:** warning-level event emitted with error code 4220

- [ ] **Test:** [P1] no startup run — service should NOT call `runExternalPairIngestion()` in `onModuleInit()`
  - **Status:** RED — service does not exist
  - **Verifies:** AC #10 — external pair lists are stable; cron schedule is sufficient
  - **Assert:** `onModuleInit()` only registers cron, does not trigger run

**CandidateDiscoveryService.isRunning getter — 1 test:**

- [ ] **Test:** [P1] `CandidateDiscoveryService.isRunning` public getter should return `_isRunning` private field value
  - **Status:** RED — getter does not exist (field is private)
  - **Verifies:** AC #10 — needed for concurrency guard
  - **Assert:** after calling internal state setter, `isRunning` reflects correct value
  - **File:** `pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.spec.ts` (MODIFIED, +1 test)

---

### Task 5: ExternalPairProcessorService — Fetch + Dedup + Score + Create (22 tests)

**File:** `pm-arbitrage-engine/src/modules/contract-matching/external-pair-processor.service.spec.ts` (NEW, ~550 lines)

**Provider fetching + error isolation — 3 tests:**

- [ ] **Test:** [P0] `processAllProviders()` should call `fetchPairs()` on both registered providers
  - **Status:** RED — ExternalPairProcessorService does not exist
  - **Verifies:** AC #4 — both providers invoked
  - **Assert:** both `oddsPipeProvider.fetchPairs()` and `predexonProvider.fetchPairs()` called once each

- [ ] **Test:** [P0] when one provider fetch fails (throws), should continue processing pairs from remaining provider
  - **Status:** RED — service does not exist
  - **Verifies:** AC #12 — per-provider error isolation
  - **Assert:** oddsPipe throws → predexon pairs still processed; stats include `providerError` for failed source

- [ ] **Test:** [P1] when provider fetch fails, error recorded in stats as `providerError` string for that source
  - **Status:** RED — service does not exist
  - **Verifies:** AC #12, #15 — error tracking in per-source stats
  - **Assert:** result stats for failed source include `providerError: expect.any(String)`

**Field mapping — 2 tests:**

- [ ] **Test:** [P0] `ExternalMatchedPair.polymarketId` should map to `ContractMatch.polymarketContractId` and `kalshiId` to `kalshiContractId`
  - **Status:** RED — service does not exist
  - **Verifies:** AC #8 — correct field mapping between different naming conventions
  - **Assert:** `prisma.contractMatch.create` called with `expect.objectContaining({ data: expect.objectContaining({ polymarketContractId: pair.polymarketId, kalshiContractId: pair.kalshiId }) })`

- [ ] **Test:** [P0] `ExternalMatchedPair.polymarketTitle` should map to `ContractMatch.polymarketDescription` and `kalshiTitle` to `kalshiDescription`
  - **Status:** RED — service does not exist
  - **Verifies:** AC #8 — titles used as descriptions
  - **Assert:** `prisma.contractMatch.create` called with `expect.objectContaining({ data: expect.objectContaining({ polymarketDescription: pair.polymarketTitle, kalshiDescription: pair.kalshiTitle }) })`

**Dedup — Predexon composite key — 2 tests:**

- [ ] **Test:** [P0] Predexon pair with matching `polymarketContractId` + `kalshiContractId` in existing ContractMatch should be skipped (deduplicated)
  - **Status:** RED — service does not exist
  - **Verifies:** AC #5 — deterministic composite key dedup
  - **Assert:** `prisma.contractMatch.findFirst` called with `{ where: { polymarketContractId: pair.polymarketId, kalshiContractId: pair.kalshiId } }` → returns existing → pair not scored

- [ ] **Test:** [P0] Predexon pair with NO matching ContractMatch should proceed to scoring
  - **Status:** RED — service does not exist
  - **Verifies:** AC #5 — novel pair passes dedup
  - **Assert:** `findFirst` returns null → `scoringStrategy.scoreMatch` called

**Dedup — OddsPipe fuzzy title matching — 3 tests:**

- [ ] **Test:** [P0] OddsPipe pair WITH contract IDs: should use composite key dedup (same as Predexon)
  - **Status:** RED — service does not exist
  - **Verifies:** AC #6 — composite key first for OddsPipe when IDs available
  - **Assert:** `findFirst` called with composite key → existing match → pair skipped

- [ ] **Test:** [P0] OddsPipe pair WITHOUT contract IDs: title similarity ABOVE threshold (>= 0.45) should be skipped (known pair)
  - **Status:** RED — service does not exist
  - **Verifies:** AC #6 — fuzzy title fallback, conservative threshold biases toward inclusion
  - **Assert:** `computeTitleSimilarity` returns 0.5 → pair skipped, `deduplicated` stat incremented

- [ ] **Test:** [P0] OddsPipe pair WITHOUT contract IDs: title similarity BELOW threshold (< 0.45) should proceed as novel pair
  - **Status:** RED — service does not exist
  - **Verifies:** AC #6 — below threshold = novel, proceed to scoring
  - **Assert:** `computeTitleSimilarity` returns 0.3 → pair proceeds to scoring

**OddsPipe ID-less pairs — 1 test:**

- [ ] **Test:** [P1] OddsPipe pair lacking BOTH `polymarketId` and `kalshiId` should be logged as `unresolvable` and skipped (not scored)
  - **Status:** RED — service does not exist
  - **Verifies:** AC #6 (dev notes) — cannot create ContractMatch without both IDs
  - **Assert:** pair with `polymarketId: null, kalshiId: null` → logged, `unresolvable` stat incremented, scoring NOT called

**LLM scoring — 2 tests:**

- [ ] **Test:** [P0] novel pair should be scored via `scoringStrategy.scoreMatch(polymarketTitle, kalshiTitle, { resolutionDate: null, category: null })`
  - **Status:** RED — service does not exist
  - **Verifies:** AC #7 — reuses existing LLM scoring pipeline, passes titles as descriptions
  - **Assert:** `scoringStrategy.scoreMatch` called with `expect.objectContaining({ })` matching title strings and null metadata

- [ ] **Test:** [P1] LLM concurrency should be limited by `EXTERNAL_PAIR_LLM_CONCURRENCY` config (default 5)
  - **Status:** RED — service does not exist
  - **Verifies:** AC #7 — pLimit-based concurrency control
  - **Assert:** with 10 pairs and concurrency=5, max 5 concurrent `scoreMatch` calls at any time

**Direction validation skip — 1 test:**

- [ ] **Test:** [P0] direction validation should be SKIPPED for external pairs; `divergenceNotes` should record `'Direction validation skipped — external pair lacks outcome metadata'`
  - **Status:** RED — service does not exist
  - **Verifies:** AC #14 — external pairs lack `outcomeLabel`, `clobTokenId`, `outcomeTokens[]`
  - **Assert:** `OutcomeDirectionValidator` NOT injected/called; ContractMatch created with `divergenceNotes` containing skip reason; score NOT capped

**Auto-approve/reject/review thresholds — 3 tests:**

- [ ] **Test:** [P0] pair with `effectiveScore >= LLM_AUTO_APPROVE_THRESHOLD` (default 85) should be auto-approved with `operatorApproved: true`
  - **Status:** RED — service does not exist
  - **Verifies:** AC #9, #13 — same thresholds as discovery
  - **Assert:** `prisma.contractMatch.create` called with `expect.objectContaining({ data: expect.objectContaining({ operatorApproved: true }) })`; `MatchApprovedEvent` + `MatchAutoApprovedEvent` emitted

- [ ] **Test:** [P0] pair with `effectiveScore < LLM_MIN_REVIEW_THRESHOLD` (default 40) should be auto-rejected
  - **Status:** RED — service does not exist
  - **Verifies:** AC #13 — below-review-threshold rejection
  - **Assert:** ContractMatch created with `operatorApproved: false`; NO `MatchApprovedEvent` emitted

- [ ] **Test:** [P0] pair with score between thresholds (40 <= score < 85) should be pending review
  - **Status:** RED — service does not exist
  - **Verifies:** AC #9, #13 — pending review range
  - **Assert:** ContractMatch created with `operatorApproved: false`; `MatchPendingReviewEvent` emitted with `expect.objectContaining({ matchId: expect.any(String), score: expect.any(Number) })`

**ContractMatch creation + origin — 2 tests:**

- [ ] **Test:** [P0] ContractMatch should be created with `origin: 'PREDEXON'` for Predexon-sourced pairs
  - **Status:** RED — service does not exist
  - **Verifies:** AC #8 — origin tracks pair source
  - **Assert:** `prisma.contractMatch.create` data includes `origin: 'PREDEXON'`

- [ ] **Test:** [P0] ContractMatch should be created with `origin: 'ODDSPIPE'` for OddsPipe-sourced pairs
  - **Status:** RED — service does not exist
  - **Verifies:** AC #8 — origin tracks pair source
  - **Assert:** `prisma.contractMatch.create` data includes `origin: 'ODDSPIPE'`

**P2002 race condition — 1 test:**

- [ ] **Test:** [P2] when `prisma.contractMatch.create` throws P2002 unique constraint violation, should log debug and skip (not fail run)
  - **Status:** RED — service does not exist
  - **Verifies:** AC #4 (dev notes) — race condition between findFirst and create
  - **Assert:** P2002 error caught silently, no exception propagated, next pair still processed

**Cluster classification — 1 test:**

- [ ] **Test:** [P1] non-rejected pairs should have `clusterClassifier.classifyMatch()` called; failure should NOT block ContractMatch creation
  - **Status:** RED — service does not exist
  - **Verifies:** AC #9 — cluster classification for non-rejected, graceful failure
  - **Assert:** `classifyMatch` called for auto-approved and pending-review; when `classifyMatch` throws, ContractMatch still created, `ClusterAssignedEvent` NOT emitted for that pair

**Event emission with payload verification — 1 test:**

- [ ] **Test:** [P0] auto-approved pair should emit `MatchApprovedEvent`, `MatchAutoApprovedEvent`, and `ClusterAssignedEvent` with correct payloads
  - **Status:** RED — service does not exist
  - **Verifies:** AC #9 — same events as CandidateDiscoveryService
  - **Assert:** `emitter.emit` called with each event name and `expect.objectContaining({ matchId, score, origin })` payloads

---

### Task 6: Events + Dashboard Gateway Handler (7 tests)

**File:** `pm-arbitrage-engine/src/common/events/external-pair-ingestion-run-completed.event.spec.ts` (NEW, ~60 lines)
**File:** `pm-arbitrage-engine/src/dashboard/dashboard.gateway.spec.ts` (MODIFIED, +2 tests)
**File:** `pm-arbitrage-engine/src/dashboard/dto/ws-events.dto.ts` (MODIFIED, +1 constant)

**Event catalog — 1 test:**

- [ ] **Test:** [P0] `EVENT_NAMES.EXTERNAL_PAIR_INGESTION_RUN_COMPLETED` should equal `'contract.external-pair-ingestion.run_completed'`
  - **Status:** RED — event name not defined in event-catalog.ts
  - **Verifies:** AC #15 — event naming follows dot-notation convention

**Event class — 2 tests:**

- [ ] **Test:** [P0] `ExternalPairIngestionRunCompletedEvent` should carry `sources` array with per-source stats: `{ source, fetched, deduplicated, scored, autoApproved, pendingReview, autoRejected, scoringFailures, unresolvable, providerError? }` + `durationMs`
  - **Status:** RED — event class does not exist
  - **Verifies:** AC #15 — per-source tracking
  - **Assert:** `new ExternalPairIngestionRunCompletedEvent(payload)` has all fields with correct types via `expect.objectContaining()`

- [ ] **Test:** [P1] event class should extend `BaseEvent` (or follow existing event pattern) with correct `eventName` property
  - **Status:** RED — event class does not exist
  - **Verifies:** Architecture — event class pattern compliance

**Dashboard gateway handler — 2 tests:**

- [ ] **Test:** [P0] DashboardGateway should have `@OnEvent` handler for `EXTERNAL_PAIR_INGESTION_RUN_COMPLETED` that broadcasts to WS clients
  - **Status:** RED — handler does not exist in dashboard.gateway.ts
  - **Verifies:** AC #15 — run stats visible to operator in real-time
  - **Assert:** when event emitted, WS clients receive message

- [ ] **Test:** [P1] WS event constant defined in `ws-events.dto.ts` for external pair ingestion run completed
  - **Status:** RED — constant not defined
  - **Verifies:** AC #15 — WS event naming convention

**Event wiring integration — 2 tests:**

**File:** `pm-arbitrage-engine/src/common/testing/event-wiring-audit.spec.ts` (MODIFIED, +2 tests)

- [ ] **Test:** [P0] `expectEventHandled()` verifies `EXTERNAL_PAIR_INGESTION_RUN_COMPLETED` event wiring from emitter to DashboardGateway handler
  - **Status:** RED — @OnEvent handler does not exist
  - **Verifies:** AC #15 — event actually reaches gateway via real EventEmitter2
  - **Assert:** `expectEventHandled({ module, eventName: EVENT_NAMES.EXTERNAL_PAIR_INGESTION_RUN_COMPLETED, ... })`

- [ ] **Test:** [P1] `expectNoDeadHandlers()` should pass after adding new handler (no dead handler drift)
  - **Status:** RED — handler does not exist
  - **Verifies:** Architecture — dead handler detection

---

### Task 7: Dashboard Origin Column + Filter (6 tests)

**Backend DTO — 2 tests:**

**File:** `pm-arbitrage-engine/src/modules/contract-matching/calibration.controller.spec.ts` (MODIFIED, +2 tests)

- [ ] **Test:** [P1] matches endpoint response DTO should include `origin` field of type `MatchOrigin`
  - **Status:** RED — `origin` not in response DTO
  - **Verifies:** AC #8, #11 — origin visible to frontend
  - **Assert:** response body contains `origin` field for each match

- [ ] **Test:** [P1] matches endpoint should support filtering by `origin` query parameter
  - **Status:** RED — filter not implemented
  - **Verifies:** AC #11 — filterable on dashboard
  - **Assert:** `GET /api/calibration/matches?origin=PREDEXON` returns only Predexon-origin matches

**Frontend component — 4 tests:**

**File:** `pm-arbitrage-dashboard/src/components/matches/OriginBadge.spec.tsx` (NEW, ~80 lines)

- [ ] **Test:** [P1] `OriginBadge` renders gray badge for `DISCOVERY` origin
  - **Status:** RED — component does not exist
  - **Verifies:** AC #11 — default/gray for discovery
  - **Assert:** badge element has gray styling and text "DISCOVERY"

- [ ] **Test:** [P1] `OriginBadge` renders blue badge for `PREDEXON`, green for `ODDSPIPE`, orange for `MANUAL`
  - **Status:** RED — component does not exist
  - **Verifies:** AC #11 — color coding per origin
  - **Assert:** each origin value produces correct color class/variant

- [ ] **Test:** [P1] matches table includes origin column rendering `OriginBadge` for each row
  - **Status:** RED — column not added to matches table
  - **Verifies:** AC #11 — origin visible in table
  - **Assert:** table renders `OriginBadge` component per match row

- [ ] **Test:** [P2] matches table origin filter dropdown filters displayed matches by selected origin
  - **Status:** RED — filter not implemented
  - **Verifies:** AC #11 — filter works
  - **Assert:** selecting "PREDEXON" in filter dropdown → only PREDEXON matches shown

---

### Independence Verification (1 test)

**File:** `pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.spec.ts` (MODIFIED, +1 test)

- [ ] **Test:** [P0] `CandidateDiscoveryService` behavior should be unchanged — no new imports, no modified method signatures, no new event handlers
  - **Status:** GREEN (existing tests should still pass) — verify transitively
  - **Verifies:** AC #16 — two pipelines are independent
  - **Assert:** existing CandidateDiscoveryService tests continue to pass unchanged; no imports from external pair ingestion

---

## Collection Lifecycle (1 test)

- [ ] **Test:** [P1] `ExternalPairIngestionService._isRunning` flag cleanup: flag resets to false in finally block after `runExternalPairIngestion()`
  - **Status:** RED — service does not exist
  - **Verifies:** Architecture — collection/flag lifecycle requirement
  - **Assert:** covered by Task 4 concurrency guard tests (flag reset after error)
  - **Comment:** `/** Cleanup: reset in finally block of runExternalPairIngestion() */`

---

## Module Registration (1 test)

- [ ] **Test:** [P1] `ExternalPairIngestionService` and `ExternalPairProcessorService` should be registered in `ContractMatchingModule` providers
  - **Status:** RED — services not registered
  - **Verifies:** AC #10 — NestJS DI wiring
  - **Assert:** verified transitively — if services instantiate via DI in integration tests, registration is correct

---

## Summary

| Category | Test Count | P0 | P1 | P2 |
|----------|-----------|----|----|-----|
| Task 1: Interface + Schema Migration | 8 | 4 | 3 | 1 |
| Task 2: Config | 8 | 0 | 8 | 0 |
| Task 3: Provider Adapters | 6 | 4 | 2 | 0 |
| Task 4: Ingestion Coordinator | 11 | 5 | 4 | 2 |
| Task 5: Pair Processor | 22 | 14 | 5 | 3 |
| Task 6: Events + Gateway | 7 | 3 | 3 | 1 |
| Task 7: Dashboard Origin | 6 | 0 | 4 | 2 |
| Independence Verification | 1 | 1 | 0 | 0 |
| Collection Lifecycle | 1 | 0 | 1 | 0 |
| Module Registration | 1 | 0 | 1 | 0 |
| **Total** | **71** | **31** | **31** | **9** |

---

## Anti-Pattern Guards

- **DO NOT** re-implement LLM scoring logic — always delegate to `SCORING_STRATEGY_TOKEN`
- **DO NOT** add a second retry layer around `fetchPairs()` — providers already have built-in retry
- **DO NOT** import backtesting module services directly into contract-matching — use DI tokens via `IExternalPairProvider` interface
- **DO NOT** create a separate rate limiter — providers manage their own rate limiting
- **DO NOT** use `processCandidate()` from CandidateDiscoveryService — it's private and takes `ContractSummary` objects
- **DO NOT** compute staleness/freshness on frontend for origin badge — origin is a static enum field
- **DO NOT** use native JS float operations for any financial calculations — use `decimal.js`
- **DO NOT** use bare `toHaveBeenCalled()` — always verify payloads with `expect.objectContaining()`
- **DO NOT** inject `OutcomeDirectionValidator` in ExternalPairProcessorService — external pairs lack outcome metadata
- **DO NOT** cap scores due to missing direction data — that penalizes all external pairs unfairly
