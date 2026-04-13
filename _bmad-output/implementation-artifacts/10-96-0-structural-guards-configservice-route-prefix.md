# Story 10-96.0: Structural Guards — configService Type Safety & Route Prefix Validation

Status: done

## Story

As an operator,
I want configService.get() type-safety enforcement and route prefix validation as structural guards,
So that two recurring defect classes (string-typed config values, missing route prefixes) are prevented at compile/startup time rather than caught in review.

## Context & History

**This is slot-zero for Epic 10.96 (Agreement #34 enforcement).** These guards slipped two consecutive epics:
- **Epic 10.9 retro (2026-04-04):** configService.get<boolean>() returning strings hit in stories 10-9-6 and 10-9-7. Global prefix duplication (`api/api/...`) in 4 controllers caught only by QA, not code review. Both committed as structural guard stories for early 10.95.
- **Epic 10.95:** Not addressed — capacity consumed by course corrections (180% scope growth). Preventive work lost to curative work.
- **Epic 10.95 retro (2026-04-13):** Promoted to slot-zero in 10.96, non-negotiable per Arbi directive. Agreement #34 ratified specifically to prevent this recurrence.

Resolves debt ledger items #1, #2, #3. Agreement #26 ("Structural guards over review vigilance").

## Acceptance Criteria

1. **Given** `configService.get<boolean>()` returns strings (NestJS behavior)
   **When** the structural guard is applied
   **Then** typed config helper functions replace raw `configService.get<boolean|number>()` calls with explicit parsing
   **And** boolean/number env vars are parsed at the boundary, not trusted as generic types

2. **Given** route prefixes can be omitted or mis-cased on new controllers
   **When** the structural guard is applied
   **Then** a startup validation check verifies all controllers have route prefixes matching kebab-case
   **And** missing or mis-cased prefixes cause a startup error (fail-fast)

3. **Given** the dashboard API client was generated before recent endpoint changes
   **When** this story completes
   **Then** the API client is regenerated via `swagger-typescript-api`
   **And** the dashboard compiles without type errors

## Tasks / Subtasks

- [x] Task 1: Create typed config helper utilities (AC: #1)
  - [x] 1.1 Create `src/common/config/typed-config.helpers.ts` with `getConfigBoolean(configService, key, defaultValue)` and `getConfigNumber(configService, key, defaultValue)` functions
  - [x] 1.2 `getConfigBoolean`: reads raw value, returns `value === true || value === 'true'` — handles both Zod-transformed and untransformed values defensively
  - [x] 1.3 `getConfigNumber`: reads raw value, calls `Number(value)`. If key is undefined/missing, return `defaultValue`. If key is present but non-parseable (NaN after `Number()`), throw `SystemHealthError` with code `INVALID_CONFIGURATION` (4006) — never silently pass a string as a number
  - [x] 1.4 Unit tests for both helpers: string 'true'/'false', actual boolean true/false, undefined returns default, explicit `null` returns default, NaN rejection for number helper (throws SystemHealthError 4006), valid number-as-string parses correctly
- [x] Task 2: Migrate 11 boolean configService.get call sites (AC: #1)
  - [x] 2.1 Replace all `configService.get<boolean>(key)` calls with `getConfigBoolean(this.configService, key, defaultValue)` across 7 files (11 call sites listed below). Note: `ALLOW_MIXED_MODE` is a permit flag (default `false`, blocks mixed mode when disabled) — use `getConfigBoolean(this.configService, 'ALLOW_MIXED_MODE', false)` to preserve existing guard-clause behavior
  - [x] 2.2 Remove the `<boolean>` type parameter from each migrated call
  - [x] 2.3 Verify existing tests still pass — zero behavior change since Zod transforms are already correct
- [x] Task 3: Add structural guard test banning raw boolean/number type assertions (AC: #1)
  - [x] 3.1 Create `src/common/config/typed-config.guard.spec.ts`
  - [x] 3.2 Grep-based test scanning `src/**/*.ts` (excluding `*.spec.ts` and `node_modules`) for patterns `configService.get<boolean>` and `configService.get<number>`
  - [x] 3.3 Test fails if any match is found, with message listing the violating files and instructions to use `getConfigBoolean`/`getConfigNumber`
  - [x] 3.4 Verify it catches a synthetic violation and passes when clean
- [x] Task 4: Add structural guard test for env schema completeness (AC: #1)
  - [x] 4.1 Create test in `src/common/config/env-schema-completeness.guard.spec.ts`
  - [x] 4.2 Grep `src/**/*.ts` (non-test) for `configService.get(...)` patterns, extract all env key string literals
  - [x] 4.3 Extract defined keys from Zod schema using `Object.keys(envSchema.shape)` at runtime — this returns all top-level key names without AST parsing. Reference: `getEnvConfig()` in `env.types.ts` already demonstrates interacting with the schema object
  - [x] 4.4 Test fails if any runtime-used key is not defined in the Zod schema — catches drift when new env vars are added without validation
  - [x] 4.5 Allowlist for legitimately unvalidated keys with comment explaining each exception: namespaced NestJS config keys (e.g., `backtesting.maxConcurrentRuns`), third-party service keys added after schema creation (e.g., `PREDEXON_API_KEY`, `ODDSPIPE_API_KEY`). Each allowlisted key gets a `// TODO: add to env.schema.ts` comment
- [x] Task 5: Create route prefix validation guard test (AC: #2)
  - [x] 5.1 Create `src/common/guards/route-prefix-validation.guard.spec.ts` as a structural guard test (not a runtime guard)
  - [x] 5.2 Grep-based approach (preferred — no infrastructure deps, runs fast): use `fs.readFileSync` + recursive `readdirSync` to scan all `src/**/*.controller.ts` files. Extract `@Controller('...')` decorator arguments via regex. Handle: single-quoted strings, double-quoted strings, template literals (reject these — prefix must be a static string)
  - [x] 5.3 For each extracted controller prefix, verify: (a) non-empty string (allowlist: `app.controller.ts` with empty `@Controller()` for health endpoint), (b) kebab-case format (regex: `/^[a-z][a-z0-9]*(-[a-z0-9]+)*(\/[a-z][a-z0-9]*(-[a-z0-9]+)*)*$/`), (c) does NOT start with `api/` or `api` (catches the exact `api/api/...` bug from 10-9-6), (d) duplicate prefixes are allowlisted per pair (e.g., `positions` shared by `single-leg-resolution.controller.ts` and `dashboard/position-management.controller.ts`)
  - [x] 5.4 Test fails on violation with actionable error message including file path and the offending prefix value
- [x] Task 6: Regenerate dashboard API client (AC: #3)
  - [x] 6.1 Start the engine (`pnpm start:dev` in `pm-arbitrage-engine/`)
  - [x] 6.2 Run `pnpm generate-api` in `pm-arbitrage-dashboard/`
  - [x] 6.3 Verify dashboard compiles: `cd pm-arbitrage-dashboard && pnpm build`
  - [x] 6.4 Commit regenerated `Api.ts` in the dashboard repo
- [x] Task 7: Run full test suite and lint (AC: all)
  - [x] 7.1 `cd pm-arbitrage-engine && pnpm lint`
  - [x] 7.2 `cd pm-arbitrage-engine && pnpm test`
  - [x] 7.3 All tests pass, including new guard tests

## Dev Notes

### Guard 1: configService.get Type-Safety — Implementation Details

**Root cause:** NestJS `ConfigService.get<T>()` type parameter is a cast, not a coercion. For env vars, values are always strings at the process.env level. The project's Zod schema (`env.schema.ts`) transforms booleans via `.string().transform((v) => v === 'true')`, so AFTER ConfigModule validation the values ARE correct types in the config cache. But:
1. New env vars added without Zod transforms silently return raw strings
2. Code using truthy/falsy checks (`if (!enabled)`) is fragile — works today because Zod transforms exist, breaks silently if transform is missing
3. `configService.get<boolean>('KEY')` reads as type-safe but isn't — the generic parameter is a lie

**Existing infrastructure to reuse (DO NOT reinvent):**
- `src/common/config/env.schema.ts` — Zod validation schema. Boolean transforms: `.string().transform((v) => v === 'true')`. Number coercion: `z.coerce.number()`. Financial: custom `decimalString()`.
- `src/common/config/env.types.ts` — `TypedConfigService = ConfigService<Env, true>` (exists but unused everywhere). `getEnvConfig()` helper.
- `src/common/config/config-accessor.service.ts` — DB-backed config accessor with env fallback. Used by only 2 services. NOT the right layer for this guard (it's for DB config, not env vars).
- `src/common/config/config-defaults.ts` — 80+ entries mapping DB field names to env keys and defaults.
- `src/common/config/effective-config.types.ts` — `EffectiveConfig` interface for DB-backed config.

**The typed helpers should be standalone functions, NOT a service.** They take `ConfigService` as a parameter, making them usable anywhere without DI changes. This is intentional — adding a new injectable service would increase constructor deps across 35+ files.

**11 boolean call sites to migrate (7 files):**

| # | File | Line | Current Pattern | Safety |
|---|------|------|----------------|--------|
| 1 | `modules/monitoring/csv-trade-log.service.ts` | ~86 | `get<boolean>('CSV_ENABLED') ?? true` then `=== false` | Fragile |
| 2 | `modules/contract-matching/calibration.service.ts` | ~55 | `get<boolean>('CALIBRATION_ENABLED') ?? true` then `!enabled` | DANGEROUS |
| 3 | `modules/contract-matching/candidate-discovery.service.ts` | ~122 | `get<boolean>('DISCOVERY_ENABLED') ?? false` then `!enabled` | DANGEROUS |
| 4 | `modules/contract-matching/candidate-discovery.service.ts` | ~142 | `get<boolean>('DISCOVERY_RUN_ON_STARTUP') ?? false` then `if (runOnStartup)` | DANGEROUS |
| 5 | `modules/execution/auto-unwind.service.ts` | ~84 | `get<boolean>('AUTO_UNWIND_ENABLED')` then `enabled !== true` | Safe but inconsistent |
| 6 | `modules/contract-matching/external-pair-ingestion.service.ts` | ~41 | `get<boolean>('EXTERNAL_PAIR_INGESTION_ENABLED')` then `enabled !== true` | Safe but inconsistent |
| 7 | `modules/contract-matching/external-pair-ingestion.service.ts` | ~67 | `get<boolean>('EXTERNAL_PAIR_INGESTION_ENABLED')` then `enabled !== true` | Safe but inconsistent |
| 8 | `modules/contract-matching/resolution-poller.service.ts` | ~48 | `get<boolean>('RESOLUTION_POLLER_ENABLED') ?? true` then `!enabled` | DANGEROUS |
| 9 | `dashboard/dashboard-event-mapper.service.ts` | ~107 | `get<boolean>('AUTO_UNWIND_ENABLED') === true` | Safe |
| 10 | `core/engine-lifecycle.service.ts` | ~260 | `get<boolean>('ALLOW_MIXED_MODE') ?? false` then `!allowMixed` | DANGEROUS |
| 11 | `modules/backtesting/ingestion/incremental-ingestion.service.ts` | ~48 | `get<boolean>('INCREMENTAL_INGESTION_ENABLED')` then `enabled !== true` | Safe but inconsistent |

**Line numbers are approximate** — always search by the env key string (e.g., `'CSV_ENABLED'`) rather than relying on exact line numbers.

**Do NOT migrate all ~105 configService.get calls.** This story focuses on boolean calls (the proven defect class) and the structural guard tests that prevent future violations. Number calls are lower risk (Zod coerces via `z.coerce.number()`) but the guard test in Task 3 covers them for future prevention. Existing safe number patterns (e.g., `Number(configService.get(...))` wrapping in `connector.module.ts`, `risk-config.utils.ts`) should remain as-is.

**Env keys used at runtime but NOT in env.schema.ts (~15 keys).** These bypass Zod validation entirely:
- `TELEGRAM_BATCH_WINDOW_MS`, `CONTRACT_PAIRS_CONFIG_PATH`, `AUDIT_LLM_BATCH_SIZE`, `AUDIT_LLM_DELAY_MS`, `COMPLEMENTARY_TOLERANCE`, `PREDEXON_API_KEY`, `PREDEXON_BASE_URL`, `ODDSPIPE_API_KEY`, `ODDSPIPE_BASE_URL`, `PMXT_ARCHIVE_BASE_URL`, `PMXT_ARCHIVE_LOCAL_DIR`, `DIVERGENCE_PRICE_THRESHOLD`, `DEGRADATION_THRESHOLD_MULTIPLIER`, `STATIC_GAS_FALLBACK_USD`
- The env-schema-completeness guard (Task 4) catches these. The story does NOT require adding all of them to env.schema.ts — only that the guard test documents the gap. Add an allowlist with `// TODO: add to env.schema.ts` for each.

**Correct defensive pattern (reference):** `leg-sequencing.service.ts:85-89` already does it right:
```typescript
const enabledRaw = this.configService.get<boolean | string>('ADAPTIVE_SEQUENCING_ENABLED', true);
const enabled = enabledRaw === true || enabledRaw === 'true';
```
The new `getConfigBoolean` helper encapsulates this exact pattern.

### Guard 2: Route Prefix Validation — Implementation Details

**Root cause:** NestJS controllers with `@Controller()` (empty) or `@Controller('camelCase')` silently create wrong routes. The `api/api/...` duplication in story 10-9-6 was caught only by QA.

**Current state — all 15 controllers are compliant:**

| Controller | Prefix | Full Route |
|-----------|--------|------------|
| `app.controller.ts` | `''` (empty — root) | `/api` |
| `trade-export.controller.ts` | `'exports'` | `/api/exports` |
| `reconciliation.controller.ts` | `'reconciliation'` | `/api/reconciliation` |
| `stress-test.controller.ts` | `'risk/stress-test'` | `/api/risk/stress-test` |
| `risk-override.controller.ts` | `'risk'` | `/api/risk` |
| `single-leg-resolution.controller.ts` | `'positions'` | `/api/positions` |
| `calibration.controller.ts` | `'knowledge-base'` | `/api/knowledge-base` |
| `backtest.controller.ts` | `'backtesting/runs'` | `/api/backtesting/runs` |
| `historical-data.controller.ts` | `'backtesting'` | `/api/backtesting` |
| `match-validation.controller.ts` | `'backtesting/validation'` | `/api/backtesting/validation` |
| `position-management.controller.ts` | `'positions'` | `/api/positions` |
| `settings.controller.ts` | `'dashboard/settings'` | `/api/dashboard/settings` |
| `performance.controller.ts` | `'performance'` | `/api/performance` |
| `match-approval.controller.ts` | `'matches'` | `/api/matches` |
| `dashboard.controller.ts` | `'dashboard'` | `/api/dashboard` |

**Known intentional sharing:** `single-leg-resolution.controller.ts` and `position-management.controller.ts` both use `@Controller('positions')`. Different method routes prevent conflicts. Allowlist this pair.

**`app.controller.ts` uses empty `@Controller()`.** This is the health check endpoint at `/api/health`. Allowlist it.

**Global prefix:** `main.ts:31` — `app.setGlobalPrefix('api')`. The guard must NOT include `api/` in controller prefixes (that was the original bug — `@Controller('api/dashboard')` produced `/api/api/dashboard`).

**Kebab-case regex for path segments:** `/^[a-z][a-z0-9]*(-[a-z0-9]+)*(\/[a-z][a-z0-9]*(-[a-z0-9]+)*)*$/`
- Allows: `positions`, `risk/stress-test`, `backtesting/runs`, `dashboard/settings`
- Rejects: `camelCase`, `PascalCase`, `api/dashboard` (starts with `api/` — likely duplication bug)

**Implementation approach — grep-based test (mandatory, do NOT use DiscoveryService).** A test using `DiscoveryService` requires bootstrapping the full app module (DB connections, external services) and is fragile. Use `fs.readFileSync` + `globSync` to scan `src/**/*.controller.ts` files and extract `@Controller('...')` arguments via regex. This is simpler, faster, runs without infrastructure, and catches violations at test time.

**Additional check:** Verify no controller prefix starts with `api` or `api/` — catches the exact `api/api/...` bug from story 10-9-6. This is the highest-value check in the guard.

### Guard 3: Dashboard API Client — Implementation Details

**Generation command** (in `pm-arbitrage-dashboard/package.json`):
```
npx swagger-typescript-api generate -p http://127.0.0.1:8080/api/docs-json -o src/api/generated -n Api.ts --axios --sort-types --sort-routes --unwrap-response-data
```

**Process:**
1. Engine must be running locally (`pnpm start:dev`)
2. Run `pnpm generate-api` in `pm-arbitrage-dashboard/`
3. Output: `pm-arbitrage-dashboard/src/api/generated/Api.ts` (single file, `@ts-nocheck`)
4. Verify dashboard compiles: `pnpm build` in dashboard repo

**Important:** `pm-arbitrage-dashboard/` is a SEPARATE git repo. The regenerated `Api.ts` must be committed separately from the engine changes.

### Project Structure Notes

- All new files go in `src/common/config/` (typed helpers, guard tests) and `src/common/guards/` (route prefix guard test)
- Follow existing naming: `typed-config.helpers.ts`, `typed-config.helpers.spec.ts`, `typed-config.guard.spec.ts`, `env-schema-completeness.guard.spec.ts`, `route-prefix-validation.guard.spec.ts`
- No new NestJS modules, no new DI providers, no constructor injection changes
- Error hierarchy: if `getConfigNumber` throws, use `SystemHealthError` (codes 4000-4999) — configuration corruption is a system health issue

### What NOT To Do

- Do NOT migrate all ~105 configService.get calls to a new pattern — only the 11 boolean calls
- Do NOT replace `ConfigService` injection with `TypedConfigService` across the codebase — that's a larger migration (debt item #5)
- Do NOT extract ConfigModule (debt item #4) — separate story
- Do NOT add the ~15 missing env keys to env.schema.ts — only document the gap via the guard test allowlist
- Do NOT add runtime startup validation hooks — use test-time guards (faster, no infrastructure deps, caught pre-merge)
- Do NOT touch `ConfigAccessor` — it handles DB-backed config, orthogonal to this story
- Do NOT add new constructor dependencies to any existing service

### Testing Standards

- Co-located tests: `typed-config.helpers.spec.ts` next to `typed-config.helpers.ts`
- Guard tests: `typed-config.guard.spec.ts` and `env-schema-completeness.guard.spec.ts` in `src/common/config/`, `route-prefix-validation.guard.spec.ts` in `src/common/guards/`
- Assertion depth: verify actual parsed values, not just call presence
- All financial math uses `decimal.js` (not applicable to this story but don't accidentally introduce native operators if touching numeric config)

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 10.96, Story 10-96-0]
- [Source: _bmad-output/implementation-artifacts/epic-10-95-retro-2026-04-13.md — Agreements #26, #34, Debt items #1-3]
- [Source: _bmad-output/implementation-artifacts/epic-10-9-retro-2026-04-04.md — Original configService/route prefix defect identification]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-13-retro-materialization.md — Slot-zero creation]
- [Source: _bmad-output/planning-artifacts/architecture.md — Configuration management, Dashboard API patterns]
- [Source: pm-arbitrage-engine/src/common/config/env.schema.ts — Zod validation schema]
- [Source: pm-arbitrage-engine/src/common/config/env.types.ts — TypedConfigService definition]
- [Source: pm-arbitrage-engine/src/common/config/config-accessor.service.ts — DB-backed config accessor]
- [Source: pm-arbitrage-engine/src/main.ts:31 — Global prefix setGlobalPrefix('api')]
- [Source: pm-arbitrage-dashboard/package.json:13 — generate-api script]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- Baseline: 3798 unit tests pass, 2 pre-existing e2e failures (core-lifecycle DB mock issue)
- Final: 3821 unit tests pass (+23 new), same pre-existing e2e failures
- `configService.get<number>` guard uses baseline count (58) to prevent new additions without requiring immediate migration
- Dashboard type fixes: BacktestConfigDto gained 6 required fields (chunkWindowDays, depthCacheBudgetMb, exitStopLossPct, maxEdgeThresholdPct, minEntryPricePct, maxEntryPriceGapPct), several endpoints return `void` due to missing Swagger decorators — fixed with `unknown` casts
- Used recursive `fs.readdirSync` instead of `globSync` (not a direct dependency)

### Completion Notes List
- AC #1: `getConfigBoolean`/`getConfigNumber` helpers created. All 11 boolean call sites migrated. Three structural guard tests: raw type assertion ban, env schema completeness (17 allowlisted keys with TODO comments), stale allowlist detection.
- AC #2: Route prefix validation guard: 6 tests covering non-empty prefix, kebab-case, no api/ duplication, no template literals, no unexpected duplicates. All 15 controllers compliant.
- AC #3: Dashboard API client regenerated. Type fixes applied for new BacktestConfigDto fields and void-returning endpoints. Dashboard builds successfully.
- Debt items #1 (configService boolean), #2 (configService number guard), #3 (route prefix guard) resolved.

### Change Log
- 2026-04-13: Story 10-96-0 implemented. Typed config helpers, 11 boolean call site migrations, 3 structural guard test suites (config type safety, env schema completeness, route prefix validation), dashboard API client regeneration with type fixes.

### File List

**Engine (pm-arbitrage-engine/) — new files:**
- `src/common/config/typed-config.helpers.ts` — getConfigBoolean, getConfigNumber
- `src/common/config/typed-config.helpers.spec.ts` — 16 unit tests
- `src/common/config/typed-config.guard.spec.ts` — 3 structural guard tests (boolean ban, number baseline)
- `src/common/config/env-schema-completeness.guard.spec.ts` — 3 structural guard tests (schema drift, stale allowlist)
- `src/common/guards/route-prefix-validation.guard.spec.ts` — 6 structural guard tests

**Engine (pm-arbitrage-engine/) — modified files:**
- `src/modules/monitoring/csv-trade-log.service.ts` — migrated CSV_ENABLED
- `src/dashboard/dashboard-event-mapper.service.ts` — migrated AUTO_UNWIND_ENABLED
- `src/modules/contract-matching/calibration.service.ts` — migrated CALIBRATION_ENABLED
- `src/core/engine-lifecycle.service.ts` — migrated ALLOW_MIXED_MODE
- `src/modules/contract-matching/candidate-discovery.service.ts` — migrated DISCOVERY_ENABLED, DISCOVERY_RUN_ON_STARTUP
- `src/modules/contract-matching/resolution-poller.service.ts` — migrated RESOLUTION_POLLER_ENABLED
- `src/modules/contract-matching/external-pair-ingestion.service.ts` — migrated EXTERNAL_PAIR_INGESTION_ENABLED (2 sites)
- `src/modules/execution/auto-unwind.service.ts` — migrated AUTO_UNWIND_ENABLED
- `src/modules/backtesting/ingestion/incremental-ingestion.service.ts` — migrated INCREMENTAL_INGESTION_ENABLED

**Dashboard (pm-arbitrage-dashboard/) — modified files:**
- `src/api/generated/Api.ts` — regenerated API client
- `src/hooks/useBacktest.ts` — fixed status string | undefined
- `src/hooks/useBacktest.spec.ts` — added missing BacktestConfigDto fields
- `src/hooks/useDashboard.ts` — simplified storage stats API call
- `src/pages/BacktestPage.tsx` — fixed void return type cast
- `src/components/backtest/RunComparisonView.tsx` — fixed void return type casts
- `src/components/backtest/NewBacktestDialog.tsx` — added missing BacktestConfigDto fields, fixed void cast
- `src/components/backtest/BacktestPositionsTable.spec.tsx` — added missing runId and unrealizedPnl
