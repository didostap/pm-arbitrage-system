---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04-generate-tests
  - step-04c-aggregate
  - step-05-validate-and-complete
lastStep: step-05-validate-and-complete
lastSaved: '2026-03-23'
inputDocuments:
  - _bmad-output/implementation-artifacts/10-7-1-pre-trade-dual-leg-liquidity-gate.md
  - _bmad/tea/testarch/knowledge/data-factories.md
  - _bmad/tea/testarch/knowledge/test-quality.md
  - _bmad/tea/testarch/knowledge/test-levels-framework.md
  - _bmad/tea/testarch/knowledge/test-priorities-matrix.md
  - _bmad/tea/testarch/knowledge/test-healing-patterns.md
  - _bmad/tea/testarch/knowledge/component-tdd.md
---

# ATDD Checklist: Story 10-7-1 — Pre-Trade Dual-Leg Liquidity Gate

## TDD Red Phase (Current)

All 18 failing tests generated with `it.skip()`.

| Test File | Test Count | Status |
|---|---|---|
| `src/modules/execution/dual-leg-depth-gate.spec.ts` | 16 | Skipped (RED) |
| `src/common/testing/paper-live-boundary/execution.spec.ts` | 2 (appended) | Skipped (RED) |
| **Total** | **18** | **All skipped** |

## Acceptance Criteria Coverage

### AC-1: Dual-leg depth verification before order submission (P0)
- [x] 1.1 Both legs sufficient → proceed to order submission
- [x] 1.2 Primary leg insufficient → reject with OPPORTUNITY_FILTERED
- [x] 1.3 Secondary leg insufficient → reject with OPPORTUNITY_FILTERED
- [x] 1.4 Both legs insufficient → reject with OPPORTUNITY_FILTERED
- [x] 1.5 Event payload contains per-platform depth details

### AC-2: Asymmetric depth capping (P0)
- [x] 2.1 Asymmetric depth → size capped to min(primary, secondary) (degenerate case documented)
- [x] 2.1b Asymmetric depth with sufficient min → proceeds at capped size
- [x] 2.2 Capped size below minFillRatio → reject with INSUFFICIENT_LIQUIDITY
- [x] 2.3 Capped size exactly at boundary → proceed (edge case, P1)

### AC-3: Fail-closed on API error (P0)
- [x] 3.1 Primary API call fails → fail-closed reject
- [x] 3.2 Secondary API call fails → fail-closed reject
- [x] 3.3 DEPTH_CHECK_FAILED event emitted with error context

### AC-4: Configurable DUAL_LEG_MIN_DEPTH_RATIO (P1)
- [x] 4.1 Default 1.0 from config
- [x] 4.2 Custom ratio 0.5 → 50% depth required
- [x] 4.3 reloadConfig updates at runtime

### Cross-cutting
- [x] 5.1/5.2 Paper/live boundary: dual-leg gate runs in both modes (describe.each matrix)
- [x] 6.1 Event wiring: OPPORTUNITY_FILTERED with new reason compatible with MatchAprUpdaterService

## Priority Distribution

| Priority | Count | Percentage |
|---|---|---|
| P0 | 13 | 72% |
| P1 | 5 | 28% |
| **Total** | **18** | 100% |

## Test Levels

| Level | Count | Location |
|---|---|---|
| Unit | 16 | `src/modules/execution/dual-leg-depth-gate.spec.ts` |
| Boundary | 2 | `src/common/testing/paper-live-boundary/execution.spec.ts` |
| E2E | 0 | N/A (backend-only story) |

## Fixture Needs

No new fixtures required. Tests reuse existing factory pattern:
- `makePairConfig()`, `makeEnriched()`, `makeOpportunity()`, `makeReservation()`
- `makeKalshiOrderBook()`, `makePolymarketOrderBook()`, `makeFilledOrder()`
- `createConfigService()`, `createMockPlatformConnector()`

## Next Steps (TDD Green Phase)

After implementing the feature (Tasks 1-3 from story):

1. Remove `it.skip()` from all 16 tests in `dual-leg-depth-gate.spec.ts`
2. Remove `it.skip()` from 2 boundary tests in `execution.spec.ts`
3. Run tests: `pnpm test`
4. Verify all 18 tests PASS (green phase)
5. If any fail:
   - Feature bug → fix implementation
   - Test bug → fix test (adjust mock data / assertions)
6. Run `pnpm lint`
7. Commit passing tests with implementation

## Implementation Guidance

### Files to Create/Modify (from story)

| File | Change |
|---|---|
| `src/common/config/env.schema.ts` | Add `DUAL_LEG_MIN_DEPTH_RATIO` |
| `src/common/config/config-defaults.ts` | Add `dualLegMinDepthRatio` entry |
| `src/common/config/settings-metadata.ts` | Add metadata under Execution group |
| `src/dashboard/dto/update-settings.dto.ts` | Add DTO field |
| `prisma/schema.prisma` | Add column to EngineConfig |
| `src/dashboard/settings.service.ts` | Add to SERVICE_RELOAD_MAP + handler |
| `src/modules/execution/execution.service.ts` | Core: new field, reloadConfig, verifyDualLegDepth, gate in execute() |

### Key Implementation Points

- Insert dual-leg gate BEFORE `const primaryAvailableDepth = await this.getAvailableDepth(...)` (~line 303)
- `dualLegMinDepthRatio` stored as `number` (like `minFillRatio`), NOT Decimal
- Reuse existing `OPPORTUNITY_FILTERED` event with reason `"insufficient dual-leg depth"`
- Parallel fetch: `Promise.all([getAvailableDepth(primary), getAvailableDepth(secondary)])`
- Existing per-leg checks remain as defense-in-depth (do not remove)

## Execution Report

- **Generation Mode:** Sequential (AI generation, backend-only)
- **Stack:** Backend (Vitest, NestJS TestingModule)
- **Knowledge Fragments Used:** data-factories, test-quality, test-levels-framework, test-priorities-matrix, test-healing-patterns, component-tdd
- **Red Phase Verified:** All 18 tests use `it.skip()`, zero placeholder assertions
