# Story 8.2: Semantic Contract Matching & Confidence Scoring

Status: done

## Story

As an operator,
I want the system to automatically identify potential cross-platform contract matches using semantic analysis,
So that I can scale beyond 20-30 manually curated pairs to 50+.

## Acceptance Criteria

1. **Given** contract descriptions are available from both platforms
   **When** the confidence scorer analyzes a potential pair
   **Then** it produces a confidence score (0-100%) based on LLM semantic analysis via the `IScoringStrategy` interface
   **And** `ConfidenceScorerService` delegates scoring to a pluggable `IScoringStrategy` implementation so the algorithm can be swapped without changing consumers
   [Source: epics.md#Story-8.2; FR-AD-05, FR-CM-02]

2. **Given** the initial `IScoringStrategy` implementation
   **When** the LLM scorer analyzes a pair
   **Then** it uses a cost-efficient primary model (Gemini 2.5 Flash via `@google/genai`) for scoring
   **And** optionally escalates to a higher-quality model (Claude Haiku 4.5 via `@anthropic-ai/sdk`) when the primary returns a score in the configurable ambiguous zone (e.g., 60-84%)
   **And** LLM provider, model selection, and escalation thresholds are configurable via environment variables
   [Source: epics.md#Story-8.2; sprint-change-proposal-2026-03-09.md#Section-4.2]

3. **Given** deterministic string-based analysis is needed for the candidate narrowing stage
   **When** the `PreFilterService` is invoked
   **Then** it produces a similarity score using TF-IDF/cosine similarity on descriptions and resolution criteria keyword overlap
   **And** the `PreFilterService` is independently testable with mock contract data
   [Source: epics.md#Story-8.2; sprint-change-proposal-2026-03-09.md — PreFilterService created in 8.2, wired into discovery pipeline in 8.4]

4. **Given** a confidence score is produced and is ≥85% (configurable threshold)
   **When** the auto-approve workflow runs
   **Then** the match is auto-approved (Prisma update + `MatchApprovedEvent` emission, same logic as `MatchApprovalService.approveMatch()`) with rationale documenting auto-approval source and score
   **And** a `MatchAutoApprovedEvent` is emitted
   **And** if the match is already approved, scoring is skipped silently (idempotency guard)
   [Source: epics.md#Story-8.2; FR-AD-06]

5. **Given** a confidence score is produced and is <85%
   **When** the review workflow runs
   **Then** the match enters the pending queue for operator review via dashboard
   **And** a `MatchPendingReviewEvent` is emitted
   [Source: epics.md#Story-8.2; FR-AD-06]

6. **Given** the LLM API returns an error during scoring
   **When** the `ConfidenceScorerService` handles the failure
   **Then** an `LlmScoringError` (code range 4100-4199) is thrown with context (model, matchId, error details)
   **And** the error carries a retry strategy for upstream consumers
   [Source: sprint-change-proposal-2026-03-09.md#Section-4.3; architecture.md error hierarchy]

## Tasks / Subtasks

- [x] **Task 1: `IScoringStrategy` interface** (AC: #1)
  - [x] Create `scoring-strategy.interface.ts` in `common/interfaces/`
  - [x] Define `IScoringStrategy` with `scoreMatch(polyDescription, kalshiDescription, metadata?)` returning `Promise<ScoringResult>` where `ScoringResult = { score: number; confidence: 'high' | 'medium' | 'low'; reasoning: string; model: string; escalated: boolean }`
  - [x] Export from `common/interfaces/` barrel (create `index.ts` if needed, or add to existing exports)

- [x] **Task 2: `LlmScoringError` error class** (AC: #6)
  - [x] Add `LLM_SCORING_ERROR_CODES` to `llm-scoring-error.ts` (range 4100-4199): `LLM_API_FAILURE: 4100`, `LLM_RESPONSE_PARSE_FAILURE: 4101`, `LLM_TIMEOUT: 4102`, `LLM_RATE_LIMITED: 4103`
  - [x] Create `llm-scoring-error.ts` in `common/errors/` extending `SystemHealthError` with `model` and `provider` fields
  - [x] Export from `common/errors/index.ts` barrel

- [x] **Task 3: New domain events** (AC: #4, #5)
  - [x] Add `MATCH_AUTO_APPROVED` and `MATCH_PENDING_REVIEW` to `EVENT_NAMES` in `event-catalog.ts`
  - [x] Create `match-auto-approved.event.ts` extending `BaseEvent` with fields: `matchId`, `confidenceScore`, `model`, `escalated`
  - [x] Create `match-pending-review.event.ts` extending `BaseEvent` with fields: `matchId`, `confidenceScore`, `model`, `escalated`
  - [x] Export both from `common/events/index.ts` barrel

- [x] **Task 4: LLM scoring strategy implementation** (AC: #1, #2)
  - [x] Install `@google/genai` and `@anthropic-ai/sdk` as dependencies
  - [x] Create `llm-scoring.strategy.ts` in `modules/contract-matching/` implementing `IScoringStrategy`
  - [x] Implement primary scoring via Gemini 2.5 Flash: build a structured prompt with both contract descriptions, parse JSON response for score + reasoning
  - [x] Implement escalation logic: if primary score falls in ambiguous zone (configurable via `LLM_ESCALATION_MIN` / `LLM_ESCALATION_MAX` env vars), re-score with Claude Haiku 4.5. If escalation API fails, throw `LlmScoringError` (do NOT fall back to primary score — preserve primary score in error metadata for debugging)
  - [x] Validate LLM-returned score is within 0-100 range; if outside range, throw `LlmScoringError` with code `LLM_RESPONSE_PARSE_FAILURE`
  - [x] Wrap all LLM API errors in `LlmScoringError` with appropriate code
  - [x] Read config from `ConfigService`: `LLM_PRIMARY_PROVIDER`, `LLM_PRIMARY_MODEL`, `LLM_PRIMARY_API_KEY`, `LLM_ESCALATION_PROVIDER`, `LLM_ESCALATION_MODEL`, `LLM_ESCALATION_API_KEY`, `LLM_ESCALATION_MIN`, `LLM_ESCALATION_MAX`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_MS`

- [x] **Task 5: `PreFilterService`** (AC: #3)
  - [x] Create `pre-filter.service.ts` in `modules/contract-matching/`
  - [x] Implement `computeSimilarity(descriptionA, descriptionB)` returning `{ tfidfScore: number; keywordOverlap: number; combinedScore: number }`
  - [x] TF-IDF + cosine similarity: tokenize descriptions, build term-frequency vectors, compute cosine similarity (pure TypeScript, no external NLP library — descriptions are short English strings)
  - [x] Keyword overlap: extract resolution-relevant keywords, compute Jaccard similarity
  - [x] Expose `filterCandidates(sourceContract, candidateContracts, threshold)` returning ranked candidates above threshold

- [x] **Task 6: `ConfidenceScorerService`** (AC: #1, #4, #5)
  - [x] Create `confidence-scorer.service.ts` in `modules/contract-matching/`
  - [x] Inject `IScoringStrategy` (via NestJS custom provider token), `KnowledgeBaseService`, `PrismaService`, `EventEmitter2`, `ConfigService`
  - [x] Implement `scoreMatch(matchId)`: fetch ContractMatch from DB via `PrismaService` → guard: skip if already approved or if descriptions are null → call strategy → persist score via `KnowledgeBaseService.updateConfidenceScore()` → if score >= threshold: auto-approve via inline Prisma update + emit `MatchApprovedEvent` + emit `MatchAutoApprovedEvent` → if score < threshold: emit `MatchPendingReviewEvent`
  - [x] Auto-approve threshold configurable via `LLM_AUTO_APPROVE_THRESHOLD` env var (default: 85)
  - [x] Auto-approval logic is self-contained (Prisma update + event emission) — does NOT import `MatchApprovalService` from `DashboardModule` (see Dev Notes for rationale)

- [x] **Task 7: Module registration and DI wiring** (AC: #1)
  - [x] Register `IScoringStrategy` as custom provider in `ContractMatchingModule` using token + `useExisting: LlmScoringStrategy`
  - [x] Add `ConfidenceScorerService`, `PreFilterService`, `LlmScoringStrategy` to `ContractMatchingModule` providers
  - [x] Add `ConfidenceScorerService`, `PreFilterService` to exports (Story 8.4 needs them)
  - [x] No new module imports needed — auto-approval uses `PrismaService` directly (already available via `PersistenceModule`)

- [x] **Task 8: Environment variable configuration** (AC: #2)
  - [x] Add all LLM env vars to `.env.example` with comments
  - [x] Add to `.env.development` with placeholder values

- [x] **Task 9: Tests** (AC: #1-6)
  - [x] `llm-scoring.strategy.spec.ts` — 13 tests: primary scoring happy path, escalation trigger in ambiguous zone (3 boundary tests), no escalation for clear scores (2 tests), API errors (2 tests), response parse failures (3 tests), metadata passthrough
  - [x] `pre-filter.service.spec.ts` — 11 tests: identical/unrelated descriptions, keyword overlap, filterCandidates ranking/threshold, empty/whitespace/single-word inputs, combined score weighted average
  - [x] `confidence-scorer.service.spec.ts` — 9 tests: auto-approve + events, boundary (85), pending review, score persistence, match not found, already approved skip, null descriptions skip, strategy error propagation
  - [x] `llm-scoring-error.spec.ts` — 8 tests: construction, code ranges, retry strategies per code, metadata, prototype chain
  - [x] `match-auto-approved.event.spec.ts` — 3 tests: construction, correlationId, escalated field
  - [x] `match-pending-review.event.spec.ts` — 3 tests: construction, correlationId, escalated field

## Dev Notes

### IScoringStrategy Interface

**Location:** `src/common/interfaces/scoring-strategy.interface.ts`

```typescript
export interface ScoringResult {
  score: number;          // 0-100
  confidence: 'high' | 'medium' | 'low';
  reasoning: string;      // LLM's explanation
  model: string;          // e.g. 'gemini-2.5-flash'
  escalated: boolean;     // true if escalation model was used
}

export interface IScoringStrategy {
  scoreMatch(
    polyDescription: string,
    kalshiDescription: string,
    metadata?: { resolutionDate?: Date; category?: string },
  ): Promise<ScoringResult>;
}
```

This follows the module dependency rule: interfaces live in `common/interfaces/`, implementations in `modules/`. [Source: CLAUDE.md#Module Dependency Rules; architecture.md lines 596-606]

### LLM SDK Integration

**Primary — Gemini 2.5 Flash:**
- Package: `@google/genai` (v1.44.0+, GA since May 2025) [Source: web research — npmjs.com, googleapis/js-genai GitHub]
- Usage: `new GoogleGenAI({apiKey}); await ai.models.generateContent({model, contents})`
- Legacy `@google/generative-ai` is deprecated — do NOT use it

**Escalation — Claude Haiku 4.5:**
- Package: `@anthropic-ai/sdk` (v0.78.0+) [Source: web research — npmjs.com @anthropic-ai/sdk]
- Usage: `new Anthropic({apiKey}); await client.messages.create({model, max_tokens, messages})`
- Model ID: `claude-haiku-4-5-20251001` [Source: CLAUDE.md environment section]

**Prompt design:** Send a structured system prompt asking the LLM to compare two prediction market contract descriptions and return a JSON object with `{score, confidence, reasoning}`. Include settlement date and category if available as additional context. Request that the LLM focus on: (1) whether they refer to the same real-world event, (2) whether settlement criteria match, (3) date alignment.

**Response parsing:** Parse JSON from LLM response text. If JSON parsing fails, throw `LlmScoringError` with code `LLM_RESPONSE_PARSE_FAILURE`. Use a regex or `JSON.parse` on extracted JSON block.

### Escalation Logic

```
Primary score in [LLM_ESCALATION_MIN, LLM_ESCALATION_MAX] → escalate
Primary score < LLM_ESCALATION_MIN → clearly bad match, no escalation needed
Primary score > LLM_ESCALATION_MAX → clearly good match, no escalation needed
```

Default env values: `LLM_ESCALATION_MIN=60`, `LLM_ESCALATION_MAX=84`. These are configurable — the operator tunes them based on observed accuracy.

The escalation model's score **replaces** the primary score entirely in the returned `ScoringResult` (it's the higher-quality assessment). The `ScoringResult.escalated` flag is set to `true` and `ScoringResult.model` reflects the escalation model.

**Escalation failure:** If the escalation API call fails, throw `LlmScoringError` with code `LLM_API_FAILURE`. Do NOT fall back to the primary score — the primary was ambiguous, so using it risks a bad approval decision. Preserve the primary score in the error's `metadata` field for debugging: `{ primaryScore, primaryModel }`.

### ConfidenceScorerService Flow

**Location:** `src/modules/contract-matching/confidence-scorer.service.ts`

**Injects:** `@Inject('IScoringStrategy')`, `KnowledgeBaseService`, `PrismaService`, `EventEmitter2`, `ConfigService`

```
scoreMatch(matchId) →
  1. Fetch ContractMatch from DB via PrismaService (need polymarketDescription, kalshiDescription, operatorApproved)
  2. Guard: if match.operatorApproved === true → log + return early (idempotency)
  3. Guard: if polymarketDescription or kalshiDescription is null → log warning + return early (can't score without descriptions)
  4. Call IScoringStrategy.scoreMatch(polyDesc, kalshiDesc, {resolutionDate})
  5. Persist score via KnowledgeBaseService.updateConfidenceScore(matchId, result.score)
  6. If score >= threshold (default 85, configurable via LLM_AUTO_APPROVE_THRESHOLD):
     a. Auto-approve via PrismaService: contractMatch.updateMany({where: {matchId, operatorApproved: false}, data: {operatorApproved: true, operatorRationale, operatorApprovalTimestamp}})
     b. Emit MatchApprovedEvent (same event as manual approval — keeps monitoring/audit consistent)
     c. Emit MatchAutoApprovedEvent (scoring-specific event with score, model, escalated)
  7. If score < threshold:
     - Emit MatchPendingReviewEvent
  8. Return ScoringResult
```

**Auto-approval is self-contained — does NOT import `MatchApprovalService` from `DashboardModule`.** Rationale: architecture dependency rules do not list `modules/contract-matching/ → dashboard/` as an allowed import direction. The `MatchApprovalService.approveMatch()` logic is a simple Prisma update + event emission (~15 lines). Replicating this inline in `ConfidenceScorerService` avoids introducing a new cross-module dependency that could create circular issues as `DashboardModule` grows. The same `MatchApprovedEvent` is emitted, so monitoring/audit consumers see no difference. [Source: architecture.md lines 596-606; dashboard/match-approval.service.ts lines 70-134]

**Escalation/model data is NOT persisted to DB** — the `ContractMatch` schema stores only `confidenceScore` (the final numeric score). Which model produced the score and whether escalation occurred is captured in the emitted `MatchAutoApprovedEvent` / `MatchPendingReviewEvent` events (available to monitoring/audit consumers). If operator needs this data queryable, a schema migration can be added in a future story.

### PreFilterService Design

**Location:** `src/modules/contract-matching/pre-filter.service.ts`

Pure computation — no DB access, no DI dependencies except `Logger`. This is intentional: Story 8.4's `CandidateDiscoveryService` will feed it contract catalog data.

**TF-IDF implementation (inline, no external library):**
1. Tokenize: lowercase, strip punctuation (`/[^a-z0-9\s]/g` → ''), split on whitespace, filter stop words
2. Term frequency: count occurrences per document
3. IDF: `log(2 / (1 + docsContaining))` (only 2 docs per comparison)
4. TF-IDF vectors: `tf * idf` for each term
5. Cosine similarity: `dot(A, B) / (||A|| * ||B||)`. If both vectors are zero (empty after stop word removal), return 0.

Descriptions are short English strings (typically 10-50 words). A full NLP library is overkill. Pure TypeScript implementation with a hardcoded stop-word list is sufficient and avoids adding heavy dependencies.

**Stop word list (hardcoded constant):**
```typescript
const STOP_WORDS = new Set([
  'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
  'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
  'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
  'could', 'should', 'may', 'might', 'shall', 'can', 'this', 'that',
  'these', 'those', 'it', 'its', 'not', 'no', 'if', 'then', 'than',
  'so', 'as', 'up', 'out', 'about', 'into', 'over', 'after', 'before',
]);
```

**Keyword extraction** for resolution-relevant terms:
```typescript
function extractKeywords(text: string): string[] {
  const dates = text.match(/\d{4}[-/]\d{1,2}[-/]\d{1,2}/g) || [];
  const percentages = text.match(/\d+\.?\d*%/g) || [];
  const outcomes = (text.match(/\b(yes|no|true|false|win|lose|above|below|over|under)\b/gi) || []);
  const numbers = text.match(/\b\d+\.?\d*\b/g) || [];
  return [...dates, ...percentages, ...outcomes, ...numbers].map(s => s.toLowerCase());
}
```

**Keyword overlap:** Compute Jaccard similarity on extracted keywords: `|intersection| / |union|`. If union is empty, return 0.

**Combined score:** `combinedScore = (tfidfWeight * tfidfScore) + (keywordWeight * keywordOverlap)` where `tfidfWeight = 0.6`, `keywordWeight = 0.4` (defaults, adjustable in implementation).

**`filterCandidates(sourceContract, candidates, threshold)`:** Returns candidates sorted by `combinedScore` descending, filtered to those above `threshold`.

### LlmScoringError Design

**Location:** `src/common/errors/llm-scoring-error.ts`

```typescript
export const LLM_SCORING_ERROR_CODES = {
  LLM_API_FAILURE: 4100,
  LLM_RESPONSE_PARSE_FAILURE: 4101,
  LLM_TIMEOUT: 4102,
  LLM_RATE_LIMITED: 4103,
} as const;
```

Extends `SystemHealthError`. Adds `model: string` and `provider: string` fields. Default retry strategy: `{ maxRetries: 2, initialDelayMs: 1000, maxDelayMs: 5000 }` for API failures; no retry for parse failures. [Source: system-error.ts RetryStrategy interface; sprint-change-proposal-2026-03-09.md#Section-4.3]

### Event Additions

In `event-catalog.ts` after `RESOLUTION_DIVERGED`:
```typescript
// [Story 8.2] Confidence Scoring Events
MATCH_AUTO_APPROVED: 'contract.match.auto_approved',
MATCH_PENDING_REVIEW: 'contract.match.pending_review',
```

Event classes follow `MatchApprovedEvent` / `MatchRejectedEvent` pattern (extend `BaseEvent`, constructor with fields + optional correlationId). [Source: common/events/match-approved.event.ts]

### Environment Variables

Add to `.env.example`:
```bash
# LLM Confidence Scoring (Story 8.2)
LLM_PRIMARY_PROVIDER=gemini                  # Primary LLM provider: gemini | anthropic
LLM_PRIMARY_MODEL=gemini-2.5-flash           # Primary model ID
LLM_PRIMARY_API_KEY=                          # API key for primary provider
LLM_ESCALATION_PROVIDER=anthropic            # Escalation LLM provider: gemini | anthropic
LLM_ESCALATION_MODEL=claude-haiku-4-5-20251001  # Escalation model ID
LLM_ESCALATION_API_KEY=                      # API key for escalation provider
LLM_ESCALATION_MIN=60                        # Lower bound of ambiguous zone (score below = no escalation)
LLM_ESCALATION_MAX=84                        # Upper bound of ambiguous zone (score above = no escalation)
LLM_AUTO_APPROVE_THRESHOLD=85                # Confidence score >= this triggers auto-approval
LLM_MAX_TOKENS=1024                          # Max tokens for LLM response
LLM_TIMEOUT_MS=30000                         # LLM API call timeout in ms
```

### Module Registration Changes

In `contract-matching.module.ts`:
```typescript
export const SCORING_STRATEGY_TOKEN = 'IScoringStrategy';

@Module({
  providers: [
    ContractPairLoaderService,
    ContractMatchSyncService,
    KnowledgeBaseService,
    PreFilterService,
    LlmScoringStrategy,
    { provide: SCORING_STRATEGY_TOKEN, useClass: LlmScoringStrategy },
    ConfidenceScorerService,
  ],
  exports: [
    ContractPairLoaderService,
    KnowledgeBaseService,
    ConfidenceScorerService,
    PreFilterService,
  ],
})
```

No new module imports needed. `PrismaService` is already globally available via `PersistenceModule`. Auto-approval uses `PrismaService` directly, avoiding any `DashboardModule` dependency.

The `SCORING_STRATEGY_TOKEN` string token allows swapping `IScoringStrategy` implementation without changing consumers. `ConfidenceScorerService` injects via `@Inject(SCORING_STRATEGY_TOKEN)`. Export the token so tests and Story 8.4 can reference it. [Source: NestJS custom providers docs; architecture.md "pluggable scoring strategy"]

### Scope Boundaries — What This Story Does NOT Do

- **No discovery pipeline / batch processing.** Story 8.4 wires `PreFilterService` and `ConfidenceScorerService` into the scheduled discovery pipeline.
- **No `IContractCatalogProvider` interface.** Story 8.4 creates it.
- **No `CandidateDiscoveryService` or `CatalogSyncService`.** Story 8.4.
- **No resolution feedback loop.** Story 8.3 handles calibration and feedback.
- **No REST endpoints for scoring.** The scorer is called programmatically (by Story 8.4's pipeline). Dashboard already shows confidence scores (wired in Story 8.1).
- **No scheduled job.** Story 8.4 adds the `@nestjs/schedule` cron.

### Project Structure Notes

Files to create:
- `src/common/interfaces/scoring-strategy.interface.ts`
- `src/common/errors/llm-scoring-error.ts`
- `src/common/events/match-auto-approved.event.ts`
- `src/common/events/match-pending-review.event.ts`
- `src/modules/contract-matching/llm-scoring.strategy.ts`
- `src/modules/contract-matching/llm-scoring.strategy.spec.ts`
- `src/modules/contract-matching/pre-filter.service.ts`
- `src/modules/contract-matching/pre-filter.service.spec.ts`
- `src/modules/contract-matching/confidence-scorer.service.ts`
- `src/modules/contract-matching/confidence-scorer.service.spec.ts`
- `src/common/errors/llm-scoring-error.spec.ts`
- `src/common/events/match-auto-approved.event.spec.ts`
- `src/common/events/match-pending-review.event.spec.ts`

Files to modify:
- `src/common/errors/system-health-error.ts` — add `LLM_SCORING_ERROR_CODES` (4100-4103)
- `src/common/errors/index.ts` — export `LlmScoringError` and `LLM_SCORING_ERROR_CODES`
- `src/common/events/event-catalog.ts` — add `MATCH_AUTO_APPROVED`, `MATCH_PENDING_REVIEW`
- `src/common/events/index.ts` — export new event classes
- `src/modules/contract-matching/contract-matching.module.ts` — register new providers/exports, add imports
- `.env.example` — add LLM configuration vars
- `.env.development` — add LLM configuration vars with placeholders
- `package.json` — add `@google/genai` and `@anthropic-ai/sdk` dependencies

No files to delete.

### Testing Strategy

- **Framework:** Vitest 4 + `@golevelup/ts-vitest` for NestJS mocks [Source: tech_stack memory]
- **Co-located:** spec files next to source files
- **LLM mocking:** Mock the `@google/genai` `GoogleGenAI` class and `@anthropic-ai/sdk` `Anthropic` class at the module level using `vi.mock()`. Return predictable JSON responses. Do NOT call real LLM APIs in tests.
- **DI mocking:** Mock `PrismaService`, `KnowledgeBaseService`, `EventEmitter2`, `ConfigService` with `vi.fn()` per established patterns [Source: knowledge-base.service.spec.ts, match-approval.service.spec.ts]
- **PreFilterService:** Pure unit tests, no mocking needed — just input/output assertions on similarity calculations
- **Baseline:** 85 test files, 1538 tests currently passing. All must remain green after this story.

### References

- [Source: epics.md#Epic-8, Story 8.2] — AC, business context, FR coverage
- [Source: epics.md#Story-8.4] — Discovery pipeline (downstream consumer of PreFilterService + ConfidenceScorerService)
- [Source: sprint-change-proposal-2026-03-09.md] — Story ordering (8.1 → 8.2 → 8.4 → 8.3), LlmScoringError, PreFilterService placement
- [Source: prd.md#FR-AD-05] — Confidence scoring requirement
- [Source: prd.md#FR-AD-06] — Auto-approve ≥85%, queue <85%
- [Source: prd.md#FR-CM-02] — Semantic contract matching requirement
- [Source: architecture.md lines 495-508] — Planned file structure for contract-matching module
- [Source: architecture.md lines 596-606] — Module dependency rules
- [Source: pm-arbitrage-engine/src/modules/contract-matching/knowledge-base.service.ts] — `updateConfidenceScore()` method (Story 8.1 deliverable)
- [Source: pm-arbitrage-engine/src/dashboard/match-approval.service.ts lines 70-134] — `approveMatch()` method to reuse for auto-approval
- [Source: pm-arbitrage-engine/src/common/events/match-approved.event.ts] — Event class pattern to follow
- [Source: pm-arbitrage-engine/src/common/errors/system-health-error.ts lines 19-36] — `SYSTEM_HEALTH_ERROR_CODES` pattern (4001-4008, next available: 4100+)
- [Source: pm-arbitrage-engine/src/modules/contract-matching/contract-matching.module.ts] — Current module registration (3 providers, 2 exports)
- [Source: web research — npmjs.com] — `@google/genai` v1.44.0 (GA), `@anthropic-ai/sdk` v0.78.0
- [Source: web research — googleapis/js-genai GitHub] — Confirmed `@google/generative-ai` is deprecated, use `@google/genai`

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References
N/A

### Completion Notes List

1. **SCORING_STRATEGY_TOKEN location**: Defined in `scoring-strategy.interface.ts` (not `contract-matching.module.ts`) following existing codebase pattern (`PRICE_FEED_SERVICE_TOKEN`, `POSITION_CLOSE_SERVICE_TOKEN` are in their interface files). Avoids circular import between module ↔ service.
2. **LLM_SCORING_ERROR_CODES location**: Defined in `llm-scoring-error.ts` (not `system-health-error.ts`) following existing pattern where each error class has its own codes (`EXECUTION_ERROR_CODES` in `execution-error.ts`, etc.).
3. **TF-IDF IDF formula deviation**: Story spec says `log(2 / (1 + docsContaining))` but this produces degenerate results for 2-document comparison (shared terms get negative IDF, unique terms get 0). Implemented `1 + log(2 / docsContaining)` which gives meaningful positive weights: shared terms weight=1, unique terms weight=1.693.
4. **Module registration**: Used `useExisting` instead of `useClass` for `SCORING_STRATEGY_TOKEN` to avoid duplicate `LlmScoringStrategy` instantiation (caught in Lad code review).
5. **Race condition guard**: Auto-approval checks `updateMany.count === 0` to avoid emitting events if match was approved concurrently (caught in Lad code review).
6. **Confidence validation**: Added runtime validation that LLM-returned `confidence` field is one of `high|medium|low` (caught in Lad code review).
7. **Escalation error preservation**: Escalation catch block now preserves specific `LlmScoringError` codes (e.g., parse failure) instead of always wrapping as `LLM_API_FAILURE` (caught in Lad code review).
8. **Timeout not wired to SDKs**: `LLM_TIMEOUT_MS` is read from config but not passed to SDK calls. The error code `LLM_TIMEOUT` exists for future use. Implementing AbortController wiring is outside this story's scope.

### Test Results
- **Baseline**: 85 files, 1538 tests
- **Final**: 91 files, 1586 tests (+6 files, +48 tests)
- **All passing, lint clean**

### Code Review Record (2026-03-09)
**Reviewer:** Claude Opus 4.6 (adversarial code review)

**Issues Found:** 1 High, 5 Medium, 4 Low
**Issues Fixed:** 1 High, 5 Medium, 2 Low (L1 timeoutMs, L3 double-call test)
**Remaining (accepted):** L2 pnpm-lock.yaml doc gap, L4 weak filterCandidates assertion

**Fixes Applied:**
1. **H1 — `backoffMultiplier` missing from RetryStrategy** (`llm-scoring-error.ts`): Added `backoffMultiplier: 2` to RETRYABLE_STRATEGY and `backoffMultiplier: 0` to NO_RETRY_STRATEGY. Was causing TS2741 compilation errors.
2. **M1 — SDK clients per-call instantiation** (`llm-scoring.strategy.ts`): Added lazy client caching — `GoogleGenAI` and `Anthropic` instances created once on first use, reused on subsequent calls.
3. **M2 — Race condition guard untested** (`confidence-scorer.service.spec.ts`): Added test for `updateMany.count === 0` verifying events are NOT emitted when match was approved concurrently.
4. **M3 — Unused logger field** (`pre-filter.service.ts`): Removed unused `Logger` import and field.
5. **M4 — Missing `beforeEach` import** (`pre-filter.service.spec.ts`): Added explicit `beforeEach` to vitest imports for consistency.
6. **M5 — No API key validation** (`llm-scoring.strategy.ts`): Added constructor warnings when `LLM_PRIMARY_API_KEY` or `LLM_ESCALATION_API_KEY` are empty.
7. **L1 — `timeoutMs` unused field** (`llm-scoring.strategy.ts`): Removed field and config read (env var preserved in .env files for future use).
8. **L3 — Double-call test pattern** (`llm-scoring.strategy.spec.ts`): Replaced try/catch double-call with single `.rejects.toMatchObject()` assertion.

### File List

**Created:**
- `src/common/interfaces/scoring-strategy.interface.ts`
- `src/common/errors/llm-scoring-error.ts`
- `src/common/errors/llm-scoring-error.spec.ts`
- `src/common/events/match-auto-approved.event.ts`
- `src/common/events/match-auto-approved.event.spec.ts`
- `src/common/events/match-pending-review.event.ts`
- `src/common/events/match-pending-review.event.spec.ts`
- `src/modules/contract-matching/llm-scoring.strategy.ts`
- `src/modules/contract-matching/llm-scoring.strategy.spec.ts`
- `src/modules/contract-matching/pre-filter.service.ts`
- `src/modules/contract-matching/pre-filter.service.spec.ts`
- `src/modules/contract-matching/confidence-scorer.service.ts`
- `src/modules/contract-matching/confidence-scorer.service.spec.ts`

**Modified:**
- `src/common/interfaces/index.ts` — added IScoringStrategy, ScoringResult, SCORING_STRATEGY_TOKEN exports
- `src/common/errors/index.ts` — added LlmScoringError, LLM_SCORING_ERROR_CODES exports
- `src/common/events/event-catalog.ts` — added MATCH_AUTO_APPROVED, MATCH_PENDING_REVIEW
- `src/common/events/index.ts` — added match-auto-approved.event, match-pending-review.event exports
- `src/modules/contract-matching/contract-matching.module.ts` — added PreFilterService, LlmScoringStrategy, ConfidenceScorerService providers/exports
- `.env.example` — added LLM configuration variables
- `.env.development` — added LLM configuration variables with placeholders
- `package.json` — added @google/genai, @anthropic-ai/sdk dependencies
