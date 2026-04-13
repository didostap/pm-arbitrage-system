# Sprint Change Proposal: Closed Position Exit Data Fix

**Date:** 2026-04-16
**Trigger:** Post-implementation observation after Story 10-96-5 (model-mode dashboard columns)
**Epic:** 10.96 (Live Trading Engine Alignment & Configuration Calibration)
**Scope Classification:** Minor — Direct Adjustment (one bug-fix story)

---

## Section 1: Issue Summary

Three closed-position display issues were identified during operational review after Story 10-96-5 shipped. Investigation revealed that 10-96-5's own list-view fix is partially ineffective due to a missing backend wiring gap that predates 10-96-5.

### Root Causes (5 interconnected)

**RC-1: `getPositions()` response omits 4 model-mode fields** (`dashboard.service.ts:251-288`)
The response mapping in `getPositions()` does not include `exitMode`, `exitCriteria`, `closestCriterion`, or `closestProximity` — even though the enrichment service computes them (lines 374-377 of `position-enrichment.service.ts`) and the DTO declares them (lines 240-274 of `position-summary.dto.ts`). **This means Story 10-96-5's frontend fixes for Risk/Reward and Exit Proximity columns are inert on the list view** — the data never reaches the frontend.

**RC-2: `exitType` derived from audit events using wrong field name** (`dashboard.service.ts:189`, `dashboard-audit.service.ts:154`)
Both services read `details.type` from audit events, but the `ExitTriggeredEvent` stores the value as `details.exitType`. Since `details.type` is always undefined, the `?? 'unknown'` fallback triggers 100% of the time.

**RC-3: `exitType` lookup is redundant** (`dashboard.service.ts:147-199`)
The `exitCriterion` field is already correctly persisted on every closed position record (added in Story 10-96-3). The audit event lookup is an unnecessary extra DB query that also happens to be broken (RC-2). Database confirms all 10 closed positions have populated `exit_criterion`.

**RC-4: Enrichment service fetches live prices for CLOSED positions** (`position-enrichment.service.ts:66`)
`enrich()` has no status check — it always fetches live VWAP prices and computes dynamic `exitProximity`, `currentEdge`, and `unrealizedPnl`. For closed positions, this produces misleading values (prices continue fluctuating after close) and wastes API calls.

**RC-5: `getPositionById()` hardcodes `exitType: null`** (`dashboard.service.ts:359`)
The single-position endpoint never reads `pos.exitCriterion` and omits the 4 model-mode fields, matching the RC-1 gap.

### Evidence

| Evidence | Source |
|----------|--------|
| All 10 closed positions have `exit_criterion` populated | `SELECT exit_criterion FROM open_positions WHERE status='CLOSED'` |
| All 10 closed positions have `exit_mode = 'model'` | Same query |
| All 10 closed positions have `last_eval_criteria` populated | Same query |
| All audit events store `exitType`, not `type` | `SELECT details->>'exitType', details->>'type' FROM audit_logs WHERE event_type='execution.exit.triggered'` — exitType populated, type NULL |
| `getPositions()` omits 4 fields | `dashboard.service.ts:251-288` — no `exitMode`, `exitCriteria`, `closestCriterion`, `closestProximity` |
| `getPositionById()` hardcodes exitType | `dashboard.service.ts:359` — `exitType: null` |
| Enrichment has no CLOSED check | `position-enrichment.service.ts:66` — no early return for closed positions |

### Data Flow Showing the Disconnects

```
Closed Position in DB:
  exit_mode = 'model' ✓
  exit_criterion = 'edge_evaporation' ✓
  last_eval_criteria = [{...6 criteria...}] ✓
         │
getPositions() → enrichmentService.enrich(pos)
         │
Enrichment:
  ├── Fetches LIVE VWAP prices (wasteful, misleading) ← RC-4
  ├── Computes dynamic exitProximity (wrong for closed) ← RC-4
  ├── Reads exitMode='model' ✓
  ├── Reads lastEvalCriteria → closestCriterion ✓
  └── Returns all fields to getPositions()
         │
getPositions() response mapping:
  ├── exitProximity: enrichment.data.exitProximity ✓ (but dynamically calculated)
  ├── exitType: audit event lookup → details.type → undefined → 'unknown' ← RC-2/RC-3
  ├── exitMode: NOT INCLUDED ← RC-1
  ├── exitCriteria: NOT INCLUDED ← RC-1
  ├── closestCriterion: NOT INCLUDED ← RC-1
  └── closestProximity: NOT INCLUDED ← RC-1
         │
Frontend receives:
  exitMode = undefined → ExitModeBadge returns null (blank) ← Issue 3
  exitType = 'unknown' → ExitTypeBadge shows "unknown" ← Issue 2
  exitProximity = live values → shows SL/TP bars for closed positions ← Issue 1
  closestCriterion = undefined → model branch never activates ← 10-96-5 ineffective
```

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| **10.96** (in-progress) | **Add 1 story** | Bug-fix story completing 10-96-5's intent. Fits the epic's "live engine alignment" scope. |
| 11+ (backlog) | None | No downstream impact. |

No epics invalidated, no resequencing needed.

### Story Impact

| Story | Relationship | Details |
|-------|-------------|---------|
| **10-96-5** (done) | **Cascading gap** | 10-96-5 fixed exitMode persistence and created ModelRiskRewardCell, but the list view is inert because getPositions() never wires the fields through. The detail view works because getPositionDetails() in dashboard-audit.service.ts:211-214 DOES include the fields. |
| **10-96-3** (done) | **Prerequisite complete** | Added exitCriterion column and persistence on close — makes the audit event lookup redundant. |
| **10-2** (done) | **AC completion** | Original AC: "each position shows: which criterion is closest to triggering, proximity percentage per criterion, and exit mode indicator" — the list view AC is unmet until RC-1 is resolved. |
| **New: 10-96-6** | **Proposed** | Closed position exit data fix (this proposal). |

### Artifact Conflicts

| Artifact | Conflict | Action |
|----------|----------|--------|
| PRD | None | FR-EM-03 requires model-driven dashboard display. FR-MA-04 requires position views. Fix aligns. |
| Architecture | None | Fix is within dashboard service boundary. No new imports or patterns. |
| UX Spec | None | Columns already exist. Fix makes them data-correct for closed positions. |
| Epics | None | Story 10.2 ACs already require this behavior. |

### Technical Impact

**Backend (pm-arbitrage-engine):** 3 files modified
- `dashboard.service.ts` — Wire 4 missing fields in getPositions() + getPositionById(); read exitType from exitCriterion
- `dashboard-audit.service.ts` — Read exitType from exitCriterion; fix audit event field name as fallback
- `position-enrichment.service.ts` — Early return for CLOSED positions (skip live price fetch, return frozen data)

**Frontend (pm-arbitrage-dashboard):** 1 file modified
- `PositionsPage.tsx` — Exit Proximity column: show "—" for closed positions in fixed mode

**No DB migrations.** All required fields already exist.
**No new dependencies.** All data already persisted.

---

## Section 3: Recommended Approach

**Selected: Option 1 — Direct Adjustment**

Add one story (10-96-6) to Epic 10.96. This is a focused bug-fix touching 4 files, all within the dashboard service boundary.

**Rationale:**
- RC-1 (missing field mapping) is a 4-line addition
- RC-2/RC-3 (exitType) is a simplification — replace fragile audit event lookup with direct field read
- RC-4 (enrichment for closed positions) is a clean early-return guard
- RC-5 (getPositionById) mirrors the RC-1/RC-2 fixes
- All required data is already in the database — no new persistence
- Effort: Low (4 files, ~40-60 lines changed)
- Risk: Low (display-layer fixes + one performance improvement from skipping live price fetch for closed positions)

**Alternatives considered:**
- Rollback: Nothing to roll back — 10-96-5's backend fix (exitMode persistence) is correct and should stay
- PRD Review: Not needed — PRD already requires this behavior

---

## Section 4: Detailed Change Proposals

### Change 1: Wire Missing Fields in `getPositions()` (RC-1)

**File:** `pm-arbitrage-engine/src/dashboard/dashboard.service.ts` (lines 251-288)

```
OLD (lines 282-288):
              recalculatedEdge: enrichment.data.recalculatedEdge ?? null,
              edgeDelta: enrichment.data.edgeDelta ?? null,
              lastRecalculatedAt: enrichment.data.lastRecalculatedAt ?? null,
              dataSource: enrichment.data.dataSource ?? null,
            };

NEW:
              recalculatedEdge: enrichment.data.recalculatedEdge ?? null,
              edgeDelta: enrichment.data.edgeDelta ?? null,
              lastRecalculatedAt: enrichment.data.lastRecalculatedAt ?? null,
              dataSource: enrichment.data.dataSource ?? null,
              exitMode: enrichment.data.exitMode ?? null,
              exitCriteria: enrichment.data.exitCriteria ?? null,
              closestCriterion: enrichment.data.closestCriterion ?? null,
              closestProximity: enrichment.data.closestProximity ?? null,
            };
```

**Rationale:** These 4 fields are computed by the enrichment service, declared in the DTO, and expected by the frontend. The gap was introduced when Story 10.2 added the fields to the enrichment service and DTO but never updated the getPositions() mapping. This is the critical fix that unblocks Story 10-96-5's frontend changes.

### Change 2: Read `exitType` from `exitCriterion` (RC-2, RC-3)

**File:** `pm-arbitrage-engine/src/dashboard/dashboard.service.ts` (lines 232-236)

```
OLD:
            if (pos.status === 'CLOSED') {
              exitType = exitTypeByPairId.get(pos.pairId) ?? null;

NEW:
            if (pos.status === 'CLOSED') {
              exitType = pos.exitCriterion ?? exitTypeByPairId.get(pos.pairId) ?? null;
```

**Rationale:** Read directly from the position's `exitCriterion` field (persisted at close time since Story 10-96-3). Falls back to audit event lookup for pre-10-96-3 positions. This bypasses the field name mismatch (RC-2) for all recent positions.

**Additionally**, fix the audit event field name as fallback:

**File:** `pm-arbitrage-engine/src/dashboard/dashboard.service.ts` (line 189)

```
OLD:
            exitTypeByPairId.set(
              pairId,
              (details?.type as string) ?? 'unknown',
            );

NEW:
            exitTypeByPairId.set(
              pairId,
              (details?.exitType as string) ?? (details?.type as string) ?? 'unknown',
            );
```

**Rationale:** The `ExitTriggeredEvent` serializes the exit type as `exitType`, not `type`. Check both field names for backward compatibility.

### Change 3: Fix `exitType` in `getPositionDetails()` (RC-2)

**File:** `pm-arbitrage-engine/src/dashboard/dashboard-audit.service.ts` (lines 144-158)

```
OLD:
      let exitType: string | null = null;
      if (pos.status === 'CLOSED' || pos.status === 'EXIT_PARTIAL') {
        const exitEvent = positionAuditEvents.find(
          (e) => e.eventType === 'execution.exit.triggered',
        );
        if (exitEvent) {
          const details = this.parseAuditDetails(
            exitEvent.details,
            exitEvent.id,
          );
          exitType = (details.type as string) ?? 'unknown';
        } else {
          exitType = 'manual';
        }
      }

NEW:
      let exitType: string | null = null;
      if (pos.status === 'CLOSED' || pos.status === 'EXIT_PARTIAL') {
        if (pos.exitCriterion) {
          exitType = pos.exitCriterion;
        } else {
          const exitEvent = positionAuditEvents.find(
            (e) => e.eventType === 'execution.exit.triggered',
          );
          if (exitEvent) {
            const details = this.parseAuditDetails(
              exitEvent.details,
              exitEvent.id,
            );
            exitType = (details.exitType as string) ?? (details.type as string) ?? 'unknown';
          } else {
            exitType = 'manual';
          }
        }
      }
```

**Rationale:** Same pattern as Change 2 — prefer `exitCriterion` (reliable), fallback to audit event with corrected field name.

### Change 4: Enrichment Early Return for CLOSED Positions (RC-4)

**File:** `pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts`

After the resolution date computation (line 85) and before the order fill data validation (line 98), add an early return for CLOSED positions:

```
NEW (insert after line 95):
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

**Rationale:** Closed positions should not trigger live price fetching. All meaningful data (recalculated edge, exit criteria, exit mode) is already persisted. Returning null for currentPrices/currentEdge/unrealizedPnl/exitProximity is correct — the frontend already renders "—" for null values, and the P&L column already switches to realized P&L for CLOSED positions (PositionsPage.tsx:153).

### Change 5: Fix `getPositionById()` (RC-5)

**File:** `pm-arbitrage-engine/src/dashboard/dashboard.service.ts` (lines 326-366)

```
OLD (line 359):
        exitType: null,

NEW:
        exitType:
          pos.status === 'CLOSED' || pos.status === 'EXIT_PARTIAL'
            ? pos.exitCriterion ?? null
            : null,
```

And add the 4 missing model-mode fields (after `dataSource`):

```
OLD (lines 364-366):
              dataSource: enrichment.data.dataSource ?? null,
            };

NEW:
              dataSource: enrichment.data.dataSource ?? null,
              exitMode: enrichment.data.exitMode ?? null,
              exitCriteria: enrichment.data.exitCriteria ?? null,
              closestCriterion: enrichment.data.closestCriterion ?? null,
              closestProximity: enrichment.data.closestProximity ?? null,
            };
```

**Rationale:** Matches getPositions() behavior. The single-position endpoint should return the same fields.

### Change 6: Frontend — Exit Proximity for Closed Positions

**File:** `pm-arbitrage-dashboard/src/pages/PositionsPage.tsx` (lines 187-215)

The Exit Proximity column currently renders proximity data for all positions. For closed positions in model/shadow mode, the frozen `closestCriterion`/`closestProximity` from `lastEvalCriteria` is meaningful. For closed positions in fixed mode (or when closestCriterion is unavailable and exitProximity is null), show "—".

After Change 4 (enrichment returns null exitProximity for closed), the existing fallback at line 212 (`if (!prox) return <span className="text-muted-foreground">—</span>`) handles this automatically. No frontend code change needed for this path — the enrichment fix handles it.

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

Direct implementation by development team. No backlog reorganization or strategic replanning needed.

### Story Definition

**Story 10-96-6: Closed Position Exit Data Fix**

As an operator,
I want closed positions to display frozen exit data (exit type, exit mode, exit criteria) correctly and not continue calculating dynamic values from live market data,
so that my position history accurately reflects the state at the time each position was closed.

**Context:** Story 10-96-5 fixed exitMode persistence and added model-mode column branching, but the list view remains broken because `getPositions()` never wires `exitMode`/`exitCriteria`/`closestCriterion`/`closestProximity` through to the response. Additionally, `exitType` is derived from audit events using the wrong field name (`details.type` instead of `details.exitType`), and the enrichment service fetches live VWAP prices for closed positions (wasteful and misleading).

**Sprint Change Proposal:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16-closed-position-exit-data-fix.md`

**Acceptance Criteria:**

1. **Given** the Positions page displays closed positions, **When** the Exit Mode column renders, **Then** it shows the correct exit mode badge (model/fixed/shadow) — not blank.

2. **Given** the Positions page displays closed positions, **When** the Exit Type column renders, **Then** it shows the correct exit criterion (edge_evaporation, time_decay, etc.) — not "unknown".

3. **Given** a closed position in model/shadow mode, **When** the Exit Proximity column renders, **Then** it shows the frozen closest criterion name and proximity percentage from `lastEvalCriteria` — not dynamically calculated SL/TP proximity.

4. **Given** a closed position in fixed mode (or without lastEvalCriteria), **When** the Exit Proximity column renders, **Then** it shows "—" — not dynamically calculated values.

5. **Given** a closed position, **When** the enrichment service processes it, **Then** it does NOT fetch live VWAP prices from the price feed (no API calls for closed positions).

6. **Given** a closed position, **When** the enrichment service returns, **Then** `currentPrices`, `currentEdge`, `unrealizedPnl`, and `exitProximity` are null; `exitMode`, `exitCriteria`, `closestCriterion`, `closestProximity`, `recalculatedEdge`, `edgeDelta` are populated from frozen DB fields.

7. **Given** an EXIT_PARTIAL position, **When** the enrichment service processes it, **Then** it continues to fetch live VWAP prices and compute dynamic values (zero regression for active positions).

8. **Given** the single-position endpoint (`getPositionById`), **When** it returns a closed position, **Then** `exitType` is read from `exitCriterion` (not hardcoded null) and all 4 model-mode fields are included.

9. **Given** the position detail endpoint (`getPositionDetails`), **When** it returns a closed position, **Then** `exitType` is read from `exitCriterion` (fallback to audit event with corrected field name `exitType`).

**Tasks:**
1. Backend: Add CLOSED early-return guard in `position-enrichment.service.ts` (AC: #3, #4, #5, #6, #7)
2. Backend: Wire 4 missing fields in `getPositions()` response mapping (AC: #1, #3)
3. Backend: Read exitType from `pos.exitCriterion` in `getPositions()` + fix audit fallback field name (AC: #2)
4. Backend: Fix exitType in `getPositionDetails()` — prefer exitCriterion, fix audit fallback field name (AC: #9)
5. Backend: Fix `getPositionById()` — exitType from exitCriterion + 4 missing fields (AC: #8)
6. Tests: Enrichment spec — CLOSED early return (no price fetch, frozen data returned)
7. Tests: Enrichment spec — EXIT_PARTIAL still gets live enrichment (regression guard)
8. Tests: Dashboard service spec — getPositions() includes exitMode/exitCriteria/closestCriterion/closestProximity
9. Tests: Dashboard service spec — exitType from exitCriterion, fallback to audit event with corrected field name
10. Tests: Paper/live boundary — closed position enrichment respects mode filter
11. Lint + full test suite green

**Files Modified:**
- `pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts` — CLOSED early return
- `pm-arbitrage-engine/src/dashboard/dashboard.service.ts` — Wire fields + exitType fix in getPositions() and getPositionById()
- `pm-arbitrage-engine/src/dashboard/dashboard-audit.service.ts` — exitType fix in getPositionDetails()

**Dependencies:** Story 10-96-5 (done) — exitMode persistence. Story 10-96-3 (done) — exitCriterion column.
**Estimated Effort:** Small (3 backend files, ~60-80 lines changed, ~8-10 new tests)
**Risk:** Low (display-layer fixes + performance improvement from skipping live price fetch for closed positions)

### Handoff

| Role | Responsibility |
|------|---------------|
| Dev Agent | Implement story 10-96-6 following TDD |
| Arbi (operator) | Verify closed position display after deployment |

### Success Criteria

- Closed positions show correct Exit Mode badge (model/fixed/shadow)
- Closed positions show correct Exit Type (edge_evaporation, time_decay, etc.)
- Closed positions in model mode show frozen criteria in Exit Proximity column
- Closed positions do NOT trigger live VWAP price fetching
- EXIT_PARTIAL positions continue to work correctly (live enrichment)
- All existing tests pass, new tests cover the fixes

---

## Checklist Completion Summary

| Section | Status |
|---------|--------|
| 1. Trigger & Context | [x] Done — 5 root causes identified with DB evidence and code-level tracing |
| 2. Epic Impact | [x] Done — 1 story added to Epic 10.96, no other epics affected |
| 3. Artifact Conflicts | [x] Done — No PRD/Architecture/UX conflicts |
| 4. Path Forward | [x] Done — Direct Adjustment selected |
| 5. Proposal Components | [x] Done — Story 10-96-6 defined with 9 ACs and 11 tasks |
| 6. Final Review | [ ] Pending user approval |
