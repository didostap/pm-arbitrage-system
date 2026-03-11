# Sprint Change Proposal — Stress Test Dashboard Page

**Date:** 2026-03-13
**Triggered by:** Story 9-4 (Monte Carlo Stress Testing) — backend complete, no UI surface
**Scope:** Minor — direct implementation by development team
**Epic:** 9 (Advanced Risk & Portfolio Management)

---

## Section 1: Issue Summary

Story 9-4 delivered a comprehensive Monte Carlo stress testing backend: 1000+ random scenarios, 3 synthetic adverse scenarios, VaR at 95%/99%, drawdown probabilities, alert logic with parameter tightening suggestions, and a weekly cron schedule. The backend exposes two API endpoints (`POST /api/risk/stress-test`, `GET /api/risk/stress-test/latest`) with rich response data.

However, there is **no dashboard page** to visualize these results. The operator can only access stress test data via raw API calls, which violates the UX principle of "Zero Hunting, Zero Math, Zero Ambiguity" (UX Design Spec §Experience Principles). The operator needs to:

1. See at a glance whether risk parameters are calibrated correctly (VaR, drawdown probabilities)
2. Trigger manual stress test runs with one click
3. Review parameter tightening suggestions when alerts fire
4. Drill into scenario details (P&L distribution, synthetic results, per-contract volatilities)

This was discovered as an implementation gap — the 9-4 story focused on backend simulation logic, and the dashboard page was not scoped as part of it.

## Section 2: Impact Analysis

### Epic Impact

- **Epic 9 (in-progress):** Add one new story `9-4a-stress-test-dashboard-page`. No existing stories affected.
- **Epics 1–8, 4.5, 5.5, 6.5, 7, 7.5 (done):** No impact.
- **Epics 10–12 (backlog):** No impact.

### Story Impact

- **Story 9-4 (review):** Unaffected. Backend remains as-is. The dashboard page consumes its API.
- **No other stories require changes.**

### Artifact Conflicts

- **PRD:** No conflict. FR-RM-09 + FR-MA-04 support this addition.
- **Architecture:** No conflict. Dashboard SPA consumes engine REST API — established pattern.
- **UX Spec:** No conflict but no specific section for stress test page. Design follows established principles (progressive disclosure, information-dense panels, threshold visualization).

### Technical Impact

- **Dashboard repo (`pm-arbitrage-dashboard/`):** New page, route, nav item, hooks. ~1 new file, ~4 modified files.
- **Engine repo (`pm-arbitrage-engine/`):** No changes.
- **API client:** Must be regenerated to include stress test endpoints (routine step).
- **No infrastructure, deployment, or CI/CD changes.**

## Section 3: Recommended Approach

**Selected: Option 1 — Direct Adjustment**

Add story `9-4a-stress-test-dashboard-page` to Epic 9. Single frontend-only story following established dashboard patterns.

**Rationale:**
- Backend already done — API endpoints exist and return rich data
- Dashboard has 6 existing pages with consistent patterns to follow
- Design system components (DashboardPanel, MetricDisplay, Table, Alert, Badge) cover all needs
- No architectural decisions required — follows existing SPA patterns
- Effort: Low (1 story, ~250-400 lines of new frontend code)
- Risk: Low (additive UI, no backend changes, no cross-module dependencies)
- Timeline: No impact on Epic 9 completion — can be done in parallel with 9-4 review

**Alternatives considered:**
- Rollback: Not applicable (nothing to revert)
- MVP Review: Not applicable (MVP complete since Epic 7)

## Section 4: Detailed Change Proposals

### 4.1 sprint-status.yaml

Add story entry under Epic 9:

```yaml
9-4a-stress-test-dashboard-page: backlog # Course correction 2026-03-13: dedicated dashboard page for stress test visualization, manual trigger, and parameter suggestions
```

Update summary statistics (+1 story).

### 4.2 New Story: 9-4a-stress-test-dashboard-page.md

Full story file with:
- 5 acceptance criteria covering: data display, alert banner, manual trigger, empty state, progressive disclosure
- Detailed page layout design with ASCII wireframe
- Color coding thresholds (drawdown: green <2% / amber 2-5% / red ≥5%; VaR: green <5% bankroll / amber 5-10% / red ≥10%)
- 5 state definitions (empty, loading, data, running, error)
- 5 implementation tasks (API client regen, hooks, page component, routing, formatting utility)
- Dev notes covering: API response shape, collapsible panel pattern, drawdown bar visualization, existing components to reuse, navigation placement

### 4.3 No PRD, Architecture, or UX Spec Changes Required

The change is fully additive and within the boundaries of existing design decisions.

## Section 5: Implementation Handoff

**Change Scope:** Minor — direct implementation by development team.

**Handoff:** Developer agent receives story `9-4a-stress-test-dashboard-page.md` with complete implementation context.

**Responsibilities:**
- **Developer agent:** Implement story in `pm-arbitrage-dashboard/` repo, regenerate API client, create page + hooks, add route/navigation
- **SM (current session):** Write story file, update sprint-status.yaml

**Success Criteria:**
- `/stress-test` route loads and displays latest stress test data
- "Run Stress Test" button triggers simulation and refreshes results
- Alert banner with suggestions displays when `alertEmitted === true`
- Empty state shown when no runs exist
- Collapsible panels for scenario details and volatilities
- Navigation includes "Stress Test" link
- All existing dashboard pages unaffected
