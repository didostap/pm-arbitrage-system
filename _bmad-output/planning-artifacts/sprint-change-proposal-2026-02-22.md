# Sprint Change Proposal — Epic 5 Retro Artifact Alignment

**Date:** 2026-02-22
**Triggered by:** Epic 5 Retrospective (2026-02-21)
**Scope Classification:** Minor — Direct Adjustment
**Facilitator:** Bob (Scrum Master)
**Participant:** Arbi (Project Lead / Tech Lead)

## Section 1: Issue Summary

The Epic 5 retrospective committed to Story 5.5.0 (Interface Stabilization & Test Infrastructure), a gas estimation story in Epic 6, and 3 process changes. None were reflected in planning artifacts (`epics.md`, `sprint-status.yaml`). Story 5.5.1 has a hard dependency on 5.5.0's deliverables — the decorator pattern requires a stable, frozen interface and centralized mock factories. Starting Epic 5.5 without this correction would break the dependency chain.

**Category:** Misalignment between retro commitments and planning artifacts.

**Evidence:**
- `sprint-status.yaml` listed Epic 5.5 with only Stories 5.5.1-5.5.3 (no 5.5.0)
- `epics.md` had no Story 5.5.0 section
- Retro document defined full Story 5.5.0 spec with 7 deliverables and explicit dependency chain
- Gas estimation TODO carried since Epic 2 with retro commitment to make it an Epic 6 story
- Sprint-status summary statistics were stale (retro count, story totals)

## Section 2: Impact Analysis

### Epic Impact
| Epic | Impact | Details |
|---|---|---|
| Epic 5.5 | **Direct** | Story 5.5.0 added as first story. Dependency: 5.5.0 → 5.5.1 |
| Epic 6 | **Direct** | Story 6.0 (gas estimation) added before Story 6.1 |
| Epic 9 | Watched | Interface freeze constrains how new `IRiskManager` methods are added |
| Epic 10 | Watched | `resolutionDate` write path deferred here |
| All others | None | No impact |

### Artifact Impact
| Artifact | Change | Status |
|---|---|---|
| `epics.md` | Story 5.5.0 added, Story 6.0 added, summary entries updated | Applied |
| `sprint-status.yaml` | Story 5.5.0 entry, Story 6.0 entry, summary statistics corrected, retro status fixed | Applied |
| Architecture doc | Reconciliation module location update | Handled within Story 5.5.0 scope |
| `gotchas.md` | P&L source-of-truth rule | Handled within Story 5.5.0 scope |
| `technical-debt.md` | Mark resolved items, add Epic 5 items | Handled within Story 5.5.0 scope |
| Story template | "Check gotchas.md" reminder | Skipped — revisit when gotchas.md exists |

### PRD Impact
- None. MVP scope unchanged. These are infrastructure and quality stories supporting the existing MVP path.

## Section 3: Recommended Approach

**Selected: Direct Adjustment** — modify/add stories within existing plan.

**Rationale:**
- The retro already designed the solution with explicit deliverables and dependency chains
- No rollback needed (Epic 5.5 hasn't started)
- No MVP scope change required
- Zero architectural risk — changes align with existing architecture doc
- Story-or-drop discipline (5 epics of evidence) demands these committed items become stories

**Alternatives considered:**
- Rollback: Not applicable — no completed work to revert
- MVP Review: Not needed — MVP scope unaffected

**Effort:** Low | **Risk:** Low | **Timeline impact:** None (prep work was already planned)

## Section 4: Detailed Change Proposals

### Applied Changes

**4.1 — Story 5.5.0 added to `epics.md`** (Approved)
- Full story spec with 7 acceptance criteria covering: `cancelOrder()` implementation, centralized mock factories, test file migration, gotchas.md creation, technical-debt.md update, architecture doc update, persistence coverage audit
- Sequencing constraint and interface freeze documented in story
- DoD gates from Epic 4.5 retro included
- Epic 5.5 summary entry updated

**4.2 — Story 6.0 (Gas Estimation) added to `epics.md`** (Approved)
- Full story spec with acceptance criteria covering: TODO removal, gas estimation logic, 20% safety buffer, paper trading calibration
- Technical debt provenance documented (Epic 2 carry-forward)
- Epic 6 summary entry updated

**4.3 — `sprint-status.yaml` updated** (Approved)
- `5-5-0-interface-stabilization-test-infrastructure: backlog` added
- `6-0-gas-estimation-implementation: backlog` added
- Total Stories: 55 → 57
- Total Items: 72 → 74
- Retrospectives done: 5 → 6, stale note removed

### Skipped Changes

**4.4 — Story template gotchas.md reminder** (Skipped)
- Rationale: gotchas.md doesn't exist yet. Revisit after Story 5.5.0 delivers it.

## Section 5: Implementation Handoff

**Scope:** Minor — direct implementation by dev team.

| Recipient | Responsibility |
|---|---|
| **Scrum Master (Bob)** | Artifacts updated (this session). Create Story 5.5.0 file via CS workflow when Epic 5.5 begins. |
| **Dev agent** | Implement Story 5.5.0 → 5.5.1 → 5.5.2 → 5.5.3 in sequence |
| **Arbi (operator)** | Approve story files as they're created. Monitor interface freeze compliance. |

**Success Criteria:**
- Story 5.5.0 merges with all 7 deliverables complete before 5.5.1 begins
- Interface freeze enforced after 5.5.0
- Gas estimation story picked up early in Epic 6

**Next Steps:**
1. Run Create Story [CS] workflow for Story 5.5.0 when ready to begin Epic 5.5
2. Story 5.5.2 spec review can happen during 5.5.0 development (parallel prep)
3. Story 5.5.3 spec review can happen during 5.5.1 development (parallel prep)

---

**Proposal Status:** Approved and applied
**Sprint Change Proposal Date:** 2026-02-22
