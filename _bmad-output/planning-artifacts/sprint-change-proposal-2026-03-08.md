# Sprint Change Proposal — Position Lifecycle Improvements & Dashboard Enrichment

**Date:** 2026-03-08
**Triggered by:** Story 6.5.5 — Paper Execution Validation (5-day live paper run)
**Scope:** Minor — Direct implementation by dev agent
**Proposed Epic:** 7.5 (3 stories)

---

## Section 1: Issue Summary

During the 5-day paper trading validation (Story 6.5.5), production database analysis revealed that the position lifecycle has critical operational gaps:

1. **EXIT_PARTIAL positions are permanently stalled.** The exit monitor only queries positions with status `OPEN` (`exit-monitor.service.ts:72-73`). Once a position enters `EXIT_PARTIAL` after a partial fill, it is never re-evaluated — the remaining contracts are orphaned indefinitely. Confirmed in production: the KXNYCMINWAGE position has been stuck in EXIT_PARTIAL since Mar 7 04:10 UTC with 12 of 23 contracts unexited.

2. **Manual close does not work for OPEN positions.** The dashboard's "Close" button calls `POST /api/positions/:id/close-leg`, which is the single-leg resolution endpoint designed for `SINGLE_LEG_EXPOSED` positions. When called on an OPEN position, it returns: _"Position is not in a closeable state (status: OPEN)"_. There is no endpoint for closing an OPEN position across both platforms simultaneously.

3. **Dashboard lacks operational depth.** After several days of live operation, the following gaps became apparent:
   - No position history — only active positions are visible; closed positions disappear
   - No position detail view — no breakdown of contracts, capital invested, order history, or reasoning
   - No balance overview — operator cannot see blocked vs. available capital at a glance
   - No SL/TP projected P&L — operator cannot assess risk/reward of open positions
   - No bulk close capability — no way to exit all positions in an emergency

**Discovery context:** These were found during the paper validation gate by exporting the production database (133K audit logs, 83K order book snapshots, 14 orders, 5 positions) and analyzing execution history. The KXBTCVSGOLD position was closed via stop-loss at -$1.81 realized P&L — the operator had no way to see the projected loss before it triggered.

**Evidence:**
- DB export analysis: KXNYCMINWAGE stuck in EXIT_PARTIAL since Mar 7 04:10, 12 contracts orphaned
- Screenshot: "Position is not in a closeable state (status: OPEN)" error toast on close attempt
- Code confirmation: `exit-monitor.service.ts:72-73` — `findByStatusWithOrders('OPEN', isPaper)` excludes EXIT_PARTIAL
- Story 6.5.5k design decision: _"No auto-retry of unfilled remainder — operator decides via existing retry-leg/close-leg endpoints"_ — intentional but proved impractical during live operation

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Status | Impact |
|------|--------|--------|
| Epic 6.5 (Paper Trading Validation) | in-progress | **Unaffected.** These are findings from the validation, not blockers to it. Stories 6.5.5 and 6.5.6 can complete as planned. |
| Epic 7 (Operator Dashboard) | done | **Not reopened.** New Epic 7.5 created to keep audit trail clean. |
| Epic 10 (Story 10.3: Automatic Single-Leg Management) | backlog | **Compatible.** Our EXIT_PARTIAL fix is minimal (re-evaluate with residual sizes). Epic 10.3's full auto-close/hedge will supersede this approach. The two are additive, not conflicting. |
| Epics 8, 9, 11, 12 | backlog | **No impact.** |

### Artifact Impact

| Artifact | Change Required |
|----------|----------------|
| `epics.md` | New Epic 7.5 section with 3 stories — written upon proposal approval |
| `sprint-status.yaml` | New Epic 7.5 entries, updated summary stats and NEXT pointer — written upon proposal approval |
| Architecture | New `IPositionCloseService` interface in `common/interfaces/`, new `PositionManagementController` in `src/dashboard/`, new `batch.complete` WebSocket event type |
| UX Specification | Position history view, detail page, balance card, updated close dialog, Close All button, SL/TP projected P&L columns |
| Prisma Schema | New btree index on `audit_logs` for `(details->>'pairId')` — performance requirement for position detail page audit trail query |
| Swagger/OpenAPI | New endpoints documented, API client regenerated |

### No Impact On

- PRD scope or core goals
- Module dependency rules
- Error hierarchy (SystemError tree)
- Event naming conventions (dot-notation)
- Hot path architecture (detection → risk → execution)
- CI/CD, deployment, or infrastructure

---

## Section 3: Recommended Approach

**Selected: Direct Adjustment** — new Epic 7.5 with 3 stories added to the existing plan.

**Rationale:**
- All changes are **additive** — no existing behavior is modified except EXIT_PARTIAL positions now being re-evaluated by the exit monitor
- Every change follows **established patterns**: `IPositionCloseService` mirrors `IPriceFeedService` (Story 7.2), residual-size math extends 6.5.5k, enrichment service extensions follow 7.2's pattern, WebSocket event wiring follows 7.3
- **No rollbacks needed** — these are gaps discovered during validation, not regressions
- **No MVP scope change** — MVP was delivered in Epic 7. These are post-MVP operational improvements
- **Low-Medium risk** — Story 7.5.1 carries Medium risk (exit monitor is the trading pipeline's heartbeat; changing its query scope and adding residual-size branching could cause positions to be skipped or double-exited if subtly wrong). Stories 7.5.2 and 7.5.3 are Low risk (additive dashboard work). Test coverage requirements in 7.5.1's DoD gates mitigate the hot-path risk
- **Compatible with future work** — Epic 10.3 will eventually replace the EXIT_PARTIAL re-evaluation with a more sophisticated auto-close/hedge system

**Effort:** Medium (~1 sprint, 3 stories)
**Risk:** Low-Medium (driven by 7.5.1's exit monitor changes)
**Timeline impact:** None on existing plan — Epic 7.5 slots before Epic 8

**Alternatives considered:**
- **Rollback:** Not viable — nothing to roll back, these are gaps not regressions
- **MVP Review:** Not applicable — MVP is already delivered

---

## Section 4: Detailed Change Proposals

### Epic 7.5: Position Lifecycle Improvements & Dashboard Enrichment

Operator can manage the full position lifecycle — including partially exited positions — with comprehensive visibility into history, details, balance, and risk/reward projections.

#### Story 7.5.1: EXIT_PARTIAL Re-evaluation & Dual-Platform Close Endpoint

**Type:** Backend-heavy (trading pipeline + new endpoint)

**Changes:**
1. Exit monitor query broadened to include EXIT_PARTIAL positions alongside OPEN
2. New `getResidualSize(position)` utility — computes `entryFillSize - sum(exitOrderFilledQuantity)` per leg, aggregating across all exit orders (consistent with 6.5.5k P&L source-of-truth)
3. All exit monitor downstream logic (threshold evaluation, depth checks, VWAP, cross-leg equalization) operates on residual sizes for EXIT_PARTIAL positions
4. New `POST /api/positions/:id/close` endpoint — dual-platform close for OPEN and EXIT_PARTIAL positions
5. New `IPositionCloseService` interface in `common/interfaces/`, implementation in `src/modules/execution/`
6. New `PositionManagementController` in `src/dashboard/`
7. Single-leg failure during manual close → `SINGLE_LEG_EXPOSED` with `origin: 'manual_close'` context

**Dependencies:** None
**Risk:** Medium — touches exit monitor hot path, requires thorough test coverage

#### Story 7.5.2: Position History, Details Page & Balance Overview

**Type:** Dashboard-heavy (new views + backend DTOs + enrichment)

**Changes:**
1. `GET /api/positions` extended with status filter, pagination, isPaper filter
2. New "All Positions" tab showing full history (CLOSED, EXIT_PARTIAL, etc.)
3. New `GET /api/positions/:id/details` endpoint with orders, audit trail, capital breakdown
4. Prisma migration: `CREATE INDEX idx_audit_logs_pair_id ON audit_logs USING btree ((details->>'pairId'))` (mandatory — 133K+ rows)
5. `GET /api/risk/state` extended with `totalBankroll` (from engine config) and `availableCapital` (computed)
6. Balance card on dashboard home: bankroll, deployed, available, reserved, position count
7. New position detail page at `/positions/:id`
8. SL/TP projected P&L in enrichment service — `projectedSlPnl` and `projectedTpPnl` on position DTOs

**Dependencies:** Partial on 7.5.1 — only SL/TP projections for EXIT_PARTIAL need `getResidualSize()`. Bulk of work can start in parallel.
**Risk:** Low — all additive, no hot path changes

#### Story 7.5.3: Close All Positions & Updated Close UX

**Type:** Full-stack (new endpoint + async processing + frontend UX)

**Changes:**
1. Per-position close button updated to call `POST /api/positions/:id/close` (from 7.5.1) instead of `close-leg`
2. Close dialog updated with projected close P&L from enrichment
3. New `POST /api/positions/close-all` — returns `202 Accepted` with `batchId`, processes sequentially in background
4. Per-position execution lock during batch (no deadlock with exit monitor)
5. Rate limit pre-check per position — skip and report `rate_limited` if insufficient budget (close as many as possible)
6. WebSocket progress: `position.update` events per close, `batch.complete` event on finish
7. New `batch.complete` event type wired into `DashboardEventMapperService`, `DASHBOARD_EVENTS`, `WsEventEnvelope`
8. "Close All" button with "CLOSE ALL" typed confirmation phrase (same safety pattern as Story 4.3 risk override)
9. Frontend progress indicator driven by existing WebSocket subscription

**Dependencies:** 7.5.1 (close endpoint) + 7.5.2 (enrichment for projected close P&L)
**Risk:** Low — extends existing patterns, no hot path changes

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

All changes follow established patterns and can be implemented directly by the dev agent without architectural review.

### Responsibilities

| Role | Action |
|------|--------|
| **SM (Bob)** | Epic 7.5 written to `epics.md`, `sprint-status.yaml` updated, sprint change proposal generated (this document) |
| **Dev agent** | Implement stories sequentially: 7.5.1 → 7.5.2 → 7.5.3. Follow post-edit workflow (lint → test → commit per story). Use [CS] Create Story to generate implementation-ready story files before starting each story. |
| **Arbi (operator)** | Validate each completed story against the live paper trading environment on VPS. Confirm EXIT_PARTIAL re-evaluation works, manual close works, dashboard views are useful. |

### Implementation Sequence

```
7.5.1 (EXIT_PARTIAL + close endpoint)
  │
  ├── 7.5.2 backend can start in parallel (no dependency except SL/TP for EXIT_PARTIAL)
  │
  ▼
7.5.2 (history, details, balance, SL/TP P&L)
  │
  ▼
7.5.3 (close-all, updated close UX) — depends on both 7.5.1 and 7.5.2
```

### Success Criteria

1. EXIT_PARTIAL positions are automatically re-evaluated and can be fully closed by the exit monitor
2. `POST /api/positions/:id/close` successfully closes OPEN positions across both platforms
3. Position history shows all historical positions with realized P&L
4. Position detail page provides complete breakdown (orders, capital, audit trail)
5. Balance overview shows accurate blocked vs. available capital
6. SL/TP projected P&L is visible on all open positions
7. "Close All" bulk action closes positions sequentially with real-time feedback
8. All existing tests pass, new test coverage matches DoD gates in each story

### Next Steps

1. Run `[CS] Create Story` for Story 7.5.1 to generate the implementation-ready story file
2. Dev agent begins implementation
3. After 7.5.1 is validated on VPS, proceed to 7.5.2, then 7.5.3
