# Story 2.3: Cross-Platform Data Aggregation & Health Dashboard

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Epic Deviations

**1. No REST "health dashboard" endpoint in this story**
- **Epic AC states:** "a unified health view is available showing per-platform status"
- **This story implements:** Unified health view via in-memory aggregation + events + existing health logging infrastructure
- **Rationale:** No dashboard exists yet (Epic 7). "Available" means queryable by downstream modules via DI injection, persisted to DB, and emitted as events. REST endpoints for the operator dashboard are deferred to Epic 7 Story 7.1.

**2. "Each contract pair's data includes both platforms' pricing" simplified for MVP**
- **Epic AC states:** "each contract pair's data includes both platforms' pricing for the same event"
- **This story implements:** Both connectors' order books are ingested and available to downstream modules. Contract pair matching (knowing which Kalshi contract maps to which Polymarket contract) is Epic 3 Story 3.1's responsibility.
- **Rationale:** This story ensures both data streams flow; Epic 3 correlates them by contract pair.

## Story

As an operator,
I want to see aggregated order books from both platforms with unified health status,
So that I can verify the complete data foundation before building detection logic.

## Acceptance Criteria

**Given** both Kalshi and Polymarket connectors are running
**When** the data ingestion service orchestrates a polling cycle
**Then** normalized order books from both platforms are available to downstream modules
**And** each platform's data is ingested independently (contract pair correlation is Epic 3)
**And** a downstream module subscribing to `orderbook.updated` events receives `NormalizedOrderBook` from both platforms, distinguishable by `platformId`

**Given** both platforms are publishing health status
**When** the health service aggregates
**Then** a unified health view is available showing per-platform status (healthy/degraded/offline)
**And** platform health events are emitted via EventEmitter2 (`platform.health.degraded`, `platform.health.recovered`)
**And** health status is persisted to `platform_health_logs` table with both platforms

**Given** one platform is degraded and the other is healthy
**When** health is queried
**Then** the system reports partial health (one green, one yellow/red)
**And** downstream modules can query per-platform health independently

## Tasks / Subtasks

- [x] Task 1: Inject PolymarketConnector into DataIngestionService (AC: Both platforms ingested)
  - [x] Add `PolymarketConnector` to constructor injection in `DataIngestionService`
  - [x] Import `PolymarketConnector` from `connectors/polymarket/polymarket.connector`
  - [x] Verify `DataIngestionModule` imports `ConnectorModule` which exports `PolymarketConnector` (already configured)

- [x] Task 2: Register Polymarket WebSocket callback in onModuleInit (AC: Real-time updates)
  - [x] Add `this.polymarketConnector.onOrderBookUpdate()` callback registration
  - [x] Follow same pattern as Kalshi: async processing, error catching, logging
  - [x] Pass `PlatformId.POLYMARKET` to `healthService.recordUpdate()` for latency tracking
  - [x] Log initialization message for Polymarket WebSocket registration

- [x] Task 3: Extend ingestCurrentOrderBooks for Polymarket polling (AC: Polling path)
  - [x] Add Polymarket market tokens to polling loop (placeholder array, same pattern as Kalshi)
  - [x] **NOTE:** Placeholder token IDs will fail against the real API — polling path verification MUST use mocked connectors only. Real API verification happens when Epic 3 supplies actual contract pairs.
  - [x] Call `this.polymarketConnector.getOrderBook(tokenId)` for each Polymarket market
  - [x] Persist snapshots using existing `persistSnapshot()` (already platform-agnostic)
  - [x] Emit `orderbook.updated` event with Polymarket normalized data
  - [x] Record latency with `healthService.recordUpdate(PlatformId.POLYMARKET, latency)`
  - [x] Handle errors per-platform (Kalshi failure shouldn't skip Polymarket and vice versa)

- [x] Task 4: Extend PlatformHealthService for Polymarket (AC: Unified health view)
  - [x] Add `PlatformId.POLYMARKET` to the `platforms` array in `publishHealth()`
  - [x] Health calculation already works for any PlatformId (data-driven via Maps)
  - [x] Verify health status persistence includes Polymarket entries in `platform_health_logs`
  - [x] Verify health events emit correctly for Polymarket (degraded, recovered, disconnected)

- [x] Task 5: Add cross-platform health query methods (AC: Downstream modules query independently)
  - [x] Add `getAggregatedHealth(): Map<PlatformId, PlatformHealth>` to `PlatformHealthService`
  - [x] Returns current health for all registered platforms
  - [x] Add `getPlatformHealth(platformId: PlatformId): PlatformHealth` for per-platform queries
  - [x] These methods enable Epic 3's detection service to skip degraded platforms
  - [x] **Note on interfaces:** These methods are added directly to `PlatformHealthService` (concrete class). No `common/interfaces/` abstraction needed yet — only two consumers exist (Epic 3 detection, Epic 2.4 degradation), both in the same process. If a `IHealthMonitor` interface becomes necessary for decoupling, it should be added when the first external consumer is implemented.

- [x] Task 6: Unit tests for cross-platform DataIngestionService (AC: Comprehensive coverage)
  - [x] Extend `data-ingestion.service.spec.ts` with Polymarket test cases:
    - Both connectors registered in `onModuleInit` (two WebSocket callbacks)
    - `ingestCurrentOrderBooks()` calls both Kalshi and Polymarket connectors
    - Kalshi failure doesn't prevent Polymarket ingestion (and vice versa)
    - Polymarket WebSocket updates processed and persisted correctly
    - `healthService.recordUpdate()` called with `PlatformId.POLYMARKET`
    - Events emitted for both platforms
    - `orderbook.updated` events from both platforms carry distinct `platformId` values, enabling downstream filtering
  - [x] Mock `PolymarketConnector` alongside existing `KalshiConnector` mock

- [x] Task 7: Unit tests for PlatformHealthService cross-platform (AC: Health coverage)
  - [x] Extend `platform-health.service.spec.ts` with Polymarket test cases:
    - `publishHealth()` iterates both KALSHI and POLYMARKET
    - Health calculated independently for each platform
    - Degradation event emitted for Polymarket when stale
    - Recovery event emitted for Polymarket when recovered
    - `getAggregatedHealth()` returns both platforms
    - `getPlatformHealth()` returns correct per-platform health
    - Mixed health states: one healthy + one degraded
    - WebSocket-specific scenario: Polymarket WS disconnects while Kalshi continues — health shows Polymarket degraded/disconnected, Kalshi healthy
  - [x] Verify health persistence writes for both platforms

- [x] Task 8: Integration verification (AC: End-to-end data flow)
  - [x] Extend `test/data-ingestion.e2e-spec.ts` with cross-platform test cases:
    - Polling cycle persists snapshots for both platforms (query `order_book_snapshots` with `platform = 'KALSHI'` and `platform = 'POLYMARKET'`)
    - Health cron persists health logs for both platforms (query `platform_health_logs` with both platform values)
    - `orderbook.updated` event carries correct `platformId` for each platform
  - [x] Verify both connectors' `onModuleInit` registration via service initialization test
  - [x] All e2e tests use mocked connectors (placeholder token IDs don't hit real APIs)

## Dev Notes

### Story Context & Critical Mission

This is **Story 2.3** in Epic 2 — the cross-platform data aggregation story. This story is **CRITICAL** because:

1. **Cross-Platform Foundation Complete** — After this story, both platforms' data flows through a single ingestion pipeline. This is the prerequisite for arbitrage detection (Epic 3).
2. **Unified Health Monitoring** — Operators can see at a glance if either platform is degraded. This feeds into Epic 3's detection logic (skip degraded platforms) and Epic 2.4's graceful degradation.
3. **Relatively Simple Story** — Most infrastructure exists. This is primarily wiring PolymarketConnector into DataIngestionService and extending PlatformHealthService.

### Previous Story Intelligence (Stories 2.1 & 2.2)

**What was built in Story 2.1:**
- `PolymarketConnector` implementing `IPlatformConnector` with full connect/disconnect/getOrderBook/getHealth/getFeeSchedule
- `PolymarketWebSocketClient` with reconnection and subscription management
- Authentication via @polymarket/clob-client (L1 wallet -> L2 API key)
- Error codes 1008-1099 for Polymarket
- Rate limiter with conservative defaults (8 read/s, 4 write/s)

**What was built in Story 2.2:**
- `OrderBookNormalizerService` extended with `normalizePolymarket()` method
- PolymarketConnector now returns `NormalizedOrderBook` via both REST and WebSocket paths
- Fee constants: `POLYMARKET_TAKER_FEE = 0.02`, `POLYMARKET_MAKER_FEE = 0.00`
- Platform enum migration (DB uses uppercase KALSHI/POLYMARKET)
- NaN validation, null safety, proper Prisma types
- 198 tests passing across 21 test files

**Key Patterns Already Established:**
- Connector produces `NormalizedOrderBook` — DataIngestionService never sees raw platform data
- `persistSnapshot()` is platform-agnostic (uses `book.platformId.toUpperCase()` for DB enum)
- `PlatformHealthService` uses `Map<PlatformId, ...>` — already data-driven, just needs POLYMARKET added to the platforms array
- WebSocket callback registration pattern in `onModuleInit`

### Architecture Intelligence

**Current DataIngestionService State:**
- Only injects `KalshiConnector` — needs `PolymarketConnector` added
- `onModuleInit()` only registers Kalshi WebSocket callback
- `ingestCurrentOrderBooks()` only polls Kalshi with hardcoded placeholder ticker
- `persistSnapshot()` already platform-agnostic (no changes needed)
- `processWebSocketUpdate()` already platform-agnostic (no changes needed)

**Current PlatformHealthService State:**
- `publishHealth()` hardcodes `const platforms = [PlatformId.KALSHI]` with comment "Expand in Epic 2"
- Health calculation via `calculateHealth()` is fully data-driven (Map-based)
- No public method to query aggregated health — only `recordUpdate()` and `publishHealth()` (cron)
- Persistence and event emission already work for any PlatformId

**Module Dependencies (already configured):**
- `DataIngestionModule` imports `ConnectorModule` (via forwardRef)
- `ConnectorModule` exports both `KalshiConnector` and `PolymarketConnector`
- No new module imports needed — just inject PolymarketConnector into DataIngestionService

### File Structure — Changes Required

**Files to Modify:**

1. `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.ts`
   - Add `PolymarketConnector` constructor injection
   - Add Polymarket WebSocket registration in `onModuleInit()`
   - Extend `ingestCurrentOrderBooks()` to poll both platforms

2. `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts`
   - Add `PlatformId.POLYMARKET` to platforms array in `publishHealth()`
   - Add `getAggregatedHealth()` and `getPlatformHealth()` methods

3. `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.spec.ts`
   - Add Polymarket mock and cross-platform test cases

4. `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.spec.ts`
   - Add Polymarket health test cases and aggregated health tests

**Files NOT to Modify:**
- `connector.module.ts` — Already exports PolymarketConnector
- `data-ingestion.module.ts` — Already imports ConnectorModule
- `persistSnapshot()` — Already platform-agnostic
- `processWebSocketUpdate()` — Already platform-agnostic
- Prisma schema — No migrations needed

### Critical Implementation Details

**Polling Architecture:**
The `ingestCurrentOrderBooks()` method currently uses a hardcoded Kalshi ticker array. For Polymarket, add a separate placeholder token ID array. In production (Epic 3), these will come from the contract pair configuration. For now, use placeholders.

```typescript
// Current (Kalshi only):
const marketTickers = ['KXTABLETENNIS-26FEB121755MLADPY-MLA'];

// After (both platforms):
const kalshiTickers = ['KXTABLETENNIS-26FEB121755MLADPY-MLA'];
const polymarketTokens = ['placeholder-polymarket-token-id'];
```

**Error Isolation Pattern:**
Each platform's ingestion MUST be independent. A Kalshi failure should NOT prevent Polymarket ingestion:

```typescript
// Ingest Kalshi (isolated try/catch)
for (const ticker of kalshiTickers) {
  try { /* kalshi ingestion */ } catch { /* log, continue */ }
}

// Ingest Polymarket (isolated try/catch)
for (const tokenId of polymarketTokens) {
  try { /* polymarket ingestion */ } catch { /* log, continue */ }
}
```

**Health Service Extension:**
The only change needed in `PlatformHealthService.publishHealth()` is updating the platforms array:

```typescript
// Current:
const platforms = [PlatformId.KALSHI]; // Expand in Epic 2

// After:
const platforms = [PlatformId.KALSHI, PlatformId.POLYMARKET];
```

All other health logic (calculateHealth, staleness detection, event emission, DB persistence) already works for any PlatformId.

**New Health Query Methods:**

```typescript
getAggregatedHealth(): Map<PlatformId, PlatformHealth> {
  const healthMap = new Map<PlatformId, PlatformHealth>();
  for (const platform of [PlatformId.KALSHI, PlatformId.POLYMARKET]) {
    healthMap.set(platform, this.calculateHealth(platform));
  }
  return healthMap;
}

getPlatformHealth(platformId: PlatformId): PlatformHealth {
  return this.calculateHealth(platformId);
}
```

### Testing Strategy

**Unit Tests (DataIngestionService):**
- Verify both connectors have WebSocket callbacks registered
- Verify polling ingests from both platforms
- Verify platform isolation (one failing doesn't affect other)
- Verify events emitted for both platforms
- Verify health tracking for both platforms

**Unit Tests (PlatformHealthService):**
- Verify health published for both platforms
- Verify mixed health states (Kalshi healthy, Polymarket degraded)
- Verify `getAggregatedHealth()` returns both
- Verify `getPlatformHealth()` returns correct platform

**Expected Test Count:** ~10-15 new tests on top of existing 198

### Project Structure Notes

- Follows existing module patterns exactly
- No new files created — only extending existing services
- No new dependencies needed
- No Prisma migrations needed
- Platform-agnostic infrastructure already handles multi-platform

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3] — Acceptance criteria and BDD scenarios
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns] — Event-driven architecture
- [Source: _bmad-output/implementation-artifacts/2-1-polymarket-connector-wallet-authentication.md] — Polymarket connector implementation
- [Source: _bmad-output/implementation-artifacts/2-2-polymarket-order-book-normalization.md] — Normalization patterns
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.ts] — Current ingestion service (Kalshi-only)
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts] — Current health service (Kalshi-only)
- [Source: pm-arbitrage-engine/src/connectors/connector.module.ts] — Both connectors exported
- [Source: pm-arbitrage-engine/src/common/events/platform.events.ts] — Health event classes
- [Source: pm-arbitrage-engine/src/common/types/platform.type.ts] — PlatformHealth interface

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

None - all tests passed on first run after implementation.

### Completion Notes List

✅ **Task 1 Complete:** Injected PolymarketConnector into DataIngestionService constructor. Both KalshiConnector and PolymarketConnector now available via DI.

✅ **Task 2 Complete:** Registered Polymarket WebSocket callback in onModuleInit(). Both platforms now have real-time update handlers with async processing and error handling.

✅ **Task 3 Complete:** Extended ingestCurrentOrderBooks() with Polymarket polling. Platform isolation implemented - Kalshi failure doesn't affect Polymarket and vice versa. Placeholder token IDs used (real IDs will come from Epic 3).

✅ **Task 4 Complete:** Extended PlatformHealthService.publishHealth() to iterate both KALSHI and POLYMARKET. Health calculation, persistence, and event emission now work for both platforms.

✅ **Task 5 Complete:** Added getAggregatedHealth() and getPlatformHealth() query methods to PlatformHealthService. Downstream modules (Epic 3 detection) can now query platform health independently.

✅ **Task 6 Complete:** Added comprehensive unit tests for cross-platform DataIngestionService. Tests verify both connectors registered, polling calls both platforms, platform isolation, WebSocket updates for both platforms, health tracking, events emitted with distinct platformId values. 20 tests total.

✅ **Task 7 Complete:** Extended PlatformHealthService unit tests for cross-platform scenarios. Tests verify health published for both platforms, degradation/recovery events, mixed health states, aggregated health queries. 25 tests total.

✅ **Task 8 Complete:** Extended e2e tests with cross-platform verification. Tests verify both connectors initialized, health logs persisted for both platforms, aggregated and individual health queries work correctly. 8 e2e tests total.

**Bug Fix:** Fixed processWebSocketUpdate() to use normalized.platformId instead of hardcoded PlatformId.KALSHI for health tracking.

**Test Coverage:** 223 tests passing across 23 test files (5 new tests for error handling + correlation fixes).

**Implementation Decision:** No interface abstraction created for health query methods (getAggregatedHealth, getPlatformHealth) as per Dev Notes guidance - only two consumers exist in same process, abstraction deferred until external consumer needs it.

**Code Review Fixes Applied:**
- Added correlationId to all log entries (architecture compliance)
- Implemented SystemHealthError (codes 4000-4999) for system health failures
- Created toPlatformEnum() utility to eliminate fragile .toUpperCase() casts
- Replaced magic number with POLYMARKET_PLACEHOLDER_TOKEN_ID constant
- Added JSDoc to onModuleInit() lifecycle method
- Wrapped publishHealth() in withCorrelationId() for async context propagation

### File List

**Modified:**
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.ts` - Added PolymarketConnector injection, registered WebSocket callback, extended polling for both platforms, added correlationId to logs, uses SystemHealthError for critical failures
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts` - Added POLYMARKET to platforms array, added getAggregatedHealth() and getPlatformHealth() methods, uses toPlatformEnum utility, wrapped in correlation context
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.spec.ts` - Added Polymarket mock, 7 new cross-platform tests, updated critical failure test for SystemHealthError (total 20 tests)
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.spec.ts` - Added 4 new cross-platform health tests (total 25 tests)
- `pm-arbitrage-engine/test/data-ingestion.e2e-spec.ts` - Added PolymarketConnector, added cross-platform e2e tests (total 8 tests)

**New Files (Code Review Fixes):**
- `pm-arbitrage-engine/src/common/errors/system-health-error.ts` - SystemHealthError class (codes 4000-4999)
- `pm-arbitrage-engine/src/common/errors/system-health-error.spec.ts` - SystemHealthError unit tests (2 tests)
- `pm-arbitrage-engine/src/common/utils/platform.ts` - toPlatformEnum() utility for safe enum conversion
- `pm-arbitrage-engine/src/common/utils/platform.spec.ts` - Platform utility tests (3 tests)
- `pm-arbitrage-engine/src/common/errors/index.ts` - Updated exports
- `pm-arbitrage-engine/src/common/utils/index.ts` - Updated exports
