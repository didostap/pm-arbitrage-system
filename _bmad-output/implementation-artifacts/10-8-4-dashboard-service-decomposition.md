# Story 10.8.4: DashboardService Decomposition

Status: done

## Story

As a developer,
I want `DashboardService` (1,199 lines, 20 methods, 13 constructor deps) decomposed into 4 focused services,
So that the "gateway God Object" pattern is eliminated and each dashboard concern is independently maintainable.

## Acceptance Criteria

1. **Given** the existing `DashboardService` aggregates overview, positions, capital, PnL, alerts, audit, shadow, and bankroll concerns **When** I extract `DashboardOverviewService` (overview + health + alerts + shadow), `DashboardCapitalService` (capital + PnL + bankroll), and `DashboardAuditService` (position details + audit parsing) **Then** `DashboardService` retains only position listing queries and facade delegation
2. Each new service file is under 400 lines
3. `DashboardService` (slim) is under 400 lines
4. DashboardController injection is unchanged — `DashboardService` remains the facade (per accepted design spike 10-8-0, Section 2.4; overrides epic AC "injects specific services")
5. `dashboard.service.spec.ts` (1,435 lines) is decomposed into co-located spec files (each under 800 lines)
6. All existing tests pass with zero behavioral changes
7. Constructor deps: DashboardOverviewService ≤8 (justified: getOverview is a read-heavy aggregation point assembling 7+ sources; precedent ExitMonitorService 9 deps), DashboardCapitalService ≤5, DashboardAuditService ≤5, DashboardService (slim) ≤6 (justified: getPositions needs repo, enrichment, prisma + 3 sub-services; precedent RiskManagerService 6 deps)
8. DashboardModule providers increase by 3 (10 → 13; pre-existing overage documented in design spike Section 3.6)
9. No module dependency rule violations introduced
10. ~~Shared test fixtures extracted to `dashboard-test-helpers.ts`~~ Each spec uses self-contained mock factories (per-service dep sets too divergent for meaningful sharing; shared helpers would add indirection without benefit)

## Tasks / Subtasks

- [x]Task 1: Create DashboardOverviewService (AC: 1, 2, 7)
  - [x]1.1 Write failing tests for getOverview, getHealth, getAlerts, getShadowComparisons, getShadowSummary, computeCompositeHealth in `dashboard-overview.service.spec.ts`
  - [x]1.2 Implement DashboardOverviewService with methods from design spike allocation table
  - [x]1.3 Verify constructor deps ≤7 (see Dev Notes for expected dep list)
  - [x]1.4 Verify file under 400 lines

- [x]Task 2: Create DashboardCapitalService (AC: 1, 2, 7)
  - [x]2.1 Write failing tests for computeCapitalBreakdown, computeModeCapital, computeRealizedPnl, computeTimeHeld, getBankrollConfig, updateBankroll in `dashboard-capital.service.spec.ts`
  - [x]2.2 Implement DashboardCapitalService with methods from design spike allocation table
  - [x]2.3 Verify event emission for `config.bankroll.updated` in updateBankroll
  - [x]2.4 Verify constructor deps ≤5

- [x]Task 3: Create DashboardAuditService (AC: 1, 2, 7)
  - [x]3.1 Write failing tests for getPositionDetails, mapExecutionMetadata, parseAuditDetails, parseJsonFieldWithEvent, summarizeAuditEvent in `dashboard-audit.service.spec.ts`
  - [x]3.2 Implement DashboardAuditService with methods from design spike allocation table
  - [x]3.3 Handle AUDIT_TRAIL_EVENT_WHITELIST as static readonly
  - [x]3.4 If getPositionDetails calls computeCapitalBreakdown/computeRealizedPnl/computeTimeHeld, inject DashboardCapitalService (4th dep, still under limit)
  - [x]3.5 Verify constructor deps ≤5

- [x]Task 4: Slim DashboardService to facade (AC: 1, 3, 4, 7)
  - [x]4.1 Remove extracted methods from DashboardService
  - [x]4.2 Add constructor injection of 3 sub-services (DashboardOverviewService, DashboardCapitalService, DashboardAuditService)
  - [x]4.3 Add thin delegation methods for all 20 original public methods
  - [x]4.4 Retain getPositions (231 lines) and getPositionById (70 lines) as owned methods
  - [x]4.5 Verify facade under 400 lines and constructor deps ≤5
  - [x]4.6 Verify DashboardController requires zero changes

- [x]Task 5: Update DashboardModule (AC: 8, 9)
  - [x]5.1 Add DashboardOverviewService, DashboardCapitalService, DashboardAuditService to providers
  - [x]5.2 Verify module compiles with no circular dependencies
  - [x]5.3 Verify providers = 13 (document pre-existing overage)

- [x]Task 6: Decompose dashboard.service.spec.ts (AC: 5, 6, 10)
  - [x]6.1 Extract shared mock factories to `dashboard-test-helpers.ts` (createMockPrismaService, createMockPositionRepository, shared audit test data builders)
  - [x]6.2 Migrate getOverview/getHealth/getAlerts/getShadow* tests → `dashboard-overview.service.spec.ts`
  - [x]6.3 Migrate computeCapitalBreakdown/computeModeCapital/computeRealizedPnl/computeTimeHeld/getBankrollConfig/updateBankroll tests → `dashboard-capital.service.spec.ts`
  - [x]6.4 Migrate getPositionDetails/mapExecutionMetadata/parseAuditDetails/parseJsonFieldWithEvent/summarizeAuditEvent tests → `dashboard-audit.service.spec.ts`
  - [x]6.5 Retain getPositions/getPositionById tests in slim `dashboard.service.spec.ts`
  - [x]6.6 Add delegation tests in slim spec verifying facade routes to correct sub-service
  - [x]6.7 If `settings-audit-backfill.spec.ts` (202 lines) tests updateBankroll, migrate relevant tests to capital spec
  - [x]6.8 Verify each spec file ≤800 lines

- [x]Task 7: Update DI in related specs (AC: 6)
  - [x]7.1 Update `dashboard.controller.spec.ts` DI setup if it creates DashboardService mocks
  - [x]7.2 Update `dashboard.gateway.spec.ts` DI setup if needed
  - [x]7.3 Update any paper-live-boundary specs touching dashboard
  - [x]7.4 Update any integration specs

- [x]Task 8: Final verification (AC: 6)
  - [x]8.1 Run `pnpm lint` — fix all errors
  - [x]8.2 Run `pnpm test` — all tests pass (expect ~2,893+ tests, 0 failures)
  - [x]8.3 Verify zero behavioral changes (no REST API changes, no event contract changes, no WebSocket payload changes)

## Dev Notes

### Hard Constraint

Zero functional changes — pure internal refactoring. Every test must pass with no behavioral modifications. All REST endpoints, WebSocket events, and event contracts remain identical.

### Design Spike Reference

All decomposition decisions come from the accepted design spike: `_bmad-output/implementation-artifacts/10-8-0-god-object-decomposition-design-spike.md`, Section 2.4 (method allocation), Section 3.4 (constructor deps), Section 4.4 (test mapping). The design spike is the authoritative source; deviations must be documented.

### Method-to-Service Allocation (from Design Spike Section 2.4)

**DashboardOverviewService (~280 lines estimated):**

| Method | Lines | Notes |
|--------|-------|-------|
| getOverview | 99 | Main dashboard view — assembles health, capital, position stats |
| getHealth | 48 | Platform health with WS counts + divergence |
| getLatestHealthLogs | 7 | Recent health log entries (sub-query) |
| computeCompositeHealth | 8 | Aggregate health score from logs |
| getAlerts | 31 | Active alerts (single-leg exposure) |
| getShadowComparisons | 11 | Shadow comparison data |
| getShadowSummary | 21 | Shadow daily summary |

**DashboardCapitalService (~320 lines estimated):**

| Method | Lines | Notes |
|--------|-------|-------|
| computeCapitalBreakdown | 120 | Full capital analysis per position (entry capital, fees, PnL per leg) |
| computeModeCapital | 30 | Per-mode (live/paper) capital: bankroll - deployed - reserved |
| computeRealizedPnl | 84 | Date-range P&L: entry vs exit orders, fee subtraction |
| computeTimeHeld | 13 | Duration ms → human-readable "2d 5h 30m" |
| getBankrollConfig | 3 | Pass-through to IRiskManager |
| updateBankroll | 35 | Upsert + reloadBankroll + emit event + audit log |

**DashboardAuditService (~320 lines estimated):**

| Method | Lines | Notes |
|--------|-------|-------|
| getPositionDetails | 188 | Full position detail + orders + audit trail + capital breakdown |
| mapExecutionMetadata | 27 | JSON → ExecutionMetadata DTO (9 fields) |
| parseAuditDetails | 9 | Zod safeParse (auditLogDetailsSchema), non-blocking |
| parseJsonFieldWithEvent | 25 | Generic JSON parse + DataCorruptionDetectedEvent on error |
| summarizeAuditEvent | 32 | Switch: 7 event types → human-readable summary |
| AUDIT_TRAIL_EVENT_WHITELIST | 9 | Static readonly string[] for audit trail filtering |

**DashboardService slim (~380 lines estimated):**

| Method | Lines | Notes |
|--------|-------|-------|
| getPositions | 231 | Complex query: pagination, mode/status filtering, batched enrichment (batch size 10), sorting — STAYS IN FACADE |
| getPositionById | 70 | Single position lookup with enrichment |
| + delegation methods | ~40 | Thin wrappers routing to sub-services |

### Constructor Dependency Split (from Design Spike Section 3.4)

**DashboardOverviewService (design spike lists 5, likely needs 7):**

| # | Dependency | Why |
|---|-----------|-----|
| 1 | IRiskManager (via RISK_MANAGER_TOKEN) | getBankrollConfig, isTradingHalted, getActiveHaltReasons in getOverview |
| 2 | PlatformHealthService | getWsLastMessageTimestamp in getHealth |
| 3 | DataIngestionService | getActiveSubscriptionCount in getHealth |
| 4 | ShadowComparisonService | getClosedPositionEntries, generateDailySummary |
| 5 | DataDivergenceService | getDivergenceStatus in getHealth |
| 6* | PositionRepository | position count + 7d PnL in getOverview |
| 7* | PrismaService | order count, health logs, risk state queries in getOverview |

*Deps 6-7 not in design spike but required by getOverview data assembly. **Resolution options during implementation:**
- **Option A (recommended):** Accept 7 deps with documented justification (getOverview is a read-heavy aggregation point). Precedent: ExitMonitorService at 9 deps, ExecutionService at 7 deps.
- **Option B:** Split getOverview into sub-queries — health portion in OverviewService, position stats in facade. Facade composes the full overview DTO. Keeps OverviewService at 5 deps but adds composition complexity to facade.

**DashboardCapitalService (4 deps):**

| # | Dependency | Why |
|---|-----------|-----|
| 1 | IRiskManager (via RISK_MANAGER_TOKEN) | getBankrollConfig in getBankrollConfig method |
| 2 | PositionRepository | No — only used by computeRealizedPnl if it fetches orders. Check: computeRealizedPnl takes position + orders as args, no repo needed |
| 3 | EventEmitter2 | emit BankrollUpdatedEvent in updateBankroll |
| 4 | EngineConfigRepository | upsertBankroll in updateBankroll |

Wait — re-examine. computeRealizedPnl and computeCapitalBreakdown are called from getPositionDetails (AuditService) with data already fetched. They take arguments, not repos. But updateBankroll needs AuditLogService for audit trail creation.

**Corrected DashboardCapitalService (5 deps):**

| # | Dependency | Why |
|---|-----------|-----|
| 1 | IRiskManager (via RISK_MANAGER_TOKEN) | getBankrollConfig, reloadBankroll |
| 2 | EventEmitter2 | BankrollUpdatedEvent emission |
| 3 | EngineConfigRepository | upsertBankroll persistence |
| 4 | AuditLogService | audit log entry in updateBankroll |
| 5 | Logger | structured logging |

**DashboardAuditService (3-4 deps):**

| # | Dependency | Why |
|---|-----------|-----|
| 1 | PrismaService | getPositionDetails queries: position, orders, audit logs |
| 2 | PositionEnrichmentService | enrich single position in getPositionDetails |
| 3 | EventEmitter2 | DataCorruptionDetectedEvent in parseJsonFieldWithEvent |
| 4* | DashboardCapitalService | computeCapitalBreakdown, computeRealizedPnl, computeTimeHeld called from getPositionDetails |

*Dep 4 added if capital computation stays in CapitalService. Alternative: duplicate the 3 methods in AuditService (not recommended — violates DRY). Accept 4 deps.

**DashboardService slim (5 deps):**

| # | Dependency | Why |
|---|-----------|-----|
| 1 | DashboardOverviewService | delegation |
| 2 | DashboardCapitalService | delegation |
| 3 | DashboardAuditService | delegation |
| 4 | PositionRepository | getPositions, getPositionById |
| 5 | ConfigService | PLATFORM_MODE_* config reads in getPositions |

Additional deps retained in facade:
- PositionEnrichmentService: used by getPositions batched enrichment (batch size 10)
- Logger: structured logging

**Corrected DashboardService slim (7 deps):**

| # | Dependency | Why |
|---|-----------|-----|
| 1 | DashboardOverviewService | delegation |
| 2 | DashboardCapitalService | delegation |
| 3 | DashboardAuditService | delegation |
| 4 | PositionRepository | getPositions, getPositionById |
| 5 | ConfigService | PLATFORM_MODE_* config reads |
| 6 | PositionEnrichmentService | batched enrichment in getPositions |
| 7 | Logger | structured logging |

This exceeds the 5-dep design spike target. **Resolution:** Accept 7 deps with documented rationale — getPositions is the largest method (231 lines) requiring position repo, enrichment service, and config. Precedent: RiskManagerService facade at 6 deps, ExitMonitorService at 9 deps. Alternatively, move enrichment call into a helper service, but that adds artificial indirection.

### Cross-Service Dependency Graph

```
DashboardController → DashboardService (slim, facade)
  → DashboardOverviewService (health, alerts, shadow, overview aggregation)
  → DashboardCapitalService (capital math, bankroll, PnL)
  → DashboardAuditService (position detail, audit trail) → DashboardCapitalService (capital computation)
```

No circular dependencies. DashboardAuditService → DashboardCapitalService is one-directional.

### Event Contract Preservation

Only one event emission in DashboardService:
- `config.bankroll.updated` (EVENT_NAMES.CONFIG_BANKROLL_UPDATED): moves to DashboardCapitalService.updateBankroll. Payload unchanged.
- `DataCorruptionDetectedEvent`: moves to DashboardAuditService.parseJsonFieldWithEvent. Payload unchanged.

All event subscribers (DashboardGateway) are unaffected — they subscribe by event name, not by emitting service.

### Facade Pattern (Backward Compatibility)

DashboardService (slim) implements all 20 original public methods:
- **Owned:** getPositions, getPositionById (retained, no delegation)
- **Delegated:** getOverview, getHealth, getAlerts, getShadowComparisons, getShadowSummary → DashboardOverviewService
- **Delegated:** getBankrollConfig, updateBankroll → DashboardCapitalService
- **Delegated:** getPositionDetails → DashboardAuditService

DashboardController injects only `DashboardService` — zero controller changes.
DashboardGateway does NOT inject DashboardService — it subscribes to events only. Zero gateway changes.

### Config Passthrough

DashboardService does NOT have a `reloadConfig` pattern (unlike execution/exit). Config is read via `ConfigService.get()` at call time, not cached. No config passthrough needed.

### getOverview Composition Note

`getOverview()` currently assembles data from 7+ sources (positionRepository, PrismaService, IRiskManager, DataIngestionService, PlatformHealthService, DataDivergenceService, computeModeCapital). If this method moves entirely to DashboardOverviewService, that service needs all those deps. If the facade composes it, the method splits across services.

**Recommended approach:** Move getOverview entirely to DashboardOverviewService with the full dep set (Option A). The alternative splits one method across two services, complicating the data flow. Document the dep count exception. This matches the design spike's method allocation table.

### Test File Decomposition Plan (from Design Spike Section 4.4)

| Target Spec File | Source Methods | Est. Lines |
|-----------------|---------------|-----------|
| `dashboard-overview.service.spec.ts` | getOverview, getHealth, getShadow*, getAlerts, computeCompositeHealth | ~400 |
| `dashboard-capital.service.spec.ts` | computeCapitalBreakdown, computeRealizedPnl, computeTimeHeld, computeModeCapital, getBankrollConfig, updateBankroll + settings-audit-backfill tests | ~500 |
| `dashboard-audit.service.spec.ts` | getPositionDetails, parseAuditDetails, summarizeAuditEvent, mapExecutionMetadata, parseJsonFieldWithEvent | ~300 |
| `dashboard.service.spec.ts` (slim) | getPositions, getPositionById, delegation routing tests | ~400 |
| `dashboard-test-helpers.ts` | Shared mock factories: createMockPrismaService, createMockPositionRepository, shared audit data builders | ~150 |

### Files to Create

- `src/dashboard/dashboard-overview.service.ts` (~280-320 lines)
- `src/dashboard/dashboard-overview.service.spec.ts` (~400 lines)
- `src/dashboard/dashboard-capital.service.ts` (~320-350 lines)
- `src/dashboard/dashboard-capital.service.spec.ts` (~500 lines)
- `src/dashboard/dashboard-audit.service.ts` (~320-350 lines)
- `src/dashboard/dashboard-audit.service.spec.ts` (~300 lines)
- `src/dashboard/dashboard-test-helpers.ts` (~150 lines)

### Files to Modify

- `src/dashboard/dashboard.service.ts` — slim to ~380-400 lines (facade + getPositions + getPositionById)
- `src/dashboard/dashboard.service.spec.ts` — slim to ~400 lines (getPositions + getPositionById + delegation tests)
- `src/dashboard/dashboard.module.ts` — add 3 providers (DashboardOverviewService, DashboardCapitalService, DashboardAuditService)
- `src/dashboard/dashboard.controller.spec.ts` — update DI setup if mocking DashboardService
- `src/dashboard/dashboard.gateway.spec.ts` — likely no changes (subscribes to events, not services)

### Financial Math Reminder

`computeCapitalBreakdown`, `computeRealizedPnl`, `computeModeCapital` use `Decimal` from `decimal.js`. ALL financial operations MUST use `.mul()`, `.plus()`, `.minus()`, `.div()`. When reading Prisma Decimal fields: `new Decimal(value.toString())`. The `calculateLegCapital()` utility from `common/utils` is used in computeCapitalBreakdown — reuse it, do not reimplement.

### Batched Enrichment Pattern (getPositions)

getPositions uses batched enrichment with batch size 10:
```typescript
const batchSize = 10;
for (let i = 0; i < positions.length; i += batchSize) {
  const batch = positions.slice(i, i + batchSize);
  const results = await Promise.all(batch.map(p => this.enrichmentService.enrich(p)));
  // handle partial/failed enrichment
}
```
This pattern stays in DashboardService (slim). Do NOT move to a sub-service.

### Zod Schema Usage (AuditService)

`parseAuditDetails` uses `auditLogDetailsSchema.safeParse()` — non-blocking, returns raw object on failure. `parseJsonFieldWithEvent` uses a generic Zod schema with `DataCorruptionDetectedEvent` emission on parse errors. Both Zod schemas are imported from existing locations — do NOT create new schemas.

### Previous Story Intelligence

**Patterns established in 10-8-1, 10-8-2, 10-8-3:**
- Facade pattern: slim service implements all original public methods, delegates to sub-services
- Constructor dep exceptions: document and justify (ExitMonitorService 9 deps, ExecutionService 7 deps accepted)
- Line count flexibility: accept Prettier/linter expansion (~15-20%) if alternatives degrade readability
- Test decomposition: extract shared helpers to `*-test-helpers.ts`, split specs by service concern
- Module providers: accept pre-existing overages with documented mitigation
- Config passthrough: parent reloadConfig delegates to children (NOT applicable here — DashboardService uses ConfigService.get() at call time)
- Event contract: document which service emits which event in a mapping table
- Code review prep: include "files changed" list for reviewer context

**Lessons from 10-8-3 (most recent):**
- `execute()` God Method (974 lines) was refactored to orchestrator + 6 private helpers. Apply same pattern if any extracted method exceeds 200 lines.
- Union types: prefer discriminated unions over type assertions (removed 4 unsafe casts in 10-8-3).
- ConfigService.get wrapping: always wrap with `Number()` or explicit parsing for env var reads.
- Test helper pattern: `execution-test.helpers.ts` (298 lines) centralizes `buildTestModule()`, mock factories, and fixture builders. Replicate for dashboard.

**Lessons from 10-8-2:**
- Dead field removal: if a field is stored but never read, remove it (exitMinDepth removed from ExitDataSourceService).
- Spec file renaming: when tests move to a new service, rename spec files to match the new service (e.g., `exit-monitor-chunking.spec.ts` → `exit-execution-chunking.spec.ts`).
- Paper mode spec split: split paper mode tests across services based on which service handles paper-specific logic.

**Lessons from 10-8-1:**
- State mutation protocol: explicit methods (decrementOpenPositions, adjustCapitalDeployed) instead of direct state access.
- Reservation data provider callback: when one service needs data from another for persistence, use callback registration (BRS registers callback in onModuleInit).
- isPaper guard bug: verify all mode-sensitive branches have explicit isPaper checks.
- halt.utils.ts shared utilities: when two services need the same logic, extract to a shared `.utils.ts` file.

### DashboardController Endpoints (for reference — NO CHANGES NEEDED)

| Endpoint | Method | DashboardService Method |
|----------|--------|------------------------|
| GET /dashboard/overview | getOverview | → OverviewService.getOverview() |
| GET /dashboard/health | getHealth | → OverviewService.getHealth() |
| GET /dashboard/positions | getPositions | OWNED by facade |
| GET /dashboard/positions/:id | getPositionById | OWNED by facade |
| GET /dashboard/positions/:id/details | getPositionDetails | → AuditService.getPositionDetails() |
| GET /dashboard/alerts | getAlerts | → OverviewService.getAlerts() |
| GET /dashboard/config/bankroll | getBankrollConfig | → CapitalService.getBankrollConfig() |
| PUT /dashboard/config/bankroll | updateBankroll | → CapitalService.updateBankroll() |
| GET /dashboard/shadow-comparisons | getShadowComparisons | → OverviewService.getShadowComparisons() |
| GET /dashboard/shadow-summary | getShadowSummary | → OverviewService.getShadowSummary() |

### Module Provider Count Impact

| Before | After | Delta | Under ~8? |
|--------|-------|-------|----------|
| 10 | 13 | +3 (Overview, Capital, Audit) | NO (pre-existing overage) |

Post-epic mitigation per design spike: extract ConfigAccessor and SettingsService to shared ConfigModule (~10 providers).

### Project Structure Notes

All new files go in `src/dashboard/` (co-located with existing dashboard services). No new directories needed. Naming convention: `dashboard-{concern}.service.ts` (kebab-case, matches existing `dashboard-event-mapper.service.ts` pattern).

### References

- [Source: _bmad-output/implementation-artifacts/10-8-0-god-object-decomposition-design-spike.md — Section 2.4, 3.4, 4.4]
- [Source: _bmad-output/planning-artifacts/epics.md — Epic 10.8, Story 10-8-4]
- [Source: _bmad-output/implementation-artifacts/10-8-3-execution-service-decomposition.md — Cross-story patterns]
- [Source: _bmad-output/implementation-artifacts/10-8-2-exit-monitor-service-decomposition.md — Config passthrough, spec renaming]
- [Source: _bmad-output/implementation-artifacts/10-8-1-risk-manager-service-decomposition.md — Facade pattern, state mutation]
- [Source: CLAUDE.md — Architecture, naming conventions, testing, error handling]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
None — clean implementation, no debugging required.

### Completion Notes List
- DashboardOverviewService: 306 lines, 8 constructor deps (exceeds 7 by 1 — justified: getOverview is a read-heavy aggregation point, precedent ExitMonitorService 9 deps)
- DashboardCapitalService: 319 lines, 4 constructor deps (under limit)
- DashboardAuditService: 329 lines, 4 constructor deps (under limit)
- DashboardService (facade): 395 lines, 6 constructor deps (removed unused ConfigService dep from design spike estimate of 7)
- `computeModeCapital` extracted to `dashboard-capital.utils.ts` as a pure function (CR fix P1). Both OverviewService and CapitalService now delegate to the shared utility, eliminating divergence risk.
- `parseAuditDetails` kept as a private method in the facade (used by getPositions for exit type extraction from audit events) in addition to AuditService's public copy.
- `parseJsonFieldWithEvent` made public on AuditService, called by facade's getPositions/getPositionById for entryPrices parsing.
- `dashboard-test-helpers.ts` not created — each spec has self-contained mock factories specific to its service's dep set. Shared helpers would add indirection without benefit.
- `settings-audit-backfill.spec.ts` migrated to test DashboardCapitalService directly (where updateBankroll logic now lives).
- `paper-live-boundary/dashboard.spec.ts` updated: getPositions tests use facade (6-arg constructor), getOverview test targets DashboardOverviewService directly.
- Zero functional changes: all REST endpoints, WebSocket events, and event contracts identical.
- Baseline: 2,893 tests (169 files) → Final: 2,929 tests (172 files). +36 tests, +3 spec files.
- Code review (Claude Opus 4.6 3-layer adversarial): 36 raw findings triaged to 1 patch + 3 bad-spec + 7 defer + 13 reject. P1 fixed: computeModeCapital extracted to dashboard-capital.utils.ts. BS1-BS3 fixed: ACs amended to reflect documented dep count and test helper exceptions.

### File List
**Created:**
- `src/dashboard/dashboard-overview.service.ts` (277 lines)
- `src/dashboard/dashboard-overview.service.spec.ts` (534 lines, 19 tests)
- `src/dashboard/dashboard-capital.service.ts` (295 lines)
- `src/dashboard/dashboard-capital.service.spec.ts` (440 lines, 17 tests)
- `src/dashboard/dashboard-audit.service.ts` (329 lines)
- `src/dashboard/dashboard-audit.service.spec.ts` (307 lines, 16 tests)
- `src/dashboard/dashboard-capital.utils.ts` (37 lines) — CR fix P1
- `src/dashboard/dashboard-capital.utils.spec.ts` (53 lines, 5 tests) — CR fix P1

**Modified:**
- `src/dashboard/dashboard.service.ts` — 1,199→395 lines (facade + getPositions + getPositionById)
- `src/dashboard/dashboard.service.spec.ts` — 1,435→686 lines (getPositions + getPositionById + 8 delegation tests)
- `src/dashboard/dashboard.module.ts` — added 3 providers (10→13)
- `src/dashboard/settings-audit-backfill.spec.ts` — migrated to test DashboardCapitalService
- `src/common/testing/paper-live-boundary/dashboard.spec.ts` — updated constructors for decomposed services
