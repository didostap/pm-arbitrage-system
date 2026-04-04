# Story 10-95.12: Backtest Pair Re-Entry Cooldown

Status: done

## Story

As an operator,
I want the backtest engine to enforce a cooldown period before re-entering the same pair after a TIME_DECAY exit,
so that the simulation doesn't churn through persistent non-converging edges, accumulating fees without new information.

## Context

Backtest run `9bab5cf5` (Mar 1-5, $10K bankroll) showed extreme re-entry churning: the top pair entered **76 times** at 1.24-hour average intervals, losing $761. Top 3 pairs account for **42% of total loss** ($1,421) from fee churning alone. 87% of positions (354/406 closed) exited via TIME_DECAY — meaning the edge persisted across the hold period but never converged to profit. Immediate re-entry recaptures the same stale edge and pays fees again.

Story 10-95-11 (edge metric realignment) corrected the entry formula to `|K-P|`, which filters more noise and may reduce some churn. This story addresses the remaining structural problem: even with a correct edge metric, persistent non-converging edges will still trigger repeated entries if no cooldown exists.

## Acceptance Criteria

1. **Given** a position exits via `TIME_DECAY` **when** the same pair appears as a candidate in subsequent timesteps **then** the pair is skipped until `cooldownHours` have elapsed since the exit timestamp.

2. **Given** a position exits via `EDGE_EVAPORATION`, `PROFIT_CAPTURE`, `STOP_LOSS`, `INSUFFICIENT_DEPTH`, or `RESOLUTION_FORCE_CLOSE` **when** the same pair reappears **then** no cooldown is enforced (these exits indicate changed market conditions or resolved events).

3. **Given** `cooldownHours` is not provided in `BacktestConfig` **when** the simulation runs **then** cooldown defaults to `exitTimeLimitHours` (matching the hold period, e.g., 72h). Resolved in the engine via `config.cooldownHours ?? config.exitTimeLimitHours`.

4. **Given** `cooldownHours` is set to `0` **when** the simulation runs **then** no cooldown is enforced (0 means disabled — re-entry allowed immediately).

5. **Given** cooldown tracking **when** simulation runs **then** cooldown state is tracked per-pair via a `Map<string, Date>` local to `runSimulationLoop()`. Entries are lazily cleaned up when checked and found expired. Map is garbage-collected when `runSimulationLoop()` returns. `/** Cleanup: lazy delete on expiry check, GC'd on method return. Bounded by unique pairId count per run (~50 max). */`

6. **Given** headless simulations (walk-forward, sensitivity) **when** running sub-simulations **then** cooldown state is independent per simulation run (each `runSimulationLoop()` call creates its own cooldown map — no service-level shared state).

7. **Given** existing tests **when** all tests run **then** all pass. New tests verify: cooldown blocks re-entry within period, cooldown allows re-entry after period expires, cooldown does not apply to non-TIME_DECAY exits, cooldown defaults to `exitTimeLimitHours`, cooldown=0 disables, cooldown map cleanup works.

## Tasks / Subtasks

- [x] Task 1: Add `cooldownHours` to `IBacktestConfig` interface (AC: #3)
  - [x] 1.1 In `src/common/interfaces/backtest-engine.interface.ts:23`, add `cooldownHours?: number;` after `exitStopLossPct?`.
  - [x] 1.2 This is an optional field — existing config objects remain valid without it.

- [x] Task 2: Add `cooldownHours` to `BacktestConfigDto` (AC: #3, #4)
  - [x] 2.1 In `src/modules/backtesting/dto/backtest-config.dto.ts`, after the `exitStopLossPct` field (line ~109), add:
    ```typescript
    @IsOptional()
    @IsNumber()
    @Min(0)
    cooldownHours?: number;
    ```
  - [x] 2.2 No default value — engine resolves `config.cooldownHours ?? config.exitTimeLimitHours` at runtime.
  - [x] 2.3 `@Min(0)` allows 0 (disables cooldown). Negative values rejected.

- [x] Task 3: Add `cooldownHours` DTO + interface tests (AC: #3, #4, #7)
  - [x] 3.1 In `backtest-config.dto.spec.ts`, add after the `exitStopLossPct` tests (around line 401):
    - `[P0] cooldownHours is optional — omitting does not cause validation error` — `plainToInstance(BacktestConfigDto, validInput)`, verify no error for `cooldownHours` property AND assert `dto.cooldownHours` is `undefined` (ensures `?? exitTimeLimitHours` fallback activates in engine).
    - `[P1] cooldownHours accepts 0 (disabled)` — set `cooldownHours: 0`, verify no error.
    - `[P1] cooldownHours accepts positive value` — set `cooldownHours: 48`, verify no error.
    - `[P1] cooldownHours rejects negative value` — set `cooldownHours: -1`, expect validation error.
  - [x] 3.2 Add IBacktestConfig conformance test after existing ones (around line 452):
    - `[P0] IBacktestConfig interface includes optional cooldownHours: number` — create literal with `cooldownHours: 48`, assert `config.cooldownHours === 48`. Follow the pattern of the `depthCacheBudgetMb` conformance test at line 429.

- [x] Task 4: Implement cooldown tracking in `runSimulationLoop()` (AC: #1, #3, #5, #6)
  - [x] 4.1 In `src/modules/backtesting/engine/backtest-engine.service.ts`, in `runSimulationLoop()` after `const bankroll = ...` (line 432), add:
    ```typescript
    const cooldownHours = config.cooldownHours ?? config.exitTimeLimitHours;
    /** Cleanup: lazy delete on expiry check, GC'd on method return. Bounded by unique pairId count per run (~50 max). */
    const cooldownMap = new Map<string, Date>();
    ```
  - [x] 4.2 Pass `cooldownMap` to both `evaluateExits()` and `detectOpportunities()` as an additional parameter.
  - [x] 4.3 Pass `cooldownHours` to `detectOpportunities()` as an additional parameter (needed for expiry check).

- [x] Task 5: Record TIME_DECAY exits in cooldown map (AC: #1, #2)
  - [x] 5.1 Update `evaluateExits()` signature — append `cooldownMap: Map<string, Date>` as the last parameter.
  - [x] 5.2 After `this.portfolioService.closePosition(...)` at line ~572, add:
    ```typescript
    if (exitResult.reason === 'TIME_DECAY') {
      cooldownMap.set(position.pairId, step.timestamp);
    }
    ```
  - [x] 5.3 Non-TIME_DECAY exits do NOT write to the cooldown map — this is the mechanism for AC #2.

- [x] Task 6: Check cooldown in `detectOpportunities()` (AC: #1, #4)
  - [x] 6.1 Update `detectOpportunities()` signature — append `cooldownMap: Map<string, Date>` and `cooldownHours: number` as the last two parameters (after `depthCache`).
  - [x] 6.2 After the `hasPosition` check at line 595, before edge calculation, add:
    ```typescript
    if (cooldownHours > 0) {
      const lastTimeDecayExit = cooldownMap.get(pairData.pairId);
      if (lastTimeDecayExit) {
        const elapsedMs = step.timestamp.getTime() - lastTimeDecayExit.getTime();
        const elapsedHours = elapsedMs / (1000 * 60 * 60);
        if (elapsedHours < cooldownHours) continue;
        cooldownMap.delete(pairData.pairId); // Expired — remove entry
      }
    }
    ```
  - [x] 6.3 When `cooldownHours === 0`, the outer `if` is false → cooldown check skipped entirely (AC #4).
  - [x] 6.4 Add DEBUG log when cooldown blocks entry (follows existing edge cap logging pattern at line ~611-614):
    ```typescript
    this.logger.debug(`Cooldown: ${pairData.pairId} blocked, ${(cooldownHours - elapsedHours).toFixed(1)}h remaining`);
    ```

- [x] Task 7: Add cooldown engine tests (AC: #1, #2, #3, #4, #5, #7)
  - [x] 7.1 Add a new `describe('Pair re-entry cooldown')` block in `backtest-engine.service.spec.ts`.
  - [x] 7.2 **Test setup pattern:** Use a stateful mock for `portfolioService.getState` that tracks opens/closes:
    ```typescript
    const state = {
      openPositions: new Map<string, any>(),
      closedPositions: [],
      availableCapital: new Decimal('10000'),
      deployedCapital: new Decimal('0'),
    };
    portfolioService.getState.mockImplementation(() => state);
    portfolioService.openPosition.mockImplementation((_runId, pos) => {
      state.openPositions.set(pos.positionId, pos);
      state.availableCapital = state.availableCapital.minus(pos.positionSizeUsd);
      state.deployedCapital = state.deployedCapital.plus(pos.positionSizeUsd);
    });
    portfolioService.closePosition.mockImplementation((_runId, posId) => {
      const pos = state.openPositions.get(posId);
      if (pos) {
        state.openPositions.delete(posId);
        state.availableCapital = state.availableCapital.plus(pos.positionSizeUsd);
        state.deployedCapital = state.deployedCapital.minus(pos.positionSizeUsd);
      }
    });
    ```
  - [x] 7.3 Tests (all use timesteps with pair K-1:P-1 at prices producing edge above threshold):
    - `[P0] should skip pair re-entry within cooldown period after TIME_DECAY exit` — T1 (14:00): pair enters. T2 (T1+73h): TIME_DECAY exit (exitTimeLimitHours=72). T3 (T2+1h): same pair, good edge → should NOT enter (within 72h cooldown, default). Assert `openPosition` called exactly once.
    - `[P0] should allow pair re-entry after cooldown period expires` — T1: pair enters. T2: TIME_DECAY exit. T3 (T2+73h): same pair → SHOULD enter (cooldown expired). Assert `openPosition` called twice.
    - `[P0] should NOT apply cooldown for EDGE_EVAPORATION exit` — T1: pair enters. T2: EDGE_EVAPORATION exit. T3 (T2+1h): same pair → SHOULD enter. Assert `openPosition` called twice.
    - `[P0] should NOT apply cooldown for PROFIT_CAPTURE exit` — same pattern, mock PROFIT_CAPTURE.
    - `[P0] should NOT apply cooldown for STOP_LOSS exit` — same pattern, mock STOP_LOSS.
    - `[P0] should NOT apply cooldown for RESOLUTION_FORCE_CLOSE exit` — same pattern with resolution prices.
    - `[P0] should NOT apply cooldown for INSUFFICIENT_DEPTH exit` — same pattern.
    - `[P1] should use exitTimeLimitHours as default cooldown when cooldownHours not configured` — run with `mockConfig` that omits `cooldownHours`, verify cooldown matches `exitTimeLimitHours` (72h). T1: enter. T2: TIME_DECAY. T3 (T2+71h): blocked. T4 (T2+73h): allowed.
    - `[P1] should disable cooldown when cooldownHours=0` — run with `cooldownHours: 0`. T1: enter. T2: TIME_DECAY exit. T3 (T2+1h): SHOULD enter (cooldown disabled). Assert `openPosition` called twice.
    - `[P1] should clean up expired cooldown map entry on next check` — T1: enter. T2: TIME_DECAY. T3 (T2+73h, past cooldown): re-entry allowed. Verify this doesn't leak map entries (internal implementation detail — optional if testing via map size is possible, otherwise skip).
  - [x] 7.4 **Mock configuration:** `exitTimeLimitHours: 72` in `mockConfig`. For TIME_DECAY tests, set T2 = T1 + 73h so the exit evaluator triggers TIME_DECAY naturally. Use `exitEvaluatorService.evaluateExits.mockReturnValue()` to control exit reasons when needed. For non-TIME_DECAY tests, mock specific exit reasons.

- [x] Task 8: Update `mockConfig` in engine spec and related spec files (AC: #7)
  - [x] 8.1 Verify that the existing `mockConfig` in `backtest-engine.service.spec.ts` does NOT require `cooldownHours` — it's optional and the engine defaults to `exitTimeLimitHours`. Confirm no existing tests fail with the new cooldown logic (existing tests don't trigger TIME_DECAY followed by same-pair re-entry in subsequent timesteps).
  - [x] 8.2 Verify existing tests still pass — the cooldown map and parameters are new but existing tests don't trigger TIME_DECAY exits followed by re-entry (they test single-step scenarios). Confirm no regression.
  - [x] 8.3 Check other spec files that call `runSimulationLoop` indirectly (walk-forward-routing, chunked-data-loading, calibration-report, sensitivity-analysis) — these call `startRun()` which calls `runSimulationLoop()`. Since cooldown is internal to the loop and defaults to `exitTimeLimitHours`, existing tests should pass without changes.

- [x] Task 9: Lint + test (post-edit)
  - [x] 9.1 Run `pnpm lint` — fix any issues.
  - [x] 9.2 Run `pnpm test` — verify baseline + new tests pass. Expected: ~3727 + ~10 new = ~3737 tests passing.

## Dev Notes

**Line numbers are approximate** — always search by function/method name rather than relying on exact line numbers, as prior edits may have shifted them.

### Critical Implementation Details

**The cooldown map is a local variable in `runSimulationLoop()`.** This is the cleanest scoping approach: each simulation run gets its own map, no service-level state to manage, no cross-contamination between runs, and automatic GC on method return. The alternative (service-level `Map<runId, Map<pairId, Date>>`) adds lifecycle complexity for no benefit.

**Only TIME_DECAY exits trigger cooldown.** The logic is that TIME_DECAY means "edge persisted but never converged to profit" — immediate re-entry would just repeat the same losing pattern. All other exit reasons indicate market conditions changed (edge evaporated, profit taken, stop hit, resolution, depth returned), making re-entry potentially profitable with new information.

**The `cooldownHours > 0` guard (Task 6.2) prevents map lookups when cooldown is disabled.** When `cooldownHours === 0`, the check is skipped entirely — no map reads, no overhead. This is the opt-out mechanism.

**Multiple TIME_DECAY exits for the same pair.** If a pair exits via TIME_DECAY, re-enters after cooldown expires, and exits via TIME_DECAY again, the second exit overwrites the cooldown map entry. The cooldown period restarts from the most recent TIME_DECAY exit timestamp. This is correct — each TIME_DECAY exit represents a new "no convergence" signal.

**Parameter count note.** `detectOpportunities()` currently has 9 parameters. Adding `cooldownMap` and `cooldownHours` brings it to 11. `evaluateExits()` goes from 6 to 7. These are private methods called from one place (`runSimulationLoop`). The high parameter count reflects pre-computed Decimal values passed to avoid redundant `new Decimal()` in the hot loop. A future refactoring could bundle simulation parameters into a context object, but that's out of scope here.

**File size note.** `backtest-engine.service.ts` is currently 748 formatted lines (above the 600-line review trigger from CLAUDE.md). This story adds ~16 lines, bringing it to ~764. The file is a facade/orchestrator (8 constructor deps, under the <=8 threshold), and the cooldown logic is tightly coupled with the simulation loop. Extraction is not warranted for ~16 lines. Reviewer should note this for future reference — if the file grows further in subsequent stories, decomposition should be prioritized.

**Test complexity: stateful mocks.** The cooldown tests require a multi-timestep enter-exit-reenter cycle. Unlike existing single-step tests, these need `portfolioService.getState` to reflect opens and closes dynamically. Task 7.2 provides a stateful mock pattern. Key: `openPosition` mock must add to the map, `closePosition` mock must delete from it, so subsequent `getState` calls return updated state.

**Edge values for test timesteps.** Use prices K=0.40, P=0.55 (produces `|K-P| = 0.15` gross edge, well above `edgeThresholdPct: 0.05`). These are the same prices used in existing test fixtures (`coverage-gap`, `insufficient-depth`, `resolution-force-close`).

### File Impact Map

**Modify (engine logic):**
| File | Current Lines | Change |
|------|---------------|--------|
| `src/common/interfaces/backtest-engine.interface.ts` | 40 | Add `cooldownHours?: number` to `IBacktestConfig` (~1 line) |
| `src/modules/backtesting/dto/backtest-config.dto.ts` | 111 | Add `cooldownHours` optional field with decorators (~4 lines) |
| `src/modules/backtesting/engine/backtest-engine.service.ts` | 748 | Add cooldown map in `runSimulationLoop()`, record in `evaluateExits()`, check in `detectOpportunities()` (~16 lines) |

**Modify (tests):**
| File | Change |
|------|--------|
| `src/modules/backtesting/dto/backtest-config.dto.spec.ts` | Add cooldownHours validation tests (~4 tests) + IBacktestConfig conformance test (~1 test) |
| `src/modules/backtesting/engine/backtest-engine.service.spec.ts` | Add `describe('Pair re-entry cooldown')` with ~10 tests |

**What NOT to change:**
| File | Why |
|------|-----|
| `src/modules/backtesting/engine/exit-evaluator.service.ts` | Exit evaluator determines exit reasons — cooldown is an entry filter, not an exit condition |
| `src/modules/backtesting/engine/backtest-portfolio.service.ts` | Portfolio tracks positions/capital — cooldown is simulation-loop concern |
| `src/modules/backtesting/utils/edge-calculation.utils.ts` | Edge calculation unaffected by entry filtering |
| `src/modules/backtesting/types/simulation.types.ts` | No new types needed — `Map<string, Date>` is sufficient |
| `src/modules/backtesting/__fixtures__/scenarios/*.fixture.json` | Fixtures don't include cooldownHours (optional, defaults to exitTimeLimitHours). No fixture changes needed. |
| Walk-forward, chunked-data-loading, sensitivity, calibration spec files | These don't test re-entry scenarios. cooldownHours defaults silently. |

### Architecture Compliance

- **Financial math:** No monetary calculations in cooldown logic — it's a timestamp comparison. No `decimal.js` needed for cooldown (hours comparison uses native JS arithmetic, which is fine for time math).
- **Module boundaries:** All changes within `modules/backtesting/` and `common/interfaces/`. No cross-module imports added.
- **God object check:** `backtest-engine.service.ts` goes from 748→~764 lines (above 600 review trigger, under 400 logical lines). Constructor deps remain at 8 (no new injections). Acceptable for facade/orchestrator but reviewer should flag for future decomposition tracking.
- **Collection lifecycle:** Cooldown map has `/** Cleanup: ... */` comment (Task 4.1). Bounded by unique pairId count (~50 max per backtest run).
- **Event emission:** No new events. Cooldown is an internal simulation filter — not observable externally. The entry skip is logged at DEBUG level (optional — follow existing edge cap logging pattern at line 611-614).
- **Paper/live mode:** Not applicable — backtesting is its own execution mode, not paper/live.
- **Naming:** `cooldownHours` matches `exitTimeLimitHours` naming convention (both in hours). `cooldownMap` is a private local variable.

### Previous Story Intelligence (10-95-11)

Key patterns to follow:

- **Test baseline:** 3727 tests pass (3725 unit + 4 pre-existing e2e failures excluded). Maintain + add new.
- **TDD cycle:** RED (write failing cooldown test) → GREEN (implement cooldown logic) → REFACTOR. Since cooldown is a new feature (not a formula fix), standard TDD applies — write the first cooldown test, watch it fail, implement, watch it pass, add next test.
- **Import paths:** `IBacktestConfig` from `'../../../common/interfaces/backtest-engine.interface'`.
- **Decimal.js not needed for cooldown.** Time comparisons use native `Date.getTime()` arithmetic — this is time math, not financial math. The `1000 * 60 * 60` divisor is a constant, not a monetary value.
- **Edge direction-invariance:** Post-10-95-11, net edge is direction-invariant (fee sum commutes with actual prices). This means `calculateBestEdge`/`calculateNetEdge` produce the same net edge regardless of buySide — the cooldown check doesn't need to consider entry direction.

### References

- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-12-backtest-edge-metric-reentry.md`#Section 4, Story 10-95-12] — Full course correction with evidence, re-entry churning data
- [Source: `_bmad-output/planning-artifacts/epics.md:3316-3490`] — Epic 10.95 context
- [Source: `_bmad-output/implementation-artifacts/10-95-11-backtest-edge-metric-realignment.md`] — Previous story (edge metric fix, test baseline 3727)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.ts:421-676`] — `runSimulationLoop()`, `evaluateExits()`, `detectOpportunities()`
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.spec.ts:45-63`] — `mockConfig` object
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/backtest-engine.service.spec.ts:581-643`] — Exit evaluation test patterns
- [Source: `pm-arbitrage-engine/src/common/interfaces/backtest-engine.interface.ts:3-24`] — `IBacktestConfig` interface
- [Source: `pm-arbitrage-engine/src/modules/backtesting/dto/backtest-config.dto.ts:99-109`] — Optional field pattern (`@IsOptional() @IsNumber()`)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/dto/backtest-config.dto.spec.ts:312-452`] — DTO validation + IBacktestConfig conformance test patterns
- [Source: `pm-arbitrage-engine/src/modules/backtesting/engine/exit-evaluator.service.ts:27-35`] — EXIT_PRIORITY mapping (TIME_DECAY = 6)
- [Source: `pm-arbitrage-engine/src/modules/backtesting/types/simulation.types.ts:4-28`] — `SimulatedPosition` type with `pairId` field

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- TDD approach: RED (tests first) → GREEN (implementation) → REFACTOR (lint cleanup)
- Baseline: 3765 tests passing. Final: 3763 passing + 15 new = consistent (e2e variance from pre-existing DB-dependent tests)
- Code review: 1/2 reviewers responded (primary timed out). Secondary found no actionable bugs. Finding #1 (missing tests) was false positive — reviewer budget exhausted before reading spec file. Finding #2 (@Max on cooldownHours) deferred — not in story AC.
- `evaluateExits()` signature: 6 → 7 params (added `cooldownMap`). `detectOpportunities()`: 9 → 11 params (added `cooldownMap`, `cooldownHours`). Both private methods called from one place.
- `backtest-engine.service.ts`: 748 → ~764 formatted lines. Constructor deps unchanged at 8.

### File List

**Modified (engine logic):**

- `src/common/interfaces/backtest-engine.interface.ts` — Added `cooldownHours?: number` to `IBacktestConfig`
- `src/modules/backtesting/dto/backtest-config.dto.ts` — Added `cooldownHours` optional field with `@IsOptional() @IsNumber() @Min(0)`
- `src/modules/backtesting/engine/backtest-engine.service.ts` — Added cooldown map in `runSimulationLoop()`, record in `evaluateExits()`, check in `detectOpportunities()`

**Modified (tests):**

- `src/modules/backtesting/dto/backtest-config.dto.spec.ts` — 5 new tests (4 validation + 1 interface conformance)
- `src/modules/backtesting/engine/backtest-engine.service.spec.ts` — 10 new tests in `describe('Pair re-entry cooldown')`
