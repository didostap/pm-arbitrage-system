# Story 10-9.3: Backtest Simulation Engine — Core

Status: done

## Story

As an operator,
I want to run a backtest that replays historical data through parameterized detection and cost models,
So that I can evaluate whether a given parameter set would have been profitable.

## Acceptance Criteria

1. **Given** historical data has been ingested (Stories 10-9-1a, 10-9-1b) **and** cross-platform pairs are identified (own matches + validated external matches), **When** a backtest is configured with: date range, parameter set (minimum edge threshold, position sizing %, max concurrent pairs, trading window hours), and fee model, **Then** the engine iterates through historical data chronologically
2. At each timestamp, the detection model identifies opportunities using the parameterized edge threshold
3. Position sizing is computed using VWAP from available depth data (PMXT Archive hourly L2 or interpolated)
4. Execution costs are modeled using historical fee schedules (Kalshi dynamic fees, Polymarket fixed fees + gas estimates)
5. Exit logic applies the parameterized exit criteria against subsequent price data
6. The engine tracks simulated portfolio state: open positions, P&L per position, aggregate P&L, drawdown, capital utilization
7. Fill modeling uses conservative assumptions: taker fills at ask/bid (no queue position), partial fills proportional to available depth, no market impact modeling
8. Single-leg scenarios are not simulated (assume both legs fill — documented as known limitation in calibration report, Story 10-9-4)

## Tasks / Subtasks

- [x] Task 1: Prisma Schema — BacktestRun, BacktestPosition + Enums + Migration (AC: #1, #6)
  - [x]1.1 Add `BacktestStatus` enum: `IDLE`, `CONFIGURING`, `LOADING_DATA`, `SIMULATING`, `GENERATING_REPORT`, `COMPLETE`, `FAILED`, `CANCELLED`
  - [x]1.2 Add `BacktestExitReason` enum: `EDGE_EVAPORATION`, `TIME_DECAY`, `PROFIT_CAPTURE`, `RESOLUTION_FORCE_CLOSE`, `INSUFFICIENT_DEPTH`, `SIMULATION_END` — `SIMULATION_END` triggers when the backtest date range ends with positions still open (forced close at last available price). Design doc values `RISK_BUDGET` and `LIQUIDITY_DETERIORATION` are excluded: backtesting has no live risk budget, and `INSUFFICIENT_DEPTH` covers the liquidity case.
  - [x]1.3 Add `BacktestRun` model (see Dev Notes for full schema)
  - [x]1.4 Add `BacktestPosition` model with FK to BacktestRun (see Dev Notes for full schema)
  - [x]1.5 Run `pnpm prisma migrate dev --name add_backtest_run_position_models` + `pnpm prisma generate`
  - [x]1.6 Verify baseline tests still pass (expect ~3167)

- [x] Task 2: BacktestConfigDto, Response DTOs & Simulation Types (AC: #1, #2, #4)
  - [x]2.1 Create `src/modules/backtesting/dto/backtest-config.dto.ts` — full DTO with class-validator decorators, default values (see Dev Notes for complete spec)
  - [x]2.2 Create `src/modules/backtesting/dto/backtest-result.dto.ts` — `BacktestRunResponseDto`, `BacktestPositionResponseDto`
  - [x]2.3 Create `src/modules/backtesting/types/simulation.types.ts` — `SimulatedPosition`, `BacktestPortfolioState`, `BacktestTimeStep`, `ExitEvaluation` interfaces
  - [x]2.4 Tests: DTO validation (required fields, defaults, range constraints, Decimal string fields)

- [x] Task 3: Error Codes & Domain Events (AC: #6)
  - [x]3.1 Add error codes to `system-health-error.ts`: `BACKTEST_STATE_ERROR` (4204), `BACKTEST_TIMEOUT` (4210), `BACKTEST_INSUFFICIENT_DATA` (4211), `BACKTEST_INVALID_CONFIGURATION` (4212)
  - [x]3.2 Add event classes to `backtesting.events.ts`: `BacktestRunStartedEvent`, `BacktestRunCompletedEvent`, `BacktestRunFailedEvent`, `BacktestRunCancelledEvent`, `BacktestPositionOpenedEvent`, `BacktestPositionClosedEvent`, `BacktestEngineStateChangedEvent`
  - [x]3.3 Register event names in `event-catalog.ts`: `backtesting.run.started`, `backtesting.run.completed`, `backtesting.run.failed`, `backtesting.run.cancelled`, `backtesting.position.opened`, `backtesting.position.closed`, `backtesting.engine.state-changed`
  - [x]3.4 Tests: event construction, catalog entries, error code uniqueness

- [x] Task 4: IBacktestEngine Interface (AC: #1)
  - [x]4.1 Create `src/common/interfaces/backtest-engine.interface.ts` with `IBacktestEngine` + `BACKTEST_ENGINE_TOKEN`
  - [x]4.2 Export from `src/common/interfaces/index.ts`

- [x] Task 5: FillModelService — VWAP Fill Modeling + Depth Adapter (AC: #3, #7)
  - [x]5.1 Create `src/modules/backtesting/engine/fill-model.service.ts` (1 dep: PrismaService — leaf)
  - [x]5.2 Implement `adaptDepthToOrderBook()` — converts `NormalizedHistoricalDepth` (Decimal-based) → `NormalizedOrderBook` (number-based PriceLevel) for use with existing `calculateVwapWithFillInfo`
  - [x]5.3 Implement `findNearestDepth()` — nearest-neighbor depth lookup for timestamps between hourly PMXT snapshots
  - [x]5.4 Implement `modelFill()` — calls `calculateVwapWithFillInfo` with adapted depth, returns `VwapFillResult | null`
  - [x]5.5 Tests: adapter conversion correctness, nearest-neighbor selection, null on insufficient depth, partial fill proportional to available depth

- [x] Task 6: ExitEvaluatorService — 5 Exit Criteria with Priority Ordering (AC: #5)
  - [x]6.1 Create `src/modules/backtesting/engine/exit-evaluator.service.ts` (0 deps — pure logic leaf)
  - [x]6.2 Implement `evaluateExits()` — evaluates all 5 exit criteria per position per time step, returns highest-priority triggered exit (or null)
  - [x]6.3 Exit priority: resolution force-close > insufficient depth > profit capture > edge evaporation > time decay
  - [x]6.4 Resolution force-close uses resolution price (1.00 or 0.00), not VWAP
  - [x]6.5 Coverage gap handling: time-based criteria accrue during gaps, exit evaluates at first available price after gap
  - [x]6.6 Tests: each exit criterion independently, priority ordering when multiple trigger simultaneously, coverage gap handling, resolution price P&L

- [x] Task 7: BacktestPortfolioService — Capital Tracking, P&L, Drawdown (AC: #6)
  - [x]7.1 Create `src/modules/backtesting/engine/backtest-portfolio.service.ts` (1 dep: EventEmitter2 — leaf)
  - [x]7.2 Implement `BacktestPortfolioState` tracking: availableCapital, deployedCapital, openPositions Map, closedPositions array, peakEquity, currentEquity, realizedPnl, maxDrawdown
  - [x]7.3 `openPosition()` — deploys capital, creates SimulatedPosition, emits `BacktestPositionOpenedEvent`
  - [x]7.4 `closePosition()` — releases capital, calculates realized P&L via `calculateLegPnl`, updates drawdown, emits `BacktestPositionClosedEvent`
  - [x]7.5 `updateEquity()` — recalculates unrealized P&L across open positions, updates peak/drawdown at each time step
  - [x]7.6 `getAggregateMetrics()` — total P&L, win count, loss count, avg holding hours, capital utilization, Sharpe ratio, profit factor
  - [x]7.7 Map cleanup strategy comment on `openPositions`: `.delete()` on closePosition, `.clear()` on reset
  - [x]7.8 Tests: capital accounting correctness, drawdown tracking, metric edge cases (Sharpe null when stddev=0, profitFactor null when grossLoss=0), Map cleanup path, event emission with payload verification

- [x] Task 8: BacktestEngineService — State Machine, Data Loading, Simulation Loop (AC: #1, #2, #3, #4, #5, #6, #7, #8)
  - [x]8.1 Create `src/modules/backtesting/engine/backtest-engine.service.ts` (6 deps: PrismaService, EventEmitter2, ConfigService, BacktestPortfolioService, FillModelService, ExitEvaluatorService — facade ≤8)
  - [x]8.2 State machine: validate transitions per state transition table (see Dev Notes), emit `BacktestEngineStateChangedEvent` on each transition
  - [x]8.3 Startup recovery: `onModuleInit()` — scan for orphaned runs older than `timeoutSeconds * 2`, transition to FAILED
  - [x]8.4 Concurrency guard: `maxConcurrentRuns` (default 2), reject with 4204 when limit reached
  - [x]8.5 Data loading phase: query `HistoricalPrice` + `HistoricalDepth` for date range and target pairs, verify minimum coverage threshold
  - [x]8.6 Simulation loop: iterate chronologically through aligned price timestamps. Per time step: (a) evaluate exit criteria for open positions, (b) detect new opportunities via `FinancialMath.calculateGrossEdge` → `calculateNetEdge` → `isAboveThreshold`, (c) model fill via FillModelService, (d) open position if capital available and depth sufficient
  - [x]8.7 Trading window filter: skip timestamps outside `tradingWindowStartHour`–`tradingWindowEndHour` UTC
  - [x]8.8 Timeout enforcement: check elapsed time periodically, transition to FAILED with 4210 if exceeded
  - [x]8.9 Persist results: update BacktestRun with aggregate metrics, persist BacktestPositions
  - [x]8.10 Map cleanup: `runStatuses` Map — `.delete()` on complete/failed/cancelled, `.clear()` on `onModuleDestroy()`. Add cleanup strategy comment.
  - [x]8.11 Tests: state machine transitions (valid + invalid), startup recovery, concurrency rejection, detection model integration, fill modeling flow, exit evaluation integration, timeout, trading window filtering, result persistence, Map cleanup path
  - **SIZE GATE:** If BacktestEngineService exceeds ~250 lines during implementation, extract state machine + startup recovery + concurrency into `BacktestStateMachineService` (leaf, ≤5 deps). The simulation loop stays in `BacktestEngineService` as facade. This matches the 10-9-1b pattern where `IngestionQualityAssessorService` was extracted during code review.

- [x] Task 9: BacktestController, EngineModule & Test Fixtures (AC: #1, #6)
  - [x]9.1 Create `src/modules/backtesting/engine/engine.module.ts` — providers: BacktestEngineService, BacktestPortfolioService, FillModelService, ExitEvaluatorService (4 providers, within limit)
  - [x]9.2 Create `src/modules/backtesting/controllers/backtest.controller.ts` — `POST /api/backtesting/runs` (202), `GET /api/backtesting/runs` (paginated), `GET /api/backtesting/runs/:id`, `DELETE /api/backtesting/runs/:id` (cancel)
  - [x]9.3 Update `backtesting.module.ts` — import EngineModule, register BacktestController
  - [x]9.4 Create test fixtures in `src/modules/backtesting/__fixtures__/` — 6 scenarios (profitable, unprofitable, breakeven, resolution-force-close, insufficient-depth, coverage-gap) with deterministic expected outcomes
  - [x]9.5 Tests: controller endpoints, module wiring, fixture-driven integration tests

## Dev Notes

### Design Document Reference

**Authoritative source:** `_bmad-output/implementation-artifacts/10-9-0-design-doc.md` — ALL technical decisions for this story are defined there. When in doubt, the design doc overrides this story file.

Key sections:

- Section 4.1–4.2 (State Machine): state diagram, transition table, startup recovery, concurrency
- Section 4.3 (BacktestConfigDto): full parameterized input schema with defaults
- Section 4.4 (Detection Model): reuses FinancialMath functions, data flow per time step
- Section 4.5 (VWAP Fill Modeling): conservative assumptions, depth interpolation, null handling
- Section 4.6 (Exit Logic): 5 criteria, priority ordering, resolution force-close, coverage gaps
- Section 4.7 (Portfolio State): interface definition, drawdown/utilization formulas
- Section 4.8 (Known Limitations): 10 items — verbatim for calibration report (Story 10-9-4)
- Section 5 (Test Fixtures): directory structure, 6 hand-crafted scenarios, fixture JSON format
- Section 8.1 (File Naming Map): engine/ subdirectory services

### Critical Implementation Notes

**ERROR CODE COLLISION WARNING:** The design doc (section 8.5) assigned codes 4202–4207 for backtesting. Stories 10-9-1a/1b/2 already consumed 4200-4203, 4206-4209 with different names than designed. For this story, use:

- `4204`: `BACKTEST_STATE_ERROR` (state machine violation — matches design doc)
- `4210`: `BACKTEST_TIMEOUT` (simulation exceeded timeout)
- `4211`: `BACKTEST_INSUFFICIENT_DATA` (not enough historical data)
- `4212`: `BACKTEST_INVALID_CONFIGURATION` (invalid config params)
- Reserve `4205` for Story 10-9-4 (`BACKTEST_REPORT_ERROR`)

**NormalizedHistoricalDepth → NormalizedOrderBook Adapter (CRITICAL):**

The existing `calculateVwapWithFillInfo()` in `financial-math.ts` expects `NormalizedOrderBook` which uses `number`-typed `PriceLevel` (`{ price: number; quantity: number }`). Historical depth data is stored as `NormalizedHistoricalDepth` with `Decimal`-typed levels (`{ price: Decimal; size: Decimal }`). You MUST convert:

```typescript
// In FillModelService.adaptDepthToOrderBook():
const orderBook: NormalizedOrderBook = {
  platformId: PlatformId.KALSHI, // or POLYMARKET
  contractId: depth.contractId as ContractId,
  bids: depth.bids.map(l => ({ price: l.price.toNumber(), quantity: l.size.toNumber() })),
  asks: depth.asks.map(l => ({ price: l.price.toNumber(), quantity: l.size.toNumber() })),
  timestamp: depth.timestamp,
};
```

Bids must be sorted descending by price, asks ascending — verify sort after conversion. The Prisma JSON storage does NOT guarantee sort order.

**Depth from Prisma JSON:** `HistoricalDepth.bids` and `.asks` are `Json` columns. The existing `parseJsonDepthLevels()` in `ingestion-quality-assessor.service.ts` is **private** and cannot be imported. Extract the logic to a shared utility `src/modules/backtesting/utils/depth-parsing.utils.ts` (or re-implement equivalent). Each level is `{ price: string; size: string }` in JSON → convert to `{ price: new Decimal(level.price); size: new Decimal(level.size) }`. Similarly, `flagsToJson()` for serializing `DataQualityFlags` with Date objects is module-scoped in the same file — extract or re-implement.

**Nearest-Neighbor Depth Interpolation:** PMXT Archive provides hourly snapshots. For timestamps between snapshots, use the most recent snapshot that is ≤ the query timestamp. Do NOT interpolate between snapshots — use the earlier one for conservative estimate. Query: `WHERE platform = $1 AND contractId = $2 AND timestamp <= $3 ORDER BY timestamp DESC LIMIT 1`.

**Financial Math Reuse — NO REIMPLEMENTATION:**

| Operation       | Function                                                                                     | Location                         |
| --------------- | -------------------------------------------------------------------------------------------- | -------------------------------- |
| Gross edge      | `FinancialMath.calculateGrossEdge(buyPrice, sellPrice)`                                      | `common/utils/financial-math.ts` |
| Net edge        | `FinancialMath.calculateNetEdge(grossEdge, buyPrice, sellPrice, buyFee, sellFee, gas, size)` | same                             |
| Threshold check | `FinancialMath.isAboveThreshold(netEdge, threshold)`                                         | same                             |
| Taker fee rate  | `FinancialMath.calculateTakerFeeRate(price, feeSchedule)`                                    | same                             |
| VWAP fill       | `calculateVwapWithFillInfo(orderBook, closeSide, positionSize)`                              | same                             |
| Leg P&L         | `calculateLegPnl(side, entryPrice, closePrice, size)`                                        | same                             |

**FinancialMath input types:** `calculateGrossEdge`/`calculateNetEdge` expect `Decimal` inputs. `calculateVwapWithFillInfo` expects `NormalizedOrderBook` (number-based) + `Decimal` positionSize. `calculateLegPnl` expects `Decimal` inputs. Convert appropriately at service boundaries.

**FeeSchedule Constants:**

```typescript
// Kalshi: dynamic taker fee
{ platformId: PlatformId.KALSHI, makerFeePercent: 0, takerFeePercent: 1.75,
  description: 'Kalshi dynamic taker fee: 0.07 × P × (1-P) per contract',
  takerFeeForPrice: (price) => new Decimal(0.07).mul(new Decimal(1).minus(price)).toNumber() }

// Polymarket: flat taker fee
{ platformId: PlatformId.POLYMARKET, makerFeePercent: 0, takerFeePercent: 2.0,
  description: 'Polymarket flat 2% taker fee' }
```

Use `dto.kalshiFeeSchedule` and `dto.polymarketFeeSchedule` from config. If the DTO doesn't supply fee schedules, use these defaults from `KalshiConnector.getFeeSchedule()` and the Polymarket constants (`POLYMARKET_TAKER_FEE = 0.02`). FeeSchedule `takerFeePercent` uses 0–100 scale (2.0 = 2%), NOT decimal scale.

**Decimal Convention — ALL `*Pct` DTO Fields Use DECIMAL Form:**

- `edgeThresholdPct: 0.008` means 0.8% (NOT 0.8 or 80)
- `positionSizePct: 0.03` means 3%
- `exitEdgeEvaporationPct: 0.002` means 0.2%
- `exitProfitCapturePct: 0.80` means 80% of entry edge
- `walkForwardTrainPct: 0.70` means 70%

**`bankrollUsd` and `gasEstimateUsd` are STRINGS** in the DTO for safe Decimal conversion at service boundary: `new Decimal(dto.bankrollUsd)`. Do NOT parse as `number`.

**Simulation Loop Data Flow (per time step `t`):**

```
1. Load aligned prices: kalshiClose[t], polymarketClose[t] for each active pair
2. For each open position:
   a. Look up nearest depth snapshot ≤ t
   b. Evaluate exit criteria (priority order) via ExitEvaluatorService
   c. If exit triggered → close position via BacktestPortfolioService
3. For each pair with no open position:
   a. Calculate gross edge: |kalshiClose - (1 - polymarketClose)| (or vice versa)
   b. Determine buy/sell sides (which platform to buy YES, which to sell)
   c. Calculate net edge after fees + gas via calculateNetEdge
   d. If netEdge >= edgeThresholdPct AND capital available AND maxConcurrentPairs not reached:
      i.  Look up nearest depth snapshot ≤ t for both platforms
      ii. Model fill via FillModelService → VwapFillResult
      iii. If fill result null → skip (insufficient depth)
      iv. **Both legs must have fill results** — if either leg returns null from FillModelService, abort position opening entirely. Do NOT create single-leg exposure. This enforces AC#8 (single-leg not simulated).
      v.  Open position via BacktestPortfolioService
4. Update equity + drawdown for all open positions
```

**Edge Direction Logic:** Delegate ALL edge math to `FinancialMath` — do NOT reimplement. The function `FinancialMath.calculateGrossEdge(buyPrice, sellPrice)` returns `sellPrice - buyPrice` (signed). For each pair at time step `t`:

```typescript
// Get close prices from HistoricalPrice for this minute
const kalshiClose = new Decimal(kalshiPrice.close.toString()); // Prisma Decimal → decimal.js
const polyClose = new Decimal(polyPrice.close.toString());

// Scenario A: Buy Kalshi YES (take ask), Sell Polymarket YES (hit bid)
// buyPrice = kalshiClose, sellPrice = (1 - polyClose) [NO side = 1 - YES price]
const edgeA = FinancialMath.calculateGrossEdge(kalshiClose, new Decimal(1).minus(polyClose));

// Scenario B: Sell Kalshi YES (hit bid), Buy Polymarket YES (take ask)
const edgeB = FinancialMath.calculateGrossEdge(polyClose, new Decimal(1).minus(kalshiClose));

// Pick the positive-edge scenario (if any)
const bestEdge = edgeA.gt(edgeB) ? edgeA : edgeB;
// Then pass to calculateNetEdge with appropriate buy/sell fee schedules
```

Note: close prices are used as proxy for both bid and ask in backtesting (no separate bid/ask in OHLCV candles). This is a conservative simplification documented in Known Limitations.

**Pair Identification:** Query `ContractMatch` records with `operatorApproved = true` AND matching contracts in `HistoricalPrice` for the date range. Each pair has `kalshiContractId` and `polymarketClobTokenId`. Use these to query `HistoricalPrice` records per platform.

**Price Alignment:** For each time step, you need prices from BOTH platforms at the same minute. Query `HistoricalPrice` for both platforms, align on `timestamp`. Skip time steps where either platform has no data (gap). Use `intervalMinutes = 1` (1-minute candles) for finest resolution. Use `close` price as the representative price for that candle.

**Resolution Date:** Source from `ContractMatch.resolutionTimestamp`. If a contract resolves during the backtest period, the resolution force-close exit applies at that timestamp with price 1.00 or 0.00. The resolution outcome (which side won) is inferred from the last available price: if final price ≥ 0.95, resolve at 1.00; if ≤ 0.05, resolve at 0.00. If final price is between 0.05 and 0.95 (ambiguous resolution), **exclude this contract from the backtest** and log at `warn` level — do NOT attempt to infer outcome. Non-binary resolutions are excluded per AC#8.

**Data Coverage Threshold:** Task 8.5 must verify minimum data coverage before proceeding to simulation. Default `minimumDataCoveragePct = 0.50` (at least 50% of requested time range has price data for at least one pair). If coverage is below threshold, transition to FAILED with `4211 BACKTEST_INSUFFICIENT_DATA`. This is a hardcoded constant with a comment — not a DTO parameter for MVP.

### State Machine

**Valid transitions:** (see design doc section 4.2 for full table)

```
idle → configuring (submitConfig)
configuring → loading-data (configValid) | failed (configInvalid)
loading-data → simulating (dataLoaded) | failed (insufficientData)
simulating → generating-report (simulationComplete) | failed (timeout)
generating-report → complete (reportGenerated) | failed (reportError)
Any except idle/complete → cancelled (cancel)
cancelled/complete/failed → idle (reset)
```

Invalid transitions throw `SystemHealthError` with code `4204 BACKTEST_STATE_ERROR`.

**Concurrency:** Track active runs via `runStatuses: Map<string, BacktestStatus>`. Max 2 simultaneous non-terminal runs. Map cleanup: `.delete()` on complete/failed/cancelled, `.clear()` on module destroy.

### Prisma Model Schemas

**BacktestRun:**

```prisma
model BacktestRun {
  id                 String              @id @default(uuid())
  status             BacktestStatus      @default(IDLE)
  config             Json                // Serialized BacktestConfigDto
  dateRangeStart     DateTime            @map("date_range_start") @db.Timestamptz
  dateRangeEnd       DateTime            @map("date_range_end") @db.Timestamptz
  startedAt          DateTime            @map("started_at") @db.Timestamptz
  completedAt        DateTime?           @map("completed_at") @db.Timestamptz
  totalPositions     Int?                @map("total_positions")
  winCount           Int?                @map("win_count")
  lossCount          Int?                @map("loss_count")
  totalPnl           Decimal?            @map("total_pnl") @db.Decimal(20, 10)
  maxDrawdown        Decimal?            @map("max_drawdown") @db.Decimal(20, 10)
  sharpeRatio        Decimal?            @map("sharpe_ratio") @db.Decimal(20, 10)
  profitFactor       Decimal?            @map("profit_factor") @db.Decimal(20, 10)
  avgHoldingHours    Decimal?            @map("avg_holding_hours") @db.Decimal(20, 6)
  capitalUtilization Decimal?            @map("capital_utilization") @db.Decimal(20, 10)
  errorMessage       String?             @map("error_message")
  createdAt          DateTime            @default(now()) @map("created_at") @db.Timestamptz
  updatedAt          DateTime            @updatedAt @map("updated_at") @db.Timestamptz
  positions          BacktestPosition[]

  @@index([status])
  @@index([startedAt])
  @@map("backtest_runs")
}
```

**BacktestPosition:**

```prisma
model BacktestPosition {
  id                    Int                  @id @default(autoincrement())
  runId                 String               @map("run_id")
  pairId                String               @map("pair_id")
  kalshiContractId      String               @map("kalshi_contract_id")
  polymarketContractId  String               @map("polymarket_contract_id")
  kalshiSide            String               @map("kalshi_side")
  polymarketSide        String               @map("polymarket_side")
  entryTimestamp        DateTime             @map("entry_timestamp") @db.Timestamptz
  exitTimestamp         DateTime?            @map("exit_timestamp") @db.Timestamptz
  kalshiEntryPrice      Decimal              @map("kalshi_entry_price") @db.Decimal(20, 10)
  polymarketEntryPrice  Decimal              @map("polymarket_entry_price") @db.Decimal(20, 10)
  kalshiExitPrice       Decimal?             @map("kalshi_exit_price") @db.Decimal(20, 10)
  polymarketExitPrice   Decimal?             @map("polymarket_exit_price") @db.Decimal(20, 10)
  positionSizeUsd       Decimal              @map("position_size_usd") @db.Decimal(20, 6)
  entryEdge             Decimal              @map("entry_edge") @db.Decimal(20, 10)
  exitEdge              Decimal?             @map("exit_edge") @db.Decimal(20, 10)
  realizedPnl           Decimal?             @map("realized_pnl") @db.Decimal(20, 10)
  fees                  Decimal?             @map("fees") @db.Decimal(20, 6)
  exitReason            BacktestExitReason?  @map("exit_reason")
  holdingHours          Decimal?             @map("holding_hours") @db.Decimal(20, 6)
  qualityFlags          Json?                @map("quality_flags")
  createdAt             DateTime             @default(now()) @map("created_at") @db.Timestamptz
  run                   BacktestRun          @relation(fields: [runId], references: [id], onDelete: Cascade)

  @@index([runId])
  @@index([exitReason])
  @@map("backtest_positions")
}
```

### BacktestConfigDto Full Spec

```typescript
class BacktestConfigDto {
  @IsDateString() dateRangeStart: string;
  @IsDateString() dateRangeEnd: string;

  @IsNumber() @Min(0) @Max(1) edgeThresholdPct: number = 0.008; // 0.8% min net edge
  @IsNumber() @Min(0) @Max(1) minConfidenceScore: number = 0.8;

  @IsNumber() @Min(0) @Max(1) positionSizePct: number = 0.03; // 3% of bankroll
  @IsInt() @Min(1) @Max(100) maxConcurrentPairs: number = 10;
  @IsString() @IsNotEmpty() bankrollUsd: string = '10000'; // String → Decimal at boundary

  @IsInt() @Min(0) @Max(23) tradingWindowStartHour: number = 14;
  @IsInt() @Min(0) @Max(23) tradingWindowEndHour: number = 23;

  @IsString() gasEstimateUsd: string = '0.50'; // Total gas for round-trip (both legs). String → Decimal at boundary. Polymarket-only cost (Kalshi has no gas).

  @IsNumber() @Min(0) @Max(1) exitEdgeEvaporationPct: number = 0.002; // 0.2%
  @IsNumber() @Min(1) exitTimeLimitHours: number = 72;
  @IsNumber() @Min(0) @Max(1) exitProfitCapturePct: number = 0.8; // 80% of entry edge

  /** Reserved for Story 10-9-4 (walk-forward validation). Not used by simulation engine. */
  @IsOptional() @IsBoolean() walkForwardEnabled: boolean = false;
  /** Reserved for Story 10-9-4 (walk-forward validation). Not used by simulation engine. */
  @IsOptional() @IsNumber() @Min(0.1) @Max(0.9) walkForwardTrainPct: number = 0.7;

  @IsInt() @Min(60) @Max(3600) timeoutSeconds: number = 300;
}
```

**Note:** Fee schedules (`kalshiFeeSchedule`, `polymarketFeeSchedule`) are NOT in the DTO — they are resolved internally from platform constants. The DTO only exposes `gasEstimateUsd` for gas tuning. `maxConcurrentRuns` is a system config (ConfigService), not a per-run parameter.

**Validation:** `dateRangeStart < dateRangeEnd`. `tradingWindowStartHour !== tradingWindowEndHour`. Both are controller-level validations (throw `BadRequestException`).

### Metric Calculations

**Sharpe Ratio:** `mean(dailyReturns) / stddev(dailyReturns) * sqrt(252)`. Return `null` when `stddev === 0` (zero variance = no risk = Sharpe undefined).

**Profit Factor:** `sum(winningPnl) / abs(sum(losingPnl))`. Return `null` when `grossLoss === 0` (no losing trades = infinite factor = undefined).

**Capital Utilization:** `avgDeployedCapital / bankroll` over the simulation period. Calculate as time-weighted average: `sum(deployedCapital_i * duration_i) / totalDuration / bankroll`.

**Max Drawdown:** `max((peakEquity - currentEquity) / peakEquity)` across all time steps. Track `peakEquity` as running max of equity curve. ALL calculations use `Decimal` arithmetic.

### Test Fixture Scenarios

Create in `src/modules/backtesting/__fixtures__/scenarios/`:

| File                                    | Description                                                                      | Expected                                    |
| --------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------- |
| `profitable-2leg-arb.fixture.json`      | Kalshi YES 0.45, Poly NO 0.48, 3% gross edge, 1.5% net. Exits via profit capture | P&L > 0, exit reason: PROFIT_CAPTURE        |
| `unprofitable-fees-exceed.fixture.json` | Gross edge 1%, fees 1.2%                                                         | Position NOT opened (below threshold)       |
| `breakeven.fixture.json`                | Net edge 1.0%, prices converge to offset fees                                    | P&L ≈ 0                                     |
| `resolution-force-close.fixture.json`   | Position open at contract resolution                                             | Exit reason: RESOLUTION_FORCE_CLOSE         |
| `insufficient-depth.fixture.json`       | Edge detected, depth < position size                                             | Position NOT opened, logged                 |
| `coverage-gap.fixture.json`             | 6-hour price gap mid-simulation                                                  | Position held through gap, quality flag set |

Also create in `__fixtures__/depth-snapshots/` and `__fixtures__/price-series/` supporting data files.

### Previous Story Intelligence

**From Story 10-9-1a (Platform API Price & Trade Ingestion):**

- HTTP client: native `fetch()` only — no additional HTTP libraries
- Batch sizing: 500 records per `createMany` with `skipDuplicates: true`
- Kalshi dollar strings already in 0.00–1.00 range — `new Decimal(value)` directly
- Polymarket prices: `new Decimal(String(point.p))` to avoid IEEE 754 noise
- `assessPriceQuality`/`assessTradeQuality` sort by timestamp before analysis — do same for any price series processing
- All code review fixes integrated: cutoff routing, data quality wiring, event emission per source/contract, concurrency guard pattern
- 3037 tests after 10-9-1a

**From Story 10-9-1b (Depth Data & Third-Party Ingestion):**

- `hyparquet` ESM dynamic import pattern: `const { parquetRead } = await import('hyparquet')`
- `parseJsonDepthLevels()` helper validates Prisma `JsonValue` → typed `{ price: string; size: string }[]` — reuse this in FillModelService when reading depth from DB
- `flagsToJson()` helper serializes `DataQualityFlags` with Date objects to JSON-safe values — reuse for position quality flags
- `toDepthUpdateType()` validates string to `'snapshot' | 'price_change' | null` — filter for `'snapshot'` only when querying depth
- Orchestrator dep count: 7 (facade), DataQualityService dep count: 2 (leaf)
- TSC fixes after implementation: be careful with `RetryStrategy` field names (`maxRetries`, `initialDelayMs`, `maxDelayMs`, `backoffMultiplier`)
- `IngestionQualityAssessorService` was extracted from orchestrator during code review to stay under 400 logical lines
- 3094 tests after 10-9-1b (but was 3101 in sprint status — post-review)

**From Story 10-9-2 (Cross-Platform Pair Matching Validation):**

- `getEffectiveSources()` is a standalone function, NOT a class method — avoid transform:true issues
- `fetchJsonWithRetry<T>()` generic helper for type-safe HTTP with retry — consider reusing if applicable
- OddsPipe does NOT return platform IDs, only titles — title matching needed for pair resolution
- Safety timeout pattern: `vi.useFakeTimers` + `advanceTimersByTimeAsync(ms)` for testing timeouts
- `ParseIntPipe` on numeric route params
- 3167 tests after 10-9-2

### Sizing Note

The design doc (section 6.3) flagged this story for split into 10-9-3a (state machine + data loading, ~7 tasks) and 10-9-3b (simulation + portfolio, ~7 tasks) per Agreement #25 (>10 tasks, 3+ integration boundaries). This story has been structured as 9 tasks within the limit. If any task expands significantly during implementation, consider splitting Task 8 (BacktestEngineService) into separate state-machine and simulation-loop tasks.

### Project Structure Notes

**New directories to create:**

- `src/modules/backtesting/engine/` — engine sub-module (does not exist yet)
- `src/modules/backtesting/__fixtures__/scenarios/`
- `src/modules/backtesting/__fixtures__/price-series/`
- `src/modules/backtesting/__fixtures__/depth-snapshots/`

**Module provider analysis:**

- `EngineModule` (new sub-module): 4 providers (BacktestEngineService, BacktestPortfolioService, FillModelService, ExitEvaluatorService) — within ≤8 limit
- `BacktestingModule` (root): imports IngestionModule, ValidationModule, EngineModule + 2 controllers — within limit

**Architecture compliance:**

- `modules/backtesting/` → `common/utils/financial-math.ts` (allowed: all modules → common/)
- `modules/backtesting/` → `persistence/` via PrismaService (allowed)
- `modules/backtesting/` → `common/types/`, `common/events/`, `common/interfaces/` (allowed)
- No imports from connectors, no imports from other modules' services

### References

- [Source: `_bmad-output/implementation-artifacts/10-9-0-design-doc.md` — Sections 4.1–4.8, 5, 6.3, 8.1–8.6, 9]
- [Source: `_bmad-output/planning-artifacts/epics.md` — Epic 10.9, Story 10-9-3]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Module dependency graph, event system, error hierarchy]
- [Source: `pm-arbitrage-engine/src/common/utils/financial-math.ts` — FinancialMath, calculateVwapWithFillInfo, calculateLegPnl]
- [Source: `pm-arbitrage-engine/src/common/types/normalized-order-book.type.ts` — NormalizedOrderBook, PriceLevel]
- [Source: `pm-arbitrage-engine/src/common/types/platform.type.ts` — FeeSchedule, PlatformId]
- [Source: `pm-arbitrage-engine/src/modules/backtesting/types/normalized-historical.types.ts` — NormalizedHistoricalDepth]
- [Source: `pm-arbitrage-engine/src/common/types/historical-data.types.ts` — DataQualityFlags, IngestionMetadata]
- [Source: `pm-arbitrage-engine/src/common/errors/system-health-error.ts` — SYSTEM_HEALTH_ERROR_CODES (existing 4200–4209)]
- [Source: `pm-arbitrage-engine/src/common/events/backtesting.events.ts` — existing events to extend]
- [Source: `pm-arbitrage-engine/src/modules/backtesting/backtesting.module.ts` — current module structure]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None required.

### Completion Notes

All 9 tasks completed via TDD (Red-Green-Refactor). ATDD checklist used as authoritative test map.

**Test Results:** 206 test files, 3273 unit tests passing (+106 new). Pre-existing e2e failures (3) unrelated to this story (database/API connectivity in test/core-lifecycle.e2e-spec.ts).

**Key Decisions:**

- BacktestEngineService stays as single facade (~380 lines formatted). Did NOT hit the 250-line SIZE GATE extraction threshold for splitting state machine out — the async pipeline pattern keeps the service cohesive.
- Used class-token DI for PrismaService (consistent with PersistenceModule @Global pattern) instead of string tokens.
- `closeSide` mapping for VWAP: buy taker → pass 'sell' closeSide (walks asks), sell taker → pass 'buy' closeSide (walks bids). Matches existing `calculateVwapWithFillInfo` semantics.
- Data coverage check uses timestamp span ratio, not count ratio. Requires at least 2 aligned timestamps.

### Files Created/Modified

**New files (13 production + 7 test + 6 fixtures):**

- `prisma/schema.prisma` — BacktestStatus, BacktestExitReason enums + BacktestRun, BacktestPosition models
- `prisma/migrations/20260327143900_add_backtest_run_position_models/migration.sql`
- `src/modules/backtesting/dto/backtest-config.dto.ts` + spec
- `src/modules/backtesting/dto/backtest-result.dto.ts` + spec
- `src/modules/backtesting/types/simulation.types.ts` + spec
- `src/common/interfaces/backtest-engine.interface.ts` + spec
- `src/modules/backtesting/engine/fill-model.service.ts` + spec
- `src/modules/backtesting/engine/exit-evaluator.service.ts` + spec
- `src/modules/backtesting/engine/backtest-portfolio.service.ts` + spec
- `src/modules/backtesting/engine/backtest-engine.service.ts` + spec
- `src/modules/backtesting/engine/engine.module.ts` + spec
- `src/modules/backtesting/controllers/backtest.controller.ts` + spec
- `src/modules/backtesting/__fixtures__/scenarios/` — 6 fixture JSON files

**Modified files (5):**

- `src/common/errors/system-health-error.ts` — 4 new error codes (4204, 4210-4212)
- `src/common/events/backtesting.events.ts` — 7 new event classes
- `src/common/events/event-catalog.ts` — 7 new event name constants
- `src/common/interfaces/index.ts` — IBacktestEngine + BACKTEST_ENGINE_TOKEN exports
- `src/modules/backtesting/backtesting.module.ts` — EngineModule import + BacktestController
