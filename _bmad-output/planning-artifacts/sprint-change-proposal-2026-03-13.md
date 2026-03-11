# Sprint Change Proposal — Capital Efficiency Gating

**Date:** 2026-03-13
**Triggered by:** Paper trading observation (Sprint 9, post-Epic 8)
**Scope:** Minor — direct implementation within existing epic
**Status:** Approved by operator

---

## Section 1: Issue Summary

The system enters arbitrage positions without evaluating capital efficiency. The only opportunity quality gate is net edge ≥ 0.8% (FR-AD-03). No requirement exists to filter by resolution date presence or annualized return threshold.

**Discovery:** During live paper trading, a position on "Will OpenAI or Anthropic IPO first?" revealed:
- TP: +$0.23 vs SL: -$8.15 (35:1 risk/reward against)
- ~$50 capital locked with no known resolution date (`resolution_date: NULL`)
- Maximum theoretical profit: $1.55 on 50.14 contracts (3.09% net edge)
- Annualized return: unquantifiable (no resolution date)

**Root cause:** The PRD and detection pipeline define opportunity quality exclusively by instantaneous net edge. The system treats a 3% edge resolving in 7 days identically to a 3% edge resolving never.

**Evidence:** Confirmed via database queries — `open_positions`, `orders`, and `contract_matches` tables all validated the problem. Industry research confirms professional arbitrage systems require 15-25% annualized minimums and refuse positions without known resolution dates.

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Status | Impact |
|------|--------|--------|
| **Epic 9** (in-progress) | Advanced Risk & Portfolio Management | **Direct** — add Story 9.5: Capital Efficiency Gating & Resolution Date Filtering. Slots after 9-1b, before 9-2. |
| **Epic 10** (backlog) | Model-Driven Exits & Advanced Execution | **Watched** — Story 10.2 (five-criteria exits, criterion #3: time decay) benefits from resolution date availability. No blocking changes. |
| **Epics 11, 12** (backlog) | Extensibility, Compliance | **Unaffected** |

### Artifact Adjustments

| Artifact | Change | Severity |
|----------|--------|----------|
| **PRD** | Add FR-AD-08 (resolution date + annualized return gate). Extend Opportunity Qualification Criteria with two new gates. | Minor addition |
| **Epics** | Add Story 9.5 definition to Epic 9. Update FR coverage map with FR-AD-08 → Epic 9. Update Epic 9 summary block. | Minor addition |
| **Architecture** | No structural changes. Opportunity type needs `resolutionDate` populated in pipeline. Risk validation gets additional check. | Minimal |
| **UX Design** | No changes. Existing filter transparency patterns handle new reasons. | None |
| **Sprint Status** | Add `9-5-capital-efficiency-gating: backlog` entry under Epic 9. | Bookkeeping |
| **Env Config** | Add `MIN_ANNUALIZED_RETURN` to `.env.example` and `.env.development`. | Bookkeeping |

---

## Section 3: Recommended Approach

**Selected: Direct Adjustment** — add Story 9.5 to Epic 9 within current sprint plan.

### Rationale

This is a missing guardrail, not a design flaw. The detection pipeline works correctly — it finds real opportunities. The gap is in risk management not asking "is this opportunity worth the capital lockup?" One focused story addresses the entire problem without touching completed work or changing architecture.

### Trade-offs Considered

- **Detection (Epic 3) vs Risk (Epic 9):** Detection's job is "does an opportunity exist?" Risk's job is "should we act on it?" Capital efficiency is a deployment-of-capital decision → risk management.
- **Resolution date only vs annualized return:** Resolution date gate alone wouldn't catch known-but-too-long positions (e.g., 2% edge resolving in 6 months). Annualized return threshold handles both cases.
- **Max hold duration:** Useful safety net for positions that entered before this gate existed, but it's a separate exit management concern (Epic 10), not entry filtering.

### Effort & Risk

- **Effort:** Low — single story, single service, existing patterns
- **Risk:** Low — no architectural changes, no new dependencies, no schema migration
- **Timeline impact:** Negligible — slots into current sprint naturally

---

## Section 4: Detailed Change Proposals

### 4.1 PRD — New Functional Requirement

**File:** `_bmad-output/planning-artifacts/prd.md`
**Section:** Functional Requirements — Arbitrage Detection Module (after FR-AD-07)

```
ADD:

FR-AD-08 [MVP]: System shall reject opportunities where the contract match has no
known resolution date, or where the annualized net return falls below a configurable
minimum threshold (default: 15%). Annualized net return is calculated as:
(net_edge / capital_per_unit) × (365 / days_to_resolution). Filtered opportunities
are logged with the calculated annualized return and rejection reason.
```

### 4.2 PRD — Opportunity Qualification Criteria

**File:** `_bmad-output/planning-artifacts/prd.md`
**Section:** Opportunity Qualification Criteria

```
ADD (after edge threshold, before order book depth):

- Resolution date required: Contract match must have a known resolution date.
  Opportunities without resolution dates are filtered with reason logged. (FR-AD-08)
- Capital efficiency: Annualized net return must meet minimum threshold (configurable,
  default 15%). Formula: (net_edge / capital_per_unit) × (365 / days_to_resolution).
  Opportunities below threshold are filtered with calculated annualized return
  logged. (FR-AD-08)
```

### 4.3 Epics — Story 9.5 Definition

**File:** `_bmad-output/planning-artifacts/epics.md`
**Section:** Epic 9 (after Story 9.4, before Epic 10)

```
ADD:

### Story 9.5: Capital Efficiency Gating & Resolution Date Filtering

As an operator,
I want the system to reject opportunities that lack a known resolution date or
whose annualized return doesn't justify the capital lockup,
So that my capital is only deployed in trades with favorable time-value economics.

**Acceptance Criteria:**

**Given** an opportunity passes the net edge threshold (FR-AD-03, ≥0.8%)
**When** the contract match has no resolution date (null)
**Then** the opportunity is rejected before risk validation
**And** an `OpportunityFilteredEvent` is emitted with reason: "no resolution date"
**And** the rejection is logged with pair ID and contract descriptions

**Given** an opportunity has a known resolution date
**When** the annualized net return is calculated as:
  `(net_edge / capital_per_unit) × (365 / days_to_resolution)`
**And** the result is below the configurable minimum (default: 15%)
**Then** the opportunity is rejected before risk validation (FR-AD-08)
**And** an `OpportunityFilteredEvent` is emitted with reason: "annualized return
  {calculated}% below {threshold}% minimum"
**And** the rejection is logged with calculated annualized return, days to resolution,
  and threshold

**Given** an opportunity has a resolution date and meets the annualized return threshold
**When** the capital efficiency check passes
**Then** the opportunity proceeds to risk validation unchanged
**And** the annualized return is included in the enriched opportunity context for
  downstream logging and dashboard display

**Given** the capital efficiency gate configuration
**When** the engine starts
**Then** `MIN_ANNUALIZED_RETURN` is loaded from env config (default: 0.15)
**And** invalid values (negative, >10.0) are rejected at startup
**And** the threshold is logged at startup for operator awareness

**Given** the FR coverage map
**When** this story is complete
**Then** FR-AD-08 is covered by Epic 9 (Story 9.5)
```

### 4.4 Epics — FR Coverage Map & Epic 9 Summary

**File:** `_bmad-output/planning-artifacts/epics.md`

**FR Coverage Map** — add after FR-AD-07 line:
```
FR-AD-08: Epic 9 - Resolution date gating & annualized return threshold
```

**Epic 9 summary block** — update:
```
OLD:
**FRs covered:** FR-RM-05, FR-RM-06, FR-RM-07, FR-RM-08, FR-RM-09

NEW:
**FRs covered:** FR-AD-08, FR-RM-05, FR-RM-06, FR-RM-07, FR-RM-08, FR-RM-09
```

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

Direct implementation by dev team after story creation.

### Handoff Plan

| Role | Responsibility | Status |
|------|---------------|--------|
| **SM (Bob)** | Draft Sprint Change Proposal | ✅ Complete (this document) |
| **SM (Bob)** | Update sprint-status.yaml | Pending approval |
| **SM (create-story)** | Create full Story 9.5 implementation file | After approval |
| **PO/Arbi** | Approve PRD edits and Story 9.5 definition | Pending |
| **Dev agent** | Implement Story 9.5 via TDD workflow | After story creation |

### Success Criteria

1. Opportunities without resolution dates are filtered and logged
2. Opportunities below annualized return threshold are filtered with calculated return logged
3. Existing paper position on "Will OpenAI or Anthropic IPO first?" would have been filtered (validation test case)
4. All existing tests continue to pass
5. New filter reasons visible in Telegram alerts and audit logs via existing event infrastructure

### Recommended Next Steps

1. Approve this Sprint Change Proposal
2. Apply PRD edits (Section 4.1, 4.2)
3. Apply Epic edits (Section 4.3, 4.4)
4. Update sprint-status.yaml
5. Create Story 9.5 implementation file via create-story workflow
6. Manually close the current IPO paper position (would have been filtered)
7. Dev implements via TDD
