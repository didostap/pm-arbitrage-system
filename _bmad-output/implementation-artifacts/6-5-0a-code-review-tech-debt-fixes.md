# Story 6.5.0a: Code Review Tech Debt Fixes

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want the pre-existing tech debt items surfaced by the Story 6.5.0 code review to be resolved before paper trading validation begins,
So that the validation run produces trustworthy results on a codebase with no known observability gaps or architecture violations.

## Acceptance Criteria

1. **Given** the `verifyDepth()` method in `execution.service.ts` has a catch block that silently returns `false`
   **When** an API failure, rate limit, or transient error occurs during depth verification
   **Then** a structured warning log is emitted with the error context (platform, market, error type)
   **And** a `execution.depth-check.failed` event is emitted for monitoring consumption
   **And** the method still returns `false` (fail-closed behavior preserved)

2. **Given** the `handlePriceChange()` method in `polymarket-websocket.client.ts` may not update order book price levels
   **When** the method's behavior is investigated against Polymarket's WebSocket message types
   **Then** either: (a) confirmed dead code path — documented with rationale and no fix needed, **or** (b) confirmed bug — price levels are updated from `price_change` messages and covered by tests
   **And** investigation findings are documented in `gotchas.md`

3. **Given** `kalshi.connector.ts` has `getPositions()` throwing raw `new Error('getPositions not implemented')`
   **When** this placeholder is reviewed
   **Then** it is replaced with `throw new PlatformApiError(...)` using the SystemError hierarchy with appropriate error code
   **And** the method signature and JSDoc remain unchanged

4. **Given** the `polymarket-websocket.client.ts` staleness check detects data older than 30 seconds
   **When** stale data is detected and the emit is skipped
   **Then** a `platform.health.data-stale` event is emitted with platform identifier and staleness duration
   **And** the event is consumable by the monitoring hub for Telegram alerting

## Tasks / Subtasks

- [x]Task 1: Add structured logging + event emission to `verifyDepth()` catch block (AC: #1)
  - [x]1.1 Create `DepthCheckFailedEvent` class in `src/common/events/execution.events.ts`:
    - Extend `BaseEvent`
    - Fields: `platform: PlatformId`, `contractId: string`, `side: 'buy' | 'sell'`, `errorType: string`, `errorMessage: string`
    - Follow existing pattern (see `ExecutionFailedEvent` in same file)
  - [x]1.2 Add `DEPTH_CHECK_FAILED: 'execution.depth-check.failed'` to `EVENT_NAMES` in `src/common/events/event-catalog.ts` (after `EXECUTION_FAILED` in the Epic 5 section)
  - [x]1.3 Modify `ExecutionService.verifyDepth()` in `src/modules/execution/execution.service.ts` (lines 472-499):
    - The method needs `platformId` — callers already have it: `primaryPlatform` and `secondaryPlatform` from `resolveConnectors()` (line 78-79). Add `platformId: PlatformId` as the first parameter and update both call sites (line 160 → pass `primaryPlatform`, line 253 → pass `secondaryPlatform`)
    - In the catch block (line 495), replace the empty catch with:
      ```typescript
      catch (error) {
        this.logger.warn({
          message: 'Depth verification failed',
          module: 'execution',
          platform: platformId,
          contractId,
          side,
          errorType: error instanceof Error ? error.constructor.name : 'Unknown',
          errorMessage: error instanceof Error ? error.message : String(error),
        });
        this.eventEmitter.emit(
          EVENT_NAMES.DEPTH_CHECK_FAILED,
          new DepthCheckFailedEvent(platformId, contractId, side,
            error instanceof Error ? error.constructor.name : 'Unknown',
            error instanceof Error ? error.message : String(error)),
        );
        return false;
      }
      ```
    - Ensure `EventEmitter2` is already injected in `ExecutionService` constructor (it should be — check)
  - [x]1.4 Add unit tests in `src/modules/execution/execution.service.spec.ts`:
    - Test: when `connector.getOrderBook()` throws, `verifyDepth()` returns `false`
    - Test: when `connector.getOrderBook()` throws, a warning log is emitted
    - Test: when `connector.getOrderBook()` throws, `DepthCheckFailedEvent` is emitted via `eventEmitter.emit`
    - Mock `connector.getOrderBook` to throw `PlatformApiError` (rate limit scenario)
  - [x]1.5 Run `pnpm test` and `pnpm lint` — verify zero regressions

- [x]Task 2: Investigate and resolve `handlePriceChange()` behavior (AC: #2)
  - [x]2.1 Research Polymarket WebSocket API documentation to understand `price_change` message type:
    - Use `kindly-web-search` to find Polymarket CLOB API WebSocket documentation
    - Determine: does Polymarket's WebSocket actually send `price_change` messages? What fields do they contain?
    - Check if the current handler signature `PolymarketPriceChangeMessage` matches the real API schema
  - [x]2.2 Analyze current `handlePriceChange()` implementation (lines 200-210):
    ```typescript
    private handlePriceChange(msg: PolymarketPriceChangeMessage): void {
      const state = this.orderbookState.get(msg.asset_id);
      if (!state) return;
      const price = parseFloat(msg.price);
      if (!isNaN(price)) {
        state.timestamp = msg.timestamp ?? Date.now();
        this.emitUpdate(msg.asset_id, state);
      }
    }
    ```

    - The method updates `state.timestamp` and calls `emitUpdate()` but does NOT update `state.bids` or `state.asks`
    - This means it re-emits the same order book data with a new timestamp — stale levels with fresh timestamp
    - Determine if this is: (a) dead code (Polymarket never sends `price_change`), or (b) a bug that should update the price levels
  - [x]2.3 Check the WebSocket message routing — find where `handlePriceChange` is called:
    - Search for `handlePriceChange` references to see the dispatch logic
    - Check the `PolymarketPriceChangeMessage` type definition
  - [x]2.4 Based on findings, take action:
    - **If dead code:** Add a code comment explaining it's unreachable per current Polymarket API, add a `gotchas.md` entry
    - **If bug:** Fix `handlePriceChange` to update the relevant bid/ask levels before calling `emitUpdate()`, add tests verifying levels are updated
  - [x]2.5 Document findings in `docs/gotchas.md` as a new entry
  - [x]2.6 Run `pnpm test` and `pnpm lint`

- [x]Task 3: Replace raw `Error` with `PlatformApiError` in `getPositions()` (AC: #3)
  - [x]3.1 Modify `KalshiConnector.getPositions()` in `src/connectors/kalshi/kalshi.connector.ts` (lines 202-204):
    - Current: `throw new Error('getPositions not implemented - Epic 5 Story 5.1');`
    - Replace with:
      ```typescript
      throw new PlatformApiError(
        1008,
        'getPositions not implemented — positions tracked via Prisma OpenPosition model',
        PlatformId.KALSHI,
        'warning',
        undefined,
        { reason: 'unimplemented', plannedEpic: 'Phase 1' },
      );
      ```
    - Error code `1008` — next available in PlatformApiError range (1001-1007 already used per the error class JSDoc)
    - Import `PlatformApiError` from `../../common/errors/platform-api-error` and `PlatformId` from `../../common/types/platform.type`
  - [x]3.2 Check if `PlatformId` is already imported in `kalshi.connector.ts` (likely yes — used elsewhere in the file)
  - [x]3.3 Update the existing test in `src/connectors/kalshi/kalshi.connector.spec.ts`:
    - Change expectation from `toThrow(Error)` to `toThrow(PlatformApiError)` (or add a new test if none exists)
    - Verify thrown error has code `1008` and severity `warning`
  - [x]3.4 Run `pnpm test` and `pnpm lint`

- [x]Task 4: Add `platform.health.data-stale` event emission to staleness check (AC: #4)
  - [x]4.1 Create `DataStaleEvent` class in `src/common/events/platform.events.ts`:
    - Extend `BaseEvent`
    - Fields: `platformId: PlatformId`, `tokenId: string`, `stalenessMs: number`
    - Place after `DegradationProtocolDeactivatedEvent` (follow file ordering)
  - [x]4.2 Add `DATA_STALE: 'platform.health.data-stale'` to `EVENT_NAMES` in `src/common/events/event-catalog.ts` (in the platform section, after `PLATFORM_HEALTH_DISCONNECTED`)
  - [x]4.3 Export `DataStaleEvent` — it's auto-exported via `src/common/events/index.ts` barrel (`export * from './platform.events'`)
  - [x]4.4 Modify `PolymarketWebSocketClient.emitUpdate()` in `src/connectors/polymarket/polymarket-websocket.client.ts` (lines 212-244):
    - The staleness check is at lines 213-222. After the `this.logger.error(...)` call and before `return`, emit the event:
      ```typescript
      this.eventEmitter.emit(EVENT_NAMES.DATA_STALE, new DataStaleEvent(PlatformId.POLYMARKET, tokenId, staleness));
      ```
    - **CRITICAL:** `PolymarketWebSocketClient` is NOT `@Injectable()` — it is manually instantiated at `polymarket.connector.ts:170` with `new PolymarketWebSocketClient({ wsUrl: this.wsUrl })`. You MUST:
      1. Add `eventEmitter: EventEmitter2` to `PolymarketWebSocketConfig` interface (or as a second constructor param)
      2. Update the `PolymarketConnector` instantiation site (line 170) to pass `this.eventEmitter` (PolymarketConnector IS `@Injectable()` and likely already has EventEmitter2 — verify its constructor)
      3. Store `eventEmitter` as a private field in `PolymarketWebSocketClient`
      4. Update the test file `polymarket-websocket.client.spec.ts` (line 17) — the `new PolymarketWebSocketClient({...})` call needs the eventEmitter mock
    - This is a connector using infrastructure (`@nestjs/event-emitter`) — NOT a module import. Architecture-compliant.
    - Import `DataStaleEvent` from `../../common/events`, `EVENT_NAMES` from `../../common/events/event-catalog`, `PlatformId` from `../../common/types/platform.type`
  - [x]4.5 Add unit tests in `src/connectors/polymarket/polymarket-websocket.client.spec.ts`:
    - Test: when order book data is >30s stale, `DataStaleEvent` is emitted with correct platform, tokenId, and staleness
    - Test: when order book data is fresh (<30s), no `DataStaleEvent` is emitted
    - Mock `EventEmitter2.emit` and verify call arguments
  - [x]4.6 Run `pnpm test` and `pnpm lint`

- [x]Task 5: Final validation (all ACs)
  - [x]5.1 Run `pnpm lint` — zero errors
  - [x]5.2 Run `pnpm test` — all tests pass (baseline 1,078 + new tests)
  - [x]5.3 Run `pnpm build` — clean compilation
  - [x]5.4 Verify no new `decimal.js` violations introduced (no native arithmetic on monetary fields)
  - [x]5.5 Record final test count and new test count

## Dev Notes

### Architecture Compliance

- **Module boundaries preserved:** All changes are within existing module boundaries. No new cross-module dependencies.
- **Connector event emission:** `PolymarketWebSocketClient` emitting events requires `EventEmitter2` injection. This is infrastructure (from `@nestjs/event-emitter`), NOT a module import — permitted by architecture rules. The connector still does NOT import from `modules/`.
- **Error hierarchy enforced:** Replacing `new Error(...)` with `PlatformApiError` aligns with the absolute rule: "NEVER throw raw `Error`."
- **Event naming follows dot-notation:** `execution.depth-check.failed` and `platform.health.data-stale` follow the established pattern.
- **Fan-out pattern:** New events are consumed by monitoring (async EventEmitter2) — never blocks execution path.

### Key Technical Decisions

1. **`verifyDepth()` platform identification:**
   - The method signature is `verifyDepth(connector, contractId, side, targetPrice, targetSize)` — no `platformId` parameter.
   - Both call sites (lines 160, 253) are in `execute()` which has `primaryPlatform` and `secondaryPlatform` from `resolveConnectors()` (line 78-79). Add `platformId: PlatformId` as the first parameter.
   - This is a private method — changing its signature has no external impact.
   - `EventEmitter2` is already injected in `ExecutionService` as `this.eventEmitter` (line 47).

2. **Error code 1008 for `getPositions`:**
   - PlatformApiError codes 1001-1007 are documented in the JSDoc. 1008 is the next available.
   - Severity `warning` (not `critical`) because this is a known unimplemented path, not a runtime failure.
   - No retry strategy — method is unimplemented, retrying won't help.

3. **`EventEmitter2` in `PolymarketWebSocketClient`:**
   - The WebSocket client is NOT `@Injectable()` — it is manually instantiated at `polymarket.connector.ts:170`:
     ```typescript
     this.wsClient = new PolymarketWebSocketClient({ wsUrl: this.wsUrl });
     ```
   - Constructor is `constructor(private readonly config: PolymarketWebSocketConfig) {}` (line 34).
   - `PolymarketConnector` IS `@Injectable()` (line 39) but does NOT currently inject `EventEmitter2`. Its constructor (lines 54-75) has: `ConfigService`, `OrderBookNormalizerService`, `GasEstimationService`. You must add `private readonly eventEmitter: EventEmitter2` to `PolymarketConnector`'s constructor, then pass it through to the WebSocket client.
   - Add `eventEmitter` to `PolymarketWebSocketConfig` interface or as a second constructor param. Update both the production instantiation (polymarket.connector.ts:170) and the test instantiation (polymarket-websocket.client.spec.ts:17).

4. **`handlePriceChange` investigation approach:**
   - Use `kindly-web-search` MCP to research Polymarket CLOB WebSocket API docs.
   - Key question: does Polymarket send `price_change` WebSocket messages? The primary data channel uses full book snapshots.
   - If dead code: document and leave. If bug: fix to update bid/ask levels from the message payload.

### Previous Story Intelligence (Story 6.5.0)

**From Story 6.5.0 completion notes:**

- Final baseline: 1,078 tests, 70 test files, lint clean, build clean
- All 13 decimal violation sites fixed with zero regressions
- Swagger setup complete at `/api/docs`
- 30-minute stability run clean — 0 errors, 0 fatal, 0 unhandled exceptions
- Code review found 8 findings total: 3 HIGH (all fixed), 3 MEDIUM (all fixed), 2 LOW (documented)

**From Story 6.5.0 code review (findings #4, #5, #8, #10 — the origin of this story):**

- **Finding #4:** Silent error swallowing in `verifyDepth` — empty catch with `return false`, no logging or metrics
- **Finding #5:** `handlePriceChange` may not update price levels — only updates timestamp then re-emits stale book
- **Finding #8:** Raw `Error` throw in `getPositions` — violates SystemError hierarchy
- **Finding #10:** No metrics/event for data staleness — staleness check logs error but doesn't emit event for monitoring

**Patterns from Story 6.5.0 to follow:**

- Decimal `.toString()` bridge: `new Decimal(value.toString())` for any new numeric→Decimal conversions
- Event class pattern: extend `BaseEvent`, fields as `public readonly`, optional `correlationId` last param
- Event catalog: add to `EVENT_NAMES` const object with JSDoc comment
- Test pattern: co-located `.spec.ts` in same directory, mock `EventEmitter2` with `vi.fn()`

### Git Intelligence

Recent engine commits:

```
6d0c1d5 feat: enhance codebase with TypeScript linting rules, add new dependencies for Fastify and Swagger integration
4101ec4 feat: add audit log functionality with tamper-evident hash chain
a639988 feat: implement compliance validation for trade gating
6587379 feat: implement CSV trade logging and daily summary generation
05e1744 feat: introduce SystemErrorFilter and EventConsumerService
```

Commit message pattern: `feat:` prefix, descriptive summary.

### Codebase Current State

| Metric       | Value |
| ------------ | ----- |
| Tests        | 1,078 |
| Test files   | 70    |
| Source files | ~125  |
| Lint errors  | 0     |
| Build        | Clean |

### Files to Modify

- `src/common/events/execution.events.ts` — add `DepthCheckFailedEvent` class
- `src/common/events/platform.events.ts` — add `DataStaleEvent` class
- `src/common/events/event-catalog.ts` — add `DEPTH_CHECK_FAILED` and `DATA_STALE` to `EVENT_NAMES`
- `src/modules/execution/execution.service.ts` — add logging + event emission to `verifyDepth()` catch block (lines 495-497)
- `src/connectors/polymarket/polymarket-websocket.client.ts` — add event emission to staleness check (line 222), investigate/fix `handlePriceChange` (lines 200-210), add `EventEmitter2` to constructor
- `src/connectors/polymarket/polymarket.connector.ts` — inject `EventEmitter2` (add to constructor, lines 54-75), pass to `PolymarketWebSocketClient` instantiation (line 170)
- `src/connectors/kalshi/kalshi.connector.ts` — replace raw `Error` with `PlatformApiError` in `getPositions()` (lines 202-204)
- `docs/gotchas.md` — add `handlePriceChange` investigation findings

### Files to Create

- None — all changes are modifications to existing files

### Tests to Add/Modify

- `src/modules/execution/execution.service.spec.ts` — add tests for `verifyDepth()` error handling
- `src/connectors/polymarket/polymarket-websocket.client.spec.ts` — add tests for staleness event emission
- `src/connectors/kalshi/kalshi.connector.spec.ts` — update `getPositions` test to expect `PlatformApiError`
- `src/connectors/polymarket/polymarket.connector.spec.ts` — update mock setup if constructor changes require new `EventEmitter2` mock

### Existing Infrastructure to Leverage

- **`EventEmitter2`** — already configured via `EventEmitterModule.forRoot()` in `AppModule`
- **`BaseEvent`** — abstract base class in `src/common/events/base.event.ts` with `timestamp` and `correlationId`
- **`EVENT_NAMES`** — centralized event name catalog in `src/common/events/event-catalog.ts`
- **`PlatformApiError`** — error class in `src/common/errors/platform-api-error.ts` (codes 1001-1007 used)
- **`PlatformId`** — enum in `src/common/types/platform.type.ts`
- **Structured logger** — NestJS `Logger` with pino adapter, JSON output

### References

- [Source: _bmad-output/implementation-artifacts/6-5-0-code-review-findings.md] — Origin findings #4, #5, #8, #10
- [Source: _bmad-output/implementation-artifacts/6-5-0-codebase-readiness-tech-debt-clearance.md] — Previous story context
- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.5.0a, lines 1392-1428] — Epic definition and ACs
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts, lines 472-499] — `verifyDepth()` method
- [Source: pm-arbitrage-engine/src/connectors/polymarket/polymarket-websocket.client.ts, lines 200-244] — `handlePriceChange()` and `emitUpdate()` methods
- [Source: pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts, lines 202-204] — `getPositions()` placeholder
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts] — EVENT_NAMES catalog (136 lines, 30+ events)
- [Source: pm-arbitrage-engine/src/common/events/execution.events.ts] — Existing execution events pattern
- [Source: pm-arbitrage-engine/src/common/events/platform.events.ts] — Existing platform events pattern
- [Source: pm-arbitrage-engine/src/common/errors/platform-api-error.ts] — PlatformApiError class (codes 1001-1007)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- LAD MCP code review executed post-implementation — 1 actionable finding resolved (eventEmitter made required, not optional)

### Completion Notes List

1. **AC #1 (verifyDepth):** Added `platformId: PlatformId` param to `verifyDepth()`, updated both call sites. Catch block now emits structured warning log + `DepthCheckFailedEvent` via `execution.depth-check.failed`. Fail-closed behavior preserved. 3 new tests.

2. **AC #2 (handlePriceChange):** **Bug confirmed.** Polymarket's real `price_change` message wraps entries in a `price_changes[]` array with `best_bid`/`best_ask` fields. Our original type had flat top-level fields, causing `msg.asset_id` to always be `undefined` — handler was silently dead. Fixed type (`PolymarketPriceChangeMessage`), handler now iterates array and updates top-of-book prices. Documented in `gotchas.md` entry #8. 4 updated/new tests.

3. **AC #3 (getPositions):** Replaced raw `Error` in both `KalshiConnector.getPositions()` (code 1100 via `KALSHI_ERROR_CODES.NOT_IMPLEMENTED`) and `PolymarketConnector.getPositions()` (code 1017, new `NOT_IMPLEMENTED` in error codes) with `PlatformApiError`. User approved fixing both connectors (story only specified Kalshi). 2 updated tests.

4. **AC #4 (staleness event):** Created `DataStaleEvent` class, added `DATA_STALE: 'platform.health.data-stale'` to event catalog. Threaded `EventEmitter2` from `PolymarketConnector` (new DI injection) → `PolymarketWebSocketConfig` → `PolymarketWebSocketClient`. Staleness check now emits event before discarding stale data. 2 new tests.

5. **LAD Review:** Ran post-implementation code review. One actionable finding: made `eventEmitter` required (not optional) in `PolymarketWebSocketConfig` since staleness events are critical monitoring signals. All other findings were pre-existing issues outside story scope.

6. **Code Review (Adversarial):** 3 issues fixed:
   - **HIGH:** Error code 1008 collision — Kalshi `getPositions` used `1008` which is Polymarket's `UNAUTHORIZED`. Fixed: added `KALSHI_ERROR_CODES.NOT_IMPLEMENTED: 1100`, updated connector + test.
   - **MEDIUM:** AC #1 structured warning log had no test. Fixed: added logger spy test verifying `warn()` payload.
   - **MEDIUM:** `handlePriceChange` created phantom `quantity: 0` levels when no book snapshot existed. Fixed: skip price_change if book is empty (no bids AND no asks).
   - 2 LOW items documented (metrics baseline discrepancy, Decimal import awareness) — no code changes needed.

### Metrics

| Metric        | Before                | After             |
| ------------- | --------------------- | ----------------- |
| Tests passing | 1,069 (5 e2e failing) | 1,086 (0 failing) |
| Test files    | 70                    | 70                |
| New tests     | —                     | +8                |
| Lint errors   | 0                     | 0                 |
| Build         | Clean                 | Clean             |

### File List

**Modified (16):**

- `src/common/events/execution.events.ts` — added `DepthCheckFailedEvent` class
- `src/common/events/platform.events.ts` — added `DataStaleEvent` class
- `src/common/events/event-catalog.ts` — added `DEPTH_CHECK_FAILED`, `DATA_STALE` to `EVENT_NAMES`
- `src/common/errors/platform-api-error.ts` — added `NOT_IMPLEMENTED: 1100` to `KALSHI_ERROR_CODES`, documented Polymarket range in JSDoc
- `src/modules/execution/execution.service.ts` — `verifyDepth()` logging + event + `platformId` param
- `src/modules/execution/execution.service.spec.ts` — 4 new depth-check tests (incl. logger warning verification)
- `src/connectors/polymarket/polymarket.types.ts` — fixed `PolymarketPriceChangeMessage` schema, added `PolymarketPriceChangeEntry`, made `eventEmitter` required in config
- `src/connectors/polymarket/polymarket-websocket.client.ts` — fixed `handlePriceChange()` (array iteration + empty-book guard), added `EventEmitter2` field + `DataStaleEvent` emission
- `src/connectors/polymarket/polymarket-websocket.client.spec.ts` — updated price_change tests (4), added staleness tests (2)
- `src/connectors/polymarket/polymarket.connector.ts` — injected `EventEmitter2`, passed to WS client, `getPositions()` → `PlatformApiError(1017)`
- `src/connectors/polymarket/polymarket.connector.spec.ts` — added `EventEmitter2` mock to both TestingModules, updated `getPositions` test
- `src/connectors/polymarket/polymarket-error-codes.ts` — added `NOT_IMPLEMENTED: 1017`
- `src/connectors/kalshi/kalshi.connector.ts` — `getPositions()` → `PlatformApiError(KALSHI_ERROR_CODES.NOT_IMPLEMENTED)` (code 1100)
- `src/connectors/kalshi/kalshi.connector.spec.ts` — updated `getPositions` test (code 1100)
- `docs/gotchas.md` — entry #8 (Polymarket WebSocket `price_change` schema bug)
