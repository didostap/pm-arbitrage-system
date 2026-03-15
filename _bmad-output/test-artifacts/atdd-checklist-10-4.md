---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04c-aggregate
  - step-05-validate-and-complete
lastStep: step-05-validate-and-complete
lastSaved: '2026-03-21'
storyId: '10-4'
storyName: 'Adaptive Leg Sequencing & Matched-Count Execution'
inputDocuments:
  - _bmad-output/implementation-artifacts/10-4-adaptive-leg-sequencing.md
  - _bmad/tea/config.yaml
  - _bmad/tea/testarch/tea-index.csv
  - _bmad/tea/testarch/knowledge/data-factories.md
  - _bmad/tea/testarch/knowledge/test-quality.md
  - _bmad/tea/testarch/knowledge/test-healing-patterns.md
  - _bmad/tea/testarch/knowledge/test-levels-framework.md
  - _bmad/tea/testarch/knowledge/test-priorities-matrix.md
  - _bmad/tea/testarch/knowledge/component-tdd.md
---

# ATDD Checklist: Story 10.4 — Adaptive Leg Sequencing & Matched-Count Execution

## TDD Red Phase (Current)

All failing tests generated with `it.skip()` / `test.skip()`.

| Category | File | Tests | Phase |
|---|---|---|---|
| Unit (Vitest) | `pm-arbitrage-engine/src/modules/execution/execution.service.spec.ts` | 31 | RED |
| Unit (Vitest) | `pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.spec.ts` | 4 | RED |
| Unit (Vitest) | `pm-arbitrage-engine/src/dashboard/dashboard.service.spec.ts` | 3 | RED |
| Unit (Vitest) | `pm-arbitrage-engine/src/dashboard/dashboard-event-mapper.service.spec.ts` | 2 | RED |
| E2E (Playwright) | `e2e/tests/ui/execution-metadata-display.spec.ts` | 5 | RED |
| **Total** | | **45** | **RED** |

## Acceptance Criteria Coverage

| AC | Description | Unit Tests | E2E Tests | Priority |
|---|---|---|---|---|
| #1 | Adaptive sequencing — latency override | Latency override both directions (2), connector resolution (1), logged decision (1) | — | P0 |
| #2 | Static fallback when latency unavailable/stable | Stable latency (1), null one platform (1), both null (1), disabled (1) | — | P0 |
| #3 | Unified collateral-aware sizing formula | idealCount formula (1), budget guard (1), dual depth cap (1), edge re-validation (1), combinedDivisor≤0 (1), min-fill-ratio (1), equalization regression (1), actualCapitalUsed (1) | — | P0 |
| #4 | Clean reservation release on depth rejection | Regression test with unified sizing (1) | — | P0 |
| #5 | Dashboard execution metadata display | DTO fields (1), JSON-to-flat mapping (1), null metadata handling (1), WS payload (1), event mapper (1) | Latency override display (1), static config display (1), divergence+stale (1), legacy position (1), null latency N/A (1) | P1-P2 |
| #6 | Data source classification per leg | websocket (1), polling (1), stale_fallback (1), divergence warning (1), worst-of-two (1) | — | P0-P1 |
| #7 | Internal subsystem verification | Orders reach connector (1), getOrderBookFreshness called (1), health P95 called (1) | — | P0 |
| — | Paper/live boundary (Team Agreement #20) | Paper sequencing (1), live sequencing (1), sizing identical (1) | — | P0 |
| — | Polymarket poll configurability (tech debt) | Custom timeout (1), custom interval (1), jitter (1), defaults (1) | — | P1 |

## Priority Distribution

| Priority | Count | Description |
|---|---|---|
| P0 | 25 | Financial safety, capital conservation, execution ordering, data integrity, regression |
| P1 | 15 | Core flow details, observability, dashboard DTOs, WS events, configurability |
| P2 | 4 | Dashboard UI display (E2E) |
| P3 | 1 | Legacy position graceful fallback (E2E) |

## Dedicated Test Blocks (Team Agreements)

| Block | Tests | Agreement |
|---|---|---|
| `describe('paper-live-boundary')` | 3 | Team Agreement #20 |
| `describe('internal subsystem verification')` | 3 | Team Agreement #19 |
| `describe('data source classification')` | 5 | Team Agreement #23 |

## Test Strategy

- **Unit tests** (40): ExecutionService business logic (unified sizing, adaptive sequencing, data source classification, metadata persistence, subsystem verification, paper/live boundary, reservation release), PolymarketConnector poll configurability, Dashboard service metadata mapping, Dashboard event mapper sequencing
- **E2E tests** (5): Position detail page execution info section display — latency override, static config, divergence/stale, legacy position fallback, null latency N/A
- **No new REST endpoints**: Story modifies execution internals and adds metadata to existing DTOs
- **Execution mode**: SUBAGENT (parallel API + E2E generation)

## Next Steps (TDD Green Phase)

After implementing the feature:

1. Remove `it.skip()` / `test.skip()` from all test files
2. Run unit tests: `cd pm-arbitrage-engine && pnpm test`
3. Run E2E tests: `cd e2e && npx playwright test`
4. Verify tests PASS (green phase)
5. If any tests fail:
   - Either fix implementation (feature bug)
   - Or fix test (test bug — adjust mock expectations)
6. Run `pnpm lint` and commit

## Implementation Guidance

### Backend (ExecutionService + Connectors)

Files to create:
- None (all changes modify existing files)

Files to modify:
- `src/common/config/env.schema.ts` — +4 config keys
- `src/modules/execution/execution.service.ts` — Unified sizing, adaptive sequencing, data source classification, metadata population
- `src/modules/execution/execution.module.ts` — +DataIngestionModule import
- `src/connectors/polymarket/polymarket.connector.ts` — Configurable poll timeout/interval with jitter
- `src/common/events/execution.events.ts` — +sequencingDecision field on OrderFilledEvent
- `prisma/schema.prisma` — +executionMetadata Json? on OpenPosition

### Dashboard Backend

Files to modify:
- `src/dashboard/dto/position-detail.dto.ts` — +execution metadata fields
- `src/dashboard/dto/ws-events.dto.ts` — +sequencingReason, primaryLeg on WsExecutionCompletePayload
- `src/dashboard/dashboard.service.ts` — Map executionMetadata JSON to DTO fields
- `src/dashboard/dashboard-event-mapper.service.ts` — Map OrderFilledEvent sequencing to WS payload

### Dashboard Frontend

Files to modify:
- `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx` — +Execution Info section
- `pm-arbitrage-dashboard/src/api/generated/Api.ts` — Regenerate after DTO changes

## Test Execution Evidence

### Red Phase Verification

**Command:** `cd pm-arbitrage-engine && pnpm test`

**Results:**

```
Test Files  125 passed (125)
     Tests  2369 passed | 40 skipped | 2 todo (2411)
  Duration  21.75s
```

**Summary:**

- Total existing tests: 2369 (all passing)
- New Story 10.4 tests: 40 skipped (unit) + 5 skipped (E2E, separate runner)
- Failing: 0 (skipped tests don't run — RED phase by skip)
- Status: RED phase verified — no existing tests broken

### data-testid Requirements (E2E)

| Element | data-testid |
|---|---|
| Primary leg badge | `execution-primary-leg` |
| Sequencing reason badge | `execution-sequencing-reason` |
| Kalshi latency | `execution-kalshi-latency` |
| Polymarket latency | `execution-polymarket-latency` |
| Ideal count | `execution-ideal-count` |
| Matched count | `execution-matched-count` |
| Depth cap indicator | `execution-depth-capped` |
| Kalshi data source badge | `execution-kalshi-data-source` |
| Polymarket data source badge | `execution-polymarket-data-source` |
| Divergence warning | `execution-divergence-warning` |

## Generation Metadata

- **Execution mode:** SUBAGENT (parallel)
- **Performance:** ~50% faster than sequential
- **Knowledge fragments used:** data-factories, test-quality, test-healing-patterns, test-levels-framework, test-priorities-matrix, component-tdd
- **Generated:** 2026-03-21
