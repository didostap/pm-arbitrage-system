# Story 3.4: Contract Match Approval Workflow (MVP)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want to review and approve contract pair matches that need verification,
so that I maintain zero-tolerance accuracy on which contracts are paired.

**FRs covered:** FR-AD-04 (Operator can manually approve contract matches with confidence <85%), FR-CM-01 (Manual curation of 20-30 contract pairs in config file)

## Acceptance Criteria

### AC1: Config Pairs Marked as Operator-Approved at Startup

**Given** a contract pair exists in the `config/contract-pairs.yaml` file
**When** it is loaded at startup by `ContractPairLoaderService.onModuleInit()`
**Then** it is marked as "operator-approved" with the configured `operatorVerificationTimestamp` (FR-AD-04)
**And** no automated matching occurs — all pairs are manually curated for MVP
**And** approval status is tracked in the `contract_matches` database table

### AC2: New Pair Addition via Config + Restart

**Given** the operator wants to add a new contract pair
**When** they edit `config/contract-pairs.yaml` and restart the engine
**Then** the new pair is active immediately
**And** the system logs the new pair addition at `log` level with: event description, both contract IDs, and operator verification timestamp
**And** a new row is inserted into the `contract_matches` table with `operator_approved: true`

### AC3: Prisma Migration for contract_matches Table

**Given** the Prisma schema needs contract match tracking
**When** this story is implemented
**Then** a `contract_matches` table is created via Prisma migration with fields:
- `match_id` (UUID, primary key)
- `polymarket_contract_id` (string, not null)
- `kalshi_contract_id` (string, not null)
- `polymarket_description` (string, nullable — populated from YAML `eventDescription` for MVP, platform-specific descriptions in Epic 8)
- `kalshi_description` (string, nullable — same as above)
- `operator_approved` (boolean, default false)
- `operator_approval_timestamp` (timestamptz, nullable)
- `operator_rationale` (text, nullable — always null for config-seeded pairs; populated by Epic 7/8 approval workflows)
- `first_traded_timestamp` (timestamptz, nullable)
- `total_cycles_traded` (integer, default 0)
- `created_at` (timestamptz, default now)
- `updated_at` (timestamptz, auto-updated)
**And** unique constraint on `(polymarket_contract_id, kalshi_contract_id)` to prevent duplicate pairs
**And** index on `operator_approved` for filtering queries
**And** only the fields listed above are included — future fields (`confidence_score`, `resolution_criteria_hash`, `resolution_diverged`, etc.) are added by Epic 8's own migration

### AC4: Config Pair Seeding into Database at Startup

**Given** config pairs are loaded successfully by `ContractPairLoaderService`
**When** startup completes
**Then** each config pair is upserted into the `contract_matches` table:
- If pair already exists (matched by `polymarket_contract_id` + `kalshi_contract_id`): update `operator_approved = true`, update timestamps
- If pair is new: insert with `operator_approved = true`, `operator_approval_timestamp` from config's `operatorVerificationTimestamp`
**And** pairs that exist in DB but are no longer in config are NOT deleted (preserve historical tracking) but are no longer returned by `getActivePairs()`
**And** seeding is logged: `"Contract matches seeded to database"` with count of inserted/updated/unchanged

### AC5: ContractMatchSyncService Created

**Given** the contract match sync logic needs a dedicated service
**When** `ContractMatchSyncService` is implemented
**Then** it is created in `src/modules/contract-matching/contract-match-sync.service.ts`
**And** it implements `OnModuleInit` to run seeding after `ContractPairLoaderService` has loaded pairs
**And** it injects `PrismaService` and `ContractPairLoaderService`
**And** it is registered in `ContractMatchingModule` as a provider
**And** the module imports `PersistenceModule` (or relies on `@Global()` `PrismaService`)

### AC6: Pair Removal Tracking

**Given** a pair previously existed in config but has been removed
**When** the engine restarts with the updated config
**Then** the DB record is preserved with `operator_approved` unchanged (historical data)
**And** `ContractPairLoaderService.getActivePairs()` returns only pairs from the current config (unchanged behavior)
**And** a `log` level entry is emitted listing pairs in DB but not in config: `"Inactive contract matches detected"` with count

### AC7: Existing Test Suite Regression

**Given** all Story 3.4 changes are complete
**When** `pnpm test` runs
**Then** all 367 existing tests continue to pass
**And** new tests for `ContractMatchSyncService` add 12+ test cases
**And** `pnpm lint` passes with no errors

## Tasks / Subtasks

- [x] Task 1: Create Prisma Migration for contract_matches Table (AC: #3)
  - [x] 1.1 Add `ContractMatch` model to `prisma/schema.prisma` with all fields from AC3
  - [x] 1.2 Add `@@map("contract_matches")` and `@map` annotations for snake_case DB columns
  - [x] 1.3 Add unique constraint `@@unique([polymarketContractId, kalshiContractId])`
  - [x] 1.4 Add index `@@index([operatorApproved])`
  - [x] 1.5 Run `pnpm prisma migrate dev --name add-contract-matches-table`
  - [x] 1.6 Run `pnpm prisma generate` to regenerate client

- [x] Task 2: Create ContractMatchSyncService (AC: #1, #2, #4, #5, #6)
  - [x] 2.1 Create `src/modules/contract-matching/contract-match-sync.service.ts`
  - [x] 2.2 Inject `PrismaService` and `ContractPairLoaderService`
  - [x] 2.3 Implement `OnModuleInit` with `syncPairsToDatabase()` method
  - [x] 2.4 For each active config pair, upsert into `contract_matches`:
    - Match on `polymarket_contract_id` + `kalshi_contract_id`
    - Set `operator_approved = true`, `operator_approval_timestamp` from config
    - Set `polymarket_description` and `kalshi_description` from `eventDescription`
  - [x] 2.5 Query DB for pairs NOT in current config, log as inactive (AC6)
  - [x] 2.6 Log summary: inserted, updated, unchanged, inactive counts

- [x] Task 3: Update ContractMatchingModule (AC: #5)
  - [x] 3.1 Add `ContractMatchSyncService` to providers in `contract-matching.module.ts`
  - [x] 3.2 Verify `PrismaService` is available (globally exported from PersistenceModule)

- [x] Task 4: Write Tests (AC: #7)
  - [x] 4.1 Create `src/modules/contract-matching/contract-match-sync.service.spec.ts`
  - [x] 4.2 Test: syncs config pairs to database on module init
  - [x] 4.3 Test: upserts existing pairs (updates operator_approved and timestamps)
  - [x] 4.4 Test: inserts new pairs that don't exist in DB
  - [x] 4.5 Test: detects and logs inactive pairs (in DB but not in config)
  - [x] 4.6 Test: does not delete removed pairs from DB
  - [x] 4.7 Test: handles empty config pairs gracefully (should not happen per 3.1 validation, but defensive)
  - [x] 4.8 Test: sets polymarket_description and kalshi_description from eventDescription
  - [x] 4.9 Test: sets operator_approval_timestamp from config's operatorVerificationTimestamp
  - [x] 4.10 Test: logs summary with correct counts
  - [x] 4.11 Test: handles database errors gracefully (logs error, does not crash startup)
  - [x] 4.12 Test: concurrent pairs with same polymarket ID but different kalshi IDs (unique constraint boundary)
  - [x] 4.13 Test: pair with null/undefined operatorVerificationTimestamp (null handling)
  - [x] 4.14 Run full regression: `pnpm test` — 358 unit tests pass (e2e timeouts pre-existing, not caused by this story)

- [x] Task 5: Lint & Final Check (AC: #7)
  - [x] 5.1 Run `pnpm lint` and fix any issues
  - [x] 5.2 Verify no import boundary violations

## Dev Notes

### Architecture Constraints

- `ContractMatchSyncService` lives in `src/modules/contract-matching/` — same module as `ContractPairLoaderService`
- Allowed imports per CLAUDE.md dependency rules:
  - `modules/contract-matching/` → `common/` (types, errors)
  - `modules/contract-matching/` → `persistence/` (via globally exported PrismaService)
- The module already has `ContractPairLoaderService` registered and exported

### PrismaService Access Pattern

`PrismaService` is globally available via `@Global()` decorator on `PersistenceModule`. No need to import `PersistenceModule` in `ContractMatchingModule`.

```typescript
import { PrismaService } from '../../common/prisma.service';

@Injectable()
export class ContractMatchSyncService implements OnModuleInit {
  private readonly logger = new Logger(ContractMatchSyncService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly pairLoader: ContractPairLoaderService,
  ) {}

  async onModuleInit(): Promise<void> {
    await this.syncPairsToDatabase();
  }
}
```

### Prisma Model Definition

```prisma
model ContractMatch {
  matchId                    String    @id @default(uuid()) @map("match_id")
  polymarketContractId       String    @map("polymarket_contract_id")
  kalshiContractId           String    @map("kalshi_contract_id")
  polymarketDescription      String?   @map("polymarket_description")
  kalshiDescription          String?   @map("kalshi_description")
  operatorApproved           Boolean   @default(false) @map("operator_approved")
  operatorApprovalTimestamp  DateTime? @map("operator_approval_timestamp") @db.Timestamptz
  operatorRationale          String?   @map("operator_rationale")
  firstTradedTimestamp       DateTime? @map("first_traded_timestamp") @db.Timestamptz
  totalCyclesTraded          Int       @default(0) @map("total_cycles_traded")
  createdAt                  DateTime  @default(now()) @map("created_at") @db.Timestamptz
  updatedAt                  DateTime  @updatedAt @map("updated_at") @db.Timestamptz

  @@unique([polymarketContractId, kalshiContractId])
  @@index([operatorApproved])
  @@map("contract_matches")
}
```

### Upsert Pattern

Use Prisma's `upsert` for idempotent seeding:

```typescript
for (const pair of activePairs) {
  await this.prisma.contractMatch.upsert({
    where: {
      polymarketContractId_kalshiContractId: {
        polymarketContractId: pair.polymarketContractId,
        kalshiContractId: pair.kalshiContractId,
      },
    },
    update: {
      operatorApproved: true,
      operatorApprovalTimestamp: pair.operatorVerificationTimestamp,
      polymarketDescription: pair.eventDescription,
      kalshiDescription: pair.eventDescription,
    },
    create: {
      polymarketContractId: pair.polymarketContractId,
      kalshiContractId: pair.kalshiContractId,
      polymarketDescription: pair.eventDescription,
      kalshiDescription: pair.eventDescription,
      operatorApproved: true,
      operatorApprovalTimestamp: pair.operatorVerificationTimestamp,
    },
  });
}
```

### Inactive Pair Detection

After seeding, query for DB pairs not in current config. At MVP scale (20-30 pairs), `findMany()` on the full table is trivial. If pair count grows significantly (Epic 8+), consider filtering server-side with `NOT IN` clause.

```typescript
const dbPairs = await this.prisma.contractMatch.findMany({
  select: { polymarketContractId: true, kalshiContractId: true },
});
const configPairKeys = new Set(
  activePairs.map(p => `${p.polymarketContractId}:${p.kalshiContractId}`),
);
const inactivePairs = dbPairs.filter(
  db => !configPairKeys.has(`${db.polymarketContractId}:${db.kalshiContractId}`),
);
if (inactivePairs.length > 0) {
  this.logger.log({
    message: 'Inactive contract matches detected',
    data: { count: inactivePairs.length, pairs: inactivePairs.map(p => p.polymarketContractId) },
  });
}
```

### OnModuleInit Ordering

NestJS does NOT guarantee `OnModuleInit` execution order between providers in the same module. **Solution:** `ContractMatchSyncService.onModuleInit()` should defensively check `this.pairLoader.getActivePairs()` — if it returns an empty array, log a warning and skip seeding. In practice, `ContractPairLoaderService` will have already loaded pairs because NestJS resolves the dependency graph before calling lifecycle hooks, but do NOT rely on declaration order. The defensive check handles edge cases gracefully.

### Description Fields — MVP Simplification

For MVP, both `polymarket_description` and `kalshi_description` are populated from the YAML `eventDescription` field (same value for both). In Epic 8, when semantic matching is introduced, these will be populated from each platform's actual contract description fetched via the respective connector APIs.

### What NOT to Do (Scope Guard)

- Do NOT implement confidence scoring — that's Epic 8 (`confidence_score` not in this migration)
- Do NOT implement resolution tracking — that's Epic 8 (`resolution_diverged`, etc.)
- Do NOT create REST API endpoints for match approval — Epic 7 (Story 7.3) builds the dashboard UI
- Do NOT implement auto-approve/queue logic — that's Epic 8 (FR-AD-06)
- Do NOT modify `DetectionService` or `EdgeCalculatorService` — they don't interact with the DB table
- Do NOT implement `KnowledgeBaseService` — that's Epic 8
- Do NOT delete pairs from DB when they're removed from config — preserve historical tracking

### Existing Codebase Patterns to Follow

- **File naming:** kebab-case (`contract-match-sync.service.ts`)
- **Module registration:** See `contract-matching.module.ts` — add ContractMatchSyncService as provider
- **Logging:** Use NestJS `Logger` — `private readonly logger = new Logger(ContractMatchSyncService.name)`
- **Prisma access:** Inject `PrismaService` directly (globally available)
- **OnModuleInit pattern:** See `ContractPairLoaderService.onModuleInit()` for reference

### Testing Strategy

- Mock `PrismaService` with mock `contractMatch` methods (`upsert`, `findMany`)
- Mock `ContractPairLoaderService.getActivePairs()` to return test config pairs
- Use `Test.createTestingModule()` from `@nestjs/testing`
- Test both the happy path (sync works) and error cases (DB failure during upsert)
- Do NOT use a real database — unit tests only with mocked Prisma

### Dependencies — All Already Installed

| Package | Purpose | Installed In |
|---------|---------|-------------|
| `@prisma/client` | Database access via PrismaService | Epic 1 |
| `prisma` | Migration CLI | Epic 1 |
| `@nestjs/common` | OnModuleInit, Logger, Injectable | Epic 1 |

No new dependencies needed.

### Previous Story Intelligence (3.3)

- **367 tests passing** — regression gate baseline
- `ContractPairLoaderService` loads pairs from YAML config, validates, stores in memory
- `ContractPairConfig` has: `polymarketContractId`, `kalshiContractId`, `eventDescription`, `operatorVerificationTimestamp` (Date), `primaryLeg` ('kalshi' | 'polymarket')
- `ContractMatchingModule` exports `ContractPairLoaderService`
- `PrismaService` is `@Global()` via `PersistenceModule` — available everywhere
- No `contract_matches` table exists yet in Prisma schema
- Existing tables: `system_metadata`, `order_book_snapshots`, `platform_health_logs`

### Git Intelligence

Recent engine commits follow pattern: `feat: <description>`. Story 3.4 should use:
- `feat: add contract matches table and startup sync from config pairs`

### Project Structure Notes

New files to create:
```
prisma/migrations/<timestamp>_add_contract_matches_table/migration.sql  (auto-generated)
src/modules/contract-matching/contract-match-sync.service.ts
src/modules/contract-matching/contract-match-sync.service.spec.ts
```

Modified files:
```
prisma/schema.prisma                                           (add ContractMatch model)
src/modules/contract-matching/contract-matching.module.ts      (add ContractMatchSyncService provider)
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4 — acceptance criteria]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.1 — downstream scope (fields NOT to build)]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture — PostgreSQL, Prisma pattern]
- [Source: _bmad-output/implementation-artifacts/3-1-manual-contract-pair-configuration.md — ContractPairLoaderService API]
- [Source: pm-arbitrage-engine/src/modules/contract-matching/types/contract-pair-config.type.ts — ContractPairConfig interface]
- [Source: pm-arbitrage-engine/src/modules/contract-matching/contract-matching.module.ts — module structure]
- [Source: pm-arbitrage-engine/src/common/prisma.service.ts — PrismaService pattern]
- [Source: pm-arbitrage-engine/src/common/persistence.module.ts — @Global() PrismaService export]
- [Source: pm-arbitrage-engine/prisma/schema.prisma — existing models and conventions]
- [Source: CLAUDE.md#Module Dependency Rules — contract-matching module constraints]
- [Source: CLAUDE.md#Naming Conventions — DB tables snake_case, Prisma @map]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None

### Completion Notes List

- Migration `20260216220521_add_contract_matches_table` created and applied
- `ContractMatchSyncService` implements `OnModuleInit`, defensively handles empty pairs and DB errors
- Uses `findUnique` before `upsert` to track inserted/updated/unchanged counts accurately
- Both `polymarketDescription` and `kalshiDescription` set from `eventDescription` (MVP simplification)
- Inactive pair detection queries all DB pairs and compares with config set
- 14 new unit tests (12 original + 2 from code review), all passing. 381 total tests pass
- E2E test timeouts are pre-existing (confirmed by running without changes) — not caused by this story
- `eslint-disable @typescript-eslint/no-unsafe-assignment` added to spec file with justification comment (vitest `expect.objectContaining` returns `any`)
- Code review fix: unchanged pairs now skip `upsert` (no spurious `updatedAt` drift)
- Code review fix: added `onModuleInit` lifecycle hook test
- Code review fix: out-of-scope changes (polymarket connector, detection service) unstaged from this story's commit

### File List

- `prisma/schema.prisma` — added `ContractMatch` model
- `prisma/migrations/20260216220521_add_contract_matches_table/migration.sql` — auto-generated migration
- `src/modules/contract-matching/contract-match-sync.service.ts` — new service
- `src/modules/contract-matching/contract-match-sync.service.spec.ts` — 12 unit tests
- `src/modules/contract-matching/contract-matching.module.ts` — added `ContractMatchSyncService` provider
