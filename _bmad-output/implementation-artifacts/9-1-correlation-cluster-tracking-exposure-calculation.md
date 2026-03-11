# Story 9.1: Correlation Cluster Tracking & Exposure Calculation

Status: done

## Story

As an operator,
I want the system to dynamically track which positions belong to correlated event clusters — sourced from platform APIs and normalized via LLM — and calculate aggregate exposure per cluster,
So that I'm not unknowingly concentrated in a single risk factor, and the exposure picture reflects unified cross-platform reality rather than raw platform-specific categories.

## Acceptance Criteria

1. **Given** a `CorrelationCluster` Prisma model exists as a first-class entity with fields `id`, `name`, `slug`, `description`, `createdAt`, `updatedAt`, plus a `ClusterTagMapping` join table tracking which `{platform, rawCategory}` tuples map to each cluster
   **When** the system starts
   **Then** clusters are dynamically managed — no hardcoded list — and an "Uncategorized" default cluster exists as a catch-all (seeded via migration SQL INSERT)
   [Source: User disambiguation — dynamic clusters confirmed; PRD FR-RM-05 cluster concept; architecture.md DB naming conventions]

2. **Given** Kalshi events carry `series_ticker`/`category` and Polymarket events carry `tags[].label`
   **When** a new `ContractMatch` is created in the candidate discovery pipeline (`CandidateDiscoveryService.processCandidate`)
   **Then** raw platform categories from both sides are persisted onto `ContractMatch` via two new nullable fields: `polymarketRawCategory` (from `ContractSummary.category` of the Polymarket side) and `kalshiRawCategory` (from `ContractSummary.category` of the Kalshi side)
   [Source: Codebase — `ContractSummary.category` already extracted in `kalshi-catalog-provider.ts:143-187` and `polymarket-catalog-provider.ts:159-177`; User disambiguation point 4]

3. **Given** raw platform categories are persisted on a `ContractMatch`
   **When** cluster assignment runs (triggered after match creation)
   **Then** an `IClusterClassifier` service first checks the `ClusterTagMapping` table for deterministic fast-path matches (exact `{platform, rawCategory}` lookups for both Kalshi and Polymarket categories). Fast-path short-circuits only when both sides agree on the same cluster (or only one side has a mapping and the other is null). If both sides map to different clusters, the conflict triggers an LLM call to decide. If no mappings exist, the LLM normalizes the raw categories into a unified `CorrelationCluster`:
   - If an existing cluster semantically matches, the match is assigned to it and a new `ClusterTagMapping` row is inserted for future fast-path hits
   - If no existing cluster matches, a new `CorrelationCluster` is created with a descriptive name and slug, a `ClusterTagMapping` row is inserted, and the match is assigned
   - The `ContractMatch` gains a `clusterId` FK referencing the assigned `CorrelationCluster`
   [Source: User notes — LLM normalization non-negotiable; PRD FR-RM-05 cluster classification; IScoringStrategy pattern from `scoring-strategy.interface.ts:25-35`]

4. **Given** contract pairs are classified into correlation clusters
   **When** a new position is opened (budget reservation committed)
   **Then** cluster exposure is recalculated: `Cluster Exposure = Sum(legSize x legEntryPrice)` for all legs of all open positions in that cluster, derived from `OpenPosition.sizes` and `OpenPosition.entryPrices` JSON fields (both legs summed per position — in PM arbitrage both legs represent capital deployed, this is NOT double-counting)
   **And** only positions with active statuses (`ACTIVE`, `SINGLE_LEG_EXPOSED`, `EXIT_PARTIAL`) are included — `CLOSED` and `CANCELLED` are excluded
   **And** cluster exposure as percentage of bankroll is tracked in real-time via the `RiskManagerService`
   [Source: PRD FR-RM-05; epics.md Story 9.1 AC1; Codebase `OpenPosition` model — `sizes`/`entryPrices` are JSON `{polymarket: string, kalshi: string}`]

5. **Given** the operator disagrees with a cluster assignment
   **When** they call `POST /api/risk/cluster-override` with `{ matchId, newClusterId, rationale }`
   **Then** the override controller delegates to `IClusterClassifier.reassignCluster(matchId, newClusterId, rationale)` (contract-matching owns the write)
   **And** the override is logged to the audit trail with rationale
   **And** cluster exposure is recalculated for both the old and new clusters
   **And** a `risk.cluster.override` event is emitted
   [Source: epics.md Story 9.1 AC2; PRD Operator Triage Interface section]

6. **Given** cluster exposure changes (position opened, closed, or cluster override)
   **When** any cluster's exposure as % of bankroll exceeds 80% of the 15% hard limit (i.e., 12%)
   **Then** a `risk.cluster.limit_approached` event is emitted with cluster name, current exposure %, and threshold
   [Source: PRD soft limit zone 12-15%; risk.events.ts LimitApproachedEvent pattern]

7. **Given** the system tracks cluster exposure
   **When** `getCurrentExposure()` is called on `IRiskManager`
   **Then** the response includes a `clusterExposures` map: `Record<clusterId, { clusterName, exposureUsd, exposurePct, pairCount }>`
   **And** aggregate exposure across all clusters is included
   [Source: PRD Portfolio Correlation Calculation section; existing `RiskExposure` interface in `risk.type.ts:14-21`]

## Tasks / Subtasks

**Execution order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10** (events before services that emit them)

- [x] **Task 1: Prisma schema — CorrelationCluster + ClusterTagMapping + ContractMatch extensions** (AC: #1, #2)
  - [x] 1.1 Add `CorrelationCluster` model: `id` (uuid PK), `name` (string unique), `slug` (string unique), `description` (string nullable), `createdAt`, `updatedAt`. Map to `correlation_clusters` table. Add reverse relation `contractMatches ContractMatch[]` and `tagMappings ClusterTagMapping[]`.
  - [x] 1.2 Add `ClusterTagMapping` model: `id` (uuid PK), `clusterId` (FK → `CorrelationCluster.id`, `onDelete: Cascade`), `platform` (string — "kalshi" | "polymarket"), `rawCategory` (string), `createdAt`. Map to `cluster_tag_mappings`. Add `@@unique([clusterId, platform, rawCategory])` constraint. This replaces a JSON array and eliminates concurrent-update race conditions.
  - [x] 1.3 Add to `ContractMatch`: `polymarketRawCategory` (string nullable), `kalshiRawCategory` (string nullable), `clusterId` (string nullable FK → `CorrelationCluster.id`, `onDelete: SetNull` — if a cluster is deleted, matches revert to unclassified rather than throwing FK errors). Add Prisma relation `cluster CorrelationCluster? @relation(...)`. Add index on `clusterId`.
  - [x] 1.4 Create migration: `pnpm prisma migrate dev --name add-correlation-clusters`. Add SQL INSERT at the end of the migration file to seed the "Uncategorized" default cluster (guarantees existence regardless of service state): `INSERT INTO correlation_clusters (id, name, slug, description, created_at, updated_at) VALUES (gen_random_uuid(), 'Uncategorized', 'uncategorized', 'Default cluster for unclassified or failed-to-classify matches', NOW(), NOW());`
  - [x] 1.5 Run `pnpm prisma generate`

- [x] **Task 2: Branded type + common types** (AC: #1, #7)
  - [x] 2.1 Add `ClusterId` branded type to `common/types/branded.type.ts` following the existing `unique symbol` pattern
  - [x] 2.2 Add `ClusterExposure` interface to `common/types/risk.type.ts`: `{ clusterId: ClusterId, clusterName: string, exposureUsd: Decimal, exposurePct: Decimal, pairCount: number }`
  - [x] 2.3 Extend `RiskExposure` interface with `clusterExposures: ClusterExposure[]` and `aggregateClusterExposurePct: Decimal`
  - [x] 2.4 Add `ClusterAssignment` type: `{ clusterId: ClusterId, clusterName: string, rawCategories: { platform: string, rawCategory: string }[] }`

- [x] **Task 3: IClusterClassifier interface** (AC: #3, #5)
  - [x] 3.1 Create `common/interfaces/cluster-classifier.interface.ts` with `IClusterClassifier`
  - [x] 3.2 Method: `classifyMatch(polyCategory: string | null, kalshiCategory: string | null, polyDescription: string, kalshiDescription: string): Promise<ClusterAssignment>`
  - [x] 3.3 Method: `getOrCreateCluster(name: string, description?: string): Promise<ClusterId>`
  - [x] 3.4 Method: `reassignCluster(matchId: MatchId, newClusterId: ClusterId, rationale: string): Promise<{ oldClusterId: ClusterId | null, newClusterId: ClusterId }>` — updates `ContractMatch.clusterId`, logs to audit trail. This keeps contract-matching as the sole writer of `ContractMatch.clusterId`, preventing the cross-module write violation.
  - [x] 3.5 Export from `common/interfaces/index.ts`

- [x] **Task 4: Event catalog + event classes** (AC: #5, #6)
  - [x] 4.1 Add to `event-catalog.ts`: `CLUSTER_LIMIT_APPROACHED: 'risk.cluster.limit_approached'`, `CLUSTER_OVERRIDE: 'risk.cluster.override'`, `CLUSTER_ASSIGNED: 'risk.cluster.assigned'`. Naming note: uses underscores within segments, consistent with existing `risk.limit.approached` and `execution.single_leg.exposure` patterns in the catalog.
  - [x] 4.2 Create event classes in `common/events/risk.events.ts`: `ClusterLimitApproachedEvent(clusterName, clusterId, currentExposurePct, threshold)`, `ClusterOverrideEvent(matchId, oldClusterId, newClusterId, rationale)`, `ClusterAssignedEvent(matchId, clusterId, clusterName, wasLlmClassified)`
  - [x] 4.3 Export from `common/events/index.ts`

- [x] **Task 5: LLM cluster classifier service** (AC: #3)
  - [x] 5.1 Create `modules/contract-matching/cluster-classifier.service.ts` implementing `IClusterClassifier`
  - [x] 5.2 **Deterministic fast-path (CRITICAL optimization):** Before any LLM call, query `ClusterTagMapping` for exact `{platform, rawCategory}` matches on both the Kalshi and Polymarket categories. Fast-path resolution rules:
    - Both sides map to the **same** cluster → assign immediately, no LLM call
    - Only **one** side has a mapping (other is null or unmapped) → assign to the mapped cluster, no LLM call
    - Both sides map to **different** clusters → conflict, fall through to LLM call to decide (this combination hasn't been seen before)
    - **Neither** side has a mapping → fall through to LLM call
    This prevents redundant LLM calls for recurring categories (e.g., every `FED-RATE` Kalshi match after the first) while correctly handling cross-platform ambiguity.
  - [x] 5.3 LLM prompt: given raw Kalshi category + Polymarket tag + contract descriptions, return a cluster name. The prompt must include the list of existing cluster names for matching.
  - [x] 5.4 On LLM response: check if returned cluster name matches an existing `CorrelationCluster` (case-insensitive slug match); if yes, assign to it and INSERT `ClusterTagMapping` row(s) for the new raw categories; if no, create new cluster, INSERT mapping rows, and assign.
  - [x] 5.5 Slug generation: `name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')` — document in service comments.
  - [x] 5.6 Ensure "Uncategorized" cluster is loaded on module init (already seeded by migration). Cache its `ClusterId` for fast fallback.
  - [x] 5.7 Add config: `CLUSTER_LLM_TIMEOUT_MS` (default: 15000). Default LLM model: reuse `LLM_MODEL` env var (same as scoring service) rather than a separate `CLUSTER_LLM_MODEL` — no reason to use a different model for classification.
  - [x] 5.8 On LLM failure: assign to "Uncategorized" cluster, log warning, do NOT block match creation
  - [x] 5.9 Implement `reassignCluster()`: update `ContractMatch.clusterId` in a Prisma `$transaction`, then write `AuditLog` entry AFTER the transaction commits (not inside it). Reason: `AuditLogService.append()` uses SHA-256 hash chaining with its own read-previous-then-write Prisma call — nesting it inside an outer `$transaction` risks conflicting with the hash-chain's sequential read pattern. Audit is observability, not business logic, so writing after commit is acceptable. Return old and new cluster IDs.
  - [x] 5.10 Write co-located spec: `cluster-classifier.service.spec.ts`

- [x] **Task 6: Integrate cluster assignment into candidate discovery** (AC: #2, #3)
  - [x] 6.1 Modify `CandidateDiscoveryService.processCandidate` to persist `polymarketRawCategory` and `kalshiRawCategory` on `ContractMatch` creation (data already available from `ContractSummary.category`)
  - [x] 6.2 After successful match creation, call `IClusterClassifier.classifyMatch()` and update `ContractMatch.clusterId`
  - [x] 6.3 Handle classification failure gracefully — match is created with `clusterId = null` (Uncategorized fallback), logged as warning
  - [x] 6.4 Update existing tests in `candidate-discovery.service.spec.ts`

- [x] **Task 7: Correlation tracker service** (AC: #4, #6, #7)
  - [x] 7.1 Create `modules/risk-management/correlation-tracker.service.ts`
  - [x] 7.2 Method: `recalculateClusterExposure(clusterId?: ClusterId): Promise<void>` — queries all open positions (statuses: `ACTIVE`, `SINGLE_LEG_EXPOSED`, `EXIT_PARTIAL`) joined via `OpenPosition.pairId` → `ContractMatch.matchId` → `ContractMatch.clusterId`. For each position, calculate capital deployed from JSON fields: `sizes` (`{polymarket: string, kalshi: string}`) x `entryPrices` (`{polymarket: string, kalshi: string}`), summing both legs. Use `decimal.js` for all arithmetic. Parse JSON with Zod schema validation (`parseJsonField` pattern from Story 9-0-2).
  - [x] 7.3 Method: `getClusterExposures(): ClusterExposure[]` — returns current exposure snapshot
  - [x] 7.4 Method: `getAggregateExposurePct(): Decimal` — sum of all cluster exposures as % of bankroll
  - [x] 7.5 Emit `risk.cluster.limit_approached` event when any cluster exceeds 12% (soft limit)
  - [x] 7.6 Recalculation triggers: position opened (listen to `BUDGET_COMMITTED`), position closed (listen to `EXIT_TRIGGERED` / position closure events), cluster override (listen to `CLUSTER_OVERRIDE`)
  - [x] 7.7 Write co-located spec: `correlation-tracker.service.spec.ts`

- [x] **Task 8: Integrate correlation tracker into RiskManagerService** (AC: #7)
  - [x] 8.1 Inject `CorrelationTrackerService` into `RiskManagerService`
  - [x] 8.2 Extend `getCurrentExposure()` to include `clusterExposures` and `aggregateClusterExposurePct` from the tracker
  - [x] 8.3 Update `risk-manager.service.spec.ts` for new exposure fields

- [x] **Task 9: Cluster override + list API endpoints** (AC: #5)
  - [x] 9.1 Add `POST /api/risk/cluster-override` to `RiskOverrideController`. The controller delegates to `IClusterClassifier.reassignCluster()` — it does NOT update `ContractMatch` directly. This preserves module boundaries: contract-matching owns ContractMatch writes.
  - [x] 9.2 DTO: `ClusterOverrideDto { matchId: string, newClusterId: string, rationale: string }`. Add `@ApiProperty()` decorators for Swagger.
  - [x] 9.3 Validate matchId and newClusterId exist (404 if not)
  - [x] 9.4 After `reassignCluster()` returns, trigger `CorrelationTrackerService.recalculateClusterExposure()` for both old and new clusters
  - [x] 9.5 Emit `risk.cluster.override` event
  - [x] 9.6 Add `GET /api/risk/clusters` endpoint to list all clusters with current exposure. Add `@ApiResponse()` decorators for Swagger so the dashboard API client auto-generates types.
  - [x] 9.7 Override history query: deferred to Story 9.2 (triage recommendations will need it). Note this explicitly so it's not forgotten.
  - [x] 9.8 Response DTOs: add `@ApiProperty()` decorators for Swagger auto-generation
  - [x] 9.9 Write controller spec

- [x] **Task 10: Zod boundary schemas for new fields** (AC: #1, #2)
  - [x] 10.1 Add Zod schemas for cluster override DTO
  - [x] 10.2 Add env var schemas for new config (`CLUSTER_LLM_TIMEOUT_MS`, `RISK_CLUSTER_HARD_LIMIT_PCT`, `RISK_CLUSTER_SOFT_LIMIT_PCT`)
  - [x] 10.3 Add Zod schema for `ClusterTagMapping.platform` field: `z.enum(['kalshi', 'polymarket'])` — ensures only valid `PlatformId` values are stored (the DB column is a plain string, so Zod is the validation layer). Use this schema in the classifier service when inserting tag mappings.
  - [x] 10.4 Add Zod schemas for `OpenPosition.sizes` and `OpenPosition.entryPrices` JSON fields if not already covered by 9-0-2 (needed for exposure calculation parsing)

## Dev Notes

### Architecture & Patterns

**Module boundary design (CRITICAL — addresses cross-module dependency):**
- `ClusterClassifierService` → `modules/contract-matching/` — owns ALL writes to `ContractMatch.clusterId` and `ClusterTagMapping`. This includes both initial classification AND operator override reassignment (via `IClusterClassifier.reassignCluster()`).
- `CorrelationTrackerService` → `modules/risk-management/` — READ-ONLY access to `ContractMatch.clusterId` via Prisma joins. This is a new allowed dependency edge: `modules/risk-management/ → ContractMatch (read-only for cluster data)`. Precedent: `dashboard/` already reads ContractMatch directly. The tracker queries `OpenPosition` (persistence layer, accessible to all) joined to `ContractMatch` for `clusterId` — it never imports a contract-matching service.
- The override controller in risk-management calls `IClusterClassifier.reassignCluster()` (injected via interface token from common/interfaces/) — it does NOT write `ContractMatch` directly. This prevents the circular data flow where risk-management both reads and writes a contract-matching-owned model.
[Source: architecture.md module dependency rules; CLAUDE.md forbidden imports]

**LLM classification approach (lean, with fast-path):**
- **Fast-path first:** Before any LLM call, check `ClusterTagMapping` table for exact `{platform, rawCategory}` match. This is a simple indexed lookup that resolves instantly for any category string the system has seen before. After initial cluster population, the vast majority of classifications hit this fast-path with zero LLM cost.
- **LLM fallback:** Only invoked for genuinely new category strings. Reuse the existing Anthropic SDK client pattern from `LlmScoringService` (same provider, same rate limiter). The classifier prompt receives: raw Kalshi category, raw Polymarket tag, contract descriptions from both sides, and the current list of existing cluster names. Response: a single cluster name (existing or new).
- On LLM failure: fall back to "Uncategorized" — never block match creation for a classification failure
- Slug generation for new clusters: `name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')`

**Exposure calculation — CRITICAL implementation detail:**
- `OpenPosition` does NOT have a single `positionSizeUsd` field. Capital per position must be derived from two JSON fields:
  - `sizes` (Json): `{polymarket: string, kalshi: string}` — contract counts per leg
  - `entryPrices` (Json): `{polymarket: string, kalshi: string}` — entry prices per leg
  - Per-position capital = `new Decimal(sizes.polymarket).mul(new Decimal(entryPrices.polymarket)).plus(new Decimal(sizes.kalshi).mul(new Decimal(entryPrices.kalshi)))`
- **Why both legs are summed:** In prediction market arbitrage, both legs represent actual capital deployed — we buy contracts on both platforms. This is NOT double-counting. Unlike traditional finance hedges where one side offsets the other, both PM legs are independent purchases that each require capital.
- Join path: `OpenPosition.pairId` → `ContractMatch.matchId` → `ContractMatch.clusterId`
- Filter: only positions with status in (`ACTIVE`, `SINGLE_LEG_EXPOSED`, `EXIT_PARTIAL`) — see `PositionStatus` enum in schema.prisma
- `Cluster Exposure = Sum(per-position capital)` for all qualifying positions in cluster
- `Cluster Exposure % = Cluster Exposure / bankrollUsd x 100`
- Parse JSON fields using `parseJsonField()` helper with Zod schemas (pattern from Story 9-0-2) — never trust raw JSON casts
- All financial math uses `decimal.js` — exposure values are `Decimal`, percentages are `Decimal`

**Event-driven recalculation:**
- Listen to `BUDGET_COMMITTED` (new position opened) → recalculate cluster exposure for the affected cluster
- Listen to position closure events → recalculate
- Listen to `CLUSTER_OVERRIDE` event → recalculate both old and new clusters
- The correlation tracker does NOT poll — it reacts to events

**Integration with existing `validatePosition()`:**
- This story adds cluster exposure tracking and soft-limit alerting only
- Hard-limit enforcement (blocking trades that exceed 15%) is Story 9.2's scope
- `validatePosition()` is NOT modified in this story — cluster limits are additive in 9.2

### Codebase Touchpoints

**Files to CREATE:**
- `pm-arbitrage-engine/src/modules/risk-management/correlation-tracker.service.ts`
- `pm-arbitrage-engine/src/modules/risk-management/correlation-tracker.service.spec.ts`
- `pm-arbitrage-engine/src/modules/contract-matching/cluster-classifier.service.ts`
- `pm-arbitrage-engine/src/modules/contract-matching/cluster-classifier.service.spec.ts`
- `pm-arbitrage-engine/src/common/interfaces/cluster-classifier.interface.ts`
- `pm-arbitrage-engine/src/modules/risk-management/dto/cluster-override.dto.ts`
- `pm-arbitrage-engine/src/modules/risk-management/dto/cluster-override-response.dto.ts`
- `pm-arbitrage-engine/prisma/migrations/YYYYMMDDHHMMSS_add_correlation_clusters/migration.sql` (auto-generated + manual seed INSERT)

**Files to MODIFY:**
- `pm-arbitrage-engine/prisma/schema.prisma` — add `CorrelationCluster` model, `ClusterTagMapping` model, extend `ContractMatch` (lines 66-100)
- `pm-arbitrage-engine/src/common/types/branded.type.ts` — add `ClusterId` branded type
- `pm-arbitrage-engine/src/common/types/risk.type.ts` — add `ClusterExposure`, extend `RiskExposure` (lines 14-21)
- `pm-arbitrage-engine/src/common/events/event-catalog.ts` — add 3 cluster events (after line 174)
- `pm-arbitrage-engine/src/common/events/risk.events.ts` — add 3 event classes
- `pm-arbitrage-engine/src/common/events/index.ts` — export new events
- `pm-arbitrage-engine/src/common/interfaces/index.ts` — export `IClusterClassifier`
- `pm-arbitrage-engine/src/common/interfaces/risk-manager.interface.ts` — extend `IRiskManager` interface (lines 13-104) — adding cluster exposure methods triggers compiler-driven updates in all consumers
- `pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.ts` — persist raw categories + call classifier (modify `processCandidate` at lines 271-398)
- `pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.spec.ts` — update tests
- `pm-arbitrage-engine/src/modules/contract-matching/contract-matching.module.ts` — register `ClusterClassifierService`, export via `IClusterClassifier` token
- `pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts` — inject tracker, extend `getCurrentExposure()`
- `pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.spec.ts` — update tests
- `pm-arbitrage-engine/src/modules/risk-management/risk-management.module.ts` — register `CorrelationTrackerService`, import `IClusterClassifier` token from contract-matching
- `pm-arbitrage-engine/src/modules/risk-management/risk-override.controller.ts` — add cluster override + list endpoints with Swagger decorators

### Platform API Category Data (verified via web research)

**Kalshi:**
- `GET /search/tags_by_categories` returns tags organized by series categories (hierarchical: category → tags)
- Each event carries `series_ticker` (e.g., `FED-RATE`) and `category` (e.g., `Economics`)
- The codebase already maps `event.series_ticker || event.category` to `ContractSummary.category` in `kalshi-catalog-provider.ts`
[Source: Kalshi API docs — docs.kalshi.com/api-reference/search/get-tags-for-series-categories]

**Polymarket:**
- `GET /tags` returns all tags with `{ id, label, slug }` structure
- `GET /events/{id}/tags` returns tags for a specific event
- Events carry `tags[]` array, codebase maps `event.tags?.[0]?.label` to `ContractSummary.category` in `polymarket-catalog-provider.ts`
- Tags have relationship endpoints for discovering related tags
[Source: Polymarket API docs — docs.polymarket.com/api-reference/events/get-event-tags]

### Key Interfaces (verified from codebase)

**`BudgetReservation` already has `correlationExposure: Decimal`** (line 44 of `risk.type.ts`) — initialized to zero, never populated. This story populates it with the cluster's exposure at reservation time. Story 9.2 will use it for limit enforcement.

**`IRiskManager` interface** (`risk-manager.interface.ts:13-104`): `getCurrentExposure()` returns `RiskExposure`. Extending `RiskExposure` with `clusterExposures` and `aggregateClusterExposurePct` automatically flows through without adding new methods to `IRiskManager`. Use compiler-driven development (change types first, let `pnpm build` identify all affected consumers).

### Testing Strategy

- **Unit tests:** Co-located specs for `CorrelationTrackerService`, `ClusterClassifierService`, controller
- **LLM mock:** Mock the Anthropic SDK client in classifier tests (same pattern as `LlmScoringService` tests)
- **Fast-path tests:** Verify deterministic `ClusterTagMapping` lookup bypasses LLM entirely when category is known
- **Prisma mock:** Use the existing Prisma mock patterns from the test suite
- **Integration points:** Test the full flow: match creation → fast-path/LLM classification → tag mapping insert → exposure recalculation
- **decimal.js compliance:** All exposure calculations must use `Decimal` — no native JS operators on monetary values
- **Framework:** Vitest 4 (NOT Jest). Co-located tests. Run with `pnpm test`

### Configuration (new env vars)

```
CLUSTER_LLM_TIMEOUT_MS=15000                      # LLM call timeout for cluster classification
RISK_CLUSTER_HARD_LIMIT_PCT=0.15                  # 15% hard limit per cluster
RISK_CLUSTER_SOFT_LIMIT_PCT=0.12                  # 12% soft limit (alert threshold)
RISK_AGGREGATE_CLUSTER_LIMIT_PCT=0.50             # 50% aggregate limit across all clusters
```

Note: LLM model for classification reuses the existing `LLM_MODEL` env var (same as scoring service). No separate `CLUSTER_LLM_MODEL` — there's no reason to use a different model for classification vs scoring.

### Error Handling

- LLM classification failure → assign "Uncategorized", log warning, emit no event, do NOT block match creation
- Invalid cluster override (matchId/clusterId not found) → return 404 with `SystemError` subclass
- Prisma unique constraint on cluster name/slug → handle gracefully in `getOrCreateCluster()`
- `ClusterTagMapping` unique constraint violation (concurrent insert of same tuple) → catch P2002, treat as successful lookup (another thread won the race)
- Error code 3002 (`Correlation Cluster Limit Breach`) already reserved in PRD error table — will be used by this story for soft-limit warnings

### Previous Story Intelligence

- **9-0-1:** Established branded type pattern (`unique symbol`), compiler-driven development methodology. Use same approach for `ClusterId`.
- **9-0-2:** Established Zod boundary validation pattern. New env vars must have Zod schemas. JSON fields (`sizes`, `entryPrices` on `OpenPosition`) must be parsed with `parseJsonField()`.
- **Epic 8:** `IScoringStrategy` pattern for LLM integration — reuse for `IClusterClassifier`. `LlmScoringService` in `contract-matching/` module is the reference implementation for Anthropic SDK usage, rate limiting, error handling.
- **Epic 8 retro:** Real API data quality is systemic — LLM classification must handle messy/missing categories gracefully (null categories, empty strings, inconsistent casing).

### Deferred Items (explicitly out of scope)

- **Override history query endpoint** (`GET /api/risk/cluster-overrides?matchId=`) — deferred to Story 9.2 where triage recommendations will need override context
- **Dashboard cluster visualization** — separate dashboard story after backend is stable
- **`exposureUsd` branded USD type** — the project uses plain `Decimal` for financial values (Story 9-0-1 branded entity IDs, not monetary amounts). Flagged for future consistency review.

### Project Structure Notes

- All new files follow kebab-case naming convention
- DB tables use snake_case with `@@map()`
- DB columns use snake_case with `@map()`
- New Prisma models follow existing patterns (uuid PK, `@default(now())` for timestamps, `@db.Timestamptz`)
- `IClusterClassifier` follows the `I`-prefix interface convention in `common/interfaces/`
- Event names follow dot-notation with underscores within segments: `risk.cluster.limit_approached`, consistent with existing `execution.single_leg.exposure` and `risk.limit.approached`

### References

- [Source: PRD FR-RM-05] Correlation exposure calculation requirement
- [Source: PRD FR-RM-06] 15% cluster hard limit
- [Source: PRD Correlation Management Framework] Cluster concept, exposure formula, soft/hard/aggregate limits
- [Source: epics.md Story 9.1] User story, acceptance criteria
- [Source: architecture.md lines 520-526] Planned `correlation-tracker.service.ts` in risk-management module
- [Source: architecture.md lines 428-430] Risk management module file structure
- [Source: architecture.md lines 600-610] Module dependency rules — forbidden imports
- [Source: User disambiguation 2026-03-12] Dynamic clusters confirmed, LLM normalization in-scope, first-class entity, no backfill needed
- [Source: User review 2026-03-12] Cross-module boundary fixes, ClusterTagMapping join table, fast-path optimization, exposure formula justification, fast-path conflict resolution (both-map-to-different → LLM), onDelete behaviors, audit log transaction scope, platform type safety
- [Source: Kalshi API docs] `series_ticker`/`category` on events, `tags_by_categories` endpoint
- [Source: Polymarket API docs] `tags[]` on events, `GET /tags` endpoint
- [Source: Codebase `scoring-strategy.interface.ts:25-35`] IScoringStrategy pattern for LLM interfaces
- [Source: Codebase `candidate-discovery.service.ts:271-398`] processCandidate — exact integration point for category persistence
- [Source: Codebase `risk.type.ts:37-46`] BudgetReservation.correlationExposure field (existing, unused)
- [Source: Codebase `risk.events.ts`] Event class patterns (BaseEvent extension)
- [Source: Codebase `event-catalog.ts`] Event naming convention and catalog structure
- [Source: Codebase `schema.prisma:167-192`] OpenPosition model — sizes/entryPrices are JSON, pairId FK to ContractMatch

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (claude-opus-4-6) — 2026-03-12

### Completion Notes List

- All 10 tasks implemented across 2 sessions with TDD workflow
- All 7 Acceptance Criteria verified against implementation and tests
- Full test suite: 111 files, 1867 tests passing (93 new/modified tests for this story)
- Lint clean (zero errors)
- Lad MCP code review completed (attempt 2) — addressed: PlatformApiError misuse (switched to SystemHealthError 4007), empty slug guard, LLM JSON sanitization (strip markdown fences), per-position try-catch in exposure recalculation loop
- Review findings dismissed as non-applicable: in-memory cache scaling (single-instance system), division by zero (bankroll validated in RiskManagerService.validateConfig), LLM timeout (failure falls back to Uncategorized — no blocking risk), event emission location (controller is correct orchestrator)

### Key Design Decisions

1. **Error type for "not found"**: Used `SystemHealthError(4007)` instead of `PlatformApiError` — "entity not found" is not a platform API error. Controller does duck-type checking on `.code` property.
2. **MonitoringModule import in ContractMatchingModule**: `ClusterClassifierService` depends on `AuditLogService` which requires `AuditLogRepository`. Instead of registering both, import `MonitoringModule` which already exports `AuditLogService`.
3. **LLM JSON sanitization**: Added regex extraction of `{...}` from LLM responses to handle markdown-wrapped JSON (common LLM output pattern).
4. **Per-position error resilience**: Wrapped exposure calculation loop in try-catch per position so a single corrupted `sizes`/`entryPrices` JSON field doesn't crash the entire recalculation.
5. **forwardRef for ConnectorModule**: ContractMatchingModule uses `forwardRef(() => ConnectorModule)` to break circular dependency (ConnectorModule → DataIngestionModule → ContractMatchingModule).

### File List

**Created:**
- `pm-arbitrage-engine/prisma/migrations/20260312120827_add_correlation_clusters/migration.sql`
- `pm-arbitrage-engine/src/common/interfaces/cluster-classifier.interface.ts`
- `pm-arbitrage-engine/src/modules/contract-matching/cluster-classifier.service.ts`
- `pm-arbitrage-engine/src/modules/contract-matching/cluster-classifier.service.spec.ts`
- `pm-arbitrage-engine/src/modules/risk-management/correlation-tracker.service.ts`
- `pm-arbitrage-engine/src/modules/risk-management/correlation-tracker.service.spec.ts`
- `pm-arbitrage-engine/src/modules/risk-management/dto/cluster-override.dto.ts`
- `pm-arbitrage-engine/src/modules/risk-management/dto/cluster-override-response.dto.ts`

**Modified:**
- `pm-arbitrage-engine/prisma/schema.prisma` — CorrelationCluster, ClusterTagMapping models + ContractMatch extensions
- `pm-arbitrage-engine/src/common/types/branded.type.ts` — ClusterId branded type
- `pm-arbitrage-engine/src/common/types/risk.type.ts` — ClusterExposure, ClusterAssignment, RiskExposure extensions
- `pm-arbitrage-engine/src/common/events/event-catalog.ts` — 3 cluster events
- `pm-arbitrage-engine/src/common/events/risk.events.ts` — 3 event classes
- `pm-arbitrage-engine/src/common/interfaces/index.ts` — IClusterClassifier export
- `pm-arbitrage-engine/src/common/schemas/prisma-json.schema.ts` — clusterPlatformSchema
- `pm-arbitrage-engine/src/common/config/env.schema.ts` — CLUSTER_LLM_TIMEOUT_MS, RISK_CLUSTER_*_PCT
- `pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.ts` — cluster integration
- `pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.spec.ts` — updated tests
- `pm-arbitrage-engine/src/modules/contract-matching/contract-matching.module.ts` — module wiring
- `pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts` — tracker injection
- `pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.spec.ts` — updated tests
- `pm-arbitrage-engine/src/modules/risk-management/risk-management.module.ts` — module wiring
- `pm-arbitrage-engine/src/modules/risk-management/risk-override.controller.ts` — cluster endpoints
- `pm-arbitrage-engine/src/modules/risk-management/risk-override.controller.spec.ts` — updated tests
- `pm-arbitrage-engine/src/common/utils/financial-math.property.spec.ts` — CorrelationTrackerService mock
- `pm-arbitrage-engine/test/core-lifecycle.e2e-spec.ts` — correlationCluster mock in PrismaService

### Code Review Fixes (2026-03-12)

**Reviewer:** Amelia (Dev Agent) — adversarial code review

**Issues Fixed (3 HIGH, 4 MEDIUM, 3 LOW):**

1. **[HIGH] Triple cluster exposure recalculation on override** — Removed `@OnEvent(CLUSTER_OVERRIDE)` listener from `CorrelationTrackerService` since `RiskOverrideController` already does targeted recalculation for old+new clusters. The event listener was doing a third, full unscoped recalculation.

2. **[HIGH] LLM timeout config stored but never applied** — Added `Promise.race` with `clearTimeout` cleanup in `callLlm()`. LLM API calls now respect `CLUSTER_LLM_TIMEOUT_MS` (default 15s).

3. **[HIGH] `uncategorizedClusterId` could be undefined at runtime** — Changed `onModuleInit` to programmatically create the Uncategorized cluster if the migration seed is missing, instead of logging a warning and leaving the field undefined. Added test for create-on-missing path.

4. **[MEDIUM] `wasLlmClassified` always hardcoded `false`** — Added `wasLlmClassified: boolean` to `ClusterAssignment` type. Fast-path returns set `false`, LLM path sets `true`. `ClusterAssignedEvent` now correctly reflects classification method.

5. **[MEDIUM] `RISK_AGGREGATE_CLUSTER_LIMIT_PCT` documented but missing from env schema** — Added to `env.schema.ts` with default `0.50`. Enforcement deferred to Story 9.2.

6. **[MEDIUM] Story File List falsely claimed `events/index.ts` was modified** — Removed from File List (file already re-exports `risk.events`, so new events flowed through automatically).

7. **[MEDIUM] Unnecessary `$transaction` in `reassignCluster`** — Removed wrapper around single `contractMatch.update` (single Prisma operations are already atomic).

8. **[LOW] `findFirst` used instead of `findUnique` for unique-constrained lookups** — Changed to `findUnique` for `correlationCluster` lookups by `slug`, `id` (both have unique constraints). Updated all test mocks accordingly.

9. **[LOW] Empty slug silently fell back to Uncategorized** — Added debug log when `generateSlug()` returns empty string.

10. **[LOW] Story AC #4 says "ACTIVE" but actual Prisma enum is `OPEN`** — Documentation only; code correctly uses `OPEN`.

**Test results after fixes:** 1868 tests passing (111 files), lint clean.
