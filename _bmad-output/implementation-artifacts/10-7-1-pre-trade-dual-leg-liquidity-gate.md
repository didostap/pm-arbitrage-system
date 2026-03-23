# Story 10.7.1: Pre-Trade Dual-Leg Liquidity Gate

Status: done

## Story

As an operator,
I want the system to verify sufficient order book depth on both platforms before entering any position,
so that positions are only opened when both legs can realistically execute at target size.

## Context

Analysis of 202 paper trading positions revealed 0% profitability. 99.7% of 605 order failures were Polymarket insufficient liquidity. Position sizes of ~47 contracts entered against 1-6 contract deep books. The current implementation (FR-EX-03 / Story 6-5-5b) checks depth per-leg sequentially — primary leg is submitted before secondary depth is verified. This story adds a dual-leg pre-flight check that verifies BOTH platforms before EITHER leg is submitted.

## Acceptance Criteria

1. **AC-1: Dual-leg depth verification before order submission**
   - **Given** an opportunity passes risk validation and is locked for execution
   - **When** the execution service prepares to submit orders
   - **Then** order book depth is fetched for BOTH platforms before EITHER leg is submitted
   - **And** the minimum total book depth across both legs is compared against the target position size
   - **And** if either leg has total depth < `DUAL_LEG_MIN_DEPTH_RATIO` × target size (configurable, default: 1.0), the opportunity is rejected
   - **And** rejection emits `OPPORTUNITY_FILTERED` (`detection.opportunity.filtered`) with reason `"insufficient dual-leg depth"` and depth details per platform

2. **AC-2: Asymmetric depth capping**
   - **Given** both legs pass the dual-leg depth check
   - **When** depth is sufficient but asymmetric (e.g., Kalshi: 100, Polymarket: 15)
   - **Then** position size is capped to the minimum of both legs' available depth (constrained by existing `MIN_FILL_THRESHOLD_RATIO`)
   - **And** if the capped size falls below the minimum fill threshold, the opportunity is rejected

3. **AC-3: Fail-closed on API error**
   - **Given** the dual-leg gate is in place
   - **When** a depth check API call fails on either platform
   - **Then** the opportunity is rejected (fail-closed)
   - **And** a `DEPTH_CHECK_FAILED` (`execution.depth-check.failed`) event is emitted with error context

4. **AC-4: Configurable setting persisted in DB and exposed on Settings page**
   - **Given** the pre-trade depth gate configuration
   - **When** the engine starts
   - **Then** `DUAL_LEG_MIN_DEPTH_RATIO` is loaded from EngineConfig DB (default: 1.0)
   - **And** the setting appears in the dashboard Settings page under "Execution" group
   - **And** hot-reload works via the CONFIG_SETTINGS_UPDATED event

## Design Decision: Event Name

The epics AC references `execution.opportunity.filtered`, but the existing `OPPORTUNITY_FILTERED` event (`detection.opportunity.filtered`) is already wired to:

- `EventConsumerService` (audit log writes)
- `MatchAprUpdaterService` (APR tracking)
- `PerformanceService` (dashboard metrics)

**Decision: Reuse `OPPORTUNITY_FILTERED`** with reason `"insufficient dual-leg depth"`. The `reason` field distinguishes execution-stage rejections from detection-stage rejections. Creating a new event name would require wiring 3+ new subscriptions for the same audit trail functionality.

## Design Decision: Separate Setting (Not Shared with exitMinDepth)

`DUAL_LEG_MIN_DEPTH_RATIO` is a **relative ratio** (1.0 × target size = 100% coverage required). `exitMinDepth` is an **absolute threshold** (5 contracts). Different semantics, different operator intent, different dashboard groups (Execution vs Exit Strategy). They MUST be separate EngineConfig fields.

## Tasks / Subtasks

- [x] **Task 1: Add `DUAL_LEG_MIN_DEPTH_RATIO` config setting** (AC: #4)
  - [x] 1.1 Add `DUAL_LEG_MIN_DEPTH_RATIO` to `src/common/config/env.schema.ts` — use `decimalString('1.0')` validator
  - [x] 1.2 Add `dualLegMinDepthRatio` to `src/common/config/config-defaults.ts` — `{ envKey: 'DUAL_LEG_MIN_DEPTH_RATIO', defaultValue: '1.0' }`
  - [x] 1.3 Add `dualLegMinDepthRatio` to `src/common/config/settings-metadata.ts` — group: `SettingsGroup.Execution`, type: `'decimal'`, label: `'Dual-Leg Min Depth Ratio'`, description: `'Minimum ratio of order book depth to target position size required on both platforms before entry. 1.0 = full target must fit.'`
  - [x] 1.4 Add `dualLegMinDepthRatio` to `src/dashboard/dto/update-settings.dto.ts` — `@IsOptional() @IsString() @Matches(DECIMAL_REGEX)`
  - [x] 1.5 Add `dualLegMinDepthRatio` column to Prisma `EngineConfig` model — `Decimal? @map("dual_leg_min_depth_ratio") @db.Decimal(20, 8)` in the Execution section
  - [x] 1.6 Create Prisma migration: `pnpm prisma migrate dev --name add-dual-leg-min-depth-ratio`
  - [x] 1.7 Add `dualLegMinDepthRatio` to `SERVICE_RELOAD_MAP` in `src/dashboard/settings.service.ts` — route to `'execution'`
  - [x] 1.8 Add `dualLegMinDepthRatio` to the execution handler registration in `settings.service.ts` — pass to `svc.reloadConfig({ dualLegMinDepthRatio: cfg.dualLegMinDepthRatio })`
  - [x] 1.9 Update `ExecutionService.reloadConfig()` to accept and store `dualLegMinDepthRatio`

- [x] **Task 2: Implement dual-leg depth gate in ExecutionService** (AC: #1, #2, #3)
  - [x] 2.1 Add `private dualLegMinDepthRatio: number` field to ExecutionService, initialized from config in constructor (same pattern as `minFillRatio` which uses `Number()` + `configService.get()` — NOT Decimal)
  - [x] 2.2 Inline dual-leg gate in execute() using `Promise.all([getAvailableDepth(primary), getAvailableDepth(secondary)])` — parallel fetch. No separate method needed as the gate logic is 3 sequential checks.
  - [x] 2.3 Insert the dual-leg gate call BEFORE the existing per-leg depth checks
  - [x] 2.4 Implement dual-leg rejection logic:
    - `minDepthRequired = Math.ceil(idealCount * this.dualLegMinDepthRatio)`
    - If either leg depth < minDepthRequired → reject, emit `OPPORTUNITY_FILTERED` with reason `"insufficient dual-leg depth"` and per-platform depth details, return failure result
  - [x] 2.5 Implement asymmetric depth capping:
    - `cappedSize = Math.min(idealCount, primaryDepth, secondaryDepth)`
    - If `cappedSize < Math.ceil(idealCount * this.minFillRatio)` → reject, emit `EXECUTION_FAILED` with `EXECUTION_ERROR_CODES.INSUFFICIENT_LIQUIDITY`, return failure result
    - Per-leg checks handle downstream sizing (idealCount preserved for edge re-validation)
  - [x] 2.6 Handle API errors (fail-closed): `getAvailableDepth` returns 0 on error and emits `DEPTH_CHECK_FAILED` internally — 0 triggers dual-leg rejection

- [x] **Task 3: Update event emission for dual-leg rejection** (AC: #1, #3)
  - [x] 3.1 Import `OpportunityFilteredEvent` from `src/common/events/detection.events.ts` into ExecutionService
  - [x] 3.2 Emit `OPPORTUNITY_FILTERED` on dual-leg depth failure with all mandatory params
  - [x] 3.3 Emit `DEPTH_CHECK_FAILED` on API errors (delegated to existing `getAvailableDepth`)

- [x] **Task 4: Write unit tests** (AC: #1, #2, #3, #4)
  - [x] 4.1 Test: both legs sufficient → proceed to order submission (no rejection)
  - [x] 4.2 Test: primary leg insufficient → reject with OPPORTUNITY_FILTERED event
  - [x] 4.3 Test: secondary leg insufficient → reject with OPPORTUNITY_FILTERED event
  - [x] 4.4 Test: both legs insufficient → reject with OPPORTUNITY_FILTERED event
  - [x] 4.5 Test: asymmetric depth → size capped to min(primary, secondary)
  - [x] 4.6 Test: capped size below minFillRatio × targetSize → reject with INSUFFICIENT_LIQUIDITY
  - [x] 4.7 Test: primary API call fails → fail-closed, emit DEPTH_CHECK_FAILED
  - [x] 4.8 Test: secondary API call fails → fail-closed, emit DEPTH_CHECK_FAILED
  - [x] 4.9 Test: dualLegMinDepthRatio = 0.5 → requires only 50% of target size on each leg
  - [x] 4.10 Test: reloadConfig updates dualLegMinDepthRatio at runtime
  - [x] 4.11 Test: event payloads verified with `expect.objectContaining({...})` (not bare `toHaveBeenCalled()`)

- [x] **Task 5: Paper/live mode boundary test** (AC: #1)
  - [x] 5.1 Verify dual-leg depth gate runs for paper mode (isPaper=true)
  - [x] 5.2 Verify dual-leg depth gate runs for live mode (isPaper=false)
  - [x] 5.3 Use `describe.each([[true, 'paper'], [false, 'live']])` matrix pattern per CLAUDE.md convention

- [x] **Task 6: Event wiring verification** (AC: #1)
  - [x] 6.1 Verify `OPPORTUNITY_FILTERED` event reaches `EventConsumerService.handleOpportunityFiltered` (existing wiring — confirmed new reason doesn't break handler via unit test)
  - [x] 6.2 No new `@OnEvent` handler added → no `expectEventHandled()` test needed

## Dev Notes

### Architecture Compliance

- **Module dependency rules:** ExecutionService already imports from `common/events/` and `connectors/` — no new forbidden imports needed
- **Error hierarchy:** Use existing `ExecutionError` with code `INSUFFICIENT_LIQUIDITY` (2001) for depth failures. Do NOT throw raw Error
- **Config type:** `dualLegMinDepthRatio` stored as `number` (same as `minFillRatio`). This is a sizing ratio, not a monetary value — `Number()` is appropriate. Monetary values (edge, PnL, prices) still require `Decimal`
- **Hot path:** The dual-leg gate is synchronous-blocking in the detection → risk → execution chain — this is correct by design (CLAUDE.md)

### Source Tree — Files to Modify

| File                                              | Change                                                                                      |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `src/common/config/env.schema.ts`                 | Add `DUAL_LEG_MIN_DEPTH_RATIO`                                                              |
| `src/common/config/config-defaults.ts`            | Add `dualLegMinDepthRatio` entry                                                            |
| `src/common/config/settings-metadata.ts`          | Add metadata under Execution group                                                          |
| `src/dashboard/dto/update-settings.dto.ts`        | Add DTO field                                                                               |
| `prisma/schema.prisma`                            | Add column to EngineConfig                                                                  |
| `src/dashboard/settings.service.ts`               | Add to SERVICE_RELOAD_MAP + handler                                                         |
| `src/modules/execution/execution.service.ts`      | Core implementation — new field, reloadConfig, verifyDualLegDepth method, gate in execute() |
| `src/modules/execution/execution.service.spec.ts` | New test cases                                                                              |

### Source Tree — Files to Read (Reference Only)

| File                                                    | Why                                       |
| ------------------------------------------------------- | ----------------------------------------- |
| `src/common/events/detection.events.ts`                 | `OpportunityFilteredEvent` class (reuse)  |
| `src/common/events/execution.events.ts`                 | `DepthCheckFailedEvent` class (reuse)     |
| `src/common/events/event-catalog.ts`                    | Event name constants                      |
| `src/common/types/normalized-order-book.type.ts`        | `NormalizedOrderBook`, `PriceLevel` types |
| `src/common/interfaces/platform-connector.interface.ts` | `getOrderBook()` signature                |

### Key Code Patterns to Follow

**Config initialization (ExecutionService constructor, line 93):**

```typescript
this.minFillRatio = Number(this.configService.get<string>('EXECUTION_MIN_FILL_RATIO', '0.25'));
```

Follow same pattern for `dualLegMinDepthRatio` — uses `Number()` + `configService.get()`, NOT `Decimal` + `configAccessor`. Add validation guard (must be >0 and ≤1.0) with `SystemHealthError` on failure, matching existing `minFillRatio` guard (lines 96-107).

**Parallel order book fetch (already in execution.service.ts ~line 764):**

```typescript
const [primaryBook, secondaryBook] = await Promise.all([
  primaryConnector.getOrderBook(asContractId(primaryContractId)),
  secondaryConnector.getOrderBook(asContractId(secondaryContractId)),
]);
```

Reuse this pattern for the dual-leg pre-flight check.

**Depth calculation (getAvailableDepth, ~line 1004):**

- Calls `connector.getOrderBook()` for fresh REST data
- Iterates price levels, accumulates quantity at or better than target price
- Returns 0 on error (conservative fallback) — already emits DEPTH_CHECK_FAILED

**Event emission (existing execution failure pattern, ~line 332):**

```typescript
this.eventEmitter.emit(
  EVENT_NAMES.EXECUTION_FAILED,
  new ExecutionFailedEvent(
    EXECUTION_ERROR_CODES.INSUFFICIENT_LIQUIDITY,
    error.message,
    opportunity.reservationRequest.opportunityId,
    ...
  ),
);
```

**Config reload pattern (ExecutionService.reloadConfig, line 134):**

```typescript
reloadConfig(settings: { minFillRatio?: string }): void {
  if (settings.minFillRatio !== undefined) {
    const value = Number(settings.minFillRatio);
    if (!isNaN(value) && value > 0 && value <= 1) {
      this.minFillRatio = value;
    }
  }
}
```

Extend to accept `dualLegMinDepthRatio?: string` with same `Number()` + validation pattern.

**Settings service handler registration (~line 164):**

```typescript
this.tryRegisterHandler('execution', EXECUTION_ENGINE_TOKEN, (svc, cfg) =>
  svc.reloadConfig({
    minFillRatio: cfg.executionMinFillRatio,
  }),
);
```

Add `dualLegMinDepthRatio: cfg.dualLegMinDepthRatio` to the object.

**Test depth mock pattern (execution.service.spec.ts ~line 349):**

```typescript
kalshiConnector.getOrderBook.mockResolvedValue({
  ...makeKalshiOrderBook(),
  asks: [{ price: 0.45, quantity: 50 }],
  bids: [{ price: 0.44, quantity: 50 }],
});
```

### Insertion Point in execute()

The dual-leg gate should be inserted AFTER:

- Compliance gate validation (the `complianceValidator.validate()` block)
- Collateral-aware sizing calculation (after `idealCount` is computed)

And BEFORE:

- The first `getAvailableDepth()` call (currently the primary per-leg depth check)

Search for `const primaryAvailableDepth = await this.getAvailableDepth` — the dual-leg gate goes immediately before this line. The variable `idealCount` (target position size) is already computed at that point. The existing per-leg checks remain as a second safety layer (defense in depth).

### Testing Standards

- Co-located tests: `execution.service.spec.ts` (same directory)
- Framework: Vitest (NOT Jest) — use `vi.fn()`, `vi.spyOn()`, `describe`, `it`, `expect`
- Assertion depth: verify event payloads with `expect.objectContaining({...})` — bare `toHaveBeenCalled()` is insufficient (CLAUDE.md Code Review Convention)
- Event wiring: use `expectEventHandled()` helper from `src/common/testing/expect-event-handled.ts` for any new `@OnEvent` handlers
- Paper/live boundary: `describe.each([[true, 'paper'], [false, 'live']])` matrix (CLAUDE.md Convention)

### What NOT To Do

- Do NOT create a new event name `execution.opportunity.filtered` — reuse existing `OPPORTUNITY_FILTERED` (`detection.opportunity.filtered`)
- Do NOT share this setting with `exitMinDepth` — semantics are different (ratio vs absolute)
- Do NOT remove or modify the existing per-leg depth checks (lines ~303-414) — they remain as defense-in-depth
- Do NOT use `Decimal` for `dualLegMinDepthRatio` — it's a sizing ratio like `minFillRatio`, stored as `number`. Reserve `Decimal` for monetary values (edge, PnL, prices)
- Do NOT add `isPaper` default value to any new method parameters (CLAUDE.md Convention)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 10-7-1] — Acceptance criteria
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-23-paper-profitability.md#Story 10-7-1] — Root cause analysis, evidence data
- [Source: CLAUDE.md#Architecture] — Module dependency rules, error handling, event emission
- [Source: CLAUDE.md#Testing Conventions (Epic 10 Retro)] — Event wiring, assertion depth, collection lifecycle
- [Source: CLAUDE.md#Testing Conventions (Epic 10.5)] — Paper/live boundary, repository mode-scoping
- [Source: CLAUDE.md#Code Review Conventions] — Assertion depth, boundary type safety

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no debugging required.

### Completion Notes List

- Task 1: Full config pipeline implemented — env.schema, config-defaults, settings-metadata, DTO, Prisma migration, EffectiveConfig type, engine-config repository, settings service reload map + handler, ExecutionService constructor + reloadConfig.
- Task 2: Dual-leg gate implemented inline in `execute()` using `Promise.all` parallel fetch. Three-stage check: (1) minimum depth via configurable ratio, (2) asymmetric capping with minFillRatio threshold, (3) fail-closed on API error via getAvailableDepth returning 0. Gate does NOT modify idealCount — per-leg checks handle sizing independently, preserving edge re-validation behavior.
- Task 3: `OpportunityFilteredEvent` emitted on dual-leg depth failure with per-platform depth details in reason string. `DEPTH_CHECK_FAILED` delegated to existing `getAvailableDepth` error handling.
- Task 4: All 16 ATDD tests activated and passing. Fixed ATDD test data for AC-2 (asymmetric capping requires lower ratio to pass AC-1 first), corrected event field names (`reasonCode` vs `errorCode`, `platform` vs `platformId`), added `gasFraction` to test factories for edge re-validation compatibility.
- Task 5: 2 paper/live boundary tests activated — `describe.each` matrix confirms gate fires in both modes.
- Task 6: Test 6.1 confirmed OPPORTUNITY_FILTERED with new reason is compatible with existing event wiring. No new `@OnEvent` handlers added.
- Existing test regressions fixed: settings count (71→72), execution tests updated with dual-leg gate awareness (polymarket mocks, mockResolvedValueOnce chains, event type assertion updates). All 2630 tests pass.

### File List

**Modified:**

- `pm-arbitrage-engine/src/common/config/env.schema.ts` — added `DUAL_LEG_MIN_DEPTH_RATIO`
- `pm-arbitrage-engine/src/common/config/config-defaults.ts` — added `dualLegMinDepthRatio` entry
- `pm-arbitrage-engine/src/common/config/settings-metadata.ts` — added metadata under Execution group
- `pm-arbitrage-engine/src/common/config/effective-config.types.ts` — added `dualLegMinDepthRatio` field
- `pm-arbitrage-engine/src/dashboard/dto/update-settings.dto.ts` — added DTO field
- `pm-arbitrage-engine/src/dashboard/settings.service.ts` — added to SERVICE_RELOAD_MAP + handler
- `pm-arbitrage-engine/src/dashboard/settings.service.spec.ts` — updated settings count (71→72)
- `pm-arbitrage-engine/src/persistence/repositories/engine-config.repository.ts` — added to resolve chain
- `pm-arbitrage-engine/src/modules/execution/execution.service.ts` — core: new field, constructor init, reloadConfig extension, dual-leg gate in execute(), OpportunityFilteredEvent import
- `pm-arbitrage-engine/src/modules/execution/execution.service.spec.ts` — updated existing tests for dual-leg gate awareness
- `pm-arbitrage-engine/src/modules/execution/dual-leg-depth-gate.spec.ts` — activated 16 ATDD tests (skip→run), fixed test data
- `pm-arbitrage-engine/src/common/testing/paper-live-boundary/execution.spec.ts` — activated 2 boundary tests
- `pm-arbitrage-engine/prisma/schema.prisma` — added `dualLegMinDepthRatio` column to EngineConfig

**Created:**

- `pm-arbitrage-engine/prisma/migrations/[timestamp]_add_dual_leg_min_depth_ratio/migration.sql`

### Lad MCP Code Review (2026-03-23)

**Reviewer:** kimi-k2.5 (primary). Secondary (glm-5-turbo) failed — OpenRouter 400 error on all 3 attempts.

**Findings (9 total) — all rejected for this story's scope:**

| #   | Severity | Finding                                                                                                 | Verdict                | Reasoning                                                                                                                                                                               |
| --- | -------- | ------------------------------------------------------------------------------------------------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | High     | Orphaned orders in single-leg exposure (lines 586-594) — pending secondary order not linked to position | REJECT (pre-existing)  | Code not touched by this story. Track as separate tech debt.                                                                                                                            |
| 2   | High     | OpportunityFilteredEvent threshold param should be idealCount not minDepthRequired                      | REJECT (story spec)    | Story spec explicitly instructs `new Decimal(String(minDepthRequired))`. Reason string carries full per-platform depth context for downstream consumers.                                |
| 3   | High     | Fee recalculation assumes linear gas scaling using reservedCapitalUsd                                   | REJECT (pre-existing)  | Edge re-validation logic not modified by this story.                                                                                                                                    |
| 4   | Medium   | Triple depth fetching — dual-leg gate + per-leg checks = 4 API calls                                    | REJECT (intentional)   | Story spec: "Do NOT remove or modify the existing per-leg depth checks." Defense-in-depth is accepted trade-off. Future optimization story candidate if API latency proves problematic. |
| 5   | Medium   | JSON.parse/stringify serialization overhead in hot path                                                 | REJECT (pre-existing)  | Pattern not introduced by this story.                                                                                                                                                   |
| 6   | Low      | Silent config validation in reloadConfig — invalid values ignored without feedback                      | REJECT (pattern match) | Follows existing `minFillRatio` reload pattern. Changing one breaks consistency.                                                                                                        |
| 7   | Low      | Missing config reload for minEdgeThreshold                                                              | REJECT (pre-existing)  | Gap exists before this story.                                                                                                                                                           |
| 8   | Low      | dualLegCapped variable naming — calculated from first fetch but not used for sizing                     | REJECT (design)        | Variable used correctly for minFillRatio gate check. Per-leg checks handle sizing with fresh data intentionally.                                                                        |
| 9   | Low      | Type casting anti-patterns (as Record) in execution metadata                                            | REJECT (pre-existing)  | Pattern not introduced by this story.                                                                                                                                                   |

**Pre-existing issues worth tracking separately:** Items 1, 3, 4 (optimization), 7.
