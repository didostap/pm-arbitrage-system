---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-03-27'
workflowType: 'testarch-atdd'
inputDocuments:
  - '_bmad-output/implementation-artifacts/10-9-3-backtest-simulation-engine-core.md'
  - '_bmad-output/implementation-artifacts/10-9-0-design-doc.md'
  - '_bmad/tea/testarch/knowledge/data-factories.md'
  - '_bmad/tea/testarch/knowledge/test-quality.md'
  - '_bmad/tea/testarch/knowledge/test-levels-framework.md'
  - '_bmad/tea/testarch/knowledge/test-priorities-matrix.md'
  - '_bmad/tea/testarch/knowledge/test-healing-patterns.md'
---

# ATDD Checklist - Epic 10-9, Story 10-9.3: Backtest Simulation Engine — Core

**Date:** 2026-03-27
**Author:** Arbi
**Primary Test Level:** Unit + Integration (backend)

---

## Story Summary

**As an** operator
**I want** to run a backtest that replays historical data through parameterized detection and cost models
**So that** I can evaluate whether a given parameter set would have been profitable

---

## Acceptance Criteria

1. Engine iterates through historical data chronologically when configured with: date range, parameter set (minimum edge threshold, position sizing %, max concurrent pairs, trading window hours), and fee model
2. At each timestamp, the detection model identifies opportunities using the parameterized edge threshold
3. Position sizing is computed using VWAP from available depth data (PMXT Archive hourly L2 or interpolated)
4. Execution costs are modeled using historical fee schedules (Kalshi dynamic fees, Polymarket fixed fees + gas estimates)
5. Exit logic applies the parameterized exit criteria against subsequent price data
6. The engine tracks simulated portfolio state: open positions, P&L per position, aggregate P&L, drawdown, capital utilization
7. Fill modeling uses conservative assumptions: taker fills at ask/bid, partial fills proportional to available depth, no market impact modeling
8. Single-leg scenarios are not simulated (assume both legs fill — documented limitation)

---

## Failing Tests Created (RED Phase)

### Task 2: BacktestConfigDto Validation Tests (14 tests)

**File:** `src/modules/backtesting/dto/backtest-config.dto.spec.ts` (NEW, ~180 lines)

- [ ] **Test:** [P0] should accept valid config with all required fields (dateRangeStart, dateRangeEnd)
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #1 — core configuration acceptance
- [ ] **Test:** [P0] should apply correct default values (edgeThresholdPct=0.008, positionSizePct=0.03, maxConcurrentPairs=10, bankrollUsd='10000', etc.)
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #1 — parameter defaults
- [ ] **Test:** [P1] should reject missing dateRangeStart with validation error
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #1 — required field validation
- [ ] **Test:** [P1] should reject missing dateRangeEnd with validation error
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #1 — required field validation
- [ ] **Test:** [P1] should reject edgeThresholdPct outside 0-1 range
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #1 — range constraint
- [ ] **Test:** [P1] should reject positionSizePct outside 0-1 range
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #1 — range constraint
- [ ] **Test:** [P1] should reject maxConcurrentPairs < 1 or > 100
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #1 — range constraint
- [ ] **Test:** [P1] should reject tradingWindowStartHour outside 0-23
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #1 — range constraint
- [ ] **Test:** [P1] should reject timeoutSeconds < 60 or > 3600
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #1 — range constraint
- [ ] **Test:** [P1] should accept bankrollUsd and gasEstimateUsd as string values for safe Decimal conversion
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #1 — Decimal string convention
- [ ] **Test:** [P1] should default walkForwardEnabled=false and walkForwardTrainPct=0.70 (reserved for 10-9-4)
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #1 — future-proofing defaults
- [ ] **Test:** [P1] should reject exitEdgeEvaporationPct outside 0-1 range
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #5 — exit parameter validation
- [ ] **Test:** [P1] should reject exitTimeLimitHours < 1
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #5 — exit parameter validation
- [ ] **Test:** [P1] should reject exitProfitCapturePct outside 0-1 range
  - **Status:** RED — BacktestConfigDto class does not exist
  - **Verifies:** AC #5 — exit parameter validation

**File:** `src/modules/backtesting/dto/backtest-result.dto.spec.ts` (NEW, ~60 lines)

- [ ] **Test:** [P2] should construct BacktestRunResponseDto with aggregate metrics fields
  - **Status:** RED — BacktestRunResponseDto class does not exist
  - **Verifies:** AC #6 — response shape
- [ ] **Test:** [P2] should construct BacktestPositionResponseDto with entry/exit fields
  - **Status:** RED — BacktestPositionResponseDto class does not exist
  - **Verifies:** AC #6 — response shape

### Task 2: Simulation Types Tests (6 tests)

**File:** `src/modules/backtesting/types/simulation.types.spec.ts` (NEW, ~80 lines)

- [ ] **Test:** [P1] should construct SimulatedPosition with entry fields, null exit fields, and openedAt timestamp
  - **Status:** RED — SimulatedPosition interface does not exist
  - **Verifies:** AC #6 — position tracking type
- [ ] **Test:** [P1] should construct BacktestPortfolioState with availableCapital, deployedCapital, openPositions Map, and metric accumulators
  - **Status:** RED — BacktestPortfolioState interface does not exist
  - **Verifies:** AC #6 — portfolio state type
- [ ] **Test:** [P1] should construct BacktestTimeStep with aligned prices for both platforms
  - **Status:** RED — BacktestTimeStep interface does not exist
  - **Verifies:** AC #1 — time step data structure
- [ ] **Test:** [P1] should construct ExitEvaluation with triggered exit reason and priority
  - **Status:** RED — ExitEvaluation interface does not exist
  - **Verifies:** AC #5 — exit evaluation type

---

### Task 3: Error Codes Tests (4 tests)

**File:** `src/common/errors/system-health-error.spec.ts` (EXTEND existing, ~40 lines added)

- [ ] **Test:** [P1] should define BACKTEST_STATE_ERROR with code 4204
  - **Status:** RED — error code 4204 not defined
  - **Verifies:** AC #1 — state machine error
- [ ] **Test:** [P1] should define BACKTEST_TIMEOUT with code 4210
  - **Status:** RED — error code 4210 not defined
  - **Verifies:** AC #1 — timeout error
- [ ] **Test:** [P1] should define BACKTEST_INSUFFICIENT_DATA with code 4211
  - **Status:** RED — error code 4211 not defined
  - **Verifies:** AC #1 — insufficient data error
- [ ] **Test:** [P1] should define BACKTEST_INVALID_CONFIGURATION with code 4212
  - **Status:** RED — error code 4212 not defined
  - **Verifies:** AC #1 — configuration error
- [ ] **Test:** [P1] should have no duplicate error codes across all SYSTEM_HEALTH_ERROR_CODES
  - **Status:** GREEN (existing test pattern) — verify new codes integrated
  - **Verifies:** Cross-cutting — error code uniqueness

### Task 3: Domain Event Tests (9 tests)

**File:** `src/common/events/backtesting.events.spec.ts` (EXTEND existing, ~120 lines added)

- [ ] **Test:** [P1] should construct BacktestRunStartedEvent with runId and config snapshot
  - **Status:** RED — event class does not exist
  - **Verifies:** AC #6 — event emission
- [ ] **Test:** [P1] should construct BacktestRunCompletedEvent with runId and aggregate metrics
  - **Status:** RED — event class does not exist
  - **Verifies:** AC #6 — event emission
- [ ] **Test:** [P1] should construct BacktestRunFailedEvent with runId, error code, and message
  - **Status:** RED — event class does not exist
  - **Verifies:** AC #6 — event emission
- [ ] **Test:** [P2] should construct BacktestRunCancelledEvent with runId
  - **Status:** RED — event class does not exist
  - **Verifies:** AC #6 — event emission
- [ ] **Test:** [P1] should construct BacktestPositionOpenedEvent with position details and entry edge
  - **Status:** RED — event class does not exist
  - **Verifies:** AC #6 — position lifecycle events
- [ ] **Test:** [P1] should construct BacktestPositionClosedEvent with exit reason, realized P&L, and holding hours
  - **Status:** RED — event class does not exist
  - **Verifies:** AC #6 — position lifecycle events
- [ ] **Test:** [P1] should construct BacktestEngineStateChangedEvent with runId, fromState, and toState
  - **Status:** RED — event class does not exist
  - **Verifies:** AC #1 — state machine observability
- [ ] **Test:** [P1] should register all 7 backtesting engine events in EVENT_NAMES catalog
  - **Status:** RED — event names not registered
  - **Verifies:** Cross-cutting — event catalog completeness
- [ ] **Test:** [P1] should detect no dead handlers for backtesting engine events via expectNoDeadHandlers
  - **Status:** RED — handlers not yet implemented
  - **Verifies:** Cross-cutting — dead handler detection

---

### Task 4: IBacktestEngine Interface Tests (2 tests)

**File:** `src/common/interfaces/backtest-engine.interface.spec.ts` (NEW, ~30 lines)

- [ ] **Test:** [P2] should export IBacktestEngine interface with startRun, cancelRun, getRunStatus methods
  - **Status:** RED — interface does not exist
  - **Verifies:** AC #1 — interface contract
- [ ] **Test:** [P2] should export BACKTEST_ENGINE_TOKEN injection token
  - **Status:** RED — token does not exist
  - **Verifies:** AC #1 — DI token

---

### Task 5: FillModelService Tests (14 tests)

**File:** `src/modules/backtesting/engine/fill-model.service.spec.ts` (NEW, ~280 lines)

**adaptDepthToOrderBook() — 4 tests:**

- [ ] **Test:** [P0] should convert NormalizedHistoricalDepth (Decimal bids/asks) to NormalizedOrderBook (number PriceLevel)
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #3 — depth adapter correctness
- [ ] **Test:** [P0] should sort bids descending by price and asks ascending by price after conversion
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #3 — sort invariant (Prisma JSON does NOT guarantee order)
- [ ] **Test:** [P1] should preserve platformId and contractId in converted order book
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #3 — metadata preservation
- [ ] **Test:** [P1] should handle empty bids or asks arrays without error
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #7 — edge case handling

**findNearestDepth() — 4 tests:**

- [ ] **Test:** [P0] should return the most recent depth snapshot with timestamp <= query timestamp
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #3 — nearest-neighbor lookup (conservative: use earlier snapshot)
- [ ] **Test:** [P0] should return null when no depth snapshot exists at or before query timestamp
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #7 — insufficient data handling
- [ ] **Test:** [P1] should select correct snapshot when multiple exist (use nearest, not interpolated)
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #3 — no interpolation between snapshots
- [ ] **Test:** [P1] should filter by platform and contractId when querying depth
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #3 — scope filtering

**modelFill() — 6 tests:**

- [ ] **Test:** [P0] should return VwapFillResult when sufficient depth available via calculateVwapWithFillInfo
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #3 — VWAP fill modeling
- [ ] **Test:** [P0] should return null when depth is insufficient for requested position size
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #7 — null on insufficient depth
- [ ] **Test:** [P0] should return partial fill proportional to available depth
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #7 — partial fills proportional to depth
- [ ] **Test:** [P1] should use taker side (ask for buys, bid for sells) per conservative assumption
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #7 — taker fills at ask/bid
- [ ] **Test:** [P1] should return null when nearest depth snapshot not found
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #7 — cascading null from findNearestDepth
- [ ] **Test:** [P1] should correctly parse Prisma Json depth levels (string price/size → Decimal)
  - **Status:** RED — FillModelService does not exist
  - **Verifies:** AC #3 — Prisma JSON boundary conversion

---

### Task 6: ExitEvaluatorService Tests (12 tests)

**File:** `src/modules/backtesting/engine/exit-evaluator.service.spec.ts` (NEW, ~300 lines)

**Individual exit criteria — 5 tests:**

- [ ] **Test:** [P0] should trigger EDGE_EVAPORATION when current net edge < exitEdgeEvaporationPct
  - **Status:** RED — ExitEvaluatorService does not exist
  - **Verifies:** AC #5 — edge evaporation criterion
- [ ] **Test:** [P0] should trigger TIME_DECAY when holding duration > exitTimeLimitHours
  - **Status:** RED — ExitEvaluatorService does not exist
  - **Verifies:** AC #5 — time decay criterion
- [ ] **Test:** [P0] should trigger PROFIT_CAPTURE when edge recovery >= exitProfitCapturePct of entry edge
  - **Status:** RED — ExitEvaluatorService does not exist
  - **Verifies:** AC #5 — profit capture criterion
- [ ] **Test:** [P0] should trigger RESOLUTION_FORCE_CLOSE at contract resolution using price 1.00 or 0.00 (not VWAP)
  - **Status:** RED — ExitEvaluatorService does not exist
  - **Verifies:** AC #5 — resolution force-close with resolution price
- [ ] **Test:** [P0] should trigger INSUFFICIENT_DEPTH when no depth available for exit valuation
  - **Status:** RED — ExitEvaluatorService does not exist
  - **Verifies:** AC #5, #7 — insufficient depth exit

**Priority ordering — 3 tests:**

- [ ] **Test:** [P0] should return RESOLUTION_FORCE_CLOSE when resolution and other criteria trigger simultaneously
  - **Status:** RED — ExitEvaluatorService does not exist
  - **Verifies:** AC #5 — priority: resolution > all others
- [ ] **Test:** [P0] should return INSUFFICIENT_DEPTH over PROFIT_CAPTURE when both trigger
  - **Status:** RED — ExitEvaluatorService does not exist
  - **Verifies:** AC #5 — priority: insufficient depth > profit capture > edge evap > time decay
- [ ] **Test:** [P1] should return PROFIT_CAPTURE over EDGE_EVAPORATION when both trigger
  - **Status:** RED — ExitEvaluatorService does not exist
  - **Verifies:** AC #5 — priority ordering middle tier

**Edge cases — 4 tests:**

- [ ] **Test:** [P0] should return null when no exit criteria triggered
  - **Status:** RED — ExitEvaluatorService does not exist
  - **Verifies:** AC #5 — position stays open
- [ ] **Test:** [P0] should accrue time-based criteria during coverage gaps and evaluate at first available price after gap
  - **Status:** RED — ExitEvaluatorService does not exist
  - **Verifies:** AC #5 — coverage gap handling
- [ ] **Test:** [P1] should calculate resolution P&L using resolution price (1.00/0.00), not current market VWAP
  - **Status:** RED — ExitEvaluatorService does not exist
  - **Verifies:** AC #5 — resolution force-close P&L
- [ ] **Test:** [P1] should use all Decimal arithmetic for edge comparison (no floating-point)
  - **Status:** RED — ExitEvaluatorService does not exist
  - **Verifies:** Cross-cutting — financial math precision

---

### Task 7: BacktestPortfolioService Tests (18 tests)

**File:** `src/modules/backtesting/engine/backtest-portfolio.service.spec.ts` (NEW, ~350 lines)

**openPosition() — 4 tests:**

- [ ] **Test:** [P0] should deploy capital from availableCapital to deployedCapital and add to openPositions Map
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — capital accounting on open
- [ ] **Test:** [P0] should create SimulatedPosition with correct entry prices, edge, timestamp
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — position data integrity
- [ ] **Test:** [P0] should emit BacktestPositionOpenedEvent with position details payload (expect.objectContaining)
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — event emission with payload verification
- [ ] **Test:** [P1] should reject opening position when availableCapital < required size
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — capital constraint enforcement

**closePosition() — 4 tests:**

- [ ] **Test:** [P0] should release capital back to availableCapital and remove from openPositions Map
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — capital accounting on close
- [ ] **Test:** [P0] should calculate realized P&L using calculateLegPnl for both legs
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — P&L per position
- [ ] **Test:** [P0] should emit BacktestPositionClosedEvent with exit reason, realized P&L, and holding hours (expect.objectContaining)
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — event emission with payload verification
- [ ] **Test:** [P1] should update maxDrawdown if equity drops below previous trough ratio
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — drawdown tracking on close

**updateEquity() — 3 tests:**

- [ ] **Test:** [P0] should recalculate unrealized P&L across all open positions at each time step
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — mark-to-market equity
- [ ] **Test:** [P0] should update peakEquity as running max and maxDrawdown as (peak - current) / peak
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — drawdown formula
- [ ] **Test:** [P1] should handle zero open positions without error (equity = availableCapital)
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — edge case

**getAggregateMetrics() — 5 tests:**

- [ ] **Test:** [P0] should calculate Sharpe ratio as mean(dailyReturns) / stddev(dailyReturns) * sqrt(252)
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — Sharpe ratio formula
- [ ] **Test:** [P0] should return null Sharpe ratio when stddev of daily returns is 0
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — Sharpe edge case (zero variance)
- [ ] **Test:** [P0] should calculate profit factor as sum(winPnl) / abs(sum(lossPnl))
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — profit factor formula
- [ ] **Test:** [P0] should return null profit factor when gross loss is 0 (no losing trades)
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — profit factor edge case
- [ ] **Test:** [P0] should calculate capital utilization as time-weighted average deployed/bankroll
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** AC #6 — capital utilization formula

**Map cleanup — 2 tests:**

- [ ] **Test:** [P1] should delete entry from openPositions Map on closePosition
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** Cross-cutting — collection lifecycle (Map .delete on close)
- [ ] **Test:** [P1] should clear openPositions Map on reset
  - **Status:** RED — BacktestPortfolioService does not exist
  - **Verifies:** Cross-cutting — collection lifecycle (Map .clear on reset)

---

### Task 8: BacktestEngineService Tests (28 tests)

**File:** `src/modules/backtesting/engine/backtest-engine.service.spec.ts` (NEW, ~550 lines)

**State machine transitions — 8 tests:**

- [ ] **Test:** [P0] should transition idle → configuring on submitConfig
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — state machine
- [ ] **Test:** [P0] should transition configuring → loading-data on valid config
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — state machine
- [ ] **Test:** [P0] should transition loading-data → simulating on data loaded
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — state machine
- [ ] **Test:** [P0] should transition simulating → generating-report on simulation complete
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — state machine
- [ ] **Test:** [P0] should transition generating-report → complete on report generated
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — state machine
- [ ] **Test:** [P0] should throw SystemHealthError 4204 on invalid transition (e.g., idle → simulating)
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — invalid transition rejection
- [ ] **Test:** [P0] should allow cancel from any non-terminal state (configuring, loading-data, simulating, generating-report)
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — cancel semantics
- [ ] **Test:** [P0] should allow reset from terminal states (complete, failed, cancelled) back to idle
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — reset semantics
- [ ] **Test:** [P1] should emit BacktestEngineStateChangedEvent on every valid transition with fromState and toState payload
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1, #6 — state change observability

**Startup recovery — 2 tests:**

- [ ] **Test:** [P1] should transition orphaned runs older than timeoutSeconds * 2 to FAILED on onModuleInit
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — startup recovery
- [ ] **Test:** [P1] should not affect runs within the timeout window during startup recovery
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — startup recovery precision

**Concurrency guard — 2 tests:**

- [ ] **Test:** [P1] should enforce maxConcurrentRuns (default 2) and reject excess with SystemHealthError 4204
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — concurrency limit
- [ ] **Test:** [P1] should allow new run after previous run completes (Map cleanup frees slot)
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — concurrency slot recycling

**Data loading phase — 3 tests:**

- [ ] **Test:** [P0] should load HistoricalPrice and HistoricalDepth for configured date range and target pairs
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — data loading
- [ ] **Test:** [P0] should transition to FAILED with 4211 when data coverage < minimumDataCoveragePct (50%)
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — insufficient data gate
- [ ] **Test:** [P1] should query only operatorApproved ContractMatch records for target pairs
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — pair identification

**Detection model integration — 4 tests:**

- [ ] **Test:** [P0] should calculate gross edge for both scenarios (buy Kalshi/sell Poly and vice versa) and pick positive edge
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #2 — edge direction logic
- [ ] **Test:** [P0] should apply net edge calculation with fee schedules and gas estimate via FinancialMath
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #2, #4 — detection with costs
- [ ] **Test:** [P0] should skip opportunity when netEdge < edgeThresholdPct
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #2 — threshold filtering
- [ ] **Test:** [P1] should use close prices as proxy for bid/ask (conservative OHLCV simplification)
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #2 — conservative pricing

**Fill modeling flow — 3 tests:**

- [ ] **Test:** [P0] should abort position opening entirely when either leg returns null from FillModelService (no single-leg)
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #8 — single-leg not simulated, both legs required
- [ ] **Test:** [P0] should open position via BacktestPortfolioService when both legs have valid VwapFillResult and capital available
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #3, #6 — fill → position opening flow
- [ ] **Test:** [P1] should respect maxConcurrentPairs limit when deciding to open new positions
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — concurrent pair limit

**Exit evaluation in loop — 2 tests:**

- [ ] **Test:** [P0] should evaluate exit criteria for all open positions at each time step before detecting new opportunities
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #5 — exits evaluated before entries per loop data flow
- [ ] **Test:** [P0] should close position via BacktestPortfolioService when ExitEvaluatorService returns a triggered exit
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #5, #6 — exit → close flow

**Timeout enforcement — 2 tests:**

- [ ] **Test:** [P1] should transition to FAILED with 4210 when elapsed time exceeds timeoutSeconds
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — timeout protection
- [ ] **Test:** [P1] should check timeout periodically during simulation loop (not just at start/end)
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — periodic timeout check

**Trading window filter — 2 tests:**

- [ ] **Test:** [P1] should skip timestamps outside tradingWindowStartHour–tradingWindowEndHour UTC
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — trading window filter
- [ ] **Test:** [P2] should handle wrap-around when startHour > endHour (e.g., 22–06 UTC)
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — window wrap edge case

**Price alignment — 2 tests:**

- [ ] **Test:** [P1] should skip time steps where either platform has no price data (gap)
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — price alignment
- [ ] **Test:** [P1] should align on 1-minute timestamp intervals using close price as representative
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #1 — temporal alignment

**Resolution handling — 2 tests:**

- [ ] **Test:** [P1] should infer resolution outcome from last price (>=0.95 → 1.00, <=0.05 → 0.00)
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #5 — resolution inference
- [ ] **Test:** [P1] should exclude contracts with ambiguous resolution (final price between 0.05–0.95) and log at warn
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #8 — non-binary resolution exclusion

**Result persistence — 2 tests:**

- [ ] **Test:** [P0] should persist BacktestRun with aggregate metrics on completion
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #6 — result persistence
- [ ] **Test:** [P0] should persist all BacktestPositions with FK to BacktestRun
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** AC #6 — position persistence

**Map cleanup — 2 tests:**

- [ ] **Test:** [P1] should delete runId from runStatuses Map on complete/failed/cancelled
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** Cross-cutting — collection lifecycle (.delete on terminal)
- [ ] **Test:** [P1] should clear runStatuses Map on onModuleDestroy
  - **Status:** RED — BacktestEngineService does not exist
  - **Verifies:** Cross-cutting — collection lifecycle (.clear on destroy)

---

### Task 9: BacktestController Tests (8 tests)

**File:** `src/modules/backtesting/controllers/backtest.controller.spec.ts` (NEW, ~180 lines)

- [ ] **Test:** [P0] should POST /api/backtesting/runs with valid BacktestConfigDto and return 202
  - **Status:** RED — BacktestController does not exist
  - **Verifies:** AC #1 — run submission endpoint
- [ ] **Test:** [P1] should return 400 when dateRangeStart >= dateRangeEnd
  - **Status:** RED — BacktestController does not exist
  - **Verifies:** AC #1 — controller-level validation
- [ ] **Test:** [P1] should return 400 when tradingWindowStartHour === tradingWindowEndHour
  - **Status:** RED — BacktestController does not exist
  - **Verifies:** AC #1 — controller-level validation
- [ ] **Test:** [P1] should GET /api/backtesting/runs with pagination (limit, offset) and return list with count
  - **Status:** RED — BacktestController does not exist
  - **Verifies:** AC #6 — list runs endpoint
- [ ] **Test:** [P1] should GET /api/backtesting/runs/:id and return single run with positions
  - **Status:** RED — BacktestController does not exist
  - **Verifies:** AC #6 — get run detail endpoint
- [ ] **Test:** [P1] should DELETE /api/backtesting/runs/:id and cancel a running backtest
  - **Status:** RED — BacktestController does not exist
  - **Verifies:** AC #1 — cancel endpoint
- [ ] **Test:** [P2] should return 404 when run ID not found on GET or DELETE
  - **Status:** RED — BacktestController does not exist
  - **Verifies:** AC #6 — error handling
- [ ] **Test:** [P2] should use ParseUUIDPipe on :id parameter
  - **Status:** RED — BacktestController does not exist
  - **Verifies:** Cross-cutting — input validation

### Task 9: Module Wiring Tests (3 tests)

**File:** `src/modules/backtesting/engine/engine.module.spec.ts` (NEW, ~60 lines)

- [ ] **Test:** [P1] should register BacktestEngineService, BacktestPortfolioService, FillModelService, ExitEvaluatorService as providers
  - **Status:** RED — EngineModule does not exist
  - **Verifies:** AC #1 — module DI wiring
- [ ] **Test:** [P1] should be importable from BacktestingModule
  - **Status:** RED — EngineModule not imported yet
  - **Verifies:** AC #1 — module composition
- [ ] **Test:** [P1] should resolve BacktestEngineService via BACKTEST_ENGINE_TOKEN
  - **Status:** RED — token binding does not exist
  - **Verifies:** AC #1 — interface-based injection

### Task 9: Fixture-Driven Integration Tests (6 tests)

**File:** `src/modules/backtesting/engine/backtest-engine.integration.spec.ts` (NEW, ~300 lines)

- [ ] **Test:** [P0] FIXTURE: profitable-2leg-arb — should produce P&L > 0 with exit reason PROFIT_CAPTURE
  - **Status:** RED — engine does not exist, fixtures not created
  - **Verifies:** AC #1–#8 — full profitable scenario end-to-end
  - **Fixture data:** Kalshi YES 0.45, Poly NO 0.48, 3% gross edge, 1.5% net
- [ ] **Test:** [P0] FIXTURE: unprofitable-fees-exceed — position should NOT be opened (gross edge 1%, fees 1.2%)
  - **Status:** RED — engine does not exist, fixtures not created
  - **Verifies:** AC #2, #4 — fees exceed edge, below threshold
- [ ] **Test:** [P0] FIXTURE: breakeven — should produce P&L approximately 0 (net edge 1.0%, prices converge)
  - **Status:** RED — engine does not exist, fixtures not created
  - **Verifies:** AC #1–#6 — edge case where profit ≈ fees
- [ ] **Test:** [P0] FIXTURE: resolution-force-close — should exit with RESOLUTION_FORCE_CLOSE when position open at resolution
  - **Status:** RED — engine does not exist, fixtures not created
  - **Verifies:** AC #5, #8 — resolution scenario
- [ ] **Test:** [P1] FIXTURE: insufficient-depth — position should NOT be opened when depth < position size
  - **Status:** RED — engine does not exist, fixtures not created
  - **Verifies:** AC #3, #7 — insufficient depth gate
- [ ] **Test:** [P1] FIXTURE: coverage-gap — should hold position through 6-hour price gap with quality flag set
  - **Status:** RED — engine does not exist, fixtures not created
  - **Verifies:** AC #5, #7 — gap handling with quality annotation

---

### Event Wiring Integration Tests (3 tests)

**File:** `src/common/testing/event-wiring-audit.spec.ts` (EXTEND existing)

- [ ] **Test:** [P1] should wire BacktestPositionOpenedEvent handler in BacktestPortfolioService via real EventEmitter2
  - **Status:** RED — handler not implemented
  - **Verifies:** Cross-cutting — event wiring verification
- [ ] **Test:** [P1] should wire BacktestEngineStateChangedEvent emissions from BacktestEngineService
  - **Status:** RED — emissions not implemented
  - **Verifies:** Cross-cutting — event wiring verification
- [ ] **Test:** [P1] should detect no dead event handlers across backtesting engine module
  - **Status:** RED — module not implemented
  - **Verifies:** Cross-cutting — dead handler detection

---

## Test Summary

| Category | P0 | P1 | P2 | Total |
|----------|----|----|-----|-------|
| DTO Validation (Task 2) | 2 | 12 | 2 | 16 |
| Simulation Types (Task 2) | 0 | 4 | 0 | 4 |
| Error Codes (Task 3) | 0 | 5 | 0 | 5 |
| Domain Events (Task 3) | 0 | 9 | 1 | 10 |
| Interface (Task 4) | 0 | 0 | 2 | 2 |
| FillModelService (Task 5) | 6 | 8 | 0 | 14 |
| ExitEvaluatorService (Task 6) | 7 | 5 | 0 | 12 |
| BacktestPortfolioService (Task 7) | 9 | 9 | 0 | 18 |
| BacktestEngineService (Task 8) | 14 | 18 | 2 | 34 |
| Controller (Task 9) | 1 | 5 | 2 | 8 |
| Module Wiring (Task 9) | 0 | 3 | 0 | 3 |
| Fixture Integration (Task 9) | 4 | 2 | 0 | 6 |
| Event Wiring (cross-cutting) | 0 | 3 | 0 | 3 |
| **TOTAL** | **43** | **83** | **9** | **135** |

---

## Test File Map

| File Path | Task | Tests | New/Extend |
|-----------|------|-------|------------|
| `src/modules/backtesting/dto/backtest-config.dto.spec.ts` | 2 | 14 | NEW |
| `src/modules/backtesting/dto/backtest-result.dto.spec.ts` | 2 | 2 | NEW |
| `src/modules/backtesting/types/simulation.types.spec.ts` | 2 | 4 | NEW |
| `src/common/errors/system-health-error.spec.ts` | 3 | 5 | EXTEND |
| `src/common/events/backtesting.events.spec.ts` | 3 | 10 | EXTEND |
| `src/common/interfaces/backtest-engine.interface.spec.ts` | 4 | 2 | NEW |
| `src/modules/backtesting/engine/fill-model.service.spec.ts` | 5 | 14 | NEW |
| `src/modules/backtesting/engine/exit-evaluator.service.spec.ts` | 6 | 12 | NEW |
| `src/modules/backtesting/engine/backtest-portfolio.service.spec.ts` | 7 | 18 | NEW |
| `src/modules/backtesting/engine/backtest-engine.service.spec.ts` | 8 | 34 | NEW |
| `src/modules/backtesting/controllers/backtest.controller.spec.ts` | 9 | 8 | NEW |
| `src/modules/backtesting/engine/engine.module.spec.ts` | 9 | 3 | NEW |
| `src/modules/backtesting/engine/backtest-engine.integration.spec.ts` | 9 | 6 | NEW |
| `src/common/testing/event-wiring-audit.spec.ts` | cross | 3 | EXTEND |

---

## TDD Implementation Order (Recommended)

1. **Task 1** (Prisma schema) — no tests, but run baseline verification after migration
2. **Task 2** (DTOs + types) — 20 tests, foundational types needed by all other tasks
3. **Task 3** (Error codes + events) — 15 tests, shared infrastructure
4. **Task 4** (IBacktestEngine interface) — 2 tests, quick DI token
5. **Task 5** (FillModelService) — 14 tests, leaf service with 1 dep
6. **Task 6** (ExitEvaluatorService) — 12 tests, pure logic leaf with 0 deps
7. **Task 7** (BacktestPortfolioService) — 18 tests, leaf with 1 dep
8. **Task 8** (BacktestEngineService) — 34 tests, facade orchestrating Tasks 5-7
9. **Task 9** (Controller + module + fixtures) — 17 tests, integration wiring

---

## Fixture Data Requirements

**Directory:** `src/modules/backtesting/__fixtures__/`

| Fixture File | Subdirectory | Description |
|-------------|-------------|-------------|
| `profitable-2leg-arb.fixture.json` | `scenarios/` | Kalshi YES 0.45, Poly NO 0.48, 3% gross, 1.5% net |
| `unprofitable-fees-exceed.fixture.json` | `scenarios/` | Gross edge 1%, fees 1.2% |
| `breakeven.fixture.json` | `scenarios/` | Net edge 1.0%, convergent prices |
| `resolution-force-close.fixture.json` | `scenarios/` | Position open at contract resolution |
| `insufficient-depth.fixture.json` | `scenarios/` | Edge detected, depth < position size |
| `coverage-gap.fixture.json` | `scenarios/` | 6-hour price gap mid-simulation |
| Supporting price series | `price-series/` | Per-scenario OHLCV 1-minute candles |
| Supporting depth snapshots | `depth-snapshots/` | Per-scenario hourly L2 depth |

---

## Key Design Decisions for Test Authors

1. **All financial assertions use Decimal comparison** — never `toBe(0.03)`, always `expect(result.toString()).toBe('0.03')` or `expect(result.equals(new Decimal('0.03'))).toBe(true)`
2. **Factory functions inline per spec file** (project pattern) — no shared fixture imports
3. **Mock PrismaService** for unit tests, real EventEmitter2 for event wiring tests
4. **`vi.useFakeTimers()` for timeout tests** with `vi.advanceTimersByTimeAsync()`
5. **Priority markers in test names** — `[P0]`, `[P1]`, `[P2]` for CI prioritization
6. **AC traceability** — every test description maps to specific AC numbers
7. **Payload verification** — all event emission tests use `expect.objectContaining({...})`, never bare `toHaveBeenCalled()`
8. **SIZE GATE for Task 8** — if BacktestEngineService spec exceeds ~400 lines, split state machine tests into separate file
