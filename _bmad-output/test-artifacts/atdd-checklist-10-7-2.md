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
  - _bmad-output/implementation-artifacts/10-7-2-vwap-slippage-aware-edge-calculation.md
  - _bmad/tea/testarch/knowledge/data-factories.md
  - _bmad/tea/testarch/knowledge/test-quality.md
  - _bmad/tea/testarch/knowledge/test-levels-framework.md
  - _bmad/tea/testarch/knowledge/test-priorities-matrix.md
  - _bmad/tea/testarch/knowledge/test-healing-patterns.md
---

# ATDD Checklist: Story 10-7-2 — VWAP Slippage-Aware Edge Calculation

## TDD Red Phase (Current)

All 24 failing tests generated with `it.skip()`.

| Test File | Test Count | Status |
|---|---|---|
| `src/modules/arbitrage-detection/edge-calculator.service.spec.ts` | 18 | Skipped (RED) |
| `src/common/utils/financial-math.spec.ts` | 6 | Skipped (RED) |
| **Total** | **24** | **All skipped** |

## Story Summary

**As an** operator,
**I want** the system to calculate expected edge using VWAP fill prices at target position size,
**So that** the displayed edge accurately reflects what execution would actually achieve.

Root cause: detection uses best-level prices but execution fills across multiple levels. VWAP closes this gap.

## Acceptance Criteria Coverage

### AC-1: VWAP-based edge replaces best-bid/ask edge (P0)
- [x] 1.1 Single-level book → VWAP equals best-level → both edges identical (backward compatible)
- [x] 1.2 Multi-level book → VWAP edge is lower than best-level edge (more conservative)
- [x] 1.3 grossEdge recalculated as vwapSellPrice - vwapBuyPrice (not best-level)
- [x] 1.4 VWAP edge above threshold → enriched opportunity created with VWAP prices

### AC-2: Partial fill handling (P0)
- [x] 2.1 Thin book → partial fill VWAP → edge calculated, passes if above threshold
- [x] 2.2 Very thin book → fill ratio below `detectionMinFillRatio` → filtered with `"insufficient_vwap_depth"`
- [x] 2.3 Empty book side → VWAP returns null → filtered with `"insufficient_vwap_depth"`
- [x] 2.4 Zero price in dislocation → filtered with `"insufficient_vwap_depth"`

### AC-3: VWAP-adjusted edge threshold filtering (P0)
- [x] 3.1 VWAP edge below threshold → filtered with `"below_threshold"` (unchanged reason)
- [x] 3.2 Degradation multiplier applied to VWAP edge (not best-level)
- [x] 3.3 Capital efficiency gate (annualized return) uses VWAP net edge

### AC-4: Best-level vs VWAP edge comparison logging (P1)
- [x] 4.1 `bestLevelNetEdge` in enriched opportunity matches traditional calculation
- [x] 4.2 `OpportunityIdentifiedEvent` payload includes `bestLevelNetEdge`, `vwapBuyPrice`, `vwapSellPrice`, `buyFillRatio`, `sellFillRatio`
- [x] 4.3 `OpportunityFilteredEvent` payload for `"insufficient_vwap_depth"` carries matchId and reason
- [x] 4.4 `FilteredDislocation` includes `bestLevelNetEdge` for threshold-filtered opportunities

### AC-5: Configurable detection fill ratio (P1)
- [x] 5.1 `reloadConfig` updates `detectionMinFillRatio` at runtime
- [x] 5.2 Startup validation rejects `DETECTION_MIN_FILL_RATIO` ≤ 0
- [x] 5.3 Startup validation rejects `DETECTION_MIN_FILL_RATIO` > 1.0

### calculateVwapWithFillInfo helper (P0)
- [x] 6.1 Single-level book, full fill → `filledQty = positionSize`, `vwap = level price`
- [x] 6.2 Multi-level book, full fill → correct VWAP and `filledQty`
- [x] 6.3 Partial fill → `filledQty < positionSize`, VWAP across available
- [x] 6.4 Empty side → returns null
- [x] 6.5 Zero position size → returns null
- [x] 6.6 `totalQtyAvailable` sums all levels correctly

## Priority Distribution

| Priority | Count | Percentage |
|---|---|---|
| P0 | 17 | 71% |
| P1 | 7 | 29% |
| **Total** | **24** | 100% |

## Test Levels

| Level | Count | Location |
|---|---|---|
| Unit | 18 | `src/modules/arbitrage-detection/edge-calculator.service.spec.ts` |
| Unit | 6 | `src/common/utils/financial-math.spec.ts` |
| E2E | 0 | N/A (backend-only story) |

## Fixture Needs

No new fixtures required. Tests reuse existing factory patterns:
- `makeDislocation()`, `makePair()`, `makeOrderBook()`, `makeFeeSchedule()` — edge-calculator spec
- `makeOrderBook()` — financial-math spec (different signature, local helper)
- New `makeMultiLevelOrderBook()` helper added inline for VWAP multi-level tests
- New `makeVwapDislocation()` factory added inline for common multi-level dislocation setup

## Mock Requirements

No external mocks. Tests use existing NestJS TestingModule pattern with:
- `ConfigService` mock (inline `vi.fn()`)
- `DegradationProtocolService` mock
- `KalshiConnector` / `PolymarketConnector` mock (getFeeSchedule)
- `EventEmitter2` mock (emit spy)

## Implementation Guidance

### Files to Create/Modify (from story)

| File | Change |
|---|---|
| `src/common/utils/financial-math.ts` | Add `calculateVwapWithFillInfo()` + `VwapFillResult` interface |
| `src/common/config/env.schema.ts` | Add `DETECTION_MIN_FILL_RATIO` |
| `src/common/config/config-defaults.ts` | Add `detectionMinFillRatio` entry |
| `src/common/config/settings-metadata.ts` | Add metadata under DetectionEdge group |
| `src/common/config/effective-config.types.ts` | Add `detectionMinFillRatio` field |
| `src/dashboard/dto/update-settings.dto.ts` | Add DTO field |
| `src/dashboard/settings.service.ts` | Add to SERVICE_RELOAD_MAP + handler |
| `src/dashboard/settings.service.spec.ts` | Update settings count (72→73) |
| `src/persistence/repositories/engine-config.repository.ts` | Add to resolve chain |
| `prisma/schema.prisma` | Add column to EngineConfig |
| `src/modules/arbitrage-detection/types/enriched-opportunity.type.ts` | Add VWAP fields to EnrichedOpportunity and LiquidityDepth |
| `src/modules/arbitrage-detection/types/edge-calculation-result.type.ts` | Add `bestLevelNetEdge?` to FilteredDislocation |
| `src/modules/arbitrage-detection/edge-calculator.service.ts` | Core: VWAP edge calc, reloadConfig, config field, startup validation |

### Key Implementation Points

- **VWAP side mapping:** Buy leg (buying at ask) uses `closeSide='sell'`; Sell leg (selling at bid) uses `closeSide='buy'` — counterintuitive, document in code comment
- **Target contract conversion:** `positionSizeUsd / dislocation.buyPrice` with `Decimal.ceil()` — use best-level prices, not VWAP
- **grossEdge recalculation:** Must recompute as `vwapSellPrice - vwapBuyPrice`, NOT pass old `grossEdge`
- **Insertion point:** After fee schedule + gas estimate retrieval, BEFORE current `calculateNetEdge()` call
- **Config pipeline:** Follow exact pattern from 10-7-1 — env.schema → config-defaults → settings-metadata → DTO → Prisma → effective-config → repository → settings.service
- **Financial math tests:** Replace placeholder `calculateVwapWithFillInfo` with real import after Task 4

## Next Steps (TDD Green Phase)

After implementing the feature (Tasks 1-8 from story):

1. In `financial-math.spec.ts`: Remove placeholder type + constant, add real import for `calculateVwapWithFillInfo`
2. Remove `it.skip()` from all 6 tests in `financial-math.spec.ts`
3. Remove `it.skip()` from all 18 tests in `edge-calculator.service.spec.ts`
4. Run tests: `pnpm test`
5. Verify all 24 tests PASS (green phase)
6. If any fail:
   - Feature bug → fix implementation
   - Test bug → fix test (adjust mock data / assertions)
7. Update existing tests that assert on `EnrichedOpportunity` shape — add new fields to assertions
8. Run `pnpm lint`
9. Commit passing tests with implementation

## Running Tests

```bash
# Run all tests for affected files
cd pm-arbitrage-engine && pnpm vitest run src/common/utils/financial-math.spec.ts src/modules/arbitrage-detection/edge-calculator.service.spec.ts

# Run with verbose output
pnpm vitest run --reporter=verbose src/modules/arbitrage-detection/edge-calculator.service.spec.ts

# Run only 10-7-2 tests (by grep)
pnpm vitest run -t "10-7-2"

# Run with coverage
pnpm test:cov
```

## Test Execution Evidence

### Initial Test Run (RED Phase Verification)

**Command:** `pnpm vitest run src/common/utils/financial-math.spec.ts src/modules/arbitrage-detection/edge-calculator.service.spec.ts`

**Results:**
- Test Files: 2 passed
- Tests: 119 passed | 24 skipped (143 total)
- Duration: 1.63s

**Summary:**
- All 119 existing tests PASS (no regressions)
- All 24 new Story 10-7-2 tests SKIPPED (TDD red phase)
- Status: RED phase verified

## Execution Report

- **Generation Mode:** Sequential (AI generation, backend-only)
- **Stack:** Backend (Vitest, NestJS TestingModule)
- **Knowledge Fragments Used:** data-factories, test-quality, test-levels-framework, test-priorities-matrix, test-healing-patterns
- **Red Phase Verified:** All 24 tests use `it.skip()`, zero placeholder assertions, full test bodies with real assertions
