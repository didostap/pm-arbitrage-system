# Story 1.4: Order Book Normalization & Health Monitoring

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want Kalshi order book data normalized into the unified internal format with platform health status,
So that I can verify data quality and system health before adding more platforms.

## Acceptance Criteria

**Given** Kalshi sends an order book update
**When** the normalizer processes it
**Then** Kalshi cents are converted to decimal probability (62¢ → 0.62)
**And** the normalized output matches the PRD's `NormalizedOrderBook` schema (platform, contract_id, best_bid, best_ask, fees, timestamp, platform_health)
**And** normalization completes within 500ms (95th percentile) (FR-DI-02)

**Given** a normalized price is produced
**When** validation runs
**Then** prices outside 0.00-1.00 range are rejected, logged as error, and the opportunity is discarded

**Given** the platform health service is running
**When** 30 seconds elapse
**Then** health status is published (healthy/degraded/offline) based on API response time, update frequency, and connection state (FR-DI-04)

**Given** no order book update is received for >60 seconds
**When** data staleness is detected
**Then** platform status transitions to "degraded"
**And** a warning-level event is emitted

**Given** the engine needs to persist snapshots
**When** order book data arrives
**Then** snapshots are written to `order_book_snapshots` table (Prisma migration created in this story)
**And** health status is written to `platform_health_logs` table

## Tasks / Subtasks

- [ ] Task 1: Create Prisma migrations for data persistence (AC: Database schema)
  - [ ] Edit `prisma/schema.prisma` - add OrderBookSnapshot model with Json fields for bids/asks
  - [ ] Edit `prisma/schema.prisma` - add PlatformHealthLog model
  - [ ] Run migration: `pnpm prisma migrate dev --name add_order_book_and_health_tables`
  - [ ] Run codegen: `pnpm prisma generate`
  - [ ] Verify tables exist in DB: `pnpm prisma studio`

- [ ] Task 2: Create data-ingestion module structure (AC: Module setup)
  - [ ] Manually create `src/modules/data-ingestion/data-ingestion.module.ts`
  - [ ] Manually create `src/modules/data-ingestion/data-ingestion.service.ts`
  - [ ] Manually create `src/modules/data-ingestion/order-book-normalizer.service.ts`
  - [ ] Manually create `src/modules/data-ingestion/platform-health.service.ts`
  - [ ] Edit `src/app.module.ts` - import DataIngestionModule
  - [ ] Edit `src/app.module.ts` - add `ScheduleModule.forRoot()` to imports array (NEW in Story 1.4)
  - [ ] NOTE: @nestjs/schedule package installed in Story 1.2, but module registration is NEW here

- [ ] Task 3: Implement OrderBookNormalizerService (AC: Price normalization)
  - [ ] Transform Kalshi YES bids array to NormalizedOrderBook.bids (cent → decimal)
  - [ ] Transform Kalshi NO bids array to NormalizedOrderBook.asks (NO 35¢ → YES ask 0.65)
  - [ ] Sort asks ascending (lowest first)
  - [ ] Validate all prices in 0.00-1.00 range, throw PlatformApiError(1007) if invalid
  - [ ] Check for crossed markets (bid > ask), log warning if detected
  - [ ] Track normalization latency with rolling 100-sample window for p95 calculation
  - [ ] Write unit tests: normal case, zero spread, crossed market, empty book, price validation

- [ ] Task 4: Implement PlatformHealthService (AC: Health monitoring)
  - [ ] Add @Cron('*/30 * * * * *') decorator for 30-second health publishing
  - [ ] Implement calculateHealth() with staleness (>60s), latency (>2s), and connection checks
  - [ ] Track previous status in Map to detect transitions (degraded→healthy, healthy→degraded)
  - [ ] Emit PlatformDegradedEvent on degradation transition
  - [ ] Emit PlatformRecoveredEvent on recovery transition (degraded→healthy)
  - [ ] Persist health logs with AWAIT and error handling (not fire-and-forget)
  - [ ] Write unit tests for all state transitions and threshold checks

- [ ] Task 5: Implement DataIngestionService orchestrator (AC: Integration)
  - [ ] Implement onModuleInit() - register WebSocket callback with KalshiConnector.onOrderBookUpdate()
  - [ ] Create processWebSocketUpdate() - normalize, persist, emit event, track latency
  - [ ] Create ingestCurrentOrderBooks() - polling path called by TradingEngineService
  - [ ] Persist snapshots with error handling: await, log failures, track consecutive failures, emit alert if >10
  - [ ] Emit OrderBookUpdatedEvent after successful persistence
  - [ ] Call healthService.recordUpdate() to track latency for health monitoring
  - [ ] Add structured logging for WebSocket and polling paths
  - [ ] Write integration tests

- [ ] Task 6: Update TradingEngineService integration (AC: Pipeline orchestration)
  - [ ] Edit `src/core/trading-engine.service.ts`
  - [ ] Inject DataIngestionService in constructor
  - [ ] Replace executePipelinePlaceholder() with await dataIngestionService.ingestCurrentOrderBooks()
  - [ ] Add comment noting WebSocket updates run in parallel to polling

- [ ] Task 7: Create domain events (AC: Observability)
  - [ ] Create `src/common/events/orderbook.events.ts` with OrderBookUpdatedEvent
  - [ ] Edit `src/common/events/platform.events.ts` - add PlatformDegradedEvent
  - [ ] Edit `src/common/events/platform.events.ts` - add PlatformRecoveredEvent
  - [ ] Edit `src/common/events/platform.events.ts` - add PlatformDisconnectedEvent
  - [ ] Export all events from `src/common/events/index.ts`

- [ ] Task 8: Testing (AC: Comprehensive coverage)
  - [ ] Unit test OrderBookNormalizerService: cent conversion, YES/NO transformation, validation, crossed markets
  - [ ] Unit test PlatformHealthService: state transitions, staleness, latency thresholds, event emission
  - [ ] Unit test DataIngestionService: WebSocket flow, polling flow, persistence error handling
  - [ ] E2E test: Kalshi connector → normalizer → persistence with real demo API
  - [ ] E2E test: Health transitions over time (requires time manipulation or manual trigger)
  - [ ] All tests passing, lint clean

## Dev Notes

### 🎯 Story Context & Critical Mission

This is **Story 1.4** in Epic 1 - the fourth and final connectivity story before moving to Epic 2 (Polymarket). This story is **CRITICAL** because:

1. **First data normalization** - Establishes patterns for transforming platform-specific data into unified format
2. **Health monitoring foundation** - Creates infrastructure for all platform health tracking (Polymarket, future platforms)
3. **First module implementation** - Creates the `data-ingestion` module structure that all future modules will follow
4. **Performance baseline** - 500ms normalization SLA is the foundation for 1-second detection cycle (NFR-P2)
5. **Database schema foundation** - First Prisma migrations for audit trail and compliance (7-year retention)

**⚠️ CRITICAL: This story creates the data pipeline foundation that EVERY downstream module depends on. Normalization correctness and performance are non-negotiable.**

### 🏗️ Architecture Intelligence - Data Normalization & Health

#### The NormalizedOrderBook Contract (System-Wide Foundation)

**⚠️ CRITICAL: Story 1.3 already created this type. Use the ACTUAL implementation, do NOT redefine it.**

From `src/common/types/normalized-order-book.type.ts` (shipped in Story 1.3):

```typescript
export interface PriceLevel {
  price: number;      // Decimal probability 0.00-1.00
  quantity: number;   // Size in contracts/shares
}

export interface NormalizedOrderBook {
  platformId: PlatformId;        // Enum: KALSHI | POLYMARKET (camelCase!)
  contractId: string;             // Platform's contract identifier (camelCase!)
  bids: PriceLevel[];             // Array of bid levels, sorted descending by price
  asks: PriceLevel[];             // Array of ask levels, sorted ascending by price
  timestamp: Date;                // When this snapshot was created
  sequenceNumber?: number;        // Optional sequence tracking for delta updates
}
```

**IMPORTANT DIFFERENCES from epics AC:**

1. **Full depth arrays, not just best prices** - Epic AC says "best_bid, best_ask" but Story 1.3 correctly implemented full depth. This is BETTER for Epic 3's edge calculator which needs "liquidity depth at execution prices" (FR-AD-02).
2. **Field names are camelCase** - `platformId`, `contractId`, NOT `platform_id`
3. **No fees or platform_health in base type** - These will be added separately or in extended types

**Story 1.4 must work with this existing structure.**

**Critical Design Points:**

1. **ALL prices in decimal probability (0.00-1.00)** - Never cents, never basis points, always decimal
2. **Arrays sorted correctly:** bids descending (highest first), asks ascending (lowest first)
3. **Kalshi YES/NO to bids/asks transformation** - see next section for corrected logic
4. **timestamp is creation time, not platform time** - Audit trail uses system time (NTP-synced)

#### Kalshi YES/NO Order Book Transformation Logic

**⚠️ CORRECTED: Previous version had misleading zero-spread examples.**

**Input from Kalshi (via Story 1.3's connector):**

```typescript
// From KalshiConnector.getOrderBook() or WebSocket update
interface KalshiOrderBook {
  market_ticker: string;
  yes: [[price_cents, quantity], ...];  // Sorted descending: [[60, 1000], [59, 500]]
  no: [[price_cents, quantity], ...];   // Sorted descending: [[35, 800], [34, 600]]
}
```

**Realistic Example with Spread:**
- YES bids: [60¢, 59¢, 58¢] → people willing to BUY YES at these prices
- NO bids: [35¢, 34¢, 33¢] → people willing to BUY NO at these prices
- A NO bid at 35¢ means someone will SELL YES at 65¢ (1 - 0.35 = 0.65)
- **Result:** Best bid = 0.60 (highest YES bid), Best ask = 0.65 (lowest YES ask = 1 - highest NO bid)
- **Spread = 0.05 (5 cents)** - this is normal and correct

**⚠️ Why the previous example was wrong:**
- If YES best = 62¢ and NO best = 38¢, then 62 + 38 = 100 → zero spread → locked market
- This is rare and suggests either: (1) about to trade, (2) data issue, or (3) arbitrage opportunity
- The transformation logic is correct, but the example obscured the typical case

**Transformation Algorithm (CORRECTED):**

```typescript
// src/modules/data-ingestion/order-book-normalizer.service.ts
class OrderBookNormalizerService {
  normalize(kalshiBook: KalshiOrderBook): NormalizedOrderBook {
    const startTime = Date.now();

    // 1. Transform YES bids (already in correct format)
    const bids: PriceLevel[] = kalshiBook.yes.map(([priceCents, qty]) => ({
      price: priceCents / 100,  // 60¢ → 0.60
      quantity: qty,
    }));

    // 2. Transform NO bids to YES asks
    // NO bid at 35¢ = someone will sell YES at 65¢ (1 - 0.35)
    const asks: PriceLevel[] = kalshiBook.no.map(([priceCents, qty]) => ({
      price: 1 - (priceCents / 100),  // NO 35¢ → YES ask 0.65
      quantity: qty,
    }));

    // 3. Sort asks ascending (lowest ask first)
    asks.sort((a, b) => a.price - b.price);

    // 4. Validate all prices in 0-1 range
    const allLevels = [...bids, ...asks];
    for (const level of allLevels) {
      if (level.price < 0 || level.price > 1) {
        throw new PlatformApiError(
          1007, // Schema Change
          `Invalid price outside 0-1 range: ${level.price}`,
          PlatformId.KALSHI,
          'error',
        );
      }
    }

    // 5. Check for crossed market (best bid > best ask)
    if (bids.length > 0 && asks.length > 0 && bids[0].price > asks[0].price) {
      this.logger.warn({
        message: 'Crossed market detected',
        module: 'data-ingestion',
        contractId: kalshiBook.market_ticker,
        bestBid: bids[0].price,
        bestAsk: asks[0].price,
        spread: asks[0].price - bids[0].price,
      });
    }

    const latency = Date.now() - startTime;
    this.trackLatency(latency);

    return {
      platformId: PlatformId.KALSHI,
      contractId: kalshiBook.market_ticker,
      bids,
      asks,
      timestamp: new Date(),
      sequenceNumber: kalshiBook.seq,  // From WebSocket delta tracking
    };
  }
}
```

**Edge Cases to Handle:**

- **Empty orderbook** (no YES or NO bids): Return empty bids/asks arrays, log info (valid state for new markets)
- **Crossed market** (bid > ask): Log warning but continue - may be arbitrage opportunity or brief data race
- **Price exactly 0 or 1**: Valid (certain/impossible outcomes), allow
- **Single-sided book** (only YES or only NO bids): Valid for highly asymmetric markets, allow

#### Platform Health Monitoring Architecture

From `architecture.md#Cross-Cutting Concerns` and epics FR-DI-04:

**⚠️ CRITICAL: Story 1.3 already created this type. Use the ACTUAL implementation.**

From `src/common/types/platform.type.ts` (shipped in Story 1.3):

```typescript
export interface PlatformHealth {
  platformId: PlatformId;                // camelCase, NOT "platform"
  status: 'healthy' | 'degraded' | 'disconnected';  // NOTE: 'disconnected' not 'offline'
  lastHeartbeat: Date | null;            // camelCase, NOT "last_update"
  latencyMs: number | null;              // camelCase, NOT "response_time_ms"
  metadata?: Record<string, unknown>;    // Optional additional context
}
```

**Story 1.4 Extensions Needed:**

The existing type is minimal. For health monitoring, we need to track additional state internally (not necessarily in the type):
- Update frequency (rolling window)
- Connection state (from connector.getHealth())
- Staleness tracking (time since last update)

These can be tracked in `PlatformHealthService` private state and included in `metadata` if needed.

**Health Status Determination (CORRECTED with field names and recovery events):**

```typescript
// src/modules/data-ingestion/platform-health.service.ts
class PlatformHealthService {
  private readonly HEALTH_CHECK_INTERVAL = 30_000;  // 30 seconds (FR-DI-04)
  private readonly STALENESS_THRESHOLD = 60_000;    // 60 seconds
  private readonly DEGRADED_LATENCY_THRESHOLD = 2000;  // 2 seconds

  private lastUpdateTime: Map<PlatformId, number> = new Map();
  private latencySamples: Map<PlatformId, number[]> = new Map();
  private previousStatus: Map<PlatformId, 'healthy' | 'degraded' | 'disconnected'> = new Map(); // Track for transitions

  constructor(
    private readonly prisma: PrismaService,
    private readonly eventEmitter: EventEmitter2,
    // Inject connectors or connector registry here
  ) {}

  // ⚠️ NOTE: Using @Cron here vs core/scheduler.service.ts
  // Architecture mentions centralized scheduler, but @Cron is appropriate for self-contained module concerns
  // TradingEngineService uses SchedulerService for main polling cycle
  // PlatformHealthService uses @Cron for independent 30s health checks (different cadence)
  @Cron('*/30 * * * * *')  // Every 30 seconds - @nestjs/schedule already installed (Story 1.2)
  async publishHealth(): Promise<void> {
    const platforms = [PlatformId.KALSHI];  // Expand in Epic 2

    for (const platform of platforms) {
      const previousStatus = this.previousStatus.get(platform) || 'healthy';
      const health = this.calculateHealth(platform);

      // Persist to database (AWAIT to handle errors - not fire-and-forget)
      try {
        await this.prisma.platformHealthLog.create({
          data: {
            platform: platform,  // string enum value
            status: health.status,
            last_update: health.lastHeartbeat || new Date(),
            response_time_ms: health.latencyMs,
            connection_state: health.metadata?.connectionState as string || 'unknown',
            created_at: new Date(),
          },
        });
      } catch (error) {
        this.logger.error({
          message: 'Failed to persist health log',
          module: 'data-ingestion',
          platform,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
        // Continue processing - persistence failure shouldn't block monitoring
      }

      // Emit base health update event
      this.eventEmitter.emit('platform.health.updated', health);

      // Emit transition events (degradation AND recovery)
      if (health.status === 'degraded' && previousStatus !== 'degraded') {
        this.eventEmitter.emit(
          'platform.health.degraded',
          new PlatformDegradedEvent(platform, health, previousStatus),
        );
      } else if (health.status === 'healthy' && previousStatus === 'degraded') {
        // ⚠️ FIX: Emit recovery event when transitioning back to healthy
        this.eventEmitter.emit(
          'platform.health.recovered',
          new PlatformRecoveredEvent(platform, health, previousStatus),
        );
      } else if (health.status === 'disconnected' && previousStatus !== 'disconnected') {
        this.eventEmitter.emit(
          'platform.health.disconnected',
          new PlatformDisconnectedEvent(platform, health),
        );
      }

      // Update previous status for next check
      this.previousStatus.set(platform, health.status);
    }
  }

  private calculateHealth(platform: PlatformId): PlatformHealth {
    const lastUpdate = this.lastUpdateTime.get(platform) || 0;
    const age = Date.now() - lastUpdate;
    const connector = this.getConnector(platform);
    const connectorHealth = connector.getHealth();

    // Connection state check (most severe)
    if (connectorHealth.status === 'disconnected') {
      return {
        platformId: platform,  // CORRECTED: camelCase
        status: 'disconnected',
        lastHeartbeat: lastUpdate > 0 ? new Date(lastUpdate) : null,  // CORRECTED: camelCase
        latencyMs: null,  // CORRECTED: camelCase
        metadata: { connectionState: 'disconnected' },
      };
    }

    // Staleness check (FR-DI-04 - >60s = degraded)
    if (age > this.STALENESS_THRESHOLD) {
      return {
        platformId: platform,
        status: 'degraded',
        lastHeartbeat: new Date(lastUpdate),
        latencyMs: this.calculateP95Latency(platform),
        metadata: { degradationReason: 'stale_data', ageMs: age },
      };
    }

    // Latency check (>2s = degraded)
    const p95Latency = this.calculateP95Latency(platform);
    if (p95Latency && p95Latency > this.DEGRADED_LATENCY_THRESHOLD) {
      return {
        platformId: platform,
        status: 'degraded',
        lastHeartbeat: new Date(lastUpdate),
        latencyMs: p95Latency,
        metadata: { degradationReason: 'high_latency', thresholdMs: this.DEGRADED_LATENCY_THRESHOLD },
      };
    }

    // All checks passed - healthy
    return {
      platformId: platform,
      status: 'healthy',
      lastHeartbeat: new Date(lastUpdate),
      latencyMs: p95Latency,
      metadata: { updateFrequency: this.calculateUpdateFrequency(platform) },
    };
  }

  /**
   * Called by DataIngestionService when an orderbook update is processed.
   * Tracks update timing for staleness detection.
   */
  recordUpdate(platform: PlatformId, latencyMs: number): void {
    this.lastUpdateTime.set(platform, Date.now());

    const samples = this.latencySamples.get(platform) || [];
    samples.push(latencyMs);
    if (samples.length > 100) samples.shift();  // Rolling window
    this.latencySamples.set(platform, samples);
  }

  private calculateP95Latency(platform: PlatformId): number | null {
    const samples = this.latencySamples.get(platform);
    if (!samples || samples.length === 0) return null;

    const sorted = [...samples].sort((a, b) => a - b);
    const p95Index = Math.floor(sorted.length * 0.95);
    return sorted[p95Index];
  }

  private calculateUpdateFrequency(platform: PlatformId): number {
    // Implementation: track update count over rolling 60s window
    // Return updates per second
    return 0;  // Placeholder - implement if needed for diagnostics
  }

  private getConnector(platform: PlatformId): IPlatformConnector {
    // Inject connector registry or individual connectors in constructor
    // Return appropriate connector
    throw new Error('Implement connector lookup');
  }
}
```

### 📋 Architecture Compliance - Database Schema

From `architecture.md#Data Architecture` and `architecture.md#Naming Patterns`:

**Prisma Schema Additions (Story 1.4 - CORRECTED for full depth storage):**

```prisma
// prisma/schema.prisma

// Order book snapshots for audit trail and compliance (7-year retention)
// ⚠️ DESIGN DECISION: Store full depth (bids/asks arrays as JSON) not just best prices
// - Justification: Epic 3's edge calculator needs "liquidity depth at execution prices" (FR-AD-02)
// - Storage cost: ~1-2KB per snapshot vs ~100 bytes for best-only
// - Query pattern: Primarily time-series append, rare queries, acceptable trade-off
model OrderBookSnapshot {
  id              String   @id @default(uuid())
  platform        String   // "kalshi" | "polymarket" (consistent with PlatformHealthLog)
  contract_id     String   // Platform's contract identifier
  bids            Json     // PriceLevel[] serialized: [{price: 0.60, quantity: 1000}, ...]
  asks            Json     // PriceLevel[] serialized: [{price: 0.65, quantity: 800}, ...]
  sequence_number Int?     // Optional WebSocket sequence tracking
  created_at      DateTime @default(now()) @db.Timestamptz

  @@index([platform, contract_id, created_at])
  @@index([created_at])  // For retention policy cleanup (7-year window)
  @@map("order_book_snapshots")
}

// Platform health logs for observability and degradation analysis
model PlatformHealthLog {
  id                 String   @id @default(uuid())
  platform           String   // "kalshi" | "polymarket"
  status             String   // "healthy" | "degraded" | "disconnected" (NOT "offline")
  last_update        DateTime @db.Timestamptz
  response_time_ms   Float?   // p95 latency
  connection_state   String   // From connector.getHealth() metadata
  created_at         DateTime @default(now()) @db.Timestamptz

  @@index([platform, created_at])
  @@index([created_at])
  @@map("platform_health_logs")
}
```

**Note on JSON fields:** Prisma's `Json` type stores data as JSONB in PostgreSQL. Query performance is acceptable for time-series append-only pattern. If Epic 3 needs indexed queries on price levels, consider materialized views or separate price_levels table.

**⚠️ Addressing Epic 3's Depth Requirements:**
Story 3.3's edge calculator needs "liquidity depth at execution prices" (FR-AD-02). Story 1.3's NormalizedOrderBook already stores full depth (bids/asks arrays), and Story 1.4's Prisma schema persists this depth as JSON. **This fully satisfies Epic 3's requirements** - no schema changes needed in Epic 3.

**Migration Workflow:**

```bash
# After editing schema.prisma
cd pm-arbitrage-engine
pnpm prisma migrate dev --name add_order_book_and_health_tables
pnpm prisma generate  # Regenerate Prisma client
```

**Retention Policy (Phase 1):**

Story 1.4 creates the tables. Retention cleanup (7-year policy) will be implemented in Epic 6 (Monitoring & Alerting) via scheduled cleanup job.

### 🔧 Previous Story Learnings (Story 1.3)

#### Key Implementation Patterns Established

**1. Structured Logging with Performance Tracking**

```typescript
// Pattern from Story 1.3's connector (CORRECTED for actual NormalizedOrderBook type)
this.logger.log({
  message: 'Order book normalized',
  module: 'data-ingestion',
  timestamp: new Date().toISOString(),
  latencyMs: latency,
  contractId: normalized.contractId,  // camelCase from actual type
  metadata: {
    platformId: normalized.platformId,
    bidLevels: normalized.bids.length,  // bids is array
    askLevels: normalized.asks.length,  // asks is array
    bestBid: normalized.bids[0]?.price,
    bestAsk: normalized.asks[0]?.price,
    sequenceNumber: normalized.sequenceNumber,
  },
});
```

**For Story 1.4:** Add latency tracking to normalization service. Log every normalization with latency, track 95th percentile in-memory for performance monitoring.

**2. EventEmitter2 Integration Pattern**

From Story 1.2's `TradingEngineService`:

```typescript
// Emit domain events for observability
this.eventEmitter.emit('platform.health.degraded', event);
this.eventEmitter.emit('orderbook.updated', normalizedBook);
```

**For Story 1.4:**
- Emit `OrderBookUpdatedEvent` on every normalization
- Emit `PlatformDegradedEvent` when health transitions to degraded
- Emit `PlatformRecoveredEvent` when health recovers

**3. Prisma Service Injection Pattern**

From Story 1.2's `PersistenceModule`:

```typescript
// Inject PrismaService for database access
constructor(
  private readonly prisma: PrismaService,
  private readonly eventEmitter: EventEmitter2,
) {}
```

**For Story 1.4:** Inject PrismaService into DataIngestionService for persisting snapshots and health logs.

**4. NestJS Module Pattern**

```typescript
// src/modules/data-ingestion/data-ingestion.module.ts
@Module({
  imports: [
    PersistenceModule,  // For PrismaService
    ConnectorModule,    // For KalshiConnector
  ],
  providers: [
    DataIngestionService,
    OrderBookNormalizerService,
    PlatformHealthService,
  ],
  exports: [DataIngestionService, PlatformHealthService],
})
export class DataIngestionModule {}
```

**Constructor Injection Pattern (MVP - Concrete Class):**

```typescript
// src/modules/data-ingestion/data-ingestion.service.ts
@Injectable()
export class DataIngestionService implements OnModuleInit {
  constructor(
    private readonly kalshiConnector: KalshiConnector,  // ⚠️ MVP: Inject by concrete class
    private readonly normalizer: OrderBookNormalizerService,
    private readonly healthService: PlatformHealthService,
    private readonly prisma: PrismaService,
    private readonly eventEmitter: EventEmitter2,
  ) {}

  // ... implementation
}
```

**⚠️ Clarification:** The architecture mandates interface-based injection (`IPlatformConnector`), but for MVP with only one platform connector, Story 1.4 injects `KalshiConnector` by concrete class. This simplifies DI configuration. Future stories will refactor to token-based injection when adding Polymarket connector.

Import into AppModule:

```typescript
// src/app.module.ts
@Module({
  imports: [
    ConfigModule.forRoot({ /* ... */ }),
    EventEmitterModule.forRoot(),
    ScheduleModule.forRoot(),  // NEW - for @Cron decorators
    PersistenceModule,
    CoreModule,
    ConnectorModule,
    DataIngestionModule,  // ADD THIS
  ],
  // ...
})
export class AppModule {}
```

**5. Testing Pattern with Mocks**

From Story 1.3's connector tests:

```typescript
describe('OrderBookNormalizerService', () => {
  let service: OrderBookNormalizerService;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [OrderBookNormalizerService],
    }).compile();

    service = module.get<OrderBookNormalizerService>(OrderBookNormalizerService);
  });

  it('should convert Kalshi cents to decimal with realistic spread', () => {
    const kalshiBook = {
      market_ticker: 'TEST-MARKET',
      yes: [[60, 1000], [59, 500]],  // YES bids: 60¢, 59¢
      no: [[35, 800], [34, 600]],    // NO bids: 35¢, 34¢ → YES asks: 65¢, 66¢
    };

    const normalized = service.normalize(kalshiBook);

    // Best bid: highest YES bid = 60¢ = 0.60
    expect(normalized.bids[0].price).toBe(0.60);
    expect(normalized.bids[0].quantity).toBe(1000);

    // Best ask: 1 - highest NO bid = 1 - 0.35 = 0.65
    expect(normalized.asks[0].price).toBe(0.65);
    expect(normalized.asks[0].quantity).toBe(800);

    // Spread = 0.65 - 0.60 = 0.05 (5 cents)
    const spread = normalized.asks[0].price - normalized.bids[0].price;
    expect(spread).toBe(0.05);
  });

  it('should handle zero-spread (locked) market', () => {
    const kalshiBook = {
      market_ticker: 'TEST-MARKET',
      yes: [[62, 1000]],
      no: [[38, 800]],  // 62 + 38 = 100 → zero spread
    };

    const normalized = service.normalize(kalshiBook);

    expect(normalized.bids[0].price).toBe(0.62);
    expect(normalized.asks[0].price).toBe(0.62);  // 1 - 0.38 = 0.62
    expect(normalized.asks[0].price - normalized.bids[0].price).toBe(0);  // Zero spread
  });
});
```

### 📚 Architecture References

**Primary Sources:**
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4] - Complete acceptance criteria and BDD scenarios
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] - Database schema patterns, caching strategy
- [Source: _bmad-output/planning-artifacts/architecture.md#Module Organization] - Module structure for data-ingestion
- [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns] - Logging, validation, performance requirements
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] - Database snake_case, TypeScript camelCase conventions

**Related Stories:**
- [Source: 1-3-kalshi-platform-connector-authentication.md] - KalshiConnector interface, error handling patterns, testing patterns

### 🎯 Performance Requirements (CRITICAL)

From epics AC and NFR-P1:

**Normalization Latency SLA:**
- **Target:** 500ms at 95th percentile (FR-DI-02, NFR-P1)
- **Monitoring:** Track every normalization operation, log p95 every minute
- **Implementation:** In-memory rolling window of last 100 samples

```typescript
// ⚠️ CORRECTED: Removed health param (NormalizedOrderBook from Story 1.3 doesn't include platform_health)
class OrderBookNormalizerService {
  private latencySamples: number[] = [];

  normalize(kalshiBook: KalshiOrderBook): NormalizedOrderBook {
    const startTime = Date.now();

    // ... normalization logic (see earlier section) ...

    const latency = Date.now() - startTime;
    this.trackLatency(latency);

    if (latency > 500) {
      this.logger.warn({
        message: 'Normalization latency exceeded SLA',
        latencyMs: latency,
        threshold: 500,
        contractId: kalshiBook.market_ticker,
      });
    }

    return normalizedBook;
  }

  private trackLatency(latencyMs: number): void {
    this.latencySamples.push(latencyMs);
    if (this.latencySamples.length > 100) {
      this.latencySamples.shift();
    }
  }

  getP95Latency(): number {
    if (this.latencySamples.length === 0) return 0;
    const sorted = [...this.latencySamples].sort((a, b) => a - b);
    const p95Index = Math.floor(sorted.length * 0.95);
    return sorted[p95Index];
  }
}
```

**Health Publishing Frequency:**
- **Interval:** 30 seconds (FR-DI-04)
- **Implementation:** Use `@nestjs/schedule` with `@Cron('*/30 * * * * *')`
- **Cron pattern:** `*/30 * * * * *` = every 30 seconds

### ✅ Testing Strategy

**Unit Tests Required:**

1. **OrderBookNormalizerService Tests**
   - Cent-to-decimal conversion (62¢ → 0.62)
   - YES/NO to bid/ask transformation
   - Price validation (0.00-1.00 range)
   - Edge cases: empty orderbook, crossed market, price = 0 or 1
   - Performance: latency tracking works correctly

2. **PlatformHealthService Tests**
   - Health status calculation (healthy/degraded/offline)
   - Staleness detection (>60s = degraded)
   - Latency-based degradation (>2s = degraded)
   - Connection state transitions
   - Cron job execution (use fake timers)

3. **DataIngestionService Tests**
   - Orchestration: connector → normalizer → persistence
   - Event emission: OrderBookUpdatedEvent, PlatformDegradedEvent
   - Error handling: normalization failures, persistence failures

**Integration Tests:**

```typescript
// test/data-ingestion.e2e-spec.ts
describe('Data Ingestion (e2e)', () => {
  let app: INestApplication;
  let connector: KalshiConnector;
  let ingestionService: DataIngestionService;
  let prisma: PrismaService;

  beforeAll(async () => {
    const moduleFixture = await Test.createTestingModule({
      imports: [
        ConfigModule.forRoot({ envFilePath: '.env.test' }),
        PersistenceModule,
        ConnectorModule,
        DataIngestionModule,
      ],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();

    connector = moduleFixture.get<KalshiConnector>(KalshiConnector);
    ingestionService = moduleFixture.get<DataIngestionService>(DataIngestionService);
    prisma = moduleFixture.get<PrismaService>(PrismaService);
  });

  it('should normalize and persist Kalshi orderbook', async () => {
    await connector.connect();

    // Trigger orderbook update via WebSocket or manual call
    const orderbook = await connector.getOrderBook('CPI-22DEC-TN0.1');

    // Verify snapshot was persisted
    const snapshot = await prisma.orderBookSnapshot.findFirst({
      where: { contract_id: 'CPI-22DEC-TN0.1' },
      orderBy: { created_at: 'desc' },
    });

    expect(snapshot).toBeDefined();
    // ⚠️ CORRECTED: Schema uses bids/asks (Json), not best_bid/best_ask (Float)
    expect(snapshot.bids).toBeDefined();
    expect(snapshot.asks).toBeDefined();
    expect(Array.isArray(snapshot.bids)).toBe(true);
    expect(Array.isArray(snapshot.asks)).toBe(true);
    // Verify price levels are in valid range
    const firstBid = (snapshot.bids as any)[0];
    if (firstBid) {
      expect(firstBid.price).toBeGreaterThanOrEqual(0);
      expect(firstBid.price).toBeLessThanOrEqual(1);
    }
  }, 10000);

  it('should publish health status on schedule', async () => {
    // ⚠️ CORRECTED: Don't use fake timers with real async DB operations
    // Instead, manually trigger the health check method

    const healthService = app.get<PlatformHealthService>(PlatformHealthService);

    // Manually trigger health publication (same as cron would call)
    await healthService.publishHealth();

    // Verify health log was created
    const healthLog = await prisma.platformHealthLog.findFirst({
      where: { platform: 'kalshi' },
      orderBy: { created_at: 'desc' },
    });

    expect(healthLog).toBeDefined();
    expect(['healthy', 'degraded', 'disconnected']).toContain(healthLog.status);
  });
});
```

### 🏗️ Architecture Integration - DataIngestionService with TradingEngineService

**⚠️ CRITICAL: Story 1.2 created TradingEngineService.executeCycle() with placeholder pipeline.**

From `src/core/trading-engine.service.ts` (Story 1.2):
```typescript
async executeCycle(): Promise<void> {
  // Placeholder pipeline - actual implementation comes in later stories
  await this.executePipelinePlaceholder();
}
```

**Story 1.4 Integration Pattern:**

DataIngestionService does **NOT** run independently. It's called by TradingEngineService during each cycle:

```typescript
// src/core/trading-engine.service.ts (Story 1.4 modification)
async executeCycle(): Promise<void> {
  this.inflightOperations++;
  try {
    // STEP 1: Data Ingestion (Story 1.4)
    await this.dataIngestionService.ingestCurrentOrderBooks();

    // STEP 2: Arbitrage Detection (Epic 3)
    // await this.detectionService.detectOpportunities();

    // STEP 3: Risk Validation (Epic 4)
    // STEP 4: Execution (Epic 5)
  } finally {
    this.inflightOperations--;
  }
}
```

**WebSocket Updates - Parallel Path:**

WebSocket updates run in parallel to polling cycles (real-time):

```typescript
// src/modules/data-ingestion/data-ingestion.service.ts
async onModuleInit() {
  // Register WebSocket callback for real-time updates
  this.kalshiConnector.onOrderBookUpdate((rawBook) => {
    // Process asynchronously, don't block WebSocket
    this.processWebSocketUpdate(rawBook).catch(error => {
      this.logger.error({
        message: 'WebSocket update processing failed',
        error: error.message,
      });
    });
  });
}

private async processWebSocketUpdate(rawBook: KalshiOrderBook): Promise<void> {
  const startTime = Date.now();

  // Normalize
  const normalized = this.normalizer.normalize(rawBook);

  // Persist (with error handling, NOT fire-and-forget)
  await this.persistSnapshot(normalized);

  // Emit event
  this.eventEmitter.emit('orderbook.updated', new OrderBookUpdatedEvent(normalized));

  // Track latency for health monitoring
  this.healthService.recordUpdate(PlatformId.KALSHI, Date.now() - startTime);
}
```

**Two Data Flow Paths:**

1. **Polling (TradingEngineService → DataIngestionService.ingestCurrentOrderBooks())** - Scheduled, every 30s
2. **WebSocket (connector → DataIngestionService.processWebSocketUpdate())** - Real-time, event-driven

Both paths converge at normalization → persistence → event emission.

### 🚨 Critical Implementation Decisions

**Decision 1: Persistence Error Handling (CORRECTED - NOT fire-and-forget)**

**Answer:** AWAIT persistence, log errors, increment failure counter, alert on threshold

**Rationale (corrected from earlier):**
- **NFR-S3 requires 7-year audit trail** - silently dropping snapshots violates compliance
- **NFR-R5 requires "all snapshots logged"** - fire-and-forget breaks this guarantee
- **Better approach:** Await persistence, log failures, continue processing
- If persistence fails repeatedly (>10 failures), emit critical alert
- This balances reliability (don't lose data) with availability (don't block on transient DB issues)

```typescript
// CORRECTED persistence pattern
private async persistSnapshot(book: NormalizedOrderBook): Promise<void> {
  try {
    await this.prisma.orderBookSnapshot.create({
      data: {
        platform: book.platformId,  // CORRECTED: matches Prisma schema field name
        contract_id: book.contractId,
        bids: book.bids,  // JSON serialization
        asks: book.asks,
        sequence_number: book.sequenceNumber,
        created_at: new Date(),
      },
    });
    this.consecutiveFailures = 0;  // Reset on success
  } catch (error) {
    this.consecutiveFailures++;
    this.logger.error({
      message: 'Snapshot persistence failed',
      module: 'data-ingestion',
      contractId: book.contractId,
      failures: this.consecutiveFailures,
      error: error instanceof Error ? error.message : 'Unknown',
    });

    // Critical alert after sustained failures
    if (this.consecutiveFailures >= 10) {
      this.eventEmitter.emit(
        'system.health.critical',
        new SystemHealthError(4005, 'Persistent snapshot write failure', 'critical'),
      );
    }
  }
}
```

**Decision 2: How to handle normalization failures?**

**Answer:** Log error, skip snapshot persistence, DO NOT emit OrderBookUpdatedEvent

**Rationale:**
- Invalid data should never reach detection module
- Platform health will detect staleness and mark degraded
- Operator alerted via health monitoring

**Decision 3: Should health service query connectors or track passively?**

**Answer:** Passive tracking via `recordUpdate()` calls from DataIngestionService

**Rationale:**
- Active polling adds load to connectors
- Passive tracking measures actual data flow (more accurate)
- Connector's `getHealth()` provides connection state backup

**Decision 4: Manual file creation vs nest g generators?**

**Answer:** Manual file creation (consistent with Stories 1.1-1.3)

**Rationale:**
- NestJS generators use their own conventions that may conflict with architecture
- Stories 1.1-1.3 created files manually for precise control
- Consistency across stories is critical for maintainability

### 🔄 Next Steps After Completion

1. **Verify database migrations:**
   ```bash
   cd pm-arbitrage-engine
   pnpm prisma migrate dev --name add_order_book_and_health_tables
   pnpm prisma studio  # Verify tables exist
   ```

2. **Run integration test:**
   ```bash
   pnpm test:e2e
   # Verify Kalshi → normalizer → persistence flow works
   ```

3. **Update sprint status:**
   - Change `1-4-order-book-normalization-health-monitoring: backlog` → `ready-for-dev`

4. **Ready for Story 1.5:**
   - Structured Logging, Correlation Tracking & Event Infrastructure
   - Will build on the event emission patterns from this story

---

## ⚠️ CRITICAL CORRECTIONS FROM REVIEW

This story was **reviewed and corrected** before implementation. The following critical issues were fixed:

### ✅ Fixed Issues

**1. NormalizedOrderBook Type Mismatch (CRITICAL)**
- ❌ Original: Defined type with `best_bid`, `best_ask` single values
- ✅ Corrected: Uses actual type from Story 1.3 with `bids: PriceLevel[]`, `asks: PriceLevel[]` arrays
- ✅ Uses correct field names: `platformId`, `contractId` (camelCase)

**2. YES/NO Transformation Logic (CRITICAL)**
- ❌ Original: Zero-spread example (62¢ + 38¢ = 100) obscured typical case
- ✅ Corrected: Realistic spread examples (YES 60¢, NO 35¢ → bid=0.60, ask=0.65, spread=0.05)
- ✅ Full arrays transformation, not just best prices
- ✅ Crossed market detection added

**3. PlatformHealth Type (SIGNIFICANT)**
- ❌ Original: Redefined type with wrong field names (`last_update`, `response_time_ms`)
- ✅ Corrected: Uses actual type from Story 1.3 (`lastHeartbeat`, `latencyMs`, `status: 'disconnected'` not `'offline'`)

**4. Fire-and-Forget Persistence (CRITICAL)**
- ❌ Original: Fire-and-forget with no error handling (violates NFR-S3, NFR-R5)
- ✅ Corrected: Await persistence, log errors, track consecutive failures, emit alert if >10

**5. Missing PlatformRecoveredEvent (SIGNIFICANT)**
- ❌ Original: Only emitted degradation events
- ✅ Corrected: Track previous state, emit recovery events on degraded→healthy transition

**6. Prisma Schema (SIGNIFICANT)**
- ❌ Original: Single best_bid/best_ask fields
- ✅ Corrected: JSON fields storing full bids/asks arrays (satisfies Epic 3 depth requirements)

**7. TradingEngineService Integration (CRITICAL)**
- ❌ Original: Integration path unclear
- ✅ Corrected: Explicit integration via `executeCycle()` calling `ingestCurrentOrderBooks()`, plus parallel WebSocket path

**8. Task List (MODERATE)**
- ❌ Original: Used `nest g` generators (inconsistent with Stories 1.1-1.3)
- ✅ Corrected: Manual file creation, explicit WebSocket callback wiring, removed duplicate @nestjs/schedule installation

**9. Test Examples (MODERATE)**
- ❌ Original: Wrong field names, fake timers with real async DB
- ✅ Corrected: Correct field names, manual method trigger for health tests, realistic spread scenarios

**10. Depth Data for Epic 3 (CLARIFIED)**
- ✅ Added note: Full depth already captured, Epic 3 requirements satisfied

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

New files to be created:
- `pm-arbitrage-engine/prisma/migrations/[timestamp]_add_order_book_and_health_tables/migration.sql`
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.module.ts`
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.ts`
- `pm-arbitrage-engine/src/modules/data-ingestion/data-ingestion.service.spec.ts`
- `pm-arbitrage-engine/src/modules/data-ingestion/order-book-normalizer.service.ts`
- `pm-arbitrage-engine/src/modules/data-ingestion/order-book-normalizer.service.spec.ts`
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.ts`
- `pm-arbitrage-engine/src/modules/data-ingestion/platform-health.service.spec.ts`
- `pm-arbitrage-engine/src/common/events/orderbook.events.ts`
- `pm-arbitrage-engine/test/data-ingestion.e2e-spec.ts`

Modified files:
- `pm-arbitrage-engine/src/app.module.ts` (import DataIngestionModule, ScheduleModule)
- `pm-arbitrage-engine/prisma/schema.prisma` (add OrderBookSnapshot and PlatformHealthLog models)
- `pm-arbitrage-engine/package.json` (add @nestjs/schedule if not present)
