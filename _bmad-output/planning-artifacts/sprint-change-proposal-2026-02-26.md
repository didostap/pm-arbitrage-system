# Sprint Change Proposal — Code Review Tech Debt Triage

**Date:** 2026-02-26
**Trigger:** Story 6.5.0 code review findings (LAD MCP review, 2026-02-25)
**Scope Classification:** Minor
**Recommended Approach:** Direct Adjustment

---

## 1. Issue Summary

Code review of Story 6-5-0 (Codebase Readiness & Tech Debt Clearance) surfaced 11 findings, of which 6 require future action. These are pre-existing tech debt items originating from Epics 1, 2, and 5 — not regressions introduced by Story 6.5.0. They range from a potential stale pricing bug to missing observability to unvalidated external inputs.

**Evidence:** Full findings documented in `_bmad-output/implementation-artifacts/6-5-0-code-review-findings.md`.

| # | Finding | Origin | Assessed Severity |
|---|---------|--------|-------------------|
| 4 | Silent error swallowing in `verifyDepth` catch block | Epic 5 | Medium |
| 5 | `handlePriceChange` may not update price levels (potential stale pricing) | Epic 2 | High (if confirmed) |
| 7 | Hardcoded order polling timeouts, no retry/jitter | Epic 5 | Low |
| 8 | Raw `Error` throw in `getPositions` placeholder | Epic 1 | Low |
| 10 | No metrics/events for data staleness detection | Epic 2 | Medium |
| 11 | Unvalidated external API response types in `postOrder` | Epic 5 | Medium |

---

## 2. Impact Analysis

### Epic Impact

| Epic | Impact | Action |
|------|--------|--------|
| **Epic 6.5** (current) | Findings #4, #5, #8, #10 are small-scope fixes that should land before validation | Add Story 6.5.0a |
| **Epic 7** | Finding #4 was originally earmarked here; resolved by 6.5.0a instead | No change needed |
| **Epic 10** | Finding #7 fits Story 10.4 (adaptive leg sequencing) | Backlog note added |
| **Epic 11** | Finding #11 fits Story 11.1 (connector plugin architecture) | Backlog note added |
| All others | No impact | — |

### Artifact Conflicts

- **PRD:** No conflicts. Fixes improve compliance with FR-DI-02, FR-DI-04, FR-MA-01, NFR-R5.
- **Architecture:** No conflicts. Fixes close compliance gaps against documented mandates (event emission, SystemError hierarchy).
- **UI/UX:** No impact.
- **Sprint status:** Updated with new story entry.
- **Epics doc:** Updated with story definition and backlog notes.

---

## 3. Recommended Approach

**Direct Adjustment** — one new story in Epic 6.5, two backlog annotations in Epics 10 and 11.

**Rationale:**
1. **Small scope** — 4 targeted fixes, estimated 4-5h total dev effort
2. **Ideal timing** — fixing observability gaps and potential data accuracy issues before the validation run ensures trustworthy validation results
3. **Zero timeline risk** — story slots before 6-5-1 which is still in backlog
4. **Architecture alignment** — all 4 fixes close compliance gaps against documented mandates

**Alternatives considered:**
- Rollback: Not viable — findings are pre-existing, not regressions
- MVP scope reduction: Not applicable — MVP is already complete

---

## 4. Detailed Change Proposals

### 4.1 New Story: 6.5.0a (Code Review Tech Debt Fixes)

Added to `epics.md` under Epic 6.5 with 4 acceptance criteria covering findings #4, #5, #8, #10. Full story text in the epics document.

**Sequencing updated:** `6.5.0 → 6.5.0a → [6.5.1 + 6.5.2 + 6.5.3 in parallel] → 6.5.4 → 6.5.5 → 6.5.6`

### 4.2 Backlog Note: Epic 10, Story 10.4

Added tech debt note for Finding #7 (configurable timeouts + jitter for order polling) to be addressed during adaptive leg sequencing implementation.

### 4.3 Backlog Note: Epic 11, Story 11.1

Added tech debt note for Finding #11 (runtime validation of external API responses) to be addressed during connector plugin architecture implementation.

### 4.4 Sprint Status Update

Added `6-5-0a-code-review-tech-debt-fixes: backlog` entry. Updated total story count from 64 to 65.

---

## 5. Implementation Handoff

**Scope:** Minor — direct implementation by dev team.

| Step | Owner | Action |
|------|-------|--------|
| 1 | Scrum Master | Create story file via Create Story workflow |
| 2 | Dev agent | Implement Story 6.5.0a via TDD workflow |
| 3 | Dev agent | Run code review on completed story |
| 4 | Scrum Master | Update sprint status to `done` after review passes |

**Success criteria:**
- All 4 acceptance criteria met
- All existing tests pass + new tests for event emissions
- `pnpm lint` zero errors
- Findings #7 and #11 backlog notes visible in epics doc for future pickup
