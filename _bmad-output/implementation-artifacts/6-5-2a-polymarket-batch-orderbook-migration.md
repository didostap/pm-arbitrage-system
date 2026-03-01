# Story 6.5.2a: Polymarket Batch Order Book Migration & Health Log Optimization

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want Polymarket order books fetched via a single batch API call instead of sequential per-pair requests,
so that rate limit consumption drops from O(n) to O(1), ingestion latency improves ~6x, and all order books share a consistent timestamp for accurate arbitrage detection.

## Acceptance Criteria

1. **Given** the Polymarket connector has multiple configured token IDs
   **When** `DataIngestionService.ingestCurrentOrderBooks()` runs a polling cycle
   **Then** all Polymarket order books are fetched via a single `clobClient.getOrderBooks(params: BookParams[])` call
   **And** only 1 rate limit read token is consumed per cycle (regardless of pair count)
   **And** each returned `OrderBookSummary` is normalized via `normalizePolymarket()` into `NormalizedOrderBook`
   **And** all normalized books are persisted and events emitted as before

2. **Given** the batch `getOrderBooks()` call returns results
   **When** some token IDs return empty or missing order books
   **Then** the missing tokens are logged at warning level with their token IDs
   **And** successfully returned order books are still processed normally
   **And** no error is thrown for partial results

3. **Given** the batch `getOrderBooks()` call fails entirely (network error, rate limit, 5xx)
   **When** the error is caught
   **Then** a `PlatformApiError` is thrown with appropriate error code and retry strategy
   **And** the error is handled identically to the current single-call error path

4. **Given** `PlatformHealthService.publishHealth()` runs on its 30-second cron
   **When** a platform's health status has NOT changed since the last tick
   **Then** no `platform_health_logs` row is written to the database
   **And** the in-memory status and event emission continue as before

5. **Given** `PlatformHealthService.publishHealth()` runs on its 30-second cron
   **When** a platform's health status HAS changed (e.g., `healthy → degraded`)
   **Then** a `platform_health_logs` row IS written with the new status
   **And** the appropriate domain event is emitted as before

6. **Given** the Polymarket connector exposes `getOrderBooks(contractIds: string[])`
   **When** inspecting the `IPlatformConnector` interface
   **Then** the interface is unchanged — `getOrderBooks()` is a Polymarket-specific method, not on the shared interface
   **And** `DataIngestionService` calls it via the typed `PolymarketConnector` reference (already injected as concrete type, not via interface)

7. **Given** `getOrderBooks()` is called with an empty `contractIds` array
   **When** the method executes
   **Then** no SDK call is made and an empty `NormalizedOrderBook[]` is returned immediately

## Tasks / Subtasks

- [x] Task 1: Add batch `getOrderBooks()` method to `PolymarketConnector` (AC: #1, #2, #3, #7)
  - [x] 1.1 Add `getOrderBooks(contractIds: string[])` method to `PolymarketConnector`. Import `BookParams` and `Side` from `@polymarket/clob-client`.
  - [x] 1.1a Early return: if `contractIds.length === 0`, return `[]` immediately (no SDK call, no rate limit token consumed)
  - [x] 1.2 Guard: throw `PlatformApiError` with `POLYMARKET_ERROR_CODES.UNAUTHORIZED` if `clobClient` not initialized (same pattern as `getOrderBook`)
  - [x] 1.3 Call `rateLimiter.acquireRead()` once (not per token)
  - [x] 1.4 Build `BookParams[]` from contractIds — use `{ token_id, side: Side.BUY } as BookParams` (see Dev Notes on SDK type quirk)
  - [x] 1.5 Call `clobClient.getOrderBooks(params)` via `withRetry()` with `RETRY_STRATEGIES.NETWORK_ERROR`
  - [x] 1.6 Update `this.lastHeartbeat` after successful call
  - [x] 1.7 Normalize each `OrderBookSummary` via `this.normalizer.normalizePolymarket()` — build `PolymarketOrderBookMessage` from SDK response
  - [x] 1.8 Handle partial results: compare returned `asset_id` set against requested `contractIds` to identify missing tokens. Filter out nulls from normalization. Log warnings with specific missing token IDs:
    ```typescript
    const returnedIds = new Set(response.map((b) => b.asset_id));
    for (const id of contractIds) {
      if (!returnedIds.has(id)) {
        this.logger.warn({ message: 'No order book returned for token', module: 'connector', metadata: { tokenId: id } });
      }
    }
    ```
  - [x] 1.9 Error handling: catch and rethrow `PlatformApiError`, map unknown errors via `this.mapError()`
  - [x] 1.10 Add unit tests for batch method (happy path, partial results, empty input, full failure, clobClient not initialized)

- [x] Task 2: Replace sequential Polymarket loop with batch call in `DataIngestionService` (AC: #1, #2)
  - [x] 2.1 Replace the `for (const tokenId of polymarketTokens)` loop with a single `this.polymarketConnector.getOrderBooks(polymarketTokens)` call
  - [x] 2.2 Iterate returned `NormalizedOrderBook[]` for persistence (`persistSnapshot`) and event emission (`OrderBookUpdatedEvent`)
  - [x] 2.3 Record health update once for the batch: `this.healthService.recordUpdate(PlatformId.POLYMARKET, batchLatency)`
  - [x] 2.4 Log per-book ingestion details (contractId, bidLevels, askLevels, bestBid, bestAsk) inside the result loop
  - [x] 2.5 Outer error handling remains identical: catch block logs "Polymarket order book ingestion failed"
  - [x] 2.6 Handle zero-length `polymarketTokens` — skip batch call entirely (existing guard covers this)
  - [x] 2.7 Update unit tests: mock `getOrderBooks` instead of `getOrderBook`, verify single call for multiple tokens

- [x] Task 3: Guard health log persistence to status transitions only in `PlatformHealthService` (AC: #4, #5)
  - [x] 3.1 In `publishHealth()`, wrap the `prisma.platformHealthLog.create()` call with `if (health.status !== previousStatus)`
  - [x] 3.2 First-tick behavior: `previousStatus` defaults to `'healthy'` via `this.previousStatus.get(platform) || 'healthy'`. If the first calculated status is also `'healthy'`, NO DB write occurs (no transition). If the first calculated status is `'degraded'` or `'disconnected'`, a DB write DOES occur (status differs from default). This is correct — we only care about transitions, and the initial "already healthy" state needs no audit trail entry.
  - [x] 3.3 Verify ALL event emissions are NOT affected by the DB guard — these still fire every tick regardless of DB write:
    - `EVENT_NAMES.PLATFORM_HEALTH_UPDATED` (always, every tick)
    - `EVENT_NAMES.PLATFORM_HEALTH_DEGRADED` (on degradation transition)
    - `EVENT_NAMES.PLATFORM_HEALTH_RECOVERED` (on recovery transition)
    - `EVENT_NAMES.PLATFORM_HEALTH_DISCONNECTED` (on disconnection transition)
  - [x] 3.4 Add unit tests: verify DB write on transition (`healthy → degraded`), verify no DB write when status unchanged (`healthy → healthy`), verify events still fire regardless, verify first-tick-healthy produces no DB write, verify first-tick-degraded DOES produce DB write

- [x] Task 4: Run lint + test (all ACs)
  - [x] 4.1 Run `pnpm lint` — zero errors
  - [x] 4.2 Run `pnpm test` — all tests pass (no regressions)

## Dev Notes

### Key Implementation Details

**SDK Type Quirk — `BookParams.side` is typed as required but functionally optional:**

The `@polymarket/clob-client` SDK declares `BookParams` as:
```typescript
export interface BookParams {
  token_id: string;
  side: Side;  // TypeScript says required
}
```

However, the Polymarket docs describe `side` as an optional filter. The `POST /books` endpoint returns full order books (both bids and asks) regardless of the `side` value when the API ignores it. The SDK's `getOrderBooks` sends the params array as POST body JSON — the API accepts any `side` value and returns the complete book.

**Recommended approach:** Provide `Side.BUY` as a placeholder value to satisfy the TypeScript compiler:
```typescript
const params: BookParams[] = contractIds.map((id) => ({
  token_id: id,
  side: Side.BUY,
}));
```
The returned `OrderBookSummary` always contains both `bids` and `asks` arrays, matching the existing single-fetch behavior. Add a code comment explaining this.

**Mapping `OrderBookSummary` to `PolymarketOrderBookMessage`:**

The existing `getOrderBook()` method constructs a `PolymarketOrderBookMessage` from the SDK response before normalizing:
```typescript
const rawBook: PolymarketOrderBookMessage = {
  asset_id: contractId,
  market: '',
  timestamp: Date.now(),
  bids: response.bids ?? [],
  asks: response.asks ?? [],
  hash: '',
};
```
The batch method must do the same for each `OrderBookSummary` in the response array. The SDK's `OrderBookSummary` type:
```typescript
// From @polymarket/clob-client/dist/types.d.ts
interface OrderBookSummary {
  market: string;
  asset_id: string;
  timestamp: string;       // Can be epoch ms string OR ISO 8601 — handle both
  bids: OrderSummary[];    // { price: string; size: string }
  asks: OrderSummary[];
  tick_size: string;
  neg_risk: boolean;
  last_trade_price: string;
  hash: string;
}
```

Map each `OrderBookSummary` to `PolymarketOrderBookMessage`:
```typescript
const rawBook: PolymarketOrderBookMessage = {
  asset_id: book.asset_id,
  market: book.market,
  timestamp: Number(book.timestamp) || new Date(book.timestamp).getTime() || Date.now(),
  bids: book.bids ?? [],
  asks: book.asks ?? [],
  hash: book.hash,
};
```
**Timestamp parsing:** `OrderBookSummary.timestamp` is typed as `string`. It may be epoch milliseconds (e.g., `"1709145352532"`) or ISO 8601 (e.g., `"2026-02-28T18:35:52Z"`). `Number()` handles epoch strings correctly; the `new Date()` fallback handles ISO strings; `Date.now()` is the last resort. This preserves the actual server timestamp from the batch response (better than `Date.now()` for data consistency across the batch).

**Health recording for batch:**

The current sequential loop calls `healthService.recordUpdate(PlatformId.POLYMARKET, latency)` per book. With batch, record the single round-trip latency once. This gives a more accurate picture — the latency represents the actual API call time, not per-book processing time.

**`DataIngestionService` already injects `PolymarketConnector` as a concrete type** (not via `IPlatformConnector` interface), so calling a Polymarket-specific `getOrderBooks()` method requires no interface changes.

### Architecture Compliance

- **`IPlatformConnector` interface:** UNCHANGED. `getOrderBooks()` is Polymarket-specific — Kalshi has no batch equivalent. The interface contract stays as-is.
- **Module boundaries:** No new cross-module imports. `DataIngestionService` already imports `PolymarketConnector` from `connectors/polymarket/`.
- **Error hierarchy:** All errors extend `PlatformApiError` via `POLYMARKET_ERROR_CODES` — no raw `Error` throws.
- **Financial math:** Not applicable — this story deals with order book fetching, not price calculations.
- **Event emission:** `OrderBookUpdatedEvent` emitted per-book as before — downstream detection module behavior is unchanged.
- **Rate limiter:** `acquireRead()` once per batch. No changes to `rate-limiter.ts`.

### Existing Code to Modify

1. **`src/connectors/polymarket/polymarket.connector.ts`** (lines 212-275)
   - Add new `getOrderBooks(contractIds: string[])` method after the existing `getOrderBook()` method
   - Existing `getOrderBook()` remains unchanged for future single-fetch needs (e.g., retry of individual token)
   - Add imports: `import { BookParams, Side } from '@polymarket/clob-client';` (SDK re-exports these from `types.ts`)

2. **`src/modules/data-ingestion/data-ingestion.service.ts`** (lines 207-253)
   - Replace the `for (const tokenId of polymarketTokens) { ... }` sequential loop (lines ~207-248)
   - Keep the outer try/catch and degradation check unchanged
   - Keep `pollDegradedPlatforms()` call at the end unchanged

3. **`src/modules/data-ingestion/platform-health.service.ts`** (lines 53-66)
   - Wrap `prisma.platformHealthLog.create()` with status transition check
   - Everything else in `publishHealth()` remains unchanged

### Existing Test Files to Update

- `src/connectors/polymarket/polymarket.connector.spec.ts` — Add tests for `getOrderBooks()` batch method
- `src/modules/data-ingestion/data-ingestion.service.spec.ts` — Update Polymarket ingestion tests from `getOrderBook` to `getOrderBooks`
- `src/modules/data-ingestion/platform-health.service.spec.ts` — Add tests for transition-only DB writes

### Testing Strategy

**Unit tests only — no e2e tests needed.** Changes are internal to existing modules with well-mocked dependencies.

For `PolymarketConnector.getOrderBooks()`:
- Happy path: 3 tokens → single `clobClient.getOrderBooks()` call → 3 normalized books returned
- Partial results: 3 tokens → only 2 books returned → 2 normalized, warning logged for missing token
- Empty input: 0 tokens → no SDK call, return empty array
- Full failure: SDK throws → `PlatformApiError` propagated
- Client not initialized: `clobClient` null → throws `PlatformApiError` with UNAUTHORIZED code
- Normalization failure: SDK returns book that fails normalization → filtered out, warning logged

For `DataIngestionService.ingestCurrentOrderBooks()`:
- Verify single `getOrderBooks()` call (not multiple `getOrderBook()` calls)
- Verify `persistSnapshot()` called once per returned book
- Verify `OrderBookUpdatedEvent` emitted once per returned book
- Verify `healthService.recordUpdate()` called once (not per book)
- Verify degradation check still skips Polymarket when degraded
- Verify Kalshi path is completely unaffected

For `PlatformHealthService.publishHealth()`:
- Status unchanged (`healthy → healthy`): no `prisma.platformHealthLog.create()` call
- Status changed (`healthy → degraded`): one `prisma.platformHealthLog.create()` call
- All 4 event types (`UPDATED`, `DEGRADED`, `RECOVERED`, `DISCONNECTED`) still fire on their respective conditions regardless of DB write/skip
- First tick: initial healthy → no DB write (previousStatus defaults to 'healthy', no transition)
- First tick: initial degraded → DB write occurs (differs from default 'healthy')
- Kalshi and Polymarket platforms both tested independently

### Performance Impact

| Metric | Before | After |
|--------|--------|-------|
| Polymarket HTTP round-trips per cycle | 8 (one per pair) | 1 (batch) |
| Rate limit tokens consumed per cycle | 8 | 1 |
| Polymarket ingestion latency (8 pairs) | ~960ms | ~150ms |
| Data consistency window | ~960ms spread | Single server timestamp |
| Health log DB writes per day (2 platforms, 30s interval) | ~5,760 | ~0 (transition-only) |
| Max pairs before rate limit concern | ~50 | 500 per request |

### Previous Story Intelligence (Story 6.5.2)

**Metrics after 6.5.2:**
- Tests passing: 1,091 (66 test files)
- Lint errors: 0
- Build: Clean

**Key changes from 6.5.2:**
- Added `ecosystem.config.js` (pm2 config) — no impact on this story
- Added backup/restore scripts — no impact on this story
- Added `.env.production.example` — no impact on this story
- Added `dotenv` as direct dependency — no impact on this story
- Rate limiter buckets tuned in both connectors for 8-pair config — the Polymarket bucket is 20 reads (set in constructor)

**Flaky test note:** `logging.e2e-spec.ts:86` is pre-existing timing-dependent flaky test. Not related to this story.

### Git Intelligence

Recent engine commits:
```
88c6aad feat: add production environment configuration, PostgreSQL backup and restore scripts
c2fa2a9 feat: update Kalshi API integration with new base URL, enhance orderbook structure
48caebd feat: update Polymarket WebSocket handling to support nested price_change messages
6d0c1d5 feat: enhance codebase with TypeScript linting rules, add new dependencies
4101ec4 feat: add audit log functionality with tamper-evident hash chain
```

Commit pattern: `feat:` prefix, descriptive summary.

### Web Research Findings

**`@polymarket/clob-client` SDK — `getOrderBooks()` confirmed:**
- Method signature: `getOrderBooks(params: BookParams[]): Promise<OrderBookSummary[]>`
- `BookParams`: `{ token_id: string; side: Side }` — `side` is typed as required in TypeScript but the Polymarket API docs describe it as an optional filter parameter
- Implementation: `POST /books` with params as JSON body
- Limit: up to 500 tokens per request
- Each `OrderBookSummary` in the response contains: `market`, `asset_id`, `timestamp`, `bids: OrderSummary[]`, `asks: OrderSummary[]`, `tick_size`, `neg_risk`, `last_trade_price`, `hash`
- `OrderSummary`: `{ price: string; size: string }`
- The `/books` endpoint has a rate limit of 300 req/10s (per Polymarket May 2025 changelog)

### Project Structure Notes

Files to modify:
- `pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.ts` — Add `getOrderBooks()` method
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.ts` — Replace sequential loop with batch
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts` — Guard DB write to transitions

Test files to update:
- `pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.spec.ts`
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.spec.ts`
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.spec.ts`

No new files created. No schema migrations. No new dependencies. No env var changes.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.5.2a, lines 1533-1588] — Epic definition, ACs, technical notes, sequencing
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-28.md] — Full change proposal with impact analysis and performance comparison
- [Source: pm-arbitrage-engine/docs/polymarket-batch-orderbook-migration.md] — Problem analysis, SDK confirmation, complementary improvements
- [Source: pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.ts, lines 212-275] — Current `getOrderBook()` implementation
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.ts, lines 125-259] — Current `ingestCurrentOrderBooks()` with sequential loop
- [Source: pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts, lines 41-144] — Current `publishHealth()` with unconditional DB write
- [Source: pm-arbitrage-engine/node_modules/@polymarket/clob-client/dist/client.d.ts, line 37] — SDK `getOrderBooks()` type signature
- [Source: pm-arbitrage-engine/node_modules/@polymarket/clob-client/dist/types.d.ts, lines 352-355] — `BookParams` interface
- [Source: _bmad-output/implementation-artifacts/6-5-2-deployment-runbook-vps-provisioning.md] — Previous story context and metrics

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None required.

### Completion Notes List

- Task 1: Added `getOrderBooks(contractIds: string[])` to `PolymarketConnector` with batch SDK call, partial result handling, normalization, and 8 unit tests
- Task 2: Replaced sequential `for (const tokenId of polymarketTokens)` loop with single `getOrderBooks(polymarketTokens)` call; single `healthService.recordUpdate()` for the batch
- Task 3: Wrapped `prisma.platformHealthLog.create()` with `if (health.status !== previousStatus)` guard; events unaffected; 3 new tests for transition-only behavior
- Task 4: Lint 0 errors, 70 test files, 1101 tests passing (was 1091), 0 regressions
- No ambiguities found — story spec was clear and matched codebase reality

### File List

- `pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.ts` — Added `getOrderBooks()` batch method (lines 277-377)
- `pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.spec.ts` — Added 8 tests for `getOrderBooks()` batch method
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.ts` — Replaced Polymarket sequential loop with batch call
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.spec.ts` — Updated Polymarket mocks from `getOrderBook` to `getOrderBooks`
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts` — Added transition-only DB write guard
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.spec.ts` — Added 3 tests for transition-only DB writes, updated 1 existing test

### Senior Developer Review (AI)

**Reviewer:** Amelia (Dev Agent) — 2026-02-28
**Outcome:** Approved with 4 fixes applied

**Fixes applied:**
- **M2** Added comment in `pollDegradedPlatforms()` explaining why degraded polling intentionally uses sequential `getOrderBook()` instead of batch
- **M3** Renamed `latencyMs` → `batchLatencyMs` in per-book Polymarket ingestion log to avoid misleading per-book latency interpretation
- **L1** Added `isNaN` guard on `new Date()` timestamp fallback in `getOrderBooks()` to prevent NaN timestamps from invalid strings
- **L2** Added comment in `getOrderBooks()` documenting intentional leniency difference vs `getOrderBook()` on normalization failures

**Skipped (by operator):** M1 (undocumented `docs/polymarket-batch-orderbook-migration.md` in File List)

**Test results:** 70 files, 1101 tests pass. 1 pre-existing flaky e2e test (`logging.e2e-spec.ts:86` — timing-dependent, confirmed fails on pre-change code too).
