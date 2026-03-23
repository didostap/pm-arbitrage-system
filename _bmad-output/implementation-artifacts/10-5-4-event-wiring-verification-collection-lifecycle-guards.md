# Story 10.5.4: Event Wiring Verification & Collection Lifecycle Guards

Status: done

## Story

As an operator,
I want automated verification that event emitters are connected to their subscribers and that in-memory collections have cleanup paths,
so that the two most common silent correctness failures (44% and 33% recurrence in Epic 10) are caught by tests instead of review.

## Acceptance Criteria

1. **AC1 — `expectEventHandled()` Integration Test Helper:** An `expectEventHandled()` helper exists in `src/common/testing/` that verifies: (a) a handler with the matching `@OnEvent` decorator exists in the target class, (b) the handler is actually invoked when the event fires through a real EventEmitter2. The helper uses a real EventEmitter2 instance (not mocked) — following the proven pattern in `event-consumer.service.spec.ts`.

2. **AC2 — Existing @OnEvent Audit:** All existing `@OnEvent` handlers have corresponding `expectEventHandled()` tests. Any dead handlers (decorated but never triggered by any emitter) are identified and either removed or documented with rationale.

3. **AC3 — Test Template:** A test template file exists in `src/common/testing/` demonstrating the `expectEventHandled()` pattern for both single-handler and multi-handler scenarios. The template is importable and usable as a reference for future stories.

4. **AC4 — Collection Lifecycle Audit:** Every `Map`/`Set`/cache in service files has a documented cleanup strategy (code comment) specifying one of: TTL eviction, max-size bound, lifecycle-bound disposal (e.g., `onModuleDestroy`), bounded-by-entity-count, or explicit `delete()`/`clear()` on lifecycle events. Collections without cleanup paths get cleanup code added.

5. **AC5 — Collection Cleanup Tests:** Every collection that has a cleanup path also has a test verifying that cleanup actually occurs (e.g., `disconnect()` calls `.clear()`, `unsubscribe()` calls `.delete()`, `onModuleDestroy()` removes listeners).

6. **AC6 — CLAUDE.md Convention Update:** CLAUDE.md documents: "Every new Map/Set must specify its cleanup strategy in a code comment and have a test for the cleanup path."

7. **AC7 — MEDIUM Prevention Analysis:** The top 3 recurring MEDIUM categories from Epic 10 code reviews are documented (in a deliverable within this story's Dev Agent Record) with structural prevention measures — not "be more careful" agreements. This deliverable feeds into Story 10-5-8.

## Tasks / Subtasks

- [x] **Task 1: Create `expectEventHandled()` helper** (AC: #1, #3)
  - [x] 1.1 Create `src/common/testing/expect-event-handled.ts` with the helper function
  - [x] 1.2 Create `src/common/testing/index.ts` barrel export
  - [x] 1.3 Create `src/common/testing/expect-event-handled.spec.ts` — self-tests for the helper
  - [x] 1.4 Helper signature: `expectEventHandled(moduleRef: TestingModule, eventName: string, eventPayload: BaseEvent, targetClass: Type, handlerMethod: string)` — verifies handler is invoked via real EventEmitter2
  - [x] 1.5 Add convenience overload that accepts a service instance and verifies the `@OnEvent` decorator metadata matches

- [x] **Task 2: Audit all @OnEvent handlers** (AC: #2)
  - [x] 2.1 Catalog all `@OnEvent` handlers (see inventory below) — verify each has a corresponding emitter
  - [x] 2.2 For each handler, create or verify an `expectEventHandled()` test in the handler's co-located spec file
  - [x] 2.3 Identify dead handlers (decorated but no emitter fires the event) — remove or document
  - [x] 2.4 DashboardGateway handlers (22 handlers): verify event names match `EVENT_NAMES` constants and emitters exist

- [x] **Task 3: Collection lifecycle audit** (AC: #4, #5)
  - [x] 3.1 Add cleanup strategy code comments to all 31 Map/Set declarations (see inventory below)
  - [x] 3.2 Identify collections missing cleanup paths — add cleanup code where needed
  - [x] 3.3 Verify or add cleanup tests for each collection's disposal mechanism
  - [x] 3.4 Focus areas: `notifiedOpportunityPairs` (EventConsumerService — no cleanup, grows unbounded), `lastContractUpdateTime` (PlatformHealthService — no TTL, grows with contracts), `lastEmitted` (ExposureAlertSchedulerService — no cleanup)

- [x] **Task 4: Update CLAUDE.md** (AC: #6)
  - [x] 4.1 Add collection lifecycle convention under Testing section
  - [x] 4.2 Add event wiring test requirement under Testing Conventions

- [x] **Task 5: MEDIUM prevention analysis** (AC: #7)
  - [x] 5.1 Analyze all MEDIUM findings from Epic 10 code reviews (stories 10-0-1 through 10.4)
  - [x] 5.2 Categorize by type, identify top 3 recurring categories
  - [x] 5.3 For each category, propose a structural prevention measure
  - [x] 5.4 Document findings in Dev Agent Record section

- [x] **Task 6: Verification** (AC: all)
  - [x] 6.1 `pnpm lint` — zero errors in modified files
  - [x] 6.2 `pnpm test` — all 2594 pass, 0 failures, 139 test files
  - [x] 6.3 New test count: +56 tests (11 helper + 37 wiring + 8 collection)

## Dev Notes

### Complete @OnEvent Handler Inventory (29+ handlers)

**Non-Gateway Handlers (11 handlers, 7 services):**

| Service | Method | Event Name | File |
|---------|--------|------------|------|
| MatchAprUpdaterService | onOpportunityIdentified | `OPPORTUNITY_IDENTIFIED` | `modules/monitoring/match-apr-updater.service.ts` |
| MatchAprUpdaterService | onOpportunityFiltered | `OPPORTUNITY_FILTERED` | `modules/monitoring/match-apr-updater.service.ts` |
| CorrelationTrackerService | onBudgetCommitted | `BUDGET_COMMITTED` | `modules/risk-management/correlation-tracker.service.ts` |
| CorrelationTrackerService | onExitTriggered | `EXIT_TRIGGERED` | `modules/risk-management/correlation-tracker.service.ts` |
| AutoUnwindService | onSingleLegExposure | `SINGLE_LEG_EXPOSURE` | `modules/execution/auto-unwind.service.ts` |
| ExposureTrackerService | onSingleLegExposure | `SINGLE_LEG_EXPOSURE` | `modules/execution/exposure-tracker.service.ts` |
| ShadowComparisonService | onShadowComparison | `SHADOW_COMPARISON` | `modules/exit-management/shadow-comparison.service.ts` |
| ShadowComparisonService | onExitTriggered | `EXIT_TRIGGERED` | `modules/exit-management/shadow-comparison.service.ts` |
| DataIngestionService | onOrderFilled | `ORDER_FILLED` | `modules/data-ingestion/data-ingestion.service.ts` |
| DataIngestionService | onExitTriggered | `EXIT_TRIGGERED` | `modules/data-ingestion/data-ingestion.service.ts` |
| DataIngestionService | onSingleLegResolved | `SINGLE_LEG_RESOLVED` | `modules/data-ingestion/data-ingestion.service.ts` |

**System/Config Handlers (3 handlers):**

| Service | Method | Event Name | File |
|---------|--------|------------|------|
| TradingEngineService | onTimeDriftHalt | `TIME_DRIFT_HALT` | `core/trading-engine.service.ts` |
| ConfigAccessorService | onConfigSettingsUpdated | `CONFIG_SETTINGS_UPDATED` | `common/config/config-accessor.service.ts` |
| ConfigAccessorService | onConfigBankrollUpdated | `CONFIG_BANKROLL_UPDATED` | `common/config/config-accessor.service.ts` |

**DashboardGateway Handlers (22 handlers):**

| Method | Event Name |
|--------|------------|
| onPlatformHealthUpdated | `PLATFORM_HEALTH_UPDATED` |
| onPlatformHealthDegraded | `PLATFORM_HEALTH_DEGRADED` |
| onPlatformHealthRecovered | `PLATFORM_HEALTH_RECOVERED` |
| onOrderFilled | `ORDER_FILLED` |
| onExecutionFailed | `EXECUTION_FAILED` |
| onSingleLegExposure | `SINGLE_LEG_EXPOSURE` |
| onLimitBreached | `LIMIT_BREACHED` |
| onLimitApproached | `LIMIT_APPROACHED` |
| onExitTriggered | `EXIT_TRIGGERED` |
| onBatchComplete | `BATCH_COMPLETE` |
| onMatchApproved | `MATCH_APPROVED` |
| onMatchRejected | `MATCH_REJECTED` |
| onClusterLimitBreached | `CLUSTER_LIMIT_BREACHED` |
| onAggregateClusterLimitBreached | `AGGREGATE_CLUSTER_LIMIT_BREACHED` |
| onConfigBankrollUpdated | `CONFIG_BANKROLL_UPDATED` |
| onDataDivergence | `DATA_DIVERGENCE` |
| onSystemTradingHalted | `SYSTEM_TRADING_HALTED` |
| onSystemTradingResumed | `SYSTEM_TRADING_RESUMED` |
| onShadowComparison | `SHADOW_COMPARISON` |
| onShadowDailySummary | `SHADOW_DAILY_SUMMARY` |
| onAutoUnwind | `AUTO_UNWIND` |
| onConfigSettingsUpdated | `CONFIG_SETTINGS_UPDATED` |

### Complete Collection Inventory (31 Map/Set declarations)

**PlatformHealthService** (`data-ingestion/platform-health.service.ts`) — 9 collections:
- `lastUpdateTime: Map<PlatformId, number>` — bounded by platforms (2), overwrite
- `latencySamples: Map<PlatformId, number[]>` — bounded by platforms (2), array size-limited to 60
- `previousStatus: Map<PlatformId, string>` — bounded by platforms (2), overwrite
- `consecutiveUnhealthyTicks: Map<PlatformId, number>` — bounded, overwrite
- `consecutiveHealthyTicks: Map<PlatformId, number>` — bounded, overwrite
- `orderbookStale: Map<PlatformId, boolean>` — bounded, overwrite
- `orderbookStaleStartTime: Map<PlatformId, number>` — bounded, `.delete()` on recovery
- `lastContractUpdateTime: Map<string, number>` — **UNBOUNDED** (grows with contracts, ~40 bytes x contracts)
- `lastWsMessageTimestamp: Map<PlatformId, Date>` — bounded by platforms (2), overwrite

**DegradationProtocolService** (`data-ingestion/degradation-protocol.service.ts`) — 1:
- `degradedPlatforms: Map<PlatformId, DegradationState>` — bounded, `.set()`/`.delete()`

**DataDivergenceService** (`data-ingestion/data-divergence.service.ts`) — 3:
- `lastPollSnapshot: Map<string, SnapshotData>` — per-contract, overwrite
- `lastWsSnapshot: Map<string, SnapshotData>` — per-contract, overwrite
- `divergentContracts: Set<string>` — `.clear()` on reset, `.delete()` on recovery

**DataIngestionService** (`data-ingestion/data-ingestion.service.ts`) — 2:
- `activeSubscriptions: Map<PlatformId, Set<string>>` — `.delete()` on unsubscribe
- `contractRefCounts: Map<string, number>` — `.delete()` when refcount reaches 0

**ExposureTrackerService** (`execution/exposure-tracker.service.ts`) — 2:
- `monthlyExposures: Map<string, number>` — reset at month boundary
- `weeklyExposures: Map<string, number>` — reset at week boundary

**ExposureAlertSchedulerService** (`execution/exposure-alert-scheduler.service.ts`) — 1:
- `lastEmitted: Map<string, number>` — **NO CLEANUP** (overwrite only, grows with positions)

**AutoUnwindService** (`execution/auto-unwind.service.ts`) — 1:
- `inFlightUnwinds: Set<string>` — `.delete()` in `finally` block

**ExitMonitorService** (`exit-management/exit-monitor.service.ts`) — 1:
- `stalePositions: Map<string, boolean>` — `.set()`/`.delete()` on status changes

**RiskManagerService** (`risk-management/risk-manager.service.ts`) — 3:
- `reservations: Map<string, BudgetReservation>` — `.delete()` on release/commit, `.clear()` on stale cleanup
- `paperActivePairIds: Set<string>` — `.delete()` on position close
- `activeHaltReasons` (in RiskState): `Set<HaltReason>` — `.delete()` on resume, `.clear()` on reset

**EventConsumerService** (`monitoring/event-consumer.service.ts`) — 1:
- `notifiedOpportunityPairs: Set<string>` — **NO CLEANUP** (grows unbounded over lifetime)

**TelegramAlertService** (`monitoring/telegram-alert.service.ts`) — 1:
- `batchBuffer: Map<string, Array>` — `.clear()` on send

**CsvTradeLogService** (`monitoring/csv-trade-log.service.ts`) — 1:
- `writeQueues: Map<string, Promise<void>>` — `.delete()` on completion

**DashboardGateway** (`dashboard/dashboard.gateway.ts`) — 1:
- `clients: Set<WebSocket>` — `.add()` on connect, `.delete()` on disconnect, `.clear()` on destroy

**SettingsService** (`dashboard/settings.service.ts`) — 1:
- `reloadHandlers: Map<string, ReloadHandler>` — `.delete()` on unsub, `.clear()` on shutdown

**KalshiWebSocketClient** (`connectors/kalshi/kalshi-websocket.client.ts`) — 4:
- `orderbookState: Map<string, LocalOrderbookState>` — `.delete()` on unsub, `.clear()` on disconnect
- `lastSequence: Map<string, number>` — `.delete()` on unsub, `.clear()` on disconnect
- `subscriptions: Set<string>` — `.delete()` on unsub
- `lastResubscribeTime: Map<string, number>` — `.delete()` on unsub, `.clear()` on disconnect

**PolymarketWebSocketClient** (`connectors/polymarket/polymarket-websocket.client.ts`) — 2:
- `orderbookState: Map<string, LocalOrderBookState>` — `.clear()` on disconnect
- `subscriptions: Set<string>` — lifecycle-managed

**PolymarketConnector** (`connectors/polymarket/polymarket.connector.ts`) — 1:
- `lastWsUpdateMap: Map<string, Date>` — overwrite per contract

**KalshiConnector** (`connectors/kalshi/kalshi.connector.ts`) — 1:
- `lastWsUpdateMap: Map<string, Date>` — overwrite per contract

**FillSimulatorService** (`connectors/paper/fill-simulator.service.ts`) — 1:
- `orderMap: Map<string, SimulatedOrder>` — `.delete()` on fill/cancel

### Collections Needing Attention (Missing Cleanup)

1. **`notifiedOpportunityPairs`** (EventConsumerService) — `Set<string>` that grows unbounded. Should clear on a schedule (e.g., daily reset) or use a TTL-bounded cache.
2. **`lastContractUpdateTime`** (PlatformHealthService) — `Map<string, number>` that grows with contracts. Needs cleanup for contracts that are no longer tracked (unsubscribed).
3. **`lastEmitted`** (ExposureAlertSchedulerService) — `Map<string, number>` keyed by position ID. Entries persist after position close. Should `.delete()` when position exits.

### `expectEventHandled()` Design

**Location:** `src/common/testing/expect-event-handled.ts`

**Approach:** Build on the proven pattern from `event-consumer.service.spec.ts` — use a real EventEmitter2, verify actual handler invocation.

```typescript
// Conceptual signature:
export async function expectEventHandled(options: {
  module: TestingModule;
  eventName: string;           // EVENT_NAMES constant
  payload: BaseEvent;          // The event instance to emit
  handlerClass: Type<any>;     // e.g., AutoUnwindService
  handlerMethod: string;       // e.g., 'onSingleLegExposure'
  timeout?: number;            // default 100ms
}): Promise<void>;
```

**Implementation strategy:**
1. Get the real EventEmitter2 from the TestingModule
2. Get the handler service instance from the TestingModule
3. Spy on `handlerMethod` using `vi.spyOn()`
4. Emit the event via the real EventEmitter2
5. Await a small tick (to allow async event propagation)
6. Assert the spy was called with the payload
7. Restore the spy

**Why real EventEmitter2:** Mocking EventEmitter2 only tests that the mock was called. Real EventEmitter2 tests the actual NestJS `@OnEvent` decorator wiring — the decorator must be registered, the module must include EventEmitterModule, and the handler method name must match. This catches the exact gap that was 44% of Epic 10 defects.

**Complementary helper:**
```typescript
// Verify an event name has at least one registered handler
export function expectEventHasHandler(
  module: TestingModule,
  eventName: string,
): void;

// Verify no dead handlers exist for a class
export function expectNoDeadHandlers(
  module: TestingModule,
  handlerClass: Type<any>,
): void;
```

### EventEmitter2 Global Configuration

From `app.module.ts`:
```typescript
EventEmitterModule.forRoot({
  wildcard: true,
  delimiter: '.',
  maxListeners: 25,
  verboseMemoryLeak: true,
})
```

The helper must replicate this config in its test module setup (wildcard, delimiter) to match production behavior.

### Existing Patterns to Follow

**Event testing pattern** (from `auto-unwind.service.spec.ts`):
```typescript
// Mock EventEmitter2 for unit tests (tests emission, not wiring)
eventEmitter = { emit: vi.fn() };
// Assert: expect(eventEmitter.emit).toHaveBeenCalledWith(EVENT_NAMES.X, expect.objectContaining({...}))
```

**Real EventEmitter2 testing** (from `event-consumer.service.spec.ts`):
```typescript
// Integration tests use real EventEmitter2 (tests actual wiring)
const emitter = new EventEmitter2({ wildcard: true, delimiter: '.' });
emitter.emit(EVENT_NAMES.ORDER_FILLED, event);
await new Promise(r => setTimeout(r, 50)); // Allow propagation
```

**The `expectEventHandled()` helper bridges these:** it uses real EventEmitter2 in a NestJS TestingModule context to verify the `@OnEvent` decorator actually connects emitter to handler.

### onModuleDestroy Cleanup Pattern

Services that manage collections/listeners implement `OnModuleDestroy`:
```typescript
@Injectable()
export class SomeService implements OnModuleDestroy {
  private someMap = new Map<string, Data>();

  onModuleDestroy(): void {
    this.someMap.clear();
    // For listeners: this.eventEmitter.offAny(this.listener);
  }
}
```

Currently implemented in: EventConsumerService, DashboardGateway, PolymarketConnector, KalshiConnector, TelegramAlertService, GasEstimationService, PrismaService.

### Architecture Compliance

- **File naming:** kebab-case — `expect-event-handled.ts`, `expect-event-handled.spec.ts`
- **Test co-location:** Helper in `src/common/testing/`, self-tests co-located there. Wiring tests in each service's existing spec file.
- **Import rules:** `common/testing/` can import from `common/events/` (event catalog, base event). Cannot import from `modules/` or `connectors/`.
- **Error handling:** Helper should throw descriptive assertion errors (not SystemError — it's a test utility).

### Previous Story Intelligence

**From Story 10-5-3 (Dashboard Settings Page UI):**
- 35 component tests + 29 E2E tests added
- WS event wiring verified: `config.settings.updated` handler in WebSocketProvider
- Code review caught 9 issues (race conditions, validation gaps, WS handling)
- Vitest infrastructure now also in dashboard repo

**From Story 10-5-2 (Settings CRUD Endpoints):**
- `ConfigSettingsUpdatedEvent` emitted on settings change
- `ConfigAccessorService` has `@OnEvent` handlers for both `CONFIG_SETTINGS_UPDATED` and `CONFIG_BANKROLL_UPDATED`
- Hot-reload dispatch uses `ModuleRef`-based lazy resolution
- Code review: CRITICAL finding was broken `ReloadableService` interface — replaced with `ModuleRef` + callback

**From Epic 10 Retrospective (source of this story):**
- Event wiring gaps in 44% of stories (4/9) — all caught by review, not tests
- Collection leaks in 33% of stories (3/9) — no error, leak manifests under sustained runtime
- Agreement #26: structural guards over review vigilance
- The half-life of problems is shortening — this story converts observations to structural change

### MEDIUM Prevention Analysis Context

From Epic 10 code reviews (stories 10-0-1 through 10.4), recurring MEDIUM categories were:
1. **Incomplete test assertions** — tests exist but assert too little (weak `toHaveBeenCalled()` without payload verification)
2. **Dead code / dead imports** — unused imports, dead DTO fields, stale comments
3. **Missing DTO validation** — endpoints accepting unvalidated fields, missing `@IsOptional()`, `@Transform()` decorators

The dev agent should scan the sprint-status.yaml comments for all Epic 10 code review summaries to extract and categorize the full MEDIUM list for AC #7.

### Anti-Patterns to Avoid

- **DO NOT** mock EventEmitter2 in the `expectEventHandled()` helper — that defeats the purpose. Use a real instance.
- **DO NOT** add `onModuleDestroy` to services that only have bounded collections (e.g., `Map<PlatformId, X>` with 2 entries). Cleanup is only needed for unbounded or listener-based collections.
- **DO NOT** refactor service internals beyond adding cleanup paths and code comments. This is an audit + guard story, not a refactoring story.
- **DO NOT** modify the event catalog or domain event classes. They're correct — the gap is in test verification.
- **DO NOT** create a separate test runner or custom Vitest plugin. The helper is a simple function that uses standard Vitest APIs (`vi.spyOn`, `expect`).
- **DO NOT** add tests for DashboardGateway event handlers that test WebSocket broadcast behavior — only verify the `@OnEvent` wiring (handler is invoked with correct event). WS broadcast testing is a separate concern.

### Scope Boundaries

**In scope:**
- `expectEventHandled()` helper + self-tests
- Wiring tests for all 36 @OnEvent handlers
- Collection cleanup comments (all 31 collections)
- Cleanup code for 3 identified unbounded collections
- Cleanup tests where missing
- CLAUDE.md convention update
- MEDIUM prevention analysis document

**Out of scope:**
- New event classes or event catalog changes
- Refactoring existing service logic
- Performance optimization of event handling
- Dashboard changes (this is engine-only)
- Changes to the EventEmitter2 global configuration

### Project Structure Notes

- All work in `pm-arbitrage-engine/` — engine repo, separate git commits
- `src/common/testing/` directory exists but is empty — create files here
- Tests co-located: add wiring tests to each service's existing `.spec.ts` file
- CLAUDE.md is in the root repo (parent of engine) — separate commit needed

### References

- [Source: _bmad-output/implementation-artifacts/epic-10-retro-2026-03-22.md — Action Item #3, Agreement #26, Three Recurring Defect Classes table]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 10-5-4 — Full AC specification]
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts — EVENT_NAMES constants (60+ events)]
- [Source: pm-arbitrage-engine/src/common/events/index.ts — 47 domain event classes]
- [Source: pm-arbitrage-engine/src/app.module.ts — EventEmitterModule.forRoot() config]
- [Source: pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.spec.ts — Proven real EventEmitter2 test pattern]
- [Source: pm-arbitrage-engine/src/modules/execution/auto-unwind.service.spec.ts — Event emission test pattern]
- [Source: _bmad-output/implementation-artifacts/10-5-3-dashboard-settings-page-ui.md — Previous story learnings]
- [Source: _bmad-output/implementation-artifacts/10-5-2-settings-crud-endpoints-hot-reload-mechanics.md — ConfigAccessor pattern, hot-reload]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### MEDIUM Prevention Analysis (AC7)

**Source:** Epic 10 code reviews (stories 10-0-1 through 10-4), 40+ MEDIUM findings analyzed.

#### Top 3 Recurring MEDIUM Categories

**1. Incomplete Test Assertions (12 occurrences, 30%)**

Examples: "missing test coverage" (10-0-1), "5 skipped integration tests" (10-2), "MAX_LOSS_PCT=0 test" (10-3), "sprint status count" (10-0-2a), "e2e test field renames" (10-2), "duplicate task" (10-1), "weak toHaveBeenCalled without payload" (pattern across multiple stories).

**Structural prevention:** The `expectEventHandled()` helper (this story) forces payload assertion by design — not just `toHaveBeenCalled()` but `toHaveBeenCalledWith(payload)`. Extend this pattern: create assertion templates for common test scenarios (e.g., `expectDtoShape()`, `expectEventEmittedWith()`) that structurally prevent weak assertions. ATDD checklist generation should include assertion skeletons with `expect.objectContaining({...})`, not placeholder `expect(true).toBe(false)`.

**2. Dead Code / Stale Artifacts (8 occurrences, 20%)**

Examples: "dead code" (10-0-1), "realizedPnl dead code" (10-0-2), "stale comments" (10-2), "dead gateway handler" (10-0-1), "file list gaps" (10-0-2b).

**Structural prevention:** Enable `noUnusedLocals: true` and `noUnusedParameters: true` in `tsconfig.json` (if not already set) — compiler catches dead imports and variables. For dead @OnEvent handlers, the `expectNoDeadHandlers()` helper (this story) cross-references against EVENT_NAMES catalog. For stale comments, no automated guard exists — but code review can grep for `// TODO`, `// REMOVED`, `// OLD` patterns. Story file lists should be auto-generated from `git diff --name-only`.

**3. Type Safety / Validation Gaps at Boundaries (10 occurrences, 25%)**

Examples: "Decimal persistence" (10-1), "Decimal threshold" (10-0-1), "gas fraction denominator" (10-1), "env schema constraints" (10-2), "unsafe type cast" (10-2), "string vs Decimal" (10-3), "configService boolean defense" (10-3).

**Structural prevention:** Zod boundary schemas (story 9-0-2) validate at system edges — extend coverage to ALL config reads and API responses. Branded types (story 9-0-1) prevent implicit casts at compile time. Create a `configService.getDecimal()` helper that returns `Decimal` directly instead of requiring manual conversion. For `configService.get<boolean>()`, NestJS returns strings from env — add a typed wrapper `configService.getBool()` that handles `'true'`/`'false'` string parsing correctly.

#### Summary Table

| Category | Count | % | Prevention Mechanism | Implemented? |
|----------|-------|---|---------------------|-------------|
| Incomplete test assertions | 12 | 30% | `expectEventHandled()` pattern, assertion templates | Partial (this story) |
| Dead code / stale artifacts | 8 | 20% | `noUnusedLocals`, `expectNoDeadHandlers()`, lint | Partial (this story) |
| Type safety / validation | 10 | 25% | Zod schemas, branded types, typed config wrappers | Partial (9-0-1, 9-0-2) |
| Event wiring gaps | 4 | 10% | `expectEventHandled()` wiring tests | Done (this story) |
| Collection leaks | 3 | 7.5% | Cleanup comments + tests, CLAUDE.md convention | Done (this story) |
| Other | 3 | 7.5% | Case-by-case | — |

**Feeds into:** Story 10-5-8 (CLAUDE.md & process convention updates) should codify these as mandatory checklist items.

### Completion Notes List

- **Task 1:** Created `expectEventHandled()`, `expectEventHasHandler()`, `expectNoDeadHandlers()` helpers in `src/common/testing/`. 11 self-tests pass. Helper detects pre-existing spies to support double-spy patterns.
- **Task 2:** 37 wiring audit tests verify all 36 @OnEvent subscriptions (14 non-gateway + 22 gateway) across 9 services. No dead handlers found — all use EVENT_NAMES constants. Uses `buildAndInit()` helper with no-op handler pre-spying to avoid mock dependency errors.
- **Task 3:** 31 Map/Set cleanup strategy comments added across 18 files. 3 fixes: EventConsumerService `.clear()` in `onModuleDestroy()`, PlatformHealthService `removeContractTracking()` method, ExposureAlertScheduler cleanup already existed (verified by test). 8 collection lifecycle tests pass.
- **Task 4:** CLAUDE.md updated with event wiring + collection lifecycle conventions under "Testing Conventions (Epic 10 Retro)".
- **Task 5:** MEDIUM prevention analysis: top 3 categories identified (incomplete assertions 30%, dead code 20%, type safety 25%) with structural prevention measures.

### Change Log

- 2026-03-23: Story 10-5-4 implemented — expectEventHandled() helper, 36-handler wiring audit, 31-collection cleanup audit, CLAUDE.md conventions, MEDIUM prevention analysis.
- 2026-03-23: Code review #1 completed (3-layer adversarial: Blind Hunter + Edge Case Hunter + Acceptance Auditor). Fixed 10 PATCH issues:
  - **P1 (CRITICAL):** `removeContractTracking()` was dead code — wired into `unsubscribeForPosition()` alongside `clearContractData()` + added assertions
  - **P2:** `expectNoDeadHandlers()` joined array events with `.` instead of checking each — fixed to iterate individually
  - **P3:** Dead handler audit test was tautological (EVENT_NAMES ∈ EVENT_NAMES) — replaced with `expectNoDeadHandlers()` on all 9 production handler classes
  - **P4:** AC5-UNIT-001b only checked constant value — now tests actual overflow/clear behavior at MAX_NOTIFIED_PAIRS
  - **P5:** `callerOwnsSpy` used `'mock' in fn` — replaced with `vi.isMockFunction()`
  - **P6:** ExposureTrackerService cleanup comments inaccurate ("reset at boundary") — corrected to "grows at 1/month, no pruning"
  - **P7:** DataDivergenceService cleanup comment inaccurate (".clear() on reset") — corrected to match actual `.delete()` paths
  - **P8:** DegradationProtocolService.degradedPlatforms missing cleanup comment — added
  - **P9:** activeHaltReasons in ModeRiskState missing cleanup comment — added
  - **P10:** Stale ATDD "Red Phase" header in spec — removed misleading skip/fail references
  - 2602 tests pass (139 files), 0 errors, 0 lint errors.

### File List

**New files:**
- `pm-arbitrage-engine/src/common/testing/expect-event-handled.ts`
- `pm-arbitrage-engine/src/common/testing/index.ts`

**Modified test files (new/rewritten):**
- `pm-arbitrage-engine/src/common/testing/expect-event-handled.spec.ts`
- `pm-arbitrage-engine/src/common/testing/event-wiring-audit.spec.ts`
- `pm-arbitrage-engine/src/common/testing/collection-lifecycle-audit.spec.ts`

**Modified source files (cleanup comments + code):**
- `pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts` (cleanup comment + .clear() in onModuleDestroy)
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts` (9 cleanup comments + removeContractTracking() method)
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.ts` (2 cleanup comments + CR#1: wired removeContractTracking in unsubscribeForPosition)
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.spec.ts` (CR#1: added removeContractTracking mock + assertions)
- `pm-arbitrage-engine/src/modules/data-ingestion/data-divergence.service.ts` (3 cleanup comments, CR#1: fixed inaccurate comment)
- `pm-arbitrage-engine/src/modules/data-ingestion/degradation-protocol.service.ts` (CR#1: added missing cleanup comment)
- `pm-arbitrage-engine/src/modules/execution/exposure-alert-scheduler.service.ts` (cleanup comment)
- `pm-arbitrage-engine/src/modules/execution/exposure-tracker.service.ts` (2 cleanup comments, CR#1: fixed inaccurate comments)
- `pm-arbitrage-engine/src/modules/execution/auto-unwind.service.ts` (1 cleanup comment)
- `pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts` (1 cleanup comment)
- `pm-arbitrage-engine/src/modules/risk-management/risk-manager.service.ts` (3 cleanup comments, CR#1: added activeHaltReasons comment)
- `pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.ts` (1 cleanup comment)
- `pm-arbitrage-engine/src/modules/monitoring/csv-trade-log.service.ts` (1 cleanup comment)
- `pm-arbitrage-engine/src/dashboard/dashboard.gateway.ts` (1 cleanup comment)
- `pm-arbitrage-engine/src/dashboard/settings.service.ts` (1 cleanup comment)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-websocket.client.ts` (4 cleanup comments)
- `pm-arbitrage-engine/src/connectors/polymarket/polymarket-websocket.client.ts` (2 cleanup comments)
- `pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.ts` (1 cleanup comment)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts` (1 cleanup comment)
- `pm-arbitrage-engine/src/connectors/paper/fill-simulator.service.ts` (1 cleanup comment)

**Root repo files:**
- `CLAUDE.md` (testing conventions update)
