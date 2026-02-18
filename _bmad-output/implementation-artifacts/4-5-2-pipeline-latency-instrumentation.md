# Story 4.5.2: Pipeline Latency Instrumentation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want each stage of the trading pipeline to log its execution duration,
so that I have the data foundation to identify performance bottlenecks and measure the impact of the execution lock on cycle time when connected to live platforms in Epic 5.

## Acceptance Criteria

### AC1: Per-Stage Duration Logging
**Given** `TradingEngineService.executeCycle()` runs a full detection -> risk -> execution cycle
**When** each pipeline stage completes
**Then** duration in milliseconds is logged for: data ingestion, detection, edge calculation, risk validation (per-opportunity + total), execution queue processing
**And** each stage log entry includes `correlationId`, `module: 'core'`, and `data.durationMs`

### AC2: Total Cycle Time Logged
**Given** a full execution cycle completes (success or failure)
**When** the cycle-complete log entry is emitted
**Then** total cycle time in milliseconds is included in `data.durationMs`
**And** a breakdown of per-stage durations is included in `data.stageDurations` as a flat object

### AC3: Baseline Documented from Test Cycles (Human-Review Gate)
**Given** the instrumented pipeline is running
**When** at least one full test suite run completes with instrumentation active
**Then** completion notes MUST include a table with per-stage durations from the test run
**And** the completion notes MUST name the slowest stage
**Note:** Unit test durations will be near-zero due to mocked services. This is expected. A meaningful real-world baseline requires a manual integration run against live APIs, which is deferred to Epic 5's dry-run gate. The value of AC3 is verifying the instrumentation emits correct log shape, not measuring real latency.

### AC4: Regression Baseline Maintained
**Given** the regression baseline of 495 tests across 37 test files (from Story 4.5.1)
**When** instrumentation changes are made
**Then** all existing tests continue to pass
**And** `pnpm lint` passes with zero errors

## Tasks / Subtasks

- [x] Task 1: Add per-stage timing to `executeCycle()` (AC: #1, #2)
  - [x] 1.1 Add `Date.now()` markers around each pipeline stage in `executeCycle()`
  - [x] 1.2 Instrument Stage 1: `dataIngestionService.ingestCurrentOrderBooks()` — log duration after completion
  - [x] 1.3 Instrument Stage 2: `detectionService.detectDislocations()` — log duration (detection already has internal `cycleDurationMs`, add wrapper timing for completeness)
  - [x] 1.4 Instrument Stage 2b: `edgeCalculator.processDislocations()` — log duration (already has internal `processingDurationMs`, add wrapper timing)
  - [x] 1.5 Instrument Stage 3: Risk validation loop — log total duration for all `riskManager.validatePosition()` calls plus per-opportunity count
  - [x] 1.6 Instrument Stage 4: `executionQueue.processOpportunities()` — log duration
  - [x] 1.7 Add `stageDurations` object to cycle-complete log entry containing all stage timings

- [x] Task 2: Add tests for instrumentation (AC: #1, #2, #4)
  - [x] 2.1 Add test in `trading-engine.service.spec.ts` verifying cycle-complete log includes `data.stageDurations` with expected keys
  - [x] 2.2 Add test verifying each stage logs `durationMs` in its data payload
  - [x] 2.3 Verify `durationMs` values are `typeof number` (in mocked tests, values will be 0 — this is expected; the assertion validates type correctness, not real timing)
  - [x] 2.4 Run full test suite — all 495+ tests pass

- [x] Task 3: Establish baseline (AC: #3)
  - [x] 3.1 Run full test suite with instrumentation active, capture log output showing `stageDurations` entries
  - [x] 3.2 Document a table of per-stage durations in completion notes (values will be ~0ms in mocked unit tests — this is expected and sufficient for AC3; real-world baseline deferred to Epic 5)

## Dev Notes

### Current Pipeline Structure in `executeCycle()` (~lines 47-189 of `trading-engine.service.ts`, approximate as of Story 4.5.1)

The cycle already has a top-level `Date.now()` timing (`startTime` on line 67, logged at line 170). The task is to add **per-stage** granularity. Current stages:

```
Stage 1: dataIngestionService.ingestCurrentOrderBooks()     [line 83]
Stage 2: detectionService.detectDislocations()               [line 86]
Stage 2b: edgeCalculator.processDislocations()               [line 98]
Stage 3: riskManager.validatePosition() loop                 [lines 109-146]
Stage 4: executionQueue.processOpportunities()               [lines 149-165]
```

### Implementation Approach

**DO NOT refactor `executeCycle()` into separate methods or introduce a pipeline abstraction.** The method is already well-structured with clear comments. Simply add timing markers:

```typescript
// Example pattern for each stage:
const stageStart = Date.now();
await this.dataIngestionService.ingestCurrentOrderBooks();
const ingestionDurationMs = Date.now() - stageStart;
this.logger.log({
  message: `Data ingestion completed in ${ingestionDurationMs}ms`,
  correlationId: getCorrelationId(),
  data: { stage: 'data-ingestion', durationMs: ingestionDurationMs },
});
```

For the cycle-complete log, add a `stageDurations` field:
```typescript
data: {
  cycle: 'complete',
  durationMs: duration,
  stageDurations: {
    ingestionMs,
    detectionMs,
    edgeCalculationMs,
    riskValidationMs,
    executionQueueMs,
  },
}
```

### Key Constraints

- **Use `Date.now()` not `performance.now()`** — the codebase already uses `Date.now()` for timing (line 67 of `executeCycle`, detection result's `cycleDurationMs`, edge result's `processingDurationMs`). Stay consistent.
- **Do NOT add new dependencies** — no timing libraries, no decorators, no middleware. Pure inline `Date.now()` arithmetic.
- **Do NOT modify the existing log structure** — existing logs at lines 73, 88, 100, 113, 157, 170 must remain unchanged. Add new stage-timing logs alongside them, or enhance existing ones by adding `durationMs` to their `data` fields where natural.
- **Stages with zero opportunities:** When `edgeResult.opportunities` is empty, risk validation and execution queue stages won't execute. Log `0ms` for those stages rather than omitting them — consistent shape matters for monitoring.
- **Existing internal timings:** Detection already reports `detectionResult.cycleDurationMs` and edge calculation reports `edgeResult.summary.processingDurationMs`. The wrapper timing captures wall-clock time including overhead. Both are valuable — keep both. **Clarification:** `stageDurations.detectionMs` and `stageDurations.edgeCalculationMs` reflect wrapper wall-clock time only. Internal timings (`cycleDurationMs`, `processingDurationMs`) are separate fields on their respective result objects and are NOT included in `stageDurations`.
- **Error paths:** Instrumentation covers happy-path execution only. If a stage throws, the cycle-complete log may not emit (existing error handling applies). Do NOT add try/catch around individual stages for timing — let existing error handling propagate naturally. If the cycle completes with partial execution (e.g., no opportunities found), still include all `stageDurations` keys with `0ms` for unexecuted stages.

### Correlation ID Context

All logs within `executeCycle()` already run inside `withCorrelationId()` (line 63). No additional correlation setup needed. Use `getCorrelationId()` from `common/services/correlation-context.ts`.

### Test Patterns

Existing tests in `trading-engine.service.spec.ts` use:
- `vi.spyOn(service['logger'], 'log')` to capture log output
- Mock services injected via NestJS `TestingModule`
- `expect(logSpy).toHaveBeenCalledWith(expect.objectContaining({...}))` for log assertions

For the new tests, verify `stageDurations` keys exist and values are `>= 0`:
```typescript
expect(logSpy).toHaveBeenCalledWith(
  expect.objectContaining({
    message: expect.stringContaining('Trading cycle completed'),
    data: expect.objectContaining({
      stageDurations: expect.objectContaining({
        ingestionMs: expect.any(Number),
        detectionMs: expect.any(Number),
        edgeCalculationMs: expect.any(Number),
        riskValidationMs: expect.any(Number),
        executionQueueMs: expect.any(Number),
      }),
    }),
  }),
);
```

### NFR Compliance

Architecture specifies these performance targets:
- **NFR-P1:** 500ms order book normalization
- **NFR-P2:** 1s detection cycle
- **NFR-P3:** <100ms between leg submissions

This story establishes the instrumentation to measure against these NFRs. Verification against actual targets is deferred to Epic 5's dry-run gate when connected to live platforms.

### What NOT to Do

- Do NOT create a generic timing utility, decorator, or middleware — this is a simple inline instrumentation task
- Do NOT refactor `executeCycle()` into smaller methods — the current structure is clear and adding indirection hides the pipeline flow
- Do NOT add any event emissions for timing — this is logging only, not domain events
- Do NOT modify existing test files beyond `trading-engine.service.spec.ts`
- Do NOT import `performance` from `perf_hooks` — use `Date.now()` for consistency
- Do NOT create a separate spec file — add tests to the existing `describe('executeCycle')` block

### Pre-existing Condition (from Story 4.5.0)

e2e tests make live HTTP calls to production APIs (Polymarket CLOB, Kalshi). These are fragile and may fail if external services are unavailable. This is a known issue — do not attempt to fix it in this story.

### Project Structure Notes

- Primary file to modify: `pm-arbitrage-engine/src/core/trading-engine.service.ts` (lines 47-189)
- Test file to modify: `pm-arbitrage-engine/src/core/trading-engine.service.spec.ts` (lines 103-143)
- No new files needed
- No module dependency changes
- No new imports needed (already has `Date`, `getCorrelationId`)

### References

- [Source: pm-arbitrage-engine/src/core/trading-engine.service.ts:47-189] — `executeCycle()` method with current pipeline
- [Source: pm-arbitrage-engine/src/core/trading-engine.service.spec.ts:103-143] — existing `executeCycle` tests
- [Source: pm-arbitrage-engine/src/common/services/correlation-context.ts] — `withCorrelationId`, `getCorrelationId`
- [Source: _bmad-output/planning-artifacts/architecture.md] — NFR-P1/P2/P3 performance targets, structured logging requirements
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.5.2] — Original requirements
- [Source: _bmad-output/implementation-artifacts/4-5-1-property-based-testing-financial-math-composition-chain.md] — Previous story context, 495 test baseline
- [Source: CLAUDE.md#Testing] — Co-located test pattern, Vitest framework
- [Source: CLAUDE.md#Architecture] — Logging format, correlationId requirement

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None required.

### Completion Notes List

- **Task 1:** Added per-stage `Date.now()` timing around all 5 pipeline stages in `executeCycle()`. Each stage emits a structured log with `stage`, `durationMs`, `correlationId`, and `module: 'core'`. Cycle-complete log includes `stageDurations` object with keys: `ingestionMs`, `detectionMs`, `edgeCalculationMs`, `riskValidationMs`, `executionQueueMs`. Existing logs preserved; detection/edge logs enhanced with wrapper timing alongside internal timings. When no opportunities exist, risk/execution stages still log `0ms`.
- **Task 2:** Added 3 new tests to `trading-engine.service.spec.ts` in the `executeCycle` describe block: (1) verifies `stageDurations` present with all 5 keys in cycle-complete log, (2) verifies each stage logs `durationMs` with correct stage name, (3) verifies all `durationMs` values are `typeof number` and `>= 0`. Full suite: 498 tests across 37 files — all passing. Lint clean.
- **Task 3 (AC3 Baseline):** Test suite run with instrumentation active confirms correct log shape. As expected with mocked services, all stage durations are ~0ms. Real-world baseline deferred to Epic 5 dry-run gate.

| Stage | Duration (mocked) | Notes |
|---|---|---|
| data-ingestion | ~0ms | Mocked — instant resolve |
| detection | ~0ms | Mocked — instant resolve |
| edge-calculation | ~0ms | Mocked — synchronous return |
| risk-validation | ~0ms | No opportunities in default mock |
| execution-queue | ~0ms | No approved opportunities in default mock |
| **Total cycle** | ~0ms | Mocked environment |

**Slowest stage:** N/A in mocked tests (all ~0ms). Real measurement requires live API integration (Epic 5).

### Code Review Fixes (Claude Opus 4.6)

- **H1 (Fixed):** Restored original `durationMs` field name in detection/edge logs (was renamed to `internalDurationMs`, breaking downstream consumers). Original logs now preserved unchanged; new stage-timing logs added alongside.
- **M1 (Fixed):** Restored original log message text for detection (`"Detection: N dislocations found"`) and edge calculation (`"Edge calculation: N actionable opportunities"`). New stage-timing logs use separate log calls instead of modifying existing ones.
- **M2 (Fixed):** Added `module: 'core'` to cycle-complete log for consistency with all stage logs.
- **M3 (Fixed):** Simplified test type casting in `stageDurations` test — replaced nested `Record<string, unknown>` chain with cleaner typed extraction while remaining lint-clean.

### File List

- `pm-arbitrage-engine/src/core/trading-engine.service.ts` — Modified: added per-stage timing instrumentation and `stageDurations` to cycle-complete log
- `pm-arbitrage-engine/src/core/trading-engine.service.spec.ts` — Modified: added 3 instrumentation tests
