# Story 2.4: Graceful Degradation & Automatic Recovery

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Epic Deviations

**1. "Opportunity thresholds widened by 1.5x" — implemented as configurable multiplier, not business logic**
- **Epic AC states:** "opportunity thresholds are widened by 1.5x on remaining healthy platforms (NFR-R2)"
- **This story implements:** A `DegradationProtocolService` that exposes a `getThresholdMultiplier(platformId): number` method returning 1.0 (normal) or a configurable value (default 1.5) when a platform is degraded. The actual threshold application happens in Epic 3's detection service — this story only provides the multiplier infrastructure.
- **Rationale:** Epic 3 (arbitrage detection) doesn't exist yet. This story provides the data; Epic 3 consumes it.

**2. "Cancel pending orders" — event-only, no execution module yet**
- **Epic AC states:** "downstream modules (execution, when it exists) will subscribe to for cancelling pending orders and halting new trades"
- **This story implements:** Emits `degradation.protocol.activated` event with full context. No order cancellation logic — that's Epic 5's responsibility when it subscribes to this event.
- **Rationale:** Execution module doesn't exist until Epic 5. Event contract is defined now; subscribers come later.

## Story

As an operator,
I want the system to detect platform outages, manage degradation state, and recover automatically,
So that one platform failing doesn't compromise the system's ability to operate on healthy platforms.

## Acceptance Criteria

**Given** a platform's WebSocket has not sent data
**When** 81 seconds elapse (WebSocket timeout threshold)
**Then** the platform is marked as "degraded" (FR-DI-03)
**And** the system transitions to polling mode for that platform
**And** a high-priority `PlatformDegradedEvent` is emitted with platform ID, last data timestamp, and degradation reason

**Given** a platform is in degraded state
**When** the degradation protocol activates
**Then** the platform's health status is set to "degraded" and exposed to all downstream modules
**And** a `degradation.protocol.activated` event is emitted that downstream modules (execution, when it exists) will subscribe to for cancelling pending orders and halting new trades
**And** opportunity thresholds are widened by 1.5x on remaining healthy platforms (NFR-R2)

**Given** a degraded platform's WebSocket reconnects
**When** data flow resumes
**Then** the system validates data freshness (timestamp within 30 seconds)
**And** platform status transitions back to "healthy"
**And** a `PlatformRecoveredEvent` is emitted
**And** opportunity thresholds return to normal
**And** recovery is logged with outage duration and impact summary

**Given** a platform is degraded
**When** polling mode is active
**Then** the system continues fetching order book data via REST at 30-second intervals
**And** existing data from that platform is marked with `platform_health: "degraded"` in normalized output

## Tasks / Subtasks

- [x] Task 1: Create DegradationProtocolService (AC: Degradation protocol, threshold multiplier)
  - [x] Create `pm-arbitrage-engine/src/modules/data-ingestion/degradation-protocol.service.ts`
  - [x] Inject `EventEmitter2`, `Logger`
  - [x] Track degraded platforms in `Map<PlatformId, DegradationState>` (platformId → { degradedAt, reason, pollingCycleCount })
  - [x] `activateProtocol(platformId, reason)`: sets platform as degraded, emits `degradation.protocol.activated` event, starts threshold widening
  - [x] `deactivateProtocol(platformId)`: clears degraded state, emits `degradation.protocol.deactivated`, logs outage duration (calculated from `degradedAt`) and impact summary including polling cycle count
  - [x] `getEdgeThresholdMultiplier(platformId): number`: returns the edge threshold multiplier for the given platform. If this platform is degraded, returns 1.0 (its data is unreliable). If this platform is healthy but ANY other platform is degraded, returns the configurable widening multiplier (default 1.5) per NFR-R2. If all platforms are healthy, returns 1.0. Add clear JSDoc explaining these semantics for Epic 3's consumer.
  - [x] `isDegraded(platformId): boolean`: check if platform is currently in degradation protocol
  - [x] `getDegradationState(platformId): DegradationState | null`: get degradation details
  - [x] `incrementPollingCycle(platformId)`: increments polling cycle counter for outage impact tracking
  - [x] Use `@nestjs/config` for `DEGRADATION_THRESHOLD_MULTIPLIER` (default 1.5)

- [x] Task 2: Create DegradationProtocolActivatedEvent and DegradationProtocolDeactivatedEvent (AC: Events)
  - [x] Add `DegradationProtocolActivatedEvent` to `pm-arbitrage-engine/src/common/events/platform.events.ts`
    - Fields: `platformId`, `reason`, `lastDataTimestamp`, `activatedAt`, `healthyPlatforms: PlatformId[]`
  - [x] Add `DegradationProtocolDeactivatedEvent` with: `platformId`, `outageDurationMs`, `recoveredAt`, `impactSummary`
  - [x] Verify export in `common/events/index.ts` (via existing wildcard `export * from './platform.events'`)
  - [x] Add to event catalog

- [x] Task 3: Implement WebSocket timeout detection (81s) and polling fallback (AC: Timeout, polling mode)
  - [x] Add `WEBSOCKET_TIMEOUT_THRESHOLD = 81_000` constant to `PlatformHealthService` or as config value
  - [x] Modify `PlatformHealthService.publishHealth()` to detect 81s WebSocket silence
  - [x] When 81s timeout is detected AND protocol not already active for this platform:
    - Call `DegradationProtocolService.activateProtocol(platformId, 'websocket_timeout')`
  - [x] **CRITICAL — Polling cron conflict resolution:** Modify the EXISTING `ingestCurrentOrderBooks()` method to SKIP platforms where `DegradationProtocolService.isDegraded(platformId)` returns true. Do NOT add a separate `pollDegradedPlatforms()` cron. Instead, add a NEW method `pollDegradedPlatforms()` that is called from the EXISTING `ingestCurrentOrderBooks()` at the end, after the normal platform loop. This avoids two independent 30s crons racing to poll the same platform. The degraded polling path:
    - Only polls platforms where `isDegraded()` returns true
    - Calls `connector.getOrderBook()` via REST for each degraded platform's known contracts
    - Sets `platform_health` field on the `NormalizedOrderBook` (see Task 3a below)
    - Records latency via `healthService.recordUpdate()`
    - Calls `degradationService.incrementPollingCycle(platformId)` for outage tracking
  - [x] **NOTE:** Polling fallback uses the same placeholder contract IDs as existing polling (Kalshi placeholder ticker, Polymarket placeholder token). Real contract IDs come from Epic 3's contract pair configuration. This means the degraded polling path is structurally complete but non-functional against real APIs until Epic 3 wires in actual contract pairs.
  - [x] Ensure existing 30s health check in `publishHealth()` still runs — the 81s check is *additional*, not a replacement

- [x] Task 3a: Add `platform_health` field to NormalizedOrderBook (AC: Mark degraded data)
  - [x] Add optional `platformHealth?: 'healthy' | 'degraded' | 'offline'` field to the `NormalizedOrderBook` interface in `common/types/normalized-order-book.type.ts`
  - [x] This aligns with the PRD's normalized schema which specifies `platform_health` as an enum field
  - [x] The degraded polling path sets `platformHealth: 'degraded'` on order books fetched via REST during degradation
  - [x] Normal (non-degraded) polling does NOT set this field — it defaults to undefined, meaning healthy (consumers should treat undefined as 'healthy')
  - [x] Do NOT use a `metadata` bag — `platformHealth` is a first-class typed field

- [x] Task 4: Implement recovery detection and validation (AC: Recovery, data freshness)
  - [x] Recovery is detected in `PlatformHealthService.publishHealth()` via the EXISTING health transition logic: `publishHealth()` runs every 30s, calls `calculateHealth()`, and if timestamps have become recent (because WebSocket resumed sending data and `recordUpdate()` was called), `calculateHealth()` returns `status: 'healthy'`. The existing transition check (`health.status === 'healthy' && previousStatus === 'degraded'`) then fires.
  - [x] At this transition point, add: if `DegradationProtocolService.isDegraded(platformId)`:
    - Validate data freshness: the `lastUpdateTime` tracked by `PlatformHealthService` (updated via `recordUpdate()` when WebSocket data arrives) must be within 30 seconds of `Date.now()`
    - If fresh: call `DegradationProtocolService.deactivateProtocol(platformId)`
    - If stale: keep protocol active, log "recovery rejected: data stale" with age in ms
  - [x] `deactivateProtocol()` logs recovery with: outage duration (ms, calculated from `degradedAt`), number of polling cycles during outage, last degraded reason
  - [x] Polling fallback automatically stops for recovered platform because `ingestCurrentOrderBooks()` checks `isDegraded()` before entering the degraded polling path
  - [x] `PlatformRecoveredEvent` is already emitted by the existing `publishHealth()` transition logic — verify it fires correctly alongside protocol deactivation

- [x] Task 5: Register DegradationProtocolService in DataIngestionModule (AC: DI wiring)
  - [x] Add `DegradationProtocolService` to `DataIngestionModule` providers
  - [x] Inject into `PlatformHealthService` constructor
  - [x] Inject into `DataIngestionService` constructor (for polling fallback)
  - [x] Export from module for future consumers (Epic 3 detection service)

- [x] Task 6: Unit tests for DegradationProtocolService (AC: Protocol behavior)
  - [x] Create `degradation-protocol.service.spec.ts`
  - [x] Test `activateProtocol()` emits `degradation.protocol.activated` event with correct payload
  - [x] Test `deactivateProtocol()` emits `degradation.protocol.deactivated` event with outage duration
  - [x] Test `getEdgeThresholdMultiplier()` returns 1.0 when no platforms degraded
  - [x] Test `getEdgeThresholdMultiplier()` returns 1.5 for healthy platform when another platform is degraded
  - [x] Test `getEdgeThresholdMultiplier()` returns 1.0 for the degraded platform itself
  - [x] Test `isDegraded()` correctly tracks state
  - [x] Test multiple platforms can be degraded independently
  - [x] Test double-activate same platform is idempotent

- [x] Task 7: Unit tests for WebSocket timeout and polling fallback (AC: 81s detection, polling)
  - [x] Extend `platform-health.service.spec.ts`:
    - Test 81s timeout triggers degradation protocol activation
    - Test <81s does NOT trigger protocol (60s staleness emits degraded event but not protocol)
    - Test recovery validation rejects stale data (>30s old)
    - Test recovery validation accepts fresh data (<30s old)
  - [x] Extend `data-ingestion.service.spec.ts`:
    - Test `ingestCurrentOrderBooks()` skips degraded platforms in normal loop
    - Test `ingestCurrentOrderBooks()` calls `pollDegradedPlatforms()` for degraded platforms
    - Test degraded polling sets `platformHealth: 'degraded'` on NormalizedOrderBook
    - Test degraded polling calls `incrementPollingCycle()`
    - Test polling stops when platform recovers (isDegraded returns false)

- [x] Task 8: Integration tests (AC: End-to-end degradation → polling → recovery)
  - [x] Extend `test/data-ingestion.e2e-spec.ts`:
    - Simulate WebSocket silence for 81s → verify degradation protocol activates
    - Verify polling fallback runs while degraded
    - Simulate WebSocket recovery with fresh data → verify recovery and polling stops
    - Verify health logs capture degradation/recovery transitions
    - Verify events emitted in correct order: degraded → protocol.activated → (polling) → recovered → protocol.deactivated

## Dev Notes

### Story Context & Critical Mission

This is **Story 2.4** in Epic 2 — the graceful degradation and automatic recovery story. This story is **CRITICAL** because:

1. **Resilience Foundation** — This is the ONLY protection against a platform outage bringing down the entire system. Without this, a Polymarket WebSocket crash would leave the system blind.
2. **Prerequisite for Execution** — Epic 5's execution module will subscribe to `degradation.protocol.activated` to cancel pending orders. The event contract must be right.
3. **Prerequisite for Detection** — Epic 3's detection service will call `getThresholdMultiplier()` to widen edge thresholds. The API must be clean and correct.

### Previous Story Intelligence (Stories 2.1, 2.2, 2.3)

**What was built in Story 2.3 (directly relevant):**
- `PlatformHealthService` with `publishHealth()` cron (every 30s), `calculateHealth()` with staleness/latency checks
- `getAggregatedHealth()` and `getPlatformHealth()` query methods
- Health events: `PlatformDegradedEvent`, `PlatformRecoveredEvent`, `PlatformDisconnectedEvent`
- Both connectors injected into `DataIngestionService` with WebSocket callbacks
- Platform isolation pattern: one platform's failure doesn't affect the other

**What was built in Story 2.1 (connector layer):**
- `PolymarketConnector` with `connect()` / `disconnect()` / `getOrderBook()` / `onOrderBookUpdate()`
- `PolymarketWebSocketClient` with exponential backoff reconnection
- Error codes 1008-1099 for Polymarket

**Key Patterns Already Established:**
- Health check runs every 30s via `@Cron('*/30 * * * * *')`
- `STALENESS_THRESHOLD = 60_000` (60s) triggers `degraded` status in `calculateHealth()`
- Health transitions emit events via `EventEmitter2` in `publishHealth()`
- `toPlatformEnum()` utility for safe DB enum conversion
- `withCorrelationId()` wrapper for async context propagation
- Co-located test files (`*.spec.ts` next to source)

**Bug fix from Story 2.3:** `processWebSocketUpdate()` was using hardcoded `PlatformId.KALSHI` — fixed to use `normalized.platformId`. Don't regress this.

### Architecture Intelligence

**NFR-R2 (Graceful Degradation):**
- Per-platform degradation: cancel pending orders on degraded platform, continue healthy platforms, widen thresholds 1.5x
- Recovery: validate data freshness, restore normal thresholds

**FR-DI-03:**
- 81s WebSocket timeout → transition to polling mode
- This is DIFFERENT from the 60s staleness threshold in `calculateHealth()`:
  - 60s staleness → `PlatformDegradedEvent` (health status change)
  - 81s WebSocket silence → `degradation.protocol.activated` (operational protocol with polling fallback and threshold widening)

**Communication Pattern:**
- This story's `degradation.protocol.activated` event is a **fan-out async event** — never blocks execution
- Future subscribers (Epic 3 detection, Epic 5 execution) will use `@OnEvent('degradation.protocol.activated')`

**Error Handling:**
- No new error codes needed — degradation uses events, not exceptions
- `PlatformApiError` codes 1000-1099 already handle API failures in connectors

### File Structure — Changes Required

**New Files:**

1. `pm-arbitrage-engine/src/modules/data-ingestion/degradation-protocol.service.ts`
   - Core degradation protocol logic
   - Threshold multiplier management
   - Outage tracking and recovery logging

2. `pm-arbitrage-engine/src/modules/data-ingestion/degradation-protocol.service.spec.ts`
   - Unit tests for protocol service

**Files to Modify:**

3. `pm-arbitrage-engine/src/common/events/platform.events.ts`
   - Add `DegradationProtocolActivatedEvent` and `DegradationProtocolDeactivatedEvent`

4. `pm-arbitrage-engine/src/common/events/index.ts`
   - Export new events

5. `pm-arbitrage-engine/src/common/events/event-catalog.ts`
   - Add new event names to catalog

6. `pm-arbitrage-engine/src/common/types/normalized-order-book.type.ts`
   - Add optional `platformHealth` field

7. `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts`
   - Add 81s WebSocket timeout detection
   - Inject `DegradationProtocolService`
   - Add recovery validation (data freshness within 30s)

8. `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.ts`
   - Modify `ingestCurrentOrderBooks()` to skip degraded platforms
   - Add `pollDegradedPlatforms()` private method (called from `ingestCurrentOrderBooks()`, NOT a separate cron)
   - Inject `DegradationProtocolService`

9. `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.module.ts`
   - Register `DegradationProtocolService` as provider
   - Export for future consumers

10. `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.spec.ts`
    - 81s timeout tests, recovery validation tests

11. `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.spec.ts`
    - Polling fallback tests, skip-degraded tests

12. `pm-arbitrage-engine/test/data-ingestion.e2e-spec.ts`
    - End-to-end degradation → recovery tests

**Files NOT to Modify:**
- Connector implementations — they already have reconnection logic
- `persistSnapshot()` — already platform-agnostic
- Prisma schema — no migrations needed
- `common/interfaces/` — no new interfaces (DegradationProtocolService is concrete, only two consumers in same process)

### Critical Implementation Details

**81s vs 60s — Two Different Thresholds:**
```
60s (existing STALENESS_THRESHOLD):
  → calculateHealth() returns status: 'degraded'
  → publishHealth() emits PlatformDegradedEvent
  → Health status changes, consumers see degraded health

81s (NEW WEBSOCKET_TIMEOUT_THRESHOLD):
  → publishHealth() additionally triggers degradation protocol
  → DegradationProtocolService.activateProtocol() called
  → degradation.protocol.activated event emitted
  → Polling fallback starts, thresholds widen
```

The 60s threshold is a "soft" degradation (health reporting). The 81s threshold is a "hard" degradation (operational protocol change with polling fallback).

**Polling Fallback Architecture — NO SEPARATE CRON:**

The existing `ingestCurrentOrderBooks()` already runs on a polling schedule. Adding a second `@Cron('*/30 * * * * *')` would cause both crons to race-poll the same platform. Instead:

1. Modify `ingestCurrentOrderBooks()` to **skip** degraded platforms in its normal loop
2. At the end of `ingestCurrentOrderBooks()`, call `pollDegradedPlatforms()` (a regular method, NOT a cron)
3. The degraded polling path tags data and tracks cycles

```typescript
// Inside ingestCurrentOrderBooks():
// Normal Kalshi loop — skip if degraded
if (!this.degradationService.isDegraded(PlatformId.KALSHI)) {
  for (const ticker of kalshiTickers) { /* existing logic */ }
}

// Normal Polymarket loop — skip if degraded
if (!this.degradationService.isDegraded(PlatformId.POLYMARKET)) {
  for (const tokenId of polymarketTokens) { /* existing logic */ }
}

// Poll degraded platforms via REST fallback
await this.pollDegradedPlatforms(correlationId);

// ---
private async pollDegradedPlatforms(correlationId: string): Promise<void> {
  const connectors = [
    { connector: this.kalshiConnector, contracts: kalshiTickers },
    { connector: this.polymarketConnector, contracts: [POLYMARKET_PLACEHOLDER_TOKEN_ID] },
  ];

  for (const { connector, contracts } of connectors) {
    const platformId = connector.getPlatformId();
    if (!this.degradationService.isDegraded(platformId)) continue;

    for (const contractId of contracts) {
      try {
        const startTime = Date.now();
        const book = await connector.getOrderBook(contractId);
        book.platformHealth = 'degraded'; // typed field on NormalizedOrderBook
        await this.persistSnapshot(book, correlationId);
        this.eventEmitter.emit('orderbook.updated', new OrderBookUpdatedEvent(book));
        this.healthService.recordUpdate(platformId, Date.now() - startTime);
        this.degradationService.incrementPollingCycle(platformId);
      } catch (error) {
        // Log but don't crash — platform is already degraded
      }
    }
  }
}
```

**Recovery Validation — Triggered by Health Transition, NOT WebSocket Callbacks:**

Recovery is NOT detected by hooking into WebSocket data arrival directly. The flow is:
1. WebSocket reconnects and sends data → connector calls `processWebSocketUpdate()` → `healthService.recordUpdate()` updates `lastUpdateTime`
2. Next `publishHealth()` cron (every 30s) runs → `calculateHealth()` sees recent timestamps → returns `status: 'healthy'`
3. `publishHealth()` detects transition: `previousStatus === 'degraded'` AND `health.status === 'healthy'`
4. At this transition point, check `DegradationProtocolService.isDegraded(platform)`:
   - Validate `lastUpdateTime` is within 30s of `Date.now()`
   - If valid: `deactivateProtocol(platform)` → logs outage duration, emits protocol deactivated event
   - If stale: keep protocol active, log "recovery rejected: data stale"

**Edge Threshold Multiplier Logic:**

Method is named `getEdgeThresholdMultiplier(platformId)` (not `getThresholdMultiplier`) to be self-documenting for Epic 3's consumer. JSDoc explains: "Returns the multiplier to apply to minimum edge thresholds when evaluating opportunities on the given platform."

```typescript
/**
 * Returns the edge threshold multiplier for a given platform.
 *
 * - If `platformId` is degraded: returns 1.0 (its data is unreliable, don't use it for detection)
 * - If `platformId` is healthy but ANY other platform is degraded: returns the configured
 *   widening multiplier (default 1.5) per NFR-R2 — widen thresholds on remaining healthy platforms
 * - If ALL platforms are healthy: returns 1.0 (normal thresholds)
 *
 * Epic 3's detection service multiplies its minimum edge threshold by this value:
 *   effectiveThreshold = baseThreshold * getEdgeThresholdMultiplier(platformId)
 */
getEdgeThresholdMultiplier(platformId: PlatformId): number {
  if (this.degradedPlatforms.has(platformId)) return 1.0;
  if (this.degradedPlatforms.size > 0) return this.thresholdMultiplier; // default 1.5
  return 1.0;
}
```

### Testing Strategy

**Unit Tests (DegradationProtocolService):** ~8 tests
- Protocol activation/deactivation lifecycle
- Threshold multiplier calculation
- State tracking (isDegraded, getDegradationState)
- Event emission verification
- Idempotency (double-activate)

**Unit Tests (PlatformHealthService extensions):** ~6 tests
- 81s timeout triggers protocol
- <81s does NOT trigger protocol
- Recovery validates freshness
- Recovery rejects stale data

**Unit Tests (DataIngestionService extensions):** ~5 tests
- Polling only runs for degraded platforms
- Polling tags data with degraded metadata
- Polling stops on recovery

**E2E Tests:** ~4 tests
- Full degradation → polling → recovery lifecycle
- Event ordering verification
- Health log persistence during degradation

**Expected Total:** ~23 new tests on top of existing ~223

### Project Structure Notes

- All new code stays within `modules/data-ingestion/` — no new modules
- Events added to existing `common/events/platform.events.ts`
- Follows existing patterns: `@Cron`, `EventEmitter2`, `withCorrelationId`
- `DegradationProtocolService` is a concrete class, not abstracted via interface — only two in-process consumers (health service, ingestion service)
- Future interface extraction deferred until external consumer needs it (same decision as Story 2.3's health query methods)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4] — Acceptance criteria and BDD scenarios
- [Source: _bmad-output/planning-artifacts/architecture.md#NFR-R2] — Graceful degradation specification
- [Source: _bmad-output/planning-artifacts/architecture.md#FR-DI-03] — 81s WebSocket timeout
- [Source: _bmad-output/implementation-artifacts/2-3-cross-platform-data-aggregation-health-dashboard.md] — Previous story patterns and file list
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts] — Current health service with 60s staleness
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.ts] — Current ingestion service
- [Source: pm-arbitrage-engine/src/common/events/platform.events.ts] — Existing platform events
- [Source: pm-arbitrage-engine/src/common/types/platform.type.ts] — PlatformHealth interface

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None — clean implementation with no blocking issues.

### Completion Notes List

- Implemented `DegradationProtocolService` with full lifecycle: activate, deactivate, threshold multiplier, state tracking, polling cycle counter
- Added `DegradationProtocolActivatedEvent` and `DegradationProtocolDeactivatedEvent` to event system with catalog entries
- Added `platformHealth` typed field to `NormalizedOrderBook` interface
- Modified `PlatformHealthService` with 81s WebSocket timeout detection and 30s data freshness recovery validation
- Modified `DataIngestionService` to skip degraded platforms in normal polling and added `pollDegradedPlatforms()` REST fallback method (called from existing `ingestCurrentOrderBooks()`, NOT a separate cron)
- Registered `DegradationProtocolService` in `DataIngestionModule` (providers + exports)
- Added 13 unit tests for `DegradationProtocolService`
- Added 5 unit tests for 81s timeout and recovery validation in `PlatformHealthService`
- Added 4 unit tests for polling fallback in `DataIngestionService`
- Added 4 e2e integration tests for degradation → recovery lifecycle
- Total: 249 tests passing (26 new), 0 regressions
- Lint passes clean

**Code Review Fixes (2026-02-15):**
- Fixed H1: Extracted hardcoded platform list to `allPlatforms` property derived from `Object.values(PlatformId)` for extensibility
- Fixed M1: Updated `activateProtocol()` to accept optional `lastDataTimestamp` parameter; `PlatformHealthService` now passes actual timestamp from `lastUpdateTime` map
- Fixed M2: Clarified Task 2 wording about `common/events/index.ts` export (via existing wildcard, no file change needed)
- Updated test expectations for new `activateProtocol()` signature
- All tests remain passing (249/249)

### File List

**New Files:**
- `pm-arbitrage-engine/src/modules/data-ingestion/degradation-protocol.service.ts`
- `pm-arbitrage-engine/src/modules/data-ingestion/degradation-protocol.service.spec.ts`

**Modified Files:**
- `pm-arbitrage-engine/src/common/events/platform.events.ts` — Added DegradationProtocolActivatedEvent, DegradationProtocolDeactivatedEvent
- `pm-arbitrage-engine/src/common/events/event-catalog.ts` — Added DEGRADATION_PROTOCOL_ACTIVATED, DEGRADATION_PROTOCOL_DEACTIVATED
- `pm-arbitrage-engine/src/common/types/normalized-order-book.type.ts` — Added platformHealth field
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts` — 81s timeout detection, recovery validation, DegradationProtocolService injection
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.spec.ts` — Added 5 tests for timeout/recovery
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.ts` — Skip degraded platforms, pollDegradedPlatforms(), DegradationProtocolService injection
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.spec.ts` — Added 4 tests for polling fallback
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.module.ts` — Registered DegradationProtocolService
- `pm-arbitrage-engine/test/data-ingestion.e2e-spec.ts` — Added 4 e2e tests for degradation lifecycle
