# Story 10-95.2: Hypertable Conversion — historical_prices & historical_depths

Status: done

## Story

As an operator,
I want the two largest time-series tables converted to hypertables with optimized indexes,
so that the database can handle long-term data growth efficiently without storage explosion.

## Acceptance Criteria

1. **historical_prices Hypertable Conversion** — **Given** `historical_prices` (180 GB, 248M rows) exists as a regular table, **When** the migration runs, **Then** `create_hypertable('historical_prices', 'timestamp', migrate_data => true, chunk_time_interval => INTERVAL '1 day')` succeeds **And** Prisma schema uses `@@id([id, timestamp])` composite PK.

2. **historical_depths Hypertable Conversion** — **Given** `historical_depths` (151 GB, 106M rows) exists as a regular table, **When** the migration runs, **Then** `create_hypertable('historical_depths', 'timestamp', migrate_data => true, chunk_time_interval => INTERVAL '1 day')` succeeds **And** Prisma schema uses `@@id([id, timestamp])` composite PK.

3. **Bloated Index Removal** — **Given** bloated/rarely-used indexes exist (76 GB total bloat), **When** hypertable conversion completes, **Then** the following indexes are dropped:
   - `historical_prices_contract_id_source_timestamp_idx` (27 GB, 23 scans)
   - `historical_prices_timestamp_idx` (2.1 GB, 32 scans)
   - `historical_depths_timestamp_idx` (2.9 GB, 28 scans)

4. **Backtesting Query Compatibility** — **Given** both tables are converted to hypertables, **When** backtesting queries run (price lookups, depth snapshots, OHLCV aggregation, aligned-price joins), **Then** all results match pre-migration output.

5. **Migration Backup & Scheduling** — **Given** the migration involves large data movement (~331 GB), **When** the migration is planned, **Then** a full `pg_dump` backup is taken before execution **And** a maintenance window is scheduled (estimated: 2-4 hours).

## Tasks / Subtasks

- [x] **Task 1: Update Prisma schema for composite PKs and index removal** (AC: #1, #2, #3)
  - [x] 1.1 In `prisma/schema.prisma`, modify the `HistoricalPrice` model (~line 491):
    - Remove `@id` from the `id` field (keep `@default(autoincrement())`)
    - Add `@@id([id, timestamp])` composite primary key
    - Remove `@@index([contractId, source, timestamp])` (maps to `historical_prices_contract_id_source_timestamp_idx`, 27 GB, 23 scans)
    - Remove `@@index([timestamp])` (maps to `historical_prices_timestamp_idx`, 2.1 GB, 32 scans)
    - Keep `@@index([platform, contractId, timestamp])` — used by `loadAlignedPricesForChunk` lateral join
    - Keep `@@index([source, timestamp])` — used by data-quality groupBy queries
    - Keep `@@unique([platform, contractId, source, intervalMinutes, timestamp])` — already includes `timestamp`, no change needed
  - [x] 1.2 In `prisma/schema.prisma`, modify the `HistoricalDepth` model (~line 544):
    - Remove `@id` from the `id` field (keep `@default(autoincrement())`)
    - Add `@@id([id, timestamp])` composite primary key
    - Remove `@@index([timestamp])` (maps to `historical_depths_timestamp_idx`, 2.9 GB, 28 scans)
    - Keep `@@index([platform, contractId, timestamp])` — used by depth pre-load queries
    - Keep `@@index([source, timestamp])` — used by data-quality groupBy
    - Keep `@@index([contractId, source, timestamp])` — unlike historical_prices, this index is NOT listed for removal in the AC
    - Keep `@@unique([platform, contractId, source, timestamp])` — already includes `timestamp`, no change needed
  - [x] 1.3 Run `pnpm prisma migrate dev --create-only --name hypertable-historical-prices` to generate migration 1. Then run `pnpm prisma migrate dev --create-only --name hypertable-historical-depths` to generate migration 2. Two separate migrations = smaller blast radius (if prices migration fails, depths hasn't been attempted).

- [x] **Task 2: Write manual migration SQL for historical_prices** (AC: #1, #3, #5)
  - [x] 2.1 Edit the generated migration file for `historical_prices`. The Prisma-generated SQL will handle PK changes. **Prepend** timeout disabling and **append** hypertable conversion + index drops. Final migration order:
    ```sql
    -- 1. Disable statement timeout for large data migration (180 GB)
    -- Deferred finding from 10-95-1 code review: transaction timeout risk
    SET LOCAL statement_timeout = 0;
    SET LOCAL lock_timeout = 0;

    -- 2. Prisma-generated SQL (PK change: @id(id) → @@id([id, timestamp]))
    -- ... (auto-generated)

    -- 3. Convert to hypertable
    SELECT create_hypertable('historical_prices', 'timestamp',
      migrate_data => true,
      chunk_time_interval => INTERVAL '1 day',
      if_not_exists => TRUE
    );

    -- 4. Drop bloated indexes (saving ~29.1 GB)
    DROP INDEX IF EXISTS "historical_prices_contract_id_source_timestamp_idx";
    DROP INDEX IF EXISTS "historical_prices_timestamp_idx";
    ```
  - [x] 2.2 **Critical sequencing**: Prisma PK changes must happen before `create_hypertable` because hypertable conversion validates that all unique/PK constraints include the partitioning column (`timestamp`). Index drops go last.
  - [x] 2.3 **Do NOT apply yet** — both migrations should be ready before applying either. Continue to Task 3.

- [x] **Task 3: Write manual migration SQL for historical_depths** (AC: #2, #3, #5)
  - [x] 3.1 Edit the generated migration file for `historical_depths`. Same pattern as Task 2:
    ```sql
    -- 1. Disable statement timeout for large data migration (151 GB)
    SET LOCAL statement_timeout = 0;
    SET LOCAL lock_timeout = 0;

    -- 2. Prisma-generated SQL (PK change: @id(id) → @@id([id, timestamp]))
    -- ... (auto-generated)

    -- 3. Convert to hypertable
    SELECT create_hypertable('historical_depths', 'timestamp',
      migrate_data => true,
      chunk_time_interval => INTERVAL '1 day',
      if_not_exists => TRUE
    );

    -- 4. Drop bloated index (saving ~2.9 GB)
    DROP INDEX IF EXISTS "historical_depths_timestamp_idx";
    ```
  - [x] 3.2 Apply both migrations sequentially: `pnpm prisma migrate dev`. Both will run within a maintenance window.
  - [x] 3.3 Verify `prisma generate` succeeds after migration.

- [x] **Task 4: Audit all Prisma and raw SQL consumers** (AC: #4)
  - [x] 4.1 **historicalPrice Prisma consumers** — audit all files. Confirm none use `findUnique` with the old single-column `id` key. Current usage is: `createMany`, `findMany`, `findFirst`, `aggregate`, `groupBy`, `count` — all unaffected by composite PK. Run: `grep -r "historicalPrice\.\|HistoricalPrice" src --include="*.ts" -l` to enumerate.
    Known consumers (production code):
    - `kalshi-historical.service.ts` — `createMany`
    - `polymarket-historical.service.ts` — `createMany`
    - `oddspipe.service.ts` — `createMany`
    - `ingestion-quality-assessor.service.ts` — `findMany`
    - `data-quality.service.ts` — `groupBy`, `findMany`
    - `calibration-report.service.ts` — `groupBy`, `findMany`
    - `historical-data.controller.ts` — `aggregate`, `groupBy`, `count`
    - `backtest-data-loader.service.ts` — `findMany`, `findFirst`
    - `incremental-fetch.service.spec.ts` — `aggregate` (mock)
  - [x] 4.2 **historicalDepth Prisma consumers** — same audit. Current usage: `createMany`, `findMany`, `findFirst`, `aggregate`, `groupBy`, `count` — no `findUnique`.
    Known consumers (production code):
    - `pmxt-archive.service.ts` — `createMany`
    - `fill-model.service.ts` — `findFirst`
    - `backtest-data-loader.service.ts` — `findFirst` (via lazy LRU)
    - `ingestion-quality-assessor.service.ts` — `findMany`
    - `data-quality.service.ts` — `groupBy`
    - `historical-data.controller.ts` — `aggregate`, `groupBy`, `count`
  - [x] 4.3 **Raw SQL queries** — verify the 3 raw SQL references in `backtest-data-loader.service.ts` (lines ~138, ~266, ~333) work with hypertables:
    - Line ~138: `SELECT COUNT(*) FROM (SELECT 1 FROM historical_depths WHERE ...)` — count with time range filter. Hypertable chunk pruning improves this.
    - Line ~266: `SELECT ... FROM historical_depths WHERE contract_id = ANY(...) AND timestamp >= ...` — depth batch load. Benefits from chunk pruning.
    - Line ~333: `JOIN historical_prices k ON ... AND k.timestamp >= ...` + `JOIN LATERAL (SELECT hp.close FROM historical_prices hp WHERE ...)` — aligned prices join. Benefits from chunk pruning + kept `(platform, contractId, timestamp)` index.
    All three queries are read-only, use standard SQL, and filter on `timestamp` — fully compatible with hypertables. **No changes needed.**
  - [x] 4.4 **ON CONFLICT clauses** in `predexon-bulk-insert.ts` — verify:
    - `bulkInsertPrices` line ~68: `ON CONFLICT (platform,contract_id,source,interval_minutes,timestamp)` — matches existing unique constraint (already includes `timestamp`). **No change needed.**
    - `bulkInsertDepth` line ~96: `ON CONFLICT (platform,contract_id,source,timestamp)` — matches existing unique constraint (already includes `timestamp`). **No change needed.**
  - [x] 4.5 Verify no foreign keys reference `historical_prices` or `historical_depths`. Neither model has `@relation` in Prisma schema and no other model references them.

- [x] **Task 5: Extend integration tests** (AC: #1, #2, #3, #4)
  - [x] 5.1 In `src/modules/backtesting/ingestion/timescaledb-migration.integration.spec.ts`, add two new `describe` blocks (alongside the existing `historical_trades` block):

    **`describe('TimescaleDB Migration — historical_prices')`:**
    - `[P0]` historical_prices is a hypertable: query `timescaledb_information.hypertables`
    - `[P0]` chunk interval is 1 day: query `timescaledb_information.dimensions`
    - `[P0]` composite PK exists: `(id, timestamp)` via `information_schema.table_constraints`
    - `[P0]` unique constraint includes timestamp: 5-column `(platform, contract_id, source, interval_minutes, timestamp)`
    - `[P1]` dropped indexes no longer exist: `historical_prices_contract_id_source_timestamp_idx` and `historical_prices_timestamp_idx`
    - `[P1]` kept indexes still exist: `historical_prices_platform_contract_id_timestamp_idx` and `historical_prices_source_timestamp_idx`
    - `[P1]` createMany idempotency (skipDuplicates: true)
    - `[P1]` findMany with time range filter
    - `[P1]` aggregate + groupBy work on hypertable

    **`describe('TimescaleDB Migration — historical_depths')`:**
    - `[P0]` historical_depths is a hypertable: query `timescaledb_information.hypertables`
    - `[P0]` chunk interval is 1 day: query `timescaledb_information.dimensions`
    - `[P0]` composite PK exists: `(id, timestamp)` via `information_schema.table_constraints`
    - `[P0]` unique constraint includes timestamp: 4-column `(platform, contract_id, source, timestamp)`
    - `[P1]` dropped index no longer exists: `historical_depths_timestamp_idx`
    - `[P1]` kept indexes still exist: `historical_depths_platform_contract_id_timestamp_idx`, `historical_depths_source_timestamp_idx`, `historical_depths_contract_id_source_timestamp_idx`
    - `[P1]` createMany idempotency (skipDuplicates: true)
    - `[P1]` findFirst returns correct result (used by fill-model.service.ts)
    - `[P1]` aggregate + groupBy work on hypertable

  - [x] 5.2 Follow existing test patterns from the `historical_trades` block: use `test-timescaledb-migration-` prefix for contractIds, clean up test data in beforeAll/afterAll, guard with `describe.runIf(DATABASE_URL)`.

- [x] **Task 6: Run lint and verify** (AC: all)
  - [x] 6.1 Run `cd pm-arbitrage-engine && pnpm lint`
  - [x] 6.2 Run `pnpm test`
  - [x] 6.3 Verify all tests pass with zero regressions

## Dev Notes

### Architecture Context

This is the second story in Epic 10.95 (TimescaleDB Migration). Story 10-95-1 proved the approach on `historical_trades` (5.9 GB). This story applies the same pattern to the two largest tables: `historical_prices` (180 GB, 248M rows) and `historical_depths` (151 GB, 106M rows) — 56x more data than the POC.

TimescaleDB is already installed (10-95-1). The Docker images are already swapped to `timescale/timescaledb-ha:pg16.13-ts2.26.1-oss`. No infrastructure changes needed — this is purely a migration + schema story.

### Critical Difference from Story 10-95-1

**Unique constraints already include `timestamp` for both tables.** Unlike `historical_trades` (where the unique constraint had to be modified to add `timestamp`), both `historical_prices` and `historical_depths` already have `timestamp` in their unique constraints. This means:
- **No unique constraint changes needed**
- **No ON CONFLICT clause changes needed** in `predexon-bulk-insert.ts`
- The only schema change is the PK: `@id` on `id` alone → `@@id([id, timestamp])` composite PK

### Migration Transaction Timeout Risk (Deferred from 10-95-1 Code Review)

The 10-95-1 code review explicitly deferred "migration transaction timeout risk for 10-95-2" as a finding. For 180 GB + 151 GB tables:
- `create_hypertable` with `migrate_data => true` holds an exclusive lock while reorganizing all data into chunks
- Prisma wraps each migration file in a transaction
- Default `statement_timeout` could cause the migration to fail mid-way

**Mitigation (MANDATORY):**
1. `SET LOCAL statement_timeout = 0;` at the top of each migration file (scoped to transaction)
2. `SET LOCAL lock_timeout = 0;` to prevent lock acquisition timeout
3. Split into two separate migration files (one per table) — if `historical_prices` migration fails, `historical_depths` hasn't been attempted, reducing recovery complexity
4. `if_not_exists => TRUE` on `create_hypertable` for idempotency if migration is re-run

**Fallback approach** (only if direct migration fails on production): Create new hypertable, batch-insert data in time ranges, swap table names. This is more complex and should only be used if the direct approach hits issues.

### Prerequisite: Database Backup

The operator MUST take a full `pg_dump` backup before running these migrations. Hypertable conversion is not reversible via standard migration rollback. Document this in the migration file comments.

### Hypertable Constraint Rules (Recap from 10-95-1)

All unique indexes and primary keys on a hypertable MUST include the partitioning column (`timestamp`). Both tables already satisfy this:
- `historical_prices`: PK will be `(id, timestamp)`, unique is `(platform, contract_id, source, interval_minutes, timestamp)` — compliant
- `historical_depths`: PK will be `(id, timestamp)`, unique is `(platform, contract_id, source, timestamp)` — compliant

### Index Drop Analysis

**Indexes being dropped (AC #3):**

| Index | Table | Size | Scans | Rationale |
|-------|-------|------|-------|-----------|
| `contract_id_source_timestamp_idx` | historical_prices | 27 GB | 23 | Covered by unique constraint `(platform, contract_id, source, interval_minutes, timestamp)` + kept index `(platform, contract_id, timestamp)`. Low scan count. |
| `timestamp_idx` | historical_prices | 2.1 GB | 32 | Redundant — hypertable chunk pruning replaces global timestamp index for time-range queries. |
| `timestamp_idx` | historical_depths | 2.9 GB | 28 | Same — chunk pruning handles time-range filtering. |

**Indexes being KEPT:**

| Index | Table | Reason |
|-------|-------|--------|
| `platform_contract_id_timestamp_idx` | both | Critical for `loadAlignedPricesForChunk` lateral join and depth batch loads |
| `source_timestamp_idx` | both | Used by `data-quality.service.ts` groupBy queries |
| `contract_id_source_timestamp_idx` | historical_depths only | NOT in AC drop list — 4th index retained on depths |

**Monitoring note** (deferred from 10-95-1 review): After dropping `historical_prices_contract_id_source_timestamp_idx` (27 GB, 23 scans), monitor backtesting query performance for regressions. The `(platform, contract_id, timestamp)` index should cover the same query patterns.

### Prisma Compatibility (Proven in 10-95-1)

- Standard CRUD operations are transparent to hypertables — no code changes
- `findMany`, `createMany`, `findFirst`, `aggregate`, `groupBy`, `count` all work identically
- `$queryRaw` with standard SQL works — hypertable chunk pruning is automatic
- `skipDuplicates: true` in `createMany` maps to ON CONFLICT DO NOTHING — still works

### Files to Modify

| File | Change |
|------|--------|
| `prisma/schema.prisma` (~lines 491-513) | HistoricalPrice: composite PK, remove 2 indexes |
| `prisma/schema.prisma` (~lines 544-562) | HistoricalDepth: composite PK, remove 1 index |
| `prisma/migrations/<ts1>_hypertable_historical_prices/migration.sql` | NEW: PK change + hypertable + index drops |
| `prisma/migrations/<ts2>_hypertable_historical_depths/migration.sql` | NEW: PK change + hypertable + index drops |
| `src/modules/backtesting/ingestion/timescaledb-migration.integration.spec.ts` | Extend: 2 new describe blocks (~18 tests) |

### Files NOT to Modify

- `docker-compose.yml` / `docker-compose.dev.yml` — already using TimescaleDB image (10-95-1)
- `predexon-bulk-insert.ts` — ON CONFLICT clauses already match unique constraints (timestamp included)
- `backtest-data-loader.service.ts` — raw SQL queries compatible with hypertables, no changes
- All other `historicalPrice`/`historicalDepth` consumers — no `findUnique` usage, no FK references

### Previous Story Intelligence (10-95-1)

**Patterns to reuse:**
- Composite PK pattern: `@@id([id, timestamp])` with `@default(autoincrement())` retained on `id`
- Manual migration SQL: Prisma-generated PK change first, then `create_hypertable`, then `DROP INDEX`
- Integration test pattern: `describe.runIf(DATABASE_URL)`, `test-timescaledb-migration-` prefix, cleanup in beforeAll/afterAll
- `if_not_exists => TRUE` on `create_hypertable` for idempotency

**Pitfalls learned:**
- `prisma migrate dev --create-only` may require interactive TTY — use `yes |` workaround if needed
- Integration test unique constraint verification: use `pg_index` catalog (not `information_schema.table_constraints`) for unique indexes
- Do NOT use `postgresqlExtensions` preview feature (being discontinued per prisma/prisma#26136)

**Debug notes:**
- If migration fails with `TS103: cannot create a unique index without the column "timestamp"` — the PK/constraint changes haven't been applied before `create_hypertable`. Check migration ordering.
- 10-95-1 left 8 pre-existing test failures (3 backtest-engine timeout, 5 data-ingestion e2e flaky). Current passing: 3598+. These are pre-existing and not regressions.

### Testing Approach

- **No new unit tests needed** — no production code changes, only schema + migration
- **Integration tests** — extend existing `timescaledb-migration.integration.spec.ts` with ~18 new tests across 2 describe blocks
- **Regression** — full `pnpm test` must pass with no new failures

### Project Structure Notes

- All changes within `pm-arbitrage-engine/` (separate git repo — separate commits)
- Migration files: `prisma/migrations/<timestamp>_hypertable_historical_prices/` and `prisma/migrations/<timestamp>_hypertable_historical_depths/`
- Integration tests co-located at `src/modules/backtesting/ingestion/timescaledb-migration.integration.spec.ts`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 10.95, Story 10-95-2] — AC and story requirements
- [Source: _bmad-output/implementation-artifacts/10-95-1-timescaledb-extension-installation-proof-of-concept.md] — Previous story patterns, debug notes, code review deferred findings
- [Source: _bmad-output/implementation-artifacts/sprint-status.yaml#10-95-1 comment] — Deferred findings: "migration transaction timeout risk for 10-95-2"
- [Source: _bmad-output/planning-artifacts/architecture.md#Database Architecture] — TimescaleDB configuration, hypertable requirements
- [Source: prisma/schema.prisma#HistoricalPrice ~line 491, #HistoricalDepth ~line 544] — Current model definitions
- [Source: src/modules/backtesting/ingestion/predexon-bulk-insert.ts] — ON CONFLICT clauses (already correct)
- [Source: src/modules/backtesting/engine/backtest-data-loader.service.ts ~lines 138, 266, 333] — Raw SQL queries on both tables
- [Source: src/modules/backtesting/ingestion/timescaledb-migration.integration.spec.ts] — Existing test pattern to extend

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- TimescaleDB `create_default_indexes` defaults to TRUE — recreates standalone timestamp DESC index on partitioning column after DROP INDEX. Fixed by adding `create_default_indexes => FALSE` to `create_hypertable` calls.
- Prisma `migrate dev --create-only` with both schema changes present generates a single migration for both tables. Split by reverting HistoricalDepth schema, generating migration 1 (prices only), then re-adding HistoricalDepth and generating migration 2.

### Completion Notes List
- AC #1: historical_prices converted to hypertable with `@@id([id, timestamp])` composite PK, 1-day chunk interval
- AC #2: historical_depths converted to hypertable with `@@id([id, timestamp])` composite PK, 1-day chunk interval
- AC #3: 3 bloated indexes dropped (prices: contract_id_source_timestamp + timestamp; depths: timestamp)
- AC #4: All Prisma consumers audited — no `findUnique` usage, no FK references, ON CONFLICT clauses already correct, raw SQL in backtest-data-loader compatible
- AC #5: Two separate migration files for blast radius control. Timeout disabling included.
- 18 new integration tests added (9 per table), all passing. Total: 3618 passed (baseline: 3600).

### Change Log
- Modified `prisma/schema.prisma`: HistoricalPrice composite PK, removed 2 indexes; HistoricalDepth composite PK, removed 1 index
- Created `prisma/migrations/20260404104916_hypertable_historical_prices/migration.sql`: PK change + hypertable conversion + index drops
- Created `prisma/migrations/20260404105002_hypertable_historical_depths/migration.sql`: PK change + hypertable conversion + index drop
- Extended `src/modules/backtesting/ingestion/timescaledb-migration.integration.spec.ts`: 2 new describe blocks, 18 tests

### File List
- `prisma/schema.prisma` ��� composite PKs, index removal
- `prisma/migrations/20260404104916_hypertable_historical_prices/migration.sql` — NEW
- `prisma/migrations/20260404105002_hypertable_historical_depths/migration.sql` — NEW
- `src/modules/backtesting/ingestion/timescaledb-migration.integration.spec.ts` — extended
