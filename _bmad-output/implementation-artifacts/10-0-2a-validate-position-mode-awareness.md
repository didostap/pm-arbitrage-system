# Story 10-0-2a: validatePosition Mode-Awareness & Stale Halt Recovery

Status: done

## Story

As an **operator**,
I want **`validatePosition` and `isTradingHalted` to respect paper/live mode boundaries, and stale reconciliation halts to auto-clear on clean startup**,
so that **paper trading is never blocked by unrelated live-mode halt conditions, and the system self-heals from resolved reconciliation issues**.

## Acceptance Criteria

1. **`validatePosition` mode-aware**: `validatePosition(opportunity, isPaper?)` uses `this.getState(isPaper)` for all state checks — halt status, `openPositionCount`, `totalCapitalDeployed`. When `isPaper=true`, only paper halt reasons block; when `isPaper=false` (default), only live halt reasons block. [Source: sprint-change-proposal-2026-03-15-validate-position-mode-fix.md; code — `validatePosition` at risk-manager.service.ts:491-828]

2. **`isTradingHalted` mode-aware**: `isTradingHalted(isPaper?: boolean)` checks `this.getState(isPaper ?? false).activeHaltReasons.size > 0`. Default `false` preserves backward compatibility for callers that don't pass the parameter. [Source: code — `isTradingHalted` at risk-manager.service.ts:1071-1073]

3. **`getCurrentExposure` mode-aware**: `getCurrentExposure(isPaper?: boolean)` reads from `this.getState(isPaper ?? false)` and uses `this.getBankrollForMode(isPaper ?? false)`. Default `false` preserves backward compatibility. [Source: code — `getCurrentExposure` at risk-manager.service.ts:1182-1204]

4. **Trading engine passes `isPaper`**: `TradingEngineService.executeCycle()` passes `isPaper` (derived from connector health mode, same logic already used for `reservationRequest.isPaper`) to `this.riskManager.validatePosition(opportunity, isPaper)`. [Source: code — trading-engine.service.ts:164]

5. **IRiskManager interface updated**: `validatePosition(opportunity: unknown, isPaper?: boolean)`, `isTradingHalted(isPaper?: boolean)`, `getCurrentExposure(isPaper?: boolean)` — optional parameter, backward compatible. All mock implementations in test files updated. [Source: code — risk-manager.interface.ts:18-19, 30]

6. **Stale halt auto-recovery**: In `EngineLifecycleService.onApplicationBootstrap()`, after successful reconciliation (`reconResult.discrepanciesFound === 0`), call `this.riskManager.resumeTrading('reconciliation_discrepancy')`. This is idempotent — `resumeTrading` no-ops if the reason isn't in `activeHaltReasons`. [Source: code — engine-lifecycle.service.ts:139-168]

7. **Paper trading unblocked by live halt**: When live risk state has `activeHaltReasons = Set(['reconciliation_discrepancy'])` and paper risk state has empty `activeHaltReasons`, calling `validatePosition(opportunity, true)` returns `approved: true` (assuming other limits pass). [Source: sprint-change-proposal-2026-03-15-validate-position-mode-fix.md — root cause analysis]

8. **Live trading still blocked by live halt**: When live risk state has active halt reasons, calling `validatePosition(opportunity, false)` returns `approved: false` with reason `'Trading halted: ...'`. No behavioral change for live mode. [Source: existing behavior preservation]

9. **`processOverride` — no change needed**: `processOverride` at line 905 checks `this.isTradingHalted()` to reject overrides during daily loss halt. This remains live-only (overrides apply to live trading). The default `isPaper=false` preserves current behavior. [Source: code — risk-manager.service.ts:899-1008]

10. **Tests**: New tests for paper-mode isolation:
    - `validatePosition` with `isPaper=true` approves when only live halt is active
    - `validatePosition` with `isPaper=true` rejects when paper halt is active
    - `validatePosition` with `isPaper=false` rejects when live halt is active (regression)
    - `isTradingHalted(true)` returns `false` when only live halt reasons exist
    - `isTradingHalted(false)` returns `true` when live halt reasons exist
    - `getCurrentExposure(true)` returns paper state metrics
    - Startup auto-recovery: `resumeTrading` called after clean reconciliation
    - Startup auto-recovery: `resumeTrading` NOT called when discrepancies found
      [Source: sprint-change-proposal-2026-03-15-validate-position-mode-fix.md — test requirements]

11. **All existing tests pass**: `pnpm test` passes at current baseline (2221 passed, 2 todo, 121 files). `pnpm lint` clean. [Source: CLAUDE.md post-edit workflow; baseline verified 2026-03-16]

## Tasks / Subtasks

**Execution order: 1 → 2 → 3 → 4 → 5 → 6**

- [x] **Task 1: IRiskManager interface updates** (AC: #5)
  - [x] 1.1 Update `src/common/interfaces/risk-manager.interface.ts`:
    - `validatePosition(opportunity: unknown, isPaper?: boolean): Promise<RiskDecision>;`
    - `isTradingHalted(isPaper?: boolean): boolean;`
    - `getCurrentExposure(isPaper?: boolean): RiskExposure;`
    - Add JSDoc: `@param isPaper - When true, checks paper mode state. Defaults to false (live).`
  - [x] 1.2 Update mock implementations in these test files — add optional `isPaper` to mocked `validatePosition`, `isTradingHalted`, `getCurrentExposure` signatures:
    - `src/modules/risk-management/risk-manager.service.spec.ts` (primary test file)
    - `src/core/trading-engine.service.spec.ts` (mocks `IRiskManager`)
    - `src/core/engine-lifecycle.service.spec.ts` (mocks `IRiskManager`)
    - `src/modules/risk-management/stress-test.service.spec.ts` (mocks `getCurrentExposure`)
    - `src/reconciliation/startup-reconciliation.service.spec.ts` (mocks `IRiskManager`)
      Search for `isTradingHalted:` and `validatePosition:` and `getCurrentExposure:` in spec files to catch any others.
    - **Note:** All mocks use `vi.fn()` which accepts optional params automatically — no mock signature changes needed.

- [x] **Task 2: RiskManagerService method refactoring** (AC: #1, #2, #3, #7, #8)
  - [x] 2.1 Refactor `isTradingHalted(isPaper: boolean = false)`:
    ```typescript
    isTradingHalted(isPaper: boolean = false): boolean {
      return this.getState(isPaper).activeHaltReasons.size > 0;
    }
    ```
  - [x] 2.2 Refactor `validatePosition(opportunity: unknown, isPaper: boolean = false)`:
    - Add `const state = this.getState(isPaper)` near method top
    - Add `const bankrollUsd = this.getBankrollForMode(isPaper)` near method top
    - Line 493: `if (this.isTradingHalted(isPaper))` (was `this.isTradingHalted()`)
    - All `this.liveState.openPositionCount` → `state.openPositionCount`
    - All `this.liveState.totalCapitalDeployed` → `state.totalCapitalDeployed`
    - All `this.liveState.dailyPnl` → `state.dailyPnl`
    - Replace `new FinancialDecimal(this.config.bankrollUsd)` → use `bankrollUsd` variable
    - Pass `isPaper` to reserved-slot/capital helpers: `this.getReservedPositionSlots(isPaper)` and `this.getReservedCapital(isPaper)`. These methods already accept an optional `isPaper` parameter and filter by mode when provided — but `validatePosition` currently calls them without it, causing them to aggregate across both modes. [Verified: risk-manager.service.ts:1541-1559]
  - [x] 2.3 Refactor `getCurrentExposure(isPaper: boolean = false)`:
    - `const state = this.getState(isPaper)`
    - `const bankrollUsd = this.getBankrollForMode(isPaper)`
    - All `this.liveState.*` references → `state.*`
    - `dailyLossLimitUsd` calculation uses `bankrollUsd`
    - Pass `isPaper` to reserved helpers: `this.getReservedPositionSlots(isPaper)` and `this.getReservedCapital(isPaper)` — same fix as in `validatePosition` (these calls currently aggregate across modes). [Verified: getCurrentExposure at risk-manager.service.ts:1182-1204]

- [x] **Task 3: TradingEngineService caller update** (AC: #4)
  - [x] 3.1 In `executeCycle()`, compute `isPaper` once before the opportunity loop:
    ```typescript
    const isPaper =
      this.kalshiConnector.getHealth().mode === 'paper' || this.polymarketConnector.getHealth().mode === 'paper';
    ```
    (Same logic already used at line 208 for `reservationRequest.isPaper`)
  - [x] 3.2 Pass to `validatePosition`:
    ```typescript
    const decision = await this.riskManager.validatePosition(opportunity, isPaper);
    ```

- [x] **Task 4: Stale halt auto-recovery** (AC: #6)
  - [x] 4.1 In `EngineLifecycleService.onApplicationBootstrap()`, after the reconciliation try block succeeds with `reconResult.discrepanciesFound === 0`:
    ```typescript
    if (reconResult.discrepanciesFound === 0) {
      this.riskManager.resumeTrading('reconciliation_discrepancy');
    }
    ```
    Place inside the `try` block around line 153. `resumeTrading` is idempotent — no-ops if the reason isn't present.
  - [x] 4.2 Update `engine-lifecycle.service.spec.ts`:
    - Test: `resumeTrading('reconciliation_discrepancy')` called when `discrepanciesFound === 0`
    - Test: `resumeTrading` NOT called when `discrepanciesFound > 0`

- [x] **Task 5: Tests** (AC: #10, #11)
  - [x] 5.1 Update `risk-manager.service.spec.ts`:
    - Add `describe('validatePosition mode-awareness')` block:
      - Test: `isPaper=true` approves when only live halt active
      - Test: `isPaper=true` rejects when paper halt active
      - Test: `isPaper=false` rejects when live halt active (regression guard)
      - Test: `isPaper=true` uses paper state's `openPositionCount` and `totalCapitalDeployed`
      - Test: `isPaper=true` uses paper bankroll for capital checks
    - Add `describe('isTradingHalted mode-awareness')` block:
      - Test: `isTradingHalted(true)` returns `false` when only live halt exists
      - Test: `isTradingHalted(false)` returns `true` when live halt exists
      - Test: `isTradingHalted(true)` returns `true` when paper halt exists
      - Test: `isTradingHalted()` defaults to live (backward compat)
    - Add `describe('getCurrentExposure mode-awareness')` block:
      - Test: `getCurrentExposure(true)` returns paper state values
      - Test: `getCurrentExposure()` defaults to live (backward compat)
  - [x] 5.2 Add `processOverride` regression test (AC: #9):
    - Test: `processOverride` rejects during live halt (existing behavior preserved)
    - Test: `processOverride` does NOT reject when only paper halt is active (verifies default `isPaper=false`)
  - [x] 5.3 Verify existing tests still pass — most use default `isPaper=false` so should be unaffected
  - [x] 5.4 Update `trading-engine.service.spec.ts` if mocks need `isPaper` parameter

- [x] **Task 6: Final validation + lint** (AC: #11)
  - [x] 6.1 Run `pnpm test` — all existing + new tests pass
  - [x] 6.2 Run `pnpm lint` — clean
  - [x] 6.3 Run `pnpm build` — no type errors

## Dev Notes

### Architecture Patterns & Constraints

- **Module dependency rules**: All changes within existing module boundaries. No new cross-module imports. [Source: CLAUDE.md Module Dependency Rules]
- **Financial math**: No new financial calculations — this is a state-routing fix. [Source: CLAUDE.md Domain Rules]
- **Error hierarchy**: No new error types needed. [Source: CLAUDE.md Error Handling]
- **Event emission**: No new events. Existing `SYSTEM_TRADING_HALTED` and `SYSTEM_TRADING_RESUMED` events remain unchanged.
- **Backward compatibility**: All parameter additions are optional with default `false` (live mode) — zero breaking changes for existing callers.

### Critical Implementation Details

1. **`getReservedPositionSlots(isPaper?)` and `getReservedCapital(isPaper?)`**: These private methods already accept an optional `isPaper` parameter and filter the in-memory `reservations` Map by mode when provided (lines 1541-1559). However, `validatePosition` and `getCurrentExposure` currently call them **without** `isPaper`, causing them to aggregate across both modes. Tasks 2.2 and 2.3 fix this by passing `isPaper` through. Pattern reference: `reserveBudget()` at line 1275 already uses `this.getReservedCapital(request.isPaper)`.

2. **`processOverride` — no change needed**: At line 905, `this.isTradingHalted()` is called without arguments. With the default `isPaper=false`, this continues to check live state — correct behavior since overrides apply to live trading.

3. **`haltTrading` and `resumeTrading` remain live-only**: These methods always write to `this.liveState`. For full mode-awareness, they'd need `isPaper` too. However, paper-mode-specific halts (e.g., paper daily loss) are handled by `updateDailyPnl(amount, isPaper)` which already writes to the correct mode's state via `getState(isPaper)`. No production code path currently needs to explicitly halt paper mode via `haltTrading()`. If a future story adds paper-specific halts, `haltTrading`/`resumeTrading` can be made mode-aware then.

4. **StressTestService caller**: `StressTestService.runSimulation()` at line 82 calls `getCurrentExposure()` without arguments. With default `isPaper=false`, existing behavior is preserved — stress tests run against live exposure. No change needed.

5. **Startup recovery is idempotent**: `resumeTrading('reconciliation_discrepancy')` checks `if (!this.liveState.activeHaltReasons.has(haltReason)) return`. Safe to call on every clean startup.

5a. **When `reconciliation_discrepancy` halt is set**: Only in the **catch block** of `onApplicationBootstrap()` (when `reconcile()` throws AND active positions exist) — NOT when reconciliation succeeds but finds discrepancies (`discrepanciesFound > 0`, which only logs an error). The auto-recovery in AC #6 clears halts from a **previous failed boot** where reconciliation threw. On the next clean startup, `reconcile()` succeeds with `discrepanciesFound === 0` → `resumeTrading` clears the stale halt. [Verified: engine-lifecycle.service.ts:131-168]

5b. **Mixed-mode `isPaper` uses OR logic by design**: `isPaper = kalshi.mode === 'paper' || polymarket.mode === 'paper'`. When either platform is in paper mode, the entire cycle is treated as paper. This is the established pattern from Story 5-5-3 (mixed-mode validation) — in mixed mode, execution goes through the `PaperTradingConnector` wrapper, so risk checks must also use paper state. The OR logic is not a gap; it's correct. [Source: trading-engine.service.ts:204-206, Story 5-5-3]

6. **`reserveBudget` already has the correct pattern**: Line 1215 reads `if (!request.isPaper && this.isTradingHalted())`. After this fix, `isTradingHalted()` will default to `isPaper=false`, so `reserveBudget` behavior is unchanged. The fix brings `validatePosition` in line with this existing pattern.

7. **Known debt — `CorrelationTrackerService` getter methods not mode-parameterized**: `getClusterExposures()` and `getAggregateExposurePct()` return cached results from the last `recalculateClusterExposure(clusterId?, isPaper=false)` call, stored in a single `this.clusterExposures` array. This means cluster limits in `validatePosition` may reflect the wrong mode's data if paper recalculation ran last. **Out of scope for this story** — `recalculateClusterExposure` is event-driven (budget commit / exit triggered) and in practice operates on live positions for live cycles. A proper fix (per-mode cached arrays + `isPaper` parameter on getters) should be tracked as future tech debt. [Verified: correlation-tracker.service.ts:56-209]

### Context: Why Story 9-16 Left This Out

Story 9-16's completion notes stated: _"`validatePosition` and `getCurrentExposure` remain live-only by design — mode separation occurs at `reserveBudget`/`commitReservation` level."_ The Lad MCP code review flagged this gap but it was dismissed.

The reasoning was that `validatePosition` is a "pre-screen" and `reserveBudget` is the real gate. What was missed: `validatePosition` calls `isTradingHalted()` as its VERY FIRST check and returns `approved: false` immediately — the opportunity never reaches `reserveBudget`. The pre-screen is actually the primary gate.

This story corrects that design decision. Story 9-16's completion notes should be updated to reference this course correction (see sprint change proposal, Section 4).

### References

- [Source: sprint-change-proposal-2026-03-15-validate-position-mode-fix.md] — Full root cause analysis and evidence
- [Source: Story 9-16 completion notes] — Original "by design" decision being revised
- [Source: risk-manager.service.ts:491-828] — `validatePosition()` — primary fix target
- [Source: risk-manager.service.ts:1071-1073] — `isTradingHalted()` — hardcoded to liveState
- [Source: risk-manager.service.ts:1182-1204] — `getCurrentExposure()` — hardcoded to liveState
- [Source: risk-manager.service.ts:1210-1215] — `reserveBudget()` — already has correct `!request.isPaper` guard (proves the pattern)
- [Source: risk-manager.interface.ts:18-19, 30] — Interface signatures to update
- [Source: trading-engine.service.ts:164] — Sole production caller of `validatePosition`
- [Source: trading-engine.service.ts:208] — `isPaper` already computed for `reservationRequest`
- [Source: engine-lifecycle.service.ts:139-169] — Reconciliation halt/resume path
- [Source: CLAUDE.md] — Post-edit workflow, module dependency rules

### Previous Story Intelligence

**From Story 9-16** (risk-state-paper-trade-reconciliation):

- Established the `getState(isPaper)` / `getBankrollForMode(isPaper)` pattern used throughout this fix
- `ModeRiskState` type and dual-row Prisma model already exist — no schema changes needed
- `reserveBudget()` line 1215 demonstrates the correct halt-check guard: `!request.isPaper && this.isTradingHalted()`
- Post-deploy bug: paper positions incorrectly reconciled against live APIs → `reconciliation_discrepancy` halt set → never cleared. This story adds the cleanup mechanism.

## Dev Agent Record

### Implementation Summary (2026-03-16)

**Baseline:** 2221 tests, 121 files
**Final:** 2241 tests, 121 files (+20 new tests: 15 mode-awareness + 4 dashboard halt indicator + 1 code review fix)

### Files Modified

- `src/common/interfaces/risk-manager.interface.ts` — Added `isPaper?` to `validatePosition`, `isTradingHalted`, `getCurrentExposure` with JSDoc; added `getActiveHaltReasons(isPaper?)` (code review fix)
- `src/modules/risk-management/risk-manager.service.ts` — Refactored `isTradingHalted`, `validatePosition`, `getCurrentExposure` to use `getState(isPaper)` / `getBankrollForMode(isPaper)`, pass `isPaper` to `getReservedPositionSlots`/`getReservedCapital`; added `getActiveHaltReasons()` implementation (code review fix)
- `src/core/trading-engine.service.ts` — Compute `isPaper` once before opportunity loop, pass to `validatePosition(opportunity, isPaper)`, simplified duplicate `isPaper` computation for `reservationRequest`
- `src/core/engine-lifecycle.service.ts` — Added `resumeTrading('reconciliation_discrepancy')` in else branch after clean reconciliation
- `src/modules/risk-management/risk-manager.service.spec.ts` — +13 tests: validatePosition mode-awareness (5), isTradingHalted mode-awareness (4), getCurrentExposure mode-awareness (2), processOverride regression (2)
- `src/core/engine-lifecycle.service.spec.ts` — +2 tests: auto-recovery after clean recon, no auto-recovery when discrepancies found
- `src/core/trading-engine.service.spec.ts` — Added `validatePosition` isPaper assertion to 2 existing paper/live mode tests

### Design Decisions

1. **Mock signatures unchanged:** All test mocks use `vi.fn()` which accepts any arguments — no changes needed for the optional `isPaper` parameter. Story Task 1.2 specified updating mock signatures but this was unnecessary.
2. **TradingEngine simplification:** Extracted `isPaper` computation to a single `const` before the opportunity loop, replacing the duplicated `this.kalshiConnector.getHealth().mode === 'paper' || ...` in `reservationRequest.isPaper`.
3. **`determineRejectionReason` untouched:** This private method (used by `processOverride`) still calls `getReservedPositionSlots()` without `isPaper`, which aggregates across modes. This is pre-existing behavior and out of scope (AC #9: "no change needed"). Noted as future tech debt.

### Lad MCP Code Review (2026-03-16)

- **Primary reviewer (kimi-k2.5):** 1 finding relevant to this story — recommended making `getReservedPositionSlots`/`getReservedCapital` param required (`boolean` not `boolean?`). Not addressed: would break `determineRejectionReason` which is out of scope. All other findings were pre-existing issues (paperActivePairIds leak, processOverride docs).
- **Secondary reviewer (glm-5):** Timed out (2 attempts).

### Dashboard Trading Halt Indicator (2026-03-16)

Added as a follow-up to the mode-awareness fix — halt status was not visible in the UI.

**Backend:**

- `src/dashboard/dto/dashboard-overview.dto.ts` — Added `tradingHalted: boolean`, `haltReasons: string[]`
- `src/dashboard/dashboard.service.ts` — Populate `tradingHalted` from `isTradingHalted()`, `haltReasons` from `getActiveHaltReasons()` (code review: switched from stale DB JSON to in-memory state)
- `src/dashboard/dto/ws-events.dto.ts` — Added `WsTradingHaltPayload`, `TRADING_HALT` event
- `src/dashboard/dashboard.gateway.ts` — Handlers for `SYSTEM_TRADING_HALTED`/`SYSTEM_TRADING_RESUMED`; halt handler now extracts all `activeReasons` from event details (code review fix)
- `src/dashboard/dashboard.service.spec.ts` — +2 tests (halt false, halt true with reasons); halt test updated to mock `getActiveHaltReasons` (code review fix)
- `src/dashboard/dashboard.gateway.spec.ts` — +3 tests (halt all-reasons broadcast, halt fallback-to-single-reason, resume broadcast) (code review: +1 test for fallback)

**Frontend (`pm-arbitrage-dashboard/`):**

- `src/types/ws-events.ts` — Added `WsTradingHaltPayload`, `TRADING_HALT` event
- `src/providers/WebSocketProvider.tsx` — Invalidate overview query on `TRADING_HALT` event
- `src/components/TopBar.tsx` — Red destructive badge "TRADING HALTED" with tooltip showing halt reasons

### Code Review #2 (2026-03-16)

Fixed 3 MEDIUM issues:

1. **MEDIUM — `haltReasons` stale (DB vs in-memory):** `dashboard.service.ts` sourced `haltReasons` from DB `riskState.haltReason` JSON while `tradingHalted` used in-memory `isTradingHalted()`. `haltTrading()` doesn't call `persistState()`, so halt reasons could be empty/stale. **Fix:** Added `getActiveHaltReasons(isPaper?)` to `IRiskManager` interface + implementation, replaced DB JSON parsing with in-memory call.
2. **MEDIUM — Sprint status test count wrong:** `sprint-status.yaml` said `+15 tests (2221→2236)` but actual was 2240. **Fix:** Updated to `+19 tests (2221→2240)`.
3. **MEDIUM — Gateway halt event sent only triggering reason:** `handleTradingHalted` sent `reasons: [event.reason]` (single) while `handleTradingResumed` sent all remaining. **Fix:** Extract `activeReasons` from `event.details` when available, fall back to `[event.reason]` for events without it (e.g., time_drift). +1 test for fallback path.

3 LOW issues noted (no fix required):
- L1: Dashboard `Api.ts` not documented in story File List (auto-generated file)
- L2: Frontend `WsAlertNewPayload.type` union drift — pre-existing, not introduced by this story
- L3: `determineRejectionReason` not mode-aware — documented known debt, out of scope

### Known Tech Debt (from code review)

- `getReservedPositionSlots(isPaper?: boolean)` and `getReservedCapital(isPaper?: boolean)` still accept `undefined` (aggregation mode). `determineRejectionReason` relies on this. Consider making param required and updating `determineRejectionReason` in a future story.
- `CorrelationTrackerService` getters not mode-parameterized (documented in Dev Notes #7 — unchanged).
- Frontend `WsAlertNewPayload.type` missing `cluster_limit_breached` and `aggregate_cluster_limit_breached` — backend has 5 alert types, frontend has 3.
