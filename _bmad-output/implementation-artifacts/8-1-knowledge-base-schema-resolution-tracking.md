# Story 8.1: Knowledge Base Schema & Resolution Tracking

Status: done

## Story

As an operator,
I want the contract matching knowledge base to track resolution outcomes and divergence,
So that matching accuracy improves over time from real data.

## Acceptance Criteria

1. **Given** the `contract_matches` table exists from Epic 3
   **When** this story is implemented
   **Then** a Prisma migration adds: `confidence_score` (Float, nullable), `resolution_criteria_hash` (String, nullable), `polymarket_resolution` (String, nullable), `kalshi_resolution` (String, nullable), `resolution_timestamp` (DateTime Timestamptz, nullable), `resolution_diverged` (Boolean, nullable), `divergence_notes` (String, nullable)
   [Source: epics.md#Story-8.1; FR-CM-03]

2. **Given** the expanded schema is in place
   **When** consumers need to read/write knowledge base data
   **Then** `KnowledgeBaseService` provides CRUD operations: create match entries with confidence scores, update resolution fields, query matches by resolution status (resolved/unresolved/diverged), and retrieve resolution statistics
   [Source: epics.md#Story-8.1; FR-CM-03; architecture.md#contract-matching directory]

3. **Given** both platforms have resolved a matched contract pair
   **When** `KnowledgeBaseService.recordResolution()` is called with both platform outcomes
   **Then** outcomes are persisted to the match record, divergence is computed (polymarket vs kalshi resolution mismatch), `resolution_diverged` is set accordingly, and a `ResolutionDivergedEvent` is emitted if divergence is detected
   [Source: epics.md#Story-8.1; FR-CM-04; Derived: trigger mechanism deferred to Story 8.3]

4. **Given** the dashboard already returns `confidenceScore: null` from `MatchApprovalService.toSummaryDto()`
   **When** a `ContractMatch` record has a non-null `confidenceScore` in the DB
   **Then** the dashboard returns the actual value instead of hardcoded null
   [Derived from: dashboard/match-approval.service.ts:210 hardcoded null; dashboard/dto/match-approval.dto.ts:84 "null until Epic 8"]

## Tasks / Subtasks

- [x] **Task 1: Prisma schema migration** (AC: #1)
  - [x] Add 7 new fields to `ContractMatch` model in `schema.prisma`
  - [x] Add index on `resolution_diverged` for divergence queries
  - [x] Add index on `confidence_score` for scored-match queries
  - [x] Run `pnpm prisma migrate dev --name add-knowledge-base-resolution-fields`
  - [x] Run `pnpm prisma generate`

- [x] **Task 2: Resolution divergence event** (AC: #3)
  - [x] Add `RESOLUTION_DIVERGED` to `EVENT_NAMES` in `event-catalog.ts`
  - [x] Create `ResolutionDivergedEvent` class in `common/events/`
  - [x] Export `ResolutionDivergedEvent` from `common/events/index.ts` barrel

- [x] **Task 3: KnowledgeBaseService — core CRUD** (AC: #2)
  - [x] Create `knowledge-base.service.ts` in `modules/contract-matching/`
  - [x] Implement `updateConfidenceScore(matchId, score, criteriaHash?)` — sets confidence_score and optional resolution_criteria_hash
  - [x] Implement `recordResolution(matchId, polyResolution, kalshiResolution, notes?)` — persists outcomes, computes divergence, emits event if diverged
  - [x] Implement `findByResolutionStatus(status: 'resolved' | 'unresolved' | 'diverged')` — query helpers
  - [x] Implement `getResolutionStats()` — aggregate counts (total resolved, diverged count, divergence rate)
  - [x] Register in `ContractMatchingModule` providers and exports

- [x] **Task 4: Dashboard confidence score wiring** (AC: #4)
  - [x] Update `MatchApprovalService.toSummaryDto()` to read `match.confidenceScore ?? null` instead of hardcoded `null`

- [x] **Task 5: Tests** (AC: #1-4)
  - [x] `knowledge-base.service.spec.ts` — CRUD operations, divergence detection logic, event emission, edge cases (re-recording, null inputs)
  - [x] Update `match-approval.service.spec.ts` — verify `confidenceScore` is forwarded from DB mock
  - [x] Verify migration runs cleanly (manual check)

## Dev Notes

### Prisma Schema Changes

Add to the `ContractMatch` model in `pm-arbitrage-engine/prisma/schema.prisma` (after `resolutionDate` field, line ~78):

```prisma
confidenceScore          Float?    @map("confidence_score")
resolutionCriteriaHash   String?   @map("resolution_criteria_hash")
polymarketResolution     String?   @map("polymarket_resolution")
kalshiResolution         String?   @map("kalshi_resolution")
resolutionTimestamp      DateTime? @map("resolution_timestamp") @db.Timestamptz
resolutionDiverged       Boolean?  @map("resolution_diverged")
divergenceNotes          String?   @map("divergence_notes")
```

Add indexes:
```prisma
@@index([resolutionDiverged])
@@index([confidenceScore])
```

**Existing field note:** `resolutionDate` (line 78) is the *expected* contract resolution date. `resolutionTimestamp` is *when the resolution outcome was actually recorded*. These are distinct concepts — do not conflate them.

### KnowledgeBaseService Design

- **Location:** `src/modules/contract-matching/knowledge-base.service.ts`
- **Injects:** `PrismaService`, `EventEmitter2` [Source: established pattern in ContractMatchSyncService and MatchApprovalService]
- **DB access:** Use `PrismaService` directly (no repository). Matches existing pattern — `ContractMatchSyncService` (line 35) and `MatchApprovalService` (line 76) both use `this.prisma.contractMatch.*` directly. [Source: pm-arbitrage-engine/src/modules/contract-matching/contract-match-sync.service.ts; pm-arbitrage-engine/src/dashboard/match-approval.service.ts]
- **Logging:** Use NestJS `Logger` with structured JSON (message + data object). [Source: code_style memory; all existing services follow this pattern]
- **confidence_score is a percentage (0-100), NOT a monetary value** — native `Float` is correct, no `decimal.js` needed. [Source: epics.md#Story-8.2 "confidence score (0-100%)"]

**Divergence computation logic in `recordResolution()`:**
```typescript
// Normalize to lowercase trim before comparison
const polyNorm = polyResolution.toLowerCase().trim();
const kalshiNorm = kalshiResolution.toLowerCase().trim();
const diverged = polyNorm !== kalshiNorm;
```

If diverged, emit `ResolutionDivergedEvent` via `EventEmitter2`. Do NOT block on event emission (async fan-out pattern). [Source: CLAUDE.md#Communication Patterns]

**Normalization note:** The simple lowercase/trim comparison handles expected outcomes (YES/NO/INVALID). Platforms may use different terminology for equivalent outcomes — for now, log divergences for manual investigation. Story 8.3's feedback loop is where systematic pattern analysis would catch vocabulary mismatches and refine normalization.

### Event Addition

In `src/common/events/event-catalog.ts` (after `MATCH_REJECTED`, line ~147):
```typescript
RESOLUTION_DIVERGED: 'contract.match.resolution.diverged',
```

Create `src/common/events/resolution-diverged.event.ts` extending `BaseEvent` with fields: `matchId`, `polymarketResolution`, `kalshiResolution`, `divergenceNotes`.

### Dashboard Wiring

In `src/dashboard/match-approval.service.ts`, method `toSummaryDto()` (line ~210):
```typescript
// Change from:
confidenceScore: null,
// To:
confidenceScore: match.confidenceScore ?? null,
```

The `MatchSummaryDto` already declares `confidenceScore: number | null` (line 88) with the comment "Confidence score (null until Epic 8)" — no DTO changes needed, just update the comment if desired. [Source: pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts:84-88]

### Module Registration

In `src/modules/contract-matching/contract-matching.module.ts`:
- Add `KnowledgeBaseService` to `providers` array
- Add `KnowledgeBaseService` to `exports` array (Story 8.2's `ConfidenceScorerService` and Story 8.3's feedback loop will need it)

### Scope Boundaries — What This Story Does NOT Do

- **No automated resolution detection.** Story 8.1 provides the `recordResolution()` method. Story 8.3 wires up the automation that calls it.
- **No confidence scoring logic.** Story 8.1 stores scores. Story 8.2 implements `ConfidenceScorerService` that produces them.
- **No contract-match.repository.ts.** Architecture mentions this but existing code uses PrismaService directly. Follow the established pattern.
- **No REST endpoints for resolution recording.** Story 8.3 handles the API/automation surface.

### Project Structure Notes

Files to create:
- `src/modules/contract-matching/knowledge-base.service.ts`
- `src/modules/contract-matching/knowledge-base.service.spec.ts`
- `src/common/events/resolution-diverged.event.ts`

Files to modify:
- `prisma/schema.prisma` — add 7 fields + 3 indexes to `ContractMatch` (resolution_diverged, confidence_score, resolution_timestamp)
- `src/common/events/event-catalog.ts` — add `RESOLUTION_DIVERGED`
- `src/common/events/index.ts` — export `ResolutionDivergedEvent` from barrel
- `src/modules/contract-matching/contract-matching.module.ts` — register `KnowledgeBaseService`
- `src/dashboard/match-approval.service.ts` — wire `confidenceScore` from DB
- `src/dashboard/match-approval.service.spec.ts` — update mock to include `confidenceScore`
- `src/dashboard/dto/match-approval.dto.ts` — updated `confidenceScore` ApiProperty description

No files to delete.

### Resolution Normalization Note

`recordResolution()` normalizes platform outcome strings to lowercase/trimmed before storage. Original casing is intentionally discarded — platforms use inconsistent casing (YES/Yes/yes) and normalization ensures deterministic divergence comparison. Story 8.3's feedback loop is the appropriate place to add vocabulary-mapping if needed.

### Testing Strategy

- **Framework:** Vitest 4 + `@golevelup/ts-vitest` for NestJS mocks [Source: tech_stack memory]
- **Co-located:** `knowledge-base.service.spec.ts` next to `knowledge-base.service.ts`
- **Mock `PrismaService`** with `vi.fn()` on `contractMatch.update`, `contractMatch.findMany`, `contractMatch.findUnique`, `contractMatch.count` [Source: established pattern in contract-match-sync.service.spec.ts, match-approval.service.spec.ts]
- **Mock `EventEmitter2`** with `vi.fn()` on `emit` [Source: established pattern in match-approval.service.spec.ts]

Key test scenarios:
1. `updateConfidenceScore` — happy path, match not found
2. `recordResolution` — matching resolutions (no divergence), divergent resolutions (event emitted), re-recording (idempotent update), null notes
3. `findByResolutionStatus` — each filter variant
4. `getResolutionStats` — correct aggregation
5. Dashboard `toSummaryDto` — forwards `confidenceScore` value from mock, returns null when DB field is null

### References

- [Source: epics.md#Epic-8, Story 8.1] — AC and business context
- [Source: epics.md#Story-8.3] — Resolution feedback loop (downstream consumer of this story's schema)
- [Source: prd.md#FR-CM-03] — Knowledge base storage requirements
- [Source: prd.md#FR-CM-04] — Resolution outcome feedback
- [Source: prd.md#FR-AD-05, FR-AD-07] — Confidence scoring and knowledge accumulation
- [Source: architecture.md line 499-502] — Planned file structure for contract-matching module
- [Source: architecture.md line 604] — Dependency rule: contract-matching → persistence
- [Source: sprint-change-proposal-2026-03-09.md] — Story ordering context (8.1 → 8.2 → 8.4 → 8.3)
- [Source: pm-arbitrage-engine/prisma/schema.prisma lines 66-88] — Existing ContractMatch model
- [Source: pm-arbitrage-engine/src/dashboard/match-approval.service.ts line 210] — Hardcoded confidenceScore: null
- [Source: pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts lines 84-88] — DTO already has confidenceScore field
- [Source: pm-arbitrage-engine/src/modules/contract-matching/contract-matching.module.ts] — Current module registration
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts lines 145-147] — Existing match events

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- DB had drift (prior migration `20260307021134` recorded as applied but columns were missing). Resolved by re-applying column SQL manually, then creating a separate index migration `20260309131159_add_knowledge_base_indexes`.

### Completion Notes List

- Task 1: Added 7 fields to `ContractMatch` model + 2 indexes. Existing migration had columns without indexes; created separate index migration.
- Task 2: Added `RESOLUTION_DIVERGED` event to catalog, created `ResolutionDivergedEvent` class extending `BaseEvent`, exported from barrel.
- Task 3: Created `KnowledgeBaseService` with 4 methods: `updateConfidenceScore`, `recordResolution` (with case-insensitive divergence detection + event emission), `findByResolutionStatus`, `getResolutionStats`. Registered in `ContractMatchingModule` providers and exports.
- Task 4: Changed `confidenceScore: null` to `match.confidenceScore ?? null` in `MatchApprovalService.toSummaryDto()`.
- Task 5: Created `knowledge-base.service.spec.ts` (16 tests covering all CRUD, divergence detection, event emission, edge cases). Updated `match-approval.service.spec.ts` with test for forwarding `confidenceScore` from DB.
- Code Review Fix: Added empty/whitespace-only input validation to `recordResolution()` + 2 tests (empty polyResolution, whitespace-only kalshiResolution).
- Full suite: 85 test files, 1538 tests pass, 0 failures.

### File List

**Created:**
- `pm-arbitrage-engine/src/modules/contract-matching/knowledge-base.service.ts`
- `pm-arbitrage-engine/src/modules/contract-matching/knowledge-base.service.spec.ts`
- `pm-arbitrage-engine/src/common/events/resolution-diverged.event.ts`
- `pm-arbitrage-engine/prisma/migrations/20260309131159_add_knowledge_base_indexes/migration.sql`
- `pm-arbitrage-engine/prisma/migrations/20260309133254_add_resolution_timestamp_index/migration.sql`

**Modified:**
- `pm-arbitrage-engine/prisma/schema.prisma` — added 7 fields + 3 indexes to `ContractMatch` (resolution_diverged, confidence_score, resolution_timestamp)
- `pm-arbitrage-engine/src/common/events/event-catalog.ts` — added `RESOLUTION_DIVERGED`
- `pm-arbitrage-engine/src/common/events/index.ts` — exported `ResolutionDivergedEvent`
- `pm-arbitrage-engine/src/modules/contract-matching/contract-matching.module.ts` — registered `KnowledgeBaseService`
- `pm-arbitrage-engine/src/dashboard/match-approval.service.ts` — wired `confidenceScore` from DB
- `pm-arbitrage-engine/src/dashboard/match-approval.service.spec.ts` — added `confidenceScore` forwarding test
- `pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts` — updated `confidenceScore` ApiProperty description
