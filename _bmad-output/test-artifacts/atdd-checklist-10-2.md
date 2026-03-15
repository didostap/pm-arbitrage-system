---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04c-aggregate
  - step-05-validate-and-complete
lastStep: step-05-validate-and-complete
lastSaved: '2026-03-21'
storyId: '10-2'
storyTitle: 'Five-Criteria Model-Driven Exit Logic'
inputDocuments:
  - _bmad-output/implementation-artifacts/10-2-five-criteria-model-driven-exit-logic.md
  - _bmad/tea/testarch/knowledge/data-factories.md
  - _bmad/tea/testarch/knowledge/test-quality.md
  - _bmad/tea/testarch/knowledge/test-levels-framework.md
  - _bmad/tea/testarch/knowledge/test-priorities-matrix.md
  - _bmad/tea/testarch/knowledge/test-healing-patterns.md
  - _bmad/tea/testarch/knowledge/component-tdd.md
  - _bmad/tea/testarch/knowledge/ci-burn-in.md
---

# ATDD Checklist: Story 10.2 — Five-Criteria Model-Driven Exit Logic

## TDD Red Phase (Current)

All tests generated with `it.skip()` / `test.skip()` — will fail until implementation.

| Category | Tests | Status |
|----------|-------|--------|
| Backend Unit (five-criteria-evaluator.spec.ts) | 27 | SKIPPED (RED) |
| Backend Unit (shadow-comparison.service.spec.ts) | 6 | SKIPPED (RED) |
| Backend Integration (exit-monitor-criteria.integration.spec.ts) | 8 | SKIPPED (RED) |
| E2E UI (exit-criteria-display.spec.ts) | 5 | SKIPPED (RED) |
| E2E UI (shadow-comparison.spec.ts) | 5 | SKIPPED (RED) |
| **Total** | **51** | **ALL RED** |

## Priority Distribution

| Priority | Count | Description |
|----------|-------|-------------|
| P0 (Critical) | 14 | Financial math, priority ordering, mode branching, regression, paper/live parity |
| P1 (High) | 23 | Criterion boundary cases, shadow events, data flow verification |
| P2 (Medium) | 14 | Ranking ties, dashboard display, shadow endpoints, detail pages |

## Acceptance Criteria Coverage

### AC1: Five exit criteria evaluation
- [x] C1 Edge evaporation: breakeven, above, below, with entry cost baseline (3 tests)
- [x] C2 Model confidence: drop below/above threshold, null entry, boundary (4 tests)
- [x] C3 Time decay: 168h/18h/0h remaining, null resolutionDate (4 tests)
- [x] C4 Risk budget: rank 1 trigger, rank 2+ no trigger, not approaching, ties, single position (5 tests)
- [x] C5 Liquidity: below/at/above depth, single-side insufficient (3 tests)
- [x] Priority ordering: multi-trigger → highest priority wins (2 tests)
- [x] All 5 criteria always evaluate — 5 CriterionResults returned (included in priority tests)

### AC2: EXIT_MODE config toggle
- [x] fixed → existing logic unchanged (2 regression tests)
- [x] model → evaluateModelDriven() with criteria array (1 test)
- [x] shadow → both evaluations, model primary + shadowFixedResult (1 test)

### AC3: Shadow mode comparison
- [x] ShadowComparisonEvent accumulation (1 test)
- [x] Daily summary: trigger counts + cumulative P&L delta (2 tests)
- [x] Position close: final comparison entry (1 test)
- [x] Day boundary reset (1 test)
- [x] ShadowDailySummaryEvent emission (1 test)

### AC4: Dashboard criteria display
- [x] Exit Mode badge column (1 E2E test)
- [x] Closest criterion + proximity for model mode (1 E2E test)
- [x] Fixed mode shows SL/TP proximity — no regression (1 E2E test)
- [x] 5 criteria with proximity bars on detail page (1 E2E test)
- [x] Traditional threshold display in fixed mode (1 E2E test)

### AC5: Shadow comparison table
- [x] GET /api/dashboard/shadow-comparisons shape (1 E2E test)
- [x] GET /api/dashboard/shadow-summary shape (1 E2E test)
- [x] Performance page shows shadow table (1 E2E test)
- [x] Hidden when no shadow data (1 E2E test)
- [x] Cumulative summary row (1 E2E test)

### AC6: Paper/live boundary
- [x] Criterion evaluation identical regardless of paper/live (1 unit test)
- [x] Exit execution paths remain separated (covered by integration tests)

### AC7: Internal subsystem verification
- [x] Recalculated edge flows from WS/polling into evaluation input (1 integration test)
- [x] Confidence score lookup queries ContractMatch (1 integration test)
- [x] Exit depth from getAvailableExitDepth() (1 integration test)

## Generated Files

### Backend Tests (Vitest — `it.skip()`)
1. `pm-arbitrage-engine/src/modules/exit-management/five-criteria-evaluator.spec.ts` (669 lines, 27 tests)
2. `pm-arbitrage-engine/src/modules/exit-management/shadow-comparison.service.spec.ts` (279 lines, 6 tests)
3. `pm-arbitrage-engine/src/modules/exit-management/exit-monitor-criteria.integration.spec.ts` (579 lines, 8 tests)

### E2E Tests (Playwright — `test.skip()`)
4. `e2e/tests/ui/exit-criteria-display.spec.ts` (156 lines, 5 tests)
5. `e2e/tests/ui/shadow-comparison.spec.ts` (173 lines, 5 tests)

## Next Steps (TDD Green Phase)

After implementing the feature:

1. Remove `it.skip()` / `test.skip()` from test files one-by-one as features are implemented
2. Run backend tests: `cd pm-arbitrage-engine && pnpm test`
3. Run E2E tests: `cd e2e && npx playwright test`
4. Verify tests PASS (green phase)
5. If any test fails:
   - Fix implementation (feature bug) OR
   - Fix test (test bug — update assertions)
6. Run `pnpm lint` and commit passing tests

## Implementation Guidance

### Backend Services to Implement
- `ThresholdEvaluatorService.evaluateModelDriven()` — 5 criterion methods + mode branching in `evaluate()`
- `ShadowComparisonService` — new file, event accumulation + daily summary
- `ExitMonitorService` — edge ranking, risk check, criteria persistence, new input gathering

### Types to Create
- `common/types/exit-criteria.types.ts` — `ExitCriterion`, `CriterionResult`
- Extend `ThresholdEvalInput` + `ThresholdEvalResult` with new fields
- Extend `ExitTriggeredEvent.exitType` union

### Config to Add
- `EXIT_MODE` enum + 8 threshold config keys in env schema

### Dashboard Endpoints to Create
- `GET /api/dashboard/shadow-comparisons`
- `GET /api/dashboard/shadow-summary`
- Extend `OpenPositionDto` with criteria fields

### Dashboard Frontend to Create
- Exit Mode badge column in positions table
- Multi-criterion proximity display
- Position detail criteria section
- Shadow comparison table on performance page

## Execution Metadata

- **Execution mode:** SUBAGENT (API + E2E in parallel)
- **Performance:** ~50% faster than sequential
- **Subagent A (Backend):** 3 files, 41 tests
- **Subagent B (E2E):** 2 files, 10 tests
