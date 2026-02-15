# Story 2.1: Polymarket Connector & Wallet Authentication

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Epic Deviations

**1. Authentication simplified from encrypted keystore to direct private key**
- **Epic AC states:** "the Polymarket keystore file exists and `POLYMARKET_KEYSTORE_PASSWORD` is configured... the keystore is decrypted using AES-256"
- **This story implements:** Direct private key via `POLYMARKET_PRIVATE_KEY` env var
- **Rationale:** `@polymarket/clob-client` expects an ethers `Wallet` constructed from a raw private key. Keystore encryption adds complexity with minimal security benefit for MVP (single-operator, localhost-only, SSH tunnel access). Keystore wrapping can be added as a security hardening task in Epic 11.

**2. On-chain / viem scope deferred to Epic 5**
- **Epic AC states:** "on-chain transaction handling uses viem for Polygon interactions", "gas estimation includes 20% buffer (NFR-I4)", "on-chain transaction confirmation uses 30-second timeout with chain reorg detection (NFR-I4)"
- **This story defers all three** — Polymarket's CLOB is off-chain; viem is only needed for on-chain settlement which happens in Epic 5 (trade execution).
- **FR/NFR traceability:** FR-PI-02 (wallet auth) is fully covered. NFR-I4 (on-chain confirmation, gas buffer, reorg handling) is deferred to Epic 5 Story 5.1 where `submitOrder()` is implemented.

## Story

As an operator,
I want to connect to Polymarket with wallet-based authentication,
So that I can access Polymarket's order book and trading API.

## Acceptance Criteria

**Given** the Polymarket private key is configured via `POLYMARKET_PRIVATE_KEY` environment variable
**When** the engine starts
**Then** the Polymarket connector authenticates via `@polymarket/clob-client` using L1 wallet signing → L2 API key derivation (FR-PI-02)
**And** the ClobClient is initialized with derived API credentials
**And** connection status is logged with platform ID

**Given** the Polymarket connector is initialized
**When** it connects to Polymarket's APIs
**Then** REST API client retrieves order book data via ClobClient.getOrderBook()
**And** WebSocket connection is established for real-time updates via `wss://ws-subscriptions-clob.polymarket.com/ws/market`
**And** connection status is logged with platform ID

**Given** the Polymarket WebSocket disconnects
**When** reconnection triggers
**Then** exponential backoff is applied (1s, 2s, 4s... max 60s) reusing the pattern from Epic 1
**And** reconnection attempts are logged

**Given** the Polymarket connector is implemented
**When** I inspect the code
**Then** it implements the `IPlatformConnector` interface from `common/interfaces/`
**And** rate limit enforcement reuses `withRetry()` and `PlatformApiError` from Epic 1
**And** error codes use the 1008-1099 range (Polymarket-specific within PlatformApiError 1000-1999)

## Tasks / Subtasks

- [x] Task 1: Install dependencies (AC: Dependencies available)
  - [x] Install `@polymarket/clob-client` (latest v5.2.x) — brings ethers v5, axios transitively
  - [x] Install `@polymarket/order-utils` if not already pulled in transitively
  - [x] Verify ethers v5 coexistence with existing dependencies (no conflicts)
  - [x] **DO NOT install viem** — not needed for this story; CLOB client handles all Polymarket interaction

- [x] Task 2: Create Polymarket-specific types (AC: Type safety)
  - [x] Create `src/connectors/polymarket/polymarket.types.ts`
  - [x] Define `PolymarketWebSocketConfig` interface (wsUrl, auth headers)
  - [x] Define `PolymarketOrderBookMessage` interface for WebSocket book snapshots
  - [x] Define `PolymarketPriceChangeMessage` interface for WebSocket price updates
  - [x] Define `PolymarketApiCredentials` interface wrapping ClobClient's apiKey/secret/passphrase
  - [x] Export all types

- [x] Task 3: Create Polymarket error codes (AC: Error mapping)
  - [x] Add Polymarket error codes to existing error constants file or create `src/connectors/polymarket/polymarket-error-codes.ts`
  - [x] Error codes (within 1008-1099 range):
    - `POLYMARKET_UNAUTHORIZED: 1008` — L1/L2 auth failure, critical, no retry
    - `POLYMARKET_RATE_LIMIT: 1009` — Rate limited, warning, with RETRY_STRATEGIES.RATE_LIMIT
    - `POLYMARKET_INVALID_REQUEST: 1010` — Bad request, error, no retry
    - `POLYMARKET_MARKET_NOT_FOUND: 1011` — Token ID not found, warning, no retry
    - `POLYMARKET_API_KEY_DERIVATION_FAILED: 1012` — createOrDeriveApiKey() failed, critical, retry once
    - `POLYMARKET_WEBSOCKET_ERROR: 1013` — WebSocket connection error, warning, with WEBSOCKET_RECONNECT
    - `POLYMARKET_STALE_DATA: 1014` — Order book data staleness detected, warning, no retry

- [x] Task 4: Create Polymarket WebSocket client (AC: Real-time updates)
  - [x] Create `src/connectors/polymarket/polymarket-websocket.client.ts`
  - [x] Follow exact same pattern as `KalshiWebSocketClient` (plain TypeScript class, not NestJS service)
  - [x] Connect to `wss://ws-subscriptions-clob.polymarket.com/ws/market`
  - [x] Subscribe to `book` channel for full order book snapshots
  - [x] Subscribe to `price_change` channel for incremental best bid/ask updates
  - [x] Implement reconnection with exponential backoff (reuse RETRY_STRATEGIES.WEBSOCKET_RECONNECT constants)
  - [x] Implement `onUpdate(callback)` subscriber pattern matching Kalshi's approach
  - [x] Normalize WebSocket data to `NormalizedOrderBook` format
  - [x] **Price normalization:** Polymarket prices are already decimal (0.00-1.00) — NO conversion needed (unlike Kalshi's cents ÷ 100)
  - [x] Track subscription state and resubscribe on reconnection
  - [x] Implement `getConnectionStatus(): boolean`
  - [x] Implement `connect()` and `disconnect()` methods

- [x] Task 5: Create PolymarketConnector service (AC: IPlatformConnector implementation)
  - [x] Create `src/connectors/polymarket/polymarket.connector.ts`
  - [x] `@Injectable()` decorator, implements `IPlatformConnector` and `OnModuleInit`, `OnModuleDestroy`
  - [x] Constructor injection of `ConfigService`
  - [x] Read config from environment:
    - `POLYMARKET_PRIVATE_KEY` — Wallet private key (direct, not keystore for MVP)
    - `POLYMARKET_CLOB_API_URL` — Default: `https://clob.polymarket.com`
    - `POLYMARKET_WS_URL` — Default: `wss://ws-subscriptions-clob.polymarket.com/ws/market`
    - `POLYMARKET_CHAIN_ID` — Default: `137` (Polygon mainnet)
  - [x] Implement `connect()`:
    1. Create ethers `Wallet` from private key
    2. Create temporary `ClobClient` with wallet signer
    3. Call `createOrDeriveApiKey()` to get L2 API credentials
    4. Create full `ClobClient` with API credentials and signatureType=0 (EOA)
    5. Initialize WebSocket client
    6. Log successful connection
  - [x] Implement `disconnect()`: Close WebSocket, clear ClobClient reference
  - [x] Implement `getOrderBook(contractId)`:
    1. Acquire rate limit token via `rateLimiter.acquireRead()`
    2. Call `clobClient.getOrderBook(contractId)` wrapped in `withRetry()`
    3. Transform to `NormalizedOrderBook` (prices already decimal, just map to PriceLevel[])
    4. Return normalized order book
  - [x] Implement `onOrderBookUpdate(callback)`: Delegate to WebSocket client's `onUpdate()`
  - [x] Implement `getHealth()`: Same pattern as Kalshi — check REST connected + WS connected → healthy/degraded/disconnected
  - [x] Implement `getPlatformId()`: Return `PlatformId.POLYMARKET`
  - [x] Implement `getFeeSchedule()`: Return Polymarket fee structure (taker fee ~2%, maker fee 0%)
  - [x] Stub `submitOrder()`, `cancelOrder()`, `getPositions()` with `throw new Error('Not implemented - Epic 5')` — matching Kalshi pattern
  - [x] Implement private `mapError()` method: Convert axios/ClobClient errors to `PlatformApiError` with appropriate Polymarket error codes
  - [x] Verify `PlatformId.POLYMARKET` exists in `common/types/` or `common/constants/platform.ts` — add it if missing
  - [x] Initialize `RateLimiter` — Polymarket rate limits are undocumented publicly; use conservative defaults (10 read/s, 5 write/s with 20% buffer)
  - [x] Log all HTTP 429 responses with request path, retry-after header, and timestamp — this data will be used to calibrate rate limit defaults after first week of operation

- [x] Task 6: Create SDK type declarations if needed (AC: TypeScript compatibility)
  - [x] Check if `@polymarket/clob-client` ships proper TypeScript types
  - [x] If NOT: Create `src/connectors/polymarket/polymarket-sdk.d.ts` with type declarations for ClobClient (same pattern as `kalshi-sdk.d.ts`)
  - [x] If YES: Skip this task — no custom declarations needed

- [x] Task 7: Register in ConnectorModule (AC: Module registration)
  - [x] Edit `src/connectors/connector.module.ts`
  - [x] Add `PolymarketConnector` to providers array
  - [x] Add `PolymarketConnector` to exports array

- [x] Task 8: Add environment variables (AC: Configuration)
  - [x] Update `.env.example` with Polymarket config vars:
    ```
    # Polymarket Configuration
    POLYMARKET_PRIVATE_KEY=            # Wallet private key (hex, no 0x prefix)
    POLYMARKET_CLOB_API_URL=https://clob.polymarket.com
    POLYMARKET_WS_URL=wss://ws-subscriptions-clob.polymarket.com/ws/market
    POLYMARKET_CHAIN_ID=137
    ```
  - [x] Update `.env.development` with test/sandbox values if available

- [x] Task 9: Unit tests for PolymarketConnector (AC: Comprehensive coverage)
  - [x] Create `src/connectors/polymarket/polymarket.connector.spec.ts`
  - [x] Mock `@polymarket/clob-client` ClobClient class
  - [x] Mock ConfigService with test configuration
  - [x] Test cases:
    - `connect()` creates wallet, derives API key, initializes ClobClient
    - `connect()` failure on invalid private key throws PlatformApiError (1008)
    - `connect()` failure on API key derivation throws PlatformApiError (1012)
    - `getOrderBook()` returns normalized order book with decimal prices
    - `getOrderBook()` calls rate limiter before API call
    - `getOrderBook()` wraps call in withRetry()
    - `getHealth()` returns healthy when REST + WS connected
    - `getHealth()` returns degraded when only one connected
    - `getHealth()` returns disconnected when neither connected
    - `getPlatformId()` returns PlatformId.POLYMARKET
    - `getFeeSchedule()` returns correct fee structure
    - `disconnect()` cleans up resources
    - Error mapping: axios 401 → PlatformApiError 1008
    - Error mapping: axios 429 → PlatformApiError 1009
    - Error mapping: generic error → PlatformApiError 1010

- [x] Task 10: Unit tests for PolymarketWebSocketClient (AC: WebSocket coverage)
  - [x] Create `src/connectors/polymarket/polymarket-websocket.client.spec.ts`
  - [x] Mock `ws` module (same pattern as Kalshi WS tests)
  - [x] Test cases:
    - `connect()` establishes WebSocket connection
    - Message parsing: book snapshot updates local state
    - Message parsing: price_change updates best bid/ask
    - Reconnection: triggers on close with exponential backoff
    - Reconnection: resubscribes to all tracked tokens
    - `onUpdate()` notifies all subscribers
    - `disconnect()` closes connection cleanly
    - `getConnectionStatus()` reflects actual state

## Dev Notes

### Story Context & Critical Mission

This is **Story 2.1** in Epic 2 — the first story of Polymarket Connectivity. This story is **CRITICAL** because:

1. **Second Platform Foundation** — The entire arbitrage system requires two platforms. Without Polymarket, there is no arbitrage.
2. **IPlatformConnector Validation** — This is the second implementation of the interface, proving the abstraction works across heterogeneous platforms (REST+WebSocket vs. CLOB API).
3. **Authentication Complexity** — Polymarket uses a two-level auth system (L1 wallet → L2 API key) that must be handled reliably.

### Architecture Divergence: @polymarket/clob-client vs. viem

**Original architecture specifies:** `viem` for Polymarket on-chain transactions (architecture.md)

**Actual implementation decision:** Use `@polymarket/clob-client` as primary SDK

**Rationale:**
- Polymarket's order book is **off-chain** (CLOB API), NOT on-chain — `viem` cannot access it
- `@polymarket/clob-client` provides complete abstraction: authentication, order book, trading, WebSocket
- The client uses `ethers v5` internally — coexists fine as a transitive dependency
- `viem` is NOT needed for this story — all Polymarket interaction goes through CLOB API
- Future stories (gas estimation for on-chain settlement in Epic 5) can add `viem` if needed
- User explicitly requested considering `@polymarket/clob-client` for its abstraction benefits

**Impact on architecture.md references:**
- `src/connectors/polymarket/polymarket-chain.client.ts` — **NOT NEEDED** for this story (CLOB API is off-chain)
- `src/connectors/polymarket/keystore.service.ts` — **SIMPLIFIED**: Direct private key from env var, no keystore decryption for MVP. Keystore encryption can be added later as a security hardening task.
- `viem` dependency — **DEFERRED** to Epic 5 if on-chain settlement monitoring is needed

### Authentication Flow (CRITICAL — Verify Before Coding)

```typescript
import { ClobClient } from "@polymarket/clob-client";
import { Wallet } from "ethers"; // v5.7.x (from clob-client dependency)

// Step 1: Create wallet signer from private key
const signer = new Wallet(POLYMARKET_PRIVATE_KEY);

// Step 2: Create temporary client for API key derivation
const tempClient = new ClobClient(CLOB_API_URL, CHAIN_ID, signer);

// Step 3: Derive or create API credentials (L1 → L2)
const apiCreds = await tempClient.createOrDeriveApiKey();
// Returns: { apiKey: string, secret: string, passphrase: string }

// Step 4: Create authenticated client
const client = new ClobClient(
  CLOB_API_URL,
  CHAIN_ID,
  signer,
  apiCreds,
  0 // signatureType: 0 = EOA wallet
);
```

**CRITICAL:** Always use `createOrDeriveApiKey()` — never `createApiKey()`. The derive method checks for existing credentials first, avoiding unnecessary key creation.

**CRITICAL:** If you get `L2_AUTH_NOT_AVAILABLE` error, it means `createOrDeriveApiKey()` was not called before making authenticated requests.

### Price Normalization

**Polymarket prices are already decimal (0.00-1.00)** — NO conversion needed.

This is different from Kalshi where cents must be divided by 100. The normalizer for Polymarket is essentially a pass-through for price values.

```typescript
// Kalshi: 62 cents → 0.62 (divide by 100)
// Polymarket: 0.62 → 0.62 (pass-through)
```

### WebSocket Architecture

Polymarket provides two WebSocket endpoints:
1. **Market channel** (`/ws/market`) — Order book snapshots, price changes (used in this story)
2. **User channel** (`/ws/user`) — Order fills, trade notifications (used in Epic 5)

**Message types for market channel:**
- `book` — Full order book snapshot (bids + asks array)
- `price_change` — Incremental best bid/ask update

**Subscription format:**
```json
{
  "auth": {},
  "type": "subscribe",
  "markets": ["<condition_id>"],
  "assets_ids": ["<token_id>"]
}
```

**Alternative consideration:** `@polymarket/real-time-data-client` package provides a wrapper for WebSocket data streaming. Evaluate during implementation whether to use it or implement custom WebSocket client following Kalshi's pattern. Custom client is recommended for consistency with existing patterns.

### Contract ID Semantics for Polymarket

Polymarket uses two identifiers:
- **condition_id** — Identifies the market/event (e.g., "Will X happen?")
- **token_id** — Identifies a specific outcome token (YES or NO side of the market)

For `IPlatformConnector.getOrderBook(contractId)`, the `contractId` parameter maps to Polymarket's **token_id** (the tradeable asset). The mapping from cross-platform contract pairs (Epic 3) to Polymarket token_ids will be formalized in Epic 3 Story 3.1's contract pair configuration. For this story, `getOrderBook()` accepts a token_id string directly.

WebSocket subscriptions use both: `markets` (condition_id) subscribes to all outcomes of a market, `assets_ids` (token_id) subscribes to a specific outcome. Use `assets_ids` for targeted order book streaming.

### Fee Structure

Polymarket fees (as of Feb 2026):
- **Taker fee:** ~2% (varies, check current schedule)
- **Maker fee:** 0%
- **No gas fees for CLOB operations** — Order matching is off-chain
- **Gas fees apply only for on-chain settlement** (deferred to Epic 5)

### Rate Limiting

Polymarket's CLOB API rate limits are not well-documented publicly. Conservative defaults:
- Read operations: 10 requests/second (with 20% buffer → 8 effective)
- Write operations: 5 requests/second (with 20% buffer → 4 effective)

Use the existing `RateLimiter` utility with a custom tier configuration. Adjust based on observed 429 responses during testing.

### Ethers v5 Coexistence

`@polymarket/clob-client` depends on `ethers v5.7.x`. This is a **transitive dependency** — it lives in the clob-client's node_modules. Our project doesn't directly use ethers anywhere else, so there's no conflict.

**DO NOT** add ethers as a direct dependency. Let it come through `@polymarket/clob-client`.

If future stories need `viem` for on-chain operations, they coexist fine — they are completely independent libraries.

### Existing Kalshi Patterns to Reuse

| Pattern | Location | How to Reuse |
|---------|----------|-------------|
| IPlatformConnector | `common/interfaces/platform-connector.interface.ts` | Implement same interface |
| PlatformApiError | `common/errors/platform-api-error.ts` | Use with Polymarket error codes (1008-1099) |
| withRetry() | `common/utils/with-retry.ts` | Wrap ClobClient API calls |
| RateLimiter | `common/utils/rate-limiter.ts` | Create Polymarket tier config |
| RETRY_STRATEGIES | `connectors/kalshi/kalshi.types.ts` or `common/` | Reuse RATE_LIMIT, NETWORK_ERROR, WEBSOCKET_RECONNECT |
| Structured logging | All connector files | Same format: message, module, timestamp, platformId, metadata |
| WebSocket client pattern | `connectors/kalshi/kalshi-websocket.client.ts` | Same class structure, reconnection, subscriber pattern |
| Error mapping | `kalshi.connector.ts` mapError() | Same pattern, different error codes |
| Health status logic | `kalshi.connector.ts` getHealth() | Identical logic with PlatformId.POLYMARKET |

### Order Book Data Staleness Warning

There have been reported issues with Polymarket's `/book` endpoint returning stale data while `/price` remains accurate. The implementing agent should:
1. Always include timestamp in normalized order book
2. Consider cross-validating with `/price` endpoint for critical operations
3. Log warnings if order book timestamp is older than 30 seconds

### Project Structure Notes

**New files to create:**
```
src/connectors/polymarket/
├── polymarket.connector.ts           # Main NestJS service (IPlatformConnector)
├── polymarket.connector.spec.ts      # Unit tests
├── polymarket-websocket.client.ts    # WebSocket client
├── polymarket-websocket.client.spec.ts
├── polymarket.types.ts               # Polymarket-specific types
└── polymarket-error-codes.ts         # Error code constants (1008-1099)
```

**Files to modify:**
- `src/connectors/connector.module.ts` — Add PolymarketConnector to providers/exports
- `.env.example` — Add Polymarket config vars
- `.env.development` — Add Polymarket dev values
- `package.json` — `@polymarket/clob-client` dependency added via pnpm

**Alignment with architecture:** Follows `src/connectors/polymarket/` directory structure from architecture.md. Deviates by not creating `polymarket-chain.client.ts` or `keystore.service.ts` (not needed with CLOB client approach).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1] — Acceptance criteria and BDD scenarios
- [Source: _bmad-output/planning-artifacts/architecture.md#Platform Connector Interface] — IPlatformConnector contract
- [Source: _bmad-output/planning-artifacts/architecture.md#Polymarket Connector Files] — Expected file structure
- [Source: _bmad-output/implementation-artifacts/1-6-ntp-synchronization-time-management.md] — Previous story patterns (events, logging)
- [Source: src/connectors/kalshi/kalshi.connector.ts] — Reference implementation for connector pattern
- [Source: src/connectors/kalshi/kalshi-websocket.client.ts] — WebSocket client reference implementation
- [npm: @polymarket/clob-client v5.2.3](https://www.npmjs.com/package/@polymarket/clob-client) — Primary Polymarket SDK
- [Polymarket CLOB Quickstart](https://docs.polymarket.com/developers/CLOB/quickstart) — Authentication flow documentation
- [Polymarket WebSocket Overview](https://docs.polymarket.com/developers/CLOB/websocket/wss-overview) — WebSocket channel documentation
- [GitHub: Polymarket/clob-client](https://github.com/Polymarket/clob-client) — Source code and examples

### Testing Strategy

**Unit Tests Required:**

1. **polymarket.connector.spec.ts**
   - connect() flow: wallet creation → API key derivation → ClobClient initialization
   - connect() error handling: invalid key, derivation failure
   - getOrderBook() returns normalized data (prices already decimal)
   - getOrderBook() rate limiting and retry behavior
   - getHealth() state transitions (healthy/degraded/disconnected)
   - getFeeSchedule() returns correct structure
   - Error mapping: HTTP status codes → PlatformApiError codes
   - disconnect() cleanup

2. **polymarket-websocket.client.spec.ts**
   - Connection establishment and subscription
   - Message parsing: book snapshots
   - Message parsing: price_change updates
   - Reconnection with exponential backoff
   - Subscriber notification pattern
   - Connection status tracking

**Manual Verification:**
```bash
cd pm-arbitrage-engine
pnpm start:dev

# Check logs for:
# - "Connecting to Polymarket CLOB API"
# - "API credentials derived successfully"
# - "WebSocket connected to Polymarket market channel"
# - Order book data flowing (if subscribed to a market)
```

### Critical Implementation Decisions

**Decision 1: Use @polymarket/clob-client instead of raw viem**
- **Answer:** @polymarket/clob-client v5.2.3
- **Rationale:** CLOB is off-chain; viem can't access it; client provides complete abstraction; user explicitly requested it

**Decision 2: Direct private key vs. encrypted keystore**
- **Answer:** Direct private key from environment variable for MVP
- **Rationale:** Simpler setup; architecture's keystore approach is a security hardening concern for Phase 1; env vars are sufficient for single-operator MVP behind SSH tunnel

**Decision 3: Custom WebSocket client vs. @polymarket/real-time-data-client**
- **Answer:** Custom WebSocket client following Kalshi's pattern
- **Rationale:** Consistency with existing codebase; full control over reconnection and normalization; real-time-data-client is for broader streaming use cases

**Decision 4: Error code range**
- **Answer:** 1008-1099 for Polymarket (within PlatformApiError 1000-1999)
- **Rationale:** Kalshi uses 1001-1007; Polymarket starts at 1008; leaves room for future platforms

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None

### Completion Notes List

- Installed `@polymarket/clob-client@5.2.3` and `@ethersproject/wallet@5.8.0` (needed for direct import since pnpm doesn't hoist)
- `@polymarket/order-utils` comes transitively via clob-client
- ethers v5 coexists fine as transitive dep — no conflicts
- viem NOT installed (already existed in package.json from earlier, but not used by this story)
- Task 6 (SDK type declarations) skipped — `@polymarket/clob-client` ships proper TypeScript `.d.ts` files
- Created PolymarketConnector implementing IPlatformConnector with full connect/disconnect/getOrderBook/getHealth/getFeeSchedule
- Created PolymarketWebSocketClient following Kalshi's pattern with exponential backoff reconnection
- Polymarket prices pass through as-is (already decimal 0.00-1.00, no conversion needed)
- Rate limiter uses conservative defaults: 8 read/s, 4 write/s (10/5 with 20% buffer)
- 18 unit tests for connector, 12 unit tests for WebSocket client — all passing
- All 179 tests pass (21 test files), no regressions
- ESLint clean
- Code review (CR workflow) completed: 2 MEDIUM issues fixed (File List documentation, rate limit logging enhancement)

### Change Log

- 2026-02-15: Story 2.1 implementation complete — all tasks done, all tests passing
- 2026-02-15: Code review fixes applied — enhanced rate limit logging with request path, updated File List with pnpm-lock.yaml

### File List

**New files:**
- `src/connectors/polymarket/polymarket.types.ts`
- `src/connectors/polymarket/polymarket-error-codes.ts`
- `src/connectors/polymarket/polymarket-websocket.client.ts`
- `src/connectors/polymarket/polymarket-websocket.client.spec.ts`
- `src/connectors/polymarket/polymarket.connector.ts`
- `src/connectors/polymarket/polymarket.connector.spec.ts`

**Modified files:**
- `src/connectors/connector.module.ts` — Added PolymarketConnector to providers/exports
- `.env.example` — Added Polymarket config vars
- `.env.development` — Added Polymarket config vars
- `package.json` — Added @polymarket/clob-client, @ethersproject/wallet dependencies
- `pnpm-lock.yaml` — Updated with new dependencies (@polymarket/clob-client, @ethersproject/wallet)

**Deleted files:**
- `src/connectors/polymarket/.gitkeep` — Replaced by actual implementation files
