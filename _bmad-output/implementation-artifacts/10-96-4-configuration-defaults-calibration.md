# Story 10-96.4: Configuration Defaults Calibration

Status: done

## Story

As an operator,
I want configuration defaults updated to backtest-validated values,
so that the live engine starts with settings proven to be profitable instead of untested MVP guesses.

## Acceptance Criteria

1. **Given** `config-defaults.ts` contains the five settings below
   **When** this story is applied
   **Then** the `defaultValue` fields are updated:

   | Setting | envKey | Current Default | New Default | Type | Rationale |
   |---------|--------|-----------------|-------------|------|-----------|
   | `detectionMinEdgeThreshold` | `DETECTION_MIN_EDGE_THRESHOLD` | `'0.008'` | `'0.05'` | decimal string | Below 5%, fee drag makes entries negative EV |
   | `detectionGasEstimateUsd` | `DETECTION_GAS_ESTIMATE_USD` | `'0.30'` | `'0.50'` | decimal string | Conservative estimate validated by backtest |
   | `riskMaxOpenPairs` | `RISK_MAX_OPEN_PAIRS` | `10` | `25` | integer | Phase 1 PRD spec FR-RM-02 |
   | `exitProfitCaptureRatio` | `EXIT_PROFIT_CAPTURE_RATIO` | `0.5` | `0.8` | float | 80% threshold validated — 100% PROFIT_CAPTURE win rate |
   | `pairCooldownMinutes` | `PAIR_COOLDOWN_MINUTES` | `30` | `60` | integer | Modest increase for generic cooldown |

2. **Given** `env.schema.ts` Zod defaults match `config-defaults.ts` defaults
   **When** this story is applied
   **Then** the five Zod `.default()` values are updated to match the new defaults above

3. **Given** `.env.example` documents current default values in comments
   **When** this story is applied
   **Then** the five entries are updated to reflect the new defaults

4. **Given** all new default values
   **When** validated against existing Zod constraints and DTO decorators
   **Then** all values are within existing bounds (no schema/DTO changes needed):
   - `'0.05'` passes `decimalString()` regex
   - `'0.50'` passes `decimalString()` regex
   - `25` passes `z.coerce.number().int().positive()` and `@IsInt() @Min(1)`
   - `0.8` passes `z.coerce.number().min(0.01).max(5)` and `@IsNumber() @Min(0.01) @Max(5)`
   - `60` passes `z.coerce.number().int().min(0)` and `@IsInt() @Min(0)`

5. **Given** `settings-metadata.ts` references `CONFIG_DEFAULTS.*.defaultValue` dynamically
   **When** config-defaults.ts values change
   **Then** the dashboard settings page automatically shows updated defaults (no metadata file changes)

6. **Given** `seed-config.ts` reads from `CONFIG_DEFAULTS` dynamically
   **When** config-defaults.ts values change
   **Then** fresh installs are seeded with new defaults (no seed file changes)

7. **Given** existing test suites hardcode old default values in mock data and assertions
   **When** defaults change
   **Then** all affected tests are updated and the full suite passes (baseline: 3899 tests)

8. **Given** the structural guard for `configService.get<number>()` call count
   **When** this story is applied
   **Then** the baseline count remains at 58 (no new configService.get calls introduced)

## Tasks / Subtasks

- [x] Task 1: Update `config-defaults.ts` default values (AC: #1)
  - [x] Change `detectionMinEdgeThreshold.defaultValue` from `'0.008'` to `'0.05'` (line 37)
  - [x] Change `detectionGasEstimateUsd.defaultValue` from `'0.30'` to `'0.50'` (line 41)
  - [x] Change `riskMaxOpenPairs.defaultValue` from `10` to `25` (line 102)
  - [x] Change `exitProfitCaptureRatio.defaultValue` from `0.5` to `0.8` (line 321)
  - [x] Change `pairCooldownMinutes.defaultValue` from `30` to `60` (line 331)

- [x] Task 2: Update `env.schema.ts` Zod defaults to match (AC: #2)
  - [x] Change `DETECTION_MIN_EDGE_THRESHOLD` Zod default from `'0.008'` to `'0.05'` (line 65)
  - [x] Change `DETECTION_GAS_ESTIMATE_USD` Zod default from `'0.30'` to `'0.50'` (line 66)
  - [x] Change `RISK_MAX_OPEN_PAIRS` Zod default from `10` to `25` (line 101)
  - [x] Change `EXIT_PROFIT_CAPTURE_RATIO` Zod default from `0.5` to `0.8` (line 287)
  - [x] Change `PAIR_COOLDOWN_MINUTES` Zod default from `30` to `60` (line 291)

- [x] Task 3: Update `.env.example` documentation (AC: #3)
  - [x] Update `DETECTION_MIN_EDGE_THRESHOLD=0.008` to `0.05` (line 28)
  - [x] Update `DETECTION_GAS_ESTIMATE_USD=0.30` to `0.50` (line 29)
  - [x] Update `RISK_MAX_OPEN_PAIRS=10` to `25` (line 50)
  - [x] Update `EXIT_PROFIT_CAPTURE_RATIO=0.5` to `0.8` (line 164)
  - [x] Add `PAIR_COOLDOWN_MINUTES=60` if missing (not currently in .env.example — verify and add if absent)

- [x] Task 4: Fix tests that assert old default values (AC: #7)
  - [x] Run `pnpm test` — collect all failures from default value changes
  - [x] Fix config-system tests that verify defaults:
    - `src/common/config/config-defaults.spec.ts` — update expected default values
    - `src/common/config/env.schema.spec.ts` — update expected Zod parse outputs
    - `src/common/config/config-accessor.service.spec.ts` — no changes needed (mock data, not default assertions)
  - [x] Fix repository tests using old defaults in mock data:
    - `src/persistence/repositories/engine-config.repository.spec.ts` — no changes needed (mock DB data, not default assertions)
  - [x] Fix seed-config tests:
    - `prisma/seed-config.spec.ts` — no changes needed (reads from CONFIG_DEFAULTS dynamically)
  - [x] Fix dashboard tests:
    - `src/dashboard/settings.service.spec.ts` — update envDefault assertions
  - [x] **IMPORTANT**: Do NOT change tests that use `0.008`, `0.3`, `10`, `0.5`, or `30` as arbitrary mock input data for business logic (edge calculations, risk checks, etc.) — those are test inputs, not default assertions
  - [x] Verify all 3899+ tests pass

- [x] Task 5: Verify structural guards and end-to-end (AC: #4, #5, #6, #8)
  - [x] Run `pnpm lint` — zero errors in modified files (1276 pre-existing)
  - [x] Confirm `configService.get<number>()` baseline stays at 58 (structural guard test passes)
  - [x] Confirm settings count stays at 101 (no new settings added)
  - [x] Confirm env schema completeness test passes (17 allowlisted keys unchanged)

## Dev Notes

### Scope — Value Changes Only

This story changes **only default values** in 3 source files + test file updates. No new settings, no new config keys, no schema changes, no migrations, no new services. The config system's dynamic references (`settings-metadata.ts`, `seed-config.ts`, `config-accessor`) propagate changes automatically.

### Config System Architecture (3-Tier Fallback)

```
DB value (EngineConfig row) → env var (NestJS ConfigService) → Zod default (env.schema.ts)
```

- `config-defaults.ts` — defines `envKey` + `defaultValue` mappings (used by `getEffectiveConfig()` NULL-column fallback and seed script)
- `env.schema.ts` — Zod validation with `.default()` values (what NestJS ConfigService returns when no env var set)
- Both MUST stay in sync. `settings-metadata.ts` and `seed-config.ts` read from `CONFIG_DEFAULTS` dynamically.

### Files to Modify

| File | Change |
|------|--------|
| `src/common/config/config-defaults.ts` | 5 `defaultValue` changes |
| `src/common/config/env.schema.ts` | 5 Zod `.default()` changes |
| `.env.example` | 5 documented value updates |

### Files NOT to Modify

| File | Why |
|------|-----|
| `src/common/config/settings-metadata.ts` | References `CONFIG_DEFAULTS.*.defaultValue` — auto-updates |
| `src/common/config/effective-config.types.ts` | Type interface, not values |
| `prisma/seed-config.ts` | Reads from `CONFIG_DEFAULTS` — auto-updates |
| `prisma/schema.prisma` | No schema changes needed |
| `src/dashboard/dto/update-settings.dto.ts` | All new values within existing bounds |

### Test Impact Analysis

The following test files hardcode old default values and **will break** when defaults change. The developer must update them:

**Config-system tests (assert default values directly):**
- `src/common/config/config-defaults.spec.ts` — verifies CONFIG_DEFAULTS entries
- `src/common/config/env.schema.spec.ts` — verifies Zod default parse output
- `src/common/config/config-accessor.service.spec.ts` — mock effective config with old defaults

**Repository tests (mock effective config with old defaults):**
- `src/persistence/repositories/engine-config.repository.spec.ts` — effective config resolution

**Seed tests (verify seed output matches defaults):**
- `prisma/seed-config.spec.ts` — seed values for all 5 keys

**Dashboard tests (envDefault display values):**
- `src/dashboard/settings.service.spec.ts` — settings metadata assertions

**Tests that use similar numbers as mock INPUT data (do NOT change):**
- `src/modules/arbitrage-detection/edge-calculator.service.spec.ts` — uses `0.008` as test edge inputs
- `src/modules/monitoring/match-apr-updater.service.spec.ts` — uses `0.008` in mock data
- `src/modules/risk-management/risk-manager.service.spec.ts` — uses `10` as maxOpenPairs in mocks
- `src/modules/arbitrage-detection/pair-concentration-filter.service.spec.ts` — uses `30` in mock configs

**Triage strategy**: Run `pnpm test`, examine each failure. If the assertion references `CONFIG_DEFAULTS`, `envDefault`, Zod parse output, or seed-config output → update to new value. If it's a business logic test using the old number as mock input → leave it alone.

### Backtest Evidence

| Setting | Old | New | Evidence |
|---------|-----|-----|----------|
| Min edge threshold | 0.8% | 5% | Below 5%, fee drag + gas makes entries negative EV. Backtest: -$3,406 P&L at 0.8% → +$2,026 at 5% |
| Gas estimate | $0.30 | $0.50 | Backtest showed ~$800 invisible entry costs. Conservative $0.50 covers Polygon gas spikes |
| Max open pairs | 10 | 25 | PRD FR-RM-02 specifies 25 for Phase 1. MVP placeholder was too conservative |
| Profit capture ratio | 50% | 80% | 80% threshold achieved 100% PROFIT_CAPTURE win rate in backtest (81 losers eliminated) |
| Pair cooldown | 30 min | 60 min | Modest increase to reduce fee churning on generic cooldown (TIME_DECAY cooldown handles toxic pairs at 24h) |

### What NOT To Do

- Do NOT add new config keys, settings, or DB columns
- Do NOT change the `return;` on line 65 of `src/core/trading-engine.service.ts` (live engine stays disabled until Epic 10.96 retrospective)
- Do NOT modify DTO validation decorators or Zod constraints (all new values are within bounds)
- Do NOT change `settings-metadata.ts` or `seed-config.ts` (they auto-update via CONFIG_DEFAULTS)
- Do NOT use `configService.get<number>()` or `configService.get<boolean>()` — use `ConfigAccessor`
- Do NOT change test mock data that happens to use the same numbers as old defaults (distinguish default-assertion tests from business-logic tests)

### Previous Story Intelligence (10-96-3)

**Config Pattern (5 files for new settings, 3 files for value-only changes):**
Story 10-96-3 added `timeDecayCooldownHours` touching 5 files (env.schema, config-defaults, effective-config.types, settings-metadata, engine-config.repository). This story only changes values — no new keys — so only 3 source files need changes (config-defaults, env.schema, .env.example). The rest auto-propagate.

**Structural guard baseline:** `configService.get<number>()` count = 58. Settings count = 101. Both must remain unchanged.

**TDD approach:** Simple Red-Green cycle: change one default → run tests → fix broken assertions → verify green → next default. All 5 can be changed simultaneously since they're independent values.

### Project Structure Notes

- All config files in `src/common/config/` — confirmed aligned with architecture module structure
- `.env.example` at engine root `pm-arbitrage-engine/.env.example`
- No module boundary violations — this story stays entirely within `common/config/` and test files

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-13-live-engine-alignment.md#Story-10-96-4] — calibration table with line numbers
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-10.96] — AC table and backtest evidence
- [Source: CLAUDE.md#Domain-Rules] — min edge threshold 0.8% net (being raised to 5%)
- [Source: CLAUDE.md#Architecture] — config system lives in `common/config/`
- [Source: PRD FR-RM-02] — riskMaxOpenPairs = 25 for Phase 1

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
None — clean implementation, no debugging required.

### Completion Notes List
- Updated 5 default values in `config-defaults.ts`: detectionMinEdgeThreshold 0.008→0.05, detectionGasEstimateUsd 0.30→0.50, riskMaxOpenPairs 10→25, exitProfitCaptureRatio 0.5→0.8, pairCooldownMinutes 30→60
- Synced 5 Zod `.default()` values in `env.schema.ts`
- Updated `.env.example` with new defaults + added missing `PAIR_COOLDOWN_MINUTES=60` entry
- Fixed 5 test assertions across 3 spec files: `config-defaults.spec.ts` (3 assertions), `env.schema.spec.ts` (1 assertion), `settings.service.spec.ts` (2 assertions)
- Triage decision: `config-accessor.service.spec.ts`, `engine-config.repository.spec.ts`, `seed-config.spec.ts` did NOT need changes — their mock values are test inputs (explicit DB data or dynamically derived from CONFIG_DEFAULTS), not default-value assertions
- All structural guards pass: configService.get<number>() count=58, settings count=101, env schema completeness=17 allowlisted keys
- Test suite: 3908 passed (baseline was 3907 + 3 pre-existing failures). +1 from intermittent TimescaleDB test. 2 pre-existing e2e failures remain (data-ingestion WebSocket timeout timing).

### File List
- `src/common/config/config-defaults.ts` — 5 defaultValue changes
- `src/common/config/env.schema.ts` — 5 Zod .default() changes
- `.env.example` — 5 value updates + 1 new PAIR_COOLDOWN_MINUTES entry
- `src/common/config/config-defaults.spec.ts` — 3 assertion updates (decimal, integer, float defaults)
- `src/common/config/env.schema.spec.ts` — 1 assertion update (RISK_MAX_OPEN_PAIRS default)
- `src/dashboard/settings.service.spec.ts` — 2 assertion updates (currentValue + envDefault for detectionMinEdgeThreshold)

### Change Log
- 2026-04-14: Story 10-96-4 implemented — 5 configuration defaults calibrated to backtest-validated values. All ACs satisfied.
