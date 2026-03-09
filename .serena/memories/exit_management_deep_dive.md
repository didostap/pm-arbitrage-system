# Exit Management Module — Deep Dive Investigation

## Overview
The exit-management module handles automated position unwinding when exit thresholds are triggered. It operates on 30-second polling cycles and manages both full and partial exit scenarios.

---

## 1. Exit Execution Flow

### Single-Leg Exit Failure Scenario
When one leg fills but the other fails during exit, the system follows these steps:

1. **Primary Leg Submission** (lines 379-414 in exit-monitor.service.ts):
   - Submit primary leg exit order
   - If submission fails or order doesn't fill → position stays OPEN, retry next cycle
   - On success → persist primary exit order

2. **Secondary Leg Submission** (lines 430-470):
   - Submit secondary leg (using same exitSize for cross-leg equalization)
   - If submission fails OR order doesn't fill → call `handlePartialExit()`

3. **handlePartialExit() Flow** (lines 741-838):
   - Position status → EXIT_PARTIAL (not SINGLE_LEG_EXPOSED)
   - Emits SINGLE_LEG_EXPOSURE event with full context
   - Includes filled order data, failed order data, and current book prices
   - Provides P&L scenarios and recommended actions in event
   - Logs error with both leg details

### Full Exit vs Partial Exit Determination (lines 555-558)
- Full exit: BOTH kalshi exit fill size >= entry fill size AND polymarket exit fill size >= entry fill size
- Partial exit: If EITHER leg fill size < entry fill size
- Note: Even if both legs return `partial` status, as long as both filled enough, it's still a full exit

### P&L Calculation for Exits (lines 486-549)
```
Per-leg P&L = (exit filled price - entry price) × exit filled quantity
Exit fees = exit filled price × exit filled quantity × taker fee rate
Realized P&L = kalshi P&L + polymarket P&L - exit fees
Capital returned = exited entry capital + realized P&L
```

---

## 2. EXIT_PARTIAL Status — What Happens

### When Position Enters EXIT_PARTIAL
1. Position record updated to status = 'EXIT_PARTIAL'
2. Capital released via `riskManager.releasePartialCapital()` for the exited portion
3. Position is NOT removed from open position tracking
4. Position remains in database for operator intervention

### Risk Manager Behavior During EXIT_PARTIAL (risk-manager.service.ts, lines 977-1016)
Key: `pairId` parameter is **intentionally ignored** during partial exit
```
- totalCapitalDeployed is decremented by exited capital
- openPositionCount is NOT decremented
- paperActivePairIds Set is NOT modified
- Position still occupies a position slot
- Capital allocation happens ONLY for exited portion
```
This is critical: EXIT_PARTIAL positions remain "open" in risk management until fully closed.

### SINGLE_LEG_EXPOSURE Event During EXIT_PARTIAL (lines 643-693)
When partial exit occurs, a `SingleLegExposureEvent` is emitted with:
- `filledLeg`: Platform, orderId, side, prices, actual fill sizes
- `failedLeg`: Platform, reason, reasonCode (PARTIAL_EXIT_FAILURE = code 2003), attempted prices
- `currentPrices`: bestBid/bestAsk for both platforms (or null if fetch failed)
- `pnlScenarios`: Three human-readable strings
  - `closeNowEstimate`
  - `retryAtCurrentPrice`
  - `holdRiskAssessment`
- `recommendedActions`: Array of action strings, always includes:
  - "Retry exit via POST /api/positions/:id/retry-leg"
  - "Close remaining via POST /api/positions/:id/close-leg"

---

## 3. Retry Mechanism (POST /api/positions/:id/retry-leg)

### Entry Point
- Controller: `single-leg-resolution.controller.ts`, lines 40-58
- Service: `single-leg-resolution.service.ts`, lines 65-234

### Retry Preconditions (lines 78-87)
- Position status must be SINGLE_LEG_EXPOSED or EXIT_PARTIAL
- Accepts a single parameter: `price` (decimal 0-1, required)

### Retry Logic Flow
1. Get position with pair details
2. Identify failed platform (the one with null orderId)
3. Get connector, contract ID, side, and position size from failed platform
4. Determine if paper/mixed mode from connector health
5. Submit order at requested price to failed platform
6. On fill or partial fill:
   - Create new order record
   - Update position: status = OPEN, link new order to failed platform
   - Calculate new edge = |entryFillPrice - retryFilledPrice|
   - Emit ORDER_FILLED event
   - Emit SINGLE_LEG_RESOLVED event (resolutionType = 'retried')
   - Return: { success: true, orderId, newEdge }
7. On no fill:
   - Do NOT update position status
   - Return: { success: false, reason, pnlScenarios, recommendedActions }

### Retry Success → Position Transitions Back to OPEN
Key: Once retry leg fills, position returns to OPEN status and can be picked up by exit manager in next cycle

### Retry Failure → Provides Guidance
Returns current P&L scenarios and recommended actions if retry order doesn't fill.

---

## 4. Close Leg Mechanism (POST /api/positions/:id/close-leg)

### Entry Point
- Controller: `single-leg-resolution.controller.ts`, lines 60-78
- Service: `single-leg-resolution.service.ts`, lines 236-443

### Close Preconditions (lines 249-258)
- Position status must be SINGLE_LEG_EXPOSED or EXIT_PARTIAL
- Accepts optional parameter: `rationale` (string, max 500 chars)

### Close Logic Flow
1. Get position with pair details
2. Identify filled platform (the one with non-null orderId)
3. Get connector, contract ID, and filled side
4. Fetch current order book for filled platform
5. Determine close price:
   - If filled side was BUY → close side is SELL → use best bid
   - If filled side was SELL → close side is BUY → use best ask
   - Throws CLOSE_FAILED (severity: warning, http 422) if empty side
6. Submit close order at best price, fill size = original filled quantity
7. On fill or partial fill:
   - Create close order record
   - Calculate P&L: (closeFillPrice - entryFillPrice) × qty - fee
   - Update position status → CLOSED
   - Release full capital via `riskManager.closePosition()`
   - Emit SINGLE_LEG_RESOLVED event (resolutionType = 'closed')
   - Return: { success: true, closeOrderId, realizedPnl }
8. On no fill:
   - Throws CLOSE_FAILED (severity: error, http 502)

### Close Success → Position Fully Closed
Position moves to CLOSED status, capital released, position slot freed.

---

## 5. Single-Leg Exposure Event During Exit Failures

### Fired By
- `handlePartialExit()` when primary leg fills but secondary fails
- During partial exit when exit fill sizes don't match entry sizes

### Event Structure
```typescript
SingleLegExposureEvent {
  positionId: string,
  pairId: string,
  expectedEdge: number,
  filledLeg: {
    platform: PlatformId,           // KALSHI or POLYMARKET
    orderId: string,
    side: 'buy' | 'sell',
    price: number,
    size: number,
    fillPrice: number,
    fillSize: number
  },
  failedLeg: {
    platform: PlatformId,
    reason: string,                 // Error message or "Partial exit — remainder contracts unexited"
    reasonCode: number,             // EXECUTION_ERROR_CODES.PARTIAL_EXIT_FAILURE = 2003
    attemptedPrice: number,
    attemptedSize: number
  },
  currentPrices: {
    kalshi: { bestBid: number | null, bestAsk: number | null },
    polymarket: { bestBid: number | null, bestAsk: number | null }
  },
  pnlScenarios: {
    closeNowEstimate: string,
    retryAtCurrentPrice: string,
    holdRiskAssessment: string
  },
  recommendedActions: string[],     // Including retry-leg and close-leg endpoints
  correlationId?: string,
  isPaper: boolean,
  mixedMode: boolean
}
```

### Reason Codes
- PARTIAL_EXIT_FAILURE = 2003: One leg filled, other partially/failed during exit
- Reason strings always guide operator to use POST endpoints

---

## 6. Retry Mechanism Within Exit Manager

### Automatic Retries
Exit manager does NOT automatically retry failed exit legs. Instead:
- First exit attempt fails → position stays OPEN
- Operator decides via HTTP endpoint or system waits for next polling cycle
- Next cycle re-evaluates and may re-attempt

### Circuit Breaker Pattern (lines 35-36, 118-129)
- Tracks consecutive full evaluation failures
- After 3 consecutive full failures, skips next cycle to prevent spam
- Resets on first success

### No Implicit Retry Loop
Design principle: Exit execution is synchronous decision-making, not auto-retry

---

## 7. Critical Data Flow for EXIT_PARTIAL

```
Exit Manager evaluates position → threshold triggered
    ↓
Evaluates both legs for available depth
    ↓
Submits primary leg → fills (or partial)
    ↓
Submits secondary leg → FAILS or incomplete fill
    ↓
handlePartialExit() called
    ↓
Position: OPEN → EXIT_PARTIAL
Risk: releasePartialCapital() for exited portion (NOT closing position)
    ↓
SINGLE_LEG_EXPOSURE event emitted with full context
    ↓
Monitoring/Dashboard receives event
Operator sees remediation endpoints in recommended actions
    ↓
Operator calls POST /api/positions/:id/retry-leg OR close-leg
    ↓
Position: EXIT_PARTIAL → (OPEN if retry fills) OR (CLOSED if close succeeds)
```

---

## 8. Position Status Lifecycle

```
OPEN
  ↓
[Exit threshold triggers] → Primary leg fails → OPEN (retry next cycle)
[Exit threshold triggers] → Primary + Secondary both fill/partial → Check fill sizes
  ├─ Both fills >= entry → CLOSED
  └─ Any fill < entry → EXIT_PARTIAL
      ↓ [Operator action needed]
      ├─ retry-leg succeeds → OPEN
      ├─ retry-leg fails → EXIT_PARTIAL (unchanged)
      ├─ close-leg succeeds → CLOSED
      └─ close-leg fails → ERROR (2502)

SINGLE_LEG_EXPOSED
  ↓ [Via single-leg-resolution endpoints]
  ├─ retry-leg succeeds → OPEN
  ├─ close-leg succeeds → CLOSED
```

---

## 9. Key Implementation Files

### Core Exit Logic
- `/src/modules/exit-management/exit-monitor.service.ts` (873 lines)
  - `evaluatePositions()` — polling loop (30s interval)
  - `evaluatePosition()` — threshold evaluation
  - `executeExit()` — primary/secondary submission, full vs partial determination
  - `handlePartialExit()` — partial exit handling

- `/src/modules/exit-management/threshold-evaluator.service.ts` (213 lines)
  - `evaluate()` — stop-loss (priority 1), take-profit (priority 2), time-based (priority 3)
  - Considers entry cost baseline (6.5.5i) for threshold offset

### Operator Intervention
- `/src/modules/execution/single-leg-resolution.controller.ts` (140 lines)
  - POST :id/retry-leg
  - POST :id/close-leg

- `/src/modules/execution/single-leg-resolution.service.ts` (597 lines)
  - `retryLeg()` — retry failed leg
  - `closeLeg()` — close filled leg via best available price
  - `buildPnlScenarios()` — calculate scenarios for guidance

### Position & Risk Management
- `/src/persistence/repositories/position.repository.ts` — updateStatus()
- `/src/modules/risk-management/risk-manager.service.ts` — closePosition(), releasePartialCapital()

---

## 10. Scenario Examples

### Scenario A: Kalshi Fills, Polymarket Fails During Exit
1. Exit triggered, kalshi fills at 0.55, polymarket submission fails
2. handlePartialExit() → position EXIT_PARTIAL
3. SINGLE_LEG_EXPOSURE emitted: filledLeg=KALSHI(0.55), failedLeg=POLYMARKET(error)
4. Operator receives event with "Retry via POST /api/positions/:id/retry-leg"
5. Operator calls retry-leg with price=0.54
6. Polymarket fills at 0.54 → position OPEN
7. Next exit cycle picks up and re-evaluates

### Scenario B: Both Legs Partially Fill, But Kalshi More Than Polymarket
1. Exit triggered, kalshi fills 80% at 0.55, polymarket fills 30% at 0.54
2. kalshiExitFillSize (80%) >= kalshiFillSize (100%)? No → partial exit
3. polymarketExitFillSize (30%) >= polymarketFillSize (100%)? No → partial exit
4. Position → EXIT_PARTIAL
5. Operator calls close-leg → closes polymarket at best bid (say 0.53)
6. Position CLOSED, realized PnL includes both partial fills

### Scenario C: Primary Leg Fails, Never Gets Secondary
1. Exit triggered, primary leg submission fails immediately
2. No handlePartialExit() → position stays OPEN
3. Next cycle (30s later) re-evaluates
4. If threshold still active, retries primary

---

## 11. Non-Implemented / Not Directly Related

- Global exception filter (mentioned in CLAUDE.md as not yet implemented)
- Interceptors (mentioned in CLAUDE.md as not yet implemented)
- Dashboard SPA event subscription (separate repo, pm-arbitrage-dashboard)

---

## 12. Summary: Exit Execution Resilience

**When one leg fills but other fails:**
- Position persists with partial execution marked in database
- Capital is partially released (proportional to exited amount)
- Operator receives detailed event with remediation paths
- Two clear next steps: retry or close (not auto-resolved)
- Position tracking maintains open slot until full resolution

**No automatic retry loop:**
- By design, exit manager doesn't spin-retry on single failure
- Relies on polling cycle + operator action or market conditions improving
- Circuit breaker prevents spam after 3 consecutive full failures

**EXIT_PARTIAL is a stable intermediate state:**
- Not an error state, but a real position status
- Requires human intervention or market condition improvement
- Both retry-leg and close-leg are valid remediation endpoints
