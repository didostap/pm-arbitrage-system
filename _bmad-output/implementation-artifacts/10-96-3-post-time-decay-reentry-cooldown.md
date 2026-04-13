# Story 10-96.3: Post-TIME_DECAY Re-Entry Cooldown

Status: done

## Story

As an operator,
I want the live engine to enforce a cooldown period after TIME_DECAY exits,
So that toxic pairs aren't immediately re-entered, preventing fee churning on persistent non-converging edges.

## Acceptance Criteria

1. **Given** `timeDecayCooldownHours` config setting (default `24`) **when** the pair concentration filter evaluates an opportunity **and** the most recent closed position for that pair exited via `time_decay` or `time_based` within the cooldown window **then** the opportunity is rejected with reason `'time_decay_cooldown_active'` and an `OpportunityFilteredEvent` is emitted.

2. **Given** a position exits with reason other than `time_decay`/`time_based` (e.g., `profit_capture`, `edge_evaporation`, `stop_loss`) **when** cooldown is checked **then** only the existing generic `pairCooldownMinutes` applies (no change to existing behavior).

3. **Given** `timeDecayCooldownHours` is set to `0` **when** cooldown is checked **then** the TIME_DECAY-specific cooldown is disabled (only generic `pairCooldownMinutes` applies).

4. **Given** any position is closed via the exit-execution pipeline **when** `positionRepository.closePosition()` is called **then** the exit type from the threshold evaluator (`evalResult.type`) is persisted in the new `exitCriterion` column on OpenPosition.

5. **Given** a position is closed via non-threshold paths (manual close, single-leg resolution, reconciliation) **when** `positionRepository.closePosition()` is called **then** `exitCriterion` is `null` (these do not trigger TIME_DECAY cooldown).

6. **Given** the new `timeDecayCooldownHours` config setting **when** the dashboard settings page is loaded **then** it appears under the `RiskManagement` group after `pairCooldownMinutes` with label, description, and `min: 0`.

7. **Given** the structural guard baseline **when** this story is complete **then** `configService.get<number>()` count remains at `58` (new config accessed via `ConfigAccessor`).

## Tasks / Subtasks

- [x] **Task 1: Add `exitCriterion` to OpenPosition + `timeDecayCooldownHours` to EngineConfig in Prisma** (AC: #4, #6)
  - [x] 1.1 `prisma/schema.prisma` — In the `OpenPosition` model, after `exitMode` (line ~406), add:
    ```prisma
    exitCriterion         String?        @map("exit_criterion") @db.VarChar(30)
    ```
    Values will be: `'time_decay'`, `'time_based'`, `'stop_loss'`, `'take_profit'`, `'edge_evaporation'`, `'model_confidence'`, `'risk_budget'`, `'liquidity_deterioration'`, `'profit_capture'`, or `null`.
  - [x] 1.2 `prisma/schema.prisma` — In the `EngineConfig` model, after `exitStopLossPct` (in the exit/risk section), add:
    ```prisma
    timeDecayCooldownHours  Int?           @map("time_decay_cooldown_hours")
    ```
  - [x] 1.3 Create Prisma migration: `pnpm prisma migrate dev --name add_exit_criterion_and_time_decay_cooldown`.
  - [x] 1.4 Run `pnpm prisma generate`.

- [x] **Task 2: Add `timeDecayCooldownHours` across the config stack** (AC: #6, #7)
  - [x] 2.1 `src/common/config/env.schema.ts` — After `PAIR_COOLDOWN_MINUTES` (line ~291), add:
    ```typescript
    TIME_DECAY_COOLDOWN_HOURS: z.coerce.number().int().min(0).default(24),
    ```
  - [x] 2.2 `src/common/config/config-defaults.ts` — After `pairCooldownMinutes` entry (line ~332), add:
    ```typescript
    timeDecayCooldownHours: {
      envKey: 'TIME_DECAY_COOLDOWN_HOURS',
      defaultValue: 24,
    },
    ```
  - [x] 2.3 `src/common/config/effective-config.types.ts` — After `pairCooldownMinutes` (line ~127), add:
    ```typescript
    timeDecayCooldownHours: number;
    ```
  - [x] 2.4 `src/common/config/settings-metadata.ts` — After `pairCooldownMinutes` entry (line ~365), add in `SettingsGroup.RiskManagement`:
    ```typescript
    timeDecayCooldownHours: {
      group: SettingsGroup.RiskManagement,
      label: 'TIME_DECAY Cooldown',
      description: 'Hours to block re-entry after a TIME_DECAY exit. 0 = disabled (generic cooldown only).',
      type: 'integer',
      envDefault: CONFIG_DEFAULTS.timeDecayCooldownHours.defaultValue,
      min: 0,
      unit: 'h',
    },
    ```
  - [x] 2.5 `src/persistence/repositories/engine-config.repository.ts` — After `pairCooldownMinutes` resolve mapping (line ~182), add:
    ```typescript
    timeDecayCooldownHours: resolve('timeDecayCooldownHours') as number,
    ```
  - [x] 2.6 `src/common/config/env.schema.spec.ts` — Add 3 tests for `TIME_DECAY_COOLDOWN_HOURS`:
    - Default value is 24
    - Accepts 0 (disabled)
    - Rejects negative value
  - [x] 2.7 `src/persistence/repositories/engine-config.repository.spec.ts` — Add assertion for new resolve mapping.
  - [x] 2.8 `src/dashboard/settings.service.spec.ts` — Update settings count from `100` to `101` (line 254).

- [x] **Task 3: Modify `positionRepository.closePosition()` to accept optional exitCriterion** (AC: #4, #5)
  - [x] 3.1 `src/persistence/repositories/position.repository.ts` — Update `closePosition()` signature (line ~76):
    ```typescript
    async closePosition(
      positionId: PositionId | string,
      realizedPnl: Decimal,
      exitCriterion?: string | null,
    ) {
    ```
    Update the `data` object:
    ```typescript
    data: {
      status: 'CLOSED',
      realizedPnl: realizedPnl.toDecimalPlaces(8),
      ...(exitCriterion != null && { exitCriterion }),
    },
    ```
  - [x] 3.2 `src/persistence/repositories/position.repository.spec.ts` — Update existing `closePosition` tests to verify the 2-arg call still works (backward compatible). Add 2 new tests:
    - `should persist exitCriterion when provided` — call with `'time_decay'`, verify `data.exitCriterion` in update call.
    - `should not include exitCriterion when omitted` — call with 2 args, verify `data` does NOT contain `exitCriterion`.

- [x] **Task 4: Pass exit type to `closePosition()` at all call sites** (AC: #4, #5)
  - [x] 4.1 `src/modules/exit-management/exit-execution.service.ts` (line ~640) — Pass exit type from the evaluation result. The `closePosition` call currently receives `(position.positionId, accumulatedPnl)`. Add a 3rd arg for the exit criterion. **Check what's in scope at the call site**: the exit type may be available as a local variable (e.g., `exitType`) or via `evalResult.type`. Search for how the `ExitTriggeredEvent` constructor (later in the method, line ~693) gets its `exitType` argument — use the same source. Pass `exitType ?? null` (or `evalResult.type ?? null`) to handle the case where `type` is `undefined` (optional field on `ThresholdEvalResult`), mapping it to `null` for the DB column.
  - [x] 4.2 `src/modules/execution/single-leg-resolution.service.ts` (line ~437) — Leave as 2-arg call (no exitCriterion for single-leg resolution, which is an emergency close).
  - [x] 4.3 `src/modules/execution/position-close.service.ts` (lines ~155, ~508) — Leave as 2-arg calls (manual/IPositionCloseService closes have no threshold evaluation).
  - [x] 4.4 `src/modules/exit-management/exit-execution.service.spec.ts` — Update existing `closePosition` call assertions to verify `exitType` is passed as 3rd arg. Use `expect.objectContaining` pattern.
  - [x] 4.5 Verify `single-leg-resolution.service.spec.ts` and `position-close.service.spec.ts` assertions still pass with 2-arg calls (no changes needed — backward compatible).

- [x] **Task 5: Add new repository query for latest TIME_DECAY exits** (AC: #1, #2)
  - [x] 5.1 `src/persistence/repositories/position.repository.ts` — Add new method after `getLatestPositionDateByPairIds()` (line ~308):
    ```typescript
    /**
     * Batch-fetch latest TIME_DECAY/time_based exit timestamp per pair, mode-scoped.
     * Returns Map<pairId, Date> where Date is updatedAt (close time) of the most recent
     * closed position with exit_criterion IN ('time_decay', 'time_based').
     * Pairs with no such exits are absent from the map.
     */
    async getLatestTimeDecayExitByPairIds(
      pairIds: string[],
      isPaper: boolean,
    ): Promise<Map<string, Date>> {
      if (pairIds.length === 0) return new Map();
      const rows = await this.prisma.$queryRaw<
        { pair_id: string; latest_exit: Date }[]
      >`
        SELECT pair_id, MAX(updated_at) AS latest_exit
        FROM open_positions
        WHERE pair_id IN (${Prisma.join(pairIds)})
          AND status = 'CLOSED'
          AND exit_criterion IN ('time_decay', 'time_based')
          AND is_paper = ${isPaper}
        GROUP BY pair_id -- MODE-FILTERED
      `;
      const map = new Map<string, Date>();
      for (const row of rows) {
        map.set(row.pair_id, row.latest_exit);
      }
      return map;
    }
    ```
  - [x] 5.2 `src/persistence/repositories/position.repository.spec.ts` — Add test for `getLatestTimeDecayExitByPairIds`:
    - Returns Map with correct pair→date for time_decay exits
    - Excludes non-time_decay exits (profit_capture, stop_loss)
    - Returns empty map when no TIME_DECAY exits exist
    - Filters by isPaper

- [x] **Task 6: Extend pair-concentration-filter with TIME_DECAY cooldown check** (AC: #1, #2, #3)
  - [x] 6.1 `src/modules/arbitrage-detection/pair-concentration-filter.service.ts` — In `filterOpportunities()`:
    - After line 39 (after `const diversityThreshold = config.pairDiversityThreshold;`), load new config value alongside the other config extractions:
      ```typescript
      const timeDecayCooldownHours = config.timeDecayCooldownHours;
      ```
    - In the `Promise.all` block (lines 55-61), add a 3rd parallel query:
      ```typescript
      [latestDates, openCounts, timeDecayExits] = await Promise.all([
        this.positionRepository.getLatestPositionDateByPairIds(pairIds, isPaper),
        this.positionRepository.getActivePositionCountsByPair(isPaper),
        timeDecayCooldownHours > 0
          ? this.positionRepository.getLatestTimeDecayExitByPairIds(pairIds, isPaper)
          : Promise.resolve(new Map<string, Date>()),
      ]);
      ```
    - After the existing cooldown check (line 112, after `}`), add:
      ```typescript
      // 1b. TIME_DECAY-specific cooldown check
      if (!reason && timeDecayCooldownHours > 0) {
        const lastTimeDecayExit = timeDecayExits.get(pairId);
        if (lastTimeDecayExit && now - lastTimeDecayExit.getTime() < timeDecayCooldownHours * 3_600_000) {
          reason = 'time_decay_cooldown_active';
        }
      }
      ```
    - In `emitFilteredEvent()`, add the new reason to the config value mapping:
      ```typescript
      const configValue =
        reason === 'pair_cooldown_active'
          ? cooldownMinutes
          : reason === 'time_decay_cooldown_active'
            ? timeDecayCooldownHours
            : reason === 'pair_max_concurrent_reached'
              ? maxConcurrent
              : diversityThreshold;
      ```
    - Pass `timeDecayCooldownHours` to `emitFilteredEvent()` (add parameter).
  - [x] 6.2 `src/modules/arbitrage-detection/pair-concentration-filter.service.spec.ts` — Add `describe('TIME_DECAY cooldown')` block with tests:
    - `should block re-entry within TIME_DECAY cooldown period` — mock `getLatestTimeDecayExitByPairIds` to return recent date, verify opportunity is filtered with reason `'time_decay_cooldown_active'`.
    - `should allow re-entry after TIME_DECAY cooldown expires` — mock exit date older than 24h, verify opportunity passes.
    - `should NOT apply TIME_DECAY cooldown for non-time_decay exits` — mock `getLatestTimeDecayExitByPairIds` returning empty map (no time_decay exits), verify opportunity passes (only generic cooldown applies).
    - `should disable TIME_DECAY cooldown when timeDecayCooldownHours=0` — set config to 0, verify `getLatestTimeDecayExitByPairIds` is NOT called, opportunity passes.
    - `should emit OpportunityFilteredEvent with correct reason and threshold` — verify event emitted with reason `'time_decay_cooldown_active'` and threshold = 24.
    - `should apply TIME_DECAY cooldown independently from generic cooldown` — mock both cooldowns: generic cooldown expired but TIME_DECAY active → filtered.
    - `should handle concurrent generic + TIME_DECAY cooldown (TIME_DECAY wins)` — mock both active, verify TIME_DECAY reason takes priority (generic check runs first but either blocking is correct).
  - [x] 6.3 Verify existing tests still pass — new `getLatestTimeDecayExitByPairIds` mock must return empty map by default in existing test setup.

- [x] **Task 7: Verify structural guards and run full test suite** (AC: #7)
  - [x] 7.1 `typed-config.guard.spec.ts` — `configService.get<number>()` baseline remains 58. No new `configService.get<number>()` calls added (uses ConfigAccessor).
  - [x] 7.2 `typed-config.guard.spec.ts` — env schema completeness guard passes with 1 new key.
  - [x] 7.3 Regenerate dashboard API client via `swagger-typescript-api`.
  - [x] 7.4 Run `pnpm lint` — fix any issues.
  - [x] 7.5 Run `pnpm test` — verify baseline + new tests pass.

## Dev Notes

### Design Decision: DB-Mediated Exit Reason Flow (NOT Interface Extension)

The sprint change proposal mentions extending `pair-concentration-filter.interface.ts` to accept exit reason context from the exit monitor. **This story deliberately does NOT do that** because:

1. **Module dependency rules forbid** `exit-management/` → `arbitrage-detection/` imports. The pair-concentration-filter is in `modules/arbitrage-detection/`, and the exit monitor is in `modules/exit-management/`.
2. **DB-mediated approach is cleaner**: the exit pipeline persists `exitCriterion` on `OpenPosition`, and the detection pipeline reads it via a new repository query. No cross-module coupling.
3. **Restart-safe**: persisted data survives process restarts, unlike in-memory signaling.
4. **The `IPairConcentrationFilter` interface does NOT change** — its signature `filterOpportunities(opportunities, isPaper)` remains unchanged. The filter internally queries for TIME_DECAY exit data.

### Why Both `time_decay` AND `time_based` Trigger Cooldown

The live threshold evaluator returns different exit types depending on mode:

- **Fixed mode** (`exitMode: 'fixed'`): time-limit exits return `type: 'time_based'`
- **Model/shadow mode** (`exitMode: 'model'|'shadow'`): criterion C3 returns `type: 'time_decay'`

Both mean "held too long, edge didn't converge." The cooldown query checks for BOTH: `exit_criterion IN ('time_decay', 'time_based')`. This ensures the cooldown works regardless of exit mode configuration.

### Implementation Site: `pair-concentration-filter.service.ts`

The cooldown check goes here (not in `edge-calculator.service.ts` or `detection.service.ts`) because:

- It's a **re-entry risk filter**, not an edge/signal filter
- It uses the same DB queries and config patterns as the existing `pairCooldownMinutes` check
- The service already has `PositionRepository` injected (3 constructor deps, under the <=5 threshold for leaf services; adding no new deps)

### Config Pattern (5 Files, Not 7)

Unlike the Decimal config fields from 10-96-2 (which touch 7 files), `timeDecayCooldownHours` is a plain integer:

| File                                                       | Type                                         | Notes                                       |
| ---------------------------------------------------------- | -------------------------------------------- | ------------------------------------------- |
| `src/common/config/env.schema.ts`                          | `z.coerce.number().int().min(0).default(24)` | Integer, not Decimal.                       |
| `src/common/config/config-defaults.ts`                     | `ConfigDefaultEntry`                         | `defaultValue: 24` (number).                |
| `src/common/config/effective-config.types.ts`              | `number` field                               | Plain number.                               |
| `src/common/config/settings-metadata.ts`                   | `SettingsMetadataEntry`                      | Group: `RiskManagement`. Type: `'integer'`. |
| `src/persistence/repositories/engine-config.repository.ts` | `resolve() as number`                        | Same cast as `pairCooldownMinutes`.         |

**Not needed:** `prisma/seed-config.ts` — integers are handled implicitly by the seed logic (no DECIMAL_FIELDS or FLOAT_FIELDS entry needed). The Prisma `Int?` column is auto-detected.

### Position Repository Changes

**`closePosition()` — backward-compatible 3rd parameter:**

```typescript
async closePosition(positionId, realizedPnl, exitCriterion?)
```

Existing 2-arg callers (single-leg-resolution, position-close) continue to work unchanged. Only exit-execution passes the 3rd arg.

**New query — `getLatestTimeDecayExitByPairIds()`:**

- Uses `MAX(updated_at)` as the close time (`@updatedAt` is auto-set by Prisma on any update)
- Filters: `status = 'CLOSED'`, `exit_criterion IN ('time_decay', 'time_based')`, `is_paper = ?`
- Returns `Map<pairId, Date>` (same pattern as existing `getLatestPositionDateByPairIds`)
- Pairs with no TIME_DECAY exits are absent from the map (no cooldown applies)
- `-- MODE-FILTERED` comment on raw SQL (required per CLAUDE.md)

### Cooldown Interaction Model

The generic cooldown and TIME_DECAY cooldown are **independent checks**:

| Check               | Measures From                                       | Duration                       | Config   |
| ------------------- | --------------------------------------------------- | ------------------------------ | -------- |
| Generic cooldown    | `MAX(created_at)` of ANY position                   | `pairCooldownMinutes` (30 min) | Existing |
| TIME_DECAY cooldown | `MAX(updated_at)` of CLOSED + time_decay/time_based | `timeDecayCooldownHours` (24h) | **New**  |

Both run in sequence. Either can block. TIME_DECAY cooldown is the binding constraint (24h >> 30min).

### Structural Guard Preservation

- **`configService.get<number>()` baseline: 58.** No new `configService.get<number>()` calls. Pair-concentration-filter reads config via `ConfigAccessor.get()` which returns the full effective config object.
- **Settings count: 100 → 101.** Update `settings.service.spec.ts` count.
- **Env schema completeness guard:** Adding entry to both `CONFIG_DEFAULTS` and `env.schema.ts` keeps the guard passing.

### Backtest Reference (what we're porting)

**From 10-95-12** (`backtest-engine.service.ts:440,609-611,647-661`):

- Cooldown map: `Map<string, Date>` local to `runSimulationLoop()`
- Records: `cooldownMap.set(position.pairId, step.timestamp)` on TIME_DECAY exits only
- Checks: `cooldownHours > 0 → map lookup → elapsed hours < cooldownHours → skip`
- Default: `config.cooldownHours ?? config.exitTimeLimitHours` (72h in backtest)

**Live adaptation differences:**

- Backtest uses in-memory map (scoped to simulation run) → Live uses DB column (persists across restarts)
- Backtest checks `reason === 'TIME_DECAY'` only → Live checks both `'time_decay'` and `'time_based'` (fixed vs model mode)
- Backtest default 72h → Live default 24h (per sprint change proposal)
- Backtest tracks in simulation loop → Live tracks in pair-concentration-filter (detection pipeline)

### Filter Reason String

New: `'time_decay_cooldown_active'`

Joins existing reasons in pair-concentration-filter:

- `'pair_cooldown_active'` — generic cooldown
- `'pair_max_concurrent_reached'` — max concurrent positions per pair
- `'pair_above_average_concentration'` — diversity enforcement

### Call Sites for `positionRepository.closePosition()`

| Call Site                                     | File                                    | Exit Criterion                                                                |
| --------------------------------------------- | --------------------------------------- | ----------------------------------------------------------------------------- |
| Exit-execution pipeline (threshold evaluator) | `exit-execution.service.ts:640`         | `evalResult.type` (e.g., `'time_decay'`, `'stop_loss'`)                       |
| Single-leg resolution                         | `single-leg-resolution.service.ts:437`  | `null` (emergency close, no threshold eval)                                   |
| Manual/IPositionCloseService                  | `position-close.service.ts:155,508`     | `null` (operator-initiated, no threshold eval)                                |
| Startup reconciliation                        | `startup-reconciliation.service.ts:524` | Not via `positionRepository.closePosition` (uses `riskManager.closePosition`) |

Only the exit-execution pipeline has a meaningful exit criterion from the threshold evaluator. All other paths leave `exitCriterion` as null, which correctly does NOT trigger TIME_DECAY cooldown.

### What NOT To Do

- Do NOT modify `IPairConcentrationFilter` interface — the filter reads exit data from DB, not via method parameters.
- Do NOT use `configService.get<number>()` — use `ConfigAccessor.get()` (already used by the service). Structural guard baseline must stay at 58.
- Do NOT add Decimal fields — `timeDecayCooldownHours` is a plain integer, not financial math.
- Do NOT modify `edge-calculator.service.ts`, `detection.service.ts`, or `trading-engine.service.ts`.
- Do NOT change the `return;` on line 65 of `trading-engine.service.ts` — live engine stays disabled until Epic 10.96 is complete.
- Do NOT change defaults for existing config values (that's story 10-96-4).
- Do NOT add `timeDecayCooldownHours` to `DECIMAL_FIELDS` or `FLOAT_FIELDS` in seed-config.ts — it's an integer, handled implicitly.
- Do NOT use `getConfigNumber()` — pair-concentration-filter uses `ConfigAccessor` pattern, not direct `configService` calls.

### Previous Story Intelligence

**From 10-96-2 (max edge cap / entry filters):**

- Config stack pattern: 7 files per Decimal field, 5 files per integer field. Follow the integer pattern here.
- Settings count was 97→100. Now 100→101.
- TDD cycle: Write failing test first, implement, refactor. Assertion depth: verify exact values with `expect.objectContaining()`.
- `reloadDecimalFilter()` pattern not needed here — `ConfigAccessor.get()` is already hot-reload compatible.

**From 10-96-1a (startup/websocket fixes):**

- Prisma schema alignment is CRITICAL: every config field must appear in ALL required config stack files. Story 10-96-1 missed 4 files and required a hotfix. Use the checklist in Task 2.

**From 10-96-0 (structural guards):**

- Structural guard `configService.get<number>()` baseline = 58. Do NOT add calls.
- Env schema completeness guard: adding to both `CONFIG_DEFAULTS` and `env.schema.ts` keeps it passing.

### File Size Impact

- `pair-concentration-filter.service.ts`: 190 lines → ~215 lines (well under 600 review trigger)
- `position.repository.ts`: ~340 lines → ~370 lines (well under 600 review trigger)
- No service exceeds constructor dep limits (pair-concentration-filter: 3 deps, no change)

### Project Structure Notes

All new code goes in existing files — no new files, modules, or services needed:

- Config: 5 existing config stack files
- Schema: `prisma/schema.prisma` (2 column additions)
- Migration: `prisma/migrations/<timestamp>/migration.sql` (auto-generated)
- Repository: `src/persistence/repositories/position.repository.ts`
- Filter: `src/modules/arbitrage-detection/pair-concentration-filter.service.ts`
- Exit persistence: `src/modules/exit-management/exit-execution.service.ts`

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 10.96, Story 10-96-3]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-13-live-engine-alignment.md — Section 4, Story 10-96-3]
- [Source: _bmad-output/implementation-artifacts/10-95-12-backtest-pair-reentry-cooldown.md — Backtest implementation being ported]
- [Source: _bmad-output/implementation-artifacts/10-96-2-max-edge-cap-and-entry-liquidity-filters.md — Config stack pattern, previous story intelligence]
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/pair-concentration-filter.service.ts — Current filter implementation]
- [Source: pm-arbitrage-engine/src/persistence/repositories/position.repository.ts:76-88 — closePosition() to modify]
- [Source: pm-arbitrage-engine/src/persistence/repositories/position.repository.ts:289-308 — getLatestPositionDateByPairIds() query pattern]
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-execution.service.ts:639-643 — closePosition call site]
- [Source: pm-arbitrage-engine/src/common/types/exit-criteria.types.ts:9-15 — ExitCriterion type (live)]
- [Source: pm-arbitrage-engine/src/common/events/execution.events.ts:94-122 — ExitTriggeredEvent.exitType values]
- [Source: pm-arbitrage-engine/src/common/interfaces/pair-concentration-filter.interface.ts — Interface (unchanged)]
- [Source: pm-arbitrage-engine/src/common/config/config-defaults.ts:329-332 — pairCooldownMinutes pattern]
- [Source: pm-arbitrage-engine/src/common/config/env.schema.ts:291 — PAIR_COOLDOWN_MINUTES pattern]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None.

### Completion Notes List

- All 7 tasks completed via strict TDD (Red-Green-Refactor).
- 17 new tests added across 7 spec files. Baseline 3882 → 3899 unit tests pass.
- Pre-existing failures: TimescaleDB integration tests (DB-dependent, unrelated).
- Code review (Lad MCP): 1 false positive (SETTINGS_METADATA verified present), 1 minor (added SQL comment for `time_based` legacy), 1 deferred (cooldown priority attribution — tested, correct per AC).
- Dashboard API client regenerated via `swagger-typescript-api` — `timeDecayCooldownHours` confirmed in `UpdateSettingsDto`.
- `UpdateSettingsDto` updated with `timeDecayCooldownHours` field for API validation.
- Structural guards: `configService.get<number>()` baseline 58 (no new calls), env schema completeness passes, settings count 100→101.

### File List

**Schema & Migration:**

- `prisma/schema.prisma` — Added `exitCriterion` to OpenPosition, `timeDecayCooldownHours` to EngineConfig
- `prisma/migrations/20260413233636_add_exit_criterion_and_time_decay_cooldown/migration.sql` — Auto-generated

**Config Stack (5 files):**

- `src/common/config/env.schema.ts` — `TIME_DECAY_COOLDOWN_HOURS` Zod schema
- `src/common/config/config-defaults.ts` — `timeDecayCooldownHours` default entry
- `src/common/config/effective-config.types.ts` — `timeDecayCooldownHours: number` type
- `src/common/config/settings-metadata.ts` — Dashboard metadata under RiskManagement
- `src/persistence/repositories/engine-config.repository.ts` — resolve mapping

**Repository:**

- `src/persistence/repositories/position.repository.ts` — `closePosition()` 3rd param, `getLatestTimeDecayExitByPairIds()` new method

**Filter:**

- `src/modules/arbitrage-detection/pair-concentration-filter.service.ts` — TIME_DECAY cooldown check

**Exit Persistence:**

- `src/modules/exit-management/exit-execution.service.ts` — Pass `evalResult.type` to `closePosition()`

**Dashboard DTO:**

- `src/dashboard/dto/update-settings.dto.ts` — `timeDecayCooldownHours` validation

**Dashboard API Client:**

- `pm-arbitrage-dashboard/src/api/generated/Api.ts` — Regenerated

**Test Files (updated assertions or new tests):**

- `src/common/config/env.schema.spec.ts` — +3 tests
- `src/persistence/repositories/engine-config.repository.spec.ts` — +2 assertions + mock data
- `src/dashboard/settings.service.spec.ts` — Count 100→101
- `src/persistence/repositories/position.repository.spec.ts` — +7 tests (closePosition exitCriterion + getLatestTimeDecayExitByPairIds)
- `src/modules/arbitrage-detection/pair-concentration-filter.service.spec.ts` — +7 tests (TIME_DECAY cooldown block)
- `src/modules/exit-management/exit-execution-pnl-persistence.spec.ts` — Updated closePosition assertions
- `src/modules/exit-management/exit-execution-partial-reevaluation.spec.ts` — Updated closePosition assertion
- `src/modules/exit-management/exit-execution-partial-fills.spec.ts` — Updated closePosition assertion
- `src/modules/exit-management/exit-monitor-core.spec.ts` — Updated closePosition assertion
- `src/modules/exit-management/exit-monitor-data-source.spec.ts` — Updated closePosition assertion
- `src/common/testing/paper-live-boundary/exit-management/pnl-persistence.spec.ts` — Updated closePosition assertion
