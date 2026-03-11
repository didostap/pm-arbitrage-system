# Sprint Change Proposal: Matches Page Redesign & Data Alignment

**Date:** 2026-03-13
**Triggered by:** Accumulated implementation drift — Epic 8 (semantic matching) and Epic 9 (risk/portfolio management) added fields to `contract_matches` without corresponding UI updates
**Scope Classification:** Minor — direct implementation by dev team
**Proposed Story:** `9-7-matches-page-redesign`

---

## Section 1: Issue Summary

The dashboard matches page was built during Epic 7 (Story 7-3) as a card-based list with basic status filtering. Since then, Epic 8 added semantic matching fields (categories, confidence scoring) and Epic 9 added risk management fields (correlation clusters, resolution dates, trading activity). The result is that 8 of 22 `contract_matches` database fields are invisible to the operator.

Additionally, the page has structural shortcomings: no detail view for individual matches, no cluster-based filtering, a single consolidated view for all statuses, and dead code referencing Epic 8 as future work (Epic 8 is complete).

**Impact:** The operator cannot see cluster assignments, resolution dates, platform categories, primary leg designation, or trading activity from the dashboard — all operationally critical during active paper trading.

---

## Section 2: Impact Analysis

### Epic Impact

**Contained to Epic 9.** No other epics affected. New course-correction story `9-7-matches-page-redesign` follows the established pattern (9-1a, 9-1b, 9-5, 9-6).

### Story Impact

No existing stories require modification. This is a net-new story.

### Artifact Conflicts

| Artifact | Change Type | Details |
|---|---|---|
| Backend DTO (`match-approval.dto.ts`) | Additive | Add 8 missing fields to `MatchSummaryDto` |
| Backend Service (`match-approval.service.ts`) | Additive | Extend `toSummaryDto()`, add Prisma `include` for `CorrelationCluster` |
| Generated API Client (`Api.ts`) | Regenerate | Auto-generated from updated Swagger |
| `MatchesPage.tsx` | Rewrite | Card list → tabbed table views + cluster filter |
| `MatchCard.tsx` | Delete | Replaced by table rows |
| `MatchApprovalDialog.tsx` | Minor enhance | Show new fields in approval context |
| `App.tsx` routing | Additive | Add `/matches/:id` route |
| New `MatchDetailPage.tsx` | New file | Full record detail view |
| UX Design Spec | Minor update | Document table layout, cluster filter, status tabs |

### Technical Impact

- **Backend:** Non-breaking API change (additive fields in response). One additional Prisma `include` for the `CorrelationCluster` relation.
- **Frontend:** Component rewrite (MatchesPage), component deletion (MatchCard), new component (MatchDetailPage), new route.
- **No infrastructure, deployment, or CI/CD changes.**

---

## Section 3: Recommended Approach

**Selected: Direct Adjustment** — add a single new story within Epic 9.

### Rationale

- Lowest effort, lowest risk path
- Clean additive backend change, contained frontend rewrite
- Follows established Epic 9 course-correction pattern
- No dependencies on other teams or architectural decisions
- Immediate operational value for the operator during active paper trading

### Alternatives Considered

- **Rollback:** Not applicable — backend fields already exist and are in production use by the engine
- **MVP Review:** Not applicable — MVP is complete (Epic 7), this is Phase 1 enrichment
- **Separate epic:** Over-engineering for a single story; Epic 9 course-correction pattern is the right home

### Effort & Risk

- **Effort:** Medium (backend small, frontend moderate)
- **Risk:** Low (additive changes only, no breaking changes)
- **Timeline impact:** None — slots into Epic 9's active sprint

---

## Section 4: Detailed Change Proposals

### 4.1 Backend: Extend MatchSummaryDto

**File:** `pm-arbitrage-engine/src/dashboard/dto/match-approval.dto.ts`

**ADD these 8 fields to MatchSummaryDto class:**

```
polymarketRawCategory: string | null    // Platform category from Polymarket
kalshiRawCategory: string | null        // Platform category from Kalshi
firstTradedTimestamp: string | null      // ISO 8601, when pair first traded
totalCyclesTraded: number               // Detection cycles that led to trades
primaryLeg: string | null               // "kalshi" | "polymarket"
resolutionDate: string | null           // ISO 8601, when contracts resolve
resolutionCriteriaHash: string | null   // SHA hash for change detection
cluster: { id: string; name: string; slug: string } | null  // Resolved cluster object (not just foreign key)
```

**Rationale:** Expose all operationally relevant data. `cluster` is resolved as an object (not raw `clusterId`) so the frontend doesn't need a separate lookup. `resolutionCriteriaHash` is included for completeness — the detail page can show it.

### 4.2 Backend: Update Service Mapping

**File:** `pm-arbitrage-engine/src/dashboard/match-approval.service.ts`

- Add `include: { cluster: true }` to Prisma `findMany` and `findUnique` queries
- Extend `toSummaryDto()` to map the 8 new fields
- Map `cluster` relation to `{ id, name, slug } | null`

### 4.3 Backend: Add Cluster Filter Query Parameter

**File:** `pm-arbitrage-engine/src/dashboard/match-approval.controller.ts`

- Add optional `clusterId` query parameter to `listMatches` endpoint
- Add Prisma WHERE clause: `clusterId: clusterId ?? undefined`

### 4.4 Frontend: Redesign MatchesPage with Tabbed Status Views

**File:** `pm-arbitrage-dashboard/src/pages/MatchesPage.tsx`

**OLD:** Single view with toggle buttons (pending/approved/all), card-based list

**NEW:**
- Three distinct tabs: **Pending**, **Approved**, **All** — each renders its own table instance
- Cluster dropdown filter (populated from distinct clusters in the data, or a dedicated endpoint)
- Table columns: Status badge, Polymarket description, Kalshi description, Confidence %, Cluster, Resolution Date, Primary Leg, Created, Actions
- Clickable rows navigate to `/matches/:id` detail page
- Pagination retained

### 4.5 Frontend: New Match Detail Page

**New file:** `pm-arbitrage-dashboard/src/pages/MatchDetailPage.tsx`

Full record display for a single match. All 22+ fields organized in sections:
- **Header:** Status badge, match ID, confidence score, cluster badge
- **Contract Pair:** Side-by-side Polymarket/Kalshi descriptions, contract IDs, CLOB token ID, raw categories
- **Resolution:** Resolution date, resolution criteria hash, per-platform resolution outcomes, divergence status + notes, resolution timestamp
- **Trading Activity:** First traded timestamp, total cycles traded, primary leg
- **Operator Review:** Approval status, timestamp, rationale
- **Actions:** Approve/Reject buttons (if pending)

**Route:** Add `<Route path="/matches/:id" element={<MatchDetailPage />} />` to `App.tsx`

### 4.6 Frontend: Delete MatchCard Component

**File:** `pm-arbitrage-dashboard/src/components/MatchCard.tsx`

**Action:** Delete entirely. The card layout is replaced by table rows in the redesigned MatchesPage.

### 4.7 Frontend: Dead Code Cleanup

- Remove `"Knowledge Base: Coming in Epic 8"` text (Epic 8 is complete)
- Remove any other stale references discovered during implementation

### 4.8 Regenerate API Client

After backend DTO changes are deployed:
```bash
cd pm-arbitrage-dashboard && pnpm generate-api
```

---

## Section 5: Implementation Handoff

### Scope: Minor

Direct implementation by the dev agent. No PO/PM/Architect involvement needed.

### Handoff Recipients

| Role | Responsibility |
|---|---|
| SM (current session) | Create story file, update sprint-status.yaml, update epics.md |
| Dev agent | Implement backend DTO extension, frontend redesign, dead code cleanup |

### Success Criteria

1. All 22 `contract_matches` fields are accessible through the dashboard (table + detail page)
2. Matches page uses table layout with separate tabs for Pending, Approved, All
3. Cluster filter works on all tabs
4. Individual match detail page displays full record at `/matches/:id`
5. `MatchCard.tsx` deleted, no dead code references to Epic 8 as future
6. All existing tests pass, new tests cover added DTO fields
7. Generated API client regenerated and types aligned

### Artifacts to Update Post-Implementation

- `sprint-status.yaml` — add `9-7-matches-page-redesign: ready-for-dev`
- `epics.md` — add Story 9.7 definition
- UX Design Spec — minor update documenting table layout, cluster filter, status tabs (can be deferred)
