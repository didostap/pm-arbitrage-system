# Story 1.3: Kalshi Platform Connector & Authentication

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want to connect to Kalshi's API with authenticated access and see raw order book data,
So that I can verify platform connectivity works before building detection logic.

## Acceptance Criteria

**Given** Kalshi API credentials are configured in environment variables
**When** the engine starts
**Then** the Kalshi connector authenticates via API key (FR-PI-01)
**And** establishes a WebSocket connection for real-time data
**And** connection status is logged

**Given** the Kalshi WebSocket disconnects
**When** reconnection triggers
**Then** exponential backoff is applied (1s, 2s, 4s... max 60s)
**And** reconnection attempts are logged with attempt count

**Given** the connector is making API requests
**When** rate limit utilization reaches 70% of published limits
**Then** an alert-level log is emitted (FR-PI-04)
**And** request queueing activates to enforce 20% safety buffer (FR-PI-03)

**Given** a Kalshi API call fails
**When** the error matches a known error code (1001-1007)
**Then** the appropriate `PlatformApiError` is thrown with severity and retry strategy
**And** retryable errors use `withRetry()` with exponential backoff
**And** non-retryable errors (1001 Unauthorized, 1007 Schema Change) are escalated immediately

**Given** the `IPlatformConnector` interface is defined in `common/interfaces/`
**When** the Kalshi connector is implemented
**Then** it implements all interface methods (`submitOrder`, `cancelOrder`, `getOrderBook`, `getPositions`, `getHealth`, `getPlatformId`, `getFeeSchedule`, `connect`, `disconnect`, `onOrderBookUpdate`)
**And** the `SystemError` base class and `PlatformApiError` subclass exist in `common/errors/`
**And** the `withRetry()` utility exists in `common/utils/`

## Tasks / Subtasks

- [x] Task 1: Define IPlatformConnector interface (AC: Interface definition)
  - [x] Create `src/common/interfaces/platform-connector.interface.ts`
  - [x] Define all method signatures per architecture specification
  - [x] Add TypeDoc comments for each method
  - [x] Export from `src/common/interfaces/index.ts`

- [x] Task 2: Define core types (AC: Type safety)
  - [x] Create `src/common/types/normalized-order-book.type.ts` (NormalizedOrderBook interface)
  - [x] Create `src/common/types/platform.type.ts` (PlatformId enum, PlatformHealth, OrderParams, etc.)
  - [x] Export from `src/common/types/index.ts`

- [x] Task 3: Create error hierarchy (AC: Error handling)
  - [x] Create `src/common/errors/system-error.ts` (base class)
  - [x] Create `src/common/errors/platform-api-error.ts` (1000-1999 codes)
  - [x] Define Kalshi-specific error codes (1001-1007)
  - [x] Add severity levels and retry strategies
  - [x] Export from `src/common/errors/index.ts`

- [x] Task 4: Implement withRetry() utility (AC: Retry logic)
  - [x] Create `src/common/utils/with-retry.ts`
  - [x] Implement exponential backoff algorithm
  - [x] Support max retries and timeout configuration
  - [x] Add comprehensive error handling
  - [x] Write unit tests

- [x] Task 5: Implement rate limiter utility (AC: Rate limit enforcement)
  - [x] Create `src/common/utils/rate-limiter.ts`
  - [x] Implement dual-bucket rate limiter (separate read/write limits)
  - [x] Add 70% alert threshold and 20% safety buffer enforcement
  - [x] Support tier configuration (Basic: 20r/10w, Advanced: 30/30, etc.)
  - [x] Write comprehensive unit tests

- [x] Task 6: Install and configure Kalshi SDK (AC: Authentication)
  - [x] Install `kalshi-typescript` npm package (latest stable)
  - [x] Create Kalshi configuration service wrapper
  - [x] Add KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH to environment
  - [x] Verify SDK initialization and authentication flow
  - [x] Write unit tests for SDK wrapper

- [x] Task 7: Implement Kalshi WebSocket client (AC: Real-time data, reconnection)
  - [x] Install WebSocket dependencies: `pnpm add ws` and `pnpm add -D @types/ws`
  - [x] Create `src/connectors/kalshi/kalshi-websocket.client.ts`
  - [x] Implement WebSocket connection with RSA-PSS auth headers during handshake
  - [x] Check if `kalshi-typescript` SDK provides signing utility; if not, implement minimal RSA-PSS signing function
  - [x] Subscribe to `orderbook_delta` channel
  - [x] Implement local orderbook state maintenance (apply deltas to snapshot)
  - [x] Implement exponential backoff reconnection (1s, 2s, 4s... max 60s)
  - [x] Handle disconnect/error events with logging
  - [x] Write unit tests with WebSocket mocks

- [x] Task 8: Implement KalshiConnector service (AC: All interface methods)
  - [x] Create `src/connectors/kalshi/kalshi.connector.ts`
  - [x] Implement IPlatformConnector interface
  - [x] Wire together SDK client and WebSocket client
  - [x] Transform Kalshi YES/NO bid structure to NormalizedOrderBook format
  - [x] Implement all required methods with proper error handling
  - [x] Add structured logging for all operations
  - [x] Write comprehensive unit tests

- [x] Task 9: Create Connector module (AC: Module wiring)
  - [x] Create `src/connectors/connector.module.ts`
  - [x] Register KalshiConnector as provider
  - [x] Export connector for dependency injection
  - [x] Import into AppModule

- [x] Task 10: Integration testing (AC: End-to-end connectivity)
  - [x] Unit tests cover connection lifecycle, orderbook transformation, error mapping
  - [x] Test authentication success/failure scenarios via mocked SDK
  - [x] Test WebSocket delta application and state management
  - [x] Test rate limit enforcement (read/write separation)
  - [x] Verify all logs are properly structured

## Dev Notes

### 🎯 Story Context & Critical Mission

This is **Story 1.3** in Epic 1 - the third story building toward complete Kalshi connectivity. This story is **CRITICAL** because:

1. **First platform integration** - Establishes patterns for all future platform connectors (Polymarket in Epic 2, potential third platforms in Phase 1+)
2. **Interface-driven architecture** - The `IPlatformConnector` interface is the foundation of the entire platform abstraction layer
3. **Error handling foundation** - Creates the centralized error hierarchy used by ALL modules
4. **Retry patterns** - Implements `withRetry()` utility used throughout the system
5. **Production-grade WebSocket management** - Establishes reconnection and resilience patterns

**⚠️ CRITICAL: This story creates foundational infrastructure that EVERY future module depends on. Do not cut corners.**

### 🏗️ Architecture Intelligence - Platform Abstraction Layer

#### The IPlatformConnector Interface (Foundation of Everything)

From `architecture.md#API & Communication Patterns`:

```typescript
interface IPlatformConnector {
  // Order Management
  submitOrder(params: OrderParams): Promise<OrderResult>
  cancelOrder(orderId: string): Promise<CancelResult>

  // Market Data
  getOrderBook(contractId: string): Promise<NormalizedOrderBook>
  getPositions(): Promise<Position[]>

  // Platform Metadata
  getHealth(): PlatformHealth
  getPlatformId(): PlatformId
  getFeeSchedule(): FeeSchedule

  // Connection Lifecycle
  connect(): Promise<void>
  disconnect(): Promise<void>
  onOrderBookUpdate(callback: (book: NormalizedOrderBook) => void): void
}
```

**Why this interface matters:**

From `architecture.md#Cross-Cutting Concerns`:
> Platform Abstraction — Every module touches platform-specific behavior (authentication, data formats, execution mechanics, fee structures). Clean abstraction boundary between platform connectors and core logic is the single most critical architectural decision.

**Implications for Story 1.3:**
- This interface MUST be complete and correct - it won't change
- All methods MUST handle errors via the centralized error hierarchy
- The interface is the ONLY contract between connectors and core modules
- Future connectors (Polymarket, etc.) implement this exact interface

#### Centralized Error Hierarchy (System-Wide Foundation)

From `architecture.md#API & Communication Patterns - Error Handling`:

```
SystemError (base class)
  ├── PlatformApiError (1000-1999) — severity, retryStrategy, platformId
  ├── ExecutionError (2000-2999) — severity, retryStrategy, affectedPositionId
  ├── RiskLimitError (3000-3999) — severity, limitType, currentValue, threshold
  └── SystemHealthError (4000-4999) — severity, component, diagnosticInfo
```

**For Story 1.3:** Implement `SystemError` base class and `PlatformApiError` subclass only. Other error types come in later stories.

**Kalshi-Specific Error Codes (1001-1007):**

From PRD error catalog and architecture specification:

- **1001 - Unauthorized**: Invalid API key/secret, auth failed → Severity: CRITICAL, Retry: NO
- **1002 - Rate Limit Exceeded**: Hit platform rate limit → Severity: WARNING, Retry: YES (exponential backoff)
- **1003 - Invalid Request**: Malformed request parameters → Severity: ERROR, Retry: NO
- **1004 - Market Not Found**: Contract ID doesn't exist → Severity: WARNING, Retry: NO
- **1005 - Insufficient Funds**: Account balance too low → Severity: WARNING, Retry: NO
- **1006 - Order Rejected**: Order validation failed → Severity: WARNING, Retry: NO (but may retry with adjusted parameters)
- **1007 - Schema Change**: API response schema changed unexpectedly → Severity: CRITICAL, Retry: NO (defensive parsing failed)

**Error Class Structure:**

```typescript
// src/common/errors/system-error.ts
export abstract class SystemError extends Error {
  constructor(
    public readonly code: number,
    message: string,
    public readonly severity: 'critical' | 'error' | 'warning',
    public readonly retryStrategy?: RetryStrategy,
    public readonly metadata?: Record<string, any>,
  ) {
    super(message);
    this.name = this.constructor.name;
  }
}

// src/common/errors/platform-api-error.ts
export class PlatformApiError extends SystemError {
  constructor(
    code: number, // 1000-1999
    message: string,
    public readonly platformId: PlatformId,
    severity: 'critical' | 'error' | 'warning',
    retryStrategy?: RetryStrategy,
    metadata?: Record<string, any>,
  ) {
    super(code, message, severity, retryStrategy, metadata);
  }
}
```

#### The withRetry() Utility (Standardized Resilience)

From `architecture.md#Process Patterns`:

> Standardized retry utility with exponential backoff matching PRD error catalog. Each `SystemError` subclass carries its own `retryStrategy` (max retries, backoff intervals). Shared `withRetry(fn, strategy)` utility wraps retryable operations.

**Implementation Requirements:**

```typescript
// src/common/utils/with-retry.ts
export interface RetryStrategy {
  maxRetries: number;
  initialDelayMs: number;
  maxDelayMs: number;
  backoffMultiplier: number; // e.g., 2 for exponential doubling
}

export async function withRetry<T>(
  fn: () => Promise<T>,
  strategy: RetryStrategy,
  onRetry?: (attempt: number, error: Error) => void,
): Promise<T> {
  // Implement exponential backoff with jitter
  // Log each retry attempt
  // Throw final error after max retries exhausted
}
```

**Default Retry Strategies:**

```typescript
export const RETRY_STRATEGIES = {
  RATE_LIMIT: {
    maxRetries: 5,
    initialDelayMs: 1000,
    maxDelayMs: 60000,
    backoffMultiplier: 2,
  },
  NETWORK_ERROR: {
    maxRetries: 3,
    initialDelayMs: 500,
    maxDelayMs: 5000,
    backoffMultiplier: 2,
  },
  WEBSOCKET_RECONNECT: {
    maxRetries: Infinity, // Keep trying
    initialDelayMs: 1000,
    maxDelayMs: 60000,
    backoffMultiplier: 2,
  },
} as const;
```

### 🌐 Kalshi API Technical Specifications

#### Authentication (RSA-PSS Per-Request Signing)

**⚠️ CRITICAL: Kalshi uses RSA-PSS cryptographic signing, NOT Bearer tokens.**

**Authentication Method:** Every HTTP request requires three custom headers:

1. **`KALSHI-ACCESS-KEY`** - Your API Key ID (public identifier)
2. **`KALSHI-ACCESS-TIMESTAMP`** - Request timestamp in milliseconds (e.g., `1707649200000`)
3. **`KALSHI-ACCESS-SIGNATURE`** - RSA-PSS signature of the request

**Signature Generation:**
```
message = timestamp + method + path (without query params)
signature = RSA-PSS-Sign(message, privateKey, SHA-256, MGF1)
encoded_signature = Base64(signature)
```

**Example:**
```typescript
// For GET https://demo-api.kalshi.co/trade-api/v2/markets?limit=10
const timestamp = Date.now().toString();
const method = 'GET';
const path = '/trade-api/v2/markets'; // Query params excluded
const message = timestamp + method + path;
const signature = signRSAPSS(message, privateKey); // RSA-PSS with SHA-256
```

**SDK Handles This Automatically:**

We'll use the official `kalshi-typescript` SDK (npm package) which encapsulates RSA-PSS signing.

**⚠️ Note:** The SDK exports `Configuration` and API-specific classes (e.g., `PortfolioApi`, `MarketApi`), not a unified `KalshiClient`. Exact API surface should be verified at implementation time by reviewing the SDK's TypeScript definitions.

**Example SDK initialization pattern (verify exact API at implementation):**

```typescript
import { Configuration, MarketApi, PortfolioApi } from 'kalshi-typescript';

const config = new Configuration({
  apiKey: process.env.KALSHI_API_KEY_ID,
  privateKeyPath: process.env.KALSHI_PRIVATE_KEY_PATH, // Path to .pem file
  basePath: 'https://demo-api.kalshi.co',
});

const marketApi = new MarketApi(config);
const portfolioApi = new PortfolioApi(config);
```

**Alternative:** If SDK provides a unified client class, use that. Check SDK documentation and TypeScript types during implementation.

**Environment Variables:**
```env
KALSHI_API_KEY_ID=your-key-id-here              # Public Key ID from Kalshi dashboard
KALSHI_PRIVATE_KEY_PATH=/path/to/private.pem    # RSA private key in PEM format
KALSHI_API_BASE_URL=https://demo-api.kalshi.co  # Demo environment
# Production: https://trading-api.kalshi.com OR https://api.elections.kalshi.com
```

**Obtaining Credentials:**
1. Sign up at https://demo.kalshi.co
2. Navigate to API settings in dashboard
3. Generate API key pair → download private key (.pem file)
4. Store .pem file securely (NOT in git)
5. Add .pem path to environment variables

**Critical:** Always use demo environment for development. Production API requires real funds.

#### REST API Endpoints (Core Subset for MVP)

**Base URL:** `https://demo-api.kalshi.co/trade-api/v2/`
**⚠️ Note:** Path includes `/trade-api/v2/` not just `/v1/`

**SDK Methods (auto-generated from OpenAPI spec):**

The `kalshi-typescript` SDK provides typed methods:

```typescript
// Markets
await client.GetMarkets({ limit: 100, status: 'open' });
await client.GetMarket({ ticker: 'CPI-22DEC-TN0.1' });

// Orderbook
await client.GetMarketOrderbook({ ticker: 'CPI-22DEC-TN0.1', depth: 10 });

// Portfolio
await client.GetPositions();
await client.GetPortfolioBalance();

// Orders (placeholder for Epic 5)
await client.CreateOrder({ /* ... */ });
await client.CancelOrder({ order_id: 'abc123' });
```

**Response Format:**
```json
{
  "cursor": "next_page_token",  // For pagination
  "markets": [ /* array of market objects */ ]
}
```

**Error Response:**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid API key",
    "details": { /* additional context */ }
  }
}
```

#### Rate Limits (Critical for FR-PI-03, FR-PI-04)

**⚠️ Kalshi uses TIERED rate limits with SEPARATE read/write buckets:**

| Tier | Read Limit (req/s) | Write Limit (req/s) |
|------|-------------------|---------------------|
| **Basic** | 20 | 10 |
| **Advanced** | 30 | 30 |
| **Premier** | 100 | 100 |
| **Prime** | 400 | 400 |

**Write limits** apply only to order-related endpoints:
- CreateOrder, CancelOrder, AmendOrder, BatchCreateOrders, BatchCancelOrders

**Read limits** apply to all other endpoints:
- GetMarkets, GetMarketOrderbook, GetPositions, etc.

**Implementation Requirements:**

From architecture and PRD:
- Track **separate read and write** request counts
- Alert at **70% utilization** (FR-PI-04) on EITHER bucket
- Enforce **20% safety buffer** (FR-PI-03) = use only 80% of published limit
- Example: Basic tier (20r/10w) → enforce max 16r/8w per second
- **Assume Basic tier for MVP** (most restrictive, safest default)

**Dual-Bucket Token Bucket Pattern:**

```typescript
// src/common/utils/rate-limiter.ts
class RateLimiter {
  private readTokens: number;
  private writeTokens: number;
  private lastRefill: number;

  constructor(
    private readonly maxReadTokens: number,  // e.g., 16 (80% of 20)
    private readonly maxWriteTokens: number, // e.g., 8 (80% of 10)
    private readonly refillRate: number = 1, // refill every second
  ) {
    this.readTokens = maxReadTokens;
    this.writeTokens = maxWriteTokens;
    this.lastRefill = Date.now();
  }

  async acquireRead(): Promise<void> {
    this.refill();
    await this.acquire('read', this.readTokens, this.maxReadTokens);
    this.readTokens--;
  }

  async acquireWrite(): Promise<void> {
    this.refill();
    await this.acquire('write', this.writeTokens, this.maxWriteTokens);
    this.writeTokens--;
  }

  private async acquire(type: 'read' | 'write', tokens: number, maxTokens: number): Promise<void> {
    const utilization = 1 - tokens / maxTokens;
    if (utilization >= 0.7) {
      logger.warn({
        message: 'Rate limit utilization high',
        module: 'connector',
        type,
        utilization: `${(utilization * 100).toFixed(1)}%`,
        tokensRemaining: tokens,
      });
    }

    if (tokens < 1) {
      const waitMs = (1 / this.refillRate) * 1000;
      await new Promise(resolve => setTimeout(resolve, waitMs));
      this.refill();
    }
  }

  private refill(): void {
    const now = Date.now();
    const elapsed = (now - this.lastRefill) / 1000;
    const tokensToAdd = elapsed * this.refillRate;

    this.readTokens = Math.min(this.maxReadTokens, this.readTokens + tokensToAdd);
    this.writeTokens = Math.min(this.maxWriteTokens, this.writeTokens + tokensToAdd);
    this.lastRefill = now;
  }

  getUtilization(): { read: number; write: number } {
    return {
      read: (1 - this.readTokens / this.maxReadTokens) * 100,
      write: (1 - this.writeTokens / this.maxWriteTokens) * 100,
    };
  }
}
```

**Configuration (Basic tier with 20% buffer):**
```typescript
const rateLimiter = new RateLimiter(
  16, // 80% of 20 read req/s
  8,  // 80% of 10 write req/s
  1,  // refill every second
);
```

#### WebSocket Connection (Real-Time Order Books)

**WebSocket URL:** `wss://demo-api.kalshi.co/trade-api/v2/ws`

**⚠️ Authentication:** Use RSA-PSS headers during WebSocket handshake

Unlike REST, WebSocket authentication requires passing the same three headers (`KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-SIGNATURE`, `KALSHI-ACCESS-TIMESTAMP`) during the initial connection handshake.

**🚨 DESIGN DECISION: WebSocket Handshake Signing**

The `kalshi-typescript` SDK handles RSA-PSS signing for REST API calls, but **may not provide WebSocket support or a standalone signing utility**. There are three approaches:

1. **Check if SDK exposes a signing function** - If `Configuration` or another class exports a `signRequest(timestamp, method, path)` method, use it
2. **Reuse SDK's internal crypto module** - If SDK internals can be imported (check TypeScript definitions), leverage them
3. **Implement minimal signing function** - If neither works, implement RSA-PSS signing in `kalshi-websocket.client.ts` using Node.js `crypto` module

**This is the ONE case where manual RSA-PSS signing is acceptable** - WebSocket handshake auth has no alternative. Scope it narrowly:

```typescript
// src/connectors/kalshi/kalshi-websocket.client.ts
import { createSign } from 'crypto';
import { readFileSync } from 'fs';
import WebSocket from 'ws';

class KalshiWebSocketClient {
  private signHandshake(timestamp: string, path: string): string {
    const message = `${timestamp}GET${path}`;
    const privateKey = readFileSync(this.privateKeyPath, 'utf-8');

    const sign = createSign('RSA-SHA256');
    sign.update(message);
    sign.end();

    const signature = sign.sign({
      key: privateKey,
      padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
      saltLength: crypto.constants.RSA_PSS_SALTLEN_DIGEST,
    }, 'base64');

    return signature;
  }

  async connect(): Promise<void> {
    const timestamp = Date.now().toString();
    const path = '/trade-api/v2/ws';
    const signature = this.signHandshake(timestamp, path);

    const ws = new WebSocket(`wss://demo-api.kalshi.co${path}`, {
      headers: {
        'KALSHI-ACCESS-KEY': this.apiKeyId,
        'KALSHI-ACCESS-TIMESTAMP': timestamp,
        'KALSHI-ACCESS-SIGNATURE': signature,
      },
    });

    // ... rest of connection logic
  }
}
```

**Implementation Note:** During Task 7, verify if SDK provides a signing utility first. Only implement manual signing if necessary.

**Connection Flow:**
1. Generate RSA-PSS signature for WebSocket handshake
2. Connect to WebSocket URL with auth headers
3. Subscribe to `orderbook_delta` channel
4. Receive `orderbook_snapshot` (initial state)
5. Receive `orderbook_delta` messages (incremental updates)
6. Maintain local orderbook state by applying deltas

**Subscribe Message Format:**
```json
{
  "id": 1,
  "cmd": "subscribe",
  "params": {
    "channels": ["orderbook_delta"],
    "market_ticker": "CPI-22DEC-TN0.1"
  }
}
```

**Orderbook Snapshot Message (example - verify against actual API):**
```json
{
  "msg": {
    "seq": 12345,
    "market_ticker": "CPI-22DEC-TN0.1",
    "yes": [[62, 1000], [61, 500]],      // [price_in_cents, quantity]
    "no": [[38, 800], [39, 600]],        // [price_in_cents, quantity]
    "yes_dollars": 15000,                // Total YES bid size in dollars (may be array)
    "no_dollars": 12000                  // Total NO bid size in dollars (may be array)
  },
  "type": "orderbook_snapshot",
  "sid": 1
}
```

**Orderbook Delta Message (example - verify against actual API):**
```json
{
  "msg": {
    "seq": 12346,
    "market_ticker": "CPI-22DEC-TN0.1",
    "price": 63,        // Price in cents (may include price_dollars field)
    "delta": 200,       // Quantity change (positive = added, negative = removed)
    "delta_fp": 2.00,   // May include floating-point delta field
    "side": "yes"       // "yes" or "no"
  },
  "type": "orderbook_delta",
  "sid": 1
}
```

**⚠️ IMPORTANT:** These message formats are examples based on documentation review. **Verify exact field names and structure** against Kalshi's current AsyncAPI specification or by examining actual WebSocket messages during implementation. The API may include additional fields (e.g., `market_id`, `price_dollars`, `delta_fp`) not shown in these simplified examples.

**⚠️ CRITICAL: Delta-Based State Maintenance**

Kalshi's WebSocket provides **incremental updates**, not full snapshots. The client must:

1. Store initial snapshot in local state
2. Apply each delta sequentially:
   - If `delta > 0`: Add/update price level
   - If `delta < 0`: Remove quantity (or entire level if goes to 0)
3. Track sequence numbers to detect missed messages
4. Request new snapshot if sequence gap detected

**Orderbook Structure - YES/NO Bids Only:**

Kalshi uses YES/NO bid structure (NO asks):
- **YES bids**: Bids to buy YES at price X cents
- **NO bids**: Bids to buy NO at price (100 - X) cents
- **No separate "asks"** - A NO bid at 40¢ is equivalent to a YES ask at 60¢ (reciprocal relationship)

**Reconnection Requirements:**

From architecture (NFR-I3):
> Auto-reconnecting WebSockets (exponential backoff, max 60s)

**Reconnection Pattern:**
- Disconnect detected → wait 1s → reconnect attempt 1
- Fail → wait 2s → reconnect attempt 2
- Fail → wait 4s → reconnect attempt 3
- ...continue doubling until 60s max delay
- Keep attempting indefinitely (use `RETRY_STRATEGIES.WEBSOCKET_RECONNECT`)
- **After reconnection**: Request fresh snapshot, reset local state

**Logging Requirements:**
- Log every disconnect with reason
- Log every reconnection attempt with attempt count and delay
- Log successful reconnection with sequence number
- Log sequence gaps (trigger snapshot refresh)

### 📋 Architecture Compliance - File Structure

From `architecture.md#Complete Project Directory Structure`:

```
src/
├── common/
│   ├── interfaces/
│   │   ├── platform-connector.interface.ts    # NEW - IPlatformConnector
│   │   └── index.ts                            # NEW - Export barrel
│   ├── errors/
│   │   ├── system-error.ts                     # NEW - Base error class
│   │   ├── platform-api-error.ts               # NEW - 1000-1999 codes
│   │   └── index.ts                            # NEW - Export barrel
│   ├── types/
│   │   ├── normalized-order-book.type.ts       # NEW - Core data contract
│   │   ├── platform.type.ts                    # NEW - PlatformId enum, OrderParams, etc.
│   │   └── index.ts                            # NEW - Export barrel
│   ├── constants/
│   │   ├── error-codes.ts                      # NEW - 1001-1007 Kalshi codes
│   │   ├── platform.ts                         # NEW - PlatformId.KALSHI
│   │   └── index.ts                            # NEW - Export barrel
│   └── utils/
│       ├── with-retry.ts                       # NEW - Retry utility
│       └── index.ts                            # NEW - Export barrel
├── connectors/
│   ├── connector.module.ts                     # NEW - Module definition
│   └── kalshi/
│       ├── kalshi.connector.ts                 # NEW - IPlatformConnector implementation (wraps SDK + WebSocket)
│       ├── kalshi.connector.spec.ts            # NEW - Unit tests
│       ├── kalshi-websocket.client.ts          # NEW - WebSocket client (delta state management)
│       ├── kalshi-websocket.client.spec.ts     # NEW - Unit tests
│       └── kalshi.types.ts                     # NEW - Kalshi-specific types (YES/NO orderbook structures)
```

**Critical:** Do NOT deviate from this structure. These file locations are referenced throughout the architecture and future stories depend on them.

### 🔧 Previous Story Learnings (Stories 1.1 & 1.2)

#### Key Patterns Established

**1. Structured Logging Pattern (Story 1.2)**

From Story 1.2's implementation, all logs use structured format:

```typescript
this.logger.log({
  message: 'Kalshi connection established',
  module: 'connector',
  timestamp: new Date().toISOString(),
  platformId: 'kalshi',
  metadata: {
    baseUrl: this.apiBaseUrl,
    websocketConnected: true,
  },
});
```

**Required fields:** `message`, `module`, `timestamp`
**Optional:** `metadata` object for additional context

**2. NestJS Module Pattern (Stories 1.1 & 1.2)**

From Story 1.2's CoreModule:

```typescript
@Module({
  imports: [/* dependencies */],
  providers: [/* services */],
  exports: [/* exposed services */],
})
export class ConnectorModule {}
```

Import into AppModule:
```typescript
@Module({
  imports: [
    ConfigModule.forRoot({ /* ... */ }),
    CoreModule,
    ConnectorModule, // ADD THIS
  ],
  // ...
})
export class AppModule {}
```

**3. ConfigService Injection Pattern (Story 1.2)**

```typescript
constructor(
  private readonly configService: ConfigService,
) {
  this.apiKeyId = this.configService.get<string>('KALSHI_API_KEY_ID');
  this.privateKeyPath = this.configService.get<string>('KALSHI_PRIVATE_KEY_PATH');
  this.apiBaseUrl = this.configService.get<string>(
    'KALSHI_API_BASE_URL',
    'https://demo-api.kalshi.co', // NO /v1 suffix
  );
}
```

**4. Testing Pattern with Vitest + NestJS (Story 1.2)**

```typescript
import { Test, TestingModule } from '@nestjs/testing';
import { ConfigService } from '@nestjs/config';

describe('KalshiConnector', () => {
  let connector: KalshiConnector;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        KalshiConnector,
        {
          provide: ConfigService,
          useValue: {
            get: vi.fn((key: string, defaultValue?: any) => {
              const config = {
                KALSHI_API_KEY_ID: 'test-key-id',
                KALSHI_PRIVATE_KEY_PATH: '/path/to/test.pem',
                KALSHI_API_BASE_URL: 'https://demo-api.kalshi.co',
              };
              return config[key] ?? defaultValue;
            }),
          },
        },
      ],
    }).compile();

    connector = module.get<KalshiConnector>(KalshiConnector);
  });

  it('should be defined', () => {
    expect(connector).toBeDefined();
  });
});
```

**5. Environment Configuration Pattern (Story 1.1)**

`.env.development`:
```env
# Existing from Stories 1.1 & 1.2
NODE_ENV=development
PORT=8080
DATABASE_URL="postgresql://postgres:password@postgres:5433/pmarbitrage?schema=public"
POLLING_INTERVAL_MS=30000

# NEW for Story 1.3 - Kalshi Configuration
KALSHI_API_KEY_ID=your-key-id-here                      # Public Key ID from Kalshi dashboard
KALSHI_PRIVATE_KEY_PATH=./secrets/kalshi-demo-key.pem   # Path to RSA private key (.pem file)
KALSHI_API_BASE_URL=https://demo-api.kalshi.co          # Demo environment (NO /v1 suffix)
```

`.env.example`:
```env
# Kalshi API Configuration
KALSHI_API_KEY_ID=                          # Kalshi API Key ID (get from demo.kalshi.co dashboard)
KALSHI_PRIVATE_KEY_PATH=./secrets/key.pem   # Path to RSA private key in PEM format (NOT committed to git)
KALSHI_API_BASE_URL=https://demo-api.kalshi.co  # Demo: demo-api.kalshi.co | Prod: trading-api.kalshi.com
```

**⚠️ CRITICAL: .pem File Security**

Add to `.gitignore`:
```gitignore
# Kalshi credentials
secrets/
*.pem
```

Create `secrets/` directory structure:
```bash
mkdir -p secrets
# Place kalshi-demo-key.pem in secrets/ directory
chmod 600 secrets/kalshi-demo-key.pem  # Restrict file permissions
```

#### Critical Deviations from Previous Stories

**Story 1.1 Deviation - PrismaService Location:**
> Implemented in `src/common/prisma.service.ts` instead of `src/persistence/prisma.service.ts`. Later moved to `src/common/persistence.module.ts` in Story 1.2.

**Impact for Story 1.3:** Use `PersistenceModule` (from Story 1.2) if database access needed. For this story, connectors are stateless - no direct database access required.

### 🎨 Key Implementation Decisions

#### Decision 0: Use Official Kalshi SDK vs Manual Implementation

**Question:** Implement RSA-PSS signing manually or use `kalshi-typescript` SDK?

**Decision:** **Use `kalshi-typescript` SDK (v2.1.3+)** for REST API, manual WebSocket client

**Rationale:**
- **Auth is cryptographic plumbing, not business logic** - RSA-PSS signing is complex with real security risk if implemented incorrectly
- **SDK is official and maintained** - Auto-generated from Kalshi's OpenAPI spec, tracks API changes
- **Full control maintained** - SDK wrapped behind `IPlatformConnector` interface, can swap later if needed
- **WebSocket still manual** - SDK may not handle delta-based orderbook well, manual client gives us full control over state management
- **Architecture compliance** - "Full control over dependencies" refers to avoiding opinionated community boilerplate, not rejecting vendor auth libraries

**Implementation Pattern:**
```typescript
// Wrap SDK behind our interface
export class KalshiConnector implements IPlatformConnector {
  private readonly client: KalshiClient;
  private readonly wsClient: KalshiWebSocketClient; // Manual implementation

  constructor(config: ConfigService) {
    // SDK handles REST + auth
    this.client = new KalshiClient({
      apiKey: config.get('KALSHI_API_KEY_ID'),
      privateKeyPath: config.get('KALSHI_PRIVATE_KEY_PATH'),
      baseUrl: config.get('KALSHI_API_BASE_URL'),
    });

    // Manual WebSocket for delta-based orderbook
    this.wsClient = new KalshiWebSocketClient(/* ... */);
  }

  async getOrderBook(contractId: string): Promise<NormalizedOrderBook> {
    const rawOrderBook = await this.client.GetMarketOrderbook({ ticker: contractId });
    return this.normalizeOrderBook(rawOrderBook); // Transform YES/NO to standard format
  }

  // ... other methods
}
```

#### Decision 1: IPlatformConnector Interface - Complete vs Placeholder Methods

**Question:** Should all interface methods be fully implemented in Story 1.3, or can some be placeholders?

**Decision:** **Hybrid approach** based on acceptance criteria:

**MUST be fully functional:**
- `connect()` - Establish REST and WebSocket connections
- `disconnect()` - Clean shutdown
- `getOrderBook()` - REST API call for order book snapshot
- `getHealth()` - Connection status check
- `getPlatformId()` - Return `PlatformId.KALSHI`
- `getFeeSchedule()` - Return Kalshi fee structure
- `onOrderBookUpdate()` - WebSocket subscription callback

**CAN be placeholder implementations:**
- `submitOrder()` - Not needed until Epic 5 (Trade Execution)
- `cancelOrder()` - Not needed until Epic 5
- `getPositions()` - Not needed until Epic 5

**Placeholder pattern:**
```typescript
async submitOrder(params: OrderParams): Promise<OrderResult> {
  throw new Error('submitOrder not implemented - Epic 5 Story 5.1');
}
```

**Rationale:**
- Story 1.3 acceptance criteria focus on **connectivity and authentication**
- Order submission comes in Epic 5 when execution module is built
- Interface completeness allows future stories to inject connector immediately
- Placeholder methods prevent silent failures if accidentally called early

#### Decision 2: Rate Limit Implementation - Dual-Bucket Token Bucket

**Question:** How to enforce Kalshi's tiered read/write rate limits with 70% alert and 20% buffer?

**Decision:** **Dual-bucket token bucket algorithm** (separate read/write buckets) with Basic tier default

**Rationale:**
- Kalshi uses **separate read and write limits** (Basic: 20r/10w req/s)
- PRD explicitly requires "20% safety buffer" (FR-PI-03) → enforce 16r/8w on Basic
- Architecture specifies "alert at 70% utilization" (FR-PI-04) on EITHER bucket
- Token bucket naturally models rate limits with bursts
- Tier-aware design allows easy upgrade to Advanced/Premier later
- Production-grade pattern worth implementing once correctly

**Location:** `src/common/utils/rate-limiter.ts` (shared utility, not Kalshi-specific)

**Tier Configuration:**
```typescript
export const RATE_LIMIT_TIERS = {
  BASIC: { read: 20, write: 10 },
  ADVANCED: { read: 30, write: 30 },
  PREMIER: { read: 100, write: 100 },
  PRIME: { read: 400, write: 400 },
} as const;

// With 20% safety buffer
export const ENFORCED_LIMITS = {
  BASIC: { read: 16, write: 8 },
  ADVANCED: { read: 24, write: 24 },
  PREMIER: { read: 80, write: 80 },
  PRIME: { read: 320, write: 320 },
} as const;
```

**Implementation:** (See updated code in Rate Limits section above)

#### Decision 3: WebSocket State Management - Delta Application with Snapshot Reset

**Question:** How to handle Kalshi's delta-based orderbook updates reliably?

**Decision:** **Maintain local orderbook state, apply deltas sequentially, reset on reconnection**

**Rationale:**
- Kalshi's WebSocket provides **incremental updates** (orderbook_delta), not full snapshots
- Must maintain local state to construct full orderbook view
- Sequence numbers detect missed messages → trigger snapshot refresh
- Reconnection invalidates state → must request fresh snapshot
- This pattern is standard for exchange APIs (prevents bandwidth waste)

**State Management Pattern:**
```typescript
class KalshiWebSocketClient {
  private orderbookState: Map<string, OrderbookSnapshot> = new Map();
  private lastSequence: number = 0;

  private handleSnapshot(msg: OrderbookSnapshotMessage): void {
    const { ticker, seq, yes, no } = msg.msg;
    this.orderbookState.set(ticker, { seq, yes, no });
    this.lastSequence = seq;
  }

  private handleDelta(msg: OrderbookDeltaMessage): void {
    const { seq, price, delta, side } = msg.msg;

    // Sequence gap detection
    if (seq !== this.lastSequence + 1) {
      this.logger.warn({
        message: 'Sequence gap detected, requesting snapshot',
        expected: this.lastSequence + 1,
        received: seq,
      });
      this.requestSnapshot();
      return;
    }

    // Apply delta to local state
    const state = this.orderbookState.get(msg.ticker);
    if (!state) {
      this.requestSnapshot();
      return;
    }

    this.applyDelta(state, price, delta, side);
    this.lastSequence = seq;

    // Emit updated orderbook to subscribers
    this.emit('orderbook', this.transformToNormalized(state));
  }

  private applyDelta(state: OrderbookSnapshot, price: number, delta: number, side: 'yes' | 'no'): void {
    const levels = side === 'yes' ? state.yes : state.no;
    const levelIndex = levels.findIndex(([p]) => p === price);

    if (delta > 0) {
      // Add or update price level
      if (levelIndex >= 0) {
        levels[levelIndex][1] += delta;
      } else {
        levels.push([price, delta]);
        levels.sort((a, b) => b[0] - a[0]); // Descending price order
      }
    } else {
      // Remove quantity
      if (levelIndex >= 0) {
        levels[levelIndex][1] += delta; // delta is negative
        if (levels[levelIndex][1] <= 0) {
          levels.splice(levelIndex, 1); // Remove level if quantity goes to 0
        }
      }
    }
  }
}
```

**Reconnection Pattern:**
- Disconnect detected → wait 1s → reconnect attempt 1
- Fail → wait 2s → reconnect attempt 2
- Fail → wait 4s → reconnect attempt 3
- ...continue doubling until 60s max delay
- Keep attempting indefinitely (use `RETRY_STRATEGIES.WEBSOCKET_RECONNECT`)
- **On successful reconnection:** Clear old state, subscribe, wait for fresh snapshot

### ✅ Testing Strategy

#### Unit Tests Required

**1. SystemError & PlatformApiError Tests**

```typescript
// src/common/errors/system-error.spec.ts
describe('SystemError', () => {
  it('should create error with all properties', () => {
    const error = new PlatformApiError(
      1001,
      'Unauthorized',
      PlatformId.KALSHI,
      'critical',
    );
    expect(error.code).toBe(1001);
    expect(error.severity).toBe('critical');
    expect(error.platformId).toBe(PlatformId.KALSHI);
  });
});
```

**2. withRetry() Utility Tests**

```typescript
// src/common/utils/with-retry.spec.ts
describe('withRetry', () => {
  it('should succeed on first try', async () => {
    const fn = vi.fn().mockResolvedValue('success');
    const result = await withRetry(fn, RETRY_STRATEGIES.NETWORK_ERROR);
    expect(result).toBe('success');
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('should retry on failure with exponential backoff', async () => {
    const fn = vi.fn()
      .mockRejectedValueOnce(new Error('fail1'))
      .mockRejectedValueOnce(new Error('fail2'))
      .mockResolvedValue('success');

    const result = await withRetry(fn, RETRY_STRATEGIES.NETWORK_ERROR);
    expect(result).toBe('success');
    expect(fn).toHaveBeenCalledTimes(3);
  });

  it('should throw after max retries', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('fail'));
    await expect(
      withRetry(fn, { maxRetries: 2, initialDelayMs: 10, maxDelayMs: 100, backoffMultiplier: 2 })
    ).rejects.toThrow('fail');
    expect(fn).toHaveBeenCalledTimes(3); // initial + 2 retries
  });
});
```

**3. RateLimiter Tests (Dual-Bucket)**

```typescript
// src/common/utils/rate-limiter.spec.ts
describe('RateLimiter', () => {
  let limiter: RateLimiter;
  const mockLogger = { warn: vi.fn(), log: vi.fn() };

  beforeEach(() => {
    limiter = new RateLimiter(16, 8); // Basic tier: 16 read, 8 write
    vi.clearAllMocks();
  });

  it('should allow read requests within limit', async () => {
    await limiter.acquireRead();
    const utilization = limiter.getUtilization();
    expect(utilization.read).toBeLessThan(10); // <10% utilization
  });

  it('should allow write requests within limit', async () => {
    await limiter.acquireWrite();
    const utilization = limiter.getUtilization();
    expect(utilization.write).toBeLessThan(20); // <20% utilization
  });

  it('should emit alert at 70% read utilization', async () => {
    // Consume 70% of read tokens (11/16 = 68.75%)
    for (let i = 0; i < 11; i++) {
      await limiter.acquireRead();
    }

    expect(mockLogger.warn).toHaveBeenCalledWith(
      expect.objectContaining({
        message: 'Rate limit utilization high',
        type: 'read',
      })
    );
  });

  it('should emit alert at 70% write utilization', async () => {
    // Consume 70% of write tokens (6/8 = 75%)
    for (let i = 0; i < 6; i++) {
      await limiter.acquireWrite();
    }

    expect(mockLogger.warn).toHaveBeenCalledWith(
      expect.objectContaining({
        message: 'Rate limit utilization high',
        type: 'write',
      })
    );
  });

  it('should track read and write buckets separately', async () => {
    // Exhaust write tokens
    for (let i = 0; i < 8; i++) {
      await limiter.acquireWrite();
    }

    // Read bucket should still have tokens
    await limiter.acquireRead(); // Should not block
    const utilization = limiter.getUtilization();
    expect(utilization.read).toBeLessThan(10);
    expect(utilization.write).toBeGreaterThan(90);
  });
});
```

**4. Kalshi SDK Wrapper Tests**

```typescript
// src/connectors/kalshi/kalshi.connector.spec.ts (SDK integration tests)
describe('KalshiConnector - SDK Integration', () => {
  let connector: KalshiConnector;
  let mockClient: any;

  beforeEach(async () => {
    // Mock the SDK client
    mockClient = {
      GetMarkets: vi.fn(),
      GetMarketOrderbook: vi.fn(),
      GetPositions: vi.fn(),
    };

    const module = await Test.createTestingModule({
      providers: [
        KalshiConnector,
        {
          provide: ConfigService,
          useValue: {
            get: vi.fn((key: string) => {
              const config = {
                KALSHI_API_KEY_ID: 'test-key-id',
                KALSHI_PRIVATE_KEY_PATH: '/path/to/test.pem',
                KALSHI_API_BASE_URL: 'https://demo-api.kalshi.co',
              };
              return config[key];
            }),
          },
        },
      ],
    }).compile();

    connector = module.get<KalshiConnector>(KalshiConnector);
    // Inject mocked SDK client
    (connector as any).client = mockClient;
  });

  it('should call SDK GetMarketOrderbook method', async () => {
    mockClient.GetMarketOrderbook.mockResolvedValue({
      orderbook: {
        yes: [[62, 1000], [61, 500]],
        no: [[38, 800], [39, 600]],
      },
    });

    const orderbook = await connector.getOrderBook('CPI-22DEC-TN0.1');

    expect(mockClient.GetMarketOrderbook).toHaveBeenCalledWith({
      ticker: 'CPI-22DEC-TN0.1',
      depth: 10,
    });
    expect(orderbook).toBeDefined();
  });

  it('should transform YES/NO bids to NormalizedOrderBook format', async () => {
    mockClient.GetMarketOrderbook.mockResolvedValue({
      orderbook: {
        yes: [[62, 1000]],  // 62¢ YES bid
        no: [[38, 800]],    // 38¢ NO bid = 62¢ YES ask
      },
    });

    const orderbook = await connector.getOrderBook('CPI-22DEC-TN0.1');

    // Verify transformation (Story 1.4 will define exact format)
    expect(orderbook).toHaveProperty('bids');
    expect(orderbook).toHaveProperty('asks');
  });

  it('should throw PlatformApiError on SDK error', async () => {
    mockClient.GetMarketOrderbook.mockRejectedValue(
      new Error('API error: UNAUTHORIZED')
    );

    await expect(connector.getOrderBook('CPI-22DEC-TN0.1'))
      .rejects.toThrow(PlatformApiError);
  });
});
```

**5. KalshiWebSocketClient Tests**

```typescript
// src/connectors/kalshi/kalshi-websocket.client.spec.ts
describe('KalshiWebSocketClient', () => {
  let client: KalshiWebSocketClient;
  let mockWS: any;

  beforeEach(() => {
    mockWS = {
      send: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      readyState: WebSocket.OPEN,
    };
    global.WebSocket = vi.fn(() => mockWS) as any;
  });

  it('should connect with RSA-PSS auth headers', async () => {
    client = new KalshiWebSocketClient({
      apiKeyId: 'test-key-id',
      privateKeyPath: '/path/to/test.pem',
      url: 'wss://demo-api.kalshi.co/trade-api/v2/ws',
    });

    await client.connect();

    expect(global.WebSocket).toHaveBeenCalledWith(
      'wss://demo-api.kalshi.co/trade-api/v2/ws',
      expect.objectContaining({
        headers: expect.objectContaining({
          'KALSHI-ACCESS-KEY': 'test-key-id',
          'KALSHI-ACCESS-SIGNATURE': expect.any(String),
          'KALSHI-ACCESS-TIMESTAMP': expect.any(String),
        }),
      })
    );
  });

  it('should subscribe to orderbook_delta channel', async () => {
    await client.connect();
    await client.subscribe('CPI-22DEC-TN0.1');

    expect(mockWS.send).toHaveBeenCalledWith(
      JSON.stringify({
        id: 1,
        cmd: 'subscribe',
        params: {
          channels: ['orderbook_delta'],
          market_ticker: 'CPI-22DEC-TN0.1',
        },
      })
    );
  });

  it('should apply deltas to local orderbook state', () => {
    const snapshot = {
      yes: [[62, 1000], [61, 500]],
      no: [[38, 800]],
    };

    const delta = {
      price: 63,
      delta: 200,
      side: 'yes',
    };

    client.applyDelta(snapshot, delta);

    expect(snapshot.yes).toContainEqual([63, 200]);
  });

  it('should detect sequence gaps and request snapshot', () => {
    client.handleDelta({ msg: { seq: 100 }, type: 'orderbook_delta' });
    client.handleDelta({ msg: { seq: 105 }, type: 'orderbook_delta' }); // Gap!

    expect(mockWS.send).toHaveBeenCalledWith(
      expect.stringContaining('snapshot')
    );
  });

  it('should trigger reconnect on disconnect with exponential backoff', async () => {
    vi.useFakeTimers();

    const disconnectHandler = mockWS.addEventListener.mock.calls.find(
      call => call[0] === 'close'
    )?.[1];

    disconnectHandler();

    // First retry after 1s
    vi.advanceTimersByTime(1000);
    expect(global.WebSocket).toHaveBeenCalledTimes(2);

    // Second retry after 2s
    vi.advanceTimersByTime(2000);
    expect(global.WebSocket).toHaveBeenCalledTimes(3);

    vi.useRealTimers();
  });
});
```

**6. KalshiConnector Integration Tests**

```typescript
// src/connectors/kalshi/kalshi.connector.spec.ts
describe('KalshiConnector', () => {
  let connector: KalshiConnector;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [
        KalshiConnector,
        {
          provide: ConfigService,
          useValue: {
            get: vi.fn((key: string) => {
              const config = {
                KALSHI_API_KEY_ID: 'test-key-id',
                KALSHI_PRIVATE_KEY_PATH: '/path/to/test.pem',
                KALSHI_API_BASE_URL: 'https://demo-api.kalshi.co',
              };
              return config[key];
            }),
          },
        },
      ],
    }).compile();

    connector = module.get<KalshiConnector>(KalshiConnector);
  });

  it('should implement IPlatformConnector interface', () => {
    expect(connector.connect).toBeDefined();
    expect(connector.disconnect).toBeDefined();
    expect(connector.getOrderBook).toBeDefined();
    expect(connector.getPlatformId()).toBe(PlatformId.KALSHI);
  });

  it('should establish SDK and WebSocket connections on connect()', async () => {
    // Mock SDK client and WebSocket connections
    await connector.connect();
    expect(connector.getHealth().status).toBe('healthy');
  });

  it('should handle connection failures gracefully', async () => {
    // Mock connection failure
    // Verify PlatformApiError thrown with correct code
  });
});
```

#### E2E Tests Required

```typescript
// test/kalshi-connection.e2e-spec.ts
describe('Kalshi Connection (e2e)', () => {
  let app: INestApplication;
  let connector: KalshiConnector;

  beforeAll(async () => {
    const moduleFixture = await Test.createTestingModule({
      imports: [
        ConfigModule.forRoot({ envFilePath: '.env.test' }),
        ConnectorModule,
      ],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();

    connector = moduleFixture.get<KalshiConnector>(KalshiConnector);
  });

  afterAll(async () => {
    await connector.disconnect();
    await app.close();
  });

  it('should connect to Kalshi demo API', async () => {
    await expect(connector.connect()).resolves.not.toThrow();
    expect(connector.getHealth().status).toBe('healthy');
  }, 10000);

  it('should fetch order book data', async () => {
    await connector.connect();
    const orderBook = await connector.getOrderBook('MARKET-TEST');
    expect(orderBook).toHaveProperty('bids');
    expect(orderBook).toHaveProperty('asks');
  }, 10000);
});
```

**Note:** E2E tests require valid Kalshi demo API credentials in `.env.test`:
- `KALSHI_API_KEY_ID` - Your Key ID from Kalshi dashboard
- `KALSHI_PRIVATE_KEY_PATH` - Path to .pem file (ensure test file has read access)
- `KALSHI_API_BASE_URL` - Use `https://demo-api.kalshi.co` for testing

### 📚 Architecture References

**Primary Sources:**
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3] - Complete acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns] - IPlatformConnector interface specification
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns - Error Handling] - Error hierarchy and codes
- [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns] - Retry utility specification
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] - File naming conventions
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries] - Directory organization

**External Documentation:**
- Kalshi API Documentation: https://kalshi.com/docs (verify latest endpoints and authentication)
- Kalshi Demo Environment: https://demo.kalshi.co (for obtaining test credentials)

### 🎯 Definition of Done Checklist

Before marking Story 1.3 complete, verify:

**✅ Interface & Foundation**
- [ ] `IPlatformConnector` interface defined with all methods
- [ ] `SystemError` base class implemented
- [ ] `PlatformApiError` subclass with Kalshi error codes (1001-1007)
- [ ] `withRetry()` utility implemented with exponential backoff
- [ ] All foundation code has unit tests with 80%+ coverage

**✅ Kalshi Implementation**
- [ ] `KalshiApiClient` authenticates and calls REST endpoints
- [ ] `KalshiWebSocketClient` connects and subscribes to order books
- [ ] `KalshiConnector` implements IPlatformConnector interface
- [ ] Rate limiting enforced with 70% alert and 20% safety buffer
- [ ] WebSocket reconnection with exponential backoff (max 60s)
- [ ] All errors use centralized error hierarchy

**✅ Module Integration**
- [ ] `ConnectorModule` created and exported
- [ ] Module imported into `AppModule`
- [ ] Connector can be injected via DI

**✅ Configuration**
- [ ] `.env.development` has Kalshi credentials
- [ ] `.env.example` documents all Kalshi variables
- [ ] README updated with "Obtaining Kalshi API Credentials" section

**✅ Testing**
- [ ] All unit tests passing (`pnpm test`)
- [ ] E2E test connects to Kalshi demo API
- [ ] All tests passing in CI pipeline
- [ ] Coverage report shows 80%+ on new code

**✅ Logging & Observability**
- [ ] All operations use structured logging
- [ ] Connection events logged (connect, disconnect, reconnect)
- [ ] Rate limit warnings logged at 70% utilization
- [ ] Errors logged with full context

**✅ Documentation**
- [ ] All public methods have TypeDoc comments
- [ ] README section on Kalshi setup
- [ ] No TODO/FIXME comments in production code

### 🚨 Critical Anti-Patterns to Avoid

**❌ DO NOT:**
1. **Use Bearer token authentication** - Kalshi uses RSA-PSS signing, NOT Bearer tokens
2. **Use /v1/ API paths** - Correct path is `/trade-api/v2/`
3. **Assume standard bid/ask orderbook** - Kalshi uses YES/NO bid structure (no asks)
4. **Use single rate limiter** - Must separate read/write buckets
5. **Assume WebSocket provides full snapshots** - It's delta-based, must maintain local state
6. **Implement RSA-PSS signing manually** - Use `kalshi-typescript` SDK
7. **Skip sequence number tracking** - Gaps require snapshot refresh
8. **Implement placeholder methods by returning null/undefined** - Throw explicit errors
9. **Use console.log()** - Always use NestJS Logger with structured format
10. **Hardcode API credentials** - Always use ConfigService
11. **Throw raw Error()** - Use SystemError hierarchy
12. **Implement retry logic inline** - Use withRetry() utility
13. **Put shared code in kalshi/ directory** - Use common/ for cross-platform code
14. **Mix REST and WebSocket logic in one file** - Separate SDK wrapper and WebSocket client

**✅ DO:**
1. **Use kalshi-typescript SDK** - Official, handles auth correctly
2. **Follow interface contract exactly** - IPlatformConnector is the foundation
3. **Transform YES/NO to standard format** - Normalize in connector before returning
4. **Track orderbook deltas with sequence numbers** - Detect gaps, request snapshots
5. **Reset WebSocket state on reconnection** - Old deltas invalid after disconnect
6. **Use structured logging everywhere** - Include module, timestamp, metadata
7. **Test edge cases thoroughly** - Auth failures, sequence gaps, delta application
8. **Document Kalshi-specific quirks** - YES/NO structure, delta updates, tiered limits
9. **Make placeholder methods obvious** - Throw descriptive errors for unimplemented features
10. **Keep .pem files out of git** - Add to .gitignore, use environment variable for path

### 🔄 Next Steps After Completion

1. **Update sprint status:**
   - Change `1-3-kalshi-platform-connector-authentication: backlog` → `done`

2. **Commit the work:**
   ```bash
   git add .
   git commit -m "feat(connectors): implement Kalshi platform connector with authentication

   - Add IPlatformConnector interface defining platform abstraction
   - Implement SystemError hierarchy with PlatformApiError (1001-1007)
   - Add withRetry() utility for exponential backoff resilience
   - Implement KalshiApiClient for REST API with rate limiting
   - Implement KalshiWebSocketClient with auto-reconnection
   - Create KalshiConnector implementing full IPlatformConnector interface
   - Add comprehensive unit and E2E tests
   - Configure Kalshi credentials in environment variables

   Addresses Story 1.3 (Epic 1): Kalshi connectivity foundation

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
   ```

3. **Verify integration:**
   ```bash
   docker-compose up
   # Check logs for "Kalshi connection established"
   # Verify no connection errors
   ```

4. **Proceed to Story 1.4:**
   - Order Book Normalization & Health Monitoring
   - Will consume the Kalshi connector built in this story

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None.

### Completion Notes List

- Implemented `IPlatformConnector` interface with all 10 methods as specified in architecture
- Created `NormalizedOrderBook`, `PlatformId`, `PlatformHealth`, `OrderParams`, `OrderResult`, `CancelResult`, `Position`, `FeeSchedule` types
- Built `SystemError` base class and `PlatformApiError` subclass with Kalshi error codes 1001-1007
- Implemented `withRetry()` utility with exponential backoff and jitter
- Implemented dual-bucket `RateLimiter` with separate read/write limits, 70% alert threshold, 20% safety buffer
- Used `kalshi-typescript` SDK v3.6.0 for REST API authentication (RSA-PSS handled by SDK's BaseAPI)
- `KalshiAuth` is not exported from SDK's public API — implemented RSA-PSS signing directly in `KalshiWebSocketClient` using Node.js `crypto` module for WebSocket handshake auth
- WebSocket client maintains local orderbook state via delta application with sequence gap detection
- Placeholder methods (`submitOrder`, `cancelOrder`, `getPositions`) throw `PlatformApiError` — will be implemented in Epic 5
- All 74 tests passing (27 new tests for this story), lint clean
- `PortfolioApi` and `OrdersApi` imports removed for now to satisfy `noUnusedLocals` — will be added back in Epic 5

### File List

New files:
- `pm-arbitrage-engine/src/common/types/platform.type.ts`
- `pm-arbitrage-engine/src/common/types/normalized-order-book.type.ts`
- `pm-arbitrage-engine/src/common/types/index.ts`
- `pm-arbitrage-engine/src/common/interfaces/platform-connector.interface.ts`
- `pm-arbitrage-engine/src/common/interfaces/index.ts`
- `pm-arbitrage-engine/src/common/errors/system-error.ts`
- `pm-arbitrage-engine/src/common/errors/platform-api-error.ts`
- `pm-arbitrage-engine/src/common/errors/platform-api-error.spec.ts`
- `pm-arbitrage-engine/src/common/errors/index.ts`
- `pm-arbitrage-engine/src/common/utils/with-retry.ts`
- `pm-arbitrage-engine/src/common/utils/with-retry.spec.ts`
- `pm-arbitrage-engine/src/common/utils/rate-limiter.ts`
- `pm-arbitrage-engine/src/common/utils/rate-limiter.spec.ts`
- `pm-arbitrage-engine/src/common/utils/index.ts`
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi.types.ts`
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-sdk.d.ts`
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-websocket.client.ts`
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-websocket.client.spec.ts`
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts`
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.spec.ts`
- `pm-arbitrage-engine/src/connectors/connector.module.ts`

Modified files:
- `pm-arbitrage-engine/src/app.module.ts` (added ConnectorModule import)
- `pm-arbitrage-engine/.env.development` (added Kalshi env vars, placeholder key)
- `pm-arbitrage-engine/.env.example` (added Kalshi env vars)
- `pm-arbitrage-engine/.gitignore` (added secrets/ and *.pem)
- `pm-arbitrage-engine/package.json` (added ws, kalshi-typescript, @vitest/coverage-v8 deps)
