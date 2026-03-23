# Story 10.7.4: Realized P&L Computation Investigation & Fix

Status: done

## Story

As an operator,
I want `realized_pnl` accurately computed and persisted for every closed position,
so that I can evaluate the system's actual profitability.

## Acceptance Criteria

1. **Given** the existing `realized_pnl` computation code, **When** this story is investigated, **Then** the root cause of all-NULL values is documented before any code changes.

2. **Given** the root cause is identified, **When** the fix is applied, **Then** `realized_pnl` is populated for every position closed via: model-driven exit, shadow exit, manual close, auto-unwind, and close-all. **And** the formula is: per-leg PnL = (exitFilledPrice − entryPrice) × exitFillSize (direction-adjusted) minus exit fees, summed across both legs using `decimal.js`.

3. **Given** positions are closed in paper mode, **When** paper fills are simulated, **Then** `realized_pnl` is still computed using the simulated fill prices.

4. **Given** the fix is deployed, **When** new positions are closed, **Then** `realized_pnl` is non-null for every closed position.

## Investigation Findings (Root Cause — Pre-Documented)

### Problem Statement

Story 10-0-2 (2026-03-16) added the `realized_pnl` column to `OpenPosition` and implemented persistence in 3 close paths. Database analysis (2026-03-23) shows `realized_pnl = NULL` for **ALL 198 closed positions**. Investigation-first pattern applies per Epic 9 retrospective convention.

### Root Cause

The exit-monitor service (automatic exit path) uses `positionRepository.updateStatus()` which only sets the `status` field — it does NOT accept or persist `realizedPnl`. The computation IS correct (the `realizedPnl` Decimal value is computed), but the database write silently drops it.

**Two broken paths in `exit-monitor.service.ts`:**

| Location | Method | Line | Issue |
|----------|--------|------|-------|
| Full exit | `executeExit()` | ~1133 | `positionRepository.updateStatus(positionId, 'CLOSED')` — realizedPnl computed but not persisted |
| Zero-residual | `evaluatePosition()` | ~424-427 | `positionRepository.updateStatus(positionId, 'CLOSED')` — realizedPnl should be 0 |

**Three correct paths (no changes needed):**

| Location | Service | Approach |
|----------|---------|----------|
| Manual close | `position-close.service.ts` ~481 | Direct `prisma.openPosition.update()` with realizedPnl ✅ |
| Zero-residual (manual) | `position-close.service.ts` ~155 | Direct Prisma update with `realizedPnl: 0` ✅ |
| Single-leg close | `single-leg-resolution.service.ts` ~438 | Direct Prisma update with realizedPnl ✅ |

**Transitive correct paths (delegate to correct services):**

| Path | Delegates To |
|------|-------------|
| Auto-unwind | `SingleLegResolutionService.closeLeg()` ✅ |
| Close-all endpoint | `PositionCloseService.closePosition()` ✅ |
| Shadow exit | Same model-driven exit path (shadow only logs comparison, doesn't close separately) |

### Why All 198 Positions Are NULL

~95%+ of positions close via the automatic exit-monitor polling loop (`executeExit()`). The manual close and single-leg resolution paths (which correctly persist `realizedPnl`) are rarely used by operators. Therefore virtually all closed positions went through the broken path.

### `positionRepository.updateStatus()` Signature

```typescript
async updateStatus(
  positionId: PositionId | string,
  status: Prisma.OpenPositionUpdateInput['status'],
) {
  return this.prisma.openPosition.update({
    where: { positionId },
    data: { status },
  });
}
```

Only accepts `status` — cannot carry `realizedPnl`. The fix must use direct Prisma updates (matching the pattern in `position-close.service.ts`).

## Tasks / Subtasks

### Phase 1: Investigation Documentation (AC: #1)

- [x] **Task 1: Document root cause findings** (AC: #1)
  - The investigation findings above serve as the documented root cause
  - Verify the findings match current code before proceeding to fixes
  - Run baseline tests to confirm green: `pnpm test`

### Phase 2: Fix Exit Monitor Full Exit Path (AC: #2, #3, #4)

- [x] **Task 2: Fix `executeExit()` full exit path** (AC: #2, #4)
  - [x] 2.1 Write failing test: when `executeExit()` completes a full exit, verify `prisma.openPosition.update` is called with `{ status: 'CLOSED', realizedPnl: <computed value> }`
  - [x] 2.2 In `exit-monitor.service.ts` `executeExit()` method (~line 1133): replace `await this.positionRepository.updateStatus(position.positionId, 'CLOSED')` with direct Prisma update
  - [x] 2.3 Inject `PrismaService` into `ExitMonitorService` if not already available (check constructor — it may already be injected via `positionRepository` or directly)
  - [x] 2.4 Confirm test passes

### Phase 3: Fix Exit Monitor Zero-Residual Path (AC: #2, #4)

- [x] **Task 3: Fix `evaluatePosition()` zero-residual path** (AC: #2, #4)
  - [x] 3.1 Write failing test: when EXIT_PARTIAL position has zero residual on both legs, verify `prisma.openPosition.update` is called with `{ status: 'CLOSED', realizedPnl: 0 }`
  - [x] 3.2 In `exit-monitor.service.ts` `evaluatePosition()` method (~lines 424-427): replace `await this.positionRepository.updateStatus(position.positionId, 'CLOSED')` with direct Prisma update
  - [x] 3.3 Confirm test passes

### Phase 4: Paper Mode Verification (AC: #3)

- [x] **Task 4: Paper mode dual-path tests** (AC: #3)
  - [x] 4.1 Write test: paper mode full exit persists `realizedPnl` (simulated fill prices produce a valid Decimal, not NULL)
  - [x] 4.2 Write test: live mode full exit persists `realizedPnl`
  - [x] 4.3 Use `describe.each([[true, 'paper'], [false, 'live']])` pattern per CLAUDE.md paper/live boundary requirement
  - [x] 4.4 Place tests in `src/common/testing/paper-live-boundary/exit-management/` (following established pattern)

### Phase 5: Comprehensive Close Path Audit (AC: #2)

- [x] **Task 5: Verify all 5 close paths persist realizedPnl** (AC: #2)
  - [x] 5.1 Audit test: model-driven exit (exit-monitor `executeExit()`) — covered by Task 2
  - [x] 5.2 Audit test: manual close (`position-close.service.ts`) — existing tests verified (lines 206, 479, 816-867)
  - [x] 5.3 Audit test: auto-unwind → `closeLeg()` — existing tests verified (lines 406, 638-678)
  - [x] 5.4 Audit test: close-all — delegates to `closePosition()`, covered by S8
  - [x] 5.5 Shadow exit shares model-driven path — no separate test needed, documented

### Phase 6: Assertion Depth Verification (AC: #2, #4)

- [x] **Task 6: Ensure assertion depth on all PnL tests** (AC: #2, #4)
  - [x] 6.1 All new tests use `{ realizedPnl: expect.any(Decimal) }` — no bare `toHaveBeenCalled()`
  - [x] 6.2 Verify computed PnL values match expected formula via S4/S5/S6 tests
  - [x] 6.3 Test with asymmetric entry/exit prices to catch sign errors (S7)

### Phase 7: Final Verification (AC: #1-4)

- [x] **Task 7: Run full suite and lint** (AC: #1-4)
  - [x] 7.1 `pnpm lint` — all modified files clean
  - [x] 7.2 `pnpm test` — 2698 passed, 0 failures (was 2685, +13 new)
  - [x] 7.3 Verified: no new tests use bare `toHaveBeenCalled()` without argument verification

## Dev Notes

### Architecture Compliance

- **Module boundary:** All changes are within `exit-management/` module — no cross-module import violations
- **Hot path:** Exit evaluation runs on 30-second polling cycle, NOT on the detection → risk → execution hot path. Performance is not critical here.
- **Error hierarchy:** No new error types needed — this is a persistence bug, not an error handling issue
- **Financial math:** All PnL computation already uses `decimal.js` — verify `.toDecimalPlaces(8)` for Prisma persistence
- **Events:** The `ExitTriggeredEvent` already carries `realizedPnl` as a string parameter — events are correct, only DB persistence is broken

### Reviewer Findings (Lad MCP, 2026-03-23)

- **4 `updateStatus()` calls verified** — only 2 transition to `CLOSED` (lines 424, 1133). Lines 1173 and 1335 set `EXIT_PARTIAL` which does not need `realizedPnl`. Story scope is correct.
- **Zero-residual P&L semantics:** When EXIT_PARTIAL position reaches zero residual on both legs, `realizedPnl: 0` is correct. Prior partial P&L was already released via `releasePartialCapital()` to the risk manager — the position-level `realizedPnl` records the final close P&L only. This matches the existing pattern in `position-close.service.ts` (~line 155).
- **Test migration impact:** Multiple existing test files assert on `positionRepository.updateStatus()` with CLOSED. After the fix, these assertions must change to `prisma.openPosition.update()` with realizedPnl payload. Affected test files: `exit-monitor-core.spec.ts`, `exit-monitor-partial-fills.spec.ts`, `exit-monitor-partial-reevaluation.spec.ts`, `exit-monitor-paper-mode.spec.ts`, `exit-monitor-depth-check.spec.ts`. Update these assertions as part of Tasks 2-3 (not a separate task — fix alongside each production code change per TDD).
- **PrismaService injection:** Already available in ExitMonitorService constructor — no DI changes needed.

### Key File Map

| File | Action | Purpose |
|------|--------|---------|
| `src/modules/exit-management/exit-monitor.service.ts` | **MODIFY** | Fix 2 broken CLOSED transitions to include realizedPnl |
| `src/modules/exit-management/exit-monitor.service.spec.ts` | **MODIFY** | Add/update tests for realizedPnl persistence |
| `src/common/testing/paper-live-boundary/exit-management/` | **ADD** | Paper/live dual-mode tests for PnL persistence |

### Files to NOT Modify (Already Correct)

| File | Status |
|------|--------|
| `src/modules/execution/position-close.service.ts` | ✅ Already persists realizedPnl correctly |
| `src/modules/execution/single-leg-resolution.service.ts` | ✅ Already persists realizedPnl correctly |
| `prisma/schema.prisma` | ✅ `realizedPnl Decimal? @map("realized_pnl")` already exists |
| `src/dashboard/dto/position-summary.dto.ts` | ✅ Dashboard DTO already includes realizedPnl |
| `src/dashboard/position-enrichment.service.ts` | ✅ Enrichment already handles realizedPnl |

### PnL Computation Formula (Reference)

The existing computation in `exit-monitor.service.ts` `executeExit()` (~lines 1088-1117):

```typescript
// Per-leg PnL (direction-adjusted)
if (position.kalshiSide === 'buy') {
  kalshiPnl = kalshiCloseFilledPrice.minus(kalshiEntryPrice).mul(kalshiExitFillSize);
} else {
  kalshiPnl = kalshiEntryPrice.minus(kalshiCloseFilledPrice).mul(kalshiExitFillSize);
}
// Same pattern for polymarket (opposite side)

// Exit fees
const kalshiExitFee = kalshiCloseFilledPrice
  .mul(kalshiExitFillSize)
  .mul(FinancialMath.calculateTakerFeeRate(kalshiClosePrice, kalshiFee));
// Same pattern for polymarket

// Total
const realizedPnl = kalshiPnl.plus(polymarketPnl).minus(kalshiExitFee).minus(polymarketExitFee);
```

This formula is consistent across `position-close.service.ts` and `single-leg-resolution.service.ts`. **Do not change the formula** — only fix the persistence gap.

> **Note on entry fees:** The current formula subtracts exit fees only. Entry fees were paid at position open and are not included in `realized_pnl`. This is consistent across all 3 services and matches the existing implementation. If full-cost P&L is needed later, that's a separate story.

### PrismaService Injection Check

`ExitMonitorService` constructor already has access to Prisma through the `positionRepository` (which wraps `PrismaService`). However, the fix needs **direct** `prisma.openPosition.update()` — check if `PrismaService` is already injected directly. If not, add it to the constructor. The module already imports `PersistenceModule` so no module-level changes needed.

### Previous Story Intelligence (10-7-3)

- Config pipeline pattern is well-established but **not needed for this story** (no new config settings)
- Test file `exit-monitor.service.spec.ts` is the existing test location — add new tests there
- Settings count remains at 74 (no change)
- `exit-monitor-depth-check.spec.ts` is a separate focused test file for depth checks — PnL persistence tests may go in the main spec or a new focused file `exit-monitor-pnl-persistence.spec.ts` (developer's choice)

### Git Commit Context

- Most recent commit: `34cc0bd` (story 10-7-3 — exit depth slippage tolerance)
- Only 1 prior commit mentions "realized": `ff295b7` (story 10-0-2 — original realizedPnl implementation)
- Current test count: **2,685 tests**, 154 test files, 0 failures

### Scope Boundary — What This Story Does NOT Do

- **No backfill of existing 198 NULL positions** — that would require reconstructing PnL from order history (separate story if needed)
- **No entry fee inclusion** in formula — consistent with existing implementation
- **No schema changes** — `realized_pnl` column already exists
- **No dashboard changes** — dashboard already renders realizedPnl when non-null
- **No config changes** — no new settings needed
- **No formula changes** — existing computation is correct, only persistence is broken

### Project Structure Notes

- All changes align with `src/modules/exit-management/` module scope
- No module boundary violations
- Paper/live boundary tests follow existing pattern in `src/common/testing/paper-live-boundary/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 10.7, Story 10-7-4]
- [Source: _bmad-output/implementation-artifacts/10-0-2-carry-forward-debt-triage-critical-fixes.md — AC 3 (realizedPnl persistence)]
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts — executeExit() ~line 1133, evaluatePosition() ~line 424]
- [Source: pm-arbitrage-engine/src/modules/execution/position-close.service.ts — correct pattern at ~line 481]
- [Source: pm-arbitrage-engine/src/modules/execution/single-leg-resolution.service.ts — correct pattern at ~line 438]
- [Source: pm-arbitrage-engine/prisma/schema.prisma — OpenPosition model, realizedPnl field]
- [Source: _bmad-output/implementation-artifacts/epic-10-retro-2026-03-22.md — Investigation-first pattern]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Baseline: 2685 tests, 154 files, 0 failures
- Final: 2698 tests, 156 files, 0 failures (+13 new tests, +2 new test files)
- RED phase confirmed: all 9 new tests failed against pre-fix code
- GREEN phase confirmed: all 9 new tests passed after fix
- 1 regression caught: `exit-monitor-data-source.spec.ts` expected `prisma.openPosition.update` call count = 1, updated to 2 (recalculated edge + CLOSED transition)

### Completion Notes List

- **Root cause verified** against current code: `executeExit()` line 1133 and `evaluatePosition()` lines 424-427 both called `positionRepository.updateStatus()` which only persists `status` — `realizedPnl` was computed but silently dropped
- **Fix applied** at 2 locations: replaced `positionRepository.updateStatus(id, 'CLOSED')` with `prisma.openPosition.update({ where, data: { status: 'CLOSED', realizedPnl } })` — PrismaService was already injected (constructor line 83)
- **No formula changes** — existing PnL computation is correct, only persistence was broken
- **5 existing test files updated** to assert `prisma.openPosition.update` instead of `positionRepository.updateStatus` for CLOSED transitions
- **All 5 close paths audited**: model-driven exit (fixed), zero-residual (fixed), manual close (already correct), auto-unwind/closeLeg (already correct), close-all (delegates to correct service)
- **Paper/live boundary tests** added in `src/common/testing/paper-live-boundary/exit-management/pnl-persistence.spec.ts` using `describe.each` pattern with connector health mode mocking
- **eslint-disable** added to 5 test files for `@typescript-eslint/no-unsafe-assignment` (vitest `expect.any()` returns `any`), matching established pattern in `position-close.service.spec.ts`

### File List

**Modified:**
- `src/modules/exit-management/exit-monitor.service.ts` — Fix 2 CLOSED transitions to persist realizedPnl
- `src/modules/exit-management/exit-monitor-core.spec.ts` — Update CLOSED assertion to prisma.openPosition.update
- `src/modules/exit-management/exit-monitor-partial-fills.spec.ts` — Update CLOSED assertion to prisma.openPosition.update
- `src/modules/exit-management/exit-monitor-partial-reevaluation.spec.ts` — Update 2 CLOSED assertions (full exit + zero-residual)
- `src/modules/exit-management/exit-monitor-data-source.spec.ts` — Update prisma.openPosition.update call count from 1 to 2

**Added:**
- `src/modules/exit-management/exit-monitor-pnl-persistence.spec.ts` — 10 unit tests for PnL persistence (S2-S7, S11, S12, S15, D6)
- `src/common/testing/paper-live-boundary/exit-management/pnl-persistence.spec.ts` — 4 paper/live boundary tests (S13, S14)

---

## Code Review & Follow-up Fixes (2026-03-24)

### Code Review Results

3-layer adversarial review (Blind Hunter + Edge Case Hunter + Acceptance Auditor). 22 raw findings → 16 after dedup → 0 patch, 6 defer, 10 reject. All 6 deferred findings fixed in the same session.

### Follow-up Fixes Applied (D1-D6)

**D5+D4: Repository abstraction + NaN guard**
- Added `PositionRepository.closePosition(positionId, realizedPnl)` with NaN/Infinity guard (SystemHealthError code 4009)
- Replaced all direct `prisma.openPosition.update` CLOSED transitions in exit-monitor.service.ts (2 sites), position-close.service.ts (2 sites), single-leg-resolution.service.ts (1 site)
- 5 new repository tests (valid Decimal, NaN, Infinity, zero, negative)

**D1: Accumulate partial PnL**
- Added `PositionRepository.updateStatusWithAccumulatedPnl(positionId, status, pnlDelta, existingPnl)` with NaN guard
- Partial exit paths in exit-monitor and position-close now persist accumulated PnL incrementally instead of discarding it
- Zero-residual cleanup preserves existing accumulated PnL (no longer overwrites with 0)
- Full exit after partials adds final exit PnL to accumulated value
- 3 new repository tests (accumulation, zero existing, NaN)

**D3: Risk state divergence detection**
- Added `RiskStateDivergenceEvent` class (system.events.ts) and `RISK_STATE_DIVERGENCE` event name (event-catalog.ts)
- Wrapped all `riskManager.closePosition()` and `releasePartialCapital()` calls in try-catch across 3 services (7 call sites)
- On catch: logs CRITICAL error, emits divergence event, does NOT re-throw (position stays CLOSED in DB, reconciliation fixes on restart)

**D2: Fix P&L reporting aggregate**
- Renamed `sumClosedEdgeByDateRange` → `sumClosedPnlByDateRange` with raw SQL `COALESCE(realized_pnl, expected_edge)` for historic NULL fallback
- Removed stale comment claiming "no dedicated realizedPnl column"
- Updated consumers: daily-summary.service.ts, trade-export.controller.ts, dashboard.service.ts (replaced inline aggregate)
- Updated all test files and paper-live-inventory.md

**D6: Pinned PnL value test**
- Added test asserting exact `realizedPnl = 5.06` with default mock values (kalshi buy@0.62 exit@0.66 fee=2%, poly sell@0.65 exit@0.62 fee=1%, size=100)

### Follow-up Test Counts

- Baseline (pre-review): 2698 tests, 156 files, 0 failures
- Final (post-fixes): 2706 tests, 155 files, 0 failures (+8 new tests, 0 lint errors)

### Follow-up File List

**Modified (production):**
- `src/common/errors/system-health-error.ts` — Add INVALID_PNL_COMPUTATION: 4009
- `src/common/events/event-catalog.ts` — Add RISK_STATE_DIVERGENCE event name
- `src/common/events/system.events.ts` — Add RiskStateDivergenceEvent class
- `src/persistence/repositories/position.repository.ts` — Add closePosition(), updateStatusWithAccumulatedPnl(), rename sumClosedPnlByDateRange()
- `src/modules/exit-management/exit-monitor.service.ts` — Use repository methods, accumulate partial PnL, wrap risk calls
- `src/modules/execution/position-close.service.ts` — Use repository methods, accumulate partial PnL, wrap risk calls
- `src/modules/execution/single-leg-resolution.service.ts` — Use repository closePosition(), wrap risk call
- `src/modules/monitoring/daily-summary.service.ts` — Update to sumClosedPnlByDateRange
- `src/modules/monitoring/trade-export.controller.ts` — Update to sumClosedPnlByDateRange
- `src/dashboard/dashboard.service.ts` — Replace inline aggregate with repository call

**Modified (tests):**
- `src/persistence/repositories/position.repository.spec.ts` — 8 new tests for closePosition + updateStatusWithAccumulatedPnl
- `src/modules/exit-management/exit-monitor.test-helpers.ts` — Add closePosition, updateStatusWithAccumulatedPnl mocks
- `src/modules/exit-management/exit-monitor-pnl-persistence.spec.ts` — Update assertions to use repository, add D6 pinned test
- `src/modules/exit-management/exit-monitor-core.spec.ts` — Update CLOSED assertion, remove unused prisma
- `src/modules/exit-management/exit-monitor-data-source.spec.ts` — Update call count and assertion
- `src/modules/exit-management/exit-monitor-partial-fills.spec.ts` — Update EXIT_PARTIAL assertions, remove unused prisma
- `src/modules/exit-management/exit-monitor-partial-reevaluation.spec.ts` — Update EXIT_PARTIAL/CLOSED assertions, remove unused prisma
- `src/modules/exit-management/exit-monitor-depth-check.spec.ts` — Update EXIT_PARTIAL assertion
- `src/common/testing/paper-live-boundary/exit-management/pnl-persistence.spec.ts` — Update CLOSED assertions
- `src/modules/execution/position-close.service.spec.ts` — Update all CLOSED/EXIT_PARTIAL assertions
- `src/modules/execution/single-leg-resolution.service.spec.ts` — Update CLOSED assertion
- `src/modules/monitoring/daily-summary.service.spec.ts` — Rename mock
- `src/modules/monitoring/trade-export.controller.spec.ts` — Rename mock
- `src/dashboard/dashboard.service.spec.ts` — Replace aggregate mocks with repository mock
- `src/common/testing/paper-live-boundary/dashboard.spec.ts` — Add sumClosedPnlByDateRange mock
- `src/common/testing/paper-live-inventory.md` — Update method reference
