# Story 5.5.2: Paper Position State Isolation & Tracking

Status: done

## Story

As an operator,
I want paper trading positions tracked separately from live positions,
So that paper results never contaminate live P&L or risk calculations.

## Acceptance Criteria

1. **Given** the Prisma schema
   **When** migration runs
   **Then** `open_positions` and `orders` tables have an `is_paper` Boolean column (default: false)
   **And** a composite index exists on `(is_paper, status)` for both tables

2. **Given** paper mode is active for a platform
   **When** a paper order fills
   **Then** the resulting order is persisted with `isPaper = true`
   **And** the resulting position is persisted with `isPaper = true`

3. **Given** risk budget queries (position limits, exposure calculations)
   **When** querying positions
   **Then** repository methods filter by `isPaper = false` by default (live-only)
   **And** paper positions have an isolated risk budget that does not affect live limits

4. **Given** paper positions exist
   **When** the exit monitor evaluates positions
   **Then** only live positions are evaluated for exit (paper positions excluded from live exit loop)

5. **Given** paper positions exist
   **When** startup reconciliation runs
   **Then** risk budget recalculation uses only live positions
   **And** paper positions are excluded from live risk state

## Out of Scope

- **Mixed mode validation & tagging** — Story 5.5.3
- **Dashboard visual distinction** (amber border, `[PAPER]` tag) — Epic 7 (dashboard not yet implemented)
- **Paper P&L toggle in dashboard** — Epic 7
- **Persistent paper trade history export** — future enhancement
- **Separate paper risk budget tracking/display** — future (paper positions skip risk entirely in MVP)

## Tasks / Subtasks

- [x] Task 1: Add `isPaper` column to Prisma schema (AC: 1)
  - [x] 1.1 Add `isPaper` field to `Order` model in `prisma/schema.prisma`:
    ```prisma
    isPaper    Boolean     @default(false) @map("is_paper")
    ```
    Place after `fillSize` field (line 137), before `createdAt`.
  - [x] 1.2 Add `isPaper` field to `OpenPosition` model:
    ```prisma
    isPaper           Boolean        @default(false) @map("is_paper")
    ```
    Place after `reconciliationContext` field (line 167), before the relation fields.
  - [x] 1.3 Add composite indexes for both models:

    ```prisma
    // In Order model, add after existing @@index([createdAt]):
    @@index([isPaper, status])

    // In OpenPosition model, add after existing @@index([createdAt]):
    @@index([isPaper, status])
    ```

  - [x] 1.4 Run `pnpm prisma migrate dev --name add-is-paper-columns` to generate and apply migration
  - [x] 1.5 Run `pnpm prisma generate` to regenerate client types
  - [x] 1.6 Verify migration SQL contains: `ALTER TABLE "orders" ADD COLUMN "is_paper" BOOLEAN NOT NULL DEFAULT false` and same for `open_positions`. Existing rows get `false` (correct — they are all live).

- [x] Task 2: Update `ExecutionService` to propagate `isPaper` flag (AC: 2)
  - [x] 2.1 Determine paper mode at execution time. The `ExecutionService` already has both connectors injected via tokens (`KALSHI_CONNECTOR_TOKEN`, `POLYMARKET_CONNECTOR_TOKEN`). Check the connector's health to determine paper mode:
    ```typescript
    // At the start of execute(), after resolving connectors:
    const primaryHealth = primaryConnector.getHealth();
    const secondaryHealth = secondaryConnector.getHealth();
    const isPaper = primaryHealth.mode === 'paper' || secondaryHealth.mode === 'paper';
    ```
    **Rationale:** If either leg is paper, the entire position is paper. Mixed-mode tagging (`mixedMode: true`) is Story 5.5.3 scope — for now, any paper involvement means `isPaper = true`.
  - [x] 2.2 Pass `isPaper` to `orderRepository.create()` calls. There are 4 call sites in `execution.service.ts`:
    - **Primary order creation** (~line 195 in `execute()`): Add `isPaper` to the create input
    - **Secondary order creation (success path)** (~line 310 in `execute()`): Add `isPaper`
    - **Secondary order creation (pending path)** (~line 263 in `execute()`): Add `isPaper`
    - All in `execute()` method. The `handleSingleLeg()` method does NOT create orders (it only creates positions using the already-persisted primary order).
  - [x] 2.3 Pass `isPaper` to `positionRepository.create()` calls. There are 2 call sites:
    - **Two-leg position** (~line 332 in `execute()`): Add `isPaper` to the create input
    - **Single-leg position** (~line 463 in `handleSingleLeg()`): Add `isPaper`. **IMPORTANT:** `handleSingleLeg` does not have access to connector health directly. Pass `isPaper` as a parameter from `execute()`.
  - [x] 2.4 Update `handleSingleLeg()` method signature to accept `isPaper: boolean` parameter. It currently has 15 parameters — add `isPaper` as the 16th:
    ```typescript
    private async handleSingleLeg(
      pairId: string,
      primaryLeg: string,
      // ... existing 13 params ...
      errorMessage: string,
      isPaper: boolean,  // NEW — 16th param
    ): Promise<ExecutionResult>
    ```
    Update both call sites in `execute()` to pass `isPaper`.
  - [x] 2.5 Unit tests in `execution.service.spec.ts`:
    - Test: when both connectors are live (no `mode` field in health), orders/positions created with `isPaper: false` (verify via repository mock `.toHaveBeenCalledWith()`)
    - Test: when primary connector health has `mode: 'paper'`, orders/positions created with `isPaper: true`
    - Test: when secondary connector health has `mode: 'paper'`, orders/positions created with `isPaper: true`
    - Test: `handleSingleLeg` receives and passes `isPaper` to position creation

- [x] Task 3: Update `PositionRepository` with `isPaper` filtering (AC: 3, 4, 5)
  - [x] 3.1 Update `findByStatusWithOrders()` — add optional `isPaper` parameter (defaults to `false`):
    ```typescript
    async findByStatusWithOrders(
      status: Prisma.OpenPositionWhereInput['status'],
      isPaper: boolean = false,
    ) {
      return this.prisma.openPosition.findMany({
        where: { status, isPaper },
        include: { pair: true, kalshiOrder: true, polymarketOrder: true },
      });
    }
    ```
    **This is called by ExitMonitorService** (line 62) — default `false` means exit monitor evaluates live positions only without any caller changes.
  - [x] 3.2 Update `findActivePositions()` — add optional `isPaper` parameter (defaults to `false`):
    ```typescript
    async findActivePositions(isPaper: boolean = false) {
      return this.prisma.openPosition.findMany({
        where: {
          isPaper,
          status: {
            in: ['OPEN', 'SINGLE_LEG_EXPOSED', 'EXIT_PARTIAL', 'RECONCILIATION_REQUIRED'],
          },
        },
        include: { pair: true, kalshiOrder: true, polymarketOrder: true },
      });
    }
    ```
    **This is called by StartupReconciliationService** (lines 309, 697) — default `false` means reconciliation processes live positions only without caller changes.
  - [x] 3.3 Update `findByStatus()` — add optional `isPaper` parameter (defaults to `false`):
    ```typescript
    async findByStatus(
      status: Prisma.OpenPositionWhereInput['status'],
      isPaper: boolean = false,
    ) {
      return this.prisma.openPosition.findMany({
        where: { status, isPaper },
      });
    }
    ```
    **Called by reconciliation** (line 268 for `SINGLE_LEG_EXPOSED`, line 485 for `RECONCILIATION_REQUIRED`).
  - [x] 3.4 Update `findByStatusWithPair()` — add optional `isPaper` parameter (defaults to `false`):
    ```typescript
    async findByStatusWithPair(
      status: Prisma.OpenPositionWhereInput['status'],
      isPaper: boolean = false,
    ) {
      return this.prisma.openPosition.findMany({
        where: { status, isPaper },
        include: { pair: true },
      });
    }
    ```
  - [x] 3.5 **DO NOT** modify `findById()`, `findByIdWithPair()`, `findByPairId()`, `updateStatus()`, `updateWithOrder()`, `create()` — these are lookup-by-ID or write operations that don't need paper filtering. ID lookups will return the correct record regardless of `isPaper`.
  - [x] 3.6 Unit tests in a new `position.repository.spec.ts` (co-located at `src/persistence/repositories/position.repository.spec.ts`):
    - Test: `findByStatusWithOrders('OPEN')` default filters to `isPaper: false`
    - Test: `findByStatusWithOrders('OPEN', true)` filters to `isPaper: true`
    - Test: `findActivePositions()` default filters to `isPaper: false`
    - Test: `findActivePositions(true)` filters to `isPaper: true`
    - Test: `findByStatus('OPEN')` default filters to `isPaper: false`
    - Test: `findByStatusWithPair('OPEN')` default filters to `isPaper: false`
    - Mock `PrismaService` with `vi.fn()` — verify the `where` clause passed to Prisma contains `isPaper`.

- [x] Task 4: Update `OrderRepository` with `isPaper` filtering (AC: 3)
  - [x] 4.1 Update `findPendingOrders()` — add optional `isPaper` parameter (defaults to `false`):
    ```typescript
    async findPendingOrders(isPaper: boolean = false) {
      return this.prisma.order.findMany({
        where: { status: 'PENDING', isPaper },
      });
    }
    ```
    **Called by reconciliation** (line 207) — default `false` means only live pending orders are reconciled.
  - [x] 4.2 **DO NOT** modify `findById()`, `findByPairId()`, `updateStatus()`, `updateOrderStatus()`, `create()` — these are ID-based lookups or write operations.
  - [x] 4.3 Unit tests in a new `order.repository.spec.ts` (co-located at `src/persistence/repositories/order.repository.spec.ts`):
    - Test: `findPendingOrders()` default filters to `isPaper: false`
    - Test: `findPendingOrders(true)` filters to `isPaper: true`
    - Mock `PrismaService` — verify `where` clause contains `isPaper`.

- [x] Task 5: Update mock factories (AC: all)
  - [x] 5.1 In `src/test/mock-factories.ts`, verify that `createMockPlatformConnector()` already returns a `getHealth` mock. Update the default to NOT include `mode` (i.e., live mode — `mode` is `undefined`). This should already be the case from Story 5.5.1.
  - [x] 5.2 Add a convenience helper or document the pattern for creating a paper-mode mock in tests:
    ```typescript
    // In tests that need paper mode:
    const kalshiConnector = createMockPlatformConnector(PlatformId.KALSHI);
    kalshiConnector.getHealth.mockReturnValue({
      platformId: PlatformId.KALSHI,
      status: 'healthy',
      lastHeartbeat: new Date(),
      latencyMs: 50,
      mode: 'paper',
    });
    ```
    No factory change needed — tests override `getHealth` per-test.

- [x] Task 6: Run lint + test suite (AC: all)
  - [x] 6.1 Run `pnpm lint` — fix any issues
  - [x] 6.2 Run `pnpm test` — all tests pass (existing + new)
  - [x] 6.3 Verify test count increased (new repository tests + execution isPaper tests)

## Dev Notes

### Design Decision: Default `false` on Repository Query Methods

All query methods that return collections default to `isPaper = false`. This provides **zero-change backward compatibility**:

- `ExitMonitorService` calls `findByStatusWithOrders('OPEN')` — continues to get live positions only
- `StartupReconciliationService` calls `findActivePositions()` — continues to get live positions only
- `StartupReconciliationService` calls `findPendingOrders()` — continues to get live pending orders only

No caller code changes required for isolation. This is the safest approach because:

1. Existing callers (exit monitor, reconciliation) were written for live-only — they get live-only by default
2. Paper position queries are an opt-in concern for future stories (5.5.3, Epic 7 dashboard)
3. If a future caller forgets to pass `isPaper`, it defaults to live — fail-safe

### Design Decision: `isPaper` Source — Connector Health, Not Process Env

The `isPaper` flag is derived from `connector.getHealth().mode === 'paper'` at execution time, NOT from `process.env.PLATFORM_MODE_*`. Reasons:

1. `ExecutionService` already has the connector injected — no new dependency needed
2. The connector's health is the canonical source of truth for mode (set by `ConnectorModule` factory in Story 5.5.1)
3. Avoids coupling `ExecutionService` to `ConfigService` for paper mode detection
4. If either connector is paper, the whole position is paper (no "half paper" positions in MVP)

### Design Decision: Paper Positions Skip Live Risk Budget

In this MVP, paper positions are created with `isPaper = true` but do NOT reserve or commit live risk budget. The existing `reserveBudget()`/`commitReservation()`/`closePosition()` calls in the execution pipeline still fire — but because:

- The `RiskManager` uses in-memory counters
- `recalculateRiskBudget()` (called at startup) filters by `isPaper = false`
- Exit monitor evaluates only live positions

Paper trades "appear" to consume budget during a session but get cleaned out at restart. This is acceptable for MVP. A future story can add a separate paper risk budget.

**IMPORTANT:** Do NOT add any `isPaper` check to `RiskManager` itself. The risk manager is unaware of paper mode. Isolation is enforced at the repository and execution layers.

### Prisma Schema Change Details

```prisma
model Order {
  // ... existing fields ...
  fillSize   Decimal?    @map("fill_size") @db.Decimal(20, 8)
  isPaper    Boolean     @default(false) @map("is_paper")      // NEW
  createdAt  DateTime    @default(now()) @map("created_at") @db.Timestamptz
  // ... rest unchanged ...

  @@index([pairId])
  @@index([platform, status])
  @@index([createdAt])
  @@index([isPaper, status])   // NEW — accelerates "find live OPEN orders"
  @@map("orders")
}

model OpenPosition {
  // ... existing fields ...
  reconciliationContext Json? @map("reconciliation_context")
  isPaper           Boolean        @default(false) @map("is_paper")  // NEW

  // ... relations unchanged ...

  @@index([pairId])
  @@index([status])
  @@index([createdAt])
  @@index([isPaper, status])   // NEW — accelerates "find live OPEN positions"
  @@map("open_positions")
}
```

The `@default(false)` means:

- All existing rows automatically get `is_paper = false` — correct, they're all live
- New rows default to `false` unless explicitly set — fail-safe for any code path that doesn't set it

### Execution Service Integration Points

**4 order creation call sites in `execute()`:**

1. Primary order persist (~line 195):

```typescript
const primaryOrderRecord = await this.orderRepository.create({
  platform: ...,
  contractId: ...,
  pair: { connect: { matchId: pairId } },
  side: primarySide,
  price: targetPrice.toNumber(),
  size: targetSize,
  status: ...,
  fillPrice: primaryOrder.filledPrice,
  fillSize: primaryOrder.filledQuantity,
  isPaper,  // ADD THIS
});
```

2. Secondary order persist — success path (~line 310): same pattern, add `isPaper`
3. Secondary order persist — pending path (~line 263): same pattern, add `isPaper`

**2 position creation call sites:**

1. Two-leg position in `execute()` (~line 332): add `isPaper` to create input
2. Single-leg position in `handleSingleLeg()` (~line 463): add `isPaper` — must receive it as parameter from `execute()`

### `handleSingleLeg` Parameter Threading

`handleSingleLeg` is a private method with 15 parameters. Adding `isPaper` as 16th parameter is consistent with the existing pattern (the method already threads many values from `execute()`). There are exactly **2 call sites** for `handleSingleLeg` in `execute()`:

1. After secondary depth verification fails (~line 220)
2. After secondary order submission fails or returns non-filled (~line 251 and ~line 283)

Both must pass `isPaper`.

### Repository Method Signatures — Before vs After

**PositionRepository:**
| Method | Before | After |
|--------|--------|-------|
| `findByStatus(status)` | Filters by status only | `findByStatus(status, isPaper = false)` |
| `findByStatusWithPair(status)` | Filters by status only | `findByStatusWithPair(status, isPaper = false)` |
| `findByStatusWithOrders(status)` | Filters by status only | `findByStatusWithOrders(status, isPaper = false)` |
| `findActivePositions()` | All active statuses | `findActivePositions(isPaper = false)` |

**OrderRepository:**
| Method | Before | After |
|--------|--------|-------|
| `findPendingOrders()` | All pending | `findPendingOrders(isPaper = false)` |

### Test Strategy

**Repository tests** mock `PrismaService` and verify the `where` clause:

```typescript
describe('PositionRepository', () => {
  it('findByStatusWithOrders defaults to isPaper false', async () => {
    await repo.findByStatusWithOrders('OPEN');
    expect(prisma.openPosition.findMany).toHaveBeenCalledWith({
      where: { status: 'OPEN', isPaper: false },
      include: { pair: true, kalshiOrder: true, polymarketOrder: true },
    });
  });
});
```

**Execution tests** mock connectors with `getHealth` returning `mode: 'paper'` or no mode, then verify `orderRepository.create` and `positionRepository.create` called with correct `isPaper`:

```typescript
it('should set isPaper true when primary connector is paper', async () => {
  kalshiConnector.getHealth.mockReturnValue({ ...healthDefaults, mode: 'paper' });
  await service.execute(opportunity, reservation);
  expect(orderRepository.create).toHaveBeenCalledWith(expect.objectContaining({ isPaper: true }));
  expect(positionRepository.create).toHaveBeenCalledWith(expect.objectContaining({ isPaper: true }));
});
```

### Known Limitation: handleSingleLeg Parameter Count

`handleSingleLeg` already has 15 parameters. Adding `isPaper` as the 16th is a code smell. The correct fix is refactoring to a context object:

```typescript
interface SingleLegContext {
  pairId: string;
  primaryLeg: string;
  primaryOrderId: string;
  // ... all 15 existing params + isPaper
}
```

However, this refactor is **out of scope** for this story — it would change all call sites and tests for a pre-existing debt. Track as tech debt for a future cleanup story. For now, the 16th parameter is consistent with the existing pattern.

### Known Limitation: Risk Budget Contamination During Session

Paper trades fire `reserveBudget()`/`commitReservation()` during a session, consuming live budget counters in the `RiskManager` in-memory state. This means:

- **Single-mode operation assumed:** Run either all-paper or all-live within a session
- **If paper trades hit daily loss limit:** Live trading would halt until restart
- **Cleaned at restart:** `recalculateRiskBudget()` queries `findActivePositions(isPaper = false)`, restoring correct live-only counters

This is acceptable for MVP. A future story can add a separate paper risk budget or make `RiskManager` mode-aware. Do NOT attempt to fix this in the current story — `IRiskManager` is frozen.

### Known Limitation: Paper Position Lifecycle

Paper positions in the DB are "write and forget" in MVP:

- **Exit monitor ignores them** (default `isPaper = false` filter)
- **Reconciliation ignores them** (same default filter)
- **No automatic cleanup** — paper positions accumulate as historical records
- **In-memory order map (FillSimulatorService) is lost on restart** — paper orders exist in DB but simulator state is gone

This is acceptable. Paper positions serve as a historical audit trail of simulated trades. Future stories can add paper position cleanup, paper exit monitoring, or paper P&L reporting.

### DoD Gates (from Epic 4.5 Retro, carried forward)

1. **Test isolation:** No shared mutable state — repository tests use fresh mocks per test
2. **Interface preservation:** No interface changes. `isPaper` is a Prisma schema field, not an interface method. Repository method signatures add an optional parameter with default — backward-compatible.
3. **Normalization ownership:** Connectors not touched in this story

### Interface Freeze Compliance

`IPlatformConnector` (11 methods) and `IRiskManager` (13 methods) — **UNCHANGED**. This story only modifies:

- Prisma schema (data model)
- Repository methods (optional parameter additions)
- `ExecutionService` (pass-through of `isPaper` flag)

No new interface methods. No new connector methods. No new risk manager methods.

### Previous Story Intelligence (5.5.1)

Key learnings from Story 5.5.1:

- `PaperTradingConnector.getHealth()` returns `{ ...realHealth, mode: 'paper' }` — this is the detection mechanism for paper mode
- Paper orders are stored in-memory in `FillSimulatorService` — but the `OrderResult` returned to `ExecutionService` is identical to a live result
- `PlatformHealth.mode` is optional — `undefined` means live. Check with `=== 'paper'`, not `!== 'live'`
- Mock factories default `getHealth` to NOT include `mode` field — correct for live mode testing
- `.env.development` already has `PLATFORM_MODE_KALSHI=paper` and `PLATFORM_MODE_POLYMARKET=paper`

### Migration Rollback

The migration is safe to rollback:

- `ALTER TABLE "orders" DROP COLUMN "is_paper"` — removes column and index
- `ALTER TABLE "open_positions" DROP COLUMN "is_paper"` — removes column and index
- No data loss — the column has a default value and no dependent constraints

### Project Structure Notes

**New files:**

- `prisma/migrations/<timestamp>_add_is_paper_columns/migration.sql` — auto-generated
- `src/persistence/repositories/position.repository.spec.ts` — repository unit tests
- `src/persistence/repositories/order.repository.spec.ts` — repository unit tests

**Modified files:**

- `prisma/schema.prisma` — add `isPaper` field + composite indexes to `Order` and `OpenPosition`
- `src/persistence/repositories/position.repository.ts` — add `isPaper` parameter to 4 query methods
- `src/persistence/repositories/order.repository.ts` — add `isPaper` parameter to `findPendingOrders`
- `src/modules/execution/execution.service.ts` — detect paper mode from connector health, pass `isPaper` to order/position creation, update `handleSingleLeg` signature
- `src/modules/execution/execution.service.spec.ts` — add paper mode tests

**NOT modified (by design):**

- `src/modules/risk-management/risk-manager.service.ts` — unaware of paper mode
- `src/modules/exit-management/exit-monitor.service.ts` — gets live-only positions via default `isPaper = false`
- `src/reconciliation/startup-reconciliation.service.ts` — gets live-only data via defaults
- `src/connectors/paper/*` — no changes needed
- `src/common/interfaces/*` — interface freeze in effect
- `src/test/mock-factories.ts` — no changes needed (existing defaults work)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5.5, Story 5.5.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Environment Configuration — Paper Trading Configuration]
- [Source: _bmad-output/implementation-artifacts/5-5-1-paper-trading-connector-mode-configuration.md — PaperTradingConnector, FillSimulatorService, PlatformHealth.mode]
- [Source: _bmad-output/implementation-artifacts/5-5-0-interface-stabilization-test-infrastructure.md — Interface Freeze, Mock Factories]
- [Source: pm-arbitrage-engine/prisma/schema.prisma — Order (lines 127-150), OpenPosition (lines 153-177)]
- [Source: pm-arbitrage-engine/src/persistence/repositories/position.repository.ts — 10 methods, findActivePositions, findByStatusWithOrders]
- [Source: pm-arbitrage-engine/src/persistence/repositories/order.repository.ts — 6 methods, findPendingOrders]
- [Source: pm-arbitrage-engine/src/modules/execution/execution.service.ts — execute() order/position creation, handleSingleLeg()]
- [Source: pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts — evaluatePositions() line 62]
- [Source: pm-arbitrage-engine/src/reconciliation/startup-reconciliation.service.ts — recalculateRiskBudget() lines 695-724]
- [Source: pm-arbitrage-engine/src/common/types/platform.type.ts — PlatformHealth.mode]
- [Source: CLAUDE.md#Architecture, #Error Handling, #Naming Conventions, #Testing, #Domain Rules]

### LAD Design Review — Applied Fixes

Review performed by LAD MCP (kimi-k2-thinking + glm-4.7). Key findings analyzed:

1. **Paper mode detection flaw (Primary, Critical):** DISMISSED — reviewer misread `PaperTradingConnector.getHealth()`. It returns `{ ...realHealth, mode: 'paper' }` (augments, doesn't delegate). Tested in `paper-trading.connector.spec.ts`.
2. **handleSingleLeg 16th parameter (Both, Medium):** ACKNOWLEDGED — added "Known Limitation" section documenting the tech debt. Refactoring to context object is out of scope for this story.
3. **Risk state contamination mid-session (Both, Medium):** ACKNOWLEDGED — added "Known Limitation" section. Single-mode operation assumed for MVP. Cleaned at restart.
4. **Missing repository queries (Primary, High):** DISMISSED — `findByIdWithPair()`, `findByPairId()` are ID-based lookups returning specific records. No `isPaper` filter needed. Only collection queries need filtering.
5. **Event payload missing isPaper (Primary, Medium):** DEFERRED to Story 5.5.3 (mixed mode tagging). No event consumers exist (monitoring module is Epic 6).
6. **Paper position zombies (Secondary, Low):** ACKNOWLEDGED — added "Known Limitation" section. Paper positions are historical audit records in MVP.
7. **Migration backfill (Primary, Low):** DISMISSED — Story 5.5.1 stores paper orders in-memory only. No paper data exists in DB. `@default(false)` is correct.
8. **PlatformHealth type question (Secondary):** CONFIRMED — Story 5.5.1 already added `mode?: 'paper' | 'live'` to PlatformHealth. Real connectors return `undefined` = live.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None — clean implementation, no debugging required.

### Completion Notes List

- All 6 tasks completed with TDD (tests first, then implementation, then verify)
- Baseline: 793 tests → Final: 808 tests (+15 new tests)
- 57 test files, all passing, lint clean
- Migration `20260222231041_add_is_paper_columns` applied successfully
- No interface changes — interface freeze compliance confirmed
- Mock factories required no changes (default `getHealth` omits `mode` = live)
- No changes to risk-manager, exit-monitor, reconciliation, or connectors (isolation via repository defaults)

### File List

**New:**

- `prisma/migrations/20260222231041_add_is_paper_columns/migration.sql`

**Modified:**

- `prisma/schema.prisma` — `isPaper` field + `@@index([isPaper, status])` on `Order` and `OpenPosition`
- `src/persistence/repositories/position.repository.ts` — optional `isPaper` param (default `false`) on `findByStatus`, `findByStatusWithPair`, `findByStatusWithOrders`, `findActivePositions`
- `src/persistence/repositories/order.repository.ts` — optional `isPaper` param (default `false`) on `findPendingOrders`
- `src/modules/execution/execution.service.ts` — paper mode detection from connector health, `isPaper` propagated to 4 order creations + 2 position creations, `handleSingleLeg` signature updated (16th param)
- `src/persistence/repositories/position.repository.spec.ts` — 8 new isPaper filtering tests (12 total)
- `src/persistence/repositories/order.repository.spec.ts` — 2 new isPaper filtering tests (6 total)
- `src/modules/execution/execution.service.spec.ts` — 5 new isPaper propagation tests (19 total)
- `src/reconciliation/reconciliation.controller.ts` — clarifying comment on live-only paper filtering
