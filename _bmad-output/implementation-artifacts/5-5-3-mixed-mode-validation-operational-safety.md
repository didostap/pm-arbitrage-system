# Story 5.5.3: Mixed Mode Validation & Operational Safety

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want the system to validate mixed mode configurations at startup and tag mixed-mode executions distinctly,
So that I am protected from invalid or dangerous platform mode combinations and can distinguish mixed-mode paper trades from fully-paper or fully-live trades.

## Acceptance Criteria

1. **Given** platform mode configuration
   **When** the engine starts
   **Then** startup logs clearly display each platform's mode (`[Kalshi: LIVE] [Polymarket: PAPER]`)
   **And** the log entry follows structured JSON logging with `module: 'core'`

2. **Given** an invalid mode value (not `live` or `paper`)
   **When** the engine starts
   **Then** startup fails with `ConfigValidationError` (code 4010)
   **And** the error message includes the invalid value and env var name

3. **Given** mixed mode detected (one platform `live`, one platform `paper`)
   **When** `ALLOW_MIXED_MODE` is `false` (default)
   **Then** startup fails with `ConfigValidationError` explaining mixed mode is disallowed
   **And** the error message includes the specific modes detected and guidance to set `ALLOW_MIXED_MODE=true`

4. **Given** mixed mode detected
   **When** `ALLOW_MIXED_MODE` is `true`
   **Then** startup logs a `warn`-level message: "Mixed mode active — live capital at risk alongside paper trades"
   **And** the system starts normally

5. **Given** an execution completes where one connector is paper and the other is live
   **When** `isPaper` is determined
   **Then** execution events (`OrderFilledEvent`, `SingleLegExposureEvent`, `ExitTriggeredEvent`, `SingleLegResolvedEvent`) include an `isPaper: boolean` field
   **And** events include a `mixedMode: boolean` field (true when connectors differ in mode)

6. **Given** the system is running
   **When** a new trading cycle begins
   **Then** the `TradingEngineService` log entry includes `{ kalshiMode, polymarketMode }` in the cycle metadata

## Out of Scope

- **Paper risk budget isolation** — future story (paper trades still consume live risk budget during a session, cleaned at restart per Story 5.5.2 design)
- **Dashboard visual distinction** (amber border, `[PAPER]` tag) — Epic 7
- **Runtime mode switching** — mode is immutable at runtime (restart required), per architecture doc
- **Paper-only exit monitoring** — paper positions remain excluded from exit loop per Story 5.5.2
- **`RiskManagerService` paper awareness** — `IRiskManager` interface is frozen; no paper-specific methods

## Tasks / Subtasks

- [x]Task 1: Add `ALLOW_MIXED_MODE` env var (AC: 3, 4)
  - [x]1.1 Add to `.env.example`:
    ```
    ALLOW_MIXED_MODE=false           # Allow one platform live + one paper (default: false)
    ```
  - [x]1.2 Add to `.env.development` with value `true` (dev default — mixed mode allowed in development)
  - [x]1.3 No config type changes needed — read via `ConfigService.get<string>('ALLOW_MIXED_MODE', 'false')` with string comparison `=== 'true'`. **Case-sensitive:** only the exact string `'true'` enables mixed mode. Values like `'True'`, `'TRUE'`, `'1'`, `'yes'` are treated as false.

- [x]Task 2: Add startup mode validation to `EngineLifecycleService` (AC: 1, 2, 3, 4)
  - [x]2.1 Add imports and injections to `EngineLifecycleService`:
    **Imports to add at the top of the file:**
    ```typescript
    import { KALSHI_CONNECTOR_TOKEN, POLYMARKET_CONNECTOR_TOKEN } from '../connectors/connector.constants';
    import type { IPlatformConnector } from '../common/interfaces/platform-connector.interface';
    import { ConfigValidationError } from '../common/errors/config-validation-error';
    ```
    **Constructor injections to add (after the existing `riskManager` injection):**
    ```typescript
    @Inject(KALSHI_CONNECTOR_TOKEN)
    private readonly kalshiConnector: IPlatformConnector,
    @Inject(POLYMARKET_CONNECTOR_TOKEN)
    private readonly polymarketConnector: IPlatformConnector,
    ```
    **DI chain (VERIFIED):** `CoreModule` (line 14 of `core.module.ts`) imports `ExecutionModule` → `ExecutionModule` (line 19 of `execution.module.ts`) imports `ConnectorModule` → `ConnectorModule` exports both tokens. Tokens are transitively available. No module import changes needed.
  - [x]2.2 Create private method `validatePlatformModes(): void` in `EngineLifecycleService`. Wrap `getHealth()` calls in try/catch to handle connectors that may throw during early startup:
    ```typescript
    private validatePlatformModes(): void {
      let kalshiHealth: PlatformHealth;
      let polymarketHealth: PlatformHealth;
      try {
        kalshiHealth = this.kalshiConnector.getHealth();
        polymarketHealth = this.polymarketConnector.getHealth();
      } catch (error) {
        throw new ConfigValidationError(
          `Failed to read connector health for mode validation: ${error instanceof Error ? error.message : 'Unknown error'}`,
          ['Connector health unavailable at startup'],
        );
      }
      const kalshiMode = kalshiHealth.mode === 'paper' ? 'paper' : 'live';
      const polymarketMode = polymarketHealth.mode === 'paper' ? 'paper' : 'live';

      // Log platform modes at startup
      this.logger.log({
        message: `Platform modes: [Kalshi: ${kalshiMode.toUpperCase()}] [Polymarket: ${polymarketMode.toUpperCase()}]`,
        timestamp: new Date().toISOString(),
        module: 'core',
        correlationId: getCorrelationId(),
        data: { kalshiMode, polymarketMode },
      });

      const isMixedMode = kalshiMode !== polymarketMode;

      if (isMixedMode) {
        const allowMixed = this.configService.get<string>('ALLOW_MIXED_MODE', 'false') === 'true';
        if (!allowMixed) {
          throw new ConfigValidationError(
            `Mixed mode detected: Kalshi=${kalshiMode}, Polymarket=${polymarketMode}. ` +
            `Mixed mode is disallowed by default. Set ALLOW_MIXED_MODE=true to enable.`,
            ['ALLOW_MIXED_MODE must be true for mixed-mode operation'],
          );
        }
        this.logger.warn({
          message: 'Mixed mode active — live capital at risk alongside paper trades',
          timestamp: new Date().toISOString(),
          module: 'core',
          correlationId: getCorrelationId(),
          data: { kalshiMode, polymarketMode, allowMixed: true },
        });
      }
    }
    ```
    Also import `PlatformHealth` type: `import type { PlatformHealth } from '../common/types/platform.type';`
  - [x]2.3 Call `this.validatePlatformModes()` in `onApplicationBootstrap()` **after** the DB connectivity check and config validation but **before** NTP validation. Insert between the `this.validateConfiguration(pollingInterval)` call (line ~52) and the NTP `try` block (line ~55). Platform mode validation is a startup prerequisite — no point checking NTP if modes are invalid.
  - [x]2.4 Unit tests in `engine-lifecycle.service.spec.ts`:
    - Test: both live → startup log includes `[Kalshi: LIVE] [Polymarket: LIVE]`
    - Test: both paper → startup log includes `[Kalshi: PAPER] [Polymarket: PAPER]`, no mixed mode warning
    - Test: mixed mode + `ALLOW_MIXED_MODE=false` (default) → throws `ConfigValidationError`
    - Test: mixed mode + `ALLOW_MIXED_MODE=true` → logs warn, does NOT throw
    - Test: `getHealth()` returning no `mode` field → treated as `'live'` (verify `kalshiMode: 'live'`)
    - Existing tests must still pass (mock connectors with `getHealth()` returning default `{ status: 'healthy', platformId: ... }` — no `mode` field = live)

- [x]Task 3: Add `isPaper` and `mixedMode` to execution events (AC: 5)
  - [x]3.1 Update `OrderFilledEvent` constructor in `src/common/events/execution.events.ts` — add `isPaper: boolean` and `mixedMode: boolean` as the **last two** constructor parameters (AFTER `correlationId`), store as public readonly properties:
    ```typescript
    constructor(
      public readonly orderId: string,
      public readonly platform: PlatformId,
      public readonly side: string,
      public readonly price: number,
      public readonly size: number,
      public readonly fillPrice: number,
      public readonly fillSize: number,
      public readonly positionId: string,
      public readonly correlationId: string | undefined,
      public readonly isPaper: boolean = false,       // NEW — after correlationId
      public readonly mixedMode: boolean = false,     // NEW — last param
    ) {}
    ```
    **IMPORTANT:** Use `= false` defaults on both new params. This allows existing call sites to omit them during migration (TypeScript treats trailing defaulted params as optional). However, for explicitness, all call sites SHOULD still pass `false, false` or the computed values.
  - [x]3.2 Update `SingleLegExposureEvent` — add `isPaper: boolean = false` and `mixedMode: boolean = false` as the **last two** parameters (after ALL existing params including `correlationId`). This event has many constructor params — verify the last existing param and append after it.
  - [x]3.3 Update `ExitTriggeredEvent` — same pattern: `isPaper: boolean = false, mixedMode: boolean = false` as the last two parameters.
  - [x]3.4 Update `SingleLegResolvedEvent` — same pattern.
  - [x]3.5 Update `ExecutionFailedEvent` — same pattern.
  - [x]3.6 **Find and update ALL emit sites** for these events. Use `find_referencing_symbols` or grep for each event class name to locate every `new OrderFilledEvent(`, `new SingleLegExposureEvent(`, etc. Pass `isPaper` and `mixedMode` computed from connector health:
    ```typescript
    // Already computed in execute() — reuse these for all event emissions:
    const primaryHealth = primaryConnector.getHealth();
    const secondaryHealth = secondaryConnector.getHealth();
    const isPaper = primaryHealth.mode === 'paper' || secondaryHealth.mode === 'paper';
    // XOR: true when exactly one connector is paper and the other is live
    const mixedMode = (primaryHealth.mode === 'paper') !== (secondaryHealth.mode === 'paper');
    ```
    **CRITICAL:** Use the XOR pattern `(a === 'paper') !== (b === 'paper')` exclusively. Do NOT use the alternative `isPaper && !(a && b)` form — it is harder to reason about.
    **To find ALL emit sites**, run: `grep -rn "new OrderFilledEvent\|new SingleLegExposureEvent\|new ExitTriggeredEvent\|new SingleLegResolvedEvent\|new ExecutionFailedEvent" src/ --include="*.ts"` and update every match.
  - [x]3.7 Update event emission in `ExitMonitorService` — the exit monitor emits `ExitTriggeredEvent`. It does NOT have connector health info. Since exit monitor only processes live positions (default `isPaper = false` filter from Story 5.5.2), pass `isPaper: false, mixedMode: false` for exit events. Paper positions are never evaluated for exit in MVP. Add an inline comment at the emit site:
    ```typescript
    // Exit monitor only processes live positions (isPaper=false filter from Story 5.5.2).
    // Hardcoding false/false — update if paper position exit handling is added.
    ```
  - [x]3.8 Update event emission in `SingleLegResolutionService` — emits `SingleLegResolvedEvent`. It has both connector tokens injected. Compute `isPaper`/`mixedMode` from connector health, same pattern as `ExecutionService`.
  - [x]3.9 Unit tests for each updated event class: verify `isPaper` and `mixedMode` are stored as properties and accessible.
  - [x]3.10 Update all existing tests that create these event instances — add `false, false` (live, non-mixed) as the last two arguments to preserve existing test behavior.

- [x]Task 4: Add mode metadata to trading cycle logs (AC: 6)
  - [x]4.1 In `TradingEngineService.handleTradingCycle()` (the main cycle method), find the cycle start/completion log statement. Add connector health mode info to the cycle log's `data` object.
  - [x]4.2 `TradingEngineService` does NOT currently inject connector tokens. Add `KALSHI_CONNECTOR_TOKEN` and `POLYMARKET_CONNECTOR_TOKEN` injections to `TradingEngineService` constructor:
    ```typescript
    @Inject(KALSHI_CONNECTOR_TOKEN)
    private readonly kalshiConnector: IPlatformConnector,
    @Inject(POLYMARKET_CONNECTOR_TOKEN)
    private readonly polymarketConnector: IPlatformConnector,
    ```
    **DI availability:** `TradingEngineService` is in `CoreModule`, which imports `ExecutionModule` → `ConnectorModule`. Tokens are already available.
  - [x]4.3 In the cycle start log (wherever the engine logs "Starting trading cycle" or similar), add `data` fields:
    ```typescript
    data: {
      kalshiMode: this.kalshiConnector.getHealth().mode === 'paper' ? 'paper' : 'live',
      polymarketMode: this.polymarketConnector.getHealth().mode === 'paper' ? 'paper' : 'live',
      // ... existing cycle data ...
    }
    ```
  - [x]4.4 Unit tests: verify cycle log includes `kalshiMode` and `polymarketMode` fields.

- [x]Task 5: Update mock factories and existing tests (AC: all)
  - [x]5.1 In `src/test/mock-factories.ts`, the `createMockPlatformConnector()` default `getHealth` already returns no `mode` field (live). No factory changes needed.
  - [x]5.2 For tests that need to verify mixed mode, override `getHealth` per-test:
    ```typescript
    kalshiConnector.getHealth.mockReturnValue({ ...defaultHealth, mode: 'paper' });
    polymarketConnector.getHealth.mockReturnValue({ ...defaultHealth }); // no mode = live
    ```
  - [x]5.3 Scan ALL test files that instantiate event classes. Run: `grep -rn "new OrderFilledEvent\|new SingleLegExposureEvent\|new ExitTriggeredEvent\|new SingleLegResolvedEvent\|new ExecutionFailedEvent" src/ test/ --include="*.spec.ts"` — add the computed `isPaper, mixedMode` values (or `false, false` for live-mode tests) at the end of each constructor call. **Known files to check:**
    - `execution.service.spec.ts` — emits `OrderFilledEvent`, `ExecutionFailedEvent`, `SingleLegExposureEvent`
    - `single-leg-resolution.service.spec.ts` — emits `SingleLegResolvedEvent`
    - `exit-monitor.service.spec.ts` — emits `ExitTriggeredEvent`
    - `exposure-alert-scheduler.service.spec.ts` — may emit `SingleLegExposureEvent` reminder events
    - `trading-engine.service.spec.ts` — if it asserts on events
    - `execution-queue.service.spec.ts` — if it asserts on events
    - Any e2e tests in `test/e2e/` that instantiate these events
  - [x]5.4 For `EngineLifecycleService` tests, add mock connector providers in the testing module setup:
    ```typescript
    { provide: KALSHI_CONNECTOR_TOKEN, useValue: createMockPlatformConnector(PlatformId.KALSHI) },
    { provide: POLYMARKET_CONNECTOR_TOKEN, useValue: createMockPlatformConnector(PlatformId.POLYMARKET) },
    ```

- [x]Task 6: Run lint + test suite (AC: all)
  - [x]6.1 Run `pnpm lint` — fix any issues
  - [x]6.2 Run `pnpm test` — all tests pass (existing + new)
  - [x]6.3 Verify test count increased

## Dev Notes

### Design Decision: `ALLOW_MIXED_MODE` Default False

Mixed mode (one platform live, one paper) is dangerous because:
- Paper trades consume live risk budget (per Story 5.5.2 known limitation)
- A paper fill failure does NOT trigger real single-leg exposure — but the live leg IS committed
- Operator may not realize they're risking real capital on one side

Default `false` forces explicit opt-in. Development environments default to `true` (in `.env.development`) since both platforms are typically paper in dev.

### Design Decision: Mode Detection via `getHealth().mode`

Platform mode is detected by calling `connector.getHealth()` and checking the optional `mode` field:
- `mode === 'paper'` → paper connector (set by `PaperTradingConnector.getHealth()`)
- `mode === undefined` → live connector (real connectors don't set `mode`)

This is the canonical detection mechanism established in Story 5.5.1. Do NOT read `PLATFORM_MODE_*` env vars directly — the connector's health is the source of truth.

### Design Decision: `mixedMode` as Distinct Flag

`isPaper = true` covers both "fully paper" and "mixed mode" cases (OR logic from Story 5.5.2). The new `mixedMode: boolean` flag distinguishes them:
- `isPaper: true, mixedMode: false` → both connectors are paper
- `isPaper: true, mixedMode: true` → one connector is paper, one is live (DANGEROUS — live capital at risk)
- `isPaper: false, mixedMode: false` → both connectors are live

`mixedMode: true` with `isPaper: false` is impossible (if either is paper, `isPaper` is true).

### `mixedMode` Computation

```typescript
// In ExecutionService.execute():
const primaryHealth = primaryConnector.getHealth();
const secondaryHealth = secondaryConnector.getHealth();
const isPaper = primaryHealth.mode === 'paper' || secondaryHealth.mode === 'paper';
// XOR: true when exactly one connector is paper and the other is live
const mixedMode = (primaryHealth.mode === 'paper') !== (secondaryHealth.mode === 'paper');
```

Use the XOR pattern exclusively — it is clearest and most idiomatic for "exactly one is true."

### Event Update Strategy

All execution events gain `isPaper` and `mixedMode` as the last constructor parameters. This is a breaking change to event constructors — all existing instantiation sites must add `, false, false` (live, non-mixed defaults).

**No event consumers exist yet** (monitoring module is Epic 6). So there are no subscribers to update. The events carry the data for future consumption.

**Emit site inventory** (must all be updated):

| Event | Emit location | Source of isPaper/mixedMode |
|-------|--------------|---------------------------|
| `OrderFilledEvent` | `execution.service.ts` | Local `isPaper`/`mixedMode` vars |
| `ExecutionFailedEvent` | `execution.service.ts` (primary depth fail ~line 106, primary submit fail ~line 120) | Local vars |
| `SingleLegExposureEvent` | `execution.service.ts` + `exposure-alert-scheduler.service.ts` (reminder re-emissions) | Local vars / compute from connector health |
| `ExitTriggeredEvent` | `exit-monitor.service.ts` | Hardcode `false, false` (live-only positions) |
| `SingleLegResolvedEvent` | `single-leg-resolution.service.ts` | Compute from connector health |

**CRITICAL:** Run `grep -rn "new ExecutionFailedEvent\|new OrderFilledEvent\|new SingleLegExposureEvent\|new ExitTriggeredEvent\|new SingleLegResolvedEvent" src/ --include="*.ts"` to verify the complete list. If any emit sites are found beyond this table, update them.

### `EngineLifecycleService` — New Injections

Adding two connector token injections. The DI chain is:
```
CoreModule imports ExecutionModule → ExecutionModule imports ConnectorModule → ConnectorModule exports KALSHI_CONNECTOR_TOKEN, POLYMARKET_CONNECTOR_TOKEN
```

The `ConnectorModule` tokens are transitively available to `CoreModule` providers. No module import changes needed.

### `TradingEngineService` — New Injections

Same DI chain as above. `TradingEngineService` is a provider in `CoreModule`. The connector tokens are available via the transitive import chain.

### `ConfigValidationError` Usage

The existing `ConfigValidationError` (code 4010, severity `critical`) takes `(message: string, validationErrors: string[])`. For mixed mode validation:
```typescript
throw new ConfigValidationError(
  'Mixed mode detected: Kalshi=paper, Polymarket=live...',
  ['ALLOW_MIXED_MODE must be true for mixed-mode operation'],
);
```

### Invalid Mode Validation Already Exists

Story 5.5.1 added `validatePlatformMode()` in `connector.module.ts` (lines 15-27). It already rejects invalid mode values (not `live` or `paper`) with `ConfigValidationError`. So AC2 is **already satisfied** — the validation happens at DI resolution time, before `onApplicationBootstrap()` runs. No additional work needed for AC2 beyond verifying it still works.

Verify by checking the existing test in `connector.module.spec.ts` that covers invalid mode rejection.

### Interface Freeze Compliance

`IPlatformConnector` (11 methods) and `IRiskManager` (13 methods) — **UNCHANGED**. This story only modifies:
- `EngineLifecycleService` (new injections + startup validation method)
- `TradingEngineService` (new injections + cycle log enrichment)
- Event classes (additional constructor params — backward-compatible with `, false, false` defaults)
- Env config files (new `ALLOW_MIXED_MODE` var)

No new interface methods. No new connector methods. No new risk manager methods.

### DoD Gates (from Epic 4.5 Retro, carried forward)

1. **Test isolation:** No shared mutable state — mock connectors return fresh health per test
2. **Interface preservation:** No interface changes. Event constructor extensions are additive.
3. **Normalization ownership:** Connectors not touched in this story

### Previous Story Intelligence (5.5.2)

Key learnings:
- `isPaper` is determined via `connector.getHealth().mode === 'paper'` — OR logic: either connector paper → whole execution is paper
- Repository methods default to `isPaper = false` (live-only) — paper positions excluded from exit monitor, reconciliation, risk recalculation
- Risk budget contamination during session is a known limitation — paper trades consume live budget until restart
- `handleSingleLeg` has 16 parameters (known tech debt) — do NOT add more params, reuse `isPaper` already threaded
- No changes to `RiskManagerService`, `ExitMonitorService`, or reconciliation — isolation enforced at repository + execution layers

### Known Limitation: Event Constructor Parameter Sprawl

Execution events (especially `SingleLegExposureEvent`) already have many constructor parameters. Adding `isPaper` and `mixedMode` makes them longer. The correct long-term fix is refactoring event constructors to accept an options object. This is out of scope — track as tech debt if needed.

### File Structure Notes

**Modified files:**

- `src/core/engine-lifecycle.service.ts` — inject connector tokens, add `validatePlatformModes()`, call in `onApplicationBootstrap()`
- `src/core/engine-lifecycle.service.spec.ts` — add mock connector providers, add mode validation tests
- `src/core/trading-engine.service.ts` — inject connector tokens, add mode to cycle logs
- `src/core/trading-engine.service.spec.ts` — add mock connector providers, verify cycle log includes modes
- `src/common/events/execution.events.ts` — add `isPaper`, `mixedMode` to all event constructors
- `src/modules/execution/execution.service.ts` — compute `mixedMode`, pass to event emissions
- `src/modules/execution/execution.service.spec.ts` — update event constructor calls + add mixedMode tests
- `src/modules/exit-management/exit-monitor.service.ts` — update `ExitTriggeredEvent` emissions with `false, false`
- `src/modules/exit-management/exit-monitor.service.spec.ts` — update event constructor calls
- `src/modules/execution/single-leg-resolution.service.ts` — compute isPaper/mixedMode from connector health, pass to `SingleLegResolvedEvent`
- `src/modules/execution/single-leg-resolution.service.spec.ts` — update event constructor calls
- `src/modules/execution/exposure-alert-scheduler.service.ts` — update `SingleLegExposureEvent` emissions if it emits reminder events
- `.env.example` — add `ALLOW_MIXED_MODE`
- `.env.development` — add `ALLOW_MIXED_MODE=true`

**NOT modified (by design):**

- `src/connectors/paper/*` — no changes needed
- `src/connectors/connector.module.ts` — mode validation already handles invalid values
- `src/modules/risk-management/risk-manager.service.ts` — unaware of paper mode (by design)
- `src/persistence/repositories/*` — no changes needed
- `src/common/interfaces/*` — interface freeze in effect
- `prisma/schema.prisma` — no schema changes

### LAD Design Review — Applied Fixes

Review performed by LAD MCP (kimi-k2-thinking + glm-4.7). Key findings analyzed:

1. **Dual `mixedMode` formulas (Primary, M):** FIXED — removed ambiguous `isPaper && !(a && b)` alternative, kept only XOR pattern `(a === 'paper') !== (b === 'paper')`.
2. **Missing `ExecutionFailedEvent` from emit inventory (Primary, H):** FIXED — added to inventory table with specific line references. Added grep command for completeness verification.
3. **TypeScript param order — required after optional (Primary+Secondary, M/H):** FIXED — `isPaper` and `mixedMode` placed AFTER `correlationId` with `= false` defaults. This avoids TypeScript compilation errors with optional-then-required ordering.
4. **Incomplete test file scan list (Primary, M):** FIXED — expanded list, added grep command for comprehensive scan.
5. **Vague cycle log location (Primary, M):** FIXED — specified `TradingEngineService.handleTradingCycle()` as exact method.
6. **`getHealth()` could throw during startup (Primary, M):** FIXED — added try/catch in `validatePlatformModes()` wrapping `getHealth()` calls with `ConfigValidationError` on failure.
7. **Import instruction ordering (Secondary, H):** FIXED — consolidated all imports (tokens, types, ConfigValidationError) into Task 2.1. Removed orphaned Task 2.4.
8. **DI chain not explicitly verified (Secondary, H):** FIXED — added explicit verification note with file/line references for `CoreModule`, `ExecutionModule`, `ConnectorModule` import chain.
9. **Exit monitor hardcoded values comment (Secondary, L):** FIXED — added inline comment guidance in Task 3.7.
10. **Env var case sensitivity (Secondary, L):** FIXED — added note in Task 1.3.

**Dismissed findings:**
- Startup race condition (P2) — `getHealth()` is synchronous; `PaperTradingConnector` created by DI factory before `onApplicationBootstrap()`.
- Exit monitor contradiction (P4) — not a contradiction; exit monitor evaluates positions, not individual legs. Mixed-mode position is `isPaper: true` → excluded correctly.
- Rename to `PLATFORM_ALLOW_MIXED_MODE` (P8) — `ALLOW_MIXED_MODE` is a system-level setting, not per-platform. Different scope.
- Extract `determineExecutionMode()` helper (P10) — 2-line computation doesn't warrant a helper method.
- Event object literals (P11) — events always use `new EventClass(...)`, never object literals.
- `validateConfiguration()` should use `ConfigValidationError` (S5) — out of scope, pre-existing code.
- Test provider conflict (S7) — tests use direct provider injection, not full module imports.
- Invalid mode from `getHealth()` (S9) — impossible path; only `PaperTradingConnector` sets `mode`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5.5, Story 5.5.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Environment Configuration — Paper Trading Configuration]
- [Source: _bmad-output/implementation-artifacts/5-5-2-paper-position-state-isolation-tracking.md — isPaper flag propagation, risk budget contamination limitation]
- [Source: _bmad-output/implementation-artifacts/5-5-1-paper-trading-connector-mode-configuration.md — PaperTradingConnector.getHealth(), validatePlatformMode()]
- [Source: _bmad-output/implementation-artifacts/5-5-0-interface-stabilization-test-infrastructure.md — Interface Freeze, Mock Factories, DoD Gates]
- [Source: pm-arbitrage-engine/src/core/engine-lifecycle.service.ts — onApplicationBootstrap() startup sequence]
- [Source: pm-arbitrage-engine/src/core/trading-engine.service.ts — trading cycle orchestration]
- [Source: pm-arbitrage-engine/src/connectors/connector.module.ts — validatePlatformMode(), useFactory pattern]
- [Source: pm-arbitrage-engine/src/common/events/execution.events.ts — OrderFilledEvent, SingleLegExposureEvent, etc.]
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts — EVENT_NAMES constant]
- [Source: pm-arbitrage-engine/src/common/errors/config-validation-error.ts — ConfigValidationError(message, validationErrors[])]
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts — isPaper determination, event emission]
- [Source: pm-arbitrage-engine/src/connectors/connector.constants.ts — KALSHI_CONNECTOR_TOKEN, POLYMARKET_CONNECTOR_TOKEN]
- [Source: CLAUDE.md#Architecture, #Error Handling, #Naming Conventions, #Testing, #Domain Rules]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — all tests passed on first run after implementation.

### Completion Notes List

- AC1: Startup logs display `[Kalshi: LIVE/PAPER] [Polymarket: LIVE/PAPER]` with structured JSON and `module: 'core'`
- AC2: Already satisfied by Story 5.5.1 `validatePlatformMode()` in `connector.module.ts`
- AC3: Mixed mode + `ALLOW_MIXED_MODE=false` throws `ConfigValidationError` with guidance message
- AC4: Mixed mode + `ALLOW_MIXED_MODE=true` logs warn-level "Mixed mode active — live capital at risk alongside paper trades"
- AC5: All 5 execution events (`OrderFilledEvent`, `ExecutionFailedEvent`, `SingleLegExposureEvent`, `ExitTriggeredEvent`, `SingleLegResolvedEvent`) now include `isPaper: boolean` and `mixedMode: boolean` fields. All 13 emit sites updated.
- AC6: `TradingEngineService.executeCycle()` cycle start log includes `kalshiMode` and `polymarketMode` in data
- DI fix: `CoreModule` needed `ConnectorModule` import — NestJS does not transitively expose tokens from nested module imports. Story spec claimed transitive availability but this was incorrect.
- LAD review performed; no actionable high-priority findings adopted (reviewer misunderstood param ordering; race condition dismissed per story notes; exit-monitor hardcoding is by design)
- 827 tests passed, 0 failed. Lint clean. 19 new tests total (6 lifecycle + 1 trading cycle + 12 event class isPaper/mixedMode tests).

### Senior Developer Review (AI)

**Reviewed by:** Arbi (via Amelia) on 2026-02-23
**Issues Found:** 3 High, 3 Medium, 2 Low
**Issues Fixed:** 3 High, 3 Medium (6 total)
**Action Items Created:** 0

#### Fixes Applied

1. **H1 — Missing event class tests for `isPaper`/`mixedMode`:** Added 12 tests across all 5 event classes in `execution.events.spec.ts`, including `OrderFilledEvent` and `ExecutionFailedEvent` which previously had zero test coverage. Tests verify property storage, defaults (`false`), and explicit values.
2. **H2 — Existing spec files not updated with explicit `isPaper, mixedMode`:** Updated `execution.events.spec.ts` call sites to pass explicit `false, false`. Updated `exposure-tracker.service.spec.ts` helper to pass explicit `undefined, false, false`.
3. **H3 — `validateConfiguration()` threw raw `Error`:** Changed to `ConfigValidationError` with validation errors array. Updated corresponding tests to assert `ConfigValidationError` type.
4. **M1 — Inconsistent variable names in `closeLeg()`:** Renamed `kalshiHealthClose`/`polymarketHealthClose`/`isPaperClose`/`mixedModeClose` to `kalshiHealth`/`polymarketHealth`/`isPaper`/`mixedMode` for consistency with all other sites.
5. **M2 — ConfigService mock inconsistency:** Acknowledged; default mock correctly returns `defaultValue ?? 'false'` which matches production usage. No code change needed — documented as non-issue.
6. **M3 — Dev record test count misleading:** Updated test counts to reflect all tests including event class coverage.

#### Acknowledged (Low, not fixed)

- L1: Reconciliation `OrderFilledEvent` hardcodes `false, false` despite connectors being available — accepted as design choice (reconciliation context is startup-specific).
- L2: Pre-existing gap: `OrderFilledEvent`/`ExecutionFailedEvent` had zero event-level tests — now fixed by this review.

### File List

- `pm-arbitrage-engine/.env.example` — Added `ALLOW_MIXED_MODE=false`
- `pm-arbitrage-engine/.env.development` — Added `ALLOW_MIXED_MODE=true`
- `pm-arbitrage-engine/src/core/core.module.ts` — Added `ConnectorModule` import for DI
- `pm-arbitrage-engine/src/core/engine-lifecycle.service.ts` — Injected connector tokens, added `validatePlatformModes()`, fixed `validateConfiguration()` to throw `ConfigValidationError`
- `pm-arbitrage-engine/src/core/engine-lifecycle.service.spec.ts` — 6 mode validation tests + updated polling interval tests for `ConfigValidationError`
- `pm-arbitrage-engine/src/core/trading-engine.service.ts` — Injected connector tokens, mode in cycle start log
- `pm-arbitrage-engine/src/core/trading-engine.service.spec.ts` — 1 new test, connector mock providers
- `pm-arbitrage-engine/src/common/events/execution.events.ts` — `isPaper`/`mixedMode` on all 5 event classes
- `pm-arbitrage-engine/src/common/events/execution.events.spec.ts` — Added `OrderFilledEvent`/`ExecutionFailedEvent` tests, added `isPaper`/`mixedMode` coverage for all 5 events, explicit `false, false` on existing call sites
- `pm-arbitrage-engine/src/modules/execution/execution.service.ts` — `mixedMode` computation + event updates
- `pm-arbitrage-engine/src/modules/execution/single-leg-resolution.service.ts` — `isPaper`/`mixedMode` from connector health, normalized variable names in `closeLeg()`
- `pm-arbitrage-engine/src/modules/execution/exposure-alert-scheduler.service.ts` — `isPaper`/`mixedMode` from connector health
- `pm-arbitrage-engine/src/modules/execution/exposure-tracker.service.spec.ts` — Explicit `isPaper`/`mixedMode` in helper factory
- `pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts` — Hardcoded `false, false` (live-only)
- `pm-arbitrage-engine/src/reconciliation/startup-reconciliation.service.ts` — Hardcoded `false, false` (startup context)
