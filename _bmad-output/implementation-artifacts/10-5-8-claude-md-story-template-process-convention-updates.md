# Story 10.5.8: CLAUDE.md, Story Template & Process Convention Updates

Status: done

## Story

As an operator,
I want all Epic 10 retro conventions, structural guard patterns, and process improvements documented in CLAUDE.md and the story creation checklist,
so that the dev agent follows these conventions automatically and Epic 11 stories are created with the new sizing and verification gates.

## Context & Motivation

Epic 10 retro produced 3 new team agreements (#24 disciplines as deliverables, #25 story sizing gate, #26 structural guards over vigilance), identified 3 recurring defect classes needing conventions, and generated structural enforcement stories (10-5-4, 10-5-5) whose patterns need to be codified. This story is the documentation counterpart — encoding the new norms so they persist beyond the retro document.

**Key insight from retro:** "Disciplines drift, deliverables ship." Open-ended behavioral commitments without enforcement mechanisms don't survive contact with real development. This story converts the retro's process agreements into concrete, documented constraints.

**Dependencies:** 10-5-4 (event wiring patterns — done), 10-5-5 (paper/live patterns — done)
**Blocks:** Epic 11 story creation (SM needs updated checklist before writing Epic 11 stories)

[Source: `_bmad-output/planning-artifacts/epics.md` Epic 10.5, Story 10-5-8]
[Source: `_bmad-output/implementation-artifacts/epic-10-retro-2026-03-22.md` — Action Items #1, #2, #6; Agreements #24, #25, #26]
[Source: `_bmad-output/implementation-artifacts/sprint-status.yaml` line 220]
[Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-22-retro-stories.md` §4, Story 10-5-8]

## Acceptance Criteria

### AC1 — Event Wiring & Collection Lifecycle Conventions Verified (10-5-4 codification)

**Given** Story 10-5-4 delivered event wiring verification patterns and collection lifecycle guards
**When** CLAUDE.md is reviewed
**Then** the following conventions are confirmed present (already added by 10-5-4 in CLAUDE.md section "Testing Conventions (Epic 10 Retro)"):
- Event wiring convention: every `@OnEvent` handler requires an `expectEventHandled()` integration test — verify key phrase "corresponding `expectEventHandled()` integration test" exists
- Collection lifecycle convention: every new Map/Set must specify cleanup strategy in a code comment and have a test for the cleanup path — verify key phrase "cleanup strategy in a code comment" exists

**And** the top 3 MEDIUM prevention measures from 10-5-4's analysis are codified in a new "Code Review Conventions (Epic 10 Retro)" section:
1. Incomplete test assertions (30%): test assertions must verify payloads with `expect.objectContaining({...})`, not just `toHaveBeenCalled()`
2. Dead code / stale artifacts (20%): remove unused imports and dead code immediately; `expectNoDeadHandlers()` catches dead event handlers
3. Type safety / validation gaps at boundaries (25%): use `decimal.js` for all financial reads from Prisma; validate external API responses at boundary; use branded types for entity IDs

[Source: `_bmad-output/implementation-artifacts/10-5-4-event-wiring-verification-collection-lifecycle-guards.md` — Dev Agent Record, MEDIUM Prevention Analysis (AC7)]
[Source: `_bmad-output/implementation-artifacts/epic-10-retro-2026-03-22.md` — Action Item #3, originally not addressed in Epic 10]

### AC2 — Paper/Live Boundary Conventions Verified (10-5-5 codification)

**Given** Story 10-5-5 delivered paper/live mode boundary patterns
**When** CLAUDE.md is reviewed
**Then** the following conventions are confirmed present (already added by 10-5-5 in CLAUDE.md section "Testing Conventions (Epic 10.5 — Paper/Live Mode Boundary)"):
- Paper/live boundary convention: every `isPaper` branch requires dual-mode test coverage — verify key phrase `describe.each([[true, 'paper'], [false, 'live']])` exists
- Repository mode-scoping: `isPaper: boolean` parameter required (no defaults) — verify key phrase "withModeFilter(isPaper)" exists
- Raw SQL `-- MODE-FILTERED` marker convention — verify key phrase "MODE-FILTERED" exists

[Source: `_bmad-output/implementation-artifacts/10-5-5-paper-live-mode-boundary-inventory-test-suite.md`]
[Source: CLAUDE.md section "Testing Conventions (Epic 10.5 — Paper/Live Mode Boundary)"]

### AC3 — Story Sizing Gate (Agreement #25)

**Given** Agreement #25 (story sizing gate for integration risk)
**When** the story creation checklist is updated
**Then** a sizing gate is added: "Stories exceeding 10 tasks or 3+ integration boundaries are flagged for splitting"
**And** the gate is a checklist item during story preparation, not a post-implementation observation
**And** CLAUDE.md documents the convention in a new "Story Design Conventions (Epic 10 Retro)" section

[Source: `_bmad-output/implementation-artifacts/epic-10-retro-2026-03-22.md` — Action Item #2, Agreement #25]
[Source: `_bmad-output/implementation-artifacts/epic-10-retro-2026-03-22.md` — "Story 10-0-1 Was Oversized" (7 phases, 17 tasks, 5 CRITICAL findings)]

### AC4 — Retro Commitments as Deliverables (Agreement #24)

**Given** Agreement #24 (retro commitments as deliverables)
**When** CLAUDE.md is updated
**Then** a new "Process Conventions (Epic 10 Retro)" section documents: "Every retro action item must be expressible as a story with ACs or a task within a story. Open-ended discipline commitments without enforcement are rejected at retro time."

[Source: `_bmad-output/implementation-artifacts/epic-10-retro-2026-03-22.md` — Agreement #24, Key Insight: "Deliverables ship. Disciplines drift."]

### AC5 — Structural Guards Over Review Vigilance (Agreement #26)

**Given** Agreement #26 (structural guards over review vigilance)
**When** CLAUDE.md is updated
**Then** the "Process Conventions (Epic 10 Retro)" section also documents: "If code review catches the same defect category three times across an epic, it becomes a pre-epic story with structural prevention — not a 'be more careful' agreement."

[Source: `_bmad-output/implementation-artifacts/epic-10-retro-2026-03-22.md` — Agreement #26, Three Recurring Defect Classes table]

### AC6 — Sequencing Verification

**Given** this story depends on patterns established by 10-5-4 and 10-5-5
**When** sequencing is evaluated
**Then** this story is implemented after 10-5-4 and 10-5-5 are complete (so documented patterns match actual implementation)

[Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-22-retro-stories.md` §4 — "Track D (last): 10-5-8 (documentation — depends on 10-5-4, 10-5-5)"]

**Status:** Both dependencies satisfied — 10-5-4 done (2026-03-23), 10-5-5 done (2026-03-23).

## Tasks / Subtasks

- [x] **Task 1: Verify 10-5-4 conventions in CLAUDE.md** (AC: #1)
  - [x] 1.1 Search CLAUDE.md for section "Testing Conventions (Epic 10 Retro)". Verify it contains key phrases: "expectEventHandled()" and "cleanup strategy in a code comment". Both must be present.
  - [x] 1.2 If missing or worded differently, add/correct to match the convention text in AC1

- [x] **Task 2: Add MEDIUM prevention measures to CLAUDE.md** (AC: #1)
  - [x] 2.1 Add new "Code Review Conventions (Epic 10 Retro)" section after "Story Design Conventions (Epic 9 Retro)"
  - [x] 2.2 Document the 3 recurring MEDIUM categories with structural prevention conventions (see Dev Notes §1)

- [x] **Task 3: Verify 10-5-5 conventions in CLAUDE.md** (AC: #2)
  - [x] 3.1 Search CLAUDE.md for section "Testing Conventions (Epic 10.5 — Paper/Live Mode Boundary)". Verify it contains key phrases: "describe.each", "withModeFilter", "MODE-FILTERED". All three must be present.
  - [x] 3.2 If missing or worded differently, add/correct to match the convention text in AC2

- [x] **Task 4: Add story sizing gate** (AC: #3)
  - [x] 4.1 Add new "Story Design Conventions (Epic 10 Retro)" section to CLAUDE.md after existing "Story Design Conventions (Epic 9 Retro)"
  - [x] 4.2 Document the sizing gate: stories >10 tasks or 3+ integration boundaries → flag for splitting
  - [x] 4.3 Add sizing gate check to `_bmad/bmm/workflows/4-implementation/bmad-create-story/checklist.md` as new subsection "3.6 Story Sizing Gate" after existing subsections 3.1-3.5 in "Step 3: Disaster Prevention Gap Analysis"

- [x] **Task 5: Add process conventions to CLAUDE.md** (AC: #4, #5)
  - [x] 5.1 Add new "Process Conventions (Epic 10 Retro)" section to CLAUDE.md before "Post-Edit Workflow"
  - [x] 5.2 Document Agreement #24: retro-as-deliverables convention
  - [x] 5.3 Document Agreement #26: structural guards over review vigilance (3x → pre-epic story)

- [x] **Task 6: Verification** (AC: all)
  - [x] 6.1 Review all CLAUDE.md changes for completeness and consistency
  - [x] 6.2 Verify no duplicate conventions (10-5-4/10-5-5 already added theirs — don't repeat)
  - [x] 6.3 Verify CLAUDE.md section ordering is logical and scannable
  - [x] 6.4 Cross-reference §4 content templates against `epic-10-retro-2026-03-22.md` Agreements #24, #25, #26 and 10-5-4 MEDIUM Prevention Analysis (Dev Agent Record, AC7 section) to ensure accurate transcription

## Dev Notes

### §1 — MEDIUM Prevention Measures (from 10-5-4 Analysis)

Story 10-5-4's MEDIUM prevention analysis (in its Dev Agent Record, AC7 section) analyzed 40+ MEDIUM findings across Epic 10 code reviews and identified these top 3 recurring categories:

**1. Incomplete Test Assertions (12 occurrences, 30%)**
Pattern: tests use `toHaveBeenCalled()` without payload verification, or assertions check existence without content.
Convention to add: "Test assertions MUST verify payloads with `expect.objectContaining({...})` or equivalent — bare `toHaveBeenCalled()` without argument verification is insufficient for event emission tests and service call verification."

**2. Dead Code / Stale Artifacts (8 occurrences, 20%)**
Pattern: unused imports, dead DTO fields, stale comments, dead `@OnEvent` handlers.
Convention to add: "Remove dead code immediately. The `expectNoDeadHandlers()` helper in `src/common/testing/expect-event-handled.ts` catches dead event handlers structurally. TypeScript strict mode (`noUnusedLocals`, `noUnusedParameters`) catches dead imports at compile time."

**3. Type Safety / Validation Gaps at Boundaries (10 occurrences, 25%)**
Pattern: `Decimal` vs `string` confusion on Prisma reads, unsafe `as` casts for API responses, env var string-to-boolean coercion.
Convention to add: "Always convert Prisma Decimal fields via `new Decimal(value.toString())`. Validate external API responses at the boundary (Zod schemas or explicit checks). Use branded types for entity IDs. Never trust `configService.get<boolean>()` — NestJS returns strings from env vars."

[Source: `_bmad-output/implementation-artifacts/10-5-4-event-wiring-verification-collection-lifecycle-guards.md` — MEDIUM Prevention Analysis (AC7), Summary Table]

### §2 — Files to Modify

| File | Change Type | Notes |
|------|-------------|-------|
| `CLAUDE.md` (root repo) | Modify | Add 3 new sections: "Code Review Conventions (Epic 10 Retro)", "Story Design Conventions (Epic 10 Retro)", "Process Conventions (Epic 10 Retro)" |
| `_bmad/bmm/workflows/4-implementation/bmad-create-story/checklist.md` | Modify | Add story sizing gate validation step |

**No engine repo files are modified.** This is a documentation-only story — no production code, no tests to run.

### §3 — CLAUDE.md Section Ordering (After Changes)

Current ordering with insertions marked:

```
## Testing
### Testing Conventions (Epic 9 Retro)
### Testing Conventions (Epic 10 Retro)          ← existing (10-5-4)
### Testing Conventions (Epic 10.5 — Paper/Live)  ← existing (10-5-5)

## Story Design Conventions (Epic 9 Retro)        ← existing
## Story Design Conventions (Epic 10 Retro)       ← NEW (Task 4): sizing gate
## Code Review Conventions (Epic 10 Retro)        ← NEW (Task 2): MEDIUM prevention
## Process Conventions (Epic 10 Retro)            ← NEW (Task 5): #24, #26

## Post-Edit Workflow                              ← existing
```

### §4 — Specific CLAUDE.md Content to Add

**"Story Design Conventions (Epic 10 Retro)" section:**
```markdown
## Story Design Conventions (Epic 10 Retro)

- **Story sizing gate:** Stories exceeding 10 tasks or 3+ integration boundaries MUST be flagged for splitting during story preparation. Story 10-0-1 (7 phases, 17 tasks, 5 CRITICAL review findings) demonstrated that oversized stories fragment the developer's mental model and make integration seam verification impractical. Pre-split review during preparation, not after implementation reveals the problem.
```

**"Code Review Conventions (Epic 10 Retro)" section:**
```markdown
## Code Review Conventions (Epic 10 Retro)

- **Assertion depth:** Test assertions MUST verify payloads with `expect.objectContaining({...})` or equivalent. Bare `toHaveBeenCalled()` without argument verification is insufficient for event emission and service call tests. This was the most common MEDIUM finding (30%) in Epic 10 code reviews.
- **Dead code removal:** Remove unused imports, dead DTO fields, and stale comments immediately. Use `expectNoDeadHandlers()` from `src/common/testing/expect-event-handled.ts` for dead event handler detection. TypeScript strict mode (`noUnusedLocals`, `noUnusedParameters`) catches dead imports at compile time.
- **Boundary type safety:** Always convert Prisma Decimal fields via `new Decimal(value.toString())`. Validate external API responses at the boundary with explicit checks. Use branded entity ID types. Never trust `configService.get<boolean>()` for env vars — NestJS returns strings; parse explicitly.
```

**"Process Conventions (Epic 10 Retro)" section:**
```markdown
## Process Conventions (Epic 10 Retro)

- **Retro commitments as deliverables (Agreement #24):** Every retro action item MUST be expressible as a story with acceptance criteria or a task within a story. Open-ended discipline commitments without enforcement mechanisms are rejected at retro time. If it can't be a story, rephrase until it can.
- **Structural guards over review vigilance (Agreement #26):** If code review catches the same defect category three times across an epic, it becomes a pre-epic story with structural prevention (test templates, linter rules, startup checks) — not a "be more careful" agreement. Recurring defect classes need constraints, not vigilance.
```

### §5 — Story Creation Checklist Update

Add to `_bmad/bmm/workflows/4-implementation/bmad-create-story/checklist.md` in "Step 3: Disaster Prevention Gap Analysis", as a new subsection:

```markdown
#### 3.6 Story Sizing Gate (Agreement #25)

- **Task count check:** Does this story exceed 10 tasks? If yes, flag for splitting.
- **Integration boundary check:** Does this story cross 3+ integration boundaries (e.g., connector + module + dashboard + persistence)? If yes, flag for splitting.
- **Historical evidence:** Story 10-0-1 had 7 phases, 17 tasks, and 5 CRITICAL review findings — oversized stories fragment the developer's mental model and make subsystem verification impractical.
- **Action:** If flagged, recommend splitting into independently deployable stories before proceeding.
```

### §6 — Anti-Patterns to Avoid

- **DO NOT** duplicate conventions already in CLAUDE.md from 10-5-4/10-5-5. Verify they exist, do not re-add.
- **DO NOT** add implementation-level details (e.g., `configService.getDecimal()` helper) that don't exist yet. Reference only patterns and tools that are currently in the codebase.
- **DO NOT** modify any engine code. This is documentation-only.
- **DO NOT** add overly prescriptive process rules. Keep conventions actionable and specific — "if X then Y" format, not aspirational statements.

### §7 — Previous Story Intelligence

**From Story 10-5-4:**
- CLAUDE.md updated with event wiring and collection lifecycle conventions (confirmed in section "Testing Conventions (Epic 10 Retro)")
- MEDIUM prevention analysis produced 3 categories with structural prevention measures
- `expectNoDeadHandlers()` helper exists at `src/common/testing/expect-event-handled.ts`

**From Story 10-5-5:**
- CLAUDE.md updated with paper/live boundary conventions (confirmed in section "Testing Conventions (Epic 10.5 — Paper/Live Mode Boundary)")
- `withModeFilter(isPaper)` helper exists at `src/persistence/repositories/mode-filter.helper.ts`
- Paper/live inventory at `src/common/testing/paper-live-inventory.md`

**From Story 10-5-7:**
- External secrets design doc at `docs/external-secrets-design.md` — referenced by this story but not modified

### Project Structure Notes

- CLAUDE.md is in the **root repo** (parent of engine) — requires a root repo commit
- `_bmad/bmm/workflows/4-implementation/bmad-create-story/checklist.md` is also in the root repo
- No engine repo files are touched — no separate engine commit needed
- Dual-repo awareness: this story only touches root repo files

### References

- [Source: `_bmad-output/implementation-artifacts/epic-10-retro-2026-03-22.md` — Action Items #1, #2, #6; Agreements #24, #25, #26; Three Recurring Defect Classes table; "Disciplines drift, deliverables ship" insight]
- [Source: `_bmad-output/planning-artifacts/epics.md` Epic 10.5, Story 10-5-8 — Full ACs]
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-22-retro-stories.md` §4, Story 10-5-8 definition and sequencing]
- [Source: `_bmad-output/implementation-artifacts/10-5-4-event-wiring-verification-collection-lifecycle-guards.md` — MEDIUM Prevention Analysis (AC7), collection/wiring conventions]
- [Source: `_bmad-output/implementation-artifacts/10-5-5-paper-live-mode-boundary-inventory-test-suite.md` — Paper/live boundary conventions]
- [Source: `CLAUDE.md` sections "Testing Conventions (Epic 9/10/10.5)" and "Story Design Conventions (Epic 9 Retro)" — existing conventions added by prior stories]
- [Source: `_bmad/bmm/workflows/4-implementation/bmad-create-story/checklist.md` — Current story creation validation checklist]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — documentation-only story, no tests or production code.

### Completion Notes List

- **Task 1:** Verified 10-5-4 conventions in CLAUDE.md — `expectEventHandled()` and "cleanup strategy in a code comment" both present in "Testing Conventions (Epic 10 Retro)" section. No corrections needed.
- **Task 2:** Added "Code Review Conventions (Epic 10 Retro)" section with 3 MEDIUM prevention measures: assertion depth (30%), dead code removal (20%), boundary type safety (25%).
- **Task 3:** Verified 10-5-5 conventions in CLAUDE.md — `describe.each`, `withModeFilter`, `MODE-FILTERED` all present in "Testing Conventions (Epic 10.5 — Paper/Live Mode Boundary)" section. No corrections needed.
- **Task 4:** Added "Story Design Conventions (Epic 10 Retro)" section with sizing gate (>10 tasks or 3+ integration boundaries → flag for split). Added §3.6 Story Sizing Gate to story creation checklist.
- **Task 5:** Added "Process Conventions (Epic 10 Retro)" section with Agreement #24 (retro-as-deliverables) and Agreement #26 (structural guards over review vigilance, 3x → pre-epic story).
- **Task 6:** Full verification pass — section ordering matches §3 target, no duplicate conventions, cross-reference against retro doc confirmed accurate transcription of all agreements.
- **Post-story:** Per user request, added 3 additional CLAUDE.md sections beyond original story scope: "Session Initialization" (Serena activation, baseline verification, memory maintenance), "Post-Implementation Review" (Lad MCP code review, retry logic, evaluation criteria), expanded "Tool Preferences" (web research failure handling, skip conditions). Serena memory file names aligned to actual project memories (`project_overview`, `suggested_commands`, `code_style`).

### File List

- `CLAUDE.md` — Added 3 story sections: "Story Design Conventions (Epic 10 Retro)", "Code Review Conventions (Epic 10 Retro)", "Process Conventions (Epic 10 Retro)". Added 2 operational sections: "Session Initialization", "Post-Implementation Review". Expanded "Tool Preferences" with web research failure handling.
- `_bmad/bmm/workflows/4-implementation/bmad-create-story/checklist.md` — Added "3.6 Story Sizing Gate (Agreement #25)" subsection
- `_bmad-output/implementation-artifacts/10-5-8-claude-md-story-template-process-convention-updates.md` — Task checkboxes, status, Dev Agent Record
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Story status updated
