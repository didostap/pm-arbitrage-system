# Sprint Change Proposal: Kalshi Normalization Deduplication

**Date:** 2026-02-18
**Trigger:** Story 4.5.4 (Technical Debt Consolidation) identified debt item #1
**Scope Classification:** Minor
**Status:** Approved

---

## Section 1: Issue Summary

During Story 4.5.4, a technical debt registry was created cataloguing 6 items from Epics 1–4. Debt item #1 (High priority) identifies that Kalshi order book normalization logic — cents-to-decimal conversion and NO-to-YES price inversion — is duplicated in 3 locations:

1. `connectors/kalshi/kalshi.connector.ts` (lines 148–155)
2. `connectors/kalshi/kalshi-websocket.client.ts` (lines 287–295)
3. `modules/data-ingestion/order-book-normalizer.service.ts` (lines 28–35)

Epic 5 (Trade Execution) will build directly on top of these connectors. Carrying 3-way duplication into execution code increases bug surface and maintenance burden.

## Section 2: Impact Analysis

**Epic Impact:**
- Epic 4.5 (in-progress): Extended by one story (4.5.5). All existing stories (4.5.0–4.5.4) remain done.
- Epic 5 (backlog): Benefits from cleaner connector code. No changes to Epic 5 stories.
- No other epics affected.

**Artifact Conflicts:** None.
- PRD: No functional requirements change.
- Architecture: Refactor follows existing `common/utils/` pattern. No new dependency arrows.
- UI/UX: No impact.

**Technical Impact:**
- 3 source files modified (import shared utility instead of inline logic)
- 1 new file created (`common/utils/kalshi-normalization.util.ts` or similar)
- New unit tests for the shared utility
- 498-test baseline must hold

## Section 3: Recommended Approach

**Selected:** Direct Adjustment — add Story 4.5.5 to Epic 4.5.

**Rationale:**
- Epic 4.5 exists specifically as a pre-execution hygiene gate
- Low effort, low risk refactor with strong test safety net (498 tests)
- Prevents bloating Epic 5 Story 5.1 with unrelated refactoring
- Single source of truth for Kalshi normalization before execution code builds on it

**Alternatives considered:**
- Fold into Epic 5 Story 5.1: Rejected — Story 5.1 is already complex (order submission, 2 new Prisma tables, position tracking)
- Defer to post-Epic 5: Rejected — increases risk of normalization bugs in live execution code

## Section 4: Detailed Change Proposals

### 4a. Add Story 4.5.5 to `epics.md`

Insert after Story 4.5.4, before Epic 5 header:

**Story 4.5.5: Kalshi Order Book Normalization Deduplication**

As an operator,
I want the Kalshi cents-to-decimal and NO-to-YES inversion logic extracted to a single shared utility,
So that Epic 5 execution code builds on a single source of truth instead of 3 duplicated implementations.

**Acceptance Criteria:**

**Given** Kalshi normalization logic is duplicated in `kalshi.connector.ts`, `kalshi-websocket.client.ts`, and `order-book-normalizer.service.ts`
**When** deduplication is complete
**Then** a shared utility exists in `common/utils/` containing the cents-to-decimal conversion and NO-to-YES price inversion
**And** all three consumers import from the shared utility instead of implementing their own
**And** all existing 498+ tests pass with zero failures
**And** `pnpm lint` reports zero errors
**And** new unit tests cover the shared utility (edge cases: zero price, boundary values 0/100 cents, YES/NO sides)

### 4b. Add story to `sprint-status.yaml`

```yaml
4-5-5-kalshi-normalization-deduplication: backlog
```

Insert after `4-5-4-technical-debt-consolidation: done`, before `epic-4-5-retrospective: optional`.

### 4c. Update `technical-debt.md` item #1 target

Retarget from "Epic 5" to "Story 4.5.5".

## Section 5: Implementation Handoff

**Scope:** Minor — direct implementation by dev agent.

**Handoff:** Scrum Master (SM) applies artifact changes (epics.md, sprint-status.yaml, technical-debt.md), then dev agent implements Story 4.5.5 via the standard create-story → implementation flow.

**Success Criteria:**
- Shared Kalshi normalization utility exists in `common/utils/`
- All 3 consumers refactored to use it
- 498+ tests pass, zero lint errors
- New unit tests for the shared utility
