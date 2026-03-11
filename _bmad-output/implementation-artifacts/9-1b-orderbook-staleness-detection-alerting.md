# Story 9.1b: Orderbook Staleness Detection & Alerting

Status: done

## Story

As an operator,
I want the system to detect when a platform stops providing valid order book data and alert me immediately via Telegram,
So that I can take corrective action without delay when an API issue occurs.

## Acceptance Criteria

1. **Given** a platform's order book data has not been successfully refreshed within a configurable staleness threshold (default: 90 seconds)
   **When** the `PlatformHealthService` 30s health tick runs
   **Then** an `ORDERBOOK_STALE` event (`platform.orderbook.stale`) is emitted with platform ID, last successful update timestamp, staleness duration in ms, and the configured threshold
   **And** the event is emitted exactly once per staleness episode (not re-emitted every tick)
   [Source: epics.md Story 9.1b AC1; sprint-change-proposal Section 5 success criteria; FR-DI-04 health publishing]

2. **Given** a Telegram alert is triggered by an `ORDERBOOK_STALE` event
   **When** the monitoring hub processes the event
   **Then** a Telegram message is sent with actionable context: platform name, staleness duration, last successful update timestamp, and suggested diagnostic steps
   [Source: epics.md Story 9.1b AC1 — "Telegram alert is sent with actionable context"]

3. **Given** a platform's order book was stale but fresh data resumes (a successful `recordUpdate()` call occurs)
   **When** the next `PlatformHealthService` 30s health tick runs
   **Then** an `ORDERBOOK_RECOVERED` event (`platform.orderbook.recovered`) is emitted with platform ID, recovery timestamp, and total downtime duration
   **And** a Telegram recovery notification is sent
   [Source: epics.md Story 9.1b AC2]

4. **Given** a platform's order book is stale (staleness threshold exceeded)
   **When** the arbitrage detection cycle runs (`DetectionService.detectDislocations()`)
   **Then** opportunities involving the stale platform are suppressed
   **And** the skip reason is logged as `orderbook_stale` with the staleness duration
   [Source: epics.md Story 9.1b AC3]

5. **Given** the operator wants to tune staleness sensitivity
   **When** `ORDERBOOK_STALENESS_THRESHOLD_MS` env var is set
   **Then** the staleness detection uses the configured threshold instead of the 90s default
   [Derived from: epics.md Story 9.1b AC1 — "configurable staleness threshold"]

## Tasks / Subtasks

**Execution order: 1 → 2 → 3 → 4 → 5 → 6 → 7**

- [x] **Task 1: Event catalog + event classes** (AC: #1, #3)
  - [x]1.1 Add to `event-catalog.ts`: `ORDERBOOK_STALE: 'platform.orderbook.stale'` and `ORDERBOOK_RECOVERED: 'platform.orderbook.recovered'`. Place after `DATA_STALE` in the Epic 1 events section.
  - [x]1.2 Create `OrderbookStaleEvent` class in `common/events/platform.events.ts` extending `BaseEvent`: fields `platformId: PlatformId`, `lastUpdateTimestamp: Date | null`, `stalenessMs: number`, `thresholdMs: number`, optional `correlationId?: string` (passed to `super()`). Follow the constructor pattern of `DataStaleEvent` (`platform.events.ts:86-95`).
  - [x]1.3 Create `OrderbookRecoveredEvent` class in `common/events/platform.events.ts` extending `BaseEvent`: fields `platformId: PlatformId`, `recoveryTimestamp: Date`, `downtimeMs: number`, optional `correlationId?: string` (passed to `super()`). Follow the constructor pattern of `PlatformRecoveredEvent`.
  - [x]1.4 Export both from `common/events/index.ts` (verify re-export barrel picks them up automatically — if `platform.events` is already re-exported, no change needed)

- [x] **Task 2: Env var + Zod schema** (AC: #5)
  - [x]2.1 Add `ORDERBOOK_STALENESS_THRESHOLD_MS` to `common/config/env.schema.ts` with `z.coerce.number().positive().default(90_000)` and descriptive comment
  - [x]2.2 Add to `.env.example` with default value and comment

- [x] **Task 3: PlatformHealthService — orderbook staleness tracking** (AC: #1, #3, #5)
  - [x]3.1 Add private state: `private orderbookStale = new Map<PlatformId, boolean>()` and `private orderbookStaleStartTime = new Map<PlatformId, number>()` to track when staleness began (for downtime calculation on recovery). No explicit initialization needed — the `?? false` fallback in `isOrderbookStale()` handles missing keys.
  - [x]3.2 Inject `ConfigService` into the constructor (add `private readonly configService: ConfigService` parameter). Read the threshold in the constructor: `this.orderbookStalenessThreshold = this.configService.get<number>('ORDERBOOK_STALENESS_THRESHOLD_MS', 90_000);`. `ConfigService` is globally available from `@nestjs/config` (registered as global in `AppModule`).
  - [x]3.3 In `publishHealth()`, inside the existing `for (const platform of platforms)` loop, after the `calculateHealth()` call and BEFORE the degradation protocol `try` block (~line 140), add orderbook staleness check wrapped in its own try-catch. The variable `lastUpdate` is already available in the loop scope (extracted from `this.lastUpdateTime.get(platform)`):
    ```typescript
    try {
      const lastUpdate = this.lastUpdateTime.get(platform) || 0;
      const dataAge = Date.now() - lastUpdate;
      const wasStale = this.orderbookStale.get(platform) ?? false;
      const isNowStale = lastUpdate > 0 && dataAge > this.orderbookStalenessThreshold;

      if (isNowStale && !wasStale) {
        // Transition to stale
        this.orderbookStale.set(platform, true);
        this.orderbookStaleStartTime.set(platform, Date.now());
        this.eventEmitter.emit(EVENT_NAMES.ORDERBOOK_STALE, new OrderbookStaleEvent(
          platform,
          lastUpdate > 0 ? new Date(lastUpdate) : null,
          dataAge,
          this.orderbookStalenessThreshold,
          correlationId,
        ));
      } else if (!isNowStale && wasStale) {
        // Transition to recovered
        const staleStart = this.orderbookStaleStartTime.get(platform) ?? Date.now();
        const downtimeMs = Date.now() - staleStart;
        this.orderbookStale.set(platform, false);
        this.orderbookStaleStartTime.delete(platform);
        this.eventEmitter.emit(EVENT_NAMES.ORDERBOOK_RECOVERED, new OrderbookRecoveredEvent(
          platform,
          new Date(),
          downtimeMs,
          correlationId,
        ));
      }
    } catch (error) {
      this.logger.error({
        message: 'Orderbook staleness detection error',
        module: 'data-ingestion',
        correlationId,
        platform,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
    ```
    Note: `correlationId` is already defined in the `publishHealth()` scope (`const correlationId = randomUUID()` at ~line 56).
  - [x]3.4 Add public method that returns staleness info including duration (needed by DetectionService for AC4 logging):
    ```typescript
    getOrderbookStaleness(platform: PlatformId): { stale: boolean; stalenessMs?: number } {
      const isStale = this.orderbookStale.get(platform) ?? false;
      if (!isStale) return { stale: false };
      const lastUpdate = this.lastUpdateTime.get(platform) ?? 0;
      return { stale: true, stalenessMs: lastUpdate > 0 ? Date.now() - lastUpdate : undefined };
    }
    ```
  - [x]3.5 Edge case: if `lastUpdateTime` is 0 (never received any data), do NOT emit `ORDERBOOK_STALE` — this is system startup, not a staleness condition. The check `lastUpdateTime > 0` handles this.
  - [x]3.6 Write co-located spec: update `platform-health.service.spec.ts` with new tests for orderbook staleness detection, recovery, and edge cases

- [x] **Task 4: DetectionService — explicit orderbook staleness suppression** (AC: #4)
  - [x]4.1 Inject `PlatformHealthService` into `DetectionService` constructor (already available — `ArbitrageDetectionModule` imports `DataIngestionModule` which exports `PlatformHealthService`)
  - [x]4.2 In `detectDislocations()`, add an orderbook staleness check BEFORE the existing `degradationService.isDegraded()` check for each platform (follows the same per-platform check pattern at `detection.service.ts:34-65`). This ensures explicit staleness logging even if the degradation protocol hasn't activated yet (faster detection at 90s vs degradation protocol at ~120s):
    ```typescript
    const kalshiStaleness = this.healthService.getOrderbookStaleness(PlatformId.KALSHI);
    if (kalshiStaleness.stale) {
      this.logger.debug({
        message: 'Skipping pair — orderbook data stale',
        module: 'arbitrage-detection',
        correlationId: getCorrelationId(),
        data: {
          eventDescription: pair.eventDescription,
          platformId: PlatformId.KALSHI,
          skipReason: 'orderbook_stale',
          stalenessMs: kalshiStaleness.stalenessMs,
        },
      });
      pairsSkipped++;
      continue;
    }
    ```
    Same pattern for Polymarket. These checks go BEFORE the existing `degradationService.isDegraded()` checks, not replacing them — both layers remain as defense-in-depth.
  - [x]4.3 Update `detection.service.spec.ts` with tests for orderbook staleness suppression

- [x] **Task 5: Telegram formatters** (AC: #2, #3)
  - [x]5.1 In `monitoring/formatters/telegram-message.formatter.ts`, add `formatOrderbookStale(event: OrderbookStaleEvent): string`:
    ```
    🟠 <b>ORDERBOOK STALE</b>

    Platform: <code>${event.platformId}</code>
    Stale for: <b>${Math.round(event.stalenessMs / 1000)}s</b>
    Last update: <code>${event.lastUpdateTimestamp?.toISOString() ?? 'never'}</code>
    Threshold: ${event.thresholdMs / 1000}s

    <b>Action:</b> Check platform API status, WebSocket connection, and connector logs.
    ```
  - [x]5.2 Add `formatOrderbookRecovered(event: OrderbookRecoveredEvent): string`:
    ```
    🟢 <b>ORDERBOOK RECOVERED</b>

    Platform: <code>${event.platformId}</code>
    Downtime: <b>${Math.round(event.downtimeMs / 1000)}s</b>
    Recovered at: <code>${event.recoveryTimestamp.toISOString()}</code>

    Orderbook data flow restored. Detection resumed.
    ```
  - [x]5.3 Register both in `FORMATTER_REGISTRY` (in `telegram-alert.service.ts`, not `telegram-message.formatter.ts`)
  - [x]5.4 Add `'platform.orderbook.stale': 'warning'` and `'platform.orderbook.recovered': 'info'` to `EVENT_SEVERITY_MAP`
  - [x]5.5 Update `telegram-message.formatter.spec.ts` with tests for both formatters

- [x] **Task 6: Event severity + Telegram eligibility registration** (AC: #2, #3)
  - [x]6.1 In `event-consumer.service.ts`, add `EVENT_NAMES.ORDERBOOK_STALE` to `WARNING_EVENTS` set (ensures severity = warning → always sends Telegram)
  - [x]6.2 Add `EVENT_NAMES.ORDERBOOK_RECOVERED` to `TELEGRAM_ELIGIBLE_INFO_EVENTS` set (info-level but operationally important → sends Telegram)

- [x] **Task 7: Dashboard WebSocket event forwarding** (AC: #1, #3)
  - [x]7.1 Check `pm-arbitrage-engine/src/dashboard/dashboard-event-mapper.service.ts` — look for `@OnEvent` decorators or `EventEmitter2.on()` calls. If it uses wildcard subscription (`**` or `onAny`), new events are forwarded automatically — no change needed. If it uses an explicit event name list, add `EVENT_NAMES.ORDERBOOK_STALE` and `EVENT_NAMES.ORDERBOOK_RECOVERED` entries.
  - [x]7.2 Write or update spec if changes are made

## Dev Notes

### Architecture & Patterns

**Module boundary compliance — NO violations:**
- `PlatformHealthService` is in `modules/data-ingestion/` and is exported from `DataIngestionModule`. It already owns platform health monitoring. Adding orderbook staleness tracking here follows single responsibility.
- `DetectionService` in `modules/arbitrage-detection/` already imports `DataIngestionModule` (which exports `PlatformHealthService` and `DegradationProtocolService`). Adding `PlatformHealthService` injection to `DetectionService` follows the established import path.
- Event classes live in `common/events/` — accessible to all modules per architecture rules.
- Telegram formatters live in `modules/monitoring/formatters/` — monitoring subscribes to events, never the reverse.
[Source: architecture.md lines 600-610; ArbitrageDetectionModule imports DataIngestionModule at `arbitrage-detection.module.ts:8`; DataIngestionModule exports PlatformHealthService at `data-ingestion.module.ts:29`]

**Relationship to existing health infrastructure:**
- `PlatformHealthService.calculateHealth()` already detects data staleness at 60s and marks status as `'degraded'`. This triggers `PLATFORM_HEALTH_DEGRADED` event and eventually activates the `DegradationProtocolService` (after 2 consecutive unhealthy ticks = ~120s total).
- The NEW `ORDERBOOK_STALE` event is a dedicated, higher-threshold (90s) alert specifically for orderbook data, complementing the generic platform degradation path. The distinction matters: platform degradation covers latency, connection issues, AND staleness; orderbook staleness is specifically about data flow.
- The existing `DataStaleEvent` (`platform.health.data-stale`) is a per-token WebSocket-level check in the Polymarket WS client (30s threshold, per individual token). This is a different concern — it discards stale individual order books at the WS layer. The new `ORDERBOOK_STALE` is a platform-level check in the health service.
[Source: Codebase `platform-health.service.ts:20` — STALENESS_THRESHOLD = 60_000; `platform-health.service.ts:52-188` — publishHealth flow; `polymarket-websocket.client.ts:281-294` — per-token staleness check]

**Detection suppression — layered approach:**
1. **Orderbook staleness check** (NEW, ~90s): `healthService.getOrderbookStaleness(platform)` — returns `{ stale: boolean, stalenessMs?: number }`. Logs `skipReason: 'orderbook_stale'` with duration.
2. **Degradation protocol check** (existing, ~120s): `degradationService.isDegraded(platform)` — logs `skipReason: 'platform degraded'`
3. Both checks are in `DetectionService.detectDislocations()`. The staleness check fires first (lower threshold), providing faster suppression and explicit logging. Both checks remain as defense-in-depth — they are not mutually exclusive.
[Source: Codebase `detection.service.ts:34-65` — existing degradation check; epics.md Story 9.1b AC3]

**Event emission — exactly-once per episode:**
- Track `orderbookStale: Map<PlatformId, boolean>` state per platform. Emit `ORDERBOOK_STALE` only on `false→true` transition. Emit `ORDERBOOK_RECOVERED` only on `true→false` transition. The 30s cron fires every tick but only emits on state changes.
- `orderbookStaleStartTime` tracks when staleness began so the recovery event can include total downtime.
[Source: Existing pattern — `previousStatus` map in `platform-health.service.ts:28-31` tracks platform status transitions the same way]

**Startup edge case:**
- If `lastUpdateTime` is 0 (no data received yet — system just booted), do NOT emit `ORDERBOOK_STALE`. The health service can't distinguish "stale" from "not yet started receiving data". The `lastUpdateTime > 0` guard handles this.
- Once the first `recordUpdate()` call sets `lastUpdateTime`, the staleness timer begins.

### Codebase Touchpoints

**Files to MODIFY (no new files created):**
- `pm-arbitrage-engine/src/common/events/event-catalog.ts` — add `ORDERBOOK_STALE`, `ORDERBOOK_RECOVERED` events (~line 32)
- `pm-arbitrage-engine/src/common/events/platform.events.ts` — add `OrderbookStaleEvent`, `OrderbookRecoveredEvent` classes (after `DataStaleEvent` ~line 95)
- `pm-arbitrage-engine/src/common/config/env.schema.ts` — add `ORDERBOOK_STALENESS_THRESHOLD_MS` Zod schema
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts` — add orderbook staleness tracking, `isOrderbookStale()` method, inject ConfigService
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.spec.ts` — add staleness/recovery tests
- `pm-arbitrage-engine/src/modules/arbitrage-detection/detection.service.ts` — inject `PlatformHealthService`, add orderbook staleness check
- `pm-arbitrage-engine/src/modules/arbitrage-detection/detection.service.spec.ts` — add staleness suppression tests
- `pm-arbitrage-engine/src/modules/monitoring/formatters/telegram-message.formatter.ts` — add formatters + severity map entries + register in `FORMATTER_REGISTRY`
- `pm-arbitrage-engine/src/modules/monitoring/formatters/telegram-message.formatter.spec.ts` — add formatter tests
- `pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts` — add to `WARNING_EVENTS` and `TELEGRAM_ELIGIBLE_INFO_EVENTS` sets
- `pm-arbitrage-engine/.env.example` — add `ORDERBOOK_STALENESS_THRESHOLD_MS=90000`

**Files to CHECK (may need modification):**
- `pm-arbitrage-engine/src/dashboard/dashboard-event-mapper.service.ts` — check if new events need explicit registration for WS forwarding
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.module.ts` — verify `ConfigService` is available (should be via `@nestjs/config` global module)

### Existing Infrastructure Reuse

| Concern | Existing Pattern | This Story |
|---------|-----------------|------------|
| Event emission | `PlatformDegradedEvent` transition detection in `publishHealth()` | Same state-transition pattern for `OrderbookStaleEvent` |
| Telegram alerting | `FORMATTER_REGISTRY` map + `handleEvent()` | Register formatters same way |
| Severity classification | `EVENT_SEVERITY_MAP` + `WARNING_EVENTS`/`TELEGRAM_ELIGIBLE_INFO_EVENTS` | Add entries to both |
| Detection suppression | `degradationService.isDegraded()` in `detectDislocations()` | Add parallel `healthService.getOrderbookStaleness()` check |
| Env var validation | Zod schemas in `env.schema.ts` with `z.coerce.number().default()` | Same pattern |
| Event classes | `BaseEvent` extension with readonly fields | Same pattern |

### Testing Strategy

- **Framework:** Vitest 4 (NOT Jest). Co-located tests. Run with `pnpm test`
- **PlatformHealthService tests** (update `platform-health.service.spec.ts`):
  - "should emit ORDERBOOK_STALE when data age exceeds threshold": set `lastUpdateTime` to `Date.now() - 91_000`, call `publishHealth()`, verify `ORDERBOOK_STALE` emitted with correct `stalenessMs` and `thresholdMs`
  - "should NOT re-emit ORDERBOOK_STALE on subsequent ticks": call `publishHealth()` again while still stale, verify NO second emission
  - "should emit ORDERBOOK_RECOVERED when data resumes": call `recordUpdate()` to refresh `lastUpdateTime`, call `publishHealth()`, verify `ORDERBOOK_RECOVERED` emitted with correct `downtimeMs`
  - "should NOT emit ORDERBOOK_STALE when lastUpdateTime is 0 (startup)": leave `lastUpdateTime` at default, call `publishHealth()`, verify no event emitted
  - "should track platforms independently": make Kalshi stale but Polymarket fresh, verify only Kalshi event emitted
  - "getOrderbookStaleness should return stale=true with duration when stale": verify return value shape
  - "getOrderbookStaleness should return stale=false when not stale": verify return value shape
- **DetectionService tests** (update `detection.service.spec.ts`):
  - "should skip pairs when orderbook is stale": mock `healthService.getOrderbookStaleness()` returning `{ stale: true, stalenessMs: 95000 }` for Kalshi, verify pairs skipped with `skipReason: 'orderbook_stale'` and `stalenessMs` in log
  - "should not skip pairs when orderbook is fresh": mock returning `{ stale: false }`, verify pairs proceed
- **Telegram formatter tests** (update `telegram-message.formatter.spec.ts`): verify HTML output contains platform name, staleness duration, timestamps, action guidance for both `formatOrderbookStale` and `formatOrderbookRecovered`
- **Green baseline:** 1880 tests across 111 files. All must pass after changes.

### Known Limitations

- **In-memory state:** The `orderbookStale` and `orderbookStaleStartTime` Maps are in-memory. If the system restarts during a staleness episode, no `ORDERBOOK_RECOVERED` event will be emitted when data resumes (the Map resets to empty). The next staleness episode will work correctly. This matches the existing pattern — `previousStatus`, `consecutiveUnhealthyTicks`, and `lastUpdateTime` are all in-memory in `PlatformHealthService`. Persisting health state to DB was intentionally avoided for performance (FR-DI-04).

### Error Handling

- New staleness detection logic in `publishHealth()` is wrapped in its own try-catch (see Task 3.3) — same pattern as the existing degradation protocol try-catch block at `platform-health.service.ts:140`
- Telegram delivery failures are handled by `TelegramAlertService` infrastructure (circuit breaker, buffer, retry)
- `getOrderbookStaleness()` is a simple map lookup + arithmetic — cannot throw
- No new error types needed — this is an observability feature, not a business logic change

### Previous Story Intelligence

- **9-1 (correlation clusters):** Added `ClusterLimitApproachedEvent` to `risk.events.ts` and 3 events to `event-catalog.ts`. Follow same event registration pattern for `ORDERBOOK_STALE`/`ORDERBOOK_RECOVERED`.
- **9-1a (Kalshi FP migration):** The incident that exposed this gap. Kalshi responses failed Zod validation → `getOrderBook()` threw → `recordUpdate()` never called → `lastUpdateTime` went stale → platform eventually degraded. But no dedicated alert fired, and the 120s degradation protocol lag meant slow detection.
- **Story 6.5.0a:** Added `DataStaleEvent` and `DATA_STALE` event to catalog for per-token WS-level staleness (30s threshold, Polymarket only). This story's platform-level `ORDERBOOK_STALE` is complementary, not duplicative.
- **Story 1.4:** Implemented `PlatformHealthService` with 30s cron tick, 60s staleness threshold, hysteresis. The 60s threshold remains for generic platform degradation; this story adds a separate 90s configurable threshold for orderbook-specific alerting.

### Configuration (new env vars)

```
ORDERBOOK_STALENESS_THRESHOLD_MS=90000    # 90s — platform orderbook staleness alert threshold
```

Note: This is independent of the existing hardcoded `STALENESS_THRESHOLD` (60s) in `PlatformHealthService` which drives platform health status to `'degraded'`. The 60s platform threshold causes status changes; the 90s orderbook threshold triggers operator alerts. The 90s default was chosen by the sprint change proposal to align with degradation protocol activation timing (~90s for 2 consecutive unhealthy ticks at 30s intervals after the 60s generic threshold).

### Deferred Items (explicitly out of scope)

- **Kalshi WS client staleness check parity:** The Polymarket WS client has a per-token 30s staleness check (`polymarket-websocket.client.ts:281-294`). The Kalshi WS client does NOT have an equivalent. Adding one is a separate improvement — this story focuses on platform-level observability.
- **Configurable generic staleness threshold:** The existing 60s `STALENESS_THRESHOLD` in `PlatformHealthService` is hardcoded. Making it configurable is a separate tech debt item.
- **Dashboard UI for staleness indicators:** Visual staleness indicators on the dashboard SPA. Separate dashboard story.

### Project Structure Notes

- No new files created — all changes modify existing files
- Event naming follows dot-notation: `platform.orderbook.stale`, `platform.orderbook.recovered`
- Event classes follow PascalCase: `OrderbookStaleEvent`, `OrderbookRecoveredEvent`
- Env var follows UPPER_SNAKE_CASE: `ORDERBOOK_STALENESS_THRESHOLD_MS`
- All imports follow established module dependency paths

### References

- [Source: epics.md Story 9.1b] User story, acceptance criteria
- [Source: sprint-change-proposal-2026-03-12.md Section 2] "Secondary issue" — no alert fired, observability gap
- [Source: sprint-change-proposal-2026-03-12.md Section 4] Files affected, implementation approach
- [Source: sprint-change-proposal-2026-03-12.md Section 5] Success criteria: "Telegram alert fires within 90s"
- [Source: PRD FR-DI-03] Platform API degradation detection within 81s
- [Source: PRD FR-DI-04] Platform health status updates every 30s
- [Source: PRD NFR-R4] Platform health detection specification
- [Source: architecture.md line 33] NFR-R4 — 30s platform health detection
- [Source: Codebase `platform-health.service.ts:19-21`] STALENESS_THRESHOLD = 60s, DEGRADED_LATENCY_THRESHOLD = 2s, DATA_FRESHNESS_THRESHOLD = 30s
- [Source: Codebase `platform-health.service.ts:52-188`] publishHealth() — cron, health calculation, transition events, degradation protocol integration
- [Source: Codebase `platform-health.service.ts:275-282`] recordUpdate() — sets lastUpdateTime
- [Source: Codebase `detection.service.ts:34-65`] detectDislocations() — existing degradation check pattern
- [Source: Codebase `arbitrage-detection.module.ts:8`] ArbitrageDetectionModule imports DataIngestionModule
- [Source: Codebase `data-ingestion.module.ts:28-29`] DataIngestionModule exports PlatformHealthService
- [Source: Codebase `event-catalog.ts:31-32`] DATA_STALE event — per-token WS-level, different scope
- [Source: Codebase `platform.events.ts:86-95`] DataStaleEvent — per-token, includes tokenId
- [Source: Codebase `polymarket-websocket.client.ts:281-294`] Per-token 30s staleness check (Polymarket only)
- [Source: Codebase `kalshi-websocket.client.ts:333-348`] Kalshi emitUpdate — no staleness check
- [Source: Codebase `event-consumer.service.ts:27-60`] CRITICAL_EVENTS, WARNING_EVENTS, TELEGRAM_ELIGIBLE_INFO_EVENTS sets
- [Source: Codebase `telegram-message.formatter.ts:112-178`] FORMATTER_REGISTRY pattern
- [Source: Codebase `telegram-message.formatter.ts:589-614`] EVENT_SEVERITY_MAP

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A

### Completion Notes List

- All 7 tasks completed in order via TDD (red-green-refactor)
- Baseline: 111 files, 1880 tests → Final: 111 files, 1898 tests (18 new tests)
- Lad MCP code review completed (2 reviewers: moonshotai/kimi-k2.5, z-ai/glm-5)
- **Review fix applied (HIGH):** Changed `getOrderbookStaleness()` from poll-state lookup to real-time on-demand calculation from `lastUpdateTime`. Eliminates up to 30s detection delay for the detection service.
- **Review fix applied (MEDIUM):** Pre-initialized `orderbookStale` Map in constructor for consistency with existing counter initialization pattern.
- Other review findings (race conditions, clock drift, skip reason formatting) were evaluated and rejected: race conditions are inherent to 30s polling design (documented in Known Limitations), clock drift is handled by NTP sync service (Story 1.6), skip reason formatting is pre-existing convention.
- Task 7 (Dashboard WS forwarding): No changes needed — dashboard uses explicit `@OnEvent` decorators, but `PLATFORM_HEALTH_UPDATED` already broadcasts health every tick. New events are for Telegram alerting, not dashboard state.
- All AC verified: AC1 (exactly-once emission), AC2 (Telegram with context), AC3 (recovery event + notification), AC4 (detection suppression with `orderbook_stale` skip reason), AC5 (configurable threshold via env var)
- **Code review (Amelia, 2026-03-13):** Fixed 2 MEDIUM, 2 LOW issues. M1: clarified Task 5.3 text (FORMATTER_REGISTRY is in telegram-alert.service.ts not formatter file). M2: accepted — stalenessMs undefined scenario architecturally unreachable. L1: added `.int()` to ORDERBOOK_STALENESS_THRESHOLD_MS Zod schema for consistency. L2: updated stale comment "14 events" → "19 events" in telegram-alert.service.ts.

### File List

**Modified:**
- `pm-arbitrage-engine/src/common/events/event-catalog.ts` — Added `ORDERBOOK_STALE`, `ORDERBOOK_RECOVERED` event names
- `pm-arbitrage-engine/src/common/events/platform.events.ts` — Added `OrderbookStaleEvent`, `OrderbookRecoveredEvent` classes
- `pm-arbitrage-engine/src/common/config/env.schema.ts` — Added `ORDERBOOK_STALENESS_THRESHOLD_MS` Zod schema
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts` — Added orderbook staleness tracking, `getOrderbookStaleness()` method, `ConfigService` injection
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.spec.ts` — Added 10 tests (staleness detection, recovery, edge cases, `getOrderbookStaleness()`)
- `pm-arbitrage-engine/src/modules/arbitrage-detection/detection.service.ts` — Added `PlatformHealthService` injection, orderbook staleness suppression checks
- `pm-arbitrage-engine/src/modules/arbitrage-detection/detection.service.spec.ts` — Added 3 tests (Kalshi stale skip, Polymarket stale skip, fresh no-skip)
- `pm-arbitrage-engine/src/modules/monitoring/formatters/telegram-message.formatter.ts` — Added `formatOrderbookStale()`, `formatOrderbookRecovered()` formatters, severity map entries
- `pm-arbitrage-engine/src/modules/monitoring/formatters/telegram-message.formatter.spec.ts` — Added 5 tests (formatter output, severity classification)
- `pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.ts` — Added formatters to `FORMATTER_REGISTRY` and `TELEGRAM_ELIGIBLE_EVENTS`
- `pm-arbitrage-engine/src/modules/monitoring/telegram-alert.service.spec.ts` — Updated `TELEGRAM_ELIGIBLE_EVENTS` count (17→19) and expected list
- `pm-arbitrage-engine/src/modules/monitoring/event-consumer.service.ts` — Added `ORDERBOOK_STALE` to `WARNING_EVENTS`, `ORDERBOOK_RECOVERED` to `TELEGRAM_ELIGIBLE_INFO_EVENTS`
- `pm-arbitrage-engine/.env.example` — Added `ORDERBOOK_STALENESS_THRESHOLD_MS=90000`
