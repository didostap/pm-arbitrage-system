# Story 5.1: Order Submission & Position Tracking

Status: done

## Story

As an operator,
I want the system to submit orders to both platforms and track open positions in the database,
So that I have a reliable record of all trades and their current state.

## Out of Scope

- **Single-leg detection logic** — Story 5.2 owns detection, alerting, and the `SingleLegExposureEvent`. This story only writes the `open_positions` row with status `single_leg_exposed` if the secondary leg fails, but does NOT implement detection timers, alert content, or P&L scenario calculations.
- **Single-leg resolution** (retry/close endpoints) — Story 5.3.
- **Exit monitoring** — Story 5.4.
- **Startup reconciliation** — Story 5.5.
- **Gas estimation for Polymarket** — existing TODO at `polymarket.connector.ts` line 312; deferred.

## Acceptance Criteria

1. **Given** an opportunity has passed risk validation (Epic 4) and is locked for execution
   **When** the execution service processes it
   **Then** the primary leg (determined by `primaryLeg` field in the contract pair config, defaulting to "kalshi") is submitted first via `IPlatformConnector.submitOrder()`
   **And** the second leg is submitted immediately after the first (target: <100ms between submissions, same event loop cycle)
   **And** order book depth is verified before each order placement — minimum size sufficient for target position at expected price

2. **Given** an order is submitted
   **When** the connector's `submitOrder()` returns with status `filled` or `partial`
   **Then** an `OrderFilledEvent` is emitted via EventEmitter2 (one event per leg, so two events on successful two-leg fill)
   **And** both orders are persisted to the `orders` table
   **And** the position is recorded in the `open_positions` table with status `open`

3. **Given** order book depth is insufficient for the target position size
   **When** depth verification fails before the primary leg
   **Then** the opportunity is abandoned, execution lock released, reservation released, and logged as "filtered: insufficient liquidity" (code 2001)

4. **Given** the contract pair config from Epic 3 Story 3.1
   **When** a new pair is defined
   **Then** it includes an optional `primaryLeg` field ("kalshi" | "polymarket", default "kalshi") specifying which platform's leg to execute first

5. **Given** the primary leg has filled but the secondary leg submission fails or returns `rejected`
   **When** the execution service detects the asymmetry
   **Then** the primary order is persisted to `orders`, an `open_positions` row is created with status `single_leg_exposed`, and `ExecutionResult.partialFill = true` is returned
   **And** `commitReservation()` is still called by `ExecutionQueueService` (Task 4.2) because capital is deployed on one leg — `partialFill: true` triggers commit, not release
   **And** if the failed leg was on Polymarket and `submitOrder()` returned `pending` (timeout), the pending order ID must be logged for reconciliation (Story 5.5 will need to check for filled-after-timeout orders)

## Tasks / Subtasks

- [x] Task 1: Create Prisma migration for `orders` and `open_positions` tables (AC: 2, 5)
  - [x] 1.1 Migration: Order model, OpenPosition model with nullable FKs to orders
  - [x] 1.2 Add enums: OrderStatus, PositionStatus
  - [x] 1.3 Migration applied: `20260218233846_add_orders_positions`
  - [x] 1.4 Created `position.repository.ts` and `order.repository.ts`

- [x] Task 2: Create `ExecutionError` class (AC: 3)
  - [x] 2.1 Created `execution-error.ts` extending SystemError (codes 2000–2999)
  - [x] 2.2 Defined codes: 2000–2004
  - [x] 2.3 Exported from `common/errors/index.ts`

- [x] Task 3: Create `IExecutionEngine` interface and `ExecutionService` (AC: 1, 2, 3, 5)
  - [x] 3.1 Defined `IExecutionEngine` in `common/interfaces/execution-engine.interface.ts`
  - [x] 3.2 Created `execution.service.ts` implementing `IExecutionEngine`
  - [x] 3.3 Implemented depth verification with bid/ask quantity checks
  - [x] 3.4 Two-leg submission: primary → immediate secondary via `await`
  - [x] 3.5 Reads `primaryLeg` from config, defaults to 'kalshi'
  - [x] 3.6 Emits `OrderFilledEvent` per filled leg
  - [x] 3.7 Persists orders and positions with correct statuses
  - [x] 3.8 Pre-primary depth failure returns failure, does NOT touch reservation

- [x] Task 4: Update `ExecutionQueueService` integration (AC: 1, 5)
  - [x] 4.1 Replaced TODO with `IExecutionEngine.execute()` call
  - [x] 4.2 Commit on success/partialFill, release on full failure
  - [x] 4.3 Error logging from `result.error`

- [x] Task 5: Add `primaryLeg` to contract pair config (AC: 4)
  - [x] 5.1 Added `primaryLeg` to ContractMatch Prisma model (nullable, no DB default). Migration: `20260218233942_add_primary_leg_to_contract_matches`. Loader defaults to 'kalshi'.

- [x] Task 6: Implement Kalshi `submitOrder()` (AC: 1, 2)
  - [x] 6.1 Implemented with `marketApi.createOrder()`, withRetry, rate limiting
  - [x] 6.2 Price conversion: decimal × 100 → cents for submission, ÷ 100 for response
  - [x] 6.3 Rate limiting via `rateLimiter.acquireWrite()`
  - [x] 6.4 Errors mapped via existing `mapError()`

- [x] Task 7: Implement Polymarket `submitOrder()` (AC: 1, 2)
  - [x] 7.1 Implemented with `clobClient.createOrder()` + `postOrder()`, 5s poll timeout
  - [x] 7.2 Maps CLOB responses to OrderResult (prices already decimal)
  - [x] 7.3 Rate limiting via `rateLimiter.acquireWrite()`
  - [x] 7.4 Errors mapped via existing `mapError()`, NOT_CONNECTED code 1015 added

- [x] Task 8: Create execution event classes (AC: 2)
  - [x] 8.1 Created `OrderFilledEvent` in `execution.events.ts`
  - [x] 8.2 Created `ExecutionFailedEvent` with reason code and context
  - [x] 8.3 Event catalog constants verified (ORDER_FILLED, SINGLE_LEG_EXPOSURE)

- [x] Task 9: Tests (all ACs)
  - [x] 9.1 Unit tests for ExecutionService: happy path, depth failure, primary leg ordering
  - [x] 9.2 Unit test: secondary depth fails → partialFill: true, single_leg_exposed
  - [x] 9.3 Unit test: secondary rejected → partialFill: true, single_leg_exposed
  - [x] 9.4 Unit tests for ExecutionError construction and code ranges
  - [x] 9.5 Unit tests for order/position repositories (CRUD operations)
  - [x] 9.6 Unit tests for ExecutionQueueService: commit on success, commit on partialFill, release on failure
  - [x] 9.7 Unit tests for Kalshi submitOrder: price conversion, status mapping, error handling
  - [x] 9.8 Unit tests for Polymarket submitOrder: not-connected error
  - [x] 9.9 All 536 tests pass (was 525 before, added 11 new)

## Dev Notes

### Architecture Constraints

- **Hot path is synchronous and blocking:** Detection → Risk validation → Execution. Never execute without risk validation. This is a direct synchronous call chain via DI injection — NOT EventEmitter2.
- **Fan-out is async:** After execution, emit events via EventEmitter2. Monitoring subscribes. Telegram API timeouts must NEVER delay the next execution cycle.
- **Module dependency rules:**
  - `modules/execution/` → `connectors/` (submits orders) + `modules/risk-management/` (budget reservation) — ALLOWED
  - `connectors/` NEVER imports from `modules/` — FORBIDDEN
  - All cross-module communication through interfaces in `common/interfaces/`

### Fill Confirmation Model

**Both connectors treat `submitOrder()` as a blocking call that returns fill status directly:**

- **Kalshi:** REST API is synchronous. POST to order endpoint returns fill/reject in the response body. No webhook/polling needed. `submitOrder()` awaits the HTTP response and maps it to `OrderResult`.
- **Polymarket:** CLOB is off-chain order matching via `@polymarket/clob-client`. The flow is `createOrder()` → `postOrder()`. The SDK returns order status. If the order isn't immediately matched, poll `getOrder()` with a 5-second timeout. If still `pending` after timeout, return `OrderResult { status: 'pending' }` — `ExecutionService` treats non-`filled` status as a failure for two-leg execution purposes. **Operational risk:** A pending Polymarket order may still fill after timeout, creating real exposure the system doesn't track. The pending order ID MUST be persisted to the `orders` table (status: `pending`) and logged at `warning` severity so Story 5.5 (startup reconciliation) can detect filled-after-timeout orders. Do NOT cancel the pending order — cancellation racing with a fill is worse than a known-pending order.

**`OrderResult.status` interpretation in `ExecutionService`:**
- `filled` → leg succeeded, proceed
- `partial` → treat as success for this story (partial fills are real exposure)
- `pending` / `rejected` → leg failed

### Commit/Release Ownership

**`ExecutionQueueService` owns all `commitReservation()` / `releaseReservation()` calls.** `ExecutionService` never touches the reservation — it only returns `ExecutionResult`. This prevents double-commit bugs and keeps the reservation lifecycle in one place.

```
ExecutionQueueService:
  1. reserveBudget()
  2. IExecutionEngine.execute()
  3. if result.success || result.partialFill → commitReservation()
     else → releaseReservation()
```

### Existing Code to Build On

**Execution Queue (already implemented):**
- `execution-queue.service.ts` — processes `RankedOpportunity[]` sequentially with lock acquisition and budget reservation
- **TODO at line ~53:** Replace `commitReservation()` with `IExecutionEngine.execute()` → then commit/release based on result
- `execution-lock.service.ts` — mutex lock with 30s auto-release timeout

**Budget Reservation Lifecycle (already implemented in risk-management):**
1. `reserveBudget(request)` → creates temporary `BudgetReservation` in-memory
2. Execution succeeds → `commitReservation(reservationId)` → permanent state, increments openPositionCount + totalCapitalDeployed
3. Execution fails → `releaseReservation(reservationId)` → returns capital to pool

**Platform Connectors (stubs ready for implementation):**
- `kalshi.connector.ts` — `submitOrder()` currently throws `"submitOrder not implemented - Epic 5 Story 5.1"`
- `polymarket.connector.ts` — `submitOrder()` currently throws `"submitOrder not implemented - Epic 5"`
- Both already implement `getOrderBook()`, `connect()`, `disconnect()`, `getHealth()`, `getFeeSchedule()`
- Kalshi uses `MarketApi` SDK + WebSocket; Polymarket uses `@polymarket/clob-client` with EOA signature

**Event System (partially scaffolded):**
- Event catalog in `event-catalog.ts` already defines: `ORDER_FILLED: 'execution.order.filled'`, `SINGLE_LEG_EXPOSURE: 'execution.single_leg.exposure'`, `EXIT_TRIGGERED: 'execution.exit.triggered'`
- `BaseEvent` abstract class exists — all events extend it with `timestamp` and `correlationId`
- Risk events (`BudgetReservedEvent`, `BudgetCommittedEvent`, etc.) are fully implemented as reference pattern

**Types Already Defined:**
- `OrderParams { contractId, side, quantity, price, type }` — input to `submitOrder()`
- `OrderResult { orderId, platformId, status, filledQuantity, filledPrice, timestamp }` — return from `submitOrder()`
- `RankedOpportunity { opportunity, netEdge: Decimal, reservationRequest }` — input from detection
- `BudgetReservation { reservationId, opportunityId, reservedPositionSlots, reservedCapitalUsd, correlationExposure, createdAt }`
- `PriceLevel { price, quantity }` — order book depth entries

**Error Classes (pattern to follow):**
- `SystemError` base class: `constructor(code, message, severity, retryStrategy?, metadata?)`
- `PlatformApiError` (1000-1999), `RiskLimitError` (3000-3999), `SystemHealthError` (4000-4999) all exist
- `ExecutionError` (2000-2999) does NOT exist yet — Story 5.1 creates it

### IExecutionEngine Interface Design

```typescript
interface IExecutionEngine {
  execute(
    opportunity: RankedOpportunity,
    reservation: BudgetReservation,
  ): Promise<ExecutionResult>;
}

interface ExecutionResult {
  success: boolean;        // true only if both legs filled
  partialFill: boolean;    // true if primary filled but secondary failed (single-leg)
  positionId?: string;     // set if position row was created (success or partialFill)
  primaryOrder?: OrderResult;
  secondaryOrder?: OrderResult;
  error?: ExecutionError;
}
```

### Depth Verification Logic

Before each leg submission, check that the order book has sufficient liquidity:
- For a BUY: sum ask quantities at or below target price >= target size
- For a SELL: sum bid quantities at or above target price >= target size
- Use `IPlatformConnector.getOrderBook(contractId)` to get fresh book
- **Pre-primary failure:** abandon entirely, return `{ success: false, partialFill: false }`
- **Post-primary (secondary depth) failure:** primary is already filled — real money at risk. Create position with status `single_leg_exposed`, return `{ success: false, partialFill: true }`

**Rate limit note:** Depth verification calls `getOrderBook()` twice per execution (once per platform). During high-frequency detection cycles this could push toward rate limits. Both connectors already use `RateLimiter` (70% threshold). If rate limited during depth check, treat as insufficient liquidity (code 2001) rather than retrying.

### Two-Leg Submission Sequence

```
1. Read primaryLeg from contract pair config (default: "kalshi" applied in ExecutionService)
2. Determine primary and secondary connectors
3. Verify depth on primary platform → insufficient = abandon (release reservation upstream)
4. Submit primary leg via connector.submitOrder()
5. If primary fails (rejected/pending) → return { success: false, partialFill: false }
6. Verify depth on secondary platform → insufficient = single-leg (see step 9)
7. Submit secondary leg via connector.submitOrder()
8. If both fill → persist both orders + position (status: open), emit 2x OrderFilledEvent, return { success: true }
9. If secondary fails or depth insufficient → persist primary order + position (status: single_leg_exposed), emit 1x OrderFilledEvent for primary, return { success: false, partialFill: true }
```

**CRITICAL:** Between primary and secondary submission, do NOT yield the event loop unnecessarily. Use direct `await` for the sequential calls. Target <100ms between submissions.

### Database Schema Design

**Migration order:** Single migration creates both tables. `orders` table has NO FK to `open_positions`. `open_positions` references `orders` (one-directional). This avoids circular FK constraints.

**orders table:**
```sql
order_id        UUID PRIMARY KEY DEFAULT gen_random_uuid()
platform        PlatformId (enum)
contract_id     VARCHAR NOT NULL
pair_id         VARCHAR NOT NULL REFERENCES contract_matches(match_id)
side            VARCHAR NOT NULL ('buy' | 'sell')
price           DECIMAL(20,8) NOT NULL
size            DECIMAL(20,8) NOT NULL
status          OrderStatus (enum: pending, filled, partial, rejected, cancelled)
fill_price      DECIMAL(20,8)
fill_size       DECIMAL(20,8)
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL
```

**open_positions table:**
```sql
position_id             UUID PRIMARY KEY DEFAULT gen_random_uuid()
pair_id                 VARCHAR NOT NULL REFERENCES contract_matches(match_id)
polymarket_order_id     UUID REFERENCES orders(order_id)  -- nullable
kalshi_order_id         UUID REFERENCES orders(order_id)  -- nullable
polymarket_side         VARCHAR
kalshi_side             VARCHAR
entry_prices            JSONB NOT NULL  -- {polymarket: string, kalshi: string} (decimal strings)
sizes                   JSONB NOT NULL  -- {polymarket: string, kalshi: string} (decimal strings)
expected_edge           DECIMAL(20,8) NOT NULL
status                  PositionStatus (enum: open, single_leg_exposed, exit_partial, closed, reconciliation_required)
created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at              TIMESTAMPTZ NOT NULL
```

**Note:** Both `kalshi_order_id` and `polymarket_order_id` are nullable to support single-leg positions (whichever leg failed has a null FK). JSONB values use decimal strings, not floats, to preserve precision.

### Price Normalization Reminder

- Internal prices: decimal probability 0.00–1.00
- Kalshi API: cents (÷100 for internal, ×100 for submission)
- Polymarket: already decimal, no conversion needed
- Shared utility: `src/common/utils/kalshi-price.util.ts` → `normalizeKalshiLevels()` for order book conversion
- For order submission to Kalshi: multiply internal price × 100 for cents

### Carry-Forward Technical Debt (from Epic 4.5 Retro)

- **Execution engine placeholder** — `execution-queue.service.ts` line 53 TODO → **THIS STORY resolves it**
- **Gas estimation TODO** — `polymarket.connector.ts` line 312 → not this story, but note for Epic 5 scope
- Use `Decimal` (decimal.js) for all financial calculations — pattern established in Epic 3

### DoD Gates (from Epic 4.5 Retro Action Items)

1. **Test isolation** — all new tests must mock platform API calls, no live HTTP
2. **Interface preservation** — do not rename existing interface methods; add new ones alongside if needed
3. **Normalization ownership** — Kalshi price conversion uses shared `normalizeKalshiLevels()` utility from `src/common/utils/kalshi-price.util.ts`

### Project Structure Notes

- New files go in existing module directories per architecture spec
- Repository files in `src/persistence/repositories/`
- Error class in `src/common/errors/`
- Interface in `src/common/interfaces/`
- Event classes in `src/common/events/`
- Co-located tests: `execution.service.spec.ts` next to `execution.service.ts`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5, Story 5.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Execution Module]
- [Source: _bmad-output/planning-artifacts/architecture.md#Platform Connector Interface]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error Handling]
- [Source: _bmad-output/planning-artifacts/architecture.md#Event Emission]
- [Source: _bmad-output/planning-artifacts/architecture.md#Database Schema Strategy]
- [Source: _bmad-output/implementation-artifacts/4-5-5-kalshi-normalization-deduplication.md#Dev Notes]
- [Source: _bmad-output/implementation-artifacts/epic-4-5-retrospective.md#Action Items]
- [Source: CLAUDE.md#Architecture, #Error Handling, #Naming Conventions, #Domain Rules]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List
- All 9 tasks completed, all acceptance criteria met
- 542 tests pass (42 test files), 0 failures
- Lint passes clean (no eslint-disable added)
- Existing test count increased from ~525 to 542

### Code Review Fixes Applied
- **H1**: Decoupled `ExecutionService` from concrete connector classes — now injects via `KALSHI_CONNECTOR_TOKEN`/`POLYMARKET_CONNECTOR_TOKEN` with `IPlatformConnector` type
- **H2**: Fixed wrong event emission on depth failure — now emits `EXECUTION_FAILED` event instead of `ORDER_FILLED` for pre-primary depth failures; added `EXECUTION_FAILED` to event catalog
- **H3**: Added 5 comprehensive Polymarket `submitOrder` tests: immediate fill, delayed fill via polling, 5s timeout → pending, cancellation → rejected, createOrder error
- **M2**: Added runtime validation for `EnrichedOpportunity` cast — returns graceful failure instead of crashing on malformed opportunity data
- **M4**: Documented `side: 'yes'` rationale in Kalshi connector (binary market convention)
- **Created** `pm-arbitrage-engine/src/connectors/connector.constants.ts` (KALSHI_CONNECTOR_TOKEN, POLYMARKET_CONNECTOR_TOKEN)

### File List

**Created:**
- `pm-arbitrage-engine/prisma/migrations/20260218233846_add_orders_positions/migration.sql`
- `pm-arbitrage-engine/prisma/migrations/20260218233942_add_primary_leg_to_contract_matches/migration.sql`
- `pm-arbitrage-engine/src/common/errors/execution-error.ts`
- `pm-arbitrage-engine/src/common/errors/execution-error.spec.ts`
- `pm-arbitrage-engine/src/common/events/execution.events.ts`
- `pm-arbitrage-engine/src/common/interfaces/execution-engine.interface.ts`
- `pm-arbitrage-engine/src/modules/execution/execution.service.ts`
- `pm-arbitrage-engine/src/modules/execution/execution.service.spec.ts`
- `pm-arbitrage-engine/src/persistence/repositories/order.repository.ts`
- `pm-arbitrage-engine/src/persistence/repositories/order.repository.spec.ts`
- `pm-arbitrage-engine/src/persistence/repositories/position.repository.ts`
- `pm-arbitrage-engine/src/persistence/repositories/position.repository.spec.ts`
- `pm-arbitrage-engine/src/connectors/connector.constants.ts` (KALSHI_CONNECTOR_TOKEN, POLYMARKET_CONNECTOR_TOKEN)

**Modified:**
- `pm-arbitrage-engine/prisma/schema.prisma` (OrderStatus/PositionStatus enums, Order/OpenPosition models, primaryLeg on ContractMatch)
- `pm-arbitrage-engine/src/common/errors/index.ts` (export ExecutionError)
- `pm-arbitrage-engine/src/common/events/index.ts` (export execution events)
- `pm-arbitrage-engine/src/common/events/event-catalog.ts` (added EXECUTION_FAILED event name)
- `pm-arbitrage-engine/src/common/interfaces/index.ts` (export IExecutionEngine)
- `pm-arbitrage-engine/src/modules/execution/execution.constants.ts` (EXECUTION_ENGINE_TOKEN)
- `pm-arbitrage-engine/src/modules/execution/execution-queue.service.ts` (replaced TODO with execute+commit/release)
- `pm-arbitrage-engine/src/modules/execution/execution-queue.service.spec.ts` (updated for new execute flow)
- `pm-arbitrage-engine/src/modules/execution/execution.module.ts` (added providers, removed direct connector imports)
- `pm-arbitrage-engine/src/connectors/connector.module.ts` (added token-based connector providers)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.ts` (submitOrder implementation, added side: 'yes' docs)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi.connector.spec.ts` (submitOrder tests)
- `pm-arbitrage-engine/src/connectors/kalshi/kalshi-sdk.d.ts` (CreateOrderRequest/Response types)
- `pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.ts` (submitOrder implementation)
- `pm-arbitrage-engine/src/connectors/polymarket/polymarket.connector.spec.ts` (submitOrder tests: +5 comprehensive tests)
- `pm-arbitrage-engine/src/connectors/polymarket/polymarket-error-codes.ts` (NOT_CONNECTED code)
