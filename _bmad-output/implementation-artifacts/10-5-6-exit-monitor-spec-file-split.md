# Story 10-5.6: Exit-Monitor Spec File Split

Status: done

## Story

As an operator,
I want the 79KB exit-monitor spec file decomposed into focused test files,
so that test maintenance burden is reduced and individual exit concerns can be tested, debugged, and modified independently.

## Context & Motivation

Epic 10 retro flagged `exit-monitor.service.spec.ts` at 69KB as a maintenance burden (Medium debt, Action Item #5). The file has since grown to **79KB (2,343 lines, 66 tests, 17 top-level describe blocks containing 22 total describes including nested)** through Stories 10.1 and 10-5-5. It is the largest spec file in the codebase by a factor of 2.5x. The only lifecycle hook is a single root-level `beforeEach` (lines 102-211) — no `afterEach`, `beforeAll`, or `afterAll` hooks exist.

The file tests ExitMonitorService orchestration — evaluation loop, exit execution, partial fills, pricing, paper mode, data source determination. Individual exit criterion tests (C1-C6) already exist in separate, appropriately-sized spec files:

- `five-criteria-evaluator.spec.ts` (31KB) — per-criterion unit tests
- `threshold-evaluator.service.spec.ts` (31KB) — threshold evaluation logic
- `exit-monitor-criteria.integration.spec.ts` (22KB) — criteria integration
- `shadow-comparison.service.spec.ts` (15KB) — shadow vs fixed comparison

**Note:** The epics.md AC4 prescribed per-criterion split files (C1-C6), but this is inapplicable — those tests are already separate. This story splits by **actual content concerns** in the orchestration spec file. This interpretation was confirmed during story creation.

[Source: `_bmad-output/implementation-artifacts/epic-10-retro-2026-03-22.md` Action Item #5, line 223-226]
[Source: `_bmad-output/planning-artifacts/epics.md` lines 2929-2968]
[Source: `_bmad-output/implementation-artifacts/sprint-status.yaml` line 218]

**Blocks:** Nothing directly. Reduces maintenance burden for all future exit-management stories.

**This is a refactoring story. Zero production code changes.**

## Acceptance Criteria

### AC1 — Shared Test Helpers Extraction

**Given** the current `exit-monitor.service.spec.ts` has a 211-line shared setup block (imports, `createMockPosition` factory, NestJS TestingModule creation, mock wiring)
**When** the split is performed
**Then** a `exit-monitor.test-helpers.ts` file exists co-located in `src/modules/exit-management/`
**And** it exports `createMockPosition()`, a test module factory function, and `setupOrderCreateMock()`
**And** each split spec file imports only the helpers it needs (no monolithic copy-pasted `beforeEach`)

[Source: `_bmad-output/planning-artifacts/epics.md` lines 2949-2952 — AC3 shared setup requirement]

### AC2 — Spec File Decomposition

**Given** the 79KB `exit-monitor.service.spec.ts`
**When** the split is complete
**Then** the original file is replaced by focused spec files, each targeting under 15KB (up to 18KB acceptable for a single cohesive describe block that cannot be further decomposed without losing test cohesion)
**And** file naming follows the pattern `exit-monitor-{concern}.spec.ts`
**And** every top-level describe block from the original file exists in exactly one split file (nested sub-describes stay with their parent)

[Source: `_bmad-output/planning-artifacts/epics.md` lines 2939-2942 — AC1 size + naming; relaxed from strict 15KB per Lad MCP review finding — EXIT_PARTIAL re-evaluation (7.5.1) is a flat describe with 12 `it()` tests at 16KB test content that cannot be split without duplicating the describe wrapper]

### AC3 — Zero Test Coverage Regression

**Given** the decomposed spec files
**When** `pnpm test` is run
**Then** all 66 exit-monitor orchestration tests pass in their new locations
**And** the total test count does not decrease (baseline: 2,631 tests as of 2026-03-23)
**And** no other test files are affected

[Source: `_bmad-output/planning-artifacts/epics.md` lines 2944-2947 — AC2 zero regression]

### AC4 — Original File Removed

**Given** all tests have been moved to split files
**When** the split is validated
**Then** `exit-monitor.service.spec.ts` is deleted
**And** no orphaned imports or references to the deleted file remain

[Derived from: AC2 + AC3 — split replaces original, doesn't duplicate]

## Tasks / Subtasks

### Phase 1: Extract Shared Test Helpers (AC: #1)

- [x] **Task 1: Create `exit-monitor.test-helpers.ts`** (AC: #1)
  - [x] 1.1 Create `src/modules/exit-management/exit-monitor.test-helpers.ts`
  - [x] 1.2 Move `createMockPosition(overrides)` factory function (lines 35-79 of original)
  - [x] 1.3 Create `createExitMonitorTestModule()` factory that encapsulates the NestJS `Test.createTestingModule` setup (lines 102-211) — returns object with `service`, `positionRepository`, `orderRepository`, `kalshiConnector`, `polymarketConnector`, `riskManager`, `eventEmitter`, `thresholdEvaluator`, `prisma`
  - [x] 1.4 Move `setupOrderCreateMock(orderRepository)` helper (lines 92-100)
  - [x] 1.5 Export all factories and necessary type aliases
  - [x] 1.6 Verify the helpers file compiles and exports are consumable

### Phase 2: Create Split Spec Files (AC: #2, #3)

- [x] **Task 2: Create `exit-monitor-core.spec.ts`** (AC: #2, #3) — ~8KB, 11 tests
  - [x] 2.1 Move: evaluatePositions (6 tests, L213-295), happy path exit (1 test, L296-337), partial exit (1 test, L338-416), first leg failure (1 test, L417-443), error isolation (1 test, L444-470), circuit breaker (1 test, L471-494)
  - [x] 2.2 Import from `exit-monitor.test-helpers.ts`; add per-file `vi.mock` for correlation-context
  - [x] 2.3 Verify all 11 tests pass: `pnpm test src/modules/exit-management/exit-monitor-core.spec.ts`

- [x] **Task 3: Create `exit-monitor-pricing.spec.ts`** (AC: #2, #3) — ~8KB, 10 tests
  - [x] 3.1 Move: getClosePrice (3 tests, L495-531), entry close price forwarding 6.5.5i (2 tests, L884-946), VWAP-aware close pricing 6.5.5k (5 tests, L1456-1551)
  - [x] 3.2 Import from helpers; add per-file `vi.mock`
  - [x] 3.3 Verify all 10 tests pass

- [x] **Task 4: Create `exit-monitor-paper-mode.spec.ts`** (AC: #2, #3) — ~12KB, 12 tests
  - [x] 4.1 Move: paper mode support — all 5 sub-describes (12 tests, L532-883)
  - [x] 4.2 Import from helpers; add per-file `vi.mock`
  - [x] 4.3 Verify all 12 tests pass

- [x] **Task 5: Create `exit-monitor-partial-fills.spec.ts`** (AC: #2, #3) — ~12KB, 6 tests
  - [x] 5.1 Move: partial fill handling 6.5.5k (6 tests, L947-1267)
  - [x] 5.2 Import from helpers; add per-file `vi.mock`
  - [x] 5.3 Verify all 6 tests pass

- [x] **Task 6: Create `exit-monitor-depth-check.spec.ts`** (AC: #2, #3) — ~8KB, 4 tests
  - [x] 6.1 Move: pre-exit depth check 6.5.5k (4 tests, L1268-1455)
  - [x] 6.2 Import from helpers; add per-file `vi.mock`
  - [x] 6.3 Verify all 4 tests pass

- [x] **Task 7: Create `exit-monitor-partial-reevaluation.spec.ts`** (AC: #2, #3) — ~18KB, 12 tests
  - [x] 7.1 Move: EXIT_PARTIAL re-evaluation 7.5.1 — all 12 tests (L1552-2093): include EXIT_PARTIAL in evaluation query, residual sizes for threshold, residual sizes for VWAP, close when fully exits, stay EXIT_PARTIAL on partial refill, defer on zero depth, no orders query for OPEN, cap by residual, race condition guard, zero residual close, zero residual one leg skip, asymmetric residual cap
  - [x] 7.2 Import from helpers; add per-file `vi.mock`
  - [x] 7.3 Verify all 12 tests pass
  - Note: This file is ~18KB (over 15KB target) because EXIT_PARTIAL re-evaluation is a single flat describe block with 12 `it()` tests. Splitting would require duplicating the describe wrapper and breaking test cohesion. Accepted per AC2 relaxation.

- [x] **Task 8: Create `exit-monitor-data-source.spec.ts`** (AC: #2, #3) — ~9KB, 11 tests
  - [x] 8.1 Move: data source determination Story 10.1 (4 tests, L2094-2170), recalculated edge computation Story 10.1 (3 tests, L2171-2226), stale fallback event deduplication Story 10.1 (3 tests, L2227-2318), paper mode freshness tracking Story 10.1 (1 test, L2319-end)
  - [x] 8.2 Import from helpers; add per-file `vi.mock`
  - [x] 8.3 Verify all 11 tests pass

### Phase 3: Delete Original & Full Validation (AC: #3, #4)

- [x] **Task 9: Delete original and run full suite** (AC: #3, #4)
  - [x] 9.1 Delete `src/modules/exit-management/exit-monitor.service.spec.ts`
  - [x] 9.2 Run `pnpm test` — verify total test count >= 2,631 and zero failures (excluding environment-dependent e2e)
  - [x] 9.3 Run `pnpm lint` — verify no lint errors
  - [x] 9.4 Verify no other files import from the deleted spec file

## Dev Notes

### Proposed Split Structure

```
src/modules/exit-management/
├── exit-monitor.test-helpers.ts              # NEW — shared factories (~5KB)
├── exit-monitor-core.spec.ts                 # NEW — 11 tests (~8KB)
├── exit-monitor-pricing.spec.ts              # NEW — 10 tests (~8KB)
├── exit-monitor-paper-mode.spec.ts           # NEW — 12 tests (~12KB)
├── exit-monitor-partial-fills.spec.ts        # NEW — 6 tests (~12KB)
├── exit-monitor-depth-check.spec.ts          # NEW — 4 tests (~8KB)
├── exit-monitor-partial-reevaluation.spec.ts # NEW — 12 tests (~18KB, accepted per AC2)
├── exit-monitor-data-source.spec.ts          # NEW — 11 tests (~9KB)
├── exit-monitor.service.spec.ts              # DELETED
├── exit-monitor.service.ts                   # UNCHANGED
├── exit-monitor-criteria.integration.spec.ts # UNCHANGED (22KB)
├── five-criteria-evaluator.spec.ts           # UNCHANGED (31KB)
├── threshold-evaluator.service.spec.ts       # UNCHANGED (31KB)
├── shadow-comparison.service.spec.ts         # UNCHANGED (15KB)
├── threshold-evaluator.service.ts            # UNCHANGED
├── shadow-comparison.service.ts              # UNCHANGED
└── exit-management.module.ts                 # UNCHANGED
```

Total: 7 new spec files + 1 helpers file. 1 file deleted. Net: +7 files.
Test count: 11 + 10 + 12 + 6 + 4 + 12 + 11 = 66 tests (unchanged).

[Source: codebase investigation — `exit-monitor.service.spec.ts` describe blocks, verified 2026-03-23]

### Test Helpers File Design

The helpers file exports three items:

```typescript
// exit-monitor.test-helpers.ts

// 1. Position factory (lines 35-79 of original)
export function createMockPosition(overrides?: Record<string, unknown>): MockPosition { ... }

// 2. Test module factory (encapsulates lines 102-211)
export async function createExitMonitorTestModule(): Promise<ExitMonitorTestContext> { ... }
// Returns: { service, positionRepository, orderRepository, kalshiConnector,
//            polymarketConnector, riskManager, eventEmitter, thresholdEvaluator, prisma }

// 3. Order create mock setup (lines 92-100)
export function setupOrderCreateMock(orderRepository: MockOrderRepository): void { ... }
```

**Each spec file** then has a minimal setup:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  createExitMonitorTestModule,
  createMockPosition,
  type ExitMonitorTestContext,
} from './exit-monitor.test-helpers';

// vi.mock MUST be in each file — Vitest hoists it at the file level, cannot be in helpers
vi.mock('../../common/services/correlation-context', () => ({
  getCorrelationId: () => 'test-correlation-id',
}));

describe('ExitMonitorService — {concern}', () => {
  let ctx: ExitMonitorTestContext;

  beforeEach(async () => {
    ctx = await createExitMonitorTestModule();
  });

  // tests use ctx.service, ctx.positionRepository, etc.
});
```

[Source: `exit-monitor.service.spec.ts` lines 1-211 — setup block structure; Vitest documentation — `vi.mock` hoisting behavior]

### Vitest `vi.mock()` Constraint

`vi.mock()` is hoisted to the top of the **file** by Vitest's transform. It **cannot** be placed in a shared helper file and imported — it must appear directly in each spec file that needs the mock. The `vi.mock('../../common/services/correlation-context', ...)` call must be duplicated in all 7 split spec files.

This is a Vitest design constraint, not a code smell. The duplication is 3 lines per file.

[Source: Vitest documentation — vi.mock is statically analyzed and hoisted per-file]

### EXIT_PARTIAL Re-evaluation Size Exception

The EXIT_PARTIAL re-evaluation block (L1552-2093, ~16KB test content, 12 tests) is a **single flat describe block** — no nested describes. Splitting it across two files would require either duplicating the describe wrapper or renaming blocks, both of which violate the "no rename" constraint and reduce test cohesion. The resulting file (~18KB with helpers overhead) exceeds the 15KB target by ~3KB but is accepted as the only file over the limit.

If the dev agent finds a natural sub-grouping within the 12 tests that warrants nested describes (e.g., "residual sizing" vs "edge case guards"), they may introduce nested describes within the single file for readability — but this is optional and not required.

[Source: codebase investigation — EXIT_PARTIAL describe block L1552-2093, verified as flat (no nested describes); Lad MCP review finding #1]

### Import Path Adjustments

When tests move to new files, relative import paths remain identical — all split files are co-located in the same `src/modules/exit-management/` directory as the original. No path changes needed for imports of production code, mock factories, or branded types.

[Source: `exit-monitor.service.spec.ts` lines 1-29 — all imports are relative to the same directory level]

### Existing Spec Files — NOT in Scope

These exit-management spec files are already appropriately sized and must NOT be modified:

| File                                        | Size | Tests                |
| ------------------------------------------- | ---- | -------------------- |
| `five-criteria-evaluator.spec.ts`           | 31KB | C1-C6 unit tests     |
| `threshold-evaluator.service.spec.ts`       | 31KB | Threshold evaluation |
| `exit-monitor-criteria.integration.spec.ts` | 22KB | Criteria integration |
| `shadow-comparison.service.spec.ts`         | 15KB | Shadow comparison    |

[Source: `find_file *.spec.ts` in exit-management directory, verified sizes 2026-03-23]

### What NOT to Do

- Do NOT change any production code (`exit-monitor.service.ts`, `threshold-evaluator.service.ts`, `shadow-comparison.service.ts`, `exit-management.module.ts`) — this is spec-only refactoring
- Do NOT modify the 4 existing exit-management spec files listed above — they are not in scope
- Do NOT change test logic, assertions, or mock behavior — only move tests between files and extract shared setup
- Do NOT rename describe blocks or test names — they must remain identical for traceability
- Do NOT add new tests — this is a pure reorganization story
- Do NOT create a `__tests__/` subdirectory — follow the co-located spec pattern used throughout the codebase
- Do NOT use `vi.doMock()` or dynamic mocking to work around the `vi.mock` hoisting constraint — just duplicate the 3-line mock in each file
- Do NOT modify `mock-factories.ts` or any shared test infrastructure outside exit-management

[Source: `_bmad-output/planning-artifacts/epics.md` lines 2966-2968 — "no production code changes"]

### Verification Checklist

1. `pnpm test src/modules/exit-management/` — all exit-management tests pass
2. `pnpm test` — full suite passes, total count >= 2,631
3. `pnpm lint` — no lint errors
4. Each new spec file under 15KB (except `exit-monitor-partial-reevaluation.spec.ts` at ~18KB — accepted): `ls -la src/modules/exit-management/exit-monitor-*.spec.ts`
5. Original file deleted: `ls src/modules/exit-management/exit-monitor.service.spec.ts` returns "not found"
6. Test count preserved: sum of `grep -c '^\s*it(' src/modules/exit-management/exit-monitor-*.spec.ts` equals 66

### Test Baseline (verified 2026-03-23)

```
Test Files: 147 passed (147)
Tests: 2,631 passed | 2 todo (2,633)
Exit-management tests: 66 in exit-monitor.service.spec.ts
```

[Source: `pnpm test` run 2026-03-23, full pass]

### Lad MCP Review Notes

Primary reviewer (kimi-k2.5) identified 6 findings. Secondary reviewer (glm-5-turbo) failed due to OpenRouter error.

**Incorporated:**

- Finding #1 (Critical): EXIT_PARTIAL splitting contradiction — merged Tasks 7/8 into single file, relaxed AC2 to allow up to 18KB for cohesive flat describe blocks
- Finding #2 (Medium): Describe block count clarified — "17 top-level describe blocks containing 22 total describes including nested"
- Finding #3 (Medium): Lifecycle hook inventory — verified: only root-level `beforeEach` exists, no `afterEach`/`beforeAll`/`afterAll`
- Finding #4 (Low): Verification command updated to `ls -la` for human-readable sizes

**Accepted as-is:**

- Finding #5 (Low): Prisma mock completeness — the helpers factory will return the exact same mock structure from the original `beforeEach`; the dev agent will handle any per-test additions
- Finding #6 (Low): Import path assumption — statement is correct for production code imports; `../../test/mock-factories.js` path is the same from all co-located files

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` lines 2929-2968] — Story definition, ACs
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-22-retro-stories.md` lines 179-218] — Story origin, parallelization notes
- [Source: `_bmad-output/implementation-artifacts/epic-10-retro-2026-03-22.md` lines 160, 223-226] — Debt item, Action Item #5
- [Source: `_bmad-output/implementation-artifacts/sprint-status.yaml` line 218] — Story status
- [Source: `src/modules/exit-management/exit-monitor.service.spec.ts`] — Source file (79KB, 2,343 lines, 66 tests, 17 describe blocks)
- [Source: `src/modules/exit-management/exit-monitor.service.ts`] — Production service (unchanged, 10 methods)
- [Source: `src/test/mock-factories.ts`] — Shared mock factories (`createMockPlatformConnector`, `createMockRiskManager`) — imported by helpers
- [Source: `_bmad-output/implementation-artifacts/10-5-5-paper-live-mode-boundary-inventory-test-suite.md`] — Prior story format reference

## Dev Agent Record

### Implementation Plan

Pure spec-file reorganization. Created shared test helpers file with `createMockPosition()`, `createExitMonitorTestModule()`, `setupOrderCreateMock()`, and `ExitMonitorTestContext` interface. Each split spec file uses destructuring assignment from the helpers factory to maintain identical variable names — zero test logic changes.

### Completion Notes

- Created 1 helpers file + 7 spec files, deleted 1 original file (net +7)
- All 66 exit-monitor orchestration tests pass in their new locations
- Full suite: 153 test files, 2,631 tests passed (baseline preserved exactly)
- Lint: 0 errors, 53 warnings (all pre-existing)
- File sizes: all under 15KB except `exit-monitor-partial-reevaluation.spec.ts` at 18KB (accepted per AC2)
- `vi.mock('../../common/services/correlation-context', ...)` duplicated in all 7 spec files per Vitest hoisting constraint
- `setupOrderCreateMock()` changed from closure-captured to parameter-passing pattern (`setupOrderCreateMock(orderRepository)`)
- No production code changed

### Debug Log

- ESLint caught unused `eventEmitter` variable in `exit-monitor-partial-reevaluation.spec.ts` — removed from destructuring
- Linter auto-fixed import ordering in `exit-monitor-depth-check.spec.ts` and `exit-monitor-paper-mode.spec.ts`

## File List

### New Files
- `src/modules/exit-management/exit-monitor.test-helpers.ts` — shared test factories (7KB)
- `src/modules/exit-management/exit-monitor-core.spec.ts` — 11 tests (11KB)
- `src/modules/exit-management/exit-monitor-pricing.spec.ts` — 10 tests (8KB)
- `src/modules/exit-management/exit-monitor-paper-mode.spec.ts` — 12 tests (12KB)
- `src/modules/exit-management/exit-monitor-partial-fills.spec.ts` — 6 tests (12KB)
- `src/modules/exit-management/exit-monitor-depth-check.spec.ts` — 4 tests (8KB)
- `src/modules/exit-management/exit-monitor-partial-reevaluation.spec.ts` — 12 tests (18KB)
- `src/modules/exit-management/exit-monitor-data-source.spec.ts` — 11 tests (11KB)

### Deleted Files
- `src/modules/exit-management/exit-monitor.service.spec.ts` — original 79KB monolith (66 tests)

## Change Log

- 2026-03-23: Story 10-5.6 implemented — split 79KB exit-monitor.service.spec.ts into 7 focused spec files + 1 shared helpers file. 66 tests preserved, 0 regressions.
- 2026-03-23: Code review completed — 3-layer adversarial (Blind Hunter + Edge Case Hunter + Acceptance Auditor). 18 raw findings triaged: 0 patch, 10 defer (all pre-existing), 8 reject (noise/by-design). All ACs pass. Clean split confirmed.
