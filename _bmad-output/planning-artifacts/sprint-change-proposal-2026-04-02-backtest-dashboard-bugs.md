# Sprint Change Proposal — Backtest Dashboard Display Bugs

**Date:** 2026-04-02
**Triggered by:** QA verification of backtest run `0b11283d-9df0-49fc-97fa-0f6ce75c781f`
**Epic:** 10.9 (Backtesting & System Calibration)
**Scope Classification:** Minor — Direct implementation by dev team

---

## 1. Issue Summary

During QA verification of a completed backtesting run (2,049 positions, date range 01/03/2026–04/03/2026), two display bugs were discovered in the dashboard frontend:

1. **Summary Tab — P&L shows $0.00:** The database correctly stores `total_pnl = -7950` and the report JSON correctly contains `summaryMetrics.netPnl = "-7950.0000000000"`. However, the frontend component `SummaryMetricsPanel.tsx` reads `metrics.totalPnl` (wrong field name) instead of `metrics.netPnl`, resulting in `undefined → 0 → $0.00`.

2. **Positions Tab — Empty trade list:** The Positions tab in `BacktestDetailPage.tsx` only renders a static count string (`"2049 positions in this run."`). No DataTable, no individual position records, no pagination — despite the API already returning paginated position data.

**Evidence:**
- Database query: `SELECT total_pnl FROM backtest_runs WHERE id = '0b11283d...'` → `-7950.0000000000`
- Report JSON: `jsonb_path_query(report, '$.summaryMetrics')` → `{"netPnl": "-7950.0000000000", ...}`
- Frontend code: `metrics.totalPnl` (line 25, 47, 64 of SummaryMetricsPanel.tsx) — field does not exist in report

---

## 2. Impact Analysis

### Epic Impact
- **Epic 10.9** is unaffected structurally. These are rendering bugs in existing dashboard components, not missing features or architectural issues.
- **No other epics** are impacted.

### Story Impact
- No existing stories need modification. A single new hotfix story covers both bugs.

### Artifact Conflicts
- **PRD:** No conflict. Dashboard and backtesting requirements remain valid.
- **Architecture:** No conflict. Backend API, data model, and report generation are all correct.
- **UX Spec:** Minor — Positions tab was intended to show position details; fix implements original intent.

### Technical Impact
- **Frontend only** (`pm-arbitrage-dashboard/`). Two files affected:
  - `src/components/backtest/SummaryMetricsPanel.tsx` — field name fix
  - `src/pages/BacktestDetailPage.tsx` — replace placeholder with DataTable
- **Zero backend changes.** API already returns all required data.

---

## 3. Recommended Approach

**Direct Adjustment** — Two targeted frontend fixes within the existing dashboard codebase.

**Rationale:**
- Root causes are definitively identified (field name mismatch + placeholder code)
- Backend data pipeline is fully correct — no API or schema changes needed
- Both fixes are low-risk, low-effort, contained to 2 frontend files
- Existing `DataTable` component and `PositionsPage.tsx` provide reference implementation for the positions table

**Effort:** Low (< 1 story point)
**Risk:** Low — no backend changes, no data model changes, no new dependencies
**Timeline impact:** None — this is a minor hotfix within the current sprint

---

## 4. Detailed Change Proposals

### Change 1: Fix P&L field name mismatch

**File:** `pm-arbitrage-dashboard/src/components/backtest/SummaryMetricsPanel.tsx`

**OLD (line 25):**
```typescript
totalPnl?: string;
```

**NEW:**
```typescript
netPnl?: string;
```

**OLD (line 47):**
```typescript
const pnlNum = metrics.totalPnl ? parseFloat(metrics.totalPnl) : 0;
```

**NEW:**
```typescript
const pnlNum = metrics.netPnl ? parseFloat(metrics.netPnl) : 0;
```

**OLD (line 64):**
```typescript
<MetricCard label="Net P&L" value={formatUsd(metrics.totalPnl)} className={pnlColor} />
```

**NEW:**
```typescript
<MetricCard label="Net P&L" value={formatUsd(metrics.netPnl)} className={pnlColor} />
```

**Rationale:** Backend `CalibrationReport.SummaryMetrics` uses `netPnl`, not `totalPnl`. The frontend type assertion assumed the wrong field name.

---

### Change 2: Implement Positions tab with DataTable

**File:** `pm-arbitrage-dashboard/src/pages/BacktestDetailPage.tsx`

**OLD (lines 138-144):**
```tsx
<TabsContent value="positions">
  <DashboardPanel title="Positions">
    <p className="text-muted-foreground">
      {(run.positionCount as number) ?? 0} positions in this run.
    </p>
  </DashboardPanel>
</TabsContent>
```

**NEW:**
Replace with a `DataTable` component rendering position records from `run.positions` with columns:
- Pair ID
- Kalshi/Polymarket sides
- Entry/exit timestamps
- Entry/exit prices (both platforms)
- Position size (USD)
- Entry/exit edge
- Realized P&L (color-coded)
- Fees
- Exit reason
- Holding hours

Include pagination support (the API already accepts `positionLimit` and `positionOffset`).

**Rationale:** The API hook already fetches position records (`positionLimit: 100`), and the `DataTable` component used on `PositionsPage.tsx` provides a ready reference pattern. The placeholder was likely left during initial backtesting UI scaffolding and never completed.

---

## 5. Implementation Handoff

**Scope:** Minor — Direct implementation by dev team.

**Handoff to:** Development team (dev agent)

**Responsibilities:**
1. Fix field name mismatch in `SummaryMetricsPanel.tsx` (3 line changes)
2. Implement positions DataTable in `BacktestDetailPage.tsx` (new component or inline)
3. Update/add frontend tests for both components
4. Verify fix against backtest run `0b11283d` on localhost

**Success criteria:**
- Summary tab displays correct P&L (`-$7,950.00` for the test run)
- Positions tab renders individual position records in a sortable, paginated table
- All existing dashboard tests pass
- Visual verification against the same backtest run
