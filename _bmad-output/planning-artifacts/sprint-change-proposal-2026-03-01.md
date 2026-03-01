# Sprint Change Proposal — 2026-03-01

## Issue Summary

Story 6-5-4 (Read-Only Detection Validation, 48h) is redundant. The paper trading mode implemented in Epic 5.5 already provides detection-with-execution-disabled capability, making a separate "read-only detection" phase unnecessary. Removing this story streamlines the Epic 6.5 validation pipeline without losing any validation coverage.

## Impact Analysis

- **Epic Impact:** Epic 6.5 only. No other epics affected.
- **Story Impact:** Stories 6-5-5 and 6-5-6 have dependency references to 6-5-4 that need cleanup.
- **Artifact Conflicts:** None. No PRD, architecture, or UI/UX changes required.
- **Technical Impact:** None. No code changes needed.

## Recommended Approach

**Direct Adjustment** — Remove story, update sequencing references, update sprint status.

- Effort: Low
- Risk: Low
- Timeline impact: Shortens Epic 6.5 by removing a 48h validation phase

## Detailed Change Proposals

### 1. DELETE Story 6-5-4 file
- File: `_bmad-output/implementation-artifacts/6-5-4-read-only-detection-validation.md`
- Action: Delete entirely

### 2. UPDATE sprint-status.yaml
- Remove line: `6-5-4-read-only-detection-validation: in-progress`

### 3. UPDATE epics.md — Epic 6.5 sequencing
- OLD: `6.5.0 → 6.5.0a → [6.5.1 + 6.5.2 in parallel] → 6.5.2a → 6.5.3 → 6.5.4 → 6.5.5 → 6.5.6`
- NEW: `6.5.0 → 6.5.0a → [6.5.1 + 6.5.2 in parallel] → 6.5.2a → 6.5.3 → 6.5.5 → 6.5.6`

### 4. UPDATE epics.md — Remove Story 6.5.4 section
- Remove the entire "Story 6.5.4: Read-Only Detection Validation (48h)" section

### 5. UPDATE epics.md — Story 6.5.5 dependencies
- Remove "Requires 6.5.4 complete with Phase 1 gate passed" → "Requires 6.5.3 complete"
- Remove "Given Story 6.5.4 Phase 1 gate has been passed and Arbi has approved proceeding" AC line
- Update Previous Story Intelligence to remove 6.5.4 references

### 6. UPDATE epics.md — Story 6.5.6 references
- Remove "Phase 1 summary from Story 6.5.4 feeds into the report" from Previous Story Intelligence

### 7. UPDATE epics.md — Stories 6.5.1, 6.5.2, 6.5.3 sequencing notes
- Change "Must complete before 6.5.4" → "Must complete before 6.5.5"

## Implementation Handoff

- **Scope:** Minor — direct file edits
- **Executed by:** Scrum Master (this session)
- **Success criteria:** sprint-status.yaml and epics.md reflect the removal; no dangling references to 6-5-4
