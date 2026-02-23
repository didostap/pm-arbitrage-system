# Story 5.5.1: Paper Trading Connector & Mode Configuration

Status: done

## Story

As a system operator,
I want per-platform paper trading mode that decorates real connectors with simulated execution,
so that I can validate the full arbitrage pipeline with real market data but no real capital at risk.

## Acceptance Criteria

1. **Given** `PLATFORM_MODE_KALSHI=paper` in env config
   **When** the application starts
   **Then** the Kalshi connector token resolves to a `PaperTradingConnector` wrapping the real `KalshiConnector`
   **And** all data methods (`getOrderBook`, `getHealth`, `getPlatformId`, `getFeeSchedule`, `onOrderBookUpdate`, `getPositions`, `connect`, `disconnect`) delegate to the real connector
   **And** execution methods (`submitOrder`, `cancelOrder`, `getOrder`) are intercepted by the fill simulator

2. **Given** `PLATFORM_MODE_POLYMARKET=paper` in env config
   **When** the application starts
   **Then** the Polymarket connector token resolves to a `PaperTradingConnector` wrapping the real `PolymarketConnector`
   **And** behavior mirrors AC1 for the Polymarket platform

3. **Given** `PLATFORM_MODE_KALSHI=live` (or unset, default)
   **When** the application starts
   **Then** the Kalshi connector token resolves to the real `KalshiConnector` directly (no wrapper)
   **And** no `PaperTradingConnector` is instantiated for Kalshi

4. **Given** paper mode is active for a platform
   **When** `submitOrder()` is called
   **Then** `FillSimulatorService` generates a simulated fill with configurable latency and slippage
   **And** the result uses the same `OrderResult` interface as live connectors
   **And** the simulated order is tracked in an in-memory map keyed by generated orderId

5. **Given** paper mode is active for a platform
   **When** `cancelOrder(orderId)` is called on a filled order
   **Then** return `{ orderId, status: 'already_filled' }` (mirrors real platform behavior)
   **And** if the orderId does not exist, return `{ orderId, status: 'not_found' }`

6. **Given** paper mode is active for a platform
   **When** `getOrder(orderId)` is called
   **Then** return the simulated order's current status from the in-memory map
   **And** if the orderId does not exist, return `{ orderId, status: 'not_found' }`

7. **Given** paper trading env vars are configured
   **When** the config is loaded
   **Then** `PAPER_FILL_LATENCY_MS_KALSHI` (default: 150), `PAPER_SLIPPAGE_BPS_KALSHI` (default: 5), `PAPER_FILL_LATENCY_MS_POLYMARKET` (default: 800), `PAPER_SLIPPAGE_BPS_POLYMARKET` (default: 15) are parsed as numbers via `Number()` (Gotcha #3)
   **And** invalid values (NaN) cause a startup validation error

8. **Given** platform mode is set
   **When** `getHealth()` is called on a paper-wrapped connector
   **Then** the response includes a `mode: 'paper'` indicator alongside the real connector's health data
   **And** `getPlatformId()` returns the same `PlatformId` as the underlying real connector

## Out of Scope

- **Paper position state isolation** — Story 5.5.2 (requires this story's paper connector first)
- **Mixed mode validation** — Story 5.5.3
- **Persistent paper trade history** — paper orders are in-memory only (MVP)
- **Paper trading P&L tracking** — Story 5.5.2
- **Gas estimation in paper mode** — Story 6.0

## Tasks / Subtasks

- [x] Task 1: Create paper trading types (AC: 7)
  - [x]1.1 Create `src/connectors/paper/paper-trading.types.ts`
  - [x]1.2 Define `PaperTradingConfig` interface:
    ```typescript
    export interface PaperTradingConfig {
      platformId: PlatformId;
      fillLatencyMs: number; // simulated fill delay
      slippageBps: number; // simulated slippage in basis points
    }
    ```
  - [x]1.3 Define `SimulatedOrder` interface:
    ```typescript
    export interface SimulatedOrder {
      orderId: string;
      platformId: PlatformId;
      contractId: string;
      side: 'buy' | 'sell';
      requestedPrice: number;
      filledPrice: number;
      quantity: number;
      status: 'filled' | 'cancelled';
      timestamp: Date;
    }
    ```
  - [x]1.4 Define `PAPER_MAX_ORDERS = 10_000` constant — maximum in-memory order retention before LRU eviction (prevents OOM in long-running paper sessions)

- [x] Task 2: Implement `FillSimulatorService` (AC: 4, 7)
  - [x]2.1 Create `src/connectors/paper/fill-simulator.service.ts` — **NOT** a NestJS `@Injectable()`. It's a plain class instantiated per `PaperTradingConnector` instance, NOT shared via DI. Each platform gets its own simulator with its own config and order map.
  - [x]2.2 Constructor takes `PaperTradingConfig`
  - [x]2.3 Implement `simulateFill(params: OrderParams): Promise<OrderResult>`:
    - Generate orderId via `crypto.randomUUID()` (Node built-in, no import needed)
    - Apply slippage: `filledPrice = params.price * (1 + slippageBps / 10000)` for buys, `* (1 - slippageBps / 10000)` for sells — **use `Decimal` for this calculation** (Gotcha #6)
    - Simulate latency: `await new Promise(resolve => setTimeout(resolve, fillLatencyMs))`
    - Store order in internal `Map<string, SimulatedOrder>`
    - Return `OrderResult` with `status: 'filled'`, `filledQuantity: params.quantity`, `filledPrice`, `timestamp: new Date()`
  - [x]2.4 Implement `getOrder(orderId: string): OrderStatusResult`:
    - Lookup in internal map → return status + fill data
    - Not found → return `{ orderId, status: 'not_found' }`
  - [x]2.5 Implement `cancelOrder(orderId: string): CancelResult`:
    - Lookup in internal map:
      - Not found → return `{ orderId, status: 'not_found' }`
      - Found with status `'filled'` → return `{ orderId, status: 'already_filled' }` (mirrors real platform behavior — cannot cancel a filled order)
      - Found with status `'cancelled'` → return `{ orderId, status: 'not_found' }` (already cancelled, treat as gone)
    - Note: In paper mode, orders fill instantly (after latency), so cancel will almost always return `'already_filled'`. This correctly simulates real platform behavior where fills happen faster than cancel requests.
  - [x]2.6 Implement `getOrderCount(): number` — returns size of internal order map (useful for testing/monitoring)
  - [x]2.7 Implement LRU eviction: when `orderMap.size >= PAPER_MAX_ORDERS`, delete the oldest entry (by insertion order — `Map` preserves insertion order, so `orderMap.keys().next().value` is the oldest). This prevents OOM in long-running paper sessions.
  - [x]2.8 Unit tests in `src/connectors/paper/fill-simulator.service.spec.ts`:
    - simulateFill returns valid OrderResult with correct platform/side/quantity
    - slippage applied correctly for buy (price increases) and sell (price decreases)
    - slippage uses Decimal math (no floating-point drift — verify with known precision-sensitive values like 0.1 + 0.2)
    - latency is simulated (use `vi.useFakeTimers()`)
    - getOrder returns stored order with fill data
    - getOrder returns not_found for unknown orderId
    - cancelOrder returns already_filled for filled order (mirrors real platform)
    - cancelOrder returns not_found for unknown orderId
    - getOrderCount tracks order map size
    - LRU eviction: inserting beyond PAPER_MAX_ORDERS evicts oldest entry

- [x] Task 3: Implement `PaperTradingConnector` (AC: 1, 2, 4, 5, 6, 8)
  - [x]3.1 Create `src/connectors/paper/paper-trading.connector.ts`
  - [x]3.2 Class implements `IPlatformConnector` — it is a plain class (NOT `@Injectable()`), instantiated by the factory in `ConnectorModule`
  - [x]3.3 Constructor takes `(realConnector: IPlatformConnector, config: PaperTradingConfig)`. Internally creates `FillSimulatorService` instance.
  - [x]3.4 **Data method delegation** — these 6 methods delegate directly to `this.realConnector`:
    - `getOrderBook(contractId)` → `this.realConnector.getOrderBook(contractId)`
    - `getFeeSchedule()` → `this.realConnector.getFeeSchedule()`
    - `getPlatformId()` → `this.realConnector.getPlatformId()`
    - `onOrderBookUpdate(callback)` → `this.realConnector.onOrderBookUpdate(callback)`
    - `getPositions()` → `this.realConnector.getPositions()`
    - `connect()` → `this.realConnector.connect()`
    - `disconnect()` → `this.realConnector.disconnect()`
  - [x]3.5 **Execution method interception** — these 3 methods route to `FillSimulatorService`:
    - `submitOrder(params)` → `this.fillSimulator.simulateFill(params)`
    - `cancelOrder(orderId)` → `this.fillSimulator.cancelOrder(orderId)`
    - `getOrder(orderId)` → `this.fillSimulator.getOrder(orderId)`
  - [x]3.6 **Health augmentation** — `getHealth()`:
    - Get real health: `const health = this.realConnector.getHealth()`
    - Return `{ ...health, mode: 'paper' as const }` — extending `PlatformHealth` to include optional `mode` field
  - [x]3.7 **IMPORTANT:** Add `mode?: 'paper' | 'live'` optional field to `PlatformHealth` interface in `src/common/types/platform.type.ts`. This is a backward-compatible addition (optional field). Default is `undefined` which means `live`.
  - [x]3.8 Unit tests in `src/connectors/paper/paper-trading.connector.spec.ts`:
    - Data methods delegate to real connector mock (verify each of 7 data methods)
    - Execution methods route to fill simulator (submitOrder, cancelOrder, getOrder)
    - getHealth returns real health with `mode: 'paper'` added
    - getPlatformId returns underlying platform's ID
    - Constructor creates its own FillSimulatorService
    - Two PaperTradingConnector instances (Kalshi + Polymarket) maintain independent order maps (per-platform isolation)

- [x] Task 4: Update `ConnectorModule` with conditional DI (AC: 1, 2, 3)
  - [x]4.1 Modify `src/connectors/connector.module.ts`:
    - Import `ConfigService` from `@nestjs/config`
    - Import `ConfigModule` in module imports (add alongside existing `forwardRef(() => DataIngestionModule)`)
    - Change `KALSHI_CONNECTOR_TOKEN` provider from `useExisting` to `useFactory`:
      ```typescript
      {
        provide: KALSHI_CONNECTOR_TOKEN,
        useFactory: (kalshi: KalshiConnector, config: ConfigService) => {
          const mode = config.get<string>('PLATFORM_MODE_KALSHI', 'live');
          if (mode === 'paper') {
            const fillLatencyMs = Number(config.get<string | number>('PAPER_FILL_LATENCY_MS_KALSHI', 150));
            const slippageBps = Number(config.get<string | number>('PAPER_SLIPPAGE_BPS_KALSHI', 5));
            return new PaperTradingConnector(kalshi, {
              platformId: PlatformId.KALSHI,
              fillLatencyMs,
              slippageBps,
            });
          }
          return kalshi;
        },
        inject: [KalshiConnector, ConfigService],
      },
      ```
    - Same pattern for `POLYMARKET_CONNECTOR_TOKEN` with Polymarket defaults (latency: 800, slippage: 15)
  - [x]4.2 **CRITICAL — Gotcha #3:** Wrap ALL numeric env reads in `Number()`. Validate with `Number.isNaN()` check — if NaN, throw `ConfigValidationError` with code `4001` and message including the env var name and invalid value: `throw new ConfigValidationError('Invalid PAPER_FILL_LATENCY_MS_KALSHI: expected number, got "abc"', 4001)`. Create a helper `validatePaperConfig(config: ConfigService, platformId: PlatformId): PaperTradingConfig` that validates and returns typed config.
  - [x]4.3 Keep exporting `KalshiConnector` and `PolymarketConnector` classes directly — `DataIngestionService` injects by class reference (NOT token), so class exports are required. This is correct: data ingestion always uses the real connector for real market data.
  - [x]4.4 **CONFIRMED (pre-verified):** `DataIngestionService` uses `private readonly kalshiConnector: KalshiConnector` (class injection, line 40). This is correct — data ingestion always gets the real connector. Only token consumers (`@Inject(KALSHI_CONNECTOR_TOKEN)`) get the paper wrapper. Token consumers are: `ExecutionService`, `SingleLegResolutionService`, `ExposureAlertSchedulerService`, `ExitMonitorService`, `StartupReconciliationService`.
  - [x]4.5 Unit tests — update `connector.module` tests (or create if none exist):
    - With `PLATFORM_MODE_KALSHI=paper`: token resolves to PaperTradingConnector instance
    - With `PLATFORM_MODE_KALSHI=live`: token resolves to KalshiConnector directly
    - With `PLATFORM_MODE_KALSHI` unset: defaults to live (KalshiConnector)
    - Same 3 tests for Polymarket

- [x] Task 5: Add env vars to `.env.example` and `.env.development` (AC: 7)
  - [x]5.1 Add to `.env.example`:
    ```
    # Paper Trading Mode (Story 5.5.1)
    PLATFORM_MODE_KALSHI=live              # Platform mode: live | paper (default: live)
    PLATFORM_MODE_POLYMARKET=live          # Platform mode: live | paper (default: live)
    PAPER_FILL_LATENCY_MS_KALSHI=150       # Simulated fill latency in ms (paper mode only)
    PAPER_SLIPPAGE_BPS_KALSHI=5            # Simulated slippage in basis points (paper mode only)
    PAPER_FILL_LATENCY_MS_POLYMARKET=800   # Simulated fill latency in ms (paper mode only, reflects on-chain)
    PAPER_SLIPPAGE_BPS_POLYMARKET=15       # Simulated slippage in basis points (paper mode only)
    ```
  - [x]5.2 Add same block to `.env.development` with `paper` mode enabled for both platforms (dev default = paper)

- [x] Task 6: Update mock factories for PlatformHealth mode field (AC: 8)
  - [x]6.1 In `src/test/mock-factories.ts`, update `createMockPlatformConnector` default `getHealth` mock to NOT include `mode` field (live connectors don't set it — `undefined` means live)
  - [x]6.2 No changes to `createMockRiskManager` or `createMockExecutionEngine`
  - [x]6.3 Verify all existing tests still pass — the `mode` field is optional, so adding it to `PlatformHealth` is backward-compatible

- [x] Task 7: Run lint + test suite (AC: all)
  - [x]7.1 Run `pnpm lint` — fix any issues
  - [x]7.2 Run `pnpm test` — all tests pass (existing + new)
  - [x]7.3 Verify test count increased (new paper connector + fill simulator tests)

## Dev Notes

### Decorator Pattern — NOT GoF Decorator, Just Wrapping

The `PaperTradingConnector` is a simple wrapper/proxy, not a complex decorator chain. It:

- Implements `IPlatformConnector` (same interface as the thing it wraps)
- Delegates data methods to the real connector (real market data)
- Intercepts execution methods with local simulation (no real orders)
- Is instantiated by a `useFactory` in `ConnectorModule`, not by DI container directly

This pattern was chosen over alternatives:

- **Strategy pattern:** Would require every consumer to know about modes — violates transparency
- **Module-level swap:** Would lose access to real market data in paper mode
- **Middleware/interceptor:** Wrong abstraction level — this is a connector concern

### DI Wiring — useFactory Pattern

The `ConnectorModule` currently uses `useExisting` to alias class to token:

```typescript
{ provide: KALSHI_CONNECTOR_TOKEN, useExisting: KalshiConnector }
```

This changes to `useFactory` which conditionally wraps:

```typescript
{
  provide: KALSHI_CONNECTOR_TOKEN,
  useFactory: (kalshi: KalshiConnector, config: ConfigService) => {
    const mode = config.get<string>('PLATFORM_MODE_KALSHI', 'live');
    if (mode === 'paper') {
      return new PaperTradingConnector(kalshi, { ... });
    }
    return kalshi;
  },
  inject: [KalshiConnector, ConfigService],
}
```

**Why `useFactory` over dynamic module:** The decision is per-platform and per-env-var. A `useFactory` is the simplest NestJS mechanism for this — the factory reads `ConfigService`, makes the decision, and returns the appropriate instance. No dynamic module registration needed.

**Why NOT `@Injectable()` on PaperTradingConnector/FillSimulatorService:** These are instantiated by the factory, not resolved by the DI container. Making them `@Injectable()` would require registering them as providers, which adds unnecessary complexity since they're only created when `mode === 'paper'`. The factory handles their lifecycle.

### Slippage Calculation

Slippage in basis points (bps): 1 bps = 0.01% = 0.0001 multiplier.

```typescript
// Buy order: price goes UP (worse for buyer)
const slippageMultiplier = new Decimal(1).plus(new Decimal(slippageBps).div(10000));
const filledPrice = new Decimal(params.price.toString()).mul(slippageMultiplier).toNumber();

// Sell order: price goes DOWN (worse for seller)
const slippageMultiplier = new Decimal(1).minus(new Decimal(slippageBps).div(10000));
const filledPrice = new Decimal(params.price.toString()).mul(slippageMultiplier).toNumber();
```

**MUST use `Decimal` for this** — Gotcha #6. Native `number * number` would introduce floating-point drift in price calculations.

### In-Memory Order Map

Paper orders are stored in a `Map<string, SimulatedOrder>` inside `FillSimulatorService`. This map:

- Lives for the lifetime of the process (no persistence)
- Is per-platform (each `PaperTradingConnector` has its own `FillSimulatorService` instance)
- Will be replaced with DB-backed storage in Story 5.5.2 (paper position state isolation)

### Config Validation — Gotcha #3

All numeric env reads MUST use `Number()` wrapper:

```typescript
const fillLatencyMs = Number(config.get<string | number>('PAPER_FILL_LATENCY_MS_KALSHI', 150));
if (Number.isNaN(fillLatencyMs)) {
  throw new ConfigValidationError('PAPER_FILL_LATENCY_MS_KALSHI must be a valid number');
}
```

`ConfigService.get<number>()` does NOT convert strings to numbers — it's a TypeScript-only hint.

### Interface Freeze Compliance

**Story 5.5.0 froze `IPlatformConnector` at 11 methods.** This story does NOT add new methods to the interface. The only change is adding an optional `mode?: 'paper' | 'live'` field to `PlatformHealth` return type — this is a backward-compatible type extension, not an interface method change.

### File Reference: Current ConnectorModule

```typescript
// src/connectors/connector.module.ts (current state)
@Module({
  imports: [forwardRef(() => DataIngestionModule)],
  providers: [
    KalshiConnector,
    PolymarketConnector,
    { provide: KALSHI_CONNECTOR_TOKEN, useExisting: KalshiConnector },
    { provide: POLYMARKET_CONNECTOR_TOKEN, useExisting: PolymarketConnector },
  ],
  exports: [KalshiConnector, PolymarketConnector, KALSHI_CONNECTOR_TOKEN, POLYMARKET_CONNECTOR_TOKEN],
})
export class ConnectorModule {}
```

### File Reference: IPlatformConnector (11 methods, frozen)

```
connect(), disconnect()           — lifecycle
getPlatformId(), getHealth()      — identity & monitoring
getOrderBook(), onOrderBookUpdate() — market data
submitOrder(), cancelOrder(), getOrder() — order management (INTERCEPTED in paper mode)
getPositions()                    — portfolio (stub)
getFeeSchedule()                  — fee info
```

### DoD Gates (from Epic 4.5 Retro, carried forward)

1. **Test isolation:** No shared mutable state — each PaperTradingConnector creates its own FillSimulatorService with fresh Map
2. **Interface preservation:** No breaking changes — `mode` field is optional on PlatformHealth
3. **Normalization ownership:** PaperTradingConnector delegates normalization-dependent methods (getOrderBook) to real connector

### Existing Error Patterns to Follow

- `ConfigValidationError` for invalid env config at startup (used in `engine-lifecycle.service.ts`)
- `PlatformApiError` codes 1000-1999 — NOT needed here since paper connector doesn't interact with real platform APIs for execution
- Paper connector errors should be descriptive but don't need error codes (they're local simulation errors)

### Previous Story Intelligence (5.5.0)

Key learnings from Story 5.5.0:

- Mock factories are centralized in `src/test/mock-factories.ts` — update `getHealth` mock default if PlatformHealth type changes
- `cancelOrder()` returns `CancelResult` with `status: 'cancelled' | 'not_found' | 'already_filled'` — paper mode only needs `'cancelled'` and `'not_found'`
- `getOrder()` returns `OrderStatusResult` — paper mode should return matching structure
- Interface freeze is in effect — all 11 methods accounted for in PaperTradingConnector
- Code review fixes from 5.5.0: Kalshi throws on unexpected cancel status, Polymarket tightened error matching — paper mode doesn't need these since it controls the responses

### LAD Design Review — Applied Fixes

Review performed by LAD MCP (kimi-k2-thinking). 10 findings analyzed, 5 incorporated:

1. **Cancel semantics (M):** Updated AC5 and Task 2.5 — `cancelOrder` on a filled paper order now returns `'already_filled'` instead of `'cancelled'`, correctly mirroring real platform behavior.
2. **Memory leak (M):** Added `PAPER_MAX_ORDERS` constant (10,000) and LRU eviction in Task 2.7 to prevent OOM in long-running paper sessions.
3. **Config validation error code (M):** Reuses existing `ConfigValidationError` (code `4010`) and added `validatePaperConfig()` helper function specification in Task 4.2.
4. **Per-platform isolation test (L):** Added test case in Task 3.8 verifying two PaperTradingConnector instances maintain independent order maps.
5. **DataIngestionModule verification (H):** Pre-verified and documented in Task 4.4 — confirmed class injection (correct behavior: data ingestion always uses real connector).

**Dismissed findings:**

- ConfigModule import "violation" — `@nestjs/config` is a framework module, not a business module. ConnectorModule already imports `DataIngestionModule`.
- PlatformHealth.mode required — would force changes in all real connectors + mocks for no MVP benefit. Optional `undefined=live` is sufficient.
- Event emission for paper trades — events are emitted by calling modules (ExecutionService), not by connectors. Paper connector returns standard `OrderResult`, so events fire naturally. Tagging is Story 5.5.3 scope.
- Remove class exports — class exports required because DataIngestionService injects by class reference.
- Slippage `.toNumber()` — `OrderResult.filledPrice` is typed as `number`. Intermediate calc uses Decimal, final conversion to `number` is at the boundary (correct pattern per project convention).

### Project Structure Notes

**New files:**

- `src/connectors/paper/paper-trading.connector.ts` — IPlatformConnector decorator
- `src/connectors/paper/paper-trading.connector.spec.ts` — connector unit tests
- `src/connectors/paper/fill-simulator.service.ts` — simulated fill generation
- `src/connectors/paper/fill-simulator.service.spec.ts` — simulator unit tests
- `src/connectors/paper/paper-trading.types.ts` — PaperTradingConfig, SimulatedOrder

**Modified files:**

- `src/connectors/connector.module.ts` — useFactory conditional wrapping
- `src/common/types/platform.type.ts` — add optional `mode` to PlatformHealth
- `src/test/mock-factories.ts` — verify getHealth mock compatibility
- `.env.example` — add paper trading env vars
- `.env.development` — add paper trading env vars (default: paper mode)

**Alignment with architecture doc:**

- Architecture specifies `src/connectors/paper/` directory — matches exactly
- Architecture specifies `paper-trading.connector.ts`, `fill-simulator.service.ts`, `paper-trading.types.ts` — matches exactly
- Architecture specifies per-platform env vars with exact names — matches exactly

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Environment Configuration — Paper Trading Configuration]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure — connectors/paper/]
- [Source: _bmad-output/implementation-artifacts/5-5-0-interface-stabilization-test-infrastructure.md — Interface Freeze, Mock Factories, cancelOrder]
- [Source: pm-arbitrage-engine/src/common/interfaces/platform-connector.interface.ts — IPlatformConnector (11 methods)]
- [Source: pm-arbitrage-engine/src/common/types/platform.type.ts — PlatformId, OrderParams, OrderResult, CancelResult, OrderStatusResult, PlatformHealth]
- [Source: pm-arbitrage-engine/src/connectors/connector.module.ts — Current DI registration]
- [Source: pm-arbitrage-engine/src/connectors/connector.constants.ts — KALSHI_CONNECTOR_TOKEN, POLYMARKET_CONNECTOR_TOKEN]
- [Source: pm-arbitrage-engine/src/test/mock-factories.ts — createMockPlatformConnector]
- [Source: pm-arbitrage-engine/docs/gotchas.md#3 — ConfigService returns strings]
- [Source: pm-arbitrage-engine/docs/gotchas.md#6 — Decimal precision for financial math]
- [Source: CLAUDE.md#Architecture, #Error Handling, #Naming Conventions, #Testing, #Domain Rules]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A

### Completion Notes List

- All 7 tasks + subtasks implemented per story spec
- `ConfigValidationError` used with existing constructor signature `(message, validationErrors[])` instead of story's `(message, code)` — existing codebase pattern, code hardcoded at 4010
- `mode` field added as optional to `PlatformHealth` — backward-compatible, `undefined` = live
- Mock factories unchanged — no `mode` field means live (correct)
- Pre-existing flaky property test (`financial-math.property.spec.ts`) occasionally fails with non-deterministic seed — not related to this story
- 32 new tests (760 → 792), 3 new spec files, 57 total test files all passing
- Lint clean

### Code Review Fixes (2026-02-22)

- **M1:** Fixed `.env.example` comment collision — restored `OPERATOR_API_TOKEN` comment, removed mangled trailing fragment
- **M2:** Corrected LAD review section — error code is `4010` (existing `ConfigValidationError`), not `4001`
- **M3:** Added `validatePlatformMode()` — rejects invalid mode values (e.g., typos) with `ConfigValidationError` instead of silently falling through to live
- +1 test for invalid mode validation (792 → 793 tests)

### File List

**New files:**

- `src/connectors/paper/paper-trading.types.ts`
- `src/connectors/paper/fill-simulator.service.ts`
- `src/connectors/paper/fill-simulator.service.spec.ts`
- `src/connectors/paper/paper-trading.connector.ts`
- `src/connectors/paper/paper-trading.connector.spec.ts`
- `src/connectors/connector.module.spec.ts`

**Modified files:**

- `src/connectors/connector.module.ts`
- `src/common/types/platform.type.ts`
- `.env.example`
- `.env.development`
