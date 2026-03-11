# Story 9.17: Stale APR Display Fix — Atomic Edge/APR Updates on Filtered Events

Status: done

## Story

As an **operator**,
I want **stale annualized return values to be cleared when an opportunity is filtered without a freshly computed APR**,
so that **the dashboard never shows a contradictory state like 28% APR alongside a -0.14% net edge**.

## Acceptance Criteria

1. **Negative net edge clears APR**: When `lastNetEdge` is written with a negative value from a filtered event that has no computed `annualizedReturn`, `lastAnnualizedReturn` is set to `null` in the `contract_matches` row. [Source: sprint-change-proposal-2026-03-14.md#Story-C AC1; edge-calculator.service.ts:217-227 emission site — `negative_edge` reason, no `annualizedReturn` in opts]

2. **Below-threshold positive edge clears APR**: When net edge is positive but below threshold (filtered before capital efficiency gate), `lastAnnualizedReturn` is set to `null`. [Source: sprint-change-proposal-2026-03-14.md#Story-C AC2; edge-calculator.service.ts:217-227 emission site — `below_threshold` reason, no `annualizedReturn` in opts]

3. **Below-threshold APR preserves computed value**: When APR is computed but falls below the minimum threshold, `lastAnnualizedReturn` is updated to the computed value (not null). [Source: sprint-change-proposal-2026-03-14.md#Story-C AC3; edge-calculator.service.ts:385-396 emission site — `annualized_return_below_threshold` reason, passes `annualizedReturn: annualizedReturn.toNumber()`]

4. **All `OpportunityFilteredEvent` emission sites audited**: Four emission sites exist in `edge-calculator.service.ts`. Three pass no `annualizedReturn` (negative edge, below threshold, no resolution date, resolution date passed). One passes a computed value (annualized return below threshold). This audit is documented in dev notes. [Source: sprint-change-proposal-2026-03-14.md#Story-C AC4; codebase investigation confirmed 4 sites]

5. **Dashboard shows "—" for null APR**: Matches table `AprCell` and match detail page Capital Efficiency section render "—" when `lastAnnualizedReturn` is null. No NaN or undefined rendering. [Source: sprint-change-proposal-2026-03-14.md#Story-C AC5; codebase investigation — already implemented correctly in MatchesPage.tsx:19-24 and MatchDetailPage.tsx:252-259]

6. **No stale APR/net-edge contradiction possible**: After fix, any filtered event without a freshly computed APR nulls out the stale value, making contradictory states (positive APR + negative edge) impossible. [Source: sprint-change-proposal-2026-03-14.md#Story-C AC6]

7. **All existing tests pass + new coverage**: `pnpm test` passes (baseline: 2065 passed, 2 todo). Existing tests that assert "preserve null annualizedReturn" behavior are updated to assert null-out behavior. New tests cover the null-out paths. `pnpm lint` clean. [Source: sprint-change-proposal-2026-03-14.md#Story-C AC7; baseline verified 2026-03-14]

## Tasks / Subtasks

**Execution order: 1 → 2 → 3**

- [x] **Task 1: Fix `handleOpportunityFiltered` to null out stale APR** (AC: #1, #2, #3, #6)
  - [x] 1.1 In `src/modules/monitoring/match-apr-updater.service.ts`, method `handleOpportunityFiltered()` (line 73-76): replace the conditional-only write with an unconditional write that sets `lastAnnualizedReturn` to either the computed value or `null`:
    ```typescript
    // Before (buggy — preserves stale APR):
    if (event.annualizedReturn != null) {
      data['lastAnnualizedReturn'] = String(event.annualizedReturn);
    }

    // After (always update — null clears stale value):
    data['lastAnnualizedReturn'] = event.annualizedReturn != null
      ? String(event.annualizedReturn)
      : null;
    ```
    Remove the comment "Only set annualizedReturn if non-null — preserve previously-persisted value" — it describes the old (incorrect) behavior.
  - [x] 1.2 **Defensive fix** in `handleOpportunityIdentified()` (line 38-40): apply the same pattern. Identified events should always carry APR (passed capital efficiency gate), but null-out defensively rather than silently preserving stale data:
    ```typescript
    // Before:
    if (annualizedReturn != null) {
      data['lastAnnualizedReturn'] = String(annualizedReturn);
    }

    // After:
    data['lastAnnualizedReturn'] = annualizedReturn != null
      ? String(annualizedReturn)
      : null;
    ```

- [x] **Task 2: Update tests** (AC: #7)
  - [x] 2.1 In `src/modules/monitoring/match-apr-updater.service.spec.ts`, update the **identified event** test `'should handle null annualizedReturn (only set netEdge and timestamp)'` (~line 108):
    - Change `expect(data).not.toHaveProperty('lastAnnualizedReturn')` → `expect(data?.['lastAnnualizedReturn']).toBeNull()`
    - This test covers the defensive fix from Task 1.2
  - [x] 2.2 Update the **filtered event** test `'should preserve null annualizedReturn (not overwrite DB value)'` (~line 247):
    - Rename test description to `'should null out lastAnnualizedReturn when event has no computed APR'`
    - Change `expect(data).not.toHaveProperty('lastAnnualizedReturn')` → `expect(data?.['lastAnnualizedReturn']).toBeNull()`
    - This test covers the primary fix from Task 1.1
  - [x] 2.3 Existing test `'should set annualizedReturn when provided (APR-threshold-filtered)'` (~line 184) — verify it still passes unchanged. This test already covers AC #3 (computed APR below threshold gets written).
  - [x] 2.4 Add a new test: **`'should null out APR on negative_edge filtered event'`** — emit `OpportunityFilteredEvent` with reason containing `negative_edge`, `annualizedReturn: null`, verify `lastAnnualizedReturn` is set to `null` in the Prisma update call. (AC: #1)
  - [x] 2.5 Add a new test: **`'should null out APR on no_resolution_date filtered event'`** — emit `OpportunityFilteredEvent` with reason `no_resolution_date`, `annualizedReturn: null`, verify `lastAnnualizedReturn` is set to `null`. (AC: #6 — no stale APR invariant)
  - [x] 2.6 Add a new test: **`'should null out APR on resolution_date_passed filtered event'`** — same pattern, reason `resolution_date_passed`. Covers the 4th emission site (edge-calculator.service.ts:346-356). (AC: #6)

- [x] **Task 3: Verify dashboard + final validation** (AC: #5, #7)
  - [x] 3.1 **Dashboard verification** (AC #5): Visually confirm in `MatchesPage.tsx:19-24` (`AprCell`) and `MatchDetailPage.tsx:252-259` that null `lastAnnualizedReturn` renders "—". No code change expected — already correct.
  - [x] 3.2 Run `pnpm test` — all tests pass
  - [x] 3.3 Run `pnpm lint` — clean
  - [x] 3.4 Run `pnpm build` — no type errors

## Dev Notes

### Root Cause Analysis

The `MatchAprUpdaterService` subscribes to both `OPPORTUNITY_IDENTIFIED` and `OPPORTUNITY_FILTERED` events to persist APR/edge data on `contract_matches` rows. The `handleOpportunityFiltered()` handler at line 73-76 conditionally writes `lastAnnualizedReturn` only when `event.annualizedReturn != null`. When the event carries no computed APR (3 of 4 emission paths), the stale value from a previous detection cycle persists. This creates contradictory display: e.g., `lastNetEdge = -0.0014` (freshly written) alongside `lastAnnualizedReturn = 0.281` (stale from a prior positive cycle). [Source: match-apr-updater.service.ts:73-76; observed on contract_matches row `6beafb32`]

### `OpportunityFilteredEvent` Emission Site Audit

All 4 sites are in `edge-calculator.service.ts` method `enrichDislocation()` + `checkCapitalEfficiency()`:

| Line | Reason | `annualizedReturn` in opts | Behavior after fix |
|------|--------|---------------------------|-------------------|
| 217-227 | `negative_edge` / `below_threshold` | Not passed (null) | Nulls out stale APR |
| 309-319 | `no_resolution_date` | Not passed (null) | Nulls out stale APR |
| 346-356 | `resolution_date_passed` | Not passed (null) | Nulls out stale APR |
| 385-396 | `annualized_return_below_threshold` | Passed (computed value) | Writes computed APR |

[Source: edge-calculator.service.ts:196-230 (edge filter), edge-calculator.service.ts:285-402 (checkCapitalEfficiency)]

### Key Invariant

After this fix, every `handleOpportunityFiltered` call writes `lastAnnualizedReturn` — either to the freshly computed value or to `null`. Combined with `lastNetEdge` always being written (line 69-71), the two fields are always atomically consistent: you can never have a stale APR from cycle N alongside a fresh net edge from cycle N+1.

### Event Ordering (No Race Condition)

Within a single detection cycle, each pair emits either `OPPORTUNITY_IDENTIFIED` or `OPPORTUNITY_FILTERED` — never both. EventEmitter2 async handlers run sequentially per event. Therefore, for any given `matchId`, APR writes cannot interleave between identified and filtered handlers. No sequence validation needed.

### Scope Boundaries

- **Backend only**: The fix is in `match-apr-updater.service.ts`. No schema changes, no migration, no new events, no interface changes.
- **Dashboard already correct**: `AprCell` (MatchesPage.tsx:19-24) and Capital Efficiency section (MatchDetailPage.tsx:252-259) already render "—" for null. Verification only — no code change.
- **No `OpportunityFilteredEvent` class changes**: The event class already supports `annualizedReturn: number | null`. No structural changes needed.

### Project Structure Notes

- **Modified files** (2):
  - `src/modules/monitoring/match-apr-updater.service.ts` — null-out logic in both handlers [Source: AC #1, #2, #3, #6]
  - `src/modules/monitoring/match-apr-updater.service.spec.ts` — update 2 existing tests + add 2 new tests [Source: AC #7]
- **Verified files** (no changes expected):
  - `pm-arbitrage-dashboard/src/pages/MatchesPage.tsx:19-24` — `AprCell` already handles null [Source: AC #5]
  - `pm-arbitrage-dashboard/src/pages/MatchDetailPage.tsx:252-259` — detail view already handles null [Source: AC #5]
  - `pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.ts` — emission sites are correct, no changes needed [Source: AC #4]
  - `pm-arbitrage-engine/src/common/events/detection.events.ts` — `OpportunityFilteredEvent` class unchanged [Source: AC #4]
- **No new files**

### References

- [Source: sprint-change-proposal-2026-03-14.md#Story-C] — Primary requirements and acceptance criteria
- [Source: CLAUDE.md] — Post-edit workflow, naming conventions
- [Source: match-apr-updater.service.ts:57-89] — `handleOpportunityFiltered()` — the buggy handler
- [Source: match-apr-updater.service.ts:15-54] — `handleOpportunityIdentified()` — defensive fix target
- [Source: match-apr-updater.service.spec.ts:108-129] — identified handler null APR test (needs update)
- [Source: match-apr-updater.service.spec.ts:247-266] — filtered handler null APR test (needs update)
- [Source: match-apr-updater.service.spec.ts:184-203] — filtered handler with computed APR test (unchanged)
- [Source: edge-calculator.service.ts:196-230] — edge filter emission site (negative_edge / below_threshold)
- [Source: edge-calculator.service.ts:285-402] — `checkCapitalEfficiency()` — 3 emission sites (no_resolution_date, resolution_date_passed, annualized_return_below_threshold)
- [Source: MatchesPage.tsx:19-24] — `AprCell` null rendering (already correct)
- [Source: MatchDetailPage.tsx:252-259] — detail page null rendering (already correct)
- [Source: Story 9-9 (match-apr-visibility)] — Original implementation of APR persistence via event subscribers
- [Source: Serena memory: codebase_structure] — File locations verified

### Previous Story Intelligence

**From Story 9-16** (risk-state-paper-trade-reconciliation):
- Code review #2 found sell-side formula consistency gaps across multiple services — pattern: always audit all callers/write-sites when fixing a data consistency issue. Applied here: audited all 4 emission sites + both handler methods.
- Test count baseline: 2065 passed, 2 todo.

**From Story 9-9** (match-apr-visibility):
- Story 9-9 introduced the `MatchAprUpdaterService` and the `lastAnnualizedReturn`/`lastNetEdge`/`lastComputedAt` columns on `ContractMatch`. The "preserve if null" pattern was an intentional design choice at the time — but it causes data staleness when the edge flips negative.
- The `OpportunityFilteredEvent` was extended with optional `annualizedReturn` field specifically for the APR-threshold-filtered case.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no blockers.

### Completion Notes List

- **Implementation**: Both `handleOpportunityIdentified()` and `handleOpportunityFiltered()` now unconditionally write both `lastAnnualizedReturn` and `lastNetEdge` — either the computed value or `null`. Removed stale-preserving comment from filtered handler.
- **Tests**: 2 existing tests updated to assert `toBeNull()` instead of `not.toHaveProperty()`. 4 new tests added covering `negative_edge`, `no_resolution_date`, `resolution_date_passed` filter reasons, and `lastNetEdge` null behavior. Also updated the `below_threshold` test assertion in the first filtered event test. Total: 14 tests in spec (was 10).
- **Test count**: 2069 passed, 2 todo (baseline: 2065 passed, 2 todo). +4 net new tests.
- **Dashboard verification**: `AprCell` (MatchesPage.tsx:19-20) and Capital Efficiency section (MatchDetailPage.tsx:259) already render "—" for null. No code change needed.
- **Lint**: clean. **Build**: clean. No type errors.
- **Code review** (Lad MCP): Secondary reviewer confirmed fix is correct. Primary reviewer timed out (infra). Post-review fixes applied:
  - Made `lastNetEdge` unconditional (same pattern as APR fix) — reviewer finding #1
  - Added `MatchAprFields` interface for type-safe property access — reviewer finding #2
  - Added `lastNetEdge` null behavior test — reviewer finding #4
  - Added JSDoc emission site audit comment on class — reviewer finding #5
  - Standardized `String()` vs `.toString()` usage — reviewer observation #1
  - Skipped input validation (finding #3) — producer validates, negative APR is legitimate
- **No deviations** from Dev Notes guidance.
- **Code review #2** (adversarial): Fixed 2 MEDIUM issues, noted 3 LOW (documentation-only):
  - M1: De-duplicated test — changed line 330 from `no_resolution_date` to `below_threshold` reason (was identical to line 290)
  - M2: Standardized string conversion — changed `event.netEdge.toString()` to `String(event.netEdge)` in filtered handler for consistency with identified handler
  - L1 (noted): First filtered event test (line 183) assertion update not tracked in Tasks — only in completion notes
  - L2 (noted): `MatchAprFields.enrichedAt` null type is defensive dead code
  - L3 (noted): Completion notes say "2 existing tests updated" but 3 were changed

### File List

- `src/modules/monitoring/match-apr-updater.service.ts` — unconditional writes for both fields, `MatchAprFields` interface, emission site audit JSDoc
- `src/modules/monitoring/match-apr-updater.service.spec.ts` — 2 tests updated, 4 tests added (net +4 tests)
