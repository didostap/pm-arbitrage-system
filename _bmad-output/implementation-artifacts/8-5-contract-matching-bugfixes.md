# Story 8.5: Contract Matching Bugfixes

Status: done

## Story

As an operator,
I want the contract matching pipeline to correctly distinguish Polymarket identifiers, filter UI noise from low-score matches, and display confidence scores accurately,
So that the trading pipeline never sends the wrong ID to the CLOB, my pending review queue only shows actionable matches, and I can trust the dashboard's data.

## Acceptance Criteria

1. **Given** the Prisma schema has a `ContractMatch` model
   **When** this story's migration runs
   **Then** a new nullable column `polymarket_clob_token_id` (`String?`) is added with index `@@index([polymarketClobTokenId])`
   **And** existing rows are unaffected (no data migration — DB was recently reset)
   [Source: sprint-change-proposal-2026-03-10.md#Update-1; prisma/schema.prisma lines 66-98]

2. **Given** `PolymarketCatalogProvider` fetches events from the Gamma API
   **When** mapping each market to `ContractSummary`
   **Then** `clobTokenId` is extracted from `market.clobTokenIds[0]` (the YES outcome token)
   **And** `ContractSummary` gains an optional `clobTokenId?: string` field
   **And** `PolymarketMarket` interface gains `clobTokenIds?: string[]`
   [Source: sprint-change-proposal-2026-03-10.md#Update-1; polymarket-catalog-provider.ts lines 13-18]

3. **Given** the discovery pipeline scores a candidate pair and creates a `ContractMatch`
   **When** the Polymarket contract has a `clobTokenId`
   **Then** `polymarketClobTokenId` is stored on the record (`polyContract.clobTokenId ?? null`)
   [Source: sprint-change-proposal-2026-03-10.md#Update-1; candidate-discovery.service.ts lines 248-265]

4. **Given** the YAML config defines manual contract pairs
   **When** `ContractPairDto` validates the config at startup
   **Then** `polymarketClobTokenId` is a required field (`@IsString() @IsNotEmpty()`)
   **And** startup fails if any pair is missing `polymarketClobTokenId`
   **And** `ContractPairConfig` runtime type includes non-optional `polymarketClobTokenId: string`
   **And** `toPairConfig()` maps `dto.polymarketClobTokenId` to the runtime config
   **And** `ContractMatchSyncService` upsert includes `polymarketClobTokenId` in both `create` and `update`
   [Source: sprint-change-proposal-2026-03-10.md#Update-1; contract-pair.dto.ts, contract-pair-config.type.ts, contract-pair-loader.service.ts:158-168, contract-match-sync.service.ts:57-78]

5. **Given** a contract pair is loaded into the active pair set
   **When** `polymarketClobTokenId` is null (auto-discovered pair without CLOB token)
   **Then** the pair is excluded from the trading pipeline with a warning log via `ContractPairLoaderService.getActivePairs()` filter
   **And** the pair remains in the knowledge base for display purposes
   [Source: sprint-change-proposal-2026-03-10.md#Update-1 — validation gate; Task: #12]

6. **Given** any CLOB consumer (orderbook fetch, order placement, price query) references a Polymarket contract
   **When** building the request to the Polymarket connector
   **Then** it uses `polymarketClobTokenId` (not `polymarketContractId`)
   **And** display-only consumers continue using `polymarketContractId`
   [Source: sprint-change-proposal-2026-03-10.md#Update-1 — CLOB consumer updates table]

7. **Given** the discovery pipeline scores a candidate pair
   **When** the score is `>= 85` (auto-approve threshold, env: `LLM_AUTO_APPROVE_THRESHOLD`)
   **Then** behavior is unchanged: auto-approved, events emitted
   [Source: sprint-change-proposal-2026-03-10.md#Update-2; candidate-discovery.service.ts lines 246-300]

8. **Given** the discovery pipeline scores a candidate pair
   **When** the score is `>= 40` and `< 85`
   **Then** the match is persisted with `operatorRationale: null` and `operatorApproved: false`
   **And** `MatchPendingReviewEvent` is emitted (existing behavior)
   [Source: sprint-change-proposal-2026-03-10.md#Update-2]

9. **Given** the discovery pipeline scores a candidate pair
   **When** the score is `< 40` (env: `LLM_MIN_REVIEW_THRESHOLD`, default 40)
   **Then** the match is persisted with `operatorApproved: false` and `operatorRationale: "Auto-rejected: below review threshold (score: X, threshold: Y)"`
   **And** NO event is emitted (silent cache to prevent redundant LLM calls on next run)
   **And** `stats.autoRejected` counter is incremented
   [Source: sprint-change-proposal-2026-03-10.md#Update-2]

10. **Given** the `DiscoveryRunCompletedEvent` is emitted
    **When** the run finishes
    **Then** `DiscoveryRunStats` includes `autoRejected: number`
    [Source: sprint-change-proposal-2026-03-10.md#Update-2]

11. **Given** the dashboard `MatchCard` component renders a match with `confidenceScore`
    **When** the score is not null
    **Then** it displays `${match.confidenceScore.toFixed(0)}%` (no multiplication by 100 — backend stores 0-100)
    [Source: sprint-change-proposal-2026-03-10.md#Update-3; pm-arbitrage-dashboard/src/components/MatchCard.tsx line 63]

12. **Given** an auto-rejected match appears in the dashboard
    **When** `MatchCard` renders it
    **Then** a new derived status `'auto-rejected'` is displayed with a slate-colored badge (`AUTO-REJECTED`)
    **And** the card has `opacity-60` (same as operator-rejected)
    **And** auto-rejected matches appear alongside operator-rejected matches (existing filter logic handles this via `operatorRationale: { not: null }`)
    [Source: sprint-change-proposal-2026-03-10.md#Update-2 — Dashboard section]

## Tasks / Subtasks

### Update 3: Confidence Score Display Fix (zero risk, instant value)

- [x] **Task 1: Fix confidence display in MatchCard** (AC: #11)
  - [x]In `pm-arbitrage-dashboard/src/components/MatchCard.tsx` line 63: remove `* 100` — change `(match.confidenceScore * 100).toFixed(0)` to `match.confidenceScore.toFixed(0)`

### Update 2: Low-Score Match Caching (standalone backend + frontend)

- [x] **Task 2: Add `LLM_MIN_REVIEW_THRESHOLD` env var + threshold validation** (AC: #9)
  - [x]Add to `.env.example` and `.env.development`: `LLM_MIN_REVIEW_THRESHOLD=40`
  - [x]In `CandidateDiscoveryService` constructor: `this.minReviewThreshold = Number(this.configService.get<number>('LLM_MIN_REVIEW_THRESHOLD', 40))`
  - [x]In `onModuleInit()` (after threshold reads): validate `this.minReviewThreshold < this.autoApproveThreshold` — if not, throw `ConfigValidationError` with message explaining the misconfiguration

- [x] **Task 3: Three-tier scoring in `processCandidate()`** (AC: #7, #8, #9)
  - [x]Add `const isBelowReviewThreshold = result.score < this.minReviewThreshold` after line 246
  - [x]Update `operatorRationale` in `prisma.contractMatch.create()` to three-tier: auto-approved → existing string, below review threshold → `"Auto-rejected: below review threshold (score: ${result.score}, threshold: ${this.minReviewThreshold})"`, otherwise → `null`
  - [x]Update post-create logic: auto-approved → existing events, below review threshold → `stats.autoRejected++` (no event), otherwise → pending review event

- [x] **Task 4: Update `DiscoveryRunStats`** (AC: #10)
  - [x]Add `autoRejected: number` to `DiscoveryRunStats` interface in `discovery-run-completed.event.ts`
  - [x]Initialize `autoRejected: 0` in the stats object in `runDiscovery()`

- [x] **Task 5: Auto-rejected visual indicator in dashboard** (AC: #12)
  - [x]Add `'auto-rejected'` to `DerivedStatus` type union
  - [x]Update `deriveStatus()`: after `operatorApproved` check, add `if (match.operatorRationale?.startsWith('Auto-rejected:')) return 'auto-rejected'` before the generic `rejected` check
  - [x]Add `statusConfig['auto-rejected']`: `{ border: 'border-l-slate-400', badge: 'bg-slate-500/10 text-slate-500', badgeLabel: 'AUTO-REJECTED' }`
  - [x]Update `isRejected` check: `const isRejected = status === 'rejected' || status === 'auto-rejected'`
  - [x]Search `MatchCard.tsx` for ALL references to `isRejected` or `status === 'rejected'` and ensure they include `'auto-rejected'` — currently only one usage (line 33, opacity), but verify no others were added

### Update 1: clobTokenId Storage & Contract ID Correction (largest change)

- [x] **Task 6: Prisma schema migration** (AC: #1)
  - [x]Add `polymarketClobTokenId String? @map("polymarket_clob_token_id")` to `ContractMatch` model after `polymarketContractId`
  - [x]Add `@@index([polymarketClobTokenId])` to indexes
  - [x]Run `pnpm prisma migrate dev --name add-polymarket-clob-token-id`
  - [x]Run `pnpm prisma generate`

- [x] **Task 7: `ContractSummary` interface update** (AC: #2)
  - [x]Add `clobTokenId?: string` to `ContractSummary` in `common/interfaces/contract-catalog-provider.interface.ts`

- [x] **Task 8: `PolymarketCatalogProvider` — extract clobTokenId** (AC: #2)
  - [x]Add `clobTokenIds?: string[]` to `PolymarketMarket` interface
  - [x]In `mapToContractSummary()`: add `clobTokenId: market.clobTokenIds?.[0]` to the returned object

- [x] **Task 9: `CandidateDiscoveryService` — store both IDs** (AC: #3)
  - [x]In `processCandidate()` `prisma.contractMatch.create()` data: add `polymarketClobTokenId: polyContract.clobTokenId ?? null`

- [x] **Task 10: `ContractPairDto` — required YAML field** (AC: #4)
  - [x]Add `@IsString() @IsNotEmpty() polymarketClobTokenId!: string` to `ContractPairDto`

- [x] **Task 11: `ContractPairConfig` runtime type** (AC: #4)
  - [x]Add `polymarketClobTokenId: string` (non-optional) to `ContractPairConfig` interface

- [x] **Task 12: `ContractPairLoaderService` — pass through + validation gate** (AC: #4, #5)
  - [x]In `toPairConfig()`: add `polymarketClobTokenId: dto.polymarketClobTokenId`
  - [x]In `getActivePairs()` or after loading pairs from DB-sourced approved matches: filter out pairs where `polymarketClobTokenId` is null/undefined with warning log

- [x] **Task 13: `ContractMatchSyncService` — sync new field** (AC: #4)
  - [x]Add `polymarketClobTokenId: pair.polymarketClobTokenId` to both `create` and `update` blocks in the upsert

- [x] **Task 14: Add `polymarketClobTokenId` to `MatchSummaryDto`** (AC: #1)
  - [x]In `src/dashboard/dto/match-approval.dto.ts` line 75: add `@ApiPropertyOptional({ type: String }) polymarketClobTokenId!: string | null;` after `polymarketContractId`
  - [x]Update `MatchApprovalService.listMatches()` and `getMatchById()` (or wherever `MatchSummaryDto` is populated from Prisma results) to include `polymarketClobTokenId` from the `ContractMatch` record

- [x] **Task 15: Regenerate dashboard API client** (AC: #1)
  - [x]Prerequisite: Tasks 6-14 complete, backend compiles and runs via `pnpm start:dev`
  - [x]Start engine backend: `pnpm start:dev` (required for Swagger JSON endpoint)
  - [x]In `pm-arbitrage-dashboard/`: `pnpm generate-api` (reads from `http://127.0.0.1:8080/api/docs-json`)
  - [x]Verify `MatchSummaryDto` in generated `Api.ts` now includes `polymarketClobTokenId`

- [x] **Task 16: CLOB consumer updates** (AC: #6)
  - [x]`detection.service.ts` line 89: `pair.polymarketClobTokenId` for `getOrderBook()`
  - [x]`data-ingestion.service.ts` line 122: `pair.polymarketClobTokenId` for batch token list
  - [x]`execution.service.ts` lines 143, 146, 1023: `polymarketClobTokenId` for primary/secondary contract ID selection and orderbook fetch
  - [x]`exit-monitor.service.ts` lines 262, 405, 407: `polymarketClobTokenId` for close price and primary/secondary contract ID
  - [x]`position-close.service.ts` lines 190, 232, 234: `polymarketClobTokenId` for orderbook and contract ID
  - [x]`single-leg-resolution.service.ts` lines 478, 483, 541: `polymarketClobTokenId` for `getContractId()` helper and orderbook fetch
  - [x]`exposure-alert-scheduler.service.ts` line 73: `polymarketClobTokenId` for orderbook fetch

- [x] **Task 17: Update example YAML config** (AC: #4)
  - [x]Add `polymarketClobTokenId` to every pair in `config/contract-pairs.example.yaml`
  - [x]Update header comments to document new field
  - [x]Existing `polymarketContractId` values change from clobTokenIds to conditionIds (hex hashes)

### Testing

- [x] **Task 18: Update existing tests** (AC: #1-12)
  - [x]`candidate-discovery.service.spec.ts` — update mock data to include `clobTokenId` on ContractSummary; add tests for three-tier scoring (auto-reject below 40, pending 40-84, auto-approve ≥85); verify `autoRejected` in stats
  - [x]`polymarket-catalog-provider.spec.ts` — verify `clobTokenId` mapped from `clobTokenIds[0]`; verify missing `clobTokenIds` → undefined
  - [x]`contract-pair.dto.spec.ts` — verify validation fails when `polymarketClobTokenId` missing
  - [x]`contract-pair-loader.service.spec.ts` — verify `toPairConfig()` maps `polymarketClobTokenId`; verify pairs without `polymarketClobTokenId` filtered from active set
  - [x]`contract-match-sync.service.spec.ts` — verify upsert includes `polymarketClobTokenId`
  - [x]`detection.service.spec.ts` — update mock pairs to include `polymarketClobTokenId`; verify it's used for `getOrderBook()`
  - [x]`execution.service.spec.ts` — update mock pairs; verify CLOB calls use `polymarketClobTokenId`
  - [x]`exit-monitor.service.spec.ts` — update mock pairs
  - [x]`position-close.service.spec.ts` — update mock pairs
  - [x]`single-leg-resolution.service.spec.ts` — update mock pairs
  - [x]`exposure-alert-scheduler.service.spec.ts` — update mock pairs
  - [x]`data-ingestion.service.spec.ts` — update mock pairs
  - [x]`discovery-run-completed.event.spec.ts` — verify `autoRejected` in stats

- [x] **Task 19: Run full suite and lint** (AC: #1-12)
  - [x]`cd pm-arbitrage-engine && pnpm lint`
  - [x]`pnpm test` — all 96+ test files must pass

## Dev Notes

### Implementation Order — FOLLOW THIS SEQUENCE

1. **Update 3** (confidence display fix) — one-line fix, zero risk, instant value
2. **Update 2** (three-tier scoring) — standalone backend + frontend, no schema change
3. **Update 1** (clobTokenId) — schema migration, 7+ CLOB consumer files, config format change, API client regen

This order minimizes risk: each update is independently deployable and testable.

### Prisma Migration

**CRITICAL:** Run `pnpm prisma migrate dev --name add-polymarket-clob-token-id` BEFORE modifying any service that references `polymarketClobTokenId`. Prisma Client won't know about the new field until `pnpm prisma generate` runs (implicit in `migrate dev`).

Schema change is additive (nullable column). No data migration needed — DB was recently reset.

```prisma
model ContractMatch {
  matchId                   String    @id @default(uuid()) @map("match_id")
  polymarketContractId      String    @map("polymarket_contract_id")
  polymarketClobTokenId     String?   @map("polymarket_clob_token_id")  // NEW
  kalshiContractId          String    @map("kalshi_contract_id")
  // ... rest unchanged ...

  @@index([polymarketClobTokenId])  // NEW
  // ... existing indexes unchanged ...
}
```

[Source: sprint-change-proposal-2026-03-10.md#Update-1; prisma/schema.prisma lines 66-98]

### `MatchSummaryDto` Backend Update

**File:** `src/dashboard/dto/match-approval.dto.ts` (line 73-92)

The Swagger/OpenAPI schema is generated from this DTO. Without adding `polymarketClobTokenId`, the dashboard API client regeneration (Task 17) won't include the new field. Add after `polymarketContractId` (line 75):

```typescript
@ApiProperty({ nullable: true, type: String, description: 'Polymarket CLOB token ID for trading (null for auto-discovered pairs without CLOB mapping)' })
polymarketClobTokenId!: string | null;
```

Also verify `match-approval.service.ts` (or wherever `MatchSummaryDto` is populated from Prisma results) maps `polymarketClobTokenId` from the `ContractMatch` record.

[Source: pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts lines 73-92; Lad review finding #1]

### Threshold Misconfiguration Guard

In `CandidateDiscoveryService.onModuleInit()`, validate thresholds after reading env vars:

```typescript
if (this.minReviewThreshold >= this.autoApproveThreshold) {
  throw new ConfigValidationError(
    `LLM_MIN_REVIEW_THRESHOLD (${this.minReviewThreshold}) must be less than LLM_AUTO_APPROVE_THRESHOLD (${this.autoApproveThreshold})`,
  );
}
```

Without this, setting `LLM_MIN_REVIEW_THRESHOLD=90` and `LLM_AUTO_APPROVE_THRESHOLD=85` would cause all scores 85-89 to be both auto-approved AND below the review threshold. The `isAutoApproved` check runs first so it would auto-approve, but the intent is clearly wrong.

[Source: Lad review finding — threshold precedence risk]

### Why `polymarketContractId` Is NOT Renamed

`polymarketContractId` stays as-is everywhere. It holds the `conditionId` (hex hash) — a market-level identifier used for: unique constraint, display, identification, knowledge base lookups. The new `polymarketClobTokenId` holds the CLOB token ID (large decimal) — required for all CLOB operations (orderbook, order placement, price queries). These are semantically distinct Polymarket identifiers.

| Field | Contains | Used For |
|-------|----------|----------|
| `polymarketContractId` | `conditionId` (hex) | Market data, display, identification, unique constraint |
| `polymarketClobTokenId` (NEW) | `clobTokenIds[0]` (YES token) | Orderbook queries, order placement, price queries |

[Source: sprint-change-proposal-2026-03-10.md#Update-1]

### CLOB Consumer Update — Complete File List

These 7 service files switch from `polymarketContractId` to `polymarketClobTokenId` for CLOB operations:

| File | Usage | Change |
|------|-------|--------|
| `detection.service.ts:89` | `getOrderBook()` | `pair.polymarketClobTokenId` |
| `data-ingestion.service.ts:122` | batch token list | `pair.polymarketClobTokenId` |
| `execution.service.ts:143,146,1023` | primary/secondary contract ID, orderbook | `polymarketClobTokenId` |
| `exit-monitor.service.ts:262,405,407` | close price, primary/secondary contract ID | `polymarketClobTokenId` |
| `position-close.service.ts:190,232,234` | orderbook, primary/secondary contract ID | `polymarketClobTokenId` |
| `single-leg-resolution.service.ts:478,483,541` | `getContractId()` helper, orderbook | `polymarketClobTokenId` |
| `exposure-alert-scheduler.service.ts:73` | orderbook | `polymarketClobTokenId` |

**Display-only consumers (NO change needed):** `match-approval.service.ts`, `knowledge-base.service.ts`, `dashboard.service.ts`, `position-enrichment.service.ts`, `compliance-config.ts`, event classes, `contract-match-sync.service.ts`, `contract-pair-loader.service.ts:findPairByContractId()`.

[Source: sprint-change-proposal-2026-03-10.md#Update-1; verified via codebase grep — 43 files reference polymarketContractId, 7 use it for CLOB operations]

### Validation Gate — No Fallbacks

Pairs without `polymarketClobTokenId` are excluded from the trading pipeline. **No silent fallback** to `polymarketContractId` for CLOB calls.

- **Manual config:** `polymarketClobTokenId` is required in `ContractPairDto` — startup fails if missing
- **Auto-discovered pairs:** pairs with null `polymarketClobTokenId` stay in knowledge base for display but don't enter detection/execution

**Gate enforcement in `ContractPairLoaderService.getActivePairs()`** (line 35):

```typescript
getActivePairs(): ContractPairConfig[] {
  return this.activePairs.filter((pair) => {
    if (!pair.polymarketClobTokenId) {
      this.logger.warn({
        message: 'Excluding pair from trading pipeline — missing polymarketClobTokenId',
        data: { matchId: pair.matchId, polymarketContractId: pair.polymarketContractId },
      });
      return false;
    }
    return true;
  });
}
```

For manual config pairs, this filter never triggers (DTO validation catches it at startup). For DB-sourced approved pairs merged via `MatchApprovedEvent` handler, this catches auto-discovered pairs that lack clobTokenId.

**Current state:** `getActivePairs()` currently returns only YAML-loaded pairs (line 36: `return [...this.activePairs]`). The filter is forward-looking — it will be needed when DB-sourced approved matches are dynamically added to the active pair set (not yet implemented). For this story, the filter ensures the gate exists at the single entry point all trading pipeline consumers use, so future DB-sourced pair loading automatically benefits.

[Source: sprint-change-proposal-2026-03-10.md#Update-1; contract-pair-loader.service.ts lines 35-37]

### `ContractPairConfig` Type Change Impact

Adding `polymarketClobTokenId: string` (non-optional) to `ContractPairConfig` will cause TypeScript compilation errors everywhere `ContractPairConfig` objects are constructed without it. **This is intentional** — the compiler catches every site that needs updating. In spec files, update mock `ContractPairConfig` objects to include `polymarketClobTokenId: 'mock-clob-token-id'`.

[Source: contract-pair-config.type.ts lines 1-13]

### Three-Tier Scoring Logic

| Score Range | Behavior | DB State | Event |
|-------------|----------|----------|-------|
| `>= 85` | Auto-approved, enters trading pipeline | `operatorApproved: true`, rationale set | `MATCH_APPROVED` + `MATCH_AUTO_APPROVED` |
| `>= 40` and `< 85` | Pending operator review | `operatorApproved: false`, `operatorRationale: null` | `MATCH_PENDING_REVIEW` |
| `< 40` | Auto-rejected, cached to prevent re-scoring | `operatorApproved: false`, rationale: `"Auto-rejected: ..."` | None (silent cache) |

Threshold `LLM_MIN_REVIEW_THRESHOLD` (default 40) is configurable via env var.

In `processCandidate()`, the change is minimal — add `isBelowReviewThreshold` check and split the else branch:

```typescript
const isAutoApproved = result.score >= this.autoApproveThreshold;
const isBelowReviewThreshold = result.score < this.minReviewThreshold;

// operatorRationale in create:
operatorRationale: isAutoApproved
  ? `Auto-approved by discovery pipeline (score: ${result.score}, model: ${result.model}, escalated: ${result.escalated})`
  : isBelowReviewThreshold
    ? `Auto-rejected: below review threshold (score: ${result.score}, threshold: ${this.minReviewThreshold})`
    : null,

// Post-create:
if (isAutoApproved) {
  stats.autoApproved++;
  // ... existing event emission ...
} else if (isBelowReviewThreshold) {
  stats.autoRejected++;
  // No event — silent cache
} else {
  stats.pendingReview++;
  // ... existing MATCH_PENDING_REVIEW event ...
}
```

[Source: sprint-change-proposal-2026-03-10.md#Update-2; candidate-discovery.service.ts lines 246-300]

### Dashboard Auto-Rejected Status

Add `'auto-rejected'` to `DerivedStatus` type. Detection logic uses string prefix matching on `operatorRationale`:

```typescript
type DerivedStatus = 'pending' | 'approved' | 'rejected' | 'auto-rejected';

function deriveStatus(match: MatchSummaryDto): DerivedStatus {
  if (match.operatorApproved) return 'approved';
  if (match.operatorRationale?.startsWith('Auto-rejected:')) return 'auto-rejected';
  if (match.operatorRationale) return 'rejected';
  return 'pending';
}

// statusConfig addition:
'auto-rejected': {
  border: 'border-l-slate-400',
  badge: 'bg-slate-500/10 text-slate-500',
  badgeLabel: 'AUTO-REJECTED',
},
```

Update `isRejected`: `const isRejected = status === 'rejected' || status === 'auto-rejected'`

The existing `buildWhereFilter()` in `match-approval.service.ts:190-201` already separates pending (`operatorRationale: null`) from rejected (`operatorRationale: { not: null }`). Auto-rejected matches are excluded from the pending queue automatically.

[Source: sprint-change-proposal-2026-03-10.md#Update-2; pm-arbitrage-dashboard/src/components/MatchCard.tsx lines 7-33]

### Example YAML Config Update

```yaml
pairs:
  - polymarketContractId: '0x3b449890af58c2e6d7e1c0e2795ddaacc5e04e3a7c90e91eb8e6b01a57df4c12'
    polymarketClobTokenId: '82155281377141165143204560708045813743531231692081828482927028490588408258574'
    kalshiContractId: 'KXLOSEMAJORITY-27JAN01'
    eventDescription: 'Will Republicans lose the House majority before the midterms?'
    operatorVerificationTimestamp: '2026-11-03T10:30:00Z'
    primaryLeg: polymarket
```

`polymarketContractId` now holds the conditionId (hex hash), not the clobTokenId. `polymarketClobTokenId` holds the large decimal string used for CLOB operations.

[Source: sprint-change-proposal-2026-03-10.md#Update-1; config/contract-pairs.example.yaml]

### Environment Variables (New)

Add to `.env.example` and `.env.development`:
```bash
# Three-tier scoring (Story 8.5)
LLM_MIN_REVIEW_THRESHOLD=40    # Scores below this are auto-rejected (cached, no operator review)
```

[Source: sprint-change-proposal-2026-03-10.md#Update-2]

### Cross-Epic Impact Warning

**Epic 9, Story 9.3** (Confidence-Adjusted Position Sizing): Uses `confidenceScore` in formula `adjusted size = base_size × confidence_score`. Since score is stored as 0-100 (not 0-1), implementation MUST divide by 100: `base_size × (confidence_score / 100)`. Without this, position sizes would be 100x too large.

**Epic 10, Story 10.2**: Exit criterion #2 references confidence score for threshold comparison. Same division-by-100 applies.

**ACTION REQUIRED after this story ships:** Update the sprint-status.yaml or epics.md with a dev note on Story 9.3: _"confidenceScore is stored as 0-100 (integer), not 0.0-1.0. Position sizing formula must be: `base_size × (confidence_score / 100)`. Without this division, position sizes will be 100x too large."_ Same note for Story 10.2. This prevents the knowledge from living only in this story's notes.

[Source: sprint-change-proposal-2026-03-10.md#Section-2 — Epic Impact]

### Scope Boundaries — What This Story Does NOT Do

- **No REST endpoint for clobTokenId lookup.** Operators update YAML config manually.
- **No auto-population of clobTokenId for existing auto-discovered pairs.** New discovery runs will populate it; existing pairs need operator intervention or re-discovery.
- **No changes to `ConfidenceScorerService`.** Three-tier logic is in `CandidateDiscoveryService.processCandidate()` only.
- **No changes to `PreFilterService`.** Scoring tiers are post-LLM-scoring logic.
- **No `findPairByContractId()` changes.** It searches by `polymarketContractId` (conditionId) — correct for identification lookups.

### Project Structure Notes

**Files to modify (pm-arbitrage-engine/):**
- `prisma/schema.prisma` — add `polymarketClobTokenId` field + index
- `src/common/interfaces/contract-catalog-provider.interface.ts` — add `clobTokenId` to `ContractSummary`
- `src/common/events/discovery-run-completed.event.ts` — add `autoRejected` to `DiscoveryRunStats`
- `src/connectors/polymarket/polymarket-catalog-provider.ts` — `PolymarketMarket` interface + `mapToContractSummary()`
- `src/modules/contract-matching/candidate-discovery.service.ts` — three-tier scoring + `polymarketClobTokenId` storage
- `src/modules/contract-matching/types/contract-pair-config.type.ts` — add `polymarketClobTokenId`
- `src/modules/contract-matching/dto/contract-pair.dto.ts` — add `polymarketClobTokenId` field with validators
- `src/modules/contract-matching/contract-pair-loader.service.ts` — `toPairConfig()` mapping + `getActivePairs()` gate
- `src/modules/contract-matching/contract-match-sync.service.ts` — upsert field
- `src/modules/arbitrage-detection/detection.service.ts` — CLOB consumer
- `src/modules/data-ingestion/data-ingestion.service.ts` — CLOB consumer
- `src/modules/execution/execution.service.ts` — CLOB consumer
- `src/modules/exit-management/exit-monitor.service.ts` — CLOB consumer
- `src/modules/execution/position-close.service.ts` — CLOB consumer
- `src/modules/execution/single-leg-resolution.service.ts` — CLOB consumer
- `src/modules/execution/exposure-alert-scheduler.service.ts` — CLOB consumer
- `src/dashboard/dto/match-approval.dto.ts` — add `polymarketClobTokenId` to `MatchSummaryDto`
- `src/dashboard/match-approval.service.ts` — map `polymarketClobTokenId` in DTO population
- `config/contract-pairs.example.yaml` — add field + update values
- `.env.example` — add `LLM_MIN_REVIEW_THRESHOLD`
- `.env.development` — add `LLM_MIN_REVIEW_THRESHOLD`

**Files to modify (pm-arbitrage-dashboard/):**
- `src/components/MatchCard.tsx` — confidence display fix + auto-rejected status

**Files to modify (test files):**
- `src/modules/contract-matching/candidate-discovery.service.spec.ts`
- `src/connectors/polymarket/polymarket-catalog-provider.spec.ts`
- `src/modules/contract-matching/dto/contract-pair.dto.spec.ts`
- `src/modules/contract-matching/contract-pair-loader.service.spec.ts`
- `src/modules/contract-matching/contract-match-sync.service.spec.ts`
- `src/modules/arbitrage-detection/detection.service.spec.ts`
- `src/modules/execution/execution.service.spec.ts`
- `src/modules/exit-management/exit-monitor.service.spec.ts`
- `src/modules/execution/position-close.service.spec.ts`
- `src/modules/execution/single-leg-resolution.service.spec.ts`
- `src/modules/execution/exposure-alert-scheduler.service.spec.ts`
- `src/modules/data-ingestion/data-ingestion.service.spec.ts`
- `src/common/events/discovery-run-completed.event.spec.ts`

**New files:**
- `prisma/migrations/*_add_polymarket_clob_token_id/migration.sql` (auto-generated)

**No files to delete.**

### Testing Strategy

- **Framework:** Vitest 4 + `@golevelup/ts-vitest` for NestJS mocks [Source: Serena memory tech_stack]
- **Co-located:** spec files next to source files
- **Key new test cases:**
  - Three-tier scoring: auto-reject (score < 40), pending review (40-84), auto-approve (≥85)
  - `autoRejected` counter in `DiscoveryRunStats`
  - `polymarketClobTokenId` validation: required in DTO, mapped in loader, stored in sync, used in CLOB consumers
  - Validation gate: pair without clobTokenId excluded from `getActivePairs()`
  - `ContractPairConfig` mock updates across all CLOB consumer spec files
- **Baseline:** 96 test files, 1626 passed, 2 todo (1628 total). All must remain green.

### References

- [Source: sprint-change-proposal-2026-03-10.md] — Full issue analysis, impact assessment, and detailed change proposals for all 3 updates
- [Source: epics.md#Epic-8] — Epic context, FR coverage (FR-AD-05, FR-AD-06, FR-AD-07, FR-CM-02-05)
- [Source: sprint-change-proposal-2026-03-10.md#Section-2] — Cross-epic impact: Story 9.3, Story 10.2 confidence score division-by-100
- [Source: pm-arbitrage-engine/prisma/schema.prisma lines 66-98] — Current ContractMatch model (verified: no polymarketClobTokenId)
- [Source: pm-arbitrage-engine/src/common/interfaces/contract-catalog-provider.interface.ts lines 1-18] — Current ContractSummary (verified: no clobTokenId)
- [Source: pm-arbitrage-engine/src/connectors/polymarket/polymarket-catalog-provider.ts lines 13-18] — Current PolymarketMarket (verified: no clobTokenIds)
- [Source: pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.ts lines 246-300] — Current binary scoring logic (verified: no three-tier)
- [Source: pm-arbitrage-engine/src/common/events/discovery-run-completed.event.ts lines 3-11] — Current DiscoveryRunStats (verified: no autoRejected)
- [Source: pm-arbitrage-engine/src/modules/contract-matching/types/contract-pair-config.type.ts lines 1-13] — Current ContractPairConfig (verified: no polymarketClobTokenId)
- [Source: pm-arbitrage-engine/src/modules/contract-matching/dto/contract-pair.dto.ts lines 1-80] — Current ContractPairDto (verified: no polymarketClobTokenId)
- [Source: pm-arbitrage-engine/src/modules/contract-matching/contract-pair-loader.service.ts lines 35-37, 158-168] — getActivePairs() and toPairConfig()
- [Source: pm-arbitrage-engine/src/modules/contract-matching/contract-match-sync.service.ts lines 57-78] — upsert block
- [Source: pm-arbitrage-engine/config/contract-pairs.example.yaml] — Current example (stores clobTokenIds in polymarketContractId)
- [Source: pm-arbitrage-dashboard/src/components/MatchCard.tsx line 63] — Confidence display bug: `(match.confidenceScore * 100)`
- [Source: pm-arbitrage-dashboard/src/components/MatchCard.tsx lines 7-33] — DerivedStatus, deriveStatus(), statusConfig, isRejected
- [Source: pm-arbitrage-dashboard/src/api/generated/Api.ts lines 255-268] — Current MatchSummaryDto (no polymarketClobTokenId)
- [Source: pm-arbitrage-dashboard/package.json line 11] — `generate-api` script command

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None — clean implementation, no debugging required.

### Completion Notes List

- **Implementation order followed:** Update 3 (display fix) → Update 2 (three-tier scoring) → Update 1 (clobTokenId) as specified in Dev Notes
- **ConfigValidationError requires 2 args** (message + validationErrors array) — not mentioned in story, discovered during implementation
- **Prisma nullable field handling:** `polymarketClobTokenId` is `String?` in Prisma schema, so CLOB consumer services accessing positions with `include: { pair: true }` get `string | null`. Used non-null assertion `!` at CLOB operation call sites since the validation gate in `getActivePairs()` guarantees non-null for trading pipeline pairs.
- **`single-leg-resolution.service.ts` method signatures:** Changed `getContractId()` and `buildPnlScenarios()` to accept `string | null` for `polymarketClobTokenId` parameter with internal `!` assertion, since Prisma-sourced positions pass nullable fields.
- **`contract-pairs.yaml` (active config):** Updated to include `polymarketClobTokenId` and changed `polymarketContractId` to a conditionId hex hash. Without this, e2e tests fail at DTO validation.
- **ContractMatchSyncService unchanged check:** Lad MCP review caught that the `polymarketClobTokenId` field was missing from the "unchanged" comparison in `syncPairsToDatabase()`. Fixed to include `polymarketClobTokenId` check — otherwise config corrections would be silently skipped.
- **Test results:** 96 test files pass, 1639 tests (up from 1635 post-implementation baseline), 4 boundary-value tests added during code review, 0 failures, 2 todo (pre-existing).
- **Cross-epic impact note:** confidenceScore is stored as 0-100 (integer). Story 9.3 and 10.2 must divide by 100 when using it in formulas (`base_size × (confidence_score / 100)`).

### File List

**pm-arbitrage-engine/ (source files modified):**
- `prisma/schema.prisma` — added `polymarketClobTokenId` field + index
- `prisma/migrations/*_add_polymarket_clob_token_id/migration.sql` — auto-generated
- `src/common/interfaces/contract-catalog-provider.interface.ts` — added `clobTokenId` to `ContractSummary`
- `src/common/events/discovery-run-completed.event.ts` — added `autoRejected` to `DiscoveryRunStats`
- `src/connectors/polymarket/polymarket-catalog-provider.ts` — `PolymarketMarket.clobTokenIds` + `mapToContractSummary`
- `src/modules/contract-matching/candidate-discovery.service.ts` — three-tier scoring, `minReviewThreshold`, `polymarketClobTokenId` storage
- `src/modules/contract-matching/types/contract-pair-config.type.ts` — added `polymarketClobTokenId`
- `src/modules/contract-matching/dto/contract-pair.dto.ts` — added `polymarketClobTokenId` validator
- `src/modules/contract-matching/contract-pair-loader.service.ts` — `toPairConfig()` mapping + `getActivePairs()` gate
- `src/modules/contract-matching/contract-match-sync.service.ts` — upsert + unchanged check
- `src/dashboard/dto/match-approval.dto.ts` — added `polymarketClobTokenId` to `MatchSummaryDto`
- `src/dashboard/match-approval.service.ts` — `toSummaryDto()` maps `polymarketClobTokenId`
- `src/modules/arbitrage-detection/detection.service.ts` — CLOB consumer
- `src/modules/data-ingestion/data-ingestion.service.ts` — CLOB consumer
- `src/modules/execution/execution.service.ts` — CLOB consumer
- `src/modules/exit-management/exit-monitor.service.ts` — CLOB consumer
- `src/modules/execution/position-close.service.ts` — CLOB consumer
- `src/modules/execution/single-leg-resolution.service.ts` — CLOB consumer
- `src/modules/execution/exposure-alert-scheduler.service.ts` — CLOB consumer
- `config/contract-pairs.example.yaml` — updated with new field + conditionId values
- `config/contract-pairs.yaml` — updated active config with new field
- `.env.example` — added `LLM_MIN_REVIEW_THRESHOLD`
- `.env.development` — added `LLM_MIN_REVIEW_THRESHOLD`

**pm-arbitrage-engine/ (spec files modified):**
- `src/modules/contract-matching/candidate-discovery.service.spec.ts`
- `src/connectors/polymarket/polymarket-catalog-provider.spec.ts`
- `src/modules/contract-matching/dto/contract-pair.dto.spec.ts`
- `src/modules/contract-matching/contract-pair-loader.service.spec.ts`
- `src/modules/contract-matching/contract-match-sync.service.spec.ts`
- `src/modules/arbitrage-detection/detection.service.spec.ts`
- `src/modules/execution/execution.service.spec.ts`
- `src/modules/exit-management/exit-monitor.service.spec.ts`
- `src/modules/execution/position-close.service.spec.ts`
- `src/modules/execution/single-leg-resolution.service.spec.ts`
- `src/modules/execution/exposure-alert-scheduler.service.spec.ts`
- `src/modules/data-ingestion/data-ingestion.service.spec.ts`
- `src/common/events/discovery-run-completed.event.spec.ts`

**pm-arbitrage-dashboard/ (modified):**
- `src/components/MatchCard.tsx` — confidence display fix + auto-rejected status
- `src/api/generated/Api.ts` — regenerated with `polymarketClobTokenId`

### Senior Developer Review (AI)

**Reviewer:** Claude Opus 4.6 (code review agent)
**Date:** 2026-03-10

**Review Findings:**
- **H1 (HIGH) — FIXED:** Unstaged changes in `contract-match-sync.service.ts` + spec containing the `polymarketClobTokenId` unchanged-check. Staged for commit.
- **M1 (MEDIUM) — FIXED:** Added 4 boundary-value tests for three-tier scoring thresholds (scores 39, 40, 84, 85) in `candidate-discovery.service.spec.ts`.
- **M2 (MEDIUM) — ACCEPTED:** 8 non-null assertions (`!`) on nullable `polymarketClobTokenId` in CLOB consumer files. Documented design choice — validation gate in `getActivePairs()` guarantees non-null for trading pipeline pairs.
- **L1 (LOW) — FIXED:** Corrected test count in Dev Agent Record completion notes.
- **L2 (LOW) — ACCEPTED:** No controller spec for `match-approval.controller.ts`. Pre-existing gap, not introduced by this story.

**Verdict:** All 12 ACs verified against implementation. All 19 tasks confirmed complete. 96 test files, 1639 tests passing, 0 failures.

**Status:** done
