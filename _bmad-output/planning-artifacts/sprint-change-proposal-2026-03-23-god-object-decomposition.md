# Sprint Change Proposal — God Object Decomposition & Structural Refactoring

**Date:** 2026-03-23
**Author:** Bob (Scrum Master)
**Scope Classification:** Moderate
**Approved:** Yes (2026-03-23)

---

## Section 1: Issue Summary

### Problem Statement

A codebase structural audit during Epic 10.7 identified **six God Objects/Files** that have accumulated multiple distinct responsibilities over Epics 4–10.5 (10 epics of organic feature growth). These oversized services violate the Single Responsibility Principle, inflate AI agent token overhead, increase cognitive load, and create implicit coupling through oversized constructors.

### Discovery Context

The audit was conducted as a proactive maintainability review after 10 feature epics grew the codebase to ~120+ source files and 2,631+ tests. No single story triggered this — the debt accumulated incrementally.

### Evidence Summary

| File | Lines | Methods | Dependencies | Responsibility Count |
|------|-------|---------|-------------|---------------------|
| `RiskManagerService` | 1,651 | 34 | 12 | 6 |
| `ExitMonitorService` | 1,438 | 10 | 23 props | 4 |
| `ExecutionService` | 1,395 | 7 | 12 | 4 |
| `DashboardService` | 1,205 | 20 | 14 | 6 |
| `TelegramMessageFormatter` | 789 | 31 functions | — | God File (1 concern per function, all in 1 file) |
| `TelegramAlertService` | 734 | 19 | 16 props | 2 |

Test file bloat mirrors source:
- `execution.service.spec.ts` — 3,714 lines
- `risk-manager.service.spec.ts` — 2,747 lines
- `dashboard.service.spec.ts` — 1,444 lines

### Why This Matters Now

1. **AI agent token efficiency:** Files >800 lines cannot be consumed in full by an AI agent without excessive token overhead, degrading code generation quality.
2. **Epic 11 readiness:** Platform extensibility work (plugin architecture, secrets management) will be significantly harder against oversized, tightly-coupled services.
3. **Test isolation:** God Object tests are fragile — changes to one responsibility break tests for unrelated responsibilities in the same file.
4. **Onboarding friction:** New contributors (human or AI) must understand 1,600 lines of mixed concerns to modify any single responsibility.

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| **Epic 10.7** (in-progress) | **None — no interruption** | Refactoring is orthogonal to paper profitability stories. Stories 10-7-2/10-7-4 touch God Objects but don't require the split to proceed. |
| **Epic 11** (backlog) | **Significant benefit** | Cleaner `RiskManagerService` and `ExecutionService` make plugin architecture (11-1) and secrets integration (11-2) substantially easier. |
| **Epic 12** (backlog) | **Moderate benefit** | Split monitoring services simplify compliance reporting extensions. |

### Story Impact

- **No existing stories need modification.** All refactoring is additive — new stories in a new epic.
- Stories 10-7-2 (VWAP edge) and 10-7-4 (realized PnL) would benefit from but do not require the split.

### Artifact Conflicts

| Artifact | Impact | Action Required |
|----------|--------|----------------|
| **PRD** | None | No functional scope change |
| **Architecture** | Minor post-update | Update Module Structure section with new service files after refactoring |
| **UX Design** | None | No API contract changes, no dashboard changes |
| **CLAUDE.md** | Minor post-update | Update Module Structure section with new service files |
| **Epics doc** | Addition | Add Epic 10.8 entry |
| **Sprint status** | Addition | Add Epic 10.8 entries |

### Technical Impact

- **Zero API contract changes** — all refactoring is internal service decomposition.
- **NestJS module registrations** — new services must be registered as providers in their respective modules and exported if used cross-module.
- **Import paths** — module barrel files (`index.ts`) should re-export from new services to minimize import churn.
- **Dependency injection** — services that currently inject a God Object will need to inject the specific extracted service instead. This is the primary migration concern.
- **Test co-location** — tests split alongside source, maintaining the project's co-location convention.

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment — New Epic 10.8

**Rationale:**
- Pure refactoring with zero functional scope change
- 2,631+ existing tests provide a comprehensive safety net
- Each story is a self-contained service extraction with clear before/after boundaries
- No rollback scenario exists (debt accumulated over 10 epics)
- No PRD/MVP scope adjustment needed

**Effort Estimate:** Medium — 6 stories (P0–P2), estimated 2–3 sessions
**Risk Level:** Low — comprehensive test coverage, no feature changes
**Timeline Impact:** None on existing roadmap. Epic 10.8 slots between 10.7 and 11.

### Alternatives Considered

| Option | Verdict | Reason |
|--------|---------|--------|
| Rollback | Not viable | No single change to revert — growth was organic over 10 epics |
| PRD/MVP Review | Not applicable | Internal quality improvement, no functional scope change |
| Defer to Epic 11 | Rejected | Would make Epic 11 stories harder; better to clean house first |
| Incremental (split within feature stories) | Rejected | Creates split-brain state during feature work; dedicated epic is cleaner |

---

## Section 4: Detailed Change Proposals

### New Epic: 10.8 — God Object Decomposition & Structural Refactoring

**Epic Goal:** Decompose all identified God Objects into focused, single-responsibility services. Every source file should be under ~600 lines after refactoring. Maintain 100% test pass rate throughout.

**Sequencing:** After Epic 10.7 completes, before Epic 11.

**Hard Constraint:** Zero functional changes. Every refactoring story must pass the existing test suite with no behavioral modifications.

---

#### Story 10-8-1: RiskManagerService Decomposition (P0)

**Current state:** 1,651 lines, 34 methods, 12 deps, 6 responsibilities
**Target state:** 4 focused services, each ~300–500 lines

| New Service | Extracted Responsibility | Key Methods |
|---|---|---|
| `BudgetReservationService` | Budget reservation lifecycle | `reserveBudget`, `commitReservation`, `releaseReservation`, `releasePartialCapital`, `adjustReservation`, `clearStaleReservations` |
| `TradingHaltService` | Trading halt/resume lifecycle | `haltTrading`, `resumeTrading`, `isTradingHalted`, `getActiveHaltReasons` |
| `RiskStateManager` | State persistence, recovery, recalculation | `initializeStateFromDb`, `persistState`, `recalculateFromPositions`, `loadBankrollFromDb` |
| `RiskManagerService` (slimmed) | Validation, PnL, config orchestration | `validatePosition`, `updateDailyPnl`, `reloadConfig`, state queries |

**Migration pattern:**
1. Extract service with methods + relevant properties
2. Register as provider in `RiskManagementModule`
3. Inject extracted service into slimmed `RiskManagerService` (facade pattern during migration)
4. Update all direct consumers to inject the specific service they need
5. Remove facade delegation once all consumers are migrated
6. Split `risk-manager.service.spec.ts` (2,747 lines) into co-located test files

**Acceptance Criteria:**
- [ ] Each new service file is under 500 lines
- [ ] All 2,631+ tests pass with zero behavioral changes
- [ ] `RiskManagerService` is under 600 lines
- [ ] No module dependency rule violations (per CLAUDE.md)
- [ ] All consumers inject the most specific service they need (no over-injection)
- [ ] `risk-manager.service.spec.ts` is decomposed into co-located files (<800 lines each)

---

#### Story 10-8-2: ExitMonitorService Decomposition (P0)

**Current state:** 1,438 lines, 10 methods, 23 config properties
**Target state:** 3 focused services, each ~300–500 lines

| New Service | Extracted Responsibility | Key Methods |
|---|---|---|
| `ExitExecutionService` | Exit order submission + partial handling | `executeExit`, `handlePartialExit` |
| `ExitDataSourceService` | Data source classification + price resolution | `classifyDataSource`, `combineDataSources`, `getClosePrice`, `getAvailableExitDepth` |
| `ExitMonitorService` (slimmed) | Evaluation loop + config | `evaluatePositions`, `evaluatePosition`, `reloadConfig`, `onModuleInit` |

**Acceptance Criteria:**
- [ ] Each new service file is under 500 lines
- [ ] All tests pass with zero behavioral changes
- [ ] `ExitMonitorService` is under 600 lines
- [ ] Config properties distributed to the service that uses them (not all 23 in one place)
- [ ] Exit-related spec files remain under 800 lines each (already split in 10-5-6)

---

#### Story 10-8-3: ExecutionService Decomposition (P1)

**Current state:** 1,395 lines, 7 methods (~200 lines/method average)
**Target state:** 3 focused services

| New Service | Extracted Responsibility | Key Methods |
|---|---|---|
| `LegSequencingService` | Sequencing strategy + connector resolution | `determineSequencing`, `resolveConnectors`, `classifyDataSource` |
| `DepthAnalysisService` | Pre-trade depth verification | `getAvailableDepth` + depth helpers |
| `ExecutionService` (slimmed) | Core execution orchestration | `execute`, `handleSingleLeg`, `reloadConfig` |

**Additional concern:** The `execute()` method itself is likely 400+ lines. If it remains >200 lines after extraction of sequencing and depth logic, further decomposition into private helper methods (not new services) within the slimmed `ExecutionService` should be applied.

**Acceptance Criteria:**
- [ ] Each new service file is under 500 lines
- [ ] All tests pass with zero behavioral changes
- [ ] `ExecutionService` is under 600 lines
- [ ] `execute()` method is under 200 lines (extract orchestration helpers if needed)
- [ ] `execution.service.spec.ts` (3,714 lines) is decomposed into co-located files (<800 lines each)

---

#### Story 10-8-4: DashboardService Decomposition (P1)

**Current state:** 1,205 lines, 20 methods, 14 deps (classic "gateway God object")
**Target state:** 4 focused services

| New Service | Extracted Responsibility | Key Methods |
|---|---|---|
| `DashboardOverviewService` | System overview + health aggregation | `getOverview`, `getHealth`, `computeCompositeHealth`, `getLatestHealthLogs` |
| `DashboardCapitalService` | Capital breakdown + PnL + bankroll | `computeCapitalBreakdown`, `computeModeCapital`, `computeRealizedPnl`, `computeTimeHeld`, `updateBankroll`, `getBankrollConfig` |
| `DashboardAuditService` | Alert retrieval + audit parsing | `getAlerts`, `parseAuditDetails`, `parseJsonFieldWithEvent`, `summarizeAuditEvent` |
| `DashboardService` (slimmed) | Position queries (delegates to existing `enrichmentService`) | `getPositions`, `getPositionById`, `getPositionDetails`, `getShadowComparisons`, `getShadowSummary` |

**Note:** `DashboardController` route handlers will need their injected service updated to point to the correct specific service.

**Acceptance Criteria:**
- [ ] Each new service file is under 400 lines
- [ ] All tests pass with zero behavioral changes
- [ ] `DashboardService` is under 400 lines
- [ ] `DashboardController` injects specific services (not a single God service)
- [ ] `dashboard.service.spec.ts` (1,444 lines) is decomposed into co-located files

---

#### Story 10-8-5: TelegramMessageFormatter Domain Split (P2)

**Current state:** 789 lines, 31 standalone functions in one file (God File, not God Object)
**Target state:** 7 domain-specific formatter files + 1 shared utils file

| New File | Functions |
|---|---|
| `execution-formatters.ts` | `formatOrderFilled`, `formatExecutionFailed`, `formatSingleLegExposure`, `formatSingleLegResolved`, `formatAutoUnwind` |
| `risk-formatters.ts` | `formatLimitApproached`, `formatLimitBreached`, `formatClusterLimitBreached`, `formatAggregateClusterLimitBreached`, `formatCorrelationFooter` |
| `platform-formatters.ts` | `formatPlatformDegraded`, `formatPlatformRecovered`, `formatOrderbookStale`, `formatOrderbookRecovered`, `formatDataDivergence` |
| `system-formatters.ts` | `formatTradingHalted`, `formatTradingResumed`, `formatSystemHealthCritical`, `formatTestAlert`, `formatBankrollUpdated`, `formatReconciliationDiscrepancy` |
| `exit-formatters.ts` | `formatExitTriggered`, `formatShadowDailySummary` |
| `detection-formatters.ts` | `formatOpportunityIdentified` |
| `matching-formatters.ts` | `formatCalibrationCompleted`, `formatResolutionDivergence`, `formatResolutionPollCompleted` |
| `formatter-utils.ts` | `escapeHtml`, `closeUnclosedTags`, `smartTruncate`, `formatTimestamp`, `paperModeTag`, `SEVERITY_EMOJI`, constants |

**Migration pattern:** Create a barrel `index.ts` in the `formatters/` directory that re-exports all functions. Existing imports of `telegram-message.formatter` continue to work via the barrel. Then migrate imports to specific files over time.

**Acceptance Criteria:**
- [ ] Each formatter file is under 200 lines
- [ ] Barrel `index.ts` re-exports all functions for backward compatibility
- [ ] All tests pass with zero behavioral changes
- [ ] `telegram-message.formatter.ts` is deleted (replaced by domain files)

---

#### Story 10-8-6: TelegramAlertService Circuit Breaker Extraction (P2)

**Current state:** 734 lines, 19 methods mixing message delivery + circuit breaking
**Target state:** 2 focused services

| New Service | Extracted Responsibility | Key Methods |
|---|---|---|
| `TelegramCircuitBreaker` | Circuit breaker state machine | `getCircuitState`, circuit state tracking, consecutive failure counting, recovery logic |
| `TelegramAlertService` (slimmed) | Message delivery, batching, buffering | `sendMessage`, `handleEvent`, `addToBatch`, `flushBatch`, `bufferMessage`, `drainBuffer`, `reloadConfig` |

**Acceptance Criteria:**
- [ ] `TelegramCircuitBreaker` is under 200 lines
- [ ] `TelegramAlertService` is under 550 lines
- [ ] All tests pass with zero behavioral changes
- [ ] Circuit breaker is independently testable

---

### Items NOT Requiring Changes (Assessed as Cohesive)

These files were assessed during the audit and found to be **single-responsibility despite their size**:

| File | Lines | Reason for No-Action |
|---|---|---|
| `StartupReconciliationService` | 861 | Single responsibility (reconciliation). Cohesive methods. |
| `PolymarketConnector` | 828 | Interface-driven (`IPlatformConnector`). All methods serve platform communication. |
| `DataIngestionService` | 812 | Borderline — watch list. Extract `IngestionSubscriptionManager` if it grows past 900. |
| `PositionCloseService` | 808 | Single responsibility (closing positions). 6 cohesive methods. |
| `KalshiConnector` | 709 | Interface-driven. Same rationale as Polymarket. |
| `SettingsMetadata` | 701 | Pure data file (config declarations). Inherently large. |

---

## Section 5: Implementation Handoff

### Change Scope: Moderate

This change requires:
- **New epic added** to the sprint plan (Epic 10.8)
- **Backlog reorganization** — sequencing 10.8 between 10.7 and 11
- **Story creation** — 6 stories with detailed extraction plans

### Handoff Recipients

| Role | Responsibility |
|------|---------------|
| **Scrum Master (Bob)** | Add Epic 10.8 to `epics.md` and `sprint-status.yaml`. Create story files when ready. |
| **Developer Agent** | Implement each story following the extraction patterns specified. Run full test suite after each story. |
| **Architect** | Post-implementation review — verify module dependency rules are maintained, update `architecture.md` Module Structure section. |

### Implementation Sequence

```
10-8-1 (RiskManagerService)     ← P0, largest/most impactful, do first
    ↓
10-8-2 (ExitMonitorService)     ← P0, depends on clean risk interfaces from 10-8-1
    ↓
10-8-3 (ExecutionService)       ← P1, may consume extracted risk/depth services
    ↓
10-8-4 (DashboardService)       ← P1, consumes all above; split last among services
    ↓
10-8-5 (TelegramFormatter)      ← P2, independent file split, no service dependencies
10-8-6 (TelegramCircuitBreaker) ← P2, independent extraction, can parallel with 10-8-5
```

### Success Criteria

1. **All 2,631+ tests pass** after each story (zero regressions)
2. **No source file exceeds 600 lines** among refactored targets
3. **No test file exceeds 800 lines** among refactored targets
4. **Zero API contract changes** — dashboard and external interfaces unchanged
5. **Module dependency rules maintained** — no forbidden imports introduced
6. **Lad MCP code review** passes for each story

### Post-Refactoring Documentation Updates

After all stories complete:
- Update `architecture.md` Module Structure section with new service files
- Update `CLAUDE.md` Module Structure section
- Update Serena `codebase_structure` memory

---

## Appendix: File Size Distribution (Post-Refactoring Projection)

| File | Before | After (est.) | Change |
|------|--------|-------------|--------|
| `RiskManagerService` | 1,651 | ~500 | -70% |
| `BudgetReservationService` | — | ~300 | new |
| `TradingHaltService` | — | ~150 | new |
| `RiskStateManager` | — | ~250 | new |
| `ExitMonitorService` | 1,438 | ~500 | -65% |
| `ExitExecutionService` | — | ~350 | new |
| `ExitDataSourceService` | — | ~300 | new |
| `ExecutionService` | 1,395 | ~600 | -57% |
| `LegSequencingService` | — | ~250 | new |
| `DepthAnalysisService` | — | ~150 | new |
| `DashboardService` | 1,205 | ~350 | -71% |
| `DashboardOverviewService` | — | ~250 | new |
| `DashboardCapitalService` | — | ~250 | new |
| `DashboardAuditService` | — | ~200 | new |
| `TelegramMessageFormatter` | 789 | deleted | — |
| 7 domain formatter files | — | ~80-150 each | new |
| `TelegramAlertService` | 734 | ~550 | -25% |
| `TelegramCircuitBreaker` | — | ~200 | new |

**Net result:** ~6,400 lines of God Object code → ~14 focused files averaging ~280 lines each. Maximum file size drops from 1,651 to ~600.
