# Exit Monitor Architecture Review — Design Document

**Story:** 10-0-3 | **Status:** Design-only spike (no production code)
**Author:** Dev Agent (Claude Opus 4.6) | **Date:** 2026-03-16
**Blocks:** Story 10.1 (Continuous Edge Recalculation), Story 10.2 (Five-Criteria Model-Driven Exit Logic)

---

## 1. Current State Analysis

### 1.1 ThresholdEvaluatorService (213 lines)

**Location:** `src/modules/exit-management/threshold-evaluator.service.ts`

**Interface — `ThresholdEvalInput`:**
```typescript
interface ThresholdEvalInput {
  initialEdge: Decimal;
  kalshiEntryPrice: Decimal;
  polymarketEntryPrice: Decimal;
  currentKalshiPrice: Decimal;
  currentPolymarketPrice: Decimal;
  kalshiSide: string;
  polymarketSide: string;
  kalshiSize: Decimal;          // INVARIANT: equals polymarketSize
  polymarketSize: Decimal;
  kalshiFeeDecimal: Decimal;
  polymarketFeeDecimal: Decimal;
  resolutionDate: Date | null;
  now: Date;
  entryClosePriceKalshi?: Decimal | null;     // 6.5.5i baseline
  entryClosePricePolymarket?: Decimal | null;
  entryKalshiFeeRate?: Decimal | null;
  entryPolymarketFeeRate?: Decimal | null;
}
```

**Interface — `ThresholdEvalResult`:**
```typescript
interface ThresholdEvalResult {
  triggered: boolean;
  type?: 'stop_loss' | 'take_profit' | 'time_based';
  currentEdge: Decimal;
  currentPnl: Decimal;
  capturedEdgePercent: Decimal;
}
```

**Evaluation flow:** Three criteria in fixed priority order with short-circuit semantics:
1. **Stop-loss (P1):** `currentPnl <= entryCostBaseline + scaledInitialEdge × SL_MULTIPLIER(-2)` → exit
2. **Take-profit (P2):** `currentPnl >= computeTakeProfitThreshold(baseline, scaledEdge)` → exit
3. **Time-based (P3):** `resolutionDate - now <= 48h` → exit
4. **No trigger:** return `{ triggered: false }`

**Key properties:**
- Stateless: all inputs per call, no inter-cycle memory
- Pure: no side effects, no I/O
- Entry cost baseline (6.5.5i): offsets thresholds by natural MtM deficit at entry
- First criterion that triggers wins (short-circuit)

### 1.2 ExitMonitorService (~989 lines)

**Location:** `src/modules/exit-management/exit-monitor.service.ts`

**Polling loop — `evaluatePositions()` @ 30s interval:**
1. Derive `isPaper` / `mixedMode` from connector health
2. Query all `OPEN` + `EXIT_PARTIAL` positions (with orders)
3. For each position: `evaluatePosition()` → if triggered → `executeExit()`
4. Circuit breaker: 3 consecutive full failures → skip next cycle

**Per-position evaluation — `evaluatePosition()`:**
1. Validate connector health (skip if disconnected)
2. Validate fill data (skip if missing)
3. Compute effective sizes (residual for `EXIT_PARTIAL`, entry fill for `OPEN`)
4. Fetch VWAP close prices via `getClosePrice()` (order book → VWAP calculation)
5. Build `ThresholdEvalInput` (fees via `FinancialMath.calculateTakerFeeRate`)
6. Call `thresholdEvaluator.evaluate(evalInput)`
7. If triggered → `executeExit(position, evalResult, ...)`

**Exit execution — `executeExit()` (480 lines):**
- Criteria-agnostic: once triggered, execution flow is identical
- Pre-exit depth check with dual-platform depth cap
- Primary → secondary leg order submission
- Full exit → `CLOSED` + `riskManager.closePosition()`
- Partial exit → `EXIT_PARTIAL` + `riskManager.releasePartialCapital()` + `SingleLegExposureEvent`
- Exit type passed through to `ExitTriggeredEvent`

### 1.3 Shared Constants (`common/constants/exit-thresholds.ts`, 68 lines)

| Constant/Function | Purpose |
|---|---|
| `SL_MULTIPLIER = -2` | SL fires at 2× initial edge loss |
| `TP_RATIO = 0.8` | TP fires at 80% of edge journey |
| `computeTakeProfitThreshold()` | Journey-based TP with edge-relative fallback (9-18) |
| `calculateExitProximity()` | Unified 0→1 proximity for SL and TP (dashboard display) |

### 1.4 Dashboard Integration (`dashboard/position-enrichment.service.ts`)

`PositionEnrichmentService.enrich()` replicates the threshold math to compute:
- SL proximity, TP proximity (via shared `calculateExitProximity()`)
- Projected SL/TP P&L thresholds
- Current edge, unrealized P&L
- Depth-sufficient indicators (VWAP)

### 1.5 Event Schema (`common/events/execution.events.ts`)

```typescript
class ExitTriggeredEvent {
  exitType: 'take_profit' | 'stop_loss' | 'time_based' | 'manual';
  // + positionId, pairId, initialEdge, finalEdge, realizedPnl, orderIds, isPaper, mixedMode
}
```

Consumers: `MonitoringEventConsumer` (audit log, Telegram), dashboard WebSocket gateway.

### 1.6 Module Boundary

`ThresholdEvaluatorService` is **internal** to `exit-management` module (not exported). Only `ExitMonitorService` is exported. Shared types/constants already in `common/`.

---

## 2. Five-Criteria Composition Model

### 2.1 Criteria Definitions & Data Sources

| # | Criterion | Trigger Condition | Data Source | Status |
|---|-----------|-------------------|-------------|--------|
| 1 | **Edge evaporation** | Recalculated edge < breakeven after costs | Live prices (WS/polling) + fee schedules + gas | **Existing** — generalization of current SL |
| 2 | **Model confidence drop** | `confidenceScore` decreased by ≥ threshold since entry | `ContractMatch.confidenceScore` (DB) | **Existing field** — needs entry snapshot + delta |
| 3 | **Time decay** | Expected value diminishes on configurable curve as resolution approaches | `ContractMatch.resolutionDate` | **Existing field** — needs continuous curve replacing binary 48h |
| 4 | **Risk budget breach** | Portfolio risk limit approached AND this position has lowest remaining edge | `IRiskManager.getCurrentExposure(isPaper)` + cross-position edge ranking | **Existing data** — needs ranking logic in caller |
| 5 | **Liquidity deterioration** | Order book depth at exit prices < minimum executable threshold | Order book from WS/polling | **Existing data** — needs minimum depth config |

**New data sources required:**
- **Criterion 2:** New `entryConfidenceScore` field on `OpenPosition` (nullable `Float?`, Prisma migration required in Story 10.2). Captured at execution time in `ExecutionService` from `ContractMatch.confidenceScore`. Current `confidenceScore` read from `ContractMatch` at evaluation time. **Legacy positions** (opened before this field exists) have `entryConfidenceScore = null` → criterion #2 proximity defaults to `0` (skipped, not triggered) — these positions have no baseline to measure degradation against.
- **Criterion 3:** Decay curve function (new, pure math) + configurable parameters (`horizonHours`, `steepness`, `triggerThreshold`)
- **Criterion 5:** Configurable `MIN_EXIT_DEPTH` threshold (new config constant). Uses absolute threshold — no entry-time depth capture needed (order books are too volatile for entry snapshots to be meaningful).

**No new external API calls** — all data already available from existing connectors and DB.

### 2.2 Composition Strategy

**Decision: Independent evaluation with priority-ordered trigger selection**

All five criteria are evaluated every cycle (no short-circuit). The result includes per-criterion proximity for dashboard display. The **trigger decision** uses priority ordering — highest-priority triggered criterion determines exit type.

**Priority order (highest = 1):**
1. Risk budget breach (P1) — portfolio-level safety, must override all others
2. Edge evaporation (P2) — position is losing money now
3. Liquidity deterioration (P3) — may not be able to exit later
4. Model confidence drop (P4) — predictive signal, less urgent
5. Time decay (P5) — gradual, least urgent

**Rationale for independent + priority over short-circuit:**
- Short-circuit (current pattern) prevents computing proximity for lower-priority criteria → dashboard blind spot
- Independent evaluation costs negligible additional CPU (all pure math, no I/O)
- Priority ordering preserves deterministic trigger behavior — operator always knows which criterion fired
- Weighted scoring adds tuning complexity without clear V1 benefit; can be added later by replacing the priority selector

**Rationale for priority order:**
- Risk budget breach is portfolio-level safety — a single position threatening the portfolio must exit first
- Edge evaporation means the position is actively unprofitable — worse than predictive signals
- Liquidity deterioration is a "window closing" signal — if we can't exit later, exit now
- Model confidence and time decay are predictive/gradual — less time-critical

### 2.3 Per-Criterion Proximity Calculation

Each criterion provides a `proximity: Decimal` value in [0, 1] where 0 = far from trigger, 1 = at/past trigger.

| Criterion | Proximity Formula | Dashboard Display |
|---|---|---|
| Edge evaporation | `calculateExitProximity(currentPnl, baseline, edgeEvaporationThreshold)` — reuses existing utility with the edge evaporation multiplier as target. Threshold: `entryCostBaseline + scaledInitialEdge × EXIT_EDGE_EVAP_MULTIPLIER`. Same P&L-journey pattern as current SL/TP. | "Edge: 62%" |
| Model confidence | Guard: if `entryConfidence <= 0`, return `0` (disabled — no baseline for delta measurement; division-by-zero protection). Otherwise: `triggerThreshold = entryConfidence × (1 - EXIT_CONFIDENCE_DROP_PCT / 100)`. Proximity = `1 - (currentConfidence - triggerThreshold) / (entryConfidence - triggerThreshold)`, clamped [0,1]. | "Confidence: 30%" |
| Time decay | `((horizonHours - hoursRemaining) / horizonHours)^steepness`, clamped [0,1]. See §8 for full curve specification. | "Time: 45%" |
| Risk budget | `0` if portfolio not approaching limit. Guard: if `totalPositions <= 1`, return `1` (single position carries all risk). Otherwise: `1 - (edgeRank - 1) / (totalPositions - 1)`, clamped [0,1]. Note: rank 1 = lowest edge → proximity 1; rank N = highest edge → proximity 0. | "Risk: 80%" |
| Liquidity deterioration | Absolute threshold formula (no entry-time depth capture needed — order books change too rapidly for entry snapshots to be meaningful): `max(0, 1 - availableDepth / EXIT_MIN_DEPTH)`. At `availableDepth >= EXIT_MIN_DEPTH` → proximity 0 (safe). At `availableDepth = 0` → proximity 1 (triggered). Guard: if `EXIT_MIN_DEPTH <= 0`, return `0` (disabled). `availableDepth = min(kalshiExitDepth, polymarketExitDepth)`. | "Depth: 15%" |

All use `decimal.js` for computation. All formulas include division-by-zero guards as specified above.

### 2.4 Per-Criterion Configurable Thresholds

| Criterion | Config Key | Type | Default | Location |
|---|---|---|---|---|
| Edge evaporation | `EXIT_EDGE_EVAP_MULTIPLIER` | Decimal | `-1.0` (breakeven after costs — intentionally different from current SL's `-2.0` which allows 2× edge loss before triggering; edge evaporation is a tighter, model-driven concept) | env / DB config |
| Model confidence | `EXIT_CONFIDENCE_DROP_PCT` | number | `20` (20% drop from entry) | env / DB config |
| Time decay horizon | `EXIT_TIME_DECAY_HORIZON_H` | number | `168` (7 days) | env / DB config |
| Time decay steepness | `EXIT_TIME_DECAY_STEEPNESS` | Decimal | `2.0` (quadratic) | env / DB config |
| Time decay trigger | `EXIT_TIME_DECAY_TRIGGER` | Decimal | `0.8` (80% proximity) | env / DB config |
| Risk budget approach | `EXIT_RISK_BUDGET_PCT` | number | `85` (% of limit) | env / DB config |
| Risk budget rank | `EXIT_RISK_RANK_CUTOFF` | number | `1` (bottom N positions) | env / DB config |
| Liquidity min depth | `EXIT_MIN_DEPTH` | number | `5` (contracts) | env / DB config |

**Storage:** Initially env vars (consistent with existing SL_MULTIPLIER/TP_RATIO pattern). Migration to DB-persisted config (like bankroll in 9-14) is a future enhancement.

---

## 3. Shadow Mode Comparison Mechanism

### 3.1 Dual-Evaluation Flow

Both fixed-threshold (MVP) and model-driven (five-criteria) evaluate every position every cycle. They share the same input data (no duplicate API calls).

```
evaluatePosition(position):
  input = buildEvalInput(position)         // shared data fetching

  fixedResult  = fixedEvaluator.evaluate(input)
  modelResult  = modelEvaluator.evaluate(modelInput)  // extended input

  activeResult = config.exitMode === 'model' ? modelResult : fixedResult
  shadowResult = config.exitMode === 'model' ? fixedResult : modelResult

  if (activeResult.triggered) → executeExit(position, activeResult)
  logShadowComparison(position, fixedResult, modelResult)
```

**Architecture: Strategy pattern with two evaluator implementations:**
- `FixedThresholdEvaluator` — current logic extracted (SL/TP/time-based)
- `ModelDrivenEvaluator` — five-criteria logic (new)
- Both implement a shared `IExitEvaluator` interface
- `ThresholdEvaluatorService` becomes a facade that delegates to both

This avoids the "two evaluator instances" complexity — a single service manages both strategies internally.

**Error handling:** Each evaluator call is independently try-caught. If the active evaluator throws, no exit occurs (same as current behavior — circuit breaker counts the failure). If only the shadow evaluator throws, the active evaluator's result still drives execution and the shadow comparison is logged as `{ error: true }`. Both evaluators throwing counts as a full evaluation failure toward the circuit breaker threshold.

### 3.2 Execution Gate

```typescript
type ExitMode = 'fixed' | 'model' | 'shadow';

// 'fixed'  — only fixed-threshold triggers execute
// 'model'  — only model-driven triggers execute
// 'shadow' — fixed-threshold executes, model-driven evaluates but only logs
```

Config: `EXIT_MODE` env var, default `'fixed'` (backward compatible).

**Precedence when both trigger simultaneously:** The active mode's result drives execution. Shadow mode's result is logged for comparison. No ambiguity — the config determines which mode is "live."

### 3.3 Diff Logging

Per-cycle comparison record emitted as `exit.shadow.comparison` event:

```typescript
interface ShadowComparisonPayload {
  positionId: PositionId;
  pairId: PairId;
  cycle: Date;
  fixed: {
    triggered: boolean;
    type?: string;
    currentPnl: string;
    proximity: { stopLoss: string; takeProfit: string; timeBased: string };
  };
  model: {
    triggered: boolean;
    triggeredCriterion?: ExitCriterion;
    currentPnl: string;
    criteria: Array<{ criterion: string; proximity: string; triggered: boolean }>;
  };
  activeModeTriggered: boolean;
  dataSource: 'websocket' | 'polling' | 'stale_fallback';
}
```

**Storage:** EventEmitter2 → `MonitoringEventConsumer` → audit log (existing pattern). Non-blocking async fan-out — never delays the next evaluation cycle.

**Retention:** Same as audit log retention policy (7 days default, pruned by cron from 9-6).

**Volume optimization:** Full-detail payloads are logged only when the two modes disagree (one triggers, other doesn't) or when any criterion proximity crosses a configurable alert threshold (e.g., > 0.7). When modes agree (both trigger or neither triggers), a compact summary is logged (triggered/not-triggered + active criterion only). This prevents excessive audit log volume with many positions (100 positions × 120 cycles/hour = 12,000 events/hour at full detail).

### 3.4 Daily Summary Aggregation

Aggregated from shadow comparison records via a scheduled task (daily cron):

```typescript
interface ShadowDailySummary {
  date: string;
  totalEvaluations: number;
  fixedTriggered: number;
  modelTriggered: number;
  bothTriggered: number;
  neitherTriggered: number;
  fixedOnlyExits: Array<{
    positionId: string;
    criterion: string;
    pnlAtTrigger: string;
  }>;
  modelOnlyExits: Array<{
    positionId: string;
    criterion: string;
    pnlAtTrigger: string;
  }>;
  cumulativePnlFixed: string;       // sum of realized P&L from fixed-triggered exits (actual or counterfactual)
  cumulativePnlModel: string;       // sum of model P&L at model's own trigger time (counterfactual from shadow logs)
  advantageModel: string;            // model cumulative - fixed cumulative
  triggerCountByCriterion: Record<ExitCriterion, number>;
}
```

**Counterfactual P&L semantics:** `cumulativePnlModel` uses the `model.currentPnl` from the first shadow log where `model.triggered=true` for that position — i.e., the P&L at the cycle when model WOULD have exited, not at the moment fixed actually exits. Similarly, `cumulativePnlFixed` uses `fixed.currentPnl` from the first shadow log where `fixed.triggered=true`. For exits by the active mode, realized P&L is used directly. This captures the true counterfactual: "what P&L would I have captured if the other mode had driven the exit decision?"

Stored in `SystemMetadata` table (existing key-value store pattern).

### 3.5 Dashboard Integration

- **Performance page:** Shadow mode comparison table (daily summaries, cumulative advantage/disadvantage chart)
- **Position cards:** Exit mode indicator badge (`Fixed` / `Model` / `Shadow`)
- **Position detail:** Per-criterion proximity bars (five horizontal bars showing 0-100% for each criterion)

---

## 4. WebSocket Data Path Integration

### 4.1 Subscription Mechanism

`IPlatformConnector.subscribeToContracts()` (from 10-0-1) is already active. ExitMonitorService uses `getClosePrice()` → `connector.getOrderBook()` which returns the latest cached book (WS-updated or poll-updated).

No additional subscription code needed — the data path is established.

### 4.2 Evaluation Trigger

**Decision: Keep `@Interval(30_000)` polling as evaluation trigger, consume WS data as source.**

At evaluation time, `getOrderBook()` returns the freshest available data (WS-updated in real-time, or poll-updated if WS stale). The polling interval determines evaluation CADENCE; WebSocket determines data FRESHNESS.

**Rationale:**
- 30s polling is a tested, stable pattern with known performance characteristics
- Event-driven evaluation on WS updates would require throttle/debounce to prevent exit churn from price jitter (prices update multiple times per second)
- The architecture decision states: "Trading cycle stays poll-based. Exit monitor gets WebSocket real-time feed." — WS provides DATA, polling provides CADENCE
- If latency reduction needed in future: reduce poll interval (simple config change) rather than event-driven (architectural change)

### 4.3 Polling Fallback

When WS data is stale (last update > `WS_STALENESS_THRESHOLD_MS`, default 60s):
1. `getOrderBook()` returns the poll-cached book (existing behavior)
2. The evaluation result carries `dataSource: 'stale_fallback'`
3. A `platform.data.fallback` event is emitted (once per position per stale period, not every cycle)
4. Dashboard shows data staleness indicator per position

**For safety-critical criterion #1 (edge evaporation):** When data source is `stale_fallback`, the **caller** (`ExitMonitorService`) applies a conservative price adjustment before building `ThresholdEvalInput` — nudges the close price by `EXIT_STALE_PRICE_PENALTY_PCT` (default 0.5%) in the unfavorable direction (lower for sell-side close, higher for buy-side close). This adjusted price is passed **only to criterion #1's edge calculation** — other criteria (especially #5 liquidity) receive raw prices to avoid distorting depth readings. The evaluator itself remains unaware of staleness adjustments, keeping it pure.

### 4.4 Data Source Tracking

`ThresholdEvalInput` extended with:
```typescript
dataSource: 'websocket' | 'polling' | 'stale_fallback';
dataFreshnessMs: number;  // age of the order book data in milliseconds
```

ExitMonitorService determines this by comparing WS last-update timestamp against current time before building eval input. The result carries `dataSource` for logging and dashboard display.

### 4.5 Dual Data Path Divergence (Team Agreement #23)

Already implemented in Story 10-0-1 with divergence monitoring. The exit monitor consumes WS-authoritative data. If divergence exceeds threshold, `platform.data.divergence` event is emitted. No additional design needed — the contract is established and enforced.

For the five-criteria evaluator specifically: criterion #1 (edge evaporation) and #5 (liquidity deterioration) are most sensitive to data freshness. Both use the `dataSource` field to qualify their results. Dashboard shows "WS" or "Poll" badges on criterion proximity indicators.

---

## 5. Interface Changes for ExitMonitorService

### 5.1 Extended `ThresholdEvalInput`

New fields added to existing interface (backward compatible — all optional with defaults):

```typescript
interface ThresholdEvalInput {
  // --- Existing fields (unchanged) ---
  initialEdge: Decimal;
  kalshiEntryPrice: Decimal;
  polymarketEntryPrice: Decimal;
  currentKalshiPrice: Decimal;
  currentPolymarketPrice: Decimal;
  kalshiSide: string;
  polymarketSide: string;
  kalshiSize: Decimal;
  polymarketSize: Decimal;
  kalshiFeeDecimal: Decimal;
  polymarketFeeDecimal: Decimal;
  resolutionDate: Date | null;
  now: Date;
  entryClosePriceKalshi?: Decimal | null;
  entryClosePricePolymarket?: Decimal | null;
  entryKalshiFeeRate?: Decimal | null;
  entryPolymarketFeeRate?: Decimal | null;

  // --- New fields for five-criteria model ---

  /** Confidence score at entry time (snapshot from ContractMatch).
   *  Null for legacy positions or if match had no score. */
  entryConfidenceScore?: number | null;

  /** Current confidence score from ContractMatch.
   *  Null if not available. */
  currentConfidenceScore?: number | null;

  /** Available exit depth on Kalshi side (contracts at close price). */
  kalshiExitDepth?: Decimal | null;

  /** Available exit depth on Polymarket side (contracts at close price). */
  polymarketExitDepth?: Decimal | null;

  /** Portfolio risk state: whether risk budget is approaching limit. */
  portfolioRiskApproaching?: boolean;

  /** Position's edge rank among all open positions (1 = lowest edge). */
  edgeRankAmongOpen?: number;

  /** Total number of open positions (for rank normalization). */
  totalOpenPositions?: number;

  /** Data source for current prices. */
  dataSource?: 'websocket' | 'polling' | 'stale_fallback';

  /** Age of the order book data in milliseconds. */
  dataFreshnessMs?: number;
}
```

### 5.2 Extended `ThresholdEvalResult`

```typescript
/** Exit criterion identifier for five-criteria model */
type ExitCriterion =
  | 'edge_evaporation'
  | 'model_confidence'
  | 'time_decay'
  | 'risk_budget'
  | 'liquidity_deterioration';

/** Per-criterion evaluation result */
interface CriterionResult {
  criterion: ExitCriterion;
  /** 0-1 proximity to trigger threshold (0 = safe, 1 = at/past trigger) */
  proximity: Decimal;
  /** Whether this criterion alone would trigger an exit */
  triggered: boolean;
  /** Criterion-specific context for logging/display */
  detail?: string;
}

interface ThresholdEvalResult {
  triggered: boolean;
  /** For fixed mode: 'stop_loss' | 'take_profit' | 'time_based'
   *  For model mode: the ExitCriterion that triggered */
  type?: 'stop_loss' | 'take_profit' | 'time_based' | ExitCriterion;
  currentEdge: Decimal;
  currentPnl: Decimal;
  capturedEdgePercent: Decimal;

  // --- New fields for five-criteria model ---

  /** Per-criterion proximity results (populated in model mode, undefined in fixed mode) */
  criteria?: CriterionResult[];

  /** Data source used for this evaluation */
  dataSource?: 'websocket' | 'polling' | 'stale_fallback';
}
```

**Backward compatibility:** All new fields are optional. Existing `FixedThresholdEvaluator` returns results without `criteria` or `dataSource`. Consumers check for field presence before accessing.

### 5.3 Evaluator Statefulness

**Decision: Evaluator remains stateless. Caller provides all inputs.**

Rationale:
- Current stateless design is simple, testable, and side-effect-free
- Criterion #2 (confidence delta) requires entry-time snapshot → store `entryConfidenceScore` on `OpenPosition` (new nullable DB column, captured at execution time in `ExecutionService`). ExitMonitorService reads current confidence from `ContractMatch.confidenceScore` and passes both values.
- Criterion #5 (depth degradation) uses absolute depth threshold, not relative to previous cycle → no previous-cycle state needed. If trend detection is desired later, it can be added as an input field (e.g., `previousCycleDepth`) provided by the caller.
- No eviction policy, no lifecycle management, no concurrency concerns

**Migration path:** If future criteria require inter-cycle state (e.g., momentum indicators), add them as explicit input fields. The evaluator never manages its own state — the caller (ExitMonitorService) is responsible for state management and can persist/cache as needed.

### 5.4 ExitMonitorService Changes

**New data-fetching responsibilities:**

```
evaluatePosition(position):
  // Existing
  1. Validate connector health
  2. Validate fill data
  3. Compute effective sizes (residual for EXIT_PARTIAL)
  4. Fetch VWAP close prices

  // New
  5. Fetch exit depth for both platforms (reuse getAvailableExitDepth)
  6. Read ContractMatch.confidenceScore from DB (via position.pair relation)
  7. Determine data source (WS vs polling) from connector health/freshness
  8. If model mode:
     a. Fetch IRiskManager.getCurrentExposure(isPaper) for risk budget check
     b. Compute edge ranking across all positions (pre-computed at cycle start)

  // Evaluation
  9. Build ThresholdEvalInput (extended)
  10. If shadow/model mode: call both evaluators
  11. Execute based on active mode's result
  12. Log shadow comparison if applicable
```

**New cycle-level pre-computation (in `evaluatePositions()`):**

For criterion #4 (risk budget breach), ExitMonitorService pre-computes a per-position edge ranking before the position loop:

```typescript
// Pre-compute edge ranking for risk budget criterion
const exposure = this.riskManager.getCurrentExposure(isPaper);
const portfolioRiskApproaching =
  exposure.totalCapitalDeployed.div(exposure.bankrollUsd).gte(RISK_BUDGET_APPROACH_PCT);

let edgeRanking: Map<string, number> | undefined;
if (portfolioRiskApproaching) {
  // Sort positions by expectedEdge ascending (lowest = rank 1)
  // Note: after Story 10.1, replace expectedEdge with recalculated current edge
  const sorted = [...positions].sort((a, b) =>
    new Decimal(a.expectedEdge.toString()).cmp(new Decimal(b.expectedEdge.toString()))
  );
  // Dense ranking: ties get same rank, next unique value gets rank+1 (not i+1)
  // Example: edges [5, 5, 10] → ranks [1, 1, 2] (not competition ranking [1, 1, 3])
  let rank = 1;
  const ranking = new Map<string, number>();
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0) {
      const prev = new Decimal(sorted[i - 1]!.expectedEdge.toString());
      const curr = new Decimal(sorted[i]!.expectedEdge.toString());
      if (!curr.eq(prev)) rank++;
    }
    ranking.set(sorted[i]!.positionId, rank);
  }
  edgeRanking = ranking;
}
```

This is computed once per cycle, not per position.

**Result consumption changes:**
- `executeExit()` already receives `evalResult` and is criteria-agnostic — no changes needed
- `ExitTriggeredEvent` emission: `evalResult.type!` already carries the exit type (new criterion names are valid union members)
- Shadow comparison logging: new async event emission after evaluation

### 5.5 ExitTriggeredEvent.exitType Expansion

```typescript
class ExitTriggeredEvent {
  exitType:
    // Fixed-threshold mode types (existing)
    | 'take_profit'
    | 'stop_loss'
    | 'time_based'
    | 'manual'
    // Model-driven mode types (new)
    | 'edge_evaporation'
    | 'model_confidence'
    | 'time_decay'
    | 'risk_budget'
    | 'liquidity_deterioration';
}
```

**Consumer impact assessment:**

| Consumer | Current Handling | Change Needed |
|---|---|---|
| `MonitoringEventConsumer` (audit log) | Logs `exitType` as string | No change (new strings logged as-is) |
| `TelegramFormatterService` | Formats exit alerts with type label | Add emoji/label mappings for 5 new types |
| Dashboard WebSocket gateway | Passes `exitType` to frontend | No change (string passthrough) |
| Dashboard frontend (position cards) | Displays exit type badge | Add icon/color mappings for 5 new types |
| CSV trade logging | Includes `exitType` in export | No change (string column) |

**Backward compatibility:** Existing types (`stop_loss`, `take_profit`, `time_based`, `manual`) remain unchanged. They are used when `EXIT_MODE = 'fixed'`. New types are used when `EXIT_MODE = 'model'`. No consumer breaks — all handle string values dynamically.

### 5.6 Dashboard Enrichment Data Flow

`PositionEnrichmentService.enrich()` currently replicates SL/TP proximity math. With five criteria, replicating the evaluator logic in the enrichment service would require new dependencies (DB confidence score, risk state, depth data) and duplicated business logic.

**Decision: Persist latest evaluation result, enrichment service reads it.**

ExitMonitorService persists the latest `CriterionResult[]` array after each evaluation cycle:
- **Storage:** New `lastEvalCriteria` JSON column on `OpenPosition` (nullable, Prisma migration in Story 10.2). Contains serialized `CriterionResult[]`.
- **Write path:** ExitMonitorService writes after every `evaluate()` call (triggered or not) — dashboard always shows current proximity.
- **Read path:** `PositionEnrichmentService.enrich()` reads `lastEvalCriteria` and deserializes. No evaluator logic needed.
- **Fixed mode:** `lastEvalCriteria` is `null` — enrichment service falls back to existing SL/TP proximity math (backward compatible).
- **Staleness:** If a position hasn't been evaluated in > 2 cycles (60s), enrichment service marks proximity data as stale for dashboard display.

This avoids logic duplication, keeps enrichment service dependencies unchanged, and provides near-real-time proximity data (≤30s old).

---

## 6. EXIT_PARTIAL Position Handling

Each criterion's behavior with residual (partially-exited) positions:

| Criterion | EXIT_PARTIAL Behavior | Notes |
|---|---|---|
| **Edge evaporation** | Uses residual sizes for P&L calculation. Entry cost baseline recomputed for residual sizes (existing pattern in `evaluatePosition()` lines 195-263). | No change from current SL — residual size handling already works |
| **Model confidence** | Confidence delta applies to the match, not the position size. No special handling needed. | Same confidence score regardless of how much is exited |
| **Time decay** | Resolution date is match-level, not position-level. No special handling needed. | Same time pressure regardless of residual size |
| **Risk budget breach** | Edge ranking uses `currentEdge` directly — this is already a per-contract metric (`currentPnl / legSize`), so positions of different sizes are naturally normalized. No additional per-unit division needed. | Fair comparison across positions regardless of residual size |
| **Liquidity deterioration** | Depth check uses residual size as the target executable amount (already the behavior — `getAvailableExitDepth` receives effective size). | Smaller residual = easier to exit = less liquidity pressure |

No architectural changes needed — the existing residual-size pattern in `evaluatePosition()` naturally extends to all five criteria.

---

## 7. Risk Budget Breach — Cross-Position Logic

**Design:**

1. **ExitMonitorService** pre-computes edge ranking at cycle start (see §5.4)
2. `portfolioRiskApproaching` is `true` when `totalCapitalDeployed / bankrollUsd >= EXIT_RISK_BUDGET_PCT` (default 85%)
3. When approaching, positions are ranked by edge ascending (lowest edge = rank 1 = first to exit)
   - **Before Story 10.1:** ranking uses `expectedEdge` from `OpenPosition` (static entry-time edge). This is the best available signal — it reflects opportunity quality at entry.
   - **After Story 10.1:** ranking should use recalculated current edge (dynamic). Story 10.1 will persist recalculated edge per position, and the ranking code here should be updated to consume it. This is explicitly noted as a Story 10.2 implementation decision informed by 10.1's availability.
4. `edgeRank` and `totalOpenPositions` passed as input to evaluator
5. Criterion #4 triggers when: `portfolioRiskApproaching && edgeRank <= EXIT_RISK_RANK_CUTOFF` (default: 1 = only the single worst position)

**Why evaluator stays isolated:**
- Evaluator receives pre-computed `portfolioRiskApproaching`, `edgeRank`, and `totalOpenPositions` as inputs
- No access to `IRiskManager` or other positions — stays stateless and testable
- The ranking logic lives in ExitMonitorService where it can access all positions in the current cycle

**Edge case — multiple positions at same rank:**
- If multiple positions have identical `currentEdge`, they all receive the same rank
- With `EXIT_RISK_RANK_CUTOFF = 1`, all tied-for-worst positions trigger simultaneously
- This is correct behavior — if risk budget is stressed and multiple positions are equally poor, exiting all of them is the right safety response

---

## 8. Time Decay Curve

**Current:** Binary 48h threshold (`hoursRemaining <= 48 → triggered`).

**Proposed:** Configurable continuous decay with quadratic default.

```typescript
function calculateTimeDecayProximity(
  hoursRemaining: number,
  horizonHours: number,     // default 168 (7 days)
  steepness: Decimal,       // default 2.0 (quadratic)
): Decimal {
  if (hoursRemaining <= 0) return new Decimal(1);
  if (hoursRemaining >= horizonHours) return new Decimal(0);

  // Quadratic (steepness=2): gentle early rise, steep near resolution
  // Linear (steepness=1): constant rate
  // Cubic (steepness=3): very gentle early, very steep late
  const normalized = new Decimal(horizonHours - hoursRemaining)
    .div(horizonHours);
  return Decimal.min(
    new Decimal(1),
    Decimal.max(new Decimal(0), normalized.pow(steepness)),
  );
}
```

**Trigger:** When `proximity >= EXIT_TIME_DECAY_TRIGGER` (default 0.8).

**Curve behavior (default steepness=2.0, horizon=168h):**

| Hours Remaining | Proximity | Triggered (at 0.8)? |
|---|---|---|
| 168 (7d) | 0.00 | No |
| 120 (5d) | 0.08 | No |
| 72 (3d) | 0.33 | No |
| 48 (2d) | 0.51 | No |
| 24 (1d) | 0.74 | No |
| 15 | 0.83 | **Yes** |
| 6 | 0.95 | **Yes** |
| 0 | 1.00 | **Yes** |

This is more gradual than the current binary 48h and provides richer dashboard information (continuous proximity bar).

**Intentional timing difference vs current 48h:** The model-driven time decay triggers at ~18h remaining (with defaults), significantly later than the current binary 48h. This is intentional — the current 48h binary is aggressive (exits 2 days before resolution regardless of P&L). The model-driven approach lets positions ride longer when other criteria (edge, confidence) are healthy. The time decay criterion works in concert with the other four criteria, not in isolation — if edge is evaporating near resolution, criterion #1 fires first. Time decay is the backstop for positions that are still healthy but running out of time.

**Backward compatibility:** When `EXIT_MODE = 'fixed'`, the existing binary 48h logic runs unchanged. The continuous curve is model-mode only.

---

## 9. Migration Path: Fixed → Model-Driven

### Phase 1: Shadow Mode (Story 10.2 implementation)
1. Deploy with `EXIT_MODE = 'shadow'` — fixed-threshold executes, model-driven evaluates silently
2. Accumulate 2+ weeks of shadow comparison data
3. Review daily summaries: compare fixed vs model P&L, trigger frequency by criterion
4. Build confidence via dashboard comparison table

### Phase 2: Model Mode
1. Switch to `EXIT_MODE = 'model'` — model-driven executes, fixed-threshold evaluates as shadow
2. Monitor for 1 week: ensure no unexpected exits, P&L tracking matches expectations
3. If issues: switch back to `'fixed'` instantly (config change, no code change)

### Phase 3: Deprecation
1. After sufficient confidence, remove `FixedThresholdEvaluator` and shadow mode
2. Clean up config, remove dead code
3. This is a future epic — not in scope for Epic 10

**Key invariant:** At every phase, `executeExit()` remains criteria-agnostic. The only thing that changes is which evaluator's `triggered` result drives the exit decision. No execution path changes during migration.

---

## 10. Risk Assessment

### What Could Go Wrong

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Model-driven exits fire prematurely on calibration edge cases | Medium | High — premature exits reduce P&L | Shadow mode validation period; EXIT_MODE config for instant rollback |
| Criterion #4 (risk budget) triggers cascading exits when multiple positions are ranked low | Low | High — mass exit event | EXIT_RISK_RANK_CUTOFF defaults to 1 (only worst position); configurable |
| Shadow mode dual evaluation exceeds 30s budget | Very Low | Medium — evaluation skips cycle | Both evaluators are pure CPU; no I/O in evaluation step; benchmark in implementation |
| New data-fetching overhead extends cycle time | Low | Medium — reduced headroom in 30s budget | §5.4 adds per-position DB read (confidence score) and per-cycle risk state query + edge ranking sort. Mitigate by bulk-fetching all confidence scores at cycle start (single query), caching risk exposure per cycle, and pre-computing edge ranking once. Benchmark total cycle time with 100+ positions during implementation. |
| New exit types break Telegram formatter or dashboard | Low | Low — display error only | All consumers handle unknown types as string passthrough; new types need formatter additions |
| Stale WS data causes incorrect edge evaporation trigger | Low | Medium — false exit | Staleness penalty (§4.3) adds conservative bias; `dataSource` tracking for audit |

### Testing Strategy Sketch

1. **Unit tests for ModelDrivenEvaluator:** Each criterion in isolation (10+ tests per criterion)
2. **Unit tests for priority ordering:** Multiple criteria triggered simultaneously → correct priority wins
3. **Integration tests for shadow mode:** Both evaluators produce results, correct one drives execution
4. **Integration tests for ExitMonitorService:** Edge ranking computation, model input construction
5. **Dual-path tests:** `EXIT_MODE = 'fixed'` produces identical results to current implementation (regression)
6. **Paper/live boundary tests:** Both evaluator modes work correctly in paper mode
7. **Property-based tests:** Random inputs → evaluator never crashes, proximity always in [0,1]

---

## 11. Story Dependency Map

```
10-0-1 (WS subscriptions) ──DONE──┐
                                   ├── 10.1 (Continuous Edge Recalculation)
10-0-3 (this spike) ──────────────┤      ↓ uses recalculated edge
                                   ├── 10.2 (Five-Criteria Model-Driven Exit Logic)
10-0-2 (debt fixes) ──DONE────────┘      ↓ uses SingleLegContext
                                   └── 10.3 (Automatic Single-Leg Management)

10.4 (Adaptive Leg Sequencing) — independent of exit criteria changes
```

**What this spike informs for 10.1:**
- Data source tracking (`dataSource` field) — 10.1 implements the WS/polling freshness detection
- `ThresholdEvalInput` extension pattern — 10.1 adds recalculated edge fields
- Dashboard display of data source indicator — 10.1 implements the frontend badge

**What this spike informs for 10.2:**
- Five-criterion composition with priority ordering — 10.2 implements `ModelDrivenEvaluator`
- Shadow mode dual-evaluation flow — 10.2 implements the strategy pattern facade
- `CriterionResult[]` array in eval result — 10.2 implements per-criterion proximity
- Daily summary aggregation — 10.2 implements the cron job
- `ExitTriggeredEvent.exitType` expansion — 10.2 extends the union

**What this spike informs for 10.3:**
- No direct dependency. SingleLegContext refactor (10-0-2) is the enabler for 10.3.

---

## Appendix A: Illustrative Type Signatures

> **Note:** These are design-time type signatures for communication. They are NOT production code and may evolve during implementation.

```typescript
// --- Strategy interface ---
interface IExitEvaluator {
  evaluate(input: ThresholdEvalInput): ThresholdEvalResult;
}

// --- Exit criterion enum ---
type ExitCriterion =
  | 'edge_evaporation'
  | 'model_confidence'
  | 'time_decay'
  | 'risk_budget'
  | 'liquidity_deterioration';

// --- Per-criterion result ---
interface CriterionResult {
  criterion: ExitCriterion;
  proximity: Decimal;
  triggered: boolean;
  detail?: string;
}

// --- Shadow comparison event payload ---
interface ShadowComparisonPayload {
  positionId: PositionId;
  pairId: PairId;
  cycle: Date;
  fixed: {
    triggered: boolean;
    type?: string;
    currentPnl: string;
    proximity: { stopLoss: string; takeProfit: string; timeBased: string };
  };
  model: {
    triggered: boolean;
    triggeredCriterion?: ExitCriterion;
    currentPnl: string;
    criteria: CriterionResult[];
  };
  activeModeTriggered: boolean;
  dataSource: 'websocket' | 'polling' | 'stale_fallback';
}

// --- Exit mode config ---
type ExitMode = 'fixed' | 'model' | 'shadow';

// --- Time decay function (pure, decimal.js) ---
function calculateTimeDecayProximity(
  hoursRemaining: number,
  horizonHours: number,
  steepness: Decimal,
): Decimal;
```

## Appendix B: Config Summary

| Config Key | Type | Default | Purpose |
|---|---|---|---|
| `EXIT_MODE` | `'fixed' \| 'model' \| 'shadow'` | `'fixed'` | Active exit evaluation strategy |
| `EXIT_EDGE_EVAP_MULTIPLIER` | Decimal | `-1.0` | Edge evaporation trigger (× initial edge) |
| `EXIT_CONFIDENCE_DROP_PCT` | number | `20` | Confidence drop threshold (%) |
| `EXIT_TIME_DECAY_HORIZON_H` | number | `168` | Time decay horizon (hours) |
| `EXIT_TIME_DECAY_STEEPNESS` | Decimal | `2.0` | Time decay curve steepness |
| `EXIT_TIME_DECAY_TRIGGER` | Decimal | `0.8` | Time decay proximity trigger threshold |
| `EXIT_RISK_BUDGET_PCT` | number | `85` | Risk budget approach threshold (%) |
| `EXIT_RISK_RANK_CUTOFF` | number | `1` | Bottom-N positions to exit on risk breach |
| `EXIT_MIN_DEPTH` | number | `5` | Minimum exit depth (contracts) |
| `WS_STALENESS_THRESHOLD_MS` | number | `60000` | WS data staleness threshold |
| `EXIT_STALE_PRICE_PENALTY_PCT` | Decimal | `0.5` | Conservative adjustment for stale data |
