# Execution & Persistence Patterns

## 1. Prisma Schema (8 models, 3 enums)

### Enums
- `Platform`: KALSHI | POLYMARKET
- `OrderStatus`: PENDING | FILLED | PARTIAL | REJECTED | CANCELLED
- `PositionStatus`: OPEN | SINGLE_LEG_EXPOSED | EXIT_PARTIAL | CLOSED | RECONCILIATION_REQUIRED

### Models
| Model | Key Fields | Purpose |
|-------|-----------|---------|
| SystemMetadata | key, value | Generic key-value store |
| OrderBookSnapshot | platform, contract_id, bids(JSON), asks(JSON), sequence_number | Audit trail (7yr retention) |
| PlatformHealthLog | platform, status, response_time_ms, connection_state | Health observability |
| ContractMatch | polymarketContractId, kalshiContractId, operatorApproved, primaryLeg, resolutionDate | Cross-platform pair tracking |
| RiskState | singletonKey("default"), dailyPnl, openPositionCount, totalCapitalDeployed, tradingHalted | Risk state singleton |
| Order | platform, contractId, pairId, side, price, size, status, fillPrice, fillSize | Order lifecycle |
| OpenPosition | pairId, poly/kalshiOrderId, poly/kalshiSide, entryPrices(JSON), sizes(JSON), expectedEdge, status, reconciliationContext(JSON) | Position lifecycle |
| RiskOverrideLog | opportunityId, rationale, approved, originalRejectionReason | Override audit trail |

### Key Relations
- ContractMatch → Order[] (1:many)
- ContractMatch → OpenPosition[] (1:many)
- Order → OpenPosition via "PolymarketOrder"/"KalshiOrder" named relations

## 2. Repository Patterns

### PositionRepository Methods
- `create(data)`, `findById(id)`, `findByPairId(pairId)`
- `findByStatus(status)`, `findByStatusWithPair(status)` — includes ContractMatch
- `findByStatusWithOrders(status)` — includes pair + both orders (for P&L calc)
- `findByIdWithPair(id)`, `updateStatus(id, status)`, `updateWithOrder(id, data)`

### OrderRepository Methods
- `create(data)`, `findById(id)`, `findByPairId(pairId)`, `updateStatus(id, status)`

Pattern: Specialized query methods with explicit `include` clauses to prevent N+1 queries.

## 3. Position State Machine
```
OPEN ──(single-leg failure)──> SINGLE_LEG_EXPOSED
SINGLE_LEG_EXPOSED ──(retry success)──> OPEN
SINGLE_LEG_EXPOSED ──(close)──> CLOSED
SINGLE_LEG_EXPOSED ──(exit timeout)──> EXIT_PARTIAL
EXIT_PARTIAL ──(retry)──> OPEN
EXIT_PARTIAL ──(close)──> CLOSED
Any ──(reconciliation issue)──> RECONCILIATION_REQUIRED
```

## 4. Execution Flow

### ExecutionService.execute(opportunity, reservation)
1. Verify depth on primary platform
2. Submit + fill primary leg
3. Persist primary order to DB
4. Verify depth on secondary platform
5. If depth fails → `handleSingleLeg()` (SINGLE_LEG_EXPOSED)
6. Submit + fill secondary leg
7. If secondary fails → `handleSingleLeg()`
8. Both succeed → persist orders + create OpenPosition(status: OPEN)
9. Emit OrderFilledEvent for both legs

### ExecutionQueueService.processOpportunities(opportunities)
For each: acquire lock → reserveBudget → execute → commit/release reservation

### SingleLegResolutionService
- `retryLeg(positionId, retryPrice)` — submit on failed platform, return new edge + P&L scenarios
- `closeLeg(positionId)` — close filled leg at market, calculate realized P&L, transition to CLOSED

### ExposureTrackerService
Tracks weekly/monthly single-leg exposure counts. Thresholds: WEEKLY_CONSECUTIVE_THRESHOLD, MONTHLY_THRESHOLD.

### ExposureAlertScheduler
Periodic re-emit of SingleLegExposureEvent for unresolved positions.

## 5. Risk Management Flow
- `reserveBudget()` — atomic capital reservation
- `commitReservation()` — finalize after execution success/partial
- `releaseReservation()` — return capital on full failure
- `validatePosition()` — pre-execution risk check
- `processOverride()` — operator override with audit logging
- `haltTrading()`/`resumeTrading()` — halt reasons: DAILY_LOSS_LIMIT, RECONCILIATION_DISCREPANCY
- State persisted to RiskState singleton in DB

## 6. Reconciliation
- `StartupReconciliationService.reconcile()` — run on boot via EngineLifecycleService
- Checks: active positions vs platform state, pending orders vs fill status
- Discrepancies tracked with `reconciliationContext` JSON on OpenPosition
- `ReconciliationController`: GET /status, POST /run, POST /resolve

## 7. Event Catalog (30 events)
Key events: ORDER_FILLED, SINGLE_LEG_EXPOSURE, SINGLE_LEG_EXPOSURE_REMINDER, SINGLE_LEG_RESOLVED, EXIT_TRIGGERED, EXECUTION_FAILED, BUDGET_RESERVED/COMMITTED/RELEASED, OPPORTUNITY_IDENTIFIED/FILTERED, LIMIT_APPROACHED/BREACHED, PLATFORM_HEALTH_*, RECONCILIATION_*, SYSTEM_*, TIME_DRIFT_*, OVERRIDE_*, ORDERBOOK_UPDATED, DEGRADATION_PROTOCOL_*

## 8. Financial Math
All calculations use `decimal.js` Decimal type via `FinancialMath` class:
- `calculateGrossEdge(priceA, priceB)`
- `calculateNetEdge(priceA, priceB, feeA, feeB, gasEstimate, positionSize)`
- `isAboveThreshold(edge, threshold)`
- `validateDecimalInput()` / `validateNumberInput()`

Prisma Decimal → decimal.js: `new Decimal(value.toString())`
