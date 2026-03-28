# Sprint Change Proposal: TimescaleDB Migration & Time-Series Storage Optimization

**Date:** 2026-04-03
**Triggered by:** Database monitoring during Epic 10.9 (Backtesting & System Calibration)
**Scope Classification:** Moderate — new infrastructure epic, architecture doc update, Docker/Prisma changes
**Status:** APPROVED (2026-04-03)

---

## Section 1: Issue Summary

### Problem Statement

The PostgreSQL database has grown to **337 GB in ~3 months** of time-series data collection, with a projected trajectory of **1.3 TB within 1 year**. Three backtesting tables (`historical_prices`, `historical_depths`, `historical_trades`) account for 99.9% of storage. The database exhibits pathological index bloat (76 GB), below-threshold cache hit rates (79.5%/84.3% vs 95% target), and an index-to-data ratio of 3.4:1 on the largest table. Standard PostgreSQL is not designed for time-series workloads at this scale.

### Discovery Context

During Epic 10.9 (Backtesting & System Calibration), the historical data ingestion pipeline (Stories 10-9-1a, 10-9-1b, 10-9-2) populated three large time-series tables. Database monitoring revealed unsustainable growth and degrading performance. A feasibility study confirmed TimescaleDB (PostgreSQL extension) as the solution — offering 85-90% compression, 10-50x query speedup, and automatic chunk-based data lifecycle management, all while preserving full Prisma and SQL compatibility.

### Evidence Summary

| Metric | Current | After Migration (Projected) |
|--------|---------|---------------------------|
| Total database size | 337 GB | ~35-45 GB |
| `historical_prices` | 180 GB (248M rows) | ~10-15 GB |
| `historical_depths` | 151 GB (106M rows) | ~20-25 GB |
| `historical_trades` | 5.9 GB (7.5M rows) | ~1 GB |
| Index bloat | 76 GB | Near-zero (chunk-local indexes) |
| Index cache hit rate | 79.5% | >95% (working set fits in RAM) |
| Table cache hit rate | 84.3% | >95% |
| Daily growth (raw) | ~3.5 GB/day | ~350 MB/day (compressed) |
| 1-year projected size | ~1.3 TB | ~170 GB |

---

## Section 2: Impact Analysis

### Checklist Results

| # | Item | Status |
|---|------|--------|
| 1.1 | Triggering story identified | [x] Done — Epic 10.9 data ingestion (10-9-1a, 10-9-1b) |
| 1.2 | Core problem defined | [x] Done — Technical limitation: PostgreSQL unsuitable for time-series at scale |
| 1.3 | Evidence gathered | [x] Done — Full DB analysis via Postgres MCP |
| 2.1 | Current epic (10.9) impact | [x] Done — No blocking impact; migration happens after 10.9 completes |
| 2.2 | Epic-level changes needed | [x] Done — New mini-epic 10.95 proposed |
| 2.3 | Remaining epics reviewed | [x] Done — Epic 11 & 12 unaffected |
| 2.4 | New epics needed | [x] Done — Epic 10.95: TimescaleDB Migration |
| 2.5 | Epic ordering | [x] Done — Insert between 10.9 and 11 |
| 3.1 | PRD conflicts | [N/A] — PRD specifies PostgreSQL 16+; TimescaleDB is a PG extension. No conflict. |
| 3.2 | Architecture conflicts | [!] Action-needed — Update technology stack table, Docker image, data model notes |
| 3.3 | UI/UX conflicts | [N/A] — No UI/UX impact |
| 3.4 | Other artifacts | [!] Action-needed — Docker Compose files, Prisma schema, CLAUDE.md |
| 4.1 | Direct Adjustment viable | [x] Viable — Effort: Medium, Risk: Low |
| 4.2 | Rollback viable | [N/A] — No rollback needed |
| 4.3 | MVP Review needed | [N/A] — MVP complete; this is Phase 1 infrastructure |
| 4.4 | Recommended path | [x] Done — Direct Adjustment (new mini-epic) |

### Epic Impact

**Epic 10.9 (in-progress):** No impact. Complete story 10-9-8 as planned. Migration happens after.

**New Epic 10.95:** 3 stories, inserted between Epic 10.9 completion and Epic 11 start. No hard dependency on Epic 11 — could theoretically run in parallel, but sequential is cleaner.

**Epic 11 (backlog):** No changes needed. Benefits from healthier database. Docker image change (postgres:16 → timescale/timescaledb-ha:pg16) will already be in place.

**Epic 12 (backlog):** Compliance reporting queries may benefit from continuous aggregates, but no required changes.

### Artifact Changes Required

**Architecture Document** (`_bmad-output/planning-artifacts/architecture.md`):

| Section | Change |
|---------|--------|
| Technology Stack table | Add: `TimescaleDB \| 2.x \| PostgreSQL extension for time-series; hypertable partitioning, native compression, continuous aggregates` |
| Database row | Update: `PostgreSQL 16+ with TimescaleDB extension` |
| Deployment section | Note: Docker image `timescale/timescaledb-ha:pg16` replaces `postgres:16` |

**Docker Compose files** (`pm-arbitrage-engine/docker-compose.yml`, `docker-compose.dev.yml`):

```
OLD: image: postgres:16
NEW: image: timescale/timescaledb-ha:pg16
```

**Prisma Schema** (`pm-arbitrage-engine/prisma/schema.prisma`):

TimescaleDB requires all unique constraints and primary keys to include the partitioning column (`timestamp`). Changes needed:

```prisma
// HistoricalPrice — PK change only (unique constraint already includes timestamp)
model HistoricalPrice {
  id              Int  @default(autoincrement())  // remove @id
  // ... other fields unchanged ...
  @@id([id, timestamp])  // composite PK including partition column
}

// HistoricalDepth — PK change only (unique constraint already includes timestamp)
model HistoricalDepth {
  id              Int  @default(autoincrement())  // remove @id
  // ... other fields unchanged ...
  @@id([id, timestamp])  // composite PK including partition column
}

// HistoricalTrade — PK change + unique constraint update
model HistoricalTrade {
  id              Int  @default(autoincrement())  // remove @id
  // ... other fields unchanged ...
  @@id([id, timestamp])  // composite PK including partition column
  @@unique([platform, contractId, source, externalTradeId, timestamp])  // add timestamp
}
```

**Prisma extensions** (schema.prisma datasource block):
```prisma
generator client {
  provider        = "prisma-client-js"
  previewFeatures = ["postgresqlExtensions"]
}

datasource db {
  provider   = "postgresql"
  url        = env("DATABASE_URL")
  extensions = [timescaledb]
}
```

**CLAUDE.md:** Add TimescaleDB note under Architecture section and Troubleshooting.

---

## Section 3: Recommended Approach

### Selected: Direct Adjustment — New Epic 10.95

**Rationale:**
- TimescaleDB is a PostgreSQL extension, not a database replacement — **fully reversible** (`DROP EXTENSION` reverts to plain tables)
- Prisma compatibility confirmed with well-documented workarounds (community-proven since 2020)
- All existing Prisma CRUD operations work unchanged against hypertables
- 3-story epic is focused, low-risk, and addresses a real scalability problem
- No impact on active development or existing features
- Significant ROI: 90% storage reduction + query performance gains + automated data lifecycle

**Effort:** Medium (3 stories, ~2-3 sessions)
**Risk:** Low (extension install is reversible; migration can be tested on staging first)
**Timeline Impact:** Adds one mini-epic between 10.9 and 11. No impact on Epic 11/12 schedules since those are in backlog.

**Trade-offs considered:**
- *Doing nothing:* Database hits 1.3 TB in a year. Cache hit rates continue degrading. Not sustainable.
- *Native PostgreSQL partitioning (pg_partman):* Manual partition management, no compression, no continuous aggregates. Inferior to TimescaleDB for this workload.
- *Separate time-series DB (InfluxDB, ClickHouse):* Requires separate infrastructure, no Prisma integration, higher operational complexity. Overkill when TimescaleDB provides the same benefits as a PostgreSQL extension.

---

## Section 4: Detailed Change Proposals — Epic 10.95

### Epic 10.95: TimescaleDB Migration & Time-Series Storage Optimization

**Goal:** Migrate time-series tables to TimescaleDB hypertables with compression, reducing storage by ~90% and improving query performance 10-50x, while maintaining full Prisma compatibility.

**Prerequisites:** Epic 10.9 complete. Full `pg_dump` backup taken before migration.

---

#### Story 10-95-1: TimescaleDB Extension Installation & Proof of Concept

As an operator,
I want TimescaleDB installed and verified on the smallest time-series table,
So that I can validate the migration approach before converting larger tables.

**Acceptance Criteria:**

1. **Given** Docker Compose files use `postgres:16` image
   **When** the migration is applied
   **Then** both `docker-compose.yml` and `docker-compose.dev.yml` use `timescale/timescaledb-ha:pg16`
   **And** existing data volumes are compatible (drop-in replacement)

2. **Given** TimescaleDB is not installed
   **When** the Prisma migration runs
   **Then** `CREATE EXTENSION IF NOT EXISTS timescaledb` succeeds
   **And** `\dx` shows timescaledb in the extensions list

3. **Given** `historical_trades` (5.9 GB, smallest table) exists
   **When** the hypertable conversion runs
   **Then** `SELECT create_hypertable('historical_trades', 'timestamp', migrate_data => true, chunk_time_interval => INTERVAL '1 day')` succeeds
   **And** the Prisma schema uses `@@id([id, timestamp])` composite PK
   **And** the unique constraint includes `timestamp`: `@@unique([platform, contractId, source, externalTradeId, timestamp])`

4. **Given** `historical_trades` is now a hypertable
   **When** existing Prisma queries execute (findMany, create, createMany)
   **Then** all operations succeed identically to before conversion

5. **Given** unused indexes exist on `historical_trades`
   **When** the migration runs
   **Then** `historical_trades_platform_contract_id_timestamp_idx` (0 scans, 676 MB) is dropped
   **And** `historical_trades_timestamp_idx` (0 scans, 132 MB) is dropped

6. **Given** the Prisma schema datasource block
   **When** the schema is updated
   **Then** `extensions = [timescaledb]` is declared
   **And** `previewFeatures = ["postgresqlExtensions"]` is enabled (if not already)

**Tasks:**
1. Update Docker Compose images (both files)
2. Update Prisma schema (extensions, composite PK, unique constraint for HistoricalTrade)
3. Create Prisma migration with `--create-only`, manually add `CREATE EXTENSION` and `create_hypertable` SQL
4. Drop unused indexes in migration SQL
5. Apply migration, verify Prisma operations work
6. Test: backtesting queries against `historical_trades` produce identical results
7. Update `.env.example` if any new env vars needed

---

#### Story 10-95-2: Hypertable Conversion — historical_prices & historical_depths

As an operator,
I want the two largest tables converted to hypertables with optimized indexes,
So that the database can handle long-term data growth efficiently.

**Acceptance Criteria:**

1. **Given** `historical_prices` (180 GB, 248M rows) exists as a regular table
   **When** the migration runs
   **Then** `create_hypertable('historical_prices', 'timestamp', migrate_data => true, chunk_time_interval => INTERVAL '1 day')` succeeds
   **And** Prisma schema uses `@@id([id, timestamp])` composite PK
   **And** chunk count is verified with `SELECT count(*) FROM timescaledb_information.chunks WHERE hypertable_name = 'historical_prices'`

2. **Given** `historical_depths` (151 GB, 106M rows) exists as a regular table
   **When** the migration runs
   **Then** `create_hypertable('historical_depths', 'timestamp', migrate_data => true, chunk_time_interval => INTERVAL '1 day')` succeeds
   **And** Prisma schema uses `@@id([id, timestamp])` composite PK

3. **Given** bloated indexes exist (76 GB total bloat)
   **When** hypertable conversion completes
   **Then** TimescaleDB creates chunk-local indexes automatically
   **And** the following rarely-used monolithic indexes are dropped:
   - `historical_prices_contract_id_source_timestamp_idx` (27 GB, 23 scans)
   - `historical_prices_timestamp_idx` (2.1 GB, 32 scans)
   - `historical_depths_timestamp_idx` (2.9 GB, 28 scans)

4. **Given** both tables are converted to hypertables
   **When** backtesting queries run (price lookups, depth snapshots, OHLCV aggregation)
   **Then** all results match pre-migration output
   **And** time-range queries show improved performance (chunk exclusion active)

5. **Given** the migration involves large data movement
   **When** the migration is planned
   **Then** a full `pg_dump` backup is taken before execution
   **And** a maintenance window is documented (estimated: 2-4 hours for 330 GB)

**Tasks:**
1. Update Prisma schema for HistoricalPrice and HistoricalDepth (composite PKs)
2. Create migration with `--create-only`, add `create_hypertable` SQL for both tables
3. Add index drop statements for bloated/unused indexes
4. Document maintenance window procedure
5. Take backup, execute migration
6. Verify chunk creation, query correctness, Prisma operations
7. Run backtesting regression tests

**Note:** This story requires a maintenance window. `migrate_data => true` on 180 GB + 151 GB tables will take 2-4 hours. Schedule accordingly.

---

#### Story 10-95-3: Compression Policies, Retention & Observability

As an operator,
I want old data automatically compressed and retention policies enforced,
So that storage stays bounded and I can monitor compression effectiveness.

**Acceptance Criteria:**

1. **Given** all three hypertables exist
   **When** compression is enabled
   **Then** each table has compression configured with appropriate `segmentby` and `orderby`:
   - `historical_prices`: segmentby `platform, contract_id, source`, orderby `timestamp DESC`
   - `historical_depths`: segmentby `platform, contract_id, source`, orderby `timestamp DESC`
   - `historical_trades`: segmentby `platform, contract_id, source`, orderby `timestamp DESC`

2. **Given** compression policies are set
   **When** the compression policy interval elapses (7 days)
   **Then** chunks older than 7 days are automatically compressed
   **And** compressed chunks remain fully queryable via Prisma

3. **Given** existing data spans ~3 months
   **When** manual compression of old chunks is triggered
   **Then** all chunks older than 7 days are compressed
   **And** total database size drops from ~337 GB to target <50 GB
   **And** compression ratio per table is logged

4. **Given** retention policies are configured
   **When** the retention interval elapses
   **Then** raw data older than 6 months is automatically dropped (chunk-level DROP, no vacuum overhead)
   **And** operator is notified via Telegram when retention runs

5. **Given** compressed data exists
   **When** the operator views the dashboard
   **Then** a new "Storage" section in the System Health page shows:
   - Total database size
   - Per-table compressed vs uncompressed size
   - Compression ratio
   - Chunk count per table

6. **Given** TimescaleDB is running
   **When** the operator needs to verify compression
   **Then** a `$queryRaw` utility or dashboard endpoint exposes `hypertable_compression_stats()`

**Tasks:**
1. Add compression configuration SQL to migration
2. Create compression policies (7-day interval)
3. Manually compress all existing old chunks
4. Add retention policies (configurable via EngineConfig, default 6 months)
5. Add Telegram notification for retention runs
6. Add Storage section to dashboard System Health page
7. Create compression stats DTO and API endpoint
8. Verify total storage reduction meets target (<50 GB)

---

## Section 5: Implementation Handoff

### Scope Classification: Moderate

This change requires backlog reorganization (new epic) and architecture doc updates, but no strategic pivot or fundamental replan.

### Handoff Recipients

| Role | Responsibility |
|------|---------------|
| **Scrum Master (Bob)** | Update `sprint-status.yaml` with new Epic 10.95 and stories. Update epics.md. |
| **Dev Agent** | Implement stories 10-95-1 through 10-95-3 following TDD workflow |
| **Operator (Arbi)** | Schedule maintenance window for Story 10-95-2. Take backup. Monitor compression results. |

### Sequencing

```
Current: Epic 10.9 in-progress (story 10-9-8 next)
    ↓
Complete Epic 10.9 (finish 10-9-8)
    ↓
NEW → Epic 10.95: TimescaleDB Migration (3 stories)
    ↓
Epic 11: Platform Extensibility & Security Hardening
    ↓
Epic 12: Advanced Compliance & Reporting
```

### Success Criteria

1. All three time-series tables are hypertables with active compression
2. Total database size < 50 GB (from 337 GB) — **85%+ reduction**
3. All existing Prisma queries and backtesting operations work unchanged
4. Cache hit rates recover to >95%
5. Automated compression and retention policies running on schedule
6. Dashboard shows compression stats
7. All existing tests pass (no regressions)

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Migration downtime (2-4 hours for large tables) | Medium | Schedule maintenance window; migrate smallest table first as validation |
| Prisma shadow database issues during future migrations | Low | Use `prisma migrate deploy` in prod (no shadow DB); test in dev first |
| Compressed chunks are append-only | Low | Only compress data >7 days old; recent data stays fully mutable |
| TimescaleDB License (TSL) for compression features | Low | TSL is free for self-hosted deployments; only restricts competing DBaaS offerings |

---

## Checklist Completion Summary

| Section | Status |
|---------|--------|
| 1. Trigger & Context | [x] Complete |
| 2. Epic Impact | [x] Complete |
| 3. Artifact Conflicts | [x] Complete — Architecture, Docker, Prisma need updates |
| 4. Path Forward | [x] Complete — Direct Adjustment selected |
| 5. Proposal Components | [x] Complete |
| 6. Final Review | [x] Complete — Approved 2026-04-03 |
