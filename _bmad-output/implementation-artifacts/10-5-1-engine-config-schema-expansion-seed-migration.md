# Story 10-5.1: EngineConfig Schema Expansion & Seed Migration

Status: done

## Story

As an operator,
I want all operational env vars persisted in the EngineConfig database table with typed columns and a seed migration that populates defaults from current `.env` values,
So that Story 10-5-2 can expose CRUD endpoints for runtime configuration changes without restart.

## Context

The system currently has ~79 env vars in `src/common/config/env.schema.ts` validated by Zod at startup. Only 2 values (bankrollUsd, paperBankrollUsd) live in the `engine_config` DB table — all others require a restart to change. The architecture mandates: "Engine configuration is persisted in a dedicated EngineConfig singleton model with typed columns — not a generic key-value store." [Source: architecture.md — Data Architecture section]

This story expands the EngineConfig Prisma model to hold all operator-tunable config values, creates a seed migration, and establishes a `getEffectiveConfig()` pattern (DB value with env var fallback for fresh installs). Story 10-5-2 builds CRUD + hot-reload on top; Story 10-5-3 builds the dashboard Settings page.

## Env Var Classification

**CRITICAL: Not all env vars move to DB.** Categorize as follows:

### Category A — Stay as env vars only (infrastructure/secrets/immutable)

These are NOT added to EngineConfig. They are either secrets (Story 10-5-7 scope), infrastructure addresses, or mode flags that require restart.

| Env Var | Reason |
|---------|--------|
| `NODE_ENV` | Infrastructure — runtime mode |
| `PORT` | Infrastructure — server binding |
| `DATABASE_URL` | Infrastructure — DB connection |
| `KALSHI_API_KEY_ID` | Secret (10-5-7 scope) |
| `KALSHI_PRIVATE_KEY_PATH` | Secret file path |
| `KALSHI_API_BASE_URL` | Platform URL — restart required |
| `POLYMARKET_PRIVATE_KEY` | Secret (10-5-7 scope) |
| `POLYMARKET_CLOB_API_URL` | Platform URL — restart required |
| `POLYMARKET_WS_URL` | Platform URL — WS reconnect required |
| `POLYMARKET_CHAIN_ID` | Blockchain network — immutable |
| `POLYMARKET_RPC_URL` | Platform URL — restart required |
| `POLYMARKET_GAMMA_API_URL` | Platform URL — restart required |
| `OPERATOR_API_TOKEN` | Secret (10-5-7 scope) |
| `PLATFORM_MODE_KALSHI` | Mode immutable at runtime per architecture |
| `PLATFORM_MODE_POLYMARKET` | Mode immutable at runtime per architecture |
| `ALLOW_MIXED_MODE` | Mode flag — restart required |
| `PAPER_FILL_LATENCY_MS_KALSHI` | Paper sim config — restart required |
| `PAPER_SLIPPAGE_BPS_KALSHI` | Paper sim config — restart required |
| `PAPER_FILL_LATENCY_MS_POLYMARKET` | Paper sim config — restart required |
| `PAPER_SLIPPAGE_BPS_POLYMARKET` | Paper sim config — restart required |
| `TELEGRAM_BOT_TOKEN` | Secret (10-5-7 scope) |
| `TELEGRAM_CHAT_ID` | Secret (10-5-7 scope) |
| `LLM_PRIMARY_API_KEY` | Secret (10-5-7 scope) |
| `LLM_ESCALATION_API_KEY` | Secret (10-5-7 scope) |
| `CSV_TRADE_LOG_DIR` | File path — restart required |
| `COMPLIANCE_MATRIX_CONFIG_PATH` | File path — restart required |
| `DASHBOARD_ORIGIN` | CORS — restart required |
| `KALSHI_API_TIER` | Platform tier — restart required |

### Category B — Move to EngineConfig DB (operator-tunable at runtime)

These get typed columns on the `engine_config` table. Grouped by functional area for readability.

**Trading Engine (1):**
- `pollingIntervalMs` ← `POLLING_INTERVAL_MS` (Int, default 30000)

**Edge Detection (4):**
- `detectionMinEdgeThreshold` ← `DETECTION_MIN_EDGE_THRESHOLD` (Decimal(20,8), default 0.008)
- `detectionGasEstimateUsd` ← `DETECTION_GAS_ESTIMATE_USD` (Decimal(20,8), default 0.30)
- `detectionPositionSizeUsd` ← `DETECTION_POSITION_SIZE_USD` (Decimal(20,8), default 300)
- `minAnnualizedReturn` ← `MIN_ANNUALIZED_RETURN` (Decimal(20,8), default 0.15)

**Gas Estimation (4):**
- `gasBufferPercent` ← `GAS_BUFFER_PERCENT` (Int, default 20)
- `gasPollIntervalMs` ← `GAS_POLL_INTERVAL_MS` (Int, default 30000)
- `gasPolPriceFallbackUsd` ← `GAS_POL_PRICE_FALLBACK_USD` (Decimal(20,8), default 0.40)
- `polymarketSettlementGasUnits` ← `POLYMARKET_SETTLEMENT_GAS_UNITS` (Int, default 150000)

**Execution (1):**
- `executionMinFillRatio` ← `EXECUTION_MIN_FILL_RATIO` (Decimal(20,8), default 0.25)

**Risk Management (3, bankroll already exists):**
- `riskMaxPositionPct` ← `RISK_MAX_POSITION_PCT` (Decimal(20,8), default 0.03)
- `riskMaxOpenPairs` ← `RISK_MAX_OPEN_PAIRS` (Int, default 10)
- `riskDailyLossPct` ← `RISK_DAILY_LOSS_PCT` (Decimal(20,8), default 0.05)

**Correlation Clusters (4):**
- `clusterLlmTimeoutMs` ← `CLUSTER_LLM_TIMEOUT_MS` (Int, default 15000)
- `riskClusterHardLimitPct` ← `RISK_CLUSTER_HARD_LIMIT_PCT` (Decimal(20,8), default 0.15)
- `riskClusterSoftLimitPct` ← `RISK_CLUSTER_SOFT_LIMIT_PCT` (Decimal(20,8), default 0.12)
- `riskAggregateClusterLimitPct` ← `RISK_AGGREGATE_CLUSTER_LIMIT_PCT` (Decimal(20,8), default 0.50)

**Telegram (6, tokens/chatId stay as env secrets):**
- `telegramTestAlertCron` ← `TELEGRAM_TEST_ALERT_CRON` (String, default '0 8 * * *')
- `telegramTestAlertTimezone` ← `TELEGRAM_TEST_ALERT_TIMEZONE` (String, default 'UTC')
- `telegramSendTimeoutMs` ← `TELEGRAM_SEND_TIMEOUT_MS` (Int, default 2000)
- `telegramMaxRetries` ← `TELEGRAM_MAX_RETRIES` (Int, default 3)
- `telegramBufferMaxSize` ← `TELEGRAM_BUFFER_MAX_SIZE` (Int, default 100)
- `telegramCircuitBreakMs` ← `TELEGRAM_CIRCUIT_BREAK_MS` (Int, default 60000)

**CSV Logging (1, dir stays as env):**
- `csvEnabled` ← `CSV_ENABLED` (Boolean, default true)

**LLM Scoring (10, API keys stay as env secrets):**
- `llmPrimaryProvider` ← `LLM_PRIMARY_PROVIDER` (String, default 'gemini')
- `llmPrimaryModel` ← `LLM_PRIMARY_MODEL` (String, default 'gemini-2.5-flash')
- `llmEscalationProvider` ← `LLM_ESCALATION_PROVIDER` (String, default 'anthropic')
- `llmEscalationModel` ← `LLM_ESCALATION_MODEL` (String, default 'claude-haiku-4-5-20251001')
- `llmEscalationMin` ← `LLM_ESCALATION_MIN` (Int, default 60)
- `llmEscalationMax` ← `LLM_ESCALATION_MAX` (Int, default 84)
- `llmAutoApproveThreshold` ← `LLM_AUTO_APPROVE_THRESHOLD` (Int, default 85)
- `llmMinReviewThreshold` ← `LLM_MIN_REVIEW_THRESHOLD` (Int, default 40)
- `llmMaxTokens` ← `LLM_MAX_TOKENS` (Int, default 1024)
- `llmTimeoutMs` ← `LLM_TIMEOUT_MS` (Int, default 30000)

**Discovery (7):**
- `discoveryEnabled` ← `DISCOVERY_ENABLED` (Boolean, default true)
- `discoveryRunOnStartup` ← `DISCOVERY_RUN_ON_STARTUP` (Boolean, default false)
- `discoveryCronExpression` ← `DISCOVERY_CRON_EXPRESSION` (String, default '0 0 8,20 * * *')
- `discoveryPrefilterThreshold` ← `DISCOVERY_PREFILTER_THRESHOLD` (Decimal(20,8), default 0.25)
- `discoverySettlementWindowDays` ← `DISCOVERY_SETTLEMENT_WINDOW_DAYS` (Int, default 7)
- `discoveryMaxCandidatesPerContract` ← `DISCOVERY_MAX_CANDIDATES_PER_CONTRACT` (Int, default 20)
- `discoveryLlmConcurrency` ← `DISCOVERY_LLM_CONCURRENCY` (Int, default 10)

**Resolution Polling (3):**
- `resolutionPollerEnabled` ← `RESOLUTION_POLLER_ENABLED` (Boolean, default true)
- `resolutionPollerCronExpression` ← `RESOLUTION_POLLER_CRON_EXPRESSION` (String, default '0 0 6 * * *')
- `resolutionPollerBatchSize` ← `RESOLUTION_POLLER_BATCH_SIZE` (Int, default 100)

**Calibration (2):**
- `calibrationEnabled` ← `CALIBRATION_ENABLED` (Boolean, default true)
- `calibrationCronExpression` ← `CALIBRATION_CRON_EXPRESSION` (String, default '0 0 7 1 */3 *')

**Staleness Thresholds (2):**
- `orderbookStalenessThresholdMs` ← `ORDERBOOK_STALENESS_THRESHOLD_MS` (Int, default 90000)
- `wsStalenessThresholdMs` ← `WS_STALENESS_THRESHOLD_MS` (Int, default 60000)

**Polling Concurrency (2):**
- `kalshiPollingConcurrency` ← `KALSHI_POLLING_CONCURRENCY` (Int, default 10)
- `polymarketPollingConcurrency` ← `POLYMARKET_POLLING_CONCURRENCY` (Int, default 5)

**Audit Log (1):**
- `auditLogRetentionDays` ← `AUDIT_LOG_RETENTION_DAYS` (Int, default 7)

**Stress Testing (3):**
- `stressTestScenarios` ← `STRESS_TEST_SCENARIOS` (Int, default 1000)
- `stressTestDefaultDailyVol` ← `STRESS_TEST_DEFAULT_DAILY_VOL` (Decimal(20,8), default 0.03)
- `stressTestMinSnapshots` ← `STRESS_TEST_MIN_SNAPSHOTS` (Int, default 30)

**Auto-Unwind (3):**
- `autoUnwindEnabled` ← `AUTO_UNWIND_ENABLED` (Boolean, default false)
- `autoUnwindDelayMs` ← `AUTO_UNWIND_DELAY_MS` (Int, default 2000)
- `autoUnwindMaxLossPct` ← `AUTO_UNWIND_MAX_LOSS_PCT` (Float, default 5)

**Adaptive Sequencing (2):**
- `adaptiveSequencingEnabled` ← `ADAPTIVE_SEQUENCING_ENABLED` (Boolean, default true)
- `adaptiveSequencingLatencyThresholdMs` ← `ADAPTIVE_SEQUENCING_LATENCY_THRESHOLD_MS` (Int, default 200)

**Polymarket Order Polling (2):**
- `polymarketOrderPollTimeoutMs` ← `POLYMARKET_ORDER_POLL_TIMEOUT_MS` (Int, default 5000)
- `polymarketOrderPollIntervalMs` ← `POLYMARKET_ORDER_POLL_INTERVAL_MS` (Int, default 500)

**Exit Mode (10):**
- `exitMode` ← `EXIT_MODE` (String, default 'fixed')
- `exitEdgeEvapMultiplier` ← `EXIT_EDGE_EVAP_MULTIPLIER` (Float, default -1.0)
- `exitConfidenceDropPct` ← `EXIT_CONFIDENCE_DROP_PCT` (Int, default 20)
- `exitTimeDecayHorizonH` ← `EXIT_TIME_DECAY_HORIZON_H` (Int, default 168)
- `exitTimeDecaySteepness` ← `EXIT_TIME_DECAY_STEEPNESS` (Float, default 2.0)
- `exitTimeDecayTrigger` ← `EXIT_TIME_DECAY_TRIGGER` (Float, default 0.8)
- `exitRiskBudgetPct` ← `EXIT_RISK_BUDGET_PCT` (Int, default 85)
- `exitRiskRankCutoff` ← `EXIT_RISK_RANK_CUTOFF` (Int, default 1)
- `exitMinDepth` ← `EXIT_MIN_DEPTH` (Int, default 5)
- `exitProfitCaptureRatio` ← `EXIT_PROFIT_CAPTURE_RATIO` (Float, default 0.5)

**Total Category B columns: 71 new columns** (plus existing 2 bankroll columns = 73 total data columns).

## Acceptance Criteria

### AC 1: Prisma Schema Expansion

**Given** the current EngineConfig model has only `bankrollUsd` and `paperBankrollUsd`
**When** the schema expansion is applied
**Then** all Category B env vars have corresponding typed columns on the `engine_config` table
**And** column naming uses `snake_case` via `@map()` (Prisma convention)
**And** Prisma field naming uses `camelCase` (TypeScript convention)
**And** financial values (thresholds, percentages stored as decimal) use `@db.Decimal(20, 8)`
**And** integer values (ms timings, counts, percentages stored as int) use `Int`
**And** boolean values use `Boolean`
**And** string values (cron expressions, provider names, model names, modes) use `String`
**And** float values (multipliers, ratios with negative ranges) use `Float`
**And** all new columns are nullable (`?`) to support incremental migration — fresh installs seed defaults, existing installs get NULL until seed runs

### AC 2: Seed Migration

**Given** an existing database with an `engine_config` row containing only bankroll values
**When** the seed migration runs
**Then** all new columns are populated from the current Zod-validated env var values
**And** columns that were NULL (pre-existing row) are filled with env var defaults
**And** if no `engine_config` row exists (fresh install), one is created with all defaults from env vars
**And** the migration is idempotent — running it again does not overwrite values already set by the operator via dashboard
**And** the seed uses Prisma `upsert` with the singleton key for transaction safety (safe for multi-instance startup)
**And** boolean env vars (stored as `'true'`/`'false'` strings in env) are correctly transformed to DB `Boolean` before upsert
**And** `paperBankrollUsd` is NOT seeded — it remains NULL (only set via dashboard)

### AC 3: `getEffectiveConfig()` Method

**Given** the EngineConfigRepository
**When** a `getEffectiveConfig()` method is called
**Then** it returns the DB row value for each config key
**And** if the DB column is NULL (migration hasn't run or column not yet seeded), it falls back to the Zod-validated env var value
**And** the return type is a fully-typed interface `EffectiveConfig` where no field is optional (all resolved to concrete values)
**And** the method is a single DB read (not N queries)
**And** `Prisma.Decimal` values are converted to plain decimal notation strings (no scientific notation) via `.toString()`
**And** existing `bankrollUsd`/`paperBankrollUsd` columns are included in the `EffectiveConfig` output (mapped from `RISK_BANKROLL_USD` env var)

### AC 4: EffectiveConfig Type

**Given** the new `EffectiveConfig` interface
**When** defined in `src/common/config/effective-config.types.ts`
**Then** it contains all Category B fields with their resolved TypeScript types
**And** financial Decimal fields are typed as `string` (for safe transport — consuming services convert to `Decimal` as needed)
**And** it re-exports or references the Zod env schema defaults for documentation
**And** the type is importable from `common/config/` by any module

### AC 5: Repository Expansion

**Given** the existing `EngineConfigRepository` with only `get()` and `upsertBankroll()`
**When** expanded for this story
**Then** a new `upsert(fields: Partial<EngineConfigUpdateInput>)` method exists for bulk updates (Story 10-5-2 will use this)
**And** `EngineConfigUpdateInput` is a type containing all Category B fields (no id, singletonKey, timestamps)
**And** the existing `upsertBankroll()` method is preserved for backward compatibility (existing callers unchanged)
**And** `getEffectiveConfig()` is implemented on the repository (delegates env var fallback to a pure function)

### AC 6: Env Var Fallback Mapping

**Given** a mapping between EngineConfig DB columns and env var keys
**When** defined in `src/common/config/config-defaults.ts`
**Then** a `CONFIG_DEFAULTS` record maps each EngineConfig field name to its corresponding env var key and Zod default
**And** this mapping is the single source of truth for the fallback chain: DB → env var → Zod default
**And** the mapping includes the existing `bankrollUsd` → `RISK_BANKROLL_USD` entry (unified mapping for all config)
**And** the `getEffectiveConfig()` method uses this mapping
**And** future Story 10-5-2 endpoints use this mapping for "reset to default" functionality

### AC 7: Prisma Migration

**Given** the schema changes
**When** `pnpm prisma migrate dev --name add_engine_config_settings_columns` is run
**Then** a single migration file is created adding all ~71 new columns
**And** the migration is reversible (all new columns are nullable, drop is safe)
**And** `pnpm prisma generate` produces an updated client with all new fields typed

### AC 8: Seed Script

**Given** the need to populate defaults on existing databases
**When** a seed script (`prisma/seed-config.ts`) runs
**Then** it reads env vars (already validated by Zod at app startup)
**And** for each Category B config field, it sets the DB value ONLY IF the column is currently NULL
**And** it logs each field seeded and each field skipped (already has a value)
**And** the seed script can be invoked via `pnpm prisma:seed-config` (new package.json script)
**And** the seed script is also called during `onModuleInit` of the persistence module so it auto-seeds on first startup after migration

### AC 9: Test Coverage

**Given** the new code
**When** tests are run
**Then** `getEffectiveConfig()` is tested with: all-DB-values, all-NULL-fallback, mixed DB+NULL
**And** the seed script is tested with: empty table, existing row with NULLs, existing row with values (no overwrite)
**And** `CONFIG_DEFAULTS` mapping is tested to match env schema keys (compile-time + runtime check)
**And** the `upsert()` method is tested with partial updates (only changes specified fields)
**And** all Decimal fields round-trip correctly through DB (string → Prisma.Decimal → string)

### AC 10: No Consumer Changes

**Given** this is a schema + data story only
**When** the changes are deployed
**Then** NO existing service reads are changed — all modules still read from `ConfigService` (env vars) as before
**And** Story 10-5-2 will add the `getEffectiveConfig()` call sites and hot-reload wiring
**And** existing bankroll endpoints (`GET/PUT /api/config/bankroll`) continue working unchanged

## Tasks / Subtasks

- [x] Task 1 — Prisma schema expansion (AC: #1, #7)
  - [x] 1.1 Add all 71 Category B columns to the `EngineConfig` model in `prisma/schema.prisma`
  - [x] 1.2 All new columns nullable (`?`) with `@map("snake_case_name")`
  - [x] 1.3 Run `pnpm prisma migrate dev --name add_engine_config_settings_columns`
  - [x] 1.4 Run `pnpm prisma generate` and verify no TS errors

- [x] Task 2 — EffectiveConfig type + CONFIG_DEFAULTS mapping (AC: #4, #6)
  - [x] 2.1 Create `src/common/config/effective-config.types.ts` with the `EffectiveConfig` interface
  - [x] 2.2 Create `src/common/config/config-defaults.ts` with the `CONFIG_DEFAULTS` mapping record
  - [x] 2.3 Mapping must reference env schema keys and Zod defaults for each field

- [x] Task 3 — Repository expansion (AC: #3, #5)
  - [x] 3.1 Add `getEffectiveConfig(envFallback: Partial<EffectiveConfig>): Promise<EffectiveConfig>` to `EngineConfigRepository`
  - [x] 3.2 Add `upsert(fields: Partial<EngineConfigUpdateInput>): Promise<EngineConfig>` method
  - [x] 3.3 Keep existing `upsertBankroll()` unchanged

- [x] Task 4 — Seed script (AC: #8)
  - [x] 4.1 Create `prisma/seed-config.ts` that reads validated env vars and upserts only NULL columns
  - [x] 4.2 Add `prisma:seed-config` script to `package.json`
  - [x] 4.3 Integrate auto-seed call in persistence module `onModuleInit` (for each column individually: seed only if that specific column is currently NULL)

- [x] Task 5 — Tests (AC: #9)
  - [x] 5.1 `engine-config.repository.spec.ts` — test `getEffectiveConfig()` with all-DB, all-NULL, mixed scenarios
  - [x] 5.2 `engine-config.repository.spec.ts` — test `upsert()` partial updates
  - [x] 5.3 `config-defaults.spec.ts` — verify mapping completeness against env schema
  - [x] 5.4 `seed-config.spec.ts` — test seed idempotency (no overwrite of existing values)
  - [x] 5.5 Decimal round-trip tests for all financial columns

- [x] Task 6 — Verification (AC: #10)
  - [x] 6.1 Run full test suite — zero regressions
  - [x] 6.2 Verify existing bankroll endpoints still work
  - [x] 6.3 Run `pnpm lint` — zero errors

## Dev Notes

### Existing Pattern to Follow — Bankroll (Story 9-14)

The bankroll implementation is the reference pattern for this story:

- **Schema**: `prisma/schema.prisma` lines 19-29 — EngineConfig singleton with `@map("engine_config")`
- **Repository**: `src/persistence/repositories/engine-config.repository.ts` — `get()`, `upsertBankroll()`
- **Event**: `src/common/events/config.events.ts` — `BankrollUpdatedEvent`
- **Event catalog**: `src/common/events/event-catalog.ts` line 214 — `CONFIG_BANKROLL_UPDATED`
- **Dashboard controller**: `src/dashboard/dashboard.controller.ts` lines 149-165 — `GET/PUT /api/config/bankroll`
- **Dashboard service**: `src/dashboard/dashboard.service.ts` lines 170-190 — orchestrates DB write → reload → event
- **DTO**: `src/dashboard/dto/bankroll-config.dto.ts` — validation with `@Matches`, `IsPositiveDecimalConstraint`
- **Risk manager**: `src/modules/risk-management/risk-manager.service.ts` — `loadBankrollFromDb()`, `reloadBankroll()`

### Key Architectural Constraints

1. **Typed columns, NOT key-value store** — Architecture explicitly says: "Engine configuration is persisted in a dedicated EngineConfig singleton model with typed columns — not a generic key-value store." [Source: architecture.md]
2. **Three-tier config**: env vars (seed defaults) → DB (operator-tunable) → Docker secrets (credentials). This story implements the DB tier expansion.
3. **Singleton pattern**: `singletonKey: 'default'` unique constraint — one config row per database.
4. **Decimal precision**: ALL financial values use `@db.Decimal(20, 8)` in schema and `decimal.js` in code. Never native JS math on monetary values.
5. **Nullable for migration safety**: New columns MUST be nullable so existing rows don't break. Seed script fills NULLs.

### Env Var Schema Location

- **Zod schema**: `src/common/config/env.schema.ts` (262 lines, ~79 env vars)
- **Type inference**: `src/common/config/env.types.ts` — `Env` type, `TypedConfigService`, `getEnvConfig()`
- **Validation**: Zod validates at startup via ConfigModule's `validate` function

### Prisma Column Type Mapping

| Zod Type | Prisma Type | DB Type | Example Fields |
|----------|-------------|---------|----------------|
| `decimalString()` | `Decimal @db.Decimal(20, 8)` | `DECIMAL(20,8)` | `detectionMinEdgeThreshold` |
| `z.coerce.number().int()` | `Int` | `INTEGER` | `pollingIntervalMs` |
| `z.string().transform(v => v === 'true')` | `Boolean` | `BOOLEAN` | `discoveryEnabled` |
| `z.string()` | `String` | `TEXT` | `discoveryCronExpression` |
| `z.enum([...])` | `String` | `TEXT` | `exitMode`, `llmPrimaryProvider` |
| `z.coerce.number()` (non-int) | `Float` | `DOUBLE PRECISION` | `exitTimeDecaySteepness` |

### Files to Create

| File | Purpose |
|------|---------|
| `src/common/config/effective-config.types.ts` | `EffectiveConfig` interface + `EngineConfigUpdateInput` type |
| `src/common/config/config-defaults.ts` | `CONFIG_DEFAULTS` mapping (DB field → env key → default) |
| `prisma/seed-config.ts` | Seed script for populating DB from env vars |
| `src/common/config/config-defaults.spec.ts` | Tests for CONFIG_DEFAULTS completeness |

### Files to Modify

| File | Change |
|------|--------|
| `prisma/schema.prisma` | Add ~67 columns to EngineConfig model |
| `src/persistence/repositories/engine-config.repository.ts` | Add `getEffectiveConfig()`, `upsert()` |
| `src/persistence/repositories/engine-config.repository.spec.ts` | Tests for new methods |
| `package.json` | Add `prisma:seed-config` script |

### Validation Scope & Enum Handling

- **Input validation (min/max, range checks) is Story 10-5-2 scope.** This story's `upsert()` method is a raw persistence method — the service layer in 10-5-2 will validate ranges matching Zod schema constraints before calling `upsert()`.
- **Enum-valued strings** (`exitMode`, `llmPrimaryProvider`, `llmEscalationProvider`): stored as `String` in Prisma (no DB-level enum). Validation of allowed values happens at the API layer (10-5-2). This is consistent with the existing pattern where `KALSHI_API_TIER` is a Zod enum but stored as a string.
- **Zod default synchronization**: If Zod defaults change in `env.schema.ts`, existing DB values (seeded with old defaults) do NOT auto-update. This is intentional — operator-set values are preserved. A "reset to default" mechanism is 10-5-2 scope (uses `CONFIG_DEFAULTS` mapping).

### Anti-Patterns to Avoid

1. **DO NOT** create a generic key-value `settings` table — architecture prohibits this
2. **DO NOT** change any existing service to read from DB instead of ConfigService — that's Story 10-5-2
3. **DO NOT** add CRUD endpoints — that's Story 10-5-2
4. **DO NOT** add dashboard UI — that's Story 10-5-3
5. **DO NOT** move secrets (API keys, tokens) to DB — that's Story 10-5-7
6. **DO NOT** change the `env.schema.ts` Zod validation — env vars remain the startup validation layer
7. **DO NOT** break existing `upsertBankroll()` callers — bankroll endpoints must keep working
8. **DO NOT** use `Float` for financial values — use `Decimal(20,8)`. Float is only for non-financial ratios/multipliers.

### Project Structure Notes

- All new files in `src/common/config/` — shared by all modules per architecture dependency rules
- Repository changes in `src/persistence/repositories/` — standard location
- Seed script in `prisma/` — Prisma convention for seed files
- Tests co-located with source files (same directory)

### References

- [Source: architecture.md — Data Architecture section] — EngineConfig singleton, typed columns mandate
- [Source: architecture.md — Environment Configuration] — Three-tier config (env → DB → secrets)
- [Source: env.schema.ts] — Full env var inventory with Zod types and defaults
- [Source: engine-config.repository.ts] — Existing repository pattern
- [Source: bankroll-config.dto.ts] — Existing DTO pattern for config endpoints
- [Source: config.events.ts] — BankrollUpdatedEvent pattern
- [Source: Epic 10 retrospective] — Action items feeding into Epic 10.5
- [Source: epics.md — Epic 10.5] — Story sequencing: Track A (10-5-1 → 10-5-2 → 10-5-3)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context) via Claude Code CLI with bmad-dev-skill

### Debug Log References
- ATDD checklist: `_bmad-output/test-artifacts/atdd-checklist-10-5-1.md`
- Migration: `prisma/migrations/20260322143136_add_engine_config_settings_columns/migration.sql`

### Completion Notes List
- **39 ATDD tests** unskipped and passing (17 repository, 12 config-defaults, 10 seed-config)
- **Test counts**: 2409 baseline → 2448 final (+39 new, 0 regressions)
- **Lint**: 0 errors (4 pre-existing warnings in unrelated file)
- **Lad MCP code review** (attempt 2): primary reviewer (kimi-k2.5) returned 8 findings. 3 fixed:
  - CRITICAL: `getEffectiveConfig()` now merges env fallbacks with CONFIG_DEFAULTS when no DB row exists (guarantees complete EffectiveConfig)
  - MEDIUM: Fixed misleading comment on paperBankrollUsd in repository
  - MEDIUM: PersistenceModule seed error handling now distinguishes schema-not-ready (warn) from fatal errors (error)
- 5 findings skipped with rationale:
  - HIGH (upsert create path): seed always runs first; row exists by 10-5-2. Cast intentional.
  - HIGH (paperBankrollUsd in update type): by design — AC5 says "all Category B fields"; paperBankrollUsd has own endpoint.
  - MEDIUM (resolveField duck typing): matches codebase convention (Prisma Decimal toString pattern). Date fields not in CONFIG_DEFAULTS.
  - LOW (boolean case-sensitivity): matches Zod schema convention.
  - LOW (float parsing edge): not a real issue — `parseFloat('5.0')` returns `5.0`.
- Secondary reviewer (z-ai/glm-5-turbo) failed consistently with provider error — not actionable.
- **ATDD idempotency test fix**: mock `createdRow` was incomplete (only 5 fields, comment said "all"). Expanded to include all 71+ fields for realistic simulation.

### File List

**Created:**
| File | Purpose |
|------|---------|
| `src/common/config/effective-config.types.ts` | `EffectiveConfig` interface + `EngineConfigUpdateInput` type |
| `src/common/config/config-defaults.ts` | `CONFIG_DEFAULTS` mapping (72 entries: 71 Cat B + bankrollUsd) |
| `prisma/seed-config.ts` | Seed script — idempotent, NULL-only seeding, boolean/int/float/decimal conversion |
| `prisma/migrations/20260322143136_add_engine_config_settings_columns/migration.sql` | 71 ADD COLUMN statements |

**Modified:**
| File | Change |
|------|--------|
| `prisma/schema.prisma` | +71 nullable typed columns on EngineConfig model |
| `src/persistence/repositories/engine-config.repository.ts` | +`getEffectiveConfig()`, +`upsert()`, imports for new types |
| `src/persistence/repositories/engine-config.repository.spec.ts` | +17 tests (unskipped from ATDD), type-safe mock casts |
| `src/common/config/config-defaults.spec.ts` | +12 tests (unskipped from ATDD), unused var fix |
| `prisma/seed-config.spec.ts` | +10 tests (unskipped from ATDD), complete idempotency mock |
| `src/common/persistence.module.ts` | +OnModuleInit auto-seed with error classification |
| `package.json` | +`prisma:seed-config` script |
