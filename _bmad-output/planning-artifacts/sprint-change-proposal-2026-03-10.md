# Sprint Change Proposal — Contract Matching Bug Fixes & Improvements

**Date:** 2026-03-10
**Triggered by:** Epic 8 implementation (Stories 8.1, 8.2, 8.4)
**Scope classification:** Minor — Direct implementation by development team
**Author:** Bob (Scrum Master), reviewed with Arbi

---

## Section 1: Issue Summary

Three issues were identified during and after Epic 8's intelligent contract matching pipeline implementation:

### Issue 1: clobTokenId Storage & Contract ID Correction

Polymarket uses two semantically distinct identifiers:
- **`conditionId`** (hex hash) — identifies a market, used for Gamma API market data queries
- **`clobTokenId`** (large decimal) — identifies an outcome token, used for all CLOB operations (orderbook, order placement, prices)

The system has a single `polymarketContractId` field used for both purposes. Manual config rows store clobTokenIds (works for trading but wrong for market data). Auto-discovered rows store conditionIds from the Gamma API (correct for market data but CLOB calls would fail). The `PolymarketCatalogProvider` does not extract `clobTokenIds` from the Gamma API response at all.

**Evidence:** Polymarket API docs confirm CLOB endpoints require `token_id`, not `conditionId`. The `PolymarketMarket` interface in the catalog provider is missing the `clobTokenIds` field.

### Issue 2: Low-Score Match UI Noise

When the discovery pipeline scores a candidate pair below the auto-approve threshold (85), it persists the match and emits a `MATCH_PENDING_REVIEW` event. This is correct for plausible matches (e.g., score 45-84) but creates UI noise for junk matches (e.g., score 8%) that will never be approved. The operator's pending review queue fills with unmatchable pairs.

The caching behavior itself is correct — persisted matches prevent redundant LLM API calls on subsequent discovery runs via the duplicate check.

**Evidence:** `candidate-discovery.service.ts` lines 246-300 treat all sub-85 scores identically.

### Issue 3: Confidence Score Display Bug

The dashboard Matches page displays confidence as `9200%` instead of `92%`. The backend stores scores as 0-100 integers (validated in `knowledge-base.service.ts:25-32`). The frontend multiplies by 100 again.

**Evidence:** `MatchCard.tsx:63` — `(match.confidenceScore * 100).toFixed(0)%`. Only occurrence in the dashboard; no other files format `confidenceScore`.

---

## Section 2: Impact Analysis

### Epic Impact

**Epic 8 (in-progress):** Stories 8.1, 8.2, 8.4 are done but need corrective patches. Story 8.3 (Resolution Feedback Loop, backlog) is unaffected. A new story 8.5 addresses all three fixes within the existing epic structure.

**Epic 9 (backlog) — ACTION REQUIRED:** Story 9.3 (Confidence-Adjusted Position Sizing) uses `confidenceScore` in the formula `adjusted size = base_size × confidence_score`. The epics doc says "90% confidence → 90% of base size." Since the score is stored as 0-100 (not 0-1), the implementation MUST divide by 100: `base_size × (confidence_score / 100)`. Without this, position sizes would be 100x too large. **Add an explicit TODO/warning to the Story 9.3 backlog item now** — relying on the developer to read this sprint change doc is insufficient.

**Epic 10 (backlog):** Story 10.2 exit criterion #2 references confidence score for threshold comparison. Same division-by-100 consideration applies. Add a cross-reference note to the Story 10.2 backlog item.

**No epics invalidated, added, removed, or resequenced.**

### Artifact Conflicts

**PRD:** No conflicts with core goals. The PRD specifies "confidence scoring 0-100%" and "auto-approve ≥85%, queue <85%" — consistent with the backend. Only the frontend display is wrong.

**PRD artifact note:** The PRD's knowledge base schema (line 1158) shows `polymarket_contract_id` with example `"0x3a4b..."` (a conditionId format), while the existing `contract-pairs.example.yaml` stores large decimal strings (clobTokenIds) in `polymarketContractId`. This pre-existing inconsistency is resolved by Update 1: `polymarketContractId` now consistently holds the conditionId (hex hash), matching the PRD example, and the new `polymarketClobTokenId` field holds the trading token ID.

**Architecture:** Data model change — new `polymarketClobTokenId` column on `ContractMatch`. Catalog provider interface gains `clobTokenId` field. No architectural pattern changes.

**UI/UX:** `MatchCard.tsx` fix for confidence display. New `auto-rejected` visual status (slate color badge) for low-score cached matches. No wireframe or flow changes.

**Other:** Prisma migration required. Test updates for affected services. Config documentation update.

---

## Section 3: Recommended Approach

**Path:** Direct Adjustment — one new story (8.5) addressing all three issues within Epic 8.

**Rationale:** All three issues are localized bug fixes with clear root causes. No architectural rethinking required. The fixes are additive (new schema field, new scoring tier, one-line display fix). The CLOB consumer updates are the highest-risk change but are well-bounded — 8 files switching from `polymarketContractId` to `polymarketClobTokenId`, with a validation gate ensuring the field is always populated before reaching the trading pipeline.

**Effort estimate:** Low (1-2 day story)
**Risk level:** Low-Medium (CLOB consumer updates touch the critical trading path — needs thorough test coverage)
**Timeline impact:** None — fits within current Epic 8 scope

---

## Section 4: Detailed Change Proposals

### Update 1: clobTokenId Storage & Contract ID Correction

#### Schema Change

**File:** `pm-arbitrage-engine/prisma/schema.prisma` (line 68)

```
OLD:
model ContractMatch {
  matchId                   String    @id @default(uuid()) @map("match_id")
  polymarketContractId      String    @map("polymarket_contract_id")
  kalshiContractId          String    @map("kalshi_contract_id")

NEW:
model ContractMatch {
  matchId                   String    @id @default(uuid()) @map("match_id")
  polymarketContractId      String    @map("polymarket_contract_id")
  polymarketClobTokenId     String?   @map("polymarket_clob_token_id")
  kalshiContractId          String    @map("kalshi_contract_id")
```

- Nullable in Prisma (auto-discovered pairs may not have it initially)
- Required at the trading pipeline boundary (validation gate)
- New index: `@@index([polymarketClobTokenId])`
- No data migration — DB was recently reset, no existing rows

#### What Gets Renamed vs. What's New

**Nothing is renamed.** `polymarketContractId` stays as-is everywhere.

**One new field added:** `polymarketClobTokenId` — stores the CLOB token ID for trading operations.

| Field | Contains | Used For |
|-------|----------|----------|
| `polymarketContractId` | `conditionId` (hex) | Market data, display, identification, unique constraint |
| `polymarketClobTokenId` (NEW) | `clobTokenIds[0]` (YES token) | Orderbook queries, order placement, price queries |

#### Catalog Provider — Extract clobTokenId from Gamma API

**File:** `pm-arbitrage-engine/src/connectors/polymarket/polymarket-catalog-provider.ts`

```
OLD (lines 13-18):
interface PolymarketMarket {
  conditionId: string;
  question: string;
  description?: string;
  endDate?: string;
}

NEW:
interface PolymarketMarket {
  conditionId: string;
  clobTokenIds?: string[];
  question: string;
  description?: string;
  endDate?: string;
}
```

`mapToContractSummary()` (lines 96-111):

```
OLD:
return {
  contractId: market.conditionId,
  ...
};

NEW:
return {
  contractId: market.conditionId,
  clobTokenId: market.clobTokenIds?.[0],
  ...
};
```

#### ContractSummary Interface

**File:** `pm-arbitrage-engine/src/common/interfaces/contract-catalog-provider.interface.ts`

Add: `clobTokenId?: string;` — Polymarket-only, CLOB token ID for trading.

#### CandidateDiscoveryService — Store Both IDs

**File:** `pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.ts` (lines 248-265)

```
OLD:
polymarketContractId: polyContract.contractId,

NEW:
polymarketContractId: polyContract.contractId,
polymarketClobTokenId: polyContract.clobTokenId ?? null,
```

#### ContractPairConfig Runtime Type

**File:** `pm-arbitrage-engine/src/modules/contract-matching/types/contract-pair-config.type.ts`

```
OLD:
export interface ContractPairConfig {
  polymarketContractId: string;
  kalshiContractId: string;
  ...
}

NEW:
export interface ContractPairConfig {
  polymarketContractId: string;
  polymarketClobTokenId: string;
  kalshiContractId: string;
  ...
}
```

Non-optional on the runtime type — validation gate guarantees it.

#### ContractPairDto — Required YAML Field

**File:** `pm-arbitrage-engine/src/modules/contract-matching/dto/contract-pair.dto.ts`

Add `polymarketClobTokenId` with `@IsString() @IsNotEmpty()` — required field, validation error if missing from YAML config.

#### ContractPairLoaderService — Pass Through

**File:** `pm-arbitrage-engine/src/modules/contract-matching/contract-pair-loader.service.ts` (line 158-168)

Add `polymarketClobTokenId: dto.polymarketClobTokenId` to `toPairConfig()`.

#### ContractMatchSyncService — Sync New Field

**File:** `pm-arbitrage-engine/src/modules/contract-matching/contract-match-sync.service.ts` (lines 57-78)

Add `polymarketClobTokenId` to both `create` and `update` blocks in the upsert.

#### Example YAML Config

**File:** `pm-arbitrage-engine/config/contract-pairs.example.yaml`

```yaml
# Fields:
#   polymarketContractId     - Polymarket condition ID (required, hex hash from Gamma API)
#   polymarketClobTokenId    - Polymarket CLOB token ID (required, large decimal string for YES outcome)
#   kalshiContractId         - Kalshi ticker (required, e.g. KXEVENT-YYMM format)
#   eventDescription         - Human-readable event description (required, min 3 chars)
#   operatorVerificationTimestamp - ISO 8601 datetime when operator verified (required)
#   primaryLeg               - Which platform to execute first: "kalshi" (default) or "polymarket" (optional)

pairs:
  - polymarketContractId: '0x3b449890af58c2e6d7e1c0e2795ddaacc5e04e3a7c90e91eb8e6b01a57df4c12'
    polymarketClobTokenId: '82155281377141165143204560708045813743531231692081828482927028490588408258574'
    kalshiContractId: 'KXLOSEMAJORITY-27JAN01'
    eventDescription: 'Will Republicans lose the House majority before the midterms?'
    operatorVerificationTimestamp: '2026-11-03T10:30:00Z'
    primaryLeg: polymarket
```

#### Validation Gate — No Fallbacks

Pairs without `polymarketClobTokenId` are excluded from the trading pipeline. No silent fallback to `polymarketContractId` for CLOB calls.

- **Manual config:** `polymarketClobTokenId` is required in `ContractPairDto` — startup fails if missing
- **Auto-discovered pairs:** pairs with null `polymarketClobTokenId` stay in knowledge base for display but don't enter detection/execution

**Gate enforcement location:** `ContractPairLoaderService.getActivePairs()` in `contract-pair-loader.service.ts:35`. This method is the single entry point for all trading pipeline consumers (`DetectionService`, `DataIngestionService`, `TradingEngineService`). For manual config pairs, the gate is already enforced by `ContractPairDto` validation at startup (missing `polymarketClobTokenId` = validation error). For auto-discovered pairs loaded from DB into the active pair set (via `MatchApprovedEvent` handler or similar), the `getActivePairs()` method must filter out any pair where `polymarketClobTokenId` is null, with a warning log:

```typescript
// In getActivePairs() or wherever DB-sourced approved pairs are merged:
if (!pair.polymarketClobTokenId) {
  this.logger.warn({
    message: 'Excluding pair from trading pipeline — missing polymarketClobTokenId',
    data: { matchId: pair.matchId, polymarketContractId: pair.polymarketContractId },
  });
  continue; // or filter
}
```

#### CLOB Consumer Updates (8 files)

All switch from `polymarketContractId` to `polymarketClobTokenId`:

| File | Line(s) | Change |
|------|---------|--------|
| `detection.service.ts` | 88-89 | `getOrderBook(pair.polymarketClobTokenId)` |
| `execution.service.ts` | 140-147 | `dislocation.pairConfig.polymarketClobTokenId` |
| `exit-monitor.service.ts` | 260-265, 403-408 | `position.pair.polymarketClobTokenId` |
| `position-close.service.ts` | close orders | `polymarketClobTokenId` |
| `data-ingestion.service.ts` | batch fetch | `pair.polymarketClobTokenId` |
| `exposure-alert-scheduler.service.ts` | orderbook queries | `polymarketClobTokenId` |
| `single-leg-resolution.service.ts` | hedge orders | `polymarketClobTokenId` |

#### Display-Only Consumers (no change)

`match-approval.service.ts`, `knowledge-base.service.ts`, `dashboard.service.ts`, `position-enrichment.service.ts`, `compliance-config.ts`, event classes, `contract-match-sync.service.ts`, `contract-pair-loader.service.ts:findPairByContractId()` — all continue using `polymarketContractId`.

#### Dashboard Frontend (no change for this update)

`MatchCard.tsx:50`, `MatchApprovalDialog.tsx:57`, `Api.ts:265` — display `polymarketContractId`. API client regenerated after backend changes.

---

### Update 2: Low-Score Match Caching

#### Three-Tier Scoring Logic

| Score Range | Behavior | DB State |
|-------------|----------|----------|
| `>= 85` (auto-approve) | Auto-approved, enters trading pipeline | `operatorApproved: true`, rationale set |
| `>= 40` and `< 85` | Pending operator review | `operatorApproved: false`, `operatorRationale: null` |
| `< 40` (min review) | Auto-rejected, cached to prevent re-scoring | `operatorApproved: false`, rationale: `"Auto-rejected: ..."` |

Threshold (`LLM_MIN_REVIEW_THRESHOLD`, default 40) is configurable via env var — tunable without redeploy, adjust after observing score distribution in production.

#### File Changes

**File:** `pm-arbitrage-engine/src/modules/contract-matching/candidate-discovery.service.ts`

Constructor — add:
```typescript
this.minReviewThreshold = Number(
  this.configService.get<number>('LLM_MIN_REVIEW_THRESHOLD', 40),
);
```

`processCandidate()` (lines 246-300) — three-tier logic:
```typescript
const isAutoApproved = result.score >= this.autoApproveThreshold;
const isBelowReviewThreshold = result.score < this.minReviewThreshold;

// In create data:
operatorRationale: isAutoApproved
  ? `Auto-approved by discovery pipeline (score: ${result.score}, ...)`
  : isBelowReviewThreshold
    ? `Auto-rejected: below review threshold (score: ${result.score}, threshold: ${this.minReviewThreshold})`
    : null,

// After create:
if (isAutoApproved) {
  stats.autoApproved++;
  // emit MATCH_APPROVED + MATCH_AUTO_APPROVED
} else if (isBelowReviewThreshold) {
  stats.autoRejected++;
  // no event — silent cache
} else {
  stats.pendingReview++;
  // emit MATCH_PENDING_REVIEW
}
```

`DiscoveryStats` — add `autoRejected: number` counter. Included in `DiscoveryRunCompletedEvent` payload.

#### Dashboard — Auto-Rejected Visual Indicator

**File:** `pm-arbitrage-dashboard/src/components/MatchCard.tsx`

New derived status `'auto-rejected'` with slate color badge, distinguished from operator-rejected (red):

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

Auto-rejected matches appear in the "rejected" tab (existing filter picks them up via `operatorRationale: { not: null }`), visually distinct from operator-rejected matches.

**`isRejected` usage update:** The existing code uses `isRejected` at line 30 (`const isRejected = status === 'rejected'`) and line 33 (`isRejected && 'opacity-60'`). With the new `'auto-rejected'` status, this check must be updated. Use a helper to avoid scattering the logic:

```typescript
// Line 30 — replace:
const isRejected = status === 'rejected';

// With:
const isRejected = status === 'rejected' || status === 'auto-rejected';
```

Only one usage site (line 33, opacity). No other places in `MatchCard.tsx` check `isRejected` or `status === 'rejected'` directly — the action buttons (line 76) check `status === 'pending'` which is unaffected.

#### Why No Other Changes Are Needed

The existing `buildWhereFilter()` in `match-approval.service.ts:190-201` already separates pending (`operatorRationale: null`) from rejected (`operatorRationale: { not: null }`). Auto-rejected matches are excluded from the pending queue automatically.

---

### Update 3: Confidence Score Display Bug

#### Single-Line Fix

**File:** `pm-arbitrage-dashboard/src/components/MatchCard.tsx` (line 63)

```
OLD:
Confidence: {match.confidenceScore !== null ? `${(match.confidenceScore * 100).toFixed(0)}%` : 'N/A (manual pair)'}

NEW:
Confidence: {match.confidenceScore !== null ? `${match.confidenceScore.toFixed(0)}%` : 'N/A (manual pair)'}
```

Only occurrence of `confidenceScore` formatting in the dashboard. Verified: `MatchApprovalDialog.tsx` does not display confidence, `Api.ts` and `ws-events.ts` are type definitions only.

---

## Section 5: Implementation Handoff

**Change scope:** Minor — direct implementation by development team.

**Deliverable:** Story 8.5 covering all three updates, implemented via strict TDD workflow.

**Implementation order:**
1. Update 3 (confidence display fix) — zero risk, instant value
2. Update 2 (low-score caching) — standalone backend + frontend change
3. Update 1 (clobTokenId) — largest change, schema migration + 8 CLOB consumers + config format
4. Regenerate dashboard API client (`pnpm generate-api` in `pm-arbitrage-dashboard/`) — required after Update 1 adds `polymarketClobTokenId` to `MatchSummaryDto`, must happen before dashboard code referencing the new field compiles

**Success criteria:**
- All existing tests pass after changes
- New tests cover: validation gate for missing `polymarketClobTokenId`, three-tier scoring logic, auto-rejected dashboard rendering
- Manual verification: confidence displays correctly, auto-rejected matches appear in rejected tab with slate badge, YAML config without `polymarketClobTokenId` fails at startup
- `pnpm lint` and `pnpm test` pass

**Post-implementation:**
- Operator updates `contract-pairs.yaml` to include `polymarketClobTokenId` for all pairs
- Monitor `autoRejected` stat in discovery run logs to tune `LLM_MIN_REVIEW_THRESHOLD`

---

**Sprint Status Update:** Add story `8-5-contract-matching-bugfixes` with status `backlog` to `sprint-status.yaml` under Epic 8.
