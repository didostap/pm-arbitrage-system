# Story 4.1: Position Sizing & Portfolio Limits

Status: done

## Story

As an operator,
I want the system to enforce maximum position size per pair and maximum simultaneous open pairs,
so that no single trade or accumulation of trades can over-expose my capital.

**FRs covered:** FR-RM-01 (position size capped at 3% of bankroll per pair), FR-RM-02 (max 10 simultaneous open pairs)

## Acceptance Criteria

### AC1: Position Size Capped at 3% of Bankroll

**Given** an opportunity is being evaluated for execution
**When** the risk manager validates the position
**Then** position size is capped at 3% of bankroll per arbitrage pair (FR-RM-01)
**And** the calculated position size in USD is included in the `RiskDecision` response
**And** position sizing uses `Decimal.js` (via `FinancialDecimal`) for precision

### AC2: Maximum Simultaneous Open Pairs Enforced

**Given** the operator has configured a maximum of 10 simultaneous open pairs
**When** a new opportunity passes edge validation
**Then** the trade is rejected if it would exceed the max open pairs limit (FR-RM-02)
**And** rejection is logged with current position count and limit
**And** a `risk.limit.approached` event is emitted when count reaches 80% of max (8 of 10)

> **Note:** Position count is initialized to 0 on startup; actual increment/decrement is deferred to Epic 5 execution integration. Until Epic 5, all opportunities will pass the open-pairs check.

### AC3: IRiskManager Interface Defined

**Given** the `IRiskManager` interface is defined in `common/interfaces/`
**When** the risk manager service is implemented
**Then** it exposes `validatePosition(opportunity: EnrichedOpportunity): Promise<RiskDecision>` that returns approve/reject with reasoning
**And** it exposes `getCurrentExposure(): RiskExposure` for dashboard queries
**And** it exposes `getOpenPositionCount(): number` for pipeline checks
**And** the interface is exported from `common/interfaces/index.ts`

### AC4: RiskLimitError Created

**Given** a risk limit is breached
**When** the risk manager rejects a trade
**Then** it throws `RiskLimitError` (codes 3000-3999) from `common/errors/`
**And** the error includes `limitType`, `currentValue`, and `threshold` properties
**And** codes used: 3001 = position size exceeded, 3002 = max open pairs exceeded

### AC5: Risk Configuration from Environment

**Given** bankroll and risk parameters are configured
**When** the engine starts
**Then** bankroll amount (`RISK_BANKROLL_USD`), position size limit % (`RISK_MAX_POSITION_PCT`), and max open pairs (`RISK_MAX_OPEN_PAIRS`) are loaded from environment config
**And** invalid values (negative bankroll, >100% position size, non-positive max pairs) are rejected at startup via `ConfigValidationError`
**And** validated config values are logged at startup (bankroll amount masked to order of magnitude for security)

### AC6: Prisma Migration for risk_states Table

**Given** the risk manager needs to track state
**When** this story is implemented
**Then** a `risk_states` table is created via Prisma migration with fields:
- `id` (UUID, primary key)
- `daily_pnl` (Decimal, default 0) -- placeholder for Story 4.2
- `open_position_count` (Int, default 0)
- `last_reset_timestamp` (timestamptz, nullable) -- for Story 4.2 daily reset
- `total_capital_deployed` (Decimal, default 0)
- `created_at` (timestamptz, default now)
- `updated_at` (timestamptz, auto-updated)
**And** only one row exists (singleton pattern, enforced by application logic and a unique constraint on a `singleton_key` column defaulting to `'default'`)

### AC7: Risk Events Emitted

**Given** the risk manager evaluates a position
**When** a limit is approached (80% threshold)
**Then** a `LimitApproachedEvent` is emitted via EventEmitter2 with `limitType`, `currentValue`, `threshold`, and `percentUsed`
**And** the event class is created in `common/events/risk.events.ts`
**And** the event is exported from `common/events/index.ts`

### AC8: Trading Engine Integration Point

**Given** the trading engine pipeline has a placeholder at STEP 3 for risk validation
**When** this story is implemented
**Then** the `TradingEngineService` calls `riskManager.validatePosition()` for each actionable opportunity from the edge calculation result
**And** approved opportunities proceed (logged, placeholder for Epic 5 execution)
**And** rejected opportunities are logged with the rejection reason
**And** the `CoreModule` imports `RiskManagementModule`

### AC9: Risk Types Created

**Given** the risk module needs shared types
**When** this story is implemented
**Then** `RiskDecision`, `RiskExposure`, and `RiskConfig` types are created in `common/types/risk.type.ts`
**And** they are exported from `common/types/index.ts`

### AC10: All Tests Pass

**Given** all Story 4.1 changes are complete
**When** `pnpm test` runs
**Then** all 381 existing tests continue to pass
**And** new tests for `RiskManagerService` add 12+ test cases
**And** `pnpm lint` passes with no errors

## Tasks / Subtasks

- [x] Task 1: Create RiskLimitError class (AC: #4)
  - [x] 1.1 Create `src/common/errors/risk-limit-error.ts` extending `SystemError`
  - [x] 1.2 Add `limitType`, `currentValue`, `threshold` properties
  - [x] 1.3 Define `RISK_ERROR_CODES` constant: `POSITION_SIZE_EXCEEDED: 3001`, `MAX_OPEN_PAIRS_EXCEEDED: 3002`
  - [x] 1.4 Export from `src/common/errors/index.ts`

- [x] Task 2: Create Risk Types (AC: #9)
  - [x] 2.1 Create `src/common/types/risk.type.ts`
  - [x] 2.2 Define `RiskDecision` interface: `{ approved: boolean; reason: string; maxPositionSizeUsd: Decimal; currentOpenPairs: number; }`
  - [x] 2.3 Define `RiskExposure` interface: `{ openPairCount: number; totalCapitalDeployed: Decimal; bankrollUsd: Decimal; availableCapital: Decimal; }`
  - [x] 2.4 Define `RiskConfig` interface: `{ bankrollUsd: number; maxPositionPct: number; maxOpenPairs: number; }` (bankrollUsd is `number` from env; wrap in `FinancialDecimal` at calculation boundary in service layer)
  - [x] 2.5 Export from `src/common/types/index.ts`

- [x] Task 3: Create IRiskManager Interface (AC: #3)
  - [x] 3.1 Create `src/common/interfaces/risk-manager.interface.ts`
  - [x] 3.2 Define `validatePosition(opportunity: EnrichedOpportunity): Promise<RiskDecision>`
  - [x] 3.3 Define `getCurrentExposure(): RiskExposure`
  - [x] 3.4 Define `getOpenPositionCount(): number`
  - [x] 3.5 Export from `src/common/interfaces/index.ts`

- [x] Task 4: Create Risk Event Classes (AC: #7)
  - [x] 4.1 Create `src/common/events/risk.events.ts`
  - [x] 4.2 Define `LimitApproachedEvent` extending `BaseEvent` with: `limitType`, `currentValue`, `threshold`, `percentUsed`
  - [x] 4.3 Define `LimitBreachedEvent` extending `BaseEvent` with: `limitType`, `currentValue`, `threshold` (placeholder for Story 4.2)
  - [x] 4.4 Verify `EVENT_NAMES.LIMIT_APPROACHED` and `EVENT_NAMES.LIMIT_BREACHED` already exist in `event-catalog.ts` (they do -- no changes needed to catalog)
  - [x] 4.5 Export from `src/common/events/index.ts`

- [x] Task 5: Prisma Migration for risk_states (AC: #6)
  - [x] 5.1 Add `RiskState` model to `prisma/schema.prisma`
  - [x] 5.2 Use `@@map("risk_states")` and `@map` annotations for snake_case columns
  - [x] 5.3 Run `pnpm prisma migrate dev --name add-risk-states-table`
  - [x] 5.4 Run `pnpm prisma generate`

- [x] Task 6: Create RiskManagementModule and RiskManagerService (AC: #1, #2, #3, #5, #8)
  - [x] 6.1 Create `src/modules/risk-management/risk-management.module.ts`
  - [x] 6.2 Create `src/modules/risk-management/risk-manager.service.ts` implementing `IRiskManager`
  - [x] 6.3 Inject `ConfigService`, `PrismaService`, `EventEmitter2`
  - [x] 6.4 Implement `OnModuleInit` for config validation and state initialization
  - [x] 6.5 Implement `validatePosition()`: check open pair count, calculate max position size (3% bankroll)
  - [x] 6.6 Implement `getCurrentExposure()`: return current risk state snapshot
  - [x] 6.7 Implement `getOpenPositionCount()`: return current open pair count
  - [x] 6.8 Emit `LimitApproachedEvent` when open pairs reach 80% of max
  - [x] 6.9 Register module providers and exports

- [x] Task 7: Add Environment Config Variables (AC: #5)
  - [x] 7.1 Add `RISK_BANKROLL_USD`, `RISK_MAX_POSITION_PCT`, `RISK_MAX_OPEN_PAIRS` to `.env.example`
  - [x] 7.2 Add same to `.env.development` with sensible defaults (bankroll=10000, pct=0.03, pairs=10)

- [x] Task 8: Integrate into Trading Engine (AC: #8)
  - [x] 8.1 Import `RiskManagementModule` in `CoreModule`
  - [x] 8.2 Inject `RiskManagerService` (via `IRiskManager` token) into `TradingEngineService`
  - [x] 8.3 After edge calculation, iterate `edgeResult.opportunities` and call `validatePosition()` for each
  - [x] 8.4 Log approved/rejected decisions with correlationId
  - [x] 8.5 Approved opportunities: log as "ready for execution" (Epic 5 placeholder)

- [x] Task 9: Write Tests (AC: #10)
  - [x] 9.1 Create `src/modules/risk-management/risk-manager.service.spec.ts`
  - [x] 9.2 Test: validates config on module init (rejects negative bankroll, >1.0 pct, non-positive pairs)
  - [x] 9.3 Test: approves opportunity when under all limits
  - [x] 9.4 Test: rejects opportunity when max open pairs reached
  - [x] 9.5 Test: calculates position size as bankroll * maxPositionPct
  - [x] 9.6 Test: returns correct risk exposure snapshot
  - [x] 9.7 Test: emits LimitApproachedEvent when open pairs at 80% of max
  - [x] 9.8 Test: does NOT emit LimitApproachedEvent when below 80%
  - [x] 9.9 Test: handles zero bankroll gracefully (rejects all trades)
  - [x] 9.10 Test: uses Decimal.js for position size calculation
  - [x] 9.11 Test: logs rejection with current count and limit
  - [x] 9.12 Test: RiskLimitError has correct code, limitType, currentValue, threshold
  - [x] 9.13 Test: upserts risk state to database on position count change
  - [x] 9.14 Test: trading engine calls validatePosition for each opportunity
  - [x] 9.15 Test: trading engine logs approved and rejected decisions separately
  - [x] 9.16 Run full regression: `pnpm test` -- all tests pass

- [x] Task 10: Lint & Final Check (AC: #10)
  - [x] 10.1 Run `pnpm lint` and fix any issues
  - [x] 10.2 Verify no import boundary violations per CLAUDE.md rules

## Dev Notes

### Architecture Constraints

- `RiskManagerService` lives in `src/modules/risk-management/` per architecture spec
- Allowed imports per CLAUDE.md dependency rules:
  - `modules/risk-management/` -> `common/` (interfaces, errors, events, types)
  - `modules/risk-management/` -> `persistence/` (via globally exported PrismaService)
  - `core/` -> `modules/risk-management/` (orchestrates via IRiskManager interface)
- **FORBIDDEN:** `risk-management/` must NOT import from `connectors/`, `modules/execution/`, or any other module directly
- The trading engine imports risk management through the module system, NOT direct service import -- use NestJS DI token pattern

### DI Token Pattern for IRiskManager

Use a string injection token so the trading engine depends on the interface, not the concrete service:

```typescript
// In risk-management.module.ts
const RISK_MANAGER_TOKEN = 'IRiskManager';

@Module({
  providers: [
    {
      provide: RISK_MANAGER_TOKEN,
      useClass: RiskManagerService,
    },
  ],
  exports: [RISK_MANAGER_TOKEN],
})
export class RiskManagementModule {}

// In trading-engine.service.ts
constructor(
  @Inject('IRiskManager') private readonly riskManager: IRiskManager,
) {}
```

### RiskLimitError Pattern (Follow SystemHealthError)

```typescript
import { SystemError, RetryStrategy } from './system-error';

export class RiskLimitError extends SystemError {
  constructor(
    code: number,
    message: string,
    severity: 'critical' | 'error' | 'warning',
    public readonly limitType: string,
    public readonly currentValue: number,
    public readonly threshold: number,
    retryStrategy?: RetryStrategy,
    metadata?: Record<string, unknown>,
  ) {
    super(code, message, severity, retryStrategy, metadata);
  }
}

export const RISK_ERROR_CODES = {
  POSITION_SIZE_EXCEEDED: 3001,
  MAX_OPEN_PAIRS_EXCEEDED: 3002,
  DAILY_LOSS_LIMIT_BREACHED: 3003, // Story 4.2
  BUDGET_RESERVATION_FAILED: 3004, // Story 4.4
} as const;
```

### Risk Event Classes (Follow Existing Pattern)

```typescript
import { BaseEvent } from './base.event';

export class LimitApproachedEvent extends BaseEvent {
  constructor(
    public readonly limitType: string,
    public readonly currentValue: number,
    public readonly threshold: number,
    public readonly percentUsed: number,
    correlationId?: string,
  ) {
    super(correlationId);
  }
}

export class LimitBreachedEvent extends BaseEvent {
  constructor(
    public readonly limitType: string,
    public readonly currentValue: number,
    public readonly threshold: number,
    correlationId?: string,
  ) {
    super(correlationId);
  }
}
```

### Prisma Model Definition

```prisma
model RiskState {
  id                    String   @id @default(uuid()) @map("id")
  singletonKey          String   @unique @default("default") @map("singleton_key")
  dailyPnl              Decimal  @default(0) @map("daily_pnl") @db.Decimal(20, 8)
  openPositionCount     Int      @default(0) @map("open_position_count")
  lastResetTimestamp     DateTime? @map("last_reset_timestamp") @db.Timestamptz
  totalCapitalDeployed  Decimal  @default(0) @map("total_capital_deployed") @db.Decimal(20, 8)
  createdAt             DateTime @default(now()) @map("created_at") @db.Timestamptz
  updatedAt             DateTime @updatedAt @map("updated_at") @db.Timestamptz

  @@map("risk_states")
}
```

### Config Validation Pattern (Follow EdgeCalculatorService)

```typescript
@Injectable()
export class RiskManagerService implements IRiskManager, OnModuleInit {
  private readonly logger = new Logger(RiskManagerService.name);
  private config!: RiskConfig;

  constructor(
    private readonly configService: ConfigService,
    private readonly prisma: PrismaService,
    private readonly eventEmitter: EventEmitter2,
  ) {}

  onModuleInit(): void {
    const bankroll = this.configService.get<number>('RISK_BANKROLL_USD');
    const maxPct = this.configService.get<number>('RISK_MAX_POSITION_PCT', 0.03);
    const maxPairs = this.configService.get<number>('RISK_MAX_OPEN_PAIRS', 10);

    if (!bankroll || bankroll <= 0) {
      throw new ConfigValidationError('RISK_BANKROLL_USD must be a positive number');
    }
    if (maxPct <= 0 || maxPct > 1) {
      throw new ConfigValidationError('RISK_MAX_POSITION_PCT must be between 0 and 1');
    }
    if (maxPairs <= 0 || !Number.isInteger(maxPairs)) {
      throw new ConfigValidationError('RISK_MAX_OPEN_PAIRS must be a positive integer');
    }

    this.config = { bankrollUsd: bankroll, maxPositionPct: maxPct, maxOpenPairs: maxPairs };
    this.logger.log({
      message: 'Risk manager configuration validated',
      data: {
        bankrollMagnitude: `$${Math.pow(10, Math.floor(Math.log10(bankroll)))}+`,
        maxPositionPct: maxPct,
        maxOpenPairs: maxPairs,
      },
    });
  }
}
```

### Position Sizing Logic

Position size calculation for this story is straightforward:

```typescript
const maxPositionSizeUsd = new FinancialDecimal(this.config.bankrollUsd)
  .mul(new FinancialDecimal(this.config.maxPositionPct));
```

The `recommendedPositionSize` field on `EnrichedOpportunity` is `null` -- the risk manager returns the max size in `RiskDecision.maxPositionSizeUsd` rather than mutating the opportunity object. Epic 5's execution module will use this value.

### In-Memory Position Count (MVP)

For MVP, the risk manager tracks open position count **in-memory** (initialized from DB on startup, updated via method calls from execution module in Epic 5). This story only sets up the framework:
- `openPositionCount` starts at 0 on startup (no positions exist pre-Epic 5)
- The `risk_states` table persists the count for crash recovery
- Epic 5 will call risk manager methods to increment/decrement count on trade fill/exit

### Trading Engine Integration

The trading engine currently ends at edge calculation. Add risk validation after:

```typescript
// STEP 3: Risk Validation (Epic 4)
const riskResults = [];
for (const opportunity of edgeResult.opportunities) {
  const decision = await this.riskManager.validatePosition(opportunity);
  riskResults.push({ opportunity, decision });
  this.logger.log({
    message: decision.approved
      ? 'Opportunity approved by risk manager'
      : `Opportunity rejected: ${decision.reason}`,
    correlationId: getCorrelationId(),
    data: {
      pair: `${opportunity.dislocation.pairConfig.polymarketContractId}:${opportunity.dislocation.pairConfig.kalshiContractId}`,
      netEdge: opportunity.netEdge.toString(),
      approved: decision.approved,
      maxPositionSizeUsd: decision.maxPositionSizeUsd.toString(),
      currentOpenPairs: decision.currentOpenPairs,
    },
  });
}

// STEP 4: Execution (Epic 5) - placeholder
```

### What NOT to Do (Scope Guard)

- Do NOT implement daily loss limit tracking -- that's Story 4.2
- Do NOT implement operator risk override endpoint -- that's Story 4.3
- Do NOT implement execution locking or budget reservation -- that's Story 4.4
- Do NOT implement correlation cluster tracking -- that's Epic 9 (Story 9.1)
- Do NOT implement confidence-adjusted position sizing -- that's Epic 9 (Story 9.3)
- Do NOT modify `EnrichedOpportunity.recommendedPositionSize` type from `null` -- Epic 5 will update the type
- Do NOT implement actual order submission -- that's Epic 5
- Do NOT create REST endpoints for risk state -- that's Epic 7
- Do NOT implement `dailyPnl` tracking or midnight reset -- that's Story 4.2

### Existing Codebase Patterns to Follow

- **File naming:** kebab-case (`risk-manager.service.ts`)
- **Module registration:** See `arbitrage-detection.module.ts` or `contract-matching.module.ts`
- **Logging:** NestJS `Logger` with structured JSON: `this.logger.log({ message, correlationId, data })`
- **Config access:** `ConfigService` from `@nestjs/config` (see `EdgeCalculatorService` for pattern)
- **Prisma access:** Inject `PrismaService` directly (globally available via `@Global()`)
- **Event emission:** `this.eventEmitter.emit(EVENT_NAMES.LIMIT_APPROACHED, new LimitApproachedEvent(...))`
- **Error class:** Follow `SystemHealthError` pattern (extends `SystemError`, adds domain properties)
- **Test framework:** Vitest + `Test.createTestingModule()` from `@nestjs/testing`
- **Decimal math:** Use `FinancialDecimal` from `common/utils/financial-math.ts` for all monetary calculations

### Testing Strategy

- Mock `PrismaService` with mock `riskState` methods (`findFirst`, `upsert`)
- Mock `ConfigService.get()` to return test config values
- Mock `EventEmitter2.emit()` to verify event emission
- Create mock `EnrichedOpportunity` objects with known values
- Test both approve and reject paths
- Test config validation error cases
- Do NOT use a real database -- unit tests only with mocked Prisma

### Dependencies -- All Already Installed

| Package | Purpose | Installed In |
|---------|---------|-------------|
| `@prisma/client` | Database access via PrismaService | Epic 1 |
| `prisma` | Migration CLI | Epic 1 |
| `@nestjs/common` | OnModuleInit, Logger, Injectable, Inject | Epic 1 |
| `@nestjs/config` | ConfigService for env vars | Epic 1 |
| `@nestjs/event-emitter` | EventEmitter2 for domain events | Epic 1 |
| `decimal.js` | FinancialDecimal for position sizing | Epic 3 |

No new dependencies needed.

### Previous Story Intelligence (3.4)

- **381 tests passing** -- regression gate baseline
- `ContractMatchSyncService` demonstrates OnModuleInit + PrismaService pattern
- `PrismaService` is `@Global()` via `PersistenceModule` -- available everywhere without imports
- Existing tables: `system_metadata`, `order_book_snapshots`, `platform_health_logs`, `contract_matches`
- `ConfigValidationError` already exists in `common/errors/` for startup validation failures
- `FinancialDecimal` with precision=20 for all monetary calculations
- Event pattern: extend `BaseEvent`, use `EVENT_NAMES` catalog, emit via `EventEmitter2`

### Git Intelligence

Recent engine commits follow pattern: `feat: <description>`. Story 4.1 should use:
- `feat: add risk management module with position sizing and portfolio limits`

### Project Structure Notes

New files to create:
```
src/common/errors/risk-limit-error.ts
src/common/types/risk.type.ts
src/common/interfaces/risk-manager.interface.ts
src/common/events/risk.events.ts
src/modules/risk-management/risk-management.module.ts
src/modules/risk-management/risk-manager.service.ts
src/modules/risk-management/risk-manager.service.spec.ts
prisma/migrations/<timestamp>_add_risk_states_table/migration.sql  (auto-generated)
```

Modified files:
```
prisma/schema.prisma                          (add RiskState model)
src/common/errors/index.ts                    (export RiskLimitError)
src/common/types/index.ts                     (export risk types)
src/common/interfaces/index.ts                (export IRiskManager)
src/common/events/index.ts                    (export risk events)
src/core/core.module.ts                       (import RiskManagementModule)
src/core/trading-engine.service.ts            (inject IRiskManager, add STEP 3)
.env.example                                  (add RISK_* variables)
.env.development                              (add RISK_* variables)
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1 -- acceptance criteria, BDD scenarios]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2 -- downstream scope (daily loss limit, NOT to build)]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.4 -- downstream scope (execution locking, NOT to build)]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture -- PostgreSQL, Prisma pattern]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns -- synchronous hot path]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error Taxonomy -- RiskLimitError 3000-3999]
- [Source: pm-arbitrage-engine/src/common/errors/system-error.ts -- SystemError base class]
- [Source: pm-arbitrage-engine/src/common/errors/system-health-error.ts -- subclass pattern]
- [Source: pm-arbitrage-engine/src/common/errors/platform-api-error.ts -- error codes pattern]
- [Source: pm-arbitrage-engine/src/common/events/base.event.ts -- BaseEvent pattern]
- [Source: pm-arbitrage-engine/src/common/events/event-catalog.ts -- LIMIT_APPROACHED, LIMIT_BREACHED]
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/types/enriched-opportunity.type.ts -- EnrichedOpportunity]
- [Source: pm-arbitrage-engine/src/modules/arbitrage-detection/edge-calculator.service.ts -- ConfigService validation pattern]
- [Source: pm-arbitrage-engine/src/core/trading-engine.service.ts -- STEP 3 placeholder at line 104]
- [Source: pm-arbitrage-engine/src/core/core.module.ts -- module import pattern]
- [Source: pm-arbitrage-engine/prisma/schema.prisma -- existing models and conventions]
- [Source: CLAUDE.md#Module Dependency Rules -- risk-management allowed imports]
- [Source: CLAUDE.md#Error Handling -- SystemError hierarchy]
- [Source: CLAUDE.md#Domain Rules -- 3% bankroll, max pairs]
- [Source: _bmad-output/implementation-artifacts/3-4-contract-match-approval-workflow-mvp.md -- PrismaService pattern, test count baseline]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Fixed `common/` import boundary: `IRiskManager` uses `unknown` param type instead of importing `EnrichedOpportunity` from `modules/`
- Fixed `PrismaService` import path: `../../common/prisma.service` (not `../../persistence/prisma.service`)
- Fixed `ConfigService.get` returning strings from env: added `Number()` conversion for all risk config values
- Added `RISK_*` env vars to e2e test files to prevent `ConfigValidationError` on AppModule init

### Completion Notes List

- All 10 tasks completed with 16 new tests (397 total, 0 failures)
- `RiskLimitError` with codes 3001-3004 created following `SystemHealthError` pattern
- `RiskDecision`, `RiskExposure`, `RiskConfig` types in `common/types/`
- `IRiskManager` interface in `common/interfaces/` with `unknown` param to avoid import boundary violation
- `LimitApproachedEvent` and `LimitBreachedEvent` in `common/events/`
- `risk_states` Prisma table with singleton pattern
- `RiskManagerService` validates config on init, checks open pairs limit, emits approach events at 80%
- Trading engine iterates `edgeResult.opportunities` calling `validatePosition()` for each
- Position sizing uses `FinancialDecimal` (Decimal.js) for precision

### File List

New files:
- `src/common/errors/risk-limit-error.ts`
- `src/common/types/risk.type.ts`
- `src/common/interfaces/risk-manager.interface.ts`
- `src/common/events/risk.events.ts`
- `src/modules/risk-management/risk-management.module.ts`
- `src/modules/risk-management/risk-manager.service.ts`
- `src/modules/risk-management/risk-manager.service.spec.ts`
- `prisma/migrations/20260217002511_add_risk_states_table/migration.sql`

Modified files:
- `prisma/schema.prisma` (added RiskState model)
- `src/common/errors/index.ts` (export RiskLimitError)
- `src/common/types/index.ts` (export risk types)
- `src/common/interfaces/index.ts` (export IRiskManager)
- `src/common/events/index.ts` (export risk events)
- `src/core/core.module.ts` (import RiskManagementModule)
- `src/core/trading-engine.service.ts` (inject IRiskManager, add STEP 3 risk validation)
- `src/core/trading-engine.service.spec.ts` (add IRiskManager mock + integration tests)
- `.env.example` (add RISK_* variables)
- `.env.development` (add RISK_* variables)
- `test/app.e2e-spec.ts` (add RISK_* env vars)
- `test/core-lifecycle.e2e-spec.ts` (add RISK_* env vars)
- `test/logging.e2e-spec.ts` (add RISK_* env vars)
