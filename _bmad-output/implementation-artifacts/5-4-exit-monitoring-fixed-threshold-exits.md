# Story 5.4: Exit Monitoring & Fixed Threshold Exits

Status: done

## Story

As an operator,
I want open positions continuously monitored and automatically closed when exit thresholds are hit,
So that profits are captured and losses are limited without manual intervention.

## Out of Scope

- **Model-driven exits** (continuous edge recalculation, 5-criteria exit logic) — FR-EM-02, FR-EM-03, Phase 1 (Epic 10, Stories 10.1/10.2). This story implements fixed thresholds only.
- **Automatic single-leg management** (auto-close/hedge on partial exit) — FR-EX-07, Phase 1 (Epic 10, Story 10.3). Partial exits reuse the manual resolution workflow from Story 5.3.
- **Telegram alert integration** — Epic 6, Story 6.1. Events are emitted; Telegram consumption is a future subscriber.
- **Dashboard UI** — Epic 7. No frontend in this story.
- **Startup reconciliation of exit state** — Story 5.5. If the engine crashes mid-exit, reconciliation handles it.

## Acceptance Criteria

1. **Given** a position is in `OPEN` state
   **When** the exit monitor evaluates it during each polling cycle
   **Then** current edge is recalculated using live order book prices from both platforms
   **And** the three fixed thresholds are evaluated in priority order: stop-loss (highest priority), take-profit, time-based

2. **Given** the current captured edge reaches 80% of initial edge
   **When** the take-profit threshold is hit
   **Then** exit orders are submitted to both platforms to reverse each leg on its respective platform (sell what was bought, buy what was sold)
   **And** an `ExitTriggeredEvent` is emitted with exit type `take_profit`, realized P&L, and initial vs. final edge

3. **Given** the current loss reaches 2x the initial edge
   **When** the stop-loss threshold is hit
   **Then** exit orders are submitted immediately (reversing each leg on its platform)
   **And** an `ExitTriggeredEvent` is emitted with exit type `stop_loss` and loss details

4. **Given** a position is within 48 hours of contract resolution
   **When** the time-based threshold is hit
   **Then** exit orders are submitted (reversing each leg on its platform)
   **And** an `ExitTriggeredEvent` is emitted with exit type `time_based` and remaining edge

5. **Given** an exit order fills on both platforms
   **When** the position is fully closed
   **Then** the position transitions to `CLOSED` with complete P&L record
   **And** daily P&L in risk budget is updated via `riskManager.closePosition()`
   **And** the position count is decremented, freeing capacity for new trades

6. **Given** an exit order fails to fill on one platform
   **When** a partial exit occurs
   **Then** the position transitions to `EXIT_PARTIAL`
   **And** a `SingleLegExposureEvent` is emitted, reusing the same detection and resolution workflow from Stories 5.2/5.3
   **And** the operator can resolve via the same retry-leg or close-leg endpoints

7. **Given** either platform connector is in `disconnected` health state
   **When** the exit monitor evaluates positions involving that platform
   **Then** evaluation is skipped for those positions (stale order book data would produce unreliable threshold calculations)
   **And** a warning is logged with the skipped position count

## Tasks / Subtasks

- [x] Task 1: Add `resolutionDate` to ContractMatch schema (AC: 4)
  - [x] 1.1 Add `resolutionDate DateTime? @map("resolution_date") @db.Timestamptz` to the `ContractMatch` model in `prisma/schema.prisma`
  - [x] 1.2 Create Prisma migration: `pnpm prisma migrate dev --name add-resolution-date-to-contract-match`
  - [x] 1.3 Run `pnpm prisma generate` to regenerate the client

- [x] Task 2: Create `ExitTriggeredEvent` class (AC: 2, 3, 4)
  - [x] 2.1 Add `ExitTriggeredEvent` to `src/common/events/execution.events.ts` extending `BaseEvent`
  - [x] 2.2 Payload: `positionId`, `pairId`, `exitType` (`'take_profit' | 'stop_loss' | 'time_based'`), `initialEdge` (Decimal string), `finalEdge` (Decimal string), `realizedPnl` (Decimal string), `kalshiCloseOrderId`, `polymarketCloseOrderId`
  - [x] 2.3 Update `EVENT_NAMES.EXIT_TRIGGERED` comment from placeholder to implemented: `'execution.exit.triggered'` (already registered)
  - [x] 2.4 Unit test for event construction in `execution.events.spec.ts`

- [x] Task 3: Create `ExitManagementModule` scaffolding (AC: all)
  - [x] 3.1 Create `src/modules/exit-management/exit-management.module.ts`
  - [x] 3.2 Import: `ConnectorModule`, `RiskManagementModule` (for `RISK_MANAGER_TOKEN`), connector tokens via `ConnectorModule`
  - [x] 3.3 Export: `ExitMonitorService` (for core trading engine to invoke if needed)

- [x] Task 4: Create `ThresholdEvaluatorService` (AC: 1, 2, 3, 4)
  - [x] 4.1 Create `src/modules/exit-management/threshold-evaluator.service.ts`
  - [x] 4.2 Pure evaluation logic — no side effects, no DB access, no connector calls. Takes position data + current prices → returns threshold result
  - [x] 4.3 Implement `evaluate(params: ThresholdEvalInput): ThresholdEvalResult`
  - [x] 4.4 Return includes `currentEdge`, `currentPnl`, `capturedEdgePercent` for logging/events
  - [x] 4.5 All math uses `Decimal` (decimal.js) — no floating point

- [x] Task 5: Create `ExitMonitorService` (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] 5.1 Create `src/modules/exit-management/exit-monitor.service.ts`
  - [x] 5.2 Inject: `PositionRepository`, `OrderRepository`, Kalshi and Polymarket connectors (via `KALSHI_CONNECTOR_TOKEN` / `POLYMARKET_CONNECTOR_TOKEN`), `EventEmitter2`, `IRiskManager` (via `RISK_MANAGER_TOKEN`), `ThresholdEvaluatorService`, `Logger`
  - [x] 5.3 Implement `evaluatePositions(): Promise<void>` — the main polling entry point
  - [x] 5.4 Implement `executeExit(position, evalResult): Promise<void>`
  - [x] 5.5 Implement `getClosePrice(connector, contractId, originalSide): Promise<Decimal | null>`
  - [x] 5.6 Use `@Interval(30000)` from `@nestjs/schedule` for polling (30-second cycle)
  - [x] 5.7 Add circuit breaker: if 3 consecutive evaluation cycles fail entirely, skip exactly 1 cycle

- [x] Task 6: Add `PositionRepository.findByStatusWithOrders()` method (AC: 5)
  - [x] 6.1 Add `findByStatusWithOrders(status)` with `{ pair: true, kalshiOrder: true, polymarketOrder: true }` include
  - [x] 6.2 Add JSDoc explaining the use case (exit monitor needs entry fill prices for P&L)

- [x] Task 7: Update `SingleLegResolutionService` and `ExposureAlertScheduler` for `EXIT_PARTIAL` (AC: 6)
  - [x] 7.1 In `SingleLegResolutionService.retryLeg()`: accept BOTH `SINGLE_LEG_EXPOSED` AND `EXIT_PARTIAL`
  - [x] 7.2 In `SingleLegResolutionService.closeLeg()`: same update — accept both statuses
  - [x] 7.3 In `ExposureAlertScheduler`: query for `{ in: ['SINGLE_LEG_EXPOSED', 'EXIT_PARTIAL'] }`
  - [x] 7.4 Add unit tests for EXIT_PARTIAL acceptance in `single-leg-resolution.service.spec.ts`
  - [x] 7.5 Add unit test in `exposure-alert-scheduler.service.spec.ts` confirming EXIT_PARTIAL positions included

- [x] Task 8: Add error code for partial exit (AC: 6)
  - [x] 8.1 Add `PARTIAL_EXIT_FAILURE: 2008` to execution error codes in `src/common/errors/execution-error.ts`

- [x] Task 9: Register module in AppModule (AC: all)
  - [x] 9.1 Add `ExitManagementModule` to imports in `src/app.module.ts`
  - [x] 9.2 `ScheduleModule.forRoot()` already imported in `AppModule`

- [x] Task 10: Extract connector tokens to shared `ConnectorModule` (AC: all)
  - [x] 10.1 Tokens already live in `ConnectorModule` (`src/connectors/connector.module.ts`) — confirmed
  - [x] 10.3 Simply imported `ConnectorModule` in `ExitManagementModule`. No move needed.
  - [x] 10.4 `ExitManagementModule` imports `ConnectorModule` directly

- [x] Task 11: Tests (all ACs)
  - [x] 11.1 Unit tests for `ThresholdEvaluatorService` (12 tests covering all specified scenarios)
  - [x] 11.2 Unit tests for `ExitMonitorService` (12 tests covering all specified scenarios)
  - [x] 11.3 Unit tests for `ExitTriggeredEvent` construction (5 tests)
  - [x] 11.4 All existing tests continue to pass (645 total, up from 613+ baseline)

## Dev Notes

### Architecture Constraints

- **New module: `exit-management/`** — This is the first story creating this module. Follow the architecture's module structure pattern: `exit-management.module.ts`, `exit-monitor.service.ts`, `threshold-evaluator.service.ts`, co-located tests.
- **Module dependency rules (from CLAUDE.md):**
  - `modules/exit-management/` → `connectors/` (exit orders) + `modules/risk-management/` (budget release) — ALLOWED
  - Cross-module access through interfaces in `common/interfaces/` — use `RISK_MANAGER_TOKEN`, `KALSHI_CONNECTOR_TOKEN`, `POLYMARKET_CONNECTOR_TOKEN`
  - `connectors/` NEVER imports from `modules/` — FORBIDDEN
- **Fan-out is async:** `ExitTriggeredEvent` and `SingleLegExposureEvent` emissions are on the EventEmitter2 async path. Event emission must NEVER delay the exit monitor's next evaluation.
- **ThresholdEvaluatorService is pure:** Zero side effects, zero I/O. Takes data in, returns evaluation result. This makes it trivially testable and replaceable in Phase 1 when model-driven exits are introduced (Epic 10).

### Exit Execution Flow

```
ExitMonitorService (polling every 30s via @Interval)
    |
    v
PositionRepository.findByStatusWithOrders('OPEN')
    |
    v
For each OPEN position:
    |
    ├── Check connector health (both platforms must be connected)
    |
    ├── Fetch current order books from both connectors
    |   - Kalshi: connector.getOrderBook(pair.kalshiContractId)
    |   - Polymarket: connector.getOrderBook(pair.polymarketContractId)
    |
    ├── Get close prices:
    |   - kalshiSide === 'buy' → closeKalshi at bestBid (selling)
    |   - kalshiSide === 'sell' → closeKalshi at bestAsk (buying)
    |   - Same logic for Polymarket side
    |
    ├── Build ThresholdEvalInput:
    |   - initialEdge: position.expectedEdge
    |   - Entry prices from ORDER records (linked via kalshiOrderId/polymarketOrderId)
    |   - Current close prices from order books
    |   - Fee schedules from connectors
    |   - resolutionDate from pair (ContractMatch)
    |
    ├── ThresholdEvaluatorService.evaluate(input)
    |
    └── If triggered:
        |
        ├── Submit exit order on primary platform
        ├── Submit exit order on secondary platform
        |
        ├── Both fill:
        |   1. Persist both exit orders
        |   2. Calculate realized P&L
        |   3. Position → CLOSED
        |   4. riskManager.closePosition(capital, pnl)
        |   5. Emit ExitTriggeredEvent
        |
        ├── First fills, second fails:
        |   1. Persist successful exit order
        |   2. Position → EXIT_PARTIAL
        |   3. Emit SingleLegExposureEvent
        |   4. Operator resolves via Story 5.3 endpoints
        |
        └── First fails:
            1. Position stays OPEN
            2. Log warning
            3. Will retry on next 30s cycle
```

### Edge & P&L Calculation — CRITICAL

**Entry state (from ExecutionService, Story 5.1):**
A position has two legs. Example: Kalshi BUY at 0.62, Polymarket SELL at 0.65. Initial edge = 0.03 (3%).

**Current P&L calculation:**
For each leg, calculate the gain/loss if we close it now:
- Kalshi leg (bought at 0.62): close by selling at current best bid. P&L = (bestBid - 0.62) * size
- Polymarket leg (sold at 0.65): close by buying at current best ask. P&L = (0.65 - bestAsk) * size
- Total P&L = kalshiPnl + polymarketPnl - exitFees

**Threshold checks:**
Per-leg P&L is calculated using each leg's own size and entry price. Total P&L is the sum of both legs' P&L minus exit fees. Leg sizes may differ (e.g., after a partial fill resolution from Story 5.3 where `fillSize < size`).
- **Take-profit:** totalPnl >= 0.80 * initialEdge * minLegSize — where `minLegSize = Decimal.min(kalshiSize, polymarketSize)`. Uses min to be conservative: the edge was priced assuming matched sizes, so threshold should scale to the smaller leg.
- **Stop-loss:** totalPnl <= -(2 * initialEdge * minLegSize)
- **Time-based:** Now + 48 hours >= resolutionDate

**IMPORTANT — Use entry fill prices from ORDER records, NOT position.entryPrices:**
Story 5.3 established this pattern: `entryPrices` on the position may be incomplete for single-leg-resolved positions. Always use the linked Order records' `fillPrice` for accurate P&L. The `findByStatusWithOrders()` query includes order relations for this reason.

### Connector Token Access Pattern

The Kalshi and Polymarket connectors are injected via tokens. Check how `SingleLegResolutionService` (Story 5.3) handles this — it injects:
```typescript
@Inject(KALSHI_CONNECTOR_TOKEN) private readonly kalshiConnector: IPlatformConnector,
@Inject(POLYMARKET_CONNECTOR_TOKEN) private readonly polymarketConnector: IPlatformConnector,
```

**Circular dependency risk:** If connector tokens currently live in `ExecutionModule`, do NOT import `ExecutionModule` into `ExitManagementModule` — this creates a circular dependency path if `ExecutionModule` ever needs exit-management services. Instead, move connector registrations to `ConnectorModule` (`src/connectors/connector.module.ts`) per Task 10. The architecture's module dependency graph already shows `connectors/` as a shared dependency consumed by both `execution/` and `exit-management/`. **Do NOT create duplicate provider registrations.**

### Resolution Date

The `ContractMatch` model currently has no `resolutionDate` field. This story adds it as a **nullable** DateTime:
- Null means time-based exit threshold is skipped for that pair (ThresholdEvaluatorService handles null gracefully)
- It's the **earliest resolution date** between both platform's contracts for that pair
- Stored as `timestamptz` in PostgreSQL for timezone safety
- **No write path exists yet.** There is currently no API endpoint or configuration mechanism to set `resolutionDate` on existing contract pairs. Until such a mechanism is added (candidates: extend the contract pair config from Story 3.1, or add a `PATCH /api/contract-matches/:id` endpoint in a future story), the field will remain null for all pairs and time-based exits will never trigger. This is acceptable for MVP — take-profit and stop-loss are the primary exit mechanisms. The time-based exit becomes functional once operators can set resolution dates, which can be done via a simple Prisma Studio edit or a future API endpoint.

### Partial Exit Handling

When one exit leg fails, the position transitions to `EXIT_PARTIAL`. This reuses the infrastructure from Stories 5.2 and 5.3:
- `SingleLegExposureEvent` is emitted (same event class, different context)
- `ExposureAlertScheduler` (Story 5.3) will detect it and start 60-second re-emissions
- Operator can use `POST /api/positions/:id/retry-leg` or `POST /api/positions/:id/close-leg` to resolve

**IMPORTANT:** The `SingleLegResolutionService` currently checks for `SINGLE_LEG_EXPOSED` status. It needs to ALSO accept `EXIT_PARTIAL` status for retry-leg and close-leg operations. Update the validation check in both `retryLeg()` and `closeLeg()` to accept either status. Similarly, `ExposureAlertScheduler.handleCron()` should query for BOTH `SINGLE_LEG_EXPOSED` AND `EXIT_PARTIAL` positions.

### Fee Handling

- `getFeeSchedule()` returns `takerFeePercent` on a 0-100 scale. Convert: `takerFeeDecimal = takerFeePercent / 100`
- Exit orders are taker orders (taking liquidity from the book at best bid/ask)
- Both legs incur taker fees on exit
- Use `Decimal` (decimal.js) for all fee calculations

### Error Codes

Add to existing execution error codes:
```typescript
PARTIAL_EXIT_FAILURE: 2008,  // One exit leg filled but the other failed
```

### Existing Code to Build On

**SingleLegResolutionService (single-leg-resolution.service.ts):**
- `closeLeg()` — pattern for submitting opposing trades (buy→sell at bestBid, sell→buy at bestAsk)
- `getConnector()` — resolves connector by platform
- `getContractId()` — gets contract ID from ContractMatch
- `getSide()` — gets side from position

**ExposureAlertScheduler (exposure-alert-scheduler.service.ts):**
- Pattern for `@Interval(60000)` polling with error isolation
- Connector health check before operations
- Debounce via in-memory map

**PositionRepository (position.repository.ts):**
- `findByStatusWithPair()` — existing query for positions with ContractMatch included
- `updateStatus()` — simple status transitions

**Event catalog (event-catalog.ts):**
- `EXIT_TRIGGERED: 'execution.exit.triggered'` — already registered as placeholder

**IRiskManager (risk-manager.interface.ts):**
- `closePosition(capitalReturned, pnlDelta)` — added in Story 5.3, ready to use

### DoD Gates (from Epic 4.5 Retro Action Items)

1. **Test isolation** — all new tests must mock platform API calls, no live HTTP
2. **Interface preservation** — do not rename existing interface methods; add new ones alongside if needed
3. **Normalization ownership** — order books from `getOrderBook()` are already normalized (decimal probability 0.00-1.00)

### Project Structure Notes

**New files (exit-management module):**
- `src/modules/exit-management/exit-management.module.ts`
- `src/modules/exit-management/exit-monitor.service.ts`
- `src/modules/exit-management/exit-monitor.service.spec.ts`
- `src/modules/exit-management/threshold-evaluator.service.ts`
- `src/modules/exit-management/threshold-evaluator.service.spec.ts`

**Modified files:**
- `prisma/schema.prisma` — add `resolutionDate` to ContractMatch
- `src/common/events/execution.events.ts` — add `ExitTriggeredEvent` class
- `src/common/events/execution.events.spec.ts` — add event tests
- `src/common/errors/execution-error.ts` — add error code 2008
- `src/app.module.ts` — import `ExitManagementModule`
- `src/persistence/repositories/position.repository.ts` — add `findByStatusWithOrders()`
- `src/modules/execution/single-leg-resolution.service.ts` — accept `EXIT_PARTIAL` status in retryLeg/closeLeg
- `src/modules/execution/single-leg-resolution.service.spec.ts` — add EXIT_PARTIAL tests
- `src/modules/execution/exposure-alert-scheduler.service.ts` — also query EXIT_PARTIAL positions
- `src/modules/execution/exposure-alert-scheduler.service.spec.ts` — add EXIT_PARTIAL test

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5, Story 5.4]
- [Source: _bmad-output/planning-artifacts/prd.md#FR-EM-01]
- [Source: _bmad-output/planning-artifacts/architecture.md#Exit Management Module]
- [Source: _bmad-output/planning-artifacts/architecture.md#Module Dependency Graph]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error Handling]
- [Source: _bmad-output/planning-artifacts/architecture.md#Event Emission]
- [Source: _bmad-output/implementation-artifacts/5-1-order-submission-position-tracking.md#Dev Notes]
- [Source: _bmad-output/implementation-artifacts/5-3-single-leg-resolution-operator-actions.md#Dev Notes]
- [Source: CLAUDE.md#Architecture, #Error Handling, #Event Emission, #Domain Rules]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None

### Completion Notes List

- All 11 tasks with all subtasks implemented and verified
- 647 tests passing across 50 test files (up from ~613 baseline, +2 from code review)
- Lint clean — zero warnings/errors
- ThresholdEvaluatorService is pure (zero side effects) — ready for Phase 1 replacement with model-driven exits
- Connector tokens already in ConnectorModule — no move needed (Task 10 simplified)
- EXIT_PARTIAL status integrates seamlessly with existing SingleLegResolution and ExposureAlertScheduler workflows
- resolutionDate field added as nullable — time-based exits will activate once operators populate this field
- Circuit breaker implements skip-one-cycle pattern after 3 consecutive full failures

### Code Review Fixes (Amelia — CR Agent)

- **M1 Fixed:** `handlePartialExit` now receives actual `failedAttemptedPrice` and `failedAttemptedSize` instead of hardcoded zeros — operator gets complete context for resolution
- **M3 Fixed:** `executeExit` param typed as `ThresholdEvalResult` instead of inline `{ type?: string; ... }` — removed unsafe `as` cast
- **L1 Fixed:** Added 2 test cases for guard branches: missing side data, missing fill data
- **L2 Fixed:** Circuit breaker log now includes `data` field per project convention
- **M2 Withdrawn:** Repository registration per-module follows established codebase pattern (`PersistenceModule` is `@Global()` for `PrismaService` only)

### Change Log

- Added `resolutionDate` to ContractMatch schema + migration
- Added `ExitTriggeredEvent` class and tests
- Added `PARTIAL_EXIT_FAILURE: 2008` error code
- Added `findByStatusWithOrders()` to PositionRepository
- Updated `SingleLegResolutionService` to accept EXIT_PARTIAL status
- Updated `ExposureAlertScheduler` to query EXIT_PARTIAL positions
- Created `exit-management` module with ThresholdEvaluatorService, ExitMonitorService
- Registered ExitManagementModule in AppModule

### File List

**Created:**
- `pm-arbitrage-engine/src/modules/exit-management/exit-management.module.ts`
- `pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.ts`
- `pm-arbitrage-engine/src/modules/exit-management/exit-monitor.service.spec.ts`
- `pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.ts`
- `pm-arbitrage-engine/src/modules/exit-management/threshold-evaluator.service.spec.ts`
- `pm-arbitrage-engine/prisma/migrations/20260220000643_add_resolution_date_to_contract_match/migration.sql`

**Modified:**
- `pm-arbitrage-engine/prisma/schema.prisma`
- `pm-arbitrage-engine/src/common/events/execution.events.ts`
- `pm-arbitrage-engine/src/common/events/execution.events.spec.ts`
- `pm-arbitrage-engine/src/common/events/event-catalog.ts`
- `pm-arbitrage-engine/src/common/errors/execution-error.ts`
- `pm-arbitrage-engine/src/persistence/repositories/position.repository.ts`
- `pm-arbitrage-engine/src/modules/execution/single-leg-resolution.service.ts`
- `pm-arbitrage-engine/src/modules/execution/single-leg-resolution.service.spec.ts`
- `pm-arbitrage-engine/src/modules/execution/exposure-alert-scheduler.service.ts`
- `pm-arbitrage-engine/src/modules/execution/exposure-alert-scheduler.service.spec.ts`
- `pm-arbitrage-engine/src/app.module.ts`
