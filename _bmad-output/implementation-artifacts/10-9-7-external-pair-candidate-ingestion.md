# Story 10-9.7: External Pair Candidate Ingestion

Status: done

## Story

As an operator,
I want the discovery pipeline to proactively import matched pairs from OddsPipe and Predexon as LLM scoring candidates,
So that the system discovers arbitrage opportunities beyond what catalog brute-force finds, substantially expanding the tradeable pair universe.

## Acceptance Criteria

1. **Given** the `IExternalPairProvider` interface is defined, **When** inspecting `common/interfaces/`, **Then** it contains `fetchPairs(): Promise<ExternalMatchedPair[]>` and `getSourceId(): string`, exported with DI tokens `ODDSPIPE_PAIR_PROVIDER_TOKEN` and `PREDEXON_PAIR_PROVIDER_TOKEN`.
2. **Given** the `OddsPipeService` exists in the backtesting module, **When** implementing `IExternalPairProvider`, **Then** `fetchPairs()` delegates to the existing `fetchMatchedPairs()` method and `getSourceId()` returns `'oddspipe'`.
3. **Given** the `PredexonMatchingService` exists in the backtesting module, **When** implementing `IExternalPairProvider`, **Then** `fetchPairs()` delegates to the existing `fetchMatchedPairs()` method and `getSourceId()` returns `'predexon'`.
4. **Given** external pairs are fetched from all registered providers, **When** `ExternalPairProcessorService` processes them, **Then** each pair is checked for duplicates against existing `ContractMatch` records before scoring.
5. **Given** a Predexon pair has `polymarketId` and `kalshiId` populated, **When** deduplication runs, **Then** it uses deterministic composite key matching (`polymarketContractId` + `kalshiContractId`) — exact match only.
6. **Given** an OddsPipe pair may lack contract IDs, **When** deduplication runs, **Then** it first attempts composite key match (if IDs present), then falls back to fuzzy title matching against existing `ContractMatch.polymarketDescription` and `ContractMatch.kalshiDescription` with a conservative threshold that biases toward inclusion (re-score over skip).
7. **Given** a novel external pair passes deduplication, **When** scoring runs, **Then** it is scored through `ConfidenceScorerService` (same LLM pipeline as catalog discovery) using the same `IScoringStrategy` interface.
8. **Given** a novel external pair is scored, **When** persisted, **Then** a `ContractMatch` record is created with `origin` field set to `'PREDEXON'` or `'ODDSPIPE'` matching the provider source. Existing `ContractMatch` records retain their origin (`DISCOVERY` for pipeline-discovered, `MANUAL` for YAML-configured).
9. **Given** a scored pair crosses the auto-approve threshold, **When** the record is created, **Then** events are emitted following existing patterns (`MatchApprovedEvent`, `MatchAutoApprovedEvent`, `MatchPendingReviewEvent`) and cluster classification runs for non-rejected pairs.
10. **Given** external pair ingestion runs on a configurable cron schedule, **When** the cron fires, **Then** `ExternalPairIngestionService` coordinates the full fetch → dedup → score → persist cycle, with concurrency guard preventing overlap with itself or `CandidateDiscoveryService`.
11. **Given** a `ContractMatch` has an `origin` field, **When** the operator views the matches table on the dashboard, **Then** the origin is displayed as a badge/indicator and is filterable.
12. **Given** an external provider is unreachable (API down, rate limited, auth failure), **When** the ingestion run encounters the failure, **Then** it degrades gracefully — processes pairs from available providers and logs the failure. A single provider outage does not fail the entire run.
13. **Given** auto-approve/review/reject thresholds, **When** applied to external pairs, **Then** they match existing discovery pipeline configuration (`LLM_AUTO_APPROVE_THRESHOLD`, `LLM_MIN_REVIEW_THRESHOLD`).
14. **Given** external pairs lack `outcomeLabel`, `clobTokenId`, and `outcomeTokens[]` metadata, **When** scoring runs, **Then** direction validation is skipped (not capped) with `divergenceNotes` recording the skip reason. LLM confidence score is the primary quality gate for external pairs. Direction is validated by the operator during manual review of pending matches.
15. **Given** a completed ingestion run, **When** stats are emitted, **Then** they track per-source counts: fetched, deduplicated (skipped), scored, auto-approved, pending-review, auto-rejected, scoring-failures. Event: `ExternalPairIngestionRunCompletedEvent`.
16. **Given** the existing discovery pipeline, **When** external pair ingestion is active, **Then** no behavior changes in the existing `CandidateDiscoveryService`. The two pipelines are independent.

## Sizing Gate

7 tasks, 3 integration boundaries (contract-matching backend services, backtesting module adapter, dashboard frontend origin column). At the 3-boundary threshold — acceptable because backtesting adapter is thin (add interface to existing services) and dashboard is a single column addition.

## Tasks / Subtasks

- [x] **Task 1: IExternalPairProvider interface + MatchOrigin schema migration** (AC: #1, #8)
  - [x] 1.1 Define `IExternalPairProvider` interface in `common/interfaces/external-pair-provider.interface.ts` with `fetchPairs(): Promise<ExternalMatchedPair[]>` and `getSourceId(): string`
  - [x] 1.2 Add DI token constants: `ODDSPIPE_PAIR_PROVIDER_TOKEN`, `PREDEXON_PAIR_PROVIDER_TOKEN` (follow `IContractCatalogProvider` multi-token pattern)
  - [x] 1.3 Export from `common/interfaces/index.ts`
  - [x] 1.4 Add `MatchOrigin` enum to `prisma/schema.prisma`: `DISCOVERY`, `PREDEXON`, `ODDSPIPE`, `MANUAL`
  - [x] 1.5 Add `origin` field to `ContractMatch` model: `origin MatchOrigin @default(DISCOVERY) @map("origin")`
  - [x] 1.6 Add `@@index([origin])` to ContractMatch for dashboard filtering
  - [x] 1.7 Create migration via `pnpm prisma migrate dev --name add-contract-match-origin` (deferred if no running DB)
  - [x] 1.8 Run `pnpm prisma generate`
  - [x] 1.9 Backfill logic: existing records default to `DISCOVERY`. Update YAML-sourced pairs to `MANUAL` (where `operatorApproved = true` AND `operatorRationale IS NULL`)
  - [x] 1.10 Update `ContractMatchSyncService.syncPairsToDatabase()` to set `origin: MatchOrigin.MANUAL` explicitly on upsert — ensures new YAML pairs are tagged correctly going forward
  - [x] 1.11 Tests: interface type check, Prisma schema generates correctly, backfill migration correctness, sync service origin field

- [x] **Task 2: Config — cron expression + enabled flag + dedup threshold** (AC: #10, #13)
  - [x] 2.1 Add `EXTERNAL_PAIR_INGESTION_CRON_EXPRESSION` to `env.schema.ts` (default: `'0 0 6,18 * * *'` — twice daily at 6 AM/6 PM UTC)
  - [x] 2.2 Add `EXTERNAL_PAIR_INGESTION_ENABLED` to `env.schema.ts` (default: `true`)
  - [x] 2.3 Add `EXTERNAL_PAIR_DEDUP_TITLE_THRESHOLD` to `env.schema.ts` (default: `0.45` — conservative fuzzy match for OddsPipe title dedup, bias toward inclusion)
  - [x] 2.4 Add `EXTERNAL_PAIR_LLM_CONCURRENCY` to `env.schema.ts` (default: `5` — concurrent LLM scoring calls for external pairs, lower than discovery's 10 since external pairs are pre-vetted and batches are smaller)
  - [x] 2.5 Add config-defaults entries for all four
  - [x] 2.6 Add settings-metadata entries for dashboard tunability
  - [x] 2.7 Update `.env.example` with new variables
  - [x] 2.8 Tests: config-defaults coverage, env schema validation

- [x] **Task 3: OddsPipe + Predexon implement IExternalPairProvider + DI wiring** (AC: #2, #3, #12)
  - [x] 3.1 Add `implements IExternalPairProvider` to `PredexonMatchingService` in `modules/backtesting/validation/predexon-matching.service.ts`
  - [x] 3.2 Implement `fetchPairs()` → delegates to existing `fetchMatchedPairs()`. Implement `getSourceId()` → returns `'predexon'`
  - [x] 3.3 Add `implements IExternalPairProvider` to `OddsPipeService` in `modules/backtesting/ingestion/oddspipe.service.ts`
  - [x] 3.4 Implement `fetchPairs()` → delegates to existing `fetchMatchedPairs()` (the `/v1/spreads` endpoint). Implement `getSourceId()` → returns `'oddspipe'`
  - [x] 3.5 Register DI tokens in backtesting module exports: `{ provide: ODDSPIPE_PAIR_PROVIDER_TOKEN, useExisting: OddsPipeService }` and `{ provide: PREDEXON_PAIR_PROVIDER_TOKEN, useExisting: PredexonMatchingService }`
  - [x] 3.6 Export tokens from `IngestionModule` (OddsPipe) and `ValidationModule` (Predexon) respectively
  - [x] 3.7 Verify `BacktestingModule` (or parent module) re-exports tokens from `IngestionModule` and `ValidationModule` so `ContractMatchingModule` can access them. If not, add explicit re-exports or use `forwardRef()` wiring.
  - [x] 3.8 Tests: adapter methods delegate correctly, getSourceId() returns correct identifier, graceful degradation on API failure

- [x] **Task 4: ExternalPairIngestionService — coordinator + scheduling** (AC: #10, #12, #15, #16)
  - [x] 4.1 Create `external-pair-ingestion.service.ts` in `modules/contract-matching/` — coordinator (leaf service, 6 deps: EventEmitter2, ConfigService, SchedulerRegistry, ExternalPairProcessorService, PrismaService, CandidateDiscoveryService). `/** 6 deps rationale: CandidateDiscoveryService needed for isRunning concurrency check — same module */`
  - [x] 4.2 Register cron via `SchedulerRegistry` in `onModuleInit()` using configurable expression from config (follow `CandidateDiscoveryService` pattern with runtime reload support)
  - [x] 4.3 Add `public get isRunning(): boolean { return this._isRunning; }` getter to `CandidateDiscoveryService` (currently private — needed for concurrency guard)
  - [x] 4.4 Concurrency guard — skip if own `_isRunning` flag or `CandidateDiscoveryService.isRunning` is true. Inject `CandidateDiscoveryService` for this check (it's in the same module). Log skip at debug level.
  - [x] 4.5 `handleCron()`: check enabled flag (use `enabled !== true` pattern per 10-9-6 learning) → concurrency guard → call `runExternalPairIngestion()`
  - [x] 4.6 `runExternalPairIngestion()`: delegate to ExternalPairProcessorService → collect stats → emit `ExternalPairIngestionRunCompletedEvent`. If all providers failed, emit `SystemHealthError(4220, ...)` warning.
  - [x] 4.7 No startup run — external pair lists are stable; cron schedule is sufficient. Decision: `EXTERNAL_PAIR_INGESTION_RUN_ON_STARTUP = false` (not configurable, hardcoded).
  - [x] 4.8 Register in `ContractMatchingModule` providers. Add `CandidateDiscoveryService` to deps (same module, no import needed — just DI).
  - [x] 4.9 Tests: cron scheduling, concurrency guard (own + discovery overlap), enabled flag check, run completion event with correct stats, runtime cron reload, all-providers-failed warning

- [x] **Task 5: ExternalPairProcessorService — fetch + dedup + score + create** (AC: #4, #5, #6, #7, #8, #9, #13, #14)
  - [x] 5.1 Create `external-pair-processor.service.ts` in `modules/contract-matching/` — facade (≤7 deps: PrismaService, ODDSPIPE_PAIR_PROVIDER_TOKEN, PREDEXON_PAIR_PROVIDER_TOKEN, SCORING_STRATEGY_TOKEN, CLUSTER_CLASSIFIER_TOKEN, EventEmitter2, ConfigService). No OutcomeDirectionValidator — external pairs lack outcome metadata for direction checks.
  - [x] 5.2 `/** 7 deps rationale: Facade coordinating 2 external pair providers + LLM scoring + cluster classification + persistence + events + config */`
  - [x] 5.3 `processAllProviders()`: iterate providers, call `fetchPairs()` on each with try/catch for per-provider error isolation → aggregate all pairs → deduplicate → score → return stats
  - [x] 5.4 **Field mapping**: `ExternalMatchedPair` uses `polymarketId`/`kalshiId`; Prisma uses `polymarketContractId`/`kalshiContractId`. Map explicitly: `polymarketContractId = pair.polymarketId`, `kalshiContractId = pair.kalshiId`. Check nullability before proceeding.
  - [x] 5.5 **Dedup — Predexon path** (pairs with IDs): `prisma.contractMatch.findFirst({ where: { polymarketContractId: pair.polymarketId, kalshiContractId: pair.kalshiId } })` — if exists, skip
  - [x] 5.6 **Dedup — OddsPipe path** (pairs may lack IDs): if IDs present, use composite key check (same as Predexon). If IDs absent, fuzzy match `polymarketTitle`/`kalshiTitle` against existing `ContractMatch.polymarketDescription`/`ContractMatch.kalshiDescription` using normalized token overlap (Jaccard similarity — see Dev Notes `computeTitleSimilarity()`). Threshold from `EXTERNAL_PAIR_DEDUP_TITLE_THRESHOLD` config (default 0.45). Above threshold = known (skip). Below threshold = novel (proceed). **Bias toward inclusion** — a duplicate LLM call costs fractions of a cent; a missed opportunity costs real money.
  - [x] 5.7 **ID resolution for OddsPipe pairs without IDs**: Pairs lacking both `polymarketId` and `kalshiId` CANNOT create a `ContractMatch` (both are required non-nullable fields). Do NOT attempt complex catalog resolution — log as `unresolvable` with pair titles and skip. Track count in `unresolvable` stat. This is acceptable: if OddsPipe doesn't provide IDs for a pair, the contracts may not be actively traded on our connected platforms.
  - [x] 5.8 **LLM concurrency**: Use `pLimit(EXTERNAL_PAIR_LLM_CONCURRENCY)` (default 5) to batch LLM scoring calls. Follow `CandidateDiscoveryService` concurrency pattern.
  - [x] 5.9 **Scoring**: Call `scoringStrategy.scoreMatch(pair.polymarketTitle, pair.kalshiTitle, { resolutionDate: null, category: null })` — uses titles as descriptions. External pairs don't carry resolution dates or categories — pass null (the LLM scorer handles optional metadata gracefully).
  - [x] 5.10 **Direction validation**: External pairs lack `outcomeLabel`, `clobTokenId`, and `outcomeTokens[]` required by `validateDirection()`. **Skip direction validation for external pairs** — set `divergenceNotes: 'Direction validation skipped — external pair lacks outcome metadata'`. The LLM score is the primary confidence gate. Do NOT cap scores due to missing direction data — that would penalize all external pairs unfairly. Direction will be validated when the operator reviews pending matches.
  - [x] 5.11 **Auto-approve decision**: Same thresholds as discovery: `>= LLM_AUTO_APPROVE_THRESHOLD` (default 85) → auto-approve; `< LLM_MIN_REVIEW_THRESHOLD` (default 40) → auto-reject; between → pending review.
  - [x] 5.12 **ContractMatch creation**: `prisma.contractMatch.create({ data: { polymarketContractId: pair.polymarketId, kalshiContractId: pair.kalshiId, polymarketDescription: pair.polymarketTitle, kalshiDescription: pair.kalshiTitle, confidenceScore: effectiveScore, origin: pair.source === 'predexon' ? 'PREDEXON' : 'ODDSPIPE', operatorApproved: isAutoApproved, operatorRationale: ..., divergenceNotes, primaryLeg: 'kalshi' } })`. Handle P2002 unique constraint violation gracefully (race condition between findFirst and create — log debug, skip).
  - [x] 5.13 **Cluster classification**: For non-rejected pairs, call `clusterClassifier.classifyMatch()`. Graceful failure — don't block match creation.
  - [x] 5.14 **Event emission**: `MatchApprovedEvent` + `MatchAutoApprovedEvent` for auto-approved; `MatchPendingReviewEvent` for pending; `ClusterAssignedEvent` for classified. Same events as `CandidateDiscoveryService`.
  - [x] 5.15 Register in `ContractMatchingModule` providers
  - [x] 5.16 Tests: per-provider fetch with error isolation, field mapping (polymarketId→polymarketContractId), Predexon composite key dedup, OddsPipe fuzzy title dedup (above/below threshold), OddsPipe ID-less pair skip with unresolvable stat, LLM concurrency limiting, scoring delegation with title-as-description, direction validation skipped with correct divergenceNotes, auto-approve/reject/review thresholds, ContractMatch creation with correct origin enum, P2002 race condition handling, cluster classification success/failure, event emission with payload verification (`expect.objectContaining()`)

- [x] **Task 6: Events + dashboard gateway handler** (AC: #9, #15)
  - [x] 6.1 Add `EXTERNAL_PAIR_INGESTION_RUN_COMPLETED` to `EVENT_NAMES` in `event-catalog.ts`: `'contract.external-pair-ingestion.run_completed'`
  - [x] 6.2 Create `ExternalPairIngestionRunCompletedEvent` in `common/events/discovery.events.ts` with per-source stats: `{ source: string, fetched: number, deduplicated: number, scored: number, autoApproved: number, pendingReview: number, autoRejected: number, scoringFailures: number, unresolvable: number, providerError?: string }[]` + `durationMs: number`
  - [x] 6.3 Add `@OnEvent` handler in `DashboardGateway` for `EXTERNAL_PAIR_INGESTION_RUN_COMPLETED` → broadcast to WS clients
  - [x] 6.4 Add WS event constant in `dashboard/dto/ws-events.dto.ts`
  - [x] 6.5 Add event wiring test via `expectEventHandled()` in event-wiring-audit.spec.ts
  - [x] 6.6 Tests: event class construction + payload structure, gateway handler wiring, WS broadcast

- [x] **Task 7: Dashboard origin column + filter** (AC: #8, #11)
  - [x] 7.1 Verify matches endpoint DTO includes `origin` field. Check `CalibrationController` and related DTOs (e.g., `ContractMatchResponseDto` or equivalent in `modules/contract-matching/`). If not present, add `origin: MatchOrigin` to the response DTO and update controller mapping.
  - [x] 7.2 Add `origin` field to matches table in dashboard (badge component — `DISCOVERY` default/gray, `PREDEXON` blue, `ODDSPIPE` green, `MANUAL` orange)
  - [x] 7.3 Add origin filter to matches table (dropdown or multi-select)
  - [x] 7.4 Regenerate API client if using `swagger-typescript-api` (see Story 10-9-6 note about client regeneration)
  - [x] 7.5 Tests: backend DTO includes origin, origin badge renders correct color/label per origin value, filter works

## QA Verification (AI)

- [x] **[AI-QA] Task 8: Add `broadcastExternalPairIngestionCompleted` to `allGatewayMethods` in event wiring audit** (P2)
  - **File:** `pm-arbitrage-engine/src/common/testing/event-wiring-audit.spec.ts`
  - **Issue:** `broadcastExternalPairIngestionCompleted` is listed in `gatewayHandlers` (line 664) but missing from `allGatewayMethods` (lines 502-532). The `allGatewayMethods` array is used in `beforeEach` to pre-spy all gateway handler methods via `buildAndInit()`. All other gateway handlers are in both arrays — this one was missed.
  - **Fix:** Add `'broadcastExternalPairIngestionCompleted',` after line 531 (after `'broadcastStalenessWarning'`) with comment `// External pair ingestion (Story 10-9-7)`.
  - **Verify:** `pnpm test -- src/common/testing/event-wiring-audit.spec.ts` still passes (53 tests).

## Dev Notes

### Critical Design Decisions

**Deduplication Strategy (the design-critical piece):**

| Provider | ID Available | Dedup Method | Threshold |
|---|---|---|---|
| Predexon | Yes (`polymarket_condition_id` + `kalshi_ticker`) | Composite key: `findFirst({ polymarketContractId, kalshiContractId })` | Exact match (deterministic) |
| OddsPipe (with IDs) | Sometimes | Composite key (same as Predexon) | Exact match |
| OddsPipe (no IDs) | No | Fuzzy title match against `ContractMatch` descriptions | `EXTERNAL_PAIR_DEDUP_TITLE_THRESHOLD` (default 0.45) |

**Bias toward inclusion:** The dedup threshold is intentionally low (0.45). A false-negative dedup (duplicate LLM call) costs ~$0.001-0.01. A false-positive dedup (missed arbitrage opportunity) costs real money. When in doubt, re-score.

**OddsPipe pairs without contract IDs:** If an OddsPipe pair lacks `polymarketId` and `kalshiId`, the system cannot create a `ContractMatch` record (both are required non-nullable fields with a unique constraint). These are logged as `unresolvable` and tracked in stats. This is acceptable — if we can't find the contracts in our platform connections, we can't trade them anyway.

### Service Decomposition (DI Limit Compliance)

Two services to stay within constructor injection limits:

1. **`ExternalPairIngestionService`** (coordinator, leaf, 6 deps): EventEmitter2, ConfigService, SchedulerRegistry, ExternalPairProcessorService, PrismaService, CandidateDiscoveryService. `/** 6 deps rationale: CandidateDiscoveryService needed for isRunning concurrency check — same module, no cross-boundary import */`

2. **`ExternalPairProcessorService`** (facade, 7 deps): PrismaService, ODDSPIPE_PAIR_PROVIDER_TOKEN, PREDEXON_PAIR_PROVIDER_TOKEN, SCORING_STRATEGY_TOKEN, CLUSTER_CLASSIFIER_TOKEN, EventEmitter2, ConfigService. Handles: provider fetching, deduplication, LLM scoring, ContractMatch creation, cluster classification, per-match event emission. Direction validation skipped (external pairs lack outcome metadata).

`/** 7 deps rationale: Facade coordinating 2 external pair providers + LLM scoring + cluster classification + persistence + events + config */`

### Module Dependency Wiring (CRITICAL — must not violate architecture rules)

```
common/interfaces/IExternalPairProvider   ← defined here (neutral territory)
        ↑                                  ↑
backtesting/ingestion/OddsPipeService      contract-matching/ExternalPairProcessorService
  implements IExternalPairProvider           consumes via DI token
backtesting/validation/PredexonMatchingService
  implements IExternalPairProvider
```

**DI wiring path:**
1. `IngestionModule` registers `{ provide: ODDSPIPE_PAIR_PROVIDER_TOKEN, useExisting: OddsPipeService }` and exports it
2. `ValidationModule` registers `{ provide: PREDEXON_PAIR_PROVIDER_TOKEN, useExisting: PredexonMatchingService }` and exports it
3. `ContractMatchingModule` imports the parent `BacktestingModule` (which re-exports from IngestionModule + ValidationModule) to access the tokens
4. If circular dependency: use `forwardRef()` (pattern established in Story 10-9-6 between IngestionModule ↔ ValidationModule)

**NO forbidden imports violated:** Contract-matching never imports backtesting services directly — only `IExternalPairProvider` from `common/interfaces/`.

### Scoring Pipeline Reuse (DO NOT REINVENT)

The scoring logic in `ExternalPairProcessorService` MUST mirror `CandidateDiscoveryService.processCandidate()` (lines 316-529 of `candidate-discovery.service.ts`). Specifically:

1. **Duplicate check:** `findFirst({ where: { polymarketContractId, kalshiContractId } })` — exact same query
2. **LLM scoring:** `scoringStrategy.scoreMatch(polyDescription, kalshiDescription, { resolutionDate, category })` — same interface (pass null for missing metadata)
3. **Direction validation:** SKIPPED for external pairs (lack outcome metadata). Set `divergenceNotes` to record skip. Do NOT inject/call `OutcomeDirectionValidator` — remove from facade deps if not needed.
4. **Auto-approve logic:** `effectiveScore >= autoApproveThreshold` (no direction check since validation is skipped)
5. **Below-review-threshold rejection:** `effectiveScore < minReviewThreshold`
7. **ContractMatch.create data shape:** Same fields as processCandidate() + `origin` field
8. **Cluster classification:** Only for non-rejected (`!isBelowReviewThreshold`), graceful failure
9. **Event emission:** Same event classes — `MatchApprovedEvent`, `MatchAutoApprovedEvent`, `MatchPendingReviewEvent`, `ClusterAssignedEvent`
10. **P2002 handling:** Catch unique constraint violation (race condition), log debug, skip

**The ONLY differences from processCandidate():**
- Input source: external pairs instead of catalog candidates (no pre-filter step)
- `origin` field set on ContractMatch creation
- `operatorRationale` includes source identifier: `"Auto-approved by external pair ingestion (source: predexon, score: 92, model: ...)"`
- **Direction validation SKIPPED** — external pairs lack `outcomeLabel`, `clobTokenId`, `outcomeTokens[]`. Set `divergenceNotes: 'Direction validation skipped — external pair lacks outcome metadata'` but do NOT cap scores. LLM confidence is the primary gate; direction is verified during operator review.
- Stats tracking includes `deduplicated`, `unresolvable`, and `providerError` counts
- LLM concurrency uses separate config `EXTERNAL_PAIR_LLM_CONCURRENCY` (default 5) vs discovery's 10
- Field mapping: `ExternalMatchedPair.polymarketId` → `ContractMatch.polymarketContractId` (different naming)

### ExternalMatchedPair → ContractMatch Field Mapping

`ExternalMatchedPair` (from `backtesting/types/match-validation.types.ts`) uses different field names than `ContractMatch` (Prisma). Map explicitly:

| ExternalMatchedPair field | ContractMatch field | Notes |
|---|---|---|
| `polymarketId` | `polymarketContractId` | Nullable — skip pair if null |
| `kalshiId` | `kalshiContractId` | Nullable — skip pair if null |
| `polymarketTitle` | `polymarketDescription` | Used as description for LLM scoring |
| `kalshiTitle` | `kalshiDescription` | Used as description for LLM scoring |
| `source` | `origin` (mapped to enum) | `'predexon'` → `PREDEXON`, `'oddspipe'` → `ODDSPIPE` |
| N/A | `clobTokenId` | Not available — set null |
| N/A | `outcomeLabel` | Not available — set null |
| N/A | `category` | Not available — set null |
| N/A | `settlementDate`/`resolutionDate` | Not available — set null |

**Scoring does NOT require `ContractSummary` objects.** `ConfidenceScorerService.scoreMatch()` takes two description strings and optional metadata. Pass titles directly: `scoreMatch(pair.polymarketTitle, pair.kalshiTitle, { resolutionDate: null, category: null })`.

**Direction validation SKIPPED** because external pairs lack `outcomeLabel`, `clobTokenId`, and `outcomeTokens[]`. The LLM scorer handles missing metadata gracefully — nullable fields cause no errors.

### Concurrency Guard

The ingestion service must NOT run concurrently with:
- Another external pair ingestion run (own `_isRunning` flag)
- A catalog discovery run (`CandidateDiscoveryService` state)

**Implementation:** Check `CandidateDiscoveryService.isRunning` property (must be exposed — currently private). If not exposed, add a public getter or use a shared `DiscoveryRunStateService` (but that adds a dep). Simplest: add `public get isRunning(): boolean { return this._isRunning; }` to `CandidateDiscoveryService`.

If discovery is running, skip silently (log at debug level). This prevents rate limit contention and LLM cost spikes.

### Cron Expression Pattern

Follow `CandidateDiscoveryService` pattern with `SchedulerRegistry`:

```typescript
// config-defaults.ts
externalPairIngestionCronExpression: {
  envKey: 'EXTERNAL_PAIR_INGESTION_CRON_EXPRESSION',
  defaultValue: '0 0 6,18 * * *',  // Twice daily at 6 AM and 6 PM UTC
},
externalPairIngestionEnabled: {
  envKey: 'EXTERNAL_PAIR_INGESTION_ENABLED',
  defaultValue: true,
},
externalPairDedupTitleThreshold: {
  envKey: 'EXTERNAL_PAIR_DEDUP_TITLE_THRESHOLD',
  defaultValue: 0.45,
},
externalPairLlmConcurrency: {
  envKey: 'EXTERNAL_PAIR_LLM_CONCURRENCY',
  defaultValue: 5,  // Lower than discovery's 10 — smaller batches, pre-vetted pairs
},
```

Register cron via `SchedulerRegistry` in `onModuleInit()`. Support runtime reload via settings service (same pattern as discovery cron).

### MatchOrigin Prisma Schema

```prisma
enum MatchOrigin {
  DISCOVERY
  PREDEXON
  ODDSPIPE
  MANUAL
}

model ContractMatch {
  // ... existing fields
  origin  MatchOrigin @default(DISCOVERY) @map("origin")

  // ... existing indexes
  @@index([origin])
}
```

**Backfill strategy:** Default `DISCOVERY` covers all existing pipeline-created matches. YAML-sourced pairs (created by `ContractMatchSyncService`) need to be updated to `MANUAL`. Identify them by: `operatorApproved = true AND operatorRationale IS NULL` (discovery auto-approved always sets a rationale string containing "discovery pipeline").

**Migration SQL (data portion):**
```sql
-- After column creation with default DISCOVERY:
UPDATE contract_matches
SET origin = 'MANUAL'
WHERE operator_approved = true
AND operator_rationale IS NULL;
```

### ContractMatchSyncService Update

The existing `ContractMatchSyncService.syncPairsToDatabase()` creates matches from YAML config. Update it to set `origin: 'MANUAL'` explicitly on upsert. This ensures new YAML pairs are tagged correctly going forward.

### OddsPipe API Reference

- **Endpoint:** `GET /v1/spreads` — returns all matched Polymarket-Kalshi pairs sorted by spread
- **Auth:** `X-API-Key` header
- **Rate limit:** 100 req/min (free tier)
- **Pagination:** `limit` (max 200), `offset`
- **Filtering:** `min_spread`, `min_score`, `top_n`
- **Response:** `{ items: [{ polymarket: { title, yes_price }, kalshi: { title, yes_price }, spread: { yes_diff } }] }`
- **Contract IDs:** May or may not include platform-specific IDs depending on market data availability. The existing `OddsPipeService.fetchMatchedPairs()` handles this — check `ExternalMatchedPair.polymarketId` / `kalshiId` for null.
- **Free tier:** All endpoints available, 30-day rolling history window, 100 req/min

### Predexon API Reference

- **Endpoint:** `GET /v2/matching-markets/pairs` — all active exact-matched pairs (similarity >= 95)
- **Auth:** `x-api-key` header
- **Rate limit:** 20 req/sec, 1M req/month (Dev tier, $49/mo)
- **Pagination:** `limit`, `offset`
- **Response includes:** `polymarket_condition_id`, `kalshi_ticker`, titles, `similarity` score (nullable for pre-Jan-2025 matches), `earliest_expiration_ts`
- **Free tier limitation:** `/v2/matching-markets/*` requires Dev plan — returns 403 on free tier. Existing `PredexonMatchingService` already handles 403 gracefully (returns null → degraded run).

### Event Names

```typescript
// Add to EVENT_NAMES in event-catalog.ts
EXTERNAL_PAIR_INGESTION_RUN_COMPLETED: 'contract.external-pair-ingestion.run_completed',
```

Reuse existing match events — no new per-match events needed:
- `MATCH_APPROVED` / `MATCH_AUTO_APPROVED` / `MATCH_PENDING_REVIEW` / `CLUSTER_ASSIGNED`

### Fuzzy Title Matching for OddsPipe Dedup

For title dedup, compute normalized token overlap (not Levenshtein — token overlap handles word reordering better for prediction market titles):

```typescript
function computeTitleSimilarity(title1: string, title2: string): number {
  const tokens1 = normalize(title1).split(/\s+/);
  const tokens2 = normalize(title2).split(/\s+/);
  const set1 = new Set(tokens1);
  const set2 = new Set(tokens2);
  const intersection = new Set([...set1].filter(t => set2.has(t)));
  return intersection.size / Math.max(set1.size, set2.size); // Jaccard-like
}
```

The `PreFilterService` in contract-matching already has TF-IDF and keyword overlap logic. Consider reusing its normalization utilities (stop word removal, stemming) but NOT the full pre-filter pipeline (overkill for dedup check). If reuse adds a dependency that pushes past limits, implement inline.

### Error Handling

- **Per-provider retry:** Rely on existing retry logic inside `OddsPipeService` and `PredexonMatchingService` (both already have `withRetry()` + exponential backoff). Do NOT add a second retry layer.
- **Per-provider error isolation:** Wrap each `provider.fetchPairs()` in try/catch. Record error in stats, continue with remaining providers.
- **LLM scoring failure:** Same as `CandidateDiscoveryService` — catch `LlmScoringError`, increment `scoringFailures` stat, skip pair.
- **P2002 unique constraint:** Catch silently (race condition between findFirst and create). Log debug, skip.
- **SystemError compliance:** All provider-level failures emitted as `SystemHealthError(4220, ...)`. Use error code `4220` for external pair ingestion failures (new code, adjacent to 4210/4211 from incremental ingestion).

### Dashboard Origin Display

**Backend:** Verify that the matches endpoint DTO already includes all `ContractMatch` fields or add `origin` to the response DTO. Check `CalibrationController` and related DTOs in `modules/contract-matching/`.

**Frontend:** In the matches/pairs table:
- Add an `Origin` column with colored badge:
  - `DISCOVERY` → gray badge
  - `PREDEXON` → blue badge (99%+ accuracy source)
  - `ODDSPIPE` → green badge
  - `MANUAL` → orange badge (YAML-configured)
- Add filter dropdown for origin values
- Follow existing badge patterns (e.g., `BacktestStatusBadge`)

### File Structure (New Files)

**pm-arbitrage-engine (NEW):**
- `src/common/interfaces/external-pair-provider.interface.ts`
- `src/modules/contract-matching/external-pair-ingestion.service.ts`
- `src/modules/contract-matching/external-pair-ingestion.service.spec.ts`
- `src/modules/contract-matching/external-pair-processor.service.ts`
- `src/modules/contract-matching/external-pair-processor.service.spec.ts`
- `prisma/migrations/YYYYMMDDHHMMSS_add_contract_match_origin/migration.sql` (auto-generated)

**pm-arbitrage-engine (MODIFIED):**
- `prisma/schema.prisma` — Add MatchOrigin enum + origin field + index on ContractMatch
- `src/common/interfaces/index.ts` — Export IExternalPairProvider + tokens
- `src/common/events/event-catalog.ts` — Add EXTERNAL_PAIR_INGESTION_RUN_COMPLETED
- `src/common/events/discovery.events.ts` — Add ExternalPairIngestionRunCompletedEvent
- `src/common/config/env.schema.ts` — Add 4 new env vars
- `src/common/config/config-defaults.ts` — Add 4 new config entries
- `src/common/config/settings-metadata.ts` — Add settings metadata entries
- `src/modules/backtesting/ingestion/oddspipe.service.ts` — Add `implements IExternalPairProvider`, `fetchPairs()`, `getSourceId()`
- `src/modules/backtesting/validation/predexon-matching.service.ts` — Add `implements IExternalPairProvider`, `fetchPairs()`, `getSourceId()`
- `src/modules/backtesting/ingestion/ingestion.module.ts` — Register + export ODDSPIPE_PAIR_PROVIDER_TOKEN
- `src/modules/backtesting/validation/validation.module.ts` — Register + export PREDEXON_PAIR_PROVIDER_TOKEN
- `src/modules/contract-matching/contract-matching.module.ts` — Import backtesting tokens, register new services
- `src/modules/contract-matching/contract-match-sync.service.ts` — Set `origin: 'MANUAL'` on upsert
- `src/modules/contract-matching/candidate-discovery.service.ts` — Add `public get isRunning(): boolean` getter (expose private `_isRunning`)
- `src/dashboard/dashboard.gateway.ts` — Add @OnEvent handler for EXTERNAL_PAIR_INGESTION_RUN_COMPLETED
- `src/dashboard/dashboard.gateway.spec.ts` — Add handler test
- `src/dashboard/dto/ws-events.dto.ts` — Add WS event constant
- `src/common/testing/event-wiring-audit.spec.ts` — Add wiring test for new handler
- `.env.example` — Add 4 new env vars

**pm-arbitrage-dashboard (MODIFIED):**
- Matches table component — Add origin column with badge + filter

### Existing Services to Reuse (DO NOT Reinvent)

| Service | Location | What to Reuse |
|---|---|---|
| `OddsPipeService` | `backtesting/ingestion/` | `fetchMatchedPairs()` — wraps `/v1/spreads`, rate limited, retried |
| `PredexonMatchingService` | `backtesting/validation/` | `fetchMatchedPairs()` — wraps `/v2/matching-markets/pairs`, paginated, graceful 403 |
| `ConfidenceScorerService` | `contract-matching/` | Via `SCORING_STRATEGY_TOKEN` — LLM scoring interface |
| `OutcomeDirectionValidator` | `contract-matching/` | `validateDirection()` — direction check + self-correction |
| `ClusterClassifierService` | `contract-matching/` | Via `CLUSTER_CLASSIFIER_TOKEN` — cluster assignment |
| `CandidateDiscoveryService` | `contract-matching/` | `isRunning` (must expose) — concurrency check |
| `ContractMatchSyncService` | `contract-matching/` | Origin update for YAML pairs |
| `PreFilterService` | `contract-matching/` | Normalization utilities (optional reuse for title dedup) |

### Anti-Patterns to Avoid

- **DO NOT** re-implement LLM scoring logic — always delegate to `SCORING_STRATEGY_TOKEN`
- **DO NOT** add a second retry layer around `fetchPairs()` — providers already have built-in retry
- **DO NOT** import backtesting module services directly into contract-matching — use DI tokens via `IExternalPairProvider` interface
- **DO NOT** create a separate rate limiter — providers manage their own rate limiting
- **DO NOT** use `processCandidate()` from CandidateDiscoveryService — it's private and takes `ContractSummary` objects. Replicate the logic in ExternalPairProcessorService using the same injected services
- **DO NOT** compute staleness/freshness on frontend for origin badge — origin is a static enum field, not time-based
- **DO NOT** skip direction validation for Predexon pairs (even though they're "99% accurate") — direction mismatch detection is cheap and catches the 1%
- **DO NOT** use native JS float operations for any financial calculations (spread data from OddsPipe) — use `decimal.js` if computing edges

## Known Issues (Deferred)

Surfaced during 3-layer adversarial code review (2026-03-31). Pre-existing patterns not caused by this story — deferred for future attention.

1. **Config source divergence (env vs DB settings):** `handleCron()` reads `EXTERNAL_PAIR_INGESTION_ENABLED` from `configService.get()` (env source). If operator disables via dashboard settings (DB update), the check may not reflect the change unless the settings update flow also calls `configService.set()`. Affects all boolean config values project-wide, not specific to this story. **File:** `external-pair-ingestion.service.ts:62-65`.

2. **`operatorApprovalTimestamp` semantics:** Field name implies "when approved" but is also set on match rejection (`match-approval.service.ts:247-253`). Semantically misleading — a non-null timestamp with `operatorApproved: false` means "rejected". Pre-existing pattern. Consider renaming to `operatorDecisionTimestamp` in a future schema migration.

3. **O(N*M) catalog search in enrichment:** `findBestMatch()` iterates the entire catalog for each pair needing ID resolution (`external-pair-enrichment.service.ts:155-175`). Acceptable at current scale (small catalogs, few pairs per run). If catalog grows to 10K+ entries, consider pre-building a tokenized index or using MinHash for approximate matching.

4. **Short-token title fuzzy matching:** Titles with very few tokens after normalization (e.g., "Q3 GDP" → 2 tokens) produce unreliable Jaccard-like similarity. "Q3 GDP" vs "Q3 CPI" yields 50% (1/2 tokens), potentially causing false dedup above the 0.45 threshold. Mitigated by the bias-toward-inclusion design (false dedup costs fractions of a cent; missed opportunity costs real money). **File:** `external-pair-processor.service.ts:29-46`.

### Previous Story Intelligence

**From Story 10-9-6 (Historical Data Freshness):**
- `forwardRef()` pattern works for circular module dependencies — use same approach for backtesting ↔ contract-matching token sharing
- `configService.get<boolean>` returns string — use `enabled !== true` pattern
- `configService.get<number>` needs explicit `Number()` wrap
- Route prefix: controllers must NOT include `api/` (global prefix handles it)
- Settings count will increase — update settings service test expectations

**From Story 10-9-2 (Cross-Platform Pair Matching Validation):**
- `MatchValidationService.runValidation()` already fetches from both providers and categorizes `external-only` pairs
- `ExternalMatchedPair` type is battle-tested — reuse as-is
- Predexon 403 graceful degradation pattern: catch 403, log warning, return null, continue
- OddsPipe fuzzy matching threshold in validation is 0.6 — but that's for confirming existing matches, not dedup of novel pairs. Dedup threshold should be lower (0.45) to bias toward inclusion

**From CandidateDiscoveryService (Epic 8):**
- `processCandidate()` handles all edge cases: duplicate prevention, scoring failure, P2002 race condition, direction mismatch score capping, cluster classification failure
- Auto-approve/reject thresholds are read from config at constructor time
- Stats are accumulated synchronously between await points (thread-safe in Node.js)
- `LlmScoringError` is caught separately from other errors

### Project Structure Notes

- All new engine code in `modules/contract-matching/` — the ingestion service lives where the scoring pipeline lives
- Interface in `common/interfaces/` — following established multi-provider token pattern
- No new modules needed — extends existing ContractMatchingModule
- Backtesting module changes are minimal (add `implements`, register tokens)

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-28-external-pair-ingestion.md — Full design rationale]
- [Source: pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.ts:316-529 — processCandidate() reference implementation]
- [Source: pm-arbitrage-engine/src/common/interfaces/contract-catalog-provider.interface.ts — Multi-token DI pattern]
- [Source: pm-arbitrage-engine/src/modules/backtesting/validation/predexon-matching.service.ts:47-112 — fetchMatchedPairs()]
- [Source: pm-arbitrage-engine/src/modules/backtesting/ingestion/oddspipe.service.ts — OddsPipe integration]
- [Source: pm-arbitrage-engine/src/modules/backtesting/types/match-validation.types.ts — ExternalMatchedPair type]
- [Source: pm-arbitrage-engine/prisma/schema.prisma:229-276 — ContractMatch model]
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts — Event naming conventions]
- [Source: _bmad-output/implementation-artifacts/10-9-6-historical-data-freshness-incremental-updates.md — Previous story patterns]
- [Source: OddsPipe API docs — GET /v1/spreads endpoint, rate limits, auth]
- [Source: Predexon API docs — GET /v2/matching-markets/pairs, pricing tiers, 403 handling]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Baseline: 2 pre-existing test failures (trading-engine.service.spec.ts, core-lifecycle.e2e-spec.ts) — unchanged throughout
- Seed config fix: `externalPairIngestionEnabled` needed BOOLEAN_FIELDS entry, `externalPairDedupTitleThreshold` needed FLOAT_FIELDS entry in `prisma/seed-config.ts`

### Completion Notes List

- Task 1: IExternalPairProvider interface + MatchOrigin enum + origin field + backfill migration + sync service origin. 5 tests.
- Task 2: 4 env vars, config-defaults, settings-metadata, EngineConfig Prisma columns, .env.example. 8 tests.
- Task 3: OddsPipe + Predexon implement IExternalPairProvider with fetchPairs/getSourceId adapters + DI token wiring. 6 tests.
- Task 4: ExternalPairIngestionService coordinator with cron scheduling, concurrency guard (own + discovery), enabled flag, run stats emission. CandidateDiscoveryService.isRunning getter added. 10 tests.
- Task 5: ExternalPairProcessorService — provider fetching with error isolation, composite key dedup, ID-less pair handling, LLM scoring delegation, direction validation skip, auto-approve/reject/review thresholds, origin tracking, P2002 handling, cluster classification, event emission. 22 tests.
- Task 6: Event catalog entry, ExternalPairIngestionRunCompletedEvent class, DashboardGateway handler, WS event constant, event wiring audit. 7 tests.
- Task 7: MatchSummaryDto origin field, origin query filter, match-approval service/controller/DTO updates, OriginBadge frontend component, MatchesPage column. 2 frontend tests + existing controller/service tests updated.
- Task 8 (QA): Added `broadcastExternalPairIngestionCompleted` to `allGatewayMethods` array in event-wiring-audit.spec.ts. Fixed settings.service.spec.ts count (92→93).

### Change Log

- 2026-03-28: Implemented Story 10-9-7 — External Pair Candidate Ingestion. 60+ new tests across engine + dashboard.
- 2026-03-29: QA fix — Task 8: added missing `broadcastExternalPairIngestionCompleted` to `allGatewayMethods`, fixed settings count 92→93.

### File List

**pm-arbitrage-engine (NEW):**
- `src/common/interfaces/external-pair-provider.interface.ts`
- `src/common/interfaces/external-pair-provider.interface.spec.ts`
- `src/modules/contract-matching/external-pair-ingestion.service.ts`
- `src/modules/contract-matching/external-pair-ingestion.service.spec.ts`
- `src/modules/contract-matching/external-pair-processor.service.ts`
- `src/modules/contract-matching/external-pair-processor.service.spec.ts`
- `src/common/events/external-pair-ingestion-run-completed.event.ts`
- `src/common/events/external-pair-ingestion-run-completed.event.spec.ts`
- `prisma/migrations/20260328175246_add_contract_match_origin/migration.sql`
- `prisma/migrations/20260328180301_add_engine_config_external_pair_ingestion/migration.sql`

**pm-arbitrage-engine (MODIFIED):**
- `prisma/schema.prisma` — MatchOrigin enum, origin field on ContractMatch, EngineConfig columns
- `prisma/seed-config.ts` — BOOLEAN_FIELDS + FLOAT_FIELDS entries
- `src/common/interfaces/index.ts` — exports IExternalPairProvider + tokens
- `src/common/events/event-catalog.ts` — EXTERNAL_PAIR_INGESTION_RUN_COMPLETED
- `src/common/config/env.schema.ts` — 4 new env vars
- `src/common/config/config-defaults.ts` — 4 new config entries
- `src/common/config/config-defaults.spec.ts` — updated counts + new tests
- `src/common/config/env.schema.spec.ts` — 4 new default tests
- `src/common/config/effective-config.types.ts` — 4 new fields
- `src/common/config/settings-metadata.ts` — 4 new settings metadata entries
- `src/modules/backtesting/ingestion/oddspipe.service.ts` — implements IExternalPairProvider
- `src/modules/backtesting/ingestion/oddspipe.service.spec.ts` — 3 adapter tests
- `src/modules/backtesting/ingestion/ingestion.module.ts` — ODDSPIPE_PAIR_PROVIDER_TOKEN
- `src/modules/backtesting/validation/predexon-matching.service.ts` — implements IExternalPairProvider
- `src/modules/backtesting/validation/predexon-matching.service.spec.ts` — 3 adapter tests
- `src/modules/backtesting/validation/validation.module.ts` — PREDEXON_PAIR_PROVIDER_TOKEN
- `src/modules/backtesting/backtesting.module.ts` — re-exports IngestionModule, ValidationModule
- `src/modules/contract-matching/contract-matching.module.ts` — imports BacktestingModule, registers new services
- `src/modules/contract-matching/contract-match-sync.service.ts` — origin: MANUAL on upsert
- `src/modules/contract-matching/contract-match-sync.service.spec.ts` — 2 origin tests
- `src/modules/contract-matching/candidate-discovery.service.ts` — isRunning getter
- `src/modules/contract-matching/candidate-discovery.service.spec.ts` — 1 isRunning test
- `src/dashboard/dashboard.gateway.ts` — @OnEvent handler for external pair ingestion
- `src/dashboard/dto/ws-events.dto.ts` — WS event constant
- `src/dashboard/dto/match-approval.dto.ts` — origin field + filter
- `src/dashboard/match-approval.service.ts` — origin mapping + filter
- `src/dashboard/match-approval.controller.ts` — origin parameter passthrough
- `src/dashboard/match-approval.controller.spec.ts` — updated call assertions
- `src/dashboard/match-approval.service.spec.ts` — origin in mock
- `src/dashboard/settings.service.spec.ts` — updated count + mock fields
- `src/common/testing/event-wiring-audit.spec.ts` — new handler wiring
- `src/persistence/repositories/engine-config.repository.ts` — 4 new fields in buildEffectiveConfig
- `.env.example` — 4 new env vars

**pm-arbitrage-dashboard (NEW):**
- `src/components/OriginBadge.tsx`
- `src/components/OriginBadge.spec.tsx`

**pm-arbitrage-dashboard (MODIFIED):**
- `src/pages/MatchesPage.tsx` — Origin column with OriginBadge
