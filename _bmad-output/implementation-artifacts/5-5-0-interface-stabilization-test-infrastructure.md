# Story 5.5.0: Interface Stabilization & Test Infrastructure

Status: done

## Story

As a developer,
I want cancelOrder() implemented, mocks centralized, and documentation updated,
So that the interface is frozen and stable before building the decorator pattern on top.

## Acceptance Criteria

1. **Given** `cancelOrder()` is defined in `IPlatformConnector` but not implemented
   **When** Story 5.5.0 is complete
   **Then** `cancelOrder()` is functional on both Kalshi and Polymarket connectors
   **And** cancellation errors are wrapped in `ExecutionError` with appropriate error codes

2. **Given** mock files are duplicated across 15+ test files
   **When** Story 5.5.0 is complete
   **Then** centralized mock factories exist: `createMockPlatformConnector()`, `createMockRiskManager()`, `createMockExecutionEngine()`
   **And** each factory returns a complete mock with sensible defaults and per-call overrides
   **And** all existing test files are migrated to use factories (zero duplicated mock definitions)

3. **Given** P&L source-of-truth confusion occurred in Stories 5.3, 5.4, 5.5
   **When** Story 5.5.0 is complete
   **Then** `gotchas.md` exists in project root with P&L source-of-truth rule: "Always compute P&L from order fill records, never from `position.entryPrices`"
   **And** rule includes a code example showing correct vs incorrect approach

4. **Given** technical debt items accumulated across Epics 2-5
   **When** Story 5.5.0 is complete
   **Then** `technical-debt.md` is updated: Kalshi dedup marked resolved, Epic 5 items added, gas estimation references its Epic 6 story

5. **Given** reconciliation module lives in `src/reconciliation/` not `persistence/`
   **When** Story 5.5.0 is complete
   **Then** architecture doc reflects actual module location with rationale (ADR from Story 5.5)

6. **Given** persistence repository coverage is 52.17% statements / 0% branches
   **When** Story 5.5.0 is complete
   **Then** coverage audit documents which untested paths are business logic vs Prisma pass-through
   **And** specific gaps are flagged for coverage in stories that touch those files

## Out of Scope

- **Paper trading connector** — Story 5.5.1 (requires this story's interface freeze first)
- **Paper position state isolation** — Story 5.5.2
- **Mixed mode validation** — Story 5.5.3
- **Gas estimation implementation** — Story 6.0
- **Monitoring module** — Epic 6
- **Dashboard module** — Epic 7
- **New interface methods beyond `cancelOrder()`** — Interface freeze takes effect after this story

## Tasks / Subtasks

- [x] Task 1: Implement `cancelOrder()` on KalshiConnector (AC: 1)
  - [x] 1.1 Extend the `KalshiOrdersApi` local interface (line 40 in `kalshi.connector.ts`) to add `cancelOrder(orderId: string): Promise<KalshiCancelOrderResponse>` — Kalshi SDK's `OrdersApi` already has `cancelOrder(orderId)` returning `AxiosPromise<CancelOrderResponse>` with `{ order: Order, reduced_by: number, reduced_by_fp: string }`
  - [x] 1.2 Implement `cancelOrder(orderId: string): Promise<CancelResult>` in `KalshiConnector`:
    - Check `this.connected` — if not, throw `PlatformApiError` (code 1001)
    - Call `this.rateLimiter.acquireWrite()` — cancel is a **DELETE** operation that mutates order state (same tier as `submitOrder`, NOT `acquireRead()`)
    - Call `this.ordersApi.cancelOrder(orderId)` wrapped in `withRetry()` with `RETRY_STRATEGIES.NETWORK_ERROR`
    - Map response using `response.data.order.status` (the `OrderStatus` enum — NOT `reduced_by`):
      - `order.status === 'canceled'` → return `{ orderId, status: 'cancelled' }`
      - `order.status === 'executed'` (order filled before cancel arrived) → return `{ orderId, status: 'already_filled' }`
      - Note: `reduced_by` is the quantity reduced, NOT the cancellation status indicator. Do NOT use `reduced_by > 0` as the primary status check.
    - Handle errors: 404/not found → return `{ orderId, status: 'not_found' }`, other errors → throw `PlatformApiError` via `this.mapError(error)`
  - [x] 1.3 Unit tests: cancel success (status=canceled), not connected, order not found (404), order already filled (status=executed), SDK error, rate limiter called with acquireWrite

- [x] Task 2: Implement `cancelOrder()` on PolymarketConnector (AC: 1)
  - [x] 2.1 Implement `cancelOrder(orderId: string): Promise<CancelResult>` in `PolymarketConnector`:
    - Check `this.connected && this.clobClient` — if not, throw `PlatformApiError` (code 1001)
    - Call `this.rateLimiter.acquireWrite()` — cancel is a **DELETE** operation (same tier as `submitOrder`, NOT `acquireRead()`)
    - Call `this.clobClient.cancelOrder({ orderID: orderId })` — Polymarket's `ClobClient.cancelOrder()` accepts `OrderPayload { orderID: string }` and returns `Promise<any>`. Internally sends `DELETE /order` with L2 auth headers.
    - The CLOB client does NOT throw structured errors — check for `"NOT_FOUND"` / `"MATCHED"` strings in error messages. Map: success → `{ orderId, status: 'cancelled' }`, not found → `{ orderId, status: 'not_found' }`, already matched → `{ orderId, status: 'already_filled' }`, other → throw `PlatformApiError`
  - [x] 2.2 Use `withRetry()` with `RETRY_STRATEGIES.NETWORK_ERROR` (same as `getOrder()`)
  - [x] 2.3 Unit tests: cancel success, not connected, order not found, order already matched/filled, SDK error, rate limiter called with acquireWrite

- [x] Task 3: Create centralized mock factories (AC: 2)
  - [x] 3.1 Create `src/test/mock-factories.ts` (new file in test utilities)
  - [x] 3.2 Implement `createMockPlatformConnector(overrides?)` factory:
    - Returns complete `IPlatformConnector` mock with ALL 11 methods: `connect`, `disconnect`, `getPlatformId`, `getHealth`, `getOrderBook`, `submitOrder`, `cancelOrder`, `getOrder`, `getPositions`, `getFeeSchedule`, `onOrderBookUpdate`
    - Sensible defaults: `getPlatformId` returns `PlatformId.KALSHI`, `getHealth` returns `{ status: 'healthy' }`, etc.
    - Accept overrides parameter for per-test customization
    - Accept `platformId` parameter to switch between KALSHI/POLYMARKET defaults
  - [x] 3.3 Implement `createMockRiskManager(overrides?)` factory:
    - Returns complete `IRiskManager` mock with ALL 13 methods: `validatePosition`, `getCurrentExposure`, `getOpenPositionCount`, `updateDailyPnl`, `isTradingHalted`, `haltTrading`, `resumeTrading`, `recalculateFromPositions`, `processOverride`, `reserveBudget`, `commitReservation`, `releaseReservation`, `closePosition`
    - Sensible defaults: `isTradingHalted` returns `false`, `validatePosition` returns valid result, etc.
  - [x] 3.4 Implement `createMockExecutionEngine(overrides?)` factory:
    - Returns complete `IExecutionEngine` mock with required methods
    - Check `IExecutionEngine` interface in `common/interfaces/` for exact method list
  - [x] 3.5 Unit tests for each factory: verify all interface methods present, verify defaults, verify overrides work

- [x] Task 4: Migrate all existing test files to use mock factories (AC: 2)
  - [x] 4.1 **Files using IPlatformConnector mocks (search for `KALSHI_CONNECTOR_TOKEN` or `POLYMARKET_CONNECTOR_TOKEN`):**
    - `src/modules/execution/execution.service.spec.ts` (lines 145-192 — inline partial mock)
    - `src/modules/execution/single-leg-resolution.service.spec.ts` (lines 88-124 — inline full mock)
    - `src/modules/execution/exposure-alert-scheduler.service.spec.ts` (lines 99-134 — inline full mock)
    - `src/modules/exit-management/exit-monitor.service.spec.ts` (lines 93-141 — inline partial mock)
    - `src/reconciliation/startup-reconciliation.service.spec.ts` (lines 15-40 — factory already exists but local)
    - `src/modules/data-ingestion/data-ingestion.service.spec.ts` (lines 22-28 — partial mock)
    - `src/modules/arbitrage-detection/detection.service.spec.ts` (lines 42-49 — minimal mock)
  - [x] 4.2 **Files using IRiskManager mocks (search for `RISK_MANAGER_TOKEN`):**
    - `src/modules/execution/execution.service.spec.ts`
    - `src/modules/execution/single-leg-resolution.service.spec.ts`
    - `src/modules/execution/execution-queue.service.spec.ts`
    - `src/modules/exit-management/exit-monitor.service.spec.ts`
    - ~~`src/modules/exit-management/exposure-alert-scheduler.service.spec.ts`~~ (does not use `RISK_MANAGER_TOKEN` — migrated for platform connector mocks only in Task 4.1)
    - `src/modules/risk-management/risk-override.controller.spec.ts`
    - `src/reconciliation/startup-reconciliation.service.spec.ts`
  - [x] 4.3 For each file: import factory, replace inline mock with factory call + per-test overrides. **CRITICAL:** Preserve any test-specific mock behaviors (e.g., `mockReturnValue`, `mockResolvedValue` chains set up in individual tests) — factory provides defaults, tests still override as needed.
  - [x] 4.4 Run `pnpm test` after each file migration to ensure zero regressions. Do NOT batch migrations.

- [x] Task 5: Update `gotchas.md` with P&L source-of-truth rule (AC: 3)
  - [x] 5.1 Add entry #7 to `docs/gotchas.md` (file already exists at `pm-arbitrage-engine/docs/gotchas.md`, currently has 6 entries):

    ```
    ## 7. P&L Source of Truth: Order Fill Records, Not Position Entry Prices

    **Source:** Stories 5.3, 5.4, 5.5 Dev Notes

    Always compute P&L from order fill records (`order.fillPrice`, `order.fillSize`), never from `position.entryPrices`. The `entryPrices` field is a convenience snapshot set at position creation time and may drift from reality if partial fills or reconciliation adjustments occur.

    **Problem:**
    const pnl = position.entryPrices.kalshi - position.entryPrices.polymarket; // WRONG — uses snapshot, not actual fills

    **Solution:**
    const kalshiCost = new Decimal(order.kalshiOrder.fillPrice.toString()).mul(new Decimal(order.kalshiOrder.fillSize.toString()));
    const polyCost = new Decimal(order.polymarketOrder.fillPrice.toString()).mul(new Decimal(order.polymarketOrder.fillSize.toString()));
    const pnl = kalshiCost.plus(polyCost).minus(totalCapitalDeployed); // Correct — uses actual fill data
    ```

- [x] Task 6: Update `technical-debt.md` (AC: 4)
  - [x] 6.1 Mark item #1 (Kalshi dedup) as resolved — Story 4.5.5 extracted `normalizeKalshiLevels` utility
  - [x] 6.2 Mark item #2 (execution queue TODO) as resolved — Story 5.1 implemented `IExecutionEngine.execute()` call
  - [x] 6.3 Update item #3 (gas estimation) to reference Epic 6, Story 6.0 explicitly
  - [x] 6.4 Add new items from Epic 5:
    - `cancelOrder()` placeholder removed (this story — mark as resolved after Task 1+2)
    - `getPositions()` still unimplemented on both connectors (future — not needed until portfolio-level reconciliation)
    - Reconciliation module at `src/reconciliation/` instead of `persistence/` per architecture spec (intentional deviation, ADR documented)
    - Persistence repository coverage gap: 52.17% statements / 0% branches (coverage audit in Task 7)

- [x] Task 7: Persistence coverage audit (AC: 6)
  - [x] 7.1 Run `pnpm test:cov` and capture persistence module coverage breakdown
  - [x] 7.2 For each repository (`position.repository.ts`, `order.repository.ts`, `contract-match.repository.ts`, `audit-log.repository.ts`, `risk-state.repository.ts`, `order-book-snapshot.repository.ts`):
    - Identify untested methods/branches
    - Classify each: **business logic** (needs tests) vs **Prisma pass-through** (simple delegation, low risk)
    - Flag business logic gaps for specific future stories (e.g., "position.repository.findActivePositions() needs branch coverage for empty result + error paths — add in next story touching reconciliation")
  - [x] 7.3 Document findings in a `docs/coverage-audit.md` file
  - [x] 7.4 Add untested business logic paths as tech debt items in `technical-debt.md`

- [x] Task 8: Update architecture documentation (AC: 5)
  - [x] 8.1 In `_bmad-output/planning-artifacts/architecture.md`, find the project structure tree (around line 566) where `startup-reconciliation.service.ts` is listed under `persistence/`
  - [x] 8.2 Update to reflect actual location: `src/reconciliation/` as a dedicated module with its own directory
  - [x] 8.3 Add brief ADR note: "Reconciliation was moved from `persistence/` to a dedicated `ReconciliationModule` at `src/reconciliation/` during Story 5.5 to avoid expanding `PersistenceModule`'s dependency surface and preventing circular DI."
  - [x] 8.4 Verify no other architecture doc references to the old location

## Dev Notes

### cancelOrder() Implementation Details

**Kalshi SDK (VERIFIED from node_modules/kalshi-typescript v3.6.0):**

- `OrdersApi.cancelOrder(orderId: string, subaccount?: number)` → `AxiosPromise<CancelOrderResponse>`
- HTTP method: `DELETE /portfolio/orders/{order_id}`
- `CancelOrderResponse` type (verified): `{ order: Order, reduced_by: number, reduced_by_fp: string }`
- `Order.status` is typed as `OrderStatus` enum: `'resting' | 'canceled' | 'executed'` — there are ONLY these 3 values
- The existing `KalshiOrdersApi` local interface (line 40 of `kalshi.connector.ts`) currently only declares `getOrder()` — you MUST extend it to add `cancelOrder(orderId: string): Promise<KalshiCancelOrderResponse>`
- Define `KalshiCancelOrderResponse` inline: `{ data: { order: { order_id: string; status: string; remaining_count: number; fill_count: number }; reduced_by: number } }`
- **CRITICAL STATUS MAPPING — use `order.status`, NOT `reduced_by`:**
  - `order.status === 'canceled'` → `'cancelled'` (cancel succeeded)
  - `order.status === 'executed'` → `'already_filled'` (order filled before cancel arrived, `reduced_by` will be 0)
  - `reduced_by` is the quantity reduced from the resting amount — use it for logging only, NOT for status determination
- **Rate limiter: use `acquireWrite()`** — cancel is DELETE (write tier), same as `submitOrder()`. Do NOT use `acquireRead()`.
- Follow the EXACT same pattern as `getOrder()`: connected check → rate limiter → withRetry → map response → error handling with `mapError()`

**Polymarket CLOB Client (VERIFIED from node_modules/@polymarket/clob-client v5.2.3):**

- `ClobClient.cancelOrder(payload: OrderPayload): Promise<any>` where `OrderPayload = { orderID: string }`
- HTTP method: `DELETE /order` with L2 auth headers (requires `canL2Auth()` — wallet signer + API creds)
- The client's `cancelOrder` method calls `this.del()` internally — it sends the `OrderPayload` as request body
- Response is loosely typed `Promise<any>` — success typically returns an acknowledgment object
- Error handling must be string-based (CLOB client does not use structured error codes):
  - Check error message for `"not found"` / `"404"` → `'not_found'`
  - Check error message for `"matched"` / `"already"` → `'already_filled'`
  - Other errors → throw `PlatformApiError` via `this.mapError(error)`
- **Rate limiter: use `acquireWrite()`** — cancel is DELETE (write tier), same as `submitOrder()`. Do NOT use `acquireRead()`.
- Follow the EXACT same error handling pattern as `getOrder()` in `polymarket.connector.ts`: not-found → return result with `'not_found'` status, everything else → throw `PlatformApiError`
- Also available but NOT needed: `cancelOrders(ordersHashes[])` for batch cancel, `cancelAll()` for all orders

**CancelResult type** (already defined in `src/common/types/platform.type.ts`):

```typescript
export interface CancelResult {
  orderId: string;
  status: 'cancelled' | 'not_found' | 'already_filled';
}
```

### Mock Factory Design

**Location:** `src/test/mock-factories.ts`

The reconciliation spec file (`startup-reconciliation.service.spec.ts`) already has local `createMockConnector()` and `createMockRiskManager()` factories — use these as the **template** for the centralized versions. The pattern:

```typescript
export const createMockPlatformConnector = (
  platformId: PlatformId = PlatformId.KALSHI,
  overrides: Partial<Record<keyof IPlatformConnector, unknown>> = {},
) => ({
  connect: vi.fn(),
  disconnect: vi.fn(),
  getPlatformId: vi.fn().mockReturnValue(platformId),
  getHealth: vi.fn().mockReturnValue({ status: 'healthy', platformId }),
  getOrderBook: vi.fn(),
  submitOrder: vi.fn(),
  cancelOrder: vi.fn(),
  getOrder: vi.fn(),
  getPositions: vi.fn(),
  getFeeSchedule: vi.fn().mockReturnValue({
    platformId,
    makerFeePercent: 0,
    takerFeePercent: platformId === PlatformId.KALSHI ? 0 : 2,
    description: `${platformId} fees`,
  }),
  onOrderBookUpdate: vi.fn(),
  ...overrides,
});
```

**Migration strategy for test files:**

Some test files only mock a subset of interface methods (e.g., `detection.service.spec.ts` only needs `getOrderBook`). After migration, these files will get **full** mocks with unused methods as no-op `vi.fn()`. This is fine — unused mocks don't affect test behavior. The benefit: when a new method is added to the interface, only the factory needs updating, not 15+ test files.

**Mock migration safety checks (from code review):**

- After each file migration, verify: (1) all tests still pass, (2) test count unchanged, (3) no silent behavior changes
- Watch for tests that assert on `mock.calls.length` — full mocks with extra no-op methods won't affect call counts since unused methods aren't called
- Tests using partial mocks (e.g., `detection.service.spec.ts` with only `getOrderBook`) will now get full mocks — this is fine because unused `vi.fn()` methods are never called and don't affect assertions
- If any test relied on a method being `undefined` (not just a no-op mock), the migration will change behavior — scan for `expect(connector.someMethod).toBeUndefined()` patterns before migrating

**CRITICAL — preserve test-specific behaviors:** Many tests set up specific mock return values in individual `it()` blocks or `beforeEach()`. The factory provides defaults; tests override what they need:

```typescript
// Before (inline mock):
kalshiConnector = { submitOrder: vi.fn(), getOrderBook: vi.fn(), ... };
kalshiConnector.submitOrder.mockResolvedValue({ orderId: 'k-1', status: 'filled', ... });

// After (factory):
kalshiConnector = createMockPlatformConnector(PlatformId.KALSHI);
kalshiConnector.submitOrder.mockResolvedValue({ orderId: 'k-1', status: 'filled', ... });
```

### Mock Duplication Map (Current State)

Files with duplicated `IPlatformConnector` mocks (7 files):

1. `execution.service.spec.ts` — partial (5 methods), lines 145-192
2. `single-leg-resolution.service.spec.ts` — full (11 methods), lines 88-124
3. `exposure-alert-scheduler.service.spec.ts` — full (11 methods), lines 99-134
4. `exit-monitor.service.spec.ts` — partial (8 methods), lines 93-141
5. `startup-reconciliation.service.spec.ts` — factory exists locally, lines 15-40
6. `data-ingestion.service.spec.ts` — minimal (2 methods), lines 22-28
7. `detection.service.spec.ts` — minimal (1 method), lines 42-49

Files with duplicated `IRiskManager` mocks (7 files):

1. `execution.service.spec.ts`
2. `single-leg-resolution.service.spec.ts` — full (13 methods), lines 126-140
3. `execution-queue.service.spec.ts`
4. `exit-monitor.service.spec.ts` — partial (4 methods), lines 143-148
5. `exposure-alert-scheduler.service.spec.ts`
6. `risk-override.controller.spec.ts`
7. `startup-reconciliation.service.spec.ts` — factory exists locally, lines 42-56

### Interface Freeze Rule

**After this story merges, `IPlatformConnector` and `IRiskManager` are FROZEN.**

No new methods until Epic 6 unless the team discusses and handles the full ripple (mock factory update + decorator update in paper trading connector) in the same PR.

Current `IPlatformConnector` methods (11 total — the final interface):

1. `connect()` / `disconnect()` — lifecycle
2. `getPlatformId()` / `getHealth()` — identity & monitoring
3. `getOrderBook()` / `onOrderBookUpdate()` — market data
4. `submitOrder()` / `cancelOrder()` / `getOrder()` — order management
5. `getPositions()` — portfolio (stub, not implemented yet)
6. `getFeeSchedule()` — fee info

Current `IRiskManager` methods (13 total — the final interface):

1. `validatePosition()` / `reserveBudget()` / `commitReservation()` / `releaseReservation()` — position lifecycle
2. `getCurrentExposure()` / `getOpenPositionCount()` — state queries
3. `updateDailyPnl()` / `closePosition()` — P&L management
4. `isTradingHalted()` / `haltTrading()` / `resumeTrading()` — halt management
5. `recalculateFromPositions()` — reconciliation support
6. `processOverride()` — operator overrides

### DoD Gates (from Epic 4.5 Retro)

1. **Test isolation:** No shared mutable state between tests — mock factories return fresh mocks via `vi.fn()` per call
2. **Interface preservation:** No breaking changes to existing interface methods — `cancelOrder` already declared, just not implemented
3. **Normalization ownership:** Connectors own all platform-specific normalization — cancelOrder follows same error mapping patterns as submitOrder/getOrder

### Sequencing Constraint

This story MUST complete before Story 5.5.1 begins. Dependency chain: `cancelOrder()` → mock factory (needs final interface) → decorator in 5.5.1 (wraps stable interface).

### Project Structure Notes

**New files:**

- `src/test/mock-factories.ts` — centralized mock factory functions
- `src/test/mock-factories.spec.ts` — factory tests
- `docs/coverage-audit.md` — persistence coverage audit results

**Modified files:**

- `src/connectors/kalshi/kalshi.connector.ts` — implement `cancelOrder()`, extend `KalshiOrdersApi` interface
- `src/connectors/kalshi/kalshi.connector.spec.ts` — replace placeholder test with real cancel tests
- `src/connectors/polymarket/polymarket.connector.ts` — implement `cancelOrder()`
- `src/connectors/polymarket/polymarket.connector.spec.ts` — replace placeholder test with real cancel tests
- `src/modules/execution/execution.service.spec.ts` — migrate to mock factories
- `src/modules/execution/single-leg-resolution.service.spec.ts` — migrate to mock factories
- `src/modules/execution/execution-queue.service.spec.ts` — migrate to mock factories
- `src/modules/execution/exposure-alert-scheduler.service.spec.ts` — migrate to mock factories
- `src/modules/exit-management/exit-monitor.service.spec.ts` — migrate to mock factories
- `src/modules/risk-management/risk-override.controller.spec.ts` — migrate to mock factories
- `src/modules/data-ingestion/data-ingestion.service.spec.ts` — migrate to mock factories
- `src/modules/arbitrage-detection/detection.service.spec.ts` — migrate to mock factories
- `src/reconciliation/startup-reconciliation.service.spec.ts` — migrate to centralized factories (replace local factories)
- `docs/gotchas.md` — add P&L source-of-truth rule (#7)
- `technical-debt.md` — mark resolved items, add Epic 5 items
- `_bmad-output/planning-artifacts/architecture.md` — update reconciliation module location

### Rate Limiter Verification (CONFIRMED from codebase)

Both connectors have `acquireRead()` and `acquireWrite()` on their `RateLimiter` instances:

- `getOrderBook()` → `acquireRead()` (Kalshi line 145, Polymarket line 214) ✅
- `submitOrder()` → `acquireWrite()` (Kalshi line 191, Polymarket line 339) ✅
- `getOrder()` → `acquireRead()` (Kalshi line 273, Polymarket line 465) ✅
- `cancelOrder()` → **MUST use `acquireWrite()`** — it's a DELETE/mutation, same tier as `submitOrder()`

### Event Emission for Cancellations

Cancel operations do NOT need to emit events in this story. Rationale:

- `cancelOrder()` is a tool called by the reconciliation module and future exit management
- The **caller** decides what events to emit based on the `CancelResult` (e.g., `ReconciliationDiscrepancyEvent` if cancel fails)
- Adding event emission inside the connector violates the connector's single responsibility (platform API adapter only)
- Events are part of the fan-out path, not the connector layer

If the team later needs `order.cancelled` events, they should be emitted by the module calling `cancelOrder()`, not the connector itself.

### Existing Code Patterns to Follow

**cancelOrder pattern** — mirror `getOrder()` with one key difference (acquireWrite):

- Connected check → `acquireWrite()` → withRetry → response mapping → error handling
- Kalshi: `ordersApi.cancelOrder(orderId)`, map via `response.data.order.status` (use `OrderStatus` enum, NOT `reduced_by`)
- Polymarket: `clobClient.cancelOrder({ orderID: orderId })`, handle response (DELETE /order with L2 auth)
- 404/not-found → return `{ status: 'not_found' }` (DON'T throw)
- Already filled → return `{ status: 'already_filled' }` (DON'T throw)
- Other errors → throw `PlatformApiError` via `mapError()`

**Test file mock registration pattern:**

```typescript
{ provide: KALSHI_CONNECTOR_TOKEN, useValue: kalshiConnector },
{ provide: POLYMARKET_CONNECTOR_TOKEN, useValue: polymarketConnector },
{ provide: RISK_MANAGER_TOKEN, useValue: riskManager },
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5.5, Story 5.5.0]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure — connectors/paper/]
- [Source: _bmad-output/planning-artifacts/architecture.md#Module Dependency Graph]
- [Source: _bmad-output/implementation-artifacts/5-5-startup-reconciliation-crash-recovery.md#Dev Notes — Architecture Constraints]
- [Source: _bmad-output/implementation-artifacts/5-5-startup-reconciliation-crash-recovery.md#Dev Notes — getOrder() Implementation Details]
- [Source: pm-arbitrage-engine/docs/gotchas.md — existing 6 entries]
- [Source: pm-arbitrage-engine/technical-debt.md — existing 6 items]
- [Source: CLAUDE.md#Architecture, #Error Handling, #Naming Conventions, #Testing]
- [Source: node_modules/kalshi-typescript — OrdersApi.cancelOrder(), CancelOrderResponse]
- [Source: node_modules/@polymarket/clob-client — ClobClient.cancelOrder(OrderPayload)]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — all tasks completed without debugging issues.

### Completion Notes List

- Task 1: Kalshi `cancelOrder()` — mirrors `getOrder()` pattern with `acquireWrite()`. Extended `KalshiOrdersApi` interface and added `KalshiCancelOrderResponse` type. Maps `order.status` (not `reduced_by`) for result.
- Task 2: Polymarket `cancelOrder()` — uses case-insensitive `.toLowerCase()` for error string matching. Calls `clobClient.cancelOrder({ orderID })`.
- Task 3: Mock factories in `src/test/mock-factories.ts` — 3 factories with sensible defaults and override support. 17 factory tests.
- Task 4: Migrated 9 test files. All inline mock definitions replaced. Test count grew from 731 → 758 (new cancel + factory tests). Zero regressions.
- Task 5: `gotchas.md` entry #7 added with P&L source-of-truth rule and code examples.
- Task 6: `technical-debt.md` — items #1,#2 resolved, #3 updated, #7-#12 added (Epic 5 items).
- Task 7: `docs/coverage-audit.md` created. Key finding: `OrderRepository.updateOrderStatus()` branch logic (4 test cases needed) and `PositionRepository.findActivePositions()` status list (snapshot test recommended). Added as tech debt #11, #12.
- Task 8: Architecture doc updated — reconciliation module moved from `persistence/` to `src/reconciliation/`, ADR note added, requirements mapping table updated.
- **Code Review Fixes (Amelia, 2026-02-22):**
  - M1: Kalshi `cancelOrder` now throws `PlatformApiError` on unexpected order status instead of silent fallthrough to `'cancelled'`. Added test. (kalshi.connector.ts:309, +1 test)
  - M2: Polymarket `cancelOrder` error matching tightened from `includes('already')` to `includes('already matched')` to prevent false `already_filled` on unrelated "already" errors. Added test. (polymarket.connector.ts:487, +1 test)
  - M3: Mock factory Kalshi fee default (0%) — won't-fix, deliberate test default; fee-sensitive tests already override.
  - L1: `technical-debt.md` #7 wording corrected.
  - L2: `coverage-audit.md` added note about post-review test count (760).
  - L3: Story subtask 4.2 corrected — `exposure-alert-scheduler.service.spec.ts` does not use `RISK_MANAGER_TOKEN`.
  - Test count: 758 → 760 (+2 new tests). Zero regressions.

### File List

**New files:**

- `src/test/mock-factories.ts` — centralized mock factory functions
- `src/test/mock-factories.spec.ts` — factory unit tests (17 tests)
- `docs/coverage-audit.md` — persistence coverage audit results

**Modified files (implementation):**

- `src/connectors/kalshi/kalshi.connector.ts` — `cancelOrder()` implementation + `KalshiCancelOrderResponse` type + `KalshiOrdersApi` extension
- `src/connectors/kalshi/kalshi.connector.spec.ts` — cancel tests (7 tests: 6 original + 1 unexpected status), removed placeholder
- `src/connectors/polymarket/polymarket.connector.ts` — `cancelOrder()` implementation + tightened error matching (review fix M2)
- `src/connectors/polymarket/polymarket.connector.spec.ts` — cancel tests (7 tests: 6 original + 1 ambiguous error), removed placeholder

**Modified files (mock migration):**

- `src/modules/execution/execution.service.spec.ts`
- `src/modules/execution/single-leg-resolution.service.spec.ts`
- `src/modules/execution/execution-queue.service.spec.ts`
- `src/modules/execution/exposure-alert-scheduler.service.spec.ts`
- `src/modules/exit-management/exit-monitor.service.spec.ts`
- `src/modules/risk-management/risk-override.controller.spec.ts`
- `src/modules/data-ingestion/data-ingestion.service.spec.ts`
- `src/modules/arbitrage-detection/detection.service.spec.ts`
- `src/reconciliation/startup-reconciliation.service.spec.ts`

**Modified files (documentation):**

- `docs/gotchas.md` — entry #7 (P&L source-of-truth)
- `technical-debt.md` — resolved #1,#2; updated #3; added #7-#12
- `_bmad-output/planning-artifacts/architecture.md` — reconciliation module location + ADR
