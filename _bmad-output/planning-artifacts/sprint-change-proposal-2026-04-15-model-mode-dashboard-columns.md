# Sprint Change Proposal: Model-Mode Dashboard Column Display Fix

**Date:** 2026-04-15
**Trigger:** Operational observation during model-mode paper trading
**Epic:** 10.96 (Live Trading Engine Alignment & Configuration Calibration)
**Scope Classification:** Minor — Direct Adjustment (one bug-fix story)

---

## Section 1: Issue Summary

When the engine runs with `EXIT_MODE=model`, the Positions page "Risk/Reward" and "Exit Proximity" columns display **fixed-mode** data — SL/TP dollar projections and SL/TP proximity bars — instead of adapting to the six-criteria model-driven exit logic implemented in Story 10-2.

**Evidence:** Screenshot shows SL/TP bars (25%, 0%, 17%) and fixed projected P&L (SL: -$91.57 / TP: +$22.50) while the engine is actively evaluating positions with six criteria. The exit monitor IS running model-mode evaluations and persisting `lastEvalCriteria` to the database, but the dashboard never renders this data.

**Discovery context:** Observed during live paper trading with model-mode enabled. The exit monitor correctly evaluates all six criteria and persists `lastEvalCriteria` to each position — but the dashboard ignores it and shows stale fixed-mode indicators.

### Root Causes (4 interconnected)

**RC-1: `exitMode` frozen at position creation time** (`execution.service.ts:1044`)
Position's `exitMode` is set once from `configService.get('EXIT_MODE')` at position open. The exit monitor evaluates using its own `this.exitMode` (the current engine config), but `recalculateAndPersistEdge()` never writes the current mode back to the position record. If the engine mode changes after position creation, the position retains a stale `exitMode`.

**RC-2: Risk/Reward column has zero mode-awareness** (`PositionsPage.tsx:168-172`)
The column always renders `<RiskRewardCell sl={pos.projectedSlPnl} tp={pos.projectedTpPnl} />` — fixed-mode SL/TP thresholds. No branching on `exitMode`. In model mode, these thresholds are irrelevant to actual exit decisions.

**RC-3: Exit Proximity frontend gate checks stale `exitMode`** (`PositionsPage.tsx:190`)
The conditional `pos.exitMode === 'model' || pos.exitMode === 'shadow'` reads the position's DB field (stale per RC-1). Even when `lastEvalCriteria` is populated and `closestCriterion` is computed, the model branch never activates because the position's `exitMode` is `'fixed'`.

**RC-4: Backend enrichment unconditionally computes fixed-mode data** (`position-enrichment.service.ts:291-311`)
The enrichment service always computes `exitProximity` (SL/TP proximity), `projectedSlPnl`, and `projectedTpPnl` from fixed-mode formulas — regardless of exit mode. Model criteria are appended from `lastEvalCriteria` but the fixed data is always the primary return.

### Data Flow Showing the Disconnect

```
Engine config: EXIT_MODE=model
         │
Exit Monitor ── this.exitMode='model' ── evaluates 6 criteria ✓
         │
         ├── persists lastEvalCriteria ✓
         ├── persists recalculatedEdge ✓
         └── does NOT persist exitMode ✗ ← RC-1
         │
Position DB ── exitMode='fixed' (stale)
         │
Enrichment ── reads position.exitMode='fixed'
         │
         ├── computes fixed SL/TP proximity (always) ← RC-4
         ├── reads lastEvalCriteria → closestCriterion ✓
         └── returns exitMode='fixed' to frontend
         │
Frontend ── pos.exitMode === 'model' → FALSE ← RC-3
         │
         ├── Risk/Reward: fixed SL/TP (always) ← RC-2
         └── Exit Proximity: SL/TP bars (fixed fallthrough)
```

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| **10.96** (in-progress) | **Add 1 story** | Bug-fix story for dashboard mode-adaptive columns. Fits the epic's "live engine alignment" scope. |
| 11+ (backlog) | None | No downstream impact. |

No epics invalidated, no resequencing needed.

### Story Impact

| Story | Relationship | Details |
|-------|-------------|---------|
| **10-2** (done) | **Original AC partially unmet** | AC: "each position shows: which criterion is closest to triggering, proximity percentage per criterion, and exit mode indicator" — this works ONLY if exitMode was 'model' at creation time. The fix completes the AC intent. |
| **10-96-1** (done) | **Percentage SL context** | Percentage SL is only in `evaluateFixed()`. In model mode, the 6 criteria handle risk. Risk/Reward column should reflect this. |
| **New: 10-96-5** | **Proposed** | Dashboard model-mode column fix (this proposal). |

### Artifact Conflicts

| Artifact | Conflict | Action |
|----------|----------|--------|
| PRD | None | FR-EM-03 requires model-driven dashboard display. Fix aligns with PRD. |
| Architecture | None | Fix is within existing module boundaries. No new imports or patterns. |
| UX Spec | None | Columns already exist. Fix makes them mode-adaptive. |
| Epics | None | Story 10.2 ACs already require this behavior. |

### Technical Impact

**Backend (pm-arbitrage-engine):** 2 files modified
- `exit-monitor.service.ts` — Add `exitMode` to `updateData` in `recalculateAndPersistEdge()`
- `position-enrichment.service.ts` — Mode-conditional data computation

**Frontend (pm-arbitrage-dashboard):** 2-3 files modified
- `PositionsPage.tsx` — Risk/Reward column mode branching
- `RiskRewardCell.tsx` — Model-mode variant (or new component)
- `ExitProximityIndicator.tsx` — No changes needed (already correct for fixed mode)

**No DB migrations.** The `exitMode` column already exists on `OpenPosition`.
**No new dependencies.** All data is already computed and available.

---

## Section 3: Recommended Approach

**Selected: Option 1 — Direct Adjustment**

Add one story (10-96-5) to the current Epic 10.96. This is a focused bug-fix touching 4-5 files across engine and dashboard.

**Rationale:**
- The bug is entirely within existing module boundaries
- All required data (`lastEvalCriteria`, `closestCriterion`, `closestProximity`) is already computed and persisted — it just never reaches the display
- The fix is a single root-cause correction (RC-1: persist `exitMode`) plus frontend adaptation (RC-2, RC-3)
- Epic 10.96 is the correct home — it's literally about aligning live engine behavior with correct display
- Effort: Low (1 story, ~4-5 files, ~50-80 lines changed)
- Risk: Low (display-only changes + one additional DB field write per evaluation cycle)

**Alternatives considered:**
- Rollback: Nothing to roll back — the feature works, it's the display that's broken
- PRD Review: Not needed — PRD already requires this behavior (FR-EM-03)

---

## Section 4: Detailed Change Proposals

### Change 1: Exit Monitor — Persist `exitMode` to Position

**File:** `pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts`
**Method:** `recalculateAndPersistEdge()` (line ~823)

```
OLD:
    const updateData: Record<string, unknown> = {
      recalculatedEdge: recalculatedEdge.toFixed(8),
      lastRecalculatedAt: now,
      recalculationDataSource: dataSource,
    };

NEW:
    const updateData: Record<string, unknown> = {
      recalculatedEdge: recalculatedEdge.toFixed(8),
      lastRecalculatedAt: now,
      recalculationDataSource: dataSource,
      exitMode,
    };
```

**Rationale:** The exit monitor already receives `exitMode` as a parameter. Writing it to the position on every evaluation cycle ensures the position always reflects the mode actively used for evaluation — not just the mode at creation time. This is the single root-cause fix that unblocks RC-3 (frontend gate).

### Change 2: Position Enrichment — Mode-Conditional Data

**File:** `pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts`

**Approach:** When `exitMode` is `'model'` or `'shadow'`, the enrichment should still compute fixed-mode `exitProximity` and `projectedSlPnl`/`projectedTpPnl` (they serve as fallback and shadow comparison baseline), but the response should clearly signal which data the frontend should prioritize via `exitMode`.

No structural change needed here after Change 1 — the enrichment already reads `position.exitMode` and already computes `closestCriterion`/`closestProximity` from `lastEvalCriteria`. With Change 1, the `exitMode` will now be current, and the existing enrichment logic becomes correct.

### Change 3: Risk/Reward Column — Model-Mode Branching

**File:** `pm-arbitrage-dashboard/src/pages/PositionsPage.tsx` (lines 164-173)

```
OLD:
    columnHelper.display({
      id: 'riskReward',
      header: 'Risk/Reward',
      enableSorting: false,
      cell: ({ row }) => {
        const pos = row.original;
        if (pos.status === 'CLOSED') return <span className="text-muted-foreground">—</span>;
        return <RiskRewardCell sl={pos.projectedSlPnl} tp={pos.projectedTpPnl} />;
      },
    }),

NEW:
    columnHelper.display({
      id: 'riskReward',
      header: 'Risk/Reward',
      enableSorting: false,
      cell: ({ row }) => {
        const pos = row.original;
        if (pos.status === 'CLOSED') return <span className="text-muted-foreground">—</span>;
        // Model/shadow mode: show criteria-based risk/reward
        if ((pos.exitMode === 'model' || pos.exitMode === 'shadow') && pos.exitCriteria?.length) {
          return <ModelRiskRewardCell criteria={pos.exitCriteria} />;
        }
        return <RiskRewardCell sl={pos.projectedSlPnl} tp={pos.projectedTpPnl} />;
      },
    }),
```

**Rationale:** In model mode, the 6 criteria determine exits, not SL/TP thresholds. The new `ModelRiskRewardCell` should display the highest-proximity loss criterion (edge_evaporation, risk_budget, liquidity_deterioration, model_confidence, time_decay) as "Risk" and the profit_capture criterion proximity as "Reward". This maps directly to what the operator needs: "what's most likely to stop me out, and how close am I to taking profit?"

### Change 4: Exit Proximity Column — Already Correct After Change 1

**File:** `pm-arbitrage-dashboard/src/pages/PositionsPage.tsx` (line 190)

No code change needed. The existing conditional:
```typescript
if ((pos.exitMode === 'model' || pos.exitMode === 'shadow') && pos.closestCriterion) {
```
...will start working correctly once Change 1 ensures `pos.exitMode` reflects the current engine mode.

### Change 5: New Component — ModelRiskRewardCell

**File:** `pm-arbitrage-dashboard/src/components/cells/ModelRiskRewardCell.tsx` (NEW)

A new cell component that:
- Accepts the `exitCriteria` array
- Categorizes criteria into risk (edge_evaporation, risk_budget, liquidity_deterioration, model_confidence, time_decay) and reward (profit_capture)
- Shows the highest-proximity risk criterion and profit_capture proximity
- Color-coded: red for risk, green for reward (matching existing SL/TP color convention)
- Tooltip with all criteria proximities on hover

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

Direct implementation by development team. No backlog reorganization or strategic replanning needed.

### Story Definition

**Story 10-96-5: Dashboard Model-Mode Risk/Reward & Exit Proximity Fix**

As an operator, I want the Risk/Reward and Exit Proximity columns to dynamically adapt their display based on the active exit mode, so that I see relevant criteria data when running in model or shadow mode instead of misleading fixed-mode SL/TP thresholds.

**Context:** Story 10-2 implemented six-criteria model-driven exits with dashboard display, but the `exitMode` field on positions is frozen at creation time (never updated by the exit monitor). When the engine mode changes post-creation, the dashboard shows fixed-mode data even though model-mode evaluation is active.

**Acceptance Criteria:**

1. **Given** the exit monitor evaluates a position, **When** `recalculateAndPersistEdge()` runs, **Then** the position's `exitMode` field is updated to the current engine exit mode on every evaluation cycle.

2. **Given** the engine is running in model mode, **When** the Positions page displays open positions, **Then** the Exit Proximity column shows the closest criterion name and proximity percentage (not SL/TP bars).

3. **Given** the engine is running in model mode, **When** the Positions page displays open positions, **Then** the Risk/Reward column shows criteria-based risk/reward: highest-proximity loss criterion as risk, profit_capture proximity as reward (not fixed SL/TP projected P&L).

4. **Given** the engine is running in fixed mode, **When** the Positions page displays open positions, **Then** both columns display the existing SL/TP data (zero regression).

5. **Given** the engine is running in shadow mode, **When** the Positions page displays open positions, **Then** both columns display model-mode data (shadow uses model for display, fixed for decisions).

6. **Given** a position was created in fixed mode but the engine has since switched to model mode, **When** the exit monitor runs its next evaluation cycle, **Then** the position's `exitMode` is updated to 'model' and the dashboard reflects the new mode on next refresh.

7. **Given** a ModelRiskRewardCell is rendered, **When** the operator hovers over it, **Then** a tooltip shows all six criteria with their proximity percentages.

**Tasks:**
1. Backend: Add `exitMode` to `updateData` in `recalculateAndPersistEdge()` (RC-1 fix)
2. Frontend: Create `ModelRiskRewardCell` component with criteria categorization
3. Frontend: Add model-mode branching to Risk/Reward column in `PositionsPage.tsx`
4. Tests: Exit monitor spec — verify `exitMode` persisted on evaluation
5. Tests: Paper/live boundary — verify mode update works for both paper and live positions
6. Tests: Frontend component test for `ModelRiskRewardCell`
7. Dashboard API client regeneration (if DTO changes)
8. Lint + full test suite green

**Files Modified:**
- `pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts`
- `pm-arbitrage-dashboard/src/pages/PositionsPage.tsx`
- `pm-arbitrage-dashboard/src/components/cells/ModelRiskRewardCell.tsx` (NEW)
- `pm-arbitrage-dashboard/src/components/cells/index.ts`

**Dependencies:** None — all required data already computed and persisted.
**Estimated Effort:** Small (4-5 files, ~80-100 lines)
**Risk:** Low (display fix + one additional field write per eval cycle)

### Handoff

| Role | Responsibility |
|------|---------------|
| Dev Agent | Implement story 10-96-5 following TDD |
| Arbi (operator) | Verify model-mode display after deployment |

### Success Criteria

- With `EXIT_MODE=model`: Risk/Reward shows criteria-based risk/reward, Exit Proximity shows closest criterion
- With `EXIT_MODE=fixed`: Both columns display SL/TP data (zero regression)
- With `EXIT_MODE=shadow`: Both columns display model-mode data
- Switching modes mid-session updates positions on next exit monitor cycle (30s)
- All existing tests pass, new tests cover the fix

---

## Checklist Completion Summary

| Section | Status |
|---------|--------|
| 1. Trigger & Context | [x] Done — 4 root causes identified with code-level evidence |
| 2. Epic Impact | [x] Done — 1 story added to Epic 10.96, no other epics affected |
| 3. Artifact Conflicts | [x] Done — No PRD/Architecture/UX conflicts |
| 4. Path Forward | [x] Done — Direct Adjustment selected |
| 5. Proposal Components | [x] Done — Story defined with ACs and tasks |
| 6. Final Review | [ ] Pending user approval |
