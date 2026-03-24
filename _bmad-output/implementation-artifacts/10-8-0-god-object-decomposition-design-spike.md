# Story 10.8.0: God Object Decomposition Design Spike

Status: done

## Story

As the architect,
I want a single design document with method-to-service allocation tables for all 6 God Objects,
so that all code stories (10-8-1 through 10-8-6) have an unambiguous decomposition plan reviewed and accepted before implementation begins.

## Acceptance Criteria

1. **Given** the 6 identified God Objects (RiskManagerService 1,651 lines, ExitMonitorService 1,616 lines, ExecutionService 1,543 lines, DashboardService 1,199 lines, TelegramMessageFormatter 797 lines, TelegramAlertService 734 lines)
   **When** the design spike is complete
   **Then** a single document exists with:
   - Method-to-service allocation table for each God Object (which methods move where)
   - Test file mapping plan (which spec files split and where tests migrate)
   - Constructor dependency splits (which deps go to which new service)
   - Cross-service touchpoint analysis (`closePosition()`, `releasePartialCapital()`, PnL accumulation path through chunking loop)
   - ConfigAccessor circular DI resolution paths

2. **Given** the design document is produced
   **When** submitted for review
   **Then** Arbi accepts the document before any code story (10-8-1 through 10-8-6) starts

3. **Given** line/dependency/responsibility limits from architecture
   **When** the allocation tables are finalized
   **Then** every proposed service meets the epic AC targets (see Proposed Target Services table in Dev Notes) as the minimum bar, with CLAUDE.md limits (~300 service lines excl. imports/types, ~400 file lines) as the preferred target
   **And** no target service constructor exceeds 5 injected dependencies
   **And** no affected module's providers array exceeds ~8 services post-decomposition

4. **Given** services are decomposed across boundaries
   **When** cross-module callers exist for decomposed methods
   **Then** the design document includes an interface migration table showing existing interface method reassignments, new interfaces required, and backward compatibility strategy

## Tasks / Subtasks

- [x] Task 1: Audit current state of all 6 God Objects (AC: #1)
  - [x] 1.1 Read each God Object file; record exact line count, method count, constructor deps, and responsibility groups
  - [x] 1.2 Read each God Object's spec file; record line count, describe block structure, test count
  - [x] 1.3 For each God Object, identify all external consumers (who injects/calls it) using `find_referencing_symbols` or grep
  - [x] 1.4 Compile findings into a "Current State" section of the design document
- [x] Task 2: Create method-to-service allocation tables (AC: #1, #3)
  - [x] 2.1 RiskManagerService → BudgetReservationService + TradingHaltService + RiskStateManager + slimmed RiskManagerService
  - [x] 2.2 ExitMonitorService → ExitExecutionService + ExitDataSourceService + slimmed ExitMonitorService
  - [x] 2.3 ExecutionService → LegSequencingService + DepthAnalysisService + slimmed ExecutionService
  - [x] 2.4 DashboardService → DashboardOverviewService + DashboardCapitalService + DashboardAuditService + slimmed DashboardService
  - [x] 2.5 TelegramMessageFormatter → 7 domain formatter files + formatter-utils.ts
  - [x] 2.6 TelegramAlertService → TelegramCircuitBreaker + slimmed TelegramAlertService
  - [x] 2.7 For each table: list every method/function, its target service, estimated line count, and verify target service stays under limits
  - [x] 2.8 For each "slimmed" service: document the specific responsibilities it retains, justify why they cannot move to sub-services, and specify whether it acts as a facade/coordinator or retains stateful responsibilities
- [x] Task 3: Create constructor dependency split tables (AC: #1, #3)
  - [x] 3.1 For each God Object, map every constructor parameter to its target service
  - [x] 3.2 Verify no target service exceeds 5 injected dependencies
  - [x] 3.3 Identify new cross-service dependencies introduced by the split (e.g., slimmed RiskManagerService injecting BudgetReservationService)
  - [x] 3.4 Check for circular DI risks — especially ConfigAccessor patterns where config reload chains cross service boundaries
  - [x] 3.5 Verify module provider counts post-decomposition: for each affected module, count providers before/after and flag any exceeding ~8
- [x] Task 4: Create test file mapping plan (AC: #1)
  - [x] 4.1 For each God Object spec file, map describe blocks to target spec files
  - [x] 4.2 Verify target spec files stay under ~800 lines each
  - [x] 4.3 Identify shared test fixtures/mocks that need extraction into test helpers
  - [x] 4.4 Note any integration tests (event wiring, `expectEventHandled`) that must remain intact
  - [x] 4.5 Check E2E tests in `test/e2e/` that reference each God Object; verify they will pass with decomposed services and note any modifications required
- [x] Task 5: Cross-service touchpoint analysis (AC: #1)
  - [x] 5.1 Trace `closePosition()` call chain: who calls it, what state it mutates, what events it emits
  - [x] 5.2 Trace `releasePartialCapital()` call chain: same analysis
  - [x] 5.3 Trace PnL accumulation path through the exit chunking loop (`executeExit` in ExitMonitorService)
  - [x] 5.4 Trace `reserveBudget → commitReservation → releaseReservation` lifecycle across execution + risk services
  - [x] 5.5 Identify any method calls that cross the proposed new service boundaries and determine interface contracts
  - [x] 5.6 Document the execution hot path (detection → risk → execution) touchpoints that MUST remain synchronous
  - [x] 5.7 Transaction boundary mapping: for each cross-service touchpoint, identify units of work that must stay atomic (same Prisma transaction), which service owns the transaction, and how transaction handles are passed between decomposed services
  - [x] 5.8 Event contract mapping: for each event emitted by a God Object, specify which decomposed service now emits it, verify payload compatibility, and note any event pattern changes
- [x] Task 6: ConfigAccessor circular DI resolution (AC: #1)
  - [x] 6.1 Map all `reloadConfig()` methods across the 6 God Objects
  - [x] 6.2 Trace config reload trigger chains (SchedulerService calls `reloadConfig` on multiple services)
  - [x] 6.3 For each proposed new service, determine which config properties it needs
  - [x] 6.4 Identify any circular dependency scenarios (Service A depends on Service B which depends on Service A for config)
  - [x] 6.5 Propose resolution pattern (forwardRef, config passed as parameter, config sub-object injection)
  - [x] 6.6 Identify constructor-time circular dependencies (not just reload-time) and specify config injection strategy per service: full ConfigAccessor, typed config partial, or config via method parameters
- [x] Task 7: Interface migration table (AC: #4)
  - [x] 7.1 Map existing interface methods (`IRiskManager`, `IExecutionEngine`, etc.) to their post-decomposition service owners
  - [x] 7.2 Identify new interfaces required for cross-module boundaries (e.g., `IBudgetReservation` if execution module needs budget methods)
  - [x] 7.3 Define backward compatibility strategy: existing interface delegates to new sub-services vs. interface split
  - [x] 7.4 Specify injection tokens for new services that are consumed cross-module
- [x] Task 8: Reviewer context template (AC: prerequisite from retro)
  - [x] 8.1 Create a reusable template for Lad MCP `context` parameter that includes: changes summary, codebase conventions snippet, out-of-scope declaration
  - [x] 8.2 Include this template in the design document so all 10-8-X story files can reference it
- [x] Task 9: Compile design document and submit for review (AC: #2)
  - [x] 9.1 Assemble all tables and analysis into a single design document at `_bmad-output/implementation-artifacts/10-8-0-design-doc.md`
  - [x] 9.2 Include implementation sequence recommendation (dependencies between stories)
  - [x] 9.3 Submit to Arbi for review and acceptance

## Dev Notes

### Nature of This Story

This is a **design document story**, not a code story. The deliverable is a markdown document with structured analysis tables. No production code is written or modified. The output gates all subsequent Epic 10.8 code stories.

### Owner

Winston (Architect agent). Arbi must accept before any code story starts.

### God Object Current State (verified 2026-03-24)

Line counts have **drifted upward** since the original course correction (2026-03-23). Use these verified values:

| # | God Object | File Path | Lines | Methods | Deps | Violations |
|---|-----------|-----------|-------|---------|------|------------|
| 1 | RiskManagerService | `src/modules/risk-management/risk-manager.service.ts` | **1,651** | 35 | 5 | 5.5x service limit, 7 responsibility areas |
| 2 | ExitMonitorService | `src/modules/exit-management/exit-monitor.service.ts` | **1,616** | 10 | **9** | 5.4x service limit, 9 deps (limit: 5), 2 methods >500 lines |
| 3 | ExecutionService | `src/modules/execution/execution.service.ts` | **1,543** | 7 | **9** | 5.1x service limit, 9 deps, `execute()` ~1,000 lines |
| 4 | DashboardService | `src/dashboard/dashboard.service.ts` | **1,199** | 20 | **12** | 4x service limit, 12 deps (worst), 7 responsibility areas |
| 5 | TelegramMessageFormatter | `src/modules/monitoring/formatters/telegram-message.formatter.ts` | **797** | 32 | N/A | Pure functions, 2x file limit |
| 6 | TelegramAlertService | `src/modules/monitoring/telegram-alert.service.ts` | **734** | 20 | 1 | 1.8x file limit, 5 distinct responsibilities |

**Total God Object code: ~7,540 lines**

### Responsibility Breakdown (Pre-Analysis)

The god-object-analyzer identified these responsibility groups. Use as starting point for allocation tables — verify against code before finalizing:

**RiskManagerService (7 groups):**
1. Config/bankroll management (6 methods): `loadBankrollFromDb`, `reloadBankroll`, `reloadConfig`, `buildReloadEnvFallback`, `getBankrollConfig`, `getBankrollUsd`
2. Risk validation + cluster limits (4 methods): `validatePosition`, `determineRejectionReason`, `extractPairContext`, `fetchTriageWithDtos`
3. Budget reservation lifecycle (5 methods): `reserveBudget`, `commitReservation`, `releaseReservation`, `adjustReservation`, `getReservedPositionSlots`, `getReservedCapital`
4. Position lifecycle (2 methods): `closePosition`, `releasePartialCapital`
5. Halt management (4 methods): `isTradingHalted`, `getActiveHaltReasons`, `haltTrading`, `resumeTrading`
6. DB state persistence/init (4 methods): `onModuleInit`, `clearStaleReservations`, `initializeStateFromDb`, `persistState`
7. Daily P&L / cron / reconciliation (3 methods): `updateDailyPnl`, `handleMidnightReset`, `recalculateFromPositions`

**ExitMonitorService (5 groups):**
1. Poll loop orchestration: `evaluatePositions` (~140 lines)
2. Per-position evaluation: `evaluatePosition` (~500 lines — builds criteria inputs, calls threshold evaluator, persists recalculated edge, emits shadow comparison)
3. Exit order execution: `executeExit` (~550 lines — chunked dual-leg submission, P&L computation, risk state updates, events)
4. Market data helpers: `getClosePrice`, `getAvailableExitDepth`
5. Data freshness: `classifyDataSource`, `combineDataSources`

**ExecutionService (5 groups):**
1. Main execution orchestration: `execute()` (~1,000 lines — compliance, sizing, depth, order submission, position creation)
2. Single-leg handling: `handleSingleLeg` (~250 lines)
3. Depth checking: `getAvailableDepth`
4. Adaptive sequencing: `determineSequencing`
5. Data source classification: `classifyDataSource`, `resolveConnectors`

**DashboardService (7 groups):**
1. Overview/health (4 methods): `getOverview`, `getHealth`, `getLatestHealthLogs`, `computeCompositeHealth`
2. Position listing (2 methods): `getPositions`, `getPositionById`
3. Position full detail (1 method): `getPositionDetails` (orders, audit trail, capital breakdown)
4. Bankroll management (2 methods): `getBankrollConfig`, `updateBankroll`
5. P&L / capital computation (3 methods): `computeRealizedPnl`, `computeCapitalBreakdown`, `computeModeCapital`
6. Utility / DTO mapping (5 methods): `parseAuditDetails`, `parseJsonFieldWithEvent`, `summarizeAuditEvent`, `mapExecutionMetadata`, `computeTimeHeld`
7. Shadow mode (2 methods): `getShadowComparisons`, `getShadowSummary`

**TelegramMessageFormatter (2 groups):**
1. HTML utility functions (6): `escapeHtml`, `smartTruncate`, `closeUnclosedTags`, `formatTimestamp`, `formatCorrelationFooter`, `paperModeTag`
2. Per-event formatters (26): one per event type — group by domain (execution, risk, platform, system, exit, detection, matching)

**TelegramAlertService (5 groups):**
1. HTTP transport: `sendMessage`
2. Circuit breaker: `getCircuitState`, failure tracking in `enqueueAndSend`
3. Message batching: `addToBatch`, `flushBatch`, `consolidateMessages`, `truncateHtmlSafe`
4. Failure buffer: `bufferMessage`, `evictLowestPriority`, `triggerBufferDrain`, `drainBuffer`
5. Event dispatch: `sendEventAlert`, `handleEvent`, plus `FORMATTER_REGISTRY`

### Proposed Target Services (from epic ACs — minimum bar; CLAUDE.md ~300/~400 limits are preferred target)

| God Object | Target Services | Line Target |
|-----------|----------------|-------------|
| RiskManagerService | BudgetReservationService + TradingHaltService + RiskStateManager + slimmed RiskManagerService | ≤600 each |
| ExitMonitorService | ExitExecutionService + ExitDataSourceService + slimmed ExitMonitorService | ≤500 each |
| ExecutionService | LegSequencingService + DepthAnalysisService + slimmed ExecutionService | ≤500 each, `execute()` ≤200 lines |
| DashboardService | DashboardOverviewService + DashboardCapitalService + DashboardAuditService + slimmed DashboardService | ≤400 each |
| TelegramMessageFormatter | 7 domain files + formatter-utils.ts + barrel index.ts | ≤200 each |
| TelegramAlertService | TelegramCircuitBreaker + slimmed TelegramAlertService | CB ≤200, alert ≤550 |

### Implementation Sequence (from course correction)

```
10-8-0 (this story — design spike, GATE)
  ↓
10-8-1 (RiskManager) — foundational, other stories depend on risk interfaces
  ↓
10-8-2 (ExitMonitor) — depends on stable risk interfaces from 10-8-1
  ↓
10-8-3 (Execution) — depends on 10-8-1
  ↓
10-8-4 (Dashboard) — depends on 10-8-1, 10-8-2, 10-8-3 (injects their services)
  ↓ (parallel)
10-8-5 (TelegramFormatter) — independent
10-8-6 (TelegramCircuitBreaker) — independent
```

### Critical Cross-Service Touchpoints to Analyze

These are the highest-risk interaction patterns that the design doc must resolve:

1. **`closePosition()` chain:** Called by ExitMonitorService's `executeExit` → delegates to RiskManagerService → mutates budget state + emits events. After decomposition, `closePosition()` will move to a new sub-service — all callers must update.

2. **`releasePartialCapital()` chain:** Called during partial exits → risk state mutation. Must stay in the budget reservation service boundary.

3. **PnL accumulation in chunked exit loop:** `executeExit` runs a chunked loop submitting exit legs, accumulating realized PnL per chunk, then calling `closePosition` with final PnL. After decomposition, this loop lives in ExitExecutionService but needs to call into risk management for P&L recording.

4. **Budget reservation lifecycle:** `reserveBudget() → commitReservation() → releaseReservation()` spans execution (caller) and risk-management (implementer). After RiskManager decomposition, these move to BudgetReservationService — ExecutionService must inject the new service or a stable interface.

5. **Config reload cascade:** SchedulerService triggers `reloadConfig()` on RiskManagerService, ExitMonitorService, ExecutionService. After decomposition, each new sub-service may need its own `reloadConfig()` or receive config from its parent.

### Architecture Constraints (Hard Rules)

- **Module dependency rules:** No module imports another module's service directly — interfaces only via `common/interfaces/`. New services created by decomposition must respect this. If BudgetReservationService is in `risk-management/`, it's fine for other risk services to inject it directly (same module). But if execution needs it, it goes through `IRiskManager` or a new interface.
- **Zero functional changes:** Every story must pass the existing test suite with no behavioral modifications. The design doc must prove each decomposition is behavior-preserving.
- **Hot path must stay synchronous:** Detection → Risk validation → Execution. Don't accidentally make this async during decomposition.
- **Fan-out must stay async:** Events → Monitoring → Dashboard/Telegram. Don't accidentally make this synchronous.

### Reviewer Context Template (Prerequisite)

Epic 10.7 retro identified 19% actionable code review rate. Root cause: reviewers lacked context about project conventions and change scope. The design document must include a reusable template for Lad MCP `context` parameter containing:
1. **Changes summary:** What was changed and why (one paragraph)
2. **Codebase conventions snippet:** Key rules from CLAUDE.md relevant to the review (module boundaries, error hierarchy, testing standards, naming)
3. **Out-of-scope declaration:** What the reviewer should NOT flag (e.g., "pre-existing patterns not touched by this PR")

This template will be embedded in each 10-8-X story file's dev notes.

### Agreements Referenced

- **Agreement #27 (upgraded):** Design sketch gate — was an honor-system pre-step, failed across two retros. Now a formal story (this one) with a verifiable artifact (the design document). No code story starts without accepted design doc.
- **Agreement #30:** No standalone soft commitments. Every retro action item must be a story task or AC with a verifiable artifact. Three consecutive retros (Epics 9, 10, 10.5) proved soft disciplines fail while story-embedded deliverables ship 100%.

### Output Artifact

The design document should be created at: `_bmad-output/implementation-artifacts/10-8-0-design-doc.md`

### Project Structure Notes

- All 6 God Objects are in `pm-arbitrage-engine/src/` — the nested independent git repo
- **DashboardService** is in `src/dashboard/` (top-level module), NOT in `src/modules/` like the other God Objects. This affects its module boundary — it injects services from multiple modules, making its dependency split analysis different.
- Design document lives in the main repo under `_bmad-output/implementation-artifacts/`
- No changes to `pm-arbitrage-engine/` code in this story

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-23-god-object-decomposition.md] — Original course correction proposal with initial method-to-service allocation tables
- [Source: _bmad-output/implementation-artifacts/epic-10-7-retro-2026-03-24.md] — Retro that added 10-8-0 gate, Agreement #27 upgrade, Agreement #30, reviewer context template prerequisite
- [Source: _bmad-output/implementation-artifacts/sprint-status.yaml#L238-250] — Epic 10.8 status and story list
- [Source: CLAUDE.md#No-God-Objects-or-God-Files] — Hard constraints on service/file limits
- [Source: CLAUDE.md#Module-Dependency-Rules] — Allowed and forbidden import patterns
- [Source: CLAUDE.md#Testing] — Co-located tests, assertion depth, event wiring verification

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Baseline: 2,842 tests pass across 160 files (verified pre-work)
- Used Serena `get_symbols_overview` + `find_symbol` for all 6 God Objects
- Used Serena `find_referencing_symbols` for external consumer discovery
- All line counts verified via `wc -l`

### Completion Notes List

- **Task 1 (Audit):** All 6 God Objects audited. Exact line counts (7,540 total), method counts (35+12+7+20+32+20=126), constructor deps (5+9+9+12+N/A+1), spec file sizes (14,059 total lines, 579 tests). External consumers mapped via `find_referencing_symbols`.
- **Task 2 (Allocation tables):** Method-to-service allocation tables created for all 6 God Objects with line ranges, target services, and estimated post-decomposition sizes. All targets meet epic minimums. Noted 3 God Methods requiring internal refactoring: validatePosition (341), evaluatePosition (515), execute (974).
- **Task 3 (Dep splits):** Constructor dependencies mapped for all 15 new services. All ≤5 deps. No circular DI risks. Module provider counts: RiskManagement OK (8), ExitManagement OK (7), Execution/Dashboard/Monitoring already over limit pre-decomposition.
- **Task 4 (Test mapping):** Spec file split plans for all 6 God Objects. ExitMonitor tests already split into 11 files — mapped to target services. Shared test helpers identified. Paper/live boundary tests and event wiring tests flagged as must-preserve. No E2E tests exist.
- **Task 5 (Touchpoints):** Traced closePosition, releasePartialCapital, PnL chunking, budget reservation lifecycle. Key finding: no multi-service Prisma transactions exist — all state updates are in-memory with periodic persistence. Hot path stays synchronous. Event contracts preserve all payloads.
- **Task 6 (Config DI):** SettingsService uses `ModuleRef.get(token, { strict: false })` — no compile-time circular risk. Proposed parent-to-child config passthrough pattern. Config properties mapped per new service.
- **Task 7 (Interfaces):** IRiskManager (19 methods) unchanged — facade delegates to sub-services. IExecutionEngine (1 method) unchanged. No new cross-module interfaces needed. Full backward compatibility.
- **Task 8 (Reviewer template):** Reusable Lad MCP context template created with changes summary, conventions snippet, and out-of-scope declaration sections.
- **Task 9 (Compile):** Design document assembled at `_bmad-output/implementation-artifacts/10-8-0-design-doc.md`. 9 sections covering all 8 analysis areas plus implementation sequence.

### File List

- `_bmad-output/implementation-artifacts/10-8-0-design-doc.md` — NEW: Complete decomposition design document
- `_bmad-output/implementation-artifacts/10-8-0-god-object-decomposition-design-spike.md` — MODIFIED: Tasks checked, Dev Agent Record, status → review
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — MODIFIED: Story status → in-progress

### Change Log

- 2026-03-24: Design document created with all 9 sections. Submitted for Arbi's review.
