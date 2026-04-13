# Story 10-96.5: Dashboard Model-Mode Risk/Reward & Exit Proximity Fix

Status: done

## Story

As an operator,
I want the Risk/Reward and Exit Proximity columns to dynamically adapt their display based on the active exit mode,
so that I see relevant criteria data when running in model or shadow mode instead of misleading fixed-mode SL/TP thresholds.

## Context

Story 10-2 implemented six-criteria model-driven exits with dashboard display. The exit monitor correctly evaluates all six criteria in model/shadow mode and persists `lastEvalCriteria` to each position's DB record. However, the position's `exitMode` field is frozen at creation time (set once in `execution.service.ts:1044`) and never updated by the exit monitor. When the engine runs `EXIT_MODE=model`, the dashboard still shows fixed-mode SL/TP data because `position.exitMode` reads as `'fixed'`.

**Four interconnected root causes:**
- **RC-1:** `exitMode` frozen at position creation — `recalculateAndPersistEdge()` never writes `exitMode` to the position record
- **RC-2:** Risk/Reward column has zero mode-awareness — always renders `<RiskRewardCell sl tp />` (fixed SL/TP thresholds)
- **RC-3:** Exit Proximity frontend gate checks stale `exitMode` — the existing `pos.exitMode === 'model'` branch never activates because the DB value is `'fixed'`
- **RC-4:** Backend enrichment always computes fixed-mode data — but this auto-resolves with RC-1 fix since enrichment already reads `position.exitMode` and computes `closestCriterion`/`closestProximity` from `lastEvalCriteria`

**Sprint Change Proposal:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-15-model-mode-dashboard-columns.md`

## Acceptance Criteria

1. **Given** the exit monitor evaluates a position, **When** `recalculateAndPersistEdge()` runs, **Then** the position's `exitMode` field is updated to the current engine exit mode on every evaluation cycle.

2. **Given** the engine is running in model mode, **When** the Positions page displays open positions, **Then** the Exit Proximity column shows the closest criterion name and proximity percentage (not SL/TP bars). *(Note: this already works in the frontend code — AC is satisfied once RC-1 is fixed.)*

3. **Given** the engine is running in model mode, **When** the Positions page displays open positions, **Then** the Risk/Reward column shows criteria-based risk/reward: highest-proximity loss criterion as "Risk", profit_capture proximity as "Reward" (not fixed SL/TP projected P&L).

4. **Given** the engine is running in fixed mode, **When** the Positions page displays open positions, **Then** both columns display the existing SL/TP data (zero regression).

5. **Given** the engine is running in shadow mode, **When** the Positions page displays open positions, **Then** both columns display model-mode data (shadow uses model for display, fixed for decisions).

6. **Given** a position was created in fixed mode but the engine has since switched to model mode, **When** the exit monitor runs its next evaluation cycle, **Then** the position's `exitMode` is updated to `'model'` and the dashboard reflects the new mode on next refresh.

7. **Given** a `ModelRiskRewardCell` is rendered, **When** the operator hovers over it, **Then** a tooltip shows all six criteria with their proximity percentages.

## Tasks / Subtasks

- [x] Task 1: Backend — Add `exitMode` to `updateData` in `recalculateAndPersistEdge()` (AC: #1, #6)
  - [x] 1.1 In `exit-monitor.service.ts` method `recalculateAndPersistEdge()` (line ~823), add `exitMode` to the `updateData` object
  - [x] 1.2 Write test in `exit-monitor-data-source.spec.ts` (alongside existing updateData tests at lines 121-135): verify `prisma.openPosition.update` is called with `data` containing `exitMode` matching the service's current exit mode
  - [x] 1.3 Write test in `exit-monitor-criteria.integration.spec.ts` (alongside existing criteria persistence tests): verify mode transition — position created with `exitMode: 'fixed'`, then evaluated with service `exitMode = 'model'` → `updateData` contains `exitMode: 'model'`
  - [x] 1.4 Paper/live boundary test: verify `exitMode` is persisted for both paper and live positions (use `createMockPosition({ isPaper: true })` and `createMockPosition({ isPaper: false })`)

- [x] Task 2: Frontend — Create `ModelRiskRewardCell` component (AC: #3, #7)
  - [x] 2.1 Create `pm-arbitrage-dashboard/src/components/cells/ModelRiskRewardCell.tsx`
  - [x] 2.2 Define known criteria constants and filter defensively: `const RISK_CRITERIA = ['edge_evaporation', 'model_confidence', 'time_decay', 'risk_budget', 'liquidity_deterioration']` and `const REWARD_CRITERIA = ['profit_capture']`. Filter incoming criteria to known names with valid numeric proximity (`!isNaN(parseFloat(c.proximity))`)
  - [x] 2.3 Display highest-proximity risk criterion name + proximity % in red (`text-red-600`); profit_capture proximity % in green (`text-emerald-600`). Edge cases: if no valid risk criteria found → show `—` for risk; if no `profit_capture` → show `—` for reward; if criteria array is empty or all invalid → return `<span className="text-muted-foreground">—</span>` (consistent with `RiskRewardCell` null pattern)
  - [x] 2.4 Tooltip on hover: show all six criteria with proximity percentages. Add `data-testid="model-risk-reward-cell"` on container, `data-testid="risk-criterion-name"` on risk label, `data-testid="reward-criterion-value"` on reward value
  - [x] 2.5 Export from `components/cells/index.ts`

- [x] Task 3: Frontend — Add model-mode branching to Risk/Reward column (AC: #3, #4, #5)
  - [x] 3.1 In `PositionsPage.tsx` Risk/Reward column (lines 164-173), add `exitMode === 'model' || exitMode === 'shadow'` branch. Preserve existing `pos.status === 'CLOSED'` check ABOVE the mode branch (line 169 — must remain first)
  - [x] 3.2 When model/shadow AND `exitCriteria?.length`: render `<ModelRiskRewardCell criteria={pos.exitCriteria} />`
  - [x] 3.3 Fallthrough to existing `<RiskRewardCell>` for fixed mode or missing criteria data

- [x] Task 4: Verify Exit Proximity column works (AC: #2)
  - [x] 4.1 Confirm `PositionsPage.tsx` Exit Proximity column (lines 184-213) already has correct model/shadow branching — no code change needed, just verify after RC-1 fix

- [x] Task 5: Lint + full test suite green (AC: all)
  - [x] 5.1 Run `cd pm-arbitrage-engine && pnpm lint && pnpm test`
  - [x] 5.2 Verify dashboard builds cleanly: `cd pm-arbitrage-dashboard && pnpm build`

## Dev Notes

### Dual-Repo Structure

This story spans **two independent git repos** — commit separately:
- `pm-arbitrage-engine/` — backend fix (Task 1)
- `pm-arbitrage-dashboard/` — frontend changes (Tasks 2-4)

### Backend Fix — Exact Location

**File:** `pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts`
**Method:** `recalculateAndPersistEdge()` (lines 768-855)

The `updateData` object is constructed at lines 823-828:
```typescript
const updateData: Record<string, unknown> = {
  recalculatedEdge: recalculatedEdge.toFixed(8),
  lastRecalculatedAt: now,
  recalculationDataSource: dataSource,
};
```

Add `exitMode` to this object. The `exitMode` parameter is already available in the method signature (passed from `this.exitMode` which is typed as `ExitMode = 'fixed' | 'model' | 'shadow'` from `common/types/exit-criteria.types.ts`).

The conditional block at lines 830-839 already handles `lastEvalCriteria` persistence for model/shadow modes — the `exitMode` write is unconditional (write it regardless of mode so the position always reflects the active engine mode).

**No enrichment changes needed.** `position-enrichment.service.ts` (line 322) already reads `position.exitMode` and computes `closestCriterion`/`closestProximity` from `lastEvalCriteria` (lines 321-351). With the RC-1 fix, the enrichment response automatically becomes correct.

### Backend Test Patterns

Use existing test infrastructure in `exit-monitor.test-helpers.ts`:
- `createExitMonitorTestModule()` — factory for test module context
- `createMockPosition(overrides)` — position factory with spread overrides
- Assertion pattern: `expect(prisma.openPosition.update).toHaveBeenCalledWith(expect.objectContaining({ data: expect.objectContaining({ exitMode: 'model' }) }))`

Existing test examples:
- `exit-monitor-data-source.spec.ts` (lines 121-135) — verifies `updateData` fields
- `exit-monitor-criteria.integration.spec.ts` (lines 534-548) — verifies `lastEvalCriteria` persistence

### Frontend — ModelRiskRewardCell Component

**New file:** `pm-arbitrage-dashboard/src/components/cells/ModelRiskRewardCell.tsx`

**Props interface:**
```typescript
interface ModelRiskRewardCellProps {
  criteria: Array<{
    criterion: string;
    proximity: string;
    triggered: boolean;
    detail?: string;
  }>;
}
```

**Criteria categorization:**
- **Risk criteria** (5): `edge_evaporation`, `model_confidence`, `time_decay`, `risk_budget`, `liquidity_deterioration`
- **Reward criteria** (1): `profit_capture`

**Display logic:**
- Find highest-proximity risk criterion → show name + `XX%` in red (`text-red-600`)
- Find profit_capture → show `XX%` in green (`text-emerald-600`)
- Use `font-mono tabular-nums` for numeric values (per UX spec)
- Tooltip: list all 6 criteria with proximity percentages

**Follow existing cell component patterns** (see `RiskRewardCell.tsx`, `ExitTypeBadge.tsx`):
- Handle null/invalid gracefully (return `—`)
- Use `Tooltip` / `TooltipTrigger` / `TooltipContent` from `@/components/ui/tooltip`
- `cursor-help` class on trigger element
- `text-xs` for cell content

**Criterion label formatting:** Replace underscores with spaces: `edge_evaporation` → `edge evaporation` (consistent with Exit Proximity column at line 194 of PositionsPage.tsx: `pos.closestCriterion.replace(/_/g, ' ')`)

### Frontend — Risk/Reward Column Modification

**File:** `pm-arbitrage-dashboard/src/pages/PositionsPage.tsx` (lines 164-173)

Add mode branch before existing `<RiskRewardCell>`:
```typescript
if ((pos.exitMode === 'model' || pos.exitMode === 'shadow') && pos.exitCriteria?.length) {
  return <ModelRiskRewardCell criteria={pos.exitCriteria} />;
}
return <RiskRewardCell sl={pos.projectedSlPnl} tp={pos.projectedTpPnl} />;
```

### Frontend — Exit Proximity Column (NO CHANGES)

The Exit Proximity column at lines 184-213 **already has correct model/shadow branching**:
```typescript
if ((pos.exitMode === 'model' || pos.exitMode === 'shadow') && pos.closestCriterion) {
  // Shows criterion name + proximity %
}
```
This code never activated because `pos.exitMode` was stale. With RC-1 fixed, it works automatically.

### API Types — Already Complete

The generated `PositionSummaryDto` in `pm-arbitrage-dashboard/src/api/generated/Api.ts` already includes all required fields:
- `exitMode?: string | null`
- `exitCriteria?: any[] | null`
- `closestCriterion?: string | null`
- `closestProximity?: number | null`
- `projectedSlPnl?: string | null`
- `projectedTpPnl?: string | null`

**No API client regeneration needed** — all fields are already in the contract.

### What NOT To Do

- Do NOT modify `position-enrichment.service.ts` — it already handles everything correctly after RC-1
- Do NOT modify `ExitProximityIndicator.tsx` — it's the fixed-mode component and works correctly
- Do NOT modify the Exit Proximity column definition — it already has correct branching
- Do NOT create DB migrations — `exitMode` column already exists on `OpenPosition`
- Do NOT regenerate the API client — all fields already present
- Do NOT change the `return;` on line 65 of `trading-engine.service.ts` (live engine stays disabled)
- Do NOT use `configService.get<boolean>()` or `configService.get<number>()` — use `ConfigAccessor`

### Previous Story Intelligence (10-96-4)

- Test suite baseline: 3908 tests (+ 3 pre-existing e2e failures)
- Structural guard baseline: `configService.get<number>()` count = 58, settings count = 101 (do not change)
- Pattern: TDD red-green cycle per unit of behavior
- Code review: 3-layer adversarial (Blind Hunter + Edge Case Hunter + Acceptance Auditor)

### Project Structure Notes

- Backend files in `pm-arbitrage-engine/src/modules/exit-management/` — within exit-management module boundary
- Frontend files in `pm-arbitrage-dashboard/src/components/cells/` and `src/pages/` — standard locations
- No module boundary violations — backend change is within exit-management, frontend change is within dashboard
- `ExitMode` type imported from `common/types/exit-criteria.types.ts`

### References

- [Source: sprint-change-proposal-2026-04-15-model-mode-dashboard-columns.md] — 4 root causes, 5 changes, data flow diagram
- [Source: epics.md#Story-10.2] — Original AC: "each position shows: which criterion is closest to triggering, proximity percentage per criterion, and exit mode indicator"
- [Source: prd.md#FR-EM-03] — "System shall trigger exits based on five criteria"
- [Source: architecture.md#Exit-Management] — Exit path architecture, WebSocket feed, position monitoring
- [Source: ux-design-specification.md#Typography] — `font-mono tabular-nums` for metric values, semantic color only
- [Source: CLAUDE.md#Testing] — Co-located specs, assertion depth, paper/live boundary tests

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None.

### Completion Notes List

- **Task 1 (Backend):** Added `exitMode` to `updateData` object in `recalculateAndPersistEdge()` — unconditional write on every evaluation cycle. 1 line of production code. 5 new tests: 1 unit (data-source spec verifies exitMode='fixed' in updateData), 2 integration (criteria spec: exitMode='model' persistence + fixed→model transition), 2 paper/live boundary (data-source spec: both isPaper=true and isPaper=false positions get exitMode persisted). Boundary test in `paper-live-boundary/exit.spec.ts` verifies mode-correct query path with updated connector mocks.
- **Task 2 (Frontend):** Created `ModelRiskRewardCell.tsx` — defensive filtering of criteria (known names + valid numeric proximity), highest-proximity risk criterion in red, profit_capture in green, tooltip with all 6 criteria. Handles empty/invalid criteria gracefully.
- **Task 3 (Frontend):** Added model/shadow mode branch to Risk/Reward column in `PositionsPage.tsx`. CLOSED check preserved as first gate. Falls through to existing `RiskRewardCell` for fixed mode or missing criteria.
- **Task 4 (Frontend):** Verified Exit Proximity column already has correct model/shadow branching at line 193. No changes needed — activates automatically with RC-1 fix.
- **Task 5:** Engine lint clean (0 new errors), 4004 tests pass (+7 from 3997 baseline), 1 pre-existing e2e failure unchanged. Dashboard builds clean.

### Change Log

- 2026-04-15: Story 10-96-5 implementation complete. RC-1 fixed (exitMode persisted on every eval cycle). ModelRiskRewardCell component created. Risk/Reward column mode-aware. Exit Proximity column auto-fixed via RC-1.

### File List

**pm-arbitrage-engine/ (backend)**
- `src/modules/exit-management/exit-monitor.service.ts` — added `exitMode` to updateData in recalculateAndPersistEdge()
- `src/modules/exit-management/exit-monitor-data-source.spec.ts` — +3 tests (exitMode persistence + paper/live boundary)
- `src/modules/exit-management/exit-monitor-criteria.integration.spec.ts` — +2 tests (exitMode model persistence + fixed→model transition)
- `src/common/testing/paper-live-boundary/exit.spec.ts` — +2 boundary tests (exitMode query path for paper/live), connector mocks updated with getFeeSchedule

**pm-arbitrage-dashboard/ (frontend)**
- `src/components/cells/ModelRiskRewardCell.tsx` — NEW: model-mode risk/reward cell component
- `src/components/cells/index.ts` — added ModelRiskRewardCell export
- `src/pages/PositionsPage.tsx` — added model/shadow mode branching to Risk/Reward column
