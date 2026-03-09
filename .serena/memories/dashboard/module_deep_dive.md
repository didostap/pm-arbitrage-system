# Dashboard Module Deep Investigation (March 8, 2026)

## 1. Module Definition (dashboard.module.ts)

**Imports:**
- DataIngestionModule (for price feed service)

**Controllers:**
- DashboardController
- MatchApprovalController
- PerformanceController
- NOTE: No PositionManagementController exists

**Providers:**
- DashboardGateway (WebSocket server)
- DashboardEventMapperService (event → DTO mapper)
- DashboardService (core business logic)
- PositionEnrichmentService (P&L enrichment)
- MatchApprovalService (contract match approval/rejection)
- PerformanceService (analytics/trends)

## 2. DashboardController — Endpoints

**Base path:** `/dashboard`
**All endpoints:** Guarded with AuthTokenGuard + Swagger docs

**GET /dashboard/overview**
- Returns: OverviewResponseDto
- Data: systemHealth, trailingPnl7d, executionQualityRatio, openPositionCount, activeAlertCount

**GET /dashboard/health**
- Returns: HealthListResponseDto (PlatformHealthDto[])
- Per-platform status, connectivity, dataFresh flag, mode (live/paper)

**GET /dashboard/positions** (PAGINATED)
- Query params: mode ('live' | 'paper' | 'all'), page (default 1), limit (default 50, max 200)
- Returns: PositionListResponseDto
- Fields: PositionSummaryDto[] with full enrichment

**GET /dashboard/positions/:id**
- Returns: PositionDetailResponseDto (single PositionSummaryDto)
- Fully enriched position data
- Throws NOT_FOUND (404) if position not found

**GET /dashboard/alerts**
- Returns: AlertListResponseDto (AlertSummaryDto[])
- Currently only returns single_leg_exposure alerts (SINGLE_LEG_EXPOSED status)

## 3. DashboardService — Methods

**getOverview()** → DashboardOverviewDto
- Queries last 7d closed positions, aggregates expectedEdge sum
- Computes execution quality ratio (filled/total orders)
- Calls getLatestHealthLogs() + computeCompositeHealth()
- Uses Decimal for financial math

**getHealth()** → PlatformHealthDto[]
- Fetches latest health logs for each platform (distinct)
- Maps platform mode from config (PLATFORM_MODE_KALSHI, PLATFORM_MODE_POLYMARKET)
- Returns: platformId, status (healthy|degraded|disconnected), apiConnected, dataFresh, lastUpdate, mode

**getPositions(mode?, page, limit)** → { data: PositionSummaryDto[], count: number }
- Filters by status: OPEN, SINGLE_LEG_EXPOSED, EXIT_PARTIAL
- Optional mode filter (isPaper field)
- **CRITICAL:** Enriches positions in BATCHES (batch size 10) to avoid overwhelming connectors
- Calls enrichmentService.enrich(pos) for each position
- Logs partial/failed enrichment warnings, continues anyway

**getPositionById(positionId)** → PositionSummaryDto | null
- Single position query with enrichment
- Returns null if not found (controller throws 404)

**getAlerts()** → AlertSummaryDto[]
- Currently hardcoded: only SINGLE_LEG_EXPOSED positions
- Returns: id, type: 'single_leg_exposure', severity: 'critical', message, timestamp, acknowledged: false

## 4. PositionEnrichmentService — P&L Enrichment

**Injects:** IPriceFeedService (via PRICE_FEED_SERVICE_TOKEN)

**enrich(position)** → EnrichmentResult
```
{
  status: 'enriched' | 'partial' | 'failed'
  data: EnrichedPosition
  errors?: string[]
}
```

**EnrichedPosition fields:**
- currentPrices: { kalshi: string|null, polymarket: string|null }
- currentEdge: string|null (edge per unit = currentPnl / legSize)
- unrealizedPnl: string|null (USD value)
- exitProximity: { stopLoss: string, takeProfit: string }|null (0-1 scale)
- resolutionDate: string|null (ISO)
- timeToResolution: string|null (e.g., "2d 5h")

**Calculation logic:**
1. Fetch current close prices via priceFeed.getCurrentClosePrice()
2. Extract Decimal entry prices/sizes from orders
3. Calculate per-leg P&L using calculateLegPnl()
4. Subtract exit fees (price × size × feeRate)
5. Compute currentEdge = totalPnl / legSize (per-unit edge)
6. Compute entry cost baseline (FinancialMath.computeEntryCostBaseline)
7. Compute exit proximity (0-1 range) for stop-loss and take-profit thresholds
8. Use 8 decimal places (.toFixed(8)) for all Decimal → string conversions

**Failure modes:**
- Missing order fill data → failed
- Missing side data → failed
- Either price unavailable → partial (log warning)
- Both prices unavailable → failed

## 5. DashboardGateway — WebSocket Real-Time Updates

**Path:** `/ws`
**Auth:** Token via URL query param (?token=...)

**Event handlers (all async fan-out):**

1. @OnEvent(PLATFORM_HEALTH_UPDATED|DEGRADED|RECOVERED)
   - Broadcasts: WS_EVENTS.HEALTH_CHANGE (WsHealthChangePayload)

2. @OnEvent(ORDER_FILLED)
   - Broadcasts: WS_EVENTS.EXECUTION_COMPLETE (WsExecutionCompletePayload, status='filled')

3. @OnEvent(EXECUTION_FAILED)
   - Broadcasts: WS_EVENTS.EXECUTION_COMPLETE (status='failed')

4. @OnEvent(SINGLE_LEG_EXPOSURE)
   - Broadcasts: WS_EVENTS.ALERT_NEW (WsAlertNewPayload)
   - Message: `Single-leg exposure on position X: [platform] leg failed (reason)`

5. @OnEvent(LIMIT_BREACHED)
   - Broadcasts: WS_EVENTS.ALERT_NEW (severity='critical')
   - Message includes limit type, currentValue, threshold

6. @OnEvent(LIMIT_APPROACHED)
   - Broadcasts: WS_EVENTS.ALERT_NEW (severity='warning')
   - Message includes percent used

7. @OnEvent(EXIT_TRIGGERED)
   - Broadcasts: WS_EVENTS.POSITION_UPDATE (status='closed')

8. @OnEvent(MATCH_APPROVED|REJECTED)
   - Broadcasts: WS_EVENTS.MATCH_PENDING (status='approved'|'rejected')

**Broadcast mechanism:**
- Iterates clients set, skips non-OPEN connections
- Wraps error handling (logs + removes dead clients)

## 6. DashboardEventMapperService — Event → DTO Mapping

**mapHealthEvent(health)** → WsHealthChangePayload
- Maps status + apiConnected + dataFresh flags

**mapExecutionCompleteEvent(event, status)** → WsExecutionCompletePayload
- Includes: orderId, platform, side, positionId, isPaper

**mapExecutionFailedEvent(event)** → WsExecutionCompletePayload
- status='failed', positionId=null

**mapSingleLegAlert(event)** → WsAlertNewPayload
- type='single_leg_exposure', severity='critical'
- Message format: `Single-leg exposure on position X: [platform] leg failed (reason)`

**mapLimitBreachedAlert(event)** → WsAlertNewPayload
- type='risk_limit_breached', severity='critical'
- Message shows limit type + values

**mapLimitApproachedAlert(event)** → WsAlertNewPayload
- type='risk_limit_approached', severity='warning'
- Message shows % used

**mapPositionUpdate(event)** → WsPositionUpdatePayload
- Lightweight: frontend refetches via REST on receiving this

**mapMatchApprovedEvent(event)** → WsMatchPendingPayload
- status='approved'

**mapMatchRejectedEvent(event)** → WsMatchPendingPayload
- status='rejected'

## 7. DTOs Overview

### Request DTOs
- ApproveMatchDto: { rationale: string }
- RejectMatchDto: { rationale: string }
- MatchListQueryDto: { status?, page?, limit? }
- CloseLegDto (execution module): { rationale: string }
- RetryLegDto (execution module): { price: string }

### Response DTOs
**PositionSummaryDto fields:**
```
id: string
pairName: string
platforms: { kalshi: string, polymarket: string }
entryPrices: { kalshi: string, polymarket: string }
currentPrices: { kalshi: string|null, polymarket: string|null }
initialEdge: string
currentEdge: string|null
unrealizedPnl: string|null
exitProximity: { stopLoss: string, takeProfit: string }|null
resolutionDate: string|null
timeToResolution: string|null
isPaper: boolean
status: string (OPEN|SINGLE_LEG_EXPOSED|EXIT_PARTIAL|CLOSED|RECONCILIATION_REQUIRED)
```

**Response Wrappers:**
- OverviewResponseDto: { data: DashboardOverviewDto, timestamp }
- HealthListResponseDto: { data: PlatformHealthDto[], count, timestamp }
- PositionDetailResponseDto: { data: PositionSummaryDto, timestamp }
- PositionListResponseDto: { data: PositionSummaryDto[], count, page, limit, timestamp }
- AlertListResponseDto: { data: AlertSummaryDto[], count, timestamp }
- MatchListResponseDto: { data: MatchSummaryDto[], count, page, limit, timestamp }
- MatchDetailResponseDto: { data: MatchSummaryDto, timestamp }
- MatchActionResponseDto: { data: { matchId, status, operatorRationale, timestamp }, timestamp }

**WebSocket Payloads:**
- WsHealthChangePayload
- WsExecutionCompletePayload
- WsAlertNewPayload
- WsPositionUpdatePayload
- WsMatchPendingPayload
- WsEventEnvelope<T>

## 8. Other Controllers (Non-Position-Close)

### MatchApprovalController
- POST /matches/:id/approve
- POST /matches/:id/reject
- GET /matches, GET /matches/:id
- Throws 409 CONFLICT if match already approved
- Emits MatchApprovedEvent / MatchRejectedEvent

### PerformanceController
- GET /performance/weekly
- GET /performance/daily
- GET /performance/trends
- Query params: weeks, days, mode (live|paper|all)

## 9. CRITICAL: Position Close/Exit Endpoints

**Execution module (NOT dashboard):**
- Controller: SingleLegResolutionController (src/modules/execution/)
- Base path: `/positions`
- POST `/positions/:id/retry-leg` — DTO: RetryLegDto { price: string }
- POST `/positions/:id/close-leg` — DTO: CloseLegDto { rationale: string }

**These are for SINGLE_LEG_EXPOSED recovery only, not normal position closure.**

**NO general position close endpoint exists in dashboard or execution controllers.**

## 10. Common Interfaces Check

**Existing interfaces in src/common/interfaces/:**
- IPlatformConnector
- IRiskManager
- IExecutionQueue
- IExecutionEngine
- IPriceFeedService (token-injected)

**NOT found:**
- IPositionCloseService
- IExitService

## 11. Architecture Observations

1. **Position queries are read-only**: Dashboard bypasses repository layer, uses PrismaService directly (acknowledged TODO in code)
2. **Enrichment is batched**: Protects connectors from concurrent RPC load (batch size 10)
3. **Prices are optional**: Partial enrichment allowed, warnings logged, frontend handles nulls
4. **WebSocket is fire-and-forget**: Never blocks execution cycle, dead clients auto-removed
5. **Alerts are single-source**: Only SINGLE_LEG_EXPOSED currently, hardcoded in getAlerts()
6. **Entry cost baseline**: Complex offset calculation (6.5.5i spec) for exit proximity
7. **All Decimals → strings**: 8 decimal places precision for API responses

## 12. Key Files
- /pm-arbitrage-engine/src/dashboard/dashboard.module.ts
- /pm-arbitrage-engine/src/dashboard/dashboard.controller.ts
- /pm-arbitrage-engine/src/dashboard/dashboard.service.ts
- /pm-arbitrage-engine/src/dashboard/dashboard.gateway.ts
- /pm-arbitrage-engine/src/dashboard/dashboard-event-mapper.service.ts
- /pm-arbitrage-engine/src/dashboard/position-enrichment.service.ts
- /pm-arbitrage-engine/src/dashboard/match-approval.controller.ts
- /pm-arbitrage-engine/src/dashboard/match-approval.service.ts
- /pm-arbitrage-engine/src/dashboard/performance.controller.ts
- /pm-arbitrage-engine/src/dashboard/dto/* (all DTOs)
- /pm-arbitrage-engine/src/modules/execution/single-leg-resolution.controller.ts
- /pm-arbitrage-engine/src/common/interfaces/price-feed-service.interface.ts
