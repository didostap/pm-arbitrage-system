# Story 1.2: Core Engine Lifecycle & Graceful Shutdown

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want the trading engine to start up cleanly, run a continuous polling loop, and shut down gracefully,
So that I can deploy and restart the system safely without data loss.

## Acceptance Criteria

**Given** the engine process starts
**When** initialization completes
**Then** the trading engine service begins the main polling loop at configured intervals
**And** engine lifecycle service registers startup and shutdown hooks
**And** a startup log entry is written with timestamp and configuration summary

**Given** the engine receives SIGTERM/SIGINT
**When** graceful shutdown initiates
**Then** the polling loop stops accepting new cycles
**And** any in-flight operations complete before process exit
**And** all database connections are closed cleanly
**And** a shutdown log entry is written with timestamp

**Given** the scheduler service is running
**When** polling interval elapses
**Then** the next cycle triggers (detection → risk → execution pipeline placeholder)
**And** cycle timing is logged for performance monitoring

**Given** a polling cycle is in progress
**When** the next scheduled interval fires
**Then** the scheduler skips the interval (prevents overlapping cycles)
**And** a skip event is logged with reason "cycle already in progress"

## Tasks / Subtasks

- [x] Task 1: Implement EngineLifecycleService (AC: 1, 2)
  - [x] Create `src/core/engine-lifecycle.service.ts` and `.spec.ts`
  - [x] Implement `onApplicationBootstrap` hook for startup logging
  - [x] Implement `onApplicationShutdown` hook for graceful termination
  - [x] Register SIGTERM and SIGINT handlers
  - [x] Ensure database connections close cleanly on shutdown

- [x] Task 2: Implement TradingEngineService (AC: 1, 3)
  - [x] Create `src/core/trading-engine.service.ts` and `.spec.ts`
  - [x] Implement main polling loop with placeholder pipeline
  - [x] Add in-flight operation tracking for graceful shutdown
  - [x] Log cycle timing for performance monitoring
  - [x] Implement shutdown flag to stop accepting new cycles

- [x] Task 3: Implement SchedulerService (AC: 3, overlap prevention)
  - [x] Create `src/core/scheduler.service.ts` and `.spec.ts`
  - [x] Configure polling interval from environment (default 30s)
  - [x] Integrate with @nestjs/schedule for interval management
  - [x] Implement cycle-in-progress check to prevent overlaps
  - [x] Trigger TradingEngineService on each interval if no cycle active
  - [x] Log scheduler initialization, shutdown, and skipped intervals

- [x] Task 4: Create CoreModule and wire services (AC: All)
  - [x] Create `src/core/core.module.ts`
  - [x] Register all core services as providers
  - [x] Import CoreModule in AppModule
  - [x] Verify startup/shutdown flow works end-to-end

- [x] Task 5: Add configuration for polling intervals (AC: 3)
  - [x] Add POLLING_INTERVAL_MS to .env.development (default 30000)
  - [x] Update .env.example with polling configuration
  - [x] Add stop_grace_period: 15s to docker-compose.yml engine service
  - [x] Validate configuration at startup

- [x] Task 6: Write comprehensive tests (AC: All)
  - [x] Unit tests for EngineLifecycleService (startup/shutdown hooks)
  - [x] Unit tests for TradingEngineService (polling loop, shutdown)
  - [x] Unit tests for SchedulerService (interval triggering)
  - [x] Integration test for complete startup → poll → shutdown cycle

## Dev Notes

### 🎯 Story Context & Purpose

This is **Story 1.2** in Epic 1 - the second story in the project. Story 1.1 completed the project scaffold, and now we're building the core engine lifecycle that orchestrates the entire trading system.

**Critical Mission:** Build the beating heart of the arbitrage engine - a continuous polling loop that runs the detection → risk → execution pipeline, with production-grade startup and shutdown handling.

**Why This Story Matters:**
- Every future module (detection, risk, execution) depends on this orchestration layer
- Graceful shutdown prevents data loss during deployments and restarts
- The polling cycle is where all performance requirements (NFR-P1, NFR-P2, NFR-P3) originate
- This establishes the foundation for the "single event loop cycle" execution model described in the architecture

### 🔬 Architecture Intelligence - Core Patterns

#### The Core Orchestrator Pattern

From `architecture.md#Project Structure & Boundaries`:

```
core/ → modules/* (orchestrates all modules via interfaces)
```

The `core/` directory sits **above** all feature modules (data-ingestion, detection, execution, risk, monitoring) and orchestrates them without direct dependencies. This story creates that orchestration foundation.

#### Lifecycle Service Pattern (NestJS)

NestJS provides two critical lifecycle hooks for managing application state:

1. **`onApplicationBootstrap()`** - Runs after all modules are initialized but before the app starts listening
2. **`onApplicationShutdown()`** - Runs when a shutdown signal is received (SIGTERM/SIGINT)

These hooks are the *only* correct place for:
- Startup logging and configuration validation
- Database connection verification
- Graceful termination of long-running operations
- Resource cleanup (closing DB connections, stopping schedulers)

**Anti-pattern to avoid:** Never put startup/shutdown logic in `main.ts` or service constructors. Use NestJS lifecycle hooks for proper dependency injection and testability.

#### The Polling Cycle Architecture

From `architecture.md#Data Flow`:

```
core/trading-engine (orchestrates the polling cycle)
    ↓
modules/data-ingestion/ (aggregate, health check, publish NormalizedOrderBook)
    ↓ (synchronous DI call)
modules/arbitrage-detection/ (identify opportunities, calculate edge)
    ↓ (synchronous DI call)
modules/risk-management/ (validate position, check limits, reserve budget)
    ↓ (synchronous DI call)
modules/execution/ (submit orders, manage legs, lock execution)
    ↓ (EventEmitter2 fan-out)
modules/monitoring/ (audit logs, Telegram alerts, dashboard events)
```

**For Story 1.2:** The pipeline is a *placeholder* - actual module implementations come later. This story focuses on:
- Starting the loop
- Calling a placeholder `executeCycle()` method
- Stopping the loop gracefully
- Logging cycle timing

#### Scheduler Pattern (@nestjs/schedule)

NestJS provides `@nestjs/schedule` for interval-based execution. From the architecture, the system needs:

1. **Polling cycle:** Every 30 seconds (configurable via `POLLING_INTERVAL_MS`)
2. **NTP sync checks:** Every 6 hours (Story 1.6)
3. **Daily test alerts:** Configured time, default 8am (Epic 6)

**For Story 1.2:** Implement only the polling cycle scheduler. NTP and alerts come in later stories.

### 🏗️ Technical Requirements from Architecture

#### 1. Graceful Shutdown Must Handle In-Flight Operations

From `architecture.md#Infrastructure & Deployment`:

> Docker HEALTHCHECK on engine container — internal health endpoint, 3 consecutive failures (30-second intervals) triggers automatic restart.

**Critical implications:**
- Docker's default grace period is 10 seconds, but Story 1.1 didn't configure `stop_grace_period`
- **MUST ADD** to docker-compose.yml: `stop_grace_period: 15s` (15s for safety margin)
- This gives 12-13 seconds for graceful shutdown (leaving 2-3s buffer)
- Any cycle that starts must be allowed to complete (or safely aborted)
- Database writes must be committed or rolled back - no partial state
- WebSocket connections to platforms (Epic 1 Story 1.3) must close cleanly

**Key pattern: In-flight operation tracking**

Use a counter pattern in TradingEngineService:
- Increment `inflightOperations` when cycle starts
- Decrement when cycle completes (in finally block)
- In shutdown: wait for counter to reach 0 (with 12s timeout)
- If timeout expires, log forced shutdown but complete anyway

#### 2. Structured Logging with Correlation IDs

From `architecture.md#Process Patterns - Logging`:

> Every log entry includes: `timestamp`, `level`, `module`, `correlationId`, `message`, `data`.

**For Story 1.2:** The correlation ID system will be implemented in Epic 1 Story 1.5 (Structured Logging & Event Infrastructure). For now, use basic structured logging:

```typescript
this.logger.log({
  message: 'Engine startup complete',
  timestamp: new Date().toISOString(),
  module: 'core',
  configSummary: {
    pollingIntervalMs: this.pollingInterval,
    environment: process.env.NODE_ENV,
  },
});
```

**Note:** Story 1.5 will add the `CorrelationIdInterceptor` that generates a unique ID per polling cycle. Don't implement correlation IDs in this story - just prepare for them by using structured logging.

#### 3. Configuration via @nestjs/config

From Story 1.1, `ConfigModule` is already set up globally:

```typescript
// app.module.ts (already exists from Story 1.1)
@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: `.env.${process.env.NODE_ENV || 'development'}`,
    }),
  ],
})
export class AppModule {}
```

**For Story 1.2:** Inject `ConfigService` into services to read polling interval:

```typescript
constructor(
  private readonly configService: ConfigService,
) {
  this.pollingInterval = this.configService.get<number>('POLLING_INTERVAL_MS', 30000);
}
```

Add to `.env.development`:
```env
POLLING_INTERVAL_MS=30000  # 30 seconds for MVP
```

Add to `.env.example`:
```env
POLLING_INTERVAL_MS=30000  # Polling cycle interval in milliseconds
```

#### 4. Testing with Vitest + SWC Decorators

From Story 1.1, Vitest is configured with `unplugin-swc` for decorator metadata support. All tests must use NestJS testing utilities:

```typescript
import { Test, TestingModule } from '@nestjs/testing';
import { EngineLifecycleService } from './engine-lifecycle.service';

describe('EngineLifecycleService', () => {
  let service: EngineLifecycleService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [EngineLifecycleService],
    }).compile();

    service = module.get<EngineLifecycleService>(EngineLifecycleService);
  });

  it('should implement onApplicationBootstrap', () => {
    expect(service.onApplicationBootstrap).toBeDefined();
  });
});
```

### 📋 Architecture Compliance Requirements

#### File Locations (MUST follow exactly)

Per `architecture.md#Project Structure`:

```
src/core/
├── core.module.ts                   # NEW: Core module definition
├── trading-engine.service.ts        # NEW: Main polling loop orchestrator
├── trading-engine.service.spec.ts   # NEW: Unit tests
├── engine-lifecycle.service.ts      # NEW: Startup/shutdown hooks
├── engine-lifecycle.service.spec.ts # NEW: Unit tests
├── scheduler.service.ts             # NEW: Interval management
└── scheduler.service.spec.ts        # NEW: Unit tests
```

**Critical:** Do NOT place these files anywhere else. The `core/` directory is the designated location for engine lifecycle and orchestration logic.

#### Naming Conventions (MUST follow exactly)

From `architecture.md#Naming Patterns`:

- **Files:** `kebab-case` (e.g., `engine-lifecycle.service.ts`)
- **Classes:** `PascalCase` (e.g., `EngineLifecycleService`)
- **Methods:** `camelCase` (e.g., `onApplicationBootstrap`, `executeCycle`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `POLLING_INTERVAL_MS`)

#### Module Registration Pattern

```typescript
// src/core/core.module.ts
import { Module } from '@nestjs/common';
import { ScheduleModule } from '@nestjs/schedule';
import { EngineLifecycleService } from './engine-lifecycle.service';
import { TradingEngineService } from './trading-engine.service';
import { SchedulerService } from './scheduler.service';

@Module({
  imports: [
    ScheduleModule.forRoot(), // Required for @Cron() decorators
  ],
  providers: [
    EngineLifecycleService,
    TradingEngineService,
    SchedulerService,
  ],
  exports: [TradingEngineService], // Expose for future monitoring integration
})
export class CoreModule {}
```

```typescript
// src/app.module.ts (UPDATE existing file)
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { PrismaService } from './common/prisma.service';
import { CoreModule } from './core/core.module'; // ADD THIS

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: `.env.${process.env.NODE_ENV || 'development'}`,
    }),
    CoreModule, // ADD THIS
  ],
  controllers: [AppController],
  providers: [AppService, PrismaService],
})
export class AppModule {}
```

### 🔧 Library & Framework Requirements

#### Required Dependencies

**Check Story 1.1's package.json first** to verify what's already installed:

- `@nestjs/common` (11.x) - ✅ Already installed
- `@nestjs/config` - ✅ Already installed
- `@nestjs/schedule` - ❓ **CHECK IF ALREADY INSTALLED**

If `@nestjs/schedule` is not in package.json from Story 1.1:

```bash
pnpm add @nestjs/schedule
```

**Note:** Verify first to avoid duplicate work or version conflicts.

#### NestJS Lifecycle Interfaces

```typescript
import { Injectable, OnApplicationBootstrap, OnApplicationShutdown } from '@nestjs/common';

@Injectable()
export class EngineLifecycleService
  implements OnApplicationBootstrap, OnApplicationShutdown
{
  async onApplicationBootstrap() {
    // Runs after all modules initialized, before app.listen()
  }

  async onApplicationShutdown(signal?: string) {
    // Runs when SIGTERM/SIGINT received
  }
}
```

**Critical:** These interfaces are the *only* correct way to hook into NestJS lifecycle. Never use process.on('SIGTERM') directly.

#### NestJS Schedule API - Dynamic Interval Solution

⚠️ **CRITICAL LIMITATION: @Interval() decorator does NOT support dynamic config values**

The decorator requires a compile-time constant. Use `SchedulerRegistry` instead:

```typescript
import { Injectable, OnModuleInit } from '@nestjs/common';
import { SchedulerRegistry } from '@nestjs/schedule';

@Injectable()
export class SchedulerService implements OnModuleInit {
  onModuleInit() {
    const intervalMs = this.configService.get<number>('POLLING_INTERVAL_MS', 30000);
    const interval = setInterval(() => this.handlePollingCycle(), intervalMs);
    this.schedulerRegistry.addInterval('pollingCycle', interval);
  }

  private async handlePollingCycle() {
    if (this.tradingEngine.isCycleInProgress()) {
      this.logger.debug('Skipping - cycle in progress');
      return;
    }
    await this.tradingEngine.executeCycle();
  }
}
```

**Key requirements:**
- Use `SchedulerRegistry.addInterval()` for runtime configuration
- Add `isCycleInProgress()` check to prevent overlapping cycles
- NestJS Schedule auto-clears intervals on shutdown

### 📚 Previous Story Intelligence (Story 1.1 Learnings)

#### Key Findings from Story 1.1 Completion

**1. Project Structure Foundation Established**
- NestJS 11.x initialized in `pm-arbitrage-engine/` subdirectory
- Fastify adapter configured (2-3x faster than Express)
- PostgreSQL on port 5433 (avoiding local PostgreSQL conflict on 5432)
- Directory structure created: `modules/`, `connectors/`, `common/`, `core/`
- All directories have `.gitkeep` placeholder files

**2. PrismaService Lifecycle - Critical Decision**

⚠️ **IMPORTANT: PrismaService already manages its own lifecycle**

From NestJS patterns, PrismaService likely implements `onModuleInit` and `onModuleDestroy` (check Story 1.1's implementation):
- `onModuleInit()` → calls `$connect()`
- `onModuleDestroy()` → calls `$disconnect()`

**DO NOT duplicate connection management in EngineLifecycleService.** NestJS automatically calls these hooks.

**What EngineLifecycleService SHOULD do:**
- Verify database is reachable by running a simple query (e.g., `prisma.$queryRaw\`SELECT 1\``)
- This confirms Prisma connected successfully without managing the connection itself

**Pattern:**
```typescript
async onApplicationBootstrap() {
  try {
    await this.prisma.$queryRaw`SELECT 1`; // Verify connectivity
    this.logger.log('Database connection verified');
  } catch (error) {
    this.logger.error('Database connection failed', error);
    throw error; // Prevent app startup if DB unavailable
  }
}

// No prisma.$disconnect() in onApplicationShutdown - Prisma handles it
```

**3. Docker Migration Strategy Pattern**
From Story 1.1:
> **Docker migration strategy:** Dockerfile CMD runs `prisma migrate deploy` on every container startup (line 47). This is acceptable for MVP single-instance deployment.

**Impact for Story 1.2:** The database schema is already migrated on container startup, so the engine can assume Prisma is ready. No need for manual migration checks in the lifecycle service.

**4. Environment Configuration Pattern Established**
From Story 1.1:
- `.env.development` - Local dev config (committed with safe defaults)
- `.env.example` - Template showing all required variables (committed)
- `ConfigModule.forRoot()` configured globally in `app.module.ts`

**Impact for Story 1.2:** Add polling configuration to existing environment files. Don't create new config files.

**5. Vitest + SWC Decorator Support Working**
From Story 1.1:
> ✅ Vitest configured with SWC for decorator metadata support - tests passing (including DB failure case)

**Impact for Story 1.2:** All tests can safely use NestJS decorators (@Injectable, @Module, etc.) and NestJS testing utilities (Test.createTestingModule). The SWC transform is already configured in `vitest.config.ts`.

**6. CI Pipeline Established**
From Story 1.1:
> ✅ GitHub Actions CI pipeline configured for lint, test, build

**Impact for Story 1.2:** All new tests will automatically run in CI. Ensure all tests pass before marking story complete.

### 🎨 Key Implementation Decisions

#### Decision 1: TradingEngineService - In-Flight Operation Tracking

**Pattern:** Counter-based tracking with shutdown coordination

```typescript
export class TradingEngineService {
  private isShuttingDown = false;
  private inflightOperations = 0; // Track active cycles

  async executeCycle() {
    if (this.isShuttingDown) return; // Skip if shutting down

    this.inflightOperations++;
    try {
      // Placeholder pipeline (100ms delay for testing timing)
      // Future: data ingestion → detection → risk → execution
    } finally {
      this.inflightOperations--;
    }
  }

  isCycleInProgress(): boolean {
    return this.inflightOperations > 0;
  }
}
```

**Key points:**
- Use finally block to guarantee counter decrement
- Expose `isCycleInProgress()` for scheduler overlap prevention
- Implement `initiateShutdown()` and `waitForShutdown(timeoutMs)` methods

#### Decision 2: EngineLifecycleService - Minimal Coordination

**Pattern:** Coordinate shutdown, don't manage connections

```typescript
export class EngineLifecycleService implements OnApplicationBootstrap, OnApplicationShutdown {
  async onApplicationBootstrap() {
    // Verify DB connectivity (Prisma manages connection lifecycle)
    await this.prisma.$queryRaw`SELECT 1`;

    // Log config summary (NO sensitive data)
    this.logger.log({ pollingIntervalMs, nodeEnv, port: 8080 });
  }

  async onApplicationShutdown(signal?: string) {
    this.tradingEngine.initiateShutdown();
    await this.tradingEngine.waitForShutdown(12000); // 12s timeout (15s Docker grace - 3s buffer)
  }
}
```

**Key points:**
- Do NOT call `prisma.$connect()` or `$disconnect()` - Prisma handles this via its own hooks
- Shutdown timeout: 12 seconds (assumes 15s Docker grace period from Task 5)
- No complex error handling - let startup fail if DB unreachable

#### Decision 3: SchedulerService - SchedulerRegistry for Dynamic Config

**Pattern:** Runtime interval registration with overlap prevention

```typescript
export class SchedulerService implements OnModuleInit {
  onModuleInit() {
    const intervalMs = this.configService.get('POLLING_INTERVAL_MS', 30000);
    const interval = setInterval(() => this.handlePollingCycle(), intervalMs);
    this.schedulerRegistry.addInterval('pollingCycle', interval);
  }

  private async handlePollingCycle() {
    if (this.tradingEngine.isCycleInProgress()) return; // Prevent overlaps
    await this.tradingEngine.executeCycle();
  }
}
```

**Key points:**
- Use `SchedulerRegistry.addInterval()` not `@Interval()` decorator
- Check `isCycleInProgress()` before starting new cycle
- NestJS Schedule auto-clears intervals on shutdown - no manual cleanup

### ✅ Testing Requirements

#### Unit Tests Required

**1. EngineLifecycleService Tests (`engine-lifecycle.service.spec.ts`)**

```typescript
import { Test, TestingModule } from '@nestjs/testing';
import { ConfigService } from '@nestjs/config';
import { EngineLifecycleService } from './engine-lifecycle.service';
import { TradingEngineService } from './trading-engine.service';
import { PrismaService } from '../common/prisma.service';

describe('EngineLifecycleService', () => {
  let service: EngineLifecycleService;
  let prisma: PrismaService;
  let tradingEngine: TradingEngineService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        EngineLifecycleService,
        {
          provide: ConfigService,
          useValue: {
            get: vi.fn((key: string, defaultValue: any) => defaultValue),
          },
        },
        {
          provide: PrismaService,
          useValue: {
            $connect: vi.fn(),
            $disconnect: vi.fn(),
          },
        },
        {
          provide: TradingEngineService,
          useValue: {
            initiateShutdown: vi.fn(),
            waitForShutdown: vi.fn(),
          },
        },
      ],
    }).compile();

    service = module.get<EngineLifecycleService>(EngineLifecycleService);
    prisma = module.get<PrismaService>(PrismaService);
    tradingEngine = module.get<TradingEngineService>(TradingEngineService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  describe('onApplicationBootstrap', () => {
    it('should verify database connectivity on startup', async () => {
      await service.onApplicationBootstrap();
      expect(prisma.$connect).toHaveBeenCalled();
    });

    it('should throw if database connection fails', async () => {
      vi.mocked(prisma.$connect).mockRejectedValueOnce(new Error('Connection failed'));
      await expect(service.onApplicationBootstrap()).rejects.toThrow('Connection failed');
    });
  });

  describe('onApplicationShutdown', () => {
    it('should stop trading engine and close database', async () => {
      await service.onApplicationShutdown('SIGTERM');

      expect(tradingEngine.initiateShutdown).toHaveBeenCalled();
      expect(tradingEngine.waitForShutdown).toHaveBeenCalledWith(8000);
      expect(prisma.$disconnect).toHaveBeenCalled();
    });
  });
});
```

**2. TradingEngineService Tests (`trading-engine.service.spec.ts`)**

```typescript
import { Test, TestingModule } from '@nestjs/testing';
import { TradingEngineService } from './trading-engine.service';

describe('TradingEngineService', () => {
  let service: TradingEngineService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [TradingEngineService],
    }).compile();

    service = module.get<TradingEngineService>(TradingEngineService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  describe('executeCycle', () => {
    it('should execute placeholder pipeline and log timing', async () => {
      await service.executeCycle();
      expect(service.getInflightOperations()).toBe(0);
    });

    it('should skip cycle if shutting down', async () => {
      service.initiateShutdown();
      await service.executeCycle();
      // Should return immediately without incrementing inflightOperations
    });

    it('should track in-flight operations', async () => {
      const cyclePromise = service.executeCycle();
      expect(service.getInflightOperations()).toBe(1);
      await cyclePromise;
      expect(service.getInflightOperations()).toBe(0);
    });
  });

  describe('shutdown', () => {
    it('should wait for in-flight operations to complete', async () => {
      const cyclePromise = service.executeCycle();
      expect(service.getInflightOperations()).toBe(1);

      const shutdownPromise = service.waitForShutdown(5000);
      await cyclePromise; // Complete the cycle

      await shutdownPromise;
      expect(service.getInflightOperations()).toBe(0);
    });

    it('should timeout if operations take too long', async () => {
      // Simulate a long-running operation by not awaiting executeCycle
      service.executeCycle();

      const startTime = Date.now();
      await service.waitForShutdown(500); // 500ms timeout
      const duration = Date.now() - startTime;

      expect(duration).toBeGreaterThanOrEqual(500);
      expect(duration).toBeLessThan(600); // Should not wait longer than timeout
    });
  });
});
```

**3. SchedulerService Tests (`scheduler.service.spec.ts`)**

```typescript
import { Test, TestingModule } from '@nestjs/testing';
import { ConfigService } from '@nestjs/config';
import { SchedulerService } from './scheduler.service';
import { TradingEngineService } from './trading-engine.service';

describe('SchedulerService', () => {
  let service: SchedulerService;
  let tradingEngine: TradingEngineService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        SchedulerService,
        {
          provide: ConfigService,
          useValue: {
            get: vi.fn().mockReturnValue(30000),
          },
        },
        {
          provide: TradingEngineService,
          useValue: {
            executeCycle: vi.fn(),
          },
        },
      ],
    }).compile();

    service = module.get<SchedulerService>(SchedulerService);
    tradingEngine = module.get<TradingEngineService>(TradingEngineService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  describe('handlePollingCycle', () => {
    it('should call trading engine executeCycle', async () => {
      await service.handlePollingCycle();
      expect(tradingEngine.executeCycle).toHaveBeenCalled();
    });

    it('should not throw if executeCycle fails', async () => {
      vi.mocked(tradingEngine.executeCycle).mockRejectedValueOnce(new Error('Cycle failed'));
      await expect(service.handlePollingCycle()).resolves.not.toThrow();
    });
  });
});
```

#### Integration Test Required

**E2E Test: Complete Startup → Poll → Shutdown Cycle**

⚠️ **IMPORTANT: This test requires database setup or mocking**

```typescript
// test/core-lifecycle.e2e-spec.ts
describe('Core Lifecycle (e2e)', () => {
  let app: INestApplication;

  beforeEach(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [ConfigModule.forRoot({ envFilePath: '.env.test' }), CoreModule],
    })
      // Mock PrismaService to avoid needing real database
      .overrideProvider(PrismaService)
      .useValue({
        $queryRaw: vi.fn().mockResolvedValue([{ '?column?': 1 }]),
        $connect: vi.fn(),
        $disconnect: vi.fn(),
      })
      .compile();

    app = moduleFixture.createNestApplication();
    await app.init();
  });

  it('should start and shut down gracefully', async () => {
    expect(app).toBeDefined();
    await new Promise(resolve => setTimeout(resolve, 1000));
    await expect(app.close()).resolves.not.toThrow();
  }, 10000);
});
```

**Alternative:** Run E2E tests against real PostgreSQL using docker-compose with test-specific database.

**Test Coverage Requirements:**
- All three services: 80%+ line coverage
- All critical paths tested (startup success, startup failure, shutdown success, shutdown timeout)
- Integration test verifies end-to-end flow

### 📊 Git Intelligence Summary

**Recent Commits (Last 5):**
```
aa36155 feat: add initial project documentation for prediction market arbitrage system, including architecture, epics, and product requirements
05264ad chore: initial
```

**Analysis:**
- Only 2 commits exist in the repository - project is at the very beginning
- First commit (05264ad) is the repository initialization
- Second commit (aa36155) added all planning artifacts (PRD, Architecture, Epics)
- Story 1.1 work exists but hasn't been committed yet (based on completed story file)

**Implementation Patterns to Follow:**
- Use clear, descriptive commit messages with scope prefix (e.g., `feat(core):`, `test(core):`)
- Keep commits focused on single logical changes
- Follow conventional commits format established by planning docs commit

**No code patterns to extract yet** - Story 1.1 created the scaffold but the implementation hasn't been committed. This story will establish the first code patterns:
- NestJS service structure with lifecycle hooks
- Structured logging format
- Graceful shutdown patterns
- Test patterns with Vitest + NestJS testing utilities

### 🎯 Critical Implementation Checklist

Before marking Story 1.2 complete, verify ALL of the following:

**✅ Code Implementation**@@Interval
- [ ] `src/core/core.module.ts` created with all providers registered
- [ ] `src/core/engine-lifecycle.service.ts` implements OnApplicationBootstrap and OnApplicationShutdown
- [ ] `src/core/trading-engine.service.ts` has executeCycle(), initiateShutdown(), waitForShutdown()
- [ ] `src/core/scheduler.service.ts` uses @Interval decorator to trigger cycles
- [ ] `src/app.module.ts` imports CoreModule
- [ ] `@nestjs/schedule` added to package.json dependencies

**✅ Configuration**
- [ ] `.env.development` has POLLING_INTERVAL_MS=30000
- [ ] `.env.example` has POLLING_INTERVAL_MS documented
- [ ] `docker-compose.yml` engine service has `stop_grace_period: 15s`

**✅ Testing**
- [ ] `engine-lifecycle.service.spec.ts` - tests startup, shutdown, database connectivity
- [ ] `trading-engine.service.spec.ts` - tests cycle execution, shutdown, in-flight tracking
- [ ] `scheduler.service.spec.ts` - tests interval triggering, error handling
- [ ] `test/core-lifecycle.e2e-spec.ts` - integration test for full startup → shutdown flow
- [ ] All tests passing: `pnpm test`
- [ ] All tests passing in CI pipeline

**✅ Behavior Verification**
- [ ] `docker-compose up` starts engine, logs "Engine startup complete"
- [ ] Polling cycles execute every 30 seconds (check logs for "Starting trading cycle")
- [ ] Cycle timing is logged (e.g., "Trading cycle completed in 120ms")
- [ ] CTRL+C (SIGINT) triggers graceful shutdown with "Shutdown complete" log
- [ ] Database connections close cleanly (no Prisma warnings on shutdown)
- [ ] Health endpoint still returns 200 after startup (existing from Story 1.1)

**✅ Documentation**
- [ ] All three services have TypeDoc comments on public methods
- [ ] Co-located spec files exist for all services
- [ ] No TODO or FIXME comments left in code

**✅ Architecture Compliance**
- [ ] All files in correct locations per architecture.md
- [ ] Naming conventions followed (kebab-case files, PascalCase classes, camelCase methods)
- [ ] No forbidden dependencies (core/ only imports from common/ and platform libraries)
- [ ] Structured logging used (not console.log)
- [ ] No raw Error throws (would use SystemError hierarchy, but not needed yet)

### 📖 References & Source Documentation

**Primary Sources:**

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2] - Complete acceptance criteria and BDD scenarios
- [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions] - Lifecycle patterns and graceful shutdown requirements
- [Source: _bmad-output/planning-artifacts/architecture.md#Infrastructure & Deployment] - Docker health check integration and shutdown timing
- [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns - Logging] - Structured logging format requirements
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries] - Directory organization and module dependencies
- [Source: _bmad-output/implementation-artifacts/1-1-project-scaffold-development-environment.md] - Previous story completion notes and deviations

**NestJS Official Documentation:**

- [NestJS Lifecycle Events](https://docs.nestjs.com/fundamentals/lifecycle-events) - OnApplicationBootstrap, OnApplicationShutdown interfaces
- [NestJS Task Scheduling](https://docs.nestjs.com/techniques/task-scheduling) - @nestjs/schedule usage, @Interval decorator
- [NestJS Configuration](https://docs.nestjs.com/techniques/configuration) - ConfigService injection and environment variables
- [NestJS Testing](https://docs.nestjs.com/fundamentals/testing) - Test.createTestingModule patterns

**Related Stories & Dependencies:**

- **Story 1.1** (completed) - Provides project scaffold, Prisma setup, Docker configuration
- **Story 1.3** (next) - Will use TradingEngineService to integrate Kalshi connector into the pipeline
- **Story 1.5** (Epic 1) - Will add CorrelationIdInterceptor for tracking cycles across modules
- **Story 1.6** (Epic 1) - Will add NTP sync scheduling to SchedulerService

### 🚀 Next Steps After Story Completion

Once Story 1.2 is complete and all tests pass:

1. **Commit the work:**
   ```bash
   git add .
   git commit -m "feat(core): implement engine lifecycle and polling loop

   - Add EngineLifecycleService with startup/shutdown hooks
   - Add TradingEngineService with placeholder pipeline
   - Add SchedulerService for 30-second polling intervals
   - Implement graceful shutdown with in-flight operation tracking
   - Add comprehensive unit and integration tests
   - Configure POLLING_INTERVAL_MS environment variable

   Addresses Story 1.2 from Epic 1

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
   ```

2. **Update sprint status:**
   - Change `1-2-core-engine-lifecycle-graceful-shutdown: backlog` to `ready-for-dev` in `sprint-status.yaml`

3. **Proceed to Story 1.3:**
   - Kalshi Platform Connector & Authentication
   - Will integrate the Kalshi connector into the TradingEngineService pipeline

4. **Test the deployment:**
   ```bash
   docker-compose build
   docker-compose up
   # Verify logs show polling cycles and graceful shutdown
   ```

### ⚠️ Common Pitfalls & How to Avoid Them

**Pitfall 1: Using @Interval decorator for dynamic config**
- ❌ `@Interval(this.configService.get('INTERVAL'))` - decorator doesn't support dynamic values
- ✅ Use `SchedulerRegistry.addInterval()` with runtime config value

**Pitfall 2: Not tracking in-flight operations**
- ❌ Shutting down immediately when SIGTERM received
- ✅ Use inflightOperations counter and wait with timeout

**Pitfall 3: Throwing errors from shutdown handlers**
- ❌ Throwing errors in onApplicationShutdown (prevents clean shutdown)
- ✅ Log errors but complete shutdown gracefully

**Pitfall 4: Managing Prisma connection lifecycle**
- ❌ Calling `prisma.$connect()` and `$disconnect()` manually - Prisma manages this
- ✅ Only verify connectivity with a test query (`$queryRaw\`SELECT 1\``)

**Pitfall 5: Using process.on('SIGTERM') directly**
- ❌ Bypassing NestJS lifecycle system
- ✅ Implement OnApplicationShutdown interface

**Pitfall 6: Not testing shutdown scenarios**
- ❌ Only testing happy path startup
- ✅ Test shutdown timeout, database failure, in-flight operations

**Pitfall 7: Not preventing overlapping cycles**
- ❌ Starting new cycle while previous one still running - can cause race conditions
- ✅ Check `isCycleInProgress()` before starting new cycle in scheduler

**Pitfall 8: Creating utils/ directory**
- ❌ Putting helper functions in `src/utils/`
- ✅ Keep helpers in module scope or `src/common/` for cross-cutting concerns

### 🎓 Learning Opportunities

**NestJS Lifecycle Mastery:**
This story provides hands-on experience with NestJS lifecycle hooks - a critical pattern for production systems. Understanding when `onApplicationBootstrap` vs `onModuleInit` runs, and how `onApplicationShutdown` integrates with Docker's grace period, is essential for building resilient services.

**Graceful Shutdown Patterns:**
The in-flight operation tracking pattern demonstrated here is a production-grade technique applicable to any long-running service. This same pattern will be used in Epic 5 (Trade Execution) to prevent partial position fills during deployment.

**Testing Lifecycle Hooks:**
Testing NestJS lifecycle hooks requires understanding module compilation and mocking. The test patterns in this story establish best practices for the entire project.

**Architecture Compliance:**
This story enforces strict architecture boundaries - `core/` orchestrates but doesn't implement domain logic, `common/` provides shared infrastructure, and modules remain loosely coupled. These patterns scale to complex systems.

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

N/A - Implementation completed without blocking issues

### Completion Notes List

✅ **Task 1 - EngineLifecycleService**: Implemented lifecycle hooks using NestJS OnApplicationBootstrap and OnApplicationShutdown interfaces. Database connectivity verified via $queryRaw without managing Prisma connection lifecycle (Prisma handles this automatically). Graceful shutdown coordinates with TradingEngineService with 12-second timeout (15s Docker grace - 3s buffer).

✅ **Task 2 - TradingEngineService**: Implemented main polling loop orchestrator with placeholder pipeline (100ms delay). In-flight operation tracking using counter pattern ensures graceful shutdown. Cycle timing logged for performance monitoring. Shutdown flag prevents new cycles during termination.

✅ **Task 3 - SchedulerService**: Integrated @nestjs/schedule with SchedulerRegistry for dynamic polling interval configuration (30s default). Prevents overlapping cycles via isCycleInProgress() check. Logs initialization, skipped intervals, and errors.

✅ **Task 4 - CoreModule**: Created module wiring all three services with ScheduleModule.forRoot() for scheduler support. PrismaService included for DI. Exported TradingEngineService for future monitoring integration. Imported into AppModule.

✅ **Task 5 - Configuration**: Added POLLING_INTERVAL_MS to .env.development and .env.example (30000ms default). Updated docker-compose.yml with stop_grace_period: 15s for graceful shutdown window.

✅ **Task 6 - Comprehensive Tests**: 36 tests total - 11 tests for EngineLifecycleService (startup verification, config validation, shutdown coordination, error handling), 11 tests for TradingEngineService (cycle execution, in-flight tracking, shutdown timeout), 8 tests for SchedulerService (interval registration, overlap prevention, error resilience), 4 E2E tests for complete lifecycle (startup → polling → shutdown), 2 app controller tests. All tests passing with 100% coverage of critical paths.

**Technical Decisions:**
- Used SchedulerRegistry instead of @Interval decorator to support runtime config values
- Implemented counter-based in-flight operation tracking for shutdown coordination
- PrismaService lifecycle NOT managed by EngineLifecycleService (Prisma handles via onModuleInit/onModuleDestroy)
- Structured logging with timestamp, module, and metadata for all lifecycle events
- Error handling graceful - shutdown completes even if trading engine fails

**Code Review Fixes Applied:**
- ✅ Added missing E2E integration test (test/core-lifecycle.e2e-spec.ts) - 4 tests covering startup → polling → shutdown cycle
- ✅ Added configuration validation for POLLING_INTERVAL_MS (1s min, 5min max)
- ✅ Standardized structured logging - all logs now include `module: 'core'` field consistently
- ✅ Extracted magic number SHUTDOWN_CHECK_INTERVAL_MS = 100 as class constant
- ✅ Updated File List with pnpm-lock.yaml and vitest.config.ts changes
- ✅ Updated vitest.config.ts to include E2E test pattern
- ✅ Fixed test/app.e2e-spec.ts to use Fastify adapter
- ✅ **Eliminated PrismaService duplicate registration** - Created `PersistenceModule` as `@Global()` module, single source of truth for database access
- 📝 EventEmitter2 integration deferred to monitoring module implementation (requires new infrastructure)

### File List

**New Files:**
- pm-arbitrage-engine/src/core/core.module.ts
- pm-arbitrage-engine/src/core/engine-lifecycle.service.ts
- pm-arbitrage-engine/src/core/engine-lifecycle.service.spec.ts
- pm-arbitrage-engine/src/core/trading-engine.service.ts
- pm-arbitrage-engine/src/core/trading-engine.service.spec.ts
- pm-arbitrage-engine/src/core/scheduler.service.ts
- pm-arbitrage-engine/src/core/scheduler.service.spec.ts
- pm-arbitrage-engine/src/common/persistence.module.ts
- pm-arbitrage-engine/test/core-lifecycle.e2e-spec.ts

**Modified Files:**
- pm-arbitrage-engine/src/app.module.ts (added CoreModule import)
- pm-arbitrage-engine/.env.development (added POLLING_INTERVAL_MS)
- pm-arbitrage-engine/.env.example (added POLLING_INTERVAL_MS documentation)
- pm-arbitrage-engine/docker-compose.yml (added stop_grace_period: 15s)
- pm-arbitrage-engine/package.json (added @nestjs/schedule dependency)
- pm-arbitrage-engine/pnpm-lock.yaml (dependency updates for @nestjs/schedule)
- pm-arbitrage-engine/vitest.config.ts (added E2E test pattern to include path)
- pm-arbitrage-engine/test/app.e2e-spec.ts (updated for Fastify adapter)

