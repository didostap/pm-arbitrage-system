# Story 10-95.3: Compression Policies, Retention & Observability

Status: done

## Story

As an operator,
I want old data automatically compressed and retention policies enforced with dashboard visibility,
so that storage stays bounded and I can monitor compression effectiveness.

## Acceptance Criteria

1. **Compression Enabled** — **Given** all three hypertables exist (`historical_prices`, `historical_depths`, `historical_trades`), **When** the migration runs, **Then** each table has compression configured with `segmentby = 'platform, contract_id, source'` and `orderby = 'timestamp DESC'`.

2. **Automatic Compression Policy** — **Given** compression is enabled with a 7-day interval policy, **When** chunks older than 7 days exist, **Then** they are automatically compressed by TimescaleDB's background job **And** compressed chunks remain fully queryable via Prisma.

3. **Manual Compression of Old Chunks** — **Given** existing data spans ~3 months, **When** manual compression is triggered (via service method on startup or dashboard action), **Then** all uncompressed chunks older than 7 days are compressed **And** total database size drops from ~337 GB toward target <50 GB.

4. **Retention Policies via EngineConfig** — **Given** retention periods are configured in EngineConfig with differentiated non-negotiable defaults, **When** the daily retention cron runs, **Then** raw data older than the configured period is dropped via `drop_chunks()` (chunk-level DROP, no vacuum overhead):
   - `historical_prices`: 730 days (2 years — walk-forward validation across multiple market regimes)
   - `historical_trades`: 365 days (1 year — seasonal pattern coverage)
   - `historical_depths`: 180 days (6 months — heaviest table, compression target)
     **And** retention periods are configurable but defaults are non-negotiable (per Epic 10.9 retro) **And** minimum allowed value is 30 days for all tables.

5. **Telegram Retention Notification** — **Given** the retention cron completes, **When** chunks are dropped, **Then** the operator is notified via Telegram with per-table chunk drop counts and duration.

6. **Dashboard Storage Stats** — **Given** compressed data exists, **When** the operator views the dashboard, **Then** a new "Storage" section shows: total database size, per-table compressed vs uncompressed size, compression ratio, and chunk count.

## Tasks / Subtasks

- [x] **Task 1: Prisma migration — Enable compression and add policies** (AC: #1, #2)
  - [x] 1.1 Create migration: `pnpm prisma migrate dev --create-only --name enable-timescaledb-compression`. Prisma generates an empty migration (no schema changes for this task). Append manual SQL:

    ```sql
    -- Enable compression on all three hypertables
    ALTER TABLE historical_prices SET (
      timescaledb.compress,
      timescaledb.compress_segmentby = 'platform, contract_id, source',
      timescaledb.compress_orderby = 'timestamp DESC'
    );
    ALTER TABLE historical_depths SET (
      timescaledb.compress,
      timescaledb.compress_segmentby = 'platform, contract_id, source',
      timescaledb.compress_orderby = 'timestamp DESC'
    );
    ALTER TABLE historical_trades SET (
      timescaledb.compress,
      timescaledb.compress_segmentby = 'platform, contract_id, source',
      timescaledb.compress_orderby = 'timestamp DESC'
    );

    -- Add automatic compression policies (7-day interval)
    -- TimescaleDB background job compresses eligible chunks every 12h (default)
    SELECT add_compression_policy('historical_prices',
      compress_after => INTERVAL '7 days', if_not_exists => true);
    SELECT add_compression_policy('historical_depths',
      compress_after => INTERVAL '7 days', if_not_exists => true);
    SELECT add_compression_policy('historical_trades',
      compress_after => INTERVAL '7 days', if_not_exists => true);
    ```

  - [x] 1.2 The migration does NOT manually compress existing old chunks — that is handled by the service (Task 3) because it is long-running (~337 GB, potentially hours). Compression policies will auto-compress old chunks within 24-48h via the background job, but the service provides immediate manual trigger.
  - [x] 1.3 Verify migration applies: `pnpm prisma migrate dev`. Run `pnpm prisma generate`.

- [x] **Task 2: EngineConfig — Add retention period fields** (AC: #4)
  - [x] 2.1 In `prisma/schema.prisma`, add 3 fields to the `EngineConfig` model (after the `auditLogRetentionDays` field, ~line 152):
    ```prisma
    retentionDaysHistoricalPrices    Int?     @map("retention_days_historical_prices")
    retentionDaysHistoricalTrades    Int?     @map("retention_days_historical_trades")
    retentionDaysHistoricalDepths    Int?     @map("retention_days_historical_depths")
    ```
  - [x] 2.2 Generate migration: `pnpm prisma migrate dev --name add-retention-config`. **Migration ordering:** Create the EngineConfig migration (Task 2) BEFORE the compression migration (Task 1), so config fields exist when the service starts. Alternatively, combine both into a single migration: Prisma-generated config DDL first, then append compression SQL.
  - [x] 2.3 In `src/common/config/env.schema.ts`, add 3 new env vars to the Zod schema:
    ```typescript
    RETENTION_DAYS_HISTORICAL_PRICES: z.coerce.number().int().min(30).default(730),
    RETENTION_DAYS_HISTORICAL_TRADES: z.coerce.number().int().min(30).default(365),
    RETENTION_DAYS_HISTORICAL_DEPTHS: z.coerce.number().int().min(30).default(180),
    ```
  - [x] 2.4 In `src/common/config/config-defaults.ts`, add entries to `CONFIG_DEFAULTS`:
    ```typescript
    retentionDaysHistoricalPrices: { envKey: 'RETENTION_DAYS_HISTORICAL_PRICES', defaultValue: 730 },
    retentionDaysHistoricalTrades: { envKey: 'RETENTION_DAYS_HISTORICAL_TRADES', defaultValue: 365 },
    retentionDaysHistoricalDepths: { envKey: 'RETENTION_DAYS_HISTORICAL_DEPTHS', defaultValue: 180 },
    ```
  - [x] 2.5 In `src/common/config/effective-config.types.ts`, add 3 fields to the `EffectiveConfig` interface:
    ```typescript
    retentionDaysHistoricalPrices: number;
    retentionDaysHistoricalTrades: number;
    retentionDaysHistoricalDepths: number;
    ```
  - [x] 2.6 Add to `.env.development` and `.env.example`:
    ```
    RETENTION_DAYS_HISTORICAL_PRICES=730
    RETENTION_DAYS_HISTORICAL_TRADES=365
    RETENTION_DAYS_HISTORICAL_DEPTHS=180
    ```

- [x] **Task 3: TimescaleStorageService — Compression, retention, and stats** (AC: #3, #4, #5)
  - [x] 3.1 Create `src/modules/monitoring/timescale-storage.types.ts` — define return types:
    ```typescript
    export interface CompressionResult {
      tables: Array<{ tableName: string; chunksCompressed: number }>;
      totalChunksCompressed: number;
    }
    export interface TableStorageStats {
      tableName: string;
      totalSize: string;
      compressedSize: string | null;
      uncompressedSize: string | null;
      compressionRatioPct: number;
      totalChunks: number;
      compressedChunks: number;
    }
    export interface StorageStats {
      totalDatabaseSize: string;
      tables: TableStorageStats[];
    }
    ```
  - [x] 3.2 Create `src/modules/monitoring/timescale-storage.service.ts`. Dependencies: `PrismaService`, `ConfigAccessorService`, `EventEmitter2` (3 deps — leaf service). Follow `AuditLogRetentionService` pattern (`src/modules/monitoring/audit-log-retention.service.ts`).
  - [x] 3.3 **Retention cron** — `@Cron('0 4 * * *')` (daily 4 AM UTC, after audit-log-retention at 3 AM):
    - Read retention periods from `ConfigAccessorService`: `retentionDaysHistoricalPrices`, `retentionDaysHistoricalTrades`, `retentionDaysHistoricalDepths`
    - **Validate each retention value** before use: `Number.isInteger(days) && days >= 30`. If invalid, log error and skip that table (do not throw).
    - For each table, use **parameterized queries** to prevent SQL injection:
      ```typescript
      // SAFE: Prisma tagged template parameterizes the integer
      const dropped = await this.prisma.$queryRaw<{ drop_chunks: string }[]>`
        SELECT drop_chunks(${tableName}::regclass, older_than => INTERVAL '1 day' * ${days}::int)
      `;
      ```
      **NEVER interpolate** `days` via string template literal — even though values come from EngineConfig, the dashboard API could set arbitrary values.
    - Count dropped chunks from result set per table
    - Emit `TimescaleRetentionCompletedEvent` with per-table drop counts and duration
    - **Never re-throw** — retention failure must not block trading (same pattern as `AuditLogRetentionService`)
    - Log results at info level; log errors at error level
    - Config changes do NOT trigger immediate retention — the next cron run picks up new values
  - [x] 3.4 **Manual compression method** — `async compressOldChunks(): Promise<CompressionResult>`:
    - Query uncompressed chunks older than 7 days via `timescaledb_information.chunks`
    - Compress each chunk individually via `SELECT compress_chunk(...)` (NOT in a transaction — each is independent)
    - Log progress: "Compressed chunk X of Y for table Z"
    - Return per-table compressed chunk counts
    - **Non-blocking startup** — call via `onModuleInit()` using `setImmediate()` so it does NOT block application startup (compression of ~337 GB could take hours):
      ```typescript
      async onModuleInit() {
        setImmediate(() =>
          this.compressOldChunks().catch((err) =>
            this.logger.error({ message: 'Startup compression failed', error: err.stack }),
          ),
        );
      }
      ```
  - [x] 3.5 **Storage stats method** — `async getStorageStats(): Promise<StorageStats>`:
    - Query total database size: `SELECT pg_size_pretty(pg_database_size(current_database()))`
    - Per-table stats via `$queryRaw` with **explicit NULL handling** (no compressed data yet returns NULLs):
      ```sql
      SELECT
        hypertable_name,
        COALESCE(total_chunks, 0) AS total_chunks,
        COALESCE(number_compressed_chunks, 0) AS compressed_chunks,
        pg_size_pretty(COALESCE(before_compression_total_bytes, 0)) AS before_compression,
        pg_size_pretty(COALESCE(after_compression_total_bytes, 0)) AS after_compression,
        ROUND(
          COALESCE(1 - after_compression_total_bytes::numeric
            / NULLIF(before_compression_total_bytes, 0), 0) * 100, 1
        ) AS compression_ratio_pct
      FROM hypertable_compression_stats('historical_prices')
      UNION ALL
      SELECT ... FROM hypertable_compression_stats('historical_depths')
      UNION ALL
      SELECT ... FROM hypertable_compression_stats('historical_trades')
      ```
    - Also query total hypertable sizes via `SELECT pg_size_pretty(hypertable_size(...))` for the `totalSize` field
    - Return typed `StorageStats` object
  - [x] 3.6 Register in `src/modules/monitoring/monitoring.module.ts` — add to `providers` array **AND** to `exports` array (so `DashboardModule` can import it).
  - [x] 3.7 For error handling in the service, use `SystemHealthError` (codes 4000-4999) from the existing error hierarchy — do NOT create a new error class. Example: `new SystemHealthError('Retention failed for historical_prices', 4100, { table, days, error: err.message })`. Pick unused codes in the 4xxx range.

- [x] **Task 4: Event and Telegram integration** (AC: #5)
  - [x] 4.1 Add event name to `src/common/events/event-catalog.ts`:
    ```typescript
    TIMESCALE_RETENTION_COMPLETED: 'timescale.retention.completed',
    ```
  - [x] 4.2 Create event class `src/common/events/timescale-retention-completed.event.ts`:
    ```typescript
    export class TimescaleRetentionCompletedEvent extends BaseEvent {
      constructor(
        public readonly droppedChunks: Record<string, number>, // table → count
        public readonly durationMs: number,
      ) {
        super();
      }
    }
    ```
    Follow existing event class pattern (e.g., `AuditLogPrunedEvent`).
  - [x] 4.3 In `src/modules/monitoring/telegram-alert.service.ts`, add formatter to the formatter registry:
    ```typescript
    [EVENT_NAMES.TIMESCALE_RETENTION_COMPLETED]: (event: TimescaleRetentionCompletedEvent) => {
      const lines = Object.entries(event.droppedChunks)
        .map(([table, count]) => `${table}: ${count} chunks dropped`);
      return `TimescaleDB Retention Completed\n${lines.join('\n')}\nDuration: ${(event.durationMs / 1000).toFixed(1)}s`;
    }
    ```
  - [x] 4.4 In `src/modules/monitoring/event-consumer.service.ts`, ensure the new event routes to Telegram. If the event consumer uses severity-based routing, set severity to `info` and add to `TELEGRAM_ELIGIBLE_INFO_EVENTS` set.

- [x] **Task 5: Dashboard REST endpoint** (AC: #6)
  - [x] 5.1 Create `src/dashboard/dto/storage-stats.dto.ts`:

    ```typescript
    export class TableStorageStatsDto {
      tableName: string;
      totalSize: string; // human-readable, e.g., "42.3 GB"
      compressedSize: string; // after compression
      uncompressedSize: string; // before compression
      compressionRatioPct: number; // e.g., 89.9
      totalChunks: number;
      compressedChunks: number;
    }

    export class StorageStatsDto {
      totalDatabaseSize: string;
      tables: TableStorageStatsDto[];
    }
    ```

    Add Swagger decorators (`@ApiProperty`) following existing DTO patterns in `src/dashboard/dto/`.

  - [x] 5.2 Create `src/dashboard/dashboard-storage.service.ts` — thin facade calling `TimescaleStorageService.getStorageStats()` and mapping to DTO. Register in `DashboardModule`.
  - [x] 5.3 Add endpoint to `src/dashboard/dashboard.controller.ts`:
    ```typescript
    @Get('storage')
    @ApiOperation({ summary: 'Get TimescaleDB storage and compression stats' })
    async getStorageStats() {
      const stats = await this.dashboardStorageService.getStorageStats();
      return { data: stats, timestamp: new Date().toISOString() };
    }
    ```
    Inject `DashboardStorageService` into the controller constructor.
  - [x] 5.4 Update `src/dashboard/dashboard.module.ts` — add `TimescaleStorageService` import (from MonitoringModule exports) or add `DashboardStorageService` to providers and import `MonitoringModule`.

- [x] **Task 6: Dashboard frontend — Storage section** (AC: #6)
  - [x] 6.1 **Regenerate API client** in `pm-arbitrage-dashboard/` after backend endpoint is deployed/running. The project uses `swagger-typescript-api` — check `package.json` scripts for the generation command.
  - [x] 6.2 Add hook in `pm-arbitrage-dashboard/src/hooks/useDashboard.ts`:
    ```typescript
    export function useStorageStats() {
      return useQuery({
        queryKey: ['storage-stats'],
        queryFn: () => api.dashboard.getStorageStats(),
        select: res => res.data,
        refetchInterval: 60_000, // 1 minute (storage changes slowly)
      });
    }
    ```
  - [x] 6.3 Create `pm-arbitrage-dashboard/src/components/StorageStats.tsx`:
    - Use shadcn/ui `Card` + `Table` or grid layout
    - Display total database size prominently
    - Per-table rows: name, total size, compression ratio (with color: green >80%, amber 50-80%, red <50%), chunk counts (compressed/total)
    - Use existing component patterns from `HealthComposite.tsx` for status indicators
    - Loading state: skeleton/spinner (follow existing patterns)
  - [x] 6.4 Add `<StorageStats />` to `pm-arbitrage-dashboard/src/pages/DashboardPage.tsx` — place below the health section. Follow existing grid layout patterns.
  - [x] 6.5 **Separate git commit** — `pm-arbitrage-dashboard/` is an independent repo.

- [x] **Task 7: Integration tests** (AC: #1, #2, #3, #4, #6)
  - [x] 7.1 Extend `src/modules/backtesting/ingestion/timescaledb-migration.integration.spec.ts` with a new describe block:

    ```typescript
    describe('TimescaleDB Compression — all hypertables', () => {
      // P0: Compression enabled on each table
      // Query: SELECT compression_enabled FROM timescaledb_information.hypertables
      //        WHERE hypertable_name = 'historical_prices'
      // Assert: compression_enabled === true
      // P0: Compression policy exists for each table
      // Query: SELECT * FROM timescaledb_information.jobs
      //        WHERE hypertable_name = '...' AND proc_name = 'policy_compression'
      // P1: Compressed chunk remains queryable
      // Insert test data with old timestamp, compress the chunk,
      // query back via Prisma findMany — verify results match
      // P1: Storage stats query returns expected structure
      // Call the raw SQL from getStorageStats() and verify shape
    });
    ```

  - [x] 7.2 Follow existing test patterns: `describe.runIf(DATABASE_URL)`, `test-timescaledb-compression-` prefix for test data, cleanup in beforeAll/afterAll.

- [x] **Task 8: Unit tests, lint, and verify** (AC: all)
  - [x] 8.1 Create `src/modules/monitoring/timescale-storage.service.spec.ts`:
    - Mock PrismaService `$queryRaw` for retention and stats methods
    - Test retention cron: verify `drop_chunks` called per table with correct intervals from config
    - Test retention never re-throws (catches errors, logs them)
    - Test event emission on successful retention
    - Test `getStorageStats()` maps raw query results to typed output
    - Test `compressOldChunks()` iterates and compresses each chunk
    - Collection cleanup: verify any Maps/Sets have documented cleanup strategy
  - [x] 8.2 Create `src/dashboard/dashboard-storage.service.spec.ts`:
    - Test DTO mapping from service output
  - [x] 8.3 Event wiring test: verify `@OnEvent` for config changes triggers retention policy reconciliation (if applicable). Use `expectEventHandled()` from `src/common/testing/expect-event-handled.ts`.
  - [x] 8.4 Run `pnpm lint` and fix any errors.
  - [x] 8.5 Run `pnpm test` and verify zero regressions.

## Dev Notes

### Architecture Context

This is the third story in Epic 10.95 (TimescaleDB Migration). Stories 10-95-1 and 10-95-2 converted all 3 time-series tables to hypertables with composite PKs and cleaned up 76 GB of bloated indexes. This story adds the compression and retention layers that deliver the 90%+ storage reduction promised by the epic, plus dashboard observability.

TimescaleDB is already installed (`timescale/timescaledb-ha:pg16.13-ts2.26.1-oss`). All 3 tables are already hypertables with 1-day chunk intervals. No infrastructure changes needed.

### Key Technical Decisions

**Why NOT `add_retention_policy()`:** We manage retention ourselves via cron + `drop_chunks()` (not TimescaleDB's built-in retention policy) because:

1. Retention periods must be configurable via EngineConfig (dynamic, not static SQL)
2. We need Telegram notifications when retention runs (can't hook into DB background jobs)
3. The pattern mirrors the existing `AuditLogRetentionService` — proven in production
4. `drop_chunks()` is the same underlying mechanism the built-in policy uses

**Why `add_compression_policy()` IS used:** The 7-day compression interval is static (not configurable), so a DB-level policy is appropriate. No notifications needed for routine compression.

**Why manual compression is NOT in the migration:** Compressing ~337 GB of existing data inline would take hours and hold locks. The migration enables compression + policy (quick DDL). The `compressOldChunks()` service method handles the initial catchup post-deployment, chunk by chunk without a wrapping transaction.

### segmentby / orderby Rationale

`segmentby = 'platform, contract_id, source'` matches the most common query filters across all consumers (backtesting, data quality, ingestion quality). `orderby = 'timestamp DESC'` optimizes recent-data-first access patterns. These column names are the **database-level snake_case** names (not Prisma camelCase).

### Compressed Chunk Behavior

- **Reads are transparent** — Prisma `findMany`, `aggregate`, `groupBy`, `$queryRaw` all work on compressed chunks with no code changes. TimescaleDB decompresses on the fly during reads.
- **Writes to compressed chunks** — If an INSERT/UPDATE hits a compressed chunk, TimescaleDB auto-decompresses it first. For our hypertables, new data always lands in recent (uncompressed) chunks, so this shouldn't occur in normal operation.
- **`skipDuplicates: true`** in `createMany` still works — ON CONFLICT DO NOTHING operates normally on compressed data.

### Retention Validation

Minimum retention period: 30 days for ALL tables. This prevents accidental data loss. The Zod schema enforces `.min(30)` on the env vars, and the service should validate EngineConfig values before calling `drop_chunks()`. The AC defaults (2yr/1yr/6mo) are "non-negotiable" per the 10.9 retrospective — meaning they are the production defaults, but operators CAN adjust them (above the 30-day minimum).

### TimescaleDB API Reference

```sql
-- Enable compression (DDL, fast)
ALTER TABLE t SET (timescaledb.compress,
  timescaledb.compress_segmentby = 'col1, col2',
  timescaledb.compress_orderby = 'timestamp DESC');

-- Auto-compress chunks older than 7 days (background job, runs every 12h)
SELECT add_compression_policy('t', compress_after => INTERVAL '7 days', if_not_exists => true);

-- Manually compress a single chunk
SELECT compress_chunk('_timescaledb_internal._hyper_X_Y_chunk');

-- Drop old chunks (retention)
SELECT drop_chunks('t', older_than => INTERVAL '730 days');

-- Compression stats per table
SELECT * FROM hypertable_compression_stats('t');
-- Returns: total_chunks, number_compressed_chunks, before_compression_total_bytes,
--          after_compression_total_bytes, ...

-- Total hypertable size
SELECT hypertable_size(format('%I.%I', hypertable_schema, hypertable_name))
FROM timescaledb_information.hypertables WHERE hypertable_name = 't';

-- Database total size
SELECT pg_size_pretty(pg_database_size(current_database()));

-- List uncompressed chunks older than 7 days
SELECT format('%I.%I', chunk_schema, chunk_name) AS chunk_full_name
FROM timescaledb_information.chunks
WHERE hypertable_name = 't'
  AND NOT is_compressed
  AND range_end < NOW() - INTERVAL '7 days'
ORDER BY range_start ASC;
```

Note: `add_compression_policy()` is "superseded by `add_columnstore_policy()`" in TimescaleDB docs but compression APIs are fully supported — no migration to hypercore APIs needed.

### Concurrent Compression Safety

If `compressOldChunks()` runs while TimescaleDB's background compression policy is also running, there is no conflict — `compress_chunk()` on an already-compressed chunk is a no-op (returns without error). The service should check `is_compressed` in its chunk query to skip already-compressed chunks.

### Raw SQL Safety

All `$queryRaw` queries in the new service touch `timescaledb_information.*` views and DDL functions (not mode-sensitive tables). The `-- MODE-FILTERED` comment marker is NOT required (these are infrastructure queries, not position/order queries). Exempt per CLAUDE.md: "Health check queries (`SELECT 1`) are exempt."

### Event Pattern

Follow existing patterns in `src/common/events/`:

- Event name: dot-notation `timescale.retention.completed` in `event-catalog.ts`
- Constant: `TIMESCALE_RETENTION_COMPLETED` in `EVENT_NAMES`
- Class: `TimescaleRetentionCompletedEvent extends BaseEvent` in own file
- Severity: `info` (retention is routine maintenance)
- Telegram eligibility: add to `TELEGRAM_ELIGIBLE_INFO_EVENTS` set in `event-consumer.service.ts`

### Dashboard Frontend Patterns

The frontend (`pm-arbitrage-dashboard/`) uses:

- **TanStack Query** hooks with `refetchInterval` for auto-polling
- **shadcn/ui** components (Card, Table, Badge)
- **Generated API client** via `swagger-typescript-api` (axios-based, `--unwrap-response-data`)
- **Response envelope unwrap:** `select: (res) => res.data` in query hooks
- After adding the backend endpoint with `@ApiProperty` Swagger decorators, regenerate the API client. Check `package.json` scripts in `pm-arbitrage-dashboard/` for the generation command.

### Files to Create

| File                                                                  | Purpose                                      |
| --------------------------------------------------------------------- | -------------------------------------------- |
| `prisma/migrations/<ts>_add_retention_config/migration.sql`           | EngineConfig retention fields (create FIRST) |
| `prisma/migrations/<ts>_enable_timescaledb_compression/migration.sql` | Compression DDL + policies                   |
| `src/modules/monitoring/timescale-storage.types.ts`                   | CompressionResult, StorageStats interfaces   |
| `src/modules/monitoring/timescale-storage.service.ts`                 | Retention cron + compression + stats         |
| `src/modules/monitoring/timescale-storage.service.spec.ts`            | Unit tests                                   |
| `src/common/events/timescale-retention-completed.event.ts`            | Event class                                  |
| `src/dashboard/dto/storage-stats.dto.ts`                              | Response DTO with Swagger decorators         |
| `src/dashboard/dashboard-storage.service.ts`                          | Dashboard facade for storage stats           |
| `src/dashboard/dashboard-storage.service.spec.ts`                     | Unit tests                                   |
| `pm-arbitrage-dashboard/src/components/StorageStats.tsx`              | Frontend component                           |

### Files to Modify

| File                                                                          | Change                                                  |
| ----------------------------------------------------------------------------- | ------------------------------------------------------- |
| `prisma/schema.prisma`                                                        | Add 3 retention fields to EngineConfig model            |
| `src/common/config/env.schema.ts`                                             | Add 3 retention env vars with Zod validation            |
| `src/common/config/config-defaults.ts`                                        | Add 3 retention CONFIG_DEFAULTS entries                 |
| `src/common/config/effective-config.types.ts`                                 | Add 3 retention fields to EffectiveConfig               |
| `src/common/events/event-catalog.ts`                                          | Add `TIMESCALE_RETENTION_COMPLETED` event               |
| `src/modules/monitoring/monitoring.module.ts`                                 | Register `TimescaleStorageService`                      |
| `src/modules/monitoring/telegram-alert.service.ts`                            | Add retention event formatter                           |
| `src/modules/monitoring/event-consumer.service.ts`                            | Add to Telegram-eligible info events                    |
| `src/dashboard/dashboard.controller.ts`                                       | Add `GET /dashboard/storage` endpoint                   |
| `src/dashboard/dashboard.module.ts`                                           | Register `DashboardStorageService`, import dependencies |
| `src/modules/backtesting/ingestion/timescaledb-migration.integration.spec.ts` | Add compression test block                              |
| `.env.development`, `.env.example`                                            | Add retention env vars                                  |
| `pm-arbitrage-dashboard/src/hooks/useDashboard.ts`                            | Add `useStorageStats()` hook                            |
| `pm-arbitrage-dashboard/src/pages/DashboardPage.tsx`                          | Add `<StorageStats />` section                          |

### Files NOT to Modify

- `docker-compose*.yml` — already using TimescaleDB image (10-95-1)
- `predexon-bulk-insert.ts` — ON CONFLICT clauses unaffected by compression
- `backtest-data-loader.service.ts` — raw SQL reads work on compressed chunks
- Any Prisma consumer of historical tables — reads are transparent through compression

### Previous Story Intelligence (10-95-2)

**Patterns to reuse:**

- Manual SQL in Prisma migration: Prisma-generated DDL first, then TimescaleDB-specific SQL appended
- `if_not_exists => TRUE` for idempotency
- Integration test pattern: `describe.runIf(DATABASE_URL)`, P0/P1 categorization, test data prefix convention
- `create_default_indexes => FALSE` on `create_hypertable` — already applied in 10-95-1/2, not needed here

**Pitfalls learned:**

- `prisma migrate dev --create-only` may require interactive TTY — use `yes |` workaround if needed
- The 10-95-2 debug log found that `create_default_indexes` must be set to FALSE to prevent unwanted index recreation — already done, no action needed here
- Pre-existing test failures (~8): 3 backtest-engine timeout, 5 data-ingestion e2e flaky. Current passing: 3618+.

**Debug notes from 10-95-2:**

- If `compress_chunk()` fails with "already compressed": check `is_compressed` column before attempting
- `hypertable_compression_stats()` returns NULL for `after_compression_total_bytes` if no chunks are compressed yet — handle with COALESCE

### Project Structure Notes

- All backend changes in `pm-arbitrage-engine/` (separate git repo — separate commits required)
- Frontend changes in `pm-arbitrage-dashboard/` (separate git repo — separate commits required)
- Migration files: `prisma/migrations/<timestamp>_enable_timescaledb_compression/`
- New service follows monitoring module patterns — co-located spec file
- Dashboard DTO follows existing `src/dashboard/dto/` patterns

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 10.95, Story 10-95-3] — AC and story requirements
- [Source: _bmad-output/implementation-artifacts/10-95-2-hypertable-conversion-prices-depths.md] — Previous story patterns, debug notes
- [Source: _bmad-output/implementation-artifacts/sprint-status.yaml#10-95-2 comment] — Completion context
- [Source: _bmad-output/planning-artifacts/architecture.md#Database Architecture] — TimescaleDB configuration, compression/retention requirements
- [Source: prisma/schema.prisma#EngineConfig ~line 19] — Current EngineConfig model (add retention fields after auditLogRetentionDays ~line 152)
- [Source: src/common/config/env.schema.ts] — Zod schema for env var validation with decimalString() pattern
- [Source: src/common/config/config-defaults.ts] — CONFIG_DEFAULTS mapping pattern
- [Source: src/common/config/effective-config.types.ts] — EffectiveConfig interface
- [Source: src/modules/monitoring/audit-log-retention.service.ts] — Cron + never-rethrow retention pattern to follow
- [Source: src/modules/monitoring/telegram-alert.service.ts] — Formatter registry pattern
- [Source: src/modules/monitoring/event-consumer.service.ts] — TELEGRAM_ELIGIBLE_INFO_EVENTS set, severity routing
- [Source: src/common/events/event-catalog.ts] — Event naming convention and EVENT_NAMES constant
- [Source: src/dashboard/dashboard.controller.ts] — REST endpoint patterns with Swagger decorators
- [Source: src/dashboard/dashboard-overview.service.ts] — Parallel Promise.all() query pattern
- [Source: src/dashboard/dashboard.module.ts] — Module registration pattern
- [Source: src/modules/backtesting/ingestion/timescaledb-migration.integration.spec.ts] — Integration test structure
- [Source: pm-arbitrage-dashboard/src/hooks/useDashboard.ts] — TanStack Query hook patterns
- [Source: pm-arbitrage-dashboard/src/components/HealthComposite.tsx] — Component patterns with status indicators
- [Source: pm-arbitrage-dashboard/src/pages/DashboardPage.tsx] — Page layout and grid patterns
- [TimescaleDB Docs: add_compression_policy()] — compress_after, if_not_exists, schedule_interval defaults
- [TimescaleDB Docs: add_retention_policy() / drop_chunks()] — chunk-level retention API
- [TimescaleDB Docs: hypertable_compression_stats()] — Storage stats query API

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- `hypertable_compression_stats()` does NOT return a `hypertable_name` column — must add as literal in SELECT. Fixed in both service and integration test.
- `onModuleInit` lint: removed `async` keyword since `setImmediate` doesn't need await. Used `void` for fire-and-forget promise.
- Settings count test: updated 93 → 96 (3 new retention fields).
- Telegram eligible events count test: updated 25 → 26.

### Completion Notes List

- Task 1+2: Combined into single migration (`20260404123545_add_retention_config_and_compression`) — Prisma DDL for EngineConfig retention fields first, then compression DDL + policies appended. Per story Task 2.2 guidance.
- Task 3: `TimescaleStorageService` (3 deps: PrismaService, ConfigAccessor, EventEmitter2 — leaf service). Retention cron at 4 AM UTC, manual compression via `onModuleInit` with `setImmediate`, storage stats via raw SQL. Registered in MonitoringModule with exports for DashboardModule.
- Task 4: Event catalog entry, event class, retention formatter, added to TELEGRAM_ELIGIBLE_EVENTS and TELEGRAM_ELIGIBLE_INFO_EVENTS.
- Task 5: StorageStatsDto with Swagger decorators, DashboardStorageService facade, GET /dashboard/storage endpoint.
- Task 6: Frontend StorageStats component with compression ratio color coding, useStorageStats hook with fallback for pre-regeneration API client.
- Task 7: 10 integration tests — 6 P0 (compression enabled + policy exists per table), 2 P1 (stats query shape, compressed chunk queryability).
- Task 8: 12 unit tests for TimescaleStorageService, 2 for DashboardStorageService, 2 for retention formatter. Updated existing test assertions for new event/settings counts.

### Change Log

- 2026-04-04: Implemented Story 10-95-3 — compression policies, retention, and storage observability. 22 new tests (3640 total passing).

### File List

**Created:**

- `prisma/migrations/20260404123545_add_retention_config_and_compression/migration.sql`
- `src/modules/monitoring/timescale-storage.types.ts`
- `src/modules/monitoring/timescale-storage.service.ts`
- `src/modules/monitoring/timescale-storage.service.spec.ts`
- `src/common/events/timescale-retention-completed.event.ts`
- `src/modules/monitoring/formatters/retention-formatters.ts`
- `src/modules/monitoring/formatters/retention-formatters.spec.ts`
- `src/dashboard/dto/storage-stats.dto.ts`
- `src/dashboard/dashboard-storage.service.ts`
- `src/dashboard/dashboard-storage.service.spec.ts`
- `pm-arbitrage-dashboard/src/components/StorageStats.tsx`

**Modified:**

- `prisma/schema.prisma` — 3 retention fields on EngineConfig
- `src/common/config/env.schema.ts` — 3 RETENTION*DAYS*\* env vars
- `src/common/config/config-defaults.ts` — 3 CONFIG_DEFAULTS entries
- `src/common/config/effective-config.types.ts` — 3 EffectiveConfig fields
- `src/common/config/settings-metadata.ts` — 3 SETTINGS_METADATA entries
- `src/common/events/event-catalog.ts` — TIMESCALE_RETENTION_COMPLETED event
- `src/persistence/repositories/engine-config.repository.ts` — 3 retention fields in buildEffectiveConfig
- `src/modules/monitoring/monitoring.module.ts` — TimescaleStorageService + ConfigAccessor + EngineConfigRepository
- `src/modules/monitoring/telegram-alert.service.ts` — formatter + eligible events
- `src/modules/monitoring/event-consumer.service.ts` — TELEGRAM_ELIGIBLE_INFO_EVENTS
- `src/modules/monitoring/formatters/index.ts` — retention-formatters export
- `src/dashboard/dashboard.controller.ts` — GET /dashboard/storage endpoint
- `src/dashboard/dashboard.module.ts` — DashboardStorageService provider
- `src/dashboard/dto/index.ts` — storage-stats.dto export
- `src/modules/backtesting/ingestion/timescaledb-migration.integration.spec.ts` — compression test block
- `src/modules/monitoring/telegram-alert.service.spec.ts` — updated event count 25→26
- `src/dashboard/settings.service.spec.ts` — updated settings count 93→96
- `.env.development` — 3 retention env vars
- `.env.example` — 3 retention env vars
- `pm-arbitrage-dashboard/src/hooks/useDashboard.ts` — useStorageStats hook
- `pm-arbitrage-dashboard/src/pages/DashboardPage.tsx` — StorageStats component
