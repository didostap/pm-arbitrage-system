---
stepsCompleted:
  - step-01-preflight-and-context
  - step-02-generation-mode
  - step-03-test-strategy
  - step-04c-aggregate
  - step-05-validate-and-complete
lastStep: step-05-validate-and-complete
lastSaved: '2026-03-22'
storyId: '10-5-4'
storyTitle: 'Event Wiring Verification & Collection Lifecycle Guards'
inputDocuments:
  - _bmad-output/implementation-artifacts/10-5-4-event-wiring-verification-collection-lifecycle-guards.md
  - _bmad/tea/testarch/knowledge/data-factories.md
  - _bmad/tea/testarch/knowledge/test-quality.md
  - _bmad/tea/testarch/knowledge/test-healing-patterns.md
  - _bmad/tea/testarch/knowledge/test-levels-framework.md
  - _bmad/tea/testarch/knowledge/test-priorities-matrix.md
---

# ATDD Checklist: Story 10-5-4 — Event Wiring Verification & Collection Lifecycle Guards

## TDD Red Phase (Current)

All tests generated with `it.skip()` — will fail until implementation.

| File | Tests | ACs Covered | Status |
|------|-------|-------------|--------|
| `src/common/testing/expect-event-handled.spec.ts` | 11 | AC1, AC3 | RED |
| `src/common/testing/event-wiring-audit.spec.ts` | 36 | AC2 | RED |
| `src/common/testing/collection-lifecycle-audit.spec.ts` | 7 | AC4, AC5 | RED |
| **Total** | **54** | | **RED** |

## Acceptance Criteria Coverage

### AC1 — `expectEventHandled()` Integration Test Helper

| Test ID | Scenario | Priority | File |
|---------|----------|----------|------|
| AC1-UNIT-001 | Handler invoked via real EventEmitter2 | P0 | expect-event-handled.spec.ts |
| AC1-UNIT-002 | Throws when handler method doesn't exist | P0 | expect-event-handled.spec.ts |
| AC1-UNIT-003 | Throws when @OnEvent event name mismatches | P0 | expect-event-handled.spec.ts |
| AC1-UNIT-004 | Works with async handlers | P1 | expect-event-handled.spec.ts |
| AC1-UNIT-005 | Timeout when handler never invoked | P0 | expect-event-handled.spec.ts |
| AC1-UNIT-006 | Payload passed correctly to handler | P1 | expect-event-handled.spec.ts |

### AC2 — Existing @OnEvent Audit (36 handlers)

| Service | Handler | Event | Priority | File |
|---------|---------|-------|----------|------|
| MatchAprUpdaterService | onOpportunityIdentified | OPPORTUNITY_IDENTIFIED | P0 | event-wiring-audit.spec.ts |
| MatchAprUpdaterService | onOpportunityFiltered | OPPORTUNITY_FILTERED | P0 | event-wiring-audit.spec.ts |
| CorrelationTrackerService | onBudgetCommitted | BUDGET_COMMITTED | P0 | event-wiring-audit.spec.ts |
| CorrelationTrackerService | onExitTriggered | EXIT_TRIGGERED | P0 | event-wiring-audit.spec.ts |
| AutoUnwindService | onSingleLegExposure | SINGLE_LEG_EXPOSURE | P0 | event-wiring-audit.spec.ts |
| ExposureTrackerService | onSingleLegExposure | SINGLE_LEG_EXPOSURE | P0 | event-wiring-audit.spec.ts |
| ShadowComparisonService | onShadowComparison | SHADOW_COMPARISON | P0 | event-wiring-audit.spec.ts |
| ShadowComparisonService | onExitTriggered | EXIT_TRIGGERED | P0 | event-wiring-audit.spec.ts |
| DataIngestionService | onOrderFilled | ORDER_FILLED | P0 | event-wiring-audit.spec.ts |
| DataIngestionService | onExitTriggered | EXIT_TRIGGERED | P0 | event-wiring-audit.spec.ts |
| DataIngestionService | onSingleLegResolved | SINGLE_LEG_RESOLVED | P0 | event-wiring-audit.spec.ts |
| TradingEngineService | onTimeDriftHalt | TIME_DRIFT_HALT | P0 | event-wiring-audit.spec.ts |
| ConfigAccessorService | onConfigSettingsUpdated | CONFIG_SETTINGS_UPDATED | P0 | event-wiring-audit.spec.ts |
| ConfigAccessorService | onConfigBankrollUpdated | CONFIG_BANKROLL_UPDATED | P0 | event-wiring-audit.spec.ts |
| DashboardGateway | (22 handlers) | (22 events) | P1 | event-wiring-audit.spec.ts |
| Dead handler audit | — | — | P0 | event-wiring-audit.spec.ts |

### AC3 — Test Template

| Test ID | Scenario | Priority | File |
|---------|----------|----------|------|
| AC3-UNIT-002 | Single-handler scenario template | P1 | expect-event-handled.spec.ts |
| AC3-UNIT-003 | Multi-handler scenario template | P1 | expect-event-handled.spec.ts |

### AC4/AC5 — Collection Lifecycle

| Test ID | Collection | Service | Priority | File |
|---------|-----------|---------|----------|------|
| AC5-UNIT-001 | notifiedOpportunityPairs | EventConsumerService | P0 | collection-lifecycle-audit.spec.ts |
| AC5-UNIT-001b | notifiedOpportunityPairs .delete on exit | EventConsumerService | P1 | collection-lifecycle-audit.spec.ts |
| AC5-UNIT-001c | notifiedOpportunityPairs .clear on overflow | EventConsumerService | P1 | collection-lifecycle-audit.spec.ts |
| AC5-UNIT-002 | lastContractUpdateTime | PlatformHealthService | P0 | collection-lifecycle-audit.spec.ts |
| AC5-UNIT-003 | lastEmitted | ExposureAlertScheduler | P0 | collection-lifecycle-audit.spec.ts |
| AC5-UNIT-004a-c | onModuleDestroy cleanup | Multiple services | P1 | collection-lifecycle-audit.spec.ts |
| AC5-UNIT-005 | Bounded collections | PlatformHealthService | P2 | collection-lifecycle-audit.spec.ts |

### AC6 — CLAUDE.md Convention Update

- [ ] CLAUDE.md contains: "Every new Map/Set must specify its cleanup strategy in a code comment and have a test for the cleanup path."
- [ ] CLAUDE.md contains event wiring test requirement under Testing Conventions

### AC7 — MEDIUM Prevention Analysis

- [ ] Top 3 recurring MEDIUM categories documented
- [ ] Structural prevention measures proposed (not "be more careful")
- [ ] Document placed in Dev Agent Record

## Priority Summary

| Priority | Count | Percentage |
|----------|-------|-----------|
| P0 | 22 | 41% |
| P1 | 30 | 56% |
| P2 | 2 | 3% |
| **Total** | **54** | |

## Next Steps (TDD Green Phase)

After implementing Story 10-5-4:

1. **Create `src/common/testing/expect-event-handled.ts`** — the helper function
2. **Create `src/common/testing/index.ts`** — barrel export
3. **Replace placeholder assertions** in collection-lifecycle-audit.spec.ts with real service tests
4. **Upgrade wiring audit tests** from EVENT_NAMES existence checks to full `expectEventHandled()` integration tests
5. **Remove `it.skip()`** from all test files
6. **Run tests:** `cd pm-arbitrage-engine && pnpm test`
7. **Verify all tests PASS** (green phase)
8. **Add CLAUDE.md conventions** (AC6)
9. **Write MEDIUM prevention analysis** (AC7)
10. **Run `pnpm lint`** — zero errors

## Implementation Guidance

### Files to Create

| File | Purpose |
|------|---------|
| `src/common/testing/expect-event-handled.ts` | Helper function implementation |
| `src/common/testing/index.ts` | Barrel export |

### Files to Modify

| File | Change |
|------|--------|
| `src/modules/monitoring/event-consumer.service.ts` | Add `notifiedOpportunityPairs.clear()` to `onModuleDestroy()` |
| `src/modules/data-ingestion/platform-health.service.ts` | Add `removeContractTracking()` method with `.delete()` |
| All 31 Map/Set declarations | Add cleanup strategy code comments |
| `CLAUDE.md` (root repo) | Add collection lifecycle + event wiring conventions |

### Architecture Constraints

- `src/common/testing/` can import from `common/events/` but NOT from `modules/` or `connectors/`
- Wiring tests use real EventEmitter2 (not mocked) — matches `event-consumer.service.spec.ts` pattern
- Collection cleanup tests should be co-located with service spec files (final placement)
- CLAUDE.md is in root repo — requires separate git commit

## Execution Report

- **Mode:** Sequential (Worker B empty — backend only)
- **Files generated:** 3 test files + 1 checklist
- **Test count:** 54 (all `it.skip()`)
- **TDD phase:** RED
