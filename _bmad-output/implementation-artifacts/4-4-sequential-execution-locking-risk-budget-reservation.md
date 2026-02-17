# Story 4.4: Sequential Execution Locking & Risk Budget Reservation

Status: done

## Story

As an operator,
I want concurrent opportunities to be evaluated and executed sequentially with atomic risk budget reservations,
so that two simultaneous opportunities can't both pass risk checks and then collectively breach limits.

## Acceptance Criteria (BDD)

### AC1: Sequential Evaluation of Concurrent Opportunities
**Given** multiple opportunities are detected in the same cycle,
**When** they are ranked by expected edge (highest first) by the detection module,
**Then** the execution queue receives them pre-ranked and processes each sequentially, not in parallel.

### AC2: Atomic Budget Reservation on Passing Risk Validation
**Given** an opportunity is next in the execution queue,
**When** the execution lock is acquired,
**Then** `reserveBudget()` is called which internally validates budget availability (halt check, open pairs including reserved slots, available capital including reserved capital) and atomically reserves the risk budget (position count, daily capital, correlation exposure placeholder),
**And** subsequent opportunities see the updated budget including the reservation.

**Precise pipeline per opportunity:** `lock.acquire()` → `riskManager.reserveBudget()` (validates + reserves atomically) → placeholder execute → `commitReservation()` or `releaseReservation()` → `lock.release()`. Note: `validatePosition()` is NOT called separately inside the queue — `reserveBudget()` performs its own validation. However, `validatePosition()` is still called as a pre-filter in `executeCycle()` before opportunities enter the queue (cheap pre-screen), and it accounts for active reservations in its budget calculations.

### AC3: Reservation Commit on Successful Execution
**Given** execution completes for a reserved opportunity,
**When** both legs fill successfully,
**Then** the reservation is committed (budget permanently allocated to new position).

### AC4: Reservation Release on Execution Failure
**Given** execution fails for a reserved opportunity,
**When** the opportunity is abandoned,
**Then** the reservation is released (budget returned to available pool),
**And** the next opportunity in the queue can proceed.

### AC5: Global Lock Enforcement
**Given** the execution lock service is implemented,
**When** I inspect the code,
**Then** it uses a global execution lock (MVP) ensuring only one opportunity is processed at a time,
**And** reservation check + execution happens atomically within the lock,
**And** the lock has a safety timeout of 30 seconds to prevent deadlock from unexpected hangs.

### AC6: Stale Reservation Cleanup on Startup
**Given** the engine restarts after a crash while a reservation was active,
**When** startup reconciliation runs (`onModuleInit`),
**Then** any stale reservations are released (budget returned to available pool),
**And** `reservedCapital` and `reservedPositionSlots` are reset to 0 in the `risk_states` table.

## Tasks / Subtasks

- [x] Task 1: Create `ExecutionLockService` in `src/modules/execution/` (AC: #5)
  - [x] 1.1 Create `execution-lock.service.ts` with promise-based global lock (acquire/release)
  - [x] 1.2 Create `execution-lock.service.spec.ts` with concurrency tests
  - [x] 1.3 Wire into `ExecutionModule` (create `execution.module.ts` replacing `.gitkeep`)
- [x] Task 2: Add budget reservation methods to `IRiskManager` and `RiskManagerService` (AC: #2, #3, #4)
  - [x] 2.1 Add `reserveBudget(opportunity: ReservationRequest): Promise<BudgetReservation>` to `IRiskManager` (typed input, not `unknown`)
  - [x] 2.2 Add `commitReservation(reservationId): Promise<void>` to `IRiskManager`
  - [x] 2.3 Add `releaseReservation(reservationId): Promise<void>` to `IRiskManager`
  - [x] 2.4 Implement reservation tracking in `RiskManagerService` (in-memory Map + state mutation)
  - [x] 2.5 Ensure `validatePosition()` accounts for active reservations in budget calculations
  - [x] 2.6 Add `BudgetReservation` type to `common/types/risk.type.ts`
  - [x] 2.7 Add reservation-related events (`risk.budget.reserved`, `risk.budget.committed`, `risk.budget.released`) AND add `BUDGET_RESERVED`, `BUDGET_COMMITTED`, `BUDGET_RELEASED` constants to `event-catalog.ts`
  - [x] 2.8 Write unit tests for all reservation paths (reserve, commit, release, reserve-after-reserve)
- [x] Task 3: Create `ExecutionQueueService` for sequential opportunity processing (AC: #1)
  - [x] 3.1 Create `execution-queue.service.ts` — accepts ranked opportunities, processes sequentially
  - [x] 3.2 Integrate lock acquisition → reservation → (placeholder) execution → commit/release flow
  - [x] 3.3 Write unit tests for queue ordering, sequential processing, failure handling
- [x] Task 4: Integrate into `TradingEngineService.executeCycle()` (AC: #1, #2, #3, #4, #5)
  - [x] 4.1 Define `IExecutionQueue` interface in `common/interfaces/` with `processOpportunities(opportunities: RankedOpportunity[]): Promise<ExecutionQueueResult[]>`
  - [x] 4.2 Add `EXECUTION_QUEUE_TOKEN` to `src/modules/execution/execution.constants.ts` (same DI token pattern as `RISK_MANAGER_TOKEN`)
  - [x] 4.3 Inject `IExecutionQueue` into `TradingEngineService` via token — replace the direct `for` loop over opportunities (Step 3/4 in executeCycle)
  - [x] 4.4 Pre-filter with `validatePosition()` (cheap pre-screen), then pass approved opportunities sorted by `netEdge` descending to `processOpportunities()`
  - [x] 4.5 Update e2e tests for new execution flow (mock `EXECUTION_QUEUE_TOKEN`)
- [x] Task 5: Persist reservation state for crash recovery (AC: #3, #4, #6)
  - [x] 5.1 Add `reservedCapital` and `reservedPositionSlots` columns to `risk_states` table (Prisma migration)
  - [x] 5.2 On startup (`onModuleInit`): clear in-memory reservations Map, reset `reservedCapital` and `reservedPositionSlots` to 0 in DB (crash recovery — AC6)
  - [x] 5.3 `persistState()` includes reservation totals

## Dev Notes

### Architecture Constraints

**Module placement:** The `ExecutionLockService` and `ExecutionQueueService` live in `src/modules/execution/`. This module currently contains only a `.gitkeep` file — you are creating the first real files here.

**Dependency rules (CRITICAL — do not violate):**
- `modules/execution/` may import from `modules/risk-management/` (budget reservation) and `connectors/` (future order submission)
- `modules/execution/` may import from `common/` (interfaces, errors, events, types)
- `modules/execution/` must NOT import from `modules/data-ingestion/`, `modules/arbitrage-detection/`, `modules/contract-matching/`, `modules/monitoring/`, or `modules/exit-management/`
- `core/` orchestrates `modules/execution/` via interface injection — never direct service import

**Hot path is synchronous DI injection:** `Detection → Risk validation → Execution`. Blocking is correct. Never execute without risk validation completing first.

**Fan-out is async EventEmitter2:** Monitoring subscribes to events. Telegram/dashboard timeouts must never delay execution cycles.

### Concurrency Model — Node.js Single-Threaded Event Loop

The global execution lock does NOT need OS-level mutexes. Node.js is single-threaded. The lock guards against **re-entrant async calls within the same event loop** — specifically preventing overlapping `executeCycle()` calls from the scheduler.

A simple promise-based lock pattern is sufficient for MVP:

```typescript
class ExecutionLockService {
  private lockPromise: Promise<void> | null = null;
  private releaseFn: (() => void) | null = null;

  private lockTimeout: NodeJS.Timeout | null = null;
  private readonly LOCK_TIMEOUT_MS = 30_000; // 30s safety timeout

  async acquire(): Promise<void> {
    while (this.lockPromise) {
      await this.lockPromise;
    }
    this.lockPromise = new Promise(resolve => {
      this.releaseFn = resolve;
    });
    // Safety timeout — auto-release if execution hangs
    this.lockTimeout = setTimeout(() => {
      this.logger.error({ message: 'Execution lock timeout — force releasing after 30s' });
      this.release();
    }, this.LOCK_TIMEOUT_MS);
  }

  release(): void {
    if (this.lockTimeout) {
      clearTimeout(this.lockTimeout);
      this.lockTimeout = null;
    }
    if (this.releaseFn) {
      const fn = this.releaseFn;
      this.releaseFn = null;
      this.lockPromise = null;
      fn();
    }
  }

  isLocked(): boolean {
    return this.lockPromise !== null;
  }
}
```

Phase 1 replaces this with optimistic concurrency (version counter on risk budget).

### Budget Reservation Design

**Three budget dimensions reserved atomically:**
1. **Position count** — increment `openPositionCount` reservation by 1
2. **Daily capital** — reserve `maxPositionSizeUsd` from `availableCapital`
3. **Correlation exposure** — placeholder for Epic 9; stored as `Decimal(0)` in `BudgetReservation`, NOT checked or enforced in `reserveBudget()` validation logic for MVP. Epic 9 will add real correlation calculations.

**Reservation lifecycle:**
```
reserve() → in-memory reservation created, tracked by reservationId
  → validatePosition() now sees reduced available budget
  → commit() → reservation becomes permanent state (openPositionCount++, totalCapitalDeployed += amount)
  → release() → reservation removed, budget returned to pool
```

**Reservation must be reflected in `validatePosition()`:** When a subsequent opportunity is validated, the budget calculation must include all active reservations. This means `getCurrentExposure()` and `validatePosition()` check both committed state AND active reservations.

### Existing Code to Modify

**`src/common/interfaces/risk-manager.interface.ts`** — Add 3 new methods:
```typescript
reserveBudget(request: ReservationRequest): Promise<BudgetReservation>;
commitReservation(reservationId: string): Promise<void>;
releaseReservation(reservationId: string): Promise<void>;
```

**`src/common/interfaces/execution-queue.interface.ts`** — New interface:
```typescript
export interface IExecutionQueue {
  processOpportunities(opportunities: RankedOpportunity[]): Promise<ExecutionQueueResult[]>;
}
```

**`src/modules/risk-management/risk-manager.service.ts`** — Implement reservation tracking:
- Add `private reservations: Map<string, BudgetReservation>` in-memory store
- `reserveBudget()` — validates budget (including active reservations), creates reservation, returns it
- `commitReservation()` — moves reservation to permanent state (mutates `openPositionCount`, `totalCapitalDeployed`)
- `releaseReservation()` — removes reservation, returns budget to pool
- Modify `validatePosition()` — account for reserved position slots and reserved capital
- Modify `getCurrentExposure()` — include reservation totals in exposure calculation
- Modify `persistState()` — include reservation totals

**`src/core/trading-engine.service.ts`** — Replace Step 4 placeholder:
- Inject `IExecutionQueue` (or `ExecutionQueueService`)
- After risk validation loop, pass approved opportunities (ranked by netEdge desc) to queue service
- Queue service handles lock → reserve → (placeholder execute) → commit/release

**`src/common/types/risk.type.ts`** — Add:
```typescript
interface ReservationRequest {
  opportunityId: string;
  recommendedPositionSizeUsd: Decimal;
  pairId: string;  // contract pair identifier
}

interface BudgetReservation {
  reservationId: string;
  opportunityId: string;
  reservedPositionSlots: number;  // always 1 for MVP
  reservedCapitalUsd: Decimal;
  correlationExposure: Decimal;   // placeholder for Epic 9 — always Decimal(0), NOT validated/enforced in MVP
  createdAt: Date;
}

interface RankedOpportunity {
  opportunity: unknown;  // full opportunity object from detection
  netEdge: Decimal;
  reservationRequest: ReservationRequest;
}

interface ExecutionQueueResult {
  opportunityId: string;
  reserved: boolean;
  executed: boolean;  // placeholder always true/false for MVP
  committed: boolean;
  error?: string;
}
```

**`src/common/errors/risk-limit-error.ts`** — Error code `3005` (`BUDGET_RESERVATION_FAILED`) is already reserved. Use it when reservation fails due to insufficient budget after accounting for active reservations.

**`src/common/events/`** — Add new events:
- `BudgetReservedEvent` → `risk.budget.reserved`
- `BudgetCommittedEvent` → `risk.budget.committed`
- `BudgetReleasedEvent` → `risk.budget.released`

### Prisma Schema Changes

Add two columns to `RiskState` model:
```prisma
reservedCapital       Decimal   @default(0) @map("reserved_capital") @db.Decimal(20, 8)
reservedPositionSlots Int       @default(0) @map("reserved_position_slots")
```

Migration name: `add_budget_reservation_columns`

### Files to Create

| File | Purpose |
|------|---------|
| `src/modules/execution/execution.module.ts` | NestJS module (replaces `.gitkeep`) |
| `src/modules/execution/execution.constants.ts` | `EXECUTION_QUEUE_TOKEN` DI token |
| `src/modules/execution/execution-lock.service.ts` | Global promise-based execution lock with 30s safety timeout |
| `src/modules/execution/execution-lock.service.spec.ts` | Lock concurrency + timeout tests |
| `src/modules/execution/execution-queue.service.ts` | Sequential opportunity processing with lock + reservation |
| `src/modules/execution/execution-queue.service.spec.ts` | Queue ordering and failure handling tests |
| `src/common/interfaces/execution-queue.interface.ts` | `IExecutionQueue` interface |

### Files to Modify

| File | Change |
|------|--------|
| `src/common/interfaces/risk-manager.interface.ts` | Add `reserveBudget`, `commitReservation`, `releaseReservation` |
| `src/common/interfaces/index.ts` | Add re-export of `IExecutionQueue` |
| `src/common/types/risk.type.ts` | Add `BudgetReservation` type |
| `src/common/events/risk.events.ts` | Add `BudgetReservedEvent`, `BudgetCommittedEvent`, `BudgetReleasedEvent` |
| `src/common/events/event-catalog.ts` | Add `BUDGET_RESERVED`, `BUDGET_COMMITTED`, `BUDGET_RELEASED` event names |
| `src/modules/risk-management/risk-manager.service.ts` | Implement reservation methods, modify `validatePosition()` and `getCurrentExposure()` |
| `src/modules/risk-management/risk-manager.service.spec.ts` | Add reservation tests |
| `src/modules/risk-management/risk-management.module.ts` | Import `ExecutionModule` if needed for DI |
| `src/core/trading-engine.service.ts` | Integrate `ExecutionQueueService`, replace Step 4 placeholder |
| `src/core/core.module.ts` | Import `ExecutionModule` |
| `prisma/schema.prisma` | Add `reservedCapital`, `reservedPositionSlots` columns |
| `test/app.e2e-spec.ts` | May need updates for new module |

### Testing Strategy

**Framework:** Vitest + `@nestjs/testing` Test.createTestingModule() — same as Stories 4.1-4.3.

**Co-located tests:** Each `.service.ts` gets a `.service.spec.ts` in the same directory.

**Key test scenarios:**

1. **ExecutionLockService:**
   - Acquire succeeds when unlocked
   - Second acquire waits until first releases
   - Release when not locked is a no-op
   - isLocked() reflects current state
   - Multiple sequential acquire/release cycles work correctly
   - Lock auto-releases after 30s timeout (use fake timers)
   - Timeout is cleared on normal release

2. **Budget Reservation (RiskManagerService):**
   - `reserveBudget()` succeeds when budget available
   - `reserveBudget()` fails (3005) when no budget left after existing reservations
   - `reserveBudget()` fails when trading halted
   - `reserveBudget()` fails when max open pairs reached (including reserved slots)
   - Active reservation reduces available budget for next `validatePosition()` call
   - `commitReservation()` converts reservation to permanent state
   - `commitReservation()` with invalid ID throws error
   - `releaseReservation()` returns budget to pool
   - `releaseReservation()` with invalid ID throws error
   - Multiple concurrent reservations tracked correctly
   - `getCurrentExposure()` includes reservation totals
   - Events emitted on reserve/commit/release
   - `onModuleInit` clears stale reservations and resets DB reservation columns (AC6)

3. **ExecutionQueueService:**
   - Opportunities processed in netEdge descending order
   - Lock acquired before each opportunity
   - Budget reserved after lock acquisition
   - Reservation committed on success (placeholder — returns true for now)
   - Reservation released on failure
   - Failed opportunity doesn't block subsequent ones
   - Empty queue returns immediately
   - Single opportunity processed correctly

**Mocking:** Mock `PrismaService` (same as 4.3), mock `EventEmitter2`, mock `ExecutionLockService` in queue tests, mock `IRiskManager` in queue tests.

**Target:** ~30-40 new tests. Running total should reach ~480-490 from current 447 baseline.

### Previous Story Intelligence (from 4.3)

**Patterns to follow:**
- DI token pattern: Use `RISK_MANAGER_TOKEN` from `risk-management.constants.ts` when injecting `IRiskManager`
- `ConfigService.get()` returns strings — use `Number()` conversion
- `PrismaService` import path: `../../common/prisma.service` (not `../../persistence/`)
- `ValidationPipe` applied locally, NOT globally
- Use `HttpException` throws (not `@Res`) for status codes
- `eslint-disable` pragmas need comments explaining why

**Error code allocation:** `BUDGET_RESERVATION_FAILED: 3005` already reserved in `risk-limit-error.ts` (bumped from 3004 during Story 4.3). Use it.

**Test baseline:** 447 tests passing after Story 4.3.

### Code Review Learnings from 4.3

- Remove dead code (Story 4.3 had dead halt check in `determineRejectionReason`)
- Include all relevant fields in return objects (4.3 missed `dailyPnl` in approved override)
- Add proper mocks to e2e tests when new Prisma models are introduced
- Avoid double invocations in controller tests

### What This Story Does NOT Include (Explicit Scope Boundaries)

- **No actual order submission** — execution is a placeholder (returns success/fail). Real execution is Epic 5, Story 5.1.
- **No `IExecutionEngine` interface** — that's Story 5.1.
- **No `open_positions` or `orders` tables** — Story 5.1.
- **No correlation cluster enforcement** — Epic 9. Track `correlationExposure` as a placeholder `Decimal(0)` in `BudgetReservation`.
- **No optimistic concurrency** — Phase 1. MVP uses global lock with 30s safety timeout.
- **No Telegram/dashboard integration** — Events are emitted; monitoring module (Epic 6) subscribes.
- **No REST endpoints** — this is internal infrastructure only.

### Integration Points with Future Stories

- **Story 5.1** will inject `ExecutionLockService` and call `acquire()/release()` around actual order submission. The queue service's placeholder execution callback will be replaced with real `IExecutionEngine.execute()`.
- **Story 5.5** (Startup Reconciliation) will call `releaseReservation()` for any stale reservations found on startup.
- **Epic 9** will add real correlation exposure calculations to `reserveBudget()`.
- **Story 6.4** (Compliance Validation) runs inside the lock window, after lock acquire but before order submission.

### Project Structure Notes

- `src/modules/execution/` directory exists with `.gitkeep` — replace with real module files
- All new files follow kebab-case naming convention
- Module registered in `core.module.ts` imports array
- No changes to `app.module.ts` needed (core module handles orchestration imports)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4, Story 4.4]
- [Source: _bmad-output/planning-artifacts/architecture.md#Execution Module, Sequential Execution Locking, Hot Path]
- [Source: _bmad-output/implementation-artifacts/4-3-operator-risk-override.md#Dev Notes, Code Patterns]
- [Source: CLAUDE.md#Architecture, Module Dependency Rules, Error Handling, Event Emission]
- [Source: prisma/schema.prisma#RiskState model]
- [Source: src/core/trading-engine.service.ts#executeCycle Step 4 placeholder]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None

### Completion Notes List

- Implemented `ExecutionLockService` with promise-based global lock, 30s safety timeout, 9 tests
- Added `BudgetReservation`, `ReservationRequest`, `RankedOpportunity`, `ExecutionQueueResult` types to `risk.type.ts`
- Extended `IRiskManager` interface with `reserveBudget()`, `commitReservation()`, `releaseReservation()`
- Implemented reservation tracking in `RiskManagerService` with in-memory Map, atomic validation+reservation in `reserveBudget()`, commit/release lifecycle, 16 new tests
- Modified `validatePosition()` and `getCurrentExposure()` to account for active reservations
- Added `BudgetReservedEvent`, `BudgetCommittedEvent`, `BudgetReleasedEvent` event classes and `BUDGET_RESERVED`, `BUDGET_COMMITTED`, `BUDGET_RELEASED` event catalog constants
- Created `ExecutionQueueService` processing ranked opportunities sequentially with lock → reserve → execute → commit/release, 9 tests
- Created `IExecutionQueue` interface and `EXECUTION_QUEUE_TOKEN` DI constant
- Integrated queue into `TradingEngineService.executeCycle()` — pre-filter with `validatePosition()`, sort by netEdge desc, pass to queue
- Created `ExecutionModule` with DI wiring, imported into `CoreModule`
- Added `reservedCapital` and `reservedPositionSlots` columns to `risk_states` (Prisma migration)
- Startup crash recovery clears stale reservations via `onModuleInit`
- `persistState()` includes reservation totals
- All 481 tests pass (34 new), lint clean
- Test baseline: 447 → 481

### Code Review Fixes (Claude Opus 4.6)
- **H1 Fixed:** `reserveBudget()` now uses `min(request.recommendedPositionSizeUsd, maxPositionSizeUsd)` instead of always using config max — avoids over-reserving when detection recommends smaller positions
- **M1 Fixed:** Removed dead `else` branch in `ExecutionQueueService.processOneOpportunity()` — placeholder execution always succeeds, added TODO for Story 5.1
- **M2 Verified:** `eslint-disable @typescript-eslint/no-misused-promises` was actually needed (async mock callbacks) — kept with updated comment
- **M3 Fixed:** `validatePosition()` now checks available capital (including reserved capital) as a pre-screen — prevents unnecessary lock acquire cycles
- **L1 Fixed:** `determineRejectionReason()` now includes reserved slots in open pairs check — consistent with `validatePosition()` and `reserveBudget()`
- **L2 Fixed:** Removed unused `EventEmitter2` injection from `ExecutionQueueService`
- 3 new tests added: recommended < max reservation, recommended > max cap, validatePosition capital rejection
- Test count: 481 → 484, lint clean

### File List

**New files:**
- `src/modules/execution/execution-lock.service.ts`
- `src/modules/execution/execution-lock.service.spec.ts`
- `src/modules/execution/execution-queue.service.ts`
- `src/modules/execution/execution-queue.service.spec.ts`
- `src/modules/execution/execution.module.ts`
- `src/modules/execution/execution.constants.ts`
- `src/common/interfaces/execution-queue.interface.ts`
- `prisma/migrations/20260217151402_add_budget_reservation_columns/migration.sql`

**Modified files:**
- `src/common/interfaces/risk-manager.interface.ts`
- `src/common/interfaces/index.ts`
- `src/common/types/risk.type.ts`
- `src/common/events/risk.events.ts`
- `src/common/events/event-catalog.ts`
- `src/modules/risk-management/risk-manager.service.ts`
- `src/modules/risk-management/risk-manager.service.spec.ts`
- `src/core/trading-engine.service.ts`
- `src/core/trading-engine.service.spec.ts`
- `src/core/core.module.ts`
- `prisma/schema.prisma`

**Deleted files:**
- `src/modules/execution/.gitkeep`
