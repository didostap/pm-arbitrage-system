# Story 4.5.3: Shared e2e Test Environment Config

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want all e2e test files to share a single environment configuration,
so that adding a new env var requires touching one file instead of three.

## Acceptance Criteria

### AC1: Single Shared Source
**Given** environment variables are currently duplicated across `app.e2e-spec.ts`, `core-lifecycle.e2e-spec.ts`, and `logging.e2e-spec.ts`
**When** a shared test environment config is extracted
**Then** all three e2e test files import from a single shared source
**And** the duplicated `process.env` assignment blocks are removed from each file

### AC2: All e2e Tests Pass
**Given** the shared config replaces per-file env setup
**When** `pnpm test` is run
**Then** all 498 existing tests pass (including all e2e tests)

### AC3: Single-File Modification for New Env Vars
**Given** the shared config is in place
**When** a new environment variable needs to be added for e2e tests
**Then** modifying exactly one file (`test/setup.ts`) is sufficient

### AC4: Lint Clean
**Given** all changes are complete
**When** `pnpm lint` is run
**Then** zero errors are reported

## Tasks / Subtasks

- [x] Task 1: Create `test/setup.ts` with shared env config (AC: #1, #3)
  - [x] 1.1 Create `test/setup.ts` with the 5 duplicated `process.env` assignments
  - [x] 1.2 Verify `vitest.config.ts` already references `./test/setup.ts` in `setupFiles` (line 9 — already configured, no change needed)

- [x] Task 2: Remove duplicated env vars from e2e files (AC: #1)
  - [x] 2.1 Remove `process.env` block (lines 9-13) from `test/app.e2e-spec.ts`
  - [x] 2.2 Remove `process.env` block (lines 11-15) from `test/core-lifecycle.e2e-spec.ts`
  - [x] 2.3 Remove `process.env` block (lines 16-20) from `test/logging.e2e-spec.ts`
  - [x] 2.4 Remove any associated comments (e.g., `// Risk management env vars required by RiskManagerService.onModuleInit`)

- [x] Task 3: Verify all tests pass (AC: #2, #4)
  - [x] 3.1 Run `pnpm test` — all 498 tests pass
  - [x] 3.2 Run `pnpm lint` — zero errors

## Dev Notes

### The Duplication Today

All three files have this identical block at module scope:

```typescript
// Risk management env vars required by RiskManagerService.onModuleInit
process.env.RISK_BANKROLL_USD = '10000';
process.env.RISK_MAX_POSITION_PCT = '0.03';
process.env.RISK_MAX_OPEN_PAIRS = '10';
process.env.RISK_DAILY_LOSS_PCT = '0.05';
process.env.OPERATOR_API_TOKEN = 'test-token';
```

### The Fix

`vitest.config.ts` already declares `setupFiles: ['./test/setup.ts']` (line 9), but the file doesn't exist yet. Vitest `setupFiles` run before each test file — this is the idiomatic place for shared env config.

Create `test/setup.ts` containing the 5 `process.env` assignments. Then delete those same assignments from the three e2e files. That's it.

### Implementation Pattern

```typescript
// test/setup.ts
// Shared environment variables for e2e tests.
// Vitest runs this file before each test file via setupFiles in vitest.config.ts.

process.env.RISK_BANKROLL_USD = '10000';
process.env.RISK_MAX_POSITION_PCT = '0.03';
process.env.RISK_MAX_OPEN_PAIRS = '10';
process.env.RISK_DAILY_LOSS_PCT = '0.05';
process.env.OPERATOR_API_TOKEN = 'test-token';
```

### Scope Boundary — `data-ingestion.e2e-spec.ts` is OUT OF SCOPE

The 4th e2e file (`data-ingestion.e2e-spec.ts`) does NOT use `process.env` assignments at all. It uses `ConfigModule.forRoot({ envFilePath: '.env.test' })` with a targeted module slice instead of `AppModule`. Do NOT modify this file.

### Key Constraints

- **Do NOT modify `vitest.config.ts`** — it already has the correct `setupFiles` entry
- **Do NOT modify `data-ingestion.e2e-spec.ts`** — different pattern, out of scope
- **Do NOT add any new env vars** — only extract the existing 5
- **Do NOT change test logic, imports, or module bootstrap** — only remove the `process.env` lines and their comments
- **Do NOT create a utility function or class** — plain `process.env` assignments in `setup.ts` is sufficient

### Vitest `setupFiles` Behavior

`setupFiles` in Vitest execute before each test file in the same process. Since these `process.env` assignments are module-level in the current code (they run once when the file is imported), moving them to `setupFiles` has identical semantics — they'll be set before any test file executes.

**Important:** `setupFiles` runs for ALL test files (unit + e2e), not just e2e. This is fine because:
- The env vars only affect `RiskManagerService.onModuleInit` and `AuthGuard`, which are only instantiated in e2e tests that import `AppModule`
- Unit tests mock these services and never read `process.env` directly
- Setting unused env vars has zero side effects

### Pre-existing Condition

e2e tests make live HTTP calls to production APIs (Polymarket CLOB, Kalshi). These are fragile and may fail if external services are unavailable. This is a known issue — do not attempt to fix it in this story.

### Project Structure Notes

- **New file:** `pm-arbitrage-engine/test/setup.ts`
- **Modified files:**
  - `pm-arbitrage-engine/test/app.e2e-spec.ts` — remove lines 9-13 (env vars)
  - `pm-arbitrage-engine/test/core-lifecycle.e2e-spec.ts` — remove lines 11-15 (env vars)
  - `pm-arbitrage-engine/test/logging.e2e-spec.ts` — remove lines 16-20 (env vars)
- **Not modified:** `vitest.config.ts`, `data-ingestion.e2e-spec.ts`, any unit test files

### References

- [Source: pm-arbitrage-engine/vitest.config.ts:9] — `setupFiles: ['./test/setup.ts']` already configured
- [Source: pm-arbitrage-engine/test/app.e2e-spec.ts:9-13] — duplicated env vars
- [Source: pm-arbitrage-engine/test/core-lifecycle.e2e-spec.ts:11-15] — duplicated env vars
- [Source: pm-arbitrage-engine/test/logging.e2e-spec.ts:16-20] — duplicated env vars
- [Source: pm-arbitrage-engine/test/data-ingestion.e2e-spec.ts] — different pattern, out of scope
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.5.3] — Original requirements
- [Source: _bmad-output/implementation-artifacts/4-5-2-pipeline-latency-instrumentation.md] — Previous story, 498 test baseline
- [Source: CLAUDE.md#Testing] — Co-located test pattern, Vitest framework

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None needed — straightforward extraction.

### Completion Notes List

- `test/setup.ts` already existed with `import 'reflect-metadata'` — env vars appended after it
- All 498 tests pass, lint clean
- No changes to `vitest.config.ts`, `data-ingestion.e2e-spec.ts`, or any unit tests

### File List

- `pm-arbitrage-engine/test/setup.ts` — added 5 shared env var assignments
- `pm-arbitrage-engine/test/app.e2e-spec.ts` — removed duplicated env block (7 lines: comment + 5 env vars + blank line)
- `pm-arbitrage-engine/test/core-lifecycle.e2e-spec.ts` — removed duplicated env block (7 lines: comment + 5 env vars + blank line)
- `pm-arbitrage-engine/test/logging.e2e-spec.ts` — removed duplicated env block (7 lines: comment + 5 env vars + blank line)
