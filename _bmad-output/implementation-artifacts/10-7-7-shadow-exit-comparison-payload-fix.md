# Story 10.7.7: Shadow Exit Comparison Event Payload Fix

Status: done

## Story

As an operator,
I want shadow exit comparison audit logs to contain actual decision data,
so that I can evaluate shadow vs. model exit performance and identify strategy improvements.

## Context

Story 10-2 introduced shadow mode — the fixed (threshold) evaluator runs as primary while the 6-criteria model evaluator runs in shadow for comparison. Each evaluation cycle emits a `ShadowComparisonEvent` (`execution.exit.shadow_comparison`). There are **979** audit log entries for this event, but key decision fields are absent from the payload — the event stores raw `fixedResult`/`modelResult` objects but lacks top-level summary fields (`shadowDecision`, `modelDecision`, `agreement`, `currentEdge`), making audit log queries for decision analysis return NULL.

**Root Cause:** The `ShadowComparisonEvent` class (Story 10.2) was designed with nested result objects but no derived decision summary fields. The audit log stores the full event via `sanitizeEventForAudit()` (JSON round-trip), so nested data IS persisted — but consumers querying for top-level decision fields get NULL because those fields don't exist. The `WsShadowComparisonPayload` WebSocket DTO and CSV trade log handler also lack these fields.

**This is NOT a serialization bug** — it's a missing-fields design gap. The fix adds derived decision summary fields to the event class and populates them at the emission point.

## Acceptance Criteria

**AC-1: Event Payload Decision Fields**
- Given the shadow comparison service evaluates a position
- When it emits the `ShadowComparisonEvent`
- Then the payload includes these NEW top-level fields:
  - `shadowDecision`: string — current system (fixed evaluator) decision. Format: `"hold"` or `"exit:<type>"` (e.g., `"exit:stop_loss"`, `"exit:take_profit"`)
  - `modelDecision`: string — model (6-criteria) evaluator decision. Format: `"hold"` or `"exit:<criterion>"` (e.g., `"exit:edge_evaporation"`)
  - `agreement`: boolean — `fixedResult.triggered === modelResult.triggered`. Agreement means both trigger OR both hold. If both trigger with different exit types (e.g., fixed=`stop_loss`, model=`edge_evaporation`), agreement is still `true` — type-level differences are captured in `divergenceDetail` for informational analysis only.
  - `currentEdge`: string — current edge at evaluation time (Decimal serialized via `.toFixed(8)`)
- And existing fields (`positionId`, `pairId`, `fixedResult`, `modelResult`, `timestamp`) remain unchanged (backward-compatible)
- And no new fields are null when the comparison completes

**AC-2: Divergence Detail on Disagreement**
- Given shadow (fixed) and model evaluators disagree (`agreement === false`)
- When the comparison event is emitted
- Then a `divergenceDetail` object is included with:
  - `triggeredCriteria`: array of criterion names that triggered (from modelResult.criteria where `triggered === true`)
  - `proximityValues`: record of criterion → proximity string (via `.toFixed(8)`) for ALL 6 criteria. Keys match the `criterion` field values exactly (e.g., `"edge_evaporation"`, `"model_confidence"`)
  - `fixedType`: the fixed evaluator's exit type (or `null` if not triggered)
  - `modelType`: the model evaluator's exit type (or `null` if not triggered)
- Given they agree (`agreement === true`)
- Then `divergenceDetail` is `null`

**AC-3: WebSocket Payload Update**
- Given a shadow comparison event is broadcast via WebSocket
- When the dashboard gateway forwards it
- Then `WsShadowComparisonPayload` includes: `shadowDecision`, `modelDecision`, `agreement`, `currentEdge`
- And the dashboard SPA receives these fields without frontend code changes (it renders raw event data)

**AC-4: CSV Trade Log Update**
- Given a shadow comparison event is logged to CSV trade log
- When `buildTradeLogRecord` handles `SHADOW_COMPARISON`
- Then the `edge` field is populated from `currentEdge` (currently `'N/A'`)
- And the `side` field includes agreement status: `"shadow_comparison:agree"` or `"shadow_comparison:disagree"`

**AC-5: ShadowComparisonService Payload Update**
- Given the `ShadowComparisonService` receives the updated event
- When it normalizes and accumulates the comparison
- Then `ShadowComparisonPayload` interface includes `agreement` and `currentEdge`
- And the daily summary calculation can use `agreement` for aggregate agree/disagree counts

**AC-6: Audit Log Queryability**
- Given the updated events are stored in audit logs
- When querying `audit_log` WHERE `event_type = 'execution.exit.shadow_comparison'`
- Then `details->>'shadowDecision'`, `details->>'modelDecision'`, `details->>'agreement'`, `details->>'currentEdge'` return non-null values
- And `details->'divergenceDetail'` is non-null only when `details->>'agreement' = 'false'`

## Tasks / Subtasks

- [x] Task 1: Update `ShadowComparisonEvent` class with decision fields (AC: #1, #2)
  - [x] 1.1 `src/common/events/execution.events.ts` — Add constructor params to `ShadowComparisonEvent`:
    - `public readonly shadowDecision: string` — derived: `fixedResult.triggered ? \`exit:${fixedResult.type}\` : 'hold'`
    - `public readonly modelDecision: string` — derived: `modelResult.triggered ? \`exit:${modelResult.type}\` : 'hold'`
    - `public readonly agreement: boolean` — `fixedResult.triggered === modelResult.triggered`
    - `public readonly currentEdge: string` — `evalResult.currentEdge.toFixed(8)`
    - `public readonly divergenceDetail: DivergenceDetail | null`
  - [x] 1.2 Same file — Define `DivergenceDetail` interface (exported):
    ```typescript
    export interface DivergenceDetail {
      triggeredCriteria: string[];
      proximityValues: Record<string, string>;
      fixedType: string | null;
      modelType: string | null;
    }
    ```
  - [x] 1.3 `src/common/events/execution.events.spec.ts` — Tests (use `expect.objectContaining({...})` for all payload assertions):
    - Event serializes all new fields via `JSON.parse(JSON.stringify(event))`
    - `divergenceDetail` is null when `agreement === true`
    - `divergenceDetail` is populated when `agreement === false`
    - Decision string format: `"hold"` vs `"exit:<type>"` for both evaluators
    - Type undefined but triggered: decision string is `"exit:unknown"`

  **Full constructor signature after changes:**
  ```typescript
  constructor(
    public readonly positionId: PositionId,
    public readonly pairId: PairId,
    public readonly fixedResult: { triggered: boolean; type?: string; currentPnl: string },
    public readonly modelResult: { triggered: boolean; type?: string; currentPnl: string; criteria: Array<{...}> },
    public readonly timestamp: Date,
    // ── New fields (appended after existing) ──
    public readonly shadowDecision: string,
    public readonly modelDecision: string,
    public readonly agreement: boolean,
    public readonly currentEdge: string,
    public readonly divergenceDetail: DivergenceDetail | null,
    correlationId?: string,
  )
  ```

- [x] Task 2: Update emission point in ExitMonitorService (AC: #1, #2)
  - [x] 2.1 `src/modules/exit-management/exit-monitor.service.ts` — At the shadow comparison emission block (~line 779-802), compute and pass new fields:
    - `shadowDecision`: derive from `evalResult.triggered` and `evalResult.type`
    - `modelDecision`: derive from `evalResult.shadowModelResult.triggered` and `evalResult.shadowModelResult.type`
    - `agreement`: `evalResult.triggered === evalResult.shadowModelResult.triggered`
    - `currentEdge`: `evalResult.currentEdge.toFixed(8)`
    - `divergenceDetail`: when `!agreement`, build from `evalResult.criteria` (criterion names, proximity values, types); when agreement, pass `null`. **Defensive fallback:** if `evalResult.criteria` is undefined or empty, set `triggeredCriteria: []` and `proximityValues: {}` in divergenceDetail (don't skip it — the `fixedType`/`modelType` still carry value)
  - [x] 2.2 `src/modules/exit-management/exit-monitor-shadow-emission.spec.ts` — Tests (use `expect.objectContaining({...})` for event payload verification, never bare `toHaveBeenCalledWith(new ShadowComparisonEvent(...))`):
    - Emitted event contains `shadowDecision`, `modelDecision`, `agreement`, `currentEdge` with correct values
    - Both-trigger scenario: `agreement === true`, both decisions are `"exit:<type>"`
    - Both-hold scenario: `agreement === true`, both decisions are `"hold"`
    - Fixed-triggers-model-holds scenario: `agreement === false`, `divergenceDetail` populated with model criteria
    - Model-triggers-fixed-holds scenario: `agreement === false`, `divergenceDetail` populated
    - `currentEdge` matches `evalResult.currentEdge.toFixed(8)`

- [x] Task 3: Update `ShadowComparisonPayload` interface and handler (AC: #5)
  - [x] 3.1 `src/modules/exit-management/shadow-comparison.service.ts` — Update `ShadowComparisonPayload` interface:
    - Add `agreement: boolean`
    - Add `currentEdge: Decimal`
    - Add `divergenceDetail: { triggeredCriteria: string[]; proximityValues: Record<string, string>; fixedType: string | null; modelType: string | null } | null`
  - [x] 3.2 Same file — Update `handleShadowComparison()` normalization block to extract new fields from event, converting `currentEdge` string → `Decimal`
  - [x] 3.3 `src/modules/exit-management/shadow-comparison.service.spec.ts` — Update `makeShadowEvent` helper with new fields; add tests:
    - Normalized payload includes `agreement` and `currentEdge`
    - Agreement aggregation: count agree vs disagree in daily buffer

- [x] Task 4: Update WebSocket payload (AC: #3)
  - [x] 4.1 `src/dashboard/dto/ws-events.dto.ts` — Add to `WsShadowComparisonPayload`:
    - `shadowDecision: string`
    - `modelDecision: string`
    - `agreement: boolean`
    - `currentEdge: string`
  - [x] 4.2 `src/dashboard/dashboard.gateway.ts` — Update `handleShadowComparison()` broadcast data (~line 220-227) to include new fields from event
  - [x] 4.3 `src/dashboard/dashboard.gateway.spec.ts` — Test: broadcast includes new fields with correct values

- [x] Task 5: Update CSV trade log handler (AC: #4)
  - [x] 5.1 `src/modules/monitoring/event-consumer.service.ts` — Update `buildTradeLogRecord` for `SHADOW_COMPARISON` case (~line 367-388):
    - Set `edge` to `this.str(e['currentEdge'], 'N/A')` instead of `'N/A'`
    - Set `side` to `` `shadow_comparison:${e['agreement'] ? 'agree' : 'disagree'}` ``
  - [x] 5.2 `src/modules/monitoring/event-consumer.service.spec.ts` — Tests:
    - Trade log record has `edge` populated from `currentEdge`
    - Trade log record `side` is `"shadow_comparison:agree"` when agreement is true
    - Trade log record `side` is `"shadow_comparison:disagree"` when agreement is false

- [x] Task 6: Audit log queryability verification (AC: #6)
  - [x] 6.1 Add integration-style test in `src/modules/monitoring/event-consumer.service.spec.ts`:
    - Emit a `ShadowComparisonEvent` with new fields through `sanitizeEventForAudit()`
    - Verify JSON output has top-level `shadowDecision`, `modelDecision`, `agreement`, `currentEdge` keys
    - Verify `divergenceDetail` is non-null only when `agreement === false`

## Dev Notes

### Architecture & Naming Convention

**Field naming rationale (matches epic AC exactly):**
- `shadowDecision` = the fixed/threshold evaluator's decision (the established baseline). In `EXIT_MODE=shadow`, fixed is primary — it's the "shadow" baseline being compared against.
- `modelDecision` = the 6-criteria model evaluator's decision (the new model being tested in shadow mode).

**Decision string format:** `"hold"` when `triggered === false`, `"exit:<type>"` when `triggered === true`. Type comes from `evalResult.type` (fixed) or `evalResult.shadowModelResult.type` (model). If type is undefined but triggered is true, use `"exit:unknown"`.

### Key Source Files

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `src/common/events/execution.events.ts:124-150` | `ShadowComparisonEvent` class — ADD new constructor params | Current 6 params → 11 params |
| `src/modules/exit-management/exit-monitor.service.ts:772-803` | Emission point — COMPUTE and PASS new fields | `evalResult.currentEdge`, `evalResult.shadowModelResult` |
| `src/modules/exit-management/threshold-evaluator.service.ts:84-103` | `ThresholdEvalResult` — READ ONLY, understand available data | `currentEdge`, `shadowModelResult`, `criteria` |
| `src/modules/exit-management/shadow-comparison.service.ts:12-32` | `ShadowComparisonPayload` interface — UPDATE | Add `agreement`, `currentEdge`, `divergenceDetail` |
| `src/modules/exit-management/shadow-comparison.service.ts:78-132` | `handleShadowComparison()` — UPDATE normalization | Extract new fields |
| `src/dashboard/dto/ws-events.dto.ts:83-90` | `WsShadowComparisonPayload` — ADD 4 fields | |
| `src/dashboard/dashboard.gateway.ts:216-228` | WS broadcast — ADD new fields to data object | |
| `src/modules/monitoring/event-consumer.service.ts:367-388` | CSV trade log — UPDATE `edge` and `side` | |

### Data Available at Emission Point

At `exit-monitor.service.ts:779`, these values are in scope:
```typescript
evalResult.triggered          // boolean — fixed evaluator triggered?
evalResult.type               // string | undefined — fixed evaluator exit type
evalResult.currentEdge        // Decimal — current edge
evalResult.currentPnl         // Decimal — current P&L
evalResult.shadowModelResult  // { triggered, type?, currentPnl, criteria? }
evalResult.criteria           // CriterionResult[] — 6-criteria details
// CriterionResult = { criterion: string, proximity: Decimal, triggered: boolean, detail?: string }
```

### Reuse — DO NOT Reinvent

- **`ShadowComparisonEvent` class** — Extend it, don't replace it. Add new params AFTER existing ones to maintain backward-compatible construction order. Existing `fixedResult` and `modelResult` remain for downstream consumers.
- **`sanitizeEventForAudit()`** — No changes needed. It uses `JSON.parse(JSON.stringify(event))` which automatically serializes all public properties including new ones.
- **`CriterionResult` type** — Already defined in `src/modules/exit-management/threshold-evaluator.service.ts` (exported). Import from there if needed for type safety in proximity/criterion extraction: `import { CriterionResult } from './threshold-evaluator.service';`
- **Decimal serialization** — Use `.toFixed(8)` for all Decimal-to-string conversions in the event (matches existing pattern in `fixedResult.currentPnl` and `modelResult.currentPnl`).

### DO NOT Touch

- **ThresholdEvalResult interface** — Read-only reference. The evaluation logic is unchanged.
- **Threshold evaluator logic** — No changes to how decisions are made, only how they're reported.
- **`audit-log.service.ts`** — The audit trail stores whatever `sanitizeEventForAudit` returns. No schema changes needed.
- **Prisma schema** — `AuditLog.details` is `Json` type. No migration needed.
- **`risk-manager.service.ts`** — God Object, untouchable (10-8-1 decomposition pending).
- **`exit-monitor.service.ts` evaluation logic** — Only touch the emission block (lines 772-803). Do not alter how `evalResult` is computed.

### Test Patterns (from 10-7-6)

- Mock EventEmitter2 with `{ emit: vi.fn(), on: vi.fn() }` for unit tests
- Use `expect.objectContaining({...})` for event payload verification (never bare `toHaveBeenCalled()`)
- Use `expectEventHandled()` from `src/common/testing/expect-event-handled.ts` for event wiring verification
- Co-locate test files: `shadow-comparison.service.spec.ts` next to service, `execution.events.spec.ts` next to events
- For exit-monitor shadow tests, check which spec file covers shadow emission — likely `exit-monitor-core.spec.ts` or similar

### Backward Compatibility

New constructor params are appended AFTER existing ones. All existing call sites pass the same arguments in the same order. The new fields are mandatory (no defaults) — the single emission point in `exit-monitor.service.ts` is the only place constructing this event, so only one call site needs updating.

### Financial Math

- `currentEdge` is serialized as string via `.toFixed(8)` at emission, converted back to `Decimal` in `ShadowComparisonService` handler — follows established pattern for `currentPnl`.
- No new financial calculations — just passing through existing `evalResult.currentEdge`.

### Project Structure Notes

- No new files created — only modifications to existing files
- No new modules, no new DI tokens, no config changes
- No Prisma migration needed (audit log `details` is untyped JSON)
- Dashboard SPA renders raw WS data — no frontend changes needed

### References

- [Source: src/common/events/execution.events.ts#ShadowComparisonEvent] — Event class to modify
- [Source: src/modules/exit-management/exit-monitor.service.ts#L772-L803] — Single emission point
- [Source: src/modules/exit-management/threshold-evaluator.service.ts#ThresholdEvalResult] — Available data at emission
- [Source: src/modules/exit-management/shadow-comparison.service.ts#ShadowComparisonPayload] — Consumer interface
- [Source: src/modules/monitoring/event-consumer.service.ts#L367-L388] — CSV trade log handler
- [Source: src/dashboard/dto/ws-events.dto.ts#WsShadowComparisonPayload] — WS DTO
- [Source: src/dashboard/dashboard.gateway.ts#L216-L228] — WS broadcast

### Previous Story Intelligence (10-7-6)

- Config pipeline NOT needed for this story (no new settings)
- Test count at end of 10-7-6: 2776 tests passing
- Code review findings to avoid: NaN guards on numeric conversions, ensure `Decimal` serialization consistency
- Event emission pattern: emit via `this.eventEmitter.emit(EVENT_NAMES.X, new XEvent(...))` — same pattern applies here

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Task 1: Added `DivergenceDetail` interface and 5 new constructor params to `ShadowComparisonEvent`. 8 tests (serialize, divergence null/populated, decision formats, backward compat, catalog).
- Task 2: Updated shadow comparison emission block in `exit-monitor.service.ts` to compute and pass `shadowDecision`, `modelDecision`, `agreement`, `currentEdge`, `divergenceDetail`. 6 tests covering all agree/disagree scenarios.
- Task 3: Extended `ShadowComparisonPayload` with `agreement`, `currentEdge`, `divergenceDetail`. Updated normalization in `handleShadowComparison()`. Added `agreeCount`/`disagreeCount` to `DailySummary`. 3 new tests.
- Task 4: Added 4 fields to `WsShadowComparisonPayload` DTO and gateway broadcast. 1 test.
- Task 5: Updated CSV trade log `buildTradeLogRecord` for SHADOW_COMPARISON: `edge` from `currentEdge`, `side` includes agree/disagree. 3 tests.
- Task 6: Added 2 integration tests verifying `sanitizeEventForAudit()` produces top-level queryable fields.

**Total: 23 new tests. 2776 → 2799 all passing. 0 lint errors.**
- Code Review Fix (P-1): Imported canonical `DivergenceDetail` type in `shadow-comparison.service.ts`, replaced 2 inline structural duplicates.
- Code Review Fix (BS-1): Propagated `agreeCount`/`disagreeCount` through full daily summary chain: `ShadowDailySummaryEvent` constructor → `emitDailySummary()` → `WsShadowDailySummaryPayload` DTO → gateway broadcast → Telegram formatter (with agreement rate %). 1 new test.

**Post-review total: 24 new tests. 2776 → 2800 all passing. 0 lint errors.**

### File List

- `src/common/events/execution.events.ts` — Added `DivergenceDetail` interface, extended `ShadowComparisonEvent` constructor
- `src/common/events/execution.events.spec.ts` — 8 new tests for `ShadowComparisonEvent`
- `src/modules/exit-management/exit-monitor.service.ts` — Updated shadow emission block with new field computation
- `src/modules/exit-management/exit-monitor-shadow-emission.spec.ts` — NEW: 6 tests for shadow emission
- `src/modules/exit-management/shadow-comparison.service.ts` — Extended `ShadowComparisonPayload`, normalization, `DailySummary`
- `src/modules/exit-management/shadow-comparison.service.spec.ts` — 3 new tests, updated `makeShadowEvent` helper
- `src/dashboard/dto/ws-events.dto.ts` — Added 4 fields to `WsShadowComparisonPayload`
- `src/dashboard/dashboard.gateway.ts` — Updated broadcast with new fields
- `src/dashboard/dashboard.gateway.spec.ts` — 1 new test for shadow broadcast
- `src/modules/monitoring/event-consumer.service.ts` — Updated CSV trade log `side` and `edge`
- `src/modules/monitoring/event-consumer.service.spec.ts` — 5 new tests (3 CSV + 2 audit)
- `src/modules/monitoring/formatters/telegram-message.formatter.ts` — Added `agreeCount`/`disagreeCount` to `formatShadowDailySummary` (code review fix BS-1)

### Change Log

- 2026-03-24: Story 10.7.7 implemented. Added decision summary fields (shadowDecision, modelDecision, agreement, currentEdge, divergenceDetail) to ShadowComparisonEvent and all downstream consumers (ShadowComparisonService, WebSocket, CSV trade log, audit log). 23 new tests, all 2799 tests pass.
- 2026-03-24: Code review completed. 3-layer adversarial (Blind Hunter + Edge Case Hunter + Acceptance Auditor), 22 raw findings triaged to 1 patch + 1 bad-spec + 20 reject. Fixed both actionable items: P1 imported canonical DivergenceDetail type (eliminated 3-location duplication), BS1 propagated agreeCount/disagreeCount through ShadowDailySummaryEvent → WS DTO → gateway → Telegram formatter. All 2800 tests pass.
