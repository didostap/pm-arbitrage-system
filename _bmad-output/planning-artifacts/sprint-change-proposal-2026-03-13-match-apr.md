# Sprint Change Proposal: Match APR Visibility

**Date:** 2026-03-13
**Trigger:** Story 9-5 (Capital Efficiency Gating) — APR computed but never surfaced
**Category:** Feature Gap — computed data not exposed to operator
**Mode:** Incremental Review
**Path Forward:** Direct Adjustment — new Story 9-9 in Epic 9

---

## 1. Issue Summary

Story 9-5 introduced capital efficiency gating in `EdgeCalculatorService.checkCapitalEfficiency()`, computing `annualizedReturn = netEdge × (365 / daysToResolution)` to filter opportunities below the `MIN_ANNUALIZED_RETURN` threshold (default 15%).

**Problem:** This critical financial metric exists only in-memory during the detection cycle:

| Layer | APR Present? |
|-------|-------------|
| `EdgeCalculatorService` (detection) | Yes — computed, used for pass/fail gate |
| `EnrichedOpportunity` type | Yes — carried as `annualizedReturn: Decimal \| null` |
| `OpportunityIdentifiedEvent` payload | Yes — emitted with APR as number |
| `ContractMatch` DB model | **No** — no APR columns |
| `MatchSummaryDto` API response | **No** — no APR fields |
| Matches page (dashboard) | **No** — no APR column |

The operator approves contract matches without visibility into expected capital efficiency. This undermines informed match approval decisions — the operator cannot assess which pairs justify capital lockup.

---

## 2. Impact Analysis

### Epic Scope

| Epic | Impact |
|------|--------|
| **Epic 9** (in-progress) | **Direct** — add Story 9-9. No dependency on other in-progress stories. |
| All other epics | **Unaffected** |

### Artifact Conflicts

| Artifact | Conflict? | Notes |
|----------|-----------|-------|
| PRD (Section 5.3) | None | Already requires "Annualized return calculation" |
| UX Design | None | No prescribed Matches page columns; follows existing DataTable patterns |
| Architecture | **Yes** | Dashboard module cannot import from detection — requires event-driven persistence |
| Prisma Schema | **Yes** | `ContractMatch` model missing 3 columns |
| DTOs | **Yes** | `MatchSummaryDto` missing 3 fields |
| Frontend | **Yes** | Matches table missing sortable APR column |

### Risk Assessment

- **Hot-path impact:** Zero — persistence happens in async event fan-out only
- **Breaking changes:** None — new DB columns are nullable, new DTO fields are optional
- **Staleness:** ~30s lag (one detection polling cycle) acceptable for display metric; `lastComputedAt` provides transparency
- **Timeline:** Minimal — self-contained, no cross-story dependencies

---

## 3. Recommended Approach: Event-Driven Persistence (Option A)

Two options were evaluated:

| Criterion | Option A: Persist via Events | Option B: Compute at API Time |
|-----------|------------------------------|-------------------------------|
| Architecture compliance | Follows existing fan-out pattern | **Violates boundary** — dashboard needs detection logic |
| Hot-path impact | Zero | Zero, but adds API-time computation |
| Sortability | Native DB sort (indexable) | Requires in-memory sort |
| Data availability | Always in DB, fast queries | Requires live orderbook + fee schedules |
| Staleness | ~30s with timestamp | Always fresh but expensive |
| Complexity | Low — established pattern | High — reimplements calculation |

**Decision: Option A.** The ~30s staleness is acceptable. Architectural boundary preservation and native DB sortability are decisive advantages. This follows the same monitoring → persistence pattern used by audit logging, Telegram alerts, and dashboard WebSocket updates.

### Mechanism

Subscribe to existing `OpportunityIdentifiedEvent` and `OpportunityFilteredEvent` in the monitoring module's async event fan-out path. On each event, update the corresponding `ContractMatch` record with:

- `last_annualized_return` — computed APR (Decimal, nullable)
- `last_net_edge` — net edge used in calculation (Decimal, nullable)
- `last_computed_at` — timestamp of computation (DateTime, nullable)

---

## 4. Detailed Change Proposals

### 4.1 Database Migration

**File:** `pm-arbitrage-engine/prisma/schema.prisma` — `ContractMatch` model

```prisma
last_annualized_return Decimal?  @map("last_annualized_return")
last_net_edge          Decimal?  @map("last_net_edge")
last_computed_at       DateTime? @map("last_computed_at")
```

**Migration name:** `add-match-apr-fields`

### 4.2 Event Subscriber

**Location:** `pm-arbitrage-engine/src/modules/monitoring/`

Subscribe to:
- `detection.opportunity.identified` → update match with APR, net edge, timestamp
- `detection.opportunity.filtered` → update match with last known values (if capital-efficiency filtered)

Maps `pairId` from event payload → `ContractMatch` record → upsert APR fields.

### 4.3 API DTO Update

**File:** `pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts` — `MatchSummaryDto`

```typescript
lastAnnualizedReturn: number | null;  // e.g., 0.42 = 42% annualized
lastNetEdge: number | null;           // e.g., 0.008 = 0.8%
lastComputedAt: string | null;        // ISO 8601 timestamp
```

### 4.4 Service Mapping

**File:** `pm-arbitrage-engine/src/dashboard/match-approval.service.ts` — `toSummaryDto()`

Map new Prisma `Decimal?` columns → `number | null` via `.toNumber()`.

### 4.5 Controller Sort Support

**File:** `pm-arbitrage-engine/src/dashboard/match-approval.controller.ts` — `listMatches()`

Extend sort/order query parameters to accept `lastAnnualizedReturn` as a valid sort field. Add Prisma `orderBy` mapping.

### 4.6 Frontend — Matches Page Table Column

**File:** `pm-arbitrage-dashboard/src/pages/MatchesPage.tsx`

- **Column:** "Est. APR" — sortable
- **Format:** percentage (e.g., "42.1%") or "—" when null
- **Color coding:** green ≥ 30%, yellow 15-30%, gray when null
- **Sort:** clicking column header triggers API sort by `lastAnnualizedReturn` (asc/desc)
- **Tooltip on null:** "Awaiting next detection cycle"

### 4.7 Frontend — Match Detail Page

**File:** `pm-arbitrage-dashboard/src/pages/MatchDetailPage.tsx`

Add "Capital Efficiency" card section:
- Est. APR (formatted percentage)
- Net Edge (formatted percentage)
- Last Updated (relative time, absolute in tooltip)
- Staleness indicator (amber if > 5 minutes old)

---

## 5. Implementation Handoff

### Story Definition

**ID:** `9-9-match-apr-visibility`
**Title:** Match APR Visibility — Persist & Display Estimated Annualized Return
**Epic:** 9 (Advanced Risk & Portfolio Management)
**Effort:** Medium (3-5 hours)

### Acceptance Criteria

1. `ContractMatch` table has `last_annualized_return`, `last_net_edge`, `last_computed_at` columns (nullable)
2. APR values persisted via event subscriber on each detection cycle
3. `GET /api/contract-matches` returns `lastAnnualizedReturn`, `lastNetEdge`, `lastComputedAt`
4. `GET /api/contract-matches` supports `sortBy=lastAnnualizedReturn` with `order=asc|desc`
5. Matches page table shows sortable "Est. APR" column with percentage formatting and color coding
6. Match detail page shows "Capital Efficiency" section with APR, net edge, staleness indicator
7. Null handling: "—" displayed when no APR data available
8. All existing tests pass; new tests cover event subscriber, DTO mapping, sort behavior

### Implementation Order

1. Prisma migration + generate
2. Event subscriber (monitoring module)
3. DTO + service mapping + controller sort
4. Frontend table column (sortable)
5. Frontend detail section
6. Tests throughout (TDD)

### Sprint Status Update

Add to `sprint-status.yaml` under Epic 9:
```yaml
9-9-match-apr-visibility: ready-for-dev
```

### Handoff Roles

| Role | Responsibility | Status |
|------|---------------|--------|
| SM (Bob) | Draft Sprint Change Proposal | ✅ Complete |
| SM (Bob) | Update sprint-status.yaml | Pending approval |
| SM (create-story) | Create Story 9-9 implementation file | After approval |
| PO/Arbi | Approve proposal | **Pending** |
| Dev agent | Implement Story 9-9 via TDD | After story creation |

---

**Prepared by:** Bob (Scrum Master Agent)
**Workflow:** Course Correction — Direct Adjustment
**Awaiting:** Operator approval to proceed
