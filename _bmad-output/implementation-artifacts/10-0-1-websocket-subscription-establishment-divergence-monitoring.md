# Story 10-0-1: WebSocket Subscription Establishment & Divergence Monitoring

Status: done

## Story

As an operator,
I want WebSocket connections to actually subscribe to contract tickers and divergence between poll and WebSocket data paths to be monitored,
So that exit decisions can use real-time data and I'm alerted when data paths drift apart.

## Acceptance Criteria

1. **Given** the `IPlatformConnector` interface **When** this story is implemented **Then** two new methods exist: `subscribeToContracts(contractIds: ContractId[]): void` and `unsubscribeFromContracts(contractIds: ContractId[]): void` [Source: epics.md#Story-10-0-1, AC #1; retro action item #6]

2. **Given** the `KalshiConnector` **When** `subscribeToContracts` is called **Then** it uses Kalshi's `update_subscription` command with `action: "add_markets"` to batch-add tickers to the existing `orderbook_delta` subscription **And** `unsubscribeFromContracts` uses `action: "delete_markets"` **And** the connector tracks the `sid` (subscription ID) from the initial `subscribed` response [Source: Kalshi WS API docs — docs.kalshi.com/websockets/websocket-connection; disambiguation Q2 confirmed]

3. **Given** the `PolymarketConnector` **When** `subscribeToContracts` is called **Then** it sends `{ assets_ids: [...], operation: "subscribe" }` per Polymarket's dynamic subscription format **And** `unsubscribeFromContracts` sends `{ assets_ids: [...], operation: "unsubscribe" }` **And** `ContractId` for Polymarket maps to the `clobTokenId` (asset_id), not the condition ID — this is the same identifier used by the existing `getOrderBook()` method [Source: Polymarket WS API docs — docs.polymarket.com/trading/orderbook#dynamic-subscribe-and-unsubscribe; disambiguation Q2 confirmed]

4. **Given** the `PaperTradingConnector` **When** `subscribeToContracts` or `unsubscribeFromContracts` is called **Then** it delegates to `this.realConnector.subscribeToContracts(contractIds)` / `this.realConnector.unsubscribeFromContracts(contractIds)` (paper mode uses real market data) [Source: existing PaperTradingConnector delegation pattern — paper-trading.connector.ts:33-47]

5. **Given** the WS protocol correctness fixes (prerequisite for working subscriptions) **When** this story is implemented **Then** Kalshi `KalshiWebSocketClient.unsubscribe()` uses the correct `sids`-based or `update_subscription`-based unsubscribe format (not the current incorrect `market_ticker` format) **And** Polymarket `PolymarketWebSocketClient.sendSubscribe()` uses `{ assets_ids: [...], operation: "subscribe" }` for dynamic subscriptions (not the current `{ auth: {}, type: 'subscribe', ... }` format) **And** Polymarket `PolymarketWebSocketClient.unsubscribe()` sends a WS `{ assets_ids: [...], operation: "unsubscribe" }` message (currently only does local cleanup) [Source: Kalshi WS docs — unsubscribe requires sids; Polymarket WS docs — dynamic subscription uses `operation` field; disambiguation Q1 confirmed as in-scope protocol correctness fixes]

6. **Given** `DataIngestionService` **When** the system starts up **Then** it queries open positions from the database and subscribes to the contract IDs for both legs of each open position (startup rehydration) **And** exposes `subscribeForPosition(pairId: PairId, kalshiContractId: ContractId, polymarketContractId: ContractId)` and `unsubscribeForPosition(pairId: PairId)` methods **And** manages a `Map<PairId, { kalshiContractId, polymarketContractId }>` of active subscriptions internally [Source: epics.md#Story-10-0-1, AC #1 — "exit monitor subscribes to tickers for all open positions"; disambiguation Q4 — DataIngestionService owns connector interactions, startup rehydration confirmed]

7. **Given** the exit monitor opens a new position (via `OrderFilledEvent` or position status change to OPEN) **When** the event fires **Then** `DataIngestionService.subscribeForPosition()` is called to subscribe to the pair's contract IDs on both platforms [Source: disambiguation Q4 — event-driven subscription lifecycle]

8. **Given** a position transitions to CLOSED **When** the position close event fires **Then** `DataIngestionService.unsubscribeForPosition()` is called **And** the connector-level unsubscribe is only called if no other open position references the same contract ID (ref-counting) [Derived from: multiple positions can share the same contract match/pair]

9. **Given** WebSocket subscriptions are active **When** both poll and WebSocket data arrive for the same contract **Then** a new `DataDivergenceService` in `data-ingestion/` compares best-bid and best-ask prices from both sources **And** divergence exceeding a configurable threshold (default: 2% price delta or 90s staleness delta) emits a `platform.data.divergence` event **And** the service is read-only and observational — it does not arbitrate or modify either data path [Source: epics.md#Story-10-0-1, AC #2; retro Team Agreement #23; disambiguation Q3 — read-only observational constraint]

10. **Given** the data path contract **When** the system operates **Then** polling remains authoritative for entry decisions (detection pipeline reads poll snapshots) **And** WebSocket is authoritative for exit decisions (exit monitor reads WS-maintained book) **And** this contract is documented in code-level JSDoc on the data path entry points [Source: epics.md#Story-10-0-1, AC #3; retro architecture decision — "retrofit, don't rethink"]

11. **Given** the dashboard health view **When** platform health is displayed **Then** three new fields appear on `PlatformHealthDto`: `wsSubscriptionCount` (number of active WS subscriptions), `divergenceStatus` (`'normal' | 'divergent'`), and `wsLastMessageTimestamp` (ISO timestamp of most recent WS message received) [Source: epics.md#Story-10-0-1, AC #2 — "divergence metrics are available on the dashboard health view"; retro Team Agreement #18 — vertical slice minimum; disambiguation Q5 confirmed with wsLastMessageTimestamp addition]

12. **Given** a divergence event fires **Then** the `DashboardEventMapperService` maps it to a WS gateway push event for real-time dashboard notification **And** the `TelegramAlertService` (via `EventConsumerService`) sends an alert [Source: existing fan-out pattern — event-consumer.service.ts subscribes to events, telegram-alert.service.ts formats alerts]

13. **Given** internal subsystem verification (Team Agreement #19) **When** tests are written for subscription establishment **Then** tests verify that subscribe messages are actually sent over the WebSocket connection (not just that the handler processes mock data) **And** tests verify startup rehydration queries open positions and subscribes [Source: retro Team Agreement #19 — internal subsystem verification mandate]

## Tasks / Subtasks

### Phase 1: WS Protocol Correctness Fixes (prerequisite for all subscription work)

- [x] **Task 1: Fix Kalshi WS client subscription ID tracking** (AC: #5)
  - [x] Add `subscriptionId: number | null` property to `KalshiWebSocketClient` to store the `sid` from `subscribed` responses
  - [x] Update `handleMessage()` to extract and store `sid` from `{ type: "subscribed", msg: { sid: N } }` responses
  - [x] Refactor `unsubscribe(ticker)` to use `update_subscription` with `action: "delete_markets"` and stored `sid`, instead of the current incorrect `{ cmd: 'unsubscribe', params: { channels, market_ticker } }` format
  - [x] Add `addMarkets(tickers: string[])` method that sends `{ cmd: "update_subscription", params: { sids: [sid], market_tickers: tickers, action: "add_markets" } }`
  - [x] Add `removeMarkets(tickers: string[])` method that sends `{ cmd: "update_subscription", params: { sids: [sid], market_tickers: tickers, action: "delete_markets" } }`
  - [x] Update `debouncedResubscribe()` to use `addMarkets` for reconnection scenarios
  - [x] Tests: verify `subscribed` response stores `sid`; verify `addMarkets` sends correct JSON; verify `removeMarkets` sends correct JSON; verify `unsubscribe` uses `update_subscription` format (internal subsystem verification: assert WS `.send()` is called with correct payload)

- [x] **Task 2: Fix Polymarket WS client dynamic subscribe/unsubscribe** (AC: #5)
  - [x] Refactor `sendSubscribe(tokenId)` to send `{ assets_ids: [tokenId], operation: "subscribe" }` for dynamic subscriptions (current format `{ auth: {}, type: 'subscribe', markets: [], assets_ids: [tokenId] }` does not match Polymarket docs)
  - [x] Add `sendInitialSubscription(tokenIds: string[])` method for the initial subscription message: `{ type: "market", assets_ids: [...], custom_feature_enabled: true }`
  - [x] Differentiate initial vs dynamic subscription: first call after `connect()` uses initial format; subsequent calls use dynamic `operation: "subscribe"` format. Track with `hasInitialSubscription` flag.
  - [x] Update `unsubscribe(tokenId)` to send `{ assets_ids: [tokenId], operation: "unsubscribe" }` over WS before cleaning up local state
  - [x] Tests: verify dynamic subscribe sends `operation: "subscribe"` payload; verify unsubscribe sends `operation: "unsubscribe"` payload; verify initial subscription sends `type: "market"` format (internal subsystem verification: assert WS `.send()` is called)

### Phase 2: IPlatformConnector Interface Extension

- [x] **Task 3: Add subscription methods to IPlatformConnector** (AC: #1)
  - [x] Add `subscribeToContracts(contractIds: ContractId[]): void` to `platform-connector.interface.ts`
  - [x] Add `unsubscribeFromContracts(contractIds: ContractId[]): void` to `platform-connector.interface.ts`
  - [x] Compiler-driven migration: let TypeScript errors identify all implementors that need updating (Team Agreement #7)

- [x] **Task 4: Implement on KalshiConnector** (AC: #2)
  - [x] `subscribeToContracts(contractIds)` → calls `wsClient.addMarkets(contractIds.map(id => id as string))` (Kalshi uses market_ticker = contractId)
  - [x] `unsubscribeFromContracts(contractIds)` → calls `wsClient.removeMarkets(contractIds.map(id => id as string))`
  - [x] If `wsClient.subscriptionId` is null (no existing orderbook_delta subscription), fall back to creating a new subscription via `subscribe()` for the first ticker, then `addMarkets()` for the rest. Guard with a `pendingSubscription` flag to prevent concurrent `subscribe()` calls during connection establishment.
  - [x] Subscription failures (WS disconnected, invalid ticker) should log at `error` level but NOT throw — subscription is best-effort and will be retried on next reconnect via `debouncedResubscribe()`
  - [x] Tests: verify connector delegates to WS client methods correctly; verify concurrent calls with null SID don't create duplicate subscriptions

- [x] **Task 5: Implement on PolymarketConnector** (AC: #3)
  - [x] `subscribeToContracts(contractIds)` → calls `wsClient.subscribe(tokenId)` for each contractId (Polymarket uses per-asset dynamic subscription)
  - [x] `unsubscribeFromContracts(contractIds)` → calls `wsClient.unsubscribe(tokenId)` for each contractId
  - [x] Tests: verify connector delegates to WS client methods correctly

- [x] **Task 6: Implement on PaperTradingConnector** (AC: #4)
  - [x] `subscribeToContracts(contractIds)` → `this.realConnector.subscribeToContracts(contractIds)`
  - [x] `unsubscribeFromContracts(contractIds)` → `this.realConnector.unsubscribeFromContracts(contractIds)`
  - [x] Tests: verify delegation to real connector

### Phase 3: Subscription Lifecycle Management

- [x] **Task 7: Add subscription management to DataIngestionService** (AC: #6, #7, #8)
  - [x]Add `activeSubscriptions: Map<string, { kalshiContractId: ContractId, polymarketContractId: ContractId }>` (keyed by PairId string)
  - [x]Add `contractRefCounts: Map<string, number>` (keyed by `${platformId}:${contractId}`) for ref-counting shared contracts
  - [x]Implement `subscribeForPosition(pairId: PairId, kalshiContractId: ContractId, polymarketContractId: ContractId): void`
    - Increment ref counts; if ref count goes from 0→1, call `connector.subscribeToContracts([contractId])`
    - Store in `activeSubscriptions`
  - [x]Implement `unsubscribeForPosition(pairId: PairId): void`
    - Decrement ref counts; if ref count goes from 1→0, call `connector.unsubscribeFromContracts([contractId])`
    - Remove from `activeSubscriptions`
    - Call `divergenceService.clearContractData(platformId, contractId)` to prevent memory leaks in divergence Maps
  - [x]Implement `getActiveSubscriptionCount(platformId: PlatformId): number` — counts entries in `activeSubscriptions` where the platform matches, for dashboard health DTO
  - [x]Tests: verify subscribe called on first position for a contract; verify unsubscribe NOT called while other positions reference same contract; verify unsubscribe called when last position for a contract closes; verify divergence data cleared on unsubscribe

- [x] **Task 8: Startup subscription rehydration** (AC: #6)
  - [x]In `DataIngestionService.onModuleInit()`, after registering WS callbacks, query `positionRepository.findByStatus(['OPEN', 'SINGLE_LEG_EXPOSED', 'EXIT_PARTIAL'])` (all active positions)
  - [x]For each active position with its pair, call `subscribeForPosition(pairId, kalshiContractId, polymarketClobTokenId)`
  - [x]Log startup subscription count: `"Rehydrated N WS subscriptions for M active positions"`
  - [x]Tests: verify rehydration queries active positions on startup; verify subscriptions established for each (internal subsystem verification per Team Agreement #19)

- [x] **Task 9: Event-driven subscription lifecycle** (AC: #7, #8)
  - [x]Subscribe to `EVENT_NAMES.ORDER_FILLED` — when a new position is fully opened (both legs filled), call `subscribeForPosition()`
  - [x]Subscribe to `EVENT_NAMES.EXIT_TRIGGERED` — when position exits, call `unsubscribeForPosition()`
  - [x]Subscribe to `EVENT_NAMES.SINGLE_LEG_RESOLVED` — when single-leg resolved to CLOSED, call `unsubscribeForPosition()`
  - [x]Guard: check position status transition to avoid double-subscribe/unsubscribe
  - [x]Tests: verify ORDER_FILLED triggers subscribe; verify EXIT_TRIGGERED triggers unsubscribe; verify idempotent for duplicate events

### Phase 4: Divergence Detection

- [x] **Task 10: Create `DataDivergenceService`** (AC: #9, #10)
  - [x]New file: `src/modules/data-ingestion/data-divergence.service.ts`
  - [x]Inject: `PlatformHealthService`, `EventEmitter2`, `ConfigService`
  - [x]Maintain `lastPollSnapshot: Map<string, { bestBid: Decimal, bestAsk: Decimal, timestamp: Date }>` (keyed by `${platformId}:${contractId}`)
  - [x]Maintain `lastWsSnapshot: Map<string, { bestBid: Decimal, bestAsk: Decimal, timestamp: Date }>` (same key)
  - [x]`recordPollData(platformId, contractId, book: NormalizedOrderBook): void` — called by `DataIngestionService.ingestCurrentOrderBooks()` after processing each poll result
  - [x]`recordWsData(platformId, contractId, book: NormalizedOrderBook): void` — called by `DataIngestionService.processWebSocketUpdate()`
  - [x]`checkDivergence(platformId, contractId): void` — called after each record operation:
    - Use `NormalizedOrderBook.timestamp` for both sources (set at message receipt time for WS, at polling time for polls — consistent with existing staleness detection in 9-1b)
    - Compute price delta: `|pollBestBid - wsBestBid|` and `|pollBestAsk - wsBestAsk|`
    - Compute staleness delta: `|pollTimestamp - wsTimestamp|` in milliseconds
    - If price delta > configurable threshold (env: `DIVERGENCE_PRICE_THRESHOLD`, default: `0.02`) OR staleness delta > configurable threshold (env: `DIVERGENCE_STALENESS_THRESHOLD_MS`, default: `90000`): emit `platform.data.divergence` event
    - Only emit if state transitions from normal→divergent (exactly-once per divergence onset, following pattern from 9-1b staleness detection)
    - **Recovery:** divergent→normal transition requires BOTH price delta AND staleness delta to return below thresholds. Recovery also emits once (log level, no event) to clear dashboard status.
  - [x]`clearContractData(platformId, contractId): void` — removes entries from both snapshot Maps. Called by `DataIngestionService.unsubscribeForPosition()` to prevent unbounded Map growth.
  - [x]`getDivergenceStatus(platformId: PlatformId): 'normal' | 'divergent'` — returns `'divergent'` if ANY contract on that platform is currently in divergent state, `'normal'` otherwise. Used by dashboard health DTO.
  - [x]**Read-only constraint:** This service compares and emits. It does NOT modify poll or WS data. It does NOT arbitrate which path is "correct." Consumers (trading cycle, exit monitor) select their authoritative path independently.
  - [x]Tests: verify price divergence triggers event; verify staleness divergence triggers event; verify no event when below threshold; verify exactly-once emission (no repeated events for sustained divergence); verify recovery requires BOTH deltas below threshold; verify clearContractData removes Map entries

- [x] **Task 11: Add `platform.data.divergence` event to catalog and create event class** (AC: #9, #12)
  - [x]Add `DATA_DIVERGENCE: 'platform.data.divergence'` to `EVENT_NAMES` in `event-catalog.ts`
  - [x]Create `DataDivergenceEvent` class in `common/events/platform.events.ts` extending `BaseEvent`:
    - `platformId: PlatformId`
    - `contractId: ContractId`
    - `pollBestBid: string`, `pollBestAsk: string`, `pollTimestamp: string`
    - `wsBestBid: string`, `wsBestAsk: string`, `wsTimestamp: string`
    - `priceDelta: string`, `stalenessDeltaMs: number`

- [x] **Task 12: Wire divergence recording into DataIngestionService** (AC: #9)
  - [x]In `ingestCurrentOrderBooks()`, after each successful poll + normalization, call `divergenceService.recordPollData(platformId, contractId, book)`
  - [x]In `processWebSocketUpdate()`, after persist + emit, call `divergenceService.recordWsData(platformId, contractId, book)`
  - [x]Tests: verify poll path calls `recordPollData`; verify WS path calls `recordWsData`

### Phase 5: WS Message Timestamp Tracking

- [x] **Task 13: Track last WS message timestamp per platform** (AC: #11)
  - [x]Add `lastWsMessageTimestamp: Map<PlatformId, Date>` to `PlatformHealthService`
  - [x]Expose `getWsLastMessageTimestamp(platformId): Date | null`
  - [x]Update `recordContractUpdate()` (already called for WS updates) to also update `lastWsMessageTimestamp` when the source is WS — add optional `source?: 'poll' | 'ws'` parameter (default: `'poll'` for backward compatibility)
  - [x]Update `processWebSocketUpdate()` call to pass `source: 'ws'`
  - [x]Tests: verify WS updates set timestamp; verify poll updates do NOT set timestamp

### Phase 6: Dashboard Vertical Slice

- [x] **Task 14: Extend `PlatformHealthDto` with WS fields** (AC: #11)
  - [x]Add `wsSubscriptionCount: number` — from `DataIngestionService.getActiveSubscriptionCount(platformId)`
  - [x]Add `divergenceStatus: 'normal' | 'divergent'` — from `DataDivergenceService.getDivergenceStatus(platformId)` (returns `'divergent'` if ANY contract on that platform is divergent)
  - [x]Add `wsLastMessageTimestamp: string | null` — ISO timestamp from `PlatformHealthService.getWsLastMessageTimestamp()`
  - [x]Update `DashboardService.getHealth()` to populate new fields
  - [x]Add `@ApiProperty` decorators with descriptions
  - [x]Tests: verify DTO populated correctly from service data

- [x] **Task 15: Map divergence event to dashboard WS push** (AC: #12)
  - [x]Add handler in `DashboardEventMapperService` for `EVENT_NAMES.DATA_DIVERGENCE`
  - [x]Map to a `divergence_alert` WS event payload with platform, contract, price delta, staleness delta
  - [x]Wire into `DashboardGateway` for real-time push
  - [x]Tests: verify event mapping produces correct WS payload

- [x] **Task 16: Wire Telegram alert for divergence** (AC: #12)
  - [x]Add `EVENT_NAMES.DATA_DIVERGENCE` to `EventConsumerService` subscription list
  - [x]Add formatter in `TelegramAlertService` for divergence alerts (platform, contract, deltas)
  - [x]Tests: verify event consumer forwards to Telegram; verify alert message format

### Phase 7: Data Path Contract Documentation

- [x] **Task 17: Document data path contract** (AC: #10)
  - [x]Add JSDoc on `DataIngestionService.ingestCurrentOrderBooks()`: `/** Polling path — authoritative for ENTRY decisions (detection pipeline). */`
  - [x]Add JSDoc on `DataIngestionService.processWebSocketUpdate()`: `/** WebSocket path — authoritative for EXIT decisions (exit monitor). */`
  - [x]Add block comment at top of `data-ingestion.service.ts` explaining the dual data path architecture and which consumers use which path
  - [x]No code behavior changes in this task — documentation only

## Dev Notes

### Architecture Context

This story bridges the gap identified in story 9-20: WebSocket connections exist but no tickers are subscribed. It establishes the subscription mechanism and divergence detection required by the dual data path architecture decided in the Epic 9 retro. [Source: epic-9-retro-2026-03-15.md#Action-Items, item #6]

**Dual data path architecture (decided in Epic 9 retro):**
- **Polling path** → entry decisions (detection pipeline). Remains unchanged. `TradingEngineService` calls `DataIngestionService.ingestCurrentOrderBooks()` each cycle.
- **WebSocket path** → exit decisions (exit monitor). Story 10.1 will make exit monitor consume WS data. This story establishes the subscriptions that make WS data flow.
- **Divergence monitoring** → observational only. Does NOT decide which path is "correct." [Source: epic-9-retro-2026-03-15.md#Architecture-Decision]

### Protocol Correctness Fixes (Why WS Client Code Changes)

Both WS clients have protocol issues that prevent subscriptions from working correctly. These are prerequisite fixes, not scope creep:

**Kalshi:**
- Current `unsubscribe()` sends `{ cmd: 'unsubscribe', params: { channels: ['orderbook_delta'], market_ticker: ticker } }` — Kalshi docs require `sids` for unsubscribe, or `update_subscription` with `action: "delete_markets"`. [Source: docs.kalshi.com/websockets/websocket-connection]
- Kalshi supports `update_subscription` with `action: "add_markets"` / `action: "delete_markets"` for dynamically managing markets on an existing subscription — more efficient than per-ticker subscribe/unsubscribe.
- Must track `sid` from `subscribed` response: `{ type: "subscribed", msg: { channel: "orderbook_delta", sid: 1 } }`

**Polymarket:**
- Current `sendSubscribe()` sends `{ auth: {}, type: 'subscribe', markets: [], assets_ids: [tokenId] }` — does not match Polymarket docs. Dynamic subscription format is `{ assets_ids: [...], operation: "subscribe" }`. [Source: docs.polymarket.com/trading/orderbook#dynamic-subscribe-and-unsubscribe]
- Current `unsubscribe()` only cleans up local state — never sends a WS message. Should send `{ assets_ids: [...], operation: "unsubscribe" }`.
- Initial subscription (on connect) uses different format: `{ type: "market", assets_ids: [...], custom_feature_enabled: true }`. Dynamic subscribe (after connected) uses `{ assets_ids: [...], operation: "subscribe" }`.

**Connector subscription semantics are asymmetric:** Kalshi uses batch `update_subscription` (one subscription, many markets). Polymarket uses per-asset dynamic subscribe/unsubscribe. The `IPlatformConnector.subscribeToContracts()` method abstracts this — callers pass `ContractId[]` and connectors handle platform-specific batching internally.

### Subscription Lifecycle

```
Startup:
  DataIngestionService.onModuleInit()
    → query active positions (OPEN, SINGLE_LEG_EXPOSED, EXIT_PARTIAL)
    → subscribeForPosition() for each
    → log "Rehydrated N subscriptions"

Runtime:
  ORDER_FILLED event → subscribeForPosition(pairId, kalshiContractId, polymarketContractId)
  EXIT_TRIGGERED / SINGLE_LEG_RESOLVED(→CLOSED) → unsubscribeForPosition(pairId)

Contract ref-counting:
  Multiple positions can share the same contract (same pair, different time periods).
  Only call connector.subscribeToContracts when refCount goes 0→1.
  Only call connector.unsubscribeFromContracts when refCount goes 1→0.
```

### Module Boundaries

- `DataIngestionService` owns all connector WS interactions (subscribe/unsubscribe) — exit monitor does NOT import from connectors.
- `DataDivergenceService` lives in `data-ingestion/` module — colocated with both data paths.
- Events cross module boundaries: `DataDivergenceEvent` emitted from data-ingestion, consumed by monitoring (Telegram), dashboard (WS push).
- `IPlatformConnector` interface change in `common/interfaces/` — available to all modules.

### Existing Code to Reuse

| What | Where | How |
|------|-------|-----|
| `NormalizedOrderBook` | `common/types/normalized-order-book.type.ts` | WS callbacks already receive this type |
| `ContractId` branded type | `common/types/branded.type.ts` | Use for all contract ID parameters |
| `PairId` branded type | `common/types/branded.type.ts` | Use for subscription map keys |
| `BaseEvent` | `common/events/base.event.ts` | Extend for `DataDivergenceEvent` |
| `EVENT_NAMES` | `common/events/event-catalog.ts` | Add `DATA_DIVERGENCE` entry |
| `PlatformHealthService.recordContractUpdate()` | `data-ingestion/platform-health.service.ts` | Add `source` param for WS timestamp tracking |
| `DashboardEventMapperService` | `dashboard/dashboard-event-mapper.service.ts` | Add divergence event mapping |
| `EventConsumerService` | `monitoring/event-consumer.service.ts` | Add divergence event subscription |
| `PositionRepository.findByStatus()` | `persistence/repositories/position.repository.ts` | Startup rehydration query |
| Exactly-once emission pattern | `platform-health.service.ts` (staleness detection, 9-1b) | Follow same pattern for divergence state transitions |

### Configuration

New environment variables (add to `.env.example` and validate in config):
- `DIVERGENCE_PRICE_THRESHOLD=0.02` — price delta threshold for divergence (decimal, 0.02 = 2%)
- `DIVERGENCE_STALENESS_THRESHOLD_MS=90000` — staleness delta threshold for divergence (ms)

Follow existing config validation pattern: read via `ConfigService.get<number>()` with fallback defaults. No Zod schema needed for these — they're simple numeric thresholds with sensible defaults, consistent with how `ORDERBOOK_STALENESS_THRESHOLD_S` is handled in `PlatformHealthService`. [Source: platform-health.service.ts:41 — orderbookStalenessThreshold config pattern]

### Alert Severity

Divergence alerts should use `warning` severity (not `error`) in Telegram — divergence is observational, not actionable failure. The operator should be aware, but this is not a trading halt condition. [Source: CLAUDE.md — severity routing: Warning → dashboard update + log]

### Testing Strategy

- **Co-located spec files** per project convention
- **Internal subsystem verification (Team Agreement #19):** Tests must assert WS `.send()` is called with correct JSON payloads, not just that handlers process mock data
- **Paper/live boundary (Team Agreement #20):** Paper connector delegation tests for new methods
- **Dual-path tests:** Verify both poll and WS paths feed into divergence service independently
- **Startup rehydration test:** Mock `positionRepository.findByStatus()` returning active positions, verify subscriptions established
- **Ref-counting tests:** Multiple positions sharing same contract → single subscription; last close → unsubscribe

### Project Structure Notes

New files:
- `src/modules/data-ingestion/data-divergence.service.ts`
- `src/modules/data-ingestion/data-divergence.service.spec.ts`

Modified files:
- `src/common/interfaces/platform-connector.interface.ts` — 2 new methods
- `src/connectors/kalshi/kalshi-websocket.client.ts` — sid tracking, addMarkets/removeMarkets, fix unsubscribe
- `src/connectors/kalshi/kalshi-websocket.client.spec.ts` — new tests
- `src/connectors/kalshi/kalshi.connector.ts` — implement subscribeToContracts/unsubscribeFromContracts
- `src/connectors/kalshi/kalshi.connector.spec.ts` — new tests
- `src/connectors/polymarket/polymarket-websocket.client.ts` — fix sendSubscribe, fix unsubscribe, add sendInitialSubscription
- `src/connectors/polymarket/polymarket-websocket.client.spec.ts` — new tests
- `src/connectors/polymarket/polymarket.connector.ts` — implement subscribeToContracts/unsubscribeFromContracts
- `src/connectors/polymarket/polymarket.connector.spec.ts` — new tests
- `src/connectors/paper/paper-trading.connector.ts` — delegate new methods
- `src/connectors/paper/paper-trading.connector.spec.ts` — new tests
- `src/modules/data-ingestion/data-ingestion.module.ts` — provide DataDivergenceService
- `src/modules/data-ingestion/data-ingestion.service.ts` — subscription lifecycle, divergence recording, startup rehydration
- `src/modules/data-ingestion/data-ingestion.service.spec.ts` — new tests
- `src/modules/data-ingestion/platform-health.service.ts` — wsLastMessageTimestamp, source param
- `src/modules/data-ingestion/platform-health.service.spec.ts` — new tests
- `src/common/events/event-catalog.ts` — add DATA_DIVERGENCE
- `src/common/events/platform.events.ts` — add DataDivergenceEvent
- `src/dashboard/dto/platform-health.dto.ts` — 3 new fields
- `src/dashboard/dashboard.service.ts` — populate new health fields
- `src/dashboard/dashboard.service.spec.ts` — new tests
- `src/dashboard/dashboard-event-mapper.service.ts` — divergence event mapping
- `src/dashboard/dashboard-event-mapper.service.spec.ts` — new tests
- `src/modules/monitoring/event-consumer.service.ts` — subscribe to divergence event
- `src/modules/monitoring/telegram-alert.service.ts` — format divergence alert
- `.env.example` — 2 new variables

### References

- [Source: epics.md#Story-10-0-1] — Story definition, acceptance criteria
- [Source: epic-9-retro-2026-03-15.md#Action-Items, item #6] — WebSocket subscription establishment scope
- [Source: epic-9-retro-2026-03-15.md#Architecture-Decision] — Dual data path, retrofit approach
- [Source: epic-9-retro-2026-03-15.md#Team-Agreements, #18] — Vertical slice minimum
- [Source: epic-9-retro-2026-03-15.md#Team-Agreements, #19] — Internal subsystem verification
- [Source: epic-9-retro-2026-03-15.md#Team-Agreements, #20] — Paper/live boundary first-class
- [Source: epic-9-retro-2026-03-15.md#Team-Agreements, #23] — Two-data-path divergence monitoring
- [Source: docs.kalshi.com/websockets/websocket-connection] — Kalshi WS subscribe/unsubscribe/update_subscription format
- [Source: docs.kalshi.com/websockets/orderbook-updates] — Kalshi orderbook_delta snapshot/delta format
- [Source: docs.polymarket.com/trading/orderbook] — Polymarket WS dynamic subscribe/unsubscribe format
- [Source: docs.polymarket.com/market-data/websocket/overview] — Polymarket WS channels and heartbeat
- [Source: platform-connector.interface.ts:20-53] — Current IPlatformConnector (11 methods)
- [Source: kalshi-websocket.client.ts:159-205] — Current Kalshi subscribe/unsubscribe/sendSubscribe
- [Source: polymarket-websocket.client.ts:144-174] — Current Polymarket subscribe/unsubscribe/sendSubscribe
- [Source: data-ingestion.service.ts:61-129] — Current onModuleInit (registers callbacks, no subscriptions)
- [Source: data-ingestion.service.ts:346-396] — Current processWebSocketUpdate
- [Source: exit-monitor.service.ts:966-988] — Current getClosePrice (polling-based)
- [Source: paper-trading.connector.ts:33-47] — Paper connector delegation pattern
- [Source: platform-health.service.ts:419-428] — recordContractUpdate (add source param)

### Pre-Existing Test Failures

21 tests failing in `candidate-discovery.service.spec.ts` before this story. Not related to this work. Baseline: 2098 passing / 2121 total.

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- Pre-existing test failures: 21 tests in `candidate-discovery.service.spec.ts` (documented in story, unrelated)
- Baseline: 2098 passing tests → Final: 2141 passing tests (+43 new tests)
- Post-review: 2141 → 2175 passing tests (+34 review-fix tests)

### Completion Notes List
- **Phase 1 (Tasks 1-2):** Fixed Kalshi WS client to track subscription ID from `subscribed` responses, use `update_subscription` with `sids` for add/remove markets. Fixed Polymarket WS client to use correct dynamic subscribe/unsubscribe format (`operation: "subscribe"/"unsubscribe"`) and initial format (`type: "market"`). 13 new tests with internal subsystem verification (assert WS `.send()` called with correct payloads).
- **Phase 2 (Tasks 3-6):** Extended `IPlatformConnector` with `subscribeToContracts`/`unsubscribeFromContracts`. Compiler-driven migration updated all 3 implementors (Kalshi, Polymarket, Paper) and mock factories. KalshiConnector uses `addMarkets`/individual `subscribe` fallback when no SID. PolymarketConnector iterates per-asset. PaperTradingConnector delegates to real connector.
- **Phase 3 (Tasks 7-9):** Added ref-counted subscription lifecycle to DataIngestionService with `activeSubscriptions` Map and `contractRefCounts` Map. Startup rehydration queries active positions via `PositionRepository.findByStatusWithPair()`. Event-driven lifecycle uses `@OnEvent` decorators for ORDER_FILLED (subscribe when OPEN), EXIT_TRIGGERED (unsubscribe), SINGLE_LEG_RESOLVED/closed (unsubscribe).
- **Phase 4 (Tasks 10-12):** Created `DataDivergenceService` with exactly-once divergent/normal state transitions following existing staleness detection pattern. Configurable thresholds via `DIVERGENCE_PRICE_THRESHOLD` and `DIVERGENCE_STALENESS_THRESHOLD_MS`. Wired `recordPollData`/`recordWsData` into polling and WS paths. `clearContractData` called on unsubscribe to prevent memory leaks.
- **Phase 5 (Task 13):** Added `lastWsMessageTimestamp` Map to `PlatformHealthService` with `source` parameter on `recordContractUpdate()` (backward compatible default: `'poll'`).
- **Phase 6 (Tasks 14-16):** Extended `PlatformHealthDto` with `wsSubscriptionCount`, `divergenceStatus`, `wsLastMessageTimestamp`. Updated `DashboardService.getHealth()`. Added `DIVERGENCE_ALERT` WS event type and `mapDivergenceAlert` in event mapper. Added `DATA_DIVERGENCE` to warning severity and FORMATTED_EVENTS in Telegram alert service.
- **Phase 7 (Task 17):** Added JSDoc on both data paths and block comment documenting dual data path architecture at top of `data-ingestion.service.ts`.

### Code Review #1 (2026-03-15)
Fixed 5 CRITICAL, 8 HIGH, 8 MEDIUM issues:
- **C1:** Added missing `@OnEvent(DATA_DIVERGENCE)` handler in `DashboardGateway` — `mapDivergenceAlert()` was dead code
- **C2:** Added 3 tests verifying divergence recording wiring (`recordPollData`/`recordWsData` assertions)
- **C3:** Fixed false divergence alerts from empty order book sides — changed `&&` to `||` guard, removed `?? 0` defaults
- **C4:** Fixed paper position rehydration — startup now queries both live and paper positions
- **C5:** Added `pendingSubscription` guard to `KalshiWebSocketClient` and `KalshiConnector.subscribeToContracts`
- **H1:** Reset `_subscriptionId` and `_pendingSubscription` on `disconnect()` to prevent stale SID after reconnect
- **H2:** Updated `KalshiSubscribeCommand` type to `cmd: 'subscribe'` only, added `KalshiUpdateSubscriptionCommand` for `update_subscription`
- **H3:** Replaced unsafe `as unknown as PairId`/`as unknown as string` double-casts with proper `asPairId()`/`unwrapId()` utilities
- **H4:** Added test verifying 3 new health DTO fields (`wsSubscriptionCount`, `divergenceStatus`, `wsLastMessageTimestamp`)
- **H5:** Added test for `mapDivergenceAlert()` WS envelope mapping
- **H6:** Added test for DATA_DIVERGENCE Telegram formatter dispatch
- **H7:** Added 2 tests for `clearContractData` on unsubscribe (last-position cleanup, shared-contract ref-counting)
- **H8:** Replaced shallow "not throw" connector tests with proper delegation assertions (verify `addMarkets`/`subscribe`/`unsubscribe` called with correct args)
- **M1:** Made `sendInitialSubscription` private on `PolymarketWebSocketClient`
- **M2:** Reset `hasInitialSubscription` on `disconnect()` in `PolymarketWebSocketClient`
- **M3:** Changed `priceThreshold` from `number` to `Decimal` per financial math rules
- **M4:** Replaced inline Telegram formatter with named `formatDataDivergence()` function using HTML escaping + emoji
- **M5:** Removed dead `subscribeToTicker` method from `KalshiConnector`
- **M7:** Added test verifying recovery log emission on divergence resolution
- **M8:** Added test verifying cross-platform divergence independence

### File List
New files:
- `src/modules/data-ingestion/data-divergence.service.ts`
- `src/modules/data-ingestion/data-divergence.service.spec.ts`

Modified files:
- `src/common/interfaces/platform-connector.interface.ts`
- `src/common/events/event-catalog.ts`
- `src/common/events/platform.events.ts`
- `src/connectors/kalshi/kalshi-websocket.client.ts`
- `src/connectors/kalshi/kalshi-websocket.client.spec.ts`
- `src/connectors/kalshi/kalshi.connector.ts`
- `src/connectors/kalshi/kalshi.connector.spec.ts`
- `src/connectors/polymarket/polymarket-websocket.client.ts`
- `src/connectors/polymarket/polymarket-websocket.client.spec.ts`
- `src/connectors/polymarket/polymarket.connector.ts`
- `src/connectors/polymarket/polymarket.connector.spec.ts`
- `src/connectors/paper/paper-trading.connector.ts`
- `src/connectors/paper/paper-trading.connector.spec.ts`
- `src/modules/data-ingestion/data-ingestion.module.ts`
- `src/modules/data-ingestion/data-ingestion.service.ts`
- `src/modules/data-ingestion/data-ingestion.service.spec.ts`
- `src/modules/data-ingestion/platform-health.service.ts`
- `src/modules/monitoring/event-severity.ts`
- `src/modules/monitoring/telegram-alert.service.ts`
- `src/modules/monitoring/telegram-alert.service.spec.ts`
- `src/dashboard/dto/platform-health.dto.ts`
- `src/dashboard/dto/ws-events.dto.ts`
- `src/dashboard/dashboard.service.ts`
- `src/dashboard/dashboard.service.spec.ts`
- `src/dashboard/dashboard-event-mapper.service.ts`
- `src/test/mock-factories.ts`
- `src/modules/data-ingestion/price-feed.service.spec.ts`
- `src/connectors/kalshi/kalshi.types.ts`
- `src/dashboard/dashboard.gateway.ts`
- `src/modules/monitoring/formatters/telegram-message.formatter.ts`
- `.env.example`
