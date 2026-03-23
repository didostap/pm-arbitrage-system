# Sprint Change Proposal — Epic 10.5 Retro Convention Encoding

**Date:** 2026-03-23
**Triggered by:** Epic 10.5 Retrospective
**Scope:** Minor — Documentation/process artifact updates only
**Status:** Approved

---

## 1. Issue Summary

Epic 10.5 retrospective (2026-03-23) produced three new team agreements (#27-#29) that must be encoded into project artifacts before Epic 10.7 begins. Agreement #24 (validated by 100% vs 62% follow-through comparison) proves that undocumented disciplines drift — conventions must be artifact-encoded to survive.

### Triggering Findings

1. **5/5 code stories had critical findings caught only at review** — no earlier architecture checkpoint exists (→ Agreement #27: design sketch gate)
2. **Secondary Lad MCP reviewer consistently failed** — single point of failure in quality gate (→ Agreement #28: reviewer redundancy)
3. **Backend naming mismatch caused cascading E2E failures in 10-5-3** — spec-to-implementation divergence (→ Agreement #29: naming walkthrough)

---

## 2. Impact Analysis

### Epic Impact
- **Epic 10.5:** Complete. No changes needed.
- **Epic 10.7:** No scope changes. Preparation plan (4 items + 2 AC templates) already documented in retro. Applied during story creation.
- **Epic 11+:** No impact.

### Artifact Conflicts
- **PRD:** None. MVP complete.
- **Architecture:** None. Process conventions, not architecture decisions.
- **UX:** None.
- **CLAUDE.md:** Three new convention sections added.

### Technical Impact
- None. Documentation-only change.

---

## 3. Recommended Approach

**Direct Adjustment** — encode agreements into CLAUDE.md.

**Rationale:** All action items are process conventions requiring artifact encoding. No story/epic restructuring needed. Sprint status already accurate.

---

## 4. Changes Applied

### CLAUDE.md — Three new sections added

**Story Design Conventions (Epic 10.5 Retro):**
- Agreement #27: Design sketch gate for hot-path stories (execution, edge calc, risk)
- Agreement #29: Pre-implementation naming walkthrough (string literals, enums, DTOs, API paths)

**Code Review Conventions (Epic 10.5 Retro):**
- Agreement #28: Reviewer redundancy — fallback reviewer before each epic

### Sprint Status YAML
- Verified accurate: epic-10-5 done, retrospective done, summary stats current
- No changes needed

---

## 5. Implementation Handoff

**Scope:** Minor — direct implementation complete.
**Executed by:** Bob (SM) during course correction workflow.
**No further handoff required.**

### Epic 10.7 Pre-Kickoff Checklist (from retro, NOT part of this proposal)

These are preparation tasks to be executed before Epic 10.7 story creation:

1. [ ] Design sketch for 10-7-1 (Dual-Leg Liquidity Gate) — Winston reviews
2. [ ] VWAP knowledge transfer for 10-7-2 implementer
3. [ ] Structural guard dry run against execution module — Dana
4. [ ] Investigation scope caps in 10-7-4 and 10-7-9 story context — Bob during story creation
5. [ ] Apply ConfigAccessor AC template to 6 stories (10-7-1, -3, -5, -6, -8, -9)
6. [ ] Apply financial math invariant tests AC template to 2 stories (10-7-2, 10-7-4)

---

## 6. Approval

- **Approved by:** Arbi (2026-03-23)
- **Conditions:** None
