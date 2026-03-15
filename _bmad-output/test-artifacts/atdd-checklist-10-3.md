---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04c-aggregate
  - step-05-validate-and-complete
lastStep: step-05-validate-and-complete
lastSaved: '2026-03-21'
storyId: '10-3'
storyName: 'Automatic Single-Leg Management'
inputDocuments:
  - _bmad-output/implementation-artifacts/10-3-automatic-single-leg-management.md
  - _bmad/tea/config.yaml
  - _bmad/tea/testarch/tea-index.csv
  - _bmad/tea/testarch/knowledge/data-factories.md
  - _bmad/tea/testarch/knowledge/test-quality.md
  - _bmad/tea/testarch/knowledge/test-healing-patterns.md
  - _bmad/tea/testarch/knowledge/test-levels-framework.md
  - _bmad/tea/testarch/knowledge/test-priorities-matrix.md
  - _bmad/tea/testarch/knowledge/component-tdd.md
---

# ATDD Checklist: Story 10.3 — Automatic Single-Leg Management

## TDD Red Phase (Current)

All failing tests generated with `test.skip()` / `it.skip()`.

| Category | File | Tests | Phase |
|---|---|---|---|
| Unit (Vitest) | `pm-arbitrage-engine/src/modules/execution/auto-unwind.service.spec.ts` | 46 | RED |
| E2E (Playwright) | `e2e/tests/ui/auto-unwind-display.spec.ts` | 3 | RED |
| **Total** | | **49** | **RED** |

## Acceptance Criteria Coverage

| AC | Description | Unit Tests | E2E Tests | Priority |
|---|---|---|---|---|
| #1 | Auto-unwind after stabilization delay | Config guard (2), Close success (3), Close failure (3), Delay (2) | — | P0 |
| #2 | SingleLegContext in AutoUnwindEvent | Event payload (3) | — | P0 |
| #3 | Paper/live mode | Paper-live-boundary (4), Mixed mode (1) | — | P0 |
| #4 | Dashboard visibility | Monitoring (4) | Position detail (2), Alert card (1) | P1-P2 |
| #5 | Internal subsystem verification | Subsystem verification (4) | — | P0 |
| #6 | Zero regression when disabled | Zero-regression (4) | — | P0 |
| #7 | Loss threshold skip | Loss threshold (6), Estimation edge cases (2) | — | P0 |

## Priority Distribution

| Priority | Count | Description |
|---|---|---|
| P0 | 30 | Financial safety, capital exposure, data integrity, regression |
| P1 | 16 | Core flow details, timing, monitoring, dashboard display |
| P2 | 3 | Secondary display, CSV logging, alert card |

## Dedicated Test Blocks (Team Agreements)

| Block | Tests | Agreement |
|---|---|---|
| `describe('paper-live-boundary')` | 4 | Team Agreement #20 |
| `describe('internal-subsystem-verification')` | 4 | Team Agreement #19 |
| `describe('zero-regression')` | 4 | AC #6 |

## Test Strategy

- **Unit tests** (46): AutoUnwindService business logic, config guards, loss estimation, race conditions, event payloads, error handling, monitoring integration
- **E2E tests** (3): Dashboard position detail page auto-unwind section, alert card inline display, operator action buttons
- **No new REST endpoints**: Auto-unwind is event-driven (`@OnEvent`), not REST-exposed
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

### Backend (AutoUnwindService)

Files to create:
- `src/modules/execution/auto-unwind.service.ts` — Event-driven auto-unwind logic

Files to modify:
- `src/common/config/env.schema.ts` — +3 config keys
- `src/common/events/execution.events.ts` — +AutoUnwindEvent class
- `src/common/events/event-catalog.ts` — +AUTO_UNWIND event name
- `src/modules/execution/execution.module.ts` — +AutoUnwindService provider
- `src/modules/monitoring/event-consumer.service.ts` — +AUTO_UNWIND subscriber
- `src/modules/monitoring/telegram-formatter.service.ts` — +formatAutoUnwind()
- `src/modules/monitoring/csv-trade-logger.service.ts` — +auto-unwind CSV format
- `src/dashboard/dashboard-event-mapper.service.ts` — +AutoUnwindEvent mapping
- `src/dashboard/dashboard.gateway.ts` — +AUTO_UNWIND WS emission
- `src/dashboard/dto/` — Extend alert DTO with auto-unwind fields

### Frontend (Dashboard)

Files to modify:
- `pm-arbitrage-dashboard/src/pages/PositionDetailPage.tsx` — +auto-unwind section
- Alert card component — +inline auto-unwind data
- `pm-arbitrage-dashboard/src/api/generated/Api.ts` — Regenerate after DTO changes

## Generation Metadata

- **Execution mode:** SUBAGENT (parallel)
- **Performance:** ~50% faster than sequential
- **Knowledge fragments used:** data-factories, test-quality, test-healing-patterns, test-levels-framework, test-priorities-matrix, component-tdd
- **Generated:** 2026-03-21
