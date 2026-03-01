# Story 6.5.4: WebSocket Stability & Structured Log Payloads

Status: done

## Story

As an operator,
I want the Polymarket WebSocket connection to stay alive during idle periods, health status to not flap on transient reconnects, and all event log entries to show real structured values instead of `[object]`,
so that paper trading validation runs against a stable, observable system where health reflects real connectivity problems and logs are usable for diagnosis.

## Acceptance Criteria

1. **Given** the Polymarket WebSocket client is connected
   **When** no market data arrives for an extended idle period
   **Then** the client sends periodic ping frames (every 30s) to keep the connection alive
   **And** the server does not close the connection with code 1006 due to inactivity

2. **Given** the WebSocket connection drops and reconnects within one health check cycle (30s)
   **When** the platform health service evaluates health on the next tick
   **Then** the platform is NOT marked as degraded (transient reconnect is tolerated)
   **And** the degradation protocol is NOT activated

3. **Given** the WebSocket connection has been down for 2+ consecutive health check ticks (~60s of confirmed timeout)
   **When** the platform health service evaluates health
   **Then** the degradation protocol IS activated with reason `websocket_timeout`
   **And** degradation is only cleared after 2+ consecutive healthy observations

4. **Given** any domain event is emitted with Date, array, or nested object fields
   **When** `EventConsumerService.summarizeEvent()` processes the event for logging
   **Then** Date values appear as ISO 8601 strings (e.g. `2026-03-01T12:00:00.000Z`)
   **And** arrays appear as actual arrays (e.g. `["polymarket"]`)
   **And** nested plain objects appear as serialized objects (e.g. `{"pollingCycleCount": 3, "reason": "websocket_timeout"}`)
   **And** no field in the log output contains the literal string `[object]`

## Tasks / Subtasks

- [x] Task 1: Add WebSocket keepalive ping to PolymarketWebSocketClient (AC: #1)
  - [x] 1.1 Add `private pingInterval: NodeJS.Timeout | null = null` and `private pongTimeout: NodeJS.Timeout | null = null` fields
  - [x] 1.2 In `connect()`, after WebSocket `open` event: start a 30s `setInterval` that sends `ws.ping()`. **Before each ping, clear any existing `pongTimeout`** to prevent overlapping timeouts. After ping, set a 10s `setTimeout` for pong timeout.
  - [x] 1.3 Register `ws.on('pong')` handler that clears `pongTimeout` and sets it to `null`
  - [x] 1.4 On pong timeout: log warning and call `this.ws.terminate()` (hard close, no close frame) to trigger reconnection via existing backoff
  - [x] 1.5 **Add null guard in ping callback**: `if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;` — prevents calling `ping()` on a dead/null socket
  - [x] 1.6 Add `private clearPingTimers()` helper that clears both `pingInterval` and `pongTimeout`. Call it from: `disconnect()`, `close` handler, **and `error` handler**
  - [x] 1.7 Write tests: ping interval starts on connect, clears on disconnect, pong timeout forces reconnect, **overlapping timeout cleared before new ping**, **null ws guard prevents crash**, **error handler cleans up timers**, **reconnect restarts ping interval**
- [x] Task 2: Add WebSocket keepalive ping to KalshiWebSocketClient (AC: #1)
  - [x] 2.1 Same pattern as Task 1 — identical `clearPingTimers()`, null guard, overlapping timeout prevention, error handler cleanup
  - [x] 2.2 Write tests: mirror Polymarket ping tests for Kalshi client
- [x] Task 3: Add consecutive-check hysteresis to PlatformHealthService (AC: #2, #3)
  - [x] 3.1 Add `consecutiveUnhealthyTicks: Map<PlatformId, number>` and `consecutiveHealthyTicks: Map<PlatformId, number>` to the service. Initialize all known platforms to 0 in constructor.
  - [x] 3.2 In `checkPlatformHealth()`: increment `consecutiveUnhealthyTicks` when a platform is unhealthy, reset to 0 when healthy (and vice versa for `consecutiveHealthyTicks`)
  - [x] 3.3 Only transition healthy → degraded when `consecutiveUnhealthyTicks >= 2` (i.e., 2 consecutive 30s ticks = 60-90s confirmed depending on tick alignment)
  - [x] 3.4 Only transition degraded → healthy when `consecutiveHealthyTicks >= 2` (i.e., 2 consecutive healthy observations after recovery)
  - [x] 3.5 **REMOVE the standalone `WEBSOCKET_TIMEOUT_THRESHOLD = 81_000` direct-activation check** (lines ~126-141 that directly call `activateProtocol()`). The per-tick `calculateHealth()` still uses `STALENESS_THRESHOLD = 60_000` to determine if a tick is "unhealthy". The consecutive-tick mechanism replaces the old 81s single-shot trigger entirely. This prevents the 81s check from bypassing hysteresis.
  - [x] 3.6 Write tests: single unhealthy tick does NOT degrade, 2 consecutive ticks DO degrade, single healthy tick does NOT recover, 2 consecutive healthy ticks DO recover, counter resets on opposite observation, **counters initialize to 0**, **single-tick staleness at 65s does not trigger degradation**
- [x] Task 4: Fix `summarizeEvent()` in EventConsumerService (AC: #4)
  - [x] 4.1 Replace the `typeof value === 'object' && value !== null ? '[object]' : value` logic (line ~313) with a recursive `serializeValue()` method with proper type handling:
    - `null` / `undefined` → passthrough
    - `Date` instance → `.toISOString()`
    - `Decimal` instance (`instanceof Decimal` from `decimal.js`) → `.toString()`
    - `Array` → `.map(v => this.serializeValue(v, seen))` (recursive)
    - Plain objects → recursively serialize each property
    - Primitives → passthrough
  - [x] 4.2 **Add circular reference protection**: accept a `WeakSet` parameter (default `new WeakSet()`), check `seen.has(value)` before recursing, return `'[Circular]'` if detected
  - [x] 4.3 **Add max depth guard**: accept a `depth` parameter (default 0), return `'[MaxDepth]'` if `depth > 10` — prevents stack overflow on deeply nested objects
  - [x] 4.4 **Wrap `summarizeEvent()` in try/catch**: on serialization failure, log warning and return `{ error: 'serialization_failed', eventType: event.constructor.name }` — prevents event pipeline crash
  - [x] 4.5 Write tests: Date → ISO string, array of Dates → array of ISO strings, Decimal → string, nested object passthrough, null → null, primitive passthrough, no `[object]` in any output, **circular reference → `[Circular]`**, **deep nesting (>10 levels) → `[MaxDepth]`**, **serialization error → fallback object**

## Dev Notes

### Architecture Compliance

- **Module boundaries**: All changes are within allowed import paths. No new cross-module imports introduced.
  - `connectors/polymarket/` and `connectors/kalshi/` — internal WebSocket client changes only
  - `modules/data-ingestion/platform-health.service.ts` — internal service logic change
  - `modules/monitoring/event-consumer.service.ts` — internal serialization fix
- **Event system**: No new events. Existing events emit the same payloads — only the logging serialization changes.
- **Error handling**: No new error types needed. Existing `PlatformApiError` hierarchy covers WebSocket failures.

### File Structure — Exact Files to Modify

| File | Change |
|------|--------|
| `src/connectors/polymarket/polymarket-websocket.client.ts` | Add ping interval (30s), pong timeout (10s), cleanup |
| `src/connectors/polymarket/polymarket-websocket.client.spec.ts` | Tests for ping/pong keepalive |
| `src/connectors/kalshi/kalshi-websocket.client.ts` | Add ping interval (30s), pong timeout (10s), cleanup |
| `src/connectors/kalshi/kalshi-websocket.client.spec.ts` | Tests for ping/pong keepalive |
| `src/modules/data-ingestion/platform-health.service.ts` | Add consecutive tick counters, hysteresis logic |
| `src/modules/data-ingestion/platform-health.service.spec.ts` | Tests for consecutive-check behavior |
| `src/modules/monitoring/event-consumer.service.ts` | Fix `summarizeEvent()` to handle Date/array/object/Decimal |
| `src/modules/monitoring/event-consumer.service.spec.ts` | Tests for serialization correctness |

**No new files.** No schema changes. No new dependencies. No env var changes. No migration needed.

### Technical Implementation Details

#### Task 1 & 2: WebSocket Keepalive

The `ws` library (used by both clients) supports native ping/pong:
```typescript
// ws.ping() sends a WebSocket ping frame
// 'pong' event fires when server responds
this.ws.ping();
this.ws.on('pong', () => { /* reset pong timeout */ });
```

**Implementation pattern:**
```typescript
private pingInterval: NodeJS.Timeout | null = null;
private pongTimeout: NodeJS.Timeout | null = null;

private clearPingTimers(): void {
  if (this.pingInterval) { clearInterval(this.pingInterval); this.pingInterval = null; }
  if (this.pongTimeout) { clearTimeout(this.pongTimeout); this.pongTimeout = null; }
}

// In connect(), after 'open' event:
this.pingInterval = setInterval(() => {
  if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return; // null guard
  if (this.pongTimeout) { clearTimeout(this.pongTimeout); this.pongTimeout = null; } // clear stale timeout
  this.ws.ping();
  this.pongTimeout = setTimeout(() => {
    this.logger.warn('Pong timeout — forcing reconnect');
    this.ws.terminate(); // hard close, triggers 'close' → reconnect
  }, 10_000);
}, 30_000);

this.ws.on('pong', () => {
  if (this.pongTimeout) {
    clearTimeout(this.pongTimeout);
    this.pongTimeout = null;
  }
});

// In disconnect(), 'close' handler, AND 'error' handler:
this.clearPingTimers();
```

**Existing reconnect mechanism** (`RETRY_STRATEGIES.WEBSOCKET_RECONNECT`: 1s initial, 60s max, 2x multiplier, `maxRetries: Infinity`) handles the reconnect after `terminate()`. No changes to reconnect logic needed.

#### Task 3: Consecutive-Check Hysteresis

**Current behavior** (single-observation trigger):
- `platform-health.service.ts` line 126-141: checks `wsAge > 81_000` once → activates degradation
- Line 83-96: healthy observation → immediately deactivates degradation

**New behavior** (consecutive-check):
- Track `consecutiveUnhealthyTicks` per platform — increment when unhealthy, reset on healthy
- Track `consecutiveHealthyTicks` per platform — increment when healthy, reset on unhealthy
- Degrade only when `consecutiveUnhealthyTicks >= 2`
- Recover only when `consecutiveHealthyTicks >= 2`
- **REMOVE the standalone 81s `WEBSOCKET_TIMEOUT_THRESHOLD` direct-activation check** (lines ~126-141). This check directly calls `activateProtocol()` on a single observation, which **bypasses the consecutive-tick hysteresis entirely**. The per-tick `calculateHealth()` still uses `STALENESS_THRESHOLD = 60_000` to determine if a tick is "unhealthy" — that threshold is sufficient. Two consecutive unhealthy ticks (each >60s stale) gives ~60-90s effective degradation trigger depending on tick alignment.
- Initialize all counter Maps in the constructor with all known `PlatformId` values set to 0

**Constants to add:**
```typescript
private static readonly CONSECUTIVE_UNHEALTHY_TICKS_THRESHOLD = 2;
private static readonly CONSECUTIVE_HEALTHY_TICKS_THRESHOLD = 2;
```

#### Task 4: Fix `summarizeEvent()`

**Current code** (`event-consumer.service.ts` line ~306-316):
```typescript
private summarizeEvent(event: BaseEvent): Record<string, unknown> | string {
  if (!event || typeof event !== 'object') return 'unknown';
  const summary: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(event)) {
    if (key === 'correlationId') continue;
    summary[key] =
      typeof value === 'object' && value !== null ? '[object]' : value;
  }
  return summary;
}
```

**Fixed implementation:**
```typescript
private static readonly MAX_SERIALIZE_DEPTH = 10;

private summarizeEvent(event: BaseEvent): Record<string, unknown> | string {
  try {
    if (!event || typeof event !== 'object') return 'unknown';
    const summary: Record<string, unknown> = {};
    const seen = new WeakSet();
    for (const [key, value] of Object.entries(event)) {
      if (key === 'correlationId') continue;
      summary[key] = this.serializeValue(value, seen, 0);
    }
    return summary;
  } catch (error) {
    this.logger.warn({ error, eventType: event?.constructor?.name }, 'Event serialization failed');
    return { error: 'serialization_failed', eventType: event?.constructor?.name ?? 'unknown' };
  }
}

private serializeValue(value: unknown, seen: WeakSet<object>, depth: number): unknown {
  if (value === null || value === undefined) return value;
  if (typeof value !== 'object') return value; // primitives passthrough
  if (depth > EventConsumerService.MAX_SERIALIZE_DEPTH) return '[MaxDepth]';
  if (seen.has(value)) return '[Circular]';
  seen.add(value);
  if (value instanceof Date) return value.toISOString();
  if ('toFixed' in value) return String(value); // Decimal duck-typing
  if (Array.isArray(value)) return value.map((v) => this.serializeValue(v, seen, depth + 1));
  const serialized: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value)) {
    serialized[k] = this.serializeValue(v, seen, depth + 1);
  }
  return serialized;
}
```

**Key design decisions:**
- **Circular reference protection** via `WeakSet` — prevents stack overflow if any event accidentally has cycles
- **Max depth guard** (10 levels) — prevents runaway recursion on deeply nested objects
- **Error boundary** in `summarizeEvent()` — serialization failure returns a fallback object instead of crashing the event pipeline
- **Recursive**: `DegradationProtocolDeactivatedEvent.impactSummary` has nested fields. `SingleLegExposureEvent.currentPrices` has 2-level nesting. Recursive handles all depths without special-casing.
- **Decimal detection** uses `instanceof Decimal` (imported from `decimal.js`). This is more type-safe than duck-typing via `toFixed` — the monitoring module already depends on `decimal.js` transitively. Note: `Prisma.Decimal` instances will serialize as plain objects; if Prisma Decimals appear in events, convert via `new Decimal(val.toString())` at the emission site.

### Previous Story Intelligence (Story 6.5.3)

- **Documentation-only story** — no code changes, no test changes
- Test count at 6.5.3: 1,101 tests (70 test files), 0 lint errors
- Story 6.5.2a introduced batch order book fetching for Polymarket and transition-only health log persistence
- Flaky test note: `logging.e2e-spec.ts:86` is a pre-existing timing-dependent flaky test — ignore if it appears

### Git Intelligence

Recent commits (engine repo):
```
c470f15 feat: implement batch fetching of order books for Polymarket
48caebd feat: update Polymarket WebSocket handling to support nested price_change messages
05e1744 feat: introduce SystemErrorFilter + EventConsumerService
```

**Relevant to this story:**
- `48caebd`: Added `handlePriceChange()` logic with staleness detection (the code we are modifying for keepalive)
- `05e1744`: Introduced `EventConsumerService` with the `summarizeEvent()` method we are fixing
- `c470f15`: Batch order book fetch — be careful not to break the `PolymarketWebSocketClient` contract used by `DataIngestionService`

### Key Domain Events Affected by `summarizeEvent()` Fix

Events with object/Date/array fields that currently log as `[object]`:

| Event | Field | Type | Current Log | Fixed Log |
|-------|-------|------|------------|-----------|
| `DegradationProtocolActivatedEvent` | `healthyPlatforms` | `PlatformId[]` | `[object]` | `["kalshi"]` |
| `DegradationProtocolActivatedEvent` | `lastDataTimestamp` | `Date \| null` | `[object]` | `"2026-03-01T..."` |
| `DegradationProtocolActivatedEvent` | `activatedAt` | `Date` | `[object]` | `"2026-03-01T..."` |
| `DegradationProtocolDeactivatedEvent` | `recoveredAt` | `Date` | `[object]` | `"2026-03-01T..."` |
| `DegradationProtocolDeactivatedEvent` | `impactSummary` | `{pollingCycleCount, reason}` | `[object]` | `{"pollingCycleCount":3,"reason":"websocket_timeout"}` |
| `SingleLegExposureEvent` | `filledLeg` | object | `[object]` | Full object |
| `SingleLegExposureEvent` | `failedLeg` | object | `[object]` | Full object |
| `SingleLegExposureEvent` | `currentPrices` | nested object | `[object]` | Full nested object |
| `SingleLegExposureEvent` | `pnlScenarios` | nested object | `[object]` | Full nested object |
| `SingleLegExposureEvent` | `recommendedActions` | `string[]` | `[object]` | `["close_filled_leg"]` |
| `ExecutionFailedEvent` | `context` | `Record<string, unknown>` | `[object]` | Full object |
| All events (BaseEvent) | `timestamp` | `Date` | `[object]` | ISO string |

### Testing Requirements

**All tests co-located (same directory as source).** Vitest + unplugin-swc.

- **WebSocket ping tests**: Mock `ws` library. Use `vi.useFakeTimers()`. Test cases:
  - `ping()` called every 30s after connect
  - `terminate()` called after 10s pong timeout
  - Pong receipt clears timeout
  - `clearPingTimers()` called on disconnect, close, AND error
  - **Overlapping timeout: previous `pongTimeout` cleared before new ping sends**
  - **Null ws guard: ping callback returns early if `this.ws` is null or readyState !== OPEN**
  - **Reconnect scenario: after disconnect + reconnect, ping interval restarts fresh**
  - **Error handler: `error` event clears ping timers before reconnect**
- **Health hysteresis tests**: Mock platform data timestamps. Test cases:
  - Single unhealthy tick does NOT trigger degradation
  - 2 consecutive unhealthy ticks DO trigger degradation
  - Single healthy tick after degradation does NOT trigger recovery
  - 2 consecutive healthy ticks DO trigger recovery
  - Counter resets on opposite observation (healthy resets unhealthy counter, vice versa)
  - Counters initialize to 0 for all platforms
  - **Single-tick staleness at 65s (>60s threshold) does NOT degrade (needs 2 ticks)**
  - Verify `DegradationProtocolService.activateProtocol()` only called after consecutive threshold met
  - **No standalone 81s direct-activation path exists** (the old bypass is removed)
- **summarizeEvent tests**: Test cases:
  - Date → ISO string
  - Array of Dates → array of ISO strings
  - Decimal → string (via `toFixed` duck-typing)
  - Nested object → recursively serialized
  - null → null, undefined → undefined
  - Primitives → passthrough
  - No `[object]` in any output
  - **Circular reference → `'[Circular]'` (not stack overflow)**
  - **Deep nesting (>10 levels) → `'[MaxDepth]'`**
  - **Serialization error → fallback `{ error: 'serialization_failed', eventType: '...' }`**

### Project Structure Notes

- All changes within `pm-arbitrage-engine/src/` — no root repo changes
- Files follow existing kebab-case naming convention
- Tests co-located with source (`.spec.ts` suffix)
- No new modules, no new files, no new dependencies

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.5.4, lines 1649-1687] — Epic definition, ACs, previous story intelligence
- [Source: pm-arbitrage-engine/src/connectors/polymarket/polymarket-websocket.client.ts] — WebSocket client (no keepalive, staleness at 30s, handlePriceChange at line 207)
- [Source: pm-arbitrage-engine/src/connectors/kalshi/kalshi-websocket.client.ts] — Kalshi WS client (no keepalive, sequence gap detection)
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts] — Health cron (30s tick), staleness 60s, WS timeout 81s, single-observation triggers
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/degradation-protocol.service.ts] — Activate/deactivate lifecycle, event classes with Date/array/nested object fields
- [Source: pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts, lines 306-316] — `summarizeEvent()` with `[object]` fallback
- [Source: pm-arbitrage-engine/src/common/events/platform.events.ts] — DegradationProtocol events
- [Source: pm-arbitrage-engine/src/common/events/execution.events.ts] — SingleLegExposure, ExecutionFailed events
- [Source: pm-arbitrage-engine/src/common/errors/platform-api-error.ts] — `RETRY_STRATEGIES.WEBSOCKET_RECONNECT` (1s initial, 60s max, 2x, maxRetries: Infinity)
- [Source: _bmad-output/implementation-artifacts/6-5-3-validation-framework-go-no-go-criteria.md] — Previous story, test count baseline (1,101 tests)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None — no unresolved issues.

### Completion Notes List

- All 4 tasks implemented via strict TDD (tests first, then implementation)
- Baseline: 1,101 tests (70 files) → Final: 1,139 tests (70 files), +38 new tests
- 0 lint errors
- WebSocket keepalive added to both Polymarket and Kalshi WS clients (identical pattern: 30s ping, 10s pong timeout, clearPingTimers on disconnect/close/error)
- Removed standalone 81s WEBSOCKET_TIMEOUT_THRESHOLD direct-activation bypass — replaced with consecutive-tick hysteresis (2 unhealthy ticks to degrade, 2 healthy ticks to recover)
- Fixed summarizeEvent() with recursive serializeValue() — handles Date→ISO, Decimal→string (via `instanceof Decimal`), arrays, nested objects, circular refs, and max depth
- E2E test updated for 2-tick hysteresis recovery
- No new files, no new dependencies, no schema changes, no env var changes

**Code Review Fixes (CR-1):**
- Reverted `RETRY_STRATEGIES.WEBSOCKET_RECONNECT.maxRetries` from `20` back to `Infinity` (undocumented behavioral change)
- Updated circuit breaker test in polymarket-websocket.client.spec.ts to test Infinity reconnect behavior
- Added overlapping timeout prevention test to kalshi-websocket.client.spec.ts (was missing vs Polymarket parity)
- Fixed audit-log.service.spec.ts: added `vi.useFakeTimers()` to key-insertion-order hash test (timing-dependent flake)
- Reverted weakened timestamp assertion in logging.e2e-spec.ts back to strict `toBeInstanceOf(Date)`
- Updated story Task 4.1 docs: `instanceof Decimal` (actual) instead of duck-typing via `toFixed` (original spec)

### File List

- `pm-arbitrage-engine/src/connectors/polymarket/polymarket-websocket.client.ts` — Added keepalive ping (30s interval, 10s pong timeout, clearPingTimers)
- `pm-arbitrage-engine/src/connectors/polymarket/polymarket-websocket.client.spec.ts` — Added 9 keepalive tests
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-websocket.client.ts` — Added keepalive ping (same pattern as Polymarket)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-websocket.client.spec.ts` — Added 8 keepalive tests
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts` — Removed 81s bypass, added consecutiveUnhealthyTicks/consecutiveHealthyTicks maps and hysteresis logic
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.spec.ts` — Replaced 81s tests with 7 consecutive-check hysteresis tests, updated recovery tests for 2-tick requirement
- `pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts` — Replaced summarizeEvent() with recursive serializeValue() (circular ref + depth protection)
- `pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.spec.ts` — Added 11 serialization tests
- `pm-arbitrage-engine/src/common/errors/platform-api-error.ts` — Reverted maxRetries to Infinity (CR-1 fix: undocumented change)
- `pm-arbitrage-engine/src/modules/monitoring/audit-log.service.spec.ts` — Fixed timing-dependent hash test with vi.useFakeTimers() (CR-1 fix)
- `pm-arbitrage-engine/test/data-ingestion.e2e-spec.ts` — Updated recovery e2e test for 2-tick hysteresis
- `pm-arbitrage-engine/test/logging.e2e-spec.ts` — Reverted weakened timestamp assertion (CR-1 fix)
