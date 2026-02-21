# Story 5.2: Single-Leg Exposure Detection & Alerting

Status: done

## Story

As an operator,
I want the system to detect when only one leg fills and immediately alert me with full context,
So that I can make an informed decision about the exposed position.

## Out of Scope

- **Single-leg resolution** (retry/close endpoints) — Story 5.3 owns operator actions (`POST /api/positions/:id/retry-leg`, `POST /api/positions/:id/close-leg`).
- **Exit monitoring** — Story 5.4.
- **Startup reconciliation** — Story 5.5.
- **Automatic single-leg management** (auto-close/hedge) — Epic 10, Story 10.3 (FR-EX-07).
- **Recurring alert re-emission every 60 seconds** — Story 5.3 owns the "continue emitting every 60s until resolved" behavior, as it's tied to the resolution workflow.

## Acceptance Criteria

1. **Given** the primary leg has filled
   **When** the secondary leg submission fails (rejected, pending after Polymarket's 5s poll timeout, or depth insufficient)
   **Then** single-leg exposure is detected immediately within the execution flow (detection is synchronous — Story 5.1's `handleSingleLeg()` is called inline, not via a separate timer)
   **And** a `SingleLegExposureEvent` (critical severity) is emitted with: filled leg details (platform, side, price, size, fillPrice, fillSize), failed leg details (platform, reason, reasonCode, attemptedPrice, attemptedSize), current prices on both platforms, estimated P&L scenarios (close now, retry at current price, hold), and recommended actions (FR-EX-04 satisfied: the 5s timeout is enforced by Polymarket's poll timeout in Story 5.1; FR-EX-05 satisfied: full context alert)

2. **Given** the position status is `SINGLE_LEG_EXPOSED` (precondition: set by Story 5.1's `handleSingleLeg()`)
   **When** the `SingleLegExposureEvent` is emitted
   **Then** the event payload includes P&L scenarios (closeNow, retryAtCurrentPrice, holdRiskAssessment) and recommended operator actions
   **And** the `ExecutionError` (code 2004, critical severity) log entry includes the P&L scenarios and recommended actions alongside the existing position/pair context

3. **Given** single-leg exposure events accumulate
   **When** the monthly count exceeds 5
   **Then** a warning event is emitted: "Single-leg exposure count ({count}) exceeds monthly threshold (5). Systematic investigation recommended." (NFR-R3: <5 events/month target, <2/month compliance)

4. **Given** single-leg exposure events accumulate on a weekly basis
   **When** more than 1 event occurs per week for 3+ consecutive weeks
   **Then** a critical warning event is emitted: "Sustained weekly single-leg exposure ({count}/week for {weeks} consecutive weeks). Systematic root cause investigation required." (NFR-R3 compliance rule)

## Tasks / Subtasks

- [x] Task 1: Create `SingleLegExposureEvent` class (AC: 1)
  - [x] 1.1 Create event class in `common/events/execution.events.ts` extending `BaseEvent`
  - [x] 1.2 Payload: filledLeg (platform, orderId, side, price, size, fillPrice, fillSize), failedLeg (platform, reason, reasonCode, attemptedPrice, attemptedSize), currentPrices ({kalshi: {bid, ask}, polymarket: {bid, ask}}), pnlScenarios (closeNow, retryAtCurrentPrice, hold), recommendedActions (string[]), positionId, pairId, expectedEdge
  - [x] 1.3 Verify event uses `EVENT_NAMES.SINGLE_LEG_EXPOSURE` ('execution.single_leg.exposure')

- [x] Task 2: Create P&L scenario calculator (AC: 1)
  - [x] 2.1 Create `single-leg-pnl.util.ts` in `common/utils/` or within execution module
  - [x] 2.2 Implement `calculateSingleLegPnlScenarios()`: takes filled leg details + current order books → returns {closeNow: Decimal, retryAtCurrentPrice: Decimal, hold: string}
  - [x] 2.3 "Close now" = cost to unwind filled leg at current market (opposing trade on same platform, using best bid/ask)
  - [x] 2.4 "Retry at current price" = expected edge if secondary fills at current market price minus fees
  - [x] 2.5 "Hold" = risk assessment description (exposure amount, time sensitivity)
  - [x] 2.6 Use `Decimal` (decimal.js) for all calculations
  - [x] 2.7 Unit tests for P&L scenarios with various market conditions

- [x] Task 3: Emit `SingleLegExposureEvent` from `ExecutionService` (AC: 1, 2)
  - [x] 3.1 Update `handleSingleLeg()` in `execution.service.ts` to fetch current order books from both connectors
  - [x] 3.2 Call P&L scenario calculator with filled leg + current books
  - [x] 3.3 Build recommended actions list based on scenarios (e.g., "Retry secondary at current ask", "Close filled leg to limit loss to $X")
  - [x] 3.4 Emit `SingleLegExposureEvent` via EventEmitter2
  - [x] 3.5 Ensure event emission is non-blocking (async fan-out path — never delay execution cycle)

- [x] Task 4: Exposure count tracking — monthly and weekly (AC: 3, 4)
  - [x] 4.1 Create `ExposureTrackerService` in execution module that tracks single-leg events per calendar month AND per ISO week
  - [x] 4.2 On each `SingleLegExposureEvent`, increment both monthly counter and weekly counter
  - [x] 4.3 Monthly threshold: when count exceeds 5, emit warning event (AC: 3)
  - [x] 4.4 Weekly threshold: track consecutive weeks with >1 event; when 3+ consecutive weeks breached, emit critical warning event (AC: 4)
  - [x] 4.5 Counters reset at start of each calendar month (UTC) and ISO week respectively
  - [x] 4.6 In-memory tracking is acceptable (rebuilt from position history on restart if needed)
  - [x] 4.7 Unit tests for monthly threshold, weekly consecutive threshold, resets, and rebuild-from-DB

- [x] Task 5: Tests (all ACs)
  - [x] 5.1 Unit tests for `SingleLegExposureEvent` construction and payload validation
  - [x] 5.2 Unit tests for P&L scenario calculator: profitable retry, unprofitable close, edge cases (empty book, zero liquidity)
  - [x] 5.3 Unit tests for `ExecutionService.handleSingleLeg()`: verifies event emission with correct payload
  - [x] 5.4 Unit tests for exposure tracker: monthly increment/threshold, weekly consecutive tracking, resets, rebuild-from-DB
  - [x] 5.5 Integration: verify `handleSingleLeg()` → `SingleLegExposureEvent` emission end-to-end
  - [x] 5.6 All existing tests continue to pass (542+ baseline from Story 5.1)

## Dev Notes

### Architecture Constraints

- **Intentional deviation from architecture spec:** The architecture spec references `leg-manager.service.ts` for "Single-leg detection, retry/unwind logic." For MVP, detection and event emission are co-located in `ExecutionService.handleSingleLeg()` (established by Story 5.1). This is simpler — `handleSingleLeg()` already has all the context needed (filled order, connectors, pair config). Story 5.3 may introduce `leg-manager.service.ts` for resolution logic (retry/close endpoints), or it may be deferred to Epic 10 refactoring when auto-management is added. **Do NOT create `leg-manager.service.ts` in this story.**
- **Hot path is synchronous and blocking:** Detection → Risk validation → Execution. The `handleSingleLeg()` method runs inline within `ExecutionService.execute()`. Any order book fetches for P&L scenarios must be fast but tolerate failure (fallback to "prices unavailable" rather than crashing the execution flow).
- **Fan-out is async:** The `SingleLegExposureEvent` emission is on the EventEmitter2 async path. Downstream consumers (future Telegram alerts in Epic 6, monitoring hub) subscribe to this event. Event emission must NEVER delay the execution return.
- **Module dependency rules:**
  - `modules/execution/` → `connectors/` (fetches current order books for P&L) + `modules/risk-management/` (budget reservation) — ALLOWED
  - `connectors/` NEVER imports from `modules/` — FORBIDDEN
  - All cross-module communication through interfaces in `common/interfaces/`

### What Story 5.1 Already Provides (DO NOT DUPLICATE)

**`ExecutionService.handleSingleLeg()` (execution.service.ts) already:**
1. Creates `OpenPosition` with status `SINGLE_LEG_EXPOSED`
2. Persists the filled primary order to `orders` table
3. Emits `OrderFilledEvent` for the filled primary leg only
4. Logs warning with position ID, pair ID, error code
5. Returns `ExecutionResult { success: false, partialFill: true, positionId, error: ExecutionError(2004) }`

**This story ADDS to `handleSingleLeg()`:**
1. Fetch current order books from both connectors (for P&L scenarios)
2. Calculate P&L scenarios (close now, retry, hold)
3. Build recommended actions list
4. Emit `SingleLegExposureEvent` with full context payload

**Do NOT restructure the existing `handleSingleLeg()` flow.** Add the new logic AFTER the position is created and primary order is persisted, BEFORE the return statement.

### SingleLegExposureEvent Design

```typescript
class SingleLegExposureEvent extends BaseEvent {
  constructor(
    public readonly positionId: string,
    public readonly pairId: string,
    public readonly expectedEdge: number,
    public readonly filledLeg: {
      platform: PlatformId;
      orderId: string;
      side: string;
      price: number;
      size: number;
      fillPrice: number;
      fillSize: number;
    },
    public readonly failedLeg: {
      platform: PlatformId;
      reason: string;
      reasonCode: number;
      attemptedPrice: number;
      attemptedSize: number;
    },
    public readonly currentPrices: {
      kalshi: { bestBid: number | null; bestAsk: number | null };
      polymarket: { bestBid: number | null; bestAsk: number | null };
    },
    public readonly pnlScenarios: {
      closeNowEstimate: string;   // Decimal string: loss/gain if unwinding filled leg now
      retryAtCurrentPrice: string; // Decimal string: edge if secondary fills at current price
      holdRiskAssessment: string;  // Human-readable risk description
    },
    public readonly recommendedActions: string[],
    correlationId?: string,
  ) {
    super(correlationId);
  }
}
```

### P&L Scenario Calculation Logic

**Close Now Estimate:**
- Filled leg was a BUY → unwind by selling at best bid on same platform
- Filled leg was a SELL → unwind by buying at best ask on same platform
- P&L = (unwindPrice - fillPrice) × fillSize (negative = loss)
- Account for taker fees on the unwind trade
- If order book is empty/unavailable → return "UNAVAILABLE" string

**Retry at Current Price:**
- Secondary leg failed → get current best price on secondary platform for the intended side
- Calculate net edge: |filledPrice - secondaryCurrentPrice| - fees - gas
- If positive → "Retry would yield ~X% edge"
- If negative → "Retry at current price would result in ~X% loss"
- If unavailable → "UNAVAILABLE"

**Hold Risk Assessment (exact format — not a suggestion, this IS the output):**
- Template: `"EXPOSED: ${exposureUsd} on {platform} ({side} {size}@{fillPrice}). No hedge. Immediate operator action recommended."`
- `exposureUsd` = fillPrice × fillSize (capital at risk on one platform), formatted to 2 decimal places
- If order books unavailable, append: `" Current market prices unavailable — risk assessment may be stale."`

**Recommended Actions (ordered by preference):**
1. If retryEdge > 0: "Retry secondary leg at current {side} price ({price}) — estimated {edge}% edge"
2. If closeNowLoss < retryLoss: "Close filled leg on {platform} — estimated loss ${amount}"
3. Always: "Monitor position via `GET /api/positions/{id}` — Story 5.3 will add retry/close endpoints"

### Exposure Count Tracking (Monthly + Weekly)

**ExposureTrackerService** — injectable NestJS service in execution module:
- Subscribes to `EVENT_NAMES.SINGLE_LEG_EXPOSURE` via `@OnEvent` decorator
- **Monthly tracking:** `Map<string, number>` keyed by `YYYY-MM`. If count > 5 → emit warning event.
- **Weekly tracking:** `Map<string, number>` keyed by ISO week `YYYY-Wnn`. Track consecutive weeks with count > 1. If 3+ consecutive weeks breached → emit critical warning event.
- Consecutive week logic: maintain `consecutiveBreachedWeeks: number` counter. On each event, check if current ISO week has >1 event. At week boundary (first event of new week), evaluate if previous week was breached; if yes, increment `consecutiveBreachedWeeks`; if no, reset to 0. **Edge case:** A week with zero events that passes silently does NOT increment or reset the counter — the counter is only evaluated on event arrival. This is correct: no events = no tracking needed, and the next event in a future week will evaluate the gap.
- On startup: query `PositionRepository.findByStatus('SINGLE_LEG_EXPOSED')` with `createdAt` in current month/week to rebuild counters (resilience to restart)

**Note:** Do NOT add a new Prisma migration for this. In-memory tracking with startup rebuild is sufficient for MVP.

### Existing Code Integration Points

**Files to MODIFY:**
- `src/modules/execution/execution.service.ts` — Add order book fetch + P&L calc + event emission to `handleSingleLeg()`
- `src/common/events/execution.events.ts` — Add `SingleLegExposureEvent` class
- `src/modules/execution/execution.module.ts` — Register `ExposureTrackerService` as provider

**Files to CREATE:**
- `src/modules/execution/single-leg-pnl.util.ts` — P&L scenario calculator utility
- `src/modules/execution/single-leg-pnl.util.spec.ts` — Tests for P&L calculator
- `src/modules/execution/exposure-tracker.service.ts` — Monthly count tracker
- `src/modules/execution/exposure-tracker.service.spec.ts` — Tests for tracker

**Files to READ (context only, no changes):**
- `src/common/events/base.event.ts` — BaseEvent class to extend
- `src/common/events/event-catalog.ts` — EVENT_NAMES.SINGLE_LEG_EXPOSURE already defined
- `src/common/types/platform.type.ts` — PlatformId, OrderResult, FeeSchedule types
- `src/common/types/normalized-order-book.type.ts` — NormalizedOrderBook, PriceLevel types
- `src/connectors/connector.constants.ts` — KALSHI_CONNECTOR_TOKEN, POLYMARKET_CONNECTOR_TOKEN
- `src/persistence/repositories/position.repository.ts` — findByStatus() for monthly count rebuild

### handleSingleLeg() Modification Pattern

The existing `handleSingleLeg()` method has 15 parameters. **Do NOT add more parameters.** Instead:
1. The connectors are already available as `this.kalshiConnector` and `this.polymarketConnector` (class members)
2. Fetch order books inside `handleSingleLeg()` using the connectors directly
3. Wrap order book fetches in try/catch — if a platform is degraded, use null for prices

```typescript
// Add AFTER position creation, BEFORE the return statement in handleSingleLeg():

// Fetch current order books for P&L scenarios with 2s timeout per fetch.
// These fetches ADD latency to the execution return path — cap total at ~2s.
// If platforms are slow/degraded, fall back to null prices rather than blocking.
const ORDERBOOK_FETCH_TIMEOUT_MS = 2000;
const withTimeout = <T>(promise: Promise<T>, ms: number): Promise<T | null> =>
  Promise.race([promise, new Promise<null>((resolve) => setTimeout(() => resolve(null), ms))]);

const [kalshiBook, polymarketBook] = await Promise.all([
  withTimeout(this.kalshiConnector.getOrderBook(dislocation.pairConfig.kalshiContractId), ORDERBOOK_FETCH_TIMEOUT_MS).catch(() => null),
  withTimeout(this.polymarketConnector.getOrderBook(dislocation.pairConfig.polymarketContractId), ORDERBOOK_FETCH_TIMEOUT_MS).catch(() => null),
]);

const currentPrices = {
  kalshi: kalshiBook
    ? { bestBid: kalshiBook.bids[0]?.price ?? null, bestAsk: kalshiBook.asks[0]?.price ?? null }
    : { bestBid: null, bestAsk: null },
  polymarket: polymarketBook
    ? { bestBid: polymarketBook.bids[0]?.price ?? null, bestAsk: polymarketBook.asks[0]?.price ?? null }
    : { bestBid: null, bestAsk: null },
};

const pnlScenarios = calculateSingleLegPnlScenarios({
  filledPlatform: primaryPlatform,
  filledSide: primarySide,
  fillPrice: primaryOrder.filledPrice,
  fillSize: primaryOrder.filledQuantity,
  currentPrices,
  secondaryPlatform: secondaryPlatform,
  secondarySide: secondarySide,
  fees: { /* from connectors' getFeeSchedule() */ },
});

const recommendedActions = buildRecommendedActions(pnlScenarios, position.positionId);

this.eventEmitter.emit(
  EVENT_NAMES.SINGLE_LEG_EXPOSURE,
  new SingleLegExposureEvent(
    position.positionId, pairId, enriched.netEdge.toNumber(),
    { /* filled leg details */ },
    { /* failed leg details */ },
    currentPrices, pnlScenarios, recommendedActions,
  ),
);
```

### Price Normalization Reminder

- Internal prices: decimal probability 0.00–1.00
- Kalshi API: cents (÷100 for internal, ×100 for submission)
- Polymarket: already decimal, no conversion needed
- `getOrderBook()` returns already-normalized prices (both connectors handle normalization internally)
- P&L calculations use decimal probability — the `Decimal` library for all math

### Fee Schedule Access

Both connectors expose `getFeeSchedule()` returning `FeeSchedule` (defined in `src/common/types/platform.type.ts`). **IMPORTANT:** `makerFeePercent` and `takerFeePercent` use a 0-100 percentage scale (e.g., `2.0` means 2% fee), NOT decimal scale. For P&L math, convert: `takerFeeDecimal = feeSchedule.takerFeePercent / 100`. The P&L calculator should accept fee rates as decimal parameters (0.00–1.00 scale) rather than importing connectors directly — the caller converts before passing.

### DoD Gates (from Epic 4.5 Retro Action Items)

1. **Test isolation** — all new tests must mock platform API calls, no live HTTP
2. **Interface preservation** — do not rename existing interface methods; add new ones alongside if needed
3. **Normalization ownership** — order books from `getOrderBook()` are already normalized

### Project Structure Notes

- New files go in `src/modules/execution/` (P&L util, exposure tracker)
- Event class added to existing `src/common/events/execution.events.ts`
- Co-located tests: `single-leg-pnl.util.spec.ts` next to `single-leg-pnl.util.ts`
- No new Prisma migration needed
- No new module imports needed (connectors already available via DI)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5, Story 5.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Execution Module]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error Handling]
- [Source: _bmad-output/planning-artifacts/architecture.md#Event Emission]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]
- [Source: _bmad-output/implementation-artifacts/5-1-order-submission-position-tracking.md#Dev Notes]
- [Source: CLAUDE.md#Architecture, #Error Handling, #Event Emission, #Domain Rules]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean implementation, no blocking issues.

### Completion Notes List

- **Task 1:** Created `SingleLegExposureEvent` class in `execution.events.ts` extending `BaseEvent`. Full payload: filledLeg, failedLeg, currentPrices, pnlScenarios, recommendedActions, positionId, pairId, expectedEdge. Uses `EVENT_NAMES.SINGLE_LEG_EXPOSURE`.
- **Task 2:** Created `single-leg-pnl.util.ts` in execution module with `calculateSingleLegPnlScenarios()` and `buildRecommendedActions()`. All math via `decimal.js`. Close-now, retry, and hold scenarios implemented per spec. 12 unit tests.
- **Task 3:** Modified `handleSingleLeg()` in `execution.service.ts`: fetches current order books with 2s timeout per platform, calculates P&L scenarios, builds recommended actions, emits `SingleLegExposureEvent`. Graceful fallback to null prices on API failure. Event emission via `eventEmitter.emit()` (async fan-out, non-blocking). 2 new integration tests.
- **Task 4:** Created `ExposureTrackerService` with `@OnEvent` subscriber. Monthly threshold (>5 → warning via `LIMIT_APPROACHED`), weekly consecutive threshold (3+ weeks with >1 → critical via `LIMIT_BREACHED`). In-memory maps keyed by `YYYY-MM` and `YYYY-Wnn`. Startup rebuild from `PositionRepository.findByStatus('SINGLE_LEG_EXPOSED')`. Registered in `ExecutionModule`. 7 unit tests.
- **Task 5:** 26 new tests total across 4 test files. All 568 tests pass (baseline was 542+). Lint clean.
- **Code Review Fixes (2026-02-19):** 4 issues fixed — (H1) Added pnlScenarios and recommendedActions to ExecutionError metadata for AC 2 compliance; (M1) Fixed buildRecommendedActions close condition to trigger when retry is not profitable, not just on explicit loss; (M2) rebuildFromDb now rebuilds consecutiveBreachedWeeks by walking back through weekly position history; (M3) Added end-to-end weekly consecutive test using vi.setSystemTime across 3 week boundaries. 4 new tests added, 572 total passing.

### Change Log

- 2026-02-19: Story 5.2 implementation complete — SingleLegExposureEvent, P&L calculator, event emission, exposure tracking (monthly + weekly)
- 2026-02-19: Code review fixes — AC 2 ExecutionError metadata, buildRecommendedActions condition, rebuildFromDb consecutive weeks, e2e weekly test

### File List

**New files:**
- `pm-arbitrage-engine/src/modules/execution/single-leg-pnl.util.ts`
- `pm-arbitrage-engine/src/modules/execution/single-leg-pnl.util.spec.ts`
- `pm-arbitrage-engine/src/modules/execution/exposure-tracker.service.ts`
- `pm-arbitrage-engine/src/modules/execution/exposure-tracker.service.spec.ts`
- `pm-arbitrage-engine/src/common/events/execution.events.spec.ts`

**Modified files:**
- `pm-arbitrage-engine/src/common/events/execution.events.ts` — Added `SingleLegExposureEvent` class
- `pm-arbitrage-engine/src/modules/execution/execution.service.ts` — Added order book fetch, P&L calc, event emission to `handleSingleLeg()`; added pnlScenarios/recommendedActions to ExecutionError metadata
- `pm-arbitrage-engine/src/modules/execution/execution.service.spec.ts` — Added `getFeeSchedule` to mocks, 3 new tests for `SingleLegExposureEvent` emission and error metadata
- `pm-arbitrage-engine/src/modules/execution/execution.module.ts` — Registered `ExposureTrackerService`
