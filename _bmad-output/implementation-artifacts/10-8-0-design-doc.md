# Epic 10.8 God Object Decomposition — Design Document

**Story:** 10-8-0 | **Date:** 2026-03-24 | **Owner:** Winston (Architect)
**Status:** Accepted by Arbi (2026-03-24)

---

## 1. Current State Audit

### 1.1 God Object Summary

| # | God Object | File | Lines | Methods | Constructor Deps | Spec Lines | Tests |
|---|-----------|------|-------|---------|-----------------|-----------|-------|
| 1 | RiskManagerService | `src/modules/risk-management/risk-manager.service.ts` | **1,651** | 36 | 5 | 2,754 | 172 |
| 2 | ExitMonitorService | `src/modules/exit-management/exit-monitor.service.ts` | **1,616** | 10 | **9** | 5,178 (11 files) | 137 |
| 3 | ExecutionService | `src/modules/execution/execution.service.ts` | **1,543** | 8 | **9** | 3,259 + 793 | 104 |
| 4 | DashboardService | `src/dashboard/dashboard.service.ts` | **1,199** | 20 | **12** | 1,435 | 42 |
| 5 | TelegramMessageFormatter | `src/modules/monitoring/formatters/telegram-message.formatter.ts` | **797** | 32 | N/A | 609 | 42 |
| 6 | TelegramAlertService | `src/modules/monitoring/telegram-alert.service.ts` | **734** | 21 | 1 | 1,031 | 82 |

**Total:** 7,540 lines of God Object code, ~15,059 lines of associated test code, 579 tests.

*Note: Method counts exclude constructors. RiskManagerService has 36 entries including constructor (35 methods + constructor). ExitMonitorService has 10 methods + constructor. ExecutionService has 8 entries including constructor (7 methods + constructor). TelegramAlertService has 21 entries including constructor (20 methods + constructor).*

### 1.2 Module Provider Counts (Pre-Decomposition)

| Module | Current Providers | Limit (~8) | Status |
|--------|-----------------|-----------|--------|
| RiskManagementModule | 5 | ~8 | OK |
| ExitManagementModule | 5 | ~8 | OK |
| ExecutionModule | **13** | ~8 | **OVER** (pre-existing) |
| DashboardModule | **10** | ~8 | **OVER** (pre-existing) |
| MonitoringModule | **10** | ~8 | **OVER** (pre-existing) |

### 1.3 Constructor Dependency Audit

| God Object | Deps | Limit (5) | Injected Services |
|-----------|------|----------|-------------------|
| RiskManagerService | 5 | 5 | ConfigService, EventEmitter2, PrismaService, CorrelationTrackerService, EngineConfigRepository |
| ExitMonitorService | **9** | 5 | PositionRepository, OrderRepository, IPlatformConnector×2 (via tokens), EventEmitter2, IRiskManager (via token), ThresholdEvaluatorService, PrismaService, ConfigService |
| ExecutionService | **9** | 5 | IPlatformConnector×2 (via tokens), EventEmitter2, OrderRepository, PositionRepository, ComplianceValidatorService, ConfigService, PlatformHealthService, DataDivergenceService |
| DashboardService | **12** | 5 | PrismaService, ConfigService, PositionEnrichmentService, PositionRepository, EventEmitter2, IRiskManager (via token), EngineConfigRepository, DataIngestionService, DataDivergenceService, PlatformHealthService, ShadowComparisonService, AuditLogService |
| TelegramAlertService | 1 | 5 | ConfigService |

### 1.4 External Consumers (Non-Test)

| God Object | Provided Via | External Consumers |
|-----------|-------------|-------------------|
| RiskManagerService | `RISK_MANAGER_TOKEN` (IRiskManager) | ExitMonitorService, DashboardService, SettingsService (via ModuleRef), ExecutionQueueService, EngineLifecycleService, SingleLegResolutionService, PositionCloseService, StartupReconciliationService, RiskOverrideController*, StressTestService* |
| ExitMonitorService | Direct class | SettingsService (reloadConfig), DashboardModule (via ExitManagementModule export) |
| ExecutionService | `EXECUTION_ENGINE_TOKEN` (IExecutionEngine) | ExecutionQueueService, SettingsService |
| DashboardService | Direct class | DashboardController |
| TelegramMessageFormatter | Stateless functions | TelegramAlertService (imports all 26 formatters) |
| TelegramAlertService | Direct class | EventConsumerService, DailySummaryService, SettingsService |

*\* RiskOverrideController and StressTestService are within the risk-management module — listed for completeness but not cross-module consumers. SettingsService uses `ModuleRef.get(RISK_MANAGER_TOKEN)` at runtime, not `@Inject`. TradingEngineService accesses risk via ExecutionQueueService (indirect consumer). Total: 9 non-test files inject `RISK_MANAGER_TOKEN`.*

### 1.5 Method Inventory by God Object

#### RiskManagerService (36 entries incl. constructor, 1,651 lines)

| Group | Method | Lines | Size | Target Service |
|-------|--------|-------|------|---------------|
| **Config/Bankroll** | constructor | 92–98 | 7 | RiskManagerService (slim) |
| | loadBankrollFromDb | 143–183 | 41 | RiskStateManager |
| | reloadBankroll | 185–216 | 32 | RiskStateManager |
| | reloadConfig | 219–281 | 63 | RiskManagerService (slim) — delegates |
| | buildReloadEnvFallback | 284–293 | 10 | RiskStateManager |
| | getBankrollConfig | 295–308 | 14 | RiskStateManager |
| | getBankrollUsd | 310–312 | 3 | RiskStateManager |
| | getBankrollForMode | 104–111 | 8 | RiskStateManager |
| | validateConfig | 314–374 | 61 | RiskStateManager |
| **Risk Validation** | validatePosition | 573–913 | **341** | RiskManagerService (slim) |
| | determineRejectionReason | 915–923 | 9 | RiskManagerService (slim) |
| | extractPairContext | 925–958 | 34 | RiskManagerService (slim) |
| | fetchTriageWithDtos | 960–982 | 23 | RiskManagerService (slim) |
| | processOverride | 984–1093 | 110 | RiskManagerService (slim) |
| **Budget Reservation** | reserveBudget | 1300–1415 | 116 | BudgetReservationService |
| | commitReservation | 1417–1460 | 44 | BudgetReservationService |
| | releaseReservation | 1462–1500 | 39 | BudgetReservationService |
| | adjustReservation | 1502–1534 | 33 | BudgetReservationService |
| | getReservedPositionSlots | 1631–1639 | 9 | BudgetReservationService |
| | getReservedCapital | 1641–1649 | 9 | BudgetReservationService |
| **Position Lifecycle** | closePosition | 1536–1586 | 51 | BudgetReservationService |
| | releasePartialCapital | 1588–1629 | 42 | BudgetReservationService |
| **Halt Management** | isTradingHalted | 1156–1158 | 3 | TradingHaltService |
| | getActiveHaltReasons | 1160–1162 | 3 | TradingHaltService |
| | haltTrading | 1164–1184 | 21 | TradingHaltService |
| | resumeTrading | 1186–1206 | 21 | TradingHaltService |
| **DB State/Init** | onModuleInit | 113–118 | 6 | RiskStateManager |
| | clearStaleReservations | 120–141 | 22 | BudgetReservationService |
| | initializeStateFromDb | 376–521 | 146 | RiskStateManager |
| | persistState | 523–571 | 49 | RiskStateManager |
| **Daily P&L/Cron** | updateDailyPnl | 1095–1154 | 60 | RiskStateManager |
| | handleMidnightReset | 1235–1269 | 35 | RiskStateManager |
| | recalculateFromPositions | 1208–1233 | 26 | RiskStateManager |
| **State Getters** | getState | 100–102 | 3 | RiskStateManager |
| | getCurrentExposure | 1271–1294 | 24 | RiskStateManager |
| | getOpenPositionCount | 1296–1298 | 3 | RiskStateManager |

#### ExitMonitorService (10 methods + constructor, 1,616 lines)

| Group | Method | Lines | Size | Target Service |
|-------|--------|-------|------|---------------|
| **Config/Init** | constructor | 74–134 | 61 | ExitMonitorService (slim) |
| | reloadConfig | 137–184 | 48 | ExitMonitorService (slim) |
| | onModuleInit | 186–208 | 23 | ExitMonitorService (slim) |
| **Poll Orchestration** | evaluatePositions | 210–344 | 135 | ExitMonitorService (slim) |
| **Per-Position Eval** | evaluatePosition | 346–860 | **515** | ExitMonitorService (slim) |
| **Exit Execution** | executeExit | 862–1417 | **556** | ExitExecutionService |
| | handlePartialExit | 1469–1570 | 102 | ExitExecutionService |
| **Market Data** | getAvailableExitDepth | 1425–1467 | 43 | ExitDataSourceService |
| | getClosePrice | 1572–1594 | 23 | ExitDataSourceService |
| **Data Freshness** | classifyDataSource | 1597–1604 | 8 | ExitDataSourceService |
| | combineDataSources | 1607–1614 | 8 | ExitDataSourceService |

#### ExecutionService (8 entries incl. constructor, 1,543 lines)

| Group | Method | Lines | Size | Target Service |
|-------|--------|-------|------|---------------|
| **Config** | constructor | 81–148 | 68 | ExecutionService (slim) |
| | reloadConfig | 151–174 | 24 | ExecutionService (slim) |
| **Orchestration** | execute | 176–1149 | **974** | ExecutionService (slim) — must refactor to ≤200 |
| **Depth** | getAvailableDepth | 1151–1195 | 45 | DepthAnalysisService |
| **Sequencing** | handleSingleLeg | 1197–1438 | 242 | LegSequencingService |
| | determineSequencing | 1440–1509 | 70 | LegSequencingService |
| **Data Source** | classifyDataSource | 1511–1519 | 9 | DepthAnalysisService |
| | resolveConnectors | 1521–1541 | 21 | LegSequencingService |

#### DashboardService (20 methods, 1,199 lines)

| Group | Method | Lines | Size | Target Service |
|-------|--------|-------|------|---------------|
| **Overview/Health** | getOverview | 65–163 | 99 | DashboardOverviewService |
| | getHealth | 205–252 | 48 | DashboardOverviewService |
| | getLatestHealthLogs | 1146–1152 | 7 | DashboardOverviewService |
| | computeCompositeHealth | 1154–1161 | 8 | DashboardOverviewService |
| | getAlerts | 1023–1053 | 31 | DashboardOverviewService |
| | getShadowComparisons | 1164–1174 | 11 | DashboardOverviewService |
| | getShadowSummary | 1177–1197 | 21 | DashboardOverviewService |
| **Position Listing** | getPositions | 254–484 | 231 | DashboardService (slim) |
| | getPositionById | 486–555 | 70 | DashboardService (slim) |
| **Position Detail** | getPositionDetails | 567–754 | 188 | DashboardAuditService |
| **Bankroll** | getBankrollConfig | 165–167 | 3 | DashboardCapitalService |
| | updateBankroll | 169–203 | 35 | DashboardCapitalService |
| **Capital/P&L** | computeCapitalBreakdown | 888–1007 | 120 | DashboardCapitalService |
| | computeModeCapital | 857–886 | 30 | DashboardCapitalService |
| | computeRealizedPnl | 1061–1144 | 84 | DashboardCapitalService |
| | computeTimeHeld | 1009–1021 | 13 | DashboardCapitalService |
| **DTO Mapping** | mapExecutionMetadata | 758–784 | 27 | DashboardAuditService |
| | parseAuditDetails | 788–796 | 9 | DashboardAuditService |
| | parseJsonFieldWithEvent | 798–822 | 25 | DashboardAuditService |
| | summarizeAuditEvent | 824–855 | 32 | DashboardAuditService |

#### TelegramMessageFormatter (32 functions, 797 lines)

| Group | Function | Lines | Size | Target File |
|-------|----------|-------|------|-------------|
| **Utilities** | escapeHtml | 18–23 | 6 | formatter-utils.ts |
| | smartTruncate | 29–51 | 23 | formatter-utils.ts |
| | closeUnclosedTags | 56–86 | 31 | formatter-utils.ts |
| | formatTimestamp | 88–90 | 3 | formatter-utils.ts |
| | formatCorrelationFooter | 92–101 | 10 | formatter-utils.ts |
| | paperModeTag | 103–108 | 6 | formatter-utils.ts |
| **Detection** | formatOpportunityIdentified | 112–128 | 17 | detection-formatters.ts |
| **Execution** | formatOrderFilled | 130–158 | 29 | execution-formatters.ts |
| | formatExecutionFailed | 160–179 | 20 | execution-formatters.ts |
| | formatSingleLegExposure | 181–238 | 58 | execution-formatters.ts |
| | formatSingleLegResolved | 240–279 | 40 | execution-formatters.ts |
| | formatAutoUnwind | 759–797 | 39 | execution-formatters.ts |
| **Exit** | formatExitTriggered | 281–313 | 33 | exit-formatters.ts |
| **Risk** | formatLimitApproached | 315–332 | 18 | risk-formatters.ts |
| | formatLimitBreached | 334–350 | 17 | risk-formatters.ts |
| | formatClusterLimitBreached | 628–665 | 38 | risk-formatters.ts |
| | formatAggregateClusterLimitBreached | 667–681 | 15 | risk-formatters.ts |
| | formatBankrollUpdated | 683–700 | 18 | risk-formatters.ts |
| **Platform** | formatPlatformDegraded | 352–375 | 24 | platform-formatters.ts |
| | formatPlatformRecovered | 377–391 | 15 | platform-formatters.ts |
| | formatOrderbookStale | 588–607 | 20 | platform-formatters.ts |
| | formatOrderbookRecovered | 609–626 | 18 | platform-formatters.ts |
| | formatDataDivergence | 702–719 | 18 | platform-formatters.ts |
| **System** | formatTradingHalted | 393–409 | 17 | system-formatters.ts |
| | formatTradingResumed | 411–430 | 20 | system-formatters.ts |
| | formatReconciliationDiscrepancy | 432–453 | 22 | system-formatters.ts |
| | formatSystemHealthCritical | 455–473 | 19 | system-formatters.ts |
| | formatTestAlert | 475–487 | 13 | system-formatters.ts |
| **Resolution** | formatResolutionDivergence | 491–509 | 19 | resolution-formatters.ts |
| | formatResolutionPollCompleted | 511–539 | 29 | resolution-formatters.ts |
| | formatCalibrationCompleted | 541–584 | 44 | resolution-formatters.ts |
| | formatShadowDailySummary | 723–757 | 35 | resolution-formatters.ts |

#### TelegramAlertService (21 entries incl. constructor, 734 lines)

| Group | Method | Lines | Size | Target Service |
|-------|--------|-------|------|---------------|
| **Init/Config** | constructor | 266–284 | 19 | TelegramAlertService (slim) |
| | onModuleInit | 286–301 | 16 | TelegramAlertService (slim) |
| | reloadConfig | 304–327 | 24 | TelegramCircuitBreaker |
| | isEnabled | 329–331 | 3 | TelegramAlertService (slim) |
| | getBufferSize | 333–335 | 3 | TelegramCircuitBreaker |
| | getBufferContents | 337–339 | 3 | TelegramCircuitBreaker |
| **Circuit Breaker** | getCircuitState | 341–350 | 10 | TelegramCircuitBreaker |
| | sendMessage | 356–393 | 38 | TelegramCircuitBreaker |
| | enqueueAndSend | 398–452 | 55 | TelegramCircuitBreaker |
| | bufferMessage | 650–658 | 9 | TelegramCircuitBreaker |
| | evictLowestPriority | 660–685 | 26 | TelegramCircuitBreaker |
| | triggerBufferDrain | 687–694 | 8 | TelegramCircuitBreaker |
| | drainBuffer | 696–733 | 38 | TelegramCircuitBreaker |
| **Event Dispatch** | sendEventAlert | 462–489 | 28 | TelegramAlertService (slim) |
| | handleEvent | 493–517 | 25 | TelegramAlertService (slim) |
| | handleTestAlert | 624–646 | 23 | TelegramAlertService (slim) |
| **Batching** | addToBatch | 521–549 | 29 | TelegramAlertService (slim) |
| | flushBatch | 551–562 | 12 | TelegramAlertService (slim) |
| | consolidateMessages | 564–589 | 26 | TelegramAlertService (slim) |
| | truncateHtmlSafe | 591–596 | 6 | TelegramAlertService (slim) |
| | onModuleDestroy | 598–617 | 20 | TelegramAlertService (slim) |

---

## 2. Method-to-Service Allocation Tables

### 2.1 RiskManagerService → 4 Services

#### BudgetReservationService (~320 lines)

**Responsibilities:** Atomic budget reservation lifecycle, position close/partial capital release, reservation bookkeeping.

| Method | Size | Notes |
|--------|------|-------|
| reserveBudget | 116 | Core — validates + reserves atomically |
| commitReservation | 44 | Reservation → committed |
| releaseReservation | 39 | Reservation → released |
| adjustReservation | 33 | Depth-aware capital adjustment |
| closePosition | 51 | Position CLOSED → return capital + P&L |
| releasePartialCapital | 42 | EXIT_PARTIAL → partial capital return |
| clearStaleReservations | 22 | Startup cleanup |
| getReservedPositionSlots | 9 | Query helper |
| getReservedCapital | 9 | Query helper |
| **Total method lines** | **365** | + imports/state/boilerplate ≈ **~320 lines** |

**State owned:** `reservations` Map, `paperActivePairIds` Set.

**Justification for retained responsibilities:** Budget reservation is a single atomic concern — splitting reserve/commit/release across services would break the atomicity guarantee. Position close and partial capital release are budget operations (return capital to pool) and must be co-located with the reservation map.

#### TradingHaltService (~100 lines)

**Responsibilities:** Halt state management, halt/resume with multi-reason support, event emission on state changes.

| Method | Size | Notes |
|--------|------|-------|
| isTradingHalted | 3 | Read from state |
| getActiveHaltReasons | 3 | Read from state |
| haltTrading | 21 | Add reason + emit event |
| resumeTrading | 21 | Remove reason + emit event |
| **Total method lines** | **48** | + imports/state ≈ **~100 lines** |

**State access protocol:** TradingHaltService receives a reference to the `ModeRiskState` objects from RiskStateManager via getter methods (`RiskStateManager.getState(isPaper)`). It reads/writes `activeHaltReasons` on the shared state reference directly. This is safe because: (a) both services are in the same module, (b) halt mutations are single-threaded (Node.js event loop), and (c) `persistState()` is called by RiskStateManager after any halt state change via the event emission path (TradingHaltService emits `system.trading.halted` → RiskStateManager subscribes and persists). The constructor receives RiskStateManager as a dependency and caches the state references during initialization.

**Design note:** Small by design — halt management is a narrow concern. The alternative (merging into RiskStateManager) was rejected because halt state changes emit events and have different access patterns than state persistence.

#### RiskStateManager (~400 lines)

**Responsibilities:** Risk state persistence to/from DB, bankroll management, daily P&L tracking, midnight reset, reconciliation state sync, exposure getters.

| Method | Size | Notes |
|--------|------|-------|
| onModuleInit | 6 | Triggers loadBankrollFromDb + initializeStateFromDb |
| loadBankrollFromDb | 41 | Read bankroll from engine_config |
| reloadBankroll | 32 | Re-read bankroll + recalculate limits |
| buildReloadEnvFallback | 10 | Env var fallback for config |
| getBankrollConfig | 14 | Expose bankroll + timestamp |
| getBankrollUsd | 3 | Single-value getter |
| getBankrollForMode | 8 | Live/paper bankroll selector |
| validateConfig | 61 | Startup config validation |
| initializeStateFromDb | 146 | Full state restoration from DB |
| persistState | 49 | Serialize state to DB |
| updateDailyPnl | 60 | P&L delta + limit check + emit |
| handleMidnightReset | 35 | Cron — reset daily counters |
| recalculateFromPositions | 26 | Reconciliation sync |
| getCurrentExposure | 24 | Compute exposure snapshot |
| getOpenPositionCount | 3 | Read from state |
| getState | 3 | Return raw state object (shared ref for TradingHaltService, BudgetReservationService) |
| decrementOpenPositions | ~8 | Called by BudgetReservationService.closePosition — decrements openPositionCount + totalCapitalDeployed |
| adjustCapitalDeployed | ~6 | Called by BudgetReservationService.releasePartialCapital — decrements totalCapitalDeployed only |
| **Total method lines** | **~535** | + imports/state/types ≈ **~420 lines** |

**State owned:** `liveState`, `paperState` (ModeRiskState), `config` (RiskConfig), `bankrollUpdatedAt`.

**State mutation API for BudgetReservationService:** `closePosition` and `releasePartialCapital` in BudgetReservationService need to modify `openPositionCount` and `totalCapitalDeployed` on `ModeRiskState`. Rather than mutating shared references directly, BudgetReservationService calls explicit RiskStateManager methods: `decrementOpenPositions(capitalReturned, isPaper)` and `adjustCapitalDeployed(capitalDelta, isPaper)`, followed by `updateDailyPnl(pnlDelta, isPaper)` and `persistState(isPaper)`. This keeps state mutations traceable.

**Justification:** State persistence and bankroll management are tightly coupled — `initializeStateFromDb` restores bankroll, daily P&L, halt reasons, and position counts as a single atomic operation. Splitting further would require passing partial state between services during initialization.

#### Slimmed RiskManagerService (~500 lines)

**Role:** Facade implementing `IRiskManager`. Delegates to sub-services. Owns risk validation logic directly (cannot be extracted — it's a single decision flow that references all sub-service state).

| Method | Size | Notes |
|--------|------|-------|
| constructor | 7 | Injects 3 sub-services + deps |
| reloadConfig | ~30 | Delegates to RiskStateManager + sub-services |
| validatePosition | **341** | Core risk validation — retained |
| determineRejectionReason | 9 | Helper for validatePosition |
| extractPairContext | 34 | Helper for validatePosition |
| fetchTriageWithDtos | 23 | Helper for validatePosition |
| processOverride | 110 | Operator override flow |
| + delegation methods | ~45 | ~15 thin wrappers (3 lines each) |
| **Total method lines** | **~599** | + imports ≈ **~500 lines** |

**Why validatePosition stays:** It reads state from RiskStateManager, checks reservations from BudgetReservationService, and queries halt state from TradingHaltService in a single decision flow. Moving it to any sub-service would create circular dependencies.

**Concrete refactoring plan for 10-8-1:** Extract `validatePosition` internal phases into private helpers within the same file: (a) `checkHaltAndCooldown` (~40 lines — halt state, cooldown, trading window), (b) `checkPositionLimits` (~80 lines — pair limits, cluster limits, max open), (c) `checkBudgetAndSizing` (~120 lines — bankroll %, reservation, depth sizing), (d) `buildValidationResult` (~50 lines — approval/rejection assembly). The 341-line method becomes a ~50-line orchestrator calling 4 helpers. This does not reduce the *file* line count, but brings the primary method under the ~200-line readability threshold. To bring the *file* under ~400 lines, consider extracting `processOverride` (110 lines) to a separate `RiskOverrideService` — evaluate during 10-8-1 implementation.

**Delegation pattern:** Each IRiskManager method that moved to a sub-service gets a 3-line delegator:
```typescript
async closePosition(...args) { return this.budgetService.closePosition(...args); }
```

#### Estimated Post-Decomposition Sizes

| Service | Est. Lines | Epic Target | CLAUDE.md Target | Status |
|---------|-----------|-------------|-----------------|--------|
| BudgetReservationService | ~320 | ≤600 | ~300 | ~OK |
| TradingHaltService | ~100 | ≤600 | ~300 | OK |
| RiskStateManager | ~420 | ≤600 | ~300 | Above preferred — justified (see above) |
| RiskManagerService (slim) | ~500 | ≤600 | ~300 | Above preferred — refactoring plan in 10-8-1 |

**Note:** RiskStateManager (~420) and slimmed RiskManagerService (~500) exceed the ~300 preferred target but meet the ≤600 epic minimum. RiskStateManager's overage is justified by the atomic initialization requirement. For the slim service, `validatePosition` (341 lines) is the bottleneck — see concrete refactoring plan above. If `processOverride` (110 lines) is extracted to a `RiskOverrideService`, the slim file drops to ~390, near the ~400 file limit.

---

### 2.2 ExitMonitorService → 3 Services

#### ExitExecutionService (~450 lines)

**Responsibilities:** Chunked dual-leg exit order submission, P&L computation per chunk, partial exit handling.

| Method | Size | Notes |
|--------|------|-------|
| executeExit | **556** | Must refactor to ~350 by extracting chunk-loop helpers |
| handlePartialExit | 102 | EXIT_PARTIAL status transition |
| **Total method lines** | **658** | Post-refactor ≈ **~430 lines** |

**Refactoring required:** `executeExit` at 556 lines must be decomposed during 10-8-2. Extract: (a) chunk calculation helper (~80 lines), (b) per-leg order submission helper (~100 lines), (c) P&L accumulation helper (~60 lines), (d) position state transition helper (~80 lines). Target: `executeExit` orchestrator ≤200 lines + 4 private helpers. Total file stays ~430 (methods are extracted within the file, not removed).

#### ExitDataSourceService (~140 lines)

**Responsibilities:** Market data fetching for exits, depth analysis, data source classification, close price lookup.

| Method | Size | Notes |
|--------|------|-------|
| getAvailableExitDepth | 43 | Depth from order book |
| getClosePrice | 23 | **Owned here** — price lookup for exit orders |
| classifyDataSource | 8 | WS vs polling classification |
| combineDataSources | 8 | Merge dual data sources |
| **Total method lines** | **82** | + imports/types ≈ **~140 lines** |

**Design note:** This is intentionally thin. It isolates the data-fetching concern from exit execution logic. Both ExitExecutionService and ExitMonitorService (slim) inject this service for data access. `getClosePrice` lives here (data-fetching concern); ExitExecutionService calls `this.exitDataSourceService.getClosePrice()` during exit order preparation.

#### Slimmed ExitMonitorService (~500 lines)

**Role:** Poll loop orchestration and per-position evaluation. Injects ExitExecutionService + ExitDataSourceService.

| Method | Size | Notes |
|--------|------|-------|
| constructor | ~30 | Reduced from 61 (config read stays) |
| reloadConfig | 48 | Config hot-reload |
| onModuleInit | 23 | Scheduler setup |
| evaluatePositions | 135 | Poll loop orchestrator |
| evaluatePosition | **515** | Must refactor to ~300 |
| **Total method lines** | **751** | Post-refactor ≈ **~500 lines** |

**Concrete refactoring plan for 10-8-2:** `evaluatePosition` at 515 lines must be decomposed. Extract private helpers: (a) `buildCriteriaInputs` (~120 lines — fetch order books, compute edge, build threshold inputs), (b) `performShadowComparison` (~80 lines — shadow evaluation + event emission), (c) `recalculateAndPersistEdge` (~60 lines — edge recalculation + DB persistence). Target: `evaluatePosition` orchestrator ≤200 lines + 3 private helpers. Total file stays ~500 (methods extracted within file).

#### Estimated Post-Decomposition Sizes

| Service | Est. Lines | Epic Target | Status |
|---------|-----------|-------------|--------|
| ExitExecutionService | ~430 | ≤500 | OK |
| ExitDataSourceService | ~140 | ≤500 | OK |
| ExitMonitorService (slim) | ~500 | ≤500 | Borderline — refactoring plan above |

---

### 2.3 ExecutionService → 3 Services

#### LegSequencingService (~370 lines)

**Responsibilities:** Single-leg exposure handling, adaptive leg sequencing, connector resolution.

| Method | Size | Notes |
|--------|------|-------|
| handleSingleLeg | 242 | Full single-leg resolution flow |
| determineSequencing | 70 | Latency-based primary leg selection |
| resolveConnectors | 21 | Platform → connector mapping |
| **Total method lines** | **333** | + imports/types ≈ **~370 lines** |

#### DepthAnalysisService (~150 lines)

**Responsibilities:** Order book depth checking, data source classification, depth sufficiency validation.

| Method | Size | Notes |
|--------|------|-------|
| getAvailableDepth | 45 | Core depth check |
| classifyDataSource | 9 | WS vs polling |
| + extracted from execute() | ~60 | Depth validation phases from execute() |
| **Total method lines** | **~114** | + imports ≈ **~150 lines** |

#### Slimmed ExecutionService (~400 lines)

**Role:** Coordinator implementing `IExecutionEngine`. The `execute()` method orchestrates phases by delegating to DepthAnalysisService (depth), LegSequencingService (sequencing), and calling platform connectors directly for order submission.

| Method | Size | Notes |
|--------|------|-------|
| constructor | ~40 | Reduced config validation |
| reloadConfig | 24 | Hot-reload |
| execute | **974** → ~200 | Major refactoring — extract phases |
| **Total method lines** | **~264** | + imports ≈ **~400 lines** |

**Concrete refactoring plan for 10-8-3:** `execute()` at 974 lines is the worst God Method in the codebase. Extract into phases:
- (a) Compliance validation → already delegated to `ComplianceValidatorService` (~no change)
- (b) Depth analysis → delegated to `DepthAnalysisService.getAvailableDepth()` + depth validation phases (~60 lines extracted)
- (c) `submitOrderPair` private helper (~150 lines — dual-leg order creation, API calls, fill verification)
- (d) `createPositionFromFills` private helper (~120 lines — position record assembly, DB write)
- (e) `emitExecutionEvents` private helper (~80 lines — event payload construction, emission)
- (f) `handleExecutionFailure` private helper (~100 lines — error classification, reservation release, single-leg check)

Target: `execute()` orchestrator ≤200 lines calling 4 private helpers + 2 injected services. The 974→200 reduction is achievable because the method's control flow is a linear pipeline (validate → size → submit → record → emit) with error handling at each stage. Shared local state between phases: `reservation`, `opportunity`, `connectors`, `fillResults` — pass as parameters to each helper. Total file stays ~400 (extracted code remains in-file as private methods).

#### Estimated Post-Decomposition Sizes

| Service | Est. Lines | Epic Target | Status |
|---------|-----------|-------------|--------|
| LegSequencingService | ~370 | ≤500 | OK |
| DepthAnalysisService | ~150 | ≤500 | OK |
| ExecutionService (slim) | ~400 | ≤500, execute() ≤200 | OK (with refactoring) |

---

### 2.4 DashboardService → 4 Services

#### DashboardOverviewService (~280 lines)

**Responsibilities:** System overview, health status, alerts, shadow mode summaries.

| Method | Size | Notes |
|--------|------|-------|
| getOverview | 99 | Main dashboard view |
| getHealth | 48 | Platform + system health |
| getLatestHealthLogs | 7 | Recent health log entries |
| computeCompositeHealth | 8 | Aggregate health score |
| getAlerts | 31 | Active alerts list |
| getShadowComparisons | 11 | Shadow comparison data |
| getShadowSummary | 21 | Shadow daily summary |
| **Total method lines** | **225** | + imports/deps ≈ **~280 lines** |

#### DashboardCapitalService (~320 lines)

**Responsibilities:** Capital breakdown computation, P&L calculation, bankroll management.

| Method | Size | Notes |
|--------|------|-------|
| computeCapitalBreakdown | 120 | Full capital analysis |
| computeModeCapital | 30 | Per-mode (live/paper) capital |
| computeRealizedPnl | 84 | Date-range P&L computation |
| computeTimeHeld | 13 | Duration calculation |
| getBankrollConfig | 3 | Delegates to IRiskManager |
| updateBankroll | 35 | Bankroll update + audit |
| **Total method lines** | **285** | + imports ≈ **~320 lines** |

#### DashboardAuditService (~320 lines)

**Responsibilities:** Position detail with full audit trail, DTO mapping, audit log parsing.

| Method | Size | Notes |
|--------|------|-------|
| getPositionDetails | 188 | Full position detail + orders + audit |
| mapExecutionMetadata | 27 | JSON → ExecutionMetadata DTO |
| parseAuditDetails | 9 | Safe JSON parse for audit details |
| parseJsonFieldWithEvent | 25 | Generic JSON field parser with event |
| summarizeAuditEvent | 32 | Audit event → human summary |
| AUDIT_TRAIL_EVENT_WHITELIST | 9 | Static constant |
| **Total method lines** | **290** | + imports ≈ **~320 lines** |

#### Slimmed DashboardService (~380 lines)

**Role:** Facade for DashboardController. Owns position listing (the largest query surface). Delegates to sub-services.

| Method | Size | Notes |
|--------|------|-------|
| constructor | 15 | Injects 3 sub-services + deps |
| getPositions | **231** | Complex query with filters/sorting |
| getPositionById | 70 | Single position lookup |
| + delegation methods | ~40 | Thin wrappers to sub-services |
| **Total method lines** | **~356** | + imports ≈ **~380 lines** |

**Why getPositions stays:** It's the primary position list endpoint with complex filtering (status, mode, date range, sorting). Moving it would just shift the dependency problem. The facade pattern keeps DashboardController's injection stable.

#### Estimated Post-Decomposition Sizes

| Service | Est. Lines | Epic Target | Status |
|---------|-----------|-------------|--------|
| DashboardOverviewService | ~280 | ≤400 | OK |
| DashboardCapitalService | ~320 | ≤400 | OK |
| DashboardAuditService | ~320 | ≤400 | OK |
| DashboardService (slim) | ~380 | ≤400 | OK |

---

### 2.5 TelegramMessageFormatter → 7 Domain Files + Utils

All files in `src/modules/monitoring/formatters/`:

| File | Formatters | Est. Lines |
|------|-----------|-----------|
| `formatter-utils.ts` | escapeHtml, smartTruncate, closeUnclosedTags, formatTimestamp, formatCorrelationFooter, paperModeTag, constants | ~110 |
| `detection-formatters.ts` | formatOpportunityIdentified | ~30 (+imports) |
| `execution-formatters.ts` | formatOrderFilled, formatExecutionFailed, formatSingleLegExposure, formatSingleLegResolved, formatAutoUnwind | ~200 |
| `exit-formatters.ts` | formatExitTriggered | ~45 (+imports) |
| `risk-formatters.ts` | formatLimitApproached, formatLimitBreached, formatClusterLimitBreached, formatAggregateClusterLimitBreached, formatBankrollUpdated | ~120 |
| `platform-formatters.ts` | formatPlatformDegraded, formatPlatformRecovered, formatOrderbookStale, formatOrderbookRecovered, formatDataDivergence | ~110 |
| `system-formatters.ts` | formatTradingHalted, formatTradingResumed, formatReconciliationDiscrepancy, formatSystemHealthCritical, formatTestAlert | ~105 |
| `resolution-formatters.ts` | formatResolutionDivergence, formatResolutionPollCompleted, formatCalibrationCompleted, formatShadowDailySummary | ~140 |
| `index.ts` | Barrel re-exports from all domain files | ~20 |

All files well under the ≤200 target. The existing `telegram-message.formatter.ts` is replaced by these 9 files.

---

### 2.6 TelegramAlertService → 2 Services

#### TelegramCircuitBreaker (~220 lines)

**Responsibilities:** HTTP transport, circuit breaker state machine, failure buffer, priority-based eviction, buffer drain.

| Method | Size | Notes |
|--------|------|-------|
| constructor | ~10 | Config values |
| reloadConfig | 24 | Hot-reload CB settings |
| getCircuitState | 10 | CLOSED/OPEN/HALF_OPEN |
| sendMessage | 38 | Single HTTP send attempt |
| enqueueAndSend | 55 | CB check → send → buffer on failure |
| bufferMessage | 9 | Add to priority buffer |
| evictLowestPriority | 26 | Buffer overflow handling |
| triggerBufferDrain | 8 | Initiate async drain |
| drainBuffer | 38 | Drain buffer with retry |
| getBufferSize | 3 | Buffer length |
| getBufferContents | 3 | Buffer snapshot |
| **Total method lines** | **224** | + imports/types/state (~60 lines) ≈ **~285 lines** |

**State owned:** `buffer`, `consecutiveFailures`, `circuitOpenUntil`, `lastRetryAfterMs`, `draining`.

#### Slimmed TelegramAlertService (~530 lines)

**Role:** Event dispatch, message batching, Telegram-specific business logic. Injects TelegramCircuitBreaker for transport.

| Method | Size | Notes |
|--------|------|-------|
| constructor | 10 | Injects TelegramCircuitBreaker + ConfigService |
| onModuleInit | 16 | Enable/disable check |
| isEnabled | 3 | Status getter |
| sendEventAlert | 28 | Formatter registry dispatch |
| handleEvent | 25 | Format + batch + error fallback |
| handleTestAlert | 23 | @Cron daily test |
| addToBatch | 29 | Batch window management |
| flushBatch | 12 | Timer-based batch flush |
| consolidateMessages | 26 | Multi-message consolidation |
| truncateHtmlSafe | 6 | Safe HTML truncation |
| onModuleDestroy | 20 | Flush all pending batches |
| **Total method lines** | **198** | + FORMATTER_REGISTRY (103) + TELEGRAM_ELIGIBLE_EVENTS (34) + imports ≈ **~530 lines** |

**Note:** The `FORMATTER_REGISTRY` and `TELEGRAM_ELIGIBLE_EVENTS` constants account for ~137 lines. These are data-only and stay in this file as the registry owner. Story 10-8-5 (formatter split) will update the import paths but won't move the registry.

**Registry extraction option (evaluate during 10-8-6):** Extract `FORMATTER_REGISTRY` (103 lines) and `TELEGRAM_ELIGIBLE_EVENTS` (34 lines) to `telegram-registry.constants.ts`. This drops the slim service from ~530 to ~393, under the ~400 file limit. Trade-off: one more file, but cleaner separation of data from behavior.

#### Estimated Post-Decomposition Sizes

| Service | Est. Lines | Epic Target | Status |
|---------|-----------|-------------|--------|
| TelegramCircuitBreaker | ~285 | ≤200 | **OVER** — requires trimming during 10-8-6 (inline state declarations, compact error handling) or adjust target to ≤300 |
| TelegramAlertService (slim) | ~530 (~393 with registry extraction) | ≤550 | OK (under ~400 file limit if registries extracted) |

---

## 3. Constructor Dependency Split Tables

### 3.1 RiskManagerService Decomposition

| New Service | Constructor Dependencies | Count | Under 5? |
|------------|------------------------|-------|----------|
| BudgetReservationService | EventEmitter2, PrismaService, RiskStateManager | 3 | YES |
| TradingHaltService | EventEmitter2, RiskStateManager | 2 | YES |
| RiskStateManager | ConfigService, PrismaService, EventEmitter2, EngineConfigRepository, CorrelationTrackerService | 5 | YES |
| RiskManagerService (slim) | BudgetReservationService, TradingHaltService, RiskStateManager, EventEmitter2, CorrelationTrackerService | 5 | YES |

**Cross-service deps introduced:** RiskManagerService (slim) → BudgetReservationService, TradingHaltService, RiskStateManager. All within same module — direct injection, no interface needed.

### 3.2 ExitMonitorService Decomposition

| New Service | Constructor Dependencies | Count | Under 5? |
|------------|------------------------|-------|----------|
| ExitExecutionService | OrderRepository, IPlatformConnector×2, EventEmitter2, IRiskManager | 5 | YES |
| ExitDataSourceService | IPlatformConnector×2, ConfigService | 3 | YES |
| ExitMonitorService (slim) | PositionRepository, ExitExecutionService, ExitDataSourceService, ThresholdEvaluatorService, ConfigService | 5 | YES |

**Deps reduced from 9 → max 5.** PrismaService removed from ExitMonitorService entirely (only needed by ExitExecutionService for position updates — but those go through repositories).

### 3.3 ExecutionService Decomposition

| New Service | Constructor Dependencies | Count | Under 5? |
|------------|------------------------|-------|----------|
| LegSequencingService | IPlatformConnector×2, EventEmitter2, OrderRepository, PositionRepository | 5 | YES |
| DepthAnalysisService | IPlatformConnector×2, DataDivergenceService, PlatformHealthService | 4 | YES |
| ExecutionService (slim) | LegSequencingService, DepthAnalysisService, ComplianceValidatorService, EventEmitter2, ConfigService | 5 | YES |

**Deps reduced from 9 → max 5.** PlatformHealthService moves to DepthAnalysisService (health affects depth decisions). OrderRepository and PositionRepository move to LegSequencingService (single-leg handling creates/updates records).

### 3.4 DashboardService Decomposition

| New Service | Constructor Dependencies | Count | Under 5? |
|------------|------------------------|-------|----------|
| DashboardOverviewService | IRiskManager, PlatformHealthService, DataIngestionService, ShadowComparisonService, DataDivergenceService | 5 | YES |
| DashboardCapitalService | IRiskManager, PositionRepository, EventEmitter2, EngineConfigRepository | 4 | YES |
| DashboardAuditService | PrismaService, AuditLogService, PositionEnrichmentService | 3 | YES |
| DashboardService (slim) | DashboardOverviewService, DashboardCapitalService, DashboardAuditService, PositionRepository, ConfigService | 5 | YES |

**Deps reduced from 12 → max 5.** DataDivergenceService used only by getHealth → moves to DashboardOverviewService (replaces PrismaService, which is not needed — all queries go through repositories or injected services). EventEmitter2 moves to DashboardCapitalService (needed by `updateBankroll` event emission).

### 3.5 TelegramAlertService Decomposition

| New Service | Constructor Dependencies | Count | Under 5? |
|------------|------------------------|-------|----------|
| TelegramCircuitBreaker | ConfigService | 1 | YES |
| TelegramAlertService (slim) | TelegramCircuitBreaker, ConfigService | 2 | YES |

### 3.6 Module Provider Counts Post-Decomposition

| Module | Before | After | Delta | Under ~8? |
|--------|--------|-------|-------|----------|
| RiskManagementModule | 5 | 8 | +3 (BudgetReservation, TradingHalt, RiskStateManager) | YES |
| ExitManagementModule | 5 | 7 | +2 (ExitExecution, ExitDataSource) | YES |
| ExecutionModule | **13** | **15** | +2 (LegSequencing, DepthAnalysis) | **NO** (pre-existing problem) |
| DashboardModule | **10** | **13** | +3 (Overview, Capital, Audit) | **NO** (pre-existing problem) |
| MonitoringModule | **10** | **11** | +1 (TelegramCircuitBreaker) | **NO** (pre-existing problem) |

**AC #3 exception — pre-existing provider overages:** ExecutionModule (13→15), DashboardModule (10→13), and MonitoringModule (10→11) already exceed the ~8 limit before this epic. The decomposition adds +2, +3, +1 respectively. These are accepted exceptions because:
1. The overages are pre-existing (not introduced by decomposition)
2. Reducing them requires module restructuring beyond this epic's scope (zero functional changes)

**Concrete mitigation plan (post-Epic 10.8 follow-up):**
- **ExecutionModule (15):** Extract `OrderRepository`, `PositionRepository`, `ComplianceValidatorService` to a shared `PersistenceModule` import → reduces to ~12. Further: evaluate splitting single-leg services (SingleLegResolutionService, PositionCloseService, AutoUnwindService) into an `ExecutionRecoveryModule` → target ~8.
- **DashboardModule (13):** Extract `SettingsService`, `EngineConfigRepository`, `ConfigAccessorService` to a shared `ConfigModule` → reduces to ~10. Further: DashboardOverviewService, DashboardCapitalService, DashboardAuditService could move to a `DashboardServicesModule` that DashboardModule imports → target ~8.
- **MonitoringModule (11):** Already near limit. Extract `MatchAprUpdaterService` and calendar-related services to a `ContractLifecycleModule` if they don't belong in monitoring → target ~8.

These follow-up stories should be added to the backlog after Epic 10.8 completes.

### 3.7 Circular DI Risk Assessment

No circular dependencies introduced:
- **RiskManager sub-services:** Linear dependency chain: RiskManagerService (slim) → {BudgetReservation, TradingHalt, RiskStateManager}. No sub-service depends on RiskManagerService.
- **ExitMonitor sub-services:** ExitMonitorService (slim) → {ExitExecution, ExitDataSource}. No circular.
- **Execution sub-services:** ExecutionService (slim) → {LegSequencing, DepthAnalysis}. No circular.
- **Dashboard sub-services:** DashboardService (slim) → {Overview, Capital, Audit}. No circular.
- **Cross-module:** ExitExecutionService → IRiskManager (via token). This is the same cross-module pattern that exists today — no change.

---

## 4. Test File Mapping Plan

### 4.1 RiskManagerService Tests (2,754 lines, 172 tests → 3 spec files)

Current: `risk-manager.service.spec.ts` (monolithic)

| Target Spec File | Describe Blocks | Est. Lines | Est. Tests |
|-----------------|----------------|-----------|-----------|
| `budget-reservation.service.spec.ts` | reserveBudget, commitReservation, releaseReservation, adjustReservation, closePosition, releasePartialCapital, getReservedPositionSlots, getReservedCapital, clearStaleReservations | ~750 | ~50 |
| `trading-halt.service.spec.ts` | halt management, halt state persistence | ~200 | ~15 |
| `risk-state-manager.service.spec.ts` | config validation, database persistence, startup state restoration, daily P&L, midnight reset, recalculateFromPositions, getCurrentExposure, bankroll getters, decrementOpenPositions, adjustCapitalDeployed | ~850 | ~52 |
| `risk-manager.service.spec.ts` (slim) | validatePosition, processOverride, delegation smoke tests | ~750 | ~55 |
| **Shared test helper** | `risk-test-helpers.ts` | ~250 | — |

*Test arithmetic: 50+15+52+55 = 172 tests (matches original). Line estimates include new boilerplate (imports, `beforeEach`, module setup) per file, so total spec lines (~2,550 + ~250 helper) will exceed original 2,754 — expected for split files.*

**Shared fixtures to extract:** `createMockConfigService()`, `mockPrismaService`, `mockEventEmitter`, `mockEngineConfigRepository` — used across all 3+ spec files. Extract to `risk-test-helpers.ts`.

### 4.2 ExitMonitorService Tests (5,178 lines across 11 files, 137 tests)

Tests are **already split** into domain-specific files. Mapping:

| Current Spec File | Lines | Target Service | Action |
|-------------------|-------|---------------|--------|
| exit-monitor-core.spec.ts | 326 | ExitMonitorService (slim) | Keep |
| exit-monitor-criteria.integration.spec.ts | 615 | ExitMonitorService (slim) | Keep |
| exit-monitor-data-source.spec.ts | 290 | ExitDataSourceService | Move |
| exit-monitor-depth-check.spec.ts | 670 | ExitDataSourceService | Move |
| exit-monitor-chunking.spec.ts | 962 | ExitExecutionService | Move |
| exit-monitor-partial-fills.spec.ts | 379 | ExitExecutionService | Move |
| exit-monitor-partial-reevaluation.spec.ts | 630 | ExitExecutionService | Move |
| exit-monitor-pnl-persistence.spec.ts | 454 | ExitExecutionService | Move |
| exit-monitor-pricing.spec.ts | 228 | ExitDataSourceService | Move |
| exit-monitor-paper-mode.spec.ts | 395 | Split across services | Split |
| exit-monitor-shadow-emission.spec.ts | 229 | ExitMonitorService (slim) | Keep |

**Shared helper:** `exit-monitor.test-helpers.ts` (226 lines) — already exists, update `createExitMonitorTestModule` to wire new sub-services.

### 4.3 ExecutionService Tests (3,259 + 793 lines, 104+ tests)

Current: `execution.service.spec.ts` (monolithic) + `dual-leg-depth-gate.spec.ts`

| Target Spec File | Source Describe Blocks | Est. Lines |
|-----------------|----------------------|-----------|
| `leg-sequencing.service.spec.ts` | handleSingleLeg, determineSequencing | ~600 |
| `depth-analysis.service.spec.ts` | getAvailableDepth, classifyDataSource + dual-leg-depth-gate.spec.ts | ~900 |
| `execution.service.spec.ts` (slim) | execute orchestration, config validation, reloadConfig | ~1,200 |

### 4.4 DashboardService Tests (1,435 lines, 42 tests)

Current: `dashboard.service.spec.ts` + `settings-audit-backfill.spec.ts` (202 lines)

| Target Spec File | Source Methods | Est. Lines |
|-----------------|---------------|-----------|
| `dashboard-overview.service.spec.ts` | getOverview, getHealth, getShadow*, getAlerts | ~400 |
| `dashboard-capital.service.spec.ts` | computeCapitalBreakdown, computeRealizedPnl, updateBankroll + settings-audit-backfill | ~500 |
| `dashboard-audit.service.spec.ts` | getPositionDetails, parseAuditDetails, summarizeAuditEvent | ~300 |
| `dashboard.service.spec.ts` (slim) | getPositions, getPositionById, delegation tests | ~400 |

### 4.5 TelegramMessageFormatter Tests (609 lines, 42 tests)

Tests split to match domain files. Each domain spec file imports only the relevant formatters + utils.

### 4.6 TelegramAlertService Tests (1,031 lines, 82 tests)

| Target Spec File | Source Blocks | Est. Lines |
|-----------------|--------------|-----------|
| `telegram-circuit-breaker.spec.ts` | circuit breaker, sendMessage, buffer, drain | ~500 |
| `telegram-alert.service.spec.ts` (slim) | sendEventAlert, batching, test alert, init | ~550 |

### 4.7 Integration Tests That Must Remain Intact

- **Paper/Live boundary tests** (`src/common/testing/paper-live-boundary/`): `risk.spec.ts`, `exit.spec.ts`, `execution.spec.ts`, `dashboard.spec.ts`, `monitoring.spec.ts` — these test the full service contract including mode isolation. Update constructor calls to wire new sub-services but preserve test semantics.
- **Event wiring tests** (`expectEventHandled`): Any `@OnEvent` handler tests must remain wired through the actual EventEmitter2 → handler path. If event emission moves to a sub-service, the wiring test must follow.
- **Financial math property tests** (`financial-math.property.spec.ts`): Tests `reserveBudget` E2E — update to use BudgetReservationService or the facade.

### 4.8 E2E Tests

No `test/e2e/` directory exists. N/A.

---

## 5. Cross-Service Touchpoint Analysis

### 5.1 `closePosition()` Call Chain

```
ExitMonitorService.executeExit()
  → (after successful dual-leg exit)
  → RiskManagerService.closePosition(capitalReturned, pnlDelta, pairId, isPaper)
    → this.getState(isPaper).openPositionCount--
    → this.getState(isPaper).totalCapitalDeployed -= capitalReturned
    → this.updateDailyPnl(pnlDelta, isPaper)
    → this.persistState(isPaper)
    → this.eventEmitter.emit(EVENT_NAMES.BUDGET_RELEASED, ...)  // 'risk.budget.released'
```

**Post-decomposition:**
```
ExitExecutionService.executeExit()
  → IRiskManager.closePosition()  // unchanged cross-module call via interface
    → RiskManagerService.closePosition()  // facade
      → BudgetReservationService.closePosition()
        → RiskStateManager.decrementOpenPositions()  // explicit state mutation
        → RiskStateManager.updateDailyPnl()           // injected
        → RiskStateManager.persistState()              // injected
        → eventEmitter.emit(EVENT_NAMES.BUDGET_RELEASED, ...)  // 'risk.budget.released'
```

**Risk:** BudgetReservationService needs access to RiskStateManager for state mutations and P&L updates. Resolved via constructor injection (same module). State mutations use explicit RiskStateManager methods (`decrementOpenPositions`, `adjustCapitalDeployed`) rather than direct state reference manipulation.

### 5.2 `releasePartialCapital()` Call Chain

```
ExitMonitorService.handlePartialExit()
  → RiskManagerService.releasePartialCapital(capitalReleased, realizedPnl, pairId, isPaper)
    → this.getState(isPaper).totalCapitalDeployed -= capitalReleased
    → this.updateDailyPnl(realizedPnl, isPaper)
    → this.persistState(isPaper)
```

**Post-decomposition:** Same pattern as closePosition — BudgetReservationService → RiskStateManager for state updates.

### 5.3 PnL Accumulation Through Exit Chunking Loop

```
ExitMonitorService.executeExit():
  let accumulatedPnl = new Decimal(0)
  for (chunk of chunks):
    submit kalshi close order → kalshiResult
    submit polymarket close order → polyResult
    chunkPnl = calculate from fill prices
    accumulatedPnl = accumulatedPnl.plus(chunkPnl)

  if (partial):
    handlePartialExit(accumulatedPnl, ...)
      → riskManager.releasePartialCapital(exitedCapital, accumulatedPnl)
  else:
    riskManager.closePosition(totalCapital, accumulatedPnl)
```

**Post-decomposition:** This entire loop moves to ExitExecutionService. The `riskManager` calls remain cross-module via `IRiskManager` interface — no change to the call pattern.

**Transaction boundary:** The chunking loop does NOT use a Prisma transaction — each chunk is a separate order submission with its own DB write. P&L is accumulated in memory and written once at the end via closePosition/releasePartialCapital. This is correct and must be preserved.

### 5.4 Budget Reservation Lifecycle

```
TradingEngineService (core/):
  → ExecutionQueueService.enqueue(opportunity, reservation)
    where reservation = IRiskManager.reserveBudget(request)

ExecutionService.execute():
  → (on success) IRiskManager.commitReservation(reservationId)
  → (on failure) IRiskManager.releaseReservation(reservationId)
  → (on depth sizing) IRiskManager.adjustReservation(reservationId, newCapital)
```

**Post-decomposition:** All calls go through `IRiskManager` interface — the facade delegates to `BudgetReservationService`. No caller changes needed.

### 5.5 Cross-Service Boundary Methods

| Method Call | Caller Module | Callee Module | Interface | Change Needed? |
|------------|--------------|---------------|-----------|---------------|
| closePosition | exit-management | risk-management | IRiskManager | NO |
| releasePartialCapital | exit-management | risk-management | IRiskManager | NO |
| reserveBudget | core | risk-management | IRiskManager | NO |
| commitReservation | execution | risk-management | IRiskManager | NO |
| releaseReservation | execution | risk-management | IRiskManager | NO |
| adjustReservation | execution | risk-management | IRiskManager | NO |
| updateDailyPnl | exit-management | risk-management | IRiskManager | NO |
| isTradingHalted | core, execution | risk-management | IRiskManager | NO |
| getBankrollConfig | dashboard | risk-management | IRiskManager | NO |

**All cross-module calls go through IRiskManager.** No new cross-module interfaces needed for the risk decomposition. The facade pattern preserves backward compatibility.

### 5.6 Hot Path (Synchronous) — MUST STAY SYNCHRONOUS

```
TradingEngineService.executeCycle():
  detection.scan()                    // sync
  → risk.validatePosition()          // sync (stays in RiskManagerService slim)
  → execution.execute()              // sync (stays in ExecutionService slim)
```

**No change.** The hot path calls `IRiskManager.validatePosition()` and `IExecutionEngine.execute()`, both remain synchronous method calls. Sub-service delegation within each module is also synchronous.

### 5.7 Transaction Boundary Mapping

| Operation | Transaction Scope | Owner | Post-Decomposition Owner |
|-----------|------------------|-------|-------------------------|
| reserveBudget | In-memory Map update (no Prisma tx) | RiskManagerService | BudgetReservationService |
| commitReservation | In-memory state update + persistState | RiskManagerService | BudgetReservationService → RiskStateManager.persistState |
| closePosition | In-memory state update + persistState | RiskManagerService | BudgetReservationService → RiskStateManager |
| execute() order creation | Prisma single-row inserts (no tx) | ExecutionService | ExecutionService (slim) — unchanged |
| executeExit chunked orders | Per-chunk order writes (no wrapping tx) | ExitMonitorService | ExitExecutionService |
| persistState | Single `prisma.riskState.upsert()` | RiskManagerService | RiskStateManager |
| initializeStateFromDb | Multiple reads (no tx needed — startup) | RiskManagerService | RiskStateManager |

**Key finding:** No multi-service Prisma transactions exist today. State updates are in-memory with periodic persistence via `persistState()`. This simplifies decomposition — no transaction handle passing needed between new services.

### 5.8 Event Contract Mapping

This table covers **events whose emitter changes** after decomposition. Events emitted by services not being decomposed (e.g., EventConsumerService, DashboardGateway, DailySummaryService) are unaffected and omitted.

| Event (actual string from event-catalog.ts) | Current Emitter | Post-Decomposition Emitter | Payload Change? |
|----------------------------------------------|----------------|---------------------------|----------------|
| `risk.limit.approached` | RiskManagerService.updateDailyPnl | RiskStateManager.updateDailyPnl | NO |
| `risk.limit.breached` | RiskManagerService.updateDailyPnl | RiskStateManager.updateDailyPnl | NO |
| `system.trading.halted` | RiskManagerService.haltTrading | TradingHaltService.haltTrading | NO |
| `system.trading.resumed` | RiskManagerService.resumeTrading | TradingHaltService.resumeTrading | NO |
| `risk.budget.released` | RiskManagerService.closePosition | BudgetReservationService.closePosition | NO |
| `risk.budget.reserved` | RiskManagerService.reserveBudget | BudgetReservationService.reserveBudget | NO |
| `risk.budget.committed` | RiskManagerService.commitReservation | BudgetReservationService.commitReservation | NO |
| `risk.override.applied` | RiskManagerService.processOverride | RiskManagerService (slim).processOverride | NO (same service) |
| `execution.order.filled` | ExecutionService.execute | ExecutionService (slim).execute | NO |
| `execution.order.failed` | ExecutionService.execute | ExecutionService (slim).execute | NO |
| `execution.single_leg.exposure` | ExecutionService.handleSingleLeg | LegSequencingService.handleSingleLeg | NO |
| `execution.single_leg.resolved` | ExecutionService.handleSingleLeg | LegSequencingService.handleSingleLeg | NO |
| `execution.exit.triggered` | ExitMonitorService.executeExit | ExitExecutionService.executeExit | NO |
| `execution.exit.partial_chunked` | ExitMonitorService.executeExit | ExitExecutionService.executeExit | NO |
| `execution.exit.shadow_comparison` | ExitMonitorService.evaluatePosition | ExitMonitorService (slim).evaluatePosition | NO (same service) |
| `execution.exit.shadow_daily_summary` | ExitMonitorService.evaluatePositions | ExitMonitorService (slim).evaluatePositions | NO (same service) |
| `config.bankroll.updated` | DashboardService.updateBankroll | DashboardCapitalService.updateBankroll | NO |

**All events preserve their payloads.** The emitting service changes but the event name and payload contract remain identical. EventConsumerService and DashboardGateway subscribe by event name, not by emitter identity.

### 5.9 @OnEvent / @Cron Handler Migration

**Key finding:** None of the 6 God Objects contain `@OnEvent` decorators. All event subscriptions live in `EventConsumerService` (monitoring module) and `DashboardGateway` (dashboard module), neither of which is being decomposed. Therefore, no `@OnEvent` handler migration is required.

**@Cron and @Interval handlers in God Objects:**

| Decorator | Current Service | Method | Post-Decomposition Service |
|-----------|----------------|--------|---------------------------|
| `@Cron('0 0 0 * * *')` | RiskManagerService | handleMidnightReset | RiskStateManager |
| `@Interval(30000)` | ExitMonitorService | evaluatePositions | ExitMonitorService (slim) |
| `@Cron(TELEGRAM_TEST_ALERT_CRON)` | TelegramAlertService | handleTestAlert | TelegramAlertService (slim) |

These decorators move with their methods — no wiring changes needed. The NestJS scheduler resolves decorators on the provider class, so the module must register the new service class that carries the decorator.

---

## 6. ConfigAccessor Circular DI Resolution

### 6.1 Current Config Reload Architecture

```
SettingsService (dashboard module)
  → onModuleInit()
    → registerAllHandlers()  // uses ModuleRef.get(token, { strict: false })
      → risk: RISK_MANAGER_TOKEN → svc.reloadConfig()
      → telegram: TelegramAlertService → svc.reloadConfig(cfg)
      → exit-monitor: ExitMonitorService → svc.reloadConfig(cfg)
      → execution: EXECUTION_ENGINE_TOKEN → svc.reloadConfig(cfg)
      → detection: EdgeCalculatorService → svc.reloadConfig(cfg)
      → data-ingestion: DataIngestionService → svc.reloadConfig(cfg)
      → discovery-cron: CandidateDiscoveryService → svc.reloadConfig(cfg)
      → resolution-cron: ResolutionPollerService → svc.reloadConfig(cfg)
      → calibration-cron: CalibrationService → svc.reloadConfig(cfg)
      → polling-interval: SchedulerService → svc.reloadConfig(cfg)
      → trading-window: SchedulerService → svc.reloadConfig(cfg)
```

**Key insight:** SettingsService uses `ModuleRef.get(token, { strict: false })` to resolve services at runtime, bypassing compile-time DI graph. This avoids circular imports entirely.

### 6.2 Config Properties per New Service

| Service | Config Properties Needed | Source |
|---------|------------------------|--------|
| BudgetReservationService | bankrollUsd, riskMaxPositionPct, riskMaxOpenPairs | Via RiskStateManager (injected) |
| TradingHaltService | (none — halt reasons are runtime state) | — |
| RiskStateManager | bankrollUsd, paperBankrollUsd, riskMaxPositionPct, riskMaxOpenPairs, riskDailyLossPct | ConfigService + EngineConfigRepository |
| ExitExecutionService | exitMaxChunkSize | Via ExitMonitorService (slim) reload passthrough |
| ExitDataSourceService | wsStalenessThresholdMs, exitMinDepth, exitDepthSlippageTolerance | Via ExitMonitorService (slim) reload passthrough |
| LegSequencingService | (none — uses connector-provided data) | — |
| DepthAnalysisService | dualLegMinDepthRatio | Via ExecutionService (slim) reload passthrough |
| DashboardOverviewService | (none — reads from injected services) | — |
| DashboardCapitalService | (none — reads from IRiskManager) | — |
| DashboardAuditService | (none — reads from Prisma) | — |
| TelegramCircuitBreaker | sendTimeoutMs, maxRetries, bufferMaxSize, circuitBreakMs | ConfigService (constructor) + reloadConfig |

### 6.3 Proposed Config Injection Strategy

**Strategy: Parent-to-child config passthrough**

For services within the same module, the parent (slimmed) service receives `reloadConfig()` from SettingsService and passes relevant config subsets to child services:

```typescript
// ExitMonitorService (slim)
reloadConfig(settings: ExitConfig): void {
  // Own config
  this.exitMode = settings.exitMode;
  // Passthrough to children
  this.exitExecutionService.reloadConfig({ exitMaxChunkSize: settings.exitMaxChunkSize });
  this.exitDataSourceService.reloadConfig({
    wsStalenessThresholdMs: settings.wsStalenessThresholdMs,
    exitMinDepth: settings.exitMinDepth,
  });
}
```

**Advantages:**
1. No changes to SettingsService — it still calls `svc.reloadConfig()` on the same tokens
2. No circular DI risk — parent passes config downward
3. Each child gets only the config it needs (typed config partial)

**RiskManagerService special case:** RiskManagerService.reloadConfig() re-reads from DB (not from SettingsService params). After decomposition, the facade's reloadConfig() calls RiskStateManager.reloadConfig() which performs the DB read. BudgetReservationService reads config from RiskStateManager (injected).

### 6.4 Constructor-Time Config

Services that read config in constructor (ExitMonitorService, ExecutionService) must continue doing so. The constructor config reads move to the child service that owns those properties:

| Current Constructor Config Read | Moves To |
|-------------------------------|----------|
| ExitMonitorService: 12 config properties | ExitMonitorService (slim): pass to children at construction |
| ExecutionService: 3 config properties | ExecutionService (slim): keep minFillRatio, pass dualLegMinDepthRatio to DepthAnalysisService |

### 6.5 No Circular Dependencies

No service pairs form a cycle:
- ConfigAccessor (in DashboardModule) → EngineConfigRepository (shared) — no module imports dashboard
- SettingsService → ModuleRef.get() — runtime resolution, no compile-time dependency
- New sub-services depend only on their parent (within-module) or cross-module interfaces

---

## 7. Interface Migration Table

### 7.1 Existing Interface Method Reassignment

#### IRiskManager (19 methods) — `src/common/interfaces/risk-manager.interface.ts`

| Interface Method | Current Implementer | Post-Decomposition Implementer | Delegation Target |
|-----------------|--------------------|-----------------------------|-------------------|
| validatePosition | RiskManagerService | RiskManagerService (slim) | Direct — owns logic |
| getCurrentExposure | RiskManagerService | RiskManagerService (slim) | → RiskStateManager |
| getOpenPositionCount | RiskManagerService | RiskManagerService (slim) | → RiskStateManager |
| updateDailyPnl | RiskManagerService | RiskManagerService (slim) | → RiskStateManager |
| isTradingHalted | RiskManagerService | RiskManagerService (slim) | → TradingHaltService |
| getActiveHaltReasons | RiskManagerService | RiskManagerService (slim) | → TradingHaltService |
| haltTrading | RiskManagerService | RiskManagerService (slim) | → TradingHaltService |
| resumeTrading | RiskManagerService | RiskManagerService (slim) | → TradingHaltService |
| recalculateFromPositions | RiskManagerService | RiskManagerService (slim) | → RiskStateManager |
| processOverride | RiskManagerService | RiskManagerService (slim) | Direct — owns logic |
| reserveBudget | RiskManagerService | RiskManagerService (slim) | → BudgetReservationService |
| commitReservation | RiskManagerService | RiskManagerService (slim) | → BudgetReservationService |
| releaseReservation | RiskManagerService | RiskManagerService (slim) | → BudgetReservationService |
| adjustReservation | RiskManagerService | RiskManagerService (slim) | → BudgetReservationService |
| closePosition | RiskManagerService | RiskManagerService (slim) | → BudgetReservationService |
| releasePartialCapital | RiskManagerService | RiskManagerService (slim) | → BudgetReservationService |
| getBankrollConfig | RiskManagerService | RiskManagerService (slim) | → RiskStateManager |
| getBankrollUsd | RiskManagerService | RiskManagerService (slim) | → RiskStateManager |
| reloadBankroll | RiskManagerService | RiskManagerService (slim) | → RiskStateManager |

**Strategy: Facade delegates to sub-services.** The IRiskManager interface is **unchanged**. The slimmed RiskManagerService still implements it fully. All cross-module consumers (ExitMonitor, Execution, Dashboard) continue injecting `RISK_MANAGER_TOKEN` as before. Zero breaking changes.

#### IExecutionEngine (1 method) — `src/common/interfaces/execution-engine.interface.ts`

| Interface Method | Current Implementer | Post-Decomposition Implementer |
|-----------------|--------------------|-----------------------------|
| execute | ExecutionService | ExecutionService (slim) |

**Strategy: No change.** ExecutionService (slim) implements IExecutionEngine directly. The `execute()` method stays in the slim service — it delegates internally to LegSequencingService and DepthAnalysisService.

### 7.2 New Interfaces Required

**None required for cross-module boundaries.** All decomposed services are consumed within their own module. Cross-module access continues through the existing IRiskManager and IExecutionEngine interfaces.

**Recommended (not required) internal interfaces for testability:**

| Interface | Purpose | Consumed By |
|-----------|---------|------------|
| (none) | Sub-services are injected directly within their module | — |

**Rationale:** Creating interfaces for within-module dependencies adds boilerplate without benefit. NestJS's testing module can mock concrete classes directly. If a sub-service ever needs cross-module access in the future, an interface can be added then.

### 7.3 Injection Tokens for New Services

No new injection tokens needed. New sub-services are provided directly by class:

```typescript
// risk-management.module.ts
providers: [
  { provide: RISK_MANAGER_TOKEN, useClass: RiskManagerService },
  BudgetReservationService,
  TradingHaltService,
  RiskStateManager,
  // ... existing providers
]
```

Cross-module consumers continue using `RISK_MANAGER_TOKEN` and `EXECUTION_ENGINE_TOKEN`.

### 7.4 Backward Compatibility

**Full backward compatibility.** No changes to:
- IRiskManager interface contract
- IExecutionEngine interface contract
- RISK_MANAGER_TOKEN / EXECUTION_ENGINE_TOKEN injection tokens
- Module import/export structure
- Event names or payloads
- REST API endpoints

The decomposition is purely internal to each module.

---

## 8. Reviewer Context Template

Use the following template for every Lad MCP `code_review` `context` parameter across stories 10-8-1 through 10-8-6:

```
### Changes Summary
[1-2 sentences: What was decomposed and why. Example: "Split RiskManagerService (1,651 lines, 7 responsibilities) into BudgetReservationService + TradingHaltService + RiskStateManager + slimmed RiskManagerService facade. Pure internal refactoring — zero functional changes."]

### Codebase Conventions (from CLAUDE.md)
- Services: ~300 line preferred limit, ~400 absolute file limit
- Constructor: max 5 injected dependencies
- Module providers: max ~8 services
- Module boundaries: cross-module access via interfaces in common/interfaces/ only
- Errors: must extend SystemError hierarchy
- Events: must emit via EventEmitter2 with dot-notation names
- Financial math: decimal.js only, never native JS operators
- Testing: co-located specs, assertion depth (verify payloads not just calls), event wiring verification via expectEventHandled
- Paper/Live: isPaper parameter required on mode-sensitive queries, dual-mode test matrix

### Out-of-Scope (DO NOT FLAG)
- Pre-existing patterns in code not touched by this PR (e.g., existing God Objects not being decomposed in this story)
- Line counts in files not modified by this story
- Stylistic preferences that don't affect correctness or violate CLAUDE.md
- Test patterns inherited from the original spec file
- Module provider counts that were already over limit before this story
```

---

## 9. Implementation Sequence

### Dependency Graph

```
10-8-0 (this design doc — GATE)
  ↓
10-8-1 (RiskManager decomposition) — foundational, risk interfaces stable first
  ↓
10-8-2 (ExitMonitor decomposition) — depends on stable risk sub-services
  ↓
10-8-3 (Execution decomposition) — depends on 10-8-1
  ↓
10-8-4 (Dashboard decomposition) — depends on 10-8-1, 10-8-2, 10-8-3
  ↓ (parallel from here)
10-8-5 (TelegramFormatter domain split) — independent
10-8-6 (TelegramCircuitBreaker extraction) — independent
```

### Recommended Sequencing Notes

1. **10-8-1 first:** RiskManagerService is the most referenced God Object (9 non-test consumers via IRiskManager). Stabilizing the facade pattern here validates the approach for all subsequent stories.
2. **10-8-2 before 10-8-3:** ExitMonitorService depends on IRiskManager for closePosition/releasePartialCapital. With 10-8-1 complete, the risk interface is stable.
3. **10-8-4 last (among core):** DashboardService injects services from risk, execution, and exit modules. It must decompose after all its dependencies are stable.
4. **10-8-5 and 10-8-6 parallel:** TelegramMessageFormatter and TelegramAlertService have no dependencies on the other decomposition stories. They can run in parallel with 10-8-4 or even earlier.

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| validatePosition (341 lines) prevents slimmed RiskManager from meeting ~300 preferred limit | High | Low (meets ≤600 epic target) | Internal refactoring to extract validation sub-steps as private helpers |
| execute() (974 lines) refactoring scope is larger than estimated | Medium | Medium | Time-box phase extraction; if needed, split into additional stories |
| ExitMonitor evaluatePosition (515 lines) refactoring | Medium | Low | Same approach as execute() — extract criteria-building helpers |
| Module provider counts increase beyond ~8 | High | Low (pre-existing problem) | Evaluate PersistenceModule consolidation in separate story post-epic |
| TelegramCircuitBreaker ~285 lines exceeds ≤200 target | High | Low | Adjust target to ≤300 or trim during 10-8-6 |
| Mid-sequence story stalls (partially decomposed codebase) | Low | High | See rollback strategy below |

### Rollback Strategy

Each decomposition story is designed to be **independently revertible** via `git revert` because:

1. **Zero functional changes:** Every story passes the existing test suite unmodified. Reverting returns to the pre-decomposition state with all tests green.
2. **Facade pattern:** The slimmed service implements the same interface as the God Object. External consumers don't change — only the internal implementation is restructured.
3. **Independent modules:** Each story decomposes one God Object. Stories 10-8-5 and 10-8-6 have no dependencies on 10-8-1 through 10-8-4.

**If a story stalls:**
- **10-8-1 stalls:** All subsequent stories (10-8-2, 10-8-3, 10-8-4) are blocked. Revert 10-8-1 and reassess. Stories 10-8-5 and 10-8-6 can proceed independently.
- **10-8-2 or 10-8-3 stalls:** 10-8-4 is blocked. The stalled story can be reverted without affecting 10-8-1 (already merged). Remaining independent stories proceed.
- **10-8-4 stalls:** Dashboard decomposition is cosmetic (read-only service). Revert and defer to post-epic. All other stories are unaffected.

**Epic abort criteria:** If 2+ stories require revert, reassess the decomposition approach in a retro before continuing.
