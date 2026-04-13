# Story 10-96.6: Closed Position Exit Data Fix

Status: done

## Story

As an operator,
I want closed positions to display frozen exit data (exit type, exit mode, exit criteria) correctly and not continue calculating dynamic values from live market data,
so that my position history accurately reflects the state at the time each position was closed.

## Context

Story 10-96-5 fixed `exitMode` persistence and added model-mode column branching to the dashboard. However, the **list view** remains broken because `getPositions()` in `dashboard.service.ts` never wires `exitMode`/`exitCriteria`/`closestCriterion`/`closestProximity` through to the response. Additionally, `exitType` is derived from audit events using the wrong field name (`details.type` instead of `details.exitType`), and the enrichment service fetches live VWAP prices for closed positions (wasteful and misleading).

**Five interconnected root causes:**

| RC | Summary | Location |
|----|---------|----------|
| RC-1 | `getPositions()` response omits 4 model-mode fields | `dashboard.service.ts:251-288` |
| RC-2 | `exitType` audit events read `details.type` instead of `details.exitType` | `dashboard.service.ts:190`, `dashboard-audit.service.ts:154` |
| RC-3 | `exitType` lookup is redundant — `exitCriterion` already on the position record since 10-96-3 | `dashboard.service.ts:147-199` |
| RC-4 | Enrichment fetches live prices for CLOSED positions | `position-enrichment.service.ts:118-131` |
| RC-5 | `getPositionById()` hardcodes `exitType: null` and omits 4 model-mode fields | `dashboard.service.ts:359, 364-366` |

**Sprint Change Proposal:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16-closed-position-exit-data-fix.md`

## Acceptance Criteria

1. **Given** the Positions page displays closed positions, **When** the Exit Mode column renders, **Then** it shows the correct exit mode badge (model/fixed/shadow) — not blank.

2. **Given** the Positions page displays closed positions, **When** the Exit Type column renders, **Then** it shows the correct exit criterion (edge_evaporation, time_decay, etc.) — not "unknown".

3. **Given** a closed position in model/shadow mode, **When** the Exit Proximity column renders, **Then** it shows the frozen closest criterion name and proximity percentage from `lastEvalCriteria` — not dynamically calculated SL/TP proximity.

4. **Given** a closed position in fixed mode (or without lastEvalCriteria), **When** the Exit Proximity column renders, **Then** it shows a dash — not dynamically calculated values.

5. **Given** a closed position, **When** the enrichment service processes it, **Then** it does NOT fetch live VWAP prices from the price feed (no API calls for closed positions).

6. **Given** a closed position, **When** the enrichment service returns, **Then** `currentPrices`, `currentEdge`, `unrealizedPnl`, and `exitProximity` are null; `exitMode`, `exitCriteria`, `closestCriterion`, `closestProximity`, `recalculatedEdge`, `edgeDelta` are populated from frozen DB fields.

7. **Given** an EXIT_PARTIAL position, **When** the enrichment service processes it, **Then** it continues to fetch live VWAP prices and compute dynamic values (zero regression for active positions).

8. **Given** the single-position endpoint (`getPositionById`), **When** it returns a closed position, **Then** `exitType` is read from `exitCriterion` (not hardcoded null) and all 4 model-mode fields are included.

9. **Given** the position detail endpoint (`getPositionDetails`), **When** it returns a closed position, **Then** `exitType` is read from `exitCriterion` (fallback to audit event with corrected field name `exitType`).

## Tasks / Subtasks

- [x] Task 1: Backend — Add CLOSED early-return guard in `position-enrichment.service.ts` (AC: #3, #4, #5, #6, #7)
  - [x] 1.1 Write failing test: CLOSED position returns frozen data with null currentPrices/currentEdge/unrealizedPnl/exitProximity
  - [x] 1.2 Write failing test: CLOSED position does NOT call `priceFeed.getVwapClosePrice()`
  - [x] 1.3 Write failing test: CLOSED position populates exitMode/exitCriteria/closestCriterion/closestProximity/recalculatedEdge/edgeDelta from DB fields
  - [x] 1.4 Implement early return in `enrich()` for `position.status === 'CLOSED'` — after resolution date computation (line 85), before VWAP fetch (line 118)
  - [x] 1.5 Write test: CLOSED position with `exitMode: 'fixed'` and `lastEvalCriteria: null` returns all criteria fields as null (AC #4 edge case)
  - [x] 1.6 Write test: CLOSED position with malformed `lastEvalCriteria` (missing criterion/proximity fields) does not throw, returns null criteria fields
  - [x] 1.7 Write failing test: EXIT_PARTIAL position still calls `priceFeed.getVwapClosePrice()` (regression guard — existing EXIT_PARTIAL tests at spec lines 610-824 cover the positive path; this test explicitly asserts the CLOSED guard does NOT intercept EXIT_PARTIAL)
  - [x] 1.8 Verify EXIT_PARTIAL test passes with no code change (existing path handles it)
- [x] Task 2: Backend — Wire 4 missing fields in `getPositions()` response mapping (AC: #1, #3)
  - [x] 2.1 Write failing test: `getPositions()` response includes exitMode/exitCriteria/closestCriterion/closestProximity from enrichment
  - [x] 2.2 Add 4 fields to return object at `dashboard.service.ts:282-288`
- [x] Task 3: Backend — Read exitType from `pos.exitCriterion` in `getPositions()` + fix audit fallback field name (AC: #2)
  - [x] 3.1 Write failing test: CLOSED position exitType reads from `pos.exitCriterion`
  - [x] 3.2 Write failing test: audit fallback uses `details.exitType` (not `details.type`)
  - [x] 3.3 Update `dashboard.service.ts:235`: add `pos.exitCriterion ??` before `exitTypeByPairId.get()`
  - [x] 3.4 Update `dashboard.service.ts:190`: change `details?.type` to `details?.exitType ?? details?.type`
- [x] Task 4: Backend — Fix exitType in `getPositionDetails()` — prefer exitCriterion, fix audit fallback field name (AC: #9)
  - [x] 4.1 Write failing test: `getPositionDetails()` reads exitType from `pos.exitCriterion` for CLOSED positions (note: `getPositionDetails()` calls `enrichmentService.enrich()` internally — after Task 1's CLOSED early return, enrichment returns frozen data for CLOSED positions; the test should verify both exitType sourcing AND that enrichment returns frozen data through this flow)
  - [x] 4.2 Write failing test: `getPositionDetails()` falls back to audit event with `details.exitType` when `pos.exitCriterion` is null
  - [x] 4.3 Update `dashboard-audit.service.ts:144-158`: add `pos.exitCriterion` check before audit event lookup; fix `details.type` to `details.exitType ?? details.type`
- [x] Task 5: Backend — Fix `getPositionById()` — exitType from exitCriterion + 4 missing fields (AC: #8)
  - [x] 5.1 Write failing test: `getPositionById()` for CLOSED position has exitType from exitCriterion (not null)
  - [x] 5.2 Write failing test: `getPositionById()` response includes exitMode/exitCriteria/closestCriterion/closestProximity
  - [x] 5.3 Update `dashboard.service.ts:359`: replace `exitType: null` with conditional read from `pos.exitCriterion`
  - [x] 5.4 Add 4 model-mode fields after `dataSource` at `dashboard.service.ts:364-366`
- [x] Task 6: Tests — Paper/live boundary for closed position enrichment (AC: #5, #6)
  - [x] 6.1 Add test in `paper-live-boundary/dashboard.spec.ts`: CLOSED paper position enrichment returns frozen data
  - [x] 6.2 Add test: CLOSED live position enrichment returns frozen data
- [x] Task 7: Lint + full test suite green (AC: all)
  - [x] 7.1 Run `cd pm-arbitrage-engine && pnpm lint && pnpm test`
  - [x] 7.2 Verify 4004+ tests pass (baseline: 4004 pass, 1 pre-existing e2e failure)

## Dev Notes

### Scope: Backend Only

This story modifies **3 backend files** in `pm-arbitrage-engine/src/dashboard/`. No frontend changes needed — the frontend already handles null values correctly:
- Risk/Reward column: shows "—" for CLOSED positions (line 170 of `PositionsPage.tsx`)
- Exit Proximity column: shows "—" when `exitProximity` is null (line 211); shows frozen criterion data when `closestCriterion` is populated (line 193)
- Exit Type column: shows `ExitTypeBadge` when exitType has a value (line 237)
- Exit Mode column: shows `ExitModeBadge` with the mode value (line 225)

### Change 1: Enrichment CLOSED Early Return (`position-enrichment.service.ts`)

**Method:** `enrich()` (line 66)
**Insert after:** Resolution date computation (line 85-95), before order fill data validation (line 98)

For CLOSED positions, skip the VWAP price fetch and return frozen data:

```typescript
// CLOSED positions: return frozen data, skip live price fetching
if (position.status === 'CLOSED') {
  const exitMode = position.exitMode ?? null;
  let exitCriteria: EnrichedPosition['exitCriteria'] = null;
  let closestCriterion: string | null = null;
  let closestProximity: number | null = null;

  if (position.lastEvalCriteria && Array.isArray(position.lastEvalCriteria)) {
    const rawCriteria = position.lastEvalCriteria as Array<{
      criterion: string;
      proximity: string;
      triggered: boolean;
      detail?: string;
    }>;
    exitCriteria = rawCriteria;
    let maxProximity = -1;
    for (const c of rawCriteria) {
      const prox = parseFloat(c.proximity);
      if (!isNaN(prox) && prox > maxProximity) {
        maxProximity = prox;
        closestCriterion = c.criterion;
        closestProximity = prox;
      }
    }
  }

  const recalcEdge = position.recalculatedEdge
    ? new Decimal(position.recalculatedEdge.toString())
    : null;
  const initialEdge = position.expectedEdge
    ? new Decimal(position.expectedEdge.toString())
    : null;
  const edgeDelta = recalcEdge && initialEdge
    ? recalcEdge.minus(initialEdge).toFixed(8)
    : null;

  return {
    status: 'enriched',
    data: {
      currentPrices: { kalshi: null, polymarket: null },
      currentEdge: null,
      unrealizedPnl: null,
      exitProximity: null,
      resolutionDate,
      timeToResolution,
      projectedSlPnl: null,
      projectedTpPnl: null,
      recalculatedEdge: recalcEdge?.toFixed(8) ?? null,
      edgeDelta,
      lastRecalculatedAt: position.lastRecalculatedAt?.toISOString() ?? null,
      dataSource: position.recalculationDataSource ?? null,
      dataFreshnessMs: null,
      exitMode,
      exitCriteria,
      closestCriterion,
      closestProximity,
    },
  };
}
```

**Reuses** the same `closestCriterion` computation pattern already at lines 332-351 of the existing method — the CLOSED early return mirrors this logic exactly.

**EXIT_PARTIAL must NOT hit this guard.** Only `position.status === 'CLOSED'` triggers the early return. EXIT_PARTIAL positions continue through the full enrichment path (live prices, dynamic exitProximity, etc.).

### Change 2: Wire 4 Missing Fields in `getPositions()` (`dashboard.service.ts`)

**Location:** Response mapping at lines 282-288

Add after the existing `dataSource` line (line 285):

```typescript
exitMode: enrichment.data.exitMode ?? null,
exitCriteria: enrichment.data.exitCriteria ?? null,
closestCriterion: enrichment.data.closestCriterion ?? null,
closestProximity: enrichment.data.closestProximity ?? null,
```

These fields are already computed by the enrichment service, declared in `PositionSummaryDto` (lines 242-273), and expected by the frontend. The gap was a simple omission in the response mapping.

### Change 3: Read exitType from `pos.exitCriterion` (`dashboard.service.ts`)

**Two locations:**

**3a — Primary exitType read (line 235):**
```typescript
// OLD:
exitType = exitTypeByPairId.get(pos.pairId) ?? null;

// NEW:
exitType = pos.exitCriterion ?? exitTypeByPairId.get(pos.pairId) ?? null;
```

`exitCriterion` is populated at position close time (since Story 10-96-3). Fallback to audit event lookup for pre-10-96-3 positions.

**3b — Audit event field name fix (line 190):**
**Verified:** DB query confirms `exitType` is the correct field: `SELECT details->>'exitType', details->>'type' FROM audit_logs WHERE event_type='execution.exit.triggered'` — `exitType` populated, `type` NULL for all rows. See sprint change proposal Evidence table.
```typescript
// OLD:
(details?.type as string) ?? 'unknown',

// NEW:
(details?.exitType as string) ?? (details?.type as string) ?? 'unknown',
```

`ExitTriggeredEvent` stores the exit type as `exitType`, not `type`. Check both for backward compatibility.

### Change 4: Fix exitType in `getPositionDetails()` (`dashboard-audit.service.ts`)

**Location:** Lines 144-158

```typescript
// OLD:
let exitType: string | null = null;
if (pos.status === 'CLOSED' || pos.status === 'EXIT_PARTIAL') {
  const exitEvent = positionAuditEvents.find(
    (e) => e.eventType === 'execution.exit.triggered',
  );
  if (exitEvent) {
    const details = this.parseAuditDetails(exitEvent.details, exitEvent.id);
    exitType = (details.type as string) ?? 'unknown';
  } else {
    exitType = 'manual';
  }
}

// NEW:
let exitType: string | null = null;
if (pos.status === 'CLOSED' || pos.status === 'EXIT_PARTIAL') {
  if (pos.exitCriterion) {
    exitType = pos.exitCriterion;
  } else {
    const exitEvent = positionAuditEvents.find(
      (e) => e.eventType === 'execution.exit.triggered',
    );
    if (exitEvent) {
      const details = this.parseAuditDetails(exitEvent.details, exitEvent.id);
      exitType = (details.exitType as string) ?? (details.type as string) ?? 'unknown';
    } else {
      exitType = 'manual';
    }
  }
}
```

Prefer `exitCriterion` (reliable, persisted at close time). Fallback to audit event with corrected field name.

### Change 5: Fix `getPositionById()` (`dashboard.service.ts`)

**5a — exitType (line 359):**
```typescript
// OLD:
exitType: null,

// NEW:
exitType:
  pos.status === 'CLOSED' || pos.status === 'EXIT_PARTIAL'
    ? pos.exitCriterion ?? null
    : null,
```

**5b — 4 model-mode fields (after line 365):**
```typescript
// Add after dataSource line:
exitMode: enrichment.data.exitMode ?? null,
exitCriteria: enrichment.data.exitCriteria ?? null,
closestCriterion: enrichment.data.closestCriterion ?? null,
closestProximity: enrichment.data.closestProximity ?? null,
```

### Test Patterns

**Framework:** Vitest (`import { describe, it, expect, vi, beforeEach } from 'vitest'`)

**Enrichment spec** (`position-enrichment.service.spec.ts`):
- Mock factory: `createMockPriceFeed()` with `getVwapClosePrice: vi.fn()`
- Position factory: `createMockPosition({ status: 'CLOSED', exitMode: 'model', exitCriterion: 'edge_evaporation', lastEvalCriteria: [...], ... })`
- Assert price feed NOT called: `expect(priceFeed.getVwapClosePrice).not.toHaveBeenCalled()`
- Assert frozen data: `expect(result.data.currentPrices).toEqual({ kalshi: null, polymarket: null })`
- EXIT_PARTIAL regression: `createMockPosition({ status: 'EXIT_PARTIAL' })` — verify `priceFeed.getVwapClosePrice` IS called

**Dashboard service spec** (`dashboard.service.spec.ts`):
- Mock factory: `createMockPrisma()`, `createMockEnrichmentService()`, `createMockPositionRepository()`
- Direct constructor injection (no TestBed)
- Enrichment mock returns `{ status: 'enriched', data: { exitMode: 'model', exitCriteria: [...], closestCriterion: 'edge_evaporation', closestProximity: 0.85, ... } }`
- Assert response fields: `expect(result.data[0]!.exitMode).toBe('model')`
- For exitType tests: mock position with `{ status: 'CLOSED', exitCriterion: 'edge_evaporation' }` and verify `result.data[0]!.exitType === 'edge_evaporation'`
- For audit fallback: mock position without exitCriterion, mock audit events with `{ details: JSON.stringify({ exitType: 'time_decay' }) }`

**Dashboard audit service spec** (`dashboard-audit.service.spec.ts`):
- Mock factory: `createMockPrisma()`, `createMockEnrichmentService()`, `createMockEventEmitter()`, `createMockCapitalService()`
- Assert exitType: `expect(result!.exitType).toBe('edge_evaporation')`

**Paper/live boundary** (`paper-live-boundary/dashboard.spec.ts`):
- Uses `.each()` pattern for mode variations
- Existing tests verify `getPositions(mode)` filtering and `getOverview()` capital separation
- Add new tests verifying CLOSED position enrichment returns frozen data for both paper and live modes

### What NOT To Do

- Do NOT modify any frontend files — the frontend already handles all edge cases correctly
- Do NOT regenerate the API client — all fields already present in generated types
- Do NOT create DB migrations — `exitCriterion`, `exitMode`, `lastEvalCriteria` columns already exist
- Do NOT modify `exit-monitor.service.ts` — the exit monitor is not touched by this story
- Do NOT change the `return;` on line 65 of `trading-engine.service.ts` (live engine stays disabled)
- Do NOT use `configService.get<boolean>()` or `configService.get<number>()` — use `ConfigAccessor`
- Do NOT modify `ExitProximityIndicator.tsx`, `ModelRiskRewardCell.tsx`, or `RiskRewardCell.tsx`

### Previous Story Intelligence (10-96-5)

- **Test baseline:** 4004 tests pass, 1 pre-existing e2e failure (unchanged since 10-96-5)
- **Pattern:** TDD red-green cycle per unit of behavior
- **Code review:** 3-layer adversarial (Blind Hunter + Edge Case Hunter + Acceptance Auditor)
- **Key learning:** `getPositionDetails()` in `dashboard-audit.service.ts` (lines 211-214) ALREADY includes the 4 model-mode fields from enrichment — the detail view works, only the list view (`getPositions()`) and single-position view (`getPositionById()`) are broken
- **Key learning:** Enrichment service already computes `closestCriterion`/`closestProximity` from `lastEvalCriteria` (lines 321-351) — the CLOSED early return mirrors this logic

### Git Intelligence

Recent engine commits follow the pattern: `feat:` prefix for new features, `fix:` for bug fixes. Most recent relevant commit: `68d0115 feat: implement exitMode persistence in ExitMonitorService` (Story 10-96-5).

### Project Structure Notes

- All 3 modified files are in `pm-arbitrage-engine/src/dashboard/` — within the dashboard module boundary
- No module boundary violations — changes are purely within dashboard service layer
- `exitCriterion` field is on `OpenPosition` model (Prisma schema) — already exists since Story 10-96-3
- `exitMode` field is on `OpenPosition` model — persisted since Story 10-96-5
- `lastEvalCriteria` field is on `OpenPosition` model — persisted since Story 10-2

### Files Modified

- `pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts` — CLOSED early return (new code ~40 lines)
- `pm-arbitrage-engine/src/dashboard/dashboard.service.ts` — Wire 4 fields in `getPositions()` + `getPositionById()`; exitType from `exitCriterion` (~15 lines changed)
- `pm-arbitrage-engine/src/dashboard/dashboard-audit.service.ts` — exitType from `exitCriterion` in `getPositionDetails()` (~10 lines changed)

### References

- [Source: sprint-change-proposal-2026-04-16-closed-position-exit-data-fix.md] — 5 root causes, 6 changes, data flow diagram
- [Source: 10-96-5-dashboard-model-mode-risk-reward-exit-proximity-fix.md] — Previous story with RC-1 fix
- [Source: epics.md#Epic-10.96] — Live Trading Engine Alignment epic
- [Source: prd.md#FR-EM-03] — "System shall trigger exits based on five criteria"
- [Source: prd.md#FR-MA-04] — "System shall provide lightweight web dashboard"
- [Source: CLAUDE.md#Testing] — Co-located specs, assertion depth, paper/live boundary tests
- [Source: CLAUDE.md#Financial-Math] — decimal.js requirement for `recalculatedEdge`/`edgeDelta` computation

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- No halts or blockers encountered during implementation.

### Completion Notes List
- **Task 1:** Added CLOSED early-return guard in `position-enrichment.service.ts:enrich()`. Inserts after resolution date computation, before VWAP fetch. Returns frozen data (null currentPrices/currentEdge/unrealizedPnl/exitProximity) with populated exitMode/exitCriteria/closestCriterion/closestProximity/recalculatedEdge/edgeDelta from DB fields. EXIT_PARTIAL regression guard confirmed — CLOSED guard does NOT intercept EXIT_PARTIAL. 7 new tests added.
- **Task 2:** Wired 4 missing fields (exitMode, exitCriteria, closestCriterion, closestProximity) in `getPositions()` response mapping. 1 new test.
- **Task 3:** `getPositions()` now reads exitType from `pos.exitCriterion` first, falls back to audit event. Audit event field name fixed: `details.exitType ?? details.type` for backward compatibility. 2 new tests.
- **Task 4:** `getPositionDetails()` now prefers `pos.exitCriterion` for exitType, falls back to audit event with corrected field name `details.exitType ?? details.type`. 2 new tests.
- **Task 5:** `getPositionById()` now reads exitType from `pos.exitCriterion` (was hardcoded null) and includes 4 model-mode fields from enrichment. 2 new tests.
- **Task 6:** Paper/live boundary tests added for CLOSED position enrichment — verifies frozen data for both paper and live modes. 2 new tests.
- **Task 7:** Lint passes (auto-fix applied). Full suite: 4021 tests pass (+17 from 4004 baseline), 1 pre-existing e2e failure unchanged.

### File List
- `pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts` — CLOSED early-return guard (~40 lines added)
- `pm-arbitrage-engine/src/dashboard/position-enrichment.service.spec.ts` — 7 new tests for CLOSED early return
- `pm-arbitrage-engine/src/dashboard/dashboard.service.ts` — Wire 4 fields in getPositions() + getPositionById(); exitType from exitCriterion; audit field name fix
- `pm-arbitrage-engine/src/dashboard/dashboard.service.spec.ts` — 7 new tests (getPositions: 3, getPositionById: 2, mock fix: parseAuditDetails added)
- `pm-arbitrage-engine/src/dashboard/dashboard-audit.service.ts` — exitType from exitCriterion in getPositionDetails(); audit field name fix
- `pm-arbitrage-engine/src/dashboard/dashboard-audit.service.spec.ts` — 2 new tests for getPositionDetails exitType
- `pm-arbitrage-engine/src/common/testing/paper-live-boundary/dashboard.spec.ts` — 2 new tests for CLOSED paper/live enrichment

### Change Log
- 2026-04-16: Implemented all 7 tasks for Story 10-96-6. Fixed 5 root causes: RC-1 getPositions() missing 4 model-mode fields, RC-2 exitType audit field name mismatch, RC-3 exitType now reads from exitCriterion (bypasses redundant audit lookup), RC-4 enrichment skips VWAP fetch for CLOSED positions, RC-5 getPositionById() hardcoded exitType:null + missing model-mode fields. 17 new tests, 4021 total pass.
