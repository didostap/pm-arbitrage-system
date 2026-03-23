# Story 10-7.9: Trading Window Analysis & Time-of-Day Filtering

Status: done

## Story

As an operator,
I want the system to optionally restrict trading to configurable UTC hours with adequate liquidity,
So that trades are only placed when order books can support them, informed by hourly performance analysis.

## Context

90% of 202 paper positions opened 15:00–21:00 UTC. The epic context (course correction 2026-03-23) flags that positions are entered against thin books at off-peak hours. This is an investigation-first story: Phase 1 analyzes existing position data by UTC hour to document where liquidity, fill success, and single-leg exposure concentrate; Phase 2 adds configurable trading windows that skip detection/execution during operator-specified off-hours while leaving exit monitoring unaffected.

**Dependencies:** Independent — no hard dependencies on other 10-7 stories. Builds on existing config pipeline (established in 10-7-1 through 10-7-8).

## Acceptance Criteria

1. **AC-1: Hourly analysis findings.** Given existing position data, when investigation queries are executed, then the dev notes document: (a) position count per UTC hour, (b) average expected edge per UTC hour, (c) average realized PnL per UTC hour, (d) single-leg exposure event count per UTC hour. Queries use `$queryRaw` against `open_positions` and `audit_logs` tables with `EXTRACT(HOUR FROM created_at AT TIME ZONE 'UTC')` grouping.

2. **AC-2: Configurable UTC trading windows.** `TRADING_WINDOW_START_UTC` (integer, default: 0) and `TRADING_WINDOW_END_UTC` (integer, default: 24) are registered through the full config pipeline (env.schema → config-defaults → settings-metadata → effective-config → Prisma → repository → DTO → settings.service) and appear in the dashboard Settings page under "Trading Engine" group. Hot-reload via `CONFIG_SETTINGS_UPDATED` event.

3. **AC-3: Cycle-level gate.** When the current UTC hour falls outside the configured trading window, the `SchedulerService.handlePollingCycle()` skips calling `executeCycle()` entirely. A log entry at `log` level is emitted: `"Skipping trading cycle — outside configured trading window"` with `currentHour`, `windowStart`, `windowEnd` in the data payload. No detection, risk validation, or execution occurs.

4. **AC-4: Exit monitoring unaffected.** Open positions continue to be monitored and can trigger exits regardless of whether the current time is inside or outside the trading window. The `ExitMonitorService` cron runs independently of the trading engine polling cycle.

5. **AC-5: Midnight-spanning windows.** When `start > end` (e.g., 22/6), the window spans midnight: hours ≥ start OR hours < end are inside the window. When `start < end` (e.g., 14/21), the window is normal: hours ≥ start AND hours < end are inside. Default `0/24` means always active (no restriction).

6. **AC-6: Startup validation.** `SchedulerService.onModuleInit()` (or a separate `validateTradingWindow()` call) validates: `tradingWindowStartUtc` is integer 0–23, `tradingWindowEndUtc` is integer 1–24, `start !== end` (zero-length window disallowed). Invalid values throw `ConfigValidationError`.

7. **AC-7: Backward compatibility.** Given configuration where `TRADING_WINDOW_START_UTC=0` and `TRADING_WINDOW_END_UTC=24` (defaults), then every cycle proceeds — behavior is identical to pre-story.

## Tasks / Subtasks

### Phase 1: Investigation

- [x] Task 1: Hourly performance analysis (AC: #1)
  - [x] 1.1 Write `$queryRaw` query: position count + avg expected_edge + avg realized_pnl grouped by UTC hour from `open_positions` (filter `is_paper = true`)
  - [x] 1.2 Write `$queryRaw` query: single-leg exposure event count grouped by UTC hour from `audit_logs` where `event_type = 'execution.single_leg.exposure'`
  - [x] 1.3 Execute both queries against the dev database (use a temporary test or script)
  - [x] 1.4 Document findings in Dev Agent Record section — include the UTC hour distribution and any clear liquidity/performance patterns

### Phase 2: Config Pipeline

- [x] Task 2: Config pipeline — add 2 new settings (AC: #2, #6)
  - [x] 2.1 `env.schema.ts` — add `TRADING_WINDOW_START_UTC: z.coerce.number().int().min(0).max(23).default(0)` and `TRADING_WINDOW_END_UTC: z.coerce.number().int().min(1).max(24).default(24)` in the Trading Engine section
  - [x] 2.2 `config-defaults.ts` — add `tradingWindowStartUtc: { envKey: 'TRADING_WINDOW_START_UTC', defaultValue: 0 }` and `tradingWindowEndUtc: { envKey: 'TRADING_WINDOW_END_UTC', defaultValue: 24 }` under Trading Engine section
  - [x] 2.3 `settings-metadata.ts` — add both to `SettingsGroup.TradingEngine` with label, description, type: 'integer'. `tradingWindowStartUtc` min: 0, max: 23. `tradingWindowEndUtc` min: 1, max: 24
  - [x] 2.4 `effective-config.types.ts` — add `tradingWindowStartUtc: number` and `tradingWindowEndUtc: number` under Trading Engine section
  - [x] 2.5 `prisma/schema.prisma` — add `tradingWindowStartUtc Int? @map("trading_window_start_utc")` and `tradingWindowEndUtc Int? @map("trading_window_end_utc")` to EngineConfig model
  - [x] 2.6 Run `pnpm prisma migrate dev --name add-trading-window-settings`
  - [x] 2.7 `engine-config.repository.ts` — add both fields to the `resolve()` chain in `getEffectiveConfig()`
  - [x] 2.8 `update-settings.dto.ts` — add both as optional `@IsOptional() @IsInt() @Min(0) @Max(23)` / `@Min(1) @Max(24)` fields
  - [x] 2.9 Update settings count tests: `config-defaults.spec.ts` 78 → 80, `settings.service.spec.ts` 80 → 82

### Phase 3: Trading Window Gate

- [x] Task 3: SchedulerService — trading window logic (AC: #3, #5, #6, #7)
  - [x] 3.1 Add private instance fields: `tradingWindowStartUtc: number = 0` and `tradingWindowEndUtc: number = 24`
  - [x] 3.2 In `onModuleInit()`, read from `configService.get<number>('TRADING_WINDOW_START_UTC', 0)` and `configService.get<number>('TRADING_WINDOW_END_UTC', 24)`. Validate with `validateTradingWindow()`
  - [x] 3.3 Add private `validateTradingWindow()` method: checks integer range (start: 0–23, end: 1–24), `start !== end`. Throws `ConfigValidationError` on invalid
  - [x] 3.4 Add private `isWithinTradingWindow(): boolean` method implementing the logic from AC-5:
    - `start === 0 && end === 24` → always true
    - `start < end` → `currentHour >= start && currentHour < end`
    - `start > end` → `currentHour >= start || currentHour < end`
  - [x] 3.5 In `handlePollingCycle()`, add window check before the `isCycleInProgress()` check. If `!isWithinTradingWindow()`, log at `log` level with `{ message: 'Skipping trading cycle — outside configured trading window', data: { currentHour, windowStart, windowEnd } }` and return
  - [x] 3.6 Add `reloadTradingWindow(cfg: { tradingWindowStartUtc?: number; tradingWindowEndUtc?: number })` method: validate, update instance fields, log change

- [x] Task 4: Hot-reload wiring (AC: #2)
  - [x] 4.1 `settings.service.ts` — add `tradingWindowStartUtc: ['trading-window']` and `tradingWindowEndUtc: ['trading-window']` to `SERVICE_RELOAD_MAP`
  - [x] 4.2 `settings.service.ts` — add `'trading-window'` handler: `this.tryRegisterHandler('trading-window', SchedulerService, (svc, cfg) => svc.reloadTradingWindow({ tradingWindowStartUtc: cfg.tradingWindowStartUtc, tradingWindowEndUtc: cfg.tradingWindowEndUtc }))`

### Phase 4: Tests

- [x] Task 5: Tests (AC: #1–7)
  - [x] 5.1 `isWithinTradingWindow()` — normal window (14/21): hour 15 → true, hour 10 → false, hour 21 → false (end exclusive), hour 14 → true (start inclusive)
  - [x] 5.2 `isWithinTradingWindow()` — midnight-spanning (22/6): hour 23 → true, hour 3 → true, hour 10 → false, hour 22 → true (start inclusive), hour 6 → false (end exclusive)
  - [x] 5.3 `isWithinTradingWindow()` — default (0/24): any hour → true
  - [x] 5.4 `handlePollingCycle()` — outside window: `executeCycle()` NOT called, log emitted
  - [x] 5.5 `handlePollingCycle()` — inside window: `executeCycle()` called normally
  - [x] 5.6 `handlePollingCycle()` — default window (0/24): `executeCycle()` always called
  - [x] 5.7 Config validation: start = 24 → ConfigValidationError
  - [x] 5.8 Config validation: end = 0 → ConfigValidationError
  - [x] 5.9 Config validation: start === end → ConfigValidationError
  - [x] 5.10 Hot-reload: `reloadTradingWindow()` updates window values and validates
  - [x] 5.11 Hot-reload: invalid values log warning, current values preserved (follows EdgeCalculatorService pattern)
  - [x] 5.12 Settings count: config-defaults.spec.ts 78→80
  - [x] 5.13 Settings count: settings.service.spec.ts 80→82
  - [x] 5.14 Paper/live mode boundary: trading window applies identically in both modes (no mode-dependent branching added)

## Dev Notes

### Architecture — Why Cycle-Level Gate in SchedulerService

The trading window gate lives in `SchedulerService.handlePollingCycle()` — NOT in `TradingEngineService.executeCycle()`. Rationale:

1. **Separation of concerns:** The scheduler owns time-based policy (WHEN to run cycles); the engine owns business logic (HOW to run cycles). Trading windows are a time-based policy.
2. **Dependency count:** `TradingEngineService` already has 9 constructor dependencies (approaching the 10-dependency God Object threshold from CLAUDE.md). `SchedulerService` has 4 dependencies and already injects `ConfigService`.
3. **Exit monitoring is unaffected:** `ExitMonitorService` runs on its own `@Cron` schedule, completely independent of `SchedulerService.handlePollingCycle()`. No changes needed for AC-4.

### Insertion Point in SchedulerService

The window check goes at the top of `handlePollingCycle()` (line 99), before the `isCycleInProgress()` check:

```
Current flow:
  handlePollingCycle() → isCycleInProgress? → executeCycle()

New flow:
  handlePollingCycle() → [TRADING WINDOW CHECK] → isCycleInProgress? → executeCycle()
```

### `isWithinTradingWindow()` Logic

```typescript
private isWithinTradingWindow(): boolean {
  if (this.tradingWindowStartUtc === 0 && this.tradingWindowEndUtc === 24) {
    return true; // Default: always active
  }
  const currentHour = new Date().getUTCHours();
  if (this.tradingWindowStartUtc < this.tradingWindowEndUtc) {
    // Normal window (e.g., 14-21)
    return currentHour >= this.tradingWindowStartUtc && currentHour < this.tradingWindowEndUtc;
  }
  // Midnight-spanning window (e.g., 22-6)
  return currentHour >= this.tradingWindowStartUtc || currentHour < this.tradingWindowEndUtc;
}
```

Start hour is inclusive, end hour is exclusive (standard interval convention).

### Config Pipeline Pattern

Follow the exact pattern from `pollingIntervalMs` (already in Trading Engine group). The pipeline is:

1. `env.schema.ts` — Zod validation with `z.coerce.number().int()`
2. `config-defaults.ts` — `{ envKey, defaultValue }` entry
3. `settings-metadata.ts` — `{ group: SettingsGroup.TradingEngine, label, description, type: 'integer', envDefault }` entry
4. `effective-config.types.ts` — typed field (`number`)
5. `prisma/schema.prisma` — nullable Int column on EngineConfig
6. Prisma migration
7. `engine-config.repository.ts` — `resolve()` in `getEffectiveConfig()`
8. `update-settings.dto.ts` — DTO with `@IsOptional() @IsInt() @Min() @Max()`
9. `settings.service.ts` — SERVICE_RELOAD_MAP + handler

### Hot-Reload Pattern

settings.service.ts already imports `SchedulerService` (line 33) for the `'polling-interval'` handler. The new `'trading-window'` handler reuses the same reference:

```typescript
// In SERVICE_RELOAD_MAP:
tradingWindowStartUtc: ['trading-window'],
tradingWindowEndUtc: ['trading-window'],

// In registerAllHandlers():
this.tryRegisterHandler('trading-window', SchedulerService, (svc, cfg) =>
  svc.reloadTradingWindow({
    tradingWindowStartUtc: cfg.tradingWindowStartUtc,
    tradingWindowEndUtc: cfg.tradingWindowEndUtc,
  }),
);
```

### Reload Validation Strategy

Check the existing `EdgeCalculatorService.reloadConfig()` pattern for how to handle invalid hot-reload values: it logs a warning and preserves current values (does NOT throw). Follow the same pattern in `reloadTradingWindow()` — warn and preserve on invalid, update on valid. Startup validation in `onModuleInit()` CAN throw `ConfigValidationError` since env var values should always be valid.

### Investigation Queries (Phase 1)

The dev agent should run these against the dev database (PostgreSQL on port 5433):

**Position distribution by UTC hour:**

```sql
SELECT EXTRACT(HOUR FROM created_at AT TIME ZONE 'UTC')::int AS hour,
       COUNT(*) AS position_count,
       AVG(expected_edge::numeric) AS avg_expected_edge,
       AVG(realized_pnl::numeric) AS avg_realized_pnl
FROM open_positions
WHERE is_paper = true
GROUP BY hour ORDER BY hour;
```

**Single-leg events by UTC hour:**

```sql
SELECT EXTRACT(HOUR FROM created_at AT TIME ZONE 'UTC')::int AS hour,
       COUNT(*) AS single_leg_events
FROM audit_logs
WHERE event_type = 'execution.single_leg.exposure'
GROUP BY hour ORDER BY hour;
```

These are one-time analysis queries — run them, document findings in the Dev Agent Record, then proceed with implementation. Do NOT create permanent endpoints or services for this analysis.

### Testing Patterns

- Framework: **Vitest** (not Jest)
- Co-located: `scheduler.service.spec.ts` in `src/core/`
- To test `isWithinTradingWindow()` with controlled time, use `vi.useFakeTimers()` + `vi.setSystemTime(new Date('2026-03-24T15:00:00Z'))` to control `Date.getUTCHours()` return value
- Use `describe.each` for the hour matrix tests to reduce boilerplate
- Mock `tradingEngine.executeCycle()` and `tradingEngine.isCycleInProgress()` for cycle gate tests
- For config validation tests, construct service with invalid config values and expect `ConfigValidationError` in `onModuleInit()`

### Files to Modify

| #   | File                                                       | Change                                                                      |
| --- | ---------------------------------------------------------- | --------------------------------------------------------------------------- |
| 1   | `src/common/config/env.schema.ts`                          | +2 env var definitions (integers)                                           |
| 2   | `src/common/config/config-defaults.ts`                     | +2 config default entries                                                   |
| 3   | `src/common/config/settings-metadata.ts`                   | +2 settings metadata entries (TradingEngine group)                          |
| 4   | `src/common/config/effective-config.types.ts`              | +2 typed fields                                                             |
| 5   | `prisma/schema.prisma`                                     | +2 columns on EngineConfig (Int)                                            |
| 6   | `prisma/migrations/*/migration.sql`                        | Auto-generated migration                                                    |
| 7   | `src/persistence/repositories/engine-config.repository.ts` | +2 resolve entries                                                          |
| 8   | `src/dashboard/dto/update-settings.dto.ts`                 | +2 DTO fields                                                               |
| 9   | `src/dashboard/settings.service.ts`                        | +2 SERVICE_RELOAD_MAP entries, +1 'trading-window' handler                  |
| 10  | `src/core/scheduler.service.ts`                            | Trading window gate, validation, reloadTradingWindow, isWithinTradingWindow |
| 11  | `src/core/scheduler.service.spec.ts`                       | ~14 new tests                                                               |
| 12  | `src/common/config/config-defaults.spec.ts`                | Count 78→80                                                                 |
| 13  | `src/dashboard/settings.service.spec.ts`                   | Count 80→82                                                                 |

### Existing Code Reuse

- `ConfigValidationError` from `src/common/errors/`
- `ConfigService.get<number>()` for startup values (already injected in SchedulerService)
- `tryRegisterHandler()` in settings.service.ts for hot-reload registration
- `SERVICE_RELOAD_MAP` pattern for mapping config keys to reload handlers
- `SchedulerService` already imported in settings.service.ts (line 33)
- `SettingsGroup.TradingEngine` enum value already exists
- `@IsInt() @Min() @Max()` decorators already used in update-settings.dto.ts
- `z.coerce.number().int()` pattern already used in env.schema.ts

### Anti-Patterns to Avoid

- Do NOT put the trading window gate in `TradingEngineService` — it already has 9 constructor dependencies; `SchedulerService` owns time-based policy
- Do NOT create a new service for this — it's ~20 lines of logic in an existing service
- Do NOT add a new NestJS module — this lives in `core/`
- Do NOT create a permanent dashboard endpoint for hourly analysis — the investigation is one-time, documented in dev notes
- Do NOT add day-of-week filtering — the epic AC only specifies UTC hour windows (day-of-week is a future enhancement)
- Do NOT emit events for every skipped cycle — that would be one event per 30 seconds during off-hours. A log entry is sufficient
- Do NOT modify `TradingEngineService.executeCycle()` — the gate belongs in the scheduler
- Do NOT modify `ExitMonitorService` — it already runs independently via its own cron

### Project Structure Notes

- All changes align with existing module boundaries (core, common config, persistence, dashboard)
- No new cross-module dependencies introduced
- Config pipeline follows established `pollingIntervalMs` pattern exactly (integer type, TradingEngine group)
- SchedulerService is the natural home for time-based trading policy

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 10.7, Story 10-7-9]
- [Source: _bmad-output/planning-artifacts/prd.md — NFR-R1 (99% uptime during Mon-Fri 9am-5pm ET), Timing Validity (10s persistence)]
- [Source: _bmad-output/planning-artifacts/architecture.md — Configuration Management, Core Module, Scheduler Service]
- [Source: _bmad-output/implementation-artifacts/10-7-8-dynamic-minimum-edge-threshold-book-depth.md — config pipeline pattern, code review findings]
- [Source: src/core/scheduler.service.ts — handlePollingCycle insertion point line 99]
- [Source: src/core/trading-engine.service.ts — executeCycle(), 9 constructor dependencies]
- [Source: src/common/config/config-defaults.ts — pollingIntervalMs pattern]
- [Source: src/dashboard/settings.service.ts — SERVICE_RELOAD_MAP, SchedulerService import line 33]
- [Source: src/common/config/settings-metadata.ts — SettingsGroup.TradingEngine]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Task 1 (Investigation): 371 paper positions analyzed. 95% opened 13:00–21:00 UTC. Peak hours 14–16 UTC have 61% of volume AND highest avg expected edge (0.043–0.044). Off-peak (0–12 UTC) has only 4% volume with lower edges (0.015–0.019). All realized_pnl still NULL (10-7-4 fix applies to future closings). Single-leg events mirror position distribution — 69% in 14–16 UTC.

### File List

- `src/common/config/env.schema.ts` — +2 env var definitions (TRADING_WINDOW_START_UTC, TRADING_WINDOW_END_UTC)
- `src/common/config/config-defaults.ts` — +2 config default entries
- `src/common/config/settings-metadata.ts` — +2 settings metadata entries (TradingEngine group)
- `src/common/config/effective-config.types.ts` — +2 typed fields
- `prisma/schema.prisma` — +2 columns on EngineConfig (Int?)
- `prisma/migrations/20260324181920_add_trading_window_settings/migration.sql` — auto-generated
- `src/persistence/repositories/engine-config.repository.ts` — +2 resolve entries
- `src/dashboard/dto/update-settings.dto.ts` — +2 DTO fields
- `src/dashboard/settings.service.ts` — +2 SERVICE_RELOAD_MAP entries, +1 trading-window handler
- `src/core/scheduler.service.ts` — trading window gate, validation, reloadTradingWindow, isWithinTradingWindow
- `src/core/scheduler.service.spec.ts` — +25 new tests (was 7, now 32)
- `src/common/config/config-defaults.spec.ts` — count 78→80, +2 field entries
- `src/dashboard/settings.service.spec.ts` — count 80→82, +2 mock fields
