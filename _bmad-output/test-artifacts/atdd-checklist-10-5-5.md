---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-23'
inputDocuments:
  - '_bmad-output/implementation-artifacts/10-5-5-paper-live-mode-boundary-inventory-test-suite.md'
  - '_bmad/tea/config.yaml'
  - 'pm-arbitrage-engine/vitest.config.ts'
  - 'pm-arbitrage-engine/src/common/testing/expect-event-handled.ts'
  - 'pm-arbitrage-engine/src/common/testing/index.ts'
  - '_bmad/tea/testarch/knowledge/data-factories.md'
  - '_bmad/tea/testarch/knowledge/test-quality.md'
  - '_bmad/tea/testarch/knowledge/test-healing-patterns.md'
  - '_bmad/tea/testarch/knowledge/test-levels-framework.md'
  - '_bmad/tea/testarch/knowledge/test-priorities-matrix.md'
  - '_bmad/tea/testarch/knowledge/component-tdd.md'
---

# ATDD Checklist — Story 10-5.5: Paper/Live Mode Boundary Inventory & Test Suite

## Step 1: Preflight & Context

### Stack Detection
- Config: `test_stack_type: fullstack`
- Story scope: Backend-only (Vitest unit/integration tests)
- Detected stack for this story: `backend`

### Prerequisites
- [x] Story approved with clear ACs (5 ACs)
- [x] Test framework configured (Vitest + unplugin-swc)
- [x] Dev environment available

### Story Summary
Story 10-5.5 addresses paper/live mode contamination (22% recurrence in Epic 10). Goal: inventory all 20 isPaper/is_paper boundary points, close 8 test coverage gaps, add structural guards (withModeFilter + required isPaper params), and document conventions.

### Acceptance Criteria
1. **AC1 — Branch Inventory Document**: List every mode-divergent location, categorize coverage
2. **AC2 — Integration Test Suite**: Per-module spec files in `src/common/testing/paper-live-boundary/`
3. **AC3 — Repository Mode-Scoping**: `withModeFilter` helper + required `isPaper` parameters
4. **AC4 — Raw SQL Audit**: All raw SQL includes `is_paper` filtering + `-- MODE-FILTERED` markers
5. **AC5 — Convention Documentation**: CLAUDE.md updates + story creation checklist

### Affected Modules
risk-management, execution, exit-management, reconciliation, monitoring, connectors, dashboard, persistence

### Existing Test Patterns
- `src/common/testing/` directory convention from Story 10-5-4
- `expectEventHandled` helper pattern (3 exports)
- `event-wiring-audit.spec.ts` (731 lines), `collection-lifecycle-audit.spec.ts` (331 lines)
- Barrel `index.ts` for re-exports

### Coverage Gap Summary (8 gaps to close)
1. FillSimulator: no test verifying it CANNOT produce partial/rejected
2. RiskManager halt/resume: no test verifying paperState is not affected
3. ExitMonitor: missing negative test (live positions NOT evaluated in paper mode)
4. EventConsumer: no config/connector mismatch test
5. Dashboard: mode filter integration test needed
6. Reconciliation controller: no test for isPaper=false hardcode
7. Repository defaults: dangerous `= false` defaults to remove
8. Raw SQL audit coverage

### Knowledge Fragments Applied
- Test Levels: Unit for isolated logic, integration for service/DB
- Priorities: P0 for paper/live contamination (compliance-critical)
- TDD: Red-green-refactor cycle
- Quality: Deterministic, isolated, explicit, <300 lines
- Data Factories: Factory functions with overrides

## Step 2: Generation Mode

**Mode:** AI Generation
**Reason:** Backend-only story (Vitest unit/integration tests). All 5 ACs are well-specified with 20 concrete boundary points documented. No browser recording needed.

## Step 3: Test Strategy

### Test Levels
- **Unit**: withModeFilter helper, FillSimulator status constraint, RiskManager halt/resume isolation, mode immutability
- **Integration**: Dashboard mode filtering, reconciliation endpoint hardcode, EventConsumer config/connector mismatch, ExitMonitor negative test
- **Compilation**: Required isPaper params (removal of `= false` defaults) — compiler is the test

### Priority Assignment
- **P0**: risk.spec.ts (7), connectors.spec.ts (3), exit.spec.ts (3), mode-filter.helper.spec.ts (3) = 16 tests
- **P1**: execution.spec.ts (3), reconciliation.spec.ts (2), dashboard.spec.ts (3), monitoring.spec.ts (2), exit.spec.ts (1) = 11 tests

## Step 4: ATDD Test Generation (RED PHASE)

### TDD Red Phase Validation
- [x] All tests use `it.skip()` — TDD red phase compliant
- [x] All tests assert expected behavior (not placeholders)
- [x] All tests marked as `expected_to_fail`
- [x] No `expect(true).toBe(true)` placeholder assertions

### Execution Mode
- Requested: auto → Resolved: subagent
- Worker A (P0): 4 files, 17 tests (16 P0 + 1 P1)
- Worker B (P1): 4 files, 10 tests (all P1)
- E2E: Skipped (backend-only story)

### Generated Files (8 spec files + 1 barrel)

| File | Lines | Tests | Priority | Coverage Gap |
|---|---|---|---|---|
| `risk.spec.ts` | 248 | 7 | P0 | halt/resume isolation, bankroll/PnL isolation |
| `connectors.spec.ts` | 167 | 3 | P0 | FillSimulator status constraint, mode immutability |
| `exit.spec.ts` | 221 | 4 | P0+P1 | Negative mode test, isPaper flag propagation |
| `mode-filter.helper.spec.ts` | 65 | 3 | P0 | TRUE RED — helper doesn't exist yet |
| `execution.spec.ts` | 223 | 3 | P1 | Flag propagation, live halt isolation |
| `reconciliation.spec.ts` | 190 | 2 | P1 | Dual-mode recalculation, isPaper=false hardcode |
| `dashboard.spec.ts` | 197 | 3 | P1 | Mode-filtered getPositions, getOverview capital |
| `monitoring.spec.ts` | 175 | 2 | P1 | Telegram dedup isolation, config/connector mismatch |
| `index.ts` (barrel) | 19 | — | — | Documentation and module discovery |

### Summary Statistics
- **Total tests**: 27 (all with `it.skip()`)
- **P0 tests**: 16
- **P1 tests**: 11
- **Total lines**: 1,505
- **All files under 300 lines**: Yes
- **TDD phase**: RED

### Acceptance Criteria Coverage
- [x] AC2 — 7 per-module spec files created in `src/common/testing/paper-live-boundary/`
- [x] AC3 — `mode-filter.helper.spec.ts` covers `withModeFilter()` contract (true red phase)
- [ ] AC1 — Branch inventory document (implementation task, not test)
- [ ] AC4 — Raw SQL audit (implementation task, not test)
- [ ] AC5 — Convention documentation (implementation task, not test)

### Next Steps (TDD Green Phase)
1. Implement `withModeFilter()` helper → remove `it.skip()` from `mode-filter.helper.spec.ts`
2. Remove `= false` defaults from repository methods → fix compilation errors
3. Remove `it.skip()` from per-module tests one at a time
4. Run `pnpm test` → verify all pass (green phase)
5. Complete AC1 (inventory doc), AC4 (raw SQL audit), AC5 (CLAUDE.md updates)

## Step 5: Validation & Completion

### Validation Checklist
- [x] All 8 spec files exist on disk (verified)
- [x] All tests use `it.skip()` — 29 literal occurrences across 8 files
- [x] No placeholder assertions found
- [x] All files under 300 lines
- [x] Barrel `index.ts` created
- [x] No orphaned browser sessions (N/A — backend-only)
- [x] ATDD checklist saved to `_bmad-output/test-artifacts/atdd-checklist-10-5-5.md`

### Key Risks & Assumptions
1. **Import paths**: Test imports reference actual module paths — some may need adjustment when the dev agent runs the tests for the first time (constructor signatures, DI tokens)
2. **Mock completeness**: Mocks are based on source code reading but may need additional providers for NestJS DI to resolve correctly
3. **`mode-filter.helper.spec.ts`**: True red phase — import will fail until the helper is implemented
4. **`describe.each` dual-mode matrix**: Exit, execution, and dashboard specs use `describe.each` for paper/live dual-mode testing — runtime test count exceeds literal `it.skip` count

### Recommended Next Workflow
Use `/bmad-dev-skill` with story file `_bmad-output/implementation-artifacts/10-5-5-paper-live-mode-boundary-inventory-test-suite.md` to implement the story. The dev agent should:
1. Start with `mode-filter.helper.ts` (true red → green)
2. Remove `= false` defaults (compiler-driven migration)
3. Un-skip tests one module at a time, fixing any mock/import issues
4. Complete non-test ACs (inventory doc, raw SQL audit, CLAUDE.md updates)
