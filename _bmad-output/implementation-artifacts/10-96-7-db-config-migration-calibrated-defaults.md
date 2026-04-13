# Story 10-96.7: DB Config Migration — Activate Calibrated Defaults

Status: review

## Story

As an operator,
I want the engine_config DB row updated to match the backtest-validated defaults from 10-96-4,
so that the 5% minimum edge threshold and 0.8 profit capture ratio are actually active in paper and live trading.

## Context

Story 10-96-4 ("Configuration Defaults Calibration") updated 5 code defaults in `config-defaults.ts` to backtest-validated values. However, the seed script (`prisma/seed-config.ts`) is idempotent — it only populates NULL columns, never overwrites existing values. The `engine_config` DB row retains the pre-calibration values because they were seeded at initial setup and are non-null.

**Paper trading evidence (Apr 14-15, 38h run):**
- 19 positions, 6.25% win rate, -$347 realized PnL
- 11/16 closed positions entered with expected_edge below 5% — structurally unprofitable at entry because round-trip spread + fees exceeded the edge
- Single most impactful fix: migrating `detection_min_edge_threshold` from 0.008 to 0.05 would have prevented $207 of $347 total losses

**Sprint Change Proposal:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16-paper-trading-profitability-fix.md`

## Acceptance Criteria

1. **Given** the engine_config row has `detection_min_edge_threshold = 0.008`, **When** the Prisma migration runs, **Then** `detection_min_edge_threshold` is updated to `0.05` **And** `exit_profit_capture_ratio` is updated to `0.8`.

2. **Given** the seed script's idempotent design (only sets NULLs), **When** future config calibrations are needed, **Then** a documented pattern exists for applying config value changes via Prisma migration SQL **And** the `seed-config.ts` header comment warns that changing defaults does NOT update existing DB rows.

3. **Given** the migration is applied, **When** the engine starts, **Then** `configAccessor.detectionMinEdgeThreshold` returns `0.05` **And** `configAccessor.exitProfitCaptureRatio` returns `0.8` **And** the dashboard Settings page reflects the new values.

## Tasks / Subtasks

- [x] Task 1: Create Prisma migration SQL — update all 5 stale config values (AC: #1, #3)
  - [x] 1.1 Write a consistency guard test: verify the 5 CONFIG_DEFAULTS values match the migration target values (this test passes immediately — CONFIG_DEFAULTS was already updated by 10-96-4; the guard prevents future drift between code defaults and migration targets)
  - [x] 1.2 Create migration file via `prisma migrate dev --name calibrate_config_defaults --create-only` (generates empty migration, does NOT apply yet)
  - [x] 1.3 Write migration SQL: UPDATE 5 settings in `engine_config` WHERE `singleton_key = 'default'`
  - [x] 1.4 Apply migration via `prisma migrate dev` (applies the pending migration)
  - [x] 1.5 Verify: the consistency guard test from 1.1 passes (migration targets match code defaults)
  - [x] 1.6 Update stale test fixtures in existing `prisma/seed-config.spec.ts`: the `defaultEnvValues` object and test expectations still use pre-calibration values (0.008, 0.30, 10, 0.5, 30). Update to match calibrated values (0.05, 0.50, 25, 0.8, 60). Key locations: `defaultEnvValues` mock (~lines 33-49), env value test inputs (~line 253 `DETECTION_MIN_EDGE_THRESHOLD: '0.008'`), Prisma Decimal mock objects (~line 305 `detectionMinEdgeThreshold: { toString: () => '0.008' }`), fixture objects (~line 348 `exitProfitCaptureRatio: 0.5, pairCooldownMinutes: 30`), and value assertions (~lines 377 `riskMaxOpenPairs toBe(10)`, ~line 426 `exitProfitCaptureRatio toBe(0.5)`).
- [x] Task 2: Add idempotency warning to seed-config.ts (AC: #2)
  - [x] 2.1 Add header comment block to `prisma/seed-config.ts` documenting: (a) seed is idempotent — only sets NULLs, (b) changing CONFIG_DEFAULTS does NOT update existing DB rows, (c) use a Prisma migration SQL UPDATE for config value changes, (d) reference this story as the first instance of the pattern
- [x] Task 3: Update production .env with calibrated values — operator action (AC: #3)
  - [x] 3.1 Document the .env update needed: 4 stale values + 1 missing value (see Dev Notes)
  - [x] 3.2 NOTE: `.env` is gitignored. This is an operator manual step, not a code change. The migration fixes the DB; the .env update prevents re-seeding stale values if DB is ever reset.
- [x] Task 4: Lint + full test suite green (AC: all)
  - [x] 4.1 Run `cd pm-arbitrage-engine && pnpm lint && pnpm test`
  - [x] 4.2 Verify 4021+ tests pass (baseline: 4021 pass, 1 pre-existing e2e failure)

## Dev Notes

### Scope: Data Migration + Documentation

This story introduces **no new production code logic**. It is a data migration (SQL UPDATE) and a documentation update (seed-config.ts header). The TDD cycle is abbreviated — the consistency guard test is the only new test.

### All 5 Stale Config Values

Story 10-96-4 calibrated 5 code defaults. The same idempotent seed gap affects all 5. The migration must update ALL of them, not just the 2 highlighted in the AC:

| DB Column (snake_case) | Prisma Field (camelCase) | DB Type | Old Value | New Value | CONFIG_DEFAULTS line |
|---|---|---|---|---|---|
| `detection_min_edge_threshold` | `detectionMinEdgeThreshold` | Decimal(20,8) | 0.008 | 0.05 | `config-defaults.ts:35-38` |
| `detection_gas_estimate_usd` | `detectionGasEstimateUsd` | Decimal(20,8) | 0.30 | 0.50 | `config-defaults.ts:39-42` |
| `risk_max_open_pairs` | `riskMaxOpenPairs` | Int | 10 | 25 | `config-defaults.ts:102` |
| `exit_profit_capture_ratio` | `exitProfitCaptureRatio` | Float | 0.5 | 0.8 | `config-defaults.ts:319-322` |
| `pair_cooldown_minutes` | `pairCooldownMinutes` | Int | 30 | 60 | `config-defaults.ts:329-332` |

### Migration SQL

Create via: `cd pm-arbitrage-engine && npx prisma migrate dev --name calibrate_config_defaults --create-only`

Then write `prisma/migrations/<timestamp>_calibrate_config_defaults/migration.sql`:

```sql
-- Story 10-96-7: Activate backtest-validated config defaults from 10-96-4.
--
-- The seed script (prisma/seed-config.ts) is idempotent — it only sets NULL columns.
-- Story 10-96-4 updated code defaults in config-defaults.ts, but the existing
-- engine_config DB row retains pre-calibration values because they were non-null.
--
-- This migration applies the calibrated values directly via SQL UPDATE.
-- Pattern: When CONFIG_DEFAULTS values change and must propagate to existing DBs,
-- create a Prisma migration with an UPDATE statement (not an ALTER/ADD COLUMN).

UPDATE "engine_config"
SET
  "detection_min_edge_threshold" = 0.05,
  "detection_gas_estimate_usd" = 0.50,
  "risk_max_open_pairs" = 25,
  "exit_profit_capture_ratio" = 0.8,
  "pair_cooldown_minutes" = 60,
  "updated_at" = NOW()
WHERE "singleton_key" = 'default';
```

**Fresh DB safety:** On `prisma migrate reset`, this UPDATE affects 0 rows (engine_config table is empty pre-seed). The subsequent seed uses CONFIG_DEFAULTS (which already has the calibrated values), so fresh installs get correct values automatically.

**No `--create-only` quirk:** When using `--create-only`, the migration is generated but not applied. You must run `prisma migrate dev` again (without `--create-only`) to apply it. This two-step approach lets you write custom SQL before applying.

### Seed-Config Warning

Add a header comment block to `prisma/seed-config.ts` after the existing file-level JSDoc (line 10, before the imports). The warning should document:

```typescript
/**
 * ⚠️  CONFIG DEFAULT PROPAGATION WARNING
 *
 * This seed script is IDEMPOTENT: it only sets columns that are currently NULL.
 * Changing a defaultValue in CONFIG_DEFAULTS does NOT update existing DB rows.
 *
 * To propagate new defaults to existing databases:
 * 1. Update the defaultValue in src/common/config/config-defaults.ts
 * 2. Create a Prisma migration: npx prisma migrate dev --name <description> --create-only
 * 3. Write an UPDATE SQL statement in the migration file (see Story 10-96-7 pattern)
 * 4. Apply: npx prisma migrate dev
 *
 * First instance of this pattern: migrations/<timestamp>_calibrate_config_defaults/
 */
```

Insert AFTER the existing JSDoc block (lines 1-7) and BEFORE the first import statement (line 9, `import { PrismaClient...`).

### Production .env — Operator Manual Update Required

The `.env` file (gitignored, operator-managed) still contains pre-calibration values. After the DB migration, the DB takes priority over env vars in the 3-tier chain (DB → env → code default), so the engine will use correct values. However, the .env should be updated for consistency and to prevent re-seeding stale values if the DB is ever reset.

**Current .env values (stale):**
```
DETECTION_MIN_EDGE_THRESHOLD=0.008    # → change to 0.05
DETECTION_GAS_ESTIMATE_USD=0.30       # → change to 0.50
RISK_MAX_OPEN_PAIRS=10                # → change to 25
EXIT_PROFIT_CAPTURE_RATIO=0.5         # → change to 0.8
# PAIR_COOLDOWN_MINUTES               # → add: PAIR_COOLDOWN_MINUTES=60
```

**Already updated** (by 10-96-4): `.env.development`, `.env.example`, `.env.production.example` — no changes needed.

### Consistency Guard Test

The one new test verifies that CONFIG_DEFAULTS values match the migration targets. This prevents future drift where someone updates one but not the other.

**File:** `prisma/seed-config.spec.ts` — this file already exists with ~450 lines of tests for `buildSeedPayloads()`. Add the consistency guard test as a new `describe` block at the end of the file.

```typescript
import { CONFIG_DEFAULTS } from '../src/common/config/config-defaults.js';

describe('CONFIG_DEFAULTS calibration consistency', () => {
  it('should match the migration-applied values from 10-96-7', () => {
    // These values were applied to the DB via migration.
    // If CONFIG_DEFAULTS drifts from these, the seed (on fresh DB) will
    // produce different values than the migration (on existing DB).
    expect(CONFIG_DEFAULTS.detectionMinEdgeThreshold.defaultValue).toBe('0.05');
    expect(CONFIG_DEFAULTS.detectionGasEstimateUsd.defaultValue).toBe('0.50');
    expect(CONFIG_DEFAULTS.riskMaxOpenPairs.defaultValue).toBe(25);
    expect(CONFIG_DEFAULTS.exitProfitCaptureRatio.defaultValue).toBe(0.8);
    expect(CONFIG_DEFAULTS.pairCooldownMinutes.defaultValue).toBe(60);
  });
});
```

Note: `detectionMinEdgeThreshold` and `detectionGasEstimateUsd` are Decimal fields — their CONFIG_DEFAULTS values are strings (`'0.05'`, `'0.50'`). `exitProfitCaptureRatio` is a Float — its value is a number (`0.8`). `riskMaxOpenPairs` and `pairCooldownMinutes` are Ints — their values are numbers (`25`, `60`).

### Config-Accessor 3-Tier Resolution Chain (Reference)

The `configAccessor` reads from `engine-config.repository.ts:buildEffectiveConfig()` which resolves each field via:

1. **DB value** (if non-null) — takes priority
2. **Env var fallback** (from NestJS ConfigService) — used when DB is null
3. **CONFIG_DEFAULTS.defaultValue** — last resort

After this migration, the DB values are non-null and correct. The env vars and code defaults become irrelevant for these 5 fields.

**Key files in the resolution chain:**
- `src/common/config/config-accessor.service.ts` — singleton cache, `refresh()` calls repository
- `src/persistence/repositories/engine-config.repository.ts` — `getEffectiveConfig()`, `buildEffectiveConfig()`, `resolveField()`
- `src/common/config/config-defaults.ts` — `CONFIG_DEFAULTS` object (76 keys)
- `prisma/seed-config.ts` — idempotent seed (only sets NULLs)

### Rollback

If the calibrated values cause unexpected behavior, revert via direct SQL:

```sql
UPDATE "engine_config"
SET
  "detection_min_edge_threshold" = 0.008,
  "detection_gas_estimate_usd" = 0.30,
  "risk_max_open_pairs" = 10,
  "exit_profit_capture_ratio" = 0.5,
  "pair_cooldown_minutes" = 30,
  "updated_at" = NOW()
WHERE "singleton_key" = 'default';
```

Note: This restores the pre-calibration values. If the operator has changed any of these via the dashboard after migration, the rollback will overwrite those changes too.

### AC #3 Verification (Manual)

AC #3 ("dashboard Settings page reflects the new values") is verified manually after migration by starting the engine and checking the Settings page. No automated test is needed — the settings endpoint reads from `configAccessor`, which reads from the DB. The migration updates the DB, and the existing `settings.service.spec.ts` tests verify the read path.

### ConfigAccessor Cache Invalidation

`ConfigAccessor` caches the effective config in memory (singleton). The migration updates the DB directly — the running engine (if any) will still serve stale cached values until restart. **The engine must be restarted after migration.** This happens naturally during deploy (process restart). If running the migration manually during development, restart the dev server afterward.

### What NOT To Do

- Do NOT modify `config-defaults.ts` — code defaults are already correct (updated by 10-96-4)
- Do NOT modify `settings-metadata.ts` or `update-settings.dto.ts` — no new settings being added
- Do NOT modify `engine-config.repository.ts` or `config-accessor.service.ts` — resolution chain is correct
- Do NOT modify `.env.development`, `.env.example`, or `.env.production.example` — already updated by 10-96-4
- Do NOT create schema changes (ALTER TABLE) — all columns already exist
- Do NOT use `configService.get<boolean>()` or `configService.get<number>()` — use `ConfigAccessor`
- Do NOT modify any frontend files
- Do NOT regenerate the Prisma client — no schema change, just data migration

### Migration Naming Convention

Recent migrations follow the timestamp pattern:
- `20260413233636_add_exit_criterion_and_time_decay_cooldown`
- `20260413215232_add_entry_filter_config`
- `20260413204442_add_exit_stop_loss_pct`

Prisma auto-generates the timestamp. Use name: `calibrate_config_defaults` (via `--name calibrate_config_defaults`).

No prior migrations contain `UPDATE "engine_config"` data changes — this is the first instance of the config migration pattern.

### Previous Story Intelligence (10-96-6)

- **Test baseline:** 4021 tests pass, 1 pre-existing e2e failure (unchanged since 10-96-5)
- **Pattern:** TDD red-green cycle per unit of behavior
- **Code review:** 3-layer adversarial (Blind Hunter + Edge Case Hunter + Acceptance Auditor)
- **Key learning:** 10-96-4 updated `.env.development` (4 values + PAIR_COOLDOWN_MINUTES) and `.env.production.example` (3 values) but NOT `.env` — the production env file is operator-managed and gitignored
- **Key learning:** The seed script's P8 optimization (line 162) skips the entire upsert when all columns are populated — existing DBs with pre-calibration values never get updated by the seed

### Git Intelligence

Recent engine commits follow the pattern: `feat:` prefix for new features, `fix:` for bug fixes. Most recent relevant commits:
- `901c048 feat: update edge detection and risk management configurations` (10-96-4 code defaults)
- `a198745 feat: enhance handling of CLOSED positions in Dashboard services` (10-96-6)

This story's commit should use: `fix: migrate engine_config to backtest-validated defaults (10-96-7)`

### Project Structure Notes

- Migration file goes in `pm-arbitrage-engine/prisma/migrations/<timestamp>_calibrate_config_defaults/migration.sql`
- Seed warning goes in `pm-arbitrage-engine/prisma/seed-config.ts` (header area, after JSDoc lines 1-7)
- Consistency test goes in `pm-arbitrage-engine/prisma/seed-config.spec.ts` (new or existing file)
- All changes within `pm-arbitrage-engine/` — separate git repo from root

### Files Modified

- New: `pm-arbitrage-engine/prisma/migrations/<timestamp>_calibrate_config_defaults/migration.sql` — UPDATE 5 config values
- Modified: `pm-arbitrage-engine/prisma/seed-config.ts` — header warning (documentation only)
- Modified: `pm-arbitrage-engine/prisma/seed-config.spec.ts` — consistency guard test + stale fixture updates

### References

- [Source: sprint-change-proposal-2026-04-16-paper-trading-profitability-fix.md#Section-4-Story-10-96-7] — Full story spec, root cause chain, evidence
- [Source: epics.md#Story-10-96-7] — Epic-level AC
- [Source: 10-96-6-closed-position-exit-data-fix.md] — Previous story (test baseline 4021, patterns)
- [Source: sprint-status.yaml#line-311] — 10-96-4 completion: 5 defaults calibrated
- [Source: CLAUDE.md#Domain-Rules] — "Minimum threshold: 5% net"
- [Source: CLAUDE.md#Testing] — Co-located specs, assertion depth
- [Source: CLAUDE.md#Financial-Math] — decimal.js for Decimal fields

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no debugging needed.

### Completion Notes List

- **Task 1:** Created Prisma migration `20260416082353_calibrate_config_defaults` with UPDATE SQL for 5 stale config values. Added consistency guard test in `seed-config.spec.ts` verifying CONFIG_DEFAULTS match migration targets. Updated all stale test fixtures (defaultEnvValues, Decimal mock objects, integer/float assertions) from pre-calibration to calibrated values.
- **Task 2:** Added CONFIG DEFAULT PROPAGATION WARNING header comment to `seed-config.ts` documenting: idempotent behavior, migration pattern for propagating defaults, reference to first instance.
- **Task 3:** Operator action documented in Dev Notes — `.env` is gitignored, migration fixes DB values, .env update prevents stale re-seeding on DB reset.
- **Task 4:** 4022 tests pass (+3 from 4019 baseline). 1 pre-existing e2e failure unchanged. No regressions. Lint clean on modified files (codebase has pre-existing `@typescript-eslint/no-unsafe-member-access` warnings).
- **Code Review (Lad MCP):** 2 reviewers (kimi-k2.5, glm-5). Primary: approve with P2/P3 suggestions (migration safety check — rejected per Dev Notes "Fresh DB safety" design; zero-update test — already covered by idempotency test). Secondary: flagged `config-accessor.service.spec.ts` stale mock values — reviewed and determined these are test fixtures for accessor mechanics, not default value assertions; out of story scope. 4 spec files have pre-existing stale mock values (`0.008` for detectionMinEdgeThreshold): `config-accessor.service.spec.ts`, `engine-config.repository.spec.ts`, `settings.service.spec.ts`, `update-settings.dto.spec.ts`. These are deferred test hygiene items, not functional issues.

### Change Log

- 2026-04-16: Story 10-96-7 implemented — DB config migration + seed documentation + test fixture alignment

### File List

- New: `prisma/migrations/20260416082353_calibrate_config_defaults/migration.sql` — UPDATE 5 config values to backtest-validated defaults
- Modified: `prisma/seed-config.ts` — Added CONFIG DEFAULT PROPAGATION WARNING header comment
- Modified: `prisma/seed-config.spec.ts` — Added consistency guard test, updated 5 stale fixture values across defaultEnvValues, Decimal mocks, createdRow fixture, integer assertions, float assertions
